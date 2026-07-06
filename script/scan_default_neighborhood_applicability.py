#!/usr/bin/env python3
"""Scan where the default-neighborhood planner has applicable plan shapes.

This is a lightweight pre-evaluation pass.  It only needs each dataset's
`*_base_pca.vars.fvecs` artifact, reuses the SAQ default-plan DP and the
default-neighborhood candidate generator, and reports whether the current fixed
policy has any non-default candidate to score.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from generate_default_neighborhood_plans import (
    compact_seg_plan,
    generate_candidates,
    infer_default_plan,
)
from propose_residual_plan import K_DIM_PADDING_SIZE
from segment_diagnostics import read_fvecs


DEFAULT_ROOT = Path("/tmp/saq-run")
DEFAULT_DATE = "2026_07_06"
DEFAULT_BITS = (3.0, 4.0, 5.0)


@dataclass(frozen=True)
class ArtifactDataset:
    dataset: str
    data_dir: Path
    vars_path: Path


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def compact_float(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value).replace(".", "p")


def discover_datasets(data_root: Path, selected: set[str] | None) -> list[ArtifactDataset]:
    suffix = "_base_pca.vars.fvecs"
    datasets: list[ArtifactDataset] = []
    for vars_path in sorted(data_root.glob(f"*/*{suffix}")):
        dataset = vars_path.name[: -len(suffix)]
        if selected is not None and dataset not in selected:
            continue
        datasets.append(ArtifactDataset(dataset=dataset, data_dir=vars_path.parent, vars_path=vars_path))
    return datasets


def variance_summary(vars_path: Path) -> dict[str, Any]:
    variance = read_fvecs(vars_path).reshape(-1).astype(np.float64, copy=False)
    padded_dim = int(((variance.size + K_DIM_PADDING_SIZE - 1) // K_DIM_PADDING_SIZE) * K_DIM_PADDING_SIZE)
    total = float(variance.sum())

    def share(top: int) -> float:
        if total <= 0:
            return 0.0
        return float(variance[: min(top, variance.size)].sum() / total)

    return {
        "dimension_raw": int(variance.size),
        "dimension_padded": padded_dim,
        "variance_top64_share": share(64),
        "variance_top128_share": share(128),
        "variance_top256_share": share(256),
    }


def joined_families(rows: list[dict[str, Any]]) -> str:
    families = sorted(
        {
            family
            for row in rows
            for family in str(row.get("families", "")).split(";")
            if family and family != "default"
        }
    )
    return ";".join(families)


def classify_default(default_row: dict[str, Any]) -> str:
    segment_count = int(default_row["segment_count"])
    zero_tail_dim = int(default_row["zero_tail_dim_len"])
    if segment_count == 1:
        return "single_uniform"
    if zero_tail_dim > 0:
        return "multi_segment_with_zero_tail"
    return "multi_segment_no_zero_tail"


def classify_applicability(default_row: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    non_default = [row for row in rows if not row["is_default"]]
    feasible = [row for row in non_default if row["is_feasible"]]
    if feasible:
        return "has_feasible_non_default_candidates"
    if int(default_row["segment_count"]) == 1:
        return "abstain_single_uniform_default"
    if non_default:
        return "non_default_candidates_guard_rejected"
    return "abstain_no_non_default_candidates"


def scan_one(dataset: ArtifactDataset, avg_bits: float, args: argparse.Namespace) -> dict[str, Any]:
    variance = variance_summary(dataset.vars_path)
    gen_args = argparse.Namespace(
        data_dir=dataset.data_dir,
        dataset=dataset.dataset,
        avg_bits=avg_bits,
        default_plan="",
        default_plan_csv=None,
        plan_id=0,
        dimension=0,
        min_positive_bits=args.min_positive_bits,
        min_zero_tail_dim=args.min_zero_tail_dim,
        max_segments=args.max_segments,
        max_nonzero_segment_dim=args.max_nonzero_segment_dim,
        exclude_internal_1bit=args.exclude_internal_1bit,
        exclude_nonfinal_1bit=args.exclude_nonfinal_1bit,
        filter_infeasible=False,
        require_nonincreasing_bits=args.require_nonincreasing_bits,
        expect_plan=[],
        output_prefix=args.output_prefix,
    )
    default, default_meta = infer_default_plan(gen_args)
    total_dim = sum(int(seg["dim_len"]) for seg in default)
    rows = generate_candidates(default, avg_bits, total_dim, gen_args)
    default_rows = [row for row in rows if row["is_default"]]
    if len(default_rows) != 1:
        raise ValueError(f"expected one default row for {dataset.dataset} B={avg_bits}, got {len(default_rows)}")
    default_row = default_rows[0]
    non_default = [row for row in rows if not row["is_default"]]
    feasible = [row for row in non_default if row["is_feasible"]]
    infeasible = [row for row in non_default if not row["is_feasible"]]
    top_feasible = ";".join(str(row["seg_plan"]) for row in feasible[:5])

    meta = default_meta.get("meta", {}) if isinstance(default_meta, dict) else {}
    result = {
        "dataset": dataset.dataset,
        "data_dir": str(dataset.data_dir),
        "avg_bits": avg_bits,
        "status": "ok",
        **variance,
        "default_plan": compact_seg_plan(default),
        "default_shape": classify_default(default_row),
        "default_segment_count": int(default_row["segment_count"]),
        "default_nonzero_segment_count": int(default_row["nonzero_segment_count"]),
        "default_positive_bitwidths": str(default_row["positive_bitwidths"]),
        "default_zero_tail_dim": int(default_row["zero_tail_dim_len"]),
        "default_max_segment_dim": int(default_row["max_segment_dim_len"]),
        "default_max_nonzero_segment_dim": int(default_row["max_nonzero_segment_dim_len"]),
        "default_has_positive_1bit_segment": bool(default_row["has_positive_1bit_segment"]),
        "candidate_count": len(rows),
        "non_default_candidate_count": len(non_default),
        "feasible_non_default_candidate_count": len(feasible),
        "infeasible_non_default_candidate_count": len(infeasible),
        "non_default_families": joined_families(non_default),
        "feasible_non_default_families": joined_families(feasible),
        "top_feasible_non_default_plans": top_feasible,
        "applicability": classify_applicability(default_row, rows),
        "dp_cost": meta.get("dp_cost", ""),
        "dp_used_bits": meta.get("dp_used_bits", ""),
        "total_bits_budget": meta.get("total_bits_budget", ""),
    }
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "dataset",
        "avg_bits",
        "status",
        "dimension_raw",
        "dimension_padded",
        "variance_top64_share",
        "variance_top128_share",
        "variance_top256_share",
        "default_plan",
        "default_shape",
        "default_segment_count",
        "default_nonzero_segment_count",
        "default_positive_bitwidths",
        "default_zero_tail_dim",
        "default_max_segment_dim",
        "default_max_nonzero_segment_dim",
        "default_has_positive_1bit_segment",
        "candidate_count",
        "non_default_candidate_count",
        "feasible_non_default_candidate_count",
        "infeasible_non_default_candidate_count",
        "non_default_families",
        "feasible_non_default_families",
        "top_feasible_non_default_plans",
        "applicability",
        "dp_cost",
        "dp_used_bits",
        "total_bits_budget",
        "data_dir",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan default-neighborhood applicability across datasets/B.")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_ROOT / "data", help="Root containing SAQ dataset artifact directories.")
    parser.add_argument("--dataset", action="append", default=[], help="Dataset prefix to scan. Repeatable. Defaults to all discovered artifacts.")
    parser.add_argument("--bits", type=float, nargs="+", default=list(DEFAULT_BITS), help="Average bit budgets to scan.")
    parser.add_argument("--date", default=DEFAULT_DATE, help="Date label used by the default output prefix.")
    parser.add_argument("--output-prefix", type=Path, default=None, help="Output prefix for .csv and .json files.")
    parser.add_argument("--min-positive-bits", type=int, default=2, help="Generator guard: minimum positive segment bits.")
    parser.add_argument("--min-zero-tail-dim", type=int, default=0, help="Generator guard: minimum nonempty zero-tail length.")
    parser.add_argument("--max-segments", type=int, default=6, help="Generator guard: maximum total segment count.")
    parser.add_argument("--max-nonzero-segment-dim", type=int, default=0, help="Generator guard: maximum positive segment width.")
    parser.add_argument("--exclude-internal-1bit", action="store_true", help="Generator guard: reject internal 1-bit segments.")
    parser.add_argument(
        "--exclude-nonfinal-1bit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generator guard: reject non-final 1-bit segments.",
    )
    parser.add_argument(
        "--require-nonincreasing-bits",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require segment bits to be nonincreasing from head to tail.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = set(args.dataset) if args.dataset else None
    datasets = discover_datasets(args.data_root, selected)
    if selected is not None:
        found = {dataset.dataset for dataset in datasets}
        missing = sorted(selected - found)
        if missing:
            raise FileNotFoundError(f"missing dataset artifacts for: {', '.join(missing)}")
    if not datasets:
        raise FileNotFoundError(f"no *_base_pca.vars.fvecs artifacts under {args.data_root}")

    prefix = args.output_prefix or (
        DEFAULT_ROOT / "reports" / f"default_neighborhood_applicability_scan_{args.date}"
    )
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        for avg_bits in args.bits:
            label = f"{dataset.dataset} B={compact_float(avg_bits)}"
            print(f"=== SCAN {label} ===", flush=True)
            try:
                row = scan_one(dataset, float(avg_bits), args)
            except Exception as exc:  # keep broad so one bad artifact does not hide the rest
                row = {
                    "dataset": dataset.dataset,
                    "data_dir": str(dataset.data_dir),
                    "avg_bits": float(avg_bits),
                    "status": "error",
                    "error": str(exc),
                }
            rows.append(row)
            print(json.dumps(row, default=json_default), flush=True)

    csv_path = prefix.with_suffix(".csv")
    json_path = prefix.with_suffix(".json")
    write_csv(csv_path, rows)
    summary = {
        "data_root": args.data_root,
        "datasets": [dataset.dataset for dataset in datasets],
        "bits": [float(bit) for bit in args.bits],
        "guards": {
            "min_positive_bits": args.min_positive_bits,
            "min_zero_tail_dim": args.min_zero_tail_dim,
            "max_segments": args.max_segments,
            "max_nonzero_segment_dim": args.max_nonzero_segment_dim,
            "exclude_internal_1bit": args.exclude_internal_1bit,
            "exclude_nonfinal_1bit": args.exclude_nonfinal_1bit,
            "require_nonincreasing_bits": args.require_nonincreasing_bits,
        },
        "summary_csv": csv_path,
        "rows": rows,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2, default=json_default) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "summary_csv": str(csv_path),
                "summary_json": str(json_path),
                "row_count": len(rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
