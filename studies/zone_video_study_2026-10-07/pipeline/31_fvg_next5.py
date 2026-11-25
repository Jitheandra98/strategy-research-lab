"""Stage 31: after a fresh FVG, does price go $5 further? Frozen in PREREGISTRATION.md (2026-10-26 d).
usage: 31_fvg_next5.py <minute_pickle> <out_dir> <tf_minutes>"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
M1, OUT, TF = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
COST, TGT, W, LIFE = 0.30, 5.0, 12, 288
m1 = pd.read_pickle(M1)[["open", "high", "low", "close"]]
b = m1.resample(f"{TF}min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
T = b.index; O, H, L, C = (b[k].to_numpy() for k in ["open", "high", "low", "close"]); n = len(C)
pc = np.r_[np.nan, C[:-1]]
tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
A = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
# live opposite FVG/IFVG zones: arrays of (start, end, top, bot) per direction of the ZONE
zon = {1: [], -1: []}
for i in range(2, n - 1):
    for d, top, bot in ((1, L[i], H[i - 2]), (-1, L[i - 2], H[i])):
        if top - bot < 0.25 * A[i]: continue
        seg = C[i + 1:i + 1 + LIFE]
        br = np.where(seg < bot)[0] if d == 1 else np.where(seg > top)[0]
        if not len(br): zon[d].append((i + 1, i + 1 + LIFE, top, bot)); continue
        k = i + 1 + br[0]; zon[d].append((i + 1, k + 1, top, bot))
        seg2 = C[k + 1:k + 1 + LIFE]; br2 = np.where(seg2 > top)[0] if d == 1 else np.where(seg2 < bot)[0]
        zon[-d].append((k + 1, (k + 2 + br2[0]) if len(br2) else k + 1 + LIFE, top, bot))
Zd = {d: np.array(sorted(v)) for d, v in zon.items()}


def in_zone(i, d, px):
    z = Zd[d]; lo = np.searchsorted(z[:, 0], i - 2 * LIFE - 2); hi = np.searchsorted(z[:, 0], i, side="right")
    s = z[lo:hi]; return bool(((s[:, 1] > i) & (s[:, 3] <= px) & (s[:, 2] >= px)).any())


def measure(i, d):
    e = C[i]; seg = slice(i + 1, i + 1 + W)
    fav = (H[seg] - e) if d == 1 else (e - L[seg]); adv = (e - L[seg]) if d == 1 else (H[seg] - e)
    hitT = np.where(fav >= TGT)[0]; hitS = np.where(adv >= TGT)[0]
    ft = hitT[0] if len(hitT) else W; fs = hitS[0] if len(hitS) else W
    if ft == W and fs == W: r11 = d * (C[i + W] - e)
    elif fs <= ft: r11 = -TGT          # same candle: stop first (conservative)
    else: r11 = TGT
    nostop = TGT if ft < W else d * (C[i + W] - e)
    mfe_before_stop = fav[:fs].max() if fs > 0 else 0.0
    return dict(next5=fav[0] >= TGT, within12=ft < W, pnl_1to1=r11 - COST, pnl_nostop=nostop - COST,
                loss_1to1=fs <= ft and fs < W, mfe_before_stop=mfe_before_stop, worst12=adv.max(), atr=A[i])


rows = []
for i in range(30, n - W - 1):
    for d in (1, -1):
        fvg = (L[i] > H[i - 2]) if d == 1 else (H[i] < L[i - 2])
        size = (L[i] - H[i - 2]) if d == 1 else (L[i - 2] - H[i])
        body = np.sign(C[i] - O[i])
        if fvg and size >= 0.25 * A[i] and not in_zone(i, -d, C[i]):
            rows.append(dict(t=T[i], d=d, kind="FVG", **measure(i, d)))
        elif body == d and i % 7 == 0:   # control sample: every 7th candle closing in that direction
            rows.append(dict(t=T[i], d=d, kind="any candle", **measure(i, d)))
R = pd.DataFrame(rows); R["year"] = R.t.dt.year; R.to_pickle(OUT / f"fvg_next5_{TF}m.pkl")
g = R.groupby(["year", "kind"]).agg(n=("d", "size"), atr=("atr", "median"), next_candle_5=("next5", "mean"),
                                     within_1h_5=("within12", "mean"), pnl_1to1=("pnl_1to1", "mean"), pnl_nostop=("pnl_nostop", "mean"),
                                     worst_1h=("worst12", "median"))
pd.set_option("display.width", 220); print(f"=== {TF}m ==="); print(g.round(3).unstack("kind").to_string())
F = R[R.kind == "FVG"]; Ls = F[F.loss_1to1]
print("\nlosing 1:1 FVG trades:", len(Ls), "of", len(F), "— were in profit first by ≥$1:", (Ls.mfe_before_stop >= 1).mean().round(3),
      "≥$2:", (Ls.mfe_before_stop >= 2).mean().round(3), "≥$3:", (Ls.mfe_before_stop >= 3).mean().round(3), "median $", Ls.mfe_before_stop.median().round(2))
print("all years FVG: next candle +$5", F.next5.mean().round(3), " +$5 within 1h", F.within12.mean().round(3), " $/trade 1:1", F.pnl_1to1.mean().round(3), " no stop", F.pnl_nostop.mean().round(3))
print("worst no-stop trades $:", F.pnl_nostop.nsmallest(5).round(1).tolist())
