#!/usr/bin/env python3
"""Frozen 48-row residual-panel audit; no raw data or query inputs are read."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import platform
import resource
import shlex
import signal
import sys
import time
from pathlib import Path

import numpy as np

from research.correlated_pair_allocation import diagnostic as d


COMPARATORS = (("CORR_GREEDY", "S"), ("CORR_GREEDY", "V"), ("ADJ", "S"), ("EA", "S"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def array_hash(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype="<f8").tobytes()).hexdigest()


def scalar_dp(costs: np.ndarray, total: int = d.TOTAL_BITS,
              group_bounds: tuple[int, int] | None = None) -> list[int]:
    """Direct axis/state DP; exact ties prefer the smaller last decision.

    With groups, a pending state retains the first axis's bit count. Completing
    it prefers smaller (group bits, first-axis bits), matching legacy E. We
    retain the prefix separately until group completion so addition order also
    matches E: prefix + (first SSE + second SSE). No legacy group curves or
    allocator are used here.
    """
    costs = np.asarray(costs, dtype=np.float64)
    if costs.ndim != 2 or costs.shape[1] != 9 or not np.isfinite(costs).all():
        raise ValueError("expected finite per-axis costs at widths 1..9")
    previous = np.full(total + 1, np.inf)
    previous[0] = 0.0
    grouped = group_bounds is not None
    if grouped and costs.shape[0] % 2:
        raise ValueError("odd axis count with pair constraints")
    steps = costs.shape[0] // 2 if grouped else costs.shape[0]
    choices = np.full((steps, total + 1, 2 if grouped else 1), -1, dtype=np.int16)
    for step in range(steps):
        current = np.full(total + 1, np.inf)
        if grouped:
            pending = np.full((9, total + 1), np.inf)
            for first in range(1, 10):
                if first <= total:
                    pending[first - 1, first:] = previous[:total + 1 - first]
            for group_bits in range(group_bounds[0], group_bounds[1] + 1):
                for first in range(1, 10):
                    second = group_bits - first
                    if not 1 <= second <= 9 or second > total:
                        continue
                    candidate = pending[first - 1, :total + 1 - second] + (
                        costs[2 * step, first - 1] + costs[2 * step + 1, second - 1])
                    improved = candidate < current[second:]
                    current[second:][improved] = candidate[improved]
                    choices[step, second:, 0][improved] = first
                    choices[step, second:, 1][improved] = second
        else:
            for bits in range(1, min(9, total) + 1):
                candidate = previous[:total + 1 - bits] + costs[step, bits - 1]
                improved = candidate < current[bits:]
                current[bits:][improved] = candidate[improved]
                choices[step, bits:, 0][improved] = bits
        previous = current
    if not np.isfinite(previous[total]):
        raise ValueError("infeasible scalar budget")
    result = []
    remaining = total
    for step in range(steps - 1, -1, -1):
        selected = choices[step, remaining].tolist()
        if min(selected) < 1:
            raise RuntimeError("scalar backtrack failure")
        result[0:0] = selected
        remaining -= sum(selected)
    if remaining or sum(result) != total:
        raise RuntimeError("scalar budget mismatch")
    return result


def selected_sse(costs: np.ndarray, bits: list[int]) -> float:
    return float(sum(costs[axis, width - 1] for axis, width in enumerate(bits)))


def allocations(curves: list[d.PairCurve]) -> tuple[dict[str, list[int]], np.ndarray, np.ndarray]:
    axes = [axis for curve in curves for axis in curve.axes]
    fit = np.array([[axis.fit_sse[bits] for bits in range(1, 10)] for axis in axes])
    evaluation = np.array([[axis.eval_sse[bits] for bits in range(1, 10)] for axis in axes])
    empirical_groups = d.allocate_bits(curves)
    empirical = [b for curve, group in zip(curves, empirical_groups) for b in curve.splits[group]]
    constrained = scalar_dp(fit, group_bounds=(6, 10))
    if empirical != constrained:
        raise AssertionError("independent constrained scalar DP differs from E, including ties")
    legacy_objective = sum(curve.fit_sse[b] for curve, b in zip(curves, empirical_groups))
    if not math.isclose(selected_sse(fit, constrained), legacy_objective, rel_tol=1e-12, abs_tol=1e-10):
        raise AssertionError("constrained scalar and E objectives differ")
    variance = np.concatenate([curve.eigenvalues for curve in curves])
    proxy = variance[:, None] * 2.0 ** (-2.0 * np.arange(1, 10))
    result = {
        "U": [b for curve in curves for b in curve.splits[8]],
        "V": scalar_dp(proxy, group_bounds=(6, 10)),
        "E": empirical,
        "S": scalar_dp(fit),
    }
    for arm, bits in result.items():
        if len(bits) != 128 or sum(bits) != 512 or not all(1 <= b <= 9 for b in bits):
            raise AssertionError(f"invalid {arm} payload")
        if arm != "S" and not all(6 <= sum(bits[g:g + 2]) <= 10 for g in range(0, 128, 2)):
            raise AssertionError(f"invalid {arm} group budget")
    fit_s, fit_e = (selected_sse(fit, result[arm]) for arm in ("S", "E"))
    if fit_s > fit_e + 1e-10 + 1e-12 * abs(fit_e):
        raise AssertionError("free scalar fit SSE exceeds restricted E")
    return result, fit, evaluation


def evaluate_pairing(dataset: str, fold: str, plan: str, pairs: list[d.Pair],
                     fit: np.ndarray, evaluation: np.ndarray, output: Path):
    started_cpu, started_wall = time.process_time(), time.monotonic()
    curves = [d.pair_curve(fit, evaluation, pair) for pair in pairs]
    arms, fit_costs, eval_costs = allocations(curves)
    compute_cpu, compute_wall = time.process_time() - started_cpu, time.monotonic() - started_wall
    identity = {"dataset": dataset, "stage": "RESIDUAL_NLIST1024", "fold": fold, "plan": plan}
    model = {
        "pairs": np.asarray(pairs, dtype=np.uint8),
        "means": np.asarray([curve.mean for curve in curves]),
        "bases": np.asarray([curve.basis for curve in curves]),
        "eigenvalues": np.asarray([curve.eigenvalues for curve in curves]),
    }
    raw_rows = []
    for group, curve in enumerate(curves):
        for local_axis, axis in enumerate(curve.axes):
            for bits in range(1, 10):
                centers = axis.centers[bits]
                model[f"g{group:02d}_a{local_axis}_b{bits}"] = centers
                raw_rows.append({**identity, "group": group, "dim1": pairs[group][0],
                                 "dim2": pairs[group][1], "local_axis": local_axis,
                                 "bits": bits, "fit_sse": axis.fit_sse[bits],
                                 "eval_sse": axis.eval_sse[bits],
                                 "fit_variance": float(curve.eigenvalues[local_axis]),
                                 "center_count": len(centers), "codebook_sha256": array_hash(centers)})
    for arm, bits in arms.items():
        model[f"bits_{arm}"] = np.asarray(bits, dtype=np.uint8)
    model_path = output / "models" / f"{dataset}_{fold}_{plan}.npz"
    np.savez(model_path, **model)
    model_hash = sha256(model_path)
    summaries, selections = [], []
    for arm, bits in arms.items():
        fit_sse, eval_sse = selected_sse(fit_costs, bits), selected_sse(eval_costs, bits)
        group_bits = [sum(bits[g:g + 2]) for g in range(0, 128, 2)]
        entries = sum(1 << b for b in bits)
        transform_bytes = sum(curve.mean.nbytes + curve.basis.nbytes for curve in curves)
        summaries.append({**identity, "arm": arm, "fit_total_sse": fit_sse,
                          "eval_total_sse": eval_sse, "fit_sse_per_vector": fit_sse / len(fit),
                          "eval_sse_per_vector": eval_sse / len(evaluation),
                          "eval_gain_vs_U_pct": 100 * (1 - eval_sse / selected_sse(eval_costs, arms["U"])),
                          "payload_bits_per_vector": sum(bits), "payload_bytes_per_vector": sum(bits) // 8,
                          "groups_outside_6_10": sum(b < 6 or b > 10 for b in group_bits),
                          **{f"axes_bits_{b}": bits.count(b) for b in range(1, 10)},
                          "shared_transform_bytes": transform_bytes,
                          "shared_pairing_bytes": 128, "shared_bit_metadata_bytes": 128,
                          "shared_selected_codebook_bytes": entries * 8,
                          "selected_lookup_entries": entries,
                          "shared_model_total_bytes": transform_bytes + 256 + entries * 8,
                          "archive_file": str(model_path.relative_to(output)),
                          "archive_sha256": model_hash, "archive_bytes": model_path.stat().st_size,
                          "pairing_shared_compute_cpu_seconds": compute_cpu,
                          "pairing_shared_compute_wall_seconds": compute_wall})
        for group, pair in enumerate(pairs):
            for local_axis in range(2):
                axis = 2 * group + local_axis
                width = bits[axis]
                selections.append({**identity, "arm": arm, "group": group,
                                   "dim1": pair[0], "dim2": pair[1], "local_axis": local_axis,
                                   "bits": width, "group_bits": group_bits[group],
                                   "fit_sse": float(fit_costs[axis, width - 1]),
                                   "eval_sse": float(eval_costs[axis, width - 1])})
    return summaries, selections, raw_rows


def comparison_rows(summary):
    rows = []
    for dataset in ("SIFT1M", "GIST1M_HEAD128"):
        for fold in ("A_TO_B", "B_TO_A"):
            selected = {(row["plan"], row["arm"]): row for row in summary
                        if row["dataset"] == dataset and row["fold"] == fold}
            candidate = selected[("CORR_GREEDY", "E")]["eval_sse_per_vector"]
            for plan, arm in COMPARATORS:
                baseline = selected[(plan, arm)]["eval_sse_per_vector"]
                rows.append({"dataset": dataset, "fold": fold, "candidate": "CORR_GREEDY-E",
                             "comparator": f"{plan}-{arm}", "candidate_eval_sse_per_vector": candidate,
                             "comparator_eval_sse_per_vector": baseline,
                             "gain_fraction": 1 - candidate / baseline})
    return rows


def decision(comparisons) -> str:
    if all(row["gain_fraction"] >= 0.05 for row in comparisons):
        return "ELIGIBLE_FOR_CONFIRMATION"
    # A local signal must beat all four controls in the same dataset/fold.
    # Pairing-only gains while losing to CORR-S do not rescue allocation.
    contexts = {(row["dataset"], row["fold"]) for row in comparisons}
    if any(all(row["gain_fraction"] > 0 for row in comparisons
               if (row["dataset"], row["fold"]) == context) for context in contexts):
        return "PARK_INCONCLUSIVE"
    return "STOP_CURRENT_FORMULATION"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    for dataset in ("sift", "gist"):
        parser.add_argument(f"--{dataset}-panel", type=Path, required=True)
        parser.add_argument(f"--{dataset}-indices", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cpu-seconds", type=int, required=True,
                        help="remaining task CPU budget, including this runner")
    parser.add_argument("--frozen", action="store_true", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    if not 1 <= args.cpu_seconds <= 7200:
        raise ValueError("CPU allowance must be in 1..7200 seconds")
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        if os.environ.get(name) != "1":
            raise ValueError(f"{name} must be 1")
    if args.output.exists():
        raise ValueError("output must be a new durable directory")
    if str(args.output.resolve()).startswith("/tmp/"):
        raise ValueError("results must persist outside /tmp")
    args.output.mkdir(parents=True)
    (args.output / "models").mkdir()
    cpu_started, wall_started = time.process_time(), time.monotonic()
    cpu_limit = math.ceil(cpu_started) + args.cpu_seconds
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 1))
    resource.setrlimit(resource.RLIMIT_AS, (16 << 30, 16 << 30))

    def budget_exceeded(signum, frame):
        raise RuntimeError("CPU budget exhausted; partial records retained")

    signal.signal(signal.SIGXCPU, budget_exceeded)
    metadata = [f"command={shlex.join(sys.argv)}", f"cwd={Path.cwd()}", f"host={platform.node()}",
                f"python={platform.python_version()}", f"numpy={np.__version__}",
                f"affinity={sorted(os.sched_getaffinity(0))}", f"seed={d.SEED}",
                "threads=1", f"cpu_allowance_seconds={args.cpu_seconds}", "address_space_limit_bytes=17179869184",
                "candidate=CORR_GREEDY-E", "comparators=CORR_GREEDY-S,CORR_GREEDY-V,ADJ-S,EA-S",
                "decision=ELIGIBLE_all16_gains>=0.05;PARK_any_context_all4_gains>0;otherwise_STOP",
                "V_proxy=fit_eigenvalue*2**(-2*bits)",
                "tie_rule=smaller_last_group_budget_then_smaller_first_axis_bits;S_smaller_last_axis_bits",
                "data_scope=historical_16384_indices;GIST_first128_after_full_dimensional_residualization",
                "metadata_accounting=per_shared_model_not_per_vector;float64_means_bases_codebooks;uint8_pairs_bits",
                "archive_accounting=all_candidate_codebooks_and_eigenvalues_plus_npz_overhead;not_deployment_bytes",
                "lookup_entries=selected_scalar_centers;no_query_lookup_tables_materialized",
                "timing=shared_pairing_compute_repeated_on_arm_rows_do_not_sum;resources.tsv_includes_IO",
                "claim_limit=base_only_reconstruction;crossfit_directions_not_independent_datasets"]
    for path in (Path(__file__), Path(d.__file__)):
        metadata.append(f"source_sha256[{path.name}]={sha256(path)}")
    summary, selections, raw_rows = [], [], []
    status = "BLOCKED"
    try:
        for offset, (name, label) in enumerate((("sift", "SIFT1M"), ("gist", "GIST1M_HEAD128"))):
            panel_path, indices_path = getattr(args, f"{name}_panel"), getattr(args, f"{name}_indices")
            indices = np.fromfile(indices_path, dtype="<u8")
            if not np.array_equal(indices, d.sample_indices(offset)):
                raise ValueError(f"{name} indices do not match frozen historical ordering")
            metadata.extend((f"{name}_panel_path={panel_path.resolve()}",
                             f"{name}_panel_sha256={sha256(panel_path)}",
                             f"{name}_indices_path={indices_path.resolve()}",
                             f"{name}_indices_sha256={sha256(indices_path)}"))
            (args.output / "metadata.txt").write_text("\n".join(metadata) + "\n")
            panel = d.read_ordered_panel(panel_path)
            for fold, fit, evaluation in (("A_TO_B", panel[:d.FOLD_ROWS], panel[d.FOLD_ROWS:]),
                                          ("B_TO_A", panel[d.FOLD_ROWS:], panel[:d.FOLD_ROWS])):
                variance, correlation, _ = d.moments(fit)
                plans = {"ADJ": d.adjacent_pairs(), "CORR_GREEDY": d.correlation_pairs(correlation),
                         "EA": d.eigenvalue_allocation_pairs(variance)}
                for plan, pairs in plans.items():
                    rows, choices, curves = evaluate_pairing(label, fold, plan, pairs, fit, evaluation, args.output)
                    summary.extend(rows)
                    selections.extend(choices)
                    raw_rows.extend(curves)
                    for filename, values in (("summary.tsv", summary), ("allocations.tsv", selections),
                                             ("axis_curves.tsv", raw_rows)):
                        d.write_tsv(args.output / filename, values)
                    print(f"completed {label} {fold} {plan}; {len(summary)}/48 rows", flush=True)
        if len(summary) != 48:
            raise AssertionError("incomplete frozen result matrix")
        comparisons = comparison_rows(summary)
        d.write_tsv(args.output / "comparisons.tsv", comparisons)
        status = decision(comparisons)
        (args.output / "decision.txt").write_text(status + "\nNo confirmation experiment launched.\n")
    except BaseException as error:
        (args.output / "failure.txt").write_text(f"{type(error).__name__}: {error}\n")
        raise
    finally:
        (args.output / "metadata.txt").write_text("\n".join(metadata) + "\n")
        d.write_tsv(args.output / "resources.tsv", [{"status": status, "summary_rows": len(summary),
                    "cpu_seconds": time.process_time() - cpu_started,
                    "wall_seconds": time.monotonic() - wall_started,
                    "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}])
    return 0


if __name__ == "__main__":
    sys.exit(main())
