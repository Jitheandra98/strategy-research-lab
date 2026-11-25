# FIXED-EXIT ENTRY SEARCH: results (2026-11-09)
The owner's rule: every trade is 1 MGC with a $250 stop and a $100 take profit. Rules: SPEC.md (written before the test).
Code: search.py → results.txt; all 1,764 strategies are in library_results.csv. Unseen check: unseen_check.py →
unseen_check.txt.

## Verdict: 0 of 1,764 strategies pass, not even the naive bar with no luck check
A win nets $97 and a loss costs $255 or more, so the **break-even win rate is 72.4 %**.

Random entries with this exit:
| | 2012–2019 | 2020 → Sep 2026 |
|---|---|---|
| Random BUY | 70.4 % win, PF 0.91, −$6.58/trade | 73.5 % win, PF 1.05, **+$3.55/trade** |
| Random SELL | 70.5 % win, PF 0.91, −$6.53/trade | 67.5 % win, PF 0.79, −$17.60/trade |

Buying at random made money in 2020–26 only because gold went from about $1,500 to over $4,000. The same random
buying lost money in 2012–19.

- 1,252 strategies had at least 100 trades in 2012–2019.
- **Naive winners** (PF ≥ 1.15 and t ≥ 2 in 2012–19, no luck check): **0**. **With the luck check: 0. Held up in
  2020–26: 0.**
- Buy rules with PF > 1 went from 11.9 % in 2012–19 to 58.7 % in 2020–26, and sell rules from 21.7 % to 4.0 %. Their
  results rose and fell with the market, not with the rule.
- Against random timing, 1 of 1,252 strategies reached z ≥ 2 in 2012–19, where luck alone would give about 29.
- Against random entries on days in the same daily-trend state, 7 strategies reached z ≥ 2 in 2012–19 and none did in
  both periods. The best was z 2.51; the luck-adjusted bar for 1,764 tries is z 4.03.

## The closest one, checked all the way
Sell 1 MGC when a 5m bar closes down through a $100 level while gold's daily close is below its EMA 200.
- 2012–19: 94 trades, 80 % won, PF 1.50, t 1.76. It fails the bar set beforehand (100 trades and t 2).
- 2020 → Sep 2026: 126 trades, 80 % won, PF 1.54, with 80 of the trades in the 2026 sell-off.
- Against random sells on the same downtrend days: z 1.80 and 2.55, both under the luck bar of 4.03.
- **Unseen MGC futures, Sep 25 → Nov 6 2026.** Gold was in a daily downtrend the whole time, falling from $4,320 to $3,884,
  which is exactly the condition this rule waits for. Result: **38 trades, 25 won (66 %; 72.4 % needed), −$890.**

It does not work.

## Corrections made during this run (both make the test fairer; neither changes the verdict)
1. The first z-scores compared each rule with random copies that kept more trades than the rule did, because random
   signals don't cluster. That inflated z: 37 strategies were at z ≥ 2 before the correction and 1 after.
2. The trend-filtered rules were first compared with random entries on all days. A comparison with random entries on
   days in the same daily-trend state was added.

## What it taught
1. With a $100 target and a $250 stop, a random entry already wins 70–74 % of the time, and the account needs 72.4 % to
   profit. The exit sets the win rate. Whether it lands above or below break-even depends on the market's direction.
2. No entry from the standard toolkit beat random timing on gold after costs. The toolkit covered moving averages,
   breakouts, RSI, Bollinger, MACD, streaks, big bars, inside bars, engulfing, stochastic, momentum, clock times,
   weekdays, opening ranges, previous highs and lows, round numbers and gaps, each run with and against the trend.
3. The only thing that made money with this exit was being long during gold's 2020–26 rise. That came from the market,
   not from a setup.

## Ledger
1,764 variants added, for at least 2,786 on this gold history. None passed.
