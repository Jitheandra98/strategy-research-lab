"""Stage 12 — the candidate strategy as it would actually be traded: one position at a time.

Setup A: 4H zone (4H-chart FVG/OB, or 4H FVG imported on 5m), arrival from outside, 4H trend
aligned (EMA100 slope over 10 closed 4H bars), entry next 5m open after the touch bar, stop beyond
the zone/touch extreme +0.25 ATR, target R_TARGET x risk, 48-bar time stop. Signals that fire while
a position is open are skipped. Also runs the same engine on 5m-only zones and counter-trend 4H
zones as controls. Writes analysis/portfolio_*.csv and figures/equity.png
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(sys.argv[1])
A, F = OUT / "analysis", OUT / "figures"
F.mkdir(exist_ok=True)
ev = pd.read_csv(OUT / "events.csv")
ev["time_ct"] = pd.to_datetime(ev.time_ct, utc=True).dt.tz_convert("America/Chicago")
ev["family"] = ev.zone_tf + ":" + ev.zone_kind
tr = pd.read_csv(OUT / "data" / "confirmation_trades.csv")
tr = tr.merge(ev[["zone_uid", "i", "family", "zone_tf", "trend4_aligned", "time_ct", "video_ts"]]
              .rename(columns={"i": "event_i"}), on=["zone_uid", "event_i"])
days = np.sort(ev.time_ct.dt.date.unique())
cut = days[int(len(days) * 0.6)]


def run(sel, R, name):
    col, bcol = f"r{R}", f"bars{R}"
    s = sel.dropna(subset=[col]).sort_values("entry_i").drop_duplicates(["entry_i", "tdir"])
    busy_until, taken = -1, []
    for r in s.itertuples():
        if r.entry_i <= busy_until:
            continue
        taken.append(r)
        busy_until = r.entry_i + int(getattr(r, bcol))
    t = pd.DataFrame(taken)
    if t.empty:
        return None, t
    t["R"] = t[col]
    t["equity"] = t.R.cumsum()
    t["dd"] = t.equity - t.equity.cummax()
    t["split"] = np.where(t.time_ct.dt.date < cut, "DEV", "HOLDOUT")
    out = {"setup": name, "R_target": R, "trades": len(t), "win": (t.R > 0).mean(), "exp_R": t.R.mean(),
           "total_R": t.R.sum(), "max_dd_R": t.dd.min(), "worst_streak": worst_streak(t.R),
           "dev_exp": t[t.split == "DEV"].R.mean(), "ho_exp": t[t.split == "HOLDOUT"].R.mean(),
           "trades_per_week": len(t) / (len(days) / 5), "med_risk_pts": t.risk_pts.median()}
    return out, t


def worst_streak(r):
    w = cur = 0
    for x in r:
        cur = cur + 1 if x <= 0 else 0
        w = max(w, cur)
    return w


fam4 = (tr.zone_tf == "4h") | (tr.family == "5m:4H")
setups = {
    "A: 4H zone + 4H trend, touch": tr[fam4 & (tr.trend4_aligned == True) & (tr.conf == "C0_TOUCH")],
    "control: 4H zone counter-trend": tr[fam4 & (tr.trend4_aligned == False) & (tr.conf == "C0_TOUCH")],
    "control: 5m zones only, touch": tr[~fam4 & (tr.conf == "C0_TOUCH")],
    "control: 5m zones + 5m reclaim": tr[~fam4 & (tr.conf == "C1_RECLAIM")],
}
rows, curves = [], {}
for name, sel in setups.items():
    for R in (1, 2, 3):
        o, t = run(sel, R, name)
        if o:
            rows.append(o)
            if R == 2:
                curves[name] = t
                slug = {"A: 4H zone + 4H trend, touch": "A", "control: 4H zone counter-trend": "ctrl_4h_countertrend",
                        "control: 5m zones only, touch": "ctrl_5m_touch",
                        "control: 5m zones + 5m reclaim": "ctrl_5m_reclaim"}.get(name, name.split(":")[0].strip())
                t.to_csv(A / f"portfolio_trades_{slug}_{R}R.csv", index=False)
res = pd.DataFrame(rows)
res.to_csv(A / "portfolio_summary.csv", index=False)
pd.set_option("display.width", 220)
print(res.round(3).to_string())

fig, ax = plt.subplots(figsize=(8.5, 3.6))
colors = ["#1b5e20", "#9e9e9e", "#c62828", "#ef6c00"]
for (name, t), cl in zip(curves.items(), colors):
    ax.plot(t.time_ct, t.equity, label=f"{name} (n={len(t)})", color=cl, lw=1.6 if name.startswith("A") else 1)
ax.axvline(pd.Timestamp(cut).tz_localize("America/Chicago"), color="k", ls="--", lw=.8)
ax.text(pd.Timestamp(cut).tz_localize("America/Chicago"), ax.get_ylim()[1] * .9, "  HOLDOUT →", fontsize=8)
ax.axhline(0, color="k", lw=.6)
ax.set_ylabel("cumulative R (2R target, after 0.3 pt cost)")
ax.set_title("One position at a time — reconstructed MGC 5m, Nov 2025 – Sep 2026", fontsize=10)
ax.legend(fontsize=7, loc="upper left")
fig.tight_layout()
fig.savefig(F / "equity.png")
