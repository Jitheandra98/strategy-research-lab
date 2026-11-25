# Pre-registration — STATION2 zone-interaction study (videos of 2026-10-06/07)

Written 2026-10-07, **before any outcome (post-interaction price movement) was computed**.

## Sources
- V1 `Screen Recording 2026-10-06 at 9.09.21 PM.mov` (3h38m)
- V2 `Screen Recording 2026-10-07 at 12.50.20 AM 1.mov` (3h25m)
- V3 `Screen Recording 2026-10-07 at 7.20.49 AM.mov` (10h08m)

All three are TradingView bar-replay sessions of OANDA:XAUUSD with a 15m pane (left) and a 4h pane (right),
both running STATION2 (THE STATION APPOINTMENT v2.0, `CE_VERSION = "STA-2.1"`) plus QUANTUM FLOW CORE v1.0.

## Data splits (fixed now, not to be changed after seeing results)
| Split | What | Use |
|---|---|---|
| DISCOVERY | interactions whose arrival bar was revealed on screen in **V1 or V2** | all exploration, feature screening, clustering, rule building |
| VALIDATION | interactions revealed on screen in **V3** | opened **once** per frozen rule set; no rule is edited after looking |
| EXTERNAL (bonus) | the same zone engine on Dukascopy 15m/4H bars for **2022-07-15 → 2024-04-30 excluding every bar replayed in any video** | a larger out-of-video check of the frozen rules; clearly labelled as not-from-video |

V3 is chronologically the latest replay material (checked after dating) and is the longest video, so it is the
natural holdout. If dating shows V3 overlaps V1/V2 replayed dates, overlapping bars are dropped from VALIDATION.

## Outcome definitions (fixed now)
- Units: 15m ATR(14) at the arrival bar (primary), zone height (secondary), points (reported).
- Reference price: close of the arrival bar (the first bar whose range enters the zone from outside).
- "Reaction direction": away from the zone in its defending direction (demand → up, supply → down).
- Horizons: 1, 2, 3, 5, 10, 20 bars after the arrival bar.
- MFE/MAE over 20 bars in the reaction direction.
- Primary binary target **R1**: price reaches +1.0 ATR in the reaction direction before it reaches −1.0 ATR
  (both measured from the arrival close, using bar highs/lows; same-bar ties count as a loss).
- Secondary target **BRK**: a 15m close beyond the far edge within 10 bars (zone failure).
- Base rate is always reported next to every conditional rate. A conditional rate must beat the base rate
  by a margin whose 95% Wilson interval excludes the base rate to be called "moderate evidence";
  holding up in VALIDATION as well is required for "strong evidence".

## Labelling discipline
interesting observation (n<20 or CI overlaps base) → candidate hypothesis (DISCOVERY only) →
moderate evidence (DISCOVERY CI excludes base) → strong evidence (also holds in VALIDATION, same sign, CI excludes base).
Multiple-comparisons: the number of conditions screened is reported; a Benjamini–Hochberg q-value is given.

---
## Addendum 2026-10-08 02:30 CDT — "1H sweep-and-reject" (owner's live trade, recording 2026-10-07 11.21.51 PM)
Written BEFORE any test of it. Source: owner's narration at 11:38–11:50 PM ("this is the sweep point… the
institutional buy point… one hour… first reaction to the zone… only through rejections… take profit at the top of
the breaker block… if it persists in this zone I will just close out the trade"). Live trade: paper BUY ~4,128.5 inside a
green 1H STATION2 box after price swept the 1H low; TP ~4,135 (red OB above); TP not reached, price fell to ~4,119.

Frozen rules (BUY; SELL mirrored):
1. Zones = STATION2 port run on 1H bars (UTC hours); a box is usable from the close of its birth bar until archived;
   its direction flips once it is inverted (breaker / IFVG).
2. At a 3m bar: low is inside a live bullish 1H box (low <= top and low >= bottom - 0.25·ATR1H) AND low < low of the
   last CLOSED 1H candle (the sweep of "the one-hour point").
3. Entry: first 3m close back above that 1H low within 5 bars (15 min) of the sweep bar → enter at that close.
4. Target = bottom of the nearest live bearish 1H box above entry (none → no trade).
5. Stop A (primary) = lowest low since the sweep − 0.10·ATR1H. Stop B = box bottom − 0.10·ATR1H.
6. Time exit (owner's "if it stays in the zone, close"): 2 h after entry at the 3m close. Variant: 8 h.
7. Cost 0.30 pt per trade; stop checked before target inside a bar; one open trade per direction.
Control: identical rules on placebo boxes (every box shifted by ±2·ATR1H at random, 3 draws).
Periods: EXTERNAL 2016-01→2020-12 · IN-SAMPLE 2021-01→2026-03 · FORWARD 2026-04-01→2026-10-07 (never looked at).
Pass = mean R > 0 with 95% CI excluding 0 in FORWARD and EXTERNAL, and beating placebo in both.

---
## Addendum 2026-10-10 — "1H box-to-box edge fade, tight stop" (the FIRST trade in recording 2026-10-07 11.21.51 PM)
Written BEFORE any test of it. Source: frames 00:00–16:30 of the recording (owner's paper account): SELL 616 at 4,138.19 =
bottom edge of the red 1H STATION2 box, SL 4,139.96 (risk 1.77 pt), TP 4,128.58 = top of the green 1H box below
(≈ 5.4R). TP filled ~00:26 TV clock (+$5,918 paper). He then reversed long at 4,128.5 (tested in the 2026-10-08 addendum)
and moved that stop to entry once in profit.

Frozen rules (SELL; BUY mirrored):
1. Zones = same 1H STATION2 port as stage 26 (usable from the close of the birth bar; direction flips once inverted).
2. Arm: a live bearish 1H box whose bottom is ABOVE the last closed 1H close, and a live bullish 1H box whose top is
   below that close (price is "between boxes").
3. Entry: limit SELL at the box bottom, filled by the first 1m bar whose high reaches it (previous 1m high below it).
   Same-bar stop touch counts as a loss.
4. Stop = entry + 0.20·ATR1H (primary). Variant: fixed 1.8 pt.
5. Target = top of the nearest live bullish 1H box below entry; trade only if target ≥ 2R away.
6. Break-even (primary): after +1R in favour, stop moves to entry. Variant: no break-even.
7. Time exit 8 h at the 1m close. Cost 0.30 pt. One open trade per direction. A box re-arms only after price has
   been ≥ 0.5·ATR1H away from the edge since its last trade.
Control: placebo boxes (every box shifted ±2·ATR1H at random, 3 draws), identical rules.
Periods: EXTERNAL 2016-01→2020-12 · IN-SAMPLE 2021-01→2026-03 · FORWARD 2026-04-01→2026-10-07.
Pass = mean R > 0 with 95% CI excluding 0 in FORWARD and EXTERNAL, and beating placebo in both.
Script: pipeline/27_h1_edge_fade.py; outputs h1_edge_fade/.

---
## Addendum 2026-10-25 — "4H CHoCH → retrace to the area → LTF CHoCH again" (owner's market-structure thesis)
Owner (chat, 2026-10-25): when the 4H prints a change of character, price goes back into that area, then a sell CHoCH
comes again and price continues down; same for buys. Written BEFORE any test.

Structure (both TFs): swings = pivots 3/3 (STATION2 PIVOT_LEN), usable only once confirmed (3 bars later).
Break = a candle CLOSE beyond the last confirmed unbroken swing. A break against the current trend = CHoCH, with the
trend = BOS. 4H candles on the 17:00 New York grid; LTF = 15m.
SELL setup (BUY mirrored):
1. 4H bearish CHoCH: a closed 4H candle closes below the last 4H swing low while 4H trend was up.
   Leg top = highest high between that swing low and the CHoCH candle; leg low = lowest low from leg top to CHoCH.
2. The "area" — two pre-registered versions:
   OB  = the last up-close 4H candle at or before the leg top (its low → high);
   PREM = 50%–100% of the leg (leg low + 0.5·leg → leg top).
3. Retrace: within 10 days, a 15m high trades back into the area (high ≥ area bottom). Cancelled before that if
   price closes a 15m bar above the leg top or a 4H bullish CHoCH prints.
4. Entry (primary): the first 15m bearish CHoCH after the touch, within 3 days → sell at that 15m close.
   Variant: the first 15m bearish break of any kind (BOS or CHoCH).
5. Stop = highest high from the touch to entry + 0.10·ATR4H (structure stop). Variant: leg top + 0.10·ATR4H.
6. Exits: 2R, 3R, and "leg low" (the 4H low made by the CHoCH move); time stop 5 days; cost 0.30; stop first in a bar.
Control: every 15m CHoCH in the same direction anywhere (no 4H context), with the same stop logic and exits.
Periods: EXTERNAL 2016–20 · IN-SAMPLE 2021→2026-03 · FORWARD 2026-04→2026-10-23.
Pass = mean R > 0 with 95% CI excluding 0 in EXTERNAL and FORWARD, and above the control in both.
Data: HistData 1m (EST→UTC) 2016→2026-09 + Dukascopy after; HistData misses ~28% of Mar–Jul 2023 minutes.

---
## Addendum 2026-10-25 (b) — same structure thesis on 1H → 3m (owner asked "what of the 1 hour")
Written BEFORE the test. Identical rules to addendum 2026-10-25 with HTF = 1H (UTC hours) and LTF = 3m; every window
kept in HTF bars: retrace within 60 HTF bars, LTF entry within 18 HTF bars of the touch, time stop 30 HTF bars;
buffers in 1H ATR. Control = every 3m CHoCH. Same periods and pass rule.

---
## Addendum 2026-10-26 — "Tokyo IFVG → New York goes to it → structure change → move" (owner's new strategy)
Owner (chat): trade only New York; if an inverse FVG forms in the Tokyo session, New York goes to that IFVG, structure
changes there, and it gives its move. Written BEFORE any test.
Definitions (New York time, gold 15m bars for the FVGs, 3m bars for the entry):
- FVG (15m, 3 candles): bull = low[i] > high[i-2], bear = high[i] < low[i-2]; size ≥ 0.25·ATR15. Kept 48 h.
- IFVG = a 15m CLOSE beyond the far side (bull FVG closes below its bottom → BEARISH IFVG = resistance; bear FVG closes
  above its top → BULLISH IFVG = support). Counted if that inversion close is in the TOKYO session 19:00–04:00 NY.
- New York session = 08:00–16:00 NY. An IFVG qualifies if price at 08:00 is outside it (not already inside).
H-A (magnet): share of qualifying IFVGs that New York touches (3m high/low reaches the near edge) vs a MIRROR control
  (same box size, same distance from the 08:00 price, on the other side). Pass: real touch rate > mirror, 95% CI.
H-B (trade, the owner's rule): first NY touch of the IFVG, then the first 3m CHoCH (pivots 3/3) in the IFVG direction
  before 16:00 → enter at that 3m close. Stop = extreme since the touch ± 0.10·ATR15; targets 2R and 3R; flat at 16:00;
  cost 0.30. Variant H-B0: limit entry at the near edge on the touch, stop beyond the far edge + 0.10·ATR15.
  At most one trade per day per direction (the IFVG touched first). Control = identical rules on the mirror boxes.
Periods: EXTERNAL 2016–20 · IN-SAMPLE 2021→2026-03 · FORWARD 2026-04→2026-10-23.
Pass = mean R > 0 with CI excluding 0 in EXTERNAL and FORWARD and above the mirror control.

---
## Addendum 2026-10-26 (b) — owner's two clock setups (St. Louis = Central Time), 5m chart. Written BEFORE testing.
Zones on 5m (all live up to 24 h):
- FVG: 3-candle gap ≥ 0.25·ATR5 (bull = demand, bear = supply). A 5m close through its far side turns it into an IFVG
  of the opposite type (live until a close through its other side).
- OB: when a 5m close breaks the last confirmed 5m swing high (pivots 3/3), the last down-close candle of the previous 10
  is a demand zone (its low → high); dies on a close below its low. Supply mirrored.
SETUP E (evening): window 7:00–8:00 PM CT. First touch of a live zone in the window → limit at the near edge (or the bar
  open if it opens inside); demand = buy, supply = sell. Stop = far edge ± 0.10·ATR5; target 2R; out after 60 min.
  One trade per window per direction. Sub-group: zones born inside the window.
SETUP N (New York): at the 9:00 AM CT bar open, if price is inside live demand zone(s) and no supply zone → buy at that
  open (supply mirrored; inside both → skip). Stop = far edge of the containing zone nearest to price ± 0.10·ATR5;
  target 2R; out after 60 min.
Cost 0.30 pt. Reported: win rate, mean R, and % per year at 1% risk per trade.
Controls: (1) the same rules at EVERY other hour of the day (is 7 PM / 9 AM special?); (2) placebo zones shifted
±2·ATR5 at random. Periods: EXT 2016–20 · IS 2021→2026-03 · FWD 2026-04→2026-10-23.
Pass = mean R > 0 with CI excluding 0 in EXT and FWD, above placebo, and the hour standing out from other hours.

---
## Addendum 2026-10-26 (c) — Claude's own plan: trend-following on 4H, wide stops, let winners run. Written BEFORE testing.
4H candles (17:00 NY grid), gold 2016-01 → 2026-10-23. Trend = close vs EMA100 and EMA100 vs its value 10 bars ago.
PLAN T (primary): LONG when a 4H close is above the highest high of the previous 20 4H bars AND trend is up (close >
EMA100, EMA100 rising); SHORT mirrored. Enter at that close. Initial stop = entry − 2·ATR4(14). Trailing exit = the lowest
low of the last 10 4H bars (only ever raised); also stop-and-reverse is NOT allowed — one position at a time.
Stops checked on 4H high/low (stop first). Cost 0.50 pt per trade (spread + slippage).
Controls: (1) same entries and exits WITHOUT the trend filter; (2) RANDOM entries — same number of trades, random bars
and random direction, same stop/trail rules (20 draws).
Report: trades, win rate, mean R, % per year at 0.5% risk per trade, worst drawdown (in R), per period.
Pass = mean R > 0 with 95% CI excluding 0 in EXT and IS, positive FWD, and above both controls.

---
## Addendum 2026-10-26 (d) — "after a fresh FVG the next candle goes $5 more (if not in a supply zone)". Written BEFORE testing.
3m and 5m. Fresh bull FVG at candle i (low[i] > high[i-2], gap ≥ 0.25·ATR); skip if close[i] sits inside a live bearish
FVG/IFVG (the "supply zone"); bear mirrored. Entry = close[i]. Measures: (1) next candle reaches entry + $5; (2) reaches
+$5 within 12 candles; (3) trade +$5 target with a −$5 stop, and with no stop (out after 12 candles); cost 0.30;
(4) losers: how far in profit they were first. Control: the same measures from EVERY candle close in the same direction
as that candle's body. Reported by year, because $5 is a different size in 2016 (gold ~$1,100) and 2026 (~$4,000).

---
## Addendum 2026-10-26 (e) — "5-step reversal" from an Instagram reel (Eliz FX Academy, owner's recording 10-24-2026)
Reel claim: HTF key level → liquidity sweep → market-structure shift → FVG/OB → buy at the 0.71 Fib retracement, stop below
the protected low, target the −0.27 extension. Written BEFORE testing. 15m execution, 4H key levels. BUY (SELL mirrored):
1. Key level: an unbroken confirmed 4H swing low (pivots 3/3, from the last 30 days).
2. Sweep: a 15m low goes below the last confirmed 15m swing low and that 15m candle CLOSES back above it; the sweep low is
   within 0.25·ATR4 of a 4H key level.
3. MSS: within 24 bars (6 h) a 15m close above the last confirmed 15m swing high. Leg = sweep low → highest high so far.
4. (Variant) the leg left a 15m bullish FVG.
5. Entry: limit at leg high − 0.71·leg, valid 48 bars after the MSS. Stop = sweep low − 0.10·ATR15. Target = leg high +
   0.27·leg (≈3.4R). Time stop 3 days. Cost 0.30. One setup at a time per direction.
Controls: the same steps 2–5 with NO key-level condition, and with a random-direction coin on the same entries.
Periods EXT 2016–20 · IS 2021→2026-03 · FWD 2026-04→2026-10-23. Pass as before.

---
## Addendum 2026-10-26 (f) — "pick the supply/demand zone that lines up with the volume-profile POC" (reel, owner's download)
Written BEFORE testing. Data has no real volume (spot gold) → profile = TIME AT PRICE from 5m bars (TPO proxy), bins 0.1·ATR1H.
1H structure, pivots 3/3. SELL (BUY mirrored): a 1H close breaks below the last confirmed 1H swing low (bearish break).
Leg = highest high since that swing low's bar → the break bar. POC = busiest price bin of the leg.
Supply zones of the leg: every 1H bearish FVG inside the leg + the OB (last up-close 1H candle at/just before the leg top).
POC zone = the zone containing the POC (none → no POC trade). Other zones = the rest (control 1).
Entry: limit at the zone's bottom edge, valid 120 1H bars after the break; cancelled if price closes above the leg top first.
Stop = zone top + 0.10·ATR1H. Targets 2R, 3R and the leg low; time stop 5 days; cost 0.30; 15m bars for fills/exits.
Control 2: a fake zone of the same size placed at a random price inside the leg.
Periods EXT 2016–20 · IS 2021→2026-03 · FWD 2026-04→2026-10-23. Pass: POC zones > 0 (CI) in EXT and FWD and above both controls.

---
## Addendum 2026-10-27 — "enter on the fair value gap created by the 8:30 AM New York candle". Written BEFORE testing.
5m bars, New York time. The 8:30 candle is the MIDDLE candle: bull FVG if low(8:35) > high(8:25), bear FVG if
high(8:35) < low(8:25); gap ≥ 0.25·ATR5. BUY on a bull FVG (SELL mirrored): limit at the gap's top (near edge) from 8:40,
valid until 11:00 NY. Stop = lowest low of the three candles − 0.10·ATR5. Targets 2R and 3R; flat at 12:00 NY. Cost 0.30.
Variant: the 9:30 NY candle (= 8:30 AM St. Louis / Central), entry valid 150 min, flat 210 min after it.
Variant: 15m candles (8:30 candle middle of 8:15/8:30/8:45).
Controls: the identical rule with the FVG made by every other 5m slot of the day (same 150/210-minute windows), and the
same trades on news vs non-news days is NOT tested (no calendar). Periods EXT 2016–20 · IS 2021→2026-03 · FWD 2026-04→10-23.
Pass: 8:30 mean R > 0 (CI) in EXT and FWD and in the top tier of all slots.

---
## Addendum 2026-10-27 (b) — ICT "Silver Bullet" (Instagram carousel goldhunter_ict, slide 6). Written BEFORE testing.
Windows (New York time): 03:00–04:00, 10:00–11:00, 14:00–15:00. 5m bars.
FVG: the FIRST 5m FVG (gap ≥ 0.25·ATR5) whose third candle closes inside the window. Bull FVG → BUY, bear → SELL.
Draw on liquidity (DOL) for a BUY = the nearest level above the entry among: previous day high (day = 18:00→17:00 NY),
today's high so far (since 18:00, up to the FVG's first candle), previous Asia (18:00–03:00) and London (03:00–08:00) highs
of today's day. SELL mirrored with lows. "Minimum framework": DOL must be ≥ $1.50 (15 gold pips) beyond the entry, else skip.
Entry: limit at the FVG near edge, valid until the window ends. Stop = FVG first candle low − 0.10·ATR5 (BUY).
Exits: (a) DOL target, (b) 2R. Flat 60 min after the window ends. Cost 0.30. One trade per window.
Controls: identical rule for every other 1-hour window of the day (24 windows, ranked) and the same FVG traded in the
opposite direction is NOT used (direction is part of the rule). Periods EXT 2016–20 · IS 2021→2026-03 · FWD 2026-04→10-23.
Pass: each Silver Bullet window mean R > 0 (CI) in EXT and FWD and in the top third of the 24 hours.
