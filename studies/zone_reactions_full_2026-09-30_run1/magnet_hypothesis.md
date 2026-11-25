# Zone magnet hypothesis

The user's observation is testable: price may be attracted into an established 4H zone, react at the first/proximal edge, travel deeper toward the distal edge, break through, and later revisit that same area from the opposite side. Treating every colored box as a permanent wall loses this sequence. Treating every box as a guaranteed magnet is also too strong. The box can be a path objective while the reaction is conditional.

## What the closer review supports

The full sampled recording contains screen sequences consistent with all three phases:

1. **Approach and first reaction.** The price tag moves from outside toward the zone. A response may occur at the proximal edge, but the five-second samples cannot prove the exact candle wick or close.
2. **Deep fill / distal test.** Price can travel through the interior and reach the far boundary. This is not a valid blind fade. Require the lower timeframe to close back out or show a defended retest.
3. **Break and later retest.** After a full cross, the prior zone can behave as an opposite-side reference. The original source calls a wick traversal `CONSUMED` and only later can mark an inversion. The research state machine must separately test closing acceptance and retest defense.

Examples visible in the review:

- Around 00:08:00–00:09:25, a previously visible 4H supply band near 4111–4134 is followed by price above it and then a return inside while the 5M structure weakens. This is a crossing → return sequence, not proof that the initial band should be sold repeatedly.
- Around 02:00:00, price rallies into a broad 4H supply region near 4630–4672 even while the 4H EMA slopes down. A higher-timeframe trend veto would miss an earlier local reversal; buying late inside the band would still need a rejection trigger.
- Around 03:10:00, two downside probes near 4512 and 4508 precede a later recovery. The first touch is not necessarily the final reaction; a confirmed reclaim is the safer research event.

The machine layer found 60 sampled quote-position transitions, of which 57 are on the 4H pane and 3 on the 5M pane. Eighteen provisional screen tracks contain at least two transitions, and five transitions are marked as later approach/retest visits within a provisional track. These are screen counts only. The screen-track IDs are geometry matches, not source-engine IDs, and the sample can skip multiple market candles.

Across the classified transitions, the descriptive phase counts are 30 approach/touch, 15 proximal-rejection, 6 distal-crossing, 2 opposite-side-retest, and 7 full-traverse transitions. They are not independent events: one track can contribute several phases, and a sampled jump can skip the interior entirely.

## Correct translation into a setup

For a long at a 4H demand zone, the zone is a candidate magnet and the entry trigger is the lower-timeframe response:

1. Register the zone only when it was available before the approach. Freeze `[L,U]`, source cohort, width, and a small tick/ATR buffer `b`.
2. Mark the first approach when price comes from above and enters the `[L,U]` band. Do not enter on the first pixel touch.
3. If price remains inside, wait. A wick to `L` is a distal test, not automatic failure or a buy. Require a completed 5M bullish close back above `U+b` with a strong body/outer-quarter close and a local high break. This is the rejection candidate.
4. If two 5M closes accept below `L-b`, cancel the rejection idea. A later 5M retest of `L` from below, followed by a bullish defense, is a separate continuation/reclaim candidate only if it occurs within the fixed window.
5. Put the stop beyond the observed structural excursion plus `b`. Target the nearest opposing native 5M zone or use the fixed 1.5R baseline. Skip if the first obstacle leaves inadequate room.

For a short at supply, mirror the inequalities. A first touch, a distal edge test, a full cross and a retest are distinct states. A second visit cannot inherit the first visit's entry permission.

## “One setup for $30” needs a precise unit

For MGC, one contract represents 10 troy ounces and a 0.10 price tick is $1. A **$30 account P&L** is roughly a 3.0-point favorable move on one contract before costs. A **$30-per-ounce gold price move** is roughly $300 per MGC contract. These are very different targets. Neither should be assumed daily. The fixed target must be expressed in points/ticks and compared with the frozen stop and nearest obstacle.

## Rules for the next test

Run three predeclared variants on verified bars:

- `PROXIMAL_REJECTION`: first approach, lower-timeframe rejection before the distal edge, next-open entry.
- `DISTAL_REJECTION`: zone is filled to the distal edge, then the lower timeframe closes back out and breaks local structure.
- `BREAK_RETEST`: two closes beyond the far edge, then a defended retest from the opposite side.

Keep the same zone geometry and costs. Report first/repeat touch, time from approach to reaction, depth inside the zone, whether the far edge was reached, and subsequent retest. Compare fixed 1.5R with nearest-opposing-zone target as separate management variants. Do not count a reaction that occurred before the zone was available, and do not count a new zone drawn by the impulse as evidence for that impulse.

The current video can motivate and illustrate these states. It cannot supply the market-clock OHLC needed to calculate their daily frequency, MFE/MAE, win rate or net expectancy. Those fields remain blank in `events.csv` and `performance_metrics.csv` until the replay-matched data is supplied.
