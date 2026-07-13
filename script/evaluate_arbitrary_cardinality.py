#!/usr/bin/env python3
"""Offline reference evaluator for fixed-rate arbitrary-cardinality products.

The instrument intentionally does not import or modify SAQ. It solves exact
weighted one-dimensional L2 quantization on a discrete support, then compares
dyadic and arbitrary integer cardinalities under the same product capacity.
"""

from __future__ import annotations

import argparse
import heapq
import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class ScalarSolution:
    requested_cardinality: int
    effective_cardinality: int
    total_weight: float
    sse: float
    mean_squared_error: float
    centroids: tuple[float, ...]
    cluster_ranges: tuple[tuple[int, int], ...]
    cluster_weights: tuple[float, ...]


@dataclass(frozen=True)
class AllocationSolution:
    cardinalities: tuple[int, ...]
    used_states: int
    capacity: int
    distortion: float


def _validate_positive_integer(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _aggregate_support(
    values: Sequence[float],
    weights: Sequence[float] | None,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not values:
        raise ValueError("scalar support must not be empty")
    if weights is None:
        weights = [1.0] * len(values)
    if len(values) != len(weights):
        raise ValueError("values and weights must have the same length")

    pairs: list[tuple[float, float]] = []
    for raw_value, raw_weight in zip(values, weights):
        value = float(raw_value)
        weight = float(raw_weight)
        if not math.isfinite(value):
            raise ValueError("support values must be finite")
        if not math.isfinite(weight) or weight <= 0.0:
            raise ValueError("support weights must be finite and positive")
        pairs.append((value, weight))
    pairs.sort()

    distinct_values: list[float] = []
    distinct_weights: list[float] = []
    for value, weight in pairs:
        if distinct_values and value == distinct_values[-1]:
            distinct_weights[-1] += weight
        else:
            distinct_values.append(value)
            distinct_weights.append(weight)
    return tuple(distinct_values), tuple(distinct_weights)


def _prefix_sums(
    values: Sequence[float], weights: Sequence[float]
) -> tuple[list[float], list[float], list[float]]:
    weight_prefix = [0.0]
    sum_prefix = [0.0]
    sum_sq_prefix = [0.0]
    for value, weight in zip(values, weights):
        weight_prefix.append(weight_prefix[-1] + weight)
        sum_prefix.append(sum_prefix[-1] + weight * value)
        sum_sq_prefix.append(sum_sq_prefix[-1] + weight * value * value)
    return weight_prefix, sum_prefix, sum_sq_prefix


def _interval_statistics(
    begin: int,
    end: int,
    weight_prefix: Sequence[float],
    sum_prefix: Sequence[float],
    sum_sq_prefix: Sequence[float],
) -> tuple[float, float, float]:
    weight = weight_prefix[end] - weight_prefix[begin]
    value_sum = sum_prefix[end] - sum_prefix[begin]
    value_sum_sq = sum_sq_prefix[end] - sum_sq_prefix[begin]
    centroid = value_sum / weight
    sse = max(0.0, value_sum_sq - value_sum * value_sum / weight)
    return weight, centroid, sse


def exact_scalar_curve(
    values: Sequence[float],
    max_cardinality: int,
    weights: Sequence[float] | None = None,
) -> dict[int, ScalarSolution]:
    """Return globally optimal weighted 1D L2 solutions for every K.

    Clusters are contiguous on sorted support. The dynamic program minimizes
    weighted SSE for exactly min(K, H) nonempty intervals, where H is the
    number of distinct support points. For K > H, the additional labels are
    unused and distortion remains zero.
    """

    _validate_positive_integer(max_cardinality, "max_cardinality")
    support, support_weights = _aggregate_support(values, weights)
    support_size = len(support)
    effective_max = min(max_cardinality, support_size)
    weight_prefix, sum_prefix, sum_sq_prefix = _prefix_sums(
        support, support_weights
    )
    total_weight = weight_prefix[-1]

    dp = [[math.inf] * (support_size + 1) for _ in range(effective_max + 1)]
    split = [[-1] * (support_size + 1) for _ in range(effective_max + 1)]
    dp[0][0] = 0.0

    for cluster_count in range(1, effective_max + 1):
        for end in range(cluster_count, support_size + 1):
            best_cost = math.inf
            best_begin = -1
            for begin in range(cluster_count - 1, end):
                prior = dp[cluster_count - 1][begin]
                if not math.isfinite(prior):
                    continue
                candidate = prior + _interval_statistics(
                    begin,
                    end,
                    weight_prefix,
                    sum_prefix,
                    sum_sq_prefix,
                )[2]
                if candidate < best_cost or (
                    candidate == best_cost
                    and (best_begin < 0 or begin < best_begin)
                ):
                    best_cost = candidate
                    best_begin = begin
            dp[cluster_count][end] = best_cost
            split[cluster_count][end] = best_begin

    effective_solutions: dict[int, ScalarSolution] = {}
    for cluster_count in range(1, effective_max + 1):
        ranges: list[tuple[int, int]] = []
        end = support_size
        for cluster in range(cluster_count, 0, -1):
            begin = split[cluster][end]
            if begin < 0:
                raise RuntimeError("failed to reconstruct exact scalar DP")
            ranges.append((begin, end))
            end = begin
        ranges.reverse()

        centroids: list[float] = []
        cluster_weights: list[float] = []
        for begin, end in ranges:
            weight, centroid, _ = _interval_statistics(
                begin,
                end,
                weight_prefix,
                sum_prefix,
                sum_sq_prefix,
            )
            centroids.append(centroid)
            cluster_weights.append(weight)

        sse = max(0.0, dp[cluster_count][support_size])
        effective_solutions[cluster_count] = ScalarSolution(
            requested_cardinality=cluster_count,
            effective_cardinality=cluster_count,
            total_weight=total_weight,
            sse=sse,
            mean_squared_error=sse / total_weight,
            centroids=tuple(centroids),
            cluster_ranges=tuple(ranges),
            cluster_weights=tuple(cluster_weights),
        )

    curve: dict[int, ScalarSolution] = {}
    for requested in range(1, max_cardinality + 1):
        effective = min(requested, support_size)
        base = effective_solutions[effective]
        curve[requested] = ScalarSolution(
            requested_cardinality=requested,
            effective_cardinality=effective,
            total_weight=base.total_weight,
            sse=base.sse,
            mean_squared_error=base.mean_squared_error,
            centroids=base.centroids,
            cluster_ranges=base.cluster_ranges,
            cluster_weights=base.cluster_weights,
        )
    return curve


def _dyadic_cardinalities(max_cardinality: int) -> tuple[int, ...]:
    values: list[int] = []
    cardinality = 1
    while cardinality <= max_cardinality:
        values.append(cardinality)
        cardinality *= 2
    return tuple(values)


def optimize_product_allocation(
    curves: Sequence[Mapping[int, ScalarSolution]],
    capacity: int,
    *,
    dyadic_only: bool,
) -> AllocationSolution:
    """Optimize additive distortion under a product-cardinality capacity."""

    _validate_positive_integer(capacity, "capacity")
    if not curves:
        raise ValueError("at least one scalar curve is required")

    # State value is (distortion, selected cardinalities). The key is product.
    frontier: dict[int, tuple[float, tuple[int, ...]]] = {1: (0.0, ())}
    for curve in curves:
        if not curve:
            raise ValueError("scalar curves must not be empty")
        available = sorted(k for k in curve if k <= capacity)
        if dyadic_only:
            dyadic = set(_dyadic_cardinalities(capacity))
            available = [k for k in available if k in dyadic]
        if not available or available[0] != 1:
            raise ValueError("each scalar curve must include cardinality one")

        next_frontier: dict[int, tuple[float, tuple[int, ...]]] = {}
        for prior_product, (prior_cost, prior_cardinalities) in frontier.items():
            for cardinality in available:
                product = prior_product * cardinality
                if product > capacity:
                    break
                candidate = (
                    prior_cost + curve[cardinality].mean_squared_error,
                    prior_cardinalities + (cardinality,),
                )
                incumbent = next_frontier.get(product)
                if incumbent is None or candidate < incumbent:
                    next_frontier[product] = candidate
        frontier = next_frontier

    if not frontier:
        raise RuntimeError("no feasible product allocation")

    # At identical distortion, use more of the already-paid fixed word; then
    # use lexicographic cardinality order as a deterministic final tie rule.
    best_product, (best_cost, best_cardinalities) = min(
        frontier.items(),
        key=lambda item: (item[1][0], -item[0], item[1][1]),
    )
    return AllocationSolution(
        cardinalities=best_cardinalities,
        used_states=best_product,
        capacity=capacity,
        distortion=best_cost,
    )


def mixed_radix_encode(codes: Sequence[int], radices: Sequence[int]) -> int:
    if len(codes) != len(radices) or not codes:
        raise ValueError("codes and radices must have the same nonzero length")
    address = 0
    multiplier = 1
    for code, radix in zip(codes, radices):
        _validate_positive_integer(radix, "radix")
        if not isinstance(code, int) or isinstance(code, bool) or not 0 <= code < radix:
            raise ValueError("mixed-radix code is out of range")
        address += code * multiplier
        multiplier *= radix
    return address


def mixed_radix_decode(address: int, radices: Sequence[int]) -> tuple[int, ...]:
    if not isinstance(address, int) or isinstance(address, bool) or address < 0:
        raise ValueError("address must be a nonnegative integer")
    if not radices:
        raise ValueError("at least one radix is required")
    product = math.prod(radices)
    if address >= product:
        raise ValueError("address is outside the mixed-radix product")

    remainder = address
    codes: list[int] = []
    for radix in radices:
        _validate_positive_integer(radix, "radix")
        codes.append(remainder % radix)
        remainder //= radix
    return tuple(codes)


def build_squared_l2_lookup(
    query: Sequence[float],
    centroids: Sequence[Sequence[float]],
    radices: Sequence[int],
    capacity: int,
) -> list[float | None]:
    if len(query) != len(centroids) or len(query) != len(radices):
        raise ValueError("query, centroids, and radices must have equal length")
    _validate_positive_integer(capacity, "capacity")
    used_states = math.prod(radices)
    if used_states > capacity:
        raise ValueError("mixed-radix product exceeds lookup capacity")
    for values, radix in zip(centroids, radices):
        if len(values) != radix:
            raise ValueError("each centroid table must match its radix")

    table: list[float | None] = [None] * capacity
    for address in range(used_states):
        codes = mixed_radix_decode(address, radices)
        table[address] = sum(
            (float(query_value) - float(values[code])) ** 2
            for query_value, values, code in zip(query, centroids, codes)
        )
    return table


def shannon_entropy(weights: Sequence[float]) -> float:
    if not weights:
        raise ValueError("weights must not be empty")
    total = sum(float(weight) for weight in weights)
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("weights must have positive finite sum")
    entropy = 0.0
    for raw_weight in weights:
        weight = float(raw_weight)
        if not math.isfinite(weight) or weight < 0.0:
            raise ValueError("weights must be finite and nonnegative")
        if weight > 0.0:
            probability = weight / total
            entropy -= probability * math.log2(probability)
    return entropy


def huffman_code_lengths(weights: Sequence[float]) -> tuple[int, ...]:
    """Return deterministic optimal binary-prefix lengths for positive symbols."""

    if not weights:
        raise ValueError("weights must not be empty")
    numeric = tuple(float(weight) for weight in weights)
    if any(not math.isfinite(weight) or weight <= 0.0 for weight in numeric):
        raise ValueError("Huffman symbol weights must be finite and positive")
    if len(numeric) == 1:
        return (0,)

    heap: list[tuple[float, int, tuple[int, ...]]] = [
        (weight, index, (index,)) for index, weight in enumerate(numeric)
    ]
    heapq.heapify(heap)
    lengths = [0] * len(numeric)
    while len(heap) > 1:
        left_weight, left_first, left_symbols = heapq.heappop(heap)
        right_weight, right_first, right_symbols = heapq.heappop(heap)
        symbols = left_symbols + right_symbols
        for symbol in symbols:
            lengths[symbol] += 1
        heapq.heappush(
            heap,
            (left_weight + right_weight, min(left_first, right_first), symbols),
        )
    return tuple(lengths)


def expected_prefix_length(weights: Sequence[float]) -> float:
    lengths = huffman_code_lengths(weights)
    total = sum(float(weight) for weight in weights)
    return sum(
        float(weight) * length for weight, length in zip(weights, lengths)
    ) / total


def _serialize_curve(curve: Mapping[int, ScalarSolution]) -> list[dict[str, object]]:
    return [asdict(curve[cardinality]) for cardinality in sorted(curve)]


def evaluate_weighted_dimensions(
    dimensions: Sequence[Mapping[str, object]],
    block_bits: int,
    max_cardinality: int | None = None,
) -> dict[str, object]:
    if not isinstance(block_bits, int) or isinstance(block_bits, bool) or block_bits < 0:
        raise ValueError("block_bits must be a nonnegative integer")
    capacity = 1 << block_bits
    if max_cardinality is None:
        max_cardinality = capacity
    _validate_positive_integer(max_cardinality, "max_cardinality")

    curves: list[dict[int, ScalarSolution]] = []
    for dimension in dimensions:
        values = dimension.get("values")
        weights = dimension.get("weights")
        if not isinstance(values, list):
            raise ValueError("each dimension must contain a values list")
        if weights is not None and not isinstance(weights, list):
            raise ValueError("dimension weights must be a list when present")
        curves.append(exact_scalar_curve(values, max_cardinality, weights))

    arbitrary = optimize_product_allocation(curves, capacity, dyadic_only=False)
    dyadic = optimize_product_allocation(curves, capacity, dyadic_only=True)
    return {
        "block_bits": block_bits,
        "capacity": capacity,
        "dimension_count": len(dimensions),
        "max_cardinality": max_cardinality,
        "arbitrary": asdict(arbitrary),
        "dyadic": asdict(dyadic),
        "curves": [_serialize_curve(curve) for curve in curves],
    }


def run_synthetic_witness() -> dict[str, object]:
    dimensions: list[dict[str, object]] = [
        {"values": [-1.0, 0.0, 1.0], "weights": [1.0, 1.0, 1.0]},
        {
            "values": [-2.0, -1.0, 0.0, 1.0, 2.0],
            "weights": [1.0, 1.0, 1.0, 1.0, 1.0],
        },
    ]
    evaluation = evaluate_weighted_dimensions(dimensions, block_bits=4)
    curves = [
        exact_scalar_curve(
            dimension["values"], 16, dimension["weights"]  # type: ignore[arg-type]
        )
        for dimension in dimensions
    ]
    arbitrary = optimize_product_allocation(curves, 16, dyadic_only=False)

    selected = [
        curve[cardinality]
        for curve, cardinality in zip(curves, arbitrary.cardinalities)
    ]
    centroid_tables = [solution.centroids for solution in selected]
    query = (0.25, -0.5)
    lookup = build_squared_l2_lookup(
        query, centroid_tables, arbitrary.cardinalities, arbitrary.capacity
    )

    encoded_addresses: set[int] = set()
    max_lookup_difference = 0.0
    for codes in itertools.product(
        *(range(cardinality) for cardinality in arbitrary.cardinalities)
    ):
        address = mixed_radix_encode(codes, arbitrary.cardinalities)
        encoded_addresses.add(address)
        if mixed_radix_decode(address, arbitrary.cardinalities) != codes:
            raise RuntimeError("mixed-radix encode/decode mismatch")
        direct = sum(
            (query_value - centroid_tables[dimension][code]) ** 2
            for dimension, (query_value, code) in enumerate(zip(query, codes))
        )
        table_value = lookup[address]
        if table_value is None:
            raise RuntimeError("valid address has no lookup entry")
        max_lookup_difference = max(
            max_lookup_difference, abs(table_value - direct)
        )

    marginal_entropy = [
        shannon_entropy(solution.cluster_weights) for solution in selected
    ]
    marginal_huffman = [
        expected_prefix_length(solution.cluster_weights) for solution in selected
    ]
    joint_weights = [1.0] * arbitrary.used_states
    three_symbol_huffman = expected_prefix_length([1.0, 1.0, 1.0])

    result = {
        "protocol": "A4-0",
        "status": "PASS",
        "scope": "synthetic instrument validation only",
        "budget_semantics": {
            "stored_block_bits": 4,
            "fixed_address_capacity": 16,
            "constraint": "product(K_j) <= 2^B_g",
        },
        "source": {
            "dimensions": dimensions,
            "independence": True,
            "joint_support_size": 15,
        },
        "allocation": {
            "arbitrary": asdict(arbitrary),
            "dyadic": evaluation["dyadic"],
        },
        "unrestricted_block_vq_support_oracle": {
            "capacity": 16,
            "joint_support_size": 15,
            "distortion": 0.0,
            "reason": "one codeword per discrete joint atom fits in the capacity",
        },
        "mixed_radix": {
            "radices": arbitrary.cardinalities,
            "valid_addresses": len(encoded_addresses),
            "unused_addresses": arbitrary.capacity - len(encoded_addresses),
            "query": query,
            "lookup_entries": len(lookup),
            "max_lookup_direct_difference": max_lookup_difference,
        },
        "entropy": {
            "selected_marginal_shannon_bits": marginal_entropy,
            "selected_marginal_shannon_sum_bits": sum(marginal_entropy),
            "selected_separate_huffman_expected_bits": marginal_huffman,
            "selected_separate_huffman_sum_bits": sum(marginal_huffman),
            "selected_joint_huffman_expected_bits": expected_prefix_length(
                joint_weights
            ),
            "three_by_three_explanation": {
                "one_factor_huffman_expected_bits": three_symbol_huffman,
                "two_factor_separate_huffman_expected_bits": 2.0
                * three_symbol_huffman,
                "joint_fixed_length_bits": 4,
            },
            "interpretation": "Huffman values are expected lengths, not fixed addresses",
        },
        "scalar_curves": evaluation["curves"],
        "claims_not_established": [
            "natural-data prevalence",
            "ANN distance-estimation improvement",
            "recall or QPS improvement",
            "novelty over prior mixed-radix or entropy-constrained quantization",
        ],
    }

    dyadic = result["allocation"]["dyadic"]  # type: ignore[index]
    checks = {
        "arbitrary_cardinalities": arbitrary.cardinalities == (3, 5),
        "arbitrary_used_states": arbitrary.used_states == 15,
        "arbitrary_zero_distortion": arbitrary.distortion == 0.0,
        "dyadic_cardinalities": tuple(dyadic["cardinalities"]) == (4, 4),
        "dyadic_used_states": dyadic["used_states"] == 16,
        "dyadic_distortion": math.isclose(
            float(dyadic["distortion"]), 0.1, rel_tol=0.0, abs_tol=1e-15
        ),
        "mixed_radix_bijection": encoded_addresses
        == set(range(arbitrary.used_states)),
        "lookup_parity": max_lookup_difference == 0.0,
        "three_by_three_expected_length": math.isclose(
            2.0 * three_symbol_huffman,
            10.0 / 3.0,
            rel_tol=0.0,
            abs_tol=1e-15,
        ),
    }
    result["predeclared_checks"] = checks
    if not all(checks.values()):
        result["status"] = "FAIL"
        raise RuntimeError(f"synthetic witness failed: {checks}")
    return result


def _write_json(payload: Mapping[str, object], output: Path | None) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(serialized, end="")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized, encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    witness = subparsers.add_parser(
        "synthetic-witness", help="run the frozen A4-0 two-dimensional witness"
    )
    witness.add_argument("--output", type=Path)

    evaluate = subparsers.add_parser(
        "evaluate-spec", help="evaluate weighted scalar supports from JSON"
    )
    evaluate.add_argument("--input", type=Path, required=True)
    evaluate.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.command == "synthetic-witness":
        _write_json(run_synthetic_witness(), args.output)
        return 0

    spec = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("input specification must be a JSON object")
    dimensions = spec.get("dimensions")
    block_bits = spec.get("block_bits")
    max_cardinality = spec.get("max_cardinality")
    if not isinstance(dimensions, list):
        raise ValueError("input specification must contain a dimensions list")
    if not isinstance(block_bits, int):
        raise ValueError("input specification must contain integer block_bits")
    if max_cardinality is not None and not isinstance(max_cardinality, int):
        raise ValueError("max_cardinality must be an integer when present")
    result = evaluate_weighted_dimensions(dimensions, block_bits, max_cardinality)
    _write_json(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
