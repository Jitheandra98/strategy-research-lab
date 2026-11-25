"""Stage 19: "BOX-TO-BOX 3m v1" — the strategy written from the live replay watch (live_watch/WATCH_LOG.md, setups #1-#7,
2026-09-30/10-01). Rules frozen 2026-10-07 ~21:10 local, BEFORE any historical test.

Levels : every 4H-pane STATION2 box alive on the chart (any kind/state until archived/evicted) -> top, CE (midline), bottom.
Arrival: SHORT side - a 3m high reaches L - tol after the prior 20 3m bars (1 h) all stayed below L - tol (tol = 0.05 ATR4).
         LONG side mirrored. Several levels hit on the same bar/direction count once (the first level hit).
Trigger: within 40 3m bars (2 h) after the arrival: the 3m closes below the most recent 3m swing low (fractal 2/2) that formed
         after the arrival (SHORT; mirrored for LONG). Cancel if a 3m close goes beyond L + 0.5 ATR4 first (accepted).
Entry  : the trigger close.  Stop: extreme since the arrival + 0.05 ATR4.
Target : the nearest 4H level (any box top/CE/bottom alive) in the trade direction that is >= 1R from entry; if none <= 4R
         away, 2R. Time stop 160 bars (8 h). Cost 0.30 pt per trade. Same-bar stop+target = stop.
usage: 19_box2box.py <build_dir> <work_dir> <minute_pickle> <tag> [placebo_draws]
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

B, W, M1, TAG = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
NPLC = int(sys.argv[5]) if len(sys.argv) > 5 else 5
COST, TOLK, ACCK, WIN, LOOKB, TMAX = 0.30, 0.05, 0.5, 40, 20, 160
m1 = pd.read_pickle(W / M1)[["open", "high", "low", "close"]]
m3 = m1.resample("3min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
h4 = pd.read_pickle(B / "bars4h.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl")
m3 = m3[(m3.index >= h4.index[150]) & (m3.index <= h4.index[-1] + pd.Timedelta(hours=4))]
T = m3.index.values; n = len(T)
O, H, L, C = (m3[k].to_numpy() for k in ["open", "high", "low", "close"])
h4a = h4.copy(); h4a["avail"] = pd.to_datetime(h4a.avail)
A4 = pd.merge_asof(pd.DataFrame({"t": m3.index}), h4a[["avail", "atr"]].rename(columns={"avail": "t"}).sort_values("t"),
                   on="t", direction="backward").atr.to_numpy()
TR4 = pd.merge_asof(pd.DataFrame({"t": m3.index}), h4a[["avail", "trend"]].rename(columns={"avail": "t"}).sort_values("t"),
                    on="t", direction="backward").trend.to_numpy()
pmax = pd.Series(H).shift(1).rolling(LOOKB).max().to_numpy()
pmin = pd.Series(L).shift(1).rolling(LOOKB).min().to_numpy()
swl = np.zeros(n, bool); swh = np.zeros(n, bool)
swh[2:-2] = (H[2:-2] > H[1:-3]) & (H[2:-2] > H[:-4]) & (H[2:-2] > H[3:-1]) & (H[2:-2] > H[4:])
swl[2:-2] = (L[2:-2] < L[1:-3]) & (L[2:-2] < L[:-4]) & (L[2:-2] < L[3:-1]) & (L[2:-2] < L[4:])


def zone_windows(top, bot):
    av = z4.born_time.map(lambda x: h4a.avail.get(x, pd.NaT))
    end = (z4.end_time + pd.Timedelta(hours=4)).where(z4.end_time.notna(), pd.Timestamp(T[-1], tz="UTC"))
    i0 = np.searchsorted(T, av.dt.tz_convert(None).values.astype("datetime64[ns]"))
    i1 = np.searchsorted(T, end.dt.tz_convert(None).values.astype("datetime64[ns]"))
    return i0, i1


def levels_alive(i, top, bot, i0, i1):
    m = (i0 <= i) & (i1 > i)
    return np.r_[top[m], (top[m] + bot[m]) / 2, bot[m]]


def run(top, bot):
    i0, i1 = zone_windows(top, bot)
    ok = ~np.isnan(i0.astype(float))
    arrivals = {}
    for zi in range(len(top)):
        a, b = int(i0[zi]), int(min(i1[zi], n - 1))
        if b - a < 5 or a <= LOOKB: continue
        for lv in (top[zi], (top[zi] + bot[zi]) / 2, bot[zi]):
            tol = TOLK * A4[a:b]
            hit_s = np.where((H[a:b] >= lv - tol) & (pmax[a:b] < lv - tol))[0] + a
            hit_l = np.where((L[a:b] <= lv + tol) & (pmin[a:b] > lv + tol))[0] + a
            kind = "top" if lv == top[zi] else ("bot" if lv == bot[zi] else "ce")
            for k in hit_s: arrivals.setdefault((k, -1), (lv, kind, int(z4.dir.iloc[zi])))
            for k in hit_l: arrivals.setdefault((k, 1), (lv, kind, int(z4.dir.iloc[zi])))
    rows = []
    for (k, d), (lv, lkind, zdir) in sorted(arrivals.items()):
        if np.isnan(A4[k]) or k + WIN + TMAX >= n: continue
        a4 = A4[k]; ext = H[k] if d == -1 else L[k]; trig = None
        for q in range(k + 1, k + WIN):
            ext = max(ext, H[q]) if d == -1 else min(ext, L[q])
            if (d == -1 and C[q] > lv + ACCK * a4) or (d == 1 and C[q] < lv - ACCK * a4): break
            sw = np.where(swl[k:q - 1])[0] if d == -1 else np.where(swh[k:q - 1])[0]
            if len(sw):
                ref = L[k + sw[-1]] if d == -1 else H[k + sw[-1]]
                if (d == -1 and C[q] < ref) or (d == 1 and C[q] > ref): trig = q; break
        if trig is None: continue
        entry = C[trig]; stop = ext + TOLK * a4 if d == -1 else ext - TOLK * a4
        risk = abs(stop - entry)
        if risk <= 0: continue
        lvls = levels_alive(trig, top, bot, i0, i1)
        cand = (entry - lvls) if d == -1 else (lvls - entry)
        cand = cand[(cand >= risk) & (cand <= 4 * risk)]
        tdist = cand.min() if len(cand) else 2 * risk
        tgt = entry - tdist if d == -1 else entry + tdist
        seg = slice(trig + 1, trig + 1 + TMAX)
        hs = (H[seg] >= stop) if d == -1 else (L[seg] <= stop)
        ht = (L[seg] <= tgt) if d == -1 else (H[seg] >= tgt)
        fs = np.argmax(hs) if hs.any() else TMAX; ft = np.argmax(ht) if ht.any() else TMAX
        if fs == TMAX and ft == TMAX: R = d * (C[trig + TMAX] - entry) / risk; w = 0
        elif fs <= ft: R, w = -1.0, 0
        else: R, w = tdist / risk, 1
        rows.append(dict(lkind=lkind, zone_dir=zdir, trend4=TR4[trig], time=pd.Timestamp(T[k], tz="UTC"), trig_time=pd.Timestamp(T[trig], tz="UTC"), dir=d, level=lv,
                         entry=entry, stop=stop, target=tgt, risk=risk, risk_atr4=risk / a4, tgt_R=tdist / risk,
                         R=R - COST / risk, win=w))
    return pd.DataFrame(rows)


real = run(z4.top.to_numpy(), z4.bot.to_numpy()); real["src"] = "real"
rng = np.random.default_rng(21)
atr_b = np.interp(z4.born_time.astype("int64"), h4.index.astype("int64"), h4.atr.ffill().bfill().to_numpy())
plc = []
for k in range(NPLC):
    sh = rng.choice([-1, 1], len(z4)) * rng.uniform(1, 3, len(z4)) * atr_b
    p = run(z4.top.to_numpy() + sh, z4.bot.to_numpy() + sh); p["src"] = "placebo"; p["draw"] = k; plc.append(p)
R = pd.concat([real] + plc); R.to_pickle(W / f"box2box_{TAG}.pkl")
R["year"] = R.time.dt.year


def summ(g):
    se = g.R.std() / np.sqrt(len(g)) if len(g) > 1 else np.nan
    return pd.Series(dict(n=len(g), win=g.win.mean(), avgR=g.R.mean(), ci=1.96 * se, medTgtR=g.tgt_R.median(),
                          totalR=g.R.sum()))


S = R.groupby(["src", "year"]).apply(summ).reset_index()
S.loc[S.src == "placebo", ["n", "totalR"]] /= NPLC
allp = R.groupby("src").apply(summ).reset_index(); allp["year"] = "ALL"
allp.loc[allp.src == "placebo", ["n", "totalR"]] /= NPLC
out = pd.concat([S, allp]); out.to_csv(W / f"box2box_{TAG}_summary.csv", index=False)
pd.set_option("display.width", 200)
print(out.pivot_table(index="year", columns="src", values=["n", "win", "avgR", "ci"]).round(3).to_string())
