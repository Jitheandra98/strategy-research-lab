# Owner's "five blue lines" plan, pre-registered 2026-11-08 (written BEFORE testing)

## What the five lines are
Desk Context (DESK_CONTEXT.pine, section 3) draws a session VWAP anchored at 18:00 New York (thick center line, #00BCD4) with
±1 SD and ±2 SD bands (lighter lines). SD = the weighted standard deviation of hlc3 around the VWAP since the anchor.
The owner saw them on his chart but didn't know what they were.

## His idea, restated
Wait one hour after Tokyo opens. If price spent that hour between the two UPPER lines → buy day (long trend). Between the two
LOWER lines → sell day. When New York opens, price pulls back to the center line (or one line beyond it), takes the
liquidity, and then moves with the trend again → enter at that pullback in the day's direction. He asked me to set TP and SL.

## Rules (fixed now)
- Data: gold spot 5m, Jan 2012 → Sep 2026. **No volume exists in our data**, so the lines are equal-weighted, exactly what
  Desk Context draws on a feed without volume. On a volume feed (MGC) the lines sit somewhat differently, especially in NY
  hours. Session = CME day from 18:00 ET (Desk Context's anchor).
- Lines used to decide on a bar = their values after the previous bar closed (no look-ahead).
- Tokyo open = 00:00 UTC (the QF CORE default). Bias is decided at 01:00 UTC from the 12 five-minute closes of 00:00–00:55 UTC.
  MAIN: BUY day if every close is above +1 SD, SELL day if every close is below −1 SD.
  STRICT (check): every close between +1 and +2 SD (buy) or between −1 and −2 SD (sell).
- NY window = 08:00–12:00 ET. Only the first qualifying touch is traded, one trade per day.
- Entry E1 (center line): buy day → first bar that opens above the VWAP and trades down to it → buy limit at the VWAP.
  Stop = −1 SD line − 0.1. Sell day = mirror.
- Entry E2 (the line beyond): buy day → first bar that opens above −1 SD and trades down to it → buy at −1 SD.
  Stop = −2 SD − 0.1. Mirror for sell days.
- Targets (prices frozen at entry): T1 = +1 SD line, T2 = +2 SD line (−1 / −2 SD on sell days).
- Exit = stop, target, or the session's last bar (16:55 ET). Inside the entry bar only the stop can count (price had to pass
  the entry to reach the stop). After that the stop counts first inside a bar, and a gap through the stop fills at the open.
  Skip trades with risk < 0.2 pt.
- 1 MGC ($10/pt), cost 0.3 pt per round trip, also checked at 0.5 pt. Limit fills on touch (generous to the plan).
- Variants: E1T1 = MAIN, plus E1T2, E2T1, E2T2. The STRICT bias is shown for E1T1.

## Pass bar (same as every test today)
a) PF ≥ 1.15 after 0.3 pt in each period 2012–19, 2020–23, 2024–26; b) long AND short profitable; c) profitable at 0.5 pt;
d) ≥ 9 of 15 years profitable; e) ≥ 30 trades per period.
Diagnostics: does the Tokyo-hour bias predict the day (01:00 UTC → 16:55 ET move in the bias direction)? How often does NY
touch the line? Before-fee result per trade in R.
