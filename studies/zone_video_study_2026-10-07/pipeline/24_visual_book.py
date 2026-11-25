"""Stage 24: VISUAL BOOK — charts drawn from the price data for (a) big moves from the videos with the perfect entry,
the realistic 3m entry, stop and where the move ended; (b) look-alikes: the same picture (sweep + reclaim, at a 4H box)
taken live, where the stop was hit. Random draws (seed 11), not hand-picked.
usage: 24_visual_book.py <build_dir> <work_dir> <bigmoves_dir> <out_dir> [n_big] [n_fail]"""
import base64, io, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

B, W, BM, OUT = (Path(x) for x in sys.argv[1:5]); OUT.mkdir(parents=True, exist_ok=True)
NB = int(sys.argv[5]) if len(sys.argv) > 5 else 16; NF = int(sys.argv[6]) if len(sys.argv) > 6 else 10
b = pd.read_pickle(B / "bars15.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl"); h4 = pd.read_pickle(B / "bars4h.pkl")
h4["avail"] = pd.to_datetime(h4.avail)
zav = z4.born_time.map(lambda x: h4.avail.get(x, pd.NaT))
zend = (z4.end_time + pd.Timedelta(hours=4)).fillna(pd.Timestamp("2100-01-01", tz="UTC"))
S = pd.read_pickle(BM / "big_moves.pkl"); S = S[S.real_entry.notna()]
F = pd.read_pickle(B / "sweep_trades_full.pkl"); rev = pd.read_pickle(W / "bar_reveal.pkl")
F["bar"] = F.time.dt.floor("15min"); F = F[F.bar.map(lambda x: x in rev) & F.at_box & (F.R_2R <= -0.9)]
rng = np.random.default_rng(11)
SB = S.iloc[rng.choice(len(S), min(NB, len(S)), replace=False)].sort_values("turn_time")
SF = F.iloc[rng.choice(len(F), min(NF, len(F)), replace=False)].sort_values("time")


def hms(s): s = int(round(s)); return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def chart(t0, t1, marks, title):
    w = b.loc[t0:t1]
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=90); fig.patch.set_facecolor("#111"); ax.set_facecolor("#111")
    x = np.arange(len(w))
    lo, hi = w.low.min(), w.high.max(); pad = (hi - lo) * 0.15
    alive = (zav <= w.index[0]) & (zend > w.index[0])
    for _, z in z4[alive].iterrows():
        if z.top < lo - pad or z.bot > hi + pad: continue
        col = "#2e7d32" if z.dir == 1 else "#c62828"
        ax.add_patch(Rectangle((0, z.bot), len(w), z.top - z.bot, color=col, alpha=0.13, lw=0))
        ax.axhline((z.top + z.bot) / 2, color=col, alpha=0.35, lw=0.6, ls=":")
    up = w.close >= w.open
    ax.vlines(x, w.low, w.high, color=np.where(up, "#9ccc65", "#ef5350"), lw=0.8)
    ax.bar(x, (w.close - w.open).abs().clip(lower=0.05), bottom=np.minimum(w.open, w.close),
           color=np.where(up, "#9ccc65", "#ef5350"), width=0.7)
    for (tm, px, lab, col, mk) in marks:
        if tm is None: ax.axhline(px, color=col, lw=1, ls="--"); ax.text(1, px, f" {lab} {px:,.1f}", color=col, va="bottom", fontsize=8); continue
        i = w.index.get_indexer([tm.floor("15min")], method="nearest")[0]
        ax.plot(i, px, marker=mk, color=col, ms=10); ax.annotate(lab, (i, px), color=col, fontsize=8, xytext=(6, 6), textcoords="offset points")
    ax.set_ylim(lo - pad, hi + pad); ax.tick_params(colors="#aaa", labelsize=8)
    ticks = np.linspace(0, len(w) - 1, 6).astype(int)
    ax.set_xticks(ticks); ax.set_xticklabels([w.index[k].tz_convert("America/New_York").strftime("%d %b %H:%M") for k in ticks])
    ax.set_title(title, color="#eee", fontsize=10, loc="left")
    for s in ax.spines.values(): s.set_color("#333")
    buf = io.BytesIO(); fig.tight_layout(); fig.savefig(buf, format="png", facecolor="#111"); plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


cards = []
for k, r in enumerate(SB.itertuples(), 1):
    dirn = 1 if r.dir == "UP" else -1
    t0 = r.turn_time - pd.Timedelta(hours=18); t1 = min(r.end_time + pd.Timedelta(hours=3), r.turn_time + pd.Timedelta(days=4))
    ing = ", ".join([s for s, f in (("at " + str(r.box), r.at_box), ("sweep of the old " + ("low" if dirn == 1 else "high"), r.sweep),
                                     ("3m displacement + FVG", r.disp), ("near a 4H open", r.h4open)) if f]) or "none of the ICT ingredients"
    marks = [(r.turn_time, r.start, "PERFECT entry", "#ffeb3b", "o"), (r.real_entry_time, r.real_entry, "REALISTIC 3m entry", "#29b6f6", "^" if dirn == 1 else "v"),
             (None, r.stop, "stop", "#ef5350", None), (r.end_time, r.end, "move ended", "#ab47bc", "s")]
    img = chart(t0, t1, marks, f"#{k} {r.dir} move {r.move:,.0f} pts · video V{r.video} {hms(r.video_t)}")
    cards.append(f"""<section class="card win"><h2>Big move #{k}: {r.dir} {r.move:,.0f} pts in {r.hours:.0f} h</h2>
<p><b>Video V{r.video} at {hms(r.video_t)}</b> · turn {r.turn_time.tz_convert('America/New_York'):%a %d %b %Y %H:%M} NY ({r.session})</p>
<p>At the turn: <b>{ing}</b>.<br>Perfect entry {r.start:,.2f} · realistic 3m entry {r.real_entry:,.2f}
({(r.real_entry_time - r.turn_time).total_seconds() / 60:.0f} min later) · stop {r.stop:,.2f} · move ended {r.end:,.2f}
→ from the realistic entry: <b>{r.R_to_end:+.1f}R</b>, {r.captured:.0%} of the move.</p><img src="data:image/png;base64,{img}"></section>""")
fcards = []
for k, r in enumerate(SF.itertuples(), 1):
    marks = [(r.time, r.entry, "entry (sweep + reclaim at 4H box)", "#29b6f6", "^" if r.dir == 1 else "v"),
             (None, r.stop, "stop", "#ef5350", None)]
    v, vt, _ = sorted(rev[r.bar])[0]
    img = chart(r.time - pd.Timedelta(hours=18), r.time + pd.Timedelta(hours=18), marks,
                f"Look-alike #{k} · {'BUY' if r.dir == 1 else 'SELL'} · video V{v} {hms(vt)}")
    fcards.append(f"""<section class="card loss"><h2>Look-alike #{k}: same picture, {'BUY' if r.dir == 1 else 'SELL'} → stopped out</h2>
<p><b>Video V{v} at {hms(vt)}</b> · {r.time.tz_convert('America/New_York'):%a %d %b %Y %H:%M} NY · sweep of the old {'low' if r.dir == 1 else 'high'}
at a 4H box, 15m closed back → entry {r.entry:,.2f}, stop {r.stop:,.2f} → <b>stop hit</b> ({r.R_2R:+.2f}R).</p>
<img src="data:image/png;base64,{img}"></section>""")
Lk = pd.read_csv(BM / "lookalikes.csv")
tbl = "".join(f"<tr><td>{r.picture}</td><td>{r.turns_with_this_picture:,}</td><td>{r.became_big_move:,}</td><td>{r.share_big:.0%}</td></tr>" for r in Lk.itertuples())
html = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Big Moves Visual Book</title><style>
body{{background:#111;color:#eee;font:15px/1.5 -apple-system,system-ui,sans-serif;max-width:1050px;margin:0 auto;padding:16px}}
.card{{background:#1b1b1b;border-left:6px solid #777;padding:10px 16px;margin:20px 0;border-radius:8px}} .win{{border-color:#2e7d32}} .loss{{border-color:#c62828}}
img{{width:100%;border-radius:6px}} table{{border-collapse:collapse}} td,th{{border:1px solid #333;padding:4px 10px}} .box{{background:#222;padding:12px 16px;border-radius:8px}}
</style></head><body><h1>Big Moves Visual Book</h1>
<div class="box"><p>Built from what price did in your three videos (Sep 2022 → Apr 2026), no indicator rules: every move of at least
$20 (or 2× the 4H ATR) — <b>{len(S)} big moves</b>. Each chart shows the 4H boxes (green/red shading, dotted = midline),
the <b style="color:#ffeb3b">perfect entry</b>, the <b style="color:#29b6f6">first realistic 3m entry</b>, the <b style="color:#ef5350">stop</b>
and <b style="color:#ab47bc">where the move ended</b>, with the video timestamp to watch it yourself.</p>
<p><b>What the turns had in common</b> (all 15m turns on video vs the ones that became big moves):</p>
<table><tr><th>Picture at the turn</th><th>Turns</th><th>Became big</th><th>Chance</th></tr>{tbl}</table>
<p><b>The catch</b>: taken live (no hindsight), every sweep + reclaim from 2022–26 = 1,544 trades at <b>−0.13R</b> each; 2016–22 = 2,356 trades
at −0.13R. The second section shows random examples of that same picture where the stop was hit.</p></div>
<h1>Part 1 — big moves (random {len(SB)} of {len(S)})</h1>{''.join(cards)}
<h1>Part 2 — same picture, no move (random {len(SF)} stopped-out sweep + reclaim trades at a 4H box)</h1>{''.join(fcards)}
</body></html>"""
(OUT / "BIG_MOVES_VISUAL_BOOK.html").write_text(html)
print("written", OUT / "BIG_MOVES_VISUAL_BOOK.html", round((OUT / "BIG_MOVES_VISUAL_BOOK.html").stat().st_size / 1e6, 1), "MB")
