#!/usr/bin/env python3
"""Solve one dense maximum-weight perfect matching with NetworkX Blossom."""

from __future__ import annotations

import argparse
import itertools
import math
from pathlib import Path

import networkx as nx


WEIGHT_SCALE = 10**12


def solve(vertex_count: int, edges: list[tuple[int, int, float]]):
    expected = vertex_count * (vertex_count - 1) // 2
    if vertex_count <= 0 or vertex_count % 2 or len(edges) != expected:
        raise ValueError("complete even-order graph required")
    minimum = min(weight for _, _, weight in edges)
    maximum = max(weight for _, _, weight in edges)
    span = maximum - minimum
    graph = nx.Graph()
    graph.add_nodes_from(range(vertex_count))
    for first, second, weight in edges:
        scaled = 1 if span == 0 else 1 + round(
            (weight - minimum) / span * WEIGHT_SCALE
        )
        graph.add_edge(first, second, weight=scaled)
    matching = nx.max_weight_matching(
        graph, maxcardinality=True, weight="weight"
    )
    pairs = sorted(tuple(sorted(pair)) for pair in matching)
    if len(pairs) != vertex_count // 2:
        raise RuntimeError("NetworkX result is not perfect")
    flattened = list(itertools.chain.from_iterable(pairs))
    if sorted(flattened) != list(range(vertex_count)):
        raise RuntimeError("NetworkX result is not a partition")
    bound = vertex_count * span / (4 * WEIGHT_SCALE)
    return pairs, bound


def read_edges(path: Path):
    with path.open(encoding="utf-8") as source:
        header = source.readline().rstrip("\n").split("\t")
        if header != ["vertices", "first", "second", "weight"]:
            raise ValueError("edge header")
        rows = [line.rstrip("\n").split("\t") for line in source]
    vertex_counts = {int(row[0]) for row in rows}
    if len(vertex_counts) != 1:
        raise ValueError("vertex count")
    edges = [(int(row[1]), int(row[2]), float(row[3])) for row in rows]
    if not all(math.isfinite(weight) for _, _, weight in edges):
        raise ValueError("non-finite edge")
    return vertex_counts.pop(), edges


def exhaustive(vertex_count, weights, used=None):
    used = [False] * vertex_count if used is None else used
    try:
        first = used.index(False)
    except ValueError:
        return 0.0
    used[first] = True
    best = -math.inf
    for second in range(first + 1, vertex_count):
        if used[second]:
            continue
        used[second] = True
        best = max(
            best,
            weights[first, second] + exhaustive(vertex_count, weights, used),
        )
        used[second] = False
    used[first] = False
    return best


def self_test():
    for vertex_count in (2, 4, 6, 8, 10):
        for seed in range(7):
            edges = []
            weights = {}
            for first in range(vertex_count):
                for second in range(first + 1, vertex_count):
                    weight = float(
                        (first * 37 + second * 17 + first * second * 11 + seed * 13)
                        % 29
                        - 14
                    )
                    edges.append((first, second, weight))
                    weights[first, second] = weight
            pairs, _ = solve(vertex_count, edges)
            actual = sum(weights[pair] for pair in pairs)
            if actual != exhaustive(vertex_count, weights):
                raise RuntimeError("exhaustive mismatch")
    edges = []
    for first in range(128):
        for second in range(first + 1, 128):
            weight = 1000.0 if second == (first ^ 1) else float((first + second) % 7)
            edges.append((first, second, weight))
    pairs, _ = solve(128, edges)
    if any(second != (first ^ 1) for first, second in pairs):
        raise RuntimeError("128D preferred pair mismatch")
    print("solve_matching: PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.input is None or args.output is None:
        parser.error("input and output are required")
    vertex_count, edges = read_edges(args.input)
    pairs, bound = solve(vertex_count, edges)
    with args.output.open("w", encoding="utf-8") as destination:
        destination.write(f"rounding_bound\t{bound:.17g}\n")
        destination.write("first\tsecond\n")
        for first, second in pairs:
            destination.write(f"{first}\t{second}\n")


if __name__ == "__main__":
    main()
