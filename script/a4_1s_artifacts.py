#!/usr/bin/env python3
"""Canonical artifact and provenance helpers for the frozen A4-1S gate.

The module is intentionally limited to deterministic serialization,
provenance, path authorization, and build-manifest plumbing.  Importing it has
no filesystem side effects, does not import NumPy, and never generates a
fixture or executes a scientific gate.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 1
PROTOCOL_VERSION = "saq-attempt4-a4-1s-20260713-schema1"
STAGE = "A4-1S"
PARENT_PREREGISTRATION_COMMIT = (
    "3aa2f6e219763cfe72218050e420766a5a0efbcb"
)
ZERO_COMMIT = "0" * 40

REQUIRED_TRANSLATION_UNITS = (
    "research/a4_1s/a4_1s_native.cpp",
    "research/a4_1s/block_cli.cpp",
    "research/a4_1s/block_vq.cpp",
    "research/a4_1s/exact_quantizer.cpp",
    "research/a4_1s/numeric_runtime.cpp",
    "research/a4_1s/representation.cpp",
    "research/a4_1s/representation_cli.cpp",
)
MANDATORY_COMPILE_FLAGS = (
    "-std=c++20",
    "-O3",
    "-fno-fast-math",
    "-ffp-contract=off",
    "-frounding-math",
    "-mfpmath=sse",
)
FROZEN_THREAD_ENVIRONMENT = {
    "MKL_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
}

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMON_KEYS = frozenset(
    {
        "schema_version",
        "protocol_version",
        "stage",
        "status",
        "parent_preregistration_commit",
        "implementation_commit",
        "execution_commit",
        "command",
        "thread_environment",
        "input_ledger",
        "output_ledger",
    }
)


class ArtifactContractError(RuntimeError):
    """Raised when an A4-1S artifact or provenance contract is violated."""


@dataclass(frozen=True)
class FileIdentity:
    """Content identity returned by deterministic writers and hash helpers."""

    size_bytes: int
    sha256: str
    record_count: int | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }
        if self.record_count is not None:
            result["record_count"] = self.record_count
        return result


def _require_plain_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ArtifactContractError(f"{name} must be an integer >= {minimum}")
    return value


def _validate_json_value(value: Any, location: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ArtifactContractError(
                f"nonfinite JSON number at {location}; emit IEEE bits instead"
            )
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ArtifactContractError(
                    f"JSON object key at {location} is not a string"
                )
            _validate_json_value(child, f"{location}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_json_value(child, f"{location}[{index}]")
        return
    raise ArtifactContractError(
        f"unsupported JSON value {type(value).__name__} at {location}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes without a record delimiter."""

    _validate_json_value(value)
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise ArtifactContractError(f"value is not canonical JSON: {error}") from error
    return text.encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | os.PathLike[str], *, chunk_size: int = 1 << 20) -> str:
    _require_plain_int(chunk_size, "chunk_size", minimum=1)
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def file_identity(path: str | os.PathLike[str]) -> FileIdentity:
    target = Path(path)
    size = target.stat().st_size
    return FileIdentity(size_bytes=size, sha256=sha256_file(target))


def _write_mode(exclusive: bool) -> str:
    return "xb" if exclusive else "wb"


def write_canonical_json(
    path: str | os.PathLike[str],
    value: Any,
    *,
    exclusive: bool = True,
) -> FileIdentity:
    """Write one canonical JSON artifact without implicitly creating parents."""

    payload = canonical_json_bytes(value) + b"\n"
    with Path(path).open(_write_mode(exclusive)) as destination:
        destination.write(payload)
        destination.flush()
    return FileIdentity(size_bytes=len(payload), sha256=sha256_bytes(payload))


def write_canonical_json_lines(
    path: str | os.PathLike[str],
    records: Iterable[Mapping[str, Any]],
    *,
    exclusive: bool = True,
) -> FileIdentity:
    """Stream canonical JSONL and return its bytes, digest, and record count."""

    digest = hashlib.sha256()
    size_bytes = 0
    record_count = 0
    with Path(path).open(_write_mode(exclusive)) as destination:
        for record in records:
            if not isinstance(record, Mapping):
                raise ArtifactContractError("every JSONL record must be an object")
            line = canonical_json_bytes(record) + b"\n"
            destination.write(line)
            digest.update(line)
            size_bytes += len(line)
            record_count += 1
        destination.flush()
    return FileIdentity(
        size_bytes=size_bytes,
        sha256=digest.hexdigest(),
        record_count=record_count,
    )


def _validate_relative_ledger_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ArtifactContractError("ledger path must be a nonempty string")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise ArtifactContractError(f"ledger path is not normalized: {value!r}")
    if str(pure) != value or "\\" in value:
        raise ArtifactContractError(f"ledger path must be normalized POSIX: {value!r}")
    return value


def relative_posix_path(
    path: str | os.PathLike[str], root: str | os.PathLike[str]
) -> str:
    target = Path(path).resolve(strict=False)
    base = Path(root).resolve(strict=True)
    try:
        relative = target.relative_to(base)
    except ValueError as error:
        raise ArtifactContractError(f"path {target} is outside ledger root {base}") from error
    return _validate_relative_ledger_path(relative.as_posix())


def make_input_ledger_entry(
    file_path: str | os.PathLike[str],
    *,
    ledger_path: str,
    role: str,
) -> dict[str, Any]:
    identity = file_identity(file_path)
    if not isinstance(role, str) or not role:
        raise ArtifactContractError("input ledger role must be nonempty")
    return {
        "path": _validate_relative_ledger_path(ledger_path),
        "role": role,
        "sha256": identity.sha256,
        "size_bytes": identity.size_bytes,
    }


def make_output_ledger_entry(
    file_path: str | os.PathLike[str],
    *,
    ledger_path: str,
    role: str,
    timed: bool,
) -> dict[str, Any]:
    identity = file_identity(file_path)
    if not isinstance(role, str) or not role:
        raise ArtifactContractError("output ledger role must be nonempty")
    if not isinstance(timed, bool):
        raise ArtifactContractError("output ledger timed must be boolean")
    return {
        "path": _validate_relative_ledger_path(ledger_path),
        "role": role,
        "sha256": identity.sha256,
        "size_bytes": identity.size_bytes,
        "timed": timed,
    }


def make_detail_ledger_entry(
    file_path: str | os.PathLike[str],
    *,
    ledger_path: str,
    role: str,
    record_count: int,
    schema_version: int = SCHEMA_VERSION,
) -> dict[str, Any]:
    identity = file_identity(file_path)
    if not isinstance(role, str) or not role:
        raise ArtifactContractError("detail ledger role must be nonempty")
    return {
        "path": _validate_relative_ledger_path(ledger_path),
        "record_count": _require_plain_int(record_count, "record_count"),
        "role": role,
        "schema_version": _require_plain_int(
            schema_version, "schema_version", minimum=1
        ),
        "sha256": identity.sha256,
        "size_bytes": identity.size_bytes,
    }


def sort_ledger(entries: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized = [dict(entry) for entry in entries]
    for entry in normalized:
        _validate_relative_ledger_path(entry.get("path"))
    normalized.sort(key=lambda entry: entry["path"].encode("utf-8"))
    paths = [entry["path"] for entry in normalized]
    if len(paths) != len(set(paths)):
        raise ArtifactContractError("ledger contains duplicate paths")
    return normalized


def ordered_ledger_sha256(entries: Iterable[Mapping[str, Any]]) -> str:
    """Hash the canonical, path-sorted ledger array without a self-reference."""

    return sha256_bytes(canonical_json_bytes(sort_ledger(entries)))


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _lexical_absolute(path: str | os.PathLike[str], repo_root: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return Path(os.path.abspath(os.fspath(candidate)))


def _resolve_guard_path(path: Path, description: str) -> Path:
    try:
        return path.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise ArtifactContractError(
            f"cannot resolve {description} (possible symlink loop): {path}"
        ) from error


def guard_synthetic_read_path(
    path: str | os.PathLike[str],
    *,
    repo_root: str | os.PathLike[str],
    allowed_files: Iterable[str | os.PathLike[str]] = (),
    allowed_roots: Iterable[str | os.PathLike[str]] = (),
    extra_forbidden_roots: Iterable[str | os.PathLike[str]] = (),
    require_allowlist_match: bool = False,
) -> Path:
    """Reject repo data/results, registered data roots, and allowlist escapes.

    The function checks both the lexical path and the symlink-resolved path so
    an attempted open is rejected before any content is read.
    """

    try:
        repo = Path(repo_root).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ArtifactContractError(f"cannot resolve repository root: {repo_root}") from error
    lexical = _lexical_absolute(path, repo)
    resolved = _resolve_guard_path(lexical, "synthetic read/write path")

    # An exact allowlist entry must bind the bytes at that literal path.  If a
    # path component is a symlink, resolving both the candidate and allowlist
    # to the same external target would otherwise authorize bytes that are not
    # represented by the committed path's Git blob.
    if lexical != resolved:
        raise ArtifactContractError(
            f"synthetic read/write path may not traverse a symlink: {path}"
        )

    for candidate in (lexical, resolved):
        if _is_within(candidate, repo):
            relative = candidate.relative_to(repo)
            if any(part in {"data", "results"} for part in relative.parts):
                raise ArtifactContractError(
                    f"forbidden repository data/results path: {path}"
                )

    forbidden = [
        (
            _lexical_absolute(root, repo),
            _resolve_guard_path(
                _lexical_absolute(root, repo), "registered forbidden root"
            ),
        )
        for root in extra_forbidden_roots
    ]
    if any(
        _is_within(candidate, root) or candidate == root
        for candidate in (lexical, resolved)
        for roots in forbidden
        for root in roots
    ):
        raise ArtifactContractError(f"forbidden registered artifact path: {path}")

    exact_allowed: set[Path] = set()
    for item in allowed_files:
        allowed_lexical = _lexical_absolute(item, repo)
        allowed_resolved = _resolve_guard_path(allowed_lexical, "file allowlist entry")
        if allowed_lexical != allowed_resolved:
            raise ArtifactContractError(
                f"synthetic file allowlist may not traverse a symlink: {item}"
            )
        exact_allowed.add(allowed_resolved)
    root_allowed: list[Path] = []
    for item in allowed_roots:
        allowed_lexical = _lexical_absolute(item, repo)
        allowed_resolved = _resolve_guard_path(allowed_lexical, "root allowlist entry")
        if allowed_lexical != allowed_resolved:
            raise ArtifactContractError(
                f"synthetic root allowlist may not traverse a symlink: {item}"
            )
        root_allowed.append(allowed_resolved)
    matched = resolved in exact_allowed or any(
        _is_within(resolved, root) for root in root_allowed
    )
    if require_allowlist_match and not matched:
        raise ArtifactContractError(f"path is outside the synthetic read allowlist: {path}")
    return resolved


def _git(
    repo_root: str | os.PathLike[str], *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment.update({"GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"})
    process = subprocess.run(
        ["git", *arguments],
        cwd=Path(repo_root),
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise ArtifactContractError(
            f"git {' '.join(arguments)} failed ({process.returncode}): {detail}"
        )
    return process


def validate_commit(value: str, *, allow_zero: bool = False) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise ArtifactContractError(f"invalid 40-hex commit: {value!r}")
    if value == ZERO_COMMIT and not allow_zero:
        raise ArtifactContractError("zero commit sentinel is not allowed here")
    return value


def git_head_commit(repo_root: str | os.PathLike[str]) -> str:
    value = (
        _git(repo_root, "rev-parse", "--verify", "HEAD^{commit}")
        .stdout.decode("ascii")
        .strip()
    )
    return validate_commit(value)


def git_worktree_is_clean(repo_root: str | os.PathLike[str]) -> bool:
    status = _git(
        repo_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout
    return status == b""


def require_clean_execution_commit(
    repo_root: str | os.PathLike[str], *, expected_commit: str | None = None
) -> str:
    head = git_head_commit(repo_root)
    if expected_commit is not None and head != validate_commit(expected_commit):
        raise ArtifactContractError(
            f"execution commit mismatch: expected {expected_commit}, found {head}"
        )
    if not git_worktree_is_clean(repo_root):
        raise ArtifactContractError("A4-1S execution requires a clean worktree")
    return head


def git_blob_oid(
    repo_root: str | os.PathLike[str],
    repo_relative_path: str,
    *,
    commit: str = "HEAD",
) -> str:
    path = _validate_relative_ledger_path(repo_relative_path)
    if commit != "HEAD":
        validate_commit(commit)
    raw = _git(repo_root, "ls-tree", "-z", commit, "--", path).stdout
    records = [record for record in raw.split(b"\0") if record]
    if len(records) != 1 or b"\t" not in records[0]:
        raise ArtifactContractError(
            f"committed path is missing or ambiguous at {commit}:{path}"
        )
    metadata, encoded_path = records[0].split(b"\t", 1)
    try:
        mode, object_type, encoded_oid = metadata.decode("ascii").split()
        observed_path = encoded_path.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as error:
        raise ArtifactContractError(
            f"cannot parse Git tree entry at {commit}:{path}"
        ) from error
    if observed_path != path:
        raise ArtifactContractError(
            f"Git tree path mismatch: expected {path!r}, found {observed_path!r}"
        )
    if mode not in {"100644", "100755"} or object_type != "blob":
        raise ArtifactContractError(
            f"committed path is not a regular file at {commit}:{path} "
            f"(mode={mode}, type={object_type})"
        )
    if re.fullmatch(r"[0-9a-f]{40,64}", encoded_oid) is None:
        raise ArtifactContractError(f"invalid Git blob object id: {encoded_oid!r}")
    return encoded_oid


def git_commit_is_ancestor(
    repo_root: str | os.PathLike[str], ancestor: str, descendant: str
) -> bool:
    """Return whether two validated commits satisfy the required ancestry."""

    older = validate_commit(ancestor)
    newer = validate_commit(descendant)
    process = _git(
        repo_root,
        "merge-base",
        "--is-ancestor",
        older,
        newer,
        check=False,
    )
    if process.returncode == 0:
        return True
    if process.returncode == 1:
        return False
    detail = process.stderr.decode("utf-8", errors="replace").strip()
    raise ArtifactContractError(
        f"git merge-base --is-ancestor failed ({process.returncode}): {detail}"
    )


def git_last_modified_commit(
    repo_root: str | os.PathLike[str],
    repo_relative_path: str,
    *,
    commit: str = "HEAD",
) -> str:
    """Return the last commit at or before ``commit`` that changed ``path``."""

    path = _validate_relative_ledger_path(repo_relative_path)
    if commit != "HEAD":
        validate_commit(commit)
    raw = _git(
        repo_root,
        "log",
        "-1",
        "--format=%H",
        commit,
        "--",
        path,
    ).stdout
    try:
        value = raw.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise ArtifactContractError(
            f"cannot decode last-modified commit for {commit}:{path}"
        ) from error
    if not value:
        raise ArtifactContractError(
            f"no committed history for path at {commit}:{path}"
        )
    return validate_commit(value)


def _forbidden_compile_flag(argument: str) -> bool:
    if argument in {
        "-Ofast",
        "-ffast-math",
        "-fassociative-math",
        "-funsafe-math-optimizations",
        "-ffinite-math-only",
        "-freciprocal-math",
        "-mfma",
        "-march",
    }:
        return True
    if argument.startswith(("-Ofast=", "-march=")):
        return True
    if argument == "-mtune=native":
        return True
    if argument.startswith("-ffp-contract=") and argument != "-ffp-contract=off":
        return True
    return False


def validate_compile_argv(arguments: Sequence[str]) -> tuple[str, ...]:
    argv = tuple(arguments)
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ArtifactContractError("compiler argv must contain nonempty strings")
    missing = [flag for flag in MANDATORY_COMPILE_FLAGS if flag not in argv]
    forbidden = [argument for argument in argv if _forbidden_compile_flag(argument)]
    if missing or forbidden:
        raise ArtifactContractError(
            f"compile flag contract failed; missing={missing}, forbidden={forbidden}"
        )
    return argv


def load_and_validate_compile_commands(
    compile_commands_path: str | os.PathLike[str],
    *,
    repo_root: str | os.PathLike[str],
) -> list[dict[str, Any]]:
    """Load all seven frozen TU commands, retaining raw command and POSIX argv."""

    source_path = Path(compile_commands_path)
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ArtifactContractError(f"cannot read compile_commands.json: {error}") from error
    if not isinstance(payload, list):
        raise ArtifactContractError("compile_commands.json must be an array")
    if len(payload) != len(REQUIRED_TRANSLATION_UNITS):
        raise ArtifactContractError(
            "compile_commands.json must contain exactly the seven frozen target entries"
        )

    repo = Path(repo_root).resolve(strict=True)
    required = set(REQUIRED_TRANSLATION_UNITS)
    found: dict[str, dict[str, Any]] = {}
    for raw_entry in payload:
        if not isinstance(raw_entry, Mapping):
            raise ArtifactContractError("compile command entry must be an object")
        raw_file = raw_entry.get("file")
        raw_directory = raw_entry.get("directory")
        if not isinstance(raw_file, str) or not isinstance(raw_directory, str):
            raise ArtifactContractError("compile command requires string file/directory")
        file_path = Path(raw_file)
        if not file_path.is_absolute():
            file_path = Path(raw_directory) / file_path
        try:
            relative = file_path.resolve(strict=False).relative_to(repo).as_posix()
        except ValueError as error:
            raise ArtifactContractError(
                f"compile command source is outside the repository: {file_path}"
            ) from error
        if relative not in required:
            raise ArtifactContractError(
                f"unexpected target translation unit in compile commands: {relative}"
            )
        if relative in found:
            raise ArtifactContractError(f"duplicate compile command for {relative}")
        raw_command = raw_entry.get("command")
        if not isinstance(raw_command, str) or not raw_command:
            raise ArtifactContractError(
                f"compile command for {relative} lacks a raw command string"
            )
        try:
            argv = validate_compile_argv(shlex.split(raw_command, posix=True))
        except ValueError as error:
            raise ArtifactContractError(
                f"invalid POSIX shell quoting for {relative}: {error}"
            ) from error
        found[relative] = {
            "argv": list(argv),
            "raw_command": raw_command,
            "source_path": relative,
        }

    missing = sorted(required - found.keys())
    if missing:
        raise ArtifactContractError(f"missing compile commands for {missing}")
    return [found[path] for path in sorted(found, key=lambda item: item.encode())]


def _validate_sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ArtifactContractError(f"{name} must be lowercase SHA-256 hex")
    return value


def _validate_input_ledger(entries: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = sort_ledger(entries)
    expected = {"path", "role", "sha256", "size_bytes"}
    for entry in result:
        if set(entry) != expected:
            raise ArtifactContractError("input ledger entry has unexpected fields")
        if not isinstance(entry["role"], str) or not entry["role"]:
            raise ArtifactContractError("input ledger role must be nonempty")
        _validate_sha256(entry["sha256"], "input ledger sha256")
        _require_plain_int(entry["size_bytes"], "input ledger size_bytes")
    return result


def _validate_output_ledger(entries: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = sort_ledger(entries)
    expected = {"path", "role", "sha256", "size_bytes", "timed"}
    for entry in result:
        if set(entry) != expected:
            raise ArtifactContractError("output ledger entry has unexpected fields")
        if not isinstance(entry["role"], str) or not entry["role"]:
            raise ArtifactContractError("output ledger role must be nonempty")
        _validate_sha256(entry["sha256"], "output ledger sha256")
        _require_plain_int(entry["size_bytes"], "output ledger size_bytes")
        if not isinstance(entry["timed"], bool):
            raise ArtifactContractError("output ledger timed must be boolean")
    return result


def common_artifact_fields(
    *,
    status: str,
    implementation_commit: str,
    execution_commit: str,
    command: Sequence[str],
    thread_environment: Mapping[str, str],
    input_ledger: Iterable[Mapping[str, Any]] = (),
    output_ledger: Iterable[Mapping[str, Any]] = (),
    parent_preregistration_commit: str = PARENT_PREREGISTRATION_COMMIT,
    allow_zero_commit: bool = False,
) -> dict[str, Any]:
    """Assemble and validate the common schema-1 artifact fields."""

    if not isinstance(status, str) or not status:
        raise ArtifactContractError("artifact status must be nonempty")
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise ArtifactContractError("artifact command must be a nonempty argv array")
    if any(
        not isinstance(key, str)
        or not isinstance(value, str)
        for key, value in thread_environment.items()
    ):
        raise ArtifactContractError("thread environment must map strings to strings")
    return {
        "command": list(command),
        "execution_commit": validate_commit(
            execution_commit, allow_zero=allow_zero_commit
        ),
        "implementation_commit": validate_commit(
            implementation_commit, allow_zero=allow_zero_commit
        ),
        "input_ledger": _validate_input_ledger(input_ledger),
        "output_ledger": _validate_output_ledger(output_ledger),
        "parent_preregistration_commit": validate_commit(
            parent_preregistration_commit
        ),
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "thread_environment": dict(sorted(thread_environment.items())),
    }


def require_frozen_thread_environment(
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source = os.environ if environment is None else environment
    observed: dict[str, str] = {}
    for key, expected in FROZEN_THREAD_ENVIRONMENT.items():
        value = source.get(key)
        if value != expected:
            raise ArtifactContractError(
                f"thread environment mismatch for {key}: expected {expected}, got {value}"
            )
        observed[key] = value
    return dict(sorted(observed.items()))


def add_artifact_body(
    common_fields: Mapping[str, Any], body: Mapping[str, Any]
) -> dict[str, Any]:
    missing = _COMMON_KEYS - set(common_fields)
    if missing:
        raise ArtifactContractError(f"common artifact fields missing {sorted(missing)}")
    overlap = set(common_fields) & set(body)
    if overlap:
        raise ArtifactContractError(f"artifact body overwrites common fields {sorted(overlap)}")
    result = dict(common_fields)
    result.update(body)
    _validate_json_value(result)
    return result


def make_artifact_index_entry(
    file_path: str | os.PathLike[str],
    *,
    ledger_path: str,
    producer_execution_commit: str,
    schema_version: int = SCHEMA_VERSION,
) -> dict[str, Any]:
    identity = file_identity(file_path)
    return {
        "path": _validate_relative_ledger_path(ledger_path),
        "producer_execution_commit": validate_commit(producer_execution_commit),
        "schema_version": _require_plain_int(
            schema_version, "schema_version", minimum=1
        ),
        "sha256": identity.sha256,
        "size_bytes": identity.size_bytes,
    }


def make_artifact_index(
    common_fields: Mapping[str, Any],
    entries: Iterable[Mapping[str, Any]],
    *,
    index_ledger_path: str,
) -> dict[str, Any]:
    """Build an external checkpoint index and reject an accidental self-entry."""

    index_path = _validate_relative_ledger_path(index_ledger_path)
    ordered = sort_ledger(entries)
    if any(entry["path"] == index_path for entry in ordered):
        raise ArtifactContractError("artifact index must not contain its own hash")
    expected = {
        "path",
        "producer_execution_commit",
        "schema_version",
        "sha256",
        "size_bytes",
    }
    for entry in ordered:
        if set(entry) != expected:
            raise ArtifactContractError("artifact index entry has unexpected fields")
        validate_commit(entry["producer_execution_commit"])
        _require_plain_int(entry["schema_version"], "schema_version", minimum=1)
        _validate_sha256(entry["sha256"], "artifact index sha256")
        _require_plain_int(entry["size_bytes"], "artifact index size_bytes")
    return add_artifact_body(
        common_fields,
        {"artifact_kind": "artifact_index", "artifacts": ordered},
    )


def make_build_runtime_manifest(
    common_fields: Mapping[str, Any],
    *,
    compile_commands: Sequence[Mapping[str, Any]],
    runtime_numeric: Mapping[str, Any],
    native_binary_path: str | os.PathLike[str],
    native_binary_ledger_path: str,
    source_paths: Iterable[str | os.PathLike[str]],
    repo_root: str | os.PathLike[str],
    numpy_version: str,
    extra_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the build/runtime manifest around already validated inputs."""

    if not isinstance(numpy_version, str) or not numpy_version:
        raise ArtifactContractError("NumPy version must be a nonempty string")
    expected_sources = set(REQUIRED_TRANSLATION_UNITS)
    command_sources = {
        entry.get("source_path")
        for entry in compile_commands
        if isinstance(entry, Mapping)
    }
    if command_sources != expected_sources:
        raise ArtifactContractError(
            "build manifest requires validated commands for exactly seven TUs"
        )

    sources: list[dict[str, Any]] = []
    for source in source_paths:
        ledger_path = relative_posix_path(source, repo_root)
        identity = file_identity(source)
        sources.append(
            {
                "path": ledger_path,
                "sha256": identity.sha256,
                "size_bytes": identity.size_bytes,
            }
        )
    sources.sort(key=lambda entry: entry["path"].encode("utf-8"))
    source_names = {entry["path"] for entry in sources}
    if len(source_names) != len(sources):
        raise ArtifactContractError("build source manifest contains duplicate paths")
    if not expected_sources.issubset(source_names):
        raise ArtifactContractError("source hash set omits a required translation unit")

    binary_identity = file_identity(native_binary_path)
    body: dict[str, Any] = {
        "artifact_kind": "build_manifest",
        "compile_commands": [dict(entry) for entry in compile_commands],
        "native_binary": {
            "path": _validate_relative_ledger_path(native_binary_ledger_path),
            "sha256": binary_identity.sha256,
            "size_bytes": binary_identity.size_bytes,
        },
        "numpy_version": numpy_version,
        "runtime_numeric": dict(runtime_numeric),
        "sources": sources,
    }
    if extra_fields:
        overlap = set(body) & set(extra_fields)
        if overlap or set(extra_fields) & _COMMON_KEYS:
            raise ArtifactContractError(
                f"extra build fields collide with schema: {sorted(overlap)}"
            )
        body.update(extra_fields)
    return add_artifact_body(common_fields, body)


def pure_constant_self_test() -> dict[str, bool]:
    """Exercise constant-only invariants without filesystem, Git, NumPy, or RNG."""

    checks = {
        "canonical_json": canonical_json_bytes({"b": 2, "a": [True, None]})
        == b'{"a":[true,null],"b":2}',
        "canonical_sha256": sha256_bytes(b"abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        "compile_flags": validate_compile_argv(
            ("g++", *MANDATORY_COMPILE_FLAGS, "-Wall", "source.cpp")
        )[0]
        == "g++",
        "constants": (
            SCHEMA_VERSION == 1
            and STAGE == "A4-1S"
            and PROTOCOL_VERSION.endswith("schema1")
            and len(PARENT_PREREGISTRATION_COMMIT) == 40
        ),
        "ledger_order": [
            entry["path"]
            for entry in sort_ledger(
                (
                    {"path": "z", "role": "x"},
                    {"path": "a", "role": "x"},
                )
            )
        ]
        == ["a", "z"],
    }
    failures = sorted(name for name, passed in checks.items() if not passed)
    if failures:
        raise AssertionError(f"A4-1S pure constant self-test failed: {failures}")
    return checks


__all__ = [
    "ArtifactContractError",
    "FROZEN_THREAD_ENVIRONMENT",
    "FileIdentity",
    "MANDATORY_COMPILE_FLAGS",
    "PARENT_PREREGISTRATION_COMMIT",
    "PROTOCOL_VERSION",
    "REQUIRED_TRANSLATION_UNITS",
    "SCHEMA_VERSION",
    "STAGE",
    "ZERO_COMMIT",
    "add_artifact_body",
    "canonical_json_bytes",
    "common_artifact_fields",
    "file_identity",
    "git_blob_oid",
    "git_commit_is_ancestor",
    "git_head_commit",
    "git_last_modified_commit",
    "git_worktree_is_clean",
    "guard_synthetic_read_path",
    "load_and_validate_compile_commands",
    "make_artifact_index",
    "make_artifact_index_entry",
    "make_build_runtime_manifest",
    "make_detail_ledger_entry",
    "make_input_ledger_entry",
    "make_output_ledger_entry",
    "ordered_ledger_sha256",
    "pure_constant_self_test",
    "relative_posix_path",
    "require_clean_execution_commit",
    "require_frozen_thread_environment",
    "sha256_bytes",
    "sha256_file",
    "sort_ledger",
    "validate_commit",
    "validate_compile_argv",
    "write_canonical_json",
    "write_canonical_json_lines",
]
