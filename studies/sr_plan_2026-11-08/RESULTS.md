# Owner's support/resistance plan — results (2026-11-08)
Rules: SPEC.md (written before testing). Code: sr_plan.py → results.txt; trades_A/B/C.csv (MAIN buffer); chart_data.json.
Gold spot 5m, Jan 2012 → Sep 2026, 1 MGC, 0.3 pt per round trip. Limit fills on touch, which is generous to the plan.

## Verdict: FAILS for every way of drawing the levels (9 of 9 variants). No profitable year in any MAIN version.
| levels (MAIN stop = 0.5 × 1H ATR, median $19) | trades | per day | win % | PF | net | years profitable |
|---|---|---|---|---|---|---|
| A. Daily highs/lows, last 5 days | 23,661 | ~6 | 27.9 | 0.82 | −$89,872 | 0 / 15 |
| B. 1-hour swing highs/lows | 28,155 | ~7 | 29.0 | 0.79 | −$118,854 | 0 / 15 |
| C. Daily floor pivots | 20,422 | ~5 | 22.9 | 0.83 | −$75,335 | 0 / 15 |
Stop checks: 0.25× ATR is worse (PF 0.66–0.76). 1.0× ATR is less bad (PF 0.84–0.88) and still loses in 14–15 of 15 years.

| A. daily H/L, by trade type | trades | PF | net | before fees |
|---|---|---|---|---|
| RANGE (buy support / sell resistance) | 15,501 | 0.80 | −$67,153 | −0.033R |
| FLIP (broken level, retest) | 8,160 | 0.86 | −$22,719 | −0.021R |
The FLIP half (his role-reversal idea) is the less bad half in all three level types, and still loses after fees.

## Why
- **Levels don't hold more than chance.** When price reached a level (A), it broke through and hit the stop 70% of the time.
  It reached the next level 22% of the time, and 8% of trades closed at the session end.
- The reward is about 3× the risk (median stop $19, target $50–83), so the plan needs to be right about 1 time in 4. It is
  right about 1 time in 4, which makes it a coin flip with a 3-to-1 payout: roughly zero before fees (−0.03R per trade).
- About 6 trades a day × $3 ≈ $4,700 a year in fees on 1 MGC turns the coin flip into a steady loss. This is the same
  cost-share story as the catalog (catalog_100_2026-11-08) and the opposite test (opposite_2026-11-08).
