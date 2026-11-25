"""Stage 7: zone interactions -> one row per interaction with features (known at the arrival bar's close) and
outcomes (measured strictly after it).

Interaction definitions (the study's own; the indicator's touch logic is not reused):
  ARRIVAL   - defending-side approach: demand: low[i-1] > top and low[i] <= top   (supply mirrored)
  FLIP      - after the zone BROKE (15m close beyond the far edge), approach from the broken side:
              former demand: high[i-1] < bot and high[i] >= bot; expected reaction = opposite of the zone's
              original direction. (This is how "failed zones" are studied.)
Zones: Z15 = zones on the 15m pane (15m FVG/OB + imported 4H FVG); Z4 = zones on the 4H pane (4H FVG/OB),
usable from the close of the 4H bar that created them. A zone is studied from availability until it is archived
or evicted by the indicator (end_time), else to the end of data.
Units: ATR = 15m ATR(14) at the arrival bar. 'rd' = reaction direction (+1 up, -1 down).
usage: 07_events.py <build_dir> <work_dir_with_frames_dated>
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

B = Path(sys.argv[1]); W = Path(sys.argv[2])
b15 = pd.read_pickle(B / "bars15.pkl"); h4 = pd.read_pickle(B / "bars4h.pkl")
z15 = pd.read_pickle(B / "zones15.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl")
s15 = pd.read_pickle(B / "struct15.pkl")
T = b15.index; n = len(T)
O, H, L, C = (b15[k].to_numpy(float) for k in ["open", "high", "low", "close"])
ATR = b15.atr.to_numpy(); EMA = b15.ema.to_numpy(); TR15 = b15.trend.to_numpy()
pos = {t: i for i, t in enumerate(T)}
HZ = 20  # outcome horizon (bars)

# ── 4H context mapped to each 15m bar (only CLOSED 4H bars are known) ──
h4c = h4.copy(); h4c["avail"] = pd.to_datetime(h4c.avail)
ctx = pd.merge_asof(pd.DataFrame({"t": T}), h4c[["avail", "trend", "atr", "ema", "close", "high", "low"]]
                    .rename(columns={"avail": "t", "trend": "tr4", "atr": "atr4", "ema": "ema4", "close": "c4",
                                     "high": "hh4", "low": "ll4"}).sort_values("t"), on="t", direction="backward")
TR4 = ctx.tr4.to_numpy(); ATR4 = ctx.atr4.to_numpy(); EMA4 = ctx.ema4.to_numpy()
# 4H structure direction from 4H BOS/CHoCH, known at the 4H bar close
s4 = pd.read_pickle(B / "struct4h.pkl")
s4["avail"] = s4.time.map(lambda x: h4c.avail.get(x, pd.NaT))
st4 = pd.merge_asof(pd.DataFrame({"t": T}), s4[["avail", "dir"]].rename(columns={"avail": "t"}).dropna().sort_values("t"),
                    on="t", direction="backward").dir.to_numpy()
# 15m structure direction (BOS/CHoCH confirmed at bar close)
sd = np.zeros(n); last = 0; sb = dict(zip(s15.bar, s15.dir))
for i in range(n):
    if i in sb: last = sb[i]
    sd[i] = last
# 15m FVG births per bar (for displacement features)
fvg_up = np.r_[False, False, L[2:] > H[:-2]]; fvg_dn = np.r_[False, False, H[2:] < L[:-2]]

# ── video reveal times (stage 5b): bar -> [(video, first time on screen, run)] ──
_rev = pd.read_pickle(W / "bar_reveal.pkl")
reveal = {k: sorted(v, key=lambda x: (x[0], x[1]))[0] for k, v in _rev.items()}
multi_video = {k for k, v in _rev.items() if len({x[0] for x in v}) > 1}

# ── zone table, availability ──
zs = []
for _, z in z15.iterrows():
    a = int(z.born_bar) + 1
    e = pos.get(z.end_time, n) if pd.notna(z.end_time) else n
    zs.append(dict(uni="Z15", zid=f"Z15_{int(z.zid):05d}", kind=z.kind, dir=int(z.dir), top=z.top, bot=z.bot,
                   born_time=z.born_time, avail=a, end=e, score_birth=z.score_birth, size_atr_birth=z.size_atr))
for _, z in z4.iterrows():
    av = h4c.avail.get(z.born_time, pd.NaT)
    if pd.isna(av) or av not in pos: continue
    a = pos[av]
    et = (z.end_time + pd.Timedelta(hours=4)) if pd.notna(z.end_time) else None
    e = int(np.searchsorted(T, et)) if et is not None else n
    zs.append(dict(uni="Z4", zid=f"Z4_{int(z.zid):05d}", kind=z.kind, dir=int(z.dir), top=z.top, bot=z.bot,
                   born_time=z.born_time, avail=a, end=e, score_birth=z.score_birth, size_atr_birth=z.size_atr))
ZS = pd.DataFrame(zs)
import os
PLACEBO = os.environ.get("PLACEBO") == "1"
if PLACEBO:
    # control: the same zones (same height, birth, life, direction) moved 1.5-3.0 ATR up or down at random
    rg = np.random.default_rng(11)
    sh = rg.choice([-1, 1], len(ZS)) * rg.uniform(1.5, 3.0, len(ZS)) * ATR[np.minimum(ZS.avail.to_numpy(), n - 1)]
    ZS["top"] = ZS.top + sh; ZS["bot"] = ZS.bot + sh


def live_zones_at(i, uni=None):
    m = (ZS.avail <= i) & (ZS.end > i)
    if uni: m &= ZS.uni == uni
    return ZS[m]


def outcome(i, rd, top, bot, zdir_def):
    """rd = reaction direction. Reference = close[i]. Returns dict of outcome measures."""
    a = ATR[i]; ref = C[i]; j1 = min(n, i + 1 + HZ)
    hh, ll, cc = H[i + 1:j1], L[i + 1:j1], C[i + 1:j1]
    if len(cc) < HZ: return None
    fav = (hh - ref) if rd == 1 else (ref - ll)
    adv = (ref - ll) if rd == 1 else (hh - ref)
    out = {}
    for k in (1, 2, 3, 5, 10, 20):
        out[f"ret{k}"] = rd * (cc[k - 1] - ref) / a
    out["mfe20"] = fav.max() / a; out["mae20"] = adv.max() / a
    out["mfe10"] = fav[:10].max() / a; out["mae10"] = adv[:10].max() / a
    # first-passage +-1 ATR (ties -> loss), and +-0.5 / 2 ATR variants
    for tgt, tag in ((1.0, "R1"), (0.5, "R05"), (2.0, "R2")):
        res = np.nan; bars = np.nan
        for k in range(HZ):
            up, dn = fav[k] >= tgt * a, adv[k] >= tgt * a
            if dn: res, bars = 0, k + 1; break
            if up: res, bars = 1, k + 1; break
        out[tag] = res; out[tag + "_bars"] = bars
    # zone break: close beyond the far edge (relative to the reaction direction) within 10 bars
    far = bot if rd == 1 else top; near = top if rd == 1 else bot
    brk = np.where((cc[:10] < far) if rd == 1 else (cc[:10] > far))[0]
    out["BRK"] = int(len(brk) > 0); out["brk_bar"] = brk[0] + 1 if len(brk) else np.nan
    # reclaim after break: a close back beyond the near edge within 10 bars of the break
    out["RECLAIM"] = 0
    if len(brk):
        after = cc[brk[0] + 1: brk[0] + 11]
        out["RECLAIM"] = int(((after > near) if rd == 1 else (after < near)).any())
    # archetype
    if out["R1"] == 1 and out["R1_bars"] <= 3 and not out["BRK"]: arc = "IMMEDIATE_REJECTION"
    elif out["R1"] == 1 and not out["BRK"]: arc = "DELAYED_REACTION"
    elif out["BRK"] and out["RECLAIM"]: arc = "FALSE_BREAK_RECLAIM"
    elif out["BRK"]: arc = "BREAK_THROUGH"
    elif out["R1"] == 1: arc = "REACTION_AFTER_DEEP_PROBE"
    elif out["mfe20"] < 1 and out["mae20"] < 1: arc = "NO_REACTION_CHOP"
    else: arc = "WEAK_OR_ADVERSE"
    out["archetype"] = arc
    return out


COST = 0.30  # points round trip (spread + slippage), charged on every trade


def edge_trade(i, rd, top, bot):
    """Limit entry at the near edge on the arrival bar (or the open if the bar opened inside), stop 0.1 ATR beyond
    the far edge, targets 1R / 2R, 40-bar time stop at the close. Same-bar stop+target -> stop (conservative).
    On the arrival bar itself only the stop can be checked (order of the high/low inside the bar is unknown)."""
    a = ATR[i]
    near = top if rd == 1 else bot; far = bot if rd == 1 else top
    entry = min(near, O[i]) if rd == 1 else max(near, O[i])
    stop = far - 0.1 * a if rd == 1 else far + 0.1 * a
    risk = abs(entry - stop)
    res = {"tr_risk_atr": risk / a}
    if (rd == 1 and L[i] <= stop) or (rd == -1 and H[i] >= stop):
        for k in ("tr1", "tr2"): res[k] = 0
        res["tr2_R"] = -1 - COST / risk; res["tr1_R"] = -1 - COST / risk; return res
    for tg in (1, 2):
        tgt = entry + rd * tg * risk; out = None
        for j in range(i + 1, min(n, i + 41)):
            hit_s = (L[j] <= stop) if rd == 1 else (H[j] >= stop)
            hit_t = (H[j] >= tgt) if rd == 1 else (L[j] <= tgt)
            if hit_s: out = (0, -1.0); break
            if hit_t: out = (1, float(tg)); break
        if out is None:
            j = min(n - 1, i + 40); out = (np.nan, rd * (C[j] - entry) / risk)
        res[f"tr{tg}"] = out[0]; res[f"tr{tg}_R"] = out[1] - COST / risk
    return res


def approach_features(i, rd, near):
    """rd = reaction direction (away from zone). Approach comes from the rd side towards the zone."""
    a = ATR[i]; f = {}
    w0 = max(0, i - 20)
    if rd == 1:   # demand-like: price came down
        k = w0 + int(np.argmax(H[w0:i])); f["travel_atr"] = (H[k] - near) / a
    else:
        k = w0 + int(np.argmin(L[w0:i])); f["travel_atr"] = (near - L[k]) / a
    f["approach_bars"] = i - k
    f["velocity_atr_per_bar"] = f["travel_atr"] / max(1, f["approach_bars"])
    rng = (H - L)
    f["rng_last3_atr"] = rng[i - 3:i].mean() / a
    f["rng_prev7_atr"] = rng[i - 10:i - 3].mean() / a
    f["accel_ratio"] = f["rng_last3_atr"] / max(1e-9, f["rng_prev7_atr"])
    f["max_rng10_atr"] = rng[i - 10:i].max() / a
    body = np.abs(C - O)
    f["body_frac_last3"] = (body[i - 3:i] / np.maximum(rng[i - 3:i], 1e-9)).mean()
    tow = -rd  # direction of travel toward the zone
    cnt = 0
    for k2 in range(i - 1, i - 15, -1):
        if np.sign(C[k2] - O[k2]) == tow: cnt += 1
        else: break
    f["consec_toward"] = cnt
    f["n_toward_last10"] = int(sum(np.sign(C[i - 10:i] - O[i - 10:i]) == tow))
    f["mom10_atr"] = tow * (C[i - 1] - C[i - 11]) / a
    f["compress5_atr"] = (H[i - 5:i].max() - L[i - 5:i].min()) / a
    f["disp_fvg_toward5"] = int((fvg_dn[i - 5:i + 1] if tow == -1 else fvg_up[i - 5:i + 1]).any())
    f["disp_fvg_away20"] = int((fvg_up[i - 20:i] if rd == 1 else fvg_dn[i - 20:i]).any())
    f["prev_bar_toward"] = int(np.sign(C[i - 1] - O[i - 1]) == tow)
    f["prev_bar_rng_atr"] = rng[i - 1] / a
    return f


def arrival_features(i, rd, top, bot):
    a = ATR[i]; ht = top - bot; f = {}
    near = top if rd == 1 else bot; far = bot if rd == 1 else top
    ext = L[i] if rd == 1 else H[i]  # the extreme that entered
    depth = (near - ext) if rd == 1 else (ext - near)
    f["pen_frac"] = depth / ht; f["pen_atr"] = depth / a
    f["wick_beyond_far"] = int((L[i] < bot) if rd == 1 else (H[i] > top))
    cl = C[i]
    f["close_loc"] = ("BEYOND_FAR" if ((cl < bot) if rd == 1 else (cl > top)) else
                      "INSIDE" if bot <= cl <= top else "OUTSIDE_NEAR")
    f["close_depth_frac"] = ((near - cl) if rd == 1 else (cl - near)) / ht  # <0 = closed back outside
    f["body_entered"] = int((min(O[i], C[i]) < top) if rd == 1 else (max(O[i], C[i]) > bot))
    f["passed_mid"] = int(depth >= 0.5 * ht)
    r = max(H[i] - L[i], 1e-9)
    f["arr_rng_atr"] = r / a
    f["arr_clv"] = rd * ((C[i] - L[i]) / r - 0.5) * 2   # +1 = closed at the reaction-side extreme
    f["arr_dir_with_reaction"] = int(np.sign(C[i] - O[i]) == rd)
    f["arr_body_frac"] = abs(C[i] - O[i]) / r
    f["gap_open_inside"] = int(bot <= O[i] <= top)
    return f


rows = []
for _, z in ZS.iterrows():
    top, bot, d0 = z.top, z.bot, z.dir
    ht = top - bot
    broken = False; prior = 0; prior_flip = 0; max_prior_pen = 0.0; last_arr = -999
    start = max(z.avail, 30)
    for i in range(start, min(z.end, n - HZ - 5)):
        # update broken state using the PREVIOUS bars only (known before bar i)
        if i - 1 >= z.avail and not broken:
            if (d0 == 1 and C[i - 1] < bot) or (d0 == -1 and C[i - 1] > top):
                broken = True; broke_at = i - 1
        if not broken:
            arr = (L[i - 1] > top and L[i] <= top) if d0 == 1 else (H[i - 1] < bot and H[i] >= bot)
            rd = d0; kind_int = "ARRIVAL"
        else:
            arr = (H[i - 1] < bot and H[i] >= bot) if d0 == 1 else (L[i - 1] > top and L[i] <= top)
            rd = -d0; kind_int = "FLIP"
        if not arr or np.isnan(ATR[i]):
            continue
        out = outcome(i, rd, top, bot, d0)
        if out is None: continue
        near = top if rd == 1 else bot
        r = dict(zone_id=z.zid, universe=z.uni, zone_kind=z.kind, zone_dir=d0, interaction=kind_int, rd=rd,
                 bar=i, time_utc=T[i], top=top, bot=bot, height_pts=ht, height_atr=ht / ATR[i],
                 size_atr_birth=z.size_atr_birth, score_birth=z.score_birth,
                 age_bars=i - z.avail, prior_arrivals=prior if kind_int == "ARRIVAL" else prior_flip,
                 prior_max_pen=max_prior_pen, bars_since_last=i - last_arr if last_arr > 0 else np.nan,
                 bars_since_break=(i - broke_at) if broken else np.nan,
                 atr=ATR[i], atr_regime=ATR[i] / np.nanmedian(ATR[max(0, i - 400):i]),
                 trend15_with=int(TR15[i] == rd), trend4_with=int(TR4[i] == rd) if not np.isnan(TR4[i]) else np.nan,
                 struct15_with=int(sd[i] == rd), struct4_with=int(st4[i] == rd) if not np.isnan(st4[i]) else np.nan,
                 ema_dist_atr=rd * (C[i] - EMA[i]) / ATR[i],
                 ema4_side_with=int(np.sign(C[i] - EMA4[i]) == rd) if not np.isnan(EMA4[i]) else np.nan,
                 hour_ny=T[i].tz_convert("America/New_York").hour, dow=T[i].tz_convert("America/New_York").dayofweek)
        r.update(approach_features(i, rd, near)); r.update(arrival_features(i, rd, top, bot))
        # location vs other zones live at i
        lz = live_zones_at(i)
        oth = lz[lz.zid != z.zid]
        ov = (np.minimum(oth.top, top) - np.maximum(oth.bot, bot)) > 0
        r["n_overlap_same"] = int((ov & (oth.dir == rd)).sum()); r["n_overlap_opp"] = int((ov & (oth.dir == -rd)).sum())
        r["nested_in_4h_same"] = int((ov & (oth.dir == rd) & (oth.uni == "Z4")).sum() > 0) if z.uni == "Z15" else np.nan
        r["conflict_4h_opp"] = int((ov & (oth.dir == -rd) & (oth.uni == "Z4")).sum() > 0)
        # room to run: nearest opposite-direction zone edge in the reaction direction
        if rd == 1:
            opp = oth[(oth.dir == -1) & (oth.bot > C[i])]; room = (opp.bot.min() - C[i]) if len(opp) else np.nan
            behind = oth[(oth.dir == 1) & (oth.top < bot) & (oth.top > bot - 2 * ATR[i])]
        else:
            opp = oth[(oth.dir == 1) & (oth.top < C[i])]; room = (C[i] - opp.top.max()) if len(opp) else np.nan
            behind = oth[(oth.dir == -1) & (oth.bot > top) & (oth.bot < top + 2 * ATR[i])]
        r["room_atr"] = room / ATR[i] if pd.notna(room) else np.nan
        r["n_support_behind_2atr"] = len(behind)
        r.update(out)
        r.update(edge_trade(i, rd, top, bot))
        # pre-arrival path (oriented: + = on the reaction side of the near edge), closes i-10..i, in ATR
        for k in range(11):
            r[f"p{k}"] = rd * (C[i - 10 + k] - near) / ATR[i]
        r["p_ext"] = rd * ((L[i] if rd == 1 else H[i]) - near) / ATR[i]
        # WAIT-and-confirm: decide at the close of bar i+k (k=1..3); outcome measured from that close
        for k in (1, 2, 3):
            j = i + k
            seen_far = (C[i:j + 1] < bot).any() if rd == 1 else (C[i:j + 1] > top).any()
            back_out = (C[j] > top) if rd == 1 else (C[j] < bot)
            r[f"c{k}_close_out"] = int(back_out); r[f"c{k}_closed_beyond"] = int(seen_far)
            r[f"c{k}_new_ext"] = int((L[j] < L[i:j].min()) if rd == 1 else (H[j] > H[i:j].max()))
            r[f"c{k}_ret_atr"] = rd * (C[j] - C[i]) / ATR[i]
            oc = outcome(j, rd, top, bot, d0)
            r[f"c{k}_R1"] = oc["R1"] if oc else np.nan
            r[f"c{k}_ret10"] = oc["ret10"] if oc else np.nan
        rv = reveal.get(T[i])
        r["video"] = rv[0] if rv else np.nan; r["video_t_reveal"] = rv[1] if rv else np.nan
        rv2 = reveal.get(T[i + 1]) if i + 1 < n else None
        r["video_t_complete"] = rv2[1] if rv2 else np.nan
        r["shown_in_multiple_videos"] = int(T[i] in multi_video)
        r["outcome_on_video"] = int(all(T[k] in reveal for k in range(i, min(n, i + HZ + 1))))
        rows.append(r)
        # bookkeeping after the event (uses bar i itself; affects only later events)
        if kind_int == "ARRIVAL": prior += 1
        else: prior_flip += 1
        max_prior_pen = max(max_prior_pen, r["pen_frac"]); last_arr = i
ev = pd.DataFrame(rows)
ev["time_ny"] = ev.time_utc.dt.tz_convert("America/New_York")
ev.to_pickle(B / ("events_placebo.pkl" if PLACEBO else "events.pkl"))
print("events", len(ev), "on video", ev.video.notna().sum(), ev.groupby(["universe", "interaction"]).size().to_dict())
