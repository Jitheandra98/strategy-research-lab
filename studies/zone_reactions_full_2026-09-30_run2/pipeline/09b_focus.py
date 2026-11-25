"""Stage 9b — stress the only consistent lead (4H zones), and score the indicator's REFLEX contract.

A. 4H-zone touch trades: breakdowns (exit mix, risk size, long/short, month, cost x2, late entry,
   top-5% trimmed, clean-bar-only events) for 4h:FVG, 4h:OB, 5m:4H and the de-duplicated union.
B. What separates 4H zone holds from breaks (feature effects, first arrivals).
C. Indicator REFLEX contract replayed on its own trigger events (first touch, station score >= 3):
   next-bar open, target +1 ATR, stop far edge -/+ 0.5 ATR, 8-bar clock, stop checked first.
Writes OUT/analysis/focus_4h.csv, focus_4h_months.csv, focus_4h_features.csv, reflex_compare.csv
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
A = OUT / "analysis"
sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module
an = import_module("09_analysis".replace("09_analysis", "09_analysis"))  # noqa (for boot_mean/wilson)


def boot(x, d):
    return an.boot_mean(np.asarray(x, float), np.asarray(d).astype(str))


ev = pd.read_csv(OUT / "events.csv")
ev["time_ct"] = pd.to_datetime(ev.time_ct, utc=True).dt.tz_convert("America/Chicago")
ev["day"] = ev.time_ct.dt.date
days = np.sort(ev.day.unique())
cut = days[int(len(days) * 0.6)]
ev["split"] = np.where(ev.day < cut, "DEV", "HOLDOUT")
ev["family"] = ev.zone_tf + ":" + ev.zone_kind
bars = pd.read_csv(OUT / "data" / "bars_5m.csv")
lab = bars.label_only.to_numpy()
# an event is "clean" if no label-covered bar within [i-2, i+24]
ev["clean"] = [not lab[max(0, i - 2):i + 25].any() for i in ev.i]
tr = pd.read_csv(OUT / "data" / "confirmation_trades.csv")
tr = tr.merge(ev[["zone_uid", "i", "family", "split", "day", "trend4_aligned", "trend5_aligned", "in_4h_same",
                  "arrival_no", "clean", "time_ct", "zone_tf"]].rename(columns={"i": "event_i"}),
              on=["zone_uid", "event_i"], how="left")
tr["month"] = tr.time_ct.dt.strftime("%Y-%m")

rows, mrows = [], []
fams = {"4h:FVG": tr.family == "4h:FVG", "4h:OB": tr.family == "4h:OB", "5m:4H": tr.family == "5m:4H",
        "4H_ANY": (tr.zone_tf == "4h") | (tr.family == "5m:4H")}
filts = {"none": lambda t: np.ones(len(t), bool), "trend4_aligned": lambda t: t.trend4_aligned == True,
         "trend4_against": lambda t: t.trend4_aligned == False, "first_arrival": lambda t: t.arrival_no == 1}
for fam, fm in fams.items():
    for fn, ff in filts.items():
        base = tr[fm]
        base = base[ff(base)]
        for conf in ["C0_TOUCH", "C1_RECLAIM", "C3_CHOCH", "C7_FVG", "K1_FLIP_RETEST"]:
            for R in (1, 2, 3):
                col = f"r{R}"
                g = base[base.conf == conf].dropna(subset=[col]).drop_duplicates(["entry_i", "tdir", "conf"])
                if len(g) < 20:
                    continue
                for sp in ["DEV", "HOLDOUT", "ALL", "ALL_CLEAN"]:
                    x = g if sp == "ALL" else g[g.clean == True] if sp == "ALL_CLEAN" else g[g.split == sp]
                    if len(x) < 10:
                        continue
                    lo, hi = boot(x[col], x.day)
                    q95 = x[col].quantile(.95)
                    rows.append(dict(family=fam, filter=fn, conf=conf, R=R, split=sp, n=len(x), win=(x[col] > 0).mean(),
                                     exp_R=x[col].mean(), lo=lo, hi=hi,
                                     exp_cost2x=(x[col] - 0.3 / x.risk_pts).mean(),
                                     exp_late=(x.r2_late.mean() if R == 2 else np.nan),
                                     exp_trim5=x[x[col] < q95][col].mean(),
                                     long_n=int((x.tdir == 1).sum()), long_exp=x[x.tdir == 1][col].mean(),
                                     short_n=int((x.tdir == -1).sum()), short_exp=x[x.tdir == -1][col].mean(),
                                     time_exit=(x[f"exit{R}"] == "TIME").mean(), med_bars=x[f"bars{R}"].median(),
                                     med_risk_pts=x.risk_pts.median(), med_risk_atr=x.risk_atr.median()))
                if fn in ("none", "trend4_aligned") and conf == "C0_TOUCH" and R == 2:
                    for mth, x in g.groupby("month"):
                        mrows.append(dict(family=fam, filter=fn, month=mth, n=len(x), exp_R=x[col].mean(), sum_R=x[col].sum()))
fo = pd.DataFrame(rows)
fo.to_csv(A / "focus_4h.csv", index=False)
pd.DataFrame(mrows).to_csv(A / "focus_4h_months.csv", index=False)

# B — 4H zone holds vs breaks
ev["held"] = ev.reaction.isin(["REJECT", "SWEEP_RECLAIM"])
e4 = ev[(ev.zone_tf == "4h") | (ev.family == "5m:4H")]
feats = {"first_arrival": e4.arrival_no == 1, "trend4_aligned": e4.trend4_aligned == True,
         "trend5_aligned": e4.trend5_aligned == True, "closed_outside_on_touch": e4.closed_outside == True,
         "fast_approach_ge2atr": e4.approach_atr >= 2, "impulse_touch_ge1_5atr": e4.touch_range_atr >= 1.5,
         "hi_vol": e4.vol_regime == "HI", "zone_ge3atr5": e4.size_atr5 >= 3, "young_le48": e4.age_bars <= 48,
         "old_gt576": e4.age_bars > 576, "session_NY": e4.session == "NY", "session_ASIA": e4.session == "ASIA",
         "session_LONDON": e4.session == "LONDON"}
frows = []
for fn, m in feats.items():
    for sp in ["DEV", "HOLDOUT", "ALL"]:
        s = e4 if sp == "ALL" else e4[e4.split == sp]
        mm = m.loc[s.index]
        a, b_ = s[mm], s[~mm]
        if len(a) < 15 or len(b_) < 15:
            continue
        frows.append(dict(feature=fn, split=sp, n_with=len(a), n_without=len(b_), hold_with=a.held.mean(),
                          hold_without=b_.held.mean(), ret24_with=a.ret24_atr.mean(), ret24_without=b_.ret24_atr.mean()))
pd.DataFrame(frows).to_csv(A / "focus_4h_features.csv", index=False)

# C — indicator REFLEX contract on its own triggers
o, h, l, c = (bars[k].to_numpy(float) for k in ["open", "high", "low", "close"])
atr = bars.atr5.to_numpy(float)
seg = bars.segment.to_numpy()
rr = []
for e in ev[ev.ind_reflex_signal == True].itertuples():
    j = e.i + 1
    if j + 9 >= len(c) or seg[j + 9] != seg[e.i]:
        continue
    d = e.dir
    far = e.bot if d == 1 else e.top
    stop = far - 0.5 * atr[j] if d == 1 else far + 0.5 * atr[j]   # source uses ATR of the fill bar (lookahead)
    ent = o[j]
    tgt = ent + d * atr[j]
    risk = (ent - stop) * d
    if risk < 0.2 * atr[j]:          # the indicator's own MIN_RISK_ATR sanity filter
        continue
    res = None
    for k in range(j, j + 9):
        if (l[k] <= stop) if d == 1 else (h[k] >= stop):
            res = (stop - ent) * d
            break
        if (h[k] >= tgt) if d == 1 else (l[k] <= tgt):
            res = (tgt - ent) * d
            break
    if res is None:
        res = (c[j + 8] - ent) * d
    rr.append(dict(day=e.day, split=e.split, family=e.family, R=(res - 0.3) / risk, win=res > 0, risk_atr=risk / atr[j]))
rf = pd.DataFrame(rr)
out = []
for sp in ["DEV", "HOLDOUT", "ALL"]:
    x = rf if sp == "ALL" else rf[rf.split == sp]
    lo, hi = boot(x.R, x.day)
    out.append(dict(split=sp, n=len(x), win=x.win.mean(), exp_R=x.R.mean(), lo=lo, hi=hi, med_R=x.R.median(),
                    med_risk_atr=x.risk_atr.median(), avg_win_R=x[x.R > 0].R.mean(), avg_loss_R=x[x.R <= 0].R.mean()))
pd.DataFrame(out).to_csv(A / "reflex_compare.csv", index=False)
print(pd.DataFrame(out).round(3).to_string())
pd.set_option("display.width", 250)
cols = ["family", "filter", "conf", "R", "split", "n", "win", "exp_R", "lo", "hi", "exp_cost2x", "exp_late", "exp_trim5",
        "long_n", "long_exp", "short_n", "short_exp", "time_exit", "med_bars", "med_risk_pts", "med_risk_atr"]
sel = fo[(fo.conf == "C0_TOUCH") & (fo.R == 2)]
print(sel[cols].round(3).to_string())

# D — sensitivity: drop arrivals that happen right after a zone becomes available (the window where
#     chart drawings — box borders/text — sit on top of candles and could fake a touch)
sens = []
for label, fam_mask, min_age in (("4H_ANY trend4_aligned", fams["4H_ANY"] & (tr.trend4_aligned == True), 3),
                                 ("4H_ANY trend4_against", fams["4H_ANY"] & (tr.trend4_aligned == False), 3),
                                 ("5m zones", ~fams["4H_ANY"], 17)):
    base = tr[fam_mask & (tr.conf == "C0_TOUCH")].merge(ev[["zone_uid", "i", "age_bars"]].rename(columns={"i": "event_i"}),
                                                        on=["zone_uid", "event_i"])
    for keep_young in (True, False):
        g = base if keep_young else base[base.age_bars >= min_age]
        g = g.dropna(subset=["r2"]).drop_duplicates(["entry_i", "tdir"])
        for sp in ["DEV", "HOLDOUT", "ALL"]:
            x = g if sp == "ALL" else g[g.split == sp]
            lo, hi = boot(x.r2, x.day)
            sens.append(dict(set=label, young_included=keep_young, min_age=min_age, split=sp, n=len(x),
                             exp_R=x.r2.mean(), lo=lo, hi=hi))
pd.DataFrame(sens).to_csv(A / "sensitivity_young_arrivals.csv", index=False)
print(pd.DataFrame(sens).round(3).to_string())
