"""Run the QF15 test copies over 2016-01 .. 2026-09 in quarterly chunks (30-day warm-up), 15m chart, keep in-chunk signals."""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
RUNNER = Path.home() / "Desktop/hey hey/trading-video-intel/tools/pine_runner/runner_values.mjs"
OUT = HERE / "chunks"; OUT.mkdir(exist_ok=True)
qs = list(pd.date_range("2016-01-01", "2026-10-01", freq="QS"))
jobs = [(v, s, min(s + pd.offsets.QuarterBegin(1, startingMonth=1), pd.Timestamp("2026-09-25"))) for s in qs[:-1] for v in ("pd",)]
def run(j):
    v, s, e = j
    f = OUT / f"{v}_{s:%Y%m}.json"
    if f.exists(): return
    tmp = OUT / f"{v}_{s:%Y%m}.raw.json"
    subprocess.run(["node", "--max-old-space-size=2500", str(RUNNER), str(HERE / f"QF15_{v}.pine"), "15",
                    (s - pd.Timedelta(days=30)).strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d"), str(tmp)],
                   capture_output=True, text=True, cwd=RUNNER.parent, timeout=7200)
    r = json.loads(tmp.read_text()) if tmp.exists() else {"status": "crash", "values": {}}
    lo, hi = s.value // 10**6, e.value // 10**6
    r = {"status": r.get("status"), "error": r.get("error"), "values": {k: [x for x in vv if lo <= x[0] < hi] for k, vv in r.get("values", {}).items()}}
    f.write_text(json.dumps(r)); tmp.unlink(missing_ok=True)
    print(v, f"{s:%Y-%m}", r["status"], len(r["values"].get("v_pd", [])), flush=True)
with ThreadPoolExecutor(3) as ex: list(ex.map(run, jobs[::-1]))
print("DONE")
