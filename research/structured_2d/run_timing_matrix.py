#!/usr/bin/env python3
"""Run and project the frozen query-free synthetic timing matrix."""

from __future__ import annotations

import argparse
import csv
import resource
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


QUERIES = {"sift": 10_000, "gist": 1_000}
NLISTS = (1024, 4096)
MODES = ("single", "batch12")
NPROBES = {
    1024: (1, 2, 4, 8, 16, 32, 64, 128, 256),
    4096: (4, 8, 16, 32, 64, 128, 256, 512, 1024),
}
COMMON = ("S128", "D128", "V128", "IVFFLAT")
BY_BUDGET = {
    32: (
        "PQ128_M32X8",
        "OPQ128_M32X8",
        "PQFULL_M32X8",
        "OPQFULL_M32X8",
        "PQFULL_M64X4",
        "OPQFULL_M64X4",
        "PQFSFULL_M64X4",
    ),
    64: (
        "PQ128_M64X8",
        "OPQ128_M64X8",
        "PQFULL_M64X8",
        "OPQFULL_M64X8",
    ),
}
SIFT_64 = (
    "PQFULL_M128X4",
    "OPQFULL_M128X4",
    "PQFSFULL_M128X4",
)


@dataclass(frozen=True)
class Cell:
    dataset: str
    nlist: int
    budget: int
    logical: str
    physical: str


def physical_id(dataset: str, budget: int, logical: str) -> str:
    if logical in ("S128", "D128", "V128"):
        return f"{logical}_{'B4' if budget == 32 else 'B8'}"
    aliases = {
        ("sift", "PQ128_M32X8"): "PQFULL_M32X8",
        ("sift", "PQ128_M64X8"): "PQFULL_M64X8",
        ("sift", "OPQ128_M32X8"): "OPQFULL_M32X8",
        ("sift", "OPQ128_M64X8"): "OPQFULL_M64X8",
        ("gist", "OPQ128_M32X8"): "OPQHEAD_M32X8",
        ("gist", "OPQ128_M64X8"): "OPQHEAD_M64X8",
    }
    return aliases.get((dataset, logical), logical)


def context_arms(
    path: Path,
) -> dict[tuple[str, int, int], tuple[tuple[str, str], ...]]:
    result: dict[tuple[str, int, int], list[tuple[str, str]]] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            if row["family"] != "RABITQ" or row["status"] != "AVAILABLE":
                continue
            key = (
                row["dataset"],
                int(row["nlist"]),
                int(row["target_bytes"]),
            )
            side = {"LOW": "LO", "HIGH": "HI"}[row["side"]]
            logical = f"RABITQ_{side}_{row['target_bytes']}"
            result.setdefault(key, []).append((logical, row["arm_id"]))
    return {
        key: tuple(sorted(set(values)))
        for key, values in result.items()
    }


def cells(finalized: Path) -> list[Cell]:
    contexts = context_arms(finalized / "context_slots.tsv")
    result: list[Cell] = []
    for dataset in ("sift", "gist"):
        for nlist in NLISTS:
            for budget in (32, 64):
                logicals = list(COMMON) + list(BY_BUDGET[budget])
                if dataset == "sift" and budget == 64:
                    logicals.extend(SIFT_64)
                context = contexts[(dataset, nlist, budget)]
                if len(logicals) != len(set(logicals)):
                    raise ValueError(
                        f"duplicate logical arm: {dataset}/{nlist}/{budget}"
                    )
                for logical in sorted(logicals):
                    result.append(
                        Cell(
                            dataset,
                            nlist,
                            budget,
                            logical,
                            physical_id(dataset, budget, logical),
                        )
                    )
                for logical, physical in context:
                    result.append(
                        Cell(dataset, nlist, budget, logical, physical)
                    )
    expected = 2 * (13 + 13 + 12 + 9)
    if len(result) != expected:
        raise ValueError(f"logical cell count {len(result)} != {expected}")
    return result


def write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def timing_path(output: Path, key: tuple[str, int, str, str]) -> Path:
    dataset, nlist, physical, mode = key
    return output / "measurements" / f"{dataset}_{nlist}_{physical}_{mode}.tsv"


def validate_measurement(path: Path, nlist: int) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != 27:
        raise ValueError(f"{path}: expected 27 measured rows")
    observed = {
        (int(row["nprobe"]), int(row["repetition"])) for row in rows
    }
    expected = {
        (nprobe, repetition)
        for nprobe in NPROBES[nlist]
        for repetition in range(3)
    }
    if observed != expected:
        raise ValueError(f"{path}: incomplete timing grid")
    for nprobe in NPROBES[nlist]:
        selected = [row for row in rows if int(row["nprobe"]) == nprobe]
        if len({row["output_hash"] for row in selected}) != 1:
            raise ValueError(f"{path}: unstable hash at nprobe={nprobe}")
        if len({row["candidates"] for row in selected}) != 1:
            raise ValueError(f"{path}: unstable candidates at nprobe={nprobe}")


def child_cpu() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def read_ledger(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def run_matrix(args: argparse.Namespace, registry: list[Cell]) -> None:
    representatives: dict[tuple[str, int, str, str], Cell] = {}
    for cell in registry:
        for mode in MODES:
            representatives.setdefault(
                (cell.dataset, cell.nlist, cell.physical, mode), cell
            )
    ledger_path = args.output / "execution_ledger.tsv"
    ledger = read_ledger(ledger_path)
    charged = sum(float(row["child_cpu_seconds"]) for row in ledger)
    completed = {row["timing_path"] for row in ledger if row["status"] == "PASS"}
    args.output.joinpath("measurements").mkdir(parents=True, exist_ok=True)

    for key, representative in sorted(representatives.items()):
        output_path = timing_path(args.output, key)
        if str(output_path) in completed and output_path.exists():
            validate_measurement(output_path, representative.nlist)
            continue
        used_hours = args.prior_cpu_hours + charged / 3600
        if used_hours >= args.cap_cpu_hours:
            raise RuntimeError(
                f"actual CPU cap reached before {key}: {used_hours:.6f} h"
            )
        command = [
            str(args.runner),
            representative.dataset,
            str(representative.nlist),
            str(representative.budget),
            (
                representative.physical
                if representative.logical.startswith("RABITQ_")
                else representative.logical
            ),
            "all",
            key[3],
            str(args.admission_root),
            str(args.pool_root),
            str(output_path),
        ]
        cpu_start = child_cpu()
        wall_start = time.monotonic()
        completed_process = subprocess.run(command, check=False)
        cpu_delta = child_cpu() - cpu_start
        wall_delta = time.monotonic() - wall_start
        charged += cpu_delta
        status = "PASS" if completed_process.returncode == 0 else "FAIL"
        ledger.append(
            {
                "dataset": representative.dataset,
                "nlist": representative.nlist,
                "budget_argument": representative.budget,
                "logical_argument": representative.logical,
                "physical_arm_id": representative.physical,
                "mode": key[3],
                "child_cpu_seconds": f"{cpu_delta:.9f}",
                "wall_seconds": f"{wall_delta:.9f}",
                "exit_code": completed_process.returncode,
                "status": status,
                "timing_path": output_path,
            }
        )
        write_tsv(
            ledger_path,
            list(ledger[0].keys()),
            ledger,
        )
        if completed_process.returncode != 0:
            raise RuntimeError(f"timing process failed: {key}")
        validate_measurement(output_path, representative.nlist)
        print(
            f"PASS\t{representative.dataset}\t{representative.nlist}\t"
            f"{representative.physical}\t{key[3]}\t"
            f"cpu_seconds={cpu_delta:.6f}",
            flush=True,
        )


def project(args: argparse.Namespace, registry: list[Cell]) -> None:
    cache: dict[tuple[str, int, str, str, int], tuple[float, float]] = {}
    for cell in registry:
        for mode in MODES:
            key = (cell.dataset, cell.nlist, cell.physical, mode)
            path = timing_path(args.output, key)
            validate_measurement(path, cell.nlist)
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream, delimiter="\t"))
            for nprobe in NPROBES[cell.nlist]:
                values = [
                    float(row["total_cpu_seconds"])
                    for row in rows
                    if int(row["nprobe"]) == nprobe
                ]
                wall_values = [
                    float(row["total_wall_seconds"])
                    for row in rows
                    if int(row["nprobe"]) == nprobe
                ]
                cache[key + (nprobe,)] = (
                    sum(values) / len(values),
                    sum(wall_values) / len(wall_values),
                )

    projection_rows: list[dict[str, object]] = []
    projected_seconds = 0.0
    projected_wall_seconds = 0.0
    for cell in registry:
        for mode in MODES:
            for nprobe in NPROBES[cell.nlist]:
                measured, measured_wall = cache[
                    (cell.dataset, cell.nlist, cell.physical, mode, nprobe)
                ]
                projected = (
                    1.25 * (measured / 64) * QUERIES[cell.dataset] * 7
                )
                projected_wall = (
                    1.25
                    * (measured_wall / 64)
                    * QUERIES[cell.dataset]
                    * 7
                )
                projected_seconds += projected
                projected_wall_seconds += projected_wall
                projection_rows.append(
                    {
                        "dataset": cell.dataset,
                        "nlist": cell.nlist,
                        "budget_bytes": cell.budget,
                        "logical_arm_id": cell.logical,
                        "physical_arm_id": cell.physical,
                        "nprobe": nprobe,
                        "mode": mode,
                        "mean_synthetic_cpu_seconds_64_queries": f"{measured:.17g}",
                        "mean_synthetic_wall_seconds_64_queries": f"{measured_wall:.17g}",
                        "official_query_count": QUERIES[cell.dataset],
                        "registered_repetitions": 7,
                        "safety_factor": "1.25",
                        "projected_cpu_seconds": f"{projected:.17g}",
                        "projected_wall_seconds": f"{projected_wall:.17g}",
                    }
                )
    write_tsv(
        args.output / "projection_cells.tsv",
        list(projection_rows[0].keys()),
        projection_rows,
    )
    ledger = read_ledger(args.output / "execution_ledger.tsv")
    synthetic_actual = sum(float(row["child_cpu_seconds"]) for row in ledger)
    synthetic_actual_wall = sum(float(row["wall_seconds"]) for row in ledger)
    total_hours = (
        args.prior_cpu_hours +
        synthetic_actual / 3600 +
        projected_seconds / 3600
    )
    summary = [
        {
            "prior_consumed_cpu_hours": f"{args.prior_cpu_hours:.9f}",
            "synthetic_timing_actual_cpu_hours": f"{synthetic_actual / 3600:.9f}",
            "projected_registered_cpu_hours": f"{projected_seconds / 3600:.9f}",
            "projected_total_cpu_hours": f"{total_hours:.9f}",
            "authorized_cap_cpu_hours": f"{args.cap_cpu_hours:.9f}",
            "synthetic_timing_actual_wall_hours": f"{synthetic_actual_wall / 3600:.9f}",
            "projected_registered_wall_hours": f"{projected_wall_seconds / 3600:.9f}",
            "authorized_cap_wall_hours": f"{args.cap_wall_hours:.9f}",
            "cpu_decision": (
                "ADMIT" if total_hours <= args.cap_cpu_hours else "STOP"
            ),
            "wall_decision": (
                "ADMIT"
                if projected_wall_seconds / 3600 <= args.cap_wall_hours
                else "STOP"
            ),
            "decision": (
                "ADMIT"
                if total_hours <= args.cap_cpu_hours
                and projected_wall_seconds / 3600 <= args.cap_wall_hours
                else "STOP"
            ),
        }
    ]
    write_tsv(
        args.output / "projection_summary.tsv",
        list(summary[0].keys()),
        summary,
    )
    print(
        f"physical_timing_processes\t{len(ledger)}\n"
        f"logical_arm_cells\t{len(registry)}\n"
        f"projected_total_cpu_hours\t{total_hours:.9f}\n"
        f"projected_registered_wall_hours\t"
        f"{projected_wall_seconds / 3600:.9f}\n"
        f"decision\t{summary[0]['decision']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--admission-root", type=Path, required=True)
    parser.add_argument("--pool-root", type=Path, required=True)
    parser.add_argument("--finalized", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prior-cpu-hours", type=float, default=48.085)
    parser.add_argument("--cap-cpu-hours", type=float, default=64.0)
    parser.add_argument("--cap-wall-hours", type=float, default=24.0)
    args = parser.parse_args()
    registry = cells(args.finalized)
    write_tsv(
        args.output / "logical_registry.tsv",
        ["dataset", "nlist", "budget", "logical", "physical"],
        [
            {
                "dataset": cell.dataset,
                "nlist": cell.nlist,
                "budget": cell.budget,
                "logical": cell.logical,
                "physical": cell.physical,
            }
            for cell in registry
        ],
    )
    run_matrix(args, registry)
    project(args, registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
