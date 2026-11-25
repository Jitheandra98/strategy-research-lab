# Live replay watch with the owner — MGC 30m, Sep 8 → Sep 17 2026 (2026-11-07)
watch.mjs logged every closed bar with Desk Context's table + new Desk Context / QF Core labels (bars.jsonl, watch.log);
next.py fed live commentary. Ideas that came from watching were pre-registered and tested on gold 5m 2012-2026 resampled to 30m
(scripts in research/asia_sweep_theorem_2026-11-07/):

| Idea seen live | 14-year result |
|---|---|
| Fade Desk Context sweeps only in RANGE (ADX < 20) — range_fade.py | PF 0.59-0.66 in RANGE, worse than TREND fades; no edge |
| Trend-exhaustion: strong trend day, next session sweeps PDL/PDH, ADX turns down -> reverse — exhaustion.py | PF 0.95-1.02, +0.02..0.11R vs random: closest to break-even, not profitable |
| ADX >= 40 turns down -> trade the counter-move — adx_peak.py | PF 0.67-0.80, = random |
| In TREND (ADX > 25 rising) sell/buy the first pullback into a fresh FVG — trend_pullback.py | PF 0.30-0.59, worse than random (thin FVG stops) |

Live lessons: ADX/regime describe the state after the move (Sep 10 range broke into a 70-pt drop before TREND printed);
8:30 ET data (Sep 11: 99-pt bar) and Fed 2 pm ET (Sep 16: -140 pts in 1 h = -$1,400 on 1 MGC) make "hold through heat" unbounded;
30m ATR stops (~$120-200 per MGC) are 6-10 % of a $2,000 account.

## Part 2 — replay Sep 30 → Nov 6 (he auto-played to the end of data; reviewed afterwards) — review_sep30_nov6.py
Python copy of Desk Context matches the chart's regime on 99 % of 1,147 logged bars (median |ADX diff| 0.03).
- Price 4216 → 3884 (Oct 30 low) → 4080. Avg day range 78 pts. Big days: Oct 22 −119, Oct 30 −149 (ADX 60), Nov 4 +132.
- Movement windows (avg 30m candle): 7:00–9:30 CT 17 pts; 7–8 pm CT (China open) 14 pts; rest 7–12. Asia is NOT quiet.
- 12 of the 15 biggest candles started while Desk Context said RANGE/TRANSITION (not TREND).
- Dashboard changes → next 4h (Sep 17–Nov 6): Regime→TREND with DI +2.7 pts (n 58, 50 % won); ADX down from >30 fade +0.4;
  ADX up from <22 with DI −1.7; DI cross −2.4; Regime→RANGE fade +0.2. All coin flips.
- Sweeps (Asia/London/PDH/PDL, first touch, complete OHLC): 135 in 37 days. Measured from the LEVEL, closed-back-inside
  looked great (42 reversed vs 14 continued) — geometric artefact; from the sweep-bar CLOSE it is 29 vs 22.
- Sweep-reclaim fade (close back inside → fade at close, stop 1 pt beyond wick, 2R, 4h max): replay 82 trades, 43 % win,
  PF 1.26, +$1,510 on 1 MGC; RANGE PF 0.84, TRANSITION 1.88, TREND 1.68 (n≈21 each).
## 14-year checks — longtest/two_ideas_14y.py (gold 5m 2012 → 2026-09-24 → 30m, cost 0.3, random same-clock control)
| Idea | 2012-19 | 2020-23 | 2024-26 | note |
|---|---|---|---|---|
| Sweep-reclaim fade (the replay winner) | PF 0.66 | 0.68 | 0.79 | 2026 Jan–Sep: 350 trades PF 0.90 ≈ −$4.5k/1 MGC |
| … only in TRANSITION | 0.71 (edge +0.14R) | 0.77 (+0.09R) | 0.88 (+0.04R) | only regime beating random in all periods; still < 1 |
| US-morning spike fade (30m bar 8–10 NY ≥ 2.5×ATR, fade) | 0.53 | 0.59 | 0.64 | 2025 0.47, 2026 0.47 — worse than random |
