# "Five blue lines" plan — results (2026-11-08)
The five lines = Desk Context's session VWAP (anchored 18:00 NY, thick line) with ±1 SD and ±2 SD bands.
Rules: SPEC.md (written before testing). Code: vwap_bands.py → results.txt; trades_E1T1…E2T2.csv; chart_data.json.
Gold spot 5m Jan 2012 → Sep 2026, 1 MGC, 0.3 pt per round trip. No volume in our data → equal-weight lines (Desk Context's
own no-volume fallback). On a volume feed (MGC) the lines sit somewhat differently in NY hours.

## Verdict: FAILS. All four entry/target choices lose, and they lose even before fees.
| entry → target | trades | win % | PF | net | avg / trade | SL / TP (median) | years + |
|---|---|---|---|---|---|---|---|
| E1 center line → +1 line (MAIN) | 234 (16/yr) | 47.9 | 0.66 | −$2,079 | −$8.88 | $31 / $30 | 5 / 15 |
| E1 center line → +2 line | 234 | 35.9 | 0.78 | −$1,489 | −$6.36 | $31 / $59 | 5 / 15 |
| E2 line below → +1 line | 209 | 38.3 | 0.70 | −$1,817 | −$8.69 | $27 / $51 | 5 / 15 |
| E2 line below → +2 line | 209 | 33.0 | 0.69 | −$1,998 | −$9.56 | $27 / $77 | 4 / 15 |
MAIN by period: PF 0.65 (2012–19), 1.28 (2020–23), 0.47 (2024–26). 2025 −$633, 2026 −$905.
STRICT bias (Tokyo hour strictly between the 1 and 2 SD lines): only 9 days in 15 years, 6 trades, all won (+$277). That is
far too few to mean anything.

## The two parts of his idea, tested separately
1. **Tokyo-hour bias → the day's trend.** 375 bias days (25/yr). The day (01:00 UTC → 16:55 ET) went the bias way on 53.3% of
   them, +1.11 pt on average (t 0.92, not reliable). By period: 46.9% (2012–19), 57.4% (2020–23), **63.5% (2024–26)**.
   It has looked better lately, which is the period he has been watching. Over 14 years it is close to a coin flip.
2. **NY pulls back to the center line, then the trend resumes.** NY touched the center line on 62% of bias days. **Those
   pullback days are the weak ones:**
   - NY never came back to the center line: 141 days, day went the bias way 56.7%, avg +5.72 pt.
   - NY came back (the days you'd trade): 234 days, 51.3%, avg −1.67 pt.
   Strong trend days don't return to the VWAP, so the plan sits out its best days and trades the days the trend is failing.
