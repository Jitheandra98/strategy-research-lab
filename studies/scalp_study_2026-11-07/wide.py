"""Wide-stop rows done honestly: trades that hit neither TP nor SL in 4 h are closed at the 4-h price (not ignored). Split long/short."""
import numpy as np, pandas as pd
a = np.load("xau1m.npy"); t, o, h, l, c = a.T; P = np.load("passage.npz")
N, HOR, COST = len(c), 240, 0.3
yr = pd.to_datetime(t, unit="s").year
fwd = np.r_[c[HOR:], np.full(HOR, np.nan)] - c
rows = []
for tp, sl in [(1, 10), (1, 20), (1, 50), (2, 20), (2, 50), (3, 50)]:
    for side, U, D, sgn in [("long", P[f"u{tp}"], P[f"d{sl}"], 1), ("short", P[f"d{tp}"], P[f"u{sl}"], -1)]:
        win = (U < D) & (U <= HOR); loss = (D <= U) & (D <= HOR); rest = ~win & ~loss
        pnl = np.where(win, tp, np.where(loss, -sl, sgn * fwd)) - COST
        for y in [2025, 2026]:
            s = (yr == y) & ~np.isnan(pnl)
            x = pnl[s]
            rows.append(dict(TP=tp, SL=sl, side=side, year=y, win=(x > 0).mean() * 100, unresolved=rest[s].mean() * 100,
                             avg_pts=x.mean(), PF=x[x > 0].sum() / -x[x < 0].sum(), worst=x.min()))
pd.set_option("display.width", 200); pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(pd.DataFrame(rows).to_string(index=False))
# drift check: what does simply holding 4 h earn per minute, long?
for y in [2025, 2026]:
    s = (yr == y) & ~np.isnan(fwd); print(y, "buy-and-hold 4h avg pts per entry:", round(np.nanmean(fwd[s]), 3))
