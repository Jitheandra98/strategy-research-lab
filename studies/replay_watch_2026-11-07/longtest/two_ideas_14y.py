"""Two ideas from watching Sep 17 - Nov 6, checked on gold 5m 2012 - 2026-09-24 resampled to 30m (NY clock).
IDEA 1  SWEEP-RECLAIM FADE exactly as it made +$1,510 in the replay: first 30m bar that trades through an unswept Asia H/L
        (after 00:00 NY), London H/L (after 05:00) or PDH/PDL and CLOSES back inside -> fade at the close, stop beyond the bar's
        extreme + 0.1 ATR30, target 2R, exit after 4h (8 bars) if neither.
IDEA 2  US-MORNING SPIKE FADE (seen Oct 2, 7, 20, 23, Nov 5, 6): a 30m bar starting 08:00-10:00 NY whose range >= 2.5 x ATR30
        (prior bar) -> fade at its close, stop beyond the spike extreme + 0.1 ATR30, target 2R, exit after 4h.
Costs 0.3 pt. Stop first inside a bar. Control: same direction, stop and target distance at the same NY clock time on 20 random days."""
import numpy as np, pandas as pd
rng = np.random.default_rng(11)
a = np.fromfile("/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
df = pd.DataFrame(a[:, 1:], columns=list("ohlc"), index=pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York"))
b = df.resample("30min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
O, H, L, C = (b[k].to_numpy() for k in "ohlc"); N = len(C); idx = b.index
clock = (idx.hour * 60 + idx.minute).to_numpy()
tday = (idx.tz_localize(None) + pd.Timedelta(hours=6)).normalize().to_numpy()
yr = (idx.tz_localize(None) + pd.Timedelta(hours=6)).year.to_numpy()
pc = np.r_[C[0], C[:-1]]; tr = np.maximum(H - L, np.maximum(abs(H - pc), abs(L - pc)))
rma = lambda x: pd.Series(x).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
atr = rma(tr); atrp = np.r_[atr[0], atr[:-1]]
up = np.r_[0, np.diff(H)]; dn = np.r_[0, -np.diff(L)]
pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
pdi = 100 * rma(pdm) / rma(tr); mdi = 100 * rma(mdm) / rma(tr)
adx = rma(100 * np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-9))
regime = np.where(adx < 20, "RANGE", np.where((adx > 25) & (adx > np.r_[adx[0], adx[:-1]]), "TREND", "TRANSITION"))
gap_ok = np.r_[np.diff(idx.asi8) // 10**9 <= 1800 * 3, False]   # avoid weekend gaps inside the 4h window roughly

def trade(k, d, R, m=2.0, n=8):
    px = C[k]; stop = px - d * R; tgt = px + d * m * R
    for j in range(k + 1, min(k + 1 + n, N)):
        if (d == 1 and L[j] <= stop) or (d == -1 and H[j] >= stop): return -R
        if (d == 1 and H[j] >= tgt) or (d == -1 and L[j] <= tgt): return m * R
    return d * (C[min(k + n, N - 1)] - px)

pool = pd.Series(np.arange(N)).groupby(clock).apply(np.array).to_dict()
def control(k, d, R):
    p = pool[clock[k]]; rs = []
    for r in p[rng.integers(0, len(p), 40)]:
        if abs(r - k) < 60 or r + 8 >= N: continue
        rs.append((trade(r, d, R) - 0.3) / R)
        if len(rs) == 20: break
    return np.mean(rs)

rows = []
# IDEA 1
days, first = np.unique(tday, return_index=True); bounds = np.r_[first, N]; prevH = prevL = None
for di in range(len(days)):
    i0, i1 = bounds[di], bounds[di + 1]; ck = clock[i0:i1]
    asia = np.flatnonzero(ck >= 18 * 60) + i0; lon = np.flatnonzero((ck >= 120) & (ck < 300)) + i0
    lv = []
    if len(asia): lv += [(H[asia].max(), 1, asia[-1] + 1), (L[asia].min(), -1, asia[-1] + 1)]
    if len(lon): lv += [(H[lon].max(), 1, lon[-1] + 1), (L[lon].min(), -1, lon[-1] + 1)]
    if prevH is not None: lv += [(prevH, 1, i0), (prevL, -1, i0)]
    for p, side, s0 in lv:
        for k in range(s0, i1):
            if (side == 1 and H[k] > p) or (side == -1 and L[k] < p):
                if ((side == 1 and C[k] < p) or (side == -1 and C[k] > p)) and k + 8 < N:
                    d = -side; R = (H[k] + 0.1 * atr[k] - C[k]) if d == -1 else (C[k] - L[k] + 0.1 * atr[k])
                    if R > 0: rows.append(dict(idea="1 sweep-reclaim fade", k=k, d=d, R=R, regime=regime[k]))
                break
    prevH, prevL = H[i0:i1].max(), L[i0:i1].min()
# IDEA 2
for k in np.flatnonzero((clock >= 8 * 60) & (clock <= 10 * 60) & ((H - L) >= 2.5 * atrp))[:]:
    if k + 8 >= N: continue
    d = -1 if C[k] > O[k] else 1
    R = (H[k] + 0.1 * atr[k] - C[k]) if d == -1 else (C[k] - L[k] + 0.1 * atr[k])
    if R > 0: rows.append(dict(idea="2 US-morning spike fade", k=k, d=d, R=R, regime=regime[k]))
T = pd.DataFrame(rows)
T["pts"] = [trade(r.k, r.d, r.R) for r in T.itertuples()]
T["r"] = (T.pts - 0.3) / T.R; T["usd"] = (T.pts - 0.3) * 10
T["ctrl"] = [control(r.k, r.d, r.R) for r in T.itertuples()]
T["y"] = yr[T.k]; T["period"] = np.where(T.y <= 2019, "2012-2019", np.where(T.y <= 2023, "2020-2023", "2024-2026"))
def summ(g):
    r = g.r; return pd.Series(dict(trades=len(g), per_year=len(g) / g.y.nunique(), win=(r > 0).mean() * 100, avg_R=r.mean(),
        PF=r[r > 0].sum() / -r[r < 0].sum(), random_R=g.ctrl.mean(), edge=r.mean() - g.ctrl.mean(), avg_usd=g.usd.mean(), med_stop=g.R.median()))
pd.set_option("display.width", 220); pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(T.groupby(["idea", "period"]).apply(summ, include_groups=False).to_string()); print()
print(T.groupby(["idea", "regime"]).apply(summ, include_groups=False).to_string()); print()
T.to_csv("two_ideas_trades.csv", index=False)
T["year"] = T.y
print(T[T.y >= 2022].groupby(["idea", "year"]).apply(summ, include_groups=False).to_string())
