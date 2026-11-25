"""Stage 15 — "when it is selling and comes to the zone we buy; vice versa for the sell."
Buy at 4H demand after price falls into it / sell at 4H supply after price rallies into it.
Split by (a) 4H trend state and (b) how hard price was moving into the zone (6-bar approach in ATR).
Entry: next 5m open after the rejection close (C1). Stop beyond zone (+0.25 ATR). Target 30 pts,
and alternatively the nearest opposing live 4H zone. One position at a time, costs 0.3 pt.
"""
import sys, importlib.util
from pathlib import Path
import numpy as np, pandas as pd
OUT = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("op", Path(__file__).parent / "14_opposite.py")
sys.argv = [sys.argv[0], str(OUT)]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    op = importlib.util.module_from_spec(spec); spec.loader.exec_module(op)
ev4, tr = op.ev4, op.tr
rj = tr[tr.conf == "C1_RECLAIM"].merge(ev4[["zone_uid", "i", "dir", "split", "trend4_aligned", "approach_atr"]]
                                       .rename(columns={"i": "event_i"}), on=["zone_uid", "event_i"]).drop_duplicates("entry_i")
rj["d"] = rj.dir
rj["push"] = np.where(rj.approach_atr >= 2, "hard move into zone (>=2 ATR in 30 min)", "normal move into zone")
rows = []
stop_zone = lambda ei, d, s: s.stop
for trend in (True, False):
    for push in rj.push.unique():
        sub = rj[(rj.trend4_aligned == trend) & (rj.push == push)]
        lab = f"{'4H trend WITH the trade' if trend else '4H trend AGAINST the trade'} | {push}"
        for r in op.run(sub, lab + " | target 30", stop_zone, op.tgt30, 96):
            rows.append(r)
        for r in op.run(sub, lab + " | target opposing 4H zone", stop_zone, op.opposing_target, 288):
            rows.append(r)
res = pd.DataFrame(rows)
res.to_csv(OUT / "analysis" / "selling_into_zone.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 110)
print(res[res.split == "ALL"][["variant", "trades", "hit_target", "stopped", "avg_pts", "usd_per_mgc", "random_same_dir_avg_pts"]].round(2).to_string())
print(res[res.split != "ALL"][["variant", "split", "trades", "avg_pts"]].round(2).to_string())
