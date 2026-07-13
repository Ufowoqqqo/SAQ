#!/usr/bin/env python3
"""Join inverse-ratio artifacts with QPS rows and compare measured frontiers."""

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np


LABEL_RE = re.compile(r"^(?P<plan>.+)_np(?P<nprobe>[0-9]+)$")


def file_record(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(8 * 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def read_single_qps_row(path):
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"expected one QPS row in {path}, found {len(rows)}")
    row = rows[0]
    required = {"nprobe", "num_threads", "QPS", "avg_tm_ms", "recall"}
    missing = required.difference(row)
    if missing:
        raise ValueError(f"missing QPS columns in {path}: {sorted(missing)}")
    parsed = {
        "nprobe": int(row["nprobe"]),
        "num_threads": int(row["num_threads"]),
        "qps": float(row["QPS"]),
        "avg_tm_ms": float(row["avg_tm_ms"]),
        "reported_recall": float(row["recall"]),
    }
    if not all(math.isfinite(value) for value in parsed.values()):
        raise ValueError(f"non-finite QPS value in {path}")
    return parsed


def load_rows(metric_path, qps_dir):
    artifact = json.loads(Path(metric_path).read_text(encoding="utf-8"))
    rows = []
    for result in artifact["results"]:
        match = LABEL_RE.match(result["label"])
        if not match:
            raise ValueError(f"invalid result label: {result['label']}")
        plan = match.group("plan")
        nprobe = int(match.group("nprobe"))
        qps_path = Path(qps_dir) / f"{result['label']}_qps.csv"
        qps = read_single_qps_row(qps_path)
        if qps["nprobe"] != nprobe:
            raise ValueError(
                f"nprobe mismatch for {result['label']}: {qps['nprobe']} != {nprobe}"
            )

        recall = float(result["recall_at_k"]["mean"])
        if abs(recall - qps["reported_recall"]) > 1e-9:
            raise ValueError(
                f"recall mismatch for {result['label']}: "
                f"{recall} != {qps['reported_recall']}"
            )
        rows.append(
            {
                "label": result["label"],
                "plan": plan,
                "nprobe": nprobe,
                **qps,
                "recall_at_k": recall,
                "inverse_ratio_at_k": float(
                    result["inverse_ratio_at_k"]["mean"]
                ),
                "inverse_ratio_min": float(result["inverse_ratio_at_k"]["min"]),
                "inverse_ratio_p01": float(result["inverse_ratio_at_k"]["p01"]),
                "inverse_ratio_p05": float(result["inverse_ratio_at_k"]["p05"]),
                "inverse_ratio_median": float(
                    result["inverse_ratio_at_k"]["median"]
                ),
                "inverse_ratio_p95": float(result["inverse_ratio_at_k"]["p95"]),
                "inverse_ratio_max": float(result["inverse_ratio_at_k"]["max"]),
                "per_query": result["per_query"],
                "result_ids_path": result["input"]["path"],
                "result_ids_bytes": result["input"]["bytes"],
                "result_ids_sha256": result["input"]["sha256"],
                "qps_path": str(qps_path.resolve()),
                "qps_bytes": qps_path.stat().st_size,
                "qps_sha256": file_record(qps_path)["sha256"],
            }
        )
    return artifact, rows


def nondominated(rows, quality_key):
    frontier = []
    for candidate in rows:
        dominated = any(
            other[quality_key] >= candidate[quality_key]
            and other["qps"] >= candidate["qps"]
            and (
                other[quality_key] > candidate[quality_key]
                or other["qps"] > candidate["qps"]
            )
            for other in rows
        )
        if not dominated:
            frontier.append(candidate)
    frontier.sort(key=lambda row: (row[quality_key], -row["qps"]))
    return frontier


def interpolate_qps(frontier, quality_key, target):
    if not frontier:
        raise ValueError("cannot interpolate an empty frontier")
    low = frontier[0][quality_key]
    high = frontier[-1][quality_key]
    if target < low or target > high:
        return {
            "status": "unreachable",
            "target": target,
            "measured_min": low,
            "measured_max": high,
        }

    for row in frontier:
        if row[quality_key] == target:
            return {
                "status": "measured",
                "target": target,
                "qps": row["qps"],
                "lower_label": row["label"],
                "upper_label": row["label"],
            }

    for lower, upper in zip(frontier, frontier[1:]):
        q0 = lower[quality_key]
        q1 = upper[quality_key]
        if q0 <= target <= q1 and q1 > q0:
            weight = (target - q0) / (q1 - q0)
            qps = lower["qps"] + weight * (upper["qps"] - lower["qps"])
            return {
                "status": "interpolated",
                "target": target,
                "qps": qps,
                "weight": weight,
                "lower_label": lower["label"],
                "upper_label": upper["label"],
            }
    raise ValueError(f"target {target} was not bracketed by frontier")


def best_measured_at_or_above(frontier, quality_key, target):
    eligible = [row for row in frontier if row[quality_key] >= target]
    if not eligible:
        return {
            "status": "unreachable",
            "target": target,
            "measured_max": max(row[quality_key] for row in frontier),
        }
    selected = max(eligible, key=lambda row: row["qps"])
    return {
        "status": "measured",
        "target": target,
        "label": selected["label"],
        "quality": selected[quality_key],
        "qps": selected["qps"],
    }


def paired_query_deltas(default_result, alternative_result):
    default = {
        int(row["query_id"]): float(row["inverse_ratio_at_k"])
        for row in default_result["per_query"]
    }
    alternative = {
        int(row["query_id"]): float(row["inverse_ratio_at_k"])
        for row in alternative_result["per_query"]
    }
    if default.keys() != alternative.keys():
        raise ValueError("paired result query IDs differ")
    delta = np.asarray(
        [alternative[query_id] - default[query_id] for query_id in sorted(default)],
        dtype=np.float64,
    )
    return {
        "count": int(delta.size),
        "mean": float(np.mean(delta)),
        "min": float(np.min(delta)),
        "p01": float(np.quantile(delta, 0.01)),
        "p05": float(np.quantile(delta, 0.05)),
        "median": float(np.median(delta)),
        "max": float(np.max(delta)),
        "fraction_negative": float(np.mean(delta < 0.0)),
        "fraction_zero": float(np.mean(delta == 0.0)),
        "fraction_positive": float(np.mean(delta > 0.0)),
    }


def summarize(metric_path, qps_dir, reference_label, default_plan, alternative_plan):
    artifact, rows = load_rows(metric_path, qps_dir)
    by_label = {row["label"]: row for row in rows}
    if reference_label not in by_label:
        raise ValueError(f"reference label not found: {reference_label}")
    reference = by_label[reference_label]
    if reference["plan"] != default_plan:
        raise ValueError("reference label does not belong to the default plan")

    plans = {row["plan"] for row in rows}
    required_plans = {default_plan, alternative_plan}
    if not required_plans.issubset(plans):
        raise ValueError(f"missing plans: {sorted(required_plans.difference(plans))}")

    frontiers = {}
    reference_comparison = {}
    for quality_key in ("recall_at_k", "inverse_ratio_at_k"):
        frontiers[quality_key] = {}
        for plan in (default_plan, alternative_plan):
            plan_rows = [row for row in rows if row["plan"] == plan]
            frontiers[quality_key][plan] = nondominated(plan_rows, quality_key)
        target = reference[quality_key]
        default_at_target = interpolate_qps(
            frontiers[quality_key][default_plan], quality_key, target
        )
        alternative_at_target = interpolate_qps(
            frontiers[quality_key][alternative_plan], quality_key, target
        )
        comparison = {
            "target": target,
            "default": default_at_target,
            "alternative": alternative_at_target,
        }
        if (
            default_at_target["status"] != "unreachable"
            and alternative_at_target["status"] != "unreachable"
        ):
            comparison["alternative_over_default_qps"] = (
                alternative_at_target["qps"] / default_at_target["qps"]
            )
        default_measured = best_measured_at_or_above(
            frontiers[quality_key][default_plan], quality_key, target
        )
        alternative_measured = best_measured_at_or_above(
            frontiers[quality_key][alternative_plan], quality_key, target
        )
        comparison["best_measured_at_or_above"] = {
            "default": default_measured,
            "alternative": alternative_measured,
        }
        if (
            default_measured["status"] == "measured"
            and alternative_measured["status"] == "measured"
        ):
            comparison["best_measured_at_or_above"][
                "alternative_over_default_qps"
            ] = alternative_measured["qps"] / default_measured["qps"]
            if quality_key == "inverse_ratio_at_k":
                comparison["best_measured_at_or_above"][
                    "paired_alternative_minus_default"
                ] = paired_query_deltas(
                    by_label[default_measured["label"]],
                    by_label[alternative_measured["label"]],
                )
        reference_comparison[quality_key] = comparison

    paired = []
    default_by_nprobe = {
        row["nprobe"]: row for row in rows if row["plan"] == default_plan
    }
    alternative_by_nprobe = {
        row["nprobe"]: row for row in rows if row["plan"] == alternative_plan
    }
    for nprobe in sorted(default_by_nprobe.keys() & alternative_by_nprobe.keys()):
        paired.append(
            {
                "nprobe": nprobe,
                **paired_query_deltas(
                    default_by_nprobe[nprobe], alternative_by_nprobe[nprobe]
                ),
            }
        )

    compact_rows = []
    for row in sorted(rows, key=lambda value: (value["plan"], value["nprobe"])):
        compact_rows.append({key: value for key, value in row.items() if key != "per_query"})

    compact_frontiers = {}
    for quality_key, by_plan in frontiers.items():
        compact_frontiers[quality_key] = {
            plan: [row["label"] for row in frontier]
            for plan, frontier in by_plan.items()
        }

    return {
        "schema_version": 1,
        "dataset": artifact["dataset"],
        "k": artifact["k"],
        "metric_artifact": str(Path(metric_path).resolve()),
        "metric_inputs": artifact["inputs"],
        "reference_label": reference_label,
        "default_plan": default_plan,
        "alternative_plan": alternative_plan,
        "rows": compact_rows,
        "frontiers": compact_frontiers,
        "reference_comparison": reference_comparison,
        "paired_inverse_ratio_delta_alternative_minus_default": paired,
    }


def write_outputs(summary, output_prefix):
    output_prefix = Path(output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = output_prefix.with_suffix(".json")
    csv_path = output_prefix.with_suffix(".csv")
    json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not summary["rows"]:
        raise ValueError("cannot write an empty row table")
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary["rows"][0].keys()))
        writer.writeheader()
        writer.writerows(summary["rows"])
    return json_path, csv_path


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--qps-dir", required=True, type=Path)
    parser.add_argument("--reference-label", required=True)
    parser.add_argument("--default-plan", default="default")
    parser.add_argument("--alternative-plan", default="fac_error")
    parser.add_argument("--output-prefix", required=True, type=Path)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    summary = summarize(
        args.metrics,
        args.qps_dir,
        args.reference_label,
        args.default_plan,
        args.alternative_plan,
    )
    json_path, csv_path = write_outputs(summary, args.output_prefix)
    print(json.dumps({
        "json": str(json_path),
        "csv": str(csv_path),
        "reference_comparison": summary["reference_comparison"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
