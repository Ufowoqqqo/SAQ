#!/usr/bin/env python3
"""Sweep SAQ plans with data-only boundary-pair inversion proxies.

This driver keeps the follow-up query-unaware: it samples base vectors as
pseudo-queries, forms close positive/negative pairs inside the same IVF cell,
turns those pairs into a per-dimension boundary-risk vector, and ranks DP plans
with an additional pair-level inversion proxy.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
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
    normalize_sum_like,
    padded_vector,
    plan_cost,
    plan_signature,
    plan_used_bits,
    rd_up_to_multiple,
)
from segment_diagnostics import load_plan, read_fvecs, read_ivecs
from sweep_boundary_plan import (
    DEFAULT_GLOBAL_BLENDS,
    DEFAULT_INTRA_SEGMENT_PENALTY_SCALES,
    DEFAULT_SEGMENT_PENALTY_SCALES,
    float_label,
    parse_float_list,
    plan_feasibility_reasons,
    plan_metrics,
    write_csv,
)


DEFAULT_TAIL_ALPHAS = "0,0.25"
DEFAULT_PAIR_ALPHAS = "0,0.5,1,2"
DEFAULT_INVERSION_PENALTY_SCALES = "0,0.02,0.05"
DEFAULT_RUNTIME_PENALTY_SCALES = "0,0.005"


Plan = list[dict[str, int]]


def normalize_cids(cids: np.ndarray) -> np.ndarray:
    if cids.ndim == 2:
        if cids.shape[1] != 1:
            raise ValueError(f"cluster id ivecs must have dimension 1, got {cids.shape[1]}")
        cids = cids[:, 0]
    return cids.astype(np.int64, copy=False).reshape(-1)


def grouped_cluster_rows(cids: np.ndarray, cluster_count: int) -> list[np.ndarray]:
    order = np.argsort(cids, kind="stable")
    sorted_cids = cids[order]
    groups: list[np.ndarray] = []
    start = 0
    for cid in range(cluster_count):
        stop = start
        while stop < sorted_cids.size and int(sorted_cids[stop]) == cid:
            stop += 1
        groups.append(order[start:stop])
        start = stop
    return groups


def block_sums(values: np.ndarray, padded_dim: int, padding_size: int) -> np.ndarray:
    if values.shape[-1] < padded_dim:
        pad_width = padded_dim - values.shape[-1]
        values = np.pad(values, [(0, 0), (0, pad_width)], mode="constant")
    elif values.shape[-1] > padded_dim:
        values = values[:, :padded_dim]
    return values.reshape(values.shape[0], padded_dim // padding_size, padding_size).sum(axis=2)


def write_boundary_pairs(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "pair_id",
        "cluster_id",
        "anchor_id",
        "positive_id",
        "negative_id",
        "positive_rank",
        "negative_rank",
        "positive_dist",
        "negative_dist",
        "margin",
        "weight",
    ]
    write_csv(path, rows, fields)


def sample_boundary_pairs(
    base: np.ndarray,
    cids: np.ndarray,
    cluster_count: int,
    boundary_rank: int,
    neighbor_window: int,
    pairs_per_anchor: int,
    anchors_per_cluster: int,
    max_anchors: int,
    max_pairs: int,
    min_cluster_size: int,
    max_candidates_per_anchor: int,
    seed: int,
    padded_dim: int,
    padding_size: int,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    if boundary_rank <= 0:
        raise ValueError("--boundary-rank must be positive")
    if neighbor_window <= 0:
        raise ValueError("--neighbor-window must be positive")
    if pairs_per_anchor <= 0:
        raise ValueError("--pairs-per-anchor must be positive")
    if anchors_per_cluster <= 0:
        raise ValueError("--anchors-per-cluster must be positive")

    rng = np.random.default_rng(seed)
    groups = grouped_cluster_rows(cids, cluster_count)
    eligible = [
        cid
        for cid, rows in enumerate(groups)
        if rows.size >= max(min_cluster_size, boundary_rank + neighbor_window + 2)
    ]
    rng.shuffle(eligible)

    energy_rows: list[np.ndarray] = []
    block_energy_rows: list[np.ndarray] = []
    pair_rows: list[dict[str, Any]] = []
    used_anchor_count = 0
    skipped_anchor_count = 0

    for cid in eligible:
        if max_anchors > 0 and used_anchor_count >= max_anchors:
            break
        if max_pairs > 0 and len(pair_rows) >= max_pairs:
            break
        cluster_rows = groups[cid]
        anchor_count = min(anchors_per_cluster, cluster_rows.size)
        anchors = rng.choice(cluster_rows, size=anchor_count, replace=False)
        for anchor_id_raw in anchors:
            if max_anchors > 0 and used_anchor_count >= max_anchors:
                break
            if max_pairs > 0 and len(pair_rows) >= max_pairs:
                break
            anchor_id = int(anchor_id_raw)
            candidates = cluster_rows
            if max_candidates_per_anchor > 0 and candidates.size > max_candidates_per_anchor:
                others = candidates[candidates != anchor_id]
                if others.size >= max_candidates_per_anchor - 1:
                    sampled = rng.choice(others, size=max_candidates_per_anchor - 1, replace=False)
                    candidates = np.concatenate([np.asarray([anchor_id], dtype=sampled.dtype), sampled])
                else:
                    candidates = candidates.copy()

            vectors = base[candidates]
            anchor = base[anchor_id].astype(np.float32, copy=False)
            diff = vectors.astype(np.float32, copy=False) - anchor
            dists = np.einsum("ij,ij->i", diff, diff, dtype=np.float64).astype(np.float64, copy=False)
            nonself = candidates != anchor_id
            candidates = candidates[nonself]
            dists = dists[nonself]
            vectors = vectors[nonself]
            if dists.size < boundary_rank + neighbor_window:
                skipped_anchor_count += 1
                continue

            order = np.argsort(dists, kind="stable")
            pos_start = max(0, boundary_rank - neighbor_window)
            pos_stop = min(boundary_rank, order.size)
            neg_start = min(boundary_rank, order.size)
            neg_stop = min(boundary_rank + neighbor_window, order.size)
            if pos_start >= pos_stop or neg_start >= neg_stop:
                skipped_anchor_count += 1
                continue

            pos_order = order[pos_start:pos_stop]
            neg_order = order[neg_start:neg_stop]
            combos: list[tuple[float, int, int]] = []
            for pos_local in pos_order:
                pos_dist = float(dists[pos_local])
                for neg_local in neg_order:
                    margin = float(dists[neg_local] - pos_dist)
                    if margin > 0:
                        combos.append((margin, int(pos_local), int(neg_local)))
            if not combos:
                skipped_anchor_count += 1
                continue
            combos.sort(key=lambda item: item[0])

            used_anchor_count += 1
            for margin, pos_local, neg_local in combos[:pairs_per_anchor]:
                if max_pairs > 0 and len(pair_rows) >= max_pairs:
                    break
                pos_vec = vectors[pos_local].astype(np.float32, copy=False)
                neg_vec = vectors[neg_local].astype(np.float32, copy=False)
                pos_delta = anchor - pos_vec
                neg_delta = anchor - neg_vec
                energy = np.square(pos_delta, dtype=np.float32) + np.square(neg_delta, dtype=np.float32)
                energy_rows.append(energy)
                block_energy_rows.append(
                    block_sums(energy.reshape(1, -1), padded_dim, padding_size).reshape(-1)
                )
                pair_rows.append(
                    {
                        "pair_id": len(pair_rows),
                        "cluster_id": int(cid),
                        "anchor_id": anchor_id,
                        "positive_id": int(candidates[pos_local]),
                        "negative_id": int(candidates[neg_local]),
                        "positive_rank": int(np.where(order == pos_local)[0][0] + 1),
                        "negative_rank": int(np.where(order == neg_local)[0][0] + 1),
                        "positive_dist": float(dists[pos_local]),
                        "negative_dist": float(dists[neg_local]),
                        "margin": float(margin),
                        "weight": 0.0,
                    }
                )

    if not pair_rows:
        raise RuntimeError("no boundary pairs were sampled; relax sampling parameters")

    pair_energy = np.vstack(energy_rows).astype(np.float64, copy=False)
    pair_block_energy = np.vstack(block_energy_rows).astype(np.float64, copy=False)
    margins = np.asarray([float(row["margin"]) for row in pair_rows], dtype=np.float64)
    summary = {
        "cluster_count": int(cluster_count),
        "eligible_cluster_count": int(len(eligible)),
        "used_anchor_count": int(used_anchor_count),
        "skipped_anchor_count": int(skipped_anchor_count),
        "sampled_pair_count": int(len(pair_rows)),
        "boundary_rank": int(boundary_rank),
        "neighbor_window": int(neighbor_window),
        "pairs_per_anchor": int(pairs_per_anchor),
        "anchors_per_cluster": int(anchors_per_cluster),
        "max_anchors": int(max_anchors),
        "max_pairs": int(max_pairs),
        "min_cluster_size": int(min_cluster_size),
        "max_candidates_per_anchor": int(max_candidates_per_anchor),
        "seed": int(seed),
        "margin_min": float(margins.min()),
        "margin_p50": float(np.percentile(margins, 50)),
        "margin_p90": float(np.percentile(margins, 90)),
        "margin_max": float(margins.max()),
    }
    return pair_energy, pair_block_energy, pair_rows, summary


def pair_weights(margins: np.ndarray, tau: float | None) -> tuple[np.ndarray, float]:
    if tau is None or tau <= 0:
        tau = float(np.percentile(margins, 50))
        if tau <= 0:
            tau = float(np.mean(margins[margins > 0])) if np.any(margins > 0) else 1.0
    weights = np.exp(-margins / tau)
    return weights.astype(np.float64, copy=False), float(tau)


def pair_risk_vector(pair_energy: np.ndarray, weights: np.ndarray) -> np.ndarray:
    denom = float(weights.sum())
    if denom <= 0:
        raise ValueError("pair weights sum to zero")
    return (pair_energy * weights[:, None]).sum(axis=0) / denom


def evaluate_pair_inversion_proxy(
    plan: Plan,
    pair_block_energy: np.ndarray,
    margins: np.ndarray,
    weights: np.ndarray,
    margin_scale: float,
    padding_size: int,
) -> dict[str, Any]:
    budgets = np.zeros(pair_block_energy.shape[0], dtype=np.float64)
    for seg in plan:
        start_block = int(seg["start_dim"]) // padding_size
        end_block = int(seg["end_dim"]) // padding_size
        bits = int(seg["bits"])
        denom = float(1 << bits) if bits > 0 else 1.0
        budgets += pair_block_energy[:, start_block:end_block].sum(axis=1) / denom

    eps = np.finfo(np.float64).eps
    ratios = margin_scale * budgets / np.maximum(margins, eps)
    hard = ratios >= 1.0
    weight_sum = float(weights.sum())
    if weight_sum <= 0:
        weighted_hard = 0.0
        weighted_ratio = 0.0
        weighted_soft = 0.0
    else:
        weighted_hard = float(weights[hard].sum() / weight_sum)
        weighted_ratio = float(np.average(ratios, weights=weights))
        weighted_soft = float(np.average(np.maximum(ratios - 1.0, 0.0), weights=weights))
    return {
        "pair_proxy_error_budget_mean": float(budgets.mean()),
        "pair_proxy_error_budget_p90": float(np.percentile(budgets, 90)),
        "pair_proxy_ratio_mean": float(ratios.mean()),
        "pair_proxy_ratio_p50": float(np.percentile(ratios, 50)),
        "pair_proxy_ratio_p90": float(np.percentile(ratios, 90)),
        "pair_proxy_ratio_p99": float(np.percentile(ratios, 99)),
        "pair_proxy_hard_inversion_rate": float(hard.mean()),
        "pair_proxy_weighted_ratio_mean": weighted_ratio,
        "pair_proxy_weighted_hard_inversion_rate": weighted_hard,
        "pair_proxy_weighted_soft_inversion_penalty": weighted_soft,
    }


def make_data_boundary_vector(
    global_vector: np.ndarray,
    residual_vector: np.ndarray,
    tail_vector: np.ndarray | None,
    pair_vector: np.ndarray,
    global_blend: float,
    tail_alpha: float,
    pair_alpha: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    base_boundary, meta = make_boundary_risk_vector(
        global_vector,
        residual_vector,
        tail_vector,
        global_blend,
        tail_alpha,
    )
    pair_norm = normalize_sum_like(pair_vector, residual_vector)
    boundary = base_boundary + pair_alpha * pair_norm
    meta.update(
        {
            "pair_alpha": float(pair_alpha),
            "pair_norm_sum": float(pair_norm.sum()),
            "boundary_sum_with_pair": float(boundary.sum()),
        }
    )
    return boundary.astype(np.float64, copy=False), meta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep query-unaware SAQ plans with data-only boundary pair inversion proxies."
    )
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
    parser.add_argument("--boundary-rank", type=int, default=100, help="Local same-cell rank boundary for base-as-query pairs.")
    parser.add_argument("--neighbor-window", type=int, default=8, help="Ranks below/above boundary used to form pair candidates.")
    parser.add_argument("--pairs-per-anchor", type=int, default=4, help="Keep this many smallest-margin pairs per sampled anchor.")
    parser.add_argument("--anchors-per-cluster", type=int, default=1, help="Sample this many base-as-query anchors per eligible IVF cell.")
    parser.add_argument("--max-anchors", type=int, default=4096, help="Maximum anchors to sample; 0 disables.")
    parser.add_argument("--max-pairs", type=int, default=20000, help="Maximum boundary pairs to keep; 0 disables.")
    parser.add_argument("--max-candidates-per-anchor", type=int, default=2048, help="Subsample cell candidates above this count; 0 disables.")
    parser.add_argument("--pair-seed", type=int, default=0, help="Random seed for data-only pair sampling.")
    parser.add_argument("--pair-weight-tau", type=float, default=0.0, help="Margin temperature for exp(-margin/tau); <=0 uses sampled median margin.")
    parser.add_argument("--inversion-margin-scale", type=float, default=1.0, help="Calibration multiplier for pair proxy error budget / exact margin.")
    parser.add_argument("--boundary-tail-quantile", type=float, default=0.95, help="Quantile used for residual tail-excess risk.")
    parser.add_argument("--boundary-global-blends", default=DEFAULT_GLOBAL_BLENDS, help="Comma-separated global blend grid.")
    parser.add_argument("--boundary-tail-alphas", default=DEFAULT_TAIL_ALPHAS, help="Comma-separated tail alpha grid.")
    parser.add_argument("--boundary-pair-alphas", default=DEFAULT_PAIR_ALPHAS, help="Comma-separated data-boundary pair alpha grid.")
    parser.add_argument("--segment-penalty-scales", default=DEFAULT_SEGMENT_PENALTY_SCALES, help="Comma-separated segment penalty scale grid.")
    parser.add_argument("--intra-segment-penalty-scales", default=DEFAULT_INTRA_SEGMENT_PENALTY_SCALES, help="Comma-separated intra-segment penalty scale grid.")
    parser.add_argument("--inversion-penalty-scales", default=DEFAULT_INVERSION_PENALTY_SCALES, help="Comma-separated plan-level inversion penalty scale grid.")
    parser.add_argument("--runtime-penalty-scales", default=DEFAULT_RUNTIME_PENALTY_SCALES, help="Comma-separated plan-level nonzero-segment penalty scale grid.")
    parser.add_argument("--min-positive-bits", type=int, default=0, help="Guard: require every positive-bit segment to use at least this many bits; 0 disables.")
    parser.add_argument("--min-zero-tail-dim", type=int, default=0, help="Guard: reject nonempty zero-bit tails shorter than this many dimensions; 0 disables.")
    parser.add_argument("--max-segments", type=int, default=0, help="Guard: reject plans with more than this many segments; 0 disables.")
    parser.add_argument("--max-nonzero-segment-dim", type=int, default=0, help="Guard: reject plans whose widest positive-bit segment exceeds this width.")
    parser.add_argument("--exclude-internal-1bit", action="store_true", help="Guard: reject plans with a 1-bit segment that is neither first nor last.")
    parser.add_argument("--exclude-nonfinal-1bit", action="store_true", help="Guard: reject plans with a 1-bit segment before the final segment.")
    parser.add_argument("--filter-infeasible", action="store_true", help="Write only feasible rows/unique plans under enabled guards.")
    parser.add_argument("--chunk-rows", type=int, default=2048, help="Rows per residual accumulation chunk.")
    parser.add_argument("--output-prefix", type=Path, required=True, help="Prefix for .csv, .unique.csv, .pairs.csv, .risk.csv, and .summary.json.")
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
    pair_alphas = parse_float_list(args.boundary_pair_alphas)
    segment_penalty_scales = parse_float_list(args.segment_penalty_scales)
    intra_segment_penalty_scales = parse_float_list(args.intra_segment_penalty_scales)
    inversion_penalty_scales = parse_float_list(args.inversion_penalty_scales)
    runtime_penalty_scales = parse_float_list(args.runtime_penalty_scales)

    base = read_fvecs(args.data_dir / f"{args.dataset}_base_pca.fvecs")
    centroids = read_fvecs(args.data_dir / f"{args.dataset}_centroid_{args.k}_pca.fvecs")
    cids = normalize_cids(read_ivecs(args.data_dir / f"{args.dataset}_cluster_id_{args.k}.ivecs"))
    global_var = read_fvecs(args.data_dir / f"{args.dataset}_base_pca.vars.fvecs").reshape(-1)
    if base.shape[0] != cids.size:
        raise ValueError(f"base rows {base.shape[0]} != cluster ids {cids.size}")

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

    pair_energy, pair_block_energy, pair_rows, pair_summary = sample_boundary_pairs(
        base=base,
        cids=cids,
        cluster_count=centroids.shape[0],
        boundary_rank=args.boundary_rank,
        neighbor_window=args.neighbor_window,
        pairs_per_anchor=args.pairs_per_anchor,
        anchors_per_cluster=args.anchors_per_cluster,
        max_anchors=args.max_anchors,
        max_pairs=args.max_pairs,
        min_cluster_size=args.min_cluster_size,
        max_candidates_per_anchor=args.max_candidates_per_anchor,
        seed=args.pair_seed,
        padded_dim=padded_dim,
        padding_size=K_DIM_PADDING_SIZE,
    )
    margins = np.asarray([float(row["margin"]) for row in pair_rows], dtype=np.float64)
    weights, tau = pair_weights(margins, args.pair_weight_tau)
    for row, weight in zip(pair_rows, weights):
        row["weight"] = float(weight)
    pair_vector_raw = pair_risk_vector(pair_energy, weights)
    pair_vector = padded_vector(pair_vector_raw, padded_dim).astype(np.float64, copy=False)
    pair_summary.update(
        {
            "pair_weight_tau": float(tau),
            "pair_weight_sum": float(weights.sum()),
            "pair_weight_min": float(weights.min()),
            "pair_weight_p50": float(np.percentile(weights, 50)),
            "pair_weight_max": float(weights.max()),
            "pair_risk_sum": float(pair_vector.sum()),
            "pair_risk_top64_share": float(np.sort(pair_vector)[-64:].sum() / pair_vector.sum())
            if pair_vector.sum() > 0
            else 0.0,
        }
    )

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
    default_key_name = "default_saq" if default_plan is not None else "global_dp_reimpl"

    rows: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    config_id = 0
    risk_cache: dict[tuple[float, float, float], tuple[np.ndarray, dict[str, Any]]] = {}
    total_configs = (
        len(global_blends)
        * len(tail_alphas)
        * len(pair_alphas)
        * len(segment_penalty_scales)
        * len(intra_segment_penalty_scales)
        * len(inversion_penalty_scales)
        * len(runtime_penalty_scales)
    )

    reference_plans: list[tuple[str, Plan]] = [
        ("global_dp_reimpl", global_plan),
        ("residual_dp", residual_plan),
    ]
    if default_plan is not None:
        reference_plans.insert(0, ("default_saq", default_plan))
    reference_metrics = {
        name: evaluate_pair_inversion_proxy(
            plan,
            pair_block_energy,
            margins,
            weights,
            args.inversion_margin_scale,
            K_DIM_PADDING_SIZE,
        )
        for name, plan in reference_plans
    }
    default_pair_metrics = evaluate_pair_inversion_proxy(
        default_key_plan,
        pair_block_energy,
        margins,
        weights,
        args.inversion_margin_scale,
        K_DIM_PADDING_SIZE,
    )
    default_soft_penalty = float(default_pair_metrics["pair_proxy_weighted_soft_inversion_penalty"])
    default_weighted_ratio = float(default_pair_metrics["pair_proxy_weighted_ratio_mean"])

    for global_blend in global_blends:
        for tail_alpha in tail_alphas:
            for pair_alpha in pair_alphas:
                cache_key = (global_blend, tail_alpha, pair_alpha)
                if cache_key not in risk_cache:
                    risk_cache[cache_key] = make_data_boundary_vector(
                        global_vector,
                        residual_vector,
                        tail_vector,
                        pair_vector,
                        global_blend,
                        tail_alpha,
                        pair_alpha,
                    )
                boundary_vector, boundary_meta = risk_cache[cache_key]
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
                        pair_metrics = evaluate_pair_inversion_proxy(
                            plan,
                            pair_block_energy,
                            margins,
                            weights,
                            args.inversion_margin_scale,
                            K_DIM_PADDING_SIZE,
                        )
                        soft_penalty = float(pair_metrics["pair_proxy_weighted_soft_inversion_penalty"])
                        weighted_ratio = float(pair_metrics["pair_proxy_weighted_ratio_mean"])
                        soft_penalty_ratio = (
                            soft_penalty / default_soft_penalty if default_soft_penalty > 0 else 0.0
                        )
                        weighted_ratio_ratio = (
                            weighted_ratio / default_weighted_ratio if default_weighted_ratio > 0 else 0.0
                        )
                        for inversion_penalty_scale in inversion_penalty_scales:
                            for runtime_penalty_scale in runtime_penalty_scales:
                                runtime_penalty = runtime_penalty_scale * float(metrics["nonzero_segment_count"])
                                ranking_score = (
                                    (candidate_cost / default_cost if default_cost > 0 else candidate_cost)
                                    + inversion_penalty_scale * (soft_penalty_ratio - 1.0)
                                    + runtime_penalty
                                )
                                row = {
                                    "config_id": config_id,
                                    "boundary_global_blend": float(global_blend),
                                    "boundary_tail_alpha": float(tail_alpha),
                                    "boundary_pair_alpha": float(pair_alpha),
                                    "segment_penalty_scale": float(segment_penalty_scale),
                                    "segment_penalty": float(segment_penalty),
                                    "intra_segment_penalty_scale": float(intra_scale),
                                    "inversion_penalty_scale": float(inversion_penalty_scale),
                                    "runtime_penalty_scale": float(runtime_penalty_scale),
                                    "ranking_score": float(ranking_score),
                                    "runtime_penalty": float(runtime_penalty),
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
                                    "boundary_cost_ratio_vs_default": float(candidate_cost / default_cost)
                                    if default_cost > 0
                                    else 0.0,
                                    "boundary_sum": boundary_sum,
                                    "global_norm_sum": float(boundary_meta["global_norm_sum"]),
                                    "residual_sum": float(boundary_meta["residual_sum"]),
                                    "tail_norm_sum": float(boundary_meta["tail_norm_sum"]),
                                    "pair_norm_sum": float(boundary_meta["pair_norm_sum"]),
                                    **metrics,
                                    **pair_metrics,
                                    "pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default": soft_penalty_ratio,
                                    "pair_proxy_weighted_ratio_mean_ratio_vs_default": weighted_ratio_ratio,
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

    rows.sort(key=lambda row: (row["ranking_score"], -row["boundary_cost_reduction_vs_default"], row["seg_plan"]))
    all_rows_by_score = sorted(
        all_rows,
        key=lambda row: (row["ranking_score"], -row["boundary_cost_reduction_vs_default"], row["seg_plan"]),
    )

    unique_rows: list[dict[str, Any]] = []
    for plan_id, (seg_plan, group_rows) in enumerate(
        sorted(groups.items(), key=lambda item: (min(row["ranking_score"] for row in item[1]), item[0]))
    ):
        best = min(group_rows, key=lambda row: row["ranking_score"])
        best_reduction = max(group_rows, key=lambda row: row["boundary_cost_reduction_vs_default"])
        unique_rows.append(
            {
                "plan_rank": plan_id,
                "plan_id": plan_id,
                "seg_plan": seg_plan,
                "plan": best["plan"],
                "config_count": len(group_rows),
                "best_config_id_by_score": best["config_id"],
                "best_ranking_score": best["ranking_score"],
                "best_config_id_by_reduction": best_reduction["config_id"],
                "best_boundary_cost_reduction_vs_default": best_reduction[
                    "boundary_cost_reduction_vs_default"
                ],
                "best_boundary_cost_ratio_vs_default": best["boundary_cost_ratio_vs_default"],
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
                "is_feasible": best["is_feasible"],
                "infeasible_reasons": best["infeasible_reasons"],
                "pair_proxy_weighted_soft_inversion_penalty": best[
                    "pair_proxy_weighted_soft_inversion_penalty"
                ],
                "pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default": best[
                    "pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default"
                ],
                "pair_proxy_weighted_hard_inversion_rate": best[
                    "pair_proxy_weighted_hard_inversion_rate"
                ],
                "pair_proxy_weighted_ratio_mean": best["pair_proxy_weighted_ratio_mean"],
                "pair_proxy_weighted_ratio_mean_ratio_vs_default": best[
                    "pair_proxy_weighted_ratio_mean_ratio_vs_default"
                ],
                "pair_proxy_ratio_p90": best["pair_proxy_ratio_p90"],
                "global_blends": ";".join(sorted({float_label(row["boundary_global_blend"]) for row in group_rows})),
                "tail_alphas": ";".join(sorted({float_label(row["boundary_tail_alpha"]) for row in group_rows})),
                "pair_alphas": ";".join(sorted({float_label(row["boundary_pair_alpha"]) for row in group_rows})),
                "segment_penalty_scales": ";".join(sorted({float_label(row["segment_penalty_scale"]) for row in group_rows})),
                "intra_segment_penalty_scales": ";".join(sorted({float_label(row["intra_segment_penalty_scale"]) for row in group_rows})),
                "inversion_penalty_scales": ";".join(sorted({float_label(row["inversion_penalty_scale"]) for row in group_rows})),
                "runtime_penalty_scales": ";".join(sorted({float_label(row["runtime_penalty_scale"]) for row in group_rows})),
            }
        )
    unique_rows.sort(key=lambda row: (row["best_ranking_score"], -row["config_count"], row["seg_plan"]))
    for idx, row in enumerate(unique_rows):
        row["plan_rank"] = idx

    output_csv = args.output_prefix.with_suffix(".csv")
    unique_csv = args.output_prefix.with_suffix(".unique.csv")
    pairs_csv = args.output_prefix.with_suffix(".pairs.csv")
    risk_csv = args.output_prefix.with_suffix(".risk.csv")
    summary_json = args.output_prefix.with_suffix(".summary.json")

    row_fields = [
        "config_id",
        "boundary_global_blend",
        "boundary_tail_alpha",
        "boundary_pair_alpha",
        "segment_penalty_scale",
        "segment_penalty",
        "intra_segment_penalty_scale",
        "inversion_penalty_scale",
        "runtime_penalty_scale",
        "ranking_score",
        "runtime_penalty",
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
        "boundary_cost_ratio_vs_default",
        "boundary_sum",
        "global_norm_sum",
        "residual_sum",
        "tail_norm_sum",
        "pair_norm_sum",
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
        "pair_proxy_error_budget_mean",
        "pair_proxy_error_budget_p90",
        "pair_proxy_ratio_mean",
        "pair_proxy_ratio_p50",
        "pair_proxy_ratio_p90",
        "pair_proxy_ratio_p99",
        "pair_proxy_hard_inversion_rate",
        "pair_proxy_weighted_ratio_mean",
        "pair_proxy_weighted_ratio_mean_ratio_vs_default",
        "pair_proxy_weighted_hard_inversion_rate",
        "pair_proxy_weighted_soft_inversion_penalty",
        "pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default",
        "is_feasible",
        "infeasible_reasons",
    ]
    unique_fields = [
        "plan_rank",
        "plan_id",
        "seg_plan",
        "plan",
        "config_count",
        "best_config_id_by_score",
        "best_ranking_score",
        "best_config_id_by_reduction",
        "best_boundary_cost_reduction_vs_default",
        "best_boundary_cost_ratio_vs_default",
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
        "is_feasible",
        "infeasible_reasons",
        "pair_proxy_weighted_soft_inversion_penalty",
        "pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default",
        "pair_proxy_weighted_hard_inversion_rate",
        "pair_proxy_weighted_ratio_mean",
        "pair_proxy_weighted_ratio_mean_ratio_vs_default",
        "pair_proxy_ratio_p90",
        "global_blends",
        "tail_alphas",
        "pair_alphas",
        "segment_penalty_scales",
        "intra_segment_penalty_scales",
        "inversion_penalty_scales",
        "runtime_penalty_scales",
    ]
    risk_fields = [
        "block_id",
        "start_dim",
        "end_dim",
        "global_risk_sum",
        "residual_risk_sum",
        "pair_risk_sum",
        "pair_risk_share",
    ]
    risk_rows = []
    pair_total = float(pair_vector.sum())
    for block_id in range(padded_dim // K_DIM_PADDING_SIZE):
        start = block_id * K_DIM_PADDING_SIZE
        end = start + K_DIM_PADDING_SIZE
        pair_sum = float(pair_vector[start:end].sum())
        risk_rows.append(
            {
                "block_id": block_id,
                "start_dim": start,
                "end_dim": end,
                "global_risk_sum": float(global_vector[start:end].sum()),
                "residual_risk_sum": float(residual_vector[start:end].sum()),
                "pair_risk_sum": pair_sum,
                "pair_risk_share": pair_sum / pair_total if pair_total > 0 else 0.0,
            }
        )

    write_csv(output_csv, rows, row_fields)
    write_csv(unique_csv, unique_rows, unique_fields)
    write_boundary_pairs(pairs_csv, pair_rows)
    write_csv(risk_csv, risk_rows, risk_fields)

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
            "boundary_pair_alphas": pair_alphas,
            "segment_penalty_scales": segment_penalty_scales,
            "intra_segment_penalty_scales": intra_segment_penalty_scales,
            "inversion_penalty_scales": inversion_penalty_scales,
            "runtime_penalty_scales": runtime_penalty_scales,
            "total_configs": total_configs,
        },
        "residual_risk_stat": args.residual_risk_stat,
        "residual_summary": residual_summary,
        "tail_summary": tail_summary,
        "pair_summary": pair_summary,
        "inversion_margin_scale": float(args.inversion_margin_scale),
        "global_dp": {
            "seg_plan": compact_seg_plan(global_plan),
            "plan": format_plan(global_plan),
            "meta": global_dp_meta,
            "pair_proxy": reference_metrics["global_dp_reimpl"],
        },
        "residual_dp": {
            "seg_plan": compact_seg_plan(residual_plan),
            "plan": format_plan(residual_plan),
            "meta": residual_dp_meta,
            "pair_proxy": reference_metrics["residual_dp"],
        },
        "default_key_name": default_key_name,
        "default_pair_proxy": default_pair_metrics,
        "default_plan": compact_seg_plan(default_plan) if default_plan is not None else None,
        "default_matches_global_dp_reimpl": (
            plan_signature(default_plan) == plan_signature(global_plan) if default_plan is not None else None
        ),
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
        "top_unique_by_score": unique_rows[:20],
        "top_configs_by_score": rows[:20],
        "top_all_configs_by_score": all_rows_by_score[:20],
        "outputs": {
            "config_csv": str(output_csv),
            "unique_csv": str(unique_csv),
            "pairs_csv": str(pairs_csv),
            "risk_csv": str(risk_csv),
            "summary_json": str(summary_json),
        },
    }
    if default_plan is not None:
        summary["default_saq"] = {
            "seg_plan": compact_seg_plan(default_plan),
            "plan": format_plan(default_plan),
            "pair_proxy": reference_metrics["default_saq"],
        }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "all_configs": len(all_rows),
                "feasible_configs": len(feasible_rows),
                "selected_configs": len(rows),
                "all_unique_plans": len(all_groups),
                "selected_unique_plans": len(unique_rows),
                "sampled_pairs": len(pair_rows),
                "pair_weight_tau": tau,
                "filter_infeasible": bool(args.filter_infeasible),
                "config_csv": str(output_csv),
                "unique_csv": str(unique_csv),
                "pairs_csv": str(pairs_csv),
                "risk_csv": str(risk_csv),
                "summary_json": str(summary_json),
                "top_unique_by_score": unique_rows[:5],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
