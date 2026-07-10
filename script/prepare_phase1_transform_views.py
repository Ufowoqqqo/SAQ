#!/usr/bin/env python3
"""Materialize the query-unaware full-dimensional transform controls for Phase 1.

The current ``gist_sample50k`` artifact contains raw and PCA-transformed base and
query vectors, but only PCA-space IVF centroids.  This tool first recovers the
historical affine PCA map from paired base rows with orthogonal Procrustes.  It
will not invert the PCA centroids until a disjoint base validation set (and the
paired query artifact) satisfy explicit reconstruction thresholds.

Every generated view uses one dataset-level affine orthogonal transform and the
same recovered raw IVF codebook and cluster assignments.  Outputs retain the
ordinary fvecs/ivecs representation expected by SAQ; no persisted-index format
is introduced or changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import struct
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


MANIFEST_SCHEMA_VERSION = 1
OPERATOR_SCHEMA_VERSION = 1
DEFAULT_DATASET = "gist_sample50k"
DEFAULT_K = 512
DEFAULT_RANDOM_SEEDS = (20260710,)
DEFAULT_VIEWS = ("identity", "current_pca", "residual_pca", "random_orthogonal")
VALID_VIEWS = frozenset(DEFAULT_VIEWS)
MAX_ISOMETRY_RELATIVE_L2_ERROR = 1e-5
DEFAULT_PREFIX_DIMS = (64, 256, 576, 832, 960)


@dataclass(frozen=True)
class RecoveryResult:
    mean: np.ndarray
    operator: np.ndarray
    fit_indices: np.ndarray
    validation_indices: np.ndarray
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class ViewSpec:
    kind: str
    name: str
    operator: np.ndarray
    apply_mean: np.ndarray
    fit_metadata: dict[str, Any]
    seed: int | None = None
    fit_mean: np.ndarray | None = None
    eigenvalues: np.ndarray | None = None
    reference_base: Path | None = None
    reference_query: Path | None = None


class FileHashCache:
    """Avoid hashing the same large source through several view symlinks."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, int, int], str] = {}

    def sha256(self, path: Path) -> str:
        resolved = path.resolve(strict=True)
        stat = resolved.stat()
        key = (str(resolved), stat.st_size, stat.st_mtime_ns)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        digest = hashlib.sha256()
        with resolved.open("rb") as handle:
            for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(block)
        value = digest.hexdigest()
        self._cache[key] = value
        return value


def sha256_array(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(struct.pack("<I", array.ndim))
    for size in array.shape:
        digest.update(struct.pack("<Q", int(size)))
    digest.update(array.view(np.uint8))
    return digest.hexdigest()


def read_vecs_shape(path: Path) -> tuple[int, int]:
    size = path.stat().st_size
    if size < 4:
        raise ValueError(f"{path} is too small to contain a vecs dimension")
    with path.open("rb") as handle:
        dim = struct.unpack("<i", handle.read(4))[0]
    if dim <= 0:
        raise ValueError(f"{path} has invalid vecs dimension {dim}")
    record_bytes = 4 + dim * 4
    if size % record_bytes != 0:
        raise ValueError(
            f"{path} size {size} is not a multiple of record size {record_bytes}"
        )
    return size // record_bytes, dim


def validate_vecs_headers(path: Path, count: int, dim: int, chunk_rows: int) -> None:
    records = np.memmap(path, dtype=np.int32, mode="r", shape=(count, dim + 1))
    for begin in range(0, count, chunk_rows):
        end = min(begin + chunk_rows, count)
        if not np.all(records[begin:end, 0] == dim):
            raise ValueError(f"{path} contains inconsistent vecs dimension headers")


def open_fvecs(path: Path) -> np.ndarray:
    count, dim = read_vecs_shape(path)
    records = np.memmap(path, dtype=np.float32, mode="r", shape=(count, dim + 1))
    return records[:, 1:]


def open_ivecs(path: Path) -> np.ndarray:
    count, dim = read_vecs_shape(path)
    records = np.memmap(path, dtype=np.int32, mode="r", shape=(count, dim + 1))
    return records[:, 1:]


def write_fvecs(path: Path, values: np.ndarray, chunk_rows: int) -> None:
    if values.ndim != 2:
        raise ValueError("fvecs values must be a two-dimensional matrix")
    path.parent.mkdir(parents=True, exist_ok=True)
    count, dim = values.shape
    with path.open("wb") as handle:
        for begin in range(0, count, chunk_rows):
            end = min(begin + chunk_rows, count)
            records = np.empty((end - begin, dim + 1), dtype=np.float32)
            records[:, 1:] = np.asarray(values[begin:end], dtype=np.float32)
            records.view(np.int32)[:, 0] = dim
            records.tofile(handle)


def write_ivecs(path: Path, values: np.ndarray, chunk_rows: int) -> None:
    if values.ndim != 2:
        raise ValueError("ivecs values must be a two-dimensional matrix")
    path.parent.mkdir(parents=True, exist_ok=True)
    count, dim = values.shape
    with path.open("wb") as handle:
        for begin in range(0, count, chunk_rows):
            end = min(begin + chunk_rows, count)
            records = np.empty((end - begin, dim + 1), dtype=np.int32)
            records[:, 0] = dim
            records[:, 1:] = np.asarray(values[begin:end], dtype=np.int32)
            records.tofile(handle)


def write_transformed_fvecs(
    path: Path,
    values: np.ndarray,
    mean: np.ndarray,
    operator: np.ndarray,
    chunk_rows: int,
) -> None:
    if values.ndim != 2 or values.shape[1] != operator.shape[0]:
        raise ValueError("transform input and operator dimensions do not match")
    if operator.shape[0] != operator.shape[1] or mean.shape != (operator.shape[0],):
        raise ValueError("a full-dimensional square operator and one mean are required")
    path.parent.mkdir(parents=True, exist_ok=True)
    count, dim = values.shape
    with path.open("wb") as handle:
        for begin in range(0, count, chunk_rows):
            end = min(begin + chunk_rows, count)
            projected = (np.asarray(values[begin:end], dtype=np.float64) - mean) @ operator
            records = np.empty((end - begin, dim + 1), dtype=np.float32)
            records[:, 1:] = projected.astype(np.float32, copy=False)
            records.view(np.int32)[:, 0] = dim
            records.tofile(handle)


def evenly_spaced_indices(count: int, requested: int) -> np.ndarray:
    if requested <= 0 or requested > count:
        raise ValueError(f"requested row count {requested} must be in [1, {count}]")
    indices = np.floor(
        (np.arange(requested, dtype=np.float64) + 0.5) * count / requested
    ).astype(np.int64)
    if np.unique(indices).size != requested:
        raise AssertionError("evenly spaced selection unexpectedly produced duplicates")
    return indices


def mapping_error_metrics(
    raw: np.ndarray,
    transformed: np.ndarray,
    indices: np.ndarray,
    mean: np.ndarray,
    operator: np.ndarray,
) -> dict[str, float]:
    raw_rows = np.asarray(raw[indices], dtype=np.float64)
    transformed_rows = np.asarray(transformed[indices], dtype=np.float64)
    predicted = (raw_rows - mean) @ operator
    error = predicted - transformed_rows
    denominator = max(float(np.linalg.norm(transformed_rows, ord="fro")), 1e-300)
    return {
        "relative_frobenius_error": float(np.linalg.norm(error, ord="fro") / denominator),
        "max_absolute_error": float(np.max(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(np.square(error)))),
    }


def all_row_mapping_error_metrics(
    raw: np.ndarray,
    transformed: np.ndarray,
    mean: np.ndarray,
    operator: np.ndarray,
    chunk_rows: int,
) -> dict[str, float]:
    squared_error = 0.0
    squared_reference = 0.0
    max_absolute_error = 0.0
    value_count = 0
    for begin in range(0, raw.shape[0], chunk_rows):
        end = min(begin + chunk_rows, raw.shape[0])
        raw_rows = np.asarray(raw[begin:end], dtype=np.float64)
        reference = np.asarray(transformed[begin:end], dtype=np.float64)
        error = (raw_rows - mean) @ operator - reference
        squared_error += float(np.sum(np.square(error), dtype=np.float64))
        squared_reference += float(np.sum(np.square(reference), dtype=np.float64))
        max_absolute_error = max(max_absolute_error, float(np.max(np.abs(error))))
        value_count += error.size
    return {
        "relative_frobenius_error": float(
            np.sqrt(squared_error / max(squared_reference, 1e-300))
        ),
        "max_absolute_error": max_absolute_error,
        "rmse": float(np.sqrt(squared_error / max(value_count, 1))),
    }


def require_mapping_thresholds(
    label: str,
    metrics: dict[str, float],
    max_relative_frobenius_error: float,
    max_absolute_error: float,
) -> None:
    if metrics["relative_frobenius_error"] > max_relative_frobenius_error:
        raise ValueError(
            f"{label} Procrustes relative Frobenius error "
            f"{metrics['relative_frobenius_error']:.6e} exceeds threshold "
            f"{max_relative_frobenius_error:.6e}; refusing to invert PCA centroids"
        )
    if metrics["max_absolute_error"] > max_absolute_error:
        raise ValueError(
            f"{label} Procrustes max absolute error "
            f"{metrics['max_absolute_error']:.6e} exceeds threshold "
            f"{max_absolute_error:.6e}; refusing to invert PCA centroids"
        )


def recover_affine_orthogonal_transform(
    raw_base: np.ndarray,
    pca_base: np.ndarray,
    raw_query: np.ndarray,
    pca_query: np.ndarray,
    fit_rows: int,
    validation_rows: int,
    max_relative_frobenius_error: float,
    max_absolute_error: float,
    chunk_rows: int,
) -> RecoveryResult:
    if raw_base.shape != pca_base.shape:
        raise ValueError("paired raw/PCA base matrices must have identical shapes")
    if raw_query.shape != pca_query.shape or raw_query.shape[1] != raw_base.shape[1]:
        raise ValueError("paired raw/PCA query matrices must match the base dimension")
    count, dim = raw_base.shape
    if fit_rows < dim + 1:
        raise ValueError(
            f"Procrustes needs at least D+1={dim + 1} fit rows; received {fit_rows}"
        )
    if fit_rows + validation_rows > count:
        raise ValueError("fit and held-out validation rows must be disjoint within base")

    fit_indices = evenly_spaced_indices(count, fit_rows)
    available_mask = np.ones(count, dtype=bool)
    available_mask[fit_indices] = False
    available = np.flatnonzero(available_mask)
    validation_indices = available[evenly_spaced_indices(available.size, validation_rows)]

    fit_raw = np.asarray(raw_base[fit_indices], dtype=np.float64)
    fit_pca = np.asarray(pca_base[fit_indices], dtype=np.float64)
    raw_center = fit_raw.mean(axis=0)
    pca_center = fit_pca.mean(axis=0)
    cross = (fit_raw - raw_center).T @ (fit_pca - pca_center)
    left, singular_values, right_t = np.linalg.svd(cross, full_matrices=False)
    operator = left @ right_t
    mean = raw_center - pca_center @ operator.T

    rank_threshold = (
        np.finfo(np.float64).eps * max(cross.shape) * max(float(singular_values[0]), 1.0)
    )
    numerical_rank = int(np.count_nonzero(singular_values > rank_threshold))
    if numerical_rank != dim:
        raise ValueError(
            f"paired Procrustes fit is rank deficient ({numerical_rank}/{dim}); "
            "the full-D historical operator is not identifiable"
        )

    fit_metrics = mapping_error_metrics(
        raw_base, pca_base, fit_indices, mean, operator
    )
    validation_metrics = mapping_error_metrics(
        raw_base, pca_base, validation_indices, mean, operator
    )
    query_metrics = all_row_mapping_error_metrics(
        raw_query, pca_query, mean, operator, chunk_rows
    )
    require_mapping_thresholds(
        "held-out base",
        validation_metrics,
        max_relative_frobenius_error,
        max_absolute_error,
    )
    require_mapping_thresholds(
        "paired query artifact",
        query_metrics,
        max_relative_frobenius_error,
        max_absolute_error,
    )

    identity = np.eye(dim, dtype=np.float64)
    orthogonality_error = float(
        np.linalg.norm(operator.T @ operator - identity, ord="fro")
    )
    sign, log_abs_determinant = np.linalg.slogdet(operator)
    diagnostics: dict[str, Any] = {
        "method": "centered orthogonal Procrustes on evenly spaced paired base rows",
        "fit_rows": fit_rows,
        "fit_indices_sha256": sha256_array(fit_indices),
        "heldout_rows": validation_rows,
        "heldout_indices_sha256": sha256_array(validation_indices),
        "fit_error": fit_metrics,
        "heldout_error": validation_metrics,
        "query_artifact_error": query_metrics,
        "thresholds": {
            "max_relative_frobenius_error": max_relative_frobenius_error,
            "max_absolute_error": max_absolute_error,
        },
        "cross_covariance_numerical_rank": numerical_rank,
        "cross_singular_value_max": float(singular_values[0]),
        "cross_singular_value_min": float(singular_values[-1]),
        "operator_orthogonality_frobenius_error": orthogonality_error,
        "operator_determinant_sign": float(sign),
        "operator_log_abs_determinant": float(log_abs_determinant),
        "operator_sha256": sha256_array(operator),
        "mean_sha256": sha256_array(mean),
    }
    return RecoveryResult(mean, operator, fit_indices, validation_indices, diagnostics)


def compute_mean_and_population_covariance(
    values: np.ndarray, chunk_rows: int
) -> tuple[np.ndarray, np.ndarray]:
    count, dim = values.shape
    total = np.zeros(dim, dtype=np.float64)
    for begin in range(0, count, chunk_rows):
        end = min(begin + chunk_rows, count)
        total += np.asarray(values[begin:end], dtype=np.float64).sum(
            axis=0, dtype=np.float64
        )
    mean = total / float(count)
    covariance = np.zeros((dim, dim), dtype=np.float64)
    for begin in range(0, count, chunk_rows):
        end = min(begin + chunk_rows, count)
        centered = np.asarray(values[begin:end], dtype=np.float64) - mean
        covariance += centered.T @ centered
    covariance /= float(count)
    covariance = (covariance + covariance.T) * 0.5
    return mean, covariance


def compute_residual_mean_and_population_covariance(
    base: np.ndarray,
    centroids: np.ndarray,
    cluster_ids: np.ndarray,
    chunk_rows: int,
) -> tuple[np.ndarray, np.ndarray]:
    count, dim = base.shape
    total = np.zeros(dim, dtype=np.float64)
    for begin in range(0, count, chunk_rows):
        end = min(begin + chunk_rows, count)
        residuals = (
            np.asarray(base[begin:end], dtype=np.float64)
            - centroids[cluster_ids[begin:end]]
        )
        total += residuals.sum(axis=0, dtype=np.float64)
    mean = total / float(count)
    covariance = np.zeros((dim, dim), dtype=np.float64)
    for begin in range(0, count, chunk_rows):
        end = min(begin + chunk_rows, count)
        residuals = (
            np.asarray(base[begin:end], dtype=np.float64)
            - centroids[cluster_ids[begin:end]]
            - mean
        )
        covariance += residuals.T @ residuals
    covariance /= float(count)
    covariance = (covariance + covariance.T) * 0.5
    return mean, covariance


def orient_components(components: np.ndarray) -> np.ndarray:
    oriented = components.copy()
    for column in range(oriented.shape[1]):
        pivot = int(np.argmax(np.abs(oriented[:, column])))
        if oriented[pivot, column] < 0.0:
            oriented[:, column] *= -1.0
    return oriented


def eigendecompose_descending(covariance: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    return eigenvalues[order], orient_components(eigenvectors[:, order])


def random_orthogonal_matrix(dim: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    matrix = rng.standard_normal((dim, dim))
    q, r = np.linalg.qr(matrix)
    signs = np.sign(np.diag(r))
    signs[signs == 0.0] = 1.0
    q *= signs
    return q


def fixed_probe_clusters(
    raw_query: np.ndarray,
    raw_centroids: np.ndarray,
    query_count: int,
    nprobe: int,
) -> np.ndarray:
    if query_count > raw_query.shape[0]:
        raise ValueError(
            f"fixed probe requires first {query_count} queries, but only "
            f"{raw_query.shape[0]} are available"
        )
    if nprobe <= 0 or nprobe > raw_centroids.shape[0]:
        raise ValueError("nprobe must be positive and no larger than the centroid count")
    queries = np.asarray(raw_query[:query_count], dtype=np.float64)
    centroids = np.asarray(raw_centroids, dtype=np.float64)
    distances = (
        np.sum(np.square(queries), axis=1)[:, None]
        + np.sum(np.square(centroids), axis=1)[None, :]
        - 2.0 * (queries @ centroids.T)
    )
    return np.argsort(distances, axis=1, kind="stable")[:, :nprobe].astype(np.int32)


def covariance_diagnostics(covariance: np.ndarray) -> dict[str, Any]:
    diagonal = np.diag(covariance).copy()
    trace = float(diagonal.sum())
    off_diagonal = covariance - np.diag(diagonal)
    covariance_fro = float(np.linalg.norm(covariance, ord="fro"))
    dim = covariance.shape[0]
    prefix_dims = sorted({value for value in DEFAULT_PREFIX_DIMS if value <= dim} | {dim})
    block_sums = [
        float(diagonal[begin : min(begin + 64, dim)].sum())
        for begin in range(0, dim, 64)
    ]
    return {
        "dimension": dim,
        "population_denominator": "N",
        "trace": trace,
        "covariance_frobenius_norm": covariance_fro,
        "off_diagonal_frobenius_norm": float(np.linalg.norm(off_diagonal, ord="fro")),
        "off_diagonal_to_total_frobenius_ratio": float(
            np.linalg.norm(off_diagonal, ord="fro") / max(covariance_fro, 1e-300)
        ),
        "variance_min": float(diagonal.min()),
        "variance_max": float(diagonal.max()),
        "variance_mean": float(diagonal.mean()),
        "variance_first_16": diagonal[:16].tolist(),
        "variance_sha256": sha256_array(diagonal),
        "block64_variance_sums": block_sums,
        "prefix_variance_fraction": {
            str(prefix): float(diagonal[:prefix].sum() / max(trace, 1e-300))
            for prefix in prefix_dims
        },
    }


def operator_diagnostics(operator: np.ndarray) -> dict[str, Any]:
    dim = operator.shape[0]
    identity = np.eye(dim, dtype=np.float64)
    residual = operator.T @ operator - identity
    sign, log_abs_determinant = np.linalg.slogdet(operator)
    return {
        "dimension": dim,
        "dtype": str(operator.dtype),
        "bytes": int(operator.nbytes),
        "sha256": sha256_array(operator),
        "orthogonality_frobenius_error": float(np.linalg.norm(residual, ord="fro")),
        "orthogonality_max_absolute_error": float(np.max(np.abs(residual))),
        "determinant_sign": float(sign),
        "log_abs_determinant": float(log_abs_determinant),
    }


def pairwise_isometry_diagnostics(
    raw_base: np.ndarray, transformed_base: np.ndarray, requested_pairs: int
) -> dict[str, Any]:
    pair_count = min(requested_pairs, raw_base.shape[0] // 2)
    indices = evenly_spaced_indices(raw_base.shape[0], 2 * pair_count)
    raw_rows = np.asarray(raw_base[indices], dtype=np.float64).reshape(
        pair_count, 2, raw_base.shape[1]
    )
    transformed_rows = np.asarray(transformed_base[indices], dtype=np.float64).reshape(
        pair_count, 2, transformed_base.shape[1]
    )
    raw_squared = np.sum(np.square(raw_rows[:, 0] - raw_rows[:, 1]), axis=1)
    transformed_squared = np.sum(
        np.square(transformed_rows[:, 0] - transformed_rows[:, 1]), axis=1
    )
    error = transformed_squared - raw_squared
    relative = np.abs(error) / np.maximum(raw_squared, 1e-300)
    return {
        "sample_pairs": pair_count,
        "row_indices_sha256": sha256_array(indices),
        "squared_distance_relative_l2_error": float(
            np.linalg.norm(error) / max(float(np.linalg.norm(raw_squared)), 1e-300)
        ),
        "squared_distance_max_absolute_error": float(np.max(np.abs(error))),
        "squared_distance_relative_error_mean": float(relative.mean()),
        "squared_distance_relative_error_p99": float(np.quantile(relative, 0.99)),
        "squared_distance_relative_error_max": float(relative.max()),
    }


def probe_agreement_diagnostics(
    transformed_query: np.ndarray,
    transformed_centroids: np.ndarray,
    fixed_probes: np.ndarray,
) -> dict[str, Any]:
    query_count, nprobe = fixed_probes.shape
    queries = np.asarray(transformed_query[:query_count], dtype=np.float64)
    centroids = np.asarray(transformed_centroids, dtype=np.float64)
    distances = (
        np.sum(np.square(queries), axis=1)[:, None]
        + np.sum(np.square(centroids), axis=1)[None, :]
        - 2.0 * (queries @ centroids.T)
    )
    observed = np.argsort(distances, axis=1, kind="stable")[:, :nprobe]
    return {
        "queries": query_count,
        "nprobe": nprobe,
        "rows_with_exact_order": int(np.count_nonzero(np.all(observed == fixed_probes, axis=1))),
        "exact_order_fraction": float(np.mean(np.all(observed == fixed_probes, axis=1))),
        "id_position_agreement_fraction": float(np.mean(observed == fixed_probes)),
        "observed_probe_sha256": sha256_array(observed.astype(np.int32)),
        "fixed_probe_sha256": sha256_array(fixed_probes),
    }


def require_view_validation(
    view_name: str,
    isometry: Mapping[str, Any],
    probe_agreement: Mapping[str, Any],
) -> None:
    relative_l2_error = float(isometry["squared_distance_relative_l2_error"])
    if relative_l2_error > MAX_ISOMETRY_RELATIVE_L2_ERROR:
        raise ValueError(
            f"{view_name} squared-distance isometry error {relative_l2_error:.6e} "
            f"exceeds {MAX_ISOMETRY_RELATIVE_L2_ERROR:.6e}"
        )
    query_count = int(probe_agreement["queries"])
    exact_order_rows = int(probe_agreement["rows_with_exact_order"])
    if exact_order_rows != query_count:
        raise ValueError(
            f"{view_name} changes fixed-probe order for "
            f"{query_count - exact_order_rows}/{query_count} queries"
        )


def vector_file_identity(
    path: Path, kind: str, hash_cache: FileHashCache
) -> dict[str, Any]:
    count, dim = read_vecs_shape(path)
    stat = path.resolve(strict=True).stat()
    return {
        "path": str(path.resolve(strict=True)),
        "format": kind,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "count": count,
        "dimension": dim,
        "sha256": hash_cache.sha256(path),
    }


def output_artifact_identity(
    path: Path,
    output_directory: Path,
    artifact_format: str,
    hash_cache: FileHashCache,
    count: int | None = None,
    dim: int | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "relative_path": str(path.relative_to(output_directory)),
        "format": artifact_format,
        "size_bytes": path.stat().st_size,
        "sha256": hash_cache.sha256(path),
        "storage": "symlink" if path.is_symlink() else "materialized",
    }
    if path.is_symlink():
        result["symlink_target"] = str(path.resolve(strict=True))
    if count is not None:
        result["count"] = count
    if dim is not None:
        result["dimension"] = dim
    return result


def create_absolute_symlink(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(source.resolve(strict=True))


def write_operator_npz(path: Path, spec: ViewSpec) -> None:
    payload: dict[str, np.ndarray] = {
        "schema_version": np.asarray(OPERATOR_SCHEMA_VERSION, dtype=np.int64),
        "transform_kind": np.asarray(spec.kind),
        "apply_mean": np.asarray(spec.apply_mean, dtype=np.float64),
        "operator": np.asarray(spec.operator, dtype=np.float64),
    }
    if spec.seed is not None:
        payload["seed"] = np.asarray(spec.seed, dtype=np.int64)
    if spec.fit_mean is not None:
        payload["fit_mean"] = np.asarray(spec.fit_mean, dtype=np.float64)
    if spec.eigenvalues is not None:
        payload["eigenvalues"] = np.asarray(spec.eigenvalues, dtype=np.float64)
    np.savez(path, **payload)


def safe_replace_directory(temp_directory: Path, target: Path, force: bool) -> None:
    if target.exists() or target.is_symlink():
        if not force:
            raise FileExistsError(f"output view already exists: {target}")
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    temp_directory.rename(target)


def materialize_view(
    *,
    spec: ViewSpec,
    output_parent: Path,
    raw_base: np.ndarray,
    raw_query: np.ndarray,
    raw_centroids: np.ndarray,
    raw_covariance: np.ndarray,
    cluster_ids_path: Path,
    fixed_probes: np.ndarray,
    input_identities: dict[str, Any],
    common_provenance: dict[str, Any],
    chunk_rows: int,
    isometry_pairs: int,
    k: int,
    force: bool,
    hash_cache: FileHashCache,
) -> Path:
    output_parent.mkdir(parents=True, exist_ok=True)
    target = output_parent / spec.name
    if (target.exists() or target.is_symlink()) and not force:
        raise FileExistsError(f"output view already exists: {target}")
    temp_directory = Path(
        tempfile.mkdtemp(prefix=f".{spec.name}.tmp-", dir=str(output_parent))
    )
    timings: dict[str, float] = {}
    try:
        base_path = temp_directory / f"{spec.name}_base.fvecs"
        query_path = temp_directory / f"{spec.name}_query.fvecs"
        centroid_path = temp_directory / f"{spec.name}_centroid_{k}.fvecs"
        variance_path = temp_directory / f"{spec.name}_base.vars.fvecs"
        cluster_ids_output = temp_directory / f"{spec.name}_cluster_id_{k}.ivecs"
        operator_path = temp_directory / f"{spec.name}_transform.npz"
        probe_path = temp_directory / (
            f"{spec.name}_fixed_probe_clusters_q{fixed_probes.shape[0]}_"
            f"nprobe{fixed_probes.shape[1]}.ivecs"
        )
        manifest_path = temp_directory / f"{spec.name}_manifest.json"

        start = time.perf_counter()
        if spec.reference_base is None:
            write_transformed_fvecs(
                base_path, raw_base, spec.apply_mean, spec.operator, chunk_rows
            )
            base_storage = "materialized transformed fvecs"
        else:
            create_absolute_symlink(spec.reference_base, base_path)
            base_storage = "validated reference to historical transformed fvecs"
        timings["base_output_seconds"] = time.perf_counter() - start

        start = time.perf_counter()
        if spec.reference_query is None:
            write_transformed_fvecs(
                query_path, raw_query, spec.apply_mean, spec.operator, chunk_rows
            )
            query_storage = "materialized transformed fvecs"
        else:
            create_absolute_symlink(spec.reference_query, query_path)
            query_storage = "validated reference to historical transformed fvecs"
        timings["query_output_seconds"] = time.perf_counter() - start

        start = time.perf_counter()
        write_transformed_fvecs(
            centroid_path, raw_centroids, spec.apply_mean, spec.operator, chunk_rows
        )
        timings["centroid_output_seconds"] = time.perf_counter() - start

        transformed_covariance = spec.operator.T @ raw_covariance @ spec.operator
        transformed_covariance = (transformed_covariance + transformed_covariance.T) * 0.5
        transformed_variance = np.diag(transformed_covariance).copy()
        start = time.perf_counter()
        write_fvecs(variance_path, transformed_variance.reshape(1, -1), chunk_rows)
        timings["variance_output_seconds"] = time.perf_counter() - start

        start = time.perf_counter()
        create_absolute_symlink(cluster_ids_path, cluster_ids_output)
        timings["cluster_id_reference_seconds"] = time.perf_counter() - start

        start = time.perf_counter()
        write_ivecs(probe_path, fixed_probes, chunk_rows)
        timings["fixed_probe_output_seconds"] = time.perf_counter() - start

        start = time.perf_counter()
        write_operator_npz(operator_path, spec)
        timings["operator_output_seconds"] = time.perf_counter() - start

        transformed_base = open_fvecs(base_path)
        transformed_query = open_fvecs(query_path)
        transformed_centroids = open_fvecs(centroid_path)
        isometry = pairwise_isometry_diagnostics(
            raw_base, transformed_base, isometry_pairs
        )
        probe_agreement = probe_agreement_diagnostics(
            transformed_query, transformed_centroids, fixed_probes
        )
        require_view_validation(spec.name, isometry, probe_agreement)

        start = time.perf_counter()
        outputs = {
            "base": output_artifact_identity(
                base_path,
                temp_directory,
                "fvecs",
                hash_cache,
                raw_base.shape[0],
                raw_base.shape[1],
            ),
            "query": output_artifact_identity(
                query_path,
                temp_directory,
                "fvecs",
                hash_cache,
                raw_query.shape[0],
                raw_query.shape[1],
            ),
            "centroids": output_artifact_identity(
                centroid_path,
                temp_directory,
                "fvecs",
                hash_cache,
                raw_centroids.shape[0],
                raw_centroids.shape[1],
            ),
            "variance": output_artifact_identity(
                variance_path,
                temp_directory,
                "fvecs",
                hash_cache,
                1,
                raw_base.shape[1],
            ),
            "cluster_ids": output_artifact_identity(
                cluster_ids_output,
                temp_directory,
                "ivecs",
                hash_cache,
                raw_base.shape[0],
                1,
            ),
            "operator": output_artifact_identity(
                operator_path, temp_directory, "npz", hash_cache
            ),
            "fixed_probe_clusters": output_artifact_identity(
                probe_path,
                temp_directory,
                "ivecs",
                hash_cache,
                fixed_probes.shape[0],
                fixed_probes.shape[1],
            ),
        }
        timings["output_hash_seconds"] = time.perf_counter() - start

        manifest: dict[str, Any] = {
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "view_name": spec.name,
            "research_contract": {
                "metric": "L2",
                "dimension_reduction": False,
                "fit_data": "base/index artifacts only",
                "query_usage": (
                    "paired artifact validation and predeclared first-query probe "
                    "materialization only; never transform/plan selection"
                ),
                "operator_scope": "one dataset-level affine orthogonal transform",
                "plan_scope": "one global SAQ plan per view (created downstream)",
                "cluster_state": "one shared canonical IVF codebook and fixed cluster ids",
                "view_validation": {
                    "max_squared_distance_relative_l2_error": (
                        MAX_ISOMETRY_RELATIVE_L2_ERROR
                    ),
                    "require_exact_fixed_probe_order": True,
                },
            },
            "transform": {
                "kind": spec.kind,
                "input_dimension": raw_base.shape[1],
                "output_dimension": raw_base.shape[1],
                "application": "(row - apply_mean) @ operator",
                "apply_mean_sha256": sha256_array(spec.apply_mean),
                "runtime_state_contract": {
                    "dtype": "float32",
                    "operator_shape": [raw_base.shape[1], raw_base.shape[1]],
                    "mean_shape": [raw_base.shape[1]],
                    "operator_bytes": raw_base.shape[1] * raw_base.shape[1] * 4,
                    "mean_bytes": raw_base.shape[1] * 4,
                    "total_bytes": (
                        raw_base.shape[1] * raw_base.shape[1] * 4
                        + raw_base.shape[1] * 4
                    ),
                    "dense_mac_per_raw_query": raw_base.shape[1] * raw_base.shape[1],
                },
                "seed": spec.seed,
                "base_storage": base_storage,
                "query_storage": query_storage,
                "fit": spec.fit_metadata,
                "operator_diagnostics": operator_diagnostics(spec.operator),
            },
            "inputs": input_identities,
            "shared_provenance": common_provenance,
            "outputs": outputs,
            "diagnostics": {
                "isometry": isometry,
                "base_covariance_after_transform": covariance_diagnostics(
                    transformed_covariance
                ),
                "fixed_probe_recomputed_in_view": probe_agreement,
            },
            "timings_seconds": timings,
        }
        start = time.perf_counter()
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
        timings["manifest_write_seconds"] = time.perf_counter() - start

        # Timings are part of the manifest; rewrite once after measuring the write.
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")

        del transformed_base, transformed_query, transformed_centroids
        safe_replace_directory(temp_directory, target, force)
        return target
    except Exception:
        shutil.rmtree(temp_directory, ignore_errors=True)
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recover the current full-D PCA artifact and materialize Phase-1 "
            "identity, current-PCA, residual-PCA, and random-orthogonal SAQ views."
        )
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--raw-base", type=Path)
    parser.add_argument("--pca-base", type=Path)
    parser.add_argument("--raw-query", type=Path)
    parser.add_argument("--pca-query", type=Path)
    parser.add_argument("--pca-centroids", type=Path)
    parser.add_argument("--cluster-ids", type=Path)
    parser.add_argument("--pca-vars", type=Path)
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--output-parent", type=Path, default=Path("data"))
    parser.add_argument("--view-prefix")
    parser.add_argument(
        "--random-seeds", type=int, nargs="+", default=list(DEFAULT_RANDOM_SEEDS)
    )
    parser.add_argument(
        "--views",
        nargs="+",
        choices=sorted(VALID_VIEWS),
        default=list(DEFAULT_VIEWS),
        help=(
            "Transform views to materialize. Phase 1b uses only "
            "current_pca residual_pca."
        ),
    )
    parser.add_argument(
        "--ivf-provenance-json",
        type=Path,
        help="Optional query-unaware IVF construction record copied into each manifest.",
    )
    parser.add_argument("--chunk-rows", type=int, default=4096)
    parser.add_argument("--procrustes-fit-rows", type=int, default=8192)
    parser.add_argument("--procrustes-validation-rows", type=int, default=4096)
    parser.add_argument("--max-procrustes-relative-fro", type=float, default=1e-5)
    parser.add_argument("--max-procrustes-max-abs", type=float, default=1e-4)
    parser.add_argument("--probe-query-count", type=int, default=128)
    parser.add_argument("--nprobe", type=int, default=16)
    parser.add_argument("--isometry-pairs", type=int, default=256)
    parser.add_argument(
        "--materialize-current-pca-base-query",
        action="store_true",
        help="rewrite current-PCA base/query instead of referencing validated inputs",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def resolve_input_paths(args: argparse.Namespace) -> dict[str, Path | None]:
    input_directory = args.input_dir or Path("data") / args.dataset
    paths: dict[str, Path | None] = {
        "raw_base": args.raw_base
        or input_directory / f"{args.dataset}_base.fvecs",
        "pca_base": args.pca_base
        or input_directory / f"{args.dataset}_base_pca.fvecs",
        "raw_query": args.raw_query
        or input_directory / f"{args.dataset}_query.fvecs",
        "pca_query": args.pca_query
        or input_directory / f"{args.dataset}_query_pca.fvecs",
        "pca_centroids": args.pca_centroids
        or input_directory / f"{args.dataset}_centroid_{args.k}_pca.fvecs",
        "cluster_ids": args.cluster_ids
        or input_directory / f"{args.dataset}_cluster_id_{args.k}.ivecs",
    }
    pca_vars = args.pca_vars or input_directory / f"{args.dataset}_base_pca.vars.fvecs"
    paths["pca_vars"] = pca_vars if pca_vars.exists() else None
    return paths


def environment_provenance() -> dict[str, Any]:
    blas_info = np.__config__.get_info("blas_opt_info")
    return {
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "byteorder": sys.byteorder,
        "blas_opt_info": {
            key: value if isinstance(value, (str, int, float, list, bool)) else str(value)
            for key, value in blas_info.items()
        },
    }


def run(args: argparse.Namespace) -> list[Path]:
    if args.k <= 0 or args.chunk_rows <= 0 or args.isometry_pairs <= 0:
        raise ValueError("K, chunk rows, and isometry pairs must be positive")
    if args.max_procrustes_relative_fro <= 0.0 or args.max_procrustes_max_abs <= 0.0:
        raise ValueError("Procrustes validation thresholds must be positive")
    if len(set(args.random_seeds)) != len(args.random_seeds):
        raise ValueError("random seeds must be unique")
    if len(set(args.views)) != len(args.views):
        raise ValueError("views must be unique")
    if args.ivf_provenance_json is not None and not args.ivf_provenance_json.is_file():
        raise FileNotFoundError(
            f"missing IVF provenance JSON: {args.ivf_provenance_json}"
        )

    paths = resolve_input_paths(args)
    required_paths = {key: value for key, value in paths.items() if key != "pca_vars"}
    for label, path in required_paths.items():
        assert path is not None
        if not path.is_file():
            raise FileNotFoundError(f"missing {label} input: {path}")

    raw_base_path = paths["raw_base"]
    pca_base_path = paths["pca_base"]
    raw_query_path = paths["raw_query"]
    pca_query_path = paths["pca_query"]
    pca_centroids_path = paths["pca_centroids"]
    cluster_ids_path = paths["cluster_ids"]
    assert all(
        path is not None
        for path in (
            raw_base_path,
            pca_base_path,
            raw_query_path,
            pca_query_path,
            pca_centroids_path,
            cluster_ids_path,
        )
    )

    raw_base_count, dim = read_vecs_shape(raw_base_path)
    expected_shapes = {
        "pca base": (pca_base_path, raw_base_count, dim),
        "raw query": (raw_query_path, None, dim),
        "pca query": (pca_query_path, None, dim),
        "PCA centroids": (pca_centroids_path, args.k, dim),
        "cluster ids": (cluster_ids_path, raw_base_count, 1),
    }
    for label, (path, expected_count, expected_dim) in expected_shapes.items():
        count, file_dim = read_vecs_shape(path)
        if expected_count is not None and count != expected_count:
            raise ValueError(
                f"{label} count {count} does not match expected {expected_count}"
            )
        if file_dim != expected_dim:
            raise ValueError(
                f"{label} dimension {file_dim} does not match expected {expected_dim}"
            )
    raw_query_count, _ = read_vecs_shape(raw_query_path)
    pca_query_count, _ = read_vecs_shape(pca_query_path)
    if raw_query_count != pca_query_count:
        raise ValueError("raw and PCA query counts do not match")

    for path in required_paths.values():
        assert path is not None
        count, file_dim = read_vecs_shape(path)
        validate_vecs_headers(path, count, file_dim, args.chunk_rows)

    raw_base = open_fvecs(raw_base_path)
    pca_base = open_fvecs(pca_base_path)
    raw_query = open_fvecs(raw_query_path)
    pca_query = open_fvecs(pca_query_path)
    pca_centroids = open_fvecs(pca_centroids_path)
    cluster_ids_matrix = open_ivecs(cluster_ids_path)
    cluster_ids = np.asarray(cluster_ids_matrix[:, 0], dtype=np.int64)
    if cluster_ids.min() < 0 or cluster_ids.max() >= args.k:
        raise ValueError(
            f"cluster ids must lie in [0, {args.k}); observed "
            f"[{cluster_ids.min()}, {cluster_ids.max()}]"
        )

    hash_cache = FileHashCache()
    hash_start = time.perf_counter()
    input_identities: dict[str, Any] = {
        "raw_base": vector_file_identity(raw_base_path, "fvecs", hash_cache),
        "historical_pca_base": vector_file_identity(
            pca_base_path, "fvecs", hash_cache
        ),
        "raw_query": vector_file_identity(raw_query_path, "fvecs", hash_cache),
        "historical_pca_query": vector_file_identity(
            pca_query_path, "fvecs", hash_cache
        ),
        "historical_pca_centroids": vector_file_identity(
            pca_centroids_path, "fvecs", hash_cache
        ),
        "cluster_ids": vector_file_identity(cluster_ids_path, "ivecs", hash_cache),
    }
    if paths["pca_vars"] is not None:
        input_identities["historical_pca_variance"] = vector_file_identity(
            paths["pca_vars"], "fvecs", hash_cache
        )
    historical_ivf_construction: dict[str, Any] | None = None
    if args.ivf_provenance_json is not None:
        with args.ivf_provenance_json.open(encoding="utf-8") as handle:
            historical_ivf_construction = json.load(handle)
        input_identities["historical_ivf_provenance"] = {
            "path": str(args.ivf_provenance_json.resolve(strict=True)),
            "format": "json",
            "bytes": args.ivf_provenance_json.stat().st_size,
            "sha256": hash_cache.sha256(args.ivf_provenance_json),
        }
    input_hash_seconds = time.perf_counter() - hash_start

    recovery_start = time.perf_counter()
    recovery = recover_affine_orthogonal_transform(
        raw_base,
        pca_base,
        raw_query,
        pca_query,
        args.procrustes_fit_rows,
        args.procrustes_validation_rows,
        args.max_procrustes_relative_fro,
        args.max_procrustes_max_abs,
        args.chunk_rows,
    )
    recovery_seconds = time.perf_counter() - recovery_start

    # This inversion happens only after recover_affine_orthogonal_transform has
    # enforced both held-out base and paired-query thresholds.
    inversion_start = time.perf_counter()
    canonical_raw_centroids = (
        np.asarray(pca_centroids, dtype=np.float64) @ recovery.operator.T
        + recovery.mean
    )
    centroid_roundtrip = (
        canonical_raw_centroids - recovery.mean
    ) @ recovery.operator
    centroid_roundtrip_error = centroid_roundtrip - np.asarray(
        pca_centroids, dtype=np.float64
    )
    inversion_seconds = time.perf_counter() - inversion_start

    covariance_start = time.perf_counter()
    raw_mean, raw_covariance = compute_mean_and_population_covariance(
        raw_base, args.chunk_rows
    )
    raw_covariance_seconds = time.perf_counter() - covariance_start

    residual_start = time.perf_counter()
    residual_mean, residual_covariance = compute_residual_mean_and_population_covariance(
        raw_base, canonical_raw_centroids, cluster_ids, args.chunk_rows
    )
    residual_eigenvalues, residual_operator = eigendecompose_descending(
        residual_covariance
    )
    residual_fit_seconds = time.perf_counter() - residual_start

    probe_start = time.perf_counter()
    probes = fixed_probe_clusters(
        raw_query, canonical_raw_centroids, args.probe_query_count, args.nprobe
    )
    probe_seconds = time.perf_counter() - probe_start

    current_covariance = recovery.operator.T @ raw_covariance @ recovery.operator
    current_variance_comparison: dict[str, Any] | None = None
    if paths["pca_vars"] is not None:
        existing_variance = np.asarray(open_fvecs(paths["pca_vars"])[0], dtype=np.float64)
        recovered_variance = np.diag(current_covariance)
        difference = recovered_variance - existing_variance
        current_variance_comparison = {
            "relative_l2_error": float(
                np.linalg.norm(difference)
                / max(float(np.linalg.norm(existing_variance)), 1e-300)
            ),
            "max_absolute_error": float(np.max(np.abs(difference))),
        }

    counts = np.bincount(cluster_ids, minlength=args.k)
    script_path = Path(__file__).resolve(strict=True)
    common_provenance: dict[str, Any] = {
        "script": {
            "path": str(script_path),
            "sha256": hash_cache.sha256(script_path),
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        },
        "environment": environment_provenance(),
        "historical_pca_recovery": recovery.diagnostics,
        "historical_ivf_construction": historical_ivf_construction,
        "canonical_raw_codebook": {
            "method": (
                "inverse affine transform of historical PCA centroids after "
                "held-out recovery gates"
            ),
            "formula": "raw_centroid = pca_centroid @ operator.T + apply_mean",
            "count": args.k,
            "dimension": dim,
            "sha256_float64": sha256_array(canonical_raw_centroids),
            "pca_roundtrip_relative_frobenius_error": float(
                np.linalg.norm(centroid_roundtrip_error, ord="fro")
                / max(float(np.linalg.norm(pca_centroids, ord="fro")), 1e-300)
            ),
            "pca_roundtrip_max_absolute_error": float(
                np.max(np.abs(centroid_roundtrip_error))
            ),
            "cluster_assignment_count_min": int(counts.min()),
            "cluster_assignment_count_max": int(counts.max()),
            "empty_clusters": int(np.count_nonzero(counts == 0)),
        },
        "common_apply_mean": {
            "definition": "recovered historical PCA base mean, shared by every view",
            "sha256": sha256_array(recovery.mean),
            "l2_difference_from_streamed_raw_mean": float(
                np.linalg.norm(recovery.mean - raw_mean)
            ),
        },
        "raw_base_covariance": covariance_diagnostics(raw_covariance),
        "residual_pca_fit": {
            "training_rows": raw_base_count,
            "training_rows_definition": "all base residuals x_i - canonical_centroid[cid_i]",
            "cluster_ids_sha256": input_identities["cluster_ids"]["sha256"],
            "residual_mean_l2_norm": float(np.linalg.norm(residual_mean)),
            "residual_mean_sha256": sha256_array(residual_mean),
            "residual_covariance": covariance_diagnostics(residual_covariance),
            "eigenvalues_first_16": residual_eigenvalues[:16].tolist(),
            "eigenvalues_sha256": sha256_array(residual_eigenvalues),
            "operator_sha256": sha256_array(residual_operator),
        },
        "fixed_probe_clusters": {
            "query_indices": f"first {args.probe_query_count} raw queries",
            "query_index_begin": 0,
            "query_index_end_exclusive": args.probe_query_count,
            "nprobe": args.nprobe,
            "distance": "squared L2 to canonical raw codebook",
            "tie_break": "stable centroid id order",
            "sha256": sha256_array(probes),
        },
        "historical_pca_variance_comparison": current_variance_comparison,
        "shared_timings_seconds": {
            "input_hash": input_hash_seconds,
            "historical_pca_recovery": recovery_seconds,
            "canonical_centroid_inversion": inversion_seconds,
            "raw_covariance": raw_covariance_seconds,
            "residual_pca_fit": residual_fit_seconds,
            "fixed_probe_generation": probe_seconds,
        },
    }

    prefix = args.view_prefix or f"{args.dataset}_phase1"
    existing_base_reference = None if args.materialize_current_pca_base_query else pca_base_path
    existing_query_reference = None if args.materialize_current_pca_base_query else pca_query_path
    identity = np.eye(dim, dtype=np.float64)
    view_specs_by_kind: dict[str, list[ViewSpec]] = {
        "identity": [ViewSpec(
            kind="identity-full",
            name=f"{prefix}_identity",
            operator=identity,
            apply_mean=recovery.mean,
            fit_metadata={
                "method": "identity orientation with the common recovered base mean",
                "training_rows": 0,
            },
        )],
        "current_pca": [ViewSpec(
            kind="current-pca-full-recovered",
            name=f"{prefix}_current_pca",
            operator=recovery.operator,
            apply_mean=recovery.mean,
            fit_metadata={
                "method": "validated historical affine PCA recovery",
                "fit_indices_sha256": recovery.diagnostics["fit_indices_sha256"],
                "heldout_indices_sha256": recovery.diagnostics[
                    "heldout_indices_sha256"
                ],
            },
            reference_base=existing_base_reference,
            reference_query=existing_query_reference,
        )],
        "residual_pca": [ViewSpec(
            kind="global-residual-pca-full",
            name=f"{prefix}_residual_pca",
            operator=residual_operator,
            apply_mean=recovery.mean,
            fit_mean=residual_mean,
            eigenvalues=residual_eigenvalues,
            fit_metadata={
                "method": (
                    "full-D eigendecomposition of population covariance over all "
                    "base residuals relative to the canonical raw codebook"
                ),
                "training_rows": raw_base_count,
                "query_rows": 0,
                "component_orientation": "largest-absolute entry positive",
            },
        )],
        "random_orthogonal": [],
    }
    for seed in args.random_seeds:
        random_start = time.perf_counter()
        random_operator = random_orthogonal_matrix(dim, seed)
        random_seconds = time.perf_counter() - random_start
        view_specs_by_kind["random_orthogonal"].append(
            ViewSpec(
                kind="seeded-random-orthogonal-full",
                name=f"{prefix}_random_seed{seed}",
                operator=random_operator,
                apply_mean=recovery.mean,
                seed=seed,
                fit_metadata={
                    "method": "numpy.default_rng(seed).standard_normal + QR",
                    "training_rows": 0,
                    "generation_seconds": random_seconds,
                    "numpy_version": np.__version__,
                },
            )
        )
    view_specs = [
        spec
        for kind in args.views
        for spec in view_specs_by_kind[kind]
    ]

    targets = [args.output_parent / spec.name for spec in view_specs]
    if not args.force:
        conflicts = [target for target in targets if target.exists() or target.is_symlink()]
        if conflicts:
            raise FileExistsError(
                "refusing to overwrite existing view(s) without --force: "
                + ", ".join(str(path) for path in conflicts)
            )

    generated: list[Path] = []
    for spec in view_specs:
        print(f"Materializing {spec.name} ({spec.kind})", flush=True)
        generated.append(
            materialize_view(
                spec=spec,
                output_parent=args.output_parent,
                raw_base=raw_base,
                raw_query=raw_query,
                raw_centroids=canonical_raw_centroids,
                raw_covariance=raw_covariance,
                cluster_ids_path=cluster_ids_path,
                fixed_probes=probes,
                input_identities=input_identities,
                common_provenance=common_provenance,
                chunk_rows=args.chunk_rows,
                isometry_pairs=args.isometry_pairs,
                k=args.k,
                force=args.force,
                hash_cache=hash_cache,
            )
        )
    return generated


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    generated = run(args)
    print("Generated Phase-1 transform views:")
    for path in generated:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
