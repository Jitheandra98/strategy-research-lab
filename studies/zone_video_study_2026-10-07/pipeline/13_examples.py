"""Stage 13: example and counter-example events per hypothesis, chosen by a seeded random draw (not hand-picked),
with the video file + timestamp where the arrival bar first appears, so each one can be checked by eye.
Writes <out>/analysis/examples.csv"""
import sys, importlib.util
from pathlib import Path
import numpy as np, pandas as pd

B = Path(sys.argv[1]); OUT = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("h", Path(__file__).parent / "11_hypotheses.py")
sys.argv = [sys.argv[0], str(B), str(OUT), "DISCOVERY"]
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
ev, H = h.ev, h.H


def hms(s):
    s = int(round(s)); return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


rows = []
rng = np.random.default_rng(2026)
for hid, (desc, pop, cond, metric, claim, kind) in H.items():
    S = ev[pop & cond & ev[metric].notna() & ev.video.notna() & ev.video_t_reveal.notna()]
    if claim == ">": good = S[metric] > (0 if metric.endswith("_R") else 0.5)
    elif claim == "<": good = S[metric] < (0 if metric.endswith("_R") else 0.5)
    else: good = pd.Series(True, index=S.index)
    for lab, sub in (("EXAMPLE", S[good]), ("COUNTEREXAMPLE", S[~good])):
        for split, vids in (("DISCOVERY", [1, 2]), ("VALIDATION", [3])):
            ss = sub[sub.video.isin(vids)]
            if not len(ss): continue
            pick = ss.iloc[rng.choice(len(ss), min(3, len(ss)), replace=False)]
            for _, r in pick.iterrows():
                rows.append(dict(hid=hid, type=lab, split=split, video=f"V{int(r.video)}", video_ts=hms(r.video_t_reveal),
                                 chart_time_ny=r.time_ny.strftime("%Y-%m-%d %H:%M"), zone=r.zone_id, kind=r.zone_kind,
                                 side="demand" if r.zone_dir == 1 else "supply", interaction=r.interaction,
                                 zone_range=f"{r.bot:.2f}-{r.top:.2f}", metric=metric, value=round(float(r[metric]), 3),
                                 archetype=r.archetype, mfe20_atr=round(r.mfe20, 2), mae20_atr=round(r.mae20, 2)))
E = pd.DataFrame(rows); E.to_csv(OUT / "analysis" / "examples.csv", index=False)
print(E.groupby(["hid", "type"]).size().unstack())
