# Tokyo bias + QF CORE order blocks / FVGs — results (2026-11-08)
Rules: SPEC.md (written before testing). Code: qf_zones.py (QF CORE v1.0 OB/FVG port → zones.npz), tokyo_plan.py →
results.txt; trades_main/buys/control.csv; chart_data.json. Gold spot 5m Jan 2012 → Sep 2026, 1 MGC, 0.3 pt per round trip.
Port check: 99% of bull OBs sit below the breaking close (bear 99% above). FVG geometry is exact. 14 years produced 38,305
internal OBs, 7,235 swing OBs and 113,307 FVGs.

## Verdict: FAILS in every variant. The Tokyo bias adds nothing.
| version (Tokyo session 01:00–09:00 UTC) | trades | win % | PF | net | avg / trade | years + |
|---|---|---|---|---|---|---|
| MAIN: bias + OB/FVG, stop just beyond, 2R | 2,201 (147/yr) | 31.7 | 0.62 | −$8,142 | −$3.70 | 0 / 15 |
| … buy days, buys only | 1,209 (81/yr) | 30.9 | 0.65 | −$4,251 | −$3.52 | 2 / 15 |
| … sell days, sells only | 992 | 32.7 | 0.60 | −$3,891 | −$3.92 | 1 / 15 |
| order blocks only | 609 | 34.8 | 0.80 | −$1,357 | −$2.23 | 3 / 15 |
| FVGs only | 1,897 | 31.0 | 0.54 | −$8,258 | −$4.35 | 0 / 15 |
| target 1R / 3R | 2,427 / 2,039 | 40.6 / 25.8 | 0.48 / 0.70 | −$9,926 / −$6,407 | | 0 / 1 |
| wide stop (zone − 1 ATR), 2R | 1,493 | 33.9 | 0.83 | −$3,909 | −$2.62 | 2 / 15 |
| … wide stop, buy days only (closest to even) | 826 | 35.8 | 0.95 | −$690 | −$0.84 | 4 / 15 |
| LOOSE bias (closes beyond the center line) | 8,414 | 32.0 | 0.66 | −$26,472 | −$3.15 | 0 / 15 |
| **CONTROL: same trades, no Tokyo bias** | 31,427 (2,095/yr) | 32.3 | **0.66** | −$98,222 | −$3.13 | 0 / 15 |

## Why
- **The bias doesn't help.** With the Tokyo bias the plan averages −$3.70 per trade; with no bias at all, −$3.13. Picking
  only the bias direction did not make OB/FVG touches work any better.
- **The zones are tiny, so fees take a huge bite.** Median zone height is 0.96 pt (internal OB), 1.34 (swing OB) and
  0.59 (FVG). The median stop is $7, so the $3 fee is about 43% of the risk on every trade.
- **Price goes straight through often.** In MAIN, 66% of trades hit the stop and 30% the 2R target. 22% were stopped inside
  the entry bar itself (price touched the zone and kept going in the same 5 minutes).
- Even before fees it is slightly negative (−0.057R per trade). Wider stops cut the fee share (PF 0.83; buy days 0.95)
  and still lose.
