# STATION2 (THE STATION APPOINTMENT v2.0): what makes zones, and what makes trades

This covers the Pine v6 source pasted into this session (`CE_VERSION = "STA-2.1"`). The zone side is ported line-for-line to [`pipeline/zone_engine.py`](pipeline/zone_engine.py), and every zone in `zones.csv` comes from that port. The decision side was not used to build any rule in this study.

## KEEP: the zone map (trusted)

| Map element | Exact rule in the source | Parameters |
|---|---|---|
| **FVG** (3-candle gap) | Bull: `low > high[2]` → zone `[high[2], low]`. Bear: `high < low[2]` → zone `[high, low[2]]`. Confirmed bars only. | Size 2–150 **points** (absolute, not ATR) |
| **OB** (order block) | On a **close** through the last confirmed pivot (`ta.pivothigh/low(3,3)`, known 3 bars late), take the most recent opposite-colour candle within 20 bars and use its full high–low (wicks included). | `PIVOT_LEN=3`, `OB_LOOKBACK=20` |
| **4H FVG on the 5m chart** | `request.security("240", [low[1], high[3], high[1], low[3], time[1]], lookahead_off)`: the 4H gap between bars j-3 and j-1 is added when `time[1]` changes. | same size filter |
| **Dedupe** | A new zone is dropped if a living same-direction zone overlaps more than 50% of the new zone. | — |
| **Cap** | More than 60 live zones evicts the **oldest**, whatever its quality or timeframe. | `MAX_ZONES=60` |
| **Lifecycle** | *Touch*: entry from the correct side, previous bar's extreme outside. *Consumed*: a **wick** reaches the far edge. *Inverted*: a consumed zone is re-crossed from the other side, flips direction, and dies after 2 touches. Consumed zones archive after 400 bars. **Active zones never expire by age.** | `MAX_TOUCHES=1`, `ZONE_ARCHIVE=400` |
| **★ STATION score** | size ≥ 1 ATR (+2), OB (+1), untouched (+1), direction = EMA100 slope over 10 bars (+1); a zone scoring ≥ 3 is shown as a station. | `SCORE_MIN=3` |
| **EQH/EQL pools** | Two confirmed pivots within 0.15 ATR and 60 bars. The pool is swept when a wick crosses it. | `EQ_TOL_ATR=0.15`, `EQ_WINDOW=60` |

### Map behaviours that matter before trusting a box

1. **The 4H zones on the 5m chart appear at different times live and on reload.** In replay (realtime), `time[1]` changes on the first 5m bar of a new 4H bar, so the gap appears as soon as it is complete. When the script recalculates on history, `lookahead_off` hands the value over only at the 4H bar's close, 4 hours later. What you saw during replay is the early timing; a reload shows the late one. This study uses the replay timing, which is also the honest real-time availability.
2. **The 60-zone cap evicts 4H zones on the 5m chart.** 5m FVGs and OBs are created many times a day, so imported 4H zones get pushed off the 5m pane after a while even though they are still valid. `report.md` measures how often this happens. The research engine tracks 4H zones on the 4H engine, so eviction does not affect the analysis.
3. **A birth-bar "touch" can happen.** The sensors run before the lifecycle within the same bar, so a zone can register a touch on the bar that created it. The port keeps this and flags it (`birth_touch`). The research uses its own arrival definition, which excludes the birth bar.
4. **Absolute point thresholds.** The 2-point minimum size and the 15-point "turn at station" distance do not scale with volatility. On 5m MGC they mean very different things in quiet Asia hours and in January 2026's 100-point candles.
5. **Consumption is by wick, not close.** One spike through the far edge kills a station even if the candle closes back inside. The sweep-and-reclaim reaction measured in this study is exactly that case.

## IGNORE: the decision layer (untrusted, used only as a comparison column)

| Profile | What it does | Why it is not used here |
|---|---|---|
| POSITION (Appointment A) | CHoCH/BOS within 15 pt of a station, a sweep within 12 bars, route gate, target = farthest pool/structure within 8 ATR, min 2R. Entry next-bar open. | Calibrated on XAUUSD 30m. Many coupled gates can't be tested separately. The far-target default hides nearer obstacles. |
| REFLEX / REACTION | First touch of a score ≥ 3 zone: next-bar open, target +1 ATR, stop far edge ± 0.5 ATR, 8-bar clock. | Payoff is asymmetric: risk is zone size + 0.5 ATR against a 1 ATR reward, so it needs a very high win rate. Measured directly in `events.csv` as `ind_reflex_signal`. |
| POOL-RIDE (B) | First touch plus an unswept pool within 2 ATR beyond it. | Same fill and exit accounting problems as below. |
| BREAKER door-2 | Trades the new direction when a consumed zone inverts. | The source's own comment says the generic version measured dead. |
| LONDON journal | Paper-tracks blocked London setups. | Bookkeeping only. |
| "The Court" ledger | Custom P&L in an `indicator()`, not a broker emulator. | Exits are skipped on the entry bar (`bar_index > entryBar`). Stops and targets use ATR from the fill bar, which is only known at that bar's close. Costs are a flat 0.5 pt. The results are not executable evidence. |

## What the research engine keeps and changes

- **Kept:** every zone-geometry rule above, the lifecycle, the score, and the pools. It uses the same default parameters.
- **Changed:** the 4H-chart engine uses a 100-bar warm-up instead of 250, because the reconstructed series starts at the replay start. A 250-bar warm-up would erase about 6 weeks of 4H data. Pivot ties are treated as strict; TradingView's tie handling is undocumented, and ties are rare at a 0.1 tick.
- **Added for research, not in the indicator:** arrival, reaction, confirmation and trade definitions. They are listed in [`backtest_spec.md`](backtest_spec.md) and were fixed before looking at results.
