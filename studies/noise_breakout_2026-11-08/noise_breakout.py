"""NOISE BREAKOUT v1 - gold intraday momentum (rules in SPEC.md, fixed before testing).
Gold spot 5m 2012-01 -> 2026-09, New York clock. Run: python3 noise_breakout.py > results.txt"""
import numpy as np, pandas as pd

DATA = "/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64"
OUT = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/noise_breakout_2026-11-08/"
a = np.fromfile(DATA).reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
O, H, L, C = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
ny = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York")
clock = (ny.hour * 60 + ny.minute).to_numpy()
date = ny.tz_localize(None).normalize().to_numpy()
LOOKBACK, USD_PT = 14, 10.0                      # 1 MGC = $10 per point
PERIODS = [(2012, 2019), (2020, 2023), (2024, 2026)]


def sessions(start_min, nbars):
    """Complete sessions only: exactly nbars contiguous 5m bars starting at start_min."""
    idx = np.flatnonzero((clock >= start_min) & (clock < start_min + 5 * nbars))
    d = date[idx]
    brk = np.r_[0, np.flatnonzero(d[1:] != d[:-1]) + 1, len(idx)]
    days, rows = [], []
    for s, e in zip(brk[:-1], brk[1:]):
        ii = idx[s:e]
        if len(ii) == nbars and clock[ii[0]] == start_min and np.all(np.diff(clock[ii]) == 5):
            days.append(d[s]); rows.append(ii)
    return np.array(days), np.array(rows)


def run(start_min, nbars, cost):
    days, R = sessions(start_min, nbars)
    OO, HH, LL, CC = O[R], H[R], L[R], C[R]
    nd = len(days)
    opn = OO[:, 0]
    prevc = np.r_[np.nan, CC[:-1, -1]]                      # previous complete session's final close
    move = np.abs(CC / opn[:, None] - 1.0)
    cs = np.vstack([np.zeros(nbars), np.cumsum(move, axis=0)])
    sigma = np.full_like(move, np.nan)
    for d in range(LOOKBACK, nd):                           # previous 14 sessions only (not today)
        sigma[d] = (cs[d] - cs[d - LOOKBACK]) / LOOKBACK
    typ = (HH + LL + CC) / 3.0
    twap = np.cumsum(typ, axis=1) / np.arange(1, nbars + 1)
    K = nbars // 6 - 1                                       # checkpoints every 30 min, first 30 min after open
    trades = []

    def close_trade(d, pos, e_bar, e_px, x_bar, x_px, x_is_open):
        last = x_bar - 1 if x_is_open else x_bar             # bars actually held
        seg_l = LL[d, e_bar:last + 1].min() if last >= e_bar else e_px
        seg_h = HH[d, e_bar:last + 1].max() if last >= e_bar else e_px
        if x_is_open:
            seg_l, seg_h = min(seg_l, x_px), max(seg_h, x_px)
        mae = (e_px - seg_l) if pos == 1 else (seg_h - e_px)
        gross = pos * (x_px - e_px)
        trades.append((pd.Timestamp(days[d]), pos, e_bar, x_bar, e_px, x_px, gross, gross - cost, mae))

    for d in range(LOOKBACK, nd):
        if np.isnan(prevc[d]):
            continue
        hi_ref, lo_ref = max(opn[d], prevc[d]), min(opn[d], prevc[d])
        pos, e_bar, e_px = 0, None, None
        for k in range(1, K + 1):
            j = 6 * k - 1
            P = CC[d, j]
            ub, lb = hi_ref * (1 + sigma[d, j]), lo_ref * (1 - sigma[d, j])
            fill = OO[d, j + 1]
            if pos == 1 and P < max(ub, twap[d, j]):
                close_trade(d, 1, e_bar, e_px, j + 1, fill, True); pos = 0
                if P < lb: pos, e_bar, e_px = -1, j + 1, fill
            elif pos == -1 and P > min(lb, twap[d, j]):
                close_trade(d, -1, e_bar, e_px, j + 1, fill, True); pos = 0
                if P > ub: pos, e_bar, e_px = 1, j + 1, fill
            elif pos == 0:
                if P > ub: pos, e_bar, e_px = 1, j + 1, fill
                elif P < lb: pos, e_bar, e_px = -1, j + 1, fill
        if pos != 0:
            close_trade(d, pos, e_bar, e_px, nbars - 1, CC[d, -1], False)
    tr = pd.DataFrame(trades, columns=["day", "dir", "e_bar", "x_bar", "e_px", "x_px", "gross", "net", "mae"])
    tr["year"] = tr["day"].dt.year
    sess = pd.DataFrame({"day": pd.to_datetime(days), "open": opn, "close": CC[:, -1], "prevc": prevc,
                         "c_first": CC[:, 5], "c_last_start": CC[:, nbars - 7]})
    return tr, sess, nd


def stats(x):
    n = len(x)
    if n == 0:
        return dict(n=0, win=np.nan, pf=np.nan, avg=np.nan, usd=0.0, dd=0.0)
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    eq = np.cumsum(x) * USD_PT
    dd = (np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]).max()
    return dict(n=n, win=100 * (x > 0).mean(), pf=pos / neg if neg > 0 else np.inf, avg=x.mean(),
                usd=x.sum() * USD_PT, dd=dd)


def fmt(s):
    return (f"{s['n']:5d} tr  win {s['win']:4.1f}%  PF {s['pf']:4.2f}  avg {s['avg']:+6.2f} pt  "
            f"net ${s['usd']:+9,.0f}  maxDD ${s['dd']:7,.0f}")


def report(name, tr, nd, cost):
    print(f"\n=== {name}  (cost {cost} pt/round trip, 1 MGC; {nd} complete sessions) ===")
    print("ALL        ", fmt(stats(tr["net"].to_numpy())))
    for y0, y1 in PERIODS:
        print(f"{y0}-{y1}  ", fmt(stats(tr.loc[tr.year.between(y0, y1), "net"].to_numpy())))
    print("long only  ", fmt(stats(tr.loc[tr.dir == 1, "net"].to_numpy())))
    print("short only ", fmt(stats(tr.loc[tr.dir == -1, "net"].to_numpy())))
    print(f"gross (before cost) avg {tr.gross.mean():+.2f} pt/trade; trading days {tr.day.nunique()} of {nd - LOOKBACK}; "
          f"worst open loss (MAE) {tr.mae.max():.1f} pt = ${tr.mae.max() * USD_PT:,.0f}; "
          f"95th pct MAE ${np.percentile(tr.mae, 95) * USD_PT:,.0f}")


if __name__ == "__main__":
    MAIN, ALT = (8 * 60 + 30, 60), (9 * 60 + 30, 78)
    tr, sess, nd = run(*MAIN, cost=0.3)
    tr.to_csv(OUT + "trades_main.csv", index=False)
    report("MAIN  COMEX 08:30-13:30 ET", tr, nd, 0.3)

    print("\nPer year (MAIN, 0.3 pt):")
    yrs_pos = 0
    for y, g in tr.groupby("year"):
        s = stats(g["net"].to_numpy()); yrs_pos += s["usd"] > 0
        print(f"  {y}  {fmt(s)}  | long ${g.loc[g.dir == 1, 'net'].sum() * USD_PT:+7,.0f}"
              f"  short ${g.loc[g.dir == -1, 'net'].sum() * USD_PT:+7,.0f}")

    tr5, _, _ = run(*MAIN, cost=0.5)
    report("MAIN  COMEX 08:30-13:30 ET", tr5, nd, 0.5)

    # ---- pass bar (SPEC.md)
    pa = all(stats(tr.loc[tr.year.between(y0, y1), "net"].to_numpy())["pf"] >= 1.15 for y0, y1 in PERIODS)
    pb = tr.loc[tr.dir == 1, "net"].sum() > 0 and tr.loc[tr.dir == -1, "net"].sum() > 0
    pc = tr5["net"].sum() > 0
    pd_ = yrs_pos >= 9
    print(f"\nPASS BAR  a) PF>=1.15 every period: {pa}   b) long AND short profitable: {pb}   "
          f"c) profitable at 0.5 pt: {pc}   d) >=9/15 years profitable ({yrs_pos}): {pd_}")
    print("VERDICT:", "PASSES -> paper-trade bot" if (pa and pb and pc and pd_) else "FAILS -> no bot")

    # ---- context: just being long gold during the same hours every day (no cost)
    bh = (sess["close"] - sess["open"]).iloc[LOOKBACK:]
    print(f"\nContext: long gold 08:30->13:30 every day, no cost: avg {bh.mean():+.2f} pt/day, total ${bh.sum() * USD_PT:+,.0f}")

    # ---- does the underlying effect exist? early move (prev close -> 09:00) vs last half hour (13:00 -> 13:30)
    print("\nIntraday-momentum check (MAIN clock): r_first = prev 13:30 -> 09:00, r_last = 13:00 -> 13:30; "
          "rest = 09:00 -> 13:30 signed by r_first")
    s = sess.iloc[LOOKBACK:].copy()
    s["r1"] = s.c_first / s.prevc - 1; s["rl"] = s.close / s.c_last_start - 1; s["rest"] = s.close / s.c_first - 1
    s["yr"] = s.day.dt.year
    for y0, y1 in PERIODS + [(2012, 2026)]:
        g = s[s.yr.between(y0, y1)].dropna()
        r = np.corrcoef(g.r1, g.rl)[0, 1]; tstat = r * np.sqrt((len(g) - 2) / (1 - r * r))
        sr = np.sign(g.r1) * g.rest * 1e4
        print(f"  {y0}-{y1}: corr(first,last) {r:+.3f} (t {tstat:+.2f}, n {len(g)});  "
              f"rest-of-session in the early direction {sr.mean():+.2f} bp (t {sr.mean() / sr.std() * np.sqrt(len(sr)):+.2f})")

    # ---- ALT clock (the paper's own hours) as a robustness check, pre-registered
    tra, _, nda = run(*ALT, cost=0.3)
    tra.to_csv(OUT + "trades_alt.csv", index=False)
    report("ALT  equity hours 09:30-16:00 ET", tra, nda, 0.3)
    print("Per year (ALT):", "  ".join(f"{y}:{g['net'].sum() * USD_PT:+,.0f}" for y, g in tra.groupby("year")))
