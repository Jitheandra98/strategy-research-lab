"""Classify sampled zone-position transitions for the magnet hypothesis.

This is a screen-level descriptive layer. It intentionally does not infer
5M OHLC, source-engine lifecycle, fills, or profitability.
"""
from pathlib import Path
import pandas as pd
import numpy as np

r=Path(__file__).resolve().parent
events=pd.read_csv(r/'events.csv')
zones=pd.read_csv(r/'zones.csv',usecols=['zone_observation_id','color_family','direction_candidate','host_timeframe','zone_type_candidate','price_uncertainty_points'])
e=events[events.event_source=='machine_sampled_quote_transition'].copy()
e=e.merge(zones,left_on='zone_observation_id',right_on='zone_observation_id',how='left',suffixes=('','_zone'))

def side(row):
    x=row.reaction_type.replace('sampled_','')
    return x.split('_to_')

def classify(row):
    before,after=side(row)
    direction=row.direction_candidate
    if direction=='demand':
        mapping={
            ('above','inside'):'approach_touch',
            ('inside','above'):'proximal_rejection',
            ('inside','below'):'distal_crossing',
            ('below','inside'):'opposite_side_retest',
            ('below','above'):'full_traverse_rebound',
            ('above','below'):'full_traverse_down',
        }
    elif direction=='supply':
        mapping={
            ('below','inside'):'approach_touch',
            ('inside','below'):'proximal_rejection',
            ('inside','above'):'distal_crossing',
            ('above','inside'):'opposite_side_retest',
            ('above','below'):'full_traverse_rebound',
            ('below','above'):'full_traverse_up',
        }
    else:
        mapping={}
    return mapping.get((before,after),'unclassified')

e['magnet_phase']=e.apply(classify,axis=1)
e['direction_confidence']=e.direction_candidate.map(lambda v:'palette_candidate' if v in ['demand','supply'] else 'unresolved')
e['observation_status']='sampled_screen_transition_only'
e['market_datetime']=''
e['market_clock_horizon']='unavailable'
e['trade_outcome']='not_evaluable'
e['notes']='A 5-second/scene sample can skip the interior and multiple 5M candles; phase is descriptive, not OHLC confirmation.'

# Build a local, frame-observed visit index. Screen-track IDs remain
# provisional geometry matches, so this is for inspection rather than counts
# of independent economic events.
e=e.sort_values(['screen_track_id','video_start_seconds','event_id']).reset_index(drop=True)
e['provisional_visit_index']=0
e['revisit_flag']=False
e['sequence_after_previous']=''
for key,g in e.groupby('screen_track_id',sort=False):
    visit=0
    prior_phase=''
    for i,row in g.iterrows():
        phase=row.magnet_phase
        if phase in ('approach_touch','opposite_side_retest'):
            visit+=1
            e.at[i,'provisional_visit_index']=visit
            e.at[i,'revisit_flag']=visit>1
        else:
            e.at[i,'provisional_visit_index']=visit
        e.at[i,'sequence_after_previous']=prior_phase
        prior_phase=phase

fields=['event_id','event_source','video_start_seconds','video_end_seconds','recording_timestamp','pane_id','host_timeframe','screen_track_id','zone_observation_id','color_family','direction_candidate','direction_confidence','zone_type_candidate','magnet_phase','provisional_visit_index','revisit_flag','price','prior_sample_price','zone_low_estimate','zone_high_estimate','price_uncertainty_points','geometry_confidence','observation_status','market_datetime','market_clock_horizon','trade_outcome','frame_before','frame_after','sequence_after_previous','notes']
with (r/'magnet_events.csv').open('x') as f:
    e[fields].to_csv(f,index=False,float_format='%.4f')

counts=e.groupby(['host_timeframe','direction_candidate','magnet_phase'],dropna=False).size().rename('screen_transition_count').reset_index()
counts['interpretation']='descriptive screen count; not independent setup frequency'
with (r/'magnet_counts.csv').open('x') as f:
    counts.to_csv(f,index=False)

chains=[]
for key,g in e.groupby('screen_track_id',sort=False):
    g=g.sort_values('video_start_seconds')
    phases=list(g.magnet_phase)
    if len(g)>=2:
        chains.append(dict(screen_track_id=key,pane_id=g.pane_id.iloc[0],host_timeframe=g.host_timeframe.iloc[0],direction_candidate=g.direction_candidate.iloc[0],first_event_seconds=int(g.video_start_seconds.min()),last_event_seconds=int(g.video_end_seconds.max()),transition_count=len(g),phase_sequence=' > '.join(phases),revisit_count=int(g.revisit_flag.sum()),status='provisional screen chain'))
chains_df=pd.DataFrame(chains)
with (r/'magnet_chains.csv').open('x') as f:
    chains_df.to_csv(f,index=False)

manual=events[events.event_source=='manual_visual_review']
summary={
    'machine_screen_transitions':int(len(e)),
    'machine_tracks_with_two_or_more_transitions':int(len(chains_df)),
    'provisional_revisit_transitions':int(e.revisit_flag.sum()),
    'four_hour_transitions':int((e.host_timeframe=='4h').sum()),
    'five_minute_transitions':int((e.host_timeframe=='5m').sum()),
    'manual_descriptive_episodes':int(len(manual)),
    'outcome_metrics':'not_evaluable_without replay-matched OHLCV and market chronology',
}
with (r/'magnet_summary.json').open('x') as f:
    import json
    json.dump(summary,f,indent=2)
print(json.dumps(summary,indent=2))

