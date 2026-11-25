"""Stage 5: date every keyframe.
In replay the 15m header shows O=H=L=C = the price of the newest revealed bar's first tick (the bar's open).
The sequence of those values is matched in order against HistData 15m opens (an independent feed; OANDA and
HistData differ by ~0.1-0.3). A match is accepted only if >= MIN_RUN consecutive values agree within TOL.
Frames whose header shows a full bar (H != L) are hovered bars (crosshair) and are not used for the sequence.
Output: frames_dated.csv with bar_utc (newest revealed 15m bar), seg (contiguous replay segment), match diff."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
W = Path(sys.argv[1])
TOL, LOOK, MIN_RUN, FAILS = 0.6, 4, 8, 3
m1 = pd.read_pickle(W / "merged_1m.pkl")  # Dukascopy where downloaded, HistData elsewhere
b15 = m1.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
O = b15.open.to_numpy(); T = b15.index
fr = pd.read_csv(W / "frames_parsed.csv")
# live price from the SELL box (stage 4b). A header is the NEWEST bar only if its close equals the live price;
# otherwise the crosshair is on an older bar (hover) and the frame is dated by interpolation instead.
import json, re
px = {}
for v in (1, 2, 3):
    for j in (W / f"v{v}/sell_ocr").glob("f_*.json"):
        try:
            its = json.loads(j.read_text()).get("items", [])
        except Exception:
            continue
        t = "".join(i["text"] for i in its).replace(" ", "")
        m = re.search(r"(\d)[.,]?(\d{3})[.,](\d{3})", t)
        if m: px[(v, int(j.stem[2:]))] = float(f"{m.group(1)}{m.group(2)}.{m.group(3)}")
fr["px"] = [px.get((v, k), np.nan) for v, k in zip(fr.video, fr.kf)]
fr["live"] = ((fr.c15 - fr.px).abs() < 0.006) | ((fr.h15 == fr.l15) & (fr.o15 == fr.c15))
out = []
for v, g in fr.groupby("video"):
    g = g.sort_values("kf").copy()
    # newest-bar open: flat headers (O=H=L=C) or complete-bar headers, but never while a crosshair label is shown
    flat = g[g.ok & g.o15.notna()]  # header bar sequence (hovered headers advance one bar per step too)
    # collapse runs of identical values
    vals = flat.o15.to_numpy(); kfs = flat.kf.to_numpy()
    runs = []  # (value, first_kf, last_kf)
    for val, kf in zip(vals, kfs):
        if runs and runs[-1][0] == val: runs[-1][2] = kf
        else: runs.append([val, kf, kf])
    rv = np.array([r[0] for r in runs])

    # Viterbi over runs: state = HistData bar index (candidates within TOLV of the value).
    TOLV = 1.5
    def emis(d): return min(d, TOLV) / 0.25
    STEP = {1: 0.0, 2: 1.5, 3: 3.0, 4: 4.5, 5: 6.0}
    JUMP = 14.0
    cand = [np.where(np.abs(O - x) < TOLV)[0] for x in rv]
    cost = [None] * len(rv); back = [None] * len(rv)
    for k in range(len(rv)):
        e = np.array([emis(abs(O[j] - rv[k])) for j in cand[k]])
        if k == 0 or len(cand[k - 1]) == 0:
            cost[k] = e + (0 if k == 0 else JUMP); back[k] = np.full(len(e), -1); continue
        prev = dict(zip(cand[k - 1], range(len(cand[k - 1]))))
        pc = cost[k - 1]; gbest = int(np.argmin(pc)); gval = pc[gbest] + JUMP
        c = np.empty(len(e)); bk = np.empty(len(e), int)
        for n, j in enumerate(cand[k]):
            best, arg = gval, gbest
            for st, pen in STEP.items():
                q = prev.get(j - st)
                if q is not None and pc[q] + pen < best:
                    best, arg = pc[q] + pen, q
            c[n] = best + e[n]; bk[n] = arg
        cost[k] = c; back[k] = bk
    # backtrack
    path = [None] * len(rv)
    if len(rv):
        q = int(np.argmin(cost[-1]))
        for k in range(len(rv) - 1, -1, -1):
            path[k] = cand[k][q] if len(cand[k]) else None
            q = back[k][q] if len(cand[k]) else 0
    # segments: break where step not in 1..5
    assign = {}; seg = 0; segs = []
    cur = []
    for k in range(len(rv)):
        j = path[k]
        if j is None: continue
        if cur and not (1 <= j - path[cur[-1]] <= 5): segs.append(cur); cur = []
        cur.append(k)
    if cur: segs.append(cur)
    for sg in segs:
        d = np.array([abs(O[path[k]] - rv[k]) for k in sg])
        # accept a segment only if long enough and close enough (otherwise AMBIGUOUS -> undated)
        if len(sg) >= MIN_RUN and np.median(d) < 0.45:
            seg += 1
            for k in sg: assign[k] = (path[k], seg, abs(O[path[k]] - rv[k]))
    # map runs -> frames
    kf2bar = {}
    for kk, (j, s, d) in assign.items():
        for kf in range(runs[kk][1], runs[kk][2] + 1):
            kf2bar[kf] = (j, s, d)
    g["bar_idx"] = g.kf.map(lambda x: kf2bar.get(x, (np.nan,))[0])
    g["seg"] = g.kf.map(lambda x: kf2bar.get(x, (np.nan, np.nan))[1])
    g["match_diff"] = g.kf.map(lambda x: kf2bar.get(x, (np.nan, np.nan, np.nan))[2])
    # forward-fill within segment across non-flat frames (hover, pauses) but not across layout loss
    g["bar_idx_ff"] = g.bar_idx.ffill(); g["seg_ff"] = g.seg.ffill()
    nxt = g.seg.bfill()
    g.loc[g.seg_ff != nxt, ["bar_idx_ff", "seg_ff"]] = np.nan  # gap between segments: unknown
    g.loc[~g.ok, ["bar_idx_ff", "seg_ff"]] = np.nan
    # NEWEST bar vs HEADER bar. With the mouse resting on the chart the header shows a bar k bars behind the
    # newest one (the chart scrolls under a still cursor). The live SELL price equals the close of the newest bar,
    # and that exact 3-decimal close appears in the header a few seconds later when that bar is hovered.
    # So: newest bar = the dated header bar whose header close == live price (searched within +-600 s).
    g["hdr_idx"] = g.bar_idx
    dated = g[g.bar_idx.notna() & g.c15.notna()]
    cmap = {}
    for t_, c_, j_ in zip(dated.t, dated.c15.round(3), dated.bar_idx):
        cmap.setdefault(c_, []).append((t_, j_))
    newest = []
    for t_, px_, lv, j_ in zip(g.t, g.px.round(3), g.live, g.bar_idx):
        if lv and pd.notna(j_):
            newest.append(j_); continue
        best = np.nan
        if pd.notna(px_) and px_ in cmap:
            c = [(abs(tt - t_), jj) for tt, jj in cmap[px_] if -60 <= tt - t_ <= 600]
            if c: best = min(c)[1]
        newest.append(best)
    g["new_idx"] = newest
    # sanity: the newest bar can never be older than the header bar; drop violations, then fill gaps by
    # carrying the last known lag (newest - header) within the segment
    bad = g.new_idx.notna() & g.hdr_idx.notna() & (g.new_idx < g.hdr_idx)
    g.loc[bad, "new_idx"] = np.nan
    g["lag"] = g.new_idx - g.hdr_idx
    g["lag_ff"] = g.groupby(g.seg_ff).lag.transform(lambda s: s.ffill().bfill())
    g["newest_idx"] = g.new_idx.fillna(g.bar_idx_ff + g.lag_ff)
    g["newest_src"] = np.where(g.new_idx.notna(), "live_price", np.where(g.newest_idx.notna(), "lag_carried", ""))
    g["bar_utc"] = g.newest_idx.map(lambda j: T[int(j)] if pd.notna(j) and int(j) < len(T) else pd.NaT)
    g["hdr_utc"] = g.bar_idx_ff.map(lambda j: T[int(j)] if pd.notna(j) else pd.NaT)
    out.append(g)
    print(f"v{v}: runs={len(runs)} matched={len(assign)} segs={seg} frames dated={g.bar_utc.notna().mean():.1%} "
          f"newest via price={(g.newest_src=='live_price').mean():.1%} lag_med={g.lag.median()} "
          f"median diff={np.nanmedian([a[2] for a in assign.values()]) if assign else np.nan:.3f}")
df = pd.concat(out)
df.to_csv(W / "frames_dated.csv", index=False)
b15.to_pickle(W / "b15_ref.pkl")
