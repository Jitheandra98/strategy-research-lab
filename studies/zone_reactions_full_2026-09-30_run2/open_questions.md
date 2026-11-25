# Open questions, missing data, and ambiguities

## 1. The data was rebuilt from pixels. How far to trust it

Every 5m bar in `data/bars_5m.csv` was read off the candles in your recording. `report.md` §1 has the full method and checks. What matters most:

| Check | Result |
|---|---|
| Coverage | 63,925 five-minute bars, 2 Nov 2025 → 30 Sep 2026, from 4,337 frames (one every 3 s of video) |
| Dates | Calendar walker agrees with 1,031 of 1,056 day labels OCR'd independently off the chart axis (97.6%) |
| 4H highs vs the chart's own 4H header | Within 0.3 pt 80%, within 1 pt 86%; our high too **low** by >1 pt 10.6%, too high 3.7% |
| 4H lows | Within 0.3 pt 83%, within 1 pt 89%; our low too **high** by >1 pt 7.9%, too low 3.3% |
| Bar-to-bar continuity (open vs previous close) | Median 0.10 pt, 90th percentile 1.9 pt |

**Known bias:** errors lean towards **wicks that are too short**. STATION2 draws its signal labels directly over the candles next to entries, and 38% of bars had a label touching them in every frame. Short wicks mean stops look slightly less likely to be hit than they were, so the backtest leans **optimistic**. `report.md` §4 re-ran the key result with every label-covered wick extended by 1 pt and by 3 pt. The 4H result survived both; the 5m result stayed at about zero.

**Not recoverable from the video:** volume (not tested at all), intrabar order (the simulator assumes the stop was hit first), and about 5 days in early February 2026 whose dates couldn't be verified, so they were excluded.

**Best next step:** export real MGC 5m data (TradingView CSV export, Databento, or CME DataMine) for the same dates and run `pipeline/07_build.py` onwards on it. The zone engine, events and analysis run unchanged, and the results can be compared with this rebuild. That removes every pixel-reading caveat above.

## 2. Ambiguities in "trust the zones"

1. **Which 4H zones?** Two sets appear on your screen. (a) Zones computed by STATION2 on the **4H pane**. (b) 4H FVGs **imported onto the 5m pane**, labelled `4H`. Both were tested (`zone_tf=4h` and `zone_kind=4H`) and behaved alike. The strategy uses both.
2. **The 60-zone cap hides 4H zones on your 5m chart.** 21% of imported 4H zones (36 of 169) were evicted from the 5m pane while still unbroken, after a median of about 3 days, because newer 5m zones filled the 60 slots. On the 4H pane they were still valid. If you've been reading 4H context off the 5m pane, you've missed some of it.
3. **Replay timing and reload timing differ for imported 4H zones.** In replay the zone appears when the 4H bar that completes it closes. After a chart reload, the indicator recalculates history and the same zone appears one 4H bar later. Screenshots taken live and after a reload won't match.
4. **"Consumed" happens on a wick.** STATION2 kills a zone on any wick through its far edge. This study kept those as `SWEEP_RECLAIM` when price closed back. 12% of 5m first arrivals were sweep-reclaims, so the indicator discards many zones that, by close, were still holding.
5. **Zone text and borders sit on top of candles.** Near each zone's birth, the indicator draws the box border and label text right over the candles. This had to be removed pixel by pixel. A sensitivity run that drops arrivals within 3 bars of a 4H zone's appearance changed the main result from +0.183R to +0.178R.

## 3. What could still change the conclusions

1. **One instrument, about 11 months, one regime shift.** It includes the January 2026 blow-off and the summer decline. The holdout is later data from the **same** recording, so it is not an independent market.
2. **The 4H edge is thin and concentrated in the tail.** Removing the top 5% of winners cuts +0.18R to +0.08R. A few large trend moves carry a lot of it.
3. **Costs.** 0.3 pt per round trip is assumed. The 4H setup survives double costs (+0.17R). 5m-zone trading does not: its median risk is only about 7 pt, so each extra 0.3 pt of cost costs about 0.04R.
4. **Execution.** Market entry on the next bar's open is assumed to fill at that open. Slippage beyond 1 tick on fast bars isn't modelled.

## 4. Questions for you

1. Did the replay ever jump or rewind? Stitching found a few breaks: around 28 Nov 2025 (Thanksgiving), 25 Feb 2026, 31 Aug 2026, and the unverified early-February stretch. If you know what happened at those points, the gaps can be explained or filled.
2. Do you want the 4H-zone strategy written as a TradingView `strategy()` script for forward paper-trading? That would be a new script, separate from STATION2. The current indicator's "court" can't serve as a fill ledger; see `indicator_teardown.md`.
3. Can you export real MGC data for Nov 2025 – Sep 2026? That is the single most valuable next input.
