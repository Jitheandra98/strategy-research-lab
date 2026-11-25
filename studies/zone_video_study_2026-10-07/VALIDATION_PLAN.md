# VALIDATION PLAN — what to test next, on data nobody has looked at

What is already done, so it is not repeated:
- V1 + V2 (Sep 2022 – Oct 2023) were used for **discovery**.
- V3 (Oct 2023 – Apr 2026) was opened **once** to score 15 frozen hypotheses (`analysis/11_hypotheses_FROZEN_*.py`, sha1 `bd7eaff…`).
- Two external sets were scored with the same frozen code: bars from 2022–2026 that no video showed, and 2016–2022 history. Neither is from a video.
- **All three splits are now spent** for these hypotheses. Any new idea found by looking at them must be tested on the fresh data below.

## 1. Data that has not been used yet (the next holdout)

| Holdout | Source | Why |
|---|---|---|
| **H-A: future gold** | OANDA:XAUUSD 15m/4H from **2026-10-08 onward**, exported from TradingView (or recorded the same way). Freeze it after ≥ 3 months (≈ 4,000 15m bars, ≈ 900 arrivals at current zone density). | Truly unseen; the same feed the indicator runs on |
| **H-B: MGC futures** | CME micro gold 15m, 2022–2026 (a broker or CME export) | The same asset on a different venue. It removes the "OANDA vs Dukascopy highs and lows" doubt |
| **H-C: other symbols** | EURUSD, NQ, BTC 15m, 2019–2026 | Tests whether the generic findings (thin bands fail, depth means failure, structure filter) are about gold or about any market |
| **H-D: the indicator's own boxes** | A Pine export of STATION2's zones (a `plot()`/`alertcondition` feed or a strategy wrapper writing top/bottom/born/state), the same periods as V1–V3 | It removes the remaining zone-matching doubt (§2 of the findings: 15m-pane agreement was only 24–59% on sampled frames) |

## 2. Exactly what to re-run, unchanged

Run `pipeline/06_build.py` → `07_events.py` → `11_hypotheses.py` on the new bars.
- Change nothing in the definitions.
- Change only the data path. For H-D, replace the zone table with the exported boxes.

Pass/fail criteria (fixed now):

| ID | Pass if (on the new holdout) |
|---|---|
| HN-A (zones = placebo) | \|R1(real) − R1(placebo)\| < 0.03 overall **and** no pre-specified subgroup has \|z\| > 3 (subgroups: first touch, STATION score ≥ 3, kind, pane, 4H trend, session) |
| H12, H13 (nulls) | R1 within ±0.04 of base, and the 95% CI contains the base |
| H11 deep arrival → failure | BRK(passed_mid) − BRK(rest) ≥ +0.20, and the CI excludes 0 |
| H08 thin → failure | BRK(height ≤ 1.3 ATR) − BRK(rest) ≥ +0.20 |
| H15 large → rarely fails | BRK(height > 2.4 ATR) ≤ 0.15 |
| HS against structure | tr2_R(against) < 0, with the CI upper bound < 0, **and** tr2_R(with) − tr2_R(against) ≥ +0.08 |
| H06 NY-AM | BRK(NY-AM) − BRK(rest) > 0 with the CI excluding 0 |
| H07 NY-PM | R1(NY-PM) − R1(rest) > 0 with the CI excluding 0 **and** real − placebo > 0. Expected to fail |

## 3. Experiments worth running (in priority order)

1. **Zone fidelity first (H-D).** Export STATION2's real boxes and re-score HN-A.
   - If the real boxes beat placebo where the port did not, the port was the problem, not the idea.
   - This is cheap and settles the biggest open doubt.
2. **ATR-scaled minimum zone size.** The indicator's fixed 2-point minimum made 72% of 2026 zones "thin". Re-run with a minimum of 1.3 × ATR(14).
   - Expect fewer zones and a lower break rate.
   - Then check whether R1 *still* equals placebo. My expectation is yes.
3. **Does the structure filter belong to zones at all?** Test HS on *every* limit order placed at a random level, ± structure.
   - If it holds there too, the filter is "don't fade a fresh 15m BOS", and zones are irrelevant to it.
4. **Exit side, not entry side.** Every reaction measure here is about 50/50. The only stable information is about *failure* and *containment*.
   - Test whether exiting an *existing* position on "deep arrival into an opposing zone" (H11) improves an existing strategy's expectancy. It probably won't, but it is the one place this information could pay.
5. **Execution-level costs.** Re-run tr*_R with 0.20 / 0.40 / 0.60 pt costs. The candidate leaf's +0.02–0.09R does not survive realistic MGC slippage.

## 4. Rules for whoever runs this

- Write the date and the sha1 of `11_hypotheses.py` into the results file before running.
- Do not change a cut-point after seeing a holdout. If you want a new variant, it is a new hypothesis and needs the *next* holdout.
- Report every hypothesis, including the ones that fail.
- Report the base rate next to every conditional rate, and report the placebo result next to every zone result.
- Paper trade only. Nothing in this study supports live money.
