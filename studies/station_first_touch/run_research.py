#!/usr/bin/env python3
"""Run the frozen Station First-Touch experiment on one feed at a time.

The runner is deliberately boring. It writes raw audits, event ledgers and
split metrics so a later review can distinguish a measured result from a
dashboard label. It never combines files with different timestamp ranges or
unknown provenance.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import math
import sys

import pandas as pd

from engine import (
    CONFIGS,
    COSTS,
    ENTRIES,
    EXITS,
    aggregate_4h,
    build_tape,
    chronological_splits,
    descriptive_visits,
    load_bars,
    simulate,
    trade_metrics,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASETS = {
    "unknown_30m_5174bars": (ROOT / "recorder_data/recorder_30m_5174bars.json", 1800),
    "unknown_5m_1744bars": (ROOT / "recorder_data/recorder_5m_1744bars.json", 300),
}


def clean(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def write_json(path: Path, payload):
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True) + "\n")


def split_label(timestamp, splits):
    for name, start, end in splits:
        if start <= int(timestamp) < end:
            return name
    return "outside"


def visit_summary(visits: pd.DataFrame):
    if visits.empty:
        return []
    rows = []
    for (split, first, direction), group in visits.groupby(
        ["split", "first", "direction"], dropna=False
    ):
        rows.append(
            {
                "split": split,
                "first_touch": bool(first),
                "direction": int(direction),
                "visits": int(len(group)),
                "mean_mfe_atr_4h": float(group.loc[group.hours == 4, "mfe_atr"].mean())
                if (group.hours == 4).any()
                else None,
                "median_mfe_atr_4h": float(group.loc[group.hours == 4, "mfe_atr"].median())
                if (group.hours == 4).any()
                else None,
                "mean_mae_atr_4h": float(group.loc[group.hours == 4, "mae_atr"].mean())
                if (group.hours == 4).any()
                else None,
                "mean_terminal_atr_4h": float(group.loc[group.hours == 4, "terminal_atr"].mean())
                if (group.hours == 4).any()
                else None,
                "mean_mfe_atr_8h": float(group.loc[group.hours == 8, "mfe_atr"].mean())
                if (group.hours == 8).any()
                else None,
                "median_mfe_atr_8h": float(group.loc[group.hours == 8, "mfe_atr"].median())
                if (group.hours == 8).any()
                else None,
                "mean_mae_atr_8h": float(group.loc[group.hours == 8, "mae_atr"].mean())
                if (group.hours == 8).any()
                else None,
                "mean_terminal_atr_8h": float(group.loc[group.hours == 8, "terminal_atr"].mean())
                if (group.hours == 8).any()
                else None,
                "evaluable_4h": int(group.loc[group.hours == 4, "evaluable"].sum()),
                "evaluable_8h": int(group.loc[group.hours == 8, "evaluable"].sum()),
            }
        )
    return rows


def run_dataset(dataset_name: str, path: Path, step: int, out_root: Path):
    out = out_root / dataset_name
    out.mkdir(parents=True, exist_ok=True)
    df, audit, gaps = load_bars(path, step)
    htf, htf_audit = aggregate_4h(df, step)
    splits = chronological_splits(df, step)
    tape = build_tape(df, step, htf)

    audit = dict(audit)
    audit.update(
        {
            "dataset_name": dataset_name,
            "timeframe_label": f"{step // 60}m",
            "htf_timeframe_label": "synthetic_UTC_4H",
            "feed_provenance": "UNKNOWN",
            "htf_audit": htf_audit,
            "splits": [dict(name=n, start=s, end=e) for n, s, e in splits],
            "zones_births": int(len(tape["zones"])),
            "events": int(len(tape["events"])),
            "visits": int(len(tape["visits"])),
            "warnings": [
                "Source provenance, symbol and venue are not encoded in this JSON feed.",
                "Missing LTF buckets are never filled forward; horizon outcomes are censored.",
                "Synthetic UTC 4H aggregation is not a broker-session 4H candle.",
                "Results are research measurements, not verified broker fills or currency P&L.",
            ],
        }
    )
    write_json(out / "data_audit.json", audit)
    gaps.to_csv(out / "missing_intervals.csv", index=False)
    tape["events"].to_csv(out / "zone_events.csv", index=False)
    tape["visits"].to_csv(out / "zone_visits.csv", index=False)
    tape["zones"].to_csv(out / "zones.csv", index=False)

    visits = descriptive_visits(df, step, tape, splits)
    if not visits.empty:
        visits["zone_class"] = visits["first"].map({True: "FIRST", False: "REPEAT"})
        visits.to_csv(out / "visit_outcomes.csv", index=False)
    else:
        pd.DataFrame().to_csv(out / "visit_outcomes.csv", index=False)
    write_json(out / "visit_summary.json", visit_summary(visits))

    metric_rows, ledger_frames, rejection_frames = [], [], []
    for split_name, start, end in splits:
        for entry, exit_family in CONFIGS:
            trades, rejected = simulate(
                df,
                step,
                tape,
                entry,
                exit_family,
                start,
                end,
                split_name,
            )
            if not trades.empty:
                ledger_frames.append(trades)
            if not rejected.empty:
                rejection_frames.append(rejected.assign(entry_model=entry, exit_family=exit_family, split=split_name))
            for cost in COSTS:
                metric = trade_metrics(trades, cost, start, end)
                metric.update(
                    {
                        "dataset_name": dataset_name,
                        "split": split_name,
                        "entry_model": entry,
                        "exit_family": exit_family,
                        "config": f"{entry}__{exit_family}",
                    }
                )
                metric_rows.append(metric)
    metrics = pd.DataFrame(metric_rows)
    ledger = pd.concat(ledger_frames, ignore_index=True) if ledger_frames else pd.DataFrame()
    rejections = pd.concat(rejection_frames, ignore_index=True) if rejection_frames else pd.DataFrame()
    metrics.to_csv(out / "metrics.csv", index=False)
    ledger.to_csv(out / "trade_ledger.csv", index=False)
    rejections.to_csv(out / "rejections.csv", index=False)

    # One validation selection, made at exactly one declared cost. Holdout is
    # reported for the selected config but never used to choose it.
    validation = metrics[(metrics.split == "validation") & (metrics.cost_points == 1.0)].copy()
    eligible = validation[
        (validation.n >= 10)
        & (validation.expectancy_r > 0)
        & (validation.bootstrap_reliable == True)
        & (validation.ci_low > 0)
    ].sort_values(["expectancy_r", "ci_low", "n"], ascending=False)
    selected = None if eligible.empty else str(eligible.iloc[0].config)
    holdout = metrics[(metrics.split == "holdout") & (metrics.cost_points == 1.0)].copy()
    if selected is None:
        holdout_selected = None
    else:
        holdout_selected = clean(holdout[holdout.config == selected].to_dict("records"))
    selection = {
        "selection_cost_points": 1.0,
        "minimum_validation_n": 10,
        "require_positive_validation_expectancy": True,
        "require_positive_validation_bootstrap_lower_ci": True,
        "selected_config": selected,
        "eligible_validation_configs": clean(eligible.to_dict("records")),
        "holdout_selected_config_metrics": holdout_selected,
        "verdict": "NO_MODEL_SELECTED" if selected is None else "ONE_CONFIG_FROZEN_FOR_HOLDOUT_REPORT",
    }
    write_json(out / "selection.json", selection)
    report = make_markdown_report(dataset_name, path, audit, metrics, visits, selection)
    (out / "QUANT_RESULTS.md").write_text(report)
    return audit, selection, metrics


def fmt(value, digits=3):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def make_markdown_report(dataset_name, path, audit, metrics, visits, selection):
    lines = [
        f"# Station First-Touch quant report — `{dataset_name}`",
        "",
        "This is a frozen research run. It does not prove profitability, identify institutional inventory, or reconstruct broker fills.",
        "The feed is kept separate because its provenance is unknown.",
        "",
        "## Data audit",
        "",
        f"- Source: `{path.resolve()}`",
        f"- SHA-256: `{audit['sha256']}`",
        f"- Rows: **{audit['rows']}**; LTF step: **{audit['step_seconds']} seconds**",
        f"- Observed range: **{audit['first_open']} → {audit['last_open']} UTC seconds**",
        f"- Missing LTF buckets: **{audit['missing_ltf_buckets']}** across **{audit['gaps']}** gaps; max gap **{audit['max_open_gap_seconds']} seconds**",
        f"- Complete synthetic 4H buckets: **{audit['htf_audit']['complete_buckets']}**; partial: **{audit['htf_audit']['partial_buckets']}**",
        f"- Zones/events/visits: **{audit['zones_births']} / {audit['events']} / {audit['visits']}**",
        "",
        "## Frozen selection",
        "",
        f"- Result: **{selection['verdict']}**",
        f"- Selected config: **{selection['selected_config'] or 'none'}**",
        "- Validation selection requires at least 10 uncensored trades, positive expectancy at 1 point cost, and a positive lower block-bootstrap CI.",
        "- Holdout is not used to select a model.",
        "",
        "## First touch versus repeat",
        "",
    ]
    if visits.empty:
        lines.append("No complete visit outcome rows were available.")
    else:
        for row in visit_summary(visits):
            lines.append(
                f"- {row['split']} / {'first' if row['first_touch'] else 'repeat'} / {'long' if row['direction'] == 1 else 'short'}: "
                f"n={row['evaluable_8h']} evaluable at 8h, median MFE={fmt(row['median_mfe_atr_8h'])} ATR, "
                f"mean terminal={fmt(row['mean_terminal_atr_8h'])} ATR."
            )
    lines += [
        "",
        "## Model metrics at 1 point cost",
        "",
        "| Split | Config | n | uncensored | expectancy (R) | win rate | PF | max DD (R) | bootstrap CI |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    view = metrics[metrics.cost_points == 1.0].copy()
    for _, row in view.iterrows():
        ci = "—" if row.ci_low is None or pd.isna(row.ci_low) else f"[{row.ci_low:.3f}, {row.ci_high:.3f}]"
        lines.append(
            f"| {row.split} | {row.config} | {int(row.entries)} | {int(row.n)} | {fmt(row.expectancy_r)} | "
            f"{fmt(row.win_rate)} | {fmt(row.profit_factor)} | {fmt(row.max_drawdown_r)} | {ci} |"
        )
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "A positive row is a conditional historical result under the declared OHLC fill assumptions. It is not evidence of live executable performance. Data gaps, synthetic 4H aggregation, unknown symbol/venue, spread, slippage, commissions and intrabar path ambiguity limit the result.",
        "The next required step is an independent, symbol-identified feed with a pre-registered holdout and broker-matched costs.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=sorted(DEFAULT_DATASETS), action="append")
    parser.add_argument("--out", type=Path, default=ROOT / "research/station_first_touch/results")
    args = parser.parse_args()
    selected = args.dataset or sorted(DEFAULT_DATASETS)
    manifest = {"contract": "EXPERIMENT_CONTRACT.md", "datasets": {}, "python": sys.version}
    for name in selected:
        path, step = DEFAULT_DATASETS[name]
        audit, selection, _ = run_dataset(name, path, step, args.out)
        manifest["datasets"][name] = {
            "source": str(path.resolve()),
            "step_seconds": step,
            "sha256": audit["sha256"],
            "selected_config": selection["selected_config"],
        }
    write_json(args.out / "run_manifest.json", manifest)
    print(json.dumps(clean(manifest), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
