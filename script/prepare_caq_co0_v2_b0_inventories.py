#!/usr/bin/env python3
"""Prepare the frozen CO-0 v2 B0 structural inventories.

This script reads only the two one-column IVF assignment files named by the
input specification. It never opens base vectors, centroids, variances,
queries, ground truth, indexes, or encoder outputs.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_INPUT_SPEC = Path("docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_cluster_ids(artifact: dict) -> list[int]:
    path = Path(artifact["path"])
    if path.stat().st_size != artifact["size_bytes"]:
        raise RuntimeError(f"cluster-id size mismatch: {path}")
    data = path.read_bytes()
    observed_hash = sha256_bytes(data)
    if observed_hash != artifact["expected_sha256"]:
        raise RuntimeError(f"cluster-id SHA-256 mismatch: {path}")

    row_size = 8
    if len(data) != artifact["rows"] * row_size:
        raise RuntimeError(f"cluster-id row count mismatch: {path}")
    result: list[int] = []
    for offset in range(0, len(data), row_size):
        dimension, cluster_id = struct.unpack_from("<ii", data, offset)
        if dimension != 1:
            raise RuntimeError(f"cluster-id dimension is not one at byte {offset}: {path}")
        result.append(cluster_id)
    return result


def allocation_rows(
    dataset_id: str,
    cluster_ids: Sequence[int],
    cluster_count: int,
    sample_size: int,
) -> tuple[list[list[object]], list[int]]:
    if any(cluster_id < 0 or cluster_id >= cluster_count for cluster_id in cluster_ids):
        raise RuntimeError(f"cluster id outside [0,{cluster_count}): {dataset_id}")
    populations = [0] * cluster_count
    for cluster_id in cluster_ids:
        populations[cluster_id] += 1
    if sum(populations) != len(cluster_ids):
        raise RuntimeError(f"cluster population sum mismatch: {dataset_id}")

    base_quotas: list[int] = []
    remainders: list[int] = []
    total_rows = len(cluster_ids)
    for population in populations:
        numerator = sample_size * population
        base_quotas.append(numerator // total_rows)
        remainders.append(numerator % total_rows)
    remaining = sample_size - sum(base_quotas)
    if remaining < 0 or remaining > cluster_count:
        raise RuntimeError(f"invalid largest-remainder residual: {dataset_id}")
    remainder_order = sorted(range(cluster_count), key=lambda c: (-remainders[c], c))
    quotas = list(base_quotas)
    for cluster_id in remainder_order[:remaining]:
        quotas[cluster_id] += 1
    if sum(quotas) != sample_size:
        raise RuntimeError(f"final quota sum mismatch: {dataset_id}")
    if any(quota > population for quota, population in zip(quotas, populations)):
        raise RuntimeError(f"quota exceeds population: {dataset_id}")

    rows: list[list[object]] = []
    for cluster_id in range(cluster_count):
        rows.append(
            [
                dataset_id,
                cluster_id,
                populations[cluster_id],
                base_quotas[cluster_id],
                remainders[cluster_id],
                quotas[cluster_id],
            ]
        )
    return rows, quotas


def selection_digest(
    protocol_version: str,
    dataset_id: str,
    cluster_id: int,
    vector_id: int,
) -> bytes:
    serialized = f"{protocol_version}|{dataset_id}|{cluster_id}|{vector_id}".encode("utf-8")
    return hashlib.sha256(serialized).digest()


def sample_and_pair_rows(
    protocol_version: str,
    dataset_id: str,
    cluster_ids: Sequence[int],
    quotas: Sequence[int],
) -> tuple[list[list[object]], list[list[object]], int]:
    ids_by_cell: dict[int, list[int]] = defaultdict(list)
    for vector_id, cluster_id in enumerate(cluster_ids):
        ids_by_cell[cluster_id].append(vector_id)

    samples: list[list[object]] = []
    pairs: list[list[object]] = []
    unpaired = 0
    for cluster_id, quota in enumerate(quotas):
        ordered = sorted(
            ids_by_cell.get(cluster_id, []),
            key=lambda vector_id: (
                selection_digest(protocol_version, dataset_id, cluster_id, vector_id),
                vector_id,
            ),
        )
        selected = ordered[:quota]
        if len(selected) != quota:
            raise RuntimeError(f"selected quota mismatch: {dataset_id} cell {cluster_id}")
        for rank, vector_id in enumerate(selected):
            samples.append([dataset_id, cluster_id, rank, vector_id])
        for pair_rank, rank in enumerate(range(0, len(selected) - 1, 2)):
            pairs.append(
                [dataset_id, cluster_id, pair_rank, selected[rank], selected[rank + 1]]
            )
        unpaired += len(selected) % 2
    return samples, pairs, unpaired


def canonical_csv(header: Sequence[str], rows: Iterable[Sequence[object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def write_deterministic_gzip(path: Path, canonical: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as zipped:
            zipped.write(canonical)
    return {
        "relative_path": path.name,
        "compressed_bytes": path.stat().st_size,
        "compressed_sha256": sha256_file(path),
        "canonical_bytes": len(canonical),
        "canonical_sha256": sha256_bytes(canonical),
    }


def expected_rotation_paths(dataset: dict) -> list[dict]:
    result: list[dict] = []
    positive_segments = [segment for segment in dataset["plan"] if segment["total_bits"] > 0]
    for logical_seed in (0, 1, 2):
        for segment_index, segment in enumerate(positive_segments):
            dimension = segment["dimensions"]
            result.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "logical_seed": logical_seed,
                    "c_rng_seed": logical_seed + 1,
                    "scope": "segmented",
                    "segment_index": segment_index,
                    "dimension": dimension,
                    "relative_path": (
                        f"{dataset['dataset_id']}/logical_seed_{logical_seed}/"
                        f"segmented_s{segment_index}_d{dimension}.f32"
                    ),
                }
            )
        dimension = dataset["positive_dimension"]
        result.append(
            {
                "dataset_id": dataset["dataset_id"],
                "logical_seed": logical_seed,
                "c_rng_seed": logical_seed + 1,
                "scope": "whole",
                "segment_index": None,
                "dimension": dimension,
                "relative_path": (
                    f"{dataset['dataset_id']}/logical_seed_{logical_seed}/whole_d{dimension}.f32"
                ),
            }
        )
    return result


def collect_rotations(rotation_root: Path, datasets: Sequence[dict]) -> list[dict]:
    rotations: list[dict] = []
    for dataset in datasets:
        for entry in expected_rotation_paths(dataset):
            path = rotation_root / entry["relative_path"]
            expected_bytes = entry["dimension"] * entry["dimension"] * 4
            if path.stat().st_size != expected_bytes:
                raise RuntimeError(f"rotation size mismatch: {path}")
            rotations.append(
                {
                    **entry,
                    "size_bytes": expected_bytes,
                    "sha256": sha256_file(path),
                }
            )

    grouped: dict[tuple[str, str, int | None, int], set[str]] = defaultdict(set)
    for rotation in rotations:
        key = (
            rotation["dataset_id"],
            rotation["scope"],
            rotation["segment_index"],
            rotation["dimension"],
        )
        grouped[key].add(rotation["sha256"])
    if any(len(hashes) != 3 for hashes in grouped.values()):
        raise RuntimeError("logical rotation seeds are not distinct within a frozen scope")
    if len(rotations) != 27:
        raise RuntimeError("unexpected rotation inventory count")
    return rotations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-spec", type=Path, default=DEFAULT_INPUT_SPEC)
    parser.add_argument("--rotation-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spec = json.loads(args.input_spec.read_text(encoding="utf-8"))
    if spec["schema_version"] != 1:
        raise RuntimeError("unsupported B0 input-spec schema")
    protocol_version = spec["protocol_version"]
    sample_size = spec["sample_size_per_dataset"]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dataset_manifests: list[dict] = []
    for dataset in spec["datasets"]:
        dataset_id = dataset["dataset_id"]
        cluster_artifact = dataset["artifacts"]["cluster_ids"]
        cluster_ids = read_cluster_ids(cluster_artifact)
        if len(cluster_ids) != dataset["rows"]:
            raise RuntimeError(f"assignment row count mismatch: {dataset_id}")
        allocation, quotas = allocation_rows(
            dataset_id,
            cluster_ids,
            dataset["ivf_clusters"],
            sample_size,
        )
        samples, pairs, unpaired = sample_and_pair_rows(
            protocol_version,
            dataset_id,
            cluster_ids,
            quotas,
        )
        if len(samples) != sample_size:
            raise RuntimeError(f"sample inventory size mismatch: {dataset_id}")

        prefix = dataset_id
        allocation_file = write_deterministic_gzip(
            args.output_dir / f"{prefix}_allocation.csv.gz",
            canonical_csv(
                [
                    "dataset_id",
                    "cell_id",
                    "population",
                    "base_quota",
                    "remainder_numerator",
                    "final_quota",
                ],
                allocation,
            ),
        )
        sample_file = write_deterministic_gzip(
            args.output_dir / f"{prefix}_sample.csv.gz",
            canonical_csv(
                ["dataset_id", "cell_id", "rank_in_cell", "vector_id"],
                samples,
            ),
        )
        pair_file = write_deterministic_gzip(
            args.output_dir / f"{prefix}_pairs.csv.gz",
            canonical_csv(
                [
                    "dataset_id",
                    "cell_id",
                    "pair_rank",
                    "stored_vector_id",
                    "query_vector_id",
                ],
                pairs,
            ),
        )
        populations = [row[2] for row in allocation]
        dataset_manifests.append(
            {
                "dataset_id": dataset_id,
                "rows": len(cluster_ids),
                "clusters": dataset["ivf_clusters"],
                "assignment_sha256": cluster_artifact["expected_sha256"],
                "population_min": min(populations),
                "population_max": max(populations),
                "empty_clusters": sum(population == 0 for population in populations),
                "sample_count": len(samples),
                "sampled_cells": sum(quota > 0 for quota in quotas),
                "pair_count": len(pairs),
                "unpaired_count": unpaired,
                "allocation_file": allocation_file,
                "sample_file": sample_file,
                "pair_file": pair_file,
            }
        )

    rotations = collect_rotations(args.rotation_dir, spec["datasets"])
    manifest = {
        "schema_version": 1,
        "stage": "V2-B0",
        "status": "PASS",
        "protocol_version": protocol_version,
        "input_spec": {
            "relative_path": args.input_spec.as_posix(),
            "sha256": sha256_file(args.input_spec),
        },
        "structural_read_scope": "two frozen D=1 cluster-id files only",
        "sample_size_per_dataset": sample_size,
        "datasets": dataset_manifests,
        "rotations": rotations,
        "generator": {
            "script": "script/prepare_caq_co0_v2_b0_inventories.py",
            "script_sha256": sha256_file(Path(__file__)),
            "python": sys.version.splitlines()[0],
            "byteorder": sys.byteorder,
        },
    }
    manifest_path = args.output_dir / "inventory_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "stage": "V2-B0",
        "status": "PASS",
        "datasets": len(dataset_manifests),
        "sample_rows": sum(item["sample_count"] for item in dataset_manifests),
        "pair_rows": sum(item["pair_count"] for item in dataset_manifests),
        "rotation_matrices": len(rotations),
        "manifest_sha256": sha256_file(manifest_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # keep a concise machine-visible failure boundary
        print(json.dumps({"stage": "V2-B0", "status": "FAIL"}, sort_keys=True))
        print(f"V2-B0 inventory preparation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
