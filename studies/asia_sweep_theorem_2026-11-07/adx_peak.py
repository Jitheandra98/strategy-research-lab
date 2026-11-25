"""Seen 3x in the Sep 2026 replay: 30m ADX climbs above 40 in a trend, the first bar it turns DOWN starts a 40-60 pt counter-move.
Rule (pre-registered): 30m, Desk Context ADX14. When ADX >= 40 and ADX < ADX[1] for the first time since it crossed 40:
trade AGAINST the trend (BUY if -DI > +DI) at that bar's close; stop beyond the trend extreme of the last 10 bars + 0.1 ATR;
targets 1R / 2R; max hold 16 bars (8 h). Cost 0.3 pt. Control: same bracket, same clock time, 20 random bars."""
import numpy as np, pandas as pd
exec(open("range_fade.py").read().split("rows = []; prevH = prevL = None")[0])
def walk_n(k0, d, px, stop, tgt, n):
    end = min(k0 + n - 1, N - 1)
    for k in range(k0, end + 1):
        if d == 1:
            if L[k] <= stop: return stop - px
            if H[k] >= tgt: return tgt - px
        else:
            if H[k] >= stop: return px - stop
            if L[k] <= tgt: return px - tgt
    return d * (C[end] - px)
rows = []; armed = False
for k in range(30, N - 17):
    if adx[k] >= 40 and adx[k - 1] < 40: armed = True
    if armed and adx[k] >= 40 and adx[k] < adx[k - 1]:
        armed = False
        d = 1 if mdi[k] > pdi[k] else -1
        ext = L[k - 9:k + 1].min() if d == 1 else H[k - 9:k + 1].max()
        px = C[k]; stop = ext - d * 0.1 * atr[k]; R = abs(px - stop)
        if R <= 0: continue
        for m in (1.0, 2.0):
            rows.append(dict(y=yr[k], k=k, d=d, R=R, m=m, pts=walk_n(k + 1, d, px, stop, px + d * m * R, 16)))
    if adx[k] < 40: armed = False
T = pd.DataFrame(rows); T["r"] = (T.pts - 0.3) / T.R; T["usd"] = (T.pts - 0.3) * 10
byck = pd.Series(np.arange(N - 17)).groupby(clock[:N - 17]).apply(np.array).to_dict()
ctrl = []
for row in T.itertuples():
    p = byck[clock[row.k]]; rs = [(walk_n(r + 1, row.d, C[r], C[r] - row.d * row.R, C[r] + row.d * row.m * row.R, 16) - 0.3) / row.R for r in p[rng.integers(0, len(p), 20)]]
    ctrl.append(np.mean(rs))
T["ctrl"] = ctrl; T["period"] = np.where(T.y <= 2019, "2012-2019", "2020-2026")
def summ(g):
    r = g.r; return pd.Series(dict(trades=len(g), per_year=len(g) / 14.7 * 2, win=(r > 0).mean() * 100, avg_R=r.mean(),
        PF=r[r > 0].sum() / -r[r < 0].sum(), random_R=g.ctrl.mean(), edge=r.mean() - g.ctrl.mean(), avg_usd=g.usd.mean(), med_stop_pts=g.R.median()))
pd.set_option("display.width", 220); pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(T.groupby(["m", "period"]).apply(summ, include_groups=False).to_string())
print(T[T.m == 1].groupby(["d", "period"]).apply(summ, include_groups=False).to_string())
