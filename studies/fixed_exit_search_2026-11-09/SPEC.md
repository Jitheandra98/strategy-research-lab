# FIXED-EXIT ENTRY SEARCH: pre-registered 2026-11-09, written BEFORE the test

## The owner's rule (their words)
"Every time the stop is $250. If you take profits more than $100, you close the trade. That is the rule... take thousand
different strategies... until you find one setup that makes money."

## Exit: the same for every strategy
- 1 MGC, entry at a 5m open.
- Long: stop at entry − 25 pt ($250), target at entry + 10 pt ($100); the target needs a 0.1 pt trade-through. Short is
  the mirror image.
- No time limit except a cap of 20 trading days (5,520 5m bars), with exit at the close if neither level is hit.
- The stop counts first if one 5m bar touches both. A bar that opens through the stop fills at that open.
- Cost 0.3 pt round trip plus 0.2 pt of slippage on stops. A win therefore nets $97 and a loss costs at least $255.
  **Break-even win rate = 72.4 %.** On a market with no drift, a random entry hits +10 before −25 about 71.4 % of the time.
- One position at a time per strategy.

## The library: 1,764 strategies, every one a single direction
Indicator families, each on 15m, 1h, 4h and daily bars (118 rules per timeframe, 472 in all). The signal comes at the
bar's close and the entry is the next 5m open.
- EMA crosses 5/20, 9/21, 10/50, 20/50, 20/100, 50/200 (buy up-cross, sell down-cross).
- Close crossing EMA 10/20/50/100/200.
- Donchian 10/20/55/100: break of the high or low, followed or faded.
- RSI 2 and 14 crossing 10/20/30 and 70/80/90: faded (mean reversion) or followed (momentum).
- Bollinger 20 at 2.0 and 2.5 SD: close outside the band, faded or followed.
- MACD 12/26/9: signal-line cross and zero cross.
- 3/4/5 consecutive up or down closes, faded or followed.
- Big bar (range ≥ 1.5/2/2.5/3 × ATR, body ≥ 50 %), followed or faded.
- Inside-bar breakout, followed or faded.
- Engulfing candle, followed or faded.
- Stochastic 14/3 cross below 20 or above 80, faded or followed.
- ROC 10/20 turning positive or negative.

Clock and level families (5m data, 116 rules):
- Entry at the open of each hour from 18:00 to 16:00 ET, plus 08:30 and 09:30, long or short (50 rules).
- Session open by weekday, long or short (10).
- Opening-range breakouts: Asia 18:00, London 03:00 and NY 09:30, with 15/30/60-minute ranges, followed or faded (36).
- First close beyond the previous day's or previous week's high or low, followed or faded (8).
- Close through a $50 or $100 round number, followed or faded (8).
- Weekly open gap of at least 0.2 × daily ATR, followed or faded (4).

Every one of the 588 base rules is run three ways: as it is, only WITH the daily trend (daily close vs EMA 200), and only
AGAINST it. 588 × 3 = 1,764.

## Luck control and pass bar (fixed now)
- Development 2012–2019. Validation 2020 → Sep 2026, looked at once.
- Each strategy is compared with 60 random-timing copies of itself in the same period, with the same direction and the
  same number of signals on random 5m bars. z = how far it beats random timing, in standard deviations of the copies.
- Gold rose from about $1,050 (2015) to over $4,000 (2026), so random LONG entries are expected to look good after
  2019. That gain comes from the market's drift, not from skill. This is why a strategy must beat random timing in its own
  direction, not merely make money.
- PASSES development: n ≥ 100, PF ≥ 1.15, t ≥ 2 against zero, and z ≥ the luck-adjusted bar for 1,764 tries
  (one-sided 5 % ÷ 1,764 ≈ z 4.0).
- HOLDS UP in validation: PF ≥ 1.15, t ≥ 2 and z ≥ 2.
- Also reported: the "naive winners" (n ≥ 100, PF ≥ 1.15, t ≥ 2 in development, with no luck check) and how they do
  in 2020–26.
- A strategy that holds up is not traded. It goes to the paper-account gate. A $250 stop at 1 % risk needs a $25,000 account.

## Expected, stated before testing
Prior studies found no timing edge in gold (ledger: ≥ 1,022 variants), so few or no rules should beat random timing.
Long rules will look good in 2020–26 because of the drift, and short rules bad.
