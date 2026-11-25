"""Build the PineTS input files from research/gold101/data/gc5m.csv (GC futures 5 m, ET timestamps, real volume).
gc5m7.f64    : [utc_ms, o, h, l, c, v, session_open_ms]  (CME session = 18:00 ET → 17:00 ET)
gc5m7_ct.f64 : same, but times are Chicago wall-clock encoded as UTC, because PineTS ignores time zones
               (hour(), time(tf, session, tz) and dayofweek() all read UTC there)."""
import csv, numpy as np, datetime as dt
from zoneinfo import ZoneInfo
ET, CT, UTC = ZoneInfo("America/New_York"), ZoneInfo("America/Chicago"), ZoneInfo("UTC")
rows, seen = [], set()
with open("../gold101/data/gc5m.csv") as f:
    r = csv.reader(f); next(r)
    for d, o, h, l, c, v in r:
        t = dt.datetime.strptime(d, "%Y-%m-%d %H:%M").replace(tzinfo=ET)
        ms = int(t.astimezone(UTC).timestamp() * 1000)
        if ms in seen: continue
        seen.add(ms); rows.append((ms, float(o), float(h), float(l), float(c), float(v)))
rows.sort(); A = np.array(rows)
cache, sess = {}, np.empty(len(A))
for i, t in enumerate(A[:, 0]):
    u = dt.datetime.fromtimestamp(t / 1000, UTC).astimezone(ET); d = (u + dt.timedelta(hours=6)).date()
    if d not in cache: cache[d] = (dt.datetime(d.year, d.month, d.day, 18, tzinfo=ET) - dt.timedelta(days=1)).astimezone(UTC).timestamp() * 1000
    sess[i] = cache[d]
B = np.column_stack([A, sess]); B.tofile("gc5m7.f64")
def ct(ms): return ms + dt.datetime.fromtimestamp(ms / 1000, UTC).astimezone(CT).utcoffset().total_seconds() * 1000
Cc = B.copy(); Cc[:, 0] = [ct(x) for x in B[:, 0]]; Cc[:, 6] = [ct(x) for x in B[:, 6]]
assert np.all(np.diff(Cc[:, 0]) > 0); Cc.tofile("gc5m7_ct.f64"); print(len(B), "bars")
