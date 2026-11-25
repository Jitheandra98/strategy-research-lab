"""Same 135 sweeps, but measured from where you could actually get in: the CLOSE of the sweep bar.
A) symmetric: does price go 15 pts toward the reversal before 15 pts toward the continuation (next 2h)?
B) the trade: closed back inside -> fade at the close, stop 1 pt beyond the sweep bar's extreme, target 2R or the opposite
   session level; 0.3 pt cost; stop checked first inside a bar; exit at the end of the 2h/4h window."""
import numpy as np, pandas as pd
exec(open("review_sep30_nov6.py").read().split("# ---- check against")[0])
S = pd.read_csv("sweeps_sep17_nov6.csv", parse_dates=["day"])
ts = {}
# rebuild sweep bar index (first bar after the level's session that trades through it)
rows=[]; prevH=prevL=None
st = np.flatnonzero(tday >= pd.Timestamp("2026-09-17"))[0]
for d in sorted(set(tday[st:])):
    i = np.flatnonzero(tday == d); ck = clock[i]
    asia = i[ck >= 18*60]; lon = i[(ck >= 120) & (ck < 300)]
    lv=[]
    if len(asia): lv += [("Asia H",H[asia].max(),1,asia[-1]+1),("Asia L",L[asia].min(),-1,asia[-1]+1)]
    if len(lon): lv += [("London H",H[lon].max(),1,lon[-1]+1),("London L",L[lon].min(),-1,lon[-1]+1)]
    if prevH is not None: lv += [("PDH",prevH,1,i[0]),("PDL",prevL,-1,i[0])]
    for nm,p,side,s0 in lv:
        for k in range(s0, i[-1]+1):
            if (side==1 and H[k]>p) or (side==-1 and L[k]<p):
                rows.append((nm,p,side,k,(C[k]<p) if side==1 else (C[k]>p))); break
    prevH,prevL = H[i].max(), L[i].min()
out=[]
for nm,p,side,k,back in rows:
    d = -side; px = C[k]
    # A) symmetric 15 from the close
    res="neither"
    for j in range(k+1, min(k+5,N)):
        good = (px-L[j] if d==-1 else H[j]-px) >= 15; bad = (H[j]-px if d==-1 else px-L[j]) >= 15
        if good and bad: res="both"; break
        if good: res="reversal 15 first"; break
        if bad: res="continuation 15 first"; break
    # B) the trade (only meaningful when closed back inside)
    stop = H[k]+1 if d==-1 else L[k]-1; R = abs(px-stop)
    tr2={}
    for name,tgt,n in (("2R/2h",px+d*2*R,4),("2R/4h",px+d*2*R,8)):
        pts=None
        for j in range(k+1, min(k+1+n,N)):
            if (d==1 and L[j]<=stop) or (d==-1 and H[j]>=stop): pts=-R; break
            if (d==1 and H[j]>=tgt) or (d==-1 and L[j]<=tgt): pts=2*R; break
        if pts is None: pts = d*(C[min(k+n,N-1)]-px)
        tr2[name]=(pts-0.3)/R; tr2[name+"_usd"]=(pts-0.3)*10
    out.append(dict(lvl=nm,back=back,regime=regime[k].split()[0],res=res,R=R,**tr2))
X=pd.DataFrame(out)
print("A) measured from the close of the sweep bar (+-15 pts, next 2h)")
print(pd.crosstab(X.res, X.back.map({True:"closed back inside",False:"closed beyond"}), margins=True).to_string())
I=X[X.back]
print(f"\nB) fade every sweep that closed back inside: {len(I)} trades, median stop {I.R.median():.1f} pts (${I.R.median()*10:.0f}/MGC)")
for c in ("2R/2h","2R/4h"):
    r=I[c]; print(f"  {c}: win {(r>0).mean():.0%}  avg {r.mean():+.2f}R  PF {r[r>0].sum()/-r[r<0].sum():.2f}  total ${I[c+'_usd'].sum():+.0f} on 1 MGC")
for g,gg in I.groupby("regime"):
    r=gg["2R/4h"]; print(f"  {g:<11} n={len(gg):3d}  avg {r.mean():+.2f}R  PF {r[r>0].sum()/max(-r[r<0].sum(),1e-9):.2f}")
