import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "script" / "evaluate_phase1b_gate.py"
SPEC = importlib.util.spec_from_file_location("evaluate_phase1b_gate", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


METRICS = (
    "mean_per_query_candidate_rmse",
    "pooled_candidate_rmse",
    "boundary_inversion_rate",
    "topk_agreement",
)


def paired_row(group: str, stage: str) -> dict[str, str]:
    row = {
        "transform": "residual_pca",
        "baseline": "current_pca",
        "plan_control": "frozen-pca",
        "rotation_group": group,
        "stage": stage,
        "bootstrap_replicates": "10000",
        "bootstrap_seed": "20260710",
        "matched_budget": "true",
    }
    for metric in METRICS:
        better_higher = metric == "topk_agreement"
        delta = 0.01 if better_higher else -0.01
        row.update(
            {
                f"{metric}_transform_minus_pca": str(delta),
                f"{metric}_ci95_low": str(delta - 0.005),
                f"{metric}_ci95_high": str(delta + 0.005),
                f"{metric}_ci_evidence": "favors_transform",
                f"{metric}_seeds_favoring_transform": "10",
            }
        )
    return row


def passing_rows() -> list[dict[str, str]]:
    rows = [
        paired_row("seed_average", stage)
        for stage in MODULE.PRIMARY_STAGES
    ]
    rows.extend(
        paired_row("off", stage) for stage in ("accurate_prefix_1", "full")
    )
    return rows


class EvaluatePhase1bGateTest(unittest.TestCase):
    def evaluate(self, rows: list[dict[str, str]]):
        return MODULE.evaluate_scientific_gates(rows)

    def test_all_frozen_gates_pass(self) -> None:
        gate_a, gate_b, gate_c, decision = self.evaluate(passing_rows())
        self.assertTrue(gate_a["pass"])
        self.assertTrue(gate_b["pass"])
        self.assertTrue(gate_c["pass"])
        self.assertEqual(
            decision,
            "permit_one_counterfactual_segment_bit_mechanism_analysis_only",
        )

    def test_gate_a_failure_stops_before_ranking(self) -> None:
        rows = passing_rows()
        full = next(
            row
            for row in rows
            if row["rotation_group"] == "seed_average" and row["stage"] == "full"
        )
        full["pooled_candidate_rmse_ci95_high"] = "0.001"
        gate_a, gate_b, gate_c, decision = self.evaluate(rows)
        self.assertFalse(gate_a["pass"])
        self.assertFalse(gate_b["evaluated"])
        self.assertFalse(gate_c["evaluated"])
        self.assertEqual(decision, "close_one_dataset_estimator_effect")

    def test_gate_b_and_c_stop_decisions_are_distinct(self) -> None:
        ranking_rows = passing_rows()
        accurate = next(
            row
            for row in ranking_rows
            if row["rotation_group"] == "seed_average"
            and row["stage"] == "accurate_prefix_1"
        )
        accurate["boundary_inversion_rate_ci95_high"] = "0.001"
        _, gate_b, gate_c, decision = self.evaluate(ranking_rows)
        self.assertFalse(gate_b["pass"])
        self.assertFalse(gate_c["evaluated"])
        self.assertEqual(
            decision,
            "narrow_estimator_mismatch_replicated_but_close_for_absent_ranking_evidence",
        )

        no_harm_rows = passing_rows()
        fast = next(
            row
            for row in no_harm_rows
            if row["rotation_group"] == "seed_average" and row["stage"] == "fast_all"
        )
        fast["mean_per_query_candidate_rmse_ci_evidence"] = "favors_pca"
        _, gate_b, gate_c, decision = self.evaluate(no_harm_rows)
        self.assertTrue(gate_b["pass"])
        self.assertFalse(gate_c["pass"])
        self.assertEqual(
            decision,
            "ranking_signal_with_stage_tradeoff_close_global_replacement",
        )


if __name__ == "__main__":
    unittest.main()
