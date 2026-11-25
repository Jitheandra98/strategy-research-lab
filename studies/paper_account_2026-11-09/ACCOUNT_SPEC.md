# PAPER ACCOUNT: inputs and qualification gate (draft, 2026-11-09)

On 2026-11-09 the owner pasted a mandate: run one paper account as portfolio manager, execution engine and risk officer.
The mandate puts survival first. It allows a trade only when there is evidence of positive expectancy after costs, and it
compounds only realized gains. The process must be proven out-of-sample before the run, and every decision is logged.
This file is step 1 of that mandate. It lists the inputs that exist and the ones that are missing, and it sets out the
evidence a strategy needs before the paper run starts.
Nothing in this file is a fill, a balance or a market observation. Every assumption is marked ASSUMPTION.

## 1. Inputs that exist
| Input | What we have | Where |
|---|---|---|
| Gold history | Spot 5m, 2012-01-02 18:00 → 2026-09-24 19:55 ET (1,035,986 bars) | trading-video-intel/tools/pine_runner/xau5m.f64 |
| MGC futures history | 1h 2025-01-01 → 2026-11-06 (10,947 bars); 5m 2026-09-13 → 2026-11-06 (11,040 bars) | research/edge_search_2026-11-07/mgc1_60m.json, mgc1_5m.json |
| Live bars for a forward run | TradingView bridge (the app must be open with port 9222) | tradingview-mcp/ |
| Instrument | MGC micro gold: $10 per point, 0.1 pt tick = $1, whole contracts only | |
| Candidate rules | Spike follow MAIN, frozen before it was tested | research/spike_follow_2026-11-08/SPEC.md |
| Candidate trade list | 1,941 trades, 2012-01 → 2026-09 | research/spike_follow_2026-11-08/trades_main.csv |
| Fill rules already used | The stop counts first inside a bar; a bar that opens through the stop fills at that open | research/spike_follow_2026-11-08/spike_follow.py |
| Cost model | 0.3 pt round trip ($3 per MGC), stress 0.5 pt. ASSUMPTION, never measured | |
| Earlier pass bar | PF ≥ 1.15 in each of 2012–19, 2020–23, 2024–26; long and short both profitable; profitable at 0.5 pt; ≥ 9 of 15 years; beats random same-clock entries | research/spike_follow_2026-11-08/SPEC.md |

## 2. Inputs that are missing (the owner decides)
| # | Input | Why it matters | Default, used only if the owner says "use defaults" (ASSUMPTION) |
|---|---|---|---|
| 1 | Starting equity | MGC can't be split, so equity decides which signals are affordable (table below) | $10,000 paper; $2,000 also reported |
| 2 | Permanent failure floor | Ends the run | $7,500 |
| 3 | Max drawdown from peak | Freezes trading pending review | 15 % of peak equity |
| 4 | Daily loss limit | Halts the session | 2 % of start-of-day equity |
| 5 | Max risk per trade and across open trades | Sizing | 1 % of min(realized, mark-to-market) equity per trade, counting the stop + 0.2 pt slippage + cost; 2 % across all open trades; no new trade if a stop-out with 2× slippage would leave less than two trades' risk above the floor |
| 6 | Strategy | | Spike follow MAIN, the closest intraday candidate (positive after 0.3 pt in all three periods). It is NOT qualified (section 5) |
| 7 | Instrument, timeframe, hours | | MGC, 30m bars, entries 08:30–10:30 ET, flat by 13:30 ET. No overnight holds, so no financing cost |
| 8 | Real costs | At this edge size, 0.1 pt decides the result | Commission from the owner's broker fee page; spread and slippage measured from MGC quotes at 08:30–10:30 and 13:30 ET |
| 9 | Evaluation period | | Historical process test 2012 → Sep 2026. Forward paper run of a length fixed before it starts (suggest 3 months) |
| 10 | Unseen history | None is left. Every year from 2012 to Sep 2026 has been used by our tests (50 rules on 2026-11-08 alone) | Only forward data. Also 6 weeks of MGC 5m (Sep 25 → Nov 6 2026) that spike follow has never seen (≈ 15 trades at 129 a year) |

How starting equity and the risk cap decide what the account can trade. Spike-follow signals, 1 MGC, risk = stop + 0.2 pt
slippage + 0.3 pt cost:
| Equity | 0.5 % cap | 1 % cap | 2 % cap |
|---|---|---|---|
| $2,000 | 0.1 % | 0.8 % | 15.1 % |
| $5,000 | 2.5 % | 29.2 % | 72.2 % |
| $10,000 | 29.2 % | 72.2 % | 92.5 % |
| $25,000 | 81.6 % | 94.7 % | 99.0 % |

Stop at 1 MGC: p10 $30, median $64, p90 $164, p99 $495. Worst historical drawdown at 1 MGC with every signal taken:
$2,969 at 0.3 pt, $4,238 at 0.5 pt. 111 of 1,941 trades lost more than 1.1R because price gapped through the stop
(worst −2.24R). Longest losing streak: 11 trades.

## 3. Evidence that qualifies a strategy for the paper run (proposed; agree before any test)
All seven must hold. The rules, exits, costs and this gate are written down before the test and are not changed after it.
1. **Expectancy after costs.** The mean net trade is above 0 with t ≥ 2 at the base cost. An idea found by searching the
   same 2012–2026 gold history again (anything we build from now on) needs t ≥ 3, because dozens of rules have already been
   tried on that history.
2. **Earlier pass bar.** PF ≥ 1.15 in each period, at least 9 of 15 years profitable, and long and short both profitable.
   It must still be profitable at 0.5 pt or at 2× the measured cost, whichever is higher, and it must beat random entries
   at the same clock time.
3. **Chronological.** Choices such as the exit policy or filters are made on 2012–2019 only, then judged once on
   2020 → Sep 2026.
4. **Survival under the account limits.** In the account simulation the run never touches the floor, and the
   peak-to-trough drawdown stays under the limit. It must stay under in the 95th percentile of 10,000 reshuffled trade
   orders, with 2× slippage at stops and gap-through fills.
5. **The affordable trades pass on their own.** A small account only takes the small-stop trades. The signals that fit
   the risk cap must pass 1–4 as a group of their own.
6. **Real costs.** Commission and slippage are measured, and 1–5 still hold at those costs.
7. **Exit-policy comparison (mandate §5).** Same entries, stops and limits for each policy:
   A) time exit at 13:30 (as tested); B) fixed target at +1R, else 13:30; C) small-profit exit that takes +0.3R net at
   the first touch, else 13:30. Report net result, drawdown and survival for each.
   If one 30m bar touches both the stop and a target, resolve it on the 5m bars. If one 5m bar touches both, the stop counts
   first. Earlier studies found that small targets raise the win rate but not the profit (scalp study 2026-11-07: TP1/SL50
   won 96 % of trades at PF ≈ 0.6). So C is not expected to help, but it is tested rather than assumed.

## 4. Decision log (mandate §6): one row per decision, fills logged separately
- Decision: timestamp, action (ENTER / EXIT / REDUCE / HOLD / NO TRADE / HALT / FREEZE / END), reason, estimated costs,
  risk at stake ($), realized equity, mark-to-market equity, drawdown from peak, distance to floor.
- Fill: order id, intended price, simulated fill price, slippage, commission.

## 5. Status on 2026-11-09: NO DEPLOYMENT
| Candidate | After-cost result | Gate |
|---|---|---|
| Spike follow MAIN | +0.20 pt ($2.04) per trade at 0.3 pt, t = 0.81; +$0.04 at 0.5 pt (t = 0.02). PF 1.09 / 1.02 / 1.05 by period; 8 of 15 years. Beats random by +0.054R (t = 1.78) | Fails 1 and 2 |
| MGC daily reopen gap | +0.42 pt gross (t = 4.65, 360 days, 2025–26), so +0.12 pt at 0.3 pt (t ≈ 1.3) and −0.08 pt at 0.5 pt. It fills at 16:59 and at the 18:00 reopen, the hardest minutes of the day to get a good fill | Fails 1 and 2 |
| All other tested rules | Lost after costs | Fail |

Proving that spike follow makes money (net mean above 0 at t = 2) would take about 13,000 trades, ≈ 100 years at
129 a year. (The 2,260 trades / 17 years in its RESULTS.md is the smaller question of whether it beats random entries.)
A few months of paper trading can neither confirm it nor reject it.

## 6. What a forward paper run can and cannot show
- It can show whether the engine obeys its own limits and how far real fills land from the model. It can also measure
  real costs and show how halts behave.
- It cannot show whether a thin edge is real. Its P&L over a few months is noise, so judge it only against the
  backtest's range.
- Spike follow may run on paper only as a labelled PROCESS TEST: "strategy not qualified".
- The rules use completed 30m bars, so the forward run can be scored once a day after 13:30 ET from that day's bars,
  using only the bars that existed at each decision. Nobody has to be awake at 08:00.
