#!/usr/bin/env python3
"""Create explicit bar/anchor inputs, never overwrite an output directory.

Modes:
  reconstruction: isolate each video stitching segment; export existing imported
                  4H anchors only. This never certifies reconstructed prices.
  chart-export: extract creation pulses from STATION_MAGNET_v2 chart CSV.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(path, rows, fields):
    with path.open("x", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def fingerprint(path):
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def reconstruction(args):
    bars = read(args.bars)
    zones = read(args.zones)
    grouped = defaultdict(list)
    anchors = defaultdict(list)
    for b in bars:
        grouped[b["segment"]].append({"time": b["time_utc"], **{k: b[k] for k in ("open", "high", "low", "close")}, "volume": ""})
    for z in zones:
        if z["tf"] != "5m" or z["kind"] != "4H":
            continue
        i = int(z["born_i"])
        b = bars[i]
        if b["segment"] != z["segment"]:
            raise ValueError(f"zone {z['zone_uid']} segment does not match birth bar")
        born = datetime.fromisoformat(b["time_utc"])
        source_born = datetime.fromisoformat(z["born_time"])
        if born != source_born:
            raise ValueError(f"zone {z['zone_uid']} birth timestamp does not match")
        anchors[z["segment"]].append({"zone_id": z["zone_uid"], "known_at": (born + timedelta(minutes=5)).isoformat(), "top": z["top"], "bottom": z["bot"], "direction": z["dir"]})
    manifest = {"evidence_valid": False, "source": "pixel reconstruction; some repairs use subsequent candles", "warning": "This adapter does not remove lookahead already embedded in repaired pixels. Results are software exercises and hypothesis generation only.", "original_files": [fingerprint(args.bars), fingerprint(args.zones)], "segments": {}}
    args.out.mkdir(parents=True, exist_ok=False)
    for seg, rows in sorted(grouped.items()):
        folder = args.out / f"segment_{seg}"
        folder.mkdir()
        write(folder / "bars.csv", rows, ["time", "open", "high", "low", "close", "volume"])
        write(folder / "zones.csv", anchors[seg], ["zone_id", "known_at", "top", "bottom", "direction"])
        manifest["segments"][seg] = {"bars": len(rows), "zones": len(anchors[seg]), "start": rows[0]["time"], "end": rows[-1]["time"]}
    (args.out / "provenance.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


def chart_export(args):
    rows = read(args.chart)
    if not rows:
        raise ValueError("Empty chart export")
    headers = list(rows[0])
    def column(name):
        exact = [h for h in headers if h.strip().lower() == name.lower()]
        matches = exact or [h for h in headers if h.strip().endswith(name)]
        if len(matches) != 1:
            raise ValueError(f"Need one unambiguous {name!r} column; found {matches}")
        return matches[0]
    keys = {k: column(k) for k in ["time", "open", "high", "low", "close", "zone_id", "zone_known_ms", "zone_top", "zone_bottom", "zone_direction"]}
    volume = next((h for h in headers if h.lower().strip() == "volume"), None)
    bars, zones = [], []
    for r in rows:
        bars.append({k: r[keys[k]] for k in ["time", "open", "high", "low", "close"]} | {"volume": r[volume] if volume else ""})
        pulse = r[keys["zone_id"]].strip()
        if not pulse or pulse.lower() in {"nan", "na", "null"}:
            continue
        values = {k: float(r[keys[k]]) for k in ["zone_id", "zone_known_ms", "zone_top", "zone_bottom", "zone_direction"]}
        if not all(math.isfinite(v) for v in values.values()):
            raise ValueError("Non-finite zone pulse")
        known = datetime.fromtimestamp(values["zone_known_ms"] / 1000, timezone.utc)
        zones.append({"zone_id": str(int(values["zone_id"])), "known_at": known.isoformat(), "top": values["zone_top"], "bottom": values["zone_bottom"], "direction": int(values["zone_direction"])})
    args.out.mkdir(parents=True, exist_ok=False)
    write(args.out / "bars.csv", bars, ["time", "open", "high", "low", "close", "volume"])
    write(args.out / "zones.csv", zones, ["zone_id", "known_at", "top", "bottom", "direction"])
    manifest = {"source": "user-supplied TradingView chart export", "input": fingerprint(args.chart), "bars": len(bars), "zones": len(zones), "symbol": args.symbol, "evidence_valid": False, "warning": "Verify symbol, contract adjustment, session, date span and replay match separately. Passing syntax checks is not independent source verification."}
    (args.out / "provenance.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("reconstruction")
    r.add_argument("--bars", required=True, type=Path)
    r.add_argument("--zones", required=True, type=Path)
    r.add_argument("--out", required=True, type=Path)
    c = sub.add_parser("chart-export")
    c.add_argument("--chart", required=True, type=Path)
    c.add_argument("--out", required=True, type=Path)
    c.add_argument("--symbol", required=True)
    a = p.parse_args()
    (reconstruction if a.mode == "reconstruction" else chart_export)(a)
