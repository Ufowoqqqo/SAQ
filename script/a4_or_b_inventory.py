#!/usr/bin/env python3
"""Build the frozen A4-OR-B fit/held-out inventory from IVF assignments."""

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
EXTRAS = ROWS_PER_SPLIT - CELLS * BASE_PER_CELL


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


def allocate(pool_sizes: list[int]) -> list[int]:
    if len(pool_sizes) != CELLS or min(pool_sizes) < BASE_PER_CELL:
        raise ValueError("every split pool must contain at least two rows per cell")
    capacity = [size - BASE_PER_CELL for size in pool_sizes]
    total = sum(capacity)
    if total < EXTRAS:
        raise ValueError("split pool is too small")
    quotient = [EXTRAS * value // total for value in capacity]
    remainder = [EXTRAS * value % total for value in capacity]
    missing = EXTRAS - sum(quotient)
    order = sorted(range(CELLS), key=lambda c: (-remainder[c], c))
    for cell in order[:missing]:
        quotient[cell] += 1
    quotas = [BASE_PER_CELL + value for value in quotient]
    if sum(quotas) != ROWS_PER_SPLIT:
        raise AssertionError("quota sum")
    if any(quota > size for quota, size in zip(quotas, pool_sizes)):
        raise AssertionError("quota exceeds pool")
    return quotas


def build(dataset_id: str, assignments: list[int]) -> list[tuple]:
    cells: dict[int, list[tuple[bytes, int]]] = defaultdict(list)
    for vector_id, cell_id in enumerate(assignments):
        if not 0 <= cell_id < CELLS:
            raise ValueError(f"invalid cell {cell_id} at vector {vector_id}")
        cells[cell_id].append((digest(dataset_id, cell_id, vector_id), vector_id))
    if len(cells) != CELLS or min(map(len, cells.values())) < 4:
        raise ValueError("all 512 cells must contain at least four base rows")

    pools: dict[str, list[list[tuple[bytes, int]]]] = {
        "fit": [[] for _ in range(CELLS)],
        "heldout": [[] for _ in range(CELLS)],
    }
    for cell_id in range(CELLS):
        ordered = sorted(cells[cell_id])
        pools["fit"][cell_id] = ordered[0::2]
        pools["heldout"][cell_id] = ordered[1::2]

    selected: dict[str, list[list[tuple[bytes, int]]]] = {}
    for split in ("fit", "heldout"):
        quotas = allocate([len(rows) for rows in pools[split]])
        selected[split] = [
            pools[split][cell][: quotas[cell]] for cell in range(CELLS)
        ]

    output: list[tuple] = []
    for split in ("fit", "heldout"):
        for cell_id in range(CELLS):
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
    return output


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
    rows = build("self_test", assignments)
    fit = [row for row in rows if row[0] == "fit"]
    heldout = [row for row in rows if row[0] == "heldout"]
    assert len(fit) == ROWS_PER_SPLIT
    assert len(heldout) == ROWS_PER_SPLIT
    assert len({row[1] for row in fit}) == CELLS
    assert len({row[1] for row in heldout}) == CELLS
    assert {sum(row[1] == cell for row in fit) for cell in range(CELLS)} == {16}
    assert {sum(row[1] == cell for row in heldout) for cell in range(CELLS)} == {
        16
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-id")
    parser.add_argument("--cluster-ids", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("PASS inventory_self_test")
        return 0
    if not args.dataset_id or not args.cluster_ids or not args.output:
        parser.error("--dataset-id, --cluster-ids, and --output are required")
    assignments = read_single_ivecs(args.cluster_ids)
    rows = build(args.dataset_id, assignments)
    write_tsv(args.output, rows)
    fit_count = sum(row[0] == "fit" for row in rows)
    heldout_count = sum(row[0] == "heldout" for row in rows)
    pair_count = sum(row[6] == "left" for row in rows)
    print(
        f"PASS rows={len(assignments)} fit={fit_count} "
        f"heldout={heldout_count} pairs={pair_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
