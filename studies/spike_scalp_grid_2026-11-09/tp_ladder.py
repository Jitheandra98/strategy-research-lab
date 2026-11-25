"""TP LADDER (2026-11-09). The owner asked how big the take profit must be for the 5m spike setup to become profitable.
Same spikes (2.5 x ATR, body >= 50 %), fills and costs as spike_scalp_grid.py / SPEC.md. Targets from 2 pt ($20) to 50 pt
($500) and no target at all; stops $50-$500; holds 1 h, 4 h, 1 day. Random entries (5 seeds) are the luck check.
Run: python3 tp_ladder.py > tp_ladder.txt"""
import numpy as np, pandas as pd

try:
    from numba import njit
except ImportError:
    def njit(f): return f

DATA = "/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64"
COST, SLIP, TICK, USD, M, K = 0.3, 0.2, 0.1, 10.0, 288, 2.5      # M = 24 h of 5m bars
TPS = [2, 3, 5, 8, 10, 15, 20, 30, 50, np.inf]
SLS = [5, 10, 20, 50]
HS = {"1 h": 60, "4 h": 240, "1 day": 1440}
WIN = {"ASIA": [(18 * 60, 24 * 60), (0, 2 * 60)], "LONDON": [(2 * 60, 8 * 60)], "NY_AM": [(8 * 60, 12 * 60)],
       "NY_PM": [(12 * 60, 17 * 60)]}
EPS = 1e-9

a = np.fromfile(DATA).reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
idx = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York")
O, H, L, C = (np.ascontiguousarray(a[:, i]) for i in range(1, 5))
N, ns = len(C), idx.asi8
clock = (idx.hour * 60 + idx.minute).to_numpy()
yr = idx.year.to_numpy()
pc = np.r_[C[0], C[:-1]]
tr = np.maximum(H - L, np.maximum(np.abs(H - pc), np.abs(L - pc)))
atrp = np.r_[0.0, pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()[:-1]]
ok = np.zeros(N, bool)
ok[:N - M - 1] = True
ok &= np.r_[np.diff(ns) == 300 * 10 ** 9, False]
WMASK = {}
for w, spans in WIN.items():
    m = np.zeros(N, bool)
    for a0, a1 in spans: m |= (clock >= a0) & (clock < a1)
    WMASK[w] = m


def first(mask):
    return np.where(mask.any(1), mask.argmax(1), M)


def prep(i, d):
    e = i + 1
    J = e[:, None] + np.arange(M)[None, :]
    ent, dd = O[e][:, None], d[:, None]
    fav = np.where(dd > 0, H[J] - ent, ent - L[J])
    adv = np.where(dd > 0, ent - L[J], H[J] - ent)
    oadv = np.where(dd > 0, ent - O[J], O[J] - ent)
    oadv[:, 0] = 0.0
    el = ns[J] - ns[e][:, None]
    P = dict(e=e, y=yr[i], oadv=oadv, clr=dd * (C[J] - ent), win={w: WMASK[w][i] for w in WIN})
    for h, mins in HS.items():
        v = el < mins * 60 * 10 ** 9
        P["last", h] = v.sum(1) - 1
        for tp in TPS:
            P["tp", tp, h] = np.full(len(e), M) if np.isinf(tp) else first((fav >= tp + TICK - EPS) & v)
        for sl in SLS: P["sl", sl, h] = first((adv >= sl - EPS) & v)
    return P


def outcome(P, tp, sl, h):
    """Net (after 0.3 pt cost, 0.2 pt stop slippage) and gross (no cost, no slippage) per trade; exit bar."""
    a_, b_, last = P["sl", sl, h], P["tp", tp, h], P["last", h]
    r = np.arange(len(a_))
    stop_hit = (a_ < M) & (a_ <= b_)                               # stop first if both in one bar
    tgt_hit = (b_ < M) & ~stop_hit
    oa = P["oadv"][r, np.minimum(a_, M - 1)]
    tp_val = tp if np.isfinite(tp) else 0.0
    base = np.where(tgt_hit, tp_val, P["clr"][r, last])
    gross = np.where(stop_hit, -np.maximum(sl, oa), base)
    net = np.where(stop_hit, gross - SLIP, gross) - COST
    return net, gross, P["e"] + np.where(stop_hit, a_, np.where(tgt_hit, b_, last))


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
                t=x.mean() / (x.std(ddof=1) / np.sqrt(n)))


def ladder(P, tag, wsets):
    rows = []
    for tp in TPS:
        for sl in SLS:
            for h in HS:
                net, gross, xg = outcome(P, tp, sl, h)
                for wname, wl in wsets.items():
                    s = np.flatnonzero(np.logical_or.reduce([P["win"][w] for w in wl]))
                    kp = s[one_at_a_time(P["e"][s], xg[s])]
                    y = P["y"][kp]
                    a_, d_, v_ = st(net[kp]), st(net[kp][y <= 2019]), st(net[kp][y >= 2020])
                    rows.append(dict(src=tag, sessions=wname, tp=tp, sl=sl, hold=h, n=a_["n"], win=a_["win"], pf=a_["pf"],
                                     net=a_["mean"], gross=gross[kp].mean(), t=a_["t"], dev_pf=d_["pf"], dev_t=d_["t"],
                                     dev_n=d_["n"], val_pf=v_["pf"], val_t=v_["t"]))
    return rows


if __name__ == "__main__":
    rng_ = H - L
    sig = ok & (atrp > 0) & (rng_ >= K * atrp) & (np.abs(C - O) >= 0.5 * rng_) & (C != O)
    i = np.flatnonzero(sig); d = np.sign(C[i] - O[i]).astype(np.int64)
    WS = {"NY AM (your setup)": ["NY_AM"], "all sessions": list(WIN)}
    rows = ladder(prep(i, d), "spike", WS)
    for sd in range(1, 6):
        rng = np.random.default_rng(1000 + sd); parts = []
        for w in WIN:
            cand = np.flatnonzero(ok & WMASK[w])
            parts.append(rng.choice(cand, size=int(WMASK[w][i].sum()), replace=False))
        ri = np.sort(np.concatenate(parts))
        rows += ladder(prep(ri, rng.choice(np.array([-1, 1]), size=len(ri))), f"random{sd}", WS)
    G = pd.DataFrame(rows)
    G.to_csv("/Users/jitheandrasubramaniam/Desktop/hey hey/research/spike_scalp_grid_2026-11-09/tp_ladder.csv", index=False)
    G["looks"] = (G.dev_n >= 100) & (G.dev_pf >= 1.15) & (G.dev_t >= 2)
    G["holds"] = G.looks & (G.val_pf >= 1.15) & (G.val_t >= 2)
    lab = lambda tp: "none" if np.isinf(tp) else f"${tp * USD:,.0f}"

    print("Gold spot 5m 2012 -> Sep 2026, spike = 2.5 x ATR 5m bar, 1 MGC, cost 0.3 pt + 0.2 pt on stops.")
    S = G[(G.src == "spike") & (G.sessions == "NY AM (your setup)")]
    for sl, h in ((10, "4 h"), (10, "1 day"), (50, "1 day")):
        print(f"\n=== YOUR SETUP (NY AM spikes), stop ${sl * USD:.0f}, hold {h}: raising the take profit ===")
        print("  target |  trades  win %  | before costs $/trade | after costs $/trade |   PF  | 14-yr total")
        for _, r in S[(S.sl == sl) & (S.hold == h)].iterrows():
            print(f"  {lab(r.tp):>6s} | {r.n:7.0f} {r.win:6.1f} | {r.gross * USD:+19.2f} | {r.net * USD:+19.2f} | "
                  f"{r.pf:5.2f} | ${r.n * r.net * USD:+10,.0f}")

    print("\n=== EVERY TARGET, all 12 stop/hold choices: average before-costs result and the BEST PF found ===")
    for sess in WS:
        print(f"\n  {sess}")
        print("  target | spikes: before costs $/trade (avg)  best PF |  random: before costs $/trade (avg)  best PF (5 seeds)")
        for tp in TPS:
            sp = G[(G.src == "spike") & (G.sessions == sess) & (G.tp == tp)]
            rn = G[(G.src != "spike") & (G.sessions == sess) & (G.tp == tp)]
            bests = rn.groupby("src").pf.max()
            print(f"  {lab(tp):>6s} | {sp.gross.mean() * USD:+28.2f}  {sp.pf.max():7.2f} | {rn.gross.mean() * USD:+28.2f}  "
                  f"{bests.min():.2f}-{bests.max():.2f}")

    sp = G[G.src == "spike"]
    print(f"\nSpike combinations with PF > 1 over 14 years: {int((sp.pf > 1).sum())} of {len(sp)}; "
          f"look like winners in 2012-19: {int(sp.looks.sum())}; hold up in 2020-26: {int(sp.holds.sum())}")
    for sd in range(1, 6):
        rg = G[G.src == f"random{sd}"]
        print(f"random seed {sd}: PF > 1: {int((rg.pf > 1).sum())} of {len(rg)}; look like winners: {int(rg.looks.sum())}; "
              f"hold up: {int(rg.holds.sum())}")
    top = sp.sort_values("pf", ascending=False).head(8)
    print("\nBest 8 spike combinations by 14-year PF:")
    for _, r in top.iterrows():
        print(f"  {r.sessions:18s} target {lab(r.tp):>5s} stop ${r.sl * USD:3.0f} hold {r.hold:5s}: {r.n:5.0f} trades, "
              f"PF {r.pf:.2f}, ${r.net * USD:+.2f}/trade, t {r.t:+.2f} | 2012-19 PF {r.dev_pf:.2f}, 2020-26 PF {r.val_pf:.2f}")
