# Re-run (from this folder)
1. `python3 make_data.py` → gc5m7.f64, gc5m7_ct.f64
2. Original #131 with probes: `cat ../../trading-video-intel/data/tradingview/sources/131_QUANTUM_FLOW_INSTITUTIONAL_PRO_EDITION.pine instr_tail.pine > orig131_instr.pine`
   then `GCFILE=./gc5m7_ct.f64 node --max-old-space-size=4096 run_gc.mjs orig131_instr.pine 5 2022-11-07T00:00:00Z 2026-11-09T00:00:00Z full131ct.json`
   (about 16 min, 2.5 GB) → `python3 audit_orig.py`  (audit_orig.py reads full131ct.json)
3. v2 with probes: `cat ../../QUANTUM_FLOW_PRO_v2_MEASURED.pine v2_tail.pine > v2_instr.pine`, then replace the line
   `newDay   = timeframe.change("D")` with `newDay   = dayofmonth(time + 25200000) != dayofmonth(time[1] + 25200000)`
   (harness only: PineTS starts days at midnight, TradingView starts CME days at 17:00 CT) → v2_instr_h.pine
   `GCFILE=./gc5m7_ct.f64 node --max-old-space-size=4096 run_gc.mjs v2_instr_h.pine 5 2022-11-07T00:00:00Z 2026-11-09T00:00:00Z v2_full.json`
4. `python3 crosscheck_v2.py v2_full.json` (25 checks) → `python3 results_v2.py v2_full.json` → `python3 calib_v2.py v2_full.json`
