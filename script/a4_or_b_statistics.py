#!/usr/bin/env python3
"""Analyze two complete A4-OR-B dataset output directories."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


REPLICATES = 10_000
SEED = 20_260_713
RATES = (4, 8)
ARMS = ("D", "A", "P", "V")


@dataclass
class Dataset:
    name: str
    root: Path
    row_keys: list[tuple[int, int]]
    pair_keys: list[tuple[int, int, int]]
    rows: np.ndarray
    pairs: np.ndarray
    cells: list[int]
    row_indices: dict[int, np.ndarray]
    pair_indices: dict[int, np.ndarray]
    group_sse: dict[tuple[int, str], np.ndarray]
    summary: dict[tuple[int, str], dict[str, str]]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def specification(row: dict[str, str]) -> tuple[int, str] | None:
    histogram = int(row["histogram"])
    rate = int(row["rate"])
    arm = row["arm"]
    if arm in ("D", "A") and histogram == 1024:
        return rate, arm
    if arm in ("P", "V") and histogram == 0:
        return rate, arm
    return None


def value_matrix(
    records: list[dict[str, str]],
    key_fields: tuple[str, ...],
    value_field: str,
) -> tuple[list[tuple[int, ...]], np.ndarray]:
    values: dict[tuple[int, str], dict[tuple[int, ...], float]] = {}
    for row in records:
        spec = specification(row)
        if spec is None:
            continue
        key = tuple(int(row[field]) for field in key_fields)
        values.setdefault(spec, {})[key] = float(row[value_field])
    expected = {(rate, arm) for rate in RATES for arm in ARMS}
    if set(values) != expected:
        raise ValueError(f"missing model records: {set(values) ^ expected}")
    keys = sorted(next(iter(values.values())))
    if any(sorted(group) != keys for group in values.values()):
        raise ValueError("row identities differ across model records")
    columns = [(rate, arm) for rate in RATES for arm in ARMS]
    matrix = np.asarray(
        [[values[column][key] for column in columns] for key in keys],
        dtype=np.float64,
    )
    return keys, matrix


def cell_indices(
    keys: list[tuple[int, ...]],
) -> tuple[list[int], dict[int, np.ndarray]]:
    cells = sorted({key[0] for key in keys})
    indices = {
        cell: np.asarray(
            [index for index, key in enumerate(keys) if key[0] == cell],
            dtype=np.int64,
        )
        for cell in cells
    }
    return cells, indices


def load_dataset(name: str, root: Path) -> Dataset:
    row_keys, rows = value_matrix(
        read_tsv(root / "reconstruction.tsv"),
        ("cell_id", "vector_id"),
        "row_sse",
    )
    pair_keys, pairs = value_matrix(
        read_tsv(root / "pairs.tsv"),
        ("cell_id", "left_vector_id", "right_vector_id"),
        "absolute_error",
    )
    cells, rows_by_cell = cell_indices(row_keys)
    pair_cells, pairs_by_cell = cell_indices(pair_keys)
    if pair_cells != cells:
        raise ValueError("row and pair cell frames differ")

    group_sse: dict[tuple[int, str], np.ndarray] = {}
    for row in read_tsv(root / "groups.tsv"):
        spec = specification(row)
        if spec is None:
            continue
        group_sse.setdefault(spec, np.zeros(64, dtype=np.float64))[
            int(row["group"])
        ] = float(row["heldout_sse"])
    summary = {
        (int(row["rate"]), row["arm"]): row
        for row in read_tsv(root / "summary.tsv")
        if specification(row) is not None
    }
    return Dataset(
        name,
        root,
        row_keys,
        pair_keys,
        rows,
        pairs,
        cells,
        rows_by_cell,
        pairs_by_cell,
        group_sse,
        summary,
    )


def sequential_sum(values: np.ndarray) -> np.ndarray:
    if values.shape[0] == 0:
        raise ValueError("empty resample")
    return np.cumsum(values, axis=0, dtype=np.float64)[-1]


def resample(
    dataset: Dataset,
    cell_draws: np.ndarray,
    generator: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    row_means = np.empty((REPLICATES, dataset.rows.shape[1]))
    pair_means = np.empty((REPLICATES, dataset.pairs.shape[1]))
    for replicate in range(REPLICATES):
        row_parts: list[np.ndarray] = []
        pair_parts: list[np.ndarray] = []
        for cell_position in cell_draws[replicate]:
            cell = dataset.cells[int(cell_position)]
            rows = dataset.row_indices[cell]
            pairs = dataset.pair_indices[cell]
            row_parts.append(
                rows[generator.integers(0, rows.size, size=rows.size)]
            )
            pair_parts.append(
                pairs[generator.integers(0, pairs.size, size=pairs.size)]
            )
        selected_rows = np.concatenate(row_parts)
        selected_pairs = np.concatenate(pair_parts)
        row_means[replicate] = (
            sequential_sum(dataset.rows[selected_rows])
            / selected_rows.size
        )
        pair_means[replicate] = (
            sequential_sum(dataset.pairs[selected_pairs])
            / selected_pairs.size
        )
        if (replicate + 1) % 1000 == 0:
            print(
                f"{dataset.name} bootstrap "
                f"{replicate + 1}/{REPLICATES}",
                flush=True,
            )
    return row_means, pair_means


def contrasts(
    row_means: np.ndarray, pair_means: np.ndarray
) -> dict[tuple[int, str], np.ndarray]:
    result: dict[tuple[int, str], np.ndarray] = {}
    for rate_index, rate in enumerate(RATES):
        offset = rate_index * len(ARMS)
        d, a, p, v = (
            row_means[..., offset + index]
            for index in range(len(ARMS))
        )
        ed, ea = pair_means[..., offset], pair_means[..., offset + 1]
        result[rate, "L_G"] = (d - a) - 0.05 * d
        result[rate, "L_V"] = d - v
        result[rate, "L_C"] = (d - a) - 0.50 * (d - v)
        result[rate, "L_Q5"] = (ed - ea) - 0.05 * ed
        result[rate, "L_P"] = 1.01 * p - a
    return result


def infer(
    dataset: Dataset,
    row_replicates: np.ndarray,
    pair_replicates: np.ndarray,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    row_point = sequential_sum(dataset.rows) / dataset.rows.shape[0]
    pair_point = sequential_sum(dataset.pairs) / dataset.pairs.shape[0]
    point_contrasts = contrasts(row_point, pair_point)
    replicate_contrasts = contrasts(row_replicates, pair_replicates)
    inference: list[dict[str, object]] = []
    point_rows: list[dict[str, object]] = []
    for rate_index, rate in enumerate(RATES):
        offset = rate_index * len(ARMS)
        d, a, p, v = row_point[offset : offset + len(ARMS)]
        ed, ea = pair_point[offset : offset + 2]
        opportunity = d - v
        group_d = dataset.group_sse[rate, "D"]
        group_a = dataset.group_sse[rate, "A"]
        gains = group_d - group_a
        leave_one_out = [
            (gains.sum() - gains[group])
            / (group_d.sum() - group_d[group])
            for group in range(64)
        ]
        scalar_cpu = int(
            next(
                row["cpu_us"]
                for row in read_tsv(dataset.root / "phases.tsv")
                if row["phase"] == "scalar_curves"
                and row["histogram"] == "1024"
            )
        )
        p_cpu = int(dataset.summary[rate, "P"]["fit_cpu_us"])
        a_bytes = int(dataset.summary[rate, "A"]["model_bytes"])
        p_bytes = int(dataset.summary[rate, "P"]["model_bytes"])
        point_rows.append(
            {
                "dataset": dataset.name,
                "rate": rate,
                "D_D": d,
                "D_A": a,
                "D_P": p,
                "D_V": v,
                "G": (d - a) / d,
                "C": (d - a) / opportunity
                if opportunity > 0
                else float("nan"),
                "Q": (ed - ea) / ed,
                "positive_groups": int(np.count_nonzero(gains > 0)),
                "min_leave_one_group_out_G": min(leave_one_out),
                "A_fit_cpu_us": scalar_cpu
                + int(dataset.summary[rate, "A"]["fit_cpu_us"]),
                "P_fit_cpu_us": p_cpu,
                "A_model_bytes": a_bytes,
                "P_model_bytes": p_bytes,
            }
        )
        for contrast in ("L_G", "L_V", "L_C", "L_Q5", "L_P"):
            estimate = float(point_contrasts[rate, contrast])
            replicates = replicate_contrasts[rate, contrast]
            delta = replicates - estimate
            inference.append(
                {
                    "hypothesis_id": (
                        f"{contrast}_{dataset.name}_B{rate}"
                    ),
                    "estimate": estimate,
                    "basic_ci_lower": estimate
                    - np.quantile(delta, 0.975, method="linear"),
                    "basic_ci_upper": estimate
                    - np.quantile(delta, 0.025, method="linear"),
                    "one_sided_lower": estimate
                    - np.quantile(delta, 0.95, method="linear"),
                    "raw_p": (
                        1 + int(np.count_nonzero(delta >= estimate))
                    )
                    / (REPLICATES + 1),
                }
            )
    return inference, point_rows


def holm(rows: list[dict[str, object]]) -> None:
    ordered = sorted(
        rows, key=lambda row: (row["raw_p"], row["hypothesis_id"])
    )
    running = 0.0
    count = len(ordered)
    for index, row in enumerate(ordered):
        adjusted = min(
            1.0, (count - index) * float(row["raw_p"])
        )
        running = max(running, adjusted)
        row["holm_adjusted_p"] = running
        row["passes"] = running < 0.05


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), delimiter="\t"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gist", type=Path, required=True)
    parser.add_argument("--cifar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    datasets = [
        load_dataset("GIST", args.gist),
        load_dataset("CIFAR", args.cifar),
    ]
    generator = np.random.Generator(np.random.PCG64(SEED))
    cell_draws = {
        dataset.name: generator.integers(
            0,
            len(dataset.cells),
            size=(REPLICATES, len(dataset.cells)),
        )
        for dataset in datasets
    }
    inference: list[dict[str, object]] = []
    points: list[dict[str, object]] = []
    for dataset in datasets:
        row_replicates, pair_replicates = resample(
            dataset, cell_draws[dataset.name], generator
        )
        dataset_inference, dataset_points = infer(
            dataset, row_replicates, pair_replicates
        )
        inference.extend(dataset_inference)
        points.extend(dataset_points)
    holm(inference)
    inference.sort(key=lambda row: str(row["hypothesis_id"]))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_rows(args.output_dir / "bootstrap.tsv", inference)
    write_rows(args.output_dir / "points.tsv", points)
    passed = all(bool(row["passes"]) for row in inference)
    print(
        f"RESULT hypotheses={len(inference)} all_pass={passed} "
        f"output={args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
