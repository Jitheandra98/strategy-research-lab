"""CROSS-CHECK (information only, SPEC.md): the 10 gold finalists, frozen, on 9 other markets. Results in R.
ES, SI, HG, TY 5 m Nov 2022 -> Nov 2026 (research/gold101/data); EURUSD, GBPUSD, USDJPY, USDCAD, USDCHF 5 m 2016 -> 2026
(built by fx_to_5m.py). Cost: 2 ticks per round trip + 1 tick at stops (FX: 1 pip + 0.5 pip).
Run: python3 -I cross_check.py <fx_5m_dir> > cross_check.txt"""
import sys, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import Market, load_csv_et, ENTRIES, STOPS, EXITS

FX = sys.argv[1]
G101 = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/gold101/data/"
F = pd.read_csv(os.path.join(HERE, "finalists.csv"))
COPIES = 50

mk = []
for key, tick, name in [("es", 0.25, "ES"), ("si", 0.005, "SI"), ("hg", 0.0005, "HG"), ("ty", 0.015625, "TY")]:
    mk.append(Market(name, *load_csv_et(G101 + f"{key}5m.csv"), tick=tick, cost=2 * tick, slip=tick, minstop=2 * tick))
for p, pip in [("eurusd", 1e-4), ("gbpusd", 1e-4), ("usdjpy", 1e-2), ("usdcad", 1e-4), ("usdchf", 1e-4)]:
    z = np.load(os.path.join(FX, f"{p}_5m.npz"))
    mk.append(Market(p.upper(), z["ns"], z["o"], z["h"], z["l"], z["c"], tick=pip / 10, cost=pip, slip=pip / 2,
                     minstop=pip))
for m in mk:
    print(f"{m.name:7s} {m.N:8,d} bars  {m.idx[0]} -> {m.idx[-1]}   cost {m.cost:g} + {m.slip:g} at stops")


def tstat(x):
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 1 and x.std(ddof=1) > 0 else np.nan


print("\nEach cell: trades, mean net R per trade (t), before-cost R, and the % of random-timing copies it beats")
rows = []
for k, r in F.iterrows():
    tf, et, flt = r.tf, ENTRIES.index(r.entry), int(r["filter"] == "with HTF")
    sm, xm = STOPS.index(r.stop), EXITS.index(r.exit)
    print(f"\n{r.final} {tf} {r.entry} ({r['filter']}) | {r.stop}, {r.exit}")
    pooled, pooled_g = [], []
    for m in mk:
        P = m.prepare(tf)
        ok = m.htf_ok(tf, P) if flt else np.ones(len(P["et"]), bool)
        mask = (P["et"] == et) & (P["fi"] >= 0) & ok
        sim = m.run(P, sm, xm)
        ev = m.trades(P, sim, mask)
        R = sim[1][ev] / sim[2][ev]
        sg = m.run(P, sm, xm, cost=0.0, slip=0.0)
        eg = m.trades(P, sg, mask)
        Rg = sg[1][eg] / sg[2][eg]
        pl = m.placebo_means(P, ev, sim, xm, COPIES, seed=7 + k, in_r=True) if len(ev) else np.array([np.nan])
        beat = 100 * np.mean(pl < R.mean()) if len(ev) else np.nan
        pooled.append(R); pooled_g.append(Rg)
        rows.append(dict(final=r.final, market=m.name, n=len(R), mean_R=R.mean() if len(R) else np.nan, t=tstat(R),
                         gross_R=Rg.mean() if len(Rg) else np.nan, placebo_R=np.nanmean(pl), beats_pct=beat))
        print(f"   {m.name:7s} {len(R):5d} trades  {R.mean() if len(R) else np.nan:+.3f}R (t {tstat(R):+5.2f})  "
              f"gross {Rg.mean() if len(Rg) else np.nan:+.3f}R  placebo {np.nanmean(pl):+.3f}R  beats {beat:3.0f} %")
    a, g = np.concatenate(pooled), np.concatenate(pooled_g)
    print(f"   POOLED  {len(a):5d} trades  {a.mean():+.3f}R (t {tstat(a):+5.2f})  gross {g.mean():+.3f}R  | markets "
          f"with net > 0: {sum(x.mean() > 0 for x in pooled if len(x))} of {len(mk)}")
pd.DataFrame(rows).to_csv(os.path.join(HERE, "cross_check.csv"), index=False)
C = pd.DataFrame(rows)
print(f"\nSUMMARY: {(C.mean_R > 0).sum()} of {len(C)} finalist x market cells made money after costs; "
      f"{(C.t >= 2).sum()} had t >= 2; {(C.beats_pct >= 95).sum()} beat 95 % of random-timing copies.")
