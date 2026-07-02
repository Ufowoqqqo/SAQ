#!/usr/bin/env python3
"""Prepare sampled PCA/IVF artifacts for SAQ diagnostics without faiss.

This is a smoke-test fallback for environments where the official SAQ faiss
preprocessing scripts cannot run. It samples a prefix of a fvecs dataset,
computes full-dimensional PCA on that sample, clusters the leading PCA dimensions
with a small NumPy Lloyd loop, and writes SAQ-compatible artifacts.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np


def read_fvecs_prefix(path: Path, limit: int | None = None) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("rb") as handle:
        dim_raw = np.fromfile(handle, dtype="<i4", count=1)
    if dim_raw.size != 1:
        raise ValueError(f"empty fvecs file: {path}")
    dim = int(dim_raw[0])
    row_size = 4 + dim * 4
    rows_total = path.stat().st_size // row_size
    rows = rows_total if limit is None else min(limit, rows_total)
    dtype = np.dtype([("dim", "<i4"), ("vec", "<f4", (dim,))])
    raw = np.fromfile(path, dtype=dtype, count=rows)
    if raw.size != rows:
        raise ValueError(f"expected {rows} rows from {path}, got {raw.size}")
    if not np.all(raw["dim"] == dim):
        raise ValueError(f"inconsistent fvecs dimensions in {path}")
    return np.asarray(raw["vec"], dtype=np.float32).copy()


def write_fvecs(path: Path, data: np.ndarray, chunk_rows: int = 8192) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.asarray(data, dtype=np.float32)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    dim = data.shape[1]
    dtype = np.dtype([("dim", "<i4"), ("vec", "<f4", (dim,))])
    with path.open("wb") as handle:
        for start in range(0, data.shape[0], chunk_rows):
            chunk = data[start : start + chunk_rows]
            out = np.empty(chunk.shape[0], dtype=dtype)
            out["dim"] = dim
            out["vec"] = chunk
            out.tofile(handle)


def write_ivecs(path: Path, data: np.ndarray, chunk_rows: int = 65536) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.asarray(data, dtype=np.int32)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    dim = data.shape[1]
    dtype = np.dtype([("dim", "<i4"), ("vec", "<i4", (dim,))])
    with path.open("wb") as handle:
        for start in range(0, data.shape[0], chunk_rows):
            chunk = data[start : start + chunk_rows]
            out = np.empty(chunk.shape[0], dtype=dtype)
            out["dim"] = dim
            out["vec"] = chunk
            out.tofile(handle)


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def compute_pca(sample: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    log(f"Computing PCA on sample shape={sample.shape}")
    mean = sample.mean(axis=0, dtype=np.float64).astype(np.float32)
    centered = sample.astype(np.float32, copy=True)
    centered -= mean
    log("Computing covariance")
    cov = (centered.T @ centered).astype(np.float64) / max(centered.shape[0] - 1, 1)
    log("Solving covariance eigendecomposition")
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order].astype(np.float32)
    components = eigvecs[:, order].astype(np.float32)
    log("Applying PCA")
    transformed = centered @ components
    variance = transformed.var(axis=0).astype(np.float32)
    return mean, components, transformed.astype(np.float32), variance


def assign_labels(data: np.ndarray, centroids: np.ndarray, chunk_rows: int) -> np.ndarray:
    labels = np.empty(data.shape[0], dtype=np.int32)
    c_norm = np.einsum("ij,ij->i", centroids, centroids)
    for start in range(0, data.shape[0], chunk_rows):
        chunk = data[start : start + chunk_rows]
        x_norm = np.einsum("ij,ij->i", chunk, chunk)[:, None]
        dist = x_norm + c_norm[None, :] - 2.0 * (chunk @ centroids.T)
        labels[start : start + chunk.shape[0]] = np.argmin(dist, axis=1).astype(np.int32)
    return labels


def lloyd_cluster(
    data_reduced: np.ndarray,
    k: int,
    iterations: int,
    chunk_rows: int,
    seed: int,
) -> np.ndarray:
    if k <= 0 or k > data_reduced.shape[0]:
        raise ValueError(f"invalid k={k} for {data_reduced.shape[0]} rows")
    rng = np.random.default_rng(seed)
    init_idx = rng.choice(data_reduced.shape[0], size=k, replace=False)
    centroids = data_reduced[init_idx].copy()
    labels = np.empty(data_reduced.shape[0], dtype=np.int32)
    for iteration in range(1, iterations + 1):
        log(f"Lloyd iteration {iteration}/{iterations}: assignment")
        labels = assign_labels(data_reduced, centroids, chunk_rows)
        counts = np.bincount(labels, minlength=k).astype(np.int64)
        log(
            "Lloyd iteration "
            f"{iteration}/{iterations}: empty={int((counts == 0).sum())}, "
            f"min_count={int(counts.min())}, p50_count={float(np.percentile(counts, 50)):.1f}, "
            f"max_count={int(counts.max())}"
        )
        sums = np.zeros_like(centroids, dtype=np.float64)
        np.add.at(sums, labels, data_reduced)
        nonempty = counts > 0
        centroids[nonempty] = (sums[nonempty] / counts[nonempty, None]).astype(np.float32)
        if np.any(~nonempty):
            refill = rng.choice(data_reduced.shape[0], size=int((~nonempty).sum()), replace=False)
            centroids[~nonempty] = data_reduced[refill]
    log("Final assignment")
    return assign_labels(data_reduced, centroids, chunk_rows)


def compute_full_centroids(data: np.ndarray, labels: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    counts = np.bincount(labels, minlength=k).astype(np.int64)
    sums = np.zeros((k, data.shape[1]), dtype=np.float64)
    log("Accumulating full-dimensional PCA centroids")
    np.add.at(sums, labels, data)
    centroids = np.zeros((k, data.shape[1]), dtype=np.float32)
    nonempty = counts > 0
    centroids[nonempty] = (sums[nonempty] / counts[nonempty, None]).astype(np.float32)
    return centroids, counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare sampled PCA/IVF artifacts for SAQ diagnostics without faiss."
    )
    parser.add_argument("--input", type=Path, required=True, help="Input base fvecs path.")
    parser.add_argument("--output-dir", type=Path, required=True, help="SAQ dataset output directory.")
    parser.add_argument("--dataset", required=True, help="Output dataset prefix.")
    parser.add_argument("--sample-size", type=int, default=100_000, help="Number of prefix rows to sample.")
    parser.add_argument("--k", type=int, default=512, help="Number of fallback IVF clusters.")
    parser.add_argument("--cluster-dims", type=int, default=64, help="Leading PCA dimensions used for clustering.")
    parser.add_argument("--iterations", type=int, default=4, help="Lloyd iterations for fallback clustering.")
    parser.add_argument("--chunk-rows", type=int, default=2048, help="Rows per assignment chunk.")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for centroid initialization.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    log(f"Reading {args.input} limit={args.sample_size}")
    raw = read_fvecs_prefix(args.input, args.sample_size)
    log(f"Loaded sample shape={raw.shape}")

    mean, components, base_pca, variance = compute_pca(raw)
    cluster_dims = min(args.cluster_dims, base_pca.shape[1])
    labels = lloyd_cluster(base_pca[:, :cluster_dims], args.k, args.iterations, args.chunk_rows, args.seed)
    centroids, counts = compute_full_centroids(base_pca, labels, args.k)

    prefix = args.dataset
    log("Writing SAQ-compatible artifacts")
    write_fvecs(out / f"{prefix}_pca_mean.fvecs", mean.reshape(1, -1))
    write_fvecs(out / f"{prefix}_pca_matrix.fvecs", components.T)
    write_fvecs(out / f"{prefix}_base_pca.fvecs", base_pca)
    write_fvecs(out / f"{prefix}_base_pca.vars.fvecs", variance.reshape(1, -1))
    write_fvecs(out / f"{prefix}_centroid_{args.k}_pca.fvecs", centroids)
    write_ivecs(out / f"{prefix}_cluster_id_{args.k}.ivecs", labels.reshape(-1, 1))

    summary = {
        "input": str(args.input),
        "output_dir": str(out),
        "dataset": prefix,
        "sample_size": int(raw.shape[0]),
        "dimension": int(raw.shape[1]),
        "k": int(args.k),
        "cluster_dims": int(cluster_dims),
        "iterations": int(args.iterations),
        "seed": int(args.seed),
        "cluster_size_min": int(counts.min()),
        "cluster_size_p50": float(np.percentile(counts, 50)),
        "cluster_size_p90": float(np.percentile(counts, 90)),
        "cluster_size_max": int(counts.max()),
        "empty_clusters": int((counts == 0).sum()),
        "variance_top1_share": float(variance[0] / variance.sum()) if variance.sum() > 0 else 0.0,
        "variance_top64_share": float(variance[:64].sum() / variance.sum()) if variance.sum() > 0 else 0.0,
    }
    (out / f"{prefix}_sampled_pca_ivf_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    log(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
