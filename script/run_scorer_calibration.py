#!/usr/bin/env python3
"""Evaluate whether cheaper data-only scorer settings preserve policy decisions."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from run_default_neighborhood_cross_dataset import (
    BUILTIN_SPECS,
    REPO_ROOT,
    DatasetSpec,
    b_label,
    bool_from_csv,
    data_dir,
    read_csv,
    select_candidates,
    write_json,
)


DEFAULT_ROOT = Path("/tmp/saq-run")
DEFAULT_MATRIX_JSON = DEFAULT_ROOT / "reports" / "fixed_policy_matrix_validation_2026_07_07.json"
DEFAULT_OVERHEAD_SUMMARY_CSV = REPO_ROOT / "docs" / "saq_fixed_policy_overhead_evaluation_2026_07_07.summary.csv"
DEFAULT_DATE = "2026_07_07"

CALIBRATION_PRESETS: dict[str, dict[str, int]] = {
    "a256_p1": {"max_anchors": 256, "max_pairs": 256, "pairs_per_anchor": 1},
    "a512_p1": {"max_anchors": 512, "max_pairs": 512, "pairs_per_anchor": 1},
    "a1024_p2": {"max_anchors": 1024, "max_pairs": 2048, "pairs_per_anchor": 2},
    "a2048_p2": {"max_anchors": 2048, "max_pairs": 4096, "pairs_per_anchor": 2},
}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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


def scorer_cmd(
    spec: DatasetSpec,
    root: Path,
    candidate_csv: Path,
    default_plan: str,
    prefix: Path,
    preset: dict[str, int],
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
        str(preset["pairs_per_anchor"]),
        "--anchors-per-cluster",
        str(spec.anchors_per_cluster),
        "--max-anchors",
        str(preset["max_anchors"]),
        "--max-pairs",
        str(preset["max_pairs"]),
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


def load_summary(prefix: Path) -> dict[str, Any]:
    path = prefix.with_suffix(".summary.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def policy_decision(selection_reason: str, has_selected: bool) -> str:
    if not has_selected:
        return "abstain"
    if selection_reason in {"conservative_eligible", "frontier_like"}:
        return "promote"
    if selection_reason == "risky_fallback_best_score":
        return "reject"
    return "unknown"


def float_or_none(value: Any) -> float | None:
    if value in {"", None}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def restore_reused_runtime(rows: list[dict[str, Any]], previous_rows: list[dict[str, Any]]) -> None:
    previous_by_key = {
        (row.get("run", ""), row.get("preset", "")): row
        for row in previous_rows
    }
    for row in rows:
        if row.get("scorer_runtime_s") not in {"", None}:
            continue
        previous = previous_by_key.get((row.get("run", ""), row.get("preset", "")))
        if previous and previous.get("scorer_runtime_s") not in {"", None}:
            row["scorer_runtime_s"] = previous["scorer_runtime_s"]


def add_reference_cost_ratios(rows: list[dict[str, Any]], reference_rows: list[dict[str, Any]]) -> None:
    reference_by_run = {row.get("run", ""): row for row in reference_rows}
    for row in rows:
        reference = reference_by_run.get(row.get("run", ""), {})
        reference_pairs = reference.get("pair_count", "")
        reference_runtime = reference.get("scorer_runtime_s", "")
        row["reference_pair_count"] = reference_pairs
        row["reference_scorer_runtime_s"] = reference_runtime

        current_pairs = float_or_none(row.get("pair_count"))
        base_pairs = float_or_none(reference_pairs)
        if current_pairs is not None and base_pairs and base_pairs > 0:
            row["pair_count_ratio_vs_reference"] = current_pairs / base_pairs
        else:
            row["pair_count_ratio_vs_reference"] = ""

        current_runtime = float_or_none(row.get("scorer_runtime_s"))
        base_runtime = float_or_none(reference_runtime)
        if current_runtime is not None and base_runtime and base_runtime > 0:
            row["scorer_runtime_ratio_vs_reference"] = current_runtime / base_runtime
        else:
            row["scorer_runtime_ratio_vs_reference"] = ""


def baseline_from_result(result: dict[str, Any]) -> dict[str, str]:
    selected = result.get("selected") or []
    if selected:
        row = selected[0]
        reason = str(row.get("selection_reason", ""))
        return {
            "baseline_plan": str(row.get("seg_plan", "")),
            "baseline_selection_reason": reason,
            "baseline_decision": policy_decision(reason, True),
        }
    return {
        "baseline_plan": "",
        "baseline_selection_reason": result.get("scorer_skipped_reason", "no_candidate_selected"),
        "baseline_decision": "abstain",
    }


def run_one(
    result: dict[str, Any],
    root: Path,
    output_dir: Path,
    preset_name: str,
    preset: dict[str, int],
    env: dict[str, str],
    force: bool,
    allow_risky_fallback: bool,
) -> dict[str, Any]:
    spec = BUILTIN_SPECS[result["spec"]["name"]]
    baseline = baseline_from_result(result)
    candidate_csv = Path(result.get("candidate_csv", ""))
    candidate_rows = read_csv(candidate_csv) if candidate_csv.exists() else []
    non_default_count = sum(not bool_from_csv(row.get("is_default", "")) for row in candidate_rows)

    out: dict[str, Any] = {
        "run": spec.name,
        "dataset": spec.dataset,
        "k": spec.k,
        "avg_bits": spec.avg_bits,
        "preset": preset_name,
        "max_anchors": preset["max_anchors"],
        "max_pairs": preset["max_pairs"],
        "pairs_per_anchor": preset["pairs_per_anchor"],
        "candidate_count": len(candidate_rows),
        "non_default_candidate_count": non_default_count,
        **baseline,
    }
    if non_default_count == 0:
        out.update(
            {
                "candidate_plan": "",
                "selection_reason": "no_candidate_selected",
                "decision": "abstain",
                "decision_matches_baseline": baseline["baseline_decision"] == "abstain",
                "plan_matches_baseline": baseline["baseline_plan"] == "",
                "scorer_runtime_s": 0.0,
                "pair_count": "",
                "used_anchor_count": "",
                "summary_json": "",
            }
        )
        return out

    prefix = output_dir / f"{spec.name}_{preset_name}"
    unique_csv = prefix.with_suffix(".unique.csv")
    if unique_csv.exists() and not force:
        runtime_s: float | str = ""
    else:
        elapsed, _ = run_timed(
            scorer_cmd(
                spec=spec,
                root=root,
                candidate_csv=candidate_csv,
                default_plan=str(result.get("default_plan", "")),
                prefix=prefix,
                preset=preset,
            ),
            REPO_ROOT,
            env,
        )
        runtime_s = elapsed

    rows = read_csv(unique_csv)
    selected = select_candidates(rows, 1, allow_risky_fallback)
    selected_row = selected[0] if selected else {}
    reason = str(selected_row.get("selection_reason", ""))
    decision = policy_decision(reason, bool(selected))
    summary = load_summary(prefix)
    pair_summary = summary.get("pair_summary", {})
    out.update(
        {
            "candidate_plan": selected_row.get("seg_plan", ""),
            "selection_reason": reason if selected else "no_candidate_selected",
            "decision": decision,
            "decision_matches_baseline": decision == baseline["baseline_decision"],
            "plan_matches_baseline": selected_row.get("seg_plan", "") == baseline["baseline_plan"],
            "selection_reason_matches_baseline": reason == baseline["baseline_selection_reason"],
            "scorer_runtime_s": runtime_s,
            "pair_count": pair_summary.get("sampled_pair_count", ""),
            "used_anchor_count": pair_summary.get("used_anchor_count", ""),
            "eligible_cluster_count": pair_summary.get("eligible_cluster_count", ""),
            "all_config_count": summary.get("all_config_count", ""),
            "unique_plan_count": summary.get("unique_plan_count", ""),
            "best_ranking_score": selected_row.get("best_ranking_score", ""),
            "best_recall_risk_score": selected_row.get("best_recall_risk_score", ""),
            "best_speed_proxy_ratio_vs_default": selected_row.get("best_speed_proxy_ratio_vs_default", ""),
            "summary_json": str(prefix.with_suffix(".summary.json")),
            "unique_csv": str(unique_csv),
        }
    )
    return out


def write_markdown(path: Path, rows: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# SAQ Fixed-Policy Scorer Calibration Evaluation")
    lines.append("")
    lines.append(f"Date: {DEFAULT_DATE.replace('_', '-')}")
    lines.append("")
    lines.append("This report evaluates whether cheaper data-only scorer sampling settings preserve the fixed-policy decisions.")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("- Candidate sets are fixed from the existing default-neighborhood matrix.")
    lines.append("- No index is built and no held-out query labels are used for selection.")
    lines.append("- `risky_fallback_best_score` is mapped to `reject`, following the fixed-policy interpretation.")
    lines.append("")
    lines.append("## Decision Stability")
    lines.append("")
    lines.append("| preset | runs | decision matches | plan matches | total runtime s |")
    lines.append("|---|---:|---:|---:|---:|")
    for preset in metadata["presets"]:
        subset = [row for row in rows if row["preset"] == preset]
        measured_runtime = sum(float(row["scorer_runtime_s"] or 0) for row in subset)
        lines.append(
            "| {preset} | {runs} | {decision_matches}/{runs} | {plan_matches}/{runs} | {runtime:.3f} |".format(
                preset=preset,
                runs=len(subset),
                decision_matches=sum(str(row["decision_matches_baseline"]) == "True" for row in subset),
                plan_matches=sum(str(row["plan_matches_baseline"]) == "True" for row in subset),
                runtime=measured_runtime,
            )
        )
    lines.append("")
    lines.append("## Per-Run Results")
    lines.append("")
    lines.append("| run | preset | decision | baseline | selected plan | plan match | pairs | pair ratio | runtime s | runtime ratio |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|")
    for row in rows:
        pair_ratio = row.get("pair_count_ratio_vs_reference", "")
        runtime_ratio = row.get("scorer_runtime_ratio_vs_reference", "")
        lines.append(
            "| {run} | {preset} | {decision} | {baseline} | `{plan}` | {plan_match} | {pairs} | {pair_ratio} | {runtime} | {runtime_ratio} |".format(
                run=row["run"],
                preset=row["preset"],
                decision=row["decision"],
                baseline=row["baseline_decision"],
                plan=row.get("candidate_plan", ""),
                plan_match=row["plan_matches_baseline"],
                pairs=row.get("pair_count", ""),
                pair_ratio=f"{float(pair_ratio):.3f}" if pair_ratio not in {"", None} else "",
                runtime=f"{float(row['scorer_runtime_s']):.3f}" if row.get("scorer_runtime_s") not in {"", None} else "",
                runtime_ratio=f"{float(runtime_ratio):.3f}" if runtime_ratio not in {"", None} else "",
            )
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("A useful cheap scorer should preserve the promote/reject/abstain decision and preferably the selected plan. If decision stability fails, the sampling setting is too aggressive for the current policy.")
    lines.append("")
    lines.append("The current stable calibration point is `a1024_p2`: it preserves every fixed-policy decision and selected plan in the checked matrix. Smaller representative settings can preserve the decision while changing the GIST B=4 selected plan, so they are not stable enough for exact-plan reproduction.")
    lines.append("")
    lines.append("Pair-count reduction alone does not fully solve scorer overhead. In the full matrix, `a1024_p2` reduces GIST sampling from 14,740 pairs to 2,048 pairs, but scorer runtime remains close to the full scorer. This indicates that the next cost-reduction target should be cached residual/tail features or a smaller scoring grid, not only fewer sampled pairs.")
    lines.append("")
    lines.append("## Output Tables")
    lines.append("")
    lines.append("```text")
    lines.append(str(path.with_suffix(".csv")))
    lines.append(str(path.with_suffix(".json")))
    lines.append("```")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scorer-cost calibration experiments.")
    parser.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX_JSON)
    parser.add_argument("--overhead-summary-csv", type=Path, default=DEFAULT_OVERHEAD_SUMMARY_CSV)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--run", action="append", dest="runs", choices=sorted(BUILTIN_SPECS))
    parser.add_argument("--preset", action="append", dest="presets", choices=sorted(CALIBRATION_PRESETS))
    parser.add_argument("--allow-risky-fallback", action="store_true", default=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=DEFAULT_ROOT / "reports" / f"fixed_policy_scorer_calibration_{DEFAULT_DATE}",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path("docs") / f"saq_fixed_policy_scorer_calibration_{DEFAULT_DATE}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matrix = json.loads(args.matrix_json.read_text(encoding="utf-8"))
    run_filter = set(args.runs or [])
    presets = args.presets or ["a256_p1", "a512_p1", "a1024_p2"]

    env = os.environ.copy()
    deps = "/tmp/saq-deps/usr/lib64"
    env["LD_LIBRARY_PATH"] = deps + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")

    args.work_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for result in matrix["results"]:
        run_name = result["spec"]["name"]
        if run_filter and run_name not in run_filter:
            continue
        for preset_name in presets:
            rows.append(
                run_one(
                    result=result,
                    root=args.root,
                    output_dir=args.work_dir,
                    preset_name=preset_name,
                    preset=CALIBRATION_PRESETS[preset_name],
                    env=env,
                    force=args.force,
                    allow_risky_fallback=bool(args.allow_risky_fallback),
                )
            )

    prefix = args.output_prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = prefix.with_suffix(".csv")
    json_path = prefix.with_suffix(".json")
    md_path = prefix.with_suffix(".md")
    previous_rows = read_csv(csv_path) if csv_path.exists() and not args.force else []
    restore_reused_runtime(rows, previous_rows)
    reference_rows = read_csv(args.overhead_summary_csv) if args.overhead_summary_csv.exists() else []
    add_reference_cost_ratios(rows, reference_rows)
    fields = [
        "run",
        "dataset",
        "k",
        "avg_bits",
        "preset",
        "max_anchors",
        "max_pairs",
        "pairs_per_anchor",
        "candidate_count",
        "non_default_candidate_count",
        "baseline_decision",
        "baseline_plan",
        "baseline_selection_reason",
        "decision",
        "candidate_plan",
        "selection_reason",
        "decision_matches_baseline",
        "plan_matches_baseline",
        "selection_reason_matches_baseline",
        "scorer_runtime_s",
        "pair_count",
        "reference_pair_count",
        "pair_count_ratio_vs_reference",
        "used_anchor_count",
        "eligible_cluster_count",
        "all_config_count",
        "unique_plan_count",
        "best_ranking_score",
        "best_recall_risk_score",
        "best_speed_proxy_ratio_vs_default",
        "reference_scorer_runtime_s",
        "scorer_runtime_ratio_vs_reference",
        "summary_json",
        "unique_csv",
    ]
    write_csv(csv_path, rows, fields)
    metadata = {
        "matrix_json": str(args.matrix_json),
        "overhead_summary_csv": str(args.overhead_summary_csv),
        "root": str(args.root),
        "work_dir": str(args.work_dir),
        "runs": sorted({row["run"] for row in rows}),
        "presets": presets,
        "allow_risky_fallback": bool(args.allow_risky_fallback),
    }
    write_json(json_path, {"metadata": metadata, "rows": rows})
    write_markdown(md_path, rows, metadata)
    print(json.dumps({"csv": str(csv_path), "json": str(json_path), "md": str(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
