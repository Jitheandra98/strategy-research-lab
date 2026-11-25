"""Stage 15: the owner's 4H box-staircase rule, written from watching the videos (V3 Mar-2024 uptrend, V2 May-2023
downtrend), then tested unchanged on every split and against placebo boxes.

BULL (BEAR mirrored):
 1 trend: 4H EMA100 trend up (STATION2 definition) AND last 4H BOS/CHoCH up - both known at the 15m bar
 2 box  : any 4H-pane box (OB/FVG; consumed/inverted boxes included = breaker/IFVG), alive on the chart
 3 escape: a 4H close above the box top, then price trades >= top + 1.0 ATR4. escape_high = highest high since.
 4 return: first 15m bar after the escape whose low touches the top (re-armed only by a new escape)
 5 entry : A = limit at the top on that bar (open if it gapped below); B = first 15m close back above top within 8 bars
 6 stop  : box bottom - 0.1 ATR15 (if stop is hit on the touch bar -> loss); target = escape_high; 192-bar (2 day) time stop
   cost 0.30 pt per trade, charged in R.
usage: 15_owner_rule.py <build_dir> <work_dir> <tag> [placebo_draws]
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

B, W, TAG = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
NPLC = int(sys.argv[4]) if len(sys.argv) > 4 else 10
COST, ESC, CONF_WIN, TMAX = 0.30, 1.0, 8, 192
b15 = pd.read_pickle(B / "bars15.pkl"); h4 = pd.read_pickle(B / "bars4h.pkl"); z4 = pd.read_pickle(B / "zones4h.pkl")
s4 = pd.read_pickle(B / "struct4h.pkl")
T = b15.index; n = len(T)
O, H, L, C, A15 = (b15[k].to_numpy(float) for k in ["open", "high", "low", "close", "atr"])
h4 = h4.copy(); h4["avail"] = pd.to_datetime(h4.avail)
ctx = pd.merge_asof(pd.DataFrame({"t": T}), h4[["avail", "trend", "atr", "close"]].rename(columns={"avail": "t"}).sort_values("t"),
                    on="t", direction="backward")
TR4, A4, C4 = ctx.trend.to_numpy(), ctx.atr.to_numpy(), ctx.close.to_numpy()   # last CLOSED 4H bar
s4["avail"] = s4.time.map(lambda x: h4.avail.get(x, pd.NaT))
ST4 = pd.merge_asof(pd.DataFrame({"t": T}), s4[["avail", "dir"]].rename(columns={"avail": "t"}).dropna().sort_values("t"),
                    on="t", direction="backward").dir.to_numpy()
new4 = np.r_[True, ctx.t.ne(ctx.t.shift()).to_numpy()[1:]] if False else np.r_[True, np.diff(np.nan_to_num(C4)) != 0]
rev = {k: sorted(v)[0] for k, v in pd.read_pickle(W / "bar_reveal.pkl").items()}  # bar -> (video, t, run)
pos = {t: i for i, t in enumerate(T)}


def trade(i_touch, d, top, bot, target, version):
    """returns (R, win, entry_bar) or None"""
    a = A15[i_touch]
    stop = bot - 0.1 * a if d == 1 else top + 0.1 * a
    if version == "A":
        ent = min(top, O[i_touch]) if d == 1 else max(bot, O[i_touch]); i0 = i_touch
        if (d == 1 and L[i_touch] <= stop) or (d == -1 and H[i_touch] >= stop):
            r = abs(ent - stop); return (-1 - COST / r, 0, i0)
        start = i_touch + 1
    else:
        i0 = None
        for k in range(i_touch, min(n, i_touch + CONF_WIN)):
            if (d == 1 and L[k] <= stop) or (d == -1 and H[k] >= stop):
                return None                              # invalidated before confirming: no trade
            if (d == 1 and C[k] > top) or (d == -1 and C[k] < bot):
                i0 = k; break
        if i0 is None: return None
        ent = C[i0]; start = i0 + 1
    risk = abs(ent - stop)
    if risk <= 0 or (d == 1 and target <= ent) or (d == -1 and target >= ent): return None
    for j in range(start, min(n, start + TMAX)):
        if (d == 1 and L[j] <= stop) or (d == -1 and H[j] >= stop): return (-1 - COST / risk, 0, i0)
        if (d == 1 and H[j] >= target) or (d == -1 and L[j] <= target):
            return ((abs(target - ent) - COST) / risk, 1, i0)
    j = min(n - 1, start + TMAX - 1)
    return ((d * (C[j] - ent) - COST) / risk, 0, i0)


def run(tops, bots):
    rows = []
    for zi, z in enumerate(z4.itertuples()):
        av = h4.avail.get(z.born_time, pd.NaT)
        if pd.isna(av) or av not in pos: continue
        a = pos[av]
        e = int(np.searchsorted(T, z.end_time + pd.Timedelta(hours=4))) if pd.notna(z.end_time) else n
        top, bot = tops[zi], bots[zi]
        for d in (1, -1):
            armed = False; esc_ext = None; closed_out = False
            for i in range(a + 1, min(e, n - 2)):
                if np.isnan(A4[i]): continue
                # 4H close beyond the box on the escape side (uses only closed 4H bars)
                if (d == 1 and C4[i] > top) or (d == -1 and C4[i] < bot): closed_out = True
                if (d == 1 and C4[i] < bot) or (d == -1 and C4[i] > top): closed_out = False; armed = False; esc_ext = None
                if closed_out and not armed:
                    ext = H[i] if d == 1 else L[i]
                    esc_ext = ext if esc_ext is None else (max(esc_ext, ext) if d == 1 else min(esc_ext, ext))
                    if (d == 1 and esc_ext >= top + ESC * A4[i]) or (d == -1 and esc_ext <= bot - ESC * A4[i]):
                        armed = True
                    continue
                if armed:
                    esc_ext = max(esc_ext, H[i - 1]) if d == 1 else min(esc_ext, L[i - 1])
                    touch = (L[i] <= top) if d == 1 else (H[i] >= bot)
                    if touch:
                        ok_trend = (TR4[i] == d) and (ST4[i] == d)
                        for ver in ("A", "B"):
                            t = trade(i, d, top, bot, esc_ext, ver)
                            if t is None: continue
                            rv = rev.get(T[i])
                            rows.append(dict(box=z.zid, kind=z.kind, dir=d, top=top, bot=bot, h_atr4=(top - bot) / A4[i],
                                             bar=i, time_utc=T[i], version=ver, trend_ok=int(ok_trend), R=t[0], win=t[1],
                                             tgt_R=abs(esc_ext - top) / max(1e-9, abs(top - (bot - 0.1 * A15[i]))),
                                             video=rv[0] if rv else np.nan, video_t=rv[1] if rv else np.nan))
                        armed = False; esc_ext = None; closed_out = False   # one trade per escape
    return pd.DataFrame(rows)


real = run(z4.top.to_numpy(), z4.bot.to_numpy())
real.to_pickle(W / f"owner_rule_{TAG}_real.pkl")
rng = np.random.default_rng(5)
atr_birth = np.interp(z4.born_time.astype("int64"), h4.index.astype("int64"), h4.atr.ffill().bfill().to_numpy())
plc = []
for k in range(NPLC):
    sh = rng.choice([-1, 1], len(z4)) * rng.uniform(1, 3, len(z4)) * atr_birth
    p = run(z4.top.to_numpy() + sh, z4.bot.to_numpy() + sh); p["draw"] = k; plc.append(p)
P = pd.concat(plc); P.to_pickle(W / f"owner_rule_{TAG}_placebo.pkl")


def summ(df, lab):
    out = []
    df = df.assign(split=np.where(df.video.isin([1, 2]), "V1+V2", np.where(df.video == 3, "V3", "OFF-VIDEO")))
    for (sp, ver, tok), g in df.groupby(["split", "version", "trend_ok"]):
        se = g.R.std() / np.sqrt(len(g)) if len(g) > 1 else np.nan
        out.append(dict(src=lab, split=sp, version=ver, trend_ok=tok, n=len(g) / (NPLC if lab == "PLACEBO" else 1),
                        win=g.win.mean(), avgR=g.R.mean(), ci=1.96 * se, medR=g.R.median(), tgtR=g.tgt_R.median()))
    return pd.DataFrame(out)


S = pd.concat([summ(real, "REAL"), summ(P, "PLACEBO")])
S.to_csv(W / f"owner_rule_{TAG}_summary.csv", index=False)
pd.set_option("display.width", 250)
print(S.round(3).to_string())
