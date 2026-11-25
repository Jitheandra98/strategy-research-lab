import json, numpy as np, datetime as dt
J = json.load(open("full131ct.json")); vt = J["vtitles"]
T = np.fromfile("full131ct.json.times.f64", dtype=np.float64)
V = np.fromfile("full131ct.json.vals.f32", dtype=np.float32).reshape(len(T), len(vt))
g = lambda k: V[:, vt.index(k)]
B = np.fromfile("gc5m7_ct.f64", dtype=np.float64).reshape(-1, 7)
idx = {t: i for i, t in enumerate(B[:, 0])}
pos = np.array([idx.get(t, -1) for t in T]); assert (pos >= 0).all()
O, H, L, C = B[:, 1], B[:, 2], B[:, 3], B[:, 4]
# Wilder ATR(14) like ta.atr
tr = np.maximum(H - L, np.maximum(abs(H - np.r_[np.nan, C[:-1]]), abs(L - np.r_[np.nan, C[:-1]]))); tr[0] = H[0] - L[0]
atr = np.full(len(B), np.nan); atr[13] = tr[:14].mean()
for i in range(14, len(B)): atr[i] = atr[i-1] + (tr[i] - atr[i-1]) / 14
print(f"bars {len(T)}  (CT clock)  {dt.datetime.utcfromtimestamp(T[0]/1000)} -> {dt.datetime.utcfromtimestamp(T[-1]/1000)}")
print("v_hour = CT hour:", np.mean(g("v_hour")[::500] == np.array([dt.datetime.utcfromtimestamp(t/1000).hour for t in T[::500]])))
def pct(k): x = g(k); return f"{int(np.nansum(x==1)):6d} bars ({100*np.nanmean(x==1):.2f}%)"
for k, name in [("v_bst","Trend BUY"),("v_sst","Trend SELL"),("v_bsr","Range BUY"),("v_ssr","Range SELL"),("v_bsb","Breakout BUY"),("v_ssb","Breakout SELL"),("v_fbuy","FINAL BUY"),("v_fsell","FINAL SELL"),("v_risk","Risk transfer"),("v_isImpulse","isImpulse"),("v_rangeContraction","rangeContraction"),("v_smallMove","'smart money' small-move test"),("v_magnet","magnet != NONE")]:
    print(f"{name:32s} {pct(k)}")
it = g("v_intent"); names = {0:"UNKNOWN",1:"IMPULSE_BULL",2:"IMPULSE_BEAR",3:"CORRECTION_BULL",4:"CORRECTION_BEAR",5:"RANGING",6:"TRANSITION"}
print("MARKET_INTENT:", {names[int(u)]: f"{100*c/len(it):.1f}%" for u, c in zip(*np.unique(it, return_counts=True))})
ph = g("v_phase"); pn = {1:"ACCUMULATION",2:"MARKUP",3:"DISTRIBUTION",4:"DECLINE"}
print("MARKET_PHASE:", {pn[int(u)]: f"{100*c/len(ph):.1f}%" for u, c in zip(*np.unique(ph, return_counts=True))}, "changes:", int((np.diff(ph)!=0).sum()))
wr, tot, wins = g("v_winrate")[-1], g("v_total")[-1], g("v_wins")[-1]; losses = tot - wins
print(f"DASHBOARD (last bar): Win Rate {wr:.1f}% of {tot:.0f}; 'Recent WR' {wins/min(tot,10)*100:.0f}%; 'Profit Factor' {(wins*15)/max(losses*8,1):.2f}")
# ---- real outcome of the FINAL signals, using the script's own levels: stop 2 ATR, TP1 1 ATR, 20-bar window
COST, SLIP = 0.3, 0.2   # points per round trip (MGC $3) + stop slippage (same as earlier studies)
res = []
for k, d in (("v_fbuy", 1), ("v_fsell", -1)):
    for j in np.where(g(k) == 1)[0]:
        i = pos[j]; a = atr[i]
        if i + 21 >= len(B) or not np.isfinite(a): continue
        e = O[i+1]; stop = e - d*2*a; tp = e + d*1*a
        out = None
        for m in range(i+1, i+21):
            if (d == 1 and L[m] <= stop) or (d == -1 and H[m] >= stop):
                px = (min(O[m], stop) if d == 1 else max(O[m], stop)); out = (px - e)*d - COST - SLIP; break
            if (d == 1 and H[m] >= tp) or (d == -1 and L[m] <= tp):
                out = (tp - e)*d - COST; break
        if out is None: out = (C[i+20] - e)*d - COST
        mfe_win = ((H[i+1:i+21].max() > C[i] + 0.5*a) if d == 1 else (L[i+1:i+21].min() < C[i] - 0.5*a))
        res.append((T[j], d, out, out/(2*a), mfe_win))
R = np.array([r[3] for r in res]); P = np.array([r[2] for r in res]); M = np.array([r[4] for r in res])
gw, gl = P[P>0].sum(), -P[P<0].sum()
print(f"\nFINAL signals traded for real (entry next bar open, stop 2 ATR, target 1 ATR, max 20 bars, cost 0.3 + 0.2 pt):")
print(f"  trades {len(P)}  wins {100*np.mean(P>0):.1f}%  avg {P.mean():+.2f} pt = ${10*P.mean():+.2f}/MGC  avg R {R.mean():+.3f}  PF {gw/gl:.2f}  total ${10*P.sum():+,.0f} at 1 MGC")
print(f"  same trades under the script's own 'win' rule (touch +0.5 ATR within 20 bars): {100*M.mean():.1f}% 'wins'")
t = R.mean()/(R.std(ddof=1)/np.sqrt(len(R))); print(f"  t-stat of avg R: {t:.2f}")
yrs = np.array([dt.datetime.utcfromtimestamp(r[0]/1000).year for r in res])
for y in sorted(set(yrs)): s = yrs == y; print(f"  {y}: n {s.sum():3d}  ${10*P[s].sum():+8,.0f}  PF {P[s][P[s]>0].sum()/max(-P[s][P[s]<0].sum(),1e-9):.2f}")
np.save("orig_final_trades.npy", np.array([(r[0], r[1], r[2], r[3]) for r in res]))
