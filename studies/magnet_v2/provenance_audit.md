# Provenance audit: reconstructed run2 data

Audit date: 2026-09-30. This review read existing code and CSVs without rerunning or modifying the run2 pipeline. Counts below were independently recomputed from its saved CSVs. It did not authenticate exchange prices or manually verify every candle against the recording.

**Conclusion:** run2 contains a video-derived reconstruction with inferred dates and repaired prices. It is useful for exploratory replay experiments and simulator checks. It is not a verified market-data export, and its earlier profitability tables do not establish a tradable edge. A causal simulator cannot remove future information already introduced while reconstructing its input candles.

## 1. Where the prices came from

The reproduction script explicitly identifies stages 1–6 as pixel reconstruction and distinguishes a later rerun on real MGC data: [run_all.sh:4](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/run_all.sh:4>). The stitching stage combines per-frame observations, generally taking medians: [04_stitch.py:268](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/04_stitch.py:268>).

The data is not a wholly random/synthetic simulation. However, some candle values are algorithmic imputations:

- Label-covered closes are replaced by the **following candle's open** at [04_stitch.py:315](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/04_stitch.py:315>).
- Missing closes are also filled from `open.shift(-1)` at [07_build.py:49](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/07_build.py:49>).
- Suspected anomalous runs are interpolated between preceding and following prices; isolated wicks can be clipped using the following candle's extremes: [07_build.py:87](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/07_build.py:87>) and [07_build.py:109](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/07_build.py:109>).
- OHLC consistency is enforced and prices are rounded to one decimal at [07_build.py:56](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/07_build.py:56>). Passing the tick-grid check therefore does not independently authenticate the prices.

Future-neighbor repair may improve visual reconstruction, but it can also change a confirmation candle, a stop touch, or an entry gap. It must remain a stated input-data limitation in every derived strategy result.

## 2. Saved data integrity and quality flags

Source files: [bars_5m.csv](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/data/bars_5m.csv>) and [bars_4h.csv](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/data/bars_4h.csv>).

| Check | Result |
|---|---|
| 5M rows | 63,925 |
| 4H rows | 1,396 |
| 5M UTC range | 2025-11-02 23:00 through 2026-09-30 16:30 |
| Duplicate or non-increasing timestamps | None in either CSV |
| Nonfinite values / internally inconsistent OHLC | None in either CSV |
| Prices outside the 0.1 grid | None after pipeline rounding |
| `label_only=True` | 24,288 rows (38.0%) |
| `body_repaired=True` | 13,817 rows (21.6%) |
| `spike_repaired=True` | 534 rows (0.84%) |
| `only_last=True` | 3 rows |
| Segments | Four: 5,255 / 16,757 / 35,948 / 5,965 bars |

These flags overlap and must not be added together. The 4H file is aggregated from the same reconstruction, so it is not an independent price source. It has 1,157 groups with 48 five-minute bars and 224 groups with 36; other groups have 6–46 bars. Some shorter groups may be scheduled sessions or holidays; completeness cannot be inferred from row count alone. The final 4H group is truncated by the recording endpoint.

The builder preserves small unobserved intraday holes inside a segment and flags them instead of supplying the absent candles: [07_build.py:61](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/07_build.py:61>). A simulator should check actual timestamp gaps, cancel stale entry orders, and avoid interpreting adjacent rows as uninterrupted five-minute intervals.

## 3. Validation claims require narrower wording

**Date agreement is fitted agreement, not held-out validation.** The date script chooses each chain's starting date by maximizing agreement with OCR day/month/year labels, then reports that winning agreement: [05_date.py:63](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/05_date.py:63>) and [05_date.py:83](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/05_date.py:83>). Those are the same labels called “held-out” in comments and the report. The reported 97.6% agreement is useful for reconstruction consistency, but it is not an independent test of timestamp accuracy.

**The strongest 4H price-agreement statistics use a selected subset.** The validator selects an endpoint by closest matching header close from up to 38 candidate candles: [06_validate.py:49](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/06_validate.py:49>). It then selects rows whose reconstructed open and close are each within 0.3 points before reporting aligned high/low results: [06_validate.py:75](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/06_validate.py:75>).

The saved [validation JSON](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/data/validation_4h_header.json:2>) contains:

| 4H session-grid comparison | High within 0.3 points | Low within 0.3 points |
|---|---:|---:|
| All 1,277 endpoint-aligned comparisons | 57.1% | 61.8% |
| Selected 519 comparisons also matching open/close | 80.2% | 82.5% |

The selected result should not be generalized to every reconstructed candle. Neither comparison establishes the intrabar sequence needed to resolve a stop and target inside one candle.

## 4. Safe subset for an exploratory anchor adapter

The [zones.csv](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/zones.csv>) subset `tf == "5m"` and `kind == "4H"` contains **169 imported 4H FVG anchors: 94 demand and 75 supply**. Every checked row has top greater than bottom, a matching `born_i`/`born_time` mapping to the 5M data, and matching segment. Widths range from 2.1 to 121.9 points.

The exported `dir` is the original direction. The engine saves `orig_dir` at creation, may flip the live `dir`, and exports `orig_dir`: [zone_engine.py:130](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/zone_engine.py:130>), [zone_engine.py:233](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/zone_engine.py:233>), [zone_engine.py:272](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/zone_engine.py:272>).

For a conservative supplied-anchor experiment:

1. Retain only identity, original direction, fixed bounds, segment, and birth timestamp.
2. Set availability to the host 5M birth candle's close, not its opening timestamp. Never allow use before that time.
3. Omit `final_state`, future touch/consume/inversion/end timestamps, and total future touch counts from selection inputs.
4. Recompute the candidate lifecycle in chronological order and record exact rules for gaps and expiry.
5. Keep provenance labeled **reconstructed replay-timing anchors** and results labeled **exploratory reconstructed-data experiment**.

The import builder deliberately assumes replay/realtime availability at the start of the next 4H interval: [07_build.py:140](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/07_build.py:140>). That is not proof of parity with the original Pine script's historical `lookahead_off` merge timing. Also, the run2 native 4H engine changes the source warm-up to 100 bars at [07_build.py:187](</Users/jitheandrasubramaniam/Desktop/hey hey/research/zone_reactions_full_2026-09-30_run2/pipeline/07_build.py:187>); its whole zone map should not be described as an exact reproduction.

## 5. What would establish stronger evidence

Use verified, timestamped MGC candles and anchors exported as they become available, with symbol/contract, feed, session, timezone, and continuous-contract adjustment recorded. Compare representative bars and anchor births against the recording. Re-run the frozen rules without tuning to the later sample, including costs and gap fills. Report reconstructed-data results separately from those independent-data results.
