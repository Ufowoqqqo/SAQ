#!/usr/bin/env python3
"""Base-only decomposition of SAQ's within-segment mixed-width opportunity.

This deliberately evaluates SAQ's own variance/2^b planning surrogate.  It is
not an encoder, query consumer, Recall experiment, or performance benchmark.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import platform
import resource
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROWS = 16_384
FOLD_ROWS = ROWS // 2
BLOCK_DIMENSIONS = 64
AVERAGE_BITS = 4
FACTOR_BITS = 64
MIN_BITS = 1
MAX_BITS = 11
ROTATION_SEED = 20_260_903
ADJUSTMENT_ROUNDS = 6
ADJUSTMENT_EPSILON = 1e-8


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    bits: int


def read_panel(path: Path, dimensions: int) -> np.ndarray:
    expected = ROWS * (dimensions + 1) * 4
    if path.stat().st_size != expected:
        raise ValueError(f"{path}: expected {expected} bytes")
    mapped = np.memmap(path, dtype="<f4", mode="r", shape=(ROWS, dimensions + 1))
    if not np.all(mapped[:, 0].view("<i4") == dimensions):
        raise ValueError(f"{path}: dimension headers")
    values = np.asarray(mapped[:, 1:], dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{path}: non-finite values")
    return values


def saq_plan(variance: np.ndarray) -> list[Segment]:
    """Reproduce SaqDataMaker::dynamic_programming for avg_bits=4."""
    dimensions = int(variance.size)
    if dimensions % BLOCK_DIMENSIONS:
        raise ValueError("SAQ dimension granularity")
    blocks = dimensions // BLOCK_DIMENSIONS
    maximum_segments = blocks // 2
    total_bits = AVERAGE_BITS * dimensions + FACTOR_BITS
    # A sparse form of f[ns][block][used_bits].
    layers: list[dict[tuple[int, int], float]] = [{(0, 0): 0.0}]
    parents: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    answer: tuple[int, int, int] | None = None
    answer_cost = float("inf")

    for segment_count in range(maximum_segments + 1):
        layer = layers[segment_count]
        for block, used_bits in sorted(layer):
            cost = layer[(block, used_bits)]
            if block == blocks:
                # Match the production planner's 1% replacement rule.
                if cost * 1.01 < answer_cost:
                    answer = (segment_count, block, used_bits)
                    answer_cost = cost
                continue
            if segment_count == maximum_segments:
                continue
            if len(layers) == segment_count + 1:
                layers.append({})
            target = layers[segment_count + 1]
            variance_sum = 0.0
            for length_blocks in range(1, blocks - block + 1):
                lo = (block + length_blocks - 1) * BLOCK_DIMENSIONS
                hi = lo + BLOCK_DIMENSIONS
                variance_sum += float(variance[lo:hi].sum())
                for bits in range(MIN_BITS, MAX_BITS + 1):
                    new_used = (
                        used_bits
                        + bits * length_blocks * BLOCK_DIMENSIONS
                        + FACTOR_BITS
                    )
                    if new_used > total_bits:
                        break
                    key = (block + length_blocks, new_used)
                    candidate = cost + variance_sum / (1 << bits)
                    if candidate < target.get(key, float("inf")):
                        target[key] = candidate
                        parents[(segment_count + 1, *key)] = (
                            block,
                            used_bits,
                            bits,
                        )
            # The production code permits one zero-bit tail segment.
            key = (blocks, used_bits)
            candidate = cost + variance_sum
            if candidate < target.get(key, float("inf")):
                target[key] = candidate
                parents[(segment_count + 1, *key)] = (block, used_bits, 0)

    if answer is None:
        raise RuntimeError("SAQ planner found no feasible plan")
    result: list[Segment] = []
    segment_count, block, used_bits = answer
    while block:
        prior_block, prior_used, bits = parents[(segment_count, block, used_bits)]
        result.append(
            Segment(
                prior_block * BLOCK_DIMENSIONS,
                block * BLOCK_DIMENSIONS,
                bits,
            )
        )
        segment_count -= 1
        block = prior_block
        used_bits = prior_used
    result.reverse()
    if result[-1].end != dimensions:
        raise RuntimeError("incomplete SAQ plan")
    return result


def plan_bits(plan: list[Segment]) -> tuple[int, int, int]:
    payload = sum((segment.end - segment.start) * segment.bits for segment in plan)
    factors = FACTOR_BITS * sum(segment.bits > 0 for segment in plan)
    return payload, factors, payload + factors


def objective(variance: np.ndarray, plan: list[Segment]) -> float:
    return sum(
        float(variance[segment.start : segment.end].sum())
        / (1 << segment.bits if segment.bits else 1)
        for segment in plan
    )


def allocate_pair_costs(costs: np.ndarray, uniform_bits: int) -> list[int]:
    groups = int(costs.shape[0])
    if costs.shape != (groups, MAX_BITS):
        raise ValueError("pair cost shape")
    target = groups * uniform_bits
    previous = np.full(target + 1, np.inf)
    previous[0] = 0.0
    choices = np.full((groups, target + 1), -1, dtype=np.int16)
    for group in range(groups):
        current = np.full(target + 1, np.inf)
        for used in np.flatnonzero(np.isfinite(previous)):
            for bits in range(MIN_BITS, MAX_BITS + 1):
                total = int(used) + bits
                if total > target:
                    break
                candidate = previous[used] + costs[group, bits - 1]
                if candidate < current[total]:
                    current[total] = candidate
                    choices[group, total] = bits
        previous = current
    if not np.isfinite(previous[target]):
        raise RuntimeError("pair allocation infeasible")
    result = [0] * groups
    total = target
    for group in range(groups - 1, -1, -1):
        bits = int(choices[group, total])
        if bits < MIN_BITS:
            raise RuntimeError("pair allocation backtrack")
        result[group] = bits
        total -= bits
    return result


def allocate_pair_bits(pair_variance: np.ndarray, uniform_bits: int) -> list[int]:
    costs = np.array(
        [pair_variance / (1 << bits) for bits in range(MIN_BITS, MAX_BITS + 1)]
    ).T
    return allocate_pair_costs(costs, uniform_bits)


def rotation(start: int, end: int) -> tuple[np.ndarray, str]:
    seed = (ROTATION_SEED + start * 1009 + end * 9176) % (2**32)
    generator = np.random.RandomState(seed)
    matrix = generator.normal(size=(end - start, end - start))
    orthogonal, triangular = np.linalg.qr(matrix)
    signs = np.where(np.diag(triangular) < 0.0, -1.0, 1.0)
    orthogonal *= signs
    digest = hashlib.sha256(np.asarray(orthogonal, dtype="<f8").tobytes()).hexdigest()
    return orthogonal, digest


def mixed_objective(
    fit: np.ndarray,
    evaluation: np.ndarray,
    plan: list[Segment],
    rotate: bool,
) -> tuple[float, list[int], str]:
    total = 0.0
    all_bits: list[int] = []
    hashes: list[str] = []
    for segment in plan:
        fit_segment = fit[:, segment.start : segment.end]
        eval_segment = evaluation[:, segment.start : segment.end]
        if segment.bits == 0:
            total += float(eval_segment.var(axis=0).sum())
            continue
        if rotate:
            orthogonal, digest = rotation(segment.start, segment.end)
            fit_segment = fit_segment @ orthogonal
            eval_segment = eval_segment @ orthogonal
            hashes.append(f"{segment.start}:{segment.end}:{digest}")
        fit_variance = fit_segment.var(axis=0)
        eval_variance = eval_segment.var(axis=0)
        fit_pairs = fit_variance.reshape(-1, 2).sum(axis=1)
        eval_pairs = eval_variance.reshape(-1, 2).sum(axis=1)
        bits = allocate_pair_bits(fit_pairs, segment.bits)
        all_bits.extend(bits)
        total += sum(
            float(group_variance) / (1 << group_bits)
            for group_variance, group_bits in zip(eval_pairs, bits)
        )
    return total, all_bits, ";".join(hashes)


def nearest_lattice(values: np.ndarray, pair_bits: list[int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    coordinate_bits = np.repeat(np.asarray(pair_bits, dtype=np.int16), 2)
    if coordinate_bits.size != values.shape[1]:
        raise ValueError("lattice bit shape")
    maximum = np.max(np.abs(values), axis=1)
    quantized = np.zeros_like(values)
    codes = np.zeros(values.shape, dtype=np.int16)
    deltas = np.zeros_like(values)
    for bits in sorted(set(pair_bits)):
        columns = coordinate_bits == bits
        delta = 2.0 * maximum / (1 << bits)
        nonzero = delta > 0
        raw = np.zeros((values.shape[0], int(columns.sum())), dtype=np.float64)
        raw[nonzero] = np.floor(
            (values[nonzero][:, columns] + maximum[nonzero, None])
            / delta[nonzero, None]
        )
        raw = np.clip(raw, 0, (1 << bits) - 1)
        codes[:, columns] = raw.astype(np.int16)
        deltas[:, columns] = delta[:, None]
        quantized[:, columns] = (
            (raw + 0.5) * delta[:, None] - maximum[:, None]
        )
    return quantized, codes, deltas


def adjusted_lattice(values: np.ndarray, pair_bits: list[int]) -> np.ndarray:
    quantized, codes, deltas = nearest_lattice(values, pair_bits)
    coordinate_bits = np.repeat(np.asarray(pair_bits, dtype=np.int16), 2)
    inner_product = np.sum(values * quantized, axis=1)
    quantized_norm = np.sum(quantized * quantized, axis=1)
    adjustment_epsilon = ADJUSTMENT_EPSILON * quantized_norm
    for _ in range(ADJUSTMENT_ROUNDS):
        changed = False
        for coordinate in range(values.shape[1]):
            original = values[:, coordinate]
            current = quantized[:, coordinate].copy()
            code = codes[:, coordinate]
            delta = deltas[:, coordinate]
            other_norm = quantized_norm - current * current
            inner_delta = delta * original
            code_maximum = (1 << int(coordinate_bits[coordinate])) - 1
            while True:
                candidate_value = current + delta
                candidate_norm = other_norm + candidate_value * candidate_value
                candidate_inner = inner_product + inner_delta
                mask = (code < code_maximum) & (
                    (inner_product * inner_product + adjustment_epsilon)
                    * candidate_norm
                    < candidate_inner * candidate_inner * quantized_norm
                )
                if not np.any(mask):
                    break
                code[mask] += 1
                current[mask] = candidate_value[mask]
                inner_product[mask] = candidate_inner[mask]
                quantized_norm[mask] = candidate_norm[mask]
                changed = True
            while True:
                candidate_value = current - delta
                candidate_norm = other_norm + candidate_value * candidate_value
                candidate_inner = inner_product - inner_delta
                mask = (code > 0) & (
                    (inner_product * inner_product + adjustment_epsilon)
                    * candidate_norm
                    < candidate_inner * candidate_inner * quantized_norm
                )
                if not np.any(mask):
                    break
                code[mask] -= 1
                current[mask] = candidate_value[mask]
                inner_product[mask] = candidate_inner[mask]
                quantized_norm[mask] = candidate_norm[mask]
                changed = True
            quantized[:, coordinate] = current
        inner_product = np.sum(values * quantized, axis=1)
        quantized_norm = np.sum(quantized * quantized, axis=1)
        if not changed:
            break
    return quantized


def angular_loss(values: np.ndarray, quantized: np.ndarray) -> float:
    original_norm = np.sum(values * values, axis=1)
    quantized_norm = np.sum(quantized * quantized, axis=1)
    inner_product = np.sum(values * quantized, axis=1)
    denominator = inner_product * inner_product
    if np.any((original_norm > 0) & (quantized_norm > 0) & (denominator == 0)):
        return float("inf")
    ratio = np.divide(
        original_norm * quantized_norm,
        denominator,
        out=np.ones_like(original_norm),
        where=denominator > 0,
    )
    return float(np.sum(original_norm * np.maximum(ratio - 1.0, 0.0)))


def empirical_lattice_result(
    fit: np.ndarray,
    evaluation: np.ndarray,
    plan: list[Segment],
) -> tuple[float, float, list[int]]:
    baseline_loss = 0.0
    mixed_loss = 0.0
    selected_bits: list[int] = []
    for segment in plan:
        if segment.bits == 0:
            omitted_energy = float(
                np.sum(evaluation[:, segment.start : segment.end] ** 2)
            )
            baseline_loss += omitted_energy
            mixed_loss += omitted_energy
            continue
        fit_segment = fit[:, segment.start : segment.end]
        eval_segment = evaluation[:, segment.start : segment.end]
        orthogonal, _ = rotation(segment.start, segment.end)
        fit_segment = fit_segment @ orthogonal
        eval_segment = eval_segment @ orthogonal
        groups = (segment.end - segment.start) // 2
        costs = np.empty((groups, MAX_BITS), dtype=np.float64)
        for bits in range(MIN_BITS, MAX_BITS + 1):
            quantized, _, _ = nearest_lattice(fit_segment, [bits] * groups)
            errors = (fit_segment - quantized).reshape(fit_segment.shape[0], groups, 2)
            costs[:, bits - 1] = np.sum(errors * errors, axis=(0, 2))
        bits = allocate_pair_costs(costs, segment.bits)
        selected_bits.extend(bits)
        baseline_quantized = adjusted_lattice(eval_segment, [segment.bits] * groups)
        mixed_quantized = adjusted_lattice(eval_segment, bits)
        baseline_loss += angular_loss(eval_segment, baseline_quantized)
        mixed_loss += angular_loss(eval_segment, mixed_quantized)
    return baseline_loss, mixed_loss, selected_bits


def format_plan(plan: list[Segment]) -> str:
    return "|".join(f"{s.start}:{s.end}:{s.bits}" for s in plan)


def analyze_dataset(dataset: str, directory: Path, dimensions: int) -> list[dict[str, object]]:
    panels = {
        "PCA": read_panel(directory / "pca_full.fvecs", dimensions),
        "RESIDUAL_NLIST1024": read_panel(
            directory / "residual_nlist1024_full.fvecs", dimensions
        ),
        "RESIDUAL_NLIST4096": read_panel(
            directory / "residual_nlist4096_full.fvecs", dimensions
        ),
    }
    rows: list[dict[str, object]] = []
    for fold, fit_slice, eval_slice in (
        ("A_TO_B", slice(0, FOLD_ROWS), slice(FOLD_ROWS, ROWS)),
        ("B_TO_A", slice(FOLD_ROWS, ROWS), slice(0, FOLD_ROWS)),
    ):
        pca_fit = panels["PCA"][fit_slice]
        plan = saq_plan(pca_fit.var(axis=0))
        payload_bits, factor_bits, total_bits = plan_bits(plan)
        expected_total = AVERAGE_BITS * dimensions + FACTOR_BITS
        if total_bits > expected_total:
            raise RuntimeError("planner exceeded frozen byte budget")
        for stage, values in panels.items():
            fit = values[fit_slice]
            evaluation = values[eval_slice]
            eval_variance = evaluation.var(axis=0)
            baseline = objective(eval_variance, plan)
            pre, pre_bits, _ = mixed_objective(fit, evaluation, plan, False)
            post, post_bits, rotation_hashes = mixed_objective(
                fit, evaluation, plan, True
            )
            baseline_lattice, mixed_lattice, lattice_bits = empirical_lattice_result(
                fit, evaluation, plan
            )
            reference_bits = [
                segment.bits
                for segment in plan
                if segment.bits > 0
                for _ in range((segment.end - segment.start) // 2)
            ]
            rows.append(
                {
                    "dataset": dataset,
                    "stage": stage,
                    "fold": fold,
                    "saq_plan": format_plan(plan),
                    "payload_bits": payload_bits,
                    "factor_bits": factor_bits,
                    "total_bits": total_bits,
                    "budget_bits": expected_total,
                    "baseline_eval_objective": baseline,
                    "mixed_pre_eval_objective": pre,
                    "mixed_pre_gain_pct": 100.0 * (baseline - pre) / baseline,
                    "mixed_post_eval_objective": post,
                    "mixed_post_gain_pct": 100.0 * (baseline - post) / baseline,
                    "pre_bits_min": min(pre_bits),
                    "pre_bits_max": max(pre_bits),
                    "pre_bits_changed_from_segment": sum(
                        bit != reference for bit, reference in zip(pre_bits, reference_bits)
                    ),
                    "post_bits_min": min(post_bits),
                    "post_bits_max": max(post_bits),
                    "post_bits_changed_from_segment": sum(
                        bit != reference for bit, reference in zip(post_bits, reference_bits)
                    ),
                    "baseline_adjusted_angular_loss": baseline_lattice,
                    "mixed_adjusted_angular_loss": mixed_lattice,
                    "mixed_adjusted_angular_gain_pct": (
                        100.0 * (baseline_lattice - mixed_lattice) / baseline_lattice
                    ),
                    "lattice_bits_min": min(lattice_bits),
                    "lattice_bits_max": max(lattice_bits),
                    "lattice_bits_changed_from_segment": sum(
                        bit != reference
                        for bit, reference in zip(lattice_bits, reference_bits)
                    ),
                    "rotation_hashes": rotation_hashes,
                }
            )
    return rows


def write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sift-stages", type=Path, required=True)
    parser.add_argument("--gist-stages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", action="store_true", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise ValueError(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)
    started_cpu = time.process_time()
    started_wall = time.monotonic()
    rows = []
    rows.extend(analyze_dataset("SIFT1M", args.sift_stages, 128))
    rows.extend(analyze_dataset("GIST1M", args.gist_stages, 960))
    residual_rows = [row for row in rows if row["stage"].startswith("RESIDUAL")]
    minimum_post_gain = min(
        float(row["mixed_adjusted_angular_gain_pct"]) for row in residual_rows
    )
    decision = "PASS" if minimum_post_gain >= 5.0 else "STOP"
    write_tsv(args.output / "summary.tsv", rows)
    (args.output / "metadata.txt").write_text(
        "\n".join(
            (
                "label=BASE_ONLY_SAQ_PLANNER_OPPORTUNITY_DECOMPOSITION",
                f"python={platform.python_version()}",
                f"numpy={np.__version__}",
                f"average_bits={AVERAGE_BITS}",
                f"factor_bits_per_positive_segment={FACTOR_BITS}",
                f"rotation_seed={ROTATION_SEED}",
                "rotation=numpy_gaussian_qr_canonical_diagonal_sign",
                "pair_schema=adjacent_pairs_equal_width_within_pair",
                "planner_objective=sum_variance_over_2_pow_bits",
                "empirical_curve=nearest_uniform_lattice_sse_with_shared_segment_maximum",
                "evaluation_loss=post_adjustment_norm_squared_times_tan_squared_angle",
                f"adjustment_rounds={ADJUSTMENT_ROUNDS}",
                f"adjustment_epsilon={ADJUSTMENT_EPSILON}",
                "plan_source=pca_fit_fold_production_saq_dp_semantics",
                "bytes=exact_payload_plus_factor_match_to_each_saq_plan",
                "gate=residual_adjusted_angular_minimum_across_datasets_nlists_folds_ge_5pct",
                f"minimum_residual_post_rotation_gain_pct={minimum_post_gain:.12g}",
                f"decision={decision}",
                "performance_status=PROTOTYPE_NOT_PERFORMANCE_EVIDENCE",
                "claim_limit=planner_surrogate_not_encoder_recall_or_qps_evidence",
                f"omp_num_threads={os.environ.get('OMP_NUM_THREADS', 'unset')}",
                f"openblas_num_threads={os.environ.get('OPENBLAS_NUM_THREADS', 'unset')}",
            )
        )
        + "\n"
    )
    with (args.output / "resources.tsv").open("w") as destination:
        destination.write("cpu_seconds\twall_seconds\tpeak_rss_bytes\n")
        destination.write(
            f"{time.process_time() - started_cpu:.9f}\t"
            f"{time.monotonic() - started_wall:.9f}\t"
            f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
