"""Watched on Sep 8 / 10 / 14 2026: in TREND (Desk Context ADX > 25 and rising), the first bounce into a fresh FVG was sold.
Rule (pre-registered): 30m gold 2012-2026. Bearish FVG: H[k] < L[k-2] (zone = H[k]..L[k-2]); bullish mirror.
When price first trades back into a fresh FVG (made within the last 20 bars, never touched) and the bar BEFORE shows
TREND in the FVG's direction (ADX > 25, ADX rising, -DI > +DI for sells / +DI > -DI for buys):
SELL at the FVG's bottom edge (limit), stop above the FVG top + 0.1 x ATR, targets 1.5R / 2R / 3R, max hold 16 bars (8 h).
Entry bar counted stop-first. Cost 0.3 pt. Control: same bracket, same clock time, 20 random bars."""
import numpy as np, pandas as pd
exec(open("range_fade.py").read().split("rows = []; prevH = prevL = None")[0])
def walk_n(k0, d, px, stop, tgt, n, entry_bar=False):
    end = min(k0 + n - 1, N - 1)
    if entry_bar and ((d == 1 and L[k0] <= stop) or (d == -1 and H[k0] >= stop)): return -abs(px - stop)
    for k in range(k0 + (1 if entry_bar else 0), end + 1):
        if d == 1:
            if L[k] <= stop: return stop - px
            if H[k] >= tgt: return tgt - px
        else:
            if H[k] >= stop: return px - stop
            if L[k] <= tgt: return px - tgt
    return d * (C[end] - px)
adx_up = np.r_[False, adx[1:] > adx[:-1]]
trend_dn = (adx > 25) & adx_up & (mdi > pdi); trend_up = (adx > 25) & adx_up & (pdi > mdi)
rows = []
for k in range(2, N - 40):
    if not (H[k] < L[k - 2] or L[k] > H[k - 2]): continue
    if H[k] < L[k - 2]: d, edge, far = -1, H[k], L[k - 2]          # bearish FVG: sell when price comes back up to H[k]
    else:               d, edge, far = 1, L[k], H[k - 2]           # bullish FVG: buy when price comes back down to L[k]
    for j in range(k + 1, min(k + 21, N - 17)):
        hit = H[j] >= edge if d == -1 else L[j] <= edge
        if not hit: continue
        ok = trend_dn[j - 1] if d == -1 else trend_up[j - 1]
        if ok:
            px = max(edge, O[j]) if d == -1 else min(edge, O[j])
            stop = far + 0.1 * atr[j] if d == -1 else far - 0.1 * atr[j]
            R = abs(px - stop)
            if R > 0:
                for m in (1.5, 2.0, 3.0):
                    rows.append(dict(y=yr[j], k=j, d=d, R=R, m=m, pts=walk_n(j, d, px, stop, px + d * m * R, 16, entry_bar=True)))
        break
T = pd.DataFrame(rows); T["r"] = (T.pts - 0.3) / T.R; T["usd"] = (T.pts - 0.3) * 10
byck = pd.Series(np.arange(N - 17)).groupby(clock[:N - 17]).apply(np.array).to_dict()
T["ctrl"] = [np.mean([(walk_n(r + 1, row.d, C[r], C[r] - row.d * row.R, C[r] + row.d * row.m * row.R, 16) - 0.3) / row.R
                      for r in byck[clock[row.k]][rng.integers(0, len(byck[clock[row.k]]), 20)]]) for row in T.itertuples()]
T["period"] = np.where(T.y <= 2019, "2012-2019", "2020-2026")
def summ(g):
    r = g.r; return pd.Series(dict(trades=len(g), per_year=len(g) / (g.y.max() - g.y.min() + 1), win=(r > 0).mean() * 100, avg_R=r.mean(),
        PF=r[r > 0].sum() / -r[r < 0].sum(), random_R=g.ctrl.mean(), edge=r.mean() - g.ctrl.mean(), avg_usd=g.usd.mean(), med_stop_pts=g.R.median()))
pd.set_option("display.width", 220); pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(T.groupby(["m", "period"]).apply(summ, include_groups=False).to_string())
print("\nby side, 2R:"); print(T[T.m == 2].groupby(["d", "period"]).apply(summ, include_groups=False).to_string())
T.to_csv("trend_pullback_trades.csv", index=False)
