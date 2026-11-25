"""Stage 28: owner's new strategy (2026-10-26) — an inverse FVG formed in the Tokyo session; New York (08-16 NY) goes to
it, structure changes there and price moves in the IFVG's direction. Rules frozen in PREREGISTRATION.md (2026-10-26).
H-A magnet: does NY touch the Tokyo IFVG more often than a mirror box (same size, same distance, other side)?
H-B trade: first NY touch -> first 3m CHoCH in the IFVG direction -> enter; stop = extreme since touch + 0.1 ATR15;
2R / 3R, flat at 16:00, cost 0.30. H-B0: limit at the near edge, stop beyond the far edge + 0.1 ATR15.
usage: 28_tokyo_ifvg.py <minute_pickle> <out_dir>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

M1, OUT = sys.argv[1], Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
COST, BUF, MINSZ, KEEP = 0.30, 0.10, 0.25, 192
m1 = pd.read_pickle(M1)[["open", "high", "low", "close"]]
agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
b = m1.resample("15min").agg(agg).dropna(); m3 = m1.resample("3min").agg(agg).dropna()
T = b.index; O, H, L, C = (b[k].to_numpy() for k in ["open", "high", "low", "close"]); n = len(T)
T3 = m3.index; O3, H3, L3, C3 = (m3[k].to_numpy() for k in ["open", "high", "low", "close"]); n3 = len(T3)
ny = T.tz_convert("America/New_York"); ny3 = T3.tz_convert("America/New_York")
print("15m", n, "3m", n3, T[0], T[-1], flush=True)


def rma_atr(H, L, C, k=14):
    pc = np.r_[np.nan, C[:-1]]
    tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
    out = np.full(len(tr), np.nan); s = tr[:k].mean(); out[k - 1] = s
    for i in range(k, len(tr)): s = (s * (k - 1) + tr[i]) / k; out[i] = s
    return out


A15 = rma_atr(H, L, C)

# ── FVGs and their inversions ──
ifvg = []
for i in range(2, n - 1):
    a = A15[i]
    if np.isnan(a): continue
    for d, top, bot in ((1, L[i], H[i - 2]), (-1, L[i - 2], H[i])):
        if top - bot < MINSZ * a: continue
        seg = C[i + 1:i + 1 + KEEP]
        inv = np.where(seg < bot)[0] if d == 1 else np.where(seg > top)[0]
        if not len(inv): continue
        k = i + 1 + inv[0]
        h = ny[k].hour
        if not (h >= 19 or h < 4): continue
        sday = (ny[k] + pd.Timedelta(hours=5)).date()
        if pd.Timestamp(sday).weekday() >= 5: continue
        # after inversion the box points the other way: old bull FVG -> bearish IFVG (resistance)
        ifvg.append(dict(born=i, inv_bar=k, dir=-d, top=top, bot=bot, sday=sday))
F = pd.DataFrame(ifvg)
print("Tokyo IFVGs", len(F), flush=True)

# 3m structure (pivots 3/3, close beyond the last confirmed swing; CHoCH = against the current trend)
P = 3; ev = []; sh = sl = None; trend = 0
for i in range(n3):
    j = i - P
    if j >= P:
        if H3[j] > H3[j - P:j].max() and H3[j] > H3[j + 1:i + 1].max(): sh = [H3[j], False]
        if L3[j] < L3[j - P:j].min() and L3[j] < L3[j + 1:i + 1].min(): sl = [L3[j], False]
    if sh is not None and not sh[1] and C3[i] > sh[0]:
        if trend == -1: ev.append((i, 1))
        trend = 1; sh[1] = True
    if sl is not None and not sl[1] and C3[i] < sl[0]:
        if trend == 1: ev.append((i, -1))
        trend = -1; sl[1] = True
EV = np.array(ev); EVb, EVd = EV[:, 0], EV[:, 1]
print("3m CHoCH", len(EV), flush=True)

t3v = T3.values
day3 = np.array([d.date() for d in ny3])
nyh3 = ny3.hour


def session(sday):
    s = pd.Timestamp(sday).tz_localize("America/New_York") + pd.Timedelta(hours=8)
    e = s + pd.Timedelta(hours=8)
    q0 = np.searchsorted(t3v, s.tz_convert("UTC").tz_localize(None).to_datetime64())
    q1 = np.searchsorted(t3v, e.tz_convert("UTC").tz_localize(None).to_datetime64())
    return q0, q1


def sim(d, entry, stop, a, b_, tgts):
    risk = d * (entry - stop); out = {}
    if risk <= 0 or a >= b_: return None
    hs = (L3[a:b_] <= stop) if d == 1 else (H3[a:b_] >= stop); m = b_ - a
    fs = np.argmax(hs) if hs.any() else m
    for nm, k in tgts.items():
        tg = entry + d * k * risk
        ht = (H3[a:b_] >= tg) if d == 1 else (L3[a:b_] <= tg)
        ft = np.argmax(ht) if ht.any() else m
        if fs == m and ft == m: R = d * (C3[b_ - 1] - entry) / risk
        elif fs <= ft: R = -1.0
        else: R = float(k)
        out[nm] = R - COST / risk
    return out


rows = []
sess_cache = {}
for r in F.itertuples():
    if r.sday not in sess_cache: sess_cache[r.sday] = session(r.sday)
    q0, q1 = sess_cache[r.sday]
    if q1 - q0 < 100 or q1 >= n3: continue
    # killed before NY? a 15m close back beyond the IFVG's other side between inversion and 08:00
    k08 = np.searchsorted(T.values, t3v[q0].astype(T.values.dtype)) if False else np.searchsorted(T.tz_convert(None).values, T3.tz_convert(None).values[q0])
    seg = C[r.inv_bar + 1:k08]
    killed = (seg > r.top).any() if r.dir == -1 else (seg < r.bot).any()
    if killed: continue
    p0 = O3[q0]; a = A15[k08 - 1]; size = r.top - r.bot
    if r.dir == -1 and p0 < r.bot: dist = r.bot - p0
    elif r.dir == 1 and p0 > r.top: dist = p0 - r.top
    else: continue                       # price already inside / on the wrong side at 08:00
    mir = (p0 - dist, p0 - dist - size) if r.dir == -1 else (p0 + dist + size, p0 + dist)   # (top, bot)
    for kind, d, top, bot in (("real", r.dir, r.top, r.bot), ("mirror", -r.dir, mir[0], mir[1])):
        edge = bot if d == -1 else top
        far = top if d == -1 else bot
        hit = np.where((H3[q0:q1] >= edge) if d == -1 else (L3[q0:q1] <= edge))[0]
        rec = dict(sday=r.sday, kind=kind, dir=d, dist=dist, dist_atr=dist / a, size_atr=size / a, touched=len(hit) > 0)
        if len(hit):
            qt = q0 + hit[0]; rec["touch_min"] = (qt - q0) * 3
            # H-B0 limit at the near edge
            st0 = far + d * -1 * BUF * a if False else (far + BUF * a if d == -1 else far - BUF * a)
            r0 = sim(d, edge, st0, qt, q1, {"2R": 2, "3R": 3})
            if r0: rec.update({f"B0_{k}": v for k, v in r0.items()}); rec["B0_risk"] = abs(edge - st0)
            # H-B first 3m CHoCH in direction d after the touch
            idx = np.where((EVb >= qt) & (EVb < q1 - 1) & (EVd == d))[0]
            if len(idx):
                e = EVb[idx[0]]; entry = C3[e]
                ext = H3[qt:e + 1].max() if d == -1 else L3[qt:e + 1].min()
                stop = ext + BUF * a if d == -1 else ext - BUF * a
                rb = sim(d, entry, stop, e + 1, q1, {"2R": 2, "3R": 3})
                if rb: rec.update({f"B_{k}": v for k, v in rb.items()}); rec["B_risk"] = abs(entry - stop); rec["B_time"] = T3[e]; rec["B_qt"] = qt
        rows.append(rec)
R = pd.DataFrame(rows)
R["period"] = np.where(pd.to_datetime(R.sday) < "2021-01-01", "1 EXT 2016-20",
                       np.where(pd.to_datetime(R.sday) < "2026-04-01", "2 IS 2021-26/03", "3 FWD 2026-04→10"))
R.to_pickle(OUT / "tokyo_ifvg_rows.pkl")
pd.set_option("display.width", 220)


def ci(x):
    x = pd.Series(x).dropna(); return pd.Series(dict(n=len(x), mean=x.mean(), ci95=1.96 * x.std() / np.sqrt(max(1, len(x)))))


print("\nH-A magnet: share touched in NY 08-16 (all qualifying IFVGs)")
print(R.groupby(["period", "kind"]).touched.apply(lambda s: f"{s.mean():.3f} (n {len(s)})").unstack())
print("median distance (×ATR15)", R[R.kind == "real"].dist_atr.median())
# one trade per day per direction: the box touched first
T_ = R[R.touched].sort_values("touch_min").groupby(["sday", "kind", "dir"]).head(1)
out = []
for (pr, kd), g in T_.groupby(["period", "kind"]):
    for c in ("B_2R", "B_3R", "B0_2R", "B0_3R"):
        out.append(dict(period=pr, boxes=kd, rule=c, **ci(g[c])))
S = pd.DataFrame(out).pivot_table(index=["rule", "period"], columns="boxes", values=["n", "mean", "ci95"]).round(3)
print("\nH-B trades (one per day per direction):"); print(S.to_string())
S.to_csv(OUT / "tokyo_ifvg_summary.csv")
print("median risk B", T_[T_.kind == "real"].B_risk.median(), " B0", T_[T_.kind == "real"].B0_risk.median())
