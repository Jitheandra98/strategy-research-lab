"""Stage 12: how many DISCOVERY single-feature effects replicate in VALIDATION (same cut-points, same sign)?
If the replication rate of 'significant-looking' discovery effects is ~50%, the screen found noise."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
B = Path(sys.argv[1]); OUT = Path(sys.argv[2]); A = OUT / "analysis"
ev = pd.read_pickle(B / "events.pkl")
ev["session"] = ev.hour_ny.map(lambda h: "ASIA" if (h >= 18 or h < 2) else "LONDON" if h < 8 else "NY_AM" if h < 12 else "NY_PM")
V = ev[ev.video == 3]
G = {"ALL_ARRIVAL": V.interaction == "ARRIVAL", "ALL_FLIP": V.interaction == "FLIP",
     "Z15_ARRIVAL": (V.universe == "Z15") & (V.interaction == "ARRIVAL"), "Z4_ARRIVAL": (V.universe == "Z4") & (V.interaction == "ARRIVAL"),
     "Z15_FLIP": (V.universe == "Z15") & (V.interaction == "FLIP"), "Z4_FLIP": (V.universe == "Z4") & (V.interaction == "FLIP")}
out = []
for tgt in ["R1", "BRK", "tr2_R"]:
    S = pd.read_csv(A / f"screen_single_{tgt}.csv")
    S = S[S.n >= 50].sort_values("z", key=abs, ascending=False)
    for _, r in S.iterrows():
        g = V[G[r.group]]; y = g[tgt]
        if r.kind == "num": m = (g[r.feature] > r.lo) & (g[r.feature] <= r.hi)
        else:
            lv = r.level
            try: lv = float(lv)
            except (TypeError, ValueError): pass
            m = g[r.feature] == lv
        a, b = y[m].dropna(), y[~m].dropna()
        if len(a) < 30: continue
        d = a.mean() - b.mean(); se = np.sqrt(a.var() / len(a) + b.var() / len(b))
        out.append(dict(target=tgt, group=r.group, cond=r.cond, disc_z=r.z, disc_q=r.q_BH, disc_lift=r.rate - r.base,
                        val_n=len(a), val_diff=d, val_z=d / se, same_sign=np.sign(d) == np.sign(r.z)))
R = pd.DataFrame(out); R.to_csv(A / "replication.csv", index=False)
for tgt, g in R.groupby("target"):
    for lab, gg in (("all", g), ("|disc z|>2.5", g[g.disc_z.abs() > 2.5]), ("disc q<0.10", g[g.disc_q < 0.10])):
        if len(gg): print(tgt, lab, "n=%d same-sign=%.0f%% val|z|>2 same-sign=%.0f%%" % (len(gg), 100 * gg.same_sign.mean(), 100 * ((gg.val_z.abs() > 2) & gg.same_sign).mean()))
