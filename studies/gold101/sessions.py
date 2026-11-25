"""Clock-window setups, using complete reference ranges and fixed UTC-6 for #101."""
from datetime import timezone, timedelta
from collections import defaultdict

import numpy as np
import pandas as pd

CHICAGO = 'America/Chicago'
LONDON = 'Europe/London'
FIXED = timezone(timedelta(hours=-6))


def windows(df, zone, start, width, span):
    local = df.index.tz_convert(zone)
    minute = local.hour * 60 + local.minute
    offsets = np.asarray((minute - start) % 1440)
    indices = np.flatnonzero(offsets < span)
    chunks = np.split(indices, np.flatnonzero(np.diff(offsets[indices]) <= 0) + 1)
    for ix in chunks:
        if not len(ix):
            continue
        ref = ix[offsets[ix] < width]
        if not np.array_equal(offsets[ref], np.arange(0, width, 5)):
            continue
        following = ix[offsets[ix] >= width]
        if len(following):
            deadline = df.index[ref[0]].value + span * 60_000_000_000
            yield ref, following, deadline


def rvol(df):
    local = df.index.tz_convert(CHICAGO)
    clock = local.hour * 60 + local.minute
    baseline = df.v.groupby(clock).transform(lambda v: v.shift().rolling(20, min_periods=20).median())
    return (df.v / baseline.replace(0, np.nan)).to_numpy()


def signals(df, emit):
    o,h,l,c,v = df[list('ohlcv')].to_numpy().T
    rv = rvol(df)
    outputs = defaultdict(list)

    def record(ident, i, side, stop, target, deadline):
        outputs[ident].append((i, side, stop, target, deadline))

    rules = [
        # id, zone, start, reference width, signal window end, exit time, R, filters
        (1, CHICAGO, 1080, 360, 480, 480, 2, 'narrow'),
        (2, LONDON, 120, 30, 120, 120, 2, 'rvol'),
        (4, CHICAGO, 440, 30, 100, 190, 2, ''),
        (7, CHICAGO, 630, 90, 150, 180, 1.5, 'narrow'),
        (8, LONDON, 630, 10, 45, 45, 1.5, 'impulse'),
        (101, FIXED, 1080, 30, 120, 120, 2, ''),
    ]
    for ident, zone, start, width, span, end, multiple, condition in rules:
        if condition == 'rvol' and not df.v.gt(0).any():
            continue
        history = []
        for ref, after, _ in windows(df, zone, start, width, span):
            high, low = h[ref].max(), l[ref].min()
            narrow = len(history) >= 20 and high-low < np.median(history[-20:])
            history.append(high-low)
            if condition == 'narrow' and not narrow:
                continue
            for i in after:
                side = 1 if c[i] > high else -1 if c[i] < low else 0
                if not side or (condition == 'rvol' and not rv[i] > 1.5):
                    continue
                if condition == 'impulse' and side * (c[ref[-1]] - o[ref[0]]) <= 0:
                    continue
                record(ident, i, side, (high+low)/2, np.nan,
                       df.index[ref[0]].value + end * 60_000_000_000)
                break
        send(ident, outputs, emit, multiple)

    fades = [
        (3, LONDON, 420, 60, 180, 180, None),
        (9, LONDON, 870, 30, 75, 75, 10),
        (10, CHICAGO, 735, 15, 45, 75, None),
    ]
    for ident, zone, start, width, span, end, excursion_window in fades:
        for ref, after, _ in windows(df, zone, start, width, span):
            high, low = h[ref].max(), l[ref].min()
            upper, lower = -np.inf, np.inf
            if excursion_window is not None:
                first = after[df.index[after] < df.index[after[0]] + pd.Timedelta(minutes=excursion_window)]
                upper, lower = h[first].max(), l[first].min()
                after = after[len(first):]
            for i in after:
                if excursion_window is None:
                    upper, lower = max(upper, h[i]), min(lower, l[i])
                if low < c[i] < high and (upper > high) != (lower < low):
                    side = -1 if upper > high else 1
                    record(ident, i, side, upper if side == -1 else lower,
                           (high+low)/2, df.index[ref[0]].value + end * 60_000_000_000)
                    break
                if excursion_window is not None:
                    if upper > high:
                        upper = max(upper, h[i])
                    if lower < low:
                        lower = min(lower, l[i])
        send(ident, outputs, emit, None)

    moves = []
    for ref, after, deadline in windows(df, CHICAGO, 440, 30, 160):
        move = c[ref[-1]] - o[ref[0]]
        strong = len(moves) >= 20 and abs(move) > np.median(moves[-20:])
        moves.append(abs(move))
        if not strong:
            continue
        side = int(np.sign(move))
        for j, i in enumerate(after[2:], 2):
            a,b = after[j-2:j]
            if b != i-1 or a != b-1:
                continue
            if side * (c[b]-c[a]) >= 0 or side * (c[a]-c[a-1]) >= 0:
                continue
            if (c[i] > max(h[a],h[b]) if side == 1 else c[i] < min(l[a],l[b])):
                record(5, i, side, min(l[a],l[b]) if side == 1 else max(h[a],h[b]), np.nan, deadline)
                break
    send(5, outputs, emit, 2)

    if df.v.gt(0).any():
        # The overnight window begins at the 17:00 Globex reopen.
        for ref, after, _ in windows(df, CHICAGO, 1020, 860, 960):
            # 7:20 is not divisible by five from 17:00? 860 minutes is exact.
            high, low = h[ref].max(), l[ref].min()
            if v[ref].sum() <= 0 or high <= low:
                continue
            vw = np.average((h[ref]+l[ref]+c[ref])/3, weights=v[ref])
            rank = (o[after[0]]-low)/(high-low)
            side = -1 if rank >= .75 else 1 if rank <= .25 else 0
            if not side:
                continue
            for i in after:
                if side*(c[i]-vw) > 0 >= side*(c[i-1]-vw):
                    ix = np.arange(after[0], i+1)
                    stop = h[ix].max() if side == -1 else l[ix].min()
                    record(6, i, side, stop, (high+low)/2,
                           df.index[ref[0]].value + 1020 * 60_000_000_000)
                    break
        send(6, outputs, emit, None)


def send(ident, outputs, emit, multiple):
    if outputs[ident]:
        ix, side, stop, target, deadline = (np.asarray(col) for col in zip(*outputs[ident]))
    else:
        ix, side, stop, target, deadline = [], 1, [], [], []
    emit(ident, ix, side, stop, target, multiple, 288, deadline=deadline)
