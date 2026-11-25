"""Stage 4b: read the live price (15m pane SELL box, top-left, fixed position) from every half-res frame.
The SELL box always shows the newest price, even when the crosshair makes the header show an older bar.
Crops are upscaled x3 and read with Vision (accurate). Follows the extractor; never overwrites."""
import subprocess, sys, time
from pathlib import Path
from PIL import Image
import pandas as pd
W = Path(sys.argv[1]); HERE = Path(__file__).parent
while True:
    left = False
    for v in (1, 2, 3):
        fd = W / f"v{v}/frames"; cd = W / f"v{v}/sell_crops"; od = W / f"v{v}/sell_ocr"
        cd.mkdir(exist_ok=True); od.mkdir(exist_ok=True)
        done = "DONE" in (W / f"extract_v{v}.log").read_text() if (W / f"extract_v{v}.log").exists() else False
        frames = sorted(fd.glob("f_*.jpg"))
        # only frames whose header is a complete bar (H != L) can be hovered; flat headers are always the newest bar
        try:
            pf = pd.read_csv(W / "frames_parsed.csv", usecols=["video", "kf", "h15", "l15"])
            need = set(pf[(pf.video == v) & ~(pf.h15 == pf.l15)].kf)
            known = set(pf[pf.video == v].kf)
            frames = [f for f in frames if int(f.stem[2:]) in need or int(f.stem[2:]) not in known]
        except FileNotFoundError:
            pass
        if not done:
            frames = frames[:-2]; left = True
        todo = []
        for f in frames:
            if (od / f"{f.stem}.json").exists():
                continue
            c = cd / f"{f.stem}.png"
            if not c.exists():
                try:
                    im = Image.open(f).crop((62, 126, 152, 146))
                    im.resize((270, 60), Image.LANCZOS).save(c)
                except Exception:
                    continue
            todo.append(str(c))
        if todo:
            left = True
            for i in range(0, len(todo), 2000):
                (W / f"v{v}/sell_todo.txt").write_text("\n".join(todo[i:i + 2000]))
                subprocess.run([str(HERE / "vision_ocr2"), str(W / f"v{v}/sell_todo.txt"), str(od)],
                               env={"OCR_PAR": "3"}, capture_output=True)
                print(time.strftime("%X"), v, i + 2000, len(todo), flush=True)
    if not left:
        print("SELL_ALL_DONE", flush=True); break
    time.sleep(30)
