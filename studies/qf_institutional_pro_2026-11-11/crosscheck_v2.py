"""Independent re-implementation of the QF PRO v2 grading engine + gate, run on the same bars.
Inputs: PineTS output (raw setup flags, scores, sessions, newDay, htf) + raw OHLC.
Checks: ATR, ADX order, VWAP, PDH/PDL, signals after the gate, every graded trade, every dashboard stat."""
import json, sys, math, numpy as np, datetime as dt

OUT = sys.argv[1] if len(sys.argv) > 1 else "v2_full.json"
J = json.load(open(OUT)); vt = J["vtitles"]
T = np.fromfile(OUT + ".times.f64", dtype=np.float64)
V = np.fromfile(OUT + ".vals.f32", dtype=np.float32).reshape(len(T), len(vt)).astype(np.float64)
g = lambda k: V[:, vt.index(k)]
B = np.fromfile("gc5m7_ct.f64", dtype=np.float64).reshape(-1, 7)
idx = {t: i for i, t in enumerate(B[:, 0])}
pos = np.array([idx[t] for t in T]); assert (np.diff(pos) == 1).all(), "bars must be contiguous"
O, H, L, C, VOL, SK = (B[pos, j] for j in (1, 2, 3, 4, 5, 6))
N = len(T)
ok_all = True
def report(name, good, detail=""):
    global ok_all
    ok_all &= bool(good)
    print(f"[{'PASS' if good else 'FAIL'}] {name} {detail}")

# ---------- settings (script defaults) ----------
STOP_ATR, TGT_ATR, MAX_BARS = 2.0, 1.0, 20
TICK, PV = 0.1, 10.0
COST, SLIP = 3 * TICK, 2 * TICK
ACCT, RISK_PCT, DAY_STOP_R = 10000.0, 1.0, 2.0

# ---------- ATR (Wilder, like ta.atr) ----------
prevC = np.r_[np.nan, C[:-1]]
tr = np.where(np.isnan(prevC), H - L, np.maximum(H - L, np.maximum(abs(H - prevC), abs(L - prevC))))
atr = np.full(N, np.nan); atr[13] = tr[:14].mean()
for i in range(14, N): atr[i] = (atr[i-1] * 13 + tr[i]) / 14
m = np.isfinite(g("v_atr")) & np.isfinite(atr)
report("ATR(14) matches", np.allclose(atr[m], g("v_atr")[m], rtol=1e-5, atol=1e-4), f"(max diff {np.max(abs(atr[m]-g('v_atr')[m])):.2e})")

# ---------- DMI: confirm ADX is really ADX (v1 had them swapped) ----------
up = H - np.r_[np.nan, H[:-1]]; dn = np.r_[np.nan, L[:-1]] - L
pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
def rma(x, n):
    out = np.full(len(x), np.nan); s = 0.0; cnt = 0
    for i, v in enumerate(x):
        if np.isnan(v): continue
        if cnt < n:
            s += v; cnt += 1
            if cnt == n: out[i] = s / n
        else: out[i] = (out[i-1] * (n - 1) + v) / n
    return out
trr = rma(np.where(np.isnan(prevC), np.nan, tr), 14)
dip = 100 * rma(np.where(np.isnan(up), np.nan, pdm), 14) / trr
dim = 100 * rma(np.where(np.isnan(dn), np.nan, mdm), 14) / trr
dx = 100 * abs(dip - dim) / np.where(dip + dim == 0, 1, dip + dim)
adx = rma(dx, 14)
m = np.isfinite(adx) & np.isfinite(g("v_adx")); m[:200] = False
report("ADX is ADX and +DI is +DI", np.allclose(adx[m], g("v_adx")[m], atol=0.05) and np.allclose(dip[m], g("v_diPlus")[m], atol=0.05),
       f"(max diff ADX {np.max(abs(adx[m]-g('v_adx')[m])):.3f}, +DI {np.max(abs(dip[m]-g('v_diPlus')[m])):.3f})")

# ---------- PDH / PDL = previous CME session's high / low ----------
keysA, invA = np.unique(B[:, 6], return_inverse=True)            # sessions over the FULL data, not just the window
sh = np.full(len(keysA), -np.inf); sl = np.full(len(keysA), np.inf)
np.maximum.at(sh, invA, B[:, 2]); np.minimum.at(sl, invA, B[:, 3])
inv = invA[pos]
m = np.isfinite(g("v_pdh")) & (inv >= 1)
report("PDH/PDL = yesterday's session high/low", np.allclose(g("v_pdh")[m], sh[inv[m]-1], atol=0.06) and np.allclose(g("v_pdl")[m], sl[inv[m]-1], atol=0.06),
       f"({100*np.mean(np.isclose(g('v_pdh')[m], sh[inv[m]-1], atol=0.06)):.2f}% / {100*np.mean(np.isclose(g('v_pdl')[m], sl[inv[m]-1], atol=0.06)):.2f}% of {m.sum()} bars)")

# ---------- session VWAP (hlc3, resets at the 17:00 CT reopen) ----------
nd = g("v_newDay") == 1
hlc3 = (H + L + C) / 3
vw = np.full(N, np.nan); sd = np.full(N, np.nan); sV = sPV = sPV2 = 0.0
for i in range(N):
    if nd[i]: sV = sPV = sPV2 = 0.0
    sV += VOL[i]; sPV += hlc3[i] * VOL[i]; sPV2 += hlc3[i] ** 2 * VOL[i]
    vw[i] = sPV / sV if sV > 0 else hlc3[i]; sd[i] = math.sqrt(max(sPV2 / sV - vw[i] ** 2, 0)) if sV > 0 else 0
report("VWAP and σ match", np.allclose(vw, g("v_vwap"), atol=0.02) and np.allclose(sd, g("v_vsd"), atol=0.05),
       f"(max diff {np.max(abs(vw-g('v_vwap'))):.4f} / {np.max(abs(sd-g('v_vsd'))):.4f})")
first_bar_of_session = np.r_[False, SK[1:] != SK[:-1]]
newday_ct = sorted(set(dt.datetime.utcfromtimestamp(T[i]/1000).strftime('%H:%M') for i in np.where(nd)[0]))
report("day starts on the first bar after the 17:00 CT reopen", (nd[1:] == first_bar_of_session[1:]).all(), str(newday_ct))

# ---------- gate + engine, written from the spec ----------
class Grader:
    def __init__(s):
        s.dir = 0; s.entry = s.stop = s.target = s.risk = float("nan"); s.bars = 0; s.kind = 1; s.ses = 0; s.qty = 0
        s.pDir = 0; s.pWait = 0; s.pKind = 1; s.pSes = 0; s.opened = s.closed = False
        s.n = s.wins = 0; s.sumR = s.sumR2 = s.winR = s.lossR = s.netPts = s.eqR = s.peakR = s.ddR = 0.0
        s.streak = s.worst = 0; s.dayR = 0.0; s.cash = s.cashPeak = ACCT; s.cashDD = 0.0; s.tooWide = 0
        s.nStop = s.nTgt = s.nTime = s.nDay = 0; s.trades = []; s.ebar = None
    def exit_at(s, px, reason, i):
        net = (px - s.entry) * s.dir - COST - (SLIP if reason == 1 else 0.0); r = net / s.risk
        s.n += 1; s.wins += net > 0; s.sumR += r; s.sumR2 += r * r; s.winR += max(r, 0); s.lossR += max(-r, 0)
        s.netPts += net; s.eqR += r; s.peakR = max(s.peakR, s.eqR); s.ddR = min(s.ddR, s.eqR - s.peakR)
        s.streak = s.streak + 1 if r < 0 else 0; s.worst = max(s.worst, s.streak); s.dayR += r
        s.nStop += reason == 1; s.nTgt += reason == 2; s.nTime += reason == 3; s.nDay += reason == 4
        if s.qty > 0:
            s.cash += s.qty * net * PV; s.cashPeak = max(s.cashPeak, s.cash); s.cashDD = min(s.cashDD, s.cash / s.cashPeak - 1)
        s.trades.append((s.ebar, i, s.dir, s.entry, px, r, reason, s.kind, s.ses))
        s.closed = True; s.dir = 0
    def step(s, i, atr_prev, day_open):
        s.opened = s.closed = False
        if day_open:
            s.dayR = 0.0; s.pDir = 0
            if s.dir != 0: s.exit_at(O[i], 4, i)
        if s.pDir != 0:
            if s.pWait > 0: s.pWait -= 1
            elif atr_prev > 0:
                s.dir = s.pDir; s.pDir = 0; s.entry = O[i]; s.risk = STOP_ATR * atr_prev
                s.stop = O[i] - s.dir * s.risk; s.target = O[i] + s.dir * TGT_ATR * atr_prev
                s.bars = 0; s.kind = s.pKind; s.ses = s.pSes; s.ebar = i
                perC = (s.risk + COST + SLIP) * PV
                s.qty = math.floor(s.cash * RISK_PCT / 100 / perC) if perC > 0 else 0
                s.tooWide += s.qty < 1; s.opened = True
            else: s.pDir = 0
        if s.dir != 0:
            s.bars += 1
            hit_stop = L[i] <= s.stop if s.dir == 1 else H[i] >= s.stop
            hit_tgt = H[i] >= s.target if s.dir == 1 else L[i] <= s.target
            if hit_stop: s.exit_at(min(O[i], s.stop) if s.dir == 1 else max(O[i], s.stop), 1, i)
            elif hit_tgt: s.exit_at(s.target, 2, i)
            elif s.bars >= MAX_BARS: s.exit_at(C[i], 3, i)

book, twin = Grader(), Grader()
ct_hm = np.array([(dt.datetime.utcfromtimestamp(t/1000).hour, dt.datetime.utcfromtimestamp(t/1000).minute) for t in T])
last_bar = (ct_hm[:, 0] == 15) & (ct_hm[:, 1] == 55)          # session.islastbar on CME 5m (16:00 CT close)
f = {k: g(k) for k in ["v_trendBuy","v_rangeBuy","v_breakBuy","v_trendSell","v_rangeSell","v_breakSell","v_scoreB","v_scoreS","v_need","v_htf","v_inKZ","v_inNY","v_inLon"]}
my_buy = np.zeros(N, bool); my_sell = np.zeros(N, bool)
for i in range(N):
    a_prev = atr[i-1] if i > 0 else float("nan")
    book.step(i, a_prev, nd[i]); twin.step(i, a_prev, nd[i])
    can = i > 60 and not last_bar[i] and book.dir == 0 and book.pDir == 0 and book.dayR > -DAY_STOP_R
    wb = f["v_trendBuy"][i] or f["v_rangeBuy"][i] or f["v_breakBuy"][i]
    ws = f["v_trendSell"][i] or f["v_rangeSell"][i] or f["v_breakSell"][i]
    okB = can and wb and f["v_scoreB"][i] >= f["v_need"][i] and f["v_htf"][i] >= 0
    okS = can and ws and f["v_scoreS"][i] >= f["v_need"][i] and f["v_htf"][i] <= 0
    buy = okB and (not okS or f["v_scoreB"][i] >= f["v_scoreS"][i]); sell = okS and not buy
    my_buy[i], my_sell[i] = buy, sell
    if buy or sell:
        d = 1 if buy else -1
        k = (1 if f["v_trendBuy"][i] else 2 if f["v_rangeBuy"][i] else 3) if buy else (1 if f["v_trendSell"][i] else 2 if f["v_rangeSell"][i] else 3)
        ses = 0 if f["v_inKZ"][i] else 1 if f["v_inNY"][i] else 2 if f["v_inLon"][i] else 3
        book.pDir, book.pKind, book.pSes, book.pWait = d, k, ses, 0
        if twin.dir == 0 and twin.pDir == 0:
            hx = int(T[i] / 60000) % 1000003; delay = 6 + ((hx * hx + 7 * hx) % 991) % 31
            twin.pDir, twin.pKind, twin.pSes, twin.pWait = d, k, ses, delay - 1

report("signals after the gate match bar for bar", (my_buy == (g("v_buy") == 1)).all() and (my_sell == (g("v_sell") == 1)).all(),
       f"(Python {my_buy.sum()} buys / {my_sell.sum()} sells, PineTS {int(g('v_buy').sum())} / {int(g('v_sell').sum())})")
pine_open = np.where(g("v_opened") == 1)[0]; pine_close = np.where(g("v_closed") == 1)[0]
py_open = np.array([t[0] for t in book.trades] + ([book.ebar] if book.dir != 0 else []))
py_close = np.array([t[1] for t in book.trades])
report("every entry bar matches", len(py_open) == len(pine_open) and (py_open == pine_open).all(), f"({len(py_open)} vs {len(pine_open)})")
report("every exit bar matches", len(py_close) == len(pine_close) and (py_close == pine_close).all(), f"({len(py_close)} vs {len(pine_close)})")
pr = np.array([t[5] for t in book.trades]); pine_r = g("v_lastR")[pine_close]
report("every trade's R matches", len(pr) == len(pine_r) and np.allclose(pr, pine_r, atol=2e-4), f"(max diff {np.max(abs(pr - pine_r)) if len(pr)==len(pine_r) else 'n/a'})")
last = N - 1
for name, mine, pine, tol in [("n", book.n, g("v_n")[last], 0), ("wins", book.wins, g("v_wins")[last], 0), ("sum R", book.sumR, g("v_sumR")[last], 0.05),
                              ("win R", book.winR, g("v_winR")[last], 0.05), ("loss R", book.lossR, g("v_lossR")[last], 0.05),
                              ("net pts", book.netPts, g("v_netPts")[last], 0.5), ("max DD R", book.ddR, g("v_ddR")[last], 0.05),
                              ("worst streak", book.worst, g("v_worst")[last], 0), ("paper cash", book.cash, g("v_cash")[last], 5.0),
                              ("too wide", book.tooWide, g("v_tooWide")[last], 0), ("stop exits", book.nStop, g("v_nStop")[last], 0),
                              ("target exits", book.nTgt, g("v_nTgt")[last], 0), ("time exits", book.nTime, g("v_nTime")[last], 0),
                              ("reopen exits", book.nDay, g("v_nDay")[last], 0), ("twin n", twin.n, g("v_tn")[last], 0),
                              ("twin sum R", twin.sumR, g("v_tSumR")[last], 0.05)]:
    report(f"stat {name}", abs(mine - pine) <= tol, f"(Python {mine:,.4f} | PineTS {pine:,.4f})")
print("\nALL CHECKS PASSED" if ok_all else "\nSOME CHECKS FAILED")
np.save("v2_trades.npy", np.array(book.trades, dtype=float)); np.save("v2_twin_trades.npy", np.array(twin.trades, dtype=float))
