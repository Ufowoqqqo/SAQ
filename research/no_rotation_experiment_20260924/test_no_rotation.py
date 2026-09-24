import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import no_rotation as n


class NoRotationTest(unittest.TestCase):
    def test_actual_rescaled_error_independent_formula(self):
        x = np.random.RandomState(71).normal(size=(12, 8))
        x[0] = 0
        widths = [2, 3, 4, 5]
        q = n.ref.adjusted_lattice(x, widths)
        expected = []
        for a, b in zip(x, q):
            expected.append(0 if a@a == 0 else sum((a - b*((a@a)/(a@b)))**2))
        measured = n.encoded_losses(x, widths)
        np.testing.assert_allclose(measured['rescaled_sse'], expected, rtol=1e-12, atol=1e-12)

    def test_no_rotation_arm_reaches_encoder_unchanged(self):
        rng = np.random.RandomState(4)
        fit, evaluation = rng.normal(size=(16, 8)), rng.normal(size=(12, 8))
        original_fit, original_eval = fit.copy(), evaluation.copy()
        captured = []
        implementation = n.encoded_losses
        def record(values, widths):
            captured.append(values.copy())
            return implementation(values, widths)
        with patch.object(n, 'encoded_losses', side_effect=record):
            losses, allocations, _, _ = n.run_fold(fit, evaluation, [n.ref.Segment(0, 8, 3)])
        np.testing.assert_array_equal(captured[0], evaluation)
        np.testing.assert_array_equal(captured[1], evaluation)
        self.assertFalse(np.array_equal(captured[2], evaluation))
        np.testing.assert_array_equal(fit, original_fit)
        np.testing.assert_array_equal(evaluation, original_eval)
        for rotation, allocation in losses:
            bits = [r['bits_per_coordinate'] for r in allocations
                    if r['rotation'] == rotation and r['allocation'] == allocation]
            self.assertEqual(2*sum(bits), 24)

    def test_held_out_values_cannot_change_allocation(self):
        rng = np.random.RandomState(5)
        fit = rng.normal(size=(20, 8)) * np.arange(1, 9)
        first = n.run_fold(fit, rng.normal(size=(9, 8)), [n.ref.Segment(0, 8, 3)])
        second = n.run_fold(fit, rng.normal(size=(9, 8))*100, [n.ref.Segment(0, 8, 3)])
        self.assertEqual(first[1], second[1])
        self.assertEqual(first[2], second[2])

    def test_zero_tail_is_charged_identically(self):
        rng = np.random.RandomState(6)
        fit, evaluation = rng.normal(size=(20, 8)), rng.normal(size=(9, 8))
        plan = [n.ref.Segment(0, 4, 3), n.ref.Segment(4, 8, 0)]
        full = n.run_fold(fit, evaluation, plan)[0]
        head = n.run_fold(fit[:, :4], evaluation[:, :4], [n.ref.Segment(0, 4, 3)])[0]
        for arm in full:
            for metric in full[arm]:
                np.testing.assert_allclose(full[arm][metric]-head[arm][metric],
                                           np.sum(evaluation[:, 4:]**2, axis=1))

    def test_zero_input_is_zero_error(self):
        for loss in n.encoded_losses(np.zeros((3, 8)), [4]*4).values():
            np.testing.assert_array_equal(loss, np.zeros(3))

    def test_invalid_full_panel_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fake.fvecs'
            path.write_bytes(b'not a full panel')
            with self.assertRaises(ValueError):
                n.ref.read_panel(path, 960)


if __name__ == '__main__':
    unittest.main()
