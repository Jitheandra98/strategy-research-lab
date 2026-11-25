from pathlib import Path
import pandas as pd,numpy as np
P=Path(__file__).resolve().parents[1]/'first_reaction'
t=pd.read_csv(P/'SCENARIO_TRADES.csv',parse_dates=['time_utc','entry_utc','exit_utc'])
t=t[t.split=='VALIDATION'].sort_values(['entry_utc','event_id'])
accepted=[];free=pd.Timestamp.min.tz_localize('UTC')
for r in t.itertuples():
 if r.entry_utc>=free:accepted.append(r.Index);free=r.exit_utc
a=t.loc[accepted].copy();a.to_csv(P/'ACCOUNT_ACCEPTED_TRADES.csv',index=False)
rows=[]
for year in [2024,2025]:
 g=a[a.entry_utc.dt.year==year]
 for cost in [.3,.6]:
  pnl=(g.gross_pts.to_numpy()-cost)*10
  eq=np.r_[5000,5000+np.cumsum(pnl)]
  dd=np.maximum.accumulate(eq)-eq
  rows.append(dict(year=year,cost_dollars=cost*10,trades=len(g),net_dollars=pnl.sum(),ending_balance=eq[-1],return_pct=100*pnl.sum()/5000,max_closed_trade_drawdown=dd.max(),profitable_trade_pct=100*np.mean(pnl>0),target_hit_pct=100*np.mean(g.exit_type=='TARGET'),trading_days=g.entry_utc.dt.date.nunique()))
r=pd.DataFrame(rows);r.to_csv(P/'ACCOUNT_YEAR_RESULTS.csv',index=False);print(r.round(2).to_string(index=False))
text='''# $5,000 account: one-contract annual scenario\n\nOne MGC-equivalent contract ($10 per gold price point), fixed size; independent XAUUSD-feed reconstruction, not MGC execution data. Selected exploratory rule: wick penetrates at least half the zone then the arrival 15m candle closes back outside. Entry at next minute open, target 0.5 arrival ATR, stop 1 ATR, exit within 30 minutes. One position at a time; concurrent signals choose ascending event ID, a deterministic arbitrary tie-break. Calendar years shown use only available replay-attributed events; omitted video coverage means these are not exhaustive full-year backtests. Previous validation data is spent.\n\nEach calendar-year scenario starts anew with $5,000. Fees and slippage are assumed at $3 or $6 round trip, not verified broker charges. Margin eligibility, futures basis, contract rolls and intratrade account liquidation are not modeled. Drawdown below is based on closed trades and understates possible intratrade drawdown.\n\n'''
text+=r.round(2).to_csv(index=False)
text+='\n\nThese are historical scenario calculations, not forecasts. They apply to the selected completed-15m-candle setup, not an immediate-touch or 5m-entry strategy.\n'
(P/'ACCOUNT_YEAR_FINDINGS.md').write_text(text)
