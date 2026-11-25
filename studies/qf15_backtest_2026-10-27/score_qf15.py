"""Score QF15 signals with the script's own exit rules on 5m gold bars.
SL = 0.5 x ATR14(15m) from entry; TP1 = 1.5 x SL, TP2 = 2.5 x SL, TP3 = nearest untaken liquidity pool (else 4 x SL);
script's own tracker: 1 ATR stop / 1 ATR target. Max hold 50 x 15m bars, then out at market. Cost 0.35 pt round trip.
Entries: MARKET = signal bar close (what you could actually do); LIMIT = resting order at the label's 'Entry' price
for 2 h after the signal (filled at the close if the label price is already worse than the close);
CLAIMED = label price filled at signal time (not achievable; shown only because that is what the chart boxes draw).
Same-5m-bar stop+target = stop first. Control: same rules at random 15m bar closes with the same direction mix.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
COST, HOLD5, LIMWIN5 = 0.35, 150, 24
a = np.fromfile(Path.home() / "Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)
t5 = (a[:, 0] if a[0, 0] > 1e11 else a[:, 0] * 1000).astype(np.int64)
H5, L5, C5 = a[:, 2], a[:, 3], a[:, 4]

def load(v):
    rows = []
    for f in sorted((HERE / "chunks_signals").glob(f"{v}_*.json")):
        d = json.loads(f.read_text())
        if d["status"] != "ok": print("BAD CHUNK", f.name, d.get("error")); continue
        V = {k: dict(map(tuple, x)) for k, x in d["values"].items()}
        for t, c in V.get("v_sig_close", {}).items():
            buy = t in V.get("v_buy_entry", {})
            rows.append(dict(t=int(t), dir=1 if buy else -1, close=c, label_entry=(V["v_buy_entry"] if buy else V["v_sell_entry"]).get(t, c),
                             atr=V["v_atr"][t], hp=V["v_hp"][t], liq=V["v_liq"][t], valid=V["v_valid"][t]))
    return pd.DataFrame(rows).sort_values("t").reset_index(drop=True)

def walk(d, e, stop, tgt, i0, i1):
    """first event from 5m bar i0 (inclusive) to i1: returns exit price"""
    for k in range(i0, min(i1, len(C5))):
        hs = L5[k] <= stop if d == 1 else H5[k] >= stop
        ht = H5[k] >= tgt if d == 1 else L5[k] <= tgt
        if hs: return stop
        if ht: return tgt
    return C5[min(i1, len(C5)) - 1]

def trade(d, e, atr, liq, i0):
    sl = 0.5 * atr; risk = sl
    out = {}
    tps = {"TP1 1.5R": e + d * 1.5 * sl, "TP2 2.5R": e + d * 2.5 * sl,
           "TP3 liquidity": liq if (liq > 0 and d * (liq - e) > 0) else e + d * 4 * sl}
    for nm, tg in tps.items():
        x = walk(d, e, e - d * sl, tg, i0, i0 + HOLD5)
        out[nm] = (d * (x - e) - COST) / risk
    x = walk(d, e, e - d * atr, e + d * atr, i0, i0 + HOLD5)
    out["tracker 1ATR:1ATR"] = (d * (x - e) - COST) / atr
    return out

def score(df, mode):
    res = []
    for r in df.itertuples():
        i0 = np.searchsorted(t5, r.t + 15 * 60000)          # first 5m bar after the 15m signal bar closed
        if i0 >= len(C5) - 2 or not r.atr > 0: continue
        d = r.dir
        if mode == "MARKET": e, ia = r.close, i0
        elif mode == "CLAIMED": e, ia = r.label_entry, i0
        else:
            e = r.label_entry
            if d * (e - r.close) >= 0: e, ia = r.close, i0
            else:
                seg = (L5[i0:i0 + LIMWIN5] <= e) if d == 1 else (H5[i0:i0 + LIMWIN5] >= e)
                if not seg.any(): continue
                ia = i0 + int(np.argmax(seg))            # fill bar: from that bar on, stop can hit (conservative)
        res.append(dict(t=r.t, dir=d, hp=r.hp, valid=r.valid, atr=r.atr, gap=d * (r.close - r.label_entry), **trade(d, e, r.atr, r.liq, ia)))
    return pd.DataFrame(res)

def period(t):
    y = pd.to_datetime(t, unit="ms").dt.year.to_numpy()
    return np.where(y <= 2020, "1) 2016-2020", np.where(y <= 2024, "2) 2021-2024", "3) 2025-2026"))

COLS = ["TP1 1.5R", "TP2 2.5R", "TP3 liquidity", "tracker 1ATR:1ATR"]
def summ(R, by):
    g = R.groupby(by)
    rows = {}
    for k, x in g:
        row = {"trades": len(x)}
        for c in COLS:
            v = x[c]; row[f"{c} | win%"] = round(100 * (v > 0).mean(), 1); row[f"{c} | avgR"] = round(v.mean(), 3)
            row[f"{c} | ±95%"] = round(1.96 * v.std() / np.sqrt(len(v)), 3)
        rows[k] = row
    return pd.DataFrame(rows).T

if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
    rng = np.random.default_rng(7)
    allout = []
    for v in ("original", "ZONE_RULE"):
        S = load(v); print(f"\n######## {v}: {len(S)} signals  ({S.t.min() and pd.to_datetime(S.t.min(), unit='ms')} → {pd.to_datetime(S.t.max(), unit='ms')})")
        print("label Entry vs actual close at signal (points, + = label shows a better price than you could get): median",
              round(S.assign(g=S.dir * (S.close - S.label_entry)).g.median(), 2), " mean", round(S.assign(g=S.dir * (S.close - S.label_entry)).g.mean(), 2),
              " median in ATR", round((S.dir * (S.close - S.label_entry) / S.atr).median(), 2))
        for mode in ("MARKET", "LIMIT", "CLAIMED"):
            R = score(S, mode); R["period"] = period(R.t); R["version"] = v; R["mode"] = mode
            R["grade"] = np.where(R.hp == 1, "HP (★)", "normal"); R["side"] = np.where(R.dir == 1, "BUY", "SELL")
            allout.append(R)
        # control: random 15m closes, same count & direction mix, ATR from the nearest real signal
        idx = rng.integers(0, len(t5) - 400, len(S) * 3)
        ts = t5[idx] // 900000 * 900000
        C = pd.DataFrame(dict(t=ts, dir=rng.choice(S.dir.to_numpy(), len(ts)), close=C5[np.searchsorted(t5, ts + 15 * 60000) - 1],
                              atr=np.interp(ts, S.t, S.atr), liq=-1, hp=0, valid=0))
        C["label_entry"] = C.close
        C = C[(C.t >= S.t.min()) & (C.t <= S.t.max())]
        R = score(C, "MARKET"); R["period"] = period(R.t); R["version"] = v; R["mode"] = "RANDOM control"; R["grade"] = "random"; R["side"] = np.where(R.dir == 1, "BUY", "SELL")
        allout.append(R)
    A = pd.concat(allout); A.to_pickle(HERE / "scored_trades.pkl")
    for v in ("original", "ZONE_RULE"):
        print(f"\n================ {v} ================")
        print(summ(A[A.version == v], ["mode", "period"]).to_string())
        print("\n-- MARKET entry by grade / side --")
        M = A[(A.version == v) & (A["mode"] == "MARKET")]
        print(summ(M, ["grade"]).to_string()); print(summ(M, ["side"]).to_string())
