"""Stage 14 — the user's 4H rule: a 4H candle wicks INTO a 4H zone and CLOSES BACK outside it
("touches the zone and claims back"). What happens over the next day?

Definitions (fixed before looking):
  zone    : 4H-engine zones (STATION2 FVG/OB on 4H bars), usable from the 4H bar after birth,
            intact = no 4H CLOSE beyond its far edge yet.
  reclaim : demand zone — 4H low <= top, 4H close > top, previous 4H low > top (came from above)
            supply zone — 4H high >= bot, 4H close < bot, previous 4H high < bot
            depth: 'edge' (wick stayed in the zone) or 'sweep' (wick went past the far edge)
  trade   : enter at the open of the next 4H bar (first 5m bar after the reclaim close)
            stop  = beyond the reclaim candle's wick extreme + 0.1 x ATR(4H)
            target= +30 / +40 / +50 pts ; time limit 6 x 4H bars (24h); stop checked first on 5m bars
  baseline: every other 4H bar, same direction, same stop distance, same targets.
Output: analysis/h4_reclaim_events.csv, analysis/h4_reclaim_summary.csv (+ print)
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
A = OUT / "analysis"
COST = 0.3
rng = np.random.default_rng(3)
b = pd.read_csv(OUT / "data" / "bars_5m.csv")
o, h, l, c = (b[k].to_numpy(float) for k in ["open", "high", "low", "close"])
seg5 = b.segment.to_numpy()
tod = b.tod.to_numpy()
n5 = len(b)
h4 = pd.read_csv(OUT / "data" / "bars_4h.csv")
h4["time_ct"] = pd.to_datetime(h4.time_ct, utc=True).dt.tz_convert("America/Chicago")
z = pd.read_csv(OUT / "zones.csv")
z = z[z.tf == "4h"].copy()
days = np.sort(h4.time_ct.dt.date.unique())
cut = days[int(len(days) * 0.6)]


def sim(d, ei, stop, tgt_pts, max_bars):
    e = o[ei]
    tgt = e + d * tgt_pts
    mfe = 0.0
    for j in range(ei, min(n5, ei + max_bars)):
        if seg5[j] != seg5[ei]:
            return (c[j - 1] - e) * d - COST, "SEG", mfe
        gap = tod[j] == 17 * 60 and j > ei
        if (l[j] <= stop) if d == 1 else (h[j] >= stop):
            px = (min(stop, o[j]) if d == 1 else max(stop, o[j])) if gap else stop
            return (px - e) * d - COST, "STOP", mfe
        if (h[j] >= tgt) if d == 1 else (l[j] <= tgt):
            return tgt_pts - COST, "TARGET", max(mfe, tgt_pts)
        mfe = max(mfe, (h[j] - e) if d == 1 else (e - l[j]))
    j = min(n5, ei + max_bars) - 1
    return (c[j] - e) * d - COST, "TIME", mfe


def mfe_mae(d, ei, max_bars):
    j1 = min(n5, ei + max_bars)
    s = seg5[ei]
    idx = np.arange(ei, j1)
    idx = idx[seg5[idx] == s]
    if len(idx) == 0:
        return np.nan, np.nan
    e = o[ei]
    return ((h[idx].max() - e) if d == 1 else (e - l[idx].min()),
            (e - l[idx].min()) if d == 1 else (h[idx].max() - e))


events = []
for sg, g in h4.groupby("segment"):
    g = g.reset_index()
    zs = z[z.segment == sg]
    live = []
    for k in range(len(g)):
        r = g.iloc[k]
        # zones born at 4H bar index < k become usable at k
        for zr in zs[zs.born_bar == k - 1].itertuples():
            live.append(dict(top=zr.top, bot=zr.bot, dir=int(zr.dir), kind=zr.kind, arrivals=0, uid=zr.zone_uid))
        if k == 0:
            continue
        p = g.iloc[k - 1]
        atr4 = r.atr4 if not np.isnan(r.atr4) else np.nan
        for zz in live:
            if zz.get("broken"):
                continue
            d = zz["dir"]
            if d == 1:
                arrived = r.low <= zz["top"] and p.low > zz["top"]
                reclaim = arrived and r.close > zz["top"]
                depth = "sweep" if r.low < zz["bot"] else "edge"
                ext = r.low
            else:
                arrived = r.high >= zz["bot"] and p.high < zz["bot"]
                reclaim = arrived and r.close < zz["bot"]
                depth = "sweep" if r.high > zz["top"] else "edge"
                ext = r.high
            if arrived:
                zz["arrivals"] += 1
            if reclaim and not np.isnan(atr4):
                ei = int(r.last_i) + 1
                if ei < n5 and seg5[ei] == sg:
                    stop = ext - 0.1 * atr4 if d == 1 else ext + 0.1 * atr4
                    risk = (o[ei] - stop) * d
                    if risk > 0:
                        ev = dict(time_ct=r.time_ct, zone=zz["uid"], kind=zz["kind"], dir=d, arrival=zz["arrivals"],
                                  depth=depth, with_trend=bool(r.trend4 == d) if not np.isnan(r.trend4) else None,
                                  entry=o[ei], stop=stop, risk=risk, ei=ei,
                                  split="DEV" if r.time_ct.date() < cut else "HOLDOUT")
                        for H in (1, 3, 6):
                            mf, ma = mfe_mae(d, ei, 48 * H)
                            ev[f"mfe_{H}x4h"] = mf
                            ev[f"mae_{H}x4h"] = ma
                        for T in (30, 40, 50):
                            pnl, why, _ = sim(d, ei, stop, T, 288)
                            ev[f"pnl_{T}"] = pnl
                            ev[f"why_{T}"] = why
                        events.append(ev)
            # a 4H CLOSE beyond the far edge breaks the zone
            if (d == 1 and r.close < zz["bot"]) or (d == -1 and r.close > zz["top"]):
                zz["broken"] = True
ev = pd.DataFrame(events)
ev.to_csv(A / "h4_reclaim_events.csv", index=False)

# baseline: random 4H bar starts, same direction and risk
base_rows = []
starts = h4.last_i.to_numpy().astype(int) + 1
starts = starts[starts < n5 - 300]
for e in ev.itertuples():
    for s in rng.choice(starts, 20, replace=False):
        stop = o[s] - e.dir * e.risk
        row = dict(dir=e.dir, with_trend=e.with_trend)
        for T in (30, 40, 50):
            row[f"pnl_{T}"], row[f"why_{T}"], _ = sim(e.dir, int(s), stop, T, 288)
        mf, ma = mfe_mae(e.dir, int(s), 288)
        row["mfe_6x4h"] = mf
        base_rows.append(row)
base = pd.DataFrame(base_rows)

rows = []
def summ(name, x, bx):
    r = dict(set=name, n=len(x))
    for T in (30, 40, 50):
        r[f"hit{T}"] = (x[f"why_{T}"] == "TARGET").mean()
        r[f"avg_pts_{T}"] = x[f"pnl_{T}"].mean()
        r[f"base_hit{T}"] = (bx[f"why_{T}"] == "TARGET").mean() if len(bx) else np.nan
        r[f"base_avg_{T}"] = bx[f"pnl_{T}"].mean() if len(bx) else np.nan
    r["median_mfe_24h"] = x["mfe_6x4h"].median()
    r["p_mfe_ge40_24h"] = (x["mfe_6x4h"] >= 40).mean()
    r["base_p_mfe_ge40_24h"] = (bx["mfe_6x4h"] >= 40).mean() if len(bx) else np.nan
    r["median_risk"] = x.risk.median()
    r["dev_avg40"] = x[x.split == "DEV"].pnl_40.mean()
    r["ho_avg40"] = x[x.split == "HOLDOUT"].pnl_40.mean()
    rows.append(r)

summ("ALL 4H reclaims", ev, base)
summ("with 4H trend", ev[ev.with_trend == True], base[base.with_trend == True])
summ("against 4H trend", ev[ev.with_trend == False], base[base.with_trend == False])
summ("with trend, edge (wick stayed in zone)", ev[(ev.with_trend == True) & (ev.depth == "edge")], base[base.with_trend == True])
summ("with trend, sweep (wick past far edge)", ev[(ev.with_trend == True) & (ev.depth == "sweep")], base[base.with_trend == True])
summ("with trend, 1st arrival", ev[(ev.with_trend == True) & (ev.arrival == 1)], base[base.with_trend == True])
sm = pd.DataFrame(rows)
sm.to_csv(A / "h4_reclaim_summary.csv", index=False)
pd.set_option("display.width", 260)
print(sm.round(3).T.to_string())
