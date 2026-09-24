import itertools
import unittest

import numpy as np

from research.correlated_pair_allocation import diagnostic as d
from research.correlated_pair_allocation import strong_baselines as s


def synthetic_curves(costs):
    curves = []
    for group in range(64):
        axes = [d.ScalarCurve(dict(enumerate(costs[2 * group + a], 1)),
                              dict(enumerate(costs[2 * group + a] * 1.2, 1))) for a in range(2)]
        fit, evaluation, splits = {}, {}, {}
        for budget in range(6, 11):
            best, first, second = min((axes[0].fit_sse[a] + axes[1].fit_sse[budget - a], a, budget - a)
                                      for a in range(1, 10) if 1 <= budget - a <= 9)
            fit[budget], splits[budget] = best, (first, second)
            evaluation[budget] = axes[0].eval_sse[first] + axes[1].eval_sse[second]
        curves.append(d.PairCurve(fit, evaluation, splits, 2.0, 1.0, 1.0,
                                  axes, np.zeros(2), np.eye(2), np.ones(2)))
    return curves


class StrongBaselineTest(unittest.TestCase):
    def test_frozen_gate_does_not_promote_pairing_only_gains(self):
        rows = [{"dataset": dataset, "fold": fold, "gain_fraction": 0.05}
                for dataset in ("sift", "gist") for fold in ("A", "B") for _ in range(4)]
        self.assertEqual(s.decision(rows), "ELIGIBLE_FOR_CONFIRMATION")
        rows[0]["gain_fraction"] = 0.01
        self.assertEqual(s.decision(rows), "PARK_INCONCLUSIVE")
        for index in range(0, 16, 4):
            rows[index]["gain_fraction"] = 0.0
        self.assertEqual(s.decision(rows), "STOP_CURRENT_FORMULATION")

    def test_constrained_dp_against_exhaustive_tied_reference(self):
        rng = np.random.RandomState(11)
        for costs in (np.zeros((4, 9)), rng.randint(0, 4, size=(4, 9))):
            feasible = [bits for bits in itertools.product(range(1, 10), repeat=4)
                        if sum(bits) == 16 and all(6 <= sum(bits[g:g + 2]) <= 10 for g in (0, 2))]
            expected = min(feasible, key=lambda b: (s.selected_sse(costs, b),
                           sum(b[2:]), b[2], sum(b[:2]), b[0]))
            self.assertEqual(s.scalar_dp(costs, 16, (6, 10)), list(expected))

    def test_exact_budgets_equivalence_and_free_optimum(self):
        rng = np.random.RandomState(17)
        # Nonmonotone curves exercise DP rather than assuming diminishing returns.
        for costs in (rng.randint(0, 30, size=(128, 9)), np.zeros((128, 9))):
            curves = synthetic_curves(costs)
            arms, fit, _ = s.allocations(curves)
            for arm, bits in arms.items():
                self.assertEqual(sum(bits), 512)
                self.assertTrue(all(1 <= b <= 9 for b in bits))
                if arm != "S":
                    self.assertTrue(all(6 <= sum(bits[g:g + 2]) <= 10 for g in range(0, 128, 2)))
            self.assertLessEqual(s.selected_sse(fit, arms["S"]), s.selected_sse(fit, arms["E"]))
            if not np.any(costs):
                self.assertEqual(arms["E"][-2:], [1, 5])

    def test_changed_evaluation_does_not_change_fit_or_allocations(self):
        rng = np.random.RandomState(29)
        fit, evaluation = rng.normal(size=(96, 2)), rng.normal(size=(64, 2))
        first = d.pair_curve(fit, evaluation, (0, 1))
        second = d.pair_curve(fit, evaluation * 25 + 10, (0, 1))
        for key in ("fit_sse", "splits"):
            self.assertEqual(getattr(first, key), getattr(second, key))
        for key in ("mean", "basis", "eigenvalues"):
            np.testing.assert_array_equal(getattr(first, key), getattr(second, key))
        for left, right in zip(first.axes, second.axes):
            self.assertEqual(left.fit_sse, right.fit_sse)
            self.assertNotEqual(left.eval_sse, right.eval_sse)
            for bits in range(1, 10):
                np.testing.assert_array_equal(left.centers[bits], right.centers[bits])
        self.assertEqual(s.allocations([first] * 64)[0], s.allocations([second] * 64)[0])


if __name__ == "__main__":
    unittest.main()
