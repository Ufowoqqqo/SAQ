#!/usr/bin/env python3
"""Propose residual-aware SAQ segment plans offline.

This script mirrors SAQ's dynamic segment/bit planner, but allows the DP cost
vector to come from pooled IVF residual variance instead of global PCA variance.
It is diagnostic-only: it does not modify encoding/search artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from segment_diagnostics import load_plan, padded_vector, read_fvecs, read_ivecs, slice_segment


K_DIM_PADDING_SIZE = 64
K_MAX_QUANT_BIT = 11
K_NUM_SHORT_FACTORS = 2
FLOAT_BITS = 32


Plan = list[dict[str, int]]


def rd_up_to_multiple(value: int, multiple: int) -> int:
    return ((value + multiple - 1) // multiple) * multiple


def infer_avg_bits(plan_csv: Path) -> float | None:
    with plan_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return None
    label = rows[0].get("avg_bits_label")
    if label is None or label == "":
        return None
    try:
        return float(label)
    except ValueError:
        return None


def normalize_plan(plan: list[dict[str, int]] | list[tuple[int, int]]) -> Plan:
    out: Plan = []
    start = 0
    for idx, item in enumerate(plan):
        if isinstance(item, dict):
            dim_len = int(item["dim_len"])
            bits = int(item["bits"])
        else:
            dim_len = int(item[0])
            bits = int(item[1])
        out.append(
            {
                "segment_id": idx,
                "start_dim": start,
                "end_dim": start + dim_len,
                "dim_len": dim_len,
                "bits": bits,
            }
        )
        start += dim_len
    return out


def plan_signature(plan: Plan) -> list[tuple[int, int]]:
    return [(int(seg["dim_len"]), int(seg["bits"])) for seg in plan]


def format_plan(plan: Plan) -> str:
    return "; ".join(
        f"{seg['start_dim']}-{seg['end_dim']}: {seg['bits']}b" for seg in plan
    )


def compact_seg_plan(plan: Plan) -> str:
    return ",".join(f"{seg['dim_len']}:{seg['bits']}" for seg in plan)


def dynamic_programming(
    risk_vector: np.ndarray,
    avg_bits: float,
    padding_size: int = K_DIM_PADDING_SIZE,
    max_quant_bit: int = K_MAX_QUANT_BIT,
    num_short_factors: int = K_NUM_SHORT_FACTORS,
) -> tuple[Plan, dict[str, Any]]:
    padded_dim = int(risk_vector.size)
    if padded_dim % padding_size != 0:
        raise ValueError(f"risk vector length {padded_dim} is not divisible by {padding_size}")

    blocks = padded_dim // padding_size
    num_bit_factors = num_short_factors * FLOAT_BITS
    total_bits = int(avg_bits * padded_dim + num_bit_factors)
    max_num_segs = blocks if avg_bits < 2 else blocks // 2
    prefix = np.concatenate([[0.0], np.cumsum(np.asarray(risk_vector, dtype=np.float64))])

    # dp[ns][i][used_bits] = cost. i is measured in 64-dimensional blocks.
    dp: list[list[dict[int, float]]] = [
        [dict() for _ in range(blocks + 1)] for _ in range(max_num_segs + 1)
    ]
    prev: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    dp[0][0][0] = 0.0

    best_cost = math.inf
    best_state: tuple[int, int, int] | None = None

    for ns in range(max_num_segs + 1):
        for i in range(blocks + 1):
            states = dp[ns][i]
            for used_bits in sorted(states):
                cur_cost = states[used_bits]
                if i == blocks:
                    # Match SAQ's 1.01 tolerance: do not switch plans for tiny cost
                    # differences, which tends to preserve earlier/lower-budget states.
                    if cur_cost * 1.01 < best_cost:
                        best_cost = cur_cost
                        best_state = (ns, i, used_bits)
                    continue
                if ns == max_num_segs:
                    continue

                var_sum = 0.0
                for j in range(1, blocks - i + 1):
                    start = (i + j - 1) * padding_size
                    end = (i + j) * padding_size
                    var_sum += float(prefix[end] - prefix[start])

                    for bits in range(1, max_quant_bit + 1):
                        new_used_bits = used_bits + bits * j * padding_size + num_bit_factors
                        if new_used_bits > total_bits:
                            break
                        new_cost = cur_cost + var_sum / (1 << bits)
                        key = (ns + 1, i + j, new_used_bits)
                        old_cost = dp[ns + 1][i + j].get(new_used_bits, math.inf)
                        if old_cost > new_cost:
                            dp[ns + 1][i + j][new_used_bits] = new_cost
                            prev[key] = (i, used_bits, bits)

                # SAQ allows only the final tail segment to be assigned 0 bits.
                new_cost = cur_cost + var_sum
                old_cost = dp[ns + 1][blocks].get(used_bits, math.inf)
                if old_cost > new_cost:
                    dp[ns + 1][blocks][used_bits] = new_cost
                    prev[(ns + 1, blocks, used_bits)] = (i, used_bits, 0)

    if best_state is None:
        raise RuntimeError("DP did not find a valid plan")

    ns, i, used_bits = best_state
    reversed_plan: list[tuple[int, int]] = []
    while i > 0:
        key = (ns, i, used_bits)
        if key not in prev:
            raise RuntimeError(f"missing predecessor for state {key}")
        prev_i, prev_used_bits, bits = prev[key]
        dim_len = (i - prev_i) * padding_size
        reversed_plan.append((dim_len, bits))
        ns -= 1
        i = prev_i
        used_bits = prev_used_bits

    plan = normalize_plan(list(reversed(reversed_plan)))
    meta = {
        "dp_cost": float(best_cost),
        "dp_used_bits": int(best_state[2]),
        "total_bits_budget": int(total_bits),
        "num_bit_factors": int(num_bit_factors),
        "max_num_segs": int(max_num_segs),
        "padding_size": int(padding_size),
        "max_quant_bit": int(max_quant_bit),
    }
    return plan, meta


def compute_residual_risk(
    base: np.ndarray,
    centroids: np.ndarray,
    cids: np.ndarray,
    min_cluster_size: int,
    risk_stat: str,
    chunk_rows: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    if cids.ndim == 2:
        if cids.shape[1] != 1:
            raise ValueError(f"cluster id ivecs must have dimension 1, got {cids.shape[1]}")
        cids = cids[:, 0]
    cids = cids.astype(np.int64, copy=False).reshape(-1)
    if base.shape[0] != cids.size:
        raise ValueError(f"base rows {base.shape[0]} != cluster ids {cids.size}")
    if cids.min(initial=0) < 0 or cids.max(initial=0) >= centroids.shape[0]:
        raise ValueError(
            f"cluster id range [{cids.min()}, {cids.max()}] incompatible with {centroids.shape[0]} centroids"
        )

    counts = np.bincount(cids, minlength=centroids.shape[0]).astype(np.int64)
    valid_cluster = counts >= min_cluster_size
    dim = base.shape[1]

    if risk_stat == "pooled_second_moment":
        risk_sum = np.zeros(dim, dtype=np.float64)
        used_rows = 0
        for start in range(0, base.shape[0], chunk_rows):
            stop = min(start + chunk_rows, base.shape[0])
            labels = cids[start:stop]
            row_mask = valid_cluster[labels]
            if not np.any(row_mask):
                continue
            labels = labels[row_mask]
            residual = base[start:stop][row_mask].astype(np.float64, copy=False) - centroids[labels].astype(
                np.float64, copy=False
            )
            risk_sum += np.einsum("ij,ij->j", residual, residual)
            used_rows += int(residual.shape[0])
        if used_rows == 0:
            raise ValueError("no rows remain after min-cluster-size filtering")
        risk = risk_sum / used_rows
    elif risk_stat == "pooled_centered_var":
        sums = np.zeros((centroids.shape[0], dim), dtype=np.float64)
        sums_sq = np.zeros((centroids.shape[0], dim), dtype=np.float64)
        for start in range(0, base.shape[0], chunk_rows):
            stop = min(start + chunk_rows, base.shape[0])
            labels = cids[start:stop]
            row_mask = valid_cluster[labels]
            if not np.any(row_mask):
                continue
            labels = labels[row_mask]
            residual = base[start:stop][row_mask].astype(np.float64, copy=False) - centroids[labels].astype(
                np.float64, copy=False
            )
            np.add.at(sums, labels, residual)
            np.add.at(sums_sq, labels, residual * residual)
        valid_counts = counts[valid_cluster].astype(np.float64)
        if valid_counts.size == 0:
            raise ValueError("no clusters remain after min-cluster-size filtering")
        sse = sums_sq[valid_cluster] - (sums[valid_cluster] * sums[valid_cluster]) / valid_counts[:, None]
        sse = np.maximum(sse, 0.0)
        risk = sse.sum(axis=0) / float(valid_counts.sum())
        used_rows = int(valid_counts.sum())
    else:
        raise ValueError(f"unsupported residual risk stat: {risk_stat}")

    summary = {
        "cluster_count": int(centroids.shape[0]),
        "used_cluster_count": int(valid_cluster.sum()),
        "skipped_cluster_count": int((~valid_cluster).sum()),
        "min_cluster_size": int(min_cluster_size),
        "base_count": int(base.shape[0]),
        "used_rows": int(used_rows),
        "dimension": int(dim),
        "cluster_size_min": int(counts.min()) if counts.size else 0,
        "cluster_size_p50": float(np.percentile(counts, 50)) if counts.size else 0.0,
        "cluster_size_p90": float(np.percentile(counts, 90)) if counts.size else 0.0,
        "cluster_size_max": int(counts.max()) if counts.size else 0,
    }
    return risk.astype(np.float64, copy=False), summary


def plan_used_bits(plan: Plan, num_bit_factors: int) -> int:
    total = 0
    for seg in plan:
        bits = int(seg["bits"])
        if bits > 0:
            total += bits * int(seg["dim_len"]) + num_bit_factors
    return int(total)


def plan_cost(plan: Plan, risk_vector: np.ndarray) -> float:
    cost = 0.0
    for seg in plan:
        risk_sum = float(slice_segment(risk_vector, seg["start_dim"], seg["end_dim"]).sum())
        bits = int(seg["bits"])
        cost += risk_sum / (1 << bits) if bits > 0 else risk_sum
    return float(cost)


def risk_share(vector: np.ndarray, start: int, end: int) -> tuple[float, float]:
    part_sum = float(slice_segment(vector, start, end).sum())
    total = float(vector.sum())
    return part_sum, part_sum / total if total > 0 else 0.0


def describe_plan_rows(
    plan_name: str,
    risk_source: str,
    plan: Plan,
    global_vector: np.ndarray,
    residual_vector: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for seg in plan:
        global_sum, global_share = risk_share(global_vector, seg["start_dim"], seg["end_dim"])
        residual_sum, residual_share = risk_share(residual_vector, seg["start_dim"], seg["end_dim"])
        bits = int(seg["bits"])
        denom = (1 << bits) if bits > 0 else 1
        rows.append(
            {
                "plan_name": plan_name,
                "risk_source": risk_source,
                "segment_id": int(seg["segment_id"]),
                "start_dim": int(seg["start_dim"]),
                "end_dim": int(seg["end_dim"]),
                "dim_len": int(seg["dim_len"]),
                "bits": bits,
                "global_var_sum": global_sum,
                "global_var_share": global_share,
                "residual_risk_sum": residual_sum,
                "residual_risk_share": residual_share,
                "global_cost_contrib": global_sum / denom,
                "residual_cost_contrib": residual_sum / denom,
            }
        )
    return rows


def write_plan_csv(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "plan_name",
        "risk_source",
        "segment_id",
        "start_dim",
        "end_dim",
        "dim_len",
        "bits",
        "global_var_sum",
        "global_var_share",
        "residual_risk_sum",
        "residual_risk_share",
        "global_cost_contrib",
        "residual_cost_contrib",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Propose residual-aware SAQ plans offline.")
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
    parser.add_argument("--chunk-rows", type=int, default=2048, help="Rows per residual accumulation chunk.")
    parser.add_argument("--output", type=Path, required=True, help="Output CSV with compared plans.")
    parser.add_argument("--summary-output", type=Path, default=None, help="Optional JSON summary output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    avg_bits = args.avg_bits
    default_plan: Plan | None = None
    if args.default_plan_csv is not None:
        default_plan = normalize_plan(load_plan(args.default_plan_csv, args.plan_id))
        if avg_bits is None:
            avg_bits = infer_avg_bits(args.default_plan_csv)
    if avg_bits is None:
        raise ValueError("--avg-bits is required when it cannot be inferred from --default-plan-csv")

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

    global_plan, global_dp_meta = dynamic_programming(global_vector, avg_bits)
    residual_plan, residual_dp_meta = dynamic_programming(residual_vector, avg_bits)
    num_bit_factors = int(global_dp_meta["num_bit_factors"])

    plans: list[tuple[str, str, Plan]] = []
    if default_plan is not None:
        plans.append(("default_saq", "saq_global_variance", default_plan))
    plans.append(("global_dp_reimpl", "global_pca_variance", global_plan))
    plans.append(("residual_dp", args.residual_risk_stat, residual_plan))

    rows: list[dict[str, Any]] = []
    costs: dict[str, Any] = {}
    for plan_name, risk_source, plan in plans:
        rows.extend(describe_plan_rows(plan_name, risk_source, plan, global_vector, residual_vector))
        used_bits = plan_used_bits(plan, num_bit_factors)
        costs[plan_name] = {
            "plan": format_plan(plan),
            "seg_plan": compact_seg_plan(plan),
            "segments": [
                {
                    "start_dim": int(seg["start_dim"]),
                    "end_dim": int(seg["end_dim"]),
                    "dim_len": int(seg["dim_len"]),
                    "bits": int(seg["bits"]),
                }
                for seg in plan
            ],
            "segment_count": int(len(plan)),
            "used_bits_including_nonzero_segment_overhead": int(used_bits),
            "effective_avg_bits_including_overhead": float(used_bits / padded_dim),
            "global_cost": plan_cost(plan, global_vector),
            "residual_cost": plan_cost(plan, residual_vector),
        }

    write_plan_csv(rows, args.output)

    default_key = "default_saq" if default_plan is not None else "global_dp_reimpl"
    default_residual_cost = costs[default_key]["residual_cost"]
    residual_cost = costs["residual_dp"]["residual_cost"]
    default_global_cost = costs[default_key]["global_cost"]
    residual_global_cost = costs["residual_dp"]["global_cost"]

    global_total = float(global_vector.sum())
    residual_total = float(residual_vector.sum())
    global_share = global_vector / global_total if global_total > 0 else np.zeros_like(global_vector)
    residual_share = residual_vector / residual_total if residual_total > 0 else np.zeros_like(residual_vector)
    share_tv = 0.5 * float(np.abs(global_share - residual_share).sum())
    pearson = 0.0
    if np.std(global_vector) > 0 and np.std(residual_vector) > 0:
        pearson = float(np.corrcoef(global_vector, residual_vector)[0, 1])

    summary = {
        "dataset": args.dataset,
        "data_dir": str(args.data_dir),
        "k": int(args.k),
        "avg_bits": float(avg_bits),
        "dimension": int(base.shape[1]),
        "padded_dimension": int(padded_dim),
        "residual_risk_stat": args.residual_risk_stat,
        "residual_summary": residual_summary,
        "global_dp_meta": global_dp_meta,
        "residual_dp_meta": residual_dp_meta,
        "default_plan_csv": str(args.default_plan_csv) if args.default_plan_csv else None,
        "default_matches_global_dp_reimpl": (
            plan_signature(default_plan) == plan_signature(global_plan) if default_plan is not None else None
        ),
        "plans": costs,
        "residual_cost_reduction_vs_default": (
            1.0 - residual_cost / default_residual_cost if default_residual_cost > 0 else 0.0
        ),
        "global_cost_change_vs_default": (
            residual_global_cost / default_global_cost - 1.0 if default_global_cost > 0 else 0.0
        ),
        "global_vs_residual_share_total_variation": share_tv,
        "global_vs_residual_vector_pearson": pearson,
        "output": str(args.output),
    }

    if args.summary_output is not None:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
