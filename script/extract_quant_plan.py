#!/usr/bin/env python3
"""Extract SAQ dynamic quantization plans from create_index logs.

The SAQ C++ index builder logs plans like:

    Dynamic bits allocation plan:
    4bits: | 0 -> 64 (64d 5b) | 64 -> 192 (128d 3b)

This script parses that line from stdin or one or more log files and writes a
CSV table that can be joined with per-dimension variance/rank-boundary dumps.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Iterable, TextIO


PLAN_RE = re.compile(r"(?P<avg_bits>[0-9]+(?:\.[0-9]+)?)bits:\s*(?P<body>.*)")
SEGMENT_RE = re.compile(
    r"\|\s*(?P<start>\d+)\s*->\s*(?P<end>\d+)\s*"
    r"\((?P<dim_len>\d+)d\s+(?P<bits>\d+)b\)"
)


def iter_lines(paths: list[Path]) -> Iterable[tuple[str, int, str]]:
    if not paths:
        for line_no, line in enumerate(sys.stdin, 1):
            yield "-", line_no, line.rstrip("\n")
        return

    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line_no, line in enumerate(handle, 1):
                yield str(path), line_no, line.rstrip("\n")


def parse_plan_lines(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    plan_id = 0
    for source, line_no, line in iter_lines(paths):
        plan_match = PLAN_RE.search(line)
        if plan_match is None:
            continue

        body = plan_match.group("body")
        segments = list(SEGMENT_RE.finditer(body))
        if not segments:
            continue

        for segment_id, segment in enumerate(segments):
            start_dim = int(segment.group("start"))
            end_dim = int(segment.group("end"))
            dim_len = int(segment.group("dim_len"))
            bits = int(segment.group("bits"))
            if end_dim - start_dim != dim_len:
                raise ValueError(
                    f"{source}:{line_no}: segment length mismatch: "
                    f"{start_dim}->{end_dim} but label says {dim_len}d"
                )
            rows.append(
                {
                    "source": source,
                    "line_no": str(line_no),
                    "plan_id": str(plan_id),
                    "avg_bits_label": plan_match.group("avg_bits"),
                    "segment_id": str(segment_id),
                    "start_dim": str(start_dim),
                    "end_dim": str(end_dim),
                    "dim_len": str(dim_len),
                    "bits": str(bits),
                }
            )
        plan_id += 1
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse SAQ dynamic bit allocation plans from logs into CSV."
    )
    parser.add_argument(
        "logs",
        nargs="*",
        type=Path,
        help="Log files to parse. If omitted, read stdin.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output CSV path. Defaults to stdout.",
    )
    return parser.parse_args()


def write_csv(rows: list[dict[str, str]], output: TextIO) -> None:
    fields = [
        "source",
        "line_no",
        "plan_id",
        "avg_bits_label",
        "segment_id",
        "start_dim",
        "end_dim",
        "dim_len",
        "bits",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
    args = parse_args()
    rows = parse_plan_lines(args.logs)
    if args.output is None:
        write_csv(rows, sys.stdout)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            write_csv(rows, handle)
    if not rows:
        print("warning: no SAQ quantization plan lines found", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
