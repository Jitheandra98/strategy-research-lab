"""Causal first-touch research contract (frozen before outcomes).

Only complete UTC 4H buckets and three adjacent buckets may birth an FVG.
Birth is HTF close; first_seen is the first observed LTF opening at/after birth.
First_seen can consume visit #1. Orders are eligible only on the following
LTF bar, from information available at the previous confirmed close. ATR14
is Wilder RMA seeded by 14 true ranges; EMA50 is LTF, lagged at planning.
Zone bounds 2..150 points, age 20 calendar days, capacity 200, no trend gate
except the declared EMA50 ablation. Close-through (strict) invalidates.
Distinct visits need a fully outside bar between overlaps. Reclaim window
includes first-visit bar and the following three contiguous LTF bars.
No price-path interpolation: stops win, entry-bar targets are never credited.
All fills use frozen planning ATR; gap-through-stop entries are rejected.
Eight calendar hours is the outcome horizon. Missing horizon bars and end
truncation are censored ex post, never invented. Splits cannot share samples.
Ten configurations are frozen (five entry/filter variants x two exits).
Validation selects once, >=10 closed uncensored trades, positive expectancy
at 1 point cost and positive lower block-bootstrap CI; otherwise no model.
Holdout never selects. Unknown feed provenance forbids sizing/currency P&L.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import hashlib
import json
import math

import numpy as np
import pandas as pd

H4 = 4 * 3600
H8 = 8 * 3600
DAY = 86400
COSTS = (0.0, 0.5, 1.0, 2.0)
ENTRIES = ('FT_LIMIT', 'REPEAT_LIMIT', 'FT_RECLAIM', 'FLIP_LIMIT', 'FT_LIMIT_EMA50')
EXITS = ('ZONE_2R', 'ATR_1_5R')
CONFIGS = tuple((entry, exit_) for entry in ENTRIES for exit_ in EXITS)


def load_bars(path: Path, step: int):
    """Fail closed on ambiguous timestamps/OHLC; never deduplicate silently."""
    raw = path.read_bytes()
    df = pd.DataFrame(json.loads(raw))
    required = ['time', 'open', 'high', 'low', 'close']
    if not set(required).issubset(df.columns):
        raise ValueError('Missing required timestamp/OHLC fields')
    values = df[required].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite timestamp/OHLC')
    t = df.time.to_numpy(dtype=float)
    if not np.equal(t, np.floor(t)).all() or np.any(np.diff(t) <= 0):
        raise ValueError('Timestamps must be unique, strictly increasing integer seconds')
    if np.any(t % step):
        raise ValueError('Off-grid LTF timestamp')
    if np.any(df.low > df[['open', 'close']].min(axis=1)) or np.any(df.high < df[['open', 'close']].max(axis=1)) or np.any(df.high < df.low):
        raise ValueError('Invalid OHLC envelope')
    df['time'] = df.time.astype('int64')
    delta = np.diff(df.time.to_numpy())
    gaps = [{'previous_open': int(t[i]), 'next_open': int(t[i+1]),
             'seconds_between_opens': int(d), 'unobserved_buckets': int(d // step - 1)}
            for i, d in enumerate(delta) if d != step]
    audit = dict(source=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(),
                 rows=len(df), step_seconds=step, first_open=int(t[0]), last_open=int(t[-1]),
                 observed_utc_days=int(df.time.floordiv(DAY).nunique()), gaps=len(gaps),
                 missing_ltf_buckets=sum(g['unobserved_buckets'] for g in gaps),
                 max_open_gap_seconds=int(delta.max()) if len(delta) else 0,
                 duplicates=0, out_of_order=0, off_grid=0, provenance='UNKNOWN',
                 timestamp_assumption='Unix seconds represent LTF bar openings; not externally verified',
                 alignment='Synthetic UTC-clock 4H; not exact broker-session aggregation')
    return df, audit, pd.DataFrame(gaps)


def aggregate_4h(df: pd.DataFrame, step: int):
    """A bucket must contain exactly all expected openings, with no fill-forward."""
    if H4 % step:
        raise ValueError('LTF does not divide UTC four hours')
    rows, rejected = [], []
    for bucket, g in df.groupby(df.time // H4, sort=True):
        start = int(bucket * H4)
        expected = np.arange(start, start + H4, step)
        if not np.array_equal(g.time.to_numpy(), expected):
            rejected.append(dict(time=start, observed=len(g), required=len(expected)))
            continue
        rows.append(dict(time=start, close_time=start+H4, open=float(g.open.iloc[0]),
                         high=float(g.high.max()), low=float(g.low.min()),
                         close=float(g.close.iloc[-1])))
    htf = pd.DataFrame(rows, columns=['time', 'close_time', 'open', 'high', 'low', 'close'])
    total = int(df.time.iloc[-1] // H4 - df.time.iloc[0] // H4 + 1) if len(df) else 0
    return htf, dict(total_clock_buckets=total, complete_buckets=len(rows),
                     partial_buckets=len(rejected), empty_buckets=total-len(rows)-len(rejected),
                     partial_bucket_details=rejected)


def indicators(df: pd.DataFrame, period: int = 14):
    prev = df.close.shift(1)
    tr = pd.concat([df.high-df.low, (df.high-prev).abs(), (df.low-prev).abs()], axis=1).max(axis=1).to_numpy()
    atr = np.full(len(df), np.nan)
    if len(df) >= period:
        atr[period-1] = tr[:period].mean()
        for i in range(period, len(df)):
            atr[i] = (atr[i-1] * (period-1) + tr[i]) / period
    # Pine ta.ema-style first-value recursive seed; require 50 observed closes.
    ema = df.close.ewm(span=50, adjust=False).mean().to_numpy()
    ema[:49] = np.nan
    # A causal descriptive volatility regime: ATR vs previous 100 observed ATRs.
    baseline = pd.Series(atr).shift(1).rolling(100, min_periods=50).median().to_numpy()
    return atr, ema, baseline


@dataclass
class Zone:
    id: str
    direction: int
    lo: float
    hi: float
    birth: int
    seen_i: int
    seen_time: int
    origin_birth: int
    phase: str = 'original'
    parent_id: str = ''
    active: bool = True
    visits: int = 0
    outside: bool = True
    first_i: Optional[int] = None
    first_time: Optional[int] = None
    reclaim_used: bool = False

    @property
    def near(self):
        return self.hi if self.direction == 1 else self.lo

    @property
    def far(self):
        return self.lo if self.direction == 1 else self.hi

    def proper(self, price):
        return self.direction * (price - self.near) > 0

    def invalid(self, close):
        return self.direction * (close - self.far) < 0


@dataclass(frozen=True)
class Plan:
    zone_id: str
    direction: int
    near: float
    far: float
    birth: int
    planned_time: int
    signal_time: int
    atr: float
    prior_close: float
    ema: float
    trend: str
    volatility: str
    order_kind: str = 'limit'


def zone_births(htf: pd.DataFrame, df: pd.DataFrame, min_width=2., max_width=150.):
    result = {}
    tt = df.time.to_numpy()
    for i in range(2, len(htf)):
        a, b, c = (htf.iloc[j] for j in (i-2, i-1, i))
        if int(b.time-a.time) != H4 or int(c.time-b.time) != H4:
            continue
        if c.low > a.high:
            d, lo, hi = 1, float(a.high), float(c.low)
        elif c.high < a.low:
            d, lo, hi = -1, float(c.high), float(a.low)
        else:
            continue
        if not min_width <= hi-lo <= max_width:
            continue
        birth = int(c.close_time)
        seen = int(np.searchsorted(tt, birth))
        if seen == len(df):
            continue
        z = Zone(f'Z{birth}_{d}', d, lo, hi, birth, seen, int(tt[seen]), birth)
        result.setdefault(seen, []).append(z)
    return result


def build_tape(df, step, htf=None, injected_zones=None, max_zones=200, max_age_days=20):
    """Plans precede OHLC inspection; visits/invalidation/reclaim run at close.

    injected_zones is a testing seam: events still obey first_seen eligibility.
    Plans for current bar are snapshots from the preceding confirmed bar. A
    missing next LTF bucket cancels outstanding entries and reclaim continuity.
    Indicators retain observed-bar history across gaps (ATR includes gap TR).
    """
    if htf is None:
        htf, _ = aggregate_4h(df, step)
    births = zone_births(htf, df) if injected_zones is None else injected_zones
    atr, ema, baseline = indicators(df)
    plans = [{k: [] for k in ENTRIES} for _ in range(len(df))]
    active, all_zones, events, visits = [], [], [], []
    t = df.time.to_numpy(dtype='int64')
    pending_reclaims = []

    def emit(kind, z, i, **extra):
        events.append(dict(event=kind, zone_id=z.id, parent_id=z.parent_id,
                           time=int(t[i]), available_at=int(t[i]+step), bar_i=i,
                           direction=z.direction, lo=z.lo, hi=z.hi, birth=z.birth,
                           first_seen=z.seen_time, eligible_after_close=z.seen_time+step,
                           phase=z.phase, visit_n=z.visits, **extra))

    def snapshot(z, i, kind='limit', signal_time=None):
        p, a, e = float(df.close.iloc[i-1]), float(atr[i-1]), float(ema[i-1])
        trend = 'unknown' if not math.isfinite(e) else ('aligned' if z.direction*(p-e) > 0 else 'opposed')
        v = 'unknown' if not math.isfinite(baseline[i-1]) else ('high' if a > baseline[i-1] else 'low')
        return Plan(z.id, z.direction, z.near, z.far, z.birth, int(t[i-1]+step),
                    int(t[i-1] if signal_time is None else signal_time), a, p, e, trend, v, kind)

    for i, row in enumerate(df.itertuples(index=False)):
        now = int(row.time)
        contiguous = i > 0 and now-int(t[i-1]) == step
        for z in active:
            if z.active and now-z.origin_birth >= max_age_days*DAY:
                z.active = False
                emit('expire', z, i)
        active = [z for z in active if z.active]
        # Newly visible zones cannot be planned until this bar has closed.
        for original in births.get(i, []):
            z = Zone(**asdict(original))
            active.append(z)
            all_zones.append(z)
            emit('first_seen', z, i)
        while len(active) > max_zones:
            z = min(active, key=lambda q: (q.origin_birth, q.id))
            z.active = False
            active.remove(z)
            emit('capacity_evict', z, i)

        if contiguous and math.isfinite(atr[i-1]) and atr[i-1] > 0:
            for z in active:
                if i <= z.seen_i or not z.proper(float(df.close.iloc[i-1])):
                    continue
                plan = snapshot(z, i)
                if z.phase == 'flip':
                    if z.visits == 0:
                        plans[i]['FLIP_LIMIT'].append(plan)
                else:
                    if z.visits == 0:
                        plans[i]['FT_LIMIT'].append(plan)
                        if plan.trend == 'aligned':
                            plans[i]['FT_LIMIT_EMA50'].append(plan)
                    elif z.outside:
                        plans[i]['REPEAT_LIMIT'].append(plan)
            for z, signal_i in pending_reclaims:
                if z.active and i > z.seen_i:
                    plans[i]['FT_RECLAIM'].append(snapshot(z, i, 'market', int(t[signal_i])))
        pending_reclaims = []
        # Ranking is frozen before current-bar price can decide which orders fill.
        for entry in ENTRIES:
            plans[i][entry].sort(key=lambda p: (abs(p.near-p.prior_close), p.birth, p.zone_id))

        flips = []
        for z in active:
            if not contiguous and z.first_i is not None:
                z.reclaim_used = True
            overlap = row.low <= z.hi and row.high >= z.lo
            if overlap and z.outside:
                z.visits += 1
                z.outside = False
                if z.first_i is None:
                    z.first_i, z.first_time = i, now
                emit('visit', z, i)
                visits.append(dict(zone_id=z.id, time=now, bar_i=i, direction=z.direction,
                                   phase=z.phase, visit_n=z.visits, first=z.visits == 1,
                                   near=z.near, far=z.far, lo=z.lo, hi=z.hi,
                                   birth=z.birth, first_seen=z.seen_time,
                                   eligible=i > z.seen_i, atr=float(atr[i-1]) if i else np.nan))
            elif not overlap:
                z.outside = True
            if z.invalid(row.close):
                z.active = False
                emit('invalidate', z, i)
                if z.phase == 'original':
                    f = Zone(z.id+'F', -z.direction, z.lo, z.hi, now+step, i,
                             now, z.origin_birth, 'flip', z.id)
                    flips.append(f)
                    all_zones.append(f)
                    emit('flip_armed', f, i)
                continue
            if (z.phase == 'original' and z.first_i is not None and not z.reclaim_used
                    and z.first_i > z.seen_i and i-z.first_i <= 3 and z.proper(row.close)):
                pending_reclaims.append((z, i))
                z.reclaim_used = True
                emit('reclaim_confirmed', z, i)
        active = [z for z in active if z.active] + flips
        while len(active) > max_zones:
            z = min(active, key=lambda q: (q.origin_birth, q.id))
            z.active = False
            active.remove(z)
            emit('capacity_evict', z, i)
    return dict(plans=plans, events=pd.DataFrame(events), visits=pd.DataFrame(visits),
                zones=pd.DataFrame([asdict(z) for z in all_zones]), atr=atr, ema=ema)


@dataclass
class Position:
    zone_id: str
    direction: int
    entry_i: int
    entry_time: int
    entry_price: float
    stop: float
    target: float
    risk: float
    atr: float
    planned_time: int
    signal_time: int
    trend: str
    volatility: str
    deadline: int


def try_fill(plan: Plan, row, i: int, exit_family: str):
    """None means no fill, never a search for a different touched candidate."""
    if not math.isfinite(plan.atr) or plan.atr <= 0:
        return None, 'atr_unavailable'
    d = plan.direction
    anchor = row.open if plan.order_kind == 'market' else plan.near
    stop = plan.far-d*0.25*plan.atr if exit_family == 'ZONE_2R' else anchor-d*plan.atr
    reward = 2.0 if exit_family == 'ZONE_2R' else 1.5
    if plan.order_kind == 'limit':
        crossed = row.open <= plan.near if d == 1 else row.open >= plan.near
        touched = row.low <= plan.near if d == 1 else row.high >= plan.near
        if not touched and not crossed:
            return None, 'not_touched'
        fill = float(row.open if crossed else plan.near)
    else:
        fill = float(row.open)
    risk = d * (fill-stop)
    if not math.isfinite(risk) or risk <= 0:
        return None, 'opening_beyond_stop'
    return Position(plan.zone_id, d, i, int(row.time), fill, stop, fill+d*reward*risk,
                    risk, plan.atr, plan.planned_time, plan.signal_time,
                    plan.trend, plan.volatility, int(row.time)+H8), 'filled'


def exit_on_bar(pos: Position, row, i: int, step: int):
    """Conservative OHLC chronology; gap stops precede timeout, then bar stops."""
    d = pos.direction
    if d*(row.open-pos.stop) <= 0:
        return float(row.open), 'gap_stop', int(row.time)
    if row.time >= pos.deadline:
        return float(row.open), 'timeout_gap', int(row.time)
    hit_stop = row.low <= pos.stop if d == 1 else row.high >= pos.stop
    hit_target = row.high >= pos.target if d == 1 else row.low <= pos.target
    if hit_stop:
        return pos.stop, 'stop', int(row.time+step)
    if i > pos.entry_i and hit_target:
        return pos.target, 'target', int(row.time+step)
    if row.time+step >= pos.deadline:
        return float(row.close), 'timeout', int(row.time+step)
    return None


def full_window(times, start_i, hours, step, boundary_end):
    n = int(hours*3600 // step)
    start = int(times[start_i])
    if start + hours*3600 > boundary_end:
        return False, 'split_boundary'
    if start_i+n > len(times):
        return False, 'end_data_horizon'
    if not np.array_equal(times[start_i:start_i+n], np.arange(start, start+n*step, step)):
        return False, 'gap_horizon'
    return True, ''


def simulate(df, step, tape, entry, exit_family, start, end, split, dataset_end=None):
    """Independent split runs warm lifecycle/indicators but start flat.

    The known split-end boundary prevents samples crossing partitions. Dataset
    tail horizon checks are ex post, preserving causal fills/prefix invariance.
    """
    times = df.time.to_numpy()
    dataset_end = int(times[-1]+step) if dataset_end is None else dataset_end
    trades, rejected = [], []
    pos = None

    def finish(position, outcome, censored_reason=''):
        record = asdict(position)
        record.update(entry_model=entry, exit_family=exit_family, config=entry+'__'+exit_family,
                      split=split, exit_price=None, exit_time=None, reason='end_data_open', gross_r=None)
        valid, reason = full_window(times, position.entry_i, 8, step, end if end < dataset_end else 2**62)
        if outcome is not None:
            price, why, when = outcome
            record.update(exit_price=price, exit_time=when, reason=why,
                          gross_r=position.direction*(price-position.entry_price)/position.risk)
        record['censor_reason'] = censored_reason or ('' if valid else reason)
        if outcome is None and not record['censor_reason']:
            record['censor_reason'] = 'end_data_open'
        record['evaluable'] = outcome is not None and not record['censor_reason']
        trades.append(record)

    for i, row in enumerate(df.itertuples(index=False)):
        if row.time < start:
            continue
        if row.time >= end:
            break
        # A model busy at this bar's open cannot create a hindsight same-bar entry.
        if pos is not None:
            outcome = exit_on_bar(pos, row, i, step)
            if outcome:
                finish(pos, outcome)
                pos = None
            continue
        candidates = tape['plans'][i][entry]
        if not candidates:
            continue
        p = candidates[0]
        if p.signal_time < start:
            continue
        if end < dataset_end and row.time+H8 > end:
            rejected.append(dict(time=int(row.time), zone_id=p.zone_id, reason='split_horizon_embargo'))
            continue
        pos, status = try_fill(p, row, i, exit_family)
        if status == 'opening_beyond_stop':
            rejected.append(dict(time=int(row.time), zone_id=p.zone_id, reason=status))
        if pos:
            outcome = exit_on_bar(pos, row, i, step)
            if outcome:
                finish(pos, outcome)
                pos = None
    if pos is not None:
        finish(pos, None, 'split_end_open' if end < dataset_end else '')
    return pd.DataFrame(trades), pd.DataFrame(rejected)


def chronological_splits(df, step):
    """60/20/20 observed rows, snapped forward to UTC day boundaries."""
    times = df.time.to_numpy()
    n = len(times)
    bounds = [int(times[0])]
    for fraction in (.6, .8):
        tentative = int(times[int(n*fraction)])
        boundary = int(math.ceil(tentative / DAY) * DAY)
        bounds.append(boundary)
    bounds.append(int(times[-1]+step))
    if not all(a < b for a, b in zip(bounds, bounds[1:])):
        raise ValueError('Dataset too short for distinct day-aligned partitions')
    return [(name, a, b) for name, a, b in zip(('train', 'validation', 'holdout'), bounds, bounds[1:])]


def descriptive_visits(df, step, tape, splits):
    """Excursions from near edge include touch bar (pre-touch extremes unknown).

    These are descriptive envelope measures, not achievable intrabar fills.
    Visit windows can overlap. Gap/split/tail censoring requires a full horizon.
    """
    rows = []
    times = df.time.to_numpy()
    visits = tape['visits']
    if visits.empty:
        return pd.DataFrame()
    for v in visits.to_dict('records'):
        if v['phase'] != 'original':
            continue
        split = next((x for x in splits if x[1] <= v['time'] < x[2]), None)
        if split is None:
            continue
        for hours in (4, 8):
            result = dict(**v, split=split[0], hours=hours, mfe_atr=None, mae_atr=None,
                          terminal_atr=None, evaluable=False, censor_reason='')
            ok, reason = full_window(times, v['bar_i'], hours, step, split[2])
            if not np.isfinite(v['atr']) or v['atr'] <= 0:
                reason, ok = 'atr_unavailable', False
            if ok:
                g = df.iloc[v['bar_i']:v['bar_i']+int(hours*3600//step)]
                if v['direction'] == 1:
                    favorable, adverse = g.high.max()-v['near'], v['near']-g.low.min()
                else:
                    favorable, adverse = v['near']-g.low.min(), g.high.max()-v['near']
                result.update(evaluable=True, mfe_atr=max(0., favorable)/v['atr'],
                              mae_atr=max(0., adverse)/v['atr'],
                              terminal_atr=v['direction']*(g.close.iloc[-1]-v['near'])/v['atr'])
            result['censor_reason'] = reason
            rows.append(result)
    return pd.DataFrame(rows)


def block_bootstrap(values, days, start, end, reps=2000, block_days=5, seed=7102026):
    """Circular moving blocks of whole UTC calendar days, including empty days.

    Five-day blocks preserve within-day and short serial dependence. Insufficient
    occupied days (<10), blocks (<4), or valid replicates suppress inferential CI.
    """
    values, days = np.asarray(values, float), np.asarray(days, dtype='int64')
    if not len(values):
        return dict(low=None, high=None, sample_days=0, calendar_days=0, blocks=0, reliable=False)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite bootstrap values')
    calendar = np.arange(start//DAY, (end-1)//DAY+1)
    totals, counts = np.zeros(len(calendar)), np.zeros(len(calendar))
    for value, day in zip(values, days):
        j = int(day-calendar[0])
        if 0 <= j < len(calendar):
            totals[j] += value
            counts[j] += 1
    occupied = int(np.count_nonzero(counts))
    blocks = len(calendar)//block_days
    reliable = occupied >= 10 and blocks >= 4
    result = dict(low=None, high=None, sample_days=occupied, calendar_days=len(calendar),
                  blocks=blocks, reliable=reliable)
    if not reliable:
        return result
    rng = np.random.default_rng(seed)
    nblocks = math.ceil(len(calendar)/block_days)
    starts = rng.integers(0, len(calendar), size=(reps, nblocks))
    sample = ((starts[..., None]+np.arange(block_days)) % len(calendar)).reshape(reps, -1)[:, :len(calendar)]
    denominator = counts[sample].sum(axis=1)
    ok = denominator > 0
    if ok.mean() < .9:
        result['reliable'] = False
        return result
    estimates = totals[sample].sum(axis=1)[ok]/denominator[ok]
    result.update(low=float(np.quantile(estimates, .025)), high=float(np.quantile(estimates, .975)))
    return result


def trade_metrics(trades, cost, start, end, reps=2000):
    count = len(trades)
    valid = trades[trades.evaluable == True].copy() if count else pd.DataFrame()
    result = dict(cost_points=cost, entries=count, n=len(valid), censored=count-len(valid),
                  end_data_open=int((trades.reason == 'end_data_open').sum()) if count else 0,
                  timeouts=int(valid.reason.isin(['timeout', 'timeout_gap']).sum()) if len(valid) else 0,
                  all_timeouts=int(trades.reason.isin(['timeout', 'timeout_gap']).sum()) if count else 0,
                  longs=int((valid.direction == 1).sum()) if len(valid) else 0,
                  shorts=int((valid.direction == -1).sum()) if len(valid) else 0,
                  expectancy_r=None, profit_factor=None, pf_infinite=False, max_drawdown_r=None,
                  win_rate=None)
    if not len(valid):
        result.update(ci_low=None, ci_high=None, sample_days=0, calendar_days=int(math.ceil((end-start)/DAY)),
                      bootstrap_reliable=False, blocks=0)
        return result
    net = (valid.gross_r - cost/valid.risk).to_numpy(dtype=float)
    wins, losses = net[net > 0].sum(), -net[net < 0].sum()
    equity = np.r_[0., net.cumsum()]
    bootstrap = block_bootstrap(net, valid.entry_time.to_numpy()//DAY, start, end, reps)
    result.update(expectancy_r=float(net.mean()), profit_factor=float(wins/losses) if losses else None,
                  pf_infinite=bool(not losses and wins > 0),
                  max_drawdown_r=float(np.max(np.maximum.accumulate(equity)-equity)),
                  win_rate=float(np.mean(net > 0)), ci_low=bootstrap['low'], ci_high=bootstrap['high'],
                  sample_days=bootstrap['sample_days'], calendar_days=bootstrap['calendar_days'],
                  bootstrap_reliable=bootstrap['reliable'], blocks=bootstrap['blocks'])
    return result
