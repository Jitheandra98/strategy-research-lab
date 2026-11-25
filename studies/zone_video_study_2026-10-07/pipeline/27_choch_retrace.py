"""Stage 27: owner's market-structure thesis — 4H CHoCH -> price retraces into the area -> 15m CHoCH again -> continue.
Rules frozen in PREREGISTRATION.md (addendum 2026-10-25) before this script was run.
usage: 27_choch_retrace.py <minute_pickle> <out_dir>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

M1, OUT = sys.argv[1], Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
HTF = int(sys.argv[3]) if len(sys.argv) > 3 else 240; LTF = int(sys.argv[4]) if len(sys.argv) > 4 else 15
RAT = HTF // LTF
P, BUF, COST, WAIT4, CONF15, TMAX = 3, 0.10, 0.30, 60, 18 * RAT, 30 * RAT
m1 = pd.read_pickle(M1)[["open", "high", "low", "close"]]
agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
b = m1.resample(f"{LTF}min").agg(agg).dropna()
ny = b.index.tz_convert("America/New_York")
anchor = (ny - pd.Timedelta(hours=17)).normalize() + pd.Timedelta(hours=17)
b["k4"] = b.index.floor(f"{HTF}min") if HTF != 240 else (anchor + ((ny - anchor) // pd.Timedelta(hours=4)) * pd.Timedelta(hours=4)).tz_convert("UTC")
h4 = b.groupby("k4").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
                         last15=("open", lambda s: s.index[-1]))
h4["avail"] = h4.last15 + pd.Timedelta(minutes=LTF)
print("15m", len(b), "4H", len(h4), b.index[0], b.index[-1], flush=True)


def rma_atr(H, L, C, n=14):
    tr = np.maximum(H - L, np.maximum(np.abs(H - np.r_[np.nan, C[:-1]]), np.abs(L - np.r_[np.nan, C[:-1]])))
    tr[0] = H[0] - L[0]
    out = np.full(len(tr), np.nan); s = tr[:n].mean(); out[n - 1] = s
    for i in range(n, len(tr)): s = (s * (n - 1) + tr[i]) / n; out[i] = s
    return out


def structure(H, L, C):
    """returns events: list of (bar, dir, kind, broken_swing_bar, level) and the bar of the last confirmed swing high/low"""
    n = len(C); ev = []; sh = None; sl = None; trend = 0
    lastSHbar = np.full(n, -1); lastSLbar = np.full(n, -1)
    for i in range(n):
        j = i - P
        if j >= P:
            if H[j] > H[j - P:j].max() and H[j] > H[j + 1:i + 1].max(): sh = [H[j], j, False]
            if L[j] < L[j - P:j].min() and L[j] < L[j + 1:i + 1].min(): sl = [L[j], j, False]
        if sh is not None and not sh[2] and C[i] > sh[0]:
            ev.append((i, 1, "CHoCH" if trend == -1 else "BOS", sh[1], sh[0])); trend = 1; sh[2] = True
        if sl is not None and not sl[2] and C[i] < sl[0]:
            ev.append((i, -1, "CHoCH" if trend == 1 else "BOS", sl[1], sl[0])); trend = -1; sl[2] = True
        lastSHbar[i] = sh[1] if sh else -1; lastSLbar[i] = sl[1] if sl else -1
    return ev, lastSHbar, lastSLbar


O4, H4, L4, C4 = (h4[k].to_numpy() for k in ["open", "high", "low", "close"])
A4 = rma_atr(H4, L4, C4)
ev4, _, _ = structure(H4, L4, C4)
T = b.index; H, L, C = (b[k].to_numpy() for k in ["high", "low", "close"]); n = len(T)
ev15, sh15, sl15 = structure(H, L, C)
E15 = pd.DataFrame(ev15, columns=["bar", "dir", "kind", "sbar", "lvl"])
print("4H events", len(ev4), "15m events", len(E15), flush=True)
pos_av = np.searchsorted(T.values, h4.avail.dt.tz_convert(None).values.astype(T.values.dtype)) if h4.avail.dt.tz is not None else np.searchsorted(T.tz_convert(None).values, h4.avail.values)   # first 15m bar at/after 4H close
a4_15 = pd.merge_asof(pd.DataFrame({"t": T}), pd.DataFrame({"t": h4.avail.reset_index(drop=True), "a": A4}).sort_values("t"),
                      on="t", direction="backward").a.to_numpy()


def exits(d, e, entry, stop, tgts):
    risk = d * (entry - stop); out = {}
    seg = slice(e + 1, min(n, e + 1 + TMAX))
    hs = (H[seg] >= stop) if d == -1 else (L[seg] <= stop); m = len(hs)
    fs = np.argmax(hs) if hs.any() else m
    for name, tg in tgts.items():
        if tg is None or np.isnan(tg) or d * (tg - entry) <= 0: out[name] = np.nan; continue
        ht = (L[seg] <= tg) if d == -1 else (H[seg] >= tg)
        ft = np.argmax(ht) if ht.any() else m
        if fs == m and ft == m: R = d * (C[seg][-1] - entry) / risk if m else 0.0
        elif fs <= ft: R = -1.0
        else: R = d * (tg - entry) / risk
        out[name] = R - COST / risk
    return out


ev4_dir = np.array([x[1] for x in ev4]); ev4_kind = np.array([x[2] for x in ev4]); ev4_bar = np.array([x[0] for x in ev4])
rows = []
for (i, d, kind, sb, lvl) in ev4:
    if kind != "CHoCH" or np.isnan(A4[i]) or i + 1 >= len(h4): continue
    seg = slice(sb + 1, i + 1) if sb + 1 <= i else slice(sb, i + 1)
    if d == -1:
        tb = seg.start + int(np.argmax(H4[seg])); legx = H4[tb]; legn = L4[tb:i + 1].min()
    else:
        tb = seg.start + int(np.argmin(L4[seg])); legx = L4[tb]; legn = H4[tb:i + 1].max()
    ob = tb
    for k in range(tb, max(-1, tb - 11), -1):
        if (d == -1 and C4[k] > O4[k]) or (d == 1 and C4[k] < O4[k]): ob = k; break
    areas = {"OB": (L4[ob], H4[ob]),
             "PREM": ((legn + 0.5 * (legx - legn), legx) if d == -1 else (legx, legn - 0.5 * (legn - legx)))}
    q0 = pos_av[i]
    if q0 >= n - 10: continue
    # next opposite 4H CHoCH (cancels the setup once its 4H candle has closed)
    opp = np.where((ev4_bar > i) & (ev4_dir == -d) & (ev4_kind == "CHoCH"))[0]
    q_opp = pos_av[ev4_bar[opp[0]]] if len(opp) else n
    qend = min(n - 1, q0 + WAIT4 * RAT, q_opp)
    brk = np.where((C[q0:qend] > legx) if d == -1 else (C[q0:qend] < legx))[0]
    q_brk = q0 + brk[0] if len(brk) else n
    for aname, (alo, ahi) in areas.items():
        edge = alo if d == -1 else ahi
        hit = np.where((H[q0:qend] >= edge) if d == -1 else (L[q0:qend] <= edge))[0]
        if not len(hit): continue
        qt = q0 + hit[0]
        if qt >= q_brk: continue
        for ename, need in (("CHoCH", True), ("anybreak", False)):
            cand = E15[(E15.bar >= qt) & (E15.bar <= qt + CONF15) & (E15.dir == d) & ((E15.kind == "CHoCH") | (not need))]
            if not len(cand): continue
            e = int(cand.bar.iloc[0])
            if e >= q_brk or e >= q_opp: continue
            entry = C[e]
            ext = H[qt:e + 1].max() if d == -1 else L[qt:e + 1].min()
            for sname, stop in (("A", ext - d * BUF * A4[i]), ("B", legx - d * BUF * A4[i])):
                if d * (entry - stop) <= 0: continue
                risk = d * (entry - stop)
                r = exits(d, e, entry, stop, {"2R": entry + d * 2 * risk, "3R": entry + d * 3 * risk, "leg": legn if d == -1 else legn})
                lowlegtgt = legn if d == -1 else legn
                rows.append(dict(time=T[e], dir=d, area=aname, entry_rule=ename, stop_rule=sname, entry=entry, stop=stop,
                                 risk=risk, a4=A4[i], choch4_time=h4.index[i], touch_time=T[qt],
                                 **{f"R_{k}": v for k, v in r.items()}))
S = pd.DataFrame(rows)
# leg target: for SELL the leg low (legn = lowest low of the CHoCH move); for BUY the leg high
S.to_pickle(OUT / "choch_setups.pkl")

# control: every 15m CHoCH, stop above the last confirmed 15m swing high (sell) / below swing low (buy)
crow = []
for r in E15[E15.kind == "CHoCH"].itertuples():
    e, d = r.bar, r.dir
    if e + 2 >= n or np.isnan(a4_15[e]): continue
    sb = sh15[e] if d == -1 else sl15[e]
    if sb < 0: continue
    ext = H[sb:e + 1].max() if d == -1 else L[sb:e + 1].min()
    stop = ext - d * BUF * a4_15[e]; entry = C[e]; risk = d * (entry - stop)
    if risk <= 0: continue
    rr = exits(d, e, entry, stop, {"2R": entry + d * 2 * risk, "3R": entry + d * 3 * risk})
    crow.append(dict(time=T[e], dir=d, risk=risk, **{f"R_{k}": v for k, v in rr.items()}))
Cn = pd.DataFrame(crow); Cn.to_pickle(OUT / "control_15m_choch.pkl")


def per(t):
    return np.where(t < pd.Timestamp("2021-01-01", tz="UTC"), "1 EXT 2016-20",
                    np.where(t < pd.Timestamp("2026-04-01", tz="UTC"), "2 IS 2021-26/03", "3 FWD 2026-04→10"))


S["period"] = per(S.time); Cn["period"] = per(Cn.time)


def summ(x):
    x = x.dropna()
    return pd.Series(dict(n=len(x), meanR=x.mean(), ci95=1.96 * x.std() / np.sqrt(max(1, len(x))), win=(x > 0).mean()))


res = []
for (pr, ar, er, sr), g in S.groupby(["period", "area", "entry_rule", "stop_rule"]):
    for tg in ("2R", "3R", "leg"):
        res.append(dict(period=pr, area=ar, entry=er, stop=sr, target=tg, **summ(g[f"R_{tg}"])))
for pr, g in Cn.groupby("period"):
    for tg in ("2R", "3R"):
        res.append(dict(period=pr, area="CONTROL any 15m CHoCH", entry="CHoCH", stop="A", target=tg, **summ(g[f"R_{tg}"])))
Rs = pd.DataFrame(res).sort_values(["area", "entry", "stop", "target", "period"])
Rs.to_csv(OUT / "choch_summary.csv", index=False)
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
print(Rs.round(3).to_string(index=False))
print("median risk pts A:", S[S.stop_rule == "A"].risk.median(), " control:", Cn.risk.median())
