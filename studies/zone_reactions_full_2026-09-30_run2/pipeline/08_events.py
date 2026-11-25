"""Stage 8 — zone-reaction event log, outcomes, and confirmation trades.

Definitions are fixed here BEFORE looking at results (see ../backtest_spec.md):

ARRIVAL  bar i > availability bar where price enters the zone from its correct side
         demand: low[i] <= top and low[i-1] > top ;  supply: high[i] >= bot and high[i-1] < bot
         only while the zone is intact (no 5m close beyond its far edge yet); max 3 per zone.
REACTION (within 24 bars after the arrival bar, 5m closes):
         REJECT        >= +1 ATR move away (zone direction, from the near edge) before any close beyond far edge
         SWEEP_RECLAIM wick beyond far edge, close back inside/outside within 2 bars, then +1 ATR away
         BREAK         close beyond far edge first
         BREAK_RETEST  BREAK, then price returns to the zone from the other side and moves 1 ATR away
                       in the break direction (role flip) within the window
         CHOP          none of the above
OUTCOMES MFE/MAE from close[i] at 1,3,6,12,24 bars (points and ATR); first-passage of
         +1 ATR vs close beyond far edge.
CONFIRMATIONS (searched for bars i..i+11 after arrival, zone must still be intact; first one wins):
         C0_TOUCH     none — market entry at the touch (baseline)
         C1_RECLAIM   a close back outside the zone on the near side after trading inside
         C2_ENGULF    close beyond prior bar's extreme in zone direction with a body in zone direction
         C3_CHOCH     5m structure break (BOS/CHoCH) in zone direction
         C4_DISPLACE  a bar with body >= 1.2 ATR in zone direction
         C5_WICK      touch bar itself closes in the outer third with the zone-side wick >= 50% of range
         C6_SWEEP     a 5m pool (EQL for demand / EQH for supply) swept during the window, then a close
                      back outside the zone
         C7_FVG       a new 5m FVG in zone direction is born in the window
TRADE    entry next bar OPEN after the confirmation bar; stop = extreme since arrival beyond the
         zone (or far edge, whichever is further) +/- 0.25 ATR; targets 1R/2R/3R; 48-bar time stop;
         stop checked before target on the same bar; stop fills at worse of stop/open (gaps);
         cost 0.3 pt round trip (MGC: commission + 1 tick slippage, approx).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
D = OUT / "data"
COST = 0.3
SESS_OPEN = None
ATR_ARR = None
MIN_RISK_ATR = 0.2
H_LIST = [1, 3, 6, 12, 24]


def session_of(hutc):
    return np.where(hutc < 7, "ASIA", np.where(hutc < 12, "LONDON", np.where(hutc < 17, "NY", "LATE")))


def main():
    b = pd.read_csv(D / "bars_5m.csv")
    b["time_ct"] = pd.to_datetime(b.time_ct, utc=True).dt.tz_convert("America/Chicago")
    b["time_utc"] = pd.to_datetime(b.time_utc, utc=True)
    h4 = pd.read_csv(D / "bars_4h.csv")
    z = pd.read_csv(OUT / "zones.csv")
    st5 = pd.read_csv(D / "structure_5m.csv")
    pools = pd.read_csv(D / "pools_5m.csv")
    o, h, l, c = (b[k].to_numpy(float) for k in ["open", "high", "low", "close"])
    global SESS_OPEN, ATR_ARR
    SESS_OPEN = (b.tod.to_numpy() == 17 * 60)
    ATR_ARR = pd.Series(b.atr5.to_numpy(float)).ffill().bfill().to_numpy()
    atr = b.atr5.to_numpy(float)
    seg = b.segment.to_numpy()
    n = len(b)
    sess = session_of(b.time_utc.dt.hour.to_numpy())
    trend5 = b.trend5.to_numpy()
    # 4H trend known at each 5m bar = trend of the last CLOSED 4H bar in the same segment
    h4["last_i"] = h4.last_i.astype(int)
    trend4 = np.full(n, np.nan)
    for (sg, sub) in h4.groupby("segment"):
        li = sub.last_i.to_numpy()
        tr = sub.trend4.to_numpy()
        for j in range(len(li) - 1):
            trend4[li[j] + 1:li[j + 1] + 1] = tr[j]
    # rolling ATR regime
    atr_med = pd.Series(atr).rolling(2000, min_periods=300).median().to_numpy()
    # structure events by bar
    st_by_i = {}
    for r in st5.itertuples():
        st_by_i.setdefault(int(r.i), []).append((int(r.dir), r.kind))
    # pools swept at bar
    sweep_by_i = {}
    for r in pools.itertuples():
        if not np.isnan(r.swept_i):
            sweep_by_i.setdefault(int(r.swept_i), []).append(int(r.side))
    # 5m FVG births by bar
    fvg_by_i = {}
    for r in z[(z.tf == "5m") & (z.kind == "FVG")].itertuples():
        fvg_by_i.setdefault(int(r.born_i), []).append(int(r.dir))
    # live 4H context zones per bar (for "inside 4H zone" feature): intervals [born_i+1, end]
    ctx = []
    for r in z[(z.tf == "4h") | (z.kind == "4H")].itertuples():
        ctx.append((int(r.born_i), r.top, r.bot, int(r.dir), r.tf))
    ctx = pd.DataFrame(ctx, columns=["born_i", "top", "bot", "dir", "tf"])

    events, trades = [], []
    for zr in z.itertuples():
        d = int(zr.dir)
        top, bot = float(zr.top), float(zr.bot)
        size = top - bot
        start = int(zr.born_i) + 1
        sg = zr.segment
        i = start
        arrivals = 0
        broken_at = None
        # scan forward until broken (close beyond far edge) or 3 arrivals or segment end / 6000 bars
        lim = min(n, start + 6000)
        while i < lim and seg[i] == sg and arrivals < 3:
            far_break = (c[i] < bot) if d == 1 else (c[i] > top)
            arr = (l[i] <= top and l[i - 1] > top) if d == 1 else (h[i] >= bot and h[i - 1] < bot)
            if arr:
                arrivals += 1
                ev = event_row(zr, i, d, top, bot, size, arrivals, o, h, l, c, atr, seg, sess, trend5, trend4,
                               atr_med, b, ctx, sweep_by_i, st_by_i)
                if ev is not None:
                    events.append(ev)
                    trades += confirm_trades(ev, i, d, top, bot, o, h, l, c, atr, seg, st_by_i, sweep_by_i, fvg_by_i)
            if far_break:
                broken_at = i
                if events and events[-1]["zone_uid"] == zr.zone_uid:
                    trades += flip_trades(events[-1], i, d, top, bot, o, h, l, c, atr, seg)
                break
            i += 1
    ev = pd.DataFrame(events)
    tr = pd.DataFrame(trades)
    ev.to_csv(OUT / "events.csv", index=False)
    tr.to_csv(OUT / "data" / "confirmation_trades.csv", index=False)
    print("events", len(ev), "trades", len(tr))
    print(ev.groupby(["zone_tf", "zone_kind"]).reaction.value_counts(normalize=True).unstack().round(3))


def event_row(zr, i, d, top, bot, size, k, o, h, l, c, atr, seg, sess, trend5, trend4, atr_med, b, ctx,
              sweep_by_i, st_by_i):
    n = len(c)
    a = atr[i]
    if np.isnan(a) or a <= 0 or i + 24 >= n or seg[i + 24] != seg[i] or i < 7:
        return None
    near = top if d == 1 else bot
    far = bot if d == 1 else top
    rng = h[i] - l[i]
    # touch-bar geometry (demand orientation; mirrored for supply)
    if d == 1:
        pen_wick = (top - l[i]) / size
        pen_close = (top - c[i]) / size
        close_pos = (c[i] - l[i]) / rng if rng > 0 else 0.5
        zone_wick = (min(o[i], c[i]) - l[i]) / rng if rng > 0 else 0
        approach = (c[i - 6] - c[i]) / a
    else:
        pen_wick = (h[i] - bot) / size
        pen_close = (c[i] - bot) / size
        close_pos = (h[i] - c[i]) / rng if rng > 0 else 0.5
        zone_wick = (h[i] - max(o[i], c[i])) / rng if rng > 0 else 0
        approach = (c[i] - c[i - 6]) / a
    # inside a live 4H zone (either 4H-chart zone or 4H FVG imported to 5m) at touch?
    live = ctx[(ctx.born_i < i) & (ctx.bot <= h[i]) & (ctx.top >= l[i])]
    in4_same = bool((live.dir == d).any())
    in4_opp = bool((live.dir == -d).any())
    swept_here = any(sd == -d for sd in sweep_by_i.get(i, []))  # demand zone: EQL (side -1) swept
    ev = dict(zone_uid=zr.zone_uid, zone_tf=zr.tf, zone_kind=zr.kind, dir=d, top=top, bot=bot, size=size,
              size_atr5=size / a, arrival_no=k, age_bars=i - int(zr.born_i), i=i,
              time_ct=b.time_ct.iloc[i], video_ts=b.video_ts.iloc[i], session=sess[i], hour_ct=b.time_ct.iloc[i].hour,
              weekday=b.time_ct.iloc[i].weekday(), atr=a,
              vol_regime=("HI" if not np.isnan(atr_med[i]) and a > atr_med[i] else "LO"),
              trend5_aligned=bool(trend5[i] == d), trend4_aligned=(None if np.isnan(trend4[i]) else bool(trend4[i] == d)),
              in_4h_same=in4_same, in_4h_opp=in4_opp, pen_wick=pen_wick, pen_close=pen_close,
              close_pos=close_pos, zone_wick=zone_wick, closed_outside=bool(pen_close < 0),
              touch_range_atr=rng / a, approach_atr=approach, swept_pool_at_touch=swept_here,
              score_birth=zr.score_birth)
    # indicator comparison: REFLEX = first touch of a zone scoring >=3 (size+2, OB+1, first+1, trend+1)
    sc = (2 if size >= a else 0) + (1 if zr.kind == "OB" else 0) + (1 if k == 1 else 0) + (1 if trend5[i] == d else 0)
    ev["ind_station_score"] = sc
    ev["ind_reflex_signal"] = bool(zr.tf == "5m" and k == 1 and sc >= 3)
    # outcomes
    for H in H_LIST:
        seg_ok = seg[i + H] == seg[i]
        hh = h[i + 1:i + H + 1].max()
        ll = l[i + 1:i + H + 1].min()
        mfe = (hh - c[i]) if d == 1 else (c[i] - ll)
        mae = (c[i] - ll) if d == 1 else (hh - c[i])
        ev[f"mfe{H}_atr"] = mfe / a if seg_ok else np.nan
        ev[f"mae{H}_atr"] = mae / a if seg_ok else np.nan
        ev[f"ret{H}_atr"] = (d * (c[i + H] - c[i]) / a) if seg_ok else np.nan
    # reaction classification over 24 bars
    reaction, t_react = "CHOP", None
    swept = False
    for j in range(i, i + 25):
        fav = (h[j] - near) if d == 1 else (near - l[j])
        closed_far = (c[j] < far) if d == 1 else (c[j] > far)
        wick_far = (l[j] < far) if d == 1 else (h[j] > far)
        if closed_far:
            reaction, t_react = "BREAK", j
            break
        if wick_far:
            swept = True
        if fav >= a and j > i:
            reaction, t_react = ("SWEEP_RECLAIM" if swept else "REJECT"), j
            break
    if reaction == "BREAK":
        # role flip: return to the zone from the other side then 1 ATR away in the break direction
        back = False
        for j in range(t_react + 1, i + 25):
            if d == 1:
                if h[j] >= bot:
                    back = True
                if back and (bot - l[j]) >= a:
                    reaction = "BREAK_RETEST"
                    break
            else:
                if l[j] <= top:
                    back = True
                if back and (h[j] - top) >= a:
                    reaction = "BREAK_RETEST"
                    break
    ev["reaction"] = reaction
    ev["bars_to_reaction"] = (t_react - i) if t_react is not None else np.nan
    return ev


def simulate(d, entry_i, stop, o, h, l, c, seg, R_mult, max_bars=48):
    """Enter at open[entry_i]. Returns (R, exit_reason, bars)."""
    n = len(c)
    e = o[entry_i]
    risk = (e - stop) if d == 1 else (stop - e)
    if risk < MIN_RISK_ATR * ATR_ARR[entry_i]:      # same sanity floor as the indicator (0.2 ATR)
        return None
    tgt = e + d * R_mult * risk
    for j in range(entry_i, min(n, entry_i + max_bars)):
        if seg[j] != seg[entry_i]:
            px = c[j - 1]
            return ((px - e) * d - COST) / risk, "SEG_END", j - entry_i
        hit_stop = (l[j] <= stop) if d == 1 else (h[j] >= stop)
        hit_tgt = (h[j] >= tgt) if d == 1 else (l[j] <= tgt)
        # gold does not gap intraday on 5m: fills at the order price, except at the 17:00 session
        # open where a gapped open is the fill (worse for stops, better for targets)
        gap_ok = SESS_OPEN[j] and j > entry_i
        if hit_stop:
            px = (min(stop, o[j]) if d == 1 else max(stop, o[j])) if gap_ok else stop
            return ((px - e) * d - COST) / risk, "STOP", j - entry_i
        if hit_tgt:
            px = ((max(tgt, o[j]) if d == 1 else min(tgt, o[j])) if gap_ok else tgt)
            return ((px - e) * d - COST) / risk, "TARGET", j - entry_i
    j = min(n, entry_i + max_bars) - 1
    return ((c[j] - e) * d - COST) / risk, "TIME", j - entry_i


def flip_trades(ev, ib, d, top, bot, o, h, l, c, atr, seg):
    """K1_FLIP_RETEST (continuation). Zone of direction d broke at bar ib (close beyond far edge).
    Within 36 bars price must return INTO the zone from the break side (retest), then within 6 bars
    close back out on the break side. Enter next open in direction -d. Stop = extreme since the
    retest began +/- 0.25 ATR. Same targets/costs/time stop as the reversal trades."""
    n = len(c)
    a = ev["atr"]
    td = -d
    for j in range(ib + 1, min(n - 2, ib + 37)):
        if seg[j] != seg[ib]:
            return []
        retest = (h[j] >= bot) if d == 1 else (l[j] <= top)
        if not retest:
            continue
        for k in range(j, min(n - 2, j + 7)):
            if seg[k + 1] != seg[ib]:
                return []
            back_out = (c[k] < bot) if d == 1 else (c[k] > top)
            invalid = (c[k] > top) if d == 1 else (c[k] < bot)      # reclaimed the whole zone: no flip
            if invalid:
                return []
            if back_out:
                ext = h[j:k + 1].max() if td == -1 else l[j:k + 1].min()
                stop = ext + 0.25 * a if td == -1 else ext - 0.25 * a
                row = dict(zone_uid=ev["zone_uid"], event_i=ev["i"], conf="K1_FLIP_RETEST", conf_i=k,
                           entry_i=k + 1, bars_to_conf=k - ib, entry=o[k + 1], stop=stop,
                           risk_atr=abs(o[k + 1] - stop) / a, tdir=td, risk_pts=abs(o[k + 1] - stop))
                for R in (1, 2, 3):
                    s_ = simulate(td, k + 1, stop, o, h, l, c, seg, R)
                    if s_ is None:
                        row[f"r{R}"] = np.nan
                        continue
                    row[f"r{R}"], row[f"exit{R}"], row[f"bars{R}"] = s_
                if k + 2 < n and seg[k + 2] == seg[ib]:
                    s2 = simulate(td, k + 2, stop, o, h, l, c, seg, 2)
                    row["r2_late"] = s2[0] if s2 else np.nan
                return [row]
        return []
    return []


def confirm_trades(ev, i, d, top, bot, o, h, l, c, atr, seg, st_by_i, sweep_by_i, fvg_by_i):
    n = len(c)
    a = ev["atr"]
    far = bot if d == 1 else top
    near = top if d == 1 else bot
    found = {}
    ext = l[i] if d == 1 else h[i]
    swept = False
    inside = True
    for j in range(i, min(n - 1, i + 12)):
        if seg[j] != seg[i]:
            break
        ext = min(ext, l[j]) if d == 1 else max(ext, h[j])
        closed_far = (c[j] < far) if d == 1 else (c[j] > far)
        if closed_far:
            break
        if j == i:
            found.setdefault("C0_TOUCH", j)
            if ev["close_pos"] >= 2 / 3 and ev["zone_wick"] >= 0.5:
                found.setdefault("C5_WICK", j)
        outside_close = (c[j] > near) if d == 1 else (c[j] < near)
        traded_in = True  # the arrival bar traded inside by definition
        if outside_close and traded_in:
            found.setdefault("C1_RECLAIM", j)
        if j > i or j == i:
            eng = (c[j] > h[j - 1] and c[j] > o[j]) if d == 1 else (c[j] < l[j - 1] and c[j] < o[j])
            if eng:
                found.setdefault("C2_ENGULF", j)
        if any(sd == d for sd, _ in st_by_i.get(j, [])):
            found.setdefault("C3_CHOCH", j)
        if (c[j] - o[j]) * d >= 1.2 * atr[j]:
            found.setdefault("C4_DISPLACE", j)
        if any(sd == -d for sd in sweep_by_i.get(j, [])):
            swept = True
        if swept and outside_close:
            found.setdefault("C6_SWEEP", j)
        if any(fd == d for fd in fvg_by_i.get(j, [])):
            found.setdefault("C7_FVG", j)
    out = []
    for name, j in found.items():
        if j + 1 >= n or seg[j + 1] != seg[i]:
            continue
        ext_j = min(l[i:j + 1].min(), far) if d == 1 else max(h[i:j + 1].max(), far)
        stop = ext_j - 0.25 * a if d == 1 else ext_j + 0.25 * a
        row = dict(zone_uid=ev["zone_uid"], event_i=i, conf=name, conf_i=j, entry_i=j + 1,
                   bars_to_conf=j - i, entry=o[j + 1], stop=stop, risk_atr=abs(o[j + 1] - stop) / a)
        row["tdir"] = d
        row["risk_pts"] = abs(o[j + 1] - stop)
        for R in (1, 2, 3):
            s = simulate(d, j + 1, stop, o, h, l, c, seg, R)
            if s is None:
                row[f"r{R}"] = np.nan
                continue
            row[f"r{R}"], row[f"exit{R}"], row[f"bars{R}"] = s
        # stress: confirmation acted on one bar late (entry at open[j+2]), same stop, 2R
        if j + 2 < n and seg[j + 2] == seg[i]:
            s2 = simulate(d, j + 2, stop, o, h, l, c, seg, 2)
            row["r2_late"] = s2[0] if s2 else np.nan
        out.append(row)
    return out


if __name__ == "__main__":
    main()
