import json
import unittest
from pathlib import Path

import numpy as np

from script import summarize_caq_co0_v2_b1 as summary


ROOT = Path(__file__).resolve().parents[1]


def synthetic_dataset(config, leading_r6=0.30, leading_local=0.35):
    rows = summary.CLUSTERS
    shape = (len(config.views), len(summary.ARMS), len(summary.SEEDS), rows)
    factors = np.zeros(shape, dtype=np.float64)
    factors[:, summary.ARM_INDEX["lvq_init"], :, :] = 1.0
    factors[:, summary.ARM_INDEX["caq_r6"], :, :] = 0.03
    factors[:, summary.ARM_INDEX["caq_local_fixed_point"], :, :] = 0.04
    leading = config.views.index(config.leading)
    factors[leading, summary.ARM_INDEX["caq_r6"], :, :] = leading_r6
    factors[leading, summary.ARM_INDEX["caq_local_fixed_point"], :, :] = leading_local
    return summary.DatasetMeasurements(
        config=config,
        factors=factors,
        zero=np.zeros(shape, dtype=np.bool_),
        loaded=np.ones(shape, dtype=np.bool_),
        cells=np.arange(rows, dtype=np.int16),
    )


def synthetic_pairs():
    rows = summary.CLUSTERS
    normalized = np.empty((2, 3, rows), dtype=np.float64)
    absolute = np.empty((2, 3, rows), dtype=np.float64)
    normalized[0, :, :] = 0.20
    normalized[1, :, :] = 0.10
    absolute[0, :, :] = 2.0
    absolute[1, :, :] = 1.0
    return summary.PairMeasurements(
        cells=np.arange(rows, dtype=np.int16),
        normalized_error=normalized,
        absolute_error=absolute,
        zero=np.zeros((2, 3, rows), dtype=np.bool_),
    )


class FrozenSummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ledger_path = ROOT / "docs" / "saq_caq_co0_v2_b0_hypotheses_2026_07_11.json"
        cls.ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    def make_inputs(self, cifar_r6=0.30, cifar_local=0.35):
        datasets = {
            "gist_sample50k_k512": synthetic_dataset(
                summary.DATASET_CONFIGS["gist_sample50k_k512"]
            ),
            "cifar60k_k512": synthetic_dataset(
                summary.DATASET_CONFIGS["cifar60k_k512"],
                leading_r6=cifar_r6,
                leading_local=cifar_local,
            ),
        }
        pairs = {dataset_id: synthetic_pairs() for dataset_id in datasets}
        return datasets, pairs

    def test_bootstrap_draws_are_deterministic_and_frozen(self):
        first = summary.bootstrap_draws()
        second = summary.bootstrap_draws()
        self.assertEqual(first.shape, (10000, 512))
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first[0, :8].tolist(), [431, 101, 91, 463, 37, 273, 317, 340])

    def test_synthetic_conditional_pass(self):
        datasets, pairs = self.make_inputs()
        result = summary.evaluate(self.ledger, datasets, pairs)
        self.assertEqual(result["decision"], "CONDITIONAL_PASS")
        self.assertTrue(result["checks"]["all_24_holm_rejected"])
        self.assertTrue(result["checks"]["materiality_lower_bounds_at_least_0_10"])
        self.assertEqual(len(result["hypotheses"]), 24)

    def test_synthetic_materiality_failure_is_no_go(self):
        datasets, pairs = self.make_inputs(cifar_r6=0.05, cifar_local=0.05)
        result = summary.evaluate(self.ledger, datasets, pairs)
        self.assertEqual(result["decision"], "NO_GO")
        self.assertFalse(result["checks"]["materiality_lower_bounds_at_least_0_10"])
        by_id = {item["id"]: item for item in result["hypotheses"]}
        self.assertFalse(by_id["M_CIFAR_R6"]["holm_reject"])

    def test_holm_step_down_uses_one_family(self):
        results = [
            {"one_sided_p_value": 0.001},
            {"one_sided_p_value": 0.02},
            {"one_sided_p_value": 0.04},
        ]
        summary.apply_holm(results)
        self.assertAlmostEqual(results[0]["holm_adjusted_p_value"], 0.003)
        self.assertAlmostEqual(results[1]["holm_adjusted_p_value"], 0.04)
        self.assertAlmostEqual(results[2]["holm_adjusted_p_value"], 0.04)


if __name__ == "__main__":
    unittest.main()
