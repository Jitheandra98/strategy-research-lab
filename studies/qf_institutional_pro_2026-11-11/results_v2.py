"""What the v2 dashboard would show on GC 5m, plus splits the dashboard can't show (by year)."""
import json, sys, numpy as np, datetime as dt
OUT = sys.argv[1] if len(sys.argv) > 1 else "v2_full.json"
J = json.load(open(OUT)); vt = J["vtitles"]
T = np.fromfile(OUT + ".times.f64", dtype=np.float64)
V = np.fromfile(OUT + ".vals.f32", dtype=np.float32).reshape(len(T), len(vt)).astype(np.float64)
g = lambda k: V[:, vt.index(k)]
tr = np.load("v2_trades.npy"); tw = np.load("v2_twin_trades.npy")   # (ebar, xbar, dir, entry, exit, r, reason, kind, ses)
PV = 10.0
def stats(t, label):
    if len(t) == 0: print(f"{label:28s} n 0"); return
    r = t[:, 5]; net = (t[:, 4] - t[:, 3]) * t[:, 2] - 0.3 - np.where(t[:, 6] == 1, 0.2, 0)
    pf = r[r > 0].sum() / max(-r[r < 0].sum(), 1e-12)
    tt = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if len(r) > 1 else 0
    print(f"{label:28s} n {len(r):5d}  won {100*np.mean(net>0):5.1f}%  avg {r.mean():+.3f}R  t {tt:+5.2f}  PF(R) {pf:4.2f}  1 MGC ${PV*net.sum():+9,.0f}")
print(f"bars {len(T):,}  {dt.datetime.utcfromtimestamp(T[0]/1000):%Y-%m-%d} → {dt.datetime.utcfromtimestamp(T[-1]/1000):%Y-%m-%d} (CT)")
stats(tr, "ALL v2 signals")
for k, nm in [(1, "TREND"), (2, "RANGE"), (3, "BREAK")]: stats(tr[tr[:, 7] == k], f"  {nm}")
for s, nm in [(0, "killzone"), (1, "rest of NY"), (2, "London"), (3, "off-hours")]: stats(tr[tr[:, 8] == s], f"  {nm}")
for d, nm in [(1, "buys"), (-1, "sells")]: stats(tr[tr[:, 2] == d], f"  {nm}")
yrs = np.array([dt.datetime.utcfromtimestamp(T[int(e)]/1000).year for e in tr[:, 0]])
for y in sorted(set(yrs)): stats(tr[yrs == y], f"  {y}")
stats(tw, "random-time twin")
ex = tr[:, 6]; print("exits: stop %.0f%%  target %.0f%%  time %.0f%%  reopen %.0f%%" % tuple(100*np.mean(ex == k) for k in (1, 2, 3, 4)))
last = len(T) - 1
print(f"paper account $10,000 → ${g('v_cash')[last]:,.0f}  max DD {100*g('v_cashDD')[last]:.1f}%  'too wide to take' {int(g('v_tooWide')[last])} of {len(tr)}")
print(f"max drawdown {g('v_ddR')[last]:.1f}R  worst losing run {int(g('v_worst')[last])}")
# halves
r = tr[:, 5]; h = len(r)//2
pf = lambda x: x[x > 0].sum() / max(-x[x < 0].sum(), 1e-12)
print(f"halves PF {pf(r[:h]):.2f} / {pf(r[h:]):.2f}")
# per-day frequency
days = len(set(np.round(np.fromfile('gc5m7_ct.f64', dtype=np.float64).reshape(-1,7)[:,6])))
print(f"signals per trading day ≈ {len(tr)/ (len(T)/276):.2f}")
