"""Bias check: catalog results BEFORE costs. If the simulator were biased, gross R would sit clearly below zero.
Run after catalog.py: python3 gross_check.py > gross_check.txt"""
import glob
import numpy as np, pandas as pd
from common import pf

rows = []
for f in sorted(glob.glob("trades/*.csv")):
    T = pd.read_csv(f); g = T.gross.to_numpy(); r = g / T.R.to_numpy(); m = T.year.to_numpy() >= 2024
    rows.append(dict(setup=f[7:9], n=len(T), gross_PF=pf(g), gross_R=r.mean(), gross_PF_24_26=pf(g[m]),
                     med_stop_pt=np.median(T.R), cost_share=0.3 / np.median(T.R)))
R = pd.DataFrame(rows).set_index("setup")
pd.set_option("display.width", 200)
print(R.round(3).to_string())
print(f"\ngross PF > 1 (before any cost): {(R.gross_PF > 1).sum()} of {len(R)} | mean gross R per trade: {R.gross_R.mean():+.3f}")
print(f"median stop across setups: {R.med_stop_pt.median():.2f} pt = ${R.med_stop_pt.median() * 10:.0f} on 1 MGC; "
      f"0.3 pt cost = {0.3 / R.med_stop_pt.median():.0%} of that risk")
