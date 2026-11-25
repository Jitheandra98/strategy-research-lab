# Strategy: 4H zone, with the 4H trend, entered on the first touch

**Status: a candidate for forward testing, not proven.** On about 11 months of MGC rebuilt from your replay, this was the only zone rule that made money in both the development period and the later holdout. It returned **+0.20R per trade** over 195 trades, one position at a time (95% CI +0.07 to +0.33R). Its evidence misses my pre-registered bar in one respect: holdout n was under 100. It also relies partly on a small number of large winners. Paper-trade it forward before risking money. Everything below comes from `report.md` §3.

## The one idea

The 4H map sets **location** and the 4H trend sets **direction**. The 5m chart only tells you **when price has arrived**. In this data, 5m confirmation patterns added no measurable edge, and 5m zones on their own had none.

## Setup grades

| Grade | Definition | Measured, 2R target, after 0.3 pt costs |
|---|---|---|
| **A: trade** | Price arrives at a live **4H zone** (a 4H-chart FVG/OB, or a 4H FVG imported onto 5m) **in the direction of the 4H trend** | +0.18R/trade over all 322 signals: development +0.16R, holdout +0.22R. One position at a time: +0.20R over 195 trades |
| **B: optional, smaller** | Same as A, but no clear 4H trend | Stand-in measurement is every 4H arrival without the trend filter, counter-trend ones included: +0.08R (CI −0.02 to +0.19). The trend-neutral subset wasn't measured separately. |
| **C: no trade** | A 4H zone **against** the 4H trend | −0.06R in both development and holdout |
| **C: no trade** | Any **5m-only** zone (FVG/OB), with or without a 5m confirmation | −0.015R/trade over about 10,000 signals; no confirmation turned it positive |
| **C: no trade** | Continuation after a zone breaks (flip-retest, the indicator's BREAKER idea) | −0.11R/trade over 2,543 trades (CI −0.17 to −0.06); on 4H zones −0.28R (n=67) |

## Rules (grade A)

**Context (4H), all known at the last closed 4H bar:**
1. **4H trend** = sign of the EMA(100) slope over 10 bars on the 4H chart (the indicator's `trendDir`, applied to 4H bars). Longs only when it is rising; shorts only when it is falling.
2. **Zone** = a 4H FVG or 4H OB from STATION2's zone logic, or a 4H FVG imported onto the 5m chart. It must be **intact**: no 5m **close** beyond its far edge since it formed.
3. It must be one of the zone's first 3 arrivals. Later arrivals weren't tested.

**Trigger (5m):**

4. **Arrival:** a 5m bar trades into the zone from outside. For a demand zone, `low ≤ zone top` while the previous bar's low was above the top; mirror this for supply.
5. **Entry:** market at the **open of the next 5m bar**. No confirmation candle. Waiting for a reclaim close (C1) measured about the same (+0.19R versus +0.18R), with a later fill and a wider stop.

**Risk:**

6. **Stop** = the further of the zone's far edge and the touch bar's extreme, plus a **0.25 × ATR(14, 5m)** buffer. Median risk was **25.6 points (about $256 per MGC contract)**, about 3.3 × the 5m ATR. Skip the trade if the risk is under 0.2 ATR.
7. **Target** = **2R** (1R and 3R both measured positive but not better). Leave a resting limit order.
8. **Time stop:** exit at the close of the **48th** 5m bar (4 hours). About 47% of A trades exited on the clock. Much of the result is "ride the trend after a pullback into a 4H zone", not a quick bounce.
9. One position at a time. Skip new signals while in a trade.

**No-trade filters (all measured):**
- The 4H trend is against the zone's direction.
- The zone has already had a 5m close beyond its far edge (broken).
- The arrival bar is inside an **opposite-direction** live 4H zone. This is untested as a filter, so treat it with caution.

**Context flags that changed how often 4H zones held** (hold rate = ≥ 1 ATR bounce before a close through the zone). These were consistent in development and holdout, but were **not** tested as trade filters, so don't add them without a new test:

| Flag | Hold rate with / without |
|---|---|
| Touch bar closes back outside the zone | 84% / 61% |
| Zone ≥ 3 × 5m ATR tall | 85% / 61% |
| 5m trend also aligned | 81% / 70% |
| High-volatility regime | 68% / 81% (worse) |
| Fast approach (≥ 2 ATR in 6 bars) | 65% / 79% (worse) |

## Position sizing reality check

The indicator's identity inputs say a $4,000 prop account risking 0.5% per trade, which is **$20 of risk**. One MGC contract at the median 25.6-point stop risks about **$256 plus costs**. **That account can't take this trade at that risk size, even with one micro contract.** Don't shrink the stop to make it fit; the stop is the thesis. The honest options are a larger risk budget per trade, or paper trading until the edge is confirmed.

## Pseudocode

```text
on each closed 4H bar:
    trend4 = sign(ema100_4h[now] - ema100_4h[now-10])
    update 4H zone engine (FVG, OB)                        # STATION2 zone rules, default params

on each closed 5m bar i:
    update 5m engine; import new 4H FVGs (replay/realtime timing)
    if in_position: manage(); continue
    for zone Z in live 4H zones (4H-chart zones + imported 4H FVGs), intact, arrivals < 3:
        if Z.dir != trend4: continue                       # grade C
        arrived = (Z.dir == +1 and low[i] <= Z.top and low[i-1] > Z.top) or
                  (Z.dir == -1 and high[i] >= Z.bot and high[i-1] < Z.bot)
        if not arrived: continue
        far   = Z.bot if Z.dir == +1 else Z.top
        ext   = low[i] if Z.dir == +1 else high[i]
        stop  = min(ext, far) - 0.25*ATR[i]  if Z.dir == +1 else max(ext, far) + 0.25*ATR[i]
        place market order at open[i+1]; risk = |entry - stop|
        if risk < 0.2*ATR[i]: cancel
        target = entry + Z.dir * 2 * risk ; time_stop = 48 bars
        break                                               # one position at a time

manage():
    stop first, then target (conservative when both touch in one bar); exit at close of bar 48
```

## What would falsify it

Paper trade grade A forward, unchanged, for at least 100 trades (about 7 months at 3.5 per week). Stop using it if the forward mean R is at or below 0 after 100 trades, or if drawdown passes 15R (the backtest's worst was 9.2R). Log every signal, including skipped ones, and the video/chart timestamp of each.
