"""Do any 'special places' make a $1–3 scalp win often enough to pay? Event entries on gold 1m, fade and follow,
picked on 2025 (train), judged on 2026 (test). Same stop-first, 4 h limit, cost 0.3 pt."""
import numpy as np, pandas as pd
a = np.load("xau1m.npy"); t, o, h, l, c = a.T; P = np.load("passage.npz")
N, HOR, COST = len(c), 240, 0.3
dt = pd.to_datetime(t, unit="s"); yr = dt.year.to_numpy(); hr = dt.hour.to_numpy(); mi = dt.minute.to_numpy()
day = (dt - pd.Timedelta(hours=17)).normalize()          # gold day rolls at 17:00 EST
g = pd.DataFrame(dict(h=h, l=l, day=day))
dH = g.groupby("day").h.max(); dL = g.groupby("day").l.min()
pdh = day.map(dH.shift(1)).to_numpy(); pdl = day.map(dL.shift(1)).to_numpy()
prev_h = np.r_[np.nan, h[:-1]]; prev_l = np.r_[np.nan, l[:-1]]; prev_c = np.r_[np.nan, c[:-1]]
tr = np.maximum(h - l, np.maximum(abs(h - prev_c), abs(l - prev_c)))
atr = pd.Series(tr).rolling(60).mean().to_numpy()
hi60 = pd.Series(h).shift(1).rolling(60).max().to_numpy(); lo60 = pd.Series(l).shift(1).rolling(60).min().to_numpy()
r50 = lambda x: np.floor(x / 50) * 50
ev = {  # name: (mask, direction for FOLLOW: +1 long / -1 short)
 "PDH touch from below": ((h >= pdh) & (prev_h < pdh), 1),
 "PDL touch from above": ((l <= pdl) & (prev_l > pdl), -1),
 "round 00/50 cross up": ((r50(h) > r50(prev_h)), 1),
 "round 00/50 cross down": ((r50(l) < r50(prev_l)), -1),
 "big up bar (>3 ATR)": ((c - o) > 3 * atr, 1),
 "big down bar (>3 ATR)": ((o - c) > 3 * atr, -1),
 "sweep 60m high, close back in": ((h > hi60) & (c < hi60), 1),
 "sweep 60m low, close back in": ((l < lo60) & (c > lo60), -1),
 "08:30 EST bar (data)": ((hr == 8) & (mi == 30), 0),
 "09:30 EST bar (NY open)": ((hr == 9) & (mi == 30), 0),
 "03:00 EST bar (London)": ((hr == 3) & (mi == 0), 0),
 "every minute (baseline)": (np.ones(N, bool), 0),
}
def outcome(idx, d, tp, sl):
    U, D = (P[f"u{tp}"], P[f"d{sl}"]) if d == 1 else (P[f"d{tp}"], P[f"u{sl}"])
    u, dd = U[idx], D[idx]
    win = (u < dd) & (u <= HOR); loss = (dd <= u) & (dd <= HOR)
    return win, loss
rows = []
for name, (m, fdir) in ev.items():
    m = m & ~np.isnan(atr)
    for mode in (["follow", "fade"] if fdir else ["long", "short"]):
        d = (fdir if mode == "follow" else -fdir) if fdir else (1 if mode == "long" else -1)
        for tp, sl in [(1, 1), (2, 2), (3, 3), (2, 3), (3, 2), (2, 5), (1, 3)]:
            r = dict(event=name, mode=mode, TP=tp, SL=sl, need=(sl + COST) / (tp + sl) * 100)
            for y in (2025, 2026):
                idx = np.where(m & (yr == y))[0]; idx = idx[idx < N - HOR]
                w, lo = outcome(idx, d, tp, sl)
                r[f"n{y}"] = len(idx); r[f"win{y}"] = w.sum() / max(1, w.sum() + lo.sum()) * 100
            rows.append(r)
df = pd.DataFrame(rows)
df["edge2025"] = df.win2025 - df.need; df["edge2026"] = df.win2026 - df.need
pd.set_option("display.width", 220); pd.set_option("display.float_format", lambda v: f"{v:.1f}")
print("Best 15 setups picked on 2025 (train), with their 2026 (test) result:")
print(df[df.n2025 >= 100].sort_values("edge2025", ascending=False).head(15).to_string(index=False))
print("\nSetups positive in BOTH years:", int(((df.edge2025 > 0) & (df.edge2026 > 0) & (df.n2025 >= 100)).sum()), "of", len(df))
df.to_csv("levels.csv", index=False)
