"""Stage 9 — quantify zone reactions and confirmation rules.

Split: first 60% of trading days = DEV (rules chosen here), last 40% = HOLDOUT (only confirms).
Uncertainty: Wilson intervals for rates; day-block bootstrap (2000 draws) for mean R.
Trades are de-duplicated per (entry bar, direction, confirmation, R) — overlapping zones that
produce the same order count once.
Writes OUT/analysis/*.csv and OUT/analysis/summary.json
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
A = OUT / "analysis"
A.mkdir(exist_ok=True)
rng = np.random.default_rng(7)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def boot_mean(x, days, n_boot=2000):
    x = np.asarray(x, float)
    ok = ~np.isnan(x)
    x, days = x[ok], np.asarray(days)[ok]
    if len(x) < 10:
        return (np.nan, np.nan)
    ud = np.unique(days)
    groups = {d: x[days == d] for d in ud}
    sums = np.array([groups[d].sum() for d in ud])
    cnts = np.array([len(groups[d]) for d in ud])
    idx = rng.integers(0, len(ud), size=(n_boot, len(ud)))
    means = sums[idx].sum(1) / cnts[idx].sum(1)
    return (float(np.quantile(means, .025)), float(np.quantile(means, .975)))


def main():
    ev = pd.read_csv(OUT / "events.csv", parse_dates=["time_ct"])
    ev["time_ct"] = pd.to_datetime(ev.time_ct, utc=True).dt.tz_convert("America/Chicago")
    ev["day"] = ev.time_ct.dt.date
    days = np.sort(ev.day.unique())
    cut = days[int(len(days) * 0.6)]
    ev["split"] = np.where(ev.day < cut, "DEV", "HOLDOUT")
    ev["family"] = ev.zone_tf + ":" + ev.zone_kind
    tr = pd.read_csv(OUT / "data" / "confirmation_trades.csv")
    tr = tr.drop(columns=["dir"], errors="ignore").merge(ev[["zone_uid", "i", "dir", "family", "split", "day", "session", "in_4h_same", "in_4h_opp",
                      "trend4_aligned", "trend5_aligned", "arrival_no", "size_atr5", "vol_regime", "zone_tf"]]
                  .rename(columns={"i": "event_i"}), on=["zone_uid", "event_i"], how="left")
    summary = {"split_cut_day": str(cut), "n_days": int(len(days)), "n_events": int(len(ev)),
               "date_range": [str(days[0]), str(days[-1])]}

    # 1 — reaction base rates by family × arrival
    rows = []
    for (fam, arr), g in ev.groupby(["family", "arrival_no"]):
        n = len(g)
        for r in ["REJECT", "SWEEP_RECLAIM", "BREAK", "BREAK_RETEST", "CHOP"]:
            k = int((g.reaction == r).sum())
            lo, hi = wilson(k, n)
            rows.append(dict(family=fam, arrival_no=arr, reaction=r, n=n, k=k, rate=k / n, lo=lo, hi=hi))
    rr = pd.DataFrame(rows)
    rr.to_csv(A / "reaction_rates.csv", index=False)

    # 2 — "held" = REJECT or SWEEP_RECLAIM ; feature effects on hold rate (DEV and HOLDOUT separately)
    ev["held"] = ev.reaction.isin(["REJECT", "SWEEP_RECLAIM"])
    feats = {
        "first_arrival": ev.arrival_no == 1,
        "trend5_aligned": ev.trend5_aligned == True,
        "trend4_aligned": ev.trend4_aligned == True,
        "in_4h_same": ev.in_4h_same == True,
        "in_4h_opp": ev.in_4h_opp == True,
        "big_zone_ge1atr": ev.size_atr5 >= 1,
        "closed_outside_on_touch": ev.closed_outside == True,
        "wick_reject_touch": (ev.close_pos >= 2 / 3) & (ev.zone_wick >= 0.5),
        "fast_approach_ge2atr": ev.approach_atr >= 2,
        "impulse_touch_bar_ge1_5atr": ev.touch_range_atr >= 1.5,
        "deep_touch_wick_past_mid": ev.pen_wick >= 0.5,
        "pool_swept_at_touch": ev.swept_pool_at_touch == True,
        "hi_vol_regime": ev.vol_regime == "HI",
        "young_zone_le12": ev.age_bars <= 12,
        "old_zone_gt288": ev.age_bars > 288,
    }
    frows = []
    for fam in ["5m:FVG", "5m:OB", "5m:4H", "4h:FVG", "4h:OB", "ALL"]:
        sub = ev if fam == "ALL" else ev[ev.family == fam]
        for fn, mask in feats.items():
            m = mask.loc[sub.index]
            for sp in ["DEV", "HOLDOUT"]:
                s = sub[sub.split == sp]
                mm = m.loc[s.index]
                a, b_ = s[mm], s[~mm]
                if len(a) < 20 or len(b_) < 20:
                    continue
                pa, pb = a.held.mean(), b_.held.mean()
                frows.append(dict(family=fam, feature=fn, split=sp, n_with=len(a), n_without=len(b_),
                                  hold_with=pa, hold_without=pb, diff=pa - pb,
                                  with_lo=wilson(a.held.sum(), len(a))[0], with_hi=wilson(a.held.sum(), len(a))[1],
                                  mfe12_with=a.mfe12_atr.mean(), mae12_with=a.mae12_atr.mean(),
                                  ret12_with=a.ret12_atr.mean(), ret12_without=b_.ret12_atr.mean()))
    fe = pd.DataFrame(frows)
    fe.to_csv(A / "feature_effects.csv", index=False)

    # 3 — confirmation trades
    tr = tr.dropna(subset=["family"])
    trows = []
    filters = {
        "none": lambda t: np.ones(len(t), bool),
        "in_4h_same": lambda t: t.in_4h_same == True,
        "not_in_4h_opp": lambda t: t.in_4h_opp != True,
        "trend4_aligned": lambda t: t.trend4_aligned == True,
        "trend5_aligned": lambda t: t.trend5_aligned == True,
        "first_arrival": lambda t: t.arrival_no == 1,
    }
    for fam in ["ALL", "5m:FVG", "5m:OB", "5m:4H", "4h:FVG", "4h:OB", "4H_ANY"]:
        if fam == "ALL":
            sub = tr
        elif fam == "4H_ANY":
            sub = tr[(tr.zone_tf == "4h") | (tr.family == "5m:4H")]
        else:
            sub = tr[tr.family == fam]
        for fname, ff in filters.items():
            s0 = sub[ff(sub)]
            for conf, g in s0.groupby("conf"):
                for R in (1, 2, 3):
                    col = f"r{R}"
                    gg = g.dropna(subset=[col]).drop_duplicates(["entry_i", "tdir", "conf"])
                    for sp in ["DEV", "HOLDOUT", "ALL"]:
                        x = gg if sp == "ALL" else gg[gg.split == sp]
                        if len(x) < 15:
                            continue
                        lo, hi = boot_mean(x[col].to_numpy(), x.day.astype(str).to_numpy())
                        w = x[col] > 0
                        trows.append(dict(family=fam, filter=fname, conf=conf, R=R, split=sp, n=len(x),
                                          n_days=x.day.nunique(), win=w.mean(), exp_R=x[col].mean(),
                                          exp_lo=lo, exp_hi=hi,
                                          pf=(x[col][w].sum() / -x[col][~w].sum()) if (~w).any() else np.nan,
                                          med_risk_atr=x.risk_atr.median(),
                                          time_exits=(x[f"exit{R}"] == "TIME").mean()))
    tt = pd.DataFrame(trows)
    tt.to_csv(A / "confirmation_results.csv", index=False)

    # 3b — candidate rules chosen on DEV only, then judged on HOLDOUT + stress tests
    dev = tt[(tt.split == "DEV") & (tt.n >= 100)]
    cands = dev[dev.exp_lo > 0].sort_values("exp_lo", ascending=False)
    srows = []
    for c_ in cands.itertuples():
        if c_.family == "ALL":
            sub = tr
        elif c_.family == "4H_ANY":
            sub = tr[(tr.zone_tf == "4h") | (tr.family == "5m:4H")]
        else:
            sub = tr[tr.family == c_.family]
        sub = sub[filters[c_.filter](sub)]
        col = f"r{c_.R}"
        g = sub[sub.conf == c_.conf].dropna(subset=[col]).drop_duplicates(["entry_i", "tdir", "conf"])
        ho = g[g.split == "HOLDOUT"]
        if len(ho) < 15:
            continue
        lo, hi = boot_mean(ho[col].to_numpy(), ho.day.astype(str).to_numpy())
        cost2 = ho[col] - 0.3 / ho.risk_pts
        q95 = ho[col].quantile(.95)
        srows.append(dict(family=c_.family, filter=c_.filter, conf=c_.conf, R=c_.R,
                          dev_n=c_.n, dev_exp=c_.exp_R, dev_lo=c_.exp_lo, dev_hi=c_.exp_hi,
                          ho_n=len(ho), ho_days=ho.day.nunique(), ho_win=(ho[col] > 0).mean(), ho_exp=ho[col].mean(),
                          ho_lo=lo, ho_hi=hi,
                          ho_exp_cost2x=cost2.mean(),
                          ho_exp_late=(ho.r2_late.mean() if c_.R == 2 else np.nan),
                          ho_exp_long=ho[ho.tdir == 1][col].mean(), ho_n_long=int((ho.tdir == 1).sum()),
                          ho_exp_short=ho[ho.tdir == -1][col].mean(), ho_n_short=int((ho.tdir == -1).sum()),
                          ho_exp_trim5=ho[ho[col] < q95][col].mean(),
                          all_exp=g[col].mean(), all_n=len(g)))
    sr = pd.DataFrame(srows)
    sr.to_csv(A / "candidate_rules_holdout.csv", index=False)
    summary["n_dev_candidates"] = int(len(cands))
    summary["n_candidates_positive_holdout"] = int((sr.ho_exp > 0).sum()) if len(sr) else 0

    # 4 — session / hour bias for held rate and baseline touch trade (C0, 2R)
    sess = ev.groupby(["session"]).agg(n=("held", "size"), hold=("held", "mean"), ret12=("ret12_atr", "mean"))
    sess.to_csv(A / "session_bias.csv")
    hour = ev.groupby(["hour_ct"]).agg(n=("held", "size"), hold=("held", "mean"), ret12=("ret12_atr", "mean"))
    hour.to_csv(A / "hour_bias.csv")

    # 5 — MFE/MAE by reaction for stop/target placement (in ATR and zone-size units)
    ev["mae24_zone"] = ev.mae24_atr * ev.atr / ev["size"]
    mm = ev.groupby(["family", "reaction"])[["mfe6_atr", "mae6_atr", "mfe24_atr", "mae24_atr", "mae24_zone"]]\
        .describe(percentiles=[.25, .5, .75, .9]).round(3)
    mm.to_csv(A / "mfe_mae_by_reaction.csv")
    summary["reaction_rates_first_arrival"] = rr[rr.arrival_no == 1].pivot_table(
        index="family", columns="reaction", values="rate").round(3).to_dict()
    summary["n_by_family"] = ev.family.value_counts().to_dict()
    (A / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
