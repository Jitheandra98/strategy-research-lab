"""FIXED-EXIT ENTRY SEARCH (2026-11-09). The owner's rule: every trade is 1 MGC with a $250 stop and a $100 take profit.
1,764 entry strategies from the standard toolkit, each compared with random timing in the same direction.
Rules: SPEC.md (written before testing).  Run: python3 search.py > results.txt   (writes library_results.csv)"""
import numpy as np, pandas as pd
from numba import njit
from statistics import NormalDist

DATA = "/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64"
OUT = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/fixed_exit_search_2026-11-09/"
TP, SL, COST, SLIP, TICK, USD = 10.0, 25.0, 0.3, 0.2, 0.1, 10.0
MAXBARS, B, DEV_END = 20 * 276, 60, 2019
DAY_NS, FIVE = 86_400 * 10 ** 9, 300 * 10 ** 9

# ------------------------------------------------------------------------------------------------------------ data
a = np.fromfile(DATA).reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
idx = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)    # NY wall clock
O, H, L, C = (np.ascontiguousarray(a[:, i]) for i in range(1, 5))
N, ns = len(C), idx.asi8
clock = (idx.hour * 60 + idx.minute).to_numpy()
yr = idx.year.to_numpy()
msess = ((clock - 18 * 60) % 1440).astype(np.int64)                 # minutes since the 18:00 session open
sd_idx = (idx + pd.Timedelta(hours=6)).normalize()                   # session day = the date the session closes
sday, swd = sd_idx.asi8, sd_idx.weekday.to_numpy()                   # swd 0 = Monday session (opens Sunday 18:00)
wk = (sd_idx - pd.to_timedelta(swd, unit="D")).asi8                  # week id = Monday of the session week


# ------------------------------------------------------------------------------------------- exit outcome per bar
@njit(cache=True)
def outcomes(O, H, L, C, maxbars, tp, sl, cost, slip, tick):
    """Enter at the open of bar i, long (row 0) or short (row 1); +tp target (needs a tick through), -sl stop."""
    n = len(O)
    net = np.full((2, n), np.nan)
    ex = np.full((2, n), -1, np.int64)
    for i in range(n):
        e = O[i]
        last = min(n, i + maxbars)
        for side in range(2):
            x, res = -1, 0.0
            for j in range(i, last):
                if side == 0:
                    if j > i and O[j] <= e - sl:
                        res, x = O[j] - e - slip, j; break
                    if L[j] <= e - sl:
                        res, x = -sl - slip, j; break
                    if H[j] >= e + tp + tick - 1e-9:
                        res, x = tp, j; break
                else:
                    if j > i and O[j] >= e + sl:
                        res, x = e - O[j] - slip, j; break
                    if H[j] >= e + sl:
                        res, x = -sl - slip, j; break
                    if L[j] <= e - tp - tick + 1e-9:
                        res, x = tp, j; break
            if x == -1 and i + maxbars <= n:
                x = i + maxbars - 1
                res = (C[x] - e) if side == 0 else (e - C[x])
            if x >= 0:
                net[side, i] = res - cost
                ex[side, i] = x
    return net, ex


@njit(cache=True)
def take(entries, ex):
    keep = np.zeros(len(entries), np.bool_)
    last = -1
    for k in range(len(entries)):
        i = entries[k]
        if i > last and ex[i] >= 0:
            keep[k] = True
            last = ex[i]
    return keep


@njit(cache=True)
def null_means(pool, nsig, ex, net, b, seed):
    """Mean net per trade of b random-timing copies: nsig random bars from pool, one position at a time."""
    np.random.seed(seed)
    out = np.empty(b)
    for r in range(b):
        pick = np.sort(pool[np.random.randint(0, len(pool), nsig)])
        last, s, k = -1, 0.0, 0
        for q in range(len(pick)):
            i = pick[q]
            if i > last:
                s += net[i]
                k += 1
                last = ex[i]
        out[r] = s / k if k > 0 else np.nan
    return out


@njit(cache=True)
def streak(b):
    out = np.zeros(len(b), np.int64)
    run = 0
    for i in range(len(b)):
        run = run + 1 if b[i] else 0
        out[i] = run
    return out


@njit(cache=True)
def orb_events(sday, msess, H, L, C, start, length, cutoff):
    n = len(C)
    up, dn = np.zeros(n, np.bool_), np.zeros(n, np.bool_)
    i = 0
    while i < n:
        j = i
        while j < n and sday[j] == sday[i]:
            j += 1
        rh, rl, have = -1e18, 1e18, False
        for k in range(i, j):
            if start <= msess[k] < start + length:
                rh, rl, have = max(rh, H[k]), min(rl, L[k]), True
        if have:
            fu, fd = False, False
            for k in range(i, j):
                if start + length <= msess[k] < cutoff:
                    if not fu and C[k] > rh:
                        up[k], fu = True, True
                    if not fd and C[k] < rl:
                        dn[k], fd = True, True
        i = j
    return up, dn


@njit(cache=True)
def first_cross(group, hi, lo, C):
    n = len(C)
    up, dn = np.zeros(n, np.bool_), np.zeros(n, np.bool_)
    fu, fd = False, False
    for k in range(n):
        if k == 0 or group[k] != group[k - 1]:
            fu, fd = False, False
        if not fu and C[k] > hi[k]:
            up[k], fu = True, True
        if not fd and C[k] < lo[k]:
            dn[k], fd = True, True
    return up, dn


# -------------------------------------------------------------------------------------------------- indicators
def sh(x, k=1):
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    out[k:] = x[:-k]
    return out


def ema(x, n): return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()
def rma(x, n): return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().to_numpy()
def sma(x, n): return pd.Series(x).rolling(n).mean().to_numpy()
def sstd(x, n): return pd.Series(x).rolling(n).std(ddof=0).to_numpy()
def rmax(x, n): return pd.Series(x).rolling(n).max().to_numpy()
def rmin(x, n): return pd.Series(x).rolling(n).min().to_numpy()


def xup(x, y):
    y = np.full(len(x), float(y)) if np.isscalar(y) else y
    return (x > y) & (sh(x) <= sh(y))


def xdn(x, y):
    y = np.full(len(x), float(y)) if np.isscalar(y) else y
    return (x < y) & (sh(x) >= sh(y))


def true_range(h, l, c):
    pc = sh(c)
    return np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))


def tf_rules(o, h, l, c):
    R = []

    def add(fam, name, mask, d): R.append((fam, name, np.nan_to_num(mask).astype(bool), d))

    for f, s in [(5, 20), (9, 21), (10, 50), (20, 50), (20, 100), (50, 200)]:
        ef, es = ema(c, f), ema(c, s)
        add("EMA cross", f"EMA{f}/{s} cross up -> buy", xup(ef, es), 1)
        add("EMA cross", f"EMA{f}/{s} cross down -> sell", xdn(ef, es), -1)
    for n in [10, 20, 50, 100, 200]:
        e = ema(c, n)
        add("Price x EMA", f"close crosses above EMA{n} -> buy", xup(c, e), 1)
        add("Price x EMA", f"close crosses below EMA{n} -> sell", xdn(c, e), -1)
    for n in [10, 20, 55, 100]:
        hh, ll = sh(rmax(h, n)), sh(rmin(l, n))
        up, dn = xup(c, hh), xdn(c, ll)
        add("Donchian", f"close above {n}-bar high -> buy", up, 1)
        add("Donchian", f"close above {n}-bar high -> sell (fade)", up, -1)
        add("Donchian", f"close below {n}-bar low -> sell", dn, -1)
        add("Donchian", f"close below {n}-bar low -> buy (fade)", dn, 1)
    for n in [2, 14]:
        dlt = np.diff(c, prepend=c[0])
        g, ls = rma(np.maximum(dlt, 0), n), rma(np.maximum(-dlt, 0), n)
        r = 100 * g / (g + ls)
        for lv in [10, 20, 30]:
            lo_, hi_ = xdn(r, lv), xup(r, 100 - lv)
            add("RSI", f"RSI{n} crosses below {lv} -> buy (reversion)", lo_, 1)
            add("RSI", f"RSI{n} crosses below {lv} -> sell (momentum)", lo_, -1)
            add("RSI", f"RSI{n} crosses above {100 - lv} -> sell (reversion)", hi_, -1)
            add("RSI", f"RSI{n} crosses above {100 - lv} -> buy (momentum)", hi_, 1)
    m20, s20 = sma(c, 20), sstd(c, 20)
    for k in [2.0, 2.5]:
        ou, od = xup(c, m20 + k * s20), xdn(c, m20 - k * s20)
        add("Bollinger", f"close above BB(20,{k}) -> sell (fade)", ou, -1)
        add("Bollinger", f"close above BB(20,{k}) -> buy", ou, 1)
        add("Bollinger", f"close below BB(20,{k}) -> buy (fade)", od, 1)
        add("Bollinger", f"close below BB(20,{k}) -> sell", od, -1)
    macd = ema(c, 12) - ema(c, 26)
    sig = ema(macd, 9)
    add("MACD", "MACD crosses above signal -> buy", xup(macd, sig), 1)
    add("MACD", "MACD crosses below signal -> sell", xdn(macd, sig), -1)
    add("MACD", "MACD crosses above 0 -> buy", xup(macd, 0.0), 1)
    add("MACD", "MACD crosses below 0 -> sell", xdn(macd, 0.0), -1)
    upc, dnc = streak(c > sh(c)), streak(c < sh(c))
    for n in [3, 4, 5]:
        add("Streak", f"{n} down closes -> buy (reversion)", dnc == n, 1)
        add("Streak", f"{n} down closes -> sell (follow)", dnc == n, -1)
        add("Streak", f"{n} up closes -> sell (reversion)", upc == n, -1)
        add("Streak", f"{n} up closes -> buy (follow)", upc == n, 1)
    atr_p = sh(rma(true_range(h, l, c), 14))
    rg, body = h - l, np.abs(c - o)
    for k in [1.5, 2.0, 2.5, 3.0]:
        big = (rg >= k * atr_p) & (body >= 0.5 * rg)
        bu, bd = big & (c > o), big & (c < o)
        add("Big bar", f"big up bar {k}xATR -> buy", bu, 1)
        add("Big bar", f"big up bar {k}xATR -> sell (fade)", bu, -1)
        add("Big bar", f"big down bar {k}xATR -> sell", bd, -1)
        add("Big bar", f"big down bar {k}xATR -> buy (fade)", bd, 1)
    ins = (sh(h) < sh(h, 2)) & (sh(l) > sh(l, 2))
    ibu, ibd = ins & (c > sh(h, 2)), ins & (c < sh(l, 2))
    add("Inside bar", "inside-bar break up -> buy", ibu, 1)
    add("Inside bar", "inside-bar break up -> sell (fade)", ibu, -1)
    add("Inside bar", "inside-bar break down -> sell", ibd, -1)
    add("Inside bar", "inside-bar break down -> buy (fade)", ibd, 1)
    po, pc_ = sh(o), sh(c)
    bull = (pc_ < po) & (c > o) & (o <= pc_) & (c >= po)
    bear = (pc_ > po) & (c < o) & (o >= pc_) & (c <= po)
    add("Engulfing", "bullish engulfing -> buy", bull, 1)
    add("Engulfing", "bullish engulfing -> sell (fade)", bull, -1)
    add("Engulfing", "bearish engulfing -> sell", bear, -1)
    add("Engulfing", "bearish engulfing -> buy (fade)", bear, 1)
    ll14, hh14 = rmin(l, 14), rmax(h, 14)
    kk = 100 * (c - ll14) / np.where(hh14 > ll14, hh14 - ll14, np.nan)
    dk = sma(kk, 3)
    ku, kd = xup(kk, dk) & (kk < 20), xdn(kk, dk) & (kk > 80)
    add("Stochastic", "%K crosses up below 20 -> buy (reversion)", ku, 1)
    add("Stochastic", "%K crosses up below 20 -> sell", ku, -1)
    add("Stochastic", "%K crosses down above 80 -> sell (reversion)", kd, -1)
    add("Stochastic", "%K crosses down above 80 -> buy", kd, 1)
    for n in [10, 20]:
        roc = c / sh(c, n) - 1
        add("Momentum", f"ROC{n} turns positive -> buy", xup(roc, 0.0), 1)
        add("Momentum", f"ROC{n} turns negative -> sell", xdn(roc, 0.0), -1)
    return R


def st(x):
    n = len(x)
    if n < 2: return dict(n=n, win=np.nan, pf=np.nan, mean=np.nan, t=np.nan)
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    sd = x.std(ddof=1)
    return dict(n=n, win=100 * (x > 0).mean(), pf=pos / neg if neg > 0 else np.inf, mean=x.mean(),
                t=x.mean() / (sd / np.sqrt(n)) if sd > 0 else np.nan)


if __name__ == "__main__":
    np.seterr(all="ignore")
    NET, EX = outcomes(O, H, L, C, MAXBARS, TP, SL, COST, SLIP, TICK)
    dev_bar, val_bar = yr <= DEV_END, yr > DEV_END
    POOL = {(s, p): np.flatnonzero((EX[s] >= 0) & m).astype(np.int64)
            for s in range(2) for p, m in (("dev", dev_bar), ("val", val_bar))}
    SIG0 = {k: NET[k[0]][v].std() for k, v in POOL.items()}          # per-trade spread of random entries
    print(f"Gold spot 5m {idx[0]} -> {idx[-1]} ({N:,} bars). Every trade: 1 MGC, stop $250, take profit $100.")
    print(f"Cost 0.3 pt + 0.2 pt stop slippage: a win nets ${(TP - COST) * USD:.0f}, a loss costs "
          f"${(SL + SLIP + COST) * USD:.0f}+  ->  break-even win rate {100 * (SL + SLIP + COST) / (SL + SLIP + TP):.1f}%")
    print(f"Gold: {C[dev_bar][0]:,.0f} (Jan 2012) -> {C[yr == 2015].min():,.0f} (2015 low) -> {C[-1]:,.0f} (Sep 2026)")

    print("\n=== 1. RANDOM ENTRIES with this exit (every 5m bar as an entry) ===")
    for s, nm in ((0, "random BUY "), (1, "random SELL")):
        for p, m in (("2012-2019", dev_bar), ("2020-2026", val_bar)):
            x = NET[s][(EX[s] >= 0) & m]
            q = st(x)
            print(f"  {nm} {p}: win {q['win']:.1f}%  PF {q['pf']:.2f}  ${q['mean'] * USD:+.2f} per trade")

    # ---------------------------------------------------------------------------------------- daily trend + ATR
    df5 = pd.DataFrame({"o": O, "h": H, "l": L, "c": C}, index=idx)
    agg = {"o": "first", "h": "max", "l": "min", "c": "last"}
    D = df5.resample("1D", offset="18h").agg(agg).dropna()
    d_close = (D.index + pd.Timedelta("1D")).asi8
    d_up = (D.c.to_numpy() > ema(D.c.to_numpy(), 200))
    d_atr = rma(true_range(D.h.to_numpy(), D.l.to_numpy(), D.c.to_numpy()), 14)

    def trend_at(T):
        k = np.searchsorted(d_close, T, side="right") - 1
        out = np.zeros(len(T), np.int64)
        okk = k >= 199
        out[okk] = np.where(d_up[k[okk]], 1, -1)
        return out

    # ------------------------------------------------------------------------------------------ build the library
    base = []                                            # (family, timeframe, name, direction, entries, decision ns)

    def add_entries(fam, tf, name, d, ent, dec):
        ent, dec = np.asarray(ent, np.int64), np.asarray(dec, np.int64)
        okk = ent < N
        ent, dec = ent[okk], dec[okk]
        ent, first_i = np.unique(ent, return_index=True)
        base.append((fam, tf, name, d, ent, dec[first_i]))

    for tf, (rule, off) in {"15m": ("15min", "0min"), "1h": ("1h", "0min"), "4h": ("4h", "2h"),
                            "1D": ("1D", "18h")}.items():
        b = df5.resample(rule, offset=off).agg(agg).dropna()
        close_ns = (b.index + pd.Timedelta(rule)).asi8
        for fam, name, mask, d in tf_rules(*(b[k].to_numpy() for k in "ohlc")):
            cl = close_ns[mask]
            ent = np.searchsorted(ns, cl)
            okk = (ent < N)
            okk[okk] &= (ns[ent[okk]] - cl[okk]) <= 4 * DAY_NS
            add_entries(fam, tf, name, d, ent[okk], cl[okk])
    hours = [(h_, 0) for h_ in list(range(18, 24)) + list(range(0, 17))] + [(8, 30), (9, 30)]
    for hh, mm in hours:
        e_ = np.flatnonzero(clock == hh * 60 + mm)
        add_entries("Time of day", "5m", f"enter {hh:02d}:{mm:02d} -> buy", 1, e_, ns[e_])
        add_entries("Time of day", "5m", f"enter {hh:02d}:{mm:02d} -> sell", -1, e_, ns[e_])
    so = np.flatnonzero(np.r_[True, sday[1:] != sday[:-1]])
    for wd, wn in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        e_ = so[swd[so] == wd]
        add_entries("Weekday open", "5m", f"{wn} session open -> buy", 1, e_, ns[e_])
        add_entries("Weekday open", "5m", f"{wn} session open -> sell", -1, e_, ns[e_])
    for sess, st0, cut in (("Asia 18:00", 0, 480), ("London 03:00", 540, 840), ("NY 09:30", 930, 1320)):
        for ln in (15, 30, 60):
            up, dn = orb_events(sday, msess, H, L, C, st0, ln, cut)
            for msk, side_nm, follow in ((up, "break up", 1), (dn, "break down", -1)):
                k_ = np.flatnonzero(msk)
                add_entries("Opening range", "5m", f"{sess} {ln}m range {side_nm} -> follow", follow, k_ + 1,
                            ns[k_] + FIVE)
                add_entries("Opening range", "5m", f"{sess} {ln}m range {side_nm} -> fade", -follow, k_ + 1,
                            ns[k_] + FIVE)
    for grp, lab in ((sday, "previous day"), (wk, "previous week")):
        g = pd.DataFrame({"g": grp, "h": H, "l": L}).groupby("g").agg(h=("h", "max"), l=("l", "min"))
        ph, pl = g.h.shift(1), g.l.shift(1)
        hi, lo = ph.reindex(grp).to_numpy(), pl.reindex(grp).to_numpy()
        up, dn = first_cross(grp, np.nan_to_num(hi, nan=1e18), np.nan_to_num(lo, nan=-1e18), C)
        for msk, side_nm, follow in ((up, "high", 1), (dn, "low", -1)):
            k_ = np.flatnonzero(msk)
            add_entries("Prev high/low", "5m", f"close beyond {lab} {side_nm} -> follow", follow, k_ + 1, ns[k_] + FIVE)
            add_entries("Prev high/low", "5m", f"close beyond {lab} {side_nm} -> fade", -follow, k_ + 1, ns[k_] + FIVE)
    same = np.r_[False, sday[1:] == sday[:-1]]
    for step in (50, 100):
        lv = np.floor(C / step)
        for msk, side_nm, follow in (((lv > sh(lv)) & same, "up", 1), ((lv < sh(lv)) & same, "down", -1)):
            k_ = np.flatnonzero(msk)
            add_entries("Round number", "5m", f"close through ${step} level {side_nm} -> follow", follow, k_ + 1,
                        ns[k_] + FIVE)
            add_entries("Round number", "5m", f"close through ${step} level {side_nm} -> fade", -follow, k_ + 1,
                        ns[k_] + FIVE)
    mo = so[(swd[so] == 0) & (so > 0)]
    kd_ = np.searchsorted(d_close, ns[mo], side="right") - 1
    gap = O[mo] - C[mo - 1]
    atr_at = np.where(kd_ >= 14, d_atr[np.maximum(kd_, 0)], np.nan)
    for msk, side_nm, follow in ((gap >= 0.2 * atr_at, "up", 1), (gap <= -0.2 * atr_at, "down", -1)):
        e_ = mo[msk]
        add_entries("Weekly gap", "5m", f"weekly open gap {side_nm} -> follow", follow, e_, ns[e_])
        add_entries("Weekly gap", "5m", f"weekly open gap {side_nm} -> fade", -follow, e_, ns[e_])

    # trend-matched random baseline (added after the first run): random entries on bars in the same daily-trend state
    TR5 = trend_at(ns)
    BASE0 = {}
    for s in range(2):
        for p, m in (("dev", dev_bar), ("val", val_bar)):
            for state in (None, 1, -1):
                mm = (EX[s] >= 0) & m & (True if state is None else (TR5 == state))
                v = NET[s][mm]
                BASE0[s, p, state] = (v.mean(), v.std(), 100 * (v > 0).mean(), st(v)["pf"])
    print("\n  random entries split by the daily trend (daily close vs EMA200):")
    for s, nm in ((0, "BUY "), (1, "SELL")):
        for state, sn in ((1, "uptrend  "), (-1, "downtrend")):
            q1, q2 = BASE0[s, "dev", state], BASE0[s, "val", state]
            print(f"  random {nm} in a daily {sn}: 2012-19 win {q1[2]:.1f}% PF {q1[3]:.2f} ${q1[0] * USD:+.2f}   |   "
                  f"2020-26 win {q2[2]:.1f}% PF {q2[3]:.2f} ${q2[0] * USD:+.2f}")

    lib = []
    for fam, tf, name, d, ent, dec in base:
        trd = trend_at(dec)
        lib.append((fam, tf, name, "any trend", d, ent))
        lib.append((fam, tf, name, "with daily trend", d, ent[trd == d]))
        lib.append((fam, tf, name, "against daily trend", d, ent[trd == -d]))
    R = len(lib)
    zbar = NormalDist().inv_cdf(1 - 0.05 / R)
    print(f"\nLibrary: {len(base)} base rules x 3 trend variants = {R} strategies. Luck-adjusted bar: z >= {zbar:.2f}")

    # ------------------------------------------------------------------------------------------------- evaluate
    rows = []
    for r_i, (fam, tf, name, filt, d, ent) in enumerate(lib):
        s = 0 if d == 1 else 1
        keep = take(ent, EX[s])
        tr_ = ent[keep]
        x, y = NET[s][tr_], yr[tr_]
        row = dict(family=fam, tf=tf, rule=name, trend=filt, dir="buy" if d == 1 else "sell")
        for p, m_t, m_e in (("dev", y <= DEV_END, yr[ent] <= DEV_END), ("val", y > DEV_END, yr[ent] > DEV_END)):
            q = st(x[m_t])
            nsig = int(m_e.sum())
            if nsig >= 20 and q["n"] >= 2:
                nm = null_means(POOL[s, p], nsig, EX[s], NET[s], B, 7919 * r_i + (0 if p == "dev" else 1))
                mu, sdv = np.nanmean(nm), np.nanstd(nm)
                z_copies = (q["mean"] - mu) / sdv if sdv > 0 else np.nan
                # CORRECTION after the first run: random copies keep more trades than a clustered rule does, which
                # shrinks their spread and inflates z. Scale the spread to the rule's own number of trades instead.
                z = (q["mean"] - mu) / (SIG0[s, p] / np.sqrt(q["n"]))
            else:
                z = z_copies = np.nan
            state = None if filt == "any trend" else (d if filt.startswith("with") else -d)
            mu0, sg0 = BASE0[s, p, state][:2]
            row[f"{p}_zt"] = (q["mean"] - mu0) / (sg0 / np.sqrt(q["n"])) if q["n"] >= 2 else np.nan
            row.update({f"{p}_{k}": v for k, v in q.items()})
            row[f"{p}_z"], row[f"{p}_z_copies"] = z, z_copies
        row.update({f"all_{k}": v for k, v in st(x).items()})
        rows.append(row)
    G = pd.DataFrame(rows)
    G["naive"] = (G.dev_n >= 100) & (G.dev_pf >= 1.15) & (G.dev_t >= 2)
    G["passes"] = G.naive & (G.dev_z >= zbar)
    G["holds"] = G.passes & (G.val_pf >= 1.15) & (G.val_t >= 2) & (G.val_z >= 2)
    G["naive_holds"] = G.naive & (G.val_pf >= 1.15) & (G.val_t >= 2)
    G.to_csv(OUT + "library_results.csv", index=False)

    tested = G[G.dev_n >= 100]
    print("\n=== 2. THE SEARCH ===")
    print(f"  strategies with >= 100 trades in 2012-2019: {len(tested)}")
    print(f"  beat random timing at z >= 2 in 2012-2019: {int((tested.dev_z >= 2).sum())}  "
          f"(luck alone would give about {0.0228 * len(tested):.0f})")
    print(f"  NAIVE winners in 2012-2019 (PF >= 1.15, t >= 2, no luck check): {int(G.naive.sum())}  "
          f"->  still PF >= 1.15 and t >= 2 in 2020-2026: {int(G.naive_holds.sum())}")
    print(f"  PASS 2012-2019 with the luck check (z >= {zbar:.2f}): {int(G.passes.sum())}  ->  HOLD UP in 2020-2026: "
          f"{int(G.holds.sum())}")

    print("\n=== 3. BUY rules vs SELL rules (share of strategies with PF > 1) ===")
    for dname in ("buy", "sell"):
        g = tested[tested.dir == dname]
        print(f"  {dname:4s}: 2012-2019 {100 * (g.dev_pf > 1).mean():5.1f}%   2020-2026 {100 * (g.val_pf > 1).mean():5.1f}%   "
              f"beat random timing (z >= 2) 2012-19 {100 * (g.dev_z >= 2).mean():4.1f}%, 2020-26 "
              f"{100 * (g.val_z >= 2).mean():4.1f}%")

    def show(df, title):
        print(f"\n=== {title} ===")
        print("  rule                                                   tf   trend    dir |  2012-19: trades  win%   PF"
              "    $/tr     t     z  |  2020-26: trades  win%   PF    $/tr     t     z")
        for _, r in df.iterrows():
            print(f"  {r.rule[:52]:52s} {r.tf:4s} {r.trend[:7]:7s} {r.dir:4s} | {r.dev_n:7.0f} {r.dev_win:5.1f} "
                  f"{r.dev_pf:5.2f} {r.dev_mean * USD:+7.2f} {r.dev_t:+5.2f} {r.dev_z:+5.2f} | {r.val_n:7.0f} "
                  f"{r.val_win:5.1f} {r.val_pf:5.2f} {r.val_mean * USD:+7.2f} {r.val_t:+5.2f} {r.val_z:+5.2f}")

    show(tested.sort_values("dev_z", ascending=False).head(15), "4. BEST 15 AGAINST RANDOM TIMING IN 2012-2019 (by z)")
    show(G[G.naive].sort_values("dev_t", ascending=False).head(15), "5. NAIVE WINNERS OF 2012-2019 (by t) and their 2020-2026")
    show(G[G.all_n >= 200].sort_values("all_pf", ascending=False).head(10),
         "6. WHAT A CHERRY-PICKER WOULD SEE: best 14-year PF (>= 200 trades)")
    print(f"\n  (first-run z, copies with more trades than the rule: {int((tested.dev_z_copies >= 2).sum())} strategies "
          f"at z >= 2 in 2012-19; corrected: {int((tested.dev_z >= 2).sum())})")

    print("\n=== 7. THE CLOSEST ONE, in detail: sell a 5m close down through a $100 level ===")
    for i_, (fam, tf, name, filt, d, ent) in enumerate(lib):
        if name == "close through $100 level down -> follow":
            keep = take(ent, EX[1])
            tr_ = ent[keep]
            x = NET[1][tr_]
            q = st(x)
            yrs = pd.Series(x * USD, index=yr[tr_]).groupby(level=0).agg(["count", "sum"])
            print(f"  {filt:20s}: {q['n']:4d} trades, win {q['win']:.1f}%, PF {q['pf']:.2f}, ${q['mean'] * USD:+.2f}/trade, "
                  f"t {q['t']:+.2f}; last trade {idx[tr_[-1]].date() if len(tr_) else '-'}")
            print("     by year: " + "  ".join(f"{y_ % 100:02d}:{int(r_['count'])}/${r_['sum']:+,.0f}"
                                            for y_, r_ in yrs.iterrows()))
    last_dn = D.index[np.flatnonzero(~d_up[199:])[-1] + 199].date()
    print(f"  last day gold closed below its daily EMA200: {last_dn}")
    r7 = G[(G.rule == "close through $100 level down -> follow") & (G.trend == "with daily trend")].iloc[0]
    print(f"  vs random SELLS on the same downtrend days: 2012-19 z {r7.dev_zt:+.2f}, 2020-26 z {r7.val_zt:+.2f}")
    tt = G[(G.dev_n >= 100)]
    print(f"\n  beat the trend-matched random baseline at z >= 2: 2012-19 {int((tt.dev_zt >= 2).sum())} of {len(tt)}, "
          f"both periods {int(((tt.dev_zt >= 2) & (tt.val_zt >= 2)).sum())}; max z 2012-19 {tt.dev_zt.max():+.2f}")
