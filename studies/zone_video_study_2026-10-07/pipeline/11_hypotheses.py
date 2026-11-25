"""Stage 11: the FROZEN hypothesis set. Definitions were written from DISCOVERY (V1+V2) results only and are not
edited after VALIDATION (V3) is opened. Each hypothesis = (subset of interactions, condition, metric, claim).

usage: 11_hypotheses.py <build_dir> <out_dir> [DISCOVERY|VALIDATION|EXTERNAL|ALL]
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

B = Path(sys.argv[1]); OUT = Path(sys.argv[2]); SPLIT = sys.argv[3] if len(sys.argv) > 3 else "DISCOVERY"
ev = pd.read_pickle(B / "events.pkl")
ev["split"] = np.where(ev.video.isin([1, 2]), "DISCOVERY", np.where(ev.video == 3, "VALIDATION", "EXTERNAL"))
ev.loc[(ev.split == "VALIDATION") & (ev.shown_in_multiple_videos == 1), "split"] = "OVERLAP_DROPPED"
cen = json.loads((OUT / "analysis" / "frozen.json").read_text())["centroids"]
P = [f"p{k}" for k in range(11)] + ["p_ext"]
C = np.array([cen[k] for k in sorted(cen)])
ev["state"] = [sorted(cen)[j] for j in ((ev[P].clip(-6, 12).to_numpy()[:, None, :] - C[None]) ** 2).sum(2).argmin(1)]
ev["session"] = ev.hour_ny.map(lambda h: "ASIA" if (h >= 18 or h < 2) else "LONDON" if h < 8 else "NY_AM" if h < 12 else "NY_PM")
A, F = ev.interaction == "ARRIVAL", ev.interaction == "FLIP"

# name: (description, population mask, condition mask, metric, claim, kind)
#   metric: R1 | BRK | tr2_R | c1_R1 ; claim: '>' or '<' vs population base (or 'null': |diff| < 0.04)
H = {
 "H01": ("Break-continuation: after arrival, a 15m close beyond the FAR edge on the next bar -> zone direction fails "
         "(measured from that close)", A, ev.c1_closed_beyond == 1, "c1_R1", "<", "entry"),
 "H02": ("Old-zone flip with 4H trend: FLIP retest of a zone older than 810 15m bars (~8.4 days) in the 4H EMA trend "
         "direction", F, (ev.age_bars > 810) & (ev.trend4_with == 1), "R1", ">", "entry"),
 "H03": ("Approach state B (price was hovering at/just inside the edge 10 bars earlier, short local push back in)",
         A, ev.state == "B", "R1", ">", "entry"),
 "H04": ("Long-travel arrival (state E or F: arrived from >= ~3.5 ATR away within 10 bars) -> more zone failure",
         A, ev.state.isin(["E", "F"]), "BRK", ">", "filter"),
 "H05": ("4H-pane zone whose STATION score at birth was exactly 3 -> edge limit trade (1R stop beyond far edge, 2R) "
         "is profitable", A & (ev.universe == "Z4"), ev.score_birth == 3, "tr2_R", ">", "entry"),
 "H06": ("NY AM arrivals (08:00-11:59 NY) -> more zone failure", A, ev.session == "NY_AM", "BRK", ">", "filter"),
 "H07": ("NY PM arrivals (12:00-17:59 NY) -> higher reaction rate", A, ev.session == "NY_PM", "R1", ">", "entry"),
 "H08": ("Thin zones (height <= 1.3 ATR) -> zone failure", A, ev.height_atr <= 1.3, "BRK", ">", "filter"),
 "H09": ("Hot approach (mean range of the 3 bars before arrival > 1.14 ATR) -> lower reaction rate", A,
         ev.rng_last3_atr > 1.14, "R1", "<", "filter"),
 "H10": ("Crowded + blocked: <= 0.27 ATR of room to the next opposing zone AND >= 2 overlapping same-direction "
         "zones -> reaction fails", A, (ev.room_atr <= 0.27) & (ev.n_overlap_same >= 2), "R1", "<", "filter"),
 "H11": ("Deep arrival (wick passes the zone midpoint) -> zone failure (known at the arrival bar close)", A,
         ev.passed_mid == 1, "BRK", ">", "filter"),
 "H12": ("Rejection candle is NOT informative: arrival bar closes back outside the near edge -> R1 from the close "
         "equals base (+-4 pts)", A, ev.close_loc == "OUTSIDE_NEAR", "R1", "null", "null"),
 "H13": ("Waiting does not help: 'closed back outside AND no far-edge close' by bar 2 -> R1 from bar 2 equals base",
         A, (ev.c2_close_out == 1) & (ev.c2_closed_beyond == 0), "c2_R1", "null", "null"),
 "H14": ("4H-pane FVG (not OB) arrivals -> edge trade loses", A & (ev.universe == "Z4"), ev.zone_kind == "FVG",
         "tr2_R", "<", "filter"),
 "H15": ("Large zones (height > 2.4 ATR) rarely fail", A, ev.height_atr > 2.4, "BRK", "<", "filter"),
}


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); r = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def evaluate(split):
    rows = []
    for hid, (desc, pop, cond, metric, claim, kind) in H.items():
        m = (ev.split == split) if split != "ALL" else ev.split.isin(["DISCOVERY", "VALIDATION"])
        Pp = ev[pop & m & ev[metric].notna()]; S = Pp[cond[Pp.index]]; R = Pp[~cond[Pp.index]]
        n = len(S); base = Pp[metric].mean(); rate = S[metric].mean() if n else np.nan
        if metric.endswith("_R"):
            se = S[metric].std(ddof=1) / np.sqrt(n) if n > 1 else np.nan; lo, hi = rate - 1.96 * se, rate + 1.96 * se
            rest = R[metric].mean()
        else:
            lo, hi = wilson(S[metric].sum(), n); rest = R[metric].mean()
        diff = rate - rest
        if claim == ">": ok = lo > rest
        elif claim == "<": ok = hi < rest
        else: ok = abs(rate - base) < 0.04
        same_sign = (claim == ">" and diff > 0) or (claim == "<" and diff < 0) or (claim == "null" and abs(rate - base) < 0.04)
        rows.append(dict(split=split, hid=hid, kind=kind, metric=metric, claim=claim, n=n, uniq_bars=S.bar.nunique(),
                         days=S.time_utc.dt.date.nunique(), rate=rate, ci_lo=lo, ci_hi=hi, rest=rest, base=base,
                         diff_vs_rest=diff, same_sign=same_sign, ci_excludes_rest=ok,
                         mfe_mean=S.mfe20.mean(), mae_mean=S.mae20.mean(), mfe_med=S.mfe20.median(), mae_med=S.mae20.median(),
                         desc=desc))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    res = pd.concat([evaluate(s) for s in (["DISCOVERY", "VALIDATION", "EXTERNAL"] if SPLIT == "ALL3" else [SPLIT])])
    res.to_csv(OUT / "analysis" / f"hypotheses_{SPLIT}.csv", index=False)
    pd.set_option("display.width", 250)
    print(res[["split", "hid", "metric", "claim", "n", "rate", "ci_lo", "ci_hi", "rest", "diff_vs_rest", "same_sign",
               "ci_excludes_rest"]].round(3).to_string())
