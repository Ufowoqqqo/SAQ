#!/usr/bin/env python3
"""Standalone source for the future one-shot isolated-clone PREP node.

This source is review-only during A4-V2-CACHE-I.  It is never imported as a
repository module.  A separately reviewed ASCII ``python -I -B -S -c``
bootstrap verifies these exact bytes, compiles them in memory, and calls
``run_from_bootstrap`` only after durable publication of the permanent START
record.  The source uses only the Python standard library and shares no helper
with the A4 producer, runner, parity conductor, verifier, SRUN, or cache-policy
verifier.

The implementation intentionally retains every partial isolation root,
journal, token, and capture.  It contains no cleanup, resume, or retry path.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import re
import resource
import selectors
import signal
import stat
import struct
import sys
import time
from typing import Any, Mapping, NoReturn, Sequence


SCHEMA_VERSION = 1

SOURCE_WORKTREE = "/tmp/saq-arbitrary-cardinality-feasibility-v2"
SOURCE_GIT_COMMON_DIR = "/rwproject/kdd-db/kluaq/saq/.git"
TOKEN_PATH = SOURCE_GIT_COMMON_DIR + "/saq-a4-v2-isolated-prep.lock"
STDOUT_CAPTURE_PATH = SOURCE_GIT_COMMON_DIR + "/saq-a4-v2-isolated-prep.stdout"
STDERR_CAPTURE_PATH = SOURCE_GIT_COMMON_DIR + "/saq-a4-v2-isolated-prep.stderr"

ISOLATION_ROOT = "/tmp/saq-a4-v2-par-r1-isolation"
OUTER_JOURNAL_DIR = ISOLATION_ROOT + "/prep-attempt"
OUTER_JOURNAL_PATH = OUTER_JOURNAL_DIR + "/clone_operations.jsonl"
CLONE_ROOT = ISOLATION_ROOT + "/repo"
EMPTY_TEMPLATE = ISOLATION_ROOT + "/empty-git-template"
GIT_HOME = ISOLATION_ROOT + "/git-home"
GIT_XDG = ISOLATION_ROOT + "/git-xdg"

RECEIPT_STAGING_RELATIVE = (
    "docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15.staging"
)
RECEIPT_FINAL_RELATIVE = (
    "docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15"
)
RECEIPT_FILE_NAMES = (
    "clone_inventory.json",
    "clone_operations.jsonl",
    "clone_postcheck.json",
    "prep_seal.json",
)

PREP_TOOL_RELATIVE = "script/a4_v2_isolated_clone_prep.py"
PREP_AUTH_RELATIVE = (
    "docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md"
)
PREP_AUTH_REVIEW_RELATIVE = (
    "docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md"
)
IMPLEMENTATION_MANIFEST_RELATIVE = (
    "docs/saq_a4_v2_implementation_manifest_2026_07_14.json"
)

BRANCH = "saq-arbitrary-cardinality-feasibility-v2"
FETCH_URL = "https://github.com/Ufowoqqqo/SAQ.git"
PUSH_URL = "git@github.com:Ufowoqqqo/SAQ.git"
REMOTE_REF = "refs/remotes/origin/" + BRANCH
LOCAL_REF = "refs/heads/" + BRANCH

ENV_PATH = "/usr/bin/env"
ENV_SHA256 = "4fa9935734560713b5a6250fa3481d1044ad117f220bf32c802af382bb7e5c9b"
ENV_SIZE = 45_088
PYTHON_PATH = "/usr/bin/python3.9"
PYTHON_SHA256 = "c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0"
PYTHON_SIZE = 15_448
BOOTSTRAP_EXTERNAL_PATH = "/usr/lib64/python3.9/importlib/_bootstrap_external.py"
BOOTSTRAP_EXTERNAL_SHA256 = (
    "8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4"
)
BOOTSTRAP_EXTERNAL_SIZE = 66_447
GIT_PATH = "/usr/bin/git"
GIT_SHA256 = "f7d0c1d79341f3d2d8e5c63f89c11400f48af55d8b659251c18cd7d13e3e4ed3"
GIT_SIZE = 4_397_352
GIT_REMOTE_HTTP_PATH = "/usr/libexec/git-core/git-remote-http"
GIT_REMOTE_HTTP_SHA256 = (
    "c2c458ee6ecadbb1b95fce9bef7f990a51f6486d06dae3621f8997757380a902"
)
GIT_REMOTE_HTTP_SIZE = 966_840
GIT_REMOTE_HTTPS_PATH = "/usr/libexec/git-core/git-remote-https"
GIT_REMOTE_HTTPS_TARGET = "git-remote-http"
GIT_EXEC_PATH = "/usr/libexec/git-core"
GIT_BUILTIN_LINK_SHA256 = (
    "c9cbed5f4adb8bff3cad9e95dcd8fa86548eb4ada0671cd9f888827308d8cf7b"
)
GIT_REMOTE_HTTPS_LINK_SHA256 = (
    "e2909ed8f8e19a7f87e0e57c2bebf7851351f3a949c5e6c60e2bf419f65bb7aa"
)

GIT_BUILTIN_LINKS = (
    "git-checkout",
    "git-config",
    "git-fetch",
    "git-fsck",
    "git-index-pack",
    "git-unpack-objects",
)
GIT_BUILTIN_LINK_TARGET = "../../bin/git"

GIT_ENVIRONMENT = {
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_EXEC_PATH": GIT_EXEC_PATH,
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "HOME": GIT_HOME,
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "XDG_CONFIG_HOME": GIT_XDG,
}
GIT_PREFIX = (
    GIT_PATH,
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.autocrlf=false",
    "-c",
    "core.eol=lf",
    "-c",
    "gc.auto=0",
    "-c",
    "maintenance.auto=false",
)
CLONE_ARGV = (
    *GIT_PREFIX,
    "clone",
    "--no-local",
    "--no-checkout",
    "--single-branch",
    "--no-tags",
    "--template=" + EMPTY_TEMPLATE,
    "--branch",
    BRANCH,
    FETCH_URL,
    CLONE_ROOT,
)

PROCESS_FAMILY_WALL_LIMIT_NS = 1_800_000_000_000
PROCESS_FAMILY_CPU_LIMIT_US = 1_800_000_000
MAXIMUM_OBSERVED_RSS_BYTES = 2_147_483_648
ISOLATION_LOGICAL_LIMIT = 1_073_741_824
ISOLATION_ALLOCATED_LIMIT = 1_073_741_824
ENTRY_LIMIT = 20_000
LIVE_PROCESS_LIMIT = 32
STREAM_CAP = 8_388_608
AGGREGATE_CAPTURE_CAP = 8_388_608
JOURNAL_BYTE_CAP = 67_108_864
JOURNAL_RECORD_CAP = 100_000
TOKEN_BYTE_CAP = 131_072
STRING_BYTE_CAP = 65_536
PIPE_MESSAGE_CAP = 67_108_864
PIPE_CHUNK = 65_536
EXEC_ERROR_BYTE_CAP = 8_192
PROCESS_SAMPLE_INTERVAL_NS = 10_000_000
FILESYSTEM_SAMPLE_INTERVAL_NS = 250_000_000
TERM_GRACE_NS = 5_000_000_000

RESOURCE_CEILINGS = {
    "canonical_string_bytes": STRING_BYTE_CAP,
    "isolation_allocated_bytes": ISOLATION_ALLOCATED_LIMIT,
    "isolation_logical_bytes": ISOLATION_LOGICAL_LIMIT,
    "journal_bytes": JOURNAL_BYTE_CAP,
    "journal_records": JOURNAL_RECORD_CAP,
    "live_process_count": LIVE_PROCESS_LIMIT,
    "maximum_observed_concurrent_process_family_rss_bytes": MAXIMUM_OBSERVED_RSS_BYTES,
    "process_family_cpu_microseconds": PROCESS_FAMILY_CPU_LIMIT_US,
    "process_family_wall_nanoseconds": PROCESS_FAMILY_WALL_LIMIT_NS,
    "stderr_aggregate_capture_bytes": AGGREGATE_CAPTURE_CAP,
    "stderr_bytes_per_child": STREAM_CAP,
    "stdout_aggregate_capture_bytes": AGGREGATE_CAPTURE_CAP,
    "stdout_bytes_per_child": STREAM_CAP,
    "total_filesystem_entries": ENTRY_LIMIT,
}

EXACT_ABSENT_PATHS = (
    "script/__pycache__",
    "script/a4_v2_archive.pyc",
    "script/a4_v2_cache_policy_verifier.pyc",
    "script/a4_v2_evidence.pyc",
    "script/a4_v2_isolated_clone_prep.pyc",
    "script/a4_v2_parity.pyc",
    "script/a4_v2_producer.pyc",
    "script/a4_v2_producer_wire.pyc",
    "script/a4_v2_runner.pyc",
    "script/a4_v2_verifier.pyc",
    "script/run_arbitrary_cardinality_a4_v2.pyc",
    "docs/saq_a4_v2_par_artifacts_2026_07_14.staging",
    "docs/saq_a4_v2_par_artifacts_2026_07_14",
    "docs/saq_a4_v2_execution_authority_2026_07_14",
    "build/a4_v2",
    "build/a4_v2_verifier",
    RECEIPT_STAGING_RELATIVE,
    RECEIPT_FINAL_RELATIVE,
)

CACHE_RELATIVE_PATHS = (
    "script/__pycache__",
    "script/a4_v2_archive.pyc",
    "script/a4_v2_cache_policy_verifier.pyc",
    "script/a4_v2_evidence.pyc",
    "script/a4_v2_isolated_clone_prep.pyc",
    "script/a4_v2_parity.pyc",
    "script/a4_v2_producer.pyc",
    "script/a4_v2_producer_wire.pyc",
    "script/a4_v2_runner.pyc",
    "script/a4_v2_verifier.pyc",
    "script/run_arbitrary_cardinality_a4_v2.pyc",
)

CLAIM_CEILING = (
    "Ephemeral isolated-clone preparation readiness only; no power-loss "
    "durability, PAR, scientific, systems, or SAQ claim."
)

CAPTURE_POLICY = {
    "aggregate_stderr_cap_bytes": AGGREGATE_CAPTURE_CAP,
    "aggregate_stdout_cap_bytes": AGGREGATE_CAPTURE_CAP,
    "format": "length_prefixed_multiplex_v1",
    "per_descendant_stderr_cap_bytes": STREAM_CAP,
    "per_descendant_stdout_cap_bytes": STREAM_CAP,
    "stderr_path": STDERR_CAPTURE_PATH,
    "stdout_path": STDOUT_CAPTURE_PATH,
}

TERMINAL_STATUSES = frozenset(
    {
        "PRECONDITION_NOT_MET",
        "RESOURCE_INCOMPLETE_NO_DECISION",
        "ARTIFACT_INVALID",
        "IMPLEMENTATION_INVALID",
        "ISOLATED_CLONE_PREPARED_PENDING_COMMIT_REVIEW",
    }
)
BOOTSTRAP_CONTEXT_KEYS = frozenset(
    {
        "append_terminal",
        "authority_checks",
        "capture_fds",
        "capture_policy",
        "execution_base_commit",
        "host_checks",
        "prologue_identity",
        "start_monotonic_ns",
        "start_process_cpu_microseconds",
        "start_time_clock_ticks",
        "terminal_state",
        "token_start_identity",
    }
)

RECEIPT_INVENTORY_KEYS = frozenset(
    {
        "absent_paths",
        "artifact_kind",
        "clone_identity",
        "execution_base_commit",
        "execution_base_tree",
        "git_admin",
        "git_environment",
        "host_executables",
        "resource_ceilings",
        "schema_version",
        "source_manifest_identity",
        "source_tree_sha256",
        "tracked_worktree",
    }
)
JOURNAL_RECORD_KEYS = frozenset(
    {
        "argv",
        "cwd",
        "detail_sha256",
        "environment_sha256",
        "exit_code",
        "filesystem_snapshot_identity",
        "monotonic_ns",
        "operation",
        "previous_record_sha256",
        "record_type",
        "resource_snapshot",
        "schema_version",
        "sequence",
        "signal_number",
        "status",
        "stderr_identity",
        "stdout_identity",
    }
)
POSTCHECK_KEYS = frozenset(
    {
        "artifact_kind",
        "cache_paths",
        "checkpoint",
        "claim_ceiling",
        "clone_identity",
        "journal_copy_equal",
        "journal_identity",
        "pre_document_resource_snapshot",
        "process_closure",
        "receipt_state",
        "schema_version",
        "source_tree_sha256",
    }
)
PREP_SEAL_KEYS = frozenset(
    {
        "artifact_kind",
        "claim_ceiling",
        "clone_inventory",
        "clone_operations",
        "clone_postcheck",
        "execution_base_commit",
        "execution_base_tree",
        "journal_copy_equal",
        "meter_start",
        "meter_stop",
        "resource_ledger",
        "schema_version",
        "source_manifest_identity",
        "source_tree_sha256",
        "tail_duration",
        "tail_rss",
    }
)

JOURNAL_OPERATIONS = frozenset(
    {
        "CHECKOUT_EXECUTION_BASE",
        "CLONE_NO_CHECKOUT",
        "COPY_OUTER_JOURNAL",
        "CREATE_GIT_ENVIRONMENT",
        "CREATE_NAMESPACE",
        "READY_FOR_RECEIPT_INSTALL",
        "SAMPLE_RESOURCES",
        "SET_FETCH_URL",
        "SET_PUSH_URL",
        "TERMINATE_PROCESS_GROUP",
        "VALIDATE_POSTCHECKOUT",
        "VALIDATE_PRECHECKOUT",
        "WRITE_CLONE_INVENTORY",
        "WRITE_CLONE_POSTCHECK",
    }
)

HEX_40 = re.compile(r"[0-9a-f]{40}\Z")
HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z")
RELATIVE_PATH = re.compile(r"(?:[A-Za-z0-9._-]+)(?:/[A-Za-z0-9._-]+)*\Z")

_LIBC = ctypes.CDLL(None, use_errno=True)
_PRCTL = _LIBC.prctl
_PRCTL.argtypes = [
    ctypes.c_int,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
]
_PRCTL.restype = ctypes.c_int
_RENAMEAT2 = _LIBC.renameat2
_RENAMEAT2.argtypes = [
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_uint,
]
_RENAMEAT2.restype = ctypes.c_int
PR_SET_CHILD_SUBREAPER = 36
PR_GET_CHILD_SUBREAPER = 37
RENAME_NOREPLACE = 1


class PrepFailure(RuntimeError):
    """Typed caught failure that must close the permanent terminal token."""

    def __init__(self, status: str, code: str, detail: str):
        if status not in TERMINAL_STATUSES:
            raise RuntimeError("internal PREP status is outside terminal enum")
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail


class PrepPrecondition(PrepFailure):
    def __init__(self, code: str, detail: str):
        super().__init__("PRECONDITION_NOT_MET", code, detail)


class PrepResource(PrepFailure):
    def __init__(self, code: str, detail: str):
        super().__init__("RESOURCE_INCOMPLETE_NO_DECISION", code, detail)


class PrepArtifact(PrepFailure):
    def __init__(self, code: str, detail: str):
        super().__init__("ARTIFACT_INVALID", code, detail)


class PrepImplementation(PrepFailure):
    def __init__(self, code: str, detail: str):
        super().__init__("IMPLEMENTATION_INVALID", code, detail)


PREPARATION_STATUS_PRECEDENCE = {
    "PRECONDITION_NOT_MET": 2,
    "RESOURCE_INCOMPLETE_NO_DECISION": 4,
    "ARTIFACT_INVALID": 5,
    "IMPLEMENTATION_INVALID": 6,
}


def _merge_failure(
    current: PrepFailure | None, candidate: PrepFailure | None
) -> PrepFailure | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    try:
        current_rank = PREPARATION_STATUS_PRECEDENCE[current.status]
        candidate_rank = PREPARATION_STATUS_PRECEDENCE[candidate.status]
    except KeyError as error:
        raise PrepImplementation(
            "FAILURE_PRECEDENCE_STATUS", "failure status is outside precedence"
        ) from error
    return candidate if candidate_rank < current_rank else current


def _fail(status: str, code: str, detail: str) -> NoReturn:
    raise PrepFailure(status, code, detail)


def _require_text(
    value: Any,
    description: str,
    *,
    maximum: int = STRING_BYTE_CAP,
    ascii_only: bool = False,
) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise PrepImplementation("INVALID_TEXT", f"{description} is not text")
    try:
        payload = value.encode("ascii" if ascii_only else "utf-8", errors="strict")
    except UnicodeError as error:
        raise PrepImplementation(
            "INVALID_TEXT_ENCODING", f"{description} has forbidden encoding"
        ) from error
    if len(payload) > maximum:
        raise PrepImplementation("TEXT_CAP", f"{description} exceeds cap")
    return value


def _require_uint(value: Any, description: str, maximum: int = (1 << 63) - 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise PrepImplementation("INVALID_INTEGER", f"{description} is not bounded uint")
    return value


def _require_sha256(value: Any, description: str) -> str:
    text = _require_text(value, description, maximum=64, ascii_only=True)
    if HEX_64.fullmatch(text) is None:
        raise PrepImplementation("INVALID_SHA256", f"{description} is not SHA-256")
    return text


def _require_oid(value: Any, description: str) -> str:
    text = _require_text(value, description, maximum=40, ascii_only=True)
    if HEX_40.fullmatch(text) is None:
        raise PrepImplementation("INVALID_GIT_OID", f"{description} is not Git OID")
    return text


def _require_relative(value: Any, description: str) -> str:
    text = _require_text(value, description, maximum=512)
    if RELATIVE_PATH.fullmatch(text) is None or any(
        component in {"", ".", ".."} for component in text.split("/")
    ):
        raise PrepImplementation("INVALID_PATH", f"{description} is not relative POSIX")
    return text


def _external_text(
    value: Any,
    description: str,
    *,
    maximum: int = STRING_BYTE_CAP,
    ascii_only: bool = False,
) -> str:
    try:
        return _require_text(
            value, description, maximum=maximum, ascii_only=ascii_only
        )
    except PrepImplementation as error:
        raise PrepArtifact(
            "EXTERNAL_TEXT_FIELD", f"{description} is invalid: {error.detail}"
        ) from error


def _external_oid(value: Any, description: str) -> str:
    try:
        return _require_oid(value, description)
    except PrepImplementation as error:
        raise PrepArtifact(
            "EXTERNAL_OID_FIELD", f"{description} is invalid: {error.detail}"
        ) from error


def _external_relative(value: Any, description: str) -> str:
    try:
        return _require_relative(value, description)
    except PrepImplementation as error:
        raise PrepArtifact(
            "EXTERNAL_PATH_FIELD", f"{description} is invalid: {error.detail}"
        ) from error


def _external_uint(value: Any, description: str) -> int:
    try:
        return _require_uint(value, description)
    except PrepImplementation as error:
        raise PrepArtifact(
            "EXTERNAL_UINT_FIELD", f"{description} is invalid: {error.detail}"
        ) from error


def _external_sha256(value: Any, description: str) -> str:
    try:
        return _require_sha256(value, description)
    except PrepImplementation as error:
        raise PrepArtifact(
            "EXTERNAL_SHA256_FIELD", f"{description} is invalid: {error.detail}"
        ) from error


def _validate_json_value(value: Any, location: str = "$") -> None:
    if value is None or isinstance(value, (bool, int, str)):
        if isinstance(value, str):
            _require_text(value, location)
        return
    if isinstance(value, list):
        if len(value) > JOURNAL_RECORD_CAP:
            raise PrepImplementation("JSON_COUNT_CAP", f"{location} list exceeds cap")
        for index, item in enumerate(value):
            _validate_json_value(item, f"{location}[{index}]")
        return
    if isinstance(value, dict):
        if len(value) > JOURNAL_RECORD_CAP:
            raise PrepImplementation("JSON_COUNT_CAP", f"{location} object exceeds cap")
        for key, item in value.items():
            _require_text(key, f"{location} key", maximum=256)
            _validate_json_value(item, f"{location}.{key}")
        return
    raise PrepImplementation("JSON_TYPE", f"{location} has forbidden JSON type")


def _canonical_body(value: Any) -> bytes:
    _validate_json_value(value)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_document(value: Any) -> bytes:
    return _canonical_body(value) + b"\n"


def _parse_canonical_document(payload: bytes, description: str) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in values:
            if key in result:
                raise PrepArtifact(
                    "DUPLICATE_JSON_KEY", f"duplicate key in {description}: {key}"
                )
            result[key] = item
        return result

    def reject(token: str) -> NoReturn:
        raise PrepArtifact(
            "FORBIDDEN_JSON_NUMBER", f"forbidden token in {description}: {token}"
        )

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
            parse_float=reject,
            parse_constant=reject,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as error:
        raise PrepArtifact("INVALID_JSON", f"invalid {description}: {error}") from error
    _validate_json_value(value)
    if _canonical_document(value) != payload:
        raise PrepArtifact("NONCANONICAL_JSON", f"{description} is not canonical")
    return value


def _write_all(descriptor: int, payload: bytes) -> tuple[int, int]:
    offset = 0
    count = 0
    while offset < len(payload):
        try:
            written = os.write(descriptor, payload[offset : offset + PIPE_CHUNK])
        except OSError as error:
            raise PrepResource("WRITE_FAILED", f"bounded write failed: {error}") from error
        if written <= 0:
            raise PrepImplementation("WRITE_NO_PROGRESS", "write made no progress")
        offset += written
        count += 1
    return count, offset


def _read_fd_bounded(descriptor: int, maximum: int, description: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        try:
            chunk = os.read(descriptor, min(PIPE_CHUNK, maximum + 1 - total))
        except OSError as error:
            raise PrepResource("READ_FAILED", f"{description} read failed: {error}") from error
        if not chunk:
            break
        total += len(chunk)
        if total > maximum:
            raise PrepResource("READ_CAP", f"{description} exceeds cap")
        chunks.append(chunk)
    return b"".join(chunks)


def _identity(payload: bytes) -> dict[str, Any]:
    return {"sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}


def _file_identity(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, **_identity(payload)}


def _open_absolute_dir(path: str) -> int:
    if not path.startswith("/") or os.path.normpath(path) != path:
        raise PrepImplementation("INVALID_ABSOLUTE_PATH", "directory path not normalized")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open("/", flags)
    try:
        for component in path.split("/")[1:]:
            if not component:
                continue
            next_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_relative_dir(root_fd: int, relative: str) -> int:
    relative = _require_relative(relative, "relative directory")
    descriptor = os.dup(root_fd)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        for component in relative.split("/"):
            next_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_relative_regular(
    root_fd: int,
    relative: str,
    *,
    maximum: int,
    description: str,
) -> tuple[bytes, os.stat_result]:
    relative = _require_relative(relative, description)
    parts = relative.split("/")
    parent_fd = os.dup(root_fd)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_size < 0
                or before.st_size > maximum
            ):
                raise PrepArtifact(
                    "FILE_TYPE_OR_SIZE", f"{description} is not bounded regular"
                )
            payload = bytearray()
            while len(payload) < before.st_size:
                chunk = os.read(
                    descriptor, min(1 << 20, before.st_size - len(payload))
                )
                if not chunk:
                    break
                payload.extend(chunk)
            if len(payload) != before.st_size or os.read(descriptor, 1):
                raise PrepArtifact("FILE_SIZE_CHANGED", f"{description} size changed")
            after = os.fstat(descriptor)
            if (
                before.st_dev,
                before.st_ino,
                before.st_mode,
                before.st_size,
                before.st_mtime_ns,
            ) != (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise PrepArtifact("FILE_MUTATED", f"{description} mutated")
            return bytes(payload), after
        finally:
            os.close(descriptor)
    finally:
        os.close(parent_fd)


def _read_absolute_regular(
    path: str, *, maximum: int, description: str
) -> tuple[bytes, os.stat_result]:
    parent, leaf = os.path.split(path)
    parent_fd = _open_absolute_dir(parent)
    try:
        return _read_relative_regular(
            parent_fd, leaf, maximum=maximum, description=description
        )
    finally:
        os.close(parent_fd)


def _mkdir_new(
    parent_fd: int,
    name: str,
    counters: dict[str, int],
    *,
    exists_is_precondition: bool = False,
) -> int:
    if "/" in name or name in {"", ".", ".."}:
        raise PrepImplementation("INVALID_MKDIR_NAME", "mkdir leaf is invalid")
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
    except OSError as error:
        if error.errno == errno.EEXIST:
            if exists_is_precondition:
                raise PrepPrecondition(
                    "DESTINATION_EXISTS", f"destination already exists: {name}"
                )
            raise PrepArtifact(
                "POST_ROOT_DIRECTORY_COLLISION",
                f"owned post-root directory path already exists: {name}",
            )
        raise PrepResource("MKDIR_FAILED", f"mkdir failed for {name}: {error}") from error
    counters["supervisor_directory_create_count"] += 1
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=parent_fd,
    )
    metadata = os.fstat(descriptor)
    if (
        metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        os.close(descriptor)
        raise PrepArtifact("DIRECTORY_IDENTITY", f"created directory identity differs: {name}")
    os.fsync(parent_fd)
    counters["supervisor_directory_fsync_count"] += 1
    return descriptor


def _create_new_file(
    parent_fd: int,
    name: str,
    payload: bytes,
    counters: dict[str, int],
) -> dict[str, Any]:
    if "/" in name or name in {"", ".", ".."}:
        raise PrepImplementation("INVALID_FILE_NAME", "file leaf is invalid")
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=parent_fd,
        )
    except FileExistsError as error:
        raise PrepArtifact(
            "POST_ROOT_FILE_COLLISION",
            f"owned post-root file path already exists: {name}",
        ) from error
    except OSError as error:
        raise PrepResource(
            "FILE_CREATE_FAILED", f"file creation failed for {name}: {error}"
        ) from error
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        counters["supervisor_file_fsync_count"] += 1
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_uid != os.geteuid()
            or metadata.st_size != len(payload)
        ):
            raise PrepArtifact("FILE_PUBLICATION_IDENTITY", f"new file differs: {name}")
    finally:
        os.close(descriptor)
    counters["supervisor_file_create_count"] += 1
    return _file_identity(name, payload)


def _fsync_dir(descriptor: int, counters: dict[str, int]) -> None:
    os.fsync(descriptor)
    counters["supervisor_directory_fsync_count"] += 1


def _bounded_sorted_entry_names(
    directory_fd: int,
    already_discovered: int,
    description: str,
    *,
    excluded: frozenset[str] = frozenset(),
) -> list[str]:
    names: list[str] = []
    try:
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                name = _external_text(
                    entry.name, description + " entry name", maximum=512
                )
                if name in excluded:
                    continue
                names.append(name)
                actual = already_discovered + len(names)
                if actual > ENTRY_LIMIT:
                    raise PrepResource(
                        "DIRECTORY_ENTRY_CEILING",
                        f"{description} crossed entry ceiling at {actual}",
                    )
    except PrepFailure:
        raise
    except OSError as error:
        raise PrepResource(
            "DIRECTORY_SCAN_FAILED", f"{description} scan failed: {error}"
        ) from error
    names.sort(key=lambda value: value.encode("utf-8"))
    return names


def _process_cpu_microseconds() -> int:
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    value = (
        own.ru_utime
        + own.ru_stime
        + children.ru_utime
        + children.ru_stime
    )
    result = int(value * 1_000_000)
    if result < 0:
        raise PrepImplementation("NEGATIVE_CPU", "process-family CPU is negative")
    return result


def _proc_stat(pid: int) -> dict[str, int]:
    descriptor = os.open(
        f"/proc/{pid}/stat", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        payload = _read_fd_bounded(descriptor, 65_536, f"PID {pid} stat")
    finally:
        os.close(descriptor)
    opening = payload.find(b"(")
    closing = payload.rfind(b") ")
    if opening <= 0 or closing <= opening:
        raise PrepArtifact("PROC_STAT_FRAMING", f"PID {pid} stat is ambiguous")
    fields = payload[closing + 2 :].strip().split()
    if len(fields) < 22:
        raise PrepArtifact("PROC_STAT_FIELDS", f"PID {pid} stat is truncated")
    try:
        ppid = int(fields[1])
        pgid = int(fields[2])
        user_ticks = int(fields[11])
        system_ticks = int(fields[12])
        start = int(fields[19])
        rss_pages = int(fields[21])
    except ValueError as error:
        raise PrepArtifact("PROC_STAT_NUMBER", f"PID {pid} stat number invalid") from error
    if (
        ppid < 0
        or pgid <= 0
        or user_ticks < 0
        or system_ticks < 0
        or start < 0
        or rss_pages < 0
    ):
        raise PrepArtifact("PROC_STAT_RANGE", f"PID {pid} stat number out of range")
    return {
        "ppid": ppid,
        "process_group_id": pgid,
        "cpu_clock_ticks": user_ticks + system_ticks,
        "rss_bytes": rss_pages * os.sysconf("SC_PAGE_SIZE"),
        "start_time_clock_ticks": start,
    }


def _proc_io(pid: int) -> dict[str, int] | None:
    try:
        descriptor = os.open(
            f"/proc/{pid}/io", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
    except OSError:
        return None
    try:
        payload = _read_fd_bounded(descriptor, 65_536, f"PID {pid} io")
    except PrepFailure:
        return None
    finally:
        os.close(descriptor)
    values: dict[str, int] = {}
    for line in payload.splitlines():
        if b":" not in line:
            return None
        raw_key, raw_value = line.split(b":", 1)
        try:
            key = raw_key.decode("ascii")
            text = raw_value.strip().decode("ascii")
        except UnicodeError:
            return None
        if DECIMAL.fullmatch(text) is None:
            return None
        values[key] = int(text)
    keys = (
        "cancelled_write_bytes",
        "rchar",
        "read_bytes",
        "syscr",
        "syscw",
        "wchar",
        "write_bytes",
    )
    if any(key not in values for key in keys):
        return None
    return {key: values[key] for key in keys}


def _wait_record(
    pid: int,
    raw_status: int,
    usage: resource.struct_rusage,
    proc_io: Mapping[str, int] | None,
) -> dict[str, Any]:
    exit_code: int | None = None
    signal_number: int | None = None
    if os.WIFEXITED(raw_status):
        exit_code = os.WEXITSTATUS(raw_status)
    elif os.WIFSIGNALED(raw_status):
        signal_number = os.WTERMSIG(raw_status)
    maximum_rss = int(usage.ru_maxrss)
    user_cpu = int(usage.ru_utime * 1_000_000)
    system_cpu = int(usage.ru_stime * 1_000_000)
    if maximum_rss < 0 or user_cpu < 0 or system_cpu < 0:
        raise PrepImplementation("NEGATIVE_WAIT_RESOURCE", "wait resource is negative")
    return {
        "exit_code": exit_code,
        "pid": pid,
        "proc_io": dict(proc_io) if proc_io is not None else None,
        "raw_wait_status": raw_status,
        "ru_maxrss_bytes": maximum_rss * 1024,
        "signal_number": signal_number,
        "system_cpu_microseconds": system_cpu,
        "user_cpu_microseconds": user_cpu,
    }


def _validated_wait_record(
    value: Mapping[str, Any], *, expected_pid: int
) -> dict[str, Any]:
    expected_keys = {
        "exit_code",
        "pid",
        "proc_io",
        "raw_wait_status",
        "ru_maxrss_bytes",
        "signal_number",
        "system_cpu_microseconds",
        "user_cpu_microseconds",
    }
    if set(value) != expected_keys:
        raise PrepImplementation("WAIT_RECORD_SHAPE", "wait record shape differs")
    if _require_uint(value["pid"], "wait PID") != expected_pid:
        raise PrepImplementation("WAIT_RECORD_PID", "wait record PID differs")
    exit_code = value["exit_code"]
    signal_number = value["signal_number"]
    if exit_code is not None:
        _require_uint(exit_code, "wait exit code", 255)
    if signal_number is not None:
        _require_uint(signal_number, "wait signal number", 255)
    if (exit_code is None) == (signal_number is None):
        raise PrepImplementation(
            "WAIT_RECORD_OUTCOME", "wait record outcome is not exactly one terminal state"
        )
    for key in (
        "raw_wait_status",
        "ru_maxrss_bytes",
        "system_cpu_microseconds",
        "user_cpu_microseconds",
    ):
        _require_uint(value[key], "wait record " + key)
    proc_io = value["proc_io"]
    if proc_io is not None:
        expected_io = {
            "cancelled_write_bytes",
            "rchar",
            "read_bytes",
            "syscr",
            "syscw",
            "wchar",
            "write_bytes",
        }
        if not isinstance(proc_io, dict) or set(proc_io) != expected_io:
            raise PrepImplementation("WAIT_RECORD_IO", "wait proc-io shape differs")
        for key in expected_io:
            _require_uint(proc_io[key], "wait proc-io " + key)
    return dict(value)


def _empty_operation_counts() -> dict[str, int]:
    return {
        "completed_capture_write_bytes": 0,
        "completed_capture_write_syscall_count": 0,
        "directory_entry_count": 0,
        "file_entry_count": 0,
        "reaped_process_count": 0,
        "spawned_process_count": 0,
        "supervisor_directory_create_count": 0,
        "supervisor_directory_fsync_count": 0,
        "supervisor_file_create_count": 0,
        "supervisor_file_fsync_count": 0,
    }


def _empty_storage_category() -> dict[str, int]:
    return {"allocated_bytes": 0, "entry_count": 0, "logical_bytes": 0}


def _empty_storage_ledger() -> dict[str, dict[str, int]]:
    return {
        key: _empty_storage_category()
        for key in (
            "directories",
            "git_loose_objects",
            "git_other_admin",
            "git_pack_payloads",
            "receipt",
            "temporary",
            "tracked_checkout",
        )
    }


def _classify_storage(relative: str, metadata: os.stat_result) -> str:
    if stat.S_ISDIR(metadata.st_mode):
        return "directories"
    if relative.startswith("repo/.git/objects/pack/"):
        return "git_pack_payloads"
    if relative.startswith("repo/.git/objects/"):
        return "git_loose_objects"
    if relative.startswith("repo/.git/"):
        return "git_other_admin"
    if (
        relative.startswith("repo/" + RECEIPT_FINAL_RELATIVE + "/")
        or relative.startswith("repo/" + RECEIPT_STAGING_RELATIVE + "/")
    ):
        return "receipt"
    if (
        relative.startswith("prep-attempt/")
        or (
            not stat.S_ISDIR(metadata.st_mode)
            and relative.startswith(("git-home/", "git-xdg/", "empty-git-template/"))
        )
    ):
        return "temporary"
    return "tracked_checkout"


def _scan_tree(root: str) -> tuple[dict[str, Any], dict[str, dict[str, int]]]:
    root_fd = _open_absolute_dir(root)
    root_stat = os.fstat(root_fd)
    pinned_device = root_stat.st_dev
    pinned_uid = os.geteuid()
    entry_count = 0
    discovered_count = 0
    logical = 0
    allocated = 0
    inventory_hash = hashlib.sha256()
    inventory_hash.update(b"[")
    storage = _empty_storage_ledger()

    def visit(directory_fd: int, relative: str) -> None:
        nonlocal entry_count, discovered_count, logical, allocated
        names = _bounded_sorted_entry_names(
            directory_fd,
            discovered_count,
            "isolation tree",
        )
        discovered_count += len(names)
        for name in names:
            path = name if not relative else relative + "/" + name
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if metadata.st_dev != pinned_device or metadata.st_uid != pinned_uid:
                raise PrepArtifact("TREE_DEVICE_OWNER", f"tree device/owner differs: {path}")
            if stat.S_ISLNK(metadata.st_mode):
                raise PrepArtifact("TREE_SYMLINK", f"physical tree contains symlink: {path}")
            if not stat.S_ISDIR(metadata.st_mode) and not stat.S_ISREG(metadata.st_mode):
                raise PrepArtifact("TREE_TYPE", f"physical tree type forbidden: {path}")
            category = _classify_storage(path, metadata)
            storage[category]["entry_count"] += 1
            storage[category]["logical_bytes"] += int(metadata.st_size)
            storage[category]["allocated_bytes"] += int(metadata.st_blocks) * 512
            record = {
                "allocated_bytes": int(metadata.st_blocks) * 512,
                "device_id": int(metadata.st_dev),
                "inode": int(metadata.st_ino),
                "logical_bytes": int(metadata.st_size),
                "mode_octal": f"{stat.S_IMODE(metadata.st_mode):04o}",
                "path": path,
                "type": "directory" if stat.S_ISDIR(metadata.st_mode) else "regular",
                "uid": int(metadata.st_uid),
            }
            if entry_count:
                inventory_hash.update(b",")
            inventory_hash.update(_canonical_body(record))
            entry_count += 1
            logical += record["logical_bytes"]
            allocated += record["allocated_bytes"]
            if (
                entry_count > ENTRY_LIMIT
                or logical > ISOLATION_LOGICAL_LIMIT
                or allocated > ISOLATION_ALLOCATED_LIMIT
            ):
                raise PrepResource(
                    "TREE_RESOURCE_CEILING",
                    "physical tree crossed an entry or byte ceiling: "
                    f"entries={entry_count},logical={logical},allocated={allocated}",
                )
            if stat.S_ISDIR(metadata.st_mode):
                child_fd = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=directory_fd,
                )
                try:
                    visit(child_fd, path)
                finally:
                    os.close(child_fd)

    try:
        visit(root_fd, "")
    finally:
        os.close(root_fd)
    inventory_hash.update(b"]")
    inventory_sha = inventory_hash.hexdigest()
    return (
        {
            "allocated_bytes": allocated,
            "entry_count": entry_count,
            "inventory_sha256": inventory_sha,
            "logical_bytes": logical,
        },
        storage,
    )


class HashJournal:
    """Append-only, fsynced canonical JSONL with a previous-record chain."""

    def __init__(self, descriptor: int, path: str, counters: dict[str, int]):
        self.descriptor = descriptor
        self.path = path
        self.counters = counters
        self.sequence = 0
        self.previous: str | None = None
        self.size_bytes = 0
        self.closed = False
        self.close_attempted = False
        self.close_failure: PrepFailure | None = None

    def append(
        self,
        *,
        record_type: str,
        operation: str,
        argv: list[str] | None,
        cwd: str,
        environment_sha256: str,
        status: str,
        exit_code: int | None,
        signal_number: int | None,
        stdout_identity: Mapping[str, Any] | None,
        stderr_identity: Mapping[str, Any] | None,
        filesystem_snapshot_identity: Mapping[str, Any] | None,
        resource_snapshot: Mapping[str, Any],
        detail: str,
    ) -> str:
        if self.closed or self.close_attempted:
            raise PrepImplementation("JOURNAL_CLOSED", "journal append after close")
        if self.sequence >= JOURNAL_RECORD_CAP:
            raise PrepResource("JOURNAL_RECORD_CAP", "journal record cap exceeded")
        if record_type not in {"INTENT", "RESULT", "SAMPLE", "READY_FOR_RECEIPT_INSTALL"}:
            raise PrepImplementation("JOURNAL_RECORD_TYPE", "journal record type invalid")
        if status not in {"PENDING", "OK", "FAILED", "OBSERVED", "READY"}:
            raise PrepImplementation("JOURNAL_STATUS", "journal status invalid")
        if operation not in JOURNAL_OPERATIONS:
            raise PrepImplementation("JOURNAL_OPERATION", "journal operation invalid")
        if argv is not None:
            if not isinstance(argv, list) or len(argv) > 64:
                raise PrepImplementation("JOURNAL_ARGV_COUNT", "journal argv exceeds cap")
            for index, argument in enumerate(argv):
                _require_text(
                    argument,
                    f"journal argv[{index}]",
                    maximum=512,
                    ascii_only=True,
                )
        detail_payload = _require_text(detail, "journal detail", maximum=4_096).encode(
            "utf-8"
        )
        record = {
            "argv": argv,
            "cwd": cwd,
            "detail_sha256": hashlib.sha256(detail_payload).hexdigest(),
            "environment_sha256": _require_sha256(
                environment_sha256, "journal environment SHA-256"
            ),
            "exit_code": exit_code,
            "filesystem_snapshot_identity": filesystem_snapshot_identity,
            "monotonic_ns": time.monotonic_ns(),
            "operation": _require_text(operation, "journal operation", maximum=512),
            "previous_record_sha256": self.previous,
            "record_type": record_type,
            "resource_snapshot": dict(resource_snapshot),
            "schema_version": SCHEMA_VERSION,
            "sequence": self.sequence,
            "signal_number": signal_number,
            "status": status,
            "stderr_identity": stderr_identity,
            "stdout_identity": stdout_identity,
        }
        if set(record) != JOURNAL_RECORD_KEYS:
            raise PrepImplementation("JOURNAL_SHAPE", "journal record key closure differs")
        payload = _canonical_document(record)
        if self.size_bytes + len(payload) > JOURNAL_BYTE_CAP:
            raise PrepResource("JOURNAL_BYTE_CAP", "journal byte cap exceeded")
        _write_all(self.descriptor, payload)
        os.fsync(self.descriptor)
        self.counters["supervisor_file_fsync_count"] += 1
        self.size_bytes += len(payload)
        self.previous = hashlib.sha256(payload).hexdigest()
        self.sequence += 1
        return self.previous

    def close(self) -> None:
        if self.close_attempted:
            if self.close_failure is not None:
                raise self.close_failure
            return
        self.close_attempted = True
        failure: PrepFailure | None = None
        try:
            os.fsync(self.descriptor)
            self.counters["supervisor_file_fsync_count"] += 1
        except BaseException as error:
            failure = _normalize_caught_failure(
                error,
                os_code="JOURNAL_FSYNC_OS_FAILURE",
                resource_code="JOURNAL_FSYNC_RESOURCE_FAILURE",
                implementation_code="JOURNAL_FSYNC_INVALID",
            )
        try:
            os.close(self.descriptor)
        except OSError as error:
            failure = _merge_failure(
                failure, PrepResource("JOURNAL_CLOSE_OS_FAILURE", str(error))
            )
        else:
            self.closed = True
        self.close_failure = failure
        if failure is not None:
            raise failure


class CaptureWriter:
    """Writer for the fixed length-prefixed multiplex aggregate sidecars."""

    HEADER = struct.Struct(">QBBI")

    def __init__(
        self,
        stdout_fd: int,
        stderr_fd: int,
        terminal_state: dict[str, Any],
    ):
        self.descriptors = {1: stdout_fd, 2: stderr_fd}
        self.terminal_state = terminal_state
        self.logical = {1: 0, 2: 0}
        self.write_count = {1: 0, 2: 0}
        self.write_bytes = {1: 0, 2: 0}
        self.closed = False
        self.close_attempted = False
        self.close_failure: PrepFailure | None = None
        self.closed_identities: tuple[dict[str, Any], dict[str, Any]] | None = None
        self.unresolved_streams: set[int] = set()

    def write(self, pid: int, stream: int, payload: bytes) -> None:
        if (
            self.closed
            or self.close_attempted
            or stream not in self.descriptors
            or not 0 < pid < (1 << 63)
        ):
            raise PrepImplementation("CAPTURE_FRAME", "capture frame is invalid")
        if len(payload) > PIPE_CHUNK:
            raise PrepImplementation("CAPTURE_CHUNK", "capture chunk exceeds 65536")
        frame = self.HEADER.pack(pid, stream, 0, len(payload)) + payload
        if self.logical[stream] + len(frame) > AGGREGATE_CAPTURE_CAP:
            raise PrepResource("CAPTURE_AGGREGATE_CAP", "aggregate capture cap exceeded")
        count, written = _write_all(self.descriptors[stream], frame)
        self.logical[stream] += written
        self.write_count[stream] += count
        self.write_bytes[stream] += written
        prefix = "stdout" if stream == 1 else "stderr"
        self.terminal_state[prefix + "_capture_write_syscall_count"] = self.write_count[
            stream
        ]
        self.terminal_state[prefix + "_capture_write_bytes"] = self.write_bytes[stream]

    def close_and_identify(self) -> tuple[dict[str, Any], dict[str, Any]]:
        if self.close_attempted:
            raise PrepImplementation("CAPTURE_DOUBLE_CLOSE", "captures closed twice")
        self.close_attempted = True
        identities: list[dict[str, Any]] = []
        first_error: PrepFailure | None = None
        for stream, path in ((1, STDOUT_CAPTURE_PATH), (2, STDERR_CAPTURE_PATH)):
            descriptor = self.descriptors[stream]
            try:
                os.fsync(descriptor)
                prefix = "stdout" if stream == 1 else "stderr"
                self.terminal_state[prefix + "_capture_file_fsync_count"] = (
                    self.terminal_state.get(prefix + "_capture_file_fsync_count", 1) + 1
                )
                metadata = os.fstat(descriptor)
                if metadata.st_size != self.logical[stream]:
                    raise PrepArtifact("CAPTURE_SIZE", "capture size differs")
            except BaseException as error:
                first_error = _merge_failure(
                    first_error,
                    _normalize_caught_failure(
                        error,
                        os_code="CAPTURE_FSYNC_OS_FAILURE",
                        resource_code="CAPTURE_FSYNC_RESOURCE_FAILURE",
                        implementation_code="CAPTURE_FSYNC_INVALID",
                    ),
                )
            finally:
                try:
                    os.close(descriptor)
                except OSError as error:
                    self.unresolved_streams.add(stream)
                    first_error = _merge_failure(
                        first_error,
                        PrepResource("CAPTURE_CLOSE_OS_FAILURE", str(error)),
                    )
            try:
                payload, _ = _read_absolute_regular(
                    path, maximum=AGGREGATE_CAPTURE_CAP, description="closed capture"
                )
                identities.append(_file_identity(path, payload))
            except BaseException as error:
                first_error = _merge_failure(
                    first_error,
                    _normalize_caught_failure(
                        error,
                        os_code="CAPTURE_IDENTITY_OS_FAILURE",
                        resource_code="CAPTURE_IDENTITY_RESOURCE_FAILURE",
                        implementation_code="CAPTURE_IDENTITY_INVALID",
                    ),
                )
        self.closed = not self.unresolved_streams
        if len(identities) == 2:
            self.closed_identities = (identities[0], identities[1])
        if len(identities) != 2:
            first_error = _merge_failure(
                first_error,
                PrepImplementation(
                    "CAPTURE_IDENTITY_COUNT", "capture identity count differs"
                ),
            )
        self.close_failure = first_error
        if first_error is not None:
            raise first_error
        return identities[0], identities[1]


def _readlink_absolute(path: str, description: str) -> tuple[str, os.stat_result]:
    parent, leaf = os.path.split(path)
    parent_fd = _open_absolute_dir(parent)
    try:
        metadata = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISLNK(metadata.st_mode):
            raise PrepArtifact("SYMLINK_TYPE", f"{description} is not a symlink")
        target = os.readlink(leaf, dir_fd=parent_fd)
        _external_text(target, description, maximum=512, ascii_only=True)
        after = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        if (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_size,
            metadata.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise PrepArtifact("SYMLINK_MUTATED", f"{description} changed")
        return target, after
    finally:
        os.close(parent_fd)


def _regular_host_identity(
    path: str, expected_sha256: str, expected_size: int
) -> dict[str, Any]:
    payload, metadata = _read_absolute_regular(
        path, maximum=8_388_608, description=f"host executable {path}"
    )
    observed = _file_identity(path, payload)
    if (
        metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) & 0o111 == 0
        or len(payload) != expected_size
        or observed["sha256"] != expected_sha256
    ):
        raise PrepArtifact("HOST_EXECUTABLE_IDENTITY", f"host executable differs: {path}")
    return {
        "path": path,
        "sha256": observed["sha256"],
        "size_bytes": observed["size_bytes"],
        "symlink_target": None,
        "type": "REGULAR",
    }


def _symlink_host_identity(
    path: str, expected_target: str, expected_sha256: str
) -> dict[str, Any]:
    target, metadata = _readlink_absolute(path, f"host symlink {path}")
    payload = target.encode("ascii")
    if (
        metadata.st_uid != 0
        or target != expected_target
        or hashlib.sha256(payload).hexdigest() != expected_sha256
    ):
        raise PrepArtifact("HOST_SYMLINK_IDENTITY", f"host symlink differs: {path}")
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "symlink_target": target,
        "type": "SYMLINK_TO_PINNED_TARGET",
    }


def _host_executable_inventory() -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {
        GIT_PATH: _regular_host_identity(GIT_PATH, GIT_SHA256, GIT_SIZE),
        GIT_REMOTE_HTTP_PATH: _regular_host_identity(
            GIT_REMOTE_HTTP_PATH, GIT_REMOTE_HTTP_SHA256, GIT_REMOTE_HTTP_SIZE
        ),
        GIT_REMOTE_HTTPS_PATH: _symlink_host_identity(
            GIT_REMOTE_HTTPS_PATH,
            GIT_REMOTE_HTTPS_TARGET,
            GIT_REMOTE_HTTPS_LINK_SHA256,
        ),
    }
    for leaf in GIT_BUILTIN_LINKS:
        path = GIT_EXEC_PATH + "/" + leaf
        by_path[path] = _symlink_host_identity(
            path, GIT_BUILTIN_LINK_TARGET, GIT_BUILTIN_LINK_SHA256
        )
    expected_paths = sorted(
        (
            GIT_PATH,
            *(GIT_EXEC_PATH + "/" + leaf for leaf in GIT_BUILTIN_LINKS),
            GIT_REMOTE_HTTP_PATH,
            GIT_REMOTE_HTTPS_PATH,
        ),
        key=lambda value: value.encode("ascii"),
    )
    if set(by_path) != set(expected_paths) or len(expected_paths) != 9:
        raise PrepImplementation("HOST_INVENTORY_SHAPE", "host inventory differs")
    return [by_path[path] for path in expected_paths]


def _require_match_check(value: Any, description: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"expected", "observed", "status"}:
        raise PrepImplementation("CHECK_SHAPE", f"{description} check differs")
    if value["status"] != "MATCH" or value["observed"] is None:
        raise PrepPrecondition("BOOTSTRAP_CHECK_NOT_MATCH", f"{description} is not MATCH")
    if value["expected"] != value["observed"]:
        raise PrepImplementation("CHECK_RECONCILIATION", f"{description} MATCH differs")
    return dict(value)


def _validate_bootstrap_checks(context: Mapping[str, Any]) -> None:
    for name, check in _verified_authority(context).items():
        _require_match_check(check, f"authority {name}")
    for name, check in _verified_host(context).items():
        _require_match_check(check, f"host {name}")
    execution_check = context["authority_checks"]["execution_base_commit"]
    if execution_check["observed"] != context["execution_base_commit"]:
        raise PrepImplementation("EXECUTION_BASE_RECONCILIATION", "execution base differs")


def _send_framed(descriptor: int, value: Mapping[str, Any]) -> None:
    payload = _canonical_document(dict(value))
    if len(payload) > PIPE_MESSAGE_CAP:
        raise PrepImplementation("PIPE_MESSAGE_CAP", "internal control message exceeds cap")
    _write_all(descriptor, struct.pack(">I", len(payload)) + payload)


def _read_exact(descriptor: int, size: int, description: str) -> bytes:
    payload = bytearray()
    while len(payload) < size:
        try:
            chunk = os.read(descriptor, size - len(payload))
        except InterruptedError:
            continue
        if not chunk:
            raise PrepResource("CONTROL_EOF", f"{description} ended early")
        payload.extend(chunk)
    return bytes(payload)


def _parse_control_document(payload: bytes, description: str) -> Any:
    try:
        return _parse_canonical_document(payload, description)
    except PrepArtifact as error:
        raise PrepImplementation(
            "CONTROL_DOCUMENT", f"malformed internal {description}: {error.detail}"
        ) from error


def _recv_framed(descriptor: int, description: str) -> dict[str, Any]:
    header = _read_exact(descriptor, 4, description)
    size = struct.unpack(">I", header)[0]
    if size == 0 or size > PIPE_MESSAGE_CAP:
        raise PrepImplementation("CONTROL_FRAME_SIZE", f"{description} size differs")
    value = _parse_control_document(
        _read_exact(descriptor, size, description), description
    )
    if not isinstance(value, dict):
        raise PrepImplementation("CONTROL_FRAME_TYPE", f"{description} is not object")
    return value


class FrameReader:
    def __init__(self, descriptor: int):
        self.descriptor = descriptor
        self.buffer = bytearray()
        self.expected: int | None = None

    def feed(self) -> list[dict[str, Any]]:
        try:
            payload = os.read(self.descriptor, PIPE_CHUNK)
        except BlockingIOError:
            return []
        if not payload:
            raise PrepResource("CONTROL_EOF", "worker control pipe ended")
        self.buffer.extend(payload)
        values: list[dict[str, Any]] = []
        while True:
            if self.expected is None:
                if len(self.buffer) < 4:
                    break
                self.expected = struct.unpack(">I", self.buffer[:4])[0]
                del self.buffer[:4]
                if self.expected == 0 or self.expected > PIPE_MESSAGE_CAP:
                    raise PrepImplementation("CONTROL_FRAME_SIZE", "worker frame differs")
            if len(self.buffer) < self.expected:
                break
            payload = bytes(self.buffer[: self.expected])
            del self.buffer[: self.expected]
            self.expected = None
            value = _parse_control_document(payload, "worker frame")
            if not isinstance(value, dict):
                raise PrepImplementation("CONTROL_FRAME_TYPE", "worker frame not object")
            values.append(value)
        if len(self.buffer) > PIPE_MESSAGE_CAP:
            raise PrepImplementation(
                "CONTROL_BUFFER_CAP", "worker control buffer exceeds internal cap"
            )
        return values


def _caught_failure_message(
    kind: str,
    error: BaseException,
    *,
    os_code: str,
    resource_code: str,
    implementation_code: str,
) -> dict[str, str]:
    failure = _normalize_caught_failure(
        error,
        os_code=os_code,
        resource_code=resource_code,
        implementation_code=implementation_code,
    )
    if failure.status == "PRECONDITION_NOT_MET":
        failure = PrepImplementation(
            "POST_ROOT_PRECONDITION",
            "internal post-root worker raised a precondition failure: "
            + failure.code,
        )
    code = _require_text(
        failure.code, "serialized failure code", maximum=128, ascii_only=True
    )
    detail = failure.detail.encode("utf-8", errors="replace")[:4_096].decode(
        "utf-8", errors="ignore"
    )
    return {
        "code": code,
        "detail": detail,
        "kind": kind,
        "status": failure.status,
    }


def _best_effort_exec_diagnostic(
    error: BaseException,
    *,
    os_code: str,
    resource_code: str,
    implementation_code: str,
) -> dict[str, str]:
    try:
        return _caught_failure_message(
            "EXEC_ERROR",
            error,
            os_code=os_code,
            resource_code=resource_code,
            implementation_code=implementation_code,
        )
    except BaseException:
        return {
            "code": "GIT_EXEC_DIAGNOSTIC_CAPTURE_INVALID",
            "detail": "Git exec diagnostic capture failed",
            "kind": "EXEC_ERROR",
            "status": "IMPLEMENTATION_INVALID",
        }


def _deserialize_failure(
    message: Mapping[str, Any], *, expected_kind: str
) -> PrepFailure:
    if set(message) != {"code", "detail", "kind", "status"}:
        raise PrepImplementation(
            "WORKER_FAILURE_SHAPE", "serialized worker failure shape differs"
        )
    if message["kind"] != expected_kind:
        raise PrepImplementation(
            "WORKER_FAILURE_KIND", "serialized worker failure kind differs"
        )
    status = _require_text(
        message["status"], "serialized failure status", maximum=64, ascii_only=True
    )
    if status not in {
        "RESOURCE_INCOMPLETE_NO_DECISION",
        "ARTIFACT_INVALID",
        "IMPLEMENTATION_INVALID",
    }:
        raise PrepImplementation(
            "WORKER_FAILURE_STATUS", "serialized worker failure status differs"
        )
    code = _require_text(
        message["code"], "serialized failure code", maximum=128, ascii_only=True
    )
    detail = _require_text(
        message["detail"], "serialized failure detail", maximum=4_096
    )
    return PrepFailure(status, code, detail)


def _merge_exec_diagnostics(
    current: Mapping[str, Any] | None,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    if current is None:
        return dict(candidate)
    try:
        selected = _merge_failure(
            _deserialize_failure(current, expected_kind="EXEC_ERROR"),
            _deserialize_failure(candidate, expected_kind="EXEC_ERROR"),
        )
        if selected is None:
            raise PrepImplementation(
                "GIT_EXEC_DIAGNOSTIC_MERGE",
                "Git exec diagnostic merge unexpectedly became empty",
            )
        return _best_effort_exec_diagnostic(
            selected,
            os_code="GIT_EXEC_DIAGNOSTIC_MERGE_OS_FAILURE",
            resource_code="GIT_EXEC_DIAGNOSTIC_MERGE_RESOURCE_FAILURE",
            implementation_code="GIT_EXEC_DIAGNOSTIC_MERGE_INVALID",
        )
    except BaseException as error:
        return _best_effort_exec_diagnostic(
            error,
            os_code="GIT_EXEC_DIAGNOSTIC_MERGE_OS_FAILURE",
            resource_code="GIT_EXEC_DIAGNOSTIC_MERGE_RESOURCE_FAILURE",
            implementation_code="GIT_EXEC_DIAGNOSTIC_MERGE_INVALID",
        )


def _raise_serialized_failure(
    message: Mapping[str, Any], *, expected_kind: str
) -> NoReturn:
    raise _deserialize_failure(message, expected_kind=expected_kind)


def _read_git_exec_failure(descriptor: int) -> dict[str, Any] | None:
    try:
        payload = _read_fd_bounded(
            descriptor, EXEC_ERROR_BYTE_CAP, "Git setup/exec error channel"
        )
        if not payload:
            return None
        if len(payload) < 4:
            raise PrepImplementation(
                "GIT_EXEC_ERROR_FRAME", "Git setup/exec error frame is truncated"
            )
        size = struct.unpack(">I", payload[:4])[0]
        if size == 0 or size != len(payload) - 4:
            raise PrepImplementation(
                "GIT_EXEC_ERROR_FRAME", "Git setup/exec error frame size differs"
            )
        value = _parse_control_document(payload[4:], "Git setup/exec error frame")
        if not isinstance(value, dict):
            raise PrepImplementation(
                "GIT_EXEC_ERROR_TYPE", "Git setup/exec error frame is not an object"
            )
        _deserialize_failure(value, expected_kind="EXEC_ERROR")
        return dict(value)
    except BaseException as error:
        return _best_effort_exec_diagnostic(
            error,
            os_code="GIT_EXEC_CHANNEL_OS_FAILURE",
            resource_code="GIT_EXEC_CHANNEL_RESOURCE_FAILURE",
            implementation_code="GIT_EXEC_CHANNEL_INVALID",
        )


def _validation_argvs(execution_base: str) -> tuple[tuple[str, ...], ...]:
    suffixes = (
        ("-C", CLONE_ROOT, "config", "--null", "--local", "--list"),
        ("-C", CLONE_ROOT, "show-ref", "--head", "--dereference"),
        ("-C", CLONE_ROOT, "symbolic-ref", "-q", "HEAD"),
        ("-C", CLONE_ROOT, "cat-file", "-e", execution_base + "^{commit}"),
        ("-C", CLONE_ROOT, "rev-parse", execution_base + "^{tree}"),
        (
            "-C",
            CLONE_ROOT,
            "ls-tree",
            "-rz",
            "--full-tree",
            execution_base,
        ),
        (
            "-C",
            CLONE_ROOT,
            "rev-list",
            "--objects",
            "--all",
            "--no-object-names",
        ),
        (
            "-C",
            CLONE_ROOT,
            "cat-file",
            "--batch-all-objects",
            "--batch-check=%(objectname)",
        ),
        (
            "-C",
            CLONE_ROOT,
            "fsck",
            "--full",
            "--strict",
            "--unreachable",
            "--no-reflogs",
        ),
    )
    return tuple((*GIT_PREFIX, *suffix) for suffix in suffixes)


def _allowed_git_argvs(execution_base: str) -> frozenset[tuple[str, ...]]:
    values = {
        tuple(CLONE_ARGV),
        (
            *GIT_PREFIX,
            "-C",
            CLONE_ROOT,
            "checkout",
            "--force",
            "-B",
            BRANCH,
            execution_base,
        ),
        (
            *GIT_PREFIX,
            "-C",
            CLONE_ROOT,
            "remote",
            "set-url",
            "origin",
            FETCH_URL,
        ),
        (
            *GIT_PREFIX,
            "-C",
            CLONE_ROOT,
            "remote",
            "set-url",
            "--push",
            "origin",
            PUSH_URL,
        ),
        (
            *GIT_PREFIX,
            "-C",
            CLONE_ROOT,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignored=no",
        ),
    }
    values.update(_validation_argvs(execution_base))
    return frozenset(values)


def _worker_main(
    command_read_fd: int,
    event_write_fd: int,
    output_write_fds: list[tuple[int, int]],
    output_read_fds: list[tuple[int, int]],
    execution_base: str,
    devnull_fd: int,
) -> NoReturn:
    try:
        for stdout_read, stderr_read in output_read_fds:
            os.close(stdout_read)
            os.close(stderr_read)
        os.setpgid(0, 0)
        worker_pid = os.getpid()
        if os.getpgrp() != worker_pid:
            raise PrepImplementation("WORKER_PGID", "worker PGID differs")
        _send_framed(
            event_write_fd,
            {"kind": "READY", "pid": worker_pid, "process_group_id": os.getpgrp()},
        )
        allowed = _allowed_git_argvs(execution_base)
        used: set[int] = set()
        while True:
            command = _recv_framed(command_read_fd, "parent command")
            kind = command.get("kind")
            if kind == "STOP":
                if set(command) != {"kind"}:
                    raise PrepImplementation("STOP_SHAPE", "worker STOP differs")
                break
            if set(command) != {"argv", "index", "kind"} or kind != "RUN":
                raise PrepImplementation("WORKER_COMMAND", "worker command differs")
            index = _require_uint(command["index"], "worker output index", 31)
            if index in used or index >= len(output_write_fds):
                raise PrepImplementation("WORKER_OUTPUT_INDEX", "output index differs")
            used.add(index)
            raw_argv = command["argv"]
            if not isinstance(raw_argv, list) or len(raw_argv) > 64:
                raise PrepImplementation("WORKER_ARGV", "worker argv count differs")
            argv = tuple(
                _require_text(
                    item,
                    "worker argv item",
                    maximum=512,
                    ascii_only=True,
                )
                for item in raw_argv
            )
            if argv not in allowed:
                raise PrepImplementation("WORKER_ARGV_ALLOWLIST", "worker argv not allowed")
            gate_read, gate_write = os.pipe2(os.O_CLOEXEC)
            exec_error_read, exec_error_write = os.pipe2(os.O_CLOEXEC)
            child = os.fork()
            if child == 0:
                try:
                    os.close(exec_error_read)
                    os.close(gate_write)
                    os.close(command_read_fd)
                    os.close(event_write_fd)
                    for pair_index, (stdout_write, stderr_write) in enumerate(
                        output_write_fds
                    ):
                        if pair_index != index:
                            os.close(stdout_write)
                            os.close(stderr_write)
                    gate = os.read(gate_read, 1)
                    if gate != b"G":
                        raise PrepImplementation(
                            "GIT_GATE", "Git release gate differed"
                        )
                    os.close(gate_read)
                    stdout_write, stderr_write = output_write_fds[index]
                    os.dup2(devnull_fd, 0, inheritable=True)
                    os.dup2(stdout_write, 1, inheritable=True)
                    os.dup2(stderr_write, 2, inheritable=True)
                    if stdout_write not in {0, 1, 2}:
                        os.close(stdout_write)
                    if stderr_write not in {0, 1, 2}:
                        os.close(stderr_write)
                    if devnull_fd not in {0, 1, 2}:
                        os.close(devnull_fd)
                    os.chdir("/")
                    os.execve(GIT_PATH, list(argv), dict(GIT_ENVIRONMENT))
                except BaseException as error:
                    try:
                        _send_framed(
                            exec_error_write,
                            _caught_failure_message(
                                "EXEC_ERROR",
                                error,
                                os_code="GIT_EXEC_OS_FAILURE",
                                resource_code="GIT_EXEC_RESOURCE_FAILURE",
                                implementation_code="GIT_EXEC_SETUP_INVALID",
                            ),
                        )
                    except BaseException:
                        pass
                    os._exit(127)
            os.close(exec_error_write)
            os.close(gate_read)
            stdout_write, stderr_write = output_write_fds[index]
            os.close(stdout_write)
            os.close(stderr_write)
            _send_framed(
                event_write_fd,
                {
                    "index": index,
                    "kind": "SPAWN",
                    "pid": child,
                    "process_group_id": os.getpgid(child),
                },
            )
            acknowledgement = _recv_framed(command_read_fd, "parent acknowledgement")
            if acknowledgement != {"index": index, "kind": "ACK", "pid": child}:
                raise PrepImplementation("WORKER_ACK", "worker acknowledgement differs")
            _write_all(gate_write, b"G")
            os.close(gate_write)
            exec_failure: dict[str, Any] | None = None
            try:
                exec_failure = _read_git_exec_failure(exec_error_read)
            except BaseException as error:
                exec_failure = _best_effort_exec_diagnostic(
                    error,
                    os_code="GIT_EXEC_CHANNEL_OS_FAILURE",
                    resource_code="GIT_EXEC_CHANNEL_RESOURCE_FAILURE",
                    implementation_code="GIT_EXEC_CHANNEL_INVALID",
                )
            try:
                os.close(exec_error_read)
            except BaseException as error:
                exec_failure = _merge_exec_diagnostics(
                    exec_failure,
                    _best_effort_exec_diagnostic(
                        error,
                        os_code="GIT_EXEC_CHANNEL_CLOSE_OS_FAILURE",
                        resource_code="GIT_EXEC_CHANNEL_CLOSE_RESOURCE_FAILURE",
                        implementation_code="GIT_EXEC_CHANNEL_CLOSE_INVALID",
                    ),
                )
            child_io: Mapping[str, int] | None = None
            try:
                os.waitid(os.P_PID, child, os.WEXITED | os.WNOWAIT)
                child_io = _proc_io(child)
            except BaseException as error:
                exec_failure = _merge_exec_diagnostics(
                    exec_failure,
                    _best_effort_exec_diagnostic(
                        error,
                        os_code="GIT_PRE_REAP_OBSERVATION_OS_FAILURE",
                        resource_code="GIT_PRE_REAP_OBSERVATION_RESOURCE_FAILURE",
                        implementation_code="GIT_PRE_REAP_OBSERVATION_INVALID",
                    ),
                )
            waited_pid, raw_status, usage = os.wait4(child, 0)
            if waited_pid != child:
                raise PrepImplementation("WORKER_WAIT_PID", "wait4 PID differs")
            _send_framed(
                event_write_fd,
                {
                    "exec_failure": exec_failure,
                    "index": index,
                    "kind": "WAIT",
                    "wait_record": _wait_record(child, raw_status, usage, child_io),
                },
            )
        for index, (stdout_write, stderr_write) in enumerate(output_write_fds):
            if index not in used:
                os.close(stdout_write)
                os.close(stderr_write)
        own = resource.getrusage(resource.RUSAGE_SELF)
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        _send_framed(
            event_write_fd,
            {
                "children_cpu_microseconds": int(
                    (children.ru_utime + children.ru_stime) * 1_000_000
                ),
                "children_maximum_rss_bytes": int(children.ru_maxrss) * 1024,
                "kind": "DONE",
                "self_cpu_microseconds": int(
                    (own.ru_utime + own.ru_stime) * 1_000_000
                ),
                "self_maximum_rss_bytes": int(own.ru_maxrss) * 1024,
            },
        )
        os.close(command_read_fd)
        os.close(event_write_fd)
        os.close(devnull_fd)
        os._exit(0)
    except BaseException as error:
        try:
            _send_framed(
                event_write_fd,
                _caught_failure_message(
                    "ERROR",
                    error,
                    os_code="WORKER_OS_FAILURE",
                    resource_code="WORKER_RESOURCE_FAILURE",
                    implementation_code="WORKER_UNCAUGHT_EXCEPTION",
                ),
            )
        except BaseException:
            pass
        os._exit(125)


def _set_and_verify_subreaper() -> None:
    if _PRCTL(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        code = ctypes.get_errno()
        raise PrepResource("SUBREAPER_SET", f"prctl set failed with errno {code}")
    value = ctypes.c_int(0)
    if _PRCTL(PR_GET_CHILD_SUBREAPER, ctypes.addressof(value), 0, 0, 0) != 0:
        code = ctypes.get_errno()
        raise PrepResource("SUBREAPER_GET", f"prctl get failed with errno {code}")
    if value.value != 1:
        raise PrepArtifact("SUBREAPER_STATE", "child subreaper state differs")


def _read_process_executable(pid: int) -> tuple[str, bytes, os.stat_result]:
    path = os.readlink(f"/proc/{pid}/exe")
    _external_text(path, "process executable path", maximum=512, ascii_only=True)
    descriptor = os.open(f"/proc/{pid}/exe", os.O_RDONLY | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 8_388_608:
            raise PrepArtifact("PROCESS_EXECUTABLE_TYPE", "process image differs")
        payload = _read_fd_bounded(descriptor, 8_388_608, "process executable")
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
        ) or len(payload) != before.st_size:
            raise PrepArtifact("PROCESS_EXECUTABLE_MUTATED", "process image changed")
        return path, payload, after
    finally:
        os.close(descriptor)


def _family_process_observations(
    worker_pgid: int | None,
) -> tuple[list[dict[str, Any]], int]:
    parent_pid = os.getpid()
    stats: dict[int, dict[str, int]] = {}
    for name in os.listdir("/proc"):
        if not name.isascii() or not name.isdecimal():
            continue
        pid = int(name)
        try:
            stats[pid] = _proc_stat(pid)
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError as error:
            raise PrepResource(
                "PROC_STAT_READ", f"PID {pid} stat read failed: {error}"
            ) from error
    family = {parent_pid}
    changed = True
    while changed:
        changed = False
        for pid, item in stats.items():
            if pid not in family and item["ppid"] in family:
                family.add(pid)
                changed = True
    observations: list[dict[str, Any]] = []
    active_cpu_ticks = 0
    allowed = {
        PYTHON_PATH: (PYTHON_SHA256, PYTHON_SIZE),
        ENV_PATH: (ENV_SHA256, ENV_SIZE),
        GIT_PATH: (GIT_SHA256, GIT_SIZE),
        GIT_REMOTE_HTTP_PATH: (GIT_REMOTE_HTTP_SHA256, GIT_REMOTE_HTTP_SIZE),
    }
    for pid in sorted(family):
        item = stats.get(pid)
        if item is None:
            continue
        try:
            executable_path, payload, executable_meta = _read_process_executable(pid)
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError as error:
            raise PrepResource(
                "PROCESS_EXECUTABLE_READ",
                f"PID {pid} executable read failed: {error}",
            ) from error
        try:
            refreshed = _proc_stat(pid)
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError as error:
            raise PrepResource(
                "PROC_STAT_REREAD", f"PID {pid} stat reread failed: {error}"
            ) from error
        if refreshed["start_time_clock_ticks"] != item["start_time_clock_ticks"]:
            continue
        try:
            after_path, after_payload, after_meta = _read_process_executable(pid)
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError as error:
            raise PrepResource(
                "PROCESS_EXECUTABLE_REREAD",
                f"PID {pid} executable reread failed: {error}",
            ) from error
        if (
            after_path != executable_path
            or after_payload != payload
            or (
                after_meta.st_dev,
                after_meta.st_ino,
                after_meta.st_mode,
                after_meta.st_size,
                after_meta.st_mtime_ns,
            )
            != (
                executable_meta.st_dev,
                executable_meta.st_ino,
                executable_meta.st_mode,
                executable_meta.st_size,
                executable_meta.st_mtime_ns,
            )
        ):
            raise PrepArtifact(
                "PROCESS_EXECUTABLE_TRANSITION",
                "process executable changed across refreshed stat sample",
            )
        executable_path = after_path
        payload = after_payload
        item = refreshed
        if pid == parent_pid:
            if worker_pgid is not None and item["process_group_id"] == worker_pgid:
                raise PrepArtifact("PARENT_WORKER_GROUP", "parent entered worker group")
        else:
            if item["ppid"] not in family:
                raise PrepArtifact(
                    "DESCENDANT_PARENT_IDENTITY",
                    "descendant left the observed process family",
                )
            if worker_pgid is not None and item["process_group_id"] != worker_pgid:
                raise PrepArtifact(
                    "DESCENDANT_WORKER_GROUP", "descendant left worker group"
                )
        if executable_path not in allowed:
            raise PrepArtifact(
                "PROCESS_EXECUTABLE_ALLOWLIST",
                f"unexpected sampled process image: {executable_path}",
            )
        expected_sha256, expected_size = allowed[executable_path]
        observed_sha256 = hashlib.sha256(payload).hexdigest()
        if len(payload) != expected_size or observed_sha256 != expected_sha256:
            raise PrepArtifact("PROCESS_EXECUTABLE_IDENTITY", "process image differs")
        observations.append(
            {
                "current_rss_bytes": item["rss_bytes"],
                "executable_path": executable_path,
                "executable_sha256": observed_sha256,
                "executable_size_bytes": len(payload),
                "pid": pid,
                "ppid": item["ppid"],
                "proc_io": _proc_io(pid),
                "process_group_id": item["process_group_id"],
                "start_time_clock_ticks": item["start_time_clock_ticks"],
            }
        )
        active_cpu_ticks += item["cpu_clock_ticks"]
    if not any(item["pid"] == parent_pid for item in observations):
        raise PrepArtifact("PARENT_OBSERVATION", "parent process was not observed")
    clock_ticks = os.sysconf("SC_CLK_TCK")
    if clock_ticks <= 0:
        raise PrepImplementation("CLOCK_TICK_RATE", "SC_CLK_TCK is not positive")
    return observations, active_cpu_ticks * 1_000_000 // clock_ticks


class PrepMeter:
    def __init__(self, context: Mapping[str, Any]):
        initial = resource.getrusage(resource.RUSAGE_SELF)
        if initial.ru_maxrss < 0:
            raise PrepImplementation("NEGATIVE_RSS", "initial ru_maxrss is negative")
        self.context = context
        self.maximum_rss_bytes = int(initial.ru_maxrss) * 1024
        self.maximum_live_process_count = 1
        self.last_observations: list[dict[str, Any]] = []
        self.wait_records: list[dict[str, Any]] = []
        self.actual_wait_record_count = 0
        self.total_wait_record_count = 0
        self.worker_pgid: int | None = None
        self.worker_group_verified = False
        self.observed_descendant_pids: set[int] = set()
        self.pending_process_violation = False
        self.completed_git_cpu_microseconds = 0
        self.current_observed_cpu_microseconds = _process_cpu_microseconds()
        self.next_process_sample_ns = time.monotonic_ns()
        self.next_filesystem_sample_ns = time.monotonic_ns()

    def sample_processes(self, *, force: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic_ns()
        if not force and now < self.next_process_sample_ns:
            return self.last_observations
        observations, active_cpu_microseconds = _family_process_observations(
            self.worker_pgid if self.worker_group_verified else None
        )
        actual_live = len(observations)
        self.observed_descendant_pids.update(
            item["pid"] for item in observations if item["pid"] != os.getpid()
        )
        concurrent_rss = sum(item["current_rss_bytes"] for item in observations)
        self.maximum_live_process_count = max(
            self.maximum_live_process_count, actual_live
        )
        self.maximum_rss_bytes = max(self.maximum_rss_bytes, concurrent_rss)
        self.last_observations = observations
        if self.worker_pgid is None:
            self.current_observed_cpu_microseconds = _process_cpu_microseconds()
        else:
            self.current_observed_cpu_microseconds = (
                active_cpu_microseconds + self.completed_git_cpu_microseconds
            )
        if (
            actual_live > LIVE_PROCESS_LIMIT
            or self.maximum_rss_bytes > MAXIMUM_OBSERVED_RSS_BYTES
            or self.current_observed_cpu_microseconds
            > PROCESS_FAMILY_CPU_LIMIT_US
        ):
            self.pending_process_violation = True
        self.next_process_sample_ns = now + PROCESS_SAMPLE_INTERVAL_NS
        return observations

    def add_wait_record(
        self,
        record: Mapping[str, Any],
        *,
        account_completed_git_cpu: bool,
    ) -> None:
        self.actual_wait_record_count += 1
        self.total_wait_record_count += 1
        if account_completed_git_cpu:
            self.completed_git_cpu_microseconds += (
                record["user_cpu_microseconds"]
                + record["system_cpu_microseconds"]
            )
        if len(self.wait_records) < LIVE_PROCESS_LIMIT:
            self.wait_records.append(dict(record))

    def snapshot(self, *, force: bool = True) -> dict[str, Any]:
        observations = self.sample_processes(force=force)
        wait_records = list(self.wait_records)
        wait_count = self.actual_wait_record_count
        snapshot = _resource_snapshot(
            observations,
            wait_records,
            actual_live_process_count=len(observations),
            actual_wait_record_count=wait_count,
            maximum_observed_rss_bytes=self.maximum_rss_bytes,
            process_family_cpu_microseconds=self.current_observed_cpu_microseconds,
        )
        self.wait_records.clear()
        self.actual_wait_record_count = 0
        self.next_filesystem_sample_ns = time.monotonic_ns() + FILESYSTEM_SAMPLE_INTERVAL_NS
        return snapshot

    def ceiling_violations(self, snapshot: Mapping[str, Any]) -> list[str]:
        violations: list[str] = []
        comparisons = (
            ("isolation_allocated_bytes", ISOLATION_ALLOCATED_LIMIT),
            ("isolation_entry_count", ENTRY_LIMIT),
            ("isolation_logical_bytes", ISOLATION_LOGICAL_LIMIT),
            ("live_process_count", LIVE_PROCESS_LIMIT),
            (
                "maximum_observed_concurrent_process_family_rss_bytes",
                MAXIMUM_OBSERVED_RSS_BYTES,
            ),
            ("process_family_cpu_microseconds", PROCESS_FAMILY_CPU_LIMIT_US),
        )
        for key, limit in comparisons:
            if snapshot[key] > limit:
                violations.append(key)
        wall = time.monotonic_ns() - self.context["start_monotonic_ns"]
        if wall < 0:
            raise PrepImplementation("NEGATIVE_WALL", "monotonic wall is negative")
        if wall > PROCESS_FAMILY_WALL_LIMIT_NS:
            violations.append("process_family_wall_nanoseconds")
        if snapshot["process_observation_overflow"]:
            violations.append("process_observation_overflow")
        if snapshot["wait_record_overflow"]:
            violations.append("wait_record_overflow")
        return violations


class WorkerHandle:
    def __init__(
        self,
        execution_base: str,
        counters: dict[str, int],
        meter: PrepMeter,
        state: dict[str, Any],
    ):
        self.execution_base = execution_base
        self.counters = counters
        self.closed = False
        self.process_reaped = False
        self.group_verified = False
        self.descriptor_close_failure: PrepFailure | None = None
        self.unresolved_parent_fds: set[int] = set()
        self.command_read_fd, self.command_write_fd = os.pipe2(os.O_CLOEXEC)
        self.event_read_fd, self.event_write_fd = os.pipe2(os.O_CLOEXEC)
        self.output_pipes: list[tuple[tuple[int, int], tuple[int, int]]] = []
        for _ in range(32):
            stdout_read, stdout_write = os.pipe2(os.O_CLOEXEC)
            stderr_read, stderr_write = os.pipe2(os.O_CLOEXEC)
            self.output_pipes.append(
                ((stdout_read, stderr_read), (stdout_write, stderr_write))
            )
        self.devnull_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        self.parent_open_fds = {
            self.command_read_fd,
            self.command_write_fd,
            self.event_read_fd,
            self.event_write_fd,
            self.devnull_fd,
            *(
                descriptor
                for read_pair, write_pair in self.output_pipes
                for descriptor in (*read_pair, *write_pair)
            ),
        }
        self.pid = os.fork()
        counters["spawned_process_count"] += 1
        if self.pid == 0:
            try:
                os.close(self.command_write_fd)
                os.close(self.event_read_fd)
                _worker_main(
                    self.command_read_fd,
                    self.event_write_fd,
                    [item[1] for item in self.output_pipes],
                    [item[0] for item in self.output_pipes],
                    execution_base,
                    self.devnull_fd,
                )
            finally:
                os._exit(125)
        state["worker"] = self
        setpgid_failure: PrepFailure | None = None
        try:
            os.setpgid(self.pid, self.pid)
        except ProcessLookupError as error:
            raise PrepResource(
                "WORKER_PROCESS_LOST", "worker exited before parent PGID setup"
            ) from error
        except OSError as error:
            setpgid_failure = PrepResource(
                "WORKER_SETPGID_OS_FAILURE",
                f"parent setpgid failed before READY: {error}",
            )
        try:
            observed_pgid = os.getpgid(self.pid)
        except ProcessLookupError as error:
            raise PrepResource(
                "WORKER_PROCESS_LOST", "worker exited before parent PGID verification"
            ) from error
        except OSError as error:
            if setpgid_failure is not None:
                raise setpgid_failure
            raise PrepResource(
                "WORKER_GETPGID_OS_FAILURE",
                f"parent getpgid failed before READY: {error}",
            ) from error
        if observed_pgid != self.pid or os.getpgrp() == self.pid:
            if setpgid_failure is not None:
                raise setpgid_failure
            raise PrepArtifact(
                "WORKER_GROUP_TOPOLOGY", "parent-created worker group topology differs"
            )
        self.group_verified = True
        meter.worker_pgid = self.pid
        meter.worker_group_verified = True
        if setpgid_failure is not None:
            raise setpgid_failure
        self.close_parent_fd(self.command_read_fd)
        self.close_parent_fd(self.event_write_fd)
        self.close_parent_fd(self.devnull_fd)
        for _, (stdout_write, stderr_write) in self.output_pipes:
            self.close_parent_fd(stdout_write)
            self.close_parent_fd(stderr_write)
        os.set_blocking(self.event_read_fd, False)
        self.reader = FrameReader(self.event_read_fd)
        selector = selectors.DefaultSelector()
        selector.register(self.event_read_fd, selectors.EVENT_READ)
        ready: dict[str, Any] | None = None
        deadline = meter.context["start_monotonic_ns"] + PROCESS_FAMILY_WALL_LIMIT_NS
        try:
            while ready is None:
                now = time.monotonic_ns()
                if now >= deadline:
                    raise PrepResource(
                        "WORKER_READY_TIMEOUT",
                        "worker readiness exceeded the process-family wall cap",
                    )
                meter.sample_processes(force=True)
                if meter.pending_process_violation:
                    raise PrepResource(
                        "WORKER_READY_RESOURCE_CEILING",
                        "worker readiness crossed a process, RSS, or CPU ceiling",
                    )
                timeout = min(0.01, max((deadline - now) / 1_000_000_000, 0.0))
                for _, _ in selector.select(timeout):
                    for message in self.reader.feed():
                        kind = message.get("kind")
                        if kind == "ERROR":
                            _raise_serialized_failure(
                                message, expected_kind="ERROR"
                            )
                        if kind != "READY" or ready is not None:
                            raise PrepImplementation(
                                "WORKER_READY_EVENT",
                                "worker readiness event differs",
                            )
                        ready = message
        finally:
            selector.close()
        if set(ready) != {"kind", "pid", "process_group_id"} or ready["kind"] != "READY":
            raise PrepImplementation("WORKER_READY_SHAPE", "worker readiness differs")
        if ready["pid"] != self.pid or ready["process_group_id"] != self.pid:
            raise PrepArtifact("WORKER_READY_IDENTITY", "worker readiness identity differs")
        if os.getpgid(self.pid) != self.pid or os.getpgrp() == self.pid:
            raise PrepArtifact("WORKER_GROUP_TOPOLOGY", "worker group topology differs")
        self.next_index = 0
        self.done_message: dict[str, Any] | None = None
        self.parent_wait_records: list[dict[str, Any]] = []

    def close_parent_fd(self, descriptor: int) -> None:
        if descriptor not in self.parent_open_fds:
            return
        try:
            os.close(descriptor)
        except OSError as error:
            failure: PrepFailure
            if error.errno == errno.EBADF:
                failure = PrepImplementation(
                    "WORKER_FD_OWNERSHIP",
                    f"owned worker descriptor {descriptor} was already invalid",
                )
            else:
                failure = PrepResource(
                    "WORKER_FD_CLOSE",
                    f"owned worker descriptor {descriptor} close failed: {error}",
                )
            self.unresolved_parent_fds.add(descriptor)
            self.descriptor_close_failure = _merge_failure(
                self.descriptor_close_failure, failure
            )
            raise failure
        else:
            self.parent_open_fds.discard(descriptor)

    def output_read_pair(self, index: int) -> tuple[int, int]:
        return self.output_pipes[index][0]

    def send(self, value: Mapping[str, Any]) -> None:
        if self.closed:
            raise PrepImplementation("WORKER_CLOSED", "send after worker close")
        _send_framed(self.command_write_fd, value)


def _filesystem_identity() -> dict[str, Any]:
    summary, _ = _scan_tree(ISOLATION_ROOT)
    return {
        "allocated_bytes": summary["allocated_bytes"],
        "entry_count": summary["entry_count"],
        "inventory_sha256": summary["inventory_sha256"],
        "logical_bytes": summary["logical_bytes"],
    }


def _journal_resource_sample(
    journal: HashJournal,
    meter: PrepMeter,
    *,
    operation: str = "SAMPLE_RESOURCES",
    detail: str = "periodic observed resource sample",
) -> dict[str, Any]:
    snapshot = meter.snapshot(force=True)
    journal.append(
        record_type="SAMPLE",
        operation=operation,
        argv=None,
        cwd="/",
        environment_sha256=hashlib.sha256(_canonical_body(GIT_ENVIRONMENT)).hexdigest(),
        status="OBSERVED",
        exit_code=None,
        signal_number=None,
        stdout_identity=None,
        stderr_identity=None,
        filesystem_snapshot_identity=_filesystem_identity(),
        resource_snapshot=snapshot,
        detail=detail,
    )
    violations = meter.ceiling_violations(snapshot)
    if violations:
        raise PrepResource(
            "OBSERVED_RESOURCE_CEILING",
            "observed ceiling violation: " + ",".join(sorted(set(violations))),
        )
    return snapshot


def _run_git_command(
    worker: WorkerHandle,
    journal: HashJournal,
    meter: PrepMeter,
    capture: CaptureWriter,
    counters: dict[str, int],
    *,
    operation: str,
    argv: Sequence[str],
) -> tuple[bytes, bytes, dict[str, Any]]:
    if worker.next_index >= len(worker.output_pipes):
        raise PrepImplementation("GIT_COMMAND_COUNT", "Git command count exceeds pipe pool")
    argv_list = [
        _require_text(item, "Git argv", maximum=512, ascii_only=True) for item in argv
    ]
    before = meter.snapshot(force=True)
    journal.append(
        record_type="INTENT",
        operation=operation,
        argv=argv_list,
        cwd="/",
        environment_sha256=hashlib.sha256(_canonical_body(GIT_ENVIRONMENT)).hexdigest(),
        status="PENDING",
        exit_code=None,
        signal_number=None,
        stdout_identity=None,
        stderr_identity=None,
        filesystem_snapshot_identity=_filesystem_identity(),
        resource_snapshot=before,
        detail="Git child intent before worker release",
    )
    violations = meter.ceiling_violations(before)
    if violations:
        raise PrepResource("OBSERVED_RESOURCE_CEILING", ",".join(violations))
    index = worker.next_index
    worker.next_index += 1
    stdout_fd, stderr_fd = worker.output_read_pair(index)
    os.set_blocking(stdout_fd, False)
    os.set_blocking(stderr_fd, False)
    selector = selectors.DefaultSelector()
    selector.register(worker.event_read_fd, selectors.EVENT_READ, ("event", 0))
    selector.register(stdout_fd, selectors.EVENT_READ, ("output", 1))
    selector.register(stderr_fd, selectors.EVENT_READ, ("output", 2))
    stdout = bytearray()
    stderr = bytearray()
    stream_open = {1: True, 2: True}
    child_pid: int | None = None
    wait_record: dict[str, Any] | None = None
    exec_diagnostic_failure: PrepFailure | None = None
    worker.send({"argv": argv_list, "index": index, "kind": "RUN"})
    try:
        while wait_record is None or any(stream_open.values()):
            now = time.monotonic_ns()
            if now >= meter.next_process_sample_ns:
                meter.sample_processes(force=True)
                if meter.pending_process_violation:
                    _journal_resource_sample(
                        journal,
                        meter,
                        detail="observed process-count, RSS, or CPU ceiling violation",
                    )
            if now >= meter.next_filesystem_sample_ns:
                _journal_resource_sample(journal, meter)
            wall = now - meter.context["start_monotonic_ns"]
            if wall < 0:
                raise PrepImplementation("NEGATIVE_WALL", "Git loop wall is negative")
            if wall > PROCESS_FAMILY_WALL_LIMIT_NS:
                raise PrepResource("WALL_CEILING", "process-family wall ceiling exceeded")
            timeout = max(
                min(
                    (meter.next_process_sample_ns - now) / 1_000_000_000,
                    0.01,
                ),
                0.0,
            )
            events = selector.select(timeout)
            for key, _ in events:
                category, stream = key.data
                if category == "event":
                    for message in worker.reader.feed():
                        kind = message.get("kind")
                        if kind == "SPAWN":
                            if set(message) != {
                                "index",
                                "kind",
                                "pid",
                                "process_group_id",
                            } or message["index"] != index:
                                raise PrepImplementation("SPAWN_SHAPE", "spawn event differs")
                            if child_pid is not None:
                                raise PrepImplementation("SPAWN_DUPLICATE", "duplicate spawn")
                            child_pid = _require_uint(message["pid"], "Git child PID")
                            if message["process_group_id"] != worker.pid:
                                raise PrepArtifact("GIT_CHILD_PGID", "Git child PGID differs")
                            counters["spawned_process_count"] += 1
                            meter.sample_processes(force=True)
                            if meter.pending_process_violation:
                                _journal_resource_sample(
                                    journal,
                                    meter,
                                    detail="observed fork-boundary ceiling violation",
                                )
                            worker.send(
                                {"index": index, "kind": "ACK", "pid": child_pid}
                            )
                        elif kind == "WAIT":
                            if set(message) != {
                                "exec_failure",
                                "index",
                                "kind",
                                "wait_record",
                            }:
                                raise PrepImplementation("WAIT_SHAPE", "wait event differs")
                            if message["index"] != index or wait_record is not None:
                                raise PrepImplementation("WAIT_INDEX", "wait event index differs")
                            if not isinstance(message["wait_record"], dict):
                                raise PrepImplementation("WAIT_RECORD", "wait record differs")
                            if child_pid is None:
                                raise PrepImplementation(
                                    "WAIT_BEFORE_SPAWN", "wait event preceded spawn"
                                )
                            wait_record = _validated_wait_record(
                                message["wait_record"], expected_pid=child_pid
                            )
                            meter.add_wait_record(
                                wait_record, account_completed_git_cpu=True
                            )
                            counters["reaped_process_count"] += 1
                            meter.sample_processes(force=True)
                            exec_failure = message["exec_failure"]
                            if exec_failure is not None:
                                if not isinstance(exec_failure, dict):
                                    exec_diagnostic_failure = _merge_failure(
                                        exec_diagnostic_failure,
                                        PrepImplementation(
                                            "GIT_EXEC_FAILURE_TYPE",
                                            "Git setup/exec failure is not an object",
                                        ),
                                    )
                                else:
                                    try:
                                        candidate_exec_failure = _deserialize_failure(
                                            exec_failure, expected_kind="EXEC_ERROR"
                                        )
                                    except BaseException as error:
                                        candidate_exec_failure = (
                                            _normalize_caught_failure(
                                                error,
                                                os_code="GIT_EXEC_DIAGNOSTIC_OS_FAILURE",
                                                resource_code="GIT_EXEC_DIAGNOSTIC_RESOURCE_FAILURE",
                                                implementation_code="GIT_EXEC_DIAGNOSTIC_INVALID",
                                            )
                                        )
                                    exec_diagnostic_failure = _merge_failure(
                                        exec_diagnostic_failure,
                                        candidate_exec_failure,
                                    )
                        elif kind == "ERROR":
                            _raise_serialized_failure(
                                message, expected_kind="ERROR"
                            )
                        else:
                            raise PrepImplementation("WORKER_EVENT", "worker event differs")
                else:
                    try:
                        chunk = os.read(key.fd, PIPE_CHUNK)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(key.fd)
                        worker.close_parent_fd(key.fd)
                        stream_open[stream] = False
                        continue
                    if child_pid is None:
                        raise PrepImplementation("OUTPUT_BEFORE_SPAWN", "output preceded spawn")
                    target = stdout if stream == 1 else stderr
                    if len(target) + len(chunk) > STREAM_CAP:
                        raise PrepResource("CHILD_STREAM_CAP", "child stream cap exceeded")
                    target.extend(chunk)
                    capture.write(child_pid, stream, chunk)
                    meter.sample_processes(force=True)
    finally:
        selector.close()
    if child_pid is None or wait_record is None:
        raise PrepImplementation("GIT_CHILD_CLOSURE", "Git child closure incomplete")
    raw_status = wait_record["raw_wait_status"]
    exit_code = wait_record["exit_code"]
    signal_number = wait_record["signal_number"]
    status = "OK" if exit_code == 0 and signal_number is None else "FAILED"
    after = meter.snapshot(force=True)
    stdout_identity = _identity(bytes(stdout))
    stderr_identity = _identity(bytes(stderr))
    journal.append(
        record_type="RESULT",
        operation=operation,
        argv=argv_list,
        cwd="/",
        environment_sha256=hashlib.sha256(_canonical_body(GIT_ENVIRONMENT)).hexdigest(),
        status=status,
        exit_code=exit_code,
        signal_number=signal_number,
        stdout_identity=stdout_identity,
        stderr_identity=stderr_identity,
        filesystem_snapshot_identity=_filesystem_identity(),
        resource_snapshot=after,
        detail=f"Git child result raw_wait_status={raw_status}",
    )
    violations = meter.ceiling_violations(after)
    if violations:
        raise PrepResource("OBSERVED_RESOURCE_CEILING", ",".join(violations))
    if status != "OK":
        raise PrepResource(
            "GIT_COMMAND_FAILED",
            f"Git command failed: operation={operation} exit={exit_code} signal={signal_number}",
        )
    if exec_diagnostic_failure is not None:
        raise exec_diagnostic_failure
    return bytes(stdout), bytes(stderr), wait_record


def _parse_config(payload: bytes) -> list[tuple[str, str]]:
    if not payload.endswith(b"\x00"):
        raise PrepArtifact("GIT_CONFIG_FRAMING", "Git config output lacks NUL")
    result: list[tuple[str, str]] = []
    for record in payload[:-1].split(b"\x00"):
        if record.count(b"\n") != 1:
            raise PrepArtifact("GIT_CONFIG_RECORD", "Git config record differs")
        raw_key, raw_value = record.split(b"\n", 1)
        try:
            key = raw_key.decode("utf-8", errors="strict")
            value = raw_value.decode("utf-8", errors="strict")
        except UnicodeError as error:
            raise PrepArtifact("GIT_CONFIG_ENCODING", "Git config is not UTF-8") from error
        _external_text(key, "Git config key", maximum=512)
        _external_text(value, "Git config value", maximum=512)
        result.append((key, value))
    if len(result) != len(set(result)):
        raise PrepArtifact("GIT_CONFIG_DUPLICATE", "Git config contains duplicate pair")
    return result


def _expected_config(final: bool) -> list[tuple[str, str]]:
    values = [
        ("core.repositoryformatversion", "0"),
        ("core.filemode", "true"),
        ("core.bare", "false"),
        ("core.logallrefupdates", "true"),
        ("remote.origin.url", FETCH_URL),
        ("remote.origin.fetch", "+" + LOCAL_REF + ":" + REMOTE_REF),
        ("remote.origin.tagOpt", "--no-tags"),
        (f"branch.{BRANCH}.remote", "origin"),
        (f"branch.{BRANCH}.merge", LOCAL_REF),
    ]
    if final:
        values.append(("remote.origin.pushurl", PUSH_URL))
    return values


def _parse_ref_output(payload: bytes, execution_base: str) -> str:
    try:
        lines = payload.decode("ascii", errors="strict").splitlines(keepends=True)
    except UnicodeError as error:
        raise PrepArtifact("GIT_REF_ENCODING", "Git refs are not ASCII") from error
    expected = {
        f"{execution_base} HEAD\n",
        f"{execution_base} {LOCAL_REF}\n",
        f"{execution_base} {REMOTE_REF}\n",
    }
    if set(lines) != expected or len(lines) != 3:
        raise PrepArtifact("GIT_REF_CLOSURE", "Git ref closure differs")
    return hashlib.sha256(_canonical_body(sorted(lines))).hexdigest()


def _parse_oid_lines(payload: bytes, description: str) -> set[str]:
    try:
        text = payload.decode("ascii", errors="strict")
    except UnicodeError as error:
        raise PrepArtifact("GIT_OID_ENCODING", f"{description} not ASCII") from error
    if text and not text.endswith("\n"):
        raise PrepArtifact("GIT_OID_FRAMING", f"{description} lacks final LF")
    values = text.splitlines()
    if len(values) > ENTRY_LIMIT:
        raise PrepResource("GIT_OID_COUNT_CAP", f"{description} exceeds count cap")
    if len(values) != len(set(values)):
        raise PrepArtifact("GIT_OID_DUPLICATE", f"{description} has duplicates")
    for value in values:
        _external_oid(value, description)
    return set(values)


def _parse_ls_tree(payload: bytes) -> dict[str, dict[str, str]]:
    if not payload.endswith(b"\x00"):
        raise PrepArtifact("LS_TREE_FRAMING", "ls-tree output lacks NUL")
    result: dict[str, dict[str, str]] = {}
    for raw_record in payload[:-1].split(b"\x00"):
        if raw_record.count(b"\t") != 1:
            raise PrepArtifact("LS_TREE_RECORD", "ls-tree record differs")
        raw_header, raw_path = raw_record.split(b"\t", 1)
        fields = raw_header.split(b" ")
        if len(fields) != 3:
            raise PrepArtifact("LS_TREE_HEADER", "ls-tree header differs")
        try:
            mode = fields[0].decode("ascii")
            object_type = fields[1].decode("ascii")
            oid = fields[2].decode("ascii")
            path = raw_path.decode("utf-8", errors="strict")
        except UnicodeError as error:
            raise PrepArtifact("LS_TREE_ENCODING", "ls-tree encoding differs") from error
        _external_relative(path, "ls-tree path")
        _external_oid(oid, "ls-tree object")
        if mode not in {"100644", "100755"} or object_type != "blob":
            raise PrepArtifact("LS_TREE_TYPE", f"forbidden tracked type: {path}")
        if os.path.basename(path) in {".gitattributes", ".gitmodules"}:
            raise PrepArtifact("LS_TREE_CONTROL_FILE", f"forbidden tracked file: {path}")
        if path in result:
            raise PrepArtifact("LS_TREE_DUPLICATE", f"duplicate tracked path: {path}")
        result[path] = {"mode": mode, "oid": oid, "type": object_type}
    if not result:
        raise PrepArtifact("LS_TREE_COUNT", "ls-tree is empty")
    if len(result) > ENTRY_LIMIT:
        raise PrepResource("LS_TREE_COUNT_CAP", "ls-tree count exceeds cap")
    ordered = sorted(result, key=lambda value: value.encode("utf-8"))
    if list(result) != ordered:
        raise PrepArtifact("LS_TREE_ORDER", "ls-tree path order differs")
    return result


def _validate_reflogs(execution_base: str) -> str:
    git_fd = _open_absolute_dir(CLONE_ROOT + "/.git")
    expected_paths = {
        "logs/HEAD",
        "logs/refs/heads/" + BRANCH,
        "logs/refs/remotes/origin/" + BRANCH,
    }
    observed: list[dict[str, Any]] = []
    logs_fd = _open_relative_dir(git_fd, "logs")
    try:
        stack: list[tuple[int, str]] = [(os.dup(logs_fd), "logs")]
        found: set[str] = set()
        discovered_count = 0
        while stack:
            directory_fd, prefix = stack.pop()
            try:
                names = _bounded_sorted_entry_names(
                    directory_fd,
                    discovered_count,
                    "Git reflog tree",
                )
                discovered_count += len(names)
                for name in names:
                    relative = prefix + "/" + name
                    metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if stat.S_ISDIR(metadata.st_mode):
                        child = os.open(
                            name,
                            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=directory_fd,
                        )
                        stack.append((child, relative))
                    elif stat.S_ISREG(metadata.st_mode):
                        found.add(relative)
                    else:
                        raise PrepArtifact("REFLOG_TYPE", "reflog type differs")
            finally:
                os.close(directory_fd)
        if found != expected_paths:
            raise PrepArtifact("REFLOG_PATH_CLOSURE", "reflog paths differ")
        for relative in sorted(found, key=lambda value: value.encode("utf-8")):
            payload, _ = _read_relative_regular(
                git_fd,
                relative,
                maximum=1_048_576,
                description="Git reflog",
            )
            if not payload or not payload.endswith(b"\n"):
                raise PrepArtifact("REFLOG_FRAMING", "reflog framing differs")
            lines = payload.splitlines(keepends=True)
            if len(lines) > 8:
                raise PrepArtifact("REFLOG_LINE_COUNT", "reflog line count differs")
            for line in lines:
                if len(line) > 4_096 or b"\t" not in line:
                    raise PrepArtifact("REFLOG_LINE", "reflog line differs")
                prefix, message = line[:-1].split(b"\t", 1)
                fields = prefix.split(b" ")
                if len(fields) < 6:
                    raise PrepArtifact("REFLOG_FIELDS", "reflog fields differ")
                try:
                    old_oid = fields[0].decode("ascii")
                    new_oid = fields[1].decode("ascii")
                    message.decode("utf-8", errors="strict")
                except UnicodeError as error:
                    raise PrepArtifact("REFLOG_ENCODING", "reflog encoding differs") from error
                _external_oid(old_oid, "reflog old OID")
                _external_oid(new_oid, "reflog new OID")
                if new_oid != execution_base:
                    raise PrepArtifact("REFLOG_NEW_OID", "reflog target differs")
            observed.append({"path": relative, **_identity(payload)})
    finally:
        os.close(logs_fd)
        os.close(git_fd)
    return hashlib.sha256(_canonical_body(observed)).hexdigest()


def _validate_forbidden_git_state() -> None:
    forbidden = (
        ".git/config.worktree",
        ".git/shallow",
        ".git/info/grafts",
        ".git/objects/info/alternates",
        ".git/refs/replace",
        ".git/modules",
    )
    clone_fd = _open_absolute_dir(CLONE_ROOT)
    try:
        for relative in forbidden:
            try:
                os.stat(relative, dir_fd=clone_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise PrepArtifact("FORBIDDEN_GIT_STATE", f"forbidden Git state: {relative}")
        for relative in (".git/hooks", ".git/info/attributes"):
            try:
                metadata = os.stat(relative, dir_fd=clone_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if stat.S_ISDIR(metadata.st_mode):
                directory = _open_relative_dir(clone_fd, relative)
                try:
                    if any(True for _ in os.scandir(directory)):
                        raise PrepArtifact("FORBIDDEN_GIT_STATE", f"nonempty {relative}")
                finally:
                    os.close(directory)
            elif metadata.st_size != 0:
                raise PrepArtifact("FORBIDDEN_GIT_STATE", f"nonempty {relative}")
    finally:
        os.close(clone_fd)


def _run_validation_suite(
    worker: WorkerHandle,
    journal: HashJournal,
    meter: PrepMeter,
    capture: CaptureWriter,
    counters: dict[str, int],
    execution_base: str,
    *,
    final_config: bool,
) -> dict[str, Any]:
    outputs: list[tuple[bytes, bytes, dict[str, Any]]] = []
    for argv in _validation_argvs(execution_base):
        outputs.append(
            _run_git_command(
                worker,
                journal,
                meter,
                capture,
                counters,
                operation=(
                    "VALIDATE_POSTCHECKOUT" if final_config else "VALIDATE_PRECHECKOUT"
                ),
                argv=argv,
            )
        )
    for _, stderr, _ in outputs:
        if stderr:
            raise PrepArtifact("GIT_VALIDATION_STDERR", "Git validation stderr not empty")
    config = _parse_config(outputs[0][0])
    if sorted(config) != sorted(_expected_config(final_config)):
        raise PrepArtifact("GIT_CONFIG_CLOSURE", "Git local config differs")
    ref_inventory_sha256 = _parse_ref_output(outputs[1][0], execution_base)
    if outputs[2][0] != (LOCAL_REF + "\n").encode("ascii"):
        raise PrepArtifact("GIT_SYMBOLIC_HEAD", "symbolic HEAD differs")
    if outputs[3][0]:
        raise PrepArtifact("GIT_CAT_FILE_OUTPUT", "cat-file -e emitted output")
    try:
        tree_text = outputs[4][0].decode("ascii", errors="strict")
    except UnicodeError as error:
        raise PrepArtifact(
            "GIT_TREE_OID_ENCODING", "execution tree OID output is not ASCII"
        ) from error
    if not tree_text.endswith("\n"):
        raise PrepArtifact("GIT_TREE_OID_FRAMING", "tree OID output differs")
    execution_tree = _external_oid(tree_text[:-1], "execution tree")
    tracked_tree = _parse_ls_tree(outputs[5][0])
    reachable = _parse_oid_lines(outputs[6][0], "reachable object set")
    all_objects = _parse_oid_lines(outputs[7][0], "all object set")
    if not reachable or reachable != all_objects:
        raise PrepArtifact("GIT_OBJECT_SET", "Git object sets differ")
    if outputs[8][0] or outputs[8][1]:
        raise PrepArtifact("GIT_FSCK_OUTPUT", "Git fsck output is not empty")
    reflog_inventory_sha256 = _validate_reflogs(execution_base)
    _validate_forbidden_git_state()
    return {
        "all_objects": all_objects,
        "config_payload": outputs[0][0],
        "execution_tree": execution_tree,
        "fsck_stderr": outputs[8][1],
        "fsck_stdout": outputs[8][0],
        "reachable": reachable,
        "ref_inventory_sha256": ref_inventory_sha256,
        "reflog_inventory_sha256": reflog_inventory_sha256,
        "tracked_tree": tracked_tree,
    }


def _git_blob_oid(payload: bytes) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {len(payload)}\x00".encode("ascii"))
    digest.update(payload)
    return digest.hexdigest()


def _expected_directory_paths(paths: Sequence[str]) -> set[str]:
    result: set[str] = set()
    for path in paths:
        components = path.split("/")[:-1]
        for index in range(1, len(components) + 1):
            result.add("/".join(components[:index]))
    return result


def _validate_tracked_worktree(
    tracked_tree: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    root_fd = _open_absolute_dir(CLONE_ROOT)
    root_meta = os.fstat(root_fd)
    pinned_device = root_meta.st_dev
    pinned_uid = os.geteuid()
    files: dict[str, dict[str, Any]] = {}
    directories: set[str] = set()
    inventory: list[dict[str, Any]] = []
    entry_count = 0
    discovered_count = 0
    logical_bytes = 0
    allocated_bytes = 0

    def visit(directory_fd: int, relative: str) -> None:
        nonlocal entry_count, discovered_count, logical_bytes, allocated_bytes
        names = _bounded_sorted_entry_names(
            directory_fd,
            discovered_count,
            "tracked worktree",
            excluded=frozenset({".git"}) if not relative else frozenset(),
        )
        discovered_count += len(names)
        for name in names:
            path = name if not relative else relative + "/" + name
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if metadata.st_dev != pinned_device or metadata.st_uid != pinned_uid:
                raise PrepArtifact("WORKTREE_DEVICE_OWNER", f"worktree differs: {path}")
            logical = int(metadata.st_size)
            allocated = int(metadata.st_blocks) * 512
            entry_count += 1
            logical_bytes += logical
            allocated_bytes += allocated
            if (
                entry_count > ENTRY_LIMIT
                or logical_bytes > ISOLATION_LOGICAL_LIMIT
                or allocated_bytes > ISOLATION_ALLOCATED_LIMIT
            ):
                raise PrepResource(
                    "WORKTREE_RESOURCE_CEILING",
                    "tracked worktree crossed an entry or byte ceiling: "
                    f"entries={entry_count},logical={logical_bytes},"
                    f"allocated={allocated_bytes}",
                )
            if stat.S_ISDIR(metadata.st_mode):
                if stat.S_IMODE(metadata.st_mode) != 0o700:
                    raise PrepArtifact("WORKTREE_DIRECTORY_MODE", f"mode differs: {path}")
                directories.add(path)
                inventory.append(
                    {
                        "allocated_bytes": allocated,
                        "logical_bytes": logical,
                        "mode_octal": "0700",
                        "path": path,
                        "type": "directory",
                    }
                )
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=directory_fd,
                )
                try:
                    visit(child, path)
                finally:
                    os.close(child)
            elif stat.S_ISREG(metadata.st_mode):
                payload, stable = _read_relative_regular(
                    root_fd,
                    path,
                    maximum=ISOLATION_LOGICAL_LIMIT,
                    description="tracked worktree file",
                )
                mode = stat.S_IMODE(stable.st_mode)
                if mode not in {0o600, 0o700}:
                    raise PrepArtifact("WORKTREE_FILE_MODE", f"mode differs: {path}")
                files[path] = {
                    "mode": "100755" if mode == 0o700 else "100644",
                    "oid": _git_blob_oid(payload),
                }
                inventory.append(
                    {
                        "allocated_bytes": allocated,
                        "logical_bytes": logical,
                        "mode_octal": f"{mode:04o}",
                        "path": path,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "type": "regular",
                    }
                )
            else:
                raise PrepArtifact("WORKTREE_TYPE", f"worktree type differs: {path}")

    try:
        visit(root_fd, "")
    finally:
        os.close(root_fd)
    expected_files = {
        path: {"mode": item["mode"], "oid": item["oid"]}
        for path, item in tracked_tree.items()
    }
    if files != expected_files:
        raise PrepArtifact("WORKTREE_GIT_TREE", "physical files differ from Git tree")
    if directories != _expected_directory_paths(list(expected_files)):
        raise PrepArtifact("WORKTREE_DIRECTORY_SET", "physical directories differ")
    if len(inventory) > ENTRY_LIMIT:
        raise PrepResource("WORKTREE_ENTRY_LIMIT", "worktree entries exceed cap")
    executable_count = sum(item["mode"] == "100755" for item in files.values())
    summary = {
        "allocated_bytes": allocated_bytes,
        "device_id": pinned_device,
        "directory_count": len(directories),
        "entry_count": len(inventory),
        "executable_file_count": executable_count,
        "inventory_sha256": hashlib.sha256(_canonical_body(inventory)).hexdigest(),
        "logical_bytes": logical_bytes,
        "nonexecutable_file_count": len(files) - executable_count,
        "owner_uid": pinned_uid,
    }
    return summary


def _path_absent(root_fd: int, relative: str) -> bool:
    try:
        os.stat(relative, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return True
    return False


def _validate_exact_absences() -> list[str]:
    root_fd = _open_absolute_dir(CLONE_ROOT)
    result: list[str] = []
    try:
        for relative in EXACT_ABSENT_PATHS:
            _require_relative(relative, "exact absent path")
            if not _path_absent(root_fd, relative):
                raise PrepArtifact("EXPECTED_PATH_PRESENT", f"path is present: {relative}")
            result.append(relative)
    finally:
        os.close(root_fd)
    return result


def _validate_source_manifest() -> tuple[dict[str, Any], str]:
    root_fd = _open_absolute_dir(CLONE_ROOT)
    try:
        manifest_payload, _ = _read_relative_regular(
            root_fd,
            IMPLEMENTATION_MANIFEST_RELATIVE,
            maximum=1_048_576,
            description="implementation manifest",
        )
        try:
            manifest = _parse_canonical_document(
                manifest_payload, "implementation manifest"
            )
        except PrepImplementation as error:
            raise PrepArtifact(
                "SOURCE_MANIFEST_JSON",
                "source manifest value constraints differ: " + error.detail,
            ) from error
        if not isinstance(manifest, dict):
            raise PrepArtifact("SOURCE_MANIFEST_TYPE", "source manifest is not object")
        if manifest.get("schema_version") != 2:
            raise PrepArtifact("SOURCE_MANIFEST_VERSION", "source manifest version differs")
        source_files = manifest.get("source_files")
        python_files = manifest.get("python_source_files")
        if (
            not isinstance(source_files, list)
            or len(source_files) != 37
            or not isinstance(python_files, list)
            or len(python_files) != 10
        ):
            raise PrepArtifact("SOURCE_MANIFEST_COUNT", "source manifest counts differ")
        preimage: list[dict[str, Any]] = []
        paths: list[str] = []
        for index, record in enumerate(source_files):
            if not isinstance(record, dict) or set(record) != {
                "family",
                "path",
                "role",
                "sha256",
                "size_bytes",
            }:
                raise PrepArtifact("SOURCE_RECORD_SHAPE", "source record differs")
            path = _external_relative(record["path"], f"source path {index}")
            expected_size = _external_uint(record["size_bytes"], "source size")
            expected_sha256 = _external_sha256(
                record["sha256"], "source SHA-256"
            )
            payload, _ = _read_relative_regular(
                root_fd,
                path,
                maximum=16_777_216,
                description="implementation source",
            )
            if len(payload) != expected_size or hashlib.sha256(payload).hexdigest() != expected_sha256:
                raise PrepArtifact("SOURCE_FILE_IDENTITY", f"source identity differs: {path}")
            paths.append(path)
            preimage.append(
                {"path": path, "sha256": expected_sha256, "size_bytes": expected_size}
            )
        if len(paths) != len(set(paths)) or paths != sorted(
            paths, key=lambda value: value.encode("utf-8")
        ):
            raise PrepArtifact("SOURCE_PATH_CLOSURE", "source paths/order differ")
        if python_files != [path for path in paths if path.endswith(".py")]:
            raise PrepArtifact("PYTHON_SOURCE_CLOSURE", "Python source list differs")
        source_tree_sha256 = hashlib.sha256(_canonical_body(preimage)).hexdigest()
        if manifest.get("source_tree_sha256") != source_tree_sha256:
            raise PrepArtifact("SOURCE_TREE_SHA256", "source-tree SHA-256 differs")
        return (
            _file_identity(IMPLEMENTATION_MANIFEST_RELATIVE, manifest_payload),
            source_tree_sha256,
        )
    finally:
        os.close(root_fd)


def _normalize_modes(
    tracked_tree: Mapping[str, Mapping[str, str]], counters: dict[str, int]
) -> None:
    root_fd = _open_absolute_dir(CLONE_ROOT)
    tracked_executable = {
        path for path, item in tracked_tree.items() if item["mode"] == "100755"
    }
    discovered_count = 0

    def visit(directory_fd: int, relative: str) -> None:
        nonlocal discovered_count
        names = _bounded_sorted_entry_names(
            directory_fd,
            discovered_count,
            "mode-normalization tree",
        )
        discovered_count += len(names)
        for name in names:
            path = name if not relative else relative + "/" + name
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode):
                raise PrepArtifact("NORMALIZE_SYMLINK", f"symlink in clone: {path}")
            if stat.S_ISDIR(metadata.st_mode):
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=directory_fd,
                )
                try:
                    os.fchmod(child, 0o700)
                    visit(child, path)
                    _fsync_dir(child, counters)
                finally:
                    os.close(child)
            elif stat.S_ISREG(metadata.st_mode):
                if path.startswith(".git/"):
                    immutable = bool(
                        re.fullmatch(r"\.git/objects/[0-9a-f]{2}/[0-9a-f]{38}", path)
                        or re.fullmatch(
                            r"\.git/objects/pack/pack-[0-9a-f]{40}\.(?:pack|idx|rev)",
                            path,
                        )
                    )
                    mode = 0o400 if immutable else 0o600
                else:
                    mode = 0o700 if path in tracked_executable else 0o600
                file_fd = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=directory_fd,
                )
                try:
                    os.fchmod(file_fd, mode)
                finally:
                    os.close(file_fd)
            else:
                raise PrepArtifact("NORMALIZE_TYPE", f"forbidden clone type: {path}")

    try:
        visit(root_fd, "")
        _fsync_dir(root_fd, counters)
    finally:
        os.close(root_fd)


def _validate_git_admin(validation: Mapping[str, Any]) -> dict[str, Any]:
    git_root = CLONE_ROOT + "/.git"
    root_fd = _open_absolute_dir(git_root)
    inventory: list[dict[str, Any]] = []
    logical = 0
    allocated = 0
    discovered_count = 0

    def visit(directory_fd: int, relative: str) -> None:
        nonlocal logical, allocated, discovered_count
        names = _bounded_sorted_entry_names(
            directory_fd,
            discovered_count,
            "Git admin tree",
        )
        discovered_count += len(names)
        for name in names:
            path = name if not relative else relative + "/" + name
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if metadata.st_uid != os.geteuid():
                raise PrepArtifact("GIT_ADMIN_OWNER", f"Git admin owner differs: {path}")
            if stat.S_ISDIR(metadata.st_mode):
                expected_mode = 0o700
                object_type = "directory"
            elif stat.S_ISREG(metadata.st_mode):
                immutable = bool(
                    re.fullmatch(r"objects/[0-9a-f]{2}/[0-9a-f]{38}", path)
                    or re.fullmatch(
                        r"objects/pack/pack-[0-9a-f]{40}\.(?:pack|idx|rev)", path
                    )
                )
                expected_mode = 0o400 if immutable else 0o600
                object_type = "regular"
            else:
                raise PrepArtifact("GIT_ADMIN_TYPE", f"Git admin type differs: {path}")
            if stat.S_IMODE(metadata.st_mode) != expected_mode:
                raise PrepArtifact("GIT_ADMIN_MODE", f"Git admin mode differs: {path}")
            item = {
                "allocated_bytes": int(metadata.st_blocks) * 512,
                "logical_bytes": int(metadata.st_size),
                "mode_octal": f"{expected_mode:04o}",
                "path": path,
                "type": object_type,
            }
            inventory.append(item)
            logical += item["logical_bytes"]
            allocated += item["allocated_bytes"]
            if (
                len(inventory) > ENTRY_LIMIT
                or logical > ISOLATION_LOGICAL_LIMIT
                or allocated > ISOLATION_ALLOCATED_LIMIT
            ):
                raise PrepResource(
                    "GIT_ADMIN_RESOURCE_CEILING",
                    "Git admin tree crossed an entry or byte ceiling: "
                    f"entries={len(inventory)},logical={logical},"
                    f"allocated={allocated}",
                )
            if stat.S_ISDIR(metadata.st_mode):
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=directory_fd,
                )
                try:
                    visit(child, path)
                finally:
                    os.close(child)

    try:
        visit(root_fd, "")
    finally:
        os.close(root_fd)
    if len(inventory) > ENTRY_LIMIT:
        raise PrepResource("GIT_ADMIN_ENTRY_LIMIT", "Git admin entries exceed cap")
    return {
        "allocated_bytes": allocated,
        "config_sha256": hashlib.sha256(validation["config_payload"]).hexdigest(),
        "entry_count": len(inventory),
        "fsck_stderr_sha256": hashlib.sha256(validation["fsck_stderr"]).hexdigest(),
        "fsck_stdout_sha256": hashlib.sha256(validation["fsck_stdout"]).hexdigest(),
        "head_ref": LOCAL_REF,
        "inventory_sha256": hashlib.sha256(_canonical_body(inventory)).hexdigest(),
        "logical_bytes": logical,
        "object_count": len(validation["all_objects"]),
        "reachable_object_count": len(validation["reachable"]),
        "ref_inventory_sha256": validation["ref_inventory_sha256"],
        "reflog_inventory_sha256": validation["reflog_inventory_sha256"],
        "unreachable_object_count": 0,
    }


def _decode_wait_status(raw_status: int) -> tuple[int | None, int | None]:
    if os.WIFEXITED(raw_status):
        return os.WEXITSTATUS(raw_status), None
    if os.WIFSIGNALED(raw_status):
        return None, os.WTERMSIG(raw_status)
    return None, None


def _close_worker_descriptors(worker: WorkerHandle) -> None:
    if not worker.process_reaped:
        raise PrepImplementation(
            "WORKER_DESCRIPTOR_CLOSE_ORDER",
            "worker descriptors cannot close before process reap closure",
        )
    first_error = worker.descriptor_close_failure
    for descriptor in sorted(worker.parent_open_fds):
        if descriptor in worker.unresolved_parent_fds:
            continue
        try:
            os.close(descriptor)
        except OSError as error:
            failure: PrepFailure
            if error.errno == errno.EBADF:
                failure = PrepImplementation(
                    "WORKER_FD_OWNERSHIP",
                    f"owned worker descriptor {descriptor} was already invalid",
                )
            else:
                failure = PrepResource(
                    "WORKER_FD_CLOSE",
                    f"owned worker descriptor {descriptor} close failed: {error}",
                )
            worker.unresolved_parent_fds.add(descriptor)
            first_error = _merge_failure(first_error, failure)
        else:
            worker.parent_open_fds.discard(descriptor)
    if first_error is not None:
        worker.descriptor_close_failure = first_error
        raise first_error
    if worker.parent_open_fds:
        raise PrepImplementation(
            "WORKER_FD_CLOSURE", "worker descriptor ownership did not drain"
        )
    worker.closed = True


def _reap_worker_and_orphans(
    worker: WorkerHandle,
    meter: PrepMeter,
    counters: dict[str, int],
    deadline_ns: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    while True:
        if time.monotonic_ns() >= deadline_ns:
            raise PrepResource(
                "WORKER_REAP_TIMEOUT", "worker did not exit before the wall deadline"
            )
        try:
            info = os.waitid(
                os.P_PID,
                worker.pid,
                os.WEXITED | os.WNOWAIT | os.WNOHANG,
            )
        except ChildProcessError as error:
            raise PrepResource(
                "WORKER_PROCESS_LOST", "worker disappeared before parent wait"
            ) from error
        if info is not None:
            if int(info.si_pid) != worker.pid:
                raise PrepImplementation(
                    "WORKER_WAITID_PID", "worker waitid PID differs"
                )
            break
        meter.sample_processes(force=True)
        if meter.pending_process_violation:
            raise PrepResource(
                "WORKER_REAP_RESOURCE_CEILING",
                "worker reap observed a process, RSS, or CPU ceiling violation",
            )
        time.sleep(0.01)
    worker_io = _proc_io(worker.pid)
    waited_pid, raw_status, usage = os.wait4(worker.pid, os.WNOHANG)
    if waited_pid != worker.pid:
        raise PrepImplementation("WORKER_WAIT_PID", "parent worker wait PID differs")
    worker_record = _wait_record(worker.pid, raw_status, usage, worker_io)
    records.append(worker_record)
    meter.add_wait_record(worker_record, account_completed_git_cpu=False)
    counters["reaped_process_count"] += 1
    while True:
        try:
            info = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOWAIT | os.WNOHANG)
        except ChildProcessError:
            break
        if info is None:
            raise PrepResource(
                "LIVE_ADOPTED_DESCENDANT",
                "a live adopted descendant remained after normal worker exit",
            )
        orphan_pid = int(info.si_pid)
        orphan_io = _proc_io(orphan_pid)
        waited_pid, raw_status, usage = os.wait4(orphan_pid, os.WNOHANG)
        if waited_pid != orphan_pid:
            raise PrepImplementation("ORPHAN_WAIT_PID", "orphan wait PID differs")
        record = _wait_record(waited_pid, raw_status, usage, orphan_io)
        records.append(record)
        meter.add_wait_record(record, account_completed_git_cpu=True)
        counters["reaped_process_count"] += 1
    try:
        os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG)
    except ChildProcessError:
        drained = True
    else:
        drained = False
    if not drained:
        raise PrepImplementation("WAIT_NOT_DRAINED", "wait closure did not reach ECHILD")
    worker.process_reaped = True
    return worker_record, records


def _stop_worker_successfully(
    worker: WorkerHandle,
    journal: HashJournal,
    meter: PrepMeter,
    counters: dict[str, int],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    worker.send({"kind": "STOP"})
    selector = selectors.DefaultSelector()
    selector.register(worker.event_read_fd, selectors.EVENT_READ)
    deadline = meter.context["start_monotonic_ns"] + PROCESS_FAMILY_WALL_LIMIT_NS
    done: dict[str, Any] | None = None
    try:
        while done is None:
            now = time.monotonic_ns()
            if now > deadline:
                raise PrepResource("WORKER_STOP_TIMEOUT", "worker stop exceeded wall cap")
            meter.sample_processes(force=True)
            if meter.pending_process_violation:
                _journal_resource_sample(
                    journal,
                    meter,
                    detail="observed worker-stop resource ceiling violation",
                )
            for _, _ in selector.select(0.01):
                for message in worker.reader.feed():
                    if message.get("kind") == "DONE":
                        expected_keys = {
                            "children_cpu_microseconds",
                            "children_maximum_rss_bytes",
                            "kind",
                            "self_cpu_microseconds",
                            "self_maximum_rss_bytes",
                        }
                        if set(message) != expected_keys:
                            raise PrepImplementation("WORKER_DONE_SHAPE", "DONE differs")
                        for key in expected_keys - {"kind"}:
                            _require_uint(message[key], "worker DONE " + key)
                        done = dict(message)
                        meter.sample_processes(force=True)
                        if meter.pending_process_violation:
                            _journal_resource_sample(
                                journal,
                                meter,
                                detail="observed worker-DONE resource ceiling violation",
                            )
                    elif message.get("kind") == "ERROR":
                        _raise_serialized_failure(
                            message, expected_kind="ERROR"
                        )
                    else:
                        raise PrepImplementation("WORKER_STOP_EVENT", "stop event differs")
    finally:
        selector.close()
    worker.close_parent_fd(worker.command_write_fd)
    worker.command_write_fd = -1
    worker_record, records = _reap_worker_and_orphans(
        worker, meter, counters, deadline
    )
    meter.worker_pgid = None
    meter.worker_group_verified = False
    if worker_record["signal_number"] is not None:
        raise PrepResource(
            "WORKER_SIGNAL",
            f"worker terminated by signal {worker_record['signal_number']}",
        )
    if worker_record["exit_code"] != 0:
        raise PrepImplementation("WORKER_EXIT", "worker did not exit zero")
    worker.done_message = done
    _close_worker_descriptors(worker)
    meter.sample_processes(force=True)
    return done, records


def _terminate_worker_group(
    worker: WorkerHandle,
    meter: PrepMeter,
    counters: dict[str, int],
    journal: HashJournal | None,
    detail: str,
) -> list[dict[str, Any]]:
    if worker.closed:
        return []
    if worker.process_reaped:
        meter.worker_pgid = None
        meter.worker_group_verified = False
        cleanup_failure: PrepFailure | None = None
        try:
            _close_worker_descriptors(worker)
        except BaseException as error:
            cleanup_failure = _merge_failure(
                cleanup_failure,
                _normalize_caught_failure(
                    error,
                    os_code="WORKER_DESCRIPTOR_CLOSE_OS_FAILURE",
                    resource_code="WORKER_DESCRIPTOR_CLOSE_RESOURCE_FAILURE",
                    implementation_code="WORKER_DESCRIPTOR_CLOSE_INVALID",
                ),
            )
        try:
            meter.sample_processes(force=True)
        except BaseException as error:
            cleanup_failure = _merge_failure(
                cleanup_failure,
                _normalize_caught_failure(
                    error,
                    os_code="POST_REAP_SAMPLE_OS_FAILURE",
                    resource_code="POST_REAP_SAMPLE_RESOURCE_FAILURE",
                    implementation_code="POST_REAP_SAMPLE_INVALID",
                ),
            )
        if cleanup_failure is not None:
            raise cleanup_failure
        return []
    if not worker.group_verified:
        cleanup_failure: PrepFailure | None = None
        records: list[dict[str, Any]] = []
        try:
            worker.close_parent_fd(worker.command_write_fd)
        except BaseException as error:
            cleanup_failure = _merge_failure(
                cleanup_failure,
                _normalize_caught_failure(
                    error,
                    os_code="UNVERIFIED_WORKER_EOF_OS_FAILURE",
                    resource_code="UNVERIFIED_WORKER_EOF_RESOURCE_FAILURE",
                    implementation_code="UNVERIFIED_WORKER_EOF_INVALID",
                ),
            )
        else:
            worker.command_write_fd = -1
        reap_deadline = time.monotonic_ns() + TERM_GRACE_NS
        while time.monotonic_ns() < reap_deadline:
            try:
                waited_pid, raw_status, usage = os.wait4(worker.pid, os.WNOHANG)
            except ChildProcessError:
                worker.process_reaped = True
                break
            if waited_pid == worker.pid:
                worker.process_reaped = True
                try:
                    record = _wait_record(worker.pid, raw_status, usage, None)
                    meter.add_wait_record(
                        record, account_completed_git_cpu=False
                    )
                    counters["reaped_process_count"] += 1
                    records.append(record)
                except BaseException as error:
                    cleanup_failure = _merge_failure(
                        cleanup_failure,
                        _normalize_caught_failure(
                            error,
                            os_code="UNVERIFIED_WORKER_WAIT_OS_FAILURE",
                            resource_code="UNVERIFIED_WORKER_WAIT_RESOURCE_FAILURE",
                            implementation_code="UNVERIFIED_WORKER_WAIT_INVALID",
                        ),
                    )
                break
            if waited_pid != 0:
                raise PrepImplementation(
                    "UNVERIFIED_WORKER_WAIT_PID",
                    "unverified worker wait PID differs",
                )
            time.sleep(0.01)
        if not worker.process_reaped:
            raise PrepResource(
                "UNVERIFIED_WORKER_REAP_TIMEOUT",
                "unverified worker did not reap after command-channel EOF",
            )
        meter.worker_pgid = None
        meter.worker_group_verified = False
        try:
            _close_worker_descriptors(worker)
        except BaseException as error:
            cleanup_failure = _merge_failure(
                cleanup_failure,
                _normalize_caught_failure(
                    error,
                    os_code="WORKER_DESCRIPTOR_CLOSE_OS_FAILURE",
                    resource_code="WORKER_DESCRIPTOR_CLOSE_RESOURCE_FAILURE",
                    implementation_code="WORKER_DESCRIPTOR_CLOSE_INVALID",
                ),
            )
        try:
            meter.sample_processes(force=True)
        except BaseException as error:
            cleanup_failure = _merge_failure(
                cleanup_failure,
                _normalize_caught_failure(
                    error,
                    os_code="POST_REAP_SAMPLE_OS_FAILURE",
                    resource_code="POST_REAP_SAMPLE_RESOURCE_FAILURE",
                    implementation_code="POST_REAP_SAMPLE_INVALID",
                ),
            )
        if cleanup_failure is not None:
            raise cleanup_failure
        return records
    before: dict[str, Any] | None = None
    journal_failure: PrepFailure | None = None
    signal_failure: PrepFailure | None = None

    def signal_worker_group(signal_number: int, *, require_leader: bool) -> None:
        nonlocal signal_failure
        if not worker.group_verified:
            return
        try:
            if require_leader:
                observed_pgid = os.getpgid(worker.pid)
                if observed_pgid != worker.pid:
                    raise PrepArtifact(
                        "WORKER_GROUP_REVERIFICATION",
                        "worker leader PGID changed before signal",
                    )
            else:
                meter.sample_processes(force=True)
            os.kill(-worker.pid, signal_number)
        except ProcessLookupError:
            return
        except BaseException as error:
            signal_failure = _merge_failure(
                signal_failure,
                _normalize_caught_failure(
                    error,
                    os_code="PROCESS_GROUP_SIGNAL_OS_FAILURE",
                    resource_code="PROCESS_GROUP_SIGNAL_RESOURCE_FAILURE",
                    implementation_code="PROCESS_GROUP_SIGNAL_INVALID",
                ),
            )

    if journal is not None and not journal.closed and not journal.close_attempted:
        try:
            before = meter.snapshot(force=True)
            journal.append(
                record_type="INTENT",
                operation="TERMINATE_PROCESS_GROUP",
                argv=None,
                cwd="/",
                environment_sha256=hashlib.sha256(
                    _canonical_body(GIT_ENVIRONMENT)
                ).hexdigest(),
                status="PENDING",
                exit_code=None,
                signal_number=signal.SIGTERM,
                stdout_identity=None,
                stderr_identity=None,
                filesystem_snapshot_identity=_filesystem_identity(),
                resource_snapshot=before,
                detail=detail,
            )
        except BaseException as error:
            journal_failure = _merge_failure(
                journal_failure,
                _normalize_caught_failure(
                    error,
                    os_code="TERMINATION_JOURNAL_OS_FAILURE",
                    resource_code="TERMINATION_JOURNAL_RESOURCE_FAILURE",
                    implementation_code="TERMINATION_JOURNAL_INVALID",
                ),
            )
    signal_worker_group(signal.SIGTERM, require_leader=True)
    deadline = time.monotonic_ns() + TERM_GRACE_NS
    records: list[dict[str, Any]] = []
    worker_reaped = False
    while time.monotonic_ns() < deadline:
        try:
            waited_pid, raw_status, usage = os.wait4(worker.pid, os.WNOHANG)
        except ChildProcessError:
            worker_reaped = True
            break
        if waited_pid == worker.pid:
            record = _wait_record(worker.pid, raw_status, usage, None)
            meter.add_wait_record(record, account_completed_git_cpu=False)
            counters["reaped_process_count"] += 1
            records.append(record)
            worker_reaped = True
            break
        time.sleep(0.01)
    if not worker_reaped:
        signal_worker_group(signal.SIGKILL, require_leader=True)
        kill_deadline = time.monotonic_ns() + TERM_GRACE_NS
        while time.monotonic_ns() < kill_deadline:
            try:
                waited_pid, raw_status, usage = os.wait4(worker.pid, os.WNOHANG)
            except ChildProcessError:
                worker_reaped = True
                break
            if waited_pid == worker.pid:
                record = _wait_record(worker.pid, raw_status, usage, None)
                meter.add_wait_record(record, account_completed_git_cpu=False)
                counters["reaped_process_count"] += 1
                records.append(record)
                worker_reaped = True
                break
            time.sleep(0.01)
        if not worker_reaped:
            raise PrepResource("WORKER_REAP_TIMEOUT", "worker did not reap after SIGKILL")
    try:
        remaining = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOWAIT | os.WNOHANG)
    except ChildProcessError:
        remaining = False
    if remaining is not False:
        signal_worker_group(signal.SIGKILL, require_leader=False)
    drain_deadline = time.monotonic_ns() + TERM_GRACE_NS
    while True:
        try:
            orphan_pid, raw_status, usage = os.wait4(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if orphan_pid == 0:
            if time.monotonic_ns() >= drain_deadline:
                raise PrepResource(
                    "ADOPTED_REAP_TIMEOUT",
                    "adopted descendants did not drain after SIGKILL",
                )
            time.sleep(0.01)
            continue
        record = _wait_record(orphan_pid, raw_status, usage, None)
        records.append(record)
        meter.add_wait_record(record, account_completed_git_cpu=True)
        counters["reaped_process_count"] += 1
    worker.process_reaped = True
    meter.worker_pgid = None
    meter.worker_group_verified = False
    cleanup_failure: PrepFailure | None = None
    try:
        _close_worker_descriptors(worker)
    except BaseException as error:
        cleanup_failure = _merge_failure(
            cleanup_failure,
            _normalize_caught_failure(
                error,
                os_code="WORKER_DESCRIPTOR_CLOSE_OS_FAILURE",
                resource_code="WORKER_DESCRIPTOR_CLOSE_RESOURCE_FAILURE",
                implementation_code="WORKER_DESCRIPTOR_CLOSE_INVALID",
            ),
        )
    try:
        meter.sample_processes(force=True)
    except BaseException as error:
        cleanup_failure = _merge_failure(
            cleanup_failure,
            _normalize_caught_failure(
                error,
                os_code="POST_TERMINATION_SAMPLE_OS_FAILURE",
                resource_code="POST_TERMINATION_SAMPLE_RESOURCE_FAILURE",
                implementation_code="POST_TERMINATION_SAMPLE_INVALID",
            ),
        )
    if journal is not None and not journal.closed and not journal.close_attempted:
        try:
            after = meter.snapshot(force=True)
            journal.append(
                record_type="RESULT",
                operation="TERMINATE_PROCESS_GROUP",
                argv=None,
                cwd="/",
                environment_sha256=hashlib.sha256(
                    _canonical_body(GIT_ENVIRONMENT)
                ).hexdigest(),
                status="OK",
                exit_code=None,
                signal_number=None,
                stdout_identity=None,
                stderr_identity=None,
                filesystem_snapshot_identity=_filesystem_identity(),
                resource_snapshot=after,
                detail="worker process group signalled and reaped",
            )
        except BaseException as error:
            journal_failure = _merge_failure(
                journal_failure,
                _normalize_caught_failure(
                    error,
                    os_code="TERMINATION_JOURNAL_OS_FAILURE",
                    resource_code="TERMINATION_JOURNAL_RESOURCE_FAILURE",
                    implementation_code="TERMINATION_JOURNAL_INVALID",
                ),
            )
    combined_failure = _merge_failure(signal_failure, journal_failure)
    combined_failure = _merge_failure(combined_failure, cleanup_failure)
    if combined_failure is not None:
        raise combined_failure
    return records


def _create_namespace_and_journal(
    counters: dict[str, int],
    context: Mapping[str, Any],
    state: dict[str, Any],
) -> tuple[HashJournal, PrepMeter]:
    tmp_fd = _open_absolute_dir("/tmp")
    try:
        tmp_meta = os.fstat(tmp_fd)
        try:
            os.stat(os.path.basename(ISOLATION_ROOT), dir_fd=tmp_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise PrepPrecondition(
                "ISOLATION_NAMESPACE_PRESENT", "isolation namespace is not absent"
            )
        root_fd = _mkdir_new(
            tmp_fd,
            os.path.basename(ISOLATION_ROOT),
            counters,
            exists_is_precondition=True,
        )
        state["root_created"] = True
    finally:
        os.close(tmp_fd)
    try:
        root_meta = os.fstat(root_fd)
        if root_meta.st_dev != tmp_meta.st_dev:
            raise PrepArtifact("ISOLATION_DEVICE", "isolation device differs")
        journal_dir_fd = _mkdir_new(root_fd, "prep-attempt", counters)
        try:
            try:
                journal_fd = os.open(
                    "clone_operations.jsonl",
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | os.O_NOFOLLOW
                    | os.O_CLOEXEC,
                    0o600,
                    dir_fd=journal_dir_fd,
                )
            except FileExistsError as error:
                raise PrepArtifact(
                    "POST_ROOT_JOURNAL_COLLISION",
                    "owned post-root journal path already exists",
                ) from error
            except OSError as error:
                raise PrepResource(
                    "JOURNAL_CREATE_FAILED", f"journal creation failed: {error}"
                ) from error
            journal = HashJournal(journal_fd, OUTER_JOURNAL_PATH, counters)
            state["journal"] = journal
            counters["supervisor_file_create_count"] += 1
            os.fsync(journal_fd)
            counters["supervisor_file_fsync_count"] += 1
            _fsync_dir(journal_dir_fd, counters)
        finally:
            os.close(journal_dir_fd)
        meter = PrepMeter(context)
        state["meter"] = meter
        snapshot = meter.snapshot(force=True)
        journal.append(
            record_type="RESULT",
            operation="CREATE_NAMESPACE",
            argv=None,
            cwd="/",
            environment_sha256=hashlib.sha256(
                _canonical_body(GIT_ENVIRONMENT)
            ).hexdigest(),
            status="OK",
            exit_code=None,
            signal_number=None,
            stdout_identity=None,
            stderr_identity=None,
            filesystem_snapshot_identity=_filesystem_identity(),
            resource_snapshot=snapshot,
            detail="exclusive isolation namespace and outer journal created",
        )
        journal.append(
            record_type="INTENT",
            operation="CREATE_GIT_ENVIRONMENT",
            argv=None,
            cwd="/",
            environment_sha256=hashlib.sha256(
                _canonical_body(GIT_ENVIRONMENT)
            ).hexdigest(),
            status="PENDING",
            exit_code=None,
            signal_number=None,
            stdout_identity=None,
            stderr_identity=None,
            filesystem_snapshot_identity=_filesystem_identity(),
            resource_snapshot=snapshot,
            detail="create empty HOME XDG and Git template directories",
        )
        for leaf in ("git-home", "git-xdg", "empty-git-template"):
            descriptor = _mkdir_new(root_fd, leaf, counters)
            try:
                if any(True for _ in os.scandir(descriptor)):
                    raise PrepArtifact("GIT_ENVIRONMENT_NOT_EMPTY", f"{leaf} is not empty")
                _fsync_dir(descriptor, counters)
            finally:
                os.close(descriptor)
        snapshot = meter.snapshot(force=True)
        journal.append(
            record_type="RESULT",
            operation="CREATE_GIT_ENVIRONMENT",
            argv=None,
            cwd="/",
            environment_sha256=hashlib.sha256(
                _canonical_body(GIT_ENVIRONMENT)
            ).hexdigest(),
            status="OK",
            exit_code=None,
            signal_number=None,
            stdout_identity=None,
            stderr_identity=None,
            filesystem_snapshot_identity=_filesystem_identity(),
            resource_snapshot=snapshot,
            detail="empty Git environment directories created and fsynced",
        )
        violations = meter.ceiling_violations(snapshot)
        if violations:
            raise PrepResource("OBSERVED_RESOURCE_CEILING", ",".join(violations))
        return journal, meter
    finally:
        os.close(root_fd)


def _clone_identity(
    execution_base: str,
    execution_tree: str,
    source_tree_sha256: str,
    tracked_worktree: Mapping[str, Any],
    object_count: int,
) -> dict[str, Any]:
    root_fd = _open_absolute_dir(CLONE_ROOT)
    try:
        metadata = os.fstat(root_fd)
    finally:
        os.close(root_fd)
    return {
        "branch": BRANCH,
        "clean_tree": True,
        "device_id": int(metadata.st_dev),
        "fetch_url": FETCH_URL,
        "git_common_dir": CLONE_ROOT + "/.git",
        "git_object_count": object_count,
        "head_commit": execution_base,
        "head_tree": execution_tree,
        "owner_uid": int(metadata.st_uid),
        "push_url": PUSH_URL,
        "root": CLONE_ROOT,
        "source_tree_sha256": source_tree_sha256,
        "worktree_entry_count": tracked_worktree["entry_count"],
    }


def _build_clone_inventory(
    context: Mapping[str, Any],
    validation: Mapping[str, Any],
    tracked_worktree: Mapping[str, Any],
    git_admin: Mapping[str, Any],
    absent_paths: list[str],
    host_executables: list[dict[str, Any]],
    source_manifest_identity: Mapping[str, Any],
    source_tree_sha256: str,
) -> dict[str, Any]:
    clone_identity = _clone_identity(
        context["execution_base_commit"],
        validation["execution_tree"],
        source_tree_sha256,
        tracked_worktree,
        len(validation["all_objects"]),
    )
    value = {
        "absent_paths": absent_paths,
        "artifact_kind": "a4_v2_isolated_clone_inventory",
        "clone_identity": clone_identity,
        "execution_base_commit": context["execution_base_commit"],
        "execution_base_tree": validation["execution_tree"],
        "git_admin": dict(git_admin),
        "git_environment": dict(GIT_ENVIRONMENT),
        "host_executables": host_executables,
        "resource_ceilings": dict(RESOURCE_CEILINGS),
        "schema_version": SCHEMA_VERSION,
        "source_manifest_identity": dict(source_manifest_identity),
        "source_tree_sha256": source_tree_sha256,
        "tracked_worktree": dict(tracked_worktree),
    }
    if set(value) != RECEIPT_INVENTORY_KEYS:
        raise PrepImplementation("INVENTORY_SHAPE", "clone inventory shape differs")
    return value


def _process_closure(
    worker: WorkerHandle,
    meter: PrepMeter,
    counters: Mapping[str, int],
) -> dict[str, Any]:
    descendant_count = max(
        len(meter.observed_descendant_pids), counters["spawned_process_count"]
    )
    return {
        "descendant_count": descendant_count,
        "live_process_count": 1,
        "parent_is_child_subreaper": True,
        "parent_outside_worker_group": True,
        "reaped_process_count": counters["reaped_process_count"],
        "wait_drained_to_echild": True,
        "worker_pgid": worker.pid,
        "worker_pid": worker.pid,
    }


def _append_receipt_install_intents(
    journal: HashJournal,
    meter: PrepMeter,
) -> None:
    for operation, detail in (
        ("WRITE_CLONE_INVENTORY", "install closed clone inventory"),
        ("COPY_OUTER_JOURNAL", "copy closed outer journal byte-for-byte"),
        ("WRITE_CLONE_POSTCHECK", "install closed clone postcheck"),
    ):
        snapshot = meter.snapshot(force=True)
        journal.append(
            record_type="INTENT",
            operation=operation,
            argv=None,
            cwd="/",
            environment_sha256=hashlib.sha256(
                _canonical_body(GIT_ENVIRONMENT)
            ).hexdigest(),
            status="PENDING",
            exit_code=None,
            signal_number=None,
            stdout_identity=None,
            stderr_identity=None,
            filesystem_snapshot_identity=_filesystem_identity(),
            resource_snapshot=snapshot,
            detail=detail,
        )
    snapshot = meter.snapshot(force=True)
    journal.append(
        record_type="READY_FOR_RECEIPT_INSTALL",
        operation="READY_FOR_RECEIPT_INSTALL",
        argv=None,
        cwd="/",
        environment_sha256=hashlib.sha256(_canonical_body(GIT_ENVIRONMENT)).hexdigest(),
        status="READY",
        exit_code=None,
        signal_number=None,
        stdout_identity=None,
        stderr_identity=None,
        filesystem_snapshot_identity=_filesystem_identity(),
        resource_snapshot=snapshot,
        detail="clone closed and ready for finite receipt installation",
    )


def _rename_noreplace(
    parent_fd: int, source: str, destination: str
) -> None:
    result = _RENAMEAT2(
        parent_fd,
        source.encode("ascii"),
        parent_fd,
        destination.encode("ascii"),
        RENAME_NOREPLACE,
    )
    if result != 0:
        code = ctypes.get_errno()
        if code == errno.EEXIST:
            raise PrepArtifact(
                "POST_ROOT_RECEIPT_COLLISION", "receipt final already exists"
            )
        raise PrepResource("RECEIPT_RENAME", f"renameat2 failed with errno {code}")


def _build_resource_ledger(
    context: Mapping[str, Any],
    capture: CaptureWriter,
    counters: dict[str, int],
    meter_stop: Mapping[str, int],
    filesystem: Mapping[str, Any],
    storage: Mapping[str, Mapping[str, int]],
    *,
    maximum_live_process_count: int,
    maximum_observed_rss_bytes: int,
) -> dict[str, Any]:
    counters["directory_entry_count"] = storage["directories"]["entry_count"]
    counters["file_entry_count"] = filesystem["entry_count"] - counters["directory_entry_count"]
    counters["completed_capture_write_syscall_count"] = sum(
        capture.write_count.values()
    )
    counters["completed_capture_write_bytes"] = sum(capture.write_bytes.values())
    for dimension in ("allocated_bytes", "entry_count", "logical_bytes"):
        if sum(category[dimension] for category in storage.values()) != filesystem[
            dimension
        ]:
            raise PrepImplementation("STORAGE_RECONCILIATION", "storage ledger differs")
    wall = meter_stop["monotonic_ns"] - context["start_monotonic_ns"]
    if wall < 0:
        raise PrepImplementation("NEGATIVE_WALL", "meter-stop wall is negative")
    ledger = {
        "isolation_allocated_bytes": filesystem["allocated_bytes"],
        "isolation_entry_count": filesystem["entry_count"],
        "isolation_logical_bytes": filesystem["logical_bytes"],
        "maximum_live_process_count": maximum_live_process_count,
        "maximum_observed_concurrent_process_family_rss_bytes": maximum_observed_rss_bytes,
        "network_bytes": {
            "reason": "UNAVAILABLE_NO_AUTHORITATIVE_COUNTER",
            "value": None,
        },
        "operation_counts": dict(counters),
        "process_family_cpu_microseconds": meter_stop[
            "process_family_cpu_microseconds"
        ],
        "stderr_capture_bytes": capture.logical[2],
        "stdout_capture_bytes": capture.logical[1],
        "storage_ledger": storage,
        "wall_nanoseconds": wall,
    }
    if (
        ledger["isolation_allocated_bytes"] > ISOLATION_ALLOCATED_LIMIT
        or ledger["isolation_entry_count"] > ENTRY_LIMIT
        or ledger["isolation_logical_bytes"] > ISOLATION_LOGICAL_LIMIT
        or ledger["maximum_live_process_count"] > LIVE_PROCESS_LIMIT
        or ledger["maximum_observed_concurrent_process_family_rss_bytes"]
        > MAXIMUM_OBSERVED_RSS_BYTES
        or ledger["process_family_cpu_microseconds"] > PROCESS_FAMILY_CPU_LIMIT_US
        or ledger["wall_nanoseconds"] > PROCESS_FAMILY_WALL_LIMIT_NS
        or ledger["stderr_capture_bytes"] > AGGREGATE_CAPTURE_CAP
        or ledger["stdout_capture_bytes"] > AGGREGATE_CAPTURE_CAP
    ):
        raise PrepResource("FINAL_RESOURCE_CEILING", "final resource ceiling exceeded")
    return ledger


def _install_receipt(
    context: Mapping[str, Any],
    journal: HashJournal,
    meter: PrepMeter,
    capture: CaptureWriter,
    counters: dict[str, int],
    worker: WorkerHandle,
    inventory: Mapping[str, Any],
    source_manifest_identity: Mapping[str, Any],
    source_tree_sha256: str,
    execution_tree: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _append_receipt_install_intents(journal, meter)
    journal.close()
    journal_payload, _ = _read_absolute_regular(
        OUTER_JOURNAL_PATH,
        maximum=JOURNAL_BYTE_CAP,
        description="closed outer journal",
    )
    if len(journal_payload) != journal.size_bytes:
        raise PrepImplementation("JOURNAL_CLOSED_SIZE", "closed journal size differs")
    outer_journal_identity = _file_identity(OUTER_JOURNAL_PATH, journal_payload)
    clone_fd = _open_absolute_dir(CLONE_ROOT)
    try:
        docs_fd = _open_relative_dir(clone_fd, "docs")
        try:
            staging_leaf = os.path.basename(RECEIPT_STAGING_RELATIVE)
            final_leaf = os.path.basename(RECEIPT_FINAL_RELATIVE)
            for leaf in (staging_leaf, final_leaf):
                try:
                    os.stat(leaf, dir_fd=docs_fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                raise PrepArtifact(
                    "POST_ROOT_RECEIPT_COLLISION",
                    f"receipt path exists after exclusive root creation: {leaf}",
                )
            staging_fd = _mkdir_new(docs_fd, staging_leaf, counters)
            try:
                inventory_payload = _canonical_document(dict(inventory))
                inventory_identity = _create_new_file(
                    staging_fd, "clone_inventory.json", inventory_payload, counters
                )
                journal_identity = _create_new_file(
                    staging_fd, "clone_operations.jsonl", journal_payload, counters
                )
                journal_identity["path"] = (
                    RECEIPT_FINAL_RELATIVE + "/clone_operations.jsonl"
                )
                pre_document_snapshot = meter.snapshot(force=True)
                postcheck = {
                    "artifact_kind": "a4_v2_isolated_clone_postcheck",
                    "cache_paths": [
                        {"path": path, "state": "ABSENT"}
                        for path in CACHE_RELATIVE_PATHS
                    ],
                    "checkpoint": "READY_FOR_RECEIPT_INSTALL_PRE_DOCUMENT",
                    "claim_ceiling": CLAIM_CEILING,
                    "clone_identity": dict(inventory["clone_identity"]),
                    "journal_copy_equal": True,
                    "journal_identity": journal_identity,
                    "pre_document_resource_snapshot": pre_document_snapshot,
                    "process_closure": _process_closure(worker, meter, counters),
                    "receipt_state": {
                        "final_exists": False,
                        "first_three_files_fsynced": True,
                        "staging_exists": True,
                        "staging_mode_octal": "0700",
                        "staging_owner_uid": os.geteuid(),
                    },
                    "schema_version": SCHEMA_VERSION,
                    "source_tree_sha256": source_tree_sha256,
                }
                if set(postcheck) != POSTCHECK_KEYS:
                    raise PrepImplementation("POSTCHECK_SHAPE", "clone postcheck differs")
                postcheck_payload = _canonical_document(postcheck)
                postcheck_identity = _create_new_file(
                    staging_fd, "clone_postcheck.json", postcheck_payload, counters
                )
                _fsync_dir(staging_fd, counters)
                frozen_filesystem, frozen_storage = _scan_tree(ISOLATION_ROOT)
                meter.sample_processes(force=True)
                maximum_live_process_count = meter.maximum_live_process_count
                maximum_observed_rss_bytes = meter.maximum_rss_bytes
                meter_stop = {
                    "monotonic_ns": time.monotonic_ns(),
                    "process_family_cpu_microseconds": _process_cpu_microseconds(),
                }
                ledger = _build_resource_ledger(
                    context,
                    capture,
                    counters,
                    meter_stop,
                    frozen_filesystem,
                    frozen_storage,
                    maximum_live_process_count=maximum_live_process_count,
                    maximum_observed_rss_bytes=maximum_observed_rss_bytes,
                )
                inventory_identity["path"] = (
                    RECEIPT_FINAL_RELATIVE + "/clone_inventory.json"
                )
                postcheck_identity["path"] = (
                    RECEIPT_FINAL_RELATIVE + "/clone_postcheck.json"
                )
                seal = {
                    "artifact_kind": "a4_v2_isolated_clone_prep_seal",
                    "claim_ceiling": CLAIM_CEILING,
                    "clone_inventory": inventory_identity,
                    "clone_operations": journal_identity,
                    "clone_postcheck": postcheck_identity,
                    "execution_base_commit": context["execution_base_commit"],
                    "execution_base_tree": execution_tree,
                    "journal_copy_equal": True,
                    "meter_start": {
                        "monotonic_ns": context["start_monotonic_ns"],
                        "process_family_cpu_microseconds": context[
                            "start_process_cpu_microseconds"
                        ],
                    },
                    "meter_stop": meter_stop,
                    "resource_ledger": ledger,
                    "schema_version": SCHEMA_VERSION,
                    "source_manifest_identity": dict(source_manifest_identity),
                    "source_tree_sha256": source_tree_sha256,
                    "tail_duration": "NOT_MEASURED_NOT_INTERPRETED",
                    "tail_rss": "NOT_MEASURED_NOT_INTERPRETED",
                }
                if set(seal) != PREP_SEAL_KEYS:
                    raise PrepImplementation("PREP_SEAL_SHAPE", "PREP seal differs")
                seal_payload = _canonical_document(seal)
                seal_identity = _create_new_file(
                    staging_fd, "prep_seal.json", seal_payload, counters
                )
                _fsync_dir(staging_fd, counters)
                names = _bounded_sorted_entry_names(
                    staging_fd,
                    0,
                    "receipt staging directory",
                )
                if names != sorted(RECEIPT_FILE_NAMES):
                    raise PrepArtifact("RECEIPT_FILE_SET", "receipt file set differs")
            finally:
                os.close(staging_fd)
            _rename_noreplace(docs_fd, staging_leaf, final_leaf)
            _fsync_dir(docs_fd, counters)
            if not _path_absent(docs_fd, staging_leaf):
                raise PrepArtifact("RECEIPT_STAGING_REMAINS", "receipt staging remains")
            final_meta = os.stat(final_leaf, dir_fd=docs_fd, follow_symlinks=False)
            if (
                not stat.S_ISDIR(final_meta.st_mode)
                or stat.S_IMODE(final_meta.st_mode) != 0o700
                or final_meta.st_uid != os.geteuid()
            ):
                raise PrepArtifact("RECEIPT_FINAL_IDENTITY", "receipt final differs")
        finally:
            os.close(docs_fd)
    finally:
        os.close(clone_fd)
    seal_identity["path"] = RECEIPT_FINAL_RELATIVE + "/prep_seal.json"
    return outer_journal_identity, seal_identity


def _append_physical_validation_records(
    journal: HashJournal,
    meter: PrepMeter,
    *,
    before: bool,
    detail: str,
) -> None:
    snapshot = meter.snapshot(force=True)
    journal.append(
        record_type="INTENT" if before else "RESULT",
        operation="VALIDATE_POSTCHECKOUT",
        argv=None,
        cwd="/",
        environment_sha256=hashlib.sha256(_canonical_body(GIT_ENVIRONMENT)).hexdigest(),
        status="PENDING" if before else "OK",
        exit_code=None,
        signal_number=None,
        stdout_identity=None,
        stderr_identity=None,
        filesystem_snapshot_identity=_filesystem_identity(),
        resource_snapshot=snapshot,
        detail=detail,
    )
    violations = meter.ceiling_violations(snapshot)
    if violations:
        raise PrepResource("OBSERVED_RESOURCE_CEILING", ",".join(violations))


def _perform_preparation(
    context: Mapping[str, Any],
    capture: CaptureWriter,
    counters: dict[str, int],
    state: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], int]:
    _validate_bootstrap_checks(context)
    if context["capture_policy"] != CAPTURE_POLICY:
        raise PrepImplementation("CAPTURE_POLICY", "bootstrap capture policy differs")
    host_executables = _host_executable_inventory()
    _set_and_verify_subreaper()
    journal, meter = _create_namespace_and_journal(counters, context, state)
    worker = WorkerHandle(
        context["execution_base_commit"], counters, meter, state
    )
    state["worker"] = worker
    meter.worker_pgid = worker.pid
    meter.sample_processes(force=True)
    _run_git_command(
        worker,
        journal,
        meter,
        capture,
        counters,
        operation="CLONE_NO_CHECKOUT",
        argv=CLONE_ARGV,
    )
    precheckout = _run_validation_suite(
        worker,
        journal,
        meter,
        capture,
        counters,
        context["execution_base_commit"],
        final_config=False,
    )
    checkout_argv = (
        *GIT_PREFIX,
        "-C",
        CLONE_ROOT,
        "checkout",
        "--force",
        "-B",
        BRANCH,
        context["execution_base_commit"],
    )
    _run_git_command(
        worker,
        journal,
        meter,
        capture,
        counters,
        operation="CHECKOUT_EXECUTION_BASE",
        argv=checkout_argv,
    )
    set_fetch_argv = (
        *GIT_PREFIX,
        "-C",
        CLONE_ROOT,
        "remote",
        "set-url",
        "origin",
        FETCH_URL,
    )
    _run_git_command(
        worker,
        journal,
        meter,
        capture,
        counters,
        operation="SET_FETCH_URL",
        argv=set_fetch_argv,
    )
    set_push_argv = (
        *GIT_PREFIX,
        "-C",
        CLONE_ROOT,
        "remote",
        "set-url",
        "--push",
        "origin",
        PUSH_URL,
    )
    _run_git_command(
        worker,
        journal,
        meter,
        capture,
        counters,
        operation="SET_PUSH_URL",
        argv=set_push_argv,
    )
    postcheckout = _run_validation_suite(
        worker,
        journal,
        meter,
        capture,
        counters,
        context["execution_base_commit"],
        final_config=True,
    )
    if (
        precheckout["execution_tree"] != postcheckout["execution_tree"]
        or precheckout["tracked_tree"] != postcheckout["tracked_tree"]
        or precheckout["all_objects"] != postcheckout["all_objects"]
    ):
        raise PrepArtifact("PRE_POST_GIT_CLOSURE", "pre/post Git closure differs")
    status_argv = (
        *GIT_PREFIX,
        "-C",
        CLONE_ROOT,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=no",
    )
    status_stdout, status_stderr, _ = _run_git_command(
        worker,
        journal,
        meter,
        capture,
        counters,
        operation="VALIDATE_POSTCHECKOUT",
        argv=status_argv,
    )
    if status_stdout or status_stderr:
        raise PrepArtifact("GIT_STATUS_NOT_CLEAN", "postcheckout Git status is not empty")
    _stop_worker_successfully(worker, journal, meter, counters)
    _append_physical_validation_records(
        journal,
        meter,
        before=True,
        detail="begin no-follow physical Git-tree and stage-absence validation",
    )
    _normalize_modes(postcheckout["tracked_tree"], counters)
    tracked_worktree = _validate_tracked_worktree(postcheckout["tracked_tree"])
    absent_paths = _validate_exact_absences()
    source_manifest_identity, source_tree_sha256 = _validate_source_manifest()
    git_admin = _validate_git_admin(postcheckout)
    _append_physical_validation_records(
        journal,
        meter,
        before=False,
        detail="physical Git-tree, source, admin and absence validation passed",
    )
    inventory = _build_clone_inventory(
        context,
        postcheckout,
        tracked_worktree,
        git_admin,
        absent_paths,
        host_executables,
        source_manifest_identity,
        source_tree_sha256,
    )
    outer_journal_identity, receipt_seal_identity = _install_receipt(
        context,
        journal,
        meter,
        capture,
        counters,
        worker,
        inventory,
        source_manifest_identity,
        source_tree_sha256,
        postcheckout["execution_tree"],
    )
    return outer_journal_identity, receipt_seal_identity, meter.maximum_rss_bytes


def _close_captures(
    capture: CaptureWriter,
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    PrepFailure | None,
]:
    if capture.close_attempted:
        stdout_identity: dict[str, Any] | None = None
        stderr_identity: dict[str, Any] | None = None
        if capture.closed_identities is not None:
            stdout_identity, stderr_identity = capture.closed_identities
        failure = capture.close_failure
        if not capture.closed and failure is None:
            failure = PrepImplementation(
                "CAPTURE_CLOSURE_STATE", "capture closure state is unresolved"
            )
        return stdout_identity, stderr_identity, failure
    try:
        stdout_identity, stderr_identity = capture.close_and_identify()
        return stdout_identity, stderr_identity, None
    except PrepFailure as error:
        if capture.closed_identities is None:
            return None, None, error
        return (
            capture.closed_identities[0],
            capture.closed_identities[1],
            error,
        )
    except OSError as error:
        return None, None, PrepResource("CAPTURE_CLOSE_IO", str(error))


def _outer_journal_identity_if_closed(
    journal: HashJournal | None,
) -> dict[str, Any] | None:
    if journal is None:
        return None
    if not journal.closed:
        journal.close()
    payload, _ = _read_absolute_regular(
        OUTER_JOURNAL_PATH,
        maximum=JOURNAL_BYTE_CAP,
        description="retained outer journal",
    )
    return _file_identity(OUTER_JOURNAL_PATH, payload)


def _normalize_caught_failure(
    error: BaseException,
    *,
    os_code: str,
    resource_code: str,
    implementation_code: str,
) -> PrepFailure:
    if isinstance(error, PrepFailure):
        return error
    if isinstance(error, (KeyboardInterrupt, MemoryError, TimeoutError)):
        return PrepResource(resource_code, type(error).__name__)
    detail = f"{type(error).__name__}:{error}"
    detail = detail.encode("utf-8", errors="replace")[:4_096].decode(
        "utf-8", errors="ignore"
    )
    if isinstance(error, OSError):
        return PrepResource(os_code, detail)
    return PrepImplementation(implementation_code, detail)


def _run_attempt(context: Mapping[str, Any]) -> int:
    capture_fds = context["capture_fds"]
    if (
        not isinstance(capture_fds, dict)
        or set(capture_fds) != {"stderr", "stdout"}
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in capture_fds.values()
        )
    ):
        raise PrepImplementation("CAPTURE_FDS", "bootstrap capture descriptors differ")
    if not isinstance(context["terminal_state"], dict):
        raise PrepImplementation("TERMINAL_STATE", "bootstrap terminal state differs")
    capture = CaptureWriter(
        capture_fds["stdout"],
        capture_fds["stderr"],
        context["terminal_state"],
    )
    counters = _empty_operation_counts()
    state: dict[str, Any] = {
        "journal": None,
        "meter": None,
        "root_created": False,
        "worker": None,
    }
    outer_journal_identity: dict[str, Any] | None = None
    receipt_seal_identity: dict[str, Any] | None = None
    stdout_identity: dict[str, Any] | None = None
    stderr_identity: dict[str, Any] | None = None
    maximum_rss_bytes = 0
    try:
        (
            outer_journal_identity,
            receipt_seal_identity,
            maximum_rss_bytes,
        ) = _perform_preparation(context, capture, counters, state)
        stdout_identity, stderr_identity = capture.close_and_identify()
        _publish_terminal(
            context,
            status="ISOLATED_CLONE_PREPARED_PENDING_COMMIT_REVIEW",
            code="ISOLATED_CLONE_PREPARED",
            detail="isolated clone receipt published pending commit and review",
            outer_journal_identity=outer_journal_identity,
            receipt_seal_identity=receipt_seal_identity,
            stdout_identity=stdout_identity,
            stderr_identity=stderr_identity,
            capture=capture,
            maximum_rss_bytes=maximum_rss_bytes,
        )
        return 0
    except BaseException as error:
        worker = state.get("worker")
        meter = state.get("meter")
        journal = state.get("journal")
        failure = _normalize_caught_failure(
            error,
            os_code="OPERATING_SYSTEM_RESOURCE_FAILURE",
            resource_code="RUNTIME_RESOURCE_FAILURE",
            implementation_code="UNCAUGHT_PREP_EXCEPTION",
        )
        if state["root_created"] and failure.status == "PRECONDITION_NOT_MET":
            failure = PrepImplementation(
                "POST_ROOT_PRECONDITION",
                "post-root failure was incorrectly classified as precondition: "
                + failure.code,
            )
        termination_failure: PrepFailure | None = None
        observation_failure: PrepFailure | None = None
        outer_journal_failure: PrepFailure | None = None
        capture_failure: PrepFailure | None = None
        if isinstance(meter, PrepMeter):
            maximum_rss_bytes = meter.maximum_rss_bytes
        else:
            own = resource.getrusage(resource.RUSAGE_SELF)
            maximum_rss_bytes = int(own.ru_maxrss) * 1024
            if maximum_rss_bytes < 0:
                raise PrepImplementation(
                    "NEGATIVE_RSS", "failure fallback ru_maxrss is negative"
                )
        if isinstance(worker, WorkerHandle) and not worker.closed and isinstance(meter, PrepMeter):
            try:
                _terminate_worker_group(
                    worker,
                    meter,
                    counters,
                    journal if isinstance(journal, HashJournal) else None,
                    "caught PREP failure requires group termination",
                )
            except BaseException as termination_error:
                termination_failure = _normalize_caught_failure(
                    termination_error,
                    os_code="PROCESS_GROUP_TERMINATION_OS_FAILURE",
                    resource_code="PROCESS_GROUP_TERMINATION_RESOURCE_FAILURE",
                    implementation_code="PROCESS_GROUP_TERMINATION_INVALID",
                )
        if isinstance(worker, WorkerHandle) and not worker.process_reaped:
            # Do not let the bootstrap publish a fallback while an unverified
            # worker remains live; command-channel EOF was the only safe stop.
            os._exit(70)
        if (
            isinstance(journal, HashJournal)
            and not journal.closed
            and not journal.close_attempted
            and isinstance(meter, PrepMeter)
        ):
            try:
                failure_snapshot = meter.snapshot(force=True)
                failure_violations = meter.ceiling_violations(failure_snapshot)
                journal.append(
                    record_type="SAMPLE",
                    operation="SAMPLE_RESOURCES",
                    argv=None,
                    cwd="/",
                    environment_sha256=hashlib.sha256(
                        _canonical_body(GIT_ENVIRONMENT)
                    ).hexdigest(),
                    status="OBSERVED",
                    exit_code=None,
                    signal_number=None,
                    stdout_identity=None,
                    stderr_identity=None,
                    filesystem_snapshot_identity=_filesystem_identity(),
                    resource_snapshot=failure_snapshot,
                    detail="final observed failure-boundary resource snapshot",
                )
                if failure_violations:
                    observation_failure = _merge_failure(
                        observation_failure,
                        PrepResource(
                            "FAILURE_BOUNDARY_RESOURCE_CEILING",
                            "observed ceiling violation: "
                            + ",".join(sorted(set(failure_violations))),
                        ),
                    )
            except BaseException as observation_error:
                observation_failure = _merge_failure(
                    observation_failure,
                    _normalize_caught_failure(
                        observation_error,
                        os_code="FAILURE_OBSERVATION_OS_FAILURE",
                        resource_code="FAILURE_OBSERVATION_RESOURCE_FAILURE",
                        implementation_code="FAILURE_OBSERVATION_INVALID",
                    ),
                )
        try:
            outer_journal_identity = _outer_journal_identity_if_closed(
                journal if isinstance(journal, HashJournal) else None
            )
        except BaseException as outer_error:
            outer_journal_identity = None
            outer_journal_failure = _normalize_caught_failure(
                outer_error,
                os_code="OUTER_JOURNAL_CLOSE_OS_FAILURE",
                resource_code="OUTER_JOURNAL_CLOSE_RESOURCE_FAILURE",
                implementation_code="OUTER_JOURNAL_CLOSE_INVALID",
            )
        if not capture.closed or capture.close_failure is not None:
            try:
                stdout_identity, stderr_identity, capture_failure = _close_captures(
                    capture
                )
            except BaseException as capture_error:
                stdout_identity = None
                stderr_identity = None
                capture_failure = _normalize_caught_failure(
                    capture_error,
                    os_code="CAPTURE_CLOSE_OS_FAILURE",
                    resource_code="CAPTURE_CLOSE_RESOURCE_FAILURE",
                    implementation_code="CAPTURE_CLOSE_INVALID",
                )
        if isinstance(meter, PrepMeter):
            try:
                meter.sample_processes(force=True)
                final_wall = time.monotonic_ns() - context["start_monotonic_ns"]
                if final_wall < 0:
                    raise PrepImplementation(
                        "NEGATIVE_WALL", "failure-terminal wall is negative"
                    )
                if (
                    meter.pending_process_violation
                    or final_wall > PROCESS_FAMILY_WALL_LIMIT_NS
                ):
                    observation_failure = _merge_failure(
                        observation_failure,
                        PrepResource(
                            "FAILURE_TERMINAL_RESOURCE_CEILING",
                            "failure-terminal process, RSS, CPU, or wall ceiling crossed",
                        ),
                    )
            except BaseException as final_sample_error:
                observation_failure = _merge_failure(
                    observation_failure,
                    _normalize_caught_failure(
                        final_sample_error,
                        os_code="FAILURE_TERMINAL_SAMPLE_OS_FAILURE",
                        resource_code="FAILURE_TERMINAL_SAMPLE_RESOURCE_FAILURE",
                        implementation_code="FAILURE_TERMINAL_SAMPLE_INVALID",
                    ),
                )
            maximum_rss_bytes = meter.maximum_rss_bytes
        for candidate in (
            observation_failure,
            capture_failure,
            outer_journal_failure,
            termination_failure,
        ):
            if (
                candidate is not None
                and state["root_created"]
                and candidate.status == "PRECONDITION_NOT_MET"
            ):
                candidate = PrepImplementation(
                    "POST_ROOT_PRECONDITION",
                    "post-root cleanup was incorrectly classified as precondition: "
                    + candidate.code,
                )
            selected = _merge_failure(failure, candidate)
            if selected is None:
                raise PrepImplementation(
                    "FAILURE_MERGE_EMPTY", "failure merge unexpectedly became empty"
                )
            failure = selected
        _publish_terminal(
            context,
            status=failure.status,
            code=failure.code,
            detail=failure.detail,
            outer_journal_identity=outer_journal_identity,
            receipt_seal_identity=receipt_seal_identity,
            stdout_identity=stdout_identity,
            stderr_identity=stderr_identity,
            capture=capture,
            maximum_rss_bytes=maximum_rss_bytes,
        )
        return 70


def _resource_snapshot(
    process_observations: list[dict[str, Any]],
    wait_records: list[dict[str, Any]],
    *,
    actual_live_process_count: int,
    actual_wait_record_count: int,
    maximum_observed_rss_bytes: int,
    process_family_cpu_microseconds: int,
) -> dict[str, Any]:
    filesystem, _ = _scan_tree(ISOLATION_ROOT)
    return {
        "isolation_allocated_bytes": filesystem["allocated_bytes"],
        "isolation_entry_count": filesystem["entry_count"],
        "isolation_logical_bytes": filesystem["logical_bytes"],
        "live_process_count": actual_live_process_count,
        "maximum_observed_concurrent_process_family_rss_bytes": maximum_observed_rss_bytes,
        "process_family_cpu_microseconds": process_family_cpu_microseconds,
        "process_observations": process_observations[:LIVE_PROCESS_LIMIT],
        "process_observation_overflow": actual_live_process_count > LIVE_PROCESS_LIMIT,
        "sample_monotonic_ns": time.monotonic_ns(),
        "wait_record_count": actual_wait_record_count,
        "wait_record_overflow": actual_wait_record_count > LIVE_PROCESS_LIMIT,
        "wait_records": wait_records[:LIVE_PROCESS_LIMIT],
    }


def _terminal_process_identity(
    context: Mapping[str, Any],
    *,
    exit_code: int | None,
    signal_number: int | None,
    maximum_rss_bytes: int,
) -> dict[str, Any]:
    wall_nanoseconds = time.monotonic_ns() - context["start_monotonic_ns"]
    if wall_nanoseconds < 0 or maximum_rss_bytes < 0:
        raise PrepImplementation("NEGATIVE_RESOURCE", "terminal resource is negative")
    return {
        "cpu_microseconds": _process_cpu_microseconds(),
        "exit_code": exit_code,
        "maximum_observed_concurrent_rss_bytes": maximum_rss_bytes,
        "pid": os.getpid(),
        "process_group_id": os.getpgrp(),
        "signal_number": signal_number,
        "start_time_clock_ticks": context["start_time_clock_ticks"],
        "wall_nanoseconds": wall_nanoseconds,
    }


def _source_gitdir_ledger(
    context: Mapping[str, Any], capture: CaptureWriter | None
) -> dict[str, int]:
    token_payload, token_meta = _read_absolute_regular(
        TOKEN_PATH, maximum=TOKEN_BYTE_CAP, description="PREP permanent token"
    )
    stdout_payload = b""
    stderr_payload = b""
    stdout_payload, stdout_meta = _read_absolute_regular(
        STDOUT_CAPTURE_PATH,
        maximum=AGGREGATE_CAPTURE_CAP,
        description="PREP stdout capture",
    )
    stderr_payload, stderr_meta = _read_absolute_regular(
        STDERR_CAPTURE_PATH,
        maximum=AGGREGATE_CAPTURE_CAP,
        description="PREP stderr capture",
    )
    return {
        "capture_bytes": len(stdout_payload) + len(stderr_payload),
        "source_git_common_dir_fsync_count_before_terminal": context["terminal_state"].get(
            "common_dir_fsync_count", 1
        ),
        "source_gitdir_created_entry_count_before_terminal": 1
        + int(stdout_meta is not None)
        + int(stderr_meta is not None),
        "start_token_allocated_bytes": int(token_meta.st_blocks) * 512,
        "start_token_file_fsync_count": 1,
        "start_token_logical_bytes": len(token_payload),
        "start_token_write_bytes": context["terminal_state"].get(
            "start_token_write_bytes", context["token_start_identity"]["size_bytes"]
        ),
        "start_token_write_syscall_count": context["terminal_state"].get(
            "start_token_write_syscall_count", 0
        ),
        "stderr_capture_allocated_bytes": (
            int(stderr_meta.st_blocks) * 512 if stderr_meta is not None else 0
        ),
        "stderr_capture_file_fsync_count": context["terminal_state"].get(
            "stderr_capture_file_fsync_count", 0
        ),
        "stderr_capture_logical_bytes": len(stderr_payload),
        "stderr_capture_write_bytes": (
            context["terminal_state"].get("stderr_capture_write_bytes", 0)
        ),
        "stderr_capture_write_syscall_count": (
            context["terminal_state"].get("stderr_capture_write_syscall_count", 0)
        ),
        "stdout_capture_allocated_bytes": (
            int(stdout_meta.st_blocks) * 512 if stdout_meta is not None else 0
        ),
        "stdout_capture_file_fsync_count": context["terminal_state"].get(
            "stdout_capture_file_fsync_count", 0
        ),
        "stdout_capture_logical_bytes": len(stdout_payload),
        "stdout_capture_write_bytes": (
            context["terminal_state"].get("stdout_capture_write_bytes", 0)
        ),
        "stdout_capture_write_syscall_count": (
            context["terminal_state"].get("stdout_capture_write_syscall_count", 0)
        ),
    }


def _verified_authority(context: Mapping[str, Any]) -> dict[str, Any]:
    checks = context["authority_checks"]
    expected = {
        "authorization",
        "authorization_review",
        "execution_base_commit",
        "source_head_commit",
    }
    if not isinstance(checks, dict) or set(checks) != expected:
        raise PrepImplementation("AUTHORITY_CHECK_SHAPE", "authority checks differ")
    return {key: dict(checks[key]) for key in sorted(checks)}


def _verified_host(context: Mapping[str, Any]) -> dict[str, Any]:
    checks = context["host_checks"]
    expected = {
        "bootstrap",
        "bootstrap_external",
        "env",
        "git",
        "git_checkout",
        "git_config",
        "git_fetch",
        "git_fsck",
        "git_index_pack",
        "git_remote_http",
        "git_remote_https",
        "git_unpack_objects",
        "prep_tool",
        "python",
    }
    if not isinstance(checks, dict) or set(checks) != expected:
        raise PrepImplementation("HOST_CHECK_SHAPE", "host checks differ")
    return {key: dict(checks[key]) for key in sorted(checks)}


def _publish_terminal(
    context: Mapping[str, Any],
    *,
    status: str,
    code: str,
    detail: str,
    outer_journal_identity: Mapping[str, Any] | None,
    receipt_seal_identity: Mapping[str, Any] | None,
    stdout_identity: Mapping[str, Any] | None,
    stderr_identity: Mapping[str, Any] | None,
    capture: CaptureWriter | None,
    maximum_rss_bytes: int,
) -> None:
    if status not in TERMINAL_STATUSES:
        raise PrepImplementation("TERMINAL_STATUS", "terminal status invalid")
    detail_payload = _require_text(detail, "terminal detail", maximum=4_096).encode(
        "utf-8"
    )
    record = {
        "outer_journal_identity": outer_journal_identity,
        "previous_record_sha256": context["token_start_identity"]["sha256"],
        "receipt_seal_identity": receipt_seal_identity,
        "record_type": "TERMINAL",
        "schema_version": SCHEMA_VERSION,
        "sequence": 1,
        "source_gitdir_pre_terminal_ledger": _source_gitdir_ledger(context, capture),
        "status": status,
        "status_detail": {
            "code": _require_text(code, "terminal status code", maximum=128, ascii_only=True),
            "detail_sha256": hashlib.sha256(detail_payload).hexdigest(),
            "detail_size_bytes": len(detail_payload),
        },
        "stderr_capture_identity": stderr_identity,
        "stdout_capture_identity": stdout_identity,
        "terminal_process_identity": _terminal_process_identity(
            context,
            exit_code=0 if status == "ISOLATED_CLONE_PREPARED_PENDING_COMMIT_REVIEW" else None,
            signal_number=None,
            maximum_rss_bytes=maximum_rss_bytes,
        ),
        "verified_authority_identity": _verified_authority(context),
        "verified_host_identity": _verified_host(context),
    }
    context["append_terminal"](record)


def run_from_bootstrap(context: Mapping[str, Any]) -> int:
    """Run exactly one PREP attempt after the bootstrap's durable START.

    The full worker/Git/receipt state machine is below this reviewed entry
    surface.  Any exception is converted once into the frozen terminal token;
    no state is removed and no operation is retried.
    """

    if not isinstance(context, dict) or set(context) != BOOTSTRAP_CONTEXT_KEYS:
        raise PrepImplementation("BOOTSTRAP_CONTEXT", "bootstrap context differs")
    return _run_attempt(context)


__A4_V2_INLINE_BOOTSTRAP_RAW_BEGIN__ = """
import sys,posix
a=sys.argv
if len(a)!=12: raise RuntimeError("argv")
hx=lambda s,n:isinstance(s,str) and len(s)==n and s.isascii() and all(c in "0123456789abcdef" for c in s)
dc=lambda s:isinstance(s,str) and s.isascii() and s.isdecimal() and (s=="0" or s[0]!="0")
if not(hx(a[1],64) and dc(a[2]) and hx(a[3],64) and dc(a[4]) and hx(a[5],40) and hx(a[6],64) and dc(a[7]) and hx(a[8],64) and dc(a[9]) and hx(a[10],64) and dc(a[11])): raise RuntimeError("claims")
bs,bn,ps,pn,base,ts,tn,aus,aun,ars,arn=a[1],int(a[2]),a[3],int(a[4]),a[5],a[6],int(a[7]),a[8],int(a[9]),a[10],int(a[11])
if not(0<pn<bn<=65536 and 0<tn<=1048576 and 0<aun<=1048576 and 0<arn<=1048576): raise RuntimeError("caps")
if sys.__spec__.origin!="built-in" or posix.__spec__.origin!="built-in": raise RuntimeError("builtins")
if not(sys.flags.isolated==1 and sys.flags.ignore_environment==1 and sys.flags.no_site==1 and sys.flags.dont_write_bytecode==1 and sys.flags.optimize==0): raise RuntimeError("flags")
if posix.environ!={b"LANG":b"C",b"LC_ALL":b"C",b"PATH":b"/usr/bin:/bin"}: raise RuntimeError("environment")
posix.umask(0o077)
df=posix.O_RDONLY|posix.O_DIRECTORY|posix.O_NOFOLLOW|posix.O_CLOEXEC
d=posix.open("/",df)
for c in ("rwproject","kdd-db","kluaq","saq",".git"):
 n=posix.open(c,df,dir_fd=d);posix.close(d);d=n
start=("{\"capture_policy\":{\"aggregate_stderr_cap_bytes\":8388608,\"aggregate_stdout_cap_bytes\":8388608,\"format\":\"length_prefixed_multiplex_v1\",\"per_descendant_stderr_cap_bytes\":8388608,\"per_descendant_stdout_cap_bytes\":8388608,\"stderr_path\":\"/rwproject/kdd-db/kluaq/saq/.git/saq-a4-v2-isolated-prep.stderr\",\"stdout_path\":\"/rwproject/kdd-db/kluaq/saq/.git/saq-a4-v2-isolated-prep.stdout\"},\"claimed_authorization_identity\":{\"path\":\"docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md\",\"sha256\":\""+aus+"\",\"size_bytes\":"+str(aun)+"},\"claimed_authorization_review_identity\":{\"path\":\"docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md\",\"sha256\":\""+ars+"\",\"size_bytes\":"+str(arn)+"},\"claimed_bootstrap_identity\":{\"sha256\":\""+bs+"\",\"size_bytes\":"+str(bn)+"},\"claimed_execution_base_commit\":\""+base+"\",\"previous_record_sha256\":null,\"prologue_identity\":{\"sha256\":\""+ps+"\",\"size_bytes\":"+str(pn)+"},\"record_type\":\"START\",\"schema_version\":1,\"sequence\":0,\"source_git_common_dir_path\":\"/rwproject/kdd-db/kluaq/saq/.git\",\"umask_octal\":\"0077\"}\n").encode("ascii")
f=posix.open("saq-a4-v2-isolated-prep.lock",posix.O_WRONLY|posix.O_CREAT|posix.O_EXCL|posix.O_NOFOLLOW|posix.O_CLOEXEC,0o600,dir_fd=d)
off=sc=0
while off<len(start):
 w=posix.write(f,start[off:]);
 if w<=0: raise RuntimeError("write")
 off+=w;sc+=1
posix.fsync(f);posix.close(f);posix.fsync(d);posix.close(d)
# A4_V2_DURABLE_START_RAW_PREFIX_END
import hashlib,json,os,resource,stat,time
class BF(Exception):
 def __init__(self,status,code,detail): self.status,self.code,self.detail=status,code,detail;super().__init__(detail)
ROOT="/rwproject/kdd-db/kluaq/saq/.git"
TOKEN=ROOT+"/saq-a4-v2-isolated-prep.lock"
OUT=ROOT+"/saq-a4-v2-isolated-prep.stdout"
ERR=ROOT+"/saq-a4-v2-isolated-prep.stderr"
WT="/tmp/saq-arbitrary-cardinality-feasibility-v2"
TP="script/a4_v2_isolated_clone_prep.py"
AP="docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md"
RP="docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md"
CAP={"aggregate_stderr_cap_bytes":8388608,"aggregate_stdout_cap_bytes":8388608,"format":"length_prefixed_multiplex_v1","per_descendant_stderr_cap_bytes":8388608,"per_descendant_stdout_cap_bytes":8388608,"stderr_path":ERR,"stdout_path":OUT}
def rd(path,limit,pseudo=False):
 if not path.startswith("/") or os.path.normpath(path)!=path: raise BF("IMPLEMENTATION_INVALID","PATH","path")
 parts=path.split("/")[1:];q=os.open("/",df)
 try:
  for c in parts[:-1]:
   z=os.open(c,df,dir_fd=q);os.close(q);q=z
  z=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=q)
  try:
   m=os.fstat(z)
   if not stat.S_ISREG(m.st_mode) or m.st_size<0 or (not pseudo and m.st_size>limit): raise BF("ARTIFACT_INVALID","FILE_TYPE","file")
   b=bytearray()
   while True:
    x=os.read(z,min(65536,limit+1-len(b)))
    if not x: break
    b.extend(x)
    if len(b)>limit: raise BF("RESOURCE_INCOMPLETE_NO_DECISION","READ_CAP","read")
   n=os.fstat(z)
   if (m.st_dev,m.st_ino,m.st_mode,m.st_size,m.st_mtime_ns)!=(n.st_dev,n.st_ino,n.st_mode,n.st_size,n.st_mtime_ns): raise BF("ARTIFACT_INVALID","FILE_MUTATED","file")
   if not pseudo and len(b)!=m.st_size: raise BF("ARTIFACT_INVALID","FILE_SIZE","file")
   return bytes(b),n
  finally: os.close(z)
 finally: os.close(q)
def ident(path,b): return {"path":path,"sha256":hashlib.sha256(b).hexdigest(),"size_bytes":len(b)}
def exe(path,sha,size,target=None): return {"path":path,"sha256":sha,"size_bytes":size,"symlink_target":target,"type":"REGULAR" if target is None else "SYMLINK_TO_PINNED_TARGET"}
def check(expected): return {"expected":expected,"observed":None,"status":"UNAVAILABLE"}
authority={"authorization":check({"path":AP,"sha256":aus,"size_bytes":aun}),"authorization_review":check({"path":RP,"sha256":ars,"size_bytes":arn}),"execution_base_commit":check(base),"source_head_commit":check(base)}
host={"bootstrap":check({"sha256":bs,"size_bytes":bn}),"bootstrap_external":check(exe("/usr/lib64/python3.9/importlib/_bootstrap_external.py","8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4",66447)),"env":check(exe("/usr/bin/env","4fa9935734560713b5a6250fa3481d1044ad117f220bf32c802af382bb7e5c9b",45088)),"git":check(exe("/usr/bin/git","f7d0c1d79341f3d2d8e5c63f89c11400f48af55d8b659251c18cd7d13e3e4ed3",4397352)),"git_checkout":check(exe("/usr/libexec/git-core/git-checkout","c9cbed5f4adb8bff3cad9e95dcd8fa86548eb4ada0671cd9f888827308d8cf7b",13,"../../bin/git")),"git_config":check(exe("/usr/libexec/git-core/git-config","c9cbed5f4adb8bff3cad9e95dcd8fa86548eb4ada0671cd9f888827308d8cf7b",13,"../../bin/git")),"git_fetch":check(exe("/usr/libexec/git-core/git-fetch","c9cbed5f4adb8bff3cad9e95dcd8fa86548eb4ada0671cd9f888827308d8cf7b",13,"../../bin/git")),"git_fsck":check(exe("/usr/libexec/git-core/git-fsck","c9cbed5f4adb8bff3cad9e95dcd8fa86548eb4ada0671cd9f888827308d8cf7b",13,"../../bin/git")),"git_index_pack":check(exe("/usr/libexec/git-core/git-index-pack","c9cbed5f4adb8bff3cad9e95dcd8fa86548eb4ada0671cd9f888827308d8cf7b",13,"../../bin/git")),"git_remote_http":check(exe("/usr/libexec/git-core/git-remote-http","c2c458ee6ecadbb1b95fce9bef7f990a51f6486d06dae3621f8997757380a902",966840)),"git_remote_https":check(exe("/usr/libexec/git-core/git-remote-https","e2909ed8f8e19a7f87e0e57c2bebf7851351f3a949c5e6c60e2bf419f65bb7aa",15,"git-remote-http")),"git_unpack_objects":check(exe("/usr/libexec/git-core/git-unpack-objects","c9cbed5f4adb8bff3cad9e95dcd8fa86548eb4ada0671cd9f888827308d8cf7b",13,"../../bin/git")),"prep_tool":check({"path":TP,"sha256":ts,"size_bytes":tn}),"python":check(exe("/usr/bin/python3.9","c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0",15448))}
state={"common_dir_fsync_count":1,"start_token_write_bytes":len(start),"start_token_write_syscall_count":sc,"stderr_capture_file_fsync_count":0,"stderr_capture_write_bytes":0,"stderr_capture_write_syscall_count":0,"stdout_capture_file_fsync_count":0,"stdout_capture_write_bytes":0,"stdout_capture_write_syscall_count":0}
captures={"stdout":None,"stderr":None};terminal_written=False;terminal_attempted=False
start_id={"sha256":hashlib.sha256(start).hexdigest(),"size_bytes":len(start)}
def openc():
 q=os.open("/",df)
 for c in ("rwproject","kdd-db","kluaq","saq",".git"):
  z=os.open(c,df,dir_fd=q);os.close(q);q=z
 return q
def append_terminal(rec):
 global terminal_written,terminal_attempted
 if terminal_attempted or terminal_written: raise BF("IMPLEMENTATION_INVALID","TERMINAL_DUPLICATE","terminal")
 terminal_attempted=True
 keys={"outer_journal_identity","previous_record_sha256","receipt_seal_identity","record_type","schema_version","sequence","source_gitdir_pre_terminal_ledger","status","status_detail","stderr_capture_identity","stdout_capture_identity","terminal_process_identity","verified_authority_identity","verified_host_identity"}
 if not isinstance(rec,dict) or set(rec)!=keys: raise BF("IMPLEMENTATION_INVALID","TERMINAL_SHAPE","terminal")
 b=json.dumps(rec,allow_nan=False,ensure_ascii=True,separators=(",",":"),sort_keys=True).encode("ascii")+b"\n"
 old,_=rd(TOKEN,131072)
 if old!=start or len(old)+len(b)>131072: raise BF("IMPLEMENTATION_INVALID","TOKEN_STATE","token")
 q=openc()
 try:
  z=os.open("saq-a4-v2-isolated-prep.lock",os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=q)
  try:
   off=0
   while off<len(b):
    w=os.write(z,b[off:])
    if w<=0: raise BF("RESOURCE_INCOMPLETE_NO_DECISION","TOKEN_WRITE","token")
    off+=w
   os.fsync(z)
  finally: os.close(z)
  os.fsync(q)
 finally: os.close(q)
 terminal_written=True
def close_capture(name,path):
 fdv=captures[name];p=name+"_capture_"
 if fdv is None: return None,b"",None
 try: os.fsync(fdv);state[p+"file_fsync_count"]+=1
 finally: os.close(fdv)
 captures[name]=None
 try:
  b,m=rd(path,8388608);return {"path":path,"sha256":hashlib.sha256(b).hexdigest(),"size_bytes":len(b)},b,m
 except FileNotFoundError: return None,b"",None
def kernel_start():
 st,_=rd("/proc/self/stat",65536,True);tail=st[st.rfind(b") ")+2:].split()
 if len(tail)<22: raise BF("ARTIFACT_INVALID","PROC_STAT","proc")
 ticks=int(tail[19]);hz=os.sysconf("SC_CLK_TCK")
 if ticks<=0 or hz<=0: raise BF("IMPLEMENTATION_INVALID","PROCESS_START","proc")
 return ticks,ticks*1000000000//hz
def fallback_terminal(status,code,detail,start_ticks,start_ns):
 so,sob,som=close_capture("stdout",OUT);se,seb,sem=close_capture("stderr",ERR)
 tb,tm=rd(TOKEN,131072)
 ru=resource.getrusage(resource.RUSAGE_SELF);ch=resource.getrusage(resource.RUSAGE_CHILDREN)
 rss=int(ru.ru_maxrss)*1024
 cpu=int((ru.ru_utime+ru.ru_stime+ch.ru_utime+ch.ru_stime)*1000000)
 wall=time.monotonic_ns()-start_ns
 if rss<0 or cpu<0 or wall<0: raise BF("IMPLEMENTATION_INVALID","NEGATIVE_RESOURCE","resource")
 led={"capture_bytes":len(sob)+len(seb),"source_git_common_dir_fsync_count_before_terminal":state["common_dir_fsync_count"],"source_gitdir_created_entry_count_before_terminal":1+int(som is not None)+int(sem is not None),"start_token_allocated_bytes":tm.st_blocks*512,"start_token_file_fsync_count":1,"start_token_logical_bytes":len(tb),"start_token_write_bytes":state["start_token_write_bytes"],"start_token_write_syscall_count":state["start_token_write_syscall_count"],"stderr_capture_allocated_bytes":0 if sem is None else sem.st_blocks*512,"stderr_capture_file_fsync_count":state["stderr_capture_file_fsync_count"],"stderr_capture_logical_bytes":len(seb),"stderr_capture_write_bytes":state["stderr_capture_write_bytes"],"stderr_capture_write_syscall_count":state["stderr_capture_write_syscall_count"],"stdout_capture_allocated_bytes":0 if som is None else som.st_blocks*512,"stdout_capture_file_fsync_count":state["stdout_capture_file_fsync_count"],"stdout_capture_logical_bytes":len(sob),"stdout_capture_write_bytes":state["stdout_capture_write_bytes"],"stdout_capture_write_syscall_count":state["stdout_capture_write_syscall_count"]}
 db=detail.encode("utf-8",errors="replace")[:4096]
 rec={"outer_journal_identity":None,"previous_record_sha256":start_id["sha256"],"receipt_seal_identity":None,"record_type":"TERMINAL","schema_version":1,"sequence":1,"source_gitdir_pre_terminal_ledger":led,"status":status,"status_detail":{"code":code[:128],"detail_sha256":hashlib.sha256(db).hexdigest(),"detail_size_bytes":len(db)},"stderr_capture_identity":se,"stdout_capture_identity":so,"terminal_process_identity":{"cpu_microseconds":cpu,"exit_code":None,"maximum_observed_concurrent_rss_bytes":rss,"pid":os.getpid(),"process_group_id":os.getpgrp(),"signal_number":None,"start_time_clock_ticks":start_ticks,"wall_nanoseconds":wall},"verified_authority_identity":authority,"verified_host_identity":host}
 append_terminal(rec)
def observe_file(chk,path,display,limit):
 try: b,_=rd(path,limit);o=ident(display,b)
 except FileNotFoundError: raise BF("PRECONDITION_NOT_MET","IDENTITY_UNAVAILABLE",display)
 except BF as e:
  if e.status in ("RESOURCE_INCOMPLETE_NO_DECISION","IMPLEMENTATION_INVALID"): raise
  raise BF("PRECONDITION_NOT_MET","IDENTITY_UNAVAILABLE",display)
 chk["observed"]=o;chk["status"]="MATCH" if o==chk["expected"] else "MISMATCH"
 if chk["status"]!="MATCH": raise BF("PRECONDITION_NOT_MET","IDENTITY_MISMATCH",display)
 return b
def source_read(path,limit,code,display):
 try: return rd(path,limit)
 except FileNotFoundError: raise BF("PRECONDITION_NOT_MET",code,display)
 except BF as e:
  if e.status in ("RESOURCE_INCOMPLETE_NO_DECISION","IMPLEMENTATION_INVALID"): raise
  raise BF("PRECONDITION_NOT_MET",code,display)
def observe_exec(chk,path):
 e=chk["expected"]
 if e["type"]=="REGULAR":
  try: b,m=rd(path,8388608);o=exe(e["path"],hashlib.sha256(b).hexdigest(),len(b))
  except FileNotFoundError: raise BF("ARTIFACT_INVALID","EXEC_UNAVAILABLE",path)
 else:
  q=None
  try:
   q=os.open(os.path.dirname(path),df);leaf=os.path.basename(path);m=os.stat(leaf,dir_fd=q,follow_symlinks=False)
   if not stat.S_ISLNK(m.st_mode): raise BF("ARTIFACT_INVALID","LINK_TYPE",path)
   t=os.readlink(leaf,dir_fd=q);n=os.stat(leaf,dir_fd=q,follow_symlinks=False)
   try: b=t.encode("ascii")
   except UnicodeError: raise BF("ARTIFACT_INVALID","LINK_ENCODING",path)
   if (m.st_dev,m.st_ino,m.st_mode,m.st_size,m.st_mtime_ns)!=(n.st_dev,n.st_ino,n.st_mode,n.st_size,n.st_mtime_ns) or m.st_size!=len(b): raise BF("ARTIFACT_INVALID","LINK_MUTATED",path)
   o=exe(e["path"],hashlib.sha256(b).hexdigest(),len(b),t)
  except FileNotFoundError: raise BF("ARTIFACT_INVALID","LINK_UNAVAILABLE",path)
  finally:
   if q is not None: os.close(q)
 chk["observed"]=o;chk["status"]="MATCH" if o==e else "MISMATCH"
 if chk["status"]!="MATCH": raise BF("ARTIFACT_INVALID","EXEC_MISMATCH",path)
 return b
exit_code=70;start_ticks=None;start_ns=None;ns=None;prep_entered=False
try:
 q=openc()
 try:
  for name,path in (("stdout",OUT),("stderr",ERR)):
   z=os.open(os.path.basename(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=q);captures[name]=z;os.fsync(z);state[name+"_capture_file_fsync_count"]=1;os.fsync(q);state["common_dir_fsync_count"]+=1
 finally: os.close(q)
 start_ticks,start_ns=kernel_start()
 cmd,_=rd("/proc/self/cmdline",131072,True);v=cmd.split(b"\0")
 if len(v)!=18 or v[-1]!=b"" or v[0]!=b"/usr/bin/python3.9" or v[1:5]!=[b"-I",b"-B",b"-S",b"-c"]: raise BF("ARTIFACT_INVALID","CMDLINE","cmdline")
 src=v[5]
 if v[6:17]!=[x.encode("ascii") for x in a[1:]]: raise BF("ARTIFACT_INVALID","CMDLINE_CLAIMS","cmdline")
 actual={"sha256":hashlib.sha256(src).hexdigest(),"size_bytes":len(src)};host["bootstrap"]["observed"]=actual;host["bootstrap"]["status"]="MATCH" if actual==host["bootstrap"]["expected"] else "MISMATCH"
 if host["bootstrap"]["status"]!="MATCH" or hashlib.sha256(src[:pn]).hexdigest()!=ps or len(src[:pn])!=pn or not src[pn:].startswith(b"# A4_V2_DURABLE_START_RAW_PREFIX_END\n"): raise BF("ARTIFACT_INVALID","BOOTSTRAP_IDENTITY","bootstrap")
 if os.getcwd()!="/" or sys.path!=["/usr/lib64/python39.zip","/usr/lib64/python3.9","/usr/lib64/python3.9/lib-dynload"] or sys.pycache_prefix is not None or not sys.dont_write_bytecode: raise BF("ARTIFACT_INVALID","PYTHON_RUNTIME","runtime")
 observe_exec(host["env"],"/usr/bin/env");observe_exec(host["python"],"/usr/bin/python3.9");observe_exec(host["bootstrap_external"],"/usr/lib64/python3.9/importlib/_bootstrap_external.py");observe_exec(host["git"],"/usr/bin/git");observe_exec(host["git_remote_http"],"/usr/libexec/git-core/git-remote-http");observe_exec(host["git_remote_https"],"/usr/libexec/git-core/git-remote-https")
 for k in ("git_checkout","git_config","git_fetch","git_fsck","git_index_pack","git_unpack_objects"): observe_exec(host[k],host[k]["expected"]["path"])
 py,_=rd("/usr/bin/python3.9",8388608);pe=os.open("/proc/self/exe",os.O_RDONLY|os.O_CLOEXEC);pm=os.fstat(pe);pf=os.stat("/usr/bin/python3.9");os.close(pe)
 if (pm.st_dev,pm.st_ino)!=(pf.st_dev,pf.st_ino): host["python"]["status"]="MISMATCH";raise BF("ARTIFACT_INVALID","PYTHON_LEADER","python")
 tool=observe_file(host["prep_tool"],WT+"/"+TP,TP,1048576);observe_file(authority["authorization"],WT+"/"+AP,AP,1048576);observe_file(authority["authorization_review"],WT+"/"+RP,RP,1048576)
 link,_=source_read(WT+"/.git",4096,"SOURCE_GITDIR_UNAVAILABLE","gitdir")
 gitdir="/rwproject/kdd-db/kluaq/saq/.git/worktrees/saq-arbitrary-cardinality-feasibility-v2"
 if link!=("gitdir: "+gitdir+"\n").encode("ascii"): raise BF("PRECONDITION_NOT_MET","SOURCE_GITDIR_LINK","gitdir")
 head,_=source_read(gitdir+"/HEAD",4096,"SOURCE_HEAD_UNAVAILABLE","HEAD")
 if head!=("ref: refs/heads/saq-arbitrary-cardinality-feasibility-v2\n").encode("ascii"): raise BF("PRECONDITION_NOT_MET","SOURCE_HEAD_REF","HEAD")
 ref,_=source_read(ROOT+"/refs/heads/saq-arbitrary-cardinality-feasibility-v2",4096,"SOURCE_HEAD_OID_UNAVAILABLE","HEAD")
 try: oid=ref.decode("ascii").strip()
 except UnicodeError: raise BF("PRECONDITION_NOT_MET","SOURCE_HEAD_OID_UNAVAILABLE","HEAD")
 if not hx(oid,40): raise BF("PRECONDITION_NOT_MET","SOURCE_HEAD_OID_INVALID","HEAD")
 for k in ("execution_base_commit","source_head_commit"):
  authority[k]["observed"]=oid;authority[k]["status"]="MATCH" if oid==base else "MISMATCH"
 if oid!=base: raise BF("PRECONDITION_NOT_MET","SOURCE_HEAD_OID","HEAD")
 ns={"__builtins__":__builtins__,"__file__":TP,"__name__":"a4_v2_isolated_clone_prep"};exec(compile(tool,TP,"exec",dont_inherit=True,optimize=0),ns,ns)
 fn=ns.get("run_from_bootstrap")
 if not callable(fn): raise BF("IMPLEMENTATION_INVALID","PREP_ENTRYPOINT","prep")
 context={"append_terminal":append_terminal,"authority_checks":authority,"capture_fds":{"stderr":captures["stderr"],"stdout":captures["stdout"]},"capture_policy":CAP,"execution_base_commit":base,"host_checks":host,"prologue_identity":{"sha256":ps,"size_bytes":pn},"start_monotonic_ns":start_ns,"start_process_cpu_microseconds":0,"start_time_clock_ticks":start_ticks,"terminal_state":state,"token_start_identity":start_id}
 prep_entered=True
 exit_code=fn(context)
 if exit_code not in (0,70) or not terminal_written: raise BF("IMPLEMENTATION_INVALID","PREP_TERMINAL_MISSING","prep")
except BF as e:
 if start_ticks is None or start_ns is None: start_ticks,start_ns=kernel_start()
 if not prep_entered and not terminal_attempted and not terminal_written: fallback_terminal(e.status,e.code,e.detail,start_ticks,start_ns)
 exit_code=70
except (KeyboardInterrupt,MemoryError,TimeoutError) as e:
 if start_ticks is None or start_ns is None: start_ticks,start_ns=kernel_start()
 if not prep_entered and not terminal_attempted and not terminal_written: fallback_terminal("RESOURCE_INCOMPLETE_NO_DECISION","BOOTSTRAP_RESOURCE_FAILURE",type(e).__name__,start_ticks,start_ns)
 exit_code=70
except OSError as e:
 if start_ticks is None or start_ns is None: start_ticks,start_ns=kernel_start()
 if not prep_entered and not terminal_attempted and not terminal_written: fallback_terminal("RESOURCE_INCOMPLETE_NO_DECISION","BOOTSTRAP_OS_ERROR",type(e).__name__+":"+str(e),start_ticks,start_ns)
 exit_code=70
except BaseException as e:
 if start_ticks is None or start_ns is None: start_ticks,start_ns=kernel_start()
 if not prep_entered and not terminal_attempted and not terminal_written: fallback_terminal("IMPLEMENTATION_INVALID","BOOTSTRAP_EXCEPTION",type(e).__name__+":"+str(e),start_ticks,start_ns)
 exit_code=70
sys.exit(exit_code)
""" # __A4_V2_INLINE_BOOTSTRAP_RAW_END__
