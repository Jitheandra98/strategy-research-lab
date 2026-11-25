# Owner's premium/discount rules — QF15 (v15) pdPct on 15m XAUUSD, 2016-01 → 2026-09 (score_touch.py / score_touch.log)
Green touch (pd crosses ≤5 %) = buy, red touch (≥95 %) = sell, stop 1.5 ATR14, fill at bar close, 5m exits, stop-first, cost 0.35.
All touches PF 3R 0.69 / 0.90 / 0.75 (2016-20 / 21-24 / 25-26) vs RANDOM 0.80 / 0.87 / 0.96 → no edge, red-touch sells worst.
1st vs 2nd vs 3rd+ touch: all ≈ random or worse. Trading WITH the trend on 3rd+ touches: 0.89 / 0.79 / 1.25 — inconsistent.
Session-open "fast run from the other extreme" (within 2h): only ~13 cases in 10 years with this definition → untestable as defined.
Caveat: v15 code, not 15.2; ~80 % of touches are re-touches while price grinds along the extreme.
