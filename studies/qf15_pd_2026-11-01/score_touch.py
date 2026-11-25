"""Owner's premium/discount rules on QF15 15m, 2016-2026:
 touch green (pd<=5) = buy, touch red (pd>=95) = sell; first touch vs repeated (trend); session-open runs. 3R/4R/hold, MAE, random control."""
import json, glob, warnings
import numpy as np, pandas as pd
from pathlib import Path
warnings.filterwarnings("ignore")
H = Path(__file__).resolve().parent
v = {}
for f in sorted(glob.glob(str(H / "chunks/*.json"))):
    r = json.load(open(f))
    for k, vv in r["values"].items(): v.setdefault(k, []).extend(vv)
df = pd.DataFrame({k: pd.Series({t: x for t, x in vv}) for k, vv in v.items()}).sort_index().dropna(subset=["v_pd"])
df.index = pd.to_datetime(df.index, unit="ms")
a = np.fromfile(Path.home() / "Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)
t5 = (a[:, 0] if a[0, 0] > 1e11 else a[:, 0] * 1000).astype("int64"); H5, L5, C5 = a[:, 2], a[:, 3], a[:, 4]
COST, HOLD5, STOP_ATR = 0.35, 288, 1.5
pdv = df.v_pd.to_numpy(); atr = df.v_atr14.to_numpy()
ts = (df.index.view("int64") // 10**6) + 15 * 60 * 1000   # bar close time (ms) -> first 5m bar after
ct = df.index.tz_localize("UTC").tz_convert("America/Chicago")
mins = ct.hour * 60 + ct.minute
# events
ev = []
side_last = 0; cnt = 0; last_ext_bar = {1: -10**9, -1: -10**9}
for i in range(1, len(pdv)):
    g = pdv[i] <= 5 and pdv[i - 1] > 5
    r = pdv[i] >= 95 and pdv[i - 1] < 95
    if not (g or r): 
        if pdv[i] <= 5: last_ext_bar[1] = i
        if pdv[i] >= 95: last_ext_bar[-1] = i
        continue
    d = 1 if g else -1               # green touch -> buy, red touch -> sell
    cnt = cnt + 1 if side_last == d else 1
    side_last = d
    opp_recent = i - last_ext_bar[-d] <= 8          # came from the other extreme within 2h ("fast run")
    m = mins[i]
    sess = "NY open" if 510 <= m < 600 else "Tokyo open" if 1080 <= m < 1200 else "London open" if 120 <= m < 240 else "other"
    ev.append((i, d, min(cnt, 3), opp_recent, sess))
    last_ext_bar[d] = i
E = pd.DataFrame(ev, columns=["i", "dir", "nth", "fastRun", "sess"])
rng = np.random.default_rng(7)
R = pd.DataFrame({"i": rng.choice(np.arange(200, len(pdv) - 1), len(E) * 2, replace=False), "dir": rng.choice([1, -1], len(E) * 2)})
def sim(row):
    i, d = int(row.i), int(row.dir)
    if np.isnan(atr[i]): return None
    k = np.searchsorted(t5, ts[i]); 
    if k >= len(C5): return None
    e = C5[k - 1]; risk = STOP_ATR * atr[i]; c = COST / risk
    hs, ls = H5[k:k + HOLD5], L5[k:k + HOLD5]
    adv = (e - ls) / risk if d == 1 else (hs - e) / risk
    fav = (hs - e) / risk if d == 1 else (e - ls) / risk
    stop = np.argmax(adv >= 1) if (adv >= 1).any() else 10**9
    out = {}
    for RR in (3, 4):
        hit = np.argmax(fav >= RR) if (fav >= RR).any() else 10**9
        out[f"r{RR}"] = (RR - c) if hit < stop else (-1 - c) if stop < 10**9 else d * (C5[min(k + HOLD5, len(C5)) - 1] - e) / risk - c
    out["hold"] = -1 - c if stop < 10**9 else d * (C5[min(k + HOLD5, len(C5)) - 1] - e) / risk - c
    pre = adv[:stop] if stop < 10**9 else adv
    p1 = np.argmax(fav[:stop] >= 1) if (fav[:stop] >= 1).any() else None
    out["plus1"] = p1 is not None; out["maeBefore1"] = pre[:p1 + 1].max() if p1 is not None else np.nan
    out["year"] = df.index[i].year
    return out
def run(X):
    o = [sim(r) for r in X.itertuples()]
    X = X.copy(); keep = [x is not None for x in o]; X = X[keep]
    return pd.concat([X.reset_index(drop=True), pd.DataFrame([x for x in o if x]).reset_index(drop=True)], axis=1)
E = run(E); R = run(R)
for X in (E, R): X["period"] = pd.cut(X.year, [0, 2020, 2024, 2100], labels=["2016-20", "2021-24", "2025-26"])
def pf(x): w = x[x > 0].sum(); l = -x[x < 0].sum(); return w / l if l > 0 else np.inf
def summ(g): return pd.Series({"n": len(g), "PF 3R": pf(g.r3), "avgR 3R": g.r3.mean(), "PF 4R": pf(g.r4), "avgR 4R": g.r4.mean(), "PF hold": pf(g.hold), "avgR hold": g.hold.mean(), "reach+1R%": g.plus1.mean() * 100})
pd.set_option("display.width", 220); pd.set_option("display.float_format", lambda x: f"{x:.2f}")
print("== ALL TOUCHES (green=buy, red=sell) vs RANDOM, by period")
print(pd.concat({"TOUCH": E.groupby("period").apply(summ), "RANDOM": R.groupby("period").apply(summ)}))
print("\n== by side (1=green buy, -1=red sell)"); print(E.groupby(["dir", "period"]).apply(summ))
print("\n== 1st vs 2nd vs 3rd+ touch on same side (trend idea)"); print(E.groupby(["nth", "period"]).apply(summ))
print("\n== FADE the 3rd+ touch instead (trade WITH the trend)")
T3 = E[E.nth == 3].copy(); T3["dir"] = -T3.dir; T3 = run(T3[["i", "dir"]]); T3["period"] = pd.cut(T3.year, [0, 2020, 2024, 2100], labels=["2016-20", "2021-24", "2025-26"]); print(T3.groupby("period").apply(summ))
print("\n== session-open touches after a fast run from the other extreme"); print(E[E.fastRun].groupby(["sess", "period"]).apply(summ))
print("\n== session (all touches)"); print(E.groupby("sess").apply(summ))
w = E[E.plus1]; print("\nMAE before +1R (touch trades that reached +1R):", w.maeBefore1.describe(percentiles=[.5, .75, .9]).round(2).to_dict())
E.to_pickle(H / "touch_trades.pkl")
