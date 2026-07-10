import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "script" / "summarize_phase1_transform.py"
SPEC = importlib.util.spec_from_file_location("summarize_phase1_transform", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


QUERY_FIELDS = [
    "transform",
    "config_id",
    "plan_control",
    "rotation_control",
    "rotation_seed",
    "query",
    "stage",
    "stage_semantics",
    "candidate_count",
    "finite_count",
    "nonfinite_count",
    "bias",
    "mae",
    "rmse",
    "abs_relative_eps1e-12_p50",
    "abs_relative_eps1e-12_p90",
    "abs_relative_eps1e-12_p99",
    "topk_used",
    "fixed_candidate_topk_agreement",
    "exact_best_estimated_rank",
    "strict_exact_topk_vs_outside_boundary_inversions",
    "boundary_pairs",
    "strict_boundary_inversion_rate",
    "logical_factor_bytes_per_candidate",
    "logical_fast_code_bytes_per_candidate",
    "logical_long_code_bytes_per_candidate",
    "logical_long_factor_bytes_per_candidate",
    "logical_total_requested_bytes_per_candidate",
    "logical_byte_model",
]

SEGMENT_FIELDS = [
    "transform",
    "config_id",
    "plan_control",
    "rotation_control",
    "rotation_seed",
    "segment",
    "offset",
    "dimensions",
    "bits",
    "distance_mode",
    "mode_semantics",
    "total_count",
    "finite_count",
    "nonfinite_count",
    "bias",
    "mae",
    "rmse",
    "abs_relative_eps1e-12_p50",
    "abs_relative_eps1e-12_p90",
    "abs_relative_eps1e-12_p99",
    "transform_variance_sum",
    "pca_variance_sum",
    "transform_planner_proxy",
    "pca_planner_proxy",
    "true_residual_ip_mean",
    "true_residual_ip_abs_mean",
    "true_residual_ip_sq_mean",
    "accurate_distance_implied_ip_abs_error_mean",
    "accurate_distance_implied_ip_sq_error_mean",
]

CONFIG_FIELDS = [
    "transform",
    "config_id",
    "plan_control",
    "rotation_control",
    "rotation_enabled",
    "rotation_seed",
    "seed_scope",
    "N",
    "D",
    "K",
    "queries",
    "fixed_probes_per_query",
    "topk_requested",
    "nominal_B",
    "vars_bound_m",
    "segments",
    "plan",
    "nominal_code_bits_per_vector",
    "transform_planner_proxy_total",
    "pca_planner_proxy_total",
    "actual_serialized_index_bytes",
    "actual_serialized_index_bytes_per_vector",
    "build_time_s",
    "serialization_time_s",
    "measurement_time_s",
    "candidate_evaluations",
    "exact_distance_scope",
]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class SummarizePhase1TransformTest(unittest.TestCase):
    def make_prefix(self, root: Path, transform: str, quality_delta: float) -> Path:
        prefix = root / transform
        query_rows: list[dict[str, object]] = []
        config_rows: list[dict[str, object]] = []
        segment_rows: list[dict[str, object]] = []
        stages = [
            ("vars_conservative_lower_bound_all", 4, 0, 0, 0),
            ("fast_prefix_1", 4, 8, 0, 0),
            ("fast_all", 4, 16, 0, 0),
            ("accurate_prefix_1", 4, 16, 8, 8),
            ("full", 4, 16, 24, 24),
        ]
        rotations = [(f"seed{seed}", seed) for seed in range(10)] + [("off", -1)]
        for rotation_control, rotation_seed in rotations:
            config_id = f"{transform}__native__{rotation_control}"
            serialized_bytes = 1000
            config_rows.append(
                {
                    "transform": transform,
                    "config_id": config_id,
                    "plan_control": "native",
                    "rotation_control": rotation_control,
                    "rotation_enabled": int(rotation_seed >= 0),
                    "rotation_seed": rotation_seed,
                    "seed_scope": "synthetic",
                    "N": 100,
                    "D": 192,
                    "K": 4,
                    "queries": 3,
                    "fixed_probes_per_query": 2,
                    "topk_requested": 2,
                    "nominal_B": 4,
                    "vars_bound_m": 4,
                    "segments": 3,
                    "plan": "0:64@4b|64:128@4b|128:192@4b",
                    "nominal_code_bits_per_vector": 768,
                    "transform_planner_proxy_total": 6,
                    "pca_planner_proxy_total": 6,
                    "actual_serialized_index_bytes": serialized_bytes,
                    "actual_serialized_index_bytes_per_vector": serialized_bytes / 100,
                    "build_time_s": 1,
                    "serialization_time_s": 0.1,
                    "measurement_time_s": 2,
                    "candidate_evaluations": 60,
                    "exact_distance_scope": "transform_view_squared_L2",
                }
            )
            seed_noise = 0 if rotation_seed < 0 else (rotation_seed - 4.5) * 0.01
            for query in range(3):
                for stage, factor_bytes, fast_bytes, long_bytes, long_factor_bytes in stages:
                    baseline_rmse = 10 + query
                    baseline_mae = 5 + query
                    query_rows.append(
                        {
                            "transform": transform,
                            "config_id": config_id,
                            "plan_control": "native",
                            "rotation_control": rotation_control,
                            "rotation_seed": rotation_seed,
                            "query": query,
                            "stage": stage,
                            "stage_semantics": (
                                "conservative_lower_bound_not_ordinary_distance_estimator"
                                if stage.startswith("vars_")
                                else "progressive_distance_estimate"
                            ),
                            "candidate_count": 20,
                            "finite_count": 20,
                            "nonfinite_count": 0,
                            "bias": quality_delta + seed_noise,
                            "mae": baseline_mae + quality_delta / 2 + seed_noise,
                            "rmse": baseline_rmse + quality_delta + seed_noise,
                            "abs_relative_eps1e-12_p50": 0.1,
                            "abs_relative_eps1e-12_p90": 0.2,
                            "abs_relative_eps1e-12_p99": 0.3,
                            "topk_used": 2,
                            "fixed_candidate_topk_agreement": 0.8 - quality_delta * 0.05,
                            "exact_best_estimated_rank": 2 + quality_delta,
                            "strict_exact_topk_vs_outside_boundary_inversions": 2,
                            "boundary_pairs": 36,
                            "strict_boundary_inversion_rate": 0.1 + quality_delta * 0.01,
                            "logical_factor_bytes_per_candidate": factor_bytes,
                            "logical_fast_code_bytes_per_candidate": fast_bytes,
                            "logical_long_code_bytes_per_candidate": long_bytes,
                            "logical_long_factor_bytes_per_candidate": long_factor_bytes,
                            "logical_total_requested_bytes_per_candidate": (
                                factor_bytes + fast_bytes + long_bytes + long_factor_bytes
                            ),
                            "logical_byte_model": "synthetic_cumulative",
                        }
                    )
            for segment in range(3):
                error = float(segment + 1) + quality_delta * 0.01
                segment_rows.append(
                    {
                        "transform": transform,
                        "config_id": config_id,
                        "plan_control": "native",
                        "rotation_control": rotation_control,
                        "rotation_seed": rotation_seed,
                        "segment": segment,
                        "offset": segment * 64,
                        "dimensions": 64,
                        "bits": 4,
                        "distance_mode": "accurate_full_code",
                        "mode_semantics": "full_code_distance_estimate",
                        "total_count": 60,
                        "finite_count": 60,
                        "nonfinite_count": 0,
                        "bias": 0,
                        "mae": error,
                        "rmse": error * 2,
                        "abs_relative_eps1e-12_p50": 0.1,
                        "abs_relative_eps1e-12_p90": 0.2,
                        "abs_relative_eps1e-12_p99": 0.3,
                        "transform_variance_sum": segment + 1,
                        "pca_variance_sum": segment + 1,
                        "transform_planner_proxy": segment + 1,
                        "pca_planner_proxy": segment + 1,
                        "true_residual_ip_mean": 0,
                        "true_residual_ip_abs_mean": 1,
                        "true_residual_ip_sq_mean": 1,
                        "accurate_distance_implied_ip_abs_error_mean": error * 3,
                        "accurate_distance_implied_ip_sq_error_mean": (error * 3) ** 2,
                    }
                )
        write_csv(Path(f"{prefix}.query_stages.csv"), QUERY_FIELDS, query_rows)
        write_csv(Path(f"{prefix}.segment_errors.csv"), SEGMENT_FIELDS, segment_rows)
        write_csv(Path(f"{prefix}.configs.csv"), CONFIG_FIELDS, config_rows)
        return prefix

    def add_matched_plan_controls(self, prefix: Path) -> None:
        for suffix, fields in (
            ("query_stages", QUERY_FIELDS),
            ("segment_errors", SEGMENT_FIELDS),
            ("configs", CONFIG_FIELDS),
        ):
            path = Path(f"{prefix}.{suffix}.csv")
            native_rows = read_csv(path)
            rows: list[dict[str, object]] = list(native_rows)
            for plan_control in ("frozen-pca", "uniform"):
                for native in native_rows:
                    cloned: dict[str, object] = dict(native)
                    cloned["plan_control"] = plan_control
                    cloned["config_id"] = native["config_id"].replace(
                        "__native__", f"__{plan_control}__"
                    )
                    rows.append(cloned)
            write_csv(path, fields, rows)

    def make_experiment(self, root: Path) -> list[str]:
        specs = []
        for transform, delta in (
            ("current_pca", 0.0),
            ("identity", -1.0),
            ("residual_pca", 0.0),
            ("random_orthogonal", 1.0),
        ):
            prefix = self.make_prefix(root, transform, delta)
            self.add_matched_plan_controls(prefix)
            specs.append(f"{transform}={prefix}")
        return specs

    def test_seed_averaging_bootstrap_prefix_curves_and_proxy_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            specs = self.make_experiment(root)

            output = root / "summary"
            paths = MODULE.summarize(
                specs,
                output,
                bootstrap_replicates=200,
                bootstrap_seed=17,
            )
            for path in paths.values():
                self.assertTrue(path.is_file(), path)

            with paths["provenance"].open(encoding="utf-8") as handle:
                provenance = json.load(handle)
            self.assertEqual(provenance["bootstrap_replicates"], 200)
            self.assertEqual(provenance["bootstrap_seed"], 17)
            self.assertEqual(
                provenance["inputs"]["current_pca"]["configs"]["sha256"],
                MODULE.sha256_file(Path(f"{root / 'current_pca'}.configs.csv")),
            )
            self.assertEqual(
                provenance["outputs"]["paired_vs_pca"]["sha256"],
                MODULE.sha256_file(paths["paired_vs_pca"]),
            )

            curves = read_csv(paths["stage_curves"])
            identity_seeded = [
                row
                for row in curves
                if row["transform"] == "identity"
                and row["plan_control"] == "native"
                and row["rotation_group"] == "seed_average"
                and row["stage"] == "accurate_prefix_1"
            ]
            self.assertEqual(len(identity_seeded), 1)
            self.assertEqual(identity_seeded[0]["rotation_seeds"], "0|1|2|3|4|5|6|7|8|9")
            self.assertAlmostEqual(
                float(identity_seeded[0]["mean_query_logical_total_requested_bytes_per_candidate"]),
                36.0,
            )
            self.assertTrue(
                any(
                    row["transform"] == "identity"
                    and row["plan_control"] == "native"
                    and row["rotation_group"] == "off"
                    and row["stage"] == "full"
                    for row in curves
                )
            )

            paired = read_csv(paths["paired_vs_pca"])
            identity_full = next(
                row
                for row in paired
                if row["transform"] == "identity"
                and row["plan_control"] == "native"
                and row["rotation_group"] == "seed_average"
                and row["stage"] == "full"
            )
            self.assertAlmostEqual(
                float(identity_full["mean_per_query_candidate_rmse_transform_minus_pca"]),
                -1.0,
            )
            self.assertLess(
                float(identity_full["pooled_candidate_rmse_transform_minus_pca"]),
                -0.9,
            )
            self.assertEqual(
                identity_full["mean_per_query_candidate_rmse_ci_excludes_zero"],
                "true",
            )
            self.assertEqual(
                identity_full["mean_per_query_candidate_rmse_ci_evidence"],
                "favors_transform",
            )
            self.assertEqual(
                identity_full["descriptive_mean_rate_quality_relation"],
                "transform_partially_dominates_pca",
            )
            identity_prefix = next(
                row
                for row in paired
                if row["transform"] == "identity"
                and row["plan_control"] == "native"
                and row["rotation_group"] == "seed_average"
                and row["stage"] == "accurate_prefix_1"
            )
            self.assertEqual(
                identity_prefix["stage_match_type"],
                "matched_intermediate_family_and_bytes",
            )
            self.assertEqual(identity_prefix["matched_budget"], "true")

            per_seed = read_csv(paths["per_seed_effects"])
            rmse_seed_rows = [
                row
                for row in per_seed
                if row["transform"] == "identity"
                and row["plan_control"] == "native"
                and row["stage"] == "accurate_prefix_1"
                and row["metric"] == "mean_per_query_candidate_rmse"
            ]
            self.assertEqual(len(rmse_seed_rows), 11)
            self.assertEqual(
                {int(row["rotation_seed"]) for row in rmse_seed_rows},
                {*range(10), -1},
            )

            proxy = read_csv(paths["segment_proxy"])
            identity_proxy = next(
                row
                for row in proxy
                if row["transform"] == "identity"
                and row["plan_control"] == "native"
                and row["rotation_group"] == "seed_average"
            )
            self.assertAlmostEqual(
                float(identity_proxy["spearman_transform_proxy_vs_implied_ip_rmse"]),
                1.0,
            )
            self.assertEqual(
                identity_proxy[
                    "seedwise_spearman_transform_proxy_vs_implied_ip_mae_finite_count"
                ],
                "10",
            )

            markdown = paths["markdown"].read_text(encoding="utf-8")
            self.assertIn("does not make an automatic novelty", markdown)
            self.assertIn("descriptive only", markdown)

            second = root / "summary_again"
            second_paths = MODULE.summarize(
                specs,
                second,
                bootstrap_replicates=200,
                bootstrap_seed=17,
            )
            self.assertEqual(
                paths["paired_vs_pca"].read_text(encoding="utf-8"),
                second_paths["paired_vs_pca"].read_text(encoding="utf-8"),
            )

    def test_spearman_ties_and_incomplete_seed_grid(self) -> None:
        self.assertAlmostEqual(MODULE.spearman([1, 1, 2], [3, 3, 4]), 1.0)
        rows = []
        for seed in range(9):
            row = {column: "0" for column in QUERY_FIELDS}
            row.update(
                {
                    "transform": "current_pca",
                    "plan_control": "native",
                    "rotation_control": f"seed{seed}",
                    "rotation_seed": str(seed),
                    "query": "0",
                    "stage": "full",
                    "stage_semantics": "progressive_distance_estimate",
                    "logical_byte_model": "synthetic",
                }
            )
            rows.append(row)
        with self.assertRaisesRegex(ValueError, "cover 0..9 exactly"):
            MODULE.aggregate_query_seeds(rows)

    def test_pooled_rmse_recomputes_square_root_inside_bootstrap(self) -> None:
        # Mean per-query RMSE favors the transform: (0 + 10) / 2 < 6.
        # Correct pooled RMSE reverses the direction: sqrt((0^2 + 10^2)/2) > 6.
        observed, lower, upper = MODULE.paired_bootstrap_pooled_rmse_ci(
            [0.0, 100.0],
            [1.0, 1.0],
            [36.0, 36.0],
            [1.0, 1.0],
            replicates=500,
            seed=9,
        )
        self.assertGreater(observed, 1.0)
        self.assertLess(lower, 0.0)
        self.assertGreater(upper, 0.0)

    def test_zero_boundary_pairs_becomes_na(self) -> None:
        rows = []
        for seed in range(10):
            row = {column: "0" for column in QUERY_FIELDS}
            row.update(
                {
                    "transform": "current_pca",
                    "config_id": f"current_pca__native__seed{seed}",
                    "plan_control": "native",
                    "rotation_control": f"seed{seed}",
                    "rotation_seed": str(seed),
                    "query": "0",
                    "stage": "full",
                    "stage_semantics": "progressive_distance_estimate",
                    "candidate_count": "2",
                    "finite_count": "2",
                    "nonfinite_count": "0",
                    "topk_used": "2",
                    "boundary_pairs": "0",
                    "strict_boundary_inversion_rate": "0",
                    "logical_byte_model": "synthetic",
                }
            )
            rows.append(row)
        aggregated = MODULE.aggregate_query_seeds(rows)
        self.assertEqual(len(aggregated), 1)
        self.assertTrue(
            MODULE.math.isnan(aggregated[0]["strict_boundary_inversion_rate"])
        )

    def test_rejects_raw_contract_and_metadata_failures_before_averaging(self) -> None:
        cases = (
            "candidate_mean_cancellation",
            "nonfinite",
            "segment_nonfinite",
            "orphan",
            "frozen_plan",
            "bytes",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                specs = self.make_experiment(root)
                identity = root / "identity"
                query_path = Path(f"{identity}.query_stages.csv")
                segment_path = Path(f"{identity}.segment_errors.csv")
                config_path = Path(f"{identity}.configs.csv")
                if case in {"candidate_mean_cancellation", "nonfinite", "orphan"}:
                    rows = read_csv(query_path)
                    targets = [
                        row
                        for row in rows
                        if row["plan_control"] == "native"
                        and row["query"] == "0"
                        and row["stage"] == "full"
                    ]
                    if case == "candidate_mean_cancellation":
                        seed0 = next(row for row in targets if row["rotation_seed"] == "0")
                        seed1 = next(row for row in targets if row["rotation_seed"] == "1")
                        seed0.update(candidate_count="19", finite_count="19", boundary_pairs="34")
                        seed1.update(candidate_count="21", finite_count="21", boundary_pairs="38")
                    elif case == "nonfinite":
                        targets[0].update(finite_count="19", nonfinite_count="1")
                    else:
                        targets[0]["config_id"] = "missing_config"
                    write_csv(query_path, QUERY_FIELDS, rows)
                elif case == "segment_nonfinite":
                    rows = read_csv(segment_path)
                    rows[0].update(finite_count="59", nonfinite_count="1")
                    write_csv(segment_path, SEGMENT_FIELDS, rows)
                else:
                    rows = read_csv(config_path)
                    if case == "frozen_plan":
                        target = next(
                            row
                            for row in rows
                            if row["plan_control"] == "frozen-pca"
                            and row["rotation_seed"] == "0"
                        )
                        target["plan"] = "0:192@3b"
                    else:
                        seed0 = next(
                            row
                            for row in rows
                            if row["plan_control"] == "native"
                            and row["rotation_seed"] == "0"
                        )
                        seed1 = next(
                            row
                            for row in rows
                            if row["plan_control"] == "native"
                            and row["rotation_seed"] == "1"
                        )
                        seed0["actual_serialized_index_bytes"] = "899"
                        seed1["actual_serialized_index_bytes"] = "901"
                    write_csv(config_path, CONFIG_FIELDS, rows)

                patterns = {
                    "candidate_mean_cancellation": "structure differs across rotation",
                    "nonfinite": "non-finite candidate estimates",
                    "segment_nonfinite": "non-finite segment estimates",
                    "orphan": "orphan query row",
                    "frozen_plan": "matched-plan contract mismatch",
                    "bytes": "structural metadata actual_serialized_index_bytes",
                }
                with self.assertRaisesRegex(ValueError, patterns[case]):
                    MODULE.summarize(
                        specs,
                        root / "invalid_summary",
                        bootstrap_replicates=10,
                        bootstrap_seed=3,
                    )

    def test_rotation_control_must_match_seed(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match rotation_seed"):
            MODULE.rotation_group(
                {"rotation_control": "seed9", "rotation_seed": "3"}
            )

    def test_requires_identical_canonical_query_reference_inventories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            specs = self.make_experiment(root)
            inventory = "query,candidate_count,rank,base_id,exact_distance\n0,20,1,7,1.5\n"
            for transform in (
                "current_pca",
                "identity",
                "residual_pca",
                "random_orthogonal",
            ):
                Path(f"{root / transform}.query_reference.csv").write_text(
                    inventory, encoding="utf-8"
                )
            MODULE.summarize(
                specs,
                root / "valid_reference_summary",
                bootstrap_replicates=10,
                bootstrap_seed=3,
            )

            Path(f"{root / 'residual_pca'}.query_reference.csv").write_text(
                inventory.replace(",7,", ",8,"), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                ValueError, "canonical query-reference inventory differs"
            ):
                MODULE.summarize(
                    specs,
                    root / "invalid_reference_summary",
                    bootstrap_replicates=10,
                    bootstrap_seed=3,
                )


if __name__ == "__main__":
    unittest.main()
