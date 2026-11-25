# BOX-TO-BOX 3m — strategy written from watching your replay (v1, 2026-10-07)

This is the strategy as I saw it work on your screen (30 Sep – 1 Oct 2026 replay). The rules are exact, so anyone,
including a script, applies them the same way every time. Below the rules is what happened when I ran them
on every 3-minute candle from 2016 to 2026.

## The map (4H chart)
- Every STATION2 box on the 4H chart (OB, FVG, IFVG, breaker, imported 4H FVG) gives **three levels**: top, middle (CE) and bottom.
- Price travels from one level to the next. A trade happens only **at** a level, never in between.

## The setup (3m chart)
1. **Arrival.** Price reaches a 4H level from the other side, after the previous hour (20 × 3m candles) stayed clearly away from it (more than 0.05 × 4H ATR).
   - Rally into a level → look for a **SELL**.
   - Drop into a level → look for a **BUY**.
2. **Confirmation (the bias).** Within the next 2 hours (40 × 3m candles):
   - **SELL:** a 3m candle **closes below the last 3m swing low** that formed after the touch (the rejection breaks 3m structure).
   - **BUY:** a 3m candle **closes above the last 3m swing high** that formed after the touch.
   - **Cancel** if price instead closes more than half a 4H ATR through the level. The level was accepted, so price travels on to the next box.
3. **Entry:** the close of the confirmation candle.
4. **Stop:** just beyond the extreme made since the touch (+0.05 × 4H ATR).
5. **Target:** the **next 4H level** in the trade's direction (any box top, CE or bottom) that is at least 1R away. If there is none within 4R, use 2R.
6. **Time limit:** 8 hours. **Costs:** 0.30 pt per trade (spread + slippage).

**Best filter found** (chosen on 2022–24 only): trade only **with the 4H trend** (STATION2 EMA100 slope) and only in the **London (02:00–08:00 NY) or New York morning (08:00–12:00 NY)** sessions.

## What I saw live on your replay
Every setup was written in `WATCH_LOG.md` before its result was known.

| # | Where | Side | Result |
|---|---|---|---|
| 1 | under the red 4H box, double top 4,202 | SELL | −1.0R |
| 2 | 4H box midline (CE) 4,218 | SELL | +1.6R |
| 4 | top of the green 4H box 4,140 | BUY | +2.4R |
| 6 | under the red 4H box 4,193 | SELL | +0.9R |
| 7 | under the red 4H box 4,184 | SELL | +0.5R |

Total: **+4.4R over 5 trades.** "Price travels to the next box" was right 3 times out of 4.

## What happened on every candle, 2016–2026 (`pipeline/19_box2box.py`)

| Version | Data | Trades | Win rate | Avg per trade (95%) | Same rules, random boxes |
|---|---|---|---|---|---|
| All setups | 2022–2026 | 19,861 | 37.9% | **−0.067R ± 0.016** | −0.067R |
| All setups, per year | 2022 / 23 / 24 / 25 / 26 | — | — | −0.09 / −0.08 / −0.11 / −0.05 / −0.01R | similar |
| Best filter (trend + London/NY-AM) | 2022–24 (picked here) | 2,968 | 37.5% | −0.003R ± 0.040 | −0.049R |
| Best filter | 2025–26 (check) | 2,186 | 38.2% | −0.003R ± 0.047 | +0.014R |
| Best filter | 2016–21 (check) | 5,880 | 34.8% | **−0.125R ± 0.029** | −0.133R |

## Verdict

- **What I saw on screen is real.** Price travels box to box and often rejects at box edges and midlines. My 5 watched trades made +4.4R.
- **Over 10 years it is a losing strategy.** Over thousands of identical setups the average trade loses 0.07R. The best filtered version only breaks even, and it lost 0.13R per trade in 2016–21.
- **The boxes add nothing.** The same rules on randomly placed boxes give the same results.
- **Why the replay looked so good:** 5 trades over 1.5 days is a tiny sample. A coin-flip strategy has runs like +4.4R all the time. Over 20,000 trades the runs cancel out.

**Do not trade this with real money.** If you still want to use it, use it as a paper-trading plan: log every setup as it happens (as in `WATCH_LOG.md`), with no skipping, until there are at least 100 trades. Only a positive result after 100 trades logged that way would mean something.
