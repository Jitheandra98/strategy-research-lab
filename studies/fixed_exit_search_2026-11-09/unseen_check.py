"""UNSEEN CHECK (2026-11-09): the closest rule from search.py on MGC1! futures data the search never saw.
Rule: in a daily downtrend (daily close < EMA200), when a 5m bar closes down through a $100 level (same session),
sell 1 MGC at the next 5m open; target -10 pt ($100), stop +25 pt ($250); same fills and costs as search.py.
Data: MGC1! 5m Sep 13 -> Nov 6 2026 (signals from Sep 25 on) and MGC1! 1h Jan 2025 -> Nov 2026 for the daily trend."""
import json
import numpy as np, pandas as pd

ROOT = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/edge_search_2026-11-07/"
TP, SL, COST, SLIP, TICK, USD = 10.0, 25.0, 0.3, 0.2, 0.1, 10.0


def load(p):
    a = np.array(json.load(open(ROOT + p)), dtype=float)
    idx = pd.to_datetime(a[:, 0].astype(np.int64), unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
    return pd.DataFrame(a[:, 1:], columns=list("ohlc"), index=idx)


m5, h1 = load("mgc1_5m.json"), load("mgc1_60m.json")
D = h1.resample("1D", offset="18h").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
ema200 = D.c.ewm(span=200, adjust=False).mean()
d_close = (D.index + pd.Timedelta("1D")).asi8
down = (D.c < ema200).to_numpy()
print(f"MGC daily bars {D.index[0].date()} -> {D.index[-1].date()} ({len(D)}); EMA200 valid from bar 200 = "
      f"{D.index[199].date()}")
print("Daily close vs EMA200, last 8 weeks (Fridays):")
for d_, r in D[D.index >= "2026-09-10"].iterrows():
    if d_.weekday() == 3:                                            # bin starting Thursday 18:00 = Friday session
        print(f"  {(d_ + pd.Timedelta('1D')).date()}  close {r.c:8.1f}  EMA200 {ema200[d_]:8.1f}  "
              f"{'DOWN' if r.c < ema200[d_] else 'up'}")

O, H, L, C = (m5[k].to_numpy() for k in "ohlc")
ns = m5.index.asi8
sday = (m5.index + pd.Timedelta(hours=6)).normalize().asi8
k_d = np.searchsorted(d_close, ns + 5 * 60 * 10 ** 9, side="right") - 1    # daily bar completed before the 5m close
trend_down = (k_d >= 199) & down[np.clip(k_d, 0, len(D) - 1)]
lv = np.floor(C / 100.0)
sig = np.r_[False, (lv[1:] < lv[:-1]) & (sday[1:] == sday[:-1])] & trend_down
sig &= m5.index >= pd.Timestamp("2026-09-25")
cand = np.flatnonzero(sig)

trades, last_exit = [], -1
for k in cand:
    i = k + 1
    if i >= len(C) or i <= last_exit: continue
    e, res, x, why = O[i], None, None, None
    for j in range(i, len(C)):
        if j > i and O[j] >= e + SL: res, x, why = e - O[j] - SLIP, j, "STOP (gap)"; break
        if H[j] >= e + SL: res, x, why = -SL - SLIP, j, "STOP"; break
        if L[j] <= e - TP - TICK: res, x, why = TP, j, "TARGET"; break
    if x is None:
        trades.append(dict(entry=m5.index[i], price=e, exit="open at data end", net_usd=(e - C[-1] - COST) * USD))
        break
    trades.append(dict(entry=m5.index[i], price=e, exit=f"{why} {m5.index[x]}", net_usd=(res - COST) * USD))
    last_exit = x

T = pd.DataFrame(trades)
print(f"\nSignals Sep 25 -> Nov 6 (daily downtrend + close down through a $100 level): {len(cand)}; trades taken: {len(T)}")
for _, r in T.iterrows():
    print(f"  SELL {r.entry}  at {r.price:8.1f}  ->  {r.exit:32s}  ${r.net_usd:+7.0f}")
if len(T):
    closed = T[~T.exit.str.startswith("open")]
    w = (closed.net_usd > 0).sum()
    print(f"closed trades: {len(closed)}, won {w}, net ${closed.net_usd.sum():+,.0f}"
          + (f"; still open: ${T.net_usd.iloc[-1]:+,.0f} marked" if len(closed) < len(T) else ""))
