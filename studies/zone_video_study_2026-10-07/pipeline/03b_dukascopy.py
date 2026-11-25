"""Stage 3b: download Dukascopy XAUUSD 1m BID candles (free public datafeed), one request at a time,
cache raw .bi5 files, and build one UTC DataFrame. URL months are 0-based. Prices are x1000."""
import lzma, sys, time, urllib.request
from pathlib import Path
import numpy as np, pandas as pd
W = Path(sys.argv[1]); start, end = sys.argv[2], sys.argv[3]
raw = W / "duka_raw"; raw.mkdir(exist_ok=True)
from concurrent.futures import ThreadPoolExecutor
days = [d for d in pd.date_range(start, end, freq="D") if d.weekday() != 5]  # Saturday: market closed

def fetch(day):
    f = raw / f"{day:%Y%m%d}.bi5"
    if not f.exists():
        url = f"https://datafeed.dukascopy.com/datafeed/XAUUSD/{day.year}/{day.month-1:02d}/{day.day:02d}/BID_candles_min_1.bi5"
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "zone-research/0.1 (personal study)"})
                f.write_bytes(urllib.request.urlopen(req, timeout=30).read()); break
            except Exception as e:
                time.sleep(3 * (attempt + 1))
        time.sleep(0.25)

with ThreadPoolExecutor(4) as ex:   # 4 concurrent requests at most
    list(ex.map(fetch, days))
frames = []
for day in days:
    f = raw / f"{day:%Y%m%d}.bi5"
    if not f.exists() or f.stat().st_size == 0:
        continue
    a = np.frombuffer(lzma.decompress(f.read_bytes()), dtype=">i4,>i4,>i4,>i4,>i4,>f4")
    df = pd.DataFrame(a.tolist(), columns=["t", "open", "close", "low", "high", "volume"])
    df.index = pd.Timestamp(day, tz="UTC") + pd.to_timedelta(df.pop("t"), unit="s")
    df[["open", "close", "low", "high"]] /= 1000.0
    frames.append(df)
m1 = pd.concat(frames).sort_index()
# Dukascopy fills closed-market minutes with flat zero-volume candles; drop them
m1 = m1[m1.volume > 0][["open", "high", "low", "close", "volume"]]
m1.to_pickle(W / "duka_1m.pkl")
print(len(m1), m1.index.min(), m1.index.max())
