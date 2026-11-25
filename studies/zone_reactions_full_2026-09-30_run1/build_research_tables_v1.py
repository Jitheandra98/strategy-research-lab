"""Derive auditable screen observations. Does NOT create market-bar backtests."""
from pathlib import Path
import pandas as pd
import numpy as np
import json,csv,re,hashlib

r=Path(__file__).resolve().parent
def save_csv(name,df):
    with (r/name).open('x',newline='') as f:df.to_csv(f,index=False,float_format='%.4f')
def timestamp(t):return f'{int(t)//3600:02}:{int(t)//60%60:02}:{int(t)%60:02}'

p=pd.read_csv(r/'fullspan_panes.csv');z=pd.read_csv(r/'fullspan_zones.csv')
p['recording_timestamp']=p.video_pts_seconds.map(timestamp)
p['market_datetime']=''
p['market_datetime_status']='unverified; chart tooltip and recording time are not bar time'
p['quote_axis_check']=np.where(p.price.notna() & p.axis_model.notna() & (p.quote_axis_difference_points.abs()<=np.maximum(.5,2*p.quote_axis_uncertainty_points)),'consistent','missing_or_inconsistent')
save_csv('pane_observations.csv',p)
quotes={(v.video_pts_seconds,v.pane_id):v for v in p.itertuples()}
z=z.sort_values(['video_pts_seconds','pane_id','color_family','top_price_estimate']).reset_index(drop=True)
z['zone_observation_id']=[f'ZO{i+1:06}' for i in range(len(z))]
z['recording_timestamp']=z.video_pts_seconds.map(timestamp)
z['screen_track_id']=''
z['track_identity_status']='provisional geometry match, not source-engine ID'
z['source_birth_market_datetime']=''
z['source_availability_market_datetime']=''
z['source_lifecycle_state']='unknown'
z['cohort']='unresolved_source_kind_on_'+z.host_timeframe+'_host'
z['quote_price']=np.nan;z['quote_relation']='unavailable'
tracks={};seq=0
events=[]

def relation(price,lo,hi,err):
    if price<lo-err:return 'below'
    if price>hi+err:return 'above'
    if lo+err<price<hi-err:return 'inside'
    return 'boundary_uncertain'

for i,v in z.iterrows():
    t=int(v.video_pts_seconds);lo=v.bottom_price_estimate;hi=v.top_price_estimate
    if pd.isna(lo) or pd.isna(hi):continue
    err=max(.1,float(v.price_uncertainty_points))
    candidates=[]
    for k,a in tracks.items():
        if a['pane']!=v.pane_id or a['family']!=v.color_family or not 0<t-a['last']<=10:continue
        tol=max(.4,err+a['error'])
        # Bound matching to original geometry. Never chain drifting bounds.
        distance=max(abs(lo-a['low']),abs(hi-a['high']))
        if distance<=tol and .70<(hi-lo)/(a['high']-a['low'])<1.43:
            candidates.append((distance,k))
    if candidates:
        _,key=min(candidates)
        a=tracks[key]
    else:
        seq+=1;key=f'ST{seq:05}'
        a=dict(pane=v.pane_id,family=v.color_family,low=lo,high=hi,error=err,first=t,last=t,n=0,relation=None,rel_time=None,prev_quote=None,observations=[],ambiguous_matches=0)
        tracks[key]=a
    if len(candidates)>1:a['ambiguous_matches']+=1
    a['last']=t;a['n']+=1;a['observations'].append(v.zone_observation_id)
    z.at[i,'screen_track_id']=key
    q=quotes.get((t,v.pane_id))
    if q is None or q.quote_axis_check!='consistent':continue
    price=float(q.price)
    rel=relation(price,a['low'],a['high'],max(err,a['error']))
    z.at[i,'quote_price']=price;z.at[i,'quote_relation']=rel
    if rel=='boundary_uncertain':continue
    if a['relation'] is not None and a['relation']!=rel and t-a['rel_time']<=10:
        fr=a['relation']
        expected='above' if v.direction_candidate=='demand' else 'below'
        opposite='below' if expected=='above' else 'above'
        label='sampled_'+fr+'_to_'+rel
        interpretation='screen_position_transition_only'
        if fr==expected and rel=='inside':interpretation='possible_contact'
        elif fr=='inside' and rel==expected:interpretation='possible_rejection'
        elif rel==opposite:interpretation='possible_crossing'
        elif fr==opposite and rel=='inside':interpretation='possible_return'
        e=dict(event_id=f'MC{len(events)+1:05}',event_source='machine_sampled_quote_transition',video_start_seconds=a['rel_time'],video_end_seconds=t,recording_timestamp=timestamp(t),market_datetime='',price=price,prior_sample_price=a['prev_quote'],pane_id=v.pane_id,screen_track_id=key,zone_observation_id=v.zone_observation_id,zone_low_estimate=a['low'],zone_high_estimate=a['high'],zone_4h_low_estimate=a['low'] if v.host_timeframe=='4h' else '',zone_4h_high_estimate=a['high'] if v.host_timeframe=='4h' else '',zone_5m_low_estimate=a['low'] if v.host_timeframe=='5m' else '',zone_5m_high_estimate=a['high'] if v.host_timeframe=='5m' else '',zone_type=v.zone_type_candidate,reaction_type=label,interpretation=interpretation,candle_behavior='unverified',session='unverified',trend='unverified',volatility='unverified',volume='unverified',indicator_signal_generated='unverified; visible historical labels are not signal birth',setup_grade='U',verification_status='candidate_requires_manual_review',censoring_reason='market clock, OHLC, zone identity and intrabar path unverified',outcome='not_evaluable',geometry_confidence=v.geometry_confidence,frame_before=str(r/'frames'/f'frame_{a["rel_time"]:05}.jpg'),frame_after=v.frame_file)
        for horizon in [5,15,30,60]:e[f'mfe_{horizon}m_points']='';e[f'mae_{horizon}m_points']=''
        e.update(win='',net_R='',notes='No touch/rejection/sweep or profitable entry is certified by sampled quote movement. A boundary can be crossed between samples without an observed inside quote.')
        events.append(e)
    a['relation']=rel;a['rel_time']=t;a['prev_quote']=price

save_csv('zones.csv',z)
tr=[]
for key,a in tracks.items():
    tr.append(dict(screen_track_id=key,pane_id=a['pane'],color_family=a['family'],first_seen_recording_seconds=a['first'],last_seen_recording_seconds=a['last'],observations=a['n'],frozen_low_estimate=a['low'],frozen_high_estimate=a['high'],price_uncertainty_points=a['error'],ambiguous_match_frames=a['ambiguous_matches'],source_engine_id='',identity_status='provisional geometry match only; disappearance is not proof of invalidation'))
save_csv('zone_tracks.csv',pd.DataFrame(tr))
manual_path=r/'manual_events.json'
if manual_path.exists():events.extend(json.loads(manual_path.read_text()))
edf=pd.DataFrame(events)
save_csv('events.csv',edf)

# Counts describe captured screen candidates. They are NOT trade frequency.
counts=(edf.groupby(['event_source','reaction_type'],dropna=False).size().rename('count').reset_index())
counts['population']='screen observations; not independent market setups'
save_csv('pattern_counts.csv',counts)
metrics=[]
for h in ['H1_rejection','H2_break_retest','H3_oscillation_veto']:
    for metric in ['frequency_per_market_day','win_rate','mean_net_R','MFE_MAE_5_15_30_60m','best_stop','best_target','session_bias']:
        metrics.append(dict(hypothesis=h,metric=metric,value='',status='not_estimable',reason='Verified market bars, chronological zone identities and executable trade ledger unavailable'))
save_csv('performance_metrics.csv',pd.DataFrame(metrics))

fi=pd.concat([pd.read_csv(r/'frame_index.csv'),pd.read_csv(r/'scene_frame_index.csv')],ignore_index=True).sort_values('second')
fi['sampling_class']=np.where(fi.reason.notna(),'scene_refinement','baseline_5_seconds')
fi['status']=fi.status.fillna('ok')
fi['ocr_file']=fi.second.map(lambda t:str(r/'ocr_merged'/f'frame_{int(t):05}.json'))
save_csv('all_frame_index.csv',fi)
bins=pd.cut(p.video_pts_seconds,range(0,14401,1800),right=False)
cov=[]
for interval,pp in p.groupby(bins,observed=True):
    cov.append(dict(recording_start=timestamp(interval.left),recording_end=timestamp(min(interval.right,13013)),frames=pp.video_pts_seconds.nunique(),panes=len(pp),calibrated_panes=int((pp.status=='calibrated').sum()),quote_panes=int(pp.price.notna().sum()),consistent_quote_panes=int((pp.quote_axis_check=='consistent').sum())))
save_csv('coverage_by_interval.csv',pd.DataFrame(cov))
quality=dict(baseline_frames=2604,scene_refinement_frames=544,total_frames=int(fi.second.nunique()),frame_gap_max_seconds=int(fi.second.diff().max()),video_seconds=13013.12,last_sample_second=13012,panes=len(p),calibrated_panes=int((p.status=='calibrated').sum()),quote_panes=int(p.price.notna().sum()),consistent_quote_panes=int((p.quote_axis_check=='consistent').sum()),zone_observations=len(z),provisional_zone_tracks=len(tr),machine_transition_candidates=int((edf.event_source=='machine_sampled_quote_transition').sum()),manual_descriptive_events=int((edf.event_source=='manual_visual_review').sum()),backtest_evaluable_events=0,zone_geometry_counts=z.geometry_confidence.value_counts().to_dict(),ocr_merge=json.loads((r/'ocr_merge_summary.json').read_text()))
with (r/'quality_summary.json').open('x') as f:json.dump(quality,f,indent=2)
print(json.dumps(quality,indent=2))
