#!/usr/bin/env python3
"""Batch sweep boundary-aware SAQ segment plans.

This is the batch counterpart of propose_residual_plan.py. It loads dataset
artifacts and computes global/residual/tail risk once, then enumerates many
boundary-aware DP hyperparameter settings.
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
    K_DIM_PADDING_SIZE,
    compact_seg_plan,
    compute_residual_risk,
    compute_residual_tail_risk,
    dynamic_programming,
    format_plan,
    infer_avg_bits,
    make_boundary_risk_vector,
    normalize_plan,
    padded_vector,
    plan_cost,
    plan_signature,
    plan_used_bits,
    rd_up_to_multiple,
)
from segment_diagnostics import load_plan, read_fvecs, read_ivecs


DEFAULT_GLOBAL_BLENDS = "0,0.15,0.25,0.4"
DEFAULT_TAIL_ALPHAS = "0,0.1,0.25,0.5"
DEFAULT_SEGMENT_PENALTY_SCALES = "0,0.005,0.01,0.02,0.04"
DEFAULT_INTRA_SEGMENT_PENALTY_SCALES = "0,0.8,1.6,2.4,3.2,4.8,6.4"


def parse_float_list(text: str) -> list[float]:
    values: list[float] = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        values.append(float(token))
    if not values:
        raise ValueError(f"empty float list: {text!r}")
    return values


def float_label(value: float) -> str:
    return f"{value:g}"


def plan_metrics(plan: list[dict[str, int]]) -> dict[str, Any]:
    nonzero = [seg for seg in plan if int(seg["bits"]) > 0]
    largest = max(nonzero or plan, key=lambda seg: int(seg["dim_len"]))
    positive_bits = [int(seg["bits"]) for seg in nonzero]
    zero_tail = 0
    if plan and int(plan[-1]["bits"]) == 0:
        zero_tail = int(plan[-1]["dim_len"])
    return {
        "segment_count": int(len(plan)),
        "nonzero_segment_count": int(len(nonzero)),
        "max_segment_dim_len": int(max(int(seg["dim_len"]) for seg in plan)),
        "max_nonzero_segment_dim_len": int(max(int(seg["dim_len"]) for seg in nonzero)) if nonzero else 0,
        "largest_nonzero_segment": f"{largest['start_dim']}-{largest['end_dim']}:{largest['bits']}b",
        "positive_bitwidths": ";".join(str(bit) for bit in positive_bits),
        "min_positive_bits": int(min(positive_bits)) if positive_bits else 0,
        "zero_tail_dim_len": int(zero_tail),
        "has_positive_1bit_segment": any(bit == 1 for bit in positive_bits),
        "has_internal_1bit_segment": any(
            int(seg["bits"]) == 1 and 0 < idx < len(plan) - 1 for idx, seg in enumerate(plan)
        ),
        "has_nonfinal_1bit_segment": any(
            int(seg["bits"]) == 1 and idx < len(plan) - 1 for idx, seg in enumerate(plan)
        ),
        "has_128_512_segment": any(
            int(seg["start_dim"]) == 128 and int(seg["end_dim"]) == 512 for seg in plan
        ),
        "has_wide_128_512_5bit": any(
            int(seg["start_dim"]) == 128 and int(seg["end_dim"]) == 512 and int(seg["bits"]) == 5
            for seg in plan
        ),
    }


def plan_feasibility_reasons(metrics: dict[str, Any], args: argparse.Namespace) -> list[str]:
    reasons: list[str] = []
    if args.min_positive_bits > 0 and int(metrics["min_positive_bits"]) < args.min_positive_bits:
        reasons.append(f"min_positive_bits<{args.min_positive_bits}")
    if args.min_zero_tail_dim > 0:
        zero_tail = int(metrics["zero_tail_dim_len"])
        if 0 < zero_tail < args.min_zero_tail_dim:
            reasons.append(f"zero_tail_dim_len<{args.min_zero_tail_dim}")
    if args.max_segments > 0 and int(metrics["segment_count"]) > args.max_segments:
        reasons.append(f"segment_count>{args.max_segments}")
    if args.max_nonzero_segment_dim > 0 and int(metrics["max_nonzero_segment_dim_len"]) > args.max_nonzero_segment_dim:
        reasons.append(f"max_nonzero_segment_dim_len>{args.max_nonzero_segment_dim}")
    if args.exclude_internal_1bit and bool(metrics["has_internal_1bit_segment"]):
        reasons.append("internal_1bit_segment")
    if args.exclude_nonfinal_1bit and bool(metrics["has_nonfinal_1bit_segment"]):
        reasons.append("nonfinal_1bit_segment")
    return reasons


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch sweep boundary-aware SAQ plans.")
    parser.add_argument("--data-dir", type=Path, required=True, help="SAQ dataset artifact directory.")
    parser.add_argument("--dataset", required=True, help="Dataset artifact prefix.")
    parser.add_argument("--k", type=int, required=True, help="Number of IVF clusters.")
    parser.add_argument("--avg-bits", type=float, default=None, help="Average bit budget B. Inferred from plan CSV if omitted.")
    parser.add_argument("--default-plan-csv", type=Path, default=None, help="Optional extracted SAQ default plan CSV.")
    parser.add_argument("--plan-id", type=int, default=0, help="Plan id to read from default plan CSV.")
    parser.add_argument(
        "--residual-risk-stat",
        choices=("pooled_centered_var", "pooled_second_moment"),
        default="pooled_centered_var",
        help="Residual risk vector used by residual-aware DP.",
    )
    parser.add_argument("--min-cluster-size", type=int, default=2, help="Skip clusters smaller than this size.")
    parser.add_argument("--boundary-tail-quantile", type=float, default=0.95, help="Quantile used for residual tail-excess risk.")
    parser.add_argument("--boundary-global-blends", default=DEFAULT_GLOBAL_BLENDS, help="Comma-separated global blend grid.")
    parser.add_argument("--boundary-tail-alphas", default=DEFAULT_TAIL_ALPHAS, help="Comma-separated tail alpha grid.")
    parser.add_argument("--segment-penalty-scales", default=DEFAULT_SEGMENT_PENALTY_SCALES, help="Comma-separated segment penalty scale grid.")
    parser.add_argument("--intra-segment-penalty-scales", default=DEFAULT_INTRA_SEGMENT_PENALTY_SCALES, help="Comma-separated intra-segment penalty scale grid.")
    parser.add_argument("--min-positive-bits", type=int, default=0, help="Guard: require every positive-bit segment to use at least this many bits; 0 disables.")
    parser.add_argument("--min-zero-tail-dim", type=int, default=0, help="Guard: reject nonempty zero-bit tails shorter than this many dimensions; 0 disables.")
    parser.add_argument("--max-segments", type=int, default=0, help="Guard: reject plans with more than this many segments; 0 disables.")
    parser.add_argument("--max-nonzero-segment-dim", type=int, default=0, help="Guard: reject plans whose widest positive-bit segment exceeds this width; 0 disables.")
    parser.add_argument("--exclude-internal-1bit", action="store_true", help="Guard: reject plans with a 1-bit segment that is neither first nor last.")
    parser.add_argument("--exclude-nonfinal-1bit", action="store_true", help="Guard: reject plans with a 1-bit segment before the final segment.")
    parser.add_argument("--filter-infeasible", action="store_true", help="Write only feasible rows/unique plans under the enabled guards.")
    parser.add_argument("--chunk-rows", type=int, default=2048, help="Rows per residual accumulation chunk.")
    parser.add_argument("--output-prefix", type=Path, required=True, help="Prefix for .csv, .unique.csv, and .summary.json outputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    avg_bits = args.avg_bits
    default_plan = None
    if args.default_plan_csv is not None:
        default_plan = normalize_plan(load_plan(args.default_plan_csv, args.plan_id))
        if avg_bits is None:
            avg_bits = infer_avg_bits(args.default_plan_csv)
    if avg_bits is None:
        raise ValueError("--avg-bits is required when it cannot be inferred from --default-plan-csv")

    global_blends = parse_float_list(args.boundary_global_blends)
    tail_alphas = parse_float_list(args.boundary_tail_alphas)
    segment_penalty_scales = parse_float_list(args.segment_penalty_scales)
    intra_segment_penalty_scales = parse_float_list(args.intra_segment_penalty_scales)

    base = read_fvecs(args.data_dir / f"{args.dataset}_base_pca.fvecs")
    centroids = read_fvecs(args.data_dir / f"{args.dataset}_centroid_{args.k}_pca.fvecs")
    cids = read_ivecs(args.data_dir / f"{args.dataset}_cluster_id_{args.k}.ivecs")
    global_var = read_fvecs(args.data_dir / f"{args.dataset}_base_pca.vars.fvecs").reshape(-1)

    padded_dim = rd_up_to_multiple(base.shape[1], K_DIM_PADDING_SIZE)
    global_vector = padded_vector(global_var, padded_dim).astype(np.float64, copy=False)
    residual_vector_raw, residual_summary = compute_residual_risk(
        base,
        centroids,
        cids,
        args.min_cluster_size,
        args.residual_risk_stat,
        args.chunk_rows,
    )
    residual_vector = padded_vector(residual_vector_raw, padded_dim).astype(np.float64, copy=False)

    tail_vector = None
    tail_summary = None
    if any(alpha > 0 for alpha in tail_alphas):
        tail_vector_raw, tail_summary = compute_residual_tail_risk(
            base,
            centroids,
            cids,
            args.min_cluster_size,
            args.boundary_tail_quantile,
            args.chunk_rows,
        )
        tail_vector = padded_vector(tail_vector_raw, padded_dim).astype(np.float64, copy=False)

    global_plan, global_dp_meta = dynamic_programming(global_vector, avg_bits)
    residual_plan, residual_dp_meta = dynamic_programming(residual_vector, avg_bits)
    num_bit_factors = int(global_dp_meta["num_bit_factors"])
    default_key_plan = default_plan if default_plan is not None else global_plan

    boundary_cache: dict[tuple[float, float], tuple[np.ndarray, dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    config_id = 0
    total_configs = len(global_blends) * len(tail_alphas) * len(segment_penalty_scales) * len(intra_segment_penalty_scales)
    for global_blend in global_blends:
        for tail_alpha in tail_alphas:
            cache_key = (global_blend, tail_alpha)
            if cache_key not in boundary_cache:
                boundary_cache[cache_key] = make_boundary_risk_vector(
                    global_vector,
                    residual_vector,
                    tail_vector,
                    global_blend,
                    tail_alpha,
                )
            boundary_vector, boundary_meta = boundary_cache[cache_key]
            boundary_sum = float(boundary_vector.sum())
            for segment_penalty_scale in segment_penalty_scales:
                segment_penalty = segment_penalty_scale * boundary_sum / (2.0 ** float(avg_bits))
                for intra_scale in intra_segment_penalty_scales:
                    plan, meta = dynamic_programming(
                        boundary_vector,
                        avg_bits,
                        segment_penalty=segment_penalty,
                        intra_segment_penalty_scale=intra_scale,
                    )
                    used_bits = plan_used_bits(plan, num_bit_factors)
                    candidate_cost = plan_cost(plan, boundary_vector, segment_penalty, intra_scale)
                    default_cost = plan_cost(default_key_plan, boundary_vector, segment_penalty, intra_scale)
                    global_cost = plan_cost(global_plan, boundary_vector, segment_penalty, intra_scale)
                    residual_cost = plan_cost(residual_plan, boundary_vector, segment_penalty, intra_scale)
                    reduction = 1.0 - candidate_cost / default_cost if default_cost > 0 else 0.0
                    sig = compact_seg_plan(plan)
                    metrics = plan_metrics(plan)
                    infeasible_reasons = plan_feasibility_reasons(metrics, args)
                    row = {
                        "config_id": config_id,
                        "boundary_global_blend": float(global_blend),
                        "boundary_tail_alpha": float(tail_alpha),
                        "segment_penalty_scale": float(segment_penalty_scale),
                        "segment_penalty": float(segment_penalty),
                        "intra_segment_penalty_scale": float(intra_scale),
                        "seg_plan": sig,
                        "plan": format_plan(plan),
                        "dp_cost": float(meta["dp_cost"]),
                        "dp_used_bits": int(meta["dp_used_bits"]),
                        "used_bits_including_nonzero_segment_overhead": int(used_bits),
                        "effective_avg_bits_including_overhead": float(used_bits / padded_dim),
                        "boundary_cost": float(candidate_cost),
                        "default_boundary_cost": float(default_cost),
                        "global_boundary_cost": float(global_cost),
                        "residual_boundary_cost": float(residual_cost),
                        "boundary_cost_reduction_vs_default": float(reduction),
                        "boundary_sum": boundary_sum,
                        "global_norm_sum": float(boundary_meta["global_norm_sum"]),
                        "residual_sum": float(boundary_meta["residual_sum"]),
                        "tail_norm_sum": float(boundary_meta["tail_norm_sum"]),
                        **metrics,
                        "is_feasible": not infeasible_reasons,
                        "infeasible_reasons": ";".join(infeasible_reasons),
                    }
                    rows.append(row)
                    groups[sig].append(row)
                    config_id += 1

    all_rows = rows
    all_groups = groups
    feasible_rows = [row for row in all_rows if row["is_feasible"]]
    if args.filter_infeasible:
        rows = feasible_rows
        groups = defaultdict(list)
        for row in rows:
            groups[row["seg_plan"]].append(row)

    rows.sort(key=lambda row: (-row["boundary_cost_reduction_vs_default"], row["boundary_cost"], row["seg_plan"]))
    all_rows_by_reduction = sorted(
        all_rows,
        key=lambda row: (-row["boundary_cost_reduction_vs_default"], row["boundary_cost"], row["seg_plan"]),
    )

    unique_rows: list[dict[str, Any]] = []
    for plan_id, (seg_plan, group_rows) in enumerate(
        sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
    ):
        best = min(group_rows, key=lambda row: row["boundary_cost"])
        best_reduction = max(group_rows, key=lambda row: row["boundary_cost_reduction_vs_default"])
        unique_rows.append(
            {
                "plan_id": plan_id,
                "seg_plan": seg_plan,
                "plan": best["plan"],
                "config_count": len(group_rows),
                "best_config_id_by_cost": best["config_id"],
                "best_boundary_cost": best["boundary_cost"],
                "best_reduction_config_id": best_reduction["config_id"],
                "best_boundary_cost_reduction_vs_default": best_reduction["boundary_cost_reduction_vs_default"],
                "segment_count": best["segment_count"],
                "nonzero_segment_count": best["nonzero_segment_count"],
                "max_segment_dim_len": best["max_segment_dim_len"],
                "max_nonzero_segment_dim_len": best["max_nonzero_segment_dim_len"],
                "largest_nonzero_segment": best["largest_nonzero_segment"],
                "positive_bitwidths": best["positive_bitwidths"],
                "min_positive_bits": best["min_positive_bits"],
                "zero_tail_dim_len": best["zero_tail_dim_len"],
                "has_positive_1bit_segment": best["has_positive_1bit_segment"],
                "has_internal_1bit_segment": best["has_internal_1bit_segment"],
                "has_nonfinal_1bit_segment": best["has_nonfinal_1bit_segment"],
                "has_128_512_segment": best["has_128_512_segment"],
                "has_wide_128_512_5bit": best["has_wide_128_512_5bit"],
                "is_feasible": best["is_feasible"],
                "infeasible_reasons": best["infeasible_reasons"],
                "global_blends": ";".join(sorted({float_label(row["boundary_global_blend"]) for row in group_rows})),
                "tail_alphas": ";".join(sorted({float_label(row["boundary_tail_alpha"]) for row in group_rows})),
                "segment_penalty_scales": ";".join(sorted({float_label(row["segment_penalty_scale"]) for row in group_rows})),
                "intra_segment_penalty_scales": ";".join(sorted({float_label(row["intra_segment_penalty_scale"]) for row in group_rows})),
            }
        )
    unique_rows.sort(
        key=lambda row: (
            -row["config_count"],
            row["segment_count"],
            row["max_nonzero_segment_dim_len"],
            -row["best_boundary_cost_reduction_vs_default"],
            row["seg_plan"],
        )
    )
    for idx, row in enumerate(unique_rows):
        row["plan_rank"] = idx

    output_csv = args.output_prefix.with_suffix(".csv")
    unique_csv = args.output_prefix.with_suffix(".unique.csv")
    summary_json = args.output_prefix.with_suffix(".summary.json")

    row_fields = [
        "config_id",
        "boundary_global_blend",
        "boundary_tail_alpha",
        "segment_penalty_scale",
        "segment_penalty",
        "intra_segment_penalty_scale",
        "seg_plan",
        "plan",
        "dp_cost",
        "dp_used_bits",
        "used_bits_including_nonzero_segment_overhead",
        "effective_avg_bits_including_overhead",
        "boundary_cost",
        "default_boundary_cost",
        "global_boundary_cost",
        "residual_boundary_cost",
        "boundary_cost_reduction_vs_default",
        "boundary_sum",
        "global_norm_sum",
        "residual_sum",
        "tail_norm_sum",
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
        "is_feasible",
        "infeasible_reasons",
    ]
    unique_fields = [
        "plan_rank",
        "plan_id",
        "seg_plan",
        "plan",
        "config_count",
        "best_config_id_by_cost",
        "best_boundary_cost",
        "best_reduction_config_id",
        "best_boundary_cost_reduction_vs_default",
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
        "is_feasible",
        "infeasible_reasons",
        "global_blends",
        "tail_alphas",
        "segment_penalty_scales",
        "intra_segment_penalty_scales",
    ]
    write_csv(output_csv, rows, row_fields)
    write_csv(unique_csv, unique_rows, unique_fields)

    summary = {
        "dataset": args.dataset,
        "data_dir": str(args.data_dir),
        "k": int(args.k),
        "avg_bits": float(avg_bits),
        "dimension": int(base.shape[1]),
        "padded_dimension": int(padded_dim),
        "grid": {
            "boundary_global_blends": global_blends,
            "boundary_tail_alphas": tail_alphas,
            "segment_penalty_scales": segment_penalty_scales,
            "intra_segment_penalty_scales": intra_segment_penalty_scales,
            "total_configs": total_configs,
        },
        "residual_risk_stat": args.residual_risk_stat,
        "residual_summary": residual_summary,
        "tail_summary": tail_summary,
        "global_dp": {
            "seg_plan": compact_seg_plan(global_plan),
            "plan": format_plan(global_plan),
            "meta": global_dp_meta,
        },
        "residual_dp": {
            "seg_plan": compact_seg_plan(residual_plan),
            "plan": format_plan(residual_plan),
            "meta": residual_dp_meta,
        },
        "default_plan": compact_seg_plan(default_plan) if default_plan is not None else None,
        "feasibility_guard": {
            "min_positive_bits": int(args.min_positive_bits),
            "min_zero_tail_dim": int(args.min_zero_tail_dim),
            "max_segments": int(args.max_segments),
            "max_nonzero_segment_dim": int(args.max_nonzero_segment_dim),
            "exclude_internal_1bit": bool(args.exclude_internal_1bit),
            "exclude_nonfinal_1bit": bool(args.exclude_nonfinal_1bit),
            "filter_infeasible": bool(args.filter_infeasible),
        },
        "all_config_count": len(all_rows),
        "feasible_config_count": len(feasible_rows),
        "infeasible_config_count": len(all_rows) - len(feasible_rows),
        "selected_config_count": len(rows),
        "all_unique_plan_count": len(all_groups),
        "feasible_unique_plan_count": len({row["seg_plan"] for row in feasible_rows}),
        "unique_plan_count": len(unique_rows),
        "top_unique_by_frequency": unique_rows[:20],
        "top_configs_by_reduction": rows[:20],
        "top_all_configs_by_reduction": all_rows_by_reduction[:20],
        "outputs": {
            "config_csv": str(output_csv),
            "unique_csv": str(unique_csv),
            "summary_json": str(summary_json),
        },
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "all_configs": len(all_rows),
        "feasible_configs": len(feasible_rows),
        "selected_configs": len(rows),
        "all_unique_plans": len(all_groups),
        "selected_unique_plans": len(unique_rows),
        "filter_infeasible": bool(args.filter_infeasible),
        "config_csv": str(output_csv),
        "unique_csv": str(unique_csv),
        "summary_json": str(summary_json),
        "top_unique_by_frequency": unique_rows[:5],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
