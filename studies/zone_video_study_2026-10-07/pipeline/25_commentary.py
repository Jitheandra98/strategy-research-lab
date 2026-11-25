"""Stage 25: play-by-play COMMENTARY of each video, in the owner's auction language, built from the price data and the
real STATION2 boxes. For every big swing (stage 22, >= $20 or 2x ATR4) shown on screen, in time order:
 - where it turned: the nearest 4H box AND 15m box level at the turn, named by what the box was at that moment
   (order block / FVG / breaker = broken OB flipped / IFVG = broken FVG flipped / imported 4H FVG), and which edge
 - who took control (buyers / sellers), whether old highs/lows were swept first
 - the 15m imbalance it left (first 15m FVG in the move) and whether price came back to fill it before continuing
 - where it stopped: the box level at the end of the swing
 - size, duration, video timestamp; moves >= $50 are flagged as the big auction moves
usage: 25_commentary.py <build_dir> <work_dir> <bigmoves_dir> <out_dir>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

B, W, BM, OUT = (Path(x) for x in sys.argv[1:5]); OUT.mkdir(parents=True, exist_ok=True)
b = pd.read_pickle(B / "bars15.pkl"); h4 = pd.read_pickle(B / "bars4h.pkl"); h4["avail"] = pd.to_datetime(h4.avail)
z4 = pd.read_pickle(B / "zones4h.pkl"); z15 = pd.read_pickle(B / "zones15.pkl")
S = pd.read_pickle(BM / "big_moves.pkl").sort_values("turn_time")
T = b.index; H, L, C = (b[k].to_numpy() for k in ["high", "low", "close"])
pos = {t: i for i, t in enumerate(T)}
A4 = pd.merge_asof(pd.DataFrame({"t": T}), h4[["avail", "atr"]].rename(columns={"avail": "t"}).sort_values("t"),
                   on="t", direction="backward").atr.to_numpy()


def prep(z, tf):
    z = z.copy()
    if tf == "4H":
        z["av"] = z.born_time.map(lambda x: h4.avail.get(x, pd.NaT)); z["en"] = (z.end_time + pd.Timedelta(hours=4))
    else:
        z["av"] = z.born_time + pd.Timedelta(minutes=15); z["en"] = z.end_time
    z["en"] = z.en.fillna(pd.Timestamp("2100-01-01", tz="UTC"))
    return z


Z4, Z15 = prep(z4, "4H"), prep(z15, "15m")


def name_box(z, t):
    inv = pd.notna(z.inverted_time) and z.inverted_time <= t
    cons = pd.notna(z.consumed_time) and z.consumed_time <= t and not inv
    d = z.dir * (-1 if inv else 1)
    side = "bullish" if d == 1 else "bearish"
    if z.kind == "OB": base = "breaker block" if inv else "order block"
    elif z.kind == "FVG": base = "IFVG" if inv else "fair value gap"
    else: base = "imported 4H FVG" + (" (inverted)" if inv else "")
    return f"{side} {base}" + (" (already filled once)" if cons else "")


def nearest(Z, t, px, tf, tol):
    a = Z[(Z.av <= t) & (Z.en > t)]
    if not len(a): return None
    lv = pd.concat([a.top.rename("lv").to_frame().assign(edge="top"), ((a.top + a.bot) / 2).rename("lv").to_frame().assign(edge="middle (CE)"),
                    a.bot.rename("lv").to_frame().assign(edge="bottom")])
    lv["dist"] = (lv.lv - px).abs(); r = lv.sort_values("dist").iloc[0]
    if r.dist > tol: return None
    z = a.loc[r.name] if not isinstance(a.loc[r.name], pd.DataFrame) else a.loc[r.name].iloc[0]
    return f"the {r.edge} of a {tf} {name_box(z, t)} ({z.bot:,.1f}–{z.top:,.1f})"


def fvg_story(i0, i1, d):
    for k in range(i0 + 2, i1):
        gap = (L[k] > H[k - 2]) if d == 1 else (H[k] < L[k - 2])
        if gap:
            g_lo, g_hi = (H[k - 2], L[k]) if d == 1 else (H[k], L[k - 2])
            for m in range(k + 1, i1 + 1):
                if (d == 1 and L[m] <= g_hi) or (d == -1 and H[m] >= g_lo):
                    return (f"It left a 15m fair value gap at {g_lo:,.1f}–{g_hi:,.1f}, came back to fill it "
                            f"{(T[m] - T[k]).total_seconds() / 3600:.1f} h later, and pushed on from there.")
            return f"It left a 15m fair value gap at {g_lo:,.1f}–{g_hi:,.1f} and never looked back — the gap stayed open."
    return "No clean 15m fair value gap — it moved in a grind, not a displacement."


def hms(s): s = int(round(s)); return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


for v in (1, 2, 3):
    Sv = S[S.video == v]
    if not len(Sv): continue
    lines = [f"# Commentary — video V{v}\n",
             f"Play-by-play of every move of at least $20 (or 2× the 4H ATR) shown in V{v}: {len(Sv)} moves, "
             f"{(Sv.move >= 50).sum()} of them $50+. Times = when the turn appears on screen in the video.",
             "Built after the fact from the price data and the real STATION2 boxes — it describes what happened; "
             "it is not a signal list.\n"]
    day = None
    for r in Sv.itertuples():
        i0, i1 = pos[r.turn_time], pos[r.end_time]; d = 1 if r.dir == "UP" else -1
        ny = r.turn_time.tz_convert("America/New_York")
        if ny.date() != day:
            day = ny.date(); lines.append(f"\n## {ny:%A %d %B %Y}\n")
        tol = 0.2 * (A4[i0] if not np.isnan(A4[i0]) else 10)
        at4 = nearest(Z4, r.turn_time, r.start, "4H", tol); at15 = nearest(Z15, r.turn_time, r.start, "15m", tol)
        en4 = nearest(Z4, r.end_time, r.end, "4H", tol); en15 = nearest(Z15, r.end_time, r.end, "15m", tol)
        who = "Buyers" if d == 1 else "Sellers"; other = "sellers" if d == 1 else "buyers"
        where = at4 or at15
        big = "💥 **BIG AUCTION MOVE** — " if r.move >= 50 else ""
        s = [f"**V{v} {hms(r.video_t)} — {ny:%H:%M} NY ({r.session}).** {big}"]
        if where:
            s.append(f"Price came {'down' if d == 1 else 'up'} into {where}" + (f", lined up with {at15}" if at4 and at15 else "") + ".")
        else:
            s.append(f"Price turned at {r.start:,.1f} with no STATION2 box right there — an unmarked level.")
        if r.sweep:
            s.append(f"First it ran the old {'lows' if d == 1 else 'highs'} — the {other} who were "
                     f"{'selling the lows got trapped' if d == 1 else 'buying the highs got trapped'} — then a 15m candle closed back.")
        s.append(f"{who} took over from {r.start:,.1f}." + (" The turn came right around a new 4H candle open." if r.h4open else ""))
        s.append(fvg_story(i0, i1, d))
        s.append(f"The move ran **{r.move:,.0f} points in {r.hours:.0f} h** to {r.end:,.1f}" +
                 (f", where it hit {en4 or en15} and the auction turned again." if (en4 or en15) else ", into open space with no box — then reversed.") )
        if pd.notna(r.real_entry):
            s.append(f"*Realistic entry: the first 3m confirmation came {(r.real_entry_time - r.turn_time).total_seconds() / 60:.0f} min "
                     f"after the turn at {r.real_entry:,.1f} (stop {r.stop:,.1f}) → {r.R_to_end:+.1f}R to the end of the move.*")
        lines.append(" ".join(s) + "\n")
    (OUT / f"COMMENTARY_V{v}.md").write_text("\n".join(lines))
    print("V", v, len(Sv), "moves ->", OUT / f"COMMENTARY_V{v}.md")
