import zipfile, io, pandas as pd, numpy as np
from pathlib import Path
D = Path("/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/data/raw/histdata/xauusd")
fr = []
for f in ["XAUUSD_2025.zip"] + [f"XAUUSD_2026{m:02d}.zip" for m in range(1, 10)]:
    z = zipfile.ZipFile(D / f)
    n = [x for x in z.namelist() if x.endswith(".csv")][0]
    fr.append(pd.read_csv(z.open(n), sep=";", header=None, names="dt o h l c v".split()))
d = pd.concat(fr)
d["t"] = pd.to_datetime(d.dt, format="%Y%m%d %H%M%S")   # HistData = EST without DST
d = d.drop_duplicates("t").sort_values("t")
np.save("xau1m.npy", np.c_[d.t.astype("int64").to_numpy() // 10**9, d[["o", "h", "l", "c"]].to_numpy()])
print(len(d), d.t.min(), d.t.max(), d.c.iloc[0], d.c.iloc[-1])
