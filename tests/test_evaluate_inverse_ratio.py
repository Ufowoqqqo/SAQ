import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from script.evaluate_inverse_ratio import (
    evaluate_result,
    inverse_ratio_for_query,
    read_fvecs,
    read_ivecs,
    summarize,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "script" / "evaluate_inverse_ratio.py"


def write_vecs(path, values, dtype):
    values = np.asarray(values, dtype=dtype)
    with open(path, "wb") as handle:
        for row in values:
            np.asarray([row.size], dtype="<i4").tofile(handle)
            row.tofile(handle)


class InverseRatioMetricTest(unittest.TestCase):
    def setUp(self):
        self.base = np.asarray(
            [
                [1.0, 0.0],
                [-1.0, 0.0],
                [0.0, 1.0],
                [0.0, -1.0],
                [2.0, 0.0],
                [0.0, 2.0],
            ],
            dtype=np.float32,
        )
        self.query = np.asarray([0.0, 0.0], dtype=np.float32)

    def test_exact_ids_score_one(self):
        score = inverse_ratio_for_query(
            self.query, self.base, np.asarray([0, 4]), np.asarray([0, 4])
        )
        self.assertEqual(score, 1.0)

    def test_disjoint_equal_distance_ids_score_one(self):
        score = inverse_ratio_for_query(
            self.query, self.base, np.asarray([0, 2]), np.asarray([1, 3])
        )
        self.assertEqual(score, 1.0)

    def test_hand_computed_nontrivial_ratio(self):
        score = inverse_ratio_for_query(
            self.query, self.base, np.asarray([0, 4]), np.asarray([4, 5])
        )
        expected = 2.0 / (2.0 / 1.0 + 2.0 / 2.0)
        self.assertAlmostEqual(score, expected, places=15)

    def test_returned_ids_are_sorted_by_true_distance(self):
        score = inverse_ratio_for_query(
            self.query, self.base, np.asarray([0, 4]), np.asarray([5, 0])
        )
        self.assertEqual(score, 1.0)

    def test_uses_euclidean_not_squared_distance(self):
        score = inverse_ratio_for_query(
            self.query, self.base, np.asarray([0]), np.asarray([4])
        )
        self.assertEqual(score, 0.5)
        self.assertNotEqual(score, 0.25)

    def test_zero_exact_distance_stops(self):
        base = np.vstack([np.zeros((1, 2), dtype=np.float32), self.base])
        with self.assertRaisesRegex(ValueError, "zero Euclidean distance"):
            inverse_ratio_for_query(
                self.query, base, np.asarray([0]), np.asarray([1])
            )

    def test_returned_set_closer_than_groundtruth_stops(self):
        with self.assertRaisesRegex(ValueError, "closer than exact ground truth"):
            inverse_ratio_for_query(
                self.query, self.base, np.asarray([4]), np.asarray([0])
            )

    def test_validation_rejects_duplicate_invalid_and_short_rows(self):
        queries = self.query.reshape(1, -1)
        groundtruth = np.asarray([[0, 4]], dtype=np.int32)
        with self.assertRaisesRegex(ValueError, "duplicate IDs"):
            evaluate_result(
                self.base,
                queries,
                groundtruth,
                np.asarray([[0, 0]], dtype=np.int32),
                2,
            )
        with self.assertRaisesRegex(ValueError, "invalid ID"):
            evaluate_result(
                self.base,
                queries,
                groundtruth,
                np.asarray([[0, -1]], dtype=np.int32),
                2,
            )
        with self.assertRaisesRegex(ValueError, "need 2"):
            evaluate_result(
                self.base,
                queries,
                groundtruth,
                np.asarray([[0]], dtype=np.int32),
                2,
            )

    def test_validation_rejects_nonfinite_values_and_query_mismatch(self):
        groundtruth = np.asarray([[0]], dtype=np.int32)
        returned = np.asarray([[0]], dtype=np.int32)
        queries = np.asarray([[math.nan, 0.0]], dtype=np.float32)
        with self.assertRaisesRegex(ValueError, "non-finite"):
            evaluate_result(self.base, queries, groundtruth, returned, 1)
        with self.assertRaisesRegex(ValueError, "query count mismatch"):
            evaluate_result(
                self.base,
                np.vstack([self.query, self.query]),
                groundtruth,
                returned,
                1,
            )

    def test_deterministic_aggregate_statistics(self):
        actual = summarize(np.asarray([0.5, 0.75, 1.0], dtype=np.float64))
        self.assertEqual(actual["count"], 3)
        self.assertEqual(actual["mean"], 0.75)
        self.assertEqual(actual["min"], 0.5)
        self.assertEqual(actual["median"], 0.75)
        self.assertEqual(actual["max"], 1.0)
        self.assertAlmostEqual(actual["p01"], 0.505)
        self.assertAlmostEqual(actual["p05"], 0.525)
        self.assertAlmostEqual(actual["p95"], 0.975)

    def test_uniform_vecs_round_trip_and_dimension_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            fvecs = directory / "x.fvecs"
            ivecs = directory / "x.ivecs"
            write_vecs(fvecs, self.base, np.dtype("<f4"))
            write_vecs(ivecs, [[0, 1], [2, 3]], np.dtype("<i4"))
            np.testing.assert_array_equal(read_fvecs(fvecs), self.base)
            np.testing.assert_array_equal(
                read_ivecs(ivecs), np.asarray([[0, 1], [2, 3]], dtype=np.int32)
            )

            malformed = directory / "malformed.ivecs"
            with open(malformed, "wb") as handle:
                np.asarray([2, 0, 1, 1, 2, 3], dtype="<i4").tofile(handle)
            with self.assertRaisesRegex(ValueError, "nonuniform"):
                read_ivecs(malformed)

    def test_cli_writes_query_level_json_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            base = directory / "base.fvecs"
            queries = directory / "query.fvecs"
            groundtruth = directory / "gt.ivecs"
            returned = directory / "returned.ivecs"
            output = directory / "result.json"
            write_vecs(base, self.base, np.dtype("<f4"))
            write_vecs(queries, [self.query], np.dtype("<f4"))
            write_vecs(groundtruth, [[0, 4]], np.dtype("<i4"))
            write_vecs(returned, [[0, 5]], np.dtype("<i4"))

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--base",
                    str(base),
                    "--queries",
                    str(queries),
                    "--groundtruth",
                    str(groundtruth),
                    "--results",
                    f"fixture={returned}",
                    "--k",
                    "2",
                    "--dataset",
                    "fixture",
                    "--output",
                    str(output),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            stdout = json.loads(completed.stdout)
            artifact = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout["results"][0]["label"], "fixture")
            self.assertEqual(len(artifact["inputs"]["base"]["sha256"]), 64)
            self.assertEqual(len(artifact["results"][0]["per_query"]), 1)
            self.assertAlmostEqual(
                artifact["results"][0]["recall_at_k"]["mean"], 0.5
            )
            self.assertAlmostEqual(
                artifact["results"][0]["inverse_ratio_at_k"]["mean"], 1.0
            )


if __name__ == "__main__":
    unittest.main()
