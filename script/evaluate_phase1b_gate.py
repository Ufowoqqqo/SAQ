#!/usr/bin/env python3
"""Evaluate the preregistered SAQ transform Phase-1b closure gate.

This script intentionally implements only the frozen CIFAR60k decision in
``docs/saq_transform_phase1b_external_replication_protocol_2026_07_10.md``.
It consumes the ordinary Phase-1 summarizer output plus the two view manifests
and raw runner prefixes, validates the matched artifact contract, and emits a
machine-readable decision and a compact paper-facing report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_BASE_SHA256 = "a7170faaa80a072cd603ed472104049ead87fbaff224e94a529021d161f8aea4"
EXPECTED_QUERY_SHA256 = "88109c80b4f4d779440422df89eb9242c23d8cd4021682782294c50c57cca6d7"
EXPECTED_N = 60_000
EXPECTED_D = 512
EXPECTED_Q = 1_000
EXPECTED_K = 512
EXPECTED_NPROBE = 16
EXPECTED_TOPK = 100
EXPECTED_BOOTSTRAP_REPLICATES = 10_000
EXPECTED_BOOTSTRAP_SEED = 20260710
EXPECTED_PLAN_CONTROL = "frozen-pca"
EXPECTED_EXACT_SCOPE = "canonical_raw_float64_squared_L2"
EXPECTED_RUNTIME_STATE_BYTES = (EXPECTED_D * EXPECTED_D + EXPECTED_D) * 4
EXPECTED_ROTATIONS = {f"seed{seed}" for seed in range(10)} | {"off"}
PRIMARY_STAGES = ("fast_all", "accurate_prefix_1", "full")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no CSV header")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path} contains no data rows")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nested(value: Mapping[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            raise ValueError(f"manifest is missing {'.'.join(keys)}")
        current = current[key]
    return current


def as_float(row: Mapping[str, str], column: str) -> float:
    try:
        value = float(row[column])
    except (KeyError, ValueError) as error:
        raise ValueError(f"invalid or missing numeric column {column!r}") from error
    if not math.isfinite(value):
        raise ValueError(f"column {column!r} is not finite")
    return value


def as_int(row: Mapping[str, str], column: str) -> int:
    value = as_float(row, column)
    if value != int(value):
        raise ValueError(f"column {column!r} is not integral: {value}")
    return int(value)


def bool_text(row: Mapping[str, str], column: str) -> bool:
    try:
        value = row[column].strip().lower()
    except KeyError as error:
        raise ValueError(f"missing boolean column {column!r}") from error
    if value not in {"true", "false"}:
        raise ValueError(f"column {column!r} is not true/false: {value!r}")
    return value == "true"


def check(name: str, condition: bool, detail: str) -> dict[str, object]:
    return {"name": name, "pass": bool(condition), "detail": detail}


def validate_manifest_pair(
    current: Mapping[str, Any], residual: Mapping[str, Any]
) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for label, manifest in (("current_pca", current), ("residual_pca", residual)):
        raw_base = nested(manifest, "inputs", "raw_base")
        raw_query = nested(manifest, "inputs", "raw_query")
        checks.extend(
            [
                check(
                    f"{label}_raw_base",
                    raw_base.get("sha256") == EXPECTED_BASE_SHA256
                    and raw_base.get("count") == EXPECTED_N
                    and raw_base.get("dimension") == EXPECTED_D,
                    f"sha256={raw_base.get('sha256')} shape={raw_base.get('count')}x{raw_base.get('dimension')}",
                ),
                check(
                    f"{label}_raw_query",
                    raw_query.get("sha256") == EXPECTED_QUERY_SHA256
                    and raw_query.get("count") == EXPECTED_Q
                    and raw_query.get("dimension") == EXPECTED_D,
                    f"sha256={raw_query.get('sha256')} shape={raw_query.get('count')}x{raw_query.get('dimension')}",
                ),
            ]
        )
        isometry = float(
            nested(
                manifest,
                "diagnostics",
                "isometry",
                "squared_distance_relative_l2_error",
            )
        )
        checks.append(
            check(
                f"{label}_isometry",
                math.isfinite(isometry) and isometry <= 1e-5,
                f"relative_l2={isometry:.6e}",
            )
        )
        runtime = nested(manifest, "transform", "runtime_state_contract")
        checks.append(
            check(
                f"{label}_runtime_state",
                runtime.get("dtype") == "float32"
                and runtime.get("operator_shape") == [EXPECTED_D, EXPECTED_D]
                and runtime.get("mean_shape") == [EXPECTED_D]
                and runtime.get("total_bytes") == EXPECTED_RUNTIME_STATE_BYTES,
                f"dtype={runtime.get('dtype')} bytes={runtime.get('total_bytes')}",
            )
        )
        construction = nested(
            manifest, "shared_provenance", "historical_ivf_construction"
        )
        checks.append(
            check(
                f"{label}_historical_ivf_provenance",
                construction.get("sample_size") == EXPECTED_N
                and construction.get("dimension") == EXPECTED_D
                and construction.get("k") == EXPECTED_K
                and construction.get("cluster_dims") == 64
                and construction.get("iterations") == 4
                and construction.get("seed") == 0
                and construction.get("empty_clusters") == 0,
                (
                    f"sample={construction.get('sample_size')} K={construction.get('k')} "
                    f"cluster_dims={construction.get('cluster_dims')} "
                    f"iterations={construction.get('iterations')} seed={construction.get('seed')}"
                ),
            )
        )

    for artifact in ("cluster_ids", "fixed_probe_clusters"):
        current_sha = nested(current, "outputs", artifact, "sha256")
        residual_sha = nested(residual, "outputs", artifact, "sha256")
        checks.append(
            check(
                f"matched_{artifact}",
                current_sha == residual_sha,
                f"current={current_sha} residual={residual_sha}",
            )
        )
    current_runtime = nested(current, "transform", "runtime_state_contract")
    residual_runtime = nested(residual, "transform", "runtime_state_contract")
    checks.append(
        check(
            "matched_runtime_state",
            current_runtime == residual_runtime,
            f"current_bytes={current_runtime.get('total_bytes')} residual_bytes={residual_runtime.get('total_bytes')}",
        )
    )
    return checks


def validate_raw_outputs(
    current_prefix: Path, residual_prefix: Path
) -> tuple[list[dict[str, object]], dict[str, str]]:
    checks: list[dict[str, object]] = []
    config_sets: dict[str, list[dict[str, str]]] = {}
    for label, prefix in (("current_pca", current_prefix), ("residual_pca", residual_prefix)):
        configs = load_csv(Path(f"{prefix}.configs.csv"))
        queries = load_csv(Path(f"{prefix}.query_stages.csv"))
        segments = load_csv(Path(f"{prefix}.segment_errors.csv"))
        config_sets[label] = configs
        controls = {row["rotation_control"] for row in configs}
        plans = {row["plan_control"] for row in configs}
        plan_strings = {row["plan"] for row in configs}
        scopes = {row["exact_distance_scope"] for row in configs}
        structural = all(
            as_int(row, "N") == EXPECTED_N
            and as_int(row, "D") == EXPECTED_D
            and as_int(row, "K") == EXPECTED_K
            and as_int(row, "queries") == EXPECTED_Q
            and as_int(row, "fixed_probes_per_query") == EXPECTED_NPROBE
            and as_int(row, "topk_requested") == EXPECTED_TOPK
            for row in configs
        )
        no_nonfinite = all(as_int(row, "nonfinite_count") == 0 for row in queries)
        no_nonfinite = no_nonfinite and all(
            as_int(row, "nonfinite_count") == 0 for row in segments
        )
        min_candidates = min(as_int(row, "candidate_count") for row in queries)
        checks.extend(
            [
                check(
                    f"{label}_config_grid",
                    len(configs) == 11
                    and controls == EXPECTED_ROTATIONS
                    and plans == {EXPECTED_PLAN_CONTROL},
                    f"configs={len(configs)} controls={sorted(controls)} plans={sorted(plans)}",
                ),
                check(
                    f"{label}_structure",
                    structural and len(plan_strings) == 1 and len(next(iter(plan_strings)).split("|")) >= 2,
                    f"plans={sorted(plan_strings)}",
                ),
                check(
                    f"{label}_canonical_exact_scope",
                    scopes == {EXPECTED_EXACT_SCOPE},
                    f"scopes={sorted(scopes)}",
                ),
                check(
                    f"{label}_finite_and_candidate_count",
                    no_nonfinite and min_candidates >= EXPECTED_TOPK,
                    f"nonfinite={not no_nonfinite} min_candidates={min_candidates}",
                ),
            ]
        )

    current_by_control = {
        row["rotation_control"]: row for row in config_sets["current_pca"]
    }
    residual_by_control = {
        row["rotation_control"]: row for row in config_sets["residual_pca"]
    }
    matched = True
    mismatches: list[str] = []
    for control in sorted(EXPECTED_ROTATIONS):
        left = current_by_control.get(control)
        right = residual_by_control.get(control)
        if left is None or right is None:
            matched = False
            mismatches.append(f"{control}:missing")
            continue
        for column in ("plan", "nominal_code_bits_per_vector", "actual_serialized_index_bytes"):
            if left[column] != right[column]:
                matched = False
                mismatches.append(f"{control}:{column}")
    checks.append(
        check(
            "matched_plan_and_serialized_bytes",
            matched,
            "none" if not mismatches else ",".join(mismatches),
        )
    )

    reference_paths = {
        "current_pca": Path(f"{current_prefix}.query_reference.csv"),
        "residual_pca": Path(f"{residual_prefix}.query_reference.csv"),
    }
    reference_hashes = {label: sha256_file(path) for label, path in reference_paths.items()}
    checks.append(
        check(
            "matched_canonical_query_reference",
            len(set(reference_hashes.values())) == 1,
            f"hashes={reference_hashes}",
        )
    )
    reference_rows = load_csv(reference_paths["current_pca"])
    reference_queries = {as_int(row, "query") for row in reference_rows}
    checks.append(
        check(
            "canonical_query_reference_coverage",
            reference_queries == set(range(EXPECTED_Q)),
            f"queries={len(reference_queries)} rows={len(reference_rows)}",
        )
    )
    return checks, reference_hashes


def select_row(
    rows: Sequence[Mapping[str, str]], rotation_group: str, stage: str
) -> Mapping[str, str]:
    matches = [
        row
        for row in rows
        if row.get("transform") == "residual_pca"
        and row.get("baseline") == "current_pca"
        and row.get("plan_control") == EXPECTED_PLAN_CONTROL
        and row.get("rotation_group") == rotation_group
        and row.get("stage") == stage
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one paired row for {rotation_group}/{stage}, found {len(matches)}"
        )
    return matches[0]


def metric_snapshot(row: Mapping[str, str], metric: str) -> dict[str, object]:
    return {
        "delta": as_float(row, f"{metric}_transform_minus_pca"),
        "ci95_low": as_float(row, f"{metric}_ci95_low"),
        "ci95_high": as_float(row, f"{metric}_ci95_high"),
        "ci_evidence": row[f"{metric}_ci_evidence"],
        "seeds_favoring_residual": as_int(
            row, f"{metric}_seeds_favoring_transform"
        ),
    }


def evaluate_scientific_gates(
    paired_rows: Sequence[Mapping[str, str]]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    seeded = {
        stage: select_row(paired_rows, "seed_average", stage)
        for stage in PRIMARY_STAGES
    }
    off = {
        stage: select_row(paired_rows, "off", stage)
        for stage in ("accurate_prefix_1", "full")
    }
    for row in [*seeded.values(), *off.values()]:
        if as_int(row, "bootstrap_replicates") != EXPECTED_BOOTSTRAP_REPLICATES:
            raise ValueError("bootstrap replicate count differs from preregistration")
        if as_int(row, "bootstrap_seed") != EXPECTED_BOOTSTRAP_SEED:
            raise ValueError("bootstrap seed differs from preregistration")
        if not bool_text(row, "matched_budget"):
            raise ValueError("paired row is not matched-plan/logical-byte/serialized-byte")

    gate_a_conditions: dict[str, bool] = {}
    gate_a_metrics: dict[str, Any] = {}
    for stage in ("accurate_prefix_1", "full"):
        gate_a_metrics[stage] = {}
        for metric in ("mean_per_query_candidate_rmse", "pooled_candidate_rmse"):
            snapshot = metric_snapshot(seeded[stage], metric)
            gate_a_metrics[stage][metric] = snapshot
            gate_a_conditions[f"{stage}_{metric}_ci_below_zero"] = (
                float(snapshot["ci95_high"]) < 0.0
            )
            gate_a_conditions[f"{stage}_{metric}_at_least_8_of_10"] = (
                int(snapshot["seeds_favoring_residual"]) >= 8
            )
        off_delta = as_float(
            off[stage], "mean_per_query_candidate_rmse_transform_minus_pca"
        )
        gate_a_metrics[stage]["rotation_off_mean_query_rmse_delta"] = off_delta
        gate_a_conditions[f"{stage}_rotation_off_direction"] = off_delta < 0.0
    gate_a = {
        "pass": all(gate_a_conditions.values()),
        "conditions": gate_a_conditions,
        "metrics": gate_a_metrics,
    }

    boundary = metric_snapshot(
        seeded["accurate_prefix_1"], "boundary_inversion_rate"
    )
    topk = metric_snapshot(seeded["accurate_prefix_1"], "topk_agreement")
    gate_b_conditions = {
        "boundary_ci_below_zero": float(boundary["ci95_high"]) < 0.0,
        "boundary_at_least_8_of_10": int(boundary["seeds_favoring_residual"]) >= 8,
        "top100_point_no_harm": float(topk["delta"]) >= 0.0,
    }
    gate_b = {
        "evaluated": bool(gate_a["pass"]),
        "pass": bool(gate_a["pass"]) and all(gate_b_conditions.values()),
        "conditions": gate_b_conditions,
        "metrics": {"boundary_inversion_rate": boundary, "topk_agreement": topk},
    }

    gate_c_conditions: dict[str, bool] = {}
    gate_c_metrics: dict[str, Any] = {}
    for stage, metrics in (
        (
            "fast_all",
            (
                "mean_per_query_candidate_rmse",
                "pooled_candidate_rmse",
                "boundary_inversion_rate",
                "topk_agreement",
            ),
        ),
        ("full", ("boundary_inversion_rate", "topk_agreement")),
    ):
        gate_c_metrics[stage] = {}
        for metric in metrics:
            snapshot = metric_snapshot(seeded[stage], metric)
            gate_c_metrics[stage][metric] = snapshot
            gate_c_conditions[f"{stage}_{metric}_no_significant_harm"] = (
                snapshot["ci_evidence"] != "favors_pca"
            )
    gate_c_evaluated = bool(gate_a["pass"] and gate_b["pass"])
    gate_c = {
        "evaluated": gate_c_evaluated,
        "pass": gate_c_evaluated and all(gate_c_conditions.values()),
        "conditions": gate_c_conditions,
        "metrics": gate_c_metrics,
    }

    if not gate_a["pass"]:
        decision = "close_one_dataset_estimator_effect"
    elif not gate_b["pass"]:
        decision = "narrow_estimator_mismatch_replicated_but_close_for_absent_ranking_evidence"
    elif not gate_c["pass"]:
        decision = "ranking_signal_with_stage_tradeoff_close_global_replacement"
    else:
        decision = "permit_one_counterfactual_segment_bit_mechanism_analysis_only"
    return gate_a, gate_b, gate_c, decision


def render_markdown(report: Mapping[str, Any]) -> str:
    artifact = report["artifact_gate"]
    lines = [
        "# SAQ Transform Phase 1b Gate Result",
        "",
        f"- Artifact gate: **{'PASS' if artifact['pass'] else 'FAIL'}**",
        f"- Gate A, narrow estimator replication: **{'PASS' if report['gate_a']['pass'] else 'FAIL'}**",
        (
            "- Gate B, practical ranking evidence: **"
            + ("NOT EVALUATED" if not report["gate_b"]["evaluated"] else ("PASS" if report["gate_b"]["pass"] else "FAIL"))
            + "**"
        ),
        (
            "- Gate C, progressive no-harm: **"
            + ("NOT EVALUATED" if not report["gate_c"]["evaluated"] else ("PASS" if report["gate_c"]["pass"] else "FAIL"))
            + "**"
        ),
        f"- Decision: `{report['decision']}`",
        "",
        "## Artifact Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for item in artifact["checks"]:
        detail = str(item["detail"]).replace("|", "\\|")
        lines.append(
            f"| `{item['name']}` | {'PASS' if item['pass'] else 'FAIL'} | {detail} |"
        )
    lines.extend(
        [
            "",
            "## Frozen Gate Conditions",
            "",
        ]
    )
    for gate_name in ("gate_a", "gate_b", "gate_c"):
        gate = report[gate_name]
        lines.append(f"### {gate_name.replace('_', ' ').title()}")
        lines.append("")
        for name, passed in gate["conditions"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'}: `{name}`")
        lines.append("")
    lines.extend(
        [
            "## Interpretation Boundary",
            "",
            "This is a fixed-candidate estimator replication. It does not establish an ",
            "end-to-end IVF Recall-QPS result, a learned-transform contribution, or a claim ",
            "about full-dimensional IVF partition quality.",
            "",
        ]
    )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    current_manifest = load_json(args.current_manifest)
    residual_manifest = load_json(args.residual_manifest)
    checks = validate_manifest_pair(current_manifest, residual_manifest)
    raw_checks, reference_hashes = validate_raw_outputs(
        args.current_result_prefix, args.residual_result_prefix
    )
    checks.extend(raw_checks)
    artifact_pass = all(bool(item["pass"]) for item in checks)

    paired_rows = load_csv(Path(f"{args.summary_prefix}.paired_vs_pca.csv"))
    if artifact_pass:
        gate_a, gate_b, gate_c, decision = evaluate_scientific_gates(paired_rows)
    else:
        empty_gate = {"evaluated": False, "pass": False, "conditions": {}, "metrics": {}}
        gate_a = dict(empty_gate)
        gate_b = dict(empty_gate)
        gate_c = dict(empty_gate)
        decision = "invalid_replication_artifact_gate_failed"
    return {
        "protocol": "docs/saq_transform_phase1b_external_replication_protocol_2026_07_10.md",
        "dataset": "cifar60k",
        "artifact_gate": {
            "pass": artifact_pass,
            "checks": checks,
            "query_reference_sha256": reference_hashes,
        },
        "gate_a": gate_a,
        "gate_b": gate_b,
        "gate_c": gate_c,
        "decision": decision,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-prefix", type=Path, required=True)
    parser.add_argument("--current-manifest", type=Path, required=True)
    parser.add_argument("--residual-manifest", type=Path, required=True)
    parser.add_argument("--current-result-prefix", type=Path, required=True)
    parser.add_argument("--residual-result-prefix", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run(args)
    except (FileNotFoundError, KeyError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = Path(f"{args.output_prefix}.json")
    markdown_path = Path(f"{args.output_prefix}.md")
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"artifact_gate={'PASS' if report['artifact_gate']['pass'] else 'FAIL'}")
    print(f"decision={report['decision']}")
    print(f"json={json_path}")
    print(f"markdown={markdown_path}")
    return 0 if report["artifact_gate"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
