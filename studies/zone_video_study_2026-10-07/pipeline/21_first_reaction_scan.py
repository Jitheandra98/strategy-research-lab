"""Exploratory first-reaction scan. All entries occur at next minute open after arrival 15m close.
Existing splits are spent: discovery selects, V3 checks robustness, not fresh validation.
Independent-feed 1m reconstruction; missing minutes excluded; stop wins same-minute ties.
"""
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'first_reaction';OUT.mkdir(exist_ok=True)
W=Path('/private/tmp/claude-501/-Users-jitheandrasubramaniam-Desktop-hey-hey/83c4d8f6-bdef-49fd-ad3c-a2670b98bde3/scratchpad/work')
e=pd.read_csv(ROOT/'EVENT_DATASET.csv',low_memory=False)
e['time_utc']=pd.to_datetime(e.time_utc,utc=True)
m=pd.read_pickle(W/'merged_1m.pkl').sort_index();m=m[~m.index.duplicated()]
t=m.index.asi8;sig=(e.time_utc+pd.Timedelta(minutes=15)).astype('int64').to_numpy();idx=np.searchsorted(t,sig)
valid=(idx<len(t)-30);ix=np.minimum(idx,len(t)-31)
valid &= t[ix]==sig
future=ix[:,None]+np.arange(30)[None,:]
valid &= ((t[future]-sig[:,None])==np.arange(30)[None,:]*60_000_000_000).all(axis=1)
e=e[valid].copy().reset_index(drop=True);ix=ix[valid];future=future[valid]
a=e.atr.to_numpy();rd=e.rd.to_numpy();entry=m.open.to_numpy()[ix]
h=m.high.to_numpy()[future];l=m.low.to_numpy()[future];cl=m.close.to_numpy()[future]
fav=np.where(rd[:,None]==1,h-entry[:,None],entry[:,None]-l)/a[:,None]
adv=np.where(rd[:,None]==1,entry[:,None]-l,h-entry[:,None])/a[:,None]
mark=rd[:,None]*(cl-entry[:,None])/a[:,None]
# Discovery-derived cuts only, fixed before robustness scoring.
d=e[e.split=='DISCOVERY']
q={f:d[f].quantile([1/3,2/3]).to_list() for f in ['height_atr','accel_ratio','rng_last3_atr','compress5_atr','velocity_atr_per_bar']}
masks={'ALL':np.ones(len(e),bool),'ARRIVAL':e.interaction.eq('ARRIVAL').to_numpy(),'FLIP':e.interaction.eq('FLIP').to_numpy(),
'close_back_outside':e.close_loc.eq('OUTSIDE_NEAR').to_numpy(),'shallow_wick':(e.pen_frac<=.25).to_numpy(),
'deep_wick_reclaim':((e.pen_frac>=.5)&e.close_loc.eq('OUTSIDE_NEAR')).to_numpy(),
'body_reaction':((e.arr_dir_with_reaction==1)&(e.arr_body_frac>=.6)).to_numpy(),
'with_15m_structure':e.struct15_with.eq(1).to_numpy(),'with_4h_trend':e.trend4_with.eq(1).to_numpy(),
'first_arrival':((e.interaction=='ARRIVAL')&(e.prior_arrivals==0)).to_numpy(),
'multiple_toward':(e.consec_toward>=3).to_numpy(),'4h_zone':e.universe.eq('Z4').to_numpy()}
for f,cuts in q.items():
 masks[f+'_low']=(e[f]<=cuts[0]).to_numpy();masks[f+'_high']=(e[f]>cuts[1]).to_numpy()
for x,y in [('close_back_outside','accel_ratio_low'),('close_back_outside','with_15m_structure'),('shallow_wick','compress5_atr_low'),('deep_wick_reclaim','with_4h_trend'),('body_reaction','rng_last3_atr_high'),('first_arrival','velocity_atr_per_bar_low')]: masks[x+' & '+y]=masks[x]&masks[y]
rows=[];details={}
for target in [.25,.5,.75]:
 for stop in [.5,1.0]:
  for hold in [5,15,30]:
   hs=adv[:,:hold]>=stop;ht=fav[:,:hold]>=target
   fs=np.where(hs.any(axis=1),hs.argmax(axis=1),hold);ft=np.where(ht.any(axis=1),ht.argmax(axis=1),hold)
   gross=np.where((fs<hold)&(fs<=ft),-stop,np.where(ft<hold,target,mark[:,hold-1]))*a
   status=np.where((fs<hold)&(fs<=ft),'STOP',np.where(ft<hold,'TARGET','TIME'))
   for name,mask in masks.items():
    # One signal per candle/direction within each condition, prevents stacked boxes multiplying same trade.
    chosen=e[mask].drop_duplicates(['time_utc','rd']).index.to_numpy()
    for split in ['DISCOVERY','VALIDATION']:
     use=chosen[e.loc[chosen,'split'].to_numpy()==split]
     if len(use)<40:continue
     net=gross[use]-.3
     rows.append(dict(pattern=name,target_atr=target,stop_atr=stop,hold_min=hold,split=split,n=len(use),target_rate=(status[use]=='TARGET').mean(),stop_rate=(status[use]=='STOP').mean(),net_pts=net.mean(),net_pts_cost06=(gross[use]-.6).mean(),net_R=(net/(stop*a[use])).mean(),median_pts=np.median(net)))
   details[(target,stop,hold)]=(gross,status)
# Save trade paths for the selected illustrative scenario; selection was based on discovery.
gross,status=details[(.5,1.0,30)]
chosen=e[masks['deep_wick_reclaim']].drop_duplicates(['time_utc','rd']).index.to_numpy()
hs=adv>=1.0;ht=fav>=.5
fs=np.where(hs.any(axis=1),hs.argmax(axis=1),30);ft=np.where(ht.any(axis=1),ht.argmax(axis=1),30)
exit_offset=np.where((fs<30)&(fs<=ft),fs,np.where(ft<30,ft,29))
tr=e.loc[chosen,['event_id','split','video','time_utc','video_ts_arrival','atr','rd']].copy()
tr['entry_utc']=tr.time_utc+pd.Timedelta(minutes=15)
tr['exit_utc']=tr.entry_utc+pd.to_timedelta(exit_offset[chosen]+1,unit='min')
tr['gross_pts']=gross[chosen];tr['net_pts']=gross[chosen]-.3;tr['exit_type']=status[chosen]
tr.to_csv(OUT/'SCENARIO_TRADES.csv',index=False)
r=pd.DataFrame(rows);r.to_csv(OUT/'ALL_RESULTS.csv',index=False)
sel=r[(r.split=='DISCOVERY')&(r.n>=80)&(r.pattern!='ALL')].sort_values('net_R',ascending=False).drop_duplicates('pattern').head(10)
keys=['pattern','target_atr','stop_atr','hold_min'];rank=sel.merge(r[r.split=='VALIDATION'],on=keys,suffixes=('_discovery','_robustness'))
rng=np.random.default_rng(7);examples=[]
for k,row in rank.iterrows():
 gross,status=details[(row.target_atr,row.stop_atr,row.hold_min)]
 mask=masks[row.pattern];chosen=e[mask].drop_duplicates(['time_utc','rd']).index.to_numpy();use=chosen[e.loc[chosen,'split'].to_numpy()=='VALIDATION']
 tmp=pd.DataFrame({'day':e.loc[use,'time_utc'].dt.date.to_numpy(),'net':gross[use]-.3})
 daily=tmp.groupby('day').net.agg(['sum','count']).to_numpy();draw=rng.integers(0,len(daily),(1000,len(daily)))
 means=daily[draw,0].sum(1)/daily[draw,1].sum(1)
 rank.loc[k,'daily_ci_lo_pts']=np.quantile(means,.025);rank.loc[k,'daily_ci_hi_pts']=np.quantile(means,.975)
 for outcome in ['TARGET','STOP']:
  uu=use[status[use]==outcome]
  for j in uu[:2]:
   er=e.loc[j];examples.append(dict(pattern=row.pattern,event_id=er.event_id,video=er.video,video_ts=er.video_ts_arrival,chart_time=er.chart_time_ny,outcome=outcome,net_pts=gross[j]-.3))
rank.to_csv(OUT/'TOP_PATTERNS.csv',index=False);pd.DataFrame(examples).to_csv(OUT/'EXAMPLES.csv',index=False)
print('eligible events',len(e),'excluded',len(valid)-valid.sum(),'conditions',len(masks),'configurations',18)
print(rank[['pattern','n_discovery','net_R_discovery','n_robustness','net_R_robustness','net_pts_robustness','daily_ci_lo_pts','daily_ci_hi_pts']].round(4).to_string(index=False))
text=f'''# First-reaction pattern scan — 2026-10-07\n\nExploratory results, using reconstructed zone events and independent-feed one-minute bars. All existing splits were previously inspected. V3 is a robustness check, not an untouched holdout.\n\nEntry: next minute open after the arrival 15m candle closes. This tests reactions still available after a completed candle; it cannot settle immediate-touch scalping. Targets: 0.25/0.5/0.75 arrival ATR; stops: 0.5/1 ATR; holding limits: 5/15/30 minutes. Costs: 0.30 and 0.60 points per trade. Same-minute target/stop ties lose. No missing minute is filled. These settings are research choices, not the user's exact trade rules.\n\nEligible event rows: {len(e)}; excluded for missing execution window: {int(len(valid)-valid.sum())}. {len(masks)} conditions × 18 configurations were screened on discovery only. Multiple zones on the same candle/direction are counted once within each condition. Separate trades still overlap; these are signal-level results, not portfolio returns. Daily bootstrap intervals measure dependence sensitivity but do not correct selection or prove significance.\n\nTop conditions selected by discovery net R (minimum 80 signals), one configuration per condition:\n\n'''
text+=rank[['pattern','target_atr','stop_atr','hold_min','n_discovery','net_R_discovery','n_robustness','net_R_robustness','net_pts_robustness','daily_ci_lo_pts','daily_ci_hi_pts']].round(4).to_csv(index=False)
text+='\n\nSee ALL_RESULTS.csv for every attempted condition/settings combination and EXAMPLES.csv for successes and failures. Zone identity and interpolated video timestamps retain the limitations documented in audit/TAKEOVER_AUDIT.md. A positive result must survive matched random-band controls, realistic execution, portfolio overlap constraints and new unseen data before becoming a trading recommendation.\n'
(OUT/'FIRST_REACTION_FINDINGS.md').write_text(text)
