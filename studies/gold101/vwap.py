"""OHLCV VWAP strategies. HLC3 stands in for individual traded prices."""
import numpy as np
import pandas as pd

from run import clock
from sessions import rvol


def signals(df, emit):
    if not df.v.gt(0).any():
        return
    o,h,l,c,v = [df[x] for x in 'ohlcv']
    a = df.atr
    px = (h+l+c)/3
    dates, minutes = clock(df)
    weighted = px*v
    vol = v.groupby(dates).cumsum().replace(0, np.nan)
    vw = weighted.groupby(dates).cumsum()/vol
    var = (px**2*v).groupby(dates).cumsum()/vol - vw**2
    sd = np.sqrt(var.clip(lower=0))
    delta = c-vw
    rising = vw.gt(vw.shift(5)) & pd.Series(dates == np.roll(dates, 5), index=df.index)
    above = delta.gt(0)
    below6 = delta.lt(0).shift(1).rolling(6).sum().eq(6)
    session = pd.Series(dates, index=df.index)
    same6 = session.eq(session.shift(6))

    def send(ident, mask, side, stop, target=None, multiple=None, n=12, exit_signal=None):
        ix = np.flatnonzero(mask)
        emit(ident, ix, side, np.asarray(stop)[ix], None if target is None else np.asarray(target)[ix],
             multiple, n, exit_signal)

    send(31, above & below6 & rising & same6, 1, l, multiple=2, exit_signal=c.lt(vw))
    send(32, h.ge(vw) & c.lt(vw) & below6 & same6, -1, h, multiple=2)
    low2 = vw-2*sd
    high1 = vw+sd
    high2 = vw+2*sd
    reentry = c.ge(low2) & (c.shift().lt(low2.shift()) | l.lt(low2))
    send(33, same6 & reentry & (vw-vw.shift(6)).abs().lt(.25*a), 1, l.combine(l.shift(), min), vw, n=8)
    send(34, same6 & rising & c.gt(high1) & l.le(high1) & c.gt(high1).shift().rolling(6).sum().eq(6),
         1, l, high2, n=8)
    us = pd.Series((minutes >= 440) & (minutes < 950), index=df.index)
    usv = (v*us).groupby(dates).cumsum().replace(0,np.nan)
    usvw = (weighted*us).groupby(dates).cumsum()/usv
    send(35, (minutes >= 470) & (minutes < 950) & c.gt(vw) & c.gt(usvw) & c.shift().le(usvw.shift()),
         1, l, exit_signal=(c.lt(vw)|c.lt(usvw)))

    H,L,C = h.to_numpy(),l.to_numpy(),c.to_numpy()
    vv = np.r_[0,v.cumsum().to_numpy()]
    ww = np.r_[0,weighted.cumsum().to_numpy()]
    sk = session.to_numpy()
    session_high = h.groupby(dates).cummax().to_numpy()
    session_starts = np.r_[0, np.flatnonzero(sk[1:] != sk[:-1])+1]
    ends = np.r_[session_starts[1:],len(df)]
    V = vw.to_numpy()

    def anchored(start, stop):
        denom = vv[stop+1]-vv[start]
        return (ww[stop+1]-ww[start])/denom if denom > 0 else np.nan

    rows = []
    for anchor in np.flatnonzero(c.gt(h.shift().rolling(30).max())):
        for i in range(anchor+1,min(len(c),anchor+13)):
            if sk[i] != sk[anchor]:
                break
            line = anchored(anchor,i)
            if L[i] <= line < C[i]:
                rows.append((i,L[i],H[anchor:i].max()))
                break
    send_rows(36, rows, emit, n=10)

    rows = []
    anchor = None
    for i in range(4,len(c)):
        if sk[i] != sk[i-1]:
            anchor = None
        j = i-2
        if sk[i] == sk[i-4] and L[j] == min(L[i-4:i+1]) and (L[i-4:i+1] == L[j]).sum() == 1:
            anchor = j
        if anchor is None or i <= anchor+2:
            continue
        line = anchored(anchor,i)
        if C[i] > line and C[i-1] <= anchored(anchor,i-1) and C[i-2] <= anchored(anchor,i-2):
            rows.append((i,min(L[i-2:i+1]),V[i] if V[i] > C[i] else np.nan))
    send_rows(37, rows, emit, n=8)

    crosses = ((above != above.shift()) & session.eq(session.shift())).rolling(12).sum().ge(3)
    rv = rvol(df)
    rows = []
    dirs = []
    for j in np.flatnonzero(crosses & ~crosses.shift(fill_value=False) & session.eq(session.shift(11))):
        hi,lo = max(H[j-11:j+1]),min(L[j-11:j+1])
        for i in range(j+1,min(len(c),j+13)):
            if sk[i] != sk[j]:
                break
            if rv[i]>1.5 and (C[i]>hi or C[i]<lo):
                rows.append((i,(hi+lo)/2,np.nan))
                dirs.append(1 if C[i]>hi else -1)
                break
    send_rows(38, rows, emit, n=10, side=dirs, multiple=2)

    prior = np.full(len(c),np.nan)
    for start,end in zip(session_starts[1:],ends[1:]):
        prior[start:end] = V[start-1]
    send(39, c.shift().gt(prior) & l.le(prior) & c.gt(prior) & rising, 1, l,
         np.where(session_high>C,session_high,np.nan), n=10)

    rows = []
    for j in np.flatnonzero(c.gt(high2) & c.shift().le(high2.shift())):
        for i in range(j+1,min(len(c),j+4)):
            if sk[i] != sk[j]:
                break
            if C[i]<high1.iloc[i]:
                rows.append((i,max(H[j:i+1]),V[i]))
                break
    send_rows(40, rows, emit, n=8, side=-1)


def send_rows(ident, rows, emit, n, side=1, multiple=None):
    ix, stop, target = zip(*rows) if rows else ([],[],[])
    emit(ident, ix, side, stop, target, multiple, n)
