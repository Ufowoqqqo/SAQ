#!/usr/bin/env python3
"""Validate and materialize the frozen LP-0 Gate-A projection artifacts.

This script is deliberately specific to the preregistered GIST point.  It
does not fit a new projection, choose a dimension, build an index, or evaluate
quality.  It recovers the already-frozen historical PCA mapping, validates all
registered identities, and writes the smallest common head/tail/replay inputs
needed by the Gate-A evaluator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from prepare_phase1_transform_views import (
    all_row_mapping_error_metrics,
    fixed_probe_clusters,
    open_fvecs,
    open_ivecs,
    read_vecs_shape,
    recover_affine_orthogonal_transform,
    sha256_array,
    validate_vecs_headers,
)


SCHEMA_VERSION = 1
DATASET = "gist_sample50k"
N = 50_000
D = 960
RETAINED_D = 576
K = 512
QUERY_COUNT = 128
NPROBE = 16
FIT_ROWS = 8192
VALIDATION_ROWS = 4096
MAX_MAPPING_RELATIVE_FRO = 1e-5
MAX_MAPPING_ABSOLUTE = 1e-4
MAX_RETAINED_ORTHOGONALITY = 1e-12
TAIL_CHECK_TOLERANCE = 1e-6

EXPECTED_FILE_SHA256 = {
    "raw_base": "bd31f1332e60205472a50cf83a7c4c8cf5ecf5ffd6145cb4e8c44d591f8b2066",
    "raw_query": "0d1d620049de12da455ed7201e97cbab372c4d54d0e6dedbc8c503f62c911299",
    "pca_base": "a027be4e9942c7935ba4c7184eac09b4ad2d2c6fbe561ed9a598e66933b20671",
    "pca_query": "8f888359b836b3a5f498d3bf15bf63744024e320f99fe668c3953db2535cf974",
    "pca_centroids": "48af2216744f9bb39fd7dccf2e0358aa705a4647227adb777796623c676674db",
    "cluster_ids": "c466b5685dd4ef12f42f1d7fa304f42b2c9989df12190c84b8bb4c0a29618eb1",
    "pca_variance": "20345de79dbd6ead9728c2c9abdbdb3f12e4f0ad449122f586d87ed3036b9c35",
}
EXPECTED_MEAN_SHA256 = (
    "9d70b61994ad42c4d35734a786b3814493f8da721cfbfd19943b1b9875167114"
)
EXPECTED_OPERATOR_SHA256 = (
    "5e5de629a3bd95d1b5fe72f29db495113b1313e106ea3caad56992a526d58bdb"
)
EXPECTED_RETAINED_OPERATOR_SHA256 = (
    "b3d467728c62d2540f1d34309a78a8419ecebeafce9e3a07319af4eb35623b53"
)
EXPECTED_PROBE_FILE_SHA256 = (
    "a568c32ff9555aaef9df68e49b65a64f895fb5e37c5aefdf63ff0102732e7b80"
)
EXPECTED_PROBE_ARRAY_SHA256 = (
    "c0e1ed9424a8a287cba9d85dabb2732c89ad132485ae431432c55725e674ebfc"
)
EXPECTED_CANDIDATE_SHA256 = (
    "f5eaef79fbbceda7a0cb04adb5dc232d24d00e0173b4cd70bb0f29ddae25b099"
)
EXPECTED_CANDIDATE_TOTAL = 442_823
EXPECTED_CANDIDATE_MIN = 1675
EXPECTED_CANDIDATE_MAX = 5433

INPUT_FILENAMES = {
    "raw_base": f"{DATASET}_base.fvecs",
    "raw_query": f"{DATASET}_query.fvecs",
    "pca_base": f"{DATASET}_base_pca.fvecs",
    "pca_query": f"{DATASET}_query_pca.fvecs",
    "pca_centroids": f"{DATASET}_centroid_{K}_pca.fvecs",
    "cluster_ids": f"{DATASET}_cluster_id_{K}.ivecs",
    "pca_variance": f"{DATASET}_base_pca.vars.fvecs",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_equal(label: str, observed: Any, expected: Any) -> None:
    if observed != expected:
        raise ValueError(f"{label}: observed {observed!r}, expected {expected!r}")


def require_mapping(label: str, metrics: dict[str, float]) -> None:
    if metrics["relative_frobenius_error"] > MAX_MAPPING_RELATIVE_FRO:
        raise ValueError(
            f"{label} relative Frobenius mapping error "
            f"{metrics['relative_frobenius_error']:.6e} exceeds "
            f"{MAX_MAPPING_RELATIVE_FRO:.6e}"
        )
    if metrics["max_absolute_error"] > MAX_MAPPING_ABSOLUTE:
        raise ValueError(
            f"{label} maximum mapping error {metrics['max_absolute_error']:.6e} "
            f"exceeds {MAX_MAPPING_ABSOLUTE:.6e}"
        )


def array_digest_prefix(dtype: np.dtype[Any], shape: Sequence[int]) -> hashlib._Hash:
    digest = hashlib.sha256()
    digest.update(str(np.dtype(dtype)).encode("ascii"))
    digest.update(struct.pack("<I", len(shape)))
    for size in shape:
        digest.update(struct.pack("<Q", int(size)))
    return digest


def write_dense_binary(path: Path, values: np.ndarray, dtype: str) -> dict[str, Any]:
    """Write an explicitly shaped little-endian dense matrix.

    The file contract is ``uint32 rows, uint32 cols, row-major values``.  It is
    intentionally trivial to read from the C++ replay diagnostic.
    """

    array = np.ascontiguousarray(values, dtype=np.dtype(dtype).newbyteorder("<"))
    if array.ndim == 1:
        array = array.reshape(1, -1)
    if array.ndim != 2:
        raise ValueError("dense binary artifacts must be matrices")
    with path.open("wb") as handle:
        handle.write(struct.pack("<II", *array.shape))
        array.tofile(handle)
    return artifact_identity(path, "dense-binary-v1", array)


def write_vecs(
    path: Path,
    values: np.ndarray,
    dtype: np.dtype[Any],
    chunk_rows: int,
) -> dict[str, Any]:
    if values.ndim != 2:
        raise ValueError("vecs artifacts must be matrices")
    count, dim = values.shape
    value_dtype = np.dtype(dtype)
    digest = array_digest_prefix(value_dtype, values.shape)
    with path.open("wb") as handle:
        for begin in range(0, count, chunk_rows):
            end = min(begin + chunk_rows, count)
            chunk = np.ascontiguousarray(values[begin:end], dtype=value_dtype)
            digest.update(chunk.view(np.uint8))
            if value_dtype == np.dtype(np.float32):
                records = np.empty((end - begin, dim + 1), dtype=np.float32)
                records[:, 1:] = chunk
                records.view(np.int32)[:, 0] = dim
            elif value_dtype == np.dtype(np.int32):
                records = np.empty((end - begin, dim + 1), dtype=np.int32)
                records[:, 0] = dim
                records[:, 1:] = chunk
            else:
                raise ValueError(f"unsupported vecs dtype {value_dtype}")
            records.tofile(handle)
    result = artifact_identity(path, "fvecs" if value_dtype == np.float32 else "ivecs")
    result.update(
        {
            "dtype": str(value_dtype),
            "shape": [count, dim],
            "array_sha256": digest.hexdigest(),
        }
    )
    return result


def vecs_file_sha256(values: np.ndarray, dtype: np.dtype[Any], chunk_rows: int) -> str:
    """Hash the exact fvecs/ivecs serialization without creating a file."""

    if values.ndim != 2:
        raise ValueError("vecs artifacts must be matrices")
    count, dim = values.shape
    value_dtype = np.dtype(dtype)
    digest = hashlib.sha256()
    for begin in range(0, count, chunk_rows):
        end = min(begin + chunk_rows, count)
        chunk = np.ascontiguousarray(values[begin:end], dtype=value_dtype)
        if value_dtype == np.dtype(np.float32):
            records = np.empty((end - begin, dim + 1), dtype=np.float32)
            records[:, 1:] = chunk
            records.view(np.int32)[:, 0] = dim
        elif value_dtype == np.dtype(np.int32):
            records = np.empty((end - begin, dim + 1), dtype=np.int32)
            records[:, 0] = dim
            records[:, 1:] = chunk
        else:
            raise ValueError(f"unsupported vecs dtype {value_dtype}")
        digest.update(records.view(np.uint8))
    return digest.hexdigest()


def artifact_identity(
    path: Path, artifact_format: str, values: np.ndarray | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "relative_path": path.name,
        "format": artifact_format,
        "size_bytes": path.stat().st_size,
        "file_sha256": sha256_file(path),
    }
    if values is not None:
        result.update(
            {
                "dtype": str(values.dtype),
                "shape": list(values.shape),
                "array_sha256": sha256_array(values),
            }
        )
    return result


def candidate_rows(
    cluster_ids: np.ndarray, probes: np.ndarray
) -> Iterable[tuple[int, np.ndarray]]:
    inverted = [
        np.flatnonzero(cluster_ids == cluster).astype("<i4", copy=False)
        for cluster in range(K)
    ]
    for query_id, probe_row in enumerate(probes):
        if np.unique(probe_row).size != NPROBE:
            raise ValueError(f"query {query_id} contains duplicate probe ids")
        candidates = np.concatenate([inverted[int(cluster)] for cluster in probe_row])
        if np.unique(candidates).size != candidates.size:
            raise ValueError(f"query {query_id} contains duplicate candidate ids")
        yield query_id, candidates


def candidate_inventory(
    cluster_ids: np.ndarray, probes: np.ndarray, output: Path | None
) -> dict[str, Any]:
    digest = hashlib.sha256()
    counts: list[int] = []
    handle = output.open("wb") if output is not None else None
    try:
        for query_id, candidates in candidate_rows(cluster_ids, probes):
            header = struct.pack("<IQ", query_id, candidates.size)
            payload = np.ascontiguousarray(candidates, dtype="<i4").tobytes()
            digest.update(header)
            digest.update(payload)
            if handle is not None:
                handle.write(header)
                handle.write(payload)
            counts.append(int(candidates.size))
    finally:
        if handle is not None:
            handle.close()
    result = {
        "queries": len(counts),
        "total": sum(counts),
        "minimum_per_query": min(counts),
        "maximum_per_query": max(counts),
        "sha256": digest.hexdigest(),
        "record_contract": "<query_id:uint32,count:uint64,candidate_ids:int32[]>",
        "order": "probe-file order, then ascending base row id",
    }
    require_equal("candidate query count", result["queries"], QUERY_COUNT)
    require_equal("candidate total", result["total"], EXPECTED_CANDIDATE_TOTAL)
    require_equal("candidate minimum", result["minimum_per_query"], EXPECTED_CANDIDATE_MIN)
    require_equal("candidate maximum", result["maximum_per_query"], EXPECTED_CANDIDATE_MAX)
    require_equal("candidate SHA-256", result["sha256"], EXPECTED_CANDIDATE_SHA256)
    return result


def input_identity(path: Path, expected_sha256: str) -> dict[str, Any]:
    observed = sha256_file(path)
    require_equal(f"input SHA-256 for {path.name}", observed, expected_sha256)
    count, dimension = read_vecs_shape(path)
    return {
        "path": str(path.resolve(strict=True)),
        "size_bytes": path.stat().st_size,
        "count": count,
        "dimension": dimension,
        "sha256": observed,
    }


def prepare_base_tail_values(
    pca_base: np.ndarray,
    pca_centroids: np.ndarray,
    cluster_ids: np.ndarray,
    chunk_rows: int,
) -> tuple[np.ndarray, np.ndarray]:
    exact_sq = np.empty((N, 1), dtype=np.float64)
    deployed_norm = np.empty((N, 1), dtype=np.float32)
    for begin in range(0, N, chunk_rows):
        end = min(begin + chunk_rows, N)
        tail = np.asarray(pca_base[begin:end, RETAINED_D:], dtype=np.float64)
        tail -= np.asarray(
            pca_centroids[cluster_ids[begin:end], RETAINED_D:], dtype=np.float64
        )
        squared = np.einsum("ij,ij->i", tail, tail, dtype=np.float64)
        exact_sq[begin:end, 0] = squared
        deployed_norm[begin:end, 0] = np.sqrt(squared).astype(np.float32)
    if not np.all(np.isfinite(exact_sq)) or not np.all(np.isfinite(deployed_norm)):
        raise ValueError("base tail artifacts contain non-finite values")
    return exact_sq, deployed_norm


def prepare_query_tail_values(
    raw_query: np.ndarray,
    pca_query: np.ndarray,
    pca_centroids: np.ndarray,
    raw_centroids: np.ndarray,
    probes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int]]:
    exact = np.empty((QUERY_COUNT, NPROBE), dtype=np.float64)
    deployed = np.empty((QUERY_COUNT, NPROBE), dtype=np.float32)
    maximum_error = 0.0
    negative_clamps = 0
    for query_id in range(QUERY_COUNT):
        centroid_ids = probes[query_id]
        raw_difference = (
            np.asarray(raw_query[query_id], dtype=np.float64)[None, :]
            - raw_centroids[centroid_ids]
        )
        full_sq = np.einsum(
            "ij,ij->i", raw_difference, raw_difference, dtype=np.float64
        )
        head_difference = (
            np.asarray(pca_query[query_id, :RETAINED_D], dtype=np.float64)[None, :]
            - np.asarray(
                pca_centroids[centroid_ids, :RETAINED_D], dtype=np.float64
            )
        )
        head_sq = np.einsum(
            "ij,ij->i", head_difference, head_difference, dtype=np.float64
        )
        derived = full_sq - head_sq
        tail_difference = (
            np.asarray(pca_query[query_id, RETAINED_D:], dtype=np.float64)[None, :]
            - np.asarray(
                pca_centroids[centroid_ids, RETAINED_D:], dtype=np.float64
            )
        )
        materialized = np.einsum(
            "ij,ij->i", tail_difference, tail_difference, dtype=np.float64
        )
        scale = np.maximum(1.0, full_sq)
        invalid_negative = derived < (-TAIL_CHECK_TOLERANCE * scale)
        if np.any(invalid_negative):
            raise ValueError(
                f"query {query_id} has tail_q_sq below the registered clamp tolerance"
            )
        clamp_mask = derived < 0.0
        negative_clamps += int(np.count_nonzero(clamp_mask))
        derived[clamp_mask] = 0.0
        error = np.abs(derived - materialized)
        tolerance = TAIL_CHECK_TOLERANCE * np.maximum(1.0, np.abs(materialized))
        if np.any(error > tolerance):
            raise ValueError(
                f"query {query_id} derived/materialized tail mismatch exceeds tolerance"
            )
        maximum_error = max(maximum_error, float(error.max()))
        exact[query_id] = materialized
        deployed[query_id] = derived.astype(np.float32)
    if not np.all(np.isfinite(exact)) or not np.all(np.isfinite(deployed)):
        raise ValueError("query tail artifacts contain non-finite values")
    return exact, deployed, {
        "maximum_derived_vs_materialized_absolute_error": maximum_error,
        "negative_values_clamped": negative_clamps,
        "relative_absolute_tolerance": TAIL_CHECK_TOLERANCE,
    }


def validate_inputs(input_dir: Path, chunk_rows: int) -> tuple[dict[str, Path], dict[str, Any]]:
    paths = {label: input_dir / name for label, name in INPUT_FILENAMES.items()}
    for label, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing frozen {label}: {path}")
    identities = {
        label: input_identity(path, EXPECTED_FILE_SHA256[label])
        for label, path in paths.items()
    }
    expected_shapes = {
        "raw_base": (N, D),
        "raw_query": (1000, D),
        "pca_base": (N, D),
        "pca_query": (1000, D),
        "pca_centroids": (K, D),
        "cluster_ids": (N, 1),
        "pca_variance": (1, D),
    }
    for label, expected in expected_shapes.items():
        observed = (identities[label]["count"], identities[label]["dimension"])
        require_equal(f"{label} shape", observed, expected)
        validate_vecs_headers(paths[label], *expected, chunk_rows)
    return paths, identities


def build_validated_state(input_dir: Path, chunk_rows: int) -> dict[str, Any]:
    paths, inputs = validate_inputs(input_dir, chunk_rows)
    raw_base = open_fvecs(paths["raw_base"])
    raw_query = open_fvecs(paths["raw_query"])
    pca_base = open_fvecs(paths["pca_base"])
    pca_query = open_fvecs(paths["pca_query"])
    pca_centroids = open_fvecs(paths["pca_centroids"])
    cluster_ids_matrix = open_ivecs(paths["cluster_ids"])
    cluster_ids = np.asarray(cluster_ids_matrix[:, 0], dtype=np.int32)
    if cluster_ids.min() < 0 or cluster_ids.max() >= K:
        raise ValueError("cluster ids fall outside [0, 512)")

    recovery = recover_affine_orthogonal_transform(
        raw_base,
        pca_base,
        raw_query,
        pca_query,
        FIT_ROWS,
        VALIDATION_ROWS,
        MAX_MAPPING_RELATIVE_FRO,
        MAX_MAPPING_ABSOLUTE,
        chunk_rows,
    )
    require_equal(
        "recovered mean array SHA-256",
        sha256_array(recovery.mean),
        EXPECTED_MEAN_SHA256,
    )
    require_equal(
        "recovered operator array SHA-256",
        sha256_array(recovery.operator),
        EXPECTED_OPERATOR_SHA256,
    )
    retained_operator = np.ascontiguousarray(
        recovery.operator[:, :RETAINED_D], dtype=np.float64
    )
    require_equal(
        "retained operator array SHA-256",
        sha256_array(retained_operator),
        EXPECTED_RETAINED_OPERATOR_SHA256,
    )
    gram_error = retained_operator.T @ retained_operator - np.eye(RETAINED_D)
    normalized_orthogonality = float(
        np.linalg.norm(gram_error, ord="fro") / RETAINED_D
    )
    if normalized_orthogonality > MAX_RETAINED_ORTHOGONALITY:
        raise ValueError(
            f"retained operator normalized orthogonality error "
            f"{normalized_orthogonality:.6e} exceeds "
            f"{MAX_RETAINED_ORTHOGONALITY:.6e}"
        )
    for label in ("fit_error", "heldout_error", "query_artifact_error"):
        require_mapping(label, recovery.diagnostics[label])

    raw_centroids = (
        np.asarray(pca_centroids, dtype=np.float64) @ recovery.operator.T
        + recovery.mean
    )
    centroid_mapping = all_row_mapping_error_metrics(
        raw_centroids,
        pca_centroids,
        recovery.mean,
        recovery.operator,
        chunk_rows,
    )
    require_mapping("centroid round trip", centroid_mapping)
    probes = fixed_probe_clusters(raw_query, raw_centroids, QUERY_COUNT, NPROBE)
    require_equal(
        "fixed probe array SHA-256",
        sha256_array(probes),
        EXPECTED_PROBE_ARRAY_SHA256,
    )
    probe_file_sha256 = vecs_file_sha256(probes, np.dtype(np.int32), chunk_rows)
    require_equal(
        "fixed probe file SHA-256",
        probe_file_sha256,
        EXPECTED_PROBE_FILE_SHA256,
    )
    replay = candidate_inventory(cluster_ids, probes, None)
    query_tail_exact, query_tail_deployed, tail_validation = prepare_query_tail_values(
        raw_query, pca_query, pca_centroids, raw_centroids, probes
    )
    return {
        "paths": paths,
        "inputs": inputs,
        "raw_base": raw_base,
        "raw_query": raw_query,
        "pca_base": pca_base,
        "pca_query": pca_query,
        "pca_centroids": pca_centroids,
        "cluster_ids": cluster_ids,
        "mean": recovery.mean,
        "operator": recovery.operator,
        "retained_operator": retained_operator,
        "raw_centroids": raw_centroids,
        "probes": probes,
        "probe_file_sha256": probe_file_sha256,
        "candidate_inventory": replay,
        "query_tail_exact": query_tail_exact,
        "query_tail_deployed": query_tail_deployed,
        "recovery": recovery.diagnostics,
        "retained_normalized_orthogonality": normalized_orthogonality,
        "centroid_mapping": centroid_mapping,
        "tail_validation": tail_validation,
    }


def materialize(state: dict[str, Any], output_dir: Path, chunk_rows: int) -> Path:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite output directory: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    try:
        outputs: dict[str, dict[str, Any]] = {}
        outputs["apply_mean"] = write_dense_binary(
            temporary / "lp0_apply_mean.f64bin", state["mean"], "<f8"
        )
        outputs["retained_operator"] = write_dense_binary(
            temporary / "lp0_retained_operator_d960_d576.f64bin",
            state["retained_operator"],
            "<f8",
        )
        outputs["raw_centroids"] = write_dense_binary(
            temporary / "lp0_raw_centroids_k512_d960.f64bin",
            state["raw_centroids"],
            "<f8",
        )
        outputs["pca_head_base"] = write_vecs(
            temporary / "lp0_pca_head_base_d576.fvecs",
            state["pca_base"][:, :RETAINED_D],
            np.dtype(np.float32),
            chunk_rows,
        )
        outputs["pca_head_query"] = write_vecs(
            temporary / "lp0_pca_head_query_q128_d576.fvecs",
            state["pca_query"][:QUERY_COUNT, :RETAINED_D],
            np.dtype(np.float32),
            chunk_rows,
        )
        outputs["pca_head_centroids"] = write_vecs(
            temporary / "lp0_pca_head_centroids_k512_d576.fvecs",
            state["pca_centroids"][:, :RETAINED_D],
            np.dtype(np.float32),
            chunk_rows,
        )
        base_tail_exact, base_tail_deployed = prepare_base_tail_values(
            state["pca_base"],
            state["pca_centroids"],
            state["cluster_ids"],
            chunk_rows,
        )
        outputs["base_tail_sq_exact"] = write_dense_binary(
            temporary / "lp0_base_tail_sq_exact.f64bin", base_tail_exact, "<f8"
        )
        outputs["base_tail_norm_deployed"] = write_dense_binary(
            temporary / "lp0_base_tail_norm_deployed.f32bin",
            base_tail_deployed,
            "<f4",
        )
        outputs["query_probe_tail_sq_exact"] = write_dense_binary(
            temporary / "lp0_query_probe_tail_sq_exact.f64bin",
            state["query_tail_exact"],
            "<f8",
        )
        outputs["query_probe_tail_sq_deployed"] = write_dense_binary(
            temporary / "lp0_query_probe_tail_sq_deployed.f32bin",
            state["query_tail_deployed"],
            "<f4",
        )
        probe_path = temporary / "lp0_fixed_probes_q128_nprobe16.ivecs"
        outputs["fixed_probes"] = write_vecs(
            probe_path, state["probes"], np.dtype(np.int32), chunk_rows
        )
        require_equal(
            "generated fixed-probe file SHA-256",
            outputs["fixed_probes"]["file_sha256"],
            EXPECTED_PROBE_FILE_SHA256,
        )
        candidate_path = temporary / "lp0_candidate_inventory_q128.bin"
        replay = candidate_inventory(
            state["cluster_ids"], state["probes"], candidate_path
        )
        require_equal(
            "candidate file SHA-256", sha256_file(candidate_path), EXPECTED_CANDIDATE_SHA256
        )
        outputs["candidate_inventory"] = artifact_identity(
            candidate_path, "lp0-candidate-records-v1"
        )

        script_path = Path(__file__).resolve(strict=True)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "status": "LP-0 Gate-A artifact preparation only; no quality result",
            "preregistration": "docs/saq_lossy_projection_lp0_preregistration_2026_07_11.md",
            "frozen_contract": {
                "dataset": DATASET,
                "N": N,
                "D": D,
                "d": RETAINED_D,
                "queries": QUERY_COUNT,
                "K": K,
                "nprobe": NPROBE,
                "candidate_order": "probe-file order, then ascending base row id",
                "tail_summary": (
                    "base residual L2 norm cast once to float32; query tail squared "
                    "norm derived in float64, clamped by registered rule, cast once"
                ),
            },
            "source_inputs": state["inputs"],
            "recovered_mapping": {
                "application": "(row - mean) @ retained_operator",
                "mean_array_sha256": sha256_array(state["mean"]),
                "full_operator_array_sha256": sha256_array(state["operator"]),
                "retained_operator_array_sha256": sha256_array(
                    state["retained_operator"]
                ),
                "retained_operator_shape": [D, RETAINED_D],
                "retained_normalized_orthogonality_frobenius": state[
                    "retained_normalized_orthogonality"
                ],
                "recovery_diagnostics": state["recovery"],
                "centroid_round_trip": state["centroid_mapping"],
            },
            "fixed_replay": {
                **replay,
                "probe_file_sha256": outputs["fixed_probes"]["file_sha256"],
                "probe_array_sha256": outputs["fixed_probes"]["array_sha256"],
            },
            "tail_validation": state["tail_validation"],
            "outputs": outputs,
            "preparer": {
                "relative_path": "script/prepare_lp0_gate_a_artifacts.py",
                "sha256": sha256_file(script_path),
                "python": sys.version.split()[0],
                "numpy": np.__version__,
            },
        }
        manifest_path = temporary / "lp0_gate_a_artifacts_manifest.json"
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temporary.rename(output_dir)
        return output_dir / manifest_path.name
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def run_self_test() -> None:
    values = np.arange(12, dtype=np.float64).reshape(3, 4)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "matrix.f64bin"
        identity = write_dense_binary(path, values, "<f8")
        with path.open("rb") as handle:
            shape = struct.unpack("<II", handle.read(8))
            recovered = np.fromfile(handle, dtype="<f8").reshape(shape)
        require_equal("self-test dense round trip", recovered.tolist(), values.tolist())
        require_equal("self-test array hash", identity["array_sha256"], sha256_array(values))

    cluster_ids = np.arange(K, dtype=np.int32)
    probes = np.tile(np.arange(NPROBE, dtype=np.int32), (QUERY_COUNT, 1))
    rows = list(candidate_rows(cluster_ids, probes))
    require_equal("self-test candidate rows", len(rows), QUERY_COUNT)
    require_equal("self-test first candidates", rows[0][1].tolist(), list(range(NPROBE)))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and materialize the preregistered LP-0 Gate-A inputs."
    )
    parser.add_argument(
        "--input-dir", type=Path, default=Path("data") / DATASET
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--chunk-rows", type=int, default=4096)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate frozen identities/recovery/replay without writing artifacts",
    )
    parser.add_argument(
        "--self-test", action="store_true", help="run format/helper tests and exit"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_test()
        print("LP-0 preparer self-test: PASS")
        return 0
    if args.chunk_rows <= 0:
        raise ValueError("chunk rows must be positive")
    if not args.validate_only and args.output_dir is None:
        raise ValueError("--output-dir is required unless --validate-only is used")
    state = build_validated_state(args.input_dir, args.chunk_rows)
    print(
        "LP-0 frozen validation: PASS "
        f"(candidate_sha256={state['candidate_inventory']['sha256']})"
    )
    if args.validate_only:
        return 0
    manifest = materialize(state, args.output_dir, args.chunk_rows)
    print(f"LP-0 artifacts: {manifest.parent}")
    print(f"Manifest SHA-256: {sha256_file(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
