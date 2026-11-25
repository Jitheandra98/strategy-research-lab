"""Can we tell, at the moment a ◆ PENDING appears, which ones will win?
Features use only bars up to the pending bar's close. Trade = enter at pending close, SL 0.5 ATR, TP1 1.5R (variant B).
Train 2016-2020, test untouched 2021-2024 and 2025-2026. Models: logistic regression + gradient boosting.
Check: AUC (0.5 = coin flip) and average R of the trades the model likes most (top 20 % / top 10 %).
"""
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
from score_pending import load, score
from score_qf15 import t5, H5, L5, C5, period
HERE = Path(__file__).resolve().parent
# 15m bars from 5m
b = pd.DataFrame({"h": H5, "l": L5, "c": C5, "o": np.fromfile(Path.home() / "Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)[:, 1]},
                 index=pd.to_datetime(t5, unit="ms"))
q = b.resample("15min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
pc = q.c.shift(); tr = pd.concat([q.h - q.l, (q.h - pc).abs(), (q.l - pc).abs()], axis=1).max(axis=1)
q["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
q["atr_reg"] = q.atr / q.atr.rolling(500).median()
for n in (4, 16, 96): q[f"ret{n}"] = (q.c - q.c.shift(n)) / q.atr
q["pos96"] = (q.c - q.l.rolling(96).min()) / (q.h.rolling(96).max() - q.l.rolling(96).min())
q["e50s"] = (q.c.ewm(span=50).mean().diff(8)) / q.atr
q["vs200"] = (q.c - q.c.ewm(span=200).mean()) / q.atr
q["body"] = (q.c - q.o) / (q.h - q.l).replace(0, np.nan)
q["cloc"] = (q.c - q.l) / (q.h - q.l).replace(0, np.nan)
day = (q.index + pd.Timedelta(hours=1)).date            # ~ 23:00 UTC futures day
q["dayrng"] = (q.h.groupby(day).cummax() - q.l.groupby(day).cummin()) / (q.atr * 16)
q["daypos"] = (q.c - q.l.groupby(day).cummin()) / (q.h.groupby(day).cummax() - q.l.groupby(day).cummin()).replace(0, np.nan)

ALIGN = ["ret4", "ret16", "ret96", "e50s", "vs200", "body"]          # multiplied by direction (with/against the trade)
ALIGN01 = ["pos96", "cloc", "daypos"]                               # 0..1, flipped for sells
def feats(P):
    X = q.reindex(pd.to_datetime(P.t, unit="ms")).reset_index(drop=True)
    d = P.dir.to_numpy()
    F = pd.DataFrame({"dir": d, "hour": pd.to_datetime(P.t, unit="ms").dt.hour, "dow": pd.to_datetime(P.t, unit="ms").dt.dayofweek,
                      "atr_reg": X.atr_reg, "dayrng": X.dayrng})
    for c in ALIGN: F[c] = X[c].to_numpy() * d
    for c in ALIGN01: F[c] = np.where(d == 1, X[c], 1 - X[c])
    F["label_gap"] = d * (P.close - P.price).to_numpy() / P.atr.to_numpy()
    F["liq_dist"] = np.where(P.liq > 0, d * (P.liq - P.close) / P.atr, np.nan)
    F["hsin"], F["hcos"] = np.sin(2 * np.pi * F.hour / 24), np.cos(2 * np.pi * F.hour / 24)
    return F

pd.set_option("display.width", 200)
for v in ("original", "ZONE_RULE"):
    P = load(v); R = score(P, "B")
    D = P.merge(R[["t", "dir", "TP1 1.5R"]], on=["t", "dir"]).rename(columns={"TP1 1.5R": "R"})
    F = feats(D); y = (D.R > 0).astype(int); per = period(D.t)
    tr_ = per == "1) 2016-2020"
    gb = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=100, random_state=0)
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    Fl = F.drop(columns=["hour"]).fillna(F.median(numeric_only=True))
    gb.fit(F[tr_], y[tr_]); lr.fit(Fl[tr_], y[tr_])
    print(f"\n======== {v}: {len(D)} pendings, win rate {y.mean():.1%} ========")
    rows = []
    for name, p in (("boosting", gb.predict_proba(F)[:, 1]), ("logistic", lr.predict_proba(Fl)[:, 1])):
        for pr in ("1) 2016-2020", "2) 2021-2024", "3) 2025-2026"):
            m = per == pr; Rm, pm = D.R[m].to_numpy(), p[m]
            row = dict(model=name, period=pr + (" (TRAIN)" if pr.startswith("1") else " (UNSEEN)"), n=m.sum(), AUC=round(roc_auc_score(y[m], pm), 3),
                       all_avgR=round(Rm.mean(), 3))
            for top in (0.2, 0.1):
                cut = np.quantile(pm, 1 - top); s = Rm[pm >= cut]
                row[f"top{int(top*100)}%_n"] = len(s); row[f"top{int(top*100)}%_win"] = f"{(s > 0).mean():.1%}"
                row[f"top{int(top*100)}%_avgR"] = round(s.mean(), 3); row[f"top{int(top*100)}%_±95"] = round(1.96 * s.std() / np.sqrt(len(s)), 3)
            rows.append(row)
    print(pd.DataFrame(rows).to_string(index=False))
    # gross (no cost) check of the best-looking slice
    co = pd.Series(lr.named_steps["logisticregression"].coef_[0], index=Fl.columns).sort_values()
    print("logistic weights (standardised; + = more likely to win):"); print(co.round(3).to_string())
