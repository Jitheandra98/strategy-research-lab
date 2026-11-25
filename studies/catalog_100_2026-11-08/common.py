"""Shared data, clocks, indicators, simulator and pass bar for the catalog test (conventions in SPEC.md)."""
import numpy as np, pandas as pd

DATA = "/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64"
a = np.fromfile(DATA).reshape(-1, 5)
t = (a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000).astype(np.int64)
O, H, L, C = (np.ascontiguousarray(a[:, k]) for k in range(1, 5))
N = len(C)
utc = pd.to_datetime(t, unit="s", utc=True)
_ct = utc.tz_convert("America/Chicago")
_ln = utc.tz_convert("Europe/London")
ctm = (_ct.hour * 60 + _ct.minute).to_numpy()            # Chicago minute of day
lnm = (_ln.hour * 60 + _ln.minute).to_numpy()            # London minute of day
fixm = ((t // 60) - 360) % 1440                          # fixed UTC-6 minute of day (no DST)
smin = (ctm - 17 * 60) % 1440                            # minutes since the 17:00 CT session start (monotonic in a session)

_sdate = (_ct.tz_localize(None) + pd.Timedelta(hours=7)).normalize()   # CME trade date
sid = pd.factorize(_sdate)[0]
nS = sid.max() + 1
sfirst = np.r_[0, np.flatnonzero(np.diff(sid)) + 1]
slast = np.r_[sfirst[1:] - 1, N - 1]
send = slast[sid]
s_date = pd.DatetimeIndex(_sdate[sfirst])
YEAR = _sdate.year.to_numpy()

sH = np.maximum.reduceat(H, sfirst); sL = np.minimum.reduceat(L, sfirst); sC = C[slast]; sO = O[sfirst]
_prev = lambda x: np.r_[np.nan, x[:-1]]
pdh, pdl, pdc = _prev(sH)[sid], _prev(sL)[sid], _prev(sC)[sid]
settle = np.full(nS, np.nan)
_m = ctm == 12 * 60 + 25
settle[sid[_m]] = C[_m]                                   # 12:30 CT price
prev_settle = _prev(settle)                               # per session


def rma(x, n):
    return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


_sPC = np.r_[sC[0], sC[:-1]]
sTR = np.maximum(sH - sL, np.maximum(np.abs(sH - _sPC), np.abs(sL - _sPC)))
prev_datr = _prev(rma(sTR, 14))                           # per session: previous session's daily ATR

_iso = s_date.isocalendar()
_wkey = (_iso["year"].to_numpy() * 100 + _iso["week"].to_numpy())
wid_s = pd.factorize(_wkey)[0]
wid = wid_s[sid]
_g = pd.DataFrame({"w": wid_s, "h": sH, "l": sL, "o": sO})
wH = _g.groupby("w").h.max().to_numpy(); wL = _g.groupby("w").l.min().to_numpy(); wO = _g.groupby("w").o.first().to_numpy()
pwh, pwl = _prev(wH)[wid], _prev(wL)[wid]
wopen = wO[wid]

# ---- 5m indicators
_pc = np.r_[C[0], C[:-1]]
TR = np.maximum(H - L, np.maximum(np.abs(H - _pc), np.abs(L - _pc)))
ATR = rma(TR, 14)
E9, E20, E21, E50 = ema(C, 9), ema(C, 20), ema(C, 21), ema(C, 50)
_d = np.diff(C, prepend=C[0])
RSI = 100 - 100 / (1 + rma(np.maximum(_d, 0), 14) / np.maximum(rma(np.maximum(-_d, 0), 14), 1e-12))
_up = np.r_[0, np.diff(H)]; _dn = np.r_[0, -np.diff(L)]
_pdm = np.where((_up > _dn) & (_up > 0), _up, 0.0); _mdm = np.where((_dn > _up) & (_dn > 0), _dn, 0.0)
PDI = 100 * rma(_pdm, 14) / np.maximum(ATR, 1e-12); MDI = 100 * rma(_mdm, 14) / np.maximum(ATR, 1e-12)
ADX = rma(100 * np.abs(PDI - MDI) / np.maximum(PDI + MDI, 1e-12), 14)
_s = pd.Series(C)
SMA20 = _s.rolling(20).mean().to_numpy(); SD20 = _s.rolling(20).std(ddof=0).to_numpy()
BBU, BBL = SMA20 + 2 * SD20, SMA20 - 2 * SD20
KU, KL = E20 + 1.5 * ATR, E20 - 1.5 * ATR


def prior_max(x, n):
    return pd.Series(x).rolling(n).max().shift(1).to_numpy()


def prior_min(x, n):
    return pd.Series(x).rolling(n).min().shift(1).to_numpy()


def pivots(k=3):
    """3-bar fractal swing highs/lows. Returns arrays of pivot indices (usable from index + k)."""
    h, l = pd.Series(H), pd.Series(L)
    lm, rm = h.rolling(k).max().shift(1), h[::-1].rolling(k).max().shift(1)[::-1]
    ln, rn = l.rolling(k).min().shift(1), l[::-1].rolling(k).min().shift(1)[::-1]
    ph = np.flatnonzero(((h > lm) & (h > rm)).to_numpy())
    pl = np.flatnonzero(((l < ln) & (l < rn)).to_numpy())
    return ph, pl


NAN = float("nan")


def simulate(sigs, min_r=0.2):
    """sigs: (i, d, stop, tgt_price, tgt_R, lim, exit_arr). Entry at O[i+1]; stop first; one trade at a time;
    forced exit at lim (capped at the session's last bar). Returns DataFrame(i, e, x, d, gross, R, year)."""
    sigs = sorted(sigs, key=lambda s: s[0])
    rows, busy = [], -1
    for i, d, stop, tgt, tgtR, lim, xa in sigs:
        if i <= busy or i + 1 >= N:
            continue
        e = i + 1
        if sid[e] != sid[i]:
            continue
        lim = min(lim, send[i])
        if lim < e:
            continue
        px = O[e]
        R = d * (px - stop)
        if not R >= min_r:
            continue
        if tgtR > 0:
            tgt = px + d * tgtR * R
        if tgt == tgt and d * (tgt - px) <= 0:
            continue
        x, xp = lim, C[lim]
        for j in range(e, lim + 1):
            if d == 1:
                if j > e and O[j] <= stop: x, xp = j, O[j]; break
                if L[j] <= stop: x, xp = j, stop; break
                if tgt == tgt and H[j] >= tgt: x, xp = j, tgt; break
            else:
                if j > e and O[j] >= stop: x, xp = j, O[j]; break
                if H[j] >= stop: x, xp = j, stop; break
                if tgt == tgt and L[j] <= tgt: x, xp = j, tgt; break
            if xa is not None and xa[j]: x, xp = j, C[j]; break
        rows.append((i, e, x, d, d * (xp - px), R, YEAR[i]))
        busy = x
    return pd.DataFrame(rows, columns=["i", "e", "x", "d", "gross", "R", "year"])


PERIODS = [(2012, 2019), (2020, 2023), (2024, 2026)]


def pf(x):
    neg = -x[x < 0].sum()
    return x[x > 0].sum() / neg if neg > 0 else (np.inf if len(x) else np.nan)


def evaluate(T):
    """Pass bar from SPEC.md. Returns a dict of numbers and booleans."""
    if len(T) == 0:
        return dict(n=0, per_yr=0, win=np.nan, PF=np.nan, avg_pt=np.nan, usd=0, PF_12_19=np.nan, PF_20_23=np.nan,
                    PF_24_26=np.nan, long_usd=0, short_usd=0, usd_at_05=0, yrs_pos=0, PASS=False)
    n3, n5 = T.gross.to_numpy() - 0.3, T.gross.to_numpy() - 0.5
    per = [T.year.between(a, b).to_numpy() for a, b in PERIODS]
    pfs = [pf(n3[m]) for m in per]
    yrs = pd.Series(n3).groupby(T.year.to_numpy()).sum()
    r = dict(n=len(T), per_yr=len(T) / T.year.nunique(), win=100 * (n3 > 0).mean(), PF=pf(n3), avg_pt=n3.mean(),
             usd=n3.sum() * 10, PF_12_19=pfs[0], PF_20_23=pfs[1], PF_24_26=pfs[2],
             long_usd=n3[T.d.to_numpy() == 1].sum() * 10, short_usd=n3[T.d.to_numpy() == -1].sum() * 10,
             usd_at_05=n5.sum() * 10, yrs_pos=int((yrs > 0).sum()))
    r["PASS"] = bool(all(p >= 1.15 for p in pfs) and r["long_usd"] > 0 and r["short_usd"] > 0 and r["usd_at_05"] > 0
                     and r["yrs_pos"] >= 9 and all(m.sum() >= 30 for m in per))
    return r
