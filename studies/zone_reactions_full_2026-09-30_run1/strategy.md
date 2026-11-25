# Zone-reaction strategy specification, research version 1

**Status: unvalidated candidate rules.** The recording motivates these tests; it does not establish a profitable system. No rule here is a recommendation to place a current trade. The objective is positive expectancy after costs with tolerable losses, not 100% winning trades.

## Keep the map; replace the decision layer

Preserve the original source's zone bounds, birth rules, insertion order, deduplication and lifecycle for the reproduction study. See `zone_engine_spec.md`. Do not replace the zones with the earlier experimental v3 strategy's anchors. Freeze an anchor at contact and retain its ID even if its drawing later disappears.

Separate native 4H anchors from 4H FVGs imported onto the 5M host. Their availability and touch/consumption histories differ. A native 5M zone can supply additional execution context; it is not automatically independent confluence, especially when it was born during the same impulse.

The entry engine has explicit states:

```text
KNOWN ZONE → CONTACT
  → closing rejection + local structure break → H1 candidate
  → two closes through far edge → ACCEPTANCE
       → later defended retest → H2 candidate
       → close back through defended edge → cancellation
  → unresolved overlap / oscillation / timeout → no entry
```

The source's wick-based CONSUMED state is logged separately. It is not the research definition of acceptance. A sweep through the far edge can therefore consume a source zone and still become an H1 rejection candidate.

## Common definitions

Use verified standard 5M candles and completed 4H context from the same feed. `[L,U]` is the frozen zone. It must have been available before the touch bar. Demand contact requires the preceding 5M low above `U` and the current low at or below `U`; supply mirrors this with highs and `L`. Distinguish gap-through events.

At contact freeze `b = ceil_to_tick(max(one tick, 0.10 × preceding completed 5M ATR14))`. The 0.10 multiplier is a registered starting parameter, not an optimized result. Require full warm-up and verified continuity. Qualifying triggers expire 30 elapsed market minutes after contact.

## H1: rejection and local recovery

For a long at demand, require a completed 5M candle that:

1. Closes at or above `U+b` and above its open.
2. Has body/range at least 0.50 and closes in the upper quarter of its range.
3. Closes above the highs of the three immediately preceding completed 5M candles.

Short at supply: close at or below `L-b`, bearish candle, lower-quarter close, and close below all three prior lows. Zero-range candles cannot qualify. A far-edge sweep is recorded as a subgroup, not required.

Enter at the next regular 5M open with adverse slippage. Long stop: below `min(L, lowest low from contact through trigger)-b`, rounded outward. Short stop mirrors it above `max(U, highest high)+b`. Skip a discontinuous next bar, an open through the stop, or an actual entry risk greater than 1.5 times the planned trigger-close risk. Never widen the stop.

## H2: acceptance and a defended retest

For a long through supply:

1. Require two consecutive completed 5M closes at or above `U+b`. At least one must be bullish, with body/range at least 0.50 and an upper-quarter close.
2. On a strictly later bar, require `low <= U+b`, `high >= U-b`, `close >= U+b`, a bullish body/range at least 0.50 and an upper-quarter close. This retest must occur within the original 30-minute qualification window.
3. Before that retest, a close at or below `U-b` cancels the continuation setup. Cancellation takes priority.

Short through demand mirrors these inequalities around `L`. Enter at the next regular 5M open under H1's gap rules. Long stop: below `min(U, lowest low from the first acceptance candle through the retest)-b`. For shorts, above `max(L, highest high over that interval)+b`.

No retest means no H2 trade. A later runaway move does not justify inserting an earlier fill. Record the last completed 4H close's agreement with the break; do not require it in the primary experiment.

## H3: congestion veto

At an otherwise valid trigger, inspect six completed 5M closes, including the trigger. With `M=(L+U)/2`, encode closes above `M+b` as +1, below `M-b` as −1, otherwise 0. Ignore zeros when counting adjacent sign changes.

Veto if at least three sign changes occur, or at least four of six closes lie inside `[L,U]`. Run one predeclared ablation without this veto. The veto is a hypothesis; a congested chart does not establish its predictive value or the eventual breakout direction.

## Exits, sizing and conflicts

- Primary target: 1.5 initial price-risk units from the actual entry fill, rounded away from entry to the tick. This is a common comparison rule, not the discovered best target.
- Close remaining exposure after 60 elapsed market minutes. Stops and targets remain active on the entry candle. No trailing stop, averaging down, partial exit or break-even move in this first experiment.
- One position in the combined portfolio. If opposite directions qualify together, abstain. For same-direction ties, choose earliest trigger, then narrower frozen anchor, then oldest source availability, then stable zone ID. Record rejected duplicates.
- Use whole contracts. Quantity is `floor(study risk budget / (stop distance × contract multiplier + assumed round-trip costs))`. Zero means skip. Margin requirements are an additional feasibility constraint. Gaps can exceed planned risk.
- Log all skipped, cancelled and unresolved opportunities. An attractive later move cannot reverse the original rule decision.

MGC represents 10 troy ounces; its 0.10 price tick is $1 per contract. Use the actual tradable contract and broker charges when evaluating fills. [CME contract overview](https://www.cmegroup.com/education/lessons/micro-gold-and-micro-silver-futures-product-overview).

Two separate, finite management alternatives are specified in `candidate_protocol.md`: trigger-candle stop and nearest opposing native 5M-zone target. Test each alone against the primary specification. Do not combine whichever pieces look best after seeing results.

## Context and no-trade rules

Record last completed 4H direction, zone kind/age, first versus repeat contact, width/ATR, 5M overlap, opposing-zone distance, hour, volume and volatility. These are explanatory variables initially, not extra optimized gates. The replay includes local rallies against a declining 4H EMA, so a universal EMA veto requires its own test.

No primary entry with unknown zone availability, missing bars, unresolved instrument/roll settings, no valid stop, an H3 veto, expired qualification, a gap-rule failure, conflicting directions or insufficient whole-contract risk capacity. Never infer order-book liquidity or institutional intent from candle pixels.

Grade A means all research rules and data requirements are satisfied. B/C mean specific rule failures. U means unevaluable data. These grades do not express win probability; none of this video's screen-only cases is certified as an executable A trade.

## Implementation order

1. Reproduce and instrument the original zone engine with stable IDs and `available_at`, without changing its geometry.
2. Export each lifecycle transition and completed candle. Add the H1/H2 state machine independently of the old signals.
3. Apply the execution/accounting rules in `backtest_spec.md` and verify edge cases against lower-timeframe records.
4. Evaluate unseen data with costs and parameter choices frozen. Only then consider promoting a research candidate to a live indicator.

This file is the final **candidate specification** from the recording study. It is not a validated finished trading system. The earlier compiled Pine experiments remain separate artifacts and do not implement this exact protocol.
