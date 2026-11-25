"""SPIKE FOLLOW v1 - rules in SPEC.md (fixed before testing). Gold spot 5m 2012-01 -> 2026-09 resampled to 30m, NY clock.
Run: python3 spike_follow.py > results.txt"""
import numpy as np, pandas as pd

DATA = "/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64"
OUT = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/spike_follow_2026-11-08/"
rng = np.random.default_rng(8)
a = np.fromfile(DATA).reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
df = pd.DataFrame(a[:, 1:], columns=list("ohlc"),
                  index=pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York"))
b = df.resample("30min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
O, H, L, C = (b[k].to_numpy() for k in "ohlc"); N = len(C); idx = b.index
clock = (idx.hour * 60 + idx.minute).to_numpy()
assert set(np.unique(clock % 30)) == {0}
date = idx.tz_localize(None).normalize().to_numpy()
yr = idx.year.to_numpy()
pc = np.r_[C[0], C[:-1]]
tr = np.maximum(H - L, np.maximum(np.abs(H - pc), np.abs(L - pc)))
atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
atrp = np.r_[atr[0], atr[:-1]]                                   # previous bar's ATR (trigger)
COST, USD = 0.3, 10.0
PERIODS = [(2012, 2019), (2020, 2023), (2024, 2026)]
HALF = pd.Timedelta(minutes=30)
x1300 = np.flatnonzero(clock == 13 * 60)
i1300 = dict(zip(date[x1300], x1300))                             # bar 13:00-13:30 of each date
spike = (clock >= 8 * 60) & (clock <= 10 * 60) & ((H - L) >= 2.5 * atrp) & (C != O)
spikes = np.flatnonzero(spike)


def ride(k, d, stop, x_i):
    """Enter at O[k+1]; walk bars k+1..x_i; stop first (gap-through exits at the open); else exit at C[x_i]."""
    px = O[k + 1]
    for j in range(k + 1, x_i + 1):
        if d == 1:
            if O[j] <= stop: return O[j] - px
            if L[j] <= stop: return stop - px
        else:
            if O[j] >= stop: return px - O[j]
            if H[j] >= stop: return px - stop
    return d * (C[x_i] - px)


def tradable(k):
    return k + 1 < N and idx[k + 1] - idx[k] == HALF and date[k + 1] == date[k] and i1300.get(date[k], -1) > k


pool = {c: np.flatnonzero(clock == c) for c in range(8 * 60, 10 * 60 + 1, 30)}


def control(k, d, R):
    """Same clock, direction, stop distance and 13:30 exit on 20 random other days (net R)."""
    p, out = pool[clock[k]], []
    for r in p[rng.integers(0, len(p), 80)]:
        if date[r] == date[k] or not tradable(r): continue
        out.append((ride(r, d, O[r + 1] - d * R, i1300[date[r]]) - COST) / R)
        if len(out) == 20: break
    return np.mean(out) if out else np.nan


# ---------------- MAIN: first spike of the day, ride to 13:30
rows, seen = [], set()
for k in spikes:
    if date[k] in seen: continue
    seen.add(date[k])
    if not tradable(k): continue
    d = 1 if C[k] > O[k] else -1
    stop = L[k] - 0.1 * atr[k] if d == 1 else H[k] + 0.1 * atr[k]
    R = d * (O[k + 1] - stop)
    if R <= 0: continue
    rows.append(dict(day=pd.Timestamp(date[k]), year=yr[k], clock=clock[k], d=d, R=R,
                     gross=ride(k, d, stop, i1300[date[k]]), ctrl=control(k, d, R)))
M = pd.DataFrame(rows)


def stats(x):
    n = len(x)
    if n == 0: return dict(n=0, win=np.nan, pf=np.nan, avg=np.nan, usd=0.0, dd=0.0)
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    eq = np.r_[0, np.cumsum(x)] * USD
    return dict(n=n, win=100 * (x > 0).mean(), pf=pos / neg if neg > 0 else np.inf, avg=x.mean(), usd=x.sum() * USD,
                dd=(np.maximum.accumulate(eq) - eq).max())


def fmt(s):
    return (f"{s['n']:5d} tr  win {s['win']:4.1f}%  PF {s['pf']:4.2f}  avg {s['avg']:+6.2f} pt  "
            f"net ${s['usd']:+9,.0f}  maxDD ${s['dd']:7,.0f}")


def block(T, cost, title, with_ctrl):
    T = T.copy(); T["net"] = T.gross - cost; T["r"] = T.net / T.R
    print(f"\n=== {title}  (cost {cost} pt, 1 MGC; {len(T)} trades, {len(T) / T.year.nunique():.0f}/yr, "
          f"median stop ${T.R.median() * USD:,.0f}) ===")
    sel = [("ALL       ", T)] + [(f"{y0}-{y1} ", T[T.year.between(y0, y1)]) for y0, y1 in PERIODS] + \
          [("long only ", T[T.d == 1]), ("short only", T[T.d == -1])]
    for name, g in sel:
        line = name + " " + fmt(stats(g.net.to_numpy()))
        if with_ctrl:
            line += f"  | avg {g.r.mean():+.3f}R vs random {g.ctrl.mean():+.3f}R -> edge {g.r.mean() - g.ctrl.mean():+.3f}R"
        print(line)
    return T


if __name__ == "__main__":
    T3 = block(M, 0.3, "MAIN  spike follow -> 13:30", True)
    print("\nPer year (MAIN, 0.3 pt):")
    yrs_pos = 0
    for y, g in T3.groupby("year"):
        s = stats(g.net.to_numpy()); yrs_pos += s["usd"] > 0
        print(f"  {y}  {fmt(s)}  | long ${g[g.d == 1].net.sum() * USD:+7,.0f}  short ${g[g.d == -1].net.sum() * USD:+7,.0f}")
    T5 = block(M, 0.5, "MAIN  spike follow -> 13:30", False)
    print("\nDiagnostic only (NOT for picking): by spike start time, 0.3 pt")
    for c, g in T3.groupby("clock"):
        print(f"  {c // 60:02d}:{c % 60:02d}  " + fmt(stats(g.net.to_numpy())))

    pa = all(stats(T3[T3.year.between(y0, y1)].net.to_numpy())["pf"] >= 1.15 for y0, y1 in PERIODS)
    pb = T3[T3.d == 1].net.sum() > 0 and T3[T3.d == -1].net.sum() > 0
    pc = T5.net.sum() > 0
    pd_ = yrs_pos >= 9
    pe = all((g.r.mean() - g.ctrl.mean()) > 0 for g in (T3[T3.year.between(y0, y1)] for y0, y1 in PERIODS))
    print(f"\nPASS BAR  a) PF>=1.15 every period: {pa}  b) long AND short profitable: {pb}  c) profitable at 0.5 pt: {pc}  "
          f"d) >=9/15 years ({yrs_pos}): {pd_}  e) beats random every period: {pe}")
    print("VERDICT:", "PASSES -> paper-trade bot only" if all([pa, pb, pc, pd_, pe]) else "FAILS -> no bot")
    T3.to_csv(OUT + "trades_main.csv", index=False)

    # ---------------- ALT: exact mirror of the losing fade (every spike bar)
    alt = []
    for k in spikes:
        if k + 8 >= N: continue
        d = 1 if C[k] > O[k] else -1
        Rf = (H[k] + 0.1 * atr[k] - C[k]) if d == 1 else (C[k] - L[k] + 0.1 * atr[k])   # the fade's stop distance
        if Rf <= 0: continue
        px = C[k]; tgt = px + d * Rf; stop = px - d * 2 * Rf; res = None
        for j in range(k + 1, k + 9):
            if d == 1:
                if L[j] <= stop: res = stop - px; break
                if H[j] >= tgt: res = tgt - px; break
            else:
                if H[j] >= stop: res = px - stop; break
                if L[j] <= tgt: res = px - tgt; break
        if res is None: res = d * (C[k + 8] - px)
        alt.append(dict(year=yr[k], d=d, R=2 * Rf, gross=res))
    A = pd.DataFrame(alt)
    block(A, 0.3, "ALT  exact mirror of the fade (target = fade stop, stop = fade 2R, 4h)", False)
    A3 = A.assign(net=A.gross - 0.3)
    print("Per year (ALT):", "  ".join(f"{y}:{g.net.sum() * USD:+,.0f}" for y, g in A3.groupby("year")))
