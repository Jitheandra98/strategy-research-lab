"""Stage 6: bars + STATION2 zones.

Bars: Dukascopy XAUUSD 1m -> 15m (UTC, left-labelled). 4H bars on the grid chosen by 06a_grid.py (validated against
the 4h pane header in the video). Zones: the line-for-line STATION2 (STA-2.1) port from run2 (zone_engine.py),
run on (a) the 15m chart with the replay-time 4H FVG import, (b) the 4H chart.
Outputs (W): bars15.pkl, bars4h.pkl, zones15.pkl, zones4h.pkl
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from zone_engine import ZoneEngine

W = Path(sys.argv[1])
GRID = json.loads((W / "h4_grid.json").read_text())   # {"mode": "...", ...}


def bars15_from_1m(m1):
    b = m1.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    return b


def h4_key(idx):
    """4H bucket start for each UTC timestamp, per the validated grid."""
    if GRID["mode"] == "ny_session":
        # buckets anchored at 17:00 America/New_York (TradingView/OANDA session open), 4h each
        ny = idx.tz_convert("America/New_York")
        anchor = (ny - pd.Timedelta(hours=17)).normalize() + pd.Timedelta(hours=17)
        k = anchor + ((ny - anchor) // pd.Timedelta(hours=4)) * pd.Timedelta(hours=4)
        return k.tz_convert("UTC")
    off = pd.Timedelta(hours=GRID["utc_offset_h"])
    return (idx - off).floor("4h") + off


def build():
    import os
    m1 = pd.read_pickle(W / os.environ.get("SRC", "duka_1m.pkl"))
    if "START" in os.environ: m1 = m1.loc[os.environ["START"]:os.environ["END"]]
    b15 = bars15_from_1m(m1)
    b15["h4key"] = h4_key(b15.index)
    h4 = b15.groupby("h4key").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                                  close=("close", "last"), volume=("volume", "sum"),
                                  last15=("open", lambda s: s.index[-1]))
    h4.index.name = "time"
    # 4H bar becomes "closed" (available) when its last 15m bar closes
    h4["avail"] = h4.last15 + pd.Timedelta(minutes=15)
    # replay-time import: inside forming 4H bar j the tuple refers to closed bars j-1 and j-3
    H = h4.reset_index()
    j_of = dict(zip(H.time, H.index))
    rows = []
    for k in b15.h4key:
        j = j_of[k]
        if j >= 3:
            rows.append((H.low[j - 1], H.high[j - 3], H.high[j - 1], H.low[j - 3], H.time[j - 1]))
        else:
            rows.append((np.nan,) * 4 + (pd.NaT,))
    imp = pd.DataFrame(rows, columns=["h4bl", "h4bh", "h4sl", "h4sh", "h4t"])
    e15 = ZoneEngine(b15[["open", "high", "low", "close"]], h4_import=imp, label="15m").run()
    z15 = e15.zones_frame(times=b15.index)
    b15["atr"] = e15.atr; b15["ema"] = e15.ema; b15["trend"] = e15.trend
    e4 = ZoneEngine(h4[["open", "high", "low", "close"]], cfg=dict(WARMUP=100), label="4h").run()
    z4 = e4.zones_frame(times=h4.index)
    h4["atr"] = e4.atr; h4["ema"] = e4.ema; h4["trend"] = e4.trend
    # structure events (BOS/CHoCH) for both charts, kept for features
    s15 = pd.DataFrame(e15.structure, columns=["bar", "dir", "kind", "level"]); s15["time"] = b15.index[s15.bar]
    s4 = pd.DataFrame(e4.structure, columns=["bar", "dir", "kind", "level"]); s4["time"] = h4.index[s4.bar]
    pools = pd.DataFrame(e15.pools)
    b15.to_pickle(W / "bars15.pkl"); h4.to_pickle(W / "bars4h.pkl")
    z15.to_pickle(W / "zones15.pkl"); z4.to_pickle(W / "zones4h.pkl")
    s15.to_pickle(W / "struct15.pkl"); s4.to_pickle(W / "struct4h.pkl"); pools.to_pickle(W / "pools15.pkl")
    print("15m bars", len(b15), "4h bars", len(h4), "zones15", len(z15), z15.kind.value_counts().to_dict(),
          "zones4h", len(z4), z4.kind.value_counts().to_dict())


if __name__ == "__main__":
    build()
