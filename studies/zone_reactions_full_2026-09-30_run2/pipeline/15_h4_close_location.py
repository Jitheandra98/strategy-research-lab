"""Stage 15 — where does the 4H candle CLOSE relative to the 4H zone it touched, and what follows?
For every 4H bar that trades into an intact 4H zone (touch from the zone's near side), classify the close:
  A  closed back OUTSIDE the near edge (reclaim / bounce)
  B  closed INSIDE, near half (beginning of the zone)
  C  closed INSIDE, far half (end of the zone)
  D  closed BEYOND the far edge (break)
Then measure, from that 4H close, the next 1 and 3 4H bars: net move in the zone's direction (+ = bounce side),
and max excursion each way; P(>=40 pts in bounce direction) and P(>=40 in break direction) within 3 bars (12h).
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
OUT = Path(sys.argv[1]); A = OUT / "analysis"
h4 = pd.read_csv(OUT / "data" / "bars_4h.csv"); h4["time_ct"] = pd.to_datetime(h4.time_ct, utc=True).dt.tz_convert("America/Chicago")
z = pd.read_csv(OUT / "zones.csv"); z = z[z.tf == "4h"]
days = np.sort(h4.time_ct.dt.date.unique()); cut = days[int(len(days) * .6)]
rows = []
for sg, g in h4.groupby("segment"):
    g = g.reset_index(drop=True); zs = z[z.segment == sg]; live = []
    for k in range(1, len(g)):
        for zr in zs[zs.born_bar == k - 1].itertuples():
            live.append(dict(top=zr.top, bot=zr.bot, dir=int(zr.dir), kind=zr.kind, n=0))
        r, p = g.iloc[k], g.iloc[k - 1]
        for zz in live:
            if zz.get("broken"): continue
            d, top, bot = zz["dir"], zz["top"], zz["bot"]; size = top - bot
            touched = (r.low <= top and p.low > top) if d == 1 else (r.high >= bot and p.high < bot)
            if touched:
                zz["n"] += 1
                if d == 1:
                    pos = (r.close - bot) / size        # >1 above top (outside near), <0 below bot (break)
                else:
                    pos = (top - r.close) / size
                cls = "A outside near edge (reclaim)" if pos > 1 else "B inside, near half" if pos >= .5 else "C inside, far half (end of zone)" if pos >= 0 else "D beyond far edge (break)"
                out = dict(cls=cls, dir=d, touch_no=zz["n"], with_trend=(r.trend4 == d) if not np.isnan(r.trend4) else None,
                           split="DEV" if r.time_ct.date() < cut else "HOLDOUT", size=size)
                for H in (1, 3):
                    if k + H < len(g):
                        nxt = g.iloc[k + 1:k + 1 + H]
                        out[f"net{H}"] = d * (g.iloc[k + H].close - r.close)
                        out[f"up{H}"] = (nxt.high.max() - r.close) if d == 1 else (r.close - nxt.low.min())      # bounce-side excursion
                        out[f"dn{H}"] = (r.close - nxt.low.min()) if d == 1 else (nxt.high.max() - r.close)      # break-side excursion
                rows.append(out)
            if (d == 1 and r.close < bot) or (d == -1 and r.close > top):
                zz["broken"] = True
x = pd.DataFrame(rows).dropna(subset=["net3"])
x.to_csv(A / "h4_close_location_events.csv", index=False)
def s(g):
    return pd.Series(dict(n=len(g), next1_net=g.net1.mean(), next3_net=g.net3.mean(), p_next3_bounce_side=(g.net3 > 0).mean(),
                          p_bounce40_12h=(g.up3 >= 40).mean(), p_break40_12h=(g.dn3 >= 40).mean(),
                          med_bounce_exc=g.up3.median(), med_break_exc=g.dn3.median()))
pd.set_option("display.width", 250)
print("ALL touches\n", x.groupby("cls").apply(s).round(2).to_string())
print("\nWITH 4H trend\n", x[x.with_trend == True].groupby("cls").apply(s).round(2).to_string())
print("\nAGAINST 4H trend\n", x[x.with_trend == False].groupby("cls").apply(s).round(2).to_string())
print("\nWITH trend, by split (next3_net)\n", x[x.with_trend == True].groupby(["cls", "split"]).net3.agg(["size", "mean"]).round(2).to_string())
x.groupby(["with_trend", "cls"]).apply(s).round(3).to_csv(A / "h4_close_location_summary.csv")
