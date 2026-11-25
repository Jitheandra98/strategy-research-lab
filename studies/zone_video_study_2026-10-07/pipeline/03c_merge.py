"""Stage 3c: one 1m series. Dukascopy for every UTC day it was downloaded (complete feed), HistData elsewhere.
Where both exist they agree (median |open diff| = 0.00 over Sep-Oct 2022). Writes W/merged_1m.pkl + coverage report."""
import lzma, sys
from pathlib import Path
import numpy as np, pandas as pd
W = Path(sys.argv[1])
hd = pd.read_pickle(W / "xau_1m.pkl")[["open", "high", "low", "close", "volume"]]
frames, days = [], []
for f in sorted((W / "duka_raw").glob("*.bi5")):
    if f.stat().st_size == 0: continue
    day = pd.Timestamp(f.stem, tz="UTC")
    a = np.frombuffer(lzma.decompress(f.read_bytes()), dtype=">i4,>i4,>i4,>i4,>i4,>f4")
    df = pd.DataFrame(a.tolist(), columns=["t", "open", "close", "low", "high", "volume"])
    df.index = day + pd.to_timedelta(df.pop("t"), unit="s")
    df[["open", "close", "low", "high"]] /= 1000.0
    frames.append(df[df.volume > 0][["open", "high", "low", "close", "volume"]]); days.append(day.date())
dk = pd.concat(frames).sort_index()
keep_hd = hd[~pd.Index(hd.index.date).isin(set(days))]
m = pd.concat([dk, keep_hd]).sort_index()
m = m[~m.index.duplicated()]
m.to_pickle(W / "merged_1m.pkl")
src = pd.Series(np.where(pd.Index(m.index.date).isin(set(days)), "duka", "histdata"), index=m.index)
print(len(m), "duka days", len(days), m.index.min(), m.index.max())
print(m.resample("W").size().loc["2022-08":"2024-08"].describe())
