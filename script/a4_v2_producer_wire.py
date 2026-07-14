#!/usr/bin/env python3
"""Strict producer-side wire codecs for the frozen A4 V2 native child.

This module is deliberately producer-only.  The independent verifier must not
import it: the V2 protocol forbids sharing the producer parser core.  The wire
formats retain the predecessor's little-endian binary inputs and TSV/binary
outputs so that the implementation does not replace the frozen native-child
architecture with an in-process constructor.

Importing this module performs no I/O, process launch, RNG operation, or
scientific computation.
"""

from __future__ import annotations

import hashlib
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, Iterator, Sequence


ROWS = 8192
DIMENSIONS = 128
GROUPS = 64
MAX_K = 256
PROTOCOL_HASH_DOMAIN = "saq-attempt4-a4-1-20260713-schema2"
_UINT64_MAX = (1 << 64) - 1

_UINT = re.compile(r"^(?:0|[1-9][0-9]*)$")
_SINT = re.compile(r"^(?:0|-?[1-9][0-9]*)$")
_HEX32 = re.compile(r"^0x[0-9a-f]{8}$")
_HEX64 = re.compile(r"^0x[0-9a-f]{16}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class WireError(RuntimeError):
    """A malformed or semantically inconsistent producer/native interchange."""


class WireControlError(WireError):
    """A complete interchange that exposes a registered scientific control failure."""

    def __init__(self, detail: str, block_unit: object | None = None):
        super().__init__(detail)
        self.block_unit = block_unit


def _uint(text: str, field: str, maximum: int | None = None) -> int:
    if _UINT.fullmatch(text) is None:
        raise WireError(f"{field} is not canonical unsigned decimal")
    value = int(text)
    if maximum is not None and value > maximum:
        raise WireError(f"{field} exceeds {maximum}")
    return value


def _sint(text: str, field: str) -> int:
    if _SINT.fullmatch(text) is None:
        raise WireError(f"{field} is not canonical signed decimal")
    return int(text)


def _bool(text: str, field: str) -> bool:
    if text not in {"0", "1"}:
        raise WireError(f"{field} is not a canonical boolean")
    return text == "1"


def _bits(
    text: str,
    width: int,
    field: str,
    *,
    canonical_zero: bool = False,
    allow_positive_infinity: bool = False,
    nonnegative: bool = False,
) -> str:
    matcher = _HEX32 if width == 32 else _HEX64
    if matcher.fullmatch(text) is None:
        raise WireError(f"{field} is not canonical binary{width}")
    raw = int(text, 16)
    exponent_mask = 0x7F800000 if width == 32 else 0x7FF0000000000000
    if raw & exponent_mask == exponent_mask:
        if not allow_positive_infinity or raw != exponent_mask:
            raise WireError(f"{field} is nonfinite")
    signless_mask = 0x7FFFFFFF if width == 32 else 0x7FFFFFFFFFFFFFFF
    sign_mask = 0x80000000 if width == 32 else 0x8000000000000000
    if canonical_zero and raw & signless_mask == 0 and raw != 0:
        raise WireError(f"{field} uses noncanonical negative zero")
    if nonnegative and raw & sign_mask:
        raise WireError(f"{field} is negative")
    # V2 in-memory records use the schema form without the predecessor 0x.
    return text[2:]


def _ordered_float32_bits(text: str) -> int:
    raw = int(text, 16)
    if raw & 0x7FFFFFFF == 0:
        raw = 0  # Signed zeros compare as one serialized scalar value.
    return (~raw & 0xFFFFFFFF) if raw & 0x80000000 else raw | 0x80000000


def _digest(text: str, field: str) -> str:
    if _SHA256.fullmatch(text) is None:
        raise WireError(f"{field} is not canonical SHA-256")
    return text


@dataclass(frozen=True)
class ExactValue:
    numerator: str
    denominator: str
    binary_grid_exponent: int

    def __post_init__(self) -> None:
        numerator = _sint(self.numerator, "exact numerator")
        denominator = _uint(self.denominator, "exact denominator")
        if denominator == 0:
            raise WireError("exact denominator is zero")
        if numerator == 0 and self.denominator != "1":
            raise WireError("zero rational denominator is not canonical one")
        if math.gcd(abs(numerator), denominator) != 1:
            raise WireError("exact rational is not reduced")


@dataclass(frozen=True)
class ScalarCluster:
    support_begin: int
    support_end_exclusive: int
    mean: ExactValue
    binary32_bits: str
    binary64_bits: str


@dataclass(frozen=True)
class ScalarSolution:
    requested_cardinality: int
    effective_cardinality: int
    exact_sse: ExactValue
    clusters: tuple[ScalarCluster, ...]
    comparison_count: int
    exact_tie_count: int
    serialized_binary32_strictly_increasing: bool


@dataclass(frozen=True)
class ScalarCoordinate:
    coordinate_id: int
    fit_row_count: int
    distinct_support_size: int
    solutions: tuple[ScalarSolution, ...]
    predecessor_monotone: tuple[bool, ...]


@dataclass(frozen=True)
class ProductAllocationItem:
    item_id: int
    capacity: int
    dyadic: bool
    requested_cardinalities: tuple[int, int]
    effective_cardinalities: tuple[int, int]
    used_states: int
    all_reachable: bool
    exact_sse: ExactValue
    candidate_count: int


@dataclass(frozen=True)
class GlobalAllocationItem:
    item_id: int
    bit_budget: int
    used_bits: int
    all_reachable: bool
    exact_sse: ExactValue
    transition_count: int
    bit_widths: tuple[int, ...]
    effective_cardinalities: tuple[int, ...]


@dataclass(frozen=True)
class BlockPoint:
    cell_id: int
    vector_id: int
    selection_digest: str
    coordinate0_bits: str
    coordinate1_bits: str


class U16LeView(Sequence[int]):
    """Read-only integer view over an immutable little-endian uint16 preimage."""

    __slots__ = ("_payload",)

    def __init__(self, payload: bytes):
        if len(payload) % 2 != 0:
            raise WireError("uint16 preimage has odd byte length")
        self._payload = payload

    def __len__(self) -> int:
        return len(self._payload) // 2

    def __getitem__(self, index: int | slice) -> int | tuple[int, ...]:
        if isinstance(index, slice):
            return tuple(self[item] for item in range(*index.indices(len(self))))
        normalized = index if index >= 0 else len(self) + index
        if not 0 <= normalized < len(self):
            raise IndexError(index)
        offset = 2 * normalized
        return int.from_bytes(self._payload[offset : offset + 2], "little")

    def __iter__(self) -> Iterator[int]:
        return (value[0] for value in struct.iter_unpack("<H", self._payload))


@dataclass(frozen=True)
class BlockStep:
    iteration: int
    prior_sse_bits: str
    candidate_sse_bits: str
    changed_assignment_count: int
    empty_center_ids: tuple[int, ...]
    centers_after_binary64_bits: tuple[tuple[str, str], ...]
    assignments_before_le_u16: bytes
    assignments_after_le_u16: bytes

@dataclass(frozen=True)
class BlockStart:
    start_id: int
    first_seed_digest: str
    initialization_vector_ids: tuple[int, ...]
    initial_centers_binary64_bits: tuple[tuple[str, str], ...]
    initial_sse_bits: str
    steps: tuple[BlockStep, ...]
    iteration_count: int
    converged: bool
    failure: str
    final_sse_bits: str
    final_assignments_le_u16: bytes
    final_centers_binary64_bits: tuple[tuple[str, str], ...]
    final_centers_binary32_bits: tuple[tuple[str, str], ...]
    distance_comparison_count: int
    assignment_tie_count: int
    farthest_tie_count: int
    distinct_serialized_center_count: int

    @property
    def final_assignments(self) -> U16LeView:
        return U16LeView(self.final_assignments_le_u16)


@dataclass(frozen=True)
class BlockUnit:
    word_bits: int
    capacity: int
    group_id: int
    control_valid: bool
    failure: str
    failed_start_id: int
    failure_detail: str
    ordered_points: tuple[BlockPoint, ...]
    cartesian_centers_binary64_bits: tuple[tuple[str, str], ...]
    cartesian_sse_bits: str
    filled_sse_bits: str
    starts: tuple[BlockStart, ...]
    selected_start_id: int | None
    wire_control_failures: tuple[str, ...]


@dataclass(frozen=True)
class EncodingUnit:
    arm_id: int
    word_bits: int
    row_count: int
    labels_per_row: int
    labels_le_u16: bytes
    payload: bytes
    roundtrip_labels_le_u16: bytes
    roundtrip_match: bool
    roundtrip_mismatch_count: int
    total_distance_comparisons: int
    total_payload_bytes: int
    total_pack_operations: int
    total_unpack_operations: int
    mixed_radix_encodes: int
    mixed_radix_decodes: int
    native_owned_payload_high_water_bytes: int

    @property
    def rows(self) -> range:
        """Compatibility-sized row inventory without retained row objects."""

        return range(self.row_count)


def _text_lines(path: Path) -> Iterator[list[str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as source:
            for line_number, raw in enumerate(source, start=1):
                if not raw.endswith("\n") or raw.endswith("\r\n"):
                    raise WireError(f"{path.name}:{line_number} has noncanonical LF")
                line = raw[:-1]
                if "\r" in line:
                    raise WireError(f"{path.name}:{line_number} contains CR")
                yield line.split("\t")
    except (OSError, UnicodeError) as error:
        raise WireError(f"cannot read native output {path}: {error}") from error


def parse_scalar_suite(path: Path, coordinate_id: int) -> ScalarCoordinate:
    """Parse one coordinate using the exact frozen terminal grammar."""

    if not 0 <= coordinate_id < DIMENSIONS:
        raise WireError("scalar coordinate is outside the frozen inventory")
    lines = iter(_text_lines(path))

    def take(field: str) -> list[str]:
        try:
            return next(lines)
        except StopIteration as error:
            raise WireError(f"truncated scalar output before {field}") from error

    if take("magic") != ["A4S_SCALAR_RESULT_V1"]:
        raise WireError("scalar output magic mismatch")
    case = take("CASE")
    if (
        len(case) != 10
        or case[0] != "CASE"
        or _uint(case[1], "case id") != coordinate_id
    ):
        raise WireError("scalar CASE header mismatch")
    sample_count = _uint(case[2], "scalar sample count")
    maximum_cardinality = _uint(case[3], "scalar maximum K")
    support_size = _uint(case[4], "scalar support size")
    header_comparisons = _uint(case[5], "scalar total comparisons", _UINT64_MAX)
    header_ties = _uint(case[6], "scalar total ties", _UINT64_MAX)
    effective_layers = min(MAX_K, support_size)
    if (
        sample_count != ROWS
        or maximum_cardinality != MAX_K
        or not 1 <= support_size <= ROWS
        or case[7:9] != ["0", "0"]
        or _uint(case[9], "scalar predecessor layer count") != effective_layers
    ):
        raise WireError("scalar full-shape descriptor mismatch")

    support_weight = 0
    prior_grid: int | None = None
    lowest_vector_ids: set[int] = set()
    for support_id in range(support_size):
        fields = take("SUPPORT")
        if (
            len(fields) != 6
            or fields[0] != "SUPPORT"
            or _uint(fields[1], "support case") != coordinate_id
            or _uint(fields[2], "support id") != support_id
        ):
            raise WireError("malformed or out-of-order scalar SUPPORT")
        grid = _sint(fields[3], "support grid integer")
        weight = _uint(fields[4], "support weight", _UINT64_MAX)
        vector_id = _uint(fields[5], "support lowest vector id", ROWS - 1)
        if weight == 0 or (prior_grid is not None and grid <= prior_grid):
            raise WireError("scalar support is empty or not strictly ordered")
        if vector_id in lowest_vector_ids:
            raise WireError("scalar support repeats a lowest vector id")
        prior_grid = grid
        lowest_vector_ids.add(vector_id)
        support_weight += weight
    if support_weight != ROWS:
        raise WireError("scalar support weights do not cover the fit rows")

    solutions: list[ScalarSolution] = []
    for requested in range(1, MAX_K + 1):
        fields = take("SOLUTION")
        if (
            len(fields) != 10
            or fields[0] != "SOLUTION"
            or _uint(fields[1], "solution case") != coordinate_id
            or _uint(fields[2], "requested K", MAX_K) != requested
        ):
            raise WireError("malformed or out-of-order scalar SOLUTION")
        effective = _uint(fields[3], "effective K", MAX_K)
        if effective != min(requested, support_size):
            raise WireError("scalar effective K mismatch")
        exact_sse = ExactValue(fields[4], fields[5], _sint(fields[6], "SSE exponent"))
        if exact_sse.binary_grid_exponent != -298 or int(exact_sse.numerator) < 0:
            raise WireError("scalar SSE exact contract mismatch")
        if _uint(fields[7], "interval count", MAX_K) != effective:
            raise WireError("scalar interval count mismatch")
        comparisons = _uint(fields[8], "comparison count", _UINT64_MAX)
        ties = _uint(fields[9], "tie count", _UINT64_MAX)
        if (requested == 1 or requested > support_size) and (comparisons != 0 or ties != 0):
            raise WireError("scalar copied/base layer reports nonzero work")

        clusters: list[ScalarCluster] = []
        for cluster_id in range(effective):
            cluster = take("CLUSTER")
            if (
                len(cluster) != 11
                or cluster[0] != "CLUSTER"
                or _uint(cluster[1], "cluster case") != coordinate_id
                or _uint(cluster[2], "cluster K", MAX_K) != requested
                or _uint(cluster[3], "cluster id", MAX_K - 1) != cluster_id
            ):
                raise WireError("malformed or out-of-order scalar CLUSTER")
            begin = _uint(cluster[4], "cluster begin", support_size)
            end = _uint(cluster[5], "cluster end", support_size)
            prior_end = 0 if not clusters else clusters[-1].support_end_exclusive
            if begin != prior_end or not begin < end:
                raise WireError("scalar partition is not contiguous")
            mean = ExactValue(cluster[6], cluster[7], _sint(cluster[8], "mean exponent"))
            if mean.binary_grid_exponent != -149:
                raise WireError("scalar mean exponent is not -149")
            clusters.append(
                ScalarCluster(
                    begin,
                    end,
                    mean,
                    _bits(cluster[9], 32, "cluster binary32"),
                    _bits(cluster[10], 64, "cluster binary64"),
                )
            )
        if clusters[-1].support_end_exclusive != support_size:
            raise WireError("scalar partition does not cover support")

        predecessor = take("PREDECESSOR_ROW")
        if (
            len(predecessor) < 5
            or predecessor[0] != "PREDECESSOR_ROW"
            or _uint(predecessor[1], "predecessor case") != coordinate_id
            or _uint(predecessor[2], "predecessor K", MAX_K) != requested
        ):
            raise WireError("malformed or out-of-order scalar PREDECESSOR_ROW")
        predecessor_count = _uint(predecessor[3], "predecessor count")
        if predecessor_count != support_size + 1 or len(predecessor) != 4 + predecessor_count:
            raise WireError("predecessor row shape mismatch")
        predecessor_values = [
            _uint(value, "predecessor index", support_size)
            for value in predecessor[4:]
        ]
        if predecessor_values[0] != 0 or any(
            value > prefix
            or (prefix > 0 and value == prefix)
            or (prefix > 0 and value < predecessor_values[prefix - 1])
            for prefix, value in enumerate(predecessor_values)
        ):
            raise WireError("predecessor row violates bounds/monotonicity")

        solution = ScalarSolution(
            requested,
            effective,
            exact_sse,
            tuple(clusters),
            comparisons,
            ties,
            all(
                _ordered_float32_bits(left.binary32_bits)
                < _ordered_float32_bits(right.binary32_bits)
                for left, right in zip(clusters, clusters[1:])
            ),
        )
        if requested > support_size:
            copied = solutions[support_size - 1]
            if solution.exact_sse != copied.exact_sse or solution.clusters != copied.clusters:
                raise WireError("scalar K>H solution is not an exact copied optimum")
        solutions.append(solution)

    monotone: list[bool] = []
    for layer in range(1, effective_layers + 1):
        fields = take("MONOTONE")
        if (
            len(fields) != 4
            or fields[0] != "MONOTONE"
            or _uint(fields[1], "monotone case") != coordinate_id
            or _uint(fields[2], "monotone layer", MAX_K) != layer
        ):
            raise WireError("malformed or out-of-order scalar MONOTONE")
        monotone.append(_bool(fields[3], "monotone value"))
    if not all(monotone):
        raise WireError("scalar predecessor monotonicity control failed")
    if take("END_CASE") != ["END_CASE", str(coordinate_id)]:
        raise WireError("scalar END_CASE mismatch")
    if take("END") != ["END", "1"]:
        raise WireError("scalar END mismatch")
    try:
        next(lines)
    except StopIteration:
        pass
    else:
        raise WireError("scalar output has trailing records")
    if (
        sum(solution.comparison_count for solution in solutions) != header_comparisons
        or sum(solution.exact_tie_count for solution in solutions) != header_ties
    ):
        raise WireError("scalar CASE work totals mismatch")
    return ScalarCoordinate(
        coordinate_id,
        sample_count,
        support_size,
        tuple(solutions),
        tuple(monotone),
    )


class _Reader:
    def __init__(self, path: Path):
        try:
            self._source = path.open("rb")
        except OSError as error:
            raise WireError(f"cannot open native binary output {path}: {error}") from error

    def __enter__(self) -> "_Reader":
        return self

    def __exit__(self, *_: object) -> None:
        self._source.close()

    def take(self, count: int, field: str) -> bytes:
        value = self._source.read(count)
        if len(value) != count:
            raise WireError(f"truncated {field}")
        return value

    def require(self, expected: bytes, field: str) -> None:
        if self.take(len(expected), field) != expected:
            raise WireError(f"{field} mismatch")

    def u8(self, field: str) -> int:
        return self.take(1, field)[0]

    def boolean(self, field: str) -> bool:
        value = self.u8(field)
        if value not in {0, 1}:
            raise WireError(f"{field} is not a canonical boolean byte")
        return value == 1

    def u32(self, field: str) -> int:
        return int(struct.unpack("<I", self.take(4, field))[0])

    def i32(self, field: str) -> int:
        return int(struct.unpack("<i", self.take(4, field))[0])

    def u64(self, field: str) -> int:
        return int(struct.unpack("<Q", self.take(8, field))[0])

    def decimal(self, field: str, positive: bool) -> str:
        size = self.u32(f"{field} length")
        if size == 0:
            raise WireError(f"{field} is empty")
        try:
            value = self.take(size, field).decode("ascii")
        except UnicodeError as error:
            raise WireError(f"{field} is not ASCII") from error
        parsed = _uint(value, field) if positive else _sint(value, field)
        if positive and parsed == 0:
            raise WireError(f"{field} must be positive")
        return value

    def exact(self, field: str, expected_exponent: int) -> ExactValue:
        exponent = self.i32(f"{field} exponent")
        numerator = self.decimal(f"{field} numerator", False)
        denominator = self.decimal(f"{field} denominator", True)
        value = ExactValue(numerator, denominator, exponent)
        if exponent != expected_exponent:
            raise WireError(f"{field} exponent is not {expected_exponent}")
        return value

    def eof(self) -> None:
        if self._source.read(1) != b"":
            raise WireError("native binary output has trailing bytes")


def parse_allocation_item(path: Path, expected_item_id: int) -> ProductAllocationItem | GlobalAllocationItem:
    if not 0 <= expected_item_id <= 257:
        raise WireError("expected allocation item id is outside [0,257]")
    with _Reader(path) as source:
        source.require(b"A4ALO001", "allocation output magic")
        if source.u32("allocation schema") != 1:
            raise WireError("allocation schema mismatch")
        kind = source.u32("allocation kind")
        item_id = source.u32("allocation item id")
        if item_id != expected_item_id:
            raise WireError("allocation item id mismatch")
        if expected_item_id < 256:
            if kind != 1:
                raise WireError("product allocation item has wrong kind")
            rate_index = expected_item_id // 128
            within_rate = expected_item_id % 128
            expected_group = within_rate // 2
            expected_set = within_rate % 2
            expected_capacity = 16 if rate_index == 0 else 256
            capacity = source.u32("product capacity")
            cardinality_set = source.u32("product cardinality set")
            if capacity != expected_capacity or cardinality_set != expected_set:
                raise WireError("product item id/capacity/cardinality-set binding mismatch")
            if source.u32("product curve count") != 2:
                raise WireError("product curve count mismatch")
            requested: list[int] = []
            effective: list[int] = []
            reachable: list[bool] = []
            for offset in range(2):
                curve_id = source.u32(f"product curve {offset} id")
                if curve_id != 2 * expected_group + offset:
                    raise WireError("product item id/coordinate-pair binding mismatch")
                requested_value = source.u32(f"product curve {offset} requested")
                effective_value = source.u32(f"product curve {offset} effective")
                reachable_value = source.boolean(f"product curve {offset} reachable")
                if (
                    not 1 <= requested_value <= capacity
                    or not 1 <= effective_value <= requested_value
                    or reachable_value != (effective_value == requested_value)
                ):
                    raise WireError("product cardinality/reachability invariant mismatch")
                requested.append(requested_value)
                effective.append(effective_value)
                reachable.append(reachable_value)
            if cardinality_set == 1 and any(
                value == 0 or value & (value - 1) != 0 for value in requested
            ):
                raise WireError("dyadic product allocation selected a non-power-of-two K")
            used = source.u64("product used states")
            all_reachable = source.boolean("product all reachable")
            exact_sse = source.exact("product SSE", -298)
            if int(exact_sse.numerator) < 0:
                raise WireError("product SSE is negative")
            candidates = source.u64("product candidates")
            source.require(b"A4AOEND1", "allocation terminal")
            source.eof()
            if used != requested[0] * requested[1] or used > capacity:
                raise WireError("product used-state invariant mismatch")
            if all_reachable != all(reachable):
                raise WireError("product reachability invariant mismatch")
            expected_candidates = (
                5 if cardinality_set == 1 and capacity == 16 else
                9 if cardinality_set == 1 else
                capacity
            )
            if candidates != expected_candidates:
                raise WireError("product optimized-frontier counter mismatch")
            return ProductAllocationItem(
                item_id,
                capacity,
                cardinality_set == 1,
                (requested[0], requested[1]),
                (effective[0], effective[1]),
                used,
                all_reachable,
                exact_sse,
                candidates,
            )
        if kind != 2:
            raise WireError("global allocation item has wrong kind")
        expected_budget = 256 if expected_item_id == 256 else 512
        budget = source.u32("global budget")
        if budget != expected_budget or source.u32("global curve count") != DIMENSIONS:
            raise WireError("global curve count mismatch")
        used_bits = source.u32("global used bits")
        all_reachable = source.boolean("global all reachable")
        exact_sse = source.exact("global SSE", -298)
        if int(exact_sse.numerator) < 0:
            raise WireError("global SSE is negative")
        transitions = source.u64("global transitions")
        if source.u32("global selected record count") != DIMENSIONS:
            raise WireError("global selected-record count mismatch")
        widths: list[int] = []
        effective: list[int] = []
        replay_reachable = True
        for coordinate in range(DIMENSIONS):
            if source.u32("global coordinate") != coordinate:
                raise WireError("global coordinate order mismatch")
            width = source.u8("global width")
            requested = source.u32("global requested K")
            observed_effective = source.u32("global effective K")
            reachable = source.boolean("global reachable")
            if (
                width > 8
                or requested != 1 << width
                or not 1 <= observed_effective <= requested
                or reachable != (requested == observed_effective)
            ):
                raise WireError("global selected-record invariant mismatch")
            widths.append(width)
            effective.append(observed_effective)
            replay_reachable = replay_reachable and reachable
        source.require(b"A4AOEND1", "allocation terminal")
        source.eof()
        if used_bits != sum(widths) or used_bits > budget:
            raise WireError("global bit-budget invariant mismatch")
        if all_reachable != replay_reachable:
            raise WireError("global reachability invariant mismatch")
        return GlobalAllocationItem(
            item_id,
            budget,
            used_bits,
            all_reachable,
            exact_sse,
            transitions,
            tuple(widths),
            tuple(effective),
        )


def _center_pair(
    fields: Sequence[str],
    offset: int,
    field: str,
    width: int = 64,
    *,
    canonical_zero: bool = False,
) -> tuple[str, str]:
    return (
        _bits(fields[offset], width, f"{field}[0]", canonical_zero=canonical_zero),
        _bits(
            fields[offset + 1],
            width,
            f"{field}[1]",
            canonical_zero=canonical_zero,
        ),
    )


def _append_u16(payload: bytearray, value: int, maximum: int, field: str) -> None:
    if not 0 <= value < maximum or value > 0xFFFF:
        raise WireError(f"{field} is outside its uint16 codebook")
    payload.extend(struct.pack("<H", value))


_BLOCK_FAILURES = {
    "NONE",
    "NONFINITE_CONTROL",
    "CANDIDATE_SSE_INCREASE",
    "ITERATION_LIMIT",
    "SERIALIZED_CENTER_COLLISION",
    "CARTESIAN_DOMINANCE",
}


def parse_block_suite(
    path: Path,
    *,
    word_bits: int,
    group_id: int,
    expected_axis0_bits: Sequence[str],
    expected_axis1_bits: Sequence[str],
) -> BlockUnit:
    """Parse one full eight-start unit with an exact, streaming grammar."""

    if word_bits not in {4, 8} or not 0 <= group_id < GROUPS:
        raise WireError("block unit identity is outside the frozen inventory")
    capacity = 1 << word_bits
    lines = iter(_text_lines(path))

    def take(field: str) -> list[str]:
        try:
            return next(lines)
        except StopIteration as error:
            raise WireError(f"truncated block output before {field}") from error

    if take("magic") != ["A4S_BLOCK_RESULT_V1"]:
        raise WireError("block output magic mismatch")
    if take("protocol") != ["PROTOCOL", PROTOCOL_HASH_DOMAIN]:
        raise WireError("block hash-domain mismatch")
    case = take("CASE")
    if len(case) != 13 or case[0] != "CASE":
        raise WireError("block CASE header mismatch")
    axis0_count = _uint(case[7], "block axis0 count")
    axis1_count = _uint(case[8], "block axis1 count")
    reported_control_valid = _bool(case[9], "block control valid")
    case_failure = case[10]
    if case_failure not in _BLOCK_FAILURES:
        raise WireError("unknown block case failure")
    failed_start_id = _uint(case[11], "block failed start", 7)
    failure_detail = case[12]
    if (
        _uint(case[1], "block case id") != group_id
        or case[2] != PROTOCOL_HASH_DOMAIN
        or case[3] != "synthetic_cost_projection"
        or _uint(case[4], "block capacity") != capacity
        or _uint(case[5], "block group") != group_id
        or _uint(case[6], "block point count") != ROWS
        or axis0_count != len(expected_axis0_bits)
        or axis1_count != len(expected_axis1_bits)
        or axis0_count == 0
        or axis1_count == 0
        or axis0_count * axis1_count > capacity
    ):
        raise WireError("block CASE descriptor/unit binding mismatch")
    if reported_control_valid != (case_failure == "NONE"):
        raise WireError("block control/failure header mismatch")
    if reported_control_valid and failure_detail != "":
        raise WireError("valid block case has a failure detail")
    if reported_control_valid and failed_start_id != 0:
        raise WireError("valid block case has a nonzero failed-start id")
    if not reported_control_valid and failure_detail == "":
        raise WireError("invalid block case omits its failure detail")

    wire_control_failures: list[str] = []

    for axis_id, expected in enumerate((expected_axis0_bits, expected_axis1_bits)):
        for axis_index, expected_bits in enumerate(expected):
            fields = take("AXIS")
            if (
                len(fields) != 5
                or fields[0] != "AXIS"
                or _uint(fields[1], "axis case") != group_id
                or _uint(fields[2], "axis id", 1) != axis_id
                or _uint(fields[3], "axis index") != axis_index
                or _bits(fields[4], 64, "block axis") != expected_bits
            ):
                raise WireError("block AXIS identity/order/value mismatch")

    points: list[BlockPoint] = []
    prior_point_key: tuple[int, str, int] | None = None
    seen_vector_ids = bytearray(ROWS)
    for row in range(ROWS):
        fields = take("ROW")
        if (
            len(fields) != 8
            or fields[0] != "ROW"
            or _uint(fields[1], "row case") != group_id
            or _uint(fields[2], "block row", ROWS - 1) != row
        ):
            raise WireError("malformed or out-of-order block ROW")
        cell_id = _uint(fields[3], "block cell")
        vector_id = _uint(fields[4], "block vector", ROWS - 1)
        digest = _digest(fields[5], "block selection digest")
        expected_digest = hashlib.sha256(
            f"{PROTOCOL_HASH_DOMAIN}|synthetic_cost_projection|{cell_id}|{vector_id}".encode(
                "utf-8"
            )
        ).hexdigest()
        key = (cell_id, digest, vector_id)
        if (
            cell_id != 0
            or digest != expected_digest
            or seen_vector_ids[vector_id] != 0
            or (prior_point_key is not None and key <= prior_point_key)
        ):
            raise WireError("block ROW provenance/order identity mismatch")
        seen_vector_ids[vector_id] = 1
        prior_point_key = key
        points.append(
            BlockPoint(
                cell_id,
                vector_id,
                digest,
                _bits(fields[6], 32, "block coordinate0"),
                _bits(fields[7], 32, "block coordinate1"),
            )
        )
    if not all(seen_vector_ids):
        raise WireError("block ROW vector inventory is not the frozen panel")

    cartesian_header = take("CARTESIAN")
    if (
        len(cartesian_header) != 5
        or cartesian_header[0] != "CARTESIAN"
        or _uint(cartesian_header[1], "Cartesian case") != group_id
        or _uint(cartesian_header[2], "Cartesian count", capacity)
        != axis0_count * axis1_count
    ):
        raise WireError("block CARTESIAN descriptor mismatch")
    allow_case_infinity = case_failure == "NONFINITE_CONTROL"
    cartesian_sse = _bits(
        cartesian_header[3],
        64,
        "Cartesian SSE",
        canonical_zero=True,
        allow_positive_infinity=allow_case_infinity,
        nonnegative=True,
    )
    filled_sse = _bits(
        cartesian_header[4],
        64,
        "filled SSE",
        canonical_zero=True,
        allow_positive_infinity=allow_case_infinity,
        nonnegative=True,
    )
    cartesian: list[tuple[str, str]] = []
    for center_id in range(axis0_count * axis1_count):
        fields = take("CARTESIAN_CENTER")
        if (
            len(fields) != 5
            or fields[0] != "CARTESIAN_CENTER"
            or _uint(fields[1], "Cartesian-center case") != group_id
            or _uint(fields[2], "Cartesian center id") != center_id
        ):
            raise WireError("Cartesian center identity/order mismatch")
        center = _center_pair(fields, 3, "Cartesian center")
        expected_center = (
            expected_axis0_bits[center_id % axis0_count],
            expected_axis1_bits[center_id // axis0_count],
        )
        if center != expected_center:
            raise WireError("Cartesian center differs from the bound scalar axes")
        cartesian.append(center)

    starts: list[BlockStart] = []
    for start_id in range(8):
        fields = take("START")
        if (
            len(fields) != 19
            or fields[0] != "START"
            or _uint(fields[1], "start case") != group_id
            or _uint(fields[2], "block start id", 7) != start_id
        ):
            raise WireError("malformed or out-of-order block START")
        first_seed_digest = _digest(fields[3], "first-seed digest")
        selected_count = _uint(fields[4], "selected vector count", capacity)
        initial_count = _uint(fields[5], "initial center count", capacity)
        start_failure = fields[10]
        if start_failure not in _BLOCK_FAILURES:
            raise WireError("unknown block start failure")
        allow_start_infinity = start_failure == "NONFINITE_CONTROL"
        initial_sse = _bits(
            fields[6],
            64,
            "initial SSE",
            canonical_zero=True,
            allow_positive_infinity=allow_start_infinity,
            nonnegative=True,
        )
        step_count = _uint(fields[7], "step count", 300)
        iteration_count = _uint(fields[8], "iteration count", 300)
        converged = _bool(fields[9], "converged")
        final_sse = _bits(
            fields[11],
            64,
            "final SSE",
            canonical_zero=True,
            allow_positive_infinity=allow_start_infinity,
            nonnegative=True,
        )
        final_assignment_count = _uint(fields[12], "final assignment count", ROWS)
        final_center_count = _uint(fields[13], "final center count", capacity)
        serialized_count = _uint(fields[14], "serialized center count", capacity)
        distinct_count = _uint(fields[15], "distinct center count", capacity)
        distance_count = _uint(fields[16], "block distance count", _UINT64_MAX)
        assignment_ties = _uint(fields[17], "block assignment ties", _UINT64_MAX)
        farthest_ties = _uint(fields[18], "block farthest ties", _UINT64_MAX)
        if step_count != iteration_count:
            raise WireError("block step/iteration count mismatch")
        if distinct_count > serialized_count:
            raise WireError("block distinct-center count exceeds serialized inventory")
        if start_failure == "NONE" and not converged:
            wire_control_failures.append(
                f"start {start_id} is failure-free but did not converge"
            )
        expected_selected_count = (
            capacity - len(cartesian) if start_id == 0 else capacity
        )
        full_final_state = (
            initial_count == capacity
            and final_assignment_count == ROWS
            and final_center_count == capacity
            and serialized_count == capacity
        )
        if start_failure == "NONE" and (
            selected_count != expected_selected_count or not full_final_state
        ):
            raise WireError("failure-free block start has an incomplete inventory")
        if start_failure in {
            "CANDIDATE_SSE_INCREASE",
            "ITERATION_LIMIT",
            "SERIALIZED_CENTER_COLLISION",
            "CARTESIAN_DOMINANCE",
        } and (
            selected_count != expected_selected_count or not full_final_state
        ):
            raise WireError("finite failed block start has an incomplete final state")
        if start_failure == "NONFINITE_CONTROL" and (
            initial_count == 0
            or final_center_count == 0
            or serialized_count not in {0, final_center_count}
            or final_assignment_count not in {0, ROWS}
        ):
            raise WireError("nonfinite block start has an invalid retained-state shape")
        if (
            start_failure in {"CANDIDATE_SSE_INCREASE", "ITERATION_LIMIT"}
            and converged
        ) or (start_failure == "ITERATION_LIMIT" and step_count != 300):
            raise WireError("block failure kind disagrees with convergence inventory")
        if start_failure == "SERIALIZED_CENTER_COLLISION" and (
            not converged or distinct_count >= capacity
        ):
            raise WireError("serialized-collision failure lacks its complete witness")
        if start_failure == "NONFINITE_CONTROL" and converged:
            raise WireError("nonfinite block start cannot be marked converged")

        selected_ids: list[int] = []
        for selected_index in range(selected_count):
            child = take("START_SELECTED")
            if (
                len(child) != 5
                or child[0] != "START_SELECTED"
                or _uint(child[1], "selected case") != group_id
                or _uint(child[2], "selected start", 7) != start_id
                or _uint(child[3], "selected index") != selected_index
            ):
                raise WireError("START_SELECTED identity/order mismatch")
            selected_ids.append(_uint(child[4], "selected vector", ROWS - 1))
        if len(set(selected_ids)) != len(selected_ids):
            raise WireError("START_SELECTED repeats a vector")
        if start_id == 0:
            if first_seed_digest != "0" * 64:
                raise WireError("Cartesian start has a nonzero first-seed digest")
            if selected_count + len(cartesian) != initial_count:
                raise WireError("Cartesian fill selection/center inventory mismatch")
        elif not selected_ids or first_seed_digest != hashlib.sha256(
            (
                f"{PROTOCOL_HASH_DOMAIN}|synthetic_cost_projection|{capacity}|"
                f"{group_id}|{start_id}|0|{selected_ids[0]}"
            ).encode("utf-8")
        ).hexdigest():
            raise WireError("salted start digest/vector binding mismatch")
        elif selected_count != initial_count:
            raise WireError("salted start selection/center inventory mismatch")
        initial_centers: list[tuple[str, str]] = []
        for center_id in range(initial_count):
            child = take("START_CENTER")
            if (
                len(child) != 6
                or child[0] != "START_CENTER"
                or _uint(child[1], "initial-center case") != group_id
                or _uint(child[2], "initial-center start", 7) != start_id
                or _uint(child[3], "initial center id") != center_id
            ):
                raise WireError("START_CENTER identity/order mismatch")
            initial_centers.append(_center_pair(child, 4, "initial center"))
        if start_id == 0 and initial_centers[: len(cartesian)] != cartesian:
            raise WireError("Cartesian start does not retain its exact axis-product prefix")

        steps: list[BlockStep] = []
        for iteration in range(1, step_count + 1):
            step_header = take("STEP")
            if (
                len(step_header) != 9
                or step_header[0] != "STEP"
                or _uint(step_header[1], "step case") != group_id
                or _uint(step_header[2], "step start", 7) != start_id
                or _uint(step_header[3], "step iteration", 300) != iteration
            ):
                raise WireError("STEP identity/order mismatch")
            prior_sse = _bits(
                step_header[4],
                64,
                "step prior SSE",
                canonical_zero=True,
                nonnegative=True,
            )
            candidate_sse = _bits(
                step_header[5],
                64,
                "step candidate SSE",
                canonical_zero=True,
                nonnegative=True,
            )
            changed_count = _uint(step_header[6], "changed assignments", ROWS)
            empty_count = _uint(step_header[7], "empty center count", capacity)
            center_count = _uint(step_header[8], "step center count", capacity)
            if center_count != capacity:
                raise WireError("accepted block STEP has the wrong center count")
            if int(candidate_sse, 16) > int(prior_sse, 16):
                wire_control_failures.append(
                    f"start {start_id} accepted STEP {iteration} increases SSE"
                )
            empty_ids: list[int] = []
            for empty_index in range(empty_count):
                child = take("STEP_EMPTY")
                if (
                    len(child) != 6
                    or child[0] != "STEP_EMPTY"
                    or _uint(child[1], "empty case") != group_id
                    or _uint(child[2], "empty start", 7) != start_id
                    or _uint(child[3], "empty iteration", 300) != iteration
                    or _uint(child[4], "empty index") != empty_index
                ):
                    raise WireError("STEP_EMPTY identity/order mismatch")
                empty_ids.append(_uint(child[5], "empty center", capacity - 1))
            if len(set(empty_ids)) != len(empty_ids):
                raise WireError("STEP_EMPTY repeats a center")
            step_centers: list[tuple[str, str]] = []
            for center_id in range(center_count):
                child = take("STEP_CENTER")
                if (
                    len(child) != 7
                    or child[0] != "STEP_CENTER"
                    or _uint(child[1], "step-center case") != group_id
                    or _uint(child[2], "step-center start", 7) != start_id
                    or _uint(child[3], "step-center iteration", 300) != iteration
                    or _uint(child[4], "step center id") != center_id
                ):
                    raise WireError("STEP_CENTER identity/order mismatch")
                step_centers.append(_center_pair(child, 5, "step center"))
            assignment_preimages: list[bytes] = []
            for tag in ("STEP_ASSIGNMENT_BEFORE", "STEP_ASSIGNMENT_AFTER"):
                packed = bytearray()
                for row in range(ROWS):
                    child = take(tag)
                    if (
                        len(child) != 7
                        or child[0] != tag
                        or _uint(child[1], "assignment-preimage case") != group_id
                        or _uint(child[2], "assignment-preimage start", 7) != start_id
                        or _uint(child[3], "assignment-preimage iteration", 300)
                        != iteration
                        or _uint(child[4], "assignment-preimage row", ROWS - 1) != row
                        or _uint(child[5], "assignment-preimage vector", ROWS - 1)
                        != points[row].vector_id
                    ):
                        raise WireError(f"{tag} identity/order mismatch")
                    _append_u16(
                        packed,
                        _uint(child[6], "assignment-preimage label", capacity - 1),
                        capacity,
                        "assignment-preimage label",
                    )
                assignment_preimages.append(bytes(packed))
            observed_changed = sum(
                assignment_preimages[0][offset : offset + 2]
                != assignment_preimages[1][offset : offset + 2]
                for offset in range(0, 2 * ROWS, 2)
            )
            if observed_changed != changed_count:
                raise WireError("STEP changed-assignment count mismatch")
            step = BlockStep(
                iteration,
                prior_sse,
                candidate_sse,
                changed_count,
                tuple(empty_ids),
                tuple(step_centers),
                assignment_preimages[0],
                assignment_preimages[1],
            )
            if steps and (
                step.prior_sse_bits != steps[-1].candidate_sse_bits
                or step.assignments_before_le_u16
                != steps[-1].assignments_after_le_u16
            ):
                raise WireError("accepted block STEP chain is discontinuous")
            if changed_count == 0 and iteration != step_count:
                wire_control_failures.append(
                    f"start {start_id} continues after convergence at STEP {iteration}"
                )
            steps.append(step)

        if steps and initial_sse != steps[0].prior_sse_bits:
            raise WireError("block initial SSE differs from first STEP")
        if converged != bool(steps and steps[-1].changed_assignment_count == 0):
            wire_control_failures.append(
                f"start {start_id} convergence flag differs from its STEP trace"
            )

        final_assignments = bytearray()
        for row in range(final_assignment_count):
            child = take("FINAL_ASSIGNMENT")
            if (
                len(child) != 6
                or child[0] != "FINAL_ASSIGNMENT"
                or _uint(child[1], "final-assignment case") != group_id
                or _uint(child[2], "final-assignment start", 7) != start_id
                or _uint(child[3], "final-assignment row", ROWS - 1) != row
                or _uint(child[4], "final-assignment vector", ROWS - 1)
                != points[row].vector_id
            ):
                raise WireError("FINAL_ASSIGNMENT identity/order mismatch")
            _append_u16(
                final_assignments,
                _uint(child[5], "final-assignment label", capacity - 1),
                capacity,
                "final-assignment label",
            )
        final_centers: list[tuple[str, str]] = []
        for center_id in range(final_center_count):
            child = take("FINAL_CENTER")
            if (
                len(child) != 6
                or child[0] != "FINAL_CENTER"
                or _uint(child[1], "final-center case") != group_id
                or _uint(child[2], "final-center start", 7) != start_id
                or _uint(child[3], "final center id") != center_id
            ):
                raise WireError("FINAL_CENTER identity/order mismatch")
            final_centers.append(_center_pair(child, 4, "final center"))
        serialized: list[tuple[str, str]] = []
        for center_id in range(serialized_count):
            child = take("FINAL_SERIALIZED_CENTER")
            if (
                len(child) != 6
                or child[0] != "FINAL_SERIALIZED_CENTER"
                or _uint(child[1], "serialized-center case") != group_id
                or _uint(child[2], "serialized-center start", 7) != start_id
                or _uint(child[3], "serialized center id") != center_id
            ):
                raise WireError("FINAL_SERIALIZED_CENTER identity/order mismatch")
            serialized.append(
                _center_pair(child, 4, "serialized center", 32, canonical_zero=True)
            )
        if len(set(serialized)) != distinct_count:
            raise WireError("serialized-center distinct count does not match its preimage")
        if take("END_START") != ["END_START", str(group_id), str(start_id)]:
            raise WireError("block END_START mismatch")
        if not steps and (
            initial_sse != final_sse or tuple(initial_centers) != tuple(final_centers)
        ):
            raise WireError("zero-step block start changes its retained final state")
        if steps and final_assignment_count == ROWS and (
            bytes(final_assignments) != steps[-1].assignments_after_le_u16
            or final_sse != steps[-1].candidate_sse_bits
        ):
            raise WireError("block final state differs from the last accepted STEP")
        starts.append(
            BlockStart(
                start_id=start_id,
                first_seed_digest=first_seed_digest,
                initialization_vector_ids=tuple(selected_ids),
                initial_centers_binary64_bits=tuple(initial_centers),
                initial_sse_bits=initial_sse,
                steps=tuple(steps),
                iteration_count=iteration_count,
                converged=converged,
                failure=start_failure,
                final_sse_bits=final_sse,
                final_assignments_le_u16=bytes(final_assignments),
                final_centers_binary64_bits=tuple(final_centers),
                final_centers_binary32_bits=tuple(serialized),
                distance_comparison_count=distance_count,
                assignment_tie_count=assignment_ties,
                farthest_tie_count=farthest_ties,
                distinct_serialized_center_count=distinct_count,
            )
        )

    if filled_sse != starts[0].initial_sse_bits:
        raise WireError("filled Cartesian-start SSE differs from start 0 initial SSE")

    best = take("BEST")
    selected_start: int | None
    if not reported_control_valid:
        if best != ["BEST", str(group_id), "0"]:
            raise WireError("invalid block case has malformed BEST terminal")
        selected_start = None
    else:
        if (
            len(best) != 8
            or best[0:3] != ["BEST", str(group_id), "1"]
        ):
            raise WireError("valid block case has malformed BEST header")
        selected_start = _uint(best[3], "best start", 7)
        selected = starts[selected_start]
        replay_best = min(
            range(8), key=lambda start_id: (int(starts[start_id].final_sse_bits, 16), start_id)
        )
        if selected_start != replay_best:
            wire_control_failures.append("BEST violates the frozen lower-start tie rule")
        if (
            _bits(best[4], 64, "best SSE", canonical_zero=True, nonnegative=True)
            != selected.final_sse_bits
            or _uint(best[5], "best center count")
            != len(selected.final_centers_binary64_bits)
            or _uint(best[6], "best assignment count") * 2
            != len(selected.final_assignments_le_u16)
            or _uint(best[7], "best serialized-center count")
            != len(selected.final_centers_binary32_bits)
        ):
            raise WireError("BEST header differs from the selected start")
        for center_id, (center64, center32) in enumerate(
            zip(
                selected.final_centers_binary64_bits,
                selected.final_centers_binary32_bits,
            )
        ):
            child = take("BEST_CENTER")
            if (
                len(child) != 7
                or child[0] != "BEST_CENTER"
                or _uint(child[1], "best-center case") != group_id
                or _uint(child[2], "best-center id") != center_id
                or _center_pair(child, 3, "best center") != center64
                or _center_pair(
                    child,
                    5,
                    "best serialized center",
                    32,
                    canonical_zero=True,
                ) != center32
            ):
                raise WireError("BEST_CENTER duplicate-state mismatch")
        for row in range(ROWS):
            child = take("BEST_ASSIGNMENT")
            expected_label = int.from_bytes(
                selected.final_assignments_le_u16[2 * row : 2 * row + 2], "little"
            )
            if (
                len(child) != 5
                or child[0] != "BEST_ASSIGNMENT"
                or _uint(child[1], "best-assignment case") != group_id
                or _uint(child[2], "best-assignment row", ROWS - 1) != row
                or _uint(child[3], "best-assignment vector", ROWS - 1)
                != points[row].vector_id
                or _uint(child[4], "best-assignment label", capacity - 1)
                != expected_label
            ):
                raise WireError("BEST_ASSIGNMENT duplicate-state mismatch")
    if take("END_CASE") != ["END_CASE", str(group_id)]:
        raise WireError("block END_CASE mismatch")
    terminal = take("END")
    expected_valid = 1 if reported_control_valid else 0
    if terminal != ["END", "1", str(expected_valid), str(1 - expected_valid)]:
        raise WireError("block END inventory mismatch")
    try:
        next(lines)
    except StopIteration:
        pass
    else:
        raise WireError("block output has trailing records")
    failed_starts = [start for start in starts if start.failure != "NONE"]
    if reported_control_valid and failed_starts:
        raise WireError("valid block case contains a failed start")
    if not reported_control_valid and (
        not failed_starts
        or failed_starts[0].start_id != failed_start_id
        or failed_starts[0].failure != case_failure
    ):
        raise WireError("block case header does not identify the exact first failed start")
    unit = BlockUnit(
        word_bits=word_bits,
        capacity=capacity,
        group_id=group_id,
        control_valid=reported_control_valid and not wire_control_failures,
        failure=case_failure,
        failed_start_id=failed_start_id,
        failure_detail=failure_detail,
        ordered_points=tuple(points),
        cartesian_centers_binary64_bits=tuple(cartesian),
        cartesian_sse_bits=cartesian_sse,
        filled_sse_bits=filled_sse,
        starts=tuple(starts),
        selected_start_id=selected_start,
        wire_control_failures=tuple(wire_control_failures),
    )
    if wire_control_failures:
        raise WireControlError("; ".join(wire_control_failures), unit)
    return unit


def parse_encoding_suite(path: Path, *, expected_arm_id: int, word_bits: int) -> EncodingUnit:
    if expected_arm_id not in range(4) or word_bits not in {4, 8}:
        raise WireError("encoding unit identity is outside the frozen inventory")
    paid_bytes = 32 if word_bits == 4 else 64
    expected_label_count = DIMENSIONS if expected_arm_id == 3 else GROUPS
    with _Reader(path) as source:
        source.require(b"A4EOUT02", "encoding output magic")
        if source.u32("encoding schema") != 2:
            raise WireError("encoding schema mismatch")
        if source.u32("encoding arm") != expected_arm_id or source.u32("encoding bits") != word_bits:
            raise WireError("encoding arm/rate mismatch")
        if (
            source.u32("encoding row count") != ROWS
            or source.u32("encoding dimension count") != DIMENSIONS
            or source.u32("encoding group count") != GROUPS
            or source.u32("encoding arm count") != 1
        ):
            raise WireError("encoding full-shape descriptor mismatch")
        labels_preimage = bytearray()
        payload_preimage = bytearray()
        roundtrip_preimage = bytearray()
        observed_comparisons = 0
        observed_pack = 0
        observed_unpack = 0
        mismatch_count = 0
        for vector_id in range(ROWS):
            if source.u32("encoding row marker") != 0x31574F52:
                raise WireError("encoding row marker mismatch")
            if source.u32("encoding vector id") != vector_id:
                raise WireError("encoding vector order mismatch")
            if source.u32("encoding row arm") != expected_arm_id:
                raise WireError("encoding row arm mismatch")
            comparisons = source.u64("encoding row comparisons")
            label_count = source.u32("encoding label count")
            if label_count != expected_label_count:
                raise WireError("encoding label count mismatch")
            row_labels = bytearray()
            # Preserve a malformed-but-replayable packing result as compact
            # uint16.  The producer validates the selected model's narrower
            # label domain and classifies violations as CONTROL_INVALID.
            label_maximum = 1 << 16
            for _ in range(label_count):
                _append_u16(
                    row_labels,
                    source.u32("encoding label"),
                    label_maximum,
                    "encoding label",
                )
            payload_count = source.u32("encoding payload bytes")
            if payload_count != paid_bytes:
                raise WireError("encoding payload size mismatch")
            row_payload = source.take(payload_count, "encoding payload")
            roundtrip_count = source.u32("encoding roundtrip count")
            if roundtrip_count != label_count:
                raise WireError("encoding roundtrip count mismatch")
            row_roundtrip = bytearray()
            for _ in range(roundtrip_count):
                _append_u16(
                    row_roundtrip,
                    source.u32("encoding roundtrip label"),
                    label_maximum,
                    "encoding roundtrip label",
                )
            match_byte = source.u32("encoding roundtrip match")
            if match_byte not in {0, 1}:
                raise WireError("encoding roundtrip match is not a canonical boolean")
            pack_count = source.u64("encoding pack count")
            unpack_count = source.u64("encoding unpack count")
            row_equal = row_labels == row_roundtrip
            if match_byte == 1 and not row_equal:
                raise WireError("encoding child claims a false roundtrip match")
            if match_byte == 0 or not row_equal or pack_count != 1 or unpack_count != 1:
                mismatch_count += 1
            labels_preimage.extend(row_labels)
            payload_preimage.extend(row_payload)
            roundtrip_preimage.extend(row_roundtrip)
            observed_comparisons += comparisons
            observed_pack += pack_count
            observed_unpack += unpack_count
        source.require(b"A4EOEND2", "encoding output terminal")
        if source.u32("encoding terminal rows") != ROWS or source.u32("encoding terminal arms") != 1:
            raise WireError("encoding terminal shape mismatch")
        if source.u32("encoding terminal arm") != expected_arm_id:
            raise WireError("encoding terminal arm mismatch")
        total_comparisons = source.u64("encoding total comparisons")
        total_payload = source.u64("encoding total payload")
        total_pack = source.u64("encoding total pack")
        total_unpack = source.u64("encoding total unpack")
        mixed_encodes = source.u64("encoding mixed-radix encodes")
        mixed_decodes = source.u64("encoding mixed-radix decodes")
        if source.u64("encoding arm vectors") != ROWS:
            raise WireError("encoding arm-vector count mismatch")
        native_hwm = source.u64("encoding native payload HWM")
        source.eof()
    if total_payload != ROWS * paid_bytes:
        raise WireError("encoding terminal totals mismatch")
    if (
        total_comparisons != observed_comparisons
        or total_pack != observed_pack
        or total_unpack != observed_unpack
    ):
        raise WireError("encoding comparison total mismatch")
    expected_mixed = ROWS * GROUPS if expected_arm_id in {0, 1} else 0
    if mixed_encodes != expected_mixed or mixed_decodes != expected_mixed:
        raise WireError("encoding mixed-radix total mismatch")
    if native_hwm < ROWS * DIMENSIONS * 4:
        raise WireError("encoding native payload HWM omits the matrix")
    return EncodingUnit(
        arm_id=expected_arm_id,
        word_bits=word_bits,
        row_count=ROWS,
        labels_per_row=expected_label_count,
        labels_le_u16=bytes(labels_preimage),
        payload=bytes(payload_preimage),
        roundtrip_labels_le_u16=bytes(roundtrip_preimage),
        roundtrip_match=mismatch_count == 0,
        roundtrip_mismatch_count=mismatch_count,
        total_distance_comparisons=total_comparisons,
        total_payload_bytes=total_payload,
        total_pack_operations=total_pack,
        total_unpack_operations=total_unpack,
        mixed_radix_encodes=mixed_encodes,
        mixed_radix_decodes=mixed_decodes,
        native_owned_payload_high_water_bytes=native_hwm,
    )


def pack_u32_le(values: Iterable[int]) -> bytes:
    """Canonical little-endian helper for producer/native input frames."""

    payload = bytearray()
    for value in values:
        if not 0 <= int(value) <= 0xFFFFFFFF:
            raise WireError("uint32 input value is out of range")
        payload.extend(struct.pack("<I", int(value)))
    return bytes(payload)


def pack_u64_le(values: Iterable[int]) -> bytes:
    payload = bytearray()
    for value in values:
        if not 0 <= int(value) <= 0xFFFFFFFFFFFFFFFF:
            raise WireError("uint64 input value is out of range")
        payload.extend(struct.pack("<Q", int(value)))
    return bytes(payload)
