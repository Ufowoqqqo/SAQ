#!/usr/bin/env python3
"""Write the frozen raw-diagnostic row selections for native extraction."""

import argparse
from pathlib import Path
import sys

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research.correlated_pair_allocation.diagnostic import sample_indices


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)
    for name, offset in (("sift", 0), ("gist", 1)):
        indices = np.asarray(sample_indices(offset), dtype="<u8")
        indices.tofile(args.output / f"{name}_indices.u64")


if __name__ == "__main__":
    main()
