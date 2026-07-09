#!/usr/bin/env python3
"""Compare SAQ variance DP with a data-only fac-error DP objective."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BLOCK_DIM = 64
MAX_BITS = 13
NUM_BIT_FACTORS = 2 * 4 * 8


@dataclass(frozen=True)
class SegmentKey:
    start_block: int
    end_block: int
    bits: int


@dataclass
class PlanResult:
    dataset: str
    objective: str
    avg_bits: int
    dim: int
    padded_dim: int
    sample_rows: int
    pair_count: int
    max_pairs: int
    objective_value: float
    used_bits: int
    budget_bits: int
    num_segments: int
    plan: list[tuple[int, int]]


def parse_float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return math.nan


def read_measurement(path: Path) -> tuple[dict[SegmentKey, dict[str, float]], dict[str, Any]]:
    rows: dict[SegmentKey, dict[str, float]] = {}
    meta: dict[str, Any] = {"path": str(path)}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            start_dim = int(row["start_dim"])
            end_dim = int(row["end_dim"])
            bits = int(row["bits"])
            key = SegmentKey(start_dim // BLOCK_DIM, end_dim // BLOCK_DIM, bits)
            rows[key] = {
                "variance_sum": parse_float(row["variance_sum"]),
                "saq_proxy": parse_float(row["saq_proxy"]),
                "mean_fac_error": parse_float(row["mean_fac_error"]),
                "mean_abs_l2_error": parse_float(row["mean_abs_l2_error"]),
            }
            if "dataset" not in meta:
                meta = {
                    "path": str(path),
                    "case": row["case"],
                    "dataset": row["dataset"],
                    "sample_rows": int(row["sample_rows"]),
                    "total_rows": int(row["total_rows"]),
                    "dim": int(row["dim"]),
                    "pair_count": int(row["pair_count"]),
                    "max_pairs": int(row["max_pairs"]),
                    "source_mode": row["source_mode"],
                    "rotation": row["rotation"],
                }
            else:
                meta["pair_count"] = min(int(meta["pair_count"]), int(row["pair_count"]))
    if not rows:
        raise ValueError(f"empty measurement file: {path}")
    meta["padded_dim"] = max(key.end_block for key in rows) * BLOCK_DIM
    return rows, meta


def objective_cost(rows: dict[SegmentKey, dict[str, float]], key: SegmentKey, objective: str) -> float:
    values = rows[key]
    if objective == "variance":
        if key.bits == 0:
            return values["variance_sum"]
        return values["saq_proxy"]
    if objective == "fac_error":
        if key.bits == 0:
            return values["mean_abs_l2_error"]
        return values["mean_fac_error"]
    raise ValueError(f"unknown objective: {objective}")


def used_bits(plan: list[tuple[int, int]]) -> int:
    return sum(bits * dim + (NUM_BIT_FACTORS if bits > 0 else 0) for dim, bits in plan)


def plan_to_string(plan: list[tuple[int, int]]) -> str:
    return "_".join(f"{dim}x{bits}" for dim, bits in plan)


def run_dp(rows: dict[SegmentKey, dict[str, float]], meta: dict[str, Any], avg_bits: int, objective: str) -> PlanResult:
    padded_dim = int(meta["padded_dim"])
    num_blocks = padded_dim // BLOCK_DIM
    budget_bits = avg_bits * padded_dim + NUM_BIT_FACTORS
    max_num_segs = num_blocks if avg_bits < 2 else num_blocks // 2

    states: list[list[dict[int, tuple[float, tuple[int, int] | None]]]] = [
        [dict() for _ in range(num_blocks + 1)] for _ in range(max_num_segs + 1)
    ]
    states[0][0][0] = (0.0, None)

    best: tuple[float, int, int] | None = None
    for ns in range(max_num_segs + 1):
        for i in range(num_blocks + 1):
            for cur_bits in sorted(list(states[ns][i])):
                cur_cost, _ = states[ns][i][cur_bits]
                if i == num_blocks:
                    if best is None or cur_cost * 1.01 < best[0]:
                        best = (cur_cost, ns, cur_bits)
                    continue
                if ns == max_num_segs:
                    continue

                for end in range(i + 1, num_blocks + 1):
                    dim_len = (end - i) * BLOCK_DIM
                    for bits in range(1, MAX_BITS + 1):
                        next_bits = cur_bits + bits * dim_len + NUM_BIT_FACTORS
                        if next_bits > budget_bits:
                            break
                        key = SegmentKey(i, end, bits)
                        cost = objective_cost(rows, key, objective)
                        if not math.isfinite(cost):
                            continue
                        next_cost = cur_cost + cost
                        old = states[ns + 1][end].get(next_bits)
                        if old is None or next_cost < old[0]:
                            states[ns + 1][end][next_bits] = (next_cost, (i, bits))

                zero_key = SegmentKey(i, num_blocks, 0)
                zero_cost = objective_cost(rows, zero_key, objective)
                if math.isfinite(zero_cost):
                    next_cost = cur_cost + zero_cost
                    old = states[ns + 1][num_blocks].get(cur_bits)
                    if old is None or next_cost < old[0]:
                        states[ns + 1][num_blocks][cur_bits] = (next_cost, (i, 0))

    if best is None:
        raise RuntimeError(f"no DP plan found for {meta['dataset']} B={avg_bits} {objective}")

    best_cost, ns, bit_state = best
    plan_rev: list[tuple[int, int]] = []
    i = num_blocks
    b_state = bit_state
    while i > 0:
        entry = states[ns][i].get(b_state)
        if entry is None or entry[1] is None:
            raise RuntimeError(f"broken backtrack for {meta['dataset']} B={avg_bits} {objective}")
        prev_i, seg_bits = entry[1]
        dim_len = (i - prev_i) * BLOCK_DIM
        plan_rev.append((dim_len, seg_bits))
        ns -= 1
        i = prev_i
        if seg_bits > 0:
            b_state -= seg_bits * dim_len + NUM_BIT_FACTORS
    plan = list(reversed(plan_rev))

    return PlanResult(
        dataset=str(meta["dataset"]),
        objective=objective,
        avg_bits=avg_bits,
        dim=int(meta["dim"]),
        padded_dim=padded_dim,
        sample_rows=int(meta["sample_rows"]),
        pair_count=int(meta["pair_count"]),
        max_pairs=int(meta["max_pairs"]),
        objective_value=best_cost,
        used_bits=used_bits(plan),
        budget_bits=budget_bits,
        num_segments=len(plan),
        plan=plan,
    )


def compare_plans(variance: PlanResult, fac_error: PlanResult) -> dict[str, Any]:
    return {
        "dataset": variance.dataset,
        "avg_bits": variance.avg_bits,
        "dim": variance.dim,
        "padded_dim": variance.padded_dim,
        "sample_rows": variance.sample_rows,
        "pair_count": variance.pair_count,
        "budget_bits": variance.budget_bits,
        "variance_used_bits": variance.used_bits,
        "fac_error_used_bits": fac_error.used_bits,
        "variance_num_segments": variance.num_segments,
        "fac_error_num_segments": fac_error.num_segments,
        "same_plan": variance.plan == fac_error.plan,
        "variance_plan": plan_to_string(variance.plan),
        "fac_error_plan": plan_to_string(fac_error.plan),
        "variance_cost": variance.objective_value,
        "fac_error_cost": fac_error.objective_value,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Fac-Error DP Falsification Summary",
        "",
        "The fac-error objective uses CAQ `mean_fac_error` for positive-bit segments and measured zero-bit dropped-tail L2 error for the optional zero tail.",
        "Both objectives use SAQ's original DP budget, metadata factor cost, max-segment rule, and 1% replacement tolerance.",
        "",
        "| dataset | B | sample rows | pairs | same plan | variance plan | fac-error plan |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {dataset} | {avg_bits} | {sample_rows} | {pair_count} | {same_plan} | `{variance_plan}` | `{fac_error_plan}` |".format(
                **row
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small fac-error DP falsification study.")
    parser.add_argument("--inputs", nargs="+", required=True, help="Estimator-error measurement CSV files.")
    parser.add_argument("--avg-bits", nargs="+", type=int, default=[4], help="Average bit budgets to test.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for .csv and .md.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparisons: list[dict[str, Any]] = []
    for input_path in args.inputs:
        rows, meta = read_measurement(Path(input_path))
        for avg_bits in args.avg_bits:
            variance = run_dp(rows, meta, avg_bits, "variance")
            fac_error = run_dp(rows, meta, avg_bits, "fac_error")
            comparisons.append(compare_plans(variance, fac_error))

    comparisons.sort(key=lambda row: (row["dataset"], row["avg_bits"]))
    output_prefix = Path(args.output_prefix)
    write_csv(output_prefix.with_suffix(".csv"), comparisons)
    write_markdown(output_prefix.with_suffix(".md"), comparisons)
    print(f"wrote {output_prefix.with_suffix('.csv')}")
    print(f"wrote {output_prefix.with_suffix('.md')}")


if __name__ == "__main__":
    main()
