#!/usr/bin/env python3
"""Run the fixed-policy validation matrix end to end.

This is a thin orchestration layer around the existing default-neighborhood
drivers:

1. scan default-plan applicability for the matrix datasets;
2. run candidate generation, data-only scoring, and optional safe-searcher
   evaluation for the fixed matrix;
3. rebuild the clean fixed-policy validation report from the matrix summary.

Risky fallback is exposed only as reject diagnostics. It is not a promotion
role in the final fixed-policy report.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path("/tmp/saq-run")
DEFAULT_DATE = "2026_07_07"

MATRIX_RUNS = (
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

SCAN_DATASETS = (
    "gist_full",
    "cifar60k",
    "deep1M_sample100k",
    "audio",
    "word2vec_sample100k",
)

SCAN_BITS = ("3", "4", "5")


def with_ld_library_path(env: dict[str, str]) -> dict[str, str]:
    out = dict(env)
    deps = "/tmp/saq-deps/usr/lib64"
    out["LD_LIBRARY_PATH"] = deps + (":" + out["LD_LIBRARY_PATH"] if out.get("LD_LIBRARY_PATH") else "")
    return out


def run_command(cmd: list[str], *, env: dict[str, str], dry_run: bool) -> None:
    print("RUN", " ".join(cmd), flush=True)
    if dry_run:
        return
    subprocess.run(cmd, cwd=REPO_ROOT, env=env, check=True)


def default_paths(root: Path, date: str) -> dict[str, Path]:
    reports = root / "reports"
    return {
        "applicability_prefix": reports / f"fixed_policy_applicability_scan_{date}",
        "validation_prefix": reports / f"fixed_policy_matrix_validation_{date}",
        "report_prefix": reports / f"fixed_policy_validation_matrix_{date}",
        "manifest": reports / f"fixed_policy_matrix_{date}.manifest.json",
    }


def build_scan_cmd(args: argparse.Namespace, applicability_prefix: Path) -> list[str]:
    cmd = [
        "python",
        str(REPO_ROOT / "script" / "scan_default_neighborhood_applicability.py"),
        "--data-root",
        str(args.root / "data"),
    ]
    for dataset in SCAN_DATASETS:
        cmd.extend(["--dataset", dataset])
    cmd.append("--bits")
    cmd.extend(SCAN_BITS)
    cmd.extend(["--date", args.date, "--output-prefix", str(applicability_prefix)])
    return cmd


def build_validation_cmd(
    args: argparse.Namespace, validation_prefix: Path, artifact_date: str
) -> list[str]:
    cmd = [
        "python",
        str(REPO_ROOT / "script" / "run_default_neighborhood_cross_dataset.py"),
        "--root",
        str(args.root),
        "--date",
        artifact_date,
        "--max-eval-per-run",
        str(args.max_eval_per_run),
        "--output-prefix",
        str(validation_prefix),
    ]
    for run in MATRIX_RUNS:
        cmd.extend(["--run", run])
    if args.evaluate:
        cmd.append("--evaluate")
    if args.include_reject_diagnostics:
        cmd.append("--allow-risky-fallback")
    if args.use_cost_reduced_scorer:
        cmd.append("--use-cost-reduced-scorer")
    if args.scorer_grid_preset:
        cmd.extend(["--scorer-grid-preset", args.scorer_grid_preset])
    if args.feature_cache_dir:
        cmd.extend(["--feature-cache-dir", str(args.feature_cache_dir)])
    if args.force:
        cmd.append("--force")
    if args.force_build:
        cmd.append("--force-build")
    if args.force_eval:
        cmd.append("--force-eval")
    return cmd


def build_report_cmd(
    args: argparse.Namespace,
    summary_csv: Path,
    applicability_csv: Path,
    report_prefix: Path,
) -> list[str]:
    cmd = [
        "python",
        str(REPO_ROOT / "script" / "report_fixed_policy_validation.py"),
        "--root",
        str(args.root),
        "--date",
        args.date,
        "--summary-csv",
        str(summary_csv),
        "--applicability-csv",
        str(applicability_csv),
        "--output-prefix",
        str(report_prefix),
    ]
    if args.expected_csv:
        cmd.extend(
            [
                "--expected-csv",
                str(args.expected_csv),
                "--compare-ignore-field",
                "source_report",
            ]
        )
    return cmd


def write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the fixed-policy validation matrix.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--date", default=DEFAULT_DATE, help="Date label for matrix summary/report outputs.")
    parser.add_argument(
        "--artifact-date",
        default=None,
        help="Date label for reusable generator/scorer/compare artifacts. Defaults to --date.",
    )
    parser.add_argument(
        "--evaluate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Build/evaluate selected candidates with the safe searcher.",
    )
    parser.add_argument(
        "--include-reject-diagnostics",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Evaluate risky fallback only as reject diagnostics, never as promotion.",
    )
    parser.add_argument("--max-eval-per-run", type=int, default=1)
    parser.add_argument(
        "--use-cost-reduced-scorer",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use the validated endpoint-grid scorer with query-unaware feature caching in the validation stage.",
    )
    parser.add_argument(
        "--scorer-grid-preset",
        choices=("full", "endpoints"),
        default="full",
        help="Scorer grid preset passed to run_default_neighborhood_cross_dataset.py.",
    )
    parser.add_argument(
        "--feature-cache-dir",
        type=Path,
        default=None,
        help="Optional feature-cache directory passed to run_default_neighborhood_cross_dataset.py.",
    )
    parser.add_argument("--force", action="store_true", help="Rerun candidate generation and scoring.")
    parser.add_argument("--force-build", action="store_true", help="Rebuild custom indexes.")
    parser.add_argument("--force-eval", action="store_true", help="Rerun compare/QPS measurements.")
    parser.add_argument("--skip-scan", action="store_true", help="Reuse an existing applicability CSV.")
    parser.add_argument("--skip-validation", action="store_true", help="Reuse an existing matrix summary CSV.")
    parser.add_argument("--skip-report", action="store_true", help="Do not rebuild the clean report outputs.")
    parser.add_argument("--applicability-csv", type=Path, default=None)
    parser.add_argument("--summary-csv", type=Path, default=None)
    parser.add_argument("--expected-csv", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_date = args.artifact_date or args.date
    if args.use_cost_reduced_scorer:
        if args.scorer_grid_preset == "full":
            args.scorer_grid_preset = "endpoints"
        if args.feature_cache_dir is None:
            args.feature_cache_dir = (
                args.root / "reports" / f"fixed_policy_scorer_feature_cache_{artifact_date}"
            )
    paths = default_paths(args.root, args.date)
    applicability_csv = args.applicability_csv or paths["applicability_prefix"].with_suffix(".csv")
    summary_csv = args.summary_csv or paths["validation_prefix"].with_suffix(".csv")
    summary_json = paths["validation_prefix"].with_suffix(".json")
    report_csv = paths["report_prefix"].with_suffix(".csv")
    report_md = paths["report_prefix"].with_suffix(".md")
    report_json = paths["report_prefix"].with_suffix(".json")

    env = with_ld_library_path(os.environ)
    commands: list[list[str]] = []

    if not args.skip_scan:
        commands.append(build_scan_cmd(args, paths["applicability_prefix"]))
    if not args.skip_validation:
        commands.append(build_validation_cmd(args, paths["validation_prefix"], artifact_date))
    if not args.skip_report:
        commands.append(build_report_cmd(args, summary_csv, applicability_csv, paths["report_prefix"]))

    manifest = {
        "date": args.date,
        "artifact_date": artifact_date,
        "root": str(args.root),
        "runs": list(MATRIX_RUNS),
        "scan_datasets": list(SCAN_DATASETS),
        "scan_bits": list(SCAN_BITS),
        "evaluate": bool(args.evaluate),
        "include_reject_diagnostics": bool(args.include_reject_diagnostics),
        "max_eval_per_run": int(args.max_eval_per_run),
        "use_cost_reduced_scorer": bool(args.use_cost_reduced_scorer),
        "scorer_grid_preset": args.scorer_grid_preset,
        "feature_cache_dir": str(args.feature_cache_dir) if args.feature_cache_dir else "",
        "outputs": {
            "applicability_csv": str(applicability_csv),
            "summary_csv": str(summary_csv),
            "summary_json": str(summary_json),
            "report_csv": str(report_csv),
            "report_md": str(report_md),
            "report_json": str(report_json),
        },
        "commands": commands,
        "dry_run": bool(args.dry_run),
    }

    for cmd in commands:
        run_command(cmd, env=env, dry_run=args.dry_run)

    write_manifest(paths["manifest"], manifest)
    print(json.dumps({"manifest": str(paths["manifest"]), "outputs": manifest["outputs"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
