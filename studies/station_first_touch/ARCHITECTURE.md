# Station First Touch — research architecture

This is the clean-room research version of Station Appointment. It preserves the familiar Station palette and makes the Station a **zone registry only**. Structure labels, oscillator scores, dashboard confidence and broad confluence do not vote on the entry.

## Causal flow

1. Import a 4H fair-value gap only after the 4H candle that defines it has closed. The Pine implementation uses the confirmed higher-timeframe request pattern; a zone cannot produce a signal on its birth bar.
2. Keep each zone as its own state: direction, near edge, far edge, birth time, first visibility, active/invalidated, first touch, repeat visits, and flip state. Overlapping zones are not collapsed into one visit.
3. A first-touch candidate is created when the lower-timeframe bar approaches from outside and intersects the near edge. There is no CHoCH/BOS gate in this experiment. A displayed touch is an observation event, not proof of a fill.
4. The Python ledger freezes the plan from the prior confirmed close, fills a limit at the near edge when the next bar reaches it, rejects an opening gap beyond the stop, checks stops before targets, and records missing horizons as censored.
5. The Python harness measures two declared management families: stop beyond the far edge by 0.25 ATR with a 2R target, and a 1 ATR stop with a 1.5R target. The Pine panel defaults to the second family for readable live observation; neither family is approved by the data.
6. A failed zone can create a separate inverse flip candidate. It is not silently treated as a normal first touch.
7. The chart panel reports the latest reaction state as `MEASURING`, `STRONG`, `MODERATE`, `WEAK`, `FAILED` or `REPEAT`. The 30m FVG context and current membership inside a 4H zone are displayed as descriptive fields only; they do not become hidden confluence votes.

## Frozen models

The harness measures `FT_LIMIT`, `REPEAT_LIMIT`, `FT_RECLAIM`, `FLIP_LIMIT`, and the declared `FT_LIMIT_EMA50` ablation under two exit families. Validation may select one configuration only if it has at least 10 uncensored observations, positive expectancy after the declared 1-point cost, and a positive lower block-bootstrap confidence bound. Holdout never selects.

## What this architecture is for

The product question is narrow: does the first return to a confirmed 4H zone contain information about the subsequent 4–8-hour excursion after controlling for the same fill and cost rules? The architecture can support that question. It also exposes whether later touches weaken, whether a close-through creates a distinct inverse-zone hypothesis, and whether 30m context adds information after the 4H location has already been known. It cannot infer institutional holdings from candles or turn a chart-side paper ledger into broker execution evidence.

The current legacy feeds have unknown symbol/venue provenance and thousands of missing lower-timeframe buckets. The present run therefore returns a research result and a no-model-selected state. A symbol-identified, continuous feed with broker-matched costs is required before sizing or live deployment.
