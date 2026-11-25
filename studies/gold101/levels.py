"""Prior-session references and failed moves (#41–60).

#45–46 require official settlements and are intentionally absent.
The session changes at 17:00 Chicago time. The first reported open of that
session/week supplies the open only if the 17:00 bar was present. A change in
the optional symbol field invalidates prior levels built from a different
contract. For #48 the proximity check uses the previous close. In #53 the
pattern height uses the second trough. An intrabar low used for a sweep must
be strictly beyond the reference and a reclaim must finish strictly inside.
"""
import numpy as np
import pandas as pd


def signals(df, emit):
    o, h, l, c, atr = (df[col] for col in ("o", "h", "l", "c", "atr"))
    idx = df.index
    chicago = idx.tz_convert("America/Chicago").tz_localize(None)
    date = pd.Series((chicago + pd.Timedelta(hours=7)).normalize(), index=idx)
    week = date - pd.to_timedelta(date.dt.dayofweek, unit="D")
    symbol = df["symbol"] if "symbol" in df else pd.Series(1, index=idx)
    # Segment ID also prevents matching levels across switches back to an earlier symbol.
    contract = symbol.ne(symbol.shift()).cumsum()
    gap = pd.Series(idx.to_series().diff().ne(pd.Timedelta(minutes=5)), index=idx)
    session_break = date.ne(date.shift()) | contract.ne(contract.shift())
    pattern_break = session_break | gap
    session = session_break.cumsum()

    def add(id, cond, side, stop, target=None, r=None, bars=12):
        rows = np.flatnonzero(np.asarray(cond, dtype=bool))
        def take(value):
            return value if value is None or np.isscalar(value) else np.asarray(value)[rows]
        emit(id, rows, take(side), take(stop), take(target), r, bars)

    def previous_period(period):
        groups = df.assign(period=period, contract=contract, stamp=chicago).groupby(
            ["period", "contract"], sort=False
        )
        agg = groups.agg(
            hi=("h", "max"), lo=("l", "min"), op=("o", "first"),
            cl=("c", "last"), first_stamp=("stamp", "first")
        )
        keys = pd.MultiIndex.from_arrays([period, contract])
        prior = agg.groupby(level="contract", sort=False).shift().reindex(keys)
        prior.index = idx
        now = agg.reindex(keys)
        now.index = idx
        now["op"] = now.op.where(now.first_stamp.dt.hour.eq(17) & now.first_stamp.dt.minute.eq(0))
        return prior, now

    yesterday, today = previous_period(date)
    last_week, this_week = previous_period(week)
    yesterday_hi, yesterday_lo = yesterday.hi, yesterday.lo
    yesterday_mid = (yesterday_hi + yesterday_lo) / 2
    last_week_mid = (last_week.hi + last_week.lo) / 2
    above = c.gt(yesterday_hi)
    second = above & c.shift().gt(yesterday_hi) & ~pattern_break
    already_above = c.shift(2).gt(yesterday_hi) & ~pattern_break.shift(fill_value=True)
    add(41, second & ~already_above, 1, np.minimum(l, l.shift()), r=2)
    add(42, l.lt(yesterday_lo) & c.gt(yesterday_lo), 1, l, r=2)
    add(43, h.gt(last_week.hi) & c.lt(last_week.hi), -1, h, r=2)
    prev_six = c.shift().rolling(6).max()
    add(44, c.gt(last_week_mid) & prev_six.lt(last_week_mid)
        & week.eq(week.shift(6)) & contract.eq(contract.shift(6)), 1, l, r=2, bars=18)

    # Wilder smoothed directional movement. Use only values observed by the close.
    up, down = h.diff(), -l.diff()
    pos_dm = up.where((up > down) & (up > 0), 0)
    neg_dm = down.where((down > up) & (down > 0), 0)
    pos_sm = pos_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    neg_sm = neg_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    dx = 100 * (pos_sm - neg_sm).abs() / (pos_sm + neg_sm).replace(0, np.nan)
    adx = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    under = l.lt(yesterday_mid)
    prior_dip = under.groupby(session).cummax()
    dip_low = l.where(under).groupby(session).cummin().groupby(session).ffill()
    crossing = c.gt(yesterday_mid) & (
        (c.shift().le(yesterday_mid) & ~session_break) | under
    )
    qualify = today.op.between(yesterday_lo, yesterday_hi) & prior_dip & crossing & adx.lt(20)
    add(47, qualify & qualify.groupby(session).cumsum().eq(1), 1, dip_low, yesterday_hi)

    prev_close = c.shift()
    round_level = (prev_close / 25).round() * 25
    add(48, prev_close.sub(round_level).abs().le(0.5)
        & h.gt(round_level) & c.le(round_level - 0.5) & ~pattern_break,
        -1, h, r=1.5, bars=8)

    pivot = (yesterday.hi + yesterday.lo + yesterday.cl) / 3
    pivot_excursion = l.le(pivot - 0.5 * atr)
    # Start an excursion below the pivot and clear it on the first recovery.
    above = c.gt(pivot)
    runs = (session_break | above.shift(fill_value=False)).cumsum()
    reached = pivot_excursion.groupby(runs).cummax()
    excursion_low = l.groupby(runs).cummin()
    add(49, above & reached, 1, excursion_low, r=1.5, bars=10)

    prev_hour = c.shift().rolling(12).min()
    test = l.le(this_week.op) & c.gt(this_week.op) & prev_hour.gt(this_week.op)
    test &= week.eq(week.shift(12)) & contract.eq(contract.shift(12))
    test &= idx.to_series().diff(12).eq(pd.Timedelta(hours=1))
    week_group = (week.ne(week.shift()) | contract.ne(contract.shift())).cumsum()
    add(50, test & test.groupby(week_group).cumsum().eq(1), 1, l, r=2)

    # Swings are timestamped two bars after their center. Keep the first signal
    # for each distinct pattern, and require its reference and trigger to share
    # the same uninterrupted session.
    def swings(series, high):
        center = series.shift(2)
        compare = center.gt if high else center.lt
        complete = ~pattern_break.rolling(4, min_periods=4).max().fillna(1).astype(bool)
        return np.flatnonzero(
            compare(series) & compare(series.shift()) & compare(series.shift(3))
            & compare(series.shift(4)) & complete
        ) - 2

    sh, sl = swings(h, True), swings(l, False)
    contig = pattern_break.cumsum().to_numpy()
    av, hv, lv, cv = (series.to_numpy() for series in (atr, h, l, c))
    gains = c.diff().clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    losses = (-c.diff()).clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rsi = (100 * gains / (gains + losses).replace(0, np.nan)).to_numpy()

    def trigger_between(start, end, condition):
        return next((i for i in range(start, end)
                     if contig[i] == contig[start] and condition(i)), None)

    def next_swing_bound(swings, j, start):
        return min(len(df), swings[j + 1] + 2 if j + 1 < len(swings) else len(df),
                   int(np.searchsorted(contig, contig[start], side="right")))

    found = {id: [] for id in (51, 53, 54, 55)}
    for j, b in enumerate(sh[1:], 1):
        a = sh[j - 1]
        start = b + 2
        if contig[a] != contig[start]:
            continue
        end = next_swing_bound(sh, j, start)
        if abs(hv[b] - hv[a]) <= 0.2 * av[b]:
            low_edge, high_edge = sorted((hv[a], hv[b]))
            sig = trigger_between(start, end, lambda i: hv[i] > high_edge and cv[i] < low_edge)
            if sig is not None:
                found[51].append((sig, hv[sig], lv[a:b+1].min()))
        if j >= 2:
            first = sh[j - 2]
            if contig[first] != contig[start]:
                continue
            if 0 < hv[b] - hv[a] < hv[a] - hv[first]:
                last_low = sl[np.searchsorted(sl, b) - 1] if len(sl) else -1
                if not a < last_low < b:
                    continue
                neckline = lv[last_low]
                sig = trigger_between(start, end, lambda i: cv[i] < neckline)
                if sig is not None:
                    found[55].append((sig, hv[b], np.nan))

    for j, b in enumerate(sl[1:], 1):
        a = sl[j - 1]
        start = b + 2
        if contig[a] != contig[start]:
            continue
        double = abs(lv[b] - lv[a]) <= 0.25 * av[b]
        diverges = lv[b] < lv[a] and rsi[b] > rsi[a]
        if not (double or diverges):
            continue
        end = next_swing_bound(sl, j, start)
        neckline = hv[a:b+1].max()
        sig = trigger_between(start, end, lambda i: cv[i] > neckline)
        if sig is not None and double:
            found[53].append((sig, lv[b], neckline + neckline - lv[b]))
        if diverges:
            prior_high = np.searchsorted(sh, b) - 1
            if prior_high >= 0 and sh[prior_high] > a:
                swing_high = hv[sh[prior_high]]
                div_sig = trigger_between(start, end, lambda i: cv[i] > swing_high)
                if div_sig is not None:
                    found[54].append((div_sig, lv[b], np.nan))

    for id, side, r, bars in [(51, -1, None, 10), (53, 1, None, 12), (54, 1, 2, 12), (55, -1, 2, 12)]:
        matches = np.array(found[id]).reshape(-1, 3)
        emit(id, matches[:, 0].astype(int), side, matches[:, 1],
             matches[:, 2] if r is None else None, r, bars)

    # #52 follows the original broken edge until a reclaim plus a higher close.
    low20 = l.shift().rolling(20).min().to_numpy()
    high20 = h.shift().rolling(20).max().to_numpy()
    brk = pattern_break.to_numpy()
    down_breaks = np.flatnonzero((cv < low20) & ~brk)
    f52 = []
    next_allowed = 0
    for i in down_breaks:
        if i < next_allowed:
            continue
        end = int(np.searchsorted(contig, contig[i], side="right"))
        next_allowed = end
        edge, bottom = low20[i], lv[i]
        for j in range(i + 1, end - 1):
            bottom = min(bottom, lv[j])
            if lv[j] <= edge < cv[j] < cv[j + 1]:
                f52.append((j + 1, min(bottom, lv[j + 1]), (edge + high20[i]) / 2))
                next_allowed = j + 2
                break
    rows = np.array(f52).reshape(-1, 3)
    emit(52, rows[:, 0].astype(int), 1, rows[:, 1], rows[:, 2], None, 12)

    body = (o - c).abs()
    pin = l.lt(l.shift().rolling(30).min()) & (
        np.minimum(o, c) - l >= 2 * body
    ) & (c >= l + 0.75 * (h - l)) & h.gt(l)
    add(56, pin.shift(fill_value=False) & c.gt(h.shift()) & ~pattern_break,
        1, l.shift(), r=1.5, bars=8)
    four_down = c.diff().lt(0).shift().rolling(4).sum().eq(4)
    engulf = c.gt(o) & o.le(np.minimum(o.shift(), c.shift())) & c.ge(np.maximum(o.shift(), c.shift()))
    add(57, four_down & engulf & c.gt(h.shift()) & ~pattern_break,
        1, np.minimum(l, l.shift()), r=1.5, bars=8)

    mean = c.shift().rolling(30).mean()
    sd = c.shift().rolling(30).std(ddof=0).replace(0, np.nan)
    z = (c - mean) / sd
    recovery = z.gt(-2)
    z_group = (pattern_break | recovery.shift(fill_value=False)).cumsum()
    oversold = z.le(-2.5).groupby(z_group).cummax()
    z_low = l.groupby(z_group).cummin()
    add(58, recovery & oversold, 1, z_low, mean, bars=8)

    highs20 = h.shift().rolling(20).max()
    lows20 = l.shift().rolling(20).min()
    breakout = c.gt(highs20)
    after_high = h.rolling(3).max()
    same_run = pd.Series(contig, index=idx)
    stalled = breakout.shift(3, fill_value=False) & (
        after_high < c.shift(3) + 0.25 * atr.shift(3)
    ) & c.lt(highs20.shift(3)) & c.gt(lows20.shift(3)) & same_run.eq(same_run.shift(3))
    add(59, stalled, -1, h.rolling(4).max(), (highs20 + lows20).shift(3) / 2, bars=10)

    high12 = h.shift().rolling(12).max()
    low12 = l.shift().rolling(12).min()
    f60 = []
    high12a, low12a = high12.to_numpy(), low12.to_numpy()
    for i in np.flatnonzero((h > high12) & (l >= low12)):
        hi, lo = high12a[i], low12a[i]
        for j in range(i + 1, min(i + 7, len(df))):
            if brk[j]:
                break
            if lv[j] < lo:
                if lo < cv[j] < hi:
                    f60.append((j, lv[j], (hi + lo) / 2))
                break
    # Where multiple overlapping frozen ranges trigger together, use the first.
    rows = np.array(f60).reshape(-1, 3)
    _, unique = np.unique(rows[:, 0], return_index=True)
    rows = rows[unique]
    emit(60, rows[:, 0].astype(int), 1, rows[:, 1], rows[:, 2], None, 8)
