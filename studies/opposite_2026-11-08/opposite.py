"""Owner's idea (2026-11-08): "everything we test loses money - do the opposite."
For every rule tested on 2026-11-07/08 we take its exact trades and flip them: same entry, same exit, opposite side.
Opposite gross = -(original gross). Both sides still pay 0.3 pt per round trip.
This flip is GENEROUS to the opposite: in a bar that touched both the stop and the target, the original was charged the stop,
and the flip gets the mirror of that (a win). A strict re-simulation can only make the opposite worse.
Pass bar = the same one used all day (catalog_100_2026-11-08/common.py: evaluate). Run: python3 opposite.py > results.txt"""
import glob, os, sys
import numpy as np, pandas as pd

R = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/"
sys.path.insert(0, R + "catalog_100_2026-11-08")
os.chdir(R + "catalog_100_2026-11-08")
from common import evaluate                                   # same pass bar as every test today

rules = []                                                    # (name, DataFrame[gross, d, year])


def add(name, df, g="gross", d="d", y="year"):
    rules.append((name, pd.DataFrame({"gross": df[g].to_numpy(float), "d": df[d].to_numpy(int), "year": df[y].to_numpy(int)})))


A = R + "asia_sweep_theorem_2026-11-07/"
for f, tag in [("trades.csv", ""), ("trades_bias.csv", " +1H bias")]:
    T = pd.read_csv(A + f)
    for (v, tn), g in T.groupby(["v", "tn"]): add(f"11-07 theorem {v} -> {tn}{tag}", g, "pts", "d", "y")
T = pd.read_csv(A + "range_fade_trades.csv")
for m, g in T[T.regime == "RANGE"].groupby("m"): add(f"11-07 range-only sweep fade {m}R", g, "pts", "d", "y")
T = pd.read_csv(A + "exhaustion_trades.csv")
for (r_, m), g in T.groupby(["rule", "m"]): add(f"11-07 exhaustion {r_} {m}R", g, "pts", "d", "y")
T = pd.read_csv(A + "trend_pullback_trades.csv")
for m, g in T.groupby("m"): add(f"11-07 trend FVG pullback {m}R", g, "pts", "d", "y")
T = pd.read_csv(R + "replay_watch_2026-11-07/longtest/two_ideas_trades.csv")
for idea, g in T.groupby("idea"): add(f"11-07 {idea}", g, "pts", "d", "y")
add("11-08 NOISE BREAKOUT", pd.read_csv(R + "noise_breakout_2026-11-08/trades_main.csv"), "gross", "dir", "year")
add("11-08 SPIKE FOLLOW", pd.read_csv(R + "spike_follow_2026-11-08/trades_main.csv"))
add("11-08 18:00 range breakout (Chicago)", pd.read_csv("single_main_trades.csv"))
add("11-08 18:00 range breakout (fixed UTC-6)", pd.read_csv("single_alt_trades.csv"))
names = dict(l.split(None, 1) for l in open("catalog_results.txt") if l[:2].isdigit() and l[2] == " ")
for f in sorted(glob.glob("trades/*.csv")):
    k = os.path.basename(f)[:2]
    add(f"11-08 catalog #{k} {names.get(k, '').split('  ')[0].strip()}", pd.read_csv(f))

rows = []
for name, T in rules:
    o = evaluate(T)                                           # original
    F = T.assign(gross=-T.gross, d=-T.d)                      # flipped
    e = evaluate(F)
    rows.append(dict(rule=name, n=o["n"], orig_PF=o["PF"], orig_usd=o["usd"], gross_usd=T.gross.sum() * 10,
                     opp_PF=e["PF"], opp_usd=e["usd"], opp_PF_12_19=e["PF_12_19"], opp_PF_20_23=e["PF_20_23"],
                     opp_PF_24_26=e["PF_24_26"], opp_at_05=e["usd_at_05"], opp_yrs_pos=e["yrs_pos"], opp_PASS=e["PASS"]))
S = pd.DataFrame(rows).sort_values("opp_PF", ascending=False)
S.to_csv(R + "opposite_2026-11-08/opposite_scoreboard.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
fmt = {c: "{:,.2f}".format for c in S.columns if "PF" in c}
fmt.update({c: "{:+,.0f}".format for c in ["orig_usd", "gross_usd", "opp_usd", "opp_at_05"]})
print(S.to_string(index=False, formatters=fmt))
n = S.n.sum(); cost = n * 0.3 * 10
print(f"\n{len(S)} rules, {n:,} trades. Opposite passes the bar: {int(S.opp_PASS.sum())}. "
      f"Opposite profitable at all (0.3 pt): {(S.opp_usd > 0).sum()}. Original profitable: {(S.orig_usd > 0).sum()}.")
print(f"All rules together, 1 MGC per trade: before costs ${S.gross_usd.sum():+,.0f}; costs ${cost:,.0f} (paid by BOTH sides).")
print(f"  original after costs ${S.orig_usd.sum():+,.0f}   |   opposite after costs ${S.opp_usd.sum():+,.0f}")
