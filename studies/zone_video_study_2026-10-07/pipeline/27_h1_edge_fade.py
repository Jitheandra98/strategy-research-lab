"""Stage 27: forward test of the FIRST trade in recording 2026-10-07 11.21.51 PM — "1H box-to-box edge fade, tight stop".
Rules frozen in PREREGISTRATION.md (addendum 2026-10-10) before this script was run.
SELL: price between boxes (last closed 1H close below a live bearish 1H box, a live bullish 1H box below it); limit SELL at
the bearish box bottom, filled by the first 1m bar that reaches it from below. Stop entry + 0.20 ATR1H (variant: 1.8 pt).
Target = top of the nearest live bullish 1H box below entry, only if >= 2R. Break-even after +1R (variant: none).
Time exit 8 h, cost 0.30. BUY mirrored. Placebo: boxes shifted +/-2 ATR1H (3 draws).
usage: 27_h1_edge_fade.py <work_dir> <out_dir>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from zone_engine import ZoneEngine

W, OUT = Path(sys.argv[1]), Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
COST, SK, SFIX, MINR, TMAX, REARM = 0.30, 0.20, 1.8, 2.0, 480, 0.5
hist = pd.read_pickle(W / "hist_2016_1m.pkl").loc[:"2020-12-31"]
mrg = pd.read_pickle(W / "merged_1m.pkl").loc["2021-01-01":"2026-09-20"]
fwd = pd.read_pickle(W / "fwd" / "duka_1m.pkl").loc["2026-09-20 00:01":]
m1 = pd.concat([hist, mrg, fwd])[["open", "high", "low", "close"]]
m1 = m1[~m1.index.duplicated()].sort_index()
agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
h1 = m1.resample("1h").agg(agg).dropna()
print("1m", m1.index[0], m1.index[-1], len(m1), "1h", len(h1), flush=True)

eng = ZoneEngine(h1, label="1h").run()
Z = eng.zones_frame(times=h1.index)
A1 = np.asarray(eng.atr, dtype=float)
FAR = pd.Timestamp("2100-01-01", tz="UTC")
Z["av"] = Z.born_time + pd.Timedelta(hours=1)
Z["en"] = (Z.end_time + pd.Timedelta(hours=1)).fillna(FAR)
Z["inv"] = (Z.inverted_time + pd.Timedelta(hours=1)).fillna(FAR)
print("1h zones", len(Z), flush=True)

T = m1.index.values.astype("datetime64[ns]")
H, L, C = (m1[k].to_numpy() for k in ("high", "low", "close"))
n = len(T)
# last CLOSED 1h bar for each 1m bar (1h bar labelled t closes at t+1h; 1m bar labelled s closes at s+1m)
hk = np.searchsorted(h1.index.values, (m1.index - pd.Timedelta(minutes=59)).values, side="right") - 2
hk = np.clip(hk, 0, None)
C1H = h1.close.to_numpy()[hk]
ATR = A1[hk]


def segments(top, bot):
    """Each box -> 1 or 2 segments with an effective direction (flipped after inversion)."""
    s = []
    for i, z in enumerate(Z.itertuples()):
        a, e, v = z.av.to_datetime64(), z.en.to_datetime64(), z.inv.to_datetime64()
        if v < e:
            if a < v: s.append((a, v, top[i], bot[i], z.dir))
            s.append((max(a, v), e, top[i], bot[i], -z.dir))
        elif a < e:
            s.append((a, e, top[i], bot[i], z.dir))
    S = pd.DataFrame(s, columns=["a", "e", "top", "bot", "d"])
    return S


def run(top, bot, tag):
    S = segments(top, bot)
    sa, se = S.a.values.astype("datetime64[ns]"), S.e.values.astype("datetime64[ns]")
    stp, sbt, sd = S.top.to_numpy(), S.bot.to_numpy(), S.d.to_numpy()
    cands = []
    for j in range(len(S)):
        i0, i1 = np.searchsorted(T, sa[j]), np.searchsorted(T, se[j])
        if i1 - i0 < 2: continue
        i0 = max(i0, 1)
        r = np.arange(i0, i1)
        if sd[j] == -1:   # bearish box: sell at bottom, reached from below, last 1h close below it
            edge = sbt[j]; hit = (H[r] >= edge) & (H[r - 1] < edge) & (C1H[r] < edge)
        else:
            edge = stp[j]; hit = (L[r] <= edge) & (L[r - 1] > edge) & (C1H[r] > edge)
        for k in r[hit]: cands.append((k, j))
    cands.sort()
    rows = []; busy = {1: -1, -1: -1}; last = {}
    for k, j in cands:
        d = int(sd[j])  # trade direction = box defending direction
        if k <= busy[d] or not np.isfinite(ATR[k]) or k + TMAX >= n: continue
        edge = sbt[j] if d == -1 else stp[j]; a = ATR[k]
        if j in last:   # re-arm only after price went >= 0.5 ATR away since the last trade
            f0 = last[j]
            if d == -1 and L[f0:k].min() > edge - REARM * a: continue
            if d == 1 and H[f0:k].max() < edge + REARM * a: continue
        t = T[k]
        live = (sa <= t) & (se > t) & (sd == -d)
        if d == -1: c = stp[live & (stp < edge)]
        else: c = sbt[live & (sbt > edge)]
        if not len(c): continue
        tgt = c.max() if d == -1 else c.min()
        entry = edge
        res = dict(time=pd.Timestamp(t, tz="UTC"), dir=d, entry=entry, target=tgt, room=d * (tgt - entry), atr1h=a, tag=tag)
        ok = False
        for sname, risk in (("K", SK * a), ("F", SFIX)):
            if d * (tgt - entry) < MINR * risk:
                continue
            ok = True
            stop = entry - d * risk
            seg = slice(k + 1, k + 1 + TMAX)
            hh, ll, cc = H[seg], L[seg], C[seg]; m = len(hh)
            first = lambda x: int(np.argmax(x)) if x.any() else m
            s0 = 0 if (L[k] <= stop if d == 1 else H[k] >= stop) else first(ll <= stop if d == 1 else hh >= stop)
            tt = first(hh >= tgt if d == 1 else ll <= tgt)
            b = first(hh >= entry + risk if d == 1 else ll <= entry - risk)
            for bename in ("BE", "noBE"):
                if s0 == 0 and (L[k] <= stop if d == 1 else H[k] >= stop):
                    R, out, ex = -1.0, "stop", 0
                elif bename == "noBE" or b >= s0:
                    if tt < s0: R, out, ex = d * (tgt - entry) / risk, "target", tt
                    elif s0 < m: R, out, ex = -1.0, "stop", s0
                    else: R, out, ex = d * (cc[-1] - entry) / risk, "time", m
                else:
                    after = (hh[b + 1:] <= entry) if d == 1 else (ll[b + 1:] >= entry)
                    s1 = b + 1 + int(np.argmax(after)) if after.any() else m
                    if tt < s1 and tt < m: R, out, ex = d * (tgt - entry) / risk, "target", tt
                    elif s1 < m: R, out, ex = 0.0, "be", s1
                    else: R, out, ex = d * (cc[-1] - entry) / risk, "time", m
                res[f"R_{sname}_{bename}"] = R - COST / risk
                res[f"out_{sname}_{bename}"] = out
                res[f"exit_{sname}_{bename}"] = ex
            res[f"risk_{sname}"] = risk
        if not ok: continue
        rows.append(res); last[j] = k
        busy[d] = k + 1 + res.get("exit_K_BE", res.get("exit_F_BE", 0))  # one open trade per direction
    return pd.DataFrame(rows)


real = run(Z.top.to_numpy(), Z.bot.to_numpy(), "real")
print("real trades", len(real), flush=True)
rng = np.random.default_rng(7); pl = []
zat = Z.atr_birth.fillna(Z.size).to_numpy()
for q in range(3):
    sh = rng.choice([-1, 1], len(Z)) * 2 * zat
    pl.append(run(Z.top.to_numpy() + sh, Z.bot.to_numpy() + sh, f"placebo{q}"))
    print("placebo", q, len(pl[-1]), flush=True)
R = pd.concat([real] + pl, ignore_index=True)
R.to_pickle(OUT / "h1_edge_fade_trades.pkl")


def period(t):
    return np.where(t < pd.Timestamp("2021-01-01", tz="UTC"), "EXTERNAL 2016-20",
                    np.where(t < pd.Timestamp("2026-04-01", tz="UTC"), "IN-SAMPLE 2021-26/03", "FORWARD 2026-04→10"))


R["period"] = period(R.time); R["kind"] = np.where(R.tag == "real", "real", "placebo")
out = []
for (pr, kd), g in R.groupby(["period", "kind"]):
    for v in ("K_BE", "K_noBE", "F_BE", "F_noBE"):
        x = g[f"R_{v}"].dropna(); div = 3 if kd == "placebo" else 1
        out.append(dict(period=pr, boxes=kd, variant=v, n=len(x) // div, meanR=x.mean(), ci95=1.96 * x.std() / np.sqrt(len(x)),
                        win=(x > 0).mean(), hit_target=(g[f"out_{v}"] == "target").mean(),
                        usd_per_trade_1MGC=(x * g.loc[x.index, f"risk_{v[0]}"]).mean() * 10))
S = pd.DataFrame(out); S.to_csv(OUT / "h1_edge_fade_summary.csv", index=False)
pd.set_option("display.width", 220)
print(S.round(3).to_string())
print("median room", real.room.median(), "median risk K", real.risk_K.median(), "median ATR1H", real.atr1h.median())
