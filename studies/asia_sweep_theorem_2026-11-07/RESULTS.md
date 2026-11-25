# Owner's theorem with Desk Context (2026-11-07) — theorem.py / bias_filter.py → theorem.txt / bias_filter.txt
Theorem: Asia sets its low (18:00–00:00 NY) → NY (08:00–11:00) sweeps it → price taps a fresh bullish OB/FVG just below → the move
goes to the other side (mirror for highs). Gold spot 5m 2012-01 → 2026-09, New York clock with DST, Desk Context sessions.

Rules (V1): Asia low intact at 08:00; fresh 5m OB/FVG (last 3 days, never touched) with its top within 1.5×ATR(1h) under the Asia low;
NY sweeps the Asia low and touches the zone → buy at zone top, stop under zone (0.1×ATR5 buffer), target Asia high (also 2R/3R),
exit 16:55. Cost 0.3 pt. Control: same stop/target distance at the same NY clock time on 20 random other days.

| Rule | 2012–2019 | 2020–2026 |
|---|---|---|
| V1 theorem → Asia high | 221 tr, win 14 %, PF 0.62, −$3.41/tr, random −0.33R vs −0.48R | 178 tr, win 12 %, PF 0.82, −$1.36/tr |
| V1 theorem → 2R | PF 0.45 | PF 0.52 |
| V2a Desk Context sweep alert (close back inside) → Asia high | PF 0.82 | PF 0.90 |
| V2b sweep then later reclaim → Asia high | PF 0.75 | PF 0.84 |
| V3 previous-5-day NY level sweep → 2R | PF 0.84 | PF 0.63 |
With Desk Context's 1H bias (buy only BULL / sell only BEAR): no improvement (V1 PF 0.53 / 0.76; V2a 0.90 / 1.06 ≈ $0).
Only green cell: V1 buys 2020–26 (PF 1.27, 96 trades) = gold's bull run; same buys 2012–19 PF 0.58, sells lost. Not an edge.
Every variant ≈ the random same-bracket control → the sweep/zone timing adds nothing.
