# Owner's support/resistance plan, pre-registered 2026-11-08 (written BEFORE testing)

## The plan in his words, restated
Every day there are support levels below price and resistance levels above. Price comes up to a resistance → SELL, stop just
above it, take profit at the next support. Price comes down to a support → BUY, stop just below it, take profit at the next
resistance. A broken resistance becomes support → buy when price comes back to it. A broken support becomes resistance → sell
the retest. (His "it will sell from there" is read as "price bounces from there, so we buy"; to be confirmed with him.)

Because a level's role is simply where it sits relative to price, the whole plan is one rule: **when price comes down to a level,
buy it; when price comes up to a level, sell it; stop just beyond the level; target the next level.** A broken level flips role
automatically. Each trade is tagged RANGE (level traded in its role at the session open) or FLIP (level traded after it broke).

## Levels (three common definitions, fixed at the 17:00 CT session start, no intraday redraw)
- A. DAILY H/L: the highs and lows of the previous 5 CME sessions (10 levels).
- B. 1H SWINGS: 3-bar fractal swing highs/lows on 1-hour bars from the previous 5 sessions, confirmed before the session starts.
- C. FLOOR PIVOTS: P, R1–R3, S1–S3 from the previous session's high, low and close.
Levels closer together than the stop buffer are merged into one zone (their average).

## Mechanics
- Data: gold spot 5m, Jan 2012 → Sep 2026, CME sessions 17:00 → 16:00 CT. 1 MGC ($10/pt), cost 0.3 pt per round trip
  (also checked at 0.5).
- Entry = limit order AT the level, filled when a 5m bar that opened on the near side reaches it. If one bar touches a level
  above AND below its open, the order is unknown, so skip it.
- Stop = level ± buffer. MAIN buffer = 0.5 × ATR(14) of 1-hour bars at the session start ("just beyond the level"). Checked
  at 0.25× and 1.0×.
- Target = the next level in the trade's direction. No next level → no trade.
- In the entry bar, if the stop price is also reached, it counts as stopped (we can't know the order). After that the stop
  counts first inside a bar, and a gap through the stop fills at the open. Flat at the session's last bar. One trade at a time.

## Pass bar (same as every test today)
a) PF ≥ 1.15 after 0.3 pt in each period 2012–19, 2020–23, 2024–26; b) long AND short profitable; c) profitable at 0.5 pt;
d) ≥ 9 of 15 years profitable; e) ≥ 30 trades per period. Also reported: before-fee result per trade in R (≈ 0 means a coin
flip), and RANGE vs FLIP trades separately. 3 level types × 3 buffers = 9 variants; MAIN buffer decides the verdict.
