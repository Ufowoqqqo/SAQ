#!/usr/bin/env python3
"""Non-random unit tests for the independent A4-1S Python authority."""

from __future__ import annotations

import array
import struct
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "script"))

import a4_1s_artifacts as artifacts  # noqa: E402
import a4_1s_reference as reference  # noqa: E402
import a4_1s_runner as runner  # noqa: E402


class ExactReferenceTests(unittest.TestCase):
    def test_binary32_grid_decode_canonicalizes_signed_zero(self) -> None:
        self.assertEqual(reference.decode_float32_grid(0x00000000), 0)
        self.assertEqual(reference.decode_float32_grid(0x80000000), 0)
        self.assertEqual(reference.decode_float32_grid(0x00000001), 1)
        self.assertEqual(reference.decode_float32_grid(0x80000001), -1)
        self.assertEqual(reference.decode_float32_grid(0x00800000), 1 << 23)

    def test_direct_rounding_midpoints_and_thirds(self) -> None:
        minimum_subnormal = Fraction(1, 1 << 149)
        cases = (
            (minimum_subnormal / 2, 0x00000000),
            (3 * minimum_subnormal / 2, 0x00000002),
            (-minimum_subnormal / 2, 0x80000000),
            (-3 * minimum_subnormal / 2, 0x80000002),
            (Fraction(1, 3), 0x3EAAAAAB),
            (Fraction(-1, 3), 0xBEAAAAAB),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    reference.round_fraction_to_ieee_bits(
                        value, fraction_bits=23, exponent_bits=8
                    ),
                    expected,
                )

    def test_lookup_replay_precision_layers(self) -> None:
        origin = (reference.float32_bits(0.0), reference.float32_bits(0.0))
        reconstruction = (
            reference.float32_bits(3.0),
            reference.float32_bits(4.0),
        )
        pre_narrow, stored = reference.point_lookup_entry_bits(
            origin, reconstruction
        )
        self.assertEqual(pre_narrow, reference.float64_bits(25.0))
        self.assertEqual(stored, reference.float32_bits(25.0))
        scalar_pre, scalar_stored = reference.scalar_lookup_entry_bits(
            reference.float32_bits(0.0), reference.float32_bits(-1.0)
        )
        self.assertEqual(scalar_pre, reference.float64_bits(1.0))
        self.assertEqual(scalar_stored, reference.float32_bits(1.0))

    def test_exact_scalar_partition_and_at_most_alias(self) -> None:
        bits = [0x80000002, 0x00000000, 0x00000002]
        curve = reference.exact_scalar_curve_reference(
            bits,
            5,
            weights=[1, 2, 1],
            vector_ids=[9, 4, 7],
        )
        self.assertEqual(curve.support, (-2, 0, 2))
        self.assertEqual(curve.at(1).objective_grid, Fraction(8, 1))
        self.assertEqual(curve.at(2).objective_grid, Fraction(8, 3))
        self.assertEqual(curve.at(3).objective_grid, Fraction(0, 1))
        self.assertEqual(curve.at(5).effective_cardinality, 3)
        self.assertEqual(curve.at(5).clusters, curve.at(3).clusters)

    def test_product_allocation_frozen_witness(self) -> None:
        first = reference.exact_scalar_curve_reference(
            [reference.float32_bits(value) for value in (-1.0, 0.0, 1.0)], 16
        )
        second = reference.exact_scalar_curve_reference(
            [reference.float32_bits(value) for value in (-2.0, -1.0, 0.0, 1.0, 2.0)],
            16,
        )
        arbitrary = reference.exact_product_allocation_reference(
            first, second, 16, dyadic_only=False
        )
        dyadic = reference.exact_product_allocation_reference(
            first, second, 16, dyadic_only=True
        )
        self.assertEqual(arbitrary.cardinalities, (3, 5))
        self.assertEqual(arbitrary.objective_grid, 0)
        # A4-1S allocates raw fitting SSE.  Unlike the separately preserved
        # A4-0 MSE witness, unequal support counts therefore make (2,8) the
        # exact dyadic winner for this deliberately tiny fixture.
        self.assertEqual(dyadic.cardinalities, (2, 8))

    def test_full_shape_scalar_replay_is_independent(self) -> None:
        parsed = {
            "support_count": 3,
            "maximum_cardinality": 1,
            "support": [
                {
                    "support_id": 0,
                    "grid_integer": "-1",
                    "weight": "1",
                    "lowest_vector_id": 0,
                },
                {
                    "support_id": 1,
                    "grid_integer": "0",
                    "weight": "2",
                    "lowest_vector_id": 1,
                },
                {
                    "support_id": 2,
                    "grid_integer": "1",
                    "weight": "1",
                    "lowest_vector_id": 2,
                },
            ],
            "solutions": {
                1: {
                    "objective": {
                        "binary_grid_exponent": -298,
                        "denominator": "1",
                        "numerator": "2",
                    },
                    "clusters": [
                        {
                            "begin": 0,
                            "end": 3,
                            "mean": {
                                "binary_grid_exponent": -149,
                                "denominator": "1",
                                "numerator": "0",
                            },
                            "binary32_bits": "0x00000000",
                            "binary64_bits": "0x0000000000000000",
                        }
                    ],
                }
            },
        }
        replay, interval_count, internal_high_water = (
            runner._independent_scalar_solution_replays(parsed)
        )
        self.assertEqual(interval_count, 1)
        self.assertGreater(internal_high_water, 0)
        self.assertEqual(
            replay[1],
            {
                "binary_grid_exponent": -298,
                "denominator": "1",
                "numerator": "2",
            },
        )
        parsed["solutions"][1]["objective"]["numerator"] = "1"
        with self.assertRaisesRegex(
            runner.GateFailure, "independent exact replay mismatch"
        ):
            runner._independent_scalar_solution_replays(parsed)


class RepresentationReferenceTests(unittest.TestCase):
    def test_block_distinctness_applies_only_to_selected_start(self) -> None:
        case = {
            "capacity": 3,
            "point_count": 3,
            "failure": "NONE",
            "failed_start_id": 0,
            "best": {"control_valid": True, "start_id": 0},
            "validation_best_start_sse_comparison_count": 0,
            "starts": {
                0: {
                    "converged": True,
                    "distinct_serialized_center_count": 3,
                    "failure": "NONE",
                    "final_assignment_count": 3,
                    "final_center_count": 3,
                    "final_sse_bits": "0x0000000000000000",
                    "serialized_center_count": 3,
                },
                1: {
                    "converged": True,
                    "distinct_serialized_center_count": 2,
                    "failure": "NONE",
                    "final_assignment_count": 3,
                    "final_center_count": 3,
                    "final_sse_bits": "0x3ff0000000000000",
                    "serialized_center_count": 3,
                },
            },
        }
        runner._validate_block_selected_distinctness(case)

        case["starts"][0]["distinct_serialized_center_count"] = 2
        with self.assertRaisesRegex(
            runner.GateFailure, "valid block BEST selected colliding centers"
        ):
            runner._validate_block_selected_distinctness(case)

        case["starts"][0]["failure"] = "SERIALIZED_CENTER_COLLISION"
        case["best"] = {"control_valid": False}
        case["failure"] = "SERIALIZED_CENTER_COLLISION"
        case["failed_start_id"] = 0
        runner._validate_block_selected_distinctness(case)

        case["failed_start_id"] = 1
        with self.assertRaisesRegex(
            runner.GateFailure, "does not identify the winning start"
        ):
            runner._validate_block_selected_distinctness(case)

        case["failed_start_id"] = 0
        case["starts"][0]["distinct_serialized_center_count"] = 3
        with self.assertRaisesRegex(
            runner.GateFailure, "collision failure has no selected-center collision"
        ):
            runner._validate_block_selected_distinctness(case)

        case["failure"] = "NONFINITE_CONTROL"
        case["starts"][0]["final_sse_bits"] = "0x7ff0000000000000"
        runner._validate_block_selected_distinctness(case)
        self.assertEqual(case["validation_best_start_sse_comparison_count"], 0)

    def test_frozen_terminal_status_precedence_matrix(self) -> None:
        fixture = runner._status_precedence_fixture()
        self.assertTrue(fixture["passed"])
        self.assertEqual(fixture["case_count"], 6)
        self.assertEqual(
            runner._resolve_frozen_terminal_status(
                ["NO_GO_EXACT_SOLVER_COST", "NO_GO_REPRESENTATION"]
            ),
            "NO_GO_REPRESENTATION",
        )

    def test_mixed_radix_and_matched_payload_round_trip(self) -> None:
        radices = (3, 5)
        for codes in reference.all_mixed_radix_codes(radices):
            address = reference.mixed_radix_encode(codes, radices)
            self.assertEqual(reference.mixed_radix_decode(address, radices), codes)

        labels4 = tuple(index % 16 for index in range(64))
        payload4 = reference.pack_matched_labels(labels4, 4)
        self.assertEqual(len(payload4), 32)
        self.assertEqual(reference.unpack_matched_labels(payload4, 4), labels4)

        labels8 = tuple((3 * index) % 256 for index in range(64))
        payload8 = reference.pack_matched_labels(labels8, 8)
        self.assertEqual(len(payload8), 64)
        self.assertEqual(reference.unpack_matched_labels(payload8, 8), labels8)

    def test_global_payload_round_trip_and_zero_tail(self) -> None:
        widths = (0, 1, 3, 8, 5)
        labels = (0, 1, 5, 255, 17)
        payload = reference.pack_global_labels(labels, widths, 8)
        self.assertEqual(reference.unpack_global_labels(payload, widths), labels)
        self.assertEqual(payload[3:], bytes(5))

    def test_canonical_artifact_constants(self) -> None:
        checks = artifacts.pure_constant_self_test()
        self.assertTrue(all(checks.values()))
        self.assertFalse(artifacts.canonical_json_bytes({"a": 1}).endswith(b"\n"))

    def test_strict_json_equality_rejects_python_numeric_coercions(self) -> None:
        expected = {"flag": True, "count": 1, "nested": [0, "x"]}
        self.assertTrue(runner._strict_json_equal(expected, dict(expected)))
        self.assertFalse(
            runner._strict_json_equal(expected, {**expected, "flag": 1})
        )
        self.assertFalse(
            runner._strict_json_equal(expected, {**expected, "count": 1.0})
        )
        self.assertFalse(
            runner._strict_json_equal(expected, {**expected, "nested": [False, "x"]})
        )


class AllocationItemCodecTests(unittest.TestCase):
    @staticmethod
    def _global_models() -> list[runner.CompactCoordinateModel]:
        models: list[runner.CompactCoordinateModel] = []
        for coordinate in range(128):
            objectives = [{}]
            for cardinality in range(1, 257):
                # Coordinate zero strictly benefits from its first bit.  All
                # other width choices are plateaus, making an all-zero vector
                # structurally valid but not the frozen DP winner.
                numerator = 10 if coordinate == 0 and cardinality == 1 else 0
                objectives.append(
                    {
                        "binary_grid_exponent": -298,
                        "denominator": "1",
                        "numerator": str(numerator),
                    }
                )
            models.append(
                runner.CompactCoordinateModel(
                    [0, *range(1, 257)],
                    objectives,
                    [array.array("I") for _ in range(257)],
                    [array.array("Q") for _ in range(257)],
                    256,
                )
            )
        return models

    def test_product_writer_is_little_endian_and_terminal(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="a4-1s-allocation-item-test-"
        ) as directory:
            path = Path(directory) / "product-request.bin"
            file_bytes, peak_live_bytes = runner._write_allocation_item_input(
                path, item_id=0, models=self._global_models()
            )
            payload = path.read_bytes()
        self.assertEqual(payload[:8], b"A4ALI001")
        self.assertEqual(struct.unpack_from("<III", payload, 8), (1, 1, 0))
        self.assertEqual(payload[-8:], b"A4AIEND1")
        self.assertEqual(file_bytes, len(payload))
        self.assertGreaterEqual(peak_live_bytes, file_bytes)

    def test_product_parser_rejects_nonoptimal_valid_cardinalities(self) -> None:
        payload = bytearray(b"A4ALO001")
        payload.extend(struct.pack("<III", 1, 1, 0))
        payload.extend(struct.pack("<III", 16, 0, 2))
        # The selected (1,16) product fills all 16 states and its exact
        # objective is self-consistent, but the fixture's frozen optimum is
        # (2,8) with objective zero.
        payload.extend(struct.pack("<IIIB", 0, 1, 1, 1))
        payload.extend(struct.pack("<IIIB", 1, 16, 16, 1))
        payload.extend(struct.pack("<QB", 16, 1))
        payload.extend(struct.pack("<i", -298))
        payload.extend(struct.pack("<I", 2))
        payload.extend(b"10")
        payload.extend(struct.pack("<I", 1))
        payload.extend(b"1")
        payload.extend(struct.pack("<Q", 16))
        payload.extend(b"A4AOEND1")
        with tempfile.TemporaryDirectory(
            prefix="a4-1s-allocation-item-test-"
        ) as directory:
            path = Path(directory) / "nonoptimal-valid-product.bin"
            path.write_bytes(payload)
            with self.assertRaisesRegex(
                runner.GateFailure, "optimum/tie/result replay mismatch"
            ):
                runner._parse_allocation_item_output(
                    path, expected_item_id=0, models=self._global_models()
                )

    def test_global_parser_rejects_nonoptimal_valid_widths(self) -> None:
        payload = bytearray(b"A4ALO001")
        payload.extend(struct.pack("<III", 1, 2, 256))
        payload.extend(struct.pack("<II", 256, 128))
        payload.extend(struct.pack("<IB", 0, 1))
        payload.extend(struct.pack("<i", -298))
        payload.extend(struct.pack("<I", 2))
        payload.extend(b"10")
        payload.extend(struct.pack("<I", 1))
        payload.extend(b"1")
        payload.extend(
            struct.pack("<QI", runner._global_transition_count(128, 256), 128)
        )
        for coordinate in range(128):
            payload.extend(struct.pack("<IBIIB", coordinate, 0, 1, 1, 1))
        payload.extend(b"A4AOEND1")
        with tempfile.TemporaryDirectory(
            prefix="a4-1s-allocation-item-test-"
        ) as directory:
            path = Path(directory) / "nonoptimal-valid-global.bin"
            path.write_bytes(payload)
            with self.assertRaisesRegex(
                runner.GateFailure, "optimum/tie/result replay mismatch"
            ):
                runner._parse_allocation_item_output(
                    path, expected_item_id=256, models=self._global_models()
                )


if __name__ == "__main__":
    unittest.main()
