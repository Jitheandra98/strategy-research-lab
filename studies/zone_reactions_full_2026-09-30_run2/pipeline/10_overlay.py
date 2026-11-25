"""Stage 10 — visual fidelity check + annotated examples.

overlay  : draw the reconstructed engine's live 5m zones (as of the frame's last bar) on the video
           frame with thin outlines, so they can be compared with the indicator's own boxes.
example  : crop a frame around an event and annotate zone, arrival, confirmation, entry/stop.
Usage: python 10_overlay.py WORK OUT overlay <frame_id> [...]
       python 10_overlay.py WORK OUT example <event_row_index> [...]
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

W, OUT, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
SHOTS = OUT / "screenshots"
SHOTS.mkdir(exist_ok=True)
FONT = ImageFont.load_default()
recs = {}
for line in (W / "digitized" / "frames.jsonl").open():
    r = json.loads(line)
    recs[r["frame_id"]] = r
fmap = pd.read_json(W / "stitched" / "frame_map.jsonl", lines=True).set_index("frame_id")
bars = pd.read_csv(OUT / "data" / "bars_5m.csv")
bars["time_ct"] = pd.to_datetime(bars.time_ct, utc=True).dt.tz_convert("America/Chicago")
key = {(c, g): i for i, (c, g) in enumerate(zip(bars.chain, bars.g))}
zones = pd.read_csv(OUT / "zones.csv")


def frame_geom(fid):
    r, fm = recs[fid], fmap.loc[fid]
    pf = r["price_fit"]
    y = lambda p: (p - pf["a"]) / pf["b"]
    # bar index i (row in bars) -> x pixel, via g = k + off
    def x_of(i):
        g = bars.g.iloc[i]
        k = g - fm.off
        return r["phase"] + k * r["pitch"]
    return r, fm, y, x_of


def overlay(fid):
    r, fm, y, x_of = frame_geom(fid)
    i_last = key.get((fm.chain, int(fm.g_last)))
    img = Image.open(W / f"seg{r['seg']}" / "frames" / f"f_{r['n']:06d}.jpg").convert("RGB")
    d = ImageDraw.Draw(img)
    x_right = r["layout"]["axis_x"] - 8
    live = zones[(zones.tf == "5m") & (zones.born_i <= i_last) &
                 (zones.end_i.isna() | (zones.end_i > i_last))]
    shown = 0
    for z in live.itertuples():
        state = "ACTIVE"
        if pd.notna(z.consumed_i) and z.consumed_i <= i_last:
            state = "INVERTED" if pd.notna(z.inverted_i) and z.inverted_i <= i_last else "CONSUMED"
        elif pd.notna(z.first_touch_i) and z.first_touch_i <= i_last:
            state = "TOUCHED"
        if state == "CONSUMED":
            continue
        x0 = max(r["layout"]["plot_x0"], x_of(int(z.born_i)))
        y0, y1 = y(z.top), y(z.bot)
        if y1 < r["layout"]["plot_y0"] or y0 > r["layout"]["plot_y1"]:
            continue
        col = (255, 255, 0) if z.dir == 1 else (255, 0, 255)
        d.rectangle([x0, y0, x_right, y1], outline=col, width=2)
        d.text((x_right - 150, y0 + 1), f"{z.kind} {state[:3]}", fill=col, font=FONT)
        shown += 1
    t = bars.time_ct.iloc[i_last]
    d.text((70, 1300), f"RECONSTRUCTED ENGINE OVERLAY  frame {fid}  last bar {t:%Y-%m-%d %H:%M} CT  "
                       f"yellow=demand magenta=supply ({shown} live zones)", fill=(255, 255, 0), font=FONT)
    out = SHOTS / f"overlay_{fid}.jpg"
    img.crop((0, 60, r["layout"]["axis_x"] + 90, 1330)).save(out, quality=90)
    return out


def example(ev_idx):
    ev = pd.read_csv(OUT / "events.csv").iloc[ev_idx]
    i = int(ev.i)
    c, g = bars.chain.iloc[i], bars.g.iloc[i]
    # pick a frame that shows bar i with ~40 bars after it and the clean view
    cands = fmap[(fmap.chain == c) & (fmap.g_last >= g + 30)].sort_values("g_last")
    if not len(cands):
        return None
    fid = cands.index[0]
    r, fm, y, x_of = frame_geom(fid)
    img = Image.open(W / f"seg{r['seg']}" / "frames" / f"f_{r['n']:06d}.jpg").convert("RGB")
    d = ImageDraw.Draw(img)
    x_i = x_of(i)
    col = (255, 255, 0) if ev.dir == 1 else (255, 0, 255)
    d.rectangle([x_i - 60, y(ev.top), x_i + 240, y(ev.bot)], outline=col, width=3)
    d.line([x_i, y(ev.top) - 40, x_i, y(ev.bot) + 40], fill=(0, 255, 255), width=1)
    txt = (f"{ev.zone_tf} {ev.zone_kind} {'DEMAND' if ev.dir == 1 else 'SUPPLY'} arrival #{int(ev.arrival_no)}  "
           f"{pd.to_datetime(ev.time_ct):%Y-%m-%d %H:%M} CT  reaction={ev.reaction}")
    d.text((x_i - 60, y(ev.top) - 55), txt, fill=col, font=FONT)
    d.text((x_i - 60, y(ev.top) - 42), f"video {ev.video_ts}", fill=col, font=FONT)
    # the Setup-A trade on this event, if any: entry (white), stop (red), 2R target (green)
    try:
        pt = pd.read_csv(OUT / "analysis" / "portfolio_trades_A_2R.csv")
        m = pt[(pt.zone_uid == ev.zone_uid) & (pt.event_i == ev.i)]
        if len(m):
            t = m.iloc[0]
            xe = x_of(int(t.entry_i))
            tgt = t.entry + t.tdir * 2 * t.risk_pts
            for price, cl, lab in ((t.entry, (255, 255, 255), "entry"), (t.stop, (255, 60, 60), "stop"),
                                   (tgt, (60, 255, 120), "2R target")):
                d.line([xe, y(price), xe + 220, y(price)], fill=cl, width=2)
                d.text((xe + 224, y(price) - 6), lab, fill=cl, font=FONT)
            d.text((x_i - 60, y(ev.top) - 29), f"Setup A result {t.R:+.2f}R ({t.exit2})", fill=(255, 255, 255), font=FONT)
    except FileNotFoundError:
        pass
    x0 = int(max(60, x_i - 420)); x1 = int(min(r["layout"]["axis_x"] + 80, x_i + 420))
    yc = (y(ev.top) + y(ev.bot)) / 2
    y0 = int(max(70, yc - 380)); y1 = int(min(1320, yc + 380))
    out = SHOTS / f"example_{ev_idx}_{ev.zone_kind}_{ev.reaction}.jpg"
    img.crop((x0, y0, x1, y1)).save(out, quality=90)
    return out


if __name__ == "__main__":
    for a in sys.argv[4:]:
        print(overlay(a) if mode == "overlay" else example(int(a)))
