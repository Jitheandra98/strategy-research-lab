from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,csv
import numpy as np
from PIL import Image
from zone_parser_v1 import panes_from_image
r=Path(__file__).resolve().parent
(r/'axes_crops').mkdir(exist_ok=True);(r/'ocr_axes').mkdir(exist_ok=True)
def make(p):
 with Image.open(p) as im:
  spans=panes_from_image(np.asarray(im))
  if len(spans)!=2:return {'frame':p.stem,'status':'unsupported_layout'}
  canvas=Image.new('RGB',(600,im.height),'white')
  offsets=[]
  for i,(l,rt) in enumerate(spans):
   x=rt-300; offsets.append(x);canvas.paste(im.crop((x,0,rt,im.height)),(i*300,0))
  dest=r/'axes_crops'/p.name
  if dest.exists():raise FileExistsError(dest)
  canvas.save(dest,quality=96)
  return {'frame':p.stem,'status':'ok','left_offset':offsets[0],'right_offset':offsets[1],'path':str(dest)}
paths=sorted(p for p in (r/'frames').glob('frame_*.jpg') if not (r/'axes_crops'/p.name).exists())
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(make,paths))
with (r/'scene_axis_crop_index.csv').open('x',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['frame','status','left_offset','right_offset','path']);w.writeheader();w.writerows(rows)
with (r/'ocr_scene_axes_inputs.txt').open('x') as f:f.write('\n'.join(z['path'] for z in rows if z['status']=='ok')+'\n')
with (r/'ocr_scene_accurate_coarse_inputs.txt').open('x') as f:f.write('\n'.join(str(p) for p in paths if int(p.stem.split('_')[1])%30==0)+'\n')
print('Axis crops:',sum(z['status']=='ok' for z in rows),'/',len(rows),flush=True)
