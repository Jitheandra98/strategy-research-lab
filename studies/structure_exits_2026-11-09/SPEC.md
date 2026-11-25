# MARKET-STRUCTURE ENTRIES × ANY STOP AND TARGET: pre-registered 2026-11-09, before any test

## The owner's idea (in their words, then restated)
"You can switch up the profit levels and stop loss levels... You can enter anywhere in the market according to the market
structure, and you can adjust the stop loss and take profit. And give me the report what will make me money."

Restated: let market structure (swings, breaks of structure, change of character, liquidity sweeps, order blocks, fair
value gaps) choose the entries. For each kind of entry, let me choose the stop and the target, from tight to wide and
from small to large. Then report whether any combination makes money.

## Data and costs
- **Gold, main test:** XAU/USD spot 5 m bars, 2012-01-02 → 2026-09-24 (trading-video-intel/tools/pine_runner/xau5m.f64),
  on the New York clock.
  - Trades are 1 MGC ($10 per point).
  - Cost: 0.3 pt per round trip, plus 0.2 pt of slippage on every stop.
  - Targets and limit entries fill only if price trades 1 tick (0.1) through them.
- **Unseen gold:** GC futures 5 m (research/gold101/data/gc5m.csv), trades entered 2026-09-25 → 2026-11-08. This is
  information only, because six weeks is too short to judge.
- **Other markets, cross-check only (finalists only):** ES, SI, HG, TY 5 m from Nov 2022 to Nov 2026 (gold101/data), and
  EURUSD, GBPUSD, USDJPY, USDCAD, USDCHF 1 m bars built into 5 m bars, 2016–2026.
  - Results are in R (multiples of the risk on each trade).
  - Cost: 2 ticks per round trip plus 1 tick at stops (FX: 1 pip plus 0.5 pip).

## Timeframes
5 m, 15 m, 1 h and 4 h. All are built from the 5 m bars and aligned to the 18:00 New York session open. 1 day is used only
for the trend filter.

## Market structure (each timeframe on its own, swing strength k = 5)
- **Swing high** at bar p: high[p] is above the 5 highs before it and at least as high as the 5 highs after it. It is
  known only when bar p+5 closes. A swing low is the mirror.
- **Break:** a bar closes above the latest confirmed swing high (each swing level can be broken once).
  - If the last break was also up, it is a **BOS** (continuation).
  - If the last break was down, or there was none, it is a **CHoCH** (change of character).
  - Breaks down are the mirror.
  - **Bias** = the direction of the last break.
- **Protected low** of an up-break: the lowest low between the broken swing high and the break bar.

## The 8 entries (buy rules; sells are the mirror)
Market entries fill at the open of the first 5 m bar after the signal bar closes. Limit orders are live from that bar
for 20 signal-timeframe bars, and are cancelled earlier if structure breaks the other way.

| # | Entry | When | Order | Structure level (stop side) |
|---|---|---|---|---|
| 1 | BOS break | up-BOS | market | protected low |
| 2 | CHoCH break | up-CHoCH | market | protected low |
| 3 | BOS retest | after an up-BOS | limit at the broken swing-high price | protected low |
| 4 | CHoCH discount | after an up-CHoCH | limit at 50 % of the leg (protected low → highest high so far) | protected low |
| 5 | Liquidity sweep | a bar trades below the latest swing low (not yet broken or swept) and closes back above it | market | low of that bar |
| 6 | Order block | after an up-BOS or up-CHoCH: the down-close bar with the lowest low between the broken swing high and the break | limit at its high | its low |
| 7 | Fair value gap | after an up-BOS or up-CHoCH: the newest bull gap in the leg (low[j] > high[j−2], at least 0.25 ATR) | limit at the gap top | gap bottom |
| 8 | Higher low | a new swing low is confirmed above the previous one while the bias is up | market | that swing low |

## Stops (5)
ATR is the signal timeframe's 14-bar ATR at the signal.
- **Structure stops:** the structure level minus 0.1 ATR (tight), minus 0.5 ATR (medium), or minus 1.0 ATR (wide).
- **ATR stops:** the entry minus 1.5 ATR, or minus 3 ATR. These ignore structure.

The stop is never closer than one round-trip cost (gold 0.3 pt). Two cases where price is already beyond the stop:
- A market entry whose price is already past its stop is skipped.
- A limit filled past its stop counts as stopped at once.

R = the distance from entry to stop.

## Exits (9)
- **Fixed targets:** 0.5R, 1R, 1.5R, 2R, 3R or 5R.
- **Trail:** no target. Each newly confirmed swing low (after the entry) raises the stop to that low minus the stop's own
  buffer (0.5 ATR for ATR stops). The stop never moves down.
- **Breakeven then 3R:** once +1R is touched, the stop moves to entry + 0.3 pt; the target is 3R.
- **Time only:** no target.

Every trade also ends at a time limit of 100 signal bars after entry, at a 5 m close. That is 8 h on 5 m, 25 h on 15 m,
about 4 days on 1 h and about 3 weeks on 4 h.

Fill rules:
- If a stop and a target both fall in one 5 m bar, the stop counts first.
- A gap through the stop fills at the open, minus slippage.
- A limit filled inside a bar can be stopped in that bar, but cannot reach its target in that bar.

One position at a time per strategy.

## Trend filter (2)
- **None.**
- **With the higher timeframe:** trade only in the direction of the bias of the timeframe above, as of its last
  completed bar. The pairs are 5 m→1 h, 15 m→4 h, 1 h→1 day and 4 h→1 day.

## Grid
8 entries × 4 timeframes × 2 filters = **64 entry sets**. Each entry set is run with 5 stops × 9 exits, for
**2,880 strategies**. All of them go into the idea ledger.

## Chronology (fixed now)
- **Choose on 2012 → 2019** (trades entered in those years).
- **Judge once on 2020 → 2026-09-24.**

## Finalists (fixed now)
1. For each of the 64 entry sets, keep the stop + exit with the best t-statistic of net $ per trade in 2012–2019. It needs
   at least 150 trades.
2. The 10 entry sets whose best t is highest (and above 0) become the finalists, frozen with that stop and exit.

## Pass bar: every finalist is judged on 2020 → 2026-09, all four must hold
1. Net $ per trade above 0 with t ≥ 2.58 (10 finalists: a one-sided 0.5 % test).
2. It beats at least 95 % of 200 placebo copies. A placebo copy re-enters every one of the finalist's trades at a random
   bar in the same calendar month and the same time-of-day slot, with the same direction, stop distance (in points) and
   exit rule. This answers: was it the entry, or would random timing with the same stop and target do as well?
3. Profitable in at least 5 of the 7 calendar years 2020–2026.
4. Still net positive at double cost (0.6 pt per round trip plus 0.4 pt at stops).

A finalist that passes this test still faces the paper-account gate (paper_account_2026-11-09/ACCOUNT_SPEC.md §3). That
gate also asks for t ≥ 3 for anything found by searching the gold history again, real measured costs, and account
survival. Nothing goes live from this test.

## Also reported (no pass or fail)
- How many of the 2,880 strategies made money on 2012–2019, how many on 2020–2026, and whether the good ones on the first
  were good on the second.
- For each entry, how the win rate and net result change as the target moves from 0.5R to 5R.
- The finalists on the unseen GC weeks, and on the other markets (in R).
