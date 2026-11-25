# IDEA LEDGER: every trading idea tested on our gold data (started 2026-11-09)

Why this file exists: the more ideas we test on the same history, the more of them look good by pure luck. If we ran
1,000 rules with no edge at all, about 23 of them would show t ≥ 2, and about one would show t ≥ 3. So every new idea is
added here before it is tested, and the bar it has to clear rises with the total.

Rule for every new idea: SPEC.md written before the test → chronological split (develop on older data, judge newer data
once) → the same rules run on random entries as a luck check → this ledger updated → only then the paper-account gate
(paper_account_2026-11-09/ACCOUNT_SPEC.md §3).

| Date | Idea | Folder | Variants | Result |
|---|---|---|---|---|
| 2026-09-30 | STATION2 zones from the MGC replay video (5m zones, 4H zones with trend) | zone_reactions_full_2026-09-30_run2 | — | 5m zones no edge; 4H zones with 4H trend ≈ +0.2R in dev and holdout: **open candidate**, thin, never confirmed |
| 2026-10-07 → 10-27 | Zone video study: 8 frozen hypotheses + stages 26–30, 35 (sweep-and-reject, CHoCH retrace, Tokyo IFVG, clock setups, 4H breakout, Silver Bullet) | zone_video_study_2026-10-07 | ≥ 14 | All fail; zones = placebo boxes |
| 2026-10-27 | QF15 signals (two entry versions, pending entries) | qf15_backtest_2026-10-27 | ≥ 4 | = random entries; the dashboard win rate is a look-back illusion |
| 2026-11-07 | $1–3 scalps at levels and times (gold 1m) | scalp_study_2026-11-07 | 168 + TP/SL grid | 0 positive in both years; TP1/SL50 wins 96 % at PF 0.6 |
| 2026-11-07 | Own edge search: trend ensemble, hour-of-day, daily reopen | edge_search_2026-11-07 | 3 | Trend < buy-and-hold; reopen gap **real** (t 4.65) but ≈ costs |
| 2026-11-07 | Hold through heat at OB/FVG | heat_recovery_2026-11-07 | 1 | 80 % wins, PF 0.7–0.9 |
| 2026-11-07 | NY sweep of Asia low (theorem, Desk Context alert, 5-day levels) | asia_sweep_theorem_2026-11-07 | ≥ 4 | PF 0.45–0.90 ≈ random |
| 2026-11-07 | Replay-watch ideas (sweep fades, ADX turn, FVG pullback, sweep-reclaim, spike fade) | replay_watch_2026-11-07 | 6 | Best PF 0.95–1.02; sweep-reclaim PF 0.66–0.79 over 14 years |
| 2026-11-08 | Noise-area breakout (the AI assistant's idea) | noise_breakout_2026-11-08 | 2 | PF 0.97; morning momentum **real** (t 4.8) but < costs |
| 2026-11-08 | 100-setup catalog + 18:00 range breakout | catalog_100_2026-11-08 | 48 | 0 pass; coin flips before costs |
| 2026-11-08 | Trade the opposite of all losing rules | opposite_2026-11-08 | 78 | 0 pass; fees are paid both ways |
| 2026-11-08 | Spike follow to 13:30 (+ mirror of the fade) | spike_follow_2026-11-08 | 2 | PF 1.06, t 0.8: fails |
| 2026-11-08 | Buy support / sell resistance + flips | sr_plan_2026-11-08 | 9 | PF 0.79–0.83, no profitable year |
| 2026-11-08 | Tokyo VWAP-band bias + NY pullback | vwap_bands_2026-11-08 | 4 | PF 0.66; bias 63.5 % in 2024–26 only (**open thread**) |
| 2026-11-08 | Tokyo bias + QF CORE OB/FVG | tokyo_obfvg_2026-11-08 | 5 | PF 0.62; no-bias control 0.66 |
| 2026-11-09 | Spike follow exits: +1R target, small profit +0.3R | paper_account_2026-11-09 | 2 | PF 0.92 both; all $10k accounts froze in 2014 |
| 2026-11-09 | 5m spike scalp: $20–50 target, $20–500 stop, 1 h / 4 h, 4 sessions, 3 spike sizes | spike_scalp_grid_2026-11-09 | 432 | 0 of 432 profitable; random entries do as well |
| 2026-11-09 | Same spikes, bigger targets ($20 → $500, none), stops $50–500, holds up to 1 day | spike_scalp_grid_2026-11-09 (tp_ladder) | 240 | No target makes NY AM profitable (best PF 0.99); 7 all-session combos PF 1.01–1.07, all losing in 2012–19 |
| 2026-11-09 | My fixed exit ($250 stop, $100 target) × the standard entry toolkit (MAs, breakouts, RSI, BB, MACD, patterns, sessions, levels, gaps) × with/against daily trend | fixed_exit_search_2026-11-09 | 1,764 | 0 pass, 0 even naive winners; random BUY made money only in 2020–26 (drift); closest rule lost −$890 on unseen MGC weeks |

| 2026-11-09 | US stocks 1926–2026: the 6 published factor strategies (size, value, momentum, reversal, profitability, investment) + the market | all_markets_2026-11-09 (Kenneth French data) | 7 | Only owning the market still works; all 6 strategies faded after publication (none t ≥ 2 after) |
| 2026-11-09 | Trend following across 38 futures (TSMOM-12, 1/3/12 blend), my TradingView data 1981–2026 | all_markets_2026-11-09 (trend) | 2 | TSMOM-12 Sharpe 0.83 over 46 yrs, but 0.39 (t 1.46, beats 94.6 % of random) after publication: fails narrowly; blend fails |
| 2026-11-09 | Market-structure entries (BOS, CHoCH, retest, discount, sweep, OB, FVG, higher low) on 5m/15m/1h/4h, ± higher-TF trend, × 5 stops × 9 exits (0.5R → 5R, trail, BE, time) | structure_exits_2026-11-09 | 2,880 | 0 of 10 finalists pass; the target changes the win rate, not the result; 5 m fees ≈ 0.3R a trade; 2020–26 profits = gold's rally (random timing did as well or better for 9 of 10); 0 of 90 cross-market cells reach t ≥ 2 |
| 2026-11-11 | QF INSTITUTIONAL PRO (#131) signals as coded; then QF PRO v2 MEASURED (its 3 setups fixed: TREND, RANGE, BREAK, + score gate) | qf_institutional_pro_2026-11-11 | 2 | v1: Trend/Range never fire, only 196 breakout signals in 4 yrs GC 5m: −0.017R, t −0.34 (dashboard claimed WR 89.9 %, PF 16.68 from placeholders). v2 last 7 weeks: 60 trades, −0.076R, PF 0.79; random-time twin did +0.23R; 4-year v2 run pending |

**Total so far: at least 5,668 rule variants on the same 2012–2026 gold history** (counting only the numbers we are sure
of). None has passed a pre-registered bar. Outside gold: 7 published US stock strategies were checked, and only the
market itself passed.

What is real but too small to trade at 1 MGC: the 17:00–18:00 reopen drift (+0.42 pt a day), morning direction carrying
into the 13:30 close (t 4.8), and riding morning spikes (+$1–2 a trade). Every one of them is about the size of the
$3–5 round-trip cost.
