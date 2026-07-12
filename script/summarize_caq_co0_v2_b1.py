#!/usr/bin/env python3
"""Frozen V2-B1 cell-bootstrap analysis.

This program summarizes only a completed CO-0 v2 B1 measurement. It exposes
no dataset, view, arm, seed, threshold, or bootstrap override.
"""

import argparse
import csv
import gzip
import hashlib
import json
import math
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

import numpy as np


HYPOTHESES_SHA256 = "a70d38f380f2b4efa29c536bdf2c015f1af314552e78eb906dfc24dc8e7c7f34"
BOOTSTRAP_SEED = 20260711
BOOTSTRAP_REPLICATES = 10000
CLUSTERS = 512
ALPHA = 0.05
ARMS = ("lvq_init", "caq_r6", "caq_local_fixed_point", "corrected_exact")
ARM_INDEX = {name: index for index, name in enumerate(ARMS)}
SEEDS = (0, 1, 2)


@dataclass(frozen=True)
class DatasetConfig:
    dataset_id: str
    original_rows: int
    selected_rows: int
    views: Tuple[str, ...]
    leading: str
    controls: Mapping[str, str]


DATASET_CONFIGS = {
    "gist_sample50k_k512": DatasetConfig(
        dataset_id="gist_sample50k_k512",
        original_rows=50000,
        selected_rows=50000,
        views=(
            "native_s0_d64_b11",
            "native_s1_d192_b6",
            "native_s2_d320_b4",
            "native_s3_d256_b2",
            "uniform_s0_d64_b4",
            "uniform_s1_d192_b4",
            "uniform_s2_d320_b4",
            "uniform_s3_d256_b4",
            "whole_d832_b4",
        ),
        leading="native_s0_d64_b11",
        controls={
            "LEAD_B4": "uniform_s0_d64_b4",
            "S1": "native_s1_d192_b6",
            "S2": "native_s2_d320_b4",
            "S3": "native_s3_d256_b2",
            "WHOLE": "whole_d832_b4",
        },
    ),
    "cifar60k_k512": DatasetConfig(
        dataset_id="cifar60k_k512",
        original_rows=60000,
        selected_rows=50000,
        views=(
            "native_s0_d64_b9",
            "native_s1_d192_b5",
            "native_s2_d128_b3",
            "uniform_s0_d64_b4",
            "uniform_s1_d192_b4",
            "uniform_s2_d128_b4",
            "whole_d384_b4",
        ),
        leading="native_s0_d64_b9",
        controls={
            "LEAD_B4": "uniform_s0_d64_b4",
            "S1": "native_s1_d192_b5",
            "S2": "native_s2_d128_b3",
            "WHOLE": "whole_d384_b4",
        },
    ),
}


EXPECTED_HYPOTHESIS_IDS = (
    "M_GIST_R6",
    "M_GIST_LOCAL",
    "M_CIFAR_R6",
    "M_CIFAR_LOCAL",
    "A_GIST_R6_LEAD_B4",
    "A_GIST_R6_S1",
    "A_GIST_R6_S2",
    "A_GIST_R6_S3",
    "A_GIST_R6_WHOLE",
    "A_GIST_LOCAL_LEAD_B4",
    "A_GIST_LOCAL_S1",
    "A_GIST_LOCAL_S2",
    "A_GIST_LOCAL_S3",
    "A_GIST_LOCAL_WHOLE",
    "A_CIFAR_R6_LEAD_B4",
    "A_CIFAR_R6_S1",
    "A_CIFAR_R6_S2",
    "A_CIFAR_R6_WHOLE",
    "A_CIFAR_LOCAL_LEAD_B4",
    "A_CIFAR_LOCAL_S1",
    "A_CIFAR_LOCAL_S2",
    "A_CIFAR_LOCAL_WHOLE",
    "E_GIST_NORM_IP",
    "E_CIFAR_NORM_IP",
)


class AnalysisError(RuntimeError):
    pass


@dataclass
class DatasetMeasurements:
    config: DatasetConfig
    factors: np.ndarray
    zero: np.ndarray
    loaded: np.ndarray
    cells: np.ndarray


@dataclass
class PairMeasurements:
    cells: np.ndarray
    normalized_error: np.ndarray
    absolute_error: np.ndarray
    zero: np.ndarray


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AnalysisError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--hypotheses", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def load_ledger(path: Path) -> Mapping[str, object]:
    require(path.is_file(), "hypothesis ledger does not exist")
    require(sha256(path) == HYPOTHESES_SHA256, "hypothesis ledger SHA-256 mismatch")
    ledger = json.loads(path.read_text(encoding="utf-8"))
    require(ledger["family_size"] == 24, "hypothesis family size changed")
    require(ledger["alpha"] == ALPHA, "hypothesis alpha changed")
    ids = tuple(item["id"] for item in ledger["hypotheses"])
    require(ids == EXPECTED_HYPOTHESIS_IDS, "hypothesis order or identity changed")
    bootstrap = ledger["bootstrap"]
    require(bootstrap["replicates"] == BOOTSTRAP_REPLICATES, "bootstrap count changed")
    require(bootstrap["seed"] == BOOTSTRAP_SEED, "bootstrap seed changed")
    require(bootstrap["draws_per_replicate"] == CLUSTERS, "bootstrap draw count changed")
    return ledger


def allocate_dataset(config: DatasetConfig) -> DatasetMeasurements:
    shape = (len(config.views), len(ARMS), len(SEEDS), config.original_rows)
    return DatasetMeasurements(
        config=config,
        factors=np.full(shape, np.nan, dtype=np.float64),
        zero=np.zeros(shape, dtype=np.bool_),
        loaded=np.zeros(shape, dtype=np.bool_),
        cells=np.full(config.original_rows, -1, dtype=np.int16),
    )


def load_encoding_measurements(run_dir: Path) -> Dict[str, DatasetMeasurements]:
    measurements = {
        dataset_id: allocate_dataset(config)
        for dataset_id, config in DATASET_CONFIGS.items()
    }
    files = sorted(run_dir.glob("**/*.encoding.csv.gz"))
    require(len(files) == 192, f"expected 192 encoding shards, found {len(files)}")

    row_count = 0
    for path in files:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            require(reader.fieldnames is not None, f"missing encoding header: {path}")
            for row in reader:
                dataset_id = row["dataset_id"]
                require(dataset_id in measurements, f"unknown dataset in {path}")
                dataset = measurements[dataset_id]
                config = dataset.config
                try:
                    view_index = config.views.index(row["view_id"])
                except ValueError as error:
                    raise AnalysisError(f"unknown view in {path}: {row['view_id']}") from error
                require(row["arm"] in ARM_INDEX, f"unknown arm in {path}")
                arm_index = ARM_INDEX[row["arm"]]
                seed = int(row["logical_seed"])
                vector_id = int(row["vector_id"])
                cell = int(row["cell_id"])
                require(seed in SEEDS, f"seed out of range in {path}")
                require(0 <= vector_id < config.original_rows, f"vector id out of range in {path}")
                require(0 <= cell < CLUSTERS, f"cell out of range in {path}")
                require(
                    not dataset.loaded[view_index, arm_index, seed, vector_id],
                    f"duplicate encoding row in {path}",
                )
                factor = float(row["independent_error_factor"])
                require(math.isfinite(factor), f"non-finite independent factor in {path}")
                dataset.factors[view_index, arm_index, seed, vector_id] = factor
                dataset.zero[view_index, arm_index, seed, vector_id] = bool(int(row["zero_segment"]))
                dataset.loaded[view_index, arm_index, seed, vector_id] = True
                if dataset.cells[vector_id] == -1:
                    dataset.cells[vector_id] = cell
                else:
                    require(dataset.cells[vector_id] == cell, "vector/cell assignment changed across shards")
                row_count += 1

    expected_rows = 0
    for dataset in measurements.values():
        selected = dataset.cells >= 0
        require(int(selected.sum()) == dataset.config.selected_rows, "selected-vector count mismatch")
        require(bool(dataset.loaded[:, :, :, selected].all()), "encoding matrix is incomplete")
        zero_reference = dataset.zero[:, :1, :, selected]
        require(
            bool(np.equal(dataset.zero[:, :, :, selected], zero_reference).all()),
            "zero-segment flags differ across arms",
        )
        expected_rows += (
            dataset.config.selected_rows
            * len(dataset.config.views)
            * len(ARMS)
            * len(SEEDS)
        )
    require(row_count == expected_rows, "encoding row count mismatch")
    return measurements


def load_pair_measurements(run_dir: Path) -> Dict[str, PairMeasurements]:
    records: Dict[str, MutableMapping[Tuple[int, int], Dict[str, object]]] = {
        dataset_id: {} for dataset_id in DATASET_CONFIGS
    }
    relevant_files: List[Path] = []
    for path in sorted(run_dir.glob("**/*.pairs.csv.gz")):
        dataset_id = next((name for name in DATASET_CONFIGS if name in path.parts), None)
        if dataset_id is None:
            continue
        config = DATASET_CONFIGS[dataset_id]
        if path.parent.name != config.leading:
            continue
        arm = path.name.split(".", 1)[0]
        if arm not in ("caq_r6", "corrected_exact"):
            continue
        relevant_files.append(path)

    require(len(relevant_files) == 12, f"expected 12 primary pair shards, found {len(relevant_files)}")
    for path in relevant_files:
        dataset_id = next(name for name in DATASET_CONFIGS if name in path.parts)
        arm = path.name.split(".", 1)[0]
        arm_index = 0 if arm == "caq_r6" else 1
        with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                seed = int(row["logical_seed"])
                cell = int(row["cell_id"])
                pair_rank = int(row["pair_rank"])
                require(seed in SEEDS and 0 <= cell < CLUSTERS, f"invalid pair key in {path}")
                key = (cell, pair_rank)
                record = records[dataset_id].setdefault(
                    key,
                    {
                        "normalized": np.full((2, 3), np.nan, dtype=np.float64),
                        "absolute": np.full((2, 3), np.nan, dtype=np.float64),
                        "zero": np.zeros((2, 3), dtype=np.bool_),
                        "loaded": np.zeros((2, 3), dtype=np.bool_),
                    },
                )
                loaded = record["loaded"]
                require(not loaded[arm_index, seed], f"duplicate pair row in {path}")
                normalized = float(row["normalized_absolute_ip_error"])
                absolute = float(row["absolute_ip_error"])
                require(math.isfinite(normalized) and math.isfinite(absolute), f"non-finite pair error in {path}")
                record["normalized"][arm_index, seed] = normalized
                record["absolute"][arm_index, seed] = absolute
                record["zero"][arm_index, seed] = bool(int(row["zero_norm_pair"]))
                loaded[arm_index, seed] = True

    result: Dict[str, PairMeasurements] = {}
    expected_counts = {
        "gist_sample50k_k512": 24842,
        "cifar60k_k512": 24884,
    }
    for dataset_id, dataset_records in records.items():
        ordered = sorted(dataset_records.items())
        require(len(ordered) == expected_counts[dataset_id], "primary pair count mismatch")
        cells = np.empty(len(ordered), dtype=np.int16)
        normalized = np.empty((2, 3, len(ordered)), dtype=np.float64)
        absolute = np.empty((2, 3, len(ordered)), dtype=np.float64)
        zero = np.empty((2, 3, len(ordered)), dtype=np.bool_)
        for index, ((cell, _pair_rank), record) in enumerate(ordered):
            require(bool(record["loaded"].all()), "primary pair matrix is incomplete")
            require(bool(np.equal(record["zero"], record["zero"][:1]).all()), "pair zero flags differ across arms")
            cells[index] = cell
            normalized[:, :, index] = record["normalized"]
            absolute[:, :, index] = record["absolute"]
            zero[:, :, index] = record["zero"]
        result[dataset_id] = PairMeasurements(cells, normalized, absolute, zero)
    return result


def bootstrap_draws() -> np.ndarray:
    generator = np.random.Generator(np.random.PCG64(BOOTSTRAP_SEED))
    return generator.integers(0, CLUSTERS, size=(BOOTSTRAP_REPLICATES, CLUSTERS))


def cell_sums(cells: np.ndarray, values: np.ndarray) -> np.ndarray:
    return np.bincount(cells, weights=values, minlength=CLUSTERS).astype(np.float64)


def bootstrap_ratio(
    numerator_by_cell: np.ndarray,
    denominator_by_cell: np.ndarray,
    draws: np.ndarray,
) -> Tuple[np.ndarray, int]:
    result = np.empty(draws.shape[0], dtype=np.float64)
    zero_denominators = 0
    for begin in range(0, draws.shape[0], 256):
        batch = draws[begin : begin + 256]
        numerator = numerator_by_cell[batch].sum(axis=1)
        denominator = denominator_by_cell[batch].sum(axis=1)
        zero = denominator == 0
        zero_denominators += int(zero.sum())
        result[begin : begin + len(batch)] = np.divide(
            numerator,
            denominator,
            out=np.zeros_like(numerator),
            where=~zero,
        )
    return result, zero_denominators


def valid_view(dataset: DatasetMeasurements, view_index: int, arm_index: int) -> np.ndarray:
    selected = dataset.cells >= 0
    required_arms = (ARM_INDEX["lvq_init"], arm_index, ARM_INDEX["corrected_exact"])
    finite = np.isfinite(dataset.factors[view_index, required_arms, :, :]).all(axis=(0, 1))
    nonzero = ~dataset.zero[view_index, required_arms, :, :].any(axis=(0, 1))
    return selected & finite & nonzero


def ratio_components(
    dataset: DatasetMeasurements,
    view_index: int,
    arm_index: int,
    mask: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    init = dataset.factors[view_index, ARM_INDEX["lvq_init"], :, :]
    arm = dataset.factors[view_index, arm_index, :, :]
    exact = dataset.factors[view_index, ARM_INDEX["corrected_exact"], :, :]
    numerator_seed = arm[:, mask] - exact[:, mask]
    denominator_seed = init[:, mask] - exact[:, mask]
    numerator = numerator_seed.mean(axis=0)
    denominator = denominator_seed.mean(axis=0)
    cells = dataset.cells[mask].astype(np.int64)
    return numerator, denominator, numerator_seed, denominator_seed


def ratio_statistic(
    dataset: DatasetMeasurements,
    view_index: int,
    arm_index: int,
    mask: np.ndarray,
    draws: np.ndarray,
) -> Mapping[str, object]:
    numerator, denominator, numerator_seed, denominator_seed = ratio_components(
        dataset, view_index, arm_index, mask
    )
    main_denominator = float(denominator.sum())
    require(main_denominator != 0, "registered ratio denominator is zero")
    point = float(numerator.sum() / main_denominator)
    numerator_cells = cell_sums(dataset.cells[mask], numerator)
    denominator_cells = cell_sums(dataset.cells[mask], denominator)
    bootstraps, zero_replicates = bootstrap_ratio(numerator_cells, denominator_cells, draws)
    seed_points = []
    for seed in SEEDS:
        seed_denominator = float(denominator_seed[seed].sum())
        require(seed_denominator != 0, "seed-specific ratio denominator is zero")
        seed_points.append(float(numerator_seed[seed].sum() / seed_denominator))
    return {
        "point": point,
        "bootstraps": bootstraps,
        "seed_points": seed_points,
        "zero_denominator_replicates": zero_replicates,
        "valid_count": int(mask.sum()),
        "numerator_quantiles": np.percentile(numerator, [0, 25, 50, 75, 100], method="linear").tolist(),
        "denominator_quantiles": np.percentile(denominator, [0, 25, 50, 75, 100], method="linear").tolist(),
    }


def materiality_statistic(
    dataset: DatasetMeasurements,
    arm: str,
    draws: np.ndarray,
) -> Mapping[str, object]:
    view_index = dataset.config.views.index(dataset.config.leading)
    arm_index = ARM_INDEX[arm]
    mask = valid_view(dataset, view_index, arm_index)
    return ratio_statistic(dataset, view_index, arm_index, mask, draws)


def amplification_statistic(
    dataset: DatasetMeasurements,
    arm: str,
    control_name: str,
    draws: np.ndarray,
) -> Mapping[str, object]:
    leading_index = dataset.config.views.index(dataset.config.leading)
    control_index = dataset.config.views.index(dataset.config.controls[control_name])
    arm_index = ARM_INDEX[arm]
    mask = valid_view(dataset, leading_index, arm_index) & valid_view(dataset, control_index, arm_index)
    leading = ratio_statistic(dataset, leading_index, arm_index, mask, draws)
    control = ratio_statistic(dataset, control_index, arm_index, mask, draws)
    return {
        "point": float(leading["point"] - control["point"]),
        "bootstraps": leading["bootstraps"] - control["bootstraps"],
        "seed_points": [
            float(leading["seed_points"][seed] - control["seed_points"][seed])
            for seed in SEEDS
        ],
        "zero_denominator_replicates": int(
            leading["zero_denominator_replicates"] + control["zero_denominator_replicates"]
        ),
        "valid_count": int(mask.sum()),
        "leading_point": float(leading["point"]),
        "control_point": float(control["point"]),
    }


def estimator_statistic(pair: PairMeasurements, draws: np.ndarray) -> Mapping[str, object]:
    valid = ~pair.zero.any(axis=(0, 1))
    valid &= np.isfinite(pair.normalized_error).all(axis=(0, 1))
    valid &= np.isfinite(pair.absolute_error).all(axis=(0, 1))
    require(bool(valid.any()), "no valid registered estimator pairs")
    normalized_seed = pair.normalized_error[0, :, valid] - pair.normalized_error[1, :, valid]
    absolute_seed = pair.absolute_error[0, :, valid] - pair.absolute_error[1, :, valid]
    # NumPy advanced indexing places the selected-pair axis first in this form.
    if normalized_seed.shape[0] != len(SEEDS):
        normalized_seed = normalized_seed.T
        absolute_seed = absolute_seed.T
    normalized = normalized_seed.mean(axis=0)
    absolute = absolute_seed.mean(axis=0)
    cells = pair.cells[valid].astype(np.int64)
    normalized_cells = cell_sums(cells, normalized)
    count_cells = np.bincount(cells, minlength=CLUSTERS).astype(np.float64)
    bootstraps, zero_replicates = bootstrap_ratio(normalized_cells, count_cells, draws)
    return {
        "point": float(normalized.mean()),
        "bootstraps": bootstraps,
        "seed_points": [float(normalized_seed[seed].mean()) for seed in SEEDS],
        "absolute_point": float(absolute.mean()),
        "absolute_seed_points": [float(absolute_seed[seed].mean()) for seed in SEEDS],
        "zero_denominator_replicates": zero_replicates,
        "valid_count": int(valid.sum()),
    }


def hypothesis_statistic(
    hypothesis: Mapping[str, object],
    datasets: Mapping[str, DatasetMeasurements],
    pairs: Mapping[str, PairMeasurements],
    draws: np.ndarray,
) -> Mapping[str, object]:
    hypothesis_id = str(hypothesis["id"])
    dataset_id = str(hypothesis["dataset"])
    if hypothesis_id.startswith("M_"):
        arm = "caq_r6" if hypothesis_id.endswith("_R6") else "caq_local_fixed_point"
        return materiality_statistic(datasets[dataset_id], arm, draws)
    if hypothesis_id.startswith("A_"):
        arm = "caq_r6" if "_R6_" in hypothesis_id else "caq_local_fixed_point"
        control = next(
            name for name in datasets[dataset_id].config.controls if hypothesis_id.endswith("_" + name)
        )
        return amplification_statistic(datasets[dataset_id], arm, control, draws)
    require(hypothesis_id.startswith("E_"), "unknown hypothesis class")
    return estimator_statistic(pairs[dataset_id], draws)


def summarize_statistic(
    hypothesis: Mapping[str, object], statistic: Mapping[str, object]
) -> Dict[str, object]:
    bootstraps = statistic["bootstraps"]
    null = float(hypothesis["value"])
    p_value = float((1 + np.count_nonzero(bootstraps <= null)) / (BOOTSTRAP_REPLICATES + 1))
    result = {
        "id": hypothesis["id"],
        "class": hypothesis["class"],
        "dataset": hypothesis["dataset"],
        "null_value": null,
        "point_estimate": float(statistic["point"]),
        "percentile_2_5": float(np.percentile(bootstraps, 2.5, method="linear")),
        "percentile_97_5": float(np.percentile(bootstraps, 97.5, method="linear")),
        "one_sided_lower_5": float(np.percentile(bootstraps, 5.0, method="linear")),
        "one_sided_p_value": p_value,
        "seed_point_estimates": [float(value) for value in statistic["seed_points"]],
        "valid_count": int(statistic["valid_count"]),
        "zero_denominator_replicates": int(statistic["zero_denominator_replicates"]),
    }
    for key in (
        "absolute_point",
        "absolute_seed_points",
        "leading_point",
        "control_point",
        "numerator_quantiles",
        "denominator_quantiles",
    ):
        if key in statistic:
            value = statistic[key]
            result[key] = value if isinstance(value, list) else float(value)
    return result


def apply_holm(results: List[Dict[str, object]]) -> None:
    order = sorted(range(len(results)), key=lambda index: (results[index]["one_sided_p_value"], index))
    running = 0.0
    family_size = len(results)
    for rank, index in enumerate(order):
        candidate = min(1.0, (family_size - rank) * results[index]["one_sided_p_value"])
        running = max(running, candidate)
        results[index]["holm_adjusted_p_value"] = running
        results[index]["holm_reject"] = running <= ALPHA


def evaluate(
    ledger: Mapping[str, object],
    datasets: Mapping[str, DatasetMeasurements],
    pairs: Mapping[str, PairMeasurements],
) -> Dict[str, object]:
    draws = bootstrap_draws()
    results = []
    raw_statistics: Dict[str, Mapping[str, object]] = {}
    for hypothesis in ledger["hypotheses"]:
        statistic = hypothesis_statistic(hypothesis, datasets, pairs, draws)
        raw_statistics[str(hypothesis["id"])] = statistic
        results.append(summarize_statistic(hypothesis, statistic))
    apply_holm(results)

    result_by_id = {result["id"]: result for result in results}
    all_holm = all(bool(result["holm_reject"]) for result in results)
    materiality = all(
        result_by_id[hypothesis_id]["one_sided_lower_5"] >= 0.10
        for hypothesis_id in ("M_GIST_R6", "M_GIST_LOCAL", "M_CIFAR_R6", "M_CIFAR_LOCAL")
    )
    zero_denominator_replicates = sum(
        int(result["zero_denominator_replicates"]) for result in results
    )
    ratio_seed_consistency = all(
        all(value >= 0.10 for value in result_by_id[hypothesis_id]["seed_point_estimates"])
        for hypothesis_id in ("M_GIST_R6", "M_GIST_LOCAL", "M_CIFAR_R6", "M_CIFAR_LOCAL")
    )
    estimator_ids = ("E_GIST_NORM_IP", "E_CIFAR_NORM_IP")
    estimator_seed_consistency = all(
        all(value > 0 for value in result_by_id[hypothesis_id]["seed_point_estimates"])
        for hypothesis_id in estimator_ids
    )
    unscaled_estimator_direction = all(
        result_by_id[hypothesis_id].get("absolute_point", 0) > 0
        for hypothesis_id in estimator_ids
    )

    conditional_pass = all(
        (
            all_holm,
            materiality,
            ratio_seed_consistency,
            estimator_seed_consistency,
            unscaled_estimator_direction,
        )
    )
    return {
        "schema_version": 1,
        "stage": "V2-B1",
        "decision": "CONDITIONAL_PASS" if conditional_pass else "NO_GO",
        "interpretation": (
            "A conditional pass establishes only an SAQ-specific limitation; it is not a method contribution."
            if conditional_pass
            else "The frozen limitation gate did not pass; no rescue sweep is authorized."
        ),
        "checks": {
            "all_24_holm_rejected": all_holm,
            "materiality_lower_bounds_at_least_0_10": materiality,
            "zero_denominator_replicates": zero_denominator_replicates,
            "ratio_seed_consistency": ratio_seed_consistency,
            "estimator_seed_consistency": estimator_seed_consistency,
            "unscaled_estimator_direction": unscaled_estimator_direction,
        },
        "sensitivity": {
            hypothesis_id: {
                "point": result_by_id[hypothesis_id]["point_estimate"],
                "lower_5": result_by_id[hypothesis_id]["one_sided_lower_5"],
                "threshold_0_05": result_by_id[hypothesis_id]["one_sided_lower_5"] >= 0.05,
                "registered_threshold_0_10": result_by_id[hypothesis_id]["one_sided_lower_5"] >= 0.10,
                "threshold_0_20": result_by_id[hypothesis_id]["one_sided_lower_5"] >= 0.20,
            }
            for hypothesis_id in ("M_GIST_R6", "M_GIST_LOCAL", "M_CIFAR_R6", "M_CIFAR_LOCAL")
        },
        "hypotheses": results,
        "bootstrap": {
            "rng": "NumPy Generator(PCG64)",
            "seed": BOOTSTRAP_SEED,
            "replicates": BOOTSTRAP_REPLICATES,
            "draws_per_replicate": CLUSTERS,
            "percentile_method": "linear",
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
    }


def verify_run_manifest(run_dir: Path) -> Mapping[str, object]:
    manifest_path = run_dir / "run_manifest.json"
    require(manifest_path.is_file(), "run manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["status"] == "COMPLETE", "B1 run is not complete")
    require(manifest["threads"] == 1, "B1 run did not use one thread")
    require(manifest["encoding_rows"] == 9600000, "run-manifest encoding count mismatch")
    require(manifest["pair_rows"] == 4773192, "run-manifest pair count mismatch")
    require(len(manifest["shards"]) == 192, "run-manifest shard count mismatch")
    require(
        sum(item["total_bytes"] for item in manifest["shards"])
        == manifest["serialized_output_bytes"],
        "run-manifest serialized-byte sum mismatch",
    )
    require(
        sum(item["code_bytes"] for item in manifest["shards"]) == manifest["code_bytes"],
        "run-manifest code-byte sum mismatch",
    )
    require(
        manifest["work_accounting_ns"]["arms"]["corrected_exact"]["cpu"]
        == manifest["exact_cpu_ns"],
        "exact CPU accounting mismatch",
    )
    return manifest


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    verify_run_manifest(args.run_dir)
    ledger = load_ledger(args.hypotheses)
    datasets = load_encoding_measurements(args.run_dir)
    pairs = load_pair_measurements(args.run_dir)
    result = evaluate(ledger, datasets, pairs)
    result["analysis_work_accounting_seconds"] = {
        "wall": time.perf_counter() - wall_start,
        "cpu": time.process_time() - cpu_start,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"stage": "V2-B1", "decision": result["decision"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (AnalysisError, KeyError, ValueError) as error:
        print(f"V2-B1 summarizer stopped: {error}", file=sys.stderr)
        raise SystemExit(1)
