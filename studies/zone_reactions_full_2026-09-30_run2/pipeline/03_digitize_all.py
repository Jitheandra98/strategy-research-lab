"""Stage 3 — digitize the 5m pane of every OCR'd frame.

Writes WORK/digitized/frames.jsonl : one record per frame
  {frame_id, seg, n, video_s, ok, why, price_fit, pitch, phase, k_last, labels:[...], bars:[...]}
video_s = segment start + n * FRAME_STEP (recording seconds).
"""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import digitize as D

W = Path(sys.argv[1])
SEGS = {m["seg"]: m for m in json.loads((W / "extract_done.json").read_text())} if (W / "extract_done.json").exists() else {}


def seg_start(s):
    if s in SEGS:
        return SEGS[s]["start"], SEGS[s]["frame_step"]
    m = json.loads((W / f"seg{s}" / "segment.json").read_text()) if (W / f"seg{s}" / "segment.json").exists() else None
    if m:
        return m["start"], m["frame_step"]
    # segment still running: recompute the same grid as 01_extract.py
    seg_len = 13013.12 / 4
    return (int(s * seg_len) // 3) * 3, 3


def work(ocr_path):
    ocr_path = Path(ocr_path)
    seg = int(ocr_path.name.split("_")[0][3:])
    n = int(ocr_path.stem.split("_")[-1])
    frame = W / f"seg{seg}" / "frames" / f"f_{n:06d}.jpg"
    st, step = seg_start(seg)
    rec = {"frame_id": f"seg{seg}_{n:06d}", "seg": seg, "n": n, "video_s": st + n * step}
    try:
        img, items = D.load(frame, ocr_path)
        r = D.digitize(img, items)
    except Exception as e:  # keep going; record the failure
        r = {"ok": False, "why": f"exception: {e!r}"}
    rec.update(r)
    return rec


if __name__ == "__main__":
    out_dir = W / "digitized"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "frames.jsonl"
    done = set()
    if out.exists():
        for line in out.open():
            done.add(json.loads(line)["frame_id"])
    todo = sorted(p for p in (W / "ocr_frames").glob("seg*_f_*.json")
                  if f"{p.name.split('_')[0]}_{int(p.stem.split('_')[-1]):06d}" not in done)
    print(f"todo {len(todo)} (already {len(done)})", flush=True)
    with ProcessPoolExecutor(7) as ex, out.open("a") as f:
        for i, rec in enumerate(ex.map(work, todo, chunksize=8)):
            f.write(json.dumps(rec) + "\n")
            if i % 200 == 0:
                print(i, rec["frame_id"], rec.get("ok"), rec.get("why"), flush=True)
    print("DIGITIZE COMPLETE", flush=True)
