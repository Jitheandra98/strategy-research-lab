"""Reopen gap on MGC continuous futures (trade prices), 1h bars from his TradingView, Jan 2025 - Nov 2026.
gap = 18:00 NY bar OPEN vs 16:00 NY bar CLOSE (the last trade before the 17:00 break). Roll days (continuous-contract
jumps, |gap| > 40 bp) removed. Spot over the same dates for comparison. Trade = buy 16:59, sell at the reopen."""
import json, numpy as np, pandas as pd
b = np.array(json.load(open("mgc1_60m.json")))
f = pd.DataFrame(b[:, 1:], columns="o h l c".split(), index=pd.to_datetime(b[:, 0], unit="s").tz_localize("UTC").tz_convert("America/New_York"))
rows = []
for d, g in f.groupby(f.index.date):
    pre = g[g.index.hour == 16]
    if pre.empty: continue
    nxt = f[(f.index > pre.index[-1]) & (f.index <= pre.index[-1] + pd.Timedelta(hours=4))]
    reo = nxt[nxt.index.hour == 18]
    if reo.empty: continue
    p0, p1, p2 = pre.c.iloc[-1], reo.o.iloc[0], reo.c.iloc[0]
    rows.append(dict(day=pd.Timestamp(d), price=p0, gap_bp=(p1 / p0 - 1) * 1e4, gap_pts=p1 - p0, hour1_bp=(p2 / p1 - 1) * 1e4))
r = pd.DataFrame(rows)
rolls = r[r.gap_bp.abs() > 40]; r = r[r.gap_bp.abs() <= 40]
print("removed as roll days:", list(rolls.day.dt.date.astype(str)), "\n")
def show(lab, x, col):
    v = x[col]; print(f"{lab}: n={len(v)}  mean {v.mean():.2f}  median {v.median():.2f}  t={v.mean()/(v.std()/np.sqrt(len(v))):.2f}  up {(v>0).mean()*100:.0f} %")
show("MGC gap (bp)", r, "gap_bp"); show("MGC gap (points)", r, "gap_pts"); show("MGC first hour after reopen (bp)", r, "hour1_bp")
for y in sorted(r.day.dt.year.unique()): show(f"  MGC gap bp {y}", r[r.day.dt.year == y], "gap_bp")
COST = 0.3
net = r.gap_pts - COST
print(f"\nAs a trade (buy 16:59, sell at reopen, cost {COST} pt): avg {net.mean():.2f} pt, win {(net>0).mean()*100:.0f} %, PF {net[net>0].sum()/-net[net<0].sum():.2f}, worst {net.min():.1f} pt, best {net.max():.1f} pt")
for c in [0.5, 0.8]:
    n2 = r.gap_pts - c; print(f"  if real cost is {c} pt: avg {n2.mean():.2f} pt, PF {n2[n2>0].sum()/-n2[n2<0].sum():.2f}")
r.to_csv("reopen_fut.csv", index=False)
