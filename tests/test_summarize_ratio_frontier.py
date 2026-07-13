import unittest

from script.summarize_ratio_frontier import (
    best_measured_at_or_above,
    interpolate_qps,
    nondominated,
    paired_query_deltas,
)


class RatioFrontierSummaryTest(unittest.TestCase):
    def test_nondominated_removes_equal_quality_slower_point(self):
        rows = [
            {"label": "a", "quality": 0.9, "qps": 100.0},
            {"label": "b", "quality": 0.95, "qps": 80.0},
            {"label": "c", "quality": 0.95, "qps": 70.0},
        ]
        frontier = nondominated(rows, "quality")
        self.assertEqual([row["label"] for row in frontier], ["a", "b"])

    def test_interpolation_uses_adjacent_measured_points(self):
        frontier = [
            {"label": "low", "quality": 0.9, "qps": 100.0},
            {"label": "high", "quality": 1.0, "qps": 50.0},
        ]
        actual = interpolate_qps(frontier, "quality", 0.95)
        self.assertEqual(actual["status"], "interpolated")
        self.assertAlmostEqual(actual["qps"], 75.0)
        self.assertEqual(actual["lower_label"], "low")
        self.assertEqual(actual["upper_label"], "high")

    def test_interpolation_reports_unreachable(self):
        frontier = [
            {"label": "low", "quality": 0.9, "qps": 100.0},
            {"label": "high", "quality": 1.0, "qps": 50.0},
        ]
        actual = interpolate_qps(frontier, "quality", 1.01)
        self.assertEqual(actual["status"], "unreachable")
        self.assertEqual(actual["measured_max"], 1.0)

    def test_best_measured_at_or_above_uses_highest_qps(self):
        frontier = [
            {"label": "low", "quality": 0.9, "qps": 100.0},
            {"label": "eligible_fast", "quality": 0.96, "qps": 80.0},
            {"label": "eligible_slow", "quality": 0.99, "qps": 60.0},
        ]
        actual = best_measured_at_or_above(frontier, "quality", 0.95)
        self.assertEqual(actual["status"], "measured")
        self.assertEqual(actual["label"], "eligible_fast")

    def test_best_measured_at_or_above_reports_unreachable(self):
        frontier = [
            {"label": "low", "quality": 0.9, "qps": 100.0},
            {"label": "high", "quality": 0.94, "qps": 80.0},
        ]
        actual = best_measured_at_or_above(frontier, "quality", 0.95)
        self.assertEqual(actual["status"], "unreachable")
        self.assertEqual(actual["measured_max"], 0.94)

    def test_paired_query_deltas(self):
        default = {
            "per_query": [
                {"query_id": 0, "inverse_ratio_at_k": 0.9},
                {"query_id": 1, "inverse_ratio_at_k": 0.8},
                {"query_id": 2, "inverse_ratio_at_k": 0.7},
            ]
        }
        alternative = {
            "per_query": [
                {"query_id": 0, "inverse_ratio_at_k": 0.8},
                {"query_id": 1, "inverse_ratio_at_k": 0.8},
                {"query_id": 2, "inverse_ratio_at_k": 0.8},
            ]
        }
        actual = paired_query_deltas(default, alternative)
        self.assertAlmostEqual(actual["mean"], 0.0)
        self.assertEqual(actual["fraction_negative"], 1.0 / 3.0)
        self.assertEqual(actual["fraction_zero"], 1.0 / 3.0)
        self.assertEqual(actual["fraction_positive"], 1.0 / 3.0)


if __name__ == "__main__":
    unittest.main()
