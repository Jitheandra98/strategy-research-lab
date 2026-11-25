# Candidate protocol: original 4H zones, independent 5M decisions

Status: **research hypotheses, not a validated trading strategy**. This protocol defines what to test after verified chronological market data is available. It does not assert a win rate, an optimal entry, or profitability. Its numerical thresholds are deliberately few, fixed research choices; they were not estimated from the recording.

The user's premise is that the original indicator's zones are useful anchors. Preserve those anchors and test the decision layer independently. Trust in an anchor does not imply that it holds on every visit. The source indicator's signals and result labels must never determine which reactions enter the sample.

## 1. What remains fixed

Use the exact geometry, insertion order, deduplication, host-specific availability, and lifecycle described in `zone_engine_spec.md`. Keep the attached source unchanged. Freeze a copy of the zone bounds and state immediately before a study event, while continuing to log the original engine's state changes. A consumed box and an independently annotated rejected price move are compatible: the source consumes zones on a wick reaching their far boundary, without requiring a closing acceptance.

Run two distinct anchor cohorts. Do not pool them as identical observations:

| Cohort | Available anchors | Earliest allowed use |
|---|---|---|
| NATIVE_4H | Original chart-native OB/FVG zones on a 4H host; source direction and state preserved | After the source engine actually creates the zone on a completed 4H bar |
| IMPORTED_4H_5M | Original `kind=4H` objects in the 5M host's array; these are imported FVGs, not imported 4H OBs | After the original security request and host processing actually deliver and retain the zone |

A 4H chart-native FVG and a matching imported 4H FVG may have equal boundaries but different birth times, retention, scoring, and touch histories. Give them separate IDs and a possible common `economic_zone_group_id`; a match is not automatically an independent event. The original `request.security` timing must be reproduced rather than replaced with a more convenient mapping. TradingView documents that requested-timeframe values, offsets, and lookahead settings affect historical availability. [TradingView documentation](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/)

Native 5M zones remain measured execution context: overlap with the 4H band, distance to the nearest opposing 5M zone, and new-zone creation after displacement. They are not an extra entry requirement in this first test. Requiring every attractive 5M feature at once would hide which element helped.

## 2. Three clocks and the event unit

Keep `video_pts_seconds`, `market_bar_datetime_utc`, and `knowledge_time_utc` separate. Recording time retrieves evidence; market time measures outcomes; knowledge time prevents future information from entering a decision. Store chart timezone and its DST conversion. A selected historical candle's OHLC legend or crosshair date does not establish the newest replay candle's OHLC or time.

One event begins when verified 5M prices first enter a previously available zone from its expected side:

- Demand `[L,U]`: previous 5M low is strictly above `U`, and the current low reaches `U` or lower.
- Supply `[L,U]`: previous 5M high is strictly below `L`, and the current high reaches `L` or higher.
- The original zone must be present in its anchor cohort no later than the previous 5M close. A zone first created on the touch candle is recorded descriptively, but excluded from predictive entry research for that touch.
- The event stores a frozen `[L,U]`, the direction and original state at approach, and a monotonically increasing touch index. One event may pass through several reaction states; those states are not separate independent trials.
- Annotate events in all source states. Candidate H1/H2 entries begin only from original ACTIVE/TOUCHED states; eligibility is frozen at approach. Consumption during this reaction does not erase the event or retrospectively cancel its label.
- A recorded visit already in progress is left-censored. An unobserved interval before a supposed first touch prevents classifying it as the first touch. Duplicate replay visits to the same contract/date/zone/event are linked and counted once.

A new event for the same zone requires the previous event to have finished and **two consecutive completed 5M bars wholly on the expected approach side**. The next intrusion is a new visit. Overlapping zones are linked to one economic reaction group for clustered statistics. They must not multiply a single rally into several independent wins.

The event observation window is 60 elapsed market minutes from first touch, and the entry-qualification window is the first 30 minutes, including the touch bar. This is six 5M bars only when the data is continuous. A trading halt, session closure, or missing bar is not silently skipped to extend the window.

## 3. Independent reaction vocabulary

These labels describe price behavior. They do not inherit the original indicator's STATION/REFLEX/BREAKER signals or its consumed/inverted terminology.

| Label | Verified price definition |
|---|---|
| TOUCH | The first expected-side intrusion defined above. |
| REJECTION | After TOUCH, at least one completed 5M close returns outside the proximal edge in the expected direction by buffer `b`: demand close `>= U+b`; supply close `<= L-b`. |
| DISTAL_SWEEP | An extreme penetrates the far edge by at least one tick, then a completed close returns beyond the proximal edge within the entry-qualification window. Demand low `<= L-tick`; supply high `>= U+tick`. An optional known-swing sweep is a separate descriptive flag, not a substitute. |
| PROVISIONAL_BREAK | One completed 5M close is beyond the far edge by `b`. Demand close `<= L-b`; supply close `>= U+b`. |
| FIVE_MINUTE_ACCEPTANCE | Two consecutive completed 5M closes satisfy PROVISIONAL_BREAK on the same side. This is an operational label, not proof of institutional intent or of a completed 4H break. |
| FOUR_HOUR_ACCEPTANCE | The latest *completed and available* native 4H close is beyond the same far edge by `b`. Store the 4H close's actual availability; never apply a developing 4H candle's eventual close to earlier 5M entries. |
| RETEST | After FIVE_MINUTE_ACCEPTANCE, a later 5M bar revisits the far boundary: broken supply high edge `U` from above, or broken demand low edge `L` from below, allowing `b` tolerance. |
| RECLAIM_FAILURE | After a qualifying H1 trigger, a later 5M close returns beyond the zone's far edge in the adverse direction by `b` before the event window ends. |
| BREAK_FAILURE | After FIVE_MINUTE_ACCEPTANCE, a 5M close crosses back inside the far boundary by `b`: broken supply close `<= U-b`; broken demand close `>= L+b`. |
| UNRESOLVED | Available evidence cannot place a reaction in another category or does not cover the required window. This is not a loss. |

Use ordered state transitions rather than a single retrospective story label. A zone can first reject, then break, then retest. Retain all these timestamps.

For each event freeze `ATR14_prev` from the fully completed 5M bar immediately before touch. Set `b = ceil_to_tick(max(1 tick, 0.10 * ATR14_prev))`. ATR here defines a measurable tolerance, not the zone geometry. Unavailable ATR means the numeric candidate test is not evaluable. All primary tests keep this one tolerance; there is no search over many ATR multipliers.

## 4. H1: 4H-zone rejection confirmed by a 5M reclaim

**Hypothesis:** entering after a clear closing rejection of a previously known 4H anchor yields better net results than treating its first touch as an entry.

Long at demand; reverse inequalities and candle direction for short at supply:

1. TOUCH occurs in a pre-existing ACTIVE/TOUCHED demand anchor. Freeze `[L,U]`, `b`, and the touch index at that moment.
2. Within the first 30 market minutes, find the first completed 5M bar `t` with `close[t] >= U+b`, `close[t] > open[t]`, body/range `>= 0.50`, and `(close-low)/range >= 0.75`. Zero-range bars do not qualify.
3. Require `close[t]` to exceed the highs of **all three immediately preceding completed 5M bars**. For a short, close must be below all three prior lows, candle bearish, and close in its bottom quarter. These bars and the zone must all be known at decision time.
4. Schedule a market entry at the next regular 5M bar open; no trigger-bar fill. A stopped reaction that eventually looks good is still a stopped trade.
5. Primary long stop is one frozen buffer below `min(L, lowest low from touch through trigger)`; primary short stop is above `max(U, highest high through trigger)`. Round outward to the contract tick. Do not widen it after entry.
6. The entry is skipped if the next bar does not open exactly at the expected 5M continuation, opens through the stop, or gaps so far that initial risk exceeds 1.5 times the planned close-to-stop distance. This is an order-entry rule using information available at the open; the gap itself must still be logged.
7. Primary target is 1.5 initial price-risk units from the actual entry fill. Exit any remaining position after 60 elapsed market minutes under the timing rules in `backtest_spec.md`.

A distal sweep is a descriptive split, not required for every H1 trade. This allows the test to discover whether a sweep adds information or merely selects unusually large stop distances. Also record the native 5M zones available before touch and those formed by the trigger. A zone born with the trigger is confirmation context known at the close, not an anchor that predicted the earlier turn.

**How H1 can fail:** reclaim candles can be late, risk can be too wide, 5M momentum can exhaust immediately, and zone rejection can be only a short interruption of the 4H trend. Compare net expectancy and missed opportunities with the predeclared first-touch diagnostic, not with hand-picked successful screenshots.

## 5. H2: 4H-zone break followed by a 5M retest

**Hypothesis:** after price accepts through a known 4H zone, a subsequent defended retest is a better continuation entry than fading every contact with that zone.

Long through supply; mirror for short through demand:

1. Start from the same known-zone approach event and frozen `[L,U]`/`b`. A source-engine consumed/inverted transition is logged, but does not substitute for closing acceptance.
2. Obtain TWO consecutive completed 5M closes `>= U+b`. At least one of the two is a bullish candle with body/range `>=0.50` and close in its top quarter. The first bar need not close above a historic swing because the 4H zone boundary is the tested structure.
3. Only a strictly later bar can be the retest. Within 30 market minutes of the original touch, find the first bar with `low <= U+b`, `high >= U-b`, `close >= U+b`, `close > open`, body/range `>=0.50`, and close in its top quarter. This bar touches the tolerance band and rejects it upward.
4. Before the qualifying retest, a close `<= U-b` cancels the pending long continuation for this event. For broken demand, a close `>= L+b` cancels the short continuation. The cancel condition is checked before a retest entry.
5. Schedule the entry for the next regular 5M open. Use the same gap/continuity rules as H1.
6. Primary long stop lies below `min(U, lowest low from the first acceptance close through the retest trigger)-b`; primary short stop lies above `max(L, highest high over that interval)+b`. This invalidates the defended boundary rather than assuming price must traverse the entire old zone.
7. Use the same primary 1.5R target and 60-minute maximum holding time as H1.

Log whether the last completed 4H close also accepted the break. This first protocol does not require that close: it tests fast 5M execution while preserving a separate flag for slower 4H confirmation. Any future hard 4H-confirmation gate is a new registered experiment, not an unnoticed improvement to this one.

**How H2 can fail:** strong moves may never retest, a retest may be the beginning of a failed breakout, and repeated local probes may cause losses despite a later correct directional view. No retest means no H2 fill; do not insert a hindsight market entry into the runaway move.

## 6. H3: oscillation is a reason to abstain

**Hypothesis:** alternating 5M closes around the same 4H band identify a group where abstaining improves results after costs.

At each otherwise valid H1/H2 trigger, inspect the most recent six completed 5M closes, including the trigger. Let `M=(L+U)/2`. Assign each close `+1` above `M+b`, `-1` below `M-b`, or `0` in between. Count sign changes between consecutive nonzero entries, ignoring zero entries.

Set `oscillation_veto=true` if either:

- there are at least three sign changes in that sequence; or
- at least four of the six closes lie inside `[L,U]`.

The first candidate configuration uses the veto. Its one fixed ablation runs the identical H1/H2 rules without it. Compare both filled opportunities and the outcome distribution of skipped opportunities. A congestion screenshot followed by a breakout does not establish that congestion predicts the breakout's direction. No additional oscillator or indicator score is introduced.

## 7. Keep trade management simple and test alternatives finitely

No scaling in, averaging down, break-even move, trailing stop, partial take profit, or discretionary extension appears in this protocol. Such features need separate experiments after a stable core rule exists. One position is allowed at a time in the combined portfolio; setup-level opportunity analysis is reported separately.

Only two alternative management choices are registered, one at a time against the primary configuration:

- **STOP_TRIGGER:** use the qualifying trigger candle's low minus `b` for longs, or high plus `b` for shorts. This tests whether the broader structural stop buys useful survival or only increases risk. Do not combine this with the target alternative in the first study.
- **TARGET_NEAREST_ZONE:** freeze the nearest opposing *5M-host native* ACTIVE/TOUCHED zone available at the entry decision. A long target is one tick before the lower edge of the nearest supply wholly above the entry; a short target is one tick above the upper edge of the nearest demand wholly below it. If the opposing zone overlaps entry, no such target exists, or net planned reward/risk is below 1.5, skip. This variant intentionally changes the opportunity set and must report that change.

Nearest-zone targeting is a hypothesis, not an assumed improvement. Report how often the fixed 1.5R target lies beyond an opposing zone, but do not silently veto those baseline entries. Imported 4H zones are not substituted for native 5M targets when the latter are absent. That would be another target policy.

## 8. A/B/C grades are conformance labels

These grades describe observable compliance with this protocol, not demonstrated win probabilities:

| Grade | Meaning | Action in this candidate research |
|---|---|---|
| A | Verified chronology, known anchor, full H1/H2 confirmation, no H3 veto, valid stop and executable entry assumptions | Eligible in the primary test |
| B | Valid anchor reaction and reliable chronology, but missing a mandatory candle confirmation or rejected by H3 | Retain in the opportunity/control log; no primary trade |
| C | No valid prior anchor, a failed setup, or a rule-based entry invalidation | Retain with reason; no primary trade |
| U | Required price, time, zone identity, continuity, or knowledge-time evidence is unavailable | Unevaluable; do not mix with measured wins or losses |

Do not call a screenshot A+ because the later move is large. If the user-facing label A+ is desired, it is an alias of A **conformance**, with no performance claim attached.

## 9. Context to measure before promoting more filters

Record, but do not optimize entry decisions on, these available-at-trigger variables:

- 4H anchor kind and age; approach direction; first versus repeat touch; width/5M ATR; ACTIVE versus TOUCHED at approach.
- Last closed 4H candle direction and whether its close lies above, inside, or below the band; closed-4H acceptance flag; native and imported cohort identity.
- Overlap with a pre-existing same-direction native 5M zone; nearest opposing 5M-zone distance/risk; whether the trigger creates a new 5M FVG or OB under the unchanged source.
- Body/range, upper/lower wick ratios, rolling true-range rank, and verified exchange volume if available. Chart pixels cannot establish aggressive buyer/seller order flow.
- Market hour in the specified exchange/chart timezone; session definitions fixed before analysis; long/short; contract and roll proximity.

Volume, session, EMA alignment, and 5M-zone overlap become filters only if a later registered comparison supports them. All parts of this reviewed recording are development data, including attractive examples found late in the video. A genuine holdout must be untouched by video review and parameter selection.

The companion `backtest_spec.md` defines exact schemas, accounting, censored outcomes, small-sample handling, and prospective validation. Until those inputs and checks are available, this document is a concrete testable specification—not an evidence-validated instruction to place trades.
