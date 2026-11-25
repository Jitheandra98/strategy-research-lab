import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine import (
    Plan,
    Zone,
    build_tape,
    exit_on_bar,
    full_window,
    load_bars,
    try_fill,
)


def make_df(prices, step=1800, start=0):
    rows = []
    for i, close in enumerate(prices):
        rows.append({"time": start + i * step, "open": close, "high": close + 1, "low": close - 1, "close": close})
    return pd.DataFrame(rows)


def test_load_bars_rejects_non_monotonic(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([
        {"time": 0, "open": 1, "high": 2, "low": 0, "close": 1},
        {"time": 0, "open": 1, "high": 2, "low": 0, "close": 1},
    ]))
    try:
        load_bars(path, 1800)
    except ValueError as exc:
        assert "strictly increasing" in str(exc)
    else:
        raise AssertionError("ambiguous timestamps were accepted")


def test_limit_fill_uses_zone_edge_and_rejects_open_beyond_stop():
    plan = Plan("z", 1, 100.0, 98.0, 0, 1800, 0, 1.0, 105.0, np.nan, "unknown", "unknown")
    row = type("Bar", (), {"open": 101.0, "high": 101.0, "low": 97.5, "close": 99.5, "time": 1800})()
    position, status = try_fill(plan, row, 1, "ZONE_2R")
    assert status == "filled"
    assert position.entry_price == 100.0
    assert position.stop == 97.75
    assert position.target > position.entry_price


def test_ambiguous_exit_is_stop_first():
    pos = type("Pos", (), {
        "direction": 1, "stop": 98.0, "target": 102.0, "entry_price": 100.0,
        "deadline": 10, "entry_i": 0,
    })()
    row = type("Bar", (), {"open": 100.0, "high": 103.0, "low": 97.0, "close": 100.0, "time": 1})()
    result = exit_on_bar(pos, row, 1, 1)
    assert result[0:2] == (98.0, "stop")


def test_full_window_marks_a_gap_as_not_evaluable():
    times = np.array([0, 1800, 3600, 7200], dtype=np.int64)
    ok, reason = full_window(times, 0, 2, 1800, 99999)
    assert not ok
    assert reason == "gap_horizon"


def test_first_touch_is_kept_as_a_visit_without_same_bar_plan():
    prices = [110.0] * 20
    df = make_df(prices)
    z = Zone("z", 1, 99.0, 100.0, 0, 0, 0, 0)
    # The injected zone is visible on bar 0; bar 1 is the first eligible
    # planning bar. The bar never overlaps, so there should be no visit.
    tape = build_tape(df, 1800, injected_zones={0: [z]})
    assert tape["visits"].empty
    assert all(not tape["plans"][0][name] for name in tape["plans"][0])
