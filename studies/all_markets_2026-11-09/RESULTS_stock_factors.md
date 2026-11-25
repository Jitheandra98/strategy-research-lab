# US STOCK STRATEGIES, 1926 → 2026: results (2026-11-09)
Rules: SPEC_stock_factors.md (written before looking at the numbers). Code: stock_factors.py → stock_factors.txt and
stock_factors_stats.csv. Data: the Kenneth R. French Data Library (public; provenance.csv). It covers all NYSE, AMEX
and NASDAQ stocks, including dead companies. The strategies are long–short paper portfolios, shown **before** trading
costs.

## Verdict: of the six famous stock strategies, none still works. Only owning the market does.
| Strategy | Before publication | After publication | Last 10 years | Still works? |
|---|---|---|---|---|
| Market: own all stocks (vs T-bills) | — | +8.33 %/yr, t 4.54 (1926–2026) | +13.03 %/yr | **yes** |
| Size (small minus big), pub. 1981 | +3.46 %/yr | +0.09 %/yr, t 0.06 | −2.57 %/yr | no |
| Value (cheap minus dear), pub. 1992 | +5.26 %/yr | +2.12 %/yr, t 1.08 | −0.16 %/yr | no |
| Momentum (winners minus losers), pub. 1993 | +8.84 %/yr | +4.50 %/yr, t 1.54 | +3.08 %/yr | no (positive but weak; −52.8 % in 2009) |
| Short-term reversal, pub. 1990 | +10.61 %/yr | +1.92 %/yr, t 0.94 | −0.96 %/yr | no |
| Profitability (robust minus weak), pub. 2013 | +3.22 %/yr | +1.95 %/yr, t 0.82 | +2.19 %/yr | no |
| Investment (conservative minus aggressive), pub. 2004 | +4.36 %/yr | +0.23 %/yr, t 0.16 | −0.48 %/yr | no |

- Every strategy was strong in the years before it was published and much weaker after.
- The years after publication are the honest test, because nobody could have mined them. Short-term reversal fell
  from +10.6 % a year to +1.9 %, and the investment strategy from +4.4 % to +0.2 %.
- The market itself: $1 in all US stocks in July 1926 grew to about $19,567 by September 2026, before tax and fees.
  $1 in T-bills grew to about $26. The price of that growth was a worst year of −44 % (1931), a deepest fall of
  −85 %, and 15.6 years before stocks regained an old peak.

## What it taught
1. Even the most famous, best-documented stock edges lost most of their power once they were published. The edges
   that remained are small and have long losing stretches.
2. The one thing that paid for 100 years was taking stock-market risk itself. That is investing, and it comes with
   crashes. It matches the gold result: with the owner's exit, only being long while gold rose made money.
3. Searching "all stocks" for setups faces the same two walls as gold: costs and luck. The data that includes dead
   companies (this library) is the only fair test of stock ideas; free price downloads contain only survivors.

## Not covered yet
Trend following across 40+ futures markets (stock indices, bonds, currencies, commodities). It needs daily futures
history, possibly from the owner's TradingView app, with their OK.
