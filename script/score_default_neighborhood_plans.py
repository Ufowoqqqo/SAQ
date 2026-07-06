#!/usr/bin/env python3
"""Score default-neighborhood SAQ candidates with v3 data-boundary proxies.

This driver evaluates a fixed candidate list instead of generating new DP plans.
It keeps the same query-unaware scoring terms as sweep_data_boundary_pairs.py:
residual/global/tail/pair boundary cost, data-boundary inversion proxies, a
plan-shape speed proxy, and the conservative role-selection guard.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from generate_default_neighborhood_plans import parse_plan_spec
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
from sweep_data_boundary_pairs import (
    DEFAULT_INVERSION_PENALTY_SCALES,
    DEFAULT_PAIR_ALPHAS,
    DEFAULT_RUNTIME_PENALTY_SCALES,
    DEFAULT_SPEED_PROXY_SCALES,
    DEFAULT_TAIL_ALPHAS,
    DEFAULT_WEIGHTED_RATIO_PENALTY_SCALES,
    annotate_conservative_roles,
    evaluate_pair_inversion_proxy,
    evaluate_speed_proxy,
    normalize_cids,
    pair_risk_vector,
    pair_weights,
    pareto_frontier,
    role_shortlist,
    sample_boundary_pairs,
    write_boundary_pairs,
)


Plan = list[dict[str, int]]


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


def read_candidate_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"candidate CSV is empty: {path}")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        plan = parse_plan_spec(row["seg_plan"])
        sig = compact_seg_plan(plan)
        if sig in seen:
            continue
        seen.add(sig)
        item = dict(row)
        item["plan_obj"] = plan
        item["seg_plan"] = sig
        out.append(item)
    return out


def bool_from_csv(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def infer_default_plan_from_candidates(candidates: list[dict[str, Any]]) -> Plan | None:
    defaults = [row["plan_obj"] for row in candidates if bool_from_csv(row.get("is_default", ""))]
    if len(defaults) > 1:
        sigs = {compact_seg_plan(plan) for plan in defaults}
        if len(sigs) > 1:
            raise ValueError(f"candidate CSV has multiple distinct defaults: {sorted(sigs)}")
    return defaults[0] if defaults else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score fixed default-neighborhood SAQ candidates with v3 data-boundary proxies."
    )
    parser.add_argument("--candidate-csv", type=Path, required=True, help="Candidate CSV from generate_default_neighborhood_plans.py.")
    parser.add_argument("--data-dir", type=Path, required=True, help="SAQ dataset artifact directory.")
    parser.add_argument("--dataset", required=True, help="Dataset artifact prefix.")
    parser.add_argument("--k", type=int, required=True, help="Number of IVF clusters.")
    parser.add_argument("--avg-bits", type=float, default=None, help="Average bit budget B. Inferred from plan CSV if omitted.")
    parser.add_argument("--default-plan", default="", help="Optional compact default plan override.")
    parser.add_argument("--default-plan-csv", type=Path, default=None, help="Optional extracted SAQ default plan CSV.")
    parser.add_argument("--plan-id", type=int, default=0, help="Plan id to read from --default-plan-csv.")
    parser.add_argument(
        "--residual-risk-stat",
        choices=("pooled_centered_var", "pooled_second_moment"),
        default="pooled_centered_var",
        help="Residual risk vector used by residual-aware scoring.",
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
    parser.add_argument("--weighted-ratio-penalty-scales", default=DEFAULT_WEIGHTED_RATIO_PENALTY_SCALES, help="Comma-separated penalty scale grid for weighted pair-ratio risk.")
    parser.add_argument("--runtime-penalty-scales", default=DEFAULT_RUNTIME_PENALTY_SCALES, help="Legacy comma-separated nonzero-segment penalty scale grid.")
    parser.add_argument("--speed-proxy-scales", default=DEFAULT_SPEED_PROXY_SCALES, help="Comma-separated plan-shape speed proxy scale grid.")
    parser.add_argument("--speed-nonzero-segment-weight", type=float, default=0.55, help="Speed proxy weight for positive-bit segment count.")
    parser.add_argument("--speed-segment-weight", type=float, default=0.10, help="Speed proxy weight for total segment count.")
    parser.add_argument("--speed-nonzero-dim-weight", type=float, default=0.25, help="Speed proxy weight for nonzero-dimensional coverage.")
    parser.add_argument("--speed-bitwork-weight", type=float, default=0.10, help="Speed proxy weight for dim*bit payload relative to budget.")
    parser.add_argument("--speed-zero-tail-reward", type=float, default=0.0, help="Speed proxy reward for a wider final zero-bit tail.")
    parser.add_argument("--conservative-role-soft-inversion-max", type=float, default=1.0, help="Conservative role guard: max weighted soft-inversion ratio vs default; <=0 disables.")
    parser.add_argument("--conservative-role-weighted-ratio-max", type=float, default=1.0, help="Conservative role guard: max weighted pair-ratio mean vs default; <=0 disables.")
    parser.add_argument("--conservative-role-speed-proxy-max", type=float, default=1.0, help="Conservative role guard: max speed-proxy ratio vs default; <=0 disables.")
    parser.add_argument("--conservative-role-max-nonzero-segments", type=int, default=0, help="Conservative role guard: max positive-bit segments; 0 disables.")
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
    candidates = read_candidate_rows(args.candidate_csv)

    avg_bits = args.avg_bits
    default_source = "candidate_csv"
    default_plan = infer_default_plan_from_candidates(candidates)
    if args.default_plan:
        default_plan = parse_plan_spec(args.default_plan)
        default_source = "default_plan_arg"
    elif args.default_plan_csv is not None:
        default_plan = normalize_plan(load_plan(args.default_plan_csv, args.plan_id))
        default_source = "default_plan_csv"
        if avg_bits is None:
            avg_bits = infer_avg_bits(args.default_plan_csv)
    if default_plan is None:
        raise ValueError("no default plan found; provide --default-plan or include is_default=True in --candidate-csv")
    if avg_bits is None:
        raise ValueError("--avg-bits is required when it cannot be inferred from --default-plan-csv")

    global_blends = parse_float_list(args.boundary_global_blends)
    tail_alphas = parse_float_list(args.boundary_tail_alphas)
    pair_alphas = parse_float_list(args.boundary_pair_alphas)
    segment_penalty_scales = parse_float_list(args.segment_penalty_scales)
    intra_segment_penalty_scales = parse_float_list(args.intra_segment_penalty_scales)
    inversion_penalty_scales = parse_float_list(args.inversion_penalty_scales)
    weighted_ratio_penalty_scales = parse_float_list(args.weighted_ratio_penalty_scales)
    runtime_penalty_scales = parse_float_list(args.runtime_penalty_scales)
    speed_proxy_scales = parse_float_list(args.speed_proxy_scales)

    base = read_fvecs(args.data_dir / f"{args.dataset}_base_pca.fvecs")
    centroids = read_fvecs(args.data_dir / f"{args.dataset}_centroid_{args.k}_pca.fvecs")
    cids = normalize_cids(read_ivecs(args.data_dir / f"{args.dataset}_cluster_id_{args.k}.ivecs"))
    global_var = read_fvecs(args.data_dir / f"{args.dataset}_base_pca.vars.fvecs").reshape(-1)
    if base.shape[0] != cids.size:
        raise ValueError(f"base rows {base.shape[0]} != cluster ids {cids.size}")

    padded_dim = rd_up_to_multiple(base.shape[1], K_DIM_PADDING_SIZE)
    for row in candidates:
        dim = sum(int(seg["dim_len"]) for seg in row["plan_obj"])
        if dim != padded_dim:
            raise ValueError(f"candidate {row['seg_plan']} has dimension {dim}, expected padded dim {padded_dim}")

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

    default_pair_metrics = evaluate_pair_inversion_proxy(
        default_plan,
        pair_block_energy,
        margins,
        weights,
        args.inversion_margin_scale,
        K_DIM_PADDING_SIZE,
    )
    default_soft_penalty = float(default_pair_metrics["pair_proxy_weighted_soft_inversion_penalty"])
    default_weighted_ratio = float(default_pair_metrics["pair_proxy_weighted_ratio_mean"])
    default_speed_metrics = evaluate_speed_proxy(
        default_plan,
        padded_dim,
        avg_bits,
        args.speed_nonzero_segment_weight,
        args.speed_segment_weight,
        args.speed_nonzero_dim_weight,
        args.speed_bitwork_weight,
        args.speed_zero_tail_reward,
    )
    default_speed_proxy_raw = float(default_speed_metrics["speed_proxy_raw"])

    reference_metrics = {
        "default_saq": default_pair_metrics,
        "global_dp_reimpl": evaluate_pair_inversion_proxy(
            global_plan,
            pair_block_energy,
            margins,
            weights,
            args.inversion_margin_scale,
            K_DIM_PADDING_SIZE,
        ),
        "residual_dp": evaluate_pair_inversion_proxy(
            residual_plan,
            pair_block_energy,
            margins,
            weights,
            args.inversion_margin_scale,
            K_DIM_PADDING_SIZE,
        ),
    }

    rows: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    risk_cache: dict[tuple[float, float, float], tuple[np.ndarray, dict[str, Any]]] = {}
    config_id = 0
    total_configs = (
        len(candidates)
        * len(global_blends)
        * len(tail_alphas)
        * len(pair_alphas)
        * len(segment_penalty_scales)
        * len(intra_segment_penalty_scales)
        * len(inversion_penalty_scales)
        * len(weighted_ratio_penalty_scales)
        * len(runtime_penalty_scales)
        * len(speed_proxy_scales)
    )

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
                        default_cost = plan_cost(default_plan, boundary_vector, segment_penalty, intra_scale)
                        global_cost = plan_cost(global_plan, boundary_vector, segment_penalty, intra_scale)
                        residual_cost = plan_cost(residual_plan, boundary_vector, segment_penalty, intra_scale)
                        for candidate in candidates:
                            plan = candidate["plan_obj"]
                            sig = compact_seg_plan(plan)
                            candidate_cost = plan_cost(plan, boundary_vector, segment_penalty, intra_scale)
                            reduction = 1.0 - candidate_cost / default_cost if default_cost > 0 else 0.0
                            metrics = plan_metrics(plan)
                            infeasible_reasons = plan_feasibility_reasons(metrics, args)
                            used_bits = plan_used_bits(plan, num_bit_factors)
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
                            speed_metrics = evaluate_speed_proxy(
                                plan,
                                padded_dim,
                                avg_bits,
                                args.speed_nonzero_segment_weight,
                                args.speed_segment_weight,
                                args.speed_nonzero_dim_weight,
                                args.speed_bitwork_weight,
                                args.speed_zero_tail_reward,
                            )
                            speed_proxy_raw = float(speed_metrics["speed_proxy_raw"])
                            speed_proxy_ratio = (
                                speed_proxy_raw / default_speed_proxy_raw if default_speed_proxy_raw > 0 else 1.0
                            )
                            speed_proxy_score = speed_proxy_ratio - 1.0
                            boundary_cost_ratio = candidate_cost / default_cost if default_cost > 0 else candidate_cost
                            for inversion_penalty_scale in inversion_penalty_scales:
                                for weighted_ratio_penalty_scale in weighted_ratio_penalty_scales:
                                    for runtime_penalty_scale in runtime_penalty_scales:
                                        for speed_proxy_scale in speed_proxy_scales:
                                            soft_inversion_penalty = inversion_penalty_scale * (
                                                soft_penalty_ratio - 1.0
                                            )
                                            weighted_ratio_penalty = weighted_ratio_penalty_scale * (
                                                weighted_ratio_ratio - 1.0
                                            )
                                            recall_risk_score = (
                                                boundary_cost_ratio
                                                + soft_inversion_penalty
                                                + weighted_ratio_penalty
                                            )
                                            runtime_penalty = runtime_penalty_scale * float(
                                                metrics["nonzero_segment_count"]
                                            )
                                            speed_penalty = speed_proxy_scale * speed_proxy_score
                                            ranking_score = recall_risk_score + runtime_penalty + speed_penalty
                                            row = {
                                                "config_id": config_id,
                                                "candidate_rank": candidate.get("candidate_rank", ""),
                                                "candidate_families": candidate.get("families", ""),
                                                "candidate_rationales": candidate.get("rationales", ""),
                                                "candidate_is_default": bool_from_csv(candidate.get("is_default", "")),
                                                "boundary_global_blend": float(global_blend),
                                                "boundary_tail_alpha": float(tail_alpha),
                                                "boundary_pair_alpha": float(pair_alpha),
                                                "segment_penalty_scale": float(segment_penalty_scale),
                                                "segment_penalty": float(segment_penalty),
                                                "intra_segment_penalty_scale": float(intra_scale),
                                                "inversion_penalty_scale": float(inversion_penalty_scale),
                                                "weighted_ratio_penalty_scale": float(weighted_ratio_penalty_scale),
                                                "runtime_penalty_scale": float(runtime_penalty_scale),
                                                "speed_proxy_scale": float(speed_proxy_scale),
                                                "ranking_score": float(ranking_score),
                                                "recall_risk_score": float(recall_risk_score),
                                                "boundary_cost_ratio_term": float(boundary_cost_ratio),
                                                "soft_inversion_penalty_term": float(soft_inversion_penalty),
                                                "weighted_ratio_penalty_term": float(weighted_ratio_penalty),
                                                "runtime_penalty": float(runtime_penalty),
                                                "legacy_runtime_penalty": float(runtime_penalty),
                                                "speed_penalty": float(speed_penalty),
                                                "speed_proxy_score": float(speed_proxy_score),
                                                "speed_proxy_ratio_vs_default": float(speed_proxy_ratio),
                                                "seg_plan": sig,
                                                "plan": format_plan(plan),
                                                "used_bits_including_nonzero_segment_overhead": int(used_bits),
                                                "effective_avg_bits_including_overhead": float(used_bits / padded_dim),
                                                "boundary_cost": float(candidate_cost),
                                                "default_boundary_cost": float(default_cost),
                                                "global_boundary_cost": float(global_cost),
                                                "residual_boundary_cost": float(residual_cost),
                                                "boundary_cost_reduction_vs_default": float(reduction),
                                                "boundary_cost_ratio_vs_default": float(boundary_cost_ratio),
                                                "boundary_sum": boundary_sum,
                                                "global_norm_sum": float(boundary_meta["global_norm_sum"]),
                                                "residual_sum": float(boundary_meta["residual_sum"]),
                                                "tail_norm_sum": float(boundary_meta["tail_norm_sum"]),
                                                "pair_norm_sum": float(boundary_meta["pair_norm_sum"]),
                                                **metrics,
                                                **pair_metrics,
                                                **speed_metrics,
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
        best_recall = min(group_rows, key=lambda row: row["recall_risk_score"])
        best_speed = min(group_rows, key=lambda row: row["speed_proxy_score"])
        best_reduction = max(group_rows, key=lambda row: row["boundary_cost_reduction_vs_default"])
        unique_rows.append(
            {
                "plan_rank": plan_id,
                "plan_id": plan_id,
                "seg_plan": seg_plan,
                "plan": best["plan"],
                "candidate_rank": best["candidate_rank"],
                "candidate_families": best["candidate_families"],
                "candidate_rationales": best["candidate_rationales"],
                "candidate_is_default": best["candidate_is_default"],
                "config_count": len(group_rows),
                "best_config_id_by_score": best["config_id"],
                "best_ranking_score": best["ranking_score"],
                "best_config_id_by_recall_risk": best_recall["config_id"],
                "best_recall_risk_score": best_recall["recall_risk_score"],
                "best_config_id_by_speed_proxy": best_speed["config_id"],
                "best_speed_proxy_score": best_speed["speed_proxy_score"],
                "best_speed_proxy_ratio_vs_default": best_speed["speed_proxy_ratio_vs_default"],
                "best_speed_proxy_raw": best_speed["speed_proxy_raw"],
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
                "speed_proxy_nonzero_segment_count": best["speed_proxy_nonzero_segment_count"],
                "speed_proxy_segment_count": best["speed_proxy_segment_count"],
                "speed_proxy_nonzero_dim_len": best["speed_proxy_nonzero_dim_len"],
                "speed_proxy_zero_tail_dim_len": best["speed_proxy_zero_tail_dim_len"],
                "speed_proxy_bit_dim_sum": best["speed_proxy_bit_dim_sum"],
                "speed_proxy_bitwork_ratio_to_budget": best["speed_proxy_bitwork_ratio_to_budget"],
                "global_blends": ";".join(sorted({float_label(row["boundary_global_blend"]) for row in group_rows})),
                "tail_alphas": ";".join(sorted({float_label(row["boundary_tail_alpha"]) for row in group_rows})),
                "pair_alphas": ";".join(sorted({float_label(row["boundary_pair_alpha"]) for row in group_rows})),
                "segment_penalty_scales": ";".join(sorted({float_label(row["segment_penalty_scale"]) for row in group_rows})),
                "intra_segment_penalty_scales": ";".join(sorted({float_label(row["intra_segment_penalty_scale"]) for row in group_rows})),
                "inversion_penalty_scales": ";".join(sorted({float_label(row["inversion_penalty_scale"]) for row in group_rows})),
                "weighted_ratio_penalty_scales": ";".join(sorted({float_label(row["weighted_ratio_penalty_scale"]) for row in group_rows})),
                "runtime_penalty_scales": ";".join(sorted({float_label(row["runtime_penalty_scale"]) for row in group_rows})),
                "speed_proxy_scales": ";".join(sorted({float_label(row["speed_proxy_scale"]) for row in group_rows})),
            }
        )
    unique_rows.sort(key=lambda row: (row["best_ranking_score"], -row["config_count"], row["seg_plan"]))
    for idx, row in enumerate(unique_rows):
        row["plan_rank"] = idx
    annotate_conservative_roles(unique_rows, args)
    pareto_rows = pareto_frontier(
        unique_rows,
        recall_field="best_recall_risk_score",
        speed_field="best_speed_proxy_ratio_vs_default",
    )
    roles_rows = role_shortlist(unique_rows, args)

    output_csv = args.output_prefix.with_suffix(".csv")
    unique_csv = args.output_prefix.with_suffix(".unique.csv")
    pareto_csv = args.output_prefix.with_suffix(".pareto.csv")
    roles_csv = args.output_prefix.with_suffix(".roles.csv")
    pairs_csv = args.output_prefix.with_suffix(".pairs.csv")
    risk_csv = args.output_prefix.with_suffix(".risk.csv")
    summary_json = args.output_prefix.with_suffix(".summary.json")

    row_fields = [
        "config_id",
        "candidate_rank",
        "candidate_families",
        "candidate_rationales",
        "candidate_is_default",
        "boundary_global_blend",
        "boundary_tail_alpha",
        "boundary_pair_alpha",
        "segment_penalty_scale",
        "segment_penalty",
        "intra_segment_penalty_scale",
        "inversion_penalty_scale",
        "weighted_ratio_penalty_scale",
        "runtime_penalty_scale",
        "speed_proxy_scale",
        "ranking_score",
        "recall_risk_score",
        "boundary_cost_ratio_term",
        "soft_inversion_penalty_term",
        "weighted_ratio_penalty_term",
        "runtime_penalty",
        "legacy_runtime_penalty",
        "speed_penalty",
        "speed_proxy_score",
        "speed_proxy_ratio_vs_default",
        "seg_plan",
        "plan",
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
        "speed_proxy_raw",
        "speed_proxy_nonzero_segment_count",
        "speed_proxy_segment_count",
        "speed_proxy_nonzero_dim_len",
        "speed_proxy_zero_tail_dim_len",
        "speed_proxy_nonzero_dim_fraction",
        "speed_proxy_zero_tail_fraction",
        "speed_proxy_bit_dim_sum",
        "speed_proxy_bitwork_ratio_to_budget",
        "is_feasible",
        "infeasible_reasons",
    ]
    unique_fields = [
        "plan_rank",
        "plan_id",
        "seg_plan",
        "plan",
        "candidate_rank",
        "candidate_families",
        "candidate_rationales",
        "candidate_is_default",
        "config_count",
        "best_config_id_by_score",
        "best_ranking_score",
        "best_config_id_by_recall_risk",
        "best_recall_risk_score",
        "best_config_id_by_speed_proxy",
        "best_speed_proxy_score",
        "best_speed_proxy_ratio_vs_default",
        "best_speed_proxy_raw",
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
        "conservative_role_is_eligible",
        "conservative_role_reasons",
        "pair_proxy_weighted_soft_inversion_penalty",
        "pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default",
        "pair_proxy_weighted_hard_inversion_rate",
        "pair_proxy_weighted_ratio_mean",
        "pair_proxy_weighted_ratio_mean_ratio_vs_default",
        "pair_proxy_ratio_p90",
        "speed_proxy_nonzero_segment_count",
        "speed_proxy_segment_count",
        "speed_proxy_nonzero_dim_len",
        "speed_proxy_zero_tail_dim_len",
        "speed_proxy_bit_dim_sum",
        "speed_proxy_bitwork_ratio_to_budget",
        "global_blends",
        "tail_alphas",
        "pair_alphas",
        "segment_penalty_scales",
        "intra_segment_penalty_scales",
        "inversion_penalty_scales",
        "weighted_ratio_penalty_scales",
        "runtime_penalty_scales",
        "speed_proxy_scales",
    ]
    pareto_fields = ["pareto_rank"] + unique_fields
    role_fields = ["role", "selection_reason"] + unique_fields
    risk_fields = [
        "block_id",
        "start_dim",
        "end_dim",
        "global_risk_sum",
        "residual_risk_sum",
        "pair_risk_sum",
        "pair_risk_share",
    ]
    pair_total = float(pair_vector.sum())
    risk_rows = []
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
    write_csv(pareto_csv, pareto_rows, pareto_fields)
    write_csv(roles_csv, roles_rows, role_fields)
    write_boundary_pairs(pairs_csv, pair_rows)
    write_csv(risk_csv, risk_rows, risk_fields)

    summary = {
        "dataset": args.dataset,
        "data_dir": str(args.data_dir),
        "candidate_csv": str(args.candidate_csv),
        "k": int(args.k),
        "avg_bits": float(avg_bits),
        "dimension": int(base.shape[1]),
        "padded_dimension": int(padded_dim),
        "candidate_count": len(candidates),
        "grid": {
            "boundary_global_blends": global_blends,
            "boundary_tail_alphas": tail_alphas,
            "boundary_pair_alphas": pair_alphas,
            "segment_penalty_scales": segment_penalty_scales,
            "intra_segment_penalty_scales": intra_segment_penalty_scales,
            "inversion_penalty_scales": inversion_penalty_scales,
            "weighted_ratio_penalty_scales": weighted_ratio_penalty_scales,
            "runtime_penalty_scales": runtime_penalty_scales,
            "speed_proxy_scales": speed_proxy_scales,
            "total_configs": total_configs,
        },
        "scoring": {
            "planner_version": "default_neighborhood_candidate_scoring_v1",
            "inherits_scoring_from": "data_boundary_pairs_v3",
            "recall_risk_score": "boundary_cost_ratio + soft_inversion_penalty + weighted_ratio_penalty",
            "ranking_score": "recall_risk_score + legacy_runtime_penalty + speed_penalty",
            "speed_proxy": "lower is faster; combines nonzero segment count, segment count, nonzero dimensions, and bitwork",
            "speed_proxy_weights": {
                "nonzero_segment_weight": float(args.speed_nonzero_segment_weight),
                "segment_weight": float(args.speed_segment_weight),
                "nonzero_dim_weight": float(args.speed_nonzero_dim_weight),
                "bitwork_weight": float(args.speed_bitwork_weight),
                "zero_tail_reward": float(args.speed_zero_tail_reward),
            },
        },
        "conservative_role_guard": {
            "soft_inversion_max": float(args.conservative_role_soft_inversion_max),
            "weighted_ratio_max": float(args.conservative_role_weighted_ratio_max),
            "speed_proxy_max": float(args.conservative_role_speed_proxy_max),
            "max_nonzero_segments": int(args.conservative_role_max_nonzero_segments),
            "eligible_plan_count": len(
                [row for row in unique_rows if bool(row["conservative_role_is_eligible"])]
            ),
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
        "default_source": default_source,
        "default_plan": compact_seg_plan(default_plan),
        "default_pair_proxy": default_pair_metrics,
        "default_matches_global_dp_reimpl": plan_signature(default_plan) == plan_signature(global_plan),
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
        "pareto_plan_count": len(pareto_rows),
        "top_unique_by_score": unique_rows[:20],
        "pareto_frontier": pareto_rows[:20],
        "role_shortlist": roles_rows,
        "top_configs_by_score": rows[:20],
        "top_all_configs_by_score": all_rows_by_score[:20],
        "outputs": {
            "config_csv": str(output_csv),
            "unique_csv": str(unique_csv),
            "pareto_csv": str(pareto_csv),
            "roles_csv": str(roles_csv),
            "pairs_csv": str(pairs_csv),
            "risk_csv": str(risk_csv),
            "summary_json": str(summary_json),
        },
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "all_configs": len(all_rows),
                "feasible_configs": len(feasible_rows),
                "selected_configs": len(rows),
                "selected_unique_plans": len(unique_rows),
                "sampled_pairs": len(pair_rows),
                "pair_weight_tau": tau,
                "config_csv": str(output_csv),
                "unique_csv": str(unique_csv),
                "pareto_csv": str(pareto_csv),
                "roles_csv": str(roles_csv),
                "pairs_csv": str(pairs_csv),
                "risk_csv": str(risk_csv),
                "summary_json": str(summary_json),
                "role_shortlist": roles_rows,
                "top_unique_by_score": unique_rows[:5],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
