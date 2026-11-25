"""The owner's way: enter at an OB / FVG, don't run from heat, allow up to -$100 on 1 MGC (10 pts), hold 1-2 h for the
liquidity grab and the move back. Measured on gold 1m (HistData XAUUSD, 2025-01 -> 2026-09):
  - entries: first touch of every fresh 5m FVG (gap >= 1 pt) and of its order block (last opposite candle before the impulse),
    limit fill at the zone edge, in the zone's direction;
  - control: same direction, same minute of day, random other day (does a zone bend the odds vs. any entry?);
  - path on 1m bars: entry-bar adverse counted, entry-bar favorable not; stop counted first inside a minute; cost 0.3 pt ($3).
MGC: $10 per point."""
import numpy as np, pandas as pd
rng = np.random.default_rng(11)
a = np.load("/Users/jitheandrasubramaniam/Desktop/hey hey/research/scalp_study_2026-11-07/xau1m.npy")
t1 = a[:, 0].astype(np.int64); O1, H1, L1, C1 = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
N, COST, K = len(C1), 0.3, 240
yr1 = pd.to_datetime(t1, unit="s").year.to_numpy()

# ---- 5m bars from 1m
g = t1 // 300
st = np.r_[0, np.flatnonzero(np.diff(g)) + 1]; en = np.r_[st[1:], N]
O5, C5 = O1[st], C1[en - 1]; H5 = np.maximum.reduceat(H1, st); L5 = np.minimum.reduceat(L1, st); T5 = t1[st]
zones = []
for j in range(2, len(st) - 1):
    if T5[j] - T5[j - 2] != 600: continue                     # no gaps across breaks/weekends
    if L5[j] - H5[j - 2] >= 1.0:                               # bullish FVG
        zones.append((st[j + 1], L5[j], 1, "FVG"))
        for k in range(j - 2, max(j - 6, -1), -1):
            if C5[k] < O5[k]:
                if H5[k] < L5[j]: zones.append((st[j + 1], H5[k], 1, "OB"))
                break
    if L5[j - 2] - H5[j] >= 1.0:                               # bearish FVG
        zones.append((st[j + 1], H5[j], -1, "FVG"))
        for k in range(j - 2, max(j - 6, -1), -1):
            if C5[k] > O5[k]:
                if L5[k] > H5[j]: zones.append((st[j + 1], L5[k], -1, "OB"))
                break
ent = {}
for s, lvl, d, kind in zones:
    e = min(s + 1440, N - K - 1)
    if s >= e: continue
    hit = np.flatnonzero(L1[s:e] <= lvl) if d == 1 else np.flatnonzero(H1[s:e] >= lvl)
    if hit.size == 0: continue
    m = s + hit[0]
    if t1[min(m + K, N - 1)] - t1[m] > K * 60 + 3600: continue  # would be held over a weekend
    px = min(lvl, O1[m]) if d == 1 else max(lvl, O1[m])
    ent[(m, d, kind)] = px
Z = pd.DataFrame([(m, d, k, p) for (m, d, k), p in ent.items()], columns=["m", "d", "kind", "px"]).sort_values("m").reset_index(drop=True)

# ---- control: same direction, same minute-of-day, random other day of the same year
mod = (t1 // 60) % 1440
by = pd.Series(np.arange(N)).groupby([mod, yr1]).apply(np.array).to_dict()
ctl = []
for m, d in zip(Z.m, Z.d):
    pool = by[(mod[m], yr1[m])]; r = pool[rng.integers(len(pool))]
    if r + K < N and t1[r + K] - t1[r] <= K * 60 + 3600 and abs(int(r) - int(m)) > 1440: ctl.append((r, d, "CONTROL", O1[r]))
Cdf = pd.DataFrame(ctl, columns=["m", "d", "kind", "px"])

ADV = [2.5, 5, 7.5, 10, 15, 20]; FAV = [0.3, 2, 3, 5, 10, 20]; BIG = 10**6
def paths(df):
    m, d, px = df.m.to_numpy(), df.d.to_numpy(), df.px.to_numpy(); n = len(m)
    tA = {x: np.full(n, BIG) for x in ADV}; tF = {x: np.full(n, BIG) for x in FAV}; cl = {}
    adv0 = np.where(d == 1, px - L1[m], H1[m] - px)
    for x in ADV: tA[x][adv0 >= x] = 0
    for k in range(1, K + 1):
        j = m + k
        fav = np.where(d == 1, H1[j] - px, px - L1[j]); adv = np.where(d == 1, px - L1[j], H1[j] - px)
        for x in ADV: tA[x][(tA[x] == BIG) & (adv >= x)] = k
        for x in FAV: tF[x][(tF[x] == BIG) & (fav >= x)] = k
        if k in (60, 120, 240): cl[k] = d * (C1[j] - px)
    return tA, tF, cl
def outcome(P, T, S, L):
    tA, tF, cl = P; tt, ts = tF[T], tA[S]
    win = (tt <= L) & (tt < ts); loss = (ts <= L) & (ts <= tt)
    pts = np.where(win, T, np.where(loss, -S, cl[L]))
    exit_k = np.where(win, tt, np.where(loss, ts, L))
    return win, loss, (pts - COST) * 10, exit_k
def table(P, yrs, lab):
    rows = []
    for S in [5, 10, 15]:
        for T in [2, 3, 5, 10]:
            for L in [60, 120]:
                w, lo, usd, _ = outcome(P, T, S, L)
                for y in [2025, 2026]:
                    s = yrs == y; u = usd[s]
                    rows.append(dict(set=lab, year=y, max_loss=f"${S*10:.0f}", target=f"${T*10:.0f}", hold=f"{L//60}h", trades=s.sum(),
                                     win=w[s].mean()*100, hit_max_loss=lo[s].mean()*100, timeout=100-w[s].mean()*100-lo[s].mean()*100,
                                     avg_usd=u.mean(), PF=u[u > 0].sum() / -u[u < 0].sum()))
    return pd.DataFrame(rows)
def recovery(P, yrs, lab, S=10, L=120):
    tA, tF, _ = P; rows = []
    for X in [2.5, 5, 7.5]:
        for Y in [0.3, 2, 3, 5]:
            base = (tA[X] <= L) & (tA[X] < tF[Y])
            came = base & (tF[Y] <= L) & (tF[Y] < tA[S]); died = base & (tA[S] <= L) & (tA[S] <= tF[Y])
            for y in [2025, 2026]:
                s = yrs == y; b = base[s].sum()
                rows.append(dict(set=lab, year=y, down=f"-${X*10:.0f}", back_to=("break-even" if Y == 0.3 else f"+${Y*10:.0f}"),
                                 trades_that_went_down=b, came_back=came[s].sum()/b*100, hit_minus_100=died[s].sum()/b*100,
                                 still_open_at_2h=100-came[s].sum()/b*100-died[s].sum()/b*100))
    return pd.DataFrame(rows)
def account(P, df, yrs, T, S, L, y, start=2000.0):
    _, _, usd, ek = outcome(P, T, S, L)
    m = df.m.to_numpy(); bal, peak, mdd, free, n, path = start, start, 0.0, -1, 0, []
    for i in np.argsort(m):
        if yrs[i] != y or m[i] <= free: continue
        bal += usd[i]; n += 1; free = m[i] + ek[i]; peak = max(peak, bal); mdd = min(mdd, bal - peak); path.append(bal)
    return dict(year=y, target=f"${T*10}", max_loss=f"${S*10}", hold=f"{L//60}h", trades=n, end_balance=round(bal), worst_drawdown=round(mdd), lowest=round(min(path)) if path else start)

PZ, PC = paths(Z), paths(Cdf)
yz, yc = yr1[Z.m.to_numpy()], yr1[Cdf.m.to_numpy()]
pd.set_option("display.width", 250); pd.set_option("display.float_format", lambda v: f"{v:.1f}"); pd.set_option("display.max_rows", 500)
print("zone entries:", len(Z), Z.kind.value_counts().to_dict(), "| control entries:", len(Cdf))
tz, tc = table(PZ, yz, "ZONES (OB+FVG)"), table(PC, yc, "CONTROL (random time)")
main = pd.concat([tz, tc]); main.to_csv("outcomes.csv", index=False)
print("\n== Max loss $100, hold up to 2h ==")
print(main[(main.max_loss == "$100") & (main.hold == "2h")].to_string(index=False))
print("\n== Best avg $ of all 24 combos per set/year ==")
print(main.sort_values("avg_usd", ascending=False).groupby(["set", "year"]).head(1).to_string(index=False))
rz, rc = recovery(PZ, yz, "ZONES"), recovery(PC, yc, "CONTROL")
rec = pd.concat([rz, rc]); rec.to_csv("recovery.csv", index=False)
print("\n== Once a trade is down $X: does it come back before -$100 (within 2h of entry)? ==")
print(rec.to_string(index=False))
print("\n== $2,000 account, 1 MGC, one trade at a time, every zone touch ==")
print(pd.DataFrame([account(PZ, Z, yz, T, 10, 120, y) for y in [2025, 2026] for T in [2, 3, 5]]).to_string(index=False))
for kind in ["FVG", "OB"]:
    s = (Z.kind == kind).to_numpy(); w, lo, usd, _ = outcome(PZ, 3, 10, 120)
    for y in [2025, 2026]:
        q = s & (yz == y); u = usd[q]
        print(f"{kind} {y}: n={q.sum()} win {w[q].mean()*100:.1f} % loss {lo[q].mean()*100:.1f} % avg ${u.mean():.2f} PF {u[u>0].sum()/-u[u<0].sum():.2f}  (target $30, max loss $100, 2h)")
