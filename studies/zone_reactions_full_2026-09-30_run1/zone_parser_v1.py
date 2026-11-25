#!/usr/bin/env python3
"""Conservative visual observations, NOT reconstructed OHLC or trade outcomes.

Reads original-size frame JPEGs and Apple Vision OCR JSON. All output creation
is exclusive. Colored rectangles are candidates until manual label/geometry
review. Recording seconds are not market minutes. No temporal interpolation.
"""
from __future__ import annotations
import argparse, csv, json, math, re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image

FAMILIES = {
    "green": ("demand", "FVG_or_imported_4H"),
    "red": ("supply", "FVG_or_imported_4H"),
    "blue": ("demand", "OB"),
    "pink": ("supply", "OB"),
}

def price_number(text):
    """Accept only standalone axis numbers; never silently repair digits."""
    t = text.strip().replace(" ", "").replace(",", "")
    if not re.fullmatch(r"\d{4}\.\d{1,2}", t): return None
    v = float(t)
    return v if 2000 <= v <= 9000 else None

def grouped(indices, max_gap=1):
    a = np.asarray(indices, dtype=int)
    if not len(a): return []
    return np.split(a, np.where(np.diff(a)>max_gap)[0]+1)

def panes_from_image(im):
    h,w = im.shape[:2]
    white = np.mean(np.all(im[int(.125*h):int(.867*h),:,:3] > 170, axis=2),axis=0)
    spans = [(int(g[0]),int(g[-1])+1) for g in grouped(np.where(white < .60)[0]) if len(g)>.25*w]
    # Two large chart panels. A single chart or blocking full-height modal is
    # an explicit unsupported layout, rather than a guessed half-screen split.
    return spans[:2] if len(spans)==2 else []

def robust_axis(items, left, right, top, bottom, image_width):
    raw=[]
    for o in items:
        cy=o['y']+o['h']/2
        p=price_number(o['text'])
        if p is not None and right-image_width*.035 < o['x'] < right and top<cy<bottom and o['x']+o['w']<right+6:
            raw.append((cy,p,o['text'],o.get('confidence',0),o['x']))
    if len(raw)<5: return None,raw
    ys=np.array([v[0] for v in raw]); ps=np.array([v[1] for v in raw])
    fits=[]
    for model in ['linear','log']:
        zs=np.log(ps) if model=='log' else ps
        best=None
        for i in range(len(ys)):
            for j in range(i+1,len(ys)):
                if abs(ys[i]-ys[j])<80: continue
                b=(zs[j]-zs[i])/(ys[j]-ys[i]); a=zs[i]-b*ys[i]
                if b>=0: continue
                residual=np.abs((zs-a)/b-ys)
                inside=residual<3.2
                key=(int(inside.sum()),-float(np.median(residual[inside])) if inside.any() else -1e6)
                if best is None or key>best[0]: best=(key,inside)
        if best is None or best[0][0]<5: continue
        keep=best[1]
        for _ in range(2):
            b,a=np.polyfit(ys[keep],zs[keep],1)
            residual=np.abs((zs-a)/b-ys)
            keep=residual<3.2
        if keep.sum()<5 or np.ptp(ys[keep])<.35*(bottom-top): continue
        rmse=float(np.sqrt(np.mean(residual[keep]**2)))
        fits.append(dict(model=model,a=float(a),b=float(b),n_inliers=int(keep.sum()),n_axis=len(raw),rmse_pixels=rmse,max_error_pixels=float(residual[keep].max()),y_min=float(ys[keep].min()),y_max=float(ys[keep].max()),axis_left=float(np.median(np.array([v[4] for v in raw])[keep]))))
    if not fits: return None,raw
    # Inlier coverage takes precedence; log must materially improve a tie.
    fits.sort(key=lambda f:(-f['n_inliers'],f['rmse_pixels'] + (.2 if f['model']=='log' else 0)))
    return fits[0],raw

def at_price(axis,y):
    if axis is None: return None
    z=axis['a']+axis['b']*y
    return math.exp(z) if axis['model']=='log' else z

def price_error(axis,y):
    if axis is None: return None
    # OCR alignment plus a 2-pixel border/antialias allowance, conservative 95%-like band.
    d=2+2*axis['rmse_pixels']
    return abs(at_price(axis,y-d)-at_price(axis,y+d))/2

def quote_from_tag(items,left,right,top,bottom):
    found=[]
    for o in items:
        cy=o['y']+o['h']/2
        if not (left<o['x']<right and top<cy<bottom and o['x']>right-250): continue
        m=re.search(r'MGC[A-Z]\d{4}',o['text'])
        if not m: continue
        remainder=o['text'][m.end():].strip()
        p=price_number(remainder)
        src=o['text']
        if p is None:
            matches=[]
            for q in items:
                if abs(q['y']+q['h']/2-cy)<8 and q['x']>=o['x']+o['w']-10 and q['x']<right:
                    value=price_number(q['text'])
                    if value is not None: matches.append((q['x'],value,q['text']))
            if matches:
                _,p,t=min(matches); src += ' | '+t
        if p is not None: found.append(dict(price=p,quote_y=cy,quote_text=src,quote_ocr_confidence=o.get('confidence',0)))
    return max(found,key=lambda f:f['quote_ocr_confidence']) if found else {}

def color_mask(rgb,family):
    r,g,b=np.moveaxis(rgb.astype(float),-1,0)
    if family=='green': return (g-r>40)&(g-b>20)&(b-r>0)&(b-r<.8*(g-r))
    if family=='blue': return (b-r>40)&(b-g>18)&(g-r>8)
    if family=='pink': return (r-g>30)&(b-g>-3)&(b-g<.55*(r-g))&(g>.26*r)
    if family=='red': return (r-g>50)&(r-b>45)&(g<.30*r)&(b<.34*r)
    raise ValueError(family)

def line_start(im,y,left,right,family,color):
    row=im[max(0,y-1):y+2,left:right,:3]
    m=color_mask(row,family)&(np.linalg.norm(row.astype(float)-color,axis=2)<65)
    v=m.any(axis=0).astype(float)
    smooth=np.convolve(v,np.ones(17)/17,mode='same')
    good=np.where(smooth>.40)[0]
    chunks=grouped(good,max_gap=12)
    chunks=[c for c in chunks if len(c)>35 and c[-1]>len(v)-30]
    if not chunks: return None
    return left+int(chunks[-1][0])+4

def zone_candidates(im,left,plot_right,top,bottom,items,axis):
    # Future-side strip reduces candle/text contamination. Detect only native
    # solid/dashed palette boundaries: inverted/consumed objects remain missing.
    width=plot_right-left
    x0=int(left+.82*width);x1=int(left+.98*width)
    if x1-x0<50: return [],[]
    profile=np.median(im[top:bottom,x0:x1,:3],axis=1).astype(float)
    chroma=profile.max(axis=1)-profile.min(axis=1)
    lines=[]
    for family in FAMILIES:
        valid=color_mask(profile,family)
        prominence=np.zeros(len(profile))
        for y in range(6,len(profile)-6):
            neighbors=np.r_[chroma[y-6:y-2],chroma[y+3:y+7]]
            prominence[y]=chroma[y]-np.median(neighbors)
        groups=grouped(np.where(valid&(prominence>12))[0],max_gap=4)
        for group in groups:
            i=int(group[np.argmax(prominence[group])]);y=top+i
            color=profile[i]
            xstart=line_start(im,y,left,plot_right,family,color)
            if xstart is None: continue
            lines.append(dict(y=y,x_start=xstart,family=family,prominence=round(float(prominence[i]),2),rgb=','.join(str(int(x)) for x in color)))
    lines.sort(key=lambda l:l['y'])
    zones=[]
    for family,(direction,kind) in FAMILIES.items():
        these=[v for v in lines if v['family']==family]
        possibilities=[]
        for i,a in enumerate(these):
            for j,b in enumerate(these[i+1:],i+1):
                dy=b['y']-a['y']
                dx=abs(a['x_start']-b['x_start'])
                if not (6<=dy<.65*(bottom-top) and dx<=14): continue
                lx=int((a['x_start']+b['x_start'])/2)
                strip=im[a['y']+2:b['y']-1,max(left,lx-8):min(plot_right,lx+9),:3]
                edge=float(np.max(np.mean(color_mask(strip,family),axis=0))) if strip.size else 0
                # Long rectangles without a visible supporting vertical edge
                # are possible overlapped boundaries, not confirmed geometry.
                geometric='high' if dx<=7 and edge>=.55 else 'medium' if dx<=12 and edge>=.20 else 'low'
                if geometric=='low': continue
                score=edge-.012*dx-.0001*dy
                possibilities.append((score,i,j,edge,geometric))
        used=set()
        for score,i,j,edge,geometric in sorted(possibilities,reverse=True):
            if i in used or j in used: continue
            a,b=these[i],these[j];used.update([i,j])
            lx=int((a['x_start']+b['x_start'])/2)
            labeltexts=[]
            for o in items:
                cy=o['y']+o['h']/2
                if lx-12<=o['x']<min(plot_right,lx+340) and a['y']<cy<b['y'] and re.search(r'\b(?:STATION|FVG|OB|4H)\b',o['text'],re.I):
                    labeltexts.append(o['text'])
            text=' | '.join(labeltexts)
            semantics='medium_palette_only'
            actualkind=kind
            if re.search(r'\b4H\b',text,re.I): actualkind='imported_4H';semantics='high_palette_and_label'
            elif re.search(r'\bFVG\b',text,re.I): actualkind='FVG';semantics='high_palette_and_label'
            elif re.search(r'\bOB\b',text,re.I) and kind=='OB': semantics='high_palette_and_label'
            zones.append(dict(color_family=family,direction_candidate=direction,zone_type_candidate=actualkind,source_timeframe='unknown',zone_left_px=lx,zone_right_px=plot_right,zone_top_px=a['y'],zone_bottom_px=b['y'],top_price_estimate=at_price(axis,a['y']),bottom_price_estimate=at_price(axis,b['y']),price_uncertainty_points=max(price_error(axis,a['y']) or 0,price_error(axis,b['y']) or 0) if axis else None,geometry_confidence=geometric,semantics_confidence=semantics,vertical_edge_support=round(edge,3),label_ocr=text,verification_status='machine_candidate_requires_review',zone_identity_status='frame_local_only',possible_trade_box='not_fully_excluded'))
    return zones,lines

def process_one(args):
    root,ocr_path=args
    root=Path(root);ocr_path=Path(ocr_path)
    o=json.loads(ocr_path.read_text());frame=root/'frames'/(ocr_path.stem+'.jpg')
    if not frame.exists(): frame=Path(o['path'])
    im=np.array(Image.open(frame).convert('RGB'));h,w=im.shape[:2]
    seconds=int(re.search(r'(\d+)$',ocr_path.stem).group(1))
    base=dict(frame_file=str(frame),video_pts_seconds=seconds,ocr_file=str(ocr_path))
    panes=panes_from_image(im); observations=[];zones=[];borders=[]
    if len(panes)!=2:
        return [dict(**base,pane_id='unknown',status='unsupported_layout')],[],[]
    top=int(.065*h);bottom=int(.891*h)
    for pi,(left,right) in enumerate(panes):
        pane='left_5m' if pi==0 else 'right_4h'
        # Timeframe is validated against a chart-title OCR where readable.
        titles=[v['text'] for v in o['items'] if left<v['x']<right and v['y']<.10*h and 'Micro Gold' in v['text']]
        title=' | '.join(titles)
        tf='5m' if pi==0 else '4h'
        verified=bool(re.search(r'Futures\s*[•·.]?\s*5\b',title)) if pi==0 else bool(re.search(r'4\s*h',title,re.I))
        axis,anchors=robust_axis(o['items'],left,right,top,bottom,w)
        quote=quote_from_tag(o['items'],left,right,top,bottom)
        plotright=int(axis['axis_left']-7) if axis else right-int(.025*w)
        obs=dict(**base,pane_id=pane,host_timeframe=tf,timeframe_verified_by_title=verified,title_ocr=title,pane_left_px=left,pane_right_px=right,plot_right_px=plotright,axis_model=axis['model'] if axis else '',axis_anchor_count=axis['n_inliers'] if axis else 0,axis_rmse_pixels=axis['rmse_pixels'] if axis else None,axis_a=axis['a'] if axis else None,axis_b=axis['b'] if axis else None,status='calibrated' if axis else 'axis_calibration_failed',**quote)
        if axis and quote:
            obs['quote_axis_difference_points']=quote['price']-at_price(axis,quote['quote_y'])
            obs['quote_axis_uncertainty_points']=price_error(axis,quote['quote_y'])
        zs,ls=zone_candidates(im,left,plotright,top,bottom,o['items'],axis)
        for z in zs:zones.append(dict(**base,pane_id=pane,host_timeframe=tf,axis_model=axis['model'] if axis else '',**z))
        for b in ls:borders.append(dict(**base,pane_id=pane,**b))
        obs['zone_candidate_count']=len(zs);observations.append(obs)
    return observations,zones,borders

def write_csv_exclusive(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with open(path,'x',newline='') as f:
        writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--limit',type=int);ap.add_argument('--prefix',default='visual_parser_v1');ap.add_argument('--frames',nargs='*',type=int)
    args=ap.parse_args();root=Path(args.root)
    paths=sorted((root/'ocr').glob('frame_*.json'))
    if args.frames is not None:paths=[p for p in paths if int(p.stem.split('_')[-1]) in args.frames]
    if args.limit:paths=paths[:args.limit]
    for name in ['panes','zones','borders','summary']:
        ext='json' if name=='summary' else 'csv'
        if (root/f'{args.prefix}_{name}.{ext}').exists():raise FileExistsError('Refusing to overwrite output')
    panes=[];zones=[];borders=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i,(p,z,b) in enumerate(pool.map(process_one,[(str(root),str(p)) for p in paths],chunksize=10)):
            panes.extend(p);zones.extend(z);borders.extend(b)
            if (i+1)%100==0:print(f'parsed {i+1}/{len(paths)} frames',flush=True)
    write_csv_exclusive(root/f'{args.prefix}_panes.csv',panes)
    write_csv_exclusive(root/f'{args.prefix}_zones.csv',zones)
    write_csv_exclusive(root/f'{args.prefix}_borders.csv',borders)
    summary=dict(frame_count=len(paths),pane_count=len(panes),calibrated_panes=sum(p.get('status')=='calibrated' for p in panes),quote_panes=sum('price' in p for p in panes),zone_candidates=len(zones),border_candidates=len(borders),limitations=['Not OHLC','Recording seconds are not market minutes','No cross-frame zone identity','Palette cannot separate FVG/imported 4H without labels','Possible trade boxes not fully excluded','Inverted/consumed/weak/occluded zones undercovered','Candidate observations need manual verification'])
    with open(root/f'{args.prefix}_summary.json','x') as f:json.dump(summary,f,indent=2)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
