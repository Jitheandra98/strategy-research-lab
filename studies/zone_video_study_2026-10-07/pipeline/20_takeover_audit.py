"""Reproduce the takeover provenance audit without modifying the original datasets."""
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
WORK=Path('/private/tmp/claude-501/-Users-jitheandrasubramaniam-Desktop-hey-hey/83c4d8f6-bdef-49fd-ad3c-a2670b98bde3/scratchpad/work')
OUT=ROOT/'audit'; OUT.mkdir(exist_ok=True)
e=pd.read_csv(ROOT/'EVENT_DATASET.csv',low_memory=False)
f=pd.read_csv(WORK/'frames_dated.csv',low_memory=False)
b=pd.read_pickle(WORK/'b15_ref.pkl')
direct=set((int(r.video),b.index[int(r.newest_idx)]) for r in f[f.newest_idx.notna()].itertuples())
e['sampled_frame_dates_arrival']=[(int(v),pd.Timestamp(t)) in direct for v,t in zip(e.video,e.time_utc)]
# This flag checks dated frame presence; it does NOT certify a visually identified candle/zone.
e['video_provenance']=np.where(e.sampled_frame_dates_arrival,'DATED_SAMPLED_FRAME','INFERRED_BETWEEN_FRAMES')
z=pd.read_csv(ROOT/'data/zone_visual_check.csv')
z['zone_id']=np.where(z.pane=='15m','Z15_','Z4_')+z.zid.astype(int).map(lambda n:f'{n:05d}')
vis=z.groupby('zone_id').hit.mean()
e['corrected_zone_edge_seen_rate']=e.zone_id.map(vis)
e.groupby(['split','video_provenance']).agg(events=('event_id','size'),R1=('R1','mean'),BRK=('BRK','mean')).to_csv(OUT/'provenance_summary.csv')
e[['event_id','zone_id','video','time_utc','video_provenance','zone_edge_seen_rate','corrected_zone_edge_seen_rate']].to_csv(OUT/'event_provenance.csv',index=False)
# Daily cluster bootstrap accounts for multiple zones touching on one candle and overlapping horizons.
rng=np.random.default_rng(20261007)
rows=[]
for (split,prov),g in e.groupby(['split','video_provenance']):
    g=g[g.R1.notna()].copy();g['day']=pd.to_datetime(g.time_utc).dt.date
    d=g.groupby('day').R1.agg(['sum','count']).to_numpy()
    draws=rng.integers(0,len(d),size=(2000,len(d)))
    rates=d[draws,0].sum(axis=1)/d[draws,1].sum(axis=1)
    rows.append(dict(split=split,provenance=prov,n=len(g),days=len(d),rate=g.R1.mean(),ci_lo=np.quantile(rates,.025),ci_hi=np.quantile(rates,.975)))
pd.DataFrame(rows).to_csv(OUT/'daily_bootstrap_R1.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
print('events',len(e),'zones',e.zone_id.nunique(),'distinct bar/direction',len(e[['bar','rd']].drop_duplicates()))
