import unittest

import numpy as np

from research.correlated_pair_allocation import opportunity as subject


class OpportunityTest(unittest.TestCase):
    @staticmethod
    def reference_adjustment(values, pair_bits):
        quantized, codes, deltas = subject.nearest_lattice(values, pair_bits)
        coordinate_bits = np.repeat(np.asarray(pair_bits), 2)
        for row in range(values.shape[0]):
            inner = float(values[row] @ quantized[row])
            quantized_norm = float(quantized[row] @ quantized[row])
            epsilon = subject.ADJUSTMENT_EPSILON * quantized_norm
            for _ in range(subject.ADJUSTMENT_ROUNDS):
                changed = 0
                for coordinate in range(values.shape[1]):
                    original = values[row, coordinate]
                    current = quantized[row, coordinate]
                    other_norm = quantized_norm - current * current
                    inner_delta = deltas[row, coordinate] * original
                    maximum = (1 << int(coordinate_bits[coordinate])) - 1
                    while codes[row, coordinate] < maximum:
                        candidate = current + deltas[row, coordinate]
                        candidate_norm = other_norm + candidate * candidate
                        candidate_inner = inner + inner_delta
                        if ((inner * inner + epsilon) * candidate_norm
                                >= candidate_inner * candidate_inner * quantized_norm):
                            break
                        codes[row, coordinate] += 1
                        current = candidate
                        inner = candidate_inner
                        quantized_norm = candidate_norm
                        changed += 1
                    while codes[row, coordinate] > 0:
                        candidate = current - deltas[row, coordinate]
                        candidate_norm = other_norm + candidate * candidate
                        candidate_inner = inner - inner_delta
                        if ((inner * inner + epsilon) * candidate_norm
                                >= candidate_inner * candidate_inner * quantized_norm):
                            break
                        codes[row, coordinate] -= 1
                        current = candidate
                        inner = candidate_inner
                        quantized_norm = candidate_norm
                        changed += 1
                    quantized[row, coordinate] = current
                inner = float(values[row] @ quantized[row])
                quantized_norm = float(quantized[row] @ quantized[row])
                if changed == 0:
                    break
        return quantized

    def test_saq_plan_matches_budget_and_granularity(self):
        plan = subject.saq_plan(np.ones(128))
        self.assertEqual(plan, [subject.Segment(0, 128, 4)])
        self.assertEqual(subject.plan_bits(plan), (512, 64, 576))

    def test_pair_allocator_preserves_equal_width_for_equal_variance(self):
        bits = subject.allocate_pair_bits(np.ones(32), 4)
        self.assertEqual(bits, [4] * 32)

    def test_pair_allocator_moves_bits_to_higher_variance(self):
        variance = np.ones(32)
        variance[0] = 100.0
        bits = subject.allocate_pair_bits(variance, 4)
        self.assertEqual(sum(bits), 128)
        self.assertGreater(bits[0], 4)

    def test_rotation_is_deterministic_and_orthogonal(self):
        first, first_hash = subject.rotation(0, 64)
        second, second_hash = subject.rotation(0, 64)
        self.assertEqual(first_hash, second_hash)
        np.testing.assert_array_equal(first, second)
        np.testing.assert_allclose(first.T @ first, np.eye(64), atol=1e-12)

    def test_nearest_lattice_and_adjustment_are_deterministic(self):
        rng = np.random.RandomState(9)
        values = rng.normal(size=(16, 4))
        nearest, codes, deltas = subject.nearest_lattice(values, [2, 3])
        self.assertEqual(nearest.shape, values.shape)
        self.assertEqual(codes.shape, values.shape)
        self.assertTrue(np.all(deltas >= 0))
        first = subject.adjusted_lattice(values, [2, 3])
        second = subject.adjusted_lattice(values, [2, 3])
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(
            first, self.reference_adjustment(values, [2, 3])
        )
        self.assertTrue(np.isfinite(subject.angular_loss(values, first)))


if __name__ == "__main__":
    unittest.main()
