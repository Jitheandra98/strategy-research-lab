# Reproducible backtest contract

## Study status and boundaries

No performance backtest has been run on the supplied replay. `zones.csv` and `events.csv` contain screen observations with uncertainty and censoring, not a substitute OHLC feed. Do not feed approximate video prices into a futures execution backtest. The entire reviewed recording is development data.

Primary hypotheses and parameters are fixed in `strategy.md` and `candidate_protocol.md`. Any later change receives a new protocol version before results are examined. Keep the original zone-engine reproduction separate from a prospective change to its higher-timeframe availability or deduplication.

## Required inputs

### Bars

`instrument, contract, feed, adjustment_policy, timestamp_open_utc, timestamp_close_utc, timeframe, open, high, low, close, volume, session_id, quality_status`.

Required: complete 5M OHLCV, matching 4H bars or a verified session-aligned aggregation, and preferably 1M or tick data for ambiguous order sequencing. Store timestamps as UTC instants. Exchange timezone is metadata; daylight-saving handling must use the exchange calendar, not a hard-coded offset. Do not construct 4H bars by an arbitrary midnight UTC resample.

Check duplicates, ordering, high/low consistency, tick grid, missing bars, session breaks and contract changes. Tick-grid anomalies require feed/adjustment explanation; they are not silently rounded away. Separate continuous-chart analysis from actual-contract fills. Back adjustment and rolls can move historical levels; document the exact mapping and do not execute a nonexistent continuous contract.

### Original zones and transitions

`zone_id, economic_group_id, cohort, kind, direction, lower, upper, source_origin_time, source_confirmation_time, available_at, host_timeframe, born_host_index, state_before, state_after, touch_count, source_code_sha256, full_inputs, transition_time`.

Cohorts: native 4H, imported 4H on 5M, native 5M. Preserve original array order, width filters, deduplication, warm-up and removal policy. The OB origin candle is not its availability time. Never backdate the anchor to the candle that later supplies its bounds. Imported 4H availability must reproduce the original merge behavior before a correction is tested. [TradingView higher-timeframe data](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/).

Compare exported geometry/lifecycle against representative Pine charts, including an import boundary, duplicate rejection, same-bar birth/consumption, inversion and array eviction. A drawing disappearing is not sufficient evidence of consumption.

## Event population and chronological state

An eligible event starts with a known active/touched 4H anchor available strictly before the 5M contact bar. Freeze bounds, direction, pre-contact ATR14 and buffer. Do not rewrite the event when a zone later flips or disappears. Keep the source-engine state and independently defined reaction state as separate fields.

Rearm after at least two consecutive completed 5M bars fully outside the zone on its original approach side. If a source ID remains unavailable or consumed before a new event, it cannot create a fresh primary active-zone contact. A consumed anchor can still complete the original event's H2 acceptance/retest sequence.

Group overlapping same-timeframe/same-direction anchors as related economic opportunities using a declared interval-overlap graph at contact. Preserve member IDs. Report per-zone counts and deduplicated economic-event counts separately; never treat neighboring/overlapping reactions as independent samples.

The observation window is 60 elapsed market-clock minutes after contact; the trigger window is 30 minutes. A trigger whose scheduled entry falls after the qualification deadline is rejected. Entry and setup clocks are distinct. A trading halt, missing bar or recording boundary does not become a normal failure or a win; record censoring.

## Exact signal chronology

For a bar opening at `t` and closing at `t+5m`, compute the trigger only at `t+5m`. The earliest market entry is the next bar opening at `t+5m`, with adverse slippage and no latency advantage. All zone/context inputs must have `available_at <= trigger_close`. Require the zone itself to predate the contact bar.

For ATR use Wilder's true-range average over 14 completed 5M bars, initialized consistently with Pine; verify warm-up agreement before signal comparison. Freeze ATR at the completed bar immediately before contact. Do not use the fill candle's final ATR, high or low to decide its opening order.

H1/H2 and the gap, cancel and congestion inequalities are those in `strategy.md`. Test boundary equality explicitly. No favorable intrabar ordering is inferred from a 5M OHLC candle.

```text
for each verified 5M bar, in chronological order:
    at open:
        process existing stop gaps using actual open and adverse slippage
        handle scheduled time exit, unless already stopped
        validate and fill previously scheduled entry
        set target from actual fill and precomputed stop
    during bar:
        evaluate active stop/target, including new positions
        use lower-timeframe sequence when complete; otherwise mark ambiguity
    at close:
        update original zone-engine state in source order
        update pre-existing research events and record all transitions
        qualify H1/H2, apply veto/conflict/continuity rules
        schedule next-open entry; never fill it in the trigger bar
        start new contacts only from zones available before this bar
```

For next-open gap gating, compare actual slipped fill-to-stop risk with 1.5 times planned trigger-close-to-stop risk. Skip if the open or slipped fill is already through the stop or if the next bar is not the expected regular 5M bar. Event comparisons retain these skipped candidates.

## Execution and cost accounting

- Input the actual broker round-trip commission/exchange fees per contract. Missing commission is not zero. Keep a gross diagnostic separately, labelled gross.
- Register primary adverse slippage of one tick on each market/stop fill as an explicit simulation assumption. Stress at two and four ticks, and stress doubled fees. This does not claim one tick represents real historical execution.
- Long entry: open plus slippage; short entry: open minus slippage. Stops round away from entry. Targets round away from entry from 1.5 price-risk units. Orders are not submitted retrospectively.
- Stop gaps fill at the worse opening price plus adverse slippage, not the old stop. A stop crossed on the entry bar is active. A favorable gap beyond a resting target fills at the limit price under the conservative primary model, with no invented price improvement.
- For limit targets, require price penetration by one tick for the conservative primary fill assumption; exact touches are an ambiguity/sensitivity cohort. No queue position is inferred from candles.
- If both stop and target are reachable in one 5M bar, resolve with complete lower-timeframe data. If still ambiguous, publish stop-first and target-first bounds; use stop-first in the primary ledger. Count the ambiguous fraction explicitly.
- At exactly entry time +60 minutes, close at that regular bar's open with adverse slippage. If an opening gap has already crossed the stop, process the stop first. If the expected time/bar is missing, mark the timeout outcome censored and report it; do not hold through an unknown gap and call it a valid 60-minute exit.
- Primary report uses one contract for setup comparisons, and separately the whole-contract portfolio size rule with user-specified risk capital and margin constraints. Do not invent the user's risk budget.

Currency P&L per contract: `direction × (exit_fill-entry_fill) × 10 − round_trip_fees`. Initial price risk: `abs(entry_fill-initial_stop)`. Net R: net P&L divided by initial price risk ×10×quantity. Also report cost-inclusive budget risk separately; do not change the R denominator midtrade. Actual slippage is already in fills and must not be subtracted twice.

MGC's tick/multiplier: [CME Micro Gold overview](https://www.cmegroup.com/education/lessons/micro-gold-and-micro-silver-futures-product-overview). TradingView simulation is useful for cross-checks but retains fill assumptions: [strategy documentation](https://www.tradingview.com/pine-script-docs/concepts/strategies/).

## MFE/MAE and requested outcome fields

For each actual entry, horizons are 5, 15, 30 and 60 elapsed **market-clock minutes**, never recording seconds. Include only bars wholly within the window from the entry open through the horizon. Require complete bar coverage and known contract mapping.

For a long, opportunity MFE=`max(0,max(high)-entry_fill)`, MAE=`max(0,entry_fill-min(low))`; reverse for a short. Export price points and initial-risk units. Opportunity excursions continue to the declared horizon regardless of an earlier hypothetical exit. Trade excursions end at the actual exit and require intrabar ordering on the exit bar, otherwise bounds/ambiguity. Do not label opportunity MFE as realized profit or count a profitable later bounce after a stopped trade as a win.

`events.csv` fields for MFE/MAE, win and net_R remain blank in the current video-derived dataset. Blank means unavailable, never zero. The reason is explicit in `censoring_reason` and `performance_metrics.csv`.

## Comparators and finite experiments

Run H1 and H2 separately, then the declared one-position combined portfolio. Compare H3 on versus off. Test STOP_TRIGGER and TARGET_NEAREST_ZONE individually, not their selected combination. Keep cohorts separate before any pooled result. Record first/repeat contact, direction, regime and costs without using exploratory subgroup winners as validation.

First-touch comparator: after the first completed contact bar, enter at the next regular 5M open in the original zone direction without the H1 confirmation. Use the same frozen buffer, structural stop, 1.5R target, gap checks and 60-minute hold. This is a reproducible next-open diagnostic, not a claim to fill at the exact intrabar first-touch price.

Old indicator signals require their first knowable timestamp and the same honest fill/cost model. Its badges and scoreboards are not the ground-truth comparator ledger.

## Statistics, uncertainty and promotion

Report all candidates, exclusions, censoring, fills and closed trades. Show net mean/median R, win rate (net P&L>0), loss/breakeven rates, profit factor, drawdown, loss streak, exposure, cost share and MFE/MAE distributions. Frequency needs verified market-day/session coverage as denominator. A count of frames or screen tracks is not trading frequency.

Use confidence intervals that respect clustering: resample market weeks/economic episodes, not individual neighboring trades. Publish the bootstrap seed, block definition and replication count (10,000 proposed). With too few blocks, report descriptive uncertainty and do not claim significance. Show leave-one-week-out sensitivity and the fraction of profit from the largest winners. Win-rate intervals alone cannot establish positive expectancy.

No “best stop,” “best session” or A+ probability from a small or censored sample. Treat observed parameter winners as development choices. Reserve a genuinely unreviewed chronological period with parameters frozen; all periods visible in this recording are excluded from untouched holdout status. Purge overlapping events at split boundaries and impose an embargo of at least maximum lookback/holding dependency.

A planning gate is at least 100 closed trades per setup and enough distinct market weeks/regimes to estimate uncertainty, a positive lower bound of unseen net expectancy under conservative costs, stable sensitivity and drawdown within a predeclared capital limit. These are research gates, not guarantees or proof of sample sufficiency. If too few trades occur, collect more data rather than relax the rules after seeing results.

## Required edge-case verification

Verify: future-dated OB origin exclusion; delayed import availability; same-bar birth/consumption; shared-array duplicate suppression; sweep/reclaim with consumed source state; H2 cancellation before retest; exact 30-minute expiry; one-bar stop/target conflict; entry-bar stop; adverse stop gap; 60-minute timeout; missing bar; contract roll; partial tick-grid mismatch; zero-contract sizing; conflicting signals and day/week accounting boundaries. Save traces with bar and zone IDs. These checks validate implementation, not profitability.
