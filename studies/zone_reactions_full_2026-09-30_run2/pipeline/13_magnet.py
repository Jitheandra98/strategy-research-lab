"""Stage 13 — the trader's "zones are magnets" model, tested directly.

A. MAGNET: after a zone forms, how often does price come back to it within 1/2/4/6/12 4H bars —
   and is that MORE than for any price level the same distance away? Baseline = from random start
   bars (±2000 bars around the zone's birth, same segment), probability price reaches a level at the
   same distance on the same side within the same horizon.
B. WHERE the reaction happens: for arrivals that held, how deep did price go before turning —
   near third / middle third / far third of the box / beyond the far edge (sweep) and back.
C. REVISITS: after a zone reacts once, does price come back (next 4H bars) and react again?
D. THE SETUP: 4H zone + initial rejection (5m close back outside the zone) → enter next 5m open.
   How often does price travel +30 pts (≈ $30/oz, $300 per MGC contract) and at what cost in
   adverse excursion? Simulated with a 30-pt target, and compared with RANDOM entries in the same
   direction with the SAME stop distance (so the 30 pts is not just gold's normal daily range).
Writes analysis/magnet_*.csv and prints a summary.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
A = OUT / "analysis"
rng = np.random.default_rng(11)
COST = 0.3

b = pd.read_csv(OUT / "data" / "bars_5m.csv")
b["time_ct"] = pd.to_datetime(b.time_ct, utc=True).dt.tz_convert("America/Chicago")
o, h, l, c = (b[k].to_numpy(float) for k in ["open", "high", "low", "close"])
atr = pd.Series(b.atr5).ffill().bfill().to_numpy()
seg = b.segment.to_numpy()
n = len(b)
tod = b.tod.to_numpy()
z = pd.read_csv(OUT / "zones.csv")
ev = pd.read_csv(OUT / "events.csv")
ev["time_ct"] = pd.to_datetime(ev.time_ct, utc=True).dt.tz_convert("America/Chicago")
days = np.sort(ev.time_ct.dt.date.unique())
cut = days[int(len(days) * 0.6)]
ev["split"] = np.where(ev.time_ct.dt.date < cut, "DEV", "HOLDOUT")
is4 = lambda d: (d.zone_tf == "4h") | (d.zone_kind == "4H") if "zone_tf" in d else (d.tf == "4h") | (d.kind == "4H")

# future extremes over horizon H (within segment)
def fut_ext(H):
    fmin = np.full(n, np.nan)
    fmax = np.full(n, np.nan)
    for s in np.unique(seg):
        idx = np.where(seg == s)[0]
        lo = pd.Series(l[idx][::-1]).rolling(H, min_periods=H).min().to_numpy()[::-1]
        hi = pd.Series(h[idx][::-1]).rolling(H, min_periods=H).max().to_numpy()[::-1]
        # value at position p = extreme over p..p+H-1 ; we want p+1..p+H
        fmin[idx[:-1]] = lo[1:]
        fmax[idx[:-1]] = hi[1:]
    return fmin, fmax

# ── A. magnet ────────────────────────────────────────────────────────────────
HS = {1: 48, 2: 96, 4: 192, 6: 288, 12: 576}
fx = {k: fut_ext(H) for k, H in HS.items()}
rows = []
for zr in z.itertuples():
    i0 = int(zr.born_i)
    if i0 + 1 >= n:
        continue
    d = int(zr.dir)
    dist = (c[i0] - zr.top) if d == 1 else (zr.bot - c[i0])   # distance from price to the zone's near edge
    if dist <= 0:
        continue                                                # price already inside/through
    fam = "4H" if (zr.tf == "4h" or zr.kind == "4H") else "5m"
    r = dict(zone_uid=zr.zone_uid, fam=fam, kind=zr.kind, tf=zr.tf, dir=d, dist_pts=dist, dist_atr=dist / atr[i0],
             size=zr.size)
    lo_w, hi_w = max(0, i0 - 2000), min(n - 1, i0 + 2000)
    cand = np.arange(lo_w, hi_w)
    cand = cand[seg[cand] == seg[i0]]
    samp = rng.choice(cand, size=min(300, len(cand)), replace=False) if len(cand) else cand
    for k, H in HS.items():
        fmin, fmax = fx[k]
        if np.isnan(fmin[i0]):
            r[f"rev_{k}"] = np.nan
            continue
        r[f"rev_{k}"] = float(fmin[i0] <= zr.top) if d == 1 else float(fmax[i0] >= zr.bot)
        r[f"mid_{k}"] = float(fmin[i0] <= (zr.top + zr.bot) / 2) if d == 1 else float(fmax[i0] >= (zr.top + zr.bot) / 2)
        r[f"far_{k}"] = float(fmin[i0] <= zr.bot) if d == 1 else float(fmax[i0] >= zr.top)
        s2 = samp[~np.isnan(fmin[samp])]
        if len(s2):
            if d == 1:
                r[f"base_{k}"] = float((fmin[s2] <= c[s2] - dist).mean())
            else:
                r[f"base_{k}"] = float((fmax[s2] >= c[s2] + dist).mean())
    rows.append(r)
mg = pd.DataFrame(rows)
mg.to_csv(A / "magnet_revisits.csv", index=False)
mrows = []
for fam, g in mg.groupby("fam"):
    for k in HS:
        x = g.dropna(subset=[f"rev_{k}", f"base_{k}"])
        mrows.append(dict(fam=fam, horizon_4h_bars=k, n=len(x), revisit=x[f"rev_{k}"].mean(),
                          baseline_same_distance=x[f"base_{k}"].mean(), lift=x[f"rev_{k}"].mean() - x[f"base_{k}"].mean(),
                          reach_mid=x[f"mid_{k}"].mean(), reach_far_edge=x[f"far_{k}"].mean(),
                          median_dist_pts=x.dist_pts.median()))
msum = pd.DataFrame(mrows)
msum.to_csv(A / "magnet_summary.csv", index=False)

# ── B. where the reaction happens (held arrivals) ────────────────────────────
held = ev[ev.reaction.isin(["REJECT", "SWEEP_RECLAIM"])].copy()
depth = []
for e in held.itertuples():
    j1 = int(e.i + (e.bars_to_reaction if not np.isnan(e.bars_to_reaction) else 0))
    if e.dir == 1:
        ext = l[e.i:j1 + 1].min()
        dp = (e.top - ext) / e.size
    else:
        ext = h[e.i:j1 + 1].max()
        dp = (ext - e.bot) / e.size
    depth.append(dp)
held["depth"] = depth
held["where"] = pd.cut(held.depth, [-1e9, 1 / 3, 2 / 3, 1.0, 1e9],
                       labels=["near third", "middle third", "far third / end of box", "beyond far edge (sweep)"])
held["fam"] = np.where(is4(held), "4H", "5m")
loc = held.groupby(["fam", "where"], observed=False).size().groupby(level=0).transform(lambda s: s / s.sum()).rename("share")
loc = loc.reset_index()
loc["n"] = held.groupby(["fam", "where"], observed=False).size().values
loc.to_csv(A / "magnet_reaction_location.csv", index=False)

# ── C. revisits and repeated reactions ───────────────────────────────────────
ev["held"] = ev.reaction.isin(["REJECT", "SWEEP_RECLAIM"])
ev["fam"] = np.where(is4(ev), "4H", "5m")
seq = []
for (uid), g in ev.sort_values("i").groupby("zone_uid"):
    g = g.sort_values("arrival_no")
    for k in range(len(g)):
        r = g.iloc[k]
        seq.append(dict(fam=r.fam, arrival_no=int(r.arrival_no), held=bool(r.held),
                        prev_held=(bool(g.iloc[k - 1].held) if k > 0 else None),
                        gap_4h_bars=((r.i - g.iloc[k - 1].i) / 48 if k > 0 else np.nan)))
sq = pd.DataFrame(seq)
rev = sq.groupby(["fam", "arrival_no"]).agg(n=("held", "size"), hold_rate=("held", "mean"),
                                            median_gap_4h=("gap_4h_bars", "median")).reset_index()
cond = sq[sq.arrival_no > 1].groupby(["fam", "arrival_no", "prev_held"]).held.agg(["size", "mean"]).reset_index()
rev.to_csv(A / "magnet_repeat_reactions.csv", index=False)
cond.to_csv(A / "magnet_repeat_conditional.csv", index=False)
# how many zones get a 2nd arrival at all (price comes back after the first reaction)
second = ev[ev.arrival_no == 1].groupby("fam").zone_uid.nunique()
second2 = ev[ev.arrival_no == 2].groupby("fam").zone_uid.nunique()

# ── D. the setup: 4H zone + initial rejection → +30 pts? ─────────────────────
tr = pd.read_csv(OUT / "data" / "confirmation_trades.csv")
tr = tr.merge(ev[["zone_uid", "i", "fam", "trend4_aligned", "split", "time_ct", "dir"]].rename(columns={"i": "event_i"}),
              on=["zone_uid", "event_i"])


def sim_pts(d, ei, stop, tgt_pts, max_bars):
    """target = entry + d*tgt_pts. returns (pnl_pts, reason, mfe_pts, mae_pts)."""
    e = o[ei]
    tgt = e + d * tgt_pts
    mfe = mae = 0.0
    for j in range(ei, min(n, ei + max_bars)):
        if seg[j] != seg[ei]:
            return (c[j - 1] - e) * d - COST, "SEG", mfe, mae, j
        gap = tod[j] == 17 * 60 and j > ei
        adv = (e - l[j]) if d == 1 else (h[j] - e)
        fav = (h[j] - e) if d == 1 else (e - l[j])
        if (l[j] <= stop) if d == 1 else (h[j] >= stop):
            px = (min(stop, o[j]) if d == 1 else max(stop, o[j])) if gap else stop
            return (px - e) * d - COST, "STOP", mfe, max(mae, adv), j
        if (h[j] >= tgt) if d == 1 else (l[j] <= tgt):
            return tgt_pts - COST, "TARGET", max(mfe, fav), mae, j
        mfe, mae = max(mfe, fav), max(mae, adv)
    j = min(n, ei + max_bars) - 1
    return (c[j] - e) * d - COST, "TIME", mfe, mae, j


setups = {
    "4H zone + rejection, WITH 4H trend": (tr.fam == "4H") & (tr.conf == "C1_RECLAIM") & (tr.trend4_aligned == True),
    "4H zone + rejection, AGAINST 4H trend": (tr.fam == "4H") & (tr.conf == "C1_RECLAIM") & (tr.trend4_aligned == False),
    "4H zone + rejection, any trend": (tr.fam == "4H") & (tr.conf == "C1_RECLAIM"),
    "5m zone + rejection (control)": (tr.fam == "5m") & (tr.conf == "C1_RECLAIM"),
}
drows, detail = [], []
for name, m in setups.items():
    s = tr[m].drop_duplicates(["entry_i", "tdir"]).sort_values("entry_i")
    for tgt_pts in (15, 30, 45):
        for stop_mode in ("zone", "fixed15"):
            for max_bars in (96,):
                res, base = [], []
                busy = -1
                for r in s.itertuples():
                    if r.entry_i <= busy:
                        continue                                # one position at a time
                    ei = int(r.entry_i)
                    d = int(r.tdir)
                    stop = r.stop if stop_mode == "zone" else o[ei] - d * 15
                    risk = abs(o[ei] - stop)
                    if risk < 0.2 * atr[ei]:
                        continue
                    p, why, mfe, mae, jx = sim_pts(d, ei, stop, tgt_pts, max_bars)
                    busy = jx                                   # flat again only after the exit bar
                    res.append(dict(pnl=p, why=why, risk=risk, split=r.split, day=str(r.time_ct.date())))
                    # random baseline: 10 random entries, same segment ±1500 bars, same direction and risk
                    cand = np.arange(max(1, ei - 1500), min(n - max_bars - 1, ei + 1500))
                    cand = cand[seg[cand] == seg[ei]]
                    for rb in rng.choice(cand, size=min(10, len(cand)), replace=False):
                        pb, whyb, _, _, _ = sim_pts(d, int(rb), o[rb] - d * risk, tgt_pts, max_bars)
                        base.append(pb)
                x = pd.DataFrame(res)
                if x.empty:
                    continue
                for sp in ("DEV", "HOLDOUT", "ALL"):
                    y = x if sp == "ALL" else x[x.split == sp]
                    if len(y) < 10:
                        continue
                    drows.append(dict(setup=name, target_pts=tgt_pts, stop=stop_mode, split=sp, trades=len(y),
                                      hit_target=(y.why == "TARGET").mean(), stopped=(y.why == "STOP").mean(),
                                      timed_out=(y.why == "TIME").mean(), avg_pts=y.pnl.mean(),
                                      avg_usd_per_mgc=10 * y.pnl.mean(), median_risk_pts=y.risk.median(),
                                      random_same_dir_same_stop_avg_pts=(np.mean(base) if sp == "ALL" else np.nan),
                                      trades_per_week=len(y) / (len(days) / 5) * (1 if sp == "ALL" else np.nan)))
dd = pd.DataFrame(drows)
dd.to_csv(A / "magnet_setup_30pts.csv", index=False)

# daily context: how big is gold's day in this sample?
b["date"] = b.time_ct.dt.date
dr = b.groupby("date").agg(hi=("high", "max"), lo=("low", "min"), n=("open", "size"))
dr = dr[dr.n > 150]
daily = dict(median_daily_range_pts=float((dr.hi - dr.lo).median()), p25=float((dr.hi - dr.lo).quantile(.25)),
             share_days_range_ge_30=float(((dr.hi - dr.lo) >= 30).mean()))

pd.set_option("display.width", 250)
print("DAILY", daily)
print("\nA. MAGNET\n", msum.round(3).to_string())
print("\nB. WHERE HELD ARRIVALS TURNED\n", loc.round(3).to_string())
print("\nC. REPEAT ARRIVALS\n", rev.round(3).to_string())
print(cond.round(3).to_string())
print("zones with 1st arrival", second.to_dict(), "with 2nd arrival", second2.to_dict())
print("\nD. SETUP\n", dd.round(3).to_string())
pd.Series(daily).to_csv(A / "magnet_daily_range.csv")
