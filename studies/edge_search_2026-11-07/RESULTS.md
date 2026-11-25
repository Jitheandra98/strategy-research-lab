# Edge search on my own initiative (2026-11-07) — where real edges usually live
1. **Slow trend-following** (textbook TSMOM-252 / SMA200 / Donchian 55-20 ensemble, 10 % vol target, not tuned) — trend.py:
   gold 2013-26 Sharpe 0.41 (buy-and-hold same risk 0.56), all of it from the long side (shorts −0.6 %/yr);
   6 FX majors 2017-26: Sharpe −0.20. Trade PF on gold 1.3–1.8 but that is gold's bull drift, not timing skill.
2. **Hour-of-day seasonality** (gold spot 5m, train 2013-19 / test 2020-26) — hours.py: one standout, the daily reopen.
   reopen.py: spot 16:55 → reopen gap +1.9 / +2.9 bp (t≈9.4 in both halves, up 62–66 % of days).
3. **Checked on real MGC futures** (MGC1! 1h from his TradingView, Jan 2025 → Nov 2026, 9 roll days removed) — reopen_fut.py:
   gap = 18:00 open vs 16:00-bar close: +1.05 bp = **+0.42 pt per day**, t=4.8, up 59 %, positive in 2025 and 2026.
   As a trade (buy 16:59, sell at reopen): +0.12 pt/trade at 0.3 pt cost (PF 1.28), −0.08 at 0.5 pt (PF 0.86).
   → A real pattern, the strongest of the whole project, but ≈ $4 gross per MGC per day; costs eat it.
Data limits: TradingView gives ~11k bars per pull (5m back to Sep 13 2026; 1h back to Jan 2025).
