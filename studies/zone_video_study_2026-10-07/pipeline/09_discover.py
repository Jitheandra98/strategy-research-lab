"""Stage 9: DISCOVERY analysis (V1+V2 events only). Nothing here reads VALIDATION (V3) or EXTERNAL outcomes.

Outputs to <out>/analysis/:
  base_rates.csv, archetypes.csv          what happens at all
  screen_single.csv                       every single-feature bin vs its group's base rate (Wilson CI, z, BH q)
  screen_pairs.csv                        pairwise AND of the strongest single conditions
  tree_rules.txt                          shallow decision trees (depth 3, leaf >= 60) per group
  clusters.csv, cluster_centroids.csv     k-means "states" of the 10-bar approach + arrival bar
  confirm.csv                             WAIT-and-confirm (decide 1-3 bars after arrival)
  frozen.json                             every cut-point / rule / centroid, to be applied unchanged to V3 + EXTERNAL
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.tree import DecisionTreeClassifier, export_text

B = Path(sys.argv[1]); OUT = Path(sys.argv[2]); A = OUT / "analysis"; A.mkdir(parents=True, exist_ok=True)
ev = pd.read_pickle(B / "events.pkl")
D = ev[ev.video.isin([1, 2])].copy()
D = D[D.R1.notna()]
print("discovery events", len(D))

NUM = ["height_atr", "size_atr_birth", "age_bars", "prior_arrivals", "prior_max_pen", "bars_since_last",
       "bars_since_break", "atr_regime", "ema_dist_atr", "travel_atr", "approach_bars", "velocity_atr_per_bar",
       "rng_last3_atr", "accel_ratio", "max_rng10_atr", "body_frac_last3", "consec_toward", "n_toward_last10",
       "mom10_atr", "compress5_atr", "prev_bar_rng_atr", "pen_frac", "pen_atr", "close_depth_frac", "arr_rng_atr",
       "arr_clv", "arr_body_frac", "room_atr", "n_overlap_same", "n_overlap_opp", "n_support_behind_2atr", "hour_ny",
       "score_birth"]
BIN = ["trend15_with", "trend4_with", "struct15_with", "struct4_with", "ema4_side_with", "disp_fvg_toward5",
       "disp_fvg_away20", "prev_bar_toward", "wick_beyond_far", "body_entered", "passed_mid", "arr_dir_with_reaction",
       "gap_open_inside", "nested_in_4h_same", "conflict_4h_opp"]
CAT = ["zone_kind", "close_loc", "session"]


def session(h):
    return "ASIA" if (h >= 18 or h < 2) else "LONDON" if h < 8 else "NY_AM" if h < 12 else "NY_PM"


D["session"] = D.hour_ny.map(session)
GROUPS = {"ALL_ARRIVAL": D.interaction == "ARRIVAL", "ALL_FLIP": D.interaction == "FLIP",
          "Z15_ARRIVAL": (D.universe == "Z15") & (D.interaction == "ARRIVAL"),
          "Z4_ARRIVAL": (D.universe == "Z4") & (D.interaction == "ARRIVAL"),
          "Z15_FLIP": (D.universe == "Z15") & (D.interaction == "FLIP"),
          "Z4_FLIP": (D.universe == "Z4") & (D.interaction == "FLIP")}


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); r = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


TGT = "R1"
GROUP_SD = {}


def stats(sub, base_p, base_n):
    y = sub[TGT].dropna(); n = len(y); p = y.mean() if n else np.nan
    if TGT.endswith("_R"):   # continuous R-multiple: mean, t-interval, z vs group mean
        sd = y.std(ddof=1) if n > 1 else np.nan; se = sd / np.sqrt(n) if n > 1 else np.nan
        lo, hi = p - 1.96 * se, p + 1.96 * se
        z = (p - base_p) / se if n > 1 else np.nan
    else:
        k = y.sum(); lo, hi = wilson(k, n)
        z = (p - base_p) / np.sqrt(base_p * (1 - base_p) * (1 / n + 1 / max(1, base_n - n))) if n and base_n > n else np.nan
    days = sub.time_utc.dt.date.nunique()
    return dict(target=TGT, n=n, uniq_bars=sub.bar.nunique(), days=days, rate=p, ci_lo=lo, ci_hi=hi, z=z,
                p_val=2 * (1 - norm.cdf(abs(z))) if pd.notna(z) else np.nan, BRK=sub.BRK.mean(),
                ret10_mean=sub.ret10.mean(), ret10_med=sub.ret10.median(), mfe_med=sub.mfe20.median(),
                mae_med=sub.mae20.median(), mfe_mean=sub.mfe20.mean(), mae_mean=sub.mae20.mean())


def bh(p):
    p = np.asarray(p, float); m = np.isfinite(p).sum(); q = np.full(len(p), np.nan)
    idx = np.where(np.isfinite(p))[0]; o = idx[np.argsort(p[idx])]
    run = 1.0
    for r, i in reversed(list(enumerate(o, 1))):
        run = min(run, p[i] * m / r); q[i] = run
    return q


# ── base rates & archetypes ──
br = []
for g, m in GROUPS.items():
    s = stats(D[m], D[m].R1.mean(), m.sum()); s.update(group=g, R2=D[m].R2.mean(), R05=D[m].R05.mean(),
                                                        RECLAIM=D[m].RECLAIM.mean()); br.append(s)
pd.DataFrame(br).to_csv(A / "base_rates.csv", index=False)
arc = D.groupby(["interaction", "universe"]).archetype.value_counts(normalize=True).unstack().round(3)
arc.to_csv(A / "archetypes.csv")

frozen = {"cuts": {}, "groups": list(GROUPS)}
for TGT in ["R1", "BRK", "tr2_R"]:
    # ── single-feature screen ──
    conds = {}   # name -> function(df) -> bool mask  (built from frozen cuts)
    rows = []
    for g, m in GROUPS.items():
        G = D[m]; bp = G[TGT].mean(); bn = G[TGT].notna().sum()
        for f in NUM:
            x = G[f]
            if x.notna().sum() < 90 or x.nunique() < 3: continue
            q = np.unique(np.nanquantile(x, [1 / 3, 2 / 3]))
            frozen["cuts"].setdefault(g, {})[f] = q.tolist()
            edges = [-np.inf] + q.tolist() + [np.inf]
            for b in range(len(edges) - 1):
                lo, hi = edges[b], edges[b + 1]
                name = f"{f} in ({lo:.3g},{hi:.3g}]"
                sub = G[(x > lo) & (x <= hi)]
                if len(sub) < 25: continue
                s = stats(sub, bp, bn); s.update(group=g, feature=f, cond=name, lo=lo, hi=hi, kind="num"); rows.append(s)
        for f in BIN + CAT:
            if f not in G or G[f].nunique() < 2: continue
            for lv in G[f].dropna().unique():
                sub = G[G[f] == lv]
                if len(sub) < 25: continue
                s = stats(sub, bp, bn); s.update(group=g, feature=f, cond=f"{f} == {lv}", level=lv, kind="lvl"); rows.append(s)
    S = pd.DataFrame(rows)
    S["q_BH"] = bh(S.p_val.to_numpy())
    S["base"] = S.group.map({g: D[m][TGT].mean() for g, m in GROUPS.items()})
    S["lift"] = S.rate - S.base
    S.sort_values("z", key=abs, ascending=False).to_csv(A / f"screen_single_{TGT}.csv", index=False)
    print(TGT, "single tests:", len(S), " q<0.10:", (S.q_BH < 0.10).sum())


    def mask_of(G, r):
        if r["kind"] == "num":
            return (G[r["feature"]] > r["lo"]) & (G[r["feature"]] <= r["hi"])
        return G[r["feature"]] == r["level"]


    # ── pairwise AND of the strongest single conditions (both directions: good and bad) ──
    prow = []
    for g, m in GROUPS.items():
        G = D[m]; bp = G[TGT].mean(); bn = G[TGT].notna().sum()
        top = S[(S.group == g)].sort_values("z", key=abs, ascending=False).head(24).to_dict("records")
        for a in range(len(top)):
            for b in range(a + 1, len(top)):
                ra, rb = top[a], top[b]
                if ra["feature"] == rb["feature"]: continue
                mm = mask_of(G, ra) & mask_of(G, rb)
                sub = G[mm]
                if len(sub) < 40: continue
                s = stats(sub, bp, bn)
                s.update(group=g, cond=f"{ra['cond']} AND {rb['cond']}", a=ra["cond"], b=rb["cond"],
                         a_rate=ra["rate"], b_rate=rb["rate"]); prow.append(s)
    PR = pd.DataFrame(prow)
    if len(PR):
        PR["q_BH"] = bh(PR.p_val.to_numpy()); PR["base"] = PR.group.map({g: D[m][TGT].mean() for g, m in GROUPS.items()})
        PR["synergy"] = PR.rate - np.where(PR.rate > PR.base, np.maximum(PR.a_rate, PR.b_rate), np.minimum(PR.a_rate, PR.b_rate))
        PR.sort_values("z", key=abs, ascending=False).to_csv(A / f"screen_pairs_{TGT}.csv", index=False)
        print(TGT, "pair tests:", len(PR), " q<0.10:", (PR.q_BH < 0.10).sum())

TGT = "R1"
# ── shallow trees ──
feats = NUM + BIN
txt = []
frozen["trees"] = {}
for g, m in GROUPS.items():
    G = D[m]
    X = G[feats].astype(float).fillna(-999); y = G.R1.astype(int)
    if len(G) < 300: continue
    t = DecisionTreeClassifier(max_depth=3, min_samples_leaf=60, random_state=0).fit(X, y)
    txt.append(f"=== {g} (n={len(G)}, base R1={y.mean():.3f})\n" + export_text(t, feature_names=feats, show_weights=True))
    leaf = t.apply(X); lt = pd.DataFrame({"leaf": leaf, "R1": y}).groupby("leaf").R1.agg(["size", "mean"])
    txt.append(lt.round(3).to_string())
    import pickle; pickle.dump(t, open(A / f"tree_{g}.pkl", "wb"))
(A / "tree_rules.txt").write_text("\n".join(txt))

# ── sequence states: k-means on the oriented approach path + arrival extreme ──
P = [f"p{k}" for k in range(11)] + ["p_ext"]
Z = D[D.interaction == "ARRIVAL"]
Xc = Z[P].clip(-6, 12).to_numpy()
class _KM:  # plain k-means (sklearn's threadpoolctl probe crashes in this env)
    def __init__(self, X, k, n_init=20, seed=0, iters=200):
        rng = np.random.default_rng(seed); best = None
        for _ in range(n_init):
            c = X[rng.choice(len(X), k, replace=False)].copy()
            for _ in range(iters):
                lab = ((X[:, None, :] - c[None]) ** 2).sum(2).argmin(1)
                nc = np.array([X[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
                if np.allclose(nc, c): break
                c = nc
            inertia = ((X - c[lab]) ** 2).sum()
            if best is None or inertia < best[0]: best = (inertia, c, lab)
        self.cluster_centers_, self.labels_ = best[1], best[2]
km = _KM(Xc, 6)
Z = Z.assign(state=km.labels_)
names = {}
cen = pd.DataFrame(km.cluster_centers_, columns=P)
order = cen.p0.sort_values().index  # name by starting distance: A = started closest
for j, c in enumerate(order): names[c] = "ABCDEF"[j]
cen.index = [names[i] for i in cen.index]
cen.sort_index().round(2).to_csv(A / "cluster_centroids.csv")
cl = []
for c, G in Z.groupby("state"):
    s = stats(G, Z.R1.mean(), len(Z)); s.update(state=names[c], BRK_rate=G.BRK.mean(), tr2_R=G.tr2_R.mean()); cl.append(s)
pd.DataFrame(cl).sort_values("state").to_csv(A / "clusters.csv", index=False)
frozen["centroids"] = {names[i]: km.cluster_centers_[i].tolist() for i in range(6)}

# ── WAIT-and-confirm ──
crow = []
for g in ["ALL_ARRIVAL", "Z15_ARRIVAL", "Z4_ARRIVAL", "ALL_FLIP"]:
    G = D[GROUPS[g]]
    for k in (1, 2, 3):
        for cond, mm in [(f"closed back outside by bar {k}", G[f"c{k}_close_out"] == 1),
                         (f"no close beyond far edge by bar {k}", G[f"c{k}_closed_beyond"] == 0),
                         (f"closed outside AND no far close by bar {k}", (G[f"c{k}_close_out"] == 1) & (G[f"c{k}_closed_beyond"] == 0)),
                         (f"closed beyond far edge by bar {k}", G[f"c{k}_closed_beyond"] == 1),
                         (f"made a new extreme at bar {k}", G[f"c{k}_new_ext"] == 1)]:
            sub = G[mm & G[f"c{k}_R1"].notna()]
            base = G[G[f"c{k}_R1"].notna()]
            if len(sub) < 25: continue
            n = len(sub); kk = sub[f"c{k}_R1"].sum(); lo, hi = wilson(kk, n)
            crow.append(dict(group=g, k=k, cond=cond, n=n, R1_from_confirm=kk / n, ci_lo=lo, ci_hi=hi,
                             base_R1_from_k=base[f"c{k}_R1"].mean(), ret10_from_confirm=sub[f"c{k}_ret10"].mean()))
pd.DataFrame(crow).to_csv(A / "confirm.csv", index=False)
(A / "frozen.json").write_text(json.dumps(frozen, indent=1, default=float))
print("done")
