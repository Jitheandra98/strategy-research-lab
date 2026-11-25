# MARKET-STRUCTURE ENTRIES × ANY STOP AND TARGET: results (2026-11-09)
Rules: SPEC.md (written before any test). Code: engine.py, structure_exits.py → results.txt, grid.csv, finalists.csv,
finalist_trades.csv; cross_check.py → cross_check.txt (FX 5 m bars come from fx_to_5m.py). Re-running gives the same
numbers.

## The idea
Let market structure pick the entry: break of structure, change of character, retests, discount entries, liquidity
sweeps, order blocks, fair value gaps and higher lows. Then let me choose the stop (tight, medium or wide behind the
structure, or ATR-based) and the target (0.5R up to 5R, trailing behind swings, breakeven then 3R, or time only). The
question was which combination makes money.

The test: 8 entries × 4 timeframes (5 m, 15 m, 1 h, 4 h) × with or without the higher-timeframe trend × 5 stops × 9 exits
= **2,880 strategies** on gold from 2012 to 2026, at 1 MGC with real fees and slippage.

## Verdict: none of them makes money reliably. 0 of the 10 finalists pass.
The best stop and exit for each entry set was chosen on 2012–2019. The 10 best entry sets were then judged once on
2020 → Sep 2026. Every one failed at least one of the four conditions set beforehand.

| | Strategy | Stop, exit | 2012–19 t | 2020–26 $/trade (t) | Random timing, same stop/target | Years up (of 7) |
|---|---|---|---|---|---|---|
| F1 | 1 h CHoCH break | wide structure, 2R | 2.59 | +$28 (1.00) | −$44 | 5 |
| F2 | 4 h higher low | 3 ATR, trail | 1.46 | +$28 (0.54) | +$42 | 4 |
| F3 | 4 h BOS break | tight structure, BE → 3R | 1.07 | +$69 (0.85) | +$209 | 4 |
| F4 | 4 h CHoCH break | tight structure, trail | 0.99 | −$11 (−0.24) | −$15 | 2 |
| F5 | 1 h CHoCH break + 4 h trend | tight structure, 3R | 0.87 | +$49 (1.63) | +$67 | 6 |
| F6 | 4 h BOS retest | tight structure, 5R | 0.68 | −$67 (−0.89) | +$192 | 2 |
| F7 | 4 h higher low + daily trend | tight structure, trail | 0.61 | +$102 (1.87) | +$142 | 6 |
| F8 | 4 h liquidity sweep + daily trend | tight structure, 3R | 0.61 | +$36 (1.15) | +$57 | 5 |
| F9 | 4 h BOS break + daily trend | medium structure, 0.5R | 0.58 | +$100 (2.83) | +$124 | 4 |
| F10 | 4 h liquidity sweep | 3 ATR, 2R | 0.54 | +$25 (0.33) | +$43 | 5 |

The bar (all four): t ≥ 2.58, beats 95 % of random-timing copies, at least 5 of 7 years up, and still positive at double
cost.

## What it teaches
**1. The target changes how often you win, not whether you make money.** Across every timeframe (medium structure stop,
2012–2026), the net result per trade stays about the same whatever the target, while the win rate swings widely:

| Entry | TP 0.5R | TP 1R | TP 2R | TP 5R | Trail |
|---|---|---|---|---|---|
| BOS break | −0.14R (64 % win) | −0.14R (48 %) | −0.13R (37 %) | −0.10R (32 %) | −0.14R (29 %) |
| Liquidity sweep | −0.44R (53 %) | −0.43R (47 %) | −0.43R (33 %) | −0.42R (19 %) | −0.41R (18 %) |
| Order block | −0.41R (55 %) | −0.40R (44 %) | −0.41R (30 %) | −0.40R (19 %) | −0.37R (19 %) |
| Fair value gap | −0.61R (46 %) | −0.59R (42 %) | −0.61R (29 %) | −0.61R (16 %) | −0.60R (14 %) |

All 8 entries and all 9 exits are in results.txt.

**2. The timeframe matters more than the target, because of fees.** Before fees and slippage, every timeframe is close to
zero: structure entries do about as well as random ones. After fees:

| | Median stop | Before fees (TP 2R) | After fees (TP 2R) | Made money 2012–19 | Made money 2020–26 |
|---|---|---|---|---|---|
| 5 m | $22 | −0.07R | −0.38R | 0 % of 720 | 7 % |
| 15 m | $39 | −0.04R | −0.21R | 0.4 % | 31 % |
| 1 h | $84 | −0.01R | −0.08R | 11 % | 70 % |
| 4 h | $183 | −0.01R | −0.04R | 29 % | 60 % |

- **On 5 m charts:** fees and slippage take about a third of the risk on every trade (about 0.3R). Not one of the 720
  five-minute strategies made money in 2012–2019.
- **The only cells above zero after fees:** 4 h trades with a trailing or time exit (+0.03R to +0.05R). That is the slow,
  let-winners-run style, the same effect the trend-following test found. It is just as small here, and it did not
  carry over to the other markets.

**3. The 2020–2026 profits came from gold going up, not from structure.**
- Gold roughly doubled over those years, and 42 % of all 2,880 strategies made money in them (10 % did in 2012–2019).
- In every finalist that made money, the buys made it. F1's buys made +$15,820 while its sells lost $4,806. For F5 it
  was +$17,748 and −$1,434, for F7 +$17,101 and −$3,380, and for F9 +$13,096 and +$1,259.
- For 9 of the 10 finalists, random entries in the same months with the same stop and target made as much or more.

## The two closest
- **F9, 4 h BOS break with the daily trend, medium structure stop, 0.5R target.** In 2020–26 it won 74 % of trades,
  with PF 1.82 and t 2.83. Against that:
  - It lost in 3 of 7 years, and 58 % of its profit came from 2026 alone.
  - Random entries in the same months with the same stop and target did better (+$124 a trade vs +$100).
  - It was weak in 2012–2019 (t 0.58).
  - On the other 9 markets it was about zero (−0.02R a trade).
  - Its median stop is $422 a trade.
- **F1, 1 h CHoCH break, wide structure stop, 2R target.** This is the only finalist that beat random timing in gold
  2020–26 (+$28 vs −$44 a trade). Against that:
  - Its own profit is not distinguishable from zero (t 1.0), and its sells lost money.
  - Across the 9 other markets it was −0.01R a trade.
  - On the unseen GC weeks it lost $1,299 in 10 trades.

## Checks
- **Other markets:** ES, SI, HG, TY from 2022 to 2026, and 5 FX pairs from 2016 to 2026, all with the 10 finalists
  frozen.
  - 32 of the 90 cells made money, and none had t ≥ 2.
  - The best pooled result was F10 (4 h liquidity sweep): +0.03R a trade, t 0.85, up in 7 of 9 markets. That is too small
    to matter.
  - The worst was F8: −0.14R, t −3.1.
- **Unseen gold:** GC futures, trades entered 2026-09-25 → 11-08. The 10 finalists together lost $3,952 (information only).
- **A caution about the random-timing check.** The random copies are matched to the same calendar month. In a month gold
  rose, a random buy early in the month catches the move that a BOS signal only confirms later. That makes this check
  harsh on trend entries (BOS, higher low) and easy on reversal entries (CHoCH, sweeps). It changes no verdict: every
  finalist also failed at least one other condition.

## Ledger
+2,880 variants on the same 2012–2026 gold history. The total is now at least 5,666, and none has passed.
