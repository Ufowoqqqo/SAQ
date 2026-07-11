import csv
import importlib.util
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "script" / "run_graph_phase3.py"
SPEC = importlib.util.spec_from_file_location("run_graph_phase3", MODULE_PATH)
phase3 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = phase3
SPEC.loader.exec_module(phase3)


class GraphPhase3Test(unittest.TestCase):
    def make_event(self, seed, query_id, root_id, estimator, rank):
        exact_best_distance = 10.0 + query_id + root_id
        selected_exact_distance = exact_best_distance + 0.25 * (rank - 1)
        exact_best_id = 100 + query_id * 10 + root_id
        return phase3.Event(
            subset=64,
            max_queries=2,
            seed=seed,
            query_id=query_id,
            root_id=root_id,
            exact_best_id=exact_best_id,
            exact_best_distance=exact_best_distance,
            exact_gap=0.5 + root_id,
            degree=3,
            distinct_clusters=1,
            estimator=estimator,
            rank_exact_best=float(rank),
            est_best_id=(
                exact_best_id if rank == 1 else 200 + query_id * 10 + root_id
            ),
            est_best_estimate=9.0,
            est_best_exact_distance=selected_exact_distance,
            exact_regret=selected_exact_distance - exact_best_distance,
            top1_disagree=float(rank != 1),
        )

    def synthetic_events(self):
        ranks = {
            "symqg_fht_fastscan": {
                0: ((1, 3), (2, 2)),
                1: ((3, 1), (2, 2)),
            },
            "symqg_fht_scalar": {
                0: ((1, 3), (2, 2)),
                1: ((3, 1), (2, 2)),
            },
            "saq_fast": {
                0: ((1, 1), (1, 3)),
                1: ((1, 1), (3, 1)),
            },
        }
        events = []
        for estimator, seed_values in ranks.items():
            for seed, query_values in seed_values.items():
                for query_id, root_values in enumerate(query_values):
                    for root_id, rank in enumerate(root_values):
                        events.append(
                            self.make_event(seed, query_id, root_id, estimator, rank)
                        )
        return events

    def test_parsers_and_canonical_matrix(self):
        settings = phase3.parse_settings(None)
        seeds = phase3.parse_seeds("0-9")
        self.assertTrue(phase3.is_canonical(settings, seeds, 32, 8))
        self.assertEqual(phase3.parse_seeds("0,2-4"), (0, 2, 3, 4))
        self.assertFalse(phase3.is_canonical(settings, seeds[:-1], 32, 8))
        with self.assertRaises(ValueError):
            phase3.parse_settings(["64:2", "64:3"])

    def test_resume_requires_new_event_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "seed_00"
            event_path, aggregate_path, summary_path = phase3.artifact_paths(prefix)
            event_path.write_text(
                "query_id,root_id,estimator,rank_exact_best\n0,0,saq_fast,1\n",
                encoding="utf-8",
            )
            aggregate_path.write_text(
                "estimator,approx_code_bits_per_candidate\nsaq_fast,64\n",
                encoding="utf-8",
            )
            summary_path.write_text("summary\n", encoding="utf-8")
            self.assertFalse(phase3.run_is_complete(prefix))

            with event_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=sorted(phase3.REQUIRED_EVENT_COLUMNS)
                )
                writer.writeheader()
                writer.writerow({field: "0" for field in writer.fieldnames})
            self.assertTrue(phase3.run_is_complete(prefix))

    def test_resume_requires_identical_command(self):
        prefix = Path("runs/subset_64/seed_00")
        prior = {str(prefix): ["profiler", "-graph_degree=8"]}
        self.assertTrue(
            phase3.resume_command_matches(
                prefix, ["profiler", "-graph_degree=8"], prior
            )
        )
        self.assertFalse(
            phase3.resume_command_matches(
                prefix, ["profiler", "-graph_degree=32"], prior
            )
        )

    def test_queries_not_seeds_or_roots_are_independent_units(self):
        events = self.synthetic_events()
        specs = [
            phase3.RunSpec(phase3.Setting(64, 2), seed, Path(f"seed_{seed}"))
            for seed in (0, 1)
        ]
        phase3.validate_events(events, specs, roots_per_query=2, expected_degree=3)
        query_rows = phase3.build_query_metrics(events, (1, 2))
        code_bits = {
            (64, seed, estimator): bits
            for seed in (0, 1)
            for estimator, bits in (
                ("symqg_fht_fastscan", 64.0),
                ("symqg_fht_scalar", 64.0),
                ("saq_fast", 48.0),
            )
        }
        seed_rows = phase3.build_seed_summary(
            query_rows, events, code_bits, (1, 2)
        )
        overall, averaged_queries = phase3.build_overall_summary(
            query_rows, seed_rows, events, code_bits, (1, 2)
        )
        baseline = next(
            row
            for row in overall
            if row["estimator"] == "symqg_fht_fastscan"
        )
        self.assertEqual(baseline["n_queries"], 2)
        self.assertEqual(baseline["seed_count"], 2)
        self.assertEqual(baseline["rank_mean_n_queries"], 2)
        self.assertAlmostEqual(baseline["rank_mean"], 2.0)

        paired = phase3.build_paired_summary(averaged_queries, (1, 2))
        rank_delta = next(
            row
            for row in paired
            if row["candidate"] == "saq_fast" and row["metric"] == "rank_mean"
        )
        self.assertEqual(rank_delta["n_queries"], 2)
        self.assertAlmostEqual(rank_delta["candidate_minus_baseline_mean"], -0.5)

    def test_event_validation_rejects_inconsistent_regret(self):
        events = self.synthetic_events()
        events[0] = replace(events[0], exact_regret=1.0)
        specs = [
            phase3.RunSpec(phase3.Setting(64, 2), seed, Path(f"seed_{seed}"))
            for seed in (0, 1)
        ]
        with self.assertRaisesRegex(ValueError, "regret identity"):
            phase3.validate_events(
                events, specs, roots_per_query=2, expected_degree=3
            )

    def test_margin_conditioning_deduplicates_seeds_and_estimators(self):
        boundaries, rows = phase3.build_margin_conditioned(self.synthetic_events())
        self.assertEqual(boundaries[0]["n_query_root_events"], 4)
        baseline_events = sum(
            int(row["n_query_root_events"])
            for row in rows
            if row["estimator"] == "symqg_fht_fastscan"
        )
        self.assertEqual(baseline_events, 4)


if __name__ == "__main__":
    unittest.main()
