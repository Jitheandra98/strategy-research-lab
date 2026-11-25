"""Build 5 m bars (New York clock) from the 1 m FX files for cross_check.py. The pickles need numpy 2, so run with the
trading-video-intel venv:  trading-video-intel/.venv/bin/python3 -I fx_to_5m.py <out_dir>"""
import sys
import numpy as np, pandas as pd

SRC = "/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/data/raw/histdata"
OUT = sys.argv[1]
for p in ["eurusd", "gbpusd", "usdjpy", "usdcad", "usdchf"]:
    df = pd.read_pickle(f"{SRC}/{p}_1m_2016_2026.pkl")
    df.index = df.index.tz_convert("America/New_York").tz_localize(None)
    r = df.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    np.savez_compressed(f"{OUT}/{p}_5m.npz", ns=r.index.as_unit("ns").asi8.astype(np.int64),
                        o=r.open.to_numpy(float), h=r.high.to_numpy(float), l=r.low.to_numpy(float),
                        c=r.close.to_numpy(float))
    print(p, len(r), r.index[0], r.index[-1])
