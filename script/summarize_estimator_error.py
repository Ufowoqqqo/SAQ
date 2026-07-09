#!/usr/bin/env python3
"""Summarize data-only CAQ/SAQ distance-estimator error measurements."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


PREDICTORS = (
    "saq_proxy",
    "mean_aligned_sse",
    "mean_direction_loss",
    "mean_fac_error",
)

TARGETS = (
    "mean_abs_ip_error",
    "mean_sq_ip_error",
    "mean_abs_l2_error",
    "mean_sq_l2_error",
    "mean_rel_l2_error",
)

FOCUS_TARGETS = {
    "mean_abs_ip_error",
    "mean_abs_l2_error",
    "mean_rel_l2_error",
}

FOCUS_PREDICTORS = {
    "saq_proxy",
    "mean_direction_loss",
    "mean_fac_error",
}


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


def solve_linear(a: list[list[float]], b: list[float]) -> list[float] | None:
    n = len(b)
    mat = [row[:] + [rhs] for row, rhs in zip(a, b)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(mat[r][col]))
        if abs(mat[pivot][col]) < 1e-12:
            return None
        if pivot != col:
            mat[col], mat[pivot] = mat[pivot], mat[col]
        div = mat[col][col]
        for j in range(col, n + 1):
            mat[col][j] /= div
        for r in range(n):
            if r == col:
                continue
            factor = mat[r][col]
            for j in range(col, n + 1):
                mat[r][j] -= factor * mat[col][j]
    return [mat[i][n] for i in range(n)]


def rank_r2(features: list[list[float]], target: list[float]) -> float:
    if len(target) < 3:
        return math.nan
    ranked_y = rank_values(target)
    ranked_features = [rank_values(col) for col in features]
    columns = [[1.0] * len(target)] + ranked_features
    p = len(columns)
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for i in range(len(target)):
        row = [columns[j][i] for j in range(p)]
        for r in range(p):
            xty[r] += row[r] * ranked_y[i]
            for c in range(p):
                xtx[r][c] += row[r] * row[c]
    beta = solve_linear(xtx, xty)
    if beta is None:
        return math.nan
    mean_y = sum(ranked_y) / len(ranked_y)
    sst = sum((y - mean_y) ** 2 for y in ranked_y)
    if sst == 0:
        return math.nan
    sse = 0.0
    for i, y in enumerate(ranked_y):
        pred = sum(beta[j] * columns[j][i] for j in range(p))
        sse += (y - pred) ** 2
    return 1.0 - sse / sst


def read_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows.extend(reader)
    return rows


def group_key(row: dict[str, str]) -> tuple[str, str, str, str, str, str]:
    return (
        row["case"],
        row["dataset"],
        row["source_mode"],
        row["rotation"],
        row["sample_rows"],
        row["max_pairs"],
    )


def finite_xy(rows: list[dict[str, str]], predictor: str, target: str) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for row in rows:
        x = parse_float(row[predictor])
        y = parse_float(row[target])
        if math.isfinite(x) and math.isfinite(y):
            xs.append(x)
            ys.append(y)
    return xs, ys


def summarize_corr(
    key: tuple[str, str, str, str, str, str],
    scope: str,
    predictor: str,
    target: str,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    xs, ys = finite_xy(rows, predictor, target)
    tau, discord_rate, comparable_pairs = kendall(xs, ys)
    return {
        "case": key[0],
        "dataset": key[1],
        "source_mode": key[2],
        "rotation": key[3],
        "sample_rows": key[4],
        "max_pairs": key[5],
        "scope": scope,
        "predictor": predictor,
        "target": target,
        "num_candidates": len(xs),
        "spearman": spearman(xs, ys),
        "kendall_tau": tau,
        "discordant_pair_rate": discord_rate,
        "comparable_pairs": comparable_pairs,
    }


def summarize_incremental(
    key: tuple[str, str, str, str, str, str],
    scope: str,
    target: str,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    proxy: list[float] = []
    direction: list[float] = []
    fac_error: list[float] = []
    y: list[float] = []
    for row in rows:
        values = {
            "proxy": parse_float(row["saq_proxy"]),
            "direction": parse_float(row["mean_direction_loss"]),
            "fac_error": parse_float(row["mean_fac_error"]),
            "target": parse_float(row[target]),
        }
        if all(math.isfinite(values[name]) for name in values):
            proxy.append(values["proxy"])
            direction.append(values["direction"])
            fac_error.append(values["fac_error"])
            y.append(values["target"])
    r2_proxy = rank_r2([proxy], y)
    r2_proxy_direction = rank_r2([proxy, direction], y)
    r2_proxy_fac = rank_r2([proxy, fac_error], y)
    return {
        "case": key[0],
        "dataset": key[1],
        "source_mode": key[2],
        "rotation": key[3],
        "sample_rows": key[4],
        "max_pairs": key[5],
        "scope": scope,
        "target": target,
        "num_candidates": len(y),
        "rank_r2_proxy": r2_proxy,
        "rank_r2_proxy_plus_direction": r2_proxy_direction,
        "rank_r2_gain_direction": r2_proxy_direction - r2_proxy
        if math.isfinite(r2_proxy) and math.isfinite(r2_proxy_direction)
        else math.nan,
        "rank_r2_proxy_plus_fac_error": r2_proxy_fac,
        "rank_r2_gain_fac_error": r2_proxy_fac - r2_proxy
        if math.isfinite(r2_proxy) and math.isfinite(r2_proxy_fac)
        else math.nan,
    }


def summarize_group(
    key: tuple[str, str, str, str, str, str], rows: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    corr_rows: list[dict[str, Any]] = []
    incremental_rows: list[dict[str, Any]] = []
    rows_by_bit: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_bit[int(row["bits"])].append(row)

    for target in TARGETS:
        for predictor in PREDICTORS:
            corr_rows.append(summarize_corr(key, "all_bits", predictor, target, rows))
            bit_rows = [
                summarize_corr(key, f"bit={bit}", predictor, target, rows_by_bit[bit])
                for bit in sorted(rows_by_bit)
            ]
            corr_rows.extend(bit_rows)
            valid = [row for row in bit_rows if math.isfinite(row["spearman"])]
            if valid:
                corr_rows.append(
                    {
                        "case": key[0],
                        "dataset": key[1],
                        "source_mode": key[2],
                        "rotation": key[3],
                        "sample_rows": key[4],
                        "max_pairs": key[5],
                        "scope": "within_bit_mean",
                        "predictor": predictor,
                        "target": target,
                        "num_candidates": sum(int(row["num_candidates"]) for row in valid),
                        "spearman": sum(float(row["spearman"]) for row in valid) / len(valid),
                        "kendall_tau": sum(float(row["kendall_tau"]) for row in valid) / len(valid),
                        "discordant_pair_rate": sum(float(row["discordant_pair_rate"]) for row in valid)
                        / len(valid),
                        "comparable_pairs": sum(int(row["comparable_pairs"]) for row in valid),
                    }
                )

        incremental_rows.append(summarize_incremental(key, "all_bits", target, rows))
        bit_inc = [
            summarize_incremental(key, f"bit={bit}", target, rows_by_bit[bit])
            for bit in sorted(rows_by_bit)
        ]
        incremental_rows.extend(bit_inc)
        valid_inc = [row for row in bit_inc if math.isfinite(row["rank_r2_gain_direction"])]
        if valid_inc:
            incremental_rows.append(
                {
                    "case": key[0],
                    "dataset": key[1],
                    "source_mode": key[2],
                    "rotation": key[3],
                    "sample_rows": key[4],
                    "max_pairs": key[5],
                    "scope": "within_bit_mean",
                    "target": target,
                    "num_candidates": sum(int(row["num_candidates"]) for row in valid_inc),
                    "rank_r2_proxy": sum(float(row["rank_r2_proxy"]) for row in valid_inc) / len(valid_inc),
                    "rank_r2_proxy_plus_direction": sum(
                        float(row["rank_r2_proxy_plus_direction"]) for row in valid_inc
                    )
                    / len(valid_inc),
                    "rank_r2_gain_direction": sum(float(row["rank_r2_gain_direction"]) for row in valid_inc)
                    / len(valid_inc),
                    "rank_r2_proxy_plus_fac_error": sum(
                        float(row["rank_r2_proxy_plus_fac_error"]) for row in valid_inc
                    )
                    / len(valid_inc),
                    "rank_r2_gain_fac_error": sum(float(row["rank_r2_gain_fac_error"]) for row in valid_inc)
                    / len(valid_inc),
                }
            )

    return corr_rows, incremental_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
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


def write_markdown(path: Path, corr_rows: list[dict[str, Any]], incremental_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Estimator Error Summary",
        "",
        "Each row is computed from query-unaware data-only residual pairs.",
        "Higher rank agreement is better; lower discordant-pair rate is better.",
        "",
        "## Predictor Agreement",
        "",
        "| dataset | scope | predictor | target | candidates | Spearman | Kendall tau | discordant pairs |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    display_corr = [
        row
        for row in corr_rows
        if row["scope"] in {"all_bits", "within_bit_mean"}
        and row["predictor"] in FOCUS_PREDICTORS
        and row["target"] in FOCUS_TARGETS
    ]
    for row in display_corr:
        lines.append(
            "| {dataset} | {scope} | {predictor} | {target} | {num_candidates} | {spearman} | {kendall_tau} | {discordant_pair_rate} |".format(
                dataset=row["dataset"],
                scope=row["scope"],
                predictor=row["predictor"],
                target=row["target"],
                num_candidates=row["num_candidates"],
                spearman=fmt_float(row["spearman"]),
                kendall_tau=fmt_float(row["kendall_tau"]),
                discordant_pair_rate=fmt_float(row["discordant_pair_rate"]),
            )
        )

    lines.extend(
        [
            "",
            "## Incremental Rank-R2",
            "",
            "The proxy-only model uses ranked `saq_proxy`; the extended models add ranked direction loss or CAQ fac-error.",
            "",
            "| dataset | scope | target | candidates | proxy R2 | +direction R2 | direction gain | +fac-error R2 | fac-error gain |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    display_inc = [
        row
        for row in incremental_rows
        if row["scope"] in {"all_bits", "within_bit_mean"} and row["target"] in FOCUS_TARGETS
    ]
    for row in display_inc:
        lines.append(
            "| {dataset} | {scope} | {target} | {num_candidates} | {rank_r2_proxy} | {rank_r2_proxy_plus_direction} | {rank_r2_gain_direction} | {rank_r2_proxy_plus_fac_error} | {rank_r2_gain_fac_error} |".format(
                dataset=row["dataset"],
                scope=row["scope"],
                target=row["target"],
                num_candidates=row["num_candidates"],
                rank_r2_proxy=fmt_float(row["rank_r2_proxy"]),
                rank_r2_proxy_plus_direction=fmt_float(row["rank_r2_proxy_plus_direction"]),
                rank_r2_gain_direction=fmt_float(row["rank_r2_gain_direction"]),
                rank_r2_proxy_plus_fac_error=fmt_float(row["rank_r2_proxy_plus_fac_error"]),
                rank_r2_gain_fac_error=fmt_float(row["rank_r2_gain_fac_error"]),
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize estimator-error measurement CSVs.")
    parser.add_argument("--inputs", nargs="+", required=True, help="Measurement CSV files.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for summary files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_rows([Path(path) for path in args.inputs])
    grouped: dict[tuple[str, str, str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[group_key(row)].append(row)

    corr_rows: list[dict[str, Any]] = []
    incremental_rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        group_corr, group_inc = summarize_group(key, grouped[key])
        corr_rows.extend(group_corr)
        incremental_rows.extend(group_inc)

    output_prefix = Path(args.output_prefix)
    write_csv(output_prefix.with_suffix(".summary.csv"), corr_rows)
    write_csv(output_prefix.with_suffix(".incremental.csv"), incremental_rows)
    write_markdown(output_prefix.with_suffix(".md"), corr_rows, incremental_rows)
    print(f"wrote {output_prefix.with_suffix('.summary.csv')}")
    print(f"wrote {output_prefix.with_suffix('.incremental.csv')}")
    print(f"wrote {output_prefix.with_suffix('.md')}")


if __name__ == "__main__":
    main()
