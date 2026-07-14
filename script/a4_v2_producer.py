#!/usr/bin/env python3
"""A4 V2 comparative-instrument producer.

The module contains the 396-unit producer state machine and no top-level
execution.  NumPy is imported lazily inside ``run_attempt`` so importing this
source during review cannot generate the synthetic panel.  All optimized
scientific decisions remain in the frozen native child; Python supplies the
registered binary interchange, strict parsing, producer controls, immutable
in-memory records, packing aggregation, and atomic intermediate bundle.

The independent verifier and archive implementation must not import this
module.  In particular, this producer's parser and direct block-control replay
are not evidence of independent verification.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import struct
import ctypes
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, NoReturn, Protocol, Sequence

import a4_v2_producer_wire as wire


PROTOCOL_VERSION = "saq-a4-v2-synthetic-construction-20260714-schema1"
SCIENTIFIC_HASH_DOMAIN = "saq-attempt4-a4-1-20260713-schema2"
DATASET_ID = "synthetic_cost_projection"
SEED = 20260713
RAW_INPUT_SHA256 = "10e128854768358323a8b13066a6f34076cfc7216db35992ac58ece0ec6f5b0c"
SELECTION_STREAM_SHA256 = "6e7dbc26c7d5f63c2c8e5a5fa4d647cf3237597696c3f2431fd715ffbc712145"
ARM_ORDER = (
    "dyadic_word",
    "arbitrary_word",
    "trained_block_vq",
    "global_dyadic_pack_cap8",
)
ARM_OWNER = {
    "dyadic_word": "C_arm_dyadic",
    "arbitrary_word": "C_arm_arbitrary",
    "trained_block_vq": "C_arm_block",
    "global_dyadic_pack_cap8": "C_arm_global",
}
PRIMARY_CAP_MICROSECONDS = 34_560_000_000
_LIBC = ctypes.CDLL(None, use_errno=True)
_RENAMEAT2 = _LIBC.renameat2
_RENAMEAT2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
_RENAMEAT2.restype = ctypes.c_int
_RENAME_NOREPLACE = 1


class ProducerFailure(RuntimeError):
    """A status-bearing producer failure resolved by the supervisor."""

    def __init__(self, status: str, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class BundlePublicationVisibleFailure(ProducerFailure):
    """The physical bundle target is visible but cannot be admitted as U395."""

    def __init__(self, detail: str):
        super().__init__("ARTIFACT_INVALID", detail)
        self.physical_target_visible = True


class ProducerHooks(Protocol):
    """Supervisor-owned effects available to one producer attempt."""

    attempt_id: int
    attempt_root: Path

    def switch(self, phase: str, owner: str) -> None: ...

    def invoke_native(self, arguments: Sequence[str]) -> None: ...

    def complete_unit(self, unit_index: int, state: "ProducerState") -> bool: ...

    def fail_unpublished_unit(self, status: str, detail: str) -> NoReturn: ...

    def note_created_temporary(self, path: Path) -> None: ...

    def note_deleted_temporary(self, path: Path) -> None: ...

    def reserve_permanent_bundle(self, byte_count: int) -> None: ...

    def mark_bundle_publication_visible(self) -> None: ...

    def commit_permanent_bundle(self, byte_count: int) -> None: ...

    def cancel_permanent_bundle(self, byte_count: int) -> None: ...

    def check_operational(self) -> None: ...


@dataclass(frozen=True)
class InputIdentity:
    raw_sha256: str
    raw_bytes: int
    selection_digest_stream_sha256: str


@dataclass(frozen=True)
class GroupAllocationRecord:
    word_bits: int
    group_id: int
    dyadic: wire.ProductAllocationItem
    arbitrary: wire.ProductAllocationItem


@dataclass(frozen=True)
class GlobalAllocationRecord:
    word_bits: int
    allocation: wire.GlobalAllocationItem


@dataclass(frozen=True)
class BlockStepRecord:
    step: wire.BlockStep

    @property
    def assignments_before_le_u16(self) -> bytes:
        return self.step.assignments_before_le_u16

    @property
    def assignments_after_le_u16(self) -> bytes:
        return self.step.assignments_after_le_u16


@dataclass(frozen=True)
class BlockStartRecord:
    start: wire.BlockStart
    direct_replay_match: bool
    cartesian_dominance_pass: bool

    @property
    def steps(self) -> tuple[BlockStepRecord, ...]:
        return tuple(BlockStepRecord(step) for step in self.start.steps)


@dataclass(frozen=True)
class BlockRecord:
    unit: wire.BlockUnit
    starts: tuple[BlockStartRecord, ...]
    selected_centers_binary32_bits: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class EncodingRecord:
    arm: str
    unit: wire.EncodingUnit
    label_domain_valid: bool

    @property
    def labels_le_u16(self) -> bytes:
        return self.unit.labels_le_u16

    @property
    def payload(self) -> bytes:
        return self.unit.payload

    @property
    def roundtrip_match(self) -> bool:
        return self.unit.roundtrip_match

    @property
    def roundtrip_mismatch_count(self) -> int:
        return self.unit.roundtrip_mismatch_count

    @property
    def control_valid(self) -> bool:
        return self.label_domain_valid and self.unit.roundtrip_match


@dataclass(frozen=True)
class BundleFileIdentity:
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class BundleIdentity:
    directory: str
    files: tuple[BundleFileIdentity, ...]
    total_bytes: int


@dataclass(frozen=True)
class ProducerState:
    """Immutable logical prefix; the read-only NumPy panel is an input view."""

    matrix: Any | None = None
    input_identity: InputIdentity | None = None
    scalar_coordinates: tuple[wire.ScalarCoordinate, ...] = ()
    group_allocations: tuple[GroupAllocationRecord, ...] = ()
    global_allocations: tuple[GlobalAllocationRecord, ...] = ()
    blocks: tuple[BlockRecord, ...] = ()
    encodings: tuple[EncodingRecord, ...] = ()
    bundle: BundleIdentity | None = None
    completed_unit_count: int = 0
    last_completed_unit_index: int = -1
    full_shape_complete: bool = False
    representation_valid: bool = True
    control_valid: bool = True

    def complete(self, unit_index: int, **changes: Any) -> "ProducerState":
        if unit_index != self.last_completed_unit_index + 1:
            raise ProducerFailure(
                "IMPLEMENTATION_INVALID",
                f"noncontiguous producer unit {unit_index} after {self.last_completed_unit_index}",
            )
        return replace(
            self,
            completed_unit_count=unit_index + 1,
            last_completed_unit_index=unit_index,
            full_shape_complete=unit_index == 395,
            **changes,
        )


def _canonical_json_body(value: Any) -> bytes:
    """Bundle JSON codec; research evidence has a separate implementation."""

    def reject_floats(item: Any) -> None:
        if isinstance(item, float):
            raise ProducerFailure("IMPLEMENTATION_INVALID", "floating JSON bundle value")
        if isinstance(item, Mapping):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ProducerFailure("IMPLEMENTATION_INVALID", "non-string bundle key")
                reject_floats(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                reject_floats(child)

    reject_floats(value)
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _write_new(path: Path, payload: bytes, hooks: ProducerHooks) -> None:
    if path.exists():
        raise ProducerFailure("ARTIFACT_INVALID", f"refusing to overwrite {path}")
    try:
        with path.open("xb", buffering=0) as output:
            written = output.write(payload)
            if written != len(payload):
                raise OSError("short write")
            os.fsync(output.fileno())
    except OSError as error:
        raise ProducerFailure("ARTIFACT_INVALID", f"cannot write {path}: {error}") from error
    hooks.note_created_temporary(path)


def _write_new_at(
    directory_fd: int,
    name: str,
    path: Path,
    payload: bytes,
    hooks: ProducerHooks,
) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
        try:
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise OSError("short write")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as error:
        raise ProducerFailure("ARTIFACT_INVALID", f"cannot write {path}: {error}") from error
    hooks.note_created_temporary(path)


def _rename_noreplace(parent_fd: int, source: str, destination: str) -> None:
    if _RENAMEAT2(
        parent_fd,
        source.encode("utf-8"),
        parent_fd,
        destination.encode("utf-8"),
        _RENAME_NOREPLACE,
    ) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))


def _delete_temporary(path: Path, hooks: ProducerHooks) -> None:
    try:
        path.unlink()
    except OSError as error:
        raise ProducerFailure("ARTIFACT_INVALID", f"cannot delete temporary {path}: {error}") from error
    hooks.note_deleted_temporary(path)


def _generate_panel(np: Any) -> tuple[Any, InputIdentity]:
    generator = np.random.Generator(np.random.PCG64(SEED))
    matrix = generator.standard_normal((wire.ROWS, wire.DIMENSIONS), dtype=np.float32)
    if (
        matrix.shape != (wire.ROWS, wire.DIMENSIONS)
        or matrix.dtype != np.dtype("float32")
        or not matrix.flags.c_contiguous
        or matrix.dtype.byteorder not in {"<", "=", "|"}
    ):
        raise ProducerFailure("IMPLEMENTATION_INVALID", "synthetic panel shape/dtype/order mismatch")
    raw = memoryview(matrix).cast("B")
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    if len(raw) != 4_194_304 or raw_sha256 != RAW_INPUT_SHA256:
        raise ProducerFailure("ARTIFACT_INVALID", "synthetic panel identity mismatch")
    selection_digests = [
        hashlib.sha256(
            f"{SCIENTIFIC_HASH_DOMAIN}|{DATASET_ID}|0|{vector_id}".encode("utf-8")
        ).hexdigest()
        for vector_id in range(wire.ROWS)
    ]
    stream = json.dumps(selection_digests, separators=(",", ":")).encode("utf-8")
    selection_sha256 = hashlib.sha256(stream).hexdigest()
    if selection_sha256 != SELECTION_STREAM_SHA256:
        raise ProducerFailure("ARTIFACT_INVALID", "selection-digest stream mismatch")
    matrix.flags.writeable = False
    return matrix, InputIdentity(raw_sha256, len(raw), selection_sha256)


def _matrix_u32_bits(np: Any, matrix: Any) -> Any:
    view = matrix.view(np.uint32)
    if view.shape != matrix.shape or not view.flags.c_contiguous:
        raise ProducerFailure("IMPLEMENTATION_INVALID", "panel uint32 view mismatch")
    return view


def _write_scalar_input(path: Path, matrix_bits: Any, coordinate: int, hooks: ProducerHooks) -> None:
    payload = bytearray(b"A4SCL001")
    payload.extend(struct.pack("<I", 1))
    payload.extend(struct.pack("<III", coordinate, wire.ROWS, wire.MAX_K))
    for vector_id in range(wire.ROWS):
        payload.extend(
            struct.pack(
                "<IQQ",
                int(matrix_bits[vector_id, coordinate]),
                1,
                vector_id,
            )
        )
    _write_new(path, bytes(payload), hooks)


def _write_exact(output: bytearray, value: wire.ExactValue) -> None:
    numerator = value.numerator.encode("ascii")
    denominator = value.denominator.encode("ascii")
    output.extend(struct.pack("<iI", value.binary_grid_exponent, len(numerator)))
    output.extend(numerator)
    output.extend(struct.pack("<I", len(denominator)))
    output.extend(denominator)


def _append_allocation_curve(
    payload: bytearray,
    coordinate: wire.ScalarCoordinate,
    maximum_cardinality: int,
) -> None:
    payload.extend(struct.pack("<I", coordinate.coordinate_id))
    for solution in coordinate.solutions[:maximum_cardinality]:
        payload.extend(struct.pack("<I", solution.effective_cardinality))
        _write_exact(payload, solution.exact_sse)


def _write_allocation_item_input(
    path: Path,
    *,
    item_id: int,
    scalar: Sequence[wire.ScalarCoordinate],
    hooks: ProducerHooks,
) -> None:
    if len(scalar) != wire.DIMENSIONS:
        raise ProducerFailure("IMPLEMENTATION_INVALID", "allocation requires 128 scalar curves")
    payload = bytearray(b"A4ALI001")
    payload.extend(struct.pack("<I", 1))
    if item_id < 256:
        rate_index = item_id // 128
        within_rate = item_id % 128
        group_id = within_rate // 2
        cardinality_set = within_rate % 2
        capacity = 16 if rate_index == 0 else 256
        payload.extend(struct.pack("<IIIIII", 1, item_id, capacity, cardinality_set, 2, capacity))
        _append_allocation_curve(payload, scalar[2 * group_id], capacity)
        _append_allocation_curve(payload, scalar[2 * group_id + 1], capacity)
    elif item_id in {256, 257}:
        budget = 256 if item_id == 256 else 512
        payload.extend(struct.pack("<IIIII", 2, item_id, budget, wire.DIMENSIONS, wire.MAX_K))
        for coordinate in scalar:
            _append_allocation_curve(payload, coordinate, wire.MAX_K)
    else:
        raise ProducerFailure("IMPLEMENTATION_INVALID", "allocation item id outside [0,257]")
    payload.extend(b"A4AIEND1")
    _write_new(path, bytes(payload), hooks)


def _group_record(state: ProducerState, word_bits: int, group_id: int) -> GroupAllocationRecord:
    for record in state.group_allocations:
        if record.word_bits == word_bits and record.group_id == group_id:
            return record
    raise ProducerFailure("IMPLEMENTATION_INVALID", "missing group allocation")


def _global_record(state: ProducerState, word_bits: int) -> GlobalAllocationRecord:
    for record in state.global_allocations:
        if record.word_bits == word_bits:
            return record
    raise ProducerFailure("IMPLEMENTATION_INVALID", "missing global allocation")


def _block_record(state: ProducerState, word_bits: int, group_id: int) -> BlockRecord:
    for record in state.blocks:
        if record.unit.word_bits == word_bits and record.unit.group_id == group_id:
            return record
    raise ProducerFailure("IMPLEMENTATION_INVALID", "missing block record")


def _selected_scalar(
    state: ProducerState, coordinate_id: int, requested_cardinality: int
) -> wire.ScalarSolution:
    return state.scalar_coordinates[coordinate_id].solutions[requested_cardinality - 1]


def _solution_is_representable(solution: wire.ScalarSolution, requested: int) -> bool:
    """Apply the frozen collapse rule only to a selected scalar alphabet."""

    return (
        solution.requested_cardinality == requested
        and solution.effective_cardinality == requested
        and len(solution.clusters) == requested
        and solution.serialized_binary32_strictly_increasing
    )


def _product_is_representable(
    state: ProducerState,
    group_id: int,
    allocation: wire.ProductAllocationItem,
) -> bool:
    if not allocation.all_reachable:
        return False
    selected = tuple(
        _selected_scalar(state, 2 * group_id + offset, requested)
        for offset, requested in enumerate(allocation.requested_cardinalities)
    )
    return (
        allocation.effective_cardinalities
        == tuple(solution.effective_cardinality for solution in selected)
        and all(
            _solution_is_representable(solution, requested)
            for solution, requested in zip(selected, allocation.requested_cardinalities)
        )
    )


def _write_block_input(
    path: Path,
    *,
    np: Any,
    state: ProducerState,
    word_bits: int,
    group_id: int,
    hooks: ProducerHooks,
) -> None:
    matrix_bits = _matrix_u32_bits(np, state.matrix)
    allocation = _group_record(state, word_bits, group_id).arbitrary
    axis0 = _selected_scalar(state, 2 * group_id, allocation.requested_cardinalities[0])
    axis1 = _selected_scalar(state, 2 * group_id + 1, allocation.requested_cardinalities[1])
    dataset = DATASET_ID.encode("utf-8")
    payload = bytearray(b"A4BLK001")
    payload.extend(struct.pack("<I", 1))
    payload.extend(struct.pack("<IIII", group_id, 1 << word_bits, group_id, len(dataset)))
    payload.extend(dataset)
    payload.extend(struct.pack("<III", wire.ROWS, len(axis0.clusters), len(axis1.clusters)))
    for vector_id in range(wire.ROWS):
        payload.extend(
            struct.pack(
                "<IIQQ",
                int(matrix_bits[vector_id, 2 * group_id]),
                int(matrix_bits[vector_id, 2 * group_id + 1]),
                0,
                vector_id,
            )
        )
    for cluster in axis0.clusters:
        payload.extend(struct.pack("<Q", int(cluster.binary64_bits, 16)))
    for cluster in axis1.clusters:
        payload.extend(struct.pack("<Q", int(cluster.binary64_bits, 16)))
    _write_new(path, bytes(payload), hooks)


def _float32(bits: str) -> float:
    return float(struct.unpack("<f", struct.pack("<I", int(bits, 16)))[0])


def _float64(bits: str) -> float:
    return float(struct.unpack("<d", struct.pack("<Q", int(bits, 16)))[0])


def _float64_bits(value: float) -> str:
    return f"{struct.unpack('<Q', struct.pack('<d', value))[0]:016x}"


def _assign_points(
    points: Sequence[wire.BlockPoint],
    centers: Sequence[tuple[str, str]],
) -> tuple[bytes, str]:
    decoded = tuple((_float64(first), _float64(second)) for first, second in centers)
    if not decoded:
        raise ProducerFailure("IMPLEMENTATION_INVALID", "block replay has no centers")
    assignments = bytearray()
    total = 0.0
    for point in points:
        x0 = _float32(point.coordinate0_bits)
        x1 = _float32(point.coordinate1_bits)
        best_id = 0
        difference0 = x0 - decoded[0][0]
        square0 = difference0 * difference0
        difference1 = x1 - decoded[0][1]
        square1 = difference1 * difference1
        best = square0 + square1
        for center_id in range(1, len(decoded)):
            difference0 = x0 - decoded[center_id][0]
            square0 = difference0 * difference0
            difference1 = x1 - decoded[center_id][1]
            square1 = difference1 * difference1
            distance = square0 + square1
            if distance < best:
                best = distance
                best_id = center_id
        if not math.isfinite(best):
            raise ProducerFailure("IMPLEMENTATION_INVALID", "nonfinite block replay distance")
        assignments.extend(struct.pack("<H", best_id))
        total += best
        if not math.isfinite(total):
            raise ProducerFailure("IMPLEMENTATION_INVALID", "nonfinite block replay SSE")
    return bytes(assignments), _float64_bits(total)


def _inspect_block_unit(
    unit: wire.BlockUnit,
) -> tuple[
    tuple[BlockStartRecord, ...],
    tuple[tuple[str, str], ...],
    str | None,
]:
    cartesian_sse = _float64(unit.cartesian_sse_bits)
    records: list[BlockStartRecord] = []
    for start in unit.starts:
        before_centers = start.initial_centers_binary64_bits
        direct = True
        for step in start.steps:
            before, before_sse = _assign_points(unit.ordered_points, before_centers)
            after, after_sse = _assign_points(unit.ordered_points, step.centers_after_binary64_bits)
            direct = (
                direct
                and before == step.assignments_before_le_u16
                and after == step.assignments_after_le_u16
                and before_sse == step.prior_sse_bits
                and after_sse == step.candidate_sse_bits
            )
            before_centers = step.centers_after_binary64_bits
        replayable_final = (
            len(start.final_centers_binary64_bits) == unit.capacity
            and len(start.final_assignments_le_u16) == 2 * wire.ROWS
            and start.final_sse_bits != "7ff0000000000000"
        )
        if replayable_final:
            final, final_sse = _assign_points(
                unit.ordered_points, start.final_centers_binary64_bits
            )
            direct = (
                direct
                and final == start.final_assignments_le_u16
                and final_sse == start.final_sse_bits
            )
        elif start.failure != "NONFINITE_CONTROL":
            raise ProducerFailure(
                "IMPLEMENTATION_INVALID",
                "finite block trace omits its replayable final state",
            )
        records.append(
            BlockStartRecord(
                start,
                direct,
                _float64(start.final_sse_bits) <= cartesian_sse,
            )
        )
    if not all(record.direct_replay_match for record in records):
        raise ProducerFailure("IMPLEMENTATION_INVALID", "block producer direct replay mismatch")

    control_detail: str | None = None
    if not unit.control_valid:
        if unit.wire_control_failures:
            control_detail = "; ".join(unit.wire_control_failures)
        else:
            control_detail = (
                f"block B{unit.word_bits} group {unit.group_id} "
                f"{unit.failure}: {unit.failure_detail}"
            )
    selected_centers: tuple[tuple[str, str], ...] = ()
    if unit.selected_start_id is not None:
        selected = unit.starts[unit.selected_start_id]
        selected_centers = selected.final_centers_binary32_bits
        if (
            not records[0].cartesian_dominance_pass
            or not records[unit.selected_start_id].cartesian_dominance_pass
        ):
            control_detail = control_detail or "block Cartesian-dominance control failed"
        if selected.distinct_serialized_center_count != unit.capacity:
            control_detail = control_detail or "selected block codebook collapses in binary32"
    elif unit.control_valid:
        raise ProducerFailure(
            "IMPLEMENTATION_INVALID", "valid block trace omits its selected start"
        )
    return tuple(records), selected_centers, control_detail


def _write_u32_sequence(output: bytearray, values: Sequence[int]) -> None:
    for value in values:
        output.extend(struct.pack("<I", int(value)))


def _write_encoding_input(
    path: Path,
    *,
    np: Any,
    state: ProducerState,
    word_bits: int,
    arm_id: int,
    hooks: ProducerHooks,
) -> None:
    matrix_bits = _matrix_u32_bits(np, state.matrix)
    payload = bytearray(b"A4ENC002")
    payload.extend(
        struct.pack(
            "<IIIIIIQ",
            2,
            arm_id,
            word_bits,
            wire.ROWS,
            wire.DIMENSIONS,
            wire.GROUPS,
            wire.ROWS * wire.DIMENSIONS,
        )
    )
    payload.extend(memoryview(matrix_bits).cast("B"))
    payload.extend(struct.pack("<I", arm_id))
    if arm_id in {0, 1}:
        for group_id in range(wire.GROUPS):
            group = _group_record(state, word_bits, group_id)
            selected = group.dyadic if arm_id == 0 else group.arbitrary
            first = _selected_scalar(state, 2 * group_id, selected.requested_cardinalities[0])
            second = _selected_scalar(state, 2 * group_id + 1, selected.requested_cardinalities[1])
            payload.extend(
                struct.pack(
                    "<III",
                    group_id,
                    selected.requested_cardinalities[0],
                    selected.requested_cardinalities[1],
                )
            )
            _write_u32_sequence(payload, tuple(int(cluster.binary32_bits, 16) for cluster in first.clusters))
            _write_u32_sequence(payload, tuple(int(cluster.binary32_bits, 16) for cluster in second.clusters))
    elif arm_id == 2:
        for group_id in range(wire.GROUPS):
            block = _block_record(state, word_bits, group_id)
            payload.extend(struct.pack("<II", group_id, block.unit.capacity))
            for first, second in block.selected_centers_binary32_bits:
                payload.extend(struct.pack("<II", int(first, 16), int(second, 16)))
    elif arm_id == 3:
        allocation = _global_record(state, word_bits).allocation
        for coordinate, width in enumerate(allocation.bit_widths):
            solution = _selected_scalar(state, coordinate, 1 << width)
            payload.extend(struct.pack("<III", coordinate, width, len(solution.clusters)))
            _write_u32_sequence(payload, tuple(int(cluster.binary32_bits, 16) for cluster in solution.clusters))
    else:
        raise ProducerFailure("IMPLEMENTATION_INVALID", "encoding arm id outside [0,3]")
    payload.extend(b"A4EIEND2")
    payload.extend(struct.pack("<II", wire.ROWS, arm_id))
    _write_new(path, bytes(payload), hooks)


def _encoding_record(state: ProducerState, arm: str, unit: wire.EncodingUnit) -> EncodingRecord:
    expected_labels = wire.DIMENSIONS if arm == "global_dyadic_pack_cap8" else wire.GROUPS
    expected_label_bytes = wire.ROWS * expected_labels * 2
    expected_payload_bytes = wire.ROWS * (32 if unit.word_bits == 4 else 64)
    if (
        unit.row_count != wire.ROWS
        or unit.labels_per_row != expected_labels
        or len(unit.labels_le_u16) != expected_label_bytes
        or len(unit.roundtrip_labels_le_u16) != expected_label_bytes
        or len(unit.payload) != expected_payload_bytes
    ):
        raise ProducerFailure("IMPLEMENTATION_INVALID", "encoding compact-state shape mismatch")
    label_domain_valid = True
    if arm == "global_dyadic_pack_cap8":
        widths = _global_record(state, unit.word_bits).allocation.bit_widths
        for flat_index, (label,) in enumerate(struct.iter_unpack("<H", unit.labels_le_u16)):
            if label >= (1 << widths[flat_index % wire.DIMENSIONS]):
                label_domain_valid = False
                break
    else:
        label_maximum = 1 << unit.word_bits
        label_domain_valid = all(
            label < label_maximum
            for (label,) in struct.iter_unpack("<H", unit.labels_le_u16)
        )
    return EncodingRecord(arm, unit, label_domain_valid)


def _exact_object(value: wire.ExactValue) -> dict[str, Any]:
    return {
        "binary_grid_exponent": value.binary_grid_exponent,
        "denominator": value.denominator,
        "numerator": value.numerator,
    }


def _product_model(state: ProducerState, coordinate0: int, allocation: wire.ProductAllocationItem) -> dict[str, Any]:
    first = _selected_scalar(state, coordinate0, allocation.requested_cardinalities[0])
    second = _selected_scalar(state, coordinate0 + 1, allocation.requested_cardinalities[1])
    return {
        "centroids_binary32_bits": [
            [cluster.binary32_bits for cluster in first.clusters],
            [cluster.binary32_bits for cluster in second.clusters],
        ],
        "effective_cardinalities": list(allocation.effective_cardinalities),
        "invalid_states": allocation.capacity - allocation.used_states,
        "requested_cardinalities": list(allocation.requested_cardinalities),
        "used_states": allocation.used_states,
    }


def _bundle_models(state: ProducerState) -> dict[str, Any]:
    rates: list[dict[str, Any]] = []
    for word_bits in (4, 8):
        groups: list[dict[str, Any]] = []
        for group_id in range(wire.GROUPS):
            allocation = _group_record(state, word_bits, group_id)
            block = _block_record(state, word_bits, group_id)
            groups.append(
                {
                    "arbitrary_word": _product_model(state, 2 * group_id, allocation.arbitrary),
                    "coordinates": [2 * group_id, 2 * group_id + 1],
                    "dyadic_word": _product_model(state, 2 * group_id, allocation.dyadic),
                    "group_id": group_id,
                    "trained_block_vq": {
                        "center_count": 1 << word_bits,
                        "centers_binary32_bits": [list(center) for center in block.selected_centers_binary32_bits],
                        "selected_start_id": block.unit.selected_start_id,
                    },
                }
            )
        global_allocation = _global_record(state, word_bits).allocation
        global_centroids = []
        for coordinate, width in enumerate(global_allocation.bit_widths):
            solution = _selected_scalar(state, coordinate, 1 << width)
            global_centroids.append([cluster.binary32_bits for cluster in solution.clusters])
        rates.append(
            {
                "capacity": 1 << word_bits,
                "global_dyadic_pack_cap8": {
                    "bit_widths": list(global_allocation.bit_widths),
                    "cardinalities": [1 << width for width in global_allocation.bit_widths],
                    "centroids_binary32_bits": global_centroids,
                },
                "groups": groups,
                "payload_bytes": 32 if word_bits == 4 else 64,
                "word_bits": word_bits,
            }
        )
    return {
        "artifact_kind": "a4_comparative_models",
        "protocol_version": PROTOCOL_VERSION,
        "rates": rates,
        "schema_version": 1,
    }


def _encoding_for(state: ProducerState, word_bits: int, arm: str) -> EncodingRecord:
    for record in state.encodings:
        if record.unit.word_bits == word_bits and record.arm == arm:
            return record
    raise ProducerFailure("IMPLEMENTATION_INVALID", "missing encoding arm")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_bundle(state: ProducerState, output_root: Path, hooks: ProducerHooks) -> BundleIdentity:
    if len(state.encodings) != 8:
        raise ProducerFailure("IMPLEMENTATION_INVALID", "bundle requires all eight encoding units")
    staging = output_root / "bundle.staging"
    destination = output_root / "bundle"
    parent_fd = os.open(
        output_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.mkdir("bundle.staging", 0o700, dir_fd=parent_fd)
    except OSError as error:
        os.close(parent_fd)
        raise ProducerFailure("ARTIFACT_INVALID", f"cannot create bundle staging: {error}") from error
    hooks.note_created_temporary(staging)
    staging_fd: int | None = None
    identities: list[BundleFileIdentity] = []
    reserved_bytes: int | None = None
    published = False
    try:
        staging_fd = os.open(
            "bundle.staging",
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        hooks.switch("C_bundle_io", "C_common_manifest")
        models_bytes = _canonical_json_body(_bundle_models(state))
        models_path = staging / "models.json"
        _write_new_at(staging_fd, "models.json", models_path, models_bytes, hooks)
        identities.append(BundleFileIdentity("models.json", len(models_bytes), hashlib.sha256(models_bytes).hexdigest()))

        code_identities: list[dict[str, Any]] = []
        for word_bits in (4, 8):
            code_path = staging / f"codes_b{word_bits:02d}.bin"
            expected_size = 1_048_576 if word_bits == 4 else 2_097_152
            try:
                descriptor = os.open(
                    code_path.name,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                    dir_fd=staging_fd,
                )
                with os.fdopen(descriptor, "wb", buffering=0) as output:
                    digest = hashlib.sha256()
                    total = 0
                    for arm in ARM_ORDER:
                        hooks.switch("C_bundle_io", ARM_OWNER[arm])
                        payload = _encoding_for(state, word_bits, arm).payload
                        written = output.write(payload)
                        if written != len(payload):
                            raise OSError("short code-file write")
                        digest.update(payload)
                        total += len(payload)
                    os.fsync(output.fileno())
            except OSError as error:
                raise ProducerFailure("ARTIFACT_INVALID", f"cannot write {code_path}: {error}") from error
            hooks.note_created_temporary(code_path)
            if total != expected_size:
                raise ProducerFailure("IMPLEMENTATION_INVALID", "code-file size mismatch")
            identity = BundleFileIdentity(code_path.name, total, digest.hexdigest())
            identities.append(identity)
            code_identities.append(
                {
                    "arm_order": list(ARM_ORDER),
                    "layout": "arm-major_then_vector-major",
                    "path": code_path.name,
                    "payload_bytes": 32 if word_bits == 4 else 64,
                    "sha256": identity.sha256,
                    "size_bytes": identity.size_bytes,
                    "vector_count": wire.ROWS,
                    "word_bits": word_bits,
                }
            )

        hooks.switch("C_bundle_io", "C_common_manifest")
        manifest = {
            "arm_order": list(ARM_ORDER),
            "artifact_kind": "a4_comparative_bundle_manifest",
            "code_files": code_identities,
            "input": {
                "dtype": "little-endian binary32",
                "order": "C",
                "raw_sha256": state.input_identity.raw_sha256 if state.input_identity else "",
                "shape": [wire.ROWS, wire.DIMENSIONS],
            },
            "models": {
                "path": "models.json",
                "schema_version": 1,
                "sha256": identities[0].sha256,
                "size_bytes": identities[0].size_bytes,
            },
            "protocol_version": PROTOCOL_VERSION,
            "schema_version": 1,
        }
        manifest_bytes = _canonical_json_body(manifest)
        manifest_path = staging / "representation_manifest.json"
        _write_new_at(
            staging_fd,
            "representation_manifest.json",
            manifest_path,
            manifest_bytes,
            hooks,
        )
        identities.append(
            BundleFileIdentity(
                "representation_manifest.json",
                len(manifest_bytes),
                hashlib.sha256(manifest_bytes).hexdigest(),
            )
        )
        hooks.check_operational()
        total_bytes = sum(item.size_bytes for item in identities)
        bundle_identity = BundleIdentity("bundle", tuple(identities), total_bytes)
        hooks.reserve_permanent_bundle(total_bytes)
        reserved_bytes = total_bytes
        os.fsync(staging_fd)
        _rename_noreplace(parent_fd, "bundle.staging", "bundle")
        published = True
        hooks.mark_bundle_publication_visible()
        os.fsync(parent_fd)
        hooks.commit_permanent_bundle(total_bytes)
    except BaseException as error:
        if reserved_bytes is not None and not published:
            hooks.cancel_permanent_bundle(reserved_bytes)
        if published:
            if isinstance(error, BundlePublicationVisibleFailure):
                raise
            raise BundlePublicationVisibleFailure(
                "bundle target became physically visible before admissible U395: "
                f"{type(error).__name__}"
            ) from error
        # A staging directory is never evidence.  Deletion accounting is
        # performed by the supervisor during attempt cleanup.
        raise
    finally:
        close_error: BaseException | None = None
        if staging_fd is not None:
            try:
                os.close(staging_fd)
            except BaseException as error:
                close_error = error
        try:
            os.close(parent_fd)
        except BaseException as error:
            if close_error is None:
                close_error = error
        if close_error is not None:
            if published:
                raise BundlePublicationVisibleFailure(
                    "bundle target became physically visible before descriptor cleanup: "
                    f"{type(close_error).__name__}"
                ) from close_error
            raise close_error
    return bundle_identity


def _stop_after(hooks: ProducerHooks, state: ProducerState) -> bool:
    return hooks.complete_unit(state.last_completed_unit_index, state)


def run_attempt(hooks: ProducerHooks, output_root: Path) -> ProducerState:
    """Run one attempt from U000; return the complete or cap-stopped prefix."""

    hooks.switch("C_setup", "C_setup")
    try:
        import numpy as np  # type: ignore[import-not-found]
    except ImportError as error:
        raise ProducerFailure("IMPLEMENTATION_INVALID", "NumPy is unavailable") from error
    if np.__version__ != "1.23.5":
        raise ProducerFailure("IMPLEMENTATION_INVALID", "NumPy version mismatch")
    matrix, input_identity = _generate_panel(np)
    state = ProducerState(matrix=matrix, input_identity=input_identity).complete(0)
    if _stop_after(hooks, state):
        return state

    matrix_bits = _matrix_u32_bits(np, matrix)
    for coordinate in range(wire.DIMENSIONS):
        hooks.switch("C_core", "C_shared_fit")
        stem = f"scalar_{coordinate:03d}"
        input_path = hooks.attempt_root / f"{stem}.input"
        output_path = hooks.attempt_root / f"{stem}.output"
        _write_scalar_input(input_path, matrix_bits, coordinate, hooks)
        hooks.invoke_native(("scalar-suite", str(input_path), str(output_path)))
        parsed = wire.parse_scalar_suite(output_path, coordinate)
        _delete_temporary(input_path, hooks)
        _delete_temporary(output_path, hooks)
        state = state.complete(
            1 + coordinate,
            scalar_coordinates=(*state.scalar_coordinates, parsed),
        )
        if _stop_after(hooks, state):
            return state

    allocation_unit = 129
    for word_bits in (4, 8):
        rate_index = 0 if word_bits == 4 else 1
        for group_id in range(wire.GROUPS):
            parsed_by_kind: dict[bool, wire.ProductAllocationItem] = {}
            for dyadic in (False, True):
                hooks.switch("C_core", "C_arm_dyadic" if dyadic else "C_arm_arbitrary")
                item_id = ((rate_index * wire.GROUPS + group_id) * 2) + (1 if dyadic else 0)
                stem = f"allocation_{item_id:03d}"
                input_path = hooks.attempt_root / f"{stem}.input"
                output_path = hooks.attempt_root / f"{stem}.output"
                _write_allocation_item_input(
                    input_path,
                    item_id=item_id,
                    scalar=state.scalar_coordinates,
                    hooks=hooks,
                )
                hooks.invoke_native(("allocation-item", str(input_path), str(output_path)))
                parsed = wire.parse_allocation_item(output_path, item_id)
                if not isinstance(parsed, wire.ProductAllocationItem) or parsed.dyadic != dyadic:
                    raise ProducerFailure("IMPLEMENTATION_INVALID", "allocation item kind mismatch")
                parsed_by_kind[dyadic] = parsed
                _delete_temporary(input_path, hooks)
                _delete_temporary(output_path, hooks)
            state = state.complete(
                allocation_unit,
                group_allocations=(
                    *state.group_allocations,
                    GroupAllocationRecord(
                        word_bits,
                        group_id,
                        parsed_by_kind[True],
                        parsed_by_kind[False],
                    ),
                ),
                representation_valid=(
                    state.representation_valid
                    and _product_is_representable(state, group_id, parsed_by_kind[True])
                    and _product_is_representable(state, group_id, parsed_by_kind[False])
                ),
            )
            allocation_unit += 1
            if _stop_after(hooks, state):
                return state

    for word_bits, item_id in ((4, 256), (8, 257)):
        hooks.switch("C_core", "C_arm_global")
        stem = f"allocation_{item_id:03d}"
        input_path = hooks.attempt_root / f"{stem}.input"
        output_path = hooks.attempt_root / f"{stem}.output"
        _write_allocation_item_input(
            input_path,
            item_id=item_id,
            scalar=state.scalar_coordinates,
            hooks=hooks,
        )
        hooks.invoke_native(("allocation-item", str(input_path), str(output_path)))
        parsed = wire.parse_allocation_item(output_path, item_id)
        if not isinstance(parsed, wire.GlobalAllocationItem):
            raise ProducerFailure("IMPLEMENTATION_INVALID", "global allocation kind mismatch")
        _delete_temporary(input_path, hooks)
        _delete_temporary(output_path, hooks)
        state = state.complete(
            257 if word_bits == 4 else 258,
            global_allocations=(*state.global_allocations, GlobalAllocationRecord(word_bits, parsed)),
            representation_valid=(
                state.representation_valid
                and all(
                    _solution_is_representable(
                        _selected_scalar(state, coordinate, 1 << width),
                        1 << width,
                    )
                    for coordinate, width in enumerate(parsed.bit_widths)
                )
            ),
        )
        if _stop_after(hooks, state):
            return state

    block_unit = 259
    for word_bits in (4, 8):
        for group_id in range(wire.GROUPS):
            hooks.switch("C_core", "C_arm_block")
            stem = f"block_b{word_bits:02d}_{group_id:03d}"
            input_path = hooks.attempt_root / f"{stem}.input"
            output_path = hooks.attempt_root / f"{stem}.output"
            _write_block_input(
                input_path,
                np=np,
                state=state,
                word_bits=word_bits,
                group_id=group_id,
                hooks=hooks,
            )
            hooks.invoke_native(("block-suite", str(input_path), str(output_path)))
            allocation = _group_record(state, word_bits, group_id).arbitrary
            axis0 = _selected_scalar(
                state, 2 * group_id, allocation.requested_cardinalities[0]
            )
            axis1 = _selected_scalar(
                state, 2 * group_id + 1, allocation.requested_cardinalities[1]
            )
            try:
                parsed = wire.parse_block_suite(
                    output_path,
                    word_bits=word_bits,
                    group_id=group_id,
                    expected_axis0_bits=tuple(
                        cluster.binary64_bits for cluster in axis0.clusters
                    ),
                    expected_axis1_bits=tuple(
                        cluster.binary64_bits for cluster in axis1.clusters
                    ),
                )
            except wire.WireControlError as error:
                if not isinstance(error.block_unit, wire.BlockUnit):
                    raise ProducerFailure(
                        "IMPLEMENTATION_INVALID",
                        "complete block wire control omitted its parsed unit",
                    ) from error
                parsed = error.block_unit
            records, selected_centers, control_detail = _inspect_block_unit(parsed)
            _delete_temporary(input_path, hooks)
            _delete_temporary(output_path, hooks)
            if control_detail is not None:
                return hooks.fail_unpublished_unit("CONTROL_INVALID", control_detail)
            record = BlockRecord(parsed, records, selected_centers)
            state = state.complete(
                block_unit,
                blocks=(*state.blocks, record),
            )
            block_unit += 1
            if _stop_after(hooks, state):
                return state

    encoding_unit = 387
    for word_bits in (4, 8):
        for arm_id, arm in enumerate(ARM_ORDER):
            hooks.switch("C_core", ARM_OWNER[arm])
            stem = f"encoding_b{word_bits:02d}_{arm_id}"
            input_path = hooks.attempt_root / f"{stem}.input"
            output_path = hooks.attempt_root / f"{stem}.output"
            _write_encoding_input(
                input_path,
                np=np,
                state=state,
                word_bits=word_bits,
                arm_id=arm_id,
                hooks=hooks,
            )
            hooks.invoke_native(("encoding-suite", str(input_path), str(output_path)))
            parsed = wire.parse_encoding_suite(output_path, expected_arm_id=arm_id, word_bits=word_bits)
            record = _encoding_record(state, arm, parsed)
            _delete_temporary(input_path, hooks)
            _delete_temporary(output_path, hooks)
            state = state.complete(
                encoding_unit,
                encodings=(*state.encodings, record),
                control_valid=state.control_valid and record.control_valid,
            )
            encoding_unit += 1
            stop_after_unit = _stop_after(hooks, state)
            if not record.control_valid:
                detail = (
                    "encoding label exceeds the frozen selected codebook"
                    if not record.label_domain_valid
                    else "encoding packing/round-trip control mismatch"
                )
                raise ProducerFailure("CONTROL_INVALID", detail)
            if stop_after_unit:
                return state

    hooks.switch("C_bundle_io", "C_common_manifest")
    bundle = publish_bundle(state, output_root, hooks)
    state = state.complete(395, bundle=bundle)
    _stop_after(hooks, state)
    return state


def discard_attempt_root(path: Path) -> None:
    """Delete an unpublished attempt staging tree; never touches bundle/."""

    if path.name in {"bundle", "evidence", "verifier", "archive", "final"}:
        raise ProducerFailure("ARTIFACT_INVALID", "refusing to delete published directory")
    try:
        if path.exists():
            shutil.rmtree(path)
    except OSError as error:
        raise ProducerFailure("ARTIFACT_INVALID", f"cannot discard attempt staging: {error}") from error
