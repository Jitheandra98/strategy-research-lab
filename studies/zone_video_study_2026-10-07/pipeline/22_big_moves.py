"""Stage 22: start from the money. Every big swing in the replayed periods -> where the perfect entry was, where the
first realistic 3m entry was, which ICT ingredients were present at the turn, and how often the same picture appeared
at turns that did NOT become big moves (look-alikes).

Big swing: 15m zig-zag with reversal threshold max($20, 2 x ATR4) (owner: catch $20-40 moves).
Turn ingredients (all measured at the turning 15m bar, using only what existed then):
  box     : extreme within 0.15 ATR4 of a live 4H-box level (top / CE / bottom); which kind
  sweep   : extreme took out the lowest low (highest high) of the previous 2-24 h by >= 0.05 ATR4 and a 15m close came
            back above (below) that old extreme within 3 bars
  disp    : within 1 h after the turn a 3m candle >= 2 x 3m ATR in the new direction leaves a 3m FVG
  h4open  : the turn is within 30 min of a 4H candle open
Realistic entry: first 3m close beyond the last 3m swing (high for longs) formed after the turn; stop = turn extreme
-/+ 0.05 ATR4; R = (swing end - entry) / risk.
Look-alikes: every 15m fractal turn (5 bars each side) on video with the same ingredients -> share that became big swings.
usage: 22_big_moves.py <build_dir> <work_dir> <minute_pickle> <out_dir>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

B, W, M1, OUT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]); OUT.mkdir(parents=True, exist_ok=True)
b = pd.read_pickle(B / "bars15.pkl"); h4 = pd.read_pickle(B / "bars4h.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl")
rev = pd.read_pickle(W / "bar_reveal.pkl")
h4 = h4.copy(); h4["avail"] = pd.to_datetime(h4.avail)
T = b.index; n = len(T); H, L, C, O = (b[k].to_numpy() for k in ["high", "low", "close", "open"])
A4 = pd.merge_asof(pd.DataFrame({"t": T}), h4[["avail", "atr"]].rename(columns={"avail": "t"}).sort_values("t"),
                   on="t", direction="backward").atr.to_numpy()
m1 = pd.read_pickle(W / M1)[["open", "high", "low", "close"]]
m3 = m1.resample("3min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
m3 = m3[(m3.index >= T[0]) & (m3.index <= T[-1])]
T3 = m3.index.values; H3, L3, C3, O3 = (m3[k].to_numpy() for k in ["high", "low", "close", "open"])
tr3 = np.maximum(H3 - L3, np.abs(np.r_[np.nan, C3[:-1]] - H3)); A3 = pd.Series(tr3).ewm(alpha=1 / 14).mean().to_numpy()
n3 = len(T3)
sh3 = np.zeros(n3, bool); sl3 = np.zeros(n3, bool)
sh3[2:-2] = (H3[2:-2] > H3[1:-3]) & (H3[2:-2] > H3[:-4]) & (H3[2:-2] > H3[3:-1]) & (H3[2:-2] > H3[4:])
sl3[2:-2] = (L3[2:-2] < L3[1:-3]) & (L3[2:-2] < L3[:-4]) & (L3[2:-2] < L3[3:-1]) & (L3[2:-2] < L3[4:])
zav = z4.born_time.map(lambda x: h4.avail.get(x, pd.NaT)).values
zend = np.where(z4.end_time.notna(), (z4.end_time + pd.Timedelta(hours=4)).values, np.datetime64("2100-01-01"))
ZT, ZB, ZK = z4.top.to_numpy(), z4.bot.to_numpy(), z4.kind.to_numpy()
h4open = set(h4.index)

# ── zig-zag on 15m ──
piv = []; d = 0; ext_i = 0
for i in range(1, n):
    th = max(20.0, 2 * (A4[i] if not np.isnan(A4[i]) else 10))
    if d >= 0:
        if H[i] >= H[ext_i] or d == 0 and H[i] > H[ext_i]: ext_i = i if (d == 1 or H[i] >= H[ext_i]) else ext_i
        if d == 1 and H[i] > H[ext_i]: ext_i = i
        if (d in (0, 1)) and H[ext_i] - L[i] >= th:
            piv.append((ext_i, 1)); d = -1; ext_i = i; continue
    if d <= 0:
        if d == -1 and L[i] < L[ext_i]: ext_i = i
        if d == 0 and L[i] < L[ext_i]: pass
        if (d in (0, -1)) and H[i] - L[ext_i] >= th:
            piv.append((ext_i, -1)); d = 1; ext_i = i
swings = []
for (a, ta), (c, tc) in zip(piv[:-1], piv[1:]):
    # a swing starts at pivot a (type ta: -1 = low -> up move, 1 = high -> down move) and ends at c
    dirn = 1 if ta == -1 else -1
    swings.append((a, c, dirn))


def ingredients(i, dirn):
    a4 = A4[i]
    if np.isnan(a4): return None
    ex = L[i] if dirn == 1 else H[i]
    t = np.datetime64(T[i].tz_convert(None))
    alive = (zav <= t) & (zend > t)
    lv = np.r_[ZT[alive], (ZT[alive] + ZB[alive]) / 2, ZB[alive]]
    kinds = np.r_[ZK[alive], ZK[alive], ZK[alive]]
    names = np.r_[["top"] * alive.sum(), ["CE"] * alive.sum(), ["bottom"] * alive.sum()]
    box = None
    if len(lv):
        k = np.argmin(np.abs(lv - ex))
        if abs(lv[k] - ex) <= 0.15 * a4: box = f"{names[k]} of 4H {kinds[k]}"
    w0, w1 = max(0, i - 96), max(0, i - 8)
    sweep = False
    if w1 > w0:
        prior = L[w0:w1].min() if dirn == 1 else H[w0:w1].max()
        took = (ex < prior - 0.05 * a4) if dirn == 1 else (ex > prior + 0.05 * a4)
        back = any(((C[k] > prior) if dirn == 1 else (C[k] < prior)) for k in range(i, min(n, i + 4)))
        sweep = bool(took and back)
    j0 = np.searchsorted(T3, np.datetime64(T[i].tz_convert(None))); disp = False
    for q in range(j0 + 2, min(n3, j0 + 22)):
        big = (dirn * (C3[q - 1] - O3[q - 1])) >= 2 * A3[q - 1]
        gap = (L3[q] > H3[q - 2]) if dirn == 1 else (H3[q] < L3[q - 2])
        if big and gap: disp = True; break
    near_open = any(abs((T[i] - o).total_seconds()) <= 1800 for o in (T[i].floor("4h"), T[i].ceil("4h"))) or \
        any(abs((T[i] - o).total_seconds()) <= 1800 for o in h4.index[(h4.index >= T[i] - pd.Timedelta(hours=1)) & (h4.index <= T[i] + pd.Timedelta(hours=1))])
    hny = T[i].tz_convert("America/New_York").hour
    sess = "ASIA" if (hny >= 18 or hny < 2) else "LONDON" if hny < 8 else "NY_AM" if hny < 12 else "NY_PM"
    return dict(box=box, at_box=box is not None, sweep=sweep, disp=disp, h4open=near_open, session=sess)


def realistic(i, dirn, end_px):
    j0 = np.searchsorted(T3, np.datetime64(T[i].tz_convert(None))); ex = L[i] if dirn == 1 else H[i]
    for q in range(j0 + 1, min(n3, j0 + 80)):
        sw = np.where((sh3 if dirn == 1 else sl3)[j0:q - 1])[0]
        if len(sw):
            ref = H3[j0 + sw[-1]] if dirn == 1 else L3[j0 + sw[-1]]
            if (dirn == 1 and C3[q] > ref) or (dirn == -1 and C3[q] < ref):
                entry = C3[q]; stop = ex - dirn * 0.05 * A4[i]; risk = dirn * (entry - stop)
                if risk <= 0: return None
                return dict(real_entry_time=pd.Timestamp(T3[q], tz="UTC"), real_entry=entry, stop=stop, risk=risk,
                            R_to_end=dirn * (end_px - entry) / risk,
                            captured=dirn * (end_px - entry) / abs(end_px - ex))
    return None


rows = []
for a, c, dirn in swings:
    if T[a] not in rev: continue
    ing = ingredients(a, dirn)
    if ing is None: continue
    start = L[a] if dirn == 1 else H[a]; end = H[c] if dirn == 1 else L[c]
    rr = realistic(a, dirn, end)
    v, vt, _ = sorted(rev[T[a]])[0]
    rows.append(dict(turn_time=T[a], end_time=T[c], dir="UP" if dirn == 1 else "DOWN", start=start, end=end,
                     move=abs(end - start), hours=(T[c] - T[a]).total_seconds() / 3600, video=v, video_t=vt, **ing,
                     **(rr or {})))
S = pd.DataFrame(rows); S.to_pickle(OUT / "big_moves.pkl"); S.to_csv(OUT / "big_moves.csv", index=False)

# ── look-alikes: every 15m fractal turn (5/5) on video ──
look = []
big_turns = {(r.turn_time, 1 if r.dir == "UP" else -1) for r in S.itertuples()}
for i in range(100, n - 6):
    if T[i] not in rev: continue
    for dirn in (1, -1):
        is_turn = (L[i] == L[i - 5:i + 6].min()) if dirn == 1 else (H[i] == H[i - 5:i + 6].max())
        if not is_turn: continue
        ing = ingredients(i, dirn)
        if ing is None: continue
        look.append(dict(t=T[i], dir=dirn, big=(T[i], dirn) in big_turns, **ing))
Lk = pd.DataFrame(look); Lk.to_pickle(OUT / "all_turns.pkl")
combos = []
for name, m in [("any turn", np.ones(len(Lk), bool)), ("at 4H box", Lk.at_box), ("sweep", Lk.sweep),
                ("displacement", Lk.disp), ("at 4H open", Lk.h4open),
                ("box + sweep", Lk.at_box & Lk.sweep), ("box + displacement", Lk.at_box & Lk.disp),
                ("sweep + displacement", Lk.sweep & Lk.disp), ("box + sweep + displacement", Lk.at_box & Lk.sweep & Lk.disp),
                ("box + sweep + disp + 4H open", Lk.at_box & Lk.sweep & Lk.disp & Lk.h4open)]:
    g = Lk[m]
    combos.append(dict(picture=name, turns_with_this_picture=len(g), became_big_move=int(g.big.sum()),
                       share_big=g.big.mean() if len(g) else np.nan,
                       share_of_all_big_moves=g.big.sum() / max(1, Lk.big.sum())))
Cb = pd.DataFrame(combos); Cb.to_csv(OUT / "lookalikes.csv", index=False)
pd.set_option("display.width", 200)
print("big moves on video:", len(S), " with realistic entry:", S.real_entry.notna().sum())
print(S[["at_box", "sweep", "disp", "h4open"]].mean().round(3).to_dict())
print("median move", S.move.median(), "median R from realistic entry", S.R_to_end.median(), "captured", S.captured.median())
print(Cb.round(3).to_string())
