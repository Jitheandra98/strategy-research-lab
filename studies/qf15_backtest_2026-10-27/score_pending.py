"""Enter at the ◆ PENDING signal (zone touch), where the label's Entry price actually exists.
A  PENDING + script's scratch: market at pending-bar close; SL 0.5 ATR; TP1/TP2/TP3 as the script; if the script scratches
   the setup (no displacement in time / invalidated) and the trade is still open, exit at that bar's close.
B  PENDING, stop/target only (ignore scratch).
C  PENDING limit at the label Entry price (resting until the script validates or scratches), then as A.
H  HINDSIGHT (not tradable): A, but only on pendings that later became BUY/SELL — shows why the labels look so good.
Random control = same exits as B at random 15m closes. Cost 0.35 pt, 5m bars, stop-first, max hold 50 x 15m.
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
from score_qf15 import t5, H5, L5, C5, COST, HOLD5, period, COLS, summ
HERE = Path(__file__).resolve().parent

def load(v):
    rows = []
    for f in sorted((HERE / "chunks_pending").glob(f"{v}_*.json")):
        d = json.loads(f.read_text())
        if d["status"] != "ok": print("BAD", f.name); continue
        V = {k: dict(map(tuple, x)) for k, x in d["values"].items()}
        for side, d_, oc in (("pb", 1, "v_b_outcome"), ("ps", -1, "v_s_outcome")):
            outs = sorted(V.get(oc, {}).items())
            ot = np.array([o[0] for o in outs], dtype=np.int64); ov = np.array([o[1] for o in outs])
            for t, c in V.get(f"v_{side}_close", {}).items():
                j = np.searchsorted(ot, t, side="right")
                rows.append(dict(t=int(t), dir=d_, close=c, price=V[f"v_{side}_price"][t], atr=V[f"v_{side}_atr"][t],
                                 liq=V[f"v_{side}_liq"][t], out_t=int(ot[j]) if j < len(ot) else -1, outcome=ov[j] if j < len(ot) else -1))
    return pd.DataFrame(rows).sort_values("t").reset_index(drop=True)

def walk(d, stop, tgt, i0, i1, ix):
    """ix = 5m index of forced exit (scratch) or -1"""
    end = min(i1, len(C5))
    for k in range(i0, end):
        if (L5[k] <= stop) if d == 1 else (H5[k] >= stop): return stop
        if (H5[k] >= tgt) if d == 1 else (L5[k] <= tgt): return tgt
        if k == ix: return C5[k]
    return C5[end - 1]

def score(df, mode):
    res = []
    for r in df.itertuples():
        i0 = np.searchsorted(t5, r.t + 15 * 60000)
        if i0 >= len(C5) - 2 or not r.atr > 0: continue
        d = r.dir
        ix = np.searchsorted(t5, r.out_t + 15 * 60000) - 1 if (r.outcome == 0 and mode in ("A", "C")) else -1
        e, ia = r.close, i0
        if mode == "C" and d * (r.close - r.price) > 0:          # label price better than the close -> rest a limit there
            e = r.price
            iend = np.searchsorted(t5, r.out_t + 15 * 60000) if r.out_t > 0 else i0 + 24
            seg = (L5[i0:iend] <= e) if d == 1 else (H5[i0:iend] >= e)
            if not seg.any(): continue
            ia = i0 + int(np.argmax(seg))
        if mode == "H" and r.outcome <= 0: continue
        sl = 0.5 * r.atr
        tps = {"TP1 1.5R": e + d * 1.5 * sl, "TP2 2.5R": e + d * 2.5 * sl,
               "TP3 liquidity": r.liq if (r.liq > 0 and d * (r.liq - e) > 0) else e + d * 4 * sl}
        o = {nm: (d * (walk(d, e - d * sl, tg, ia, ia + HOLD5, ix) - e) - COST) / sl for nm, tg in tps.items()}
        o["tracker 1ATR:1ATR"] = (d * (walk(d, e - d * r.atr, e + d * r.atr, ia, ia + HOLD5, ix) - e) - COST) / r.atr
        res.append(dict(t=r.t, dir=d, outcome=r.outcome, **o))
    return pd.DataFrame(res)

if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
    rng = np.random.default_rng(11); allR = []
    names = {"A": "A pending+scratch", "B": "B pending stop/target", "C": "C pending limit@label", "H": "H HINDSIGHT (not tradable)"}
    for v in ("original", "ZONE_RULE"):
        P = load(v)
        print(f"\n######## {v}: {len(P)} pendings; became signal {np.mean(P.outcome > 0):.1%}; scratched {np.mean(P.outcome == 0):.1%}")
        for m in "ABCH":
            R = score(P, m); R["mode"] = names[m]; R["period"] = period(R.t); R["version"] = v; allR.append(R)
        idx = rng.integers(0, len(t5) - 400, len(P) * 2); ts = t5[idx] // 900000 * 900000
        Cn = pd.DataFrame(dict(t=ts, dir=rng.choice(P.dir.to_numpy(), len(ts)), close=C5[np.searchsorted(t5, ts + 15 * 60000) - 1],
                               atr=np.interp(ts, P.t, P.atr), liq=-1.0, out_t=-1, outcome=-1))
        Cn["price"] = Cn.close; Cn = Cn[(Cn.t >= P.t.min()) & (Cn.t <= P.t.max())]
        R = score(Cn, "B"); R["mode"] = "RANDOM control"; R["period"] = period(R.t); R["version"] = v; allR.append(R)
    A = pd.concat(allR); A.to_pickle(HERE / "scored_pending.pkl")
    for v in ("original", "ZONE_RULE"):
        print(f"\n================ {v} ================")
        print(summ(A[A.version == v], ["mode", "period"]).to_string())
