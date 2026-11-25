"""Follow-ups: (1) a human pace — one zone trade per day, first zone touch 08:00-11:00 New York (HistData clock is EST, no DST);
(2) when would a $2,000 account hit $0; (3) the owner's own STATION/QF replay signals (MGC futures 5m, Sep 22 - Oct 20 2026)
under the same rule: max loss $100 (10 pts), hold up to 2 h, targets $20-$100."""
import json, numpy as np, pandas as pd
exec(open("heat.py").read().split("PZ, PC = paths(Z), paths(Cdf)")[0])   # reuse data, zones and helpers (no printing)
PZ = paths(Z); yz = yr1[Z.m.to_numpy()]
hod = ((t1 // 60) % 1440) // 60
day = t1 // 86400
first = Z[(hod[Z.m] >= 8) & (hod[Z.m] < 11)].groupby(day[Z.m[(hod[Z.m] >= 8) & (hod[Z.m] < 11)]]).head(1).index.to_numpy()
print("one trade per day (first zone touch 08-11 NY):", len(first), "days")
rows = []
for T in [2, 3, 5, 10]:
    w, lo, usd, _ = outcome(PZ, T, 10, 120)
    for y in [2025, 2026]:
        idx = first[yz[first] == y]; u = usd[idx]
        bal = 2000 + np.cumsum(u); ruin = np.flatnonzero(bal <= 0)
        rows.append(dict(year=y, target=f"${T*10}", trades=len(u), win=w[idx].mean()*100, lost_100=lo[idx].mean()*100,
                         avg_usd=u.mean(), PF=u[u > 0].sum()/-u[u < 0].sum(), year_total=u.sum(), end_of_2000=2000+u.sum(),
                         lowest=bal.min(), account_gone_after=(f"{ruin[0]+1} trades" if ruin.size else "never")))
pd.set_option("display.width", 250); pd.set_option("display.float_format", lambda v: f"{v:.1f}")
print(pd.DataFrame(rows).to_string(index=False))

# every-touch account: when does it hit zero?
for T in [2, 3, 5]:
    _, _, usd, ek = outcome(PZ, T, 10, 120)
    for y in [2025, 2026]:
        bal, free, n = 2000.0, -1, 0
        for i in np.argsort(Z.m.to_numpy()):
            if yz[i] != y or Z.m[i] <= free: continue
            bal += usd[i]; n += 1; free = Z.m[i] + ek[i]
            if bal <= 0:
                print(f"every zone touch, target ${T*10}, {y}: $2,000 gone after {n} trades, on {pd.to_datetime(t1[Z.m[i]], unit='s').date()}"); break

# his own replay signals on MGC futures 5m
B = np.array(json.load(open("/Users/jitheandrasubramaniam/Desktop/hey hey/research/replay_live_2026-11-01/mgc5m_bars.json")))
Tb, Hb, Lb, Cb = B[:, 0], B[:, 2], B[:, 3], B[:, 4]
sig = [json.loads(l) for l in open("/Users/jitheandrasubramaniam/Desktop/hey hey/research/replay_live_2026-11-01/signals.jsonl")]
res = []
for s in sig:
    i0 = np.searchsorted(Tb, s["t"])
    if i0 + 24 >= len(Tb): continue
    d, e = s["dir"], s["entry"]
    for T in [2, 3, 5, 10]:
        out = None
        for k in range(i0, i0 + 24):
            adv = (e - Lb[k]) if d == 1 else (Hb[k] - e); fav = (Hb[k] - e) if d == 1 else (e - Lb[k])
            if adv >= 10: out = -10; break
            if fav >= T: out = T; break
        if out is None: out = d * (Cb[i0 + 23] - e)
        res.append(dict(kind=s["kind"], target=f"${T*10}", usd=(out - COST) * 10, win=out == T, lost=out == -10))
r = pd.DataFrame(res)
g = r.groupby(["target"]).agg(trades=("usd", "size"), win=("win", "mean"), lost_100=("lost", "mean"), avg_usd=("usd", "mean"),
                              PF=("usd", lambda u: u[u > 0].sum() / -u[u < 0].sum()))
g[["win", "lost_100"]] *= 100
print("\nHis STATION + QF replay signals (MGC 5m, Sep 22 - Oct 20 2026), max loss $100, hold 2h:"); print(g.to_string())
k = r[r.target == "$30"].groupby("kind").agg(trades=("usd", "size"), win=("win", "mean"), avg_usd=("usd", "mean"),
                                             PF=("usd", lambda u: u[u > 0].sum() / -u[u < 0].sum()))
k["win"] *= 100
print("\n  by signal type, target $30:"); print(k.to_string())
