# Backtest specification: zone reactions and 5m confirmations

These definitions were written into `pipeline/08_events.py` and `09_analysis.py` **before** the full-dataset results were computed. Any change to a threshold below counts as a new experiment and must be re-run on data that was not used to choose it.

## 1. Data

| Item | Specification |
|---|---|
| Instrument | MGC1! (Micro Gold, COMEX), continuous back-adjusted (B-ADJ), ETH session |
| Execution timeframe | 5-minute bars, America/Chicago exchange time |
| Context timeframe | 4-hour bars built from 5m on the CME session grid: 17:00, 21:00, 01:00, 05:00, 09:00, 13:00 CT (the last bar of each session is 3 h). Validated against the 4H pane header; see `report.md` §1. |
| Source here | Pixel-reconstructed from the replay video (`data/bars_5m.csv`) |
| Source for re-testing | Any MGC 5m OHLC export. The pipeline from stage 7 on runs unchanged. |
| Session labels | The indicator's UTC boundaries: ASIA < 07:00 UTC ≤ LONDON < 12:00 ≤ NY < 17:00 ≤ LATE |
| Split | First 60% of trading days = DEV; last 40% = HOLDOUT. Rules are chosen on DEV only. |

## 2. Zones (the trusted map)

Built by the port of STATION2's zone code (`pipeline/zone_engine.py`, default parameters). Two engines:

- **5m engine** on 5m bars: FVG, OB, and 4H FVGs imported with replay (realtime) timing, `kind = "4H"`.
- **4H engine** on 4H bars: FVG and OB. A zone becomes available on the 5m clock at the close of the last 5m bar of the 4H bar that created it.

A zone is usable from the bar **after** its availability bar.

## 3. Events

```
for each zone Z (direction d = +1 demand, -1 supply; near edge N, far edge F):
    for bar i after Z becomes available, while Z intact and arrivals < 3:
        ARRIVAL if  d=+1: low[i] <= top and low[i-1] > top
                    d=-1: high[i] >= bot and high[i-1] < bot
        Z is broken (stop scanning) at the first 5m CLOSE beyond F
```

Features are recorded at the arrival bar's close; none use later bars. Examples: zone kind, timeframe, size in ATR, age, arrival number, trend alignment on 5m and 4H (EMA100 slope over 10 bars, last closed 4H bar), inside a live same-direction or opposite 4H zone, penetration depth, close position, zone-side wick, approach speed (6-bar move in ATR), touch-bar range in ATR, pool swept on the touch bar, session, hour, weekday, and volatility regime (ATR vs its 2000-bar median). ATR is Wilder ATR(14) on 5m.

## 4. Reaction taxonomy (24 bars = 2 hours after arrival)

| Reaction | Rule (evaluated bar by bar, first condition met wins) |
|---|---|
| REJECT | Price moves ≥ 1 ATR away from N in direction d before any close beyond F |
| SWEEP_RECLAIM | A wick beyond F occurs first, with no close beyond F, then ≥ 1 ATR away from N |
| BREAK | A close beyond F comes first |
| BREAK_RETEST | BREAK, then price returns to the zone from the other side and moves ≥ 1 ATR away in the break direction within the window (the role flip) |
| CHOP | None of the above within 24 bars |

"Held" = REJECT or SWEEP_RECLAIM. MFE and MAE are measured from `close[i]` at 1, 3, 6, 12 and 24 bars, in ATR units.

## 5. Confirmations (searched in bars i … i+11, zone must stay intact)

| Code | Trigger bar j (earliest qualifying bar) |
|---|---|
| C0_TOUCH | j = i, no confirmation (baseline) |
| C1_RECLAIM | A close back outside the zone on the near side |
| C2_ENGULF | Close beyond the prior bar's extreme in direction d, with a body in direction d |
| C3_CHOCH | A 5m BOS/CHoCH in direction d (indicator's structure definition, pivots 3/3) |
| C4_DISPLACE | Body ≥ 1.2 × ATR in direction d |
| C5_WICK | j = i: close in the outer third of the bar and zone-side wick ≥ 50% of the range |
| C6_SWEEP | A 5m pool on the zone side (EQL for demand) swept in the window, then a close back outside the zone |
| C7_FVG | A new 5m FVG in direction d is born |
| **K1_FLIP_RETEST** (continuation, trade direction −d) | After the zone **breaks** (close beyond F), price returns into the zone from the break side within 36 bars. Within 6 bars of that, a close back out on the break side triggers the trade. It is cancelled if price closes back through the zone's near edge. Stop = extreme since the retest began ± 0.25 ATR. |

## 6. Trade simulation

```
entry  = open[j+1]                                   # next bar open: executable
stop   = min(low[i..j], F) - 0.25*ATR[i]   (d=+1)    # beyond the sweep/zone extreme
         max(high[i..j], F) + 0.25*ATR[i]  (d=-1)
risk   = |entry - stop|  ;  skip if risk < 0.2*ATR   # the indicator's own MIN_RISK_ATR floor
target = entry + d * R * risk,  R in {1, 2, 3}
for each bar k from j+1 while k < j+1+48:
    if stop touched: exit at stop → loss
    elif target touched: exit at target → win         # stop checked FIRST (conservative)
    # gold does not gap intraday on 5m: fills are at the order price, EXCEPT on the 17:00 CT
    # session-open bar, where a gapped open is the fill (worse for stops, better for targets)
time stop: exit at close of bar j+48
R_result = (d*(exit - entry) - 0.3) / risk            # 0.3 pt round-trip cost
```

**Changes made during data validation, before the final results were read.** These were fixes to glitches in the video reconstruction, not strategy tuning:

1. **No intraday gap fills.** The first simulator filled at any gapped open. Glitch bars (lines or labels read as candles) then produced trades of +10R or −140R.
2. **Minimum risk of 0.2 ATR.** Near-zero risk turned the 0.3 pt cost into dozens of R.
3. **Glitch repair on the bar series** (`07_build.py`). Isolated 1–3 bar jumps of more than 3 ATR that return, flat junk bars that are discontinuous by more than 1.5 ATR, and single wicks more than 3 ATR beyond both neighbours with the body inside them are bridged or clipped and flagged `spike_repaired`. This affected 534 bars (0.8%).

- Orders that different zones generate for the same bar, direction and confirmation count once.
- Statistics: win rate, mean R with a 95% CI from a day-block bootstrap (2000 draws), profit factor, share of time-stop exits. Reported separately for DEV, HOLDOUT and ALL.
- **Acceptance bar for a rule:** mean R > 0 with a 95% CI that excludes 0 on DEV **and** a positive mean on HOLDOUT, with n ≥ 100 in each. Anything weaker is reported as not established.
- **How many rules were tested:** about 970 combinations with enough data (7 zone families × 6 context filters × 9 confirmations × 3 targets). With that many tests, some pass development by chance. That is why the holdout decides, and why the report shows how many development passes were confirmed on holdout.

## 7. Stress tests to run before using any rule with money

1. Cost at 0.6 pt round trip, i.e. double.
2. Entry one bar later (the confirmation is seen late).
3. Separate long and short results.
4. Leave out the largest 5% of winners.
5. Re-run on MGC data from any period outside Oct 2025 – Sep 2026, with no parameter changes.
