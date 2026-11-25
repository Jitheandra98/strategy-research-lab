# SPIKE SCALP GRID: pre-registered 2026-11-09, written BEFORE the test

## The owner's idea, in their words (2026-11-09)
"When there is a volatility spike towards a direction, that means the direction is true... even in a 5 minute... there
should be a spike and timings." On 1 MGC, enter with the spike and take $20–30 (a 2–3 pt move) within about an hour,
with a stop "to be safe". With a 4-hour hold, take less profit and use a wider stop. "Try all different combinations."

## Spike (fixed; only its size k is varied)
Gold spot 5m, Jan 2012 → Sep 2026, New York clock. A spike is a 5m bar that meets three conditions:
- its range is ≥ k × ATR(14, RMA) of the bars before it;
- its body is ≥ 50 % of its range;
- its direction is its colour.
Entry is at the next 5m open, which must be the very next bar. Each combination holds one position at a time.

## Grid: every combination is one strategy (3 × 4 × 3 × 6 × 2 = 432)
- Spike size k ∈ {2.0, 2.5, 3.0}
- Timing window (start of the spike bar, ET): ASIA 18:00–01:55, LONDON 02:00–07:55, NY AM 08:00–11:55, NY PM 12:00–16:55
- Take profit ∈ {2, 3, 5} pt = {$20, $30, $50} on 1 MGC
- Stop ∈ {2, 3, 5, 10, 20, 50} pt = {$20, $30, $50, $100, $200, $500}
- Time limit ∈ {1 h, 4 h}: exit at the last 5m close inside the limit

## Fills and costs (same as the paper account)
- Cost is 0.3 pt round trip ($3).
- The stop fills at the stop, or at the open if a bar opens through it, plus 0.2 pt of slippage.
- The target needs a 0.1 pt trade-through.
- If one 5m bar touches both the stop and the target, the stop counts first (the mandate's adverse rule).
- Also reported: the share of trades decided in such a bar, and the grid if the target had counted first. That version
  is an upper bound only and never counts as a pass.

## Chronological split and pass bar (fixed now)
- Development 2012–2019: a combination LOOKS LIKE A WINNER if it has n ≥ 100 trades, PF ≥ 1.15 after costs and t ≥ 2.
- Validation 2020 → Sep 2026, looked at once: it HOLDS UP if PF ≥ 1.15 and t ≥ 2 again.
- Luck check: the same 432 combinations run on random entries, with the same windows and counts and a coin-flip
  direction, for 5 seeds. If the spike grid doesn't produce clearly more winners that hold up than the random grids do,
  its winners are luck.
- A combination that holds up is still not traded. It goes to the paper-account gate (ACCOUNT_SPEC.md §3) and needs
  t ≥ 3 there, because it came out of a 432-way search.

## Expected, stated before testing
Small targets with wide stops will win often and still lose (scalp study 2026-11-07: TP1/SL50 won 96 % at PF ≈ 0.6).
The spike's direction carries a little information (spike follow beat random by +0.05R), probably less than the
0.5 pt of cost and slippage on a 2–3 pt target.
