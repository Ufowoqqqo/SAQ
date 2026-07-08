#!/usr/bin/env python3
"""Prepare or verify fixed-policy input artifacts.

Default behavior is verification only. Preparation is explicit and dataset
scoped so that large local rebuilds are not triggered accidentally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from write_fixed_policy_input_manifest import full_sha256, inspect_xvecs_shape


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path("/tmp/saq-run")
DEFAULT_SOURCE_ROOT = Path("/rwproject/kdd-db/kluaq/dataset")
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "saq_fixed_policy_input_manifest_2026_07_08.json"
DEFAULT_LD_LIBRARY_PATH = "/tmp/saq-deps/usr/lib64"
SUPPORTED_PREPARE_DATASETS = {"gist_full", "cifar60k", "deep1M_sample100k", "word2vec_sample100k"}
DATASET_CHOICES = ("all", "gist_full", "cifar60k", "deep1M_sample100k", "audio", "word2vec_sample100k")


@dataclass(frozen=True)
class Step:
    dataset: str
    label: str
    kind: str
    argv: tuple[str, ...] = ()
    cwd: Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    source: Path | None = None
    target: Path | None = None
    note: str = ""
    large: bool = False


def quote_command(argv: tuple[str, ...], env: dict[str, str] | None = None) -> str:
    parts: list[str] = []
    for key, value in sorted((env or {}).items()):
        parts.append(f"{key}={shlex.quote(value)}")
    parts.extend(shlex.quote(str(item)) for item in argv)
    return " ".join(parts)


def display_path(path: Path) -> str:
    return str(path)


def selected_datasets(values: list[str]) -> list[str]:
    if not values or "all" in values:
        return list(DATASET_CHOICES[1:])
    out: list[str] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def repo_script(name: str) -> str:
    return str(REPO_ROOT / "script" / name)


def compute_gt_binary() -> str:
    return str(REPO_ROOT / "bin" / "compute_gt")


def sampled_pca_ivf_step(
    dataset: str,
    args: argparse.Namespace,
    input_path: Path,
    query_path: Path,
    output_dir: Path,
    sample_size: int,
    k: int,
    groundtruth_input: Path | None = None,
) -> Step:
    argv = [
        args.python,
        repo_script("prepare_sampled_pca_ivf.py"),
        "--input",
        str(input_path),
        "--query-input",
        str(query_path),
        "--output-dir",
        str(output_dir),
        "--dataset",
        dataset,
        "--sample-size",
        str(sample_size),
        "--k",
        str(k),
        "--cluster-dims",
        "64",
        "--iterations",
        "4",
        "--chunk-rows",
        "2048",
        "--seed",
        "0",
    ]
    if groundtruth_input is not None:
        argv.extend(["--groundtruth-input", str(groundtruth_input)])
    return Step(
        dataset=dataset,
        label="sampled PCA / K512 IVF preparation",
        kind="command",
        argv=tuple(argv),
        cwd=REPO_ROOT,
        large=sample_size >= 1_000_000,
    )


def compute_gt_step(
    dataset: str,
    args: argparse.Namespace,
    gt_topk: int,
    gt_threads: int,
    enable_pca: bool,
    gt_output: Path | None = None,
) -> Step:
    argv = [
        compute_gt_binary(),
        "-dataset",
        dataset,
        "-K",
        "512",
        "-B",
        "4",
        f"-enable_PCA={'true' if enable_pca else 'false'}",
        "-searcher_dist_type=0",
        f"-gt_topk={gt_topk}",
        f"-gt_threads={gt_threads}",
        "-gt_overwrite=true",
        "-logtostderr=1",
    ]
    if gt_output is not None:
        argv.append(f"-gt_output={gt_output}")
    return Step(
        dataset=dataset,
        label=f"top{gt_topk} L2 groundtruth computation",
        kind="command",
        argv=tuple(argv),
        cwd=args.root,
        env={"LD_LIBRARY_PATH": args.ld_library_path},
        large=True,
    )


def build_steps(args: argparse.Namespace) -> dict[str, list[Step]]:
    root = args.root
    source = args.source_root
    steps: dict[str, list[Step]] = {}

    steps["gist_full"] = [
        sampled_pca_ivf_step(
            "gist_full",
            args,
            source / "gist" / "gist_base.fvecs",
            source / "gist" / "gist_query.fvecs",
            root / "data" / "gist_full",
            1_000_000,
            512,
            source / "gist" / "gist_groundtruth_l2.ivecs",
        ),
        Step(
            dataset="gist_full",
            label="K4096 IVF preparation from existing PCA base",
            kind="command",
            argv=(
                args.python,
                repo_script("prepare_ivf_from_pca.py"),
                "--base-pca",
                str(root / "data" / "gist_full" / "gist_full_base_pca.fvecs"),
                "--output-dir",
                str(root / "data" / "gist_full"),
                "--dataset",
                "gist_full",
                "--k",
                "4096",
                "--cluster-dims",
                "64",
                "--iterations",
                "4",
                "--chunk-rows",
                "1024",
                "--seed",
                "0",
            ),
            cwd=REPO_ROOT,
            large=True,
        ),
        Step(
            dataset="gist_full",
            label="raw GIST base symlink",
            kind="symlink",
            source=source / "gist" / "gist_base.fvecs",
            target=root / "data" / "gist_raw" / "gist_raw_base.fvecs",
        ),
        Step(
            dataset="gist_full",
            label="raw GIST query symlink",
            kind="symlink",
            source=source / "gist" / "gist_query.fvecs",
            target=root / "data" / "gist_raw" / "gist_raw_query.fvecs",
        ),
        Step(
            dataset="gist_full",
            label="raw GIST GT symlink",
            kind="symlink",
            source=source / "gist" / "gist_groundtruth_l2.ivecs",
            target=root / "data" / "gist_raw" / "gist_raw_groundtruth.ivecs",
        ),
        compute_gt_step(
            "gist_raw",
            args,
            gt_topk=100,
            gt_threads=24,
            enable_pca=False,
            gt_output=root / "data" / "gist_full" / "gist_full_groundtruth_top100_original_l2.ivecs",
        ),
        Step(
            dataset="gist_full",
            label="activate original-space top100 GT",
            kind="copy",
            source=root / "data" / "gist_full" / "gist_full_groundtruth_top100_original_l2.ivecs",
            target=root / "data" / "gist_full" / "gist_full_groundtruth.ivecs",
        ),
    ]

    steps["cifar60k"] = [
        sampled_pca_ivf_step(
            "cifar60k",
            args,
            source / "cifar60k" / "cifar60k_base.fvecs",
            source / "cifar60k" / "cifar60k_query.fvecs",
            root / "data" / "cifar60k",
            100_000,
            512,
            source / "cifar60k" / "cifar60k_groundtruth_l2.ivecs",
        )
    ]

    steps["deep1M_sample100k"] = [
        sampled_pca_ivf_step(
            "deep1M_sample100k",
            args,
            source / "deep1M" / "deep1M_base.fvecs",
            source / "deep1M" / "deep1M_query.fvecs",
            root / "data" / "deep1M_sample100k",
            100_000,
            512,
        ),
        compute_gt_step(
            "deep1M_sample100k",
            args,
            gt_topk=100,
            gt_threads=32,
            enable_pca=True,
        ),
    ]

    steps["audio"] = [
        Step(
            dataset="audio",
            label="audio variance artifact",
            kind="unsupported",
            note=(
                "Current matrix only needs audio_base_pca.vars.fvecs for abstention. "
                "The exact historical PCA/IVF preparation command was not recovered; "
                "use an archived input bundle or existing manifest-matching artifact."
            ),
        )
    ]

    steps["word2vec_sample100k"] = [
        sampled_pca_ivf_step(
            "word2vec_sample100k",
            args,
            source / "word2vec" / "word2vec_base.fvecs",
            source / "word2vec" / "word2vec_query.fvecs",
            root / "data" / "word2vec_sample100k",
            100_000,
            512,
        )
    ]
    return steps


def print_step(step: Step) -> None:
    print(f"[{step.dataset}] {step.label}")
    if step.note:
        print(f"  note: {step.note}")
    if step.large:
        print("  cost: large")
    if step.kind == "command":
        if step.cwd is not None:
            print(f"  cwd: {step.cwd}")
        print(f"  command: {quote_command(step.argv, step.env)}")
    elif step.kind == "symlink":
        print(f"  command: mkdir -p {shlex.quote(str(step.target.parent))}")
        print(f"  command: ln -s {shlex.quote(str(step.source))} {shlex.quote(str(step.target))}")
        print("  note: existing nonmatching links require --overwrite-links during --prepare")
    elif step.kind == "copy":
        print(f"  command: cp {shlex.quote(str(step.source))} {shlex.quote(str(step.target))}")
        print("  note: existing different targets require --overwrite during --prepare")
    elif step.kind == "unsupported":
        print("  status: unsupported for clean preparation")
    else:
        print(f"  status: unknown step kind {step.kind}")


def dry_run(args: argparse.Namespace) -> int:
    plans = build_steps(args)
    datasets = selected_datasets(args.dataset)
    print("# Fixed-policy input preparation dry run")
    print(f"root: {args.root}")
    print(f"source_root: {args.source_root}")
    print()
    for dataset in datasets:
        print(f"## {dataset}")
        for step in plans[dataset]:
            print_step(step)
        print()
    return 0


def manifest_path(args: argparse.Namespace) -> Path:
    path = args.manifest
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def load_manifest(args: argparse.Namespace) -> dict[str, Any]:
    path = manifest_path(args)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def record_dataset(record: dict[str, Any]) -> str | None:
    rel = record.get("relative_to_root")
    if not rel:
        return None
    parts = Path(rel).parts
    if len(parts) >= 2 and parts[0] == "data":
        return parts[1]
    return None


def expected_full_hash(record: dict[str, Any]) -> str | None:
    return record.get("hash", {}).get("sha256")


def verify_record(record: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    rel = record.get("relative_to_root")
    path = args.root / rel if rel else Path(record["path"])
    expected_format = record.get("format", {})
    result: dict[str, Any] = {
        "path": str(path),
        "relative_to_root": rel,
        "dataset": record_dataset(record),
        "status": "matched",
        "problems": [],
    }

    if not path.exists():
        result["status"] = "missing"
        result["problems"].append("missing")
        return result
    if not path.is_file():
        result["status"] = "mismatch"
        result["problems"].append("not_regular_file")
        return result

    stat = path.stat()
    result["size_bytes"] = stat.st_size
    if "size_bytes" in record and int(record["size_bytes"]) != stat.st_size:
        result["problems"].append(
            f"size expected {record['size_bytes']} got {stat.st_size}"
        )

    shape = inspect_xvecs_shape(path, stat.st_size)
    result["format"] = shape
    for key in ("kind", "rows", "dim"):
        if key in expected_format and shape.get(key) != expected_format.get(key):
            result["problems"].append(
                f"{key} expected {expected_format.get(key)} got {shape.get(key)}"
            )
    if shape.get("status") != "ok":
        result["problems"].append(f"shape status {shape.get('status')}")

    if not args.skip_hash:
        expected = expected_full_hash(record)
        if expected is not None:
            actual = full_sha256(path)
            result["sha256"] = actual
            if actual != expected:
                result["problems"].append(
                    f"sha256 expected {expected[:16]} got {actual[:16]}"
                )
        elif args.require_full_hash:
            result["problems"].append("manifest record does not contain full sha256")

    if result["problems"]:
        result["status"] = "mismatch"
    return result


def verify_inputs(args: argparse.Namespace) -> int:
    manifest = load_manifest(args)
    datasets = set(selected_datasets(args.dataset))
    all_selected = not args.dataset or "all" in args.dataset
    files = [
        record
        for record in manifest["files"]
        if all_selected or record_dataset(record) in datasets
    ]
    if not files:
        raise ValueError("no manifest records selected")

    results = [verify_record(record, args) for record in files]
    counts = {
        "matched": sum(result["status"] == "matched" for result in results),
        "missing": sum(result["status"] == "missing" for result in results),
        "mismatch": sum(result["status"] == "mismatch" for result in results),
        "total": len(results),
    }

    print("# Fixed-policy input verification")
    print(f"manifest: {manifest_path(args)}")
    print(f"root: {args.root}")
    print(f"hash_check: {'disabled' if args.skip_hash else 'enabled'}")
    print(
        "summary: "
        f"matched={counts['matched']} missing={counts['missing']} "
        f"mismatch={counts['mismatch']} total={counts['total']}"
    )
    for result in results:
        if result["status"] == "matched" and not args.verbose:
            continue
        print(f"- [{result['status'].upper()}] {result['relative_to_root'] or result['path']}")
        for problem in result["problems"]:
            print(f"  problem: {problem}")

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "manifest": str(manifest_path(args)),
            "root": str(args.root),
            "hash_check": not args.skip_hash,
            "counts": counts,
            "results": results,
        }
        args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote JSON: {args.output_json}")

    return 0 if counts["missing"] == 0 and counts["mismatch"] == 0 else 1


def run_command(step: Step) -> None:
    env = os.environ.copy()
    env.update(step.env)
    subprocess.run(
        list(step.argv),
        cwd=str(step.cwd) if step.cwd is not None else None,
        env=env,
        check=True,
    )


def digest(path: Path) -> str:
    return full_sha256(path)


def ensure_symlink(step: Step, args: argparse.Namespace) -> None:
    assert step.source is not None and step.target is not None
    step.target.parent.mkdir(parents=True, exist_ok=True)
    if step.target.is_symlink():
        current = Path(os.readlink(step.target))
        if current == step.source:
            return
        if not args.overwrite_links:
            raise FileExistsError(
                f"{step.target} points to {current}, expected {step.source}; use --overwrite-links"
            )
        step.target.unlink()
    elif step.target.exists():
        if not args.overwrite_links:
            raise FileExistsError(f"{step.target} exists and is not a symlink; use --overwrite-links")
        if step.target.is_dir():
            raise IsADirectoryError(f"refusing to replace directory: {step.target}")
        step.target.unlink()
    step.target.symlink_to(step.source)


def copy_if_needed(step: Step, args: argparse.Namespace) -> None:
    assert step.source is not None and step.target is not None
    if not step.source.exists():
        raise FileNotFoundError(step.source)
    step.target.parent.mkdir(parents=True, exist_ok=True)
    if step.target.exists():
        if digest(step.source) == digest(step.target):
            return
        if not args.overwrite:
            raise FileExistsError(f"{step.target} exists with different content; use --overwrite")
    shutil.copyfile(step.source, step.target)


def prepare(args: argparse.Namespace) -> int:
    datasets = selected_datasets(args.dataset)
    if "audio" in datasets:
        print("audio clean preparation is unsupported: exact historical PCA/IVF command was not recovered")
        if len(datasets) == 1:
            return 1
    requested_supported = [dataset for dataset in datasets if dataset in SUPPORTED_PREPARE_DATASETS]
    if not requested_supported:
        print("no supported datasets selected for preparation")
        return 1
    if (not args.dataset or args.dataset == ["all"]) and not args.prepare_all_supported:
        print("refusing to prepare all supported datasets without --prepare-all-supported")
        return 1

    plans = build_steps(args)
    for dataset in requested_supported:
        if dataset == "gist_full" and not args.allow_large:
            print("refusing to prepare gist_full without --allow-large")
            return 1
        print(f"## preparing {dataset}")
        for step in plans[dataset]:
            print_step(step)
            if step.kind == "command":
                run_command(step)
            elif step.kind == "symlink":
                ensure_symlink(step, args)
            elif step.kind == "copy":
                copy_if_needed(step, args)
            elif step.kind == "unsupported":
                raise RuntimeError(step.note)
    return verify_inputs(args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare or verify fixed-policy input artifacts."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print preparation commands without running them.")
    mode.add_argument("--verify-only", action="store_true", help="Verify prepared inputs against the manifest.")
    mode.add_argument("--prepare", action="store_true", help="Run preparation steps for selected supported datasets.")
    parser.add_argument("--dataset", action="append", choices=DATASET_CHOICES, default=None)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--ld-library-path", default=DEFAULT_LD_LIBRARY_PATH)
    parser.add_argument("--skip-hash", action="store_true", help="Verify size/shape but skip full SHA256 checks.")
    parser.add_argument("--require-full-hash", action="store_true", help="Fail verification if a manifest record lacks full SHA256.")
    parser.add_argument("--verbose", action="store_true", help="Print matched records during verification.")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--allow-large", action="store_true", help="Allow large GIST preparation steps.")
    parser.add_argument("--prepare-all-supported", action="store_true", help="Allow --prepare --dataset all.")
    parser.add_argument("--overwrite", action="store_true", help="Allow copy steps to replace existing files.")
    parser.add_argument("--overwrite-links", action="store_true", help="Allow symlink steps to replace existing links/files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.dry_run and not args.prepare:
        args.verify_only = True
    if args.dry_run:
        return dry_run(args)
    if args.verify_only:
        return verify_inputs(args)
    if args.prepare:
        return prepare(args)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
