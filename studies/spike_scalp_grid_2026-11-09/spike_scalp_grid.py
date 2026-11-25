"""SPIKE SCALP GRID (2026-11-09). The owner's idea: a 5m volatility spike shows the true direction; enter with it on
1 MGC, take $20-30, keep a safe stop, about 1 hour (or 4 h with a smaller target and wider stop).
Rules: SPEC.md (written before testing). 432 combinations; the same grid on random entries (5 seeds) is the luck check.
Run: python3 spike_scalp_grid.py > results.txt   (also writes grid.csv)"""
import numpy as np, pandas as pd

DATA = "/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64"
OUT = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/spike_scalp_grid_2026-11-09/"
COST, SLIP, TICK, USD, M = 0.3, 0.2, 0.1, 10.0, 48            # M = 4 h of 5m bars
KS = [2.0, 2.5, 3.0]
WIN = {"ASIA": [(18 * 60, 24 * 60), (0, 2 * 60)], "LONDON": [(2 * 60, 8 * 60)], "NY_AM": [(8 * 60, 12 * 60)],
       "NY_PM": [(12 * 60, 17 * 60)]}
TPS, SLS, HS = [2.0, 3.0, 5.0], [2.0, 3.0, 5.0, 10.0, 20.0, 50.0], {"1h": 60, "4h": 240}
SEEDS = [1, 2, 3, 4, 5]
EPS = 1e-9

try:
    from numba import njit
except ImportError:                                            # plain Python fallback
    def njit(f): return f

# ------------------------------------------------------------------------------------------------------------ data
a = np.fromfile(DATA).reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
idx = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York")
O, H, L, C = (np.ascontiguousarray(a[:, i]) for i in range(1, 5))
N, ns = len(C), idx.asi8
clock = (idx.hour * 60 + idx.minute).to_numpy()
yr = idx.year.to_numpy()
pc = np.r_[C[0], C[:-1]]
tr = np.maximum(H - L, np.maximum(np.abs(H - pc), np.abs(L - pc)))
atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
atrp = np.r_[atr[0], atr[:-1]]                                 # ATR of the bars BEFORE the spike bar
ok = np.zeros(N, bool)
ok[:N - M - 1] = True                                          # room for a 4 h path
ok &= np.r_[np.diff(ns) == 300 * 10 ** 9, False]               # entry bar = the very next 5m bar
WMASK = {}
for w, spans in WIN.items():
    m = np.zeros(N, bool)
    for a0, a1 in spans: m |= (clock >= a0) & (clock < a1)
    WMASK[w] = m


def spike_signals(k):
    rng_ = H - L
    m = ok & (atrp > 0) & (rng_ >= k * atrp) & (np.abs(C - O) >= 0.5 * rng_) & (C != O)
    i = np.flatnonzero(m)
    return i, np.sign(C[i] - O[i]).astype(np.int64)


def random_signals(i_spk, seed):
    """Same number of entries per window as the spike set, random bars in that window, coin-flip direction."""
    rng = np.random.default_rng(seed)
    out = []
    for w in WIN:
        n = int(WMASK[w][i_spk].sum())
        cand = np.flatnonzero(ok & WMASK[w])
        out.append(rng.choice(cand, size=n, replace=False))
    i = np.sort(np.concatenate(out))
    return i, rng.choice(np.array([-1, 1]), size=len(i))


def first(mask):
    return np.where(mask.any(1), mask.argmax(1), M)


def prep(i, d):
    """Paths of the next 4 h for every entry, and the first bar that hits each target / stop inside each time limit."""
    e = i + 1
    J = e[:, None] + np.arange(M)[None, :]
    ent, dd = O[e][:, None], d[:, None]
    fav = np.where(dd > 0, H[J] - ent, ent - L[J])
    adv = np.where(dd > 0, ent - L[J], H[J] - ent)
    oadv = np.where(dd > 0, ent - O[J], O[J] - ent)
    oadv[:, 0] = 0.0                                            # we entered at that open
    el = ns[J] - ns[e][:, None]
    P = dict(i=i, e=e, y=yr[i], d=d, oadv=oadv, clr=dd * (C[J] - ent), win={w: WMASK[w][i] for w in WIN})
    for h, mins in HS.items():
        v = el < mins * 60 * 10 ** 9
        P["last", h] = v.sum(1) - 1
        for tp in TPS: P["tp", tp, h] = first((fav >= tp + TICK - EPS) & v)
        for sl in SLS: P["sl", sl, h] = first((adv >= sl - EPS) & v)
    return P


def outcome(P, tp, sl, h, target_first_on_tie=False):
    a_, b_, last = P["sl", sl, h], P["tp", tp, h], P["last", h]
    r = np.arange(len(a_))
    tie = (a_ == b_) & (a_ < M)
    stop_hit = (a_ < M) & ((a_ < b_) | (tie & (not target_first_on_tie)))
    tgt_hit = (b_ < M) & ~stop_hit
    oa = P["oadv"][r, np.minimum(a_, M - 1)]
    gross = np.where(stop_hit, -np.maximum(sl, oa) - SLIP, np.where(tgt_hit, tp, P["clr"][r, last]))
    xbar = np.where(stop_hit, a_, np.where(tgt_hit, b_, last))
    return gross - COST, P["e"] + xbar, tie


@njit
def one_at_a_time(e, xg):
    keep = np.zeros(len(e), np.bool_)
    last = -1
    for n in range(len(e)):
        if e[n] > last:
            keep[n] = True
            last = xg[n]
    return keep


def st(x):
    n = len(x)
    if n < 2: return dict(n=n, win=np.nan, pf=np.nan, mean=np.nan, t=np.nan)
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    return dict(n=n, win=100 * (x > 0).mean(), pf=pos / neg if neg > 0 else np.inf, mean=x.mean(),
                t=x.mean() / (x.std(ddof=1) / np.sqrt(n)) if x.std(ddof=1) > 0 else np.nan)


def grid(P, k, tag, bounds=(False,)):
    rows = []
    for tp in TPS:
        for sl in SLS:
            for h in HS:
                for fav in bounds:
                    net, xg, tie = outcome(P, tp, sl, h, fav)
                    for w in WIN:
                        s = np.flatnonzero(P["win"][w])
                        kp = s[one_at_a_time(P["e"][s], xg[s])]
                        x, y = net[kp], P["y"][kp]
                        dv, vl, al = st(x[y <= 2019]), st(x[y >= 2020]), st(x)
                        rows.append(dict(src=tag, k=k, window=w, tp=tp, sl=sl, hold=h,
                                         bound="target first on ties" if fav else "stop first (official)",
                                         **{f"dev_{q}": v for q, v in dv.items()}, **{f"val_{q}": v for q, v in vl.items()},
                                         **{f"all_{q}": v for q, v in al.items()}, tie_pct=100 * tie[kp].mean()))
    return rows


def flags(G):
    G = G.copy()
    G["looks"] = (G.dev_n >= 100) & (G.dev_pf >= 1.15) & (G.dev_t >= 2)
    G["holds"] = G.looks & (G.val_pf >= 1.15) & (G.val_t >= 2)
    return G


if __name__ == "__main__":
    print(f"Gold spot 5m {idx[0]} -> {idx[-1]} ({N:,} bars). 1 MGC = $10/pt. Cost 0.3 pt + 0.2 pt stop slippage.")
    rows, raw = [], []
    for k in KS:
        i, d = spike_signals(k)
        P = prep(i, d)
        print(f"\nk = {k}: {len(i):,} spike bars  (" + ", ".join(f"{w} {int(P['win'][w].sum()):,}" for w in WIN) + ")")
        rows += grid(P, k, "spike", bounds=(False, True))
        # raw push in the spike's direction before any cost: average move 1 h and 4 h after entry
        for h in HS:
            mv = P["clr"][np.arange(len(i)), P["last", h]]
            raw.append(dict(src="spike", k=k, hold=h, dev=mv[P["y"] <= 2019].mean(), val=mv[P["y"] >= 2020].mean()))
        for sd in SEEDS:
            ri, rd = random_signals(i, sd + int(k * 100))
            R = prep(ri, rd)
            rows += grid(R, k, f"random{sd}")
            for h in HS:
                mv = R["clr"][np.arange(len(ri)), R["last", h]]
                raw.append(dict(src=f"random{sd}", k=k, hold=h, dev=mv[R["y"] <= 2019].mean(),
                                val=mv[R["y"] >= 2020].mean()))
    G = flags(pd.DataFrame(rows))
    G.to_csv(OUT + "grid.csv", index=False)
    off = G[G.bound.str.startswith("stop")]

    print("\n=== 1. RAW PUSH: average move in the spike's direction after entry, BEFORE costs (points) ===")
    Rw = pd.DataFrame(raw)
    for (k, h), g in Rw.groupby(["k", "hold"]):
        sp, rn = g[g.src == "spike"].iloc[0], g[g.src != "spike"]
        print(f"  k {k}  {h}:  spikes  2012-19 {sp.dev:+.3f}  2020-26 {sp.val:+.3f}   |  random entries  2012-19 "
              f"{rn.dev.mean():+.3f}  2020-26 {rn.val.mean():+.3f}")
    print(f"  (the round trip costs {COST} pt plus {SLIP} pt on every stop)")

    print("\n=== 2. THE LUCK CHECK: how many of the 432 combinations look like winners in 2012-2019, and how many "
          "hold up in 2020-2026 ===")
    sp = off[off.src == "spike"]
    print(f"  SPIKE entries   : {int(sp.looks.sum()):3d} look like winners, {int(sp.holds.sum()):3d} hold up")
    for sd in SEEDS:
        rg = off[off.src == f"random{sd}"]
        print(f"  random seed {sd}  : {int(rg.looks.sum()):3d} look like winners, {int(rg.holds.sum()):3d} hold up")
    ub = G[(G.src == "spike") & ~G.bound.str.startswith("stop")]
    print(f"  upper bound (target counted first whenever a 5m bar touched both): {int(ub.looks.sum())} look like "
          f"winners, {int(ub.holds.sum())} hold up")

    print("\n=== 3. THE 15 BEST-LOOKING SPIKE COMBINATIONS IN 2012-2019 (by t), and what 2020-2026 did to them ===")
    top = sp[sp.dev_n >= 100].sort_values("dev_t", ascending=False).head(15)
    print("   k   window  TP  SL  hold |  2012-19: trades  win%    PF     $/trade    t  |  2020-26: trades  win%    PF   "
          "  $/trade    t  | ties")
    for _, r in top.iterrows():
        print(f"  {r.k:.1f} {r.window:7s} {r.tp:2.0f} {r.sl:3.0f}  {r.hold}  | {r.dev_n:7.0f} {r.dev_win:5.1f} "
              f"{r.dev_pf:5.2f} {r.dev_mean * USD:+8.2f} {r.dev_t:+5.2f} | {r.val_n:7.0f} {r.val_win:5.1f} {r.val_pf:5.2f} "
              f"{r.val_mean * USD:+8.2f} {r.val_t:+5.2f} | {r.tie_pct:4.1f}%")

    print("\n=== 4. WIN RATE IS NOT PROFIT: your exact shape (k 2.5, NY AM, take $20, 1 h), stop widened step by step ===")
    for sl in SLS:
        r = sp[(sp.k == 2.5) & (sp.window == "NY_AM") & (sp.tp == 2) & (sp.hold == "1h") & (sp.sl == sl)].iloc[0]
        print(f"  stop ${sl * USD:4.0f}:  {r.all_n:6.0f} trades  win {r.all_win:5.1f}%  PF {r.all_pf:4.2f}  "
              f"${r.all_mean * USD:+6.2f} per trade  -> 14-yr total ${r.all_n * r.all_mean * USD:+9,.0f}")
    print("  same, 4 h hold:")
    for sl in SLS:
        r = sp[(sp.k == 2.5) & (sp.window == "NY_AM") & (sp.tp == 2) & (sp.hold == "4h") & (sp.sl == sl)].iloc[0]
        print(f"  stop ${sl * USD:4.0f}:  {r.all_n:6.0f} trades  win {r.all_win:5.1f}%  PF {r.all_pf:4.2f}  "
              f"${r.all_mean * USD:+6.2f} per trade  -> 14-yr total ${r.all_n * r.all_mean * USD:+9,.0f}")

    print("\n=== 5. WHOLE GRID, 2012 -> Sep 2026 (official fills) ===")
    for src, g in (("spike", sp), ("random (5 seeds)", off[off.src != "spike"])):
        print(f"  {src:17s} combos with PF > 1: {100 * (g.all_pf > 1).mean():5.1f}%   PF >= 1.15: "
              f"{100 * (g.all_pf >= 1.15).mean():5.1f}%   median PF {g.all_pf.median():.2f}   best PF {g.all_pf.max():.2f}")
    best = sp.sort_values("all_t", ascending=False).iloc[0]
    print(f"  best spike combination over all 14 years: k {best.k} {best.window} TP {best.tp:.0f} SL {best.sl:.0f} "
          f"{best.hold}: {best.all_n:.0f} trades, PF {best.all_pf:.2f}, ${best.all_mean * USD:+.2f}/trade, t {best.all_t:+.2f}")
    print(f"  share of trades decided inside a 5m bar that touched both stop and target: median "
          f"{sp.tie_pct.median():.1f}% per combination, max {sp.tie_pct.max():.1f}%")
