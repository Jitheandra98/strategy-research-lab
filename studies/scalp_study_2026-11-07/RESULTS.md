# Scalp study — "is there a place where a $2–3 move is near-certain?" (2026-11-07)
Data: HistData XAUUSD 1m, 2025-01 → 2026-09-24 (613k bars). Entry at bar close, TP/SL in points ($ per oz = MGC points),
stop counted first when both in one minute, 4 h limit, cost 0.3 pt round trip. scan.py / wide.py / levels.py → *.txt.

1. Any minute, any direction: TP 1 / SL 50 wins 94–96 %, TP 2 / SL 20 wins ~90 % — and every combination loses (PF 0.54–0.93)
   once untouched trades are closed at 4 h instead of ignored. High hit rate is bought with rare huge losses (worst −50 pt).
   TP 2 / SL 2 = 48–50 % hits (coin flip) vs 57.5 % needed after cost.
2. 12 "special places" (PDH/PDL touch, round 00/50, big 1m bars, 60-min sweeps, 03:00 / 08:30 / 09:30 EST bars), fade & follow,
   7 TP/SL pairs = 168 setups. Best on 2025 was still below break-even (−0.7 pt of win-rate); 0 of 168 positive in both years.
Conclusion: no 100 % (or even break-even) scalp place found; the cost (~0.3 pt) alone is 15 % of a $2 target.
