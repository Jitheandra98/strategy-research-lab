"""Stage 6 — independent validation of the reconstructed 5m series.

A. 4H header check: each frame's 4H pane header shows the forming 4H bar's exact O/H/L/C
   (typed digits, 0.1 precision). Aggregate our 5m bars over the same 4H window up to the
   frame's last bar and compare. Tries candidate 4H alignments; reports which fits.
B. Internal continuity: |open_t − close_{t−1}| for consecutive bars (gold rarely gaps intraday).
C. Observation spread per bar.
Output: WORK/stitched/validation.json (+ printed summary)
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

W = Path(sys.argv[1])
b = pd.read_csv(W / "stitched" / "bars_5m_dated.csv", parse_dates=["time_ct"])
b["time_ct"] = pd.to_datetime(b.time_ct, utc=True).dt.tz_convert("America/Chicago")
f = pd.read_json(W / "stitched" / "frame_map.jsonl", lines=True)
key = {(c, g): i for i, (c, g) in enumerate(zip(b.chain, b.g))}


def bucket_start(t, scheme):
    """4H bucket start for a CT timestamp."""
    if scheme == "session17":          # 17,21,01,05,09,13 CT
        h = (t.hour - 17) % 24
        start = t - pd.Timedelta(hours=h % 4, minutes=t.minute)
        return start
    if scheme == "utc0":               # 00,04,08,12,16,20 UTC
        tu = t.tz_convert("UTC")
        s = tu - pd.Timedelta(hours=tu.hour % 4, minutes=tu.minute)
        return s.tz_convert("America/Chicago")
    if scheme == "ct0":                # 00,04,08,... CT
        return t - pd.Timedelta(hours=t.hour % 4, minutes=t.minute)


res = {}
bt = b.set_index("time_ct").sort_index()
for scheme in ["session17", "utc0", "ct0"]:
    rows = []
    for _, r in f.iterrows():
        h4 = r.get("hdr4h")
        if not isinstance(h4, list) or pd.isna(r.get("g_last")):
            continue
        i = key.get((r.chain, int(r.g_last)))
        if i is None:
            continue
        t_last = b.time_ct.iloc[i]
        s = bucket_start(t_last, scheme)
        # The 4H pane refreshes on its own clock and can lag the 5m pane by several bars.
        # Align on the header's typed close: end bar = the bar in [t_last-36, t_last+1] of this
        # bucket whose close is nearest C; then O/H/L are compared independently.
        w_all = bt.loc[s:t_last + pd.Timedelta(minutes=5)]
        w_all = w_all[w_all.chain == r.chain]
        if len(w_all) == 0:
            continue
        cand = w_all.iloc[max(0, len(w_all) - 38):]
        j = int(np.argmin(np.abs(cand.close.to_numpy() - h4[3])))
        e = cand.index[j]
        w = w_all.loc[:e]
        best = (0, dict(dO=w.open.iloc[0] - h4[0], dH=w.high.max() - h4[1], dL=w.low.min() - h4[2],
                        dC=w.close.iloc[-1] - h4[3], n=len(w), lag=len(w_all) - len(w),
                        first_tod=int(w.tod.iloc[0]), clean=bool((~w.label_only).all()),
                        frame_id=r.frame_id, video_s=r.video_s, t_last=str(t_last), bucket=str(s),
                        h4=list(h4), our=[w.open.iloc[0], w.high.max(), w.low.min(), w.close.iloc[-1]]))
        if best:
            rows.append(best[1])
    df = pd.DataFrame(rows)
    if scheme == "session17":
        df.to_csv(W / "stitched" / "validation_4h_rows.csv", index=False)
    q = {"lag_median_bars": float(df.lag.median()) if len(df) else None}
    for c in ["dO", "dH", "dL", "dC"]:
        a = df[c].abs()
        q[c] = dict(median=round(float(a.median()), 3), p90=round(float(a.quantile(.9)), 3),
                    within_0_3=round(float((a <= 0.3).mean()), 3), within_1=round(float((a <= 1.0).mean()), 3))
    al = df[(df.dO.abs() <= 0.3) & (df.dC.abs() <= 0.3)] if len(df) else df
    for c in ["dH", "dL"]:
        a = al[c]
        q[c + "_aligned"] = dict(n=len(al), within_0_3=round(float((a.abs() <= .3).mean()), 3),
                                 within_1=round(float((a.abs() <= 1).mean()), 3),
                                 ours_short_gt1=round(float(((a < -1) if c == "dH" else (a > 1)).mean()), 3),
                                 ours_over_gt1=round(float(((a > 1) if c == "dH" else (a < -1)).mean()), 3))
    res[scheme] = dict(n=len(df), **q)
    print(scheme, json.dumps(res[scheme]))

bb = b.sort_values(["chain", "g"])
gap = (bb.open - bb.close.shift()).where((bb.chain == bb.chain.shift()) & (bb.g == bb.g.shift() + 1)
                                          & (bb.tod != 17 * 60)).abs().dropna()
res["continuity_open_vs_prev_close"] = dict(n=len(gap), median=float(gap.median()), p90=float(gap.quantile(.9)),
                                             p99=float(gap.quantile(.99)), within_0_3=float((gap <= .3).mean()))
res["obs_per_bar"] = dict(median=float(b.n_obs.median()), p10=float(b.n_obs.quantile(.1)))
res["spread_high"] = dict(median=float(b.h_spread.median()), p90=float(b.h_spread.quantile(.9)))
res["pt_per_px"] = dict(median=float(b.pt_per_px.median()), p90=float(b.pt_per_px.quantile(.9)))
print(json.dumps({k: v for k, v in res.items() if k not in ("session17", "utc0", "ct0")}, indent=1))
(W / "stitched" / "validation.json").write_text(json.dumps(res, indent=1))
