# TREND FOLLOWING ACROSS ALL FUTURES MARKETS: pre-registered 2026-11-09, before pulling the data

## Why
This is the one cross-market strategy with a long published record: Moskowitz, Ooi & Pedersen, "Time series momentum",
Journal of Financial Economics (2012), sample 1985–2009. The years from 2013 on are its honest holdout, because its
authors never saw them.

## Data
- Source: daily bars from the owner's TradingView app (owner's OK on 2026-11-09), continuous front contracts, settlement
  as close.
- Each market is pulled twice, back-adjusted (the owner's chart setting) and unadjusted. The chart's original setting
  (back-adjustment ON, COMEX_MINI:MGC1!, 5 m) is restored afterwards.
- Daily return = change in the back-adjusted price ÷ previous unadjusted price. This excludes the price jump at each
  contract roll.

The 45 markets:
- Equity indices: ES, NQ, YM, RTY, FDAX, FESX, NKD
- Bonds: ZT, ZF, ZN, ZB, FGBL
- Currencies: 6E, 6J, 6B, 6A, 6C, 6S, 6N, 6M, DX
- Energy: CL, NG, HO, RB, Brent
- Metals: GC, SI, HG, PL, PA
- Grains: ZC, ZW, ZS, ZM, ZL, KE
- Softs: KC, SB, CC, CT, OJ
- Livestock: LE, HE, GF

Markets that fail to load are dropped and listed.

## The two strategies (textbook settings, NOT tuned)
- **TSMOM-12:** at each month-end, every market goes long if its past 12-month return is positive and short if it is
  negative.
- **Trend blend:** the position is the average of the signs of the past 1-, 3- and 12-month returns.

Both strategies share these rules:
- Each position is sized to 40 % annual volatility using that market's own recent volatility (60-day EWMA).
- The portfolio return is the average across the markets that have data on that day.
- Signals use data up to the month-end close and earn returns from the next day on, so there is no look-ahead.
- Cost: 0.05 % of notional per unit of position change, with a stress test at 0.20 %. The return is an excess return:
  T-bill interest on collateral is not included.

## Controls
- **Random signs:** 1,000 portfolios with the same sizing and rebalancing but a coin-flip long or short in each market
  every month.
- **Always long:** every market held long with the same sizing. This separates "markets went up" from timing.

## Windows
- Full history.
- Up to 2009, the published sample.
- 2010–2012, published but before the paper's journal year.
- **2013 → 2026, after publication: the holdout.**
- Every calendar year.

## Verdict rule (fixed now)
TREND FOLLOWING STILL WORKS if, in 2013 → 2026 after the 0.05 % cost, both of these hold:
1. The Sharpe ratio is above 0 with t ≥ 2.
2. It beats at least 95 % of the random-sign portfolios.

## Reality note (stated before)
Trading this needs one position in every market. Even with micro contracts where they exist, that takes a large account
(tens of thousands of dollars or more). This is research, not a trading plan.
