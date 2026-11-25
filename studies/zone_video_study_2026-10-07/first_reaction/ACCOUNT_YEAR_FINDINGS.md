# $5,000 account: one-contract annual scenario

One MGC-equivalent contract ($10 per gold price point), fixed size; independent XAUUSD-feed reconstruction, not MGC execution data. Selected exploratory rule: wick penetrates at least half the zone then the arrival 15m candle closes back outside. Entry at next minute open, target 0.5 arrival ATR, stop 1 ATR, exit within 30 minutes. One position at a time; concurrent signals choose ascending event ID, a deterministic arbitrary tie-break. Calendar years shown use only available replay-attributed events; omitted video coverage means these are not exhaustive full-year backtests. Previous validation data is spent.

Each calendar-year scenario starts anew with $5,000. Fees and slippage are assumed at $3 or $6 round trip, not verified broker charges. Margin eligibility, futures basis, contract rolls and intratrade account liquidation are not modeled. Drawdown below is based on closed trades and understates possible intratrade drawdown.

year,cost_dollars,trades,net_dollars,ending_balance,return_pct,max_closed_trade_drawdown,profitable_trade_pct,target_hit_pct,trading_days
2024,3.0,310,-1510.86,3489.14,-30.22,1695.07,59.35,57.42,168
2024,6.0,310,-2440.86,2559.14,-48.82,2562.5,58.39,57.42,168
2025,3.0,707,-4193.6,806.4,-83.87,4598.97,59.55,54.74,227
2025,6.0,707,-6314.6,-1314.6,-126.29,6551.97,58.84,54.74,227


These are historical scenario calculations, not forecasts. They apply to the selected completed-15m-candle setup, not an immediate-touch or 5m-entry strategy.
