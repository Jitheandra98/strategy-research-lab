"""The owner's separate setup: 18:00-18:30 range breakout (rules in SPEC.md).
MAIN = Chicago clock, ALT = fixed UTC-6 all year. Run: python3 single.py > single_results.txt"""
import numpy as np, pandas as pd
from common import (O, H, L, C, N, nS, sfirst, slast, sid, ctm, fixm, YEAR, NAN, simulate, evaluate, PERIODS, pf)

rng = np.random.default_rng(18)
R0, R1, G1 = 18 * 60, 18 * 60 + 30, 20 * 60          # range 18:00-18:30, signals 18:30-20:00, exit 20:00


def windows(clk):
    """Per session: range bar indices, signal-window bar indices (18:30..19:55)."""
    out = {}
    for s in range(nS):
        f, l = sfirst[s], slast[s]
        c = clk[f:l + 1]
        rr = np.flatnonzero((c >= R0) & (c < R1)) + f
        gg = np.flatnonzero((c >= R1) & (c < G1)) + f
        if len(rr) == 6 and len(gg) >= 2:
            out[s] = (rr, gg)
    return out


def build(win):
    sigs = []
    for s, (rr, gg) in win.items():
        rH, rL = H[rr].max(), L[rr].min(); mid = (rH + rL) / 2
        for i in gg:
            d = 1 if C[i] > rH else (-1 if C[i] < rL else 0)
            if d:
                sigs.append((i, d, mid - 0.1 if d == 1 else mid + 0.1, NAN, 2.0, gg[-1], None))
                break
    return sigs


def walk(i, d, R, lim):
    """Same trade mechanics as simulate(): entry O[i+1], stop R away, target 2R, exit at lim. Returns gross points."""
    e = i + 1; px = O[e]; stop = px - d * R; tgt = px + d * 2 * R
    for j in range(e, lim + 1):
        if d == 1:
            if j > e and O[j] <= stop: return O[j] - px
            if L[j] <= stop: return stop - px
            if H[j] >= tgt: return tgt - px
        else:
            if j > e and O[j] >= stop: return px - O[j]
            if H[j] >= stop: return px - stop
            if L[j] <= tgt: return px - tgt
    return d * (C[lim] - px)


def control(T, win, clk):
    """Same clock minute, direction, stop distance and 20:00 exit on 20 random other sessions -> mean net R."""
    keys = np.array(list(win.keys()))
    pos = {s: {clk[i]: i for i in gg} for s, (rr, gg) in win.items()}
    res = []
    for r in T.itertuples():
        s0, cm = sid[r.i], clk[r.i]; vals = []
        for s in keys[rng.integers(0, len(keys), 60)]:
            if s == s0 or cm not in pos[s]: continue
            i = pos[s][cm]; lim = win[s][1][-1]
            if i + 1 > lim: continue
            vals.append((walk(i, r.d, r.R, lim) - 0.3) / r.R)
            if len(vals) == 20: break
        res.append(np.mean(vals) if vals else np.nan)
    return np.array(res)


def show(name, T, ctrl):
    ev = evaluate(T); n3 = T.gross.to_numpy() - 0.3; rr = n3 / T.R.to_numpy()
    print(f"\n=== {name}: {ev['n']} trades ({ev['per_yr']:.0f}/yr), win {ev['win']:.1f}%, PF {ev['PF']:.2f}, "
          f"avg {ev['avg_pt']:+.2f} pt, net ${ev['usd']:+,.0f} (1 MGC, 0.3 pt); median stop ${np.median(T.R) * 10:,.0f}")
    for (a, b), key in zip(PERIODS, ["PF_12_19", "PF_20_23", "PF_24_26"]):
        m = T.year.between(a, b).to_numpy()
        print(f"  {a}-{b}: {m.sum():4d} tr  PF {ev[key]:.2f}  net ${n3[m].sum() * 10:+8,.0f}  "
              f"avg {rr[m].mean():+.3f}R vs random {np.nanmean(ctrl[m]):+.3f}R")
    print(f"  long ${ev['long_usd']:+,.0f}  short ${ev['short_usd']:+,.0f}  at 0.5 pt ${ev['usd_at_05']:+,.0f}  "
          f"years positive {ev['yrs_pos']}/15  -> {'PASS' if ev['PASS'] else 'FAIL'}")
    print("  per year:", "  ".join(f"{y}:{v * 10:+,.0f}" for y, v in pd.Series(n3).groupby(T.year.to_numpy()).sum().items()))
    return ev


if __name__ == "__main__":
    for name, clk in [("MAIN  Chicago clock 18:00-18:30 range, exit 2R / 20:00 CT", ctm),
                      ("ALT   fixed UTC-6 clock (1 h later in summer)", fixm)]:
        win = windows(clk)
        T = simulate(build(win))
        ctrl = control(T, win, clk)
        show(name, T, ctrl)
        T.assign(ctrl=ctrl).to_csv("single_" + name.split()[0].lower() + "_trades.csv", index=False)
