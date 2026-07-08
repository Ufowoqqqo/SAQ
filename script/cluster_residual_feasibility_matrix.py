#!/usr/bin/env python3
"""Cross-bit and cross-dataset cluster-residual feasibility matrix.

This driver keeps Direction 1 offline. It computes residual profiles once per
dataset case, evaluates several SAQ bit budgets, and applies a data-only
shared-plan assignment rule:

    assign cluster c to argmin_P cost(residual_profile_c, P)

No query vectors, ground-truth labels, indexes, or search outputs are used.
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

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[0]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "python"))

import cluster_residual_plan_feasibility as crp  # noqa: E402


@dataclass(frozen=True)
class MatrixCase:
    name: str
    data_dir: Path
    dataset: str
    k: int
    max_vectors: int


@dataclass(frozen=True)
class PreparedCase:
    case: MatrixCase
    paths: crp.StudyPaths
    counts: np.ndarray
    cluster_risk: np.ndarray
    global_vars: np.ndarray
    active_indices: np.ndarray
    weights: np.ndarray
    cluster_block_sums: np.ndarray
    global_block_sums: np.ndarray
    padded_dim: int
    dim: int
    num_vectors: int
    sampled_vectors: int
    num_clusters: int


def parse_case(text: str) -> MatrixCase:
    fields = {}
    for part in text.split(","):
        if not part.strip():
            continue
        key, sep, value = part.partition("=")
        if not sep:
            raise ValueError(f"bad --case field {part!r}; expected key=value")
        fields[key.strip()] = value.strip()

    required = ["name", "data_dir", "dataset", "k"]
    missing = [key for key in required if key not in fields]
    if missing:
        raise ValueError(f"--case missing fields: {', '.join(missing)}")

    return MatrixCase(
        name=fields["name"],
        data_dir=Path(fields["data_dir"]),
        dataset=fields["dataset"],
        k=int(fields["k"]),
        max_vectors=int(fields.get("max_vectors", "100000")),
    )


def split_ints(text: str) -> list[int]:
    values = [int(part.strip()) for part in text.split(",") if part.strip()]
    if not values:
        raise ValueError("expected at least one integer")
    return values


def split_floats(text: str) -> list[float]:
    values = [float(part.strip()) for part in text.split(",") if part.strip()]
    if not values:
        raise ValueError("expected at least one float")
    return values


def infer_paths(case: MatrixCase) -> crp.StudyPaths:
    args = argparse.Namespace(
        base=None,
        centroids=None,
        cluster_ids=None,
        global_vars=None,
        data_dir=str(case.data_dir),
        dataset=case.dataset,
        k=case.k,
        pca=True,
    )
    return crp.infer_paths(args)


def prepare_case(
    case: MatrixCase,
    sample_seed: int,
    chunk_size: int,
    min_cluster_size: int,
    risk_stat: str,
) -> PreparedCase:
    paths = infer_paths(case)
    for required in [paths.base, paths.centroids, paths.cluster_ids]:
        if not required.exists():
            raise FileNotFoundError(required)

    base = crp.mmap_fvecs(paths.base) if paths.base.suffix == ".fvecs" else crp.read_vector_file(paths.base)
    cluster_ids = crp.mmap_ivecs(paths.cluster_ids) if paths.cluster_ids.suffix == ".ivecs" else crp.read_vector_file(paths.cluster_ids)
    centroids = np.asarray(crp.read_vector_file(paths.centroids), dtype=np.float32)

    num_vectors, dim = base.shape
    if centroids.ndim != 2 or centroids.shape[1] != dim:
        raise ValueError(f"centroids shape {centroids.shape} does not match base dim {dim}")
    if cluster_ids.shape[0] != num_vectors:
        raise ValueError(
            f"cluster id rows {cluster_ids.shape[0]} do not match base rows {num_vectors}"
        )

    sample_indices = crp.choose_sample_indices(num_vectors, case.max_vectors, sample_seed)
    counts, cluster_risk, _ = crp.accumulate_cluster_residuals(
        base=base,
        centroids=centroids,
        cluster_ids=cluster_ids,
        sample_indices=sample_indices,
        chunk_size=chunk_size,
        risk_stat=risk_stat,
    )

    padded_dim = int(math.ceil(dim / crp.K_DIM_PADDING_SIZE) * crp.K_DIM_PADDING_SIZE)
    if padded_dim != dim:
        padded = np.zeros((cluster_risk.shape[0], padded_dim), dtype=np.float64)
        padded[:, :dim] = cluster_risk
        cluster_risk = padded

    if paths.global_vars and paths.global_vars.exists():
        global_vars = crp.pad_variance(crp.read_vector_file(paths.global_vars))
    else:
        global_weights = counts.astype(np.float64)
        if float(global_weights.sum()) <= 0.0:
            raise ValueError("cannot infer global variance without sampled vectors")
        global_vars = np.average(cluster_risk, axis=0, weights=global_weights)
    if global_vars.size != padded_dim:
        raise ValueError(f"global variance dim {global_vars.size} does not match padded dim {padded_dim}")

    nblocks = padded_dim // crp.K_DIM_PADDING_SIZE
    cluster_block_sums = cluster_risk.reshape(
        cluster_risk.shape[0], nblocks, crp.K_DIM_PADDING_SIZE
    ).sum(axis=2)
    global_block_sums = global_vars.reshape(nblocks, crp.K_DIM_PADDING_SIZE).sum(axis=1)
    active_indices = np.flatnonzero(counts >= min_cluster_size)
    if active_indices.size == 0:
        raise ValueError(f"{case.name}: no active clusters after min size filtering")

    return PreparedCase(
        case=case,
        paths=paths,
        counts=counts,
        cluster_risk=cluster_risk,
        global_vars=global_vars,
        active_indices=active_indices,
        weights=counts.astype(np.float64),
        cluster_block_sums=cluster_block_sums,
        global_block_sums=global_block_sums,
        padded_dim=padded_dim,
        dim=dim,
        num_vectors=num_vectors,
        sampled_vectors=int(sample_indices.size),
        num_clusters=centroids.shape[0],
    )


def evaluate_bit_budget(
    prepared: PreparedCase,
    avg_bits: float,
    shared_plan_counts: list[int],
    sample_seed: int,
    kmeans_iters: int,
    eps: float,
) -> dict[str, Any]:
    active = prepared.active_indices
    active_weights = prepared.weights[active]
    global_plan, global_dp_cost, total_bits = crp.dp_plan_from_block_sums(
        prepared.global_block_sums, avg_bits
    )
    global_costs = np.array(
        [crp.plan_cost(prepared.cluster_block_sums[c], global_plan) for c in range(prepared.counts.size)]
    )
    global_weighted_cost = float(np.sum(global_costs[active] * active_weights))

    local_costs = np.full(prepared.counts.size, np.nan, dtype=np.float64)
    local_plan_strings: list[str] = []
    for cid in active:
        plan, cost, _ = crp.dp_plan_from_block_sums(prepared.cluster_block_sums[cid], avg_bits)
        local_costs[cid] = cost
        local_plan_strings.append(crp.compact_plan(plan))
    local_weighted_cost = float(np.sum(local_costs[active] * active_weights))
    local_ratio = local_weighted_cost / max(global_weighted_cost, eps)
    distinct_local_plans = len(set(local_plan_strings))

    profile_totals = prepared.cluster_block_sums[active].sum(axis=1)
    features = prepared.cluster_block_sums[active] / np.maximum(profile_totals, eps)[:, None]

    shared_rows: list[dict[str, Any]] = []
    best_any_shared_ratio = math.inf
    best_any_shared_m = None
    best_any_shared_plan_count = None
    best_any_profile_assigned_ratio = math.inf
    best_small_shared_ratio = math.inf
    best_small_shared_m = None
    best_small_shared_plan_count = None
    best_small_profile_assigned_ratio = math.inf

    for m in shared_plan_counts:
        if m <= 0 or m > active.size:
            continue
        labels = crp.weighted_kmeans(features, active_weights, m, sample_seed, kmeans_iters)
        group_plans: list[crp.Plan] = []
        group_costs = np.zeros((active.size, m), dtype=np.float64)
        profile_assigned_cost = 0.0
        active_groups = 0

        for gid in range(m):
            member_mask = labels == gid
            if not np.any(member_mask):
                group_plans.append(tuple())
                group_costs[:, gid] = np.inf
                continue
            active_groups += 1
            member_indices = active[member_mask]
            member_weights = prepared.weights[member_indices]
            group_var = np.average(
                prepared.cluster_risk[member_indices], axis=0, weights=member_weights
            )
            nblocks = prepared.padded_dim // crp.K_DIM_PADDING_SIZE
            group_block_sums = group_var.reshape(nblocks, crp.K_DIM_PADDING_SIZE).sum(axis=1)
            plan, _, _ = crp.dp_plan_from_block_sums(group_block_sums, avg_bits)
            group_plans.append(plan)

            for pos, cid in enumerate(active):
                group_costs[pos, gid] = crp.plan_cost(prepared.cluster_block_sums[cid], plan)
            profile_assigned_cost += float(
                np.sum(group_costs[member_mask, gid] * active_weights[member_mask])
            )

        cost_assigned_labels = np.argmin(group_costs, axis=1)
        cost_assigned_costs = np.min(group_costs, axis=1)
        cost_assigned_weighted_cost = float(np.sum(cost_assigned_costs * active_weights))
        profile_assigned_ratio = profile_assigned_cost / max(global_weighted_cost, eps)
        cost_assigned_ratio = cost_assigned_weighted_cost / max(global_weighted_cost, eps)
        plan_strings = [crp.compact_plan(plan) for plan in group_plans if plan]

        if cost_assigned_ratio < best_any_shared_ratio:
            best_any_shared_ratio = cost_assigned_ratio
            best_any_shared_m = m
            best_any_shared_plan_count = len(set(plan_strings))
            best_any_profile_assigned_ratio = profile_assigned_ratio
        if m <= 4 and cost_assigned_ratio < best_small_shared_ratio:
            best_small_shared_ratio = cost_assigned_ratio
            best_small_shared_m = m
            best_small_shared_plan_count = len(set(plan_strings))
            best_small_profile_assigned_ratio = profile_assigned_ratio

        shared_rows.append(
            {
                "M": m,
                "active_groups": active_groups,
                "distinct_shared_plans": len(set(plan_strings)),
                "profile_assigned_ratio": profile_assigned_ratio,
                "cost_assigned_ratio": cost_assigned_ratio,
                "profile_assignment_gap": profile_assigned_ratio - cost_assigned_ratio,
                "oracle_gap": cost_assigned_ratio - local_ratio,
                "group_plans": plan_strings,
                "cost_assigned_cluster_counts": np.bincount(
                    cost_assigned_labels, minlength=m
                ).astype(int).tolist(),
            }
        )

    if not math.isfinite(best_any_shared_ratio):
        best_any_shared_ratio = math.nan
        best_any_profile_assigned_ratio = math.nan
    if not math.isfinite(best_small_shared_ratio):
        best_small_shared_ratio = math.nan
        best_small_profile_assigned_ratio = math.nan

    local_gain = 1.0 - local_ratio
    best_any_shared_gain = 1.0 - best_any_shared_ratio
    best_any_retention = best_any_shared_gain / local_gain if local_gain > eps else 0.0
    best_small_shared_gain = 1.0 - best_small_shared_ratio
    best_small_retention = best_small_shared_gain / local_gain if local_gain > eps else 0.0
    multi_segment = len(global_plan) >= 3
    visible_local_gain = local_ratio <= 0.97
    small_family_exists = best_small_shared_m is not None
    small_family_preserves_gain = best_small_retention >= 0.70
    eligible = bool(
        multi_segment
        and visible_local_gain
        and small_family_exists
        and small_family_preserves_gain
    )

    if eligible:
        decision = "continue"
    elif local_ratio <= 0.985 and len(global_plan) >= 3:
        decision = "weak-review"
    else:
        decision = "abstain"

    return {
        "case": prepared.case.name,
        "dataset": prepared.case.dataset,
        "k": prepared.case.k,
        "avg_bits": avg_bits,
        "num_vectors": prepared.num_vectors,
        "sampled_vectors": prepared.sampled_vectors,
        "num_clusters": prepared.num_clusters,
        "active_clusters": int(active.size),
        "dim": prepared.dim,
        "global_plan": crp.compact_plan(global_plan),
        "global_segment_count": len(global_plan),
        "global_used_bits": crp.plan_used_bits(global_plan),
        "total_bits": total_bits,
        "global_dp_cost": float(global_dp_cost),
        "global_weighted_cost": global_weighted_cost,
        "local_oracle_ratio": local_ratio,
        "local_gain": local_gain,
        "distinct_local_plans": distinct_local_plans,
        "best_small_M": best_small_shared_m,
        "best_small_distinct_plans": best_small_shared_plan_count,
        "best_small_profile_assigned_ratio": best_small_profile_assigned_ratio,
        "best_small_cost_assigned_ratio": best_small_shared_ratio,
        "best_small_shared_gain": best_small_shared_gain,
        "best_small_retention": best_small_retention,
        "best_any_M": best_any_shared_m,
        "best_any_distinct_plans": best_any_shared_plan_count,
        "best_any_profile_assigned_ratio": best_any_profile_assigned_ratio,
        "best_any_cost_assigned_ratio": best_any_shared_ratio,
        "best_any_shared_gain": best_any_shared_gain,
        "best_any_retention": best_any_retention,
        "eligible": eligible,
        "decision": decision,
        "shared_families": shared_rows,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "case",
        "dataset",
        "k",
        "avg_bits",
        "sampled_vectors",
        "active_clusters",
        "global_plan",
        "global_segment_count",
        "local_oracle_ratio",
        "best_small_M",
        "best_small_profile_assigned_ratio",
        "best_small_cost_assigned_ratio",
        "best_small_retention",
        "best_any_M",
        "best_any_cost_assigned_ratio",
        "best_any_retention",
        "distinct_local_plans",
        "best_small_distinct_plans",
        "decision",
        "eligible",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(path: Path, rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    lines = [
        "# Cluster Residual Eligibility Matrix",
        "",
        "This report is query-unaware. It uses base PCA vectors, IVF centroids,",
        "cluster ids, and residual variance profiles only. No query vectors or",
        "ground-truth labels are used for plan learning or assignment.",
        "",
        "## Assignment Rule",
        "",
        "For each dataset and bit budget, the driver first constructs a small",
        "family of shared plans from residual-profile groups. Each IVF cluster is",
        "then assigned to the shared plan with the lowest offline residual proxy:",
        "",
        "```text",
        "assign(c) = argmin_P cost(residual_profile_c, P)",
        "```",
        "",
        "This `cost-assigned` ratio is deployable under the current offline model:",
        "it needs one plan id per IVF cluster but no query workload.",
        "",
        "## Eligibility Rule",
        "",
        "A row is marked `continue` only when all of these data-only conditions",
        "hold:",
        "",
        "- the global SAQ plan has at least three segments;",
        "- the cluster-local oracle ratio is at most 0.97;",
        "- a shared family with M <= 4 preserves at least 70% of the local-oracle",
        "  proxy gain;",
        "- this small shared family is enough to plausibly store one plan id",
        "  per IVF cluster.",
        "",
        "Rows marked `weak-review` have some residual signal but should not drive",
        "index-format work without additional evidence. Rows marked `abstain` do",
        "not justify local plan metadata under this proxy.",
        "",
        "## Matrix",
        "",
        "| case | B | global plan | local-oracle | small M | small profile-assigned | small cost-assigned | small retention | best-any M | decision |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        best_small_m = "" if row["best_small_M"] is None else row["best_small_M"]
        best_any_m = "" if row["best_any_M"] is None else row["best_any_M"]
        lines.append(
            "| {case} | {avg_bits:g} | `{global_plan}` | {local_oracle_ratio:.6f} | "
            "{best_small_m} | {best_small_profile_assigned_ratio:.6f} | "
            "{best_small_cost_assigned_ratio:.6f} | {best_small_retention:.3f} | "
            "{best_any_m} | {decision} |".format(
                best_small_m=best_small_m,
                best_any_m=best_any_m,
                **row,
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The matrix should be read as a feasibility filter rather than an",
            "end-to-end search result. A positive row means the offline residual",
            "proxy sees exploitable cluster-local structure; it does not yet imply",
            "better recall or QPS. Negative rows are important because they define",
            "where shared local plans should not be applied.",
            "",
            "Command template:",
            "",
            "```bash",
            "python script/cluster_residual_feasibility_matrix.py \\",
            "  --case name=gist_full,data_dir=/tmp/saq-run/data/gist_full,dataset=gist_full,k=4096,max_vectors=0 \\",
            "  --bits 3,4,5 \\",
            "  --shared-plan-counts 2,4,8 \\",
            "  --output-prefix /tmp/saq-run/structural/cluster_residual_matrix",
            "```",
            "",
            f"Actual bits: `{args.bits}`",
            f"Actual shared plan counts: `{args.shared_plan_counts}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    cases = [parse_case(text) for text in args.case]
    bits = split_floats(args.bits)
    shared_plan_counts = split_ints(args.shared_plan_counts)
    rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for case in cases:
        prepared = prepare_case(
            case=case,
            sample_seed=args.sample_seed,
            chunk_size=args.chunk_size,
            min_cluster_size=args.min_cluster_size,
            risk_stat=args.risk_stat,
        )
        for avg_bits in bits:
            row = evaluate_bit_budget(
                prepared=prepared,
                avg_bits=avg_bits,
                shared_plan_counts=shared_plan_counts,
                sample_seed=args.sample_seed,
                kmeans_iters=args.kmeans_iters,
                eps=args.eps,
            )
            rows.append(row)
            summaries.append(row)
            print(
                f"{row['case']} B={avg_bits:g} local={row['local_oracle_ratio']:.6g} "
                f"small_cost_assigned={row['best_small_cost_assigned_ratio']:.6g} "
                f"decision={row['decision']}"
            )

    output_prefix = Path(args.output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json = output_prefix.with_suffix(".summary.json")
    summary_csv = output_prefix.with_suffix(".csv")
    summary_md = output_prefix.with_suffix(".md")
    summary_json.write_text(json.dumps(summaries, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(summary_csv, rows)
    write_markdown(summary_md, rows, args)

    print(f"Wrote {summary_md}")
    print(f"Wrote {summary_json}")
    print(f"Wrote {summary_csv}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a query-unaware residual-plan eligibility matrix."
    )
    parser.add_argument(
        "--case",
        action="append",
        required=True,
        help=(
            "Dataset case as name=...,data_dir=...,dataset=...,k=...,"
            "max_vectors=... . Repeat for multiple datasets."
        ),
    )
    parser.add_argument("--bits", default="3,4,5", help="Comma-separated SAQ bit budgets.")
    parser.add_argument("--shared-plan-counts", default="2,4,8", help="Shared family sizes.")
    parser.add_argument("--sample-seed", type=int, default=0, help="Deterministic sampling seed.")
    parser.add_argument("--chunk-size", type=int, default=8192, help="Residual accumulation chunk size.")
    parser.add_argument("--min-cluster-size", type=int, default=2, help="Minimum active cluster size.")
    parser.add_argument("--kmeans-iters", type=int, default=30, help="Weighted k-means iterations.")
    parser.add_argument(
        "--risk-stat",
        choices=["variance", "second_moment"],
        default="variance",
        help="Residual statistic used as the DP risk vector.",
    )
    parser.add_argument("--eps", type=float, default=1e-12, help="Numerical floor for ratios.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for .md/.json/.csv.")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
