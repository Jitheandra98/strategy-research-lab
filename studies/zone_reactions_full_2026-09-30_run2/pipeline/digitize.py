"""Candle digitizer for the 5-minute pane of the replay recording.

For one frame (+ its Vision OCR json) returns:
  layout   : price-axis x, plot box
  price_fit: price = a + b*y (robust fit to axis labels, pixel-refined centres)
  bars     : list of {k, xc, high, low, open, close, dir, flags}
             k = bar slot index on the pitch grid (0 = leftmost slot)
  labels   : time-axis anchors {k, kind: hour|day|month|year, value}
Pure pixel reading — no indicator logic here.
"""
import json, re
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

PRICE_RE = re.compile(r"^\s*(\d)[,.\s]?(\d{3})[.,](\d)\s*$")
HOUR_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")
DAY_RE = re.compile(r"^\s*(\d{1,2})\s*$")
MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
YEAR_RE = re.compile(r"^\s*(20\d\d)\s*$")

PLOT_X0 = 58
import os
MODE = os.environ.get("DIGI_MODE", "hybrid")
GAP_MAX = int(os.environ.get("DIGI_GAP", "6"))   # validated: val_frames.py, 3-frame sample
HDR_RE = re.compile(r"[O0o]\s*([\d,.]+\.\d)\s*H\s*([\d,.]+\.\d)\s*L\s*([\d,.]+\.\d)\s*C\s*([\d,.]+\.\d)")


def _num(t):
    t = t.replace(",", "")
    if t.count(".") > 1:           # OCR read the thousands comma as a dot
        head, tail = t.rsplit(".", 1)
        t = head.replace(".", "") + "." + tail
    try:
        return float(t)
    except ValueError:
        return None


def headers(items, axis_x):
    """OHLC in the pane headers (y < 100). Returns {'5m': (o,h,l,c) | None, '4h': ...}."""
    out = {"5m": None, "4h": None}
    for it in items:
        if it["y"] > 100:
            continue
        m = HDR_RE.search(it["text"].replace(" ", ""))
        if not m:
            continue
        vals = tuple(_num(g) for g in m.groups())
        if None in vals or not (vals[2] <= min(vals[0], vals[3]) and vals[1] >= max(vals[0], vals[3])):
            continue
        out["5m" if it["x"] < axis_x else "4h"] = vals
    return out


def parse_price(t):
    t = t.replace(" ", "")
    m = PRICE_RE.match(t)
    if not m:
        return None
    return float(m.group(1) + m.group(2) + "." + m.group(3))


def load(frame_path, ocr_path):
    img = np.asarray(Image.open(frame_path).convert("RGB")).astype(np.int16)
    ocr = json.load(open(ocr_path))
    return img, ocr.get("items", [])


def find_layout(img, items):
    """Left-pane price axis = the leftmost dense column of price labels."""
    H, W, _ = img.shape
    xs = []
    for it in items:
        if it["y"] < 120 or it["y"] > 1275:
            continue
        if parse_price(it["text"]) is not None and 600 < it["x"] < 2000:
            xs.append(it["x"])
    if len(xs) < 5:
        return None
    xs = np.array(sorted(xs))
    # cluster: the left pane axis is the leftmost cluster with >=5 members
    clusters = []
    cur = [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] <= 12:
            cur.append(x)
        else:
            clusters.append(cur)
            cur = [x]
    clusters.append(cur)
    clusters = [c for c in clusters if len(c) >= 5]
    if not clusters:
        return None
    axis_x = float(np.median(clusters[0]))
    # time axis row
    ty = [it["y"] for it in items if HOUR_RE.match(it["text"]) and it["x"] < axis_x]
    time_y = float(np.median(ty)) if ty else 1287.0
    return {"axis_x": axis_x, "plot_x0": PLOT_X0, "plot_x1": int(axis_x) - 6,
            "plot_y0": 120, "plot_y1": int(time_y) - 10, "time_y": time_y}


def refine_center(img, x0, x1, yc, half=13):
    """Pixel centre of the text blob in the axis column nearest yc."""
    y0, y1 = int(max(0, yc - half)), int(min(img.shape[0], yc + half))
    col = img[y0:y1, int(x0):int(x1)].mean(axis=2)
    rows = (col > 110).sum(axis=1) > 0
    if not rows.any():
        return None
    idx = np.where(rows)[0]
    # contiguous runs
    runs, s = [], idx[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if b != a + 1:
            runs.append((s, a))
            s = b
    runs.append((s, idx[-1]))
    best = min(runs, key=lambda r: abs((r[0] + r[1]) / 2 + y0 - yc))
    if best[1] - best[0] < 6 or best[1] - best[0] > 18:
        return None
    return (best[0] + best[1]) / 2 + y0


def fit_price(img, items, lay):
    pts = []
    for it in items:
        v = parse_price(it["text"])
        if v is None or abs(it["x"] - lay["axis_x"]) > 14:
            continue
        if not (lay["plot_y0"] - 30 < it["y"] < lay["plot_y1"] + 10):
            continue
        yc = refine_center(img, it["x"], it["x"] + it["w"], it["y"] + it["h"] / 2)
        if yc is not None:
            pts.append((yc, v))
    if len(pts) < 4:
        return None
    pts = np.array(pts)
    best = None
    n = len(pts)
    for i in range(n):
        for j in range(i + 1, n):
            (y1, v1), (y2, v2) = pts[i], pts[j]
            if abs(y2 - y1) < 50:
                continue
            b = (v2 - v1) / (y2 - y1)
            if b >= 0:
                continue
            a = v1 - b * y1
            res = np.abs(a + b * pts[:, 0] - pts[:, 1]) / abs(b)  # residual in px
            inl = res < 1.5
            score = inl.sum()
            if best is None or score > best[0]:
                best = (score, inl)
    if best is None or best[0] < 4:
        return None
    inl = best[1]
    A = np.vstack([np.ones(inl.sum()), pts[inl, 0]]).T
    (a, b), *_ = np.linalg.lstsq(A, pts[inl, 1], rcond=None)
    resid = np.abs(a + b * pts[inl, 0] - pts[inl, 1]) / abs(b)
    return {"a": float(a), "b": float(b), "n": int(inl.sum()), "n_all": int(n),
            "max_resid_px": float(resid.max())}


def masks(reg):
    r, g, b = reg[..., 0], reg[..., 1], reg[..., 2]
    mx = reg.max(axis=2)
    mn = reg.min(axis=2)
    mean = reg.mean(axis=2)
    gray = ((mx - mn) < 34) & (mean > 78) & (mean < 215)
    green = (g > r + 22) & (g > b + 12) & (g > 105)
    red = (r > g + 45) & (r > b + 25) & (r > 105)
    return gray, green, red


def hrun_filter(m, maxlen):
    """Remove pixels belonging to horizontal runs longer than maxlen (zone borders, lines)."""
    out = m.copy()
    H, W = m.shape
    for y in range(H):
        row = m[y]
        if not row.any():
            continue
        d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
        st = np.where(d == 1)[0]
        en = np.where(d == -1)[0]
        for s, e in zip(st, en):
            if e - s > maxlen:
                out[y, s:e] = False
    return out


def edge_centers(col_mask):
    """Centres of short horizontal coloured runs (candle body edges)."""
    cs = []
    H, W = col_mask.shape
    for y in range(H):
        row = col_mask[y]
        if not row.any():
            continue
        d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
        st = np.where(d == 1)[0]
        en = np.where(d == -1)[0]
        for s, e in zip(st, en):
            if 3 <= e - s <= 9:
                # thin edge only: rows 2 px above and below mostly uncoloured
                up = col_mask[y - 2, s:e].mean() if y >= 2 else 0
                dn = col_mask[y + 2, s:e].mean() if y + 2 < H else 0
                if up < 0.5 and dn < 0.5:
                    cs.append((s + e - 1) / 2)
    return np.array(cs)


def grid_from_edges(col_mask, items, lay, x0):
    # pitch from hour labels: consecutive 1-hour label pairs are 12 bars apart
    hrs = []
    for it in items:
        if abs(it["y"] + it["h"] / 2 - (lay["time_y"] + 9)) > 16:
            continue
        m = HOUR_RE.match(it["text"].strip())
        xc = it["x"] + it["w"] / 2
        if m and x0 < xc < lay["axis_x"]:
            hrs.append((xc, int(m.group(1)) * 60 + int(m.group(2))))
    hrs.sort()
    est = []
    for (xa, ha), (xb, hb) in zip(hrs[:-1], hrs[1:]):
        dh = (hb - ha) % 1440
        if 0 < dh <= 240:
            est.append((xb - xa) / (dh / 5))
    cs = edge_centers(col_mask)
    if len(cs) < 10:
        return None, None
    if est:
        pe = float(np.median(est))
        cands = np.arange(pe * 0.95, pe * 1.05, 0.0005)
    else:
        cands = np.arange(2.5, 30, 0.002)
    best = None
    for p in cands:
        ang = 2 * np.pi * (cs / p)
        R = np.hypot(np.cos(ang).mean(), np.sin(ang).mean())
        if best is None or R > best[0]:
            best = (R, p)
    R, p = best
    if R < 0.12:
        return None, None
    # phase = histogram peak, then circular mean of points near it (junk is uniform)
    nb = 24
    h, e = np.histogram(cs % p, bins=nb, range=(0, p))
    i = int(np.argmax(h))
    pk = (e[i] + e[i + 1]) / 2
    dd = ((cs % p) - pk + p / 2) % p - p / 2
    near = np.abs(dd) < 1.0
    ph = (pk + dd[near].mean()) % p
    return float(p), float(ph)


def digitize(img, items, lay=None):
    if lay is None:
        lay = find_layout(img, items)
    if lay is None:
        return {"ok": False, "why": "layout"}
    pf = fit_price(img, items, lay)
    if pf is None:
        return {"ok": False, "why": "price_fit", "layout": lay}
    x0, x1, y0, y1 = lay["plot_x0"], lay["plot_x1"], lay["plot_y0"], lay["plot_y1"]
    reg = img[y0:y1, x0:x1]
    gray, green, red = masks(reg)
    lit = reg.mean(axis=2) > 35
    LITD = lit.copy()                       # lit pixels, dilated ±1 row (box edges are 1-2 px lines)
    LITD[1:] |= lit[:-1]
    LITD[:-1] |= lit[1:]
    # label mask: filled bright/saturated blocks (signal & outcome labels drawn over candles).
    # 1-px candle edges vanish under a 3x3 erosion; label boxes (>=14 px tall) survive.
    mxc, mnc = reg.max(axis=2), reg.min(axis=2)
    lab = ((mxc > 90) & ((mxc - mnc) > 45)) | (reg.mean(axis=2) > 215)
    lab = ndi.binary_erosion(lab, structure=np.ones((3, 3)))
    lab = ndi.binary_dilation(lab, structure=np.ones((7, 7)))
    cand = gray | green | red
    cand = hrun_filter(cand, 9)
    green &= cand
    red &= cand
    gray &= cand
    # vertical support: keep pixels with a vertical neighbour (drop isolated text specks)
    vs = cand.copy()
    vs[1:-1] = cand[1:-1] & (cand[:-2] | cand[2:])
    prof = vs.sum(axis=0).astype(float)
    if prof.sum() < 50:
        return {"ok": False, "why": "no_candles", "layout": lay, "price_fit": pf}
    pitch, ph = grid_from_edges(green | red, items, lay, x0)
    if pitch is None:
        return {"ok": False, "why": "grid", "layout": lay, "price_fit": pf}
    half = max(1, int((pitch - 1) // 2))
    # phase refinement: the column midway between bars must be empty; shift the grid so it is
    prof_all = vs.sum(axis=0).astype(float)
    best_d, best_sc = 0.0, None
    # edge runs sit ~0.5 px right of the wick (right outline pixel is coloured on edge rows);
    # outline/wick/outline alternate every 2 px, so a wider search would alias onto the outline
    for dlt in np.arange(-1.0, 0.51, 0.25):
        cs_ = np.arange(ph + dlt, len(prof_all), pitch)
        inside = sum(prof_all[max(0, int(round(c_)) - half):int(round(c_)) + half + 1].sum() for c_ in cs_)
        gaps = sum(prof_all[int(round(c_ + pitch / 2))] for c_ in cs_ if int(round(c_ + pitch / 2)) < len(prof_all))
        sc = inside - 4 * gaps
        if best_sc is None or sc > best_sc:
            best_d, best_sc = dlt, sc
    ph = (ph + best_d) % pitch
    colour = green | red
    bars = []
    b_ = pf["b"]
    a_ = pf["a"]

    def price_of(yrow):
        return a_ + b_ * (yrow + y0)

    k = 0
    for c in np.arange(ph, len(prof), pitch):
        ci = int(round(c))
        lo_x, hi_x = max(0, ci - half), min(len(prof), ci + half + 1)
        # background-relative masks: subtract, row by row, the darker of the two gap columns
        # beside this bar. Zone fills/session tints/zone borders are in the gap columns too, so a
        # wick crossing a tinted zone stays a neutral positive increment and lines cancel out.
        gl_, gr2_ = int(round(c - pitch / 2)), int(round(c + pitch / 2))
        use_bg = MODE != "v2" and pitch >= 5 and 0 <= gl_ and gr2_ < reg.shape[1]
        if use_bg:
            gA, gB = reg[:, gl_], reg[:, gr2_]
            bg = np.where((gA.sum(axis=1) <= gB.sum(axis=1))[:, None], gA, gB)
            exc = reg[:, lo_x:hi_x] - bg[:, None, :]
            em = exc.mean(axis=2)
            gray_w = (em > 35) & ((exc.max(axis=2) - exc.min(axis=2)) < 45)
            er, eg, eb = exc[..., 0], exc[..., 1], exc[..., 2]
            green_w = (eg > er + 20) & (eg > eb + 10) & (eg > 40)
            red_w = (er > eg + 35) & (er > eb + 20) & (er > 45)
            cw = gray_w | green_w | red_w
            win = cw.copy()
            win[1:-1] = cw[1:-1] & (cw[:-2] | cw[2:])
        else:
            win = vs[:, lo_x:hi_x]
            gray_w = gray[:, lo_x:hi_x]
            green_w = green[:, lo_x:hi_x]
            red_w = red[:, lo_x:hi_x]
        # A row may extend the candle only if it has neutral (gray) candle pixels, or its coloured
        # pixels form a body edge (run >= 3 px) or an outline pair (>= 2 px, span >= 3). This drops
        # zone-box left borders (1-2 px vertical lines drawn on the birth bar's wick column) and
        # dotted pool lines, which are coloured but never gray.
        colw = (green_w | red_w) & win
        gry = gray_w & win
        grow = gry.any(axis=1)
        # coloured rows count only next to gray structure (a body edge always touches its gray
        # outline); zone text/borders are coloured with no gray anywhere near them
        near_gray = grow.copy()
        near_gray[1:] |= grow[:-1]
        near_gray[:-1] |= grow[1:]
        ok_row = grow | (colw.any(axis=1) & near_gray)
        # no gray at all → nothing candle-like was read in this frame (zone text/borders, or one of
        # the indicator's rare fully-coloured entry bars): skip; other frames/bridging cover it
        rows = win.any(axis=1) & ok_row
        if rows.sum() >= 2:
            idx = np.where(rows)[0]
            # connected vertical components allowing gaps <= 3 px
            comps, s, prev = [], idx[0], idx[0]
            for yy in idx[1:]:
                if yy - prev > GAP_MAX:
                    comps.append((s, prev))
                    s = yy
                prev = yy
            comps.append((s, prev))
            # hybrid: extent (high/low) from the background-relative mask `win`, body edges from
            # the absolute colour masks + gap-column check (measured better for open/close)
            gw = green[:, lo_x:hi_x] if MODE != "v3pure" else green_w
            rw = red[:, lo_x:hi_x] if MODE != "v3pure" else red_w

            def colour_rows(c_):
                a, b = c_
                return gw[a:b + 1].any(axis=1).sum() + rw[a:b + 1].any(axis=1).sum()

            # the real candle is the component with the most gray (wick/outline) rows; coloured-only
            # components (lines, dots) win only when no gray structure exists at all
            def gray_rows(c_):
                a, b = c_
                return int(gry[a:b + 1].any(axis=1).sum())

            # zone-box left borders: a box's left edge is a thin vertical line (often in the wick
            # column) whose top/bottom meet horizontal lines running RIGHT through the empty
            # between-bar columns (boxes extend right), never left. Cut those segments away.
            span = int(round(2 * pitch))
            g1 = int(round(c + pitch / 2))
            r0, r1 = g1, min(reg.shape[1], g1 + span + 1)
            l1 = int(round(c - pitch / 2)) + 1
            l0 = max(0, l1 - 1 - span)
            if r1 - r0 >= 4:
                Rf = LITD[:, r0:r1].mean(axis=1)
                Lf = LITD[:, l0:l1].mean(axis=1) if l1 > l0 else np.zeros(len(Rf))
                edge_row = (Rf >= 0.8) & (Lf <= 0.3)
            else:
                edge_row = np.zeros(reg.shape[0], bool)

            def box_edge(yy):
                return bool(edge_row[yy])

            trimmed = []
            for (ca, cb) in comps:
                edges = [int(yy) for yy in np.where(edge_row[ca:cb + 1] & win[ca:cb + 1].any(axis=1))[0] + ca]
                inner_wide = 0.0
                if len(edges) >= 2:
                    e0_, e1_ = edges[0], edges[-1]
                    inner = win[e0_ + 1:e1_]
                    inner_wide = float((inner.sum(axis=1) >= 2).mean()) if len(inner) else 0.0
                if len(edges) >= 2 and inner_wide <= 0.2:   # thin line between the box edges → border
                    e0, e1 = edges[0], edges[-1]
                    above = (ca, e0 - 1) if e0 - 1 >= ca else None
                    below = (e1 + 1, cb) if e1 + 1 <= cb else None
                    wide = lambda seg: 0 if seg is None else int((win[seg[0]:seg[1] + 1].sum(axis=1) >= 2).sum())
                    keep = max([x for x in (above, below) if x is not None], key=wide, default=None)
                    if keep is None or wide(keep) == 0 and (keep[1] - keep[0]) < 2:
                        continue                          # component was only a box border
                    trimmed.append(keep)
                else:
                    trimmed.append((ca, cb))
            comps = [c_ for c_ in trimmed if gray_rows(c_) > 0]
            if not comps:
                k += 1
                continue
            comp = max(comps, key=lambda c_: (gray_rows(c_), colour_rows(c_) > 0, c_[1] - c_[0]))
            a, b = comp
            flags = []
            if len(comps) > 1:
                flags.append("multi_comp")
            # body edges: colored rows inside the component
            # valid body-edge rows: coloured inside the window, but NOT in the gap columns on
            # either side (zone borders / dashed / dotted lines run straight through those)
            gl, gr_ = int(round(c - pitch / 2)), int(round(c + pitch / 2))
            def gap_hit(yy):
                return ((0 <= gl < colour.shape[1] and colour[yy, gl]) or
                        (0 <= gr_ < colour.shape[1] and colour[yy, gr_]))
            g_rows = np.array([yy for yy in range(a, b + 1) if gw[yy].sum() >= 2 and not gap_hit(yy)], int)
            r_rows = np.array([yy for yy in range(a, b + 1) if rw[yy].sum() >= 2 and not gap_hit(yy)], int)
            ng = int(sum(gw[yy].sum() for yy in g_rows)) if len(g_rows) else 0
            nr = int(sum(rw[yy].sum() for yy in r_rows)) if len(r_rows) else 0
            d = 1 if ng > nr else -1 if nr > ng else 0
            erows = g_rows if d == 1 else r_rows if d == -1 else np.array([], int)
            # a wick column that touches the plot border is clipped
            if a <= 1 or b >= vs.shape[0] - 2:
                flags.append("clipped")
            hi_p = price_of(a)
            lo_p = price_of(b)
            if len(erows):
                top_p, bot_p = price_of(erows.min()), price_of(erows.max())
                if d == 1:
                    o, cl = bot_p, top_p
                elif d == -1:
                    o, cl = top_p, bot_p
                else:
                    o = cl = (top_p + bot_p) / 2
            else:
                o = cl = None
                flags.append("no_body")
            # fully colored candle (barcolor on entry bars): whole span coloured
            wx = min(max(ci, 0), reg.shape[1] - 1)
            above = reg[max(0, a - 3):a, max(0, wx - 1):wx + 2]
            below = reg[b + 1:b + 4, max(0, wx - 1):wx + 2]
            if above.size and (above.mean(axis=2) > 60).any():
                flags.append("occ_top")
            if below.size and (below.mean(axis=2) > 60).any():
                flags.append("occ_bot")
            n_gray = int(gray_w[a:b + 1].any(axis=1).sum())
            if lab[max(0, a - 4):b + 5, lo_x:hi_x].any():
                flags.append("label")
            bars.append({"k": k, "xc": float(c + x0), "n_gray": n_gray, "high": round(hi_p, 2), "low": round(lo_p, 2),
                         "open": None if o is None else round(o, 2),
                         "close": None if cl is None else round(cl, 2),
                         "dir": d, "flags": flags, "y_top": int(a + y0), "y_bot": int(b + y0)})
        k += 1
    # drop artefacts: bars need a body edge or >=4 px of vertical extent
    bars = [b for b in bars if not ("no_body" in b["flags"] and b["y_bot"] - b["y_top"] < 4)]
    # last real bar = right end of the contiguous run of bodied bars with real height
    # (future space holds only flat dashed/dotted lines)
    ks = sorted(b["k"] for b in bars if "no_body" not in b["flags"] and b["y_bot"] - b["y_top"] >= 3
                and b["n_gray"] >= 3)
    k_last = None
    if ks:
        # rightmost real candle that sits in a dense run of real candles (future space is sparse junk)
        kset = set(ks)
        dense = [kk for kk in ks if sum(1 for j in range(kk - 10, kk + 1) if j in kset) >= 6]
        k_last = max(dense) if dense else max(ks)
        bars = [b for b in bars if b["k"] <= k_last]
        for b in bars:
            if b["k"] == k_last:
                b["flags"].append("last")
    labels = time_labels(items, lay, x0, ph, pitch)
    return {"ok": True, "layout": lay, "price_fit": pf, "pitch": float(pitch), "phase": float(ph + x0),
            "bars": bars, "labels": labels, "k_last": k_last,
            "headers": headers(items, lay["axis_x"])}


def time_labels(items, lay, x0, ph, pitch):
    out = []
    for it in items:
        if abs(it["y"] + it["h"] / 2 - (lay["time_y"] + 9)) > 16:
            continue
        xc = it["x"] + it["w"] / 2
        if xc > lay["axis_x"] - 2 or xc < x0:
            continue
        t = it["text"].strip()
        k = int(round((xc - x0 - ph) / pitch))
        m = HOUR_RE.match(t)
        if m:
            out.append({"k": k, "kind": "hour", "value": int(m.group(1)) * 60 + int(m.group(2)), "xc": xc})
            continue
        m = YEAR_RE.match(t)
        if m:
            out.append({"k": k, "kind": "year", "value": int(m.group(1)), "xc": xc})
            continue
        m = DAY_RE.match(t)
        if m and 1 <= int(m.group(1)) <= 31:
            out.append({"k": k, "kind": "day", "value": int(m.group(1)), "xc": xc})
            continue
        if t[:3] in MONTHS and len(t) <= 4:
            out.append({"k": k, "kind": "month", "value": MONTHS[t[:3]], "xc": xc})
    return sorted(out, key=lambda d: d["k"])
