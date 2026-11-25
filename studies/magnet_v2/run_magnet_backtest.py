#!/usr/bin/env python3
"""Causal 4H-zone / 5M magnet hypothesis runner; no zone inference from pixels.

Requires immutable timestamped zone anchors and chronologically ordered bars.
Use --allow-unverified for exploratory feeds; it never licenses performance claims.
All times are bar-open UTC Unix seconds or timezone-aware ISO 8601 strings.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Config:
    variant: str = "all"
    tick: float = 0.1
    atr_len: int = 14
    buffer_atr: float = 0.1
    body_atr: float = 0.5
    close_fraction: float = 0.75
    prior_lookback: int = 3
    visit_bars: int = 6
    max_visits: int = 3
    max_zone_age: int = 1200
    max_retest_age: int = 48
    stop_pad_atr: float = 0.2
    min_risk_atr: float = 0.2
    max_risk_atr: float = 2.5
    target_r: float = 1.5
    max_hold_bars: int = 12
    daily_cap: int = 3
    point_value: float = 10.0
    fee_per_side: float = 1.0
    slippage_ticks: int = 2


@dataclass(frozen=True)
class Bar:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float = 0.0


@dataclass(frozen=True)
class Zone:
    zone_id: str
    known_at: int
    top: float
    bottom: float
    direction: int


@dataclass
class State:
    zone: Zone
    phase: str = "REJECTION"
    outside: int = 0
    armed: bool = False
    visits: int = 0
    visit_i: int | None = None
    visit_low: float | None = None
    visit_high: float | None = None
    visit_buffer: float | None = None
    attempt: bool = False
    through: int = 0
    break_t: int | None = None
    break_attempt: bool = False

    def reset_visit(self) -> None:
        self.outside = 0
        self.armed = False
        self.visit_i = None
        self.visit_low = self.visit_high = self.visit_buffer = None
        self.attempt = False


def timestamp(value: Any) -> int:
    if isinstance(value, (int, float)) or str(value).replace(".", "", 1).isdigit():
        number = float(value)
        if not math.isfinite(number) or number != int(number) or not 0 <= number < 10_000_000_000:
            raise ValueError("timestamps must be whole UTC Unix seconds (not milliseconds)")
        return int(number)
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("ISO timestamps must include UTC offset or Z")
    number = dt.timestamp()
    if number != int(number):
        raise ValueError("fractional timestamps are unsupported")
    return int(number)


def iso(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")


def records(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text())
        if isinstance(raw, dict):
            raw = raw.get("bars", raw.get("data"))
        if not isinstance(raw, list) or not all(isinstance(row, dict) for row in raw):
            raise ValueError("JSON must be a list of objects, or contain a bars/data list")
        return raw
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def off_tick(number: float, tick: float) -> bool:
    return abs(number / tick - round(number / tick)) > 1e-6


def load_bars(path: Path, allow_unverified: bool = False, tick: float = 0.1) -> tuple[list[Bar], dict]:
    bars = []
    off_tick_count = 0
    for line, row in enumerate(records(path), 2):
        try:
            raw_time = row.get("time", row.get("timestamp"))
            b = Bar(timestamp(raw_time), *(float(row[key]) for key in ("open", "high", "low", "close")), float(row.get("volume") or 0))
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"bar row {line}: {exc}") from exc
        if not all(math.isfinite(x) for x in (b.o, b.h, b.l, b.c, b.v)):
            raise ValueError(f"bar row {line}: nonfinite number")
        if min(b.o, b.h, b.l, b.c) <= 0 or b.v < 0 or b.h < max(b.o, b.c, b.l) or b.l > min(b.o, b.c, b.h):
            raise ValueError(f"bar row {line}: invalid OHLC/volume")
        if b.t % 300:
            raise ValueError(f"bar row {line}: time is not on a 5M boundary")
        if bars and b.t <= bars[-1].t:
            raise ValueError(f"bar row {line}: duplicate/nonmonotonic time; no sorting or dropping is performed")
        off_tick_count += sum(off_tick(x, tick) for x in (b.o, b.h, b.l, b.c))
        bars.append(b)
    if not bars:
        raise ValueError("no bars")
    if off_tick_count and not allow_unverified:
        raise ValueError(f"{off_tick_count} OHLC values violate MGC {tick} tick grid; use --allow-unverified only for smoke research")
    return bars, {"rows": len(bars), "off_tick_ohlc_values": off_tick_count,
                  "gap_count": sum(b.t - a.t != 300 for a, b in zip(bars, bars[1:])),
                  "first_open": iso(bars[0].t), "last_open": iso(bars[-1].t)}


def load_zones(path: Path, allow_unverified: bool = False, tick: float = 0.1) -> tuple[list[Zone], dict]:
    zones, seen, off_ticks = [], set(), 0
    for line, row in enumerate(records(path), 2):
        try:
            z = Zone(str(row["zone_id"]).strip(), timestamp(row["known_at"]), float(row["top"]), float(row["bottom"]), int(row["direction"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"zone row {line}: {exc}") from exc
        if not z.zone_id or z.zone_id in seen:
            raise ValueError(f"zone row {line}: blank/duplicate zone_id; immutable anchors required")
        if not all(math.isfinite(x) for x in (z.top, z.bottom)) or not z.top > z.bottom > 0 or z.direction not in (-1, 1):
            raise ValueError(f"zone row {line}: invalid bounds/direction")
        seen.add(z.zone_id)
        off_ticks += sum(off_tick(x, tick) for x in (z.top, z.bottom))
        zones.append(z)
    if not zones:
        raise ValueError("no zones")
    if off_ticks and not allow_unverified:
        raise ValueError(f"{off_ticks} zone bounds violate MGC tick grid")
    return sorted(zones, key=lambda z: (z.known_at, z.zone_id)), {"rows": len(zones), "off_tick_bounds": off_ticks}


def atr_series(bars: list[Bar], length: int = 14) -> list[float | None]:
    """Wilder ATR with standard observed-bar gap true ranges, like ta.atr."""
    out, seed, previous = [], [], None
    for i, b in enumerate(bars):
        tr = max(b.h - b.l, abs(b.h - bars[i - 1].c), abs(b.l - bars[i - 1].c)) if i else b.h - b.l
        if previous is None:
            seed.append(tr)
            if len(seed) == length:
                previous = sum(seed) / length
        else:
            previous = (previous * (length - 1) + tr) / length
        out.append(previous)
    return out


def round_out(price: float, side: int, tick: float) -> float:
    return round((math.floor(price / tick + 1e-8) if side == 1 else math.ceil(price / tick - 1e-8)) * tick, 8)


def impulse(bars: list[Bar], i: int, atr: float, side: int, cfg: Config) -> bool:
    b = bars[i]
    prev = bars[i - cfg.prior_lookback:i]
    if len(prev) != cfg.prior_lookback or b.h <= b.l:
        return False
    if any(b.t - bars[i - j].t != 300 * j for j in range(1, cfg.prior_lookback + 1)):
        return False
    if side == 1:
        return b.c > b.o and b.c - b.o >= cfg.body_atr * atr and (b.c - b.l) / (b.h - b.l) >= cfg.close_fraction and b.c > max(p.h for p in prev)
    return b.c < b.o and b.o - b.c >= cfg.body_atr * atr and (b.h - b.c) / (b.h - b.l) >= cfg.close_fraction and b.c < min(p.l for p in prev)


def zone_step(s: State, bars: list[Bar], i: int, atr: float, cfg: Config, events: list[dict]) -> dict | None:
    b, z = bars[i], s.zone
    if z.known_at > b.t or s.phase == "EXPIRED":
        return None
    def event(kind: str) -> None:
        events.append({"bar_open": iso(b.t), "zone_id": z.zone_id, "event": kind, "visit": s.visits})
    if b.t - z.known_at > cfg.max_zone_age * 300:
        s.phase = "EXPIRED"
        event("ZONE_EXPIRED")
        return None
    edge_buffer = max(cfg.tick, cfg.buffer_atr * atr)
    distal = z.bottom if z.direction == 1 else z.top
    if s.phase == "REJECTION":
        beyond = b.c < distal - edge_buffer if z.direction == 1 else b.c > distal + edge_buffer
        s.through = s.through + 1 if beyond else 0
        if s.through >= 2:
            s.phase, s.break_t = "BREAK", b.t
            s.reset_visit()
            event("TWO_CLOSE_BREAK")
            return None  # a breakout bar is never its own retest
        outside = b.l > z.top if z.direction == 1 else b.h < z.bottom
        if s.visit_i is not None:
            s.visit_low = min(s.visit_low, b.l)
            s.visit_high = max(s.visit_high, b.h)
        # A completed visit needs two fresh FULL outside bars before a new contact.
        # While a visit is pending, outside bars can still supply its confirmation.
        s.outside = s.outside + 1 if outside else 0
        candidate = None
        if s.visit_i is not None and not s.attempt:
            if i - s.visit_i >= cfg.visit_bars:
                s.attempt = True
                event("VISIT_EXPIRED")
            else:
                through_prox = b.c > z.top + s.visit_buffer if z.direction == 1 else b.c < z.bottom - s.visit_buffer
                if through_prox and impulse(bars, i, atr, z.direction, cfg):
                    s.attempt = True
                    distal_hit = s.visit_low <= z.bottom if z.direction == 1 else s.visit_high >= z.top
                    variant = "DISTAL_REJECTION" if distal_hit else "PROXIMAL_REJECTION"
                    raw_stop = min(s.visit_low, z.bottom) - cfg.stop_pad_atr * atr if z.direction == 1 else max(s.visit_high, z.top) + cfg.stop_pad_atr * atr
                    candidate = make_signal(z, s, b, i, atr, z.direction, variant, raw_stop, z.top if z.direction == 1 else z.bottom, cfg)
        if s.outside >= 2:
            if not s.armed:
                event("ARMED")
            s.armed = True
            s.visit_i = None
        intersects = b.l <= z.top and b.h >= z.bottom
        if s.armed and intersects and s.visit_i is None and s.visits < cfg.max_visits:
            s.visits += 1
            s.visit_i, s.visit_low, s.visit_high, s.visit_buffer = i, b.l, b.h, edge_buffer
            s.attempt, s.armed, s.outside = False, False, 0
            event("FIRST_TOUCH")
            # Same-bar completed rejection is valid; touch alone is insufficient.
            through_prox = b.c > z.top + edge_buffer if z.direction == 1 else b.c < z.bottom - edge_buffer
            if through_prox and impulse(bars, i, atr, z.direction, cfg):
                s.attempt = True
                distal_hit = b.l <= z.bottom if z.direction == 1 else b.h >= z.top
                raw_stop = min(b.l, z.bottom) - cfg.stop_pad_atr * atr if z.direction == 1 else max(b.h, z.top) + cfg.stop_pad_atr * atr
                return make_signal(z, s, b, i, atr, z.direction, "DISTAL_REJECTION" if distal_hit else "PROXIMAL_REJECTION", raw_stop, z.top if z.direction == 1 else z.bottom, cfg)
        return candidate
    if b.t - s.break_t > cfg.max_retest_age * 300:
        s.phase = "EXPIRED"
        event("BREAK_RETEST_EXPIRED")
        return None
    if (-z.direction) * (b.c - distal) < -edge_buffer:
        s.phase = "EXPIRED"
        event("BREAK_RECLAIM_INVALIDATED")
        return None
    if s.break_attempt or b.t <= s.break_t or i == 0 or b.t - bars[i - 1].t != 300:
        return None
    side = -z.direction
    prior_beyond = bars[i - 1].c > distal + edge_buffer if side == 1 else bars[i - 1].c < distal - edge_buffer
    intersects = b.h >= distal - edge_buffer and b.l <= distal + edge_buffer
    closes_beyond = b.c > distal + edge_buffer if side == 1 else b.c < distal - edge_buffer
    if prior_beyond and intersects and closes_beyond and impulse(bars, i, atr, side, cfg):
        s.break_attempt = True
        raw_stop = min(b.l, distal) - cfg.stop_pad_atr * atr if side == 1 else max(b.h, distal) + cfg.stop_pad_atr * atr
        return make_signal(z, s, b, i, atr, side, "BREAK_RETEST", raw_stop, distal, cfg)
    return None


def make_signal(z: Zone, s: State, b: Bar, i: int, atr: float, side: int, variant: str, raw_stop: float, edge: float, cfg: Config) -> dict:
    stop = round_out(raw_stop, side, cfg.tick)
    risk = side * (b.c - stop)
    valid = cfg.min_risk_atr * atr <= risk <= cfg.max_risk_atr * atr
    return {"signal_i": i, "signal_time": iso(b.t + 300), "bar_open": iso(b.t), "zone_id": z.zone_id,
            "known_at": iso(z.known_at), "visit": s.visits, "variant": variant, "direction": side,
            "signal_close": b.c, "atr_previous": atr, "stop": stop, "signal_risk": risk,
            "distance_to_edge": abs(b.c - edge), "edge": edge,
            "status": "candidate" if valid else "risk_rejected_at_signal"}


def horizons(signal: dict, bars: list[Bar]) -> None:
    i, side, ref = signal["signal_i"], signal["direction"], signal["signal_close"]
    for minutes in (5, 15, 30, 60):
        n = minutes // 5
        future = bars[i + 1:i + n + 1]
        complete = len(future) == n and all(p.t == bars[i].t + 300 * (j + 1) for j, p in enumerate(future))
        signal[f"coverage_{minutes}m"] = complete
        signal[f"mfe_{minutes}m_points"] = max(0, max(side * ((p.h if side == 1 else p.l) - ref) for p in future)) if complete else None
        signal[f"mae_{minutes}m_points"] = max(0, max(-side * ((p.l if side == 1 else p.h) - ref) for p in future)) if complete else None
        signal[f"reached_30_points_{minutes}m"] = signal[f"mfe_{minutes}m_points"] >= 30 if complete else None


def run(bars: list[Bar], zones: list[Zone], cfg: Config = Config()) -> dict:
    atrs, states = atr_series(bars, cfg.atr_len), [State(z) for z in zones]
    signals, events, trades, day_entries = [], [], [], {}
    pending, position = None, None
    slip = cfg.slippage_ticks * cfg.tick
    def close_trade(p: dict, b: Bar, price: float, reason: str, ambiguous: bool = False) -> dict:
        gross = p["direction"] * (price - p["entry"]) * cfg.point_value
        result = dict(p)
        result.update(exit_time=iso(b.t if reason in ("STOP_GAP", "TARGET_GAP", "TIME") else b.t + 300),
                      exit_bar_open=iso(b.t), exit=price, exit_reason=reason, stop_target_ambiguous=ambiguous,
                      exit_bar_extrema_excluded=True, gross_usd=gross, fees_usd=2 * cfg.fee_per_side,
                      net_usd=gross - 2 * cfg.fee_per_side, gross_r=gross / (p["risk"] * cfg.point_value),
                      net_r=(gross - 2 * cfg.fee_per_side) / (p["risk"] * cfg.point_value), censored=False)
        return result
    for i, b in enumerate(bars):
        exited = False
        gap = i > 0 and b.t - bars[i - 1].t != 300
        if gap:
            events.append({"bar_open": iso(b.t), "zone_id": "", "event": "DATA_GAP", "visit": ""})
            for s in states:
                s.reset_visit()
                s.through = 0
                if s.phase == "BREAK":
                    s.phase = "EXPIRED"
            if position is not None:
                position["crossed_data_gap"] = True
        if pending is not None:
            s = pending
            pending = None
            day = iso(b.t)[:10]
            fill = round(b.o + s["direction"] * slip, 8)
            risk = s["direction"] * (fill - s["stop"])
            if b.t != bars[s["signal_i"]].t + 300:
                s["status"] = "cancelled_missing_next_bar"
            elif s["direction"] * (b.o - s["stop"]) <= 0:
                s["status"] = "cancelled_open_beyond_stop"
            elif not cfg.min_risk_atr * s["atr_previous"] <= risk <= cfg.max_risk_atr * s["atr_previous"]:
                s["status"] = "cancelled_risk_at_fill"
            elif position is not None:
                s["status"] = "blocked_position_at_fill"
            elif day_entries.get(day, 0) >= cfg.daily_cap:
                s["status"] = "blocked_daily_cap"
            else:
                target = round_out(fill + s["direction"] * cfg.target_r * risk, s["direction"], cfg.tick)
                position = {"trade_id": len(trades) + 1, "signal_id": s["signal_id"], "zone_id": s["zone_id"],
                            "visit": s["visit"], "variant": s["variant"], "direction": s["direction"],
                            "signal_time": s["signal_time"], "entry_time": iso(b.t), "entry": fill,
                            "stop": s["stop"], "target": target, "risk": risk, "full_bars_held": 0,
                            "mfe_preexit_full_bars_points": 0.0, "mae_preexit_full_bars_points": 0.0,
                            "crossed_data_gap": False}
                day_entries[day] = day_entries.get(day, 0) + 1
                s["status"] = "filled"
        if position is not None:
            p, side = position, position["direction"]
            stop_open = side * (b.o - p["stop"]) <= 0
            target_open = side * (b.o - p["target"]) >= 0
            stop_hit = b.l <= p["stop"] if side == 1 else b.h >= p["stop"]
            target_hit = b.h >= p["target"] if side == 1 else b.l <= p["target"]
            closed = None
            if stop_open:
                closed = close_trade(p, b, b.o - side * slip, "STOP_GAP")
            elif target_open:
                closed = close_trade(p, b, p["target"], "TARGET_GAP")
            elif p["full_bars_held"] >= cfg.max_hold_bars or (gap and b.t - timestamp(p["entry_time"]) >= cfg.max_hold_bars * 300):
                closed = close_trade(p, b, b.o - side * slip, "TIME")
            elif stop_hit:
                closed = close_trade(p, b, p["stop"] - side * slip, "STOP", target_hit)
            elif target_hit:
                closed = close_trade(p, b, p["target"], "TARGET")
            if closed:
                trades.append(closed)
                position, exited = None, True
            else:
                p["full_bars_held"] += 1
                p["mfe_preexit_full_bars_points"] = max(p["mfe_preexit_full_bars_points"], side * ((b.h if side == 1 else b.l) - p["entry"]))
                p["mae_preexit_full_bars_points"] = max(p["mae_preexit_full_bars_points"], -side * ((b.l if side == 1 else b.h) - p["entry"]))
        previous_atr = atrs[i - 1] if i > 0 else None
        if previous_atr is None or previous_atr <= 0:
            continue
        candidates = []
        for state in states:
            signal = zone_step(state, bars, i, previous_atr, cfg, events)
            if signal is None:
                continue
            signal["signal_id"] = len(signals) + 1
            selected = {"proximal": "PROXIMAL_REJECTION", "distal": "DISTAL_REJECTION", "break": "BREAK_RETEST"}.get(cfg.variant)
            if selected and signal["variant"] != selected:
                signal["status"] = "blocked_variant"
            horizons(signal, bars)
            signals.append(signal)
            if signal["status"] == "candidate":
                candidates.append(signal)
        candidates.sort(key=lambda s: (s["distance_to_edge"], s["zone_id"]))
        for rank, signal in enumerate(candidates):
            if position is not None:
                signal["status"] = "blocked_open_position"
            elif exited:
                signal["status"] = "blocked_exit_on_signal_bar"
            elif rank > 0:
                signal["status"] = "blocked_same_bar_competition"
            else:
                pending = signal
                signal["status"] = "pending"
    if pending:
        pending["status"] = "cancelled_data_end_before_fill"
    open_positions = []
    if position:
        position.update(censored=True, censor_time=iso(bars[-1].t + 300), gross_usd=None, net_usd=None, net_r=None)
        open_positions.append(position)
    eligible = [t for t in trades if not t["crossed_data_gap"]]
    summary = {"signals": len(signals), "closed_trades": len(trades), "open_censored_trades": len(open_positions),
               "closed_trades_crossing_data_gaps": len(trades) - len(eligible), "metric_eligible_closed_trades": len(eligible),
               "gross_usd": sum(t["gross_usd"] for t in eligible), "net_usd": sum(t["net_usd"] for t in eligible),
               "win_rate_net": sum(t["net_usd"] > 0 for t in eligible) / len(eligible) if eligible else None,
               "mean_net_r": sum(t["net_r"] for t in eligible) / len(eligible) if eligible else None,
               "stop_target_ambiguous_trades": sum(t["stop_target_ambiguous"] for t in eligible)}
    return {"summary": summary, "signals": signals, "events": events, "trades": trades, "open_positions": open_positions}


def write_csv(path: Path, rows: list[dict], empty_fields: list[str]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or empty_fields
    with path.open("x", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_output(out: Path, result: dict, metadata: dict) -> None:
    out.mkdir(parents=True, exist_ok=False)
    for name in ("signals", "events", "trades", "open_positions"):
        write_csv(out / f"{name}.csv", result[name], ["status", "zone_id"])
    with (out / "summary.json").open("x") as file:
        json.dump({"metadata": metadata, "metrics": result["summary"]}, file, indent=2, allow_nan=False)
    with (out / "README.md").open("x") as file:
        file.write("# Magnet research run\n\nUNVERIFIED EXPLORATORY RUN. These numbers do not validate trading performance.\n\n" +
                   "No 100% profitability or daily objective is established. One contract; gross and net values are USD. "
                   "Signals include risk/portfolio rejects and descriptive forward excursions, not independent trades. "
                   "Trades crossing missing bars are excluded from aggregate metrics. Open data-end positions are censored. "
                   "Intrabar exit times are bar-close labels, not known execution timestamps. "
                   "Entries are conditional decisions at the next opening print: risk and stop-gap checks may cancel an entry. This models an opening-price-aware decision, not a blind market order submitted at the prior close. "
                   "MFE/MAE excludes all exit-bar extrema; these are conservative observed full-bar excursions, not exact intrabar excursions. "
                   "A $30/oz excursion is 30 price points, approximately $300 gross on one MGC contract, not $30 P&L.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars", type=Path, required=True)
    parser.add_argument("--zones", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--allow-unverified", action="store_true")
    parser.add_argument("--variant", choices=("all", "proximal", "distal", "break"), default="all")
    parser.add_argument("--provenance", default="unspecified; mechanically validated inputs are not proof of replay provenance")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output path already exists; provide a new run directory")
    try:
        cfg = Config(variant=args.variant)
        bars, bar_info = load_bars(args.bars, args.allow_unverified, cfg.tick)
        zones, zone_info = load_zones(args.zones, args.allow_unverified, cfg.tick)
        result = run(bars, zones, cfg)
        metadata = {"evidence_valid": False, "performance_validated": False, "structural_input_checks_passed": True,
                    "mechanical_input_checks_passed": bar_info["off_tick_ohlc_values"] == 0 and zone_info["off_tick_bounds"] == 0,
                    "provenance_verification": "not independently verified", "allow_unverified": args.allow_unverified,
                    "provenance": args.provenance, "config": asdict(cfg), "bars": bar_info, "zones": zone_info,
                    "bar_file": str(args.bars.resolve()), "zone_file": str(args.zones.resolve()),
                    "bars_sha256": hashlib.sha256(args.bars.read_bytes()).hexdigest(),
                    "zones_sha256": hashlib.sha256(args.zones.read_bytes()).hexdigest(),
                    "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "deduplication": "none; each zone_id is an independent immutable supplied anchor",
                    "htf_alignment": "supplied zone known_at; no inferred UTC four-hour resampling"}
        write_output(args.out, result, metadata)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output": str(args.out.resolve()), **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
