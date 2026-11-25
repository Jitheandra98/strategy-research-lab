"""Tokyo bias (five blue lines) + QF CORE order blocks / FVGs, Tokyo session only (rules in SPEC.md, written before testing).
Needs zones.npz from qf_zones.py. Run: python3 tokyo_plan.py > results.txt"""
import json, sys
import numpy as np, pandas as pd

sys.path.insert(0, "/Users/jitheandrasubramaniam/Desktop/hey hey/research/catalog_100_2026-11-08")
from common import O, H, L, C, N, t, sid, nS, sfirst, slast, YEAR, ATR, evaluate, pf, PERIODS

D = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/tokyo_obfvg_2026-11-08/"
Z = np.load(D + "zones.npz")
K, S, TOP, BOT, TOUCH = Z["kind"], Z["side"], Z["top"], Z["bot"], Z["touch"]
Ol, Hl, Ll, Cl, Al = O.tolist(), H.tolist(), L.tolist(), C.tolist(), ATR.tolist()

# five blue lines (equal weight, anchored at the 18:00 ET session start)
x = (H + L + C) / 3
cnt = pd.Series(x).groupby(sid).cumcount().to_numpy() + 1
m1 = pd.Series(x).groupby(sid).cumsum().to_numpy() / cnt
m2 = pd.Series(x * x).groupby(sid).cumsum().to_numpy() / cnt
VW, SD = m1, np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
utcm = (t // 60) % 1440

BIAS = {"MAIN": np.zeros(nS, int), "LOOSE": np.zeros(nS, int)}
WIN = np.full((nS, 2), -1)
for s in range(1, nS):
    f, l = sfirst[s], slast[s]
    u = utcm[f:l + 1]
    tk = np.flatnonzero(u < 60) + f
    tk = tk[tk > f]
    w = np.flatnonzero((u >= 60) & (u < 540)) + f
    if len(w): WIN[s] = (w[0], w[-1])
    if len(tk) != 12: continue
    c = C[tk]
    if np.all(c > (VW + SD)[tk]): BIAS["MAIN"][s] = 1
    elif np.all(c < (VW - SD)[tk]): BIAS["MAIN"][s] = -1
    if np.all(c > VW[tk]): BIAS["LOOSE"][s] = 1
    elif np.all(c < VW[tk]): BIAS["LOOSE"][s] = -1

order = np.argsort(TOUCH, kind="stable")
ts = TOUCH[order]


def run(bias="MAIN", kinds=(0, 1, 2), m=2.0, wide=False):
    rows = []
    for s in range(1, nS):
        w0, w1 = WIN[s]
        if w0 < 0: continue
        d = BIAS[bias][s] if bias else 0
        if bias and d == 0: continue
        a, b = np.searchsorted(ts, w0), np.searchsorted(ts, w1, side="right")
        cz = [z for z in order[a:b] if K[z] in kinds and (d == 0 or S[z] == d)]
        cz.sort(key=lambda z: (TOUCH[z], -TOP[z] if S[z] == 1 else BOT[z]))
        busy = -1
        for z in cz:
            j = TOUCH[z]
            if j <= busy: continue
            dd = S[z]
            px = TOP[z] if dd == 1 else BOT[z]
            if wide: stop = BOT[z] - Al[j - 1] if dd == 1 else TOP[z] + Al[j - 1]
            else: stop = BOT[z] - 0.1 if dd == 1 else TOP[z] + 0.1
            R = dd * (px - stop)
            if R < 0.2: continue
            tgt = px + dd * m * R
            if (dd == 1 and Ll[j] <= stop) or (dd == -1 and Hl[j] >= stop):
                xb, xp = j, stop
            else:
                xb, xp = w1, Cl[w1]
                for q in range(j + 1, w1 + 1):
                    if dd == 1:
                        if Ol[q] <= stop: xb, xp = q, Ol[q]; break
                        if Ll[q] <= stop: xb, xp = q, stop; break
                        if Hl[q] >= tgt: xb, xp = q, tgt; break
                    else:
                        if Ol[q] >= stop: xb, xp = q, Ol[q]; break
                        if Hl[q] >= stop: xb, xp = q, stop; break
                        if Ll[q] <= tgt: xb, xp = q, tgt; break
            rows.append((j, xb, dd, int(K[z]), px, xp, dd * (xp - px), R, YEAR[j]))
            busy = xb
    return pd.DataFrame(rows, columns=["i", "x", "d", "kind", "entry", "exit", "gross", "R", "year"])


def line(name, T, buy_only=False):
    if len(T) == 0:
        print(f"{name:44s} no trades"); return None
    ev = evaluate(T); n3 = T.gross.to_numpy() - 0.3
    per = [T.year.between(a, b).to_numpy() for a, b in PERIODS]
    ok = all(pf(n3[q]) >= 1.15 for q in per) and ev["usd_at_05"] > 0 and ev["yrs_pos"] >= 9 and all(q.sum() >= 30 for q in per)
    passed = ok if buy_only else ev["PASS"]
    print(f"{name:44s} {ev['n']:6,d} tr ({ev['per_yr']:4.0f}/yr) win {ev['win']:4.1f}%  PF {ev['PF']:.2f} "
          f"[{ev['PF_12_19']:.2f} {ev['PF_20_23']:.2f} {ev['PF_24_26']:.2f}]  net ${ev['usd']:+9,.0f}  avg ${ev['avg_pt'] * 10:+6.2f}  "
          f"SL ${T.R.median() * 10:4.0f}  @0.5 ${ev['usd_at_05']:+8,.0f}  yrs+ {ev['yrs_pos']:2d}  before fees {(T.gross / T.R).mean():+.3f}R  "
          f"{'PASS' if passed else 'FAIL'}")
    return ev


if __name__ == "__main__":
    nb = {k: int((v != 0).sum()) for k, v in BIAS.items()}
    print(f"Bias days: MAIN {nb['MAIN']} ({(BIAS['MAIN'] == 1).sum()} buy / {(BIAS['MAIN'] == -1).sum()} sell), "
          f"LOOSE {nb['LOOSE']} ({(BIAS['LOOSE'] == 1).sum()} buy / {(BIAS['LOOSE'] == -1).sum()} sell)\n")
    res = {}
    for name, kw in [("MAIN  OB+FVG, stop just beyond, 2R", {}), ("order blocks only", {"kinds": (0, 1)}),
                     ("FVGs only", {"kinds": (2,)}), ("target 1R", {"m": 1.0}), ("target 3R", {"m": 3.0}),
                     ("wide stop (zone - 1 ATR), 2R", {"wide": True}), ("LOOSE bias (all closes beyond center)", {"bias": "LOOSE"}),
                     ("CONTROL: no Tokyo bias, every day", {"bias": None})]:
        T = run(**kw); res[name] = T
        line(name + " | all", T)
        line(name + " | buy days, buys only", T[T.d == 1], buy_only=True)
        line(name + " | sell days, sells only", T[T.d == -1], buy_only=True)
        print()
    T = res["MAIN  OB+FVG, stop just beyond, 2R"]; n3 = T.gross.to_numpy() - 0.3
    print("MAIN per year:", "  ".join(f"{y}:{v * 10:+,.0f}" for y, v in pd.Series(n3).groupby(T.year.to_numpy()).sum().items()))
    B = T[T.d == 1]; nb3 = B.gross.to_numpy() - 0.3
    print("MAIN buys per year:", "  ".join(f"{y}:{v * 10:+,.0f}" for y, v in pd.Series(nb3).groupby(B.year.to_numpy()).sum().items()))
    r = T.gross / T.R
    print(f"MAIN exits: target {100 * (r >= 1.99).mean():.0f}%, stop {100 * (r <= -0.99).mean():.0f}%, "
          f"Tokyo close {100 * ((r > -0.99) & (r < 1.99)).mean():.0f}%; stopped inside the entry bar {100 * (T.x == T.i).mean():.0f}%")
    ny = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York"); ym = (ny.year * 100 + ny.month).to_numpy()
    months = [y * 100 + mm for y in range(2012, 2027) for mm in range(1, 13) if y * 100 + mm <= 202609]
    pos = {v: q for q, v in enumerate(months)}; chart = {}
    for key, TT in (("main", T), ("buys", B), ("control", res["CONTROL: no Tokyo bias, every day"])):
        gs, ns = np.zeros(len(months)), np.zeros(len(months), int)
        idx = np.array([pos[v] for v in ym[TT.i.to_numpy()]]); np.add.at(gs, idx, TT.gross.to_numpy() * 10); np.add.at(ns, idx, 1)
        chart[key] = {"gross": np.round(gs, 1).tolist(), "n": ns.tolist()}
        TT.to_csv(D + f"trades_{key}.csv", index=False)
    json.dump(chart, open(D + "chart_data.json", "w"), separators=(",", ":"))
