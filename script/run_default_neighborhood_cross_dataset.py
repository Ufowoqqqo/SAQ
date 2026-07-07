#!/usr/bin/env python3
"""Run cross-dataset default-neighborhood SAQ validation.

The driver connects three pieces:

1. generate_default_neighborhood_plans.py creates a small candidate set near the
   SAQ default plan;
2. score_default_neighborhood_plans.py ranks those fixed candidates with the v3
   data-boundary and speed proxies;
3. optional build/evaluate measures only the selected top few candidates with
   the corrected safe searcher.

The default selection policy is conservative: evaluate non-default candidates
that pass the conservative role guard first.  A risky fallback can be enabled
explicitly to test whether the guard is over-conservative.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path("/tmp/saq-run")
DEFAULT_DATE = "2026_07_06"
SAFE_BLOCK_MIN_MODE = 2
ENDPOINT_SCORER_GRID_ARGS = {
    "boundary-global-blends": "0,0.4",
    "boundary-tail-alphas": "0,0.25",
    "boundary-pair-alphas": "0,2",
    "segment-penalty-scales": "0,0.04",
    "intra-segment-penalty-scales": "0",
    "inversion-penalty-scales": "0,0.05",
    "runtime-penalty-scales": "0",
    "speed-proxy-scales": "0",
}


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    dataset: str
    k: int
    avg_bits: int
    topk: int
    qps_nprobe: int
    compare_nprobes: tuple[int, ...]
    min_positive_bits: int = 2
    min_zero_tail_dim: int = 0
    max_segments: int = 6
    exclude_nonfinal_1bit: bool = True
    max_anchors: int = 4096
    max_pairs: int = 20000
    max_candidates_per_anchor: int = 2048
    boundary_rank: int = 100
    neighbor_window: int = 8
    pairs_per_anchor: int = 4
    anchors_per_cluster: int = 1
    pair_seed: int = 0


BUILTIN_SPECS: dict[str, DatasetSpec] = {
    "deep1M_sample100k_B4": DatasetSpec(
        name="deep1M_sample100k_B4",
        dataset="deep1M_sample100k",
        k=512,
        avg_bits=4,
        topk=100,
        qps_nprobe=200,
        compare_nprobes=(50, 100, 200, 400),
        min_positive_bits=1,
    ),
    "deep1M_sample100k_B5": DatasetSpec(
        name="deep1M_sample100k_B5",
        dataset="deep1M_sample100k",
        k=512,
        avg_bits=5,
        topk=100,
        qps_nprobe=200,
        compare_nprobes=(50, 100, 200, 400),
        min_positive_bits=2,
    ),
    "cifar60k_B3": DatasetSpec(
        name="cifar60k_B3",
        dataset="cifar60k",
        k=512,
        avg_bits=3,
        topk=10,
        qps_nprobe=200,
        compare_nprobes=(50, 100, 200, 400),
        min_positive_bits=2,
        min_zero_tail_dim=64,
    ),
    "cifar60k_B4": DatasetSpec(
        name="cifar60k_B4",
        dataset="cifar60k",
        k=512,
        avg_bits=4,
        topk=10,
        qps_nprobe=200,
        compare_nprobes=(50, 100, 200, 400),
        min_positive_bits=2,
        min_zero_tail_dim=64,
    ),
    "cifar60k_B5": DatasetSpec(
        name="cifar60k_B5",
        dataset="cifar60k",
        k=512,
        avg_bits=5,
        topk=10,
        qps_nprobe=200,
        compare_nprobes=(50, 100, 200, 400),
        min_positive_bits=2,
        min_zero_tail_dim=64,
    ),
    "gist_full_K4096_B3": DatasetSpec(
        name="gist_full_K4096_B3",
        dataset="gist_full",
        k=4096,
        avg_bits=3,
        topk=100,
        qps_nprobe=800,
        compare_nprobes=(50, 100, 200, 400, 800),
        min_positive_bits=2,
        min_zero_tail_dim=128,
    ),
    "gist_full_K4096_B4": DatasetSpec(
        name="gist_full_K4096_B4",
        dataset="gist_full",
        k=4096,
        avg_bits=4,
        topk=100,
        qps_nprobe=800,
        compare_nprobes=(50, 100, 200, 400, 800),
        min_positive_bits=2,
        min_zero_tail_dim=128,
    ),
    "gist_full_K4096_B5": DatasetSpec(
        name="gist_full_K4096_B5",
        dataset="gist_full",
        k=4096,
        avg_bits=5,
        topk=100,
        qps_nprobe=800,
        compare_nprobes=(50, 100, 200, 400, 800),
        min_positive_bits=2,
        min_zero_tail_dim=64,
    ),
    "audio_K4096_B4": DatasetSpec(
        name="audio_K4096_B4",
        dataset="audio",
        k=4096,
        avg_bits=4,
        topk=100,
        qps_nprobe=200,
        compare_nprobes=(50, 100, 200, 400),
        min_positive_bits=1,
    ),
    "word2vec_sample100k_B4": DatasetSpec(
        name="word2vec_sample100k_B4",
        dataset="word2vec_sample100k",
        k=512,
        avg_bits=4,
        topk=100,
        qps_nprobe=200,
        compare_nprobes=(50, 100, 200, 400),
        min_positive_bits=2,
    ),
}


def bool_from_csv(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def float_from_row(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value == "":
        return default
    return float(value)


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


def b_label(avg_bits: int | float) -> str:
    return f"{avg_bits:g}"


def args_stem(spec: DatasetSpec, plan: str = "") -> str:
    return (
        f"ivf{spec.k}_b{b_label(spec.avg_bits)}_caq_adj_seg"
        f"{compact_plan_for_path(plan)}_pca"
    )


def index_path(root: Path, spec: DatasetSpec, plan: str = "") -> Path:
    return root / "data" / spec.dataset / f"{args_stem(spec, plan)}.index"


def qps_path(root: Path, spec: DatasetSpec, plan: str = "") -> Path:
    topk_suffix = "" if spec.topk == 100 else f"_top{spec.topk}"
    return (
        root
        / "results"
        / "saq"
        / (
            f"qps_{spec.dataset}_{args_stem(spec, plan)}_th24_np{spec.qps_nprobe}"
            f"_sm4{topk_suffix}_safeblockminsimd.csv"
        )
    )


def data_dir(root: Path, spec: DatasetSpec) -> Path:
    return root / "data" / spec.dataset


def report_prefix(root: Path, spec: DatasetSpec, date: str, suffix: str) -> Path:
    return root / "reports" / f"{spec.name}_{suffix}_{date}"


def scorer_artifact_suffix(args: argparse.Namespace) -> str:
    parts = ["default_neighborhood_scored_auto"]
    if args.scorer_grid_preset == "endpoints":
        parts.append("grid_endpoints")
    if args.feature_cache_dir is not None:
        parts.append("cached_features")
    return "_".join(parts)


def scorer_extra_args(args: argparse.Namespace) -> list[str]:
    out: list[str] = []
    if args.scorer_grid_preset == "endpoints":
        for key, value in sorted(ENDPOINT_SCORER_GRID_ARGS.items()):
            out.extend([f"--{key}", value])
    if args.feature_cache_dir is not None:
        out.extend(["--feature-cache-dir", str(args.feature_cache_dir)])
    return out


def run_command(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    dry_run: bool = False,
) -> str:
    print("RUN", " ".join(cmd), flush=True)
    if dry_run:
        return ""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(proc.stdout, flush=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed with exit code {proc.returncode}: {' '.join(cmd)}")
    return proc.stdout


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def generator_summary_path(candidate_csv: Path) -> Path:
    return candidate_csv.with_suffix(".summary.json")


def read_generator_default_plan(candidate_csv: Path) -> str:
    summary_path = generator_summary_path(candidate_csv)
    if not summary_path.exists():
        return ""
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    return str(data.get("default_plan", ""))


def maybe_run_generator(
    spec: DatasetSpec,
    root: Path,
    date: str,
    env: dict[str, str],
    force: bool,
    dry_run: bool,
) -> Path:
    prefix = report_prefix(root, spec, date, "default_neighborhood_auto")
    csv_path = prefix.with_suffix(".csv")
    if csv_path.exists() and not force:
        print(f"REUSE {csv_path}", flush=True)
        return csv_path

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
    run_command(cmd, REPO_ROOT, env, dry_run)
    return csv_path


def maybe_run_scorer(
    spec: DatasetSpec,
    root: Path,
    date: str,
    candidate_csv: Path,
    default_plan: str,
    env: dict[str, str],
    args: argparse.Namespace,
    force: bool,
    dry_run: bool,
) -> Path:
    prefix = report_prefix(root, spec, date, scorer_artifact_suffix(args))
    unique_csv = prefix.with_suffix(".unique.csv")
    if unique_csv.exists() and not force:
        print(f"REUSE {unique_csv}", flush=True)
        return unique_csv

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
    cmd.extend(scorer_extra_args(args))
    run_command(cmd, REPO_ROOT, env, dry_run)
    return unique_csv


def select_candidates(
    unique_rows: list[dict[str, str]],
    max_eval: int,
    allow_risky_fallback: bool,
) -> list[dict[str, str]]:
    non_default = [row for row in unique_rows if not bool_from_csv(row.get("candidate_is_default", ""))]
    selected: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(rows: list[dict[str, str]], reason: str) -> None:
        for row in rows:
            if len(selected) >= max_eval:
                return
            plan = row["seg_plan"]
            if plan in seen:
                continue
            item = dict(row)
            item["selection_reason"] = reason
            selected.append(item)
            seen.add(plan)

    conservative = [
        row for row in non_default if bool_from_csv(row.get("conservative_role_is_eligible", ""))
    ]
    conservative.sort(
        key=lambda row: (
            float_from_row(row, "best_ranking_score"),
            float_from_row(row, "best_speed_proxy_ratio_vs_default"),
            row["seg_plan"],
        )
    )
    add(conservative, "conservative_eligible")

    frontier_like = [
        row
        for row in non_default
        if float_from_row(row, "best_recall_risk_score", 2.0) <= 1.0
        and float_from_row(row, "best_speed_proxy_ratio_vs_default", 2.0) <= 1.0
    ]
    frontier_like.sort(
        key=lambda row: (
            float_from_row(row, "best_ranking_score"),
            float_from_row(row, "best_speed_proxy_ratio_vs_default"),
            row["seg_plan"],
        )
    )
    add(frontier_like, "frontier_like")

    if allow_risky_fallback:
        fallback = sorted(
            non_default,
            key=lambda row: (
                float_from_row(row, "best_ranking_score"),
                float_from_row(row, "best_speed_proxy_ratio_vs_default"),
                row["seg_plan"],
            ),
        )
        add(fallback, "risky_fallback_best_score")

    return selected


def parse_compare_stdout(stdout: str) -> dict[str, Any]:
    vals: dict[str, str] = {}
    for line in stdout.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            vals[key.strip()] = value.strip()
    out: dict[str, Any] = {}
    for key in [
        "default_recall",
        "custom_recall",
        "delta_recall",
    ]:
        if key in vals:
            out[key] = float(vals[key])
    for key in [
        "custom_better_queries",
        "custom_equal_queries",
        "custom_worse_queries",
        "worst_query",
        "worst_delta_hits",
    ]:
        if key in vals:
            out[key] = int(vals[key])
    return out


def summarize_compare_csv(path: Path) -> dict[str, Any]:
    rows = read_csv(path)
    if not rows:
        raise ValueError(f"empty compare CSV: {path}")
    topk = int(rows[0]["topk"])
    default_hits = sum(int(row["default_hits"]) for row in rows)
    custom_hits = sum(int(row["custom_hits"]) for row in rows)
    deltas = [int(row["delta_hits"]) for row in rows]
    denom = len(rows) * topk
    worst_delta = min(deltas)
    worst_query = int(rows[deltas.index(worst_delta)]["query_id"])
    return {
        "default_recall": default_hits / denom,
        "custom_recall": custom_hits / denom,
        "delta_recall": (custom_hits - default_hits) / denom,
        "custom_better_queries": sum(delta > 0 for delta in deltas),
        "custom_equal_queries": sum(delta == 0 for delta in deltas),
        "custom_worse_queries": sum(delta < 0 for delta in deltas),
        "worst_query": worst_query,
        "worst_delta_hits": worst_delta,
    }


def read_qps_csv(path: Path) -> dict[str, Any]:
    rows = read_csv(path)
    if len(rows) != 1:
        raise ValueError(f"expected one QPS row in {path}, got {len(rows)}")
    row = rows[0]
    return {
        "qps": float(row["QPS"]),
        "avg_tm_ms": float(row["avg_tm_ms"]),
        "recall": float(row["recall"]),
        "ratio": float(row["ratio"]),
        "bw_mbps": float(row["bw_mbps"]),
        "compute_kopps": float(row["compute_kopps"]),
        "output": str(path),
    }


def ensure_index(
    spec: DatasetSpec,
    root: Path,
    plan: str,
    env: dict[str, str],
    force_build: bool,
    dry_run: bool,
) -> Path:
    path = index_path(root, spec, plan)
    if path.exists() and not force_build:
        print(f"REUSE {path}", flush=True)
        return path
    cmd = [
        str(REPO_ROOT / "bin" / "create_index"),
        "-dataset",
        spec.dataset,
        "-K",
        str(spec.k),
        "-B",
        b_label(spec.avg_bits),
        "-enable_PCA=true",
        "-logtostderr=1",
    ]
    if plan:
        cmd.insert(-1, f"-seg_plan={plan}")
    run_command(cmd, root, env, dry_run)
    return path


def ensure_default_qps(
    spec: DatasetSpec,
    root: Path,
    env: dict[str, str],
    force_eval: bool,
    dry_run: bool,
) -> dict[str, Any]:
    path = qps_path(root, spec)
    if path.exists() and not force_eval:
        print(f"REUSE {path}", flush=True)
        return read_qps_csv(path)
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
        f"-fix_nprobe={spec.qps_nprobe}",
        "-fix_thread=24",
        "-logtostderr=1",
    ]
    run_command(cmd, root, env, dry_run)
    return {} if dry_run else read_qps_csv(path)


def evaluate_candidate(
    spec: DatasetSpec,
    root: Path,
    date: str,
    plan: str,
    env: dict[str, str],
    force_build: bool,
    force_eval: bool,
    dry_run: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ensure_index(spec, root, "", env, False, dry_run)
    ensure_index(spec, root, plan, env, force_build, dry_run)

    compare_rows: list[dict[str, Any]] = []
    label = plan_label(plan)
    for nprobe in spec.compare_nprobes:
        output = (
            root
            / "reports"
            / f"{spec.name}_{label}_compare_np{nprobe}_top{spec.topk}_{date}.csv"
        )
        if output.exists() and not force_eval:
            print(f"REUSE {output}", flush=True)
            vals = summarize_compare_csv(output)
        else:
            cmd = [
                str(REPO_ROOT / "bin" / "compare_search_results"),
                "-dataset",
                spec.dataset,
                "-K",
                str(spec.k),
                "-B",
                b_label(spec.avg_bits),
                "-enable_PCA=true",
                "-searcher_dist_type=0",
                f"-searcher_safe_block_min_mode={SAFE_BLOCK_MIN_MODE}",
                f"-compare_topk={spec.topk}",
                f"-compare_nprobe={nprobe}",
                f"-seg_plan={plan}",
                f"-compare_output={output}",
                "-logtostderr=1",
            ]
            stdout = run_command(cmd, root, env, dry_run)
            vals = {} if dry_run else parse_compare_stdout(stdout)
        compare_rows.append(
            {
                "nprobe": nprobe,
                "compare_output": str(output),
                **vals,
            }
        )

    default_qps = ensure_default_qps(spec, root, env, force_eval, dry_run)
    custom_qps_path = qps_path(root, spec, plan)
    if custom_qps_path.exists() and not force_eval:
        print(f"REUSE {custom_qps_path}", flush=True)
        custom_qps = read_qps_csv(custom_qps_path)
    else:
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
            f"-fix_nprobe={spec.qps_nprobe}",
            "-fix_thread=24",
            f"-seg_plan={plan}",
            "-logtostderr=1",
        ]
        run_command(cmd, root, env, dry_run)
        custom_qps = {} if dry_run else read_qps_csv(custom_qps_path)

    qps_summary = {
        "qps_nprobe": spec.qps_nprobe,
        "default_qps": default_qps,
        "custom_qps": custom_qps,
        "qps_ratio_vs_default": (
            custom_qps["qps"] / default_qps["qps"]
            if default_qps and custom_qps and default_qps.get("qps", 0) > 0
            else None
        ),
    }
    return compare_rows, qps_summary


def run_spec(
    spec: DatasetSpec,
    root: Path,
    date: str,
    env: dict[str, str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    candidate_csv = maybe_run_generator(spec, root, date, env, args.force, args.dry_run)
    candidate_rows = [] if args.dry_run else read_csv(candidate_csv)
    candidate_defaults = [
        row["seg_plan"] for row in candidate_rows if bool_from_csv(row.get("is_default", ""))
    ]
    generator_default_plan = read_generator_default_plan(candidate_csv) if not args.dry_run else ""
    default_plan = candidate_defaults[0] if candidate_defaults else generator_default_plan
    generated_non_default = [
        row for row in candidate_rows if not bool_from_csv(row.get("is_default", ""))
    ]
    if not generated_non_default:
        return {
            "spec": asdict(spec),
            "candidate_csv": str(candidate_csv),
            "unique_csv": "",
            "default_plan": default_plan,
            "candidate_count": len(candidate_rows),
            "unique_plan_count": 0,
            "scorer_skipped_reason": "generator_produced_no_non_default_candidates",
            "selected": [],
            "selection_policy": {
                "max_eval_per_run": args.max_eval_per_run,
                "allow_risky_fallback": bool(args.allow_risky_fallback),
                "scorer_grid_preset": args.scorer_grid_preset,
                "feature_cache_dir": str(args.feature_cache_dir) if args.feature_cache_dir else "",
                "use_cost_reduced_scorer": bool(args.use_cost_reduced_scorer),
            },
            "evaluations": [],
            "top_unique": [],
            "generated_candidates": candidate_rows,
        }

    unique_csv = maybe_run_scorer(
        spec,
        root,
        date,
        candidate_csv,
        default_plan,
        env,
        args,
        args.force,
        args.dry_run,
    )
    unique_rows = [] if args.dry_run else read_csv(unique_csv)
    default_rows = [row for row in unique_rows if bool_from_csv(row.get("candidate_is_default", ""))]
    default_plan = default_rows[0]["seg_plan"] if default_rows else default_plan
    selected = select_candidates(unique_rows, args.max_eval_per_run, args.allow_risky_fallback)

    evaluations: list[dict[str, Any]] = []
    if args.evaluate:
        for row in selected:
            compare_rows, qps_summary = evaluate_candidate(
                spec,
                root,
                date,
                row["seg_plan"],
                env,
                args.force_build,
                args.force_eval,
                args.dry_run,
            )
            evaluations.append(
                {
                    "candidate": row,
                    "compare_rows": compare_rows,
                    "qps_summary": qps_summary,
                }
            )

    return {
        "spec": asdict(spec),
        "candidate_csv": str(candidate_csv),
        "unique_csv": str(unique_csv),
        "default_plan": default_plan,
        "unique_plan_count": len(unique_rows),
        "selected": selected,
        "selection_policy": {
            "max_eval_per_run": args.max_eval_per_run,
            "allow_risky_fallback": bool(args.allow_risky_fallback),
            "scorer_grid_preset": args.scorer_grid_preset,
            "feature_cache_dir": str(args.feature_cache_dir) if args.feature_cache_dir else "",
            "use_cost_reduced_scorer": bool(args.use_cost_reduced_scorer),
        },
        "evaluations": evaluations,
        "top_unique": unique_rows[: min(10, len(unique_rows))],
    }


def flatten_summary_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        selected = result["selected"]
        if not selected:
            rows.append(
                {
                    "run": spec["name"],
                    "dataset": spec["dataset"],
                    "k": spec["k"],
                    "avg_bits": spec["avg_bits"],
                    "topk": spec["topk"],
                    "default_plan": result["default_plan"],
                    "candidate_plan": "",
                    "selection_reason": "no_candidate_selected",
                    "scorer_skipped_reason": result.get("scorer_skipped_reason", ""),
                    "unique_csv": result.get("unique_csv", ""),
                    "scorer_grid_preset": result.get("selection_policy", {}).get("scorer_grid_preset", ""),
                    "feature_cache_dir": result.get("selection_policy", {}).get("feature_cache_dir", ""),
                    "use_cost_reduced_scorer": result.get("selection_policy", {}).get("use_cost_reduced_scorer", ""),
                    "conservative_eligible": "",
                    "best_ranking_score": "",
                    "best_recall_risk_score": "",
                    "best_speed_proxy_ratio_vs_default": "",
                    "qps_nprobe": spec["qps_nprobe"],
                    "qps_ratio_vs_default": "",
                    "custom_qps": "",
                    "default_qps": "",
                }
            )
            continue
        eval_by_plan = {
            item["candidate"]["seg_plan"]: item for item in result.get("evaluations", [])
        }
        for candidate in selected:
            evaluation = eval_by_plan.get(candidate["seg_plan"], {})
            qps_summary = evaluation.get("qps_summary", {})
            default_qps = qps_summary.get("default_qps", {})
            custom_qps = qps_summary.get("custom_qps", {})
            row: dict[str, Any] = {
                "run": spec["name"],
                "dataset": spec["dataset"],
                "k": spec["k"],
                "avg_bits": spec["avg_bits"],
                "topk": spec["topk"],
                "default_plan": result["default_plan"],
                "candidate_plan": candidate["seg_plan"],
                "candidate_family": candidate.get("candidate_families", ""),
                "selection_reason": candidate.get("selection_reason", ""),
                "scorer_skipped_reason": result.get("scorer_skipped_reason", ""),
                "unique_csv": result.get("unique_csv", ""),
                "scorer_grid_preset": result.get("selection_policy", {}).get("scorer_grid_preset", ""),
                "feature_cache_dir": result.get("selection_policy", {}).get("feature_cache_dir", ""),
                "use_cost_reduced_scorer": result.get("selection_policy", {}).get("use_cost_reduced_scorer", ""),
                "conservative_eligible": candidate.get("conservative_role_is_eligible", ""),
                "conservative_reasons": candidate.get("conservative_role_reasons", ""),
                "best_ranking_score": candidate.get("best_ranking_score", ""),
                "best_recall_risk_score": candidate.get("best_recall_risk_score", ""),
                "best_speed_proxy_ratio_vs_default": candidate.get("best_speed_proxy_ratio_vs_default", ""),
                "qps_nprobe": spec["qps_nprobe"],
                "qps_ratio_vs_default": qps_summary.get("qps_ratio_vs_default", ""),
                "custom_qps": custom_qps.get("qps", ""),
                "default_qps": default_qps.get("qps", ""),
                "custom_qps_recall": custom_qps.get("recall", ""),
                "default_qps_recall": default_qps.get("recall", ""),
            }
            for compare in evaluation.get("compare_rows", []):
                nprobe = compare["nprobe"]
                row[f"recall_np{nprobe}"] = compare.get("custom_recall", "")
                row[f"default_recall_np{nprobe}"] = compare.get("default_recall", "")
                row[f"delta_np{nprobe}"] = compare.get("delta_recall", "")
            rows.append(row)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-dataset default-neighborhood SAQ validation.")
    parser.add_argument(
        "--run",
        action="append",
        dest="runs",
        choices=sorted(BUILTIN_SPECS),
        help="Builtin run spec to execute. Repeatable. Defaults to DEEP/CIFAR/GIST.",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Experiment root containing data/ and results/.")
    parser.add_argument("--date", default=DEFAULT_DATE, help="Date label for output files.")
    parser.add_argument("--evaluate", action="store_true", help="Build/evaluate selected candidates.")
    parser.add_argument("--allow-risky-fallback", action="store_true", help="If no conservative/frontier candidate is selected, evaluate the best non-default scorer candidate.")
    parser.add_argument("--max-eval-per-run", type=int, default=1, help="Maximum selected candidates to evaluate per run.")
    parser.add_argument(
        "--scorer-grid-preset",
        choices=("full", "endpoints"),
        default="full",
        help="Scorer grid to use. 'full' preserves the historical grid; 'endpoints' uses the compact validated endpoint grid.",
    )
    parser.add_argument(
        "--feature-cache-dir",
        type=Path,
        default=None,
        help="Optional query-unaware scorer feature cache directory for residual/tail/pair features.",
    )
    parser.add_argument(
        "--use-cost-reduced-scorer",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use the validated endpoint grid and a default feature cache under <root>/reports unless explicitly overridden.",
    )
    parser.add_argument("--force", action="store_true", help="Rerun generator and scorer even if output files exist.")
    parser.add_argument("--force-build", action="store_true", help="Rebuild custom indexes even if index files exist.")
    parser.add_argument("--force-eval", action="store_true", help="Rerun compare/QPS even if output files exist.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    parser.add_argument("--output-prefix", type=Path, default=None, help="Summary output prefix. Defaults under <root>/reports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.use_cost_reduced_scorer:
        if args.scorer_grid_preset == "full":
            args.scorer_grid_preset = "endpoints"
        if args.feature_cache_dir is None:
            args.feature_cache_dir = (
                args.root / "reports" / f"fixed_policy_scorer_feature_cache_{args.date}"
            )
    run_names = args.runs or [
        "deep1M_sample100k_B4",
        "deep1M_sample100k_B5",
        "cifar60k_B4",
        "gist_full_K4096_B4",
    ]
    if args.max_eval_per_run < 0:
        raise ValueError("--max-eval-per-run must be non-negative")

    env = os.environ.copy()
    deps = "/tmp/saq-deps/usr/lib64"
    env["LD_LIBRARY_PATH"] = deps + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")

    results: list[dict[str, Any]] = []
    for name in run_names:
        spec = BUILTIN_SPECS[name]
        print(f"=== RUN {name} ===", flush=True)
        results.append(run_spec(spec, args.root, args.date, env, args))

    prefix = args.output_prefix or (
        args.root / "reports" / f"default_neighborhood_cross_dataset_validation_{args.date}"
    )
    summary_csv = prefix.with_suffix(".csv")
    summary_json = prefix.with_suffix(".json")
    rows = flatten_summary_rows(results)
    fields = sorted({key for row in rows for key in row.keys()})
    # Keep the most important fields first, then append dynamic recall columns.
    preferred = [
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
        "unique_csv",
        "scorer_grid_preset",
        "feature_cache_dir",
        "use_cost_reduced_scorer",
        "conservative_eligible",
        "conservative_reasons",
        "best_ranking_score",
        "best_recall_risk_score",
        "best_speed_proxy_ratio_vs_default",
        "qps_nprobe",
        "default_qps",
        "custom_qps",
        "qps_ratio_vs_default",
        "default_qps_recall",
        "custom_qps_recall",
    ]
    ordered_fields = [field for field in preferred if field in fields] + [
        field for field in fields if field not in preferred
    ]
    write_csv(summary_csv, rows, ordered_fields)
    write_json(
        summary_json,
        {
            "runs": run_names,
            "evaluate": bool(args.evaluate),
            "allow_risky_fallback": bool(args.allow_risky_fallback),
            "max_eval_per_run": int(args.max_eval_per_run),
            "scorer_grid_preset": args.scorer_grid_preset,
            "feature_cache_dir": str(args.feature_cache_dir) if args.feature_cache_dir else "",
            "use_cost_reduced_scorer": bool(args.use_cost_reduced_scorer),
            "summary_csv": str(summary_csv),
            "results": results,
        },
    )
    print(json.dumps({"summary_csv": str(summary_csv), "summary_json": str(summary_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
