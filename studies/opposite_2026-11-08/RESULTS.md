# "Do the opposite": results (2026-11-08)
Owner's idea: everything we test loses, so trade the opposite. opposite.py takes the exact trades of all 78 rules tested on
2026-11-07 and 2026-11-08 (604,563 trades) and flips each one: same entry, same exit, other side. Both sides pay 0.3 pt per
round trip. The flip is generous to the opposite (a bar that hit both stop and target was charged as a loss to the original,
and the flip gets it as a win), so a strict re-simulation could only make it worse. Scoreboard: opposite_scoreboard.csv.

## Verdict: the opposite loses too. 0 of 78 pass the bar.
| all 78 rules, 1 MGC per trade | dollars |
|---|---|
| before costs (original direction) | −$109,445 (≈ −$0.18 per trade, i.e. flat) |
| costs, paid by BOTH sides ($3 per trade) | $1,813,689 |
| original after costs | **−$1,923,134** |
| opposite after costs | **−$1,704,244** |

- 8 of 78 opposites made a little money at 0.3 pt (3 originals did), and none passed. The largest was the opposite of the
  1.5R trend FVG pullback: +$3,932 over 6,955 trades (≈ $0.57 per trade), PF 0.86 / 0.90 / 1.30 by period, and −$9,978 at
  0.5 pt. Two others were +$317 (106 trades) and +$358 (247 trades). That is the size of luck.
- Every opposite that looked good did so only in 2024–26, and none held in 2012–19.

## Why
The losses never came from choosing the wrong side. Before costs these rules are coin flips (gross ≈ 0). Flipping a coin flip
gives another coin flip, and the fee is paid on both sides. Costs ($1.81M) were 16× the whole directional result ($0.11M).
Picture a $19 bet on a coin (the median stop) with a $3 fee per flip. Heads loses, and switching to tails loses about the same,
because the fee is what drains the account.

## What it teaches
On gold's 5m chart at 1 MGC, direction barely matters. **Cost per trade relative to the move per trade** is what decides the
result. Only a rule that trades rarely and catches moves many times larger than $3 has a chance. Every rule tested so far
trades often with small stops.
