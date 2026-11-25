"""Behavioral tests for causal zone signals and conservative execution accounting."""
import csv
import json
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace
from pathlib import Path

from run_magnet_backtest import Bar, Config, State, Zone, atr_series, load_bars, load_zones, run, timestamp, write_output, zone_step

T = 1_800_000_000


def bar(i, o=102.5, h=103.5, l=101.6, c=102.5):
    return Bar(T + i * 300, o, h, l, c)


def anchor(known_at=T, direction=1):
    return Zone("Z", known_at, 101.5, 100.5, direction)


def fixture(distal=False):
    bars = [bar(i) for i in range(20)]
    bars.append(bar(20, 101.4, 103.9, 100.4 if distal else 101.4, 103.8))
    bars.extend(bar(i, 103.8, 105, 103, 104.4) for i in range(21, 35))
    return bars


def reflect(bars):
    return [Bar(b.t, 200 - b.o, 200 - b.l, 200 - b.h, 200 - b.c) for b in bars]


class Signals(unittest.TestCase):
    def test_touch_alone_is_insufficient(self):
        bars = fixture()
        bars[20] = bar(20, 102, 102.2, 101.4, 101.8)
        # Remain inside; no local-break impulse is allowed to follow the touch.
        bars[21:] = [bar(i, 101.6, 101.9, 101.3, 101.6) for i in range(21, 35)]
        self.assertEqual(run(bars, [anchor()])["signals"], [])

    def test_proximal_and_distal_exclusive(self):
        a = run(fixture(), [anchor()])["signals"]
        b = run(fixture(True), [anchor()])["signals"]
        self.assertEqual([x["variant"] for x in a], ["PROXIMAL_REJECTION"])
        self.assertEqual([x["variant"] for x in b], ["DISTAL_REJECTION"])

    def test_future_anchor_has_no_earlier_signals(self):
        bars = fixture()
        self.assertEqual(run(bars, [anchor(bars[21].t)])["signals"], [])
        self.assertEqual(run(bars, [anchor(bars[-1].t + 300)])["events"], [])

    def test_future_bars_do_not_change_past_signal(self):
        bars = fixture()
        earlier = run(bars[:21], [anchor()])["signals"][0]
        later = run(bars, [anchor()])["signals"][0]
        for key in ("signal_time", "stop", "atr_previous", "variant", "direction", "visit"):
            self.assertEqual(earlier[key], later[key])

    def test_short_is_symmetric(self):
        long = run(fixture(), [anchor()])
        short = run(reflect(fixture()), [Zone("Z", T, 99.5, 98.5, -1)])
        self.assertEqual(short["signals"][0]["direction"], -1)
        self.assertEqual(short["signals"][0]["variant"], long["signals"][0]["variant"])
        self.assertAlmostEqual(short["trades"][0]["net_usd"], long["trades"][0]["net_usd"])

    def test_two_consecutive_breaks_and_later_retest(self):
        cfg, events, state = Config(), [], State(anchor())
        bars = [bar(i) for i in range(3)]
        bars.extend([bar(3, 100.1, 100.2, 99.8, 100), bar(4, 100.4, 100.6, 100.3, 100.5),
                     bar(5, 100.1, 100.2, 99.8, 100), bar(6, 100.1, 100.2, 99.8, 100),
                     bar(7, 100.3, 100.6, 98.5, 98.6)])
        for i in (3, 4, 5):
            self.assertIsNone(zone_step(state, bars, i, 2, cfg, events))
            self.assertEqual(state.phase, "REJECTION")
        self.assertIsNone(zone_step(state, bars, 6, 2, cfg, events))
        self.assertEqual(state.phase, "BREAK")
        signal = zone_step(state, bars, 7, 2, cfg, events)
        self.assertEqual(signal["variant"], "BREAK_RETEST")
        self.assertEqual(signal["direction"], -1)
        self.assertIsNone(zone_step(state, bars, 7, 2, cfg, events))

    def test_retest_requires_range_contact(self):
        state = State(anchor(), phase="BREAK", break_t=T + 2 * 300)
        bars = [bar(i, 99.9, 100, 99.7, 99.8) for i in range(3)]
        bars.append(bar(3, 99.7, 100, 98, 98.1))
        self.assertIsNone(zone_step(state, bars, 3, 2, Config(), []))

    def test_failed_flip_is_permanently_retired(self):
        state, events = State(anchor(), phase="BREAK", break_t=T + 2 * 300), []
        bars = [bar(i, 99.9, 100, 99.7, 99.8) for i in range(3)]
        bars.extend([bar(3, 100, 101, 99.8, 100.9),
                     bar(4, 100.1, 100.2, 99.8, 100),
                     bar(5, 100.3, 100.6, 98.5, 98.6)])
        for i in (3, 4, 5):
            self.assertIsNone(zone_step(state, bars, i, 2, Config(), events))
        self.assertEqual(state.phase, "EXPIRED")
        self.assertEqual(events[0]["event"], "BREAK_RECLAIM_INVALIDATED")

    def test_visit_rearm_needs_two_full_outside_bars(self):
        state, events, cfg = State(anchor(), armed=True), [], Config()
        bars = [bar(i) for i in range(3)]
        # first touch weak; outside, weak touch; outside, outside, touch
        bars.extend([bar(3, 102, 102.2, 101.4, 101.8), bar(4),
                     bar(5, 102, 102.2, 101.4, 101.8), bar(6), bar(7),
                     bar(8, 102, 102.2, 101.4, 101.8)])
        for i in range(3, 9):
            zone_step(state, bars, i, 2, cfg, events)
        touches = [e for e in events if e["event"] == "FIRST_TOUCH"]
        self.assertEqual([e["visit"] for e in touches], [1, 2])
        self.assertEqual(state.visit_i, 8)

    def test_max_visits_and_variant_latch(self):
        result = run(fixture(), [anchor()], Config(variant="distal"))
        self.assertEqual(result["signals"][0]["status"], "blocked_variant")
        self.assertEqual(result["trades"], [])
        state = State(anchor(), armed=True, visits=3)
        bars = [bar(i) for i in range(3)] + [bar(3, 101.4, 103.9, 101.4, 103.8)]
        self.assertIsNone(zone_step(state, bars, 3, 2, Config(), []))
        self.assertEqual(state.visits, 3)

    def test_uses_previous_atr(self):
        bars = fixture()
        result = run(bars, [anchor()])
        self.assertAlmostEqual(result["signals"][0]["atr_previous"], atr_series(bars)[19])


class Execution(unittest.TestCase):
    def scripted_signal(self, wanted):
        def step(state, bars, i, atr, cfg, events):
            if i not in wanted:
                return None
            return {"signal_i": i, "signal_time": __import__("run_magnet_backtest").iso(bars[i].t + 300),
                    "zone_id": "Z", "visit": 1, "variant": "PROXIMAL_REJECTION", "direction": 1,
                    "signal_close": bars[i].c, "atr_previous": atr, "stop": 100.5,
                    "distance_to_edge": 1, "status": "candidate"}
        return step

    def test_daily_cap_is_on_filled_utc_day(self):
        bars = [bar(i) for i in range(34)]
        for i in (21, 24, 27, 30):
            bars[i] = bar(i, 102.5, 108, 101.6, 102.5)
        with patch("run_magnet_backtest.zone_step", side_effect=self.scripted_signal({20, 23, 26, 29})):
            result = run(bars, [anchor()])
        self.assertEqual(len(result["trades"]), 3)
        self.assertEqual([s["status"] for s in result["signals"]], ["filled", "filled", "filled", "blocked_daily_cap"])

    def test_no_entry_from_exit_bar_confirmation(self):
        bars = [bar(i) for i in range(25)]
        bars[21] = bar(21, 102.5, 108, 101.6, 102.5)
        with patch("run_magnet_backtest.zone_step", side_effect=self.scripted_signal({20, 21})):
            result = run(bars, [anchor()])
        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["signals"][1]["status"], "blocked_exit_on_signal_bar")

    def test_next_open_costs_and_time_exit(self):
        bars = fixture()
        result = run(bars, [anchor()])
        trade = result["trades"][0]
        self.assertEqual(timestamp(trade["entry_time"]), bars[21].t)
        self.assertAlmostEqual(trade["entry"], 104)
        self.assertEqual(trade["full_bars_held"], 12)
        self.assertEqual(timestamp(trade["exit_time"]), bars[33].t)
        self.assertEqual(trade["exit_reason"], "TIME")
        self.assertAlmostEqual(trade["exit"], 103.6)
        self.assertAlmostEqual(trade["gross_usd"], -4)
        self.assertAlmostEqual(trade["net_usd"], -6)
        self.assertAlmostEqual(trade["net_r"], -6 / (trade["risk"] * 10))

    def test_cancel_open_past_stop_and_missing_nextbar(self):
        bars = fixture()
        bars[21] = bar(21, 99, 99.5, 98.5, 99)
        self.assertEqual(run(bars, [anchor()])["signals"][0]["status"], "cancelled_open_beyond_stop")
        bars = fixture()
        del bars[21]
        self.assertEqual(run(bars, [anchor()])["signals"][0]["status"], "cancelled_missing_next_bar")

    def test_actual_fill_risk_rejects_large_gap(self):
        bars = fixture()
        bars[21] = bar(21, 110, 111, 109, 110)
        self.assertEqual(run(bars, [anchor()])["signals"][0]["status"], "cancelled_risk_at_fill")

    def test_stop_gap_slippage_and_stop_first_ambiguity(self):
        bars = fixture()
        bars[22] = bar(22, 99, 100, 98, 99)
        trade = run(bars, [anchor()])["trades"][0]
        self.assertEqual(trade["exit_reason"], "STOP_GAP")
        self.assertAlmostEqual(trade["exit"], 98.8)
        bars = fixture()
        bars[22] = bar(22, 104, 112, 99, 104)
        trade = run(bars, [anchor()])["trades"][0]
        self.assertTrue(trade["stop_target_ambiguous"])
        self.assertEqual(trade["exit_reason"], "STOP")
        self.assertAlmostEqual(trade["exit"], trade["stop"] - .2)
        self.assertLess(trade["mfe_preexit_full_bars_points"], 8)

    def test_actual_fill_target_and_censoring(self):
        bars = fixture()
        bars[22] = bar(22, 104, 112, 103, 110)
        trade = run(bars, [anchor()])["trades"][0]
        self.assertEqual(trade["exit_reason"], "TARGET")
        self.assertLessEqual(trade["target"] - trade["entry"], 1.5 * trade["risk"] + 1e-8)
        short = run(fixture()[:24], [anchor()])
        self.assertEqual(short["summary"]["closed_trades"], 0)
        self.assertEqual(short["summary"]["open_censored_trades"], 1)
        self.assertIsNone(short["open_positions"][0]["net_usd"])

    def test_horizons_require_exact_coverage(self):
        bars = fixture()
        del bars[22]
        signal = run(bars, [anchor()])["signals"][0]
        self.assertTrue(signal["coverage_5m"])
        self.assertFalse(signal["coverage_15m"])
        self.assertIsNone(signal["mfe_15m_points"])

    def test_competition_deterministic(self):
        result = run(fixture(), [replace(anchor(), zone_id="B"), replace(anchor(), zone_id="A")])
        status = {s["zone_id"]: s["status"] for s in result["signals"]}
        self.assertEqual(status["A"], "filled")
        self.assertEqual(status["B"], "blocked_same_bar_competition")

    def test_gap_trade_excluded_from_metrics(self):
        bars = fixture()
        del bars[22]
        result = run(bars, [anchor()])
        self.assertEqual(result["summary"]["closed_trades_crossing_data_gaps"], 1)
        self.assertEqual(result["summary"]["metric_eligible_closed_trades"], 0)


class Inputs(unittest.TestCase):
    def write_bars(self, root, rows):
        path = Path(root) / "bars.json"
        path.write_text(json.dumps(rows))
        return path

    def test_strict_data_validation_no_silent_sort_drop(self):
        good = {"time": T, "open": 100, "high": 101, "low": 99, "close": 100}
        with tempfile.TemporaryDirectory() as root:
            for rows in ([good, good], [good, {**good, "time": T - 300}], [{**good, "low": 102}], [{**good, "high": float("nan")}], [{**good, "close": "bad"}]):
                with self.assertRaises(ValueError):
                    load_bars(self.write_bars(root, rows), True)
            path = self.write_bars(root, [{**good, "close": 100.05}])
            with self.assertRaises(ValueError):
                load_bars(path)
            bars, info = load_bars(path, True)
            self.assertEqual(len(bars), 1)
            self.assertEqual(info["off_tick_ohlc_values"], 1)

    def test_timestamp_ambiguity_rejected(self):
        for value in ("2026-09-30T00:00:00", 1800000000000):
            with self.assertRaises(ValueError):
                timestamp(value)

    def test_immutable_zone_ids(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "zones.json"
            row = {"zone_id": "a", "known_at": T, "top": 101, "bottom": 100, "direction": 1}
            path.write_text(json.dumps([row, row]))
            with self.assertRaises(ValueError):
                load_zones(path)

    def test_nooverwrite(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "run"
            result = run(fixture(), [anchor()])
            write_output(out, result, {"evidence_valid": False})
            original = (out / "summary.json").read_bytes()
            with self.assertRaises(FileExistsError):
                write_output(out, result, {"evidence_valid": False})
            self.assertEqual((out / "summary.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
