"""Merge full-image OCR with accurate axis-strip OCR without overwriting inputs."""
from pathlib import Path
import json,csv

r=Path(__file__).resolve().parent
frames=sorted((r/'frames').glob('frame_*.jpg'))
offsets={}
for name in ['axis_crop_index.csv','scene_axis_crop_index.csv']:
    with (r/name).open() as f:
        offsets.update({z['frame']:z for z in csv.DictReader(f)})
missing=[p.stem for p in frames if not (r/'ocr_fast'/f'{p.stem}.json').exists() or not (r/'ocr_axes'/f'{p.stem}.json').exists()]
if missing:raise SystemExit(f'Waiting for OCR: {len(missing)} frames; no merged output written')
dest=r/'ocr_merged'
dest.mkdir(exist_ok=False)
counts={'full_accurate':0,'fast_plus_accurate_axes':0,'frames':len(frames)}
for p in frames:
    accurate=r/'ocr'/f'{p.stem}.json'
    fallback=r/'ocr_fast'/accurate.name
    chosen=accurate if accurate.exists() else fallback
    d=json.loads(chosen.read_text())
    axis_file=r/'ocr_axes'/accurate.name
    a=json.loads(axis_file.read_text())
    off=[int(offsets[p.stem][k]) for k in ['left_offset','right_offset']]
    # Keep all full-accurate OCR when available. For fast OCR remove the two
    # axis strips, retaining titles/candle text elsewhere, then add accurate OCR.
    if not accurate.exists():
        d['items']=[v for v in d['items'] if not any(x<=v['x']+v['w']/2<x+300 for x in off)]
        for v in a['items']:
            pane=0 if v['x']+v['w']/2<300 else 1
            if v['x']<300<v['x']+v['w']:continue
            q=dict(v);q['x']=v['x']-pane*300+off[pane];q['origin']='accurate_axis_crop'
            d['items'].append(q)
        method='fast_plus_accurate_axes'
    else:method='full_accurate'
    counts[method]+=1
    d.update(path=str(p),method=method,source_ocr_file=str(chosen),axis_ocr_file=str(axis_file),width=2560,height=1440)
    with (dest/accurate.name).open('x') as f:json.dump(d,f)
with (r/'ocr_merge_summary.json').open('x') as f:json.dump(counts,f,indent=2)
print(counts)
