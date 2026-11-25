"""Faithful Python port of the ZONE side of THE STATION APPOINTMENT v2.0 (Pine v6).

Ported (the trusted part):
  * 3-candle FVG sensor                      (Pine: "FVG sensor")
  * pivots (3/3), BOS/CHoCH, OB extraction  (Pine: "pivot sensor", "structure sensor")
  * 4H FVG import via request.security(240, lookahead_off)  (Pine: "4H MAP")
  * f_addZone size filter + >50% overlap dedupe + MAX_ZONES cap
  * zone lifecycle ACTIVE→TOUCHED→CONSUMED→INVERTED→ARCHIVED
  * four-term station score and eligibility (display "★ STATION")
  * EQH/EQL liquidity pools and sweeps
NOT ported (untrusted decision layer): Position/Pool-Ride/Reaction/Breaker/London trade logic,
route gate, targeting, governors. Those live in indicator_signals.py for comparison only.

Every zone keeps a full event history so the research layer can use its own touch definitions.
Pine semantics kept exactly, including script order within a bar (sensors run before lifecycle,
so a zone can register a "touch" on its birth bar — flagged as birth_touch).
"""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

CFG = dict(ATR_LEN=14, EMA_LEN=100, TREND_LB=10, PIVOT_LEN=3, FVG_MIN_PTS=2.0, ZONE_MAX_PTS=150.0,
           SIZE_LAW_ATR=1.0, SCORE_MIN=3, MAX_TOUCHES=1, EQ_TOL_ATR=0.15, EQ_WINDOW=60, OB_LOOKBACK=20,
           ZONE_ARCHIVE=400, MAX_ZONES=60, WARMUP=250)

STATE = {0: "ACTIVE", 1: "TOUCHED", 2: "CONSUMED", 3: "INVERTED", 4: "ARCHIVED"}


def rma(x, n):
    out = np.full(len(x), np.nan)
    s = None
    for i, v in enumerate(x):
        if np.isnan(v):
            continue
        if s is None:
            # Pine ta.rma seeds with SMA of the first n values
            if i >= n - 1 and not np.isnan(x[i - n + 1:i + 1]).any():
                s = np.mean(x[i - n + 1:i + 1])
                out[i] = s
            continue
        s = (s * (n - 1) + v) / n
        out[i] = s
    return out


def ema(x, n):
    out = np.full(len(x), np.nan)
    a = 2 / (n + 1)
    s = None
    for i, v in enumerate(x):
        if s is None:
            if i >= n - 1:
                s = np.mean(x[i - n + 1:i + 1])
                out[i] = s
            continue
        s = a * v + (1 - a) * s
        out[i] = s
    return out


def atr(h, l, c, n):
    pc = np.concatenate([[np.nan], c[:-1]])
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    tr[0] = h[0] - l[0]
    return rma(tr, n)


@dataclass
class Zone:
    zid: int
    top: float
    bot: float
    dir: int            # 1 demand · -1 supply (flips on inversion)
    kind: str           # OB | FVG | 4H
    born: int           # bar index of birth
    state: int = 0
    firstTouched: bool = False
    touches: int = 0
    orig_dir: int = 0
    events: list = field(default_factory=list)   # (bar, event, detail)
    score_at_birth: int = 0
    atr_at_birth: float = np.nan
    trend_at_birth: int = 0


class ZoneEngine:
    def __init__(self, df, cfg=None, h4_import=None, label="5m"):
        """df: DataFrame with columns open high low close, index 0..n-1 (bars in time order).
        h4_import: optional DataFrame aligned to df rows with columns h4bl,h4bh,h4sl,h4sh,h4t
                   (request.security values as the chart bar sees them)."""
        self.cfg = dict(CFG, **(cfg or {}))
        self.df = df.reset_index(drop=True)
        self.h4 = h4_import
        self.label = label
        c = self.cfg
        o, h, l, cl = (self.df[k].to_numpy(float) for k in ["open", "high", "low", "close"])
        self.o, self.h, self.l, self.c = o, h, l, cl
        self.atr = atr(h, l, cl, c["ATR_LEN"])
        self.ema = ema(cl, c["EMA_LEN"])
        tl = c["TREND_LB"]
        self.trend = np.where(np.concatenate([np.full(tl, np.nan), self.ema[:-tl]]) < self.ema, 1, -1)
        self.zones = []          # live list (Pine array order)
        self.all_zones = []      # every zone ever created
        self.nextid = 0
        self.pivots_h, self.pivots_l = [], []   # (bar_of_pivot, level, confirm_bar)
        self.structure = []      # (bar, dir, 'BOS'|'CHoCH', level)
        self.pools = []          # dicts: level, side, born(confirm bar), swept_bar
        self.bar_rows = []

    # ── helpers ───────────────────────────────────────────────
    def score(self, z, i):
        s = 2 if (z.top - z.bot) >= self.cfg["SIZE_LAW_ATR"] * self.atr[i] else 0
        s += 1 if z.kind == "OB" else 0
        s += 1 if not z.firstTouched else 0
        s += 1 if z.dir == self.trend[i] else 0
        return s

    def eligible(self, z, i):
        return z.state in (0, 1) and z.touches <= self.cfg["MAX_TOUCHES"] and self.score(z, i) >= self.cfg["SCORE_MIN"]

    def add_zone(self, t, b, d, k, i):
        c = self.cfg
        if not (c["FVG_MIN_PTS"] <= (t - b) <= c["ZONE_MAX_PTS"]):
            return None
        for zd in self.zones:
            if zd.dir == d and zd.state <= 1:
                ov = min(t, zd.top) - max(b, zd.bot)
                if ov > 0.5 * (t - b):
                    return None
        z = Zone(self.nextid, t, b, d, k, i, orig_dir=d)
        self.nextid += 1
        z.atr_at_birth = self.atr[i]
        z.trend_at_birth = int(self.trend[i])
        z.score_at_birth = self.score(z, i)
        z.events.append((i, "born", k))
        self.zones.append(z)
        self.all_zones.append(z)
        if len(self.zones) > c["MAX_ZONES"]:
            old = self.zones.pop(0)
            old.events.append((i, "evicted_cap", STATE[old.state]))
        return z

    # ── main loop ─────────────────────────────────────────────
    def run(self):
        c = self.cfg
        o, h, l, cl = self.o, self.h, self.l, self.c
        P = c["PIVOT_LEN"]
        lastPH = lastPL = np.nan
        structDir = 0
        last4hSeen = None
        n = len(cl)
        for i in range(n):
            warm = i > c["WARMUP"] and not np.isnan(self.atr[i]) and not np.isnan(self.ema[i])
            # 4H import (runs before FVG sensor in the Pine source)
            if self.h4 is not None and warm:
                r = self.h4.iloc[i]
                if not pd.isna(r.h4t) and (last4hSeen is None or r.h4t != last4hSeen):
                    last4hSeen = r.h4t
                    if r.h4bl > r.h4bh:
                        self.add_zone(r.h4bl, r.h4bh, 1, "4H", i)
                    if r.h4sl < r.h4sh:
                        self.add_zone(r.h4sh, r.h4sl, -1, "4H", i)
            if warm and i >= 2:
                if l[i] > h[i - 2]:
                    self.add_zone(l[i], h[i - 2], 1, "FVG", i)
                if h[i] < l[i - 2]:
                    self.add_zone(l[i - 2], h[i], -1, "FVG", i)
            # pivots: ta.pivothigh/low(P,P), confirmed P bars late. Treated as strict extremes on
            # both sides (tie handling in TradingView is undocumented; ties are rare at 0.1 tick).
            phv = plv = np.nan
            if i >= 2 * P:
                j = i - P
                if (h[j - P:j] < h[j]).all() and (h[j + 1:j + P + 1] < h[j]).all():
                    phv = h[j]
                if (l[j - P:j] > l[j]).all() and (l[j + 1:j + P + 1] > l[j]).all():
                    plv = l[j]
            breakDir = 0
            if warm:
                if not np.isnan(phv):
                    lastPH = phv
                    self.pivots_h.append((i - P, phv, i))
                    self._pool_check(self.pivots_h, phv, i, side=1)
                if not np.isnan(plv):
                    lastPL = plv
                    self.pivots_l.append((i - P, plv, i))
                    self._pool_check(self.pivots_l, plv, i, side=-1)
                if not np.isnan(lastPH) and cl[i] > lastPH:
                    kindS = "CHoCH" if structDir == -1 else "BOS"
                    self.structure.append((i, 1, kindS, lastPH))
                    breakDir = 1
                    structDir = 1
                    lastPH = np.nan
                    for k in range(1, c["OB_LOOKBACK"] + 1):
                        if i - k >= 0 and cl[i - k] < o[i - k]:
                            self.add_zone(h[i - k], l[i - k], 1, "OB", i)
                            break
                if not np.isnan(lastPL) and cl[i] < lastPL:
                    kindS = "CHoCH" if structDir == 1 else "BOS"
                    self.structure.append((i, -1, kindS, lastPL))
                    breakDir = -1
                    structDir = -1
                    lastPL = np.nan
                    for k in range(1, c["OB_LOOKBACK"] + 1):
                        if i - k >= 0 and cl[i - k] > o[i - k]:
                            self.add_zone(h[i - k], l[i - k], -1, "OB", i)
                            break
                # sweeps
                for p in self.pools:
                    if p["swept_bar"] is None and p["side"] == 1 and h[i] > p["level"]:
                        p["swept_bar"] = i
                    if p["swept_bar"] is None and p["side"] == -1 and l[i] < p["level"]:
                        p["swept_bar"] = i
            # lifecycle
            if warm and self.zones:
                for idx in range(len(self.zones) - 1, -1, -1):
                    z = self.zones[idx]
                    if z.state <= 1 or z.state == 3:
                        fa = z.dir == 1 and l[i] <= z.top and l[i - 1] > z.top
                        fb = z.dir == -1 and h[i] >= z.bot and h[i - 1] < z.bot
                        if fa or fb:
                            z.touches += 1
                            z.firstTouched = True
                            if z.state == 0:
                                z.state = 1
                            z.events.append((i, "touch", z.touches if i != z.born else "birth_touch"))
                        if z.state <= 1 and ((z.dir == 1 and l[i] <= z.bot) or (z.dir == -1 and h[i] >= z.top)):
                            z.state = 2
                            z.events.append((i, "consumed", None))
                    elif z.state == 2:
                        ib = z.dir == 1 and cl[i - 1] < z.bot and h[i] >= z.bot
                        ia = z.dir == -1 and cl[i - 1] > z.top and l[i] <= z.top
                        if ib or ia:
                            z.dir = -z.dir
                            z.state = 3
                            z.firstTouched = True
                            z.touches = 0
                            z.events.append((i, "inverted", z.dir))
                        elif i - z.born > c["ZONE_ARCHIVE"]:
                            z.state = 4
                    if z.state == 3 and z.touches >= 2:
                        z.state = 4
                    if z.state == 4:
                        z.events.append((i, "archived", None))
                        self.zones.pop(idx)
        return self

    def _pool_check(self, piv, v, i, side):
        c = self.cfg
        P = c["PIVOT_LEN"]
        if len(piv) > 30:
            piv.pop(0)
        # Pine: loops i over older pivots, first match within window & tolerance forms a pool
        for (pb, pv, _) in piv[:-1]:
            if (i - P) - pb <= c["EQ_WINDOW"] and abs(v - pv) <= c["EQ_TOL_ATR"] * self.atr[i]:
                lv = max(v, pv) if side == 1 else min(v, pv)
                self.pools.append({"level": lv, "side": side, "born": i, "pivot_bars": (pb, i - P), "swept_bar": None})
                live = [p for p in self.pools if p["side"] == side and p["swept_bar"] is None]
                if len(live) > 15:
                    live[0]["swept_bar"] = -1   # dropped by cap (not a sweep)
                break

    # ── outputs ───────────────────────────────────────────────
    def zones_frame(self, times=None):
        rows = []
        for z in self.all_zones:
            ev = z.events
            first_touch = next((b for b, e, d in ev if e == "touch" and d != "birth_touch"), None)
            birth_touch = any(e == "touch" and d == "birth_touch" for b, e, d in ev)
            consumed = next((b for b, e, d in ev if e == "consumed"), None)
            inverted = next((b for b, e, d in ev if e == "inverted"), None)
            ended = next((b for b, e, d in ev if e in ("archived", "evicted_cap")), None)
            rows.append(dict(tf=self.label, zid=z.zid, kind=z.kind, dir=z.orig_dir, top=z.top, bot=z.bot,
                             size=z.top - z.bot, born_bar=z.born, atr_birth=z.atr_at_birth,
                             size_atr=(z.top - z.bot) / z.atr_at_birth if z.atr_at_birth else np.nan,
                             trend_birth=z.trend_at_birth, score_birth=z.score_at_birth,
                             birth_touch=birth_touch, first_touch_bar=first_touch, consumed_bar=consumed,
                             inverted_bar=inverted, end_bar=ended, final_state=STATE[z.state],
                             n_touch_events=sum(1 for _, e, _ in ev if e == "touch")))
        df = pd.DataFrame(rows)
        if times is not None and len(df):
            for col in ["born_bar", "first_touch_bar", "consumed_bar", "inverted_bar", "end_bar"]:
                df[col.replace("_bar", "_time")] = df[col].map(lambda b: times[int(b)] if pd.notna(b) else pd.NaT)
        return df
