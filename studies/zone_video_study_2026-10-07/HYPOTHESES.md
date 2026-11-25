# HYPOTHESES — STATION2 zone interactions, XAUUSD (OANDA) 15m + 4H

Companion to [RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md). The numbers come from `analysis/hypotheses_ALL3.csv`, `analysis/hypotheses_EXTERNAL_2016_2022.csv`,
`analysis/replication.csv` and the real-vs-placebo tables in RESEARCH_FINDINGS §12.

## How to read this file

- **Splits.** All hypotheses were written from DISCOVERY data only (V1 and V2, Sep 2022 – Oct 2023, 5,992 interactions). The definitions were then frozen in
  `analysis/11_hypotheses_FROZEN_*.py` (sha1 `bd7eaff…`). After that they were scored once on:
  - **VALIDATION**: V3, Oct 2023 – Apr 2026, 21,260 interactions.
  - **EXT 22-26**: bars from 2022–2026 that no video showed (11,669 interactions, not on video).
  - **EXT 16-22**: 2016-01 to 2022-09 HistData, which no video covers (33,172 interactions).
- **Units.** ATR = 15m ATR(14) at the arrival bar.
  - **R1** = from the arrival bar's close, price reaches +1 ATR in the zone's direction before it reaches −1 ATR. A tie on the same bar counts as a loss. A coin flip gives ≈ 0.49–0.50.
  - **BRK** = a 15m close beyond the far edge within 10 bars.
  - **tr2_R** = a limit entry at the near edge, stop 0.1 ATR beyond the far edge, target 2R, 40-bar time stop, and 0.30 pt cost. The result is the R-multiple per trade.
- **"rest"** = the same population without the condition. "CI" = 95% Wilson interval, or a t-interval for R.
- **Evidence labels** follow the pre-registration:
  - interesting observation
  - candidate hypothesis: DISCOVERY only
  - moderate evidence: DISCOVERY CI excludes rest
  - strong evidence: the same holds in VALIDATION, with the same sign and the CI excluding rest
- **Video timestamps** (h:mm:ss) are the moment the arrival bar first appears on screen. When replay runs at 3×, the bar sits a few seconds earlier than the timestamp. Examples were drawn by a seeded random sample (`pipeline/13_examples.py`), not picked by hand. More are in `analysis/examples_formatted.txt`.

---

## Ranking (by evidence)

| Rank | ID | One-line claim | Label | Useful for |
|---|---|---|---|---|
| 1 | HN-A | STATION2 zones give no more direction than randomly shifted bands | **strong evidence (negative)** | deciding what to stop doing |
| 2 | H12 | A rejection candle at the zone (close back outside) says nothing about what happens next | **strong evidence (null)** | — |
| 3 | H13 | Waiting 2 bars for "confirmation" does not create an edge | **strong evidence (null)** | — |
| 4 | H11 | A wick past the zone midpoint means the zone is likely to fail (about 60–65%) | **strong evidence** (generic) | no-trade filter |
| 5 | H08 | Zones ≤ 1.3 ATR tall fail about 2.5× more often | **strong evidence** (generic) | no-trade filter |
| 6 | H15 | Zones > 2.4 ATR tall rarely fail (about 9–12%) | **strong evidence** (generic) | stop placement / sizing |
| 7 | HS | Edge trades against the latest 15m BOS/CHoCH direction lose about 0.11–0.17R | **moderate evidence** (selected after validation, generic) | no-trade filter |
| 8 | H06 | NY-AM arrivals (08–12 NY) fail more often | **strong evidence** (generic, effect size varies) | no-trade filter |
| 9 | H07 | NY-PM arrivals react more often | **interesting observation** (failed V3, passed both EXT) | re-test |
| 10 | H04 | Arrivals after a long run (≥ ~3.5 ATR) fail more often | **interesting observation** (failed V3) | — |

Rejected in VALIDATION (none came close): H01 break-continuation, H02 old-zone flip with the 4H trend,
H03 approach state "B", H05 4H score-3 edge trade, H09 hot approach, H10 crowded and blocked, H14 4H FVG losers.
They are listed at the end with their numbers.

"Generic" means that randomly shifted placebo bands of the same height show the same effect, so it is a property of price bands and volatility,
not of STATION2's zone logic. It can still be used as a filter.

---

## HN-A — Zones carry no directional information beyond a random band

**Observation:** In every split, the reaction rate at a STATION2 zone is the same as at a "placebo" zone. A placebo zone is the same zone (same height, birth time, lifetime and direction) moved 1.5–3.0 ATR up or down at random.

**Conditions:** every ARRIVAL and FLIP interaction. The placebo zones are built in `pipeline/07_events.py` with `PLACEBO=1`.

**Prediction:** if the zones meant something, R1(real) − R1(placebo) would be > 0.

**Evidence (ARRIVAL):**

| Split | n real | R1 real | n placebo | R1 placebo | tr2_R real | tr2_R placebo |
|---|---|---|---|---|---|---|
| DISCOVERY | 3,538 | 0.502 | 2,234 | 0.485 | −0.061 | −0.033 |
| VALIDATION | 12,029 | 0.492 | 6,736 | 0.492 | −0.092 | −0.088 |
| EXT 22-26 | 6,595 | 0.505 | 3,525 | 0.514 | −0.090 | −0.075 |

Splitting by first touch, STATION score ≥ 3, zone kind (FVG/OB/4H), chart (15m/4H pane), 4H-trend alignment and session gives 30 cells.
**No VALIDATION cell differs from placebo by more than |z| = 0.95.** The biggest discovery difference was NY-PM, +11.6 points with z = 3.4. In V3 it was +0.1 points.

**Median favourable / adverse move (20 bars):** 1.89 / 1.89 ATR in V3. The real-zone means are 2.54 and 2.59. They are symmetric.

**Examples / counterexamples:** not applicable. This is a whole-population result.

**Possible explanation:** gold on 15m is very close to a random walk at the 1-ATR scale. FVG and OB boxes are drawn from the same candles that the price path is made of, and they do not add information about future order flow.

**Confidence:** HIGH. **Risk of overfitting:** LOW. Nothing was fitted.

**Next validation:** repeat it with the indicator's own boxes exported from TradingView instead of the Python port. That would remove the zone-matching uncertainty described in §2 of the findings. Also try other symbols (MGC futures, EURUSD) and the 5m/1H panes.

---

## H12 — The rejection candle is not informative (null)

**Observation:** If the arrival candle closes back outside the zone (wick in, body out), price afterwards does exactly what it does after any other arrival.

**Conditions:** ARRIVAL; the arrival bar's close is on the reaction side of the near edge (`close_loc == OUTSIDE_NEAR`). The decision is made at that close.

**Prediction (null):** R1 from the close is within ±4 points of the base.

**Evidence:**

| Split | n | R1 | 95% CI | rest | mean / median MFE | mean / median MAE |
|---|---|---|---|---|---|---|
| DISCOVERY | 1,754 | 0.487 | 0.464–0.511 | 0.517 | 2.77 / 2.01 | 2.76 / 1.96 |
| VALIDATION | 6,101 | 0.492 | 0.479–0.504 | 0.492 | 2.58 / 1.91 | 2.63 / 1.90 |
| EXT 22-26 | 3,403 | 0.486 | 0.469–0.503 | 0.527 | 2.51 / 1.84 | 2.58 / 1.96 |
| EXT 16-22 | 9,899 | 0.495 | 0.485–0.505 | 0.513 | 2.60 / 1.86 | 2.54 / 1.81 |

By close location in DISCOVERY, R1 was:
- closed beyond the far edge: 0.500
- closed inside: 0.518
- closed back outside: 0.487

All events below closed back outside the zone on the arrival bar. They were drawn at random with seed 7.

**Rejection candle that worked** (+1 ATR first):
- V3 5:56:44 (2025-04-10 05:00 NY, demand FVG 3101.16–3104.32)
- V3 2:41:57 (2024-03-20 13:00 NY, supply OB 2173.49–2178.95)
- V3 8:05:37 (2025-12-10 20:00 NY, supply OB 4246.32–4259.10)

**Rejection candle that failed** (−1 ATR first):
- V1 2:05:28 (2023-01-20 11:00 NY, demand OB 1920.51–1925.34)
- V3 2:11:05 (2024-02-21 11:00 NY, demand 4H 2019.64–2023.35)
- V3 4:23:55 (2024-06-30 22:30 NY, demand OB 2319.40–2324.81)

In the full population these two outcomes occur equally often.

**Possible explanation:** the "rejection" is already priced into the close. What happens next is a new random draw.

**Why it looks predictive on a chart:** an edge trade that is already filled looks good when the candle closes back out. That is because the candle *is* the first part of the trade's own path, which is look-ahead (§12 of the findings).

**Confidence:** HIGH. **Risk of overfitting:** LOW.

**Next validation:** the same test on 5m and 1H. Also try "close back outside" plus a volume spike, once volume data is available.

---

## H13 — Waiting for confirmation does not help (null)

**Observation:** If you wait up to 2 bars after arrival, see the price close back outside the zone and never close beyond the far edge, then enter, R1 from that point is still a coin flip.

**Conditions:** ARRIVAL; `c2_close_out == 1` and `c2_closed_beyond == 0`. Entry is the close of bar i+2.

**Prediction (null):** R1 from bar i+2 is within ±4 points of the base.

**Evidence:**

| Split | n | R1 | 95% CI | rest |
|---|---|---|---|---|
| DISCOVERY | 1,739 | 0.476 | 0.453–0.500 | 0.486 |
| VALIDATION | 5,842 | 0.494 | 0.481–0.506 | 0.508 |
| EXT 22-26 | 3,276 | 0.501 | 0.484–0.518 | 0.499 |
| EXT 16-22 | 9,783 | 0.504 | 0.494–0.514 | 0.501 |

`analysis/confirm.csv` has the same pattern for waits of 1, 2 and 3 bars and for "made a new extreme".

**Events where you waited, saw "confirmation", and it still failed:**
- V1 0:13:17 (2022-10-07 00:15 NY, supply OB 1711.40–1717.05)
- V3 7:26:18 (2025-09-17 18:00 NY, supply FVG 3663.84–3679.39)
- V3 4:57:08 (2024-10-08 04:30 NY, supply FVG 2638.66–2640.93)

**Where it worked:**
- V3 6:08:23 (2025-05-16 14:30 NY, demand OB 3181.28–3185.39)

**Confidence:** HIGH. **Risk of overfitting:** LOW.

**Next validation:** the same test with exits tied to the zone (stop beyond the far edge) rather than ±1 ATR.

---

## H11 — A deep arrival predicts zone failure

**Observation:** When the arrival wick passes the zone's midpoint, the zone ends up closed through within 10 bars far more often.

**Conditions:** ARRIVAL; the arrival bar's extreme passes the zone midpoint (`passed_mid == 1`). This is known at the arrival bar's close.

**Prediction:** BRK (a close beyond the far edge within 10 bars) is much higher than for shallower arrivals.

**Evidence:**

| Split | n | BRK | 95% CI | rest | MFE mean/med | MAE mean/med |
|---|---|---|---|---|---|---|
| DISCOVERY | 733 | 0.595 | 0.559–0.630 | 0.215 | 2.56 / 1.93 | 2.62 / 1.82 |
| VALIDATION | 4,033 | 0.648 | 0.633–0.663 | 0.309 | 2.49 / 1.93 | 2.57 / 1.94 |
| EXT 22-26 | 2,198 | 0.650 | 0.630–0.670 | 0.310 | 2.49 / 1.87 | 2.47 / 1.86 |
| EXT 16-22 | 3,518 | 0.572 | 0.556–0.588 | 0.189 | 2.43 / 1.82 | 2.55 / 1.80 |

Placebo bands give 0.60–0.67. **The effect is generic.**

**Important:** it does **not** predict direction. In DISCOVERY, R1 after a deep arrival is about 0.50 and break-continuation fails (H01). The zone gets "used up", and then price is a coin flip again.

**Examples** (deep arrival, then a break):
- V3 6:09:12 (2025-05-20 09:30 NY, supply OB 3240.68–3248.26)
- V3 7:50:38 (2025-10-27 01:45 NY, demand FVG 4074.72–4077.80)
- V1 3:37:13 (2023-04-17 09:45 NY, demand FVG 1991.51–1995.35)

**Counterexamples** (deep, but held):
- V3 6:00:58 (2025-04-24 12:30 NY, demand OB 3319.24–3327.57). Checked by eye: the box reads "★ STATION OB ≥1ATR · S4 · T1".
- V3 8:37:26 (2026-03-20 07:00 NY, supply FVG 4677.23–4684.10)
- V1 2:31:28 (2023-02-14 10:00 NY, supply OB 1861.31–1863.51)

**Possible explanation:** the deeper price already is, the less distance a close needs to travel to get beyond the far edge. This is mostly geometry.

**Confidence:** HIGH. **Risk of overfitting:** LOW.

**Next validation:** make penetration depth continuous and test it on MGC futures. Check whether "deep arrival → stand aside" improves any trading rule *net of what it removes*.

---

## H08 — Thin zones fail

**Observation:** Zones that are short relative to current volatility get closed through far more often.

**Conditions:** ARRIVAL; zone height ≤ 1.3 × 15m ATR at the arrival bar.

**Prediction:** BRK is much higher.

**Evidence:**

| Split | n | BRK | 95% CI | rest |
|---|---|---|---|---|
| DISCOVERY | 1,165 | 0.476 | 0.447–0.504 | 0.204 |
| VALIDATION | 7,485 | 0.548 | 0.536–0.559 | 0.216 |
| EXT 22-26 | 4,087 | 0.558 | 0.543–0.573 | 0.203 |
| EXT 16-22 | 5,512 | 0.464 | 0.451–0.477 | 0.177 |

Placebo bands give 0.50–0.56. **The effect is generic.** R1 is unaffected (about 0.49–0.50).

**Examples** (thin zone, broke):
- V2 0:08:43 (2023-04-25 13:15 NY, supply OB 1992.79–1995.37)
- V3 8:14:13 (2026-01-08 15:00 NY, supply FVG 4456.27–4458.89)
- V3 4:26:55 (2024-07-08 09:45 NY, demand FVG 2367.95–2370.57)

**Counterexamples** (thin zone, held):
- V1 2:05:25 (2023-01-20 10:15 NY, supply OB 1926.62–1929.35)
- V3 5:11:10 (2024-11-19 16:00 NY, demand OB 2628.78–2631.20)
- V3 3:39:56 (2024-05-14 09:45 NY, supply FVG 2354.93–2359.62)

**Possible explanation:** geometry. It matters for this indicator because its minimum zone size is a fixed **2 points**. As gold's 15m ATR rose from 2.2 (2023) to 11.7 (2026), the median zone shrank from 1.7 to 0.74 ATR. The share of thin zones went from 32% to 72%, and the overall failure rate went from 29% to 46%.

**Confidence:** HIGH. **Risk of overfitting:** LOW.

**Next validation:** add an ATR-scaled minimum height to the indicator and re-measure the failure rate by year.

---

## H15 — Large zones rarely fail

**Observation:** Zones taller than 2.4 ATR are seldom closed through within 10 bars.

**Conditions:** ARRIVAL; height > 2.4 ATR.

**Evidence:** BRK is:
- DISCOVERY: 0.118 (n 1,167; rest 0.380)
- VALIDATION: 0.096 (n 2,167; rest 0.494)
- EXT 22-26: 0.089 (n 1,197)
- EXT 16-22: 0.092 (n 7,743)

Placebo bands give 0.07–0.10. **The effect is generic.**

**Prediction value:** this is containment, not direction. R1 is about 0.50 and the edge-trade R is about −0.04, because the stop beyond a wide zone is far away. It is useful for knowing that "price will probably stay inside this band for a while". It is not an entry signal.

**Examples** (large zone, held):
- V1 2:37:08 (2023-02-20 03:00 NY, supply 4H 1846.51–1853.35)
- V3 5:31:02 (2025-01-22 08:45 NY, supply FVG 2756.72–2776.88)

**Counterexamples** (large zone, broke):
- V1 0:47:42 (2022-11-08 10:00 NY, supply OB 1693.78–1707.12)
- V3 7:57:08 (2025-11-14 06:45 NY, demand OB 4098.66–4135.26)

**Confidence:** HIGH. **Risk of overfitting:** LOW.

**Next validation:** test a range-trading rule inside large zones, against placebo large bands.

---

## HS — Do not take an edge trade against the latest 15m structure break

**Observation:** An edge limit trade (entry at the near edge, stop beyond the far edge, 2R target) loses about 0.11–0.17R per trade when the zone points against the direction of the most recent 15m BOS/CHoCH. With the structure it is about 0R.

**Conditions:** ARRIVAL; `struct15_with == 0`. The latest confirmed 15m BOS/CHoCH (STATION2's own 3/3 pivots) points opposite to the zone. This is known before the arrival bar.

**Prediction:** tr2_R < 0 and worse than for trades with the structure.

**Evidence:**

| Split | against: n | tr2_R ± 95% | 2R hit | with: n | tr2_R ± 95% | 2R hit |
|---|---|---|---|---|---|---|
| DISCOVERY | 2,350 | −0.114 ± 0.050 | 0.288 | 1,188 | +0.043 ± 0.074 | 0.360 |
| VALIDATION | 7,365 | −0.147 ± 0.029 | 0.281 | 4,664 | −0.006 ± 0.039 | 0.342 |
| EXT 22-26 | 4,073 | −0.166 ± 0.039 | 0.271 | 2,522 | +0.033 ± 0.054 | 0.356 |
| EXT 16-22 | 12,732 | −0.124 ± 0.020 | 0.268 | 6,197 | +0.038 ± 0.031 | 0.355 |

The placebo shows the same pattern, so the effect is generic.

**Label:** moderate evidence. This condition was in the pre-registered DISCOVERY screen (`screen_single_tr2_R.csv`, q < 0.10). However, I picked it out of the replication table *after* V3 was scored, so it was not in the frozen list. It needs one more untouched dataset before it counts as strong.

**Examples** (against structure, loss):
- V1 0:07:20 (2022-10-03 03:00 NY, supply FVG 1663.97–1666.37, −1.12R)
- V3 6:00:09 (2025-04-22 18:00 NY, demand FVG 3349.51–3351.97, −1.21R)
- V3 2:52:07 (2024-04-01 05:30 NY, demand 4H 2236.01–2249.99, −1.02R)

**Counterexamples** (against structure, win):
- V2 2:48:16 (2023-09-19 01:15 NY, demand 4H 1928.12–1930.91, +1.90R)
- V3 8:17:20 (2026-01-19 10:00 NY, supply FVG 4669.94–4672.20, +1.89R)
- V3 4:30:12 (2024-07-17 12:15 NY, demand 4H 2443.91–2458.57, +0.55R)

**Possible explanation:** short-horizon momentum after a structure break. A limit order placed against fresh momentum is the order that gets filled when momentum continues, which is adverse selection.

**Confidence:** MEDIUM. **Risk of overfitting:** MEDIUM, because of the selection step.

**Next validation:** MGC futures data, 2026-10 onward, untouched. Also 5m.

---

## H06 — NY-AM arrivals fail more often

**Conditions:** ARRIVAL with the hour (New York time) in 08:00–11:59.

**Evidence:** BRK (each against the rest of the same split) is:

| Split | n | BRK | rest | 95% CI |
|---|---|---|---|---|
| DISCOVERY | 1,219 | 0.404 | 0.235 | — |
| VALIDATION | 3,474 | 0.474 | 0.402 | 0.458–0.491 |
| EXT 22-26 | 1,692 | 0.445 | 0.415 | — |
| EXT 16-22 | 5,751 | 0.333 | 0.229 | — |

The effect holds everywhere, but its size changes a lot (+3 to +17 points). Placebo bands show it too (NY-AM BRK 0.38–0.49). The NY-AM R1 is 0.46–0.49.

**Examples** (NY-AM, broke):
- V3 5:56:50 (2025-04-10 09:30 NY, demand OB 3120.41–3124.72)
- V3 6:20:08 (2025-06-23 09:30 NY, supply FVG 3378.97–3385.18)

**Counterexamples** (NY-AM, held):
- V3 3:27:40 (2024-05-02 09:45 NY, demand OB 2267.56–2285.91)
- V3 6:12:50 (2025-05-30 09:45 NY, demand FVG 3273.12–3277.89)

**Possible explanation:** the US data releases and the cash-open volatility push price through any band.

**Confidence:** MEDIUM–HIGH. **Risk of overfitting:** LOW.

**Next validation:** split by news days vs non-news days.

---

## H07 — NY-PM arrivals react more (mixed)

**Conditions:** ARRIVAL with the hour in 12:00–17:59 NY.

**Evidence:** R1 is:

| Split | n | R1 | rest | CI excludes rest? |
|---|---|---|---|---|
| DISCOVERY | 476 | 0.557 | 0.493 | yes |
| VALIDATION | 1,820 | 0.498 | 0.491 | **no** |
| EXT 22-26 | 997 | 0.544 | 0.498 | yes |
| EXT 16-22 | 3,235 | 0.519 | 0.500 | yes |

Against placebo, V3 shows +0.1 points.

**Label:** interesting observation. It failed the pre-registered holdout.

**Confidence:** LOW. **Risk of overfitting:** HIGH.

**Next validation:** if this is real, it should appear on placebo bands too. That would make it a time-of-day effect, not a zone effect. Test it as plain "15m mean reversion after 12:00 NY".

---

## H04 — Long-travel arrivals fail more (failed)

**Conditions:** ARRIVAL; the 10-bar approach path clusters into state E or F, meaning price started about 3.5 ATR or more away.

**Evidence:** BRK is:
- DISCOVERY: 0.401 vs 0.273
- VALIDATION: 0.417 vs 0.423 (**failed**)
- EXT 22-26: 0.440 vs 0.421
- EXT 16-22: 0.286 vs 0.256

**Label:** interesting observation, not reliable.

---

## Rejected hypotheses (frozen, failed in VALIDATION)

| ID | Claim (DISCOVERY) | DISCOVERY | VALIDATION | EXT 16-22 |
|---|---|---|---|---|
| H01 | A close beyond the far edge on the bar after arrival means the zone direction fails (break-continuation) | 0.413 vs 0.495 (n 298) | 0.498 vs 0.498 (n 1,991) | 0.502 vs 0.499 |
| H02 | Flip-retest of a zone older than 8.4 days, with the 4H trend, reacts | 0.590 vs 0.462 (n 571) | 0.490 vs 0.494 (n 1,248) | 0.501 vs 0.519 |
| H03 | Approach state "B" (short push back into an edge price was sitting at) reacts | 0.552 vs 0.488 (n 753) | 0.494 vs 0.491 (n 3,109) | 0.500 vs 0.505 |
| H05 | 4H-pane zone with birth score = 3: the edge trade is profitable | +0.21R vs −0.23R (n 230) | −0.03R vs +0.00R (n 339) | −0.12R vs −0.08R |
| H09 | A hot approach (last 3 bars > 1.14 ATR average range) reacts less | 0.463 vs 0.521 | 0.492 vs 0.492 | 0.504 vs 0.503 |
| H10 | Crowded (≥ 2 same-direction overlaps) and blocked (≤ 0.27 ATR room) means the reaction fails | 0.403 vs 0.510 (n 248) | 0.501 vs 0.490 (n 1,490) | 0.496 vs 0.504 |
| H14 | 4H-pane FVG edge trades lose | −0.27R vs +0.03R | +0.01R vs −0.02R | −0.10R vs −0.08R |

Seeded random examples and counterexamples with video timestamps for every one of these are in `analysis/examples_formatted.txt`.
For example, in H02:
- **Example:** V2 0:36:59 (2023-05-22 00:00 NY, demand OB 1978.32–1985.66, immediate rejection).
- **Counterexample:** V3 3:50:43 (2024-05-23 10:15 NY, supply OB 2325.45–2346.59, weak/adverse).

This is what overfitting looks like. Every one of these had a 95% interval clear of the rest in DISCOVERY, and every one collapsed to the base rate on 3–7× more data.
