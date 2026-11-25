# 100-setup catalog + "18:00 UTC−6 range breakout": pre-registered 2026-11-08, written BEFORE any test

The owner pasted a catalog of 100 gold day-trading setups (10 groups) and one separate setup. Ideas #3 and #4 of the partnership.
Exact rules are in the code (common.py, single.py, catalog.py), also written before running. This file holds the conventions.

## Data limits: what can and cannot be tested
Data = gold SPOT 5m OHLC, Jan 2012 → Sep 2026. It has **no volume**, no order flow or depth, no event calendar, and no other markets.
- TESTABLE (47): 1, 3, 4, 5, 7, 8, 9, 10, 11–20, 21–24, 26–30, 41–50, 51–60.
- NOT TESTABLE without new data (53): 2, 6, 25 (RVOL / VWAP need volume); 31–40 (exchange-volume VWAP); 61–70 (volume profile,
  RVOL); 71–80 (aggressor / order-book data); 81–90 (exact CPI / NFP / PPI / PCE / GDP / FOMC / claims timestamps);
  91–100 (DXY, ZN, silver, copper, ES, miner ETF bars). We do not swap in a stand-in (e.g. TWAP for VWAP), because that would
  test a different rule.

## Conventions (one choice each, fixed now)
- Clock: the catalog's U.S. and Asian times are **Chicago time** (its own note pins settlement to 12:30 p.m. Chicago).
  London-time setups (3, 8, 9) use the London clock. DST is handled in both.
- Session = CME trading day 17:00 → 16:00 CT. Prior-session high/low/close = the previous CME session.
  Settlement = the 12:30 CT price (close of the 12:25 bar). Week = Mon–Fri trade dates; weekly open = the week's first price.
- Bars = 5m unless the setup names another frame (14: 30m filter; 23: 15m bars).
- ATR = ATR(14, Wilder) of the trading bars. Daily ATR (45, 46) = ATR(14) of session ranges, previous session.
  EMA standard; RSI(14) and ADX/DI(14) Wilder; Bollinger(20, 2σ); Keltner = EMA20 ± 1.5 ATR.
- Confirmed swing high/low = 3-bar fractal, usable 3 bars after the pivot (no look-ahead).
- "One tick beyond" = 0.1. Stops placed "beyond" a level sit 0.1 beyond it.
- Entry at the NEXT bar's open after the signal close. Stop, target and R are fixed at entry. Inside a bar the stop counts
  first. A gap through the stop fills at the open. Targets fill at the target. Trades with R < 0.2 pt are skipped.
  A target already passed at entry → skip the trade.
- Every setup is tested **both ways** (the written side + its mirror), so gold's 2024–26 bull run can't pass as an edge.
- One open trade per setup at a time. Never held across the 16:00–17:00 CT break (forced exit at the session's last bar).
- 1 MGC = $10/pt. Cost 0.3 pt per round trip, also checked at 0.5 pt.

## Pass bar (same as ideas #1 and #2, plus a sample-size rule)
a) PF ≥ 1.15 after 0.3 pt in each period 2012–2019, 2020–2023, 2024–2026; b) long AND short both profitable;
c) profitable at 0.5 pt; d) ≥ 9 of 15 years profitable; e) ≥ 30 trades in each period.
**Multiple-testing warning, written now:** with ~49 rules tested, a few will look decent by luck. Any pass only earns paper
trading, and a thin pass (overall PF < 1.3) would need years of forward data to confirm (see spike_follow_2026-11-08).

## The separate setup: "18:00–18:30 UTC−6 range breakout"
Range = 18:00–18:30 (six 5m bars from the 18:00 candle). After 18:30, take only the first 5m close above the high (long) or
below the low (short). Stop one tick beyond the range midpoint. Exit at 2R or 20:00, whichever comes first.
MAIN = Chicago clock (what the owner's TradingView shows as "UTC−6 Chicago" in winter). ALT = a literal fixed UTC−6 all
year (one hour later in summer). Plus a random same-clock control (20 other days, same direction / stop / exit).
