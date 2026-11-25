from pathlib import Path
import json
r=Path(__file__).resolve().parent
q=json.loads((r/'quality_summary.json').read_text())
def link(label,name):return f'[{label}](<{r/name}>)'
body=f'''# Gold zone-reaction research

The most useful design change is to make zone contact the **start of a decision process**. Test a completed 5M rejection of a previously known 4H zone, or acceptance through it followed by a defended retest. Keep their failures and missed opportunities in the record. The replay supplies examples of both, but it does not establish which rule is profitable after costs.

**Completed:** full-duration frame/OCR processing, original-code separation, candidate zone/event exports, annotated examples, and exact strategy/backtest specifications. **Not established:** verified market-bar reconstruction, independent setup frequency, win rate, net R, best stops/targets, session advantage, or a validated trading indicator. A 100% profitable system cannot be inferred or guaranteed from this recording.

## Coverage and what these numbers mean

The actual video lasts **03:36:53.12**, at 2560×1440 and approximately 59.16 fps. The complete recording was sampled every five seconds, with additional one-second samples around visual changes. No original input or prior output was overwritten.

| Measurement | Result |
|---|---:|
| Baseline frames, no extraction failures | {q['baseline_frames']:,} |
| Additional one-second refinement frames | {q['scene_refinement_frames']:,} |
| Total extracted, OCR-processed frames | {q['total_frames']:,} |
| Sampled visual-change candidates refined | 136 |
| Maximum gap between sampled recording offsets | {q['frame_gap_max_seconds']} seconds |
| Last sampled offset | 03:36:52 |
| Chart-pane observations | {q['panes']:,} |
| Panes passing price-axis fit | {q['calibrated_panes']:,} |
| Panes with a parsed contract-tag quote | {q['quote_panes']:,} |
| Quote/axis consistency checks passed | {q['consistent_quote_panes']:,} |
| Frame-level zone candidates | {q['zone_observations']:,} |
| Provisional geometry tracks | {q['provisional_zone_tracks']:,} |
| Sampled quote-position transition candidates | {q['machine_transition_candidates']:,} |
| Separately labelled manual descriptive episodes | {q['manual_descriptive_events']} |
| Certified executable trades / measured win rate | 0 / unavailable |

The last row means no trade is certified from the screen dataset; it does not mean the market offered zero opportunities. Zone observations repeat across frames. Tracks can split or merge incorrectly. These are **extraction counts**, not market setup counts or evidence of an edge.

All {q['total_frames']:,} frames have full-image fast OCR and accurate price-strip OCR; {q['ocr_merge']['full_accurate']} also have full-image accurate OCR. The merged parser prefers those full-accurate results where available. Axis models are fitted separately per pane/frame, including logarithmic scaling. A good fit does not establish correct box pairing or source-zone identity.

This is a full-duration **sampled computational pass**, supplemented by selected manual inspection, not continuous human-style viewing of every video frame or complete reconstruction of every 5M candle. Scene candidates come from changes between sampled chart thumbnails; they are not an exhaustive native-frame shot detector. Accelerated replay can skip market candles even between one-second captures. The frame and interval indexes make coverage auditable.

## What the source actually does

The attachment is Pine v6 `STATION2`, with internal version text `STA-2.1`. Its three anchor sources are chart-native three-candle FVGs, full-range order blocks found after a confirmed structure break, and imported 4H FVGs. Geometry is preserved as the user's trusted research premise; whether any particular zone holds remains an empirical question.

Four details materially change how to interpret the replay:

1. **4H on a 5M host is a separate cohort.** Imported anchors use the host's lifecycle, ATR and scoring. Their touches can differ from native 4H touches.
2. **Consumption is a far-edge wick test.** It is not two closing acceptances through the zone. A visually convincing sweep/reclaim can already have consumed the source zone.
3. **Zone birth and source-candle time differ.** An OB's old opposite candle supplies its bounds only after the later structure break. A new zone created during an impulse is not prior evidence predicting that impulse.
4. **The shared array suppresses overlapping additions.** A same-direction living zone can suppress a new one irrespective of type/timeframe when overlap exceeds half the new zone's width. Missing 5M boxes do not prove missing local structure.

The exact contract, parameters and lifecycle are in {link('zone_engine_spec.md','zone_engine_spec.md')}. Original entry profiles and accounting issues are in {link('entry_layer_audit.md','entry_layer_audit.md')}. Source comments and advertised statistics were treated as untrusted claims, not instructions or validation.

The source's offset 4H request uses `lookahead_off`; its historical availability differs from the conventional confirmed-value delivery pattern. Preserve its original timing in the reproduction, then test a separately versioned correction. [TradingView higher-timeframe documentation](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/).

## The most informative visible sequences

All timestamps below are **recording offsets**. Prices are displayed quotes or approximate readings. These are selected explanatory examples, not an unbiased performance sample or proof that a proposed trigger existed in time.

| Recording position | Visible observation | What to test / what it cannot prove |
|---|---|---|
| 00:08:00 → 00:08:45 → 00:09:25 | A 4H supply band near 4111–4134 exists before price rises to 4153.9, then returns to 4128.9 while 5M breaks down. | Separate crossing, acceptance, defended retest and failed return. No exact H2 fill or win is certified. |
| 02:00:00 | A strong 5M rally reaches 4643.8 inside a broad 4H supply area near 4630–4672 while the 4H EMA declines. | Early local reversal and late entry into supply need different evaluation. A universal 4H EMA veto has a visible counterexample, not a measured failure rate. |
| 02:35:00 | A local rebound near 4075–4081 fails before a displayed quote of 4048.3; earlier buy labels remain visible. | Test cancellation after failed recovery and continuation confirmation. Labels are not a verified order ledger. |
| 03:00:00 | A strong rise is followed by a probe around 4286 near demand and recovery to 4310 toward supply. | Compare structural and candle stops, and measure the next obstacle. Do not assume the wider stop or closer target wins. |
| 03:10:00 | Probes near 4512 and then 4508 precede a recovery to 4565.5. | Test completed reclaim plus local structure confirmation. The first low cannot be called the safe entry in hindsight. |
| 03:36:50–end | A final buy annotation appears near 4188.6 with no full future horizon; screen state differs from replay. | Keep the ending right-censored. A future-space crosshair tooltip is not the current bar's date. |

Annotated evidence:

- {link('Supply before crossing','screenshots/01_supply_before_crossing.jpg')} → {link('above supply','screenshots/02_crossing_local_continuation.jpg')} → {link('return and local failure','screenshots/03_return_and_failure.jpg')}.
- {link('Local reversal meets 4H supply','screenshots/04_reversal_meets_supply.jpg')}.
- {link('Failed rebound','screenshots/05_failed_rebound.jpg')}.
- {link('Pullback inside the advance','screenshots/06_pullback_inside_advance.jpg')}.
- {link('Second downside probe','screenshots/07_second_probe.jpg')}.
- {link('Unresolved ending','screenshots/08_censored_ending.jpg')}.

## Ranked rules: evidence strength is not expected return

| Priority | Rule | Evidence status |
|---|---|---|
| 1 | Require an anchor to be known before contact; preserve native/imported cohort and source ID | Strong code/measurement requirement. Prevents retrospective selection. |
| 2 | Test H1: completed rejection beyond the proximal edge plus a strong 5M close through three prior bars | Plausible hypothesis motivated by recovery/failure examples. Net advantage unmeasured. |
| 3 | Test H2: two acceptance closes beyond the far edge, then a later defended retest | Plausible continuation hypothesis. Costs, missed runaways and failed retests may erase any advantage. |
| 4 | Test H3: abstain during repeated closing oscillation/inside-zone congestion | Unvalidated veto. Must compare skipped opportunities as well as avoided losses. |
| 5 | Compare structural stop versus trigger-candle stop, and fixed 1.5R versus the nearest opposing native 5M zone | Registered alternatives only. No “best” stop/target has been discovered. |

H1 and H2 use next-5M-open entries after confirmation, frozen invalidation, a primary 1.5R target and a 60-market-minute maximum hold. Shorts mirror longs. The first parameter values are explicitly research choices, not optimized estimates from this video. Grade A means rule/data compliance, not a win-probability claim. All screen-only examples remain grade U for executable-trade evaluation.

See {link('strategy.md','strategy.md')} for the concise rules and {link('candidate_protocol.md','candidate_protocol.md')} for the detailed hypotheses. {link('backtest_spec.md','backtest_spec.md')} defines chronological inputs, costs, gaps, same-bar ambiguity, sizing, MFE/MAE, comparators and unseen validation.

## Quantification that the evidence does and does not support

`pattern_counts.csv` counts screen-transition labels and manual examples. It must not be described as the frequency with which real zones hold or break. Only complete market time and stable zone IDs can provide that denominator. The detector can miss consumed/inverted zones and pair overlapping borders incorrectly; its confidence labels are heuristic. {link('Geometry QA notes','geometry_qa_notes.md')} explain the known errors and retained calibration artifacts.

Win rate, average R, MFE/MAE after 5/15/30/60 market minutes, session bias and best management policies are deliberately marked **not estimable** in `performance_metrics.csv`. The accelerated recording lacks a verified continuous market clock and complete exact OHLC/intrabar path. Hovered header values can refer to a different candle; contract-axis quotes are sparse screen observations, not OHLC.

Local recorder files were inspected, but their instrument/adjustment provenance and tick grid are not verified as replay-matched MGC. The 5M file covers only a short July–August interval. Substituting it would answer a different question. See {link('data_inventory.md','data_inventory.md')}.

MGC's contract size is 10 troy ounces and a 0.10 price tick is $1 per contract. Those mechanics constrain whole-contract sizing but do not establish the strategy's profitability. [CME Micro Gold overview](https://www.cmegroup.com/education/lessons/micro-gold-and-micro-silver-futures-product-overview).

## Deliverables and next implementation boundary

- {link('zones.csv','zones.csv')}: one candidate zone observation per frame, with approximate bounds, provenance, uncertainty and provisional screen track.
- {link('events.csv','events.csv')}: sampled quote-position transitions plus six separately labelled manual descriptive episodes; unavailable outcomes remain blank with reasons.
- {link('all_frame_index.csv','all_frame_index.csv')} and {link('coverage_by_interval.csv','coverage_by_interval.csv')}: complete extraction index and half-hour coverage checks.
- {link('performance_metrics.csv','performance_metrics.csv')}: requested metrics and their explicit unavailable status.
- {link('strategy.md','strategy.md')} and {link('backtest_spec.md','backtest_spec.md')}: final candidate rules and exact evaluation contract.
- {link('open_questions.md','open_questions.md')}: missing inputs and unresolved hypotheses.

The implementation should preserve the anchor engine and add stable zone/event exports, a separate H1/H2 reaction state machine, and one execution ledger. Earlier compiled Pine experiments remain separate; this report does not claim they implement or validate the present protocol. Reliable performance claims and a final deployable indicator require the replay-matched market data and unseen testing described above.
'''
with (r/'report.md').open('x') as f:f.write(body)
print('Created report.md')
