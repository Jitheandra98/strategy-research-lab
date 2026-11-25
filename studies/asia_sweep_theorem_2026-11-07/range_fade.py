"""Idea born from watching the Sep 8-10 replay with the owner: Desk Context sweeps reverse in RANGE, run in TREND.
Rule (pre-registered before looking): 30m bars (built from gold 5m, NY clock). Levels = Asia H/L (after 00:00), London H/L (after
05:00), PDH/PDL. Desk Context alert: first 30m bar that trades through an unswept level and CLOSES back inside -> FADE it at the close
(sell a high-sweep, buy a low-sweep). Stop beyond the sweep bar + 0.1 x ATR30. Target 1.5R / 2R. Exit 16:55 NY. Cost 0.3 pt.
Regime at the signal bar = Desk Context on 30m: ADX14 < 20 RANGE; ADX > 25 and rising TREND; else TRANSITION.
Control: same bracket, same NY clock time, 20 random other days in the same regime class."""
import numpy as np, pandas as pd
rng = np.random.default_rng(3)
a = np.fromfile("/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
df = pd.DataFrame(a[:, 1:], columns=list("ohlc"), index=pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York"))
b = df.resample("30min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
O, H, L, C = (b[k].to_numpy() for k in "ohlc"); N = len(C)
idx = b.index; clock = (idx.hour * 60 + idx.minute).to_numpy()
tday = (idx.tz_localize(None) + pd.Timedelta(hours=6)).normalize().to_numpy()
yr = (idx.tz_localize(None) + pd.Timedelta(hours=6)).year.to_numpy()
pc = np.r_[C[0], C[:-1]]
tr = np.maximum(H - L, np.maximum(abs(H - pc), abs(L - pc)))
atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
up = np.r_[0, np.diff(H)]; dn = np.r_[0, -np.diff(L)]
pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
rma = lambda x: pd.Series(x).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
pdi = 100 * rma(pdm) / rma(tr); mdi = 100 * rma(mdm) / rma(tr)
adx = rma(100 * np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-9))
regime = np.where(adx < 20, "RANGE", np.where((adx > 25) & (adx > np.r_[adx[0], adx[:-1]]), "TREND", "TRANSITION"))
days, first = np.unique(tday, return_index=True); bounds = np.r_[first, N]

def walk(k0, d, px, stop, tgt, end):
    for k in range(k0, end + 1):
        if d == 1:
            if L[k] <= stop: return stop - px
            if H[k] >= tgt: return tgt - px
        else:
            if H[k] >= stop: return px - stop
            if L[k] <= tgt: return px - tgt
    return d * (C[end] - px)

rows = []; prevH = prevL = None
for di in range(len(days)):
    i0, i1 = bounds[di], bounds[di + 1]; ck = clock[i0:i1]
    endi = np.flatnonzero(ck < 17 * 60)
    if len(endi) == 0: continue
    end = i0 + endi[-1]
    asia = np.flatnonzero(ck >= 18 * 60) + i0; lon = np.flatnonzero((ck >= 2 * 60) & (ck < 5 * 60)) + i0
    levels = []   # (price, isHigh, active_from_index)
    if len(asia):
        a_end = asia[-1] + 1; levels += [(H[asia].max(), True, a_end), (L[asia].min(), False, a_end)]
    if len(lon):
        l_end = lon[-1] + 1; levels += [(H[lon].max(), True, l_end), (L[lon].min(), False, l_end)]
    if prevH is not None: levels += [(prevH, True, i0), (prevL, False, i0)]
    for lv, isH, start in levels:
        for k in range(max(start, i0), end):
            if (isH and H[k] > lv) or (not isH and L[k] < lv):           # first time traded through = swept
                if (isH and C[k] < lv) or (not isH and C[k] > lv):     # closed back inside -> Desk Context alert
                    d = -1 if isH else 1; px = C[k]
                    stop = (H[k] + 0.1 * atr[k]) if d == -1 else (L[k] - 0.1 * atr[k]); R = abs(px - stop)
                    if R > 0:
                        for m in (1.5, 2.0):
                            rows.append(dict(y=yr[k], k=k, d=d, R=R, m=m, regime=regime[k], adx=adx[k], pts=walk(k + 1, d, px, stop, px + d * m * R, end)))
                break
    prevH, prevL = H[i0:i1].max(), L[i0:i1].min()
T = pd.DataFrame(rows); T["r"] = (T.pts - 0.3) / T.R; T["usd"] = (T.pts - 0.3) * 10
# control: same bracket at the same clock time on random days in the same regime
dayidx = np.searchsorted(bounds, np.arange(N), side="right") - 1
ends = {di: bounds[di] + np.flatnonzero(clock[bounds[di]:bounds[di + 1]] < 17 * 60)[-1] for di in range(len(days)) if (clock[bounds[di]:bounds[di + 1]] < 17 * 60).any()}
pool = pd.DataFrame(dict(i=np.arange(N), ck=clock, rg=regime)).groupby(["ck", "rg"]).i.apply(np.array).to_dict()
ctrl = []
for row in T.itertuples():
    p = pool.get((clock[row.k], row.regime), np.array([])); rs = []
    for r in p[rng.integers(0, max(len(p), 1), 40)] if len(p) else []:
        e = ends.get(dayidx[r]);
        if e is None or e <= r or dayidx[r] == dayidx[row.k]: continue
        px = C[r]; rs.append((walk(r + 1, row.d, px, px - row.d * row.R, px + row.d * row.m * row.R, e) - 0.3) / row.R)
        if len(rs) == 20: break
    ctrl.append(np.mean(rs) if rs else np.nan)
T["ctrl"] = ctrl; T["period"] = np.where(T.y <= 2019, "2012-2019", "2020-2026")
def summ(g):
    r = g.r; return pd.Series(dict(trades=len(g), per_year=len(g) / g.y.nunique(), win=(r > 0).mean() * 100, avg_R=r.mean(),
        PF=r[r > 0].sum() / -r[r < 0].sum(), random_R=g.ctrl.mean(), edge=r.mean() - g.ctrl.mean(), avg_usd=g.usd.mean(), med_stop_pts=g.R.median()))
pd.set_option("display.width", 220); pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(T.groupby(["m", "regime", "period"]).apply(summ, include_groups=False).to_string())
T.to_csv("range_fade_trades.csv", index=False)
