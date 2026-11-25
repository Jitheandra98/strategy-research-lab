"""Same trades, filtered by Desk Context's own 1H bias (last completed 1H close vs 1H EMA50): buys only when BULL, sells only
when BEAR. Control = same bracket at the same NY clock time on random other days whose 1H bias also matches the direction."""
import numpy as np, pandas as pd
src = open("theorem.py").read()
exec(src.split("days, first = np.unique")[0])                      # data, ATRs, zones, walk()
days, first = np.unique(tday, return_index=True); bounds = np.r_[first, N]
hEMA = pd.Series(hC).ewm(span=50, adjust=False).mean().to_numpy()
hbias = np.sign(hC - hEMA)                                           # bias known when that hour closes
bias_bar = np.repeat(np.r_[np.nan, hbias[:-1]], he - hs)            # last COMPLETED hour for every 5m bar
T = pd.read_csv("trades.csv")
T["bias"] = bias_bar[T.k.to_numpy()]
F = T[T.bias == T.d].copy()
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
for row in F.itertuples():
    pool = by_clock[clock[row.k]]; pool = pool[bias_bar[pool] == row.d]; rs = []
    for r in pool[rng.integers(0, len(pool), 60)]:
        if dayidx[r] == dayidx[row.k]: continue
        e = day_end(r)
        if e <= r: continue
        px = C[r]; rs.append((walk(r + 1, row.d, px, px - row.d * row.R, px + row.d * row.tgt_dist, e) - COST) / row.R)
        if len(rs) == 20: break
    ctrl.append(np.mean(rs) if rs else np.nan)
F["ctrl_r"] = ctrl
F["period"] = np.where(F.y <= 2019, "2012-2019", "2020-2026")
def summ(g):
    r = g.r; w = r[r > 0].sum(); l = -r[r < 0].sum()
    return pd.Series(dict(trades=len(g), per_year=len(g) / g.y.nunique(), win=(r > 0).mean() * 100, avg_R=r.mean(), PF=w / l if l else np.nan,
                          random_same_bias_R=g.ctrl_r.mean(), edge_vs_random=r.mean() - g.ctrl_r.mean(), avg_usd_1MGC=g.usd.mean()))
pd.set_option("display.width", 250); pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print("WITH Desk Context 1H bias (buys only when BULL, sells only when BEAR):")
print(F.groupby(["v", "tn", "period"]).apply(summ, include_groups=False).to_string())
print("\nV1 with bias, by side, target = other side:")
print(F[(F.v == "V1 THEOREM") & (F.tn == "other side")].groupby(["d", "period"]).apply(summ, include_groups=False).to_string())
F.to_csv("trades_bias.csv", index=False)
