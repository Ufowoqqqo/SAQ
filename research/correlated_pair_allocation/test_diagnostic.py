import tempfile
import unittest
from pathlib import Path

import numpy as np

from research.correlated_pair_allocation import diagnostic as subject


class DiagnosticTest(unittest.TestCase):
    def test_correlation_pairing_recovers_strong_pairs(self):
        correlation = np.eye(subject.DIMENSIONS)
        for first in range(0, subject.DIMENSIONS, 2):
            correlation[first, first + 1] = correlation[first + 1, first] = 0.9
        self.assertEqual(subject.correlation_pairs(correlation), subject.adjacent_pairs())

    def test_fixed_total_dp_moves_bits_to_hard_group(self):
        curves = []
        for group in range(subject.GROUPS):
            scale = 100.0 if group == 0 else 1.0
            fit = {bits: scale * 2.0 ** (-bits) for bits in range(6, 11)}
            curves.append(subject.PairCurve(fit, fit.copy(), {bits: (bits // 2, bits - bits // 2) for bits in range(6, 11)}))
        allocation = subject.allocate_bits(curves)
        self.assertEqual(sum(allocation), subject.TOTAL_BITS)
        self.assertGreater(allocation[0], subject.UNIFORM_BITS)

    def test_fvec_reader_validates_and_selects(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiny.fvecs"
            dimensions = subject.DIMENSIONS
            rows = subject.ROWS
            # Exercise the row layout without materializing the full payload.
            row_bytes = 4 * (dimensions + 1)
            with path.open("wb") as output:
                vector = np.arange(dimensions, dtype="<f4")
                for _ in range(subject.SAMPLE_ROWS):
                    output.write(np.array([dimensions], dtype="<i4").tobytes())
                    output.write(vector.tobytes())
                output.seek(rows * row_bytes - 1)
                output.write(b"\0")
            indices = np.arange(subject.SAMPLE_ROWS, dtype=np.int64)
            values = subject.read_sample(path, indices)
            self.assertEqual(values.shape, (subject.SAMPLE_ROWS, dimensions))
            self.assertEqual(values[3, 17], 17.0)

    def test_local_curve_and_dp_are_deterministic(self):
        rng = np.random.RandomState(7)
        fit = rng.normal(size=(512, 2))
        evaluation = rng.normal(size=(512, 2))
        first = subject.pair_curve(fit, evaluation, (0, 1))
        second = subject.pair_curve(fit, evaluation, (0, 1))
        self.assertEqual(first.fit_sse, second.fit_sse)
        self.assertEqual(first.splits, second.splits)


if __name__ == "__main__":
    unittest.main()
