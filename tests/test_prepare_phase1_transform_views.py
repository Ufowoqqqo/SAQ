import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "script" / "prepare_phase1_transform_views.py"
SPEC = importlib.util.spec_from_file_location("prepare_phase1_transform_views", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def squared_distances(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return np.sum(np.square(values[:, None, :] - values[None, :, :]), axis=2)


class PreparePhase1TransformViewsTest(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, np.ndarray, np.ndarray]:
        rng = np.random.default_rng(20260710)
        dataset = "toy"
        count = 192
        query_count = 24
        dim = 8
        k = 6

        input_directory = root / dataset
        input_directory.mkdir(parents=True)
        raw_base = rng.normal(size=(count, dim)).astype(np.float32)
        raw_query = rng.normal(size=(query_count, dim)).astype(np.float32)
        raw_centroids = rng.normal(size=(k, dim)).astype(np.float64)
        cluster_ids = rng.integers(0, k, size=(count, 1), dtype=np.int32)

        mean = raw_base.astype(np.float64).mean(axis=0)
        operator = MODULE.random_orthogonal_matrix(dim, 91)
        pca_base = ((raw_base.astype(np.float64) - mean) @ operator).astype(np.float32)
        pca_query = ((raw_query.astype(np.float64) - mean) @ operator).astype(np.float32)
        pca_centroids = ((raw_centroids - mean) @ operator).astype(np.float32)

        MODULE.write_fvecs(
            input_directory / f"{dataset}_base.fvecs", raw_base, chunk_rows=32
        )
        MODULE.write_fvecs(
            input_directory / f"{dataset}_base_pca.fvecs", pca_base, chunk_rows=32
        )
        MODULE.write_fvecs(
            input_directory / f"{dataset}_query.fvecs", raw_query, chunk_rows=32
        )
        MODULE.write_fvecs(
            input_directory / f"{dataset}_query_pca.fvecs", pca_query, chunk_rows=32
        )
        MODULE.write_fvecs(
            input_directory / f"{dataset}_centroid_{k}_pca.fvecs",
            pca_centroids,
            chunk_rows=32,
        )
        MODULE.write_ivecs(
            input_directory / f"{dataset}_cluster_id_{k}.ivecs",
            cluster_ids,
            chunk_rows=32,
        )
        MODULE.write_fvecs(
            input_directory / f"{dataset}_base_pca.vars.fvecs",
            np.var(pca_base, axis=0).reshape(1, -1),
            chunk_rows=32,
        )
        return input_directory, raw_base, raw_centroids

    def test_materializes_complete_isometric_views_and_fixed_probes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_directory, raw_base, _ = self.make_fixture(root)
            output_parent = root / "views"
            arguments = [
                "--dataset",
                "toy",
                "--input-dir",
                str(input_directory),
                "--output-parent",
                str(output_parent),
                "--k",
                "6",
                "--random-seeds",
                "7",
                "--chunk-rows",
                "32",
                "--procrustes-fit-rows",
                "96",
                "--procrustes-validation-rows",
                "48",
                "--probe-query-count",
                "12",
                "--nprobe",
                "3",
                "--isometry-pairs",
                "16",
            ]
            self.assertEqual(MODULE.main(arguments), 0)

            view_names = [
                "toy_phase1_identity",
                "toy_phase1_current_pca",
                "toy_phase1_residual_pca",
                "toy_phase1_random_seed7",
            ]
            fixed_probe_arrays = []
            raw_distances = squared_distances(raw_base[:16])
            for view_name in view_names:
                directory = output_parent / view_name
                base_path = directory / f"{view_name}_base.fvecs"
                query_path = directory / f"{view_name}_query.fvecs"
                centroid_path = directory / f"{view_name}_centroid_6.fvecs"
                variance_path = directory / f"{view_name}_base.vars.fvecs"
                cluster_path = directory / f"{view_name}_cluster_id_6.ivecs"
                operator_path = directory / f"{view_name}_transform.npz"
                probe_path = directory / (
                    f"{view_name}_fixed_probe_clusters_q12_nprobe3.ivecs"
                )
                manifest_path = directory / f"{view_name}_manifest.json"
                for path in (
                    base_path,
                    query_path,
                    centroid_path,
                    variance_path,
                    cluster_path,
                    operator_path,
                    probe_path,
                    manifest_path,
                ):
                    self.assertTrue(path.exists(), path)

                transformed = np.asarray(MODULE.open_fvecs(base_path)[:16])
                np.testing.assert_allclose(
                    squared_distances(transformed), raw_distances, rtol=2e-5, atol=2e-5
                )
                fixed_probe_arrays.append(np.asarray(MODULE.open_ivecs(probe_path)))

                with np.load(operator_path) as operator_data:
                    operator = operator_data["operator"]
                    np.testing.assert_allclose(
                        operator.T @ operator,
                        np.eye(operator.shape[0]),
                        rtol=1e-11,
                        atol=1e-11,
                    )
                with manifest_path.open(encoding="utf-8") as handle:
                    manifest = json.load(handle)
                self.assertFalse(manifest["research_contract"]["dimension_reduction"])
                self.assertEqual(
                    manifest["research_contract"]["operator_scope"],
                    "one dataset-level affine orthogonal transform",
                )
                self.assertEqual(len(manifest["inputs"]["raw_base"]["sha256"]), 64)
                self.assertEqual(len(manifest["outputs"]["base"]["sha256"]), 64)
                self.assertEqual(
                    manifest["diagnostics"]["fixed_probe_recomputed_in_view"][
                        "exact_order_fraction"
                    ],
                    1.0,
                )

            for probes in fixed_probe_arrays[1:]:
                np.testing.assert_array_equal(probes, fixed_probe_arrays[0])

            current_base = (
                output_parent
                / "toy_phase1_current_pca"
                / "toy_phase1_current_pca_base.fvecs"
            )
            current_query = (
                output_parent
                / "toy_phase1_current_pca"
                / "toy_phase1_current_pca_query.fvecs"
            )
            self.assertTrue(current_base.is_symlink())
            self.assertTrue(current_query.is_symlink())

    def test_recovery_gate_rejects_non_affine_paired_artifact(self) -> None:
        rng = np.random.default_rng(7)
        raw_base = rng.normal(size=(160, 7)).astype(np.float32)
        raw_query = rng.normal(size=(20, 7)).astype(np.float32)
        mean = raw_base.astype(np.float64).mean(axis=0)
        operator = MODULE.random_orthogonal_matrix(7, 3)
        pca_base = ((raw_base.astype(np.float64) - mean) @ operator).astype(np.float32)
        pca_query = ((raw_query.astype(np.float64) - mean) @ operator).astype(np.float32)
        pca_base[:, 0] += 0.01 * np.square(raw_base[:, 0])

        with self.assertRaisesRegex(ValueError, "refusing to invert PCA centroids"):
            MODULE.recover_affine_orthogonal_transform(
                raw_base,
                pca_base,
                raw_query,
                pca_query,
                fit_rows=80,
                validation_rows=40,
                max_relative_frobenius_error=1e-6,
                max_absolute_error=1e-6,
                chunk_rows=32,
            )

    def test_view_gate_rejects_isometry_or_probe_order_failure(self) -> None:
        valid_isometry = {"squared_distance_relative_l2_error": 1e-8}
        valid_probes = {"queries": 12, "rows_with_exact_order": 12}
        MODULE.require_view_validation("valid", valid_isometry, valid_probes)

        with self.assertRaisesRegex(ValueError, "isometry error"):
            MODULE.require_view_validation(
                "bad-isometry",
                {"squared_distance_relative_l2_error": 1e-3},
                valid_probes,
            )
        with self.assertRaisesRegex(ValueError, "changes fixed-probe order"):
            MODULE.require_view_validation(
                "bad-probes",
                valid_isometry,
                {"queries": 12, "rows_with_exact_order": 11},
            )


if __name__ == "__main__":
    unittest.main()
