#!/usr/bin/env python3
"""Rebuild the fixed-policy validation report from scored run summaries.

The script turns the curated fixed-policy method spec into reproducible
artifacts. It reads the existing cross-dataset scorer/evaluation summaries,
joins them with the default-plan applicability scan, applies the fixed decision
policy, and writes a clean validation table in CSV, Markdown, and JSON.

It intentionally does not rerun indexing, scoring, or search. The inputs are
the versioned report files produced by those drivers.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("/tmp/saq-run")
DEFAULT_DATE = "2026_07_07"
DEFAULT_APPLICABILITY_CSV = "default_neighborhood_applicability_scan_2026_07_06.csv"
DEFAULT_SUMMARY_CSVS = (
    "default_neighborhood_gist_B3_after_1bit_fix_2026_07_07.csv",
    "default_neighborhood_cross_dataset_validation_2026_07_06.csv",
    "default_neighborhood_gist_B5_holdout_2026_07_06.csv",
    "default_neighborhood_cifar_budget_holdout_2026_07_06.csv",
    "default_neighborhood_audio_holdout_2026_07_06.csv",
    "default_neighborhood_word2vec_holdout_2026_07_06.csv",
)

RUN_ORDER = (
    "gist_full_K4096_B3",
    "gist_full_K4096_B4",
    "gist_full_K4096_B5",
    "cifar60k_B3",
    "cifar60k_B4",
    "cifar60k_B5",
    "deep1M_sample100k_B4",
    "deep1M_sample100k_B5",
    "audio_K4096_B4",
    "word2vec_sample100k_B4",
)

TABLE_FIELDS = (
    "dataset",
    "run",
    "K",
    "B",
    "metric",
    "default_shape",
    "default_plan",
    "policy_decision",
    "selected_or_tested_plan",
    "selection_role",
    "candidate_family",
    "scorer_signal",
    "evaluation_nprobe",
    "default_recall",
    "candidate_recall",
    "delta_recall",
    "qps_nprobe",
    "default_qps",
    "candidate_qps",
    "qps_ratio",
    "interpretation",
    "source_report",
)

INTERPRETATIONS = {
    "gist_full_K4096_B3": "positive after 1-bit fix",
    "gist_full_K4096_B4": "strongest QPS-positive GIST case",
    "gist_full_K4096_B5": "positive high-budget GIST holdout",
    "cifar60k_B3": "small positive CIFAR low-budget holdout",
    "cifar60k_B4": "small positive CIFAR original case",
    "cifar60k_B5": "small positive CIFAR high-budget holdout",
    "deep1M_sample100k_B4": "rejected negative: speed gain costs too much recall",
    "deep1M_sample100k_B5": "rejected negative: speed gain costs too much recall",
    "audio_K4096_B4": "stable abstention; applicability scan also abstains at B=3/B=5",
    "word2vec_sample100k_B4": "stable abstention; applicability scan also abstains at B=3/B=5",
}

EXTENDED_SIGNAL_RUNS = {"gist_full_K4096_B3"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def b_text(value: str | int | float) -> str:
    if value == "":
        return ""
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


def key_for_applicability(row: dict[str, str]) -> tuple[str, str]:
    return (row.get("dataset", ""), b_text(row.get("avg_bits", "")))


def fmt(value: str | float | int | None, places: int) -> str:
    if value is None or value == "":
        return ""
    quantum = Decimal(1).scaleb(-places)
    rounded = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
    return f"{rounded:.{places}f}"


def recall_places(metric: str) -> int:
    return 4 if metric == "R@10" else 5


def source_json_path(source_csv: Path) -> Path:
    return source_csv.with_suffix(".json")


def load_selected_candidate_extras(source_csvs: list[Path]) -> dict[tuple[str, str], dict[str, Any]]:
    extras: dict[tuple[str, str], dict[str, Any]] = {}
    for csv_path in source_csvs:
        json_path = source_json_path(csv_path)
        if not json_path.exists():
            continue
        payload = load_json(json_path)
        for result in payload.get("results", []):
            spec = result.get("spec") or {}
            run = str(result.get("run") or spec.get("name") or "")
            selected = result.get("selected") or []
            if isinstance(selected, dict):
                selected_items = [selected]
            else:
                selected_items = selected
            for selected_item in selected_items:
                selected_plan = str(selected_item.get("seg_plan", ""))
                if run and selected_plan:
                    extras[(run, selected_plan)] = selected_item
    return extras


def load_summary_rows(source_csvs: list[Path]) -> dict[str, dict[str, str]]:
    rows_by_run: dict[str, dict[str, str]] = {}
    for source_csv in source_csvs:
        for row in read_csv(source_csv):
            run = row.get("run", "")
            if not run or run in rows_by_run:
                continue
            merged = dict(row)
            merged["source_report"] = source_csv.name
            rows_by_run[run] = merged
    return rows_by_run


def choose_policy_decision(row: dict[str, str]) -> str:
    role = row.get("selection_reason", "")
    skipped = row.get("scorer_skipped_reason", "")
    if role in {"conservative_eligible", "frontier_like"}:
        return "promote"
    if role == "risky_fallback_best_score":
        return "reject"
    if role == "no_candidate_selected" or skipped:
        return "abstain"
    return "review"


def select_evaluation_nprobe(row: dict[str, str]) -> str:
    qps_nprobe = row.get("qps_nprobe", "")
    if qps_nprobe and row.get(f"default_recall_np{qps_nprobe}", "") != "":
        return qps_nprobe
    for nprobe in ("800", "400", "200", "100", "50"):
        if row.get(f"default_recall_np{nprobe}", "") != "":
            return nprobe
    return ""


def scorer_signal(row: dict[str, str], extras: dict[tuple[str, str], dict[str, Any]]) -> str:
    run = row.get("run", "")
    skipped = row.get("scorer_skipped_reason", "")
    if skipped:
        return skipped
    parts = [
        f"recall-risk={fmt(row.get('best_recall_risk_score'), 4)}",
        f"speed-proxy={fmt(row.get('best_speed_proxy_ratio_vs_default'), 4)}",
    ]
    candidate_plan = row.get("candidate_plan", "")
    extra = extras.get((run, candidate_plan), {})
    if run in EXTENDED_SIGNAL_RUNS and extra:
        soft = extra.get("pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default")
        weighted = extra.get("pair_proxy_weighted_ratio_mean_ratio_vs_default")
        parts.append(f"soft-inversion={fmt(soft, 4)}")
        parts.append(f"weighted-ratio={fmt(weighted, 4)}")
    return "; ".join(parts)


def build_report_row(
    row: dict[str, str],
    applicability_by_key: dict[tuple[str, str], dict[str, str]],
    extras: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    dataset = row.get("dataset", "")
    run = row.get("run", "")
    b = b_text(row.get("avg_bits", ""))
    app_row = applicability_by_key.get((dataset, b), {})
    metric = f"R@{row.get('topk', '')}"
    decision = choose_policy_decision(row)
    evaluation_nprobe = select_evaluation_nprobe(row)
    recall_digits = recall_places(metric)
    default_recall = ""
    candidate_recall = ""
    delta_recall = ""
    if evaluation_nprobe:
        default_recall = fmt(row.get(f"default_recall_np{evaluation_nprobe}"), recall_digits)
        candidate_recall = fmt(row.get(f"recall_np{evaluation_nprobe}"), recall_digits)
        delta_recall = fmt(row.get(f"delta_np{evaluation_nprobe}"), recall_digits)

    selected_plan = row.get("candidate_plan", "") if decision in {"promote", "reject"} else ""
    selection_role = row.get("selection_reason", "") if decision in {"promote", "reject"} else ""
    candidate_family = row.get("candidate_family", "") if decision in {"promote", "reject"} else ""

    return {
        "dataset": dataset,
        "run": run,
        "K": b_text(row.get("k", "")),
        "B": b,
        "metric": metric,
        "default_shape": app_row.get("default_shape", ""),
        "default_plan": row.get("default_plan", ""),
        "policy_decision": decision,
        "selected_or_tested_plan": selected_plan,
        "selection_role": selection_role,
        "candidate_family": candidate_family,
        "scorer_signal": scorer_signal(row, extras),
        "evaluation_nprobe": evaluation_nprobe,
        "default_recall": default_recall,
        "candidate_recall": candidate_recall,
        "delta_recall": delta_recall,
        "qps_nprobe": row.get("qps_nprobe", "") if decision in {"promote", "reject"} else "",
        "default_qps": fmt(row.get("default_qps"), 4) if decision in {"promote", "reject"} else "",
        "candidate_qps": fmt(row.get("custom_qps"), 4) if decision in {"promote", "reject"} else "",
        "qps_ratio": fmt(row.get("qps_ratio_vs_default"), 4) if decision in {"promote", "reject"} else "",
        "interpretation": INTERPRETATIONS.get(run, ""),
        "source_report": row.get("source_report", ""),
    }


def build_report(
    source_csvs: list[Path], applicability_csv: Path
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    source_rows = load_summary_rows(source_csvs)
    applicability_rows = read_csv(applicability_csv)
    applicability_by_key = {key_for_applicability(row): row for row in applicability_rows}
    extras = load_selected_candidate_extras(source_csvs)

    missing = [run for run in RUN_ORDER if run not in source_rows]
    if missing:
        raise SystemExit(f"Missing required run rows: {', '.join(missing)}")

    rows = [
        build_report_row(source_rows[run], applicability_by_key, extras)
        for run in RUN_ORDER
    ]
    metadata = {
        "source_summary_csvs": [str(path) for path in source_csvs],
        "applicability_csv": str(applicability_csv),
        "run_order": list(RUN_ORDER),
        "decision_counts": dict(Counter(row["policy_decision"] for row in rows)),
    }
    return rows, metadata


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TABLE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]], metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    display_fields = (
        "dataset",
        "B",
        "metric",
        "default_shape",
        "policy_decision",
        "selected_or_tested_plan",
        "delta_recall",
        "qps_ratio",
        "interpretation",
    )
    lines = [
        "# Fixed-Policy Validation Report",
        "",
        "This report is generated from scored/evaluated SAQ summary files.",
        "It does not rerun indexing, scoring, or search.",
        "",
        "## Inputs",
        "",
    ]
    for source in metadata["source_summary_csvs"]:
        lines.append(f"- `{source}`")
    lines.extend(
        [
            f"- `{metadata['applicability_csv']}`",
            "",
            "## Clean Validation Table",
            "",
            "| " + " | ".join(display_fields) + " |",
            "| " + " | ".join("---" for _ in display_fields) + " |",
        ]
    )
    for row in rows:
        lines.append("| " + " | ".join(row.get(field, "") for field in display_fields) + " |")
    lines.extend(
        [
            "",
            "## Decision Counts",
            "",
        ]
    )
    for decision, count in sorted(metadata["decision_counts"].items()):
        lines.append(f"- `{decision}`: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, rows: list[dict[str, str]], metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(metadata)
    payload["rows"] = rows
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compare_expected(actual_rows: list[dict[str, str]], expected_csv: Path) -> None:
    expected_rows = read_csv(expected_csv)
    if actual_rows == expected_rows:
        print(f"Expected table matches: {expected_csv}")
        return
    print(f"Expected table mismatch: {expected_csv}")
    max_len = max(len(actual_rows), len(expected_rows))
    for index in range(max_len):
        actual = actual_rows[index] if index < len(actual_rows) else None
        expected = expected_rows[index] if index < len(expected_rows) else None
        if actual == expected:
            continue
        print(f"First differing row index: {index}")
        print("Actual:")
        print(json.dumps(actual, indent=2, sort_keys=True))
        print("Expected:")
        print(json.dumps(expected, indent=2, sort_keys=True))
        break
    raise SystemExit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the fixed-policy validation CSV/Markdown/JSON report."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument(
        "--summary-csv",
        type=Path,
        action="append",
        default=None,
        help="Summary CSV to include. Defaults to the known validation reports.",
    )
    parser.add_argument(
        "--applicability-csv",
        type=Path,
        default=None,
        help="Applicability scan CSV. Defaults under ROOT/reports.",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=None,
        help="Output prefix without extension. Defaults under ROOT/reports.",
    )
    parser.add_argument(
        "--expected-csv",
        type=Path,
        default=None,
        help="Optional CSV to compare against after generation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reports_dir = args.root / "reports"
    source_csvs = args.summary_csv or [reports_dir / name for name in DEFAULT_SUMMARY_CSVS]
    applicability_csv = args.applicability_csv or reports_dir / DEFAULT_APPLICABILITY_CSV
    output_prefix = args.output_prefix or reports_dir / f"fixed_policy_validation_{args.date}"

    rows, metadata = build_report(source_csvs, applicability_csv)
    csv_path = output_prefix.with_suffix(".csv")
    md_path = output_prefix.with_suffix(".md")
    json_path = output_prefix.with_suffix(".json")
    write_csv(csv_path, rows)
    write_markdown(md_path, rows, metadata)
    write_json(json_path, rows, metadata)

    print(f"Wrote CSV: {csv_path}")
    print(f"Wrote Markdown: {md_path}")
    print(f"Wrote JSON: {json_path}")
    print(f"Decision counts: {metadata['decision_counts']}")

    if args.expected_csv:
        compare_expected(rows, args.expected_csv)


if __name__ == "__main__":
    main()
