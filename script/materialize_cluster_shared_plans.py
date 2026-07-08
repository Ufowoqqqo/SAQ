#!/usr/bin/env python3
"""Materialize shared local SAQ plans for the mixed-plan prototype.

The materialized file is intentionally simple so the C++ index builder can read
it without an additional JSON dependency. Plan learning and assignment remain
query-unaware: they use only base PCA vectors, IVF centroids, cluster ids, and
residual variance profiles.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import cluster_residual_feasibility_matrix as matrix  # noqa: E402
import cluster_residual_plan_feasibility as crp  # noqa: E402


def compact_plan(plan: crp.Plan) -> str:
    return crp.compact_plan(plan)


def plan_search_cost(plan: crp.Plan, bit_weight: float) -> float:
    positive_segments = sum(1 for _, bits in plan if bits > 0)
    total_segments = len(plan)
    used_bits = crp.plan_used_bits(plan)
    if total_segments == 0:
        return math.inf
    return float(positive_segments + total_segments + bit_weight * used_bits)


def materialize(args: argparse.Namespace) -> dict[str, Any]:
    case = matrix.MatrixCase(
        name=args.name,
        data_dir=Path(args.data_dir),
        dataset=args.dataset,
        k=args.k,
        max_vectors=args.max_vectors,
    )
    prepared = matrix.prepare_case(
        case=case,
        sample_seed=args.sample_seed,
        chunk_size=args.chunk_size,
        min_cluster_size=args.min_cluster_size,
        risk_stat=args.risk_stat,
    )

    active = prepared.active_indices
    active_weights = prepared.weights[active]
    global_plan, _, total_bits = crp.dp_plan_from_block_sums(
        prepared.global_block_sums, args.avg_bits
    )
    global_costs = np.array(
        [crp.plan_cost(prepared.cluster_block_sums[c], global_plan) for c in range(prepared.counts.size)]
    )
    global_weighted_cost = float(np.sum(global_costs[active] * active_weights))

    local_costs = np.full(prepared.counts.size, np.nan, dtype=np.float64)
    for cid in active:
        _, cost, _ = crp.dp_plan_from_block_sums(prepared.cluster_block_sums[cid], args.avg_bits)
        local_costs[cid] = cost
    local_weighted_cost = float(np.sum(local_costs[active] * active_weights))
    local_ratio = local_weighted_cost / max(global_weighted_cost, args.eps)

    profile_totals = prepared.cluster_block_sums[active].sum(axis=1)
    features = prepared.cluster_block_sums[active] / np.maximum(profile_totals, args.eps)[:, None]
    labels = crp.weighted_kmeans(
        features, active_weights, args.shared_plan_count, args.sample_seed, args.kmeans_iters
    )

    group_plans: list[crp.Plan] = []
    group_costs = np.zeros((active.size, args.shared_plan_count), dtype=np.float64)
    profile_assigned_cost = 0.0
    nblocks = prepared.padded_dim // crp.K_DIM_PADDING_SIZE

    for gid in range(args.shared_plan_count):
        member_mask = labels == gid
        if not np.any(member_mask):
            group_plans.append(tuple())
            group_costs[:, gid] = np.inf
            continue
        member_indices = active[member_mask]
        member_weights = prepared.weights[member_indices]
        group_var = np.average(
            prepared.cluster_risk[member_indices], axis=0, weights=member_weights
        )
        group_block_sums = group_var.reshape(nblocks, crp.K_DIM_PADDING_SIZE).sum(axis=1)
        plan, _, _ = crp.dp_plan_from_block_sums(group_block_sums, args.avg_bits)
        group_plans.append(plan)
        for pos, cid in enumerate(active):
            group_costs[pos, gid] = crp.plan_cost(prepared.cluster_block_sums[cid], plan)
        profile_assigned_cost += float(np.sum(group_costs[member_mask, gid] * active_weights[member_mask]))

    unique_plan_ids: dict[str, int] = {}
    unique_plans: list[str] = []
    unique_plan_search_costs: list[float] = []
    group_to_unique: list[int] = []
    for plan in group_plans:
        plan_str = compact_plan(plan)
        if plan_str not in unique_plan_ids:
            unique_plan_ids[plan_str] = len(unique_plans)
            unique_plans.append(plan_str)
            unique_plan_search_costs.append(plan_search_cost(plan, args.search_cost_bit_weight))
        group_to_unique.append(unique_plan_ids[plan_str])

    global_search_cost = plan_search_cost(global_plan, args.search_cost_bit_weight)
    group_search_costs = np.array(
        [plan_search_cost(plan, args.search_cost_bit_weight) for plan in group_plans], dtype=np.float64
    )
    normalized_residual_costs = group_costs / np.maximum(global_costs[active], args.eps)[:, None]
    normalized_search_costs = group_search_costs / max(global_search_cost, args.eps)
    assignment_scores = normalized_residual_costs + args.search_cost_lambda * normalized_search_costs[None, :]

    cost_assigned_group = np.argmin(assignment_scores, axis=1)
    cost_assigned_costs = np.min(group_costs, axis=1)
    cost_aware_assigned_costs = group_costs[np.arange(active.size), cost_assigned_group]
    cost_assigned_weighted_cost = float(np.sum(cost_assigned_costs * active_weights))
    cost_aware_assigned_weighted_cost = float(np.sum(cost_aware_assigned_costs * active_weights))
    assigned_score = float(np.sum(assignment_scores[np.arange(active.size), cost_assigned_group] * active_weights))

    cluster_plan_ids = np.zeros(prepared.num_clusters, dtype=np.int64)
    cluster_assignment_source = np.full(prepared.num_clusters, "inactive", dtype=object)
    for pos, cid in enumerate(active):
        group_id = int(cost_assigned_group[pos])
        cluster_plan_ids[cid] = group_to_unique[group_id]
        cluster_assignment_source[cid] = "cost_aware" if args.search_cost_lambda > 0 else "cost"

    output_prefix = Path(args.output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    shared_plan_file = output_prefix.with_suffix(".shared_plans.txt")
    summary_json = output_prefix.with_suffix(".summary.json")
    assignment_csv = output_prefix.with_suffix(".assignments.csv")
    summary_md = output_prefix.with_suffix(".md")

    with shared_plan_file.open("w", encoding="utf-8") as f:
        f.write("shared_plans_v1\n")
        f.write(f"num_plans {len(unique_plans)}\n")
        for plan_id, plan_str in enumerate(unique_plans):
            f.write(f"plan {plan_id} {plan_str}\n")
        f.write(f"num_clusters {prepared.num_clusters}\n")
        f.write("assignments\n")
        for cid, plan_id in enumerate(cluster_plan_ids):
            f.write(f"{cid} {int(plan_id)}\n")

    active_set = set(active.tolist())
    active_pos = {int(cid): pos for pos, cid in enumerate(active)}
    assignment_rows: list[dict[str, Any]] = []
    for cid in range(prepared.num_clusters):
        assignment_rows.append(
            {
                "cluster_id": cid,
                "sample_count": int(prepared.counts[cid]),
                "active": bool(cid in active_set),
                "plan_id": int(cluster_plan_ids[cid]),
                "source": str(cluster_assignment_source[cid]),
                "global_cost": float(global_costs[cid]),
                "local_oracle_cost": "" if not np.isfinite(local_costs[cid]) else float(local_costs[cid]),
                "assigned_cost": ""
                if cid not in active_set
                else float(cost_aware_assigned_costs[active_pos[cid]]),
            }
        )
    with assignment_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(assignment_rows[0].keys()))
        writer.writeheader()
        writer.writerows(assignment_rows)

    local_gain = 1.0 - local_ratio
    cost_assigned_ratio = cost_assigned_weighted_cost / max(global_weighted_cost, args.eps)
    cost_aware_assigned_ratio = cost_aware_assigned_weighted_cost / max(global_weighted_cost, args.eps)
    retention = (1.0 - cost_assigned_ratio) / local_gain if local_gain > args.eps else 0.0
    cost_aware_retention = (1.0 - cost_aware_assigned_ratio) / local_gain if local_gain > args.eps else 0.0
    metadata_bits = prepared.num_clusters * max(1, math.ceil(math.log2(max(len(unique_plans), 2))))

    summary = {
        "case": args.name,
        "dataset": args.dataset,
        "k": args.k,
        "avg_bits": args.avg_bits,
        "shared_plan_count_requested": args.shared_plan_count,
        "shared_plan_count_unique": len(unique_plans),
        "num_vectors": prepared.num_vectors,
        "sampled_vectors": prepared.sampled_vectors,
        "num_clusters": prepared.num_clusters,
        "active_clusters": int(active.size),
        "global_plan": compact_plan(global_plan),
        "total_bits": total_bits,
        "local_oracle_ratio": local_ratio,
        "profile_assigned_ratio": profile_assigned_cost / max(global_weighted_cost, args.eps),
        "cost_assigned_ratio": cost_assigned_ratio,
        "cost_aware_assigned_ratio": cost_aware_assigned_ratio,
        "shared_retention": retention,
        "cost_aware_shared_retention": cost_aware_retention,
        "search_cost_lambda": args.search_cost_lambda,
        "search_cost_bit_weight": args.search_cost_bit_weight,
        "global_search_cost": global_search_cost,
        "plan_search_costs": unique_plan_search_costs,
        "assigned_score": assigned_score,
        "plan_id_metadata_bits": metadata_bits,
        "plans": unique_plans,
        "paths": {
            "shared_plan_file": str(shared_plan_file),
            "summary_json": str(summary_json),
            "assignment_csv": str(assignment_csv),
            "summary_md": str(summary_md),
        },
    }
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Materialized Cluster Shared Plans",
        "",
        "This artifact is query-unaware and is intended for the mixed-plan index",
        "prototype only.",
        "",
        f"- dataset: `{args.dataset}`",
        f"- K: {args.k}",
        f"- B: {args.avg_bits}",
        f"- requested shared plans: {args.shared_plan_count}",
        f"- unique shared plans: {len(unique_plans)}",
        f"- global plan: `{compact_plan(global_plan)}`",
        f"- local-oracle ratio: {local_ratio:.6f}",
        f"- cost-assigned ratio: {cost_assigned_ratio:.6f}",
        f"- cost-aware assigned ratio: {cost_aware_assigned_ratio:.6f}",
        f"- shared retention: {retention:.3f}",
        f"- cost-aware shared retention: {cost_aware_retention:.3f}",
        f"- search-cost lambda: {args.search_cost_lambda}",
        f"- plan-id metadata: {metadata_bits} bits",
        "",
        "## Plans",
        "",
    ]
    for plan_id, plan_str in enumerate(unique_plans):
        count = int(np.sum(cluster_plan_ids == plan_id))
        lines.append(
            f"- plan {plan_id}: `{plan_str}` ({count} clusters, "
            f"search cost {unique_plan_search_costs[plan_id]:.3f})"
        )
    lines.extend(
        [
            "",
            "## C++ Build Input",
            "",
            f"`{shared_plan_file}`",
            "",
        ]
    )
    summary_md.write_text("\n".join(lines), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize shared cluster SAQ plans.")
    parser.add_argument("--name", default="shared_plan_case", help="Case label.")
    parser.add_argument("--data-dir", required=True, help="Prepared dataset artifact directory.")
    parser.add_argument("--dataset", required=True, help="Dataset artifact prefix.")
    parser.add_argument("--k", type=int, required=True, help="IVF cluster count.")
    parser.add_argument("--avg-bits", type=float, required=True, help="SAQ bit budget.")
    parser.add_argument("--shared-plan-count", type=int, default=4, help="Shared plan family size.")
    parser.add_argument("--max-vectors", type=int, default=100000, help="Sample size; 0 means all.")
    parser.add_argument("--sample-seed", type=int, default=0, help="Deterministic sample seed.")
    parser.add_argument("--chunk-size", type=int, default=8192, help="Residual accumulation chunk size.")
    parser.add_argument("--min-cluster-size", type=int, default=2, help="Minimum active cluster size.")
    parser.add_argument("--kmeans-iters", type=int, default=30, help="Weighted k-means iterations.")
    parser.add_argument(
        "--search-cost-lambda",
        type=float,
        default=0.0,
        help="Weight for normalized plan search-cost proxy in cluster-plan assignment.",
    )
    parser.add_argument(
        "--search-cost-bit-weight",
        type=float,
        default=0.0,
        help="Optional weight for used bits in the plan search-cost proxy.",
    )
    parser.add_argument(
        "--risk-stat",
        choices=["variance", "second_moment"],
        default="variance",
        help="Residual statistic used as the DP risk vector.",
    )
    parser.add_argument("--eps", type=float, default=1e-12, help="Numerical floor for ratios.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix.")
    return parser.parse_args()


def main() -> None:
    summary = materialize(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
