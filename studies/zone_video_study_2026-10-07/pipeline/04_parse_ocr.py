"""Stage 4: parse OCR'd text bands into one row per keyframe.
Columns: video, kf, t (s into video), ok (TradingView 2-pane layout seen), split_x (x of 4h title, native px),
o15,h15,l15,c15 (15m header), o4,h4,l4,c4 (4H header), xh15/xh4 (crosshair date labels, if any)."""
import json, re, sys
from pathlib import Path
import pandas as pd
W = Path(sys.argv[1])
PRICE = re.compile(r"([OHLC])\s*[-|]?\s*(\d)[.,]?(\d{3})[.,](\d{3})")
LEAD0 = re.compile(r"(?:^|[\s,])0\s?(\d)[.,](\d{3})[.,](\d{3})")  # 'O' read as '0'
DATE = re.compile(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s*(\d{1,2})\s*([A-Z][a-z]{2})\s*'?\s*(\d{2})\s*(\d{1,2}:\d{2})?")

def ohlc(text):
    t = text.replace("O1", "O 1").replace("01.", "O 1.").replace("01,", "O 1,")
    vals = {}
    for k, a, b, c in PRICE.findall(t):
        vals.setdefault(k, float(f"{a}{b}.{c}"))
    if "O" not in vals:
        m = LEAD0.search(text)
        if m: vals["O"] = float(f"{m.group(1)}{m.group(2)}.{m.group(3)}")
    return vals

rows = []
for v in (1, 2, 3):
    pts = [float(x.strip(",")) for x in (W / f"v{v}/kf_pts.csv").read_text().split() if x.strip(",")]
    for j in sorted((W / f"v{v}/ocr").glob("b_*.json")):
        k = int(j.stem[2:]); d = json.loads(j.read_text())
        r = dict(video=v, kf=k, t=pts[k - 1] if k - 1 < len(pts) else None, ok=False)
        items = d.get("items", [])
        t15 = [i for i in items if i["y"] < 30 and re.search(r"15\s*[•·.]\s*OANDA", i["text"])]
        t4 = [i for i in items if i["y"] < 30 and re.search(r"4h\s*[•·.]?\s*OANDA", i["text"])]
        if t15 and t4:
            r["ok"] = True; sx = t4[0]["x"] - 120; r["split_x"] = round(sx)
            row = [i for i in items if 35 < i["y"] < 75]
            left = " ".join(i["text"] for i in sorted(row, key=lambda i: i["x"]) if i["x"] < sx)
            right = " ".join(i["text"] for i in sorted(row, key=lambda i: i["x"]) if i["x"] >= sx)
            for suf, txt in (("15", left), ("4", right)):
                vals = ohlc(txt)
                for kk in "OHLC":
                    r[kk.lower() + suf] = vals.get(kk)
            axis = [i for i in items if i["y"] >= 85]
            for i in axis:
                m = DATE.search(i["text"])
                if m and m.group(5):
                    key = "xh15" if i["x"] < sx else "xh4"
                    r[key] = f"{m.group(2)} {m.group(3)} 20{m.group(4)} {m.group(5)}"
                elif m:
                    key = "xd15" if i["x"] < sx else "xd4"
                    r[key] = f"{m.group(2)} {m.group(3)} 20{m.group(4)}"
            r["axis15"] = "|".join(i["text"] for i in sorted(axis, key=lambda i: i["x"]) if i["x"] < sx)
        rows.append(r)
df = pd.DataFrame(rows).sort_values(["video", "kf"])
df.to_csv(W / "frames_parsed.csv", index=False)
print(df.groupby("video").agg(n=("kf", "size"), ok=("ok", "mean"), o15=("o15", lambda s: s.notna().mean()),
      c4=("c4", lambda s: s.notna().mean()), xh=("xh15", lambda s: s.notna().mean())))
