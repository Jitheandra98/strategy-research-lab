"""Add numbered outlines to copies of reviewed screenshots; preserve originals."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,textwrap

r=Path(__file__).resolve().parent
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',30)
small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',25)
examples=[
 (480,'01_supply_before_crossing','00:08:00 | Existing 4H supply before the crossing',[(1314,109,2448,218)],
  ['1: The outlined 4H supply band is visible before price later rises above it (approximately 4111–4134).',
   'Axis quote: 4086.7 on 4H, 4086.3 on 5M. The two panes can update slightly apart.',
   'Compare 00:08:45 and 00:09:25. Approximate band geometry is not an executable entry.']),
 (525,'02_crossing_local_continuation','00:08:45 | Price above the earlier supply band',[(1317,175,1881,483),(510,190,767,515)],
  ['1: The displayed quote is 4153.9, above the supply band visible at 00:08:00.',
   '2: The 5M ascent creates new local zones. They cannot retrospectively predict the ascent that created them.',
   'A crossing alone does not certify two closed 5M acceptance bars or a valid H2 retest.']),
 (565,'03_return_and_failure','00:09:25 | Return into the earlier 4H area; 5M breakdown',[(1705,252,1870,388),(660,405,768,1070)],
  ['1: The quote returns to 4128.9, inside the approximate earlier 4111–4134 area.',
   '2: The local recovery fails and 5M trades beneath several recently drawn zones.',
   'This motivates cancellation rules after a failed reclaim. It does not establish a winning short fill.']),
 (7200,'04_reversal_meets_supply','02:00:00 | Local rally reaches a 4H supply area',[(1715,555,2447,732),(502,202,766,1080)],
  ['1: Price 4643.8 lies inside a broad outlined 4H supply region, approximately 4630–4672.',
   '2: A substantial 5M rally has already occurred while the 4H EMA still declines.',
   'Early reversal and late buying into supply are different decisions. An absolute trend veto needs testing.']),
 (9300,'05_failed_rebound','02:35:00 | Rebound failure and fresh lower prices',[(538,416,685,566),(665,555,769,1150)],
  ['1: A local rebound stalls around 4075–4081 under/near supply and a declining EMA.',
   '2: Price subsequently trades at 4048.3; earlier buy labels remain visible on the chart.',
   'Visible labels and outcome badges are comparison material, not verified orders or P&L.']),
 (10800,'06_pullback_inside_advance','03:00:00 | A pullback within a larger advance',[(478,527,711,674),(575,221,773,422)],
  ['1: After advancing above 4320, the 5M chart probes roughly 4286 near a green zone, then recovers.',
   '2: Price is 4310.0, approaching local supply again. Both the pullback and the nearby obstacle matter.',
   'Test structural versus trigger-candle stops. This still does not reveal which stop would survive a real fill.']),
 (11400,'07_second_probe','03:10:00 | A second downside probe precedes recovery',[(515,776,624,1195),(662,202,769,722)],
  ['1: Two probes near 4512 and 4508 appear before the recovery. The first low was not the final low.',
   '2: The later advance reaches 4565.5. This motivates requiring a completed reclaim and local structure break.',
   'The full H1 trigger, its availability and resulting R remain unverified from these pixels.']),
 (13010,'08_censored_ending','03:36:50 | Unresolved final signal and a changed screen state',[(486,985,660,1250),(2048,1230,2422,1310)],
  ['1: A final buy annotation sits near price 4188.6; the recording supplies no complete future outcome window.',
   '2: The right tooltip is over empty future space. It is not the current market-bar timestamp.',
   'The replay watermark is absent and a candle countdown is visible. Keep this ending separate and censored.'])
]
for t,name,title,boxes,notes in examples:
    im=Image.open(r/'frames'/f'frame_{t:05}.jpg').convert('RGB')
    canvas=Image.new('RGB',(2560,1650),'#f7f9fc');canvas.paste(im,(0,0));d=ImageDraw.Draw(canvas)
    for i,b in enumerate(boxes,1):
        d.rectangle(b,outline='#ffdf57',width=5)
        x,y=b[:2];d.rectangle((x,y,x+40,y+39),fill='#ffdf57');d.text((x+10,y+2),str(i),font=font,fill='black')
    d.text((36,1457),title,font=font,fill='#152b42')
    for i,n in enumerate(notes):d.text((36,1506+i*40),n,font=small,fill='#263e52')
    with (r/'screenshots'/f'{name}.jpg').open('xb') as f:canvas.save(f,format='JPEG',quality=95)

events=[]
specs=[
 (480,565,4128.9,'crossing_then_return','Supply band 4111–4134 visible at 480s; quote above it at 525s, back inside at 565s. Local 5M breakdown.','supply_band_kind_unverified',4111,4134,None,None,'03_return_and_failure'),
 (7200,7200,4643.8,'local_rally_into_4h_supply','Local rally against falling 4H EMA; price reaches an outlined 4H region. New 5M zones cannot be backdated.','supply_OB_visual',4630,4672,None,None,'04_reversal_meets_supply'),
 (9300,9300,4048.3,'failed_local_rebound','Local 4075–4081 rebound fails before quote 4048.3; both panes show a broad decline.','5m_supply_visual',None,None,4075,4081,'05_failed_rebound'),
 (10800,10800,4310.0,'pullback_and_recovery','Advance above 4320; probe about 4286 near green band; recovery toward local supply.','5m_demand_visual',None,None,4270,4286,'06_pullback_inside_advance'),
 (11400,11400,4565.5,'second_probe_then_recovery','Probes around 4512 and 4508 precede later rally; large 4H green band below/at the probes.','4h_demand_visual',4417,4513,None,None,'07_second_probe'),
 (13010,13012,4188.6,'right_censored_final_signal','Final buy label has no full future outcome window; ending screen differs from replay and tooltips are not bar times.','unverified',None,None,None,None,'08_censored_ending')
]
for j,(a,b,q,kind,note,zt,l4,u4,l5,u5,shot) in enumerate(specs,1):
    e=dict(event_id=f'ME{j:03}',event_source='manual_visual_review',video_start_seconds=a,video_end_seconds=b,recording_timestamp=f'{a//3600:02}:{a//60%60:02}:{a%60:02}',market_datetime='',price=q,pane_id='both',screen_track_id='',zone_observation_id='',zone_4h_low_estimate=l4,zone_4h_high_estimate=u4,zone_5m_low_estimate=l5,zone_5m_high_estimate=u5,zone_type=zt,reaction_type=kind,interpretation='descriptive pattern; not a verified strategy trade',candle_behavior=note,session='unverified',trend='qualitative only; see notes',volatility='unmeasured',volume='unverified',indicator_signal_generated='historical labels visible; exact generation time unverified',setup_grade='U',verification_status='manual_descriptive_review_only',censoring_reason='market chronology, raw OHLC, exact trigger and fill path unavailable',outcome='not_evaluable',frame_before=str(r/'frames'/f'frame_{a:05}.jpg'),frame_after=str(r/'frames'/f'frame_{b:05}.jpg'),annotated_screenshot=str(r/'screenshots'/f'{shot}.jpg'),win='',net_R='',notes=note+' All manually read zone bounds are approximate, not tick-accurate.')
    for h in [5,15,30,60]:e[f'mfe_{h}m_points']='';e[f'mae_{h}m_points']=''
    events.append(e)
with (r/'manual_events.json').open('x') as f:json.dump(events,f,indent=2)
print('Created 8 annotated screenshots and 6 manual descriptive events')
