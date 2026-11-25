"""Stage 11 — report figures (PNG) from analysis tables."""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
A, F = OUT / "analysis", OUT / "figures"
F.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .25, "figure.dpi": 130})
COL = {"REJECT": "#2e7d32", "SWEEP_RECLAIM": "#81c784", "CHOP": "#bdbdbd", "BREAK_RETEST": "#ef9a9a",
       "BREAK": "#c62828"}

# 1 reaction mix, first arrival, by family
rr = pd.read_csv(A / "reaction_rates.csv")
r1 = rr[rr.arrival_no == 1].pivot_table(index="family", columns="reaction", values="rate")
n1 = rr[rr.arrival_no == 1].groupby("family").n.first()
order = ["REJECT", "SWEEP_RECLAIM", "CHOP", "BREAK_RETEST", "BREAK"]
r1 = r1[[c for c in order if c in r1]].loc[n1.sort_values(ascending=False).index]
fig, ax = plt.subplots(figsize=(8, 3.2))
left = np.zeros(len(r1))
for c in r1.columns:
    ax.barh([f"{f}  (n={n1[f]})" for f in r1.index], r1[c], left=left, color=COL[c], label=c)
    left += r1[c].fillna(0).to_numpy()
ax.set_xlim(0, 1)
ax.set_xlabel("share of first arrivals")
ax.legend(ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(.5, 1.18), frameon=False)
ax.set_title("What price does at the first arrival into a zone (24 bars = 2 h)", pad=28, fontsize=11)
fig.tight_layout()
fig.savefig(F / "reaction_mix.png")

# 2 confirmation expectancy DEV vs HOLDOUT (family ALL & 4H_ANY, filter none, 2R)
cr = pd.read_csv(A / "confirmation_results.csv")
for fam in ["ALL", "4H_ANY", "5m:FVG", "5m:OB"]:
    sub = cr[(cr.family == fam) & (cr["filter"] == "none") & (cr.R == 2) & (cr.split.isin(["DEV", "HOLDOUT"]))]
    if sub.empty:
        continue
    confs = sorted(sub.conf.unique())
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for k, sp in enumerate(["DEV", "HOLDOUT"]):
        s = sub[sub.split == sp].set_index("conf").reindex(confs)
        x = np.arange(len(confs)) + (k - .5) * .35
        ax.bar(x, s.exp_R, width=.33, color=["#546e7a", "#ff8f00"][k], label=sp)
        ax.errorbar(x, s.exp_R, yerr=[s.exp_R - s.exp_lo, s.exp_hi - s.exp_R], fmt="none", ecolor="k", lw=.8)
        for xi, nn in zip(x, s.n):
            if not np.isnan(nn):
                ax.text(xi, ax.get_ylim()[0] if False else 0, f"{int(nn)}", ha="center", va="top", fontsize=6)
    ax.axhline(0, color="k", lw=.8)
    ax.set_xticks(np.arange(len(confs)))
    ax.set_xticklabels(confs, rotation=20, fontsize=8)
    ax.set_ylabel("mean R per trade (2R target)")
    ax.set_title(f"5m confirmation after arrival — zones: {fam}  (95% day-block CI; n under bars)", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(F / f"confirmations_{fam.replace(':', '_')}.png")

# 3 session hold rate
sb = pd.read_csv(A / "session_bias.csv")
fig, ax = plt.subplots(figsize=(5, 2.6))
ax.bar(sb.session, sb.hold, color="#546e7a")
for i, (h, n) in enumerate(zip(sb.hold, sb.n)):
    ax.text(i, h + .01, f"n={n}", ha="center", fontsize=8)
ax.set_ylabel("held share")
ax.set_ylim(0, 1)
ax.set_title("Zone holds by session (all arrivals)", fontsize=10)
fig.tight_layout()
fig.savefig(F / "session_hold.png")
print("figures written to", F)
