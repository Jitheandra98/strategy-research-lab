# NOISE BREAKOUT v1 — gold intraday momentum bot (pre-registered 2026-11-08, written BEFORE any test)

Owner's request (2026-11-08): "leave all my ideas, create your own idea with all the trading knowledge you know, a day-trading bot."
This is Claude's idea. Not secret: adapted from published intraday-momentum research
(Zarattini, Aziz & Barbon 2024, "Beat the Market — an effective intraday momentum strategy for SPY", noise-area breakout;
Gao, Han, Li & Zhou 2018, "Market intraday momentum", JFE). Never tested on gold in this project before.

## The thinking
Most of the day gold moves inside its normal noise for that time of day. When price closes clearly OUTSIDE the band it
usually reaches by that hour, somebody large is pushing (data, hedging, funds rebalancing) and that push tends to continue
into the close. So: sit out the noise, ride only real breakouts, leave when the push fades, always flat before the close.

## Rules (fixed in advance — no tuning on gold)
Data: gold spot 5m, Jan 2012 → Sep 2026, New York clock (DST aware). Bars stamped at their open.

MAIN = COMEX session 08:30–13:30 ET (13:30 = COMEX settlement). ALT = equity hours 09:30–16:00 ET (the paper's own clock).
1. Open = first bar's open. PrevClose = previous session's final close (13:30 or 16:00).
2. Noise σ(τ) at each 5m time-of-day τ = average over the previous 14 complete sessions of |Close(τ) / Open − 1|.
3. Upper band UB(τ) = max(Open, PrevClose) × (1 + σ(τ));  Lower band LB(τ) = min(Open, PrevClose) × (1 − σ(τ)).
4. Fair price = TWAP: average typical price (H+L+C)/3 of today's session bars so far (spot gold has no real volume for VWAP).
5. Decisions only every 30 minutes (first one 30 min after the open), on the closed 5m bar:
   - flat:  close > UB → BUY;  close < LB → SELL.
   - long:  close < max(UB, TWAP) → exit (and SELL if close < LB).
   - short: close > min(LB, TWAP) → exit (and BUY if close > UB).
6. Fill at the NEXT bar's open (no look-ahead). Anything still open is closed at the session close. Max 1 position.
7. Size: 1 MGC ($10 per point). Cost 0.3 pt per round trip ($3) — same as every earlier study; also reported at 0.5 pt.

## Pass bar (decided now). It only becomes a bot for PAPER trading if ALL hold for MAIN:
a. Profit factor ≥ 1.15 after 0.3 pt in each period: 2012–2019, 2020–2023, 2024–2026.
b. Long side AND short side both profitable over the full sample (not just riding gold's bull run).
c. Still profitable at 0.5 pt cost over the full sample.
d. At least 9 of the 15 years profitable.
Fails → no bot (it would only automate a loss); we write down what it taught and move to the next idea.

## Also measured (to see if the underlying effect exists at all in gold)
Does the early move (prev close → 09:00) predict the last half hour (13:00 → 13:30)? Correlation + t-stat by period.
