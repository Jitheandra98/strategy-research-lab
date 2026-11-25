"""Stage 17: owner's levels = previous days' high/low and previous London / New York session highs/lows (last 3 days).
Do 4H closes and 4H highs/lows land on them more than on the same levels moved 1-3 ATR4 at random (30 draws)?
Sessions in New York time: day = 17:00-17:00, London 02:00-08:00, New York 08:00-17:00."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
B = Path(sys.argv[1]); OUT = Path(sys.argv[2]); PLC = sys.argv[3] if len(sys.argv) > 3 else "shift"
b = pd.read_pickle(B / "bars15.pkl"); h4 = pd.read_pickle(B / "bars4h.pkl"); h4 = h4[h4.atr.notna()]
ny = b.index.tz_convert("America/New_York")
day = (ny - pd.Timedelta(hours=17)).normalize()
hr = ny.hour
lv = []
for name, m in (("DAY", np.ones(len(b), bool)), ("LONDON", (hr >= 2) & (hr < 8)), ("NY", (hr >= 8) & (hr < 17))):
    g = b[m].groupby(day[m]).agg(hi=("high", "max"), lo=("low", "min"), end=("close", lambda s: s.index[-1]))
    g["end"] = g.end + pd.Timedelta(minutes=15)
    for _, r in g.iterrows():
        lv += [(name, r.end, r.hi), (name, r.end, r.lo)]
L = pd.DataFrame(lv, columns=["kind", "avail", "px"]).sort_values("avail").reset_index(drop=True)
av = L.avail.values; px0 = L.px.values
rng = np.random.default_rng(9)
atr_at = np.interp(L.avail.astype("int64"), h4.index.astype("int64"), h4.atr.to_numpy())


def rates(px, field):
    hits = {0.05: [], 0.1: []}
    for k, r in zip(h4.index, h4.itertuples()):
        t0 = np.datetime64(k.tz_convert(None)); lo = np.searchsorted(av, t0 - np.timedelta64(3, "D")); hi = np.searchsorted(av, t0)
        P = px[lo:hi]
        if not len(P): [hits[t].append(np.nan) for t in hits]; continue
        if field == "close": d = np.abs(P - r.close).min() / r.atr
        else: d = min(np.abs(P - r.high).min(), np.abs(P - r.low).min()) / r.atr
        for t in hits: hits[t].append(d <= t)
    return {t: np.nanmean(np.array(v, float)) for t, v in hits.items()}


rows = []
for field in ("close", "high/low"):
    real = rates(px0, field)
    if PLC == "shift":
        plc = [rates(px0 + rng.choice([-1, 1], len(px0)) * rng.uniform(1, 3, len(px0)) * atr_at, field) for _ in range(30)]
    else:  # "traded": each level replaced by a random 15m close from the 3 days before it became available
        bt = b.index.values; bc = b.close.to_numpy(); plc = []
        lo_i = np.searchsorted(bt, av - np.timedelta64(3, "D")); hi_i = np.searchsorted(bt, av)
        for _ in range(30):
            k = (lo_i + rng.random(len(av)) * np.maximum(1, hi_i - lo_i)).astype(int).clip(0, len(bc) - 1)
            plc.append(rates(bc[k], field))
    for t in real:
        p = np.array([x[t] for x in plc])
        rows.append(dict(placebo=PLC, field=field, tol_atr4=t, n_4h_bars=len(h4), real=real[t], placebo_mean=p.mean(), placebo_max=p.max(),
                         lift=real[t] / p.mean(), beats_all_30=real[t] > p.max()))
R = pd.DataFrame(rows); R.to_csv(OUT, index=False); print(R.round(3).to_string())
