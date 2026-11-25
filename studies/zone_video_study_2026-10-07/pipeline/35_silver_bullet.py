"""Stage 35: ICT Silver Bullet (03-04 / 10-11 / 14-15 NY): first 5m FVG formed in the window, limit at the near edge,
stop beyond candle 1, target = nearest draw on liquidity (PDH/PDL, today's extreme, Asia/London extreme) or 2R.
Every 1-hour window of the day run as control. Frozen in PREREGISTRATION.md (2026-10-27 b)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
M1, OUT = sys.argv[1], Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
COST, MINROOM = 0.30, 1.50
m1 = pd.read_pickle(M1)[["open", "high", "low", "close"]]
b = m1.resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
T = b.index; O, H, L, C = (b[c].to_numpy() for c in ["open", "high", "low", "close"]); n = len(C)
pc = np.r_[np.nan, C[:-1]]; tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
A = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
ny = T.tz_convert("America/New_York"); hr = ny.hour.to_numpy(); mn = (ny.hour * 60 + ny.minute).to_numpy()
tday = (ny - pd.Timedelta(hours=18)).normalize()                 # trading day starts 18:00 NY
dcode = pd.factorize(tday)[0]
step = pd.Timedelta(minutes=5)
# per-day highs/lows; Asia = 18:00-03:00, London = 03:00-08:00
df = pd.DataFrame({"d": dcode, "h": H, "l": L, "hr": hr})
dayHL = df.groupby("d").agg(h=("h", "max"), l=("l", "min"))
pdh = dayHL.h.shift(1).reindex(dcode).to_numpy(); pdl = dayHL.l.shift(1).reindex(dcode).to_numpy()
asia = (hr >= 18) | (hr < 3); lon = (hr >= 3) & (hr < 8)
# running extremes of today up to bar i (inclusive), asia/london only once complete
runH = df.groupby("d").h.cummax().to_numpy(); runL = df.groupby("d").l.cummin().to_numpy()
aH = df[asia].groupby("d").h.max().reindex(dcode).to_numpy(); aL = df[asia].groupby("d").l.min().reindex(dcode).to_numpy()
lH = df[lon].groupby("d").h.max().reindex(dcode).to_numpy(); lL = df[lon].groupby("d").l.min().reindex(dcode).to_numpy()
starts = np.where((ny.minute == 0) & (np.r_[True, dcode[1:] != dcode[:-1]] | True))[0]
rows = []
for s in starts:
    h0 = hr[s]
    wend = T[s] + pd.Timedelta(hours=1); flat = wend + pd.Timedelta(hours=1)
    k = s + 2
    while k < n and T[k] < wend:
        i0, m = k - 2, k - 1
        if T[i0] < T[s] - 2 * step or T[k] - T[i0] != 2 * step: k += 1; continue
        d = 1 if L[k] > H[i0] else (-1 if H[k] < L[i0] else 0)
        top, bot = (L[k], H[i0]) if d == 1 else (L[i0], H[k])
        if d == 0 or top - bot < 0.25 * A[m]: k += 1; continue
        entry = top if d == 1 else bot
        stop = (L[i0] - 0.10 * A[m]) if d == 1 else (H[i0] + 0.10 * A[m]); risk = d * (entry - stop)
        if risk <= 0: break
        p = i0 - 1
        lv = [pdh[k], runH[p] if dcode[p] == dcode[k] else np.nan] if d == 1 else [pdl[k], runL[p] if dcode[p] == dcode[k] else np.nan]
        if h0 >= 3 and h0 < 18: lv.append(aH[k] if d == 1 else aL[k])
        if h0 >= 8 and h0 < 18: lv.append(lH[k] if d == 1 else lL[k])
        lv = np.array([x for x in lv if not np.isnan(x)])
        lv = lv[(lv - entry) * d >= MINROOM]
        if not len(lv): break
        dol = lv.min() if d == 1 else lv.max()
        f = None; q = k + 1
        while q < n and T[q] < wend:
            if (d == 1 and L[q] <= entry) or (d == -1 and H[q] >= entry): f = q; break
            q += 1
        if f is None: break
        out = {}
        for nm, tg in (("DOL", dol), ("2R", entry + d * 2 * risk)):
            R = None; q = f
            while q < n and T[q] < flat:
                if (d == 1 and L[q] <= stop) or (d == -1 and H[q] >= stop): R = -1.0; break
                if q > f and ((d == 1 and H[q] >= tg) or (d == -1 and L[q] <= tg)): R = d * (tg - entry) / risk; break
                q += 1
            if R is None: R = d * (C[min(n - 1, q - 1)] - entry) / risk
            out[nm] = R - COST / risk
        rows.append(dict(t=T[s], hour=h0, dir=d, risk=risk, room_R=d * (dol - entry) / risk, **out))
        break
R = pd.DataFrame(rows); R.to_pickle(OUT / "silver_bullet_trades.pkl")
R["period"] = np.where(R.t < pd.Timestamp("2021-01-01", tz="UTC"), "1 EXT 2016-20", np.where(R.t < pd.Timestamp("2026-04-01", tz="UTC"), "2 IS 2021-26/03", "3 FWD 2026-04→10"))
def s(g):
    o = dict(n=len(g))
    for c in ("DOL", "2R"): o[c] = g[c].mean(); o[c + "_ci"] = 1.96 * g[c].std() / np.sqrt(max(1, len(g)))
    o["winDOL"] = (g.DOL > 0).mean(); o["med_risk$"] = g.risk.median(); o["med_room_R"] = g.room_R.median(); return pd.Series(o)
pd.set_option("display.width", 220)
for h in (3, 10, 14):
    print(f"\n=== Silver Bullet {h}:00–{h+1}:00 NY ===")
    print(R[R.hour == h].groupby("period").apply(s, include_groups=False).round(3).to_string())
print("\n=== all three windows pooled ===")
print(R[R.hour.isin([3, 10, 14])].groupby("period").apply(s, include_groups=False).round(3).to_string())
hh = R.groupby("hour")[["DOL", "2R"]].mean(); hh["n"] = R.groupby("hour").size()
hh["rank_DOL"] = hh.DOL.rank(ascending=False).astype(int); hh["rank_2R"] = hh["2R"].rank(ascending=False).astype(int)
print("\nevery hour of the day (all years):"); print(hh.round(3).T.to_string())
