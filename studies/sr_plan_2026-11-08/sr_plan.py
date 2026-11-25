"""Owner's support/resistance plan (rules in SPEC.md, written before testing). Gold spot 5m 2012-2026.
One rule: price comes DOWN to a level -> buy it; comes UP to a level -> sell it; stop = level +/- buffer; target = next level.
Run: python3 sr_plan.py > results.txt"""
import bisect, json, sys
import numpy as np, pandas as pd

sys.path.insert(0, "/Users/jitheandrasubramaniam/Desktop/hey hey/research/catalog_100_2026-11-08")
from common import O, H, L, C, N, t, sid, nS, sfirst, slast, sH, sL, sC, YEAR, evaluate, rma, PERIODS, pf

OUT = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/sr_plan_2026-11-08/"
Ol, Hl, Ll, Cl = O.tolist(), H.tolist(), L.tolist(), C.tolist()

# ---- 1-hour bars (UTC hours) for the buffer ATR and the swing levels
hb = t // 3600
h_last = np.flatnonzero(np.r_[hb[1:] != hb[:-1], True]); h_first = np.r_[0, h_last[:-1] + 1]
H1, L1, C1 = np.maximum.reduceat(H, h_first), np.minimum.reduceat(L, h_first), C[h_last]
pc1 = np.r_[C1[0], C1[:-1]]
ATR1 = rma(np.maximum(H1 - L1, np.maximum(np.abs(H1 - pc1), np.abs(L1 - pc1))), 14)
hour_of = lambda i: np.searchsorted(h_last, i, side="left")
BUF = np.full(nS, np.nan)
BUF[1:] = ATR1[hour_of(sfirst[1:] - 1)]                  # 1H ATR at the end of the previous session

k = 3
s1h, s1l = pd.Series(H1), pd.Series(L1)
ph = np.flatnonzero(((s1h > s1h.rolling(k).max().shift(1)) & (s1h > s1h[::-1].rolling(k).max().shift(1)[::-1])).to_numpy())
pl = np.flatnonzero(((s1l < s1l.rolling(k).min().shift(1)) & (s1l < s1l[::-1].rolling(k).min().shift(1)[::-1])).to_numpy())
SW = {}                                                   # session -> list of (confirm_bar, price)
for hh, arr in ((ph, H1), (pl, L1)):
    for p in hh:
        if p + k >= len(h_last): continue
        SW.setdefault(sid[h_last[p]], []).append((h_last[p + k], arr[p]))


def levels(kind, s):
    if kind == "A":
        return [x for q in range(1, 6) for x in (sH[s - q], sL[s - q])]
    if kind == "B":
        return [p for q in range(1, 6) for cb, p in SW.get(s - q, []) if cb < sfirst[s]]
    Hp, Lp, Cp = sH[s - 1], sL[s - 1], sC[s - 1]; P = (Hp + Lp + Cp) / 3
    return [P, 2 * P - Lp, 2 * P - Hp, P + (Hp - Lp), P - (Hp - Lp), Hp + 2 * (P - Lp), Lp - 2 * (Hp - P)]


def merge(lv, gap):
    lv = sorted(lv); out = []; grp = [lv[0]]
    for x in lv[1:]:
        if x - grp[-1] < gap: grp.append(x)
        else: out.append(sum(grp) / len(grp)); grp = [x]
    out.append(sum(grp) / len(grp))
    return out


def run(kind, mult):
    rows = []
    for s in range(5, nS):
        buf = BUF[s] * mult
        if not buf > 0: continue
        raw = levels(kind, s)
        if len(raw) < 2: continue
        lv = merge(raw, buf)
        if len(lv) < 2: continue
        f, l = sfirst[s], slast[s]
        role = [1 if x > Ol[f] else -1 for x in lv]       # 1 = resistance at the open, -1 = support
        j = f
        while j <= l:
            o, h, lo = Ol[j], Hl[j], Ll[j]
            ku = bisect.bisect_right(lv, o); kd = bisect.bisect_left(lv, o) - 1
            up = ku < len(lv) and lv[ku] <= h
            dn = kd >= 0 and lv[kd] >= lo
            if up == dn:                                  # nothing touched, or both sides touched (order unknown)
                j += 1; continue
            if up:
                d, kk = -1, ku; px = lv[ku]; stop = px + buf; ti = ku - 1
            else:
                d, kk = 1, kd; px = lv[kd]; stop = px - buf; ti = kd + 1
            if ti < 0 or ti >= len(lv):
                j += 1; continue
            tgt = lv[ti]; x = None
            if (d == -1 and h >= stop) or (d == 1 and lo <= stop):
                x, xp = j, stop
            else:
                for m in range(j + 1, l + 1):
                    if d == -1:
                        if Ol[m] >= stop: x, xp = m, Ol[m]; break
                        if Hl[m] >= stop: x, xp = m, stop; break
                        if Ll[m] <= tgt: x, xp = m, tgt; break
                    else:
                        if Ol[m] <= stop: x, xp = m, Ol[m]; break
                        if Ll[m] <= stop: x, xp = m, stop; break
                        if Hl[m] >= tgt: x, xp = m, tgt; break
                if x is None: x, xp = l, Cl[l]
            rows.append((j, x, d, px, xp, d * (xp - px), buf, abs(tgt - px), "RANGE" if role[kk] == -d else "FLIP", YEAR[j]))
            j = x + 1
    return pd.DataFrame(rows, columns=["i", "x", "d", "entry", "exit", "gross", "R", "tgt_dist", "kind", "year"])


NAMES = {"A": "Daily highs/lows (last 5 days)", "B": "1-hour swing highs/lows", "C": "Daily floor pivots"}

if __name__ == "__main__":
    chart = {}
    ny = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York"); ym_bar = (ny.year * 100 + ny.month).to_numpy()
    for kind in "ABC":
        for mult in (0.5, 0.25, 1.0):
            T = run(kind, mult); ev = evaluate(T); n3 = T.gross.to_numpy() - 0.3
            gR = (T.gross / T.R).mean()
            tag = "MAIN" if mult == 0.5 else "check"
            print(f"\n=== {kind}. {NAMES[kind]}  buffer {mult} x 1H ATR [{tag}]: {ev['n']:,} trades ({ev['per_yr']:.0f}/yr), "
                  f"win {ev['win']:.1f}%, PF {ev['PF']:.2f}, net ${ev['usd']:+,.0f}, before fees {gR:+.3f}R/trade")
            print(f"    periods PF {ev['PF_12_19']:.2f} / {ev['PF_20_23']:.2f} / {ev['PF_24_26']:.2f}   long ${ev['long_usd']:+,.0f}  "
                  f"short ${ev['short_usd']:+,.0f}  at 0.5 pt ${ev['usd_at_05']:+,.0f}  years+ {ev['yrs_pos']}/15  -> "
                  f"{'PASS' if ev['PASS'] else 'FAIL'}")
            print(f"    median stop ${T.R.median() * 10:,.0f}  median target ${T.tgt_dist.median() * 10:,.0f}  "
                  f"(reward:risk {T.tgt_dist.median() / T.R.median():.1f})")
            for kd in ("RANGE", "FLIP"):
                g = T[T.kind == kd]; x = g.gross.to_numpy() - 0.3
                print(f"    {kd:5s} {len(g):6,d} tr  win {100 * (x > 0).mean():4.1f}%  PF {pf(x):.2f}  net ${x.sum() * 10:+10,.0f}  "
                      f"before fees {(g.gross / g.R).mean():+.3f}R")
            if mult == 0.5:
                T.to_csv(OUT + f"trades_{kind}.csv", index=False)
                print("    per year:", "  ".join(f"{y}:{v * 10:+,.0f}" for y, v in pd.Series(n3).groupby(T.year.to_numpy()).sum().items()))
                months = [y * 100 + m for y in range(2012, 2027) for m in range(1, 13) if y * 100 + m <= 202609]
                pos = {v: q for q, v in enumerate(months)}
                gs, ns = np.zeros(len(months)), np.zeros(len(months), int)
                idx = np.array([pos[v] for v in ym_bar[T.i.to_numpy()]])
                np.add.at(gs, idx, T.gross.to_numpy() * 10); np.add.at(ns, idx, 1)
                chart[kind] = {"label": NAMES[kind], "gross": np.round(gs, 1).tolist(), "n": ns.tolist()}
    json.dump(chart, open(OUT + "chart_data.json", "w"), separators=(",", ":"))
