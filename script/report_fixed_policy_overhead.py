#!/usr/bin/env python3
"""Report fixed-policy planning and search overhead from validation artifacts.

The report separates deployable method costs from the larger research
validation workflow:

* candidate generation and data-only scorer runtime;
* sampled boundary-pair counts and scorer grid size;
* final index build time and index size for default versus selected plans;
* measured QPS curves across the validation nprobe grid.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from run_default_neighborhood_cross_dataset import (
    BUILTIN_SPECS,
    REPO_ROOT,
    SAFE_BLOCK_MIN_MODE,
    DatasetSpec,
    args_stem,
    b_label,
    bool_from_csv,
    data_dir,
    index_path,
    read_csv,
    write_json,
)


DEFAULT_ROOT = Path("/tmp/saq-run")
DEFAULT_MATRIX_JSON = DEFAULT_ROOT / "reports" / "fixed_policy_matrix_validation_2026_07_07.json"
DEFAULT_DATE = "2026_07_07"


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def compact_plan_for_path(plan: str) -> str:
    if not plan:
        return ""
    suffix = "_plan"
    for ch in plan:
        if ch.isdigit():
            suffix += ch
        elif ch in {":", "x", "X"}:
            suffix += "x"
        elif ch in {",", ";"} or ch.isspace():
            if not suffix.endswith("_"):
                suffix += "_"
    return suffix.rstrip("_")


def plan_label(plan: str) -> str:
    suffix = compact_plan_for_path(plan)
    return suffix[1:] if suffix.startswith("_") else (suffix or "default")


def qps_path(root: Path, spec: DatasetSpec, nprobe: int, plan: str = "") -> Path:
    topk_suffix = "" if spec.topk == 100 else f"_top{spec.topk}"
    return (
        root
        / "results"
        / "saq"
        / (
            f"qps_{spec.dataset}_{args_stem(spec, plan)}_th24_np{nprobe}"
            f"_sm4{topk_suffix}_safeblockminsimd.csv"
        )
    )


def index_meta_path(root: Path, spec: DatasetSpec, plan: str = "") -> Path:
    return root / "results" / "saq" / f"{spec.dataset}_{args_stem(spec, plan)}.index.csv"


def read_one_row_csv(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    if len(rows) != 1:
        raise ValueError(f"expected one row in {path}, got {len(rows)}")
    return rows[0]


def read_qps(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    row = read_one_row_csv(path)
    return {
        "qps": float(row["QPS"]),
        "avg_tm_ms": float(row["avg_tm_ms"]),
        "recall": float(row["recall"]),
        "ratio": float(row["ratio"]),
        "bw_mbps": float(row["bw_mbps"]),
        "compute_kopps": float(row["compute_kopps"]),
        "output": str(path),
    }


def read_index_time(root: Path, spec: DatasetSpec, plan: str = "") -> float | None:
    path = index_meta_path(root, spec, plan)
    if not path.exists():
        return None
    row = read_one_row_csv(path)
    value = row.get("index_time_s", "")
    return float(value) if value != "" else None


def file_size_bytes(path: Path) -> int | None:
    return path.stat().st_size if path.exists() else None


def mb(value: int | float | None) -> float | None:
    return None if value is None else float(value) / (1024.0 * 1024.0)


def fmt_float(value: Any, places: int = 6) -> str:
    if value is None or value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return ""
    return f"{number:.{places}f}"


def run_timed(cmd: list[str], cwd: Path, env: dict[str, str]) -> tuple[float, str]:
    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed with exit code {proc.returncode}: {' '.join(cmd)}\n{proc.stdout}"
        )
    return elapsed, proc.stdout


def generator_cmd(spec: DatasetSpec, root: Path, prefix: Path) -> list[str]:
    cmd = [
        "python",
        str(REPO_ROOT / "script" / "generate_default_neighborhood_plans.py"),
        "--data-dir",
        str(data_dir(root, spec)),
        "--dataset",
        spec.dataset,
        "--avg-bits",
        b_label(spec.avg_bits),
        "--min-positive-bits",
        str(spec.min_positive_bits),
        "--min-zero-tail-dim",
        str(spec.min_zero_tail_dim),
        "--max-segments",
        str(spec.max_segments),
        "--filter-infeasible",
        "--output-prefix",
        str(prefix),
    ]
    if spec.exclude_nonfinal_1bit:
        cmd.insert(-2, "--exclude-nonfinal-1bit")
    return cmd


def scorer_cmd(
    spec: DatasetSpec,
    root: Path,
    candidate_csv: Path,
    default_plan: str,
    prefix: Path,
) -> list[str]:
    cmd = [
        "python",
        str(REPO_ROOT / "script" / "score_default_neighborhood_plans.py"),
        "--candidate-csv",
        str(candidate_csv),
        "--data-dir",
        str(data_dir(root, spec)),
        "--dataset",
        spec.dataset,
        "--k",
        str(spec.k),
        "--avg-bits",
        b_label(spec.avg_bits),
        "--default-plan",
        default_plan,
        "--boundary-rank",
        str(spec.boundary_rank),
        "--neighbor-window",
        str(spec.neighbor_window),
        "--pairs-per-anchor",
        str(spec.pairs_per_anchor),
        "--anchors-per-cluster",
        str(spec.anchors_per_cluster),
        "--max-anchors",
        str(spec.max_anchors),
        "--max-pairs",
        str(spec.max_pairs),
        "--max-candidates-per-anchor",
        str(spec.max_candidates_per_anchor),
        "--pair-seed",
        str(spec.pair_seed),
        "--min-positive-bits",
        str(spec.min_positive_bits),
        "--min-zero-tail-dim",
        str(spec.min_zero_tail_dim),
        "--max-segments",
        str(spec.max_segments),
        "--filter-infeasible",
        "--output-prefix",
        str(prefix),
    ]
    if spec.exclude_nonfinal_1bit:
        cmd.insert(-2, "--exclude-nonfinal-1bit")
    return cmd


def default_plan_from_candidate_csv(candidate_csv: Path) -> str:
    rows = read_csv(candidate_csv)
    for row in rows:
        if bool_from_csv(row.get("is_default", "")):
            return row["seg_plan"]
    summary_path = candidate_csv.with_suffix(".summary.json")
    if summary_path.exists():
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return str(data.get("default_plan", ""))
    return ""


def measure_planner_runtime(
    spec: DatasetSpec,
    root: Path,
    timing_dir: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    timing_dir.mkdir(parents=True, exist_ok=True)
    gen_prefix = timing_dir / f"{spec.name}_candidate"
    scorer_prefix = timing_dir / f"{spec.name}_scored"

    gen_elapsed, _ = run_timed(generator_cmd(spec, root, gen_prefix), REPO_ROOT, env)
    candidate_csv = gen_prefix.with_suffix(".csv")
    candidate_rows = read_csv(candidate_csv)
    non_default_count = sum(not bool_from_csv(row.get("is_default", "")) for row in candidate_rows)
    default_plan = default_plan_from_candidate_csv(candidate_csv)

    out: dict[str, Any] = {
        "generator_runtime_s": gen_elapsed,
        "timed_candidate_csv": str(candidate_csv),
        "timed_candidate_count": len(candidate_rows),
        "timed_non_default_candidate_count": non_default_count,
        "timed_scorer_prefix": str(scorer_prefix),
    }
    if non_default_count == 0:
        out["scorer_runtime_s"] = None
        out["planner_runtime_s"] = gen_elapsed
        out["scorer_skipped_reason"] = "generator_produced_no_non_default_candidates"
        return out

    scorer_elapsed, _ = run_timed(
        scorer_cmd(spec, root, candidate_csv, default_plan, scorer_prefix),
        REPO_ROOT,
        env,
    )
    out["scorer_runtime_s"] = scorer_elapsed
    out["planner_runtime_s"] = gen_elapsed + scorer_elapsed
    out["timed_unique_csv"] = str(scorer_prefix.with_suffix(".unique.csv"))
    out["timed_summary_json"] = str(scorer_prefix.with_suffix(".summary.json"))
    return out


def qps_cmd(spec: DatasetSpec, nprobe: int, plan: str = "") -> list[str]:
    cmd = [
        str(REPO_ROOT / "bin" / "test_qps"),
        "-dataset",
        spec.dataset,
        "-K",
        str(spec.k),
        "-B",
        b_label(spec.avg_bits),
        "-enable_PCA=true",
        "-searcher_dist_type=0",
        f"-searcher_safe_block_min_mode={SAFE_BLOCK_MIN_MODE}",
        f"-qps_topk={spec.topk}",
        f"-fix_nprobe={nprobe}",
        "-fix_thread=24",
        "-logtostderr=1",
    ]
    if plan:
        cmd.insert(-1, f"-seg_plan={plan}")
    return cmd


def ensure_qps(
    spec: DatasetSpec,
    root: Path,
    nprobe: int,
    plan: str,
    env: dict[str, str],
    measure: bool,
) -> dict[str, Any] | None:
    path = qps_path(root, spec, nprobe, plan)
    value = read_qps(path)
    if value is not None or not measure:
        return value
    run_timed(qps_cmd(spec, nprobe, plan), root, env)
    return read_qps(path)


def load_scorer_summary(unique_csv: str) -> dict[str, Any]:
    if not unique_csv:
        return {}
    csv_path = Path(unique_csv)
    if csv_path.name.endswith(".unique.csv"):
        path = csv_path.with_name(csv_path.name.removesuffix(".unique.csv") + ".summary.json")
    else:
        path = csv_path.with_suffix(".summary.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_csv_rows(path: str) -> int | None:
    if not path:
        return None
    csv_path = Path(path)
    if not csv_path.exists():
        return None
    return len(read_csv(csv_path))


def selected_candidate(result: dict[str, Any]) -> dict[str, Any]:
    selected = result.get("selected") or []
    return dict(selected[0]) if selected else {}


def build_rows(
    matrix: dict[str, Any],
    root: Path,
    env: dict[str, str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    timing_by_run: dict[str, dict[str, Any]] = {}
    summary_rows: list[dict[str, Any]] = []
    qps_rows: list[dict[str, Any]] = []

    run_filter = set(args.runs or [])
    for result in matrix["results"]:
        run_name = result["spec"]["name"]
        if run_filter and run_name not in run_filter:
            continue
        spec = BUILTIN_SPECS[run_name]
        candidate = selected_candidate(result)
        candidate_plan = str(candidate.get("seg_plan", ""))
        scorer_summary = load_scorer_summary(result.get("unique_csv", ""))
        pair_summary = scorer_summary.get("pair_summary", {})

        if args.measure_planner_runtime:
            timing_by_run[run_name] = measure_planner_runtime(spec, root, args.timing_dir, env)
        timing = timing_by_run.get(run_name, {})

        candidate_rows = count_csv_rows(result.get("candidate_csv", ""))
        unique_rows = count_csv_rows(result.get("unique_csv", ""))
        non_default_candidate_rows = None
        if result.get("candidate_csv") and Path(result["candidate_csv"]).exists():
            rows = read_csv(Path(result["candidate_csv"]))
            non_default_candidate_rows = sum(
                not bool_from_csv(row.get("is_default", "")) for row in rows
            )

        default_index = index_path(root, spec, "")
        candidate_index = index_path(root, spec, candidate_plan) if candidate_plan else None
        default_size = file_size_bytes(default_index)
        candidate_size = file_size_bytes(candidate_index) if candidate_index else None
        default_index_time = read_index_time(root, spec, "")
        candidate_index_time = read_index_time(root, spec, candidate_plan) if candidate_plan else None

        qps_point_count = 0
        qps_ratio_values: list[float] = []
        measure_qps_for_run = bool(args.measure_qps_curve and candidate_plan)
        for nprobe in spec.compare_nprobes:
            default_qps = ensure_qps(spec, root, nprobe, "", env, measure_qps_for_run)
            candidate_qps = (
                ensure_qps(spec, root, nprobe, candidate_plan, env, measure_qps_for_run)
                if candidate_plan
                else None
            )
            if default_qps or candidate_qps:
                qps_point_count += 1
            qps_ratio = None
            if default_qps and candidate_qps and default_qps.get("qps", 0) > 0:
                qps_ratio = float(candidate_qps["qps"]) / float(default_qps["qps"])
                qps_ratio_values.append(qps_ratio)
            qps_rows.append(
                {
                    "run": run_name,
                    "dataset": spec.dataset,
                    "k": spec.k,
                    "avg_bits": spec.avg_bits,
                    "topk": spec.topk,
                    "nprobe": nprobe,
                    "default_plan": result.get("default_plan", ""),
                    "candidate_plan": candidate_plan,
                    "selection_reason": candidate.get("selection_reason", ""),
                    "default_qps": default_qps.get("qps", "") if default_qps else "",
                    "candidate_qps": candidate_qps.get("qps", "") if candidate_qps else "",
                    "qps_ratio_vs_default": qps_ratio if qps_ratio is not None else "",
                    "default_avg_tm_ms": default_qps.get("avg_tm_ms", "") if default_qps else "",
                    "candidate_avg_tm_ms": candidate_qps.get("avg_tm_ms", "") if candidate_qps else "",
                    "default_qps_recall": default_qps.get("recall", "") if default_qps else "",
                    "candidate_qps_recall": candidate_qps.get("recall", "") if candidate_qps else "",
                    "default_qps_output": default_qps.get("output", "") if default_qps else "",
                    "candidate_qps_output": candidate_qps.get("output", "") if candidate_qps else "",
                }
            )

        geometric_qps_ratio = None
        if qps_ratio_values:
            geometric_qps_ratio = math.exp(
                sum(math.log(value) for value in qps_ratio_values) / len(qps_ratio_values)
            )

        summary_rows.append(
            {
                "run": run_name,
                "dataset": spec.dataset,
                "k": spec.k,
                "avg_bits": spec.avg_bits,
                "topk": spec.topk,
                "default_plan": result.get("default_plan", ""),
                "candidate_plan": candidate_plan,
                "candidate_family": candidate.get("candidate_families", ""),
                "selection_reason": candidate.get("selection_reason", "no_candidate_selected"),
                "scorer_skipped_reason": result.get("scorer_skipped_reason", ""),
                "candidate_rows": candidate_rows,
                "non_default_candidate_rows": non_default_candidate_rows,
                "unique_plan_count": result.get("unique_plan_count", unique_rows),
                "scorer_unique_plan_count": scorer_summary.get("unique_plan_count", ""),
                "all_config_count": scorer_summary.get("all_config_count", ""),
                "selected_config_count": scorer_summary.get("selected_config_count", ""),
                "pair_count": pair_summary.get("sampled_pair_count", ""),
                "used_anchor_count": pair_summary.get("used_anchor_count", ""),
                "eligible_cluster_count": pair_summary.get("eligible_cluster_count", ""),
                "max_anchors": pair_summary.get("max_anchors", spec.max_anchors),
                "max_pairs": pair_summary.get("max_pairs", spec.max_pairs),
                "max_candidates_per_anchor": pair_summary.get(
                    "max_candidates_per_anchor", spec.max_candidates_per_anchor
                ),
                "generator_runtime_s": timing.get("generator_runtime_s", ""),
                "scorer_runtime_s": timing.get("scorer_runtime_s", ""),
                "planner_runtime_s": timing.get("planner_runtime_s", ""),
                "default_index_time_s": default_index_time,
                "candidate_index_time_s": candidate_index_time,
                "index_time_ratio_vs_default": (
                    candidate_index_time / default_index_time
                    if default_index_time and candidate_index_time
                    else ""
                ),
                "default_index_size_mb": mb(default_size),
                "candidate_index_size_mb": mb(candidate_size),
                "index_size_ratio_vs_default": (
                    candidate_size / default_size if default_size and candidate_size else ""
                ),
                "index_size_delta_mb": (
                    mb(candidate_size - default_size)
                    if default_size is not None and candidate_size is not None
                    else ""
                ),
                "qps_curve_points": qps_point_count,
                "qps_curve_geomean_ratio": geometric_qps_ratio,
                "default_index_path": str(default_index) if default_index.exists() else "",
                "candidate_index_path": (
                    str(candidate_index) if candidate_index and candidate_index.exists() else ""
                ),
                "timed_candidate_csv": timing.get("timed_candidate_csv", ""),
                "timed_summary_json": timing.get("timed_summary_json", ""),
            }
        )

    metadata = {
        "matrix_json": str(args.matrix_json),
        "root": str(root),
        "measure_planner_runtime": bool(args.measure_planner_runtime),
        "measure_qps_curve": bool(args.measure_qps_curve),
        "timing_dir": str(args.timing_dir),
        "runs": [row["run"] for row in summary_rows],
    }
    return summary_rows, qps_rows, metadata


def write_markdown(path: Path, summary_rows: list[dict[str, Any]], qps_rows: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# SAQ Fixed-Policy Overhead Evaluation")
    lines.append("")
    lines.append(f"Date: {DEFAULT_DATE.replace('_', '-')}")
    lines.append("")
    lines.append("This report evaluates the extra cost of the fixed-policy layer relative to SAQ default planning.")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("- The report uses the fixed-policy matrix artifact listed below.")
    lines.append("- Candidate/scorer runtime is measured only when `--measure-planner-runtime` is enabled.")
    lines.append("- QPS curve points are measured or reused across each run's validation nprobe grid.")
    lines.append("- Index build time comes from existing `*.index.csv` metadata emitted by `create_index`; index size comes from serialized `.index` files.")
    lines.append("")
    lines.append("```text")
    lines.append(str(metadata["matrix_json"]))
    lines.append("```")
    lines.append("")
    lines.append("## Planning And Index Overhead Summary")
    lines.append("")
    lines.append("| run | candidates | pairs | planner runtime s | default index s | selected index s | default MB | selected MB | qps curve geomean |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in summary_rows:
        lines.append(
            "| {run} | {candidates} | {pairs} | {planner} | {d_time} | {c_time} | {d_mb} | {c_mb} | {qps_geo} |".format(
                run=row["run"],
                candidates=row.get("candidate_rows", ""),
                pairs=row.get("pair_count", ""),
                planner=fmt_float(row.get("planner_runtime_s"), 3),
                d_time=fmt_float(row.get("default_index_time_s"), 3),
                c_time=fmt_float(row.get("candidate_index_time_s"), 3),
                d_mb=fmt_float(row.get("default_index_size_mb"), 1),
                c_mb=fmt_float(row.get("candidate_index_size_mb"), 1),
                qps_geo=fmt_float(row.get("qps_curve_geomean_ratio"), 4),
            )
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("The deployable overhead is the planner/scorer pass plus one final selected-index build. The larger research workflow that built and evaluated multiple candidates is not counted as the deployable method.")
    lines.append("")
    lines.append("If planner runtime is blank, the row was generated from existing artifacts without rerunning candidate generation and scoring. If a selected-index field is blank, the policy abstained or the selected index artifact is missing.")
    lines.append("")
    lines.append("## Output Tables")
    lines.append("")
    lines.append("```text")
    lines.append(f"{path.with_suffix('.summary.csv')}")
    lines.append(f"{path.with_suffix('.qps_curve.csv')}")
    lines.append(f"{path.with_suffix('.json')}")
    lines.append("```")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report fixed-policy overhead from validation artifacts.")
    parser.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX_JSON)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--run", action="append", dest="runs", choices=sorted(BUILTIN_SPECS))
    parser.add_argument("--measure-planner-runtime", action="store_true")
    parser.add_argument("--measure-qps-curve", action="store_true")
    parser.add_argument(
        "--timing-dir",
        type=Path,
        default=DEFAULT_ROOT / "reports" / f"fixed_policy_overhead_timing_{DEFAULT_DATE}",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path("docs") / f"saq_fixed_policy_overhead_evaluation_{DEFAULT_DATE}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.matrix_json.exists():
        raise FileNotFoundError(args.matrix_json)
    matrix = json.loads(args.matrix_json.read_text(encoding="utf-8"))
    env = os.environ.copy()
    deps = "/tmp/saq-deps/usr/lib64"
    env["LD_LIBRARY_PATH"] = deps + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")

    summary_rows, qps_rows, metadata = build_rows(matrix, args.root, env, args)

    prefix = args.output_prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_csv = prefix.with_suffix(".summary.csv")
    qps_csv = prefix.with_suffix(".qps_curve.csv")
    json_path = prefix.with_suffix(".json")
    md_path = prefix.with_suffix(".md")

    summary_fields = [
        "run",
        "dataset",
        "k",
        "avg_bits",
        "topk",
        "default_plan",
        "candidate_plan",
        "candidate_family",
        "selection_reason",
        "scorer_skipped_reason",
        "candidate_rows",
        "non_default_candidate_rows",
        "unique_plan_count",
        "scorer_unique_plan_count",
        "all_config_count",
        "selected_config_count",
        "pair_count",
        "used_anchor_count",
        "eligible_cluster_count",
        "max_anchors",
        "max_pairs",
        "max_candidates_per_anchor",
        "generator_runtime_s",
        "scorer_runtime_s",
        "planner_runtime_s",
        "default_index_time_s",
        "candidate_index_time_s",
        "index_time_ratio_vs_default",
        "default_index_size_mb",
        "candidate_index_size_mb",
        "index_size_ratio_vs_default",
        "index_size_delta_mb",
        "qps_curve_points",
        "qps_curve_geomean_ratio",
        "default_index_path",
        "candidate_index_path",
        "timed_candidate_csv",
        "timed_summary_json",
    ]
    qps_fields = [
        "run",
        "dataset",
        "k",
        "avg_bits",
        "topk",
        "nprobe",
        "default_plan",
        "candidate_plan",
        "selection_reason",
        "default_qps",
        "candidate_qps",
        "qps_ratio_vs_default",
        "default_avg_tm_ms",
        "candidate_avg_tm_ms",
        "default_qps_recall",
        "candidate_qps_recall",
        "default_qps_output",
        "candidate_qps_output",
    ]
    write_csv(summary_csv, summary_rows, summary_fields)
    write_csv(qps_csv, qps_rows, qps_fields)
    write_json(
        json_path,
        {
            "metadata": metadata,
            "specs": {name: asdict(BUILTIN_SPECS[name]) for name in metadata["runs"]},
            "summary_rows": summary_rows,
            "qps_rows": qps_rows,
        },
    )
    write_markdown(md_path, summary_rows, qps_rows, metadata)
    print(json.dumps({"summary_csv": str(summary_csv), "qps_csv": str(qps_csv), "json": str(json_path), "md": str(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
