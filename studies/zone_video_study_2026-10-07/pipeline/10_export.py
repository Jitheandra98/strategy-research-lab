"""Stage 10: export the deliverable datasets.
EVENT_DATASET.csv : one row per zone interaction whose arrival bar was revealed on screen in a video
                    (+ split, video timestamps as h:mm:ss, quality flags). EXTERNAL rows are written separately.
ZONE_EVENTS.json  : one object per zone that had at least one on-video interaction: geometry, birth, lifecycle,
                    and its interactions in order.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

B = Path(sys.argv[1]); W = Path(sys.argv[2]); OUT = Path(sys.argv[3])
ev = pd.read_pickle(B / "events.pkl")
VNAME = {1: "V1 Screen Recording 2026-10-06 at 9.09.21 PM.mov", 2: "V2 Screen Recording 2026-10-07 at 12.50.20 AM 1.mov",
         3: "V3 Screen Recording 2026-10-07 at 7.20.49 AM.mov"}


def hms(s):
    if pd.isna(s): return ""
    s = int(round(s)); return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


ev["split"] = np.where(ev.video.isin([1, 2]), "DISCOVERY", np.where(ev.video == 3, "VALIDATION", "EXTERNAL"))
ev["event_id"] = [f"EV_{i:06d}" for i in range(len(ev))]
ev["video_ts_arrival"] = ev.video_t_reveal.map(hms)
ev["video_ts_bar_complete"] = ev.video_t_complete.map(hms)
ev["chart_time_ny"] = ev.time_ny.dt.strftime("%Y-%m-%d %H:%M")
# quality: segment-level dating agreement and data source
fr = pd.read_csv(W / "frames_dated.csv", parse_dates=["bar_utc"], low_memory=False)
segq = fr.dropna(subset=["seg"]).groupby(["video", "seg"]).match_diff.median()
# exact source per UTC day: Dukascopy files that existed when merged_1m.pkl was built, HistData otherwise
mt = (W / "merged_1m.pkl").stat().st_mtime
duka_days = {f.stem for f in (W / "duka_raw").glob("*.bi5") if f.stat().st_mtime <= mt and f.stat().st_size > 0}
ev["data_source"] = np.where(ev.time_utc.dt.strftime("%Y%m%d").isin(duka_days), "Dukascopy", "HistData")
zc = None
for f in sorted(W.glob("zone_check_v*.csv")):
    zc = pd.concat([zc, pd.read_csv(f)]) if zc is not None else pd.read_csv(f)
if zc is not None:
    # IDs are local to each pane; never pool Z15_00001 with Z4_00001.
    zc["zone_id"] = np.where(zc.pane == "15m", "Z15_", "Z4_") + zc.zid.astype(int).map(lambda n: f"{n:05d}")
    vis = zc.groupby("zone_id").hit.mean()
    ev["zone_edge_seen_rate"] = ev.zone_id.map(vis)
ev["AMBIGUOUS"] = ""
ev.loc[ev.height_atr < 0.15, "AMBIGUOUS"] += "zone thinner than 0.15 ATR (edge within data noise); "
ev.loc[ev.pen_atr.abs() < 0.05, "AMBIGUOUS"] += "touch within 0.05 ATR of the edge (feed difference could flip it); "
cols_first = ["event_id", "split", "video", "video_ts_arrival", "video_ts_bar_complete", "chart_time_ny", "time_utc",
              "zone_id", "universe", "zone_kind", "zone_dir", "interaction", "rd", "top", "bot", "AMBIGUOUS", "data_source"]
cols = cols_first + [c for c in ev.columns if c not in cols_first and c not in ("time_ny",)]
onv = ev[ev.video.notna()]
onv[cols].to_csv(OUT / "EVENT_DATASET.csv", index=False)
ev[ev.video.isna()][cols].to_csv(OUT / "data" / "EXTERNAL_EVENTS.csv", index=False)

z15 = pd.read_pickle(B / "zones15.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl")
zl = []
for zid, g in onv.groupby("zone_id"):
    uni, num = zid.split("_"); num = int(num)
    z = (z15 if uni == "Z15" else z4).set_index("zid").loc[num]
    zl.append({"zone_id": zid, "chart": "15m pane" if uni == "Z15" else "4h pane", "kind": z.kind,
               "direction_at_birth": "demand" if z.dir == 1 else "supply", "top": round(z.top, 3), "bottom": round(z.bot, 3),
               "height_pts": round(z.top - z.bot, 3), "born_time_utc": str(z.born_time),
               "first_touch_time_utc": str(z.first_touch_time), "consumed_time_utc": str(z.consumed_time),
               "inverted_time_utc": str(z.inverted_time), "ended_time_utc": str(z.end_time), "final_state": z.final_state,
               "interactions": [{"event_id": r.event_id, "video": int(r.video), "video_ts": r.video_ts_arrival,
                                 "chart_time_ny": r.chart_time_ny, "type": r.interaction, "touch_no": int(r.prior_arrivals) + 1,
                                 "penetration_frac": round(r.pen_frac, 3), "close_loc": r.close_loc,
                                 "archetype": r.archetype, "R1": None if pd.isna(r.R1) else int(r.R1),
                                 "mfe20_atr": round(r.mfe20, 2), "mae20_atr": round(r.mae20, 2)} for r in g.itertuples()]})
(OUT / "ZONE_EVENTS.json").write_text(json.dumps(zl, indent=1))
print("on-video events", len(onv), "zones", len(zl), "external events", (ev.video.isna()).sum())
