# STATION MAGNET v2 — research companion

This implements the proposed **4H zone → 5M response → distinct later visit** experiment. It is a companion to the original indicator. It does not establish a profitable system, a daily 30-point opportunity, or a 100% win rate.

Use **STATION_MAGNET_v2.pine** in this folder. The earlier `STATION_MAGNET_RESEARCH_v1.pine` and `run_magnet_backtest_v1.py` are superseded drafts with material geometry, timing and accounting defects. Their prior “smart compile” result did not validate their trading logic. The v2 source is separately checked by submitting its complete source to the Pine compiler.

## What is implemented

| Component | Purpose |
|---|---|
| `STATION_MAGNET_v2.pine` | A 5M indicator with confirmed 4H FVG anchors, reaction candidates, structural stops and export columns. No fictional fills or performance ledger. |
| `run_magnet_backtest.py` | Bar/zone validation, state transitions, conditional next-open simulation, costs, trade journal and forward excursions. |
| `test_magnet_backtest.py` | Synthetic scenarios that exercise causality, state transitions and execution. Synthetic outcomes are not market evidence. |
| `prepare_inputs.py` | Converts chart exports or isolates the earlier reconstruction into independent segments. Refuses existing output folders. |
| `provenance_audit.md` | Explains why the reconstructed data cannot verify trading profitability. |
| `reconstructed_inputs/` | Four isolated segments from the earlier reconstruction and its 169 imported 4H anchors; provenance and input hashes included. |

Original indicator source and previous research files are preserved. The source's entry signals, embedded win rates and ledger are not evidence for this experiment.

## The exact hypothesis

The user observed that a box can attract price before rejecting it, and can be revisited in a later 4H period. This experiment separates **arrival**, **response** and **execution**. “Magnet” is a descriptive hypothesis; it does not prove that price must return, or that a reaction is large enough to trade profitably.

For demand, the near edge is the box top and the far edge is its bottom. Supply reverses the edges and all directions.

1. **Arm an approach.** Require two completed 5M candles entirely outside the zone on the original approach side. Start a visit when a later candle intersects the box. A touch alone produces no entry.
2. **Track the whole visit.** Retain its low/high and freeze the edge buffer on first touch. Search for confirmation for six candles including the touch candle. Two fully outside candles reset/rearm the visit. A new visit gets fresh state; a later 4H clock boundary does not itself authorize an entry.
3. **Confirm rejection.** A completed 5M candle must close beyond the near edge plus the buffer, have a directional body ≥0.5 previous ATR, close in its outer 25%, and close beyond the previous three candle extremes. A visit that never reaches the far edge is `PROXIMAL_REJECTION`; one that reaches it is `DISTAL_REJECTION`. These labels are mutually exclusive. One confirmation attempt is consumed per visit, including a disabled, risk-rejected or competing candidate.
4. **Confirm a break separately.** Require two consecutive closes beyond the far edge plus a buffer. A reclaim resets this count. A breakout candle cannot serve as its own retest.
5. **Require a later retest.** Price must return from the breakout side into the far-edge buffer band and close back in the breakout direction with the same strong candle confirmation. This trades in the direction opposite to the original zone. Closing back through that edge's opposite buffer invalidates the flip. A missing interval also cancels the broken-zone setup. One confirmation per broken zone, with a 48-period timeout.

The default edge buffer is `max(one tick, 0.1 × previous ATR14)`. Rejection stops sit beyond both the far edge and the full visit excursion, plus 0.2 previous ATR. Retest stops sit beyond the retest wick/edge plus the same padding. Stops round outward to a tick. The stop distance must be 0.2–2.5 previous ATR. Up to three distinct rejection visits are permitted. Anchors expire after 1,200 elapsed five-minute periods; this includes market closures.

The “later 4H visit” label in Pine compares successive **touch times** against the chart's own 4H clock. Waiting within a box through the clock boundary is not a new visit. The CSV runner accepts immutable supplied anchors and does not invent an exchange-session clock from UTC boundaries.

## What is preserved, and what is an experiment

The Pine companion retains the source's imported 4H FVG **price formula**:

- Demand: top = last completed 4H low; bottom = high two 4H bars earlier.
- Supply: top = low two 4H bars earlier; bottom = last completed 4H high.
- Default width bounds: 2–150 price points.

It deliberately does not claim to reproduce every native 4H order block, every 5M box, the source's cross-timeframe deduplication, or its wick-consumption rule. All original map layers can remain visible for comparison. Overlapping research anchors retain separate identities; the closest risk-valid confirmation edge wins on a simultaneous candidate bar. The Pine display retains at most 60 anchors by default.

The original uses offset higher-timeframe data with `lookahead_off`. The companion changes availability to **offset expressions with `lookahead_on`**, so completed 4H values become available consistently at the next 4H period. It never requests the uncompleted 4H candle. This follows [TradingView's confirmed higher-timeframe request pattern](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/). Geometry and availability are separate properties; this is not a claim of exact historical/replay equivalence with STATION2.

## Execution contract in the Python runner

The signal is known only after its 5M candle closes. The runner observes the next open, includes two ticks of adverse entry slippage, and checks that the opening price has not invalidated the stop and that actual risk is still within the predeclared bounds. A missing next bar cancels the candidate.

**This is conditional execution at the opening price.** A blind market order submitted before that open cannot retroactively reject an unfavorable fill. Live automation would need to observe the new price, check the guard and submit afterwards; that delay/slippage requires separate forward measurement. The Pine companion marks candidates and does not pretend these fills already happened.

For one MGC contract, the baseline uses a $10 point value, $1 fee per side and two adverse ticks on entries and stop/time market exits. These are configurable research assumptions in `Config`, not broker fee quotes. The fixed target is 1.5 times the actual entry-to-stop distance, rounded toward the fill. Profit and loss include modeled slippage and fees; the R denominator is the actual structural price risk before costs.

Opening gaps are processed before candle extremes. A target already reached at the open precedes a later intrabar stop. When both barriers are first reached intrabar and their ordering is unknown, the stop wins and the trade is flagged ambiguous. The time exit occurs at the next observed opening price after 12 full 5M holding bars. There is one position at a time, a maximum of three fills per UTC day, and no new signal entry after an exit on the same candle.

Open trades at the dataset end are censored. Trades spanning missing bars remain in the journal but are excluded from aggregate metrics. Trade MFE/MAE includes only completed pre-exit bars; the exit-bar extrema are excluded because their ordering relative to the exit is unknown. Separate signal-based 5/15/30/60-minute excursions require complete contiguous coverage and are descriptive opportunities, not trade P&L.

The indicator's reference target is calculated from the **signal close** for display. The simulator's target is calculated from the **simulated actual fill**. They are explicitly different; no Pine/Python fill parity is asserted.

## Running it

All commands below are run from this folder. Every output path must be new.

```bash
python3 -m unittest -v test_magnet_backtest.py

python3 run_magnet_backtest.py \
  --bars reconstructed_inputs/segment_0/bars.csv \
  --zones reconstructed_inputs/segment_0/zones.csv \
  --out my_exploratory_run_01 \
  --allow-unverified \
  --provenance 'Video pixel reconstruction; repaired and inferred values'
```

For new observations, add `STATION_MAGNET_v2.pine` alongside the original map on standard MGC 5M candles and export chart data including its plots. Record the symbol/contract, continuous-contract adjustment, ETH/RTH setting, time zone, date span and script inputs with the export. Then:

```bash
python3 prepare_inputs.py chart-export \
  --chart /absolute/path/to/tradingview_export.csv \
  --symbol 'COMEX_MINI:MGC1!' \
  --out fresh_export_01

python3 run_magnet_backtest.py \
  --bars fresh_export_01/bars.csv \
  --zones fresh_export_01/zones.csv \
  --out fresh_test_01 \
  --provenance 'Record verified feed/session/date metadata here'
```

The adapter rejects ambiguous column names. An ordinary timestamped zone CSV can also be provided with `zone_id,known_at,top,bottom,direction`, where direction is +1 demand or −1 supply and `known_at` is the earliest time the immutable geometry was available. Supplying zones selected by their later success would invalidate the experiment.

## Evidence limits and next acceptance test

The existing video reconstruction contains 63,925 5M rows, but 38% are label-obscured and 21.6% have repaired bodies. Some repairs use later candles. Its dates were fitted to the same labels subsequently described as held-out validation. These facts prevent using its win rates as independent evidence. See `provenance_audit.md` for code references. The new smoke runs demonstrate pipeline behavior only, even if their profit column is positive.

Before choosing a live rule, independently export the matching raw feed, align source-zone availability, audit fills against finer data, and test untouched later observations. Compare rejection depth and first/repeat visits under the same costs and opportunity set. Preserve losing, absent and unfilled setups. Session filters, trend filters, nearest-obstacle targets, 30-point targets and automatic entries remain separate experiments; they are not inferred as improvements from this implementation.

For scale, one MGC contract represents 10 troy ounces. A $30-per-ounce gold move is approximately $300 gross per contract; $30 account P&L is approximately three price points before costs. See [CME's Micro Gold overview](https://www.cmegroup.com/education/lessons/micro-gold-and-micro-silver-futures-product-overview). Neither target is established as an everyday outcome.
