"""Review of the replay the owner played Sep 30 -> Nov 6 2026 (MGCZ2026, 30m) that I logged but had not narrated.
OHLC: complete 5m MGCZ2026 bars (replay_live_2026-11-01/mgc5m_bars.json) -> 30m. Desk Context values recomputed in Python
(ATR/ADX/DI Wilder 14 on 30m, regime rules of the indicator) and checked against the values the watcher read off the chart.
Clock: sessions on New York time (Desk Context), printed times in Central (owner)."""
import json, re, numpy as np, pandas as pd
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
raw = json.load(open("../replay_live_2026-11-01/mgc5m_bars.json"))
a = np.array(raw, dtype=float)
df = pd.DataFrame(a[:, 1:5], columns=list("ohlc"), index=pd.to_datetime(a[:, 0].astype(np.int64), unit="s", utc=True).tz_convert("America/New_York"))
b = df.resample("30min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
O, H, L, C = (b[k].to_numpy() for k in "ohlc"); N = len(C); idx = b.index
clock = (idx.hour * 60 + idx.minute).to_numpy()
tday = (idx.tz_localize(None) + pd.Timedelta(hours=6)).normalize()
ctime = idx.tz_convert("America/Chicago")
pc = np.r_[C[0], C[:-1]]
tr = np.maximum(H - L, np.maximum(abs(H - pc), abs(L - pc)))
rma = lambda x: pd.Series(x).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
atr = rma(tr)
up = np.r_[0, np.diff(H)]; dn = np.r_[0, -np.diff(L)]
pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
pdi = 100 * rma(pdm) / rma(tr); mdi = 100 * rma(mdm) / rma(tr)
adx = rma(100 * np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-9))
rising = adx > np.r_[adx[0], adx[:-1]]
regime = np.where(adx < 20, "RANGE", np.where((adx > 25) & rising, np.where(pdi > mdi, "TREND UP", "TREND DOWN"), "TRANSITION"))

# ---- check against what the watcher read off the chart
logged = {}
for line in open("bars.jsonl"):
    r = json.loads(line)
    if r["desk"] and r["t"] not in logged: logged[r["t"]] = r
tsec = (idx.tz_convert("UTC").tz_localize(None) - pd.Timestamp("1970-01-01")) // pd.Timedelta("1s")
pos = {t: i for i, t in enumerate(tsec)}
chk = [(pos[t], r) for t, r in logged.items() if t in pos and pos[t] > 150]
agree = np.mean([regime[i] == r["desk"]["Regime"] for i, r in chk])
adx_err = np.median([abs(adx[i] - float(r["desk"]["ADX 14"].split()[0])) for i, r in chk])
print(f"recomputed vs chart: regime agrees on {agree:.0%} of {len(chk)} logged bars, median |ADX diff| {adx_err:.2f}\n")

# ---- daily table from Sep 29 evening (trading day Sep 30) to Nov 6
D = []
for d, g in b.groupby(tday):
    if d < pd.Timestamp("2026-09-30"): continue
    i = np.flatnonzero(tday == d)
    big = i[np.argmax(H[i] - L[i])]
    rg = pd.Series(regime[i]).value_counts(normalize=True)
    D.append(dict(day=d.strftime("%a %m-%d"), open=O[i[0]], close=C[i[-1]], net=C[i[-1]] - O[i[0]], rng=H[i].max() - L[i].min(),
                  maxADX=adx[i].max(), trend=rg.filter(like="TREND").sum() * 100, rangepct=rg.get("RANGE", 0) * 100,
                  big_bar=f"{ctime[big]:%H:%M} CT {H[big]-L[big]:.0f} {'up' if C[big] > O[big] else 'dn'}"))
D = pd.DataFrame(D)
print(D.to_string(index=False, float_format=lambda v: f"{v:.0f}"))
print(f"\nSep 30 open {D.open.iloc[0]:.1f} -> Nov 6 close {D.close.iloc[-1]:.1f}; avg daily range {D.rng.mean():.0f} pts")

# ---- biggest 30m bars and what Desk Context said the bar BEFORE
sel = np.flatnonzero(tday >= pd.Timestamp("2026-09-30"))
top = sel[np.argsort(-(H[sel] - L[sel]))][:15]
print("\nbiggest 30m bars Sep 30-Nov 6 | Desk Context on the bar before | next 2h")
for k in sorted(top):
    nxt = C[min(k + 4, N - 1)] - C[k]
    print(f"{ctime[k]:%a %m-%d %H:%M} CT  {H[k]-L[k]:5.1f} pts {'UP' if C[k] > O[k] else 'DN'} | before: {regime[k-1]:<10} ADX {adx[k-1]:4.1f} ATR {atr[k-1]:4.1f} | next 2h {nxt:+.0f}")

# ---- hour-of-day: where the movement was (Central)
hr = pd.Series(H[sel] - L[sel], index=ctime[sel].hour).groupby(level=0).mean()
print("\navg 30m bar size by Central hour (Sep 30-Nov 6):", " ".join(f"{h}:{v:.0f}" for h, v in hr.items()))

# ---- what followed each Desk Context change (whole complete sample Sep 17 -> Nov 6, after indicator warm-up)
st = np.flatnonzero(tday >= pd.Timestamp("2026-09-17"))[0]
def fwd(k, d, n):
    e = min(k + n, N - 1)
    if e <= k: return np.nan, np.nan, np.nan
    return d * (C[e] - C[k]), (d * (H[k+1:e+1] - C[k]) if d == 1 else d * (L[k+1:e+1] - C[k])).max(), \
           (-(L[k+1:e+1] - C[k]) if d == 1 else (H[k+1:e+1] - C[k])).max()
ev = []
for k in range(st, N - 1):
    d_di = 1 if pdi[k] > mdi[k] else -1
    if regime[k].startswith("TREND") and not regime[k-1].startswith("TREND"): ev.append(("Regime -> TREND (trade with DI)", k, d_di))
    if regime[k] == "RANGE" and regime[k-1] != "RANGE": ev.append(("Regime -> RANGE (fade last 2h move)", k, -np.sign(C[k] - C[max(k-4, 0)]) or 1))
    if rising[k] and not rising[k-1] and rising[k] and adx[k] < 22 and (adx[k] - adx[k-2] if k > 1 else 0) > -9: ev.append(("ADX turns up from <22 (trade with DI)", k, d_di))
    if (not rising[k]) and rising[k-1] and adx[k-1] > 30: ev.append(("ADX turns down from >30 (fade DI)", k, -d_di))
    if np.sign(pdi[k] - mdi[k]) != np.sign(pdi[k-1] - mdi[k-1]): ev.append(("DI cross (trade new leader)", k, d_di))
E = []
for name, k, d in ev:
    for n in (4, 8):
        m, mfe, mae = fwd(k, d, n); E.append(dict(event=name, h=f"{n//2}h", move=m, mfe=mfe, mae=mae))
E = pd.DataFrame(E)
print("\nafter each Desk Context change (Sep 17-Nov 6, 30m, points in the trade direction, no costs):")
print(E.groupby(["event", "h"]).agg(n=("move", "size"), avg_move=("move", "mean"), won=("move", lambda x: (x > 0).mean() * 100),
      avg_best=("mfe", "mean"), avg_worst=("mae", "mean")).round(1).to_string())

# ---- sweeps of session levels (Asia / London / previous day), first touch only, next 2h resolution
rows = []; prevH = prevL = None
days = sorted(set(tday[st:]))
for d in days:
    i = np.flatnonzero(tday == d); ck = clock[i]
    asia = i[ck >= 18 * 60]; lon = i[(ck >= 120) & (ck < 300)]
    lv = []
    if len(asia): lv += [("Asia H", H[asia].max(), 1, asia[-1] + 1), ("Asia L", L[asia].min(), -1, asia[-1] + 1)]
    if len(lon): lv += [("London H", H[lon].max(), 1, lon[-1] + 1), ("London L", L[lon].min(), -1, lon[-1] + 1)]
    if prevH is not None: lv += [("PDH", prevH, 1, i[0]), ("PDL", prevL, -1, i[0])]
    for nm, p, side, s0 in lv:
        for k in range(s0, i[-1] + 1):
            if (side == 1 and H[k] > p) or (side == -1 and L[k] < p):
                back = (C[k] < p) if side == 1 else (C[k] > p)
                res = "neither"
                for j in range(k + 1, min(k + 5, N)):
                    rev = (p - L[j] if side == 1 else H[j] - p) >= 15; cont = (H[j] - p if side == 1 else p - L[j]) >= 15
                    if rev and cont: res = "both"; break
                    if rev: res = "reversed 15 first"; break
                    if cont: res = "continued 15 first"; break
                rows.append(dict(day=d, lvl=nm, regime=regime[k].split()[0], closed_back=back, res=res, ny=ctime[k].strftime("%H:%M")))
                break
    prevH, prevL = H[i].max(), L[i].min()
S = pd.DataFrame(rows)
print(f"\nsweeps Sep 17-Nov 6: {len(S)} on {S.day.nunique()} days")
print(pd.crosstab(S.res, S.regime, margins=True).to_string())
print(pd.crosstab(S.res, S.closed_back.map({True: "closed back inside", False: "closed beyond"}), margins=True).to_string())
S.to_csv("sweeps_sep17_nov6.csv", index=False); D.to_csv("days_sep30_nov6.csv", index=False)
