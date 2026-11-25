"""Stage 16 — the user's flip: a 4H zone BREAKS (4H close beyond its far edge); later a 4H candle comes
BACK, wicks into/through the broken zone from the break side, and CLOSES back on the break side.
Does price then move 40+ pts in the break direction (the zone's new role)?
  flip-retest (broken demand = new supply): 4H high >= zone bot, close < zone bot, prev 4H high < zone bot
  mirror for broken supply. Within 30 4H bars (~5 days) of the break; first retest only.
Measured from the next 4H open: max move each way within 1/3/6 4H bars, P(>=40 in flip direction),
and the same from random 4H bars in the same direction (baseline).
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
OUT = Path(sys.argv[1]); A = OUT / "analysis"
rng = np.random.default_rng(5)
h4 = pd.read_csv(OUT / "data" / "bars_4h.csv"); h4["time_ct"] = pd.to_datetime(h4.time_ct, utc=True).dt.tz_convert("America/Chicago")
z = pd.read_csv(OUT / "zones.csv"); z = z[z.tf == "4h"]
days = np.sort(h4.time_ct.dt.date.unique()); cut = days[int(len(days) * .6)]
rows = []
def exc(g, k, d, H):
    if k + H >= len(g): return np.nan, np.nan
    e = g.iloc[k + 1].open; nx = g.iloc[k + 1:k + 1 + H]
    return ((nx.high.max() - e) if d == 1 else (e - nx.low.min())), ((e - nx.low.min()) if d == 1 else (nx.high.max() - e))
for sg, g in h4.groupby("segment"):
    g = g.reset_index(drop=True); zs = z[z.segment == sg]
    for zr in zs.itertuples():
        k0 = int(zr.born_bar) + 1; d0 = int(zr.dir); broken_at = None
        for k in range(k0, len(g)):
            r = g.iloc[k]
            if broken_at is None:
                if (d0 == 1 and r.close < zr.bot) or (d0 == -1 and r.close > zr.top):
                    broken_at = k
                continue
            if k - broken_at > 30: break
            p = g.iloc[k - 1]; fd = -d0            # flip direction
            if fd == -1:   # broken demand, now supply: came up into it and closed back below
                touch = r.high >= zr.bot and p.high < zr.bot; ok = touch and r.close < zr.bot
                through = r.high > zr.top
            else:
                touch = r.low <= zr.top and p.low > zr.top; ok = touch and r.close > zr.top
                through = r.low < zr.bot
            if touch:
                if ok:
                    out = dict(time=r.time_ct, dir=fd, wick_through=through, bars_since_break=k - broken_at,
                               with_trend=(r.trend4 == fd) if not np.isnan(r.trend4) else None,
                               split="DEV" if r.time_ct.date() < cut else "HOLDOUT")
                    for H in (1, 3, 6):
                        out[f"fav{H}"], out[f"adv{H}"] = exc(g, k, fd, H)
                    rows.append(out)
                break      # first return only
x = pd.DataFrame(rows).dropna(subset=["fav6"])
x.to_csv(A / "h4_flip_events.csv", index=False)
# baseline: random 4H bars, same direction
base = []
for sg, g in h4.groupby("segment"):
    g = g.reset_index(drop=True)
    for k in rng.choice(np.arange(1, len(g) - 7), size=min(400, len(g) - 8), replace=False):
        for d in (1, -1):
            f, a = exc(g, k, d, 6); base.append(dict(dir=d, fav6=f, adv6=a, with_trend=(g.iloc[k].trend4 == d)))
b = pd.DataFrame(base).dropna()
def s(name, xx, bb):
    print(f"{name:42s} n={len(xx):3d}  P(+40 in flip dir,24h)={(xx.fav6>=40).mean():.2f} vs random {(bb.fav6>=40).mean():.2f} | "
          f"median fav {xx.fav6.median():5.1f} / adv {xx.adv6.median():5.1f}  (random {bb.fav6.median():.1f}/{bb.adv6.median():.1f}) | "
          f"P(fav>adv) {(xx.fav6>xx.adv6).mean():.2f} | DEV {((x.split=='DEV')&xx.index.isin(xx.index)).sum() if False else (xx[xx.split=='DEV'].fav6>=40).mean():.2f} HO {(xx[xx.split=='HOLDOUT'].fav6>=40).mean():.2f}")
s("ALL 4H flip-retests", x, b)
s("flip WITH 4H trend", x[x.with_trend == True], b[b.with_trend == True])
s("flip AGAINST 4H trend", x[x.with_trend == False], b[b.with_trend == False])
s("wick went THROUGH the zone", x[x.wick_through], b)
s("wick stayed inside the zone", x[~x.wick_through], b)
