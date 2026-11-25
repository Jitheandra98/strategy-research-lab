# US STOCK STRATEGIES, 1926 → 2026: pre-registered 2026-11-09, before looking at any number

## Why
Before searching "all the stocks", we check what a century of US stock data says about the strategies that already have
published evidence. The data is the Kenneth R. French Data Library (data_raw/kenfrench, provenance.csv). Its
portfolios are built from all NYSE, AMEX and NASDAQ stocks, including companies that died, so there is no survivorship
bias. Each strategy is a long–short paper portfolio of thousands of stocks, shown before trading costs.

## Strategies (monthly returns)
| Strategy | Column | Since | First published (post-publication period starts the year after) |
|---|---|---|---|
| Market: all stocks minus T-bills | Mkt-RF | Jul 1926 | — (no pre/post split) |
| Size: small minus big companies | SMB | Jul 1926 | Banz (1981) |
| Value: cheap minus expensive (book/price) | HML | Jul 1926 | Fama & French (1992) |
| Momentum: past-year winners minus losers | Mom | Jan 1927 | Jegadeesh & Titman (1993) |
| Short-term reversal: last month's losers minus winners | ST_Rev | Feb 1926 | Jegadeesh (1990), Lehmann (1990) |
| Profitability: robust minus weak | RMW | Jul 1963 | Novy-Marx (2013) |
| Investment: conservative minus aggressive | CMA | Jul 1963 | Titman, Wei & Xie (2004) |

## Measured for each
- Annual mean, volatility, Sharpe and t-stat.
- Worst month and worst calendar year.
- Share of positive years.
- Deepest drawdown and the longest time spent below a previous peak.

Each is measured over three windows: (a) the full sample, (b) before vs after publication, and (c) the last 10 years
(Oct 2016 → Sep 2026).

## Verdict rule (fixed now)
A strategy STILL WORKS if its post-publication mean is above 0 with t ≥ 2 and its last-10-year mean is above 0.
The post-publication years are this check's honest holdout, because nobody could have mined them.
Nothing here is traded. These portfolios need thousands of stocks long and short; retail versions (ETFs) pay fees and
capture only part of the effect.

## Expected, stated before
- The market is positive in every window.
- Momentum and value were strong historically but weaker after publication, and value had a long slump in the 2010s.
- Size is small.
- Reversal looks good on paper, but in practice its trading costs eat it.
