"""Stage 18 — live-watch question (10 Jun replay): is the session-open window filter too strict?

Setup (as used in the live plans): with the 4H trend, first pullback (arrival 1) into a 5m zone,
trigger = first 5m CLOSE back outside on the near side (C1_RECLAIM from stage 08), enter next open,
stop = stage-08 stop (beyond the touch extreme + buffer), TP = +30 pts, time stop 48 bars (4h).
Compare entry hour buckets: all hours vs session-open windows (several definitions, chart = CT).
Skip trades whose stop is > 30 pts (rule 7). One position at a time.
Output: analysis/window_test_trades.csv, analysis/window_test_summary.csv (+ print)
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
A = OUT / "analysis"
COST = 0.3
TP = 30.0
MAXB = 48
rng = np.random.default_rng(7)

b = pd.read_csv(OUT / "data" / "bars_5m.csv")
o, h, l, c = (b[k].to_numpy(float) for k in ["open", "high", "low", "close"])
seg = b.segment.to_numpy()
tod = b.tod.to_numpy()
n = len(b)
dates = pd.to_datetime(b.date).dt.date.to_numpy()

ct = pd.read_csv(OUT / "data" / "confirmation_trades.csv")
ct = ct[ct.conf == "C1_RECLAIM"]
ev = pd.read_csv(OUT / "events.csv", usecols=["zone_uid", "i", "zone_tf", "arrival_no", "trend4_aligned", "hour_ct"])
t = ct.merge(ev, left_on=["zone_uid", "event_i"], right_on=["zone_uid", "i"], how="inner")
t = t[(t.zone_tf == "5m") & (t.trend4_aligned == True)].copy()


def sim(d, ei, stop):
    e = o[ei]
    tgt = e + d * TP
    for j in range(ei, min(n, ei + MAXB)):
        if seg[j] != seg[ei]:
            return (c[j - 1] - e) * d - COST, "SEG"
        gap = tod[j] == 17 * 60 and j > ei
        if (l[j] <= stop) if d == 1 else (h[j] >= stop):
            px = (min(stop, o[j]) if d == 1 else max(stop, o[j])) if gap else stop
            return (px - e) * d - COST, "STOP"
        if (h[j] >= tgt) if d == 1 else (l[j] <= tgt):
            return TP - COST, "TARGET"
    j = min(n, ei + MAXB) - 1
    return (c[j] - e) * d - COST, "TIME"


rows = []
for r in t.itertuples():
    ei = int(r.entry_i)
    if ei >= n or seg[ei] != seg[int(r.conf_i)]:
        continue
    d = int(r.tdir)
    risk = (o[ei] - r.stop) * d
    if risk <= 0 or risk > TP:
        continue
    pnl, why = sim(d, ei, r.stop)
    rows.append(dict(ei=ei, date=dates[ei], tod=int(tod[ei]), hour=int(tod[ei]) // 60, dir=d,
                     arrival=int(r.arrival_no), risk=risk, pnl=pnl, why=why))
T = pd.DataFrame(rows).sort_values("ei")
days = np.sort(np.unique(dates))
cut = days[int(len(days) * 0.6)]
T["split"] = np.where(T.date < cut, "DEV", "HOLDOUT")


def one_at_a_time(x):
    keep, busy = [], -1
    for r in x.itertuples():
        if r.ei > busy:
            keep.append(r.Index)
            busy = r.ei + MAXB  # conservative: assume busy for the full time stop
    return x.loc[keep]


# windows in CT minutes-of-day (chart time). TV Market Sessions boxes seen on chart:
# Tokyo ~19:00, London ~02:00, NY ~08:00 (CT, summer). Also test the "ET-clock" version.
WIN = {
    "boxes_2h (19-21, 02-04, 08-10 CT)": [(19 * 60, 21 * 60), (2 * 60, 4 * 60), (8 * 60, 10 * 60)],
    "et_clock_2h (17-19, 01-03, 0730-0930 CT)": [(17 * 60, 19 * 60), (1 * 60, 3 * 60), (7 * 60 + 30, 9 * 60 + 30)],
    "nyopen only (0730-1000 CT)": [(7 * 60 + 30, 10 * 60)],
    "london only (01-04 CT)": [(1 * 60, 4 * 60)],
    "tokyo only (17-21 CT)": [(17 * 60, 21 * 60)],
}


def inwin(x, wins):
    m = np.zeros(len(x), bool)
    for a, z in wins:
        m |= (x.tod >= a) & (x.tod < z)
    return m


def boot(x):
    if len(x) < 5:
        return np.nan, np.nan
    g = x.groupby("date").pnl.sum()
    s = [rng.choice(g.values, len(g)).sum() / len(x) for _ in range(2000)]
    return np.percentile(s, 5), np.percentile(s, 95)


out = []
def summ(name, x):
    x1 = one_at_a_time(x)
    for lab, y in (("all signals", x), ("1 position", x1)):
        lo, hi = boot(y)
        out.append(dict(set=name, mode=lab, n=len(y), hit=(y.why == "TARGET").mean(), avg_pts=y.pnl.mean(),
                        ci5=lo, ci95=hi, dev=y[y.split == "DEV"].pnl.mean(), ho=y[y.split == "HOLDOUT"].pnl.mean(),
                        med_risk=y.risk.median(), pts_per_day=y.pnl.sum() / len(days)))


summ("ANY TIME", T)
summ("ANY TIME, arrival 1", T[T.arrival == 1])
for k, w in WIN.items():
    m = inwin(T, w)
    summ("IN " + k, T[m])
    summ("OUT of " + k, T[~m])
S = pd.DataFrame(out)
T.to_csv(A / "window_test_trades.csv", index=False)
S.to_csv(A / "window_test_summary.csv", index=False)
hr = T.groupby("hour").agg(n=("pnl", "size"), hit=("why", lambda s: (s == "TARGET").mean()), avg=("pnl", "mean"))
hr.to_csv(A / "window_test_by_hour.csv")
pd.set_option("display.width", 250)
print(S.round(2).to_string(index=False))
print(hr.round(2).to_string())

# ---- context filter: only within 24h (288 bars) AFTER a 4H setup in the same direction ----
bt = pd.to_datetime(b.time_ct, utc=True)
rc = pd.read_csv(A / "h4_reclaim_events.csv")
rc = rc[rc.with_trend == True]
fl = pd.read_csv(A / "h4_flip_events.csv")
fl = fl[fl.wick_through == False]
fl_t = pd.to_datetime(fl.time, utc=True) + pd.Timedelta(hours=4)  # known at the 4H close
fl_i = np.searchsorted(bt.values, fl_t.values)
ctx = [("reclaim", int(e), int(d)) for e, d in zip(rc.ei, rc.dir)] + \
      [("flip", int(e), int(d)) for e, d in zip(fl_i, fl.dir)]
lab = np.array([""] * len(T), dtype=object)
for name, s, d in ctx:
    m = (T.ei.values >= s) & (T.ei.values < s + 288) & (T.dir.values == d)
    lab[m & (lab == "")] = name
T["ctx"] = lab
out.clear()
summ("CTX any (24h after with-trend 4H reclaim or flip)", T[T.ctx != ""])
summ("CTX reclaim", T[T.ctx == "reclaim"])
summ("CTX flip", T[T.ctx == "flip"])
summ("NO CTX", T[T.ctx == ""])
for k in ["boxes_2h (19-21, 02-04, 08-10 CT)", "nyopen only (0730-1000 CT)"]:
    m = inwin(T, WIN[k]) & (T.ctx != "")
    summ("CTX + IN " + k, T[m])
    m = ~inwin(T, WIN[k]) & (T.ctx != "")
    summ("CTX + OUT of " + k, T[m])
S2 = pd.DataFrame(out)
S2.to_csv(A / "window_test_ctx_summary.csv", index=False)
print("\n--- with the 4H setup context ---")
print(S2.round(2).to_string(index=False))
