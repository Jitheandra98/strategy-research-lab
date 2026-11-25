"""Stage 23: forward test (no hindsight) of the lead from stage 22: SWEEP + RECLAIM on 15m.
LONG: a 15m low goes below the lowest low of the previous 2-24 h (bars i-96..i-8) by >= 0.05 ATR4, and within the next
3 bars a 15m CLOSE comes back above that old low -> enter at that close. Stop = lowest low since the sweep - 0.05 ATR4.
Targets: 2R and 3R, and 'swing' = the highest high of the previous 24 h (the other side of the range).
Time stop 3 days (288 bars). Cost 0.30 pt. SHORT mirrored. One trade per sweep; no new sweep trade while one is open
in the same direction. Filters reported separately: at a 4H box (sweep extreme within 0.15 ATR4 of a box level),
with 4H EMA trend, session.
usage: 23_sweep_trade.py <build_dir> <tag>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

B, TAG = Path(sys.argv[1]), sys.argv[2]
b = pd.read_pickle(B / "bars15.pkl"); h4 = pd.read_pickle(B / "bars4h.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl")
h4 = h4.copy(); h4["avail"] = pd.to_datetime(h4.avail)
T = b.index; n = len(T); H, L, C = (b[k].to_numpy() for k in ["high", "low", "close"])
ctx = pd.merge_asof(pd.DataFrame({"t": T}), h4[["avail", "atr", "trend"]].rename(columns={"avail": "t"}).sort_values("t"),
                    on="t", direction="backward")
A4, TR4 = ctx.atr.to_numpy(), ctx.trend.to_numpy()
zav = z4.born_time.map(lambda x: h4.avail.get(x, pd.NaT)).values
zend = np.where(z4.end_time.notna(), (z4.end_time + pd.Timedelta(hours=4)).values, np.datetime64("2100-01-01"))
ZT, ZB = z4.top.to_numpy(), z4.bot.to_numpy()
COST, TMAX = 0.30, 288
rows = []; busy = {1: -1, -1: -1}
for i in range(110, n - TMAX - 5):
    a4 = A4[i]
    if np.isnan(a4): continue
    for d in (1, -1):
        prior = L[i - 96:i - 8].min() if d == 1 else H[i - 96:i - 8].max()
        took = (L[i] < prior - 0.05 * a4) if d == 1 else (H[i] > prior + 0.05 * a4)
        if not took: continue
        # first bar of a sweep only (previous bar did not already sweep)
        if (d == 1 and L[i - 1] < prior - 0.05 * a4) or (d == -1 and H[i - 1] > prior + 0.05 * a4): continue
        q = None
        for k in range(i, i + 4):
            if (d == 1 and C[k] > prior) or (d == -1 and C[k] < prior): q = k; break
        if q is None or q <= busy[d]: continue
        ext = L[i:q + 1].min() if d == 1 else H[i:q + 1].max()
        entry = C[q]; stop = ext - d * 0.05 * a4; risk = d * (entry - stop)
        if risk <= 0: continue
        far = H[i - 96:i].max() if d == 1 else L[i - 96:i].min()
        t = np.datetime64(T[i].tz_convert(None)); alive = (zav <= t) & (zend > t)
        lv = np.r_[ZT[alive], (ZT[alive] + ZB[alive]) / 2, ZB[alive]]
        at_box = bool(len(lv) and np.min(np.abs(lv - ext)) <= 0.15 * a4)
        res = {}
        seg = slice(q + 1, q + 1 + TMAX)
        for name, tgt in (("2R", entry + d * 2 * risk), ("3R", entry + d * 3 * risk), ("swing", far)):
            if d * (tgt - entry) <= 0: res[f"R_{name}"] = np.nan; continue
            hs = (L[seg] <= stop) if d == 1 else (H[seg] >= stop)
            ht = (H[seg] >= tgt) if d == 1 else (L[seg] <= tgt)
            fs = np.argmax(hs) if hs.any() else TMAX; ft = np.argmax(ht) if ht.any() else TMAX
            if fs == TMAX and ft == TMAX: R = d * (C[q + TMAX] - entry) / risk
            elif fs <= ft: R = -1.0
            else: R = d * (tgt - entry) / risk
            res[f"R_{name}"] = R - COST / risk
        hny = T[q].tz_convert("America/New_York").hour
        rows.append(dict(time=T[q], dir=d, entry=entry, stop=stop, risk=risk, risk_atr4=risk / a4, at_box=at_box,
                         with_trend=int(TR4[q] == d), session="ASIA" if (hny >= 18 or hny < 2) else "LONDON" if hny < 8
                         else "NY_AM" if hny < 12 else "NY_PM", swing_R=d * (far - entry) / risk, **res))
        busy[d] = q + 8
R = pd.DataFrame(rows); R["year"] = R.time.dt.year
R.to_pickle(B / f"sweep_trades_{TAG}.pkl")


def summ(g):
    out = {"n": len(g)}
    for k in ("R_2R", "R_3R", "R_swing"):
        x = g[k].dropna(); out[k] = x.mean(); out[k + "_ci"] = 1.96 * x.std() / np.sqrt(len(x)) if len(x) > 1 else np.nan
    return pd.Series(out)


pd.set_option("display.width", 220)
print("ALL"); print(summ(R).round(3).to_dict())
for f in ("year", "at_box", "with_trend", "session", "dir"):
    print(f); print(R.groupby(f).apply(summ).round(3).to_string())
