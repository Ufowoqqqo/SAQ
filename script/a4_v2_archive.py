#!/usr/bin/env python3
"""Standalone A4 V2 pre-trailer archive-body publisher.

The archive child trusts neither producer helper code nor mutable directory
listings.  It reads the frozen prior-file set through artifact-root-relative
guards, validates canonical encodings and normative schemas, checks the
supervisor-supplied receipt/status request, publishes ``archive_body.json`` as
one atomic directory, reopens the published bytes, and returns only
``{size_bytes, sha256}`` through the explicitly inherited identity pipe.

The request is one canonical JSON document read to EOF from frozen control fd
198.
The response is one canonical JSON document written to ``--identity-pipe-fd``.
No producer, verifier, or shared artifact helper is imported.

This source may be authored and statically reviewed during A4-V2-I.  Building,
importing, or executing it requires a separately authorized later stage.
"""

from __future__ import annotations

import argparse
from collections import Counter
import ctypes
import datetime as _datetime
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time
from typing import Any, Mapping, NoReturn, Sequence


REPOSITORY_ROOT = Path(os.path.abspath(__file__)).parent.parent
SCHEMA_VERSION = 1
PRIMARY_CPU_CAP_MICROSECONDS = 34_560_000_000
PHASE_CPU_CAP_MICROSECONDS = 86_400_000_000
PHASE_WALL_CAP_NANOSECONDS = 172_800_000_000_000
STUDY_CPU_CAP_MICROSECONDS = 518_400_000_000
PEAK_RSS_CAP_BYTES = 25_769_803_776
OWNED_LIVE_TEMPORARY_CAP_BYTES = 17_179_869_184
INTERMEDIATE_BUNDLE_CAP_BYTES = 268_435_456
RESEARCH_EVIDENCE_CAP_BYTES = 4_294_967_296
MAX_REQUEST_BYTES = 16 * 1024 * 1024
MAX_SCHEMA_BYTES = 4 * 1024 * 1024
MAX_PRIOR_ARTIFACT_BYTES = 4_294_967_296

EVIDENCE_PATHS = (
    "evidence/scalar_optimum_records.jsonl",
    "evidence/allocation_summary.json",
    "evidence/block_trajectories.jsonl",
    "evidence/encoding_summary.json",
    "evidence/producer_manifest.json",
)
BUNDLE_PATHS = (
    "bundle/models.json",
    "bundle/codes_b04.bin",
    "bundle/codes_b08.bin",
    "bundle/representation_manifest.json",
)
VERIFIER_PATH = "verifier/verifier_summary.json"
PHASE_ORDER = (
    "B_build",
    "P_parity",
    "C_setup",
    "C_core",
    "C_bundle_io",
    "E_emit",
    "V_replay",
    "E_archive_body",
)
PREARCHIVE_PHASES = PHASE_ORDER[:-1]
CONTROL_FD = 198
IDENTITY_PIPE_FD = 199

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_OID_RE = re.compile(r"^[0-9a-f]{40}$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"\.[0-9]{6}Z$"
)

_LIBC = ctypes.CDLL(None, use_errno=True)
_RENAMEAT2 = getattr(_LIBC, "renameat2", None)
if _RENAMEAT2 is not None:
    _RENAMEAT2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    _RENAMEAT2.restype = ctypes.c_int
_RENAME_NOREPLACE = 1


class _Timeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]


class _Rusage(ctypes.Structure):
    _fields_ = [
        ("ru_utime", _Timeval),
        ("ru_stime", _Timeval),
        ("ru_maxrss", ctypes.c_long),
        ("ru_ixrss", ctypes.c_long),
        ("ru_idrss", ctypes.c_long),
        ("ru_isrss", ctypes.c_long),
        ("ru_minflt", ctypes.c_long),
        ("ru_majflt", ctypes.c_long),
        ("ru_nswap", ctypes.c_long),
        ("ru_inblock", ctypes.c_long),
        ("ru_oublock", ctypes.c_long),
        ("ru_msgsnd", ctypes.c_long),
        ("ru_msgrcv", ctypes.c_long),
        ("ru_nsignals", ctypes.c_long),
        ("ru_nvcsw", ctypes.c_long),
        ("ru_nivcsw", ctypes.c_long),
    ]


_GETRUSAGE = getattr(_LIBC, "getrusage", None)
if _GETRUSAGE is not None:
    _GETRUSAGE.argtypes = [ctypes.c_int, ctypes.POINTER(_Rusage)]
    _GETRUSAGE.restype = ctypes.c_int


class ArchiveContractError(RuntimeError):
    """A frozen archive, receipt, schema, or publication invariant failed."""


def _fail(message: str) -> NoReturn:
    raise ArchiveContractError(message)


def _reject_float(token: str) -> NoReturn:
    _fail(f"floating JSON number is forbidden: {token!r}")


def _reject_constant(token: str) -> NoReturn:
    _fail(f"nonfinite JSON token is forbidden: {token!r}")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _validate_json_value(value: Any, location: str = "$") -> None:
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{location}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(f"{location} has a non-string object key")
            _validate_json_value(item, f"{location}.{key}")
        return
    _fail(f"{location} contains forbidden JSON value type {type(value).__name__}")


def canonical_json_without_lf(value: Any) -> bytes:
    _validate_json_value(value)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_json_document(value: Any) -> bytes:
    return canonical_json_without_lf(value) + b"\n"


def parse_strict_json_document(
    payload: bytes,
    description: str,
    *,
    require_canonical: bool,
) -> Any:
    """Parse duplicate-free integer-only JSON, optionally requiring encoding."""

    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ArchiveContractError(f"{description} is not strict UTF-8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_float=_reject_float,
            parse_int=int,
            parse_constant=_reject_constant,
        )
    except ArchiveContractError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ArchiveContractError(f"{description} is not valid JSON") from error
    if require_canonical and canonical_json_document(value) != payload:
        _fail(f"{description} is not in frozen canonical JSON encoding")
    return value


def parse_canonical_json_lines(payload: bytes, description: str) -> list[Any]:
    if not payload:
        return []
    if not payload.endswith(b"\n"):
        _fail(f"{description} has an unterminated JSONL record")
    records: list[Any] = []
    for index, line in enumerate(payload.splitlines(keepends=True)):
        records.append(
            parse_strict_json_document(
                line,
                f"{description} line {index + 1}",
                require_canonical=True,
            )
        )
    return records


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _same_json_value(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_json_value(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _same_json_value(left[key], right[key]) for key in left
        )
    return bool(left == right)


class SchemaRegistry:
    """Independent strict validator for the schema vocabulary used here."""

    def __init__(self, root: Mapping[str, Any]):
        self._root = root

    def definition(self, name: str) -> Mapping[str, Any]:
        definitions = self._root.get("$defs")
        if not isinstance(definitions, dict) or name not in definitions:
            _fail(f"missing schema definition {name!r}")
        result = definitions[name]
        if not isinstance(result, dict):
            _fail(f"schema definition {name!r} is not an object")
        return result

    def _resolve(self, reference: str) -> Any:
        if not reference.startswith("#/"):
            _fail(f"nonlocal schema reference is forbidden: {reference!r}")
        current: Any = self._root
        for raw_part in reference[2:].split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, dict) or part not in current:
                _fail(f"unresolved schema reference {reference!r}")
            current = current[part]
        return current

    def validate_definition(self, value: Any, name: str, location: str) -> None:
        self.validate(value, self.definition(name), location)

    def validate(self, value: Any, schema: Any, location: str) -> None:
        if schema is True:
            return
        if schema is False:
            _fail(f"{location} is forbidden by schema")
        if not isinstance(schema, dict):
            _fail(f"invalid schema node at {location}")
        if "$ref" in schema:
            self.validate(value, self._resolve(schema["$ref"]), location)
        for child in schema.get("allOf", []):
            self.validate(value, child, location)
        if "oneOf" in schema:
            matches = 0
            for child in schema["oneOf"]:
                try:
                    self.validate(value, child, location)
                except ArchiveContractError:
                    continue
                matches += 1
            if matches != 1:
                _fail(f"{location} matches {matches} oneOf alternatives")
        if "if" in schema:
            try:
                self.validate(value, schema["if"], location)
                condition = True
            except ArchiveContractError:
                condition = False
            branch = schema.get("then" if condition else "else")
            if branch is not None:
                self.validate(value, branch, location)
        if "const" in schema and not _same_json_value(value, schema["const"]):
            _fail(f"{location} differs from schema const")
        if "enum" in schema and not any(
            _same_json_value(value, candidate) for candidate in schema["enum"]
        ):
            _fail(f"{location} is outside schema enum")

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
                _fail(f"{location} is not schema type {expected_type!r}")
        if isinstance(value, int) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                _fail(f"{location} is below schema minimum")
            if "maximum" in schema and value > schema["maximum"]:
                _fail(f"{location} is above schema maximum")
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                _fail(f"{location} is too short")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                _fail(f"{location} is too long")
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                _fail(f"{location} does not match schema pattern")
            if schema.get("format") == "date-time":
                _parse_utc(value, location)
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                _fail(f"{location} has too few items")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                _fail(f"{location} has too many items")
            if schema.get("uniqueItems"):
                encoded = [canonical_json_without_lf(item) for item in value]
                if len(encoded) != len(set(encoded)):
                    _fail(f"{location} violates uniqueItems")
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
                    except ArchiveContractError:
                        continue
                    matches += 1
                if matches < schema.get("minContains", 1):
                    _fail(f"{location} has too few contains matches")
                if "maxContains" in schema and matches > schema["maxContains"]:
                    _fail(f"{location} has too many contains matches")
        if isinstance(value, dict):
            missing = [key for key in schema.get("required", []) if key not in value]
            if missing:
                _fail(f"{location} is missing required keys {missing!r}")
            properties = schema.get("properties", {})
            for key, item in value.items():
                if key in properties:
                    self.validate(item, properties[key], f"{location}.{key}")
                elif schema.get("additionalProperties") is False:
                    _fail(f"{location} has forbidden key {key!r}")
                elif isinstance(schema.get("additionalProperties"), dict):
                    self.validate(
                        item,
                        schema["additionalProperties"],
                        f"{location}.{key}",
                    )


def _parse_utc(value: str, location: str) -> _datetime.datetime:
    if _UTC_RE.fullmatch(value) is None:
        _fail(f"{location} is not frozen six-fraction-digit RFC3339 UTC")
    normalized = value[:-1] + "+00:00"
    try:
        parsed = _datetime.datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ArchiveContractError(f"{location} is not a real date-time") from error
    if parsed.tzinfo is None:
        _fail(f"{location} has no UTC offset")
    return parsed.astimezone(_datetime.timezone.utc)


def normalize_artifact_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        _fail("artifact path is empty or contains a forbidden byte")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts:
        _fail(f"artifact path is not relative: {value!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        _fail(f"artifact path has dot/empty component: {value!r}")
    canonical = "/".join(path.parts)
    if canonical != value:
        _fail(f"artifact path is not normalized POSIX: {value!r}")
    return canonical


def _normalized_absolute_directory(path: Path, description: str) -> Path:
    raw = os.fspath(path)
    if not os.path.isabs(raw):
        _fail(f"{description} is not absolute")
    absolute = os.path.abspath(raw)
    if os.path.normpath(raw) != raw or absolute != raw:
        _fail(f"{description} is not a normalized absolute path")
    descriptor = _open_absolute_nofollow(
        Path(absolute),
        description,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            _fail(f"{description} is not a directory")
    finally:
        os.close(descriptor)
    return Path(absolute)


def _normalized_absolute_file_path(path: Path, description: str) -> str:
    raw = os.fspath(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        _fail(f"{description} is not a normalized absolute path")
    return raw


def _open_absolute_nofollow(path: Path, description: str, flags: int) -> int:
    raw = _normalized_absolute_file_path(path, description)
    parts = PurePosixPath(raw).parts
    directory_fd = os.open(
        "/",
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        for component in parts[1:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        return os.open(
            parts[-1],
            flags | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
    except OSError as error:
        raise ArchiveContractError(
            f"cannot open sealed no-follow {description}: {error}"
        ) from error
    finally:
        os.close(directory_fd)


def _open_artifact_root(root: Path) -> int:
    return _open_absolute_nofollow(
        root,
        "artifact root",
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )


def _open_artifact_parent(root_descriptor: int, relative: str) -> tuple[int, str]:
    parts = normalize_artifact_path(relative).split("/")
    current = os.dup(root_descriptor)
    try:
        for component in parts[:-1]:
            next_descriptor = os.open(
                component,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current,
            )
            os.close(current)
            current = next_descriptor
        return current, parts[-1]
    except OSError as error:
        os.close(current)
        raise ArchiveContractError(
            f"cannot traverse immutable artifact {relative!r}: {error}"
        ) from error


def _artifact_entry_exists(root: Path, relative: str) -> bool:
    root_descriptor = _open_artifact_root(root)
    try:
        parent_descriptor, leaf = _open_artifact_parent(root_descriptor, relative)
        try:
            try:
                os.stat(leaf, dir_fd=parent_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                return False
            return True
        finally:
            os.close(parent_descriptor)
    finally:
        os.close(root_descriptor)


def read_immutable_artifact(root: Path, relative: str, *, maximum_bytes: int) -> bytes:
    root_descriptor = _open_artifact_root(root)
    try:
        parent_descriptor, leaf = _open_artifact_parent(root_descriptor, relative)
    finally:
        os.close(root_descriptor)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(leaf, flags, dir_fd=parent_descriptor)
    except OSError as error:
        os.close(parent_descriptor)
        raise ArchiveContractError(f"cannot open immutable artifact {relative!r}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"artifact is not a regular file: {relative!r}")
        if before.st_size > maximum_bytes:
            _fail(f"artifact exceeds archive input ceiling: {relative!r}")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, min(1 << 20, before.st_size - len(payload)))
            if not chunk:
                _fail(f"artifact ended early: {relative!r}")
            payload.extend(chunk)
        if os.read(descriptor, 1):
            _fail(f"artifact grew during read: {relative!r}")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    for field in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns"):
        if getattr(before, field) != getattr(after, field):
            _fail(f"artifact mutated during archive read: {relative!r}")
    try:
        named = os.stat(leaf, dir_fd=parent_descriptor, follow_symlinks=False)
    except OSError as error:
        os.close(parent_descriptor)
        raise ArchiveContractError(
            f"artifact path disappeared after archive read: {relative!r}"
        ) from error
    os.close(parent_descriptor)
    for field in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns"):
        if getattr(after, field) != getattr(named, field):
            _fail(f"artifact path was replaced during archive read: {relative!r}")
    return bytes(payload)


def _read_sealed_file(
    path: Path,
    description: str,
    *,
    expected_size_bytes: int,
    expected_sha256: str,
    maximum_bytes: int,
) -> bytes:
    if expected_size_bytes < 0 or expected_size_bytes > maximum_bytes:
        _fail(f"{description} has an out-of-range sealed size")
    _require_sha256(expected_sha256, f"{description} SHA-256")
    descriptor = _open_absolute_nofollow(path, description, os.O_RDONLY)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size != expected_size_bytes:
            _fail(f"{description} does not have the sealed regular-file size")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, min(1 << 20, before.st_size - len(payload)))
            if not chunk:
                _fail(f"{description} ended early")
            payload.extend(chunk)
        if os.read(descriptor, 1):
            _fail(f"{description} grew during read")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in stable):
        _fail(f"{description} mutated during read")
    replacement = _open_absolute_nofollow(path, description, os.O_RDONLY)
    try:
        named = os.fstat(replacement)
    finally:
        os.close(replacement)
    if any(getattr(after, field) != getattr(named, field) for field in stable):
        _fail(f"{description} path was replaced during read")
    if sha256_bytes(bytes(payload)) != expected_sha256:
        _fail(f"{description} does not match its sealed SHA-256")
    return bytes(payload)


def _rename_noreplace(
    old_directory_fd: int,
    old_name: str,
    new_directory_fd: int,
    new_name: str,
) -> None:
    if _RENAMEAT2 is None:
        _fail("Linux renameat2 is unavailable; atomic no-replace publication is impossible")
    result = _RENAMEAT2(
        old_directory_fd,
        os.fsencode(old_name),
        new_directory_fd,
        os.fsencode(new_name),
        _RENAME_NOREPLACE,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
            _fail(f"refusing to replace published directory {new_name!r}")
        raise OSError(error_number, os.strerror(error_number))


def _require_mapping(value: Any, description: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{description} is not an object")
    return value


def _require_list(value: Any, description: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{description} is not an array")
    return value


def _require_sha256(value: Any, description: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        _fail(f"{description} is not lowercase SHA-256")
    return value


def _require_nonnegative_integer(value: Any, description: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _fail(f"{description} is not a nonnegative integer")
    return value


def _sealed_file_request(value: Any, description: str) -> dict[str, Any]:
    item = _require_mapping(value, description)
    if set(item) != {"identity_path", "read_path", "sha256", "size_bytes"}:
        _fail(f"{description} does not have the exact sealed-file key set")
    if not isinstance(item["identity_path"], str) or not isinstance(item["read_path"], str):
        _fail(f"{description} paths are not strings")
    identity_path = normalize_artifact_path(item["identity_path"])
    relative_read_path = normalize_artifact_path(item["read_path"])
    if relative_read_path != identity_path:
        _fail(f"{description} identity_path/read_path differ")
    read_path = os.fspath(
        REPOSITORY_ROOT.joinpath(*relative_read_path.split("/"))
    )
    _normalized_absolute_file_path(Path(read_path), description)
    return {
        "identity_path": identity_path,
        "read_path": read_path,
        "sha256": _require_sha256(item["sha256"], f"{description}.sha256"),
        "size_bytes": _require_nonnegative_integer(
            item["size_bytes"], f"{description}.size_bytes"
        ),
    }


def _file_identity(
    path: str,
    payload: bytes,
    *,
    phase: str,
    role: str,
    schema: str,
) -> dict[str, Any]:
    return {
        "path": normalize_artifact_path(path),
        "producing_phase": phase,
        "role": role,
        "schema": schema,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
    }


def _verify_embedded_identity(
    identity: Mapping[str, Any],
    expected_path: str,
    payload: bytes,
) -> None:
    if identity.get("path") != expected_path:
        _fail(f"embedded identity path mismatch for {expected_path!r}")
    if identity.get("size_bytes") != len(payload):
        _fail(f"embedded identity size mismatch for {expected_path!r}")
    if identity.get("sha256") != sha256_bytes(payload):
        _fail(f"embedded identity hash mismatch for {expected_path!r}")


def _derive_evidence_validity(
    scalar_records: Sequence[Mapping[str, Any]],
    allocation: Mapping[str, Any],
    block_records: Sequence[Mapping[str, Any]],
    encoding: Mapping[str, Any],
) -> tuple[bool, bool]:
    scalar_strict = {
        (record["coordinate_id"], record["requested_cardinality"]): (
            record["effective_cardinality"] == record["requested_cardinality"]
            and len(record["partition"]) == record["requested_cardinality"]
            and len(record["exact_means"]) == record["requested_cardinality"]
            and len(record["binary32_centroid_bits"])
            == record["requested_cardinality"]
            and len(record["binary64_centroid_bits"])
            == record["requested_cardinality"]
            and record["serialized_binary32_strictly_increasing"] is True
        )
        for record in scalar_records
    }
    representation_valid = True
    for record in allocation["group_records"]:
        for arm_name in ("dyadic_word", "arbitrary_word"):
            arm = record[arm_name]
            requested_product = (
                arm["requested_cardinalities"][0]
                * arm["requested_cardinalities"][1]
            )
            if (
                arm["effective_cardinalities"] != arm["requested_cardinalities"]
                or arm["used_states"] != requested_product
                or arm["invalid_states"] != record["capacity"] - requested_product
            ):
                representation_valid = False
            for coordinate, cardinality in zip(
                record["coordinates"], arm["requested_cardinalities"]
            ):
                if scalar_strict.get((coordinate, cardinality)) is not True:
                    representation_valid = False
    for record in allocation["global_records"]:
        for coordinate, cardinality in enumerate(record["cardinalities"]):
            if scalar_strict.get((coordinate, cardinality)) is not True:
                representation_valid = False
        if any(
            cardinality != 1 << width
            for cardinality, width in zip(record["cardinalities"], record["bit_widths"])
        ) or record["used_bits"] != sum(record["bit_widths"]):
            representation_valid = False

    control_valid = True
    metadata = {
        (record["word_bits"], record["group_id"]): record
        for record in block_records
        if record["record_type"] == "block_metadata_v2"
    }
    starts_by_group: dict[tuple[int, int], list[Mapping[str, Any]]] = {}
    for record in block_records:
        if record["record_type"] == "block_start_v2":
            starts_by_group.setdefault(
                (record["word_bits"], record["group_id"]), []
            ).append(record)
    if set(metadata) != set(starts_by_group):
        control_valid = False
    for key, group_metadata in metadata.items():
        starts = starts_by_group.get(key, [])
        if [record["start_id"] for record in starts] != list(range(8)):
            control_valid = False
            continue
        for record in starts:
            if record["converged"] is not True or record["direct_replay_match"] is not True:
                control_valid = False
            for step in record["steps"]:
                prior_bits = int(step["prior_sse_bits"], 16)
                candidate_bits = int(step["candidate_sse_bits"], 16)
                if (
                    prior_bits >> 63
                    or candidate_bits >> 63
                    or (prior_bits >> 52) & 0x7FF == 0x7FF
                    or (candidate_bits >> 52) & 0x7FF == 0x7FF
                    or candidate_bits > prior_bits
                ):
                    control_valid = False
        selected = [record for record in starts if record["selected_best_start"] is True]
        if len(selected) != 1:
            control_valid = False
            continue
        selected_record = selected[0]
        finite_sse = [int(record["final_sse_bits"], 16) for record in starts]
        if any(
            bits >> 63 or ((bits >> 52) & 0x7FF) == 0x7FF
            for bits in finite_sse
        ):
            control_valid = False
        selected_index = min(range(8), key=lambda index: (finite_sse[index], index))
        if (
            selected_record["start_id"] != group_metadata["selected_start_id"]
            or selected_record["start_id"] != selected_index
            or selected_record["cartesian_dominance_pass"] is not True
            or selected_record["serialized_distinct_center_count"]
            != selected_record["capacity"]
        ):
            control_valid = False
    for record in encoding["records"]:
        if record["roundtrip_match"] is not True or record["roundtrip_mismatch_count"] != 0:
            control_valid = False
    return control_valid, representation_valid


def _load_prior_files(
    root: Path,
    registry: SchemaRegistry,
    protocol_identity: Mapping[str, Any],
    schema_identity: Mapping[str, Any],
) -> tuple[
    Mapping[str, Any],
    Mapping[str, Any],
    list[dict[str, Any]],
    bool,
    bool,
]:
    payloads: dict[str, bytes] = {}
    for relative in EVIDENCE_PATHS:
        payloads[relative] = read_immutable_artifact(
            root, relative, maximum_bytes=MAX_PRIOR_ARTIFACT_BYTES
        )
    manifest = _require_mapping(
        parse_strict_json_document(
            payloads["evidence/producer_manifest.json"],
            "producer manifest",
            require_canonical=True,
        ),
        "producer manifest",
    )
    registry.validate_definition(manifest, "producer_manifest_v2", "producer_manifest")
    if manifest["prelaunch_observation"]["output_root"] != os.fspath(root):
        _fail("producer prelaunch output_root differs from archive artifact root")
    root_descriptor = _open_artifact_root(root)
    try:
        root_device = os.fstat(root_descriptor).st_dev
    finally:
        os.close(root_descriptor)
    if manifest["prelaunch_observation"]["output_filesystem_device_id"] != root_device:
        _fail("producer prelaunch filesystem device differs from archive root")
    expected_protocol = {
        "path": protocol_identity["identity_path"],
        "sha256": protocol_identity["sha256"],
        "size_bytes": protocol_identity["size_bytes"],
    }
    expected_schema = {
        "path": schema_identity["identity_path"],
        "sha256": schema_identity["sha256"],
        "size_bytes": schema_identity["size_bytes"],
    }
    if manifest["protocol_identity"] != expected_protocol:
        _fail("producer protocol identity differs from trusted archive bootstrap")
    if manifest["schema_identity"] != expected_schema:
        _fail("producer schema identity differs from trusted archive bootstrap")

    scalar_records = parse_canonical_json_lines(
        payloads["evidence/scalar_optimum_records.jsonl"], "scalar optimum JSONL"
    )
    for index, record in enumerate(scalar_records):
        registry.validate_definition(record, "scalar_optimum_v2", f"scalar[{index}]")
    allocation = _require_mapping(
        parse_strict_json_document(
            payloads["evidence/allocation_summary.json"],
            "allocation summary",
            require_canonical=True,
        ),
        "allocation summary",
    )
    registry.validate_definition(allocation, "allocation_summary_v2", "allocation")
    block_records = parse_canonical_json_lines(
        payloads["evidence/block_trajectories.jsonl"], "block trajectory JSONL"
    )
    for index, record in enumerate(block_records):
        if not isinstance(record, dict):
            _fail("block trajectory record is not an object")
        definition = (
            "block_metadata_v2"
            if record.get("record_type") == "block_metadata_v2"
            else "block_start_v2"
        )
        registry.validate_definition(record, definition, f"block[{index}]")
    encoding = _require_mapping(
        parse_strict_json_document(
            payloads["evidence/encoding_summary.json"],
            "encoding summary",
            require_canonical=True,
        ),
        "encoding summary",
    )
    registry.validate_definition(encoding, "encoding_summary_v2", "encoding")
    for identity, relative in zip(manifest["evidence_files"], EVIDENCE_PATHS[:4]):
        _verify_embedded_identity(identity, relative, payloads[relative])

    identities = [
        _file_identity(
            EVIDENCE_PATHS[0],
            payloads[EVIDENCE_PATHS[0]],
            phase="E_emit",
            role="scalar_optimum_records",
            schema="scalar_optimum_v2-jsonl",
        ),
        _file_identity(
            EVIDENCE_PATHS[1],
            payloads[EVIDENCE_PATHS[1]],
            phase="E_emit",
            role="allocation_summary",
            schema="allocation_summary_v2",
        ),
        _file_identity(
            EVIDENCE_PATHS[2],
            payloads[EVIDENCE_PATHS[2]],
            phase="E_emit",
            role="block_trajectories",
            schema="block_metadata_v2-or-block_start_v2-jsonl",
        ),
        _file_identity(
            EVIDENCE_PATHS[3],
            payloads[EVIDENCE_PATHS[3]],
            phase="E_emit",
            role="encoding_summary",
            schema="encoding_summary_v2",
        ),
        _file_identity(
            EVIDENCE_PATHS[4],
            payloads[EVIDENCE_PATHS[4]],
            phase="E_emit",
            role="producer_manifest",
            schema="producer_manifest_v2",
        ),
    ]

    if manifest["bundle_published"]:
        for relative in BUNDLE_PATHS:
            payloads[relative] = read_immutable_artifact(
                root, relative, maximum_bytes=268_435_456
            )
        models = _require_mapping(
            parse_strict_json_document(
                payloads[BUNDLE_PATHS[0]], "bundle models", require_canonical=True
            ),
            "bundle models",
        )
        representation = _require_mapping(
            parse_strict_json_document(
                payloads[BUNDLE_PATHS[3]],
                "representation manifest",
                require_canonical=True,
            ),
            "representation manifest",
        )
        registry.validate_definition(models, "models_v2", "bundle.models")
        registry.validate_definition(
            representation, "representation_manifest_v2", "bundle.manifest"
        )
        _verify_embedded_identity(
            representation["models"], "models.json", payloads[BUNDLE_PATHS[0]]
        )
        for identity, relative in zip(representation["code_files"], BUNDLE_PATHS[1:3]):
            _verify_embedded_identity(
                identity, relative.removeprefix("bundle/"), payloads[relative]
            )
        identities.extend(
            [
                _file_identity(
                    BUNDLE_PATHS[0],
                    payloads[BUNDLE_PATHS[0]],
                    phase="C_bundle_io",
                    role="comparative_models",
                    schema="models_v2",
                ),
                _file_identity(
                    BUNDLE_PATHS[1],
                    payloads[BUNDLE_PATHS[1]],
                    phase="C_bundle_io",
                    role="encoded_payloads_b04",
                    schema="raw-binary",
                ),
                _file_identity(
                    BUNDLE_PATHS[2],
                    payloads[BUNDLE_PATHS[2]],
                    phase="C_bundle_io",
                    role="encoded_payloads_b08",
                    schema="raw-binary",
                ),
                _file_identity(
                    BUNDLE_PATHS[3],
                    payloads[BUNDLE_PATHS[3]],
                    phase="C_bundle_io",
                    role="representation_manifest",
                    schema="representation_manifest_v2",
                ),
            ]
        )
    elif _artifact_entry_exists(root, "bundle"):
        _fail("bundle directory exists although manifest says unpublished")

    verifier_payload = read_immutable_artifact(
        root, VERIFIER_PATH, maximum_bytes=MAX_PRIOR_ARTIFACT_BYTES
    )
    verifier = _require_mapping(
        parse_strict_json_document(
            verifier_payload, "verifier summary", require_canonical=True
        ),
        "verifier summary",
    )
    registry.validate_definition(verifier, "verifier_summary_v2", "verifier_summary")
    if verifier["producer_identity"] != sha256_bytes(payloads[EVIDENCE_PATHS[4]]):
        _fail("verifier summary is not bound to producer manifest bytes")
    if verifier["input_identity"] != manifest["input_identity"]["input_identity_sha256"]:
        _fail("verifier summary is not bound to producer input identity")
    if verifier["decision_counts_expected"] != manifest["record_counts"]:
        _fail("verifier expected decision counts differ from producer manifest")
    verifier_mismatch = (
        verifier["decision_counts_observed"] != verifier["decision_counts_expected"]
        or bool(verifier["discrepancies"])
    )
    if verifier["status"] == "VERIFIED" and verifier_mismatch:
        _fail("VERIFIED summary has unequal counts or nonempty discrepancies")
    if verifier["status"] == "MISMATCH" and not verifier_mismatch:
        _fail("MISMATCH summary has neither a count mismatch nor discrepancy")
    if verifier["status"] == "INCOMPLETE" and not verifier["discrepancies"]:
        _fail("INCOMPLETE summary has no discrepancy")
    verifier_checkpoint = verifier["verifier_start_checkpoint"]
    expected_verifier_inputs = 9 if manifest["bundle_published"] else 5
    if (
        verifier_checkpoint["completed_unit_count"] != manifest["completed_unit_count"]
        or verifier_checkpoint["last_completed_unit_index"]
        != manifest["last_completed_unit_index"]
        or verifier_checkpoint["input_file_count"] != expected_verifier_inputs
    ):
        _fail("verifier start checkpoint does not bind the exact producer prefix")
    identities.append(
        _file_identity(
            VERIFIER_PATH,
            verifier_payload,
            phase="V_replay",
            role="verifier_summary",
            schema="verifier_summary_v2",
        )
    )
    identities.sort(key=lambda identity: identity["path"].encode("utf-8"))
    paths = [identity["path"] for identity in identities]
    if len(paths) != len(set(paths)):
        _fail("pre-trailer file identity paths are duplicated")
    for identity in identities:
        registry.validate_definition(identity, "file_identity", "pretrailer_file")
    control_valid, representation_valid = _derive_evidence_validity(
        [_require_mapping(record, "scalar record") for record in scalar_records],
        allocation,
        [_require_mapping(record, "block record") for record in block_records],
        encoding,
    )
    return manifest, verifier, identities, control_valid, representation_valid


def _read_fd_document(descriptor: int, description: str, maximum_bytes: int) -> bytes:
    if descriptor <= 2:
        _fail(f"{description} descriptor must be greater than stderr")
    try:
        os.fstat(descriptor)
    except OSError as error:
        raise ArchiveContractError(f"{description} descriptor is not open") from error
    payload = bytearray()
    while True:
        chunk = os.read(descriptor, min(1 << 20, maximum_bytes + 1 - len(payload)))
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > maximum_bytes:
            _fail(f"{description} exceeds byte ceiling")
    return bytes(payload)


def _receipt_identity(receipt: Mapping[str, Any]) -> bytes:
    return canonical_json_without_lf(dict(receipt))


def _validate_prior_archive_attempt_receipts(
    registry: SchemaRegistry,
    value: Any,
    checkpoint: Mapping[str, Any],
) -> tuple[int, int]:
    receipts = [
        _require_mapping(item, "prior archive attempt receipt")
        for item in _require_list(value, "prior archive attempt receipts")
    ]
    attempts = [receipt["attempt_id"] for receipt in receipts]
    if attempts not in ([], [0]):
        _fail("prior archive attempts are not the frozen zero-or-one retry prefix")
    for index, receipt in enumerate(receipts):
        registry.validate_definition(
            receipt, "phase_receipt", f"prior_archive_receipt[{index}]"
        )
        if receipt["phase"] != "E_archive_body":
            _fail("prior archive receipt names a different phase")
        if receipt["logical_run_id"] != checkpoint["logical_run_id"]:
            _fail("prior archive receipt has a different logical_run_id")
        if receipt["completed_unit_index"] != checkpoint["last_completed_unit_index"]:
            _fail("prior archive receipt has a different completed prefix")
        if receipt["staging_disposition"] == "ATOMICALLY_PUBLISHED":
            _fail("a prior archive retry receipt already claims publication")
        if _parse_utc(receipt["end_utc"], "prior archive end") < _parse_utc(
            receipt["start_utc"], "prior archive start"
        ):
            _fail("prior archive receipt ends before it starts")
        if _parse_utc(receipt["end_utc"], "prior archive end") > _parse_utc(
            checkpoint["start_utc"], "archive checkpoint start"
        ):
            _fail("prior archive receipt overlaps the successful attempt checkpoint")
    return (
        sum(receipt["cpu_microseconds"] for receipt in receipts),
        sum(receipt["wall_nanoseconds"] for receipt in receipts),
    )


def _validate_receipts(
    registry: SchemaRegistry,
    phase_receipts: Sequence[Mapping[str, Any]],
    attempt_ledger: Sequence[Mapping[str, Any]],
    logical_run_id: str,
    producer_receipts: Sequence[Mapping[str, Any]],
    sealed_phase_identities: Sequence[Mapping[str, Any]],
    resource_observation: Mapping[str, Any],
) -> tuple[int, int, bool]:
    phase_rank = {phase: index for index, phase in enumerate(PHASE_ORDER)}
    for index, receipt in enumerate(phase_receipts):
        registry.validate_definition(receipt, "phase_receipt", f"phase_receipt[{index}]")
        if receipt["phase"] not in PREARCHIVE_PHASES:
            _fail("phase_receipts_through_verifier contains archive receipt")
        if _parse_utc(receipt["end_utc"], "receipt end_utc") < _parse_utc(
            receipt["start_utc"], "receipt start_utc"
        ):
            _fail("phase receipt ends before it starts")
    expected_phase_order = sorted(
        phase_receipts,
        key=lambda receipt: (phase_rank[receipt["phase"]], receipt["attempt_id"]),
    )
    if list(phase_receipts) != expected_phase_order:
        _fail("phase receipts are not in frozen phase/attempt order")
    receipt_keys = [(receipt["phase"], receipt["attempt_id"]) for receipt in phase_receipts]
    if len(receipt_keys) != len(set(receipt_keys)):
        _fail("phase receipts duplicate a phase/attempt identity")
    for phase in PREARCHIVE_PHASES:
        attempts = [receipt["attempt_id"] for receipt in phase_receipts if receipt["phase"] == phase]
        allowed = ([], [0], [1], [0, 1]) if phase in {
            "C_setup",
            "C_core",
            "C_bundle_io",
        } else ([], [0], [0, 1])
        if attempts not in allowed:
            _fail(f"phase {phase} has noncontiguous attempt ids")
    if Counter(_receipt_identity(receipt) for receipt in phase_receipts) != Counter(
        _receipt_identity(receipt) for receipt in attempt_ledger
    ):
        _fail("chronological attempt ledger is not the same receipt multiset")
    expected_chronological = sorted(
        attempt_ledger,
        key=lambda receipt: (
            _parse_utc(receipt["start_utc"], "receipt start_utc"),
            phase_rank[receipt["phase"]],
            receipt["attempt_id"],
        ),
    )
    if list(attempt_ledger) != expected_chronological:
        _fail("attempt ledger is not in frozen chronological order")
    for prior, following in zip(attempt_ledger, attempt_ledger[1:]):
        if _parse_utc(prior["end_utc"], "receipt end_utc") > _parse_utc(
            following["start_utc"], "receipt start_utc"
        ):
            _fail("phase attempts overlap in the chronological ledger")
    current_phases = {"C_setup", "C_core", "C_bundle_io", "E_emit", "V_replay"}
    if any(
        receipt["logical_run_id"] != logical_run_id
        for receipt in phase_receipts
        if receipt["phase"] in current_phases
    ):
        _fail("current observation receipt has a different logical_run_id")
    producer_identity = [_receipt_identity(receipt) for receipt in producer_receipts]
    expected_producer = [
        _receipt_identity(receipt)
        for receipt in phase_receipts
        if phase_rank[receipt["phase"]] <= phase_rank["C_bundle_io"]
    ]
    if producer_identity != expected_producer:
        _fail("producer manifest receipts do not match receipts through instrument")

    present_phases = []
    for phase in PREARCHIVE_PHASES:
        if any(receipt["phase"] == phase for receipt in phase_receipts):
            present_phases.append(phase)
    mandatory = {"B_build", "P_parity", "C_setup", "E_emit", "V_replay"}
    if not mandatory.issubset(set(present_phases)):
        _fail("required B/P/C_setup/E/V receipt phase is absent")
    sealed_items: list[Mapping[str, Any]] = []
    sealed_keys = {
        "argv_sha256",
        "attempt_count",
        "binary_sha256",
        "environment_sha256",
        "execution_commit",
        "logical_run_id",
        "phase",
    }
    for index, value in enumerate(sealed_phase_identities):
        item = _require_mapping(value, f"sealed phase identity {index}")
        if set(item) != sealed_keys:
            _fail("sealed phase identity has a nonfrozen key set")
        if item["phase"] not in PREARCHIVE_PHASES:
            _fail("sealed phase identity names a non-prearchive phase")
        for key in ("argv_sha256", "binary_sha256", "environment_sha256", "logical_run_id"):
            _require_sha256(item[key], f"sealed phase identity {key}")
        if not isinstance(item["execution_commit"], str) or _GIT_OID_RE.fullmatch(item["execution_commit"]) is None:
            _fail("sealed phase identity execution_commit is not a Git OID")
        _require_nonnegative_integer(item["attempt_count"], "sealed attempt_count")
        if item["attempt_count"] not in {1, 2}:
            _fail("sealed phase attempt_count is outside the frozen retry bound")
        sealed_items.append(item)
    if [item["phase"] for item in sealed_items] != present_phases:
        _fail("sealed phase identities are not the exact started-phase inventory")
    for item in sealed_items:
        receipts = [
            receipt for receipt in phase_receipts if receipt["phase"] == item["phase"]
        ]
        if len(receipts) != item["attempt_count"]:
            _fail("sealed phase attempt_count differs from receipts")
        for receipt in receipts:
            for key in (
                "argv_sha256",
                "binary_sha256",
                "environment_sha256",
                "execution_commit",
                "logical_run_id",
            ):
                if receipt[key] != item[key]:
                    _fail(f"receipt {key} differs from sealed phase identity")
    for phase in ("B_build", "P_parity", "E_emit", "V_replay"):
        receipts = [receipt for receipt in phase_receipts if receipt["phase"] == phase]
        terminal = receipts[-1]
        expected_disposition = (
            "NONE" if phase in {"B_build", "P_parity"} else "ATOMICALLY_PUBLISHED"
        )
        if (
            terminal["exit_reason"] != "PHASE_COMPLETE"
            or terminal["staging_disposition"] != expected_disposition
        ):
            _fail(f"phase {phase} lacks its frozen terminal disposition")
        if any(receipt["staging_disposition"] == "ATOMICALLY_PUBLISHED" for receipt in receipts[:-1]):
            _fail(f"phase {phase} has a published nonterminal retry attempt")

    t_instrument = sum(
        receipt["cpu_microseconds"]
        for receipt in phase_receipts
        if receipt["phase"] in {"C_setup", "C_core", "C_bundle_io"}
    )
    t_study_through_verifier = sum(
        receipt["cpu_microseconds"] for receipt in phase_receipts
    )
    resource_complete = True
    for phase in ("B_build", "P_parity", "E_emit", "V_replay"):
        receipts = [receipt for receipt in phase_receipts if receipt["phase"] == phase]
        if (
            sum(receipt["cpu_microseconds"] for receipt in receipts)
            > PHASE_CPU_CAP_MICROSECONDS
            or sum(receipt["wall_nanoseconds"] for receipt in receipts)
            > PHASE_WALL_CAP_NANOSECONDS
        ):
            resource_complete = False
    producer_attempts = sorted(
        {
            receipt["attempt_id"]
            for receipt in phase_receipts
            if receipt["phase"] in {"C_setup", "C_core", "C_bundle_io"}
        }
    )
    if producer_attempts not in ([0], [0, 1]):
        _fail("producer attempt ids are not the frozen contiguous set")
    for attempt in producer_attempts:
        receipts = [
            receipt
            for receipt in phase_receipts
            if receipt["phase"] in {"C_setup", "C_core", "C_bundle_io"}
            and receipt["attempt_id"] == attempt
        ]
        if (
            sum(receipt["cpu_microseconds"] for receipt in receipts)
            > PHASE_CPU_CAP_MICROSECONDS
            or sum(receipt["wall_nanoseconds"] for receipt in receipts)
            > PHASE_WALL_CAP_NANOSECONDS
        ):
            resource_complete = False
    if t_study_through_verifier > STUDY_CPU_CAP_MICROSECONDS:
        resource_complete = False
    if any(
        receipt["peak_rss_bytes"] > PEAK_RSS_CAP_BYTES
        for receipt in phase_receipts
        if receipt["phase"]
        in {"B_build", "P_parity", "C_setup", "C_core", "C_bundle_io", "E_emit", "V_replay"}
    ):
        resource_complete = False
    byte_keys = {
        "intermediate_bundle_bytes",
        "maximum_live_owned_temporary_bytes",
        "research_evidence_archive_bytes",
    }
    if set(resource_observation) != byte_keys:
        _fail("resource observation has a nonfrozen key set")
    for key in byte_keys:
        _require_nonnegative_integer(resource_observation[key], f"resource observation {key}")
    if (
        resource_observation["maximum_live_owned_temporary_bytes"]
        > OWNED_LIVE_TEMPORARY_CAP_BYTES
        or resource_observation["intermediate_bundle_bytes"]
        > INTERMEDIATE_BUNDLE_CAP_BYTES
        or resource_observation["research_evidence_archive_bytes"]
        > RESEARCH_EVIDENCE_CAP_BYTES
    ):
        resource_complete = False
    return t_instrument, t_study_through_verifier, resource_complete


def _validate_request_and_build_body(
    registry: SchemaRegistry,
    request: Mapping[str, Any],
    manifest: Mapping[str, Any],
    verifier: Mapping[str, Any],
    identities: Sequence[Mapping[str, Any]],
    derived_control_valid: bool,
    derived_representation_valid: bool,
) -> tuple[dict[str, Any], int]:
    required_keys = {
        "archive_start_checkpoint",
        "attempt_ledger",
        "gate_operands",
        "phase_receipts_through_verifier",
        "resource_observation_through_verifier",
        "sealed_phase_identities",
        "status_inputs",
    }
    if set(request) != required_keys:
        _fail("archive request has a nonfrozen key set")
    checkpoint = _require_mapping(request["archive_start_checkpoint"], "archive checkpoint")
    gate = _require_mapping(request["gate_operands"], "gate operands")
    status_inputs = _require_mapping(request["status_inputs"], "archive status inputs")
    phase_receipts = [
        _require_mapping(item, "phase receipt")
        for item in _require_list(
            request["phase_receipts_through_verifier"], "phase receipts"
        )
    ]
    attempt_ledger = [
        _require_mapping(item, "attempt receipt")
        for item in _require_list(request["attempt_ledger"], "attempt ledger")
    ]
    sealed_phase_identities = [
        _require_mapping(item, "sealed phase identity")
        for item in _require_list(
            request["sealed_phase_identities"], "sealed phase identities"
        )
    ]
    resource_observation = _require_mapping(
        request["resource_observation_through_verifier"],
        "resource observation through verifier",
    )
    registry.validate_definition(checkpoint, "archive_start_checkpoint", "archive_checkpoint")
    registry.validate_definition(gate, "gate_operands", "gate_operands")
    registry.validate_definition(status_inputs, "archive_status_inputs", "status_inputs")
    if checkpoint["pretrailer_file_count"] != len(identities):
        _fail("archive checkpoint pretrailer_file_count mismatch")
    if checkpoint["completed_unit_count"] != manifest["completed_unit_count"]:
        _fail("archive checkpoint completed-unit count mismatch")
    if checkpoint["last_completed_unit_index"] != manifest["last_completed_unit_index"]:
        _fail("archive checkpoint last-unit mismatch")
    if checkpoint["logical_run_id"] != verifier["verifier_start_checkpoint"]["logical_run_id"]:
        _fail("archive checkpoint and verifier logical_run_id differ")
    if phase_receipts and _parse_utc(checkpoint["start_utc"], "archive start_utc") < max(
        _parse_utc(receipt["end_utc"], "receipt end_utc")
        for receipt in phase_receipts
    ):
        _fail("archive checkpoint precedes a through-verifier receipt end")
    t_instrument, t_study_through_verifier, resource_complete = _validate_receipts(
        registry,
        phase_receipts,
        attempt_ledger,
        checkpoint["logical_run_id"],
        manifest["phase_receipts_through_instrument"],
        sealed_phase_identities,
        resource_observation,
    )
    by_phase = {
        phase: [receipt for receipt in phase_receipts if receipt["phase"] == phase]
        for phase in PREARCHIVE_PHASES
    }
    terminal_control_invalid = any(
        receipt["exit_reason"] == "CONTROL_INVALID"
        for phase in ("C_setup", "C_core", "C_bundle_io")
        for receipt in by_phase[phase]
    )
    if any(
        receipt["completed_unit_index"] != -1
        for phase in ("B_build", "P_parity")
        for receipt in by_phase[phase]
    ):
        _fail("B/P receipt claims a scientific completed-unit index")
    if any(
        receipt["completed_unit_index"] > manifest["last_completed_unit_index"]
        for phase in ("C_setup", "C_core", "C_bundle_io")
        for receipt in by_phase[phase]
    ):
        _fail("C receipt exceeds the published producer prefix")
    if max(
        (
            receipt["completed_unit_index"]
            for phase in ("C_setup", "C_core", "C_bundle_io")
            for receipt in by_phase[phase]
        ),
        default=-1,
    ) != manifest["last_completed_unit_index"]:
        _fail("C receipts do not close at the published producer prefix")
    if any(
        receipt["completed_unit_index"] != manifest["last_completed_unit_index"]
        for phase in ("E_emit", "V_replay")
        for receipt in by_phase[phase]
    ):
        _fail("E/V receipt does not bind the published producer prefix")
    if manifest["bundle_published"] and not by_phase["C_bundle_io"]:
        _fail("published bundle lacks a C_bundle_io receipt")
    if manifest["completed_unit_count"] > 1 and not by_phase["C_core"]:
        _fail("a post-U000 producer prefix lacks a C_core receipt")
    emit_checkpoint = manifest["emit_start_checkpoint"]
    expected_emit_inputs = 4 if manifest["bundle_published"] else 0
    if (
        emit_checkpoint["completed_unit_count"] != manifest["completed_unit_count"]
        or emit_checkpoint["last_completed_unit_index"]
        != manifest["last_completed_unit_index"]
        or emit_checkpoint["input_file_count"] != expected_emit_inputs
        or emit_checkpoint["logical_run_id"] != checkpoint["logical_run_id"]
        or emit_checkpoint["start_utc"] != by_phase["E_emit"][-1]["start_utc"]
    ):
        _fail("E_emit checkpoint does not bind the exact terminal E receipt/prefix")
    verifier_checkpoint = verifier["verifier_start_checkpoint"]
    expected_verifier_inputs = 9 if manifest["bundle_published"] else 5
    if (
        verifier_checkpoint["completed_unit_count"] != manifest["completed_unit_count"]
        or verifier_checkpoint["last_completed_unit_index"]
        != manifest["last_completed_unit_index"]
        or verifier_checkpoint["input_file_count"] != expected_verifier_inputs
        or verifier_checkpoint["logical_run_id"] != checkpoint["logical_run_id"]
        or verifier_checkpoint["start_utc"] != by_phase["V_replay"][-1]["start_utc"]
    ):
        _fail("V_replay checkpoint does not bind the exact terminal V receipt/prefix")
    if gate["t_instrument_cpu_microseconds"] != t_instrument:
        _fail("gate T_instrument does not reconcile to C phase receipts")
    if gate["primary_cpu_cap_microseconds"] != PRIMARY_CPU_CAP_MICROSECONDS:
        _fail("gate carries a nonfrozen primary cap")
    if gate["cap_crossed"] != (t_instrument > PRIMARY_CPU_CAP_MICROSECONDS):
        _fail("gate cap_crossed uses the wrong strict inequality")
    for field in ("completed_unit_count", "last_completed_unit_index", "full_shape_complete"):
        if gate[field] != manifest[field]:
            _fail(f"gate operand {field} differs from producer manifest")
    if status_inputs["full_shape_complete"] != manifest["full_shape_complete"]:
        _fail("archive status full_shape_complete mismatch")
    if status_inputs["primary_cap_pass"] != (t_instrument <= PRIMARY_CPU_CAP_MICROSECONDS):
        _fail("archive primary_cap_pass mismatch")
    if status_inputs["verification_pass"] != (verifier["status"] == "VERIFIED"):
        _fail("archive verification_pass mismatch")
    if status_inputs["control_valid"] != (
        derived_control_valid and not terminal_control_invalid
    ):
        _fail(
            "archive control_valid differs from evidence and terminal C receipt"
        )
    if status_inputs["representation_valid"] != derived_representation_valid:
        _fail("archive representation_valid differs from evidence-derived representation checks")
    if status_inputs["resource_complete_through_verifier"] != resource_complete:
        _fail("archive resource_complete_through_verifier differs from recomputed ceilings")
    if status_inputs["artifact_valid"] is not True:
        _fail("validated archive inputs cannot be marked artifact-invalid")
    if not status_inputs["producer_evidence_complete"]:
        _fail("archive cannot publish with producer evidence marked incomplete")
    if not status_inputs["verifier_summary_complete"]:
        _fail("archive cannot publish with verifier summary marked incomplete")
    body = {
        "archive_start_checkpoint": dict(checkpoint),
        "artifact_kind": "a4_archive_body",
        "attempt_ledger": [dict(receipt) for receipt in attempt_ledger],
        "gate_operands": dict(gate),
        "phase_receipts_through_verifier": [dict(receipt) for receipt in phase_receipts],
        "pretrailer_files": [dict(identity) for identity in identities],
        "protocol_identity": manifest["protocol_identity"]["sha256"],
        "schema_version": SCHEMA_VERSION,
        "status_inputs": dict(status_inputs),
    }
    registry.validate_definition(body, "archive_body_v2", "archive_body")
    return body, t_study_through_verifier


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            _fail("short write")
        offset += written


def _current_process_resource_usage() -> tuple[int, int]:
    if _GETRUSAGE is None:
        _fail("getrusage is unavailable for archive prepublication ceiling checks")
    usage = _Rusage()
    if _GETRUSAGE(0, ctypes.byref(usage)) != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))
    cpu = (
        usage.ru_utime.tv_sec * 1_000_000
        + usage.ru_utime.tv_usec
        + usage.ru_stime.tv_sec * 1_000_000
        + usage.ru_stime.tv_usec
    )
    return cpu, usage.ru_maxrss * 1024


def _validate_archive_prepublication_resources(
    *,
    phase_start_monotonic_ns: int,
    prior_study_cpu_microseconds: int,
    prior_research_evidence_bytes: int,
    prior_archive_cpu_microseconds: int,
    prior_archive_wall_nanoseconds: int,
    request_size: int,
    archive_body_size: int,
) -> None:
    now = time.monotonic_ns()
    if phase_start_monotonic_ns > now:
        _fail("archive phase monotonic start is in the future")
    cpu, peak_rss = _current_process_resource_usage()
    wall = now - phase_start_monotonic_ns
    if prior_archive_cpu_microseconds + cpu > PHASE_CPU_CAP_MICROSECONDS:
        _fail("E_archive_body CPU ceiling crossed before publication")
    if prior_archive_wall_nanoseconds + wall > PHASE_WALL_CAP_NANOSECONDS:
        _fail("E_archive_body wall ceiling crossed before publication")
    if request_size + archive_body_size > OWNED_LIVE_TEMPORARY_CAP_BYTES:
        _fail("E_archive_body owned-live-byte ceiling crossed before publication")
    if prior_study_cpu_microseconds + cpu > STUDY_CPU_CAP_MICROSECONDS:
        _fail("global T_study CPU ceiling crossed before archive publication")
    if peak_rss > PEAK_RSS_CAP_BYTES:
        _fail("E_archive_body peak-RSS ceiling crossed before publication")
    if prior_research_evidence_bytes + archive_body_size > RESEARCH_EVIDENCE_CAP_BYTES:
        _fail("global research-evidence/archive byte ceiling crossed before publication")


def _publish_archive_body(
    root: Path,
    body: Mapping[str, Any],
    *,
    phase_start_monotonic_ns: int,
    prior_study_cpu_microseconds: int,
    prior_research_evidence_bytes: int,
    prior_archive_cpu_microseconds: int,
    prior_archive_wall_nanoseconds: int,
    request_size: int,
) -> bytes:
    payload = canonical_json_document(dict(body))
    _validate_archive_prepublication_resources(
        phase_start_monotonic_ns=phase_start_monotonic_ns,
        prior_study_cpu_microseconds=prior_study_cpu_microseconds,
        prior_research_evidence_bytes=prior_research_evidence_bytes,
        prior_archive_cpu_microseconds=prior_archive_cpu_microseconds,
        prior_archive_wall_nanoseconds=prior_archive_wall_nanoseconds,
        request_size=request_size,
        archive_body_size=len(payload),
    )
    root_descriptor = _open_artifact_root(root)
    try:
        for name in ("archive", "archive.staging"):
            try:
                os.stat(name, dir_fd=root_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                continue
            _fail("archive target or staging directory already exists")
        os.mkdir("archive.staging", 0o700, dir_fd=root_descriptor)
        staging_descriptor = os.open(
            "archive.staging",
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_descriptor,
        )
        try:
            flags = (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = os.open(
                "archive_body.json", flags, 0o600, dir_fd=staging_descriptor
            )
            try:
                _write_all(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.fsync(staging_descriptor)
        finally:
            os.close(staging_descriptor)
        _rename_noreplace(
            root_descriptor,
            "archive.staging",
            root_descriptor,
            "archive",
        )
        os.fsync(root_descriptor)
    finally:
        os.close(root_descriptor)
    published = read_immutable_artifact(
        root, "archive/archive_body.json", maximum_bytes=MAX_PRIOR_ARTIFACT_BYTES
    )
    if published != payload:
        _fail("published archive body differs from its exact canonical bytes")
    return published


def _parse_archive_control(payload: bytes) -> dict[str, Any]:
    control = dict(
        _require_mapping(
            parse_strict_json_document(
                payload, "archive control request", require_canonical=True
            ),
            "archive control request",
        )
    )
    expected_keys = {
        "archive_start_checkpoint",
        "artifact_root",
        "attempt_ledger",
        "gate_operands",
        "phase_receipts_through_verifier",
        "phase_start_monotonic_ns",
        "prior_archive_attempt_receipts",
        "prior_research_evidence_bytes",
        "prior_study_cpu_microseconds",
        "protocol",
        "resource_observation_through_verifier",
        "schema",
        "sealed_phase_identities",
        "status_inputs",
    }
    if set(control) != expected_keys:
        _fail("archive control request does not have the exact frozen key set")
    if not isinstance(control["artifact_root"], str):
        _fail("archive artifact_root is not a string")
    control["protocol"] = _sealed_file_request(control["protocol"], "protocol")
    control["schema"] = _sealed_file_request(control["schema"], "schema")
    for key in (
        "phase_start_monotonic_ns",
        "prior_research_evidence_bytes",
        "prior_study_cpu_microseconds",
    ):
        _require_nonnegative_integer(control[key], key)
    return control


def archive_and_return_identity(
    *,
    control_fd: int,
    identity_pipe_fd: int,
) -> None:
    if control_fd != CONTROL_FD or identity_pipe_fd != IDENTITY_PIPE_FD:
        _fail("archive control/identity descriptors differ from frozen fd 198/199")
    if control_fd == identity_pipe_fd:
        _fail("archive request and identity pipe descriptors must differ")
    try:
        request_payload = _read_fd_document(control_fd, "archive request", MAX_REQUEST_BYTES)
    finally:
        os.close(control_fd)
    control = _parse_archive_control(request_payload)
    protocol_payload = _read_sealed_file(
        Path(control["protocol"]["read_path"]),
        "composite protocol authority",
        expected_size_bytes=control["protocol"]["size_bytes"],
        expected_sha256=control["protocol"]["sha256"],
        maximum_bytes=MAX_SCHEMA_BYTES,
    )
    schema_payload = _read_sealed_file(
        Path(control["schema"]["read_path"]),
        "artifact schema",
        expected_size_bytes=control["schema"]["size_bytes"],
        expected_sha256=control["schema"]["sha256"],
        maximum_bytes=MAX_SCHEMA_BYTES,
    )
    if len(protocol_payload) != control["protocol"]["size_bytes"]:
        _fail("sealed composite protocol authority size changed after bootstrap")
    schema_object = _require_mapping(
        parse_strict_json_document(
            schema_payload, "artifact schema", require_canonical=False
        ),
        "artifact schema",
    )
    registry = SchemaRegistry(schema_object)
    root = _normalized_absolute_directory(Path(control["artifact_root"]), "artifact root")
    (
        manifest,
        verifier,
        identities,
        derived_control_valid,
        derived_representation_valid,
    ) = _load_prior_files(
        root,
        registry,
        control["protocol"],
        control["schema"],
    )
    body_request_keys = {
        "archive_start_checkpoint",
        "attempt_ledger",
        "gate_operands",
        "phase_receipts_through_verifier",
        "resource_observation_through_verifier",
        "sealed_phase_identities",
        "status_inputs",
    }
    body_request = {key: control[key] for key in body_request_keys}
    body, t_study_through_verifier = _validate_request_and_build_body(
        registry,
        body_request,
        manifest,
        verifier,
        identities,
        derived_control_valid,
        derived_representation_valid,
    )
    (
        prior_archive_cpu,
        prior_archive_wall,
    ) = _validate_prior_archive_attempt_receipts(
        registry,
        control["prior_archive_attempt_receipts"],
        _require_mapping(
            control["archive_start_checkpoint"], "archive start checkpoint"
        ),
    )
    resource_observation = control["resource_observation_through_verifier"]
    if (
        control["prior_study_cpu_microseconds"]
        != t_study_through_verifier + prior_archive_cpu
    ):
        _fail("trusted prior-study CPU differs from through-verifier plus prior archive receipts")
    if (
        control["prior_research_evidence_bytes"]
        != resource_observation["research_evidence_archive_bytes"]
    ):
        _fail("trusted prior evidence bytes differ from resource observation")
    published = _publish_archive_body(
        root,
        body,
        phase_start_monotonic_ns=control["phase_start_monotonic_ns"],
        prior_study_cpu_microseconds=control["prior_study_cpu_microseconds"],
        prior_archive_cpu_microseconds=prior_archive_cpu,
        prior_archive_wall_nanoseconds=prior_archive_wall,
        prior_research_evidence_bytes=control["prior_research_evidence_bytes"],
        request_size=len(request_payload),
    )
    identity = {
        "sha256": sha256_bytes(published),
        "size_bytes": len(published),
    }
    if identity_pipe_fd <= 2:
        _fail("archive identity pipe descriptor must be greater than stderr")
    try:
        os.fstat(identity_pipe_fd)
        _write_all(identity_pipe_fd, canonical_json_document(identity))
    finally:
        os.close(identity_pipe_fd)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("command", choices=("publish-canonical-request",))
    parser.add_argument("--control-fd", required=True, type=int, choices=(CONTROL_FD,))
    parser.add_argument(
        "--identity-pipe-fd", required=True, type=int, choices=(IDENTITY_PIPE_FD,)
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        archive_and_return_identity(
            control_fd=args.control_fd,
            identity_pipe_fd=args.identity_pipe_fd,
        )
    except (OSError, ArchiveContractError) as error:
        print(f"A4-V2 archive publication failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
