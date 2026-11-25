"""US STOCK STRATEGIES 1926 -> 2026 (2026-11-09). Rules: SPEC_stock_factors.md, written before looking at the numbers.
Reads the Kenneth R. French Data Library files (public; see provenance.csv). The data folder is passed as an argument:
  python3 -I stock_factors.py data_raw/kenfrench > stock_factors.txt"""
import sys, os
import numpy as np, pandas as pd

RAW = sys.argv[1]
PUB = {"SMB": 1981, "HML": 1992, "Mom": 1993, "ST_Rev": 1990, "RMW": 2013, "CMA": 2004}
NAME = {"Mkt-RF": "Market (stocks minus T-bills)", "SMB": "Size (small minus big)", "HML": "Value (cheap minus dear)",
        "Mom": "Momentum (winners minus losers)", "ST_Rev": "Short-term reversal", "RMW": "Profitability (robust - weak)",
        "CMA": "Investment (conservative - aggr.)"}
LAST10 = ("2016-10", "2026-09")


def read_monthly(path):
    """First block of YYYYMM rows; column names from the line just above it. Values are % per month."""
    lines = open(path, encoding="latin-1").read().splitlines()
    first = next(i for i, ln in enumerate(lines) if ln.split(",")[0].strip().isdigit()
                 and len(ln.split(",")[0].strip()) == 6)
    cols = [c.strip() for c in lines[first - 1].split(",")[1:] if c.strip()]
    rows = []
    for ln in lines[first:]:
        p = [x.strip() for x in ln.split(",")]
        if not (p[0].isdigit() and len(p[0]) == 6): break
        rows.append([float(x) for x in p[1:1 + len(cols)]])
    idx = pd.to_datetime([ln.split(",")[0].strip() for ln in lines[first:first + len(rows)]], format="%Y%m")
    df = pd.DataFrame(rows, index=idx, columns=cols).replace([-99.99, -999.0], np.nan) / 100.0
    return df


def find(sub):
    d = os.path.join(RAW, sub)
    return os.path.join(d, next(f for f in os.listdir(d) if f.endswith(".csv")))


f3 = read_monthly(find("F-F_Research_Data_Factors_CSV"))
f5 = read_monthly(find("F-F_Research_Data_5_Factors_2x3_CSV"))
mom = read_monthly(find("F-F_Momentum_Factor_CSV"))
rev = read_monthly(find("F-F_ST_Reversal_Factor_CSV"))
R = pd.concat([f3[["Mkt-RF", "SMB", "HML"]], mom.iloc[:, [0]].rename(columns=lambda c: "Mom"),
               rev.iloc[:, [0]].rename(columns=lambda c: "ST_Rev"), f5[["RMW", "CMA"]]], axis=1)
RF = f3["RF"]


def longest_run(b):
    best = run = 0
    for v in b:
        run = run + 1 if v else 0
        best = max(best, run)
    return best


def stats(r):
    r = r.dropna()
    n = len(r)
    if n < 24: return None
    m, s = r.mean(), r.std(ddof=1)
    eq = (1 + r).cumprod()
    peak = eq.cummax()
    yearly = (1 + r).groupby(r.index.year).prod() - 1
    return dict(start=r.index[0].strftime("%Y-%m"), end=r.index[-1].strftime("%Y-%m"), years=n / 12,
                ann=12 * m, vol=np.sqrt(12) * s, sharpe=(12 * m) / (np.sqrt(12) * s), t=m / (s / np.sqrt(n)),
                worst_month=r.min(), worst_year=yearly.min(), worst_year_at=int(yearly.idxmin()),
                pos_years=(yearly > 0).mean(), maxdd=(1 - eq / peak).max(), underwater_yrs=longest_run(eq < peak) / 12,
                growth=eq.iloc[-1])


def line(tag, s):
    if s is None: return f"    {tag:22s} (too short)"
    return (f"    {tag:22s} {s['start']}..{s['end']}  {s['ann'] * 100:+6.2f}%/yr  vol {s['vol'] * 100:5.1f}%  "
            f"Sharpe {s['sharpe']:+5.2f}  t {s['t']:+5.2f}  worst yr {s['worst_year'] * 100:+6.1f}% ({s['worst_year_at']})  "
            f"yrs up {s['pos_years'] * 100:3.0f}%  maxDD {s['maxdd'] * 100:5.1f}%  longest under water "
            f"{s['underwater_yrs']:4.1f} yrs")


rows, verdicts = [], []
print("US stock strategies from the Kenneth R. French Data Library (all NYSE/AMEX/NASDAQ stocks incl. dead ones),")
print(f"monthly, {R.index[0]:%b %Y} -> {R.index[-1]:%b %Y}. Long-short paper portfolios, BEFORE trading costs.\n")
for c in ["Mkt-RF", "SMB", "HML", "Mom", "ST_Rev", "RMW", "CMA"]:
    r = R[c].dropna()
    print(f"{NAME[c]}  [{c}]" + (f"   published {PUB[c]}" if c in PUB else ""))
    wins = [("full history", r)]
    if c in PUB:
        wins += [(f"before publication", r[r.index.year <= PUB[c]]), (f"after publication", r[r.index.year > PUB[c]])]
    wins += [("last 10 years", r[LAST10[0]:LAST10[1]])]
    out = {}
    for tag, x in wins:
        s = stats(x)
        out[tag] = s
        print(line(tag, s))
        if s: rows.append(dict(strategy=c, window=tag, **s))
    post = out.get("after publication") or out["full history"]
    still = post["ann"] > 0 and post["t"] >= 2 and out["last 10 years"]["ann"] > 0
    verdicts.append((c, still, post, out["last 10 years"]))
    print(f"    -> {'STILL WORKS' if still else 'DOES NOT PASS'} (after publication {post['ann'] * 100:+.2f}%/yr, "
          f"t {post['t']:+.2f}; last 10 years {out['last 10 years']['ann'] * 100:+.2f}%/yr)\n")
pd.DataFrame(rows).to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_factors_stats.csv"), index=False)

tot = (1 + R["Mkt-RF"].dropna() + RF.reindex(R["Mkt-RF"].dropna().index)).cumprod()
bills = (1 + RF.dropna()).cumprod()
print(f"$1 in all US stocks in Jul 1926 -> ${tot.iloc[-1]:,.0f} by Sep 2026 (before tax and fees); "
      f"$1 in T-bills -> ${bills.iloc[-1]:,.0f}")
print("\nSUMMARY  (after publication = the years nobody could have mined)")
for c, still, post, l10 in verdicts:
    print(f"  {NAME[c]:36s} after publication {post['ann'] * 100:+6.2f}%/yr (t {post['t']:+5.2f}) | last 10 yrs "
          f"{l10['ann'] * 100:+6.2f}%/yr | {'STILL WORKS' if still else 'does not pass'}")
