#!/usr/bin/env python3
"""Evaluate Recall@k and paper-exact 1/Ratio@k from returned IDs."""

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np


SCORE_UPPER_TOLERANCE = 1e-12
POSITION_ORDER_ULPS = 64


def sha256_file(path, chunk_bytes=8 * 1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_bytes)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_uniform_vecs(path, payload_dtype):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"input does not exist: {path}")
    byte_size = path.stat().st_size
    if byte_size < 4 or byte_size % 4 != 0:
        raise ValueError(f"invalid vecs byte size: {path}: {byte_size}")

    raw = np.memmap(path, dtype="<i4", mode="r")
    dim = int(raw[0])
    if dim <= 0:
        raise ValueError(f"invalid vecs dimension: {path}: {dim}")
    row_width = dim + 1
    if raw.size % row_width != 0:
        raise ValueError(
            f"truncated or nonuniform vecs file: {path}: "
            f"{raw.size} int32 values for row width {row_width}"
        )

    rows = raw.reshape(-1, row_width)
    if not np.all(rows[:, 0] == dim):
        bad_row = int(np.flatnonzero(rows[:, 0] != dim)[0])
        raise ValueError(
            f"nonuniform vecs dimension: {path}: row {bad_row} has "
            f"{int(rows[bad_row, 0])}, expected {dim}"
        )

    payload = rows[:, 1:]
    if payload_dtype == np.dtype("<f4"):
        payload = payload.view("<f4")
    elif payload_dtype != np.dtype("<i4"):
        raise ValueError(f"unsupported vecs dtype: {payload_dtype}")
    return payload


def read_fvecs(path):
    return read_uniform_vecs(path, np.dtype("<f4"))


def read_ivecs(path):
    return read_uniform_vecs(path, np.dtype("<i4"))


def validate_id_rows(name, ids, query_count, base_count, k):
    if ids.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional ID matrix")
    if ids.shape[0] != query_count:
        raise ValueError(
            f"{name} query count mismatch: {ids.shape[0]} != {query_count}"
        )
    if ids.shape[1] < k:
        raise ValueError(f"{name} contains {ids.shape[1]} IDs per row, need {k}")

    selected = ids[:, :k]
    invalid = np.argwhere((selected < 0) | (selected >= base_count))
    if invalid.size:
        query_id, position = (int(value) for value in invalid[0])
        raise ValueError(
            f"{name} has invalid ID {int(selected[query_id, position])} at "
            f"query {query_id}, position {position}; base count is {base_count}"
        )

    for query_id, row in enumerate(selected):
        if np.unique(row).size != k:
            raise ValueError(f"{name} has duplicate IDs at query {query_id}")
    return selected


def true_euclidean_distances(query, base, ids):
    vectors = np.asarray(base[ids], dtype=np.float64)
    query64 = np.asarray(query, dtype=np.float64)
    if not np.all(np.isfinite(query64)):
        raise ValueError("query contains a non-finite coordinate")
    if not np.all(np.isfinite(vectors)):
        raise ValueError("selected base vector contains a non-finite coordinate")
    delta = vectors - query64
    squared = np.einsum("ij,ij->i", delta, delta, dtype=np.float64)
    if not np.all(np.isfinite(squared)):
        raise ValueError("true squared-L2 distance is non-finite")
    return np.sqrt(squared)


def inverse_ratio_for_query(query, base, exact_ids, returned_ids):
    exact_distances = np.sort(true_euclidean_distances(query, base, exact_ids))
    returned_distances = np.sort(
        true_euclidean_distances(query, base, returned_ids)
    )

    if np.any(exact_distances == 0.0):
        raise ValueError("exact top-k contains a zero Euclidean distance")

    scale = np.maximum(np.maximum(exact_distances, returned_distances), 1.0)
    order_tolerance = POSITION_ORDER_ULPS * np.finfo(np.float64).eps * scale
    invalid_position = np.flatnonzero(
        returned_distances + order_tolerance < exact_distances
    )
    if invalid_position.size:
        position = int(invalid_position[0])
        raise ValueError(
            "returned set is closer than exact ground truth at position "
            f"{position}: {returned_distances[position]} < "
            f"{exact_distances[position]}"
        )

    ratio_sum = float(np.sum(returned_distances / exact_distances, dtype=np.float64))
    score = exact_distances.size / ratio_sum
    if not math.isfinite(score) or score <= 0.0:
        raise ValueError(f"invalid 1/Ratio score: {score}")
    if score > 1.0 + SCORE_UPPER_TOLERANCE:
        raise ValueError(f"1/Ratio score exceeds one: {score}")
    return score


def recall_for_query(exact_ids, returned_ids):
    return float(np.intersect1d(exact_ids, returned_ids, assume_unique=True).size) / len(
        exact_ids
    )


def linear_quantile(values, q):
    try:
        return float(np.quantile(values, q, method="linear"))
    except TypeError:
        return float(np.quantile(values, q, interpolation="linear"))


def summarize(values):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("cannot summarize an empty or non-vector value set")
    if not np.all(np.isfinite(values)):
        raise ValueError("cannot summarize non-finite values")
    return {
        "count": int(values.size),
        "mean": float(np.mean(values, dtype=np.float64)),
        "min": float(np.min(values)),
        "p01": linear_quantile(values, 0.01),
        "p05": linear_quantile(values, 0.05),
        "median": linear_quantile(values, 0.5),
        "p95": linear_quantile(values, 0.95),
        "max": float(np.max(values)),
    }


def evaluate_result(base, queries, groundtruth, returned, k):
    exact = validate_id_rows(
        "ground truth", groundtruth, queries.shape[0], base.shape[0], k
    )
    approximate = validate_id_rows(
        "returned results", returned, queries.shape[0], base.shape[0], k
    )

    inverse_ratio = np.empty(queries.shape[0], dtype=np.float64)
    recall = np.empty(queries.shape[0], dtype=np.float64)
    for query_id in range(queries.shape[0]):
        try:
            inverse_ratio[query_id] = inverse_ratio_for_query(
                queries[query_id], base, exact[query_id], approximate[query_id]
            )
        except ValueError as exc:
            raise ValueError(f"query {query_id}: {exc}") from exc
        recall[query_id] = recall_for_query(
            exact[query_id], approximate[query_id]
        )

    return {
        "recall_at_k": summarize(recall),
        "inverse_ratio_at_k": summarize(inverse_ratio),
        "per_query": [
            {
                "query_id": int(query_id),
                "recall_at_k": float(recall[query_id]),
                "inverse_ratio_at_k": float(inverse_ratio[query_id]),
            }
            for query_id in range(queries.shape[0])
        ],
    }


def parse_labeled_path(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected LABEL=PATH")
    label, path = value.split("=", 1)
    if not label or not path:
        raise argparse.ArgumentTypeError("expected nonempty LABEL=PATH")
    return label, Path(path)


def input_record(path):
    path = Path(path).resolve()
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Evaluate Recall@k and paper-exact 1/Ratio@k"
    )
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--queries", required=True, type=Path)
    parser.add_argument("--groundtruth", required=True, type=Path)
    parser.add_argument(
        "--results",
        required=True,
        action="append",
        type=parse_labeled_path,
        metavar="LABEL=PATH",
        help="returned top-k ivecs; repeat for multiple operating points",
    )
    parser.add_argument("--k", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dataset", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.k <= 0:
        raise ValueError(f"k must be positive, got {args.k}")
    labels = [label for label, _ in args.results]
    if len(set(labels)) != len(labels):
        raise ValueError("result labels must be unique")

    start = time.perf_counter()
    base = read_fvecs(args.base)
    queries = read_fvecs(args.queries)
    groundtruth = read_ivecs(args.groundtruth)
    if base.shape[1] != queries.shape[1]:
        raise ValueError(
            f"dimension mismatch: base {base.shape[1]} != queries {queries.shape[1]}"
        )

    output = {
        "schema_version": 1,
        "metric": "paper-exact 1/Ratio@k using Euclidean distance",
        "dataset": args.dataset,
        "k": args.k,
        "shape": {
            "base_count": int(base.shape[0]),
            "query_count": int(queries.shape[0]),
            "dimension": int(base.shape[1]),
        },
        "inputs": {
            "base": input_record(args.base),
            "queries": input_record(args.queries),
            "groundtruth": input_record(args.groundtruth),
        },
        "results": [],
    }

    for label, path in args.results:
        returned = read_ivecs(path)
        result_start = time.perf_counter()
        metrics = evaluate_result(base, queries, groundtruth, returned, args.k)
        output["results"].append(
            {
                "label": label,
                "input": input_record(path),
                "evaluation_seconds": time.perf_counter() - result_start,
                **metrics,
            }
        )

    output["total_seconds"] = time.perf_counter() - start
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, args.output)
    print(json.dumps({
        "output": str(args.output),
        "dataset": args.dataset,
        "k": args.k,
        "results": [
            {
                "label": row["label"],
                "recall": row["recall_at_k"]["mean"],
                "inverse_ratio": row["inverse_ratio_at_k"]["mean"],
            }
            for row in output["results"]
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

