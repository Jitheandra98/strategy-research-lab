"""Gold day-trading setups 11–30 on completed five-minute bars.

Trend slopes without a specified lookback compare consecutive bars. Four- and
ten-bar impulses use close-to-close moves. A newer qualifying pattern replaces
an older pattern of the same setup. Multi-bar patterns stay in the same COMEX
trade date. Intraday indicators may warm up across trade dates.
"""

import numpy as np
import pandas as pd


def _cross_above(value, level):
    return (value > level) & (value.shift() <= level.shift())


def _cross_below(value, level):
    return (value < level) & (value.shift() >= level.shift())


def _first_in_pattern(condition, pattern):
    """Keep the first qualifying signal for each pattern identifier."""
    ordinal = condition.astype(int).groupby(pattern, sort=False).cumsum()
    return condition & (ordinal == 1)


def _completed_bars(df, minutes):
    grouped = df.resample(f"{minutes}min", label="right", closed="left")
    bars = grouped.agg({"o": "first", "h": "max", "l": "min", "c": "last"})
    return bars.loc[grouped["c"].count() == minutes // 5]


def signals(df, emit):
    h, low, c, o, atr = (df[name] for name in ("h", "l", "c", "o", "atr"))
    position = pd.Series(np.arange(len(df)), index=df.index)
    local = df.index.tz_convert("America/Chicago").tz_localize(None)
    day = pd.Series((local + pd.Timedelta(hours=7)).normalize(), index=df.index)
    same = lambda bars: day == day.shift(bars)
    prior_atr = atr.shift()
    high20 = h.shift().rolling(20).max()
    low20 = low.shift().rolling(20).min()
    ema9, ema20, ema21, ema50 = (
        c.ewm(span=span, adjust=False, min_periods=span).mean()
        for span in (9, 20, 21, 50)
    )

    def recent(value, event):
        return value.where(event).groupby(day, sort=False).ffill()

    def send(number, condition, direction, stop, target, r, bars, exit_signal=None):
        idx = np.flatnonzero(condition.fillna(False).to_numpy(dtype=bool))

        def select(value):
            return np.asarray(value)[idx] if not np.isscalar(value) and value is not None else value

        args = (number, idx, select(direction), select(stop), select(target), r, bars)
        if exit_signal is None:
            emit(*args)
        else:
            emit(*args, exit_signal.fillna(False).to_numpy(dtype=bool))

    # 11. Snapshot the high of the newest qualifying breakout.
    breakout20 = (c > high20) & (ema20 > ema20.shift()) & (c > ema20)
    pattern = recent(position, breakout20)
    touch = (position > pattern) & (low <= ema20) & (c > ema20)
    send(11, _first_in_pattern(touch, pattern), 1, low, recent(h, breakout20), None, 12)

    # 12. Shift the pivot by two bars before using it.
    pivot_high = h.shift(2).where(
        (h.shift(2) > h.shift(4)) & (h.shift(2) > h.shift(3))
        & (h.shift(2) > h.shift()) & (h.shift(2) > h) & same(4)
    )
    pivot_low = low.shift(2).where(
        (low.shift(2) < low.shift(4)) & (low.shift(2) < low.shift(3))
        & (low.shift(2) < low.shift()) & (low.shift(2) < low) & same(4)
    )

    def higher_pivots(pivot):
        points = pivot.dropna()
        change = points.groupby(day.reindex(points.index), sort=False).diff()
        consecutive = (change > 0) & (change.groupby(day.reindex(points.index), sort=False).shift() > 0)
        return recent(consecutive.astype(float).reindex(c.index), pivot.notna()).eq(1)

    last_high = recent(pivot_high, pivot_high.notna())
    last_low = recent(pivot_low, pivot_low.notna())
    send(12, higher_pivots(pivot_high) & higher_pivots(pivot_low) & _cross_above(c, last_high),
         1, last_low, None, 2, 18)

    # 13. Direction-specific crossover exits are handled on completed bars.
    fast_up = _cross_above(ema9, ema21)
    fast_down = _cross_below(ema9, ema21)
    send(13, fast_up & (ema50 > ema50.shift(5)), 1, low.shift().rolling(5).min(),
         None, None, 18, fast_down)
    send(13, fast_down & (ema50 < ema50.shift(5)), -1, h.shift().rolling(5).max(),
         None, None, 18, fast_up)

    # 14. Right-labeled higher-timeframe candles are available at their close.
    half_hour = _completed_bars(df, 30)
    ema30 = half_hour.c.ewm(span=20, adjust=False, min_periods=20).mean()
    up30 = (half_hour.c > ema30).reindex(df.index + pd.Timedelta(minutes=5), method="ffill")
    up30.index = df.index
    delta = c.diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rsi = 100 * avg_gain / (avg_gain + avg_loss)
    rsi_under = rsi < 40
    pullback = low.where(rsi_under | rsi_under.shift(fill_value=False)).groupby(
        [day, (~rsi_under).shift(fill_value=True).cumsum()], sort=False
    ).cummin()
    send(14, up30.eq(True) & (rsi > 40) & (rsi.shift() <= 40),
         1, pullback, None, None, 12, rsi >= 65)

    # 15. Qualify the flag after all three pullback bars have closed.
    move4 = c - c.shift(4)
    flag_high, flag_low = h.rolling(3).max(), low.rolling(3).min()
    impulse_end = c.shift(3)
    for direction in (1, -1):
        impulse = direction * move4
        retracement = impulse_end - flag_low if direction == 1 else flag_high - impulse_end
        flag = same(7) & (impulse.shift(3) >= 2 * atr.shift(4)) & (
            retracement < 0.5 * impulse.shift(3)
        )
        pattern = recent(position, flag)
        edge = recent(flag_high if direction == 1 else flag_low, flag)
        opposite = recent(flag_low if direction == 1 else flag_high, flag)
        condition = (position > pattern) & (direction * (c - edge) > 0)
        target = edge + direction * recent(impulse.shift(3), flag)
        send(15, _first_in_pattern(condition, pattern), direction, opposite, target, None, 12)

    # 16. Preserve the first breakout of a sequence of repeated new highs.
    break30 = c > h.shift().rolling(30).max()
    new_break30 = break30 & (~break30.shift(fill_value=False) | ~same(1))
    pattern = recent(position, new_break30)
    level30 = recent(h.shift().rolling(30).max(), new_break30)
    retest = position.sub(pattern).between(1, 6) & (low <= level30) & (c > level30)
    send(16, _first_in_pattern(retest, pattern), 1, low, None, 2, 12)

    # 17. Wilder-style directional indicators and ADX.
    up, down = h.diff(), -low.diff()
    plus = up.where((up > down) & (up > 0), 0).ewm(alpha=1 / 14, adjust=False).mean() / atr
    minus = down.where((down > up) & (down > 0), 0).ewm(alpha=1 / 14, adjust=False).mean() / atr
    adx = (100 * (plus - minus).abs() / (plus + minus)).ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()
    di_up, di_down = _cross_above(plus, minus), _cross_below(plus, minus)
    adx_filter = (adx > 25) & (adx > adx.shift())
    send(17, di_up & adx_filter, 1, low.shift().rolling(5).min(), None, None, 18, di_down)
    send(17, di_down & adx_filter, -1, h.shift().rolling(5).max(), None, None, 18, di_up)

    # 18. Fit the prior 30 closes and evaluate the channel one bar ahead.
    width = 30
    x = np.arange(width) - (width - 1) / 2
    if len(df) >= width:
        dot = np.convolve(c.to_numpy(), x[::-1], mode="valid")
        slope = pd.Series(np.r_[np.full(width - 1, np.nan), dot / np.dot(x, x)], index=c.index).shift()
        mean = c.shift().rolling(width).mean()
        variance = (c.shift().rolling(width).var(ddof=0) - slope.pow(2) * x.var()).clip(lower=0)
        fit = mean + slope * (width + 1) / 2
        lower, upper = fit - np.sqrt(variance), fit + np.sqrt(variance)
        breach = (low <= lower) | (c.shift() < lower.shift())
        breach_low = pd.concat([low, low.shift().where(c.shift() < lower.shift())], axis=1).min(axis=1)
        send(18, (slope > 0) & breach & (c > lower), 1, breach_low, upper, None, 12)

    # 19. Freeze the latest ten-bar impulse. Retracement starts after its high.
    impulse19 = same(10) & (c - c.shift(10) >= 3 * prior_atr) & (h > h.shift().rolling(9).max())
    pattern = recent(position, impulse19)
    peak = recent(h, impulse19)
    impulse_range = peak - recent(c.shift(10), impulse19)
    retrace_low = low.where(position > pattern).groupby(pattern, sort=False).cummin()
    pullback = (peak - retrace_low) / impulse_range
    trigger = (position > pattern) & pullback.between(0.33, 0.50) & (c > h.shift())
    send(19, _first_in_pattern(trigger, pattern), 1, retrace_low, peak, None, 12)

    # 20. The second consecutive upper-channel close confirms the entry.
    upper_k = ema20 + 1.5 * atr
    lower_k = ema20 - 1.5 * atr
    above_k = c > upper_k.shift()
    confirmed = above_k & above_k.shift(fill_value=False) & same(1)
    send(20, confirmed & ~confirmed.shift(fill_value=False) & (ema20 > ema20.shift()),
         1, low.rolling(2).min(), None, None, 18, c < ema20)

    # 21. Use the previous band's bounds and compare its width with prior widths.
    middle_b = c.rolling(20).mean()
    std_b = c.rolling(20).std(ddof=0)
    upper_b, lower_b = middle_b + 2 * std_b, middle_b - 2 * std_b
    band_width = 4 * std_b / middle_b
    compressed = band_width.shift() < band_width.shift(2).rolling(100).quantile(0.10)
    for direction, edge in ((1, upper_b), (-1, lower_b)):
        condition = compressed & (direction * (c - edge.shift()) > 0)
        send(21, condition, direction, middle_b.shift(), None, 2, 12)

    # 22. Preserve the parent range after the two inside bars complete.
    parent_high, parent_low = h.shift(2), low.shift(2)
    inside = same(2) & (h.rolling(2).max() <= parent_high) & (low.rolling(2).min() >= parent_low)
    pattern = recent(position, inside)
    edge_high, edge_low = recent(parent_high, inside), recent(parent_low, inside)
    outside = (position > pattern) & ((c > edge_high) | (c < edge_low))
    send(22, _first_in_pattern(outside, pattern), np.where(c > edge_high, 1, -1),
         (edge_high + edge_low) / 2, None, 1.5, 8)

    # 23. 15-minute bars can trigger on 5-minute bars only after completion.
    quarter = _completed_bars(df, 15)
    qrange = quarter.h - quarter.l
    qualifying = quarter.loc[qrange.eq(qrange.rolling(8).min()), ["h", "l"]].copy()
    qualifying["completed"] = qualifying.index
    observed_at = df.index + pd.Timedelta(minutes=5)
    known = qualifying.reindex(observed_at, method="ffill")
    age = observed_at - pd.DatetimeIndex(known["completed"])
    known.index = df.index
    outside = (age > pd.Timedelta(0)) & (age <= pd.Timedelta(minutes=30)) & (
        (c > known.h) | (c < known.l)
    )
    send(23, _first_in_pattern(outside, known["completed"]),
         np.where(c > known.h, 1, -1), np.where(c > known.h, known.l, known.h), None, 2, 8)

    # 24. A same-bar ATR recross and price break are both required.
    atr_median = atr.shift().rolling(50).median()
    quiet = (atr < atr_median).astype(int).shift().rolling(6).sum().eq(6)
    expansion = quiet & _cross_above(atr, atr_median)
    send(24, expansion & (c > high20), 1, low, None, 2, 12)
    send(24, expansion & (c < low20), -1, h, None, 2, 12)

    # 25. Match prior volume by Chicago clock time, with no current-bar volume in its baseline.
    minutes = local.hour * 60 + local.minute
    median_volume = df.v.groupby(minutes, sort=False).transform(lambda v: v.shift().rolling(20).median())
    big_volume = (df.v > 2 * median_volume) & (h - low > 1.5 * prior_atr)
    send(25, big_volume & (c > high20), 1, (h + low) / 2, None, 1.5, 8)
    send(25, big_volume & (c < low20), -1, (h + low) / 2, None, 1.5, 8)

    # 26. Trade the first retest of a frozen box edge.
    box_high = h.shift().rolling(6).max()
    box_low = low.shift().rolling(6).min()
    box = same(6) & (box_high - box_low < 1.5 * prior_atr)
    box_break = box & ((c > box_high) | (c < box_low))
    pattern = recent(position, box_break)
    is_long = recent((c > box_high).astype(float), box_break).eq(1)
    edge = recent(box_high.where(c > box_high, box_low), box_break)
    long_touch = is_long & (low <= edge) & (c > edge)
    short_touch = ~is_long & (h >= edge) & (c < edge)
    retest = position.sub(pattern).between(1, 6) & (long_touch | short_touch)
    send(26, _first_in_pattern(retest, pattern), np.where(is_long, 1, -1),
         low.where(is_long, h), None, 2, 12)

    # 27. Both closes refer to the range from before the first breakout.
    frozen_high, frozen_low = high20.shift(), low20.shift()
    accepted_long = same(1) & (c.shift() > frozen_high) & (c > c.shift())
    accepted_short = same(1) & (c.shift() < frozen_low) & (c < c.shift())
    send(27, accepted_long, 1, frozen_high, None, 2, 10)
    send(27, accepted_short, -1, frozen_low, None, 2, 10)

    # 28. Shock orientation is the candle body's direction.
    shock = ((h - low) >= 2.5 * prior_atr).shift(fill_value=False) & same(1)
    mid = ((h + low) / 2).shift()
    send(28, shock & (c.shift() > o.shift()) & (c < mid), -1, h.shift(), o.shift(), None, 6)
    send(28, shock & (c.shift() < o.shift()) & (c > mid), 1, low.shift(), o.shift(), None, 6)

    # 29. Prior six closes define compression; their high/low define the box.
    tight = c.shift().rolling(6).max() - c.shift().rolling(6).min() <= prior_atr
    send(29, same(6) & tight & (ema50.shift() > ema50.shift(2)) & (c > box_high),
         1, box_low, None, 2, 12)

    # 30. The release itself can be observed only when the current bar closes.
    inside_k = (upper_b <= upper_k) & (lower_b >= lower_k)
    was_inside = inside_k.shift(fill_value=False)
    send(30, was_inside & (upper_b > upper_k) & (c > upper_k.shift()),
         1, ema20.shift(), None, 2, 12)
    send(30, was_inside & (lower_b < lower_k) & (c < lower_k.shift()),
         -1, ema20.shift(), None, 2, 12)
