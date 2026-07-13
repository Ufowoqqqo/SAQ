#!/usr/bin/env python3
"""Timing bootstrap for the frozen A4-1S synthetic-only command."""

from a4_1s_bootstrap_usage import capture_start


_START_CPU_US, _START_WALL_NS = capture_start()

# Scientific, artifact, reference, and NumPy-capable modules are intentionally
# imported only after the authority-bearing start snapshot above.
from a4_1s_runner import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(_START_CPU_US, _START_WALL_NS))
