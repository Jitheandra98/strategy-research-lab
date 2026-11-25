"""MARKET-STRUCTURE ENTRIES x ANY STOP AND TARGET on gold (2026-11-09). Rules: SPEC.md (written before testing).
Run: python3 -I structure_exits.py > results.txt   (writes grid.csv, finalists.csv, finalist_trades.csv)"""
import sys, os, time
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import (Market, load_xau5m, load_csv_et, ENTRIES, STOPS, EXITS, HTF)

XAU = "/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64"
GC = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/gold101/data/gc5m.csv"
USD, DEV_END, HO_FIRST, HO_LAST = 10.0, 2019, 2020, pd.Timestamp("2026-09-24 23:59")
MIN_DEV, NFINAL, COPIES, T_PASS = 150, 10, 200, 2.58
TFS = ["5m", "15m", "1h", "4h"]
t00 = time.time()


def st(x):
    n = len(x)
    if n < 2:
        return dict(n=n, mean=np.nan, t=np.nan, pf=np.nan, win=np.nan, total=float(np.sum(x)) if n else 0.0)
    m, s = x.mean(), x.std(ddof=1)
    gl = -x[x < 0].sum()
    return dict(n=n, mean=m, t=m / s * np.sqrt(n) if s > 0 else np.nan, pf=x[x > 0].sum() / gl if gl > 0 else np.inf,
                win=(x > 0).mean(), total=x.sum())


def maxdd(x):
    eq = np.cumsum(x)
    return float(np.max(np.maximum.accumulate(np.r_[0.0, eq]) - np.r_[0.0, eq])) if len(x) else 0.0


gold = Market("XAU/USD 5m", *load_xau5m(XAU), tick=0.1, cost=0.3, slip=0.2, minstop=0.3)
print(f"Gold 5 m bars: {gold.N:,}  {gold.idx[0]} -> {gold.idx[-1]}  (New York clock)")
print(f"Costs per MGC: {gold.cost} pt round trip + {gold.slip} pt at stops; $ {USD:.0f} per point.\n")

# ------------------------------------------------------------------------------------------------- full grid
rows, keep_sim = [], {}
for tf in TFS:
    P = gold.prepare(tf)
    ok = gold.htf_ok(tf, P)
    when = gold.idx[np.minimum(P["fi"], gold.N - 1)]
    inwin = (P["fi"] >= 0) & (when <= HO_LAST)
    yr = gold.year[np.minimum(P["fi"], gold.N - 1)]
    print(f"{tf}: {len(P['eb']):,} signals; with the {HTF[tf]} trend: {int(ok.sum()):,}")
    for sm in range(5):
        for xm in range(9):
            sim = gold.run(P, sm, xm)
            for et in range(8):
                for flt in (0, 1):
                    mask = (P["et"] == et) & inwin & (ok if flt else True)
                    ev = gold.trades(P, sim, mask)
                    usd = sim[1][ev] * USD
                    rr = sim[1][ev] / sim[2][ev]
                    y = yr[ev]
                    dv, ho = y <= DEV_END, y >= HO_FIRST
                    a, b = st(usd[dv]), st(usd[ho])
                    yrs_pos = sum(usd[ho & (y == k)].sum() > 0 for k in range(HO_FIRST, 2027))
                    rows.append(dict(tf=tf, entry=ENTRIES[et], filter="with HTF" if flt else "none",
                                     stop=STOPS[sm], exit=EXITS[xm], et=et, flt=flt, sm=sm, xm=xm,
                                     dev_n=a["n"], dev_mean=a["mean"], dev_t=a["t"], dev_pf=a["pf"],
                                     dev_win=a["win"], dev_R=rr[dv].mean() if dv.any() else np.nan,
                                     dev_total=a["total"], ho_n=b["n"], ho_mean=b["mean"], ho_t=b["t"],
                                     ho_pf=b["pf"], ho_win=b["win"], ho_R=rr[ho].mean() if ho.any() else np.nan,
                                     ho_total=b["total"], ho_years_pos=yrs_pos,
                                     med_stop_usd=np.median(sim[2][ev]) * USD if len(ev) else np.nan))
    print(f"   done ({time.time() - t00:.0f} s)")
G = pd.DataFrame(rows)
G.to_csv(os.path.join(HERE, "grid.csv"), index=False)

# ------------------------------------------------------------------------------------------------- grid summary
print(f"\n=== ALL {len(G):,} STRATEGIES (8 entries x 4 timeframes x 2 filters x 5 stops x 9 exits) ===")
print(f"Made money on 2012-2019: {(G.dev_total > 0).sum():,} ({(G.dev_total > 0).mean() * 100:.1f} %);  "
      f"on 2020-2026: {(G.ho_total > 0).sum():,} ({(G.ho_total > 0).mean() * 100:.1f} %);  "
      f"on both: {((G.dev_total > 0) & (G.ho_total > 0)).sum():,}")
print(f"With t >= 2 on 2012-2019: {(G.dev_t >= 2).sum()};  t >= 3: {(G.dev_t >= 3).sum()};  "
      f"t <= -2: {(G.dev_t <= -2).sum()}")
ok2 = G.dev_n.ge(MIN_DEV) & G.ho_n.ge(30)
print(f"Does a good 2012-2019 result predict 2020-2026? correlation of t-stats across {ok2.sum():,} strategies: "
      f"{G[ok2].dev_t.corr(G[ok2].ho_t):+.2f}; of $ per trade: {G[ok2].dev_mean.corr(G[ok2].ho_mean):+.2f}")
top = G[ok2].nlargest(100, "dev_t")
print(f"The 100 best on 2012-2019 (mean t {top.dev_t.mean():+.2f}) had on 2020-2026: mean t {top.ho_t.mean():+.2f}, "
      f"{(top.ho_total > 0).mean() * 100:.0f} % made money")

print("\nNet result per trade in R by target (all timeframes, medium structure stop, no filter, 2012-2026):")
hdr = "  " + f"{'entry':16s}" + "".join(f"{e:>13s}" for e in EXITS)
print(hdr)
for et in range(8):
    cells = []
    for xm in range(9):
        q = G[(G.et == et) & (G.sm == 1) & (G.flt == 0) & (G.xm == xm)]
        n = q.dev_n + q.ho_n
        r = ((q.dev_R * q.dev_n).fillna(0) + (q.ho_R * q.ho_n).fillna(0)).sum() / n.sum()
        w = ((q.dev_win * q.dev_n).fillna(0) + (q.ho_win * q.ho_n).fillna(0)).sum() / n.sum()
        cells.append(f"{r:+6.3f} ({w * 100:2.0f}%)")
    print("  " + f"{ENTRIES[et]:16s}" + "".join(f"{c:>13s}" for c in cells))
print("  (cell = mean net R per trade, with the win rate in brackets)")

print("\nBefore costs vs after, by timeframe (medium structure stop, no filter, 8 entries pooled, 2012-2026):")
print("  " + f"{'':4s}" + "".join(f"{e:>15s}" for e in EXITS))
for tf in TFS:
    P = gold.prepare(tf)
    inwin = (P["fi"] >= 0) & (gold.idx[np.minimum(P["fi"], gold.N - 1)] <= HO_LAST)
    cells = []
    for xm in range(9):
        sg, sn = gold.run(P, 1, xm, cost=0.0, slip=0.0), gold.run(P, 1, xm)
        rg, rn = [], []
        for et in range(8):
            m = (P["et"] == et) & inwin
            eg, en = gold.trades(P, sg, m), gold.trades(P, sn, m)
            rg.append(sg[1][eg] / sg[2][eg]); rn.append(sn[1][en] / sn[2][en])
        cells.append(f"{np.concatenate(rg).mean():+.3f}/{np.concatenate(rn).mean():+.3f}")
    print("  " + f"{tf:4s}" + "".join(f"{c:>15s}" for c in cells))
print("  (cell = mean R per trade before costs / after costs)")

# ------------------------------------------------------------------------------------------------- finalists
cand = G[G.dev_n >= MIN_DEV].copy()
best = cand.loc[cand.groupby(["tf", "et", "flt"]).dev_t.idxmax()].sort_values("dev_t", ascending=False)
best = best[best.dev_t > 0]
F = best.head(NFINAL).reset_index(drop=True)
print(f"\n=== FINALISTS: the best stop + exit per entry set on 2012-2019 (>= {MIN_DEV} trades), top {NFINAL} sets ===")
print(f"Entry sets with any stop + exit at t > 0: {len(best)} of 64")
for k, r in F.iterrows():
    print(f"  F{k + 1:<2d} {r.tf:3s} {r.entry:16s} {r['filter']:8s} | {r.stop:19s} {r.exit:12s} | 2012-19: "
          f"{r.dev_n:5.0f} trades, ${r.dev_mean:+7.2f}/trade, t {r.dev_t:+5.2f}, PF {r.dev_pf:4.2f}, win "
          f"{r.dev_win * 100:3.0f} %")

print("\n=== JUDGED ONCE ON 2020 -> 2026-09-24 ===")
ftr, frow = [], []
for k, r in F.iterrows():
    tf, et, flt, sm, xm = r.tf, int(r.et), int(r.flt), int(r.sm), int(r.xm)
    P = gold.prepare(tf)
    ok = gold.htf_ok(tf, P)
    when = gold.idx[np.minimum(P["fi"], gold.N - 1)]
    inwin = (P["fi"] >= 0) & (when <= HO_LAST)
    mask = (P["et"] == et) & inwin & (ok if flt else True)
    sim = gold.run(P, sm, xm)
    ev = gold.trades(P, sim, mask)
    y = gold.year[P["fi"][ev]]
    ho = y >= HO_FIRST
    usd = sim[1][ev] * USD
    s_ho = st(usd[ho])
    # placebo: same trades re-entered at random times (same month + time slot), same direction, stop distance, exit
    pm = gold.placebo_means(P, ev[ho], sim, xm, COPIES, seed=1000 + k) * USD
    beat = 100 * np.mean(pm < s_ho["mean"])
    # double cost
    sim2 = gold.run(P, sm, xm, cost=2 * gold.cost, slip=2 * gold.slip)
    ev2 = gold.trades(P, sim2, mask)
    y2 = gold.year[P["fi"][ev2]]
    s2 = st(sim2[1][ev2][y2 >= HO_FIRST] * USD)
    per_year = {yy: usd[ho & (y == yy)].sum() for yy in range(HO_FIRST, 2027)}
    ypos = sum(v > 0 for v in per_year.values())
    passed = (s_ho["mean"] > 0 and s_ho["t"] >= T_PASS) and beat >= 95 and ypos >= 5 and s2["mean"] > 0
    yrs_span = (gold.idx[P["fi"][ev[ho]][-1]] - gold.idx[P["fi"][ev[ho]][0]]).days / 365.25 if ho.sum() > 1 else np.nan
    print(f"F{k + 1:<2d} {tf} {ENTRIES[et]} ({r['filter']}) | {STOPS[sm]}, {EXITS[xm]}")
    print(f"     {s_ho['n']} trades, win {s_ho['win'] * 100:.0f} %, ${s_ho['mean']:+.2f}/trade, t {s_ho['t']:+.2f}, "
          f"PF {s_ho['pf']:.2f}, total ${s_ho['total']:+,.0f} (${s_ho['total'] / yrs_span:+,.0f}/yr at 1 MGC), "
          f"max drawdown ${maxdd(usd[ho]):,.0f}, median stop ${np.median(sim[2][ev[ho]]) * USD:,.0f}")
    print(f"     placebo (random timing, same stop/target): mean ${pm.mean():+.2f}/trade; real beats {beat:.0f} % "
          f"of {COPIES} copies | double cost: ${s2['mean']:+.2f}/trade")
    print("     by year: " + "  ".join(f"{yy}: ${v:+,.0f}" for yy, v in per_year.items()) + f"  -> {ypos}/7 positive")
    print(f"     VERDICT: {'PASSES this test' if passed else 'DOES NOT PASS'}")
    frow.append(dict(final=f"F{k + 1}", tf=tf, entry=ENTRIES[et], filter=r['filter'], stop=STOPS[sm], exit=EXITS[xm],
                     dev_n=r.dev_n, dev_mean=r.dev_mean, dev_t=r.dev_t, ho_n=s_ho["n"], ho_mean=s_ho["mean"],
                     ho_t=s_ho["t"], ho_pf=s_ho["pf"], ho_win=s_ho["win"], ho_total=s_ho["total"],
                     placebo_mean=pm.mean(), beats_placebo_pct=beat, double_cost_mean=s2["mean"], years_pos=ypos,
                     passed=passed))
    for e in ev:
        i, x = P["fi"][e], sim[0][e]
        ftr.append(dict(final=f"F{k + 1}", entry_time=gold.idx[i], side="BUY" if P["ed"][e] == 1 else "SELL",
                        entry=P["fp"][e], stop_pts=sim[2][e], exit_time=gold.idx[x], net_usd=sim[1][e] * USD))
pd.DataFrame(frow).to_csv(os.path.join(HERE, "finalists.csv"), index=False)
pd.DataFrame(ftr).to_csv(os.path.join(HERE, "finalist_trades.csv"), index=False)
FR = pd.DataFrame(frow)
print(f"\nVERDICT: {int(FR.passed.sum())} of {len(FR)} finalists pass. "
      f"Finalists that made money on 2020-2026: {(FR.ho_total > 0).sum()} of {len(FR)}.")

# ------------------------------------------------------------------------------------------------- unseen GC weeks
print("\n=== UNSEEN: GC futures 5 m, trades entered 2026-09-25 -> 2026-11-08 (information only) ===")
gc = Market("GC 5m", *load_csv_et(GC, start="2025-06-01"), tick=0.1, cost=0.3, slip=0.2, minstop=0.3)
print(f"GC bars {gc.idx[0]} -> {gc.idx[-1]} ({gc.N:,})")
for k, r in F.iterrows():
    tf, et, flt, sm, xm = r.tf, int(r.et), int(r.flt), int(r.sm), int(r.xm)
    P = gc.prepare(tf)
    ok = gc.htf_ok(tf, P)
    when = gc.idx[np.minimum(P["fi"], gc.N - 1)]
    mask = (P["et"] == et) & (P["fi"] >= 0) & (when >= pd.Timestamp("2026-09-25")) & (ok if flt else True)
    sim = gc.run(P, sm, xm)
    ev = gc.trades(P, sim, mask)
    usd = sim[1][ev] * USD
    print(f"  F{k + 1:<2d} {tf:3s} {ENTRIES[et]:16s}: {len(ev):3d} trades, won {np.mean(usd > 0) * 100 if len(ev) else 0:3.0f} %,"
          f" net ${usd.sum():+,.0f}")
print(f"\nRun time {time.time() - t00:.0f} s")
