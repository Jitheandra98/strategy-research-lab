# TREND FOLLOWING ACROSS ALL FUTURES: results (2026-11-09)
Rules: SPEC_trend.md (written before the data was pulled). Code: trend.py → trend.txt and trend_stats.csv.
Data: 38 continuous futures, daily, from the owner's TradingView. Files are in tv/data, pulled with tv/pull_all.mjs.
The chart was restored afterwards to COMEX_MINI:MGC1!, 5 m, back-adjustment ON, and this was checked. Returns leave out
the price jump at each contract roll (change in the back-adjusted price ÷ unadjusted price).

**Skipped: 7 ICE markets** (DX, Brent, coffee, sugar, cocoa, cotton, orange juice). TradingView served them under its
delayed-data name (ICEUS_DLY:, ICEEUR_DLY:), and the exact-name safety check in the pull skipped them. Under the spec
they are dropped. They could be added later as a robustness check, without changing this verdict.

## Verdict: DOES NOT PASS, yet it is the only strategy tonight that still made money after it was published
TSMOM-12: at each month-end, every market goes long after a 12-month rise and short after a 12-month fall, with each
position sized to its own volatility. All figures are after a 0.05 % cost.

| Window | Years | Return per year | Volatility | Sharpe | t | Max drawdown | Beats random-sign portfolios |
|---|---|---|---|---|---|---|---|
| Full history, 1981–2026 | 45.8 | +11.5 % | 13.7 % | 0.83 | 5.64 | 24.1 % | 100 % |
| Published sample, up to 2009 | 28.9 | +15.7 % | 13.9 % | 1.12 | 6.04 | 23.5 % | 100 % |
| 2010–2012 | 3.0 | +1.2 % | 16.0 % | 0.07 | 0.13 | 21.1 % | 58.6 % |
| **After publication, 2013–2026** | 13.8 | **+4.9 %** | 12.5 % | **0.39** | **1.46** | 24.1 % | **94.6 %** |

- The bar was t ≥ 2 and beating 95 % of random-sign portfolios. TSMOM-12 fails both, the second only narrowly. At the
  stress cost of 0.20 %, its Sharpe after publication is 0.20.
- The 1/3/12-month blend after publication: −0.5 % a year, Sharpe −0.05. It fails.
- Holding every market long with the same sizing had a Sharpe of 0.17 after publication, so trend did better than
  simply holding everything.
- Years since publication: 2013 +15 %, 2014 +13 %, 2015 +21 %, 2016 −17 %, 2017 +7 %, 2018 −7 %, 2019 −2 %,
  2020 +10 %, 2021 0 %, 2022 +22 %, 2023 −5 %, 2024 +1 %, 2025 +3 %, 2026 +6 % (Jan–Oct).
- Gross Sharpe by sector after publication:
  | Sector | Sharpe |
  |---|---|
  | Equities | 0.46 |
  | Energy | 0.36 |
  | Bonds | 0.33 |
  | Metals | 0.14 |
  | Grains | 0.13 |
  | Livestock | 0.12 |
  | Currencies | −0.05 |

## What it taught
1. Over the long run, trend following across many markets is real. Over 46 years its Sharpe was 0.83 and it beat every
   random-sign portfolio. It is the strongest result of the whole project.
2. Like the published stock strategies, it weakened once it was published. Its Sharpe was 1.12 before publication and
   0.39 after. A t of 1.46 is not enough to be sure it still works.
3. It earns its money by being spread across 38 markets and holding for months, and it still had losing years (−17 % in
   2016). That is the opposite of a 5-minute setup.
4. One position in each of about 38 markets needs a large account. This is research, not a plan.
