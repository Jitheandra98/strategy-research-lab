"""PAPER ACCOUNT process test (2026-11-09). Rules were fixed before this ran: RUN_SPEC.md + ACCOUNT_SPEC.md (owner: "use
your defaults"). Strategy = spike follow MAIN (research/spike_follow_2026-11-08), NOT qualified: this tests the machine.
Run: python3 paper_engine.py > results.txt    Writes logs/decisions_X.csv, logs/fills_X.csv, logs/trades_X.csv."""
import json, os
import numpy as np, pandas as pd

ROOT = "/Users/jitheandrasubramaniam/Desktop/hey hey/"
SPOT5 = ROOT + "trading-video-intel/tools/pine_runner/xau5m.f64"
MGC5 = ROOT + "research/edge_search_2026-11-07/mgc1_5m.json"
OLD = ROOT + "research/spike_follow_2026-11-08/trades_main.csv"
OUT = ROOT + "research/paper_account_2026-11-09/"
NY = "America/New_York"
USD, TICK = 10.0, 0.1                      # MGC: $10 per point, 0.1 pt tick
HALF, FIVE = pd.Timedelta(minutes=30), pd.Timedelta(minutes=5)
PERIODS = [(2012, 2019), (2020, 2023), (2024, 2026)]
ACCT = dict(start=10_000.0, floor=7_500.0, dd_lim=0.15, day_lim=0.02, risk_pct=0.01, slip_allow=0.2)   # ASSUMPTIONS
POL = ["A", "B", "C"]
NAME = {"A": "A  hold to 13:30", "B": "B  target +1R", "C": "C  small profit +0.3R net"}


# ------------------------------------------------------------------------------------------------------------ data
def frame(t, ohlc):
    t = np.asarray(t, dtype=np.float64)
    t = (t if t[0] < 1e11 else t / 1000).astype(np.int64)
    return pd.DataFrame(np.asarray(ohlc, dtype=np.float64), columns=list("ohlc"),
                        index=pd.to_datetime(t, unit="s", utc=True).tz_convert(NY))


class Market:
    """5m bars plus the 30m bars, ATR and spike trigger of spike_follow.py MAIN, on the New York clock."""

    def __init__(self, df5):
        self.t5, self.ns5 = df5.index, df5.index.asi8
        self.o5, self.h5, self.l5, self.c5 = (df5[k].to_numpy() for k in "ohlc")
        self.min5 = df5.index.minute.to_numpy()
        b = df5.resample("30min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
        self.O, self.H, self.L, self.C = (b[k].to_numpy() for k in "ohlc")
        self.idx, self.ns30, self.N = b.index, b.index.asi8, len(b)
        self.clock = (b.index.hour * 60 + b.index.minute).to_numpy()
        self.date = b.index.tz_localize(None).normalize().to_numpy()
        self.yr = b.index.year.to_numpy()
        pc = np.r_[self.C[0], self.C[:-1]]
        tr = np.maximum(self.H - self.L, np.maximum(np.abs(self.H - pc), np.abs(self.L - pc)))
        self.atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
        atrp = np.r_[self.atr[0], self.atr[:-1]]                       # previous bar's ATR (trigger)
        x1300 = np.flatnonzero(self.clock == 13 * 60)
        i1300 = dict(zip(self.date[x1300], x1300))
        self.x13 = np.array([i1300.get(d, -1) for d in self.date])
        nxt = np.zeros(self.N, bool)
        nxt[:-1] = (np.diff(self.ns30) == HALF.value) & (self.date[1:] == self.date[:-1])
        self.trad = nxt & (self.x13 > np.arange(self.N))
        self.spikes = np.flatnonzero((self.clock >= 480) & (self.clock <= 600) & ((self.H - self.L) >= 2.5 * atrp)
                                     & (self.C != self.O))
        self.pool = {c: np.flatnonzero(self.clock == c) for c in range(480, 601, 30)}

    def path(self, k):
        """5m index range [i0, i1): from the open of 30m bar k+1 to 13:30 that day."""
        return (np.searchsorted(self.ns5, self.ns30[k + 1]),
                np.searchsorted(self.ns5, self.ns30[self.x13[k]] + HALF.value))

    def bars5(self, i0, i1):
        return self.o5[i0:i1], self.h5[i0:i1], self.l5[i0:i1], self.c5[i0:i1]

    def signals(self, old_filter=False, since=None):
        """The day's first spike only. Decision at the spike bar's close, using only bars up to and including it."""
        out, seen = [], set()
        for k in self.spikes:
            if self.date[k] in seen: continue
            seen.add(self.date[k])
            if not self.trad[k]: continue
            d = 1 if self.C[k] > self.O[k] else -1
            stop = self.L[k] - 0.1 * self.atr[k] if d == 1 else self.H[k] + 0.1 * self.atr[k]
            if old_filter and d * (self.O[k + 1] - stop) <= 0: continue      # old study only (uses the next open)
            if since is not None and self.idx[k] < since: continue
            i0, i1 = self.path(k)
            out.append(dict(k=k, day=pd.Timestamp(self.date[k]), year=int(self.yr[k]), clock=int(self.clock[k]), d=d,
                            stop=stop, dpx=self.C[k], t_dec=self.idx[k] + HALF, i0=i0, i1=i1))
        return out


# ------------------------------------------------------------------------------------------------------- execution
def target_for(policy, d, entry, stop):
    R = d * (entry - stop)
    if policy == "A" or R <= 0: return None
    return entry + d * (R if policy == "B" else 0.3 * R + 0.3)


def bar_exit(d, o, h, l, stop, tgt, slip):
    """Resting orders inside one bar: stop first (a gap through it fills at the open), then the target, which needs a
    1-tick trade-through. Returns (fill, reason, intended price) or None."""
    if d == 1:
        if o <= stop: return o - slip, "STOP_GAP", stop
        if l <= stop: return stop - slip, "STOP", stop
        if tgt is not None and h >= tgt + TICK: return tgt, "TARGET", tgt
    else:
        if o >= stop: return o + slip, "STOP_GAP", stop
        if h >= stop: return stop + slip, "STOP", stop
        if tgt is not None and l <= tgt - TICK: return tgt, "TARGET", tgt
    return None


def walk(o, h, l, c, d, entry, stop, tgt, slip):
    for j in range(len(o)):
        x = bar_exit(d, o[j], h[j], l[j], stop, tgt, slip)
        if x: return j, x[0], x[1]
    return len(o) - 1, c[-1], "TIME_1330"


def per_contract(mk, sigs, policy, cost=0.3, slip=0.2, path30=False):
    """Every signal at a fixed 1 MGC, natural exits only (no account limits)."""
    rows = []
    for s in sigs:
        if path30:
            k, x = s["k"], mk.x13[s["k"]]
            o, h, l, c = mk.O[k + 1:x + 1], mk.H[k + 1:x + 1], mk.L[k + 1:x + 1], mk.C[k + 1:x + 1]
        else:
            o, h, l, c = mk.bars5(s["i0"], s["i1"])
        d, stop = s["d"], s["stop"]
        entry = o[0]
        j, px, why = walk(o, h, l, c, d, entry, stop, target_for(policy, d, entry, stop), slip)
        gross = d * (px - entry)
        worst = min(0.0, (d * (c[:j] - entry)).min() if j > 0 else 0.0, gross)
        rows.append(dict(day=s["day"], year=s["year"], clock=s["clock"], d=d, R=d * (entry - stop),
                         risk_dec=abs(s["dpx"] - stop), gross=gross, net=gross - cost, why=why,
                         net_usd=(gross - cost) * USD, worst_usd=(worst - cost) * USD))
    return pd.DataFrame(rows)


def control(mk, sigs, P, policy, cost, slip, seed=8, n_ctrl=20):
    """Random same-clock control: same direction, stop distance and exit policy on 20 random other days (net R)."""
    rng = np.random.default_rng(seed)
    out = np.full(len(sigs), np.nan)
    for i, s in enumerate(sigs):
        k, d, R = s["k"], s["d"], P.R.iat[i]
        if R <= 0: continue
        pool, vals = mk.pool[mk.clock[k]], []
        for r in pool[rng.integers(0, len(pool), 80)]:
            if mk.date[r] == mk.date[k] or not mk.trad[r]: continue
            o, h, l, c = mk.bars5(*mk.path(r))
            if len(o) == 0: continue
            entry = o[0]; stop = entry - d * R
            _, px, _ = walk(o, h, l, c, d, entry, stop, target_for(policy, d, entry, stop), slip)
            vals.append((d * (px - entry) - cost) / R)
            if len(vals) == n_ctrl: break
        if vals: out[i] = np.mean(vals)
    return out


# ---------------------------------------------------------------------------------------------------------- account
def run_account(mk, sigs, policy, cost=0.3, slip=0.2, start=10_000.0, floor=7_500.0, dd_lim=0.15, day_lim=0.02,
                risk_pct=0.01, slip_allow=0.2, freeze=True, log=False):
    """One paper account, one run. Equity marked at every 5m close; size from min(realized, MTM) (flat at entry)."""
    cash = peak = start
    maxdd, status, stop_day, ts_x = 0.0, "RUNNING", None, None
    trades, dec, fills, skips = [], [], [], {"risk budget": 0, "floor buffer": 0}

    def D(ts, action, reason, est_cost, risk, mtm):
        if log:
            dec.append(dict(ts=ts, action=action, reason=reason, est_cost_usd=round(est_cost, 2),
                            risk_at_stake_usd=round(risk, 2), realized_usd=round(cash, 2), mtm_usd=round(mtm, 2),
                            dd_from_peak_pct=round(100 * (1 - mtm / peak), 2), to_floor_usd=round(mtm - floor, 2)))

    def F(order, ts, side, kind, qty, intended, fill, slip_pts, cost_usd):
        if log:
            fills.append(dict(order=order, ts=ts, side=side, type=kind, qty=qty, intended=round(intended, 2),
                              fill=round(fill, 2), slip_pts=round(slip_pts, 2), cost_usd=round(cost_usd, 2)))

    for s in sigs:
        if status != "RUNNING": break
        eq = cash                                                         # flat: realized == MTM
        d, stop, dpx = s["d"], s["stop"], s["dpx"]
        dist = abs(dpx - stop)
        rpc = (dist + slip_allow + cost) * USD                           # loss at invalidation + slippage + cost
        n = int(risk_pct * eq // rpc)
        why = None
        if n == 0:
            why = "risk budget"
        else:
            while n > 0 and eq - n * (dist + 2 * slip_allow + cost) * USD < floor + 2 * risk_pct * eq: n -= 1
            if n == 0: why = "floor buffer"
        if why:
            skips[why] += 1
            D(s["t_dec"], "NO TRADE", f"{why}: 1 MGC risks ${rpc:,.0f}, budget ${risk_pct * eq:,.0f}", 0.0, 0.0, eq)
            continue
        o, h, l, c = mk.bars5(s["i0"], s["i1"])
        tt, mins = mk.t5[s["i0"]:s["i1"]], mk.min5[s["i0"]:s["i1"]]
        entry = o[0]
        tgt = target_for(policy, d, entry, stop)
        cost_usd, risk_usd, sod = n * cost * USD, n * rpc, eq
        side_in, side_out = ("BUY", "SELL") if d == 1 else ("SELL", "BUY")
        oid = 2 * len(trades) + 1
        D(s["t_dec"], "ENTER", f"{'long' if d == 1 else 'short'} {n} MGC; stop {stop:.2f}; "
          + (f"target {tgt:.2f}" if tgt is not None else "exit 13:30"), cost_usd, risk_usd, eq)
        F(oid, tt[0], side_in, "MKT entry", n, dpx, entry, d * (entry - dpx), cost_usd / 2)
        worst = 0.0
        for j in range(len(o)):
            x = bar_exit(d, o[j], h[j], l[j], stop, tgt, slip)
            if x:
                px, why, intended = x; ts_x = tt[j]; break
            if j == len(o) - 1:
                px, why, intended = c[j], "TIME_1330", c[j]; ts_x = tt[j] + FIVE; break
            mtm = cash + n * d * (c[j] - entry) * USD - cost_usd
            worst = min(worst, d * (c[j] - entry))
            peak = max(peak, mtm)
            dd = 1 - mtm / peak
            maxdd = max(maxdd, dd)
            trig = ("FLOOR_END" if mtm <= floor else "DD_FREEZE" if freeze and dd >= dd_lim
                    else "DAILY_HALT" if mtm < sod * (1 - day_lim) else None)
            if trig:                                                       # close at the next executable price
                px, why, intended = o[j + 1] - d * slip, trig, o[j + 1]; ts_x = tt[j + 1]; trig_dd = dd; break
            if mins[j] % 30 == 25:                                         # 30m decision point while open
                D(tt[j] + FIVE, "HOLD", "tested rule: hold until stop" + ("/target" if tgt is not None else "")
                  + "/13:30", 0.0, n * (d * (c[j] - stop) + slip_allow) * USD, mtm)
        gross_usd = n * d * (px - entry) * USD
        net_usd = gross_usd - cost_usd
        worst = min(worst, d * (px - entry))
        cash += net_usd
        peak = max(peak, cash)
        dd = 1 - cash / peak
        maxdd = max(maxdd, dd)
        if why == "FLOOR_END" or cash <= floor: status = "FAILED"
        elif why == "DD_FREEZE" or (freeze and dd >= dd_lim): status = "FROZEN"
        kind = {"STOP": "STOP", "STOP_GAP": "STOP (gap)", "TARGET": "LIMIT target", "TIME_1330": "MKT 13:30"}.get(
            why, "MKT forced")
        D(ts_x, "EXIT", why, cost_usd, 0.0, cash)
        F(oid + 1, ts_x, side_out, kind, n, intended, px, d * (intended - px), cost_usd / 2)
        if why == "DAILY_HALT": D(ts_x, "HALT", "daily loss limit: no more trades this session", 0.0, 0.0, cash)
        if status == "FROZEN":
            D(ts_x, "FREEZE", f"drawdown {100 * (trig_dd if why == 'DD_FREEZE' else dd):.1f}% from peak (marked) >= "
                              f"{100 * dd_lim:g}%: frozen pending review", 0.0, 0.0, cash)
        if status == "FAILED": D(ts_x, "END", "failure floor breached: run over", 0.0, 0.0, cash)
        if status != "RUNNING": stop_day = s["day"]
        trades.append(dict(day=s["day"], year=s["year"], d=d, n=n, eq_before=eq, risk_usd=risk_usd, entry=entry,
                           stop=stop, target=tgt, exit=px, why=why, gross_usd=gross_usd, cost_usd=cost_usd,
                           slip_usd=0.0 if why in ("TARGET", "TIME_1330") else n * slip * USD, net_usd=net_usd,
                           equity=cash, worst_open_usd=n * worst * USD - cost_usd))
    if status == "RUNNING":
        status = "SURVIVED"
        D(sigs[-1]["t_dec"], "END", "data ends: SURVIVED", 0.0, 0.0, cash)
    T = pd.DataFrame(trades)
    # ---- engine checks: the run is void if any fails
    if len(T):
        assert abs(cash - (start + T.net_usd.sum())) < 1e-6, "equity does not reconcile"
        assert (T.risk_usd <= risk_pct * T.eq_before + 1e-6).all(), "risk cap breached at entry"
    if log:
        acts = [r["action"] for r in dec]
        cut = next((i for i, r in enumerate(dec) if r["action"] == "FREEZE" or r["reason"].startswith("failure")), None)
        assert cut is None or "ENTER" not in acts[cut:], "entered while frozen/failed"
        assert len(fills) == 2 * len(T), "fill count"
    return dict(status=status, eq=cash, maxdd=maxdd, T=T, dec=pd.DataFrame(dec), fills=pd.DataFrame(fills),
                stop_day=stop_day, skips=skips, start=start)


def monte_carlo(P, start, floor, dd_lim=0.15, risk_pct=0.01, slip_allow=0.2, cost=0.3, sims=10_000, seed=7, **_):
    """Reshuffle trade order; same sizing and floor buffer; in-trade trough from each trade's worst open loss.
    No freeze applied, so the full max-drawdown distribution is visible; P(freeze) = P(maxDD >= limit)."""
    rng = np.random.default_rng(seed)
    dist, net, worst = P.risk_dec.to_numpy(), P.net_usd.to_numpy(), P.worst_usd.to_numpy()
    perm = rng.permuted(np.tile(np.arange(len(P), dtype=np.int32), (sims, 1)), axis=1)
    eq = np.full(sims, start); peak = eq.copy(); maxdd = np.zeros(sims)
    froze = np.full(sims, -1); floor_hit = np.zeros(sims, bool)
    for i in range(len(P)):
        j = perm[:, i]
        n = np.floor(risk_pct * eq / ((dist[j] + slip_allow + cost) * USD))
        nb = np.floor((eq - floor - 2 * risk_pct * eq) / ((dist[j] + 2 * slip_allow + cost) * USD))
        n = np.maximum(np.minimum(n, nb), 0)
        trough = eq + n * worst[j]
        dd = 1 - trough / peak
        maxdd = np.maximum(maxdd, dd)
        froze[(froze < 0) & (dd >= dd_lim)] = i
        floor_hit |= trough <= floor
        eq = eq + n * net[j]
        peak = np.maximum(peak, eq)
    f = froze[froze >= 0]
    return dict(p_freeze=100 * (froze >= 0).mean(), freeze_med_tr=np.median(f) if len(f) else np.nan,
                p_floor=100 * floor_hit.mean(), dd50=100 * np.median(maxdd), dd95=100 * np.percentile(maxdd, 95),
                end_med=np.median(eq), p_up=100 * (eq > start).mean())


# ---------------------------------------------------------------------------------------------------------- reports
def st(x):
    x = np.asarray(x, float); n = len(x)
    if n < 2: return dict(n=n, win=np.nan, pf=np.nan, mean=np.nan, t=np.nan, net=float(x.sum()), dd=0.0)
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    eq = np.r_[0.0, np.cumsum(x)]
    return dict(n=n, win=100 * (x > 0).mean(), pf=pos / neg if neg > 0 else np.inf, mean=x.mean(),
                t=x.mean() / (x.std(ddof=1) / np.sqrt(n)), net=x.sum(), dd=(np.maximum.accumulate(eq) - eq).max())


def fmt(s):
    return (f"{s['n']:5d} tr  win {s['win']:4.1f}%  PF {s['pf']:4.2f}  mean ${s['mean']:+6.2f}  t {s['t']:+5.2f}  "
            f"net ${s['net']:+8,.0f}  maxDD ${s['dd']:6,.0f}")


def pc_block(P, ctrl=None):
    r = P.net / P.R
    for name, m in [("ALL", P.year > 0)] + [(f"{a}-{b}", P.year.between(a, b)) for a, b in PERIODS] + \
                   [("long", P.d == 1), ("short", P.d == -1)]:
        line = f"  {name:9s} " + fmt(st(P[m].net_usd))
        if ctrl is not None:
            ok = m & (P.R > 0) & ~np.isnan(ctrl)
            line += f"  | edge vs random {(r[ok] - ctrl[ok]).mean():+.3f}R"
        print(line)
    yrs = P.groupby("year").net_usd.sum()
    print(f"  years profitable: {(yrs > 0).sum()} of {len(yrs)}   exits: "
          + ", ".join(f"{k} {v}" for k, v in P.why.value_counts().items()))


def acct_line(tag, r):
    T = r["T"]; x = T.net_usd if len(T) else pd.Series(dtype=float)
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    stopd = r["stop_day"].date() if r["stop_day"] is not None else "-"
    print(f"  {tag:30s} {r['status']:8s} on {str(stopd):10s} trades {len(T):4d}  no-trade "
          f"{sum(r['skips'].values()):4d}  end ${r['eq']:9,.0f} ({100 * (r['eq'] / r['start'] - 1):+6.1f}%)  "
          f"maxDD {100 * r['maxdd']:5.1f}%  PF {pos / neg if neg > 0 else np.nan:4.2f}  "
          f"avg win ${x[x > 0].mean() if pos > 0 else 0:4,.0f}  avg loss ${x[x < 0].mean() if neg > 0 else 0:5,.0f}  "
          f"costs ${(T.cost_usd.sum() + T.slip_usd.sum()) if len(T) else 0:6,.0f}")


if __name__ == "__main__":
    os.makedirs(OUT + "logs", exist_ok=True)
    a = np.fromfile(SPOT5).reshape(-1, 5)
    mk = Market(frame(a[:, 0], a[:, 1:]))
    print(f"Gold spot 5m {mk.t5[0]} -> {mk.t5[-1]} ({len(mk.t5):,} bars, {mk.N:,} 30m bars). 1 MGC = $10/pt.")
    print("ASSUMPTIONS (owner chose defaults): $10,000 start, floor $7,500, freeze at 15% below peak, daily halt at -2%,"
          "\n  1% risk per trade (stop + 0.2 pt slippage allowance + 0.3 pt cost), 0.3 pt round-trip cost, 0.2 pt stop slippage.")

    print("\n=== 1. ENGINE CHECKS (run is void if any fails) ===")
    old = pd.read_csv(OLD, parse_dates=["day"])
    rep_sigs = mk.signals(old_filter=True)
    rep = per_contract(mk, rep_sigs, "A", cost=0.3, slip=0.0, path30=True)
    same = len(rep) == len(old) and (rep.day.values == old.day.values).all() and (rep.d.values == old.d.values).all()
    gdiff = np.abs(rep.gross.values - old.gross.values).max() if same else np.nan
    print(f"  replication of trades_main.csv (30m path, no slippage, old filter): {len(rep)} vs {len(old)} trades, "
          f"same days and directions: {same}, max gross diff {gdiff:.1e} pt, net ${rep.net_usd.sum():+,.0f} vs "
          f"${(old.net * USD).sum():+,.0f}")
    assert same and gdiff < 1e-9
    sigs = mk.signals()
    beyond = sum(1 for s in sigs if s["d"] * (mk.O[s["k"] + 1] - s["stop"]) <= 0)
    print(f"  engine signals: {len(sigs)} (old look-ahead filter dropped {len(sigs) - len(rep_sigs)}; "
          f"next open already beyond the stop: {beyond})")
    ok = all(np.isclose(mk.o5[s["i0"]], mk.O[s["k"] + 1]) for s in sigs)
    print(f"  5m entry fill equals the 30m open for every signal: {ok}")
    assert ok
    print("  per-run checks inside run_account: equity reconciles, risk <= 1% at every ENTER, no ENTER after a "
          "freeze/failure, two fills per trade")

    print("\n=== 2. EXIT POLICIES AT A FIXED 1 MGC (every signal, no account limits) ===")
    PC, CT = {}, {}
    for p in POL:
        PC[p, "base"] = per_contract(mk, sigs, p, 0.3, 0.2)
        PC[p, "cost05"] = per_contract(mk, sigs, p, 0.5, 0.2)
        PC[p, "slip04"] = per_contract(mk, sigs, p, 0.3, 0.4)
        CT[p] = control(mk, sigs, PC[p, "base"], p, 0.3, 0.2)
        print(f"\n{NAME[p]}  (cost 0.3 pt, stop slippage 0.2 pt)")
        pc_block(PC[p, "base"], CT[p])
        for tag, key in (("cost 0.5 pt", "cost05"), ("stop slippage 0.4 pt", "slip04")):
            print(f"  {tag:21s}" + fmt(st(PC[p, key].net_usd)))
    print(f"\n  (5m resolution + 0.2 pt stop slippage moved A from ${rep.net_usd.sum():+,.0f} to "
          f"${PC['A', 'base'].net_usd.sum():+,.0f} over 14 years)")

    print("\n=== 3. CHRONOLOGICAL PICK: best mean net $ per trade on 2012-2019, judged once on 2020 -> Sep 2026 ===")
    dev = {p: PC[p, "base"][PC[p, "base"].year <= 2019].net_usd.mean() for p in POL}
    pick = max(dev, key=dev.get)
    print("  development 2012-2019 mean net per trade: " + "   ".join(f"{p} ${v:+.2f}" for p, v in dev.items())
          + f"   -> pick {pick}")
    V = PC[pick, "base"][PC[pick, "base"].year >= 2020]
    vper = [st(V[V.year.between(a, b)].net_usd) for a, b in PERIODS[1:]]
    print(f"  validation 2020 -> Sep 2026 ({NAME[pick]}): " + fmt(st(V.net_usd)))
    for (a_, b_), s_ in zip(PERIODS[1:], vper): print(f"     {a_}-{b_}: " + fmt(s_))
    val_ok = st(V.net_usd)["mean"] > 0 and all(s_["pf"] >= 1.15 for s_ in vper)

    print("\n=== 4. THE ACCOUNT: $10,000, all limits on (official process-test runs) ===")
    RUN = {}
    for p in POL:
        RUN[p] = r = run_account(mk, sigs, p, log=True, **ACCT)
        for kind, nm in (("dec", "decisions"), ("fills", "fills"), ("T", "trades")):
            r[kind].to_csv(OUT + f"logs/{nm}_{p}.csv", index=False)
        acct_line(NAME[p], r)
    print("\n  stress (same rules):")
    for p in POL:
        for tag, (cst, slp) in {"cost 0.5": (0.5, 0.2), "stop slip 0.4": (0.3, 0.4), "both": (0.5, 0.4)}.items():
            RUN[p, tag] = run_account(mk, sigs, p, cost=cst, slip=slp, **ACCT)
            acct_line(f"{p} {tag}", RUN[p, tag])
    print("\n  $2,000 account (floor $1,500, same percentages):")
    for p in POL:
        RUN[p, "2k"] = run_account(mk, sigs, p, **{**ACCT, "start": 2_000.0, "floor": 1_500.0})
        acct_line(f"{p} $2,000", RUN[p, "2k"])
    print("\n  DIAGNOSTIC ONLY - same $10,000 accounts with the 15% freeze switched off (floor and daily halt still on):")
    for p in POL:
        RUN[p, "nofreeze"] = r = run_account(mk, sigs, p, freeze=False, **ACCT)
        acct_line(f"{p} no freeze", r)
        ye = r["T"].groupby("year").equity.last()
        print("     year-end equity: " + "  ".join(f"{y % 100:02d}:${v / 1000:.1f}k" for y, v in ye.items()))
    for p in POL:
        R0 = RUN[p]
        if R0["status"] == "FROZEN":
            Tn = RUN[p, "nofreeze"]["T"]
            after = Tn[Tn.day > R0["stop_day"]]
            print(f"  {p}: frozen {R0['stop_day'].date()} at ${R0['eq']:,.0f}; with no freeze the next "
                  f"{len(after)} trades netted ${after.net_usd.sum():+,.0f}")

    print("\n=== 5. MONTE CARLO: 10,000 reshuffles of trade order, $10,000, sizing + floor buffer, no freeze applied ===")
    MC = {}
    for p in POL:
        for key, tag in (("slip04", "stop slip 0.4 (gate)"), ("base", "base")):
            MC[p, key] = m = monte_carlo(PC[p, key], **ACCT)
            print(f"  {p} {tag:21s} P(freeze) {m['p_freeze']:5.1f}%  (median at trade {m['freeze_med_tr']:5.0f} "
                  f"= {m['freeze_med_tr'] / 129:4.1f} yrs)  P(floor) {m['p_floor']:5.1f}%  maxDD median "
                  f"{m['dd50']:5.1f}%  95th {m['dd95']:5.1f}%  end equity median ${m['end_med']:,.0f}  "
                  f"P(end > start) {m['p_up']:4.1f}%")

    print("\n=== 6. QUALIFICATION GATE (ACCOUNT_SPEC.md section 3) ===")
    gate_rows = []
    for p in POL:
        B = PC[p, "base"]; s_all = st(B.net_usd); tneed = 2 if p == "A" else 3
        per = [st(B[B.year.between(a_, b_)].net_usd) for a_, b_ in PERIODS]
        yrs = int((B.groupby("year").net_usd.sum() > 0).sum())
        rr, okc = B.net / B.R, (B.R > 0) & ~np.isnan(CT[p])
        edges = [(rr - CT[p])[okc & B.year.between(a_, b_)].mean() for a_, b_ in PERIODS]
        aff = B[(B.risk_dec + ACCT["slip_allow"] + 0.3) * USD <= ACCT["risk_pct"] * ACCT["start"]]
        sa = st(aff.net_usd); pa = [st(aff[aff.year.between(a_, b_)].net_usd) for a_, b_ in PERIODS]
        g = {
            "1 expectancy": (s_all["mean"] > 0 and s_all["t"] >= tneed,
                             f"${s_all['mean']:+.2f}/trade, t {s_all['t']:+.2f} (needs >= {tneed})"),
            "2 old bar": (all(x["pf"] >= 1.15 for x in per) and yrs >= 9 and B[B.d == 1].net_usd.sum() > 0
                          and B[B.d == -1].net_usd.sum() > 0 and PC[p, "cost05"].net_usd.sum() > 0
                          and all(e > 0 for e in edges),
                          "PF " + "/".join(f"{x['pf']:.2f}" for x in per) + f", {yrs}/15 yrs, at 0.5 pt "
                          f"${PC[p, 'cost05'].net_usd.sum():+,.0f}, edge " + "/".join(f"{e:+.3f}" for e in edges)),
            "3 chronological": ((p == pick) and val_ok,
                                "picked; validation " + ("holds" if val_ok else "fails") if p == pick else "not picked"),
            "4 survival": (RUN[p]["status"] == "SURVIVED" and MC[p, "slip04"]["dd95"] < 15,
                           f"{RUN[p]['status']}, MC 95th maxDD {MC[p, 'slip04']['dd95']:.0f}%"),
            "5 affordable": (sa["mean"] > 0 and sa["t"] >= tneed and all(x["pf"] >= 1.15 for x in pa),
                             f"{sa['n']} trades <= $100 risk: ${sa['mean']:+.2f}, t {sa['t']:+.2f}, PF "
                             + "/".join(f"{x['pf']:.2f}" for x in pa)),
            "6 real costs": (False, "not measured yet"),
        }
        print(f"\n{NAME[p]}")
        for kk, (passed, note) in g.items():
            print(f"  {kk:16s} {'PASS' if passed else 'FAIL'}   {note}")
        gate_rows.append(all(v[0] for v in g.values()))
    print("\nDEPLOYMENT DECISION:", "PAPER RUN ALLOWED" if any(gate_rows) else "NO DEPLOYMENT (no policy passes the gate)")

    print("\n=== 7. FORWARD-LIKE CHECK: MGC1! 5m, Sep 25 -> Nov 6 2026 (this rule has never seen it) ===")
    m5 = np.array(json.load(open(MGC5)), dtype=np.float64)
    mk2 = Market(frame(m5[:, 0], m5[:, 1:]))
    s2 = mk2.signals(since=pd.Timestamp("2026-09-25", tz=NY))
    print(f"  MGC 5m {mk2.t5[0]} -> {mk2.t5[-1]}; signals since Sep 25: {len(s2)}")
    if not s2: raise SystemExit("  no signals in the unseen weeks")
    P2 = {p: per_contract(mk2, s2, p) for p in POL}
    print("  day         spike  dir    stop$   " + "   ".join(f"{p}: exit / net$" for p in POL))
    for i, s in enumerate(s2):
        print(f"  {s['day'].date()}  {s['clock'] // 60:02d}:{s['clock'] % 60:02d}  {'long ' if s['d'] == 1 else 'short'}"
              f"  {P2['A'].R.iat[i] * USD:6.0f}   " + "   ".join(
                  f"{P2[p].why.iat[i]:>9s} {P2[p].net_usd.iat[i]:+6.0f}" for p in POL))
    for p in POL:
        print(f"  {NAME[p]:27s} " + fmt(st(P2[p].net_usd)))
    r2 = run_account(mk2, s2, "A", log=True, **ACCT)
    for kind, nm in (("dec", "decisions"), ("fills", "fills"), ("T", "trades")):
        r2[kind].to_csv(OUT + f"logs/{nm}_MGC_A.csv", index=False)
    acct_line("A on MGC, fresh $10,000", r2)
