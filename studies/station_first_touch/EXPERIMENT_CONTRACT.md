# Station 4H first-touch experiment — frozen before results

September 28, 2026. This is a new research branch. The existing Station v2 indicator and cloud scripts are preserved. Station supplies zone locations; its prior session permissions, confluence score, route gate and entry doctrine are not inherited by the new signal models.

## Question

Does the first return to a previously completed 4H fair-value gap produce a stronger and more executable lower-timeframe reaction than later distinct returns? A reaction is not automatically an entry, and a profitable hypothetical entry is not a verified broker execution.

## Evidence and timing

Each file/feed is evaluated separately. The longer 30m file is the primary exploratory sample; the much shorter 5m file can only supply a limited separate check. Both have already informed earlier research, so chronological holdout slices are internally withheld for this experiment, not genuinely unseen independent market history.

Form 4H candles only from complete contiguous constituent bars. Three contiguous completed 4H bars define a gap. Bullish zone: first bar high to third bar low, when the third low exceeds the first high. Bearish zone: third high to first low, when the third high is below the first low. Keep the inherited 2–150 price-point width range initially; this is a declared measurement scope, not a discovered optimal threshold. All directions use mirrored rules.

A zone's creation time is the close of the third 4H bar. It cannot produce a historical trade before it exists. For reproducibility with a Pine indicator that commits state on chart-bar closes, the first lower-timeframe bar that sees the new zone records touches but cannot fill a newly planned limit on that same bar. A limit planned at that bar's close is first eligible on the following bar.

UTC-aggregated 4H bars may differ from an exchange's native 4H alignment. The Pine implementation must expose the selected clock and label this distinction. Offset sensitivity is diagnostic, not a license to choose the best holdout alignment.

## Candidates, declared in advance

- **FT_LIMIT:** pre-existing limit at the near edge on the first eligible visit.
- **REPEAT_LIMIT:** the same rule on later distinct visits, as a comparison.
- **FT_RECLAIM:** first visit, then a close back outside the near edge within three lower-timeframe bars; model a market fill only at the following open.
- **FLIP_LIMIT:** after a close through the far edge, the first properly approached inverse retest of the failed zone.
- **FT_TREND:** optional declared ablation of FT_LIMIT requiring agreement with lagged EMA50 slope; it must not be silently added to the base hypothesis.

Distinct visits require an intervening bar fully outside the zone. A stop-through gap is not an attractive retrospective limit fill. Every touch counts for freshness even if a strategy was busy or no limit was yet eligible. Close-through invalidates the original role; the opposite role has its own first-visit count. Retain a bounded history; expire zones after 20 calendar days.

## Exits and accounting

Compare two exit families: (1) beyond the zone's far edge by 0.25 lagged LTF ATR, target 2R; (2) 1 lagged LTF ATR stop, target 1.5R. Freeze risk inputs at order planning and levels at fill. Hold at most eight hours; report timeouts and incomplete end-of-data outcomes explicitly. These are experimental conventions, not the cancelled fixed $10/$15 instruction.

Each model holds at most one simulated position. Preselect one candidate by nearest prior close, with a stable age/ID tie-break; do not use the current bar's eventual extremes to choose an entry. Evaluate existing orders before replacing them. Charge round-turn sensitivity at 0, 0.5, 1 and 2 price points. Use price points and initial-risk R, not dollar P&L for unidentified feeds.

OHLC cannot reveal the order of intrabar prices. On limit-entry bars, allow a stop to be hit but do not award a target based solely on that same bar's range. On later bars with both barriers touched, use stop-first as a conservative convention and report the ambiguous count. Gap stops use the first available open, not the desired stop. No retroactive fills at the original touch price after confirmation. No unfinished bars used as completed evidence.

## Evaluation

Chronological 60/20/20 development/validation/holdout split; do not allow a trade outcome across a split boundary. Choose a candidate once on validation with a declared minimum sample; if none qualifies, do not manufacture a winner. Publish all candidates, both directions, costs, sample size, expectancy, drawdown, timeouts and clustered uncertainty. Overlapping visits and trades are dependent; individual-bar IID confidence is inappropriate. The independent-day/zone count matters more than raw visit count.

Descriptive reaction studies measure favorable and adverse excursion over fixed completed horizons. First-versus-repeat differences remain observational and may reflect zone age, trend or survival bias. Do not attribute a candle pattern to institutional inventory or treat a high classification accuracy as a profitable system.

## Delivery

A separate Pine indicator, reproducible Python research and regression tests, raw result ledgers, data audit, limitations and a concise verdict. Preserve Station's visual zone palette and show model/clock/entry/stop/target/state clearly. No inherited label may call an unvalidated profile calibrated, high probability or institutionally proven. Display switches must not change signal or zone calculations.

References: [TradingView higher-timeframe request semantics](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/) and [broker-emulator assumptions](https://www.tradingview.com/pine-script-docs/concepts/strategies/).
