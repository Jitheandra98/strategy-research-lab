"""Stage 3: load the independent reference feed (HistData XAUUSD 1m, 2021-2025) into one UTC parquet/pickle.
Used only to (a) date the video's bars via OCR'd header OHLC and (b) fill bars the video does not show legibly."""
import io, sys, zipfile
from pathlib import Path
import pandas as pd
RAW = Path("/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/data/raw/histdata/xauusd")
out = Path(sys.argv[1])
dfs = []
files = [RAW / f"XAUUSD_{y}.zip" for y in range(2021, 2026)] + sorted(RAW.glob("XAUUSD_2026*.zip"))
for fz in files:
    with zipfile.ZipFile(fz) as z:
        csv = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        df = pd.read_csv(io.BytesIO(z.read(csv)), sep=";", header=None, names=["ts", "open", "high", "low", "close", "volume"])
    ts = pd.DatetimeIndex(pd.to_datetime(df.pop("ts"), format="%Y%m%d %H%M%S"))
    df.index = ts.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward")
    df = df[df.index.notna()]
    df.index = df.index.tz_convert("UTC")
    dfs.append(df)
m1 = pd.concat(dfs).sort_index()
m1 = m1[~m1.index.duplicated()]
m1.to_pickle(out)
print(len(m1), m1.index.min(), m1.index.max())
