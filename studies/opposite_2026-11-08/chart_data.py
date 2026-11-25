"""Monthly money curves for the 'made money / lost money' chart (2026-11-08).
For every trade of the 78 rules in opposite.py: its month, its gross points (before fees). Fees = 0.3 pt ($3) per trade.
Output chart_data.json: months + per selectable rule monthly gross $ and trade count (1 MGC per trade)."""
import glob, json, os
import numpy as np, pandas as pd

R = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/"
a = np.fromfile("/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
ny5 = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York")
ym5 = (ny5.year * 100 + ny5.month).to_numpy()
df = pd.DataFrame(a[:, 1:], columns=list("ohlc"), index=ny5)
b30 = df.resample("30min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()   # same bars as range_fade.py
ym30 = (b30.index.year * 100 + b30.index.month).to_numpy()
ymday = lambda s: (pd.to_datetime(s).dt.year * 100 + pd.to_datetime(s).dt.month).to_numpy()

parts = {}                       # rule id -> list of (ym array, gross points array)


def put(rid, ym, g):
    parts.setdefault(rid, []).append((np.asarray(ym), np.asarray(g, float)))
    parts.setdefault("all", []).append((np.asarray(ym), np.asarray(g, float)))


A = R + "asia_sweep_theorem_2026-11-07/"
for f in ("trades.csv", "trades_bias.csv"):
    T = pd.read_csv(A + f); put("theorem", ym5[T.k], T.pts)
T = pd.read_csv(A + "range_fade_trades.csv"); T = T[T.regime == "RANGE"]; put("rangefade", ym30[T.k], T.pts)
T = pd.read_csv(A + "exhaustion_trades.csv"); put("exhaustion", ym30[T.k], T.pts)
T = pd.read_csv(A + "trend_pullback_trades.csv"); put("trendpb", ym30[T.k], T.pts)
T = pd.read_csv(R + "replay_watch_2026-11-07/longtest/two_ideas_trades.csv")
g = T[T.idea.str.startswith("1")]; put("sweep", ym30[g.k], g.pts)
g = T[T.idea.str.startswith("2")]; put("spikefade", ym30[g.k], g.pts)
T = pd.read_csv(R + "noise_breakout_2026-11-08/trades_main.csv"); put("noise", ymday(T.day), T.gross)
T = pd.read_csv(R + "spike_follow_2026-11-08/trades_main.csv"); put("spike", ymday(T.day), T.gross)
C = R + "catalog_100_2026-11-08/"
T = pd.read_csv(C + "single_main_trades.csv"); put("s1800", ym5[T.i], T.gross)
T = pd.read_csv(C + "single_alt_trades.csv"); put("s1800alt", ym5[T.i], T.gross)
for f in sorted(glob.glob(C + "trades/*.csv")):
    T = pd.read_csv(f); put("c" + os.path.basename(f)[:2], ym5[T.i], T.gross)

months = [y * 100 + m for y in range(2012, 2027) for m in range(1, 13) if y * 100 + m <= 202609]
pos = {v: k for k, v in enumerate(months)}
LABELS = {"all": "All 78 rules together", "s1800": "Your 18:00 range breakout", "sweep": "Your sweep-reclaim fade",
          "spike": "Spike follow (my idea #2)", "noise": "Noise breakout (my idea #1)", "c13": "Catalog #13 9/21 EMA shift",
          "c04": "Catalog #4 U.S. opening range breakout", "c54": "Catalog #54 RSI divergence"}
out = {"months": [f"{m // 100}-{m % 100:02d}" for m in months], "rules": {}}
for rid, label in LABELS.items():
    gs, ns = np.zeros(len(months)), np.zeros(len(months), int)
    for ym, g in parts[rid]:
        k = np.array([pos[v] for v in ym]); np.add.at(gs, k, g * 10); np.add.at(ns, k, 1)
    out["rules"][rid] = {"label": label, "gross": np.round(gs, 1).tolist(), "n": ns.tolist()}
    print(f"{label:40s} trades {ns.sum():7,d}  before fees ${gs.sum():+12,.0f}  fees ${ns.sum() * 3:12,.0f}  "
          f"after ${gs.sum() - ns.sum() * 3:+13,.0f}  opposite after ${-gs.sum() - ns.sum() * 3:+13,.0f}")
json.dump(out, open(R + "opposite_2026-11-08/chart_data.json", "w"), separators=(",", ":"))
