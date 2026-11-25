# SPIKE SCALP GRID: results (2026-11-09)
Rules: SPEC.md (written before the test). Code: spike_scalp_grid.py → results.txt; every combination is in grid.csv.
Gold spot 5m, Jan 2012 → Sep 2026. 1 MGC ($10/pt), 0.3 pt round-trip cost, 0.2 pt slippage on stops.

## Verdict: 0 of 432 combinations work. Spike entries do no better than random entries.
| | Look like winners in 2012–19 | Hold up in 2020–26 | Combos with PF > 1 over 14 years | Median PF | Best PF |
|---|---|---|---|---|---|
| Spike entries (the idea) | 0 | 0 | 0 % | 0.69 | 0.93 |
| Random entries, 5 seeds | 0 each | 0 | 0 % | 0.71 | 1.02 |
| Spikes, target counted first on ties (upper bound) | 0 | 0 | | | |

The best of 2,160 random-entry combinations (PF 1.02) beat the best spike combination (PF 0.93). Only 0.8 % of trades
(at most 8.3 %) were decided inside a 5m bar that touched both the stop and the target, so the fill rule does not
decide the result.

## Why: after a 5m spike, gold barely keeps going
Average move in the spike's direction after entry, before any cost:
| Spike size | 1 h, 2012–19 | 1 h, 2020–26 | 4 h, 2012–19 | 4 h, 2020–26 |
|---|---|---|---|---|
| 2.0 × ATR | −0.02 pt | −0.04 pt | −0.03 pt | −0.05 pt |
| 2.5 × ATR | +0.01 pt | +0.15 pt | −0.04 pt | +0.31 pt |
| 3.0 × ATR | +0.02 pt | +0.03 pt | −0.03 pt | +0.28 pt |
Random entries: about 0 (−0.06 to +0.03). The cost is 0.3 pt on every trade, plus 0.2 pt on every stop. The push after a
spike is a few cents to a few tens of cents, which is smaller than the cost. It is also noise next to an hourly move of several points.

## Win rate is not profit: the owner's exact shape (2.5 × ATR spike, NY 08:00–12:00, take $20)
| Stop | 1 h hold: win % | PF | 14-yr total | 4 h hold: win % | PF | 14-yr total |
|---|---|---|---|---|---|---|
| $20 | 44.8 | 0.56 | −$27,905 | 45.5 | 0.57 | −$28,819 |
| $50 | 59.7 | 0.65 | −$24,275 | 65.9 | 0.67 | −$25,350 |
| $100 | 63.6 | 0.70 | −$19,756 | 73.8 | 0.72 | −$20,905 |
| $200 | 64.7 | 0.75 | −$15,961 | 76.1 | 0.78 | −$15,484 |
| $500 | 64.8 | 0.77 | −$14,327 | 76.5 | 0.80 | −$13,103 |

A wider stop wins more often and still loses. With a $20 target and a $20 stop, each win nets $17 and each loss costs
about $25, so the account needs to win about 60 % of the time just to break even. With the same target and stop, the
spike entries won 44.8 % and random entries won 44–47 %.

## What it taught
1. On 5m gold, a big bar does not show "the true direction". What follows is a coin flip, and the costs make it a losing one.
2. Reshaping the target, stop or hold time only moves the loss around: rare big losses or frequent small ones.
3. The luck check matters. Out of 2,160 random-entry combinations, one reached PF 1.02. Search long enough and luck
   produces a winner. A test without a random-entry control can't tell that winner from a real one.

## Follow-up the same day: "how much if we increase the take profit?" (tp_ladder.py → tp_ladder.txt, tp_ladder.csv)
Same 2.5 × ATR spikes. Targets go from $20 up to $500, plus no target at all; stops are $50–$500; holds are 1 h, 4 h and
1 day. The luck check is random entries (5 seeds). That makes 240 combinations.

The owner's setup (NY AM spikes, $100 stop, 4 h hold):
| Target | Win % | Before costs $/trade | After costs $/trade | PF | 14-yr total |
|---|---|---|---|---|---|
| $20 | 73.8 | −1.61 | −4.83 | 0.72 | −$20,905 |
| $50 | 57.1 | −0.48 | −3.85 | 0.86 | −$14,402 |
| $100 | 47.7 | −0.12 | −3.58 | 0.90 | −$11,868 |
| $200 | 43.9 | +0.23 | −3.27 | 0.91 | −$10,119 |
| $500 | 43.0 | +0.52 | −2.99 | 0.92 | −$9,046 |
| none | 43.0 | +1.11 | −2.40 | 0.94 | −$7,231 |

- **No target makes the NY-morning setup profitable.** The best of all 120 NY-AM combinations reached PF 0.99, and
  random entries reached 0.93–1.02.
- Before costs, the result per trade stays around $0 at every target size. A bigger target lowers the win rate and
  raises the size of each win. The average stays where the entry puts it, near $0.
- Across all sessions, 7 of 240 combinations ended slightly above PF 1 (best: $500 target, $500 stop, 1-day hold,
  PF 1.07, +$4.62/trade, t 1.35). All 7 lost in 2012–2019 (PF 0.87–0.98) and made their money in 2020–2026, during
  gold's bull run. 0 look like winners in development.
- These are no longer $20–30 scalps: each one risks $500 to make about $5 a trade on average.

## Still open
Nothing from this idea. It is added to research/IDEA_LEDGER.md (now ≥ 1,022 variants, none passed).
