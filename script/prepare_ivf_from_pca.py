#!/usr/bin/env python3
"""Prepare SAQ IVF centroids/cluster ids from an existing PCA base file."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def read_fvecs(path: Path) -> np.ndarray:
    with path.open("rb") as handle:
        dim_raw = np.fromfile(handle, dtype="<i4", count=1)
    if dim_raw.size != 1:
        raise ValueError(f"empty fvecs file: {path}")
    dim = int(dim_raw[0])
    row_size = 4 + dim * 4
    rows = path.stat().st_size // row_size
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


def assign_labels(data: np.ndarray, centroids: np.ndarray, chunk_rows: int) -> np.ndarray:
    labels = np.empty(data.shape[0], dtype=np.int32)
    c_norm = np.einsum("ij,ij->i", centroids, centroids)
    progress_stride = max(chunk_rows * 100, 1)
    for start in range(0, data.shape[0], chunk_rows):
        chunk = data[start : start + chunk_rows]
        x_norm = np.einsum("ij,ij->i", chunk, chunk)[:, None]
        dist = x_norm + c_norm[None, :] - 2.0 * (chunk @ centroids.T)
        labels[start : start + chunk.shape[0]] = np.argmin(dist, axis=1).astype(np.int32)
        if start and start % progress_stride == 0:
            log(f"assigned {start}/{data.shape[0]}")
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
            f"Lloyd iteration {iteration}/{iterations}: "
            f"empty={int((counts == 0).sum())}, min={int(counts.min())}, "
            f"p50={float(np.percentile(counts, 50)):.1f}, "
            f"p90={float(np.percentile(counts, 90)):.1f}, max={int(counts.max())}"
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
    log("Accumulating full-dimensional centroids")
    np.add.at(sums, labels, data)
    centroids = np.zeros((k, data.shape[1]), dtype=np.float32)
    nonempty = counts > 0
    centroids[nonempty] = (sums[nonempty] / counts[nonempty, None]).astype(np.float32)
    return centroids, counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-pca", type=Path, required=True, help="Existing PCA-space base fvecs.")
    parser.add_argument("--output-dir", type=Path, required=True, help="SAQ dataset output directory.")
    parser.add_argument("--dataset", required=True, help="Dataset prefix.")
    parser.add_argument("--k", type=int, required=True, help="Number of IVF clusters.")
    parser.add_argument("--cluster-dims", type=int, default=64, help="Leading PCA dimensions for clustering.")
    parser.add_argument("--iterations", type=int, default=4, help="Lloyd iterations.")
    parser.add_argument("--chunk-rows", type=int, default=1024, help="Rows per assignment chunk.")
    parser.add_argument("--seed", type=int, default=0, help="Random seed.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing centroid/cid files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.output_dir
    centroid_file = out / f"{args.dataset}_centroid_{args.k}_pca.fvecs"
    cid_file = out / f"{args.dataset}_cluster_id_{args.k}.ivecs"
    summary_file = out / f"{args.dataset}_k{args.k}_pca_ivf_summary.json"
    if not args.overwrite and centroid_file.exists() and cid_file.exists():
        log("K artifacts already exist; use --overwrite to regenerate")
        return 0

    log(f"Reading PCA base {args.base_pca}")
    data = read_fvecs(args.base_pca)
    log(f"Loaded PCA base shape={data.shape}")
    cluster_dims = min(args.cluster_dims, data.shape[1])
    reduced = np.ascontiguousarray(data[:, :cluster_dims])
    labels = lloyd_cluster(reduced, args.k, args.iterations, args.chunk_rows, args.seed)
    centroids, counts = compute_full_centroids(data, labels, args.k)

    log(f"Writing centroids {centroid_file}")
    write_fvecs(centroid_file, centroids)
    log(f"Writing cluster ids {cid_file}")
    write_ivecs(cid_file, labels.reshape(-1, 1))

    summary = {
        "dataset": args.dataset,
        "source_base_pca": str(args.base_pca),
        "output_dir": str(out),
        "k": int(args.k),
        "cluster_dims": int(cluster_dims),
        "iterations": int(args.iterations),
        "chunk_rows": int(args.chunk_rows),
        "seed": int(args.seed),
        "cluster_size_min": int(counts.min()),
        "cluster_size_p50": float(np.percentile(counts, 50)),
        "cluster_size_p90": float(np.percentile(counts, 90)),
        "cluster_size_max": int(counts.max()),
        "empty_clusters": int((counts == 0).sum()),
    }
    summary_file.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
