# PROCESS TEST: run spec (written 2026-11-09, before any run)

The owner chose the defaults in ACCOUNT_SPEC.md §2 ("use your defaults"). This is a PROCESS TEST, because the strategy is not
qualified (ACCOUNT_SPEC §5). It has three jobs: check that the account engine obeys every limit, compare exits A/B/C as
mandate §5 requires, and show whether the account survives its limits. Passing any line here does not qualify the strategy.

## Account (ASSUMPTIONS: the owner said "use defaults")
- Start with $10,000 paper on 2012-01-03. Also run $2,000 with a $1,500 floor.
- Equity is marked to market (MTM) at every 5m close. MTM subtracts the round-trip cost from the moment a position opens.
- Floor $7,500: if MTM ≤ floor → forced exit at the next 5m open, status FAILED, run over.
- Drawdown: if MTM is ≥ 15 % below peak equity (the peak includes open profit) → forced exit, status FROZEN, no new trades.
- Daily loss: if MTM < 98 % of start-of-day equity → forced exit, HALT for the session.
- If several fire at once, the strictest wins: FAILED > FROZEN > HALT.
- Sizing: contracts = floor(1 % × min(realized, MTM) / risk per contract).
  Risk per contract = (|decision price − stop| + 0.2 pt slippage allowance + 0.3 pt cost) × $10.
  The decision price is the spike bar's close. 0 contracts → NO TRADE.
- Floor buffer: cut contracts until equity − contracts × (|decision − stop| + 0.4 + 0.3) × $10 ≥ floor + 2 % of equity.
- One position at a time on one instrument, so total open risk = per-trade risk (≤ 1 %, inside the 2 % cap). Correlated
  positions cannot occur.
- No partial exits (never tested), no stop widening, no averaging down. Size comes from equity only.

## Signals (unchanged from research/spike_follow_2026-11-08/SPEC.md, MAIN)
The day's first 30m bar starting 08:00–10:00 ET whose range is ≥ 2.5 × ATR(14, RMA) of the previous bar. Direction = bar
colour. Market entry at the next 30m open. Stop beyond the spike's starting extreme ± 0.1 × ATR.
The old study dropped signals whose next open was already beyond the stop. That used the next open before it existed, so
the engine keeps those signals and lets them stop out at once. The count is reported.

## Execution (5m bars inside each trade)
- Entry fill = the first 5m open of the next 30m bar. Slippage against the decision price is logged.
- Stop: a 5m bar that opens through the stop fills at that open; otherwise a touch fills at the stop. Either way, 0.2 pt
  of extra adverse slippage.
- Target (B, C) is a limit order. It fills at the target only if a 5m bar trades 0.1 pt through it. If one 5m bar touches
  both the stop and the target, the stop counts first.
- Time exit at 13:30 = close of the 13:25 5m bar.
- Forced exits (halt / freeze / floor): next 5m open, 0.2 pt slippage.
- Cost: 0.3 pt round trip per contract ($3), charged at exit.

## Exit policies (same entries, stops and limits)
A) hold to 13:30. B) target +1.0R, R = |entry fill − stop|. C) target +0.3R + 0.3 pt, which nets +0.3R after the base cost.
B and C fall back to the 13:30 exit.

## Chronological rule
Development = 2012–2019. Pick the policy with the highest mean net $ per trade at 1 MGC and base costs there.
Validation = 2020 → Sep 2026. Report the picked policy there once.

## Stress tests
- Cost 0.5 pt; stop slippage 0.4 pt; both together.
- Monte Carlo: 10,000 reshuffles of trade order per policy at 0.4 pt stop slippage. Report P(freeze), P(floor), and
  max-drawdown percentiles with no freeze applied. Each trade's worst open loss (5m closes) is used for the in-trade check.
- Random same-clock control: 20 random other days per trade, same direction, stop distance and exit policy.
- The $2,000 account.

## Forward-like check
MGC1! 5m from Sep 25 to Nov 6 2026, which this rule has never seen. Same engine, same three policies. It is about 15 trades,
so it checks the process on real futures bars. It is not evidence.

## Engine checks (the run is void if any fails)
- Replication: in 30m-path mode with 0 slippage and the old filter, the engine reproduces trades_main.csv (same days,
  directions and gross).
- No ENTER while FROZEN or FAILED. Risk at stake ≤ 1 % of equity at every ENTER.
- Final equity = start + the sum of the trades' net P&L.
- Every trade has one entry fill and one exit fill, logged apart from the decisions.

## Reported per policy (mandate §6)
Net return, max drawdown, profit factor, average net win and loss, total trading costs, survival status, and the
ACCOUNT_SPEC §3 gate (items 1–7).
