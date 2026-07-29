#!/usr/bin/env python3
"""Validate and summarize the frozen structured-2D natural-query matrix."""

from __future__ import annotations

import csv
import math
import statistics
import struct
import sys
from collections import defaultdict
from pathlib import Path


MATRIX = Path("/tmp/structured-2d-natural/matrix-v1")
FINALIZED = Path("/tmp/structured-2d-admission/finalized")
QUERIES = {"sift": 10_000, "gist": 1_000}
NPROBES = {
    1024: (1, 2, 4, 8, 16, 32, 64, 128, 256),
    4096: (4, 8, 16, 32, 64, 128, 256, 512, 1024),
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def median(values: list[float]) -> float:
    return statistics.median(values)


def mad(values: list[float]) -> float:
    center = median(values)
    return median([abs(value - center) for value in values])


def nearest_rank(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[max(1, math.ceil(probability * len(ordered))) - 1]


def latency_summary(path: Path, queries: int, probes: tuple[int, ...]) -> dict[int, dict[str, float]]:
    raw = path.read_bytes()
    expected = 7 * len(probes) * queries
    if len(raw) != expected * 8:
        raise ValueError(f"{path}: latency byte count")
    values = struct.unpack(f"={expected}d", raw)
    by_probe: dict[int, list[list[float]]] = {
        probe: [[] for _ in range(queries)] for probe in probes
    }
    offset = 0
    for _repetition in range(7):
        for probe in probes:
            block = values[offset : offset + queries]
            offset += queries
            for query, value in enumerate(block):
                by_probe[probe][query].append(value)
    result = {}
    for probe, query_repetitions in by_probe.items():
        medians = [median(values) for values in query_repetitions]
        result[probe] = {
            "latency_mean_ms": statistics.fmean(medians) * 1000,
            "latency_p50_ms": nearest_rank(medians, 0.50) * 1000,
            "latency_p95_ms": nearest_rank(medians, 0.95) * 1000,
            "latency_p99_ms": nearest_rank(medians, 0.99) * 1000,
            "latency_max_ms": max(medians) * 1000,
            "latency_mad_ms": mad(medians) * 1000,
        }
    return result


def dominates(a: dict[str, object], b: dict[str, object]) -> bool:
    return (
        float(a["recall"]) >= float(b["recall"])
        and float(a["qps"]) >= float(b["qps"])
        and (
            float(a["recall"]) > float(b["recall"])
            or float(a["qps"]) > float(b["qps"])
        )
    )


def frontier(points: list[dict[str, object]]) -> list[dict[str, object]]:
    return [point for point in points if not any(
        other is not point and dominates(other, point) for other in points
    )]


def main(output: Path) -> None:
    registry = rows(MATRIX / "logical_registry.tsv")
    ledger = rows(MATRIX / "execution_ledger.tsv")
    pass_rows = [row for row in ledger if row["status"] == "PASS"]
    pass_keys = {
        (
            row["phase"], row["dataset"], row["nlist"], row["budget"],
            row["logical_arm_id"], row["mode"], row["repetition"],
        )
        for row in pass_rows
    }
    expected_keys = set()
    for item in registry:
        prefix = (
            item["dataset"], item["nlist"], item["budget"], item["logical"]
        )
        for mode in ("single", "batch12"):
            expected_keys.add(("warmup", *prefix, mode, "0"))
            for repetition in range(7):
                expected_keys.add(
                    ("measured", *prefix, mode, str(repetition))
                )
    if len(pass_rows) != len(pass_keys):
        raise ValueError("duplicate successful ledger key")
    if pass_keys != expected_keys:
        raise ValueError(
            "successful ledger grid mismatch; "
            f"missing={sorted(expected_keys - pass_keys)} "
            f"extra={sorted(pass_keys - expected_keys)}"
        )

    resources = {
        (row["dataset"], int(row["nlist"]), row["arm_id"]): row
        for row in rows(FINALIZED / "pool_manifest.tsv")
    }
    points: list[dict[str, object]] = []
    for item in registry:
        dataset = item["dataset"]
        nlist = int(item["nlist"])
        budget = int(item["budget"])
        arm = item["logical"]
        physical = item["physical"]
        prefix = f"{dataset}_{nlist}_{budget}_{arm}"
        single_path = MATRIX / "measurements" / f"{prefix}_single.tsv"
        batch_path = MATRIX / "measurements" / f"{prefix}_batch12.tsv"
        measured_by_mode = {
            "single": rows(single_path),
            "batch12": rows(batch_path),
        }
        warmup_by_mode = {
            mode: rows(MATRIX / "warmups" / f"{prefix}_{mode}.tsv")
            for mode in ("single", "batch12")
        }
        expected_grid = {
            (repetition, probe)
            for repetition in range(7)
            for probe in NPROBES[nlist]
        }
        for mode, measured in measured_by_mode.items():
            warmup = warmup_by_mode[mode]
            observed_grid = {
                (int(row["repetition"]), int(row["nprobe"]))
                for row in measured
            }
            if observed_grid != expected_grid or len(measured) != len(expected_grid):
                raise ValueError(f"{prefix}/{mode}: measured grid")
            if len(warmup) != len(NPROBES[nlist]) or {
                (int(row["repetition"]), int(row["nprobe"]))
                for row in warmup
            } != {(0, probe) for probe in NPROBES[nlist]}:
                raise ValueError(f"{prefix}/{mode}: warmup grid")
            for row in measured + warmup:
                expected_metadata = {
                    "dataset": dataset,
                    "nlist": str(nlist),
                    "budget_bytes": str(budget),
                    "arm_id": (
                        physical if arm.startswith("RABITQ_") else arm
                    ),
                    "physical_arm_id": physical,
                    "mode": mode,
                }
                for field, expected in expected_metadata.items():
                    if row[field] != expected:
                        raise ValueError(
                            f"{prefix}/{mode}: {field}={row[field]} "
                            f"!= {expected}"
                        )
        single = measured_by_mode["single"]
        batch = measured_by_mode["batch12"]
        latencies = latency_summary(
            Path(str(single_path) + ".latency.f64"),
            QUERIES[dataset],
            NPROBES[nlist],
        )
        resource = resources[(dataset, nlist, physical)]
        for probe in NPROBES[nlist]:
            sr = [row for row in single if int(row["nprobe"]) == probe]
            br = [row for row in batch if int(row["nprobe"]) == probe]
            for field in ("recall_at_100", "output_hash", "candidates"):
                warm = [
                    row
                    for mode in ("single", "batch12")
                    for row in warmup_by_mode[mode]
                    if int(row["nprobe"]) == probe
                ]
                if len({row[field] for row in sr + br + warm}) != 1:
                    raise ValueError(f"{prefix}/{probe}: unstable {field}")
            walls = [float(row["total_wall_seconds"]) for row in br]
            qps_values = [QUERIES[dataset] / wall for wall in walls]
            point = {
                "dataset": dataset,
                "nlist": nlist,
                "budget": budget,
                "arm": arm,
                "physical": physical,
                "nprobe": probe,
                "recall": float(sr[0]["recall_at_100"]),
                "qps": median(qps_values),
                "qps_min": min(qps_values),
                "qps_max": max(qps_values),
                "qps_mad": mad(qps_values),
                "candidates": int(sr[0]["candidates"]) / QUERIES[dataset],
                "complete_bytes": int(resource["complete_system_bytes"]),
                "method_bytes_per_vector": float(resource["method_bytes_per_vector"]),
                "build_cpu_seconds": float(resource["build_cpu_seconds"]),
                "peak_rss_bytes": max(int(row["peak_rss_bytes"]) for row in sr + br),
            }
            point.update(latencies[probe])
            points.append(point)

    baseline_arms = {
        32: {
            "PQFULL_M32X8", "OPQFULL_M32X8", "PQFULL_M64X4",
            "OPQFULL_M64X4", "PQFSFULL_M64X4",
        },
        64: {
            "PQFULL_M64X8", "OPQFULL_M64X8", "PQFULL_M128X4",
            "OPQFULL_M128X4", "PQFSFULL_M128X4",
        },
    }
    comparisons = []
    group_decisions = []
    for group_key in sorted({
        (str(point["dataset"]), int(point["nlist"]), int(point["budget"]))
        for point in points
    }):
        dataset, nlist, budget = group_key
        group = [
            point for point in points
            if (point["dataset"], point["nlist"], point["budget"]) == group_key
        ]
        baseline = frontier([
            point for point in group if point["arm"] in baseline_arms[budget]
        ])
        contexts = [
            point for point in group if str(point["arm"]).startswith("RABITQ_")
        ]
        s_frontier = frontier([point for point in group if point["arm"] == "S128"])
        speed_passes = []
        quality_passes = []
        for s in s_frontier:
            speed_eligible = [
                point for point in baseline
                if float(point["recall"]) >= float(s["recall"]) - 0.001
            ]
            quality_eligible = [
                point for point in baseline
                if float(point["qps"]) >= 0.95 * float(s["qps"])
            ]
            speed = max(speed_eligible, key=lambda point: float(point["qps"])) if speed_eligible else None
            quality = max(quality_eligible, key=lambda point: float(point["recall"])) if quality_eligible else None
            context_dominator = next((
                point for point in contexts
                if float(point["recall"]) >= float(s["recall"])
                and float(point["qps"]) >= float(s["qps"])
                and int(point["complete_bytes"]) <= int(s["complete_bytes"])
                and (
                    float(point["recall"]) > float(s["recall"])
                    or float(point["qps"]) > float(s["qps"])
                    or int(point["complete_bytes"]) < int(s["complete_bytes"])
                )
            ), None)
            record = {
                "dataset": dataset,
                "nlist": nlist,
                "budget": budget,
                "s_nprobe": s["nprobe"],
                "s_recall": s["recall"],
                "s_qps": s["qps"],
                "s_p95_ms": s["latency_p95_ms"],
                "speed_arm": speed["arm"] if speed else "",
                "speed_nprobe": speed["nprobe"] if speed else "",
                "speed_recall": speed["recall"] if speed else "",
                "speed_qps": speed["qps"] if speed else "",
                "speed_qps_gain": (
                    float(s["qps"]) / float(speed["qps"]) - 1 if speed else ""
                ),
                "speed_p95_delta": (
                    float(s["latency_p95_ms"]) / float(speed["latency_p95_ms"]) - 1
                    if speed else ""
                ),
                "speed_bytes_ok": (
                    int(s["complete_bytes"]) <= int(speed["complete_bytes"]) if speed else ""
                ),
                "speed_build_ok": (
                    float(s["build_cpu_seconds"]) <= 2 * float(speed["build_cpu_seconds"])
                    if speed else ""
                ),
                "quality_arm": quality["arm"] if quality else "",
                "quality_nprobe": quality["nprobe"] if quality else "",
                "quality_recall": quality["recall"] if quality else "",
                "quality_qps": quality["qps"] if quality else "",
                "quality_recall_gain": (
                    float(s["recall"]) - float(quality["recall"]) if quality else ""
                ),
                "quality_bytes_ok": (
                    int(s["complete_bytes"]) <= int(quality["complete_bytes"]) if quality else ""
                ),
                "quality_build_ok": (
                    float(s["build_cpu_seconds"]) <= 2 * float(quality["build_cpu_seconds"])
                    if quality else ""
                ),
                "context_dominator": context_dominator["arm"] if context_dominator else "",
            }
            speed_pass = bool(
                speed
                and float(record["speed_qps_gain"]) >= 0.10
                and float(record["speed_p95_delta"]) <= 0.05
                and record["speed_bytes_ok"]
                and record["speed_build_ok"]
                and not context_dominator
            )
            quality_pass = bool(
                quality
                and float(record["quality_recall_gain"]) >= 0.002
                and record["quality_bytes_ok"]
                and record["quality_build_ok"]
                and not context_dominator
            )
            record["speed_route_pass"] = speed_pass
            record["quality_route_pass"] = quality_pass
            comparisons.append(record)
            if speed_pass:
                speed_passes.append(record)
            if quality_pass:
                quality_passes.append(record)
        group_decisions.append({
            "dataset": dataset,
            "nlist": nlist,
            "budget": budget,
            "speed_route": bool(speed_passes),
            "quality_route": bool(quality_passes),
            "best_speed_gain": max(
                (float(row["speed_qps_gain"]) for row in comparisons
                 if (row["dataset"], row["nlist"], row["budget"]) == group_key
                 and row["speed_qps_gain"] != ""),
                default=float("nan"),
            ),
            "best_quality_gain": max(
                (float(row["quality_recall_gain"]) for row in comparisons
                 if (row["dataset"], row["nlist"], row["budget"]) == group_key
                 and row["quality_recall_gain"] != ""),
                default=float("nan"),
            ),
        })

    def write_tsv(path: Path, data: list[dict[str, object]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=list(data[0]), delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(data)

    output.mkdir(parents=True, exist_ok=True)
    write_tsv(output / "points.tsv", points)
    write_tsv(output / "s_comparisons.tsv", comparisons)
    write_tsv(output / "group_decisions.tsv", group_decisions)
    total_cpu = 50.75 + sum(float(row["child_cpu_seconds"]) for row in ledger) / 3600
    total_wall = 6 + sum(float(row["wall_seconds"]) for row in ledger) / 3600
    terminal = {
        budget: {
            route: all(
                any(
                    row["budget"] == budget
                    and row["dataset"] == dataset
                    and row["nlist"] == nlist
                    and row[route]
                    for row in group_decisions
                )
                for dataset in ("sift", "gist")
                for nlist in (1024, 4096)
            )
            for route in ("speed_route", "quality_route")
        }
        for budget in (32, 64)
    }
    with (output / "summary.txt").open("w", encoding="utf-8") as stream:
        stream.write(f"registry_cells={len(registry)}\n")
        stream.write(f"successful_passes={len(pass_rows)}\n")
        stream.write(f"failed_ledger_rows={len(ledger) - len(pass_rows)}\n")
        stream.write(f"aggregate_cpu_hours={total_cpu:.9f}\n")
        stream.write(f"aggregate_wall_hours={total_wall:.9f}\n")
        stream.write(f"peak_rss_bytes={max(int(point['peak_rss_bytes']) for point in points)}\n")
        for budget, result in terminal.items():
            stream.write(
                f"budget_{budget}_speed_route={result['speed_route']}\n"
                f"budget_{budget}_quality_route={result['quality_route']}\n"
            )
    print((output / "summary.txt").read_text(), end="")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
