# PAPER ACCOUNT process test: results (2026-11-09)
Rules: RUN_SPEC.md (written before the run) and the ACCOUNT_SPEC.md defaults the owner chose. Code: paper_engine.py →
results.txt. Logs: logs/decisions_X.csv, logs/fills_X.csv, logs/trades_X.csv.
This is a PROCESS TEST. The strategy (spike follow MAIN) was not qualified before the run, and it is still not.

## Verdict: the engine works; the strategy fails. NO DEPLOYMENT.
- **Engine: all checks pass.** It reproduces the old study exactly (1,941 trades, +$3,963, gross difference 1e-14 pt).
  Risk was ≤ 1 % at every entry, equity reconciles to the cent, nothing was entered after a freeze, and every trade has
  two fills. Every decision is logged, including a HOLD row every 30 minutes while a trade is open.
- **Strategy:** no exit policy passes any item of the gate. All three $10,000 accounts froze in 2014.

## The three exits (same 1,943 signals, fixed 1 MGC, 0.3 pt cost + 0.2 pt stop slippage)
| Policy | Win % | PF | Net, 14 years | Per trade | t | Years profitable | Net at 0.5 pt |
|---|---|---|---|---|---|---|---|
| A: hold to 13:30 | 42.8 | 1.04 | +$2,570 | +$1.32 | 0.52 | 7 of 15 | −$1,316 |
| B: target +1R | 48.4 | 0.92 | −$4,954 | −$2.55 | −1.20 | 4 of 15 | −$8,840 |
| C: small profit +0.3R net | 69.3 | 0.92 | −$3,133 | −$1.61 | −1.10 | 3 of 15 | −$7,019 |

The small-profit exit won 69 % of its trades and still lost, which is the scalp study's lesson again. A target cuts off the
few big days that pay for all the losers. The chronological rule picked A on 2012–2019. On 2020 → Sep 2026, A had
PF 1.02 and t 0.23, so it fails.

## The $10,000 account, all limits on
| Policy | Status | Trades | End equity | Max DD | PF | Avg win / loss | Costs |
|---|---|---|---|---|---|---|---|
| A | FROZEN 2014-05-21 | 305 | $11,975 (+19.8 %) | 15.1 % | 1.15 | $121 / −$73 | $1,872 |
| B | FROZEN 2014-07-02 | 287 | $8,615 (−13.9 %) | 15.0 % | 0.84 | $53 / −$57 | $1,414 |
| C | FROZEN 2014-05-16 | 257 | $8,511 (−14.9 %) | 15.3 % | 0.70 | $19 / −$63 | $1,143 |

- A froze while it was up 19.8 %. Equity peaked at $14,002 in Oct 2013 and then fell 15 %. With no freeze, A's next 1,142
  trades would have lost another $1,532, so the freeze kept money.
- Stress tests (0.5 pt cost, 0.4 pt stop slippage, and both together): all nine runs froze too, between March 2013 and May 2014.
- Compounding worked as designed. Size went from 1 to 5 contracts as equity grew and shrank after losses.
- The daily loss limit never fired. With one trade a day at 1 % risk, a 2 % daily loss needs a very large gap.
- Diagnostic only, freeze switched off: A ends +4.9 % after 1,447 trades, with a 36.5 % drawdown and $9,949 paid in
  costs. Costs ate about 95 % of its gross profit. B and C sank to the floor buffer (≈ $7,660) by 2015 and stopped
  trading there. The floor itself was never breached.

## Monte Carlo (10,000 reshuffled trade orders, 0.4 pt stop slippage)
- P(freeze) is 100 % for A, B and C, with the median freeze after 1.9–2.6 years.
- 95th-percentile drawdown: A 46 %, B 29 %, C 26 %. The gate needs it under 15 %.
- P(floor breach) is 0 %, so the floor buffer held in every ordering.

## The $2,000 account
It took 13–14 trades in 14 years and logged about 1,930 NO TRADE decisions, because 1 MGC almost always risked more than
$20. It ended 4–5 % down.

## Today's problem: stops grew with the gold price
| | 2012–13 | 2017–19 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| Median spike-follow stop per MGC | $67–69 | $36–40 | $101 | $175 | $340 |
| Signals a $10,000 account can afford at 1 % | ≈ 76 % | 92–98 % | 44 % | 11.5 % | 1.4 % |

Taking a median 2026 signal at 1 % risk would need about $34,500 of equity. The 14-year averages hide this.

## Forward-like check: MGC1! 5m, Sep 25 → Nov 6 2026 (this rule never saw it)
There were 15 signals, with stops of $87–$597 per MGC. At 1 MGC, A lost $2,204 (4 of 15 won), B lost $1,956 and C lost
$684 (9 of 15 won). The $10,000 account could afford only 1 of the 15, which lost $92. Fifteen trades decide nothing,
but nothing in them argues for running this.

## Gate (ACCOUNT_SPEC §3): every item fails for every policy
| Item | A | B | C |
|---|---|---|---|
| 1 Expectancy after costs | FAIL (t 0.52) | FAIL (t −1.20) | FAIL (t −1.10) |
| 2 Earlier pass bar | FAIL (PF 1.06/1.00/1.04, 7 of 15 years) | FAIL | FAIL |
| 3 Chronological | FAIL (validation PF 1.02) | not picked | not picked |
| 4 Survival | FAIL (frozen; 95th-pct DD 46 %) | FAIL | FAIL |
| 5 Affordable trades on their own | FAIL (t 0.39) | FAIL | FAIL |
| 6 Real costs | not measured | not measured | not measured |

## What the process test taught
1. The limits fired when they should have. The floor buffer stopped every losing path above the floor, and every decision
   can be traced in the logs.
2. Under 1 % risk and a 15 % freeze, a strategy with no edge freezes in about two years. That is the rules doing their job.
3. Small-profit exits raise the win rate and lower the result. This is now shown twice.
4. The freeze is measured from the peak, so it can freeze a winning account (A at +19.8 %). It can also fire on an
   ordinary loss when the account is already near the line: A was 14.8 % down and froze 15 minutes into a routine trade.
   Whether to refuse trades whose stop-out would cross the freeze line is a design choice for the review.
5. Account size and risk % have to be set from today's stops, not from the 14-year average.

## Still open
- Real costs (commission + measured slippage) are still the first missing input.
- No strategy qualifies, so the paper account stays at NO TRADE. The engine is ready for any future candidate that first
  passes a pre-registered gate.
