"""Stage 29: owner's two clock setups (St. Louis = Central Time), 5m. Rules frozen in PREREGISTRATION.md (2026-10-26 b).
E: 7-8 PM CT, first touch of a live 5m zone (FVG / IFVG / OB) -> limit at the near edge, stop far edge +/- 0.1 ATR5,
   2R, out after 60 min. N: at the 9:00 AM CT open, price inside demand only -> buy (supply only -> sell), stop beyond
   the nearest containing zone's far edge, 2R, out after 60 min. Cost 0.30.
Controls: the same rules at every hour of the day; placebo zones shifted +/-2 ATR5.
usage: 29_clock_setups.py <minute_pickle> <out_dir>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

M1, OUT = sys.argv[1], Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
COST, BUF, MINSZ, LIFE, WIN = 0.30, 0.10, 0.25, 288, 12
m1 = pd.read_pickle(M1)[["open", "high", "low", "close"]]
b = m1.resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
T = b.index; O, H, L, C = (b[k].to_numpy() for k in ["open", "high", "low", "close"]); n = len(T)
ct = T.tz_convert("America/Chicago")
print("5m bars", n, T[0], T[-1], flush=True)

pc = np.r_[np.nan, C[:-1]]
tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
A = np.full(n, np.nan); s = tr[:14].mean(); A[13] = s
for i in range(14, n): s = (s * 13 + tr[i]) / 14; A[i] = s

# ── zone intervals: live on bars [start, end) ──
Z = []   # start, end, top, bot, dir, born
for i in range(2, n - 2):
    a = A[i]
    if np.isnan(a): continue
    for d, top, bot in ((1, L[i], H[i - 2]), (-1, L[i - 2], H[i])):
        if top - bot < MINSZ * a: continue
        seg = C[i + 1:i + 1 + LIFE]
        br = np.where(seg < bot)[0] if d == 1 else np.where(seg > top)[0]
        if not len(br):
            Z.append((i + 1, min(n, i + 1 + LIFE), top, bot, d, i)); continue
        k = i + 1 + br[0]
        Z.append((i + 1, k + 1, top, bot, d, i))
        seg2 = C[k + 1:k + 1 + LIFE]                      # IFVG: opposite type until a close through its other side
        br2 = np.where(seg2 > top)[0] if d == 1 else np.where(seg2 < bot)[0]
        Z.append((k + 1, (k + 1 + br2[0] + 1) if len(br2) else min(n, k + 1 + LIFE), top, bot, -d, k))
# OBs from 5m structure (pivots 3/3, close beyond the last confirmed swing)
P = 3; sh = sl = None
for i in range(n - 1):
    j = i - P
    if j >= P:
        if H[j] > H[j - P:j].max() and H[j] > H[j + 1:i + 1].max(): sh = [H[j], False]
        if L[j] < L[j - P:j].min() and L[j] < L[j + 1:i + 1].min(): sl = [L[j], False]
    for d, sw in ((1, sh), (-1, sl)):
        if sw is None or sw[1]: continue
        if (d == 1 and C[i] > sw[0]) or (d == -1 and C[i] < sw[0]):
            sw[1] = True
            for k in range(i - 1, max(-1, i - 11), -1):
                if (d == 1 and C[k] < O[k]) or (d == -1 and C[k] > O[k]):
                    top, bot = H[k], L[k]
                    seg = C[i + 1:i + 1 + LIFE]
                    br = np.where(seg < bot)[0] if d == 1 else np.where(seg > top)[0]
                    Z.append((i + 1, (i + 1 + br[0] + 1) if len(br) else min(n, i + 1 + LIFE), top, bot, d, i))
                    break
Z = np.array(Z, dtype=float); Z = Z[np.argsort(Z[:, 0])]
ZS = Z[:, 0].astype(int); ZE = Z[:, 1].astype(int); ZD = Z[:, 4].astype(int); ZB = Z[:, 5].astype(int)
print("zone intervals", len(Z), flush=True)


def sim(d, entry, stop, a, b_):
    risk = d * (entry - stop)
    if risk <= 0 or a >= b_: return np.nan
    tg = entry + d * 2 * risk
    for k in range(a, b_):
        if (d == 1 and L[k] <= stop) or (d == -1 and H[k] >= stop): return -1.0 - COST / risk
        if (d == 1 and H[k] >= tg) or (d == -1 and L[k] <= tg): return 2.0 - COST / risk
    return d * (C[b_ - 1] - entry) / risk - COST / risk


hour_open = np.where((ct.minute == 0))[0]
ch = ct.hour.to_numpy()


def run(ZT, ZBt, tag):
    rows = []
    for k0 in hour_open:
        if k0 + WIN + 2 >= n or np.isnan(A[k0]): continue
        if (T[k0 + WIN - 1] - T[k0]) != pd.Timedelta(minutes=55): continue   # need a full hour of bars
        lo, hi = np.searchsorted(ZS, k0 - 2 * LIFE - 2), np.searchsorted(ZS, k0 + WIN, side="right")
        idx = np.arange(lo, hi)
        a = A[k0]; hr = ch[k0]
        # ── N: inside a zone at the hour open ──
        p = O[k0]
        live = idx[(ZS[idx] <= k0) & (ZE[idx] > k0)]
        ins = live[(ZBt[live] <= p) & (ZT[live] >= p)]
        dem, sup = ins[ZD[ins] == 1], ins[ZD[ins] == -1]
        if len(dem) and not len(sup):
            st = ZBt[dem].max() - BUF * a
            rows.append(dict(t=T[k0], hour=hr, rule="N", dir=1, R=sim(1, p, st, k0, k0 + WIN), risk=p - st, tag=tag))
        elif len(sup) and not len(dem):
            st = ZT[sup].min() + BUF * a
            rows.append(dict(t=T[k0], hour=hr, rule="N", dir=-1, R=sim(-1, p, st, k0, k0 + WIN), risk=st - p, tag=tag))
        # ── E: first touch inside the hour window ──
        for d in (1, -1):
            best = None
            for k in range(k0, k0 + WIN):
                lv = idx[(ZS[idx] <= k) & (ZE[idx] > k) & (ZD[idx] == d)]
                if not len(lv): continue
                if d == 1: ok = lv[(L[k] <= ZT[lv]) & (O[k] >= ZBt[lv])]
                else: ok = lv[(H[k] >= ZBt[lv]) & (O[k] <= ZT[lv])]
                if len(ok):
                    z = ok[np.argmax(ZT[ok])] if d == 1 else ok[np.argmin(ZBt[ok])]
                    best = (k, z); break
            if best is None: continue
            k, z = best
            entry = min(ZT[z], O[k]) if d == 1 else max(ZBt[z], O[k])
            st = ZBt[z] - BUF * A[k] if d == 1 else ZT[z] + BUF * A[k]
            risk = d * (entry - st)
            if risk <= 0: continue
            if (d == 1 and L[k] <= st) or (d == -1 and H[k] >= st): R = -1.0 - COST / risk
            else: R = sim(d, entry, st, k + 1, min(n, k + 1 + WIN))
            rows.append(dict(t=T[k], hour=hr, rule="E", dir=d, R=R, risk=risk, born_in_window=ZB[z] >= k0, tag=tag))
    return pd.DataFrame(rows)


real = run(Z[:, 2], Z[:, 3], "real")
rng = np.random.default_rng(3)
sh_ = rng.choice([-1, 1], len(Z)) * 2 * np.nan_to_num(A[ZB], nan=1.0)
plc = run(Z[:, 2] + sh_, Z[:, 3] + sh_, "placebo")
R = pd.concat([real, plc]); R.to_pickle(OUT / "clock_trades.pkl")
R["period"] = np.where(R.t < pd.Timestamp("2021-01-01", tz="UTC"), "1 EXT 2016-20",
                       np.where(R.t < pd.Timestamp("2026-04-01", tz="UTC"), "2 IS 2021-26/03", "3 FWD 2026-04→10"))
yrs = {"1 EXT 2016-20": 5.0, "2 IS 2021-26/03": 5.25, "3 FWD 2026-04→10": 0.56}


def summ(g, pr=None):
    x = g.R.dropna()
    out = dict(n=len(x), win=(x > 0).mean(), meanR=x.mean(), ci95=1.96 * x.std() / np.sqrt(max(1, len(x))))
    if pr: out["pct_per_year_at_1pct_risk"] = x.sum() / yrs[pr]
    return pd.Series(out)


pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
for rule, hr in (("E", 19), ("N", 9)):
    print(f"\n=== SETUP {rule} at {hr}:00 CT ===")
    g = R[(R.rule == rule) & (R.hour == hr)]
    tab = pd.DataFrame({(pr, tg): summ(gg, pr) for (pr, tg), gg in g.groupby(["period", "tag"])}).T
    print(tab.round(3).to_string())
    if rule == "E":
        gb = g[(g.tag == "real") & (g.born_in_window == True)]
        print("zones born inside the window:"); print(pd.DataFrame({pr: summ(gg, pr) for pr, gg in gb.groupby("period")}).T.round(3).to_string())
    hh = R[(R.rule == rule) & (R.tag == "real")].groupby("hour").R.agg(["count", "mean"])
    hh["rank_of_mean"] = hh["mean"].rank(ascending=False).astype(int)
    print(f"every hour (all years, real zones) — {rule}:"); print(hh.round(3).T.to_string())
R.groupby(["rule", "tag", "hour", "period"]).R.agg(["count", "mean"]).to_csv(OUT / "clock_by_hour.csv")
