# RESEARCH FINDINGS — What price does around STATION2 zones (XAUUSD 15m + 4H, three replay videos)

*Study date: 2026-10-07. Videos: V1 `Screen Recording 2026-10-06 at 9.09.21 PM.mov`, V2 `…2026-10-07 at 12.50.20 AM 1.mov`,
V3 `…2026-10-07 at 7.20.49 AM.mov`. Pipeline: `pipeline/` (stages 01–13). Pre-registration: [PREREGISTRATION.md](PREREGISTRATION.md).
Hypothesis cards: [HYPOTHESES.md](HYPOTHESES.md). Next steps: [VALIDATION_PLAN.md](VALIDATION_PLAN.md).*

---

## 1. Executive summary

**The question:** does the way price interacts with STATION2's zones tell you where price goes next?

**The answer from 27,252 on-video interactions (and 44,841 more off-video):**

- **Direction: no.** Price reaches +1 ATR in the zone's direction before −1 ATR in **49–50%** of cases, in every split (discovery, holdout and external).
  - That is the same rate as for **placebo zones**: the same boxes moved 1.5–3 ATR to a random nearby level.
  - I screened 808 single conditions and 1,510 pairs in discovery. **None** survived a false-discovery correction for direction.
  - All 8 directional hypotheses I froze from discovery fell back to about 50% on the holdout video (V3) and on 2016–2022 data.
- **Zone failure: yes, it is predictable, but for generic reasons.**
  - A thin zone (≤ 1.3 ATR) gets closed through within 10 bars **~55%** of the time.
  - A zone whose arrival wick passes the midpoint fails **~65%** of the time.
  - A large zone (> 2.4 ATR) fails only **~9%** of the time.
  - These held in every split, **but placebo bands do exactly the same.** They are facts about price bands and volatility, not about STATION2.
- **Rejection candles and "waiting for confirmation" carry no information.** Measured from the moment you could actually act (the close), R1 is 49–50% after a close back outside the zone. It is the same after two bars of "confirmation". Candles *look* predictive only when the measurement accidentally includes the candle itself.
- **The only stable filter is generic: don't fade fresh 15m structure.**
  - Edge-limit trades against the latest 15m BOS/CHoCH lose **−0.11R to −0.17R** per trade, in all four datasets.
  - With the structure they make about **0R**.
  - Stacking the filters (wide zone + with structure + not NY-AM) gives **+0.02R to +0.09R** per trade. Every confidence interval includes zero, and placebo bands score the same.
- **The indicator drifted with volatility.** Its fixed 2-point minimum zone size meant that as gold's 15m ATR rose from 2.2 (2023) to 11.7 (2026):
  - the median zone shrank from 1.7 ATR to 0.74 ATR;
  - the share of thin zones went from 32% to 72%;
  - the break rate rose from 29% to 46%.

**Bottom line:** I found no information in these zone interactions that predicts direction better than chance. There are honest **no-trade filters**, but they would work on any price band, and they reduce losses rather than create an edge. Nothing here justifies live trading.

---

## 2. The dataset extracted from the videos

### Video properties (ffprobe)

| | V1 | V2 | V3 |
|---|---|---|---|
| Duration | 3 h 38 m (13,107 s) | 3 h 25 m (12,308 s) | 10 h 08 m (36,475 s) |
| Size | 15.0 GB | 13.5 GB | 43.8 GB |
| Video | H.264, 2880×1800, VFR (~57 fps avg) | same | same |
| Keyframes (≈ 1/s) | 13,083 | 12,311 | 36,512 |

### Ingestion

- Only keyframes were decoded (~1 per second). TradingView replay changes at most once per replay step, so this keeps every step.
- Per keyframe I saved:
  - a native-resolution text band containing both pane headers and the time axes;
  - a half-resolution frame (1440×900).
- Apple Vision OCR then read both panes' **O/H/L/C header**, the **crosshair date labels**, the **price axes** and the **live price (SELL box)**.

### Layout

- **Left pane:** OANDA:XAUUSD **15m**. **Right pane:** OANDA:XAUUSD **4h**, log scale. Both run STATION2 (`STA-2.1`) and QUANTUM FLOW CORE v1.0.
- The chart time axis is New York time.
- The replay step was 15m, at 0.5×, 1× and 3× speed.

### Dating every frame

- The header shows the open of the newest replay bar. In V1 the cursor sat still on the chart, so the header lagged a steady **23 bars** behind the live price.
- I matched the sequence of header opens to an independent 15m feed with a Viterbi alignment.
- I then resolved the *newest* bar exactly: it is the bar whose close equals the live SELL price (exact 3-decimal match).
- Results:
  - **96.1% / 99.0% / 86.5%** of frames dated (V1/V2/V3);
  - median |video open − feed open| = **0.16–0.20 pts**;
  - the newest bar is resolved from the live price on 82–95% of frames.
- About 13% of V3 frames could not be dated (mostly very fast replay or menu screens). They are excluded, not guessed.

### What was replayed

| Video | Replay runs | 15m bars revealed | Dates replayed |
|---|---|---|---|
| V1 | 76 | 12,658 | 2022-09-28 → 2023-04-18 |
| V2 | 8 | 12,152 | 2023-04-18 → 2023-10-20 |
| V3 | 291 | 50,925 | 2023-10-22 → 2026-04-22 |

- The videos do not overlap in time; only 26 bars appear in two videos. That made V3 a clean, later holdout.

### Bars

- The screen shows candles, but per-bar highs and lows are only readable when hovered. I therefore used an **independent 1-minute feed**, checked against the video:
  - Dukascopy for every day downloaded before the final build. That covers 2023-02-20 → Dec 2023 and parts of Jul–Oct 2022 and Jan–Apr 2024. 6,413 of the 27,252 events fall on Dukascopy days.
  - HistData elsewhere.
  - The per-event column `data_source` says which feed was used.
- Where both exist they agree exactly (median 0.00). The video opens agree with the feed to a median 0.16–0.20 pts.
- HistData was found to be missing **~28% of minutes in Mar–Jul 2023** (V2's period). That is why Dukascopy was downloaded for it.
- 4H bars follow the **17:00 New York session grid**. This was chosen by matching the video's 4H header: median error 0.22 vs ≥ 0.73 for the fixed UTC grids.

### Zones

- STATION2's zone logic (FVG, OB, the 4H FVG import, dedupe, 60-zone cap, lifecycle, score) comes from the line-for-line Python port (`pipeline/zone_engine.py`).
- It runs on the 15m chart (with the replay-time 4H import) and on the 4H chart.

### Zone fidelity check (`data/zone_visual_check.csv`)

- On 374 sampled frames (~125 per video) I fitted price to pixels on each pane's axis (OCR, log scale, RANSAC).
- For each zone the engine says is live on screen, I tested for a drawn horizontal box border at the predicted top and bottom edge, compared with chance at a random 6–20 px offset.

| | 4H pane (live zones) | 15m pane (live zones) |
|---|---|---|
| V1 | 69% hit vs 15% chance | 59% vs 19% |
| V2 | 65% vs 14% | **24% vs 19% (weak)** |
| V3 | 73% vs 18% | 53% vs 20% |

- Spot-checked by eye: V3 6:00:58 shows "★ STATION OB ≥1ATR · S4 · T1" exactly at the engine's 3319.24–3327.57.
- **AMBIGUOUS:** the engine's zones match the drawn boxes well on the 4H pane and partially on the 15m pane, but not one-to-one. There are three reasons:
  - feed differences in highs and lows (Dukascopy/HistData vs OANDA);
  - heavy overlap with QUANTUM FLOW CORE's own boxes;
  - TradingView rendering.
- V2's 15m pane is the weakest. Every event carries `zone_edge_seen_rate` and an `AMBIGUOUS` note:
  - 105 events have zones under 0.15 ATR;
  - 2,978 events touch within 0.05 ATR of the edge, where a feed difference could flip the touch.

### Not studied

- QUANTUM FLOW CORE's own boxes and labels ("FVG CE✓", BOS/CHoCH tags). The study is about STATION2's zones.
- Volume: the chart showed tick volume, which was not recorded per bar.

---

## 3. Zones observed

| | 15m pane | 4H pane | Total |
|---|---|---|---|
| Zones the engine created over the replayed span (May 2022 – Sep 2026 incl. warm-up) | 9,674 (FVG 5,119 · OB 3,811 · imported 4H FVG 744) | 1,469 (FVG 1,017 · OB 452) | 11,143 |
| Zones with ≥ 1 interaction revealed on screen | 6,597 | 843 | **7,440** |
| Zones born on a bar that was on screen | 6,658 | 998 | — |

Per-zone geometry, birth time, lifecycle and the full interaction list are in **[ZONE_EVENTS.json](ZONE_EVENTS.json)**.

---

## 4. Interactions observed

**27,252 interactions** whose arrival bar was revealed on screen:

| Split | Video | ARRIVAL (first approach from the defending side) | FLIP (retest from the broken side) | Total |
|---|---|---|---|---|
| DISCOVERY | V1 | 1,979 | 1,359 | 3,338 |
| DISCOVERY | V2 | 1,559 | 1,095 | 2,654 |
| VALIDATION | V3 | 12,029 | 9,231 | 21,260 |

Off-video comparison sets:
- 11,669 interactions on non-replayed bars from 2022–2026;
- 33,172 from 2016–2022 (`data/EXTERNAL_EVENTS.csv` and the 2016–22 pipeline run).

Every row of **[EVENT_DATASET.csv](EVENT_DATASET.csv)** has 120+ measured variables and outcomes, plus the video file and h:mm:ss at which the arrival bar appears.

---

## 5. Major recurring reaction types

Archetypes were defined *before* outcomes were looked at (`07_events.py`). The outcome window is 20 bars from the arrival close.

| Archetype | Definition | DISCOVERY | VALIDATION |
|---|---|---|---|
| IMMEDIATE_REJECTION | +1 ATR within 3 bars, no close beyond the far edge | 27.9% | 25.4% |
| DELAYED_REACTION | +1 ATR in bars 4–20, no break | 13.8% | 12.7% |
| BREAK_THROUGH | close beyond the far edge within 10 bars, no reclaim | 21.0% | 25.7% |
| FALSE_BREAK_RECLAIM | breaks, then closes back beyond the near edge within 10 bars | 8.1% | 16.7% |
| WEAK_OR_ADVERSE | −1 ATR first, no break | 26.9% | 18.4% |
| NO_REACTION_CHOP | neither ±1 ATR in 20 bars | 2.4% | 1.1% |

The mix shifted toward breaks and false breaks in V3, which had higher volatility and thinner zones (§12). **No pre-arrival variable predicted which archetype would occur** beyond the generic thin/wide geometry.

---

## 6. Newly discovered variables (and what they turned out to be worth)

| Variable | What it is | Worth |
|---|---|---|
| `height_atr` | zone height ÷ 15m ATR at arrival | **Strongest failure predictor** (break rate 55% / 33% / 9% by tertile in V3). No directional value. |
| `pen_frac`, `passed_mid` | how deep the arrival wick went, as a fraction of the zone | Strong failure predictor (break 21% → 59%). No directional value. |
| `struct15_with` | the latest confirmed 15m BOS/CHoCH (STATION2's own 3/3 pivots) points the zone's way | The only replicated pre-arrival trade filter (−0.15R against vs −0.01R with, in V3) |
| `zone_age`, `prior_arrivals` | bars since availability; earlier arrivals at the same zone | Older and more-touched zones break *less* (V3: 47% → 34%; 47% → 31%). Survivorship: weak zones are already dead. No direction. |
| `n_overlap_same` | other live same-direction zones overlapping this one | More overlap → fewer breaks (51% → 30%). Stacked zones act like one wide zone. |
| Live-price lag (V1) | header vs newest bar: 23 bars | A data-integrity variable. Without it every V1 timestamp would be 5¾ hours wrong. |
| Approach state A–F | k-means on the 10-bar oriented path | Separates "came from far" from "was already there". Did not replicate for direction (§11). |

---

## 7. Top candidate predictive behaviours

There is **no directional behaviour I can recommend.** The table shows what came closest and what happened to it:

| Behaviour | Discovery | Holdout V3 | Verdict |
|---|---|---|---|
| Flip-retest of an old zone (> 8.4 days) with the 4H trend | R1 0.590 (n 571) | 0.490 (n 1,248) | failed |
| Short re-entry approach (state B) | 0.552 | 0.494 | failed |
| NY-PM arrivals | 0.557 | 0.498 | failed in V3; +2 to +5 pts in both external sets → re-test |
| 4H-pane zone with birth score = 3, edge trade | +0.21R | −0.03R | failed |
| Wide zone + with 15m structure + not NY-AM, edge trade | +0.03R | +0.02R ± 0.07 | not different from 0; placebo also +0.03R |

---

## 8. Top zone-failure behaviours (validated, generic)

| Condition | Break within 10 bars (V3) | Rest | Placebo |
|---|---|---|---|
| Arrival wick passes the zone midpoint | **64.8%** | 30.9% | 63.9% |
| Arrival bar closes beyond the far edge | 87% | — | similar |
| Zone height ≤ 1.3 ATR | **54.8%** | 21.6% | 55.3% |
| NY-AM (08–12 NY) | 47.4% | 40.2% | 44.2% |
| Fresh zone (first arrival), not overlapping others | ~47–51% | — | — |
| Zone height > 2.4 ATR | **9.6%** | 49.4% | 8.8% |

A broken zone does **not** predict follow-through. The "break-continuation" hypothesis (H01) was 0.498 in V3, so after a break price is a coin flip again.

---

## 9. No-trade conditions

Ranked by how reliably they hold. Each one holds in discovery, V3 and both external sets.

1. **The zone is thinner than 1.3 × 15m ATR.**
   - The edge trade averages −0.14R (V3), −0.13R (EXT 22-26) and −0.12R (EXT 16-22).
   - Break rate ~55%.
   - In 2025–26 this rule excludes ~70% of all STATION2 zones.
2. **The latest 15m BOS/CHoCH points against the zone.**
   - The edge trade averages −0.11 to −0.17R and reaches 2R only 27–29% of the time.
3. **After the arrival bar: the wick passed the midpoint, or the bar closed beyond the far edge.**
   - Treat the zone as consumed (break 65–87%).
   - Do not *enter* on this information afterwards; it does not predict the next direction either.
4. **NY-AM arrivals.** The break rate is higher by 3–17 points. This is a weaker filter.
5. **Don't use these as entry triggers:**
   - a rejection candle;
   - two bars of "confirmation";
   - "first touch";
   - "★ STATION" status (score ≥ 3);
   - nesting inside a 4H zone;
   - 4H trend alignment.
   
   None of them changed R1 by more than 1.2 points in V3.

---

## 10. Cross-timeframe findings (15m × 4H)

Numbers are R1 in V3 for ARRIVAL events, unless noted.

| Condition | With | Against / no | Note |
|---|---|---|---|
| 4H EMA100 trend agrees with the zone | 0.487 | 0.499 | discovery +3 pts; gone in V3 |
| 4H BOS/CHoCH direction agrees | 0.496 | 0.485 | — |
| 15m zone nested inside a same-direction 4H zone | 0.488 | 0.493 | discovery said nested was *worse*; V3 says the same |
| 15m zone overlaps an opposite 4H zone (conflict) | 0.487 | 0.496 | conflict lowers break rate 45% → 39% (more zones = wider band) |
| 4H-pane zones vs 15m-pane zones | 0.498 | 0.491 | 4H zones break far less (23% vs 46%) because they are taller in 15m ATR units |

The 4H context changes **how often a zone breaks**, through geometry. It does not change **which way price goes**.

---

## 11. Sequence-pattern findings

**Approach states.** k-means (k=6) on the oriented 10-bar close path plus the arrival extreme, fitted on discovery and applied unchanged to V3:

| State | Shape (closes, in ATR from the near edge, 10 bars → arrival) | R1 DISC | R1 VAL | Break DISC | Break VAL |
|---|---|---|---|---|---|
| A | was 2 ATR *beyond* the zone, came back through it, then re-touched | 0.507 | 0.499 | 0.26 | 0.45 |
| B | sat at the edge, pushed out < 1 ATR, came back | **0.552** | 0.494 | 0.26 | 0.42 |
| C | ~1 ATR away, drifted in | 0.479 | 0.486 | 0.27 | 0.42 |
| D | ~2.5 ATR away | 0.514 | 0.493 | 0.29 | 0.42 |
| E | ~3.7 ATR away | 0.449 | 0.503 | **0.40** | 0.42 |
| F | ~5.7 ATR away (impulsive run) | 0.496 | 0.458 | **0.43** | 0.42 |

Discovery suggested that state B reacts and E/F break. **Neither replicated.**

**Confirmation sequences** ("approach → touch → close → next bar"):
- closed back outside by bar 1 / 2 / 3;
- no far-edge close;
- a new extreme on the next bar;
- a close beyond the far edge, then a reclaim.

From the moment each sequence is complete, R1 is 0.47–0.51 in every split (`analysis/confirm.csv`, H13).

---

## 12. Surprising findings

1. **Placebo zones behave the same as real zones.**
   - This is the main result. Even "first touch", "★ STATION", OB vs FVG and the 4H pane don't separate real from placebo in V3 (all |z| < 1).
   - The discovery data had one cell at z = 3.4 (NY-PM), which vanished.
2. **Rejection candles are a measurement illusion.**
   - Measured from entry at the edge, a close back outside shows +0.27R and a close beyond the far edge −1.07R (V3). That looks like a huge effect.
   - But that close is the first part of the trade's own path, known only after you are already in.
   - Measured from the close (when you could act on it), R1 is 0.492 vs 0.492.
   - Many indicator "confirmations" probably have this same look-ahead.
3. **The indicator's zones got worse automatically as gold got more volatile.** The 2-point absolute minimum produced:

| Year | 15m ATR | Median zone height | Thin-zone share | Break rate | R1 |
|---|---|---|---|---|---|
| 2022 | 2.4 | 1.68 ATR | 32% | 31% | 0.490 |
| 2023 | 2.2 | 1.70 | 34% | 29% | 0.505 |
| 2024 | 3.3 | 1.24 | 53% | 38% | 0.491 |
| 2025 | 5.8 | 0.93 | 68% | 45% | 0.490 |
| 2026 | 11.7 | 0.74 | 72% | 46% | 0.497 |

4. **Worn zones break less, not more.** "Second touch is worse" is false here. Zones on their 3rd+ arrival break 31% vs 47% on the first, because survivors are the wide or stacked ones. Direction is the same (0.474–0.504).
5. **Overfitting at scale.**
   - All 8 directional hypotheses had 95% intervals clear of the base in discovery (n = 230–1,146). All 8 returned to the base on 3–7× more data.
   - Of the 805 direction conditions screened in discovery, **52%** kept the same sign in V3, which is a coin flip.
   - Failure-related conditions kept their sign 98% of the time.
6. **The V1 header was a lie.**
   - With the mouse resting on the chart, the header showed a bar 23 bars behind the live one for the whole video.
   - Any study that read candle values from headers or tooltips without checking the live price would be 5¾ hours off.

---

## 13. Top 10 hypotheses, ranked by evidence

See **[HYPOTHESES.md](HYPOTHESES.md)** for the full cards: conditions, prediction, n, success rate, MFE/MAE, examples, counterexamples, explanation, confidence, overfitting risk and next test.

1. HN-A zones = placebo for direction (strong, negative)
2. H12 rejection candle uninformative (strong, null)
3. H13 waiting / confirmation uninformative (strong, null)
4. H11 deep arrival → zone failure (strong, generic)
5. H08 thin zone → failure (strong, generic)
6. H15 large zone → rarely fails (strong, generic)
7. HS against-structure edge trade loses (moderate, generic, selected post-validation)
8. H06 NY-AM → more failure (strong, generic, variable size)
9. H07 NY-PM → more reaction (interesting; failed V3)
10. H04 long travel → more failure (interesting; failed V3)

Rejected: H01, H02, H03, H05, H09, H10, H14.

---

## 14. Counterexamples for every major hypothesis

Every card in HYPOTHESES.md lists seeded-random counterexamples with video timestamps. A sample:

- **H11 (deep arrival → break), held instead:**
  - V3 6:00:58 (2025-04-24 12:30 NY, demand OB 3319.24–3327.57, immediate rejection, +5.3 ATR);
  - V1 2:31:28 (2023-02-14 10:00 NY);
  - V3 8:37:26 (2026-03-20 07:00 NY).
- **H08 (thin → break), held instead:**
  - V1 2:05:25 (2023-01-20 10:15 NY);
  - V3 5:11:10 (2024-11-19 16:00 NY).
- **HS (against structure → loss), won instead:**
  - V2 2:48:16 (2023-09-19 01:15 NY, +1.90R);
  - V3 8:17:20 (2026-01-19 10:00 NY, +1.89R).
- **H12 (rejection uninformative):**
  - worked: V3 5:56:44 (2025-04-10 05:00 NY);
  - failed: V1 2:05:28 (2023-01-20 11:00 NY).
- **Rejected H02 (old flip + 4H trend):**
  - looked right: V2 0:36:59;
  - failed: V3 3:50:43, V3 4:23:25.

All 15 hypotheses: `analysis/examples_formatted.txt` and `analysis/examples.csv`.

---

## 15. Proposed trading decision tree

This tree is built only from validated evidence. It uses information available **before** the arrival bar, except the last check, which uses the arrival bar's close. Confidence = the measured probability that a 2R edge trade wins, ×100, averaged over V3 and both external sets.

```
Price is approaching a STATION2 zone (15m or 4H pane)
│
├─ Zone height ≤ 1.3 × ATR15 ? ───────────────► IGNORE ZONE   (2R hit 31%, −0.13R/trade, break 55%)
│
├─ Latest 15m BOS/CHoCH points against the zone ? ─► IGNORE ZONE   (2R hit 26–28%, −0.05 to −0.09R)
│
├─ Hour 08:00–11:59 New York ? ─────────────────► WAIT          (small n; break risk higher; no proven edge)
│
└─ Otherwise (wide zone, with structure, not NY-AM)
     │   2R hit 32–35%, expectancy +0.02 to +0.09R, every 95% CI includes 0, placebo bands score the same
     │
     ├─ demand zone ► LONG at near edge, stop 0.1 ATR beyond far edge, target 2R    confidence 33
     ├─ supply zone ► SHORT (mirror)                                                 confidence 33
     │
     └─ After the arrival bar closes:
          wick passed the midpoint OR closed beyond the far edge ►  zone likely consumed (65–87%):
          do not add, do not re-enter. (Exit-or-hold makes no difference to expectancy: R1 = 50%.)
```

Why each node exists: node 1 is H08/H15, node 2 is HS, node 3 is H06, and the final check is H11.

**Honest status:** the LONG/SHORT leaf is **not** an edge. It is "least bad". At 0.30 pt costs it is about break-even, and at realistic MGC slippage it is negative. The useful part of the tree is the two IGNORE nodes.

---

## 16. Features that should be programmed into the indicator

1. **An ATR-scaled minimum zone height** (e.g. ≥ 1.3 × ATR14) instead of the fixed 2.0 pts. Grey out or hide thinner zones.
2. **A "consumed" warning** when a wick passes the midpoint, not only when it reaches the far edge. Measured break rate 65%.
3. **A 15m structure-direction badge** on each zone (with / against the last BOS/CHoCH). Against = red "no fade".
4. **The zone height in ATR units printed on the label**, e.g. "1.8 ATR".
5. **An NY-AM warning shade** (08:00–12:00 NY).
6. **Remove or label as display-only:** "★ STATION" scoring, first-touch emphasis, 4H nesting. None changed outcomes out of sample.
7. **Export hooks.** Plot top/bottom/born/state as hidden plots so zones can be exported and checked exactly (VALIDATION_PLAN H-D).

---

## 17. Features worth backtesting further

- An ATR-scaled minimum height (as above): does it change R1 vs placebo? Expected no; break rate should fall.
- **HS as a general filter** on *any* limit entry (not only zones). It is likely a "don't fade a fresh BOS" effect.
- **Exit management:** close an existing position when price makes a deep arrival into an *opposing* zone (H11).
- **NY-PM** mean reversion (H07). It failed V3 but held in both external sets; test it as a pure time-of-day effect, with placebo.
- **Containment inside wide zones** (H15): range trades inside > 2.4-ATR zones vs placebo bands.

---

## 18. Features that appear useless (for direction)

Each changed R1 by less than 3 points across its V3 tertiles or levels (`analysis/validation_feature_effects.csv`):
- approach velocity, travel distance, approach bar count;
- acceleration ratio, compression, consecutive candles toward the zone, momentum over 10 bars;
- largest candle in the approach, body/wick ratios;
- displacement FVG into or away from the zone;
- arrival-candle range, body fraction, direction, close location (CLV);
- penetration depth;
- zone age, touch count, prior penetration;
- STATION score at birth, zone kind (FVG/OB/4H), 15m or 4H pane;
- 15m and 4H EMA trend, 4H structure;
- nesting, conflict, room to the next opposing zone, stacked support behind;
- ATR regime, hour.

The one apparent exception, "bar opened inside the zone" (R1 0.409), rests on **n = 44** and shows the same in placebo: noise.

---

## 19. Exact video timestamps for important examples

Format: video h:mm:ss (when the arrival bar first appears) → chart time (New York).

| What | Where |
|---|---|
| V1 header-lag artefact (header 23 bars behind the live price) | V1 0:50:00 (frame f_003000): header 1,706.365 vs SELL 1,709.275 |
| Engine zone drawn exactly on the chart (verified by eye) | V3 ≈ 6:01:01 → 2025-04-24 ~14:15 NY: "★ STATION OB ≥1ATR · S4 · T1" at 3,319–3,327.5 |
| Deep arrival → break (H11) | V3 6:09:12 → 2025-05-20 09:30 (supply OB 3240.68–3248.26); V3 7:50:38 → 2025-10-27 01:45 |
| Thin zone → break (H08) | V3 8:14:13 → 2026-01-08 15:00 (supply FVG 4456.27–4458.89, 2.6 pts tall at ATR 7.4 → 0.35 ATR) |
| Large zone held (H15) | V3 5:31:02 → 2025-01-22 08:45 (supply FVG 2756.72–2776.88) |
| Against-structure loss (HS) | V3 6:00:09 → 2025-04-22 18:00 (demand FVG 3349.51–3351.97, −1.21R) |
| Rejection candle that failed (H12) | V1 2:05:28 → 2023-01-20 11:00; V3 4:23:55 → 2024-06-30 22:30 |
| Rejection candle that worked (H12) | V3 5:56:44 → 2025-04-10 05:00; V3 8:05:37 → 2025-12-10 20:00 |
| Discovery "edge" that failed out of sample (H02) | V2 0:36:59 → 2023-05-22 00:00 (worked); V3 3:50:43 → 2024-05-23 10:15 (failed) |

At 3× replay, the bar appears 1–3 s before the listed time.

---

## 20. Recommended next experiment

**Export STATION2's own boxes from TradingView and re-run the placebo test** (VALIDATION_PLAN H-D).

- It is the one remaining doubt that could overturn the main result: the 15m-pane zones match the drawn boxes only partially.
- It costs one Pine edit plus a CSV export.
- If the indicator's exact boxes *also* equal placebo, the zone side of STATION2 is settled. Further work should go to exits, sizing, or a different information source (order flow, volume, news timing), not more zone variants.

---

### Files

| File | Contents |
|---|---|
| [EVENT_DATASET.csv](EVENT_DATASET.csv) | 27,252 on-video interactions × 120+ variables, outcomes, split, video + timestamp, AMBIGUOUS notes |
| [ZONE_EVENTS.json](ZONE_EVENTS.json) | 7,440 zones: geometry, birth, lifecycle, interactions in order |
| [HYPOTHESES.md](HYPOTHESES.md) | Hypothesis cards (format as requested) |
| [VALIDATION_PLAN.md](VALIDATION_PLAN.md) | Unseen-data tests with fixed pass/fail criteria |
| [PREREGISTRATION.md](PREREGISTRATION.md) | Splits and outcome definitions, written before outcomes were computed |
| `analysis/` | base rates, screens (R1/BRK/tr2_R), pairs, trees, clusters, confirm, frozen cut-points, replication, hypotheses per split, decision-tree leaves, examples |
| `data/` | replay runs, 4H grid evidence, zone visual check, external events |
| `pipeline/` | every stage, rerunnable (`01_extract.sh` … `13_examples.py`) |

**Not kept:** the 62k extracted frames and OCR files (~20 GB). They were in session scratch space and are regenerable with stages 01–05b in about 3 h.

### Limitations

- **Bars:** they come from an independent feed (Dukascopy/HistData), not from candle pixels. Opens match the video to 0.16–0.20 pts, but highs and lows may differ more on spikes.
- **Zones:** they come from the Python port. Agreement with drawn boxes is good on the 4H pane and partial on the 15m pane (§2).
- **Undated frames:** 13% of V3 frames are undated, and those bars are excluded.
- **Costs:** a flat 0.30 pt.
- **Scope:** one instrument and one indicator version (STA-2.1) with default parameters, as the source has them.

---

## Addendum (owner's follow-up): do 4H candles stop at box tops, midlines and bottoms?

**The claim:** price moves box to box on the 4H chart, and each 4H candle's high or low stops at a box's top, midline or bottom (OB, FVG, breaker, IFVG).

**The test:** `pipeline/14_h4_stops.py` → `analysis/h4_extremes_at_box_levels.csv`.
- For every on-video 4H bar (1,615 in V1+V2 and 3,497 in V3), I asked whether its high or low lands within 0.05 / 0.10 / 0.20 × ATR4 of a level of any box on the chart when the bar opened.
- The boxes include consumed and inverted boxes.
- I compared that with 30 placebo copies of the same boxes, each moved 1–3 ATR4 at random.

**Results (4H-pane boxes):**

| Split | Real boxes (within 0.1 ATR4) | Placebo boxes | Ratio |
|---|---|---|---|
| V1+V2 | **88.6%** | 85.5% | 1.04 |
| V3 | **80.3%** | 80.3% | 1.00 |

- Taken separately, tops, midlines and bottoms each give ratios of 1.00–1.07.

**15m-pane boxes:**
- In V3 the ratio is 1.05–1.15 at the 0.05–0.1 ATR4 tolerance.
- But real boxes have more levels within reach of each candle (15.6 vs 13.0), because zones are made from recent price. Part of that lift is density, not stopping power.

**Why it looks true on the chart:** each 4H candle has about 7–8 boxes (about 23 lines) within its reach. With that many lines, a candle extreme lands on one of them about 80–89% of the time whether the boxes are real or random. The eye sees "it stopped exactly at the box" every time, and doesn't see that random boxes get the same hit.

## Addendum 2: the owner's 4H "box staircase" rule (written by watching the videos)

**Watched:**
- V3 uptrend, 2024-02-28 → 03-20 (2,030 → 2,186). Pullbacks landed on the tops of the green boxes price had left, then stepped up again.
- V2 downtrend, 2023-05-04 → 06-02 (2,070 → 1,950). The mirror image.

**Rule:** `pipeline/15_owner_rule.py`, bull side; the bear side is the mirror.
1. 4H EMA100 trend up and the last 4H BOS/CHoCH up.
2. Any 4H box (OB/FVG/breaker/IFVG).
3. Escape: a 4H close above the top, then price runs at least 1 ATR4 above it. The escape high is recorded.
4. Entry setup: the first 15m touch of the top.
5. Entry: (A) at the top on the touch, or (B) at the first 15m close back above the top within 8 bars.
6. Stop and target: stop at the box bottom − 0.1 ATR15; target the escape high; 2-day limit; 0.30 pt cost.

**Results, with the trend filter, version B:**

| Data | Trades | Win rate | Avg R/trade (95%) | Random boxes, same rule |
|---|---|---|---|---|
| V1+V2 | 289 | 38.8% | +0.11 ± 0.17 | +0.08 |
| V3 | 754 | 30.0% | −0.07 ± 0.11 | −0.13 |
| Non-replayed 2022–26 | 290 | 28.3% | +0.08 ± 0.20 | +0.19 |
| 2016–2022 | 1,827 | 29.9% | **−0.13 ± 0.06** | −0.10 |

**Verdict:**
- The pattern is real on the screen: price does leave boxes and come back to them. But trading it loses on the largest sample.
- Random boxes give the same result, so the box is not what drives it.
- The 4H trend filter helps (without it, results are worse) on real and random boxes alike.
- Files: `analysis/owner_4h_staircase_rule_*.csv`.

**Examples to watch (version B, with trend):**
- Wins:
  - V3 2:47:53 (2024-03-26 11:00 NY, bull OB 2165.07–2176.11, +1.86R)
  - V3 5:45:11 (2025-03-06 04:45 NY, bull OB 2881.65–2893.62, +2.74R)
- Losses:
  - V3 1:14:32 (2023-12-29 08:45 NY, bull FVG 2057.96–2061.28)
  - V3 7:44:56 (2025-10-08 18:00 NY, bull FVG 3999.05–4021.05)
  - V2 3:08:47 (2023-10-06 10:00 NY, bear OB 1825.56–1829.11)

## Addendum 3: the owner's explanation video (`Screen Recording 2026-10-07 at 8.12.09 PM.mov`, 15 min)

The owner narrates a replay from about 10 to 28 Sep 2026. The transcript is in `data/owner_video_2026-10-07_8.12PM/transcript.txt`.

**The thesis in the owner's words:**
- Price moves box to box (IFVG, FVG/CE, OB, breaker).
- Each 4H candle tends to finish its body (open/close, "don't think highs and lows", 5:17) at the top, centre or bottom of a box.
- Previous days' and London/NY highs and lows act the same way (7:56–8:47).
- One still has to "figure out the bias properly to enter" (10:27).

**Tests:** 2022–2026, 6,509–6,809 4H bars, 30 random draws each.

| Claim | Real | Random | Ratio | Verdict |
|---|---|---|---|---|
| 4H close within 0.1 ATR4 of a 4H **box top** | 34.8% | 32.5% (boxes shifted 1–3 ATR4) | 1.07 | small, beats all 30 draws |
| … of a box **midline / bottom** | 32.2% / 32.5% | 32.4% / 32.2% | ≈1.0 | no effect |
| 4H close within 0.1 ATR4 of the previous 3 days' **day/London/NY high or low** | 28.7% | 23.2% (levels shifted) | 1.24 | looked strong… |
| … the same, vs **random prices traded in the same 3 days** | 28.7% | 27.0% | 1.06 | mostly "price returns to recent prices" |
| … at 0.05 ATR4, vs traded prices | 15.8% | 16.5% | 0.96 | none |

**Reading:**
- The chart behaviour the owner describes is real: candles do finish near box edges and old highs and lows.
- But nearly as many finish near random levels and random recently traded prices, because the chart is dense with levels and price revisits where it has been.
- Box *tops* show a small extra pull (+2.3 points). That has not yet been checked against the harder traded-price control.
- None of this gives the **bias** (direction), which the owner names as the missing piece, and which every direction test here put at 50/50.

Files:
- `analysis/h4_closes_at_box_levels.csv`
- `analysis/h4_session_levels.csv`
- `analysis/h4_session_levels_vs_traded_prices.csv`
- `pipeline/16_h4_close_at_box.py`
- `pipeline/17_session_levels.py`

## Addendum 4: lower-timeframe (5m / 3m) confirmation for the bias at 4H zones

This was the owner's next idea. `pipeline/18_ltf_confirm.py` was pre-registered (rules written before any result was seen). Results are in `analysis/ltf_confirmation_5m_3m.csv`.

**Setup:**
- Every 4H-pane zone touch (arrival or flip retest), 2022–2026.
- Watch 3 hours of 5m or 3m bars.
- Four confirmations:
  - C1: CHoCH (close beyond the last LTF swing)
  - C2: sweep of the last hour's extreme, then a reclaim within 3 bars
  - C3: displacement FVG (middle bar ≥ 1.5× LTF ATR)
  - C4: engulfing close back outside the zone
- Entry at the confirmation close; stop beyond the lowest point since the touch; 1R and 2R targets; 0.30 pt cost.
- Run with and without the 4H trend filter, and on placebo zones.

**Trades:** about 60,000 real and 60,000 placebo across both timeframes.

| Confirmation | Median stop (ATR15) | 2R win rate, real / placebo (break-even 33.3%) | 1R win rate, real / placebo | R per trade, real / placebo |
|---|---|---|---|---|
| 5m C1 CHoCH | 1.67 | 33.5% / 32.8% | 49.9% / 49.0% | −0.03 / −0.06 |
| 5m C2 sweep+reclaim | 0.57 | 28.8% / 28.4% | 42.4% / 41.7% | −0.32 / −0.34 |
| 5m C3 displacement FVG | 1.92 | 33.0% / 32.3% | 50.3% / 48.9% | −0.04 / −0.07 |
| 5m C4 engulfing | 1.19 | 33.5% / 32.7% | 50.1% / 49.5% | −0.07 / −0.10 |
| 3m C1 / C2 / C3 / C4 | — | 33.1 / 25.9 / 33.9 / 33.7% | 48.9 / 38.8 / 51.1 / 50.3% | −0.07 / −0.44 / −0.04 / −0.08 |

**Findings:**
- **The 4H trend filter does not change the picture.** For example, 5m C1 with the trend: V1+V2 +0.04R, V3 −0.08R, off-video +0.02R, each with a CI of about ±0.06–0.09.
- **Verdict:** every lower-timeframe confirmation gives a coin-flip 1R win rate and a break-even 2R win rate before costs, so it loses after costs. Real zones beat placebo zones by only 0–1.5 points of win rate.
- **The sweep-and-reclaim is genuinely worse than a coin flip.** Its stop sits just under the sweep, and price revisits the sweep low most of the time.

**C5: double bottom / double top at the zone.** Added at the owner's request, with the rule fixed before the result was seen.

| | n | 1R win | 2R win (break-even 33.3%) | R/trade ± 95% |
|---|---|---|---|---|
| 5m, real zones | 3,021 | 50.9% | 32.9% | −0.05 ± 0.05 |
| 5m, placebo zones | 3,039 | 48.6% | 32.7% | −0.07 ± 0.05 |
| 3m, real zones | 5,623 | 49.8% | 33.1% | −0.06 ± 0.04 |
| 3m, placebo zones | 5,626 | 49.8% | 32.9% | −0.07 ± 0.04 |

**With the 4H trend (5m):** V1+V2 +0.12R (n 353), V3 −0.09R (n 866), off-video +0.01R (n 464). This is the same "works in the first videos, fails later" pattern seen throughout.

---
## Addendum 2026-10-08 — the owner's live trade ("1H sweep-and-reject"), tested forward
Source: recording 2026-10-07 11.21.51 PM (narrated, live market). At ~11:38–11:50 PM the owner bought ~4,128.5 inside a
green 1H box after price swept the 1H low ("the institutional buy point"), TP ~4,135 at the red OB/breaker above, plan to
close if price stayed in the zone. Live outcome: TP not reached; price fell to ~4,119 by 00:53 (TV clock).
Rules frozen in PREREGISTRATION.md before testing; script pipeline/26_h1_sweep.py; outputs h1_sweep/.
1H STATION2 port, 3m execution, 2016-01 → 2026-10-07 (incl. 6 months never used before), 0.30 pt cost.
| Period | trades | gross R (before cost) | net $/trade (stop A, 2h) | placebo net $/trade |
|---|---|---|---|---|
| 2016–20 | 8,923 | +0.01 | −0.33 ± 0.04 | −0.32 |
| 2021–26/03 | 11,272 | −0.00 | −0.31 ± 0.09 | −0.30 |
| FORWARD 2026-04→10 | 1,303 | −0.04 | −0.59 ± 0.42 | −0.51 |
Verdict: coin flip before costs, real boxes = shifted fake boxes, negative after costs in every period and variant
(stop A/B, 2h/8h, buys/sells; post-hoc ≥$20-room filter also negative). Median room to the next 1H box $4.1, median
stop $1.4 — the spread eats ~0.2R per trade. Added to the indicator as a paper-tracked module so it can be watched live.

## Addendum 2026-10-10 — the FIRST trade in the 25-min live clip (3m + 1H): "1H box-to-box edge fade, tight stop"
Source: recording 2026-10-07 11.21.51 PM, watched in full (154 frames at 10 s + Whisper transcript in
`commentary/TRANSCRIPT_2026-10-07_11.21.51PM.txt`). Two paper trades are visible, not one:
1. SELL 616 at 4,138.19 (bottom of the red 1H box), SL 4,139.96 (1.77 pt), TP 4,128.58 (top of the green 1H box) → TP hit
   ~00:26 TV clock, +$5,918 paper ≈ +5.4R. Not tested before.
2. BUY 101→505 at ~4,128.5 after the 1H-low sweep ("institutional buy point"), TP 4,135.1, SL later moved to entry; open at
   +$2,129 when the clip ends (4,133). Tested 2026-10-08 (negative). Its final result is after our data ends (2026-10-07 23:59 UTC).
Note on size: 505–616 oz on paper ≈ 50–60 MGC contracts; the −$1,815 dip in trade 2 is a $3.6 move (≈ −$36 on 1 MGC).

Trade 1 frozen in PREREGISTRATION.md (2026-10-10) and run on 2016-01 → 2026-10-07 (`pipeline/27_h1_edge_fade.py`,
outputs `h1_edge_fade/`). Primary = stop 0.20·ATR1H + break-even at +1R. Mean R per trade (± 95%), real vs placebo boxes:
| Period | trades | real K+BE | placebo K+BE | real fixed 1.8 + BE | placebo fixed + BE | real K no-BE |
|---|---|---|---|---|---|---|
| 2016–20 | 8,783 | **−0.20 ± 0.06** | −0.26 | −0.00 ± 0.05 | −0.04 | −0.48 |
| 2021–26/03 | 13,228 | −0.01 ± 0.04 | +0.01 | +0.03 ± 0.04 | +0.06 | −0.27 |
| FORWARD 2026-04→10 | 1,579 | +0.13 ± 0.11 | +0.12 | +0.17 ± 0.13 | +0.12 | −0.11 |
Verdict: FAILS the pre-registered bar (negative in 2016–20; real boxes ≈ shifted fake boxes in every period). Win rate
14–20%, target reached 12–15%: the 5R winners are real but rare, exactly as a random level would give. Two things that ARE
consistent: (a) break-even at +1R lifts every variant by ~+0.25–0.40R, on fake boxes too — an exit-management effect, and
partly a 1-minute-bar artefact (intrabar order unknown, real fills/spread on a $0.9–1.8 stop are worse); (b) 2026's
higher volatility makes everything look better, placebo included. Median stop 0.93 pt, median room 6.5 pt, ATR1H 4.8.

---
## Addendum 2026-10-25 — market structure: 4H CHoCH → retrace into the area → 15m CHoCH → continue
Rules frozen in PREREGISTRATION.md (2026-10-25) before testing; pipeline/27_choch_retrace.py; outputs choch_retrace/.
Gold 2016-01 → 2026-10-23 (HistData + Dukascopy), 0.30 pt cost. ~25 setups a year (about 2 a month).
Primary (premium area 50–100% of the leg, first 15m CHoCH, structure stop, 2R):
| Period | n | mean R | 95% CI | control: any 15m CHoCH |
|---|---|---|---|---|
| 2016–20 | 112 | +0.20 | ±0.27 | −0.09 (n 4,100) |
| 2021–26/03 | 139 | −0.17 | ±0.22 | −0.03 (n 4,376) |
| FORWARD 2026-04→10 | 16 | +0.49 | ±0.76 | −0.05 (n 437) |
All 267: +0.02R ± 0.17. Buys +0.21R (125), sells −0.14R (142). OB area: similar, slightly worse.
Verdict: NOT proven, NOT dead. No variant's CI excludes 0; sign flips between periods; forward sample (16) far too
small. Better than the zone/sweep tests (not consistently negative) — worth a live paper log, not real money.

### Same thesis on 1H → 3m (addendum b; outputs choch_retrace_1h/ — table labels say 4H/15m but mean HTF/LTF)
Premium area, first 3m CHoCH, structure stop, 2R (median stop $3.5): 2016–20 −0.23R ±0.12 (n 523, significantly
negative) · 2021–26/03 −0.06R ±0.12 (n 510) · FORWARD 2026-04→10 +0.39R ±0.42 (n 48). Pooled ≈ −0.12R. Control (every
3m CHoCH) −0.18 / −0.09 / −0.05. OB area the same picture. Verdict: fails; only the recent 6 months look good, on both
1H and 4H — possibly the 2026 trend regime, not the pattern. 4H version remains the less bad one.

---
## Addendum 2026-10-26 — "Tokyo IFVG → New York goes to it → CHoCH → move" (owner's new strategy)
Rules frozen in PREREGISTRATION.md (2026-10-26); pipeline/28_tokyo_ifvg.py; outputs tokyo_ifvg/. 2016-01 → 2026-10-23.
One clarification made while coding (before results): an IFVG qualifies only when price at 08:00 NY is on the side it
is expected to come from (below a bearish IFVG / above a bullish one); median distance 3.1 × ATR15.
H-A magnet — NY 08–16 touches the Tokyo IFVG: 2016–20 55.6% vs mirror 54.9% · 2021–26/03 51.6% vs 56.0% ·
FWD 42.5% vs 54.7% (n 1,214 / 1,124 / 181). No magnet; if anything NY goes there LESS than to a fake box.
H-B owner's trade (touch → first 3m CHoCH, structure stop, 2R, flat 16:00, one per day per direction; median stop $4.7):
−0.16R ±0.10 (n 471) · −0.03R ±0.10 (n 425) · +0.02R ±0.29 (n 56); mirror boxes −0.16 / −0.03 / +0.00 → identical.
H-B0 limit at the edge: −0.19 / −0.00 / +0.24 ±0.38 (n 59); mirror −0.22 / +0.04 / −0.05.
Verdict: fails both parts. Real Tokyo IFVGs behave like fake boxes at the same distance.

---
## Addendum 2026-10-26 (b) — owner's clock setups (Central Time, 5m): 7–8 PM zone touch · 9:00 AM inside a zone
Rules frozen first; pipeline/29_clock_setups.py; outputs clock_setups/. 2016-01 → 2026-10-23, cost 0.30.
E (7–8 PM, first touch, limit at edge, 2R, 60 min): net −0.94R (n 2,419) · −0.59R (2,473) · −0.16R (269); before costs
−0.07 / −0.09 / −0.03; win 30–36%. 7 PM ranks 23rd of 24 hours. Placebo slightly worse (zones = slightly better than
random but still negative before costs). Zones born in the window: same.
N (9:00 AM inside a zone, 2R, 60 min): net −0.69R (615) · −0.51R (601) · +0.10R ±0.33 (71); before costs +0.01 / −0.15 /
+0.24; 9 AM ranks 4th of 24 (all hours negative; 10 AM–2 PM CT is the least bad block = the most volatile hours).
Median 5m-zone stop $0.5–1.2 before 2026 → the 0.30 spread alone costs 0.3–0.6R per trade. Verdict: both fail.

---
## Addendum 2026-10-26 (c) — Claude's own plan (4H 20-bar breakout + EMA100 trend, 2-ATR stop, 10-bar trailing low)
pipeline/30_trend_plan.py; outputs trend_plan/; cost 0.50; median stop $17.
+0.17R ±0.25 (n 184) · +0.03R ±0.21 (217) · −0.05R ±0.53 (23); pooled ≈ +0.09R → ≈ +1.9 %/yr at 0.5 % risk.
Worst drawdown −36R (2021–22). Without the trend filter: same. Random entries with the same exits: +0.00 / +0.03 / −0.04.
Profits come only in trend years (2016, 2019–20, 2025–26); the top 10 % of trades make >4× the total.
Verdict: fails the pre-registered bar too — mildly positive, not distinguishable from 0. No day/swing-trading edge found.

---
## Addendum 2026-10-26 (d) — "after a fresh FVG the next candle goes $5 more" + profit seen before losses
pipeline/31_fvg_next5.py (5m), outputs fvg_next5/. 54,937 fresh FVGs (not inside an opposite FVG/IFVG), 2016–2026.
Next candle +$5: 0–2% of the time 2016–24, 8% 2025, 24% 2026 (any candle: 17%). +$5 within 1 h in 2026: 66% (any candle 65%).
$5 target / $5 stop: −$0.28 to −$0.56 per trade EVERY year (any candle the same). No stop (out after 1 h): −$0.32/trade;
2026: hits +$5 66%, misses average −$10.17, worst −$155. Losing 1:1 trades were in profit first by a median $0.5–0.8;
only 13–17% were ever up $3+. Verdict: "$5 every time" is false; the misses outweigh the hits.

---
## Addendum 2026-10-26 (e) — Instagram reel "5-step reversal" (HTF level → sweep → MSS → FVG/OB → 0.71 fib, TP −0.27)
pipeline/32_reel_reversal.py; outputs reel_reversal/. 15m, 4H swing levels, cost 0.30, planned ≈3.4R.
With key level: −0.20R ±0.34 (n 107) · −0.10R ±0.31 (125) · −0.23R (5). Win 25%. +FVG: −0.15 / −0.25 / n 3.
Without key level (same steps): −0.29 / −0.22 / −0.17 (n 1,718 / 1,964 / 192) — key level slightly less bad, still < 0.
Verdict: fails; a 3.4R target needs a >23% hit rate after costs and gets 21–26%.

---
## Addendum 2026-10-26 (f) — reel: "trade the zone that lines up with the volume-profile POC"
pipeline/33_poc_zone.py; outputs poc_zone/. Profile = time at price (no real volume in spot gold). 1H legs, 15m fills.
2R target: POC zone −0.12R ±0.09 (n 974) · −0.02 ±0.09 (948) · +0.01 ±0.27 (108); other zones −0.42 / −0.21 / −0.03;
random fake zone −0.43 / −0.26 / −0.11. POC zones clearly LESS BAD — but they are bigger (median stop $4.8 vs $2.0):
size-matched, POC ≈ other zones (large −0.06 vs −0.05; xl −0.00 vs +0.06). Before costs POC zones +0.01R.
Verdict: no edge; the POC "filter" works by picking wider zones (fewer cost-killed trades), same as the wide-zone finding.

---
## Addendum 2026-10-27 — FVG made by the 8:30 AM New York candle (and 9:30 NY = 8:30 Central)
pipeline/34_fvg_830.py; outputs fvg_830/. Limit at the near edge, stop beyond the 3 candles, 2R/3R, flat 210 min, cost 0.30.
5m 8:30 NY: −0.29R ±0.16 (261) · −0.07 ±0.18 (209) · −0.10 (19); rank 106 of 287 five-minute slots.
5m 9:30 NY: −0.33 / −0.18 / −0.12; rank 155. 15m 8:30 NY: −0.31 / −0.18 / −0.46.
15m 9:30 NY: −0.09 ±0.14 (212) · −0.03 ±0.13 (225) · +0.10 ±0.45 (20) — closest to break-even, not positive.
Verdict: fails; 8:30 is an ordinary slot (all slots average −0.25R).

---
## Addendum 2026-10-27 (b) — ICT Silver Bullet (pipeline/35_silver_bullet.py → silver_bullet/)
First 5m FVG in 03–04 / 10–11 / 14–15 NY, limit at near edge, stop beyond candle 1, target = nearest liquidity (≥ $1.50) or 2R.
Pooled 3 windows, DOL target: EXT −0.19R ±0.07 (1531) · IS −0.19 ±0.06 (1511) · FWD +0.15 ±0.20 (153). 2R: −0.23 / −0.16 / +0.11.
Per window DOL: 03:00 −0.17/−0.17/+0.13 · 10:00 −0.12/−0.17/+0.15 · 14:00 −0.27/−0.23/+0.17. All FWD CIs include 0.
By year (pooled DOL): every year 2016–2025 negative (−0.09 to −0.33); 2026 +0.03.
Hour ranks (24 hours, DOL): 10:00 = 3rd, 03:00 = 4th, 14:00 = 8th; the best hours are 10–12 NY (11:00 ranks 1st), but no hour is positive over all years.
FWD: other 21 hours −0.04R vs SB windows +0.15R — a hint, not significant (n 153, CI ±0.20).
Verdict: FAILS pre-registered pass (EXT negative with CI excluding 0). The NY late-morning windows are the "least bad" hours for FVG entries, consistent with stage 34.
