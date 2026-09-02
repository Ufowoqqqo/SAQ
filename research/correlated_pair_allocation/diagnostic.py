#!/usr/bin/env python3
"""Base-only cross-fit diagnostic for allocation across correlated 2D blocks."""

from __future__ import annotations

import argparse
import csv
import math
import os
import platform
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROWS = 1_000_000
SAMPLE_ROWS = 16_384
FOLD_ROWS = SAMPLE_ROWS // 2
DIMENSIONS = 128
GROUPS = DIMENSIONS // 2
MIN_GROUP_BITS = 6
MAX_GROUP_BITS = 10
UNIFORM_BITS = 8
TOTAL_BITS = GROUPS * UNIFORM_BITS
SEED = 20_260_902
LLOYD_ITERATIONS = 30

Pair = tuple[int, int]


@dataclass
class ScalarCurve:
    fit_sse: dict[int, float]
    eval_sse: dict[int, float]


@dataclass
class PairCurve:
    fit_sse: dict[int, float]
    eval_sse: dict[int, float]
    splits: dict[int, tuple[int, int]]


def read_sample(path: Path, indices: np.ndarray) -> np.ndarray:
    """Read the first 128 coordinates of selected rows from an fvecs file."""
    with path.open("rb") as source:
        raw_dimension = np.fromfile(source, dtype="<i4", count=1)
    if raw_dimension.size != 1:
        raise ValueError(f"empty fvecs file: {path}")
    source_dimensions = int(raw_dimension[0])
    if source_dimensions < DIMENSIONS:
        raise ValueError(f"{path}: dimension {source_dimensions} < {DIMENSIONS}")
    row_bytes = 4 * (source_dimensions + 1)
    available_rows, remainder = divmod(path.stat().st_size, row_bytes)
    if remainder or available_rows < ROWS:
        raise ValueError(f"{path}: malformed or fewer than {ROWS} rows")
    if indices.shape != (SAMPLE_ROWS,) or np.any(indices >= ROWS):
        raise ValueError("invalid sample indices")

    mapped = np.memmap(
        path, dtype="<f4", mode="r", shape=(available_rows, source_dimensions + 1)
    )
    headers = mapped[indices, 0].view("<i4")
    if not np.all(headers == source_dimensions):
        raise ValueError(f"{path}: inconsistent selected-row dimensions")
    return np.asarray(mapped[indices, 1 : DIMENSIONS + 1], dtype=np.float64)


def sample_indices(dataset_offset: int) -> np.ndarray:
    generator = np.random.RandomState(SEED + dataset_offset)
    return generator.choice(ROWS, size=SAMPLE_ROWS, replace=False)


def moments(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = values.mean(axis=0, dtype=np.float64)
    centered = values - mean
    covariance = centered.T @ centered / (values.shape[0] - 1)
    variance = np.diag(covariance).copy()
    scale = np.sqrt(np.maximum(variance, 0.0))
    denominator = np.outer(scale, scale)
    correlation = np.divide(
        covariance,
        denominator,
        out=np.zeros_like(covariance),
        where=denominator > 0,
    )
    np.fill_diagonal(correlation, 1.0)
    return variance, correlation, mean


def validate_pairs(pairs: list[Pair]) -> None:
    if len(pairs) != GROUPS:
        raise ValueError("pair count")
    used: set[int] = set()
    for first, second in pairs:
        if not (0 <= first < second < DIMENSIONS) or first in used or second in used:
            raise ValueError("invalid pair partition")
        used.update((first, second))
    if len(used) != DIMENSIONS:
        raise ValueError("incomplete pair partition")


def adjacent_pairs() -> list[Pair]:
    return [(dimension, dimension + 1) for dimension in range(0, DIMENSIONS, 2)]


def correlation_pairs(correlation: np.ndarray) -> list[Pair]:
    """Deterministic strongest-edge-first correlation matching.

    This is deliberately described as greedy rather than an exact blossom
    solution.  The diagnostic asks whether an obvious stable signal exists;
    it does not claim an optimal correlation partition.
    """
    edges = [
        (-abs(float(correlation[first, second])), first, second)
        for first in range(DIMENSIONS)
        for second in range(first + 1, DIMENSIONS)
    ]
    edges.sort()
    used = np.zeros(DIMENSIONS, dtype=bool)
    result: list[Pair] = []
    for _, first, second in edges:
        if not used[first] and not used[second]:
            used[first] = used[second] = True
            result.append((first, second))
    result.sort()
    validate_pairs(result)
    return result


def eigenvalue_allocation_pairs(variance: np.ndarray) -> list[Pair]:
    """Two-coordinate specialization used by the existing OPQ-P control."""
    order = sorted(range(DIMENSIONS), key=lambda index: (-variance[index], index))
    buckets = [[order[index]] for index in range(GROUPS)]
    products = [float(variance[index]) for index in order[:GROUPS]]
    for coordinate in order[GROUPS:]:
        selected = min(
            (index for index, bucket in enumerate(buckets) if len(bucket) < 2),
            key=lambda index: (products[index], index),
        )
        buckets[selected].append(coordinate)
        products[selected] *= float(variance[coordinate])
    result = [tuple(sorted(bucket)) for bucket in buckets]
    result.sort()
    validate_pairs(result)
    return result


def canonical_basis(fit_pair: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = fit_pair.mean(axis=0, dtype=np.float64)
    centered = fit_pair - mean
    covariance = centered.T @ centered / (fit_pair.shape[0] - 1)
    _, basis = np.linalg.eigh(covariance)
    basis = basis[:, ::-1]
    for column in range(2):
        pivot = int(np.argmax(np.abs(basis[:, column])))
        if basis[pivot, column] < 0:
            basis[:, column] *= -1
    return mean, basis


def labels_for(values: np.ndarray, centers: np.ndarray) -> np.ndarray:
    boundaries = (centers[:-1] + centers[1:]) * 0.5
    return np.searchsorted(boundaries, values, side="left")


def scalar_curve(fit: np.ndarray, evaluation: np.ndarray) -> ScalarCurve:
    fit_sse: dict[int, float] = {}
    eval_sse: dict[int, float] = {}
    for bits in range(1, MAX_GROUP_BITS):
        center_count = 1 << bits
        probabilities = (np.arange(center_count, dtype=np.float64) + 0.5) / center_count
        centers = np.quantile(fit, probabilities, method="linear")
        for _ in range(LLOYD_ITERATIONS):
            labels = labels_for(fit, centers)
            counts = np.bincount(labels, minlength=center_count)
            sums = np.bincount(labels, weights=fit, minlength=center_count)
            updated = centers.copy()
            nonempty = counts > 0
            updated[nonempty] = sums[nonempty] / counts[nonempty]
            if np.array_equal(updated, centers) or np.max(np.abs(updated - centers)) <= 1e-12:
                centers = updated
                break
            centers = updated
        fit_labels = labels_for(fit, centers)
        eval_labels = labels_for(evaluation, centers)
        fit_delta = fit - centers[fit_labels]
        eval_delta = evaluation - centers[eval_labels]
        fit_sse[bits] = float(fit_delta @ fit_delta)
        eval_sse[bits] = float(eval_delta @ eval_delta)
    return ScalarCurve(fit_sse, eval_sse)


def pair_curve(fit: np.ndarray, evaluation: np.ndarray, pair: Pair) -> PairCurve:
    mean, basis = canonical_basis(fit[:, pair])
    fit_projected = (fit[:, pair] - mean) @ basis
    eval_projected = (evaluation[:, pair] - mean) @ basis
    axes = [
        scalar_curve(fit_projected[:, axis], eval_projected[:, axis])
        for axis in range(2)
    ]
    fit_sse: dict[int, float] = {}
    eval_sse: dict[int, float] = {}
    splits: dict[int, tuple[int, int]] = {}
    for group_bits in range(MIN_GROUP_BITS, MAX_GROUP_BITS + 1):
        candidates = []
        for first_bits in range(1, group_bits):
            second_bits = group_bits - first_bits
            if first_bits >= MAX_GROUP_BITS or second_bits >= MAX_GROUP_BITS:
                continue
            candidates.append(
                (
                    axes[0].fit_sse[first_bits] + axes[1].fit_sse[second_bits],
                    first_bits,
                    second_bits,
                )
            )
        best_fit, first_bits, second_bits = min(candidates)
        fit_sse[group_bits] = best_fit
        eval_sse[group_bits] = (
            axes[0].eval_sse[first_bits] + axes[1].eval_sse[second_bits]
        )
        splits[group_bits] = (first_bits, second_bits)
    return PairCurve(fit_sse, eval_sse, splits)


def allocate_bits(curves: list[PairCurve]) -> list[int]:
    infinity = float("inf")
    previous = np.full(TOTAL_BITS + 1, infinity)
    previous[0] = 0.0
    choices = np.full((len(curves), TOTAL_BITS + 1), -1, dtype=np.int16)
    for group, curve in enumerate(curves):
        current = np.full(TOTAL_BITS + 1, infinity)
        minimum_total = MIN_GROUP_BITS * (group + 1)
        maximum_total = MAX_GROUP_BITS * (group + 1)
        for total in range(minimum_total, min(TOTAL_BITS, maximum_total) + 1):
            for bits in range(MIN_GROUP_BITS, MAX_GROUP_BITS + 1):
                prior = total - bits
                if prior < 0 or not math.isfinite(previous[prior]):
                    continue
                candidate = previous[prior] + curve.fit_sse[bits]
                if candidate < current[total]:
                    current[total] = candidate
                    choices[group, total] = bits
        previous = current
    if not math.isfinite(previous[TOTAL_BITS]):
        raise RuntimeError("fixed-total allocation is infeasible")
    result = [0] * len(curves)
    total = TOTAL_BITS
    for group in range(len(curves) - 1, -1, -1):
        bits = int(choices[group, total])
        if bits < MIN_GROUP_BITS:
            raise RuntimeError("allocation backtrack failure")
        result[group] = bits
        total -= bits
    if total != 0 or sum(result) != TOTAL_BITS:
        raise RuntimeError("allocation total mismatch")
    return result


def association_row(
    pairs: list[Pair], fit_correlation: np.ndarray, eval_correlation: np.ndarray
) -> dict[str, float]:
    fit_values = np.array([fit_correlation[pair] for pair in pairs])
    eval_values = np.array([eval_correlation[pair] for pair in pairs])
    nonzero = (fit_values != 0) & (eval_values != 0)
    sign_agreement = float(np.mean(np.sign(fit_values[nonzero]) == np.sign(eval_values[nonzero])))
    return {
        "fit_abs_mean": float(np.mean(np.abs(fit_values))),
        "fit_abs_median": float(np.median(np.abs(fit_values))),
        "eval_abs_mean": float(np.mean(np.abs(eval_values))),
        "eval_abs_median": float(np.median(np.abs(eval_values))),
        "sign_agreement": sign_agreement,
    }


def overlap(first: list[Pair], second: list[Pair]) -> int:
    return len(set(first) & set(second))


def analyze_direction(
    dataset: str,
    fold: str,
    fit: np.ndarray,
    evaluation: np.ndarray,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[Pair],
]:
    fit_variance, fit_correlation, _ = moments(fit)
    _, eval_correlation, _ = moments(evaluation)
    plans = {
        "CORR_GREEDY": correlation_pairs(fit_correlation),
        "EA": eigenvalue_allocation_pairs(fit_variance),
        "ADJ": adjacent_pairs(),
    }
    summary_rows: list[dict[str, object]] = []
    pair_rows: list[dict[str, object]] = []
    curve_rows: list[dict[str, object]] = []
    correlation_rows = [
        {
            "dataset": dataset,
            "fold": fold,
            "dim1": first,
            "dim2": second,
            "fit_correlation": float(fit_correlation[first, second]),
            "eval_correlation": float(eval_correlation[first, second]),
        }
        for first in range(DIMENSIONS)
        for second in range(first + 1, DIMENSIONS)
    ]
    all_fit_absolute = np.array(
        [abs(row["fit_correlation"]) for row in correlation_rows]
    )
    all_eval_absolute = np.array(
        [abs(row["eval_correlation"]) for row in correlation_rows]
    )
    for plan_name, pairs in plans.items():
        curves = [pair_curve(fit, evaluation, pair) for pair in pairs]
        allocated = allocate_bits(curves)
        uniform_fit = sum(curve.fit_sse[UNIFORM_BITS] for curve in curves)
        uniform_eval = sum(curve.eval_sse[UNIFORM_BITS] for curve in curves)
        allocated_fit = sum(
            curve.fit_sse[bits] for curve, bits in zip(curves, allocated)
        )
        allocated_eval = sum(
            curve.eval_sse[bits] for curve, bits in zip(curves, allocated)
        )
        association = association_row(pairs, fit_correlation, eval_correlation)
        summary_rows.append(
            {
                "dataset": dataset,
                "fold": fold,
                "plan": plan_name,
                **association,
                "uniform_fit_sse": uniform_fit,
                "allocated_fit_sse": allocated_fit,
                "fit_gain_pct": 100.0 * (uniform_fit - allocated_fit) / uniform_fit,
                "uniform_eval_sse": uniform_eval,
                "allocated_eval_sse": allocated_eval,
                "eval_gain_pct": 100.0 * (uniform_eval - allocated_eval) / uniform_eval,
                "bits_6": allocated.count(6),
                "bits_7": allocated.count(7),
                "bits_8": allocated.count(8),
                "bits_9": allocated.count(9),
                "bits_10": allocated.count(10),
                "all_pair_fit_abs_p50": float(np.quantile(all_fit_absolute, 0.50)),
                "all_pair_fit_abs_p90": float(np.quantile(all_fit_absolute, 0.90)),
                "all_pair_fit_abs_p99": float(np.quantile(all_fit_absolute, 0.99)),
                "all_pair_eval_abs_p50": float(np.quantile(all_eval_absolute, 0.50)),
                "all_pair_eval_abs_p90": float(np.quantile(all_eval_absolute, 0.90)),
                "all_pair_eval_abs_p99": float(np.quantile(all_eval_absolute, 0.99)),
            }
        )
        for group, (pair, curve, bits) in enumerate(zip(pairs, curves, allocated)):
            first_bits, second_bits = curve.splits[bits]
            pair_rows.append(
                {
                    "dataset": dataset,
                    "fold": fold,
                    "plan": plan_name,
                    "group": group,
                    "dim1": pair[0],
                    "dim2": pair[1],
                    "fit_correlation": float(fit_correlation[pair]),
                    "eval_correlation": float(eval_correlation[pair]),
                    "group_bits": bits,
                    "pc1_bits": first_bits,
                    "pc2_bits": second_bits,
                    "uniform_fit_sse": curve.fit_sse[UNIFORM_BITS],
                    "allocated_fit_sse": curve.fit_sse[bits],
                    "uniform_eval_sse": curve.eval_sse[UNIFORM_BITS],
                    "allocated_eval_sse": curve.eval_sse[bits],
                }
            )
            for candidate_bits in range(MIN_GROUP_BITS, MAX_GROUP_BITS + 1):
                candidate_first, candidate_second = curve.splits[candidate_bits]
                curve_rows.append(
                    {
                        "dataset": dataset,
                        "fold": fold,
                        "plan": plan_name,
                        "group": group,
                        "dim1": pair[0],
                        "dim2": pair[1],
                        "group_bits": candidate_bits,
                        "pc1_bits": candidate_first,
                        "pc2_bits": candidate_second,
                        "fit_sse": curve.fit_sse[candidate_bits],
                        "eval_sse": curve.eval_sse[candidate_bits],
                        "dp_selected": int(candidate_bits == bits),
                    }
                )
    return (
        summary_rows,
        pair_rows,
        curve_rows,
        correlation_rows,
        plans["CORR_GREEDY"],
    )


def write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("empty output")
    with path.open("w", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def run_dataset(dataset: str, path: Path, offset: int, output: Path) -> None:
    started_cpu = time.process_time()
    started_wall = time.monotonic()
    indices = sample_indices(offset)
    values = read_sample(path, indices)
    folds = {"A_TO_B": (values[:FOLD_ROWS], values[FOLD_ROWS:]),
             "B_TO_A": (values[FOLD_ROWS:], values[:FOLD_ROWS])}
    all_summary: list[dict[str, object]] = []
    all_pairs: list[dict[str, object]] = []
    all_curves: list[dict[str, object]] = []
    all_correlations: list[dict[str, object]] = []
    correlation_plans: dict[str, list[Pair]] = {}
    for fold, (fit, evaluation) in folds.items():
        summary, pairs, curves, correlations, correlation_plan = analyze_direction(
            dataset, fold, fit, evaluation
        )
        all_summary.extend(summary)
        all_pairs.extend(pairs)
        all_curves.extend(curves)
        all_correlations.extend(correlations)
        correlation_plans[fold] = correlation_plan
    for row in all_summary:
        row["corr_pair_overlap_across_folds"] = overlap(
            correlation_plans["A_TO_B"], correlation_plans["B_TO_A"]
        )
    write_tsv(output / f"{dataset}_summary.tsv", all_summary)
    write_tsv(output / f"{dataset}_pairs.tsv", all_pairs)
    write_tsv(output / f"{dataset}_curves.tsv", all_curves)
    write_tsv(output / f"{dataset}_correlations.tsv", all_correlations)
    cpu = time.process_time() - started_cpu
    wall = time.monotonic() - started_wall
    with (output / f"{dataset}_resources.tsv").open("w") as destination:
        destination.write("dataset\tcpu_seconds\twall_seconds\tpeak_rss_bytes\n")
        destination.write(
            f"{dataset}\t{cpu:.9f}\t{wall:.9f}\t"
            f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}\n"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sift", type=Path, required=True)
    parser.add_argument("--gist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", action="store_true", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise ValueError(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)
    metadata = [
        "label=BASE_ONLY_RECONSTRUCTION_DIAGNOSTIC",
        f"python={platform.python_version()}",
        f"numpy={np.__version__}",
        f"seed={SEED}",
        f"sample_rows={SAMPLE_ROWS}",
        f"dimensions={DIMENSIONS}",
        f"total_bits={TOTAL_BITS}",
        f"omp_num_threads={os.environ.get('OMP_NUM_THREADS', 'unset')}",
        f"openblas_num_threads={os.environ.get('OPENBLAS_NUM_THREADS', 'unset')}",
        "correlation_pairing=deterministic_strongest_edge_first_greedy",
        "quantizer=local_2d_pca_plus_deterministic_1d_lloyd",
        "claim_limit=raw_base_coordinates_not_saq_residuals_or_query_evidence",
    ]
    (args.output / "metadata.txt").write_text("\n".join(metadata) + "\n")
    run_dataset("SIFT1M", args.sift, 0, args.output)
    run_dataset("GIST1M_HEAD128", args.gist, 1, args.output)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # concise CLI failure boundary
        print(f"correlated-pair diagnostic: {error}", file=sys.stderr)
        sys.exit(1)
