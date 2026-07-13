from __future__ import annotations

import itertools
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "script"))

import evaluate_arbitrary_cardinality as evaluator  # noqa: E402


def exhaustive_scalar_sse(values: list[float], cluster_count: int) -> float:
    ordered = sorted(values)
    best = math.inf
    for boundaries in itertools.combinations(range(1, len(ordered)), cluster_count - 1):
        indices = (0,) + boundaries + (len(ordered),)
        sse = 0.0
        for begin, end in zip(indices, indices[1:]):
            segment = ordered[begin:end]
            centroid = sum(segment) / len(segment)
            sse += sum((value - centroid) ** 2 for value in segment)
        best = min(best, sse)
    return best


class ExactScalarCurveTest(unittest.TestCase):
    def test_matches_exhaustive_contiguous_partitions(self) -> None:
        values = [-3.0, -1.0, 0.5, 2.0, 5.0]
        curve = evaluator.exact_scalar_curve(values, 5)
        for cardinality in range(1, 6):
            self.assertAlmostEqual(
                curve[cardinality].sse,
                exhaustive_scalar_sse(values, cardinality),
                places=12,
            )

    def test_aggregates_duplicate_weighted_support(self) -> None:
        curve = evaluator.exact_scalar_curve(
            [0.0, 0.0, 2.0], 3, weights=[1.0, 2.0, 1.0]
        )
        self.assertAlmostEqual(curve[1].centroids[0], 0.5)
        self.assertAlmostEqual(curve[1].sse, 3.0)
        self.assertEqual(curve[2].sse, 0.0)
        self.assertEqual(curve[3].effective_cardinality, 2)
        self.assertEqual(curve[3].sse, 0.0)


class AllocationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.curves = [
            evaluator.exact_scalar_curve([-1.0, 0.0, 1.0], 16),
            evaluator.exact_scalar_curve([-2.0, -1.0, 0.0, 1.0, 2.0], 16),
        ]

    def _exhaustive(self, dyadic_only: bool) -> tuple[float, int, tuple[int, int]]:
        allowed = range(1, 17)
        if dyadic_only:
            allowed = (1, 2, 4, 8, 16)
        candidates: list[tuple[float, int, tuple[int, int]]] = []
        for first, second in itertools.product(allowed, repeat=2):
            product = first * second
            if product <= 16:
                distortion = (
                    self.curves[0][first].mean_squared_error
                    + self.curves[1][second].mean_squared_error
                )
                candidates.append((distortion, -product, (first, second)))
        distortion, negative_product, cardinalities = min(candidates)
        return distortion, -negative_product, cardinalities

    def test_arbitrary_allocation_matches_exhaustive_reference(self) -> None:
        solution = evaluator.optimize_product_allocation(
            self.curves, 16, dyadic_only=False
        )
        expected = self._exhaustive(False)
        self.assertEqual(solution.cardinalities, (3, 5))
        self.assertEqual(
            (solution.distortion, solution.used_states, solution.cardinalities),
            expected,
        )

    def test_dyadic_allocation_matches_exhaustive_reference(self) -> None:
        solution = evaluator.optimize_product_allocation(
            self.curves, 16, dyadic_only=True
        )
        expected = self._exhaustive(True)
        self.assertEqual(solution.cardinalities, (4, 4))
        self.assertAlmostEqual(solution.distortion, 0.1, places=15)
        self.assertEqual(
            (solution.distortion, solution.used_states, solution.cardinalities),
            expected,
        )


class MixedRadixTest(unittest.TestCase):
    def test_bijection_and_lookup_parity(self) -> None:
        radices = (3, 5)
        centroids = ((-1.0, 0.0, 1.0), (-2.0, -1.0, 0.0, 1.0, 2.0))
        query = (0.25, -0.5)
        lookup = evaluator.build_squared_l2_lookup(query, centroids, radices, 16)
        addresses: set[int] = set()
        for codes in itertools.product(range(3), range(5)):
            address = evaluator.mixed_radix_encode(codes, radices)
            addresses.add(address)
            self.assertEqual(evaluator.mixed_radix_decode(address, radices), codes)
            direct = sum(
                (query_value - centroids[dimension][code]) ** 2
                for dimension, (query_value, code) in enumerate(zip(query, codes))
            )
            self.assertEqual(lookup[address], direct)
        self.assertEqual(addresses, set(range(15)))
        self.assertIsNone(lookup[15])


class EntropyTest(unittest.TestCase):
    def test_uniform_three_symbol_huffman_length(self) -> None:
        self.assertEqual(evaluator.huffman_code_lengths([1.0, 1.0, 1.0]), (2, 2, 1))
        self.assertAlmostEqual(
            evaluator.expected_prefix_length([1.0, 1.0, 1.0]),
            5.0 / 3.0,
            places=15,
        )
        self.assertAlmostEqual(
            evaluator.shannon_entropy([1.0, 1.0, 1.0]), math.log2(3.0), places=15
        )


class FrozenWitnessTest(unittest.TestCase):
    def test_predeclared_witness(self) -> None:
        result = evaluator.run_synthetic_witness()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["predeclared_checks"].values()))
        self.assertEqual(
            tuple(result["allocation"]["arbitrary"]["cardinalities"]), (3, 5)
        )
        self.assertEqual(
            tuple(result["allocation"]["dyadic"]["cardinalities"]), (4, 4)
        )


if __name__ == "__main__":
    unittest.main()
