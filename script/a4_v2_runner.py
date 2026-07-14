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
import hashlib
import importlib.metadata
import json
import os
import platform
import re
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
        "authorization_identity": "docs/saq_a4_v2_implementation_authorization_2026_07_14.md",
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
    current_leader_binary = _read_regular_nofollow(Path(sys.executable), 1 << 30)
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
        or leader_binary_sha256 != _sha256(current_leader_binary)
        or leader_binary_size_bytes != len(current_leader_binary)
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

    def switch(self, phase: str) -> None:
        self.phase = phase

    def _refresh_peak(self) -> None:
        live = sum(self.live.values())
        entry = self.entries[self.phase]
        entry.maximum_live = max(entry.maximum_live, live)
        if live > TEMPORARY_LIMIT:
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", "owned temporary-byte ceiling crossed")

    def note_created(self, path: Path) -> None:
        if path.is_dir():
            return
        try:
            size = path.stat().st_size
        except OSError as error:
            _fail("ARTIFACT_INVALID", f"cannot stat created temporary {path}: {error}")
        if path in self.live:
            _fail("IMPLEMENTATION_INVALID", f"temporary path counted twice: {path}")
        self.live[path] = size
        self.entries[self.phase].created += size
        self._refresh_peak()

    def note_deleted(self, path: Path) -> None:
        if path not in self.live:
            _fail("IMPLEMENTATION_INVALID", f"deleted temporary was not owned: {path}")
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
        if sum(item.evidence_archive for item in self.entries.values()) > EVIDENCE_LIMIT:
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", "evidence/archive byte ceiling crossed")

    def atomic_external_file(self, phase: str, byte_count: int) -> None:
        entry = self.entries[phase]
        entry.created += byte_count
        conservative_live = sum(self.live.values()) + byte_count
        entry.maximum_live = max(entry.maximum_live, conservative_live)
        if conservative_live > TEMPORARY_LIMIT:
            _fail(
                "RESOURCE_INCOMPLETE_NO_DECISION",
                "owned temporary-byte ceiling crossed at external publication",
            )
        entry.evidence_archive += byte_count
        if sum(item.evidence_archive for item in self.entries.values()) > EVIDENCE_LIMIT:
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
            or sum(item.evidence_archive for item in self.entries.values())
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

    def discard_tree(self, path: Path) -> None:
        total = 0
        if path.exists():
            for child in path.rglob("*"):
                if child.is_file():
                    size = child.stat().st_size
                    total += size
                    if child not in self.live:
                        self.entries[self.phase].created += size
        self.entries[self.phase].deleted_partial += total
        for child in tuple(self.live):
            if child == path or path in child.parents:
                del self.live[child]

    def admit_tree(self, path: Path) -> None:
        if not path.exists():
            return
        for child in path.rglob("*"):
            if child.is_file() and child not in self.live:
                size = child.stat().st_size
                self.live[child] = size
                self.entries[self.phase].created += size
        self._refresh_peak()

    def objects(self, sealed: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        if self.bundle_reservations:
            _fail("IMPLEMENTATION_INVALID", "unresolved bundle-byte reservation")
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
        self.binary_sha256 = _sha256(Path(sys.executable).read_bytes())
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
        self.attribution[owner_override or self.owner] += delta
        self.last_cpu = value.cpu_microseconds
        return value

    def _close(self, value: ResourceSnapshot, reason: str, disposition: str = "NONE") -> None:
        if not self.logical_run_id:
            _fail("IMPLEMENTATION_INVALID", "instrument meter closed before identity binding")
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

    def switch(self, phase: str, owner: str) -> None:
        value = self.sample()
        if phase != self.phase:
            self._close(value, "PHASE_COMPLETE")
            self.phase = phase
            self.phase_start_cpu = value.cpu_microseconds
            self.phase_start_wall = value.wall_nanoseconds
            self.phase_start_utc = self.boundary.utc
            self.bytes.switch(phase)
        self.owner = owner

    def checkpoint(self, unit_index: int) -> ResourceSnapshot:
        self.last_completed_unit = unit_index
        return self.sample()

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

    def instrument_cpu(self) -> int:
        return _snapshot().cpu_microseconds - self.start_cpu


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

    def switch(self, phase: str, owner: str) -> None:
        self.meter.switch(phase, owner)

    def invoke_native(self, arguments: Sequence[str]) -> None:
        argv = ("/proc/self/fd/197", *arguments)
        stderr_path = self.attempt_root / f"native_stderr_{self.child_count:03d}.log"
        self.child_count += 1
        self.meter.sample()
        with stderr_path.open("xb", buffering=0) as stderr_file:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=stderr_file,
                env=_child_environment(),
                pass_fds=(197,),
                close_fds=True,
            )
            result = _wait4_integer(process.pid)
            process.returncode = result.exit_code
            os.fsync(stderr_file.fileno())
        output_path = Path(arguments[-1])
        if output_path.exists():
            self.bytes.note_created(output_path)
        elif result.exit_code == 0:
            _fail("IMPLEMENTATION_INVALID", "successful native child omitted its output")
        self.bytes.note_created(stderr_path)
        detail = stderr_path.read_bytes()[:4096]
        stderr_path.unlink()
        self.bytes.note_deleted(stderr_path)
        if result.exit_code < 0:
            self.meter.sample("C_interrupted_tail")
            self.meter.owner = "C_interrupted_tail"
            raise ExternalInterruption(
                f"native child killed by signal {-result.exit_code}: {detail!r}"
            )
        self.meter.sample()
        if result.exit_code != 0:
            _fail("IMPLEMENTATION_INVALID", f"native child failed {result.exit_code}: {detail!r}")

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
        self.last_state = state
        value = self.meter.checkpoint(unit_index)
        self._operational_check(value)
        if self.meter.instrument_cpu() > PRIMARY_CAP:
            self.cap_crossed = True
            return True
        if not state.representation_valid:
            self.representation_stop = True
            return True
        return False

    def fail_unpublished_unit(self, status: str, detail: str) -> NoReturn:
        """Close a failed unit at the prior complete prefix, never at its index."""

        if status not in STATUS_ORDER or self.last_state is None:
            _fail("IMPLEMENTATION_INVALID", "invalid unpublished-unit failure")
        prior_index = self.last_state.last_completed_unit_index
        value = self.meter.checkpoint(prior_index)
        resource_error: SupervisorFailure | None = None
        try:
            self._operational_check(value)
        except SupervisorFailure as error:
            resource_error = error
        if self.meter.instrument_cpu() > PRIMARY_CAP:
            self.cap_crossed = True
        resolved_status = (
            _status_min(status, resource_error.status)
            if resource_error is not None
            else status
        )
        raise producer.ProducerFailure(
            resolved_status,
            detail
            if resource_error is None
            else f"{detail}; {resource_error.detail}",
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
        "peak_rss_bytes": child_usage.peak_rss_bytes,
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


def _require_control_descriptors_free() -> None:
    for descriptor in (197, 198, 199):
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        raise PreconditionFailure(f"frozen control descriptor {descriptor} is already open")


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
    response_pipe: bool = False,
) -> tuple[
    list[dict[str, Any]],
    bytes,
    bytes,
    Mapping[str, Any],
    Mapping[str, Any],
    PhaseBoundary,
]:
    """Launch a fixed-argv wrapper with canonical control on fd 198."""

    receipts: list[dict[str, Any]] = []
    fixed_argv = tuple(argv)
    boundary = initial_boundary
    for attempt in range(2):
        start = boundary.snapshot
        start_utc = boundary.utc
        receipt_binary_sha256 = _sha256(Path(sys.executable).read_bytes())
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
        with stdout_path.open("xb", buffering=0) as stdout_file, stderr_path.open(
            "xb", buffering=0
        ) as stderr_file:
            process = subprocess.Popen(
                fixed_argv,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                env=_child_environment(),
                pass_fds=pass_descriptors,
                close_fds=True,
            )
            os.close(198)
            if response_pipe:
                os.close(199)
            offset = 0
            while offset < len(control_payload):
                written = os.write(request_write, control_payload[offset:])
                if written <= 0:
                    _fail("EVIDENCE_INCOMPLETE_NO_DECISION", f"{phase} control short write")
                offset += written
            os.close(request_write)
            usage = _wait4_integer(process.pid)
            process.returncode = usage.exit_code
            os.fsync(stdout_file.fileno())
            os.fsync(stderr_file.fileno())
        response = b""
        if response_read is not None:
            while True:
                chunk = os.read(response_read, 1 << 20)
                if not chunk:
                    break
                response += chunk
                if len(response) > 1 << 20:
                    _fail("EVIDENCE_INCOMPLETE_NO_DECISION", f"{phase} response too large")
            os.close(response_read)
        stdout_payload = stdout_path.read_bytes()
        stderr_payload = stderr_path.read_bytes()
        bytes_.switch(phase)
        bytes_.note_created(stdout_path)
        bytes_.note_created(stderr_path)
        target = artifact_root / published_directory
        staging = artifact_root / f"{published_directory}.staging"
        output_payload = b""
        output_object: Mapping[str, Any] = {}
        if usage.exit_code == 0:
            output_path = artifact_root / published_file
            if not output_path.is_file():
                _fail("EVIDENCE_INCOMPLETE_NO_DECISION", f"{phase} omitted published output")
            output_payload = output_path.read_bytes()
            _sha256(output_payload)
            parsed_output = _parse_json_document(
                output_payload, f"{phase} published output", True
            )
            if not isinstance(parsed_output, dict):
                _fail("EVIDENCE_INCOMPLETE_NO_DECISION", f"{phase} output is not an object")
            output_object = parsed_output
            bytes_.atomic_external_file(phase, len(output_payload))
        elif staging.exists():
            bytes_.admit_tree(staging)
        response_payload = response or stdout_payload
        response_object: Mapping[str, Any] = {}
        if usage.exit_code == 0 and response_payload:
            parsed_response = _parse_json_document(
                response_payload, f"{phase} control response", True
            )
            if not isinstance(parsed_response, dict):
                _fail("EVIDENCE_INCOMPLETE_NO_DECISION", f"{phase} response is not an object")
            response_object = parsed_response
        if response_pipe and usage.exit_code == 0 and (
            set(response_object) != {"sha256", "size_bytes"}
            or response_object.get("sha256") != _sha256(output_payload)
            or response_object.get("size_bytes") != len(output_payload)
        ):
            _fail("ARTIFACT_INVALID", f"{phase} identity response mismatch")
        for path in (stdout_path, stderr_path):
            path.unlink()
            bytes_.note_deleted(path)
        work.rmdir()
        interrupted_after_publication = usage.exit_code != 0 and target.exists()
        if usage.exit_code != 0 and staging.exists():
            bytes_.discard_tree(staging)
            shutil.rmtree(staging)
        end = _snapshot()
        end_utc = _utc_now()
        boundary = PhaseBoundary(end, end_utc)
        disposition = "ATOMICALLY_PUBLISHED" if usage.exit_code == 0 else "DISCARDED"
        reason = (
            "PHASE_COMPLETE"
            if usage.exit_code == 0
            else "EXTERNAL_INTERRUPTION"
            if usage.exit_code < 0
            else "EVIDENCE_INCOMPLETE_NO_DECISION"
        )
        receipts.append(
            _phase_receipt(
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
                reason=reason,
                disposition=disposition,
                logical_run_id=logical_run_id,
                commit=commit,
                environment_sha=environment_sha,
            )
        )
        if (
            sum(item["cpu_microseconds"] for item in receipts) > PER_PHASE_CPU_LIMIT
            or sum(item["wall_nanoseconds"] for item in receipts) > PER_PHASE_WALL_LIMIT
        ):
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", f"{phase} operational ceiling crossed")
        if max(item["peak_rss_bytes"] for item in receipts) > RSS_LIMIT:
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", f"{phase} RSS ceiling crossed")
        if usage.exit_code == 0:
            return (
                receipts,
                response_payload,
                output_payload,
                response_object,
                output_object,
                boundary,
            )
        if interrupted_after_publication:
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", f"{phase} interrupted after publication")
        if usage.exit_code > 0:
            _fail("EVIDENCE_INCOMPLETE_NO_DECISION", f"{phase} failed: {stderr_payload[:4096]!r}")
    raise SupervisorFailure("RESOURCE_INCOMPLETE_NO_DECISION", f"{phase} interrupted twice")


def _write_pipe_document(descriptor: int, value: Mapping[str, Any]) -> None:
    payload = evidence.canonical_document(value)
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("short inherited-state response write")
        offset += written


def _read_pipe_document(descriptor: int, description: str) -> Mapping[str, Any]:
    payload = bytearray()
    while True:
        chunk = os.read(descriptor, 1 << 16)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > 4 * 1024 * 1024:
            _fail("EVIDENCE_INCOMPLETE_NO_DECISION", f"{description} exceeds 4 MiB")
    if not payload:
        return {}
    return _parse_json_document(bytes(payload), description, True)


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
) -> tuple[list[dict[str, Any]], int, PhaseBoundary]:
    """Fork E_emit with COW state; no detail checkpoint crosses the boundary."""

    receipts: list[dict[str, Any]] = []
    fixed_argv = tuple(sys.argv)
    boundary = PhaseBoundary(checkpoint_start, checkpoint_utc)
    for attempt in range(2):
        start = boundary.snapshot
        start_utc = boundary.utc
        receipt_binary_sha256 = _sha256(Path(sys.executable).read_bytes())
        read_fd, write_fd = os.pipe()
        pre_fork = _snapshot()
        pid = os.fork()
        if pid == 0:
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
                status = getattr(error, "status", "EVIDENCE_INCOMPLETE_NO_DECISION")
                detail = getattr(error, "detail", str(error))
                try:
                    _write_pipe_document(
                        write_fd,
                        {"detail": detail, "ok": False, "status": status},
                    )
                    os.close(write_fd)
                finally:
                    os._exit(2)
        os.close(write_fd)
        usage = _wait4_integer(pid)
        response = _read_pipe_document(read_fd, "E_emit inherited response")
        os.close(read_fd)
        target = artifact_root / "evidence"
        staging = artifact_root / "evidence.staging"
        if usage.exit_code == 0:
            if response.get("ok") is not True or not isinstance(
                response.get("byte_ledger"), dict
            ):
                _fail(
                    "EVIDENCE_INCOMPLETE_NO_DECISION",
                    "E_emit success response is malformed",
                )
            byte_ledger.replace_phase("E_emit", response["byte_ledger"])
        else:
            if target.exists():
                _fail(
                    "RESOURCE_INCOMPLETE_NO_DECISION",
                    "E_emit died after atomic publication",
                )
            if staging.exists():
                byte_ledger.switch("E_emit")
                byte_ledger.discard_tree(staging)
                shutil.rmtree(staging)
        end = _snapshot()
        end_utc = _utc_now()
        boundary = PhaseBoundary(end, end_utc)
        exit_reason = (
            "PHASE_COMPLETE"
            if usage.exit_code == 0
            else "EXTERNAL_INTERRUPTION"
            if usage.exit_code < 0
            else str(response.get("status", "EVIDENCE_INCOMPLETE_NO_DECISION"))
        )
        receipts.append(
            _phase_receipt(
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
                reason=exit_reason,
                disposition="ATOMICALLY_PUBLISHED" if usage.exit_code == 0 else "DISCARDED",
                logical_run_id=logical_run_id,
                commit=commit,
                environment_sha=environment_sha,
            )
        )
        if (
            sum(item["cpu_microseconds"] for item in receipts) > PER_PHASE_CPU_LIMIT
            or sum(item["wall_nanoseconds"] for item in receipts) > PER_PHASE_WALL_LIMIT
            or sealed_cpu
            + sum(
                item["cpu_microseconds"]
                for item in raw_instrument_receipts
                if item["phase"] in {"C_setup", "C_core", "C_bundle_io"}
            )
            + sum(item["cpu_microseconds"] for item in receipts)
            > STUDY_CPU_LIMIT
            or max(item["peak_rss_bytes"] for item in receipts) > RSS_LIMIT
        ):
            _fail("RESOURCE_INCOMPLETE_NO_DECISION", "E_emit operational ceiling crossed")
        if usage.exit_code == 0:
            return receipts, int(response["t_instrument_cpu_microseconds"]), boundary
        if usage.exit_code > 0:
            status = str(response.get("status", "EVIDENCE_INCOMPLETE_NO_DECISION"))
            detail = str(response.get("detail", "E_emit child failed"))
            _fail(status if status in STATUS_ORDER else "EVIDENCE_INCOMPLETE_NO_DECISION", detail)
    _fail("RESOURCE_INCOMPLETE_NO_DECISION", "E_emit process interrupted twice")


def _input_file_count(state: producer.ProducerState, include_evidence: bool) -> int:
    bundle = len(state.bundle.files) if state.bundle is not None else 0
    return bundle + (5 if include_evidence else 0)


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
) -> None:
    """Ledger and remove both unpublished producer staging namespaces."""

    bundle_staging = artifact_root / "bundle.staging"
    try:
        metadata = os.lstat(bundle_staging)
    except FileNotFoundError:
        pass
    except OSError as error:
        _fail("ARTIFACT_INVALID", f"cannot inspect bundle staging: {error}")
    else:
        if not stat.S_ISDIR(metadata.st_mode):
            _fail("ARTIFACT_INVALID", "bundle staging is not a real directory")
        byte_ledger.discard_tree(bundle_staging)
        try:
            shutil.rmtree(bundle_staging)
        except OSError as error:
            _fail("ARTIFACT_INVALID", f"cannot discard bundle staging: {error}")

    byte_ledger.discard_tree(attempt_root)
    producer.discard_attempt_root(attempt_root)


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
    producer_descriptor = os.open(
        PRODUCER_NATIVE, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    )
    _reserve_fixed_descriptor(producer_descriptor, 197)
    for attempt in range(2):
        attempt_root = root / "attempt.staging"
        attempt_root.mkdir()
        hooks = SupervisorHooks(attempt, attempt_root, meter, byte_ledger, sealed_cpu)
        try:
            state = producer.run_attempt(hooks, root)
            cap_crossed = hooks.cap_crossed
            _discard_producer_staging(root, attempt_root, byte_ledger)
            meter.close_current(
                "PRIMARY_CAP_STOP"
                if hooks.cap_crossed
                else "REPRESENTATION_STOP"
                if hooks.representation_stop
                else "PHASE_COMPLETE",
                "ATOMICALLY_PUBLISHED" if state.bundle is not None else "NONE",
            )
            if _observe_closed_producer_terminal(hooks, meter):
                resource_incomplete_observed = True
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
            break
        except ExternalInterruption:
            interruption_count += 1
            state = hooks.last_state
            _discard_producer_staging(root, attempt_root, byte_ledger)
            meter.close_current("EXTERNAL_INTERRUPTION", "DISCARDED")
            if _observe_closed_producer_terminal(hooks, meter):
                resource_incomplete_observed = True
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
                break
            if interruption_count >= 2:
                high_status = _status_min(high_status, "RESOURCE_INCOMPLETE_NO_DECISION")
                resource_incomplete_observed = True
                break
            meter.begin_retry()
            continue
        except producer.ProducerFailure as error:
            state = hooks.last_state
            publication_visible = (
                isinstance(error, producer.BundlePublicationVisibleFailure)
                or hooks.publication_became_visible
            )
            high_status = _status_min(high_status, error.status)
            if error.status == "RESOURCE_INCOMPLETE_NO_DECISION":
                resource_incomplete_observed = True
            _discard_producer_staging(root, attempt_root, byte_ledger)
            meter.close_current(
                error.status,
                "ATOMICALLY_PUBLISHED" if publication_visible else "DISCARDED",
            )
            if _observe_closed_producer_terminal(hooks, meter):
                resource_incomplete_observed = True
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
            if publication_visible:
                fatal_visible_publication = error.detail
            break
        except SupervisorFailure as error:
            state = hooks.last_state
            publication_visible = hooks.publication_became_visible
            high_status = _status_min(high_status, error.status)
            # ByteLedger ceilings raise directly rather than through
            # SupervisorHooks._operational_check(), so preserve their
            # resource-incomplete result independently of the terminal
            # CPU/wall/RSS sample below.
            if error.status == "RESOURCE_INCOMPLETE_NO_DECISION":
                resource_incomplete_observed = True
            _discard_producer_staging(root, attempt_root, byte_ledger)
            meter.close_current(
                error.status,
                "ATOMICALLY_PUBLISHED" if publication_visible else "DISCARDED",
            )
            if _observe_closed_producer_terminal(hooks, meter):
                resource_incomplete_observed = True
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
            if publication_visible:
                fatal_visible_publication = error.detail
            break
        except Exception as error:
            state = hooks.last_state
            publication_visible = hooks.publication_became_visible
            high_status = _status_min(high_status, "IMPLEMENTATION_INVALID")
            _discard_producer_staging(root, attempt_root, byte_ledger)
            meter.close_current(
                "IMPLEMENTATION_INVALID",
                "ATOMICALLY_PUBLISHED" if publication_visible else "DISCARDED",
            )
            if _observe_closed_producer_terminal(hooks, meter):
                resource_incomplete_observed = True
                high_status = _status_min(
                    high_status, "RESOURCE_INCOMPLETE_NO_DECISION"
                )
            print(f"A4-V2 implementation failure: {error}", file=sys.stderr)
            if publication_visible:
                fatal_visible_publication = str(error)
            break
    os.close(197)
    if fatal_visible_publication is not None:
        _fail(
            "ARTIFACT_INVALID",
            "bundle target is physically visible but U395 was not admitted; "
            f"downstream observation is forbidden: {fatal_visible_publication}",
        )
    if state is None or state.input_identity is None:
        _fail("EVIDENCE_INCOMPLETE_NO_DECISION", "no complete U000 prefix is available")

    emit_start = meter.boundary.snapshot
    emit_start_utc = meter.boundary.utc
    byte_ledger.switch("E_emit")
    emit_receipts, t_instrument, emit_boundary = _emit_in_inherited_process(
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
    )
    instrument_receipts = _sorted_receipts((*par_receipts, *meter.receipts))
    cap_crossed = cap_crossed or t_instrument > PRIMARY_CAP

    receipts_before_verifier = _sorted_receipts(
        (*instrument_receipts, *emit_receipts)
    )
    bytes_before_verifier = byte_ledger.objects(par_byte_entries)
    prior_research_evidence = sum(
        item["research_evidence_archive_bytes"] for item in bytes_before_verifier
    )
    (
        verifier_receipts,
        _verifier_response_payload,
        verifier_payload,
        verifier_response,
        verifier_summary,
        verifier_boundary,
    ) = _external_wrapper(
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
            "par_review_binding": _sealed_read_request(
                par_review_binding
            ),
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
    )
    verification_status = str(verifier_summary.get("status"))
    expected_native_argv = ["/proc/self/fd/197", "verify-canonical-request"]
    if set(verifier_response) != {
        "native_binary_sha256",
        "native_binary_size_bytes",
        "native_child_argv",
        "native_child_argv_sha256",
        "status",
        "verifier_summary_sha256",
        "verifier_summary_size_bytes",
    } or (
        verifier_response["native_binary_sha256"] != par_seal["verifier_native"]["sha256"]
        or verifier_response["native_binary_size_bytes"]
        != par_seal["verifier_native"]["size_bytes"]
        or verifier_response["native_child_argv"] != expected_native_argv
        or verifier_response["native_child_argv_sha256"]
        != _sha256(evidence.canonical_body(expected_native_argv))
        or verifier_response["status"] != verification_status
        or verifier_response["verifier_summary_sha256"] != _sha256(verifier_payload)
        or verifier_response["verifier_summary_size_bytes"] != len(verifier_payload)
    ):
        _fail("VERIFICATION_INVALID", "verifier response identity/status mismatch")

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
    ) = _external_wrapper(
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
        response_pipe=True,
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
        _fail("IMPLEMENTATION_INVALID", "instrument attribution does not reconcile")
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
        _fail("ARTIFACT_INVALID", "archive body lacks pretrailer file inventory")
    index_files = [dict(item) for item in pretrailer]
    index_files.extend((archive_identity, resource_identity, decision_identity))
    index_files.sort(key=lambda item: item["path"].encode("utf-8"))
    if len({item["path"] for item in index_files}) != len(index_files):
        _fail("ARTIFACT_INVALID", "artifact-index paths are duplicated")
    artifact_index = {
        "artifact_kind": "a4_artifact_index",
        "files": index_files,
        "producer_commit": commit,
        "schema_version": 1,
    }
    artifact_index_payload = evidence.canonical_document(artifact_index)
    evidence.publish_final_trailer(
        root, resource_payload, decision_payload, artifact_index_payload
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
    except OSError as error:
        print(f"ARTIFACT_INVALID: {error}", file=sys.stderr)
        return 3
