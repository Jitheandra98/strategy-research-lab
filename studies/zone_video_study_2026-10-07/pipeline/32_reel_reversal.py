"""Stage 32: Instagram reel's 5-step reversal (HTF level, sweep, MSS, FVG/OB, 0.71 fib entry, -0.27 target).
Frozen in PREREGISTRATION.md (2026-10-26 e). usage: 32_reel_reversal.py <minute_pickle> <out_dir>"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
M1, OUT = sys.argv[1], Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
COST, P = 0.30, 3
m1 = pd.read_pickle(M1)[["open", "high", "low", "close"]]
agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
b = m1.resample("15min").agg(agg).dropna()
ny = b.index.tz_convert("America/New_York"); anc = (ny - pd.Timedelta(hours=17)).normalize() + pd.Timedelta(hours=17)
b["k"] = (anc + ((ny - anc) // pd.Timedelta(hours=4)) * pd.Timedelta(hours=4)).tz_convert("UTC")
h4 = b.groupby("k").agg(high=("high", "max"), low=("low", "min"), close=("close", "last"), last=("open", lambda s: s.index[-1]))
T = b.index; O, H, L, C = (b[c].to_numpy() for c in ["open", "high", "low", "close"]); n = len(C)


def atr(H, L, C):
    pc = np.r_[np.nan, C[:-1]]; tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
    return pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()


A15 = atr(H, L, C); H4, L4, C4 = h4.high.to_numpy(), h4.low.to_numpy(), h4.close.to_numpy(); A4 = atr(H4, L4, C4)
# 4H swing levels with the 15m bar from which each is known (confirm bar close)
conf_t = (h4["last"] + pd.Timedelta(minutes=15)).to_numpy()
lv = {1: [], -1: []}   # (known_from_15m_index, level, h4 index)
for j in range(P, len(h4) - P):
    k = j + P
    kn = np.searchsorted(T.values, conf_t[k].astype(T.values.dtype)) if False else np.searchsorted(T.tz_convert(None).values, pd.Timestamp(conf_t[k]).tz_convert(None).to_datetime64())
    if L4[j] < L4[j - P:j].min() and L4[j] < L4[j + 1:k + 1].min(): lv[1].append((kn, L4[j], j))
    if H4[j] > H4[j - P:j].max() and H4[j] > H4[j + 1:k + 1].max(): lv[-1].append((kn, H4[j], j))
a4_15 = pd.merge_asof(pd.DataFrame({"t": T}), pd.DataFrame({"t": pd.to_datetime(conf_t, utc=True), "a": A4}).sort_values("t"), on="t").a.to_numpy()
# 15m confirmed swings known at each bar
lastSL = np.full(n, np.nan); lastSH = np.full(n, np.nan); sl = sh = np.nan
for i in range(n):
    j = i - P
    if j >= P:
        if L[j] < L[j - P:j].min() and L[j] < L[j + 1:i + 1].min(): sl = L[j]
        if H[j] > H[j - P:j].max() and H[j] > H[j + 1:i + 1].max(): sh = H[j]
    lastSL[i], lastSH[i] = sl, sh


def keylevel_ok(i, d, ext):
    a = a4_15[i]
    if np.isnan(a): return False
    for kn, lvl, j in reversed(lv[d]):
        if kn > i: continue
        if (T[i] - h4.index[j]).days > 30: break
        seg = C[kn:i] if kn < i else np.array([])
        broken = (seg < lvl).any() if d == 1 else (seg > lvl).any()
        if not broken and abs(ext - lvl) <= 0.25 * a: return True
    return False


rows = []; busy = {1: -1, -1: -1}
for i in range(300, n - 400):
    for d in (1, -1):
        if i <= busy[d]: continue
        ref = lastSL[i - 1] if d == 1 else lastSH[i - 1]
        if np.isnan(ref): continue
        swept = (L[i] < ref and C[i] > ref) if d == 1 else (H[i] > ref and C[i] < ref)
        if not swept: continue
        ext = L[i] if d == 1 else H[i]
        key = keylevel_ok(i, d, ext)
        # MSS within 24 bars
        m = None
        for k in range(i + 1, i + 25):
            ext = min(ext, L[k]) if d == 1 else max(ext, H[k])
            lvl = lastSH[k - 1] if d == 1 else lastSL[k - 1]
            if not np.isnan(lvl) and ((d == 1 and C[k] > lvl) or (d == -1 and C[k] < lvl)): m = k; break
        if m is None: continue
        legx = H[i:m + 1].max() if d == 1 else L[i:m + 1].min()
        rng = d * (legx - ext)
        if rng <= 0: continue
        fvg = any(((L[q] > H[q - 2]) if d == 1 else (H[q] < L[q - 2])) for q in range(i + 2, m + 1))
        entry = legx - d * 0.71 * rng; stop = ext - d * 0.10 * A15[m]; tgt = legx + d * 0.27 * rng
        risk = d * (entry - stop)
        f = None
        for k in range(m + 1, m + 49):
            if (d == 1 and L[k] <= entry) or (d == -1 and H[k] >= entry): f = k; break
        res = dict(t=T[i], dir=d, key=key, fvg=fvg, filled=f is not None, risk=risk, rr=d * (tgt - entry) / risk)
        if f is not None:
            R = None
            for k in range(f, min(n, f + 288)):
                if (d == 1 and L[k] <= stop) or (d == -1 and H[k] >= stop): R = -1.0; break
                if k > f and ((d == 1 and H[k] >= tgt) or (d == -1 and L[k] <= tgt)): R = d * (tgt - entry) / risk; break
            if R is None: R = d * (C[min(n - 1, f + 287)] - entry) / risk
            res["R"] = R - COST / risk; busy[d] = k
        else:
            busy[d] = m + 48
        rows.append(res)
R = pd.DataFrame(rows); R.to_pickle(OUT / "reel_reversal.pkl")
R["period"] = np.where(R.t < pd.Timestamp("2021-01-01", tz="UTC"), "1 EXT 2016-20", np.where(R.t < pd.Timestamp("2026-04-01", tz="UTC"), "2 IS 2021-26/03", "3 FWD 2026-04→10"))
F = R[R.filled]
def s(g):
    x = g.R; return pd.Series(dict(n=len(x), win=(x > 0).mean(), meanR=x.mean(), ci95=1.96 * x.std() / np.sqrt(max(1, len(x)))))
pd.set_option("display.width", 200)
for nm, g in (("REEL: key level + sweep + MSS + 0.71", F[F.key]), ("REEL + FVG in the leg", F[F.key & F.fvg]),
              ("CONTROL: no key level", F[~F.key]), ("ALL setups", F)):
    print("\n" + nm); print(g.groupby("period").apply(s, include_groups=False).round(3).to_string())
print("\nfill rate (key):", R[R.key].filled.mean().round(3), " median planned RR:", F.rr.median().round(2), " median risk $:", F.risk.median().round(2))
