#!/usr/bin/env python3
"""Summarize the fixed-candidate SAQ Phase-1 transform diagnostic.

The C++ diagnostic writes one CSV triplet per transform view. This script
combines those triplets and uses NumPy to vectorize the query bootstrap.
Rotation seeds 0..9 are averaged *within each query* before any cross-transform inference;
the no-rotation control is kept as a separate group.  Paired confidence
intervals therefore use queries, not candidates or rotation seeds, as the
sampling unit.

Example:

    python script/summarize_phase1_transform.py \
      --output-prefix results/phase1/summary \
      current_pca=results/phase1/current_pca \
      identity=results/phase1/identity \
      residual_pca=results/phase1/residual_pca \
      random_orthogonal=results/phase1/random_orthogonal

Each input is ``[LABEL=]PREFIX`` and must provide ``PREFIX.query_stages.csv``,
``PREFIX.segment_errors.csv``, and ``PREFIX.configs.csv``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np


EXPECTED_ROTATION_SEEDS = tuple(range(10))
COMMON_STAGES = (
    "vars_conservative_lower_bound_all",
    "fast_all",
    "full",
)
DEFAULT_BOOTSTRAP_REPLICATES = 5000
DEFAULT_BOOTSTRAP_SEED = 20260710

QUERY_REQUIRED = {
    "transform",
    "config_id",
    "plan_control",
    "rotation_control",
    "rotation_seed",
    "query",
    "stage",
    "stage_semantics",
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
    "logical_factor_bytes_per_candidate",
    "logical_fast_code_bytes_per_candidate",
    "logical_long_code_bytes_per_candidate",
    "logical_long_factor_bytes_per_candidate",
    "logical_total_requested_bytes_per_candidate",
    "logical_byte_model",
}

CONFIG_REQUIRED = {
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
    "transform_planner_proxy_total",
    "pca_planner_proxy_total",
    "actual_serialized_index_bytes",
    "actual_serialized_index_bytes_per_vector",
    "build_time_s",
    "serialization_time_s",
    "measurement_time_s",
    "candidate_evaluations",
    "exact_distance_scope",
}

SEGMENT_REQUIRED = {
    "transform",
    "config_id",
    "plan_control",
    "rotation_control",
    "rotation_seed",
    "segment",
    "offset",
    "dimensions",
    "bits",
    "distance_mode",
    "total_count",
    "finite_count",
    "nonfinite_count",
    "mae",
    "rmse",
    "transform_variance_sum",
    "pca_variance_sum",
    "transform_planner_proxy",
    "pca_planner_proxy",
    "accurate_distance_implied_ip_abs_error_mean",
    "accurate_distance_implied_ip_sq_error_mean",
}

QUERY_NUMERIC_COLUMNS = (
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
    "logical_factor_bytes_per_candidate",
    "logical_fast_code_bytes_per_candidate",
    "logical_long_code_bytes_per_candidate",
    "logical_long_factor_bytes_per_candidate",
    "logical_total_requested_bytes_per_candidate",
)

CONFIG_NUMERIC_COLUMNS = (
    "N",
    "D",
    "K",
    "queries",
    "fixed_probes_per_query",
    "topk_requested",
    "nominal_B",
    "vars_bound_m",
    "segments",
    "nominal_code_bits_per_vector",
    "transform_planner_proxy_total",
    "pca_planner_proxy_total",
    "actual_serialized_index_bytes",
    "actual_serialized_index_bytes_per_vector",
    "build_time_s",
    "serialization_time_s",
    "measurement_time_s",
    "candidate_evaluations",
)

CONFIG_STRUCTURAL_NUMERIC_COLUMNS = (
    "N",
    "D",
    "K",
    "queries",
    "fixed_probes_per_query",
    "topk_requested",
    "nominal_B",
    "vars_bound_m",
    "segments",
    "nominal_code_bits_per_vector",
    "transform_planner_proxy_total",
    "pca_planner_proxy_total",
    "actual_serialized_index_bytes",
    "actual_serialized_index_bytes_per_vector",
    "candidate_evaluations",
)

CONFIG_TIMING_COLUMNS = (
    "build_time_s",
    "serialization_time_s",
    "measurement_time_s",
)

SEGMENT_NUMERIC_COLUMNS = (
    "segment",
    "offset",
    "dimensions",
    "bits",
    "mae",
    "rmse",
    "transform_variance_sum",
    "pca_variance_sum",
    "transform_planner_proxy",
    "pca_planner_proxy",
    "accurate_distance_implied_ip_abs_error_mean",
    "accurate_distance_implied_ip_sq_error_mean",
)


@dataclass(frozen=True)
class MetricSpec:
    output_name: str
    input_name: str
    better: str
    aggregation: str = "mean"


METRICS = (
    MetricSpec("mean_per_query_candidate_rmse", "rmse", "lower"),
    MetricSpec("pooled_candidate_rmse", "candidate_mse", "lower", "pooled_rmse"),
    MetricSpec("candidate_mae", "mae", "lower"),
    MetricSpec(
        "topk_agreement", "fixed_candidate_topk_agreement", "higher"
    ),
    MetricSpec(
        "boundary_inversion_rate", "strict_boundary_inversion_rate", "lower"
    ),
    MetricSpec("exact_best_rank", "exact_best_estimated_rank", "lower"),
)


@dataclass(frozen=True)
class InputBundle:
    label: str
    prefix: Path
    source_transform: str
    query_rows: tuple[dict[str, str], ...]
    segment_rows: tuple[dict[str, str], ...]
    config_rows: tuple[dict[str, str], ...]


def parse_number(value: str, column: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"column {column!r} has non-numeric value {value!r}") from error


def parse_integer(value: str, column: str) -> int:
    number = parse_number(value, column)
    if not math.isfinite(number) or number != int(number):
        raise ValueError(f"column {column!r} must be an integer, got {value!r}")
    return int(number)


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no CSV header")
        missing = sorted(required.difference(reader.fieldnames))
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError(f"{path} contains no data rows")
    return rows


def split_input_spec(specification: str) -> tuple[str | None, Path]:
    if "=" not in specification:
        return None, Path(specification)
    label, prefix = specification.split("=", 1)
    if not label or not prefix:
        raise ValueError(f"invalid input specification {specification!r}")
    return label, Path(prefix)


def load_bundle(specification: str) -> InputBundle:
    explicit_label, prefix = split_input_spec(specification)
    query_rows = read_csv(Path(f"{prefix}.query_stages.csv"), QUERY_REQUIRED)
    segment_rows = read_csv(Path(f"{prefix}.segment_errors.csv"), SEGMENT_REQUIRED)
    config_rows = read_csv(Path(f"{prefix}.configs.csv"), CONFIG_REQUIRED)
    source_transforms = {
        row["transform"]
        for rows in (query_rows, segment_rows, config_rows)
        for row in rows
    }
    if len(source_transforms) != 1:
        raise ValueError(
            f"{prefix} must contain exactly one common transform label, got "
            f"{sorted(source_transforms)}"
        )
    source_transform = next(iter(source_transforms))
    label = explicit_label or source_transform
    if not label:
        raise ValueError(f"{prefix} has an empty transform label")
    for rows in (query_rows, segment_rows, config_rows):
        for row in rows:
            row["transform"] = label
    return InputBundle(
        label=label,
        prefix=prefix,
        source_transform=source_transform,
        query_rows=tuple(query_rows),
        segment_rows=tuple(segment_rows),
        config_rows=tuple(config_rows),
    )


def rotation_group(row: Mapping[str, str]) -> tuple[str, int | None]:
    control = row["rotation_control"]
    seed = parse_integer(row["rotation_seed"], "rotation_seed")
    if control == "off":
        if seed != -1:
            raise ValueError(f"off rotation must use seed -1, got {seed}")
        return "off", None
    if seed not in EXPECTED_ROTATION_SEEDS:
        raise ValueError(
            f"seeded rotation must use one of 0..9, got control={control!r}, seed={seed}"
        )
    expected_control = f"seed{seed}"
    if control != expected_control:
        raise ValueError(
            f"rotation control {control!r} does not match rotation_seed={seed}; "
            f"expected {expected_control!r}"
        )
    return "seed_average", seed


def validate_raw_relations(
    query_rows: Sequence[Mapping[str, str]],
    segment_rows: Sequence[Mapping[str, str]],
    config_rows: Sequence[Mapping[str, str]],
    baseline: str,
) -> None:
    """Validate config linkage and fixed-candidate invariants before collapse."""

    configs: dict[tuple[str, str], Mapping[str, str]] = {}
    config_grid: dict[str, set[tuple[str, str, int]]] = defaultdict(set)
    plans: dict[tuple[str, str, str, int], Mapping[str, str]] = {}
    for row in config_rows:
        transform = row["transform"]
        config_id = row["config_id"]
        key = (transform, config_id)
        if key in configs:
            raise ValueError(f"duplicate config row for {transform}/{config_id}")
        group, seed = rotation_group(row)
        del group
        numeric_seed = -1 if seed is None else seed
        rotation_enabled = parse_integer(row["rotation_enabled"], "rotation_enabled")
        if rotation_enabled not in {0, 1} or rotation_enabled != int(seed is not None):
            raise ValueError(
                f"rotation_enabled disagrees with control for {transform}/{config_id}"
            )
        configs[key] = row
        config_grid[transform].add(
            (row["plan_control"], row["rotation_control"], numeric_seed)
        )
        plans[(transform, row["plan_control"], row["rotation_control"], numeric_seed)] = row

    if baseline not in config_grid:
        raise ValueError(f"baseline {baseline!r} has no config rows")
    expected_controls = {(f"seed{seed}", seed) for seed in EXPECTED_ROTATION_SEEDS}
    expected_controls.add(("off", -1))
    baseline_grid = config_grid[baseline]
    baseline_plans = {item[0] for item in baseline_grid}
    for transform, grid in config_grid.items():
        if grid != baseline_grid:
            missing = sorted(baseline_grid.difference(grid))
            extra = sorted(grid.difference(baseline_grid))
            raise ValueError(
                f"config grid mismatch for {transform}: missing={missing}, extra={extra}"
            )
        for plan in baseline_plans:
            observed_controls = {(control, seed) for item_plan, control, seed in grid if item_plan == plan}
            if observed_controls != expected_controls:
                raise ValueError(
                    f"{transform}/{plan} must contain rotation seeds 0..9 and off exactly"
                )

    for transform in config_grid:
        for plan in baseline_plans:
            for control, seed in expected_controls:
                candidate = plans[(transform, plan, control, seed)]
                reference = plans[(baseline, plan, control, seed)]
                if candidate["exact_distance_scope"] != reference["exact_distance_scope"]:
                    raise ValueError(
                        f"exact-distance scope mismatch for {transform}/{plan}/{control}"
                    )
                if plan in {"frozen-pca", "uniform"}:
                    for column in ("plan", "nominal_code_bits_per_vector"):
                        if candidate[column] != reference[column]:
                            raise ValueError(
                                f"matched-plan contract mismatch for {transform}/{plan}/{control}: "
                                f"{column} differs from PCA"
                            )

    seen_query: set[tuple[str, str, int, str]] = set()
    structural_groups: dict[
        tuple[str, str, int, str], list[Mapping[str, str]]
    ] = defaultdict(list)
    common_stage_rows: dict[
        tuple[str, str, str, int, int, str], Mapping[str, str]
    ] = {}
    all_stage_rows: dict[
        tuple[str, str, str, int, int, str], Mapping[str, str]
    ] = {}
    for row in query_rows:
        config_key = (row["transform"], row["config_id"])
        config = configs.get(config_key)
        if config is None:
            raise ValueError(
                f"orphan query row references unknown config {config_key[0]}/{config_key[1]}"
            )
        for column in ("plan_control", "rotation_control", "rotation_seed"):
            if row[column] != config[column]:
                raise ValueError(
                    f"query/config mismatch for {config_key[0]}/{config_key[1]}: {column}"
                )
        rotation_group(row)
        query = parse_integer(row["query"], "query")
        unique_key = (row["transform"], row["config_id"], query, row["stage"])
        if unique_key in seen_query:
            raise ValueError(f"duplicate query-stage row for {unique_key}")
        seen_query.add(unique_key)
        candidate_count = parse_integer(row["candidate_count"], "candidate_count")
        finite_count = parse_integer(row["finite_count"], "finite_count")
        nonfinite_count = parse_integer(row["nonfinite_count"], "nonfinite_count")
        if finite_count + nonfinite_count != candidate_count:
            raise ValueError(
                f"finite/nonfinite counts do not sum to candidates for {unique_key}"
            )
        if nonfinite_count != 0:
            raise ValueError(
                f"non-finite candidate estimates invalidate inference for {unique_key}"
            )
        if parse_integer(row["boundary_pairs"], "boundary_pairs") < 0:
            raise ValueError(f"boundary_pairs is negative for {unique_key}")
        structure_key = (row["transform"], row["plan_control"], query, row["stage"])
        structural_groups[structure_key].append(row)
        all_grid_key = (
            row["transform"],
            row["plan_control"],
            row["rotation_control"],
            parse_integer(row["rotation_seed"], "rotation_seed"),
            query,
            row["stage"],
        )
        all_stage_rows[all_grid_key] = row
        if row["stage"] in COMMON_STAGES:
            common_stage_rows[all_grid_key] = row

    invariant_query_columns = (
        "candidate_count",
        "topk_used",
        "boundary_pairs",
        "stage_semantics",
        "logical_factor_bytes_per_candidate",
        "logical_fast_code_bytes_per_candidate",
        "logical_long_code_bytes_per_candidate",
        "logical_long_factor_bytes_per_candidate",
        "logical_total_requested_bytes_per_candidate",
        "logical_byte_model",
    )
    for key, rows in structural_groups.items():
        for column in invariant_query_columns:
            values = {row[column] for row in rows}
            if len(values) != 1:
                raise ValueError(
                    f"query structure differs across rotation controls for {key}: {column}={values}"
                )

    baseline_common_keys = {
        key[1:] for key in common_stage_rows if key[0] == baseline
    }
    for transform in config_grid:
        transform_keys = {key[1:] for key in common_stage_rows if key[0] == transform}
        if transform_keys != baseline_common_keys:
            raise ValueError(
                f"common-stage query grid differs from PCA for transform {transform}"
            )
        if transform == baseline:
            continue
        for suffix in baseline_common_keys:
            candidate = common_stage_rows[(transform, *suffix)]
            reference = common_stage_rows[(baseline, *suffix)]
            for column in ("candidate_count", "topk_used", "boundary_pairs"):
                if candidate[column] != reference[column]:
                    raise ValueError(
                        f"fixed-candidate contract differs for {transform}/{suffix}: {column}"
                    )
            plan = suffix[0]
            if plan in {"frozen-pca", "uniform"}:
                for column in invariant_query_columns[3:]:
                    if candidate[column] != reference[column]:
                        raise ValueError(
                            f"matched-plan stage bytes differ for {transform}/{suffix}: {column}"
                        )
        for plan in {"frozen-pca", "uniform"}.intersection(baseline_plans):
            reference_keys = {
                key[2:] for key in all_stage_rows if key[:2] == (baseline, plan)
            }
            candidate_keys = {
                key[2:] for key in all_stage_rows if key[:2] == (transform, plan)
            }
            if candidate_keys != reference_keys:
                raise ValueError(
                    f"matched-plan stage grid differs for {transform}/{plan}"
                )
            for suffix in reference_keys:
                candidate = all_stage_rows[(transform, plan, *suffix)]
                reference = all_stage_rows[(baseline, plan, *suffix)]
                for column in invariant_query_columns:
                    if candidate[column] != reference[column]:
                        raise ValueError(
                            f"matched-plan metadata differs for "
                            f"{transform}/{plan}/{suffix}: {column}"
                        )

    seen_segment: set[tuple[str, str, int, str]] = set()
    for row in segment_rows:
        config_key = (row["transform"], row["config_id"])
        config = configs.get(config_key)
        if config is None:
            raise ValueError(
                f"orphan segment row references unknown config {config_key[0]}/{config_key[1]}"
            )
        for column in ("plan_control", "rotation_control", "rotation_seed"):
            if row[column] != config[column]:
                raise ValueError(
                    f"segment/config mismatch for {config_key[0]}/{config_key[1]}: {column}"
                )
        rotation_group(row)
        total_count = parse_integer(row["total_count"], "total_count")
        finite_count = parse_integer(row["finite_count"], "finite_count")
        nonfinite_count = parse_integer(row["nonfinite_count"], "nonfinite_count")
        if finite_count + nonfinite_count != total_count:
            raise ValueError(
                f"finite/nonfinite segment counts do not sum to total for "
                f"{config_key[0]}/{config_key[1]}"
            )
        if nonfinite_count != 0:
            raise ValueError(
                f"non-finite segment estimates invalidate proxy evidence for "
                f"{config_key[0]}/{config_key[1]}"
            )
        if total_count != parse_integer(
            config["candidate_evaluations"], "candidate_evaluations"
        ):
            raise ValueError(
                f"segment count disagrees with candidate evaluations for "
                f"{config_key[0]}/{config_key[1]}"
            )
        unique_key = (
            row["transform"],
            row["config_id"],
            parse_integer(row["segment"], "segment"),
            row["distance_mode"],
        )
        if unique_key in seen_segment:
            raise ValueError(f"duplicate segment-mode row for {unique_key}")
        seen_segment.add(unique_key)


def one_text(rows: Sequence[Mapping[str, object]], column: str) -> str:
    values = {str(row[column]) for row in rows}
    if len(values) != 1:
        raise ValueError(f"column {column!r} is inconsistent: {sorted(values)}")
    return next(iter(values))


def strict_mean(values: Iterable[float]) -> float:
    materialized = list(values)
    if not materialized or not all(math.isfinite(value) for value in materialized):
        return math.nan
    return statistics.fmean(materialized)


def finite_mean(values: Iterable[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return statistics.fmean(finite) if finite else math.nan


def check_seed_rows(
    rows: Sequence[Mapping[str, str]], group: str, context: str
) -> tuple[int, str, bool]:
    if group == "off":
        if len(rows) != 1:
            raise ValueError(f"{context}: off control has {len(rows)} rows, expected 1")
        rotation_group(rows[0])
        return 1, "off", True
    seeds = [rotation_group(row)[1] for row in rows]
    if len(seeds) != len(set(seeds)):
        raise ValueError(f"{context}: duplicate seeded rotation rows")
    expected = set(EXPECTED_ROTATION_SEEDS)
    observed = {seed for seed in seeds if seed is not None}
    if observed != expected:
        missing = sorted(expected.difference(observed))
        extra = sorted(observed.difference(expected))
        raise ValueError(
            f"{context}: seeded rotation rows must cover 0..9 exactly; "
            f"missing={missing}, extra={extra}"
        )
    return len(seeds), "|".join(str(seed) for seed in EXPECTED_ROTATION_SEEDS), True


def aggregate_query_seeds(rows: Sequence[Mapping[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str, int], list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        group, _ = rotation_group(row)
        key = (
            row["transform"],
            row["plan_control"],
            group,
            row["stage"],
            parse_integer(row["query"], "query"),
        )
        grouped[key].append(row)

    result: list[dict[str, object]] = []
    for key, seed_rows in grouped.items():
        transform, plan, group, stage, query = key
        context = f"query aggregation {transform}/{plan}/{group}/{stage}/q{query}"
        seed_count, seed_values, complete = check_seed_rows(seed_rows, group, context)
        output: dict[str, object] = {
            "transform": transform,
            "plan_control": plan,
            "rotation_group": group,
            "stage": stage,
            "query": query,
            "rotation_config_count": seed_count,
            "rotation_seeds": seed_values,
            "seeds_complete": complete,
            "stage_semantics": one_text(seed_rows, "stage_semantics"),
            "logical_byte_model": one_text(seed_rows, "logical_byte_model"),
        }
        for column in QUERY_NUMERIC_COLUMNS:
            values = [parse_number(row[column], column) for row in seed_rows]
            output[column] = strict_mean(values)
            if column == "rmse":
                output["candidate_mse"] = strict_mean(value * value for value in values)
        if float(output["boundary_pairs"]) == 0:
            output["strict_boundary_inversion_rate"] = math.nan
        result.append(output)
    return result


def stage_order(stage: str) -> tuple[int, int, str]:
    if stage == "vars_conservative_lower_bound_all":
        return (0, 0, stage)
    if stage.startswith("fast_prefix_"):
        return (1, int(stage.rsplit("_", 1)[1]), stage)
    if stage == "fast_all":
        return (2, 0, stage)
    if stage.startswith("accurate_prefix_"):
        return (3, int(stage.rsplit("_", 1)[1]), stage)
    if stage == "full":
        return (4, 0, stage)
    return (5, 0, stage)


def make_stage_curves(query_rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[Mapping[str, object]]] = defaultdict(list)
    for row in query_rows:
        key = (
            str(row["transform"]),
            str(row["plan_control"]),
            str(row["rotation_group"]),
            str(row["stage"]),
        )
        grouped[key].append(row)

    result: list[dict[str, object]] = []
    for key, observations in grouped.items():
        transform, plan, group, stage = key
        queries = [int(row["query"]) for row in observations]
        if len(queries) != len(set(queries)):
            raise ValueError(f"duplicate query after seed aggregation for {key}")
        output: dict[str, object] = {
            "transform": transform,
            "plan_control": plan,
            "rotation_group": group,
            "stage": stage,
            "stage_semantics": one_text(observations, "stage_semantics"),
            "query_count": len(observations),
            "rotation_config_count": int(observations[0]["rotation_config_count"]),
            "rotation_seeds": str(observations[0]["rotation_seeds"]),
            "seeds_complete": all(bool(row["seeds_complete"]) for row in observations),
        }
        summary_columns = (
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
            "strict_boundary_inversion_rate",
            "logical_factor_bytes_per_candidate",
            "logical_fast_code_bytes_per_candidate",
            "logical_long_code_bytes_per_candidate",
            "logical_long_factor_bytes_per_candidate",
            "logical_total_requested_bytes_per_candidate",
        )
        for column in summary_columns:
            values = [float(row[column]) for row in observations]
            output[f"mean_query_{column}"] = finite_mean(values)
            output[f"finite_query_count_{column}"] = sum(
                math.isfinite(value) for value in values
            )
        output["mean_per_query_candidate_rmse"] = finite_mean(
            float(row["rmse"]) for row in observations
        )
        pooled_rows = [
            row
            for row in observations
            if math.isfinite(float(row["candidate_mse"]))
            and math.isfinite(float(row["candidate_count"]))
            and float(row["candidate_count"]) > 0
        ]
        pooled_count = math.fsum(float(row["candidate_count"]) for row in pooled_rows)
        output["pooled_candidate_rmse"] = (
            math.sqrt(
                math.fsum(
                    float(row["candidate_mse"]) * float(row["candidate_count"])
                    for row in pooled_rows
                )
                / pooled_count
            )
            if pooled_count > 0
            else math.nan
        )
        output["pooled_candidate_count"] = pooled_count
        result.append(output)
    return result


def aggregate_configs(rows: Sequence[Mapping[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        group, _ = rotation_group(row)
        grouped[(row["transform"], row["plan_control"], group)].append(row)

    result: list[dict[str, object]] = []
    for key, config_rows in grouped.items():
        transform, plan_control, group = key
        context = f"config aggregation {transform}/{plan_control}/{group}"
        seed_count, seed_values, complete = check_seed_rows(config_rows, group, context)
        output: dict[str, object] = {
            "transform": transform,
            "plan_control": plan_control,
            "rotation_group": group,
            "rotation_config_count": seed_count,
            "rotation_seeds": seed_values,
            "seeds_complete": complete,
            "plan": one_text(config_rows, "plan"),
            "exact_distance_scope": one_text(config_rows, "exact_distance_scope"),
            "seed_scope": one_text(config_rows, "seed_scope"),
            "structural_metadata_status": "exact_invariant_across_rotation_controls",
        }
        for column in CONFIG_STRUCTURAL_NUMERIC_COLUMNS:
            values = [parse_number(row[column], column) for row in config_rows]
            if len(set(values)) != 1:
                raise ValueError(
                    f"{context}: structural metadata {column} differs across rotations: {values}"
                )
            output[f"mean_{column}"] = values[0]
        for column in CONFIG_TIMING_COLUMNS:
            values = [parse_number(row[column], column) for row in config_rows]
            output[f"mean_{column}"] = strict_mean(values)
        byte_values = [
            parse_number(row["actual_serialized_index_bytes"], "actual_serialized_index_bytes")
            for row in config_rows
        ]
        output["min_actual_serialized_index_bytes"] = min(byte_values)
        output["max_actual_serialized_index_bytes"] = max(byte_values)
        result.append(output)
    return result


def aggregate_accurate_segments(
    rows: Sequence[Mapping[str, str]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, int], list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        if row["distance_mode"] != "accurate_full_code":
            continue
        group, _ = rotation_group(row)
        key = (
            row["transform"],
            row["plan_control"],
            group,
            parse_integer(row["segment"], "segment"),
        )
        grouped[key].append(row)
    if not grouped:
        raise ValueError("segment errors contain no accurate_full_code rows")

    result: list[dict[str, object]] = []
    for key, seed_rows in grouped.items():
        transform, plan, group, segment = key
        context = f"segment aggregation {transform}/{plan}/{group}/segment{segment}"
        seed_count, seed_values, complete = check_seed_rows(seed_rows, group, context)
        output: dict[str, object] = {
            "transform": transform,
            "plan_control": plan,
            "rotation_group": group,
            "segment": segment,
            "rotation_config_count": seed_count,
            "rotation_seeds": seed_values,
            "seeds_complete": complete,
        }
        for column in SEGMENT_NUMERIC_COLUMNS:
            values = [parse_number(row[column], column) for row in seed_rows]
            output[column] = strict_mean(values)
            if column == "rmse":
                output["mean_seed_accurate_distance_rmse"] = strict_mean(values)
                output["rmse"] = math.sqrt(
                    strict_mean(value * value for value in values)
                )
        output["implied_ip_rmse"] = math.sqrt(
            max(0.0, float(output["accurate_distance_implied_ip_sq_error_mean"]))
        )
        result.append(output)
    return result


def average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    begin = 0
    while begin < len(order):
        end = begin + 1
        while end < len(order) and values[order[end]] == values[order[begin]]:
            end += 1
        rank = (begin + 1 + end) / 2.0
        for position in range(begin, end):
            ranks[order[position]] = rank
        begin = end
    return ranks


def spearman(values_x: Sequence[float], values_y: Sequence[float]) -> float:
    pairs = [
        (x, y)
        for x, y in zip(values_x, values_y)
        if math.isfinite(x) and math.isfinite(y)
    ]
    # Two ranked points always produce |rho|=1 and carry no useful diagnostic
    # support.  Keep n<3 explicitly unavailable rather than displaying a
    # misleading perfect association.
    if len(pairs) < 3:
        return math.nan
    ranks_x = average_ranks([pair[0] for pair in pairs])
    ranks_y = average_ranks([pair[1] for pair in pairs])
    mean_x = statistics.fmean(ranks_x)
    mean_y = statistics.fmean(ranks_y)
    centered_x = [value - mean_x for value in ranks_x]
    centered_y = [value - mean_y for value in ranks_y]
    denominator = math.sqrt(
        math.fsum(value * value for value in centered_x)
        * math.fsum(value * value for value in centered_y)
    )
    if denominator == 0:
        return math.nan
    return math.fsum(x * y for x, y in zip(centered_x, centered_y)) / denominator


def make_proxy_summaries(
    segment_rows: Sequence[Mapping[str, object]],
    raw_segment_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, object]]] = defaultdict(list)
    for row in segment_rows:
        grouped[
            (
                str(row["transform"]),
                str(row["plan_control"]),
                str(row["rotation_group"]),
            )
        ].append(row)

    measured_columns = {
        "accurate_distance_mae": "mae",
        "accurate_distance_rmse": "rmse",
        "implied_ip_mae": "accurate_distance_implied_ip_abs_error_mean",
        "implied_ip_rmse": "implied_ip_rmse",
    }
    seedwise_groups: dict[
        tuple[str, str, str, int], list[Mapping[str, str]]
    ] = defaultdict(list)
    for row in raw_segment_rows:
        if row["distance_mode"] != "accurate_full_code":
            continue
        seedwise_groups[
            (
                row["transform"],
                row["plan_control"],
                row["rotation_control"],
                parse_integer(row["rotation_seed"], "rotation_seed"),
            )
        ].append(row)
    result: list[dict[str, object]] = []
    for key, segments in grouped.items():
        transform, plan, group = key
        segments = sorted(segments, key=lambda row: int(row["segment"]))
        proxy_columns = {
            "transform_proxy": "transform_planner_proxy",
            "pca_proxy": "pca_planner_proxy",
        }
        output: dict[str, object] = {
            "transform": transform,
            "plan_control": plan,
            "rotation_group": group,
            "segment_count": len(segments),
            "descriptive_low_n_only": True,
            "segment_support_status": (
                "insufficient_n" if len(segments) < 3
                else "low_support" if len(segments) < 5
                else "descriptive_only"
            ),
            "rotation_config_count": int(segments[0]["rotation_config_count"]),
            "rotation_seeds": str(segments[0]["rotation_seeds"]),
        }
        for proxy_label, proxy_column in proxy_columns.items():
            proxy_values = [float(row[proxy_column]) for row in segments]
            output[f"distinct_{proxy_label}_values"] = len(set(proxy_values))
            for measured_label, measured_column in measured_columns.items():
                measured = [float(row[measured_column]) for row in segments]
                output[f"spearman_{proxy_label}_vs_{measured_label}"] = spearman(
                    proxy_values, measured
                )
        seedwise_targets = {
            "accurate_distance_rmse": lambda row: parse_number(row["rmse"], "rmse"),
            "implied_ip_mae": lambda row: parse_number(
                row["accurate_distance_implied_ip_abs_error_mean"],
                "accurate_distance_implied_ip_abs_error_mean",
            ),
        }
        seed_rhos: dict[str, list[float]] = {
            label: [] for label in seedwise_targets
        }
        for (owner, owner_plan, control, seed), raw_segments in seedwise_groups.items():
            if owner != transform or owner_plan != plan:
                continue
            raw_group, _ = rotation_group(
                {"rotation_control": control, "rotation_seed": str(seed)}
            )
            if raw_group != group:
                continue
            raw_segments = sorted(
                raw_segments,
                key=lambda row: parse_integer(row["segment"], "segment"),
            )
            proxies = [
                parse_number(row["transform_planner_proxy"], "transform_planner_proxy")
                for row in raw_segments
            ]
            for label, getter in seedwise_targets.items():
                seed_rhos[label].append(
                    spearman(proxies, [getter(row) for row in raw_segments])
                )
        for label, rhos in seed_rhos.items():
            finite_rhos = sorted(value for value in rhos if math.isfinite(value))
            prefix = f"seedwise_spearman_transform_proxy_vs_{label}"
            output[f"{prefix}_finite_count"] = len(finite_rhos)
            output[f"{prefix}_min"] = finite_rhos[0] if finite_rhos else math.nan
            output[f"{prefix}_median"] = (
                statistics.median(finite_rhos) if finite_rhos else math.nan
            )
            output[f"{prefix}_max"] = finite_rhos[-1] if finite_rhos else math.nan
            output[f"{prefix}_positive_count"] = sum(value > 1e-12 for value in finite_rhos)
            output[f"{prefix}_negative_count"] = sum(value < -1e-12 for value in finite_rhos)
            output[f"{prefix}_zero_count"] = sum(abs(value) <= 1e-12 for value in finite_rhos)
        result.append(output)
    return result


def quantile_sorted(values: Sequence[float], probability: float) -> float:
    if not values:
        return math.nan
    position = probability * (len(values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def stable_seed(global_seed: int, components: Sequence[object]) -> int:
    payload = "\x1f".join([str(global_seed), *(str(value) for value in components)])
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "little")


def paired_bootstrap_mean_ci(
    differences: Sequence[float], replicates: int, seed: int
) -> tuple[float, float, float]:
    if not differences:
        return math.nan, math.nan, math.nan
    if not all(math.isfinite(value) for value in differences):
        raise ValueError("paired bootstrap received a non-finite difference")
    observed = statistics.fmean(differences)
    if len(differences) == 1:
        # A one-query interval is not inferential evidence.
        return observed, math.nan, math.nan
    count = len(differences)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, count, size=(replicates, count), dtype=np.int64)
    bootstrap_means = np.asarray(differences, dtype=np.float64)[indices].mean(axis=1)
    bootstrap_means.sort()
    sorted_means = bootstrap_means.tolist()
    return (
        observed,
        quantile_sorted(sorted_means, 0.025),
        quantile_sorted(sorted_means, 0.975),
    )


def pooled_rmse(
    mean_squared_errors: Sequence[float], candidate_counts: Sequence[float]
) -> float:
    if len(mean_squared_errors) != len(candidate_counts):
        raise ValueError("MSE/count lengths differ")
    denominator = math.fsum(candidate_counts)
    if denominator <= 0:
        return math.nan
    numerator = math.fsum(
        mse * count for mse, count in zip(mean_squared_errors, candidate_counts)
    )
    return math.sqrt(max(0.0, numerator / denominator))


def paired_bootstrap_pooled_rmse_ci(
    transform_mse: Sequence[float],
    transform_counts: Sequence[float],
    pca_mse: Sequence[float],
    pca_counts: Sequence[float],
    replicates: int,
    seed: int,
) -> tuple[float, float, float]:
    lengths = {
        len(transform_mse),
        len(transform_counts),
        len(pca_mse),
        len(pca_counts),
    }
    if len(lengths) != 1:
        raise ValueError("paired pooled-RMSE vectors have different lengths")
    count = len(transform_mse)
    if count == 0:
        return math.nan, math.nan, math.nan
    values = [*transform_mse, *transform_counts, *pca_mse, *pca_counts]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("paired pooled-RMSE bootstrap received non-finite input")
    transform_point = pooled_rmse(transform_mse, transform_counts)
    pca_point = pooled_rmse(pca_mse, pca_counts)
    observed = transform_point - pca_point
    if count == 1:
        return observed, math.nan, math.nan

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, count, size=(replicates, count), dtype=np.int64)
    transform_mse_array = np.asarray(transform_mse, dtype=np.float64)
    transform_count_array = np.asarray(transform_counts, dtype=np.float64)
    pca_mse_array = np.asarray(pca_mse, dtype=np.float64)
    pca_count_array = np.asarray(pca_counts, dtype=np.float64)
    transform_sample_mse = (
        (transform_mse_array[indices] * transform_count_array[indices]).sum(axis=1)
        / transform_count_array[indices].sum(axis=1)
    )
    pca_sample_mse = (
        (pca_mse_array[indices] * pca_count_array[indices]).sum(axis=1)
        / pca_count_array[indices].sum(axis=1)
    )
    bootstrap_differences = np.sqrt(np.maximum(0.0, transform_sample_mse)) - np.sqrt(
        np.maximum(0.0, pca_sample_mse)
    )
    bootstrap_differences.sort()
    sorted_differences = bootstrap_differences.tolist()
    return (
        observed,
        quantile_sorted(sorted_differences, 0.025),
        quantile_sorted(sorted_differences, 0.975),
    )


def ci_evidence(lower: float, upper: float, better: str) -> str:
    if not math.isfinite(lower) or not math.isfinite(upper):
        return "unavailable"
    if lower <= 0 <= upper:
        return "includes_zero"
    transform_better = upper < 0 if better == "lower" else lower > 0
    return "favors_transform" if transform_better else "favors_pca"


def descriptive_relation(
    metric_differences: Mapping[str, float],
    transform_logical_bytes: float,
    pca_logical_bytes: float,
    transform_serialized_bytes: float,
    pca_serialized_bytes: float,
    tolerance: float = 1e-12,
) -> str:
    values = [
        transform_logical_bytes,
        pca_logical_bytes,
        transform_serialized_bytes,
        pca_serialized_bytes,
        *metric_differences.values(),
    ]
    if not all(math.isfinite(value) for value in values):
        return "unavailable"

    def no_worse_for_transform(spec: MetricSpec) -> bool:
        difference = metric_differences[spec.output_name]
        return difference <= tolerance if spec.better == "lower" else difference >= -tolerance

    def strictly_better_for_transform(spec: MetricSpec) -> bool:
        difference = metric_differences[spec.output_name]
        return difference < -tolerance if spec.better == "lower" else difference > tolerance

    transform_no_worse = (
        transform_logical_bytes <= pca_logical_bytes + tolerance
        and transform_serialized_bytes <= pca_serialized_bytes + tolerance
        and all(no_worse_for_transform(spec) for spec in METRICS)
    )
    transform_strict = (
        transform_logical_bytes < pca_logical_bytes - tolerance
        or transform_serialized_bytes < pca_serialized_bytes - tolerance
        or any(strictly_better_for_transform(spec) for spec in METRICS)
    )
    pca_no_worse = (
        pca_logical_bytes <= transform_logical_bytes + tolerance
        and pca_serialized_bytes <= transform_serialized_bytes + tolerance
        and all(
            metric_differences[spec.output_name] >= -tolerance
            if spec.better == "lower"
            else metric_differences[spec.output_name] <= tolerance
            for spec in METRICS
        )
    )
    pca_strict = (
        pca_logical_bytes < transform_logical_bytes - tolerance
        or pca_serialized_bytes < transform_serialized_bytes - tolerance
        or any(
            metric_differences[spec.output_name] > tolerance
            if spec.better == "lower"
            else metric_differences[spec.output_name] < -tolerance
            for spec in METRICS
        )
    )
    if transform_no_worse and transform_strict:
        return "transform_partially_dominates_pca"
    if pca_no_worse and pca_strict:
        return "pca_partially_dominates_transform"
    if not transform_strict and not pca_strict:
        return "descriptively_equal"
    return "tradeoff"


def stage_family(stage: str) -> str:
    if stage == "vars_conservative_lower_bound_all":
        return "vars"
    if stage == "fast_all" or stage.startswith("fast_prefix_"):
        return "fast"
    if stage == "full" or stage.startswith("accurate_prefix_"):
        return "accurate"
    return "unknown"


def matched_stage_pairs(
    by_stage: Mapping[
        tuple[str, str, str, str], Mapping[int, Mapping[str, object]]
    ],
    transform: str,
    baseline: str,
    plan: str,
    group: str,
    warnings: list[str],
) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    transform_stages = {
        key[3]
        for key in by_stage
        if key[:3] == (transform, plan, group)
    }
    pca_stages = {
        key[3]
        for key in by_stage
        if key[:3] == (baseline, plan, group)
    }
    for stage in COMMON_STAGES:
        if stage in transform_stages and stage in pca_stages:
            pairs.append((stage, stage, "common_endpoint"))

    def stage_bytes(owner: str, stage: str) -> float:
        rows = by_stage[(owner, plan, group, stage)]
        values = {
            float(row["logical_total_requested_bytes_per_candidate"])
            for row in rows.values()
        }
        if len(values) != 1:
            raise ValueError(
                f"logical bytes vary by query for {owner}/{plan}/{group}/{stage}"
            )
        return next(iter(values))

    pca_by_match: dict[tuple[str, float], list[str]] = defaultdict(list)
    for stage in pca_stages.difference(COMMON_STAGES):
        pca_by_match[(stage_family(stage), stage_bytes(baseline, stage))].append(stage)
    for transform_stage in sorted(
        transform_stages.difference(COMMON_STAGES), key=stage_order
    ):
        match_key = (
            stage_family(transform_stage),
            stage_bytes(transform, transform_stage),
        )
        candidates = pca_by_match.get(match_key, [])
        exact_label_matches = [
            stage for stage in candidates if stage == transform_stage
        ]
        if exact_label_matches:
            candidates = exact_label_matches
        elif plan in {"frozen-pca", "uniform"}:
            candidates = []
        if len(candidates) == 1:
            pairs.append(
                (transform_stage, candidates[0], "matched_intermediate_family_and_bytes")
            )
        elif len(candidates) > 1:
            warnings.append(
                f"Ambiguous intermediate-prefix match for "
                f"{transform}/{plan}/{group}/{transform_stage}; retained only in stage curves."
            )
    return pairs


def make_paired_comparisons(
    query_rows: Sequence[Mapping[str, object]],
    raw_query_rows: Sequence[Mapping[str, str]],
    config_rows: Sequence[Mapping[str, object]],
    baseline: str,
    replicates: int,
    bootstrap_seed: int,
    warnings: list[str],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_stage: dict[
        tuple[str, str, str, str], dict[int, Mapping[str, object]]
    ] = defaultdict(dict)
    for row in query_rows:
        key = (
            str(row["transform"]),
            str(row["plan_control"]),
            str(row["rotation_group"]),
            str(row["stage"]),
        )
        query = int(row["query"])
        if query in by_stage[key]:
            raise ValueError(f"duplicate query observation for {key}/q{query}")
        by_stage[key][query] = row

    raw_by_stage: dict[
        tuple[str, str, str, int, str], dict[int, Mapping[str, str]]
    ] = defaultdict(dict)
    for row in raw_query_rows:
        seed = parse_integer(row["rotation_seed"], "rotation_seed")
        key = (
            row["transform"],
            row["plan_control"],
            row["rotation_control"],
            seed,
            row["stage"],
        )
        query = parse_integer(row["query"], "query")
        raw_by_stage[key][query] = row

    config_map = {
        (
            str(row["transform"]),
            str(row["plan_control"]),
            str(row["rotation_group"]),
        ): row
        for row in config_rows
    }
    transforms = sorted({key[0] for key in by_stage})
    result: list[dict[str, object]] = []
    per_seed_result: list[dict[str, object]] = []
    for transform in transforms:
        if transform == baseline:
            continue
        controls = sorted(
            {(key[1], key[2]) for key in by_stage if key[0] == transform}
        )
        for plan, group in controls:
            for transform_stage, pca_stage, stage_match_type in matched_stage_pairs(
                by_stage, transform, baseline, plan, group, warnings
            ):
                stage = (
                    transform_stage
                    if transform_stage == pca_stage
                    else f"{transform_stage}__vs__{pca_stage}"
                )
                transform_key = (transform, plan, group, transform_stage)
                pca_key = (baseline, plan, group, pca_stage)
                transform_queries = by_stage[transform_key]
                pca_queries = by_stage[pca_key]
                transform_ids = set(transform_queries)
                pca_ids = set(pca_queries)
                if transform_ids != pca_ids:
                    raise ValueError(
                        f"query mismatch for {transform}/{plan}/{group}/{stage}: "
                        f"transform={sorted(transform_ids)}, PCA={sorted(pca_ids)}"
                    )
                common_ids = sorted(transform_ids)
                if not common_ids:
                    warnings.append(
                        f"No paired queries for {transform}/{plan}/{group}/{stage}; skipped."
                    )
                    continue

                transform_config = config_map.get((transform, plan, group))
                pca_config = config_map.get((baseline, plan, group))
                if transform_config is None or pca_config is None:
                    warnings.append(
                        f"Missing config summary for {transform}/{plan}/{group}; skipped."
                    )
                    continue
                for metadata in (
                    "mean_N",
                    "mean_D",
                    "mean_K",
                    "mean_queries",
                    "mean_fixed_probes_per_query",
                    "mean_topk_requested",
                    "mean_nominal_B",
                    "mean_vars_bound_m",
                ):
                    left = float(transform_config[metadata])
                    right = float(pca_config[metadata])
                    if left != right:
                        raise ValueError(
                            f"comparison contract mismatch for {transform}/{plan}/{group}: "
                            f"{metadata} is {left} versus PCA {right}"
                        )
                transform_semantics = str(
                    transform_queries[common_ids[0]]["stage_semantics"]
                )
                pca_semantics = str(pca_queries[common_ids[0]]["stage_semantics"])
                if transform_semantics != pca_semantics:
                    raise ValueError(
                        f"stage semantics mismatch for {transform}/{plan}/{group}/{stage}"
                    )
                for query in common_ids:
                    for metadata in ("candidate_count", "topk_used", "boundary_pairs"):
                        left = float(transform_queries[query][metadata])
                        right = float(pca_queries[query][metadata])
                        if left != right:
                            raise ValueError(
                                f"fixed-candidate contract mismatch for "
                                f"{transform}/{plan}/{group}/{stage}/q{query}: "
                                f"{metadata} is {left} versus PCA {right}"
                            )
                transform_logical = finite_mean(
                    float(transform_queries[q]["logical_total_requested_bytes_per_candidate"])
                    for q in common_ids
                )
                pca_logical = finite_mean(
                    float(pca_queries[q]["logical_total_requested_bytes_per_candidate"])
                    for q in common_ids
                )
                transform_serialized = float(
                    transform_config["mean_actual_serialized_index_bytes"]
                )
                pca_serialized = float(pca_config["mean_actual_serialized_index_bytes"])
                output: dict[str, object] = {
                    "transform": transform,
                    "baseline": baseline,
                    "plan_control": plan,
                    "rotation_group": group,
                    "stage": stage,
                    "transform_stage": transform_stage,
                    "pca_stage": pca_stage,
                    "stage_match_type": stage_match_type,
                    "stage_semantics": transform_semantics,
                    "transform_query_count": len(transform_ids),
                    "pca_query_count": len(pca_ids),
                    "paired_query_count": len(common_ids),
                    "bootstrap_replicates": replicates,
                    "bootstrap_seed": bootstrap_seed,
                    "transform_logical_bytes_per_candidate": transform_logical,
                    "pca_logical_bytes_per_candidate": pca_logical,
                    "transform_actual_serialized_index_bytes": transform_serialized,
                    "pca_actual_serialized_index_bytes": pca_serialized,
                    "matched_plan": transform_config["plan"] == pca_config["plan"],
                    "matched_logical_bytes": transform_logical == pca_logical,
                    "matched_serialized_bytes": (
                        transform_serialized == pca_serialized
                    ),
                    "matched_budget": (
                        transform_config["plan"] == pca_config["plan"]
                        and transform_logical == pca_logical
                        and transform_serialized == pca_serialized
                    ),
                    "dominance_scope": (
                        "partial_diagnostic_index_serialization_plus_logical_requested_bytes"
                    ),
                }
                metric_differences: dict[str, float] = {}
                evidences: list[str] = []
                for spec in METRICS:
                    comparison_seed = stable_seed(
                        bootstrap_seed, (transform, plan, group, stage, spec.output_name)
                    )
                    paired_values = [
                        (
                            float(transform_queries[q][spec.input_name]),
                            float(pca_queries[q][spec.input_name]),
                            float(transform_queries[q]["candidate_count"]),
                            float(pca_queries[q]["candidate_count"]),
                        )
                        for q in common_ids
                    ]
                    finite_pairs = [
                        pair
                        for pair in paired_values
                        if all(math.isfinite(value) for value in pair)
                        and pair[2] > 0
                        and pair[3] > 0
                    ]
                    if spec.aggregation == "pooled_rmse":
                        transform_values = [pair[0] for pair in finite_pairs]
                        pca_values = [pair[1] for pair in finite_pairs]
                        transform_counts = [pair[2] for pair in finite_pairs]
                        pca_counts = [pair[3] for pair in finite_pairs]
                        mean_difference, ci_low, ci_high = (
                            paired_bootstrap_pooled_rmse_ci(
                                transform_values,
                                transform_counts,
                                pca_values,
                                pca_counts,
                                replicates,
                                comparison_seed,
                            )
                        )
                        transform_mean = pooled_rmse(transform_values, transform_counts)
                        pca_mean = pooled_rmse(pca_values, pca_counts)
                    else:
                        differences = [pair[0] - pair[1] for pair in finite_pairs]
                        mean_difference, ci_low, ci_high = paired_bootstrap_mean_ci(
                            differences, replicates, comparison_seed
                        )
                        transform_mean = finite_mean(pair[0] for pair in finite_pairs)
                        pca_mean = finite_mean(pair[1] for pair in finite_pairs)
                    evidence = ci_evidence(ci_low, ci_high, spec.better)
                    evidences.append(evidence)
                    metric_differences[spec.output_name] = mean_difference
                    prefix = spec.output_name
                    output[f"{prefix}_better_direction"] = spec.better
                    output[f"{prefix}_paired_query_count"] = len(finite_pairs)
                    output[f"{prefix}_transform_mean"] = transform_mean
                    output[f"{prefix}_pca_mean"] = pca_mean
                    output[f"{prefix}_transform_minus_pca"] = mean_difference
                    output[f"{prefix}_ci95_low"] = ci_low
                    output[f"{prefix}_ci95_high"] = ci_high
                    output[f"{prefix}_ci_excludes_zero"] = evidence in {
                        "favors_transform",
                        "favors_pca",
                    }
                    output[f"{prefix}_ci_evidence"] = evidence

                    seed_effects: list[float] = []
                    seed_values = EXPECTED_ROTATION_SEEDS if group == "seed_average" else (-1,)
                    for rotation_seed in seed_values:
                        control = "off" if rotation_seed == -1 else f"seed{rotation_seed}"
                        transform_raw = raw_by_stage[
                            (transform, plan, control, rotation_seed, transform_stage)
                        ]
                        pca_raw = raw_by_stage[
                            (baseline, plan, control, rotation_seed, pca_stage)
                        ]
                        if set(transform_raw) != set(pca_raw):
                            raise ValueError(
                                f"per-seed query mismatch for "
                                f"{transform}/{plan}/{control}/{stage}"
                            )
                        raw_ids = sorted(transform_raw)
                        if spec.input_name == "strict_boundary_inversion_rate":
                            raw_ids = [
                                query
                                for query in raw_ids
                                if parse_integer(
                                    transform_raw[query]["boundary_pairs"],
                                    "boundary_pairs",
                                )
                                > 0
                                and parse_integer(
                                    pca_raw[query]["boundary_pairs"],
                                    "boundary_pairs",
                                )
                                > 0
                            ]
                        if spec.aggregation == "pooled_rmse":
                            transform_seed_mean = pooled_rmse(
                                [float(transform_raw[q]["rmse"]) ** 2 for q in raw_ids],
                                [float(transform_raw[q]["candidate_count"]) for q in raw_ids],
                            )
                            pca_seed_mean = pooled_rmse(
                                [float(pca_raw[q]["rmse"]) ** 2 for q in raw_ids],
                                [float(pca_raw[q]["candidate_count"]) for q in raw_ids],
                            )
                        elif raw_ids:
                            transform_seed_mean = statistics.fmean(
                                float(transform_raw[q][spec.input_name]) for q in raw_ids
                            )
                            pca_seed_mean = statistics.fmean(
                                float(pca_raw[q][spec.input_name]) for q in raw_ids
                            )
                        else:
                            transform_seed_mean = math.nan
                            pca_seed_mean = math.nan
                        seed_effect = transform_seed_mean - pca_seed_mean
                        if math.isfinite(seed_effect):
                            seed_effects.append(seed_effect)
                        if not math.isfinite(seed_effect):
                            seed_direction = "unavailable"
                        elif abs(seed_effect) <= 1e-12:
                            seed_direction = "tied"
                        elif (
                            seed_effect < 0
                            if spec.better == "lower"
                            else seed_effect > 0
                        ):
                            seed_direction = "favors_transform"
                        else:
                            seed_direction = "favors_pca"
                        per_seed_result.append(
                            {
                                "transform": transform,
                                "baseline": baseline,
                                "plan_control": plan,
                                "rotation_seed": rotation_seed,
                                "stage": stage,
                                "transform_stage": transform_stage,
                                "pca_stage": pca_stage,
                                "stage_match_type": stage_match_type,
                                "metric": spec.output_name,
                                "better_direction": spec.better,
                                "query_count": len(raw_ids),
                                "transform_mean": transform_seed_mean,
                                "pca_mean": pca_seed_mean,
                                "transform_minus_pca": seed_effect,
                                "descriptive_direction": seed_direction,
                                "matched_budget": output["matched_budget"],
                            }
                        )
                    prefix = spec.output_name
                    output[f"{prefix}_seed_effect_min"] = (
                        min(seed_effects) if seed_effects else math.nan
                    )
                    output[f"{prefix}_seed_effect_median"] = (
                        statistics.median(seed_effects) if seed_effects else math.nan
                    )
                    output[f"{prefix}_seed_effect_max"] = (
                        max(seed_effects) if seed_effects else math.nan
                    )
                    output[f"{prefix}_seeds_favoring_transform"] = sum(
                        (effect < -1e-12 if spec.better == "lower" else effect > 1e-12)
                        for effect in seed_effects
                    )
                    output[f"{prefix}_seeds_favoring_pca"] = sum(
                        (effect > 1e-12 if spec.better == "lower" else effect < -1e-12)
                        for effect in seed_effects
                    )
                    output[f"{prefix}_seeds_tied"] = sum(
                        abs(effect) <= 1e-12 for effect in seed_effects
                    )
                    output[f"{prefix}_seeds_unavailable"] = len(seed_values) - len(seed_effects)

                output["descriptive_mean_rate_quality_relation"] = (
                    "not_applicable_conservative_bound"
                    if transform_stage == "vars_conservative_lower_bound_all"
                    else descriptive_relation(
                        metric_differences,
                        transform_logical,
                        pca_logical,
                        transform_serialized,
                        pca_serialized,
                    )
                )
                output["ci_metrics_favoring_transform"] = sum(
                    evidence == "favors_transform" for evidence in evidences
                )
                output["ci_metrics_favoring_pca"] = sum(
                    evidence == "favors_pca" for evidence in evidences
                )
                output["ci_metrics_including_zero"] = sum(
                    evidence == "includes_zero" for evidence in evidences
                )
                output["all_metric_cis_favor_transform"] = all(
                    evidence == "favors_transform" for evidence in evidences
                )
                output["all_metric_cis_favor_pca"] = all(
                    evidence == "favors_pca" for evidence in evidences
                )
                result.append(output)
    return result, per_seed_result


def sortable_plan(plan: str) -> tuple[int, str]:
    order = {"native": 0, "frozen-pca": 1, "uniform": 2}
    return order.get(plan, 9), plan


def sort_rows(
    rows: Sequence[dict[str, object]], transform_order: Mapping[str, int]
) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            transform_order.get(str(row.get("transform", "")), 999),
            sortable_plan(str(row.get("plan_control", ""))),
            0 if row.get("rotation_group") == "seed_average" else 1,
            stage_order(str(row.get("stage", ""))),
            int(float(row.get("segment", 0))),
        ),
    )


def csv_value(value: object) -> object:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return format(value, ".12g")
    return value


def write_rows(path: Path, rows: Sequence[Mapping[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field, "")) for field in fields})


def markdown_number(value: object, digits: int = 4) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "NA"
    if number == 0:
        return "0"
    if abs(number) >= 10000 or abs(number) < 0.001:
        return f"{number:.3e}"
    return f"{number:.{digits}f}"


def markdown_ci(row: Mapping[str, object], metric: str) -> str:
    difference = markdown_number(row[f"{metric}_transform_minus_pca"])
    lower = markdown_number(row[f"{metric}_ci95_low"])
    upper = markdown_number(row[f"{metric}_ci95_high"])
    evidence = str(row[f"{metric}_ci_evidence"])
    return f"{difference} [{lower}, {upper}] ({evidence})"


def markdown_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def make_markdown(
    path: Path,
    bundles: Sequence[InputBundle],
    baseline: str,
    stage_path: Path,
    paired_path: Path,
    per_seed_path: Path,
    config_path: Path,
    proxy_path: Path,
    config_rows: Sequence[Mapping[str, object]],
    paired_rows: Sequence[Mapping[str, object]],
    proxy_rows: Sequence[Mapping[str, object]],
    replicates: int,
    bootstrap_seed: int,
    warnings: Sequence[str],
) -> None:
    lines = [
        "# SAQ Phase-1 transform evidence summary",
        "",
        "This report is descriptive evidence for reviewing the PCA/SAQ mismatch hypothesis. "
        "It does not make an automatic novelty or contribution claim.",
        "",
        "## Inference contract",
        "",
        f"- Baseline: `{baseline}`.",
        "- Internal-rotation seeds `0..9` are averaged within each query before inference; "
        "the `off` control is reported separately.",
        f"- The paired 95% percentile bootstrap resamples queries ({replicates} replicates, "
        f"global seed {bootstrap_seed}). SHA-256-derived comparison sub-seeds and NumPy "
        f"{np.__version__} `default_rng` make intervals stable to unrelated output additions. "
        "Candidates and "
        "seeds are not treated as independent units.",
        f"- Every reported difference is `transform - {baseline}`. Lower is better for RMSE, "
        "MAE, boundary inversion, and exact-best rank; higher is better for top-k agreement.",
        "- Two RMSE estimands are kept separate: `mean_per_query_candidate_rmse` gives queries "
        "equal weight after averaging rotation repeats within query; `pooled_candidate_rmse` "
        "reconstructs SSE as `candidate_count * RMSE^2` and recomputes each arm's square root "
        "inside every query bootstrap replicate.",
        "- `vars_conservative_lower_bound_all` is a conservative bound diagnostic, not an "
        "ordinary unbiased distance estimator.",
        "- Dominance is only a partial diagnostic comparison of mean metrics, logical requested "
        "bytes, and serialized index bytes. Serialized bytes omit the outer transform artifact; "
        "logical bytes omit query transform, centroid, LUT, and other complete-work costs. It is "
        "not a statistical, complete-Pareto, or novelty conclusion.",
        "",
        "Inputs: " + ", ".join(
            f"`{bundle.label}` (`{bundle.prefix}`)" for bundle in bundles
        ),
        "",
        "Machine-readable outputs:",
        "",
        f"- `{stage_path.name}`: all individual prefix stages against logical bytes.",
        f"- `{paired_path.name}`: common endpoints plus strictly byte-matched intermediate "
        "prefixes, with paired differences and confidence intervals.",
        f"- `{per_seed_path.name}`: descriptive seed-by-seed effects for stability review.",
        f"- `{config_path.name}`: actual serialized bytes, plans, and construction metadata.",
        f"- `{proxy_path.name}`: low-n segment proxy/error Spearman agreement.",
        "",
        "## Actual index bytes and plans",
        "",
        "| Transform | Plan control | Rotation | Segments | Serialized bytes | Bytes/vector | Plan |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in config_rows:
        lines.append(
            "| "
            + " | ".join(
                markdown_escape(value)
                for value in (
                    row["transform"],
                    row["plan_control"],
                    row["rotation_group"],
                    markdown_number(row["mean_segments"], 0),
                    markdown_number(row["mean_actual_serialized_index_bytes"], 0),
                    markdown_number(row["mean_actual_serialized_index_bytes_per_vector"]),
                    row["plan"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Paired matched-stage evidence versus PCA",
            "",
            "CI cells show mean difference and `[95% CI]`; the final tag states whether the "
            "interval favors the transform, favors PCA, or includes zero.",
            "",
            "| Transform | Plan | Rotation | Stage | Matched budget | Δmean-query RMSE | Δpooled RMSE | ΔTop-k agreement | ΔBoundary inversion | Mean relation |",
            "|---|---|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in paired_rows:
        lines.append(
            "| "
            + " | ".join(
                markdown_escape(value)
                for value in (
                    row["transform"],
                    row["plan_control"],
                    row["rotation_group"],
                    row["stage"],
                    row["matched_budget"],
                    markdown_ci(row, "mean_per_query_candidate_rmse"),
                    markdown_ci(row, "pooled_candidate_rmse"),
                    markdown_ci(row, "topk_agreement"),
                    markdown_ci(row, "boundary_inversion_rate"),
                    row["descriptive_mean_rate_quality_relation"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Planner proxy versus measured segment error",
            "",
            "Spearman values below are descriptive only. Segment counts are the effective "
            "sample sizes and are generally too small for inferential claims; ties or a "
            "single uniform segment produce `NA`. The CSV additionally reports seedwise "
            "rho min/median/max and sign counts for distance RMSE and implied-IP MAE.",
            "",
            "| Transform | Plan | Rotation | n segments | Support | ρ(transform proxy, distance RMSE) | ρ(transform proxy, IP RMSE) |",
            "|---|---|---|---:|---|---:|---:|",
        ]
    )
    for row in proxy_rows:
        lines.append(
            "| "
            + " | ".join(
                markdown_escape(value)
                for value in (
                    row["transform"],
                    row["plan_control"],
                    row["rotation_group"],
                    row["segment_count"],
                    row["segment_support_status"],
                    markdown_number(
                        row["spearman_transform_proxy_vs_accurate_distance_rmse"]
                    ),
                    markdown_number(row["spearman_transform_proxy_vs_implied_ip_rmse"]),
                )
            )
            + " |"
        )

    lines.extend(["", "## Data-quality notes", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- Complete matched query sets were available for every reported comparison.")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


STAGE_FIELDS = (
    "transform",
    "plan_control",
    "rotation_group",
    "stage",
    "stage_semantics",
    "query_count",
    "rotation_config_count",
    "rotation_seeds",
    "seeds_complete",
    "mean_per_query_candidate_rmse",
    "pooled_candidate_rmse",
    "pooled_candidate_count",
    *(
        field
        for column in (
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
            "strict_boundary_inversion_rate",
            "logical_factor_bytes_per_candidate",
            "logical_fast_code_bytes_per_candidate",
            "logical_long_code_bytes_per_candidate",
            "logical_long_factor_bytes_per_candidate",
            "logical_total_requested_bytes_per_candidate",
        )
        for field in (f"mean_query_{column}", f"finite_query_count_{column}")
    ),
)

CONFIG_FIELDS = (
    "transform",
    "plan_control",
    "rotation_group",
    "rotation_config_count",
    "rotation_seeds",
    "seeds_complete",
    "seed_scope",
    "structural_metadata_status",
    "mean_N",
    "mean_D",
    "mean_K",
    "mean_queries",
    "mean_fixed_probes_per_query",
    "mean_topk_requested",
    "mean_nominal_B",
    "mean_vars_bound_m",
    "mean_segments",
    "plan",
    "mean_nominal_code_bits_per_vector",
    "mean_transform_planner_proxy_total",
    "mean_pca_planner_proxy_total",
    "mean_actual_serialized_index_bytes",
    "min_actual_serialized_index_bytes",
    "max_actual_serialized_index_bytes",
    "mean_actual_serialized_index_bytes_per_vector",
    "mean_build_time_s",
    "mean_serialization_time_s",
    "mean_measurement_time_s",
    "mean_candidate_evaluations",
    "exact_distance_scope",
)

PROXY_FIELDS = (
    "transform",
    "plan_control",
    "rotation_group",
    "segment_count",
    "descriptive_low_n_only",
    "segment_support_status",
    "rotation_config_count",
    "rotation_seeds",
    "distinct_transform_proxy_values",
    "distinct_pca_proxy_values",
    "spearman_transform_proxy_vs_accurate_distance_mae",
    "spearman_transform_proxy_vs_accurate_distance_rmse",
    "spearman_transform_proxy_vs_implied_ip_mae",
    "spearman_transform_proxy_vs_implied_ip_rmse",
    "spearman_pca_proxy_vs_accurate_distance_mae",
    "spearman_pca_proxy_vs_accurate_distance_rmse",
    "spearman_pca_proxy_vs_implied_ip_mae",
    "spearman_pca_proxy_vs_implied_ip_rmse",
    *(
        field
        for target in ("accurate_distance_rmse", "implied_ip_mae")
        for field in (
            f"seedwise_spearman_transform_proxy_vs_{target}_finite_count",
            f"seedwise_spearman_transform_proxy_vs_{target}_min",
            f"seedwise_spearman_transform_proxy_vs_{target}_median",
            f"seedwise_spearman_transform_proxy_vs_{target}_max",
            f"seedwise_spearman_transform_proxy_vs_{target}_positive_count",
            f"seedwise_spearman_transform_proxy_vs_{target}_negative_count",
            f"seedwise_spearman_transform_proxy_vs_{target}_zero_count",
        )
    ),
)

PAIRED_BASE_FIELDS = (
    "transform",
    "baseline",
    "plan_control",
    "rotation_group",
    "stage",
    "transform_stage",
    "pca_stage",
    "stage_match_type",
    "stage_semantics",
    "transform_query_count",
    "pca_query_count",
    "paired_query_count",
    "bootstrap_replicates",
    "bootstrap_seed",
    "transform_logical_bytes_per_candidate",
    "pca_logical_bytes_per_candidate",
    "transform_actual_serialized_index_bytes",
    "pca_actual_serialized_index_bytes",
    "matched_plan",
    "matched_logical_bytes",
    "matched_serialized_bytes",
    "matched_budget",
    "dominance_scope",
)
PAIRED_METRIC_FIELDS = tuple(
    field
    for spec in METRICS
    for field in (
        f"{spec.output_name}_better_direction",
        f"{spec.output_name}_paired_query_count",
        f"{spec.output_name}_transform_mean",
        f"{spec.output_name}_pca_mean",
        f"{spec.output_name}_transform_minus_pca",
        f"{spec.output_name}_ci95_low",
        f"{spec.output_name}_ci95_high",
        f"{spec.output_name}_ci_excludes_zero",
        f"{spec.output_name}_ci_evidence",
        f"{spec.output_name}_seed_effect_min",
        f"{spec.output_name}_seed_effect_median",
        f"{spec.output_name}_seed_effect_max",
        f"{spec.output_name}_seeds_favoring_transform",
        f"{spec.output_name}_seeds_favoring_pca",
        f"{spec.output_name}_seeds_tied",
        f"{spec.output_name}_seeds_unavailable",
    )
)
PAIRED_FIELDS = (
    *PAIRED_BASE_FIELDS,
    *PAIRED_METRIC_FIELDS,
    "descriptive_mean_rate_quality_relation",
    "ci_metrics_favoring_transform",
    "ci_metrics_favoring_pca",
    "ci_metrics_including_zero",
    "all_metric_cis_favor_transform",
    "all_metric_cis_favor_pca",
)

PER_SEED_FIELDS = (
    "transform",
    "baseline",
    "plan_control",
    "rotation_seed",
    "stage",
    "transform_stage",
    "pca_stage",
    "stage_match_type",
    "metric",
    "better_direction",
    "query_count",
    "transform_mean",
    "pca_mean",
    "transform_minus_pca",
    "descriptive_direction",
    "matched_budget",
)


def summarize(
    input_specs: Sequence[str],
    output_prefix: Path,
    baseline: str = "current_pca",
    bootstrap_replicates: int = DEFAULT_BOOTSTRAP_REPLICATES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, Path]:
    if bootstrap_replicates <= 0:
        raise ValueError("bootstrap_replicates must be positive")
    bundles = [load_bundle(specification) for specification in input_specs]
    labels = [bundle.label for bundle in bundles]
    if len(labels) != len(set(labels)):
        raise ValueError(f"input labels must be unique, got {labels}")
    if baseline not in labels:
        raise ValueError(
            f"baseline {baseline!r} is absent; use {baseline}=PREFIX or --baseline LABEL"
        )
    warnings: list[str] = []
    if len(bundles) != 4:
        warnings.append(
            f"Expected four Phase-1 transform prefixes, received {len(bundles)}."
        )

    raw_query_rows = [row for bundle in bundles for row in bundle.query_rows]
    raw_config_rows = [row for bundle in bundles for row in bundle.config_rows]
    raw_segment_rows = [row for bundle in bundles for row in bundle.segment_rows]
    validate_raw_relations(
        raw_query_rows, raw_segment_rows, raw_config_rows, baseline
    )
    query_rows = aggregate_query_seeds(raw_query_rows)
    config_rows = aggregate_configs(raw_config_rows)
    segment_rows = aggregate_accurate_segments(raw_segment_rows)
    stage_rows = make_stage_curves(query_rows)
    proxy_rows = make_proxy_summaries(segment_rows, raw_segment_rows)
    paired_rows, per_seed_rows = make_paired_comparisons(
        query_rows,
        raw_query_rows,
        config_rows,
        baseline,
        bootstrap_replicates,
        bootstrap_seed,
        warnings,
    )

    transform_order = {label: index for index, label in enumerate(labels)}
    stage_rows = sort_rows(stage_rows, transform_order)
    config_rows = sort_rows(config_rows, transform_order)
    proxy_rows = sort_rows(proxy_rows, transform_order)
    paired_rows = sort_rows(paired_rows, transform_order)
    per_seed_rows = sort_rows(per_seed_rows, transform_order)

    paths = {
        "stage_curves": Path(f"{output_prefix}.stage_curves.csv"),
        "paired_vs_pca": Path(f"{output_prefix}.paired_vs_pca.csv"),
        "per_seed_effects": Path(f"{output_prefix}.per_seed_effects.csv"),
        "config_summary": Path(f"{output_prefix}.config_summary.csv"),
        "segment_proxy": Path(f"{output_prefix}.segment_proxy.csv"),
        "markdown": Path(f"{output_prefix}.md"),
    }
    write_rows(paths["stage_curves"], stage_rows, STAGE_FIELDS)
    write_rows(paths["paired_vs_pca"], paired_rows, PAIRED_FIELDS)
    write_rows(paths["per_seed_effects"], per_seed_rows, PER_SEED_FIELDS)
    write_rows(paths["config_summary"], config_rows, CONFIG_FIELDS)
    write_rows(paths["segment_proxy"], proxy_rows, PROXY_FIELDS)
    make_markdown(
        paths["markdown"],
        bundles,
        baseline,
        paths["stage_curves"],
        paths["paired_vs_pca"],
        paths["per_seed_effects"],
        paths["config_summary"],
        paths["segment_proxy"],
        config_rows,
        paired_rows,
        proxy_rows,
        bootstrap_replicates,
        bootstrap_seed,
        warnings,
    )
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        metavar="[LABEL=]PREFIX",
        help="Transform output prefix; four labeled prefixes are expected.",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        required=True,
        help="Prefix for compact summary CSVs and Markdown.",
    )
    parser.add_argument(
        "--baseline",
        default="current_pca",
        help="Canonical input label used as the paired baseline (default: current_pca).",
    )
    parser.add_argument(
        "--bootstrap-replicates",
        type=int,
        default=DEFAULT_BOOTSTRAP_REPLICATES,
        help=f"Paired query bootstrap replicates (default: {DEFAULT_BOOTSTRAP_REPLICATES}).",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=DEFAULT_BOOTSTRAP_SEED,
        help=f"Fixed bootstrap seed (default: {DEFAULT_BOOTSTRAP_SEED}).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = summarize(
            args.inputs,
            args.output_prefix,
            baseline=args.baseline,
            bootstrap_replicates=args.bootstrap_replicates,
            bootstrap_seed=args.bootstrap_seed,
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
