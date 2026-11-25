# QF INSTITUTIONAL PRO (#131) audit and QF PRO v2 MEASURED: results (2026-11-11)

Data: GC futures 5 m with real volume, 2022-11-07 → 2026-11-08 (283,787 bars, research/gold101/data/gc5m.csv),
run in PineTS on the Chicago clock. Costs per MGC: 0.3 pt round trip ($3), plus 0.2 pt slippage on stop exits.

## v1 (#131), unchanged code
| Part | Bars or signals in 4 years |
|---|---|
| Trend BUY / SELL | 0 / 0 (`close > ta.highest(close, 20)` is always false) |
| Range BUY / SELL | 0 / 0 (RSI < 30 and a crossover above 30 on the same bar) |
| Breakout BUY / SELL (base) | 2,075 / 585 |
| FINAL BUY / SELL | 187 / 9 |
| Risk transfer, isImpulse, rangeContraction | 0, 0, 0 |
| "Smart money" small-move test | 100 % of bars (fraction compared with a percent) |
| Magnet ≠ NONE | 99.99 % of bars (flag never resets) |
| MARKET_INTENT | TRANSITION 64.7 %, CORRECTION_BEAR 20.2 %, RANGING 12.7 %, CORRECTION_BULL 2.4 %, IMPULSE 0 % |
| "Bear" bars where +DI > −DI | 99.8 % (DMI tuple unpacked in the wrong order) |
| MARKET_PHASE | MARKUP 84.2 %, DECLINE 15.7 %, ACCUMULATION 0.1 % (start only), DISTRIBUTION 0 %; 18 changes in 4 years |
| "PDH" = high from two sessions ago | 99.6 % of bars |
| Dashboard at the last bar | Win Rate 89.9 % of 1,653; "Recent WR" 14,860 %; "Profit Factor" 16.68 (placeholder 15/8 constants) |

FINAL signals traded at the next bar's open, with v1's own 2 ATR stop and 1 ATR target, a 20-bar time exit and costs:
196 trades, 69.4 % won, −0.017 R per trade (t −0.34), PF 1.07 in $, +$294 at 1 MGC over 4 years.
By year: 2022 +$34, 2023 −$242, 2024 −$179, 2025 +$30, 2026 +$652.
v1's own win rule (a touch of +0.5 ATR within 20 bars) gives the same trades 87.8 % "wins".

## v2 (QUANTUM_FLOW_PRO_v2_MEASURED.pine), default inputs
- TradingView compiler (server-side check): 0 errors, 0 warnings. v1 has 25 warnings.
- Cross-check (crosscheck_v2.py): an independent Python engine matches PineTS on every signal after the gate, every
  entry bar, every exit bar, every trade's R and every dashboard statistic. That covers 25 checks, run on the last
  10,000 bars; the 4-year check is pending.
- structure_check.py: swing breaks match an independent pivot implementation on 100 % of bars. PineTS treats equal
  highs as ">= left, > right".

### Last 10,000 bars (2026-09-17 → 11-08): the dashboard verdict is NO EDGE after costs
- All: 60 trades, 61.7 % won, −0.076 R (t −0.83), PF 0.79, −$427 at 1 MGC. Halves PF 0.93 / 0.69.
- TREND 43 trades at +0.013 R; BREAK 17 at −0.301 R; RANGE 0. Killzone +0.055 R (33); rest of NY −0.100 R (20);
  off-hours −0.630 R (7).
- Random-time twin: 36 trades, +0.227 R (t 2.63). Timing adds −0.30 R; the falling market carried the sells.
- Paper $10,000 → $9,762. 39 of 60 trades were too wide for 1 % risk.
- Calibration: no band beats the baseline. The sell score at 80+ was followed by +0.84 ATR, against the sellers.

### 4 years (2022-11 → 2026-11)
Run in progress; this section is filled in when it finishes.
