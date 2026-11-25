"""Where documented edges actually live: slow trend-following, many markets, risk-scaled (Moskowitz-Ooi-Pedersen 2012;
Hurst-Ooi-Pedersen 'A Century of Evidence on Trend-Following'). Textbook parameters, NOT tuned on this data:
TSMOM 252d sign, price vs SMA200, Donchian 55-in / 20-out; ensemble = average. Signal at day close, applied next day.
Each market scaled to 10 %/yr volatility (60d realised, capped 2x). Cost: gold 2 bp, FX 1 bp per unit turnover."""
import numpy as np, pandas as pd
from pathlib import Path
R = Path("/Users/jitheandrasubramaniam/Desktop/hey hey")
def daily_from(close: pd.Series) -> pd.Series:   # trading day rolls at 22:00 UTC (17:00 New York)
    return close.groupby((close.index + pd.Timedelta(hours=2)).normalize()).last().dropna()
mk = {}
a = np.fromfile(R / "trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)
ts = a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000
mk["GOLD"] = daily_from(pd.Series(a[:, 4], index=pd.to_datetime(ts, unit="s")))
for p in ["eurusd", "gbpusd", "usdjpy", "usdchf", "usdcad", "usdsek"]:
    d = pd.read_pickle(R / f"trading-video-intel/data/raw/histdata/{p}_1m_2016_2026.pkl")
    mk[p.upper()] = daily_from(d.close.tz_convert(None))
COST = {k: (2e-4 if k == "GOLD" else 1e-4) for k in mk}

def donchian(P):
    hi, lo = P.rolling(55).max().shift(1), P.rolling(55).min().shift(1)
    xlo, xhi = P.rolling(20).min().shift(1), P.rolling(20).max().shift(1)
    pos, out = 0, []
    for p, a1, b1, c1, d1 in zip(P, hi, lo, xlo, xhi):
        if pos == 0: pos = 1 if p > a1 else -1 if p < b1 else 0
        elif pos == 1 and p < c1: pos = -1 if p < b1 else 0
        elif pos == -1 and p > d1: pos = 1 if p > a1 else 0
        out.append(pos)
    return pd.Series(out, index=P.index, dtype=float)

def run(name, P):
    r = P.pct_change()
    vol = r.rolling(60).std() * np.sqrt(252)
    sig = {"TSMOM-252": np.sign(P / P.shift(252) - 1), "SMA200": np.sign(P - P.rolling(200).mean()), "DONCH-55/20": donchian(P)}
    sig["ENSEMBLE"] = sum(sig.values()) / 3
    out = {}
    for k, s in sig.items():
        w = (s * (0.10 / vol).clip(upper=2)).shift(1)               # decided at yesterday's close
        pnl = (w * r - COST[name] * w.diff().abs()).dropna()
        out[k] = pnl
    bh = (r * (0.10 / vol).clip(upper=2).shift(1)).dropna()         # always long, same risk scaling
    out["BUY&HOLD (risk-scaled)"] = bh
    return out, sig

def stats(x):
    x = x[x.index.year >= x.index.year.min() + 1]                   # drop the warm-up year
    eq = x.cumsum(); dd = (eq - eq.cummax()).min()
    return dict(ann_ret=x.mean() * 252 * 100, sharpe=x.mean() / x.std() * np.sqrt(252), maxDD=dd * 100,
                dayPF=x[x > 0].sum() / -x[x < 0].sum())

def trade_pf(P, s):   # per-trade profit factor of a sign rule: a trade = a run of the same non-zero sign, P&L in % of price
    s = s.shift(1).fillna(0); r = P.pct_change().fillna(0)
    grp = (s != s.shift()).cumsum(); res = []
    for _, g in r.groupby(grp):
        sg = s.loc[g.index[0]]
        if sg != 0: res.append(sg * g.sum())
    res = np.array(res); return len(res), (res > 0).mean() * 100, res[res > 0].sum() / -res[res < 0].sum()

rows, port = [], {}
for name, P in mk.items():
    res, sig = run(name, P)
    port[name] = res["ENSEMBLE"]
    first = P.index.year.min() + 1
    mid = 2020 if name == "GOLD" else 2022
    for k, x in res.items():
        for lab, xx in [("all", x), (f"{first}-{mid-1}", x[x.index.year < mid]), (f"{mid}-2026", x[x.index.year >= mid])]:
            st = stats(xx) if lab == "all" else dict(ann_ret=xx.mean()*252*100, sharpe=xx.mean()/xx.std()*np.sqrt(252), maxDD=((xx.cumsum()-xx.cumsum().cummax()).min())*100, dayPF=xx[xx>0].sum()/-xx[xx<0].sum())
            rows.append(dict(market=name, rule=k, period=lab, **st))
    if name == "GOLD":
        for k in ["SMA200", "DONCH-55/20", "TSMOM-252"]:
            n, w, pf = trade_pf(P, sig[k]); print(f"GOLD {k}: {n} trades in {P.index.year.max()-P.index.year.min()} yrs, win {w:.0f} %, trade PF {pf:.2f}")
        # long side vs short side of the ensemble
        s = sig["ENSEMBLE"]; vol = P.pct_change().rolling(60).std()*np.sqrt(252); r = P.pct_change()
        for side, m in [("long side only", s.clip(lower=0)), ("short side only", s.clip(upper=0))]:
            w = (m * (0.10/vol).clip(upper=2)).shift(1); x = (w*r - COST[name]*w.diff().abs()).dropna(); x = x[x.index.year >= 2013]
            print(f"GOLD ENSEMBLE {side}: ann {x.mean()*252*100:.1f} %, Sharpe {x.mean()/x.std()*np.sqrt(252):.2f}")
df = pd.DataFrame(rows)
pd.set_option("display.width", 220); pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(df[df.rule.isin(["ENSEMBLE", "BUY&HOLD (risk-scaled)"])].to_string(index=False))
P_ = pd.DataFrame(port).dropna(how="all")
fx = P_.drop(columns="GOLD").mean(axis=1).dropna(); fx = fx[fx.index.year >= 2017]
allm = P_.mean(axis=1).dropna(); allm = allm[allm.index.year >= 2017]
for lab, x in [("FX-6 basket ensemble 2017-2026", fx), ("GOLD+FX-6 basket 2017-2026", allm)]:
    print(lab, {k: round(v, 2) for k, v in stats(pd.concat([pd.Series([0.0], index=[x.index[0] - pd.Timedelta(days=400)]), x])).items()})
df.to_csv("trend_results.csv", index=False)
