# NOISE BREAKOUT v1 — results (2026-11-08)
Rules: SPEC.md (written before the test). Code: noise_breakout.py → results.txt. Trades: trades_main.csv, trades_alt.csv.
Gold spot 5m, Jan 2012 → Sep 2026, 1 MGC ($10/pt), cost 0.3 pt per round trip.

## Verdict: FAILS the pre-registered bar → no bot
| | trades | win % | PF | net (1 MGC) | max DD |
|---|---|---|---|---|---|
| MAIN 08:30–13:30 ET, all | 2,739 | 33.8 | 0.97 | −$2,294 | $5,246 |
| 2012–2019 | 1,473 | 33.5 | 0.97 | −$587 | |
| 2020–2023 | 680 | 33.4 | 1.00 | −$74 | |
| 2024–2026 | 586 | 34.8 | 0.95 | −$1,633 | |
| long only / short only | 1,422 / 1,317 | | 0.96 / 0.98 | −$1,428 / −$866 | |
| at 0.5 pt cost | | | 0.89 | −$7,772 | |
| ALT 09:30–16:00 ET (paper's clock) | 3,053 | 32.9 | 0.97 | −$2,007 | $6,070 |

Pass bar: a) PF ≥ 1.15 every period ✗  b) long and short both positive ✗  c) positive at 0.5 pt ✗  d) ≥ 9/15 years positive ✗ (5).
Short windows lie: 2025 alone +$2,508 (PF 1.29); 2026 Jan–Sep alone −$4,747.

## What it taught
1. **Gold does have real intraday momentum.** The move from the previous 13:30 close to 09:00 predicts the last half hour
   (13:00→13:30): corr +0.079, t = +4.77 over 3,600 days (2012–19 t 4.73; 2020–23 t 0.64; 2024–26 t 2.35).
   The rest of the session (09:00→13:30) follows the early direction by +2.3 bp/day (t 2.4).
   This is the first directional effect in the whole project that is not just a clock effect.
2. **It is smaller than retail costs.** The breakout trades make +0.22 pt per trade before costs, and costs are 0.3 pt.
   The direction is right, but the edge is too small to keep after paying for each trade.
3. Together with the 17:00–18:00 reopen gap (edge_search_2026-11-07), gold's real inefficiencies look like this:
   small and real, and eaten by costs at 1-MGC size.

## Still open (next idea, not yet tested)
News-spike FOLLOW: the US-morning spike FADE (replay_watch_2026-11-07/longtest) lost in every period (PF 0.47–0.64,
worse than random). That plus point 1 suggests going WITH big 08:00–10:00 spikes. Caution: it mirrors a trade already
run on the same 14 years, so a good backtest would be weak evidence. It would need forward paper trading before any belief.
