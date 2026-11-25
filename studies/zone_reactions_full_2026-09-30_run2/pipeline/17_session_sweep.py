"""Stage 17 — idea 8: at a session open, price sweeps the PREVIOUS session's high (low) and then closes
back inside → fade it (short/long). Compared with the opposite read (the sweep continues).
Sessions (chart/CT clock of the rebuilt data): Tokyo 18:00-02:00, London 02:00-07:30, NY 07:30-16:00.
Event: within the first 18 5m bars (90 min) of a session, a bar trades beyond the previous session's
extreme; the first 5m CLOSE back inside within 6 bars triggers. Entry next open; stop beyond the sweep
extreme + 0.25 ATR(5m); target 30 / 40 pts; time stop 48 bars. Stop checked first.
Split by 4H trend: fade AGAINST the 4H trend vs fade WITH it.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
OUT = Path(sys.argv[1]); A = OUT / "analysis"; COST = .3
b = pd.read_csv(OUT / "data" / "bars_5m.csv"); b["time_ct"] = pd.to_datetime(b.time_ct, utc=True).dt.tz_convert("America/Chicago")
o, h, l, c = (b[k].to_numpy(float) for k in ["open", "high", "low", "close"])
atr = pd.Series(b.atr5).ffill().bfill().to_numpy(); seg = b.segment.to_numpy(); tod = b.tod.to_numpy(); n = len(b)
h4 = pd.read_csv(OUT / "data" / "bars_4h.csv")
trend4 = np.full(n, np.nan)
for sg, g in h4.groupby("segment"):
    li = g.last_i.to_numpy().astype(int); tr = g.trend4.to_numpy()
    for j in range(len(li) - 1): trend4[li[j] + 1:li[j + 1] + 1] = tr[j]
def sess(t):
    return 0 if (t >= 18 * 60 or t < 2 * 60) else 1 if t < 7 * 60 + 30 else 2
sid = np.array([sess(t) for t in tod])
# session blocks: new block when session id changes or segment changes
blk = np.zeros(n, int); k = 0
for i in range(1, n):
    if sid[i] != sid[i - 1] or seg[i] != seg[i - 1] or (b.time_ct.iloc[i] - b.time_ct.iloc[i - 1]).total_seconds() > 3600: k += 1
    blk[i] = k
starts = np.r_[0, np.where(np.diff(blk) != 0)[0] + 1]
def sim(d, ei, stop, T):
    e = o[ei]; tgt = e + d * T
    for j in range(ei, min(n, ei + 48)):
        if seg[j] != seg[ei]: return (c[j - 1] - e) * d - COST, "SEG"
        if (l[j] <= stop) if d == 1 else (h[j] >= stop): return (stop - e) * d - COST, "STOP"
        if (h[j] >= tgt) if d == 1 else (l[j] <= tgt): return T - COST, "TARGET"
    j = min(n, ei + 48) - 1; return (c[j] - e) * d - COST, "TIME"
rows = []
for a, bnd in zip(starts[:-1], starts[1:]):
    pass
for q in range(1, len(starts) - 1):
    ps, pe = starts[q - 1], starts[q]; s0, s1 = starts[q], starts[q + 1]
    if seg[ps] != seg[s0]: continue
    PH, PL = h[ps:pe].max(), l[ps:pe].min()
    done = False
    for i in range(s0, min(s1, s0 + 18)):
        for side in (1, -1):          # side 1 = swept the previous HIGH → fade short
            if done: break
            swept = h[i] > PH if side == 1 else l[i] < PL
            if not swept: continue
            ext = h[i] if side == 1 else l[i]
            for j in range(i, min(s1, i + 7, n - 2)):
                ext = max(ext, h[j]) if side == 1 else min(ext, l[j])
                back = c[j] < PH if side == 1 else c[j] > PL
                if back:
                    d = -side
                    stop = ext + .25 * atr[j] if d == -1 else ext - .25 * atr[j]
                    ei = j + 1
                    if abs(o[ei] - stop) < .2 * atr[ei]: break
                    r = dict(time=b.time_ct.iloc[i], session=["Tokyo", "London", "NY"][sid[i]], dir=d, risk=abs(o[ei] - stop),
                             fade_with_trend=(trend4[i] == d) if not np.isnan(trend4[i]) else None)
                    for T in (30, 40):
                        r[f"pnl{T}"], r[f"why{T}"] = sim(d, ei, stop, T)
                    rows.append(r); done = True; break
            if done: break
        if done: break
x = pd.DataFrame(rows); x.to_csv(A / "session_sweep_events.csv", index=False)
days = np.sort(x.time.dt.date.unique()); cut = days[int(len(days) * .6)]; x["split"] = np.where(x.time.dt.date < cut, "DEV", "HOLDOUT")
def s(name, g):
    print(f"{name:40s} n={len(g):4d} hit30={(g.why30=='TARGET').mean():.2f} avg30={g.pnl30.mean():+.2f} | hit40={(g.why40=='TARGET').mean():.2f} avg40={g.pnl40.mean():+.2f} | medRisk={g.risk.median():.1f} | DEV30={g[g.split=='DEV'].pnl30.mean():+.2f} HO30={g[g.split=='HOLDOUT'].pnl30.mean():+.2f}")
s("ALL session-open sweep fades", x)
s("fade AGAINST 4H trend (idea 8 live case)", x[x.fade_with_trend == False])
s("fade WITH 4H trend", x[x.fade_with_trend == True])
for ss in ("Tokyo", "London", "NY"): s(f"  {ss}", x[x.session == ss])
