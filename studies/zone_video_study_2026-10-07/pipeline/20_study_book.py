"""Stage 20: STUDY BOOK — real Box-to-Box setups from the owner's videos, with the actual chart screenshots.
Random draw (seed 7) of N wins and N losses among setups whose trigger bar was shown on screen, so the book is not
cherry-picked. For each: frame at the entry and a frame ~4 h later, plus level / entry / stop / target / result.
usage: 20_study_book.py <work_dir> <out_dir> [n_each]"""
import base64, io, sys
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image, ImageDraw

W, OUT = Path(sys.argv[1]), Path(sys.argv[2]); N = int(sys.argv[3]) if len(sys.argv) > 3 else 12
OUT.mkdir(parents=True, exist_ok=True)
R = pd.read_pickle(W / "box2box_full.pkl"); R = R[R.src == "real"].copy()
rev = pd.read_pickle(W / "bar_reveal.pkl")
R["bar"] = R.trig_time.dt.floor("15min")
R = R[R.bar.map(lambda b: b in rev)]
R["video"] = R.bar.map(lambda b: sorted(rev[b])[0][0])
fr = pd.read_csv(W / "frames_dated.csv", usecols=["video", "kf", "t", "bar_utc"], parse_dates=["bar_utc"], low_memory=False)
fr = fr[fr.bar_utc.notna()].sort_values(["video", "t"])
rng = np.random.default_rng(7)
pick = pd.concat([g.iloc[rng.choice(len(g), min(N, len(g)), replace=False)] for _, g in R.groupby("win")]).sort_values("time")


def frame_at(v, when):
    g = fr[(fr.video == v) & (fr.bar_utc >= when)]
    if not len(g): return None, None
    r = g.iloc[0]
    if (r.bar_utc - when) > pd.Timedelta(hours=2): return None, None
    return int(r.kf), float(r.t)


def hms(s): s = int(round(s)); return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def img64(v, kf, label):
    im = Image.open(W / f"v{v}/frames/f_{kf:06d}.jpg").convert("RGB")
    im = im.resize((1100, int(im.height * 1100 / im.width)), Image.LANCZOS)
    d = ImageDraw.Draw(im); d.rectangle([0, 0, 360, 26], fill=(0, 0, 0)); d.text((8, 7), label, fill=(255, 255, 0))
    b = io.BytesIO(); im.save(b, "JPEG", quality=72); return base64.b64encode(b.getvalue()).decode()


cards = []; n = 0
for r in pick.itertuples():
    k1, t1 = frame_at(r.video, r.bar)
    k2, t2 = frame_at(r.video, r.bar + pd.Timedelta(hours=4))
    if k1 is None: continue
    n += 1
    side = "SELL" if r.dir == -1 else "BUY"
    lk = {"top": "box TOP", "ce": "box MIDDLE (CE)", "bot": "box BOTTOM"}[r.lkind]
    res = "WIN" if r.win == 1 else ("LOSS" if r.R <= -0.9 else "TIME EXIT")
    ny = r.trig_time.tz_convert("America/New_York").strftime("%a %d %b %Y %H:%M")
    imgs = f'<img src="data:image/jpeg;base64,{img64(r.video, k1, f"ENTRY  V{r.video} {hms(t1)}")}">'
    if k2 is not None:
        imgs += f'<img src="data:image/jpeg;base64,{img64(r.video, k2, f"+4 HOURS  V{r.video} {hms(t2)}")}">'
    cards.append(f"""<section class="card {res.lower().replace(' ', '')}">
<h2>#{n} · {side} at the 4H {lk} · <span class="res">{res} {r.R:+.2f}R</span></h2>
<p><b>Video V{r.video} at {hms(t1)}</b> (chart time {ny} NY) · level {r.level:,.2f} · entry {r.entry:,.2f} · stop {r.stop:,.2f}
· target {r.target:,.2f} (next 4H level, {r.tgt_R:.1f}R) · with 4H trend: {"yes" if r.trend4 == r.dir else "no"}</p>
<p class="what">What happened: price came {"up" if r.dir == -1 else "down"} into the 4H {lk} at {r.level:,.2f}; the 3m then closed
{"below the last 3m swing low" if r.dir == -1 else "above the last 3m swing high"} → entry. Result: {res.lower()} ({r.R:+.2f}R after 0.30 pt cost).</p>
{imgs}</section>""")

wins = (pick.win == 1).sum(); allw = R.win.mean(); allr = R.R.mean()
html = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Box-to-Box Study Book</title><style>
:root{{--bg:#111;--fg:#eee;--mut:#aaa;--win:#2e7d32;--loss:#c62828;--card:#1b1b1b}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,system-ui,sans-serif;max-width:1150px;margin:0 auto;padding:16px}}
h1{{margin:.2em 0}} .card{{background:var(--card);border-left:6px solid #777;padding:12px 16px;margin:22px 0;border-radius:8px}}
.card.win{{border-color:var(--win)}} .card.loss{{border-color:var(--loss)}} .res{{font-weight:700}}
.win .res{{color:#66bb6a}} .loss .res{{color:#ef5350}} img{{width:100%;margin:8px 0;border-radius:6px}} .what{{color:var(--mut)}}
.box{{background:#222;padding:12px 16px;border-radius:8px}}</style></head><body>
<h1>Box-to-Box Study Book</h1>
<div class="box"><p>Real moments from your three replay videos (V1, V2, V3) where price reached a STATION2 <b>4H box</b> (top, middle or bottom)
and the <b>3m rejection</b> triggered an entry (rules: <code>live_watch/STRATEGY_BOX_TO_BOX_3M.md</code>).
Each card shows the chart <b>at the entry</b> and <b>4 hours later</b>, with the video timestamp so you can open the video and watch it yourself.</p>
<p>This book is a fair sample, not a highlight reel: <b>{N} wins and {N} losses drawn at random</b> from the {len(R):,} setups that
happened on bars shown in your videos. Across all of them: win rate <b>{allw:.0%}</b>, average <b>{allr:+.2f}R</b> per trade after costs.
Study what the winners have that the losers don't.</p>
<p>Left pane in these videos is 15m (the 3m entries are inside those candles); right pane is 4H.</p></div>
{''.join(cards)}</body></html>"""
(OUT / "STUDY_BOOK.html").write_text(html)
print("cards", n, "file", OUT / "STUDY_BOOK.html", round((OUT / "STUDY_BOOK.html").stat().st_size / 1e6, 1), "MB")
