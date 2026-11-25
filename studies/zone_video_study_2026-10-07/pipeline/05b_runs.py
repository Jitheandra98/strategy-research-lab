"""Stage 5b: turn per-frame newest-bar dates into clean REPLAY RUNS and a bar -> first-seen-on-video map.

1. A frame's newest bar is kept only if it is within 6 bars of the rolling median (9 frames) of its neighbours.
2. Kept frames are chained into runs while the newest bar moves forward by 0..8 bars per keyframe
   (replay speed up to ~8 bars/s); anything else (Select-bar jumps, rewinds) starts a new run.
3. Runs with < 10 frames are discarded (too short to trust).
4. Every bar from a run's first to last newest bar was revealed on screen; its video time = the first keyframe at
   which the newest bar reached it. Bars shown in more than one video are listed with all videos.
Outputs: W/replay_runs.csv, W/bar_reveal.pkl
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
W = Path(sys.argv[1])
b15 = pd.read_pickle(W / "b15_ref.pkl")   # reference 15m index used by the dater
T = b15.index
fr = pd.read_csv(W / "frames_dated.csv", low_memory=False)
runs, rev = [], {}
for v, g in fr.groupby("video"):
    g = g[g.newest_idx.notna()].sort_values("t")
    x = g.newest_idx.to_numpy(float); t = g.t.to_numpy(); src = g.newest_src.to_numpy()
    med = pd.Series(x).rolling(9, center=True, min_periods=5).median().to_numpy()
    keep = np.abs(x - med) <= 6
    x, t, src = x[keep], t[keep], src[keep]
    cur = [0]
    def close(cur):
        if len(cur) >= 10:
            xs = x[cur]; ts = t[cur]
            runs.append(dict(video=v, run=len(runs) + 1, t0=ts[0], t1=ts[-1], n_frames=len(cur),
                             bar0=T[int(xs.min())], bar1=T[int(xs.max())], n_bars=int(xs.max() - xs.min() + 1),
                             frac_live_price=float(np.mean(src[cur] == "live_price"))))
            rid = len(runs)
            for b in range(int(xs.min()), int(xs.max()) + 1):
                k = int(np.argmax(xs >= b))
                rev.setdefault(T[b], []).append((int(v), float(ts[k]), rid))
    for k in range(1, len(x)):
        d = x[k] - x[cur[-1]]
        if 0 <= d <= 8 and t[k] - t[cur[-1]] < 30:
            cur.append(k)
        else:
            close(cur); cur = [k]
    close(cur)
R = pd.DataFrame(runs); R.to_csv(W / "replay_runs.csv", index=False)
pd.to_pickle(rev, W / "bar_reveal.pkl")
print(R.groupby("video").agg(runs=("run", "size"), frames=("n_frames", "sum"), bars=("n_bars", "sum"),
                             first=("bar0", "min"), last=("bar1", "max")))
multi = sum(1 for k, v in rev.items() if len({a for a, _, _ in v}) > 1)
print("bars revealed:", len(rev), " shown in >1 video:", multi)
