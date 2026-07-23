#!/usr/bin/env python3
"""Build an A4-OR-B fit/held-out inventory from IVF assignments."""

from __future__ import annotations

import argparse
import hashlib
import struct
from collections import defaultdict
from pathlib import Path

PROTOCOL = "saq-attempt4-a4-1-20260713-schema2"
CELLS = 512
ROWS_PER_SPLIT = 8192
BASE_PER_CELL = 2
STRICT_RULE = "strict-all-cells"
ELIGIBLE_RULE = "eligible-min4-v1"


def read_single_ivecs(path: Path) -> list[int]:
    data = path.read_bytes()
    if len(data) % 8:
        raise ValueError("one-column ivecs size is not divisible by 8")
    result: list[int] = []
    for offset in range(0, len(data), 8):
        dimension, value = struct.unpack_from("<ii", data, offset)
        if dimension != 1:
            raise ValueError(f"expected ivecs dimension 1 at row {len(result)}")
        result.append(value)
    return result


def digest(dataset_id: str, cell_id: int, vector_id: int) -> bytes:
    key = f"{PROTOCOL}|{dataset_id}|{cell_id}|{vector_id}".encode()
    return hashlib.sha256(key).digest()


def allocate(cell_ids: list[int], pool_sizes: list[int]) -> list[int]:
    if not cell_ids or len(pool_sizes) != len(cell_ids):
        raise ValueError("cell ids and pool sizes must be nonempty and aligned")
    if min(pool_sizes) < BASE_PER_CELL:
        raise ValueError("every split pool must contain at least two rows per cell")
    capacity = [size - BASE_PER_CELL for size in pool_sizes]
    total = sum(capacity)
    extras = ROWS_PER_SPLIT - len(cell_ids) * BASE_PER_CELL
    if extras < 0:
        raise ValueError("reserved rows exceed the split size")
    if total < extras:
        raise ValueError("split pool is too small")
    quotient = [extras * value // total for value in capacity]
    remainder = [extras * value % total for value in capacity]
    missing = extras - sum(quotient)
    order = sorted(
        range(len(cell_ids)),
        key=lambda index: (-remainder[index], cell_ids[index]),
    )
    for index in order[:missing]:
        quotient[index] += 1
    quotas = [BASE_PER_CELL + value for value in quotient]
    if sum(quotas) != ROWS_PER_SPLIT:
        raise AssertionError("quota sum")
    if any(quota > size for quota, size in zip(quotas, pool_sizes)):
        raise AssertionError("quota exceeds pool")
    return quotas


def build(
    dataset_id: str,
    assignments: list[int],
    sampling_rule: str,
) -> tuple[list[tuple], dict[str, int]]:
    cells: dict[int, list[tuple[bytes, int]]] = defaultdict(list)
    for vector_id, cell_id in enumerate(assignments):
        if not 0 <= cell_id < CELLS:
            raise ValueError(f"invalid cell {cell_id} at vector {vector_id}")
        cells[cell_id].append((digest(dataset_id, cell_id, vector_id), vector_id))
    if sampling_rule == STRICT_RULE:
        if len(cells) != CELLS or min(map(len, cells.values())) < 4:
            raise ValueError("all 512 cells must contain at least four base rows")
        cell_ids = list(range(CELLS))
    elif sampling_rule == ELIGIBLE_RULE:
        cell_ids = [
            cell_id for cell_id in range(CELLS) if len(cells[cell_id]) >= 4
        ]
        if not cell_ids:
            raise ValueError("no cell contains at least four base rows")
    else:
        raise ValueError(f"unknown sampling rule: {sampling_rule}")

    pools: dict[str, dict[int, list[tuple[bytes, int]]]] = {
        "fit": {},
        "heldout": {},
    }
    for cell_id in cell_ids:
        ordered = sorted(cells[cell_id])
        pools["fit"][cell_id] = ordered[0::2]
        pools["heldout"][cell_id] = ordered[1::2]

    selected: dict[str, dict[int, list[tuple[bytes, int]]]] = {}
    for split in ("fit", "heldout"):
        quotas = allocate(
            cell_ids,
            [len(pools[split][cell_id]) for cell_id in cell_ids],
        )
        selected[split] = {
            cell_id: pools[split][cell_id][:quota]
            for cell_id, quota in zip(cell_ids, quotas)
        }

    output: list[tuple] = []
    for split in ("fit", "heldout"):
        for cell_id in cell_ids:
            rows = selected[split][cell_id]
            for selected_rank, (raw_digest, vector_id) in enumerate(rows):
                pair_id = selected_rank // 2 if split == "heldout" else -1
                pair_side = (
                    "left" if selected_rank % 2 == 0 else "right"
                ) if split == "heldout" else "-"
                if split == "heldout" and selected_rank + 1 == len(rows) and (
                    selected_rank % 2 == 0
                ):
                    pair_id, pair_side = -1, "unused"
                output.append(
                    (
                        split,
                        cell_id,
                        vector_id,
                        raw_digest.hex(),
                        selected_rank,
                        pair_id,
                        pair_side,
                    )
                )
    stats = {
        "occupied_cells": len(cells),
        "eligible_cells": len(cell_ids),
        "excluded_cells": CELLS - len(cell_ids),
        "excluded_rows": sum(
            len(rows) for cell_id, rows in cells.items() if cell_id not in cell_ids
        ),
    }
    return output, stats


def write_tsv(path: Path, rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "split\tcell_id\tvector_id\tdigest_hex\tselected_rank"
            "\tpair_id\tpair_side\n"
        )
        for row in rows:
            handle.write("\t".join(map(str, row)) + "\n")


def self_test() -> None:
    assignments = [cell for cell in range(CELLS) for _ in range(40)]
    rows, stats = build("self_test", assignments, STRICT_RULE)
    fit = [row for row in rows if row[0] == "fit"]
    heldout = [row for row in rows if row[0] == "heldout"]
    assert stats["eligible_cells"] == CELLS
    assert len(fit) == ROWS_PER_SPLIT
    assert len(heldout) == ROWS_PER_SPLIT
    assert len({row[1] for row in fit}) == CELLS
    assert len({row[1] for row in heldout}) == CELLS
    assert {sum(row[1] == cell for row in fit) for cell in range(CELLS)} == {16}
    assert {sum(row[1] == cell for row in heldout) for cell in range(CELLS)} == {
        16
    }

    sparse = assignments.copy()
    sparse.extend([CELLS - 1])
    sparse = [
        cell_id
        for vector_id, cell_id in enumerate(sparse)
        if cell_id != 0 or vector_id < 3
    ]
    try:
        build("self_test_sparse", sparse, STRICT_RULE)
    except ValueError as error:
        assert "at least four" in str(error)
    else:
        raise AssertionError("strict rule accepted a sparse cell")
    rows, stats = build("self_test_sparse", sparse, ELIGIBLE_RULE)
    assert stats["eligible_cells"] == CELLS - 1
    assert stats["excluded_cells"] == 1
    assert stats["excluded_rows"] == 3
    assert sum(row[0] == "fit" for row in rows) == ROWS_PER_SPLIT
    assert sum(row[0] == "heldout" for row in rows) == ROWS_PER_SPLIT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-id")
    parser.add_argument("--cluster-ids", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--sampling-rule",
        choices=(STRICT_RULE, ELIGIBLE_RULE),
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("PASS inventory_self_test")
        return 0
    if (
        not args.dataset_id
        or not args.cluster_ids
        or not args.output
        or not args.sampling_rule
    ):
        parser.error(
            "--dataset-id, --cluster-ids, --output, and --sampling-rule "
            "are required"
        )
    assignments = read_single_ivecs(args.cluster_ids)
    rows, stats = build(args.dataset_id, assignments, args.sampling_rule)
    write_tsv(args.output, rows)
    fit_count = sum(row[0] == "fit" for row in rows)
    heldout_count = sum(row[0] == "heldout" for row in rows)
    pair_count = sum(row[6] == "left" for row in rows)
    print(
        f"PASS sampling_rule={args.sampling_rule} rows={len(assignments)} "
        f"occupied_cells={stats['occupied_cells']} "
        f"eligible_cells={stats['eligible_cells']} "
        f"excluded_cells={stats['excluded_cells']} "
        f"excluded_rows={stats['excluded_rows']} fit={fit_count} "
        f"heldout={heldout_count} pairs={pair_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
