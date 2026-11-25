"""TREND FOLLOWING ACROSS ALL FUTURES (2026-11-09). Rules: SPEC_trend.md, written before the data was pulled.
Data: tv/data/<KEY>_adj.json (back-adjusted) and <KEY>_raw.json (unadjusted), daily, from the owner's TradingView.
Run: python3 -I trend.py tv/data > trend.txt"""
import sys, os, json, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore", message="Mean of empty slice")

DATA = sys.argv[1]
OUTDIR = os.path.dirname(os.path.abspath(__file__))
SECTOR = {"Equities": ["ES", "NQ", "YM", "RTY", "FDAX", "FESX", "NKD"], "Bonds": ["ZT", "ZF", "ZN", "ZB", "FGBL"],
          "Currencies": ["6E", "6J", "6B", "6A", "6C", "6S", "6N", "6M", "DX"], "Energy": ["CL", "NG", "HO", "RB", "BRN"],
          "Metals": ["GC", "SI", "HG", "PL", "PA"], "Grains": ["ZC", "ZW", "ZS", "ZM", "ZL", "KE"],
          "Softs": ["KC", "SB", "CC", "CT", "OJ"], "Livestock": ["LE", "HE", "GF"]}
TARGET, COM, COST, COST_STRESS, NRAND = 0.40, 60, 0.0005, 0.0020, 1000
WINDOWS = [("full history", None, None), ("published sample (to 2009)", None, "2009-12"),
           ("2010-2012", "2010-01", "2012-12"), ("AFTER PUBLICATION 2013-2026", "2013-01", None)]


def load(key, mode):
    f = os.path.join(DATA, f"{key}_{mode}.json")
    if not os.path.exists(f): return None
    b = np.array(json.load(open(f))["bars"], dtype=float)
    day = pd.to_datetime(((b[:, 0] + 43200) // 86400).astype(np.int64), unit="D")   # trading date
    return pd.Series(b[:, 4], index=day).groupby(level=0).last()


# ----------------------------------------------------------------------------------------- data + quality checks
rets, notes = {}, []
print("=== DATA CHECK (daily closes; return = change in back-adjusted price / previous unadjusted price) ===")
for sec, keys in SECTOR.items():
    for k in keys:
        adj, raw = load(k, "adj"), load(k, "raw")
        if adj is None or raw is None:
            notes.append(f"{k}: not available"); continue
        both = pd.concat([adj.rename("adj"), raw.rename("raw")], axis=1, join="inner").dropna()
        r = both.adj.diff() / both.raw.shift(1)
        bad = (both.raw.shift(1) <= 0) | (r.abs() > 0.5)
        r[bad] = np.nan
        r = r.iloc[1:]
        last_gap = abs(both.adj.iloc[-1] - both.raw.iloc[-1])
        rets[k] = r
        print(f"  {k:5s} {sec:10s} {both.index[0].date()} -> {both.index[-1].date()}  {len(both):6d} days  "
              f"dropped {int(bad.sum())}  |r|>10%: {int((r.abs() > 0.10).sum()):3d}  max |r| {r.abs().max() * 100:5.1f}%  "
              f"adj-raw at end {last_gap:.4f}")
for n in notes: print("  " + n)
R = pd.DataFrame(rets).sort_index()
R = R[R.index >= "1980-01-01"]
print(f"\n{R.shape[1]} markets, {R.index[0].date()} -> {R.index[-1].date()}")

# ------------------------------------------------------------------------------------- monthly building blocks
var = (R ** 2).ewm(com=COM, min_periods=60, ignore_na=True).mean()
vol = np.sqrt(var * 261)                                          # annualized, known at each day's close
mend = R.groupby(R.index.to_period("M")).apply(lambda g: g.index[-1])   # last trading day of each month
mend = pd.DatetimeIndex(mend.values)
EARN = mend + pd.offsets.MonthEnd(0) + pd.offsets.MonthEnd(1)    # calendar end of the NEXT month
lev = (TARGET / vol).reindex(mend)                               # position size per unit sign at month-end
cum = (1 + R.fillna(0)).cumprod()
have = R.notna().astype(int).cumsum()
ret_k = {}
for kmon in (1, 3, 12):
    past = cum.reindex(mend) / cum.reindex(mend).shift(kmon) - 1
    enough = (have.reindex(mend) - have.reindex(mend).shift(kmon)) >= 15 * kmon       # real data in the window
    ret_k[kmon] = past.where(enough)
# R_next[m] = sum of daily returns in the month AFTER month-end m (a sum is close to the month's return)
month_of = R.index.to_period("M")
msum = R.groupby(month_of).sum(min_count=10)
mcount = R.groupby(month_of).count()
msum.index = msum.index.to_timestamp("M")
nxt = msum.shift(-1).reindex(mend.to_period("M").to_timestamp("M"))
nxt.index = mend
S = (lev * nxt)                                                    # scaled next-month return per market per unit sign
valid = lev.notna() & nxt.notna()

sig12 = np.sign(ret_k[12])
blend = (np.sign(ret_k[1]) + np.sign(ret_k[3]) + np.sign(ret_k[12])) / 3
sig12, blend = sig12.where(valid & ret_k[12].notna()), blend.where(valid & ret_k[12].notna() & ret_k[1].notna()
                                                                    & ret_k[3].notna())


def portfolio(sig, cost):
    pos = sig * lev
    gross = (sig * S).mean(axis=1, skipna=True)
    turn = (pos.fillna(0) - pos.shift(1).fillna(0)).abs()
    n = sig.notna().sum(axis=1).replace(0, np.nan)
    net = gross - cost * turn.sum(axis=1) / n
    out = pd.DataFrame({"gross": gross, "net": net, "n": n})
    out.index = EARN                                               # label by the month the return is earned in
    return out.dropna(subset=["gross"])


def stat(x):
    x = x.dropna()
    if len(x) < 12: return None
    m, s = x.mean(), x.std(ddof=1)
    eq = (1 + x).cumprod()
    return dict(ann=12 * m, vol=np.sqrt(12) * s, sharpe=np.sqrt(12) * m / s, t=m / s * np.sqrt(len(x)),
                maxdd=(1 - eq / eq.cummax()).max(), yrs=len(x) / 12)


def window(df, a, b):
    d = df
    if a: d = d[d.index >= pd.Timestamp(a)]
    if b: d = d[d.index <= pd.Timestamp(b) + pd.offsets.MonthEnd(0)]
    return d


P12, PBL = portfolio(sig12, COST), portfolio(blend, COST)
P12s, PBLs = portfolio(sig12, COST_STRESS), portfolio(blend, COST_STRESS)
LONG = portfolio(pd.DataFrame(1.0, index=sig12.index, columns=sig12.columns).where(valid), 0.0)

# random-sign luck check (gross, monthly): 1,000 coin-flip portfolios with the same sizing
rng = np.random.default_rng(42)
Sv, Vv = S.to_numpy(), valid.to_numpy()
rand = np.empty((NRAND, len(S)))
for b in range(NRAND):
    sg = rng.choice([-1.0, 1.0], size=Sv.shape)
    x = np.where(Vv, sg * Sv, np.nan)
    with np.errstate(invalid="ignore"):
        rand[b] = np.nanmean(x, axis=1)
RAND = pd.DataFrame(rand.T, index=EARN)

print("\n=== RESULTS (annual figures; positions sized to 40 % vol per market, average across markets) ===")
rows = []
verdict = {}
for name, P, Ps in (("TSMOM-12", P12, P12s), ("Trend blend 1/3/12", PBL, PBLs)):
    print(f"\n{name}")
    for wn, a, b in WINDOWS:
        g, s_ = stat(window(P, a, b).gross), stat(window(P, a, b).net)
        st_ = stat(window(Ps, a, b).net)
        lg = stat(window(LONG, a, b).gross)
        rr = window(RAND, a, b)
        rs = np.sqrt(12) * rr.mean() / rr.std(ddof=1)
        pct = 100 * (rs < g["sharpe"]).mean() if g else np.nan
        npm = window(P, a, b).n.mean()
        print(f"  {wn:28s} {s_['yrs']:4.1f} yrs, ~{npm:3.0f} mkts | net {s_['ann'] * 100:+5.1f}%/yr vol {s_['vol'] * 100:4.1f}% "
              f"Sharpe {s_['sharpe']:+5.2f} t {s_['t']:+5.2f} maxDD {s_['maxdd'] * 100:4.1f}% | stress cost Sharpe "
              f"{st_['sharpe']:+5.2f} | gross Sharpe {g['sharpe']:+5.2f} beats {pct:5.1f}% of random | always-long "
              f"Sharpe {lg['sharpe']:+5.2f}")
        rows.append(dict(strategy=name, window=wn, **{f"net_{k}": v for k, v in s_.items()},
                         gross_sharpe=g["sharpe"], beats_random_pct=pct, stress_sharpe=st_["sharpe"],
                         long_sharpe=lg["sharpe"]))
        if wn.startswith("AFTER"):
            verdict[name] = (s_["sharpe"] > 0 and s_["t"] >= 2 and pct >= 95, s_, pct)
pd.DataFrame(rows).to_csv(os.path.join(OUTDIR, "trend_stats.csv"), index=False)

print("\nTSMOM-12 by calendar year (net):")
yr = P12.net.groupby(P12.index.year).apply(lambda x: (1 + x).prod() - 1)
print("  " + "  ".join(f"{y % 100:02d}:{v * 100:+.0f}%" for y, v in yr.items()))

print("\nTSMOM-12 after publication (2013-2026) by sector, gross Sharpe of each sector's own average:")
post = sig12.index >= pd.Timestamp("2012-12-01")
for sec, keys in SECTOR.items():
    ks = [k for k in keys if k in S.columns]
    if not ks: continue
    x = (sig12[ks] * S[ks]).mean(axis=1, skipna=True)[post].dropna()
    print(f"  {sec:10s} {len(ks)} mkts: {np.sqrt(12) * x.mean() / x.std(ddof=1):+5.2f}  "
          f"({12 * x.mean() * 100:+5.1f}%/yr at 40% vol per market)")

print("\nVERDICT (after publication, 2013 -> 2026; net Sharpe > 0 with t >= 2 AND beats 95% of random-sign portfolios):")
for name, (ok, s_, pct) in verdict.items():
    print(f"  {name:20s} {'STILL WORKS' if ok else 'DOES NOT PASS'}: Sharpe {s_['sharpe']:+.2f}, t {s_['t']:+.2f}, "
          f"{s_['ann'] * 100:+.1f}%/yr at {s_['vol'] * 100:.1f}% vol, beats {pct:.1f}% of random")
