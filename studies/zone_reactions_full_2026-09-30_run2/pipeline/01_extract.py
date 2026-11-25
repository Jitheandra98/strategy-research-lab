"""Stage 1 — decode the full recording once, in parallel segments.

Outputs (under WORK, which lives in scratch space because it is ~10 GB):
  frames/f_<sec*10:06d>.jpg   full 2560x1440 frame every FRAME_STEP seconds
  strips/s_<first_ms:08d>.png header strip mosaics: 40 consecutive 10 fps strips
                              (full-width y=70..116) stacked vertically = 4 s of video
Nothing existing is overwritten (ffmpeg -n; per-segment directories).
"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FF = "/Users/jitheandrasubramaniam/anaconda3/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
VIDEO = next(Path.home().joinpath("Documents").glob("Screen Recording 2026-09-30 at 7.57.42*.mov"))
WORK = Path(sys.argv[1])
DURATION = 13013.12
SEGMENTS = int(sys.argv[2]) if len(sys.argv) > 2 else 4
FRAME_STEP = 3          # seconds between full frames
STRIP_FPS = 10          # header strip sampling
TILE = 40               # strips per mosaic
STRIP_Y, STRIP_H = 70, 46


def run(seg):
    seg_len = DURATION / SEGMENTS
    start = seg * seg_len
    # align segment starts to the frame grid so frame timestamps are exact multiples
    start = (int(start) // FRAME_STEP) * FRAME_STEP
    end = DURATION if seg == SEGMENTS - 1 else ((int((seg + 1) * seg_len)) // FRAME_STEP) * FRAME_STEP
    d = WORK / f"seg{seg}"
    (d / "frames").mkdir(parents=True, exist_ok=True)
    (d / "strips").mkdir(parents=True, exist_ok=True)
    fc = (f"[0:v]split=2[a][b];"
          f"[a]fps=1/{FRAME_STEP}:round=down[fa];"
          f"[b]fps={STRIP_FPS},crop=2560:{STRIP_H}:0:{STRIP_Y},tile=1x{TILE}[fb]")
    cmd = [FF, "-nostdin", "-hide_banner", "-loglevel", "error", "-hwaccel", "videotoolbox",
           "-ss", str(start), "-t", str(end - start), "-i", str(VIDEO), "-an",
           "-filter_complex", fc,
           "-map", "[fa]", "-q:v", "2", "-start_number", "0", "-n", str(d / "frames" / "f_%06d.jpg"),
           "-map", "[fb]", "-start_number", "0", "-n", str(d / "strips" / "s_%06d.png")]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    meta = {"seg": seg, "start": start, "end": end, "rc": r.returncode, "stderr": r.stderr[-2000:],
            "elapsed": time.time() - t0, "frame_step": FRAME_STEP, "strip_fps": STRIP_FPS, "tile": TILE,
            "strip_y": STRIP_Y, "strip_h": STRIP_H}
    (d / "segment.json").write_text(json.dumps(meta, indent=2))
    print(f"seg{seg} {start:.0f}-{end:.0f}s rc={r.returncode} {meta['elapsed']:.0f}s", flush=True)
    return meta


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(SEGMENTS) as ex:
        metas = list(ex.map(run, range(SEGMENTS)))
    (WORK / "extract_done.json").write_text(json.dumps(metas, indent=2))
    print("EXTRACT COMPLETE", flush=True)
