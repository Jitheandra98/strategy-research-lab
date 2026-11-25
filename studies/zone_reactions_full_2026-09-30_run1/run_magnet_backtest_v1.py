#!/usr/bin/env python3
"""Replay-safe magnet/revisit backtest for 4H anchors and 5M execution.

This is an intentionally small, auditable implementation of the hypothesis in
magnet_hypothesis.md. It does not infer zones from screenshots. It requires
timestamped OHLC bars and creates the 4H anchor with the same offsets used by
the source Pine script (previous 4H low/high against the bar three periods
back). The runner is suitable for a replay-matched export; results from a
different feed are only a smoke test and must not be treated as validation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class Bar:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float = 0.0


@dataclass
class Zone:
    zone_id: int
    top: float
    bot: float
    direction: int
    born_i: int
    state: int = 0  # 0 active, 1 touched, 2 broken, 3 retest-ready, 4 archived
    visits: int = 0
    outside_bars: int = 0
    break_closes: int = 0
    last_visit_i: Optional[int] = None
    overlapping: bool = False


@dataclass
class Trade:
    trade_id: int
    variant: str
    direction: int
    signal_i: int
    entry_i: int
    signal_close: float
    entry: float
    stop: float
    target: float
    zone_id: int
    zone_visits: int
    exit_i: Optional[int] = None
    exit: Optional[float] = None
    exit_reason: str = ""
    r: Optional[float] = None
    mfe: Optional[float] = None
    mae: Optional[float] = None


def parse_time(v: Any) -> int:
    if isinstance(v, (int, float)):
        x = int(v)
        return x if x > 10_000_000_000 else x * 1000
    s = str(v).strip()
    try:
        return parse_time(float(s))
    except ValueError:
        text = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)


def load_bars(path: Path) -> List[Bar]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text())
        if isinstance(raw, dict):
            raw = raw.get("bars", raw.get("data", []))
        rows = raw
    else:
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))
    out: List[Bar] = []
    for r in rows:
        try:
            get = r.get if isinstance(r, dict) else lambda k: r[k]
            out.append(Bar(parse_time(get("time")), float(get("open")), float(get("high")), float(get("low")), float(get("close")), float(get("volume") or 0)))
        except (KeyError, TypeError, ValueError):
            continue
    out.sort(key=lambda x: x.t)
    dedup: Dict[int, Bar] = {b.t: b for b in out}
    return [dedup[t] for t in sorted(dedup)]


def utc_bucket(t_ms: int, hours: int = 4) -> int:
    sec = t_ms // 1000
    return sec - (sec % (hours * 3600))


def aggregate_4h(bars: List[Bar]) -> List[Dict[str, Any]]:
    buckets: Dict[int, List[Bar]] = {}
    for b in bars:
        buckets.setdefault(utc_bucket(b.t), []).append(b)
    out = []
    for key in sorted(buckets):
        group = buckets[key]
        out.append({"bucket": key * 1000, "open": group[0].o, "high": max(x.h for x in group), "low": min(x.l for x in group), "close": group[-1].c})
    return out


def true_range(b: Bar, prev_close: Optional[float]) -> float:
    return max(b.h - b.l, abs(b.h - prev_close), abs(b.l - prev_close)) if prev_close is not None else b.h - b.l


def atr_series(bars: List[Bar], length: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(bars)
    prev_close: Optional[float] = None
    values: List[float] = []
    prev_atr: Optional[float] = None
    for i, b in enumerate(bars):
        tr = true_range(b, prev_close)
        values.append(tr)
        if len(values) >= length:
            if prev_atr is None:
                prev_atr = sum(values[-length:]) / length
            else:
                prev_atr = (prev_atr * (length - 1) + tr) / length
            out[i] = prev_atr
        prev_close = b.c
    return out


def add_zone(zones: List[Zone], top: float, bot: float, direction: int, born_i: int, min_width: float, max_width: float, next_id: int, max_zones: int) -> int:
    width = top - bot
    if not (math.isfinite(top) and math.isfinite(bot) and min_width <= width <= max_width):
        return next_id
    for z in zones:
        if z.state != 4 and z.direction == direction:
            overlap = min(top, z.top) - max(bot, z.bot)
            if overlap > 0.50 * min(width, z.top - z.bot):
                return next_id
    zones.append(Zone(next_id, top, bot, direction, born_i))
    if len(zones) > max_zones:
        zones.pop(0).state = 4
    return next_id + 1


def choose_signal(
    zones: List[Zone], b: Bar, i: int, prev_atr: float, *, buffer_atr: float, body_atr: float,
    close_fraction: float, lookback: int, enable_prox: bool, enable_distal: bool,
    enable_break_retest: bool, min_bars_after_visit: int, stop_pad_atr: float,
    min_stop_atr: float, max_stop_atr: float, history: List[Bar], max_visits: int,
) -> Optional[Dict[str, Any]]:
    if i < max(lookback + 1, 2) or not prev_atr or prev_atr <= 0:
        return None
    rng = max(b.h - b.l, 1e-12)
    body = abs(b.c - b.o)
    prior_high = max(x.h for x in history[i - lookback:i])
    prior_low = min(x.l for x in history[i - lookback:i])
    bull = b.c > b.o and body >= prev_atr * body_atr and (b.c - b.l) / rng >= close_fraction and b.c > prior_high
    bear = b.c < b.o and body >= prev_atr * body_atr and (b.h - b.c) / rng >= close_fraction and b.c < prior_low
    edge_buffer = prev_atr * buffer_atr
    best: Optional[Dict[str, Any]] = None
    for z in zones:
        if z.state == 4 or not z.visits or z.visits > max_visits:
            continue
        if z.last_visit_i is not None and i - z.last_visit_i < min_bars_after_visit:
            continue
        prox = enable_prox and z.state == 1 and z.direction == 1 and b.l <= z.top and b.c > z.top + edge_buffer and bull
        distal = enable_distal and z.state == 1 and z.direction == 1 and b.l <= z.bot and b.c > z.top + edge_buffer and bull
        prox_s = enable_prox and z.state == 1 and z.direction == -1 and b.h >= z.bot and b.c < z.bot - edge_buffer and bear
        distal_s = enable_distal and z.state == 1 and z.direction == -1 and b.h >= z.top and b.c < z.bot - edge_buffer and bear
        break_long = enable_break_retest and z.state == 3 and z.direction == -1 and b.h >= z.top and b.c > z.top + edge_buffer and bull
        break_short = enable_break_retest and z.state == 3 and z.direction == 1 and b.l <= z.bot and b.c < z.bot - edge_buffer and bear
        if not (prox or distal or prox_s or distal_s or break_long or break_short):
            continue
        direction = 1 if (prox or distal or break_long) else -1
        variant = "PROX_REJECT" if (prox or prox_s) else "DISTAL_REJECT" if (distal or distal_s) else "BREAK_RETEST"
        extreme = min(b.l, z.bot) if direction == 1 else max(b.h, z.top)
        stop = extreme - prev_atr * stop_pad_atr if direction == 1 else extreme + prev_atr * stop_pad_atr
        distance = abs(b.c - (z.top if direction == 1 else z.bot))
        risk = abs(b.c - stop)
        if risk < prev_atr * min_stop_atr or risk > prev_atr * max_stop_atr:
            continue
        candidate = {"direction": direction, "variant": variant, "stop": stop, "distance": distance, "zone_id": z.zone_id, "zone_visits": z.visits}
        if best is None or candidate["distance"] < best["distance"]:
            best = candidate
    return best


def write_csv(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def run(bars: List[Bar], out: Path, args: argparse.Namespace) -> Dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    if len(bars) < 50:
        raise ValueError("at least 50 bars are required")
    atrs = atr_series(bars, args.atr_len)
    htf = aggregate_4h(bars)
    bucket_to_i = {int(x["bucket"]): i for i, x in enumerate(htf)}
    zones: List[Zone] = []
    next_zone_id = 1
    last_bucket: Optional[int] = None
    pending: Optional[Dict[str, Any]] = None
    active: Optional[Trade] = None
    trades: List[Trade] = []
    day_entries: Dict[str, int] = {}
    next_trade_id = 1
    events: List[Dict[str, Any]] = []

    for i, b in enumerate(bars):
        bucket = utc_bucket(b.t)
        if bucket != last_bucket:
            last_bucket = bucket
            hidx = bucket_to_i.get(bucket)
            if hidx is not None and hidx >= 3:
                # Source map: demand [low[1], high[3]], supply [high[1], low[3]].
                next_zone_id = add_zone(zones, htf[hidx - 1]["low"], htf[hidx - 3]["high"], 1, i, args.min_zone_points, args.max_zone_points, next_zone_id, args.max_zones)
                next_zone_id = add_zone(zones, htf[hidx - 1]["high"], htf[hidx - 3]["low"], -1, i, args.min_zone_points, args.max_zone_points, next_zone_id, args.max_zones)
        prev_atr = atrs[i - 1] if i > 0 else None
        if prev_atr:
            edge_buffer = prev_atr * args.buffer_atr
            for z in zones:
                if z.state == 4:
                    continue
                overlap = b.l <= z.top and b.h >= z.bot
                new_visit = overlap and not z.overlapping
                if new_visit:
                    z.visits += 1
                    z.last_visit_i = i
                    if z.state == 0:
                        z.state = 1
                z.outside_bars = 0 if overlap else z.outside_bars + 1
                z.overlapping = overlap
                if z.direction == 1 and b.c < z.bot - edge_buffer:
                    z.break_closes += 1
                    z.state = 3 if z.break_closes >= 2 else 2
                elif z.direction == -1 and b.c > z.top + edge_buffer:
                    z.break_closes += 1
                    z.state = 3 if z.break_closes >= 2 else 2
                if z.state == 2 and z.outside_bars >= args.rearm_outside:
                    z.state = 3
                if z.visits > args.max_visits or i - z.born_i > args.max_age_bars:
                    z.state = 4
        # Fill a market order created on the preceding close, then model the
        # current bar. If stop and target both print, stop-first is conservative.
        if pending is not None and active is None and i == pending["signal_i"] + 1:
            day = datetime.fromtimestamp(b.t / 1000, tz=timezone.utc).date().isoformat()
            day_entries.setdefault(day, 0)
            entry = b.o
            active = Trade(next_trade_id, pending["variant"], pending["direction"], pending["signal_i"], i, pending["signal_close"], entry, pending["stop"], pending["target"], pending["zone_id"], pending["zone_visits"])
            next_trade_id += 1
            pending = None
            day_entries[day] += 1
        if active is not None:
            d = active.direction
            favorable = (b.h - active.entry) if d == 1 else (active.entry - b.l)
            adverse = (active.entry - b.l) if d == 1 else (b.h - active.entry)
            active.mfe = max(active.mfe or 0.0, favorable)
            active.mae = max(active.mae or 0.0, adverse)
            hit_stop = b.l <= active.stop if d == 1 else b.h >= active.stop
            hit_target = b.h >= active.target if d == 1 else b.l <= active.target
            age = i - active.entry_i + 1
            reason = ""
            exit_price: Optional[float] = None
            if hit_stop:
                reason, exit_price = "STOP", min(b.o, active.stop) if d == 1 and b.o < active.stop else max(b.o, active.stop) if d == -1 and b.o > active.stop else active.stop
            elif hit_target:
                reason, exit_price = "TARGET", max(b.o, active.target) if d == 1 and b.o > active.target else min(b.o, active.target) if d == -1 and b.o < active.target else active.target
            elif age >= args.max_hold_bars:
                reason, exit_price = "TIME", b.c
            if reason:
                active.exit_i = i
                active.exit = exit_price
                active.exit_reason = reason
                risk = abs(active.signal_close - active.stop)
                gross = (exit_price - active.entry) * d
                active.r = gross / risk if risk > 0 else None
                trades.append(active)
                events.append({"time": b.t, "event": "EXIT", "trade_id": active.trade_id, "variant": active.variant, "direction": d, "price": exit_price, "reason": reason, "r": active.r, "mfe": active.mfe, "mae": active.mae})
                active = None
        # Evaluate a close-confirmed setup only when flat. The resulting market
        # order becomes eligible at the next 5M open.
        if active is None and pending is None and prev_atr and i < len(bars) - 1:
            day = datetime.fromtimestamp(b.t / 1000, tz=timezone.utc).date().isoformat()
            used = day_entries.get(day, 0)
            if used < args.max_daily_entries:
                sig = choose_signal(zones, b, i, prev_atr, buffer_atr=args.buffer_atr, body_atr=args.body_atr, close_fraction=args.close_fraction, lookback=args.confirm_lookback, enable_prox=args.enable_prox, enable_distal=args.enable_distal, enable_break_retest=args.enable_break_retest, min_bars_after_visit=args.min_bars_after_visit, stop_pad_atr=args.stop_pad_atr, min_stop_atr=args.min_stop_atr, max_stop_atr=args.max_stop_atr, history=bars, max_visits=args.max_visits)
                if sig:
                    risk = abs(b.c - sig["stop"])
                    target = b.c + sig["direction"] * risk * args.target_r
                    pending = {**sig, "signal_i": i, "signal_close": b.c, "target": target}
                    events.append({"time": b.t, "event": "SIGNAL", "trade_id": next_trade_id, "variant": sig["variant"], "direction": sig["direction"], "price": b.c, "reason": "next_open", "r": "", "mfe": "", "mae": ""})
    if active is not None:
        b = bars[-1]
        d = active.direction
        active.exit_i = len(bars) - 1
        active.exit = b.c
        active.exit_reason = "END"
        risk = abs(active.signal_close - active.stop)
        active.r = ((b.c - active.entry) * d) / risk if risk > 0 else None
        trades.append(active)

    trade_rows = []
    for t in trades:
        row = asdict(t)
        row["entry_time"] = bars[t.entry_i].t
        row["exit_time"] = bars[t.exit_i].t if t.exit_i is not None else ""
        trade_rows.append(row)
    write_csv(out / "trades.csv", trade_rows)
    write_csv(out / "events.csv", events)
    by_variant: Dict[str, List[Trade]] = {}
    for t in trades:
        by_variant.setdefault(t.variant, []).append(t)
    summary: Dict[str, Any] = {
        "bars": len(bars), "start": bars[0].t, "end": bars[-1].t, "htf_bars": len(htf),
        "zones_created": next_zone_id - 1, "trades": len(trades),
        "parameters": {k: v for k, v in vars(args).items() if k not in {"bars", "out"}},
        "data_warning": "Performance is valid only when bars are replay-matched to the video symbol, session, timezone, and feed. The recorder JSON supplied with this workspace is unverified and is used only for a smoke test.",
        "variants": {},
    }
    rs = [t.r for t in trades if t.r is not None]
    summary.update({"win_rate": sum(x > 0 for x in rs) / len(rs) if rs else None, "net_r": sum(rs) if rs else None, "avg_r": sum(rs) / len(rs) if rs else None})
    for name, ts in by_variant.items():
        rr = [t.r for t in ts if t.r is not None]
        summary["variants"][name] = {"trades": len(ts), "win_rate": sum(x > 0 for x in rr) / len(rr) if rr else None, "net_r": sum(rr) if rr else None, "avg_r": sum(rr) / len(rr) if rr else None}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bars", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--atr-len", type=int, default=14)
    p.add_argument("--min-zone-points", type=float, default=2.0)
    p.add_argument("--max-zone-points", type=float, default=80.0)
    p.add_argument("--max-zones", type=int, default=50)
    p.add_argument("--max-age-bars", type=int, default=1200)
    p.add_argument("--max-visits", type=int, default=3)
    p.add_argument("--rearm-outside", type=int, default=2)
    p.add_argument("--buffer-atr", type=float, default=0.10)
    p.add_argument("--body-atr", type=float, default=0.50)
    p.add_argument("--close-fraction", type=float, default=0.70)
    p.add_argument("--confirm-lookback", type=int, default=3)
    p.add_argument("--stop-pad-atr", type=float, default=0.20)
    p.add_argument("--min-stop-atr", type=float, default=0.20)
    p.add_argument("--max-stop-atr", type=float, default=2.50)
    p.add_argument("--target-r", type=float, default=1.50)
    p.add_argument("--max-hold-bars", type=int, default=60)
    p.add_argument("--max-daily-entries", type=int, default=3)
    p.add_argument("--min-bars-after-visit", type=int, default=0)
    p.add_argument("--enable-prox", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--enable-distal", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--enable-break-retest", action=argparse.BooleanOptionalAction, default=True)
    args = p.parse_args()
    summary = run(load_bars(args.bars), args.out, args)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
