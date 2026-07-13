#!/usr/bin/env python3
"""Independent exact/synthetic reference helpers for the frozen A4-1S gate.

This module never opens natural-data artifacts.  The production scalar solver
and block trainer live in compiled C++; these deliberately small Python
implementations are the independent parity authority for preregistered tiny
and randomized synthetic fixtures.
"""

from __future__ import annotations

import hashlib
import itertools
import math
import struct
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence


GRID_EXPONENT = -149
SSE_GRID_EXPONENT = -298


def float32_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def bits_to_float32(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def float64_bits(value: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def bits_to_float64(bits: int) -> float:
    return struct.unpack("<d", struct.pack("<Q", bits))[0]


def ieee_bits_to_fraction(
    bits: int, *, fraction_bits: int, exponent_bits: int
) -> Fraction:
    """Decode one finite IEEE binary value exactly as a Fraction."""

    total_bits = 1 + exponent_bits + fraction_bits
    if bits < 0 or bits >= (1 << total_bits):
        raise ValueError("IEEE bit pattern is outside the target format")
    sign = -1 if bits >> (total_bits - 1) else 1
    exponent_mask = (1 << exponent_bits) - 1
    exponent_field = (bits >> fraction_bits) & exponent_mask
    fraction = bits & ((1 << fraction_bits) - 1)
    if exponent_field == exponent_mask:
        raise ValueError("nonfinite IEEE value has no rational decoding")
    bias = (1 << (exponent_bits - 1)) - 1
    if exponent_field == 0:
        significand = fraction
        exponent = 1 - bias - fraction_bits
    else:
        significand = (1 << fraction_bits) | fraction
        exponent = exponent_field - bias - fraction_bits
    value = Fraction(sign * significand, 1)
    if exponent >= 0:
        return value * (1 << exponent)
    return value / (1 << (-exponent))


def decode_float32_grid(bits: int) -> int:
    """Decode finite binary32 bits as the exact integer n in n*2^-149."""

    sign = -1 if bits >> 31 else 1
    exponent = (bits >> 23) & 0xFF
    fraction = bits & 0x7FFFFF
    if exponent == 0xFF:
        raise ValueError("A4-1S accepts only finite binary32 values")
    if exponent == 0:
        magnitude = fraction
    else:
        magnitude = ((1 << 23) | fraction) << (exponent - 1)
    if magnitude == 0:
        return 0
    return sign * magnitude


def grid_integer_to_fraction(value: int, exponent: int = GRID_EXPONENT) -> Fraction:
    if exponent >= 0:
        return Fraction(value << exponent, 1)
    return Fraction(value, 1 << (-exponent))


def _round_ratio_ties_even(numerator: int, denominator: int) -> int:
    if numerator < 0 or denominator <= 0:
        raise ValueError("rounding ratio must be nonnegative with positive denominator")
    quotient, remainder = divmod(numerator, denominator)
    doubled = remainder << 1
    if doubled > denominator or (doubled == denominator and quotient & 1):
        quotient += 1
    return quotient


def _floor_log2_fraction(numerator: int, denominator: int) -> int:
    if numerator <= 0 or denominator <= 0:
        raise ValueError("log2 arguments must be positive")
    candidate = numerator.bit_length() - denominator.bit_length()
    if candidate >= 0:
        at_least = numerator >= (denominator << candidate)
    else:
        at_least = (numerator << (-candidate)) >= denominator
    return candidate if at_least else candidate - 1


def round_fraction_to_ieee_bits(
    value: Fraction,
    *,
    fraction_bits: int,
    exponent_bits: int,
) -> int:
    """Round a rational directly to IEEE binary bits using RN-ties-to-even."""

    if fraction_bits <= 0 or exponent_bits <= 1:
        raise ValueError("invalid IEEE format")
    sign_bit = 1 if value < 0 else 0
    magnitude = abs(value)
    total_bits = 1 + exponent_bits + fraction_bits
    if magnitude == 0:
        return 0

    bias = (1 << (exponent_bits - 1)) - 1
    minimum_normal_exponent = 1 - bias
    maximum_normal_exponent = bias
    minimum_subnormal_exponent = minimum_normal_exponent - fraction_bits
    numerator = magnitude.numerator
    denominator = magnitude.denominator
    exponent = _floor_log2_fraction(numerator, denominator)

    if exponent < minimum_normal_exponent:
        shift = -minimum_subnormal_exponent
        rounded = _round_ratio_ties_even(numerator << shift, denominator)
        if rounded == 0:
            return sign_bit << (total_bits - 1)
        if rounded >= (1 << fraction_bits):
            exponent_field = 1
            fraction_field = 0
        else:
            exponent_field = 0
            fraction_field = rounded
    else:
        shift = fraction_bits - exponent
        if shift >= 0:
            rounded = _round_ratio_ties_even(numerator << shift, denominator)
        else:
            rounded = _round_ratio_ties_even(numerator, denominator << (-shift))
        if rounded == (1 << (fraction_bits + 1)):
            rounded >>= 1
            exponent += 1
        if exponent > maximum_normal_exponent:
            exponent_field = (1 << exponent_bits) - 1
            fraction_field = 0
        else:
            exponent_field = exponent + bias
            fraction_field = rounded - (1 << fraction_bits)

    return (
        (sign_bit << (total_bits - 1))
        | (exponent_field << fraction_bits)
        | fraction_field
    )


def _rounded_ieee_fraction(
    value: Fraction, *, fraction_bits: int, exponent_bits: int
) -> tuple[int, Fraction]:
    bits = round_fraction_to_ieee_bits(
        value, fraction_bits=fraction_bits, exponent_bits=exponent_bits
    )
    return bits, ieee_bits_to_fraction(
        bits, fraction_bits=fraction_bits, exponent_bits=exponent_bits
    )


def scalar_lookup_entry_bits(value_bits: int, centroid_bits: int) -> tuple[int, int]:
    """Independent binary32-promote/subtract/square/narrow lookup replay."""

    value = ieee_bits_to_fraction(value_bits, fraction_bits=23, exponent_bits=8)
    centroid = ieee_bits_to_fraction(
        centroid_bits, fraction_bits=23, exponent_bits=8
    )
    _, difference = _rounded_ieee_fraction(
        value - centroid, fraction_bits=52, exponent_bits=11
    )
    pre_narrow_bits, squared = _rounded_ieee_fraction(
        difference * difference, fraction_bits=52, exponent_bits=11
    )
    stored_bits = round_fraction_to_ieee_bits(
        squared, fraction_bits=23, exponent_bits=8
    )
    return pre_narrow_bits, stored_bits


def point_lookup_entry_bits(
    query_bits: Sequence[int], reconstruction_bits: Sequence[int]
) -> tuple[int, int]:
    """Independent ordered two-coordinate binary64 lookup replay."""

    if len(query_bits) != 2 or len(reconstruction_bits) != 2:
        raise ValueError("point lookup requires two coordinates")
    squares: list[Fraction] = []
    for query, reconstruction in zip(query_bits, reconstruction_bits):
        query_value = ieee_bits_to_fraction(
            query, fraction_bits=23, exponent_bits=8
        )
        reconstruction_value = ieee_bits_to_fraction(
            reconstruction, fraction_bits=23, exponent_bits=8
        )
        _, difference = _rounded_ieee_fraction(
            query_value - reconstruction_value,
            fraction_bits=52,
            exponent_bits=11,
        )
        _, square = _rounded_ieee_fraction(
            difference * difference, fraction_bits=52, exponent_bits=11
        )
        squares.append(square)
    pre_narrow_bits, total = _rounded_ieee_fraction(
        squares[0] + squares[1], fraction_bits=52, exponent_bits=11
    )
    stored_bits = round_fraction_to_ieee_bits(
        total, fraction_bits=23, exponent_bits=8
    )
    return pre_narrow_bits, stored_bits


def round_grid_mean_to_float32_bits(sum_n: int, weight: int) -> int:
    return round_fraction_to_ieee_bits(
        grid_integer_to_fraction(sum_n, GRID_EXPONENT) / weight,
        fraction_bits=23,
        exponent_bits=8,
    )


def round_grid_mean_to_float64_bits(sum_n: int, weight: int) -> int:
    return round_fraction_to_ieee_bits(
        grid_integer_to_fraction(sum_n, GRID_EXPONENT) / weight,
        fraction_bits=52,
        exponent_bits=11,
    )


@dataclass(frozen=True)
class ExactCluster:
    begin: int
    end: int
    weight: int
    sum_n: int


@dataclass(frozen=True)
class ExactScalarSolution:
    requested_cardinality: int
    effective_cardinality: int
    objective_grid: Fraction
    clusters: tuple[ExactCluster, ...]


@dataclass(frozen=True)
class ExactScalarCurve:
    support: tuple[int, ...]
    support_weights: tuple[int, ...]
    support_lowest_ids: tuple[int, ...]
    solutions: tuple[ExactScalarSolution, ...]

    def at(self, cardinality: int) -> ExactScalarSolution:
        if not 1 <= cardinality <= len(self.solutions):
            raise ValueError("cardinality outside curve")
        return self.solutions[cardinality - 1]


def aggregate_float32_support(
    value_bits: Sequence[int],
    weights: Sequence[int] | None = None,
    vector_ids: Sequence[int] | None = None,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    if not value_bits:
        raise ValueError("empty scalar support")
    if weights is None:
        weights = [1] * len(value_bits)
    if vector_ids is None:
        vector_ids = list(range(len(value_bits)))
    if not (len(value_bits) == len(weights) == len(vector_ids)):
        raise ValueError("support arrays must have equal length")
    aggregate: dict[int, tuple[int, int]] = {}
    for bits, raw_weight, vector_id in zip(value_bits, weights, vector_ids):
        if raw_weight <= 0:
            raise ValueError("weights must be positive integers")
        n = decode_float32_grid(bits)
        old_weight, old_id = aggregate.get(n, (0, vector_id))
        aggregate[n] = (old_weight + int(raw_weight), min(old_id, vector_id))
    ordered = sorted((n, weight, lowest) for n, (weight, lowest) in aggregate.items())
    return (
        tuple(item[0] for item in ordered),
        tuple(item[1] for item in ordered),
        tuple(item[2] for item in ordered),
    )


def exact_scalar_curve_reference(
    value_bits: Sequence[int],
    max_cardinality: int,
    weights: Sequence[int] | None = None,
    vector_ids: Sequence[int] | None = None,
) -> ExactScalarCurve:
    """Independent O(K H^2) exact-rational reference."""

    if max_cardinality <= 0:
        raise ValueError("max_cardinality must be positive")
    support, support_weights, support_ids = aggregate_float32_support(
        value_bits, weights, vector_ids
    )
    size = len(support)
    effective_max = min(size, max_cardinality)
    prefix_w = [0]
    prefix_a = [0]
    prefix_c = [0]
    for n, weight in zip(support, support_weights):
        prefix_w.append(prefix_w[-1] + weight)
        prefix_a.append(prefix_a[-1] + weight * n)
        prefix_c.append(prefix_c[-1] + weight * n * n)

    def interval(begin: int, end: int) -> tuple[Fraction, int, int]:
        weight = prefix_w[end] - prefix_w[begin]
        value_sum = prefix_a[end] - prefix_a[begin]
        square_sum = prefix_c[end] - prefix_c[begin]
        numerator = weight * square_sum - value_sum * value_sum
        if numerator < 0:
            raise AssertionError("negative exact interval SSE")
        return Fraction(numerator, weight), weight, value_sum

    infinity: Fraction | None = None
    dp: list[list[Fraction | None]] = [
        [infinity] * (size + 1) for _ in range(effective_max + 1)
    ]
    split = [[-1] * (size + 1) for _ in range(effective_max + 1)]
    dp[0][0] = Fraction(0)
    for clusters in range(1, effective_max + 1):
        for end in range(clusters, size + 1):
            best: Fraction | None = None
            best_begin = -1
            for begin in range(clusters - 1, end):
                prior = dp[clusters - 1][begin]
                if prior is None:
                    continue
                candidate = prior + interval(begin, end)[0]
                if best is None or candidate < best or (
                    candidate == best and begin < best_begin
                ):
                    best = candidate
                    best_begin = begin
            dp[clusters][end] = best
            split[clusters][end] = best_begin

    effective: list[ExactScalarSolution] = []
    for clusters in range(1, effective_max + 1):
        end = size
        ranges: list[tuple[int, int]] = []
        for remaining in range(clusters, 0, -1):
            begin = split[remaining][end]
            if begin < 0:
                raise AssertionError("reference backtracking failed")
            ranges.append((begin, end))
            end = begin
        ranges.reverse()
        exact_clusters: list[ExactCluster] = []
        for begin, end in ranges:
            _, weight, value_sum = interval(begin, end)
            exact_clusters.append(ExactCluster(begin, end, weight, value_sum))
        objective = dp[clusters][size]
        if objective is None:
            raise AssertionError("missing reference objective")
        effective.append(
            ExactScalarSolution(clusters, clusters, objective, tuple(exact_clusters))
        )

    solutions: list[ExactScalarSolution] = []
    for requested in range(1, max_cardinality + 1):
        used = min(requested, size)
        base = effective[used - 1]
        solutions.append(
            ExactScalarSolution(
                requested,
                used,
                base.objective_grid,
                base.clusters,
            )
        )
    return ExactScalarCurve(support, support_weights, support_ids, tuple(solutions))


@dataclass(frozen=True)
class ProductAllocation:
    cardinalities: tuple[int, int]
    used_states: int
    objective_grid: Fraction


def exact_product_allocation_reference(
    first: ExactScalarCurve,
    second: ExactScalarCurve,
    capacity: int,
    *,
    dyadic_only: bool,
) -> ProductAllocation:
    allowed = range(1, capacity + 1)
    if dyadic_only:
        allowed = tuple(1 << bit for bit in range(capacity.bit_length()))
    best: tuple[Fraction, int, tuple[int, int]] | None = None
    for k1 in allowed:
        if k1 > len(first.solutions):
            continue
        for k2 in allowed:
            if k2 > len(second.solutions) or k1 * k2 > capacity:
                continue
            candidate = (
                first.at(k1).objective_grid + second.at(k2).objective_grid,
                -(k1 * k2),
                (k1, k2),
            )
            if best is None or candidate < best:
                best = candidate
    if best is None:
        raise ValueError("no feasible product allocation")
    return ProductAllocation(best[2], -best[1], best[0])


@dataclass(frozen=True)
class GlobalDyadicAllocation:
    bits: tuple[int, ...]
    used_bits: int
    objective_grid: Fraction


def exact_global_dyadic_reference(
    curves: Sequence[ExactScalarCurve], budget: int
) -> GlobalDyadicAllocation:
    frontier: dict[int, tuple[Fraction, tuple[int, ...]]] = {0: (Fraction(0), ())}
    for curve in curves:
        next_frontier: dict[int, tuple[Fraction, tuple[int, ...]]] = {}
        for used, (objective, selected) in frontier.items():
            for bits in range(9):
                if used + bits > budget:
                    break
                cardinality = 1 << bits
                if cardinality > len(curve.solutions):
                    continue
                candidate = (objective + curve.at(cardinality).objective_grid, selected + (bits,))
                incumbent = next_frontier.get(used + bits)
                if incumbent is None or candidate < incumbent:
                    next_frontier[used + bits] = candidate
        frontier = next_frontier
    used_bits, (objective, selected) = min(
        frontier.items(), key=lambda item: (item[1][0], -item[0], item[1][1])
    )
    return GlobalDyadicAllocation(selected, used_bits, objective)


def mixed_radix_encode(codes: Sequence[int], radices: Sequence[int]) -> int:
    address = 0
    multiplier = 1
    for code, radix in zip(codes, radices):
        if not 0 <= code < radix:
            raise ValueError("mixed-radix code out of range")
        address += multiplier * code
        multiplier *= radix
    return address


def mixed_radix_decode(address: int, radices: Sequence[int]) -> tuple[int, ...]:
    if address < 0 or address >= math.prod(radices):
        raise ValueError("mixed-radix address out of range")
    result: list[int] = []
    for radix in radices:
        result.append(address % radix)
        address //= radix
    return tuple(result)


def pack_matched_labels(labels: Sequence[int], word_bits: int) -> bytes:
    if len(labels) != 64:
        raise ValueError("matched panel requires 64 labels")
    if word_bits == 8:
        if any(not 0 <= label < 256 for label in labels):
            raise ValueError("B8 label out of range")
        return bytes(labels)
    if word_bits != 4:
        raise ValueError("word_bits must be 4 or 8")
    packed = bytearray(32)
    for index in range(0, 64, 2):
        low, high = labels[index], labels[index + 1]
        if not (0 <= low < 16 and 0 <= high < 16):
            raise ValueError("B4 label out of range")
        packed[index // 2] = low | (high << 4)
    return bytes(packed)


def unpack_matched_labels(payload: bytes, word_bits: int) -> tuple[int, ...]:
    if word_bits == 8:
        if len(payload) != 64:
            raise ValueError("B8 payload must be 64 bytes")
        return tuple(payload)
    if word_bits != 4 or len(payload) != 32:
        raise ValueError("B4 payload must be 32 bytes")
    result: list[int] = []
    for byte in payload:
        result.extend((byte & 0x0F, byte >> 4))
    return tuple(result)


def pack_global_labels(labels: Sequence[int], bits: Sequence[int], paid_bytes: int) -> bytes:
    if len(labels) != len(bits):
        raise ValueError("global labels and bits differ")
    payload = bytearray(paid_bytes)
    offset = 0
    for label, width in zip(labels, bits):
        if width < 0 or label < 0 or label >= (1 << width):
            raise ValueError("global label out of range")
        for local in range(width):
            if label & (1 << local):
                payload[offset // 8] |= 1 << (offset % 8)
            offset += 1
    if offset > 8 * paid_bytes:
        raise ValueError("global payload exceeds paid bytes")
    return bytes(payload)


def unpack_global_labels(payload: bytes, bits: Sequence[int]) -> tuple[int, ...]:
    result: list[int] = []
    offset = 0
    for width in bits:
        label = 0
        for local in range(width):
            if payload[offset // 8] & (1 << (offset % 8)):
                label |= 1 << local
            offset += 1
        result.append(label)
    if any(payload[index // 8] & (1 << (index % 8)) for index in range(offset, len(payload) * 8)):
        raise ValueError("nonzero global padding")
    return tuple(result)


def sha256_bytes(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8")).digest()


def assignment_digest(assignments: Sequence[int]) -> str:
    payload = b"".join(struct.pack("<H", assignment) for assignment in assignments)
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class BlockPoint:
    x: float
    y: float
    cell_id: int
    vector_id: int
    selection_digest: bytes


@dataclass(frozen=True)
class BlockStepResult:
    iteration: int
    prior_sse_bits: int
    candidate_sse_bits: int
    changed_assignment_count: int
    empty_center_ids: tuple[int, ...]
    centers_after_bits: tuple[tuple[int, int], ...]
    assignment_hash: str


@dataclass(frozen=True)
class BlockStartResult:
    start_id: int
    first_seed_digest: str
    selected_vector_ids: tuple[int, ...]
    initial_sse_bits: int
    initial_centers_bits: tuple[tuple[int, int], ...]
    final_sse_bits: int
    iterations: int
    assignment_hash: str
    centers_bits: tuple[tuple[int, int], ...]
    final_assignments: tuple[int, ...]
    empty_events: int
    converged: bool
    steps: tuple[BlockStepResult, ...]
    distance_comparison_count: int
    assignment_tie_count: int
    farthest_tie_count: int


def _distance(point: BlockPoint, center: tuple[float, float]) -> float:
    dx = point.x - center[0]
    dy = point.y - center[1]
    return dx * dx + dy * dy


def _assign_points(
    points: Sequence[BlockPoint], centers: Sequence[tuple[float, float]]
) -> tuple[list[int], float, int]:
    assignments, sse, comparisons, _ = _assign_points_audit(points, centers)
    return assignments, sse, comparisons


def _assign_points_audit(
    points: Sequence[BlockPoint], centers: Sequence[tuple[float, float]]
) -> tuple[list[int], float, int, int]:
    if not centers:
        raise ValueError("block assignment requires a center")
    assignments: list[int] = []
    sse = 0.0
    comparisons = 0
    ties = 0
    for point in points:
        best_id = 0
        best = _distance(point, centers[0])
        comparisons += 1
        for center_id in range(1, len(centers)):
            candidate = _distance(point, centers[center_id])
            comparisons += 1
            if candidate < best:
                best = candidate
                best_id = center_id
            elif candidate == best:
                ties += 1
        assignments.append(best_id)
        sse += best
    return assignments, sse, comparisons, ties


def _farthest_fill(
    points: Sequence[BlockPoint],
    initial: Sequence[tuple[float, float]],
    capacity: int,
    excluded_vector_ids: set[int] | None = None,
    selected_vector_ids: list[int] | None = None,
    audit: dict[str, int] | None = None,
) -> list[tuple[float, float]]:
    centers = list(initial)
    excluded = set() if excluded_vector_ids is None else set(excluded_vector_ids)
    while len(centers) < capacity:
        candidate_index: int | None = None
        best_distance = 0.0
        for index, point in enumerate(points):
            if point.vector_id in excluded:
                continue
            nearest = _distance(point, centers[0])
            if audit is not None:
                audit["distance_comparison_count"] += 1
            for center in centers[1:]:
                candidate = _distance(point, center)
                if audit is not None:
                    audit["distance_comparison_count"] += 1
                if candidate < nearest:
                    nearest = candidate
            if candidate_index is not None and nearest == best_distance and audit is not None:
                audit["farthest_tie_count"] += 1
            if (
                candidate_index is None
                or nearest > best_distance
                or (
                    nearest == best_distance
                    and point.vector_id < points[candidate_index].vector_id
                )
            ):
                candidate_index = index
                best_distance = nearest
        if candidate_index is None:
            raise ValueError("not enough unique block fitting rows")
        point = points[candidate_index]
        centers.append((point.x, point.y))
        excluded.add(point.vector_id)
        if selected_vector_ids is not None:
            selected_vector_ids.append(point.vector_id)
    return centers


def _farthest_first_start(
    points: Sequence[BlockPoint],
    capacity: int,
    protocol_version: str,
    dataset_id: str,
    group_id: int,
    start_id: int,
) -> tuple[list[tuple[float, float]], str, list[int], dict[str, int]]:
    first = min(
        points,
        key=lambda point: (
            sha256_bytes(
                f"{protocol_version}|{dataset_id}|{capacity}|{group_id}|"
                f"{start_id}|{point.cell_id}|{point.vector_id}"
            ),
            point.vector_id,
        ),
    )
    selected = [first.vector_id]
    audit = {"distance_comparison_count": 0, "farthest_tie_count": 0}
    centers = _farthest_fill(
        points,
        [(first.x, first.y)],
        capacity,
        {first.vector_id},
        selected,
        audit,
    )
    digest = sha256_bytes(
        f"{protocol_version}|{dataset_id}|{capacity}|{group_id}|"
        f"{start_id}|{first.cell_id}|{first.vector_id}"
    ).hex()
    return centers, digest, selected, audit


def lloyd_reference(
    points: Sequence[BlockPoint],
    centers: Sequence[tuple[float, float]],
    start_id: int,
    *,
    first_seed_digest: str = "00" * 32,
    selected_vector_ids: Sequence[int] = (),
    seed_distance_comparison_count: int = 0,
    seed_farthest_tie_count: int = 0,
    max_iterations: int = 300,
) -> BlockStartResult:
    current = list(centers)
    initial_centers_bits = tuple(
        (float64_bits(center[0]), float64_bits(center[1])) for center in current
    )
    _, initial_sse, initial_comparisons, initial_ties = _assign_points_audit(
        points, current
    )
    distance_comparisons = seed_distance_comparison_count + initial_comparisons
    assignment_ties = initial_ties
    empty_events = 0
    steps: list[BlockStepResult] = []
    for iteration in range(1, max_iterations + 1):
        before, prior_sse, before_comparisons, before_ties = _assign_points_audit(
            points, current
        )
        distance_comparisons += before_comparisons
        assignment_ties += before_ties
        sums_x = [0.0] * len(current)
        sums_y = [0.0] * len(current)
        counts = [0] * len(current)
        for point, assignment in zip(points, before):
            sums_x[assignment] += point.x
            sums_y[assignment] += point.y
            counts[assignment] += 1
        updated = list(current)
        for center_id, count in enumerate(counts):
            if count:
                updated[center_id] = (sums_x[center_id] / count, sums_y[center_id] / count)
            else:
                empty_events += 1
        after, candidate_sse, after_comparisons, after_ties = _assign_points_audit(
            points, updated
        )
        distance_comparisons += after_comparisons
        assignment_ties += after_ties
        if candidate_sse > prior_sse:
            raise AssertionError("block control SSE increased")
        changed = sum(left != right for left, right in zip(before, after))
        steps.append(
            BlockStepResult(
                iteration=iteration,
                prior_sse_bits=float64_bits(prior_sse),
                candidate_sse_bits=float64_bits(candidate_sse),
                changed_assignment_count=changed,
                empty_center_ids=tuple(
                    center_id
                    for center_id, count in enumerate(counts)
                    if count == 0
                ),
                centers_after_bits=tuple(
                    (float64_bits(center[0]), float64_bits(center[1]))
                    for center in updated
                ),
                assignment_hash=assignment_digest(after),
            )
        )
        current = updated
        if after == before:
            centers_bits = tuple(
                (float32_bits(center[0]), float32_bits(center[1])) for center in current
            )
            return BlockStartResult(
                start_id=start_id,
                first_seed_digest=first_seed_digest,
                selected_vector_ids=tuple(selected_vector_ids),
                initial_sse_bits=float64_bits(initial_sse),
                initial_centers_bits=initial_centers_bits,
                final_sse_bits=float64_bits(candidate_sse),
                iterations=iteration,
                assignment_hash=assignment_digest(after),
                centers_bits=centers_bits,
                final_assignments=tuple(after),
                empty_events=empty_events,
                converged=True,
                steps=tuple(steps),
                distance_comparison_count=distance_comparisons,
                assignment_tie_count=assignment_ties,
                farthest_tie_count=seed_farthest_tie_count,
            )
    return BlockStartResult(
        start_id=start_id,
        first_seed_digest=first_seed_digest,
        selected_vector_ids=tuple(selected_vector_ids),
        initial_sse_bits=float64_bits(initial_sse),
        initial_centers_bits=initial_centers_bits,
        final_sse_bits=0,
        iterations=max_iterations,
        assignment_hash="",
        centers_bits=(),
        final_assignments=(),
        empty_events=empty_events,
        converged=False,
        steps=tuple(steps),
        distance_comparison_count=distance_comparisons,
        assignment_tie_count=assignment_ties,
        farthest_tie_count=seed_farthest_tie_count,
    )


def make_block_points(
    rows: Sequence[Sequence[float]],
    protocol_version: str,
    dataset_id: str,
    cells: Sequence[int],
    vector_ids: Sequence[int],
) -> tuple[BlockPoint, ...]:
    points = []
    for row, cell, vector_id in zip(rows, cells, vector_ids):
        digest = sha256_bytes(f"{protocol_version}|{dataset_id}|{cell}|{vector_id}")
        points.append(BlockPoint(float(row[0]), float(row[1]), cell, vector_id, digest))
    points.sort(key=lambda point: (point.cell_id, point.selection_digest, point.vector_id))
    return tuple(points)


def block_suite_reference(
    rows: Sequence[Sequence[float]],
    capacity: int,
    protocol_version: str,
    dataset_id: str,
    group_id: int,
) -> tuple[BlockStartResult, ...]:
    cells = [index % 4 for index in range(len(rows))]
    vector_ids = list(range(len(rows)))
    points = make_block_points(rows, protocol_version, dataset_id, cells, vector_ids)
    coordinate_bits = [
        [float32_bits(row[coordinate]) for row in rows] for coordinate in range(2)
    ]
    curves = [
        exact_scalar_curve_reference(bits, capacity, vector_ids=vector_ids)
        for bits in coordinate_bits
    ]
    allocation = exact_product_allocation_reference(
        curves[0], curves[1], capacity, dyadic_only=False
    )
    selected = [curves[index].at(allocation.cardinalities[index]) for index in range(2)]
    centroid_tables: list[list[float]] = []
    for solution in selected:
        table = []
        for cluster in solution.clusters:
            table.append(
                bits_to_float64(round_grid_mean_to_float64_bits(cluster.sum_n, cluster.weight))
            )
        centroid_tables.append(table)
    start_zero = [
        (centroid_tables[0][z1], centroid_tables[1][z2])
        for z2 in range(allocation.cardinalities[1])
        for z1 in range(allocation.cardinalities[0])
    ]
    start_zero_selected: list[int] = []
    start_zero_audit = {
        "distance_comparison_count": 0,
        "farthest_tie_count": 0,
    }
    start_zero = _farthest_fill(
        points,
        start_zero,
        capacity,
        selected_vector_ids=start_zero_selected,
        audit=start_zero_audit,
    )
    results = [
        lloyd_reference(
            points,
            start_zero,
            0,
            selected_vector_ids=start_zero_selected,
            seed_distance_comparison_count=start_zero_audit[
                "distance_comparison_count"
            ],
            seed_farthest_tie_count=start_zero_audit["farthest_tie_count"],
        )
    ]
    for start_id in range(1, 8):
        start, digest, selected, start_audit = _farthest_first_start(
            points,
            capacity,
            protocol_version,
            dataset_id,
            group_id,
            start_id,
        )
        results.append(
            lloyd_reference(
                points,
                start,
                start_id,
                first_seed_digest=digest,
                selected_vector_ids=selected,
                seed_distance_comparison_count=start_audit[
                    "distance_comparison_count"
                ],
                seed_farthest_tie_count=start_audit["farthest_tie_count"],
            )
        )
    return tuple(results)


def distinct_float32_centers(result: BlockStartResult) -> int:
    return len(set(result.centers_bits))


def all_mixed_radix_codes(radices: Sequence[int]) -> Iterable[tuple[int, ...]]:
    return itertools.product(*(range(radix) for radix in radices))
