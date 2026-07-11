#!/usr/bin/env python3
"""Evaluate the preregistered LP-0 Gate-A exact-surrogate screen.

The evaluator consumes one lossy-projection oracle prefix and one native SAQ
Phase-1 prefix.  It deliberately implements only the confirmatory comparison
registered in ``docs/saq_lossy_projection_lp0_preregistration_2026_07_11.md``:

    oracle576_norm.DP - native_full_saq.full

Logical rotation seeds 0..9 are averaged within each query before inference.
The rotation-off comparator is reported separately and does not affect the
confirmatory decision.  Invalid or incomplete inputs fail closed before any
evidence files are written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import struct
import sys
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "saq_lp0_gate_a_evaluation_v1"
ORACLE_MANIFEST_SCHEMA = "saq_lp0_gate_a_oracle_v1"
EXPECTED_EXACT_SCOPE = "canonical_raw_float64_squared_L2"
EXPECTED_DATASET = "gist_sample50k"
EXPECTED_N = 50_000
EXPECTED_D = 960
EXPECTED_PROJECTED_D = 576
EXPECTED_K = 512
EXPECTED_QUERIES = 128
EXPECTED_NPROBE = 16
EXPECTED_TOPK = 100
EXPECTED_CANDIDATES = 442_823
EXPECTED_MIN_CANDIDATES = 1_675
EXPECTED_MAX_CANDIDATES = 5_433
EXPECTED_CANDIDATE_SHA256 = (
    "f5eaef79fbbceda7a0cb04adb5dc232d24d00e0173b4cd70bb0f29ddae25b099"
)
EXPECTED_PLAN_CONTROL = "frozen-pca"
EXPECTED_PLAN = "0:64@11b|64:256@6b|256:576@4b|576:832@2b|832:960@0b"
EXPECTED_CODE_BITS = 3_648
EXPECTED_NOMINAL_B = 4.0
EXPECTED_VARS_BOUND_M = 4.0
EXPECTED_SEEDS = tuple(range(10))
EXPECTED_SEED_SCOPE = (
    "logical_seed_0_9_maps_to_c_rng_seed_1_10_not_cross_plan_matrix_identity"
)
EXPECTED_BOOTSTRAP_REPLICATES = 10_000
EXPECTED_BOOTSTRAP_SEED = 20_260_711
EXPECTED_NATIVE_MANIFEST_SHA256 = (
    "d0cfe99b37ffcef93e2e6c5805c4035bf4986b7f56059595b95a67c056704a3f"
)
EXPECTED_ACCUMULATION = (
    "historical_pca_float32_coordinates_float64_accumulation"
)

EXPECTED_FROZEN_ARTIFACTS = {
    "raw_base_file": "bd31f1332e60205472a50cf83a7c4c8cf5ecf5ffd6145cb4e8c44d591f8b2066",
    "raw_query_file": "0d1d620049de12da455ed7201e97cbab372c4d54d0e6dedbc8c503f62c911299",
    "historical_pca_base_file": "a027be4e9942c7935ba4c7184eac09b4ad2d2c6fbe561ed9a598e66933b20671",
    "historical_pca_query_file": "8f888359b836b3a5f498d3bf15bf63744024e320f99fe668c3953db2535cf974",
    "historical_pca_centroids_file": "48af2216744f9bb39fd7dccf2e0358aa705a4647227adb777796623c676674db",
    "cluster_assignments_file": "c466b5685dd4ef12f42f1d7fa304f42b2c9989df12190c84b8bb4c0a29618eb1",
    "historical_pca_variance_file": "20345de79dbd6ead9728c2c9abdbdb3f12e4f0ad449122f586d87ed3036b9c35",
    "recovered_mean_array": "9d70b61994ad42c4d35734a786b3814493f8da721cfbfd19943b1b9875167114",
    "recovered_full_operator_array": "5e5de629a3bd95d1b5fe72f29db495113b1313e106ea3caad56992a526d58bdb",
    "retained_operator_array": "b3d467728c62d2540f1d34309a78a8419ecebeafce9e3a07319af4eb35623b53",
    "fixed_probes_file": "a568c32ff9555aaef9df68e49b65a64f895fb5e37c5aefdf63ff0102732e7b80",
    "fixed_probes_array": "c0e1ed9424a8a287cba9d85dabb2732c89ad132485ae431432c55725e674ebfc",
}

EXPECTED_NATIVE_INPUTS = {
    "pca_base": EXPECTED_FROZEN_ARTIFACTS["historical_pca_base_file"],
    "pca_query": EXPECTED_FROZEN_ARTIFACTS["historical_pca_query_file"],
    "raw_base": EXPECTED_FROZEN_ARTIFACTS["raw_base_file"],
    "raw_query": EXPECTED_FROZEN_ARTIFACTS["raw_query_file"],
    "pca_centroids": EXPECTED_FROZEN_ARTIFACTS["historical_pca_centroids_file"],
    "cluster_ids": EXPECTED_FROZEN_ARTIFACTS["cluster_assignments_file"],
    "pca_variance": EXPECTED_FROZEN_ARTIFACTS["historical_pca_variance_file"],
    "fixed_probes": EXPECTED_FROZEN_ARTIFACTS["fixed_probes_file"],
}

REFERENCE_COLUMNS = (
    "query",
    "candidate_count",
    "candidate_ids_fnv1a64",
    "exact_id_distance_fnv1a64",
    "exact_best_id",
    "exact_topk_used",
    "exact_topk_ids",
    "exact_topk_boundary_distance",
    "exact_first_outside_distance",
    "exact_boundary_gap",
    "exact_reference_scope",
)

ORACLE_COLUMNS = (
    "arm",
    "distance_value",
    "tail_treatment",
    "distance_reference_scope",
    "query",
    "candidate_count",
    "finite_count",
    "nonfinite_count",
    "bias",
    "mae",
    "rmse",
    "abs_relative_eps1e-12_p50",
    "abs_relative_eps1e-12_p90",
    "abs_relative_eps1e-12_p99",
    "topk_used",
    "fixed_candidate_topk_agreement",
    "exact_best_estimated_rank",
    "strict_exact_topk_vs_outside_boundary_inversions",
    "boundary_pairs",
    "strict_boundary_inversion_rate",
    "candidate_ids_fnv1a64",
    "exact_id_distance_fnv1a64",
    "estimate_id_distance_fnv1a64",
    "e_projection_bias",
    "e_projection_mae",
    "e_projection_rmse",
    "e_summary_bias",
    "e_summary_mae",
    "e_summary_rmse",
    "e_projection_e_summary_population_covariance",
    "error_sum_identity_max_abs",
)

NATIVE_CONFIG_COLUMNS = (
    "transform",
    "config_id",
    "plan_control",
    "rotation_control",
    "rotation_enabled",
    "rotation_seed",
    "seed_scope",
    "N",
    "D",
    "K",
    "queries",
    "fixed_probes_per_query",
    "topk_requested",
    "nominal_B",
    "vars_bound_m",
    "segments",
    "plan",
    "nominal_code_bits_per_vector",
    "actual_serialized_index_bytes",
    "actual_serialized_index_bytes_per_vector",
    "candidate_evaluations",
    "exact_distance_scope",
)

NATIVE_QUERY_COLUMNS = (
    "transform",
    "config_id",
    "plan_control",
    "rotation_control",
    "rotation_seed",
    "query",
    "stage",
    "stage_semantics",
    "distance_reference_scope",
    "candidate_count",
    "finite_count",
    "nonfinite_count",
    "topk_used",
    "fixed_candidate_topk_agreement",
    "exact_best_estimated_rank",
    "strict_exact_topk_vs_outside_boundary_inversions",
    "boundary_pairs",
    "strict_boundary_inversion_rate",
)

EXPECTED_ORACLE_GRID = {
    ("oracle576_none", "DP"): "none",
    ("oracle576_none", "DS"): "none",
    ("oracle576_norm", "DP"): "exact_float64_combined_tail_norm",
    ("oracle576_norm", "DS"): "deployed_float32_combined_tail_norm",
}

CANDIDATE_COLUMNS = (
    "query",
    "probe_position",
    "cluster_id",
    "candidate_position",
    "base_id",
    "D0",
    "DP_none",
    "DS_none",
    "DP_norm",
    "DS_norm",
    "e_projection_none",
    "e_summary_none",
    "e_total_none",
    "e_projection_norm",
    "e_summary_norm",
    "e_total_norm",
    "error_sum_identity_none",
    "error_sum_identity_norm",
)

EXPECTED_NATIVE_STAGES = {
    "vars_conservative_lower_bound_all",
    "fast_prefix_1",
    "fast_prefix_2",
    "fast_prefix_3",
    "fast_prefix_4",
    "fast_all",
    "accurate_prefix_1",
    "accurate_prefix_2",
    "accurate_prefix_3",
    "accurate_prefix_4",
    "full",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_csv(path: Path, required: Iterable[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no CSV header")
        missing = sorted(set(required).difference(reader.fieldnames))
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path} contains no data rows")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def as_int(row: Mapping[str, Any], column: str, context: str) -> int:
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{context}: invalid integer column {column!r}") from error
    if not math.isfinite(value) or value != int(value):
        raise ValueError(f"{context}: {column} is not a finite integer: {value!r}")
    return int(value)


def as_float(row: Mapping[str, Any], column: str, context: str) -> float:
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{context}: invalid numeric column {column!r}") from error
    if not math.isfinite(value):
        raise ValueError(f"{context}: {column} is not finite")
    return value


def require_equal(actual: Any, expected: Any, context: str) -> None:
    if actual != expected:
        raise ValueError(f"{context}: expected {expected!r}, observed {actual!r}")


def require_number(actual: Any, expected: float, context: str) -> None:
    try:
        value = float(actual)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{context}: expected numeric value") from error
    if not math.isfinite(value) or value != expected:
        raise ValueError(f"{context}: expected {expected}, observed {actual!r}")


def validate_manifest(
    manifest: Mapping[str, Any], manifest_path: Path, metrics_path: Path,
    reference_path: Path, candidate_path: Path,
) -> None:
    require_equal(
        manifest.get("schema_version"), ORACLE_MANIFEST_SCHEMA,
        "oracle manifest schema_version",
    )
    require_equal(manifest.get("status"), "complete", "oracle manifest status")

    configuration = manifest.get("configuration")
    if not isinstance(configuration, Mapping):
        raise ValueError("oracle manifest configuration must be an object")
    expected_configuration: dict[str, Any] = {
        "dataset": EXPECTED_DATASET,
        "N": EXPECTED_N,
        "D": EXPECTED_D,
        "d": EXPECTED_PROJECTED_D,
        "K": EXPECTED_K,
        "queries": EXPECTED_QUERIES,
        "fixed_probes_per_query": EXPECTED_NPROBE,
        "topk": EXPECTED_TOPK,
        "metric": "squared_L2",
        "accumulation": EXPECTED_ACCUMULATION,
    }
    for key, expected in expected_configuration.items():
        require_equal(configuration.get(key), expected, f"configuration.{key}")

    artifacts = manifest.get("frozen_artifacts")
    if not isinstance(artifacts, Mapping):
        raise ValueError("oracle manifest frozen_artifacts must be an object")
    require_equal(set(artifacts), set(EXPECTED_FROZEN_ARTIFACTS),
                  "frozen_artifacts key set")
    for key, expected_hash in EXPECTED_FROZEN_ARTIFACTS.items():
        artifact = artifacts.get(key)
        if not isinstance(artifact, Mapping):
            raise ValueError(f"frozen_artifacts.{key} must be an object")
        require_equal(
            artifact.get("expected_sha256"), expected_hash,
            f"frozen_artifacts.{key}.expected_sha256",
        )
        require_equal(
            artifact.get("observed_sha256"), expected_hash,
            f"frozen_artifacts.{key}.observed_sha256",
        )

    inventory = manifest.get("candidate_inventory")
    if not isinstance(inventory, Mapping):
        raise ValueError("oracle manifest candidate_inventory must be an object")
    expected_inventory: dict[str, Any] = {
        "expected_sha256": EXPECTED_CANDIDATE_SHA256,
        "observed_sha256": EXPECTED_CANDIDATE_SHA256,
        "expected_total": EXPECTED_CANDIDATES,
        "observed_total": EXPECTED_CANDIDATES,
        "expected_min_per_query": EXPECTED_MIN_CANDIDATES,
        "observed_min_per_query": EXPECTED_MIN_CANDIDATES,
        "expected_max_per_query": EXPECTED_MAX_CANDIDATES,
        "observed_max_per_query": EXPECTED_MAX_CANDIDATES,
        "duplicate_count": 0,
    }
    for key, expected in expected_inventory.items():
        require_equal(inventory.get(key), expected, f"candidate_inventory.{key}")

    outputs = manifest.get("outputs")
    if not isinstance(outputs, Mapping):
        raise ValueError("oracle manifest outputs must be an object")
    for key, path in (
        ("query_metrics", metrics_path),
        ("query_reference", reference_path),
        ("candidate_distances", candidate_path),
    ):
        output = outputs.get(key)
        if not isinstance(output, Mapping):
            raise ValueError(f"oracle manifest outputs.{key} must be an object")
        require_equal(
            output.get("sha256"), sha256_file(path), f"outputs.{key}.sha256"
        )
        recorded_path = output.get("path")
        if not isinstance(recorded_path, str) or not recorded_path:
            raise ValueError(f"outputs.{key}.path must be a non-empty string")
        recorded_output_path = Path(recorded_path)
        if not recorded_output_path.is_absolute():
            recorded_output_path = manifest_path.parent / recorded_output_path
        if recorded_output_path.resolve(strict=True) != path.resolve(strict=True):
            raise ValueError(
                f"outputs.{key}.path does not resolve to the supplied prefix output"
            )
        if key == "candidate_distances":
            require_equal(output.get("rows"), EXPECTED_CANDIDATES,
                          "outputs.candidate_distances.rows")


def validate_native_manifest(
    manifest: Mapping[str, Any], manifest_path: Path, native_prefix: Path,
) -> None:
    require_equal(sha256_file(manifest_path), EXPECTED_NATIVE_MANIFEST_SHA256,
                  "native comparator manifest SHA-256")
    require_equal(manifest.get("schema_version"), 1,
                  "native comparator manifest schema_version")
    require_equal(manifest.get("gate"), "LP-0 Gate A", "native manifest gate")
    require_equal(manifest.get("arm"), "native_full_saq", "native manifest arm")
    require_equal(manifest.get("protocol_commit"), "d034578",
                  "native manifest protocol_commit")
    require_equal(manifest.get("source_base_commit"), "3d94840",
                  "native manifest source_base_commit")
    require_equal(manifest.get("source_worktree_diff"),
                  "clean before native comparator execution",
                  "native manifest source_worktree_diff")
    require_equal(manifest.get("frozen_plan"), EXPECTED_PLAN,
                  "native manifest frozen_plan")

    command = manifest.get("command_contract")
    if not isinstance(command, Mapping):
        raise ValueError("native command_contract must be an object")
    expected_command: dict[str, Any] = {
        "binary": "./bin/phase1_transform_diagnostic",
        "transform_label": "native_full_saq",
        "plans": EXPECTED_PLAN_CONTROL,
        "rotation_seeds": "0,1,2,3,4,5,6,7,8,9,off",
        "logical_seed_mapping": (
            "logical s -> srand(s+1); off -> srand(0) with random_rotation=false"
        ),
        "max_queries": EXPECTED_QUERIES,
        "topk": EXPECTED_TOPK,
        "num_threads": 6,
        "B": EXPECTED_NOMINAL_B,
        "vars_bound_m": EXPECTED_VARS_BOUND_M,
        "distance": "L2Sqr",
        "quant_type": "CAQ",
        "enable_segmentation": True,
        "use_fastscan": True,
        "use_compact_layout": False,
        "caq_adj_rd_lmt": 6,
        "caq_adj_eps": 1e-8,
        "caq_ori_qB": 0,
    }
    for key, expected in expected_command.items():
        require_equal(command.get(key), expected, f"native command_contract.{key}")

    inputs = manifest.get("input_sha256")
    if not isinstance(inputs, Mapping):
        raise ValueError("native input_sha256 must be an object")
    require_equal(dict(inputs), EXPECTED_NATIVE_INPUTS, "native input SHA-256 map")

    structure = manifest.get("validated_structure")
    if not isinstance(structure, Mapping):
        raise ValueError("native validated_structure must be an object")
    expected_structure: dict[str, Any] = {
        "N": EXPECTED_N,
        "D": EXPECTED_D,
        "K": EXPECTED_K,
        "queries": EXPECTED_QUERIES,
        "nprobe": EXPECTED_NPROBE,
        "topk": EXPECTED_TOPK,
        "candidate_evaluations_per_config": EXPECTED_CANDIDATES,
        "configs": 11,
        "exact_distance_scope": EXPECTED_EXACT_SCOPE,
        "serialized_bytes_seeded": 34_201_289,
        "serialized_bytes_off": 33_300_169,
    }
    for key, expected in expected_structure.items():
        require_equal(structure.get(key), expected, f"native validated_structure.{key}")

    outputs = manifest.get("output_sha256")
    if not isinstance(outputs, Mapping):
        raise ValueError("native output_sha256 must be an object")
    expected_paths = {
        "configs": Path(f"{native_prefix}.configs.csv"),
        "query_reference": Path(f"{native_prefix}.query_reference.csv"),
        "query_stages": Path(f"{native_prefix}.query_stages.csv"),
        "segment_errors": Path(f"{native_prefix}.segment_errors.csv"),
    }
    require_equal(set(outputs), set(expected_paths), "native output SHA-256 key set")
    for key, path in expected_paths.items():
        require_equal(outputs.get(key), sha256_file(path),
                      f"native output_sha256.{key}")

    source_hashes = manifest.get("source_sha256")
    if not isinstance(source_hashes, Mapping) or not source_hashes:
        raise ValueError("native source_sha256 must be a non-empty object")
    for name, digest in source_hashes.items():
        if not isinstance(name, str) or not name or not isinstance(digest, str):
            raise ValueError("native source_sha256 contains an invalid entry")
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError(f"native source_sha256.{name} is not a SHA-256 digest")


def validate_references(
    oracle_rows: Sequence[Mapping[str, str]],
    native_rows: Sequence[Mapping[str, str]],
    oracle_path: Path,
    native_path: Path,
) -> dict[int, Mapping[str, str]]:
    if sha256_file(oracle_path) != sha256_file(native_path):
        raise ValueError(
            "oracle and native query-reference files are not byte-identical; "
            "the common D0/candidate inventory contract is invalid"
        )
    if len(oracle_rows) != EXPECTED_QUERIES or len(native_rows) != EXPECTED_QUERIES:
        raise ValueError("query-reference files must contain exactly 128 rows")
    references: dict[int, Mapping[str, str]] = {}
    for row in oracle_rows:
        query = as_int(row, "query", "oracle query reference")
        if query in references:
            raise ValueError(f"duplicate oracle query-reference row q{query}")
        references[query] = row
    require_equal(set(references), set(range(EXPECTED_QUERIES)),
                  "query-reference query set")
    counts = []
    for query, row in references.items():
        context = f"query-reference q{query}"
        count = as_int(row, "candidate_count", context)
        counts.append(count)
        require_equal(as_int(row, "exact_topk_used", context), EXPECTED_TOPK,
                      f"{context} exact_topk_used")
        require_equal(row["exact_reference_scope"], EXPECTED_EXACT_SCOPE,
                      f"{context} exact_reference_scope")
        topk_ids = row["exact_topk_ids"].split("|")
        require_equal(len(topk_ids), EXPECTED_TOPK, f"{context} exact_topk_ids length")
        if len(set(topk_ids)) != EXPECTED_TOPK:
            raise ValueError(f"{context}: duplicate ID in exact_topk_ids")
        for column in (
            "exact_topk_boundary_distance", "exact_first_outside_distance",
            "exact_boundary_gap",
        ):
            as_float(row, column, context)
    require_equal(sum(counts), EXPECTED_CANDIDATES, "reference candidate total")
    require_equal(min(counts), EXPECTED_MIN_CANDIDATES, "reference candidate minimum")
    require_equal(max(counts), EXPECTED_MAX_CANDIDATES, "reference candidate maximum")
    return references


def expected_rotation(row: Mapping[str, str], context: str) -> tuple[str, int]:
    control = row["rotation_control"]
    seed = as_int(row, "rotation_seed", context)
    if control == "off":
        require_equal(seed, -1, f"{context} off rotation seed")
        return control, seed
    if seed not in EXPECTED_SEEDS:
        raise ValueError(f"{context}: rotation seed must be 0..9 or off")
    require_equal(control, f"seed{seed}", f"{context} rotation control")
    return control, seed


def validate_native_configs(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Mapping[str, str]]:
    if len(rows) != 11:
        raise ValueError(f"native comparator requires exactly 11 configs, observed {len(rows)}")
    configs: dict[str, Mapping[str, str]] = {}
    observed_controls: set[tuple[str, int]] = set()
    transforms: set[str] = set()
    for row in rows:
        config_id = row["config_id"]
        context = f"native config {config_id}"
        if not config_id or config_id in configs:
            raise ValueError(f"duplicate or empty native config_id {config_id!r}")
        control, seed = expected_rotation(row, context)
        require_equal(as_int(row, "rotation_enabled", context), int(seed >= 0),
                      f"{context} rotation_enabled")
        require_equal(row["seed_scope"], EXPECTED_SEED_SCOPE, f"{context} seed_scope")
        require_equal(row["plan_control"], EXPECTED_PLAN_CONTROL,
                      f"{context} plan_control")
        require_equal(row["plan"], EXPECTED_PLAN, f"{context} plan")
        require_equal(as_int(row, "N", context), EXPECTED_N, f"{context} N")
        require_equal(as_int(row, "D", context), EXPECTED_D, f"{context} D")
        require_equal(as_int(row, "K", context), EXPECTED_K, f"{context} K")
        require_equal(as_int(row, "queries", context), EXPECTED_QUERIES,
                      f"{context} queries")
        require_equal(as_int(row, "fixed_probes_per_query", context), EXPECTED_NPROBE,
                      f"{context} fixed_probes_per_query")
        require_equal(as_int(row, "topk_requested", context), EXPECTED_TOPK,
                      f"{context} topk_requested")
        require_number(row["nominal_B"], EXPECTED_NOMINAL_B, f"{context} nominal_B")
        require_number(row["vars_bound_m"], EXPECTED_VARS_BOUND_M,
                       f"{context} vars_bound_m")
        require_equal(as_int(row, "segments", context), 5, f"{context} segments")
        require_equal(as_int(row, "nominal_code_bits_per_vector", context),
                      EXPECTED_CODE_BITS, f"{context} nominal_code_bits_per_vector")
        require_equal(as_int(row, "candidate_evaluations", context),
                      EXPECTED_CANDIDATES, f"{context} candidate_evaluations")
        require_equal(row["exact_distance_scope"], EXPECTED_EXACT_SCOPE,
                      f"{context} exact_distance_scope")
        if as_int(row, "actual_serialized_index_bytes", context) <= 0:
            raise ValueError(f"{context}: serialized index bytes must be positive")
        if as_float(row, "actual_serialized_index_bytes_per_vector", context) <= 0:
            raise ValueError(f"{context}: serialized bytes/vector must be positive")
        transforms.add(row["transform"])
        observed_controls.add((control, seed))
        configs[config_id] = row
    expected_controls = {(f"seed{seed}", seed) for seed in EXPECTED_SEEDS} | {("off", -1)}
    require_equal(observed_controls, expected_controls, "native rotation control set")
    if len(transforms) != 1 or "" in transforms:
        raise ValueError(f"native configs must use one non-empty transform label: {transforms}")
    return configs


def validate_ranking_row(
    row: Mapping[str, str], reference: Mapping[str, str], context: str,
) -> tuple[float, float]:
    candidate_count = as_int(row, "candidate_count", context)
    require_equal(candidate_count, as_int(reference, "candidate_count", context),
                  f"{context} candidate_count")
    require_equal(as_int(row, "finite_count", context), candidate_count,
                  f"{context} finite_count")
    require_equal(as_int(row, "nonfinite_count", context), 0,
                  f"{context} nonfinite_count")
    require_equal(as_int(row, "topk_used", context), EXPECTED_TOPK,
                  f"{context} topk_used")
    agreement = as_float(row, "fixed_candidate_topk_agreement", context)
    inversions = as_int(
        row, "strict_exact_topk_vs_outside_boundary_inversions", context
    )
    pairs = as_int(row, "boundary_pairs", context)
    expected_pairs = EXPECTED_TOPK * (candidate_count - EXPECTED_TOPK)
    require_equal(pairs, expected_pairs, f"{context} boundary_pairs")
    inversion_rate = as_float(row, "strict_boundary_inversion_rate", context)
    if not 0.0 <= agreement <= 1.0:
        raise ValueError(f"{context}: top-k agreement is outside [0,1]")
    if inversions < 0 or inversions > pairs or not 0.0 <= inversion_rate <= 1.0:
        raise ValueError(f"{context}: invalid boundary inversion endpoint")
    # CSV endpoints are printed at finite decimal precision.  This tolerance is
    # only an integrity check; inference uses the emitted rate itself.
    if not math.isclose(inversion_rate, inversions / pairs, rel_tol=1e-9, abs_tol=5e-10):
        raise ValueError(f"{context}: inversion rate disagrees with count/pairs")
    rank = as_int(row, "exact_best_estimated_rank", context)
    if rank < 1 or rank > candidate_count:
        raise ValueError(f"{context}: exact-best rank is outside candidate range")
    return agreement, inversion_rate


def validate_oracle_metrics(
    rows: Sequence[Mapping[str, str]], references: Mapping[int, Mapping[str, str]],
) -> dict[tuple[str, str, int], Mapping[str, str]]:
    expected_rows = len(EXPECTED_ORACLE_GRID) * EXPECTED_QUERIES
    if len(rows) != expected_rows:
        raise ValueError(
            f"oracle metrics require exactly {expected_rows} rows, observed {len(rows)}"
        )
    indexed: dict[tuple[str, str, int], Mapping[str, str]] = {}
    observed_grid: set[tuple[str, str]] = set()
    for row in rows:
        query = as_int(row, "query", "oracle metric")
        if query not in references:
            raise ValueError(f"oracle metric has unexpected query {query}")
        arm_value = (row["arm"], row["distance_value"])
        if arm_value not in EXPECTED_ORACLE_GRID:
            raise ValueError(f"unexpected oracle arm/value {arm_value}")
        require_equal(row["tail_treatment"], EXPECTED_ORACLE_GRID[arm_value],
                      f"oracle {arm_value} q{query} tail_treatment")
        require_equal(row["distance_reference_scope"], EXPECTED_EXACT_SCOPE,
                      f"oracle {arm_value} q{query} distance_reference_scope")
        key = (*arm_value, query)
        if key in indexed:
            raise ValueError(f"duplicate oracle metric row {key}")
        reference = references[query]
        require_equal(row["candidate_ids_fnv1a64"], reference["candidate_ids_fnv1a64"],
                      f"oracle {arm_value} q{query} candidate digest")
        require_equal(row["exact_id_distance_fnv1a64"],
                      reference["exact_id_distance_fnv1a64"],
                      f"oracle {arm_value} q{query} exact-distance digest")
        estimate_digest = row["estimate_id_distance_fnv1a64"]
        if len(estimate_digest) != 16 or any(ch not in "0123456789abcdef" for ch in estimate_digest):
            raise ValueError(f"oracle {arm_value} q{query}: invalid estimate digest")
        validate_ranking_row(row, reference, f"oracle {arm_value} q{query}")
        for column in (
            "bias", "mae", "rmse", "abs_relative_eps1e-12_p50",
            "abs_relative_eps1e-12_p90", "abs_relative_eps1e-12_p99",
        ):
            value = as_float(row, column, f"oracle {arm_value} q{query}")
            if column != "bias" and value < 0:
                raise ValueError(f"oracle {arm_value} q{query}: {column} is negative")
        indexed[key] = row
        observed_grid.add(arm_value)
    require_equal(observed_grid, set(EXPECTED_ORACLE_GRID), "oracle arm/value grid")
    for arm_value in EXPECTED_ORACLE_GRID:
        queries = {key[2] for key in indexed if key[:2] == arm_value}
        require_equal(queries, set(range(EXPECTED_QUERIES)),
                      f"oracle {arm_value} query set")

    # The no-tail DP and DS arms are registered as bit-identical.
    for query in range(EXPECTED_QUERIES):
        dp = indexed[("oracle576_none", "DP", query)]
        ds = indexed[("oracle576_none", "DS", query)]
        require_equal(dp["estimate_id_distance_fnv1a64"],
                      ds["estimate_id_distance_fnv1a64"],
                      f"oracle576_none DP/DS estimate digest q{query}")
        for column in ORACLE_COLUMNS:
            if column in {"distance_value"}:
                continue
            require_equal(dp[column], ds[column],
                          f"oracle576_none DP/DS {column} q{query}")
    return indexed


def fnv1a_append(current: int, payload: bytes) -> int:
    for value in payload:
        current ^= value
        current = (current * 1_099_511_628_211) & 0xFFFFFFFFFFFFFFFF
    return current


def fnv_digest(
    ids: Sequence[int], values: Sequence[float] | None = None,
) -> str:
    if values is not None and len(values) != len(ids):
        raise ValueError("FNV ID/value lengths differ")
    digest = 14_695_981_039_346_656_037
    digest = fnv1a_append(digest, struct.pack("<Q", len(ids)))
    order = sorted(range(len(ids)), key=ids.__getitem__)
    for position in order:
        digest = fnv1a_append(digest, struct.pack("<I", ids[position]))
        if values is not None:
            bits = struct.unpack("<Q", struct.pack("<d", values[position]))[0]
            digest = fnv1a_append(digest, struct.pack("<Q", bits))
    return f"{digest:016x}"


def recompute_ranking(
    ids: Sequence[int], exact: Sequence[float], estimate: Sequence[float],
) -> dict[str, Any]:
    exact_order = sorted(range(len(ids)), key=lambda pos: (exact[pos], ids[pos]))
    estimate_order = sorted(range(len(ids)), key=lambda pos: (estimate[pos], ids[pos]))
    exact_top = set(exact_order[:EXPECTED_TOPK])
    agreement = sum(pos in exact_top for pos in estimate_order[:EXPECTED_TOPK]) / EXPECTED_TOPK
    exact_best_rank = estimate_order.index(exact_order[0]) + 1
    outside = sorted(estimate[pos] for pos in exact_order[EXPECTED_TOPK:])
    inversions = sum(
        bisect_left(outside, estimate[pos]) for pos in exact_order[:EXPECTED_TOPK]
    )
    pairs = EXPECTED_TOPK * (len(ids) - EXPECTED_TOPK)
    return {
        "fixed_candidate_topk_agreement": agreement,
        "exact_best_estimated_rank": exact_best_rank,
        "strict_exact_topk_vs_outside_boundary_inversions": inversions,
        "boundary_pairs": pairs,
        "strict_boundary_inversion_rate": inversions / pairs,
    }


def close_float(actual: float, expected: float, context: str) -> None:
    if not math.isclose(actual, expected, rel_tol=2e-12, abs_tol=5e-13):
        raise ValueError(f"{context}: expected {expected:.17g}, observed {actual:.17g}")


def validate_metric_ranking(
    row: Mapping[str, str], ranking: Mapping[str, Any], estimate_digest: str,
    context: str,
) -> None:
    require_equal(row["estimate_id_distance_fnv1a64"], estimate_digest,
                  f"{context} estimate digest")
    require_equal(
        as_int(row, "exact_best_estimated_rank", context),
        ranking["exact_best_estimated_rank"], f"{context} exact-best rank",
    )
    require_equal(
        as_int(row, "strict_exact_topk_vs_outside_boundary_inversions", context),
        ranking["strict_exact_topk_vs_outside_boundary_inversions"],
        f"{context} boundary inversions",
    )
    require_equal(as_int(row, "boundary_pairs", context), ranking["boundary_pairs"],
                  f"{context} boundary pairs")
    close_float(
        as_float(row, "fixed_candidate_topk_agreement", context),
        float(ranking["fixed_candidate_topk_agreement"]),
        f"{context} top-k agreement",
    )
    close_float(
        as_float(row, "strict_boundary_inversion_rate", context),
        float(ranking["strict_boundary_inversion_rate"]),
        f"{context} boundary inversion rate",
    )


def validate_candidate_distances(
    path: Path,
    references: Mapping[int, Mapping[str, str]],
    oracle: Mapping[tuple[str, str, int], Mapping[str, str]],
) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no CSV header")
        require_equal(tuple(reader.fieldnames), CANDIDATE_COLUMNS,
                      "candidate-distance CSV header")

        candidate_sha = hashlib.sha256()
        observed_rows = 0
        expected_query = 0
        current_query = -1
        ids: list[int] = []
        values: dict[str, list[float]] = {
            name: [] for name in ("D0", "DP_none", "DS_none", "DP_norm", "DS_norm")
        }
        seen_ids: set[int] = set()
        seen_probe_clusters: dict[int, int] = {}
        last_probe = -1
        last_base_in_probe = -1
        max_identity_none = 0.0
        max_identity_norm = 0.0
        aggregate: dict[str, dict[str, Any]] = {
            name: {
                "count": 0.0,
                "sum": 0.0,
                "abs_sum": 0.0,
                "sq_sum": 0.0,
                "query_rmse_sum": 0.0,
                "abs_errors": [],
            }
            for name in (
                "e_projection_none", "e_total_none", "e_projection_norm",
                "e_summary_norm", "e_total_norm",
            )
        }
        projection_summary_product_sum = 0.0

        def finish_query(query: int) -> None:
            nonlocal expected_query, projection_summary_product_sum
            if query < 0:
                return
            context = f"candidate distances q{query}"
            reference = references[query]
            require_equal(len(ids), as_int(reference, "candidate_count", context),
                          f"{context} row count")
            require_equal(fnv_digest(ids), reference["candidate_ids_fnv1a64"],
                          f"{context} candidate digest")
            require_equal(fnv_digest(ids, values["D0"]),
                          reference["exact_id_distance_fnv1a64"],
                          f"{context} D0 digest")
            exact_order = sorted(
                range(len(ids)), key=lambda position: (values["D0"][position], ids[position])
            )
            require_equal(ids[exact_order[0]], as_int(reference, "exact_best_id", context),
                          f"{context} exact best ID")
            top_ids = "|".join(str(ids[position]) for position in exact_order[:EXPECTED_TOPK])
            require_equal(top_ids, reference["exact_topk_ids"],
                          f"{context} exact top-k IDs")

            score_mapping = {
                ("oracle576_none", "DP"): "DP_none",
                ("oracle576_none", "DS"): "DS_none",
                ("oracle576_norm", "DP"): "DP_norm",
                ("oracle576_norm", "DS"): "DS_norm",
            }
            for arm_value, score_name in score_mapping.items():
                score = values[score_name]
                ranking = recompute_ranking(ids, values["D0"], score)
                validate_metric_ranking(
                    oracle[(*arm_value, query)], ranking, fnv_digest(ids, score),
                    f"oracle {arm_value} q{query}",
                )

            d0 = np.asarray(values["D0"])
            projection_none = np.asarray(values["DP_none"]) - d0
            total_none = np.asarray(values["DS_none"]) - d0
            projection = np.asarray(values["DP_norm"]) - d0
            summary = np.asarray(values["DS_norm"]) - np.asarray(values["DP_norm"])
            total = np.asarray(values["DS_norm"]) - d0
            for name, errors in (
                ("e_projection_none", projection_none),
                ("e_total_none", total_none),
                ("e_projection_norm", projection),
                ("e_summary_norm", summary),
                ("e_total_norm", total),
            ):
                target = aggregate[name]
                target["count"] += len(errors)
                target["sum"] += float(errors.sum(dtype=np.float64))
                target["abs_sum"] += float(np.abs(errors).sum(dtype=np.float64))
                target["sq_sum"] += float(np.square(errors).sum(dtype=np.float64))
                target["query_rmse_sum"] += float(
                    np.sqrt(np.square(errors).mean(dtype=np.float64))
                )
                target["abs_errors"].extend(np.abs(errors).tolist())
            projection_summary_product_sum += float(
                np.multiply(projection, summary).sum(dtype=np.float64)
            )
            expected_query += 1

        for row in reader:
            context = f"candidate-distance row {observed_rows + 2}"
            query = as_int(row, "query", context)
            if query != current_query:
                finish_query(current_query)
                require_equal(query, expected_query, f"{context} query order")
                current_query = query
                ids = []
                values = {
                    name: [] for name in ("D0", "DP_none", "DS_none", "DP_norm", "DS_norm")
                }
                seen_ids = set()
                seen_probe_clusters = {}
                last_probe = -1
                last_base_in_probe = -1
                count = as_int(references[query], "candidate_count", context)
                candidate_sha.update(struct.pack("<IQ", query, count))

            position = as_int(row, "candidate_position", context)
            require_equal(position, len(ids), f"{context} candidate_position")
            probe = as_int(row, "probe_position", context)
            cluster = as_int(row, "cluster_id", context)
            base_id = as_int(row, "base_id", context)
            if not 0 <= probe < EXPECTED_NPROBE:
                raise ValueError(f"{context}: probe_position is outside 0..15")
            if not 0 <= cluster < EXPECTED_K:
                raise ValueError(f"{context}: cluster_id is outside 0..511")
            if not 0 <= base_id < EXPECTED_N:
                raise ValueError(f"{context}: base_id is outside 0..49999")
            if base_id in seen_ids:
                raise ValueError(f"{context}: duplicate candidate base_id {base_id}")
            if probe < last_probe:
                raise ValueError(f"{context}: probe_position is not monotonic")
            if probe == last_probe:
                require_equal(cluster, seen_probe_clusters[probe],
                              f"{context} cluster within probe")
                if base_id <= last_base_in_probe:
                    raise ValueError(f"{context}: base IDs are not ascending within probe")
            else:
                if probe in seen_probe_clusters:
                    raise ValueError(f"{context}: repeated probe_position {probe}")
                seen_probe_clusters[probe] = cluster
                last_base_in_probe = -1
            last_probe = probe
            last_base_in_probe = base_id
            seen_ids.add(base_id)
            ids.append(base_id)
            candidate_sha.update(struct.pack("<i", base_id))

            parsed = {name: as_float(row, name, context) for name in values}
            if any(value < 0.0 for value in parsed.values()):
                raise ValueError(f"{context}: a squared-distance value is negative")
            for name, value in parsed.items():
                values[name].append(value)
            if struct.pack("<d", parsed["DP_none"]) != struct.pack("<d", parsed["DS_none"]):
                raise ValueError(f"{context}: DP_none and DS_none are not bit-identical")

            expected_errors = {
                "e_projection_none": parsed["DP_none"] - parsed["D0"],
                "e_summary_none": parsed["DS_none"] - parsed["DP_none"],
                "e_total_none": parsed["DS_none"] - parsed["D0"],
                "e_projection_norm": parsed["DP_norm"] - parsed["D0"],
                "e_summary_norm": parsed["DS_norm"] - parsed["DP_norm"],
                "e_total_norm": parsed["DS_norm"] - parsed["D0"],
            }
            for column, expected in expected_errors.items():
                observed = as_float(row, column, context)
                tolerance = 1e-10 * max(1.0, abs(expected))
                if abs(observed - expected) > tolerance:
                    raise ValueError(
                        f"{context}: {column} violates its registered definition"
                    )
            expected_identity_none = (
                expected_errors["e_total_none"] - expected_errors["e_projection_none"]
                - expected_errors["e_summary_none"]
            )
            expected_identity_norm = (
                expected_errors["e_total_norm"] - expected_errors["e_projection_norm"]
                - expected_errors["e_summary_norm"]
            )
            identity_none = as_float(row, "error_sum_identity_none", context)
            identity_norm = as_float(row, "error_sum_identity_norm", context)
            close_float(identity_none, expected_identity_none,
                        f"{context} none error identity")
            close_float(identity_norm, expected_identity_norm,
                        f"{context} norm error identity")
            if abs(identity_none) > 1e-10 * max(1.0, abs(expected_errors["e_total_none"])):
                raise ValueError(f"{context}: none error identity exceeds tolerance")
            if abs(identity_norm) > 1e-10 * max(1.0, abs(expected_errors["e_total_norm"])):
                raise ValueError(f"{context}: norm error identity exceeds tolerance")
            max_identity_none = max(max_identity_none, abs(identity_none))
            max_identity_norm = max(max_identity_norm, abs(identity_norm))
            observed_rows += 1

        finish_query(current_query)

    require_equal(expected_query, EXPECTED_QUERIES, "candidate-distance query count")
    require_equal(observed_rows, EXPECTED_CANDIDATES, "candidate-distance row count")
    require_equal(candidate_sha.hexdigest(), EXPECTED_CANDIDATE_SHA256,
                  "candidate-distance registered inventory SHA-256")

    diagnostics: dict[str, Any] = {}
    for name, values_sum in aggregate.items():
        count = values_sum["count"]
        absolute_errors = np.asarray(values_sum["abs_errors"], dtype=np.float64)
        require_equal(absolute_errors.shape, (EXPECTED_CANDIDATES,),
                      f"{name} absolute-error sample count")
        if not np.all(np.isfinite(absolute_errors)):
            raise ValueError(f"{name} contains a non-finite absolute error")
        p50, p90, p99 = np.percentile(
            absolute_errors, (50.0, 90.0, 99.0), method="linear"
        )
        diagnostics[name] = {
            "candidate_count": int(count),
            "pooled_bias": values_sum["sum"] / count,
            "pooled_mae": values_sum["abs_sum"] / count,
            "equal_query_mean_rmse": (
                values_sum["query_rmse_sum"] / EXPECTED_QUERIES
            ),
            "pooled_rmse": math.sqrt(values_sum["sq_sum"] / count),
            "pooled_absolute_error_p50": float(p50),
            "pooled_absolute_error_p90": float(p90),
            "pooled_absolute_error_p99": float(p99),
        }
    projection_mean = aggregate["e_projection_norm"]["sum"] / EXPECTED_CANDIDATES
    summary_mean = aggregate["e_summary_norm"]["sum"] / EXPECTED_CANDIDATES
    diagnostics["projection_summary_population_covariance"] = (
        projection_summary_product_sum / EXPECTED_CANDIDATES
        - projection_mean * summary_mean
    )
    diagnostics["error_sum_identity_max_abs"] = {
        "none": max_identity_none,
        "norm": max_identity_norm,
    }
    return diagnostics


def validate_native_queries(
    rows: Sequence[Mapping[str, str]],
    configs: Mapping[str, Mapping[str, str]],
    references: Mapping[int, Mapping[str, str]],
) -> dict[tuple[str, int, str], Mapping[str, str]]:
    expected_rows = 11 * EXPECTED_QUERIES * len(EXPECTED_NATIVE_STAGES)
    if len(rows) != expected_rows:
        raise ValueError(
            f"native query stages require exactly {expected_rows} rows, observed {len(rows)}"
        )
    indexed: dict[tuple[str, int, str], Mapping[str, str]] = {}
    per_config_stages: dict[str, set[tuple[int, str]]] = defaultdict(set)
    transforms: set[str] = set()
    for row in rows:
        config_id = row["config_id"]
        config = configs.get(config_id)
        if config is None:
            raise ValueError(f"native query row references unknown config {config_id!r}")
        query = as_int(row, "query", f"native {config_id}")
        if query not in references:
            raise ValueError(f"native {config_id} has unexpected query {query}")
        stage = row["stage"]
        if stage not in EXPECTED_NATIVE_STAGES:
            raise ValueError(f"native {config_id} has unexpected stage {stage!r}")
        for column in (
            "transform", "plan_control", "rotation_control", "rotation_seed"
        ):
            require_equal(row[column], config[column],
                          f"native {config_id}/q{query}/{stage} {column}")
        require_equal(row["distance_reference_scope"], EXPECTED_EXACT_SCOPE,
                      f"native {config_id}/q{query}/{stage} exact scope")
        if stage == "full":
            require_equal(row["stage_semantics"], "progressive_distance_estimate",
                          f"native {config_id}/q{query}/full semantics")
        key = (row["rotation_control"], query, stage)
        if key in indexed:
            raise ValueError(f"duplicate native query-stage row {key}")
        if stage == "full":
            validate_ranking_row(
                row, references[query], f"native {config_id}/q{query}/full"
            )
        else:
            # Completeness rows are not inference endpoints, but non-finite
            # values would indicate the native run did not satisfy its contract.
            candidate_count = as_int(row, "candidate_count", f"native {config_id}/{stage}")
            require_equal(candidate_count,
                          as_int(references[query], "candidate_count", "reference"),
                          f"native {config_id}/q{query}/{stage} candidate_count")
            require_equal(as_int(row, "finite_count", f"native {config_id}/{stage}"),
                          candidate_count, f"native {config_id}/q{query}/{stage} finite_count")
            require_equal(as_int(row, "nonfinite_count", f"native {config_id}/{stage}"),
                          0, f"native {config_id}/q{query}/{stage} nonfinite_count")
        indexed[key] = row
        per_config_stages[config_id].add((query, stage))
        transforms.add(row["transform"])
    expected_grid = {
        (query, stage) for query in range(EXPECTED_QUERIES)
        for stage in EXPECTED_NATIVE_STAGES
    }
    for config_id, grid in per_config_stages.items():
        require_equal(grid, expected_grid, f"native {config_id} query-stage grid")
    require_equal(set(per_config_stages), set(configs), "native config/query linkage")
    if len(transforms) != 1:
        raise ValueError("native query rows must have one transform label")
    return indexed


def percentile_bootstrap(
    values: np.ndarray, bootstrap_indices: np.ndarray,
) -> tuple[float, float, float]:
    if values.shape != (EXPECTED_QUERIES,) or not np.all(np.isfinite(values)):
        raise ValueError("bootstrap input must be 128 finite query-paired deltas")
    replicates = values[bootstrap_indices].mean(axis=1)
    return (
        float(values.mean()),
        float(np.percentile(replicates, 5.0, method="linear")),
        float(np.percentile(replicates, 95.0, method="linear")),
    )


def endpoint_record(
    point: float, lower: float, upper: float, favorable: str,
) -> dict[str, Any]:
    if favorable == "higher":
        passed = lower >= 0.0
        criterion = "one_sided_95_percent_lower_bound_gte_zero"
        decision_bound = lower
    elif favorable == "lower":
        passed = upper <= 0.0
        criterion = "one_sided_95_percent_upper_bound_lte_zero"
        decision_bound = upper
    else:
        raise ValueError(f"unknown favorable direction {favorable!r}")
    return {
        "point_estimate": point,
        "one_sided_95_lower": lower,
        "one_sided_95_upper": upper,
        "favorable_direction": favorable,
        "criterion": criterion,
        "decision_bound": decision_bound,
        "pass": passed,
    }


def infer(
    oracle: Mapping[tuple[str, str, int], Mapping[str, str]],
    native: Mapping[tuple[str, int, str], Mapping[str, str]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rng = np.random.default_rng(EXPECTED_BOOTSTRAP_SEED)
    indices = rng.integers(
        0, EXPECTED_QUERIES,
        size=(EXPECTED_BOOTSTRAP_REPLICATES, EXPECTED_QUERIES),
        endpoint=False,
    )
    per_query: list[dict[str, Any]] = []
    group_results: dict[str, Any] = {}
    for group in ("seed_average", "off"):
        agreement_deltas: list[float] = []
        inversion_deltas: list[float] = []
        oracle_agreements: list[float] = []
        native_agreements: list[float] = []
        oracle_inversions: list[float] = []
        native_inversions: list[float] = []
        for query in range(EXPECTED_QUERIES):
            oracle_row = oracle[("oracle576_norm", "DP", query)]
            oracle_agreement = as_float(
                oracle_row, "fixed_candidate_topk_agreement", "oracle confirmatory"
            )
            oracle_inversion = as_float(
                oracle_row, "strict_boundary_inversion_rate", "oracle confirmatory"
            )
            controls = [f"seed{seed}" for seed in EXPECTED_SEEDS] if group == "seed_average" else ["off"]
            native_rows = [native[(control, query, "full")] for control in controls]
            native_agreement = math.fsum(
                as_float(row, "fixed_candidate_topk_agreement", "native full")
                for row in native_rows
            ) / len(native_rows)
            native_inversion = math.fsum(
                as_float(row, "strict_boundary_inversion_rate", "native full")
                for row in native_rows
            ) / len(native_rows)
            agreement_delta = oracle_agreement - native_agreement
            inversion_delta = oracle_inversion - native_inversion
            agreement_deltas.append(agreement_delta)
            inversion_deltas.append(inversion_delta)
            oracle_agreements.append(oracle_agreement)
            native_agreements.append(native_agreement)
            oracle_inversions.append(oracle_inversion)
            native_inversions.append(native_inversion)
            per_query.append(
                {
                    "rotation_group": group,
                    "query": query,
                    "oracle_topk_agreement": oracle_agreement,
                    "native_topk_agreement": native_agreement,
                    "topk_agreement_delta": agreement_delta,
                    "oracle_boundary_inversion_rate": oracle_inversion,
                    "native_boundary_inversion_rate": native_inversion,
                    "boundary_inversion_rate_delta": inversion_delta,
                    "native_rotation_config_count": len(native_rows),
                }
            )
        agreement_stats = percentile_bootstrap(np.asarray(agreement_deltas), indices)
        inversion_stats = percentile_bootstrap(np.asarray(inversion_deltas), indices)
        agreement_result = endpoint_record(*agreement_stats, favorable="higher")
        inversion_result = endpoint_record(*inversion_stats, favorable="lower")
        group_results[group] = {
            "query_count": EXPECTED_QUERIES,
            "native_rotation_config_count": 10 if group == "seed_average" else 1,
            "mean_absolute_endpoints": {
                "oracle_topk_agreement": float(np.mean(oracle_agreements)),
                "native_topk_agreement": float(np.mean(native_agreements)),
                "oracle_boundary_inversion_rate": float(np.mean(oracle_inversions)),
                "native_boundary_inversion_rate": float(np.mean(native_inversions)),
            },
            "topk_agreement_delta": agreement_result,
            "boundary_inversion_rate_delta": inversion_result,
            "pass": agreement_result["pass"] and inversion_result["pass"],
        }
    return group_results, per_query


def input_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve(strict=True)),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    columns = (
        "rotation_group", "query", "oracle_topk_agreement",
        "native_topk_agreement", "topk_agreement_delta",
        "oracle_boundary_inversion_rate", "native_boundary_inversion_rate",
        "boundary_inversion_rate_delta", "native_rotation_config_count",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def format_number(value: float) -> str:
    return f"{value:.10g}"


def write_markdown(path: Path, report: Mapping[str, Any]) -> None:
    confirmatory = report["inference"]["seed_average"]
    off = report["inference"]["off"]
    agreement = confirmatory["topk_agreement_delta"]
    inversion = confirmatory["boundary_inversion_rate_delta"]
    lines = [
        "# LP-0 Gate A Evidence",
        "",
        f"**Decision: {'PASS' if report['gate_a']['pass'] else 'FAIL'}**",
        "",
        "The confirmatory comparison is `oracle576_norm.DP - "
        "native_full_saq.full`. Positive agreement delta and negative boundary-"
        "inversion delta are favorable. Ten logical rotations are averaged within "
        "each query before the paired query bootstrap.",
        "",
        "| Rotation group | Endpoint | Point delta | One-sided 95% lower | "
        "One-sided 95% upper | Criterion | Pass |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for group_name, group in (("seed average", confirmatory), ("rotation off", off)):
        for endpoint, label in (
            ("topk_agreement_delta", "top-100 agreement"),
            ("boundary_inversion_rate_delta", "boundary inversion rate"),
        ):
            result = group[endpoint]
            lines.append(
                f"| {group_name} | {label} | {format_number(result['point_estimate'])} | "
                f"{format_number(result['one_sided_95_lower'])} | "
                f"{format_number(result['one_sided_95_upper'])} | "
                f"{result['criterion']} | {'yes' if result['pass'] else 'no'} |"
            )
    lines.extend(
        [
            "",
            "| Rotation group | Oracle agreement | Native agreement | "
            "Oracle inversion | Native inversion |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for group_name, group in (("seed average", confirmatory), ("rotation off", off)):
        absolute = group["mean_absolute_endpoints"]
        lines.append(
            f"| {group_name} | {format_number(absolute['oracle_topk_agreement'])} | "
            f"{format_number(absolute['native_topk_agreement'])} | "
            f"{format_number(absolute['oracle_boundary_inversion_rate'])} | "
            f"{format_number(absolute['native_boundary_inversion_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Original-Space Error Diagnostics",
            "",
            "| Component | Pooled bias | Pooled MAE | Equal-query mean RMSE | "
            "Pooled RMSE | Abs. error p50 | p90 | p99 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    diagnostics = report["distance_diagnostics"]
    for key, label in (
        ("e_projection_none", "pure-head projection (`DP_none-D0`)"),
        ("e_total_none", "pure-head total (`DS_none-D0`)"),
        ("e_projection_norm", "tail-norm projection (`DP_norm-D0`)"),
        ("e_summary_norm", "tail-summary precision (`DS_norm-DP_norm`)"),
        ("e_total_norm", "tail-norm oracle total (`DS_norm-D0`)"),
    ):
        values = diagnostics[key]
        lines.append(
            f"| {label} | {format_number(values['pooled_bias'])} | "
            f"{format_number(values['pooled_mae'])} | "
            f"{format_number(values['equal_query_mean_rmse'])} | "
            f"{format_number(values['pooled_rmse'])} | "
            f"{format_number(values['pooled_absolute_error_p50'])} | "
            f"{format_number(values['pooled_absolute_error_p90'])} | "
            f"{format_number(values['pooled_absolute_error_p99'])} |"
        )
    lines.extend(
        [
            "",
            "Projection-summary population covariance: "
            f"`{format_number(diagnostics['projection_summary_population_covariance'])}`. "
            "These are diagnostics; Gate A is decided only by the two paired "
            "ranking bounds above.",
            "",
            "## Registered Interpretation",
            "",
        ]
    )
    if report["gate_a"]["pass"]:
        lines.append(
            "Gate A passes at the frozen GIST, `d=576`, and `B=4` point. This is "
            "an exact-head upper-bound result only; it authorizes Gate B "
            "projected-SAQ evaluation but is not evidence of a physical-"
            "projection or SAQ-specific contribution."
        )
    else:
        failed = []
        if not agreement["pass"]:
            failed.append("top-100 agreement lower bound")
        if not inversion["pass"]:
            failed.append("boundary-inversion upper bound")
        lines.append(
            "Gate A fails because the registered " + " and ".join(failed) +
            " did not satisfy the zero-margin condition. Conclude only that the "
            "frozen GIST/`d=576`/`B=4` upper-bound point found insufficient "
            "evidence; do not generalize to projection universally."
        )
    lines.extend(
        [
            "",
            "Rotation-off is a separate diagnostic and does not alter the "
            "confirmatory decision.",
            "",
            "## Integrity And Inference Contract",
            "",
            f"- Queries: {EXPECTED_QUERIES}; candidates: {EXPECTED_CANDIDATES:,}. ",
            f"- Candidate inventory SHA-256: `{EXPECTED_CANDIDATE_SHA256}`.",
            f"- Bootstrap: {EXPECTED_BOOTSTRAP_REPLICATES:,} paired query "
            f"resamples, seed `{EXPECTED_BOOTSTRAP_SEED}`, linear percentiles.",
            "- Native logical seeds: `0..9`; C RNG mapping: `srand(s+1)`; "
            "rotation-off is `srand(0)` with rotation disabled.",
            "- Exact labels: canonical original-space float64 squared L2.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def output_paths(prefix: Path) -> tuple[Path, Path, Path]:
    return (
        Path(f"{prefix}.json"),
        Path(f"{prefix}.md"),
        Path(f"{prefix}.per_query.csv"),
    )


def evaluate(
    oracle_prefix: Path, native_prefix: Path, native_manifest_path: Path,
    output_prefix: Path,
) -> dict[str, Any]:
    oracle_metrics_path = Path(f"{oracle_prefix}.query_metrics.csv")
    oracle_reference_path = Path(f"{oracle_prefix}.query_reference.csv")
    oracle_candidate_path = Path(f"{oracle_prefix}.candidate_distances.csv")
    oracle_manifest_path = Path(f"{oracle_prefix}.manifest.json")
    native_query_path = Path(f"{native_prefix}.query_stages.csv")
    native_config_path = Path(f"{native_prefix}.configs.csv")
    native_reference_path = Path(f"{native_prefix}.query_reference.csv")

    oracle_manifest = load_json(oracle_manifest_path)
    native_manifest = load_json(native_manifest_path)
    oracle_rows = load_csv(oracle_metrics_path, ORACLE_COLUMNS)
    oracle_references = load_csv(oracle_reference_path, REFERENCE_COLUMNS)
    native_rows = load_csv(native_query_path, NATIVE_QUERY_COLUMNS)
    native_configs = load_csv(native_config_path, NATIVE_CONFIG_COLUMNS)
    native_references = load_csv(native_reference_path, REFERENCE_COLUMNS)

    validate_manifest(
        oracle_manifest, oracle_manifest_path, oracle_metrics_path,
        oracle_reference_path, oracle_candidate_path,
    )
    validate_native_manifest(native_manifest, native_manifest_path, native_prefix)
    references = validate_references(
        oracle_references, native_references,
        oracle_reference_path, native_reference_path,
    )
    oracle = validate_oracle_metrics(oracle_rows, references)
    distance_diagnostics = validate_candidate_distances(
        oracle_candidate_path, references, oracle
    )
    configs = validate_native_configs(native_configs)
    native = validate_native_queries(native_rows, configs, references)
    inference, per_query = infer(oracle, native)
    gate_pass = bool(inference["seed_average"]["pass"])

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "complete",
        "gate_a": {
            "name": "LP-0 Gate A: Exact-Surrogate Upper-Bound Screen",
            "comparison": "oracle576_norm.DP - native_full_saq.full",
            "decision_group": "seed_average",
            "pass": gate_pass,
            "next_action": (
                "authorize_gate_b_projected_saq_only" if gate_pass else
                "stop_registered_gist_d576_b4_line"
            ),
        },
        "artifact_validation": {
            "pass": True,
            "dataset": EXPECTED_DATASET,
            "N": EXPECTED_N,
            "D": EXPECTED_D,
            "d": EXPECTED_PROJECTED_D,
            "queries": EXPECTED_QUERIES,
            "candidate_count": EXPECTED_CANDIDATES,
            "candidate_inventory_sha256": EXPECTED_CANDIDATE_SHA256,
            "query_reference_files_byte_identical": True,
            "native_config_count": len(configs),
            "native_seed_grid_complete": True,
            "oracle_arm_grid_complete": True,
            "candidate_distance_rows_validated": EXPECTED_CANDIDATES,
        },
        "distance_diagnostics": distance_diagnostics,
        "inference_contract": {
            "delta": "oracle576_norm.DP - native_full_saq.full",
            "seed_aggregation": "average logical seeds 0..9 within each query",
            "sampling_unit": "query",
            "bootstrap_replicates": EXPECTED_BOOTSTRAP_REPLICATES,
            "bootstrap_seed": EXPECTED_BOOTSTRAP_SEED,
            "percentile_method": "numpy.percentile linear",
            "one_sided_confidence": 0.95,
            "agreement_condition": "5th percentile >= 0",
            "inversion_condition": "95th percentile <= 0",
            "rotation_off_role": "separate diagnostic, not a gate condition",
        },
        "inference": inference,
        "inputs": {
            "oracle_manifest": input_record(oracle_manifest_path),
            "oracle_query_metrics": input_record(oracle_metrics_path),
            "oracle_query_reference": input_record(oracle_reference_path),
            "oracle_candidate_distances": input_record(oracle_candidate_path),
            "native_query_stages": input_record(native_query_path),
            "native_configs": input_record(native_config_path),
            "native_query_reference": input_record(native_reference_path),
            "native_comparator_manifest": input_record(native_manifest_path),
        },
    }

    json_path, markdown_path, per_query_path = output_paths(output_prefix)
    for path in (json_path, markdown_path, per_query_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(per_query_path, per_query)
    report["outputs"] = {
        "per_query_csv": input_record(per_query_path),
        "markdown": {"path": str(markdown_path.resolve())},
        "json": {"path": str(json_path.resolve())},
    }
    write_markdown(markdown_path, report)
    report["outputs"]["markdown"].update(
        {"bytes": markdown_path.stat().st_size, "sha256": sha256_file(markdown_path)}
    )
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--oracle-prefix", required=True, type=Path,
        help=("Prefix providing .manifest.json, .query_metrics.csv, "
              ".query_reference.csv, and .candidate_distances.csv"),
    )
    parser.add_argument(
        "--native-prefix", required=True, type=Path,
        help="Native Phase-1 prefix providing .configs.csv, .query_stages.csv, and .query_reference.csv",
    )
    parser.add_argument(
        "--native-manifest", required=True, type=Path,
        help="Frozen native comparator manifest",
    )
    parser.add_argument(
        "--output-prefix", required=True, type=Path,
        help="Output prefix for .json, .md, and .per_query.csv",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = evaluate(
            args.oracle_prefix, args.native_prefix, args.native_manifest,
            args.output_prefix,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"LP-0 Gate A input validation failed: {error}", file=sys.stderr)
        return 2
    print(
        f"LP-0 Gate A: {'PASS' if report['gate_a']['pass'] else 'FAIL'}; "
        f"wrote {args.output_prefix}.json/.md/.per_query.csv"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
