"""Stage 18: owner's idea - at a 4H zone, take the BIAS from a lower-timeframe (5m / 3m) confirmation.
Pre-registered 2026-10-07 before any result was looked at. Bull case (bear mirrored), rd = reaction direction.

Event   : a 4H-pane zone interaction from events.pkl (ARRIVAL or FLIP), touch = start of the 15m arrival bar.
Window  : 3 hours of LTF bars from the touch. Cancel if price trades > 1.0 ATR15 beyond the far edge first.
C1 CHoCH : LTF close above the most recent LTF swing high (fractal 2/2) that formed before the close, after touch
C2 SWEEP : LTF low < lowest low of the prior 12 LTF bars (taken after touch), then a close back above that prior
           low within 3 bars
C3 DISP  : LTF bull FVG (low[k] > high[k-2]) whose middle bar range >= 1.5 x LTF ATR(14)
C5 DOUBLE: (added 2026-10-07 at owner's request, before any C5 result) double bottom after touch: two LTF swing
           lows (fractal 2/2) >= 3 bars apart, second within 0.15 ATR15 of the first, then a close above the
           highest high between them (neckline)
C4 ENGULF: bullish engulfing LTF bar (close > prior open and open <= prior close, body > prior body) closing above
           the zone's near edge after price traded inside the zone
Entry = confirmation close. Stop = lowest low since touch - 0.1 ATR15 (stop must be below entry).
Targets: 1R and 2R; 2-day time stop; cost 0.30 pt. Same-bar stop+target = stop.
usage: 18_ltf_confirm.py <build_dir> <work_dir> <minute_pickle> <tag>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

B, W, M1, TAG = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
COST = 0.30
m1 = pd.read_pickle(W / M1)[["open", "high", "low", "close"]]


def resample(m, tf):
    r = m.resample(f"{tf}min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    tr = np.maximum(r.high - r.low, np.maximum(abs(r.high - r.close.shift()), abs(r.low - r.close.shift())))
    r["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    return r


def run(ev, ltf, tf):
    t = ltf.index.values; O, H, L, C, A = (ltf[k].to_numpy() for k in ["open", "high", "low", "close", "atr"])
    n = len(t); win = int(180 / tf); tmax = int(2 * 24 * 60 / tf)
    # fractal swing highs/lows (2 bars each side), known 2 bars later
    sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    sh[2:-2] = (H[2:-2] > H[1:-3]) & (H[2:-2] > H[:-4]) & (H[2:-2] > H[3:-1]) & (H[2:-2] > H[4:])
    sl[2:-2] = (L[2:-2] < L[1:-3]) & (L[2:-2] < L[:-4]) & (L[2:-2] < L[3:-1]) & (L[2:-2] < L[4:])
    rows = []
    for e in ev.itertuples():
        i0 = np.searchsorted(t, np.datetime64(e.time_utc.tz_convert(None)))
        if i0 < 30 or i0 + win + tmax >= n: continue
        d, top, bot, a15 = e.rd, e.top, e.bot, e.atr
        # orient prices so the logic is written once for the bull case
        s = 1 if d == 1 else -1
        oH, oL = (H, L) if d == 1 else (-L, -H)
        oO, oC = s * O, s * C
        near = top if d == 1 else -bot
        far = bot if d == 1 else -top
        cancel = far - 1.0 * a15
        found = {}
        ext = np.inf
        for k in range(i0, i0 + win):
            ext = min(ext, oL[k])
            if ext < cancel: break
            # C1 CHoCH: close above the latest swing high confirmed by k (swing at j <= k-2) that is after i0-12
            if "C1" not in found:
                js = np.where(sh[max(i0 - 24, 0):k - 1])[0] if d == 1 else np.where(sl[max(i0 - 24, 0):k - 1])[0]
                if len(js):
                    j = max(i0 - 24, 0) + js[-1]
                    if k > i0 and oC[k] > oH[j]: found["C1"] = k
            if "C2" not in found and k >= i0:
                prior = oL[k - 12:k].min()
                if oL[k] < prior:
                    for q in range(k, min(k + 3, i0 + win)):
                        if oC[q] > prior: found["C2"] = q; break
            if "C3" not in found and k >= i0 + 2:
                if oL[k] > oH[k - 2] and (H[k - 1] - L[k - 1]) >= 1.5 * A[k - 1]: found["C3"] = k
            if "C4" not in found and k > i0:
                if (oC[k] > oO[k - 1] and oO[k] <= oC[k - 1] and abs(oC[k] - oO[k]) > abs(oC[k - 1] - oO[k - 1])
                        and oC[k] > near and ext <= near):
                    found["C4"] = k
            if "C5" not in found and k > i0 + 6:
                lows = [j for j in range(i0, k - 1) if (sl[j] if d == 1 else sh[j])]
                for a_ in range(len(lows) - 1, 0, -1):
                    j2 = lows[a_]; j1 = lows[a_ - 1]
                    if j2 - j1 >= 3 and abs(oL[j2] - oL[j1]) <= 0.15 * a15:
                        neck = oH[j1:j2 + 1].max()
                        if oC[k] > neck and oC[k - 1] <= neck: found["C5"] = k
                        break
        for c, k in found.items():
            entry = oC[k]; stop = oL[i0:k + 1].min() - 0.1 * a15; risk = entry - stop
            if risk <= 0: continue
            res = {}
            for tg in (1, 2):
                tgt = entry + tg * risk
                hs = oL[k + 1:k + 1 + tmax] <= stop; ht = oH[k + 1:k + 1 + tmax] >= tgt
                fs = np.argmax(hs) if hs.any() else tmax; ft = np.argmax(ht) if ht.any() else tmax
                if fs == tmax and ft == tmax:
                    R = (oC[min(n - 1, k + tmax)] - entry) / risk; w = 0
                elif fs <= ft: R, w = -1.0, 0
                else: R, w = float(tg), 1
                res[f"R{tg}"] = R - COST / risk; res[f"w{tg}"] = w
            rows.append(dict(tf=tf, conf=c, event_id=e.Index, video=e.video, split=e.split, interaction=e.interaction,
                             trend4_with=e.trend4_with, struct4_with=e.struct4_with, time_utc=e.time_utc,
                             mins_to_conf=(k - i0) * tf, risk_atr=risk / a15, **res))
    return pd.DataFrame(rows)


out = []
for src in ("real", "placebo"):
    f = B / ("events.pkl" if src == "real" else "events_placebo.pkl")
    if not f.exists(): continue
    ev = pd.read_pickle(f)
    ev = ev[ev.universe == "Z4"].copy()
    ev["split"] = np.where(ev.video.isin([1, 2]), "V1+V2", np.where(ev.video == 3, "V3", "OFF-VIDEO"))
    for tf in (5, 3):
        r = run(ev, resample(m1, tf), tf); r["src"] = src; out.append(r)
        print(src, tf, len(r), flush=True)
R = pd.concat(out); R.to_pickle(W / f"ltf_confirm_{TAG}.pkl")


def summ(g):
    return pd.Series(dict(n=len(g), win2=g.w2.mean(), R2=g.R2.mean(), ci2=1.96 * g.R2.std() / np.sqrt(len(g)),
                          win1=g.w1.mean(), R1=g.R1.mean(), ci1=1.96 * g.R1.std() / np.sqrt(len(g))))


S = R.groupby(["src", "tf", "conf", "split"]).apply(summ).reset_index()
S2 = R[R.trend4_with == 1].groupby(["src", "tf", "conf", "split"]).apply(summ).reset_index(); S2["filter"] = "4H trend with"
S["filter"] = "none"
ALL = pd.concat([S, S2]); ALL.to_csv(W / f"ltf_confirm_{TAG}_summary.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
print(ALL.pivot_table(index=["filter", "tf", "conf", "split"], columns="src", values=["n", "R2", "ci2", "R1"]).round(3).to_string())
