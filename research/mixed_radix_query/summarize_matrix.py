#!/usr/bin/env python3
"""Validate and summarize the frozen mixed-radix Recall/QPS matrix."""

from __future__ import annotations

import csv
import math
import statistics
import struct
import sys
from collections import defaultdict
from pathlib import Path


QUERIES = {"sift": 10_000, "gist": 1_000}
NPROBES = {
    1024: (1, 2, 4, 8, 16, 32, 64, 128, 256),
    4096: (4, 8, 16, 32, 64, 128, 256, 512, 1024),
}
MODES = ("single", "batch12")
REPETITIONS = 7


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def median(values: list[float]) -> float:
    return statistics.median(values)


def mad(values: list[float]) -> float:
    center = median(values)
    return median([abs(value - center) for value in values])


def nearest_rank(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[max(1, math.ceil(probability * len(ordered))) - 1]


def latency_summary(
    path: Path, timing_rows: list[dict[str, str]], queries: int
) -> dict[int, dict[str, float]]:
    """Associate each binary latency block with its TSV row, not file order."""
    raw = path.read_bytes()
    block_bytes = queries * 8
    if len(raw) != len(timing_rows) * block_bytes:
        raise ValueError(f"{path}: latency byte count")
    by_probe: dict[int, list[list[float]]] = defaultdict(list)
    for index, row in enumerate(timing_rows):
        block = raw[index * block_bytes : (index + 1) * block_bytes]
        by_probe[int(row["nprobe"])].append(
            list(struct.unpack(f"={queries}d", block))
        )
    result = {}
    for probe, repetitions in by_probe.items():
        if len(repetitions) != REPETITIONS:
            raise ValueError(f"{path}: nprobe={probe} repetition count")
        query_medians = [
            median([values[query] for values in repetitions])
            for query in range(queries)
        ]
        result[probe] = {
            "latency_mean_ms": statistics.fmean(query_medians) * 1000,
            "latency_p50_ms": nearest_rank(query_medians, 0.50) * 1000,
            "latency_p95_ms": nearest_rank(query_medians, 0.95) * 1000,
            "latency_p99_ms": nearest_rank(query_medians, 0.99) * 1000,
            "latency_max_ms": max(query_medians) * 1000,
            "latency_mad_ms": mad(query_medians) * 1000,
        }
    return result


def dominates(left: dict[str, object], right: dict[str, object]) -> bool:
    return (
        float(left["recall"]) >= float(right["recall"])
        and float(left["qps"]) >= float(right["qps"])
        and (
            float(left["recall"]) > float(right["recall"])
            or float(left["qps"]) > float(right["qps"])
        )
    )


def frontier(points: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        point
        for point in points
        if not any(
            other is not point and dominates(other, point) for other in points
        )
    ]


def validate_ledger(
    registry: list[dict[str, str]], ledger: list[dict[str, str]]
) -> None:
    expected = set()
    for item in registry:
        prefix = (
            item["dataset"],
            item["nlist"],
            item["budget"],
            item["logical"],
        )
        for mode in MODES:
            expected.add(("warmup", *prefix, mode, "0"))
            for repetition in range(REPETITIONS):
                expected.add(
                    ("measured", *prefix, mode, str(repetition))
                )
    passed = [row for row in ledger if row["status"] == "PASS"]
    keys = {
        (
            row["phase"],
            row["dataset"],
            row["nlist"],
            row["budget"],
            row["logical_arm_id"],
            row["mode"],
            row["repetition"],
        )
        for row in passed
    }
    if len(passed) != len(keys):
        raise ValueError("duplicate successful ledger key")
    if keys != expected:
        raise ValueError(
            f"successful ledger mismatch: missing={len(expected - keys)}, "
            f"extra={len(keys - expected)}"
        )


def resource_map(finalized: Path) -> dict[tuple[str, int, str], dict[str, str]]:
    result = {
        (row["dataset"], int(row["nlist"]), row["arm_id"]): row
        for row in read_rows(finalized / "pool_manifest.tsv")
    }
    pool = finalized.parent / "pool"
    for dataset in QUERIES:
        for nlist in NPROBES:
            for budget, suffix in ((32, "B4"), (64, "B8")):
                physical = f"A128_{suffix}"
                artifact = (
                    pool / dataset / f"nlist_{nlist}" / f"{physical}.faiss"
                )
                auxiliary = Path(str(artifact) + ".shape.u16")
                measured = read_rows(Path(str(artifact) + ".resources.tsv"))[0]
                dyadic = result[(dataset, nlist, f"D128_{suffix}")]
                common_bytes = (
                    int(dyadic["complete_system_bytes"])
                    - int(dyadic["artifact_serialized_bytes"])
                )
                result[(dataset, nlist, physical)] = {
                    "complete_system_bytes": str(
                        artifact.stat().st_size
                        + auxiliary.stat().st_size
                        + common_bytes
                    ),
                    "build_cpu_seconds": str(sum(
                        float(measured.get(field, 0))
                        for field in (
                            "fit_cpu_seconds",
                            "add_cpu_seconds",
                            "write_cpu_seconds",
                        )
                    )),
                    "build_wall_seconds": str(sum(
                        float(measured.get(field, 0))
                        for field in (
                            "fit_wall_seconds",
                            "add_wall_seconds",
                            "write_wall_seconds",
                        )
                    )),
                    "peak_rss_bytes": measured["peak_rss_bytes"],
                }
    return result


def main(matrix: Path, finalized: Path, output: Path) -> None:
    registry = read_rows(matrix / "logical_registry.tsv")
    ledger = read_rows(matrix / "execution_ledger.tsv")
    validate_ledger(registry, ledger)
    resources = resource_map(finalized)
    points: list[dict[str, object]] = []

    for item in registry:
        dataset = item["dataset"]
        nlist = int(item["nlist"])
        budget = int(item["budget"])
        arm = item["logical"]
        physical = item["physical"]
        prefix = f"{dataset}_{nlist}_{budget}_{arm}"
        measured = {
            mode: read_rows(matrix / "measurements" / f"{prefix}_{mode}.tsv")
            for mode in MODES
        }
        warmups = {
            mode: read_rows(matrix / "warmups" / f"{prefix}_{mode}.tsv")
            for mode in MODES
        }
        expected_grid = {
            (repetition, probe)
            for repetition in range(REPETITIONS)
            for probe in NPROBES[nlist]
        }
        for mode in MODES:
            observed = {
                (int(row["repetition"]), int(row["nprobe"]))
                for row in measured[mode]
            }
            if observed != expected_grid or len(measured[mode]) != len(expected_grid):
                raise ValueError(f"{prefix}/{mode}: measured grid")
            warmup_grid = {
                (int(row["repetition"]), int(row["nprobe"]))
                for row in warmups[mode]
            }
            if (
                len(warmups[mode]) != len(NPROBES[nlist])
                or warmup_grid != {(0, probe) for probe in NPROBES[nlist]}
            ):
                raise ValueError(f"{prefix}/{mode}: warmup grid")
            expected_metadata = {
                "dataset": dataset,
                "nlist": str(nlist),
                "budget_bytes": str(budget),
                "arm_id": arm,
                "physical_arm_id": physical,
                "mode": mode,
                "queries": str(QUERIES[dataset]),
                "threads": "1" if mode == "single" else "12",
            }
            for row in measured[mode] + warmups[mode]:
                for field, expected_value in expected_metadata.items():
                    if row[field] != expected_value:
                        raise ValueError(
                            f"{prefix}/{mode}: {field}={row[field]} "
                            f"!= {expected_value}"
                        )

        latencies = latency_summary(
            Path(
                str(matrix / "measurements" / f"{prefix}_single.tsv")
                + ".latency.f64"
            ),
            measured["single"],
            QUERIES[dataset],
        )
        resource = resources.get((dataset, nlist, physical))
        for probe in NPROBES[nlist]:
            single = [
                row for row in measured["single"]
                if int(row["nprobe"]) == probe
            ]
            batch = [
                row for row in measured["batch12"]
                if int(row["nprobe"]) == probe
            ]
            warm = [
                row
                for mode in MODES
                for row in warmups[mode]
                if int(row["nprobe"]) == probe
            ]
            for field in ("recall_at_100", "output_hash", "candidates"):
                if len({row[field] for row in single + batch + warm}) != 1:
                    raise ValueError(f"{prefix}/{probe}: unstable {field}")
            qps_values = [
                QUERIES[dataset] / float(row["total_wall_seconds"])
                for row in batch
            ]
            point: dict[str, object] = {
                "dataset": dataset,
                "nlist": nlist,
                "budget": budget,
                "arm": arm,
                "physical": physical,
                "nprobe": probe,
                "recall": float(single[0]["recall_at_100"]),
                "qps": median(qps_values),
                "qps_min": min(qps_values),
                "qps_max": max(qps_values),
                "qps_mad": mad(qps_values),
                "candidates_per_query": (
                    int(single[0]["candidates"]) / QUERIES[dataset]
                ),
                "peak_query_rss_bytes": max(
                    int(row["peak_rss_bytes"]) for row in single + batch
                ),
                "complete_system_bytes": (
                    int(resource["complete_system_bytes"]) if resource else ""
                ),
                "build_cpu_seconds": (
                    float(resource["build_cpu_seconds"]) if resource else ""
                ),
                "build_wall_seconds": (
                    float(resource["build_wall_seconds"]) if resource else ""
                ),
                "build_peak_rss_bytes": (
                    int(resource["peak_rss_bytes"]) if resource else ""
                ),
            }
            point.update(latencies[probe])
            points.append(point)

    comparisons: list[dict[str, object]] = []
    frontier_rows: list[dict[str, object]] = []
    for key in sorted({
        (str(point["dataset"]), int(point["nlist"]), int(point["budget"]))
        for point in points
    }):
        group = [
            point for point in points
            if (point["dataset"], point["nlist"], point["budget"]) == key
        ]
        all_frontier = frontier(group)
        ad_frontier = frontier([
            point for point in group
            if point["arm"] in {"A128", "D128_FULL"}
        ])
        for scope, selected in (("all", all_frontier), ("A_vs_D", ad_frontier)):
            for point in selected:
                frontier_rows.append({
                    "scope": scope,
                    **{field: point[field] for field in (
                        "dataset", "nlist", "budget", "arm",
                        "nprobe", "recall", "qps",
                    )},
                })
        by_arm_probe = {
            (str(point["arm"]), int(point["nprobe"])): point
            for point in group
        }
        for probe in NPROBES[key[1]]:
            arbitrary = by_arm_probe[("A128", probe)]
            dyadic = by_arm_probe[("D128_FULL", probe)]
            comparisons.append({
                "dataset": key[0],
                "nlist": key[1],
                "budget": key[2],
                "nprobe": probe,
                "a_recall": arbitrary["recall"],
                "d_recall": dyadic["recall"],
                "recall_delta": (
                    float(arbitrary["recall"]) - float(dyadic["recall"])
                ),
                "a_qps": arbitrary["qps"],
                "d_qps": dyadic["qps"],
                "qps_ratio": (
                    float(arbitrary["qps"]) / float(dyadic["qps"])
                ),
                "a_p95_ms": arbitrary["latency_p95_ms"],
                "d_p95_ms": dyadic["latency_p95_ms"],
                "p95_ratio": (
                    float(arbitrary["latency_p95_ms"])
                    / float(dyadic["latency_p95_ms"])
                ),
            })

    output.mkdir(parents=True, exist_ok=True)
    write_rows(output / "points.tsv", points)
    write_rows(output / "a_vs_d_same_probe.tsv", comparisons)
    write_rows(output / "frontiers.tsv", frontier_rows)
    cpu_hours = 1.5 + sum(
        float(row["child_cpu_seconds"]) for row in ledger
    ) / 3600
    wall_hours = 1.5 + sum(
        float(row["wall_seconds"]) for row in ledger
    ) / 3600
    invalid = [row for row in ledger if row["status"] != "PASS"]
    with (output / "summary.txt").open("w", encoding="utf-8") as stream:
        stream.write(f"registry_cells={len(registry)}\n")
        stream.write(f"successful_passes={sum(row['status'] == 'PASS' for row in ledger)}\n")
        stream.write(f"nonpass_accounting_rows={len(invalid)}\n")
        stream.write(f"aggregate_cpu_hours={cpu_hours:.9f}\n")
        stream.write(f"aggregate_wall_hours={wall_hours:.9f}\n")
        stream.write(
            f"peak_query_rss_bytes="
            f"{max(int(point['peak_query_rss_bytes']) for point in points)}\n"
        )
        stream.write(
            f"max_same_probe_recall_delta="
            f"{max(float(row['recall_delta']) for row in comparisons):.9f}\n"
        )
        stream.write(
            f"min_same_probe_recall_delta="
            f"{min(float(row['recall_delta']) for row in comparisons):.9f}\n"
        )
        stream.write(
            f"a_points_on_all_arm_frontiers="
            f"{sum(row['scope'] == 'all' and row['arm'] == 'A128' for row in frontier_rows)}\n"
        )
    print((output / "summary.txt").read_text(), end="")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: summarize_matrix.py MATRIX FINALIZED OUTPUT"
        )
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
