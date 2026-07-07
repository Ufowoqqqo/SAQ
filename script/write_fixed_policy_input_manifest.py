#!/usr/bin/env python3
"""Write a provenance manifest for fixed-policy input artifacts.

The fixed-policy runner can regenerate candidate, scorer, index, compare, QPS,
and report artifacts once the dataset/PCA/IVF inputs exist. This script records
the identity of those input artifacts without running experiments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from check_fixed_policy_artifacts import DEFAULT_EXPECTED_CSV, Artifact, collect_artifacts


DEFAULT_ROOT = Path("/tmp/saq-run")
DEFAULT_DATE = "2026_07_08_runner_cost_reduced_eval"
DEFAULT_OUTPUT_JSON = Path("docs/saq_fixed_policy_input_manifest_2026_07_08.json")
DEFAULT_OUTPUT_MD = Path("docs/saq_fixed_policy_input_manifest_2026_07_08.md")
DEFAULT_SAMPLE_BYTES = 1024 * 1024
HASH_CHUNK_BYTES = 8 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def mtime_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def unique_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def path_relative_to(path: Path, root: Path) -> str | None:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return None


def inspect_xvecs_shape(path: Path, size_bytes: int) -> dict[str, Any]:
    if path.suffix == ".fvecs":
        kind = "fvecs"
        value_dtype = "float32"
        item_size = 4
    elif path.suffix == ".ivecs":
        kind = "ivecs"
        value_dtype = "int32"
        item_size = 4
    else:
        return {"kind": "unknown", "status": "not_xvecs"}

    if size_bytes < 4:
        return {
            "kind": kind,
            "value_dtype": value_dtype,
            "status": "error",
            "error": "file smaller than xvecs dimension header",
        }

    with path.open("rb") as handle:
        raw_dim = handle.read(4)
    dim = int.from_bytes(raw_dim, byteorder="little", signed=True)
    if dim <= 0:
        return {
            "kind": kind,
            "value_dtype": value_dtype,
            "status": "error",
            "error": f"invalid first-row dimension {dim}",
        }

    row_size_bytes = 4 + dim * item_size
    divisible = size_bytes % row_size_bytes == 0
    rows = size_bytes // row_size_bytes if divisible else None
    return {
        "kind": kind,
        "value_dtype": value_dtype,
        "status": "ok" if divisible else "error",
        "dim": dim,
        "rows": rows,
        "row_size_bytes": row_size_bytes,
        "size_divisible_by_row_size": divisible,
        "error": None if divisible else "file size is not divisible by inferred xvecs row size",
    }


def full_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sample_sha256(path: Path, size_bytes: int, sample_bytes: int) -> str:
    digest = hashlib.sha256()
    digest.update(b"saq-input-manifest-sample-v1\0")
    digest.update(str(size_bytes).encode("ascii"))
    digest.update(b"\0")
    with path.open("rb") as handle:
        digest.update(b"first\0")
        digest.update(handle.read(sample_bytes))
        if size_bytes > sample_bytes:
            handle.seek(max(0, size_bytes - sample_bytes))
            digest.update(b"last\0")
            digest.update(handle.read(sample_bytes))
    return digest.hexdigest()


def metadata_sha256(size_bytes: int, format_info: dict[str, Any]) -> str:
    payload = {
        "size_bytes": size_bytes,
        "format": format_info,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_hash(
    path: Path,
    hash_mode: str,
    size_bytes: int,
    format_info: dict[str, Any],
    sample_bytes: int,
) -> dict[str, Any]:
    if hash_mode == "full":
        return {
            "mode": hash_mode,
            "status": "ok",
            "sha256": full_sha256(path),
        }
    if hash_mode == "sample":
        return {
            "mode": hash_mode,
            "status": "ok",
            "sample_bytes": sample_bytes,
            "sample_scheme": "sha256(size_bytes || first N bytes || last N bytes)",
            "sample_sha256": sample_sha256(path, size_bytes, sample_bytes),
        }
    if hash_mode == "metadata":
        return {
            "mode": hash_mode,
            "status": "ok",
            "metadata_scheme": "sha256(size_bytes and inferred xvecs shape)",
            "metadata_sha256": metadata_sha256(size_bytes, format_info),
        }
    raise ValueError(f"unknown hash mode: {hash_mode}")


def artifact_namespace(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        root=args.root,
        date=args.date,
        artifact_date=args.artifact_date,
        expected_csv=args.expected_csv,
        use_cost_reduced_scorer=args.use_cost_reduced_scorer,
        feature_cache_dir=args.feature_cache_dir,
    )


def collect_input_artifacts(args: argparse.Namespace) -> list[Artifact]:
    artifacts = collect_artifacts(artifact_namespace(args))
    return [artifact for artifact in artifacts if artifact.group == "input"]


def group_input_artifacts(artifacts: list[Artifact]) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        path = Path(artifact.path)
        key = str(path)
        entry = by_path.setdefault(
            key,
            {
                "path": key,
                "roles": [],
                "producers": [],
                "notes": [],
                "input_entries": 0,
            },
        )
        entry["roles"].append(artifact.role)
        entry["producers"].append(artifact.producer)
        entry["notes"].append(artifact.note)
        entry["input_entries"] += 1

    grouped = list(by_path.values())
    for entry in grouped:
        entry["roles"] = unique_preserve(entry["roles"])
        entry["producers"] = unique_preserve(entry["producers"])
        entry["notes"] = unique_preserve(entry["notes"])
    return sorted(grouped, key=lambda item: item["path"])


def inspect_input_file(
    grouped_entry: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    path = Path(grouped_entry["path"])
    record = dict(grouped_entry)
    record["relative_to_root"] = path_relative_to(path, args.root)
    record["exists"] = path.exists()

    if not path.exists():
        record["format"] = {"kind": "missing", "status": "missing"}
        record["hash"] = {"mode": args.hash_mode, "status": "missing"}
        return record

    stat = path.stat()
    record["is_file"] = path.is_file()
    record["size_bytes"] = stat.st_size
    record["size_mib"] = round(stat.st_size / (1024 * 1024), 6)
    record["mtime_utc"] = mtime_utc(path)

    if not path.is_file():
        record["format"] = {"kind": "non_file", "status": "error"}
        record["hash"] = {"mode": args.hash_mode, "status": "error", "error": "not a regular file"}
        return record

    format_info = inspect_xvecs_shape(path, stat.st_size)
    record["format"] = format_info
    record["hash"] = compute_hash(path, args.hash_mode, stat.st_size, format_info, args.sample_bytes)
    return record


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = collect_input_artifacts(args)
    grouped = group_input_artifacts(artifacts)
    files = [inspect_input_file(entry, args) for entry in grouped]
    present = sum(1 for record in files if record["exists"])
    xvecs_errors = [
        record["path"]
        for record in files
        if record.get("format", {}).get("status") == "error"
    ]
    total_size_bytes = sum(int(record.get("size_bytes", 0)) for record in files)

    return {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "source": {
            "script": "script/write_fixed_policy_input_manifest.py",
            "artifact_checker": "script/check_fixed_policy_artifacts.py",
        },
        "root": str(args.root),
        "date": args.date,
        "artifact_date": args.artifact_date or args.date,
        "expected_csv": str(args.expected_csv),
        "use_cost_reduced_scorer": bool(args.use_cost_reduced_scorer),
        "hash_mode": args.hash_mode,
        "sample_bytes": args.sample_bytes if args.hash_mode == "sample" else None,
        "summary": {
            "input_artifact_entries": len(artifacts),
            "unique_input_files": len(files),
            "present_unique_input_files": present,
            "missing_unique_input_files": len(files) - present,
            "total_size_bytes": total_size_bytes,
            "total_size_gib": round(total_size_bytes / (1024**3), 6),
            "xvecs_shape_errors": len(xvecs_errors),
        },
        "files": files,
    }


def hash_display(record: dict[str, Any]) -> str:
    hash_info = record.get("hash", {})
    if hash_info.get("status") != "ok":
        return str(hash_info.get("status", "unknown"))
    if "sha256" in hash_info:
        return f"`{hash_info['sha256'][:16]}`"
    if "sample_sha256" in hash_info:
        return f"`{hash_info['sample_sha256'][:16]}` sample"
    if "metadata_sha256" in hash_info:
        return f"`{hash_info['metadata_sha256'][:16]}` metadata"
    return "n/a"


def shape_display(record: dict[str, Any]) -> str:
    format_info = record.get("format", {})
    if format_info.get("status") == "ok":
        return f"{format_info.get('rows')} x {format_info.get('dim')}"
    return str(format_info.get("status", "unknown"))


def roles_display(record: dict[str, Any]) -> str:
    roles = record.get("roles", [])
    if len(roles) <= 2:
        return "; ".join(roles)
    return "; ".join(roles[:2]) + f"; +{len(roles) - 2} more"


def md_escape(value: str) -> str:
    return value.replace("|", "\\|")


def write_markdown(manifest: dict[str, Any], path: Path, args: argparse.Namespace) -> None:
    summary = manifest["summary"]
    lines: list[str] = []
    lines.append("# Fixed-Policy Input Artifact Provenance Manifest")
    lines.append("")
    lines.append("Date: 2026-07-08")
    lines.append("")
    lines.append(
        "This manifest records the required dataset/PCA/IVF input artifacts for "
        "the current fixed-policy validation matrix. It does not run plan search, "
        "indexing, recall comparison, or QPS measurement."
    )
    lines.append("")
    lines.append("## Generation Command")
    lines.append("")
    lines.append("```bash")
    lines.append("python script/write_fixed_policy_input_manifest.py \\")
    lines.append(f"  --root {args.root} \\")
    lines.append(f"  --date {args.date} \\")
    lines.append(f"  --artifact-date {args.artifact_date or args.date} \\")
    if args.use_cost_reduced_scorer:
        lines.append("  --use-cost-reduced-scorer \\")
    lines.append(f"  --hash-mode {args.hash_mode} \\")
    lines.append(f"  --output-json {args.output_json} \\")
    lines.append(f"  --output-md {args.output_md}")
    lines.append("```")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| field | value |")
    lines.append("|---|---:|")
    lines.append(f"| input artifact entries | {summary['input_artifact_entries']} |")
    lines.append(f"| unique input files | {summary['unique_input_files']} |")
    lines.append(f"| present unique input files | {summary['present_unique_input_files']} |")
    lines.append(f"| missing unique input files | {summary['missing_unique_input_files']} |")
    lines.append(f"| total input size | {summary['total_size_gib']:.3f} GiB |")
    lines.append(f"| xvecs shape errors | {summary['xvecs_shape_errors']} |")
    lines.append("")
    lines.append("## Hash Semantics")
    lines.append("")
    if manifest["hash_mode"] == "full":
        lines.append(
            "The checked-in manifest was generated with full-file SHA256. Matching "
            "hashes are therefore file-content identity checks for the listed "
            "input artifacts."
        )
    elif manifest["hash_mode"] == "sample":
        lines.append(
            "The checked-in manifest was generated with the sample hash mode. "
            "It hashes file size plus the first and last sample window, so it is "
            "a fast identity check, not a full file-content proof."
        )
    else:
        lines.append(
            "The checked-in manifest was generated with metadata hash mode. "
            "It hashes file size and inferred xvecs shape only, so it is not a "
            "file-content identity check."
        )
    lines.append("")
    lines.append("## Unique Input Files")
    lines.append("")
    lines.append("| artifact | roles | kind | shape | size MiB | hash prefix |")
    lines.append("|---|---|---|---:|---:|---|")
    for record in manifest["files"]:
        rel = record.get("relative_to_root") or record["path"]
        kind = record.get("format", {}).get("kind", "unknown")
        size_mib = record.get("size_mib")
        size_text = "n/a" if size_mib is None else f"{size_mib:.3f}"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{md_escape(str(rel))}`",
                    md_escape(roles_display(record)),
                    md_escape(str(kind)),
                    md_escape(shape_display(record)),
                    size_text,
                    hash_display(record),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The manifest turns the fixed-policy input substrate into an explicit, "
        "checkable contract. A future reproduction should first match these "
        "input files, then allow the runner to regenerate candidate, scorer, "
        "index, compare, QPS, and report artifacts."
    )
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "This manifest identifies current input files; it does not explain how "
        "the files were originally prepared from raw datasets, PCA training, IVF "
        "training, or groundtruth generation commands."
    )
    lines.append(
        "The xvecs shape check reads the first dimension header and verifies file "
        "size divisibility. It does not scan every row dimension unless a future "
        "script version adds a stronger verifier."
    )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(manifest: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a provenance manifest for fixed-policy input artifacts."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--artifact-date", default=None)
    parser.add_argument("--expected-csv", type=Path, default=DEFAULT_EXPECTED_CSV)
    parser.add_argument("--use-cost-reduced-scorer", action="store_true")
    parser.add_argument("--feature-cache-dir", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument(
        "--hash-mode",
        choices=("full", "sample", "metadata"),
        default="full",
        help="full hashes file contents; sample hashes size plus first/last window; metadata hashes size and xvecs shape",
    )
    parser.add_argument("--sample-bytes", type=int, default=DEFAULT_SAMPLE_BYTES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.expected_csv.exists():
        raise FileNotFoundError(f"missing expected CSV: {args.expected_csv}")
    if args.sample_bytes <= 0:
        raise ValueError("--sample-bytes must be positive")

    manifest = build_manifest(args)
    write_json(manifest, args.output_json)
    write_markdown(manifest, args.output_md, args)
    print(f"Wrote JSON: {args.output_json}")
    print(f"Wrote Markdown: {args.output_md}")
    print(json.dumps(manifest["summary"], indent=2, sort_keys=True))

    summary = manifest["summary"]
    if summary["missing_unique_input_files"] or summary["xvecs_shape_errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
