#!/usr/bin/env python3
"""SAQ segment-rotation ablation: actual mixed-lattice encoding, no local PCA.

This is a base-only encoder prototype. Global PCA and IVF residualization stay
fixed. It is not a raw-coordinate experiment or a production/query benchmark.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import platform
import resource
import sys
import time
from pathlib import Path

import numpy as np

import opportunity_reference as ref


SOURCE_COMMIT = "35f38aa7ae668a4734d7a08a9bcf73aa00da9a75"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def tsv(path, rows):
    if not rows:
        raise ValueError("empty output")
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def validate_plan(plan, dimensions):
    end = 0
    for segment in plan:
        if segment.start != end or segment.end <= end or (segment.end - end) % 2:
            raise ValueError("segments must partition dimensions into even lengths")
        if not 0 <= segment.bits <= ref.MAX_BITS:
            raise ValueError("invalid original bit width")
        end = segment.end
    if end != dimensions or not any(s.bits for s in plan):
        raise ValueError("incomplete or empty plan")


def encoded_losses(values, widths):
    """Compute error from actual selected codes, not the planning surrogate.

    CAQ rescales q by ||x||^2/<x,q>. The resulting squared reconstruction
    error equals ||x||^2 tan^2(theta); compute the reconstruction explicitly
    and check the identity. This is NOT the least-squares scale <x,q>/||q||^2.
    """
    nearest, _, _ = ref.nearest_lattice(values, widths)
    adjusted = ref.adjusted_lattice(values, widths)
    norm = np.einsum("ij,ij->i", values, values)
    inner = np.einsum("ij,ij->i", values, adjusted)
    qnorm = np.einsum("ij,ij->i", adjusted, adjusted)
    positive = norm > 0
    if np.any(positive & ((inner <= 0) | (qnorm <= 0))):
        raise FloatingPointError("nonzero input has degenerate quantized direction")
    scale = np.divide(norm, inner, out=np.zeros_like(norm), where=positive)
    reconstructed = adjusted * scale[:, None]
    error = np.sum((values - reconstructed) ** 2, axis=1)
    formula = np.zeros_like(norm)
    formula[positive] = norm[positive] * np.maximum(
        norm[positive] * qnorm[positive] / inner[positive] ** 2 - 1, 0)
    np.testing.assert_allclose(error, formula, rtol=2e-9, atol=1e-12)
    return {
        "rescaled_sse": error,
        "nearest_sse": np.sum((values - nearest) ** 2, axis=1),
        "adjusted_unscaled_sse": np.sum((values - adjusted) ** 2, axis=1),
    }


def fit_allocation(values, original_bits):
    """Only fit samples enter the additive nearest-lattice SSE allocator.

    This is the same allocator as the earlier opportunity diagnostic. Its
    objective is a proxy for the coupled post-adjustment angular objective.
    Negative results must not be described as an oracle impossibility result.
    """
    groups = values.shape[1] // 2
    costs = np.empty((groups, ref.MAX_BITS), dtype=np.float64)
    for bits in range(ref.MIN_BITS, ref.MAX_BITS + 1):
        quantized, _, _ = ref.nearest_lattice(values, [bits] * groups)
        costs[:, bits - 1] = np.sum(
            ((values - quantized) ** 2).reshape(len(values), groups, 2), axis=(0, 2))
    widths = ref.allocate_pair_costs(costs, original_bits)
    uniform = [original_bits] * groups
    # Prefer the incumbent only at exactly equal fitted objective.
    optimum = sum(costs[g, b - 1] for g, b in enumerate(widths))
    baseline = sum(costs[g, b - 1] for g, b in enumerate(uniform))
    if optimum == baseline:
        widths = uniform
    if sum(widths) != groups * original_bits or min(widths) < 1 or max(widths) > 11:
        raise AssertionError("mixed widths violate exact payload")
    if optimum > baseline + 1e-10 * max(1, abs(baseline)):
        raise AssertionError("DP worse than feasible uniform allocation")
    return widths, costs


def run_fold(fit, evaluation, plan):
    """Four arms share segment plan, input rows, factors and encoder settings."""
    validate_plan(plan, fit.shape[1])
    if fit.shape[1] != evaluation.shape[1]:
        raise ValueError("fit/evaluation shape mismatch")
    losses = {(rotation, allocation): {
        key: np.zeros(len(evaluation)) for key in
        ("rescaled_sse", "nearest_sse", "adjusted_unscaled_sse")}
        for rotation in ("IDENTITY", "QR") for allocation in ("UNIFORM", "ADAPTIVE")}
    allocations, curves, rotations = [], [], []
    for index, segment in enumerate(plan):
        start, end = segment.start, segment.end
        x, y = fit[:, start:end], evaluation[:, start:end]
        groups = (end - start) // 2
        if segment.bits == 0:
            energy = np.sum(y ** 2, axis=1)
            for metrics in losses.values():
                for key in metrics:
                    metrics[key] += energy
            continue
        for rotation in ("IDENTITY", "QR"):
            if rotation == "QR":
                matrix, digest = ref.rotation(start, end)
                np.testing.assert_allclose(matrix.T @ matrix, np.eye(end - start), atol=2e-12)
                xf, ye = x @ matrix, y @ matrix
                np.testing.assert_allclose(np.sum(ye ** 2, axis=1), np.sum(y ** 2, axis=1),
                                           rtol=1e-12, atol=1e-12)
            else:
                # No centering, PCA, rotation, or coordinate reordering here.
                xf, ye, digest = x, y, "identity"
            rotations.append({"segment": index, "rotation": rotation, "sha256": digest})
            chosen, costs = fit_allocation(xf, segment.bits)
            for group in range(groups):
                for bits in range(1, 12):
                    curves.append({"segment": index, "rotation": rotation, "pair": group,
                                   "bits_per_coordinate": bits, "fit_nearest_sse": costs[group, bits-1]})
            for allocation, widths in (("UNIFORM", [segment.bits] * groups),
                                       ("ADAPTIVE", chosen)):
                measured = encoded_losses(ye, widths)
                for key, values in measured.items():
                    losses[(rotation, allocation)][key] += values
                for group, bits in enumerate(widths):
                    allocations.append({"segment": index, "rotation": rotation,
                        "allocation": allocation, "pair": group,
                        "coordinate0": start + 2*group, "bits_per_coordinate": bits,
                        "original_bits": segment.bits})
    return losses, allocations, curves, rotations


def gain(candidate, baseline):
    return float("nan") if baseline == 0 else 100 * (1 - candidate / baseline)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panels-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite existing results")
    started_cpu, started_wall = time.process_time(), time.monotonic()
    args.output.mkdir(parents=True)
    (args.output / "STATUS.txt").write_text("RUNNING\n")
    summaries, allocations, curves, rotations, contrasts, hashes = [], [], [], [], [], []
    for dataset, dimensions in (("sift", 128), ("gist", 960)):
        directory = args.panels_root / dataset
        pca = ref.read_panel(directory / "pca_full.fvecs", dimensions)
        residual = ref.read_panel(directory / "residual_nlist1024_full.fvecs", dimensions)
        for file in (directory / "pca_full.fvecs", directory / "residual_nlist1024_full.fvecs",
                     directory / "STAGE_SOURCE.txt"):
            hashes.append({"path": str(file.resolve()), "sha256": sha256(file)})
        for fold, fit_slice, eval_slice in (
            ("A_TO_B", slice(0, 8192), slice(8192, 16384)),
            ("B_TO_A", slice(8192, 16384), slice(0, 8192))):
            plan = ref.saq_plan(pca[fit_slice].var(axis=0))
            payload, factors, total = ref.plan_bits(plan)
            if total > 4 * dimensions + 64:
                raise AssertionError("planner exceeds SAQ byte budget")
            result = run_fold(residual[fit_slice], residual[eval_slice], plan)
            losses, chosen, fitted_curves, rotation_records = result
            identity = {"dataset": dataset, "dimensions": dimensions, "fold": fold}
            allocations.extend(dict(identity, **row) for row in chosen)
            curves.extend(dict(identity, **row) for row in fitted_curves)
            rotations.extend(dict(identity, **row) for row in rotation_records)
            scalar = {}
            arrays = {}
            for (rotation, allocation), metrics in losses.items():
                rows = [row for row in chosen if row["rotation"] == rotation
                        and row["allocation"] == allocation]
                actual_payload = 2 * sum(row["bits_per_coordinate"] for row in rows)
                if actual_payload != payload:
                    raise AssertionError("unequal vector payload")
                scalar[rotation, allocation] = float(metrics["rescaled_sse"].mean())
                summaries.append(dict(identity, rotation=rotation, allocation=allocation,
                    plan=ref.format_plan(plan), payload_bits=payload, factor_bits=factors,
                    vector_total_bytes=total // 8,
                    allocation_metadata_bytes=len(rows) if allocation == "ADAPTIVE" else 0,
                    changed_pairs=sum(r["bits_per_coordinate"] != r["original_bits"] for r in rows),
                    **{key + "_per_vector": float(value.mean()) for key, value in metrics.items()}))
                for key, value in metrics.items():
                    arrays[f"{rotation}_{allocation}_{key}"] = value
            iu, ia = scalar["IDENTITY", "UNIFORM"], scalar["IDENTITY", "ADAPTIVE"]
            qu, qa = scalar["QR", "UNIFORM"], scalar["QR", "ADAPTIVE"]
            contrasts.append(dict(identity,
                allocation_gain_identity_pct=gain(ia, iu), allocation_gain_qr_pct=gain(qa, qu),
                identity_uniform_vs_qr_uniform_pct=gain(iu, qu),
                identity_adaptive_vs_qr_uniform_pct=gain(ia, qu),
                identity_adaptive_vs_qr_adaptive_pct=gain(ia, qa),
                extra_absolute_allocation_benefit_without_qr=(iu-ia)-(qu-qa)))
            np.savez_compressed(args.output / f"{dataset}_{fold}_per_vector.npz", **arrays)
            # Persist after each completed fold so interrupted runs remain inspectable.
            for name, rows in (("summary", summaries), ("contrasts", contrasts),
                               ("allocations", allocations), ("fit_curves", curves),
                               ("rotations", rotations), ("input_hashes", hashes)):
                tsv(args.output / f"{name}.tsv", rows)
            print(f"{dataset} {fold}: identity allocation gain {gain(ia, iu):.6f}%; "
                  f"identity-adaptive vs QR-uniform {gain(ia, qu):.6f}%", flush=True)
    if len(summaries) != 16 or len(contrasts) != 4:
        raise AssertionError("incomplete 2x2 result grid")
    supported = all(row["allocation_gain_identity_pct"] >= 5 for row in contrasts)
    competitive = all(row["identity_adaptive_vs_qr_uniform_pct"] >= 5 for row in contrasts)
    tsv(args.output / "metadata.tsv", [
        {"key": k, "value": v} for k, v in {
            "reference_commit": SOURCE_COMMIT, "python": platform.python_version(),
            "numpy": np.__version__, "upstream": "full PCA retained; fixed nlist1024 residuals",
            "within_segment_identity": "no random rotation; no local PCA; no reordering",
            "pairs": "adjacent; equal width within pair; 1..11 bits per coordinate",
            "adaptive_fit_objective": "nearest lattice SSE proxy; fit-only",
            "evaluation": "actual six-round adjusted codes; CAQ-rescaled squared error",
            "factor_budget": "64 bits per positive segment; payload+factors equal across arms",
            "implementation": "float64 encoder prototype; production bitwise parity not established",
            "rotation": "frozen Gaussian-QR seed20260903; not every production rotation",
            "shared_metadata": "adaptive one uint8 per positive coordinate pair; outside vector payload",
            "sampling": "reused historical rows; not independent final test",
            "status": "COMPLETE_ENCODER_DIAGNOSTIC",
            "allocation_identity_all4_ge5pct": supported,
            "identity_adaptive_vs_qr_uniform_all4_ge5pct": competitive,
            "claim_limit": "not oracle; no Recall/QPS; no general impossibility or novelty claim",
            "cpu_seconds": time.process_time()-started_cpu,
            "wall_seconds": time.monotonic()-started_wall,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            "runner_sha256": sha256(__file__),
            "reference_sha256": sha256(Path(ref.__file__)),
        }.items()])
    (args.output / "STATUS.txt").write_text("COMPLETE_ENCODER_DIAGNOSTIC\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        raise
