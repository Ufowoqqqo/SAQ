#!/usr/bin/env python3
"""Reproduce only the frozen CIFAR PCA-base/IVF inputs from the raw base."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def read_fvecs(path: Path) -> np.ndarray:
    with path.open("rb") as handle:
        dimension_raw = np.fromfile(handle, dtype="<i4", count=1)
    if dimension_raw.size != 1:
        raise ValueError(f"empty fvecs: {path}")
    dimension = int(dimension_raw[0])
    row_bytes = 4 + 4 * dimension
    if path.stat().st_size % row_bytes:
        raise ValueError("fvecs byte size")
    rows = path.stat().st_size // row_bytes
    dtype = np.dtype(
        [("dimension", "<i4"), ("vector", "<f4", (dimension,))]
    )
    raw = np.fromfile(path, dtype=dtype, count=rows)
    if raw.size != rows or not np.all(raw["dimension"] == dimension):
        raise ValueError("inconsistent fvecs")
    return np.asarray(raw["vector"], dtype=np.float32).copy()


def write_xvecs(path: Path, data: np.ndarray, value_dtype: str) -> None:
    data = np.asarray(data)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    dimension = data.shape[1]
    dtype = np.dtype(
        [("dimension", "<i4"), ("vector", value_dtype, (dimension,))]
    )
    with path.open("wb") as handle:
        for begin in range(0, data.shape[0], 8192):
            chunk = data[begin : begin + 8192]
            output = np.empty(chunk.shape[0], dtype=dtype)
            output["dimension"] = dimension
            output["vector"] = chunk
            output.tofile(handle)


def pca(data: np.ndarray) -> np.ndarray:
    mean = data.mean(axis=0, dtype=np.float64).astype(np.float32)
    centered = data.astype(np.float32, copy=True)
    centered -= mean
    log("forming covariance")
    covariance = (centered.T @ centered).astype(np.float64) / max(
        centered.shape[0] - 1, 1
    )
    log("solving covariance eigendecomposition")
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    components = eigenvectors[:, order].astype(np.float32)
    log("applying PCA")
    return (centered @ components).astype(np.float32)


def assign(
    data: np.ndarray,
    centers: np.ndarray,
    chunk_rows: int,
) -> np.ndarray:
    labels = np.empty(data.shape[0], dtype=np.int32)
    center_norm = np.einsum("ij,ij->i", centers, centers)
    for begin in range(0, data.shape[0], chunk_rows):
        chunk = data[begin : begin + chunk_rows]
        row_norm = np.einsum("ij,ij->i", chunk, chunk)[:, None]
        distances = (
            row_norm
            + center_norm[None, :]
            - 2.0 * (chunk @ centers.T)
        )
        labels[begin : begin + chunk.shape[0]] = np.argmin(
            distances, axis=1
        ).astype(np.int32)
    return labels


def cluster(
    reduced: np.ndarray,
    k: int,
    iterations: int,
    chunk_rows: int,
    seed: int,
) -> np.ndarray:
    generator = np.random.default_rng(seed)
    initial = generator.choice(reduced.shape[0], size=k, replace=False)
    centers = reduced[initial].copy()
    for iteration in range(iterations):
        log(f"Lloyd assignment {iteration + 1}/{iterations}")
        labels = assign(reduced, centers, chunk_rows)
        counts = np.bincount(labels, minlength=k).astype(np.int64)
        log(
            f"occupancy min={int(counts.min())} "
            f"empty={int(np.count_nonzero(counts == 0))} "
            f"max={int(counts.max())}"
        )
        sums = np.zeros_like(centers, dtype=np.float64)
        np.add.at(sums, labels, reduced)
        nonempty = counts > 0
        centers[nonempty] = (
            sums[nonempty] / counts[nonempty, None]
        ).astype(np.float32)
        if np.any(~nonempty):
            refill = generator.choice(
                reduced.shape[0],
                size=int(np.count_nonzero(~nonempty)),
                replace=False,
            )
            centers[~nonempty] = reduced[refill]
    log("final Lloyd assignment")
    return assign(reduced, centers, chunk_rows)


def full_centroids(
    data: np.ndarray, labels: np.ndarray, k: int
) -> np.ndarray:
    counts = np.bincount(labels, minlength=k).astype(np.int64)
    if np.any(counts == 0):
        raise ValueError("final empty IVF cell")
    sums = np.zeros((k, data.shape[1]), dtype=np.float64)
    np.add.at(sums, labels, data)
    return (sums / counts[:, None]).astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-base", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    log(f"reading raw base {args.raw_base}")
    raw = read_fvecs(args.raw_base)
    if raw.shape != (60000, 512):
        raise ValueError(f"unexpected CIFAR shape {raw.shape}")
    transformed = pca(raw)
    labels = cluster(
        transformed[:, :64], k=512, iterations=4, chunk_rows=2048, seed=0
    )
    centroids = full_centroids(transformed, labels, 512)

    base_path = args.output_dir / "cifar60k_base_pca.fvecs"
    centroid_path = (
        args.output_dir / "cifar60k_centroid_512_pca.fvecs"
    )
    ids_path = args.output_dir / "cifar60k_cluster_id_512.ivecs"
    log("writing three frozen-input candidates")
    write_xvecs(base_path, transformed, "<f4")
    write_xvecs(centroid_path, centroids, "<f4")
    write_xvecs(ids_path, labels.astype(np.int32), "<i4")
    print(f"PASS rows={raw.shape[0]} dimensions={raw.shape[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
