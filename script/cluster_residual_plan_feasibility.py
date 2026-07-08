#!/usr/bin/env python3
"""Offline cluster-residual feasibility study for structural SAQ follow-up.

This script does not build or modify an index. It compares SAQ's one global
plan against cluster-local oracle plans and small shared plan families under
the same variance-proxy DP objective used by SAQ.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from utils.io import read_somefiles  # noqa: E402


K_DIM_PADDING_SIZE = 64
K_MAX_QUANT_BITS = 13
K_NUM_SHORT_FACTORS = 2
FLOAT_BITS = 32
SEGMENT_OVERHEAD_BITS = K_NUM_SHORT_FACTORS * FLOAT_BITS


Plan = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class StudyPaths:
    base: Path
    centroids: Path
    cluster_ids: Path
    global_vars: Path | None


def infer_paths(args: argparse.Namespace) -> StudyPaths:
    if args.base and args.centroids and args.cluster_ids:
        return StudyPaths(
            base=Path(args.base),
            centroids=Path(args.centroids),
            cluster_ids=Path(args.cluster_ids),
            global_vars=Path(args.global_vars) if args.global_vars else None,
        )

    if not (args.data_dir and args.dataset and args.k):
        raise SystemExit(
            "Provide either --base/--centroids/--cluster-ids or --data-dir/--dataset/--k."
        )

    data_dir = Path(args.data_dir)
    suffix = "_pca" if args.pca else ""
    base = data_dir / f"{args.dataset}_base{suffix}.fvecs"
    centroids = data_dir / f"{args.dataset}_centroid_{args.k}{suffix}.fvecs"
    cluster_ids = data_dir / f"{args.dataset}_cluster_id_{args.k}.ivecs"
    global_vars = data_dir / f"{args.dataset}_base{suffix}.vars.fvecs"

    return StudyPaths(
        base=base,
        centroids=centroids,
        cluster_ids=cluster_ids,
        global_vars=global_vars if global_vars.exists() else None,
    )


def xvecs_shape(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        first = np.fromfile(f, dtype=np.int32, count=1)
    if first.size != 1:
        raise ValueError(f"empty xvecs file: {path}")
    dim = int(first[0])
    row_bytes = 4 * (dim + 1)
    size = path.stat().st_size
    if size % row_bytes != 0:
        raise ValueError(f"{path} size is not divisible by xvecs row size")
    rows = size // row_bytes
    return rows, dim


def mmap_fvecs(path: Path) -> np.ndarray:
    rows, dim = xvecs_shape(path)
    raw = np.memmap(path, dtype=np.int32, mode="r", shape=(rows, dim + 1))
    return raw[:, 1:].view(np.float32)


def mmap_ivecs(path: Path) -> np.ndarray:
    rows, dim = xvecs_shape(path)
    raw = np.memmap(path, dtype=np.int32, mode="r", shape=(rows, dim + 1))
    return raw[:, 1:]


def read_vector_file(path: Path) -> np.ndarray:
    return np.asarray(read_somefiles(str(path)))


def pad_variance(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    padded_dim = int(math.ceil(values.size / K_DIM_PADDING_SIZE) * K_DIM_PADDING_SIZE)
    if padded_dim == values.size:
        return values
    out = np.zeros(padded_dim, dtype=np.float64)
    out[: values.size] = values
    return out


def compact_plan(plan: Plan) -> str:
    return ",".join(f"{dim}:{bits}" for dim, bits in plan)


def plan_used_bits(plan: Plan) -> int:
    used = 0
    for dim, bits in plan:
        if bits > 0:
            used += dim * bits + SEGMENT_OVERHEAD_BITS
    return used


def plan_cost(block_sums: np.ndarray, plan: Plan) -> float:
    cost = 0.0
    block_offset = 0
    for dim, bits in plan:
        nblocks = dim // K_DIM_PADDING_SIZE
        seg_sum = float(block_sums[block_offset : block_offset + nblocks].sum())
        cost += seg_sum if bits == 0 else seg_sum / float(1 << bits)
        block_offset += nblocks
    return cost


def dp_plan_from_block_sums(block_sums: np.ndarray, avg_bits: float) -> tuple[Plan, float, int]:
    block_sums = np.asarray(block_sums, dtype=np.float64).reshape(-1)
    nblocks = int(block_sums.size)
    padded_dim = nblocks * K_DIM_PADDING_SIZE
    total_bits = int(avg_bits * padded_dim + SEGMENT_OVERHEAD_BITS)
    max_segments = nblocks if avg_bits < 2 else nblocks // 2

    states: list[list[dict[int, float]]] = [
        [dict() for _ in range(nblocks + 1)] for _ in range(max_segments + 1)
    ]
    parents: dict[tuple[int, int, int], tuple[int, int, int, int]] = {}
    states[0][0][0] = 0.0

    best_key: tuple[int, int, int] | None = None
    best_cost = math.inf

    for ns in range(max_segments + 1):
        for i in range(nblocks + 1):
            for used_bits, prefix_cost in list(states[ns][i].items()):
                if i == nblocks:
                    if prefix_cost * 1.01 < best_cost:
                        best_cost = prefix_cost
                        best_key = (ns, i, used_bits)
                    continue
                if ns == max_segments:
                    continue

                var_sum = 0.0
                for j in range(1, nblocks - i + 1):
                    var_sum += float(block_sums[i + j - 1])
                    dim_len = j * K_DIM_PADDING_SIZE
                    for bits in range(1, K_MAX_QUANT_BITS + 1):
                        new_used = used_bits + bits * dim_len + SEGMENT_OVERHEAD_BITS
                        if new_used > total_bits:
                            break
                        new_cost = prefix_cost + var_sum / float(1 << bits)
                        current = states[ns + 1][i + j].get(new_used, math.inf)
                        if new_cost < current:
                            states[ns + 1][i + j][new_used] = new_cost
                            parents[(ns + 1, i + j, new_used)] = (ns, i, used_bits, bits)

                zero_cost = prefix_cost + var_sum
                current = states[ns + 1][nblocks].get(used_bits, math.inf)
                if zero_cost < current:
                    states[ns + 1][nblocks][used_bits] = zero_cost
                    parents[(ns + 1, nblocks, used_bits)] = (ns, i, used_bits, 0)

    if best_key is None:
        raise RuntimeError("SAQ DP did not find a feasible plan")

    segments: list[tuple[int, int]] = []
    key = best_key
    while key[1] > 0:
        prev_ns, prev_i, prev_used, bits = parents[key]
        dim_len = (key[1] - prev_i) * K_DIM_PADDING_SIZE
        segments.append((dim_len, bits))
        key = (prev_ns, prev_i, prev_used)
    segments.reverse()
    plan = tuple(segments)
    return plan, best_cost, total_bits


def choose_sample_indices(num_rows: int, max_vectors: int, seed: int) -> np.ndarray:
    if max_vectors <= 0 or max_vectors >= num_rows:
        return np.arange(num_rows, dtype=np.int64)
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(num_rows, size=max_vectors, replace=False))


def accumulate_cluster_residuals(
    base: np.ndarray,
    centroids: np.ndarray,
    cluster_ids: np.ndarray,
    sample_indices: np.ndarray,
    chunk_size: int,
    risk_stat: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    num_clusters, dim = centroids.shape
    counts = np.zeros(num_clusters, dtype=np.int64)
    sums = np.zeros((num_clusters, dim), dtype=np.float64)
    sumsq = np.zeros((num_clusters, dim), dtype=np.float64)

    flat_cids = np.asarray(cluster_ids).reshape(-1)
    for start in range(0, sample_indices.size, chunk_size):
        idx = sample_indices[start : start + chunk_size]
        cids = flat_cids[idx].astype(np.int64, copy=False)
        if np.any(cids < 0) or np.any(cids >= num_clusters):
            bad = cids[(cids < 0) | (cids >= num_clusters)][0]
            raise ValueError(f"bad cluster id {bad}; expected [0, {num_clusters})")

        x = np.asarray(base[idx], dtype=np.float64)
        residual = x - centroids[cids].astype(np.float64, copy=False)
        counts += np.bincount(cids, minlength=num_clusters)
        np.add.at(sums, cids, residual)
        np.add.at(sumsq, cids, residual * residual)

    if risk_stat == "second_moment":
        denom = np.maximum(counts, 1).reshape(-1, 1)
        risk = sumsq / denom
    else:
        denom = np.maximum(counts, 1).reshape(-1, 1)
        mean = sums / denom
        risk = (sumsq / denom) - mean * mean
        risk = np.maximum(risk, 0.0)

    risk[counts == 0, :] = 0.0
    return counts, risk, sumsq


def weighted_kmeans(
    features: np.ndarray,
    weights: np.ndarray,
    k: int,
    seed: int,
    iterations: int,
) -> np.ndarray:
    del seed  # deterministic initialization below keeps reruns stable.
    n = features.shape[0]
    if k <= 0 or k > n:
        raise ValueError(f"invalid k={k} for {n} active clusters")

    centers = np.empty((k, features.shape[1]), dtype=np.float64)
    first = int(np.argmax(weights))
    centers[0] = features[first]
    min_dist = np.sum((features - centers[0]) ** 2, axis=1)
    for ci in range(1, k):
        idx = int(np.argmax(min_dist * np.sqrt(weights)))
        centers[ci] = features[idx]
        min_dist = np.minimum(min_dist, np.sum((features - centers[ci]) ** 2, axis=1))

    labels = np.zeros(n, dtype=np.int64)
    for _ in range(iterations):
        dists = np.sum((features[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        new_labels = np.argmin(dists, axis=1)
        if np.array_equal(labels, new_labels):
            break
        labels = new_labels
        for ci in range(k):
            mask = labels == ci
            if not np.any(mask):
                farthest = int(np.argmax(np.min(dists, axis=1) * np.sqrt(weights)))
                centers[ci] = features[farthest]
                labels[farthest] = ci
                continue
            centers[ci] = np.average(features[mask], axis=0, weights=weights[mask])
    return labels


def summarize_ratios(values: np.ndarray, weights: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    mask = np.isfinite(values) & (weights > 0)
    if not np.any(mask):
        return {"mean": math.nan, "p50": math.nan, "p90": math.nan}
    values = values[mask]
    weights = weights[mask]
    order = np.argsort(values)
    sorted_vals = values[order]
    sorted_weights = weights[order]
    cdf = np.cumsum(sorted_weights) / np.sum(sorted_weights)

    def wq(q: float) -> float:
        return float(sorted_vals[np.searchsorted(cdf, q, side="left")])

    return {
        "mean": float(np.average(values, weights=weights)),
        "p50": wq(0.5),
        "p90": wq(0.9),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_markdown(path: Path, summary: dict[str, Any], plan_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Cluster Residual Plan Feasibility Study",
        "",
        "This is an offline query-unaware diagnostic. It does not build or modify",
        "an index and does not use held-out query labels.",
        "",
        "## Inputs",
        "",
        f"- base: `{summary['paths']['base']}`",
        f"- centroids: `{summary['paths']['centroids']}`",
        f"- cluster ids: `{summary['paths']['cluster_ids']}`",
        f"- global vars: `{summary['paths'].get('global_vars')}`",
        f"- sampled vectors: {summary['sampled_vectors']} / {summary['num_vectors']}",
        f"- active clusters: {summary['active_clusters']} / {summary['num_clusters']}",
        f"- risk statistic: `{summary['risk_stat']}`",
        "",
        "## Result",
        "",
        f"- average bits: {summary['avg_bits']}",
        f"- global plan: `{summary['global_plan']}`",
        f"- local-oracle weighted cost ratio: {summary['local_oracle']['weighted_cost_ratio']:.6g}",
        f"- local-oracle weighted ratio mean: {summary['local_oracle']['ratio_summary']['mean']:.6g}",
        "",
        "| shared plans | profile-assigned ratio | best-of-family ratio | active groups |",
        "|---:|---:|---:|---:|",
    ]
    for row in plan_rows:
        if row["role"] != "shared_family_summary":
            continue
        lines.append(
            "| {M} | {assigned_cost_ratio_vs_global:.6g} | "
            "{best_cost_ratio_vs_global:.6g} | {active_groups} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "Continue toward real index implementation only if local-oracle plans",
            "show a noticeable weighted cost reduction and a small shared family",
            "retains much of that gain. Otherwise, this direction should stop",
            "before changing the SAQ index format.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    paths = infer_paths(args)
    for required in [paths.base, paths.centroids, paths.cluster_ids]:
        if not required.exists():
            raise FileNotFoundError(required)

    base = mmap_fvecs(paths.base) if paths.base.suffix == ".fvecs" else read_vector_file(paths.base)
    cluster_ids = mmap_ivecs(paths.cluster_ids) if paths.cluster_ids.suffix == ".ivecs" else read_vector_file(paths.cluster_ids)
    centroids = np.asarray(read_vector_file(paths.centroids), dtype=np.float32)

    num_vectors, dim = base.shape
    if centroids.ndim != 2 or centroids.shape[1] != dim:
        raise ValueError(f"centroids shape {centroids.shape} does not match base dim {dim}")
    if cluster_ids.shape[0] != num_vectors:
        raise ValueError(
            f"cluster id rows {cluster_ids.shape[0]} do not match base rows {num_vectors}"
        )

    sample_indices = choose_sample_indices(num_vectors, args.max_vectors, args.sample_seed)
    counts, cluster_risk, _ = accumulate_cluster_residuals(
        base=base,
        centroids=centroids,
        cluster_ids=cluster_ids,
        sample_indices=sample_indices,
        chunk_size=args.chunk_size,
        risk_stat=args.risk_stat,
    )

    padded_dim = int(math.ceil(dim / K_DIM_PADDING_SIZE) * K_DIM_PADDING_SIZE)
    if padded_dim != dim:
        padded = np.zeros((cluster_risk.shape[0], padded_dim), dtype=np.float64)
        padded[:, :dim] = cluster_risk
        cluster_risk = padded

    if paths.global_vars and paths.global_vars.exists():
        global_vars = pad_variance(read_vector_file(paths.global_vars))
    else:
        global_weights = counts.astype(np.float64)
        if float(global_weights.sum()) <= 0.0:
            raise ValueError("cannot infer global variance without sampled vectors")
        global_vars = np.average(cluster_risk, axis=0, weights=global_weights)
    if global_vars.size != padded_dim:
        raise ValueError(f"global variance dim {global_vars.size} does not match padded dim {padded_dim}")

    nblocks = padded_dim // K_DIM_PADDING_SIZE
    cluster_block_sums = cluster_risk.reshape(cluster_risk.shape[0], nblocks, K_DIM_PADDING_SIZE).sum(axis=2)
    global_block_sums = global_vars.reshape(nblocks, K_DIM_PADDING_SIZE).sum(axis=1)

    global_plan, global_dp_cost, total_bits = dp_plan_from_block_sums(global_block_sums, args.avg_bits)
    active_mask = counts >= args.min_cluster_size
    active_indices = np.flatnonzero(active_mask)
    if active_indices.size == 0:
        raise ValueError("no active clusters after --min-cluster-size filtering")

    global_costs = np.array([plan_cost(cluster_block_sums[c], global_plan) for c in range(counts.size)])
    local_costs = np.full(counts.size, np.nan, dtype=np.float64)
    local_plans: list[Plan | None] = [None] * counts.size
    for cid in active_indices:
        plan, cost, _ = dp_plan_from_block_sums(cluster_block_sums[cid], args.avg_bits)
        local_plans[cid] = plan
        local_costs[cid] = cost

    weights = counts.astype(np.float64)
    active_weights = weights[active_indices]
    global_weighted_cost = float(np.sum(global_costs[active_indices] * active_weights))
    local_weighted_cost = float(np.sum(local_costs[active_indices] * active_weights))
    local_ratios = local_costs[active_indices] / np.maximum(global_costs[active_indices], args.eps)

    profile_totals = cluster_block_sums[active_indices].sum(axis=1)
    safe_profile_totals = np.maximum(profile_totals, args.eps)
    features = cluster_block_sums[active_indices] / safe_profile_totals[:, None]

    plan_rows: list[dict[str, Any]] = [
        {
            "role": "global",
            "M": "",
            "group_id": "",
            "plan": compact_plan(global_plan),
            "used_bits": plan_used_bits(global_plan),
            "total_bits": total_bits,
            "assigned_clusters": int(active_indices.size),
            "assigned_vectors": int(active_weights.sum()),
            "weighted_cost": global_weighted_cost,
            "assigned_cost_ratio_vs_global": 1.0,
            "best_cost_ratio_vs_global": 1.0,
            "active_groups": "",
        },
        {
            "role": "local_oracle_summary",
            "M": "local",
            "group_id": "",
            "plan": "",
            "used_bits": "",
            "total_bits": total_bits,
            "assigned_clusters": int(active_indices.size),
            "assigned_vectors": int(active_weights.sum()),
            "weighted_cost": local_weighted_cost,
            "assigned_cost_ratio_vs_global": local_weighted_cost / max(global_weighted_cost, args.eps),
            "best_cost_ratio_vs_global": local_weighted_cost / max(global_weighted_cost, args.eps),
            "active_groups": "",
        },
    ]

    shared_results: list[dict[str, Any]] = []
    shared_counts = [int(x) for x in args.shared_plan_counts.split(",") if x.strip()]
    for m in shared_counts:
        if m <= 0 or m > active_indices.size:
            continue
        labels = weighted_kmeans(features, active_weights, m, args.sample_seed, args.kmeans_iters)
        group_plans: list[Plan] = []
        group_costs = np.zeros((active_indices.size, m), dtype=np.float64)
        active_groups = 0
        for gid in range(m):
            member_mask = labels == gid
            if not np.any(member_mask):
                group_plans.append(tuple())
                group_costs[:, gid] = np.inf
                continue
            active_groups += 1
            member_indices = active_indices[member_mask]
            member_weights = weights[member_indices]
            group_var = np.average(cluster_risk[member_indices], axis=0, weights=member_weights)
            group_block_sums = group_var.reshape(nblocks, K_DIM_PADDING_SIZE).sum(axis=1)
            plan, _, _ = dp_plan_from_block_sums(group_block_sums, args.avg_bits)
            group_plans.append(plan)
            for pos, cid in enumerate(active_indices):
                group_costs[pos, gid] = plan_cost(cluster_block_sums[cid], plan)

            assigned_mask = labels == gid
            assigned_cluster_ids = active_indices[assigned_mask]
            assigned_w = weights[assigned_cluster_ids]
            assigned_cost = float(
                np.sum(group_costs[assigned_mask, gid] * assigned_w)
            )
            plan_rows.append(
                {
                    "role": "shared_plan",
                    "M": m,
                    "group_id": gid,
                    "plan": compact_plan(plan),
                    "used_bits": plan_used_bits(plan),
                    "total_bits": total_bits,
                    "assigned_clusters": int(assigned_cluster_ids.size),
                    "assigned_vectors": int(assigned_w.sum()),
                    "weighted_cost": assigned_cost,
                    "assigned_cost_ratio_vs_global": assigned_cost / max(global_weighted_cost, args.eps),
                    "best_cost_ratio_vs_global": "",
                    "active_groups": "",
                }
            )

        assigned_cost = 0.0
        for gid in range(m):
            mask = labels == gid
            assigned_cost += float(np.sum(group_costs[mask, gid] * active_weights[mask]))
        best_costs = np.min(group_costs, axis=1)
        best_labels = np.argmin(group_costs, axis=1)
        best_weighted_cost = float(np.sum(best_costs * active_weights))
        shared_results.append(
            {
                "M": m,
                "active_groups": active_groups,
                "assigned_weighted_cost": assigned_cost,
                "assigned_cost_ratio_vs_global": assigned_cost / max(global_weighted_cost, args.eps),
                "best_weighted_cost": best_weighted_cost,
                "best_cost_ratio_vs_global": best_weighted_cost / max(global_weighted_cost, args.eps),
                "group_plans": [compact_plan(plan) for plan in group_plans if plan],
            }
        )
        plan_rows.append(
            {
                "role": "shared_family_summary",
                "M": m,
                "group_id": "",
                "plan": "",
                "used_bits": "",
                "total_bits": total_bits,
                "assigned_clusters": int(active_indices.size),
                "assigned_vectors": int(active_weights.sum()),
                "weighted_cost": assigned_cost,
                "assigned_cost_ratio_vs_global": assigned_cost / max(global_weighted_cost, args.eps),
                "best_cost_ratio_vs_global": best_weighted_cost / max(global_weighted_cost, args.eps),
                "active_groups": active_groups,
            }
        )

        if m == shared_counts[0]:
            first_shared_best_labels = np.full(counts.size, -1, dtype=np.int64)
            first_shared_best_ratios = np.full(counts.size, np.nan, dtype=np.float64)
            first_shared_best_labels[active_indices] = best_labels
            first_shared_best_ratios[active_indices] = best_costs / np.maximum(
                global_costs[active_indices], args.eps
            )

    cluster_rows: list[dict[str, Any]] = []
    first_shared_best_labels = locals().get("first_shared_best_labels", np.full(counts.size, -1, dtype=np.int64))
    first_shared_best_ratios = locals().get("first_shared_best_ratios", np.full(counts.size, np.nan, dtype=np.float64))
    for cid in range(counts.size):
        local_plan = local_plans[cid]
        cluster_rows.append(
            {
                "cluster_id": cid,
                "sample_count": int(counts[cid]),
                "active": bool(active_mask[cid]),
                "residual_risk_sum": float(cluster_risk[cid].sum()),
                "global_cost": float(global_costs[cid]),
                "local_oracle_cost": "" if not active_mask[cid] else float(local_costs[cid]),
                "local_oracle_ratio_vs_global": ""
                if not active_mask[cid]
                else float(local_costs[cid] / max(global_costs[cid], args.eps)),
                "local_oracle_plan": "" if local_plan is None else compact_plan(local_plan),
                "first_shared_best_group": int(first_shared_best_labels[cid]),
                "first_shared_best_ratio_vs_global": ""
                if not np.isfinite(first_shared_best_ratios[cid])
                else float(first_shared_best_ratios[cid]),
            }
        )

    output_prefix = Path(args.output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    cluster_csv = output_prefix.with_suffix(".clusters.csv")
    plans_csv = output_prefix.with_suffix(".plans.csv")
    summary_json = output_prefix.with_suffix(".summary.json")
    summary_md = output_prefix.with_suffix(".md")

    summary = {
        "dataset": args.dataset,
        "avg_bits": args.avg_bits,
        "risk_stat": args.risk_stat,
        "num_vectors": int(num_vectors),
        "sampled_vectors": int(sample_indices.size),
        "num_clusters": int(centroids.shape[0]),
        "active_clusters": int(active_indices.size),
        "dim": int(dim),
        "padded_dim": int(padded_dim),
        "total_bits": int(total_bits),
        "paths": {
            "base": str(paths.base),
            "centroids": str(paths.centroids),
            "cluster_ids": str(paths.cluster_ids),
            "global_vars": str(paths.global_vars) if paths.global_vars else None,
        },
        "global_plan": compact_plan(global_plan),
        "global_dp_cost": float(global_dp_cost),
        "global_weighted_cluster_cost": global_weighted_cost,
        "local_oracle": {
            "weighted_cost": local_weighted_cost,
            "weighted_cost_ratio": local_weighted_cost / max(global_weighted_cost, args.eps),
            "ratio_summary": summarize_ratios(local_ratios, active_weights),
        },
        "shared_families": shared_results,
    }

    write_csv(cluster_csv, cluster_rows, list(cluster_rows[0].keys()))
    write_csv(plans_csv, plan_rows, list(plan_rows[0].keys()))
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(summary_md, summary, plan_rows)

    print(f"Wrote {summary_md}")
    print(f"Wrote {summary_json}")
    print(f"Wrote {plans_csv}")
    print(f"Wrote {cluster_csv}")
    print(
        "local_oracle_weighted_cost_ratio="
        f"{summary['local_oracle']['weighted_cost_ratio']:.6g}"
    )
    for result in shared_results:
        print(
            f"M={result['M']} assigned_ratio={result['assigned_cost_ratio_vs_global']:.6g} "
            f"best_ratio={result['best_cost_ratio_vs_global']:.6g}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate cluster residual local/shared SAQ plan feasibility without building an index."
    )
    parser.add_argument("--data-dir", help="Dataset artifact directory.")
    parser.add_argument("--dataset", help="Dataset name used for SAQ artifact naming.")
    parser.add_argument("--k", type=int, help="IVF cluster count used for inferred artifact names.")
    parser.add_argument("--base", help="Explicit base vectors path, usually *_base_pca.fvecs.")
    parser.add_argument("--centroids", help="Explicit centroid path, usually *_centroid_K_pca.fvecs.")
    parser.add_argument("--cluster-ids", help="Explicit cluster id path, usually *_cluster_id_K.ivecs.")
    parser.add_argument("--global-vars", help="Optional global variance path, usually *_base_pca.vars.fvecs.")
    parser.add_argument("--pca", action=argparse.BooleanOptionalAction, default=True, help="Infer PCA artifact names.")
    parser.add_argument("--avg-bits", type=float, required=True, help="SAQ average bit budget B.")
    parser.add_argument("--max-vectors", type=int, default=100000, help="Sample this many base vectors; 0 means all.")
    parser.add_argument("--sample-seed", type=int, default=0, help="Deterministic sampling seed.")
    parser.add_argument("--chunk-size", type=int, default=8192, help="Rows processed per residual accumulation chunk.")
    parser.add_argument("--min-cluster-size", type=int, default=2, help="Minimum sampled vectors for active clusters.")
    parser.add_argument("--shared-plan-counts", default="2,4,8", help="Comma-separated shared plan family sizes.")
    parser.add_argument("--kmeans-iters", type=int, default=30, help="Weighted k-means iterations for profile groups.")
    parser.add_argument(
        "--risk-stat",
        choices=["variance", "second_moment"],
        default="variance",
        help="Residual statistic used as the DP risk vector.",
    )
    parser.add_argument("--eps", type=float, default=1e-12, help="Numerical floor for ratios.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for .md/.json/.csv artifacts.")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
