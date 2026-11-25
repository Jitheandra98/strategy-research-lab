# Missing inputs and unresolved questions

## Required before statistical trading claims

1. **Replay-matched data:** complete 5M OHLCV with instrument/feed metadata, and matching 4H/session aggregation. Prefer 1M/tick records to resolve entry-bar and stop/target ordering.
2. **Market chronology:** actual start/end market dates, pauses/jumps/revisited segments, and bar availability times. The recording spans the full 03:36:53; a full year of unique, continuous market bars has not been independently certified.
3. **Instrument mapping:** continuous-contract roll rules, back adjustment, ETH/session settings, timezone, and the actual delivery contract to use for executable prices.
4. **Exact inputs/build:** confirmation that the supplied Pine source and all inputs match both panes in the replay. Its partial configuration hash does not identify every setting.
5. **Zone identity export:** stable source IDs, origin/confirmation/availability, bounds and lifecycle transitions. Overlapping chart boxes cannot reliably provide this by OCR alone.
6. **Execution inputs:** commission/exchange fees, slippage assumptions, margin and user-specified study risk capital. None should be invented from a screenshot.
7. **Unseen evaluation period:** data that was not reviewed in this video and was not used to select rules or parameters.

## Questions the video cannot settle

- Are first-touch reactions superior to repeat contacts after costs? Screen appearances are not independent events.
- Does native 4H context outperform the imported 4H-on-5M cohort, once availability and source lifecycle are aligned?
- Do completed 5M rejection/acceptance rules improve net expectancy enough to justify later entry and missed moves?
- Does the oscillation veto help, or merely remove profitable breakouts as well as noise?
- Which structural stop or target policy is best? That needs the same complete opportunity set and execution model, not selected winners.
- Does the nearest opposing zone improve decisions beyond ordinary trend/volatility effects? Overlapping/recently born zones are correlated observations.
- Are session and volume effects real? The current quote/pixel dataset does not establish either.

## Current extraction limits

All 5-second baseline samples and one-second refinements were processed. This is not a review of every decoded video frame or every market tick. Full-image fast OCR plus accurate axis OCR was used throughout; a coarse subset also has full-image accurate OCR. Small labels, overlapping regions, faint/consumed/inverted zones, clipped boundaries and colored trade boxes remain problematic.

Machine geometry confidence is a heuristic detector score, not verified zone identity or trading confidence. `zones.csv` preserves candidates for review, including unresolved detections. Provisional screen tracks can split the same source zone or mistakenly join nearby zones. `events.csv` machine rows describe changes in sampled quote position, not certified candle touches, sweeps, closes or fills.

The ending screen loses the Replay watermark and shows a live-style countdown. Its final signal remains right-censored. Hovered OHLC and crosshair tooltips were not used as current-bar data. Audio was not transcribed. No price path or volume series was invented for occluded or skipped candles.

The requested report, datasets, screenshots and test specification are delivered. Verified profitability, market-minute excursions and a validated final trading indicator remain dependent on the inputs above. The empty performance fields state that limit explicitly.
