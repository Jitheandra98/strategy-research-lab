"""Stage 30: Claude's own plan — 4H 20-bar breakout with the EMA100 trend, 2-ATR stop, 10-bar trailing low. Frozen in
PREREGISTRATION.md (2026-10-26 c). usage: 30_trend_plan.py <minute_pickle> <out_dir>"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

M1, OUT = sys.argv[1], Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
COST = 0.50
m1 = pd.read_pickle(M1)[["open", "high", "low", "close"]]
b = m1.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
ny = b.index.tz_convert("America/New_York")
anc = (ny - pd.Timedelta(hours=17)).normalize() + pd.Timedelta(hours=17)
b["k"] = (anc + ((ny - anc) // pd.Timedelta(hours=4)) * pd.Timedelta(hours=4)).tz_convert("UTC")
h = b.groupby("k").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
T = h.index; O, H, L, C = (h[c].to_numpy() for c in ["open", "high", "low", "close"]); n = len(C)
pc = np.r_[np.nan, C[:-1]]
tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
A = np.full(n, np.nan); s = tr[:14].mean(); A[13] = s
for i in range(14, n): s = (s * 13 + tr[i]) / 14; A[i] = s
E = pd.Series(C).ewm(span=100, adjust=False).mean().to_numpy()
up = (C > E) & (E > np.r_[np.full(10, np.nan), E[:-10]])
dn = (C < E) & (E < np.r_[np.full(10, np.nan), E[:-10]])
hh20 = pd.Series(H).shift(1).rolling(20).max().to_numpy(); ll20 = pd.Series(L).shift(1).rolling(20).min().to_numpy()


def trade(i, d):
    entry = C[i]; stop = entry - d * 2 * A[i]; risk = 2 * A[i]
    for k in range(i + 1, n):
        if (d == 1 and L[k] <= stop) or (d == -1 and H[k] >= stop):
            px = min(stop, O[k]) if d == 1 else max(stop, O[k])
            return k, (d * (px - entry) - COST) / risk
        tl = L[max(0, k - 9):k + 1].min() if d == 1 else H[max(0, k - 9):k + 1].max()
        stop = max(stop, tl) if d == 1 else min(stop, tl)
    return n - 1, (d * (C[-1] - entry) - COST) / risk


def system(filt):
    rows = []; i = 120
    while i < n - 1:
        d = 0
        if C[i] > hh20[i] and (up[i] or not filt): d = 1
        elif C[i] < ll20[i] and (dn[i] or not filt): d = -1
        if d and not np.isnan(A[i]):
            k, R = trade(i, d); rows.append(dict(t=T[i], dir=d, R=R, bars=k - i)); i = k
        i += 1
    return pd.DataFrame(rows)


Tp = system(True); Tn = system(False)
rng = np.random.default_rng(5); rnd = []
for draw in range(20):
    rows = []; i = 120
    p = len(Tp) / (n - 120) * 1.0
    while i < n - 1:
        if rng.random() < p * 1.0 and not np.isnan(A[i]):
            d = rng.choice([-1, 1]); k, R = trade(i, d); rows.append(dict(t=T[i], dir=d, R=R, draw=draw)); i = k
        i += 1
    rnd.append(pd.DataFrame(rows))
Rn = pd.concat(rnd)
per = lambda t: np.where(t < pd.Timestamp("2021-01-01", tz="UTC"), "1 EXT 2016-20", np.where(t < pd.Timestamp("2026-04-01", tz="UTC"), "2 IS 2021-26/03", "3 FWD 2026-04→10"))
yrs = {"1 EXT 2016-20": 5.0, "2 IS 2021-26/03": 5.25, "3 FWD 2026-04→10": 0.56}
out = []
for name, D, k in (("PLAN T (trend filter)", Tp, 1), ("no trend filter", Tn, 1), ("random entries (20 draws)", Rn, 20)):
    D = D.copy(); D["period"] = per(D.t)
    for pr, g in D.groupby("period"):
        x = g.R; cum = x.cumsum(); dd = (cum - cum.cummax()).min() / (1 if k == 1 else 1)
        out.append(dict(system=name, period=pr, trades=len(x) / k, win=(x > 0).mean(), meanR=x.mean(),
                        ci95=1.96 * x.std() / np.sqrt(len(x)), pct_yr_at_half_pct=0.5 * x.sum() / k / yrs[pr],
                        worst_dd_R=dd if k == 1 else np.nan, median_bars=g.get("bars", pd.Series(dtype=float)).median()))
S = pd.DataFrame(out); S.to_csv(OUT / "trend_plan_summary.csv", index=False); Tp.to_pickle(OUT / "plan_t_trades.pkl")
pd.set_option("display.width", 220); print(S.round(3).to_string(index=False))
print("by year (PLAN T):"); print(Tp.groupby(Tp.t.dt.year).R.agg(["count", "sum", "mean"]).round(2).T.to_string())
print("median risk $", np.median(2 * A[120:]), "best trade R", Tp.R.max(), "share of R from top 10% trades", Tp.R.nlargest(max(1, len(Tp)//10)).sum() / Tp.R.sum())
