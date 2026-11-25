"""Stage 26: forward test of the owner's live trade (recording 2026-10-07 11.21.51 PM) — "1H sweep-and-reject".
Rules frozen in PREREGISTRATION.md (addendum 2026-10-08) before this script was run.
BUY: a 3m low inside a live bullish 1H STATION2 box sweeps the low of the last closed 1H candle; within 5 bars a 3m
close comes back above that low -> enter. Target = bottom of the nearest live bearish 1H box above. Stop A = sweep
extreme - 0.1 ATR1H, stop B = box bottom - 0.1 ATR1H. Time exit 2 h (variant 8 h). Cost 0.30. SELL mirrored.
Placebo: same rules on boxes shifted by +/-2 ATR1H (random sign, 3 draws).
usage: 26_h1_sweep.py <work_dir> <out_dir>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from zone_engine import ZoneEngine

W, OUT = Path(sys.argv[1]), Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
COST, TOLIN, BUF, RECL = 0.30, 0.25, 0.10, 5
hist = pd.read_pickle(W / "hist_2016_1m.pkl").loc[:"2020-12-31"]
mrg = pd.read_pickle(W / "merged_1m.pkl").loc["2021-01-01":"2026-09-20"]
fwd = pd.read_pickle(W / "fwd" / "duka_1m.pkl").loc["2026-09-20 00:01":]
m1 = pd.concat([hist, mrg, fwd])[["open", "high", "low", "close"]]
m1 = m1[~m1.index.duplicated()].sort_index()
agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
h1 = m1.resample("1h").agg(agg).dropna()
m3 = m1.resample("3min").agg(agg).dropna()
print("1m", m1.index[0], m1.index[-1], "1h bars", len(h1), "3m bars", len(m3), flush=True)

eng = ZoneEngine(h1, label="1h").run()
Z = eng.zones_frame(times=h1.index)
h1["atr"] = eng.atr
A1 = h1.atr.to_numpy()
Z["av"] = Z.born_time + pd.Timedelta(hours=1)
Z["en"] = (Z.end_time + pd.Timedelta(hours=1)).fillna(pd.Timestamp("2100-01-01", tz="UTC"))
Z["inv"] = (Z.inverted_time + pd.Timedelta(hours=1)).fillna(pd.Timestamp("2100-01-01", tz="UTC"))
print("1h zones", len(Z), Z.kind.value_counts().to_dict(), flush=True)

T3 = m3.index; H3, L3, C3 = (m3[k].to_numpy() for k in ["high", "low", "close"]); n3 = len(T3)
# last CLOSED 1H candle for each 3m bar: the 1h bar that ended at or before this 3m bar's open
hidx = np.searchsorted(h1.index.values, (T3 - pd.Timedelta(hours=1)).values, side="right") - 1
PL = np.where(hidx >= 0, h1.low.to_numpy()[np.clip(hidx, 0, None)], np.nan)
PH = np.where(hidx >= 0, h1.high.to_numpy()[np.clip(hidx, 0, None)], np.nan)
A = np.where(hidx >= 0, A1[np.clip(hidx, 0, None)], np.nan)
t3 = T3.values.astype("datetime64[ns]")
av = Z.av.values.astype("datetime64[ns]"); en = Z.en.values.astype("datetime64[ns]"); inv = Z.inv.values.astype("datetime64[ns]")
D0 = Z.dir.to_numpy()


def run(top, bot, tag):
    rows = []; busy = {1: -1, -1: -1}; cache = {}
    for d in (1, -1):
        cand = np.where((L3 < PL) if d == 1 else (H3 > PH))[0]
        for q in cand:
            if q <= busy[d] or np.isnan(A[q]) or q + 200 >= n3: continue
            t = t3[q]
            hk = hidx[q]
            if hk not in cache:
                ii = np.where((av <= t) & (en > t))[0]; cache.clear()
                cache[hk] = (ii, top[ii], bot[ii], np.where(inv[ii] <= t, -D0[ii], D0[ii]))
            ii, tp, bt, dirn = cache[hk]
            if not len(ii): continue
            ex = L3[q] if d == 1 else H3[q]
            if d == 1: inside = (dirn == 1) & (ex <= tp) & (ex >= bt - TOLIN * A[q])
            else: inside = (dirn == -1) & (ex >= bt) & (ex <= tp + TOLIN * A[q])
            if not inside.any(): continue
            lvl = PL[q] if d == 1 else PH[q]
            e = None
            for k in range(q, q + RECL):
                if (d == 1 and C3[k] > lvl) or (d == -1 and C3[k] < lvl): e = k; break
            if e is None: continue
            entry = C3[e]
            sw = L3[q:e + 1].min() if d == 1 else H3[q:e + 1].max()
            boxedge = bt[inside].min() if d == 1 else tp[inside].max()
            opp = dirn == -d
            if d == 1: c = bt[opp & (bt > entry)]
            else: c = tp[opp & (tp < entry)]
            if not len(c): continue
            tgt = c.min() if d == 1 else c.max()
            res = dict(time=T3[e], dir=d, entry=entry, target=tgt, room=d * (tgt - entry), atr1h=A[q], tag=tag)
            for sname, stop in (("A", sw - d * BUF * A[q]), ("B", boxedge - d * BUF * A[q])):
                risk = d * (entry - stop)
                if risk <= 0: continue
                for hname, hz in (("2h", 40), ("8h", 160)):
                    seg = slice(e + 1, min(n3, e + 1 + hz))
                    hs = (L3[seg] <= stop) if d == 1 else (H3[seg] >= stop)
                    ht = (H3[seg] >= tgt) if d == 1 else (L3[seg] <= tgt)
                    m = len(L3[seg])
                    fs = np.argmax(hs) if hs.any() else m; ft = np.argmax(ht) if ht.any() else m
                    if fs == m and ft == m: R = d * (C3[seg][-1] - entry) / risk; out = "time"
                    elif fs <= ft: R = -1.0; out = "stop"
                    else: R = d * (tgt - entry) / risk; out = "target"
                    res[f"R_{sname}{hname}"] = R - COST / risk; res[f"out_{sname}{hname}"] = out
                    res[f"risk_{sname}"] = risk
            rows.append(res); busy[d] = e + 40
    return pd.DataFrame(rows)


real = run(Z.top.to_numpy(), Z.bot.to_numpy(), "real")
rng = np.random.default_rng(7); pl = []
zat = Z.atr_birth.fillna(Z.size).to_numpy()
for k in range(3):
    sh = rng.choice([-1, 1], len(Z)) * 2 * zat
    pl.append(run(Z.top.to_numpy() + sh, Z.bot.to_numpy() + sh, f"placebo{k}"))
P = pd.concat(pl)
R = pd.concat([real, P]); R.to_pickle(OUT / "h1_sweep_trades.pkl")


def period(t):
    return np.where(t < pd.Timestamp("2021-01-01", tz="UTC"), "EXTERNAL 2016-20",
                    np.where(t < pd.Timestamp("2026-04-01", tz="UTC"), "IN-SAMPLE 2021-26/03", "FORWARD 2026-04→10"))


R["period"] = period(R.time); R["kind"] = np.where(R.tag == "real", "real", "placebo")
out = []
for (pr, kd), g in R.groupby(["period", "kind"]):
    for v in ("A2h", "A8h", "B2h", "B8h"):
        x = g[f"R_{v}"].dropna()
        out.append(dict(period=pr, boxes=kd, variant=v, n=len(x) // (3 if kd == "placebo" else 1), meanR=x.mean(),
                        ci95=1.96 * x.std() / np.sqrt(len(x)), win=(x > 0).mean(),
                        hit_target=(g[f"out_{v}"] == "target").mean(), totalR_per_set=x.sum() / (3 if kd == "placebo" else 1)))
S = pd.DataFrame(out); S.to_csv(OUT / "h1_sweep_summary.csv", index=False)
pd.set_option("display.width", 200)
print(S.round(3).to_string())
print("median room pts", real.room.median(), "median risk A", real.risk_A.median())
