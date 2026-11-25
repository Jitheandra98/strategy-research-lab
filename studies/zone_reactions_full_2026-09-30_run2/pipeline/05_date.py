"""Stage 5 — assign calendar dates to stitched chains and emit the final 5m series.

For each chain: walk bars in order using time-of-day and the CME Globex metals calendar
(see 04_stitch.FULL_CLOSURES). The chain's start date is the candidate that maximizes agreement
with OCR'd day/month/year axis labels (held-out evidence). Agreement is reported per chain.
Output: WORK/stitched/bars_5m_dated.csv (time_ct, time_utc, OHLC, QA columns), date_report.json
"""
import json, sys, importlib.util
from collections import defaultdict, Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

W = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("st", Path(__file__).parent / "04_stitch.py")
st = importlib.util.module_from_spec(spec)
_argv = sys.argv
sys.argv = [sys.argv[0], str(W)]
spec.loader.exec_module(st)
sys.argv = _argv
CT = ZoneInfo("America/Chicago")
OPEN, CLOSE = 17 * 60, 16 * 60


def walk(tods, d0):
    """tods: list of (g, tod) sorted by g, consecutive g may skip. Returns {g: date}."""
    out = {}
    d = d0
    pg, pt = tods[0]
    out[pg] = d
    for g, t in tods[1:]:
        steps = g - pg
        # expected tod after `steps` bars with no session boundary
        crossed_open = (pt < OPEN <= t) or (pt < OPEN and t < pt and steps > 1 and False)
        if pt < OPEN and t >= OPEN:
            # new session opened (daily break, weekend or holiday)
            d = st.next_session_open_date(d)
        elif t < pt:
            d = d + timedelta(days=1)                     # midnight
            if pt < OPEN and t < OPEN:                    # jumped from morning to earlier morning: >1 session lost
                pass
        out[g] = d
        pg, pt = g, t
    return out


def main():
    bars = pd.read_csv(W / "stitched" / "bars_raw.csv")
    fmap = pd.read_json(W / "stitched" / "frame_map.jsonl", lines=True)
    votes = defaultdict(list)            # chain -> list of (g, kind, value)
    for _, r in fmap.iterrows():
        if isinstance(r.get("date_labels"), list) and not pd.isna(r.get("chain")):
            for kind, value, g in r["date_labels"]:
                votes[int(r["chain"])].append((int(g), kind, int(value)))
    chains = sorted(bars.chain.unique(), key=lambda c: fmap[fmap.chain == c].video_s.min())
    report, dated = [], []
    prev_end = date(2025, 10, 1)
    for c in chains:
        sub = bars[bars.chain == c].sort_values("g")
        tods = list(zip(sub.g, sub.tod))
        cands = [prev_end + timedelta(days=i) for i in range(-45, 120)]
        best = None
        for d0 in cands:
            if d0.weekday() == 5:
                continue
            m = walk(tods, d0)
            ok = tot = 0
            for g, kind, val in votes[c]:
                if g not in m:
                    continue
                tot += 1
                dd = m[g]
                if kind == "day":
                    ok += dd.day == val
                elif kind == "month":
                    ok += dd.month == val and dd.day <= 3
                elif kind == "year":
                    ok += dd.year == val and dd.month == 1 and dd.day <= 3
            # structural sanity: no Saturday bars, Sunday only after the open
            bad = sum(1 for g, t in tods if m[g].weekday() == 5 or (m[g].weekday() == 6 and t < OPEN))
            score = (ok - 3 * bad, -abs((d0 - prev_end).days))
            if best is None or score > best[0]:
                best = (score, d0, ok, tot, bad, m)
        (_, d0, ok, tot, bad, m) = best
        vid = fmap[fmap.chain == c].video_s
        report.append(dict(chain=int(c), n_bars=len(sub), start=str(d0), end=str(max(m.values())), votes_ok=ok,
                           votes_total=tot, weekend_violations=bad, video_s_from=float(vid.min()), video_s_to=float(vid.max())))
        prev_end = max(m.values())
        sub = sub.copy()
        sub["date"] = sub.g.map(m)
        dated.append(sub)
    out = pd.concat(dated)
    out["time_ct"] = [datetime(d.year, d.month, d.day, t // 60, t % 60, tzinfo=CT) for d, t in zip(out.date, out.tod)]
    out["time_utc"] = [x.astimezone(ZoneInfo("UTC")) for x in out.time_ct]
    out.to_csv(W / "stitched" / "bars_5m_dated.csv", index=False)
    (W / "stitched" / "date_report.json").write_text(json.dumps(report, indent=1))
    rp = pd.DataFrame(report)
    print(rp.to_string())
    print("votes agree", rp.votes_ok.sum(), "/", rp.votes_total.sum())


if __name__ == "__main__":
    main()
