#!/usr/bin/env python3
"""Review fixed-policy matrix artifact dependencies without running experiments."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from run_default_neighborhood_cross_dataset import (
    BUILTIN_SPECS,
    DatasetSpec,
    index_path,
    plan_label,
    qps_path,
    report_prefix,
    scorer_artifact_suffix,
)
from run_fixed_policy_matrix import MATRIX_RUNS, SCAN_BITS, SCAN_DATASETS, default_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPECTED_CSV = REPO_ROOT / "docs" / "saq_fixed_policy_clean_validation_table_2026_07_07.csv"


@dataclass(frozen=True)
class Artifact:
    group: str
    role: str
    path: str
    exists: bool
    producer: str
    note: str


def compact_bool(value: bool) -> str:
    return "yes" if value else "no"


def read_expected_plans(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            run = row.get("run", "")
            if not run:
                continue
            rows[run] = row.get("selected_or_tested_plan", "")
    return rows


def add_artifact(
    artifacts: list[Artifact],
    group: str,
    role: str,
    path: Path,
    producer: str,
    note: str,
) -> None:
    artifacts.append(
        Artifact(
            group=group,
            role=role,
            path=str(path),
            exists=path.exists(),
            producer=producer,
            note=note,
        )
    )


def dataset_inputs(root: Path, spec: DatasetSpec) -> Iterable[tuple[str, Path, str]]:
    base = root / "data" / spec.dataset
    dataset = spec.dataset
    yield "base PCA vectors", base / f"{dataset}_base_pca.fvecs", "required before scorer, indexing, compare, and QPS"
    yield "PCA variance", base / f"{dataset}_base_pca.vars.fvecs", "required before applicability scan, generator, and scorer"
    yield "IVF centroids", base / f"{dataset}_centroid_{spec.k}_pca.fvecs", "required before scorer and index build"
    yield "IVF cluster ids", base / f"{dataset}_cluster_id_{spec.k}.ivecs", "required before scorer and index build"
    yield "query PCA vectors", base / f"{dataset}_query_pca.fvecs", "required before compare and QPS evaluation"
    yield "groundtruth", base / f"{dataset}_groundtruth.ivecs", "required before compare and QPS evaluation"


def candidate_artifacts(root: Path, spec: DatasetSpec, artifact_date: str) -> Iterable[tuple[str, Path]]:
    prefix = report_prefix(root, spec, artifact_date, "default_neighborhood_auto")
    yield "candidate CSV", prefix.with_suffix(".csv")
    yield "candidate summary JSON", prefix.with_suffix(".summary.json")


def scorer_artifacts(root: Path, spec: DatasetSpec, artifact_date: str, scorer_suffix: str) -> Iterable[tuple[str, Path]]:
    prefix = report_prefix(root, spec, artifact_date, scorer_suffix)
    yield "scorer config CSV", prefix.with_suffix(".csv")
    yield "scorer unique CSV", prefix.with_suffix(".unique.csv")
    yield "scorer roles CSV", prefix.with_suffix(".roles.csv")
    yield "scorer pairs CSV", prefix.with_suffix(".pairs.csv")
    yield "scorer risk CSV", prefix.with_suffix(".risk.csv")
    yield "scorer summary JSON", prefix.with_suffix(".summary.json")


def compare_artifacts(root: Path, spec: DatasetSpec, plan: str, artifact_date: str) -> Iterable[tuple[str, Path]]:
    label = plan_label(plan)
    for nprobe in spec.compare_nprobes:
        yield (
            f"compare np{nprobe}",
            root
            / "reports"
            / f"{spec.name}_{label}_compare_np{nprobe}_top{spec.topk}_{artifact_date}.csv",
        )


def collect_artifacts(args: argparse.Namespace) -> list[Artifact]:
    root: Path = args.root
    artifact_date = args.artifact_date or args.date
    expected_plans = read_expected_plans(args.expected_csv)

    class ScorerArgs:
        scorer_grid_preset = "endpoints" if args.use_cost_reduced_scorer else "full"
        feature_cache_dir = (
            args.feature_cache_dir
            if args.feature_cache_dir is not None
            else (
                root / "reports" / f"fixed_policy_scorer_feature_cache_{artifact_date}"
                if args.use_cost_reduced_scorer
                else None
            )
        )

    scorer_suffix = scorer_artifact_suffix(ScorerArgs)
    paths = default_paths(root, args.date)
    artifacts: list[Artifact] = []

    for binary in ("create_index", "compare_search_results", "test_qps"):
        add_artifact(
            artifacts,
            "build",
            f"binary:{binary}",
            REPO_ROOT / "bin" / binary,
            "cmake --build build -j",
            "required before full safe-search evaluation",
        )

    for dataset in SCAN_DATASETS:
        add_artifact(
            artifacts,
            "input",
            f"{dataset}:PCA variance for scan",
            root / "data" / dataset / f"{dataset}_base_pca.vars.fvecs",
            "external dataset/PCA/IVF preparation",
            "fixed-policy runner cannot regenerate dataset artifacts",
        )

    seen_dataset_inputs: set[tuple[str, int]] = set()
    for run in MATRIX_RUNS:
        spec = BUILTIN_SPECS[run]
        for role, path in candidate_artifacts(root, spec, artifact_date):
            add_artifact(
                artifacts,
                "runner-generated",
                f"{run}:{role}",
                path,
                "generate_default_neighborhood_plans.py",
                "generated by run_default_neighborhood_cross_dataset.py unless reused",
            )

        plan = expected_plans.get(run, "")
        if plan:
            key = (spec.dataset, spec.k)
            if key not in seen_dataset_inputs:
                seen_dataset_inputs.add(key)
                for role, path, note in dataset_inputs(root, spec):
                    add_artifact(
                        artifacts,
                        "input",
                        f"{spec.dataset} K{spec.k}:{role}",
                        path,
                        "external dataset/PCA/IVF preparation",
                        note,
                    )

            for role, path in scorer_artifacts(root, spec, artifact_date, scorer_suffix):
                add_artifact(
                    artifacts,
                    "runner-generated",
                    f"{run}:{role}",
                    path,
                    "score_default_neighborhood_plans.py",
                    "generated by scorer unless reused; feature cache may reduce repeated computation",
                )

            add_artifact(
                artifacts,
                "runner-generated",
                f"{run}:default index",
                index_path(root, spec, ""),
                "bin/create_index",
                "generated by evaluation stage if missing",
            )
            add_artifact(
                artifacts,
                "runner-generated",
                f"{run}:selected custom index",
                index_path(root, spec, plan),
                "bin/create_index -seg_plan",
                "generated by evaluation stage if missing",
            )
            for role, path in compare_artifacts(root, spec, plan, artifact_date):
                add_artifact(
                    artifacts,
                    "runner-generated",
                    f"{run}:{role}",
                    path,
                    "bin/compare_search_results",
                    "generated by evaluation stage if missing; must use safe block-min mode 2",
                )
            add_artifact(
                artifacts,
                "runner-generated",
                f"{run}:default QPS",
                qps_path(root, spec, ""),
                "bin/test_qps",
                "generated by evaluation stage if missing; must use safe block-min mode 2",
            )
            add_artifact(
                artifacts,
                "runner-generated",
                f"{run}:selected custom QPS",
                qps_path(root, spec, plan),
                "bin/test_qps -seg_plan",
                "generated by evaluation stage if missing; must use safe block-min mode 2",
            )

    if ScorerArgs.feature_cache_dir is not None:
        add_artifact(
            artifacts,
            "cache",
            "cost-reduced scorer feature-cache directory",
            ScorerArgs.feature_cache_dir,
            "score_default_neighborhood_plans.py --feature-cache-dir",
            "optional but useful; if absent, scorer recomputes and writes cache features",
        )

    add_artifact(
        artifacts,
        "report",
        "applicability CSV",
        paths["applicability_prefix"].with_suffix(".csv"),
        "scan_default_neighborhood_applicability.py",
        "input to report_fixed_policy_validation.py",
    )
    add_artifact(
        artifacts,
        "report",
        "matrix summary CSV",
        paths["validation_prefix"].with_suffix(".csv"),
        "run_default_neighborhood_cross_dataset.py",
        "input to report_fixed_policy_validation.py",
    )
    add_artifact(
        artifacts,
        "report",
        "clean report Markdown",
        paths["report_prefix"].with_suffix(".md"),
        "report_fixed_policy_validation.py",
        "generated report output",
    )
    add_artifact(
        artifacts,
        "report",
        "matrix manifest JSON",
        paths["manifest"],
        "run_fixed_policy_matrix.py",
        "records runner commands and output paths",
    )
    return artifacts


def write_text_report(artifacts: list[Artifact], args: argparse.Namespace) -> None:
    groups = ("build", "input", "runner-generated", "cache", "report")
    print("# Fixed-Policy Artifact Dependency Check")
    print()
    print(f"root: {args.root}")
    print(f"date: {args.date}")
    print(f"artifact_date: {args.artifact_date or args.date}")
    print(f"expected_csv: {args.expected_csv}")
    print(f"use_cost_reduced_scorer: {compact_bool(args.use_cost_reduced_scorer)}")
    print()
    for group in groups:
        rows = [artifact for artifact in artifacts if artifact.group == group]
        if not rows:
            continue
        present = sum(artifact.exists for artifact in rows)
        print(f"## {group} ({present}/{len(rows)} present)")
        for artifact in rows:
            status = "OK" if artifact.exists else "MISSING"
            print(f"- [{status}] {artifact.role}")
            print(f"  path: {artifact.path}")
            print(f"  producer: {artifact.producer}")
            print(f"  note: {artifact.note}")
        print()


def write_json_report(artifacts: list[Artifact], path: Path, args: argparse.Namespace) -> None:
    payload = {
        "root": str(args.root),
        "date": args.date,
        "artifact_date": args.artifact_date or args.date,
        "expected_csv": str(args.expected_csv),
        "use_cost_reduced_scorer": bool(args.use_cost_reduced_scorer),
        "artifacts": [asdict(artifact) for artifact in artifacts],
        "counts": {
            group: {
                "present": sum(artifact.exists for artifact in artifacts if artifact.group == group),
                "total": sum(1 for artifact in artifacts if artifact.group == group),
            }
            for group in sorted({artifact.group for artifact in artifacts})
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review fixed-policy matrix artifacts.")
    parser.add_argument("--root", type=Path, default=Path("/tmp/saq-run"))
    parser.add_argument("--date", default="2026_07_08_runner_cost_reduced_eval")
    parser.add_argument("--artifact-date", default=None)
    parser.add_argument("--expected-csv", type=Path, default=DEFAULT_EXPECTED_CSV)
    parser.add_argument("--use-cost-reduced-scorer", action="store_true")
    parser.add_argument("--feature-cache-dir", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.expected_csv.exists():
        raise FileNotFoundError(f"missing expected CSV: {args.expected_csv}")
    artifacts = collect_artifacts(args)
    write_text_report(artifacts, args)
    if args.output_json is not None:
        write_json_report(artifacts, args.output_json, args)
        print(f"Wrote JSON: {args.output_json}")
    missing_inputs = [artifact for artifact in artifacts if artifact.group in {"build", "input"} and not artifact.exists]
    return 1 if missing_inputs else 0


if __name__ == "__main__":
    raise SystemExit(main())
