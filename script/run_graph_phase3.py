#!/usr/bin/env python3
"""Run and aggregate the predeclared Phase 3 local graph replay matrix.

Roots are nested observations.  This module first aggregates roots within each
query, averages fixed rotation replications within a query, and only then forms
confidence intervals across queries.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Mapping, Sequence


CANONICAL_SETTINGS = ((1024, 50), (4096, 100))
CANONICAL_SEEDS = tuple(range(10))
CANONICAL_DEGREE = 32
CANONICAL_ROOTS = 8
TOP_L_VALUES = (1, 2, 4, 8, 16, 32)
BASELINE_ESTIMATOR = "symqg_fht_fastscan"
REQUIRED_EVENT_COLUMNS = {
    "query_id",
    "root_id",
    "exact_best_id",
    "exact_best_distance",
    "exact_gap",
    "degree",
    "distinct_clusters",
    "estimator",
    "rank_exact_best",
    "est_best_id",
    "est_best_estimate",
    "est_best_exact_distance",
    "exact_regret",
    "top1_disagree",
}


@dataclass(frozen=True)
class Setting:
    subset: int
    max_queries: int


@dataclass(frozen=True)
class RunSpec:
    setting: Setting
    seed: int
    prefix: Path


@dataclass(frozen=True)
class Event:
    subset: int
    max_queries: int
    seed: int
    query_id: int
    root_id: int
    exact_best_id: int
    exact_best_distance: float
    exact_gap: float
    degree: int
    distinct_clusters: int
    estimator: str
    rank_exact_best: float
    est_best_id: int
    est_best_estimate: float
    est_best_exact_distance: float
    exact_regret: float
    top1_disagree: float


def parse_settings(values: Sequence[str] | None) -> tuple[Setting, ...]:
    if not values:
        return tuple(Setting(*item) for item in CANONICAL_SETTINGS)
    settings: list[Setting] = []
    for value in values:
        for token in value.split(","):
            fields = token.strip().split(":")
            if len(fields) != 2:
                raise ValueError(f"invalid setting {token!r}; expected SUBSET:QUERIES")
            subset, queries = (int(field) for field in fields)
            if subset <= 1 or queries <= 0:
                raise ValueError(f"setting values must be positive: {token!r}")
            settings.append(Setting(subset, queries))
    if len({setting.subset for setting in settings}) != len(settings):
        raise ValueError("each Phase 3 setting must use a distinct subset size")
    return tuple(settings)


def parse_seeds(value: str) -> tuple[int, ...]:
    seeds: list[int] = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start, end = int(start_text), int(end_text)
            if start < 0 or end < start:
                raise ValueError(f"invalid seed range: {token!r}")
            seeds.extend(range(start, end + 1))
        else:
            seed = int(token)
            if seed < 0:
                raise ValueError("rotation seeds must be non-negative")
            seeds.append(seed)
    if not seeds:
        raise ValueError("at least one rotation seed is required")
    if len(set(seeds)) != len(seeds):
        raise ValueError("duplicate rotation seeds are not allowed")
    return tuple(seeds)


def is_canonical(settings: Sequence[Setting], seeds: Sequence[int], degree: int, roots: int) -> bool:
    return (
        tuple((setting.subset, setting.max_queries) for setting in settings)
        == CANONICAL_SETTINGS
        and tuple(seeds) == CANONICAL_SEEDS
        and degree == CANONICAL_DEGREE
        and roots == CANONICAL_ROOTS
    )


def artifact_paths(prefix: Path) -> tuple[Path, Path, Path]:
    return (
        Path(f"{prefix}.events.csv"),
        Path(f"{prefix}.csv"),
        Path(f"{prefix}.md"),
    )


def csv_has_columns(path: Path, required: set[str]) -> bool:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return required.issubset(set(reader.fieldnames or ())) and next(reader, None) is not None
    except (OSError, csv.Error):
        return False


def run_is_complete(prefix: Path) -> bool:
    event_path, aggregate_path, summary_path = artifact_paths(prefix)
    return (
        csv_has_columns(event_path, REQUIRED_EVENT_COLUMNS)
        and csv_has_columns(aggregate_path, {"estimator", "approx_code_bits_per_candidate"})
        and summary_path.is_file()
        and summary_path.stat().st_size > 0
    )


def load_previous_manifest(manifest_path: Path) -> dict[str, object]:
    if not manifest_path.is_file():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest root is not an object")
        return manifest
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot parse prior manifest {manifest_path}: {error}") from error


def manifest_commands(manifest: Mapping[str, object]) -> dict[str, list[str]]:
    runs = manifest.get("runs", [])
    if not isinstance(runs, list):
        raise ValueError("prior manifest runs field is not a list")
    return {
        str(run["prefix"]): [str(part) for part in run["command"]]
        for run in runs
        if isinstance(run, dict) and "prefix" in run and "command" in run
    }


def resume_command_matches(
    prefix: Path, command: Sequence[str], previous_commands: Mapping[str, Sequence[str]]
) -> bool:
    return list(previous_commands.get(str(prefix), ())) == list(command)


def higher_percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    return ordered[min(math.ceil(position), len(ordered) - 1)]


def mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else math.nan


def normal_ci(values: Sequence[float]) -> tuple[float, float, float, int]:
    """Return mean and query-level normal-approximation 95% CI."""
    if not values:
        return math.nan, math.nan, math.nan, 0
    center = statistics.fmean(values)
    if len(values) == 1:
        return center, center, center, 1
    z_value = NormalDist().inv_cdf(0.975)
    half_width = z_value * statistics.stdev(values) / math.sqrt(len(values))
    return center, center - half_width, center + half_width, len(values)


def load_events(spec: RunSpec) -> list[Event]:
    event_path = artifact_paths(spec.prefix)[0]
    with event_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_EVENT_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{event_path} is missing event columns: {sorted(missing)}")
        events = [
            Event(
                subset=spec.setting.subset,
                max_queries=spec.setting.max_queries,
                seed=spec.seed,
                query_id=int(row["query_id"]),
                root_id=int(row["root_id"]),
                exact_best_id=int(row["exact_best_id"]),
                exact_best_distance=float(row["exact_best_distance"]),
                exact_gap=float(row["exact_gap"]),
                degree=int(row["degree"]),
                distinct_clusters=int(row["distinct_clusters"]),
                estimator=row["estimator"],
                rank_exact_best=float(row["rank_exact_best"]),
                est_best_id=int(row["est_best_id"]),
                est_best_estimate=float(row["est_best_estimate"]),
                est_best_exact_distance=float(row["est_best_exact_distance"]),
                exact_regret=float(row["exact_regret"]),
                top1_disagree=float(row["top1_disagree"]),
            )
            for row in reader
        ]
    if not events:
        raise ValueError(f"{event_path} contains no events")
    return events


def load_code_bits(spec: RunSpec) -> dict[str, float]:
    aggregate_path = artifact_paths(spec.prefix)[1]
    with aggregate_path.open(newline="", encoding="utf-8") as handle:
        return {
            row["estimator"]: float(row["approx_code_bits_per_candidate"])
            for row in csv.DictReader(handle)
        }


def close_float(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-6, abs_tol=1e-6)


def validate_events(
    events: Sequence[Event],
    specs: Sequence[RunSpec],
    roots_per_query: int,
    expected_degree: int,
) -> None:
    by_run: dict[tuple[int, int], list[Event]] = defaultdict(list)
    for event in events:
        by_run[(event.subset, event.seed)].append(event)

    estimators_by_subset: dict[int, tuple[str, ...]] = {}
    roots_by_subset: dict[int, tuple[tuple[int, int], ...]] = {}
    for spec in specs:
        run_key = (spec.setting.subset, spec.seed)
        run_events = by_run.get(run_key, [])
        if not run_events:
            raise ValueError(f"no events for subset={run_key[0]}, seed={run_key[1]}")
        estimators = sorted({event.estimator for event in run_events})
        query_ids = sorted({event.query_id for event in run_events})
        estimator_signature = tuple(estimators)
        previous_estimators = estimators_by_subset.setdefault(
            spec.setting.subset, estimator_signature
        )
        if estimator_signature != previous_estimators:
            raise ValueError(f"estimator set changes across seeds for subset={spec.setting.subset}")
        expected_queries = list(range(spec.setting.max_queries))
        if query_ids != expected_queries:
            raise ValueError(
                f"subset={run_key[0]}, seed={run_key[1]} has query ids {query_ids[:3]}...; "
                f"expected 0..{spec.setting.max_queries - 1}"
            )
        counts: dict[tuple[str, int], int] = defaultdict(int)
        exact_by_root: dict[tuple[int, int], tuple[int, float, float, int]] = {}
        scalar_by_root: dict[tuple[int, int], tuple[float, int, float]] = {}
        fastscan_by_root: dict[tuple[int, int], tuple[float, int, float]] = {}
        for event in run_events:
            numeric_values = (
                event.exact_best_distance,
                event.exact_gap,
                event.rank_exact_best,
                event.est_best_estimate,
                event.est_best_exact_distance,
                event.exact_regret,
                event.top1_disagree,
            )
            if not all(math.isfinite(value) for value in numeric_values):
                raise ValueError(f"non-finite event value at run={run_key}")
            if event.degree != expected_degree:
                raise ValueError(
                    f"run={run_key} reports degree={event.degree}; expected {expected_degree}"
                )
            if not event.rank_exact_best.is_integer() or not (
                1 <= event.rank_exact_best <= event.degree
            ):
                raise ValueError(f"invalid exact-best rank at run={run_key}")
            if event.top1_disagree not in (0.0, 1.0):
                raise ValueError(f"invalid top1 indicator at run={run_key}")
            if bool(event.top1_disagree) != (event.est_best_id != event.exact_best_id):
                raise ValueError(f"top1 indicator disagrees with selected id at run={run_key}")
            expected_regret = event.est_best_exact_distance - event.exact_best_distance
            if not close_float(event.exact_regret, expected_regret):
                raise ValueError(f"exact regret identity fails at run={run_key}")
            if event.exact_gap < -1e-5 or event.exact_regret < -1e-5:
                raise ValueError(f"negative exact gap or regret at run={run_key}")
            counts[(event.estimator, event.query_id)] += 1
            exact_key = (event.query_id, event.root_id)
            exact_value = (
                event.exact_best_id,
                event.exact_best_distance,
                event.exact_gap,
                event.degree,
            )
            previous = exact_by_root.setdefault(exact_key, exact_value)
            if previous[0] != exact_value[0] or previous[3] != exact_value[3] or not (
                close_float(previous[1], exact_value[1])
                and close_float(previous[2], exact_value[2])
            ):
                raise ValueError(f"inconsistent exact fields at run={run_key}, event={exact_key}")
            if event.estimator == "symqg_fht_scalar":
                scalar_by_root[exact_key] = (
                    event.rank_exact_best,
                    event.est_best_id,
                    event.exact_regret,
                )
            elif event.estimator == "symqg_fht_fastscan":
                fastscan_by_root[exact_key] = (
                    event.rank_exact_best,
                    event.est_best_id,
                    event.exact_regret,
                )
        root_signature = tuple(sorted(exact_by_root))
        previous_roots = roots_by_subset.setdefault(spec.setting.subset, root_signature)
        if root_signature != previous_roots:
            raise ValueError(f"query-root set changes across seeds for subset={spec.setting.subset}")
        if scalar_by_root or fastscan_by_root:
            if scalar_by_root.keys() != fastscan_by_root.keys():
                raise ValueError(f"scalar/FastScan event sets differ at run={run_key}")
            for exact_key, scalar in scalar_by_root.items():
                fastscan = fastscan_by_root[exact_key]
                if (
                    scalar[0] != fastscan[0]
                    or scalar[1] != fastscan[1]
                    or not close_float(scalar[2], fastscan[2])
                ):
                    raise ValueError(
                        f"scalar/FastScan ordering mismatch at run={run_key}, event={exact_key}"
                    )
        for estimator in estimators:
            for query_id in query_ids:
                count = counts[(estimator, query_id)]
                if count != roots_per_query:
                    raise ValueError(
                        f"{estimator}, query={query_id}, run={run_key} has {count} roots; "
                        f"expected {roots_per_query}"
                    )

    exact_across_seeds: dict[tuple[int, int, int], tuple[int, float, float]] = {}
    for event in events:
        key = (event.subset, event.query_id, event.root_id)
        value = (event.exact_best_id, event.exact_best_distance, event.exact_gap)
        previous = exact_across_seeds.setdefault(key, value)
        if previous[0] != value[0] or not (
            close_float(previous[1], value[1]) and close_float(previous[2], value[2])
        ):
            raise ValueError(f"exact replay changed across seeds at event={key}")


def build_query_metrics(events: Sequence[Event], top_l_values: Sequence[int]) -> list[dict[str, object]]:
    groups: dict[tuple[int, int, int, str, int], list[Event]] = defaultdict(list)
    for event in events:
        groups[(event.subset, event.max_queries, event.seed, event.estimator, event.query_id)].append(event)

    rows: list[dict[str, object]] = []
    for key in sorted(groups):
        subset, max_queries, seed, estimator, query_id = key
        group = groups[key]
        ranks = [event.rank_exact_best for event in group]
        regrets = [event.exact_regret for event in group]
        row: dict[str, object] = {
            "subset": subset,
            "max_queries": max_queries,
            "seed": seed,
            "estimator": estimator,
            "query_id": query_id,
            "root_count": len(group),
            "top1_disagreement_rate": mean([event.top1_disagree for event in group]),
            "rank_mean": mean(ranks),
            "rank_p50": higher_percentile(ranks, 0.50),
            "rank_p90": higher_percentile(ranks, 0.90),
            "rank_p99": higher_percentile(ranks, 0.99),
            "exact_regret_mean": mean(regrets),
            "exact_regret_p90": higher_percentile(regrets, 0.90),
            "exact_gap_mean": mean([event.exact_gap for event in group]),
        }
        for top_l in top_l_values:
            row[f"top{top_l}_containment"] = mean(
                [float(event.rank_exact_best <= top_l) for event in group]
            )
        rows.append(row)
    return rows


def ci_columns(prefix: str, values: Sequence[float]) -> dict[str, object]:
    center, low, high, count = normal_ci(values)
    return {
        prefix: center,
        f"{prefix}_ci95_low": low,
        f"{prefix}_ci95_high": high,
        f"{prefix}_n_queries": count,
    }


def build_seed_summary(
    query_rows: Sequence[Mapping[str, object]],
    events: Sequence[Event],
    code_bits: Mapping[tuple[int, int, str], float],
    top_l_values: Sequence[int],
) -> list[dict[str, object]]:
    query_groups: dict[tuple[int, int, int, str], list[Mapping[str, object]]] = defaultdict(list)
    event_groups: dict[tuple[int, int, int, str], list[Event]] = defaultdict(list)
    for row in query_rows:
        query_groups[(int(row["subset"]), int(row["max_queries"]), int(row["seed"]), str(row["estimator"]))].append(row)
    for event in events:
        event_groups[(event.subset, event.max_queries, event.seed, event.estimator)].append(event)

    rows: list[dict[str, object]] = []
    for key in sorted(query_groups):
        subset, max_queries, seed, estimator = key
        queries = query_groups[key]
        run_events = event_groups[key]
        ranks = [event.rank_exact_best for event in run_events]
        row: dict[str, object] = {
            "subset": subset,
            "max_queries": max_queries,
            "seed": seed,
            "estimator": estimator,
            "n_queries": len(queries),
            "n_events": len(run_events),
            "approx_code_bits_per_candidate": code_bits[(subset, seed, estimator)],
            "rank_event_p50": higher_percentile(ranks, 0.50),
            "rank_event_p90": higher_percentile(ranks, 0.90),
            "rank_event_p99": higher_percentile(ranks, 0.99),
        }
        for metric in ("top1_disagreement_rate", "rank_mean", "exact_regret_mean"):
            row.update(ci_columns(metric, [float(query[metric]) for query in queries]))
        for top_l in top_l_values:
            metric = f"top{top_l}_containment"
            row.update(ci_columns(metric, [float(query[metric]) for query in queries]))
        rows.append(row)
    return rows


def seed_average_query_rows(
    query_rows: Sequence[Mapping[str, object]], top_l_values: Sequence[int]
) -> list[dict[str, object]]:
    groups: dict[tuple[int, int, str, int], list[Mapping[str, object]]] = defaultdict(list)
    for row in query_rows:
        groups[(int(row["subset"]), int(row["max_queries"]), str(row["estimator"]), int(row["query_id"]))].append(row)
    metrics = ["top1_disagreement_rate", "rank_mean", "exact_regret_mean"] + [
        f"top{top_l}_containment" for top_l in top_l_values
    ]
    averaged: list[dict[str, object]] = []
    for key in sorted(groups):
        subset, max_queries, estimator, query_id = key
        group = groups[key]
        row: dict[str, object] = {
            "subset": subset,
            "max_queries": max_queries,
            "estimator": estimator,
            "query_id": query_id,
            "seed_count": len(group),
        }
        for metric in metrics:
            row[metric] = mean([float(item[metric]) for item in group])
        averaged.append(row)
    return averaged


def build_overall_summary(
    query_rows: Sequence[Mapping[str, object]],
    seed_rows: Sequence[Mapping[str, object]],
    events: Sequence[Event],
    code_bits: Mapping[tuple[int, int, str], float],
    top_l_values: Sequence[int],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    averaged_queries = seed_average_query_rows(query_rows, top_l_values)
    query_groups: dict[tuple[int, int, str], list[Mapping[str, object]]] = defaultdict(list)
    for row in averaged_queries:
        query_groups[(int(row["subset"]), int(row["max_queries"]), str(row["estimator"]))].append(row)

    seed_groups: dict[tuple[int, int, str], list[Mapping[str, object]]] = defaultdict(list)
    for row in seed_rows:
        seed_groups[(int(row["subset"]), int(row["max_queries"]), str(row["estimator"]))].append(row)

    event_groups: dict[tuple[int, str, int, int], list[Event]] = defaultdict(list)
    for event in events:
        event_groups[(event.subset, event.estimator, event.query_id, event.root_id)].append(event)
    seed_averaged_ranks: dict[tuple[int, str], list[float]] = defaultdict(list)
    for (subset, estimator, _query_id, _root_id), group in event_groups.items():
        seed_averaged_ranks[(subset, estimator)].append(mean([event.rank_exact_best for event in group]))

    rows: list[dict[str, object]] = []
    for key in sorted(query_groups):
        subset, max_queries, estimator = key
        queries = query_groups[key]
        seeds = seed_groups[key]
        seed_ids = sorted({int(seed["seed"]) for seed in seeds})
        bit_values = {code_bits[(subset, seed, estimator)] for seed in seed_ids}
        if len(bit_values) != 1:
            raise ValueError(f"code-bit accounting changes across seeds for {key}")
        ranks = seed_averaged_ranks[(subset, estimator)]
        row: dict[str, object] = {
            "subset": subset,
            "max_queries": max_queries,
            "estimator": estimator,
            "n_queries": len(queries),
            "seed_count": len(seed_ids),
            "approx_code_bits_per_candidate": bit_values.pop(),
            "rank_event_seedavg_p50": higher_percentile(ranks, 0.50),
            "rank_event_seedavg_p90": higher_percentile(ranks, 0.90),
            "rank_event_seedavg_p99": higher_percentile(ranks, 0.99),
        }
        for metric in ("top1_disagreement_rate", "rank_mean", "exact_regret_mean"):
            row.update(ci_columns(metric, [float(query[metric]) for query in queries]))
            seed_values = [float(seed[metric]) for seed in seeds]
            row[f"{metric}_seed_mean"] = mean(seed_values)
            row[f"{metric}_seed_std"] = statistics.stdev(seed_values) if len(seed_values) > 1 else 0.0
            row[f"{metric}_seed_min"] = min(seed_values)
            row[f"{metric}_seed_max"] = max(seed_values)
        for top_l in top_l_values:
            metric = f"top{top_l}_containment"
            row.update(ci_columns(metric, [float(query[metric]) for query in queries]))
        rows.append(row)
    return rows, averaged_queries


def build_paired_summary(
    averaged_queries: Sequence[Mapping[str, object]], top_l_values: Sequence[int]
) -> list[dict[str, object]]:
    by_key = {
        (int(row["subset"]), str(row["estimator"]), int(row["query_id"])): row
        for row in averaged_queries
    }
    estimators_by_subset: dict[int, set[str]] = defaultdict(set)
    for row in averaged_queries:
        estimators_by_subset[int(row["subset"])].add(str(row["estimator"]))
    metric_directions = {
        "top1_disagreement_rate": "lower",
        "rank_mean": "lower",
        "exact_regret_mean": "lower",
        **{f"top{top_l}_containment": "higher" for top_l in top_l_values},
    }
    rows: list[dict[str, object]] = []
    for subset in sorted(estimators_by_subset):
        candidates = sorted(name for name in estimators_by_subset[subset] if name.startswith("saq_"))
        baseline_queries = sorted(
            key[2] for key in by_key if key[0] == subset and key[1] == BASELINE_ESTIMATOR
        )
        if not baseline_queries:
            raise ValueError(f"missing {BASELINE_ESTIMATOR} for subset={subset}")
        for candidate in candidates:
            for metric, direction in metric_directions.items():
                deltas = [
                    float(by_key[(subset, candidate, query_id)][metric])
                    - float(by_key[(subset, BASELINE_ESTIMATOR, query_id)][metric])
                    for query_id in baseline_queries
                ]
                center, low, high, count = normal_ci(deltas)
                if direction == "lower":
                    wins = sum(delta < 0 for delta in deltas)
                else:
                    wins = sum(delta > 0 for delta in deltas)
                rows.append(
                    {
                        "subset": subset,
                        "candidate": candidate,
                        "baseline": BASELINE_ESTIMATOR,
                        "metric": metric,
                        "better_direction": direction,
                        "n_queries": count,
                        "candidate_minus_baseline_mean": center,
                        "candidate_minus_baseline_ci95_low": low,
                        "candidate_minus_baseline_ci95_high": high,
                        "candidate_query_win_rate": wins / count,
                    }
                )
    return rows


def build_margin_conditioned(
    events: Sequence[Event],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    margin_values: dict[tuple[int, int, int], float] = {}
    max_queries: dict[int, int] = {}
    for event in events:
        key = (event.subset, event.query_id, event.root_id)
        previous = margin_values.setdefault(key, event.exact_gap)
        if not close_float(previous, event.exact_gap):
            raise ValueError(f"exact gap differs across estimators or seeds at {key}")
        max_queries[event.subset] = event.max_queries

    boundaries: list[dict[str, object]] = []
    bucket_by_event: dict[tuple[int, int, int], int] = {}
    for subset in sorted({key[0] for key in margin_values}):
        values = [value for key, value in margin_values.items() if key[0] == subset]
        cuts = [higher_percentile(values, probability) for probability in (0.25, 0.50, 0.75)]
        boundaries.append(
            {
                "subset": subset,
                "max_queries": max_queries[subset],
                "n_query_root_events": len(values),
                "q25_exact_gap": cuts[0],
                "q50_exact_gap": cuts[1],
                "q75_exact_gap": cuts[2],
                "unit": "squared_l2",
            }
        )
        for key, value in margin_values.items():
            if key[0] != subset:
                continue
            bucket = sum(value > cut for cut in cuts)
            bucket_by_event[key] = bucket

    seed_groups: dict[tuple[int, str, int, int], list[Event]] = defaultdict(list)
    for event in events:
        seed_groups[(event.subset, event.estimator, event.query_id, event.root_id)].append(event)
    seed_averaged: list[dict[str, object]] = []
    for (subset, estimator, query_id, root_id), group in seed_groups.items():
        seed_averaged.append(
            {
                "subset": subset,
                "estimator": estimator,
                "query_id": query_id,
                "root_id": root_id,
                "bucket": bucket_by_event[(subset, query_id, root_id)],
                "exact_gap": margin_values[(subset, query_id, root_id)],
                "rank": mean([event.rank_exact_best for event in group]),
                "top1_disagree": mean([event.top1_disagree for event in group]),
                "exact_regret": mean([event.exact_regret for event in group]),
            }
        )

    groups: dict[tuple[int, str, int], list[dict[str, object]]] = defaultdict(list)
    for row in seed_averaged:
        groups[(int(row["subset"]), str(row["estimator"]), int(row["bucket"]))].append(row)
    conditioned: list[dict[str, object]] = []
    labels = ("Q1_smallest_gap", "Q2", "Q3", "Q4_largest_gap")
    for (subset, estimator, bucket), group in sorted(groups.items()):
        query_rank_groups: dict[int, list[float]] = defaultdict(list)
        for row in group:
            query_rank_groups[int(row["query_id"])].append(float(row["rank"]))
        query_rank_means = [mean(values) for values in query_rank_groups.values()]
        rank_center, rank_low, rank_high, query_count = normal_ci(query_rank_means)
        ranks = [float(row["rank"]) for row in group]
        conditioned.append(
            {
                "subset": subset,
                "estimator": estimator,
                "margin_quartile": labels[bucket],
                "n_queries": query_count,
                "n_query_root_events": len(group),
                "exact_gap_mean_squared_l2": mean([float(row["exact_gap"]) for row in group]),
                "rank_query_mean": rank_center,
                "rank_query_mean_ci95_low": rank_low,
                "rank_query_mean_ci95_high": rank_high,
                "rank_event_seedavg_p50": higher_percentile(ranks, 0.50),
                "rank_event_seedavg_p90": higher_percentile(ranks, 0.90),
                "rank_event_seedavg_p99": higher_percentile(ranks, 0.99),
                "top1_disagreement_rate": mean([float(row["top1_disagree"]) for row in group]),
                "exact_regret_mean_squared_l2": mean([float(row["exact_regret"]) for row in group]),
            }
        )
    return boundaries, conditioned


def write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for field in row:
            if field not in seen:
                seen.add(field)
                fieldnames.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def format_ci(row: Mapping[str, object], metric: str) -> str:
    return (
        f"{float(row[metric]):.6g} "
        f"[{float(row[f'{metric}_ci95_low']):.6g}, "
        f"{float(row[f'{metric}_ci95_high']):.6g}]"
    )


def write_summary_md(
    path: Path,
    overall_rows: Sequence[Mapping[str, object]],
    canonical: bool,
    settings: Sequence[Setting],
    seeds: Sequence[int],
    top_l_values: Sequence[int],
) -> None:
    display_top_l = 4 if 4 in top_l_values else max(top_l_values)
    containment_metric = f"top{display_top_l}_containment"
    selected = [
        row
        for row in overall_rows
        if str(row["estimator"]) == BASELINE_ESTIMATOR
        or str(row["estimator"]) in {"saq_fast", "saq_full"}
        or str(row["estimator"]).startswith("saq_prefix_acc")
    ]
    lines = [
        "# Phase 3 Fixed-Seed Local-Replay Summary",
        "",
        "## Statistical Unit",
        "",
        "Each row first averages the fixed roots within one held-out query. Fixed",
        "rotation seeds are then averaged within that same query. The reported 95%",
        "interval is `mean +/- 1.96 * sample_sd / sqrt(number of queries)` across",
        "queries; roots and seeds do not inflate the independent sample count.",
        "Rank percentiles are descriptive higher-order statistics over query-root",
        "events after averaging each event across seeds.",
        "",
        f"- canonical Phase 3 matrix: `{str(canonical).lower()}`",
        f"- settings: `{', '.join(f'{s.subset}:{s.max_queries}' for s in settings)}`",
        f"- rotation seeds: `{','.join(str(seed) for seed in seeds)}`",
        "- exact gap and exact regret unit: squared L2",
        "- containment and disagreement unit: fraction of roots per query",
        "",
        "## Main Local-Ordering Results",
        "",
        f"| subset | estimator | code bits only | top-1 disagreement (95% CI) | mean rank (95% CI) | event p90 rank | exact regret (95% CI) | top-{display_top_l} containment (95% CI) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in selected:
        lines.append(
            f"| {row['subset']} | {row['estimator']} | "
            f"{float(row['approx_code_bits_per_candidate']):.6g} | "
            f"{format_ci(row, 'top1_disagreement_rate')} | "
            f"{format_ci(row, 'rank_mean')} | "
            f"{float(row['rank_event_seedavg_p90']):.6g} | "
            f"{format_ci(row, 'exact_regret_mean')} | "
            f"{format_ci(row, containment_metric)} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Constraint",
            "",
            "This output evaluates independent fixed local neighborhoods, not a",
            "path-dependent graph traversal. `code bits only` is a logical payload",
            "count, not complete byte traffic or runtime. The driver therefore does",
            "not automatically declare the Phase 3 continue condition satisfied.",
            "Use `phase3_paired_vs_symqg.csv`, `phase3_seed_summary.csv`, and",
            "`phase3_margin_conditioned.csv` to evaluate stability before applying",
            "the predeclared stop/continue rule.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def file_provenance(path: Path) -> dict[str, object]:
    resolved = path.resolve()
    stat = resolved.stat()
    return {"path": str(resolved), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def git_revision(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build_specs(output_dir: Path, settings: Sequence[Setting], seeds: Sequence[int]) -> list[RunSpec]:
    return [
        RunSpec(
            setting=setting,
            seed=seed,
            prefix=output_dir / "runs" / f"subset_{setting.subset}" / f"seed_{seed:02d}",
        )
        for setting in settings
        for seed in seeds
    ]


def build_command(
    binary: Path,
    spec: RunSpec,
    data_file: Path,
    query_file: Path,
    index_file: Path,
    degree: int,
    roots: int,
) -> list[str]:
    return [
        str(binary.resolve()),
        "-dataset=gist_sample50k",
        "-K=512",
        "-B=4",
        "-enable_PCA=true",
        f"-graph_data_file={data_file.resolve()}",
        f"-graph_query_file={query_file.resolve()}",
        f"-graph_index_file={index_file.resolve()}",
        f"-graph_subset={spec.setting.subset}",
        f"-graph_degree={degree}",
        f"-graph_max_queries={spec.setting.max_queries}",
        f"-graph_roots_per_query={roots}",
        f"-graph_topl_max={min(max(TOP_L_VALUES), degree)}",
        f"-graph_symqg_rotation_seed={spec.seed}",
        f"-graph_output_prefix={spec.prefix.resolve()}",
        "-searcher_safe_block_min_mode=2",
        "-searcher_dist_type=0",
    ]


def aggregate(
    output_dir: Path,
    specs: Sequence[RunSpec],
    roots: int,
    degree: int,
    top_l_values: Sequence[int],
    canonical: bool,
) -> None:
    events: list[Event] = []
    code_bits: dict[tuple[int, int, str], float] = {}
    for spec in specs:
        if not run_is_complete(spec.prefix):
            raise ValueError(f"run is incomplete: {spec.prefix}")
        run_events = load_events(spec)
        events.extend(run_events)
        run_code_bits = load_code_bits(spec)
        missing_estimators = {event.estimator for event in run_events} - set(run_code_bits)
        if missing_estimators:
            raise ValueError(
                f"aggregate CSV for {spec.prefix} is missing estimators: "
                f"{sorted(missing_estimators)}"
            )
        for estimator, bits in run_code_bits.items():
            code_bits[(spec.setting.subset, spec.seed, estimator)] = bits

    validate_events(events, specs, roots, degree)
    query_rows = build_query_metrics(events, top_l_values)
    seed_rows = build_seed_summary(query_rows, events, code_bits, top_l_values)
    overall_rows, averaged_queries = build_overall_summary(
        query_rows, seed_rows, events, code_bits, top_l_values
    )
    paired_rows = build_paired_summary(averaged_queries, top_l_values)
    margin_boundaries, margin_rows = build_margin_conditioned(events)

    write_csv(output_dir / "phase3_query_metrics.csv", query_rows)
    write_csv(output_dir / "phase3_seed_summary.csv", seed_rows)
    write_csv(output_dir / "phase3_overall_summary.csv", overall_rows)
    write_csv(output_dir / "phase3_paired_vs_symqg.csv", paired_rows)
    write_csv(output_dir / "phase3_margin_boundaries.csv", margin_boundaries)
    write_csv(output_dir / "phase3_margin_conditioned.csv", margin_rows)
    settings = tuple(dict.fromkeys(spec.setting for spec in specs))
    seeds = tuple(dict.fromkeys(spec.seed for spec in specs))
    write_summary_md(
        output_dir / "phase3_summary.md",
        overall_rows,
        canonical,
        settings,
        seeds,
        top_l_values,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default="./bin/profile_graph_frontier")
    parser.add_argument("--artifact-root", default="data/gist_sample50k")
    parser.add_argument("--data-file")
    parser.add_argument("--query-file")
    parser.add_argument("--index-file")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--setting",
        action="append",
        help="SUBSET:QUERIES; repeat or comma-separate. Default: 1024:50,4096:100",
    )
    parser.add_argument("--seeds", default="0-9", help="Comma/range list; default: 0-9")
    parser.add_argument("--degree", type=int, default=CANONICAL_DEGREE)
    parser.add_argument("--roots-per-query", type=int, default=CANONICAL_ROOTS)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    parser.set_defaults(resume=True)
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.degree <= 0 or args.roots_per_query <= 0:
        raise ValueError("degree and roots-per-query must be positive")
    settings = parse_settings(args.setting)
    for setting in settings:
        if args.degree >= setting.subset:
            raise ValueError("degree must be smaller than every subset")
        if args.roots_per_query > setting.subset:
            raise ValueError("roots-per-query cannot exceed a subset")
    seeds = parse_seeds(args.seeds)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_root = Path(args.artifact_root).expanduser()
    data_file = Path(args.data_file) if args.data_file else artifact_root / "gist_sample50k_base_pca.fvecs"
    query_file = Path(args.query_file) if args.query_file else artifact_root / "gist_sample50k_query_pca.fvecs"
    index_file = Path(args.index_file) if args.index_file else artifact_root / "ivf512_b4_caq_adj_seg_pca.index"
    binary = Path(args.binary).expanduser()
    repo_root = Path(__file__).resolve().parents[1]
    specs = build_specs(output_dir, settings, seeds)
    canonical = is_canonical(settings, seeds, args.degree, args.roots_per_query)

    if not args.aggregate_only and not args.dry_run:
        for path in (binary, data_file, query_file, index_file):
            if not path.is_file():
                raise FileNotFoundError(path)

    commands = {
        str(spec.prefix): build_command(
            binary, spec, data_file, query_file, index_file, args.degree, args.roots_per_query
        )
        for spec in specs
    }
    current_inputs: dict[str, object] = {}
    if not args.aggregate_only and not args.dry_run:
        current_inputs = {
            "binary": file_provenance(binary),
            "data": file_provenance(data_file),
            "queries": file_provenance(query_file),
            "index": file_provenance(index_file),
        }
    manifest: dict[str, object] = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(repo_root),
        "canonical_phase3_matrix": canonical,
        "statistical_unit": "query",
        "ci_method": "query-level normal-approximation 95% CI",
        "dataset": "gist_sample50k",
        "K": 512,
        "B": 4,
        "pca": True,
        "degree": args.degree,
        "roots_per_query": args.roots_per_query,
        "settings": [setting.__dict__ for setting in settings],
        "rotation_seeds": list(seeds),
        "inputs": current_inputs,
        "runs": [],
    }

    manifest_path = output_dir / "manifest.json"
    previous_manifest = load_previous_manifest(manifest_path) if args.resume else {}
    previous_commands = manifest_commands(previous_manifest)
    for spec in specs:
        command = commands[str(spec.prefix)]
        run_record: dict[str, object] = {
            "subset": spec.setting.subset,
            "max_queries": spec.setting.max_queries,
            "seed": spec.seed,
            "prefix": str(spec.prefix),
            "command": command,
        }
        if args.aggregate_only:
            run_record["status"] = "aggregate_only"
        elif args.dry_run:
            run_record["status"] = "dry_run"
            print(" ".join(command))
        elif args.resume and run_is_complete(spec.prefix):
            if not resume_command_matches(spec.prefix, command, previous_commands):
                raise ValueError(
                    f"complete outputs at {spec.prefix} do not match the prior manifest; "
                    "use a new --output-dir or pass --no-resume to replace them"
                )
            if previous_manifest.get("inputs") != current_inputs:
                raise ValueError(
                    "complete outputs do not match current binary/input provenance; "
                    "use a new --output-dir or pass --no-resume to replace them"
                )
            run_record["status"] = "resumed_existing"
            print(f"[resume] {spec.prefix}")
        else:
            spec.prefix.parent.mkdir(parents=True, exist_ok=True)
            log_path = Path(f"{spec.prefix}.log")
            print(
                f"[run] subset={spec.setting.subset} queries={spec.setting.max_queries} "
                f"seed={spec.seed}"
            )
            start_time = time.monotonic()
            with log_path.open("w", encoding="utf-8") as log:
                log.write("command: " + " ".join(command) + "\n\n")
                completed = subprocess.run(
                    command,
                    cwd=repo_root,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            run_record["wall_seconds"] = time.monotonic() - start_time
            run_record["returncode"] = completed.returncode
            run_record["log"] = str(log_path)
            run_record["status"] = "completed" if completed.returncode == 0 else "failed"
            if completed.returncode != 0:
                manifest["runs"].append(run_record)
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                raise RuntimeError(f"Phase 3 run failed; inspect {log_path}")
            if not run_is_complete(spec.prefix):
                raise RuntimeError(f"Phase 3 run returned success but outputs are incomplete: {spec.prefix}")
        manifest["runs"].append(run_record)
        if not args.aggregate_only:
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        return 0
    aggregate(
        output_dir,
        specs,
        args.roots_per_query,
        args.degree,
        tuple(top_l for top_l in TOP_L_VALUES if top_l <= args.degree),
        canonical,
    )
    print(f"Phase 3 query-level outputs written to {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(2)
