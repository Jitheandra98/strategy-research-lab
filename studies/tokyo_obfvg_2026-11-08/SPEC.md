# Tokyo bias + QF CORE order blocks / FVGs, pre-registered 2026-11-08 (written BEFORE testing)

## His plan (corrected by him: Tokyo only, no New York)
Watch the first hour after Tokyo opens on the five blue lines (Desk Context session VWAP ±1/±2 SD). That sets the day's bias.
On a buy day we ONLY buy: whenever price comes back to a bullish order block → buy; whenever it comes back to a fair value gap
→ buy. Sell days are the mirror (only sells, at bearish OB/FVG). He gave no TP/SL, so I set them below.

## Rules
- Data: gold spot 5m, Jan 2012 → Sep 2026. Lines are equal-weight (no volume in our data), anchored 18:00 ET as in Desk Context.
- Bias at 01:00 UTC from the 12 five-minute closes of 00:00–00:55 UTC (Tokyo = 00:00 UTC, the QF CORE default):
  MAIN = every close above +1 SD → BUY day, every close below −1 SD → SELL day.
  LOOSE (check) = every close above / below the center line.
- Zones = QF CORE v1.0 logic ported from the code he pasted, on 5m bars:
  - Order blocks: swing (length 50) and internal (length 5, with the 1.3× displacement rule) structure breaks. On a bullish
    break, the OB is the bearish candle with the lowest low between the broken pivot and the break bar; mirror for bearish.
    Removed on a full cross (High/Low mitigation) or when the swing trend flips. Max 100 stored per list.
  - FVGs: 3-candle gap ≥ 0.3 × ATR(14). Removed when a close goes through the far edge, when an opposite FVG overlaps it
    (IFVG), or when more than 15 are stored.
  A zone is tradeable from the bar after it is created until it is removed.
- Trading window = 01:00–09:00 UTC (the rest of the Tokyo session). Entry = the FIRST touch of a fresh zone in the bias
  direction. Buy day: a bar opens above a bullish zone's top and trades down to it → buy limit at the top. Sell day: mirror at
  a bearish zone's bottom. One trade at a time. A zone touched while a trade is open is used up.
- Stop = just beyond the zone (bottom − 0.1 for buys, top + 0.1 for sells). Target MAIN = 2R. Checks at 1R and 3R.
  Close at 08:55–09:00 UTC if still open.
- Inside the entry bar only the stop can count (price had to pass the entry to reach it). After that the stop counts first,
  and a gap through the stop fills at the open. Skip risk < 0.2 pt. 1 MGC, 0.3 pt per round trip (and 0.5 check).
- Variants: MAIN (OB + FVG, 2R, MAIN bias, both day types; buy days reported separately), OB only, FVG only, 1R, 3R,
  LOOSE bias, and the CONTROL: the same zone trades in the same window on EVERY day with no bias (both directions).
  The control answers whether the Tokyo bias adds anything.

## Pass bar (same as every test today)
a) PF ≥ 1.15 after 0.3 pt in each period 2012–19, 2020–23, 2024–26; b) long AND short profitable (for the buy-only view:
buy days must pass a, c, d, e); c) profitable at 0.5 pt; d) ≥ 9 of 15 years profitable; e) ≥ 30 trades per period.
