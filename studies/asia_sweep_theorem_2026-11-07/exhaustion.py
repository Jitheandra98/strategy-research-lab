"""Seen live on Sep 9 and Sep 11 2026: after a strong trend-down day, the next session sweeps the previous-day low, ADX turns
down, and price rallies. Pre-registered rule (30m, gold 5m 2012-2026 resampled, NY clock, Desk Context ADX14):
  previous day ends with ADX >= 30 and -DI > +DI (strong down day)  [mirror: +DI > -DI, sweep of PDH, SELL]
  today (18:00 -> 11:00 NY) price trades below PDL (sweep)
  A: first later bar with ADX falling and close back above PDL      -> BUY at close
  B: first later bar with +DI > -DI (the DI cross) and close > PDL   -> BUY at close
  stop under the lowest low since the sweep - 0.1 x ATR30; targets 2R / 3R; exit 16:55 NY. Cost 0.3 pt.
Control: same bracket, same NY clock time, 20 random other days."""
import numpy as np, pandas as pd
exec(open("range_fade.py").read().split("rows = []; prevH = prevL = None")[0])   # 30m bars, ADX/DI, walk(), days
rows = []
for di in range(1, len(days)):
    p0, p1 = bounds[di - 1], bounds[di]; i0, i1 = bounds[di], bounds[di + 1]
    pend = p1 - 1
    if adx[pend] < 30: continue
    d = 1 if mdi[pend] > pdi[pend] else -1                   # +1: yesterday trended DOWN -> look to BUY a PDL sweep
    lvl = L[p0:p1].min() if d == 1 else H[p0:p1].max()
    ck = clock[i0:i1]; win = np.flatnonzero((ck >= 18 * 60) | (ck < 11 * 60)) + i0
    endi = np.flatnonzero(ck < 17 * 60)
    if len(win) == 0 or len(endi) == 0: continue
    end = i0 + endi[-1]
    sw = win[(L[win] < lvl) if d == 1 else (H[win] > lvl)]
    if len(sw) == 0: continue
    s = sw[0]
    for name in ("A: ADX turns down", "B: DI cross"):
        for k in win[win >= s]:
            ok_close = C[k] > lvl if d == 1 else C[k] < lvl
            trig = (adx[k] < adx[k - 1]) if name.startswith("A") else ((pdi[k] > mdi[k]) if d == 1 else (mdi[k] > pdi[k]))
            if ok_close and trig:
                ext = L[s:k + 1].min() if d == 1 else H[s:k + 1].max()
                px = C[k]; stop = ext - d * 0.1 * atr[k]; R = abs(px - stop)
                if R > 0 and k + 1 <= end:
                    for m in (2.0, 3.0):
                        rows.append(dict(rule=name, y=yr[k], k=k, d=d, R=R, m=m, pts=walk(k + 1, d, px, stop, px + d * m * R, end)))
                break
T = pd.DataFrame(rows); T["r"] = (T.pts - 0.3) / T.R; T["usd"] = (T.pts - 0.3) * 10
dayidx = np.searchsorted(bounds, np.arange(N), side="right") - 1
ends = {di: bounds[di] + np.flatnonzero(clock[bounds[di]:bounds[di + 1]] < 17 * 60)[-1] for di in range(len(days)) if (clock[bounds[di]:bounds[di + 1]] < 17 * 60).any()}
byck = pd.Series(np.arange(N)).groupby(clock).apply(np.array).to_dict()
ctrl = []
for row in T.itertuples():
    p = byck[clock[row.k]]; rs = []
    for r in p[rng.integers(0, len(p), 40)]:
        e = ends.get(dayidx[r])
        if e is None or e <= r or dayidx[r] == dayidx[row.k]: continue
        px = C[r]; rs.append((walk(r + 1, row.d, px, px - row.d * row.R, px + row.d * row.m * row.R, e) - 0.3) / row.R)
        if len(rs) == 20: break
    ctrl.append(np.mean(rs) if rs else np.nan)
T["ctrl"] = ctrl; T["period"] = np.where(T.y <= 2019, "2012-2019", "2020-2026")
def summ(g):
    r = g.r; return pd.Series(dict(trades=len(g), per_year=len(g) / 14.7, win=(r > 0).mean() * 100, avg_R=r.mean(),
        PF=r[r > 0].sum() / -r[r < 0].sum(), random_R=g.ctrl.mean(), edge=r.mean() - g.ctrl.mean(), avg_usd=g.usd.mean(), med_stop_pts=g.R.median()))
pd.set_option("display.width", 220); pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(T.groupby(["rule", "m", "period"]).apply(summ, include_groups=False).to_string())
print("\nby side (A, 2R):"); print(T[(T.rule.str.startswith("A")) & (T.m == 2)].groupby(["d", "period"]).apply(summ, include_groups=False).to_string())
T.to_csv("exhaustion_trades.csv", index=False)
