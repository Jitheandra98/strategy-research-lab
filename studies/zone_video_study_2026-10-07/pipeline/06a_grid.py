"""Stage 6a: decide the 4H bar grid by matching the video's 4h-pane header OPEN (o4) against candidate grids.
Writes W/h4_grid.json and prints the agreement for each candidate."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
W = Path(sys.argv[1]); src = sys.argv[2] if len(sys.argv) > 2 else "duka_1m.pkl"
m1 = pd.read_pickle(W / src)
fr = pd.read_csv(W / "frames_dated.csv", parse_dates=["bar_utc"])
fr = fr[fr.bar_utc.notna() & fr.o4.notna() & (fr.h4 != fr.l4)]  # o4 = open of the forming 4H bar
fr = fr[(fr.bar_utc >= m1.index.min()) & (fr.bar_utc <= m1.index.max())]
res = {}
def key_ny(idx):
    ny = idx.tz_convert("America/New_York")
    anchor = (ny - pd.Timedelta(hours=17)).normalize() + pd.Timedelta(hours=17)
    return (anchor + ((ny - anchor) // pd.Timedelta(hours=4)) * pd.Timedelta(hours=4)).tz_convert("UTC")
cands = {f"utc+{h}": (lambda idx, h=h: (idx - pd.Timedelta(hours=h)).floor("4h") + pd.Timedelta(hours=h)) for h in range(4)}
cands["ny_session"] = key_ny
for name, f in cands.items():
    t = pd.DatetimeIndex(fr.bar_utc)
    k = f(t)
    op = m1.open.reindex(m1.index)  # 1m opens
    first = m1.groupby(f(m1.index)).open.first()
    est = first.reindex(k).to_numpy()
    d = np.abs(est - fr.o4.to_numpy())
    res[name] = (np.nanmedian(d), np.nanmean(d < 0.6), len(d))
    print(name, "median|diff|=%.3f within0.6=%.1f%% n=%d" % (res[name][0], 100 * res[name][1], res[name][2]))
best = min(res, key=lambda n: res[n][0])
g = {"mode": "ny_session"} if best == "ny_session" else {"mode": "utc", "utc_offset_h": int(best.split("+")[1])}
g["evidence"] = {k: [round(v[0], 3), round(v[1], 3), v[2]] for k, v in res.items()}
(W / "h4_grid.json").write_text(json.dumps(g, indent=1)); print("chosen", best)
