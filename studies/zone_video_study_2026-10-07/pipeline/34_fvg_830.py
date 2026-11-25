"""Stage 34: FVG made by the 8:30 NY candle (middle candle), limit at the near edge, stop beyond the 3-candle extreme,
2R/3R, flat 210 min later. Every 5m slot of the day run as control. Frozen in PREREGISTRATION.md (2026-10-27)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
M1, OUT, TF = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
COST = 0.30; VALID, FLAT = 150 // TF, 210 // TF
m1 = pd.read_pickle(M1)[["open", "high", "low", "close"]]
b = m1.resample(f"{TF}min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
T = b.index; O, H, L, C = (b[c].to_numpy() for c in ["open", "high", "low", "close"]); n = len(C)
pc = np.r_[np.nan, C[:-1]]; tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
A = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
ny = T.tz_convert("America/New_York"); slot = (ny.hour * 60 + ny.minute).to_numpy()
step = pd.Timedelta(minutes=TF)
rows = []
for m in range(1, n - FLAT - 2):
    i0, i2 = m - 1, m + 1
    if T[i2] - T[i0] != 2 * step: continue                     # three consecutive candles
    for d in (1, -1):
        gap = (L[i2] > H[i0]) if d == 1 else (H[i2] < L[i0])
        if not gap: continue
        top, bot = (L[i2], H[i0]) if d == 1 else (L[i0], H[i2])
        if top - bot < 0.25 * A[m]: continue
        entry = top if d == 1 else bot
        ext = min(L[i0], L[m], L[i2]) if d == 1 else max(H[i0], H[m], H[i2])
        stop = ext - d * 0.10 * A[m]; risk = d * (entry - stop)
        if risk <= 0: continue
        tend = T[m] + pd.Timedelta(minutes=FLAT * TF); tval = T[m] + pd.Timedelta(minutes=VALID * TF)
        f = None; k = i2 + 1
        while k < n and T[k] <= tval:
            if (d == 1 and L[k] <= entry) or (d == -1 and H[k] >= entry): f = k; break
            k += 1
        if f is None: continue
        out = {}
        for nm, kk in (("2R", 2), ("3R", 3)):
            tg = entry + d * kk * risk; R = None; q = f
            while q < n and T[q] < tend:
                if (d == 1 and L[q] <= stop) or (d == -1 and H[q] >= stop): R = -1.0; break
                if q > f and ((d == 1 and H[q] >= tg) or (d == -1 and L[q] <= tg)): R = float(kk); break
                q += 1
            if R is None: R = d * (C[min(n - 1, q - 1)] - entry) / risk
            out[nm] = R - COST / risk
        rows.append(dict(t=T[m], slot=slot[m], dir=d, risk=risk, **out))
R = pd.DataFrame(rows); R.to_pickle(OUT / f"fvg_slots_{TF}m.pkl")
R["period"] = np.where(R.t < pd.Timestamp("2021-01-01", tz="UTC"), "1 EXT 2016-20", np.where(R.t < pd.Timestamp("2026-04-01", tz="UTC"), "2 IS 2021-26/03", "3 FWD 2026-04→10"))
def s(g):
    out = {}
    for c in ("2R", "3R"):
        x = g[c]; out[f"n"] = len(x); out[f"{c}"] = x.mean(); out[f"{c}_ci"] = 1.96 * x.std() / np.sqrt(max(1, len(x)))
    out["win2R"] = (g["2R"] > 0).mean(); out["med_risk"] = g.risk.median(); return pd.Series(out)
pd.set_option("display.width", 220)
for nm, sl in (("8:30 NY", 510), ("9:30 NY (= 8:30 Central)", 570)):
    print(f"\n=== {TF}m · FVG made by the {nm} candle ===")
    print(R[R.slot == sl].groupby("period").apply(s, include_groups=False).round(3).to_string())
allslot = R.groupby("slot")["2R"].agg(["count", "mean"])
allslot["rank"] = allslot["mean"].rank(ascending=False).astype(int)
print(f"\nrank of 8:30 among {len(allslot)} slots (2R, all years):", allslot.loc[510].to_dict(), " 9:30:", allslot.loc[570].to_dict())
print("all slots: mean of means", allslot["mean"].mean().round(3), " best 5 slots:"); print(allslot.sort_values("mean", ascending=False).head(5).round(3).to_string())
