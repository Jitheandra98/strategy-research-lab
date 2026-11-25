# SPIKE FOLLOW v1 — results (2026-11-08)
Rules: SPEC.md (written before the test). Code: spike_follow.py → results.txt. Trades: trades_main.csv.
Gold spot 5m Jan 2012 → Sep 2026 → 30m bars, 1 MGC ($10/pt), cost 0.3 pt per round trip.

## Verdict: FAILS the pre-registered bar → no bot. Closest of the two ideas tested today, but thin.
| MAIN: first 08:00–10:30 spike, ride it to 13:30 | trades | win % | PF | net (1 MGC) | edge vs random |
|---|---|---|---|---|---|
| all 2012–2026 | 1,941 (129/yr) | 42.8 | 1.06 | +$3,963 | +0.054R |
| 2012–2019 | 1,118 | 42.3 | 1.09 | +$2,443 | +0.050R |
| 2020–2023 | 519 | 43.9 | 1.02 | +$389 | +0.062R |
| 2024–2026 | 304 | 42.8 | 1.05 | +$1,131 | +0.054R |
| long / short | 925 / 1,016 | | 1.10 / 1.03 | +$2,858 / +$1,105 | +0.100R / +0.012R |
| at 0.5 pt cost | | | 1.00 | +$81 | |
Median stop $64; max drawdown $2,969. Average ≈ +$2 per trade, ≈ $280 per year on 1 MGC. 2025 +$2,033; 2026 Jan–Sep −$1,023.

Pass bar: a) PF ≥ 1.15 every period ✗ (1.09 / 1.02 / 1.05)  b) long and short positive ✓  c) positive at 0.5 pt ✓ (barely, +$81)
d) ≥ 9 of 15 years ✗ (8)  e) beats random every period ✓.

## ALT — exact mirror of the losing fade: PF 0.70, −$17,101, 14 of 15 years negative
The fade lost and its mirror lost even more. The fade lost mostly because price pokes slightly past the spike extreme
(tight stop) and because costs are paid on every trade, not because spikes run far. **The opposite of a losing trade is not a
winning trade; costs are paid in both directions.**

## What it taught
1. Riding big morning spikes to the 13:30 settlement adds a small, consistent push over random (+0.05R in every period,
   both sides). This matches NOISE BREAKOUT's finding that gold's morning direction carries into the close.
2. Size of a real edge in gold at 1 MGC: about $2 per trade. It would vanish if costs were 0.5 pt instead of 0.3.
3. Diagnostic only, NOT a rule: 08:00-bar spikes PF 1.25 (+$4,268, 532 tr); 10:00-bar spikes PF 0.75. Choosing "08:00 only"
   after seeing this would be fitting to the past. It can only be tested on data it has never seen, i.e. forward, on paper.

## Still open
- A forward paper scorecard (no money) would be the only clean test, but it is too slow. Per-trade std is 1.28R, so an edge of
  +0.054R needs about 2,260 trades for t = 2, which is about 17 years at 129 trades a year. The 08:00 subset (+0.12R, 38/yr)
  would also take about 17 years. Paper trading cannot confirm an edge this thin in any useful time.
- Measure the owner's real round-trip cost. At this edge size, 0.1 pt of cost decides the result.
