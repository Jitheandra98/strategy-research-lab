# SPIKE FOLLOW v1 — pre-registered 2026-11-08, written BEFORE the test (idea #2 of the new partnership)

## Why this idea
1. The US-morning spike FADE (replay_watch_2026-11-07/longtest/two_ideas_14y.py) lost in every period: PF 0.53 / 0.59 / 0.64,
   worse than random. Fading big morning spikes keeps losing, which suggests the spikes keep going.
2. NOISE BREAKOUT (noise_breakout_2026-11-08) showed gold's morning direction carries into the 13:30 close (t 4.8 over 14 years).
Hypothesis: a big 08:00–10:30 ET spike is real news or real flow, so ride it to the COMEX settlement.
**Caution, stated in advance:** the trigger is the same as a test already run on the same 14 years. So a pass here only earns
forward PAPER trading, never money.

## Trigger (same as the fade)
Gold spot 5m 2012-01 → 2026-09 resampled to 30m bars, New York clock. Spike = a 30m bar starting 08:00, 08:30, 09:00, 09:30 or
10:00 ET whose range (H−L) ≥ 2.5 × ATR(14, RMA) of the previous bar. Direction = the spike bar's colour (close > open → up).

## MAIN — ride it to 13:30
- One trade per day: the day's first spike only.
- Enter at the NEXT 30m bar's open, in the spike's direction.
- Stop: beyond the spike's starting extreme (up spike: spike low − 0.1 × ATR; down spike: spike high + 0.1 × ATR),
  meaning the push has fully failed. If a bar opens through the stop, exit at that open. Stop counts first inside a bar.
- Otherwise exit at 13:30 ET (close of the 13:00 bar).
- 1 MGC ($10/pt), cost 0.3 pt per round trip, also reported at 0.5 pt.
- Control: the same direction, stop distance, entry clock and 13:30 exit on 20 random other days → "edge vs random".

## ALT — the exact mirror of the losing fade (every spike bar, as the fade test took them)
Enter at the spike close with the spike. Target = the fade's stop level (spike extreme + 0.1 × ATR).
Stop = the fade's target level (2 × that distance against us). Exit after 4h. Our stop counts first inside a bar.
This tests directly whether the fade's losses can be captured.

## Pass bar (same as NOISE BREAKOUT, plus one rule) — applies to MAIN
a. PF ≥ 1.15 after 0.3 pt in each period: 2012–2019, 2020–2023, 2024–2026.
b. Long side AND short side both profitable over the full sample.
c. Still profitable at 0.5 pt cost.
d. At least 9 of the 15 years profitable.
e. Beats the random same-clock control in every period.
Pass → a paper-trading bot (TradingView alerts) for 2–3 months, no money. Fail → no bot, and we write down what it taught.
