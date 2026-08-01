#!/usr/bin/env python3
"""Run the frozen A/D/PQ/OPQ natural-query matrix."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "structured_2d")
)
import run_natural_matrix as inherited
from run_timing_matrix import Cell


def physical_id(dataset: str, budget: int, logical: str) -> str:
    suffix = "B4" if budget == 32 else "B8"
    if logical == "A128":
        return f"A128_{suffix}"
    if logical == "D128_FULL":
        return f"D128_{suffix}"
    if logical.startswith("PQ128_") and dataset == "sift":
        return f"PQFULL_M{32 if budget == 32 else 64}X8"
    if logical.startswith("OPQ128_"):
        prefix = "OPQFULL" if dataset == "sift" else "OPQHEAD"
        return f"{prefix}_M{32 if budget == 32 else 64}X8"
    return logical


def cells(_: Path) -> list[Cell]:
    result: list[Cell] = []
    for dataset in ("sift", "gist"):
        for nlist in (1024, 4096):
            for budget in (32, 64):
                width = 32 if budget == 32 else 64
                logicals = (
                    "A128",
                    "D128_FULL",
                    f"PQ128_M{width}X8",
                    f"OPQ128_M{width}X8",
                )
                for logical in logicals:
                    result.append(
                        Cell(
                            dataset,
                            nlist,
                            budget,
                            logical,
                            physical_id(dataset, budget, logical),
                        )
                    )
    return result


if __name__ == "__main__":
    inherited.cells = cells
    raise SystemExit(inherited.main())
