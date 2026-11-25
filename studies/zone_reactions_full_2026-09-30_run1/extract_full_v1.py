from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess,json,csv,time
from PIL import Image,ImageOps
import numpy as np
ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/'run_config.json').read_text())
for name in ['frames','crops','ocr','screenshots','pipeline_logs']:(ROOT/name).mkdir(exist_ok=True)
times=list(range(0,int(cfg['duration_seconds']),5))
# Include the ending state without claiming the final frame's market candle closed.
if 13012 not in times:times.append(13012)
def frame(t):
 p=ROOT/'frames'/f'frame_{t:05d}.jpg'
 if p.exists():raise FileExistsError(p)
 cmd=[cfg['ffmpeg'],'-nostdin','-hide_banner','-loglevel','error','-ss',str(t),'-i',cfg['video'],'-frames:v','1','-q:v','2','-n',str(p)]
 r=subprocess.run(cmd,capture_output=True,text=True)
 if r.returncode: return {'second':t,'status':'error','detail':r.stderr}
 with Image.open(p) as im:
  # Both chart panes incl axes; remove most app title, taskbar and window chrome.
  crop=im.crop((50,75,2535,1320))
  crop.save(ROOT/'crops'/f'charts_{t:05d}.jpg',quality=93)
  thumb=np.asarray(ImageOps.grayscale(crop.resize((160,80))),dtype=np.float32)
 return {'second':t,'status':'ok','path':str(p),'crop':str(ROOT/'crops'/f'charts_{t:05d}.jpg'),'thumb':thumb}
rows=[];started=time.time()
with ThreadPoolExecutor(max_workers=6) as pool:
 jobs={pool.submit(frame,t):t for t in times}
 for n,future in enumerate(as_completed(jobs),1):
  rows.append(future.result())
  if n%100==0: print(f'{n}/{len(times)} frames in {time.time()-started:.1f}s',flush=True)
rows.sort(key=lambda r:r['second'])
scene=[];prev=None
for row in rows:
 if row['status']=='ok':
  row['sampled_change_score']=0 if prev is None else float(np.abs(row['thumb']-prev).mean())
  if row['sampled_change_score']>=12:scene.append(row['second'])
  prev=row.pop('thumb')
  row['recording_timestamp']=f"{row['second']//3600:02}:{row['second']//60%60:02}:{row['second']%60:02}"
with (ROOT/'frame_index.csv').open('x',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['second','recording_timestamp','status','path','crop','sampled_change_score','detail']);w.writeheader();w.writerows(rows)
with (ROOT/'ocr_inputs.txt').open('x') as f:f.write('\n'.join(r['path'] for r in rows if r['status']=='ok')+'\n')
with (ROOT/'scene_change_candidates.json').open('x') as f:json.dump({'method':'mean absolute grayscale difference between consecutive 5-second chart crops at160x80; candidates, not all-frame scene detection','threshold':12,'seconds':scene},f,indent=2)
print(f'COMPLETE {sum(r["status"]=="ok" for r in rows)}/{len(rows)}; scene candidates={len(scene)}; {time.time()-started:.1f}s',flush=True)
