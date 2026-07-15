#!/usr/bin/env python3
"""Long-lived A4 V2 supervisor.

The source implements the frozen prelaunch observation, integer process-family
meter, 396-unit producer supervision, one-restart rule, downstream phase
launches, and finite final hash DAG.  It has no import-time entry point.  The
only supported run surface is ``srun ARTIFACT_ROOT`` through the bootstrap.

Building or executing this source is outside A4-V2-I authority.
"""

from __future__ import annotations

import argparse
import ctypes
import datetime as datetime_module
import errno
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import signal
import shutil
import ssl
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

import a4_v2_evidence as evidence
import a4_v2_producer as producer


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPOSITORY_ROOT / "docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json"
SCHEMA_PATH = REPOSITORY_ROOT / "docs/saq_a4_v2_artifact_schema_2026_07_14.json"
IMPLEMENTATION_MANIFEST_PATH = REPOSITORY_ROOT / "docs/saq_a4_v2_implementation_manifest_2026_07_14.json"
PAR_SEAL_PATH = REPOSITORY_ROOT / "docs/saq_a4_v2_par_artifacts_2026_07_14/par_seal.json"
PAR_REVIEW_BINDING_PATH = (
    REPOSITORY_ROOT
    / "docs/saq_a4_v2_execution_authority_2026_07_14/par_review_binding.json"
)
PAR_REVIEW_MEMO_PATH = (
    REPOSITORY_ROOT
    / "docs/saq_a4_v2_par_artifacts_independent_review_2026_07_14.md"
)
PRODUCER_NATIVE = REPOSITORY_ROOT / "build/a4_v2/a4_v2_native"
VERIFIER_NATIVE = REPOSITORY_ROOT / "build/a4_v2_verifier/a4_v2_native"
VERIFIER_WRAPPER = REPOSITORY_ROOT / "script/a4_v2_verifier.py"
ARCHIVE_WRAPPER = REPOSITORY_ROOT / "script/a4_v2_archive.py"

PYTHON_SOURCE_FILES = (
    "script/a4_v2_archive.py",
    "script/a4_v2_evidence.py",
    "script/a4_v2_parity.py",
    "script/a4_v2_producer.py",
    "script/a4_v2_producer_wire.py",
    "script/a4_v2_runner.py",
    "script/a4_v2_verifier.py",
    "script/run_arbitrary_cardinality_a4_v2.py",
)
PRODUCER_NATIVE_SOURCE_FILES = (
    "research/a4_v2/CMakeLists.txt",
    "research/a4_v2/a4_v2_native.cpp",
    "research/a4_v2/block_vq.cpp",
    "research/a4_v2/block_vq.hpp",
    "research/a4_v2/exact_quantizer.cpp",
    "research/a4_v2/exact_quantizer.hpp",
    "research/a4_v2/native_cli.cpp",
    "research/a4_v2/native_cli.hpp",
    "research/a4_v2/numeric_runtime.cpp",
    "research/a4_v2/numeric_runtime.hpp",
    "research/a4_v2/representation.cpp",
    "research/a4_v2/representation.hpp",
)
VERIFIER_NATIVE_SOURCE_FILES = (
    "research/a4_v2_verifier/CMakeLists.txt",
    "research/a4_v2_verifier/a4_v2_native.cpp",
    "research/a4_v2_verifier/exact_reference.cpp",
    "research/a4_v2_verifier/exact_reference.hpp",
    "research/a4_v2_verifier/input_panel.cpp",
    "research/a4_v2_verifier/input_panel.hpp",
    "research/a4_v2_verifier/json_value.cpp",
    "research/a4_v2_verifier/json_value.hpp",
    "research/a4_v2_verifier/parity_cli.cpp",
    "research/a4_v2_verifier/parity_cli.hpp",
    "research/a4_v2_verifier/replay.cpp",
    "research/a4_v2_verifier/replay.hpp",
    "research/a4_v2_verifier/representation_parity.cpp",
    "research/a4_v2_verifier/sha256.cpp",
    "research/a4_v2_verifier/sha256.hpp",
)
PRODUCER_CMAKE_SOURCE_FILES = tuple(
    path
    for path in PRODUCER_NATIVE_SOURCE_FILES
    if path.endswith(".cpp")
)
VERIFIER_CMAKE_SOURCE_FILES = tuple(
    path
    for path in VERIFIER_NATIVE_SOURCE_FILES
    if path.endswith(".cpp")
)
SOURCE_FILES = tuple(
    sorted(
        (*PYTHON_SOURCE_FILES, *PRODUCER_NATIVE_SOURCE_FILES, *VERIFIER_NATIVE_SOURCE_FILES),
        key=lambda value: value.encode("utf-8"),
    )
)
SOURCE_FILE_METADATA = {
    path: {
        "family": (
            "producer_native"
            if path.startswith("research/a4_v2/")
            else "independent_verifier_native"
            if path.startswith("research/a4_v2_verifier/")
            else "python_runtime"
        ),
        "role": (
            "build_configuration"
            if path.endswith("/CMakeLists.txt")
            else "translation_unit"
            if path.endswith(".cpp")
            else "interface_header"
            if path.endswith(".hpp")
            else "entrypoint"
            if path == "script/run_arbitrary_cardinality_a4_v2.py"
            else "runtime_module"
        ),
    }
    for path in SOURCE_FILES
}
CMAKE_BINARY = "/usr/local/software/cmake-4.0.3/bin/cmake"
NINJA_BINARY = "/usr/local/software/ninja-1.9.0/bin/ninja"
CXX_BINARY = "/usr/bin/c++"
BUILD_COMMANDS = (
    [
        CMAKE_BINARY,
        "-S",
        "research/a4_v2",
        "-B",
        "build/a4_v2",
        "-G",
        "Ninja",
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_MAKE_PROGRAM={NINJA_BINARY}",
        f"-DCMAKE_CXX_COMPILER={CXX_BINARY}",
    ],
    [
        CMAKE_BINARY,
        "--build",
        "build/a4_v2",
        "--target",
        "a4_v2_native",
        "-j",
        "1",
    ],
    [
        CMAKE_BINARY,
        "-S",
        "research/a4_v2_verifier",
        "-B",
        "build/a4_v2_verifier",
        "-G",
        "Ninja",
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_MAKE_PROGRAM={NINJA_BINARY}",
        f"-DCMAKE_CXX_COMPILER={CXX_BINARY}",
    ],
    [
        CMAKE_BINARY,
        "--build",
        "build/a4_v2_verifier",
        "--target",
        "a4_v2_native",
        "-j",
        "1",
    ],
)
PARITY_INVENTORY = {
    "allocation_decision_count": 2_433_600,
    "block_case_count": 64,
    "block_microfixture_count": 5,
    "block_rng": {
        "algorithm": "PCG64",
        "seed": 20260713,
        "stream_scope": "block_64_only",
    },
    "representation_fixture_families": [
        "allocation",
        "rounding",
        "mixed_radix",
        "packing",
        "matched_lookup",
        "global_lookup",
    ],
    "scalar_bit_pattern_case_count": 8,
    "scalar_exhaustive_case_count": 780,
    "scalar_pcg64_case_count": 256,
    "scalar_rng": {
        "algorithm": "PCG64",
        "seed": 20260713,
        "stream_scope": "scalar_256_only",
    },
}
PRODUCER_NATIVE_CHILD_ARGV_TEMPLATES = (
    ["/proc/self/fd/197", "manifest"],
    ["/proc/self/fd/197", "native-smoke", "{output}"],
    ["/proc/self/fd/197", "par-block", "{input}", "{output}"],
    ["/proc/self/fd/197", "par-scalar", "{input}", "{output}"],
    ["/proc/self/fd/197", "representation-suite"],
    ["/proc/self/fd/197", "allocation-item", "{input}", "{output}"],
    ["/proc/self/fd/197", "block-suite", "{input}", "{output}"],
    ["/proc/self/fd/197", "encoding-suite", "{input}", "{output}"],
    ["/proc/self/fd/197", "scalar-suite", "{input}", "{output}"],
)
VERIFIER_NATIVE_CHILD_ARGV = ["/proc/self/fd/197", "verify-canonical-request"]
PAR_BUILD_ARTIFACT_FILES = tuple(
    [
        name
        for index in range(len(BUILD_COMMANDS))
        for name in (
            f"build_command_{index:02d}.stderr",
            f"build_command_{index:02d}.stdout",
        )
    ]
    + [
        "build_manifest.json",
        "build_producer_manifest.stderr",
        "build_producer_native_manifest.json",
        "build_verifier_manifest.stderr",
        "build_verifier_native_manifest.json",
        "producer_compile_commands.json",
        "verifier_compile_commands.json",
    ]
)
PAR_PARITY_ARTIFACT_FILES = (
    "block_independent.stderr",
    "block_independent.stdout",
    "block_independent.tsv",
    "block_input.bin",
    "block_optimized_run1.stderr",
    "block_optimized_run1.stdout",
    "block_optimized_run1.tsv",
    "block_optimized_run2.stderr",
    "block_optimized_run2.stdout",
    "block_optimized_run2.tsv",
    "parity_summary.json",
    "producer_native_smoke.stderr",
    "producer_native_smoke.stdout",
    "producer_native_smoke.tsv",
    "representation_independent.json",
    "representation_independent.stderr",
    "representation_independent.stdout",
    "representation_optimized.json",
    "representation_optimized.stderr",
    "scalar_independent.stderr",
    "scalar_independent.stdout",
    "scalar_independent.tsv",
    "scalar_input.bin",
    "scalar_optimized.stderr",
    "scalar_optimized.stdout",
    "scalar_optimized.tsv",
)
PAR_INDEXED_ARTIFACT_FILES = tuple(
    sorted(
        (*PAR_BUILD_ARTIFACT_FILES, *PAR_PARITY_ARTIFACT_FILES),
        key=lambda value: value.encode("utf-8"),
    )
)
PAR_DIRECTORY_FILES = frozenset(
    (*PAR_INDEXED_ARTIFACT_FILES, "artifact_index.json", "par_seal.json")
)

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
STATUS_ORDER = (
    "ARTIFACT_INVALID",
    "IMPLEMENTATION_INVALID",
    "CONTROL_INVALID",
    "RESOURCE_INCOMPLETE_NO_DECISION",
    "EVIDENCE_INCOMPLETE_NO_DECISION",
    "VERIFICATION_INVALID",
    "NO_GO_REPRESENTATION",
    "NO_GO_SYNTHETIC_INSTRUMENT_COST",
    "PASS_SYNTHETIC_INSTRUMENT_GATE_ONLY",
)
C_FAILURE_STATUSES = frozenset(
    {
        "ARTIFACT_INVALID",
        "IMPLEMENTATION_INVALID",
        "CONTROL_INVALID",
        "RESOURCE_INCOMPLETE_NO_DECISION",
    }
)
CHILD_EVIDENCE_FAILURE_EXIT_CODE = 2
CHILD_RESOURCE_FAILURE_EXIT_CODE = 3
CHILD_ARTIFACT_FAILURE_EXIT_CODE = 4
CHILD_IMPLEMENTATION_FAILURE_EXIT_CODE = 5
CHILD_EXTERNAL_INTERRUPTION_EXIT_CODE = 6
ATTRIBUTION_NAMES = (
    "C_setup",
    "C_shared_fit",
    "C_arm_dyadic",
    "C_arm_arbitrary",
    "C_arm_block",
    "C_arm_global",
    "C_common_manifest",
    "C_interrupted_tail",
)
CONFLICT_MARKERS = (
    "a4_1s_native",
    "a4_1s_runner.py",
    "a4_v2_archive.py",
    "a4_v2_native",
    "a4_v2_runner.py",
    "a4_v2_verifier.py",
    "evaluate_arbitrary_cardinality.py",
    "run_arbitrary_cardinality_a4_1s.py",
    "run_arbitrary_cardinality_a4_v2.py",
    "run_saq_cost_projection.py",
    "saq_cost_projection",
    "saq_cost_projection.py",
)
PRIMARY_CAP = 34_560_000_000
PER_PHASE_CPU_LIMIT = 86_400_000_000
PER_PHASE_WALL_LIMIT = 172_800_000_000_000
PER_ATTEMPT_CPU_LIMIT = 86_400_000_000
PER_ATTEMPT_WALL_LIMIT = 172_800_000_000_000
STUDY_CPU_LIMIT = 518_400_000_000
RSS_LIMIT = 25_769_803_776
TEMPORARY_LIMIT = 17_179_869_184
BUNDLE_LIMIT = 268_435_456
EVIDENCE_LIMIT = 4_294_967_296
MINIMUM_AVAILABLE_MEMORY = 25_769_803_776
MINIMUM_FREE_OUTPUT = 17_179_869_184
CLAIM_CEILING = (
    "A pass establishes one frozen-machine synthetic comparative-instrument admission "
    "observation and independent reproduction only; it establishes no candidate-only "
    "affordability, natural-data prevalence, SAQ integration, index-build cost, query "
    "quality, recall, QPS, frontier movement, or novelty."
)

_FIXED_CHILD_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
}
_FIXED_ENVIRONMENT = {
    "CPU": "Intel(R) Core(TM) i9-10920X CPU @ 3.50GHz",
    "GMP": "6.2.0",
    "MPFR": "4.1.0-p9",
    "MXCSR": "0x00001f80; FTZ=false; DAZ=false",
    "NumPy": "1.23.5",
    "OpenSSL": "3.5.5 27 Jan 2026",
    "Python": "CPython 3.9.25",
    "allowed_affinity": "0-23",
    "compiler": "GCC 11.5.0 20240719 (Red Hat 11.5.0-14)",
    "compiler_flags": [
        "-O3",
        "-fno-fast-math",
        "-ffp-contract=off",
        "-frounding-math",
        "-mfpmath=sse",
    ],
    "governor": "performance",
    "kernel": "5.14.0-687.24.1.el9_8.x86_64",
    "physical_memory_bytes": 33_047_748_608,
    "rounding": "FE_TONEAREST",
    "SMT": "active",
    "thread_environment": dict(_FIXED_CHILD_ENVIRONMENT),
    "threads": 1,
    "turbo": "enabled; intel_pstate/no_turbo=0",
}

_DECIMAL = re.compile(rb"^(?:0|[1-9][0-9]*)$")
_FIXED_DECIMAL = re.compile(rb"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


class SupervisorFailure(RuntimeError):
    def __init__(self, status: str, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class PreconditionFailure(RuntimeError):
    pass


class ExternalInterruption(RuntimeError):
    pass


def _fail(status: str, detail: str) -> NoReturn:
    raise SupervisorFailure(status, detail)


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


_LIBC = ctypes.CDLL(None, use_errno=True)
_GETRUSAGE = _LIBC.getrusage
_GETRUSAGE.argtypes = [ctypes.c_int, ctypes.POINTER(_Rusage)]
_GETRUSAGE.restype = ctypes.c_int
_WAIT4 = _LIBC.wait4
_WAIT4.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.POINTER(_Rusage)]
_WAIT4.restype = ctypes.c_int


def _timeval_microseconds(value: _Timeval) -> int:
    if value.tv_sec < 0 or not 0 <= value.tv_usec < 1_000_000:
        _fail("IMPLEMENTATION_INVALID", "noncanonical getrusage timeval")
    return int(value.tv_sec) * 1_000_000 + int(value.tv_usec)


def _one_rusage(who: int) -> _Rusage:
    value = _Rusage()
    if _GETRUSAGE(who, ctypes.byref(value)) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))
    return value


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_microseconds: int
    wall_nanoseconds: int
    peak_rss_bytes: int


@dataclass(frozen=True)
class PhaseBoundary:
    snapshot: ResourceSnapshot
    utc: str


def _snapshot() -> ResourceSnapshot:
    own = _one_rusage(0)
    children = _one_rusage(-1)
    cpu = sum(
        _timeval_microseconds(value)
        for value in (own.ru_utime, own.ru_stime, children.ru_utime, children.ru_stime)
    )
    rss = max(int(own.ru_maxrss), int(children.ru_maxrss), 0) * 1024
    return ResourceSnapshot(cpu, time.monotonic_ns(), rss)


@dataclass(frozen=True)
class WaitResult:
    exit_code: int
    cpu_microseconds: int
    peak_rss_bytes: int


def _wait4_integer(pid: int) -> WaitResult:
    status = ctypes.c_int()
    usage = _Rusage()
    while True:
        result = _WAIT4(pid, ctypes.byref(status), 0, ctypes.byref(usage))
        if result == pid:
            break
        number = ctypes.get_errno()
        if number == 4:  # EINTR
            continue
        raise OSError(number, os.strerror(number))
    return WaitResult(
        os.waitstatus_to_exitcode(status.value),
        _timeval_microseconds(usage.ru_utime) + _timeval_microseconds(usage.ru_stime),
        max(int(usage.ru_maxrss), 0) * 1024,
    )


def _utc_now() -> str:
    return datetime_module.datetime.now(datetime_module.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def _utc_from_realtime_ns(value: int) -> str:
    seconds, nanoseconds = divmod(value, 1_000_000_000)
    instant = datetime_module.datetime.fromtimestamp(seconds, datetime_module.timezone.utc)
    return instant.strftime("%Y-%m-%dT%H:%M:%S.") + f"{nanoseconds // 1000:06d}Z"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_identity(path: Path, relative: str, phase: str, role: str, schema: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        _fail("ARTIFACT_INVALID", f"cannot read identity file {path}: {error}")
    return {
        "path": relative,
        "producing_phase": phase,
        "role": role,
        "schema": schema,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _document_identity(path: Path) -> dict[str, Any]:
    identity = _file_identity(
        path,
        path.relative_to(REPOSITORY_ROOT).as_posix(),
        "B_build",
        "normative_document",
        "document",
    )
    return {key: identity[key] for key in ("path", "sha256", "size_bytes")}


def _child_environment() -> dict[str, str]:
    result = dict(os.environ)
    result.update(_FIXED_CHILD_ENVIRONMENT)
    return result


def _parse_json_document(payload: bytes, description: str, canonical: bool) -> Mapping[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                _fail("ARTIFACT_INVALID", f"duplicate key in {description}: {key}")
            result[key] = value
        return result

    def reject_float(token: str) -> NoReturn:
        _fail("ARTIFACT_INVALID", f"floating JSON token in {description}: {token}")

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as error:
        _fail("ARTIFACT_INVALID", f"invalid {description}: {error}")
    if not isinstance(value, dict):
        _fail("ARTIFACT_INVALID", f"{description} is not an object")
    if canonical and evidence.canonical_document(value) != payload:
        _fail("ARTIFACT_INVALID", f"{description} is not canonical JSON")
    return value


def _run_capture(arguments: Sequence[str]) -> bytes:
    completed = subprocess.run(
        list(arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=_child_environment(),
        cwd=REPOSITORY_ROOT,
    )
    if completed.returncode != 0:
        _fail(
            "IMPLEMENTATION_INVALID",
            f"preflight command failed ({arguments[0]}): {completed.stderr[:4096]!r}",
        )
    return completed.stdout


def _git_source_identity() -> tuple[str, str, str, bytes]:
    commit = _run_capture(("git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD")).decode("ascii").strip()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        _fail("ARTIFACT_INVALID", "execution commit is not a Git OID")
    if _run_capture(
        ("git", "-C", str(REPOSITORY_ROOT), "status", "--porcelain", "--untracked-files=all")
    ):
        _fail("ARTIFACT_INVALID", "execution worktree is dirty")
    repository_url = _run_capture(
        ("git", "-C", str(REPOSITORY_ROOT), "remote", "get-url", "origin")
    ).decode("utf-8").strip()
    manifest_payload = IMPLEMENTATION_MANIFEST_PATH.read_bytes()
    manifest = _parse_json_document(manifest_payload, "implementation manifest", True)
    required_manifest_keys = {
        "artifact_kind",
        "artifact_schema_identity",
        "authorization_identity",
        "build_status",
        "contract_identity",
        "implementation_binding_identity",
        "parent_preregistration_identity",
        "par_contract",
        "parent_protocol_commit",
        "producer_cmake_source_files",
        "protocol_identity",
        "python_source_files",
        "schema_version",
        "source_files",
        "source_provenance_identity",
        "source_tree_sha256",
        "verifier_cmake_source_files",
    }
    if set(manifest) != required_manifest_keys or (
        manifest.get("artifact_kind") != "a4_v2_implementation_manifest"
        or manifest.get("schema_version") != 1
        or manifest.get("parent_protocol_commit")
        != "f86a51d6923409d735dda0ee40f88fd2e0ad2e43"
        or manifest.get("build_status") != "NOT_AUTHORIZED_NOT_RUN"
    ):
        _fail("ARTIFACT_INVALID", "implementation manifest top-level contract mismatch")
    expected_documents = {
        "protocol_identity": "docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json",
        "parent_preregistration_identity": "docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md",
        "contract_identity": "docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json",
        "artifact_schema_identity": "docs/saq_a4_v2_artifact_schema_2026_07_14.json",
        "authorization_identity": "docs/saq_a4_v2_executable_identity_source_repair_authorization_2026_07_15.md",
        "implementation_binding_identity": "docs/saq_a4_v2_implementation_binding_2026_07_14.md",
        "source_provenance_identity": "docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md",
    }
    for key, relative in expected_documents.items():
        value = manifest.get(key)
        target = REPOSITORY_ROOT / relative
        target_payload = target.read_bytes()
        if value != {
            "path": relative,
            "sha256": _sha256(target_payload),
            "size_bytes": len(target_payload),
        }:
            _fail("ARTIFACT_INVALID", f"implementation manifest {key} mismatch")
    par_contract = manifest.get("par_contract")
    if not isinstance(par_contract, dict) or set(par_contract) != {
        "build_commands",
        "build_manifest_path",
        "par_command",
        "par_review_binding_path",
        "par_review_memo_path",
        "par_seal_path",
        "parity_artifact_index_path",
        "parity_inventory",
        "parity_summary_path",
        "producer_binary_identity_path",
        "producer_native_child_argv_templates",
        "verifier_binary_identity_path",
        "verifier_native_child_argv",
    }:
        _fail("ARTIFACT_INVALID", "implementation manifest PAR contract shape mismatch")
    expected_par_contract = {
        "build_commands": [list(command) for command in BUILD_COMMANDS],
        "build_manifest_path": (
            "docs/saq_a4_v2_par_artifacts_2026_07_14/build_manifest.json"
        ),
        "par_command": [
            "python",
            "script/run_arbitrary_cardinality_a4_v2.py",
            "par",
            "docs/saq_a4_v2_par_artifacts_2026_07_14",
        ],
        "par_review_binding_path": (
            "docs/saq_a4_v2_execution_authority_2026_07_14/par_review_binding.json"
        ),
        "par_review_memo_path": (
            "docs/saq_a4_v2_par_artifacts_independent_review_2026_07_14.md"
        ),
        "par_seal_path": "docs/saq_a4_v2_par_artifacts_2026_07_14/par_seal.json",
        "parity_artifact_index_path": (
            "docs/saq_a4_v2_par_artifacts_2026_07_14/artifact_index.json"
        ),
        "parity_inventory": PARITY_INVENTORY,
        "parity_summary_path": (
            "docs/saq_a4_v2_par_artifacts_2026_07_14/parity_summary.json"
        ),
        "producer_binary_identity_path": "build/a4_v2/a4_v2_native",
        "producer_native_child_argv_templates": [
            list(command) for command in PRODUCER_NATIVE_CHILD_ARGV_TEMPLATES
        ],
        "verifier_binary_identity_path": "build/a4_v2_verifier/a4_v2_native",
        "verifier_native_child_argv": list(VERIFIER_NATIVE_CHILD_ARGV),
    }
    if par_contract != expected_par_contract:
        _fail("ARTIFACT_INVALID", "implementation manifest PAR contract value mismatch")
    raw_files = manifest.get("source_files")
    if not isinstance(raw_files, list) or not raw_files:
        _fail("ARTIFACT_INVALID", "implementation manifest has no explicit source_files")
    source_preimage = []
    prior = b""
    for item in raw_files:
        if (
            not isinstance(item, dict)
            or set(item) != {"family", "path", "role", "sha256", "size_bytes"}
            or not isinstance(item.get("path"), str)
            or not isinstance(item.get("family"), str)
            or not isinstance(item.get("role"), str)
        ):
            _fail("ARTIFACT_INVALID", "malformed implementation source entry")
        relative = item["path"]
        encoded = relative.encode("utf-8")
        parts = relative.split("/")
        if relative.startswith("/") or any(part in {"", ".", ".."} for part in parts):
            _fail("ARTIFACT_INVALID", "unnormalized implementation source path")
        if prior and encoded <= prior:
            _fail("ARTIFACT_INVALID", "implementation source paths are not strictly ordered")
        prior = encoded
        source_path = REPOSITORY_ROOT / relative
        payload = source_path.read_bytes()
        observed = {"path": relative, "sha256": _sha256(payload), "size_bytes": len(payload)}
        if item.get("sha256") != observed["sha256"] or item.get("size_bytes") != observed[
            "size_bytes"
        ]:
            _fail("ARTIFACT_INVALID", f"implementation manifest identity mismatch: {relative}")
        if SOURCE_FILE_METADATA.get(relative) != {
            "family": item["family"],
            "role": item["role"],
        }:
            _fail(
                "ARTIFACT_INVALID",
                f"implementation manifest source family/role mismatch: {relative}",
            )
        source_preimage.append(observed)
    source_tree = _sha256(evidence.canonical_body(source_preimage))
    if manifest.get("source_tree_sha256") != source_tree:
        _fail("ARTIFACT_INVALID", "implementation manifest source_tree_sha256 mismatch")
    source_paths = {item["path"] for item in raw_files}
    if source_paths != set(SOURCE_FILES) or [item["path"] for item in raw_files] != list(
        SOURCE_FILES
    ):
        _fail("ARTIFACT_INVALID", "implementation manifest source closure is not exact")
    observed_producer = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "research/a4_v2").iterdir()
        if path.is_file()
    }
    observed_verifier = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "research/a4_v2_verifier").iterdir()
        if path.is_file()
    }
    observed_python = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "script").iterdir()
        if path.is_file()
        and ("a4_v2" in path.name or path.name == "run_arbitrary_cardinality_a4_v2.py")
    }
    if (
        observed_producer != set(PRODUCER_NATIVE_SOURCE_FILES)
        or observed_verifier != set(VERIFIER_NATIVE_SOURCE_FILES)
        or observed_python != set(PYTHON_SOURCE_FILES)
    ):
        _fail("ARTIFACT_INVALID", "on-disk A4-V2 source inventory differs from closure")
    expected_closures = {
        "producer_cmake_source_files": list(PRODUCER_CMAKE_SOURCE_FILES),
        "verifier_cmake_source_files": list(VERIFIER_CMAKE_SOURCE_FILES),
        "python_source_files": list(PYTHON_SOURCE_FILES),
    }
    for key in (
        "producer_cmake_source_files",
        "verifier_cmake_source_files",
        "python_source_files",
    ):
        values = manifest.get(key)
        if (
            not isinstance(values, list)
            or values != expected_closures[key]
        ):
            _fail("ARTIFACT_INVALID", f"implementation manifest {key} closure mismatch")
    return commit, repository_url, source_tree, manifest_payload


def _parse_status(payload: bytes) -> tuple[int, int]:
    pid_values: list[bytes] = []
    uid_values: list[list[bytes]] = []
    for line in payload.splitlines():
        if line.startswith(b"Pid:"):
            pid_values.append(line[4:].strip())
        elif line.startswith(b"Uid:"):
            uid_values.append(line[4:].split())
    if len(pid_values) != 1 or len(uid_values) != 1 or len(uid_values[0]) != 4:
        raise ValueError("status lacks unique Pid/Uid")
    if _DECIMAL.fullmatch(pid_values[0]) is None or any(
        _DECIMAL.fullmatch(value) is None for value in uid_values[0]
    ):
        raise ValueError("status Pid/Uid is noncanonical")
    return int(pid_values[0]), int(uid_values[0][1])


@dataclass(frozen=True)
class StatRecord:
    pid: int
    comm: bytes
    state: str
    user_ticks: int
    system_ticks: int
    start_ticks: int


def _parse_stat(payload: bytes) -> StatRecord:
    opening = payload.find(b"(")
    closing = payload.rfind(b") ")
    if opening <= 0 or closing <= opening or payload.endswith(b"\n\n"):
        raise ValueError("ambiguous proc stat framing")
    pid_token = payload[:opening].strip()
    if _DECIMAL.fullmatch(pid_token) is None:
        raise ValueError("proc stat PID is noncanonical")
    tail = payload[closing + 2 :].strip().split()
    if len(tail) < 20 or len(tail[0]) != 1:
        raise ValueError("proc stat is truncated")
    numeric = (tail[11], tail[12], tail[19])
    if any(_DECIMAL.fullmatch(item) is None for item in numeric):
        raise ValueError("proc stat counter is noncanonical")
    return StatRecord(
        int(pid_token),
        payload[opening + 1 : closing],
        tail[0].decode("ascii"),
        int(tail[11]),
        int(tail[12]),
        int(tail[19]),
    )


def _read_proc_file(pid: int, name: bytes) -> bytes:
    with open(b"/proc/" + str(pid).encode("ascii") + b"/" + name, "rb") as source:
        return source.read()


def _read_proc_executable(pid: int) -> bytes:
    value = os.readlink(b"/proc/" + str(pid).encode("ascii") + b"/exe")
    if not isinstance(value, bytes):
        raise ValueError("byte readlink returned text")
    return value


def _marker_matches(cmdline: bytes, executable: bytes) -> list[str]:
    basenames = {
        item.rsplit(b"/", 1)[-1]
        for item in cmdline.split(b"\0")
        if item
    }
    basenames.add(executable.rsplit(b"/", 1)[-1])
    return [marker for marker in CONFLICT_MARKERS if marker.encode("utf-8") in basenames]


def _validate_cmdline(payload: bytes, pid: int) -> None:
    if not payload:
        return
    if not payload.endswith(b"\0") or payload.endswith(b"\0\0"):
        raise PreconditionFailure(
            f"same-user PID {pid} nonempty cmdline lacks exactly one terminal NUL"
        )


def _process_inventory() -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    effective_uid = os.geteuid()
    captured = sorted(
        int(name)
        for name in os.listdir(b"/proc")
        if name and all(48 <= byte <= 57 for byte in name)
    )
    if not captured:
        raise PreconditionFailure("numeric /proc snapshot is empty")
    filters: list[dict[str, Any]] = []
    same_user: list[dict[str, Any]] = []
    self_start: int | None = None
    for pid in captured:
        try:
            initial_status = _read_proc_file(pid, b"status")
            status_pid, observed_uid = _parse_status(initial_status)
        except (OSError, ValueError) as error:
            raise PreconditionFailure(f"incomplete initial status for PID {pid}: {error}") from error
        if status_pid != pid:
            raise PreconditionFailure(f"initial status PID mismatch for {pid}")
        filter_index = len(filters)
        filters.append(
            {
                "effective_uid": observed_uid,
                "initial_proc_status_hex": initial_status.hex(),
                "initial_proc_status_sha256": _sha256(initial_status),
                "pid": pid,
                "same_as_preflight_effective_uid": observed_uid == effective_uid,
            }
        )
        if observed_uid != effective_uid:
            continue
        try:
            initial_stat_bytes = _read_proc_file(pid, b"stat")
            initial_cmdline = _read_proc_file(pid, b"cmdline")
            initial_executable = _read_proc_executable(pid)
            final_cmdline = _read_proc_file(pid, b"cmdline")
            final_executable = _read_proc_executable(pid)
            final_stat_bytes = _read_proc_file(pid, b"stat")
            final_status = _read_proc_file(pid, b"status")
            initial_stat = _parse_stat(initial_stat_bytes)
            final_stat = _parse_stat(final_stat_bytes)
            final_status_pid, final_uid = _parse_status(final_status)
        except (OSError, ValueError) as error:
            raise PreconditionFailure(f"unstable same-UID PID {pid}: {error}") from error
        if (
            initial_stat.pid != pid
            or final_stat.pid != pid
            or final_status_pid != pid
            or final_uid != effective_uid
            or initial_stat.start_ticks != final_stat.start_ticks
            or initial_cmdline != final_cmdline
            or initial_executable != final_executable
        ):
            raise PreconditionFailure(f"identity changed during PID {pid} inventory")
        _validate_cmdline(initial_cmdline, pid)
        _validate_cmdline(final_cmdline, pid)
        is_self = pid == os.getpid()
        markers = _marker_matches(final_cmdline, final_executable)
        if markers and not is_self:
            raise PreconditionFailure(
                f"same-user conflicting process PID {pid}: {','.join(markers)}"
            )
        if is_self:
            if not markers:
                raise PreconditionFailure("preflight self exposes no frozen conflict marker")
            self_start = initial_stat.start_ticks
        same_user.append(
            {
                "classification": "ALLOW_PREFLIGHT_SELF" if is_self else "ALLOW_NO_MARKER",
                "comm_hex": final_stat.comm.hex(),
                "conflicting_a4_or_saq_cost": False,
                "final_cmdline_hex": final_cmdline.hex(),
                "final_cmdline_sha256": _sha256(final_cmdline),
                "final_executable_target_hex": final_executable.hex(),
                "final_proc_stat_hex": final_stat_bytes.hex(),
                "final_proc_stat_sha256": _sha256(final_stat_bytes),
                "final_proc_status_hex": final_status.hex(),
                "final_proc_status_sha256": _sha256(final_status),
                "initial_cmdline_hex": initial_cmdline.hex(),
                "initial_cmdline_sha256": _sha256(initial_cmdline),
                "initial_executable_target_hex": initial_executable.hex(),
                "initial_proc_stat_hex": initial_stat_bytes.hex(),
                "initial_proc_stat_sha256": _sha256(initial_stat_bytes),
                "is_preflight_self": is_self,
                "matched_conflict_markers": markers,
                "pid": pid,
                "pid_filter_record_index": filter_index,
                "start_time_clock_ticks": final_stat.start_ticks,
                "state": final_stat.state,
                "system_cpu_clock_ticks": final_stat.system_ticks,
                "total_cpu_clock_ticks": final_stat.user_ticks + final_stat.system_ticks,
                "user_cpu_clock_ticks": final_stat.user_ticks,
            }
        )
    same_user.sort(key=lambda item: (item["pid"], item["start_time_clock_ticks"]))
    if self_start is None or sum(bool(item["is_preflight_self"]) for item in same_user) != 1:
        raise PreconditionFailure("preflight self is absent or duplicated")
    return filters, same_user, len(captured), self_start


def _memory_observation() -> tuple[bytes, int]:
    payload = Path("/proc/meminfo").read_bytes()
    matches = []
    for line in payload.splitlines():
        if line.startswith(b"MemAvailable:"):
            fields = line.split()
            if len(fields) == 3 and fields[2] == b"kB" and _DECIMAL.fullmatch(fields[1]):
                matches.append(int(fields[1]))
    if len(matches) != 1:
        raise PreconditionFailure("MemAvailable is missing or ambiguous")
    return payload, matches[0]


def _load_observation() -> tuple[bytes, dict[str, str]]:
    payload = Path("/proc/loadavg").read_bytes()
    fields = payload.split()
    if len(fields) < 3 or any(_FIXED_DECIMAL.fullmatch(item) is None for item in fields[:3]):
        raise PreconditionFailure("loadavg first three tokens are noncanonical")
    return payload, {
        "one_minute": fields[0].decode("ascii"),
        "five_minute": fields[1].decode("ascii"),
        "fifteen_minute": fields[2].decode("ascii"),
    }


def _affinity_text(values: set[int]) -> str:
    if not values:
        return ""
    ordered = sorted(values)
    ranges: list[str] = []
    begin = previous = ordered[0]
    for value in ordered[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append(str(begin) if begin == previous else f"{begin}-{previous}")
        begin = previous = value
    ranges.append(str(begin) if begin == previous else f"{begin}-{previous}")
    return ",".join(ranges)


def _cpu_model() -> str:
    values = []
    for line in Path("/proc/cpuinfo").read_bytes().splitlines():
        if line.startswith(b"model name") and b":" in line:
            values.append(line.split(b":", 1)[1].strip().decode("ascii"))
    if not values or len(set(values)) != 1:
        raise PreconditionFailure("CPU model inventory is missing or heterogeneous")
    return values[0]


def _native_manifest() -> Mapping[str, Any]:
    descriptor = os.open(
        PRODUCER_NATIVE, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    )
    _reserve_fixed_descriptor(descriptor, 197)
    try:
        completed = subprocess.run(
            ["/proc/self/fd/197", "manifest"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_child_environment(),
            pass_fds=(197,),
            close_fds=True,
            check=False,
        )
    finally:
        os.close(197)
    if completed.returncode != 0:
        raise PreconditionFailure(
            f"producer native manifest failed: {completed.stderr[:4096]!r}"
        )
    payload = completed.stdout
    return _parse_json_document(payload, "producer native manifest", True)


def _environment_identity(native: Mapping[str, Any]) -> dict[str, Any]:
    if native.get("artifact_kind") != "a4_v2_native_build_manifest" or native.get(
        "schema_version"
    ) != 1:
        raise PreconditionFailure("native manifest identity mismatch")
    flags = str(native.get("compile_flags", "")).split()
    mxcsr = native.get("initial_mxcsr")
    if (
        native.get("binary_protocols")
        != {
            "allocation_item": "A4ALI001/A4ALO001/schema-1",
            "block_suite": (
                "A4BLK001/A4S_BLOCK_RESULT_V1/"
                "saq-attempt4-a4-1-20260713-schema2"
            ),
            "encoding_suite": "A4ENC002/A4EOUT02/schema-2",
            "scalar_suite": "A4SCL001/A4S_SCALAR_RESULT_V1",
        }
        or native.get("cpu_model") != _FIXED_ENVIRONMENT["CPU"]
        or native.get("openssl_version") != "OpenSSL " + _FIXED_ENVIRONMENT["OpenSSL"]
        or native.get("numeric_contract")
        != "FE_TONEAREST;MXCSR=0x00001f80;no-FTZ;no-DAZ;no-FMA-contraction"
        or native.get("initial_rounding_mode_name") != "FE_TONEAREST"
        or native.get("final_rounding_mode_name") != "FE_TONEAREST"
        or native.get("initial_mxcsr") != native.get("final_mxcsr")
        or native.get("initial_mxcsr_flush_to_zero") is not False
        or native.get("final_mxcsr_flush_to_zero") is not False
        or native.get("initial_mxcsr_denormals_are_zero") is not False
        or native.get("final_mxcsr_denormals_are_zero") is not False
    ):
        raise PreconditionFailure("native numeric runtime changed or is nonfrozen")
    observed = {
        "CPU": _cpu_model(),
        "GMP": native.get("gmp_version"),
        "MPFR": native.get("mpfr_version"),
        "MXCSR": f"{mxcsr}; FTZ=false; DAZ=false",
        "NumPy": importlib.metadata.version("numpy"),
        "OpenSSL": ssl.OPENSSL_VERSION.removeprefix("OpenSSL "),
        "Python": f"{platform.python_implementation()} {platform.python_version()}",
        "allowed_affinity": _affinity_text(set(os.sched_getaffinity(0))),
        "compiler": f"{native.get('compiler_id')} {native.get('compiler_version')}",
        "compiler_flags": flags,
        "governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text(
            encoding="ascii"
        ).strip(),
        "kernel": os.uname().release,
        "physical_memory_bytes": os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"),
        "rounding": native.get("initial_rounding_mode_name"),
        "SMT": "active"
        if Path("/sys/devices/system/cpu/smt/active").read_text(encoding="ascii").strip() == "1"
        else "inactive",
        "thread_environment": {
            key: os.environ.get(key) for key in sorted(_FIXED_CHILD_ENVIRONMENT)
        },
        "threads": 1,
        "turbo": "enabled; intel_pstate/no_turbo="
        + Path("/sys/devices/system/cpu/intel_pstate/no_turbo").read_text(
            encoding="ascii"
        ).strip(),
    }
    if observed != _FIXED_ENVIRONMENT:
        raise PreconditionFailure("observed environment differs from frozen identity")
    result = dict(observed)
    result["environment_sha256"] = _sha256(evidence.canonical_body(result))
    return result


def _prelaunch_observation(
    output_root: Path,
    environment_identity: Mapping[str, Any],
    inventory: tuple[list[dict[str, Any]], list[dict[str, Any]], int, int],
    observed_utc: str,
) -> tuple[dict[str, Any], int]:
    filters, processes, numeric_count, self_start = inventory
    meminfo, available_kib = _memory_observation()
    loadavg, load = _load_observation()
    filesystem_root = output_root if output_root.exists() else output_root.parent
    filesystem = os.statvfs(filesystem_root)
    free_bytes = int(filesystem.f_bavail) * int(filesystem.f_frsize)
    available_bytes = available_kib * 1024
    if available_bytes < MINIMUM_AVAILABLE_MEMORY:
        raise PreconditionFailure("available memory is below frozen minimum")
    if free_bytes < MINIMUM_FREE_OUTPUT:
        raise PreconditionFailure("free output bytes are below frozen minimum")
    observation = {
        "available_memory_requirement_pass": True,
        "available_physical_memory_bytes": available_bytes,
        "conflicting_process_requirement_pass": True,
        "effective_uid": os.geteuid(),
        "environment_identity_sha256": environment_identity["environment_sha256"],
        "environment_requirement_pass": True,
        "free_output_bytes": free_bytes,
        "free_output_requirement_pass": True,
        "load_average": load,
        "loadavg_hex": loadavg.hex(),
        "loadavg_sha256": _sha256(loadavg),
        "memavailable_kib": available_kib,
        "meminfo_hex": meminfo.hex(),
        "meminfo_sha256": _sha256(meminfo),
        "numeric_pid_count": numeric_count,
        "observed_utc": observed_utc,
        "output_f_bavail": int(filesystem.f_bavail),
        "output_f_frsize": int(filesystem.f_frsize),
        "output_filesystem_device_id": filesystem_root.stat().st_dev,
        "output_root": str(output_root),
        "pid_filter_records": filters,
        "preconditions_pass": True,
        "preflight_pid": os.getpid(),
        "preflight_start_time_clock_ticks": self_start,
        "process_inventory_complete": True,
        "same_user_process_count": len(processes),
        "same_user_processes": processes,
    }
    return observation, self_start


def _verify_sealed_file(value: Any, expected_read_path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256", "size_bytes"}:
        _fail("IMPLEMENTATION_INVALID", "sealed-file object has a nonfrozen shape")
    if value["path"] != expected_read_path:
        _fail("IMPLEMENTATION_INVALID", f"sealed path mismatch: {expected_read_path}")
    parts = expected_read_path.split("/")
    if expected_read_path.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        _fail("IMPLEMENTATION_INVALID", "sealed read_path is not repository-relative POSIX")
    payload = _read_regular_nofollow(
        REPOSITORY_ROOT / expected_read_path, 1 << 30
    )
    if value["sha256"] != _sha256(payload) or value["size_bytes"] != len(payload):
        _fail("IMPLEMENTATION_INVALID", f"sealed file identity mismatch: {expected_read_path}")
    return dict(value)


def _sealed_read_request(identity: Mapping[str, Any]) -> dict[str, Any]:
    """Expand a three-key authority identity into a no-override read request."""

    if set(identity) != {"path", "sha256", "size_bytes"}:
        _fail("IMPLEMENTATION_INVALID", "cannot expand a non-document identity")
    path = identity["path"]
    if not isinstance(path, str):
        _fail("IMPLEMENTATION_INVALID", "document identity path is not a string")
    return {
        "identity_path": path,
        "read_path": path,
        "sha256": identity["sha256"],
        "size_bytes": identity["size_bytes"],
    }


def _verify_review_commit_blob(
    review_commit: str, sealed: Mapping[str, Any], expected_path: str
) -> None:
    payload = _run_capture(
        (
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "show",
            f"{review_commit}:{expected_path}",
        )
    )
    if sealed.get("sha256") != _sha256(payload) or sealed.get("size_bytes") != len(
        payload
    ):
        _fail(
            "IMPLEMENTATION_INVALID",
            f"PAR review commit blob differs from binding: {expected_path}",
        )


def _rehash_regular_nofollow(path: Path) -> tuple[str, int]:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail("IMPLEMENTATION_INVALID", f"PAR artifact is not regular: {path.name}")
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or size != before.st_size
        ):
            _fail("IMPLEMENTATION_INVALID", f"PAR artifact changed while read: {path.name}")
        return digest.hexdigest(), size
    finally:
        os.close(descriptor)


def _read_regular_nofollow(path: Path, maximum_bytes: int) -> bytes:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum_bytes:
            _fail("IMPLEMENTATION_INVALID", f"invalid bounded PAR document: {path.name}")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, min(1 << 20, before.st_size - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        after = os.fstat(descriptor)
        if (
            len(payload) != before.st_size
            or before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
        ):
            _fail("IMPLEMENTATION_INVALID", f"PAR document changed while read: {path.name}")
        return bytes(payload)
    finally:
        os.close(descriptor)


_CURRENT_CPYTHON_IDENTITY: tuple[str, int] | None = None


def _uncached_current_cpython_identity(executable: str) -> tuple[str, int]:
    """Read one stable running image after pathname validation."""

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    image_fd = os.open("/proc/self/exe", flags)
    try:
        try:
            named_fd = os.open(executable, flags)
        except OSError as error:
            _fail("ARTIFACT_INVALID", f"cannot open current CPython path: {error}")
        try:
            image_before = os.fstat(image_fd)
            named_before = os.fstat(named_fd)
            stable_fields = (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
            if (
                not stat.S_ISREG(image_before.st_mode)
                or not stat.S_ISREG(named_before.st_mode)
                or image_before.st_size <= 0
                or image_before.st_size > (1 << 30)
                or image_before.st_dev != named_before.st_dev
                or image_before.st_ino != named_before.st_ino
            ):
                _fail(
                    "ARTIFACT_INVALID",
                    "current CPython path does not identify the running image",
                )
            digest = hashlib.sha256()
            remaining = image_before.st_size
            while remaining:
                chunk = os.read(image_fd, min(1 << 20, remaining))
                if not chunk:
                    _fail(
                        "ARTIFACT_INVALID",
                        "current CPython image ended before its fstat size",
                    )
                digest.update(chunk)
                remaining -= len(chunk)
            if os.read(image_fd, 1):
                _fail("ARTIFACT_INVALID", "current CPython image grew during read")
            image_after = os.fstat(image_fd)
            if any(
                getattr(image_before, field) != getattr(image_after, field)
                for field in stable_fields
            ):
                _fail("ARTIFACT_INVALID", "current CPython image changed during read")
        finally:
            os.close(named_fd)
    finally:
        os.close(image_fd)
    try:
        named_after_fd = os.open(executable, flags)
    except OSError as error:
        _fail("ARTIFACT_INVALID", f"cannot reopen current CPython path: {error}")
    try:
        named_after = os.fstat(named_after_fd)
    finally:
        os.close(named_after_fd)
    if any(
        getattr(image_after, field) != getattr(named_after, field)
        for field in stable_fields
    ):
        _fail("ARTIFACT_INVALID", "current CPython path changed during identity read")
    return digest.hexdigest(), image_after.st_size


def _current_cpython_identity() -> tuple[str, int]:
    """Return a stable identity for the interpreter image running this process."""

    global _CURRENT_CPYTHON_IDENTITY
    if _CURRENT_CPYTHON_IDENTITY is not None:
        return _CURRENT_CPYTHON_IDENTITY
    executable = sys.executable
    if (
        not isinstance(executable, str)
        or not executable
        or not os.path.isabs(executable)
        or os.path.normpath(executable) != executable
    ):
        _fail("ARTIFACT_INVALID", "current CPython path is not normalized absolute")
    try:
        identity = _uncached_current_cpython_identity(executable)
    except SupervisorFailure:
        raise
    except OSError as error:
        _fail("ARTIFACT_INVALID", f"cannot establish current CPython identity: {error}")
    _CURRENT_CPYTHON_IDENTITY = identity
    return _CURRENT_CPYTHON_IDENTITY


def _numpy_distribution_authority() -> dict[str, Any]:
    distribution = importlib.metadata.distribution("numpy")
    if distribution.version != "1.23.5" or distribution.files is None:
        _fail("IMPLEMENTATION_INVALID", "registered NumPy distribution changed")
    files = []
    for relative in distribution.files:
        path = Path(distribution.locate_file(relative)).resolve()
        try:
            path.relative_to(REPOSITORY_ROOT)
        except ValueError:
            pass
        else:
            _fail(
                "IMPLEMENTATION_INVALID",
                "registered NumPy distribution resolves inside repository",
            )
        payload = _read_regular_nofollow(path, 1 << 30)
        files.append(
            {
                "path": path.as_posix(),
                "sha256": _sha256(payload),
                "size_bytes": len(payload),
            }
        )
    files.sort(key=lambda item: item["path"].encode("utf-8"))
    if not files or len({item["path"] for item in files}) != len(files):
        _fail("IMPLEMENTATION_INVALID", "NumPy distribution closure is invalid")
    return {"files": files, "version": distribution.version}


def _admit_par_artifact_index(
    payload: bytes, implementation_commit: str
) -> None:
    index = _parse_json_document(payload, "PAR artifact index", True)
    if set(index) != {
        "artifact_kind",
        "files",
        "implementation_commit",
        "schema_version",
    } or (
        index.get("artifact_kind") != "a4_v2_par_artifact_index"
        or index.get("implementation_commit") != implementation_commit
        or index.get("schema_version") != 1
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR artifact-index envelope mismatch")
    files = index.get("files")
    if not isinstance(files, list) or len(files) != len(PAR_INDEXED_ARTIFACT_FILES):
        _fail("IMPLEMENTATION_INVALID", "PAR artifact-index inventory length mismatch")
    observed_names: list[str] = []
    for position, item in enumerate(files):
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size_bytes"}:
            _fail("IMPLEMENTATION_INVALID", "PAR artifact-index entry shape mismatch")
        name = item.get("path")
        if (
            not isinstance(name, str)
            or "/" in name
            or name in {"", ".", ".."}
            or name != PAR_INDEXED_ARTIFACT_FILES[position]
            or not isinstance(item.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None
            or not isinstance(item.get("size_bytes"), int)
            or isinstance(item.get("size_bytes"), bool)
            or item["size_bytes"] < 0
        ):
            _fail("IMPLEMENTATION_INVALID", "PAR artifact-index order/value mismatch")
        observed_names.append(name)
        sha256, size = _rehash_regular_nofollow(PAR_SEAL_PATH.parent / name)
        if sha256 != item["sha256"] or size != item["size_bytes"]:
            _fail("IMPLEMENTATION_INVALID", f"PAR indexed artifact mismatch: {name}")
    if len(set(observed_names)) != len(observed_names):
        _fail("IMPLEMENTATION_INVALID", "PAR artifact-index has duplicate paths")
    directory_names: set[str] = set()
    with os.scandir(PAR_SEAL_PATH.parent) as entries:
        for entry in entries:
            if not entry.is_file(follow_symlinks=False):
                _fail(
                    "IMPLEMENTATION_INVALID",
                    f"PAR artifact root contains nonregular member: {entry.name}",
                )
            directory_names.add(entry.name)
    if directory_names != PAR_DIRECTORY_FILES:
        _fail("IMPLEMENTATION_INVALID", "PAR artifact-root membership mismatch")


def _parse_utc_microseconds(value: Any, field: str) -> datetime_module.datetime:
    if not isinstance(value, str) or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
        value,
    ) is None:
        _fail("IMPLEMENTATION_INVALID", f"{field} is not canonical UTC-microseconds")
    if value[:4] == "0000":
        _fail("IMPLEMENTATION_INVALID", f"{field} year is outside 0001..9999")
    try:
        return datetime_module.datetime.strptime(
            value, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=datetime_module.timezone.utc)
    except ValueError as error:
        raise SupervisorFailure(
            "IMPLEMENTATION_INVALID", f"{field} is not a real UTC instant"
        ) from error


def _decode_par_hex(value: Any, field: str, *, nonempty: bool = False) -> bytes:
    if (
        not isinstance(value, str)
        or re.fullmatch(r"(?:[0-9a-f]{2})*", value) is None
        or (nonempty and not value)
    ):
        _fail("IMPLEMENTATION_INVALID", f"{field} is not canonical byte hex")
    return bytes.fromhex(value)


def _validate_par_process_inventory(value: Mapping[str, Any]) -> None:
    """Replay every byte-level PID-filter and same-user process decision."""

    filters = value["pid_filter_records"]
    processes = value["same_user_processes"]
    filter_keys = {
        "effective_uid",
        "initial_proc_status_hex",
        "initial_proc_status_sha256",
        "pid",
        "same_as_preflight_effective_uid",
    }
    process_keys = {
        "classification",
        "comm_hex",
        "conflicting_a4_or_saq_cost",
        "final_cmdline_hex",
        "final_cmdline_sha256",
        "final_executable_target_hex",
        "final_proc_stat_hex",
        "final_proc_stat_sha256",
        "final_proc_status_hex",
        "final_proc_status_sha256",
        "initial_cmdline_hex",
        "initial_cmdline_sha256",
        "initial_executable_target_hex",
        "initial_proc_stat_hex",
        "initial_proc_stat_sha256",
        "is_preflight_self",
        "matched_conflict_markers",
        "pid",
        "pid_filter_record_index",
        "start_time_clock_ticks",
        "state",
        "system_cpu_clock_ticks",
        "total_cpu_clock_ticks",
        "user_cpu_clock_ticks",
    }
    if (
        not isinstance(filters, list)
        or not filters
        or len(filters) != value["numeric_pid_count"]
        or not isinstance(processes, list)
        or len(processes) != value["same_user_process_count"]
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR process inventory cardinality mismatch")

    filter_pids: list[int] = []
    true_filter_indexes: list[int] = []
    for index, record in enumerate(filters):
        if not isinstance(record, dict) or set(record) != filter_keys:
            _fail("IMPLEMENTATION_INVALID", "PAR PID-filter record shape mismatch")
        pid = record["pid"]
        effective_uid = record["effective_uid"]
        if (
            not isinstance(pid, int)
            or isinstance(pid, bool)
            or pid <= 0
            or not isinstance(effective_uid, int)
            or isinstance(effective_uid, bool)
            or effective_uid < 0
            or not isinstance(record["same_as_preflight_effective_uid"], bool)
            or not isinstance(record["initial_proc_status_sha256"], str)
            or re.fullmatch(
                r"[0-9a-f]{64}", record["initial_proc_status_sha256"]
            )
            is None
        ):
            _fail("IMPLEMENTATION_INVALID", "PAR PID-filter value is invalid")
        raw_status = _decode_par_hex(
            record["initial_proc_status_hex"],
            f"PAR pid_filter_records[{index}].initial_proc_status_hex",
            nonempty=True,
        )
        if _sha256(raw_status) != record["initial_proc_status_sha256"]:
            _fail("IMPLEMENTATION_INVALID", "PAR PID-filter status hash mismatch")
        try:
            parsed_pid, parsed_uid = _parse_status(raw_status)
        except ValueError as error:
            raise SupervisorFailure(
                "IMPLEMENTATION_INVALID", "PAR PID-filter status is malformed"
            ) from error
        if parsed_pid != pid or parsed_uid != effective_uid:
            _fail("IMPLEMENTATION_INVALID", "PAR PID-filter identity mismatch")
        same_uid = parsed_uid == value["effective_uid"]
        if same_uid != record["same_as_preflight_effective_uid"]:
            _fail("IMPLEMENTATION_INVALID", "PAR PID-filter UID decision mismatch")
        filter_pids.append(pid)
        if same_uid:
            true_filter_indexes.append(index)
    if filter_pids != sorted(filter_pids) or len(filter_pids) != len(set(filter_pids)):
        _fail("IMPLEMENTATION_INVALID", "PAR PID filters are not strictly ordered")

    observed_filter_indexes: list[int] = []
    observed_process_keys: list[tuple[int, int]] = []
    self_count = 0
    for process_index, process in enumerate(processes):
        if not isinstance(process, dict) or set(process) != process_keys:
            _fail("IMPLEMENTATION_INVALID", "PAR same-user process shape mismatch")
        integer_fields = {
            "pid": 1,
            "pid_filter_record_index": 0,
            "start_time_clock_ticks": 0,
            "system_cpu_clock_ticks": 0,
            "total_cpu_clock_ticks": 0,
            "user_cpu_clock_ticks": 0,
        }
        if any(
            not isinstance(process[name], int)
            or isinstance(process[name], bool)
            or process[name] < minimum
            for name, minimum in integer_fields.items()
        ) or not isinstance(process["is_preflight_self"], bool):
            _fail("IMPLEMENTATION_INVALID", "PAR same-user integer/bool value is invalid")
        filter_index = process["pid_filter_record_index"]
        if (
            filter_index not in true_filter_indexes
            or filters[filter_index]["pid"] != process["pid"]
        ):
            _fail("IMPLEMENTATION_INVALID", "PAR process/filter mapping mismatch")
        observed_filter_indexes.append(filter_index)
        observed_process_keys.append(
            (process["pid"], process["start_time_clock_ticks"])
        )

        raw_fields: dict[str, bytes] = {}
        for field, nonempty in (
            ("initial_proc_stat", True),
            ("final_proc_stat", True),
            ("final_proc_status", True),
            ("initial_cmdline", False),
            ("final_cmdline", False),
        ):
            sha_name = f"{field}_sha256"
            sha = process[sha_name]
            if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{64}", sha) is None:
                _fail("IMPLEMENTATION_INVALID", f"PAR {sha_name} is invalid")
            raw = _decode_par_hex(
                process[f"{field}_hex"],
                f"PAR same_user_processes[{process_index}].{field}_hex",
                nonempty=nonempty,
            )
            if _sha256(raw) != sha:
                _fail("IMPLEMENTATION_INVALID", f"PAR {field} hash mismatch")
            raw_fields[field] = raw
        initial_executable = _decode_par_hex(
            process["initial_executable_target_hex"], "PAR initial executable"
        )
        final_executable = _decode_par_hex(
            process["final_executable_target_hex"], "PAR final executable"
        )
        comm = _decode_par_hex(process["comm_hex"], "PAR comm", nonempty=True)
        if (
            raw_fields["initial_cmdline"] != raw_fields["final_cmdline"]
            or initial_executable != final_executable
        ):
            _fail("IMPLEMENTATION_INVALID", "PAR process identity changed during inventory")
        try:
            _validate_cmdline(raw_fields["initial_cmdline"], process["pid"])
            _validate_cmdline(raw_fields["final_cmdline"], process["pid"])
            initial_stat = _parse_stat(raw_fields["initial_proc_stat"])
            final_stat = _parse_stat(raw_fields["final_proc_stat"])
            final_status = _parse_status(raw_fields["final_proc_status"])
        except (PreconditionFailure, UnicodeError, ValueError) as error:
            raise SupervisorFailure(
                "IMPLEMENTATION_INVALID", "PAR same-user process preimage is malformed"
            ) from error
        if (
            initial_stat.pid != process["pid"]
            or final_stat.pid != process["pid"]
            or final_status != (process["pid"], value["effective_uid"])
            or initial_stat.start_ticks != final_stat.start_ticks
            or final_stat.start_ticks != process["start_time_clock_ticks"]
            or final_stat.comm != comm
            or final_stat.state != process["state"]
            or final_stat.user_ticks != process["user_cpu_clock_ticks"]
            or final_stat.system_ticks != process["system_cpu_clock_ticks"]
            or process["total_cpu_clock_ticks"]
            != final_stat.user_ticks + final_stat.system_ticks
        ):
            _fail("IMPLEMENTATION_INVALID", "PAR process preimage replay mismatch")
        markers = _marker_matches(raw_fields["final_cmdline"], final_executable)
        if (
            not isinstance(process["matched_conflict_markers"], list)
            or any(
                not isinstance(marker, str) or marker not in CONFLICT_MARKERS
                for marker in process["matched_conflict_markers"]
            )
            or len(process["matched_conflict_markers"])
            != len(set(process["matched_conflict_markers"]))
            or markers != process["matched_conflict_markers"]
        ):
            _fail("IMPLEMENTATION_INVALID", "PAR conflict-marker replay mismatch")
        is_self = (
            process["pid"] == value["preflight_pid"]
            and process["start_time_clock_ticks"]
            == value["preflight_start_time_clock_ticks"]
        )
        if is_self != process["is_preflight_self"]:
            _fail("IMPLEMENTATION_INVALID", "PAR preflight-self identity mismatch")
        if is_self:
            self_count += 1
            if process["classification"] != "ALLOW_PREFLIGHT_SELF" or not markers:
                _fail("IMPLEMENTATION_INVALID", "PAR self classification mismatch")
        elif markers or process["classification"] != "ALLOW_NO_MARKER":
            _fail("IMPLEMENTATION_INVALID", "PAR nonself classification mismatch")
        if process["conflicting_a4_or_saq_cost"] is not False:
            _fail("IMPLEMENTATION_INVALID", "PAR inventory contains a conflict")

    if (
        sorted(observed_filter_indexes) != sorted(true_filter_indexes)
        or len(observed_filter_indexes) != len(true_filter_indexes)
        or observed_process_keys != sorted(observed_process_keys)
        or len(observed_process_keys) != len(set(observed_process_keys))
        or self_count != 1
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR same-user inventory is incomplete or unordered")


def _validate_par_prelaunch_observation(
    value: Any,
    *,
    environment_sha256: str,
    logical_preimage: Mapping[str, Any],
) -> None:
    keys = {
        "available_memory_requirement_pass",
        "available_physical_memory_bytes",
        "conflicting_process_requirement_pass",
        "effective_uid",
        "environment_identity_sha256",
        "environment_requirement_pass",
        "free_output_bytes",
        "free_output_requirement_pass",
        "load_average",
        "loadavg_hex",
        "loadavg_sha256",
        "memavailable_kib",
        "meminfo_hex",
        "meminfo_sha256",
        "numeric_pid_count",
        "observed_utc",
        "output_f_bavail",
        "output_f_frsize",
        "output_filesystem_device_id",
        "output_root",
        "pid_filter_records",
        "preconditions_pass",
        "preflight_pid",
        "preflight_start_time_clock_ticks",
        "process_inventory_complete",
        "same_user_process_count",
        "same_user_processes",
    }
    if not isinstance(value, dict) or set(value) != keys:
        _fail("IMPLEMENTATION_INVALID", "PAR prelaunch observation shape mismatch")
    integer_names = {
        "available_physical_memory_bytes",
        "effective_uid",
        "free_output_bytes",
        "memavailable_kib",
        "numeric_pid_count",
        "output_f_bavail",
        "output_f_frsize",
        "output_filesystem_device_id",
        "preflight_pid",
        "preflight_start_time_clock_ticks",
        "same_user_process_count",
    }
    if any(
        not isinstance(value[name], int)
        or isinstance(value[name], bool)
        or value[name] < 0
        for name in integer_names
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR prelaunch integer field is invalid")
    pass_names = {
        "available_memory_requirement_pass",
        "conflicting_process_requirement_pass",
        "environment_requirement_pass",
        "free_output_requirement_pass",
        "preconditions_pass",
        "process_inventory_complete",
    }
    if any(value[name] is not True for name in pass_names):
        _fail("IMPLEMENTATION_INVALID", "PAR prelaunch requirement did not pass")
    meminfo = _decode_par_hex(value["meminfo_hex"], "PAR meminfo_hex", nonempty=True)
    loadavg = _decode_par_hex(value["loadavg_hex"], "PAR loadavg_hex", nonempty=True)
    if (
        value["meminfo_sha256"] != _sha256(meminfo)
        or value["loadavg_sha256"] != _sha256(loadavg)
        or value["available_physical_memory_bytes"] < MINIMUM_AVAILABLE_MEMORY
        or value["free_output_bytes"] < MINIMUM_FREE_OUTPUT
        or value["available_physical_memory_bytes"]
        != value["memavailable_kib"] * 1024
        or value["free_output_bytes"]
        != value["output_f_bavail"] * value["output_f_frsize"]
        or value["environment_identity_sha256"] != environment_sha256
        or value["effective_uid"] != os.geteuid()
        or value["output_root"] != str(PAR_SEAL_PATH.parent)
        or value["preflight_pid"] != logical_preimage["preflight_pid"]
        or value["preflight_start_time_clock_ticks"]
        != logical_preimage["preflight_start_time_clock_ticks"]
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR prelaunch identity/cap binding mismatch")
    load = value.get("load_average")
    if not isinstance(load, dict) or set(load) != {
        "one_minute",
        "five_minute",
        "fifteen_minute",
    } or any(
        not isinstance(item, str)
        or re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", item) is None
        for item in load.values()
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR load-average preimage is invalid")
    load_tokens = loadavg.split()
    try:
        observed_load = [token.decode("ascii", errors="strict") for token in load_tokens[:3]]
    except UnicodeError as error:
        raise SupervisorFailure(
            "IMPLEMENTATION_INVALID", "PAR raw load-average token is not ASCII"
        ) from error
    if len(load_tokens) < 3 or observed_load != [
        load["one_minute"],
        load["five_minute"],
        load["fifteen_minute"],
    ]:
        _fail("IMPLEMENTATION_INVALID", "PAR raw load-average replay mismatch")
    memavailable: list[int] = []
    for line in meminfo.splitlines():
        if line.startswith(b"MemAvailable:"):
            match = re.fullmatch(rb"MemAvailable:\s+([0-9]+)\s+kB", line)
            if match is None:
                _fail("IMPLEMENTATION_INVALID", "PAR MemAvailable line is malformed")
            memavailable.append(int(match.group(1)))
    if memavailable != [value["memavailable_kib"]]:
        _fail("IMPLEMENTATION_INVALID", "PAR MemAvailable replay mismatch")
    _validate_par_process_inventory(value)
    _parse_utc_microseconds(value["observed_utc"], "PAR observed_utc")
    _parse_utc_microseconds(
        logical_preimage["prelaunch_utc"], "PAR logical prelaunch_utc"
    )
    if value["observed_utc"] != logical_preimage["prelaunch_utc"]:
        _fail("IMPLEMENTATION_INVALID", "PAR observation/logical UTC differ")


def _validate_par_receipts(
    receipts: Any, implementation_commit: str
) -> list[dict[str, Any]]:
    if not isinstance(receipts, list):
        _fail("IMPLEMENTATION_INVALID", "PAR receipts are not an array")
    receipt_keys = {
        "argv_sha256",
        "attempt_id",
        "binary_sha256",
        "completed_unit_index",
        "cpu_microseconds",
        "end_utc",
        "environment_sha256",
        "execution_commit",
        "exit_reason",
        "logical_run_id",
        "peak_rss_bytes",
        "phase",
        "staging_disposition",
        "start_utc",
        "wall_nanoseconds",
    }
    signatures: list[tuple[str, int, bool]] = []
    admitted: list[dict[str, Any]] = []
    shared: tuple[str, str, str, str] | None = None
    previous_end: datetime_module.datetime | None = None
    for index, raw in enumerate(receipts):
        if not isinstance(raw, dict) or set(raw) != receipt_keys:
            _fail("IMPLEMENTATION_INVALID", "PAR receipt shape mismatch")
        item = dict(raw)
        for name in ("argv_sha256", "binary_sha256", "environment_sha256", "logical_run_id"):
            if not isinstance(item[name], str) or re.fullmatch(r"[0-9a-f]{64}", item[name]) is None:
                _fail("IMPLEMENTATION_INVALID", f"PAR receipt {name} is invalid")
        integer_bounds = {
            "attempt_id": (0, 1),
            "completed_unit_index": (-1, -1),
            "cpu_microseconds": (0, PER_PHASE_CPU_LIMIT),
            "peak_rss_bytes": (0, RSS_LIMIT),
            "wall_nanoseconds": (0, PER_PHASE_WALL_LIMIT),
        }
        for name, (minimum, maximum) in integer_bounds.items():
            value = item[name]
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < minimum
                or value > maximum
            ):
                _fail("IMPLEMENTATION_INVALID", f"PAR receipt {name} is out of range")
        if item["execution_commit"] != implementation_commit:
            _fail("IMPLEMENTATION_INVALID", "PAR receipt commit differs from I")
        start = _parse_utc_microseconds(item["start_utc"], f"receipt[{index}].start_utc")
        end = _parse_utc_microseconds(item["end_utc"], f"receipt[{index}].end_utc")
        if start > end or (previous_end is not None and previous_end > start):
            _fail("IMPLEMENTATION_INVALID", "PAR receipt UTC chronology is invalid")
        previous_end = end
        complete = item["exit_reason"] == "PHASE_COMPLETE"
        if complete:
            if item["staging_disposition"] != "NONE":
                _fail("IMPLEMENTATION_INVALID", "completed PAR receipt disposition mismatch")
        elif (
            not isinstance(item["exit_reason"], str)
            or re.fullmatch(r"EXTERNAL_SIGNAL_([1-9]|[1-5][0-9]|6[0-4])", item["exit_reason"])
            is None
            or item["staging_disposition"] != "DISCARDED"
        ):
            _fail("IMPLEMENTATION_INVALID", "interrupted PAR receipt semantics mismatch")
        signatures.append((str(item["phase"]), int(item["attempt_id"]), complete))
        identity = (
            item["argv_sha256"],
            item["binary_sha256"],
            item["environment_sha256"],
            item["logical_run_id"],
        )
        if shared is None:
            shared = identity
        elif identity != shared:
            _fail("IMPLEMENTATION_INVALID", "PAR receipt authority identities differ")
        admitted.append(item)
    allowed = {
        (("B_build", 0, True), ("P_parity", 0, True)),
        (("B_build", 0, False), ("B_build", 1, True), ("P_parity", 0, True)),
        (("B_build", 0, True), ("P_parity", 0, False), ("P_parity", 1, True)),
        (
            ("B_build", 0, False),
            ("B_build", 1, True),
            ("P_parity", 0, False),
            ("P_parity", 1, True),
        ),
    }
    if tuple(signatures) not in allowed:
        _fail("IMPLEMENTATION_INVALID", "PAR receipt sequence is not one of four frozen forms")
    for left, right in zip(admitted, admitted[1:]):
        if (
            left["phase"] == right["phase"]
            or left["phase"] == "B_build" and right["phase"] == "P_parity"
        ) and left["end_utc"] != right["start_utc"]:
            _fail("IMPLEMENTATION_INVALID", "PAR adjacent attempt boundary is not exact")
    if sum(item["cpu_microseconds"] for item in admitted) > STUDY_CPU_LIMIT:
        _fail("IMPLEMENTATION_INVALID", "PAR receipts exceed study CPU ceiling")
    for phase in ("B_build", "P_parity"):
        selected = [item for item in admitted if item["phase"] == phase]
        if (
            sum(item["cpu_microseconds"] for item in selected)
            > PER_PHASE_CPU_LIMIT
            or sum(item["wall_nanoseconds"] for item in selected)
            > PER_PHASE_WALL_LIMIT
        ):
            _fail("IMPLEMENTATION_INVALID", f"PAR {phase} aggregate ceiling crossed")
    return admitted


def _validate_par_byte_ledger(
    entries: Any, index: Mapping[str, Any], artifact_index_size: int
) -> list[dict[str, Any]]:
    if not isinstance(entries, list) or len(entries) != 2:
        _fail("IMPLEMENTATION_INVALID", "PAR byte ledger is not the exact two-entry form")
    keys = {
        "created_temporary_bytes",
        "deleted_partial_bytes",
        "maximum_live_owned_temporary_bytes",
        "permanent_intermediate_bundle_bytes",
        "phase",
        "research_evidence_archive_bytes",
    }
    admitted: list[dict[str, Any]] = []
    for position, phase in enumerate(("B_build", "P_parity")):
        raw = entries[position]
        if not isinstance(raw, dict) or set(raw) != keys or raw.get("phase") != phase:
            _fail("IMPLEMENTATION_INVALID", "PAR byte-ledger entry shape/order mismatch")
        item = dict(raw)
        for name in keys - {"phase"}:
            value = item[name]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                _fail("IMPLEMENTATION_INVALID", f"PAR byte-ledger {name} is invalid")
        if (
            item["permanent_intermediate_bundle_bytes"] != 0
            or item["maximum_live_owned_temporary_bytes"] > TEMPORARY_LIMIT
            or item["research_evidence_archive_bytes"] > item["created_temporary_bytes"]
            or item["deleted_partial_bytes"] > item["created_temporary_bytes"]
        ):
            _fail("IMPLEMENTATION_INVALID", "PAR byte-ledger cap/reconciliation mismatch")
        admitted.append(item)
    files = index.get("files")
    if not isinstance(files, list):
        _fail("IMPLEMENTATION_INVALID", "PAR index files are absent")
    sizes = {
        item.get("path"): item.get("size_bytes")
        for item in files
        if isinstance(item, dict)
    }
    expected_b = sum(int(sizes[name]) for name in PAR_BUILD_ARTIFACT_FILES)
    expected_p = sum(int(sizes[name]) for name in PAR_PARITY_ARTIFACT_FILES)
    expected_p += artifact_index_size
    if (
        admitted[0]["research_evidence_archive_bytes"] != expected_b
        or admitted[1]["research_evidence_archive_bytes"] != expected_p
        or expected_b + expected_p > EVIDENCE_LIMIT
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR evidence-byte ledger does not reconcile")
    return admitted


def _git_object_id(specification: str) -> str:
    value = _run_capture(
        ("git", "-C", str(REPOSITORY_ROOT), "rev-parse", specification)
    ).decode("ascii", errors="strict").strip()
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        _fail("IMPLEMENTATION_INVALID", f"invalid Git object identity: {specification}")
    return value


def _git_par_tree(commit: str) -> tuple[tuple[str, str, str, str], ...]:
    treeish = f"{commit}:docs/saq_a4_v2_par_artifacts_2026_07_14"
    payload = _run_capture(
        ("git", "-C", str(REPOSITORY_ROOT), "ls-tree", "-r", "-z", treeish)
    )
    records: list[tuple[str, str, str, str]] = []
    for raw in payload.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, path_bytes = raw.split(b"\t", 1)
            mode, kind, object_id = metadata.decode("ascii").split(" ")
            path = path_bytes.decode("utf-8", errors="strict")
        except (UnicodeError, ValueError) as error:
            raise SupervisorFailure(
                "IMPLEMENTATION_INVALID", "malformed recursive PAR Git tree"
            ) from error
        records.append((mode, kind, object_id, path))
    records.sort(key=lambda item: item[3].encode("utf-8"))
    if (
        {item[3] for item in records} != PAR_DIRECTORY_FILES
        or any(item[0] != "100644" or item[1] != "blob" for item in records)
        or len(records) != len(PAR_DIRECTORY_FILES)
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR Git tree mode/type/membership mismatch")
    return tuple(records)


def _load_par_seal(
    commit: str, source_tree: str, implementation_manifest_payload: bytes
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    payload = _read_regular_nofollow(PAR_SEAL_PATH, 65_536)
    if len(payload) > 5_171:
        _fail("IMPLEMENTATION_INVALID", "PAR seal exceeds exact maximal-instance bound")
    seal = _parse_json_document(payload, "PAR seal", True)
    required = {
        "artifact_index",
        "artifact_kind",
        "build_manifest",
        "implementation_commit",
        "parity_pass",
        "parity_summary",
        "phase_byte_ledger",
        "phase_receipts",
        "producer_native",
        "protocol",
        "schema",
        "schema_version",
        "source_manifest",
        "source_tree_sha256",
        "verifier_native",
    }
    if not isinstance(seal, dict) or set(seal) != required or (
        seal.get("artifact_kind") != "a4_v2_par_seal"
        or seal.get("schema_version") != 1
        or seal.get("parity_pass") is not True
        or seal.get("source_tree_sha256") != source_tree
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR seal is absent, stale, or unsuccessful")
    implementation_commit = seal.get("implementation_commit")
    if not isinstance(implementation_commit, str) or re.fullmatch(
        r"[0-9a-f]{40}", implementation_commit
    ) is None:
        _fail("IMPLEMENTATION_INVALID", "PAR implementation commit is invalid")
    protocol = _verify_sealed_file(
        seal["protocol"], "docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json"
    )
    schema = _verify_sealed_file(
        seal["schema"], "docs/saq_a4_v2_artifact_schema_2026_07_14.json"
    )
    source_manifest = _verify_sealed_file(
        seal["source_manifest"],
        "docs/saq_a4_v2_implementation_manifest_2026_07_14.json",
    )
    if (
        source_manifest["sha256"] != _sha256(implementation_manifest_payload)
        or source_manifest["size_bytes"] != len(implementation_manifest_payload)
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR source manifest differs from current closure")
    producer_file = _verify_sealed_file(seal["producer_native"], "build/a4_v2/a4_v2_native")
    verifier_file = _verify_sealed_file(
        seal["verifier_native"], "build/a4_v2_verifier/a4_v2_native"
    )
    build_manifest = _verify_sealed_file(
        seal["build_manifest"],
        "docs/saq_a4_v2_par_artifacts_2026_07_14/build_manifest.json",
    )
    parity_summary = _verify_sealed_file(
        seal["parity_summary"],
        "docs/saq_a4_v2_par_artifacts_2026_07_14/parity_summary.json",
    )
    artifact_index = _verify_sealed_file(
        seal["artifact_index"],
        "docs/saq_a4_v2_par_artifacts_2026_07_14/artifact_index.json",
    )
    receipts = _validate_par_receipts(seal.get("phase_receipts"), implementation_commit)
    build_manifest_payload = _read_regular_nofollow(
        PAR_SEAL_PATH.parent / "build_manifest.json", 16 << 20
    )
    build_manifest_document = _parse_json_document(
        build_manifest_payload, "PAR build manifest", True
    )
    if not isinstance(build_manifest_document, dict):
        _fail("IMPLEMENTATION_INVALID", "PAR build manifest is not an object")
    logical_preimage = build_manifest_document.get("logical_run_preimage")
    environment_preimage = build_manifest_document.get("environment_preimage")
    if not isinstance(logical_preimage, dict) or not isinstance(environment_preimage, dict):
        _fail("IMPLEMENTATION_INVALID", "PAR receipt identity preimages are absent")
    logical_keys = {
        "execution_commit",
        "outer_argv",
        "output_root",
        "preflight_pid",
        "preflight_start_time_clock_ticks",
        "prelaunch_utc",
        "protocol_version",
    }
    environment_keys = {
        "host_environment",
        "implementation_commit",
        "leader_binary_sha256",
        "leader_binary_size_bytes",
        "numpy_authority",
        "tool_paths",
    }
    outer_argv = logical_preimage.get("outer_argv")
    host_environment = environment_preimage.get("host_environment")
    numpy_authority = environment_preimage.get("numpy_authority")
    expected_par_argv = [
        "script/run_arbitrary_cardinality_a4_v2.py",
        "par",
        "docs/saq_a4_v2_par_artifacts_2026_07_14",
    ]
    if (
        set(logical_preimage) != logical_keys
        or set(environment_preimage) != environment_keys
        or outer_argv != expected_par_argv
        or host_environment != _FIXED_ENVIRONMENT
        or not isinstance(numpy_authority, dict)
        or set(numpy_authority) != {"files", "version"}
        or not isinstance(numpy_authority.get("files"), list)
        or numpy_authority.get("version") != "1.23.5"
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR receipt identity preimage shape mismatch")
    expected_logical = _sha256(evidence.canonical_body(logical_preimage))
    expected_environment = _sha256(evidence.canonical_body(environment_preimage))
    expected_argv = _sha256(evidence.canonical_body(outer_argv))
    leader_binary_sha256 = environment_preimage.get("leader_binary_sha256")
    leader_binary_size_bytes = environment_preimage.get("leader_binary_size_bytes")
    current_leader_sha256, current_leader_size_bytes = _current_cpython_identity()
    current_numpy_authority = _numpy_distribution_authority()
    build_producer = build_manifest_document.get("producer")
    build_verifier = build_manifest_document.get("verifier")
    build_toolchain = build_manifest_document.get("toolchain")
    par_prelaunch_observation = build_manifest_document.get("prelaunch_observation")
    if (
        build_manifest_document.get("artifact_kind") != "a4_v2_build_manifest"
        or build_manifest_document.get("schema_version") != 1
        or build_manifest_document.get("implementation_commit")
        != implementation_commit
        or build_manifest_document.get("build_commands")
        != [list(command) for command in BUILD_COMMANDS]
        or build_manifest_document.get("protocol") != protocol
        or build_manifest_document.get("schema") != schema
        or build_manifest_document.get("source_manifest") != source_manifest
        or not isinstance(build_producer, dict)
        or build_producer.get("binary") != producer_file
        or not isinstance(build_verifier, dict)
        or build_verifier.get("binary") != verifier_file
        or not isinstance(build_toolchain, dict)
        or build_toolchain.get("compile_flags") != _FIXED_ENVIRONMENT["compiler_flags"]
        or logical_preimage.get("protocol_version") != producer.PROTOCOL_VERSION
        or logical_preimage.get("execution_commit") != implementation_commit
        or logical_preimage.get("output_root") != str(PAR_SEAL_PATH.parent)
        or not isinstance(logical_preimage.get("preflight_pid"), int)
        or isinstance(logical_preimage.get("preflight_pid"), bool)
        or logical_preimage["preflight_pid"] <= 0
        or not isinstance(
            logical_preimage.get("preflight_start_time_clock_ticks"), int
        )
        or isinstance(logical_preimage.get("preflight_start_time_clock_ticks"), bool)
        or logical_preimage["preflight_start_time_clock_ticks"] <= 0
        or environment_preimage.get("implementation_commit")
        != implementation_commit
        or environment_preimage.get("tool_paths")
        != [CMAKE_BINARY, NINJA_BINARY, CXX_BINARY]
        or not isinstance(leader_binary_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", leader_binary_sha256) is None
        or not isinstance(leader_binary_size_bytes, int)
        or isinstance(leader_binary_size_bytes, bool)
        or leader_binary_size_bytes <= 0
        or leader_binary_sha256 != current_leader_sha256
        or leader_binary_size_bytes != current_leader_size_bytes
        or numpy_authority != current_numpy_authority
        or build_manifest_document.get("logical_run_id") != expected_logical
        or build_manifest_document.get("environment_sha256") != expected_environment
        or any(item["logical_run_id"] != expected_logical for item in receipts)
        or any(item["environment_sha256"] != expected_environment for item in receipts)
        or any(item["argv_sha256"] != expected_argv for item in receipts)
        or any(item["binary_sha256"] != leader_binary_sha256 for item in receipts)
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR receipt identity/preimage binding mismatch")
    _parse_utc_microseconds(
        logical_preimage["prelaunch_utc"], "PAR logical prelaunch_utc"
    )
    _validate_par_prelaunch_observation(
        par_prelaunch_observation,
        environment_sha256=expected_environment,
        logical_preimage=logical_preimage,
    )
    admitted_index_payload = _read_regular_nofollow(
        PAR_SEAL_PATH.parent / "artifact_index.json", 16 << 20
    )
    if (
        _sha256(admitted_index_payload) != artifact_index["sha256"]
        or len(admitted_index_payload) != artifact_index["size_bytes"]
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR artifact-index sealed identity mismatch")
    _admit_par_artifact_index(admitted_index_payload, implementation_commit)
    admitted_index = _parse_json_document(
        admitted_index_payload, "PAR artifact index", True
    )
    byte_entries = _validate_par_byte_ledger(
        seal.get("phase_byte_ledger"), admitted_index, len(admitted_index_payload)
    )

    review_payload = _read_regular_nofollow(PAR_REVIEW_BINDING_PATH, 65_536)
    review = _parse_json_document(review_payload, "PAR review binding", True)
    if not isinstance(review, dict) or set(review) != {
        "artifact_index",
        "artifact_kind",
        "implementation_commit",
        "par_artifact_commit",
        "par_artifact_tree_oid",
        "par_seal",
        "par_seal_maximal_instance_bytes",
        "par_seal_schema_pass",
        "review_commit",
        "review_memo",
        "review_pass",
        "schema_version",
        "source_tree_sha256",
    } or (
        review.get("artifact_kind") != "a4_v2_par_review_binding"
        or review.get("schema_version") != 1
        or review.get("review_pass") is not True
        or review.get("source_tree_sha256") != source_tree
        or review.get("implementation_commit") != implementation_commit
        or review.get("par_seal_schema_pass") is not True
        or review.get("par_seal_maximal_instance_bytes") != 5_171
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR independent-review binding is invalid")
    par_artifact_commit = review.get("par_artifact_commit")
    review_commit = review.get("review_commit")
    tree_oid = review.get("par_artifact_tree_oid")
    if any(
        not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None
        for value in (par_artifact_commit, review_commit, tree_oid)
    ):
        _fail("IMPLEMENTATION_INVALID", "PAR P/R/tree Git identity is invalid")
    if len({implementation_commit, par_artifact_commit, review_commit, commit}) != 4:
        _fail(
            "IMPLEMENTATION_INVALID",
            "PAR authority chain must use four strict commits I < P < R < E",
        )
    for ancestor, descendant in (
        (implementation_commit, par_artifact_commit),
        (par_artifact_commit, review_commit),
        (review_commit, commit),
    ):
        _run_capture(
            (
                "git",
                "-C",
                str(REPOSITORY_ROOT),
                "merge-base",
                "--is-ancestor",
                ancestor,
                descendant,
            )
        )
    tree_specification = "docs/saq_a4_v2_par_artifacts_2026_07_14"
    observed_tree_oids = tuple(
        _git_object_id(f"{authority}:{tree_specification}")
        for authority in (par_artifact_commit, review_commit, commit)
    )
    if observed_tree_oids != (tree_oid, tree_oid, tree_oid):
        _fail("IMPLEMENTATION_INVALID", "PAR tree OID changed across P/R/E")
    p_tree = _git_par_tree(par_artifact_commit)
    if _git_par_tree(review_commit) != p_tree or _git_par_tree(commit) != p_tree:
        _fail("IMPLEMENTATION_INVALID", "recursive PAR tree changed across P/R/E")
    sealed_par = _verify_sealed_file(
        review["par_seal"],
        "docs/saq_a4_v2_par_artifacts_2026_07_14/par_seal.json",
    )
    sealed_index = _verify_sealed_file(
        review["artifact_index"],
        "docs/saq_a4_v2_par_artifacts_2026_07_14/artifact_index.json",
    )
    sealed_review_memo = _verify_sealed_file(
        review["review_memo"],
        "docs/saq_a4_v2_par_artifacts_independent_review_2026_07_14.md",
    )
    if sealed_par["sha256"] != _sha256(payload) or sealed_index != artifact_index:
        _fail("IMPLEMENTATION_INVALID", "PAR review does not bind the admitted seal/index")
    _verify_review_commit_blob(
        review_commit,
        sealed_par,
        "docs/saq_a4_v2_par_artifacts_2026_07_14/par_seal.json",
    )
    _verify_review_commit_blob(
        review_commit,
        sealed_index,
        "docs/saq_a4_v2_par_artifacts_2026_07_14/artifact_index.json",
    )
    _verify_review_commit_blob(
        review_commit,
        sealed_review_memo,
        "docs/saq_a4_v2_par_artifacts_independent_review_2026_07_14.md",
    )
    committed_binding = _run_capture(
        (
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "show",
            f"{commit}:docs/saq_a4_v2_execution_authority_2026_07_14/par_review_binding.json",
        )
    )
    if committed_binding != review_payload:
        _fail("IMPLEMENTATION_INVALID", "E does not commit the admitted PAR binding")
    result = dict(seal)
    result["protocol"] = protocol
    result["schema"] = schema
    result["source_manifest"] = source_manifest
    result["producer_native"] = producer_file
    result["verifier_native"] = verifier_file
    result["build_manifest"] = build_manifest
    result["parity_summary"] = parity_summary
    par_review_binding = {
        "path": "docs/saq_a4_v2_execution_authority_2026_07_14/par_review_binding.json",
        "sha256": _sha256(review_payload),
        "size_bytes": len(review_payload),
    }
    return (
        [dict(item) for item in receipts],
        [dict(item) for item in byte_entries],
        result,
        par_review_binding,
    )


@dataclass
class PhaseBytes:
    created: int = 0
    deleted_partial: int = 0
    maximum_live: int = 0
    bundle: int = 0
    evidence_archive: int = 0


class ByteLedger:
    def __init__(self) -> None:
        self.phase = "C_setup"
        self.entries = {phase: PhaseBytes() for phase in PHASE_ORDER}
        self.live: dict[Path, int] = {}
        self.bundle_reservations: dict[str, int] = {}
        self.sealed_research_evidence_bytes = 0

    def bind_sealed_research_evidence(self, byte_count: int) -> None:
        if (
            not isinstance(byte_count, int)
            or isinstance(byte_count, bool)
            or byte_count < 0
            or self.sealed_research_evidence_bytes != 0
            or any(item.evidence_archive for item in self.entries.values())
        ):
            _fail("IMPLEMENTATION_INVALID", "invalid sealed evidence-byte baseline")
        self.sealed_research_evidence_bytes = byte_count
        if byte_count > EVIDENCE_LIMIT:
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", "sealed evidence exceeds byte ceiling")

    def switch(self, phase: str) -> None:
        self.phase = phase

    def _refresh_peak(self) -> None:
        live = sum(self.live.values())
        entry = self.entries[self.phase]
        entry.maximum_live = max(entry.maximum_live, live)
        if live > TEMPORARY_LIMIT:
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", "owned temporary-byte ceiling crossed")

    def note_created(
        self,
        path: Path,
        expected_metadata: os.stat_result | None = None,
    ) -> None:
        try:
            metadata = os.stat(path, follow_symlinks=False)
        except OSError as error:
            _fail("ARTIFACT_INVALID", f"cannot stat created temporary {path}: {error}")
        if stat.S_ISDIR(metadata.st_mode):
            return
        if not stat.S_ISREG(metadata.st_mode):
            _fail("ARTIFACT_INVALID", f"created temporary is not regular: {path}")
        if expected_metadata is not None:
            stable_fields = (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
            if any(
                getattr(expected_metadata, field) != getattr(metadata, field)
                for field in stable_fields
            ):
                _fail(
                    "ARTIFACT_INVALID",
                    f"created temporary identity changed before admission: {path}",
                )
        size = metadata.st_size
        if path in self.live:
            _fail("IMPLEMENTATION_INVALID", f"temporary path counted twice: {path}")
        previous, interrupted = _block_sigint_for_critical_section()
        try:
            self.live[path] = size
            self.entries[self.phase].created += size
            self._refresh_peak()
        except BaseException:
            _restore_sigint_after_receipt(previous)
            raise
        if _restore_sigint_after_receipt(previous):
            interrupted = True
        if interrupted:
            raise KeyboardInterrupt("temporary-byte admission interrupted at commit edge")

    def note_deleted(self, path: Path) -> None:
        if path not in self.live:
            _fail("IMPLEMENTATION_INVALID", f"deleted temporary was not owned: {path}")
        previous, interrupted = _block_sigint_for_critical_section()
        try:
            del self.live[path]
        except BaseException:
            _restore_sigint_after_receipt(previous)
            raise
        if _restore_sigint_after_receipt(previous):
            interrupted = True
        if interrupted:
            raise KeyboardInterrupt("temporary deletion interrupted at commit edge")

    def note_discarded_file(self, path: Path) -> None:
        """Commit deletion of one admitted partial regular-file artifact."""

        if path not in self.live:
            _fail("IMPLEMENTATION_INVALID", f"discarded file was not owned: {path}")
        self.entries[self.phase].deleted_partial += self.live[path]
        del self.live[path]

    def reserve_bundle(self, byte_count: int) -> None:
        if (
            not isinstance(byte_count, int)
            or isinstance(byte_count, bool)
            or byte_count < 0
            or self.phase in self.bundle_reservations
        ):
            _fail("IMPLEMENTATION_INVALID", "invalid or duplicate bundle-byte reservation")
        reserved_total = sum(self.bundle_reservations.values()) + byte_count
        if (
            sum(item.bundle for item in self.entries.values()) + reserved_total
            > BUNDLE_LIMIT
        ):
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", "bundle-byte ceiling crossed")
        self.bundle_reservations[self.phase] = byte_count

    def commit_bundle(self, byte_count: int) -> None:
        # The producer calls this only after the atomic rename has made the
        # permanent target physically visible.  All fallible protocol checks
        # therefore belong in reserve_bundle(), before that rename.  Consume
        # the already-validated reservation without introducing a new
        # post-publication rejection point.
        reserved = self.bundle_reservations.pop(self.phase, byte_count)
        for path in tuple(self.live):
            if "bundle.staging" in path.parts:
                del self.live[path]
        self.entries[self.phase].bundle += reserved

    def cancel_bundle(self, byte_count: int) -> None:
        reserved = self.bundle_reservations.get(self.phase)
        if reserved != byte_count:
            _fail("IMPLEMENTATION_INVALID", "bundle cancellation differs from reservation")
        del self.bundle_reservations[self.phase]

    def publish_evidence(self, byte_count: int) -> None:
        for path in tuple(self.live):
            if "evidence.staging" in path.parts:
                del self.live[path]
        self.entries[self.phase].evidence_archive += byte_count
        if (
            self.sealed_research_evidence_bytes
            + sum(item.evidence_archive for item in self.entries.values())
            > EVIDENCE_LIMIT
        ):
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", "evidence/archive byte ceiling crossed")

    def atomic_external_file(self, phase: str, byte_count: int) -> None:
        entry = self.entries[phase]
        entry.created += byte_count
        conservative_live = sum(self.live.values()) + byte_count
        entry.maximum_live = max(entry.maximum_live, conservative_live)
        entry.evidence_archive += byte_count
        evidence_total = self.sealed_research_evidence_bytes + sum(
            item.evidence_archive for item in self.entries.values()
        )
        # The external no-replace rename is already visible when the parent
        # records these bytes.  Account the complete immutable file first so
        # a terminal archive resource receipt cannot understate publication.
        if conservative_live > TEMPORARY_LIMIT:
            _fail(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "owned temporary-byte ceiling crossed at external publication",
            )
        if evidence_total > EVIDENCE_LIMIT:
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", "evidence/archive byte ceiling crossed")

    def replace_phase(self, phase: str, value: Mapping[str, Any]) -> None:
        keys = {
            "created_temporary_bytes",
            "deleted_partial_bytes",
            "maximum_live_owned_temporary_bytes",
            "permanent_intermediate_bundle_bytes",
            "phase",
            "research_evidence_archive_bytes",
        }
        if set(value) != keys or value.get("phase") != phase:
            _fail("IMPLEMENTATION_INVALID", f"{phase} child byte ledger shape mismatch")
        names = keys - {"phase"}
        if any(
            not isinstance(value[name], int)
            or isinstance(value[name], bool)
            or value[name] < 0
            for name in names
        ):
            _fail("IMPLEMENTATION_INVALID", f"{phase} child byte ledger is noncanonical")
        created = value["created_temporary_bytes"]
        deleted = value["deleted_partial_bytes"]
        maximum_live = value["maximum_live_owned_temporary_bytes"]
        bundle = value["permanent_intermediate_bundle_bytes"]
        evidence_archive = value["research_evidence_archive_bytes"]
        if (
            deleted > created
            or bundle > created
            or evidence_archive > created
            or maximum_live > TEMPORARY_LIMIT
        ):
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", f"{phase} child byte ceiling crossed")
        candidate = PhaseBytes(
            created=created,
            deleted_partial=deleted,
            maximum_live=maximum_live,
            bundle=bundle,
            evidence_archive=evidence_archive,
        )
        prior = self.entries[phase]
        self.entries[phase] = candidate
        if (
            sum(item.bundle for item in self.entries.values()) > BUNDLE_LIMIT
            or self.sealed_research_evidence_bytes
            + sum(item.evidence_archive for item in self.entries.values())
            > EVIDENCE_LIMIT
        ):
            self.entries[phase] = prior
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", f"{phase} global byte ceiling crossed")

    def phase_object(self, phase: str) -> dict[str, Any]:
        item = self.entries[phase]
        return {
            "created_temporary_bytes": item.created,
            "deleted_partial_bytes": item.deleted_partial,
            "maximum_live_owned_temporary_bytes": item.maximum_live,
            "permanent_intermediate_bundle_bytes": item.bundle,
            "phase": phase,
            "research_evidence_archive_bytes": item.evidence_archive,
        }

    def _regular_tree_inventory(self, path: Path) -> list[tuple[Path, int]]:
        """Inventory one terminated-child tree without following any link."""

        stable_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )

        def require_same_identity(
            expected: os.stat_result,
            observed: os.stat_result,
            description: str,
        ) -> None:
            if any(
                getattr(expected, field) != getattr(observed, field)
                for field in stable_fields
            ):
                _fail("ARTIFACT_INVALID", f"owned tree identity changed: {description}")

        try:
            root_named = os.stat(path, follow_symlinks=False)
        except FileNotFoundError:
            return []
        except OSError as error:
            _fail("ARTIFACT_INVALID", f"cannot stat owned tree {path}: {error}")
        if not stat.S_ISDIR(root_named.st_mode):
            _fail("ARTIFACT_INVALID", f"owned tree root is not a real directory: {path}")

        directory_flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        file_flags = os.O_PATH | getattr(os, "O_CLOEXEC", 0) | getattr(
            os, "O_NOFOLLOW", 0
        )
        try:
            root_fd = os.open(path, directory_flags)
        except OSError as error:
            _fail("ARTIFACT_INVALID", f"cannot open owned tree {path}: {error}")
        result: list[tuple[Path, int]] = []

        def visit(directory_fd: int, directory: Path) -> None:
            directory_before = os.fstat(directory_fd)
            try:
                with os.scandir(directory_fd) as iterator:
                    entries = sorted(
                        iterator,
                        key=lambda item: item.name.encode("utf-8"),
                    )
                for entry in entries:
                    metadata = entry.stat(follow_symlinks=False)
                    child = directory / entry.name
                    if stat.S_ISDIR(metadata.st_mode):
                        child_fd: int | None = None
                        try:
                            child_fd = os.open(
                                entry.name,
                                directory_flags,
                                dir_fd=directory_fd,
                            )
                            opened = os.fstat(child_fd)
                            require_same_identity(metadata, opened, str(child))
                            visit(child_fd, child)
                            after = os.fstat(child_fd)
                            named_after = os.stat(
                                entry.name,
                                dir_fd=directory_fd,
                                follow_symlinks=False,
                            )
                            require_same_identity(opened, after, str(child))
                            require_same_identity(opened, named_after, str(child))
                        finally:
                            active_error = sys.exc_info()[0] is not None
                            if child_fd is not None:
                                try:
                                    os.close(child_fd)
                                except OSError as error:
                                    if not active_error:
                                        _fail(
                                            "ARTIFACT_INVALID",
                                            f"cannot close owned directory {child}: {error}",
                                        )
                    elif stat.S_ISREG(metadata.st_mode):
                        child_fd = None
                        try:
                            child_fd = os.open(
                                entry.name,
                                file_flags,
                                dir_fd=directory_fd,
                            )
                            opened = os.fstat(child_fd)
                            named_after = os.stat(
                                entry.name,
                                dir_fd=directory_fd,
                                follow_symlinks=False,
                            )
                            require_same_identity(metadata, opened, str(child))
                            require_same_identity(opened, named_after, str(child))
                            result.append((child, opened.st_size))
                        finally:
                            active_error = sys.exc_info()[0] is not None
                            if child_fd is not None:
                                try:
                                    os.close(child_fd)
                                except OSError as error:
                                    if not active_error:
                                        _fail(
                                            "ARTIFACT_INVALID",
                                            f"cannot close owned file {child}: {error}",
                                        )
                    else:
                        _fail(
                            "ARTIFACT_INVALID",
                            f"owned tree contains a link or special node: {child}",
                        )
                directory_after = os.fstat(directory_fd)
                require_same_identity(
                    directory_before,
                    directory_after,
                    str(directory),
                )
            except SupervisorFailure:
                raise
            except (OSError, UnicodeError) as error:
                _fail(
                    "ARTIFACT_INVALID",
                    f"cannot inventory owned tree directory {directory}: {error}",
                )

        try:
            root_opened = os.fstat(root_fd)
            require_same_identity(root_named, root_opened, str(path))
            visit(root_fd, path)
            root_after = os.fstat(root_fd)
            root_named_after = os.stat(path, follow_symlinks=False)
            require_same_identity(root_opened, root_after, str(path))
            require_same_identity(root_opened, root_named_after, str(path))
        except SupervisorFailure:
            raise
        except OSError as error:
            _fail("ARTIFACT_INVALID", f"owned tree root changed: {path}: {error}")
        finally:
            active_error = sys.exc_info()[0] is not None
            try:
                os.close(root_fd)
            except OSError as error:
                if not active_error:
                    _fail(
                        "ARTIFACT_INVALID",
                        f"cannot close owned tree root {path}: {error}",
                    )
        return result

    def discard_tree(self, path: Path) -> None:
        inventory = self._regular_tree_inventory(path)
        inventory_by_path = dict(inventory)
        tracked = {
            child: size
            for child, size in self.live.items()
            if child == path or path in child.parents
        }
        if set(tracked) - set(inventory_by_path) or any(
            inventory_by_path[child] != size for child, size in tracked.items()
        ):
            _fail(
                "ARTIFACT_INVALID",
                f"owned tree differs from its admitted live-byte identities: {path}",
            )
        total = sum(size for _, size in inventory)
        for child, size in inventory:
            if child not in self.live:
                self.entries[self.phase].created += size
        self.entries[self.phase].deleted_partial += total
        for child in tuple(self.live):
            if child == path or path in child.parents:
                del self.live[child]

    def admit_tree(self, path: Path) -> None:
        for child, size in self._regular_tree_inventory(path):
            if child in self.live and self.live[child] != size:
                _fail(
                    "ARTIFACT_INVALID",
                    f"owned temporary changed size before tree admission: {child}",
                )
            if child not in self.live:
                self.live[child] = size
                self.entries[self.phase].created += size
        self._refresh_peak()

    def objects(self, sealed: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        if self.bundle_reservations:
            _fail("IMPLEMENTATION_INVALID", "unresolved bundle-byte reservation")
        if (
            sum(item["research_evidence_archive_bytes"] for item in sealed)
            != self.sealed_research_evidence_bytes
        ):
            _fail("IMPLEMENTATION_INVALID", "sealed evidence-byte baseline changed")
        sealed_by_phase = {item["phase"]: dict(item) for item in sealed}
        result = []
        for phase in PHASE_ORDER:
            if phase in sealed_by_phase:
                result.append(sealed_by_phase[phase])
                continue
            item = self.entries[phase]
            result.append(
                {
                    "created_temporary_bytes": item.created,
                    "deleted_partial_bytes": item.deleted_partial,
                    "maximum_live_owned_temporary_bytes": item.maximum_live,
                    "permanent_intermediate_bundle_bytes": item.bundle,
                    "phase": phase,
                    "research_evidence_archive_bytes": item.evidence_archive,
                }
            )
        return result


class InstrumentMeter:
    def __init__(
        self,
        start_cpu: int,
        start_wall: int,
        byte_ledger: ByteLedger,
        outer_argv: Sequence[str],
    ) -> None:
        self.start_cpu = start_cpu
        self.start_wall = start_wall
        now_wall = time.monotonic_ns()
        self.start_utc = _utc_from_realtime_ns(time.time_ns() - (now_wall - start_wall))
        initial = ResourceSnapshot(start_cpu, start_wall, _snapshot().peak_rss_bytes)
        self.boundary = PhaseBoundary(initial, self.start_utc)
        self.phase = "C_setup"
        self.owner = "C_setup"
        self.last_cpu = start_cpu
        self.phase_start_cpu = start_cpu
        self.phase_start_wall = start_wall
        self.phase_start_utc = self.start_utc
        self.last_completed_unit = -1
        self.receipts: list[dict[str, Any]] = []
        self.producer_attempt_id = 0
        self.attribution = {name: 0 for name in ATTRIBUTION_NAMES}
        self.bytes = byte_ledger
        self.outer_argv = tuple(outer_argv)
        self.argv_sha256 = _sha256(evidence.canonical_body(list(outer_argv)))
        self.logical_run_id = ""
        self.execution_commit = ""
        self.environment_sha256 = ""
        self.binary_sha256 = _current_cpython_identity()[0]
        self.attempt_start_cpu = start_cpu
        self.attempt_start_wall = start_wall

    def configure(self, logical_run_id: str, commit: str, environment_sha256: str) -> None:
        self.logical_run_id = logical_run_id
        self.execution_commit = commit
        self.environment_sha256 = environment_sha256

    def sample(self, owner_override: str | None = None) -> ResourceSnapshot:
        value = _snapshot()
        delta = value.cpu_microseconds - self.last_cpu
        if delta < 0:
            _fail("IMPLEMENTATION_INVALID", "cumulative CPU clock regressed")
        previous, interrupted = _block_sigint_for_critical_section()
        try:
            self.attribution[owner_override or self.owner] += delta
            self.last_cpu = value.cpu_microseconds
        except BaseException:
            _restore_sigint_after_receipt(previous)
            raise
        if _restore_sigint_after_receipt(previous):
            interrupted = True
        if interrupted:
            raise KeyboardInterrupt("instrument sample interrupted at commit edge")
        return value

    def _close(self, value: ResourceSnapshot, reason: str, disposition: str = "NONE") -> None:
        if not self.logical_run_id:
            _fail("IMPLEMENTATION_INVALID", "instrument meter closed before identity binding")
        previous, interrupted = _block_sigint_for_critical_section()
        try:
            end_utc = _utc_now()
            self.receipts.append(
                {
                    "argv_sha256": self.argv_sha256,
                    "attempt_id": self.producer_attempt_id,
                    "binary_sha256": self.binary_sha256,
                    "completed_unit_index": self.last_completed_unit,
                    "cpu_microseconds": value.cpu_microseconds - self.phase_start_cpu,
                    "end_utc": end_utc,
                    "environment_sha256": self.environment_sha256,
                    "execution_commit": self.execution_commit,
                    "exit_reason": reason,
                    "logical_run_id": self.logical_run_id,
                    "peak_rss_bytes": value.peak_rss_bytes,
                    "phase": self.phase,
                    "staging_disposition": disposition,
                    "start_utc": self.phase_start_utc,
                    "wall_nanoseconds": value.wall_nanoseconds - self.phase_start_wall,
                }
            )
            self.boundary = PhaseBoundary(value, end_utc)
        except BaseException:
            _restore_sigint_after_receipt(previous)
            raise
        if _restore_sigint_after_receipt(previous):
            interrupted = True
        if interrupted:
            raise KeyboardInterrupt("instrument receipt interrupted at commit edge")

    def switch(self, phase: str, owner: str) -> None:
        value = self.sample()
        previous, interrupted = _block_sigint_for_critical_section()
        try:
            if phase != self.phase:
                self._close(value, "PHASE_COMPLETE")
                self.phase = phase
                self.phase_start_cpu = value.cpu_microseconds
                self.phase_start_wall = value.wall_nanoseconds
                self.phase_start_utc = self.boundary.utc
                self.bytes.switch(phase)
            self.owner = owner
        except BaseException:
            _restore_sigint_after_receipt(previous)
            raise
        if _restore_sigint_after_receipt(previous):
            interrupted = True
        if interrupted:
            raise KeyboardInterrupt("instrument phase switch interrupted at commit edge")

    def checkpoint(self, unit_index: int) -> ResourceSnapshot:
        previous, interrupted = _block_sigint_for_critical_section()
        try:
            self.last_completed_unit = unit_index
            value = self.sample()
        except BaseException:
            _restore_sigint_after_receipt(previous)
            raise
        if _restore_sigint_after_receipt(previous):
            interrupted = True
        if interrupted:
            raise KeyboardInterrupt("instrument checkpoint interrupted at commit edge")
        return value

    def close_current(self, reason: str, disposition: str = "NONE") -> None:
        value = self.sample()
        self._close(value, reason, disposition)

    def extend_closed_terminal(self, value: ResourceSnapshot) -> None:
        """Extend the just-closed C receipt through its construction tail."""

        if not self.receipts:
            _fail("IMPLEMENTATION_INVALID", "terminal extension lacks a receipt")
        receipt = self.receipts[-1]
        prior = self.boundary.snapshot
        if (
            self.phase not in {"C_setup", "C_core", "C_bundle_io"}
            or receipt["phase"] != self.phase
            or receipt["attempt_id"] != self.producer_attempt_id
            or self.last_cpu != prior.cpu_microseconds
            or value.cpu_microseconds < prior.cpu_microseconds
            or value.wall_nanoseconds < prior.wall_nanoseconds
            or value.peak_rss_bytes < prior.peak_rss_bytes
        ):
            _fail("IMPLEMENTATION_INVALID", "terminal receipt extension is not contiguous")
        cpu_delta = value.cpu_microseconds - prior.cpu_microseconds
        wall_delta = value.wall_nanoseconds - prior.wall_nanoseconds
        if (
            receipt["cpu_microseconds"] + cpu_delta
            != value.cpu_microseconds - self.phase_start_cpu
            or receipt["wall_nanoseconds"] + wall_delta
            != value.wall_nanoseconds - self.phase_start_wall
        ):
            _fail("IMPLEMENTATION_INVALID", "terminal receipt extension does not reconcile")
        self.attribution[self.owner] += cpu_delta
        receipt["cpu_microseconds"] += cpu_delta
        receipt["wall_nanoseconds"] += wall_delta
        receipt["peak_rss_bytes"] = value.peak_rss_bytes
        end_utc = _utc_now()
        receipt["end_utc"] = end_utc
        self.last_cpu = value.cpu_microseconds
        self.boundary = PhaseBoundary(value, end_utc)

    def begin_retry(self) -> None:
        value = self.boundary.snapshot
        self.producer_attempt_id += 1
        if self.producer_attempt_id != 1:
            _fail("IMPLEMENTATION_INVALID", "producer exceeded the one-restart contract")
        self.phase = "C_setup"
        self.owner = "C_setup"
        self.last_cpu = value.cpu_microseconds
        self.phase_start_cpu = value.cpu_microseconds
        self.phase_start_wall = value.wall_nanoseconds
        self.phase_start_utc = self.boundary.utc
        self.last_completed_unit = -1
        self.attempt_start_cpu = value.cpu_microseconds
        self.attempt_start_wall = value.wall_nanoseconds
        self.bytes.switch("C_setup")

class SupervisorHooks:
    def __init__(
        self,
        attempt_id: int,
        attempt_root: Path,
        meter: InstrumentMeter,
        byte_ledger: ByteLedger,
        sealed_cpu: int,
    ) -> None:
        self.attempt_id = attempt_id
        self.attempt_root = attempt_root
        self.meter = meter
        self.bytes = byte_ledger
        self.sealed_cpu = sealed_cpu
        self.last_state: producer.ProducerState | None = None
        self.cap_crossed = False
        self.representation_stop = False
        self.resource_incomplete = False
        self.publication_became_visible = False
        self.child_count = 0
        self.terminal_sigint_mask: set[signal.Signals] | None = None
        self.terminal_sigint_observed = False
        self.bundle_publication_sigint_mask: set[signal.Signals] | None = None
        self.terminal_finalized = False
        self.terminal_receipt_index: int | None = None
        self.terminal_cleanup_complete = False
        self.terminal_closure_valid = True
        self.terminal_disposition = "NONE"
        self.terminal_cleanup_started = False
        self.terminal_tail_observation_attempted = False
        self.terminal_tail_extended = False
        self.terminal_root_extension_attempted = False
        self.terminal_root_extended = False
        self.terminal_known_status: str | None = None

    def switch(self, phase: str, owner: str) -> None:
        self.meter.switch(phase, owner)

    def retain_terminal_sigint_mask(
        self,
        previous: set[signal.Signals],
        interrupted: bool,
    ) -> None:
        if self.terminal_sigint_mask is not None:
            _fail("IMPLEMENTATION_INVALID", "duplicate C terminal SIGINT mask")
        self.terminal_sigint_mask = previous
        self.terminal_sigint_observed = (
            self.terminal_sigint_observed or interrupted
        )
        if _consume_deferred_sigint():
            self.terminal_sigint_observed = True
        if self.terminal_sigint_observed:
            self.resource_incomplete = True

    def begin_terminal_closure(self) -> bool:
        if self.terminal_sigint_mask is None:
            previous, interrupted = _block_sigint_for_critical_section()
            self.terminal_sigint_mask = previous
            self.terminal_sigint_observed = (
                self.terminal_sigint_observed or interrupted
            )
        if _consume_deferred_sigint():
            self.terminal_sigint_observed = True
        if self.terminal_sigint_observed:
            self.resource_incomplete = True
        return self.terminal_sigint_observed

    def observe_terminal_closure(self) -> bool:
        """Fold pending SIGINT into C state without releasing the C mask."""

        if self.terminal_sigint_mask is None:
            _fail("IMPLEMENTATION_INVALID", "C terminal SIGINT mask is absent")
        if _consume_deferred_sigint():
            self.terminal_sigint_observed = True
        if self.terminal_sigint_observed:
            self.resource_incomplete = True
        return self.terminal_sigint_observed

    def release_terminal_closure(self) -> bool:
        """Release C only after the root decision is committed.

        A delivery at the restore edge is immediately reblocked so the caller
        can patch the existing receipt and fail-stop without an async window.
        """

        interrupted = _consume_deferred_sigint()
        if interrupted:
            self.terminal_sigint_observed = True
            self.resource_incomplete = True
        previous = self.terminal_sigint_mask
        if previous is None:
            _fail("IMPLEMENTATION_INVALID", "C terminal SIGINT mask is absent")
        if self.bundle_publication_sigint_mask is not None:
            _fail(
                "IMPLEMENTATION_INVALID",
                "bundle publication SIGINT guard remains active at C release",
            )
        if signal.SIGINT in previous:
            _fail(
                "IMPLEMENTATION_INVALID",
                "C terminal guard did not retain the frozen unblocked entry mask",
            )
        self.terminal_sigint_mask = None
        if _restore_sigint_after_receipt(previous):
            interrupted = True
        if interrupted:
            retained_previous, retained_interrupted = (
                _block_sigint_for_critical_section()
            )
            self.terminal_sigint_mask = retained_previous
            self.terminal_sigint_observed = True
            self.resource_incomplete = True
            if retained_interrupted or _consume_deferred_sigint():
                self.terminal_sigint_observed = True
        else:
            try:
                current = signal.pthread_sigmask(signal.SIG_BLOCK, set())
                current_handler = signal.getsignal(signal.SIGINT)
            except (OSError, RuntimeError, ValueError) as error:
                retained_previous, retained_interrupted = (
                    _block_sigint_for_critical_section()
                )
                self.retain_terminal_sigint_mask(
                    retained_previous,
                    retained_interrupted,
                )
                _fail(
                    "IMPLEMENTATION_INVALID",
                    f"cannot verify post-C SIGINT contract: {error}",
                )
            if (
                signal.SIGINT in current
                or current_handler is not signal.default_int_handler
            ):
                retained_previous, retained_interrupted = (
                    _block_sigint_for_critical_section()
                )
                self.retain_terminal_sigint_mask(
                    retained_previous,
                    retained_interrupted,
                )
                _fail(
                    "IMPLEMENTATION_INVALID",
                    "C release did not restore the frozen unblocked SIGINT contract",
                )
        return interrupted

    def detach_terminal_mask_for_emit(self) -> "_EmitHandoffOwner":
        """Transfer the still-blocked C guard directly to E's first fork."""

        def fail_preserving_terminal_status(candidate: str, detail: str) -> NoReturn:
            self.terminal_closure_valid = False
            merged = _c_failure_status(candidate)
            if self.terminal_known_status in C_FAILURE_STATUSES:
                merged = _status_min(merged, self.terminal_known_status)
            if (
                self.terminal_receipt_index is not None
                and self.terminal_receipt_index == len(self.meter.receipts) - 1
            ):
                receipt = self.meter.receipts[self.terminal_receipt_index]
                existing = str(receipt["exit_reason"])
                if existing in STATUS_ORDER:
                    merged = _status_min(_c_failure_status(existing), merged)
                receipt["exit_reason"] = merged
            _fail(merged, detail)

        if self.terminal_sigint_mask is None:
            fail_preserving_terminal_status(
                "IMPLEMENTATION_INVALID",
                "C terminal SIGINT mask is absent",
            )
        if self.bundle_publication_sigint_mask is not None:
            fail_preserving_terminal_status(
                "IMPLEMENTATION_INVALID",
                "bundle publication SIGINT guard remains active at E handoff",
            )
        try:
            deferred_sigint = _consume_deferred_sigint()
        except BaseException as error:
            fail_preserving_terminal_status(
                error.status
                if isinstance(error, SupervisorFailure)
                else "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID",
                f"cannot consume C-to-E deferred SIGINT: {error}",
            )
        if deferred_sigint:
            self.terminal_sigint_observed = True
            self.resource_incomplete = True
            fail_preserving_terminal_status(
                "ARTIFACT_INVALID"
                if self.publication_became_visible
                else "RESOURCE_INCOMPLETE_NO_DECISION",
                "C-to-E handoff observed a deferred supervisor SIGINT",
            )
        previous = self.terminal_sigint_mask
        if signal.SIGINT in previous:
            fail_preserving_terminal_status(
                "IMPLEMENTATION_INVALID",
                "C-to-E handoff did not retain an unblocked entry mask",
            )
        try:
            current = signal.pthread_sigmask(signal.SIG_BLOCK, set())
            current_handler = signal.getsignal(signal.SIGINT)
        except (OSError, RuntimeError, ValueError) as error:
            fail_preserving_terminal_status(
                "IMPLEMENTATION_INVALID",
                f"cannot verify C-to-E SIGINT handoff: {error}",
            )
        if (
            signal.SIGINT not in current
            or current_handler is not signal.default_int_handler
        ):
            fail_preserving_terminal_status(
                "IMPLEMENTATION_INVALID",
                "C-to-E handoff lacks blocked/default supervisor SIGINT state",
            )
        handoff_owner = _EmitHandoffOwner(previous)
        self.terminal_sigint_mask = None
        return handoff_owner

    def begin_bundle_publication_commit(self) -> bool:
        if self.bundle_publication_sigint_mask is not None:
            _fail("IMPLEMENTATION_INVALID", "duplicate bundle publication guard")
        previous, interrupted = _block_sigint_for_critical_section()
        self.bundle_publication_sigint_mask = previous
        if _consume_deferred_sigint():
            interrupted = True
        if interrupted:
            self.resource_incomplete = True
        return interrupted

    def finish_bundle_publication_commit(self) -> bool:
        if self.bundle_publication_sigint_mask is None:
            _fail("IMPLEMENTATION_INVALID", "bundle publication guard is absent")
        interrupted = _consume_deferred_sigint()
        previous = self.bundle_publication_sigint_mask
        if _restore_sigint_after_receipt(previous):
            interrupted = True
        self.bundle_publication_sigint_mask = None
        if interrupted:
            self.resource_incomplete = True
        return interrupted

    def invoke_native(self, arguments: Sequence[str]) -> None:
        argv = ("/proc/self/fd/197", *arguments)
        stderr_path = self.attempt_root / f"native_stderr_{self.child_count:03d}.log"
        self.child_count += 1
        self.meter.sample()
        process: subprocess.Popen[bytes] | None = None
        result: WaitResult | None = None
        post_reap_mask: set[signal.Signals] | None = None
        launch_mask: set[signal.Signals] | None = None
        supervisor_interrupted = False
        parent_status: str | None = None
        parent_details: list[str] = []

        def record_parent_failure(status: str, detail: str) -> None:
            nonlocal parent_status
            resolved = _c_failure_status(status)
            parent_status = _status_min(parent_status, resolved)
            parent_details.append(detail)
            if resolved == "RESOURCE_INCOMPLETE_NO_DECISION":
                self.resource_incomplete = True

        stderr_file = None
        try:
            stderr_file = stderr_path.open("xb", buffering=0)
            launch_mask, launch_interrupted = _block_sigint_for_critical_section()
            if _consume_deferred_sigint():
                launch_interrupted = True
            if launch_interrupted:
                _restore_sigint_after_receipt(launch_mask)
                raise KeyboardInterrupt("producer native interrupted before launch")
            try:
                process = subprocess.Popen(
                    argv,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_file,
                    env=_child_environment(),
                    pass_fds=(197,),
                    close_fds=True,
                    preexec_fn=_prepare_native_child_sigint,
                )
            finally:
                if _consume_deferred_sigint():
                    launch_interrupted = True
                if _restore_sigint_after_receipt(launch_mask):
                    launch_interrupted = True
            if launch_interrupted:
                raise KeyboardInterrupt("producer native interrupted at launch edge")
            (
                result,
                post_reap_mask,
                terminal_edge_interrupted,
            ) = _wait4_with_deferred_postreap_sigint(process.pid)
            supervisor_interrupted = terminal_edge_interrupted
            process.returncode = result.exit_code
        except BaseException as error:
            recovery_mask, recovery_interrupted = (
                _block_sigint_for_critical_section()
            )
            if _consume_deferred_sigint():
                recovery_interrupted = True
            supervisor_interrupted = (
                supervisor_interrupted or recovery_interrupted
            )
            retained_recovery_mask = (
                launch_mask
                if signal.SIGINT in recovery_mask and launch_mask is not None
                else recovery_mask
            )
            if process is not None and result is None:
                (
                    result,
                    post_reap_mask,
                    terminal_edge_interrupted,
                    kill_error,
                ) = _kill_and_must_reap_while_sigint_blocked(
                    process.pid,
                    retained_recovery_mask,
                    recovery_interrupted,
                )
                supervisor_interrupted = (
                    supervisor_interrupted or terminal_edge_interrupted
                )
                process.returncode = result.exit_code
                if kill_error is not None:
                    record_parent_failure(
                        "IMPLEMENTATION_INVALID",
                        f"producer native termination reported: {kill_error}",
                    )
            elif process is None:
                self.retain_terminal_sigint_mask(
                    retained_recovery_mask,
                    recovery_interrupted,
                )
            elif post_reap_mask is None:
                post_reap_mask = retained_recovery_mask
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                supervisor_interrupted = True
                status = "RESOURCE_INCOMPLETE_NO_DECISION"
            elif isinstance(error, SupervisorFailure):
                status = error.status
            elif isinstance(error, OSError):
                status = "EVIDENCE_INCOMPLETE_NO_DECISION"
            else:
                status = "IMPLEMENTATION_INVALID"
            record_parent_failure(status, f"producer native supervisor failed: {error}")
        finally:
            if stderr_file is not None:
                try:
                    os.fsync(stderr_file.fileno())
                except OSError as error:
                    record_parent_failure(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"producer native stderr fsync failed: {error}",
                    )
                try:
                    stderr_file.close()
                except OSError as error:
                    record_parent_failure(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"producer native stderr close failed: {error}",
                    )

        output_path = Path(arguments[-1])
        try:
            output_metadata = os.stat(output_path, follow_symlinks=False)
        except FileNotFoundError:
            if result is not None and result.exit_code == 0:
                record_parent_failure(
                    "IMPLEMENTATION_INVALID",
                    "successful native child omitted its output",
                )
        except OSError as error:
            record_parent_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"cannot stat producer native output: {error}",
            )
        else:
            try:
                self.bytes.note_created(output_path, output_metadata)
            except SupervisorFailure as error:
                record_parent_failure(error.status, error.detail)

        stderr_metadata: os.stat_result | None = None
        try:
            stderr_metadata = os.stat(stderr_path, follow_symlinks=False)
        except OSError as error:
            record_parent_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"cannot stat producer native stderr: {error}",
            )
        if stderr_metadata is not None:
            try:
                self.bytes.note_created(stderr_path, stderr_metadata)
            except SupervisorFailure as error:
                record_parent_failure(error.status, error.detail)
                stderr_metadata = None
        detail = b""
        try:
            if stderr_metadata is not None:
                detail = _read_regular_file_prefix(
                    stderr_path,
                    4096,
                    "producer native stderr",
                    stderr_metadata,
                )
        except SupervisorFailure as error:
            record_parent_failure(error.status, error.detail)
        finally:
            stream_known, stream_present, stream_cleanup_metadata = (
                _probe_entry_nofollow(
                    stderr_path,
                    "producer native stderr cleanup",
                    record_parent_failure,
                )
            )
            if stream_present:
                if (
                    stream_cleanup_metadata is None
                    or not stat.S_ISREG(stream_cleanup_metadata.st_mode)
                ):
                    record_parent_failure(
                        "ARTIFACT_INVALID",
                        "producer native stderr became non-regular before cleanup",
                    )
                try:
                    stderr_path.unlink()
                    if stderr_path in self.bytes.live:
                        self.bytes.note_deleted(stderr_path)
                except SupervisorFailure as error:
                    record_parent_failure(error.status, error.detail)
                except OSError as error:
                    record_parent_failure(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"cannot clean producer native stderr: {error}",
                    )
            elif not stream_known:
                record_parent_failure(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    "producer native stderr cleanup presence is unknown",
                )

        if post_reap_mask is not None and _consume_deferred_sigint():
            supervisor_interrupted = True
        if supervisor_interrupted:
            record_parent_failure(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "producer native supervisor SIGINT observed after child launch",
            )
        if result is not None and result.exit_code > 0:
            record_parent_failure(
                "IMPLEMENTATION_INVALID",
                f"native child failed {result.exit_code}: {detail!r}",
            )
        terminal_failure = (
            result is None
            or parent_status is not None
            or (result is not None and result.exit_code != 0)
        )
        if post_reap_mask is not None:
            if terminal_failure:
                self.retain_terminal_sigint_mask(
                    post_reap_mask,
                    supervisor_interrupted,
                )
                post_reap_mask = None
            else:
                if _restore_sigint_after_receipt(post_reap_mask):
                    supervisor_interrupted = True
                    previous, _ = (
                        _block_sigint_for_critical_section()
                    )
                    self.retain_terminal_sigint_mask(
                        previous,
                        True,
                    )
                    record_parent_failure(
                        "RESOURCE_INCOMPLETE_NO_DECISION",
                        "producer native supervisor SIGINT observed at restore edge",
                    )
                post_reap_mask = None
        if result is None:
            self.meter.sample()
            _fail(
                parent_status or "IMPLEMENTATION_INVALID",
                "; ".join(parent_details) or "producer native has no wait receipt",
            )
        if result.exit_code < 0 or supervisor_interrupted:
            self.meter.sample("C_interrupted_tail")
            self.meter.owner = "C_interrupted_tail"
        else:
            self.meter.sample()
        if parent_status is not None:
            _fail(parent_status, "; ".join(parent_details))
        if result.exit_code < 0:
            raise ExternalInterruption(
                f"native child killed by signal {-result.exit_code}: {detail!r}"
            )

    def _resource_violation_detail(self, value: ResourceSnapshot) -> str | None:
        attempt_cpu = value.cpu_microseconds - self.meter.attempt_start_cpu
        attempt_wall = value.wall_nanoseconds - self.meter.attempt_start_wall
        if attempt_cpu > PER_ATTEMPT_CPU_LIMIT or attempt_wall > PER_ATTEMPT_WALL_LIMIT:
            return "producer-attempt operational ceiling crossed"
        if value.peak_rss_bytes > RSS_LIMIT:
            return "producer RSS ceiling crossed"
        if (
            self.sealed_cpu
            + value.cpu_microseconds
            - self.meter.start_cpu
            > STUDY_CPU_LIMIT
        ):
            return "metered-study CPU ceiling crossed"
        return None

    def _operational_check(self, value: ResourceSnapshot) -> None:
        detail = self._resource_violation_detail(value)
        if detail is not None:
            self.resource_incomplete = True
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", detail)

    def observe_terminal_resources(self, value: ResourceSnapshot) -> bool:
        """Persist a cap crossing sampled after terminal cleanup/receipt work."""

        if self._resource_violation_detail(value) is not None:
            self.resource_incomplete = True
        return self.resource_incomplete

    def complete_unit(self, unit_index: int, state: producer.ProducerState) -> bool:
        prior_index = (
            self.last_state.last_completed_unit_index
            if self.last_state is not None
            else -1
        )
        if (
            unit_index != prior_index + 1
            or self.meter.last_completed_unit != prior_index
            or state.last_completed_unit_index != unit_index
            or state.completed_unit_count != unit_index + 1
        ):
            _fail("IMPLEMENTATION_INVALID", "producer unit admission is not contiguous")
        value = self.meter.sample()
        self._operational_check(value)
        # The candidate unit becomes an atomic scientific prefix only after
        # the registered operational checks pass.  A crossing therefore
        # leaves both state and the receipt index at the prior complete unit.
        previous, interrupted = _block_sigint_for_critical_section()
        if _consume_deferred_sigint():
            interrupted = True
        if interrupted:
            self.retain_terminal_sigint_mask(previous, True)
            _fail(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "producer unit admission interrupted before prefix commit",
            )
        try:
            self.meter.last_completed_unit = unit_index
            self.last_state = state
            if value.cpu_microseconds - self.meter.start_cpu > PRIMARY_CAP:
                self.cap_crossed = True
            if not state.representation_valid:
                self.representation_stop = True
            should_stop = self.cap_crossed or self.representation_stop
        except BaseException:
            _restore_sigint_after_receipt(previous)
            raise
        if _consume_deferred_sigint():
            interrupted = True
        if interrupted:
            self.retain_terminal_sigint_mask(previous, True)
            _fail(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "producer unit admission interrupted after atomic prefix commit",
            )
        if _restore_sigint_after_receipt(previous):
            interrupted = True
        if interrupted:
            terminal_previous, _ = _block_sigint_for_critical_section()
            self.retain_terminal_sigint_mask(terminal_previous, True)
            _fail(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "producer unit admission interrupted at restore edge",
            )
        return should_stop

    def fail_unpublished_unit(self, status: str, detail: str) -> NoReturn:
        """Close a failed unit at the prior complete prefix, never at its index."""

        resolved_input = _c_failure_status(status)
        self.terminal_known_status = _status_min(
            self.terminal_known_status,
            resolved_input,
        )
        if resolved_input == "RESOURCE_INCOMPLETE_NO_DECISION":
            self.resource_incomplete = True
        try:
            self.begin_terminal_closure()
        except BaseException as error:
            candidate = (
                error.status
                if isinstance(error, SupervisorFailure)
                else "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID"
            )
            candidate = _c_failure_status(candidate)
            _fail(
                _status_min(self.terminal_known_status, candidate),
                f"cannot enter unpublished-unit terminal closure: {error}",
            )
        if status not in C_FAILURE_STATUSES or self.last_state is None:
            _fail(
                _status_min(self.terminal_known_status, "IMPLEMENTATION_INVALID"),
                "invalid unpublished-unit failure",
            )
        prior_index = self.last_state.last_completed_unit_index
        value = self.meter.checkpoint(prior_index)
        resource_error: SupervisorFailure | None = None
        try:
            self._operational_check(value)
        except SupervisorFailure as error:
            resource_error = error
        if value.cpu_microseconds - self.meter.start_cpu > PRIMARY_CAP:
            self.cap_crossed = True
        resolved_status = (
            _status_min(resolved_input, _c_failure_status(resource_error.status))
            if resource_error is not None
            else resolved_input
        )
        raise producer.ProducerFailure(
            resolved_status,
            detail
            if resource_error is None
            else f"{detail}; {resource_error.detail}",
        )

    def fail_completed_unit(
        self,
        status: str,
        detail: str,
        state: producer.ProducerState,
    ) -> NoReturn:
        """Raise a typed failure after its unit prefix is already admitted."""

        resolved_input = _c_failure_status(status)
        self.terminal_known_status = _status_min(
            self.terminal_known_status,
            resolved_input,
        )
        if resolved_input == "RESOURCE_INCOMPLETE_NO_DECISION":
            self.resource_incomplete = True
        try:
            self.begin_terminal_closure()
        except BaseException as error:
            candidate = (
                error.status
                if isinstance(error, SupervisorFailure)
                else "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID"
            )
            candidate = _c_failure_status(candidate)
            _fail(
                _status_min(self.terminal_known_status, candidate),
                f"cannot enter completed-unit terminal closure: {error}",
            )
        if (
            status not in C_FAILURE_STATUSES
            or self.last_state is None
            or state is not self.last_state
            or state.last_completed_unit_index != self.meter.last_completed_unit
        ):
            _fail(
                _status_min(self.terminal_known_status, "IMPLEMENTATION_INVALID"),
                "invalid completed-unit failure",
            )
        raise producer.ProducerFailure(resolved_input, detail)

    def capture_producer_terminal(self, error: BaseException) -> None:
        """Seal every producer-body failure before it crosses into the runner."""

        original_status = getattr(error, "status", None)
        if isinstance(error, ExternalInterruption):
            # This is the deliberate raw-signal transport event.  Its frozen
            # receipt reason is EXTERNAL_INTERRUPTION, outside STATUS_ORDER,
            # and must remain eligible for the one exact retry.
            original_status = None
        elif original_status not in C_FAILURE_STATUSES:
            original_status = (
                "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID"
            )
        if original_status in C_FAILURE_STATUSES:
            self.terminal_known_status = _status_min(
                self.terminal_known_status,
                original_status,
            )
        if original_status == "RESOURCE_INCOMPLETE_NO_DECISION":
            self.resource_incomplete = True
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            self.terminal_sigint_observed = True

        def fail_preserving_original(candidate: str, detail: str) -> NoReturn:
            self.terminal_closure_valid = False
            resolved = _c_failure_status(candidate)
            if resolved == "RESOURCE_INCOMPLETE_NO_DECISION":
                self.resource_incomplete = True
            _fail(_status_min(self.terminal_known_status, resolved), detail)

        if (
            self.terminal_sigint_mask is None
            and self.bundle_publication_sigint_mask is not None
        ):
            try:
                current = signal.pthread_sigmask(signal.SIG_BLOCK, set())
            except (OSError, RuntimeError, ValueError) as mask_error:
                fail_preserving_original(
                    "IMPLEMENTATION_INVALID",
                    f"cannot transfer bundle SIGINT guard: {mask_error}",
                )
            if signal.SIGINT in current:
                self.terminal_sigint_mask = self.bundle_publication_sigint_mask
                self.bundle_publication_sigint_mask = None
                try:
                    deferred_sigint = _consume_deferred_sigint()
                except BaseException as mask_error:
                    fail_preserving_original(
                        mask_error.status
                        if isinstance(mask_error, SupervisorFailure)
                        else "RESOURCE_INCOMPLETE_NO_DECISION"
                        if isinstance(mask_error, (KeyboardInterrupt, SystemExit))
                        else "IMPLEMENTATION_INVALID",
                        f"cannot consume transferred bundle SIGINT: {mask_error}",
                    )
                if deferred_sigint:
                    self.terminal_sigint_observed = True
            else:
                try:
                    self.begin_terminal_closure()
                except BaseException as mask_error:
                    fail_preserving_original(
                        mask_error.status
                        if isinstance(mask_error, SupervisorFailure)
                        else "RESOURCE_INCOMPLETE_NO_DECISION"
                        if isinstance(mask_error, (KeyboardInterrupt, SystemExit))
                        else "IMPLEMENTATION_INVALID",
                        f"cannot replace stale bundle SIGINT guard: {mask_error}",
                    )
                self.bundle_publication_sigint_mask = None
        else:
            try:
                self.begin_terminal_closure()
            except BaseException as mask_error:
                fail_preserving_original(
                    mask_error.status
                    if isinstance(mask_error, SupervisorFailure)
                    else "RESOURCE_INCOMPLETE_NO_DECISION"
                    if isinstance(mask_error, (KeyboardInterrupt, SystemExit))
                    else "IMPLEMENTATION_INVALID",
                    f"cannot enter captured producer terminal closure: {mask_error}",
                )

    def note_created_temporary(self, path: Path) -> None:
        self.bytes.note_created(path)

    def note_deleted_temporary(self, path: Path) -> None:
        self.bytes.note_deleted(path)

    def reserve_permanent_bundle(self, byte_count: int) -> None:
        self.bytes.reserve_bundle(byte_count)

    def mark_bundle_publication_visible(self) -> None:
        """Set the irreversible publication marker without validation."""

        self.publication_became_visible = True

    def commit_permanent_bundle(self, byte_count: int) -> None:
        self.bytes.commit_bundle(byte_count)

    def cancel_permanent_bundle(self, byte_count: int) -> None:
        self.bytes.cancel_bundle(byte_count)

    def check_operational(self) -> None:
        self._operational_check(self.meter.sample())


class EmitHooks:
    def __init__(
        self,
        byte_ledger: ByteLedger,
        start: ResourceSnapshot,
        sealed_cpu: int,
        prior_phase_cpu: int,
        prior_phase_wall: int,
    ) -> None:
        self.bytes = byte_ledger
        self.start = start
        self.sealed_cpu = sealed_cpu
        self.prior_phase_cpu = prior_phase_cpu
        self.prior_phase_wall = prior_phase_wall

    def note_created_temporary(self, path: Path) -> None:
        self.bytes.note_created(path)

    def note_research_evidence(self, byte_count: int) -> None:
        self.bytes.publish_evidence(byte_count)

    def check_operational(self) -> None:
        value = _snapshot()
        if (
            self.prior_phase_cpu
            + value.cpu_microseconds
            - self.start.cpu_microseconds
            > PER_PHASE_CPU_LIMIT
            or self.prior_phase_wall
            + value.wall_nanoseconds
            - self.start.wall_nanoseconds
            > PER_PHASE_WALL_LIMIT
            or self.sealed_cpu + value.cpu_microseconds - self.start.cpu_microseconds
            > STUDY_CPU_LIMIT
            or value.peak_rss_bytes > RSS_LIMIT
        ):
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", "E_emit operational ceiling crossed")


def _status_min(current: str | None, candidate: str) -> str:
    if current is None:
        return candidate
    return min((current, candidate), key=STATUS_ORDER.index)


def _c_failure_status(candidate: object) -> str:
    """Map any out-of-phase C failure vocabulary to Implementation."""

    return (
        candidate
        if isinstance(candidate, str) and candidate in C_FAILURE_STATUSES
        else "IMPLEMENTATION_INVALID"
    )


def _fail_preserving_prior_status(
    prior_status: str | None, candidate_status: str, detail: str
) -> NoReturn:
    """Raise the highest-precedence known status without rewriting its cause."""

    _fail(_status_min(prior_status, candidate_status), detail)


def _run_preserving_prior_status(prior_status: str | None, operation: Any) -> Any:
    """Keep a terminal producer fact sticky across a downstream operation."""

    try:
        return operation()
    except (SupervisorFailure, evidence.EvidenceFailure) as error:
        resolved = _status_min(prior_status, error.status)
        if resolved == error.status:
            raise
        raise SupervisorFailure(
            resolved,
            f"{error.detail}; prior terminal status {prior_status} retains precedence",
        ) from error


def _sorted_receipts(receipts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rank = {phase: index for index, phase in enumerate(PHASE_ORDER)}
    return sorted((dict(item) for item in receipts), key=lambda item: (rank[item["phase"]], item["attempt_id"]))


def _chronological_receipts(receipts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rank = {phase: index for index, phase in enumerate(PHASE_ORDER)}
    return sorted(
        (dict(item) for item in receipts),
        key=lambda item: (item["start_utc"], rank[item["phase"]], item["attempt_id"]),
    )


def _sealed_phase_identities(receipts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for phase in PHASE_ORDER:
        selected = [item for item in receipts if item["phase"] == phase]
        if not selected:
            continue
        identity_keys = (
            "argv_sha256",
            "binary_sha256",
            "environment_sha256",
            "execution_commit",
            "logical_run_id",
        )
        for key in identity_keys:
            if len({item[key] for item in selected}) != 1:
                _fail("IMPLEMENTATION_INVALID", f"retry changed {phase} {key}")
        result.append(
            {
                "argv_sha256": selected[0]["argv_sha256"],
                "attempt_count": len(selected),
                "binary_sha256": selected[0]["binary_sha256"],
                "environment_sha256": selected[0]["environment_sha256"],
                "execution_commit": selected[0]["execution_commit"],
                "logical_run_id": selected[0]["logical_run_id"],
                "phase": phase,
            }
        )
    return result


def _phase_receipt(
    *,
    phase: str,
    attempt_id: int,
    argv: Sequence[str],
    binary_sha256: str,
    start: ResourceSnapshot,
    start_utc: str,
    end: ResourceSnapshot,
    end_utc: str,
    child_usage: WaitResult,
    completed_unit: int,
    reason: str,
    disposition: str,
    logical_run_id: str,
    commit: str,
    environment_sha: str,
) -> dict[str, Any]:
    cpu_microseconds = end.cpu_microseconds - start.cpu_microseconds
    wall_nanoseconds = end.wall_nanoseconds - start.wall_nanoseconds
    if cpu_microseconds < 0 or wall_nanoseconds < 0:
        _fail("IMPLEMENTATION_INVALID", f"{phase} resource snapshot moved backwards")
    return {
        "argv_sha256": _sha256(evidence.canonical_body(list(argv))),
        "attempt_id": attempt_id,
        "binary_sha256": binary_sha256,
        "completed_unit_index": completed_unit,
        "cpu_microseconds": cpu_microseconds,
        "end_utc": end_utc,
        "environment_sha256": environment_sha,
        "execution_commit": commit,
        "exit_reason": reason,
        "logical_run_id": logical_run_id,
        "peak_rss_bytes": max(child_usage.peak_rss_bytes, end.peak_rss_bytes),
        "phase": phase,
        "staging_disposition": disposition,
        "start_utc": start_utc,
        "wall_nanoseconds": wall_nanoseconds,
    }


def _reserve_fixed_descriptor(source: int, target: int) -> None:
    if source != target:
        os.dup2(source, target, inheritable=True)
        os.close(source)
    else:
        os.set_inheritable(target, True)


def _block_sigint_before_external_exec() -> None:
    """Keep wrapper SIGINT pending until reviewed child entry code owns it."""

    signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})


def _prepare_native_child_sigint() -> None:
    """Give the exec'd C++ child raw, unblocked SIGINT semantics."""

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT})


def _block_sigint_for_critical_section() -> tuple[set[signal.Signals], bool]:
    """Enter a short launch or receipt-critical section without async tearing."""

    interrupted = False
    while True:
        try:
            previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
            if interrupted:
                # The frozen entry contract says SIGINT was unblocked.  If a
                # prior atomic block completed just as KeyboardInterrupt was
                # delivered, the retry reports the newly blocked mask; remove
                # that one bit to reconstruct the true entry mask.
                previous.discard(signal.SIGINT)
            return previous, interrupted
        except KeyboardInterrupt:
            interrupted = True
        except (OSError, RuntimeError, ValueError) as error:
            _fail(
                "IMPLEMENTATION_INVALID",
                f"cannot defer terminal SIGINT while constructing a receipt: {error}",
            )


def _wait4_with_deferred_postreap_sigint(
    pid: int,
) -> tuple[WaitResult, set[signal.Signals], bool]:
    """Observe terminal state without reaping, defer SIGINT, then reap exactly once."""

    observed = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
    if observed is None or observed.si_pid != pid:
        _fail("IMPLEMENTATION_INVALID", "waitid returned a foreign child identity")
    previous, interrupted = _block_sigint_for_critical_section()
    # A wait4 failure propagates with SIGINT still blocked so the caller can
    # enter its close/kill/must-reap recovery without a second-signal window.
    usage = _wait4_integer(pid)
    return usage, previous, interrupted


def _kill_and_must_reap_while_sigint_blocked(
    pid: int,
    previous: set[signal.Signals],
    interrupted: bool,
    before_kill_while_blocked: Any | None = None,
) -> tuple[WaitResult, set[signal.Signals], bool, str | None]:
    """Close, kill, and must-reap after the caller has already blocked SIGINT."""

    if _consume_deferred_sigint():
        interrupted = True
    recovery_error: str | None = None
    if before_kill_while_blocked is not None:
        try:
            before_kill_while_blocked()
        except BaseException as error:
            # Never abandon a launched child because recovery cleanup itself
            # failed.  Preserve the error, then kill and must-reap first.
            recovery_error = f"pre-kill recovery cleanup failed: {error}"
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        kill_error = None
    except OSError as error:
        kill_error = str(error)
    else:
        kill_error = None
    while True:
        try:
            usage = _wait4_integer(pid)
            break
        except InterruptedError:
            continue
        except ChildProcessError as error:
            _fail(
                "IMPLEMENTATION_INVALID",
                f"launched child {pid} became unaccountably non-waitable: {error}",
            )
        except OSError as error:
            if error.errno == errno.EINTR:
                continue
            _fail(
                "IMPLEMENTATION_INVALID",
                f"cannot reap launched child {pid}: {error}",
            )
    if _consume_deferred_sigint():
        interrupted = True
    combined_error = "; ".join(
        item for item in (recovery_error, kill_error) if item is not None
    ) or None
    return usage, previous, interrupted, combined_error


def _consume_deferred_sigint() -> bool:
    """Consume one pending SIGINT while it is blocked from asynchronous delivery."""

    try:
        if signal.SIGINT not in signal.sigpending():
            return False
        observed = signal.sigwait({signal.SIGINT})
    except (OSError, RuntimeError, ValueError) as error:
        _fail(
            "IMPLEMENTATION_INVALID",
            f"cannot inspect deferred terminal SIGINT: {error}",
        )
    if observed != signal.SIGINT:
        _fail("IMPLEMENTATION_INVALID", "sigwait consumed a foreign signal")
    return True


def _restore_sigint_after_receipt(previous: set[signal.Signals]) -> bool:
    """Restore the pre-attempt mask and report a delivery at the restore edge."""

    interrupted = False
    while True:
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous)
            return interrupted
        except KeyboardInterrupt:
            interrupted = True
        except (OSError, RuntimeError, ValueError) as error:
            _fail(
                "IMPLEMENTATION_INVALID",
                f"cannot restore SIGINT mask after receipt construction: {error}",
            )


def _require_control_descriptors_free() -> None:
    for descriptor in (197, 198, 199):
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        raise PreconditionFailure(f"frozen control descriptor {descriptor} is already open")


def _require_supervisor_sigint_contract() -> None:
    """Freeze the unblocked CPython SIGINT semantics used by phase boundaries."""

    try:
        current_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        current_handler = signal.getsignal(signal.SIGINT)
    except (OSError, RuntimeError, ValueError) as error:
        raise PreconditionFailure(f"cannot inspect supervisor SIGINT state: {error}") from error
    if signal.SIGINT in current_mask:
        raise PreconditionFailure("supervisor SIGINT is blocked at prelaunch")
    if current_handler is not signal.default_int_handler:
        raise PreconditionFailure("supervisor SIGINT handler is not CPython default")


def _read_bounded_regular_file(
    path: Path,
    maximum_bytes: int,
    description: str,
    oversize_status: str,
    expected_metadata: os.stat_result | None = None,
) -> bytes:
    descriptor: int | None = None
    identity_descriptor: int | None = None
    try:
        identity_descriptor = os.open(
            path,
            os.O_PATH
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        before = os.fstat(identity_descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail("ARTIFACT_INVALID", f"{description} is not a regular file")
        if before.st_size > maximum_bytes:
            _fail(oversize_status, f"{description} exceeds its frozen byte ceiling")
        descriptor = os.open(
            f"/proc/self/fd/{identity_descriptor}",
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0),
        )
        require_opened = os.fstat(descriptor)
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if expected_metadata is not None and any(
            getattr(expected_metadata, field) != getattr(before, field)
            for field in stable_fields
        ):
            _fail(
                "ARTIFACT_INVALID",
                f"{description} differs from its byte-ledger identity",
            )
        if any(
            getattr(before, field) != getattr(require_opened, field)
            for field in stable_fields
        ):
            _fail("ARTIFACT_INVALID", f"{description} identity reopen mismatch")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(
                descriptor, min(1 << 20, before.st_size - len(payload))
            )
            if not chunk:
                _fail("EVIDENCE_INCOMPLETE_NO_DECISION", f"{description} ended early")
            payload.extend(chunk)
        if os.read(descriptor, 1):
            _fail("ARTIFACT_INVALID", f"{description} grew during bounded read")
        after = os.fstat(descriptor)
        named = os.stat(path, follow_symlinks=False)
        identity_after = os.fstat(identity_descriptor)
        if any(
            getattr(before, field) != getattr(after, field)
            or getattr(before, field) != getattr(identity_after, field)
            or getattr(before, field) != getattr(named, field)
            for field in stable_fields
        ):
            _fail("ARTIFACT_INVALID", f"{description} changed during bounded read")
        return bytes(payload)
    except SupervisorFailure:
        raise
    except OSError as error:
        _fail(
            "EVIDENCE_INCOMPLETE_NO_DECISION",
            f"cannot read bounded {description}: {error}",
        )
    finally:
        active_error = sys.exc_info()[0] is not None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as error:
                if not active_error:
                    _fail(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"cannot close bounded {description}: {error}",
                    )
        if identity_descriptor is not None:
            try:
                os.close(identity_descriptor)
            except OSError as error:
                if not active_error:
                    _fail(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"cannot close bounded {description} identity: {error}",
                    )


def _read_regular_file_prefix(
    path: Path,
    prefix_bytes: int,
    description: str,
    expected_metadata: os.stat_result | None = None,
) -> bytes:
    """Read only a diagnostic prefix while proving a stable regular file."""

    descriptor: int | None = None
    identity_descriptor: int | None = None
    try:
        identity_descriptor = os.open(
            path,
            os.O_PATH
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        before = os.fstat(identity_descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail("ARTIFACT_INVALID", f"{description} is not a regular file")
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if expected_metadata is not None and any(
            getattr(expected_metadata, field) != getattr(before, field)
            for field in stable_fields
        ):
            _fail(
                "ARTIFACT_INVALID",
                f"{description} differs from its byte-ledger identity",
            )
        descriptor = os.open(
            f"/proc/self/fd/{identity_descriptor}",
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0),
        )
        reopened = os.fstat(descriptor)
        expected = min(before.st_size, prefix_bytes)
        payload = bytearray()
        while len(payload) < expected:
            chunk = os.read(descriptor, expected - len(payload))
            if not chunk:
                _fail(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    f"{description} ended before its diagnostic prefix",
                )
            payload.extend(chunk)
        after = os.fstat(descriptor)
        named = os.stat(path, follow_symlinks=False)
        identity_after = os.fstat(identity_descriptor)
        if any(
            getattr(before, field) != getattr(reopened, field)
            or getattr(before, field) != getattr(identity_after, field)
            or getattr(before, field) != getattr(after, field)
            or getattr(before, field) != getattr(named, field)
            for field in stable_fields
        ):
            _fail("ARTIFACT_INVALID", f"{description} changed during prefix read")
        return bytes(payload)
    except SupervisorFailure:
        raise
    except OSError as error:
        _fail(
            "EVIDENCE_INCOMPLETE_NO_DECISION",
            f"cannot read {description} prefix: {error}",
        )
    finally:
        active_error = sys.exc_info()[0] is not None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as error:
                if not active_error:
                    _fail(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"cannot close {description} prefix: {error}",
                    )
        if identity_descriptor is not None:
            try:
                os.close(identity_descriptor)
            except OSError as error:
                if not active_error:
                    _fail(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"cannot close {description} prefix identity: {error}",
                    )


def _probe_entry_nofollow(
    path: Path,
    description: str,
    record_failure: Any,
) -> tuple[bool, bool, os.stat_result | None]:
    """Return (known, present, metadata) without hiding a broken symlink."""

    try:
        return True, True, os.lstat(path)
    except FileNotFoundError:
        return True, False, None
    except OSError as error:
        record_failure(
            "EVIDENCE_INCOMPLETE_NO_DECISION",
            f"{description} no-follow presence check failed: {error}",
        )
        return False, False, None


def _cleanup_owned_staging(
    path: Path,
    phase: str,
    byte_ledger: ByteLedger,
    record_failure: Any,
) -> bool:
    """Best-effort account and remove a terminated child's staging entry."""

    known, present, metadata = _probe_entry_nofollow(
        path,
        f"{phase} staging",
        record_failure,
    )
    if not known:
        return False
    if not present:
        return True
    assert metadata is not None
    byte_ledger.switch(phase)
    if stat.S_ISDIR(metadata.st_mode):
        try:
            byte_ledger.admit_tree(path)
        except SupervisorFailure as error:
            record_failure(error.status, error.detail)
        except OSError as error:
            record_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"{phase} staging inventory failed: {error}",
            )
        try:
            byte_ledger.discard_tree(path)
        except SupervisorFailure as error:
            record_failure(error.status, error.detail)
        except OSError as error:
            record_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"{phase} staging ledger cleanup failed: {error}",
            )
        try:
            shutil.rmtree(path)
        except OSError as error:
            record_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"{phase} staging physical cleanup failed: {error}",
            )
    else:
        record_failure(
            "ARTIFACT_INVALID",
            f"{phase} staging root is not a real directory",
        )
        if stat.S_ISREG(metadata.st_mode):
            try:
                byte_ledger.note_created(path, metadata)
            except SupervisorFailure as error:
                record_failure(error.status, error.detail)
        try:
            path.unlink()
        except OSError as error:
            record_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"{phase} non-directory staging cleanup failed: {error}",
            )
        else:
            if path in byte_ledger.live:
                try:
                    byte_ledger.note_discarded_file(path)
                except SupervisorFailure as error:
                    record_failure(error.status, error.detail)

    final_known, final_present, _ = _probe_entry_nofollow(
        path,
        f"{phase} post-cleanup staging",
        record_failure,
    )
    if final_known and not final_present:
        return True
    if final_known:
        record_failure(
            "EVIDENCE_INCOMPLETE_NO_DECISION",
            f"{phase} staging remains after cleanup",
        )
    return False


def _external_wrapper(
    *,
    phase: str,
    argv: Sequence[str],
    control_factory: Any,
    artifact_root: Path,
    published_directory: str,
    published_file: str,
    completed_unit: int,
    logical_run_id: str,
    commit: str,
    environment_sha: str,
    bytes_: ByteLedger,
    initial_boundary: PhaseBoundary,
    prior_study_cpu_microseconds: int,
    response_pipe: bool = False,
    allow_published_resource_return: bool = False,
    success_validator: Any | None = None,
    post_cleanup_validator: Any | None = None,
) -> tuple[
    list[dict[str, Any]],
    bytes,
    bytes,
    Mapping[str, Any],
    Mapping[str, Any],
    PhaseBoundary,
]:
    """Launch, reap, classify, and receipt one fixed-argv external phase."""

    receipts: list[dict[str, Any]] = []
    fixed_argv = tuple(argv)
    boundary = initial_boundary
    for attempt in range(2):
        start = boundary.snapshot
        start_utc = boundary.utc
        receipt_binary_sha256 = _current_cpython_identity()[0]
        control_payload = evidence.canonical_document(
            control_factory(start_utc, start.wall_nanoseconds, tuple(receipts))
        )
        work = artifact_root / f".{phase.lower()}.staging"
        work.mkdir()
        stdout_path = work / "stdout"
        stderr_path = work / "stderr"
        request_read, request_write = os.pipe()
        _reserve_fixed_descriptor(request_read, 198)
        response_read = response_write = None
        if response_pipe:
            response_read, response_write = os.pipe()
            _reserve_fixed_descriptor(response_write, 199)
            response_write = 199
        pass_descriptors = (198, 199) if response_pipe else (198,)

        parent_status: str | None = None
        parent_details: list[str] = []
        nonresource_validation_failure = False
        post_cleanup_valid = post_cleanup_validator is None

        def record_parent_failure(status: str, detail: str) -> None:
            nonlocal parent_status, nonresource_validation_failure
            resolved = status if status in STATUS_ORDER else "IMPLEMENTATION_INVALID"
            parent_status = _status_min(parent_status, resolved)
            parent_details.append(detail)
            if resolved != "RESOURCE_INCOMPLETE_NO_DECISION":
                nonresource_validation_failure = True

        process: subprocess.Popen[bytes] | None = None
        usage: WaitResult | None = None
        post_reap_mask: set[signal.Signals] | None = None
        launch_mask: set[signal.Signals] | None = None
        supervisor_interrupted = False
        resource_return_eligible = False

        def close_recovery_controls() -> None:
            nonlocal response_read
            # Recovery invokes this callback only after SIGINT is blocked.
            # Define it before launch so the exception path can enter the
            # block/close/kill/must-reap helper as its first child action.
            for descriptor in (
                198,
                199 if response_pipe else -1,
                request_write,
            ):
                if descriptor < 0:
                    continue
                try:
                    os.close(descriptor)
                except OSError as error:
                    if error.errno != errno.EBADF:
                        record_parent_failure(
                            "EVIDENCE_INCOMPLETE_NO_DECISION",
                            f"{phase} recovery control close failed: {error}",
                        )
            if response_read is not None:
                try:
                    os.close(response_read)
                except OSError as error:
                    if error.errno != errno.EBADF:
                        record_parent_failure(
                            "EVIDENCE_INCOMPLETE_NO_DECISION",
                            f"{phase} recovery response close failed: {error}",
                        )
                response_read = None

        try:
            with stdout_path.open("xb", buffering=0) as stdout_file, stderr_path.open(
                "xb", buffering=0
            ) as stderr_file:
                launch_mask, launch_interrupted = (
                    _block_sigint_for_critical_section()
                )
                if _consume_deferred_sigint():
                    launch_interrupted = True
                if launch_interrupted:
                    _restore_sigint_after_receipt(launch_mask)
                    raise KeyboardInterrupt(
                        f"{phase} supervisor interrupted before child launch"
                    )
                try:
                    process = subprocess.Popen(
                        fixed_argv,
                        stdin=subprocess.DEVNULL,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        env=_child_environment(),
                        pass_fds=pass_descriptors,
                        close_fds=True,
                        preexec_fn=_block_sigint_before_external_exec,
                    )
                finally:
                    if _consume_deferred_sigint():
                        launch_interrupted = True
                    if _restore_sigint_after_receipt(launch_mask):
                        launch_interrupted = True
                if launch_interrupted:
                    raise KeyboardInterrupt(
                        f"{phase} supervisor interrupted at child launch"
                    )
                os.close(198)
                if response_pipe:
                    os.close(199)
                try:
                    offset = 0
                    while offset < len(control_payload):
                        written = os.write(request_write, control_payload[offset:])
                        if written <= 0:
                            record_parent_failure(
                                "EVIDENCE_INCOMPLETE_NO_DECISION",
                                f"{phase} control short write",
                            )
                            break
                        offset += written
                except OSError as error:
                    record_parent_failure(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"{phase} control write failed: {error}",
                    )
                finally:
                    try:
                        os.close(request_write)
                    except OSError as error:
                        record_parent_failure(
                            "EVIDENCE_INCOMPLETE_NO_DECISION",
                            f"{phase} control descriptor close failed: {error}",
                        )
                (
                    usage,
                    post_reap_mask,
                    terminal_edge_interrupted,
                ) = _wait4_with_deferred_postreap_sigint(process.pid)
                supervisor_interrupted = terminal_edge_interrupted
                process.returncode = usage.exit_code
                for stream_name, stream in (("stdout", stdout_file), ("stderr", stderr_file)):
                    try:
                        os.fsync(stream.fileno())
                    except OSError as error:
                        record_parent_failure(
                            "EVIDENCE_INCOMPLETE_NO_DECISION",
                            f"{phase} {stream_name} fsync failed: {error}",
                        )
        except BaseException as parent_error:
            recovery_mask, recovery_interrupted = (
                _block_sigint_for_critical_section()
            )
            if _consume_deferred_sigint():
                recovery_interrupted = True
            supervisor_interrupted = (
                supervisor_interrupted or recovery_interrupted
            )
            retained_recovery_mask = (
                launch_mask
                if signal.SIGINT in recovery_mask and launch_mask is not None
                else recovery_mask
            )
            if process is None:
                close_recovery_controls()
                _fail(
                    "RESOURCE_INCOMPLETE_NO_DECISION"
                    if recovery_interrupted
                    or isinstance(parent_error, (KeyboardInterrupt, SystemExit))
                    else "IMPLEMENTATION_INVALID",
                    f"{phase} child could not be launched: {parent_error}",
                )
            if usage is None:
                (
                    usage,
                    post_reap_mask,
                    terminal_edge_interrupted,
                    kill_error,
                ) = _kill_and_must_reap_while_sigint_blocked(
                    process.pid,
                    retained_recovery_mask,
                    recovery_interrupted,
                    close_recovery_controls,
                )
                supervisor_interrupted = (
                    supervisor_interrupted or terminal_edge_interrupted
                )
                process.returncode = usage.exit_code
                if kill_error is not None:
                    record_parent_failure(
                        "IMPLEMENTATION_INVALID",
                        f"{phase} child termination reported: {kill_error}",
                    )
            else:
                if post_reap_mask is None:
                    post_reap_mask = retained_recovery_mask
                close_recovery_controls()
            record_parent_failure(
                "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(parent_error, (KeyboardInterrupt, SystemExit))
                else parent_error.status
                if isinstance(parent_error, SupervisorFailure)
                else "IMPLEMENTATION_INVALID",
                f"{phase} parent failed after launch: {parent_error}",
            )
            if isinstance(parent_error, (KeyboardInterrupt, SystemExit)):
                supervisor_interrupted = True

        if usage is None or post_reap_mask is None:
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", f"{phase} child has no wait receipt")

        response = bytearray()
        if response_read is not None:
            try:
                while True:
                    chunk = os.read(response_read, 1 << 20)
                    if not chunk:
                        break
                    response.extend(chunk)
                    if len(response) > 1 << 20:
                        record_parent_failure(
                            "EVIDENCE_INCOMPLETE_NO_DECISION",
                            f"{phase} response exceeds 1 MiB",
                        )
                        break
            except OSError as error:
                record_parent_failure(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    f"{phase} response read failed: {error}",
                )
            finally:
                try:
                    os.close(response_read)
                except OSError as error:
                    record_parent_failure(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"{phase} response descriptor close failed: {error}",
                    )

        bytes_.switch(phase)
        stream_metadata: dict[str, os.stat_result] = {}
        for stream_name, path in (("stdout", stdout_path), ("stderr", stderr_path)):
            try:
                metadata = os.stat(path, follow_symlinks=False)
                bytes_.note_created(path, metadata)
                stream_metadata[stream_name] = metadata
            except SupervisorFailure as error:
                record_parent_failure(error.status, error.detail)
            except OSError as error:
                record_parent_failure(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    f"{phase} {stream_name} identity stat failed: {error}",
                )

        stdout_payload = b""
        stderr_payload = b""
        for stream_name, path in (("stdout", stdout_path), ("stderr", stderr_path)):
            if stream_name not in stream_metadata:
                continue
            try:
                payload = _read_bounded_regular_file(
                    path,
                    1 << 20,
                    f"{phase} {stream_name}",
                    "IMPLEMENTATION_INVALID",
                    stream_metadata.get(stream_name),
                )
                if stream_name == "stdout":
                    stdout_payload = payload
                else:
                    stderr_payload = payload
            except SupervisorFailure as error:
                record_parent_failure(error.status, error.detail)
        if usage.exit_code == 0 and stderr_payload:
            record_parent_failure(
                "IMPLEMENTATION_INVALID",
                f"{phase} successful child emitted stderr",
            )
        if usage.exit_code == 0 and response_pipe and stdout_payload:
            record_parent_failure(
                "IMPLEMENTATION_INVALID",
                f"{phase} successful identity-pipe child emitted stdout",
            )

        target = artifact_root / published_directory
        staging = artifact_root / f"{published_directory}.staging"
        target_known, target_present, target_metadata = _probe_entry_nofollow(
            target,
            f"{phase} publication target",
            record_parent_failure,
        )
        publication_visible = target_known and target_present
        publication_target_real = (
            publication_visible
            and target_metadata is not None
            and stat.S_ISDIR(target_metadata.st_mode)
        )
        if publication_visible and not publication_target_real:
            record_parent_failure(
                "ARTIFACT_INVALID",
                f"{phase} publication target is not a real directory",
            )
        output_payload = b""
        output_object: Mapping[str, Any] = {}
        output_valid = False
        if usage.exit_code == 0 and publication_target_real:
            output_path = artifact_root / published_file
            try:
                output_metadata = os.stat(output_path, follow_symlinks=False)
            except FileNotFoundError:
                record_parent_failure(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    f"{phase} omitted published output",
                )
            except OSError as error:
                record_parent_failure(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    f"{phase} published output stat failed: {error}",
                )
            else:
                if not stat.S_ISREG(output_metadata.st_mode):
                    record_parent_failure(
                        "ARTIFACT_INVALID",
                        f"{phase} published output is not a regular file",
                    )
                else:
                    try:
                        bytes_.atomic_external_file(phase, output_metadata.st_size)
                    except SupervisorFailure as error:
                        record_parent_failure(error.status, error.detail)
                        if error.status == "RESOURCE_INCOMPLETE_NO_DECISION":
                            resource_return_eligible = True
                    try:
                        output_payload = _read_bounded_regular_file(
                            output_path,
                            EVIDENCE_LIMIT,
                            f"{phase} published output",
                            "RESOURCE_INCOMPLETE_NO_DECISION",
                            output_metadata,
                        )
                        parsed_output = _parse_json_document(
                            output_payload, f"{phase} published output", True
                        )
                        if not isinstance(parsed_output, dict):
                            _fail(
                                "ARTIFACT_INVALID",
                                f"{phase} published output is not an object",
                            )
                        output_object = parsed_output
                        output_valid = True
                    except SupervisorFailure as error:
                        record_parent_failure(error.status, error.detail)
        if usage.exit_code == 0 and not publication_visible:
            record_parent_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"{phase} exited successfully without a visible target",
            )

        response_payload = bytes(response) if response_pipe else stdout_payload
        response_object: Mapping[str, Any] = {}
        response_valid = False
        if usage.exit_code == 0:
            if not response_payload:
                record_parent_failure(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    f"{phase} omitted its required control response",
                )
            else:
                try:
                    parsed_response = _parse_json_document(
                        response_payload, f"{phase} control response", True
                    )
                    if not isinstance(parsed_response, dict):
                        record_parent_failure(
                            "EVIDENCE_INCOMPLETE_NO_DECISION",
                            f"{phase} response transport is not an object",
                        )
                    else:
                        response_object = parsed_response
                        response_valid = True
                except SupervisorFailure as error:
                    record_parent_failure(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"{phase} response transport is invalid: {error.detail}",
                    )
            if response_pipe and response_valid:
                if set(response_object) != {"sha256", "size_bytes"}:
                    record_parent_failure(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"{phase} identity response has a partial shape",
                    )
                    response_valid = False
            if response_pipe and response_valid and output_valid:
                if (
                    response_object.get("sha256") != _sha256(output_payload)
                    or response_object.get("size_bytes") != len(output_payload)
                ):
                    record_parent_failure(
                        "ARTIFACT_INVALID",
                        f"{phase} identity response mismatch",
                    )
                    response_valid = False
            if response_valid and output_valid and success_validator is not None:
                try:
                    success_validator(
                        response_object,
                        output_payload,
                        output_object,
                    )
                except SupervisorFailure as error:
                    record_parent_failure(error.status, error.detail)
                    response_valid = False
                except BaseException as error:
                    record_parent_failure(
                        "RESOURCE_INCOMPLETE_NO_DECISION"
                        if isinstance(error, (KeyboardInterrupt, SystemExit))
                        else "IMPLEMENTATION_INVALID",
                        f"{phase} success-interface validator failed: {error}",
                    )
                    response_valid = False

        _, precleanup_staging_present, _ = _probe_entry_nofollow(
            staging,
            f"{phase} pre-cleanup staging",
            record_parent_failure,
        )
        if publication_visible and precleanup_staging_present:
            record_parent_failure(
                "ARTIFACT_INVALID",
                f"{phase} left staging beside a published target",
            )
        staging_absent_confirmed = _cleanup_owned_staging(
            staging,
            phase,
            bytes_,
            record_parent_failure,
        )

        for path in (stdout_path, stderr_path):
            stream_known, stream_present, stream_cleanup_metadata = (
                _probe_entry_nofollow(
                    path,
                    f"{phase} owned stream cleanup",
                    record_parent_failure,
                )
            )
            if not stream_known or not stream_present:
                continue
            if (
                stream_cleanup_metadata is None
                or not stat.S_ISREG(stream_cleanup_metadata.st_mode)
            ):
                record_parent_failure(
                    "ARTIFACT_INVALID",
                    f"{phase} owned stream became non-regular before cleanup",
                )
            try:
                path.unlink()
                if path in bytes_.live:
                    bytes_.note_deleted(path)
            except SupervisorFailure as error:
                record_parent_failure(error.status, error.detail)
            except OSError as error:
                record_parent_failure(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    f"{phase} stream cleanup failed: {error}",
                )
        try:
            work.rmdir()
        except OSError as error:
            record_parent_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"{phase} work-directory cleanup failed: {error}",
            )
        work_known, work_present, _ = _probe_entry_nofollow(
            work,
            f"{phase} post-cleanup work directory",
            record_parent_failure,
        )
        work_absent_confirmed = work_known and not work_present
        if work_known and work_present:
            record_parent_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                f"{phase} work directory remains after cleanup",
            )
        if (
            usage.exit_code == 0
            and post_cleanup_validator is not None
            and not nonresource_validation_failure
        ):
            try:
                post_cleanup_validator()
                post_cleanup_valid = True
            except SupervisorFailure as error:
                record_parent_failure(error.status, error.detail)
            except BaseException as error:
                record_parent_failure(
                    "RESOURCE_INCOMPLETE_NO_DECISION"
                    if isinstance(error, (KeyboardInterrupt, SystemExit))
                    else "IMPLEMENTATION_INVALID",
                    f"{phase} post-cleanup validator failed: {error}",
                )

        if _consume_deferred_sigint():
            supervisor_interrupted = True
        if supervisor_interrupted:
            record_parent_failure(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                f"{phase} supervisor SIGINT observed after child terminal state",
            )

        raw_wrapper_signal = usage.exit_code < 0
        clean_nested_interruption = (
            phase == "V_replay"
            and usage.exit_code == CHILD_EXTERNAL_INTERRUPTION_EXIT_CODE
        )
        retryable_interruption = clean_nested_interruption or (
            raw_wrapper_signal and phase != "V_replay"
        )
        child_interrupted = raw_wrapper_signal or clean_nested_interruption
        child_reason = (
            "PHASE_COMPLETE"
            if usage.exit_code == 0
            else "RESOURCE_INCOMPLETE_NO_DECISION"
            if raw_wrapper_signal and phase == "V_replay"
            else "EXTERNAL_INTERRUPTION"
            if retryable_interruption
            else "RESOURCE_INCOMPLETE_NO_DECISION"
            if usage.exit_code == CHILD_RESOURCE_FAILURE_EXIT_CODE
            else "EVIDENCE_INCOMPLETE_NO_DECISION"
            if usage.exit_code == CHILD_EVIDENCE_FAILURE_EXIT_CODE
            else "ARTIFACT_INVALID"
            if usage.exit_code == CHILD_ARTIFACT_FAILURE_EXIT_CODE
            else "IMPLEMENTATION_INVALID"
        )
        if (
            usage.exit_code == CHILD_RESOURCE_FAILURE_EXIT_CODE
            and publication_visible
        ):
            child_reason = "IMPLEMENTATION_INVALID"
        if retryable_interruption and publication_visible:
            child_reason = "RESOURCE_INCOMPLETE_NO_DECISION"
        if parent_status is not None:
            child_reason = (
                _status_min(child_reason, parent_status)
                if child_reason in STATUS_ORDER
                else parent_status
            )
        if attempt == 1 and retryable_interruption:
            child_reason = (
                _status_min(
                    child_reason,
                    "RESOURCE_INCOMPLETE_NO_DECISION",
                )
                if child_reason in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )

        try:
            end = _snapshot()
        except (OSError, KeyboardInterrupt, SystemExit) as error:
            snapshot_status = _status_min(parent_status, "IMPLEMENTATION_INVALID")
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                snapshot_status = _status_min(
                    parent_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
            if child_reason in STATUS_ORDER:
                snapshot_status = _status_min(snapshot_status, child_reason)
            _fail(
                snapshot_status,
                f"{phase} terminal resource snapshot failed after child reap: {error}",
            )
        end_utc = _utc_now()
        boundary = PhaseBoundary(end, end_utc)

        staging_disposition = (
            "ATOMICALLY_PUBLISHED"
            if publication_visible
            else "DISCARDED"
            if (
                target_known
                and not target_present
                and staging_absent_confirmed
                and work_absent_confirmed
            )
            else "NONE"
        )
        candidate_receipt = _phase_receipt(
            phase=phase,
            attempt_id=attempt,
            argv=fixed_argv,
            binary_sha256=receipt_binary_sha256,
            start=start,
            start_utc=start_utc,
            end=end,
            end_utc=end_utc,
            child_usage=usage,
            completed_unit=completed_unit,
            reason=child_reason,
            disposition=staging_disposition,
            logical_run_id=logical_run_id,
            commit=commit,
            environment_sha=environment_sha,
        )
        candidate_receipts = (*receipts, candidate_receipt)
        parent_resource_crossed = (
            sum(item["cpu_microseconds"] for item in candidate_receipts)
            > PER_PHASE_CPU_LIMIT
            or sum(item["wall_nanoseconds"] for item in candidate_receipts)
            > PER_PHASE_WALL_LIMIT
            or max(item["peak_rss_bytes"] for item in candidate_receipts) > RSS_LIMIT
            or prior_study_cpu_microseconds
            + sum(item["cpu_microseconds"] for item in candidate_receipts)
            > STUDY_CPU_LIMIT
        )
        if parent_resource_crossed:
            resource_return_eligible = True
            candidate_receipt["exit_reason"] = (
                _status_min(
                    str(candidate_receipt["exit_reason"]),
                    "RESOURCE_INCOMPLETE_NO_DECISION",
                )
                if candidate_receipt["exit_reason"] in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )
        receipts.append(candidate_receipt)

        if _consume_deferred_sigint():
            supervisor_interrupted = True
        if _restore_sigint_after_receipt(post_reap_mask):
            supervisor_interrupted = True
        post_reap_mask = None
        if supervisor_interrupted:
            current_reason = str(candidate_receipt["exit_reason"])
            candidate_receipt["exit_reason"] = (
                _status_min(current_reason, "RESOURCE_INCOMPLETE_NO_DECISION")
                if current_reason in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )
            if not any("supervisor SIGINT" in item for item in parent_details):
                parent_details.append(
                    f"{phase} supervisor SIGINT observed at receipt boundary"
                )

        local_detail = "; ".join(parent_details) or (
            f"{phase} child exit {usage.exit_code}: {stderr_payload[:4096]!r}"
        )
        phase_contract_complete = (
            usage.exit_code == 0
            and publication_visible
            and publication_target_real
            and staging_absent_confirmed
            and work_absent_confirmed
            and output_valid
            and response_valid
            and post_cleanup_valid
            and not supervisor_interrupted
            and not nonresource_validation_failure
        )
        final_reason = str(candidate_receipt["exit_reason"])
        if phase_contract_complete and final_reason == "PHASE_COMPLETE":
            return (
                receipts,
                response_payload,
                output_payload,
                response_object,
                output_object,
                boundary,
            )
        if (
            phase_contract_complete
            and final_reason == "RESOURCE_INCOMPLETE_NO_DECISION"
            and allow_published_resource_return
            and resource_return_eligible
        ):
            return (
                receipts,
                response_payload,
                output_payload,
                response_object,
                output_object,
                boundary,
            )
        if (
            child_interrupted
            and final_reason == "EXTERNAL_INTERRUPTION"
            and staging_disposition == "DISCARDED"
        ):
            continue
        _fail(
            final_reason
            if final_reason in STATUS_ORDER
            else "IMPLEMENTATION_INVALID",
            local_detail,
        )
    _fail("RESOURCE_INCOMPLETE_NO_DECISION", f"{phase} interrupted twice")


def _write_pipe_document(descriptor: int, value: Mapping[str, Any]) -> None:
    payload = evidence.canonical_document(value)
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("short inherited-state response write")
        offset += written


def _read_pipe_payload(descriptor: int, description: str) -> bytes:
    payload = bytearray()
    while True:
        chunk = os.read(descriptor, 1 << 16)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > 4 * 1024 * 1024:
            _fail("EVIDENCE_INCOMPLETE_NO_DECISION", f"{description} exceeds 4 MiB")
    return bytes(payload)


class _EmitHandoffOwner:
    """Restore C's original mask if E fails before a successful first fork."""

    def __init__(self, previous: set[signal.Signals]) -> None:
        self.previous = previous
        self.active = True
        self.descriptors: set[int] = set()
        self.cleanup_error: str | None = None

    def own_descriptors(self, *descriptors: int) -> None:
        if self.active:
            self.descriptors.update(descriptors)

    def restore(self) -> bool:
        if not self.active:
            return False
        close_errors: list[str] = []
        for descriptor in tuple(self.descriptors):
            try:
                os.close(descriptor)
            except OSError as error:
                if error.errno != errno.EBADF:
                    close_errors.append(f"fd {descriptor}: {error}")
        self.descriptors.clear()
        if close_errors:
            self.cleanup_error = "; ".join(close_errors)
        # Retain ownership until the mask restore itself succeeds.  A restore
        # failure is fail-stop with SIGINT still blocked and this owner still
        # active, so no caller can mistake a failed handoff for a release.
        interrupted = _restore_sigint_after_receipt(self.previous)
        self.active = False
        return interrupted

    def transfer_to_fork_parent(self) -> None:
        if not self.active:
            _fail("IMPLEMENTATION_INVALID", "E handoff owner transferred twice")
        self.descriptors.clear()
        self.active = False


def _restore_emit_handoff_after_error(
    owner: _EmitHandoffOwner,
    error: BaseException,
) -> None:
    if not owner.active:
        return
    restore_interrupted = owner.restore()
    existing = getattr(error, "status", None)
    if owner.cleanup_error is not None:
        status = (
            _status_min(existing, "IMPLEMENTATION_INVALID")
            if existing in STATUS_ORDER
            else "IMPLEMENTATION_INVALID"
        )
        _fail(
            status,
            "E pre-fork handoff descriptor cleanup failed: "
            f"{owner.cleanup_error}; original error: {error}",
        )
    if restore_interrupted:
        status = (
            _status_min(existing, "RESOURCE_INCOMPLETE_NO_DECISION")
            if existing in STATUS_ORDER
            else "RESOURCE_INCOMPLETE_NO_DECISION"
            if isinstance(error, (KeyboardInterrupt, SystemExit))
            else "IMPLEMENTATION_INVALID"
        )
        _fail(
            status,
            f"E pre-fork handoff failed at a SIGINT restore edge: {error}",
        )


def _emit_in_inherited_process_body(
    *,
    state: producer.ProducerState,
    artifact_root: Path,
    context_base: Mapping[str, Any],
    raw_instrument_receipts: Sequence[Mapping[str, Any]],
    byte_ledger: ByteLedger,
    checkpoint_start: ResourceSnapshot,
    checkpoint_utc: str,
    sealed_cpu: int,
    logical_run_id: str,
    commit: str,
    environment_sha: str,
    handoff_owner: _EmitHandoffOwner,
) -> tuple[list[dict[str, Any]], int, PhaseBoundary]:
    """Fork E_emit with COW state; no detail checkpoint crosses the boundary."""

    receipts: list[dict[str, Any]] = []
    fixed_argv = tuple(sys.argv)
    boundary = PhaseBoundary(checkpoint_start, checkpoint_utc)
    for attempt in range(2):
        start = boundary.snapshot
        start_utc = boundary.utc
        prior_emit_ledger = byte_ledger.phase_object("E_emit")
        receipt_binary_sha256 = _current_cpython_identity()[0]
        try:
            read_fd, write_fd = os.pipe()
        except OSError as error:
            _fail(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                f"E_emit response pipe could not be created: {error}",
            )
        handoff_owner.own_descriptors(read_fd, write_fd)
        try:
            pre_fork = _snapshot()
        except OSError as error:
            for descriptor in (read_fd, write_fd):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            _fail(
                "IMPLEMENTATION_INVALID",
                f"E_emit pre-fork resource snapshot failed: {error}",
            )
        parent_status: str | None = None
        parent_details: list[str] = []
        nonresource_validation_failure = False
        post_reap_mask: set[signal.Signals] | None = None
        supervisor_interrupted = False

        def record_parent_failure(status: str, detail: str) -> None:
            nonlocal parent_status, nonresource_validation_failure
            resolved = status if status in STATUS_ORDER else "IMPLEMENTATION_INVALID"
            parent_status = _status_min(parent_status, resolved)
            parent_details.append(detail)
            if resolved != "RESOURCE_INCOMPLETE_NO_DECISION":
                nonresource_validation_failure = True

        if handoff_owner.active:
            fork_mask = handoff_owner.previous
            try:
                inherited_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
            except (OSError, RuntimeError, ValueError) as error:
                _fail(
                    "IMPLEMENTATION_INVALID",
                    f"cannot inspect inherited C-to-E SIGINT mask: {error}",
                )
            if signal.SIGINT not in inherited_mask or signal.SIGINT in fork_mask:
                _fail(
                    "IMPLEMENTATION_INVALID",
                    "E did not receive the frozen blocked-to-unblocked handoff",
                )
            fork_interrupted = False
        else:
            fork_mask, fork_interrupted = _block_sigint_for_critical_section()
        if _consume_deferred_sigint():
            fork_interrupted = True
        if fork_interrupted:
            if handoff_owner.active:
                handoff_owner.restore()
                if handoff_owner.cleanup_error is not None:
                    _fail(
                        "IMPLEMENTATION_INVALID",
                        "E pre-fork interrupted cleanup failed: "
                        f"{handoff_owner.cleanup_error}",
                    )
            else:
                _restore_sigint_after_receipt(fork_mask)
            for descriptor in (read_fd, write_fd):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            _fail(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "E_emit supervisor interrupted before fork",
            )
        response_payload = b""
        parent_stage = "fork-mask restoration"
        write_fd_open = True
        read_fd_open = True
        usage: WaitResult | None = None

        def close_inherited_response_endpoints() -> None:
            nonlocal write_fd_open, read_fd_open
            # Recovery invokes this callback only after SIGINT is blocked.
            # Defining it before fork lets the launched parent enter its
            # recovery owner without any intervening setup.
            for descriptor_name, descriptor, is_open in (
                ("write", write_fd, write_fd_open),
                ("read", read_fd, read_fd_open),
            ):
                if not is_open:
                    continue
                try:
                    os.close(descriptor)
                except OSError as close_error:
                    record_parent_failure(
                        "EVIDENCE_INCOMPLETE_NO_DECISION",
                        f"E_emit inherited {descriptor_name}-descriptor "
                        f"close failed: {close_error}",
                    )
                if descriptor_name == "write":
                    write_fd_open = False
                else:
                    read_fd_open = False

        try:
            pid = os.fork()
        except OSError as error:
            _consume_deferred_sigint()
            if handoff_owner.active:
                handoff_owner.restore()
                if handoff_owner.cleanup_error is not None:
                    _fail(
                        "IMPLEMENTATION_INVALID",
                        "E pre-fork fork-failure cleanup failed: "
                        f"{handoff_owner.cleanup_error}",
                    )
            else:
                _restore_sigint_after_receipt(fork_mask)
            for descriptor in (read_fd, write_fd):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            _fail(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                f"E_emit child could not be forked: {error}",
            )
        if pid == 0:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.pthread_sigmask(signal.SIG_SETMASK, fork_mask)
            try:
                os.close(read_fd)
                child_start = _snapshot()
                byte_ledger.switch("E_emit")
                instrument_receipts = _sorted_receipts(raw_instrument_receipts)
                t_instrument = sum(
                    item["cpu_microseconds"]
                    for item in instrument_receipts
                    if item["phase"] in {"C_setup", "C_core", "C_bundle_io"}
                )
                emit_checkpoint = {
                    "completed_unit_count": state.completed_unit_count,
                    "input_file_count": _input_file_count(state, False),
                    "last_completed_unit_index": state.last_completed_unit_index,
                    "logical_run_id": logical_run_id,
                    "phase": "E_emit",
                    "start_utc": start_utc,
                }
                context = evidence.ProducerManifestContext(
                    binary_identity=context_base["binary_identity"],
                    command_identity=context_base["command_identity"],
                    emit_start_checkpoint=emit_checkpoint,
                    environment_identity=context_base["environment_identity"],
                    phase_receipts_through_instrument=instrument_receipts,
                    prelaunch_observation=context_base["prelaunch_observation"],
                    protocol_identity=context_base["protocol_identity"],
                    schema_identity=context_base["schema_identity"],
                    source_identity=context_base["source_identity"],
                )
                publication = evidence.publish_evidence(
                    state,
                    artifact_root,
                    context,
                    EmitHooks(
                        byte_ledger,
                        child_start,
                        sealed_cpu
                        + t_instrument
                        + sum(item["cpu_microseconds"] for item in receipts)
                        + pre_fork.cpu_microseconds
                        - start.cpu_microseconds,
                        sum(item["cpu_microseconds"] for item in receipts)
                        + pre_fork.cpu_microseconds
                        - start.cpu_microseconds,
                        sum(item["wall_nanoseconds"] for item in receipts)
                        + pre_fork.wall_nanoseconds
                        - start.wall_nanoseconds,
                    ),
                )
                response = {
                    "byte_ledger": byte_ledger.phase_object("E_emit"),
                    "directory": publication.directory,
                    "files": [item.object() for item in publication.files],
                    "ok": True,
                    "t_instrument_cpu_microseconds": t_instrument,
                    "total_bytes": publication.total_bytes,
                }
                _write_pipe_document(write_fd, response)
                os.close(write_fd)
                os._exit(0)
            except BaseException as error:
                status = getattr(error, "status", "IMPLEMENTATION_INVALID")
                detail = str(getattr(error, "detail", str(error)))[:4096]
                try:
                    _write_pipe_document(
                        write_fd,
                        {"detail": detail, "ok": False, "status": status},
                    )
                    os.close(write_fd)
                finally:
                    os._exit(2)
        try:
            if handoff_owner.active:
                handoff_owner.transfer_to_fork_parent()
            if _consume_deferred_sigint():
                fork_interrupted = True
            if _restore_sigint_after_receipt(fork_mask):
                fork_interrupted = True
            if fork_interrupted:
                raise KeyboardInterrupt("E_emit interrupted at fork boundary")

            parent_stage = "inherited write-descriptor close"
            os.close(write_fd)
            write_fd_open = False
            parent_stage = "inherited response drain"
            response_payload = _read_pipe_payload(
                read_fd, "E_emit inherited response"
            )
            parent_stage = "inherited read-descriptor close"
            os.close(read_fd)
            read_fd_open = False
            parent_stage = "terminal wait handoff"
            (
                usage,
                post_reap_mask,
                terminal_edge_interrupted,
            ) = _wait4_with_deferred_postreap_sigint(pid)
            supervisor_interrupted = (
                supervisor_interrupted or terminal_edge_interrupted
            )
        except BaseException as error:
            recovery_mask, recovery_interrupted = (
                _block_sigint_for_critical_section()
            )
            if _consume_deferred_sigint():
                recovery_interrupted = True
            if usage is None:
                retained_mask = (
                    fork_mask
                    if signal.SIGINT in recovery_mask
                    else recovery_mask
                )
                (
                    usage,
                    post_reap_mask,
                    terminal_edge_interrupted,
                    kill_error,
                ) = _kill_and_must_reap_while_sigint_blocked(
                    pid,
                    retained_mask,
                    recovery_interrupted,
                    close_inherited_response_endpoints,
                )
            else:
                close_inherited_response_endpoints()
                terminal_edge_interrupted = recovery_interrupted
                kill_error = None
                if post_reap_mask is None:
                    post_reap_mask = (
                        fork_mask
                        if signal.SIGINT in recovery_mask
                        else recovery_mask
                    )
            supervisor_interrupted = (
                supervisor_interrupted
                or terminal_edge_interrupted
                or recovery_interrupted
                or isinstance(error, (KeyboardInterrupt, SystemExit))
            )
            record_parent_failure(
                "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else error.status
                if isinstance(error, SupervisorFailure)
                else "EVIDENCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, OSError) and parent_stage != "terminal wait handoff"
                else "IMPLEMENTATION_INVALID",
                f"E_emit supervisor failed during {parent_stage}: {error}",
            )
            if kill_error is not None:
                record_parent_failure(
                    "IMPLEMENTATION_INVALID",
                    f"E_emit child termination reported: {kill_error}",
                )
        if post_reap_mask is None:
            _fail(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "E_emit child has no deferred terminal receipt boundary",
            )
        target = artifact_root / "evidence"
        staging = artifact_root / "evidence.staging"
        target_known, target_present, target_metadata = _probe_entry_nofollow(
            target,
            "E_emit publication target",
            record_parent_failure,
        )
        publication_visible = target_known and target_present
        publication_target_real = (
            publication_visible
            and target_metadata is not None
            and stat.S_ISDIR(target_metadata.st_mode)
        )
        if publication_visible and not publication_target_real:
            record_parent_failure(
                "ARTIFACT_INVALID",
                "E_emit publication target is not a real directory",
            )
        response: Any = {}
        response_transport_valid = False
        if usage.exit_code >= 0 and response_payload:
            try:
                response = _parse_json_document(
                    response_payload, "E_emit inherited response", True
                )
                response_transport_valid = True
            except SupervisorFailure as error:
                record_parent_failure(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    f"E_emit inherited response is invalid: {error.detail}",
                )
        expected_t_instrument = sum(
            item["cpu_microseconds"]
            for item in raw_instrument_receipts
            if item["phase"] in {"C_setup", "C_core", "C_bundle_io"}
        )
        expected_evidence_identities = (
            (
                "evidence/scalar_optimum_records.jsonl",
                "scalar_optimum_records",
                "scalar_optimum_v2-jsonl",
            ),
            (
                "evidence/allocation_summary.json",
                "allocation_summary",
                "allocation_summary_v2",
            ),
            (
                "evidence/block_trajectories.jsonl",
                "block_trajectories",
                "block_metadata_v2-or-block_start_v2-jsonl",
            ),
            (
                "evidence/encoding_summary.json",
                "encoding_summary",
                "encoding_summary_v2",
            ),
            (
                "evidence/producer_manifest.json",
                "producer_manifest",
                "producer_manifest_v2",
            ),
        )
        response_files = response.get("files") if isinstance(response, dict) else None
        files_valid = (
            isinstance(response_files, list)
            and len(response_files) == len(expected_evidence_identities)
        )
        response_file_total = 0
        if files_valid:
            for item, expected_identity in zip(
                response_files, expected_evidence_identities
            ):
                if not (
                    isinstance(item, dict)
                    and set(item)
                    == {
                        "path",
                        "producing_phase",
                        "role",
                        "schema",
                        "sha256",
                        "size_bytes",
                    }
                    and (
                        item["path"],
                        item["role"],
                        item["schema"],
                    )
                    == expected_identity
                    and item["producing_phase"] == "E_emit"
                    and isinstance(item["sha256"], str)
                    and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None
                    and isinstance(item["size_bytes"], int)
                    and not isinstance(item["size_bytes"], bool)
                    and item["size_bytes"] >= 0
                ):
                    files_valid = False
                    break
                response_file_total += item["size_bytes"]
        response_ledger = (
            response.get("byte_ledger") if isinstance(response, dict) else None
        )
        ledger_numeric_names = {
            "created_temporary_bytes",
            "deleted_partial_bytes",
            "maximum_live_owned_temporary_bytes",
            "permanent_intermediate_bundle_bytes",
            "research_evidence_archive_bytes",
        }
        ledger_shape_valid = (
            isinstance(response_ledger, dict)
            and set(response_ledger) == {*ledger_numeric_names, "phase"}
            and response_ledger.get("phase") == "E_emit"
            and all(
                isinstance(response_ledger.get(name), int)
                and not isinstance(response_ledger.get(name), bool)
                and response_ledger.get(name, -1) >= 0
                for name in ledger_numeric_names
            )
        )
        response_total = response.get("total_bytes") if isinstance(response, dict) else None
        ledger_reconciles = (
            ledger_shape_valid
            and prior_emit_ledger["created_temporary_bytes"]
            == prior_emit_ledger["deleted_partial_bytes"]
            and prior_emit_ledger["permanent_intermediate_bundle_bytes"] == 0
            and prior_emit_ledger["research_evidence_archive_bytes"] == 0
            and isinstance(response_total, int)
            and not isinstance(response_total, bool)
            and response_total == response_file_total
            and response_total <= EVIDENCE_LIMIT
            and response_ledger["created_temporary_bytes"]
            == prior_emit_ledger["created_temporary_bytes"] + response_total
            and response_ledger["deleted_partial_bytes"]
            == prior_emit_ledger["deleted_partial_bytes"]
            and response_ledger["maximum_live_owned_temporary_bytes"]
            == max(
                prior_emit_ledger["maximum_live_owned_temporary_bytes"],
                response_total,
            )
            and response_ledger["permanent_intermediate_bundle_bytes"]
            == prior_emit_ledger["permanent_intermediate_bundle_bytes"]
            and response_ledger["research_evidence_archive_bytes"]
            == prior_emit_ledger["research_evidence_archive_bytes"]
            + response_total
        )
        success_response_valid = (
            response_transport_valid
            and isinstance(response, dict)
            and set(response)
            == {
                "byte_ledger",
                "directory",
                "files",
                "ok",
                "t_instrument_cpu_microseconds",
                "total_bytes",
            }
            and response.get("ok") is True
            and response.get("directory") == "evidence"
            and files_valid
            and ledger_reconciles
            and isinstance(response.get("t_instrument_cpu_microseconds"), int)
            and not isinstance(response.get("t_instrument_cpu_microseconds"), bool)
            and response.get("t_instrument_cpu_microseconds")
            == expected_t_instrument
        )
        if usage.exit_code == 0 and not success_response_valid:
            record_parent_failure(
                "IMPLEMENTATION_INVALID"
                if response_transport_valid
                else "EVIDENCE_INCOMPLETE_NO_DECISION",
                "E_emit success response is malformed",
            )
        failure_response_shape_valid = (
            isinstance(response, dict)
            and set(response) == {"detail", "ok", "status"}
            and response.get("ok") is False
            and isinstance(response.get("detail"), str)
            and isinstance(response.get("status"), str)
        )
        allowed_failure_statuses = {
            "ARTIFACT_INVALID",
            "EVIDENCE_INCOMPLETE_NO_DECISION",
            "IMPLEMENTATION_INVALID",
            "RESOURCE_INCOMPLETE_NO_DECISION",
        }
        failure_response_valid = (
            failure_response_shape_valid
            and response.get("status") in allowed_failure_statuses
        )
        if usage.exit_code == 2 and not failure_response_valid:
            record_parent_failure(
                "IMPLEMENTATION_INVALID"
                if response_transport_valid
                else "EVIDENCE_INCOMPLETE_NO_DECISION",
                "E_emit failure response is outside its frozen typed channel"
                if failure_response_shape_valid
                else "E_emit failure response is malformed",
            )
        if usage.exit_code == 0 and not publication_visible:
            record_parent_failure(
                "EVIDENCE_INCOMPLETE_NO_DECISION",
                "E_emit exited successfully without a visible evidence target",
            )
        byte_ledger_replaced = False
        if (
            usage.exit_code == 0
            and success_response_valid
            and publication_target_real
        ):
            try:
                byte_ledger.replace_phase("E_emit", response["byte_ledger"])
                byte_ledger_replaced = True
            except SupervisorFailure as error:
                record_parent_failure(error.status, error.detail)
        _, precleanup_staging_present, _ = _probe_entry_nofollow(
            staging,
            "E_emit pre-cleanup staging",
            record_parent_failure,
        )
        if publication_visible and precleanup_staging_present:
            record_parent_failure(
                "ARTIFACT_INVALID",
                "E_emit left staging beside a published target",
            )
        staging_absent_confirmed = _cleanup_owned_staging(
            staging,
            "E_emit",
            byte_ledger,
            record_parent_failure,
        )
        if _consume_deferred_sigint():
            supervisor_interrupted = True
        if supervisor_interrupted:
            record_parent_failure(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "E_emit supervisor SIGINT observed after child terminal state",
            )

        child_reason = (
            "PHASE_COMPLETE"
            if usage.exit_code == 0
            else "EVIDENCE_INCOMPLETE_NO_DECISION"
            if usage.exit_code == 2 and not failure_response_valid
            else "EXTERNAL_INTERRUPTION"
            if usage.exit_code < 0
            else str(response["status"])
            if usage.exit_code == 2
            else "IMPLEMENTATION_INVALID"
        )
        if usage.exit_code < 0 and publication_visible:
            child_reason = "RESOURCE_INCOMPLETE_NO_DECISION"
        if parent_status is not None:
            child_reason = (
                _status_min(child_reason, parent_status)
                if child_reason in STATUS_ORDER
                else parent_status
            )
        if attempt == 1 and usage.exit_code < 0:
            child_reason = (
                _status_min(child_reason, "RESOURCE_INCOMPLETE_NO_DECISION")
                if child_reason in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )
        try:
            end = _snapshot()
        except (OSError, KeyboardInterrupt, SystemExit) as error:
            candidate_status = (
                "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID"
            )
            snapshot_status = _status_min(parent_status, candidate_status)
            if child_reason in STATUS_ORDER:
                snapshot_status = _status_min(snapshot_status, child_reason)
            _fail(
                snapshot_status,
                f"E_emit terminal resource snapshot failed after child reap: {error}",
            )
        end_utc = _utc_now()
        boundary = PhaseBoundary(end, end_utc)
        phase_contract_complete = (
            usage.exit_code == 0
            and success_response_valid
            and publication_visible
            and publication_target_real
            and staging_absent_confirmed
            and byte_ledger_replaced
            and not supervisor_interrupted
            and not nonresource_validation_failure
        )
        staging_disposition = (
            "ATOMICALLY_PUBLISHED"
            if publication_visible
            else "DISCARDED"
            if target_known and not target_present and staging_absent_confirmed
            else "NONE"
        )
        candidate_receipt = _phase_receipt(
            phase="E_emit",
            attempt_id=attempt,
            argv=fixed_argv,
            binary_sha256=receipt_binary_sha256,
            start=start,
            start_utc=start_utc,
            end=end,
            end_utc=end_utc,
            child_usage=usage,
            completed_unit=state.last_completed_unit_index,
            reason=child_reason,
            disposition=staging_disposition,
            logical_run_id=logical_run_id,
            commit=commit,
            environment_sha=environment_sha,
        )
        candidate_receipts = (*receipts, candidate_receipt)
        parent_resource_crossed = (
            sum(item["cpu_microseconds"] for item in candidate_receipts)
            > PER_PHASE_CPU_LIMIT
            or sum(item["wall_nanoseconds"] for item in candidate_receipts)
            > PER_PHASE_WALL_LIMIT
            or sealed_cpu
            + expected_t_instrument
            + sum(item["cpu_microseconds"] for item in candidate_receipts)
            > STUDY_CPU_LIMIT
            or max(item["peak_rss_bytes"] for item in candidate_receipts)
            > RSS_LIMIT
        )
        if parent_resource_crossed:
            current_reason = str(candidate_receipt["exit_reason"])
            candidate_receipt["exit_reason"] = (
                _status_min(current_reason, "RESOURCE_INCOMPLETE_NO_DECISION")
                if current_reason in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )
        receipts.append(candidate_receipt)
        if _consume_deferred_sigint():
            supervisor_interrupted = True
        if _restore_sigint_after_receipt(post_reap_mask):
            supervisor_interrupted = True
        post_reap_mask = None
        if supervisor_interrupted:
            current_reason = str(candidate_receipt["exit_reason"])
            candidate_receipt["exit_reason"] = (
                _status_min(current_reason, "RESOURCE_INCOMPLETE_NO_DECISION")
                if current_reason in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )
            if not any("supervisor SIGINT" in item for item in parent_details):
                parent_details.append(
                    "E_emit supervisor SIGINT observed at receipt boundary"
                )
        final_reason = str(candidate_receipt["exit_reason"])
        if phase_contract_complete and final_reason == "PHASE_COMPLETE":
            return receipts, expected_t_instrument, boundary
        if (
            usage.exit_code < 0
            and final_reason == "EXTERNAL_INTERRUPTION"
            and staging_disposition == "DISCARDED"
        ):
            continue
        detail = "; ".join(parent_details) or (
            str(response.get("detail", "E_emit child failed"))
            if usage.exit_code == 2 and failure_response_valid
            else "E_emit operational ceiling crossed"
            if final_reason == "RESOURCE_INCOMPLETE_NO_DECISION"
            else "E_emit success response/publication is malformed"
            if usage.exit_code == 0
            else f"E_emit child exit {usage.exit_code}"
        )
        _fail(
            final_reason if final_reason in STATUS_ORDER else "IMPLEMENTATION_INVALID",
            detail,
        )
    _fail("RESOURCE_INCOMPLETE_NO_DECISION", "E_emit process interrupted twice")


def _emit_in_inherited_process(
    *,
    state: producer.ProducerState,
    artifact_root: Path,
    context_base: Mapping[str, Any],
    raw_instrument_receipts: Sequence[Mapping[str, Any]],
    byte_ledger: ByteLedger,
    checkpoint_start: ResourceSnapshot,
    checkpoint_utc: str,
    sealed_cpu: int,
    logical_run_id: str,
    commit: str,
    environment_sha: str,
    handoff_owner: _EmitHandoffOwner,
) -> tuple[list[dict[str, Any]], int, PhaseBoundary]:
    """Own C's blocked mask until E's first fork or an explicit restore."""

    try:
        return _emit_in_inherited_process_body(
            state=state,
            artifact_root=artifact_root,
            context_base=context_base,
            raw_instrument_receipts=raw_instrument_receipts,
            byte_ledger=byte_ledger,
            checkpoint_start=checkpoint_start,
            checkpoint_utc=checkpoint_utc,
            sealed_cpu=sealed_cpu,
            logical_run_id=logical_run_id,
            commit=commit,
            environment_sha=environment_sha,
            handoff_owner=handoff_owner,
        )
    except BaseException as error:
        _restore_emit_handoff_after_error(handoff_owner, error)
        raise


def _input_file_count(state: producer.ProducerState, include_evidence: bool) -> int:
    bundle = len(state.bundle.files) if state.bundle is not None else 0
    return bundle + (5 if include_evidence else 0)


def _require_exact_final_input_tree(root: Path, bundle_published: bool) -> None:
    expected = {
        "archive": {"archive_body.json"},
        "evidence": {
            "allocation_summary.json",
            "block_trajectories.jsonl",
            "encoding_summary.json",
            "producer_manifest.json",
            "scalar_optimum_records.jsonl",
        },
        "verifier": {"verifier_summary.json"},
    }
    if bundle_published:
        expected["bundle"] = {
            "codes_b04.bin",
            "codes_b08.bin",
            "models.json",
            "representation_manifest.json",
        }
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )

    def require_same(
        expected_metadata: os.stat_result,
        observed_metadata: os.stat_result,
        description: str,
    ) -> None:
        if any(
            getattr(expected_metadata, field) != getattr(observed_metadata, field)
            for field in stable_fields
        ):
            _fail("ARTIFACT_INVALID", f"pre-F identity changed: {description}")

    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    leaf_flags = os.O_PATH | getattr(os, "O_CLOEXEC", 0) | getattr(
        os, "O_NOFOLLOW", 0
    )
    root_fd: int | None = None
    try:
        root_named = os.stat(root, follow_symlinks=False)
        root_fd = os.open(root, directory_flags)
        root_opened = os.fstat(root_fd)
        require_same(root_named, root_opened, str(root))
        with os.scandir(root_fd) as root_entries:
            observed_root = {entry.name: entry for entry in root_entries}
        if set(observed_root) != set(expected) or any(
            not stat.S_ISDIR(entry.stat(follow_symlinks=False).st_mode)
            for entry in observed_root.values()
        ):
            _fail("ARTIFACT_INVALID", "pre-F artifact-root membership is not exact")
        for directory, expected_files in expected.items():
            directory_fd: int | None = None
            try:
                entry_metadata = observed_root[directory].stat(follow_symlinks=False)
                directory_fd = os.open(
                    directory,
                    directory_flags,
                    dir_fd=root_fd,
                )
                opened_metadata = os.fstat(directory_fd)
                require_same(entry_metadata, opened_metadata, directory)
                with os.scandir(directory_fd) as child_entries:
                    observed_children = {
                        entry.name: entry for entry in child_entries
                    }
                if set(observed_children) != expected_files:
                    _fail(
                        "ARTIFACT_INVALID",
                        f"pre-F {directory} membership is not exact",
                    )
                for name, entry in observed_children.items():
                    leaf_metadata = entry.stat(follow_symlinks=False)
                    if not stat.S_ISREG(leaf_metadata.st_mode):
                        _fail(
                            "ARTIFACT_INVALID",
                            f"pre-F {directory}/{name} is not regular",
                        )
                    leaf_fd = os.open(name, leaf_flags, dir_fd=directory_fd)
                    try:
                        opened_leaf = os.fstat(leaf_fd)
                        named_leaf = os.stat(
                            name,
                            dir_fd=directory_fd,
                            follow_symlinks=False,
                        )
                        require_same(
                            leaf_metadata,
                            opened_leaf,
                            f"{directory}/{name}",
                        )
                        require_same(
                            opened_leaf,
                            named_leaf,
                            f"{directory}/{name}",
                        )
                    finally:
                        active_error = sys.exc_info()[0] is not None
                        try:
                            os.close(leaf_fd)
                        except OSError as error:
                            if not active_error:
                                _fail(
                                    "ARTIFACT_INVALID",
                                    f"cannot close exact pre-F leaf "
                                    f"{directory}/{name}: {error}",
                                )
                directory_after = os.fstat(directory_fd)
                directory_named_after = os.stat(
                    directory,
                    dir_fd=root_fd,
                    follow_symlinks=False,
                )
                require_same(opened_metadata, directory_after, directory)
                require_same(opened_metadata, directory_named_after, directory)
            finally:
                active_error = sys.exc_info()[0] is not None
                if directory_fd is not None:
                    try:
                        os.close(directory_fd)
                    except OSError as error:
                        if not active_error:
                            _fail(
                                "ARTIFACT_INVALID",
                                f"cannot close exact pre-F directory "
                                f"{directory}: {error}",
                            )
        root_after = os.fstat(root_fd)
        root_named_after = os.stat(root, follow_symlinks=False)
        require_same(root_opened, root_after, str(root))
        require_same(root_opened, root_named_after, str(root))
    except SupervisorFailure:
        raise
    except OSError as error:
        _fail("ARTIFACT_INVALID", f"cannot validate exact pre-F input tree: {error}")
    finally:
        active_error = sys.exc_info()[0] is not None
        if root_fd is not None:
            try:
                os.close(root_fd)
            except OSError as error:
                if not active_error:
                    _fail(
                        "ARTIFACT_INVALID",
                        f"cannot close exact pre-F root: {error}",
                    )


def _observe_closed_producer_terminal(
    hooks: SupervisorHooks,
    meter: InstrumentMeter,
) -> bool:
    """Observe and own the just-built terminal receipt tail exactly once."""

    fresh = _snapshot()
    incomplete = hooks.observe_terminal_resources(fresh)
    meter.extend_closed_terminal(fresh)
    return incomplete


def _discard_producer_staging(
    artifact_root: Path,
    attempt_root: Path,
    byte_ledger: ByteLedger,
    record_failure: Any,
) -> bool:
    """Ledger and remove both unpublished producer staging namespaces."""

    bundle_staging = artifact_root / "bundle.staging"
    phase = byte_ledger.phase
    bundle_absent = _cleanup_owned_staging(
        bundle_staging,
        phase,
        byte_ledger,
        record_failure,
    )
    attempt_absent = _cleanup_owned_staging(
        attempt_root,
        phase,
        byte_ledger,
        record_failure,
    )
    return bundle_absent and attempt_absent


def _finalize_producer_attempt(
    *,
    hooks: SupervisorHooks,
    meter: InstrumentMeter,
    artifact_root: Path,
    attempt_root: Path,
    byte_ledger: ByteLedger,
    reason: str,
    disposition: str,
) -> tuple[str, bool, str, bool]:
    """Close C cleanup, sticky resources, receipt, and SIGINT as one boundary."""

    if hooks.terminal_finalized:
        def merged_finalized_status(candidate: str) -> str:
            merged = _c_failure_status(candidate)
            for existing in (reason, hooks.terminal_known_status):
                if existing in STATUS_ORDER:
                    merged = _status_min(merged, _c_failure_status(existing))
            if (
                hooks.terminal_receipt_index is not None
                and hooks.terminal_receipt_index == len(meter.receipts) - 1
            ):
                existing = str(
                    meter.receipts[hooks.terminal_receipt_index]["exit_reason"]
                )
                if existing in STATUS_ORDER:
                    merged = _status_min(merged, _c_failure_status(existing))
            return merged

        try:
            terminal_interrupted = hooks.begin_terminal_closure()
        except BaseException as error:
            hooks.terminal_closure_valid = False
            _fail(
                merged_finalized_status(
                    error.status
                    if isinstance(error, SupervisorFailure)
                    else "RESOURCE_INCOMPLETE_NO_DECISION"
                    if isinstance(error, (KeyboardInterrupt, SystemExit))
                    else "IMPLEMENTATION_INVALID"
                ),
                f"cannot re-enter C terminal closure: {error}",
            )
        if (
            hooks.terminal_receipt_index is None
            or hooks.terminal_receipt_index != len(meter.receipts) - 1
        ):
            _fail(
                merged_finalized_status("IMPLEMENTATION_INVALID"),
                "C terminal receipt guard is inconsistent",
            )
        receipt = meter.receipts[hooks.terminal_receipt_index]
        merged_existing = str(receipt["exit_reason"])
        if reason in STATUS_ORDER:
            normalized_reason = _c_failure_status(reason)
            merged_existing = (
                _status_min(_c_failure_status(merged_existing), normalized_reason)
                if merged_existing in STATUS_ORDER
                else normalized_reason
            )
        if terminal_interrupted:
            hooks.resource_incomplete = True
            merged_existing = (
                _status_min(
                    merged_existing,
                    "RESOURCE_INCOMPLETE_NO_DECISION",
                )
                if merged_existing in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )
        receipt["exit_reason"] = merged_existing
        try:
            terminal_interrupted = hooks.observe_terminal_closure()
        except BaseException as error:
            hooks.terminal_closure_valid = False
            merged_existing = merged_finalized_status(
                error.status
                if isinstance(error, SupervisorFailure)
                else "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID"
            )
            receipt["exit_reason"] = merged_existing
            _fail(
                merged_existing,
                f"cannot observe re-entered C terminal closure: {error}",
            )
        if terminal_interrupted:
            hooks.resource_incomplete = True
            merged_existing = (
                _status_min(
                    merged_existing,
                    "RESOURCE_INCOMPLETE_NO_DECISION",
                )
                if merged_existing in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )
            receipt["exit_reason"] = merged_existing
        return (
            merged_existing,
            hooks.resource_incomplete,
            hooks.terminal_disposition,
            hooks.terminal_cleanup_complete,
        )

    normalized_reason = _c_failure_status(reason) if reason in STATUS_ORDER else reason
    merged_reason = (
        _status_min(normalized_reason, hooks.terminal_known_status)
        if normalized_reason in STATUS_ORDER
        and hooks.terminal_known_status in C_FAILURE_STATUSES
        else hooks.terminal_known_status
        if hooks.terminal_known_status in C_FAILURE_STATUSES
        else normalized_reason
    )
    cleanup_in_progress = False
    cleanup_accounting_complete = True

    def record_failure(status: str, detail: str) -> None:
        nonlocal merged_reason, cleanup_accounting_complete
        resolved = _c_failure_status(status)
        merged_reason = (
            _status_min(merged_reason, resolved)
            if merged_reason in STATUS_ORDER
            else resolved
        )
        if resolved == "RESOURCE_INCOMPLETE_NO_DECISION":
            hooks.resource_incomplete = True
        if cleanup_in_progress:
            cleanup_accounting_complete = False

    try:
        terminal_interrupted = hooks.begin_terminal_closure()
    except BaseException as error:
        hooks.terminal_closure_valid = False
        record_failure(
            error.status
            if isinstance(error, SupervisorFailure)
            else "RESOURCE_INCOMPLETE_NO_DECISION"
            if isinstance(error, (KeyboardInterrupt, SystemExit))
            else "IMPLEMENTATION_INVALID",
            f"cannot enter C terminal closure: {error}",
        )
        _fail(
            merged_reason
            if merged_reason in STATUS_ORDER
            else "IMPLEMENTATION_INVALID",
            "C terminal closure could not be entered",
        )
    if terminal_interrupted:
        record_failure(
            "RESOURCE_INCOMPLETE_NO_DECISION",
            "C supervisor SIGINT observed before terminal cleanup",
        )
    receipt_count_before = len(meter.receipts)
    observed_disposition = disposition
    try:
        if not hooks.terminal_cleanup_started:
            hooks.terminal_cleanup_started = True
            bundle_known, bundle_present, bundle_metadata = _probe_entry_nofollow(
                artifact_root / "bundle",
                "C bundle publication target",
                record_failure,
            )
            bundle_admitted = (
                hooks.last_state is not None
                and hooks.last_state.last_completed_unit_index == 395
                and hooks.last_state.bundle is not None
            )
            if not bundle_known:
                observed_disposition = "NONE"
                hooks.terminal_closure_valid = False
            elif bundle_present:
                hooks.publication_became_visible = True
                observed_disposition = "ATOMICALLY_PUBLISHED"
                if (
                    bundle_metadata is None
                    or not stat.S_ISDIR(bundle_metadata.st_mode)
                ):
                    record_failure(
                        "ARTIFACT_INVALID",
                        "C bundle publication target is not a real directory",
                    )
                    hooks.terminal_closure_valid = False
                if not bundle_admitted:
                    record_failure(
                        "ARTIFACT_INVALID",
                        "C bundle target is visible before U395 admission",
                    )
                    hooks.terminal_closure_valid = False
            elif bundle_admitted or hooks.publication_became_visible:
                record_failure(
                    "ARTIFACT_INVALID",
                    "C bundle publication marker disagrees with target visibility",
                )
                hooks.terminal_closure_valid = False
            cleanup_in_progress = True
            try:
                try:
                    staging_absent = _discard_producer_staging(
                        artifact_root,
                        attempt_root,
                        byte_ledger,
                        record_failure,
                    )
                except BaseException as error:
                    staging_absent = False
                    record_failure(
                        error.status
                        if isinstance(error, SupervisorFailure)
                        else "IMPLEMENTATION_INVALID",
                        f"C terminal staging cleanup failed: {error}",
                    )
            finally:
                cleanup_in_progress = False
            if (
                observed_disposition != "ATOMICALLY_PUBLISHED"
                and disposition == "DISCARDED"
                and not staging_absent
            ):
                observed_disposition = "NONE"
            hooks.terminal_closure_valid = (
                hooks.terminal_closure_valid
                and staging_absent
                and cleanup_accounting_complete
            )
            hooks.terminal_cleanup_complete = hooks.terminal_closure_valid
            hooks.terminal_disposition = observed_disposition
        else:
            observed_disposition = hooks.terminal_disposition
            if not hooks.terminal_cleanup_complete:
                hooks.terminal_closure_valid = False
        try:
            meter.close_current(merged_reason, observed_disposition)
        except BaseException as error:
            hooks.terminal_closure_valid = False
            record_failure(
                error.status
                if isinstance(error, SupervisorFailure)
                else "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID",
                f"C terminal receipt construction failed: {error}",
            )
        if len(meter.receipts) == receipt_count_before + 1:
            hooks.terminal_finalized = True
            hooks.terminal_receipt_index = len(meter.receipts) - 1
            hooks.terminal_cleanup_complete = hooks.terminal_closure_valid
            hooks.terminal_disposition = observed_disposition
        if len(meter.receipts) == receipt_count_before + 1:
            meter.receipts[-1]["exit_reason"] = merged_reason
            meter.receipts[-1]["staging_disposition"] = observed_disposition
    finally:
        try:
            terminal_interrupted = hooks.observe_terminal_closure()
        except BaseException as error:
            hooks.terminal_closure_valid = False
            record_failure(
                error.status
                if isinstance(error, SupervisorFailure)
                else "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID",
                f"cannot observe C terminal receipt boundary: {error}",
            )
            terminal_interrupted = False
        if terminal_interrupted:
            record_failure(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "C supervisor SIGINT observed at terminal receipt boundary",
            )
        if len(meter.receipts) == receipt_count_before + 1:
            meter.receipts[-1]["exit_reason"] = merged_reason
            meter.receipts[-1]["staging_disposition"] = observed_disposition
    if len(meter.receipts) != receipt_count_before + 1:
        _fail(
            merged_reason if merged_reason in STATUS_ORDER else "IMPLEMENTATION_INVALID",
            "C terminal receipt could not be constructed",
        )
    hooks.terminal_cleanup_complete = hooks.terminal_closure_valid
    hooks.terminal_disposition = observed_disposition
    return (
        merged_reason,
        hooks.resource_incomplete,
        observed_disposition,
        hooks.terminal_cleanup_complete,
    )


def _seal_producer_terminal_tail(
    hooks: SupervisorHooks,
    meter: InstrumentMeter,
) -> tuple[str, bool, bool]:
    """Extend the unique C receipt after all root-owned terminal work."""

    def merged_known_status(candidate: str) -> str:
        merged = _c_failure_status(candidate)
        if hooks.terminal_known_status in C_FAILURE_STATUSES:
            merged = _status_min(merged, hooks.terminal_known_status)
        if (
            hooks.terminal_receipt_index is not None
            and hooks.terminal_receipt_index == len(meter.receipts) - 1
        ):
            existing = str(meter.receipts[hooks.terminal_receipt_index]["exit_reason"])
            if existing in STATUS_ORDER:
                merged = _status_min(merged, _c_failure_status(existing))
        return merged

    try:
        hooks.begin_terminal_closure()
    except BaseException as error:
        hooks.terminal_closure_valid = False
        _fail(
            merged_known_status(
                error.status
                if isinstance(error, SupervisorFailure)
                else "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID"
            ),
            f"cannot enter C terminal-tail closure: {error}",
        )
    if (
        not hooks.terminal_finalized
        or hooks.terminal_receipt_index is None
        or hooks.terminal_receipt_index != len(meter.receipts) - 1
    ):
        hooks.terminal_closure_valid = False
        _fail(
            merged_known_status("IMPLEMENTATION_INVALID"),
            "C terminal receipt is not uniquely addressable",
        )
    receipt = meter.receipts[hooks.terminal_receipt_index]
    reason = str(receipt["exit_reason"])
    if hooks.terminal_tail_observation_attempted:
        if not hooks.terminal_tail_extended:
            hooks.terminal_closure_valid = False
        return reason, hooks.resource_incomplete, hooks.terminal_closure_valid
    hooks.terminal_tail_observation_attempted = True
    try:
        if _observe_closed_producer_terminal(hooks, meter):
            reason = (
                _status_min(
                    _c_failure_status(reason),
                    "RESOURCE_INCOMPLETE_NO_DECISION",
                )
                if reason in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )
        hooks.terminal_tail_extended = True
    except BaseException as error:
        hooks.terminal_closure_valid = False
        candidate = (
            error.status
            if isinstance(error, SupervisorFailure)
            else "RESOURCE_INCOMPLETE_NO_DECISION"
            if isinstance(error, (KeyboardInterrupt, SystemExit))
            else "IMPLEMENTATION_INVALID"
        )
        candidate = _c_failure_status(candidate)
        if candidate == "RESOURCE_INCOMPLETE_NO_DECISION":
            hooks.resource_incomplete = True
        reason = (
            _status_min(_c_failure_status(reason), merged_known_status(candidate))
            if reason in STATUS_ORDER
            else merged_known_status(candidate)
        )
    try:
        terminal_interrupted = hooks.observe_terminal_closure()
    except BaseException as error:
        hooks.terminal_closure_valid = False
        candidate = (
            error.status
            if isinstance(error, SupervisorFailure)
            else "RESOURCE_INCOMPLETE_NO_DECISION"
            if isinstance(error, (KeyboardInterrupt, SystemExit))
            else "IMPLEMENTATION_INVALID"
        )
        candidate = _c_failure_status(candidate)
        if candidate == "RESOURCE_INCOMPLETE_NO_DECISION":
            hooks.resource_incomplete = True
        reason = (
            _status_min(_c_failure_status(reason), merged_known_status(candidate))
            if reason in STATUS_ORDER
            else merged_known_status(candidate)
        )
        terminal_interrupted = False
    if terminal_interrupted:
        reason = (
            _status_min(
                _c_failure_status(reason),
                "RESOURCE_INCOMPLETE_NO_DECISION",
            )
            if reason in STATUS_ORDER
            else "RESOURCE_INCOMPLETE_NO_DECISION"
        )
    receipt["exit_reason"] = reason
    return reason, hooks.resource_incomplete, hooks.terminal_closure_valid


def _commit_producer_root_and_handoff(
    hooks: SupervisorHooks,
    meter: InstrumentMeter,
    high_status: str | None,
    preexisting_failure: str | None,
    preexisting_details: Sequence[str],
) -> tuple[_EmitHandoffOwner, str, bool]:
    """Commit the final C boundary, validate it, and transfer ownership to E."""

    def merged_known_status(candidate: str) -> str:
        merged = _c_failure_status(candidate)
        for existing in (
            high_status,
            preexisting_failure,
            hooks.terminal_known_status,
        ):
            if existing in STATUS_ORDER:
                merged = _status_min(merged, _c_failure_status(existing))
        if (
            hooks.terminal_receipt_index is not None
            and hooks.terminal_receipt_index == len(meter.receipts) - 1
        ):
            existing = str(meter.receipts[hooks.terminal_receipt_index]["exit_reason"])
            if existing in STATUS_ORDER:
                merged = _status_min(merged, _c_failure_status(existing))
        return merged

    try:
        hooks.begin_terminal_closure()
    except BaseException as error:
        hooks.terminal_closure_valid = False
        _fail(
            merged_known_status(
                error.status
                if isinstance(error, SupervisorFailure)
                else "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID"
            ),
            f"cannot enter C final root closure: {error}",
        )
    if (
        not hooks.terminal_finalized
        or hooks.terminal_receipt_index is None
        or hooks.terminal_receipt_index != len(meter.receipts) - 1
        or not hooks.terminal_tail_extended
    ):
        hooks.terminal_closure_valid = False
        _fail(
            merged_known_status("IMPLEMENTATION_INVALID"),
            "C root extension lacks a sealed receipt",
        )
    receipt = meter.receipts[hooks.terminal_receipt_index]
    reason = str(receipt["exit_reason"])
    if hooks.terminal_root_extension_attempted:
        _fail(
            merged_known_status("IMPLEMENTATION_INVALID"),
            "C root handoff was attempted twice",
        )
    hooks.terminal_root_extension_attempted = True

    def merge_resource() -> None:
        nonlocal reason
        if hooks.resource_incomplete:
            reason = (
                _status_min(
                    _c_failure_status(reason),
                    "RESOURCE_INCOMPLETE_NO_DECISION",
                )
                if reason in STATUS_ORDER
                else "RESOURCE_INCOMPLETE_NO_DECISION"
            )

    def validate_final_state() -> tuple[str | None, list[str]]:
        status = (
            _c_failure_status(preexisting_failure)
            if preexisting_failure is not None
            else None
        )
        details = list(preexisting_details)

        def record(candidate: str, detail: str) -> None:
            nonlocal status
            status = _status_min(status, _c_failure_status(candidate))
            details.append(detail)

        if not hooks.terminal_closure_valid:
            record(
                high_status or "IMPLEMENTATION_INVALID",
                "C terminal closure is incomplete at root commit",
            )
        if hooks.publication_became_visible and (
            receipt.get("phase") != "C_bundle_io"
            or receipt.get("completed_unit_index") != 395
            or reason != "PHASE_COMPLETE"
            or receipt.get("staging_disposition") != "ATOMICALLY_PUBLISHED"
        ):
            record(
                "ARTIFACT_INVALID",
                "visible bundle lacks the final exact U395 C receipt",
            )
        effective_high = high_status
        if reason in STATUS_ORDER:
            effective_high = _status_min(
                effective_high,
                _c_failure_status(reason),
            )
        if (
            hooks.resource_incomplete
            and effective_high
            in {"ARTIFACT_INVALID", "IMPLEMENTATION_INVALID", "CONTROL_INVALID"}
        ):
            record(
                effective_high,
                "final C root commit exposed a compound failure",
            )
        return status, details

    try:
        preliminary = _snapshot()
        hooks.observe_terminal_resources(preliminary)
        hooks.observe_terminal_closure()
        merge_resource()
        receipt["exit_reason"] = reason
        # Perform all status/visibility/compound validation before the final
        # snapshot.  A cap that first crosses at that snapshot is monotone and
        # is reclassified once below; no further scientific work follows.
        preliminary_reason = reason
        preliminary_resource = hooks.resource_incomplete
        preliminary_validation = validate_final_state()
        final_snapshot = _snapshot()
        hooks.observe_terminal_resources(final_snapshot)
        hooks.observe_terminal_closure()
        merge_resource()
        meter.extend_closed_terminal(final_snapshot)
        hooks.terminal_root_extended = True
    except BaseException as error:
        hooks.terminal_closure_valid = False
        candidate = (
            error.status
            if isinstance(error, SupervisorFailure)
            else "RESOURCE_INCOMPLETE_NO_DECISION"
            if isinstance(error, (KeyboardInterrupt, SystemExit))
            else "IMPLEMENTATION_INVALID"
        )
        candidate = _c_failure_status(candidate)
        if candidate == "RESOURCE_INCOMPLETE_NO_DECISION":
            hooks.resource_incomplete = True
        reason = (
            _status_min(_c_failure_status(reason), candidate)
            if reason in STATUS_ORDER
            else candidate
        )
        receipt["exit_reason"] = reason
        _fail(
            merged_known_status(reason),
            f"C final root observation failed: {error}",
        )
    receipt["exit_reason"] = reason
    failure_status, failure_details = (
        preliminary_validation
        if reason == preliminary_reason
        and hooks.resource_incomplete == preliminary_resource
        else validate_final_state()
    )
    if failure_status is not None:
        _fail(failure_status, "; ".join(failure_details))
    handoff_owner = hooks.detach_terminal_mask_for_emit()
    return handoff_owner, reason, hooks.resource_incomplete


def _phase_resource_objects(receipts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for phase in PHASE_ORDER:
        selected = [item for item in receipts if item["phase"] == phase]
        if not selected:
            result.append(
                {
                    "attempt_count": 0,
                    "cpu_microseconds": 0,
                    "peak_rss_bytes": 0,
                    "peak_rss_scope": "unstarted",
                    "phase": phase,
                    "started": False,
                    "wall_nanoseconds": 0,
                }
            )
            continue
        result.append(
            {
                "attempt_count": len(selected),
                "cpu_microseconds": sum(item["cpu_microseconds"] for item in selected),
                "peak_rss_bytes": max(item["peak_rss_bytes"] for item in selected),
                "peak_rss_scope": (
                    "shared_cumulative_producer"
                    if phase in {"C_setup", "C_core", "C_bundle_io"}
                    else "phase_process_family"
                ),
                "phase": phase,
                "started": True,
                "wall_nanoseconds": sum(item["wall_nanoseconds"] for item in selected),
            }
        )
    return result


def _identity_from_payload(
    path: str, payload: bytes, phase: str, role: str, schema: str
) -> dict[str, Any]:
    return {
        "path": path,
        "producing_phase": phase,
        "role": role,
        "schema": schema,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _resolve_final_status(
    high_status: str | None,
    state: producer.ProducerState,
    verification_status: str,
    cap_crossed: bool,
) -> str:
    if high_status is not None:
        return high_status
    if verification_status != "VERIFIED":
        return "VERIFICATION_INVALID"
    if not state.representation_valid:
        return "NO_GO_REPRESENTATION"
    if cap_crossed:
        return "NO_GO_SYNTHETIC_INSTRUMENT_COST"
    if state.full_shape_complete:
        return "PASS_SYNTHETIC_INSTRUMENT_GATE_ONLY"
    return "RESOURCE_INCOMPLETE_NO_DECISION"


def _run_srun(start_cpu: int, start_wall: int, artifact_root_argument: str) -> int:
    root = Path(artifact_root_argument).resolve(strict=True)
    if not root.is_dir() or any(root.iterdir()):
        raise PreconditionFailure("artifact root must be an existing empty directory")
    _require_control_descriptors_free()
    _require_supervisor_sigint_contract()
    byte_ledger = ByteLedger()
    meter = InstrumentMeter(start_cpu, start_wall, byte_ledger, tuple(sys.argv))
    # Git/source/PAR reads launch only non-capable git helpers.  The frozen
    # process/memory/filesystem snapshot is completed before the first capable
    # A4 native is launched for its sealed manifest.
    commit, repository_url, source_tree, implementation_manifest_payload = (
        _git_source_identity()
    )
    (
        par_receipts,
        par_byte_entries,
        par_seal,
        par_review_binding,
    ) = _load_par_seal(commit, source_tree, implementation_manifest_payload)
    byte_ledger.bind_sealed_research_evidence(
        sum(item["research_evidence_archive_bytes"] for item in par_byte_entries)
    )
    observed_utc = _utc_now()
    inventory = _process_inventory()
    prelaunch, self_start = _prelaunch_observation(
        root,
        {"environment_sha256": "0" * 64},
        inventory,
        observed_utc,
    )
    native_manifest = _native_manifest()
    environment_identity = _environment_identity(native_manifest)
    prelaunch["environment_identity_sha256"] = environment_identity["environment_sha256"]
    logical_preimage = {
        "execution_commit": commit,
        "outer_argv": list(sys.argv),
        "output_root": str(root),
        "preflight_pid": os.getpid(),
        "preflight_start_time_clock_ticks": self_start,
        "prelaunch_utc": prelaunch["observed_utc"],
        "protocol_version": producer.PROTOCOL_VERSION,
    }
    logical_run_id = _sha256(evidence.canonical_body(logical_preimage))
    meter.configure(logical_run_id, commit, environment_identity["environment_sha256"])
    sealed_cpu = sum(item["cpu_microseconds"] for item in par_receipts)
    protocol_identity = _document_identity(PROTOCOL_PATH)
    schema_identity = _document_identity(SCHEMA_PATH)
    if (
        protocol_identity["sha256"] != par_seal["protocol"]["sha256"]
        or protocol_identity["size_bytes"] != par_seal["protocol"]["size_bytes"]
        or schema_identity["sha256"] != par_seal["schema"]["sha256"]
        or schema_identity["size_bytes"] != par_seal["schema"]["size_bytes"]
    ):
        _fail("IMPLEMENTATION_INVALID", "runtime normative documents differ from PAR seal")
    producer_binary_identity = _file_identity(
        PRODUCER_NATIVE,
        "build/a4_v2/a4_v2_native",
        "B_build",
        "producer_native",
        "ELF",
    )
    if (
        producer_binary_identity["sha256"] != par_seal["producer_native"]["sha256"]
        or producer_binary_identity["size_bytes"]
        != par_seal["producer_native"]["size_bytes"]
    ):
        _fail("IMPLEMENTATION_INVALID", "producer binary differs from PAR seal")
    emit_context_base = {
        "binary_identity": producer_binary_identity,
        "command_identity": {"argv": list(sys.argv), "argv_sha256": meter.argv_sha256},
        "environment_identity": environment_identity,
        "prelaunch_observation": prelaunch,
        "protocol_identity": protocol_identity,
        "schema_identity": schema_identity,
        "source_identity": {
            "clean_tree": True,
            "execution_commit": commit,
            "repository_url": repository_url,
            "source_tree_sha256": source_tree,
        },
    }

    state: producer.ProducerState | None = None
    hooks: SupervisorHooks | None = None
    high_status: str | None = None
    resource_incomplete_observed = False
    interruption_count = 0
    cap_crossed = False
    fatal_visible_publication: str | None = None
    c_terminal_cleanup_complete = True
    c_release_interrupted = False
    c_release_status: str | None = None
    retry_release_hooks: SupervisorHooks | None = None

    def enter_c_handler_terminal(
        owner: SupervisorHooks,
        known_status: str | None,
        context: str,
    ) -> None:
        if known_status is not None:
            known_status = _c_failure_status(known_status)
            owner.terminal_known_status = _status_min(
                owner.terminal_known_status,
                known_status,
            )
            if known_status == "RESOURCE_INCOMPLETE_NO_DECISION":
                owner.resource_incomplete = True
        try:
            owner.begin_terminal_closure()
        except BaseException as closure_error:
            candidate = (
                closure_error.status
                if isinstance(closure_error, SupervisorFailure)
                else "RESOURCE_INCOMPLETE_NO_DECISION"
                if isinstance(closure_error, (KeyboardInterrupt, SystemExit))
                else "IMPLEMENTATION_INVALID"
            )
            candidate = _c_failure_status(candidate)
            if candidate == "RESOURCE_INCOMPLETE_NO_DECISION":
                owner.resource_incomplete = True
            _fail(
                _status_min(owner.terminal_known_status, candidate),
                f"cannot enter C terminal handler for {context}: {closure_error}",
            )

    producer_descriptor = os.open(
        PRODUCER_NATIVE, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    )
    _reserve_fixed_descriptor(producer_descriptor, 197)
    for attempt in range(2):
        attempt_root = root / "attempt.staging"
        next_hooks = SupervisorHooks(
            attempt,
            attempt_root,
            meter,
            byte_ledger,
            sealed_cpu,
        )
        hooks = next_hooks
        try:
            if retry_release_hooks is not None:
                prior_hooks = retry_release_hooks
                hooks = next_hooks
                try:
                    retry_release_interrupted = (
                        prior_hooks.release_terminal_closure()
                    )
                except BaseException as release_error:
                    hooks = prior_hooks
                    c_release_interrupted = True
                    release_status = (
                        release_error.status
                        if isinstance(release_error, SupervisorFailure)
                        else "RESOURCE_INCOMPLETE_NO_DECISION"
                        if isinstance(release_error, (KeyboardInterrupt, SystemExit))
                        else "IMPLEMENTATION_INVALID"
                    )
                    release_status = _c_failure_status(release_status)
                    enter_c_handler_terminal(
                        prior_hooks,
                        release_status,
                        "retry release failure",
                    )
                    c_release_status = _status_min(
                        c_release_status,
                        release_status,
                    )
                    if release_status == "RESOURCE_INCOMPLETE_NO_DECISION":
                        resource_incomplete_observed = True
                    high_status = _status_min(high_status, release_status)
                    state = prior_hooks.last_state
                    _finalize_producer_attempt(
                        hooks=prior_hooks,
                        meter=meter,
                        artifact_root=root,
                        attempt_root=attempt_root,
                        byte_ledger=byte_ledger,
                        reason=release_status,
                        disposition=prior_hooks.terminal_disposition,
                    )
                    break
                if retry_release_interrupted:
                    hooks = prior_hooks
                    c_release_interrupted = True
                    c_release_status = _status_min(
                        c_release_status,
                        "RESOURCE_INCOMPLETE_NO_DECISION",
                    )
                    resource_incomplete_observed = True
                    high_status = _status_min(
                        high_status,
                        "RESOURCE_INCOMPLETE_NO_DECISION",
                    )
                    _finalize_producer_attempt(
                        hooks=prior_hooks,
                        meter=meter,
                        artifact_root=root,
                        attempt_root=attempt_root,
                        byte_ledger=byte_ledger,
                        reason="RESOURCE_INCOMPLETE_NO_DECISION",
                        disposition=prior_hooks.terminal_disposition,
                    )
                    break
                retry_release_hooks = None
            attempt_root.mkdir()
            state = producer.run_attempt(hooks, root)
            cap_crossed = hooks.cap_crossed
            terminal_reason = (
                "PHASE_COMPLETE"
                if state.full_shape_complete
                else "PRIMARY_CAP_STOP"
                if hooks.cap_crossed
                else "REPRESENTATION_STOP"
                if hooks.representation_stop
                else "PHASE_COMPLETE"
            )
            (
                closed_reason,
                terminal_resource,
                _,
                c_terminal_cleanup_complete,
            ) = _finalize_producer_attempt(
                hooks=hooks,
                meter=meter,
                artifact_root=root,
                attempt_root=attempt_root,
                byte_ledger=byte_ledger,
                reason=terminal_reason,
                disposition=(
                    "ATOMICALLY_PUBLISHED" if state.bundle is not None else "NONE"
                ),
            )
            if closed_reason in STATUS_ORDER:
                high_status = _status_min(high_status, closed_reason)
            if terminal_resource:
                resource_incomplete_observed = True
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
            break
        except ExternalInterruption:
            enter_c_handler_terminal(hooks, None, "external interruption")
            interruption_count += 1
            state = hooks.last_state
            (
                closed_reason,
                terminal_resource,
                observed_disposition,
                c_terminal_cleanup_complete,
            ) = (
                _finalize_producer_attempt(
                    hooks=hooks,
                    meter=meter,
                    artifact_root=root,
                    attempt_root=attempt_root,
                    byte_ledger=byte_ledger,
                    reason=(
                        "RESOURCE_INCOMPLETE_NO_DECISION"
                        if interruption_count >= 2
                        else "EXTERNAL_INTERRUPTION"
                    ),
                    disposition="DISCARDED",
                )
            )
            if closed_reason in STATUS_ORDER:
                high_status = _status_min(high_status, closed_reason)
            if terminal_resource:
                resource_incomplete_observed = True
            if (
                closed_reason != "EXTERNAL_INTERRUPTION"
                or observed_disposition != "DISCARDED"
            ):
                break
            if interruption_count >= 2:
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
                resource_incomplete_observed = True
                break
            (
                closed_reason,
                terminal_resource,
                c_terminal_cleanup_complete,
            ) = _seal_producer_terminal_tail(hooks, meter)
            if closed_reason in STATUS_ORDER:
                high_status = _status_min(high_status, closed_reason)
            if terminal_resource:
                resource_incomplete_observed = True
            if (
                not c_terminal_cleanup_complete
                or closed_reason != "EXTERNAL_INTERRUPTION"
                or observed_disposition != "DISCARDED"
                or terminal_resource
            ):
                break
            meter.begin_retry()
            retry_release_hooks = hooks
            continue
        except producer.ProducerFailure as error:
            producer_status = _c_failure_status(error.status)
            enter_c_handler_terminal(hooks, producer_status, "producer failure")
            state = hooks.last_state
            publication_visible = (
                isinstance(error, producer.BundlePublicationVisibleFailure)
                or hooks.publication_became_visible
            )
            high_status = _status_min(high_status, producer_status)
            if producer_status == "RESOURCE_INCOMPLETE_NO_DECISION":
                resource_incomplete_observed = True
            (
                closed_reason,
                terminal_resource,
                _,
                c_terminal_cleanup_complete,
            ) = _finalize_producer_attempt(
                hooks=hooks,
                meter=meter,
                artifact_root=root,
                attempt_root=attempt_root,
                byte_ledger=byte_ledger,
                reason=producer_status,
                disposition=(
                    "ATOMICALLY_PUBLISHED" if publication_visible else "DISCARDED"
                ),
            )
            if closed_reason in STATUS_ORDER:
                high_status = _status_min(high_status, closed_reason)
            if terminal_resource:
                resource_incomplete_observed = True
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
            if publication_visible:
                fatal_visible_publication = error.detail
            break
        except SupervisorFailure as error:
            supervisor_status = _c_failure_status(error.status)
            enter_c_handler_terminal(hooks, supervisor_status, "supervisor failure")
            state = hooks.last_state
            publication_visible = hooks.publication_became_visible
            high_status = _status_min(high_status, supervisor_status)
            # ByteLedger ceilings raise directly rather than through
            # SupervisorHooks._operational_check(), so preserve their
            # resource-incomplete result independently of the terminal
            # CPU/wall/RSS sample below.
            if supervisor_status == "RESOURCE_INCOMPLETE_NO_DECISION":
                resource_incomplete_observed = True
            (
                closed_reason,
                terminal_resource,
                _,
                c_terminal_cleanup_complete,
            ) = _finalize_producer_attempt(
                hooks=hooks,
                meter=meter,
                artifact_root=root,
                attempt_root=attempt_root,
                byte_ledger=byte_ledger,
                reason=supervisor_status,
                disposition=(
                    "ATOMICALLY_PUBLISHED" if publication_visible else "DISCARDED"
                ),
            )
            if closed_reason in STATUS_ORDER:
                high_status = _status_min(high_status, closed_reason)
            if terminal_resource:
                resource_incomplete_observed = True
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
            if publication_visible:
                fatal_visible_publication = error.detail
            break
        except (KeyboardInterrupt, SystemExit) as error:
            enter_c_handler_terminal(
                hooks,
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "supervisor interruption",
            )
            state = hooks.last_state
            publication_visible = hooks.publication_became_visible
            high_status = _status_min(
                high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
            )
            resource_incomplete_observed = True
            (
                closed_reason,
                terminal_resource,
                _,
                c_terminal_cleanup_complete,
            ) = _finalize_producer_attempt(
                hooks=hooks,
                meter=meter,
                artifact_root=root,
                attempt_root=attempt_root,
                byte_ledger=byte_ledger,
                reason="RESOURCE_INCOMPLETE_NO_DECISION",
                disposition=(
                    "ATOMICALLY_PUBLISHED" if publication_visible else "DISCARDED"
                ),
            )
            if closed_reason in STATUS_ORDER:
                high_status = _status_min(high_status, closed_reason)
            if terminal_resource:
                resource_incomplete_observed = True
            if publication_visible:
                fatal_visible_publication = str(error)
            break
        except BaseException as error:
            enter_c_handler_terminal(
                hooks,
                "IMPLEMENTATION_INVALID",
                "untyped implementation failure",
            )
            state = hooks.last_state
            publication_visible = hooks.publication_became_visible
            high_status = _status_min(high_status, "IMPLEMENTATION_INVALID")
            (
                closed_reason,
                terminal_resource,
                _,
                c_terminal_cleanup_complete,
            ) = _finalize_producer_attempt(
                hooks=hooks,
                meter=meter,
                artifact_root=root,
                attempt_root=attempt_root,
                byte_ledger=byte_ledger,
                reason="IMPLEMENTATION_INVALID",
                disposition=(
                    "ATOMICALLY_PUBLISHED" if publication_visible else "DISCARDED"
                ),
            )
            if closed_reason in STATUS_ORDER:
                high_status = _status_min(high_status, closed_reason)
            if terminal_resource:
                resource_incomplete_observed = True
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
            print(f"A4-V2 implementation failure: {error}", file=sys.stderr)
            if publication_visible:
                fatal_visible_publication = str(error)
            break
    c_root_status: str | None = None
    c_root_details: list[str] = []

    def record_c_root_failure(status: str, detail: str) -> None:
        nonlocal c_root_status
        resolved = _c_failure_status(status)
        c_root_status = _status_min(c_root_status, resolved)
        c_root_details.append(detail)

    try:
        os.close(197)
    except OSError as error:
        record_c_root_failure(
            "IMPLEMENTATION_INVALID",
            f"cannot close frozen producer descriptor: {error}",
        )
    if (
        hooks is not None
        and hooks.publication_became_visible
        and (
            state is None
            or state.last_completed_unit_index != 395
            or state.bundle is None
        )
    ):
        fatal_visible_publication = (
            fatal_visible_publication
            or "independent no-follow target probe observed bundle before U395"
        )
    if fatal_visible_publication is not None:
        record_c_root_failure(
            "ARTIFACT_INVALID",
            "bundle target is physically visible but U395 was not admitted; "
            f"downstream observation is forbidden: {fatal_visible_publication}",
        )
    if not c_terminal_cleanup_complete:
        record_c_root_failure(
            high_status or "IMPLEMENTATION_INVALID",
            "C terminal staging could not be proven absent; downstream observation "
            "is forbidden",
        )
    if hooks is None:
        record_c_root_failure(
            "IMPLEMENTATION_INVALID",
            "C terminal hooks were not constructed",
        )
    else:
        (
            closed_reason,
            terminal_resource,
            c_terminal_cleanup_complete,
        ) = _seal_producer_terminal_tail(hooks, meter)
        if closed_reason in STATUS_ORDER:
            high_status = _status_min(high_status, closed_reason)
        if terminal_resource:
            resource_incomplete_observed = True
        if not c_terminal_cleanup_complete:
            record_c_root_failure(
                high_status or "IMPLEMENTATION_INVALID",
                "C terminal tail could not be completely observed",
            )
        if hooks.terminal_receipt_index is None:
            record_c_root_failure(
                "IMPLEMENTATION_INVALID",
                "C terminal receipt index is absent",
            )
        else:
            c_receipt = meter.receipts[hooks.terminal_receipt_index]
            if hooks.publication_became_visible and (
                c_receipt.get("phase") != "C_bundle_io"
                or c_receipt.get("completed_unit_index") != 395
                or c_receipt.get("exit_reason") != "PHASE_COMPLETE"
                or c_receipt.get("staging_disposition")
                != "ATOMICALLY_PUBLISHED"
            ):
                record_c_root_failure(
                    "ARTIFACT_INVALID",
                    "visible bundle lacks the exact U395 C_bundle_io/"
                    "PHASE_COMPLETE/ATOMICALLY_PUBLISHED receipt",
                )
    if (
        resource_incomplete_observed
        and high_status
        in {"ARTIFACT_INVALID", "IMPLEMENTATION_INVALID", "CONTROL_INVALID"}
    ):
        record_c_root_failure(
            high_status,
            "compound C failure is fail-stop before E/V/archive because the frozen "
            "single-axis receipt cannot independently encode a hidden resource bit",
        )
    if state is None or state.input_identity is None:
        record_c_root_failure(
            _status_min(high_status, "EVIDENCE_INCOMPLETE_NO_DECISION"),
            "no complete U000 prefix is available",
        )
    if c_release_interrupted:
        record_c_root_failure(
            c_release_status or "RESOURCE_INCOMPLETE_NO_DECISION",
            "C retry release was interrupted",
        )
    if hooks is None:
        _fail("IMPLEMENTATION_INVALID", "C terminal hooks are absent at release")
    if c_release_interrupted:
        _fail(
            c_root_status or c_release_status or "RESOURCE_INCOMPLETE_NO_DECISION",
            "; ".join(c_root_details) or "C retry release failed",
        )
    (
        emit_handoff_owner,
        closed_reason,
        terminal_resource,
    ) = _commit_producer_root_and_handoff(
        hooks,
        meter,
        high_status,
        c_root_status,
        c_root_details,
    )
    try:
        if closed_reason in STATUS_ORDER:
            high_status = _status_min(high_status, closed_reason)
        if terminal_resource:
            resource_incomplete_observed = True
        emit_start = meter.boundary.snapshot
        emit_start_utc = meter.boundary.utc
        byte_ledger.switch("E_emit")
        emit_receipts, t_instrument, emit_boundary = _run_preserving_prior_status(
            high_status,
            lambda: _emit_in_inherited_process(
                state=state,
                artifact_root=root,
                context_base=emit_context_base,
                raw_instrument_receipts=(*par_receipts, *meter.receipts),
                byte_ledger=byte_ledger,
                checkpoint_start=emit_start,
                checkpoint_utc=emit_start_utc,
                sealed_cpu=sealed_cpu,
                logical_run_id=logical_run_id,
                commit=commit,
                environment_sha=environment_identity["environment_sha256"],
                handoff_owner=emit_handoff_owner,
            ),
        )
    except BaseException as error:
        _restore_emit_handoff_after_error(emit_handoff_owner, error)
        raise
    instrument_receipts = _sorted_receipts((*par_receipts, *meter.receipts))
    cap_crossed = cap_crossed or t_instrument > PRIMARY_CAP

    receipts_before_verifier = _sorted_receipts(
        (*instrument_receipts, *emit_receipts)
    )
    bytes_before_verifier = byte_ledger.objects(par_byte_entries)
    prior_research_evidence = sum(
        item["research_evidence_archive_bytes"] for item in bytes_before_verifier
    )
    expected_native_argv = ["/proc/self/fd/197", "verify-canonical-request"]

    def validate_verifier_success(
        response: Mapping[str, Any],
        verifier_summary_payload: bytes,
        verifier_summary: Mapping[str, Any],
    ) -> None:
        verification_status = str(verifier_summary.get("status"))
        if set(response) != {
            "native_binary_sha256",
            "native_binary_size_bytes",
            "native_child_argv",
            "native_child_argv_sha256",
            "status",
            "verifier_summary_sha256",
            "verifier_summary_size_bytes",
        } or (
            response["native_binary_sha256"]
            != par_seal["verifier_native"]["sha256"]
            or response["native_binary_size_bytes"]
            != par_seal["verifier_native"]["size_bytes"]
            or response["native_child_argv"] != expected_native_argv
            or response["native_child_argv_sha256"]
            != _sha256(evidence.canonical_body(expected_native_argv))
            or response["status"] != verification_status
            or response["verifier_summary_sha256"]
            != _sha256(verifier_summary_payload)
            or response["verifier_summary_size_bytes"]
            != len(verifier_summary_payload)
        ):
            _fail(
                "IMPLEMENTATION_INVALID",
                "verifier response identity/status mismatch",
            )

    (
        verifier_receipts,
        _verifier_response_payload,
        verifier_payload,
        verifier_response,
        verifier_summary,
        verifier_boundary,
    ) = _run_preserving_prior_status(
        high_status,
        lambda: _external_wrapper(
            phase="V_replay",
            argv=(
                sys.executable,
                str(VERIFIER_WRAPPER),
                "verify-canonical-request",
                "--control-fd",
                "198",
            ),
            control_factory=lambda start_utc, start_monotonic, prior_attempts: {
                "artifact_root": str(root),
                "build_manifest": _sealed_read_request(par_seal["build_manifest"]),
                "logical_run_id": logical_run_id,
                "native_verifier": _sealed_read_request(par_seal["verifier_native"]),
                "par_review_binding": _sealed_read_request(par_review_binding),
                "phase_start_monotonic_ns": start_monotonic,
                "prior_phase_receipts": _sorted_receipts(
                    (*receipts_before_verifier, *prior_attempts)
                ),
                "prior_research_evidence_bytes": prior_research_evidence,
                "prior_study_cpu_microseconds": sum(
                    item["cpu_microseconds"]
                    for item in (*receipts_before_verifier, *prior_attempts)
                ),
                "protocol": _sealed_read_request(par_seal["protocol"]),
                "schema": _sealed_read_request(par_seal["schema"]),
                "source_manifest": _sealed_read_request(par_seal["source_manifest"]),
                "start_utc": start_utc,
            },
            artifact_root=root,
            published_directory="verifier",
            published_file="verifier/verifier_summary.json",
            completed_unit=state.last_completed_unit_index,
            logical_run_id=logical_run_id,
            commit=commit,
            environment_sha=environment_identity["environment_sha256"],
            bytes_=byte_ledger,
            initial_boundary=emit_boundary,
            prior_study_cpu_microseconds=sum(
                item["cpu_microseconds"] for item in receipts_before_verifier
            ),
            success_validator=validate_verifier_success,
        ),
    )
    verification_status = str(verifier_summary.get("status"))

    receipts_through_verifier = _sorted_receipts(
        (*instrument_receipts, *emit_receipts, *verifier_receipts)
    )
    if (
        sum(item["cpu_microseconds"] for item in receipts_through_verifier)
        > STUDY_CPU_LIMIT
    ):
        resource_incomplete_observed = True
        high_status = _status_min(high_status, "RESOURCE_INCOMPLETE_NO_DECISION")
    archive_status_inputs = {
        "artifact_valid": high_status != "ARTIFACT_INVALID",
        "control_valid": high_status != "CONTROL_INVALID" and state.control_valid,
        "full_shape_complete": state.full_shape_complete,
        "implementation_valid": high_status != "IMPLEMENTATION_INVALID",
        "primary_cap_pass": t_instrument <= PRIMARY_CAP,
        "producer_evidence_complete": True,
        "representation_valid": state.representation_valid,
        "resource_complete_through_verifier": not resource_incomplete_observed,
        "verification_pass": verification_status == "VERIFIED",
        "verifier_summary_complete": True,
    }
    bytes_through_verifier = byte_ledger.objects(par_byte_entries)
    prior_research_evidence = sum(
        item["research_evidence_archive_bytes"] for item in bytes_through_verifier
    )
    prior_study_cpu = sum(item["cpu_microseconds"] for item in receipts_through_verifier)

    def archive_control(
        start_utc: str,
        start_monotonic: int,
        prior_archive_attempts: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        return {
            "archive_start_checkpoint": {
                "completed_unit_count": state.completed_unit_count,
                "last_completed_unit_index": state.last_completed_unit_index,
                "logical_run_id": logical_run_id,
                "pretrailer_file_count": _input_file_count(state, True) + 1,
                "start_utc": start_utc,
            },
            "artifact_root": str(root),
            "attempt_ledger": _chronological_receipts(receipts_through_verifier),
            "gate_operands": {
                "cap_crossed": t_instrument > PRIMARY_CAP,
                "completed_unit_count": state.completed_unit_count,
                "full_shape_complete": state.full_shape_complete,
                "last_completed_unit_index": state.last_completed_unit_index,
                "primary_cpu_cap_microseconds": PRIMARY_CAP,
                "t_instrument_cpu_microseconds": t_instrument,
            },
            "phase_receipts_through_verifier": receipts_through_verifier,
            "phase_start_monotonic_ns": start_monotonic,
            "prior_archive_attempt_receipts": [
                dict(item) for item in prior_archive_attempts
            ],
            "prior_research_evidence_bytes": prior_research_evidence,
            "prior_study_cpu_microseconds": prior_study_cpu
            + sum(item["cpu_microseconds"] for item in prior_archive_attempts),
            "protocol": _sealed_read_request(par_seal["protocol"]),
            "resource_observation_through_verifier": {
                "intermediate_bundle_bytes": sum(
                    item["permanent_intermediate_bundle_bytes"]
                    for item in bytes_through_verifier
                ),
                "maximum_live_owned_temporary_bytes": max(
                    item["maximum_live_owned_temporary_bytes"]
                    for item in bytes_through_verifier
                ),
                "research_evidence_archive_bytes": prior_research_evidence,
            },
            "schema": _sealed_read_request(par_seal["schema"]),
            "sealed_phase_identities": _sealed_phase_identities(
                receipts_through_verifier
            ),
            "status_inputs": archive_status_inputs,
        }

    (
        archive_receipts,
        _archive_identity_response,
        _archive_payload,
        archive_identity_reply,
        archive_body,
        _archive_boundary,
    ) = _run_preserving_prior_status(
        high_status,
        lambda: _external_wrapper(
            phase="E_archive_body",
            argv=(
                sys.executable,
                str(ARCHIVE_WRAPPER),
                "publish-canonical-request",
                "--control-fd",
                "198",
                "--identity-pipe-fd",
                "199",
            ),
            control_factory=archive_control,
            artifact_root=root,
            published_directory="archive",
            published_file="archive/archive_body.json",
            completed_unit=state.last_completed_unit_index,
            logical_run_id=logical_run_id,
            commit=commit,
            environment_sha=environment_identity["environment_sha256"],
            bytes_=byte_ledger,
            initial_boundary=verifier_boundary,
            prior_study_cpu_microseconds=prior_study_cpu,
            response_pipe=True,
            allow_published_resource_return=True,
            post_cleanup_validator=lambda: _require_exact_final_input_tree(
                root, state.bundle is not None
            ),
        ),
    )
    all_receipts = _sorted_receipts((*receipts_through_verifier, *archive_receipts))

    final_status = _resolve_final_status(high_status, state, verification_status, cap_crossed)
    archive_identity = {
        "path": "archive/archive_body.json",
        "producing_phase": "E_archive_body",
        "role": "archive_body",
        "schema": "archive_body_v2",
        "sha256": archive_identity_reply["sha256"],
        "size_bytes": archive_identity_reply["size_bytes"],
    }
    phase_bytes = byte_ledger.objects(par_byte_entries)
    attribution = dict(meter.attribution)
    if sum(attribution.values()) != t_instrument:
        _fail_preserving_prior_status(
            final_status,
            "IMPLEMENTATION_INVALID",
            "instrument attribution does not reconcile",
        )
    phase_resources = _phase_resource_objects(all_receipts)
    t_study = sum(item["cpu_microseconds"] for item in all_receipts)
    byte_global = {
        "deleted_partial_bytes": sum(item["deleted_partial_bytes"] for item in phase_bytes),
        "intermediate_bundle_bytes": sum(
            item["permanent_intermediate_bundle_bytes"] for item in phase_bytes
        ),
        "maximum_live_owned_temporary_bytes": max(
            item["maximum_live_owned_temporary_bytes"] for item in phase_bytes
        ),
        "research_evidence_archive_bytes": sum(
            item["research_evidence_archive_bytes"] for item in phase_bytes
        ),
        "total_created_temporary_bytes": sum(
            item["created_temporary_bytes"] for item in phase_bytes
        ),
    }
    capped_phase_names = {
        "B_build",
        "P_parity",
        "E_emit",
        "V_replay",
        "E_archive_body",
    }
    resource_incomplete_through_archive = (
        resource_incomplete_observed
        or t_study > STUDY_CPU_LIMIT
        or byte_global["intermediate_bundle_bytes"] > BUNDLE_LIMIT
        or byte_global["maximum_live_owned_temporary_bytes"] > TEMPORARY_LIMIT
        or byte_global["research_evidence_archive_bytes"] > EVIDENCE_LIMIT
        or any(
            item["started"]
            and (
                item["peak_rss_bytes"] > RSS_LIMIT
                or (
                    item["phase"] in capped_phase_names
                    and (
                        item["cpu_microseconds"] > PER_PHASE_CPU_LIMIT
                        or item["wall_nanoseconds"] > PER_PHASE_WALL_LIMIT
                    )
                )
            )
            for item in phase_resources
        )
    )
    if resource_incomplete_through_archive:
        final_status = _status_min(
            final_status, "RESOURCE_INCOMPLETE_NO_DECISION"
        )
    resource_ledger = {
        "archive_body": archive_identity,
        "artifact_kind": "a4_resource_ledger",
        "byte_ledger": byte_global,
        "ceilings": {
            "intermediate_bundle_bytes": BUNDLE_LIMIT,
            "owned_live_temporary_bytes": TEMPORARY_LIMIT,
            "per_phase_cpu_microseconds": PER_PHASE_CPU_LIMIT,
            "per_phase_names": ["B_build", "P_parity", "E_emit", "V_replay", "E_archive_body"],
            "per_phase_wall_nanoseconds": PER_PHASE_WALL_LIMIT,
            "per_producer_attempt_cpu_microseconds": PER_ATTEMPT_CPU_LIMIT,
            "per_producer_attempt_wall_nanoseconds": PER_ATTEMPT_WALL_LIMIT,
            "producer_or_verifier_peak_rss_bytes": RSS_LIMIT,
            "research_evidence_archive_bytes": EVIDENCE_LIMIT,
            "t_study_metered_cpu_microseconds": STUDY_CPU_LIMIT,
        },
        "f_trailer_exclusion": list(evidence.FINAL_ORDER),
        "instrument_attribution_cpu_microseconds": attribution,
        "phase_attempt_receipts": all_receipts,
        "phase_byte_ledger": phase_bytes,
        "phase_resource_ledger": phase_resources,
        "schema_version": 1,
        "t_arbitrary_ready_conservative_cpu_microseconds": (
            attribution["C_setup"]
            + attribution["C_shared_fit"]
            + attribution["C_arm_arbitrary"]
            + attribution["C_interrupted_tail"]
        ),
        "t_instrument_cpu_microseconds": t_instrument,
        "t_study_metered_cpu_microseconds": t_study,
    }
    resource_payload = evidence.canonical_document(resource_ledger)
    resource_identity = _identity_from_payload(
        "final/resource_ledger.json",
        resource_payload,
        "F_trailer",
        "resource_ledger",
        "resource_ledger_v2",
    )
    decision_status_inputs = {
        "archive_complete": True,
        "artifact_index_required": True,
        "artifact_valid": archive_status_inputs["artifact_valid"],
        "control_valid": archive_status_inputs["control_valid"],
        "full_shape_complete": state.full_shape_complete,
        "implementation_valid": archive_status_inputs["implementation_valid"],
        "primary_cap_pass": t_instrument <= PRIMARY_CAP,
        "producer_evidence_complete": True,
        "representation_valid": state.representation_valid,
        "resource_complete_through_archive": not resource_incomplete_through_archive,
        "verification_pass": verification_status == "VERIFIED",
        "verifier_summary_complete": True,
    }
    decision = {
        "admissible_only_with_complete_artifact_index": True,
        "archive_body": archive_identity,
        "artifact_kind": "a4_decision",
        "claim_ceiling": CLAIM_CEILING,
        "completed_unit_count": state.completed_unit_count,
        "final_status": final_status,
        "full_shape_complete": state.full_shape_complete,
        "primary_cpu_cap_microseconds": PRIMARY_CAP,
        "protocol_identity": protocol_identity["sha256"],
        "resource_ledger": resource_identity,
        "schema_version": 1,
        "status_inputs": decision_status_inputs,
        "status_precedence": list(STATUS_ORDER),
        "t_instrument_cpu_microseconds": t_instrument,
    }
    decision_payload = evidence.canonical_document(decision)
    decision_identity = _identity_from_payload(
        "final/decision.json", decision_payload, "F_trailer", "decision", "decision_v2"
    )
    pretrailer = archive_body.get("pretrailer_files")
    if not isinstance(pretrailer, list):
        _fail_preserving_prior_status(
            final_status,
            "ARTIFACT_INVALID",
            "archive body lacks pretrailer file inventory",
        )
    index_files = [dict(item) for item in pretrailer]
    index_files.extend((archive_identity, resource_identity, decision_identity))
    index_files.sort(key=lambda item: item["path"].encode("utf-8"))
    if len({item["path"] for item in index_files}) != len(index_files):
        _fail_preserving_prior_status(
            final_status,
            "ARTIFACT_INVALID",
            "artifact-index paths are duplicated",
        )
    artifact_index = {
        "artifact_kind": "a4_artifact_index",
        "files": index_files,
        "producer_commit": commit,
        "schema_version": 1,
    }
    artifact_index_payload = evidence.canonical_document(artifact_index)
    _run_preserving_prior_status(
        final_status,
        lambda: evidence.publish_final_trailer(
            root, resource_payload, decision_payload, artifact_index_payload
        ),
    )
    # The final publisher is a direct-exit terminal operation.  If a defect
    # ever lets it return, do not execute a Python return path after rename.
    os._exit(3)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("srun", allow_abbrev=False)
    run.add_argument("artifact_root")
    parity = subparsers.add_parser("par", allow_abbrev=False)
    parity.add_argument("artifact_root")
    return parser


def main(start_cpu_microseconds: int, start_wall_nanoseconds: int) -> int:
    args = _parser().parse_args()
    try:
        if args.command == "srun":
            return _run_srun(
                start_cpu_microseconds, start_wall_nanoseconds, args.artifact_root
            )
        if args.command == "par":
            import a4_v2_parity  # Future separately authorized PAR stage only.

            try:
                return a4_v2_parity.run_par(
                    start_cpu_microseconds,
                    start_wall_nanoseconds,
                    args.artifact_root,
                    _snapshot,
                    _process_inventory,
                    _prelaunch_observation,
                )
            except a4_v2_parity.ParityFailure as error:
                print(f"IMPLEMENTATION_INVALID: {error}", file=sys.stderr)
                return 3
        raise PreconditionFailure("unsupported stage command")
    except PreconditionFailure as error:
        print(f"PRECONDITION_NOT_MET: {error}", file=sys.stderr)
        return 2
    except SupervisorFailure as error:
        print(f"{error.status}: {error.detail}", file=sys.stderr)
        return 3
    except evidence.EvidenceFailure as error:
        print(f"{error.status}: {error.detail}", file=sys.stderr)
        return 3
    except (KeyboardInterrupt, SystemExit):
        print(
            "RESOURCE_INCOMPLETE_NO_DECISION: supervisor interrupted outside a "
            "published terminal boundary",
            file=sys.stderr,
        )
        return 3
    except OSError as error:
        print(f"ARTIFACT_INVALID: {error}", file=sys.stderr)
        return 3
