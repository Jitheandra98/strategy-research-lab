# MGC replay study: what STATION2's zones actually do

**Bottom line.** 5-minute zones are not a trading edge on their own, with or without a 5-minute confirmation candle. The one pattern that held up is trading **4H zones in the direction of the 4H trend**. It made about **+0.2R per trade after costs** in both halves of the replay, and the same zones traded against the 4H trend lost. The edge is thin, depends partly on a few big trend moves, and the bars were rebuilt from video pixels. Treat it as a strong candidate for forward testing, not a proven system.

The whole 3 h 37 m recording was used, every frame at a 3-second interval. It covers MGC from **2 Nov 2025 to 30 Sep 2026**: 280 trading days, 63,925 five-minute bars, 13,688 zone arrivals and about 45,000 simulated confirmation trades.

---

## 1. Turning the video into data

A 3-hour screen recording can't be "watched" at research precision, so the bars were rebuilt from it. The full pipeline is in `pipeline/`, and `pipeline/run_all.sh` reproduces everything.

1. **Frames.** A full 2560×1440 frame every 3 s: 4,337 frames, with 99.98% digitised successfully.
2. **OCR.** Apple Vision read the price axis, the time axis and both pane headers on every frame.
3. **Candles.** A reader for STATION2's candle style (grey wick and outline, green/red body edges). It measures each pixel against the empty columns between bars, removes zone-box borders and zone text that sit over candles, and flags bars under signal labels. Price scale is a robust fit to the axis labels, with residuals under about 1 px ≈ 0.05 pt.
4. **Stitching.** Consecutive frames were aligned by price agreement, and each bar took the median of the (typically 8) frames that showed it.
5. **Dates.** A walk along the CME Globex calendar, with Christmas, New Year and Good Friday closures. The day labels OCR'd off the chart axis were held out and agree **1,031 of 1,056 times (97.6%)**.
6. **4H bars** were built on the CME session grid (17:00, 21:00, 01:00, 05:00, 09:00, 13:00 CT). This grid matched the chart's own 4H header opens in 76% of frames, against 7% (UTC-aligned) and 13% (midnight-CT-aligned). That confirms how TradingView aligns MGC 4H bars.

**Validation against numbers typed on screen.** In every frame, the 4H pane header shows the exact O/H/L/C of the forming 4H bar. Comparing it with the same window of rebuilt bars (519 frames where the window aligned):

| | within 0.3 pt | within 1 pt | ours too short by >1 pt | ours too long by >1 pt |
|---|---|---|---|---|
| 4H high | 80% | 86% | 10.6% | 3.7% |
| 4H low | 83% | 89% | 7.9% | 3.3% |

Bar-to-bar continuity (open versus previous close): median 0.10 pt, 90th percentile 1.9 pt. 534 glitch bars (0.8%) were repaired and flagged.

**The main data caveat.** STATION2's own signal labels cover the candles near entries. Labels only ever **hide** wick ends, so the rebuild leans towards short wicks, which makes stops look slightly safer than they were. §4 stress-tests this directly.

Screenshots `screenshots/overlay_*.jpg` redraw the rebuilt zone engine over real frames. Key zones land on the indicator's own boxes, for example the FVG at 4968–4971 and the ★ STATION OB at 4944–4949 on 23 Jan 2026, and the ★ STATION 4H zone at 4486–4491 on 9 Jan.

## 2. The indicator: keep the map, ignore the trades

Full detail is in [`indicator_teardown.md`](indicator_teardown.md). The zone code (FVG, OB-on-structure-break, 4H FVG import, dedupe, lifecycle, score, EQH/EQL pools) was ported line for line. The decision layer (POSITION, REFLEX, POOL-RIDE, BREAKER, the "court" ledger) was not used to build any rule, only for comparison.

Two map behaviours you should know about:

- **The 60-zone cap hides 4H zones on your 5m chart.** 21% of imported 4H zones (36 of 169) were evicted from the 5m pane while still unbroken, after a median of about 3 days. On the 4H pane they were still live.
- **Zones "die" on a wick.** 12% of 5m first arrivals wicked through the far edge and closed back (`SWEEP_RECLAIM`). The indicator marks those zones consumed.

## 3. Findings, ranked by strength of evidence

Unless stated, trades are entered at the next 5m open after the signal. Stop: beyond the zone or sweep extreme plus 0.25 ATR. Target: 2R. Time stop: 48 bars (4 h). Cost: 0.3 pt per round trip. The stop is checked first when stop and target are both touched in one bar, and there are no intraday gap fills. Development ("DEV") = 3 Nov 2025 → 20 May 2026; HOLDOUT = 21 May → 30 Sep 2026. CIs are 95%, from a day-block bootstrap.

### F1. 5-minute zones have no edge, and confirmation candles don't create one (strong)

![reaction mix](figures/reaction_mix.png)

At the first arrival into a 5m FVG or OB, price moved ≥ 1 ATR away in the zone's favour about **54%** of the time (including sweep-reclaims), and **closed through the far edge first 45%** of the time. That's close to a coin flip, and 5m zones are small (median risk about 7 pt), so the 0.3 pt cost is a real drag.

| Entry after arrival, all zones (94% are 5m FVG/OB) | n | Mean R, DEV | Mean R, HOLDOUT |
|---|---|---|---|
| Touch, no confirmation | 10,321 | −0.014 | −0.009 |
| Close back outside the zone (reclaim) | 9,082 | −0.036 | −0.013 |
| Engulfing | 5,546 | −0.034 | +0.005 |
| 5m CHoCH/BOS | 1,874 | +0.026 | −0.046 |
| Displacement candle (≥ 1.2 ATR body) | 1,253 | −0.071 | −0.044 |
| Rejection wick | 1,981 | −0.026 | −0.038 |
| Pool sweep then reclaim | 666 | −0.018 | +0.041 |
| New 5m FVG | 2,172 | −0.008 | −0.007 |

None is reliably positive, and none survives doubled costs or the pessimistic-wick test (§4). The one-at-a-time 5m-touch equity curve in the chart below ends positive, but that is +0.03R per trade across 3,729 trades with a 67R drawdown. It was negative in earlier builds of the data and goes negative once costs double. It is noise.

### F2. 4H zones in the direction of the 4H trend: the one consistent positive (moderate)

"4H zones" = STATION2's zones on the 4H chart, plus 4H FVGs imported onto the 5m chart. "4H trend" = the sign of the EMA(100) slope over 10 bars on 4H (the indicator's own `trendDir`), taken from the last closed 4H bar.

| First-touch entry at a 4H zone, 2R | n | Win | Mean R | 95% CI |
|---|---|---|---|---|
| **With the 4H trend**, DEV | 190 | 54% | **+0.160** | −0.005 to +0.337 |
| **With the 4H trend**, HOLDOUT | 132 | 56% | **+0.215** | +0.021 to +0.418 |
| **With the 4H trend**, all | 322 | 55% | **+0.183** | +0.058 to +0.315 |
| Against the 4H trend, all | 232 | 44% | −0.060 | −0.199 to +0.091 |

Traded one position at a time (grade A in [`strategy.md`](strategy.md)): **195 trades, 55% winners, +0.195R per trade (CI +0.07 to +0.33), +38R in total, max drawdown 9.2R, at worst 4 losses in a row, about 3.5 trades a week**. DEV was +0.25R and HOLDOUT +0.11R. It was positive for both longs (+0.10R, 88 trades) and shorts (+0.27R, 107 trades).

![equity](figures/equity.png)

Stress tests on the all-signals version:

| Stress | Mean R |
|---|---|
| Doubled costs | +0.165 |
| Entry one bar late | +0.147 |
| Top 5% of winners removed | +0.082 |
| Arrivals within 3 bars of the zone appearing excluded | +0.178 |

Month by month it lost a little from November to January (the parabolic blow-off) and made money from February to September. Nearly half the trades exit on the 4-hour clock, so this is largely "buy the pullback into a 4H zone and let the trend carry it", not a quick bounce.

Why it's only "moderate": the DEV confidence interval touches zero, holdout n is under the 100 pre-registered, and the result leans on the right tail. Of about 970 rule variants tested, **9 passed the DEV bar and 8 were confirmed on HOLDOUT, all from this same 4H-zone family.** The one DEV pass from another family (5m OB + new 5m FVG) failed on HOLDOUT (−0.01R). That's the false-positive pattern the holdout exists to catch.

### F3. On 4H zones, 5m confirmation adds nothing measurable (moderate)

This answers the question at the centre of the brief: what 5m behaviour should precede an entry once price reaches a 4H zone? None of the tested ones improves on simply entering at the touch.

| 4H zone, with trend, 2R | n | Mean R (all) |
|---|---|---|
| Touch (no confirmation) | 322 | +0.183 |
| Close back outside the zone | 285 | +0.191 |
| 5m CHoCH/BOS | 61 | +0.020 |
| New 5m FVG | 106 | −0.008 |

![4H confirmations](figures/confirmations_4H_ANY.png)

CHoCH and FVG confirmations arrive late, need wider stops (median 7 ATR), and mostly end on the time stop. The reclaim close performs about the same as the touch. It's a reasonable alternative if you prefer to see the zone hold first, but it isn't an improvement.

### F4. When 4H zones hold and when they break (moderate, descriptive)

"Held" = a ≥ 1 ATR bounce before any 5m close through the far edge. These effects were consistent in DEV and HOLDOUT. They describe behaviour and were **not** tested as trade filters.

| Condition at the 4H-zone touch | Held with | Held without |
|---|---|---|
| Touch bar closes back outside the zone | 84% | 61% |
| Zone ≥ 3 × 5m ATR tall | 85% | 61% |
| 5m trend aligned with zone | 81% | 70% |
| London session (07–12 UTC) | 79% | 71% |
| High-volatility regime | 68% | 81% |
| Fast approach (≥ 2 ATR in 6 bars) | 65% | 79% |

Holding more often didn't translate into better expectancy. The reclaim confirmation (row 1) is the tradeable form of that row and matched the plain touch. These are useful for grading your conviction, not as extra entry gates.

### F5. Continuation after a zone breaks loses (strong)

Waiting for a broken zone to be retested from the other side, then trading the break direction (the clean version of the indicator's BREAKER "door 2"), returned **−0.11R per trade over 2,543 trades** (CI −0.17 to −0.06). A broken 5m zone is not a reliable flip level.

### F6. The indicator's own REFLEX contract: 59% winners, zero edge (strong)

Replayed exactly on its triggers (first touch of a score ≥ 3 zone, target +1 ATR, stop beyond the far edge, 8-bar clock): **2,860 trades, 59% winners, −0.001R per trade** (CI −0.031 to +0.031). The average win is +0.59R and the average loss −0.85R. A high hit rate with a small target and a wide stop is break-even before any slippage.

### F7. Session and time of day (weak)

Zone hold rates barely differ by session, from 54% (NY) to 58% (London) across all arrivals. The 12-bar drift after arrival is most favourable in London hours (+0.23 ATR against +0.06 in Asia). Nothing here justified a session filter. The indicator's London block was not borne out as a zone-reaction effect.

## 4. How the evidence could be wrong

- **Wick truncation.** The pessimistic test re-ran everything with every label-covered bar's wicks extended 1 pt, then 3 pt, in both directions (`analysis/stress_label_wicks.csv`):

  | Setup | final | +1 pt | +3 pt |
  |---|---|---|---|
  | 4H with-trend touch, all | +0.183 | +0.190 | +0.193 |
  | Setup A one at a time | +0.195 | +0.227 | +0.229 |
  | 5m zones touch, all | −0.015 | −0.046 | −0.142 |

- **One market, one period.** The holdout is later data from the same recording. It isn't an independent market, instrument or regime.
- **Thin tail dependence.** The 4H edge is about +0.08R without its top 5% of winners.
- **Not modelled:** volume, intrabar order (stop-first is assumed), slippage beyond 1 tick, and contract rolls (B-ADJ continuous prices).
- **Multiple testing.** About 970 variants were measured. Only the 4H family's DEV→HOLDOUT agreement is treated as evidence.

## 5. Examples from the recording

Each image shows the video frame, the rebuilt zone (box), the arrival (vertical line) and, for grade-A trades, entry, stop and 2R target, captioned with the market time and **video timestamp**:

| File | What it shows | Video |
|---|---|---|
| [example_1032_4H_REJECT.jpg](screenshots/example_1032_4H_REJECT.jpg) | 4H supply zone, with the trend, rejected; +1.94R | 0:21:27 |
| [example_13273_FVG_REJECT.jpg](screenshots/example_13273_FVG_REJECT.jpg) | 4H FVG demand, 28 Jan 2026 blow-off, time exit +1.59R | 0:57:06 |
| [example_13380_OB_CHOP.jpg](screenshots/example_13380_OB_CHOP.jpg) | 4H OB demand, slow grind to target, +1.99R | 1:44:09 |
| [example_62_4H_REJECT.jpg](screenshots/example_62_4H_REJECT.jpg) | A loss: the zone did bounce 1 ATR, but not before the stop | 0:03:18 |
| [example_2118_4H_REJECT.jpg](screenshots/example_2118_4H_REJECT.jpg) | A loss at a 4H supply zone, 2 Jan 2026 | 0:40:57 |
| [example_10045_FVG_BREAK.jpg](screenshots/example_10045_FVG_BREAK.jpg), [example_2030_FVG_BREAK.jpg](screenshots/example_2030_FVG_BREAK.jpg) | Typical 5m FVGs closed straight through | 2:40:15, 0:39:42 |
| [example_9454_OB_REJECT.jpg](screenshots/example_9454_OB_REJECT.jpg) | A 5m OB that did reject; common, but it didn't pay on average | 2:38:18 |
| [overlay_seg1_000005.jpg](screenshots/overlay_seg1_000005.jpg) and 3 others | Rebuilt zone engine drawn over the indicator's own boxes | — |

## 5b. Your "zones are magnets" model, tested directly (`pipeline/13_magnet.py`)

**Gold's day is big.** The median daily range in this sample was **92 points**, and every day moved at least 30. So a 30-point move is always there in hindsight. The question is whether the zone setup catches it more often than chance.

**1. Magnet: not supported.** 56% of 4H zones were revisited within 4 × 4H bars. But from random moments, price reached a level the same distance away (median 24 pt), on the same side, 58% of the time. 4H zones are **no more attractive than any other price at that distance**. 5m zones show a tiny +2–4 point lift.

**2. Where the reaction happens: 4H zones mostly react at the edge.** When a 4H zone held, the turn came in the near third of the box 66% of the time, the middle third 21%, the far end 7%, and via a sweep beyond it 6%. 5m zones spread out much more: 39% near third, 24% middle, 16% far end, 22% sweep. A 5m entry at the first touch often gets run through the whole box.

**3. Repeat reactions: supported.** 70% of 4H zones got a second arrival, usually within about an hour (median 0.27 of a 4H bar). Second arrivals held 77% of the time, and 78% after a first hold. Third arrivals held 72%.

**4. Your setup (4H zone + first rejection → 5m entry → 30-point target), one position at a time, costs included:**

| Setup | Trades (per week) | Hit +30 pts | Stopped | Avg per trade | Random entry, same direction and stop |
|---|---|---|---|---|---|
| **With 4H trend**, stop beyond the zone (median 30 pt) | 168 (3.0) | 50% | 35% | **+2.5 pts ($25/MGC)** | +1.9 pts |
| **With 4H trend**, fixed 15-pt stop | 180 (3.2) | 39% | 56% | **+3.3 pts ($33/MGC)** | +1.5 pts |
| Against 4H trend, stop beyond zone | 110 | 27% | 45% | −3.9 pts | −1.4 pts |
| 5m zone + rejection (control) | 2,208 | 29% | 66% | +0.4 pts | −0.3 pts |

With the 4H trend the setup is profitable (DEV +1.1 pts, HOLDOUT +5.3 pts with the zone stop). However, **most of the gain also appears in random entries taken in the same direction**, so much of it is the trend itself. The zone adds roughly 0.5–2 points per trade on top. Against the trend, the zone rejection does worse than random. The setup fires about 3 times a week, not daily.

## 6. Files

| File | Contents |
|---|---|
| [`strategy.md`](strategy.md) | The rules, grades, sizing reality check, pseudocode |
| [`backtest_spec.md`](backtest_spec.md) | Exact definitions, simulation and acceptance rules |
| [`indicator_teardown.md`](indicator_teardown.md) | What in STATION2 makes zones versus trades |
| [`open_questions.md`](open_questions.md) | Data caveats, ambiguities, and questions for you |
| `zones.csv` | Every zone from both engines (9,073 rows), with birth/touch/consume/invert times |
| `events.csv` | Every zone arrival (13,688) with context, reaction, MFE/MAE at 5/15/30/60/120 min, video timestamp |
| `data/bars_5m.csv`, `data/bars_4h.csv` | The rebuilt series, with per-bar quality columns |
| `data/confirmation_trades.csv` | Every simulated trade (all confirmations × 1/2/3R) |
| `data/frame_index.csv` | Each video frame → market time, alignment, 4H header OHLC |
| `analysis/*.csv`, `figures/*.png` | All tables and charts above |
| `pipeline/` | The full reproducible pipeline (stages 01–12) |
