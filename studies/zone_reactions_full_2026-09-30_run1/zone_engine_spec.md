# Original zone engine: exact source contract

This document describes the attached source as written. It preserves the user's trusted zone geometry as the research anchor. It does not adopt the indicator's entry signals, score threshold, advertised win rates, or narrative claims as evidence of trading performance. No source or prior research file was modified.

Source: `/Users/jitheandrasubramaniam/.codex/attachments/e0e6b649-77cb-492d-bdc4-74980604482c/Pasted text.txt`  
SHA-256: `b82bad543bb2b059e35429cb7bbc88d0f0b7aa98d9823db71650ab4278f4e03a`  
Pine v6; declaration `THE STATION APPOINTMENT v2.0`, short title `STATION2`; internal `CE_VERSION = "STA-2.1"`.

Line references below refer to that exact file. Executable code takes precedence over comments. Comments contain inconsistent historic defaults and unverified performance claims; they are not instructions for this research.

## 1. Inputs: source defaults are not verified video settings

| Parameter | Source default | Zone effect |
|---|---:|---|
| `ATR_LEN` | 14 | Host-pane ATR for score, display, liquidity tolerance |
| `EMA_LEN`, `TREND_LB` | 100, 10 | Host-pane EMA slope controls score point |
| `PIVOT_LEN` | 3 | Symmetric pivot confirmation; affects OB births |
| `FVG_MIN_PTS`, `ZONE_MAX_PTS` | 2.0, 150.0 | Absolute price-width filter for **every** zone type |
| `OB_LOOKBACK` | 20 | Search most recent opposite-color candle after structure break |
| `MAX_ZONES` | 60 | One shared array cap across all zone types and states |
| `ZONE_ARCHIVE` | 400 | Consumed-state age test, measured from birth in host bars |
| `MAX_TOUCHES` | 1 | Eligibility only; exceeding it does not itself delete a zone |
| `SIZE_LAW_ATR`, `SCORE_MIN` | 1.0, 3 | Dynamic score, star, line weight, opacity |
| `inShow4H` | true | Controls creation of imported 4H FVG anchors, despite display-oriented name |
| `inShowZones` | true | Controls box creation only; arrays still compute when false |
| `EQ_TOL_ATR`, `EQ_WINDOW` | 0.15, 60 | Liquidity-cluster tolerance and pivot separation in host bars |

Source: lines 26–42, 88–104, 137–144. These defaults cannot establish what settings the video actually used. A visible star, hue, label, or dashboard value is insufficient to reconstruct every input. Record settings read directly from the video separately and leave the remainder unknown. The `CAL_HASH` is not an exhaustive configuration signature: for example, `OB_LOOKBACK`, `ZONE_ARCHIVE`, and `inShow4H` are absent from its formula (line 66).

All zone additions and lifecycle updates require `warmedUp` and a confirmed host bar. Warm-up is `bar_index > 250` plus non-null ATR and EMA, not 250 minutes. Loaded chart-history boundaries therefore affect the anchor universe.

## 2. Zone geometry and birth

### Chart-native fair-value gap (FVG)

At the close of host bar `t`:

- Bullish: if `low[t] > high[t-2]`, propose demand `[bottom=high[t-2], top=low[t]]`.
- Bearish: if `high[t] < low[t-2]`, propose supply `[bottom=high[t], top=low[t-2]]`.

There is no displacement, middle-candle body, volume, session, or trend requirement for birth. Creation still passes the shared width and deduplication filters. The box begins at the **detection bar**, not the leftmost of the three candles. Lines 513–519.

### Chart-native order block (OB)

Pivots use `ta.pivothigh/high` and `ta.pivotlow/low` with equal left/right lengths; default confirmation delay is three host bars. The last confirmed high and low are retained. On a close above the tracked high, scan `k=1..OB_LOOKBACK` for the **first** bearish candle (`close[k] < open[k]`) and propose its entire high–low range as a demand OB. On a close below the tracked low, scan for the first bullish candle and propose its entire range as a supply OB. Doji candles do not qualify. Lines 522–600.

The scan breaks upon finding that candle even if width/deduplication rejects its zone; it does not search onward for a more suitable candidate. The box's left edge and `born` field are the structure-break bar. The historical source candle is geometry provenance, not the first tradable moment. A study that dates an OB's availability to its old source candle creates lookahead bias.

`CHoCH` versus `BOS` classifies the break against prior `structDir`. This classification is not required as a separate OB birth filter. Both directions are checked in code order; do not assume a visually assigned trend is the OB definition.

### Imported 4H FVG map

The exact request is (line 502):

```pine
[h4bl, h4bh, h4sl, h4sh, h4t] = request.security(
    syminfo.tickerid, "240",
    [low[1], high[3], high[1], low[3], time[1]],
    lookahead = barmerge.lookahead_off)
```

When `h4t` changes (or on the first eligible import), the map proposes:

- Demand: if `h4bl > h4bh`, `[bottom=high_4H[3], top=low_4H[1]]`.
- Supply: if `h4sl < h4sh`, `[bottom=high_4H[1], top=low_4H[3]]`.

The resulting `kind` is the literal string `"4H"`; it is not `"FVG"`, even though the geometry is a 4H FVG. There are no imported 4H OBs. `h4t` is the source bar's opening time. It is a change detector, not a stored zone birth time. Source origin, source confirmation, import availability, and first visible frame must be distinct research fields.

**Availability matters.** TradingView documents historical `lookahead_off` higher-timeframe updates at the end of the requested interval. Combining that merge policy with `[1]` means a historical 5M chart receives the previous completed 4H triplet at the close of the next 4H interval. The normal confirmed-data pattern for equal historical/realtime timing instead uses an offset with `lookahead_on`. This source does not use that pattern. These are documented merge mechanics; exact behavior of this recording's Bar Replay and loaded history must still be verified from its visible birth sequence. Do not silently move anchors earlier or claim the entire replay used realtime semantics. [TradingView: Other timeframes and data](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/).

The requested prices are offset completed-bar prices; the main concern here is **when they become available**, not treating the uncompleted 4H bar's changing low as fixed. Preserve original availability for reproduction. A prospective correction to availability would be a separately versioned experiment, not the same original anchor study.

## 3. Shared insertion and deduplication

`f_addZone` (lines 459–480) applies to FVG, OB, and 4H:

1. Accept width only when `FVG_MIN_PTS <= top-bottom <= ZONE_MAX_PTS`.
2. Search the existing array for a same-direction zone in state 0 or 1.
3. Compute overlap `min(new_top, old_top) - max(new_bottom, old_bottom)`.
4. Suppress the new zone if overlap is strictly greater than 50% of **the new zone's width**.
5. Otherwise create `born=bar_index`, `state=0`, `firstTouched=false`, `touches=0`; extend the box to the right.
6. If array count exceeds `MAX_ZONES`, remove the oldest insertion and delete its box regardless of economic status.

Deduplication is asymmetric and indifferent to type/timeframe. A narrow new 5M FVG inside a wider living 4H zone can disappear from the anchor set. A new 4H zone can also be suppressed by an existing native zone. Consumed and inverted zones do not block insertion. Overlap exactly 50% is not rejected. The cap includes retained consumed/inverted zones, despite the input name “Max live zones.”

Order within a confirmed host bar: **4H import → local FVG → pivot/structure and OB → lifecycle**. Insertion order can therefore affect which same-bar candidate survives. A newly added zone can be touched or consumed by the very same host bar, because there is no `bar_index > born` restriction in lifecycle processing. A frame may show only the final changed state, not a prior active state.

## 4. Lifecycle: exact transitions, not trading advice

State values: `0=ACTIVE`, `1=TOUCHED`, `2=CONSUMED`, `3=INVERTED`, `4=ARCHIVED` (lines 154–163; 642–711).

| Transition | Demand rule | Supply rule |
|---|---|---|
| New touch from expected side | `low <= top` and `low[1] > top` | `high >= bottom` and `high[1] < bottom` |
| Consume active/touched zone | `low <= bottom` | `high >= top` |
| Invert previously consumed zone | `close[1] < bottom` and `high >= bottom` | `close[1] > top` and `low <= top` |

A touch increments `touches`, sets `firstTouched=true`, and moves state 0 to 1. Consecutive candles inside the zone are **not separate touches**. Price must have fully cleared the relevant edge by the previous bar's extreme before a later touch counts. The consumption test uses a wick/extreme, not a closing break. It needs no prior recorded touch and can happen on the creation bar. This implementation's consumed state is not proof of sustained market acceptance through the zone.

Inversion is evaluated only when the zone entered the iteration already consumed; it does not occur in the same branch as fresh consumption. Inversion flips direction, sets state 3, resets `touches=0`, and leaves `firstTouched=true`. It does not require a close back beyond the retest edge. Geometry stays fixed.

Inverted zones count later expected-side touches but are never consumed again by the far-edge test. They archive at two such touches. Consumed zones archive if inversion fails and `bar_index - born > ZONE_ARCHIVE`; the age is since creation, **not** time since consumption. There is no blanket age expiry for active/touched or inverted zones. The shared capacity cap can evict any retained state before these rules apply. Archival deletes both box and array item.

For research, record both the source engine state and an independent reaction annotation. A wick sweep that consumes an original zone can still be followed by a profitable reclaim; redefining consumption as a close would change the anchor lifecycle and must not be silently substituted.

## 5. Color, text, and station scoring

| Appearance | Source meaning |
|---|---|
| Blue `#3179f5` | Demand OB |
| Pink `#f77c80` | Supply OB |
| Green `#00ff68` | Demand FVG **or imported 4H** |
| Red `#ff0008` | Supply FVG **or imported 4H** |
| Grey | Consumed zone |
| Cyan `#00BCD4` | Inverted zone currently acting as demand |
| Orange `#FF5722` | Inverted zone currently acting as supply |
| Dashed border | Touched state 1 |
| Dotted border | Inverted state 3 |
| Thicker/brighter border | Current station eligibility, not a different zone geometry |

Source: lines 296–356. Overlays, transparency, compression, and overlapping boxes can alter pixel colors, so color classification needs label/geometry checks.

Score is recalculated against current **host** ATR and EMA slope:

```text
score = 2 if width >= SIZE_LAW_ATR * host_ATR else 0
      + 1 if kind == OB else 0
      + 1 if never touched else 0
      + 1 if zone direction == host EMA slope direction else 0
eligible = state in {ACTIVE, TOUCHED}
           and touches <= MAX_TOUCHES
           and score >= SCORE_MIN
```

`trendDir` is +1 only when `EMA_now > EMA[TREND_LB]`; equality counts as -1. The comment calls the score “structure-aligned,” but it compares EMA slope, not `structDir`. Imported 4H zones use 5M ATR/slope when hosted on a 5M chart. Thus a star can appear or disappear without changed boundaries or a new reaction.

Text quirks must not be mistaken for market facts:

- `≥1ATR` is literal label text even if `SIZE_LAW_ATR` is changed from 1.0.
- “dead (3rd touch)” is hardcoded, whereas `MAX_TOUCHES` defaults to 1; under defaults the text can appear at the second counted touch.
- Inverted `kind==FVG` renders as `IFVG`; **everything else**, including imported `kind==4H`, renders as `BREAKER`. The displayed word BREAKER does not prove an original OB.
- Consumed state adds `✕`. Star, score, and touch count are omitted in that branch.

## 6. The 4H pane and a 5M pane do not share a zone state

Each indicator instance has its own arrays, warm-up, pivots, history, cap, ATR, EMA, touch counts, and lifecycle. A native FVG on a 4H pane is born on its 4H detection close, labeled `FVG`, and evaluated against 4H OHLC. The 5M map imports a 4H triplet later according to request timing, labels it `4H`, and evaluates it using subsequent **5M** bars. Imported 4H objects are not a synchronized mirror of surviving boxes on the 4H pane.

On a 4H host, the additional 240-minute request references the same timeframe with an explicit one-bar offset. It may propose the prior native 4H FVG again, but living-zone deduplication usually suppresses overlapping duplicates; already consumed zones do not suppress a fresh proposal. Do not double-count such objects as separate independent discoveries.

Study records need both `source_timeframe` and `host_timeframe`, plus `pane_id` and `replay_segment_id`. Matching boundaries across panes is a candidate link, not proof of identical object identity. Confirmation of 4H context must be restricted to the last 4H candle that was closed and available at the 5M decision time. A visible developing 4H bar can be annotated as provisional context, but its eventual close cannot become an earlier filter.

## 7. Preserve versus ignore for this research

Preserve as the original-anchor baseline:

- FVG/OB/4H geometry, creation timestamps, width filtering, insertion order, deduplication, and original lifecycle.
- Exact visible zone bounds and source/host pane provenance when code reproduction is impossible.
- Zone age, width, touch history, type, and state as explanatory variables.
- Pre-existing confirmed pivots, EQH/EQL, and other zones as candidate nearby obstacles; register their actual availability.

Do not use as ground truth or selection gate:

- `STATION BUY/SELL`, `REFLEX`, `POOL-RIDE`, `BREAKER door 2`, radar arrows, SL/TP trade boxes, outcome labels, dashboard win rates, and comments advertising return statistics.
- Star eligibility, route gate, session licenses, or strategy risk governors when choosing which zone reactions enter the dataset.
- Static EMA bias as a mandatory trading rule before zone-led research tests it.

Keep indicator signals in a separate comparison field after the event is identified. Selecting only reactions with original signals would reproduce the disputed signal filter and lose the required control group. Source signal mechanics may be described elsewhere; this contract intentionally does not repair or endorse them.

Liquidity pools are separate from zones: confirmed pivot pairs within `EQ_TOL_ATR * current_ATR` and `EQ_WINDOW` host bars create EQH/EQL, capped at 15 per side. Pools are removed once an extreme strictly crosses the level. Their lines are drawn back to pivot origin even though the pair is known only at the later confirmation. A retrospective line is not evidence that it existed at that earlier bar.

## 8. Outcome measurement contract for accelerated replay

### Three clocks must stay separate

1. `video_pts_seconds`: elapsed recording time used to retrieve a screenshot.
2. `chart_bar_open/close_datetime`: market time of each candle, including timezone and DST.
3. `knowledge_time`: earliest instant a zone, pivot, filter, or completed candle was available to the decision process.

Five minutes of video is not five minutes of market time. Replay speed can change, pause, jump, and revisit history. The crosshair timestamp may refer to an old selected bar, while the replay's current bar is elsewhere. A system clock, price-axis countdown, bottom-axis date, and OHLC hover legend are different data fields. Keep their provenance and never merge them merely because OCR returns plausible digits.

### Data quality gates

A frame extraction covering the whole duration is **temporal coverage**, not proof that every zone event was observed. Even 1-second sampling may skip multiple 5M candles at high replay speed. Scene-change sampling can capture UI transitions but miss small meaningful price changes. Record frame gaps, chart changes, crop geometry, replay segments, OCR confidence, and manual verification separately.

Image-derived chart prices are estimates unless the numerical label is independently readable. Recalibrate pixel-to-price conversion after every scale/viewport change and distinguish linear versus logarithmic scale. Require at least two reliable axis anchors and preferably a third consistency check; retain the pixel/price uncertainty interval. Candle bodies partly hidden by trade boxes, labels, dashboards, overlapping zones, or compression must be marked missing rather than interpolated. Do not label a colored chart rectangle as a trusted zone without checking the source palette, text, or persistence: SL/TP boxes also use green/red.

A plausible-looking OCR sequence is not verified OHLC. The hover legend may show the cursor-selected candle, not the newest bar. Recovering sparse closes cannot recover intrabar highs/lows, limit fills, stop ordering, or volume. No MFE/MAE or P&L should be computed from estimated sparse quotes and presented as exact.

### Event identity and cohort

One event is one first entry into a registered zone during a chronological replay segment, followed through a prespecified observation window. Give repeated approaches a touch index; identify overlapping-zone membership without counting the same price reaction as independent evidence multiple times. Revisited market dates are duplicates of the same market event. An event first seen mid-reaction is left-censored; an incomplete follow-up is right-censored. Keep both in descriptive coverage, but exclude them from statistics requiring full observed windows.

At minimum retain `event_id, zone_id, pane_id, source_tf, host_tf, video_pts, market_time, knowledge_time, reaction_label, label_confidence, evidence_frame, market_time_confidence, price_source, price_uncertainty, outcome_status, exclusion_reason`. Unknown values remain null. Confidence refers to annotation quality, not expected profitability.

### Forward horizons, risk, and trade outcomes

For an independently defined trigger with fill `E`, initial stop `S`, direction `d` (+1 long/-1 short), and initial risk `r=abs(E-S)`, measure only bars/ticks after the permitted fill:

- Long `MFE_h = max(0, max(high_after_fill_through_h)-E)`; `MAE_h = max(0, E-min(low_after_fill_through_h))`.
- Short `MFE_h = max(0, E-min(low_after_fill_through_h))`; `MAE_h = max(0, max(high_after_fill_through_h)-E)`.
- Divide by frozen initial `r` for R-normalized values. Entry/stop costs must be separately specified.
- Net realized `R = (d*(exit_fill-E) - total_cost_in_points) / r` when entry/exit fills already include any specified slippage; never subtract that same slippage twice.

The horizons 5/15/30/60 refer to elapsed **market minutes after fill**, not frame offsets. Decide in advance how session breaks are treated. If entry occurs inside a candle, that candle's pre-entry extremes are unavailable as post-entry excursions; require finer data or flag ambiguity. If stop and target both appear in the same available OHLC bar, report ambiguous ordering or use a declared conservative rule, not a favorable path assumption.

A reversal/continuation label must use a preregistered price threshold and horizon. “It eventually reversed” is not a reproducible outcome. Win rate needs a complete trade rule, costs, exclusions, denominator, and independent events. Video examples alone support hypotheses; without verified chronological OHLC or tick data, frequency denominators, average R, best stops/targets, and session profitability remain unmeasured.

### Testing discipline

Predefine a small number of rules; do not optimize dozens of thresholds on the replay. Keep chronological train/validation/test periods, group overlapping events and the same trading day, and leave a purge/embargo at least as long as the outcome horizon. Match an unconditional zone-touch baseline and an appropriate direction/regime baseline so ordinary gold trend drift is not credited to the zone signal. Report confidence intervals, event counts, cost sensitivity, losses/drawdown, and performance by regime. A+ versus B/C is an explicitly provisional rule grade until unseen data separates their outcomes.
