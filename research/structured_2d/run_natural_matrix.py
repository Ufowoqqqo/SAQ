#!/usr/bin/env python3
"""Run the frozen natural-query matrix in its preregistered arm order."""

from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import os
import resource
import shutil
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from run_timing_matrix import Cell, NPROBES, cells, write_tsv


MODES = ("single", "batch12")
REPETITIONS = 7
QUERY_FILES = {
    "sift": ("sift/sift_query.fvecs", "sift/sift_groundtruth.ivecs", 10_000),
    "gist": ("gist/gist_query.fvecs", "gist/gist_groundtruth.ivecs", 1_000),
}


class DeadlineReached(RuntimeError):
    pass


def acquire_output_lock(output: Path):
    """Hold one kernel-released writer lock for the full matrix run."""
    output.mkdir(parents=True, exist_ok=True)
    path = output / ".runner.lock"
    handle = path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.seek(0)
        owner = handle.read().strip() or "unknown owner"
        handle.close()
        raise RuntimeError(
            f"matrix output already has an active runner: {owner}"
        ) from None
    handle.seek(0)
    handle.truncate()
    handle.write(
        f"pid={os.getpid()} started_epoch={time.time():.6f}\n"
    )
    handle.flush()
    os.fsync(handle.fileno())
    return handle


def child_cpu() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def measurement_path(output: Path, cell: Cell, mode: str) -> Path:
    return (
        output
        / "measurements"
        / (
            f"{cell.dataset}_{cell.nlist}_{cell.budget}_"
            f"{cell.logical}_{mode}.tsv"
        )
    )


def warmup_path(output: Path, cell: Cell, mode: str) -> Path:
    return (
        output
        / "warmups"
        / (
            f"{cell.dataset}_{cell.nlist}_{cell.budget}_"
            f"{cell.logical}_{mode}.tsv"
        )
    )


def validate_pass(path: Path, nlist: int, repetition: int) -> None:
    rows = read_rows(path)
    expected = {(probe, repetition) for probe in NPROBES[nlist]}
    observed = {
        (int(row["nprobe"]), int(row["repetition"])) for row in rows
    }
    if observed != expected or len(rows) != len(expected):
        raise ValueError(f"{path}: incomplete pass")


def validate_cell(
    measured: Path, warmup: Path, cell: Cell, mode: str, completed: int
) -> None:
    warm_rows = read_rows(warmup)
    if len(warm_rows) != len(NPROBES[cell.nlist]):
        raise ValueError(f"{warmup}: incomplete warmup")
    rows = read_rows(measured)
    expected = {
        (probe, repetition)
        for repetition in range(completed)
        for probe in NPROBES[cell.nlist]
    }
    observed = {
        (int(row["nprobe"]), int(row["repetition"])) for row in rows
    }
    valid = {
        (probe, repetition)
        for repetition in range(REPETITIONS)
        for probe in NPROBES[cell.nlist]
    }
    observed_repetitions = {repetition for _, repetition in observed}
    complete_observed = {
        (probe, repetition)
        for repetition in observed_repetitions
        for probe in NPROBES[cell.nlist]
    }
    if (
        not expected.issubset(observed)
        or observed != complete_observed
        or not observed.issubset(valid)
        or len(rows) != len(observed)
    ):
        raise ValueError(f"{measured}: incomplete measured grid")
    combined = warm_rows + rows
    for probe in NPROBES[cell.nlist]:
        selected = [
            row for row in combined if int(row["nprobe"]) == probe
        ]
        for field in ("output_hash", "candidates", "recall_at_100"):
            if len({row[field] for row in selected}) != 1:
                raise ValueError(
                    f"{measured}: unstable {field} at nprobe={probe}"
                )
    if mode == "single":
        queries = QUERY_FILES[cell.dataset][2]
        expected_bytes = len(rows) * queries * 8
        actual_bytes = Path(str(measured) + ".latency.f64").stat().st_size
        if actual_bytes != expected_bytes:
            raise ValueError(
                f"{measured}: latency bytes {actual_bytes} != {expected_bytes}"
            )


def groups(registry: list[Cell]) -> list[list[Cell]]:
    grouped: dict[tuple[str, int, int], list[Cell]] = defaultdict(list)
    for cell in registry:
        grouped[(cell.dataset, cell.nlist, cell.budget)].append(cell)
    return [
        sorted(grouped[key], key=lambda cell: cell.logical)
        for key in sorted(grouped)
    ]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_context(args: argparse.Namespace) -> None:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    path = args.output / "run_context.tsv"
    row = {
        "source_commit": commit,
        "runner_sha256": file_sha256(args.runner),
        "prior_cpu_hours": str(args.prior_cpu_hours),
        "prior_wall_hours": str(args.prior_wall_hours),
        "cap_cpu_hours": str(args.cap_cpu_hours),
        "cap_wall_hours": str(args.cap_wall_hours),
    }
    existing = read_rows(path)
    if existing:
        if existing != [row]:
            raise ValueError("run context changed across restart")
        return
    write_tsv(path, list(row), [row])


def append_ledger(path: Path, row: dict[str, object]) -> None:
    rows = read_rows(path)
    rows.append({key: str(value) for key, value in row.items()})
    write_tsv(path, list(row), rows)


def discard_uncommitted_pass(
    path: Path, repetition: int, queries: int | None
) -> None:
    """Remove output from an interrupted invocation before retrying it."""
    rows = read_rows(path)
    if not rows:
        return
    keep = [int(row["repetition"]) != repetition for row in rows]
    if all(keep):
        return
    write_tsv(
        path,
        list(rows[0]),
        [row for row, retain in zip(rows, keep) if retain],
    )
    if queries is None:
        return
    latency_path = Path(str(path) + ".latency.f64")
    block_bytes = queries * 8
    payload = latency_path.read_bytes()
    if len(payload) != len(rows) * block_bytes:
        raise ValueError(
            f"{latency_path}: cannot recover interrupted pass because "
            f"{len(payload)} bytes do not match {len(rows)} timing rows"
        )
    latency_path.write_bytes(
        b"".join(
            payload[index * block_bytes : (index + 1) * block_bytes]
            for index, retain in enumerate(keep)
            if retain
        )
    )


def publish_staged_pass(
    staged: Path, target: Path, append: bool, queries: int | None
) -> None:
    staged_rows = read_rows(staged)
    existing_rows = read_rows(target) if append else []
    merged_rows = existing_rows + staged_rows
    merged = Path(str(target) + ".merge")
    write_tsv(merged, list(staged_rows[0]), merged_rows)

    staged_latency = Path(str(staged) + ".latency.f64")
    target_latency = Path(str(target) + ".latency.f64")
    merged_latency = Path(str(target_latency) + ".merge")
    if queries is not None:
        with merged_latency.open("wb") as stream:
            if append and target_latency.exists():
                with target_latency.open("rb") as source:
                    shutil.copyfileobj(source, stream)
            with staged_latency.open("rb") as source:
                shutil.copyfileobj(source, stream)

    os.replace(merged, target)
    if queries is not None:
        os.replace(merged_latency, target_latency)
        staged_latency.unlink()
    staged.unlink()


def invoke(
    args: argparse.Namespace,
    cell: Cell,
    mode: str,
    repetition: int,
    phase: str,
    path: Path,
    append: bool,
) -> tuple[float, float]:
    query_rel, truth_rel, queries = QUERY_FILES[cell.dataset]
    latency_queries = queries if mode == "single" else None
    discard_uncommitted_pass(path, repetition, latency_queries)
    staged = Path(str(path) + f".r{repetition}.staging")
    staged.unlink(missing_ok=True)
    Path(str(staged) + ".latency.f64").unlink(missing_ok=True)
    arm_argument = (
        cell.physical
        if cell.logical.startswith("RABITQ_")
        else cell.logical
    )
    command = [
        "taskset",
        "-c",
        "0" if mode == "single" else "0-11",
        str(args.runner),
        "natural-pass",
        cell.dataset,
        str(cell.nlist),
        str(cell.budget),
        arm_argument,
        mode,
        str(args.admission_root),
        str(args.pool_root),
        str(args.data_root / query_rel),
        str(args.data_root / truth_rel),
        str(args.schedule_root),
        str(repetition),
        "truncate",
        str(staged),
    ]
    environment = dict(os.environ)
    environment.update(
        {
            "OMP_NUM_THREADS": "1" if mode == "single" else "12",
            "OMP_DYNAMIC": "FALSE",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
        }
    )
    cpu_start = child_cpu()
    wall_start = time.monotonic()
    completed = subprocess.run(command, env=environment, check=False)
    cpu_delta = child_cpu() - cpu_start
    wall_delta = time.monotonic() - wall_start
    ledger_row = {
        "phase": phase,
        "dataset": cell.dataset,
        "nlist": cell.nlist,
        "budget": cell.budget,
        "logical_arm_id": cell.logical,
        "physical_arm_id": cell.physical,
        "mode": mode,
        "repetition": repetition,
        "child_cpu_seconds": f"{cpu_delta:.9f}",
        "wall_seconds": f"{wall_delta:.9f}",
        "exit_code": completed.returncode,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "timing_path": path,
    }
    if completed.returncode != 0:
        append_ledger(args.output / "execution_ledger.tsv", ledger_row)
        raise RuntimeError(
            f"natural pass failed: {phase}/{cell}/{mode}/{repetition}"
        )
    validate_pass(staged, cell.nlist, repetition)
    publish_staged_pass(staged, path, append, latency_queries)
    append_ledger(args.output / "execution_ledger.tsv", ledger_row)
    return cpu_delta, wall_delta


def usage(args: argparse.Namespace) -> tuple[float, float]:
    rows = read_rows(args.output / "execution_ledger.tsv")
    return (
        args.prior_cpu_hours
        + sum(float(row["child_cpu_seconds"]) for row in rows) / 3600,
        args.prior_wall_hours
        + sum(float(row["wall_seconds"]) for row in rows) / 3600,
    )


def enforce_caps(args: argparse.Namespace) -> None:
    cpu_hours, wall_hours = usage(args)
    if cpu_hours >= args.cap_cpu_hours:
        raise RuntimeError(f"CPU cap reached: {cpu_hours:.6f} h")
    if wall_hours >= args.cap_wall_hours:
        raise RuntimeError(f"wall cap reached: {wall_hours:.6f} h")
    if (
        args.deadline_epoch is not None
        and time.time() >= args.deadline_epoch
    ):
        raise DeadlineReached(
            "operational deadline reached at a pass boundary"
        )


def completed_keys(args: argparse.Namespace) -> set[tuple[str, str, int, int, int, str, int]]:
    result = set()
    for row in read_rows(args.output / "execution_ledger.tsv"):
        if row["status"] != "PASS":
            continue
        result.add(
            (
                row["phase"],
                row["dataset"],
                int(row["nlist"]),
                int(row["budget"]),
                int(row["repetition"]),
                row["logical_arm_id"],
                0 if row["mode"] == "single" else 1,
            )
        )
    return result


def run(args: argparse.Namespace, registry: list[Cell]) -> None:
    args.output.joinpath("measurements").mkdir(parents=True, exist_ok=True)
    args.output.joinpath("warmups").mkdir(parents=True, exist_ok=True)
    complete = completed_keys(args)
    for group in groups(registry):
        for mode_index, mode in enumerate(MODES):
            for cell in group:
                key = (
                    "warmup",
                    cell.dataset,
                    cell.nlist,
                    cell.budget,
                    0,
                    cell.logical,
                    mode_index,
                )
                path = warmup_path(args.output, cell, mode)
                if key in complete:
                    validate_pass(path, cell.nlist, 0)
                    continue
                enforce_caps(args)
                invoke(args, cell, mode, 0, "warmup", path, False)
                validate_pass(path, cell.nlist, 0)
                complete.add(key)
                print(
                    f"WARMUP PASS {cell.dataset}/{cell.nlist}/{cell.budget}/"
                    f"{cell.logical}/{mode}",
                    flush=True,
                )

        for repetition in range(REPETITIONS):
            offset = repetition % len(group)
            ordered = group[offset:] + group[:offset]
            for mode_index, mode in enumerate(MODES):
                for cell in ordered:
                    key = (
                        "measured",
                        cell.dataset,
                        cell.nlist,
                        cell.budget,
                        repetition,
                        cell.logical,
                        mode_index,
                    )
                    path = measurement_path(args.output, cell, mode)
                    if key in complete:
                        continue
                    enforce_caps(args)
                    invoke(
                        args,
                        cell,
                        mode,
                        repetition,
                        "measured",
                        path,
                        repetition != 0,
                    )
                    complete.add(key)
                    validate_cell(
                        path,
                        warmup_path(args.output, cell, mode),
                        cell,
                        mode,
                        repetition + 1,
                    )
                    cpu_hours, wall_hours = usage(args)
                    print(
                        f"MEASURED PASS r={repetition} "
                        f"{cell.dataset}/{cell.nlist}/{cell.budget}/"
                        f"{cell.logical}/{mode} "
                        f"aggregate_cpu_h={cpu_hours:.6f} "
                        f"aggregate_wall_h={wall_hours:.6f}",
                        flush=True,
                    )
    for cell in registry:
        for mode in MODES:
            validate_cell(
                measurement_path(args.output, cell, mode),
                warmup_path(args.output, cell, mode),
                cell,
                mode,
                REPETITIONS,
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--admission-root", type=Path, required=True)
    parser.add_argument("--pool-root", type=Path, required=True)
    parser.add_argument("--finalized", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--schedule-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prior-cpu-hours", type=float, required=True)
    parser.add_argument("--prior-wall-hours", type=float, required=True)
    parser.add_argument("--cap-cpu-hours", type=float, default=256.0)
    parser.add_argument("--cap-wall-hours", type=float, default=120.0)
    parser.add_argument("--deadline-epoch", type=float)
    args = parser.parse_args()
    output_lock = acquire_output_lock(args.output)
    registry = cells(args.finalized)
    write_context(args)
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
    try:
        run(args, registry)
    except DeadlineReached as error:
        cpu_hours, wall_hours = usage(args)
        print(
            f"PAUSED {error} aggregate_cpu_hours={cpu_hours:.9f} "
            f"aggregate_wall_hours={wall_hours:.9f}",
            flush=True,
        )
        return 0
    cpu_hours, wall_hours = usage(args)
    print(
        f"COMPLETE aggregate_cpu_hours={cpu_hours:.9f} "
        f"aggregate_wall_hours={wall_hours:.9f}"
    )
    # Keep the descriptor live until all output and terminal status is written.
    del output_lock
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
