from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,csv
from PIL import Image
r=Path(__file__).resolve().parent;cfg=json.loads((r/'run_config.json').read_text())
changes=json.loads((r/'scene_change_candidates.json').read_text())['seconds']
times=sorted({s for t in changes for s in range(t-4,t) if s>=0 and s%5 and not (r/'frames'/f'frame_{s:05d}.jpg').exists()})
def grab(t):
 p=r/'frames'/f'frame_{t:05d}.jpg'
 subprocess.run([cfg['ffmpeg'],'-nostdin','-hide_banner','-loglevel','error','-ss',str(t),'-i',cfg['video'],'-frames:v','1','-q:v','2','-n',str(p)],check=True)
 with Image.open(p) as im:im.crop((50,75,2535,1320)).save(r/'crops'/f'charts_{t:05d}.jpg',quality=93)
 return {'second':t,'recording_timestamp':f'{t//3600:02}:{t//60%60:02}:{t%60:02}','path':str(p),'reason':'one-second refinement before sampled visual-change candidate'}
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(grab,times))
with (r/'scene_frame_index.csv').open('x',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (r/'ocr_scene_inputs.txt').open('x') as f:f.write('\n'.join(x['path'] for x in rows)+'\n')
print('Scene-refinement frames:',len(rows),flush=True)
