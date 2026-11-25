"""Stage 8: do the engine's zones line up with the boxes drawn on screen?

For a sample of dated frames: OCR the half-res frame, fit price->pixel on each pane's price axis (log scale, robust),
project every engine zone that should be on screen at that bar, and test for a horizontal box border at the predicted
top and bottom edge in the empty strip just left of the price axis (boxes extend right; candles do not reach there).
A border "hit" = the strongest row within +-2 px of the prediction is in the top 10% of that strip's rows.
Control: the same test at the prediction shifted by a random 6-20 px (what chance alone gives).
usage: 08_zone_check.py <work> <build_dir> <video> [every_n]
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image

W = Path(sys.argv[1]); B = Path(sys.argv[2]); V = int(sys.argv[3]); N = int(sys.argv[4]) if len(sys.argv) > 4 else 25
HERE = Path(__file__).parent
rng = np.random.default_rng(7)
fr = pd.read_csv(W / "frames_dated.csv", parse_dates=["bar_utc"])
fr = fr[(fr.video == V) & fr.bar_utc.notna()].iloc[::N]
z15 = pd.read_pickle(B / "zones15.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl")
h4 = pd.read_pickle(B / "bars4h.pkl")
fr = fr[(fr.bar_utc >= pd.read_pickle(B / "bars15.pkl").index[300])]
# OCR the sampled frames (accurate mode)
od = W / f"v{V}/ocr_full"; od.mkdir(exist_ok=True)
todo = [str(W / f"v{V}/frames/f_{k:06d}.jpg") for k in fr.kf if not (od / f"f_{k:06d}.json").exists()]
if todo:
    (od / "todo.txt").write_text("\n".join(todo))
    subprocess.run([str(HERE / "vision_ocr2"), str(od / "todo.txt"), str(od)], env={"OCR_PAR": "3"}, capture_output=True)


def num(t):
    t = t.replace(",", "").replace(" ", "")
    if t.count(".") > 1:
        t = t.replace(".", "", t.count(".") - 1)
    try:
        return float(t)
    except ValueError:
        return None


def axis_fit(items, x0, x1):
    pts = [(num(i["text"]), i["y"] + i["h"] / 2) for i in items if x0 <= i["x"] <= x1]
    pts = [(p, y) for p, y in pts if p and 500 < p < 5000 and 75 < y < 745]
    if len(pts) < 4:
        return None
    p = np.log([a for a, _ in pts]); y = np.array([b for _, b in pts])
    best = None
    for _ in range(60):  # RANSAC on pairs
        i, j = rng.choice(len(p), 2, replace=False)
        if p[i] == p[j]:
            continue
        b = (y[i] - y[j]) / (p[i] - p[j]); a = y[i] - b * p[i]
        inl = np.abs(a + b * p - y) < 1.5
        if best is None or inl.sum() > best[0]:
            best = (inl.sum(), inl)
    if best[0] < 4:
        return None
    b, a = np.polyfit(p[best[1]], y[best[1]], 1)
    return a, b, int(best[0])


def edge_scores(img, x0, x1):
    s = img[:, x0:x1, :].astype(float)
    d = np.abs(np.diff(s, axis=0)).max(axis=2).mean(axis=1)   # row y vs y+1
    sc = np.zeros(img.shape[0]); sc[1:-1] = np.maximum(d[:-1], d[1:])
    return sc


rows = []
for _, f in fr.iterrows():
    j = od / f"f_{int(f.kf):06d}.json"
    if not j.exists():
        continue
    items = json.loads(j.read_text()).get("items", [])
    sx = f.split_x / 2  # half-res
    img = np.asarray(Image.open(W / f"v{V}/frames/f_{int(f.kf):06d}.jpg").convert("RGB"))
    panes = {"15m": (sx - 95, sx - 15), "4h": (1290, 1395)}
    for pane, (ax0, ax1) in panes.items():
        fit = axis_fit(items, ax0, ax1)
        if fit is None:
            continue
        a, b, nin = fit
        axis_x = int(min(i["x"] for i in items if ax0 <= i["x"] <= ax1 and num(i["text"])))
        strip = (axis_x - 55, axis_x - 6)
        sc = edge_scores(img, *strip)
        valid = sc[85:740]; thr = np.quantile(valid, 0.90)
        t = f.bar_utc
        if pane == "15m":
            zz = z15[(z15.born_time <= t) & (z15.end_time.isna() | (z15.end_time > t))]
        else:
            z4v = z4.copy(); z4v["vis"] = z4v.born_time.map(lambda x: h4.avail.get(x, pd.NaT))
            zz = z4v[(z4v.vis <= t) & (z4v.end_time.isna() | (z4v.end_time > t))]
        # state at time t: consumed (state 2) boxes are drawn ~invisible (gray 96/80 transparency) -> skip them
        cons = zz.consumed_time.notna() & (zz.consumed_time <= t)
        inv = zz.inverted_time.notna() & (zz.inverted_time <= t)
        zz = zz.assign(state_t=np.where(inv, "INVERTED", np.where(cons, "CONSUMED", "LIVE")))
        zz = zz[zz.state_t != "CONSUMED"]
        for _, z in zz.iterrows():
            for edge, price in (("top", z.top), ("bot", z.bot)):
                y = a + b * np.log(price)
                if not (90 < y < 735):
                    continue
                yi = int(round(y))
                hit = sc[yi - 2:yi + 3].max() >= thr
                off = int(rng.choice([-1, 1]) * rng.integers(6, 21))
                yc = yi + off
                ctrl = sc[yc - 2:yc + 3].max() >= thr if 90 < yc < 735 else np.nan
                rows.append(dict(video=V, kf=int(f.kf), t=f.t, bar_utc=t, pane=pane, zid=z.zid, kind=z.kind,
                                 state=z.state_t, edge=edge, price=price, y=y, hit=hit, ctrl=ctrl, axis_inliers=nin))
res = pd.DataFrame(rows)
res.to_csv(W / f"zone_check_v{V}.csv", index=False)
print(f"v{V}: frames={res.kf.nunique()} edges={len(res)}")
print(res.groupby(["pane", "kind", "state"]).agg(n=("hit", "size"), hit=("hit", "mean"), chance=("ctrl", "mean")).round(3))
