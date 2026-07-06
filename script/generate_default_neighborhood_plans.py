#!/usr/bin/env python3
"""Generate default-neighborhood SAQ segment-plan candidates.

The current boundary-aware sweeps are good at exposing raw endpoints, but they
can miss middle plans close to the SAQ default. This generator creates a small,
structured neighborhood around the default plan: widen/split the head, merge
middle segments, and optionally expand the zero tail while keeping the SAQ bit
budget and conservative shape guards visible.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from propose_residual_plan import (
    FLOAT_BITS,
    K_DIM_PADDING_SIZE,
    K_MAX_QUANT_BIT,
    K_NUM_SHORT_FACTORS,
    compact_seg_plan,
    dynamic_programming,
    format_plan,
    infer_avg_bits,
    normalize_plan,
    padded_vector,
    plan_signature,
    plan_used_bits,
    rd_up_to_multiple,
)
from segment_diagnostics import load_plan, read_fvecs
from sweep_boundary_plan import plan_feasibility_reasons, plan_metrics, write_csv


Plan = list[dict[str, int]]


def parse_plan_spec(spec: str) -> Plan:
    parts: list[tuple[int, int]] = []
    for raw in spec.split(","):
        token = raw.strip()
        if not token:
            continue
        if ":" in token:
            left, right = token.split(":", 1)
        elif "x" in token:
            left, right = token.split("x", 1)
        else:
            raise ValueError(f"bad plan token: {token!r}")
        parts.append((int(left), int(right)))
    if not parts:
        raise ValueError("empty plan spec")
    return normalize_plan(parts)


def positive_segments(plan: Plan) -> Plan:
    return [seg for seg in plan if int(seg["bits"]) > 0]


def zero_tail_dim(plan: Plan) -> int:
    if plan and int(plan[-1]["bits"]) == 0:
        return int(plan[-1]["dim_len"])
    return 0


def raw_bit_sum(plan: Plan) -> int:
    return sum(int(seg["dim_len"]) * int(seg["bits"]) for seg in positive_segments(plan))


def total_budget_bits(avg_bits: float, padded_dim: int) -> int:
    return int(avg_bits * padded_dim + K_NUM_SHORT_FACTORS * FLOAT_BITS)


def merge_adjacent_same_bits(parts: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for dim, bits in parts:
        if dim <= 0:
            continue
        if merged and merged[-1][1] == bits:
            merged[-1] = (merged[-1][0] + dim, bits)
        else:
            merged.append((dim, bits))
    return merged


def make_plan(parts: list[tuple[int, int]], total_dim: int) -> Plan | None:
    merged = merge_adjacent_same_bits(parts)
    if sum(dim for dim, _ in merged) != total_dim:
        return None
    if any(dim <= 0 for dim, _ in merged):
        return None
    if any(bits < 0 or bits > K_MAX_QUANT_BIT for _, bits in merged):
        return None
    return normalize_plan(merged)


def is_nonincreasing_bits(plan: Plan) -> bool:
    bits = [int(seg["bits"]) for seg in plan]
    return all(bits[idx] >= bits[idx + 1] for idx in range(len(bits) - 1))


def add_candidate(
    out: dict[str, dict[str, Any]],
    plan: Plan | None,
    family: str,
    rationale: str,
    avg_bits: float,
    total_dim: int,
    require_nonincreasing: bool,
) -> None:
    if plan is None:
        return
    if sum(int(seg["dim_len"]) for seg in plan) != total_dim:
        return
    if require_nonincreasing and not is_nonincreasing_bits(plan):
        return
    used_bits = plan_used_bits(plan, K_NUM_SHORT_FACTORS * FLOAT_BITS)
    budget = total_budget_bits(avg_bits, total_dim)
    if used_bits > budget:
        return
    sig = compact_seg_plan(plan)
    existing = out.get(sig)
    if existing is None:
        out[sig] = {
            "seg_plan": sig,
            "plan": format_plan(plan),
            "families": family,
            "rationales": rationale,
            "used_bits_including_nonzero_segment_overhead": int(used_bits),
            "budget_bits": int(budget),
            "budget_slack_bits": int(budget - used_bits),
            "effective_avg_bits_including_overhead": float(used_bits / total_dim),
            **plan_metrics(plan),
        }
    else:
        families = set(str(existing["families"]).split(";"))
        rationales = set(str(existing["rationales"]).split(";"))
        families.add(family)
        rationales.add(rationale)
        existing["families"] = ";".join(sorted(families))
        existing["rationales"] = ";".join(sorted(rationales))


def infer_default_plan(args: argparse.Namespace) -> tuple[Plan, dict[str, Any]]:
    if args.default_plan:
        return parse_plan_spec(args.default_plan), {"source": "default_plan_arg"}
    if args.default_plan_csv is not None:
        avg_bits = args.avg_bits
        plan = normalize_plan(load_plan(args.default_plan_csv, args.plan_id))
        if avg_bits is None:
            avg_bits = infer_avg_bits(args.default_plan_csv)
        return plan, {"source": "default_plan_csv", "avg_bits": avg_bits}
    if args.data_dir is None or args.dataset is None or args.avg_bits is None:
        raise ValueError(
            "provide --default-plan, --default-plan-csv, or "
            "--data-dir/--dataset/--avg-bits"
        )
    global_var = read_fvecs(args.data_dir / f"{args.dataset}_base_pca.vars.fvecs").reshape(-1)
    padded_dim = rd_up_to_multiple(global_var.size, K_DIM_PADDING_SIZE)
    global_vector = padded_vector(global_var, padded_dim).astype(np.float64, copy=False)
    plan, meta = dynamic_programming(global_vector, args.avg_bits)
    return plan, {"source": "global_dp_reimpl", "meta": meta}


def gen_head_split(default: Plan, total_dim: int) -> list[tuple[Plan | None, str, str]]:
    pos = positive_segments(default)
    tail = zero_tail_dim(default)
    if len(pos) < 2:
        return []
    first = pos[0]
    second = pos[1]
    if int(second["dim_len"]) <= K_DIM_PADDING_SIZE:
        return []
    parts: list[tuple[int, int]] = [
        (int(first["dim_len"]), max(1, int(first["bits"]) - 2)),
        (K_DIM_PADDING_SIZE, min(K_MAX_QUANT_BIT, int(second["bits"]) + 1)),
        (int(second["dim_len"]) - K_DIM_PADDING_SIZE, int(second["bits"])),
    ]
    parts.extend((int(seg["dim_len"]), int(seg["bits"])) for seg in pos[2:])
    if tail:
        parts.append((tail, 0))
    plan = make_plan(parts, total_dim)
    return [(plan, "head_split", "split the post-head block and move one level of precision into it")]


def gen_head_widen_keep_levels(
    default: Plan,
    total_dim: int,
    avg_bits: float,
) -> list[tuple[Plan | None, str, str]]:
    pos = positive_segments(default)
    tail = zero_tail_dim(default)
    if len(pos) < 3:
        return []
    first = pos[0]
    second = pos[1]
    delta = K_DIM_PADDING_SIZE
    if int(second["dim_len"]) <= delta:
        return []

    raw_budget = total_budget_bits(avg_bits, total_dim) - len(pos) * K_NUM_SHORT_FACTORS * FLOAT_BITS
    rest: list[tuple[int, int]] = [(int(second["dim_len"]) - delta, int(second["bits"]))]
    rest.extend((int(seg["dim_len"]), int(seg["bits"])) for seg in pos[2:])
    rest_bits = sum(dim * bits for dim, bits in rest)
    head_dim = int(first["dim_len"]) + delta
    wanted = (raw_budget - rest_bits) / head_dim

    plans: list[tuple[Plan | None, str, str]] = []
    for head_bits in sorted({int(np.floor(wanted)), int(np.ceil(wanted))}):
        parts = [(head_dim, head_bits), *rest]
        if tail:
            parts.append((tail, 0))
        plans.append(
            (
                make_plan(parts, total_dim),
                "head_widen_keep_levels",
                "widen the head by one block while preserving later bit levels",
            )
        )
    return plans


def gen_speed_merge_same_tail(
    default: Plan,
    total_dim: int,
) -> list[tuple[Plan | None, str, str]]:
    pos = positive_segments(default)
    tail = zero_tail_dim(default)
    if len(pos) < 3:
        return []
    first = pos[0]
    second = pos[1]
    head_dim = int(first["dim_len"]) + K_DIM_PADDING_SIZE
    nonzero_dim = total_dim - tail
    if head_dim >= nonzero_dim:
        return []
    mid_dim = nonzero_dim - head_dim
    parts = [
        (head_dim, max(1, int(first["bits"]) - 2)),
        (mid_dim, max(1, int(second["bits"]) - 1)),
    ]
    if tail:
        parts.append((tail, 0))
    return [
        (
            make_plan(parts, total_dim),
            "speed_merge_same_tail",
            "merge middle/tail-positive dimensions into a lower-segment speed candidate",
        )
    ]


def gen_tail_expand_middle_merge(
    default: Plan,
    total_dim: int,
    avg_bits: float,
) -> list[tuple[Plan | None, str, str]]:
    pos = positive_segments(default)
    tail = zero_tail_dim(default)
    if len(pos) < 3:
        return []

    new_tail = tail + K_DIM_PADDING_SIZE
    if new_tail >= total_dim:
        return []
    new_nonzero_dim = total_dim - new_tail
    raw_budget = total_budget_bits(avg_bits, total_dim) - 3 * K_NUM_SHORT_FACTORS * FLOAT_BITS

    first = pos[0]
    second = pos[1]
    plans: list[tuple[Plan | None, str, str]] = []

    # Keep the original small head, widen the first middle segment, and solve
    # the final middle bitwidth from the remaining budget.
    head_dim = int(first["dim_len"])
    mid1_dim = min(new_nonzero_dim - head_dim, int(second["dim_len"]) + 2 * K_DIM_PADDING_SIZE)
    mid2_dim = new_nonzero_dim - head_dim - mid1_dim
    if mid2_dim >= K_DIM_PADDING_SIZE:
        head_bits = max(1, int(first["bits"]) - 1)
        mid1_bits = int(second["bits"])
        remain = raw_budget - head_dim * head_bits - mid1_dim * mid1_bits
        mid2_wanted = remain / mid2_dim
        for mid2_bits in sorted({int(np.floor(mid2_wanted)), int(np.ceil(mid2_wanted))}):
            parts = [(head_dim, head_bits), (mid1_dim, mid1_bits), (mid2_dim, mid2_bits), (new_tail, 0)]
            plans.append(
                (
                    make_plan(parts, total_dim),
                    "tail_expand_middle_merge",
                    "preserve a small head, merge middle dimensions, and expand the zero tail",
                )
            )

    # Widen the head and use two broad middle/tail-positive chunks. This is the
    # compact-speed counterpart of the previous middle-preserving rule.
    head_dim = int(first["dim_len"]) + K_DIM_PADDING_SIZE
    rest_dim = new_nonzero_dim - head_dim
    if rest_dim >= 2 * K_DIM_PADDING_SIZE:
        mid1_dim = (rest_dim // (2 * K_DIM_PADDING_SIZE)) * K_DIM_PADDING_SIZE
        mid1_dim = max(K_DIM_PADDING_SIZE, mid1_dim)
        mid2_dim = rest_dim - mid1_dim
        if mid2_dim >= K_DIM_PADDING_SIZE:
            head_bits = max(1, int(first["bits"]) - 2)
            mid1_bits = max(1, int(second["bits"]) - 1)
            remain = raw_budget - head_dim * head_bits - mid1_dim * mid1_bits
            mid2_wanted = remain / mid2_dim
            for mid2_bits in sorted({int(np.floor(mid2_wanted)), int(np.ceil(mid2_wanted))}):
                parts = [(head_dim, head_bits), (mid1_dim, mid1_bits), (mid2_dim, mid2_bits), (new_tail, 0)]
                plans.append(
                    (
                        make_plan(parts, total_dim),
                        "tail_expand_head_widen",
                        "widen the head, use broad middle chunks, and expand the zero tail",
                    )
                )

    return plans


def generate_candidates(default: Plan, avg_bits: float, total_dim: int, args: argparse.Namespace) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    add_candidate(
        candidates,
        default,
        "default",
        "SAQ default/global-DP baseline",
        avg_bits,
        total_dim,
        args.require_nonincreasing_bits,
    )
    generators = [
        gen_head_split(default, total_dim),
        gen_head_widen_keep_levels(default, total_dim, avg_bits),
        gen_speed_merge_same_tail(default, total_dim),
        gen_tail_expand_middle_merge(default, total_dim, avg_bits),
    ]
    for generated in generators:
        for plan, family, rationale in generated:
            add_candidate(
                candidates,
                plan,
                family,
                rationale,
                avg_bits,
                total_dim,
                args.require_nonincreasing_bits,
            )

    rows = list(candidates.values())
    for row in rows:
        reasons = plan_feasibility_reasons(row, args)
        row["is_feasible"] = not reasons
        row["infeasible_reasons"] = ";".join(reasons)
        row["is_default"] = row["seg_plan"] == compact_seg_plan(default)
    if args.filter_infeasible:
        rows = [row for row in rows if row["is_feasible"]]
    rows.sort(
        key=lambda row: (
            bool(row["is_default"]),
            int(row["budget_slack_bits"]),
            int(row["segment_count"]),
            int(row["nonzero_segment_count"]),
            row["seg_plan"],
        )
    )
    for idx, row in enumerate(rows):
        row["candidate_rank"] = idx
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate default-neighborhood SAQ plans.")
    parser.add_argument("--data-dir", type=Path, default=None, help="SAQ dataset artifact directory.")
    parser.add_argument("--dataset", default=None, help="Dataset artifact prefix.")
    parser.add_argument("--avg-bits", type=float, default=None, help="Average bit budget B.")
    parser.add_argument("--default-plan", default="", help="Compact default plan string, e.g. 64:9,192:5.")
    parser.add_argument("--default-plan-csv", type=Path, default=None, help="Optional extracted default plan CSV.")
    parser.add_argument("--plan-id", type=int, default=0, help="Plan id for --default-plan-csv.")
    parser.add_argument("--dimension", type=int, default=0, help="Plan dimension; inferred from default plan if omitted.")
    parser.add_argument("--min-positive-bits", type=int, default=2, help="Guard: minimum positive segment bits.")
    parser.add_argument("--min-zero-tail-dim", type=int, default=0, help="Guard: minimum nonempty zero-tail length.")
    parser.add_argument("--max-segments", type=int, default=0, help="Guard: maximum total segment count.")
    parser.add_argument("--max-nonzero-segment-dim", type=int, default=0, help="Guard: maximum positive segment width.")
    parser.add_argument("--exclude-internal-1bit", action="store_true", help="Guard: reject internal 1-bit segments.")
    parser.add_argument("--exclude-nonfinal-1bit", action="store_true", help="Guard: reject non-final 1-bit segments.")
    parser.add_argument("--filter-infeasible", action="store_true", help="Write only feasible candidates.")
    parser.add_argument(
        "--require-nonincreasing-bits",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require segment bits to be nonincreasing from head to tail.",
    )
    parser.add_argument("--expect-plan", action="append", default=[], help="Expected plan string for validation.")
    parser.add_argument("--output-prefix", type=Path, required=True, help="Prefix for .csv and .summary.json outputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    default, default_meta = infer_default_plan(args)
    avg_bits = args.avg_bits
    if avg_bits is None:
        avg_bits = default_meta.get("avg_bits")
    if avg_bits is None:
        raise ValueError("--avg-bits is required unless it can be inferred")
    total_dim = args.dimension or sum(int(seg["dim_len"]) for seg in default)
    if total_dim != sum(int(seg["dim_len"]) for seg in default):
        raise ValueError("--dimension does not match default plan length")

    rows = generate_candidates(default, float(avg_bits), total_dim, args)
    expected = {compact_seg_plan(parse_plan_spec(spec)) for spec in args.expect_plan}
    found = {row["seg_plan"] for row in rows}
    missing = sorted(expected - found)

    fields = [
        "candidate_rank",
        "seg_plan",
        "plan",
        "families",
        "rationales",
        "is_default",
        "is_feasible",
        "infeasible_reasons",
        "used_bits_including_nonzero_segment_overhead",
        "budget_bits",
        "budget_slack_bits",
        "effective_avg_bits_including_overhead",
        "segment_count",
        "nonzero_segment_count",
        "max_segment_dim_len",
        "max_nonzero_segment_dim_len",
        "largest_nonzero_segment",
        "positive_bitwidths",
        "min_positive_bits",
        "zero_tail_dim_len",
        "has_positive_1bit_segment",
        "has_internal_1bit_segment",
        "has_nonfinal_1bit_segment",
        "has_128_512_segment",
        "has_wide_128_512_5bit",
    ]
    csv_path = args.output_prefix.with_suffix(".csv")
    summary_path = args.output_prefix.with_suffix(".summary.json")
    write_csv(csv_path, rows, fields)
    summary = {
        "dataset": args.dataset,
        "avg_bits": float(avg_bits),
        "dimension": int(total_dim),
        "default_plan": compact_seg_plan(default),
        "default_plan_formatted": format_plan(default),
        "default_meta": default_meta,
        "candidate_count": len(rows),
        "expected_plans": sorted(expected),
        "missing_expected_plans": missing,
        "families": {
            family: sum(1 for row in rows if family in str(row["families"]).split(";"))
            for family in sorted({f for row in rows for f in str(row["families"]).split(";")})
        },
        "outputs": {
            "csv": str(csv_path),
            "summary_json": str(summary_path),
        },
        "top_candidates": rows[:20],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if missing:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
