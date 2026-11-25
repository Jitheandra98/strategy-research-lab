"""MARKET-STRUCTURE ENGINE (2026-11-09). Rules: SPEC.md (written before testing).
Swings (k = 5), BOS / CHoCH, sweeps, order blocks and fair value gaps on 5m / 15m / 1h / 4h bars built from 5 m bars
(aligned to the 18:00 New York open). Orders fill and exits run on the 5 m bars. No look-ahead: a swing exists only after
the bar k bars later has closed, and every order starts on the first 5 m bar after its signal bar closed."""
import numpy as np, pandas as pd
from numba import njit

K, MINFVG, VALID, MAXHOLD = 5, 0.25, 20, 100
TF_MIN = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1D": 1440}
HTF = {"5m": "1h", "15m": "4h", "1h": "1D", "4h": "1D"}
ENTRIES = ["BOS break", "CHoCH break", "BOS retest", "CHoCH discount", "Liquidity sweep", "Order block",
           "Fair value gap", "Higher low"]
LIMIT_TYPES = (2, 3, 5, 6)
STOPS = ["structure -0.1 ATR", "structure -0.5 ATR", "structure -1.0 ATR", "1.5 ATR", "3 ATR"]
EXITS = ["TP 0.5R", "TP 1R", "TP 1.5R", "TP 2R", "TP 3R", "TP 5R", "Trail swings", "BE then 3R", "Time only"]
DAY_NS = 86_400 * 10 ** 9


# ------------------------------------------------------------------------------------------------- structure
@njit(cache=True)
def structure(o, h, l, c, atr, k, minfvg):
    M = len(c)
    maxev = 2 * M + 16
    eb = np.empty(maxev, np.int64); ed = np.empty(maxev, np.int64); et = np.empty(maxev, np.int64)
    elim = np.empty(maxev); elvl = np.empty(maxev)
    swb = np.empty(2 * M + 2, np.int64); swp = np.empty(2 * M + 2); sws = np.empty(2 * M + 2, np.int64)
    bias = np.zeros(M, np.int64)
    ne, ns, cur = 0, 0, 0
    sh, sh_bar, sh_x, sh_sw, prev_sh = np.nan, -1, True, True, np.nan
    sl, sl_bar, sl_x, sl_sw, prev_sl = np.nan, -1, True, True, np.nan
    for b in range(M):
        p = b - k
        if p >= k:
            hp = h[p]
            ok = True
            for q in range(p - k, p):
                if h[q] >= hp:
                    ok = False; break
            if ok:
                for q in range(p + 1, b + 1):
                    if h[q] > hp:
                        ok = False; break
            if ok:
                prev_sh = sh
                sh, sh_bar, sh_x, sh_sw = hp, p, False, False
                swb[ns] = b; swp[ns] = hp; sws[ns] = 1; ns += 1
                if cur == -1 and prev_sh == prev_sh and hp < prev_sh:          # lower high in a down bias -> sell
                    eb[ne] = b; ed[ne] = -1; et[ne] = 7; elim[ne] = np.nan; elvl[ne] = hp; ne += 1
            lp = l[p]
            ok = True
            for q in range(p - k, p):
                if l[q] <= lp:
                    ok = False; break
            if ok:
                for q in range(p + 1, b + 1):
                    if l[q] < lp:
                        ok = False; break
            if ok:
                prev_sl = sl
                sl, sl_bar, sl_x, sl_sw = lp, p, False, False
                swb[ns] = b; swp[ns] = lp; sws[ns] = -1; ns += 1
                if cur == 1 and prev_sl == prev_sl and lp > prev_sl:           # higher low in an up bias -> buy
                    eb[ne] = b; ed[ne] = 1; et[ne] = 7; elim[ne] = np.nan; elvl[ne] = lp; ne += 1
        # ---- break up
        if (not sh_x) and c[b] > sh:
            sh_x = True
            typ = 0 if cur == 1 else 1
            plo, qi = l[sh_bar], sh_bar
            for z in range(sh_bar, b + 1):
                if l[z] < plo:
                    plo, qi = l[z], z
            eb[ne] = b; ed[ne] = 1; et[ne] = typ; elim[ne] = np.nan; elvl[ne] = plo; ne += 1
            if typ == 0:
                eb[ne] = b; ed[ne] = 1; et[ne] = 2; elim[ne] = sh; elvl[ne] = plo; ne += 1
            else:
                hh = h[qi]
                for z in range(qi, b + 1):
                    if h[z] > hh: hh = h[z]
                eb[ne] = b; ed[ne] = 1; et[ne] = 3; elim[ne] = 0.5 * (plo + hh); elvl[ne] = plo; ne += 1
            ob, obl = -1, np.inf
            for z in range(sh_bar, b + 1):
                if c[z] < o[z] and l[z] < obl:
                    obl, ob = l[z], z
            if ob >= 0:
                eb[ne] = b; ed[ne] = 1; et[ne] = 5; elim[ne] = h[ob]; elvl[ne] = l[ob]; ne += 1
            for z in range(b, qi + 1, -1):
                if l[z] > h[z - 2] and (l[z] - h[z - 2]) >= minfvg * atr[b]:
                    eb[ne] = b; ed[ne] = 1; et[ne] = 6; elim[ne] = l[z]; elvl[ne] = h[z - 2]; ne += 1
                    break
            cur = 1
        # ---- break down
        if (not sl_x) and c[b] < sl:
            sl_x = True
            typ = 0 if cur == -1 else 1
            phi, qi = h[sl_bar], sl_bar
            for z in range(sl_bar, b + 1):
                if h[z] > phi:
                    phi, qi = h[z], z
            eb[ne] = b; ed[ne] = -1; et[ne] = typ; elim[ne] = np.nan; elvl[ne] = phi; ne += 1
            if typ == 0:
                eb[ne] = b; ed[ne] = -1; et[ne] = 2; elim[ne] = sl; elvl[ne] = phi; ne += 1
            else:
                ll = l[qi]
                for z in range(qi, b + 1):
                    if l[z] < ll: ll = l[z]
                eb[ne] = b; ed[ne] = -1; et[ne] = 3; elim[ne] = 0.5 * (phi + ll); elvl[ne] = phi; ne += 1
            ob, obh = -1, -np.inf
            for z in range(sl_bar, b + 1):
                if c[z] > o[z] and h[z] > obh:
                    obh, ob = h[z], z
            if ob >= 0:
                eb[ne] = b; ed[ne] = -1; et[ne] = 5; elim[ne] = l[ob]; elvl[ne] = h[ob]; ne += 1
            for z in range(b, qi + 1, -1):
                if h[z] < l[z - 2] and (l[z - 2] - h[z]) >= minfvg * atr[b]:
                    eb[ne] = b; ed[ne] = -1; et[ne] = 6; elim[ne] = h[z]; elvl[ne] = l[z - 2]; ne += 1
                    break
            cur = -1
        # ---- liquidity sweeps (wick through an unbroken swing, close back inside)
        if (not sl_x) and (not sl_sw) and l[b] < sl and c[b] >= sl:
            sl_sw = True
            eb[ne] = b; ed[ne] = 1; et[ne] = 4; elim[ne] = np.nan; elvl[ne] = l[b]; ne += 1
        if (not sh_x) and (not sh_sw) and h[b] > sh and c[b] <= sh:
            sh_sw = True
            eb[ne] = b; ed[ne] = -1; et[ne] = 4; elim[ne] = np.nan; elvl[ne] = h[b]; ne += 1
        bias[b] = cur
    return eb[:ne], ed[:ne], et[:ne], elim[:ne], elvl[:ne], swb[:ns], swp[:ns], sws[:ns], bias


# ------------------------------------------------------------------------------------------------- fills + exits
@njit(cache=True)
def fills(O, H, L, start, end, d, lim, tick):
    n, N = len(start), len(O)
    fi = np.full(n, -1, np.int64); fp = np.full(n, np.nan); intra = np.zeros(n, np.bool_)
    for e in range(n):
        s = start[e]
        if s >= N: continue
        if lim[e] != lim[e]:                                   # market order
            fi[e] = s; fp[e] = O[s]; continue
        for j in range(s, min(end[e], N - 1) + 1):
            if d[e] == 1:
                if O[j] <= lim[e]:
                    fi[e] = j; fp[e] = O[j]; break
                if L[j] <= lim[e] - tick + 1e-9:
                    fi[e] = j; fp[e] = lim[e]; intra[e] = True; break
            else:
                if O[j] >= lim[e]:
                    fi[e] = j; fp[e] = O[j]; break
                if H[j] >= lim[e] + tick - 1e-9:
                    fi[e] = j; fp[e] = lim[e]; intra[e] = True; break
    return fi, fp, intra


@njit(cache=True)
def walk(O, H, L, C, i, e_px, dd, stop, tgt, be, trail, tbuf, intra, lo_px, lo_cnt, hi_px, hi_cnt, last, cost, slip,
         tick):
    """Walk one trade on 5 m bars from entry bar i. Returns (exit bar, points before cost)."""
    moved = False
    r = (e_px - stop) * dd
    c0 = lo_cnt[i] if dd == 1 else hi_cnt[i]
    for j in range(i, last + 1):
        first = intra and j == i
        if dd == 1:
            if j > i and O[j] <= stop: return j, O[j] - slip - e_px
            if L[j] <= stop: return j, stop - slip - e_px
            if not first:
                if tgt == tgt and H[j] >= tgt + tick - 1e-9: return j, tgt - e_px
                if be and (not moved) and H[j] >= e_px + r:
                    moved = True
                    if e_px + cost > stop: stop = e_px + cost
            if trail and j < last and lo_cnt[j + 1] > c0:
                nl = lo_px[j + 1] - tbuf
                if nl > stop: stop = nl
        else:
            if j > i and O[j] >= stop: return j, e_px - O[j] - slip
            if H[j] >= stop: return j, e_px - stop - slip
            if not first:
                if tgt == tgt and L[j] <= tgt - tick + 1e-9: return j, e_px - tgt
                if be and (not moved) and L[j] <= e_px - r:
                    moved = True
                    if e_px - cost < stop: stop = e_px - cost
            if trail and j < last and hi_cnt[j + 1] > c0:
                nh = hi_px[j + 1] + tbuf
                if nh < stop: stop = nh
    return last, (C[last] - e_px) * dd


TMULT = np.array([0.5, 1.0, 1.5, 2.0, 3.0, 5.0])
SBUF = np.array([0.1, 0.5, 1.0])


@njit(cache=True)
def stop_and_target(e_px, dd, lvl, a, smode, xmode, minstop):
    if smode <= 2:
        buf = SBUF[smode] * a
        stop = lvl - dd * buf
        tbuf = buf
    else:
        m = 1.5 if smode == 3 else 3.0
        stop = e_px - dd * m * a
        tbuf = 0.5 * a
    r = (e_px - stop) * dd
    if r > 0 and r < minstop:
        r = minstop
        stop = e_px - dd * r
    tgt = np.nan
    if xmode <= 5:
        tgt = e_px + dd * TMULT[xmode] * r
    elif xmode == 7:
        tgt = e_px + dd * 3.0 * r
    return stop, tgt, tbuf, r


@njit(cache=True)
def simulate(O, H, L, C, fi, fp, intra, islim, d, lvl, atr, lo_px, lo_cnt, hi_px, hi_cnt, maxhold, smode, xmode,
             cost, slip, tick, minstop):
    n, N = len(fi), len(O)
    xi = np.full(n, -1, np.int64); net = np.full(n, np.nan); R = np.full(n, np.nan); tb = np.full(n, np.nan)
    for e in range(n):
        i = fi[e]
        if i < 0 or atr[e] != atr[e]: continue
        dd = d[e]
        stop, tgt, tbuf, r = stop_and_target(fp[e], dd, lvl[e], atr[e], smode, xmode, minstop)
        if r <= 0:
            if islim[e]:                                       # resting limit filled beyond its stop: stopped at once
                xi[e] = i; net[e] = -slip - cost; R[e] = minstop; tb[e] = tbuf
            continue
        last = min(N - 1, i + maxhold - 1)
        x, res = walk(O, H, L, C, i, fp[e], dd, stop, tgt, xmode == 7, xmode == 6, tbuf, intra[e], lo_px, lo_cnt,
                      hi_px, hi_cnt, last, cost, slip, tick)
        xi[e] = x; net[e] = res - cost; R[e] = r; tb[e] = tbuf
    return xi, net, R, tb


@njit(cache=True)
def take(fi_sorted, xi_sorted):
    """One position at a time: keep a trade only if it fills after the previous kept trade has exited."""
    keep = np.zeros(len(fi_sorted), np.bool_)
    last = -1
    for k in range(len(fi_sorted)):
        if xi_sorted[k] >= 0 and fi_sorted[k] > last:
            keep[k] = True
            last = xi_sorted[k]
    return keep


@njit(cache=True)
def placebo(O, H, L, C, pool, pkey_lo, pkey_hi, d, R, tbuf, xmode, maxhold, lo_px, lo_cnt, hi_px, hi_cnt, cost, slip,
            tick, copies, seed, in_r):
    """For every real trade: `copies` re-entries at random pool bars with the same key (month + time slot), at market,
    same direction, same stop distance in points, same exit rule. Returns mean net points (in_r: net R) of each copy."""
    np.random.seed(seed)
    n, N = len(d), len(O)
    out = np.zeros(copies)
    for b in range(copies):
        s, m = 0.0, 0
        for e in range(n):
            a0, a1 = pkey_lo[e], pkey_hi[e]
            if a1 <= a0: continue
            i = pool[a0 + np.random.randint(0, a1 - a0)]
            e_px = O[i]
            dd = d[e]
            stop = e_px - dd * R[e]
            tgt = np.nan
            if xmode <= 5:
                tgt = e_px + dd * TMULT[xmode] * R[e]
            elif xmode == 7:
                tgt = e_px + dd * 3.0 * R[e]
            last = min(N - 1, i + maxhold - 1)
            x, res = walk(O, H, L, C, i, e_px, dd, stop, tgt, xmode == 7, xmode == 6, tbuf[e], False, lo_px, lo_cnt,
                          hi_px, hi_cnt, last, cost, slip, tick)
            s += (res - cost) / R[e] if in_r else res - cost
            m += 1
        out[b] = s / m if m > 0 else np.nan
    return out


# ------------------------------------------------------------------------------------------------- market wrapper
def wilder_atr(h, l, c, n=14):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy()


def asof_series(avail5, values, N):
    """Value known at each 5 m bar: the latest `values[k]` whose availability bar avail5[k] <= i. Also the count."""
    cnt = np.searchsorted(avail5, np.arange(N), side="right").astype(np.int64)
    px = np.full(N, np.nan)
    has = cnt > 0
    px[has] = values[cnt[has] - 1]
    return px, cnt


class Market:
    def __init__(self, name, ns, O, H, L, C, tick, cost, slip, minstop):
        self.name, self.tick, self.cost, self.slip, self.minstop = name, tick, cost, slip, minstop
        self.O, self.H, self.L, self.C = (np.ascontiguousarray(x, dtype=np.float64) for x in (O, H, L, C))
        self.N = len(self.C)
        idx = pd.DatetimeIndex(ns)
        self.idx = idx
        clock = (idx.hour * 60 + idx.minute).to_numpy()
        self.msess = ((clock - 18 * 60) % 1440).astype(np.int64)
        sd = (idx + pd.Timedelta(hours=6)).normalize()
        self.dayno = (sd.asi8 // DAY_NS).astype(np.int64)
        self.year = idx.year.to_numpy()
        self.month = (idx.year.to_numpy() * 12 + idx.month.to_numpy() - 1).astype(np.int64)
        self.cache = {}

    def bars(self, tf):
        """TF bars: o, h, l, c, atr, last 5 m index of each TF bar."""
        key = self.dayno * 1000 + (0 if tf == "1D" else self.msess // TF_MIN[tf])
        starts = np.r_[0, np.flatnonzero(key[1:] != key[:-1]) + 1]
        ends = np.r_[starts[1:] - 1, self.N - 1]
        o = self.O[starts]; h = np.maximum.reduceat(self.H, starts); l = np.minimum.reduceat(self.L, starts)
        c = self.C[ends]
        return o, h, l, c, wilder_atr(h, l, c), ends

    def prepare(self, tf):
        if tf in self.cache: return self.cache[tf]
        o, h, l, c, atr, ends = self.bars(tf)
        M = len(c)
        eb, ed, et, elim, elvl, swb, swp, sws, bias = structure(o, h, l, c, atr, K, MINFVG)
        # limit validity: 20 TF bars, cut at the next break the other way
        brk = np.isin(et, (0, 1))
        upb, dnb = np.sort(eb[brk & (ed == 1)]), np.sort(eb[brk & (ed == -1)])
        nxt = np.full(len(eb), M - 1, np.int64)
        for side, opp in ((1, dnb), (-1, upb)):
            m = ed == side
            k = np.searchsorted(opp, eb[m], side="right")
            nxt[m] = np.where(k < len(opp), opp[np.minimum(k, len(opp) - 1)], M - 1)
        vend = np.minimum(np.minimum(eb + VALID, nxt), M - 1)
        start = ends[eb] + 1
        end = ends[vend]
        fi, fp, intra = fills(self.O, self.H, self.L, start, end, ed, elim, self.tick)
        islim = ~np.isnan(elim)
        # swing series on the 5 m clock (a swing is usable from the 5 m bar after its confirming TF bar closed)
        lo, hi = sws == -1, sws == 1
        lo_px, lo_cnt = asof_series(ends[swb[lo]] + 1, swp[lo], self.N)
        hi_px, hi_cnt = asof_series(ends[swb[hi]] + 1, swp[hi], self.N)
        # bias of this TF on the 5 m clock
        bias5 = np.zeros(self.N, np.int64)
        kb = np.searchsorted(ends, np.arange(self.N), side="left") - 1
        bias5[kb >= 0] = bias[kb[kb >= 0]]
        # placebo pool: first 5 m bar of every TF bar, keyed by month and time slot
        pool = ends[:-1] + 1
        slot = self.msess[pool] // max(60, TF_MIN[tf])
        pkey = self.month[pool] * 100 + slot
        order = np.argsort(pkey, kind="stable")
        pool, pkey = pool[order], pkey[order]
        out = dict(tf=tf, M=M, eb=eb, ed=ed, et=et, elim=elim, elvl=elvl, atr=atr[eb], start=start, fi=fi, fp=fp,
                   intra=intra, islim=islim, lo_px=lo_px, lo_cnt=lo_cnt, hi_px=hi_px, hi_cnt=hi_cnt, bias5=bias5,
                   pool=pool, pkey=pkey, maxhold=MAXHOLD * TF_MIN[tf] // 5, ends=ends)
        self.cache[tf] = out
        return out

    def htf_ok(self, tf, P):
        """Event direction agrees with the higher timeframe's bias at the order start."""
        Q = self.prepare(HTF[tf])
        s = np.minimum(P["start"], self.N - 1)
        return Q["bias5"][s] == P["ed"]

    def run(self, P, smode, xmode, cost=None, slip=None):
        cost = self.cost if cost is None else cost
        slip = self.slip if slip is None else slip
        return simulate(self.O, self.H, self.L, self.C, P["fi"], P["fp"], P["intra"], P["islim"], P["ed"], P["elvl"],
                        P["atr"], P["lo_px"], P["lo_cnt"], P["hi_px"], P["hi_cnt"], P["maxhold"], smode, xmode, cost,
                        slip, self.tick, self.minstop)

    def trades(self, P, sim, mask):
        """Apply one-position-at-a-time to the events in `mask`. Returns event indices of kept trades (fill order)."""
        xi = sim[0]
        ev = np.flatnonzero(mask & (P["fi"] >= 0) & (xi >= 0))
        ev = ev[np.argsort(P["fi"][ev], kind="stable")]
        keep = take(P["fi"][ev], xi[ev])
        return ev[keep]

    def placebo_means(self, P, ev, sim, xmode, copies, seed, cost=None, slip=None, in_r=False):
        cost = self.cost if cost is None else cost
        slip = self.slip if slip is None else slip
        i = P["fi"][ev]
        key = self.month[i] * 100 + self.msess[i] // max(60, TF_MIN[P["tf"]])
        lo = np.searchsorted(P["pkey"], key, side="left")
        hi = np.searchsorted(P["pkey"], key, side="right")
        return placebo(self.O, self.H, self.L, self.C, P["pool"], lo, hi, P["ed"][ev], sim[2][ev], sim[3][ev], xmode,
                       P["maxhold"], P["lo_px"], P["lo_cnt"], P["hi_px"], P["hi_cnt"], cost, slip, self.tick, copies,
                       seed, in_r)


# ------------------------------------------------------------------------------------------------- loaders
def load_xau5m(path):
    a = np.fromfile(path).reshape(-1, 5)
    t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
    idx = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
    return idx.asi8, a[:, 1], a[:, 2], a[:, 3], a[:, 4]


def load_csv_et(path, start=None):
    df = pd.read_csv(path)
    tcol = df.columns[0]
    idx = pd.to_datetime(df[tcol])
    if start is not None:
        keep = idx >= pd.Timestamp(start)
        df, idx = df[keep.to_numpy()], idx[keep]
    df = df[(df.high >= df.low).to_numpy()]
    idx = pd.to_datetime(df[tcol])
    return pd.DatetimeIndex(idx).asi8, df.open.to_numpy(float), df.high.to_numpy(float), df.low.to_numpy(float), \
        df.close.to_numpy(float)
