"""Historical screen with next-open entries and stop-first intrabar sequencing."""
from pathlib import Path
import argparse
import importlib

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPOT = ROOT / 'trading-video-intel/tools/pine_runner/xau5m.f64'
YAHOO = ROOT / 'trading-video-intel/data/raw/yahoo/GC_F_5m_20261001.csv'
BAR = pd.Timedelta(minutes=5)


def load(path):
    if path == SPOT:
        a = np.fromfile(path).reshape(-1, 5)
        scale = 1000 if a[0, 0] > 1e11 else 1
        df = pd.DataFrame(a[:, 1:], columns=list('ohlc'),
                          index=pd.to_datetime(a[:, 0] / scale, unit='s', utc=True))
        df['v'] = np.nan
    else:
        df = pd.read_csv(path)
        time = next(c for c in ['datetime_et', 'ts', 'ts_event', 'timestamp', 'datetime', 'time'] if c in df)
        if time == 'datetime_et':
            dates = pd.to_datetime(df.pop(time))
            df.index = pd.DatetimeIndex(dates).tz_localize('America/New_York', ambiguous='raise').tz_convert('UTC')
        else:
            df.index = pd.to_datetime(df.pop(time), utc=True)
        df = df.rename(columns=dict(open='o', high='h', low='l', close='c', volume='v'))
        if 'v' not in df:
            df['v'] = np.nan
        df = df.sort_index()
        if df.index.to_series().diff().dropna().median() < BAR:
            fields = dict(o='first', h='max', l='min', c='last', v='sum')
            if 'symbol' in df:
                fields['symbol'] = 'first'
            df = df.resample('5min').agg(fields).dropna(subset=['o', 'h', 'l', 'c'])
    df = df.sort_index()
    if df.index.has_duplicates:
        raise ValueError('Duplicate timestamps in the selected contract series')
    if ((df.h < df[['o','c','l']].max(axis=1)) | (df.l > df[['o','c','h']].min(axis=1))).any():
        raise ValueError('Invalid OHLC ordering')
    prev = df.c.shift()
    tr = pd.concat([df.h - df.l, (df.h - prev).abs(), (df.l - prev).abs()], axis=1).max(axis=1)
    df['atr'] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    return df


def clock(df):
    ct = df.index.tz_convert('America/Chicago').tz_localize(None)
    session = (ct - pd.Timedelta(hours=17)).normalize()
    minute = ct.hour * 60 + ct.minute
    return session, minute


class Screen:
    def __init__(self, df, tick):
        self.df = df
        self.tick = tick
        self.trades = []
        self.ran = set()
        self.next_entry = {}
        self.o, self.h, self.l, self.c = df[list('ohlc')].to_numpy().T
        self.time = df.index
        session, minute = clock(df)
        self.session = session.asi8
        self.minute = minute
        times = df.index.as_unit('ns').asi8
        self.contig = np.r_[np.diff(times) == BAR.value, False]
        self.symbol = df.symbol.to_numpy() if 'symbol' in df else None

    def emit(self, ident, indices, direction, stop, target, multiple, max_bars, exit_signal=None, *, deadline=None):
        self.ran.add(ident)
        indices = np.asarray(indices, dtype=int)
        n = len(indices)
        sides = np.broadcast_to(direction, (n,))
        stops = np.broadcast_to(stop, (n,))
        targets = np.broadcast_to(np.nan if target is None else target, (n,))
        limits = np.broadcast_to(-1 if deadline is None else deadline, (n,))
        exits = None if exit_signal is None else np.asarray(exit_signal, dtype=bool)
        next_entry = self.next_entry.get(ident, 0)
        for k in np.argsort(indices, kind='stable'):
            s = indices[k]
            e = s + 1
            side = int(sides[k])
            if e < next_entry or e >= len(self.o) or not self.contig[s]:
                continue
            if self.session[s] != self.session[e] or 950 <= self.minute[e] < 1020:
                continue
            if self.symbol is not None and self.symbol[e] != self.symbol[s]:
                continue
            if limits[k] != -1 and self.time[e].value >= limits[k]:
                continue
            fill = self.o[e]
            # Round to a valid price grid after adding the one-tick buffer.
            raw_stop = stops[k] - side * self.tick
            protective = (np.floor(raw_stop / self.tick + 1e-8) if side == 1 else
                          np.ceil(raw_stop / self.tick - 1e-8)) * self.tick
            risk = side * (fill - protective)
            if not np.isfinite(risk) or risk <= 0:
                continue
            tgt = targets[k] if multiple is None else fill + side * multiple * risk
            if np.isfinite(tgt) and side * (tgt - fill) <= 0:
                continue
            end = min(e + max_bars, len(self.o) - 1)
            for j in range(e, end + 1):
                op = self.o[j]
                if j > e and (not self.contig[j-1] or self.session[j] != self.session[e] or
                              (self.symbol is not None and self.symbol[j] != self.symbol[e])):
                    # Use the last observed bar before the gap/contract switch.
                    j -= 1
                    px, why = self.c[j], 'last_bar_before_gap'
                    break
                if side * (op - protective) <= 0:
                    px, why = op, 'stop_gap'
                    break
                if np.isfinite(tgt) and side * (op - tgt) >= 0:
                    px, why = tgt, 'target'
                    break
                if j == end or 950 <= self.minute[j] < 1020 or (limits[k] != -1 and self.time[j].value >= limits[k]) or (j > e and exits is not None and exits[j-1]):
                    px, why = op, 'timed_or_signal'
                    break
                if side * ((self.l[j] if side == 1 else self.h[j]) - protective) <= 0:
                    px, why = protective, 'stop'
                    break
                if np.isfinite(tgt) and side * ((self.h[j] if side == 1 else self.l[j]) - tgt) >= 0:
                    px, why = tgt, 'target'
                    break
            next_entry = j + 1
            self.trades.append((ident, self.time[e], self.time[j], side, fill, protective, tgt, px,
                                risk, side * (px - fill), why))
        self.next_entry[ident] = next_entry


def metrics(trades, cost):
    pnl = trades.gross - cost
    if not len(pnl):
        return [0, 0, np.nan, np.nan, np.nan, np.nan]
    eq = np.r_[0, pnl.cumsum()]
    losses = -pnl[pnl < 0].sum()
    return [len(pnl), pnl.sum(), (pnl / trades.risk).mean(),
            pnl[pnl > 0].sum() / losses if losses else np.inf,
            (np.maximum.accumulate(eq) - eq).max(), (pnl > 0).mean()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('feed', choices=['spot', 'yahoo', 'futures', 'micro'])
    parser.add_argument('--file', type=Path)
    args = parser.parse_args()
    path = args.file or {'spot': SPOT, 'yahoo': YAHOO}.get(args.feed)
    if path is None:
        parser.error('--file is required for futures')
    df = load(path)
    # Exclude the partial Sunday session on the day of acquisition.
    if args.feed == 'futures':
        df = df.loc[df.index < pd.Timestamp('2026-11-07', tz='UTC')].copy()
    df.attrs['feed'] = args.feed
    print(args.feed, len(df), df.index[0], df.index[-1], 'volume nonzero', df.v.gt(0).mean())
    screen = Screen(df, 0.01 if args.feed == 'spot' else 0.10)
    for module in ['sessions', 'trend', 'vwap', 'levels', 'volume', 'events', 'intermarket']:
        if (HERE / f'{module}.py').exists():
            print(module, flush=True)
            importlib.import_module(module).signals(df, screen.emit)
    trades = pd.DataFrame(screen.trades, columns='id entry exit side fill stop target price risk gross reason'.split())
    trades = trades.sort_values(['id','entry'])
    trades.to_csv(HERE / f'{args.feed}_trades.csv', index=False)
    all_metrics = []
    windows = [('all', None, None), ('2012–2019','2012','2020'), ('2020–2023','2020','2024'),
               ('2024+','2024',None), ('through 2024',None,'2025'), ('2025','2025','2026'), ('2026','2026',None)]
    for ident in range(1,102):
        subset = trades[trades.id == ident]
        for name, start, end in windows:
            cut = subset
            if start:
                cut = cut[cut.entry >= pd.Timestamp(start, tz='UTC')]
            if end:
                cut = cut[cut.entry < pd.Timestamp(end, tz='UTC')]
            for cost in (0.0, 0.30, 0.60):
                all_metrics.append([ident, ident in screen.ran, name, cost, *metrics(cut, cost)])
    summary = pd.DataFrame(all_metrics, columns='id screened period cost trades net_points mean_r profit_factor drawdown_points win_rate'.split())
    summary.to_csv(HERE / f'{args.feed}_results.csv', index=False)
    print(f'{len(screen.ran)} screened, {trades.id.nunique()} traded, {len(trades)} trades')
    print(summary[(summary.cost == 0.30) & (summary.period == 'all') & (summary.trades > 0)]
          .sort_values('net_points', ascending=False).head(15).to_string(index=False))


if __name__ == '__main__':
    main()
