#!/usr/bin/env python3
"""Summarize SAQ planner proxy agreement with measured data-only error."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


METRICS = (
    "mean_raw_sse",
    "mean_aligned_sse",
    "mean_direction_loss",
    "mean_fac_error",
)


def parse_float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return math.nan


def rank_values(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + j - 1) / 2.0
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return math.nan
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return math.nan
    return num / den_x / den_y


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(rank_values(xs), rank_values(ys))


def kendall(xs: list[float], ys: list[float]) -> tuple[float, float, int]:
    concordant = 0
    discordant = 0
    comparable = 0
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            dx = xs[i] - xs[j]
            dy = ys[i] - ys[j]
            if dx == 0 or dy == 0:
                continue
            comparable += 1
            if dx * dy > 0:
                concordant += 1
            else:
                discordant += 1
    if comparable == 0:
        return math.nan, math.nan, 0
    tau = (concordant - discordant) / comparable
    discord_rate = discordant / comparable
    return tau, discord_rate, comparable


def read_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows.extend(reader)
    return rows


def group_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row["case"],
        row["dataset"],
        row["source_mode"],
        row["rotation"],
        row["sample_rows"],
    )


def summarize_metric(
    key: tuple[str, str, str, str, str],
    metric: str,
    scope: str,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    xs: list[float] = []
    ys: list[float] = []
    for row in rows:
        bits = int(row["bits"])
        proxy = parse_float(row["saq_proxy"])
        value = parse_float(row[metric])
        if not math.isfinite(proxy) or not math.isfinite(value):
            continue
        if metric == "mean_fac_error" and bits == 0:
            continue
        xs.append(proxy)
        ys.append(value)
    tau, discord_rate, comparable_pairs = kendall(xs, ys)
    return {
        "case": key[0],
        "dataset": key[1],
        "source_mode": key[2],
        "rotation": key[3],
        "sample_rows": key[4],
        "scope": scope,
        "metric": metric,
        "num_candidates": len(xs),
        "spearman": spearman(xs, ys),
        "kendall_tau": tau,
        "discordant_pair_rate": discord_rate,
        "comparable_pairs": comparable_pairs,
    }


def summarize_group(key: tuple[str, str, str, str, str], rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rows_by_bit: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_bit[int(row["bits"])].append(row)

    for metric in METRICS:
        out.append(summarize_metric(key, metric, "all_bits", rows))
        bit_summaries = [summarize_metric(key, metric, f"bit={bit}", rows_by_bit[bit]) for bit in sorted(rows_by_bit)]
        out.extend(bit_summaries)

        valid = [row for row in bit_summaries if math.isfinite(row["spearman"])]
        if valid:
            out.append(
                {
                    "case": key[0],
                    "dataset": key[1],
                    "source_mode": key[2],
                    "rotation": key[3],
                    "sample_rows": key[4],
                    "scope": "within_bit_mean",
                    "metric": metric,
                    "num_candidates": sum(int(row["num_candidates"]) for row in valid),
                    "spearman": sum(float(row["spearman"]) for row in valid) / len(valid),
                    "kendall_tau": sum(float(row["kendall_tau"]) for row in valid) / len(valid),
                    "discordant_pair_rate": sum(float(row["discordant_pair_rate"]) for row in valid) / len(valid),
                    "comparable_pairs": sum(int(row["comparable_pairs"]) for row in valid),
                }
            )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fmt_float(value: Any) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        return f"{value:.4f}"
    return str(value)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Planner Proxy Agreement Summary",
        "",
        "Each row compares SAQ proxy risk against one measured data-only error metric.",
        "Higher Spearman/Kendall values mean better ranking agreement; lower discordant-pair rate means fewer pairwise inversions.",
        "",
        "| dataset | source | rotation | sample rows | scope | metric | candidates | Spearman | Kendall tau | discordant pairs |",
        "|---|---|---|---:|---|---|---:|---:|---:|---:|",
    ]
    display_rows = [row for row in rows if row["scope"] in {"all_bits", "within_bit_mean"}]
    for row in display_rows:
        lines.append(
            "| {dataset} | {source_mode} | {rotation} | {sample_rows} | {scope} | {metric} | {num_candidates} | {spearman} | {kendall_tau} | {discordant_pair_rate} |".format(
                dataset=row["dataset"],
                source_mode=row["source_mode"],
                rotation=row["rotation"],
                sample_rows=row["sample_rows"],
                scope=row["scope"],
                metric=row["metric"],
                num_candidates=row["num_candidates"],
                spearman=fmt_float(row["spearman"]),
                kendall_tau=fmt_float(row["kendall_tau"]),
                discordant_pair_rate=fmt_float(row["discordant_pair_rate"]),
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize planner proxy measurement CSVs.")
    parser.add_argument("--inputs", nargs="+", required=True, help="Measurement CSV files.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for .summary.csv and .md.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_rows([Path(path) for path in args.inputs])
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[group_key(row)].append(row)

    summary_rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        summary_rows.extend(summarize_group(key, grouped[key]))

    output_prefix = Path(args.output_prefix)
    write_csv(output_prefix.with_suffix(".summary.csv"), summary_rows)
    write_markdown(output_prefix.with_suffix(".md"), summary_rows)
    print(f"wrote {output_prefix.with_suffix('.summary.csv')}")
    print(f"wrote {output_prefix.with_suffix('.md')}")


if __name__ == "__main__":
    main()
