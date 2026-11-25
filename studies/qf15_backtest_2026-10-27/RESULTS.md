# QF15 backtest — 2026-10-27
XAUUSD 15m, 2016-01 → 2026-09-24, script defaults, run unchanged via PineTS (synthetic volume).
Exits = script's own: SL 0.5 ATR14, TP1 1.5R, TP2 2.5R, TP3 nearest liquidity (else 4R), tracker 1ATR:1ATR; max hold 50 bars; cost 0.35 pt; 5m bars, stop-first.
Full tables: score.log. Code: run_qf15.py, score_qf15.py. Trades: scored_trades.pkl.

- MARKET entry (signal-bar close): negative in every period, same as RANDOM entries with the same exits (original v15 and ZONE_RULE alike).
- HP ★ vs normal and BUY vs SELL: no meaningful difference.
- CLAIMED (label "Entry" price filled at signal time): 91–94 % win. Not achievable: the label price is a median 1.17 ATR better than the price at signal time (it is the zone-contact close from earlier bars). The dashboard WR tracker uses this price, so its win rate is inflated the same way.
- LIMIT at the label price (2 h to fill): fills about half; still negative except 2025–26 TP1 (+0.13R ± 0.15, not distinguishable from zero).
Verdict: no edge found; not profitable as written.

## Entering at the ◆ PENDING signal (to actually get the label price) — score_pending.py / score_pending.log
~8,800 pendings (original) / ~9,600 (ZONE_RULE); ~38 % later become BUY/SELL, ~62 % are scratched.
A (market at pending + script scratch), B (stop/target only), C (limit at label price): all equal to RANDOM entries in every period.
H (only the pendings that later validated — needs hindsight): 64–68 % TP1 wins, positive. That gap is the whole illusion:
the good-looking trades are chosen after price has already moved. No way to fill there and keep the edge.

## Predicting which pendings win — predict_pending.py / predict.log
17 features known at the pending close (trend, momentum, range position, ATR regime, time, day range, liquidity distance, label gap).
Train 2016-20, test 2021-26. Boosting: AUC 0.78 on training years, 0.49-0.50 on unseen years (coin flip); its top-10 % picks
win 81 % in training, 34-41 % unseen (same as all pendings). Logistic: 0.49-0.50 unseen. No usable prediction.
