#!/usr/bin/env python3
"""Compute query-unaware SAQ segment diagnostics.

The main diagnostic compares SAQ's global PCA-variance quantization plan against
IVF cluster-local residual variance. It does not use query workload statistics.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Iterable

import numpy as np


def read_xvecs(path: Path, value_dtype: np.dtype) -> np.ndarray:
    """Read fvecs/ivecs-style files with a 32-bit dimension prefix per row."""
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("rb") as handle:
        dim_raw = np.fromfile(handle, dtype="<i4", count=1)
    if dim_raw.size != 1:
        raise ValueError(f"empty xvecs file: {path}")
    dim = int(dim_raw[0])
    if dim <= 0:
        raise ValueError(f"invalid xvecs dimension {dim} in {path}")

    item_size = np.dtype(value_dtype).itemsize
    row_size = 4 + dim * item_size
    file_size = path.stat().st_size
    if file_size % row_size != 0:
        raise ValueError(
            f"{path}: file size {file_size} is not divisible by row size {row_size}"
        )
    rows = file_size // row_size
    raw = np.fromfile(path, dtype=np.uint8)
    raw = raw.reshape(rows, row_size)
    dims = raw[:, :4].copy().view("<i4").reshape(rows)
    if not np.all(dims == dim):
        bad = np.flatnonzero(dims != dim)[:5].tolist()
        raise ValueError(f"{path}: inconsistent xvecs dimensions at rows {bad}")
    values = raw[:, 4:].copy().view(value_dtype).reshape(rows, dim)
    return values


def read_fvecs(path: Path) -> np.ndarray:
    return read_xvecs(path, np.dtype("<f4"))


def read_ivecs(path: Path) -> np.ndarray:
    return read_xvecs(path, np.dtype("<i4"))


def load_plan(path: Path, plan_id: int) -> list[dict[str, int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    selected = [row for row in rows if int(row.get("plan_id", 0)) == plan_id]
    if not selected:
        raise ValueError(f"no plan_id={plan_id} rows in {path}")
    segments = []
    for row in selected:
        segments.append(
            {
                "segment_id": int(row["segment_id"]),
                "start_dim": int(row["start_dim"]),
                "end_dim": int(row["end_dim"]),
                "dim_len": int(row["dim_len"]),
                "bits": int(row["bits"]),
            }
        )
    segments.sort(key=lambda item: item["segment_id"])
    return segments


def padded_vector(values: np.ndarray, padded_dim: int) -> np.ndarray:
    flat = np.asarray(values).reshape(-1)
    if flat.size > padded_dim:
        return flat[:padded_dim]
    if flat.size == padded_dim:
        return flat
    out = np.zeros(padded_dim, dtype=flat.dtype)
    out[: flat.size] = flat
    return out


def slice_segment(values: np.ndarray, start: int, end: int) -> np.ndarray:
    if start >= values.shape[-1]:
        return np.zeros(end - start, dtype=values.dtype)
    part = values[..., start : min(end, values.shape[-1])]
    if part.shape[-1] == end - start:
        return part
    pad_shape = (*part.shape[:-1], end - start - part.shape[-1])
    return np.concatenate([part, np.zeros(pad_shape, dtype=values.dtype)], axis=-1)


def top_share(values: np.ndarray, k: int) -> float:
    values = np.asarray(values, dtype=np.float64)
    total = float(values.sum())
    if total <= 0:
        return 0.0
    k = min(k, values.size)
    if k <= 0:
        return 0.0
    top = np.partition(values, values.size - k)[values.size - k :]
    return float(top.sum() / total)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def compute_cluster_diagnostics(
    base: np.ndarray,
    centroids: np.ndarray,
    cids: np.ndarray,
    segments: list[dict[str, int]],
    min_cluster_size: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    if cids.ndim == 2:
        if cids.shape[1] != 1:
            raise ValueError(f"cluster id ivecs must have dimension 1, got {cids.shape[1]}")
        cids = cids[:, 0]
    cids = cids.astype(np.int64, copy=False).reshape(-1)
    if base.shape[0] != cids.size:
        raise ValueError(f"base rows {base.shape[0]} != cluster ids {cids.size}")
    if cids.min(initial=0) < 0 or cids.max(initial=0) >= centroids.shape[0]:
        raise ValueError(
            f"cluster id range [{cids.min()}, {cids.max()}] incompatible with {centroids.shape[0]} centroids"
        )

    cluster_count = centroids.shape[0]
    cluster_sizes = np.bincount(cids, minlength=cluster_count)
    per_segment_values: list[list[float]] = [[] for _ in segments]
    per_segment_shares: list[list[float]] = [[] for _ in segments]
    per_segment_weights: list[list[int]] = [[] for _ in segments]

    used_clusters = 0
    skipped_clusters = 0
    for cid, size in enumerate(cluster_sizes):
        if size < min_cluster_size:
            skipped_clusters += 1
            continue
        idx = np.flatnonzero(cids == cid)
        residual = base[idx] - centroids[cid]
        dim_var = residual.var(axis=0)
        total_residual_var = float(dim_var.sum())
        if total_residual_var <= 0:
            skipped_clusters += 1
            continue
        used_clusters += 1
        for seg_i, seg in enumerate(segments):
            seg_var = float(slice_segment(dim_var, seg["start_dim"], seg["end_dim"]).sum())
            per_segment_values[seg_i].append(seg_var)
            per_segment_shares[seg_i].append(seg_var / total_residual_var)
            per_segment_weights[seg_i].append(int(size))

    rows = []
    for seg_i, seg in enumerate(segments):
        values = per_segment_values[seg_i]
        shares = per_segment_shares[seg_i]
        weights = np.asarray(per_segment_weights[seg_i], dtype=np.float64)
        if values and weights.sum() > 0:
            values_arr = np.asarray(values, dtype=np.float64)
            shares_arr = np.asarray(shares, dtype=np.float64)
            weighted_var = float(np.average(values_arr, weights=weights))
            weighted_share = float(np.average(shares_arr, weights=weights))
        else:
            weighted_var = 0.0
            weighted_share = 0.0
        rows.append(
            {
                "cluster_residual_var_mean": float(np.mean(values)) if values else 0.0,
                "cluster_residual_var_p50": percentile(values, 50),
                "cluster_residual_var_p90": percentile(values, 90),
                "cluster_residual_var_max": max(values) if values else 0.0,
                "cluster_residual_var_weighted_mean": weighted_var,
                "cluster_residual_var_share_mean": float(np.mean(shares)) if shares else 0.0,
                "cluster_residual_var_share_p50": percentile(shares, 50),
                "cluster_residual_var_share_p90": percentile(shares, 90),
                "cluster_residual_var_share_max": max(shares) if shares else 0.0,
                "cluster_residual_var_share_weighted_mean": weighted_share,
            }
        )

    summary = {
        "cluster_count": int(cluster_count),
        "used_cluster_count": int(used_clusters),
        "skipped_cluster_count": int(skipped_clusters),
        "min_cluster_size": int(min_cluster_size),
        "base_count": int(base.shape[0]),
        "dimension": int(base.shape[1]),
        "cluster_size_min": int(cluster_sizes.min(initial=0)),
        "cluster_size_p50": float(np.percentile(cluster_sizes, 50)),
        "cluster_size_p90": float(np.percentile(cluster_sizes, 90)),
        "cluster_size_max": int(cluster_sizes.max(initial=0)),
    }
    return rows, summary


def build_rows(
    segments: list[dict[str, int]],
    global_var: np.ndarray,
    cluster_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    padded_dim = max(seg["end_dim"] for seg in segments)
    global_var = padded_vector(global_var, padded_dim).astype(np.float64, copy=False)
    global_total = float(global_var.sum())
    rows = []
    for seg, cluster_row in zip(segments, cluster_rows):
        seg_var = slice_segment(global_var, seg["start_dim"], seg["end_dim"])
        global_var_sum = float(seg_var.sum())
        row = {
            **seg,
            "global_var_sum": global_var_sum,
            "global_var_share": global_var_sum / global_total if global_total > 0 else 0.0,
            "within_segment_top1_var_share": top_share(seg_var, 1),
            "within_segment_top8_var_share": top_share(seg_var, 8),
        }
        row.update(cluster_row)
        row["share_gap_weighted_residual_minus_global"] = (
            float(row["cluster_residual_var_share_weighted_mean"]) - float(row["global_var_share"])
        )
        row["share_gap_p90_residual_minus_global"] = (
            float(row["cluster_residual_var_share_p90"]) - float(row["global_var_share"])
        )
        rows.append(row)
    return rows


def write_csv(rows: list[dict[str, object]], output: Path | None) -> None:
    fields = [
        "segment_id",
        "start_dim",
        "end_dim",
        "dim_len",
        "bits",
        "global_var_sum",
        "global_var_share",
        "cluster_residual_var_mean",
        "cluster_residual_var_p50",
        "cluster_residual_var_p90",
        "cluster_residual_var_max",
        "cluster_residual_var_weighted_mean",
        "cluster_residual_var_share_mean",
        "cluster_residual_var_share_p50",
        "cluster_residual_var_share_p90",
        "cluster_residual_var_share_max",
        "cluster_residual_var_share_weighted_mean",
        "share_gap_weighted_residual_minus_global",
        "share_gap_p90_residual_minus_global",
        "within_segment_top1_var_share",
        "within_segment_top8_var_share",
    ]
    if output is None:
        handle = sys.stdout
        close = False
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        handle = output.open("w", newline="", encoding="utf-8")
        close = True
    try:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if close:
            handle.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare SAQ segment plans with query-unaware residual variance diagnostics."
    )
    parser.add_argument("--data-dir", type=Path, required=True, help="Dataset directory, e.g. data/audio.")
    parser.add_argument("--dataset", required=True, help="Dataset name prefix, e.g. audio.")
    parser.add_argument("--k", type=int, required=True, help="IVF cluster count used in SAQ files.")
    parser.add_argument("--plan-csv", type=Path, required=True, help="CSV produced by extract_quant_plan.py.")
    parser.add_argument("--plan-id", type=int, default=0, help="Plan id in the quant-plan CSV.")
    parser.add_argument("--no-pca", action="store_true", help="Use non-PCA filenames.")
    parser.add_argument("--min-cluster-size", type=int, default=2, help="Skip clusters smaller than this size.")
    parser.add_argument("--output", "-o", type=Path, help="Output diagnostic CSV. Defaults to stdout.")
    parser.add_argument("--summary-output", type=Path, help="Optional JSON summary path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suffix = "" if args.no_pca else "_pca"
    data_dir = args.data_dir
    dataset = args.dataset

    base_path = data_dir / f"{dataset}_base{suffix}.fvecs"
    centroid_path = data_dir / f"{dataset}_centroid_{args.k}{suffix}.fvecs"
    cids_path = data_dir / f"{dataset}_cluster_id_{args.k}.ivecs"
    vars_path = data_dir / f"{dataset}_base{suffix}.vars.fvecs"

    segments = load_plan(args.plan_csv, args.plan_id)
    base = read_fvecs(base_path)
    centroids = read_fvecs(centroid_path)
    cids = read_ivecs(cids_path)
    global_vars = read_fvecs(vars_path).reshape(-1)

    cluster_rows, summary = compute_cluster_diagnostics(
        base=base,
        centroids=centroids,
        cids=cids,
        segments=segments,
        min_cluster_size=args.min_cluster_size,
    )
    rows = build_rows(segments, global_vars, cluster_rows)
    write_csv(rows, args.output)

    summary.update(
        {
            "dataset": dataset,
            "k": args.k,
            "plan_csv": str(args.plan_csv),
            "plan_id": args.plan_id,
            "segment_count": len(segments),
            "segments": segments,
            "output": str(args.output) if args.output else "-",
        }
    )
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
