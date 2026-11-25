"""Fast digitizer check: each frame against ITS OWN 4H header (no stitching involved).

For every sampled frame: digitize, assign time-of-day from its labels, take the bars of the
current 4H bucket (session grid), align the end on the header's typed close, compare O/H/L.
Usage: python val_frames.py WORK [step] [variant-tag]
"""
import importlib.util, json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import digitize as D

spec = importlib.util.spec_from_file_location("st", HERE / "04_stitch.py")
W = Path(sys.argv[1])
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 10
_argv = sys.argv
sys.argv = [sys.argv[0], str(W)]
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
sys.argv = _argv
STARTS = {17 * 60, 21 * 60, 1 * 60, 5 * 60, 9 * 60, 13 * 60}


def one(p):
    p = Path(p)
    seg, n = p.stem.split("_f_")
    img, items = D.load(W / seg / "frames" / f"f_{n}.jpg", p)
    r = D.digitize(img, items)
    if not r.get("ok") or not r["headers"].get("4h"):
        return None
    r["frame_id"] = p.stem
    tod = st.frame_tod(r)
    bars = {b["k"]: b for b in r["bars"] if b["k"] in tod}
    kl = r["k_last"]
    if kl not in tod:
        return None
    # walk back to the bucket start
    k = kl
    while k in tod and tod[k] not in STARTS:
        k -= 1
    if k not in tod or k not in bars:
        return None
    ks = [kk for kk in range(k, kl + 1) if kk in bars]
    O, H, L, C = r["headers"]["4h"]
    # align on close (4H pane may lag): candidate ends in the last 12 bars
    best = None
    for e in ks[-12:]:
        if bars[e]["close"] is None:
            continue
        d = abs(bars[e]["close"] - C)
        if best is None or d < best[0]:
            best = (d, e)
    if best is None or best[0] > 0.5:
        return None
    sel = [bars[kk] for kk in ks if kk <= best[1]]
    if sel[0]["open"] is None or abs(sel[0]["open"] - O) > 0.5:
        return None                              # misaligned bucket start: skip, not a H/L test
    return dict(frame=p.stem, dH=max(b["high"] for b in sel) - H, dL=min(b["low"] for b in sel) - L,
                n=len(sel), lab=any("label" in b["flags"] for b in sel))


if __name__ == "__main__":
    files = sorted((W / "ocr_frames").glob("seg*_f_*.json"))[::STEP]
    with ProcessPoolExecutor(7) as ex:
        res = [x for x in ex.map(one, files, chunksize=4) if x]
    dH = np.array([x["dH"] for x in res])
    dL = np.array([x["dL"] for x in res])
    lab = np.array([x["lab"] for x in res])
    def s(a):
        return f"n={len(a)} |d|<=0.3:{(np.abs(a)<=.3).mean():.3f} <=1:{(np.abs(a)<=1).mean():.3f} short>1:{(a*1<-1).mean():.3f}"
    print("HIGH", s(dH), " (short = our high too low)")
    print("LOW ", s(-dL), " (short = our low too high)")
    print("clean-bucket HIGH", s(dH[~lab]), "| label-bucket HIGH", s(dH[lab]))
    tag = sys.argv[3] if len(sys.argv) > 3 else "cur"
    Path(W / f"valframes_{tag}.json").write_text(json.dumps(res))
