# 100-setup catalog + 18:00 range breakout — results (2026-11-08)
Rules: SPEC.md (written before testing); code common.py, single.py, catalog.py; outputs single_results.txt,
catalog_results.txt, scoreboard.csv, gross_check.txt, trades/*.csv. Gold spot 5m 2012-01 → 2026-09, 1 MGC, cost 0.3 pt.

## The owner's separate setup: 18:00–18:30 range breakout → FAIL
| version | trades | PF | net | years profitable | vs random |
|---|---|---|---|---|---|
| MAIN Chicago clock | 3,580 (239/yr) | 0.77 | −$9,691 | 1 of 15 (only 2026: +$1,701) | ≈ random (−0.36R vs −0.39R in 2012–19) |
| ALT fixed UTC−6 | 3,606 | 0.88 | −$5,741 | 2 of 15 (2025, 2026) | ≈ random |
Median stop is only $12 (1.2 pt), so the 0.3 pt cost is a quarter of the risk. It lost every year from 2012 to 2025.
It would look good only to someone looking at 2026 alone.

## The catalog: 47 of 100 testable → 0 pass
- No setup was profitable over 14 years. None was profitable in all three periods, none was profitable at 0.5 pt, and none
  reached PF 1.15 in any recent period (best 2024–26 PFs: #47 1.12, #13 1.11, #55 1.07, #04 1.06).
- **Before costs they are coin flips:** the average gross result is −0.003R per trade, and 21 of 47 sit just above
  break-even while 26 sit below (gross_check.txt). That rules out a simulator bias and also rules out a hidden edge.
- **Costs decide everything.** The median stop on these 5m setups is 1.87 pt ($19 on 1 MGC), so the 0.3 pt round trip is
  16% of the risk on every trade. A coin flip minus 16% per trade is a steady loss.
- PFs are higher in 2024–26 only because gold now moves more points per bar (price ~$4,000 vs ~$1,300), so a fixed cost is a
  smaller share. Even so, no setup clears 1.15.

Worst: #60 two-sided range trap PF 0.49, #10 post-settlement reversal 0.50, #26 low-vol box retest 0.53. Closest to
break-even: #04 US ORB 0.92, #46 settlement gap continuation 0.92 (only 40 trades), #42 prior-day low trap 0.90.

## Not tested: 53 setups need data we don't have
2, 6, 25, 31–40, 61–70 need exchange volume (VWAP / RVOL / profile). 71–80 need aggressor-side and order-book data.
81–90 need exact release timestamps. 91–100 need other markets (DXY, ZN, silver, copper, ES, miners).
Of these, **81–90 (news events)** can be tested with free official calendars (BLS, BEA, Fed), and spike_follow_2026-11-08
found a small real morning-news effect. That makes them the only untested group with a reason to expect something.

## Tally of the partnership's tests on 2026-11-08
NOISE BREAKOUT (fail, PF 0.97) · SPIKE FOLLOW (fail, PF 1.06, ~$2/trade) · 18:00 range breakout (fail, PF 0.77) ·
47 catalog setups (0 pass). That makes 50 rules tested today, none tradeable.
