"""Score calibration recomputed in Python from the per-bar scores, checked against the indicator's own counters."""
import json, sys, numpy as np
OUT = sys.argv[1]; H = 12
J = json.load(open(OUT)); vt = J["vtitles"]
T = np.fromfile(OUT + ".times.f64", dtype=np.float64)
V = np.fromfile(OUT + ".vals.f32", dtype=np.float32).reshape(len(T), len(vt)).astype(np.float64)
g = lambda k: V[:, vt.index(k)]
B = np.fromfile("gc5m7_ct.f64", dtype=np.float64).reshape(-1, 7); idx = {t: i for i, t in enumerate(B[:, 0])}
C = B[[idx[t] for t in T], 4]; atr = g("v_atr"); sb = g("v_scoreB"); ss = g("v_scoreS")
i = np.arange(len(T)); m = (i > H + 60) & (atr[np.clip(i - H, 0, None)] > 0)
fwd = np.where(m, (C - C[np.clip(i - H, 0, None)]) / atr[np.clip(i - H, 0, None)], np.nan)
bB = np.minimum((sb[np.clip(i - H, 0, None)] // 20).astype(int), 4); bS = np.minimum((ss[np.clip(i - H, 0, None)] // 20).astype(int), 4)
print(f"check vs indicator counters: bucket0 n {np.sum(m & (bB==0))} vs {g('v_cbN0')[-1]:.0f}; bucket4 n {np.sum(m & (bB==4))} vs {g('v_cbN4')[-1]:.0f}; all n {m.sum()} vs {g('v_allN')[-1]:.0f}")
print(f"{'score':>8} | {'buy score: avg move (ATR), hit, n':>34} | {'sell score: avg move, hit, n':>30}")
for b in range(4, -1, -1):
    x = fwd[m & (bB == b)]; y = -fwd[m & (bS == b)]
    print(f"{b*20:>3}–{min(b*20+19,100):<4} | {x.mean() if len(x) else float('nan'):+.3f}  {100*np.mean(x>0) if len(x) else 0:4.1f}%  {len(x):7d}      | {y.mean() if len(y) else float('nan'):+.3f}  {100*np.mean(y>0) if len(y) else 0:4.1f}%  {len(y):7d}")
a = fwd[m]; print(f"baseline | {a.mean():+.3f}  {100*np.mean(a>0):4.1f}%  {len(a):7d}      | {-a.mean():+.3f}  {100*np.mean(a<0):4.1f}%")
# does the top band beat baseline beyond noise? (overlapping windows: use n/H as effective n)
for side, s, sign in (("buy", bB, 1), ("sell", bS, -1)):
    x = sign * fwd[m & (s == 4)]; base = sign * a.mean()
    if len(x) > 10:
        se = a.std() / np.sqrt(max(len(x) / H, 1)); print(f"{side} 80–100 vs baseline: {x.mean() - base:+.3f} ATR (≈ t {(x.mean()-base)/se:+.2f}, n_eff {len(x)/H:.0f})")
