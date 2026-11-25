"""Stage 14: owner's claim — 4H candles move box to box and STOP at a box's top / midline / bottom.
For every 4H bar: distance from its high and from its low to the nearest level (top, mid, bottom) of every box
that was on the chart when the bar opened (4H-pane zones: OB, FVG, incl. consumed and inverted = breaker/IFVG;
optionally 15m-pane zones). Rate of extremes within tol x ATR4 of a level, real vs placebo boxes
(each box moved up/down by a random 1-3 ATR4, same count/heights/life), 30 placebo draws.
usage: 14_h4_stops.py <build_dir> <work_dir> <out_csv>"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
B, W, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
h4 = pd.read_pickle(B / "bars4h.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl"); z15 = pd.read_pickle(B / "zones15.pkl")
rev = pd.read_pickle(W / "bar_reveal.pkl")
vid = {}
for t, v in rev.items():
    vid.setdefault(t.floor("15min"), v[0][0])
h4 = h4[h4.atr.notna()].copy()
h4["video"] = [next((vid[t] for t in pd.date_range(k, k + pd.Timedelta(hours=4), freq="15min", inclusive="left") if t in vid), np.nan) for k in h4.index]
h4["avail_start"] = h4.index  # a box must exist before the bar opens
T4 = h4.index


def boxes(z, shift=None):
    b = pd.DataFrame({"top": z.top.values, "bot": z.bot.values, "born": z.born_time.values,
                      "end": z.end_time.values, "kind": z.kind.values})
    if shift is not None:
        b["top"] += shift; b["bot"] += shift
    return b


def rates(b, tols, avail_lag):
    born = pd.to_datetime(b.born).values; end = pd.to_datetime(b.end).values
    out = {f"{lv}_{t}": [] for lv in ("any", "top", "mid", "bot") for t in tols}
    nlev = []
    for k, r in zip(T4, h4.itertuples()):
        live = (born + avail_lag <= np.datetime64(k.tz_convert(None))) & ((pd.isna(end)) | (end > np.datetime64(k.tz_convert(None))))
        if not live.any():
            for key in out: out[key].append(np.nan)
            nlev.append(0); continue
        tp, bt = b.top.values[live], b.bot.values[live]; md = (tp + bt) / 2
        # only levels within the bar's reach matter: count levels inside [low-1ATR, high+1ATR]
        nlev.append(int(((tp > r.low - r.atr) & (bt < r.high + r.atr)).sum()))
        for lvname, L in (("top", tp), ("mid", md), ("bot", bt)):
            d = np.minimum(np.abs(L - r.high).min(), np.abs(L - r.low).min()) / r.atr
            for t in tols: out[f"{lvname}_{t}"].append(d <= t)
        dall = min(np.abs(np.r_[tp, md, bt] - r.high).min(), np.abs(np.r_[tp, md, bt] - r.low).min()) / r.atr
        for t in tols: out[f"any_{t}"].append(dall <= t)
    return pd.DataFrame(out, index=T4).assign(nlev=nlev)


tols = [0.05, 0.10, 0.20]
rng = np.random.default_rng(3)
res = []
for name, z, lag in (("4H-pane boxes", z4, np.timedelta64(4, "h")), ("15m-pane boxes", z15, np.timedelta64(15, "m"))):
    real = rates(boxes(z), tols, lag)
    atr_b = h4.atr.reindex(z.born_time.dt.floor("4h"), method="nearest").to_numpy() if False else np.nanmedian(h4.atr)
    plc = []
    for _ in range(30):
        sh = rng.choice([-1, 1], len(z)) * rng.uniform(1, 3, len(z)) * np.interp(
            z.born_time.astype("int64"), h4.index.astype("int64"), h4.atr.ffill().to_numpy())
        plc.append(rates(boxes(z, sh), tols, lag))
    for split, m in (("ON VIDEO", h4.video.notna()), ("V1+V2", h4.video.isin([1, 2])), ("V3", h4.video == 3)):
        for c in [c for c in real.columns if c != "nlev"]:
            rv = real.loc[m, c].astype(float).mean()
            pv = np.array([p.loc[m, c].astype(float).mean() for p in plc])
            res.append(dict(boxes=name, split=split, level_tol=c, n_bars=int(m.sum()), real=rv, placebo_mean=pv.mean(),
                            placebo_p95=np.quantile(pv, 0.95), placebo_max=pv.max(), lift=rv / pv.mean(),
                            real_beats_all_30=bool(rv > pv.max())))
        res.append(dict(boxes=name, split=split, level_tol="levels_in_reach", n_bars=int(m.sum()),
                        real=real.loc[m, "nlev"].mean(), placebo_mean=np.mean([p.loc[m, "nlev"].mean() for p in plc])))
R = pd.DataFrame(res); R.to_csv(OUT, index=False)
pd.set_option("display.width", 250)
print(R[R.split != "ON VIDEO"].round(3).to_string())
