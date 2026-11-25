"""The 47 testable setups of the owner's 100-setup catalog (conventions in SPEC.md, written before running).
Gold spot 5m 2012-2026. Every setup is two-sided (written side + mirror). Run: python3 catalog.py > catalog_results.txt"""
import time
import numpy as np, pandas as pd
from common import *

TICK = 0.1
Ol, Hl, Ll, Cl = O.tolist(), H.tolist(), L.tolist(), C.tolist()
POST_LDN0 = smin >= 300                     # after London midnight inside the CME session
prev = lambda x, k=1: np.r_[np.full(k, np.nan), x[:-k]]
prevb = lambda x, k=1: np.r_[np.zeros(k, bool), np.asarray(x, bool)[:-k]]      # boolean shift, False-filled


def S(h, m=0):
    """Chicago clock -> minutes since the 17:00 CT session start."""
    return ((h * 60 + m) - 17 * 60) % 1440


def win(s, clk, lo, hi, mask=None):
    f, l = sfirst[s], slast[s]
    m = (clk[f:l + 1] >= lo) & (clk[f:l + 1] < hi)
    if mask is not None:
        m &= mask[f:l + 1]
    return np.flatnonzero(m) + f


def first_close_outside(gg, rH, rL, lim, tgtR, mid, sigs):
    for i in gg:
        d = 1 if Cl[i] > rH else (-1 if Cl[i] < rL else 0)
        if d:
            sigs.append((i, d, mid - d * TICK, NAN, tgtR, lim, None))
            return


def med_filter(hist, w, n=20):
    ok = len(hist) >= n and w < np.median(hist[-n:])
    hist.append(w)
    return ok


# ------------------------------------------------------------------ 1-10 session / auction
def s01():   # Asian range expansion
    sigs, hist = [], []
    for s in range(nS):
        rr = win(s, smin, S(18), S(0))
        if len(rr) < 72: continue
        rH, rL = H[rr].max(), L[rr].min()
        if not med_filter(hist, rH - rL): continue
        gg = win(s, smin, S(0), S(2))
        if len(gg): first_close_outside(gg, rH, rL, gg[-1], 2.0, (rH + rL) / 2, sigs)
    return sigs


def _fade_back_inside(gg, rH, rL, lim, sigs):
    """First breach of [rL, rH] that closes back inside -> fade; stop beyond the excursion; target the midpoint."""
    mid, eh, el, bh, bl = (rH + rL) / 2, -1e18, 1e18, False, False
    for i in gg:
        if Hl[i] > rH: bh = True; eh = max(eh, Hl[i])
        if Ll[i] < rL: bl = True; el = min(el, Ll[i])
        if rL < Cl[i] < rH:
            if bh and not bl: sigs.append((i, -1, eh + TICK, mid, 0, lim, None)); return
            if bl and not bh: sigs.append((i, 1, el - TICK, mid, 0, lim, None)); return
            if bh and bl: return


def s03():   # London morning reversal (London clock)
    sigs = []
    for s in range(nS):
        rr = win(s, lnm, 7 * 60, 8 * 60, POST_LDN0)
        gg = win(s, lnm, 8 * 60, 10 * 60, POST_LDN0)
        if len(rr) == 12 and len(gg): _fade_back_inside(gg, H[rr].max(), L[rr].min(), gg[-1], sigs)
    return sigs


def s04():   # U.S. opening range breakout
    sigs = []
    for s in range(nS):
        rr = win(s, smin, S(7, 20), S(7, 50)); gg = win(s, smin, S(7, 50), S(9)); xx = win(s, smin, S(7, 50), S(10, 30))
        if len(rr) == 6 and len(gg) and len(xx):
            rH, rL = H[rr].max(), L[rr].min(); first_close_outside(gg, rH, rL, xx[-1], 2.0, (rH + rL) / 2, sigs)
    return sigs


def s05():   # opening drive pullback
    sigs, hist = [], []
    for s in range(nS):
        rr = win(s, smin, S(7, 20), S(7, 50))
        if len(rr) < 6: continue
        drive = C[rr[-1]] - O[rr[0]]
        ok = len(hist) >= 20 and abs(drive) > np.median(hist[-20:]); hist.append(abs(drive))
        if not ok or drive == 0: continue
        d = 1 if drive > 0 else -1
        gg = win(s, smin, S(7, 50), S(10))
        if not len(gg): continue
        run, armed, trig, ext = [], False, 0.0, 0.0
        for i in gg:
            if armed and d * (Cl[i] - trig) > 0:
                sigs.append((i, d, ext - d * TICK, NAN, 2.0, gg[-1], None)); break
            if d * (Cl[i] - Ol[i]) < 0:
                run.append(i)
                if len(run) >= 2:
                    a, b = run[-2], run[-1]; armed = True
                    trig = max(Hl[a], Hl[b]) if d == 1 else min(Ll[a], Ll[b])
                    ext = min(Ll[a], Ll[b]) if d == 1 else max(Hl[a], Hl[b])
            else:
                run = []
                if armed: ext = min(ext, Ll[i]) if d == 1 else max(ext, Hl[i])
    return sigs


def s07():   # lunch range expansion
    sigs, hist = [], []
    for s in range(nS):
        rr = win(s, smin, S(10, 30), S(12))
        if len(rr) < 18: continue
        rH, rL = H[rr].max(), L[rr].min()
        if not med_filter(hist, rH - rL): continue
        gg = win(s, smin, S(12), S(13)); xx = win(s, smin, S(12), S(13, 30))
        if len(gg) and len(xx): first_close_outside(gg, rH, rL, xx[-1], 1.5, (rH + rL) / 2, sigs)
    return sigs


def s08():   # LBMA morning auction reaction (London 10:30)
    sigs = []
    for s in range(nS):
        rr = win(s, lnm, 630, 640, POST_LDN0); gg = win(s, lnm, 640, 675, POST_LDN0)
        if len(rr) < 2 or not len(gg): continue
        net = C[rr[-1]] - O[rr[0]]
        if net == 0: continue
        d = 1 if net > 0 else -1; rH, rL = H[rr].max(), L[rr].min(); mid = (rH + rL) / 2
        for i in gg:
            if (d == 1 and Cl[i] > rH) or (d == -1 and Cl[i] < rL):
                sigs.append((i, d, mid - d * TICK, NAN, 1.5, gg[-1], None)); break
    return sigs


def s09():   # LBMA afternoon auction fade (London 15:00)
    sigs = []
    for s in range(nS):
        pre = win(s, lnm, 870, 900, POST_LDN0); au = win(s, lnm, 900, 910, POST_LDN0); gg = win(s, lnm, 910, 945, POST_LDN0)
        if len(pre) < 6 or len(au) < 2 or not len(gg): continue
        pH, pL = H[pre].max(), L[pre].min(); up, dn = H[au].max() > pH, L[au].min() < pL
        if up == dn: continue
        ext = H[au].max() if up else L[au].min()
        for i in gg:
            ext = max(ext, Hl[i]) if up else min(ext, Ll[i])
            if pL < Cl[i] < pH:
                sigs.append((i, -1 if up else 1, ext + TICK if up else ext - TICK, (pH + pL) / 2, 0, gg[-1], None)); break
    return sigs


def s10():   # post-settlement reversal
    sigs = []
    for s in range(nS):
        rr = win(s, smin, S(12, 15), S(12, 30)); gg = win(s, smin, S(12, 30), S(13)); xx = win(s, smin, S(12, 30), S(13, 30))
        if len(rr) == 3 and len(gg) and len(xx): _fade_back_inside(gg, H[rr].max(), L[rr].min(), xx[-1], sigs)
    return sigs


# ------------------------------------------------------------------ 11-20 trend / pullback
def s11():   # first 20-EMA pullback
    hh, ll = prior_max(H, 20), prior_min(L, 20); pe = prev(E20)
    sigs = []
    for d in (1, -1):
        arm = np.flatnonzero((H > hh) & (C > E20) & (E20 > pe)) if d == 1 else np.flatnonzero((L < ll) & (C < E20) & (E20 < pe))
        armset = set(arm.tolist()); E = E20.tolist()
        k, n_arm = 0, len(arm)
        while k < n_arm:
            i = arm[k]; ext = Hl[i] if d == 1 else Ll[i]; j = i + 1
            while j < N:
                if j in armset:
                    ext = max(ext, Hl[j]) if d == 1 else min(ext, Ll[j]); j += 1; continue
                touch = Ll[j] <= E[j] if d == 1 else Hl[j] >= E[j]
                if touch:
                    if (d == 1 and Cl[j] > E[j]) or (d == -1 and Cl[j] < E[j]):
                        sigs.append((j, d, (Ll[j] - TICK) if d == 1 else (Hl[j] + TICK), ext, 0, j + 12, None))
                    break
                j += 1
            k = np.searchsorted(arm, j, side="right")
    return sigs


def _pivot_events():
    ph, pl = pivots(3)
    ev = sorted([(p + 3, 1, p) for p in ph.tolist()] + [(p + 3, -1, p) for p in pl.tolist()])
    return ph, pl, ev


PH, PL, PEV = _pivot_events()


def _scan(start, stop_at, cond):
    for j in range(start, min(stop_at, N)):
        r = cond(j)
        if r is not None: return j, r
    return None, None


def s12():   # higher-low continuation (first close through the latest swing level; one signal per swing pivot)
    sigs, SHs, SLs, used = [], [], [], set()
    for k, (c, typ, p) in enumerate(PEV):
        (SHs if typ == 1 else SLs).append(p)
        nxt = PEV[k + 1][0] if k + 1 < len(PEV) else N
        if len(SHs) >= 2 and len(SLs) >= 2:
            h1, h2, l1, l2 = Hl[SHs[-2]], Hl[SHs[-1]], Ll[SLs[-2]], Ll[SLs[-1]]
            if h2 > h1 and l2 > l1 and ("H", SHs[-1]) not in used:
                j, _ = _scan(max(c, 1), nxt, lambda j: True if (Cl[j] > h2 and Cl[j - 1] <= h2) else None)
                if j is not None: sigs.append((j, 1, l2 - TICK, NAN, 2.0, j + 18, None)); used.add(("H", SHs[-1]))
            if h2 < h1 and l2 < l1 and ("L", SLs[-1]) not in used:
                j, _ = _scan(max(c, 1), nxt, lambda j: True if (Cl[j] < l2 and Cl[j - 1] >= l2) else None)
                if j is not None: sigs.append((j, -1, h2 + TICK, NAN, 2.0, j + 18, None)); used.add(("L", SLs[-1]))
    return sigs


def s13():   # 9/21 EMA cross with 50-EMA slope
    up, dn = (E9 > E21) & (prev(E9) <= prev(E21)), (E9 < E21) & (prev(E9) >= prev(E21))
    e50p = prev(E50, 5); lo5, hi5 = prior_min(L, 5), prior_max(H, 5)
    sigs = [(i, 1, lo5[i] - TICK, NAN, 0, i + 18, dn) for i in np.flatnonzero(up & (E50 > e50p))]
    sigs += [(i, -1, hi5[i] + TICK, NAN, 0, i + 18, up) for i in np.flatnonzero(dn & (E50 < e50p))]
    return sigs


def s14():   # 30m trend filter + 5m RSI pullback
    b30 = t // 1800
    idx30 = np.flatnonzero(np.r_[b30[1:] != b30[:-1], True])
    c30 = C[idx30]; e30 = ema(c30, 20)
    pos = np.searchsorted(idx30, np.arange(N), side="right") - 1
    ok = pos >= 0; up30 = np.zeros(N, bool); dn30 = np.zeros(N, bool)
    up30[ok] = (c30 > e30)[pos[ok]]; dn30[ok] = (c30 < e30)[pos[ok]]
    rp = prev(RSI); sigs = []; xl, xs = RSI >= 65, RSI <= 35          # shared exit arrays (one copy each)
    last_ge40 = np.maximum.accumulate(np.where(RSI >= 40, np.arange(N), -1))
    last_le60 = np.maximum.accumulate(np.where(RSI <= 60, np.arange(N), -1))
    for i in np.flatnonzero(up30 & (rp < 40) & (RSI >= 40)):
        k = last_ge40[i - 1]
        if k >= 0: sigs.append((i, 1, L[k + 1:i + 1].min() - TICK, NAN, 0, i + 12, xl))
    for i in np.flatnonzero(dn30 & (rp > 60) & (RSI <= 60)):
        k = last_le60[i - 1]
        if k >= 0: sigs.append((i, -1, H[k + 1:i + 1].max() + TICK, NAN, 0, i + 12, xs))
    return sigs


def s15():   # flag continuation
    mv = C - prev(C, 4); sigs, seen = [], set()
    for i in np.flatnonzero(np.abs(mv) >= 2 * ATR):
        if i + 10 >= N: continue
        d = 1 if mv[i] > 0 else -1; m = abs(mv[i])
        fh, fl = max(Hl[i + 1:i + 4]), min(Ll[i + 1:i + 4])
        if (d == 1 and Cl[i] - fl >= 0.5 * m) or (d == -1 and fh - Cl[i] >= 0.5 * m): continue
        for j in range(i + 4, i + 10):
            if (d == 1 and Cl[j] > fh) or (d == -1 and Cl[j] < fl):
                if j not in seen:
                    seen.add(j); sigs.append((j, d, (fl - TICK) if d == 1 else (fh + TICK), Cl[j] + d * m, 0, j + 12, None))
                break
    return sigs


def s16():   # break and retest of a 30-bar high/low
    hh, ll = prior_max(H, 30), prior_min(L, 30); sigs = []
    for d, brk, lvl in ((1, (C > hh) & ~(prev(C) > prev(hh)), hh), (-1, (C < ll) & ~(prev(C) < prev(ll)), ll)):
        for b in np.flatnonzero(brk):
            lv = lvl[b]
            for j in range(b + 1, min(b + 7, N)):
                if (d == 1 and Ll[j] <= lv) or (d == -1 and Hl[j] >= lv):
                    if (d == 1 and Cl[j] > lv) or (d == -1 and Cl[j] < lv):
                        sigs.append((j, d, (Ll[j] - TICK) if d == 1 else (Hl[j] + TICK), NAN, 2.0, j + 12, None))
                    break
    return sigs


def s17():   # ADX trend ignition
    up, dn = (PDI > MDI) & (prev(PDI) <= prev(MDI)), (PDI < MDI) & (prev(PDI) >= prev(MDI))
    ok = (ADX > 25) & (ADX > prev(ADX)); lo5, hi5 = prior_min(L, 5), prior_max(H, 5)
    sigs = [(i, 1, lo5[i] - TICK, NAN, 0, i + 18, dn) for i in np.flatnonzero(up & ok)]
    sigs += [(i, -1, hi5[i] + TICK, NAN, 0, i + 18, up) for i in np.flatnonzero(dn & ok)]
    return sigs


def s18():   # regression channel pullback (prior 30 closes)
    n, xm = 30, 14.5; Sxx = ((np.arange(n) - xm) ** 2).sum()
    cs, cs2 = np.r_[0, np.cumsum(C)], np.r_[0, np.cumsum(C * C)]
    conv = np.convolve(C, np.arange(n - 1, -1, -1), "valid")       # sum k*C[m+k], window start m
    idx = np.arange(n, N)
    Sy = cs[idx] - cs[idx - n]; Syy = cs2[idx] - cs2[idx - n]; Sxy = conv[idx - n] - xm * Sy
    b = Sxy / Sxx; a = Sy / n - b * xm
    sd = np.sqrt(np.maximum((Syy - Sy * Sy / n) - b * Sxy, 0) / n)
    mid = np.full(N, np.nan); slope = np.full(N, np.nan); sdv = np.full(N, np.nan)
    mid[idx] = a + b * n; slope[idx] = b; sdv[idx] = sd
    lo, hi = mid - sdv, mid + sdv
    below, above = C < lo, C > hi; sigs = []
    for i in np.flatnonzero((slope > 0) & (C > lo) & prevb(below)):
        k = i - 1
        while k > 0 and below[k - 1]: k -= 1
        sigs.append((i, 1, L[k:i + 1].min() - TICK, hi[i], 0, i + 12, None))
    for i in np.flatnonzero((slope < 0) & (C < hi) & prevb(above)):
        k = i - 1
        while k > 0 and above[k - 1]: k -= 1
        sigs.append((i, -1, H[k:i + 1].max() + TICK, lo[i], 0, i + 12, None))
    return sigs


def s19():   # shallow retracement after a 3-ATR 10-bar swing
    hh10 = pd.Series(H).rolling(10).max().to_numpy(); ll10 = pd.Series(L).rolling(10).min().to_numpy(); sigs = []
    for d in (1, -1):
        cand = (H >= hh10) & (H - ll10 >= 3 * ATR) & (L > ll10) if d == 1 else (L <= ll10) & (hh10 - L >= 3 * ATR) & (H < hh10)
        for k in np.flatnonzero(cand):
            top = Hl[k] if d == 1 else Ll[k]; sw = (Hl[k] - ll10[k]) if d == 1 else (hh10[k] - Ll[k])
            ext = top; reached = False
            for j in range(k + 1, min(k + 13, N)):
                if (d == 1 and Hl[j] > top) or (d == -1 and Ll[j] < top): break
                ext = min(ext, Ll[j]) if d == 1 else max(ext, Hl[j])
                r = abs(top - ext) / sw
                if r > 0.5: break
                reached = reached or r >= 0.33
                if reached and ((d == 1 and Cl[j] > Hl[j - 1]) or (d == -1 and Cl[j] < Ll[j - 1])):
                    sigs.append((j, d, ext - d * TICK, top, 0, j + 12, None)); break
    return sigs


def s20():   # Keltner trend ride
    ab, be = C > KU, C < KL; pe = prev(E20)
    lg = ab & prevb(ab) & ~prevb(ab, 2) & (E20 > pe)
    sh = be & prevb(be) & ~prevb(be, 2) & (E20 < pe)
    xl, xs = C < E20, C > E20                                         # shared exit arrays (one copy each)
    sigs = [(i, 1, min(Ll[i - 1], Ll[i]) - TICK, NAN, 0, i + 18, xl) for i in np.flatnonzero(lg)]
    sigs += [(i, -1, max(Hl[i - 1], Hl[i]) + TICK, NAN, 0, i + 18, xs) for i in np.flatnonzero(sh)]
    return sigs


# ------------------------------------------------------------------ 21-30 compression / volatility
def s21():   # Bollinger squeeze
    bw = (BBU - BBL) / SMA20
    p10 = pd.Series(bw).rolling(100).quantile(0.10).shift(1).to_numpy()
    sq = prevb(bw < p10)
    sigs = [(i, 1, SMA20[i] - TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(sq & (C > BBU))]
    sigs += [(i, -1, SMA20[i] + TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(sq & (C < BBL))]
    return sigs


def s22():   # inside-bar cluster
    Hp, Lp = H, L
    ins = lambda k: (np.r_[H[k:], np.full(k, np.nan)] <= Hp) & (np.r_[L[k:], np.full(k, np.nan)] >= Lp)
    sigs = []
    for p in np.flatnonzero(ins(1) & ins(2)):
        mid = (Hl[p] + Ll[p]) / 2
        for j in range(p + 3, min(p + 15, N)):
            d = 1 if Cl[j] > Hl[p] else (-1 if Cl[j] < Ll[p] else 0)
            if d: sigs.append((j, d, mid - d * TICK, NAN, 1.5, j + 8, None)); break
    return sigs


def s23():   # narrowest 15-minute bar of the last 8
    b15 = t // 900; last = np.flatnonzero(np.r_[b15[1:] != b15[:-1], True]); first = np.r_[0, last[:-1] + 1]
    h15, l15 = np.maximum.reduceat(H, first), np.minimum.reduceat(L, first); r15 = h15 - l15
    full = (last - first + 1) == 3
    narrow = full & (r15 <= pd.Series(r15).rolling(8).min().to_numpy())
    sigs = []
    for q in np.flatnonzero(narrow):
        e0 = last[q]
        for j in range(e0 + 1, min(e0 + 7, N)):
            d = 1 if Cl[j] > h15[q] else (-1 if Cl[j] < l15[q] else 0)
            if d: sigs.append((j, d, (l15[q] - TICK) if d == 1 else (h15[q] + TICK), NAN, 2.0, j + 8, None)); break
    return sigs


def s24():   # ATR regime expansion
    med = pd.Series(ATR).rolling(50).median().shift(1).to_numpy()
    bl = (ATR < med).astype(float); six = pd.Series(bl).rolling(6).sum().shift(1).to_numpy() == 6
    go = six & (ATR > med)
    sigs = [(i, 1, Ll[i] - TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(go & (C > prior_max(H, 20)))]
    sigs += [(i, -1, Hl[i] + TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(go & (C < prior_min(L, 20)))]
    return sigs


def s26():   # low-volatility box retest
    bh, bl = prior_max(H, 6), prior_min(L, 6); nar = (bh - bl) < 1.5 * prev(ATR); sigs = []
    for d, brk, lvl in ((1, nar & (C > bh), bh), (-1, nar & (C < bl), bl)):
        for b in np.flatnonzero(brk):
            lv = lvl[b]
            for j in range(b + 1, min(b + 7, N)):
                if (d == 1 and Ll[j] <= lv) or (d == -1 and Hl[j] >= lv):
                    if (d == 1 and Cl[j] > lv) or (d == -1 and Cl[j] < lv):
                        sigs.append((j, d, (Ll[j] - TICK) if d == 1 else (Hl[j] + TICK), NAN, 2.0, j + 12, None))
                    break
    return sigs


def s27():   # two-bar breakout acceptance
    rh, rl = prior_max(H, 20), prior_min(L, 20); sigs = []
    for b in np.flatnonzero((C > rh) & ~(prev(C) > prev(rh))):
        if b + 1 < N and Cl[b + 1] > rh[b] and Cl[b + 1] > Cl[b]: sigs.append((b + 1, 1, rh[b] - TICK, NAN, 2.0, b + 11, None))
    for b in np.flatnonzero((C < rl) & ~(prev(C) < prev(rl))):
        if b + 1 < N and Cl[b + 1] < rl[b] and Cl[b + 1] < Cl[b]: sigs.append((b + 1, -1, rl[b] + TICK, NAN, 2.0, b + 11, None))
    return sigs


def s28():   # volatility shock snapback
    sigs = []
    for s_ in np.flatnonzero((H - L) >= 2.5 * prev(ATR)):
        j = s_ + 1
        if j >= N: continue
        mid = (Hl[s_] + Ll[s_]) / 2
        if Cl[s_] > Ol[s_] and Cl[j] < mid: sigs.append((j, -1, max(Hl[s_], Hl[j]) + TICK, Ol[s_], 0, j + 6, None))
        if Cl[s_] < Ol[s_] and Cl[j] > mid: sigs.append((j, 1, min(Ll[s_], Ll[j]) - TICK, Ol[s_], 0, j + 6, None))
    return sigs


def s29():   # compression inside a trend
    cmx, cmn = prior_max(C, 6), prior_min(C, 6); tight = (cmx - cmn) <= prev(ATR)
    hh6, ll6 = prior_max(H, 6), prior_min(L, 6); e50r = prev(E50) > prev(E50, 7)
    lg = tight & e50r & (C > hh6) & ~(prev(C) > prev(hh6)); sh = tight & ~e50r & (C < ll6) & ~(prev(C) < prev(ll6))
    sigs = [(i, 1, ll6[i] - TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(lg)]
    sigs += [(i, -1, hh6[i] + TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(sh)]
    return sigs


def s30():   # Bollinger inside Keltner, then release
    sq = prevb((BBU < KU) & (BBL > KL))
    sigs = [(i, 1, E20[i] - TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(sq & (BBU > KU) & (C > KU))]
    sigs += [(i, -1, E20[i] + TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(sq & (BBL < KL) & (C < KL))]
    return sigs


# ------------------------------------------------------------------ 41-50 prior-session levels
def _first_per_session(idx):
    seen, out = set(), []
    for i in idx:
        if sid[i] not in seen: seen.add(sid[i]); out.append(i)
    return out


def s41():   # prior-day high / low acceptance
    ab, be = C > pdh, C < pdl; same = sid == np.r_[-1, sid[:-1]]
    ab1, be1 = prevb(ab) & same, prevb(be) & same
    sigs = [(i, 1, min(Ll[i - 1], Ll[i]) - TICK, NAN, 2.0, i + 12, None) for i in _first_per_session(np.flatnonzero(ab & ab1))]
    sigs += [(i, -1, max(Hl[i - 1], Hl[i]) + TICK, NAN, 2.0, i + 12, None) for i in _first_per_session(np.flatnonzero(be & be1))]
    return sigs


def _reclaim(level_lo, level_hi, tgtR, n_hold):
    """Trade below level_lo then close back above it -> long (and mirror at level_hi) -> first per session."""
    cmin = pd.Series(L).groupby(sid).cummin().to_numpy(); cmax = pd.Series(H).groupby(sid).cummax().to_numpy()
    sigs = [(i, 1, cmin[i] - TICK, NAN, tgtR, i + n_hold, None)
            for i in _first_per_session(np.flatnonzero((cmin < level_lo) & (C > level_lo)))]
    sigs += [(i, -1, cmax[i] + TICK, NAN, tgtR, i + n_hold, None)
             for i in _first_per_session(np.flatnonzero((cmax > level_hi) & (C < level_hi)))]
    return sigs


def s42(): return _reclaim(pdl, pdh, 2.0, 12)          # prior-day low trap (+ high trap)
def s43(): return _reclaim(pwl, pwh, 2.0, 12)          # prior-week high rejection (+ low)


def s44():   # prior-week midpoint reclaim after six closes on the other side
    pm = (pwh + pwl) / 2
    b6 = np.ones(N, bool); a6 = np.ones(N, bool)
    for k in range(1, 7):
        ck = prev(C, k); b6 &= ck < pm; a6 &= ck > pm
    sigs = [(i, 1, Ll[i] - TICK, NAN, 2.0, i + 18, None) for i in np.flatnonzero(b6 & (C > pm))]
    sigs += [(i, -1, Hl[i] + TICK, NAN, 2.0, i + 18, None) for i in np.flatnonzero(a6 & (C < pm))]
    return sigs


def _gap(s):
    f = sfirst[s]; st, da = prev_settle[s], prev_datr[s]
    if not (st == st and da == da): return None
    g = O[f] - st
    return (g, st) if abs(g) >= 0.5 * da else None


def s45():   # settlement gap fill
    sigs = []
    for s in range(nS):
        gs = _gap(s)
        if gs is None: continue
        g, st = gs; f = sfirst[s]; ro = O[f]
        for i in win(s, smin, 0, 60):
            if smin[i] % 15 != 10: continue                 # last 5m bar of each 15m bar
            if g > 0 and Cl[i] < ro: sigs.append((i, -1, H[f:i + 1].max() + TICK, st, 0, i + 12, None)); break
            if g < 0 and Cl[i] > ro: sigs.append((i, 1, L[f:i + 1].min() - TICK, st, 0, i + 12, None)); break
    return sigs


def s46():   # settlement gap continuation
    sigs = []
    for s in range(nS):
        gs = _gap(s)
        if gs is None: continue
        g, _ = gs; rr = win(s, smin, 0, 60)
        if len(rr) < 12: continue
        rH, rL = H[rr].max(), L[rr].min(); mid = (rH + rL) / 2
        for i in win(s, smin, 60, 120):
            if g > 0 and Cl[i] > rH: sigs.append((i, 1, mid - TICK, NAN, 2.0, i + 12, None)); break
            if g < 0 and Cl[i] < rL: sigs.append((i, -1, mid + TICK, NAN, 2.0, i + 12, None)); break
    return sigs


def s47():   # prior-range midpoint rotation (ADX < 20)
    sigs = []; Al = ADX.tolist()
    for s in range(1, nS):
        f, l = sfirst[s], slast[s]; ph, pl_ = sH[s - 1], sL[s - 1]
        if not (pl_ < O[f] < ph): continue
        pm = (ph + pl_) / 2; dipped = rallied = False; lo = 1e18; hi = -1e18; done_l = done_s = False
        for i in range(f, l + 1):
            if Cl[i] < pm: dipped = True; lo = min(lo, Ll[i])
            if Cl[i] > pm: rallied = True; hi = max(hi, Hl[i])
            if dipped: lo = min(lo, Ll[i])
            if rallied: hi = max(hi, Hl[i])
            if not done_l and dipped and Cl[i] > pm and (i == f or Cl[i - 1] <= pm) and Al[i] < 20:
                sigs.append((i, 1, lo - TICK, ph, 0, i + 12, None)); done_l = True
            if not done_s and rallied and Cl[i] < pm and (i == f or Cl[i - 1] >= pm) and Al[i] < 20:
                sigs.append((i, -1, hi + TICK, pl_, 0, i + 12, None)); done_s = True
    return sigs


def s48():   # $25 round-number rejection
    up = np.floor(H / 25) * 25; dn = np.ceil(L / 25) * 25
    sh = (O < up) & (H > up) & (C <= up - 0.5); lg = (O > dn) & (L < dn) & (C >= dn + 0.5)
    sigs = [(i, -1, Hl[i] + TICK, NAN, 1.5, i + 8, None) for i in np.flatnonzero(sh)]
    sigs += [(i, 1, Ll[i] - TICK, NAN, 1.5, i + 8, None) for i in np.flatnonzero(lg)]
    return sigs


def s49():   # daily pivot reversal after a 0.5-ATR excursion
    pv = (pdh + pdl + pdc) / 3
    lo_hit = pd.Series((L <= pv - 0.5 * ATR).astype(int)).groupby(sid).cummax().to_numpy().astype(bool)
    hi_hit = pd.Series((H >= pv + 0.5 * ATR).astype(int)).groupby(sid).cummax().to_numpy().astype(bool)
    cmin = pd.Series(L).groupby(sid).cummin().to_numpy(); cmax = pd.Series(H).groupby(sid).cummax().to_numpy()
    sigs = [(i, 1, cmin[i] - TICK, NAN, 1.5, i + 10, None) for i in _first_per_session(np.flatnonzero(lo_hit & (C > pv)))]
    sigs += [(i, -1, cmax[i] + TICK, NAN, 1.5, i + 10, None) for i in _first_per_session(np.flatnonzero(hi_hit & (C < pv)))]
    return sigs


def s50():   # weekly open retest after an hour on one side
    sw = wid == prev(wid.astype(float), 12)
    ab = np.ones(N, bool); be = np.ones(N, bool)
    for k in range(1, 13):
        ab &= (prev(L, k) > wopen) & (prev(C, k) > wopen); be &= (prev(H, k) < wopen) & (prev(C, k) < wopen)
    sigs = [(i, 1, Ll[i] - TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(sw & ab & (L <= wopen) & (C > wopen))]
    sigs += [(i, -1, Hl[i] + TICK, NAN, 2.0, i + 12, None) for i in np.flatnonzero(sw & be & (H >= wopen) & (C < wopen))]
    return sigs


# ------------------------------------------------------------------ 51-60 failed moves / reversals
def _last_two(ev_typ):
    """Yield (confirm_idx, next_same_type_confirm, p1, p2) for consecutive pivots of one type."""
    ps = [(c, p) for c, typ, p in PEV if typ == ev_typ]
    for k in range(1, len(ps)):
        yield ps[k][0], (ps[k + 1][0] if k + 1 < len(ps) else N), ps[k - 1][1], ps[k][1]


def s51():   # equal highs / lows swept and closed back
    sigs = []
    for c, nxt, p1, p2 in _last_two(1):
        a, b = Hl[p1], Hl[p2]
        if abs(a - b) > 0.2 * ATR[p2]: continue
        top, bot = max(a, b), min(a, b); tgt = min(Ll[p1:p2 + 1])
        for j in range(c, min(nxt, c + 100, N)):
            if Hl[j] > top:
                if Cl[j] < bot: sigs.append((j, -1, Hl[j] + TICK, tgt, 0, j + 10, None))
                break
    for c, nxt, p1, p2 in _last_two(-1):
        a, b = Ll[p1], Ll[p2]
        if abs(a - b) > 0.2 * ATR[p2]: continue
        top, bot = max(a, b), min(a, b); tgt = max(Hl[p1:p2 + 1])
        for j in range(c, min(nxt, c + 100, N)):
            if Ll[j] < bot:
                if Cl[j] > top: sigs.append((j, 1, Ll[j] - TICK, tgt, 0, j + 10, None))
                break
    return sigs


def s52():   # failed breakout retest -> reversal
    ll, hh = prior_min(L, 20), prior_max(H, 20); sigs = []
    for b in np.flatnonzero((C < ll) & ~(prev(C) < prev(ll))):
        lv, mid = ll[b], (hh[b] + ll[b]) / 2
        for j in range(b + 1, min(b + 13, N - 1)):
            if Hl[j] >= lv and Cl[j] > lv:
                if Cl[j + 1] > Cl[j]: sigs.append((j + 1, 1, min(Ll[b:j + 2]) - TICK, mid, 0, j + 13, None))
                break
    for b in np.flatnonzero((C > hh) & ~(prev(C) > prev(hh))):
        lv, mid = hh[b], (hh[b] + ll[b]) / 2
        for j in range(b + 1, min(b + 13, N - 1)):
            if Ll[j] <= lv and Cl[j] < lv:
                if Cl[j + 1] < Cl[j]: sigs.append((j + 1, -1, max(Hl[b:j + 2]) + TICK, mid, 0, j + 13, None))
                break
    return sigs


def s53():   # double bottom / top confirmation
    sigs = []
    for c, nxt, p1, p2 in _last_two(-1):
        if abs(Ll[p1] - Ll[p2]) > 0.25 * ATR[p2]: continue
        neck = max(Hl[p1:p2 + 1]); ht = neck - min(Ll[p1], Ll[p2])
        for j in range(c, min(nxt, c + 24, N)):
            if Cl[j] < Ll[p2]: break
            if Cl[j] > neck: sigs.append((j, 1, Ll[p2] - TICK, neck + ht, 0, j + 12, None)); break
    for c, nxt, p1, p2 in _last_two(1):
        if abs(Hl[p1] - Hl[p2]) > 0.25 * ATR[p2]: continue
        neck = min(Ll[p1:p2 + 1]); ht = max(Hl[p1], Hl[p2]) - neck
        for j in range(c, min(nxt, c + 24, N)):
            if Cl[j] > Hl[p2]: break
            if Cl[j] < neck: sigs.append((j, -1, Hl[p2] + TICK, neck - ht, 0, j + 12, None)); break
    return sigs


def s54():   # RSI divergence
    sigs = []
    for c, nxt, p1, p2 in _last_two(-1):
        if not (Ll[p2] < Ll[p1] and RSI[p2] > RSI[p1]): continue
        trig = max(Hl[p1:p2 + 1])
        for j in range(c, min(nxt, c + 24, N)):
            if Cl[j] < Ll[p2]: break
            if Cl[j] > trig: sigs.append((j, 1, Ll[p2] - TICK, NAN, 2.0, j + 12, None)); break
    for c, nxt, p1, p2 in _last_two(1):
        if not (Hl[p2] > Hl[p1] and RSI[p2] < RSI[p1]): continue
        trig = min(Ll[p1:p2 + 1])
        for j in range(c, min(nxt, c + 24, N)):
            if Cl[j] > Hl[p2]: break
            if Cl[j] < trig: sigs.append((j, -1, Hl[p2] + TICK, NAN, 2.0, j + 12, None)); break
    return sigs


def s55():   # three-push exhaustion
    sigs = []
    for typ in (1, -1):
        ps = [(c, p) for c, ty, p in PEV if ty == typ]
        opp = PL if typ == 1 else PH
        for k in range(2, len(ps)):
            (c, p3), p2, p1 = ps[k], ps[k - 1][1], ps[k - 2][1]
            nxt = ps[k + 1][0] if k + 1 < len(ps) else N
            v1, v2, v3 = (Hl[p1], Hl[p2], Hl[p3]) if typ == 1 else (-Ll[p1], -Ll[p2], -Ll[p3])
            if not (v1 < v2 < v3 and (v3 - v2) < (v2 - v1)): continue
            mids = opp[(opp > p2) & (opp < p3)]
            if typ == 1:
                lv = Ll[mids[-1]] if len(mids) else min(Ll[p2:p3 + 1])
                for j in range(c, min(nxt, c + 24, N)):
                    if Cl[j] > Hl[p3]: break
                    if Cl[j] < lv: sigs.append((j, -1, Hl[p3] + TICK, NAN, 2.0, j + 12, None)); break
            else:
                lv = Hl[mids[-1]] if len(mids) else max(Hl[p2:p3 + 1])
                for j in range(c, min(nxt, c + 24, N)):
                    if Cl[j] < Ll[p3]: break
                    if Cl[j] > lv: sigs.append((j, 1, Ll[p3] - TICK, NAN, 2.0, j + 12, None)); break
    return sigs


def s56():   # pin bar at a 30-bar extreme
    body = np.abs(C - O); rg = H - L; lw = np.minimum(O, C) - L; uw = H - np.maximum(O, C)
    bull = (L <= prior_min(L, 30)) & (lw >= 2 * body) & (C >= L + 0.75 * rg) & (rg > 0)
    bear = (H >= prior_max(H, 30)) & (uw >= 2 * body) & (C <= H - 0.75 * rg) & (rg > 0)
    sigs = [(p + 1, 1, Ll[p] - TICK, NAN, 1.5, p + 9, None) for p in np.flatnonzero(bull) if p + 1 < N and Cl[p + 1] > Hl[p]]
    sigs += [(p + 1, -1, Hl[p] + TICK, NAN, 1.5, p + 9, None) for p in np.flatnonzero(bear) if p + 1 < N and Cl[p + 1] < Ll[p]]
    return sigs


def s57():   # engulfing after four lower / higher closes
    c1, c2, c3, c4, c5 = (prev(C, k) for k in range(1, 6)); o1, h1, l1 = prev(O), prev(H), prev(L)
    low4 = (c1 < c2) & (c2 < c3) & (c3 < c4) & (c4 < c5); hi4 = (c1 > c2) & (c2 > c3) & (c3 > c4) & (c4 > c5)
    beng = (C > O) & (O <= np.minimum(o1, c1)) & (C >= np.maximum(o1, c1)) & (C > h1)
    seng = (C < O) & (O >= np.maximum(o1, c1)) & (C <= np.minimum(o1, c1)) & (C < l1)
    sigs = [(i, 1, min(Ll[i - 1], Ll[i]) - TICK, NAN, 1.5, i + 8, None) for i in np.flatnonzero(low4 & beng)]
    sigs += [(i, -1, max(Hl[i - 1], Hl[i]) + TICK, NAN, 1.5, i + 8, None) for i in np.flatnonzero(hi4 & seng)]
    return sigs


def s58():   # z-score snap back (30 closes)
    s_ = pd.Series(C); m = s_.rolling(30).mean().shift(1).to_numpy(); sd = s_.rolling(30).std(ddof=0).shift(1).to_numpy()
    z = (C - m) / sd; zp = prev(z); sigs = []
    for i in np.flatnonzero((zp <= -2) & (z > -2)):
        k = i - 1
        while k > 0 and z[k - 1] <= -2: k -= 1
        if z[k:i].min() <= -2.5: sigs.append((i, 1, L[k:i + 1].min() - TICK, m[i], 0, i + 8, None))
    for i in np.flatnonzero((zp >= 2) & (z < 2)):
        k = i - 1
        while k > 0 and z[k - 1] >= 2: k -= 1
        if z[k:i].max() >= 2.5: sigs.append((i, -1, H[k:i + 1].max() + TICK, m[i], 0, i + 8, None))
    return sigs


def s59():   # stalled breakout
    rh, rl = prior_max(H, 20), prior_min(L, 20); sigs = []
    for b in np.flatnonzero((C > rh) & ~(prev(C) > prev(rh))):
        if b + 3 < N and max(Hl[b + 1:b + 4]) - Cl[b] < 0.25 * ATR[b] and Cl[b + 3] < rh[b]:
            sigs.append((b + 3, -1, max(Hl[b:b + 4]) + TICK, (rh[b] + rl[b]) / 2, 0, b + 13, None))
    for b in np.flatnonzero((C < rl) & ~(prev(C) < prev(rl))):
        if b + 3 < N and Cl[b] - min(Ll[b + 1:b + 4]) < 0.25 * ATR[b] and Cl[b + 3] > rl[b]:
            sigs.append((b + 3, 1, min(Ll[b:b + 4]) - TICK, (rh[b] + rl[b]) / 2, 0, b + 13, None))
    return sigs


def s60():   # two-sided range trap
    rh, rl = prior_max(H, 12), prior_min(L, 12)
    fmax = pd.Series(H[::-1]).rolling(6, min_periods=1).max().to_numpy()[::-1]
    fmin = pd.Series(L[::-1]).rolling(6, min_periods=1).min().to_numpy()[::-1]
    sigs, seen = [], set()
    for f in np.flatnonzero((fmax > rh) & (fmin < rl)):
        hi_at = lo_at = None
        for j in range(f, min(f + 6, N)):
            if hi_at is None and Hl[j] > rh[f]: hi_at = j
            if lo_at is None and Ll[j] < rl[f]: lo_at = j
        if hi_at is None or lo_at is None or hi_at == lo_at: continue
        mid = (rh[f] + rl[f]) / 2
        if hi_at < lo_at:   # high swept first, then low -> buy the close back inside
            for j in range(lo_at, min(lo_at + 4, N)):
                if Cl[j] > rl[f]:
                    if j not in seen: seen.add(j); sigs.append((j, 1, min(Ll[lo_at:j + 1]) - TICK, mid, 0, j + 8, None))
                    break
        else:
            for j in range(hi_at, min(hi_at + 4, N)):
                if Cl[j] < rh[f]:
                    if j not in seen: seen.add(j); sigs.append((j, -1, max(Hl[hi_at:j + 1]) + TICK, mid, 0, j + 8, None))
                    break
    return sigs


REG = [("01 Asian range expansion", s01), ("03 London morning reversal", s03), ("04 U.S. opening range breakout", s04),
       ("05 Opening drive pullback", s05), ("07 Lunch range expansion", s07), ("08 LBMA AM auction reaction", s08),
       ("09 LBMA PM auction fade", s09), ("10 Post-settlement reversal", s10), ("11 First 20-EMA pullback", s11),
       ("12 Higher-low continuation", s12), ("13 9/21 EMA shift", s13), ("14 Multi-timeframe RSI pullback", s14),
       ("15 Flag continuation", s15), ("16 Break-and-retest", s16), ("17 ADX trend ignition", s17),
       ("18 Trend channel pullback", s18), ("19 Shallow retracement", s19), ("20 Keltner trend ride", s20),
       ("21 Bollinger squeeze", s21), ("22 Inside-bar cluster", s22), ("23 Narrowest 15m bar", s23),
       ("24 ATR regime expansion", s24), ("26 Low-vol box retest", s26), ("27 Two-bar breakout acceptance", s27),
       ("28 Volatility shock snapback", s28), ("29 Compression in a trend", s29), ("30 Double compression break", s30),
       ("41 Prior-day high acceptance", s41), ("42 Prior-day low trap", s42), ("43 Prior-week high rejection", s43),
       ("44 Prior-week midpoint reclaim", s44), ("45 Settlement gap fill", s45), ("46 Settlement gap continuation", s46),
       ("47 Prior-range midpoint rotation", s47), ("48 Round-number rejection", s48), ("49 Daily pivot reversal", s49),
       ("50 Weekly open retest", s50), ("51 Equal-high sweep", s51), ("52 Failed retest reversal", s52),
       ("53 Double-bottom confirmation", s53), ("54 RSI divergence", s54), ("55 Three-push exhaustion", s55),
       ("56 Pin-bar reversal", s56), ("57 Engulfing reversal", s57), ("58 Price z-score reversal", s58),
       ("59 Stalled breakout", s59), ("60 Two-sided range trap", s60)]

if __name__ == "__main__":
    import sys
    only = set(sys.argv[1:])
    rows = []
    for name, fn in REG:
        if only and name[:2] not in only: continue
        t0 = time.time(); T = simulate(fn()); ev = evaluate(T); ev["setup"] = name; rows.append(ev)
        T.to_csv(f"trades/{name[:2]}.csv", index=False)
        print(f"{name:34s} n {ev['n']:6d} ({ev['per_yr']:5.0f}/yr)  PF {ev['PF']:.2f}  "
              f"[{ev['PF_12_19']:.2f} {ev['PF_20_23']:.2f} {ev['PF_24_26']:.2f}]  net ${ev['usd']:+9,.0f}  "
              f"L ${ev['long_usd']:+8,.0f} S ${ev['short_usd']:+8,.0f}  @0.5 ${ev['usd_at_05']:+9,.0f}  "
              f"yrs+ {ev['yrs_pos']:2d}  {'PASS' if ev['PASS'] else '-'}  ({time.time() - t0:.0f}s)", flush=True)
    R = pd.DataFrame(rows).set_index("setup")
    R.to_csv("scoreboard.csv")
    print(f"\nPASS: {int(R.PASS.sum())} of {len(R)} | PF>1 overall: {(R.PF > 1).sum()} | PF>1 in all 3 periods: "
          f"{((R.PF_12_19 > 1) & (R.PF_20_23 > 1) & (R.PF_24_26 > 1)).sum()} | profitable at 0.5 pt: {(R.usd_at_05 > 0).sum()}")
