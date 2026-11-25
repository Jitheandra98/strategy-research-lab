"""Stage 21: BOX-TO-BOX v2 — the owner's corrections after reading the study book (2026-10-07):
 1 4H context: a CLOSED 4H candle touched a 4H box and REJECTED it (BUY: low <= top + tol and close > top;
   SELL: high >= bot - tol and close < bot). Boxes = every 4H-pane STATION2 box alive (OB/FVG/IFVG/breaker).
 2 Wait for the retrace: within the next 24 h, price comes back to that box edge (3m low <= top + tol for BUY).
   If a 4H candle CLOSES back inside/through the box before that (acceptance), the setup is cancelled.
 3 3m confirmation after the retrace touch, within 2 h: 3m close above the last 3m swing high formed after the touch
   (BUY; mirrored for SELL).
 4 Room: target = the nearest opposing 4H box edge beyond entry (BUY: the bottom of the next box above);
   trade only if target distance >= max($20, 2R).
 5 Stop: variant A = lowest low since the retrace touch - 0.05 ATR4 (tight); variant B = box bottom - 0.05 ATR4 (wide).
 Time stop 2 days, cost 0.30 pt. One setup per box per rejection candle.
usage: 21_box2box_v2.py <build_dir> <work_dir> <minute_pickle> <tag> [placebo_draws]
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

B, W, M1, TAG = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
NPLC = int(sys.argv[5]) if len(sys.argv) > 5 else 3
COST, TOLK, ROOM_PTS, ROOM_R, WAIT_H, CONF, TMAX = 0.30, 0.05, 20.0, 2.0, 24, 40, 960
m1 = pd.read_pickle(W / M1)[["open", "high", "low", "close"]]
h4 = pd.read_pickle(B / "bars4h.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl")
m3 = m1.resample("3min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
m3 = m3[(m3.index >= h4.index[150]) & (m3.index <= h4.index[-1] + pd.Timedelta(hours=4))]
T = m3.index.values; n = len(T)
H3, L3, C3 = (m3[k].to_numpy() for k in ["high", "low", "close"])
swh = np.zeros(n, bool); swl = np.zeros(n, bool)
swh[2:-2] = (H3[2:-2] > H3[1:-3]) & (H3[2:-2] > H3[:-4]) & (H3[2:-2] > H3[3:-1]) & (H3[2:-2] > H3[4:])
swl[2:-2] = (L3[2:-2] < L3[1:-3]) & (L3[2:-2] < L3[:-4]) & (L3[2:-2] < L3[3:-1]) & (L3[2:-2] < L3[4:])
h4 = h4[h4.atr.notna()].copy(); h4["avail"] = pd.to_datetime(h4.avail)
HO, HH, HL, HC, HA = (h4[k].to_numpy() for k in ["open", "high", "low", "close", "atr"])
HT = h4.index; HAV = h4.avail.values
zav = z4.born_time.map(lambda x: pd.to_datetime(h4.avail.get(x, pd.NaT))).values
zend = np.where(z4.end_time.notna(), (z4.end_time + pd.Timedelta(hours=4)).values, np.datetime64("2100-01-01"))


def run(top, bot):
    rows = []
    for j in range(5, len(h4) - 7):
        a4 = HA[j]; tol = TOLK * a4; t_close = HAV[j]
        alive = (zav <= np.datetime64(HT[j].tz_convert(None))) & (zend > t_close)
        idx = np.where(alive)[0]
        for zi in idx:
            tp, bt = top[zi], bot[zi]
            for d in (1, -1):
                if d == 1 and not (HL[j] <= tp + tol and HC[j] > tp and HL[j] >= bt - 2 * a4): continue
                if d == -1 and not (HH[j] >= bt - tol and HC[j] < bt and HH[j] <= tp + 2 * a4): continue
                edge = tp if d == 1 else bt
                k0 = np.searchsorted(T, t_close); kend = min(n - TMAX - 1, k0 + WAIT_H * 20)
                # acceptance cancel: a later closed 4H candle back inside/through before the retrace
                acc_t = np.datetime64("2100-01-01")
                for jj in range(j + 1, min(len(h4), j + 7)):
                    if (d == 1 and HC[jj] <= tp) or (d == -1 and HC[jj] >= bt):
                        acc_t = HAV[jj]; break
                touch = None
                for k in range(k0, kend):
                    if T[k] >= acc_t: break
                    if (d == 1 and L3[k] <= edge + tol) or (d == -1 and H3[k] >= edge - tol): touch = k; break
                if touch is None: continue
                trig = None; ext = L3[touch] if d == 1 else H3[touch]
                for q in range(touch + 1, min(n - 1, touch + CONF)):
                    ext = min(ext, L3[q]) if d == 1 else max(ext, H3[q])
                    sw = np.where(swh[touch:q - 1])[0] if d == 1 else np.where(swl[touch:q - 1])[0]
                    if len(sw):
                        ref = H3[touch + sw[-1]] if d == 1 else L3[touch + sw[-1]]
                        if (d == 1 and C3[q] > ref) or (d == -1 and C3[q] < ref): trig = q; break
                if trig is None: continue
                entry = C3[trig]
                # room: nearest opposing box edge beyond entry among alive boxes
                if d == 1:
                    opp = bot[idx][(bot[idx] > entry + 0.5) ]
                else:
                    opp = top[idx][(top[idx] < entry - 0.5)]
                if not len(opp): continue
                tgt = opp.min() if d == 1 else opp.max()
                for var, stop in (("A_tight", ext - d * tol), ("B_wide", (bt - tol) if d == 1 else (tp + tol))):
                    risk = d * (entry - stop)
                    if risk <= 0: continue
                    dist = d * (tgt - entry)
                    if dist < max(ROOM_PTS, ROOM_R * risk): continue
                    seg = slice(trig + 1, trig + 1 + TMAX)
                    hs = (L3[seg] <= stop) if d == 1 else (H3[seg] >= stop)
                    ht = (H3[seg] >= tgt) if d == 1 else (L3[seg] <= tgt)
                    fs = np.argmax(hs) if hs.any() else TMAX; ft = np.argmax(ht) if ht.any() else TMAX
                    if fs == TMAX and ft == TMAX: R = d * (C3[trig + TMAX] - entry) / risk; w = 0
                    elif fs <= ft: R, w = -1.0, 0
                    else: R, w = dist / risk, 1
                    rows.append(dict(var=var, time=pd.Timestamp(T[trig], tz="UTC"), rej_4h=HT[j], dir=d, box=zi, edge=edge,
                                     entry=entry, stop=stop, target=tgt, risk=risk, dist=dist, tgt_R=dist / risk,
                                     R=R - COST / risk, win=w))
    df = pd.DataFrame(rows)
    return df.drop_duplicates(["var", "time", "dir"]) if len(df) else df


real = run(z4.top.to_numpy(), z4.bot.to_numpy()); real["src"] = "real"
rng = np.random.default_rng(31)
atr_b = np.interp(z4.born_time.astype("int64"), h4.index.astype("int64"), h4.atr.to_numpy())
pl = []
for k in range(NPLC):
    sh = rng.choice([-1, 1], len(z4)) * rng.uniform(1, 3, len(z4)) * atr_b
    p = run(z4.top.to_numpy() + sh, z4.bot.to_numpy() + sh); p["src"] = "placebo"; pl.append(p)
R = pd.concat([real] + pl); R.to_pickle(W / f"box2box_v2_{TAG}.pkl")
R["year"] = R.time.dt.year
g = R.groupby(["src", "var", "year"]).agg(n=("R", "size"), win=("win", "mean"), avgR=("R", "mean"),
                                         sd=("R", "std"), tgtR=("tgt_R", "median"), dist=("dist", "median")).reset_index()
g["ci"] = 1.96 * g.sd / np.sqrt(g.n); g.loc[g.src == "placebo", "n"] /= NPLC
a = R.groupby(["src", "var"]).agg(n=("R", "size"), win=("win", "mean"), avgR=("R", "mean"), sd=("R", "std"),
                                  tgtR=("tgt_R", "median"), dist=("dist", "median")).reset_index()
a["ci"] = 1.96 * a.sd / np.sqrt(a.n); a.loc[a.src == "placebo", "n"] /= NPLC; a["year"] = "ALL"
out = pd.concat([g, a]).drop(columns="sd"); out.to_csv(W / f"box2box_v2_{TAG}_summary.csv", index=False)
pd.set_option("display.width", 220)
print(out.round(3).to_string())
