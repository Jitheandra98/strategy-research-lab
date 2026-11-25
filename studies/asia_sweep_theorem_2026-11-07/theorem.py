"""The owner's theorem, made mechanical and tested (gold 5m 2012-2026, New York clock, Desk Context sessions):
  Asia = 18:00-00:00, London 02:00-05:00, NY window 08:00-11:00, trading day 18:00 -> 17:00.

V1  THEOREM  Asia low still intact at 08:00 -> NY sweeps it -> price touches a FRESH bullish OB/FVG sitting just below
             (zone top within 1.5 x ATR(1h) under the Asia low, made in the last 3 days, never touched) -> BUY at the zone top.
             Stop under the zone (0.1 x ATR5 buffer). Target = the other side (Asia high); also 2R / 3R. Exit 16:55 if open.
             SELL = mirror (Asia high swept into a fresh bearish zone just above, target Asia low).
V2a DESK ALERT  first NY bar that trades through the intact Asia low AND closes back above (Desk Context's own sweep alert)
             -> BUY at that close, stop under the sweep bar, target Asia high / 2R. Mirror for highs.
V2b SWEEP+RECLAIM  NY sweeps the Asia low, then any later NY bar closes back above it -> BUY at that close.
V3  PREVIOUS NY LEVELS  the NY-window high/low of each of the last 5 days, still intact: today's NY window trades through one
             and closes back inside -> fade it, stop beyond the bar, target 2R.
CONTROL   every trade replayed on 20 random other days at the same NY clock time, same direction, same stop and target distance.
Costs 0.3 pt per round trip ($3 on 1 MGC). Stop counted first inside a bar; entry-bar favourable move not counted."""
import numpy as np, pandas as pd
rng = np.random.default_rng(5)
a = np.fromfile("/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
O, H, L, C = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
N, COST = len(C), 0.3
ny = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York")
clock = (ny.hour * 60 + ny.minute).to_numpy()
tday = (ny.tz_localize(None) + pd.Timedelta(hours=6)).normalize().to_numpy()
yr = (ny.tz_localize(None) + pd.Timedelta(hours=6)).year.to_numpy()
prevC = np.r_[C[0], C[:-1]]
tr = np.maximum(H - L, np.maximum(np.abs(H - prevC), np.abs(L - prevC)))
atr5 = pd.Series(tr).rolling(14).mean().to_numpy()
# 1h ATR(14) known at each 5m bar (last completed hour)
hk = t // 3600
hs = np.r_[0, np.flatnonzero(np.diff(hk)) + 1]; he = np.r_[hs[1:], N]
hH = np.maximum.reduceat(H, hs); hL = np.minimum.reduceat(L, hs); hC = C[he - 1]
htr = np.maximum(hH - hL, np.maximum(np.abs(hH - np.r_[hC[0], hC[:-1]]), np.abs(hL - np.r_[hC[0], hC[:-1]])))
hatr = pd.Series(htr).rolling(14).mean().shift(1).to_numpy()          # previous completed hours only
atr1h = np.repeat(hatr, he - hs)

# ---- zones (5m), valid from the bar after creation
bz, sz = [], []
for j in range(5, N):
    if t[j] - t[j - 2] != 600 or np.isnan(atr5[j]): continue
    mn = 0.25 * atr5[j]
    if L[j] - H[j - 2] >= mn:
        bz.append((j, L[j], H[j - 2]))
        for k in range(j - 2, j - 6, -1):
            if C[k] < O[k]:
                if H[k] < L[j]: bz.append((j, H[k], L[k]))
                break
    if L[j - 2] - H[j] >= mn:
        sz.append((j, L[j - 2], H[j]))
        for k in range(j - 2, j - 6, -1):
            if C[k] > O[k]:
                if L[k] > H[j]: sz.append((j, H[k], L[k]))
                break
bz = np.array(bz); sz = np.array(sz)          # columns: created_idx, top, bottom

def walk(k0, d, px, stop, tgt, end):
    """Path from bar k0 (entry bar) to end (inclusive). Returns exit points P&L (before cost)."""
    if (d == 1 and L[k0] <= stop) or (d == -1 and H[k0] >= stop): return stop - px if d == 1 else px - stop
    for k in range(k0 + 1, end + 1):
        if d == 1:
            if L[k] <= stop: return stop - px
            if H[k] >= tgt: return tgt - px
        else:
            if H[k] >= stop: return px - stop
            if L[k] <= tgt: return px - tgt
    return d * (C[end] - px)

days, first = np.unique(tday, return_index=True)
bounds = np.r_[first, N]
trades = []
ny_lows, ny_highs = [], []        # (level, day_no) of previous NY windows, for V3
for di in range(len(days)):
    i0, i1 = bounds[di], bounds[di + 1]
    ck = clock[i0:i1]
    asia = np.flatnonzero(ck >= 18 * 60) + i0
    pre = np.flatnonzero(ck < 8 * 60) + i0
    nyw = np.flatnonzero((ck >= 8 * 60) & (ck < 11 * 60)) + i0
    endi = np.flatnonzero(ck < 17 * 60)
    if len(asia) < 50 or len(nyw) < 30 or len(endi) == 0: continue
    end = endi[-1] + i0
    AH, AL = H[asia].max(), L[asia].min()
    y = yr[i0]
    for d in (1, -1):
        # Asia level intact before the NY window?
        if d == 1 and len(pre) and L[pre].min() < AL: continue
        if d == -1 and len(pre) and H[pre].max() > AH: continue
        lvl = AL if d == 1 else AH
        sw = nyw[(L[nyw] < AL) if d == 1 else (H[nyw] > AH)]
        if len(sw) == 0: continue
        s = sw[0]
        other = AH if d == 1 else AL
        # ---- V2a: same-bar close back inside (Desk Context alert)
        if (d == 1 and C[s] > AL) or (d == -1 and C[s] < AH):
            px = C[s]; stop = (L[s] if d == 1 else H[s]) - d * 0.1 * atr5[s]; R = abs(px - stop)
            if R > 0:
                for tn, tg in (("other side", other), ("2R", px + d * 2 * R)):
                    if (tg - px) * d > 0:
                        trades.append(dict(v="V2a desk sweep alert", d=d, y=y, k=s, px=px, R=R, tgt_dist=abs(tg - px), tn=tn, pts=walk(s + 1, d, px, stop, tg, end) if s + 1 <= end else 0.0))
        # ---- V2b: any later NY close back inside
        after = nyw[nyw >= s]
        back = after[(C[after] > AL) if d == 1 else (C[after] < AH)]
        if len(back):
            b = back[0]; ext = L[s:b + 1].min() if d == 1 else H[s:b + 1].max()
            px = C[b]; stop = ext - d * 0.1 * atr5[b]; R = abs(px - stop)
            if R > 0 and b + 1 <= end:
                for tn, tg in (("other side", other), ("2R", px + d * 2 * R)):
                    if (tg - px) * d > 0:
                        trades.append(dict(v="V2b sweep then reclaim", d=d, y=y, k=b, px=px, R=R, tgt_dist=abs(tg - px), tn=tn, pts=walk(b + 1, d, px, stop, tg, end)))
        # ---- V1: the theorem
        D = 1.5 * atr1h[s]
        if np.isnan(D): continue
        Z = bz if d == 1 else sz
        lo_c = np.searchsorted(Z[:, 0], np.searchsorted(t, t[i0] - 3 * 86400))
        hi_c = np.searchsorted(Z[:, 0], s)                 # created before the sweep bar
        cand = Z[lo_c:hi_c]
        if d == 1: cand = cand[(cand[:, 1] < AL) & (cand[:, 1] >= AL - D)]; order = np.argsort(-cand[:, 1])
        else:      cand = cand[(cand[:, 2] > AH) & (cand[:, 2] <= AH + D)]; order = np.argsort(cand[:, 2])
        zone = None
        for zi in order:
            c, top, bot = int(cand[zi, 0]), cand[zi, 1], cand[zi, 2]
            seg = slice(c + 1, s)
            fresh = (L[seg].min() > top) if d == 1 else (H[seg].max() < bot)
            if c + 1 >= s or fresh: zone = (top, bot); break
        if zone is None: continue
        top, bot = zone
        edge = top if d == 1 else bot
        tch = nyw[nyw >= s]
        tch = tch[(L[tch] <= edge) if d == 1 else (H[tch] >= edge)]
        if len(tch) == 0: continue
        k = tch[0]
        px = min(edge, O[k]) if d == 1 else max(edge, O[k])
        stop = (bot - 0.1 * atr5[k]) if d == 1 else (top + 0.1 * atr5[k])
        R = (px - stop) * d
        if R <= 0: continue
        for tn, tg in (("other side", other), ("2R", px + d * 2 * R), ("3R", px + d * 3 * R)):
            if (tg - px) * d > 0:
                trades.append(dict(v="V1 THEOREM", d=d, y=y, k=k, px=px, R=R, tgt_dist=abs(tg - px), tn=tn, pts=walk(k, d, px, stop, tg, end)))
    # ---- V3: previous NY window levels (last 5 days), still intact
    nyH, nyL = H[nyw].max(), L[nyw].min()
    for d, levels in ((1, ny_lows), (-1, ny_highs)):
        live = [lv for lv, dn in levels if di - dn <= 5]
        if not live: continue
        for b in nyw:
            hit = [lv for lv in live if (L[b] < lv if d == 1 else H[b] > lv)]
            if hit:
                lv = max(hit) if d == 1 else min(hit)
                if (d == 1 and C[b] > lv) or (d == -1 and C[b] < lv):
                    px = C[b]; stop = (L[b] if d == 1 else H[b]) - d * 0.1 * atr5[b]; R = abs(px - stop)
                    if R > 0 and b + 1 <= end:
                        tg = px + d * 2 * R
                        trades.append(dict(v="V3 prev NY level sweep", d=d, y=y, k=b, px=px, R=R, tgt_dist=2 * R, tn="2R", pts=walk(b + 1, d, px, stop, tg, end)))
                break
    # remember today's NY levels; drop levels traded through today (no longer intact)
    ny_lows[:] = [(lv, dn) for lv, dn in ny_lows if L[i0:i1].min() >= lv] + [(nyL, di)]
    ny_highs[:] = [(lv, dn) for lv, dn in ny_highs if H[i0:i1].max() <= lv] + [(nyH, di)]

T = pd.DataFrame(trades)
T["r"] = (T.pts - COST) / T.R
T["usd"] = (T.pts - COST) * 10
# ---- control: same clock time, random other days, same bracket
dayidx = np.searchsorted(bounds, np.arange(N), side="right") - 1
by_clock = pd.Series(np.arange(N)).groupby(clock).apply(np.array).to_dict()
ends = {}
def day_end(i):
    di = dayidx[i]
    if di not in ends:
        ck = clock[bounds[di]:bounds[di + 1]]; e = np.flatnonzero(ck < 17 * 60)
        ends[di] = bounds[di] + e[-1] if len(e) else -1
    return ends[di]
ctrl = []
for row in T.itertuples():
    pool = by_clock[clock[row.k]]; rs = []
    for r in pool[rng.integers(0, len(pool), 40)]:
        if dayidx[r] == dayidx[row.k]: continue
        e = day_end(r)
        if e <= r: continue
        px = C[r]; stop = px - row.d * row.R; tg = px + row.d * row.tgt_dist
        rs.append((walk(r + 1, row.d, px, stop, tg, e) - COST) / row.R)
        if len(rs) == 20: break
    ctrl.append(np.mean(rs) if rs else np.nan)
T["ctrl_r"] = ctrl
T.to_csv("trades.csv", index=False)

def summ(g):
    r = g.r; w = r[r > 0].sum(); l = -r[r < 0].sum()
    return pd.Series(dict(trades=len(g), per_year=len(g) / g.y.nunique(), win=(r > 0).mean() * 100, avg_R=r.mean(), PF=w / l if l else np.nan,
                          random_same_bracket_R=g.ctrl_r.mean(), edge_vs_random=r.mean() - g.ctrl_r.mean(), avg_usd_1MGC=g.usd.mean()))
T["period"] = np.where(T.y <= 2019, "2012-2019", "2020-2026")
pd.set_option("display.width", 250); pd.set_option("display.float_format", lambda v: f"{v:.2f}"); pd.set_option("display.max_rows", 200)
print(T.groupby(["v", "tn", "period"]).apply(summ, include_groups=False).to_string())
print("\nV1 by side (target = other side):")
print(T[(T.v == "V1 THEOREM") & (T.tn == "other side")].groupby(["d", "period"]).apply(summ, include_groups=False).to_string())
