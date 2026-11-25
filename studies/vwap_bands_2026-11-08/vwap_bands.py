"""Owner's "five blue lines" plan (Desk Context session VWAP ± 1/2 SD). Rules in SPEC.md, written before testing.
Gold spot 5m 2012-2026 (no volume -> equal-weight lines, Desk Context's own no-volume fallback). Run: python3 vwap_bands.py > results.txt"""
import json, sys
import numpy as np, pandas as pd

sys.path.insert(0, "/Users/jitheandrasubramaniam/Desktop/hey hey/research/catalog_100_2026-11-08")
from common import O, H, L, C, N, t, sid, nS, sfirst, slast, YEAR, ctm, evaluate, pf

OUT = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/vwap_bands_2026-11-08/"
Ol, Hl, Ll, Cl = O.tolist(), H.tolist(), L.tolist(), C.tolist()

# ---- session VWAP (equal weight) and SD of hlc3 since the 18:00 ET anchor
x = (H + L + C) / 3
g = pd.Series(x).groupby(sid)
cnt = g.cumcount().to_numpy() + 1
m1 = g.cumsum().to_numpy() / cnt
m2 = pd.Series(x * x).groupby(sid).cumsum().to_numpy() / cnt
VW, SD = m1, np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
same = np.r_[False, sid[1:] == sid[:-1]]
VWp = np.where(same, np.r_[np.nan, VW[:-1]], np.nan)          # line values known at the start of each bar
SDp = np.where(same, np.r_[np.nan, SD[:-1]], np.nan)
VWl, SDl = VWp.tolist(), SDp.tolist()

utcm = (t // 60) % 1440                                       # UTC minute of day
nym = (ctm + 60) % 1440                                       # New York minute of day (CT + 1h all year)


def bias(s, strict):
    f, l = sfirst[s], slast[s]
    tk = np.flatnonzero(utcm[f:l + 1] < 60) + f
    tk = tk[(tk > f)]                                          # inside the session, after its first bar
    if len(tk) != 12: return 0, None
    c, up1, dn1, up2, dn2 = C[tk], (VW + SD)[tk], (VW - SD)[tk], (VW + 2 * SD)[tk], (VW - 2 * SD)[tk]
    if strict:
        if np.all((c > up1) & (c < up2)): return 1, tk[-1]
        if np.all((c < dn1) & (c > dn2)): return -1, tk[-1]
    else:
        if np.all(c > up1): return 1, tk[-1]
        if np.all(c < dn1): return -1, tk[-1]
    return 0, tk[-1]


def trade_day(s, d, entry_k, tgt_k):
    """entry_k 0 = center line, 1 = one line beyond. tgt_k 1 or 2 = SD line in the trend direction. Returns a trade or None."""
    f, l = sfirst[s], slast[s]
    for j in np.flatnonzero((nym[f:l + 1] >= 480) & (nym[f:l + 1] < 720)) + f:
        v, sd = VWl[j], SDl[j]
        if not (sd == sd): continue
        lvl = v - d * entry_k * sd
        touched = (Ol[j] > lvl and Ll[j] <= lvl) if d == 1 else (Ol[j] < lvl and Hl[j] >= lvl)
        if not touched: continue
        stop = v - d * (entry_k + 1) * sd - d * 0.1
        tgt = v + d * tgt_k * sd
        R = d * (lvl - stop)
        if R < 0.2: return None
        if (d == 1 and Ll[j] <= stop) or (d == -1 and Hl[j] >= stop):
            return (j, j, d, lvl, stop, R, tgt)
        for m in range(j + 1, l + 1):
            if d == 1:
                if Ol[m] <= stop: return (j, m, d, lvl, Ol[m], R, tgt)
                if Ll[m] <= stop: return (j, m, d, lvl, stop, R, tgt)
                if Hl[m] >= tgt: return (j, m, d, lvl, tgt, R, tgt)
            else:
                if Ol[m] >= stop: return (j, m, d, lvl, Ol[m], R, tgt)
                if Hl[m] >= stop: return (j, m, d, lvl, stop, R, tgt)
                if Ll[m] <= tgt: return (j, m, d, lvl, tgt, R, tgt)
        return (j, l, d, lvl, Cl[l], R, tgt)
    return None


def run(entry_k, tgt_k, strict=False):
    rows, diag = [], []
    for s in range(1, nS):
        d, k01 = bias(s, strict)
        if d == 0: continue
        diag.append((s, d, d * (C[slast[s]] - C[k01]), YEAR[k01]))
        tr = trade_day(s, d, entry_k, tgt_k)
        if tr is not None:
            j, x, dd, px, xp, R, tgt = tr
            rows.append((j, x, dd, px, xp, dd * (xp - px), R, abs(tgt - px), YEAR[j]))
    T = pd.DataFrame(rows, columns=["i", "x", "d", "entry", "exit", "gross", "R", "tgt_dist", "year"])
    Dg = pd.DataFrame(diag, columns=["s", "d", "move", "year"])
    return T, Dg


NAMES = {"E1T1": "Center line entry, target +1 line", "E1T2": "Center line entry, target +2 line",
         "E2T1": "Next-line entry, target +1 line", "E2T2": "Next-line entry, target +2 line"}

if __name__ == "__main__":
    ny = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York"); ym_bar = (ny.year * 100 + ny.month).to_numpy()
    months = [y * 100 + m for y in range(2012, 2027) for m in range(1, 13) if y * 100 + m <= 202609]
    pos = {v: q for q, v in enumerate(months)}
    chart = {}
    for key, (ek, tk) in {"E1T1": (0, 1), "E1T2": (0, 2), "E2T1": (1, 1), "E2T2": (1, 2)}.items():
        T, Dg = run(ek, tk); ev = evaluate(T); n3 = T.gross.to_numpy() - 0.3
        if key == "E1T1":
            nb = len(Dg); up = (Dg.move > 0).mean() * 100; mv = Dg.move.mean(); tt = mv / Dg.move.std() * np.sqrt(nb)
            print(f"BIAS (MAIN): {nb} bias days in {Dg.year.nunique()} years ({nb / Dg.year.nunique():.0f}/yr; "
                  f"{(Dg.d == 1).sum()} buy days, {(Dg.d == -1).sum()} sell days)")
            print(f"  does it predict the day? 01:00 UTC -> 16:55 ET moved WITH the bias on {up:.1f}% of days; "
                  f"average {mv:+.2f} pt in the bias direction (t {tt:+.2f})")
            for a, b in [(2012, 2019), (2020, 2023), (2024, 2026)]:
                q = Dg[Dg.year.between(a, b)]
                print(f"    {a}-{b}: {len(q)} days, with-bias {100 * (q.move > 0).mean():.1f}%, avg {q.move.mean():+.2f} pt")
            print(f"  NY touched the center line on {100 * len(T) / nb:.1f}% of bias days (that's when a trade happens)")
        print(f"\n=== {key}: {NAMES[key]} — {ev['n']} trades ({ev['per_yr']:.0f}/yr), win {ev['win']:.1f}%, PF {ev['PF']:.2f}, "
              f"net ${ev['usd']:+,.0f}, avg ${ev['avg_pt'] * 10:+.2f}/trade, before fees {(T.gross / T.R).mean():+.3f}R")
        print(f"    periods PF {ev['PF_12_19']:.2f} / {ev['PF_20_23']:.2f} / {ev['PF_24_26']:.2f}   long ${ev['long_usd']:+,.0f}  "
              f"short ${ev['short_usd']:+,.0f}  at 0.5 pt ${ev['usd_at_05']:+,.0f}  years+ {ev['yrs_pos']}/15  -> "
              f"{'PASS' if ev['PASS'] else 'FAIL'}")
        r = T.gross / T.R
        print(f"    median SL ${T.R.median() * 10:,.0f}  median TP ${T.tgt_dist.median() * 10:,.0f}  "
              f"(reward:risk {T.tgt_dist.median() / T.R.median():.2f})  | hit TP {100 * np.isclose(T.gross, T.tgt_dist, atol=0.02).mean():.0f}%  "
              f"hit SL {100 * (r <= -0.99).mean():.0f}%  closed at 16:55 {100 * ((r > -0.99) & ~np.isclose(T.gross, T.tgt_dist, atol=0.02)).mean():.0f}%")
        print("    per year:", "  ".join(f"{y}:{v * 10:+,.0f}" for y, v in pd.Series(n3).groupby(T.year.to_numpy()).sum().items()))
        T.to_csv(OUT + f"trades_{key}.csv", index=False)
        gs, ns = np.zeros(len(months)), np.zeros(len(months), int)
        idx = np.array([pos[v] for v in ym_bar[T.i.to_numpy()]])
        np.add.at(gs, idx, T.gross.to_numpy() * 10); np.add.at(ns, idx, 1)
        chart[key] = {"gross": np.round(gs, 1).tolist(), "n": ns.tolist()}
    T, Dg = run(0, 1, strict=True); ev = evaluate(T)
    print(f"\n=== STRICT bias (closes between the 1 and 2 SD lines), E1T1: {len(Dg)} bias days, {ev['n']} trades, "
          f"win {ev['win']:.1f}%, PF {ev['PF']:.2f}, net ${ev['usd']:+,.0f}, years+ {ev['yrs_pos']}/15 -> {'PASS' if ev['PASS'] else 'FAIL'}; "
          f"bias moved with the day {100 * (Dg.move > 0).mean():.1f}%, avg {Dg.move.mean():+.2f} pt")
    json.dump(chart, open(OUT + "chart_data.json", "w"), separators=(",", ":"))
