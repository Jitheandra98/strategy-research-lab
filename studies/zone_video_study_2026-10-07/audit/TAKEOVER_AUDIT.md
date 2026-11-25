# Takeover audit — 2026-10-07

## Verified state

All five requested deliverables exist. No extraction, OCR, download or analysis jobs were running at takeover. The saved CSV contains 27,252 event rows, 7,440 distinct modeled zone IDs, and unique event IDs: 5,992 discovery events and 21,260 validation events. These counts describe reconstructed events, not manually verified visual observations. Additional addenda in the existing report came from work beyond the conversation history available at takeover; their claimed user requests and pre-registration have not been independently verified.

## Findings that change how the report should be read

1. **Sampled versus inferred bars.** `05b_runs.py` assigns every bar between the endpoints of a replay run to video coverage. That is an inference; sampling roughly one keyframe per second cannot establish that every intermediate replay transition was captured. Of the validation rows, 10,463 are inferred between frames and 10,797 have an arrival bar dated in at least one sampled frame. Discovery has 258 inferred and 5,734 sampled-frame rows. Dated-frame presence is not visual verification of a particular zone or candle. Future exports must distinguish these provenance classes; an exact timestamp for an inferred bar is only a sampling bound.

2. **Zone quality IDs collided.** `10_export.py` pooled the integer zone IDs from the 15m and 4H panes when computing visual hit rates, then assigned a value only to 15m zones. The two panes have independent ID namespaces. The exporter is now corrected to group by `Z15_XXXXX` / `Z4_XXXXX`. Existing deliverables have been preserved; corrected per-event values are in `event_provenance.csv` alongside the old values. These values are border-detection hit rates, not probabilities that a zone is correct.

3. **Uncertainty needs clustering.** Multiple zones interact on the same bar and their outcome windows overlap. The 27,252 rows contain only 18,192 distinct bar/direction pairs. Row-level Wilson intervals and independent-row tests can overstate precision. A reproducible daily cluster bootstrap (2,000 draws) gives the following R1 estimates for resolved outcomes from sampled-frame arrivals:
   - Discovery: 49.43%, 95% bootstrap interval 47.63–51.16%, 5,584 resolved outcomes across 295 UTC days.
   - Validation: 49.68%, interval 48.21–51.08%, 10,625 resolved outcomes across 672 UTC days.
   Daily resampling is a sensitivity check; it does not eliminate all serial dependence or revalidate the feature search.

4. **Null conclusions were overstated.** Failure to find a significant effect does not prove absence of predictive information. The weaker 15m visual agreement, independent feed reconstruction and unverified sampling completeness limit the conclusion to: *this pipeline has not demonstrated a directional edge*. “Strong evidence (null)” requires an equivalence test with a predeclared practical margin and appropriate dependence handling.

5. **The candidate trading leaf is unsupported.** The report acknowledges expectancy intervals include zero but still emits LONG/SHORT with “confidence 33.” Target-hit frequency is not calibrated decision confidence. Until zone identity and execution timing are verified and net expectancy is positive out of sample, the evidence-supported model outputs WAIT or IGNORE; a research-only directional scenario can be recorded separately.

## Next work, in order

- Establish transition capture from native frame-change detection on fast-replay excerpts and recover omitted candles or mark them inferred.
- Verify persistent visual zone identity independently of the source port, especially V2 15m; inspect exact same-feed exports if available.
- Audit pre-arrival inputs: current-bar ATR and structure computed at the arrival close cannot support a limit order placed before that candle. Recompute entry-time features from closed information.
- Re-evaluate frozen hypotheses on correctly attributed zones with clustered uncertainty and matched controls. All previously inspected splits remain spent; corrections are robustness checks, not a fresh holdout.
- Amend the five deliverables with provenance, confidence limits, successful/failed counts and evidence labels after the checks above.

## Reproduction

Run `python3 pipeline/20_takeover_audit.py`. Outputs are `provenance_summary.csv`, `event_provenance.csv`, and `daily_bootstrap_R1.csv` in this directory. Original research datasets are unchanged.
