"""Stage 33: reel claim — the supply/demand zone at the leg's volume-profile POC is the one that holds.
Profile = time at price (no real volume in spot gold). Frozen in PREREGISTRATION.md (2026-10-26 f)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
M1, OUT = sys.argv[1], Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
COST, P, VALID, TMAX = 0.30, 3, 120, 480
m1 = pd.read_pickle(M1)[["open", "high", "low", "close"]]
agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
h1 = m1.resample("1h").agg(agg).dropna(); m15 = m1.resample("15min").agg(agg).dropna(); m5 = m1.resample("5min").agg(agg).dropna()
T = h1.index; O, H, L, C = (h1[c].to_numpy() for c in ["open", "high", "low", "close"]); n = len(C)
pc = np.r_[np.nan, C[:-1]]; tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
A = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
T15 = m15.index.values; H15, L15, C15 = (m15[c].to_numpy() for c in ["high", "low", "close"])
T5 = m5.index.values; H5, L5 = m5.high.to_numpy(), m5.low.to_numpy()
t1 = T.values
rng = np.random.default_rng(9)


def poc(a, b, binw):
    s5, e5 = np.searchsorted(T5, t1[a]), np.searchsorted(T5, t1[b] + np.timedelta64(1, "h"))
    lo, hi = L5[s5:e5].min(), H5[s5:e5].max(); nb = max(1, int((hi - lo) / binw) + 1)
    prof = np.zeros(nb)
    for x, y in zip(L5[s5:e5], H5[s5:e5]):
        i0, i1 = int((x - lo) / binw), int((y - lo) / binw); prof[i0:i1 + 1] += 1.0 / (i1 - i0 + 1)
    k = int(np.argmax(prof)); return lo + (k + 0.5) * binw


def trade(d, top, bot, legx, legn, bbar):
    """SELL d=-1: limit at bot, stop top+buf. BUY d=1: limit at top, stop bot-buf."""
    buf = 0.10 * A[bbar]; entry = bot if d == -1 else top; stop = top + buf if d == -1 else bot - buf
    risk = abs(entry - stop); q0 = np.searchsorted(T15, t1[bbar] + np.timedelta64(1, "h")); q1 = min(len(C15) - 1, q0 + VALID * 4)
    fill = None
    for q in range(q0, q1):
        if (d == -1 and C15[q] > legx) or (d == 1 and C15[q] < legx): return None
        if (d == -1 and H15[q] >= entry) or (d == 1 and L15[q] <= entry): fill = q; break
    if fill is None: return None
    out = {}
    for nm, tg in (("2R", entry + d * 2 * risk), ("3R", entry + d * 3 * risk), ("leg", legn)):
        if d * (tg - entry) <= 0: out[nm] = np.nan; continue
        R = None
        for q in range(fill, min(len(C15), fill + TMAX)):
            if (d == -1 and H15[q] >= stop) or (d == 1 and L15[q] <= stop): R = -1.0; break
            if q > fill and ((d == -1 and L15[q] <= tg) or (d == 1 and H15[q] >= tg)): R = d * (tg - entry) / risk; break
        if R is None: R = d * (C15[min(len(C15) - 1, fill + TMAX - 1)] - entry) / risk
        out[nm] = R - COST / risk
    out["t"] = T[bbar]; out["risk"] = risk; return out


rows = []; sh = sl = None; shb = slb = None
for i in range(P * 2, n - 2):
    j = i - P
    if H[j] > H[j - P:j].max() and H[j] > H[j + 1:i + 1].max(): sh, shb = [H[j], False], j
    if L[j] < L[j - P:j].min() and L[j] < L[j + 1:i + 1].min(): sl, slb = [L[j], False], j
    for d, sw, swb in ((-1, sl, slb), (1, sh, shb)):
        if sw is None or sw[1] or np.isnan(A[i]) or i < 200: continue
        if not ((d == -1 and C[i] < sw[0]) or (d == 1 and C[i] > sw[0])): continue
        sw[1] = True
        seg = np.arange(swb, i + 1)
        a = seg[np.argmax(H[seg])] if d == -1 else seg[np.argmin(L[seg])]       # leg start (top for sells)
        if a >= i - 1: continue
        legx = H[a] if d == -1 else L[a]; legn = L[a:i + 1].min() if d == -1 else H[a:i + 1].max()
        zones = []
        for k in range(a + 2, i + 1):
            if d == -1 and H[k] < L[k - 2]: zones.append((L[k - 2], H[k], "FVG"))
            if d == 1 and L[k] > H[k - 2]: zones.append((L[k], H[k - 2], "FVG"))
        for k in range(a, max(-1, a - 6), -1):
            if (d == -1 and C[k] > O[k]) or (d == 1 and C[k] < O[k]): zones.append((H[k], L[k], "OB")); break
        if not zones: continue
        p = poc(a, i, 0.1 * A[i])
        for top, bot, kind in zones:
            if top - bot <= 0: continue
            grp = "POC zone" if bot <= p <= top else "other zone"
            r = trade(d, top, bot, legx, legn, i)
            if r: rows.append(dict(group=grp, kind=kind, dir=d, **r))
        # control 2: fake zone, same size as the first zone, random place inside the leg
        sz = zones[0][0] - zones[0][1]; lo_, hi_ = min(legx, legn), max(legx, legn)
        if hi_ - lo_ > sz:
            fb = rng.uniform(lo_, hi_ - sz); r = trade(d, fb + sz, fb, legx, legn, i)
            if r: rows.append(dict(group="random fake zone", kind="fake", dir=d, **r))
R = pd.DataFrame(rows); R.to_pickle(OUT / "poc_zone.pkl")
R["period"] = np.where(R.t < pd.Timestamp("2021-01-01", tz="UTC"), "1 EXT 2016-20", np.where(R.t < pd.Timestamp("2026-04-01", tz="UTC"), "2 IS 2021-26/03", "3 FWD 2026-04→10"))
pd.set_option("display.width", 220)
for tg in ("2R", "3R", "leg"):
    g = R.groupby(["period", "group"])[f"{tg}"].agg(n="count", meanR="mean", sd="std")
    g["ci95"] = 1.96 * g.sd / np.sqrt(g.n); g["win"] = R.groupby(["period", "group"])[tg].apply(lambda x: (x > 0).mean())
    print(f"\n=== target {tg} ==="); print(g.drop(columns="sd").round(3).unstack("group").to_string())
print("median risk $", R.risk.median())
