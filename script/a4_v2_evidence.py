#!/usr/bin/env python3
"""Canonical A4 V2 producer evidence and finite-trailer writers.

This module is deliberately downstream of the immutable producer state.  It
contains encoders, byte commitments, and atomic directory publication only;
it performs no fitting, allocation, rounding, assignment, packing, replay, or
payload regeneration.  The independent verifier and archive implementation
must use their own parsers and canonical logical-record encoders.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import ctypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, NoReturn, Protocol, Sequence

import a4_v2_producer as producer


PROTOCOL_VERSION = producer.PROTOCOL_VERSION
EVIDENCE_ORDER = (
    "scalar_optimum_records.jsonl",
    "allocation_summary.json",
    "block_trajectories.jsonl",
    "encoding_summary.json",
    "producer_manifest.json",
)
FINAL_ORDER = ("resource_ledger.json", "decision.json", "artifact_index.json")
FINAL_LIMITS = {
    "resource_ledger.json": 1_048_576,
    "decision.json": 65_536,
    "artifact_index.json": 2_097_152,
}
EVIDENCE_ARCHIVE_LIMIT = 4_294_967_296
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPOSITORY_ROOT / "docs/saq_a4_v2_artifact_schema_2026_07_14.json"
_LIBC = ctypes.CDLL(None, use_errno=True)
_RENAMEAT2 = _LIBC.renameat2
_RENAMEAT2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
_RENAMEAT2.restype = ctypes.c_int
_RENAME_NOREPLACE = 1


class EvidenceFailure(RuntimeError):
    def __init__(self, status: str, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class EvidenceHooks(Protocol):
    def note_created_temporary(self, path: Path) -> None: ...

    def note_research_evidence(self, byte_count: int) -> None: ...

    def check_operational(self) -> None: ...


@dataclass(frozen=True)
class FileIdentity:
    path: str
    producing_phase: str
    role: str
    schema: str
    sha256: str
    size_bytes: int

    def object(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "producing_phase": self.producing_phase,
            "role": self.role,
            "schema": self.schema,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class ProducerManifestContext:
    binary_identity: Mapping[str, Any]
    command_identity: Mapping[str, Any]
    emit_start_checkpoint: Mapping[str, Any]
    environment_identity: Mapping[str, Any]
    phase_receipts_through_instrument: Sequence[Mapping[str, Any]]
    prelaunch_observation: Mapping[str, Any]
    protocol_identity: Mapping[str, Any]
    schema_identity: Mapping[str, Any]
    source_identity: Mapping[str, Any]


@dataclass(frozen=True)
class EvidencePublication:
    directory: str
    files: tuple[FileIdentity, ...]
    total_bytes: int


def canonical_body(value: Any) -> bytes:
    """Return the frozen canonical JSON preimage without terminal LF."""

    def validate(item: Any) -> None:
        if isinstance(item, float):
            raise EvidenceFailure("IMPLEMENTATION_INVALID", "floating evidence JSON value")
        if isinstance(item, Mapping):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise EvidenceFailure("IMPLEMENTATION_INVALID", "non-string evidence key")
                validate(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                validate(child)
        elif not isinstance(item, (str, int, bool, type(None))):
            raise EvidenceFailure(
                "IMPLEMENTATION_INVALID", f"unsupported evidence value {type(item).__name__}"
            )

    validate(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise EvidenceFailure("IMPLEMENTATION_INVALID", f"canonical JSON failure: {error}") from error


def canonical_document(value: Any) -> bytes:
    return canonical_body(value) + b"\n"


class _SchemaMismatch(RuntimeError):
    pass


def _same_json_value(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_json_value(first, second) for first, second in zip(left, right)
        )
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _same_json_value(left[key], right[key]) for key in left
        )
    return bool(left == right)


class _FrozenSchema:
    """Producer-local Draft-2020-12 subset used by the normative registry."""

    def __init__(self, root: Mapping[str, Any]):
        self.root = root

    def definition(self, name: str) -> Mapping[str, Any]:
        definitions = self.root.get("$defs")
        if not isinstance(definitions, dict) or not isinstance(definitions.get(name), dict):
            raise _SchemaMismatch(f"missing schema definition {name}")
        return definitions[name]

    def resolve(self, reference: str) -> Any:
        if not reference.startswith("#/"):
            raise _SchemaMismatch(f"nonlocal schema reference {reference}")
        current: Any = self.root
        for raw in reference[2:].split("/"):
            key = raw.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, dict) or key not in current:
                raise _SchemaMismatch(f"unresolved schema reference {reference}")
            current = current[key]
        return current

    def validate_definition(self, value: Any, name: str, location: str) -> None:
        self.validate(value, self.definition(name), location)

    def validate(self, value: Any, schema: Any, location: str) -> None:
        if schema is True:
            return
        if schema is False or not isinstance(schema, dict):
            raise _SchemaMismatch(f"{location} is forbidden by schema")
        if "$ref" in schema:
            self.validate(value, self.resolve(schema["$ref"]), location)
        for child in schema.get("allOf", []):
            self.validate(value, child, location)
        if "oneOf" in schema:
            matches = 0
            for child in schema["oneOf"]:
                try:
                    self.validate(value, child, location)
                except _SchemaMismatch:
                    continue
                matches += 1
            if matches != 1:
                raise _SchemaMismatch(f"{location} matches {matches} oneOf branches")
        if "if" in schema:
            try:
                self.validate(value, schema["if"], location)
                condition = True
            except _SchemaMismatch:
                condition = False
            branch = schema.get("then" if condition else "else")
            if branch is not None:
                self.validate(value, branch, location)
        if "const" in schema and not _same_json_value(value, schema["const"]):
            raise _SchemaMismatch(f"{location} differs from schema const")
        if "enum" in schema and not any(
            _same_json_value(value, candidate) for candidate in schema["enum"]
        ):
            raise _SchemaMismatch(f"{location} is outside schema enum")
        expected_type = schema.get("type")
        if expected_type is not None:
            checks = {
                "null": value is None,
                "boolean": isinstance(value, bool),
                "integer": isinstance(value, int) and not isinstance(value, bool),
                "string": isinstance(value, str),
                "array": isinstance(value, list),
                "object": isinstance(value, dict),
            }
            if expected_type not in checks or not checks[expected_type]:
                raise _SchemaMismatch(f"{location} is not {expected_type}")
        if isinstance(value, int) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                raise _SchemaMismatch(f"{location} is below minimum")
            if "maximum" in schema and value > schema["maximum"]:
                raise _SchemaMismatch(f"{location} is above maximum")
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                raise _SchemaMismatch(f"{location} is too short")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                raise _SchemaMismatch(f"{location} is too long")
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                raise _SchemaMismatch(f"{location} does not match pattern")
            if schema.get("format") == "date-time" and re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                r"\.[0-9]{6}Z",
                value,
            ) is None:
                raise _SchemaMismatch(f"{location} is not frozen UTC")
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                raise _SchemaMismatch(f"{location} has too few items")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                raise _SchemaMismatch(f"{location} has too many items")
            if schema.get("uniqueItems"):
                encoded = [canonical_body(item) for item in value]
                if len(encoded) != len(set(encoded)):
                    raise _SchemaMismatch(f"{location} has duplicate items")
            prefix = schema.get("prefixItems", [])
            for index, child in enumerate(prefix[: len(value)]):
                self.validate(value[index], child, f"{location}[{index}]")
            if "items" in schema:
                for index in range(len(prefix), len(value)):
                    self.validate(value[index], schema["items"], f"{location}[{index}]")
            if "contains" in schema:
                matches = 0
                for index, item in enumerate(value):
                    try:
                        self.validate(item, schema["contains"], f"{location}[{index}]")
                    except _SchemaMismatch:
                        continue
                    matches += 1
                if matches < schema.get("minContains", 1) or (
                    "maxContains" in schema and matches > schema["maxContains"]
                ):
                    raise _SchemaMismatch(f"{location} has wrong contains count")
        if isinstance(value, dict):
            missing = [key for key in schema.get("required", []) if key not in value]
            if missing:
                raise _SchemaMismatch(f"{location} is missing {missing}")
            properties = schema.get("properties", {})
            for key, child in value.items():
                if key in properties:
                    self.validate(child, properties[key], f"{location}.{key}")
                elif schema.get("additionalProperties") is False:
                    raise _SchemaMismatch(f"{location} has forbidden key {key}")
                elif isinstance(schema.get("additionalProperties"), dict):
                    self.validate(
                        child,
                        schema["additionalProperties"],
                        f"{location}.{key}",
                    )


def _load_schema(expected_identity: Mapping[str, Any] | None = None) -> _FrozenSchema:
    try:
        payload = SCHEMA_PATH.read_bytes()
        if expected_identity is not None and (
            expected_identity.get("path")
            != "docs/saq_a4_v2_artifact_schema_2026_07_14.json"
            or expected_identity.get("sha256") != _sha256(payload)
            or expected_identity.get("size_bytes") != len(payload)
        ):
            raise EvidenceFailure(
                "IMPLEMENTATION_INVALID", "evidence schema identity differs from sealed context"
            )
        value = json.loads(payload.decode("utf-8", errors="strict"))
        if not isinstance(value, dict):
            raise ValueError("schema root is not an object")
        return _FrozenSchema(value)
    except EvidenceFailure:
        raise
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        raise EvidenceFailure(
            "IMPLEMENTATION_INVALID", f"cannot load frozen artifact schema: {error}"
        ) from error


def _validate_or_fail(
    registry: _FrozenSchema, value: Any, definition: str, location: str
) -> None:
    try:
        registry.validate_definition(value, definition, location)
    except _SchemaMismatch as error:
        raise EvidenceFailure(
            "IMPLEMENTATION_INVALID", f"{location} fails frozen schema: {error}"
        ) from error


def _exact(value: Any) -> dict[str, Any]:
    return {
        "binary_grid_exponent": value.binary_grid_exponent,
        "denominator": value.denominator,
        "numerator": value.numerator,
    }


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _u16_preimage(values: Sequence[int]) -> bytes:
    payload = bytearray()
    for value in values:
        if not 0 <= int(value) <= 0xFFFF:
            raise EvidenceFailure("IMPLEMENTATION_INVALID", "assignment exceeds uint16")
        payload.extend(struct.pack("<H", int(value)))
    return bytes(payload)


def _u32_preimage(values: Sequence[int]) -> bytes:
    payload = bytearray()
    for value in values:
        if not 0 <= int(value) <= 0xFFFFFFFF:
            raise EvidenceFailure("IMPLEMENTATION_INVALID", "row id exceeds uint32")
        payload.extend(struct.pack("<I", int(value)))
    return bytes(payload)


def _scalar_lines(state: producer.ProducerState) -> tuple[bytes, int]:
    output = bytearray()
    count = 0
    for coordinate in state.scalar_coordinates:
        for solution in coordinate.solutions:
            record = {
                "binary32_centroid_bits": [item.binary32_bits for item in solution.clusters],
                "binary64_centroid_bits": [item.binary64_bits for item in solution.clusters],
                "comparison_count": str(solution.comparison_count),
                "coordinate_id": coordinate.coordinate_id,
                "distinct_support_size": coordinate.distinct_support_size,
                "effective_cardinality": solution.effective_cardinality,
                "exact_means": [_exact(item.mean) for item in solution.clusters],
                "exact_sse": _exact(solution.exact_sse),
                "exact_tie_count": str(solution.exact_tie_count),
                "fit_row_count": coordinate.fit_row_count,
                "partition": [
                    {
                        "support_begin": item.support_begin,
                        "support_end_exclusive": item.support_end_exclusive,
                    }
                    for item in solution.clusters
                ],
                "record_type": "scalar_optimum_v2",
                "requested_cardinality": solution.requested_cardinality,
                "serialized_binary32_strictly_increasing": (
                    solution.serialized_binary32_strictly_increasing
                ),
            }
            output.extend(canonical_document(record))
            count += 1
    return bytes(output), count


def _allocation_arm(value: Any) -> dict[str, Any]:
    return {
        "effective_cardinalities": list(value.effective_cardinalities),
        "enumerated_candidate_count": str(value.candidate_count),
        "exact_fitting_sse": _exact(value.exact_sse),
        "invalid_states": value.capacity - value.used_states,
        "requested_cardinalities": list(value.requested_cardinalities),
        "used_states": value.used_states,
    }


def _allocation_object(state: producer.ProducerState) -> dict[str, Any]:
    groups = []
    for record in state.group_allocations:
        groups.append(
            {
                "arbitrary_word": _allocation_arm(record.arbitrary),
                "capacity": 1 << record.word_bits,
                "coordinates": [2 * record.group_id, 2 * record.group_id + 1],
                "dyadic_word": _allocation_arm(record.dyadic),
                "group_id": record.group_id,
                "record_type": "group_allocation_v2",
                "word_bits": record.word_bits,
            }
        )
    globals_ = []
    for record in state.global_allocations:
        value = record.allocation
        globals_.append(
            {
                "bit_widths": list(value.bit_widths),
                "cardinalities": [1 << width for width in value.bit_widths],
                "enumerated_transition_count": str(value.transition_count),
                "exact_fitting_sse": _exact(value.exact_sse),
                "record_type": "global_allocation_v2",
                "total_bit_budget": value.bit_budget,
                "used_bits": value.used_bits,
                "word_bits": record.word_bits,
            }
        )
    return {
        "artifact_kind": "a4_allocation_summary",
        "global_records": globals_,
        "group_records": groups,
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": 1,
    }


def _block_lines(state: producer.ProducerState) -> tuple[bytes, int, int, int]:
    output = bytearray()
    metadata_count = 0
    start_count = 0
    step_count = 0
    for record in state.blocks:
        unit = record.unit
        allocation = next(
            (
                item.arbitrary
                for item in state.group_allocations
                if item.word_bits == unit.word_bits and item.group_id == unit.group_id
            ),
            None,
        )
        if allocation is None or unit.selected_start_id is None:
            raise EvidenceFailure("IMPLEMENTATION_INVALID", "block metadata dependency missing")
        row_ids = tuple(point.vector_id for point in unit.ordered_points)
        metadata = {
            "arbitrary_cardinalities": list(allocation.requested_cardinalities),
            "arbitrary_used_states": allocation.used_states,
            "capacity": unit.capacity,
            "coordinates": [2 * unit.group_id, 2 * unit.group_id + 1],
            "fit_row_count": len(unit.ordered_points),
            "group_id": unit.group_id,
            "record_type": "block_metadata_v2",
            "row_order_vector_ids_sha256": _sha256(_u32_preimage(row_ids)),
            "selected_start_id": unit.selected_start_id,
            "word_bits": unit.word_bits,
        }
        output.extend(canonical_document(metadata))
        metadata_count += 1
        for materialized in record.starts:
            start = materialized.start
            steps = []
            for step_record in materialized.steps:
                step = step_record.step
                steps.append(
                    {
                        "accepted": True,
                        "assignments_after_sha256": _sha256(
                            step_record.assignments_after_le_u16
                        ),
                        "assignments_before_sha256": _sha256(
                            step_record.assignments_before_le_u16
                        ),
                        "candidate_sse_bits": step.candidate_sse_bits,
                        "centers_after_binary64_bits_sha256": _sha256(
                            canonical_body([list(pair) for pair in step.centers_after_binary64_bits])
                        ),
                        "changed_assignment_count": step.changed_assignment_count,
                        "empty_center_ids": list(step.empty_center_ids),
                        "iteration": step.iteration,
                        "prior_sse_bits": step.prior_sse_bits,
                    }
                )
            is_cartesian = start.start_id == 0
            prefill_centers = (
                [list(pair) for pair in unit.cartesian_centers_binary64_bits]
                if is_cartesian
                else None
            )
            start_object = {
                "accepted_update_count": len(steps),
                "assignment_tie_count": str(start.assignment_tie_count),
                "capacity": unit.capacity,
                "cartesian_dominance_pass": materialized.cartesian_dominance_pass,
                "converged": start.converged,
                "direct_replay_match": materialized.direct_replay_match,
                "distance_comparison_count": str(start.distance_comparison_count),
                "farthest_tie_count": str(start.farthest_tie_count),
                "final_assignments": list(start.final_assignments),
                "final_assignments_sha256": _sha256(_u16_preimage(start.final_assignments)),
                "final_centers_binary32_bits": [
                    list(pair) for pair in start.final_centers_binary32_bits
                ],
                "final_centers_binary64_bits": [
                    list(pair) for pair in start.final_centers_binary64_bits
                ],
                "final_sse_bits": start.final_sse_bits,
                "group_id": unit.group_id,
                "initial_centers_binary64_bits": [
                    list(pair) for pair in start.initial_centers_binary64_bits
                ],
                "initialization_kind": (
                    "cartesian_fill" if is_cartesian else "hashed_farthest_first"
                ),
                "initialization_vector_ids": list(start.initialization_vector_ids),
                "iteration_count": start.iteration_count,
                "prefill_cartesian_centers_binary64_bits": prefill_centers,
                "prefill_cartesian_centers_binary64_bits_sha256": (
                    _sha256(canonical_body(prefill_centers)) if prefill_centers is not None else None
                ),
                "prefill_cartesian_sse_bits": unit.cartesian_sse_bits if is_cartesian else None,
                "record_type": "block_start_v2",
                "selected_best_start": start.start_id == unit.selected_start_id,
                "serialized_distinct_center_count": start.distinct_serialized_center_count,
                "start_id": start.start_id,
                "steps": steps,
                "word_bits": unit.word_bits,
            }
            output.extend(canonical_document(start_object))
            start_count += 1
            step_count += len(steps)
    return bytes(output), metadata_count, start_count, step_count


def _encoding_object(state: producer.ProducerState) -> dict[str, Any]:
    records = []
    for record in state.encodings:
        unit = record.unit
        arm_index = producer.ARM_ORDER.index(record.arm)
        payload_bytes = 32 if unit.word_bits == 4 else 64
        byte_length = len(record.payload)
        records.append(
            {
                "alignment_bytes": 1,
                "arm": record.arm,
                "capacity": 1 << unit.word_bits,
                "code_file_path": f"codes_b{unit.word_bits:02d}.bin",
                "distance_comparison_count": str(unit.total_distance_comparisons),
                "file_byte_length": byte_length,
                "file_byte_offset": arm_index * producer.wire.ROWS * payload_bytes,
                "labels_per_vector": (
                    producer.wire.DIMENSIONS
                    if record.arm == "global_dyadic_pack_cap8"
                    else producer.wire.GROUPS
                ),
                "output_bytes": byte_length,
                "pack_operation_count": str(unit.total_pack_operations),
                "payload_bytes_per_vector": payload_bytes,
                "payload_hex": record.payload.hex(),
                "payload_sha256": _sha256(record.payload),
                "record_type": "encoding_arm_summary_v2",
                "roundtrip_match": record.roundtrip_match,
                "roundtrip_mismatch_count": record.roundtrip_mismatch_count,
                "roundtrip_vector_count": len(unit.rows),
                "unpack_operation_count": str(unit.total_unpack_operations),
                "vector_count": len(unit.rows),
                "word_bits": unit.word_bits,
            }
        )
    return {
        "artifact_kind": "a4_encoding_summary",
        "protocol_version": PROTOCOL_VERSION,
        "records": records,
        "schema_version": 1,
    }


def decision_counts(state: producer.ProducerState) -> dict[str, int]:
    return {
        "allocation_group_records": len(state.group_allocations),
        "allocation_global_records": len(state.global_allocations),
        "block_metadata_records": len(state.blocks),
        "block_start_records": sum(len(record.starts) for record in state.blocks),
        "block_step_records": sum(
            len(start.steps) for record in state.blocks for start in record.starts
        ),
        "bundle_files": len(state.bundle.files) if state.bundle is not None else 0,
        "encoding_arm_records": len(state.encodings),
        "scalar_optimum_records": sum(
            len(coordinate.solutions) for coordinate in state.scalar_coordinates
        ),
    }


def _input_identity(state: producer.ProducerState) -> dict[str, Any]:
    if state.input_identity is None:
        raise EvidenceFailure("IMPLEMENTATION_INVALID", "input identity is unavailable")
    value = {
        "cell_id": 0,
        "dataset_id": producer.DATASET_ID,
        "dtype": "little-endian binary32",
        "generator": "Generator(PCG64(20260713)).standard_normal((8192,128), dtype=float32)",
        "numpy": "1.23.5",
        "order": "C",
        "raw_bytes": state.input_identity.raw_bytes,
        "raw_sha256": state.input_identity.raw_sha256,
        "selection_digest_stream_sha256": state.input_identity.selection_digest_stream_sha256,
        "selection_hash_domain": producer.SCIENTIFIC_HASH_DOMAIN,
        "shape": [producer.wire.ROWS, producer.wire.DIMENSIONS],
        "vector_id_order": "0..8191 ascending",
    }
    value["input_identity_sha256"] = _sha256(canonical_body(value))
    return value


def _identity(
    name: str,
    payload: bytes,
    *,
    role: str,
    schema: str,
    phase: str = "E_emit",
) -> FileIdentity:
    return FileIdentity(
        f"evidence/{name}", phase, role, schema, _sha256(payload), len(payload)
    )


def _write_new(path: Path, payload: bytes, hooks: EvidenceHooks | None) -> None:
    try:
        with path.open("xb", buffering=0) as output:
            if output.write(payload) != len(payload):
                raise OSError("short write")
            os.fsync(output.fileno())
    except OSError as error:
        raise EvidenceFailure("EVIDENCE_INCOMPLETE_NO_DECISION", f"cannot write {path}: {error}") from error
    if hooks is not None:
        hooks.note_created_temporary(path)


def _write_new_at(
    directory_fd: int,
    name: str,
    path: Path,
    payload: bytes,
    hooks: EvidenceHooks | None,
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
        raise EvidenceFailure("EVIDENCE_INCOMPLETE_NO_DECISION", f"cannot write {path}: {error}") from error
    if hooks is not None:
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


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_evidence(
    state: producer.ProducerState,
    artifact_root: Path,
    context: ProducerManifestContext,
    hooks: EvidenceHooks,
) -> EvidencePublication:
    """Encode the exact completed prefix and atomically publish evidence/."""

    staging = artifact_root / "evidence.staging"
    destination = artifact_root / "evidence"
    parent_fd = os.open(
        artifact_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.mkdir("evidence.staging", 0o700, dir_fd=parent_fd)
    except OSError as error:
        os.close(parent_fd)
        raise EvidenceFailure("EVIDENCE_INCOMPLETE_NO_DECISION", f"cannot create evidence staging: {error}") from error
    hooks.note_created_temporary(staging)
    staging_fd: int | None = None
    try:
        staging_fd = os.open(
            "evidence.staging",
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        registry = _load_schema(context.schema_identity)
        scalar_bytes, _ = _scalar_lines(state)
        allocation_object = _allocation_object(state)
        allocation_bytes = canonical_document(allocation_object)
        block_bytes, _, _, _ = _block_lines(state)
        encoding_object = _encoding_object(state)
        encoding_bytes = canonical_document(encoding_object)
        payloads = (
            scalar_bytes,
            allocation_bytes,
            block_bytes,
            encoding_bytes,
        )
        specifications = (
            (
                "scalar_optimum_records.jsonl",
                "scalar_optimum_records",
                "scalar_optimum_v2-jsonl",
            ),
            ("allocation_summary.json", "allocation_summary", "allocation_summary_v2"),
            (
                "block_trajectories.jsonl",
                "block_trajectories",
                "block_metadata_v2-or-block_start_v2-jsonl",
            ),
            ("encoding_summary.json", "encoding_summary", "encoding_summary_v2"),
        )
        try:
            for index, line in enumerate(scalar_bytes.splitlines()):
                _validate_or_fail(
                    registry,
                    json.loads(line.decode("utf-8", errors="strict")),
                    "scalar_optimum_v2",
                    f"scalar record {index}",
                )
            _validate_or_fail(
                registry, allocation_object, "allocation_summary_v2", "allocation summary"
            )
            for index, line in enumerate(block_bytes.splitlines()):
                record = json.loads(line.decode("utf-8", errors="strict"))
                definition = (
                    "block_metadata_v2"
                    if record.get("record_type") == "block_metadata_v2"
                    else "block_start_v2"
                )
                _validate_or_fail(registry, record, definition, f"block record {index}")
            _validate_or_fail(
                registry, encoding_object, "encoding_summary_v2", "encoding summary"
            )
        except (UnicodeError, ValueError, json.JSONDecodeError) as error:
            raise EvidenceFailure(
                "IMPLEMENTATION_INVALID", f"generated evidence is not strict JSON: {error}"
            ) from error
        identities = [
            _identity(name, payload, role=role, schema=schema)
            for payload, (name, role, schema) in zip(payloads, specifications)
        ]

        manifest = {
            "artifact_kind": "a4_producer_manifest",
            "binary_identity": dict(context.binary_identity),
            "bundle_published": state.bundle is not None,
            "command_identity": dict(context.command_identity),
            "completed_unit_count": state.completed_unit_count,
            "emit_start_checkpoint": dict(context.emit_start_checkpoint),
            "environment_identity": dict(context.environment_identity),
            "evidence_files": [item.object() for item in identities],
            "full_shape_complete": state.full_shape_complete,
            "input_identity": _input_identity(state),
            "last_completed_unit_index": state.last_completed_unit_index,
            "phase_receipts_through_instrument": [
                dict(item) for item in context.phase_receipts_through_instrument
            ],
            "prelaunch_observation": dict(context.prelaunch_observation),
            "protocol_identity": dict(context.protocol_identity),
            "record_counts": decision_counts(state),
            "schema_identity": dict(context.schema_identity),
            "schema_version": 1,
            "source_identity": dict(context.source_identity),
        }
        _validate_or_fail(registry, manifest, "producer_manifest_v2", "producer manifest")
        manifest_bytes = canonical_document(manifest)
        for payload, (name, _, _) in zip(payloads, specifications):
            _write_new_at(staging_fd, name, staging / name, payload, hooks)
            hooks.check_operational()
        _write_new_at(
            staging_fd,
            "producer_manifest.json",
            staging / "producer_manifest.json",
            manifest_bytes,
            hooks,
        )
        hooks.check_operational()
        identities.append(
            _identity(
                "producer_manifest.json",
                manifest_bytes,
                role="producer_manifest",
                schema="producer_manifest_v2",
            )
        )
        total = sum(item.size_bytes for item in identities)
        if total > EVIDENCE_ARCHIVE_LIMIT:
            raise EvidenceFailure(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "producer evidence exceeds frozen byte ceiling",
            )
        # The supervisor reserves the global research-evidence bytes before
        # the no-replace publication.  A failed rename terminates this event;
        # the reservation can therefore never be used to admit later bytes.
        hooks.note_research_evidence(total)
        os.fsync(staging_fd)
        hooks.check_operational()
        try:
            _rename_noreplace(parent_fd, "evidence.staging", "evidence")
            os.fsync(parent_fd)
        except OSError as error:
            raise EvidenceFailure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"cannot publish evidence directory: {error}",
            ) from error
    finally:
        if staging_fd is not None:
            os.close(staging_fd)
        os.close(parent_fd)
    return EvidencePublication("evidence", tuple(identities), total)


def _finish_final_publication(parent_fd: int, staging_fd: int) -> NoReturn:
    """Enter the signal-safe terminal F publication path."""

    try:
        _rename_noreplace(parent_fd, "final.staging", "final")
        os.fsync(parent_fd)
        os.close(staging_fd)
        os.close(parent_fd)
    except BaseException:
        os._exit(3)
    os._exit(0)


def publish_final_trailer(
    artifact_root: Path,
    resource_payload: bytes,
    decision_payload: bytes,
    artifact_index_payload: bytes,
) -> NoReturn:
    """Perform the finite three-file F_trailer and nothing else."""

    staging = artifact_root / "final.staging"
    parent_fd = os.open(
        artifact_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.mkdir("final.staging", 0o700, dir_fd=parent_fd)
    except OSError as error:
        os.close(parent_fd)
        raise EvidenceFailure("EVIDENCE_INCOMPLETE_NO_DECISION", f"cannot create final staging: {error}") from error
    staging_fd: int | None = None
    try:
        staging_fd = os.open(
            "final.staging",
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        payloads = (resource_payload, decision_payload, artifact_index_payload)
        for name, payload in zip(FINAL_ORDER, payloads):
            if len(payload) > FINAL_LIMITS[name]:
                raise EvidenceFailure(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    f"{name} exceeds frozen byte ceiling",
                )
            _write_new_at(staging_fd, name, staging / name, payload, None)
        os.fsync(staging_fd)
        _finish_final_publication(parent_fd, staging_fd)
    finally:
        if staging_fd is not None:
            os.close(staging_fd)
        os.close(parent_fd)
    os._exit(3)
