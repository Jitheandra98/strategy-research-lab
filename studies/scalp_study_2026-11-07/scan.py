"""Scalp truth table on gold 1m (HistData XAUUSD, 2025-01 → 2026-09).
For every minute, both directions: does price reach +TP before −SL (1m bars, stop counted first on ties), within 4 h?
Cost 0.3 pt round trip (MGC: ~1 tick spread + commission ≈ $3 on a $10/pt contract)."""
import numpy as np, pandas as pd
a = np.load("xau1m.npy"); t, o, h, l, c = a.T
N, HOR, COST = len(c), 240, 0.3
TH = [1, 2, 3, 5, 10, 20, 50]
up = {x: np.full(N, HOR + 1, np.int16) for x in TH}; dn = {x: np.full(N, HOR + 1, np.int16) for x in TH}
for k in range(1, HOR + 1):
    hk = np.r_[h[k:], np.full(k, -np.inf)] - c; lk = c - np.r_[l[k:], np.full(k, np.inf)]
    for x in TH:
        m = (up[x] > HOR) & (hk >= x); up[x][m] = k
        m = (dn[x] > HOR) & (lk >= x); dn[x][m] = k
np.savez("passage.npz", **{f"u{x}": up[x] for x in TH}, **{f"d{x}": dn[x] for x in TH})
yr = pd.to_datetime(t, unit="s").year
rows = []
for tp in [1, 2, 3]:
    for sl in [1, 2, 3, 5, 10, 20, 50]:
        for y in [2025, 2026]:
            s = yr == y
            winL = (up[tp] < dn[sl]) & (up[tp] <= HOR); lossL = (dn[sl] <= up[tp]) & (dn[sl] <= HOR)
            winS = (dn[tp] < up[sl]) & (dn[tp] <= HOR); lossS = (up[sl] <= dn[tp]) & (up[sl] <= HOR)
            w = np.r_[winL[s], winS[s]].mean(); lo = np.r_[lossL[s], lossS[s]].mean()
            exp = w * (tp - COST) - lo * (sl + COST)
            pfv = w * (tp - COST) / (lo * (sl + COST))
            rows.append(dict(TP=tp, SL=sl, year=y, hit_TP_first=w * 100, hit_SL_first=lo * 100, need_to_break_even=(sl + COST) / (tp + sl) * 100, exp_pts=exp, PF=pfv))
pd.set_option("display.width", 200); pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(pd.DataFrame(rows).to_string(index=False))
