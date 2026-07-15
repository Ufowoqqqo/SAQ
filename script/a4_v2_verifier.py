#!/usr/bin/env python3
"""Independent A4 V2 full-replay verifier and atomic summary publisher.

This module is intentionally standalone.  In particular, it must not import
the producer runner, producer parsers, producer canonical encoders, or any
scientific implementation module.  Its only shared authorities are the
frozen input identity and the normative protocol/schema documents.

The executable interface to the independently linked native verifier is one
canonical JSON document on stdin and one canonical JSON document on stdout::

    a4_v2_native verify-canonical-request

The request contains inherited no-follow artifact descriptors and immutable
identities, never pathname reopenings or producer-derived scientific answers.
The native response must contain the independently
recomputed decision counts and discrepancy inventory.  A nonzero native exit
or a malformed response is a verifier-publication failure; it is not silently
converted into a scientific mismatch.

This source may be authored and statically reviewed during A4-V2-I.  Building,
importing, or executing it requires the separately authorized later stage.
"""

from __future__ import annotations

import argparse
import ctypes
import datetime as _datetime
import errno
import fcntl
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import resource
import selectors
import signal
import shlex
import ssl
import stat
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping, NoReturn, Optional, Sequence


REPOSITORY_ROOT = Path(os.path.abspath(__file__)).parent.parent
PROTOCOL_VERSION = "saq-a4-v2-synthetic-construction-20260714-schema1"
SCHEMA_VERSION = 1
NATIVE_BASENAME = "a4_v2_native"
NATIVE_IDENTITY_PATH = "build/a4_v2_verifier/a4_v2_native"
NATIVE_EXEC_FD = 197
CONTROL_FD = 198
GIT_BINARY = "/usr/bin/git"
PROTOCOL_AUTHORITY_IDENTITY_PATH = (
    "docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json"
)
PAR_SEAL_SCHEMA_IDENTITY_PATH = (
    "docs/saq_a4_v2_par_report_seal_schema_2026_07_14.json"
)
PAR_SEAL_MAXIMAL_INSTANCE_IDENTITY_PATH = (
    "docs/saq_a4_v2_par_report_seal_maximal_instance_2026_07_14.json"
)
PAR_DIRECTORY_IDENTITY_PATH = "docs/saq_a4_v2_par_artifacts_2026_07_14"
PAR_REVIEW_BINDING_IDENTITY_PATH = (
    "docs/saq_a4_v2_execution_authority_2026_07_14/par_review_binding.json"
)
PAR_SEAL_IDENTITY_PATH = PAR_DIRECTORY_IDENTITY_PATH + "/par_seal.json"
PAR_ARTIFACT_INDEX_IDENTITY_PATH = (
    PAR_DIRECTORY_IDENTITY_PATH + "/artifact_index.json"
)
PAR_REVIEW_MEMO_IDENTITY_PATH = (
    "docs/saq_a4_v2_par_artifacts_independent_review_2026_07_14.md"
)
PARITY_SUMMARY_IDENTITY_PATH = (
    PAR_DIRECTORY_IDENTITY_PATH + "/parity_summary.json"
)
PAR_SEAL_EXACT_MAX_BYTES = 5_171
PAR_SEAL_COARSE_MAX_BYTES = 65_536
PAR_SEAL_KEYS = frozenset(
    {
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
)
PROTOCOL_COMPONENT_ROLES = {
    "docs/saq_a4_v2_artifact_schema_2026_07_14.json": (
        "parent_srun_artifact_schema"
    ),
    "docs/saq_a4_v2_par_report_erratum_authorization_2026_07_14.md": (
        "authorization_provenance"
    ),
    PAR_SEAL_MAXIMAL_INSTANCE_IDENTITY_PATH: "par_seal_maximal_instance",
    PAR_SEAL_SCHEMA_IDENTITY_PATH: "par_seal_schema",
    "docs/saq_a4_v2_par_report_timing_closure_erratum_2026_07_14.json": (
        "machine_readable_erratum"
    ),
    "docs/saq_a4_v2_par_report_timing_closure_erratum_2026_07_14.md": (
        "normative_prose_erratum"
    ),
    "docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json": (
        "parent_machine_contract"
    ),
    "docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md": (
        "parent_preregistration"
    ),
}
GIT_OUTPUT_CAP_BYTES = 64 << 20
NATIVE_IO_CHUNK_BYTES = 64 << 10
NATIVE_WATCHDOG_INTERVAL_NANOSECONDS = 1_000_000_000
PUBLICATION_CPU_RESERVE_MICROSECONDS = 60_000_000
PUBLICATION_WALL_RESERVE_NANOSECONDS = 60_000_000_000
PRIMARY_CPU_CAP_MICROSECONDS = 34_560_000_000
PHASE_CPU_CAP_MICROSECONDS = 86_400_000_000
PHASE_WALL_CAP_NANOSECONDS = 172_800_000_000_000
PHASE_PEAK_RSS_CAP_BYTES = 25_769_803_776
OWNED_LIVE_TEMPORARY_CAP_BYTES = 17_179_869_184
RESEARCH_EVIDENCE_CAP_BYTES = 4_294_967_296
MINIMUM_AVAILABLE_MEMORY_BYTES = 25_769_803_776
MINIMUM_FREE_OUTPUT_BYTES = 17_179_869_184
STUDY_CPU_CAP_MICROSECONDS = 518_400_000_000

CMAKE_BINARY = "/usr/local/software/cmake-4.0.3/bin/cmake"
NINJA_BINARY = "/usr/local/software/ninja-1.9.0/bin/ninja"
CXX_BINARY = "/usr/bin/c++"
EXPECTED_CMAKE_VERSION = "cmake version 4.0.3"
EXPECTED_NINJA_VERSION = "1.9.0"
EXPECTED_COMPILER_ID = "GCC"
EXPECTED_COMPILER_VERSION = "11.5.0 20240719 (Red Hat 11.5.0-14)"
EXPECTED_COMPILE_FLAGS = (
    "-O3",
    "-fno-fast-math",
    "-ffp-contract=off",
    "-frounding-math",
    "-mfpmath=sse",
)
EXPECTED_LIBRARIES = {
    "gmp": "6.2.0",
    "mpfr": "4.1.0-p9",
    "openssl": "OpenSSL 3.5.5 27 Jan 2026",
}
EXPECTED_PAR_HOST_ENVIRONMENT = {
    "CPU": "Intel(R) Core(TM) i9-10920X CPU @ 3.50GHz",
    "GMP": EXPECTED_LIBRARIES["gmp"],
    "MPFR": EXPECTED_LIBRARIES["mpfr"],
    "MXCSR": "0x00001f80; FTZ=false; DAZ=false",
    "NumPy": "1.23.5",
    "OpenSSL": "3.5.5 27 Jan 2026",
    "Python": "CPython 3.9.25",
    "allowed_affinity": "0-23",
    "compiler": f"{EXPECTED_COMPILER_ID} {EXPECTED_COMPILER_VERSION}",
    "compiler_flags": list(EXPECTED_COMPILE_FLAGS),
    "governor": "performance",
    "kernel": "5.14.0-687.24.1.el9_8.x86_64",
    "physical_memory_bytes": 33_047_748_608,
    "rounding": "FE_TONEAREST",
    "SMT": "active",
    "thread_environment": {
        "MKL_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
    },
    "threads": 1,
    "turbo": "enabled; intel_pstate/no_turbo=0",
}
BUILD_COMMANDS = (
    (
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
    ),
    (
        CMAKE_BINARY,
        "--build",
        "build/a4_v2",
        "--target",
        "a4_v2_native",
        "-j",
        "1",
    ),
    (
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
    ),
    (
        CMAKE_BINARY,
        "--build",
        "build/a4_v2_verifier",
        "--target",
        "a4_v2_native",
        "-j",
        "1",
    ),
)
EXPECTED_PAR_COMMAND = (
    "python",
    "script/run_arbitrary_cardinality_a4_v2.py",
    "par",
    PAR_DIRECTORY_IDENTITY_PATH,
)
EXPECTED_PAR_OUTER_ARGV = EXPECTED_PAR_COMMAND[1:]
EXPECTED_PRODUCER_NATIVE_ARGV_TEMPLATES = (
    ("/proc/self/fd/197", "manifest"),
    ("/proc/self/fd/197", "native-smoke", "{output}"),
    ("/proc/self/fd/197", "par-block", "{input}", "{output}"),
    ("/proc/self/fd/197", "par-scalar", "{input}", "{output}"),
    ("/proc/self/fd/197", "representation-suite"),
    ("/proc/self/fd/197", "allocation-item", "{input}", "{output}"),
    ("/proc/self/fd/197", "block-suite", "{input}", "{output}"),
    ("/proc/self/fd/197", "encoding-suite", "{input}", "{output}"),
    ("/proc/self/fd/197", "scalar-suite", "{input}", "{output}"),
)
EXPECTED_VERIFIER_NATIVE_ARGV = ("/proc/self/fd/197", "verify-canonical-request")
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
PHASE_BYTE_KEYS = {
    "created_temporary_bytes",
    "deleted_partial_bytes",
    "maximum_live_owned_temporary_bytes",
    "permanent_intermediate_bundle_bytes",
    "phase",
    "research_evidence_archive_bytes",
}

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
DECISION_COUNT_KEYS = (
    "allocation_group_records",
    "allocation_global_records",
    "block_metadata_records",
    "block_start_records",
    "block_step_records",
    "bundle_files",
    "encoding_arm_records",
    "scalar_optimum_records",
)
INDEPENDENCE_ATTESTATIONS = (
    "optimized_solver_not_shared",
    "allocation_logic_not_shared",
    "tie_logic_not_shared",
    "rational_to_float_not_shared",
    "block_trainer_not_shared",
    "packer_not_shared",
    "logical_record_encoder_not_shared",
    "parser_core_not_shared",
    "producer_self_replay_not_used",
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
ARM_ORDER = (
    "dyadic_word",
    "arbitrary_word",
    "trained_block_vq",
    "global_dyadic_pack_cap8",
)
PRODUCER_CMAKE_SOURCE_FILES = (
    "research/a4_v2/a4_v2_native.cpp",
    "research/a4_v2/block_vq.cpp",
    "research/a4_v2/exact_quantizer.cpp",
    "research/a4_v2/native_cli.cpp",
    "research/a4_v2/numeric_runtime.cpp",
    "research/a4_v2/representation.cpp",
)
VERIFIER_CMAKE_SOURCE_FILES = (
    "research/a4_v2_verifier/a4_v2_native.cpp",
    "research/a4_v2_verifier/exact_reference.cpp",
    "research/a4_v2_verifier/input_panel.cpp",
    "research/a4_v2_verifier/json_value.cpp",
    "research/a4_v2_verifier/parity_cli.cpp",
    "research/a4_v2_verifier/replay.cpp",
    "research/a4_v2_verifier/representation_parity.cpp",
    "research/a4_v2_verifier/sha256.cpp",
)
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
EXPECTED_SOURCE_FILES = (
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
    *PYTHON_SOURCE_FILES,
)
EXPECTED_SOURCE_METADATA = {
    path: {
        "family": "producer_native",
        "role": (
            "build_configuration"
            if path.endswith("/CMakeLists.txt")
            else "translation_unit"
            if path.endswith(".cpp")
            else "interface_header"
        ),
    }
    for path in EXPECTED_SOURCE_FILES
    if path.startswith("research/a4_v2/")
}
EXPECTED_SOURCE_METADATA.update(
    {
        path: {
            "family": "independent_verifier_native",
            "role": (
                "build_configuration"
                if path.endswith("/CMakeLists.txt")
                else "translation_unit"
                if path.endswith(".cpp")
                else "interface_header"
            ),
        }
        for path in EXPECTED_SOURCE_FILES
        if path.startswith("research/a4_v2_verifier/")
    }
)
EXPECTED_SOURCE_METADATA.update(
    {
        path: {
            "family": "python_runtime",
            "role": (
                "entrypoint"
                if path == "script/run_arbitrary_cardinality_a4_v2.py"
                else "runtime_module"
            ),
        }
        for path in PYTHON_SOURCE_FILES
    }
)
PAR_INDEXED_FILE_NAMES = tuple(
    sorted(
        (
            *(name for index in range(4) for name in (
                f"build_command_{index:02d}.stderr",
                f"build_command_{index:02d}.stdout",
            )),
            "build_manifest.json",
            "build_producer_manifest.stderr",
            "build_producer_native_manifest.json",
            "build_verifier_manifest.stderr",
            "build_verifier_native_manifest.json",
            "producer_compile_commands.json",
            "verifier_compile_commands.json",
            "scalar_input.bin",
            "scalar_optimized.tsv",
            "scalar_independent.tsv",
            "scalar_optimized.stdout",
            "scalar_optimized.stderr",
            "scalar_independent.stdout",
            "scalar_independent.stderr",
            "block_input.bin",
            "block_optimized_run1.tsv",
            "block_optimized_run2.tsv",
            "block_independent.tsv",
            "block_optimized_run1.stdout",
            "block_optimized_run1.stderr",
            "block_optimized_run2.stdout",
            "block_optimized_run2.stderr",
            "block_independent.stdout",
            "block_independent.stderr",
            "representation_optimized.json",
            "representation_independent.json",
            "representation_optimized.stderr",
            "representation_independent.stdout",
            "representation_independent.stderr",
            "producer_native_smoke.tsv",
            "producer_native_smoke.stdout",
            "producer_native_smoke.stderr",
            "parity_summary.json",
        ),
        key=lambda value: value.encode("utf-8"),
    )
)
PAR_DIRECTORY_FILE_NAMES = tuple(
    sorted(
        (
            *PAR_INDEXED_FILE_NAMES,
            "artifact_index.json",
            "par_seal.json",
        ),
        key=lambda value: value.encode("utf-8"),
    )
)
PARITY_INVENTORY = {
    "allocation_decision_count": 2_433_600,
    "block_case_count": 64,
    "block_microfixture_count": 5,
    "block_rng": {
        "algorithm": "PCG64",
        "seed": 20_260_713,
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
        "seed": 20_260_713,
        "stream_scope": "scalar_256_only",
    },
}

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


class VerificationContractError(RuntimeError):
    """A frozen artifact, schema, or verifier-interface contract failed."""

    status = "ARTIFACT_INVALID"

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class VerificationImplementationError(VerificationContractError):
    """The reviewed verifier, tool, timer, or ledger violated its contract."""

    status = "IMPLEMENTATION_INVALID"


class VerificationEvidenceError(VerificationContractError):
    """Verifier publication or its required response is incomplete."""

    status = "EVIDENCE_INCOMPLETE_NO_DECISION"


class VerificationResourceError(VerificationContractError):
    """A registered V-replay or global publication ceiling was crossed."""


    status = "RESOURCE_INCOMPLETE_NO_DECISION"


class VerificationExternalInterruption(VerificationContractError):
    """The independent native replay was externally signalled."""

    status = "EXTERNAL_INTERRUPTION"


def _fail(message: str) -> NoReturn:
    raise VerificationContractError(message)


def _implementation_fail(message: str) -> NoReturn:
    raise VerificationImplementationError(message)


def _evidence_fail(message: str) -> NoReturn:
    raise VerificationEvidenceError(message)


def _resource_fail(message: str) -> NoReturn:
    raise VerificationResourceError(message)


def _run_as_verifier_implementation(operation: Any) -> Any:
    """Classify reviewed native/tool failures without hiding resource/signal facts."""

    try:
        return operation()
    except (VerificationResourceError, VerificationExternalInterruption):
        raise
    except VerificationContractError as error:
        raise VerificationImplementationError(error.detail) from error
    except OSError as error:
        raise VerificationImplementationError(str(error)) from error


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
    """Return the frozen canonical UTF-8 JSON preimage without a trailing LF."""

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


def parse_canonical_json_document(payload: bytes, description: str) -> Any:
    """Parse one duplicate-free, integer-only canonical JSON document."""

    if not payload.endswith(b"\n") or payload.endswith(b"\n\n"):
        _fail(f"{description} must have exactly one terminal LF")
    try:
        text = payload[:-1].decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise VerificationContractError(f"{description} is not strict UTF-8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_float=_reject_float,
            parse_int=int,
            parse_constant=_reject_constant,
        )
    except VerificationContractError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise VerificationContractError(f"{description} is not valid JSON") from error
    if canonical_json_document(value) != payload:
        _fail(f"{description} is not in frozen canonical JSON encoding")
    return value


def parse_strict_json_document(payload: bytes, description: str) -> Any:
    """Parse duplicate-free, integer-only JSON without imposing whitespace.

    Normative source documents such as the checked-in JSON Schema are allowed
    to use human-readable indentation.  Produced scientific artifacts are not;
    those continue to use :func:`parse_canonical_json_document`.
    """

    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise VerificationContractError(f"{description} is not strict UTF-8") from error
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_float=_reject_float,
            parse_int=int,
            parse_constant=_reject_constant,
        )
    except VerificationContractError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise VerificationContractError(f"{description} is not valid JSON") from error


def parse_canonical_json_lines(payload: bytes, description: str) -> list[Any]:
    """Parse canonical JSONL; the empty file represents an empty record class."""

    if not payload:
        return []
    if not payload.endswith(b"\n"):
        _fail(f"{description} has an unterminated JSONL record")
    records: list[Any] = []
    for index, line in enumerate(payload.splitlines(keepends=True)):
        records.append(parse_canonical_json_document(line, f"{description} line {index + 1}"))
    return records


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _same_json_value(left: Any, right: Any) -> bool:
    """JSON equality that does not confuse booleans with integers."""

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
    """Strict validator for the JSON-Schema vocabulary used by A4 V2.

    JSON Schema alone does not express the protocol's order, arithmetic, and
    hash-preimage invariants.  Those are checked separately below.
    """

    _SUPPORTED_KEYWORDS = frozenset(
        {
            "$schema",
            "$id",
            "$comment",
            "title",
            "description",
            "$defs",
            "$ref",
            "allOf",
            "oneOf",
            "not",
            "if",
            "then",
            "else",
            "const",
            "enum",
            "type",
            "minimum",
            "maximum",
            "minLength",
            "maxLength",
            "pattern",
            "format",
            "minItems",
            "maxItems",
            "uniqueItems",
            "prefixItems",
            "items",
            "contains",
            "minContains",
            "maxContains",
            "required",
            "properties",
            "additionalProperties",
        }
    )
    _SINGLE_SCHEMA_KEYWORDS = frozenset(
        {"not", "if", "then", "else", "items", "contains", "additionalProperties"}
    )
    _SCHEMA_ARRAY_KEYWORDS = frozenset({"allOf", "oneOf", "prefixItems"})

    def __init__(self, root: Mapping[str, Any]):
        if not isinstance(root, dict):
            _fail("schema root is not an object")
        self._root = root
        self._audit_schema_node(root, "schema")

    def _audit_schema_node(self, schema: Any, location: str) -> None:
        """Reject every unimplemented keyword before validating any instance."""

        if isinstance(schema, bool):
            return
        if not isinstance(schema, dict):
            _fail(f"{location} is not a schema object or boolean")
        unknown = set(schema) - self._SUPPORTED_KEYWORDS
        if unknown:
            _fail(f"{location} uses unsupported schema keywords: {sorted(unknown)!r}")
        definitions = schema.get("$defs", {})
        if not isinstance(definitions, dict):
            _fail(f"{location}.$defs is not an object")
        for name, child in definitions.items():
            if not isinstance(name, str):
                _fail(f"{location}.$defs contains a non-string name")
            self._audit_schema_node(child, f"{location}.$defs.{name}")
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            _fail(f"{location}.properties is not an object")
        for name, child in properties.items():
            if not isinstance(name, str):
                _fail(f"{location}.properties contains a non-string name")
            self._audit_schema_node(child, f"{location}.properties.{name}")
        for keyword in self._SINGLE_SCHEMA_KEYWORDS:
            if keyword in schema:
                self._audit_schema_node(schema[keyword], f"{location}.{keyword}")
        for keyword in self._SCHEMA_ARRAY_KEYWORDS:
            if keyword not in schema:
                continue
            children = schema[keyword]
            if not isinstance(children, list):
                _fail(f"{location}.{keyword} is not an array")
            for index, child in enumerate(children):
                self._audit_schema_node(child, f"{location}.{keyword}[{index}]")
        if "required" in schema and (
            not isinstance(schema["required"], list)
            or any(not isinstance(item, str) for item in schema["required"])
        ):
            _fail(f"{location}.required is not a string array")
        if "type" in schema and schema["type"] not in {
            "null",
            "boolean",
            "integer",
            "string",
            "array",
            "object",
        }:
            _fail(f"{location}.type is unsupported")
        if "format" in schema and schema["format"] != "date-time":
            _fail(f"{location}.format is unsupported")
        if "pattern" in schema:
            if not isinstance(schema["pattern"], str):
                _fail(f"{location}.pattern is not a string")
            try:
                re.compile(schema["pattern"])
            except re.error as error:
                raise VerificationContractError(
                    f"{location}.pattern is not a valid regular expression"
                ) from error

    def definition(self, name: str) -> Mapping[str, Any]:
        definitions = self._root.get("$defs")
        if not isinstance(definitions, dict) or name not in definitions:
            _fail(f"schema definition is missing: {name}")
        result = definitions[name]
        if not isinstance(result, dict):
            _fail(f"schema definition is not an object: {name}")
        return result

    def _resolve(self, reference: str) -> Any:
        if not reference.startswith("#/"):
            _fail(f"only local schema references are permitted: {reference!r}")
        current: Any = self._root
        for raw_part in reference[2:].split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, dict) or part not in current:
                _fail(f"unresolved schema reference: {reference!r}")
            current = current[part]
        return current

    def validate_definition(self, value: Any, name: str, location: str = "$") -> None:
        self.validate(value, self.definition(name), location)

    def validate_root(self, value: Any, location: str = "$") -> None:
        self.validate(value, self._root, location)

    def validate(self, value: Any, schema: Any, location: str = "$") -> None:
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
            match_count = 0
            for child in schema["oneOf"]:
                try:
                    self.validate(value, child, location)
                except VerificationContractError:
                    continue
                match_count += 1
            if match_count != 1:
                _fail(f"{location} matches {match_count} oneOf alternatives")
        if "not" in schema:
            try:
                self.validate(value, schema["not"], location)
            except VerificationContractError:
                pass
            else:
                _fail(f"{location} matches forbidden not schema")
        if "if" in schema:
            try:
                self.validate(value, schema["if"], location)
                condition = True
            except VerificationContractError:
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
            type_ok = {
                "null": value is None,
                "boolean": isinstance(value, bool),
                "integer": isinstance(value, int) and not isinstance(value, bool),
                "string": isinstance(value, str),
                "array": isinstance(value, list),
                "object": isinstance(value, dict),
            }.get(expected_type)
            if type_ok is None:
                _fail(f"unsupported schema type {expected_type!r} at {location}")
            if not type_ok:
                _fail(f"{location} is not schema type {expected_type}")

        if isinstance(value, int) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                _fail(f"{location} is below schema minimum")
            if "maximum" in schema and value > schema["maximum"]:
                _fail(f"{location} is above schema maximum")
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                _fail(f"{location} is shorter than schema minLength")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                _fail(f"{location} is longer than schema maxLength")
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                _fail(f"{location} does not match schema pattern")
            if schema.get("format") == "date-time":
                _validate_utc(value, location)
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                _fail(f"{location} has too few array items")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                _fail(f"{location} has too many array items")
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
                    except VerificationContractError:
                        continue
                    matches += 1
                if matches < schema.get("minContains", 1):
                    _fail(f"{location} has too few contains matches")
                if "maxContains" in schema and matches > schema["maxContains"]:
                    _fail(f"{location} has too many contains matches")
        if isinstance(value, dict):
            required = schema.get("required", [])
            missing = [key for key in required if key not in value]
            if missing:
                _fail(f"{location} is missing required keys: {missing!r}")
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


def _utc_datetime(value: str, location: str) -> _datetime.datetime:
    if _UTC_RE.fullmatch(value) is None:
        _fail(f"{location} is not frozen six-fraction-digit RFC3339 UTC")
    normalized = value[:-1] + "+00:00"
    try:
        parsed = _datetime.datetime.fromisoformat(normalized)
    except ValueError as error:
        raise VerificationContractError(f"{location} is not a real date-time") from error
    if parsed.tzinfo is None:
        _fail(f"{location} lacks a UTC offset")
    return parsed


def _validate_utc(value: str, location: str) -> None:
    _utc_datetime(value, location)


def normalize_artifact_path(value: str) -> str:
    """Return a canonical artifact-root-relative POSIX path."""

    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        _fail("artifact path is empty or contains a forbidden byte")
    path = PurePosixPath(value)
    if path.is_absolute():
        _fail(f"absolute artifact path is forbidden: {value!r}")
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        _fail(f"dot or empty artifact path component is forbidden: {value!r}")
    canonical = "/".join(parts)
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
    """Open an absolute path without following any path-component symlink."""

    raw = _normalized_absolute_file_path(path, description)
    parts = PurePosixPath(raw).parts
    if not parts or parts[0] != "/":
        _fail(f"{description} lacks an absolute POSIX root")
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
        raise VerificationContractError(
            f"cannot open sealed no-follow {description}: {error}"
        ) from error
    finally:
        os.close(directory_fd)


def _hash_open_regular_fd(descriptor: int, description: str) -> tuple[os.stat_result, str]:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        _fail(f"{description} is not a regular file")
    digest = hashlib.sha256()
    offset = 0
    while offset < metadata.st_size:
        chunk = os.pread(descriptor, min(1 << 20, metadata.st_size - offset), offset)
        if not chunk:
            _fail(f"{description} ended before its fstat size")
        digest.update(chunk)
        offset += len(chunk)
    if os.pread(descriptor, 1, metadata.st_size):
        _fail(f"{description} grew beyond its fstat size")
    after = os.fstat(descriptor)
    stable = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(metadata, field) != getattr(after, field) for field in stable):
        _fail(f"{description} changed while hashing")
    return after, digest.hexdigest()


def _open_and_validate_sealed_file(
    path: Path,
    description: str,
    *,
    expected_size_bytes: int,
    expected_sha256: str,
) -> tuple[int, os.stat_result]:
    if not isinstance(expected_size_bytes, int) or isinstance(expected_size_bytes, bool) or expected_size_bytes < 0:
        _fail(f"{description} expected size is not a nonnegative integer")
    _require_sha256(expected_sha256, f"{description} expected SHA-256")
    descriptor = _open_absolute_nofollow(path, description, os.O_RDONLY)
    try:
        metadata, observed_sha256 = _hash_open_regular_fd(descriptor, description)
        if metadata.st_size != expected_size_bytes or observed_sha256 != expected_sha256:
            _fail(f"{description} does not match reviewed sealed size/SHA-256")
        return descriptor, metadata
    except BaseException:
        os.close(descriptor)
        raise


def _revalidate_sealed_fd_and_path(
    descriptor: int,
    path: Path,
    description: str,
    expected_metadata: os.stat_result,
    expected_sha256: str,
) -> None:
    observed_metadata, observed_sha256 = _hash_open_regular_fd(descriptor, description)
    stable = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(expected_metadata, field) != getattr(observed_metadata, field)
        for field in stable
    ) or observed_sha256 != expected_sha256:
        _fail(f"sealed {description} changed across native invocation")
    replacement_fd = _open_absolute_nofollow(path, description, os.O_RDONLY)
    try:
        named_metadata, named_sha256 = _hash_open_regular_fd(replacement_fd, description)
    finally:
        os.close(replacement_fd)
    if any(
        getattr(expected_metadata, field) != getattr(named_metadata, field)
        for field in stable
    ) or named_sha256 != expected_sha256:
        _fail(f"sealed {description} path was replaced across native invocation")


def _read_sealed_manifest(
    path: Path,
    description: str,
    *,
    expected_size_bytes: int,
    expected_sha256: str,
) -> tuple[bytes, dict[str, Any]]:
    descriptor, metadata = _open_and_validate_sealed_file(
        path,
        description,
        expected_size_bytes=expected_size_bytes,
        expected_sha256=expected_sha256,
    )
    try:
        payload = bytearray()
        offset = 0
        while offset < metadata.st_size:
            chunk = os.pread(descriptor, min(1 << 20, metadata.st_size - offset), offset)
            if not chunk:
                _fail(f"{description} ended during sealed read")
            payload.extend(chunk)
            offset += len(chunk)
        _revalidate_sealed_fd_and_path(
            descriptor, path, description, metadata, expected_sha256
        )
    finally:
        os.close(descriptor)
    identity = {
        "path": _normalized_absolute_file_path(path, description),
        "sha256": expected_sha256,
        "size_bytes": expected_size_bytes,
    }
    return bytes(payload), identity


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


def _open_artifact_root(root: Path) -> int:
    return _open_absolute_nofollow(
        root,
        "artifact root",
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )


def _open_artifact_parent(
    root_descriptor: int,
    relative: str,
) -> tuple[int, str]:
    """Return a no-follow descriptor for the leaf's parent and its leaf name."""

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
        raise VerificationContractError(
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
    """Read a regular non-symlink file and reject an in-read mutation."""

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
        raise VerificationContractError(f"cannot open immutable artifact {relative!r}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"artifact is not a regular file: {relative!r}")
        if before.st_size > maximum_bytes:
            _fail(f"artifact exceeds verifier byte ceiling: {relative!r}")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1 << 20, remaining))
            if not chunk:
                _fail(f"artifact ended before its recorded size: {relative!r}")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail(f"artifact grew during read: {relative!r}")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        _fail(f"artifact mutated during immutable read: {relative!r}")
    try:
        named = os.stat(leaf, dir_fd=parent_descriptor, follow_symlinks=False)
    except OSError as error:
        os.close(parent_descriptor)
        raise VerificationContractError(
            f"artifact path disappeared after read: {relative!r}"
        ) from error
    os.close(parent_descriptor)
    if any(getattr(after, field) != getattr(named, field) for field in stable_fields):
        _fail(f"artifact path was replaced during immutable read: {relative!r}")
    return b"".join(chunks)


def open_immutable_artifact(
    root: Path, relative: str, *, maximum_bytes: int
) -> tuple[bytes, dict[str, Any]]:
    """Read and retain a stable no-follow descriptor for native replay."""

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
        raise VerificationContractError(
            f"cannot open retained immutable artifact {relative!r}"
        ) from error
    try:
        if descriptor < 200:
            moved = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 200)
            os.close(descriptor)
            descriptor = moved
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"retained artifact is not regular: {relative!r}")
        if before.st_size > maximum_bytes:
            _fail(f"retained artifact exceeds byte ceiling: {relative!r}")
        payload = bytearray()
        digest = hashlib.sha256()
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(
                descriptor, min(1 << 20, before.st_size - offset), offset
            )
            if not chunk:
                _fail(f"retained artifact ended early: {relative!r}")
            payload.extend(chunk)
            digest.update(chunk)
            offset += len(chunk)
        if os.pread(descriptor, 1, before.st_size):
            _fail(f"retained artifact grew during read: {relative!r}")
        after = os.fstat(descriptor)
        stable = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if any(getattr(before, field) != getattr(after, field) for field in stable):
            _fail(f"retained artifact mutated during read: {relative!r}")
        named = os.stat(leaf, dir_fd=parent_descriptor, follow_symlinks=False)
        if any(getattr(after, field) != getattr(named, field) for field in stable):
            _fail(f"retained artifact path was replaced: {relative!r}")
        return bytes(payload), {
            "fd": descriptor,
            "metadata": after,
            "path": relative,
            "sha256": digest.hexdigest(),
            "size_bytes": after.st_size,
        }
    except BaseException:
        os.close(descriptor)
        raise
    finally:
        os.close(parent_descriptor)


def revalidate_immutable_artifact(root: Path, handle: Mapping[str, Any]) -> None:
    relative = handle["path"]
    descriptor = handle["fd"]
    expected = handle["metadata"]
    observed, observed_hash = _hash_open_regular_fd(
        descriptor, f"retained artifact {relative}"
    )
    stable = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    if (
        any(getattr(expected, field) != getattr(observed, field) for field in stable)
        or observed_hash != handle["sha256"]
    ):
        _fail(f"retained artifact changed across native replay: {relative!r}")
    root_descriptor = _open_artifact_root(root)
    try:
        parent_descriptor, leaf = _open_artifact_parent(root_descriptor, relative)
    finally:
        os.close(root_descriptor)
    try:
        named_descriptor = os.open(
            leaf,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_descriptor,
        )
        try:
            named, named_hash = _hash_open_regular_fd(
                named_descriptor, f"named artifact {relative}"
            )
        finally:
            os.close(named_descriptor)
    finally:
        os.close(parent_descriptor)
    if (
        any(getattr(expected, field) != getattr(named, field) for field in stable)
        or named_hash != handle["sha256"]
    ):
        _fail(f"retained artifact path changed across native replay: {relative!r}")


def close_immutable_artifacts(
    handles: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    errors: list[str] = []
    for handle in handles.values():
        try:
            os.close(handle["fd"])
        except OSError as error:
            errors.append(f"artifact fd {handle['fd']} close failed: {error}")
    return errors


def read_immutable_external(path: Path, description: str, *, maximum_bytes: int) -> bytes:
    descriptor = _open_absolute_nofollow(path, description, os.O_RDONLY)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"{description} is not a regular file")
        if before.st_size > maximum_bytes:
            _fail(f"{description} exceeds byte ceiling")
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
    for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"):
        if getattr(before, field) != getattr(after, field):
            _fail(f"{description} mutated during read")
    replacement = _open_absolute_nofollow(path, description, os.O_RDONLY)
    try:
        named = os.fstat(replacement)
    finally:
        os.close(replacement)
    for field in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns"):
        if getattr(after, field) != getattr(named, field):
            _fail(f"{description} path was replaced during read")
    return bytes(payload)


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


def _require_git_oid(value: Any, description: str) -> str:
    if not isinstance(value, str) or _GIT_OID_RE.fullmatch(value) is None:
        _fail(f"{description} is not a lowercase 40-hex Git OID")
    return value


def _sealed_file_request(
    value: Any,
    description: str,
) -> tuple[Path, dict[str, Any]]:
    item = _require_mapping(value, description)
    expected_keys = {"identity_path", "read_path", "sha256", "size_bytes"}
    if set(item) != expected_keys:
        _fail(f"{description} does not have the exact sealed-file key set")
    if not isinstance(item["identity_path"], str) or not isinstance(item["read_path"], str):
        _fail(f"{description} paths are not strings")
    identity_path = normalize_artifact_path(item["identity_path"])
    relative_read_path = normalize_artifact_path(item["read_path"])
    if relative_read_path != identity_path:
        _fail(f"{description} identity_path/read_path differ")
    read_path = REPOSITORY_ROOT.joinpath(*relative_read_path.split("/"))
    _normalized_absolute_file_path(read_path, description)
    sha256 = _require_sha256(item["sha256"], f"{description}.sha256")
    size_bytes = _require_nonnegative_integer(
        item["size_bytes"], f"{description}.size_bytes"
    )
    return read_path, {
        "identity_path": identity_path,
        "read_path": os.fspath(read_path),
        "sha256": sha256,
        "size_bytes": size_bytes,
    }


def _read_all_from_fixed_fd(descriptor: int, description: str, maximum_bytes: int) -> bytes:
    if descriptor != CONTROL_FD:
        _fail(f"{description} descriptor is not frozen fd {CONTROL_FD}")
    payload = bytearray()
    while True:
        chunk = os.read(descriptor, min(1 << 20, maximum_bytes + 1 - len(payload)))
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > maximum_bytes:
            _fail(f"{description} exceeds its byte ceiling")
    return bytes(payload)


def _read_reviewed_sealed_file(
    item: Mapping[str, Any],
    description: str,
    *,
    maximum_bytes: int,
) -> bytes:
    if item["size_bytes"] > maximum_bytes:
        _fail(f"{description} exceeds its reviewed byte ceiling")
    descriptor, metadata = _open_and_validate_sealed_file(
        Path(item["read_path"]),
        description,
        expected_size_bytes=item["size_bytes"],
        expected_sha256=item["sha256"],
    )
    try:
        payload = bytearray()
        offset = 0
        while offset < metadata.st_size:
            chunk = os.pread(
                descriptor, min(1 << 20, metadata.st_size - offset), offset
            )
            if not chunk:
                _fail(f"{description} ended during reviewed read")
            payload.extend(chunk)
            offset += len(chunk)
        _revalidate_sealed_fd_and_path(
            descriptor,
            Path(item["read_path"]),
            description,
            metadata,
            item["sha256"],
        )
    finally:
        os.close(descriptor)
    return bytes(payload)


def _read_repo_identity(
    value: Any,
    description: str,
    *,
    maximum_bytes: int = 16 << 20,
) -> tuple[bytes, dict[str, Any]]:
    identity = _require_mapping(value, description)
    if set(identity) != {"path", "sha256", "size_bytes"}:
        _fail(f"{description} has a nonfrozen document identity shape")
    path = normalize_artifact_path(identity["path"])
    sealed = {
        "identity_path": path,
        "read_path": os.fspath(REPOSITORY_ROOT.joinpath(*path.split("/"))),
        "sha256": _require_sha256(identity["sha256"], f"{description}.sha256"),
        "size_bytes": _require_nonnegative_integer(
            identity["size_bytes"], f"{description}.size_bytes"
        ),
    }
    return _read_reviewed_sealed_file(sealed, description, maximum_bytes=maximum_bytes), dict(identity)


def _validate_protocol_authority(
    protocol_bytes: bytes,
    protocol_identity: Mapping[str, Any],
    schema_identity: Mapping[str, Any],
) -> tuple[dict[str, Any], SchemaRegistry, dict[str, dict[str, Any]]]:
    """Validate the composite authority and its complete eight-blob closure."""

    if protocol_identity["identity_path"] != PROTOCOL_AUTHORITY_IDENTITY_PATH:
        _fail("control protocol is not the frozen composite authority manifest")
    authority = dict(
        _require_mapping(
            parse_canonical_json_document(protocol_bytes, "composite protocol authority"),
            "composite protocol authority",
        )
    )
    if set(authority) != {
        "artifact_kind",
        "components",
        "erratum",
        "parent_protocol_commit",
        "protocol_authority_revision",
        "schema_version",
        "supersedes_only",
        "unchanged_parent_blobs",
    }:
        _fail("composite protocol authority has a nonfrozen shape")
    if (
        authority["artifact_kind"] != "a4_v2_composite_protocol_authority"
        or authority["erratum"] != "A4-V2-P-ERRATUM-1"
        or authority["parent_protocol_commit"]
        != "f86a51d6923409d735dda0ee40f88fd2e0ad2e43"
        or authority["protocol_authority_revision"]
        != "saq-a4-v2-synthetic-construction-20260714-erratum1"
        or authority["schema_version"] != 1
        or authority["supersedes_only"]
        != [
            "parent sole-F_trailer timing-closure wording",
            "parent outside-F_trailer wrapper prohibition wording",
            "missing terminal-P receipt/publication closure",
        ]
        or authority["unchanged_parent_blobs"] is not True
    ):
        _fail("composite protocol authority revision/erratum is not frozen")
    components = _require_list(authority["components"], "protocol components")
    expected_paths = sorted(PROTOCOL_COMPONENT_ROLES, key=lambda value: value.encode("utf-8"))
    observed_paths: list[str] = []
    admitted: dict[str, dict[str, Any]] = {}
    payloads: dict[str, bytes] = {}
    for index, raw in enumerate(components):
        component = _require_mapping(raw, f"protocol component {index}")
        if set(component) != {"path", "role", "sha256", "size_bytes"}:
            _fail("protocol component has a nonfrozen identity shape")
        path = normalize_artifact_path(component["path"])
        if PROTOCOL_COMPONENT_ROLES.get(path) != component["role"]:
            _fail(f"protocol component role/path is not frozen: {path}")
        payload, identity = _read_repo_identity(
            {
                "path": path,
                "sha256": component["sha256"],
                "size_bytes": component["size_bytes"],
            },
            f"protocol component {path}",
            maximum_bytes=64 << 20,
        )
        observed_paths.append(path)
        admitted[path] = identity
        payloads[path] = payload
    if observed_paths != expected_paths or len(observed_paths) != len(set(observed_paths)):
        _fail("composite protocol component closure/order differs from the frozen eight blobs")
    artifact_schema = admitted["docs/saq_a4_v2_artifact_schema_2026_07_14.json"]
    expected_schema = {
        "path": schema_identity["identity_path"],
        "sha256": schema_identity["sha256"],
        "size_bytes": schema_identity["size_bytes"],
    }
    if artifact_schema != expected_schema:
        _fail("control artifact schema differs from the composite authority component")

    seal_schema = _require_mapping(
        parse_strict_json_document(
            payloads[PAR_SEAL_SCHEMA_IDENTITY_PATH], "PAR seal schema"
        ),
        "PAR seal schema",
    )
    seal_registry = SchemaRegistry(seal_schema)
    maximal_payload = payloads[PAR_SEAL_MAXIMAL_INSTANCE_IDENTITY_PATH]
    if len(maximal_payload) != PAR_SEAL_EXACT_MAX_BYTES:
        _fail("registered PAR seal maximal instance does not establish exact M=5171")
    maximal_instance = _require_mapping(
        parse_canonical_json_document(maximal_payload, "PAR seal maximal instance"),
        "PAR seal maximal instance",
    )
    if set(maximal_instance) != PAR_SEAL_KEYS:
        _fail("PAR seal maximal instance does not exercise the exact 15-key shape")
    seal_registry.validate(maximal_instance, seal_schema, "PAR seal maximal instance")
    return authority, seal_registry, admitted


def _validate_source_manifest(
    source_manifest_bytes: bytes,
    protocol_identity: Mapping[str, Any],
    schema_identity: Mapping[str, Any],
    authority_components: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if protocol_identity["identity_path"] != PROTOCOL_AUTHORITY_IDENTITY_PATH:
        _fail("source-manifest bootstrap is not the composite protocol authority")
    if schema_identity["identity_path"] != (
        "docs/saq_a4_v2_artifact_schema_2026_07_14.json"
    ):
        _fail("source-manifest bootstrap is not the frozen artifact schema")
    manifest = dict(
        _require_mapping(
            parse_canonical_json_document(
                source_manifest_bytes, "implementation source manifest"
            ),
            "implementation source manifest",
        )
    )
    expected_keys = {
        "artifact_kind",
        "artifact_schema_identity",
        "authorization_identity",
        "build_status",
        "contract_identity",
        "implementation_binding_identity",
        "par_contract",
        "parent_protocol_commit",
        "parent_preregistration_identity",
        "producer_cmake_source_files",
        "protocol_identity",
        "python_source_files",
        "schema_version",
        "source_provenance_identity",
        "source_files",
        "source_tree_sha256",
        "verifier_cmake_source_files",
    }
    if set(manifest) != expected_keys:
        _fail("implementation source manifest has a nonfrozen top-level shape")
    if (
        manifest["artifact_kind"] != "a4_v2_implementation_manifest"
        or manifest["schema_version"] != 1
        or manifest["build_status"] != "NOT_AUTHORIZED_NOT_RUN"
    ):
        _fail("implementation source manifest authority/status mismatch")
    _require_git_oid(manifest["parent_protocol_commit"], "parent protocol commit")
    if manifest["parent_protocol_commit"] != "f86a51d6923409d735dda0ee40f88fd2e0ad2e43":
        _fail("implementation source manifest parent protocol commit is not frozen")
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
        _fail("source manifest protocol identity differs from verifier bootstrap")
    if manifest["artifact_schema_identity"] != expected_schema:
        _fail("source manifest schema identity differs from verifier bootstrap")
    expected_identity_paths = {
        "protocol_identity": PROTOCOL_AUTHORITY_IDENTITY_PATH,
        "parent_preregistration_identity": (
            "docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md"
        ),
        "contract_identity": (
            "docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json"
        ),
        "artifact_schema_identity": (
            "docs/saq_a4_v2_artifact_schema_2026_07_14.json"
        ),
        "authorization_identity": (
            "docs/saq_a4_v2_implementation_authorization_2026_07_14.md"
        ),
        "implementation_binding_identity": (
            "docs/saq_a4_v2_implementation_binding_2026_07_14.md"
        ),
        "source_provenance_identity": (
            "docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md"
        ),
    }
    for key, expected_path in expected_identity_paths.items():
        identity = _require_mapping(manifest[key], f"source manifest {key}")
        if identity.get("path") != expected_path:
            _fail(f"source manifest {key} path is not frozen")

    expected_parent_preregistration = authority_components[
        expected_identity_paths["parent_preregistration_identity"]
    ]
    if manifest["parent_preregistration_identity"] != expected_parent_preregistration:
        _fail("source manifest parent-preregistration provenance differs from authority")
    if manifest["contract_identity"] != authority_components[
        expected_identity_paths["contract_identity"]
    ]:
        _fail("source manifest parent contract differs from composite authority")
    for key in (
        "protocol_identity",
        "artifact_schema_identity",
        "authorization_identity",
        "contract_identity",
        "implementation_binding_identity",
        "parent_preregistration_identity",
        "source_provenance_identity",
    ):
        _read_repo_identity(manifest[key], f"source manifest {key}", maximum_bytes=16 << 20)

    raw_files = _require_list(manifest["source_files"], "implementation source files")
    if not raw_files:
        _fail("implementation source closure is empty")
    source_preimage: list[dict[str, Any]] = []
    source_paths: list[str] = []
    source_families: dict[str, str] = {}
    for index, raw in enumerate(raw_files):
        item = _require_mapping(raw, f"source file {index}")
        if set(item) != {"family", "path", "role", "sha256", "size_bytes"}:
            _fail("implementation source entry has a nonfrozen shape")
        path = normalize_artifact_path(item["path"])
        expected_metadata = EXPECTED_SOURCE_METADATA.get(path)
        if expected_metadata is None or {
            "family": item["family"],
            "role": item["role"],
        } != expected_metadata:
            _fail(f"implementation source family/role is not frozen for {path}")
        payload, _ = _read_repo_identity(
            {"path": path, "sha256": item["sha256"], "size_bytes": item["size_bytes"]},
            f"implementation source {path}",
            maximum_bytes=64 << 20,
        )
        if len(payload) != item["size_bytes"]:
            _fail("implementation source size changed after sealed read")
        source_paths.append(path)
        source_families[path] = item["family"]
        source_preimage.append(
            {"path": path, "sha256": item["sha256"], "size_bytes": item["size_bytes"]}
        )
    if source_paths != sorted(source_paths, key=lambda value: value.encode("utf-8")) or len(source_paths) != len(set(source_paths)):
        _fail("implementation source closure is not strictly UTF-8 path ordered")
    if source_paths != list(EXPECTED_SOURCE_FILES):
        _fail("implementation source closure differs from the exact runtime/build union")
    if sha256_bytes(canonical_json_without_lf(source_preimage)) != manifest["source_tree_sha256"]:
        _fail("implementation source_tree_sha256 does not bind the reviewed closure")
    _require_sha256(manifest["source_tree_sha256"], "source_tree_sha256")
    for key in (
        "producer_cmake_source_files",
        "verifier_cmake_source_files",
        "python_source_files",
    ):
        values = _require_list(manifest[key], key)
        if not values or any(not isinstance(value, str) for value in values):
            _fail(f"{key} is empty or contains a non-string path")
        normalized = [normalize_artifact_path(value) for value in values]
        if normalized != sorted(normalized, key=lambda value: value.encode("utf-8")) or len(normalized) != len(set(normalized)):
            _fail(f"{key} is not a unique UTF-8 ordered path list")
        if any(value not in source_families for value in normalized):
            _fail(f"{key} names a file outside the reviewed source closure")
    verifier_sources = manifest["verifier_cmake_source_files"]
    if manifest["producer_cmake_source_files"] != list(PRODUCER_CMAKE_SOURCE_FILES):
        _fail("producer CMake closure differs from the frozen translation-unit list")
    if verifier_sources != list(VERIFIER_CMAKE_SOURCE_FILES):
        _fail("verifier CMake closure differs from the frozen translation-unit list")
    if manifest["python_source_files"] != list(PYTHON_SOURCE_FILES):
        _fail("Python runtime closure differs from the frozen eight-file inventory")
    par_contract = _require_mapping(manifest["par_contract"], "PAR contract")
    par_keys = {
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
    }
    if set(par_contract) != par_keys:
        _fail("source manifest PAR contract has a nonfrozen shape")
    expected_contract = {
        "build_commands": [list(command) for command in BUILD_COMMANDS],
        "build_manifest_path": (
            "docs/saq_a4_v2_par_artifacts_2026_07_14/build_manifest.json"
        ),
        "par_command": list(EXPECTED_PAR_COMMAND),
        "par_review_binding_path": PAR_REVIEW_BINDING_IDENTITY_PATH,
        "par_review_memo_path": PAR_REVIEW_MEMO_IDENTITY_PATH,
        "par_seal_path": PAR_SEAL_IDENTITY_PATH,
        "parity_artifact_index_path": PAR_ARTIFACT_INDEX_IDENTITY_PATH,
        "parity_inventory": PARITY_INVENTORY,
        "parity_summary_path": PARITY_SUMMARY_IDENTITY_PATH,
        "producer_binary_identity_path": "build/a4_v2/a4_v2_native",
        "producer_native_child_argv_templates": [
            list(command) for command in EXPECTED_PRODUCER_NATIVE_ARGV_TEMPLATES
        ],
        "verifier_binary_identity_path": NATIVE_IDENTITY_PATH,
        "verifier_native_child_argv": list(EXPECTED_VERIFIER_NATIVE_ARGV),
    }
    if par_contract != expected_contract:
        _fail("source manifest PAR contract differs from the exact frozen contract")
    if par_contract["parity_inventory"] != PARITY_INVENTORY:
        _fail("PAR contract parity_inventory differs from the frozen fixture inventory")
    return manifest


def _manifest_sealed_file(value: Any, description: str) -> dict[str, Any]:
    item = _require_mapping(value, description)
    if set(item) != {"path", "sha256", "size_bytes"}:
        _fail(f"{description} has a nonfrozen sealed-file shape")
    path = normalize_artifact_path(item["path"])
    return {
        "path": path,
        "sha256": _require_sha256(item["sha256"], f"{description}.sha256"),
        "size_bytes": _require_nonnegative_integer(
            item["size_bytes"], f"{description}.size_bytes"
        ),
    }


def _document_identity(value: Any, description: str) -> dict[str, Any]:
    item = _require_mapping(value, description)
    if set(item) != {"path", "sha256", "size_bytes"}:
        _fail(f"{description} has a nonfrozen document-identity shape")
    return {
        "path": normalize_artifact_path(item["path"]),
        "sha256": _require_sha256(item["sha256"], f"{description}.sha256"),
        "size_bytes": _require_nonnegative_integer(
            item["size_bytes"], f"{description}.size_bytes"
        ),
    }


def _external_document_identity(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": item["identity_path"],
        "sha256": item["sha256"],
        "size_bytes": item["size_bytes"],
    }


def _read_par_document(
    value: Any,
    description: str,
    expected_identity_path: str,
    *,
    maximum_bytes: int,
) -> tuple[bytes, dict[str, Any]]:
    identity = _document_identity(value, description)
    if identity["path"] != expected_identity_path:
        _fail(f"{description} path differs from the frozen PAR authority")
    payload, observed = _read_repo_identity(
        identity, description, maximum_bytes=maximum_bytes
    )
    if observed != identity:
        _fail(f"{description} identity changed during reviewed read")
    return payload, identity


def _read_manifest_sealed_repo_file(
    value: Any,
    description: str,
    expected_identity_path: str,
    *,
    maximum_bytes: int,
) -> tuple[bytes, dict[str, Any]]:
    identity = _manifest_sealed_file(value, description)
    if identity["path"] != expected_identity_path:
        _fail(f"{description} path differs from the frozen build authority")
    payload = _read_reviewed_sealed_file(
        {
            "identity_path": identity["path"],
            "read_path": os.fspath(
                REPOSITORY_ROOT.joinpath(*expected_identity_path.split("/"))
            ),
            "sha256": identity["sha256"],
            "size_bytes": identity["size_bytes"],
        },
        description,
        maximum_bytes=maximum_bytes,
    )
    return payload, identity


def _require_exact_regular_directory(
    directory: Path,
    expected_names: Sequence[str],
    description: str,
) -> None:
    descriptor = _open_absolute_nofollow(
        directory,
        description,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        observed = sorted(os.listdir(descriptor), key=lambda value: value.encode("utf-8"))
        expected = sorted(expected_names, key=lambda value: value.encode("utf-8"))
        if observed != expected:
            _fail(f"{description} membership differs from the exact frozen inventory")
        for name in observed:
            metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):
                _fail(f"{description} contains non-regular entry {name!r}")
    finally:
        os.close(descriptor)


def _validate_par_artifact_index(
    payload: bytes,
    implementation_commit: str,
) -> dict[str, bytes]:
    index = _require_mapping(
        parse_canonical_json_document(payload, "PAR artifact index"),
        "PAR artifact index",
    )
    if set(index) != {
        "artifact_kind",
        "files",
        "implementation_commit",
        "schema_version",
    } or (
        index["artifact_kind"] != "a4_v2_par_artifact_index"
        or index["schema_version"] != 1
        or index["implementation_commit"] != implementation_commit
    ):
        _fail("PAR artifact index authority/commit is not frozen")
    files = _require_list(index["files"], "PAR artifact index files")
    names: list[str] = []
    result: dict[str, bytes] = {}
    par_directory = REPOSITORY_ROOT / "docs/saq_a4_v2_par_artifacts_2026_07_14"
    for position, raw in enumerate(files):
        item = _require_mapping(raw, f"PAR artifact-index file {position}")
        if set(item) != {"path", "sha256", "size_bytes"}:
            _fail("PAR artifact-index entry has a nonfrozen shape")
        name = normalize_artifact_path(item["path"])
        if "/" in name:
            _fail("PAR artifact-index entry is not a direct directory member")
        identity = {
            "identity_path": (
                "docs/saq_a4_v2_par_artifacts_2026_07_14/" + name
            ),
            "read_path": os.fspath(par_directory / name),
            "sha256": _require_sha256(item["sha256"], f"PAR index {name} hash"),
            "size_bytes": _require_nonnegative_integer(
                item["size_bytes"], f"PAR index {name} size"
            ),
        }
        result[name] = _read_reviewed_sealed_file(
            identity,
            f"PAR indexed artifact {name}",
            maximum_bytes=1 << 30,
        )
        names.append(name)
    if names != list(PAR_INDEXED_FILE_NAMES) or len(names) != len(set(names)):
        _fail("PAR artifact index is not the exact ordered full evidence inventory")
    _require_exact_regular_directory(
        par_directory,
        PAR_DIRECTORY_FILE_NAMES,
        "PAR artifact directory",
    )
    return result


def _validate_par_review_binding(
    review_binding_bytes: bytes,
    review_binding_identity: Mapping[str, Any],
    seal_registry: SchemaRegistry,
    source_manifest: Mapping[str, Any],
    build_manifest: Mapping[str, Any],
    build_manifest_identity: Mapping[str, Any],
    source_manifest_identity: Mapping[str, Any],
    protocol_identity: Mapping[str, Any],
    schema_identity: Mapping[str, Any],
    native_identity: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contract = _require_mapping(source_manifest["par_contract"], "PAR contract")
    if (
        contract["par_review_binding_path"] != PAR_REVIEW_BINDING_IDENTITY_PATH
        or contract["par_review_memo_path"] != PAR_REVIEW_MEMO_IDENTITY_PATH
        or contract["par_seal_path"] != PAR_SEAL_IDENTITY_PATH
        or contract["parity_artifact_index_path"]
        != PAR_ARTIFACT_INDEX_IDENTITY_PATH
        or contract["parity_summary_path"] != PARITY_SUMMARY_IDENTITY_PATH
        or review_binding_identity["identity_path"]
        != PAR_REVIEW_BINDING_IDENTITY_PATH
    ):
        _fail("PAR review paths differ from the frozen source contract")

    review = dict(
        _require_mapping(
            parse_canonical_json_document(
                review_binding_bytes, "PAR independent-review binding"
            ),
            "PAR independent-review binding",
        )
    )
    if set(review) != {
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
    }:
        _fail("PAR independent-review binding has a nonfrozen shape")
    if (
        review["artifact_kind"] != "a4_v2_par_review_binding"
        or _require_nonnegative_integer(
            review["schema_version"], "PAR review schema_version"
        )
        != 1
        or review["review_pass"] is not True
        or review["par_seal_schema_pass"] is not True
        or review["par_seal_maximal_instance_bytes"] != PAR_SEAL_EXACT_MAX_BYTES
        or _require_sha256(
            review["source_tree_sha256"], "PAR review source_tree_sha256"
        )
        != source_manifest["source_tree_sha256"]
    ):
        _fail("PAR independent-review binding is stale or unsuccessful")
    implementation_commit = _require_git_oid(
        review["implementation_commit"], "PAR binding implementation commit"
    )
    par_artifact_commit = _require_git_oid(
        review["par_artifact_commit"], "PAR artifact commit"
    )
    review_commit = _require_git_oid(review["review_commit"], "PAR review commit")
    par_tree_oid = _require_git_oid(
        review["par_artifact_tree_oid"], "PAR artifact tree OID"
    )
    if implementation_commit != build_manifest["implementation_commit"]:
        _fail("PAR binding implementation commit differs from the build authority")
    if len({implementation_commit, par_artifact_commit, review_commit}) != 3:
        _fail("PAR binding requires distinct I<P<R commits before execution")

    par_seal_bytes, par_seal_identity = _read_par_document(
        review["par_seal"],
        "PAR reviewed seal",
        PAR_SEAL_IDENTITY_PATH,
        maximum_bytes=PAR_SEAL_COARSE_MAX_BYTES,
    )
    if len(par_seal_bytes) > PAR_SEAL_EXACT_MAX_BYTES:
        _fail("PAR seal exceeds the registered exact 5171-byte maximum")
    artifact_index_bytes, artifact_index_identity = _read_par_document(
        review["artifact_index"],
        "PAR reviewed artifact index",
        PAR_ARTIFACT_INDEX_IDENTITY_PATH,
        maximum_bytes=16 << 20,
    )
    review_memo_bytes, review_memo_identity = _read_par_document(
        review["review_memo"],
        "PAR independent-review memo",
        PAR_REVIEW_MEMO_IDENTITY_PATH,
        maximum_bytes=16 << 20,
    )

    seal = dict(
        _require_mapping(
            parse_canonical_json_document(par_seal_bytes, "PAR reviewed seal"),
            "PAR reviewed seal",
        )
    )
    if set(seal) != PAR_SEAL_KEYS:
        _fail("PAR reviewed seal has a nonfrozen shape")
    seal_registry.validate_root(seal, "PAR reviewed seal")
    if (
        seal["artifact_kind"] != "a4_v2_par_seal"
        or _require_nonnegative_integer(
            seal["schema_version"], "PAR seal schema_version"
        )
        != 1
        or seal["parity_pass"] is not True
        or _require_sha256(
            seal["source_tree_sha256"], "PAR seal source_tree_sha256"
        )
        != source_manifest["source_tree_sha256"]
        or _require_git_oid(
            seal["implementation_commit"], "PAR implementation commit"
        )
        != build_manifest["implementation_commit"]
    ):
        _fail("PAR reviewed seal differs from the admitted source/build authority")

    expected_sealed = {
        "build_manifest": _external_document_identity(build_manifest_identity),
        "protocol": _external_document_identity(protocol_identity),
        "schema": _external_document_identity(schema_identity),
        "source_manifest": _external_document_identity(source_manifest_identity),
        "verifier_native": _external_document_identity(native_identity),
    }
    for key, expected_identity in expected_sealed.items():
        if _document_identity(seal[key], f"PAR seal {key}") != expected_identity:
            _fail(f"PAR seal {key} differs from the trusted verifier bootstrap")
    producer_identity = _manifest_sealed_file(
        build_manifest["producer"]["binary"], "build producer binary"
    )
    if (
        _document_identity(seal["producer_native"], "PAR seal producer binary")
        != producer_identity
        or _document_identity(seal["artifact_index"], "PAR seal artifact index")
        != artifact_index_identity
    ):
        _fail("PAR review binding does not bind the admitted index/binaries")
    parity_summary_bytes, parity_summary_identity = _read_par_document(
        seal["parity_summary"],
        "PAR parity summary",
        PARITY_SUMMARY_IDENTITY_PATH,
        maximum_bytes=16 << 20,
    )

    receipts = [
        dict(_require_mapping(item, f"PAR phase receipt {index}"))
        for index, item in enumerate(
            _require_list(seal["phase_receipts"], "PAR phase receipts")
        )
    ]
    previous_end: Optional[_datetime.datetime] = None
    receipt_identity_keys = (
        "argv_sha256",
        "binary_sha256",
        "environment_sha256",
        "execution_commit",
        "logical_run_id",
    )
    phase_attempts: dict[str, list[dict[str, Any]]] = {
        "B_build": [],
        "P_parity": [],
    }
    logical_run_id: Optional[str] = None
    shared_receipt_authority: Optional[tuple[str, str, str, str]] = None
    receipt_signatures: list[tuple[str, int, bool]] = []
    for index, receipt in enumerate(receipts):
        start = _utc_datetime(receipt["start_utc"], f"PAR receipt {index} start_utc")
        end = _utc_datetime(receipt["end_utc"], f"PAR receipt {index} end_utc")
        if start > end:
            _fail("PAR receipt start_utc is later than end_utc")
        if previous_end is not None and start != previous_end:
            _fail("PAR adjacent attempt UTC boundary is not exact")
        previous_end = end
        phase = receipt["phase"]
        if phase not in phase_attempts:
            _fail("PAR receipt phase is outside the frozen B/P inventory")
        phase_attempts[phase].append(receipt)
        if receipt["execution_commit"] != implementation_commit:
            _fail("PAR receipt execution commit differs from I")
        if logical_run_id is None:
            logical_run_id = receipt["logical_run_id"]
        elif receipt["logical_run_id"] != logical_run_id:
            _fail("PAR receipts do not share one logical_run_id")
        authority = (
            receipt["argv_sha256"],
            receipt["binary_sha256"],
            receipt["environment_sha256"],
            receipt["logical_run_id"],
        )
        if shared_receipt_authority is None:
            shared_receipt_authority = authority
        elif authority != shared_receipt_authority:
            _fail("PAR B/P receipt authority identities differ")
        receipt_signatures.append(
            (
                phase,
                receipt["attempt_id"],
                receipt["exit_reason"] == "PHASE_COMPLETE",
            )
        )
    allowed_receipt_signatures = {
        (("B_build", 0, True), ("P_parity", 0, True)),
        (
            ("B_build", 0, False),
            ("B_build", 1, True),
            ("P_parity", 0, True),
        ),
        (
            ("B_build", 0, True),
            ("P_parity", 0, False),
            ("P_parity", 1, True),
        ),
        (
            ("B_build", 0, False),
            ("B_build", 1, True),
            ("P_parity", 0, False),
            ("P_parity", 1, True),
        ),
    }
    if tuple(receipt_signatures) not in allowed_receipt_signatures:
        _fail("PAR receipt sequence is not one of the four frozen forms")
    environment_preimage = _require_mapping(
        build_manifest["environment_preimage"], "PAR environment preimage"
    )
    logical_run_preimage = _require_mapping(
        build_manifest["logical_run_preimage"], "PAR logical-run preimage"
    )
    expected_receipt_authority = (
        sha256_bytes(canonical_json_without_lf(logical_run_preimage["outer_argv"])),
        environment_preimage["leader_binary_sha256"],
        build_manifest["environment_sha256"],
        build_manifest["logical_run_id"],
    )
    if shared_receipt_authority != expected_receipt_authority:
        _fail("PAR receipts are not bound to the admitted argv/binary/environment/run")
    for phase, attempts in phase_attempts.items():
        if not attempts or [item["attempt_id"] for item in attempts] != list(
            range(len(attempts))
        ):
            _fail(f"PAR {phase} attempts are not contiguous from zero")
        if attempts[-1]["exit_reason"] != "PHASE_COMPLETE":
            _fail(f"PAR {phase} terminal attempt is not complete")
        for earlier in attempts[:-1]:
            if not earlier["exit_reason"].startswith("EXTERNAL_SIGNAL_"):
                _fail(f"PAR {phase} retry was not caused by an external signal")
        first = attempts[0]
        for attempt in attempts[1:]:
            if any(attempt[key] != first[key] for key in receipt_identity_keys):
                _fail(f"PAR {phase} retry changed a frozen authority identity")
        if sum(item["cpu_microseconds"] for item in attempts) > PHASE_CPU_CAP_MICROSECONDS:
            _fail(f"PAR {phase} aggregate CPU exceeds the phase ceiling")
        if sum(item["wall_nanoseconds"] for item in attempts) > PHASE_WALL_CAP_NANOSECONDS:
            _fail(f"PAR {phase} aggregate wall time exceeds the phase ceiling")
        if max(item["peak_rss_bytes"] for item in attempts) > PHASE_PEAK_RSS_CAP_BYTES:
            _fail(f"PAR {phase} peak RSS exceeds the phase ceiling")
    if sum(item["cpu_microseconds"] for item in receipts) > STUDY_CPU_CAP_MICROSECONDS:
        _fail("PAR B/P aggregate CPU already exceeds the study ceiling")
    byte_ledger = [
        _require_mapping(item, f"PAR byte-ledger entry {index}")
        for index, item in enumerate(
            _require_list(seal["phase_byte_ledger"], "PAR phase byte ledger")
        )
    ]
    if [item.get("phase") for item in byte_ledger] != ["B_build", "P_parity"]:
        _fail("PAR seal byte-ledger inventory is not exactly B_build/P_parity")
    indexed_payloads = _validate_par_artifact_index(
        artifact_index_bytes, build_manifest["implementation_commit"]
    )
    if indexed_payloads.get("build_manifest.json") != canonical_json_document(
        dict(build_manifest)
    ):
        _fail("PAR artifact index build manifest differs from admitted build bytes")
    if indexed_payloads.get("parity_summary.json") != parity_summary_bytes:
        _fail("PAR artifact index parity summary differs from the reviewed seal")
    indexed_evidence_bytes = len(artifact_index_bytes) + sum(
        len(payload) for payload in indexed_payloads.values()
    )
    if sum(item["research_evidence_archive_bytes"] for item in byte_ledger) != indexed_evidence_bytes:
        _fail("PAR B/P byte ledger does not exactly charge every indexed/index byte")
    if indexed_evidence_bytes > RESEARCH_EVIDENCE_CAP_BYTES:
        _fail("PAR evidence/index bytes exceed the research-evidence ceiling")
    for item in byte_ledger:
        if item["created_temporary_bytes"] < item["deleted_partial_bytes"]:
            _fail("PAR byte ledger deletes more temporary bytes than it creates")
        if item["maximum_live_owned_temporary_bytes"] > OWNED_LIVE_TEMPORARY_CAP_BYTES:
            _fail("PAR byte ledger exceeds the owned-live-byte ceiling")
        if item["permanent_intermediate_bundle_bytes"] != 0:
            _fail("PAR byte ledger reports a forbidden permanent intermediate bundle")
        if item["research_evidence_archive_bytes"] > RESEARCH_EVIDENCE_CAP_BYTES:
            _fail("PAR byte ledger entry exceeds the research-evidence ceiling")
    par_tree_blobs = {
        PAR_SEAL_IDENTITY_PATH: par_seal_bytes,
        PAR_ARTIFACT_INDEX_IDENTITY_PATH: artifact_index_bytes,
        PARITY_SUMMARY_IDENTITY_PATH: parity_summary_bytes,
    }
    par_tree_blobs.update(
        {
            "docs/saq_a4_v2_par_artifacts_2026_07_14/" + name: data
            for name, data in indexed_payloads.items()
        }
    )
    if len(par_tree_blobs) != len(PAR_DIRECTORY_FILE_NAMES):
        _fail("PAR tree byte map is not the exact immutable directory membership")
    if _document_identity(review["par_seal"], "PAR binding seal") != par_seal_identity:
        _fail("PAR binding seal identity changed during validation")
    if _document_identity(review["review_memo"], "PAR binding review memo") != review_memo_identity:
        _fail("PAR binding review-memo identity changed during validation")
    if _document_identity(seal["parity_summary"], "PAR seal parity summary") != parity_summary_identity:
        _fail("PAR parity-summary identity changed during validation")
    return {
        "implementation_commit": implementation_commit,
        "par_artifact_commit": par_artifact_commit,
        "par_research_evidence_bytes": indexed_evidence_bytes,
        "review_commit": review_commit,
        "par_artifact_tree_oid": par_tree_oid,
        "par_tree_blobs": par_tree_blobs,
        "review_memo_bytes": review_memo_bytes,
        "review_binding_bytes": review_binding_bytes,
    }, receipts


def _run_frozen_git(arguments: Sequence[str], description: str) -> bytes:
    command = [GIT_BINARY, "-C", os.fspath(REPOSITORY_ROOT), *arguments]
    environment = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "HOME": "/nonexistent",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            close_fds=True,
            cwd=REPOSITORY_ROOT,
            env=environment,
            timeout=60,
        )
    except subprocess.TimeoutExpired as error:
        raise VerificationContractError(
            f"frozen Git {description} exceeded 60 seconds"
        ) from error
    if (
        len(completed.stdout) > GIT_OUTPUT_CAP_BYTES
        or len(completed.stderr) > GIT_OUTPUT_CAP_BYTES
    ):
        _fail(f"frozen Git {description} exceeded its output ceiling")
    if completed.returncode != 0:
        _fail(
            f"frozen Git {description} failed with exit {completed.returncode}; "
            f"stderr_sha256={sha256_bytes(completed.stderr)}"
        )
    if completed.stderr:
        _fail(f"frozen Git {description} emitted unexpected stderr")
    return completed.stdout


def _validate_git_execution_authority(
    git_authority: Mapping[str, Any],
    execution_commit: str,
    source_manifest: Mapping[str, Any],
    source_manifest_bytes: bytes,
) -> None:
    implementation_commit = _require_git_oid(
        git_authority["implementation_commit"], "Git implementation commit"
    )
    par_artifact_commit = _require_git_oid(
        git_authority["par_artifact_commit"], "Git PAR artifact commit"
    )
    review_commit = _require_git_oid(
        git_authority["review_commit"], "Git review commit"
    )
    execution_commit = _require_git_oid(execution_commit, "Git execution commit")
    par_tree_oid = _require_git_oid(
        git_authority["par_artifact_tree_oid"], "Git PAR artifact tree OID"
    )
    par_tree_blobs = _require_mapping(
        git_authority["par_tree_blobs"], "Git PAR tree blobs"
    )
    if (
        len(
            {
                implementation_commit,
                par_artifact_commit,
                review_commit,
                execution_commit,
            }
        )
        != 4
    ):
        _fail("Git authority requires four distinct I<P<R<E commits")
    for commit, label in (
        (implementation_commit, "implementation"),
        (par_artifact_commit, "PAR"),
        (review_commit, "review"),
        (execution_commit, "execution"),
    ):
        if _run_frozen_git(
            ("cat-file", "-t", commit), f"{label} object type"
        ) != b"commit\n":
            _fail(f"Git {label} authority is not a commit object")
    if _run_frozen_git(
        ("cat-file", "-t", par_tree_oid), "PAR tree object type"
    ) != b"tree\n":
        _fail("Git PAR artifact-tree authority is not a tree object")
    expected_head = execution_commit.encode("ascii") + b"\n"
    if _run_frozen_git(("rev-parse", "HEAD"), "HEAD identity") != expected_head:
        _fail("current Git HEAD differs from the producer execution commit")
    if _run_frozen_git(
        ("status", "--porcelain=v1", "--untracked-files=all"),
        "clean-worktree check",
    ):
        _fail("current Git execution worktree is not clean")
    for ancestor, descendant, label in (
        (implementation_commit, par_artifact_commit, "implementation-to-PAR"),
        (par_artifact_commit, review_commit, "PAR-to-review"),
        (review_commit, execution_commit, "review-to-execution"),
    ):
        if _run_frozen_git(
            ("merge-base", "--is-ancestor", ancestor, descendant),
            f"{label} ancestry",
        ):
            _fail(f"Git {label} ancestry emitted unexpected stdout")
    implementation_blobs = {
        "docs/saq_a4_v2_implementation_manifest_2026_07_14.json": (
            source_manifest_bytes
        )
    }
    for raw in source_manifest["source_files"]:
        item = _require_mapping(raw, "Git implementation source entry")
        path = normalize_artifact_path(item["path"])
        payload = _run_frozen_git(
            ("show", f"{implementation_commit}:{path}"),
            f"implementation blob {path}",
        )
        if (
            len(payload) != item["size_bytes"]
            or sha256_bytes(payload) != item["sha256"]
        ):
            _fail(f"implementation Git blob differs from source manifest: {path}")
        implementation_blobs[path] = payload
    for commit, label in (
        (implementation_commit, "implementation"),
        (par_artifact_commit, "PAR"),
        (review_commit, "review"),
        (execution_commit, "execution"),
    ):
        for path, payload in implementation_blobs.items():
            if _run_frozen_git(
                ("show", f"{commit}:{path}"), f"{label} source blob {path}"
            ) != payload:
                _fail(f"{label} commit changed reviewed implementation blob {path}")

    expected_paths = sorted(par_tree_blobs, key=lambda value: value.encode("utf-8"))
    expected_prefix = PAR_DIRECTORY_IDENTITY_PATH + "/"
    if expected_paths != [expected_prefix + name for name in PAR_DIRECTORY_FILE_NAMES]:
        _fail("Git PAR tree payload map differs from exact directory membership")
    if _run_frozen_git(
        (
            "ls-tree",
            "-r",
            "-z",
            implementation_commit,
            "--",
            PAR_DIRECTORY_IDENTITY_PATH,
        ),
        "implementation premature PAR-tree check",
    ):
        _fail("I already contains the PAR artifact tree that P must add")
    reference_tree_entries: Optional[dict[str, str]] = None
    for commit, label in (
        (par_artifact_commit, "PAR"),
        (review_commit, "review"),
        (execution_commit, "execution"),
    ):
        if _run_frozen_git(
            ("rev-parse", f"{commit}:{PAR_DIRECTORY_IDENTITY_PATH}"),
            f"{label} PAR tree OID",
        ) != par_tree_oid.encode("ascii") + b"\n":
            _fail(f"{label} commit does not preserve the admitted PAR tree OID")
        raw_tree = _run_frozen_git(
            (
                "ls-tree",
                "-r",
                "-z",
                "--full-tree",
                commit,
                "--",
                PAR_DIRECTORY_IDENTITY_PATH,
            ),
            f"{label} recursive PAR tree",
        )
        entries: dict[str, str] = {}
        for raw_entry in raw_tree.split(b"\0"):
            if not raw_entry:
                continue
            try:
                metadata, raw_path = raw_entry.split(b"\t", 1)
                mode, object_type, raw_oid = metadata.split(b" ", 2)
                path = raw_path.decode("utf-8", errors="strict")
                oid = raw_oid.decode("ascii", errors="strict")
            except (ValueError, UnicodeError) as error:
                raise VerificationContractError(
                    f"{label} recursive PAR tree output is malformed"
                ) from error
            if mode != b"100644" or object_type != b"blob":
                _fail(f"{label} PAR tree contains a nonregular/non-100644 entry")
            _require_git_oid(oid, f"{label} PAR tree blob OID")
            if path in entries:
                _fail(f"{label} PAR tree contains a duplicate path")
            entries[path] = oid
        if sorted(entries, key=lambda value: value.encode("utf-8")) != expected_paths:
            _fail(f"{label} PAR tree recursive membership is not exact")
        if reference_tree_entries is None:
            reference_tree_entries = entries
        elif entries != reference_tree_entries:
            _fail(f"{label} PAR tree blob OIDs differ from P")
        for path in expected_paths:
            payload = par_tree_blobs[path]
            if _run_frozen_git(
                ("show", f"{commit}:{path}"), f"{label} PAR blob {path}"
            ) != payload:
                _fail(f"{label} PAR blob differs from admitted live bytes: {path}")

    review_memo_bytes = git_authority["review_memo_bytes"]
    for commit, label in (
        (implementation_commit, "implementation"),
        (par_artifact_commit, "PAR"),
    ):
        if _run_frozen_git(
            ("ls-tree", "-r", "-z", commit, "--", PAR_REVIEW_MEMO_IDENTITY_PATH),
            f"{label} premature review memo check",
        ):
            _fail(f"{label} commit already contains the review memo that R must add")
    for commit, label in (
        (implementation_commit, "implementation"),
        (par_artifact_commit, "PAR"),
        (review_commit, "review"),
    ):
        if _run_frozen_git(
            ("ls-tree", "-r", "-z", commit, "--", PAR_REVIEW_BINDING_IDENTITY_PATH),
            f"{label} premature E-binding check",
        ):
            _fail(f"{label} commit already contains the E-only review binding")
    for commit, label in ((review_commit, "review"), (execution_commit, "execution")):
        if _run_frozen_git(
            ("show", f"{commit}:{PAR_REVIEW_MEMO_IDENTITY_PATH}"),
            f"{label} PAR review memo",
        ) != review_memo_bytes:
            _fail(f"{label} commit lacks the exact admitted review memo")
    if _run_frozen_git(
        ("show", f"{execution_commit}:{PAR_REVIEW_BINDING_IDENTITY_PATH}"),
        "execution PAR review binding",
    ) != git_authority["review_binding_bytes"]:
        _fail("execution commit lacks the exact admitted E review binding")


def _validate_tool_identity(
    value: Any,
    description: str,
    expected_path: str,
) -> None:
    item = _require_mapping(value, description)
    if set(item) != {"path", "sha256", "size_bytes"}:
        _fail(f"{description} has a nonfrozen identity shape")
    if item["path"] != expected_path:
        _fail(f"{description} path differs from the frozen executable")
    descriptor, metadata = _open_and_validate_sealed_file(
        Path(expected_path),
        description,
        expected_size_bytes=_require_nonnegative_integer(
            item["size_bytes"], f"{description}.size_bytes"
        ),
        expected_sha256=_require_sha256(
            item["sha256"], f"{description}.sha256"
        ),
    )
    try:
        _revalidate_sealed_fd_and_path(
            descriptor, Path(expected_path), description, metadata, item["sha256"]
        )
    finally:
        os.close(descriptor)


def _validate_compile_records(
    value: Any,
    compile_commands_payload: bytes,
    expected_sources: Sequence[str],
    description: str,
) -> None:
    records = _require_list(value, f"{description} translation units")
    if len(records) != len(expected_sources):
        _fail(f"{description} translation-unit count differs from the frozen closure")
    raw_commands = _require_list(
        parse_strict_json_document(
            compile_commands_payload, f"{description} compile_commands"
        ),
        f"{description} compile_commands",
    )
    if len(raw_commands) != len(expected_sources):
        _fail(f"{description} compile_commands count differs from the frozen closure")
    raw_by_source: dict[str, Mapping[str, Any]] = {}
    for index, raw_value in enumerate(raw_commands):
        raw = _require_mapping(raw_value, f"{description} raw compile command {index}")
        if set(raw) not in (
            {"command", "directory", "file"},
            {"command", "directory", "file", "output"},
        ) or any(not isinstance(item, str) or not item for item in raw.values()):
            _fail(f"{description} compile_commands entry has a nonfrozen shape")
        source_path = Path(raw["file"])
        if not source_path.is_absolute():
            source_path = Path(raw["directory"]) / source_path
        try:
            source = source_path.resolve(strict=False).relative_to(
                REPOSITORY_ROOT
            ).as_posix()
        except ValueError as error:
            raise VerificationContractError(
                f"{description} compile source is outside the repository"
            ) from error
        if source in raw_by_source:
            _fail(f"{description} compile_commands duplicates {source}")
        raw_by_source[source] = raw
    observed_sources: list[str] = []
    allowed_numeric_flags = set(EXPECTED_COMPILE_FLAGS)
    expected_nonsemantic_flags = {"-DNDEBUG", "-std=c++20", "-Wall", "-Wextra", "-Wpedantic"}
    for index, raw_value in enumerate(records):
        record = _require_mapping(raw_value, f"{description} translation unit {index}")
        if set(record) != {"argv", "argv_sha256", "raw_command", "source"}:
            _fail(f"{description} translation-unit record has a nonfrozen shape")
        source = normalize_artifact_path(record["source"])
        argv = _require_list(record["argv"], f"{description} argv for {source}")
        if not argv or any(not isinstance(argument, str) for argument in argv):
            _fail(f"{description} translation-unit argv is malformed")
        raw = raw_by_source.get(source)
        if raw is None or record["raw_command"] != raw["command"]:
            _fail(f"{description} translation unit is not bound to compile_commands")
        try:
            tokenized = shlex.split(raw["command"], posix=True)
        except ValueError as error:
            raise VerificationContractError(
                f"{description} raw compile command cannot be tokenized"
            ) from error
        if argv != tokenized:
            _fail(f"{description} argv differs from tokenized raw command")
        numeric_candidates = [
            argument
            for argument in argv
            if argument.startswith(("-O", "-f", "-m"))
        ]
        if (
            argv[0] != CXX_BINARY
            or argv.count("-c") != 1
            or any(argv.count(flag) != 1 for flag in EXPECTED_COMPILE_FLAGS)
            or set(numeric_candidates) != allowed_numeric_flags
            or any(argv.count(flag) != 1 for flag in expected_nonsemantic_flags)
        ):
            _fail(f"{description} compiler/flag contract mismatch for {source}")
        if sha256_bytes(canonical_json_without_lf(argv)) != record["argv_sha256"]:
            _fail(f"{description} translation-unit argv hash mismatch")
        observed_sources.append(source)
    if observed_sources != list(expected_sources):
        _fail(f"{description} translation-unit source order/closure is not frozen")


def _validate_native_manifest_output(
    payload: bytes,
    description: str,
    *,
    producer: bool,
) -> None:
    manifest = _require_mapping(
        parse_canonical_json_document(payload, description), description
    )
    common = {
        "compile_flags": " ".join(EXPECTED_COMPILE_FLAGS),
        "compiler_id": EXPECTED_COMPILER_ID,
        "compiler_version": EXPECTED_COMPILER_VERSION,
        "gmp_version": EXPECTED_LIBRARIES["gmp"],
        "openssl_version": EXPECTED_LIBRARIES["openssl"],
        "schema_version": 1,
    }
    if any(manifest.get(key) != expected for key, expected in common.items()):
        _fail(f"{description} numeric/tool identity differs from the frozen contract")
    if producer:
        if (
            manifest.get("artifact_kind") != "a4_v2_native_build_manifest"
            or manifest.get("mpfr_version") != EXPECTED_LIBRARIES["mpfr"]
            or manifest.get("initial_mxcsr") != "0x00001f80"
            or manifest.get("final_mxcsr") != "0x00001f80"
            or manifest.get("initial_rounding_mode") != 0
            or manifest.get("final_rounding_mode") != 0
            or manifest.get("initial_rounding_mode_name") != "FE_TONEAREST"
            or manifest.get("final_rounding_mode_name") != "FE_TONEAREST"
            or any(
                manifest.get(key) is not False
                for key in (
                    "initial_mxcsr_denormals_are_zero",
                    "final_mxcsr_denormals_are_zero",
                    "initial_mxcsr_flush_to_zero",
                    "final_mxcsr_flush_to_zero",
                )
            )
        ):
            _fail("producer native manifest violates the frozen numeric contract")
    elif (
        manifest.get("artifact_kind") != "a4_v2_verifier_source_manifest"
        or manifest.get("producer_source_linked") is not False
        or manifest.get("numpy_repo_imports") is not False
        or manifest.get("parity_surfaces")
        != ["par-scalar", "par-block", "par-representation"]
        or manifest.get("input_authority")
        != {
            "numpy": "1.23.5",
            "python": "CPython 3.9.25",
            "role": "registered-input-regeneration-only",
        }
    ):
        _fail("verifier native manifest violates the frozen independence contract")


def _par_affinity_text(cpus: set[int]) -> str:
    if not cpus:
        _fail("PAR verifier observed an empty CPU-affinity set")
    ordered = sorted(cpus)
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


def _observed_par_cpu_model() -> str:
    models: list[str] = []
    for line in Path("/proc/cpuinfo").read_bytes().splitlines():
        if line.startswith(b"model name") and b":" in line:
            models.append(
                line.split(b":", 1)[1].strip().decode("ascii", errors="strict")
            )
    if not models or len(set(models)) != 1:
        _fail("PAR verifier CPU inventory is missing or heterogeneous")
    return models[0]


def _observed_par_host_environment() -> dict[str, Any]:
    """Independently observe the frozen host fields embedded by PAR."""

    try:
        numpy_version = importlib.metadata.version("numpy")
    except importlib.metadata.PackageNotFoundError as error:
        raise VerificationContractError(
            "registered NumPy distribution is unavailable"
        ) from error
    observed = {
        "CPU": _observed_par_cpu_model(),
        # The persisted producer/verifier native manifests independently bind
        # these library and numeric-runtime fields in this same build record.
        "GMP": EXPECTED_LIBRARIES["gmp"],
        "MPFR": EXPECTED_LIBRARIES["mpfr"],
        "MXCSR": "0x00001f80; FTZ=false; DAZ=false",
        "NumPy": numpy_version,
        "OpenSSL": ssl.OPENSSL_VERSION.removeprefix("OpenSSL "),
        "Python": f"{platform.python_implementation()} {platform.python_version()}",
        "allowed_affinity": _par_affinity_text(set(os.sched_getaffinity(0))),
        "compiler": f"{EXPECTED_COMPILER_ID} {EXPECTED_COMPILER_VERSION}",
        "compiler_flags": list(EXPECTED_COMPILE_FLAGS),
        "governor": Path(
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        ).read_text(encoding="ascii").strip(),
        "kernel": os.uname().release,
        "physical_memory_bytes": os.sysconf("SC_PHYS_PAGES")
        * os.sysconf("SC_PAGE_SIZE"),
        "rounding": "FE_TONEAREST",
        "SMT": (
            "active"
            if Path("/sys/devices/system/cpu/smt/active")
            .read_text(encoding="ascii")
            .strip()
            == "1"
            else "inactive"
        ),
        "thread_environment": {
            name: os.environ.get(name)
            for name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")
        },
        "threads": 1,
        "turbo": "enabled; intel_pstate/no_turbo="
        + Path("/sys/devices/system/cpu/intel_pstate/no_turbo")
        .read_text(encoding="ascii")
        .strip(),
    }
    if observed != EXPECTED_PAR_HOST_ENVIRONMENT:
        _fail("PAR verifier host differs from the complete frozen environment")
    return observed


def _observed_numpy_distribution_authority() -> dict[str, Any]:
    """Rehash the complete registered NumPy closure and its loaded PCG64 files."""

    try:
        distribution = importlib.metadata.distribution("numpy")
    except importlib.metadata.PackageNotFoundError as error:
        raise VerificationContractError(
            "registered NumPy distribution is unavailable"
        ) from error
    distribution_files = distribution.files
    if distribution.version != "1.23.5" or distribution_files is None:
        _fail("registered NumPy distribution/version changed")
    repository = REPOSITORY_ROOT.resolve()
    distribution_paths: list[Path] = []
    for relative in distribution_files:
        path = Path(distribution.locate_file(relative)).resolve(strict=True)
        try:
            path.relative_to(repository)
        except ValueError:
            pass
        else:
            _fail("registered NumPy distribution resolves inside the repository")
        distribution_paths.append(path)
    closure_paths = {path.as_posix() for path in distribution_paths}
    if not distribution_paths or len(closure_paths) != len(distribution_paths):
        _fail("registered NumPy distribution closure is empty or duplicated")
    try:
        numpy_spec = importlib.util.find_spec("numpy")
    except (ImportError, AttributeError) as error:
        raise VerificationContractError(
            "registered NumPy import origin cannot be resolved"
        ) from error
    if numpy_spec is None or not isinstance(numpy_spec.origin, str):
        _fail("registered NumPy import origin is unavailable")
    numpy_origin = Path(numpy_spec.origin).resolve(strict=True)
    if numpy_origin.as_posix() not in closure_paths:
        _fail("NumPy import origin is outside the registered distribution closure")

    try:
        numpy = importlib.import_module("numpy")
        numpy_random = importlib.import_module("numpy.random")
        numpy_pcg64 = importlib.import_module("numpy.random._pcg64")
    except ImportError as error:
        raise VerificationContractError(
            "registered NumPy/PCG64 runtime cannot be imported"
        ) from error
    pcg64 = getattr(numpy_random, "PCG64", None)
    if (
        getattr(numpy, "__version__", None) != "1.23.5"
        or getattr(pcg64, "__module__", None) != "numpy.random._pcg64"
        or getattr(numpy_pcg64, "PCG64", None) is not pcg64
    ):
        _fail("loaded NumPy/PCG64 runtime differs from the registered authority")
    files: list[dict[str, Any]] = []
    for path in distribution_paths:
        payload = read_immutable_external(
            path, f"registered NumPy file {path}", maximum_bytes=1 << 30
        )
        files.append(
            {
                "path": path.as_posix(),
                "sha256": sha256_bytes(payload),
                "size_bytes": len(payload),
            }
        )
    files.sort(key=lambda item: item["path"].encode("utf-8"))

    loaded_paths: set[str] = set()
    for module, description in (
        (numpy, "numpy/__init__"),
        (numpy_random, "numpy/random/__init__"),
        (numpy_pcg64, "numpy/random/_pcg64"),
    ):
        raw_path = getattr(module, "__file__", None)
        if not isinstance(raw_path, str) or not raw_path:
            _fail(f"loaded {description} module lacks a filesystem origin")
        path = Path(raw_path).resolve(strict=True)
        try:
            path.relative_to(repository)
        except ValueError:
            pass
        else:
            _fail(f"loaded {description} module resolves inside the repository")
        loaded_paths.add(path.as_posix())
    if len(loaded_paths) != 3 or not loaded_paths.issubset(closure_paths):
        _fail("loaded NumPy/random/PCG64 files are outside the full distribution closure")
    return {"files": files, "version": distribution.version}


def _validate_par_build_run_authority(build: Mapping[str, Any]) -> None:
    environment = dict(
        _require_mapping(build["environment_preimage"], "PAR environment preimage")
    )
    environment_keys = {
        "host_environment",
        "implementation_commit",
        "leader_binary_sha256",
        "leader_binary_size_bytes",
        "numpy_authority",
        "tool_paths",
    }
    if set(environment) != environment_keys:
        _fail("PAR environment preimage does not have the exact six-field shape")
    implementation_commit = _require_git_oid(
        build["implementation_commit"], "build implementation commit"
    )
    if (
        environment["implementation_commit"] != implementation_commit
        or environment["tool_paths"] != [CMAKE_BINARY, NINJA_BINARY, CXX_BINARY]
    ):
        _fail("PAR environment preimage differs from build/tool authority")
    host_environment = dict(
        _require_mapping(environment["host_environment"], "PAR host environment")
    )
    if (
        host_environment != EXPECTED_PAR_HOST_ENVIRONMENT
        or host_environment != _observed_par_host_environment()
    ):
        _fail("PAR host-environment preimage is not the complete frozen observation")
    numpy_authority = dict(
        _require_mapping(environment["numpy_authority"], "PAR NumPy authority")
    )
    if set(numpy_authority) != {"files", "version"}:
        _fail("PAR NumPy authority does not have the exact two-field shape")
    numpy_files = _require_list(numpy_authority["files"], "PAR NumPy files")
    for index, raw in enumerate(numpy_files):
        item = _require_mapping(raw, f"PAR NumPy file {index}")
        if set(item) != {"path", "sha256", "size_bytes"}:
            _fail("PAR NumPy file identity has a nonfrozen shape")
        if not isinstance(item["path"], str) or not Path(item["path"]).is_absolute():
            _fail("PAR NumPy file identity path is not absolute")
        _require_sha256(item["sha256"], f"PAR NumPy file {index} SHA-256")
        _require_nonnegative_integer(
            item["size_bytes"], f"PAR NumPy file {index} size"
        )
    if numpy_authority != _observed_numpy_distribution_authority():
        _fail("PAR NumPy distribution/PCG64 closure differs from independent rehash")

    leader_sha256 = _require_sha256(
        environment["leader_binary_sha256"], "PAR CPython leader SHA-256"
    )
    leader_size = _require_nonnegative_integer(
        environment["leader_binary_size_bytes"], "PAR CPython leader size"
    )
    if leader_size == 0:
        _fail("PAR CPython leader is empty")
    leader_bytes = read_immutable_external(
        Path(sys.executable), "current CPython leader", maximum_bytes=1 << 30
    )
    if len(leader_bytes) != leader_size or sha256_bytes(leader_bytes) != leader_sha256:
        _fail("PAR CPython leader bytes differ from the current execution authority")
    environment_sha256 = sha256_bytes(canonical_json_without_lf(environment))
    if _require_sha256(build["environment_sha256"], "PAR environment SHA-256") != environment_sha256:
        _fail("PAR environment SHA-256 does not bind the complete preimage")

    logical = dict(
        _require_mapping(build["logical_run_preimage"], "PAR logical-run preimage")
    )
    logical_keys = {
        "execution_commit",
        "outer_argv",
        "output_root",
        "preflight_pid",
        "preflight_start_time_clock_ticks",
        "prelaunch_utc",
        "protocol_version",
    }
    if set(logical) != logical_keys:
        _fail("PAR logical-run preimage does not have the exact seven-field shape")
    outer_argv = _require_list(logical["outer_argv"], "PAR outer argv")
    expected_output_root = os.fspath(
        (REPOSITORY_ROOT / PAR_DIRECTORY_IDENTITY_PATH).resolve()
    )
    preflight_pid = _require_nonnegative_integer(
        logical["preflight_pid"], "PAR preflight PID"
    )
    preflight_start = _require_nonnegative_integer(
        logical["preflight_start_time_clock_ticks"], "PAR preflight start time"
    )
    if (
        logical["execution_commit"] != implementation_commit
        or outer_argv != list(EXPECTED_PAR_OUTER_ARGV)
        or logical["output_root"] != expected_output_root
        or not isinstance(logical["prelaunch_utc"], str)
        or preflight_pid == 0
        or preflight_start == 0
        or logical["protocol_version"] != PROTOCOL_VERSION
    ):
        _fail("PAR logical-run preimage differs from the frozen launch authority")
    _utc_datetime(logical["prelaunch_utc"], "PAR logical prelaunch_utc")
    logical_run_id = sha256_bytes(canonical_json_without_lf(logical))
    if _require_sha256(build["logical_run_id"], "PAR logical_run_id") != logical_run_id:
        _fail("PAR logical_run_id does not bind the exact seven-field preimage")

    observation = dict(
        _require_mapping(build["prelaunch_observation"], "PAR prelaunch observation")
    )
    expected_observation_keys = {
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
    pass_fields = {
        "available_memory_requirement_pass",
        "conflicting_process_requirement_pass",
        "environment_requirement_pass",
        "free_output_requirement_pass",
        "preconditions_pass",
        "process_inventory_complete",
    }
    if set(observation) != expected_observation_keys or any(
        observation[field] is not True for field in pass_fields
    ):
        _fail("PAR prelaunch observation shape/pass authority is not frozen")
    _utc_datetime(observation["observed_utc"], "PAR prelaunch observed_utc")
    if (
        observation["observed_utc"] != logical["prelaunch_utc"]
        or observation["output_root"] != expected_output_root
        or observation["preflight_pid"] != preflight_pid
        or observation["preflight_start_time_clock_ticks"] != preflight_start
        or observation["environment_identity_sha256"] != environment_sha256
        or observation["effective_uid"] != os.geteuid()
        or observation["output_filesystem_device_id"]
        != os.stat(expected_output_root, follow_symlinks=False).st_dev
    ):
        _fail("PAR prelaunch observation does not bind logical/environment authority")
    environment_identity = dict(environment)
    environment_identity["environment_sha256"] = environment_sha256
    _validate_prelaunch(observation, environment_identity)


def _validate_build_manifest(
    build_manifest_bytes: bytes,
    source_manifest_identity: Mapping[str, Any],
    protocol_identity: Mapping[str, Any],
    schema_identity: Mapping[str, Any],
    artifact_schema_bytes: bytes,
    native_identity: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    expected_runtime_argv: Sequence[str],
) -> dict[str, Any]:
    build = dict(
        _require_mapping(
            parse_canonical_json_document(build_manifest_bytes, "native build manifest"),
            "native build manifest",
        )
    )
    expected_keys = {
        "artifact_kind",
        "build_commands",
        "environment_preimage",
        "environment_sha256",
        "implementation_commit",
        "libraries",
        "logical_run_id",
        "logical_run_preimage",
        "prelaunch_observation",
        "producer",
        "protocol",
        "schema",
        "schema_version",
        "source_manifest",
        "toolchain",
        "verifier",
    }
    if (
        set(build) != expected_keys
        or build["artifact_kind"] != "a4_v2_build_manifest"
        or _require_nonnegative_integer(
            build["schema_version"], "build schema_version"
        )
        != 1
    ):
        _fail("native build manifest top-level authority mismatch")
    _require_git_oid(build["implementation_commit"], "build implementation commit")
    expected_source = _external_document_identity(source_manifest_identity)
    expected_protocol = _external_document_identity(protocol_identity)
    expected_schema = _external_document_identity(schema_identity)
    if _manifest_sealed_file(build["source_manifest"], "build source manifest") != expected_source:
        _fail("build manifest is not bound to the reviewed source manifest")
    if _manifest_sealed_file(build["protocol"], "build protocol") != expected_protocol:
        _fail("build manifest protocol differs from the trusted bootstrap")
    if _manifest_sealed_file(build["schema"], "build schema") != expected_schema:
        _fail("build manifest schema differs from the trusted bootstrap")
    commands = _require_list(build["build_commands"], "build commands")
    expected_commands = [list(command) for command in BUILD_COMMANDS]
    if (
        commands != expected_commands
        or commands != source_manifest["par_contract"]["build_commands"]
    ):
        _fail("build commands differ from the exact frozen PAR contract")
    toolchain = _require_mapping(build["toolchain"], "build toolchain")
    if set(toolchain) != {
        "cmake",
        "cmake_version",
        "compile_flags",
        "compiler",
        "compiler_id",
        "compiler_version",
        "ninja",
        "ninja_version",
    }:
        _fail("build toolchain has a nonfrozen shape")
    if (
        toolchain["compile_flags"] != list(EXPECTED_COMPILE_FLAGS)
        or toolchain["cmake_version"] != EXPECTED_CMAKE_VERSION
        or toolchain["ninja_version"] != EXPECTED_NINJA_VERSION
        or toolchain["compiler_id"] != EXPECTED_COMPILER_ID
        or toolchain["compiler_version"] != EXPECTED_COMPILER_VERSION
    ):
        _fail("build toolchain values differ from the exact frozen contract")
    _validate_tool_identity(toolchain["cmake"], "CMake executable", CMAKE_BINARY)
    _validate_tool_identity(toolchain["ninja"], "Ninja executable", NINJA_BINARY)
    _validate_tool_identity(toolchain["compiler"], "C++ compiler", CXX_BINARY)
    libraries = _require_mapping(build["libraries"], "build libraries")
    if dict(libraries) != EXPECTED_LIBRARIES:
        _fail("build library inventory differs from exact frozen versions")
    for key, source_key, expected_binary_path in (
        ("producer", "producer_cmake_source_files", "build/a4_v2/a4_v2_native"),
        ("verifier", "verifier_cmake_source_files", NATIVE_IDENTITY_PATH),
    ):
        target = _require_mapping(build[key], f"build {key}")
        target_keys = {
            "binary",
            "cmake_lists",
            "cmake_source_files",
            "compile_commands",
            "manifest_argv",
            "manifest_argv_sha256",
            "manifest_output_sha256",
            "translation_units",
        }
        if key == "verifier":
            target_keys |= {"runtime_argv", "runtime_argv_sha256"}
        if set(target) != target_keys:
            _fail(f"build {key} target has a nonfrozen shape")
        binary = _manifest_sealed_file(target["binary"], f"build {key} binary")
        if binary["path"] != expected_binary_path:
            _fail(f"build {key} binary path is not frozen")
        _read_reviewed_sealed_file(
            {
                "identity_path": binary["path"],
                "read_path": os.fspath(
                    REPOSITORY_ROOT.joinpath(*binary["path"].split("/"))
                ),
                "sha256": binary["sha256"],
                "size_bytes": binary["size_bytes"],
            },
            f"build {key} binary",
            maximum_bytes=1 << 30,
        )
        if key == "verifier" and binary != _external_document_identity(native_identity):
            _fail("build verifier binary differs from the executed sealed binary")
        cmake_lists = _manifest_sealed_file(target["cmake_lists"], f"build {key} CMakeLists")
        source_entry = next(
            (
                item
                for item in source_manifest["source_files"]
                if item["path"] == cmake_lists["path"]
            ),
            None,
        )
        if source_entry is None or (
            source_entry["sha256"] != cmake_lists["sha256"]
            or source_entry["size_bytes"] != cmake_lists["size_bytes"]
        ):
            _fail(f"build {key} CMakeLists is outside the exact source closure")
        _read_repo_identity(
            {
                "path": cmake_lists["path"],
                "sha256": cmake_lists["sha256"],
                "size_bytes": cmake_lists["size_bytes"],
            },
            f"build {key} CMakeLists",
        )
        if target["cmake_source_files"] != source_manifest[source_key]:
            _fail(f"build {key} CMake closure differs from source manifest")
        compile_commands_path = (
            "docs/saq_a4_v2_par_artifacts_2026_07_14/"
            f"{key}_compile_commands.json"
        )
        compile_payload, _ = _read_manifest_sealed_repo_file(
            target["compile_commands"],
            f"build {key} compile_commands",
            compile_commands_path,
            maximum_bytes=64 << 20,
        )
        _validate_compile_records(
            target["translation_units"],
            compile_payload,
            source_manifest[source_key],
            key,
        )
        manifest_argv = target["manifest_argv"]
        if manifest_argv != [expected_binary_path, "manifest"]:
            _fail(f"build {key} manifest argv is not frozen")
        if sha256_bytes(canonical_json_without_lf(manifest_argv)) != target["manifest_argv_sha256"]:
            _fail(f"build {key} manifest argv hash mismatch")
        manifest_output_path = (
            "docs/saq_a4_v2_par_artifacts_2026_07_14/"
            f"build_{key}_native_manifest.json"
        )
        manifest_output = read_immutable_external(
            REPOSITORY_ROOT.joinpath(*manifest_output_path.split("/")),
            f"build {key} native manifest output",
            maximum_bytes=16 << 20,
        )
        if sha256_bytes(manifest_output) != _require_sha256(
            target["manifest_output_sha256"], f"build {key} manifest output"
        ):
            _fail(f"build {key} manifest output hash differs from persisted bytes")
        _validate_native_manifest_output(
            manifest_output,
            f"build {key} native manifest output",
            producer=key == "producer",
        )
        if key == "verifier":
            runtime_argv = list(expected_runtime_argv)
            if target["runtime_argv"] != runtime_argv:
                _fail("build verifier runtime argv differs from wrapper execution")
            runtime_hash = sha256_bytes(canonical_json_without_lf(runtime_argv))
            if target["runtime_argv_sha256"] != runtime_hash:
                _fail("build verifier runtime argv hash mismatch")
            if source_manifest["par_contract"]["verifier_native_child_argv"] != runtime_argv:
                _fail("source/build verifier child argv contracts differ")
    artifact_schema = _require_mapping(
        parse_strict_json_document(artifact_schema_bytes, "artifact schema"),
        "artifact schema",
    )
    SchemaRegistry(artifact_schema).validate_definition(
        build["prelaunch_observation"],
        "prelaunch_observation",
        "PAR build prelaunch observation",
    )
    _validate_par_build_run_authority(build)
    return build


def _verify_file_identity(identity: Mapping[str, Any], relative: str, payload: bytes) -> None:
    if identity.get("path") != relative:
        _fail(f"file identity path mismatch for {relative!r}")
    if identity.get("size_bytes") != len(payload):
        _fail(f"file identity size mismatch for {relative!r}")
    if identity.get("sha256") != sha256_bytes(payload):
        _fail(f"file identity hash mismatch for {relative!r}")


def _hash_object_omitting(value: Mapping[str, Any], field: str) -> str:
    if field not in value:
        _fail(f"hash-bearing object lacks {field!r}")
    preimage = dict(value)
    del preimage[field]
    return sha256_bytes(canonical_json_without_lf(preimage))


def _decode_hex(value: Any, description: str, *, nonempty: bool = False) -> bytes:
    if not isinstance(value, str) or len(value) % 2:
        _fail(f"{description} is not even-length lowercase hex")
    if nonempty and not value:
        _fail(f"{description} may not be empty")
    try:
        payload = bytes.fromhex(value)
    except ValueError as error:
        raise VerificationContractError(f"{description} is malformed hex") from error
    if payload.hex() != value:
        _fail(f"{description} is not canonical lowercase hex")
    return payload


def _parse_proc_status(payload: bytes, description: str) -> tuple[int, int]:
    pid_values: list[bytes] = []
    uid_values: list[list[bytes]] = []
    for line in payload.splitlines():
        if line.startswith(b"Pid:"):
            pid_values.append(line[4:].strip())
        elif line.startswith(b"Uid:"):
            uid_values.append(line[4:].split())
    if len(pid_values) != 1 or len(uid_values) != 1 or len(uid_values[0]) != 4:
        _fail(f"{description} lacks unique canonical Pid/Uid fields")
    tokens = [pid_values[0], *uid_values[0]]
    if any(re.fullmatch(rb"(?:0|[1-9][0-9]*)", token) is None for token in tokens):
        _fail(f"{description} has a noncanonical decimal Pid/Uid field")
    return int(pid_values[0]), int(uid_values[0][1])


def _parse_proc_stat(payload: bytes, description: str) -> tuple[int, bytes, str, int, int, int]:
    if payload.endswith(b"\n"):
        payload = payload[:-1]
    opening = payload.find(b"(")
    closing = payload.rfind(b") ")
    if opening <= 0 or closing <= opening or closing + 4 > len(payload):
        _fail(f"{description} has malformed comm/state framing")
    pid_token = payload[:opening].strip()
    comm = payload[opening + 1 : closing]
    tail = payload[closing + 2 :].split()
    if re.fullmatch(rb"[1-9][0-9]*", pid_token) is None or len(tail) < 20:
        _fail(f"{description} has malformed pid or too few fields")
    state_bytes = tail[0]
    if re.fullmatch(rb"[A-Za-z]", state_bytes) is None:
        _fail(f"{description} has malformed process state")
    numeric = (tail[11], tail[12], tail[19])
    if any(re.fullmatch(rb"(?:0|[1-9][0-9]*)", token) is None for token in numeric):
        _fail(f"{description} has malformed utime/stime/starttime")
    return (
        int(pid_token),
        comm,
        state_bytes.decode("ascii"),
        int(tail[11]),
        int(tail[12]),
        int(tail[19]),
    )


def _cmdline_fields(payload: bytes, description: str) -> list[bytes]:
    if not payload:
        return []
    if not payload.endswith(b"\x00") or payload.endswith(b"\x00\x00"):
        _fail(f"{description} lacks exactly one terminal NUL")
    fields = payload.split(b"\x00")
    if fields[-1] != b"":
        _fail(f"{description} terminal split invariant failed")
    return fields[:-1]


def _byte_basename(value: bytes) -> bytes:
    return value.rsplit(b"/", 1)[-1]


def _validate_prelaunch(observation: Mapping[str, Any], environment: Mapping[str, Any]) -> None:
    loadavg = _decode_hex(observation["loadavg_hex"], "loadavg_hex", nonempty=True)
    meminfo = _decode_hex(observation["meminfo_hex"], "meminfo_hex", nonempty=True)
    if sha256_bytes(loadavg) != observation["loadavg_sha256"]:
        _fail("loadavg SHA-256 does not bind loadavg_hex")
    if sha256_bytes(meminfo) != observation["meminfo_sha256"]:
        _fail("meminfo SHA-256 does not bind meminfo_hex")
    load_tokens = loadavg.split()
    if len(load_tokens) < 3:
        _fail("raw /proc/loadavg lacks three load tokens")
    expected_load = observation["load_average"]
    if [token.decode("ascii", errors="strict") for token in load_tokens[:3]] != [
        expected_load["one_minute"],
        expected_load["five_minute"],
        expected_load["fifteen_minute"],
    ]:
        _fail("parsed load-average tokens do not match raw /proc/loadavg")
    memavailable: list[int] = []
    for line in meminfo.splitlines():
        if line.startswith(b"MemAvailable:"):
            match = re.fullmatch(rb"MemAvailable:\s+([0-9]+)\s+kB", line)
            if match is None:
                _fail("raw MemAvailable line is malformed")
            memavailable.append(int(match.group(1)))
    if memavailable != [observation["memavailable_kib"]]:
        _fail("MemAvailable is not unique or does not match recorded kB")
    if observation["available_physical_memory_bytes"] != memavailable[0] * 1024:
        _fail("available physical memory arithmetic does not reconcile")
    if observation["free_output_bytes"] != (
        observation["output_f_bavail"] * observation["output_f_frsize"]
    ):
        _fail("statvfs free-output arithmetic does not reconcile")
    if observation["available_physical_memory_bytes"] < MINIMUM_AVAILABLE_MEMORY_BYTES:
        _fail("launched observation was below frozen memory precondition")
    if observation["free_output_bytes"] < MINIMUM_FREE_OUTPUT_BYTES:
        _fail("launched observation was below frozen disk precondition")
    if _hash_object_omitting(environment, "environment_sha256") != environment["environment_sha256"]:
        _fail("environment identity hash does not bind its canonical preimage")
    if observation["environment_identity_sha256"] != environment["environment_sha256"]:
        _fail("prelaunch observation is not bound to embedded environment")

    effective_uid = observation["effective_uid"]
    filters = observation["pid_filter_records"]
    processes = observation["same_user_processes"]
    if observation["numeric_pid_count"] != len(filters):
        _fail("numeric_pid_count does not match PID-filter record count")
    filter_pids = [record["pid"] for record in filters]
    if filter_pids != sorted(filter_pids) or len(filter_pids) != len(set(filter_pids)):
        _fail("PID-filter records are not strictly PID ordered")
    true_filter_indexes: list[int] = []
    for index, record in enumerate(filters):
        raw = _decode_hex(
            record["initial_proc_status_hex"],
            f"pid_filter_records[{index}].initial_proc_status_hex",
            nonempty=True,
        )
        if sha256_bytes(raw) != record["initial_proc_status_sha256"]:
            _fail("PID-filter status hash mismatch")
        parsed_pid, parsed_euid = _parse_proc_status(raw, f"PID-filter status {index}")
        if parsed_pid != record["pid"] or parsed_euid != record["effective_uid"]:
            _fail("PID-filter parsed identity mismatch")
        same_uid = parsed_euid == effective_uid
        if same_uid != record["same_as_preflight_effective_uid"]:
            _fail("PID-filter effective-UID classification mismatch")
        if same_uid:
            true_filter_indexes.append(index)
    if observation["same_user_process_count"] != len(processes):
        _fail("same_user_process_count does not match process array")
    if len(processes) != len(true_filter_indexes):
        _fail("same-user process array does not cover every true PID filter")
    observed_filter_indexes = [
        process["pid_filter_record_index"] for process in processes
    ]
    if sorted(observed_filter_indexes) != sorted(true_filter_indexes):
        _fail("same-user process array is not the exact true-filter-index multiset")
    process_keys = [(record["pid"], record["start_time_clock_ticks"]) for record in processes]
    if process_keys != sorted(process_keys) or len(process_keys) != len(set(process_keys)):
        _fail("same-user process entries are not uniquely ordered")

    self_count = 0
    for process_index, process in enumerate(processes):
        filter_index = process["pid_filter_record_index"]
        if filter_index not in true_filter_indexes or filters[filter_index]["pid"] != process["pid"]:
            _fail("same-user process does not bind its unique PID-filter record")
        raw_fields: dict[str, bytes] = {}
        for field, nonempty in (
            ("initial_proc_stat", True),
            ("final_proc_stat", True),
            ("final_proc_status", True),
            ("initial_cmdline", False),
            ("final_cmdline", False),
        ):
            raw = _decode_hex(
                process[f"{field}_hex"],
                f"same_user_processes[{process_index}].{field}_hex",
                nonempty=nonempty,
            )
            if sha256_bytes(raw) != process[f"{field}_sha256"]:
                _fail(f"same-user {field} hash mismatch")
            raw_fields[field] = raw
        if raw_fields["initial_cmdline"] != raw_fields["final_cmdline"]:
            _fail("same-user initial/final cmdline bytes differ")
        initial_exe = _decode_hex(process["initial_executable_target_hex"], "initial exe")
        final_exe = _decode_hex(process["final_executable_target_hex"], "final exe")
        if initial_exe != final_exe:
            _fail("same-user initial/final executable targets differ")
        initial_stat = _parse_proc_stat(raw_fields["initial_proc_stat"], "initial proc stat")
        final_stat = _parse_proc_stat(raw_fields["final_proc_stat"], "final proc stat")
        final_status = _parse_proc_status(raw_fields["final_proc_status"], "final proc status")
        if initial_stat[0] != process["pid"] or final_stat[0] != process["pid"]:
            _fail("same-user stat PID mismatch")
        if final_status != (process["pid"], effective_uid):
            _fail("same-user final status PID/effective-UID mismatch")
        if initial_stat[5] != final_stat[5] or final_stat[5] != process["start_time_clock_ticks"]:
            _fail("same-user start-time identity is unstable")
        if final_stat[1].hex() != process["comm_hex"]:
            _fail("same-user final comm bytes mismatch")
        if final_stat[2] != process["state"]:
            _fail("same-user final state mismatch")
        if final_stat[3] != process["user_cpu_clock_ticks"]:
            _fail("same-user user CPU ticks mismatch")
        if final_stat[4] != process["system_cpu_clock_ticks"]:
            _fail("same-user system CPU ticks mismatch")
        if process["total_cpu_clock_ticks"] != final_stat[3] + final_stat[4]:
            _fail("same-user total CPU ticks do not reconcile")
        argv_fields = _cmdline_fields(raw_fields["final_cmdline"], "final cmdline")
        basenames = [
            *([_byte_basename(final_exe)] if final_exe else []),
            *(_byte_basename(field) for field in argv_fields if field),
        ]
        matches = [marker for marker in CONFLICT_MARKERS if marker.encode("ascii") in basenames]
        if matches != process["matched_conflict_markers"]:
            _fail("same-user conflict-marker list does not replay")
        is_self = (
            process["pid"] == observation["preflight_pid"]
            and process["start_time_clock_ticks"]
            == observation["preflight_start_time_clock_ticks"]
        )
        if is_self != process["is_preflight_self"]:
            _fail("preflight-self classification does not replay")
        if is_self:
            self_count += 1
            if process["classification"] != "ALLOW_PREFLIGHT_SELF":
                _fail("preflight self lacks exact allow classification")
            if not matches:
                _fail("preflight self lacks a frozen A4 conflict marker")
        else:
            if matches or process["classification"] != "ALLOW_NO_MARKER":
                _fail("nonself process has a forbidden marker or classification")
        if process["conflicting_a4_or_saq_cost"] is not False:
            _fail("launched process inventory contains a conflict")
    if self_count != 1:
        _fail("process inventory does not contain exactly one preflight self")


def _expected_prefix_counts(completed_unit_count: int, block_step_records: int) -> dict[str, int]:
    def completed_after(first_index: int, count: int) -> int:
        return max(0, min(count, completed_unit_count - first_index))

    scalar_coordinates = completed_after(1, 128)
    group_allocations = completed_after(129, 128)
    global_allocations = completed_after(257, 2)
    block_groups = completed_after(259, 128)
    encodings = completed_after(387, 8)
    return {
        "allocation_group_records": group_allocations,
        "allocation_global_records": global_allocations,
        "block_metadata_records": block_groups,
        "block_start_records": block_groups * 8,
        "block_step_records": block_step_records,
        "bundle_files": 4 if completed_unit_count == 396 else 0,
        "encoding_arm_records": encodings,
        "scalar_optimum_records": scalar_coordinates * 256,
    }


def _validate_record_order_and_counts(
    manifest: Mapping[str, Any],
    scalar_records: Sequence[Mapping[str, Any]],
    allocation: Mapping[str, Any],
    block_records: Sequence[Mapping[str, Any]],
    encoding: Mapping[str, Any],
) -> dict[str, int]:
    for index, record in enumerate(scalar_records):
        expected_coordinate, requested = divmod(index, 256)
        if record["coordinate_id"] != expected_coordinate or record["requested_cardinality"] != requested + 1:
            _fail("scalar JSONL is not coordinate-major then increasing-K")

    group_records = allocation["group_records"]
    for index, record in enumerate(group_records):
        expected_word_bits = 4 if index < 64 else 8
        expected_group = index if index < 64 else index - 64
        if record["word_bits"] != expected_word_bits or record["group_id"] != expected_group:
            _fail("allocation group records violate B4-then-B8 group order")
        if record["coordinates"] != [2 * expected_group, 2 * expected_group + 1]:
            _fail("allocation group coordinates do not match frozen grouping")
    global_records = allocation["global_records"]
    if [record["word_bits"] for record in global_records] != [4, 8][: len(global_records)]:
        _fail("global allocation records violate B4-then-B8 order")

    metadata_count = 0
    start_count = 0
    step_count = 0
    cursor = 0
    while cursor < len(block_records):
        metadata = block_records[cursor]
        if metadata.get("record_type") != "block_metadata_v2":
            _fail("block JSONL group does not begin with metadata")
        expected_word_bits = 4 if metadata_count < 64 else 8
        expected_group = metadata_count if metadata_count < 64 else metadata_count - 64
        if metadata["word_bits"] != expected_word_bits or metadata["group_id"] != expected_group:
            _fail("block metadata violates B4-then-B8 group order")
        cursor += 1
        metadata_count += 1
        selected = 0
        for start_id in range(8):
            if cursor >= len(block_records):
                _fail("block JSONL ends inside an eight-start group")
            start = block_records[cursor]
            if (
                start.get("record_type") != "block_start_v2"
                or start["word_bits"] != expected_word_bits
                or start["group_id"] != expected_group
                or start["start_id"] != start_id
            ):
                _fail("block start order or identity mismatch")
            if start["iteration_count"] != len(start["steps"]):
                _fail("block iteration_count does not equal steps length")
            if start["accepted_update_count"] != len(start["steps"]):
                _fail("block accepted_update_count does not equal steps length")
            if [step["iteration"] for step in start["steps"]] != list(
                range(1, len(start["steps"]) + 1)
            ):
                _fail("block step iteration sequence is not contiguous")
            selected += int(start["selected_best_start"])
            if start["selected_best_start"] != (metadata["selected_start_id"] == start_id):
                _fail("block metadata and selected-start flag disagree")
            step_count += len(start["steps"])
            start_count += 1
            cursor += 1
        if selected != 1:
            _fail("block group does not have exactly one selected start")

    encoding_records = encoding["records"]
    expected_encoding_order = [
        (word_bits, arm)
        for word_bits in (4, 8)
        for arm in ARM_ORDER
    ]
    if [
        (record["word_bits"], record["arm"]) for record in encoding_records
    ] != expected_encoding_order[: len(encoding_records)]:
        _fail("encoding records violate B4/B8 registered-arm prefix order")
    for index, record in enumerate(encoding_records):
        arm_index = index % 4
        expected_offset = arm_index * 8192 * record["payload_bytes_per_vector"]
        expected_length = 8192 * record["payload_bytes_per_vector"]
        if record["file_byte_offset"] != expected_offset:
            _fail("encoding subrange offset does not match frozen formula")
        if record["file_byte_length"] != expected_length or record["output_bytes"] != expected_length:
            _fail("encoding subrange length does not match frozen formula")
        payload = _decode_hex(record["payload_hex"], "encoding payload_hex", nonempty=True)
        if len(payload) != expected_length or sha256_bytes(payload) != record["payload_sha256"]:
            _fail("encoding payload preimage does not match size/hash")

    observed = {
        "allocation_group_records": len(group_records),
        "allocation_global_records": len(global_records),
        "block_metadata_records": metadata_count,
        "block_start_records": start_count,
        "block_step_records": step_count,
        "bundle_files": 4 if manifest["bundle_published"] else 0,
        "encoding_arm_records": len(encoding_records),
        "scalar_optimum_records": len(scalar_records),
    }
    expected = _expected_prefix_counts(manifest["completed_unit_count"], step_count)
    if observed != expected or observed != manifest["record_counts"]:
        _fail("producer record counts do not match the exact atomic-unit prefix")
    expected_last = manifest["completed_unit_count"] - 1
    if manifest["last_completed_unit_index"] != expected_last:
        _fail("last_completed_unit_index does not match completed_unit_count")
    full = manifest["completed_unit_count"] == 396
    if manifest["full_shape_complete"] != full or manifest["bundle_published"] != full:
        _fail("full-shape and bundle flags do not match U395 completion")
    return observed


def _load_and_validate_inputs(
    artifact_root: Path,
    protocol_bytes: bytes,
    protocol_identity: Mapping[str, Any],
    schema_bytes: bytes,
    schema_identity: Mapping[str, Any],
) -> tuple[
    SchemaRegistry,
    Mapping[str, Any],
    dict[str, bytes],
    dict[str, dict[str, Any]],
    int,
]:
    schema_object = _require_mapping(
        parse_strict_json_document(schema_bytes, "artifact schema"), "artifact schema"
    )
    registry = SchemaRegistry(schema_object)

    _require_exact_regular_directory(
        artifact_root / "evidence",
        [PurePosixPath(path).name for path in EVIDENCE_PATHS],
        "producer evidence directory",
    )
    payloads: dict[str, bytes] = {}
    handles: dict[str, dict[str, Any]] = {}
    for relative in EVIDENCE_PATHS:
        payloads[relative], handles[relative] = open_immutable_artifact(
            artifact_root, relative, maximum_bytes=4_294_967_296
        )
    manifest = _require_mapping(
        parse_canonical_json_document(
            payloads["evidence/producer_manifest.json"], "producer manifest"
        ),
        "producer manifest",
    )
    registry.validate_definition(manifest, "producer_manifest_v2", "producer_manifest")
    expected_protocol_identity = {
        "path": protocol_identity["identity_path"],
        "sha256": protocol_identity["sha256"],
        "size_bytes": protocol_identity["size_bytes"],
    }
    expected_schema_identity = {
        "path": schema_identity["identity_path"],
        "sha256": schema_identity["sha256"],
        "size_bytes": schema_identity["size_bytes"],
    }
    if manifest["protocol_identity"] != expected_protocol_identity:
        _fail("producer protocol identity differs from trusted sealed bootstrap")
    if manifest["schema_identity"] != expected_schema_identity:
        _fail("producer schema identity differs from trusted sealed bootstrap")
    if len(protocol_bytes) != protocol_identity["size_bytes"] or sha256_bytes(protocol_bytes) != protocol_identity["sha256"]:
        _fail("trusted protocol bytes do not match their sealed identity")
    if len(schema_bytes) != schema_identity["size_bytes"] or sha256_bytes(schema_bytes) != schema_identity["sha256"]:
        _fail("trusted schema bytes do not match their sealed identity")
    if sha256_bytes(
        canonical_json_without_lf(manifest["command_identity"]["argv"])
    ) != manifest["command_identity"]["argv_sha256"]:
        _fail("producer argv hash does not bind canonical argv preimage")
    if _hash_object_omitting(manifest["input_identity"], "input_identity_sha256") != manifest[
        "input_identity"
    ]["input_identity_sha256"]:
        _fail("producer input identity hash does not bind canonical preimage")
    _validate_prelaunch(manifest["prelaunch_observation"], manifest["environment_identity"])
    if manifest["prelaunch_observation"]["output_root"] != os.fspath(artifact_root):
        _fail("prelaunch output_root differs from normalized artifact root")
    root_descriptor = _open_artifact_root(artifact_root)
    try:
        root_device = os.fstat(root_descriptor).st_dev
    finally:
        os.close(root_descriptor)
    if manifest["prelaunch_observation"]["output_filesystem_device_id"] != root_device:
        _fail("prelaunch output filesystem device differs from artifact root")

    for identity, relative in zip(manifest["evidence_files"], EVIDENCE_PATHS[:4]):
        _verify_file_identity(identity, relative, payloads[relative])

    scalar_records = parse_canonical_json_lines(
        payloads["evidence/scalar_optimum_records.jsonl"], "scalar optimum JSONL"
    )
    for index, record in enumerate(scalar_records):
        registry.validate_definition(record, "scalar_optimum_v2", f"scalar[{index}]")
    allocation = _require_mapping(
        parse_canonical_json_document(
            payloads["evidence/allocation_summary.json"], "allocation summary"
        ),
        "allocation summary",
    )
    registry.validate_definition(allocation, "allocation_summary_v2", "allocation")
    block_records = parse_canonical_json_lines(
        payloads["evidence/block_trajectories.jsonl"], "block trajectories JSONL"
    )
    for index, record in enumerate(block_records):
        definition = "block_metadata_v2" if record.get("record_type") == "block_metadata_v2" else "block_start_v2"
        registry.validate_definition(record, definition, f"block[{index}]")
    encoding = _require_mapping(
        parse_canonical_json_document(
            payloads["evidence/encoding_summary.json"], "encoding summary"
        ),
        "encoding summary",
    )
    registry.validate_definition(encoding, "encoding_summary_v2", "encoding")
    _validate_record_order_and_counts(
        manifest,
        [_require_mapping(item, "scalar record") for item in scalar_records],
        allocation,
        [_require_mapping(item, "block record") for item in block_records],
        encoding,
    )

    if manifest["bundle_published"]:
        _require_exact_regular_directory(
            artifact_root / "bundle",
            [PurePosixPath(path).name for path in BUNDLE_PATHS],
            "producer bundle directory",
        )
        for relative in BUNDLE_PATHS:
            payloads[relative], handles[relative] = open_immutable_artifact(
                artifact_root, relative, maximum_bytes=268_435_456
            )
        models = _require_mapping(
            parse_canonical_json_document(payloads["bundle/models.json"], "bundle models"),
            "bundle models",
        )
        representation = _require_mapping(
            parse_canonical_json_document(
                payloads["bundle/representation_manifest.json"], "representation manifest"
            ),
            "representation manifest",
        )
        registry.validate_definition(models, "models_v2", "bundle.models")
        registry.validate_definition(
            representation, "representation_manifest_v2", "bundle.manifest"
        )
        _verify_file_identity(
            representation["models"], "models.json", payloads["bundle/models.json"]
        )
        for identity, relative in zip(representation["code_files"], BUNDLE_PATHS[1:3]):
            local_relative = relative.removeprefix("bundle/")
            _verify_file_identity(identity, local_relative, payloads[relative])
    elif _artifact_entry_exists(artifact_root, "bundle"):
        _fail("bundle directory exists although producer manifest says unpublished")
    expected_paths = list(EVIDENCE_PATHS) + (
        list(BUNDLE_PATHS) if manifest["bundle_published"] else []
    )
    if list(handles) != expected_paths or set(payloads) != set(expected_paths):
        _fail("retained artifact descriptor closure is not exact")
    return registry, manifest, payloads, handles, len(payloads)


def _native_request(
    protocol_identity: Mapping[str, Any],
    schema_identity: Mapping[str, Any],
    source_manifest_identity: Mapping[str, Any],
    build_manifest_identity: Mapping[str, Any],
    native_identity: Mapping[str, Any],
    native_child_argv_sha256: str,
    manifest: Mapping[str, Any],
    producer_manifest_payload: bytes,
    artifact_handles: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_files": {
            path: {
                "fd": handle["fd"],
                "sha256": handle["sha256"],
                "size_bytes": handle["size_bytes"],
            }
            for path, handle in artifact_handles.items()
        },
        "build_manifest_sha256": build_manifest_identity["sha256"],
        "completed_unit_count": manifest["completed_unit_count"],
        "decision_counts_expected": dict(manifest["record_counts"]),
        "input_identity_sha256": manifest["input_identity"]["input_identity_sha256"],
        "last_completed_unit_index": manifest["last_completed_unit_index"],
        "native_binary_sha256": native_identity["sha256"],
        "native_child_argv_sha256": native_child_argv_sha256,
        "producer_manifest_sha256": sha256_bytes(producer_manifest_payload),
        "protocol_identity": _external_document_identity(protocol_identity),
        "protocol_version": PROTOCOL_VERSION,
        "schema_identity": _external_document_identity(schema_identity),
        "schema_version": SCHEMA_VERSION,
        "source_manifest_sha256": source_manifest_identity["sha256"],
    }


def _validate_prior_phase_receipts(
    registry: SchemaRegistry,
    value: Any,
    manifest: Mapping[str, Any],
    logical_run_id: str,
    implementation_commit: str,
    execution_commit: str,
    par_phase_receipts: Sequence[Mapping[str, Any]],
) -> tuple[int, int, int, int]:
    receipts = [
        _require_mapping(item, "verifier prior phase receipt")
        for item in _require_list(value, "verifier prior phase receipts")
    ]
    if not receipts:
        _fail("verifier prior phase receipt inventory is empty")
    phase_order = {
        phase: index
        for index, phase in enumerate(
            (
                "B_build",
                "P_parity",
                "C_setup",
                "C_core",
                "C_bundle_io",
                "E_emit",
                "V_replay",
            )
        )
    }
    for index, receipt in enumerate(receipts):
        registry.validate_definition(receipt, "phase_receipt", f"prior_receipt[{index}]")
        if receipt["phase"] not in phase_order:
            _fail("verifier prior receipt includes archive phase")
        if _parse_utc_for_receipt(receipt["end_utc"]) < _parse_utc_for_receipt(
            receipt["start_utc"]
        ):
            _fail("verifier prior receipt ends before it starts")
    expected_order = sorted(
        receipts,
        key=lambda receipt: (phase_order[receipt["phase"]], receipt["attempt_id"]),
    )
    if receipts != expected_order:
        _fail("verifier prior receipts are not in phase/attempt order")
    keys = [(receipt["phase"], receipt["attempt_id"]) for receipt in receipts]
    if len(keys) != len(set(keys)):
        _fail("verifier prior receipts duplicate a phase/attempt")
    observed_par_receipts = [
        dict(receipt)
        for receipt in receipts
        if receipt["phase"] in {"B_build", "P_parity"}
    ]
    if observed_par_receipts != [dict(receipt) for receipt in par_phase_receipts]:
        _fail("verifier B/P receipts differ from the independently reviewed PAR seal")
    for receipt in receipts:
        expected_commit = (
            implementation_commit
            if receipt["phase"] in {"B_build", "P_parity"}
            else execution_commit
        )
        if receipt["execution_commit"] != expected_commit:
            _fail("verifier prior receipt differs from its frozen execution commit")
    if not {"B_build", "P_parity", "C_setup", "E_emit"}.issubset(
        {receipt["phase"] for receipt in receipts}
    ):
        _fail("verifier prior receipts omit a mandatory B/P/C_setup/E phase")
    for phase in phase_order:
        attempts = [receipt["attempt_id"] for receipt in receipts if receipt["phase"] == phase]
        allowed = ([], [0], [1], [0, 1]) if phase in {
            "C_setup",
            "C_core",
            "C_bundle_io",
        } else ([], [0], [0, 1])
        if attempts not in allowed:
            _fail(f"verifier prior phase {phase} has noncontiguous attempts")
    manifest_receipts = [dict(receipt) for receipt in manifest["phase_receipts_through_instrument"]]
    observed_instrument = [
        dict(receipt)
        for receipt in receipts
        if receipt["phase"] in {"B_build", "P_parity", "C_setup", "C_core", "C_bundle_io"}
    ]
    if observed_instrument != manifest_receipts:
        _fail("verifier prior receipts do not exactly reproduce producer manifest receipts")
    if any(
        receipt["completed_unit_index"] != -1
        for receipt in receipts
        if receipt["phase"] in {"B_build", "P_parity"}
    ):
        _fail("verifier prior B/P receipt claims a scientific prefix")
    c_receipts = [
        receipt
        for receipt in receipts
        if receipt["phase"] in {"C_setup", "C_core", "C_bundle_io"}
    ]
    allowed_c_exit_reasons = {
        "ARTIFACT_INVALID",
        "CONTROL_INVALID",
        "EXTERNAL_INTERRUPTION",
        "IMPLEMENTATION_INVALID",
        "PHASE_COMPLETE",
        "PRIMARY_CAP_STOP",
        "REPRESENTATION_STOP",
        "RESOURCE_INCOMPLETE_NO_DECISION",
    }
    if any(
        receipt["exit_reason"] not in allowed_c_exit_reasons
        for receipt in c_receipts
    ):
        _fail("verifier prior C receipt has a nonfrozen exit reason")
    producer_attempts = sorted({receipt["attempt_id"] for receipt in c_receipts})
    if producer_attempts not in ([0], [0, 1]):
        _fail("prior producer attempt ids are not the frozen global set")
    c_receipts_by_attempt = {
        attempt: [
            receipt for receipt in c_receipts if receipt["attempt_id"] == attempt
        ]
        for attempt in producer_attempts
    }
    for attempt, attempt_receipts in c_receipts_by_attempt.items():
        if any(
            prior["end_utc"] != following["start_utc"]
            for prior, following in zip(
                attempt_receipts, attempt_receipts[1:]
            )
        ):
            _fail("verifier C phase boundaries are not temporally contiguous")
        observed_phases = [receipt["phase"] for receipt in attempt_receipts]
        if observed_phases != ["C_setup", "C_core", "C_bundle_io"][: len(observed_phases)]:
            _fail("verifier C attempt phases are not a prefix from C_setup")
        phase_bounds = {
            "C_setup": (0, 0),
            "C_core": (0, 394),
            "C_bundle_io": (394, 395),
        }
        if any(
            not (
                phase_bounds[receipt["phase"]][0]
                <= receipt["completed_unit_index"]
                <= phase_bounds[receipt["phase"]][1]
            )
            for receipt in attempt_receipts
        ):
            _fail("verifier C receipt prefix is outside its frozen phase range")
        if any(
            following["completed_unit_index"]
            < prior["completed_unit_index"]
            for prior, following in zip(
                attempt_receipts, attempt_receipts[1:]
            )
        ):
            _fail("verifier C completed prefix regresses within one attempt")
        if any(
            receipt["exit_reason"] != "PHASE_COMPLETE"
            or receipt["staging_disposition"] != "NONE"
            for receipt in attempt_receipts[:-1]
        ):
            _fail("verifier C attempt continued after a terminal receipt")
        if any(
            receipt["completed_unit_index"]
            != {"C_setup": 0, "C_core": 394}[receipt["phase"]]
            for receipt in attempt_receipts[:-1]
        ):
            _fail("verifier C phase boundary closes at the wrong unit")
        if attempt == 0 and producer_attempts == [0, 1] and (
            attempt_receipts[-1]["exit_reason"] != "EXTERNAL_INTERRUPTION"
            or attempt_receipts[-1]["staging_disposition"] != "DISCARDED"
        ):
            _fail("verifier producer retry lacks its frozen interrupted attempt")
    if producer_attempts == [0, 1] and (
        c_receipts_by_attempt[0][-1]["end_utc"]
        != c_receipts_by_attempt[1][0]["start_utc"]
    ):
        _fail("verifier producer retry does not start at the attempt-0 boundary")
    if (
        c_receipts_by_attempt[producer_attempts[-1]][-1][
            "completed_unit_index"
        ]
        != manifest["last_completed_unit_index"]
    ):
        _fail("verifier final C attempt does not close at the producer prefix")
    final_c_receipt = c_receipts_by_attempt[producer_attempts[-1]][-1]
    c_study_cpu = sum(
        receipt["cpu_microseconds"]
        for receipt in receipts
        if receipt["phase"]
        in {"B_build", "P_parity", "C_setup", "C_core", "C_bundle_io"}
    )
    final_attempt_receipts = c_receipts_by_attempt[producer_attempts[-1]]
    final_external_has_resource_trigger = (
        sum(receipt["cpu_microseconds"] for receipt in final_attempt_receipts)
        > PHASE_CPU_CAP_MICROSECONDS
        or sum(receipt["wall_nanoseconds"] for receipt in final_attempt_receipts)
        > PHASE_WALL_CAP_NANOSECONDS
        or max(receipt["peak_rss_bytes"] for receipt in final_attempt_receipts)
        > PHASE_PEAK_RSS_CAP_BYTES
        or c_study_cpu > STUDY_CPU_CAP_MICROSECONDS
    )
    if manifest["bundle_published"]:
        allowed_final = (
            final_c_receipt["exit_reason"] == "PHASE_COMPLETE"
            and final_c_receipt["staging_disposition"] == "ATOMICALLY_PUBLISHED"
            and final_c_receipt["phase"] == "C_bundle_io"
            and final_c_receipt["completed_unit_index"] == 395
        )
    elif final_c_receipt["exit_reason"] in {
        "PRIMARY_CAP_STOP",
        "REPRESENTATION_STOP",
    }:
        allowed_final = final_c_receipt["staging_disposition"] == "NONE"
    elif final_c_receipt["exit_reason"] in {
        "ARTIFACT_INVALID",
        "CONTROL_INVALID",
        "IMPLEMENTATION_INVALID",
        "RESOURCE_INCOMPLETE_NO_DECISION",
    }:
        allowed_final = final_c_receipt["staging_disposition"] == "DISCARDED"
    elif final_c_receipt["exit_reason"] == "EXTERNAL_INTERRUPTION":
        allowed_final = (
            producer_attempts == [0]
            and final_c_receipt["staging_disposition"] == "DISCARDED"
            and final_external_has_resource_trigger
        )
    else:
        allowed_final = False
    if not allowed_final:
        _fail("verifier final C receipt has an impossible terminal disposition")
    published_c_receipts = [
        receipt
        for receipt in c_receipts
        if receipt["staging_disposition"] == "ATOMICALLY_PUBLISHED"
    ]
    if manifest["bundle_published"]:
        if len(published_c_receipts) != 1 or (
            published_c_receipts[0]["phase"] != "C_bundle_io"
            or published_c_receipts[0]["exit_reason"] != "PHASE_COMPLETE"
            or published_c_receipts[0]["completed_unit_index"] != 395
            or published_c_receipts[0] is not final_c_receipt
        ):
            _fail("verifier published bundle lacks its unique successful U395 receipt")
    elif published_c_receipts:
        _fail("verifier prior C receipt claims a visible unpublished bundle")
    emit_receipts = [receipt for receipt in receipts if receipt["phase"] == "E_emit"]
    if not emit_receipts:
        _fail("verifier prior receipts omit E_emit")
    if any(
        receipt["exit_reason"] != "EXTERNAL_INTERRUPTION"
        or receipt["staging_disposition"] != "DISCARDED"
        for receipt in emit_receipts[:-1]
    ):
        _fail("verifier prior E_emit retry lacks its frozen interrupted attempt")
    if len(emit_receipts) == 2 and (
        emit_receipts[0]["end_utc"] != emit_receipts[1]["start_utc"]
    ):
        _fail("verifier E_emit retry does not start at the attempt-0 boundary")
    terminal_emit = emit_receipts[-1]
    if terminal_emit["exit_reason"] != "PHASE_COMPLETE" or terminal_emit["staging_disposition"] != "ATOMICALLY_PUBLISHED":
        _fail("verifier prior E_emit receipt is not a complete publication")
    prior_verifier_receipts = [
        receipt for receipt in receipts if receipt["phase"] == "V_replay"
    ]
    if [receipt["attempt_id"] for receipt in prior_verifier_receipts] not in (
        [],
        [0],
    ):
        _fail("prior V_replay receipts imply more than one frozen restart")
    if any(
        receipt["completed_unit_index"] != manifest["last_completed_unit_index"]
        for receipt in (*emit_receipts, *prior_verifier_receipts)
    ):
        _fail("verifier prior E/V receipt differs from the producer prefix")
    if any(
        receipt["staging_disposition"] == "ATOMICALLY_PUBLISHED"
        for receipt in prior_verifier_receipts
    ):
        _fail("a prior V_replay retry receipt already claims publication")
    if any(
        receipt["exit_reason"] != "EXTERNAL_INTERRUPTION"
        or receipt["staging_disposition"] != "DISCARDED"
        for receipt in prior_verifier_receipts
    ):
        _fail("prior V_replay retry lacks its frozen interrupted attempt")
    for receipt in receipts:
        if receipt["phase"] in {"C_setup", "C_core", "C_bundle_io", "E_emit", "V_replay"} and receipt["logical_run_id"] != logical_run_id:
            _fail("verifier prior current-run receipt has a different logical_run_id")
    emit_checkpoint = manifest["emit_start_checkpoint"]
    expected_emit_inputs = 4 if manifest["bundle_published"] else 0
    if (
        emit_checkpoint["completed_unit_count"] != manifest["completed_unit_count"]
        or emit_checkpoint["last_completed_unit_index"] != manifest["last_completed_unit_index"]
        or emit_checkpoint["input_file_count"] != expected_emit_inputs
        or emit_checkpoint["logical_run_id"] != logical_run_id
        or emit_checkpoint["start_utc"] != emit_receipts[-1]["start_utc"]
    ):
        _fail("E_emit checkpoint does not bind the successful phase attempt/prefix")
    chronological = sorted(
        receipts,
        key=lambda receipt: (
            _parse_utc_for_receipt(receipt["start_utc"]),
            phase_order[receipt["phase"]],
            receipt["attempt_id"],
        ),
    )
    for prior, following in zip(chronological, chronological[1:]):
        if _parse_utc_for_receipt(prior["end_utc"]) > _parse_utc_for_receipt(
            following["start_utc"]
        ):
            _fail("verifier prior phase attempts overlap")
    prior_cpu = sum(receipt["cpu_microseconds"] for receipt in receipts)
    prior_verifier_cpu = sum(
        receipt["cpu_microseconds"] for receipt in prior_verifier_receipts
    )
    prior_verifier_peak_rss = max(
        (receipt["peak_rss_bytes"] for receipt in prior_verifier_receipts),
        default=0,
    )
    prior_verifier_wall = sum(
        receipt["wall_nanoseconds"] for receipt in prior_verifier_receipts
    )
    return (
        prior_cpu,
        prior_verifier_cpu,
        prior_verifier_wall,
        prior_verifier_peak_rss,
    )


def _parse_utc_for_receipt(value: Any) -> _datetime.datetime:
    if not isinstance(value, str):
        _fail("receipt UTC is not a string")
    _validate_utc(value, "receipt UTC")
    return _datetime.datetime.fromisoformat(value[:-1] + "+00:00")


def _native_child_limits(cpu_seconds: int) -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))


def _validate_verifier_system_preflight(artifact_root: Path) -> None:
    if _artifact_entry_exists(artifact_root, "verifier") or _artifact_entry_exists(
        artifact_root, "verifier.staging"
    ):
        _fail("verifier publication target/staging already exists at preflight")


def _sample_native_process(pid: int) -> Optional[tuple[int, int]]:
    """Return root-process CPU microseconds and peak RSS, or None after exit."""

    try:
        stat_payload = Path(f"/proc/{pid}/stat").read_bytes()
        status_payload = Path(f"/proc/{pid}/status").read_bytes()
    except FileNotFoundError:
        return None
    closing = stat_payload.rfind(b")")
    if closing < 0:
        _fail("native watchdog observed malformed /proc stat")
    fields = stat_payload[closing + 2 :].split()
    if len(fields) < 13:
        _fail("native watchdog observed truncated /proc stat")
    try:
        ticks = int(fields[11]) + int(fields[12])
    except ValueError as error:
        raise VerificationContractError("native watchdog CPU fields are invalid") from error
    ticks_per_second = os.sysconf("SC_CLK_TCK")
    cpu_microseconds = ticks * 1_000_000 // ticks_per_second
    peak_kib = 0
    for line in status_payload.splitlines():
        if line.startswith((b"VmHWM:", b"VmRSS:")):
            parts = line.split()
            if len(parts) != 3 or parts[2] != b"kB":
                _fail("native watchdog observed malformed RSS status")
            try:
                peak_kib = max(peak_kib, int(parts[1]))
            except ValueError as error:
                raise VerificationContractError(
                    "native watchdog RSS field is invalid"
                ) from error
    return cpu_microseconds, peak_kib * 1024


def _kill_close_reap_native(process: subprocess.Popen[bytes]) -> str | None:
    """Kill one native process group, close its pipes, and must-reap once."""

    cleanup_errors: list[str] = []
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as error:
            cleanup_errors.append(f"killpg failed: {error}")
    for name, pipe in (
        ("stdin", process.stdin),
        ("stdout", process.stdout),
        ("stderr", process.stderr),
    ):
        if pipe is None or pipe.closed:
            continue
        try:
            pipe.close()
        except OSError as error:
            cleanup_errors.append(f"{name} close failed: {error}")
    while process.returncode is None:
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as error:
                cleanup_errors.append(f"repeated killpg failed: {error}")
        except InterruptedError:
            continue
        except (ChildProcessError, OSError) as error:
            cleanup_errors.append(f"native wait failed: {error}")
            break
    if process.returncode is None:
        cleanup_errors.append("native child remained non-waitable without a return code")
    return "; ".join(cleanup_errors) or None


def _exchange_native_bounded(
    process: subprocess.Popen[bytes],
    request_payload: bytes,
    stdout_budget: int,
    watchdog: Any,
) -> tuple[bytes, int, str]:
    """Full-duplex native exchange bounded by the registered evidence budget."""

    if stdout_budget < 0:
        _implementation_fail("native stdout budget is negative")
    if process.stdin is None or process.stdout is None or process.stderr is None:
        _implementation_fail("native verifier pipes are incomplete")
    stdin_pipe = process.stdin
    stdout_pipe = process.stdout
    stderr_pipe = process.stderr
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr_count = 0
    stderr_hasher = hashlib.sha256()
    request_offset = 0
    request_complete = False
    open_outputs = {"stdout", "stderr"}

    def close_registered(pipe: Any) -> None:
        try:
            selector.unregister(pipe)
        except KeyError:
            pass
        try:
            pipe.close()
        except OSError as error:
            _implementation_fail(f"cannot close native interface pipe: {error}")

    try:
        for pipe in (stdin_pipe, stdout_pipe, stderr_pipe):
            os.set_blocking(pipe.fileno(), False)
        selector.register(stdin_pipe, selectors.EVENT_WRITE, "stdin")
        selector.register(stdout_pipe, selectors.EVENT_READ, "stdout")
        selector.register(stderr_pipe, selectors.EVENT_READ, "stderr")
        next_watchdog = time.monotonic_ns()
        while process.poll() is None or open_outputs:
            now = time.monotonic_ns()
            if now >= next_watchdog:
                watchdog()
                next_watchdog = now + NATIVE_WATCHDOG_INTERVAL_NANOSECONDS
            timeout = max(
                0.0,
                min(
                    1.0,
                    (next_watchdog - time.monotonic_ns()) / 1_000_000_000,
                ),
            )
            try:
                events = selector.select(timeout)
            except OSError as error:
                if error.errno == errno.EINTR:
                    continue
                _implementation_fail(f"native interface selector failed: {error}")
            for key, _ in events:
                pipe = key.fileobj
                stream_name = key.data
                if stream_name == "stdin":
                    if request_offset == len(request_payload):
                        request_complete = True
                        close_registered(pipe)
                        continue
                    try:
                        written = os.write(
                            pipe.fileno(),
                            request_payload[
                                request_offset : request_offset + NATIVE_IO_CHUNK_BYTES
                            ],
                        )
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        close_registered(pipe)
                        continue
                    except OSError as error:
                        _implementation_fail(
                            f"native request transport write failed: {error}"
                        )
                    if written <= 0:
                        _implementation_fail("native request transport short write")
                    request_offset += written
                    if request_offset == len(request_payload):
                        request_complete = True
                        close_registered(pipe)
                    continue

                read_size = NATIVE_IO_CHUNK_BYTES
                if stream_name == "stdout":
                    read_size = min(
                        read_size,
                        stdout_budget + 1 - len(stdout),
                    )
                    if read_size <= 0:
                        _resource_fail(
                            "native verifier response cannot fit the registered "
                            "remaining research-evidence budget"
                        )
                try:
                    chunk = os.read(pipe.fileno(), read_size)
                except BlockingIOError:
                    continue
                except OSError as error:
                    _implementation_fail(
                        f"native {stream_name} transport read failed: {error}"
                    )
                if not chunk:
                    close_registered(pipe)
                    open_outputs.remove(stream_name)
                    continue
                if stream_name == "stdout":
                    stdout.extend(chunk)
                    if len(stdout) > stdout_budget:
                        _resource_fail(
                            "native verifier response cannot fit the registered "
                            "remaining research-evidence budget"
                        )
                else:
                    stderr_count += len(chunk)
                    stderr_hasher.update(chunk)

        if process.returncode is None:
            _implementation_fail("native verifier terminated without a return code")
        if process.returncode == 0 and not request_complete:
            _implementation_fail(
                "successful native verifier did not consume the complete request"
            )
        for pipe in (stdin_pipe, stdout_pipe, stderr_pipe):
            if not pipe.closed:
                close_registered(pipe)
        return bytes(stdout), stderr_count, stderr_hasher.hexdigest()
    finally:
        try:
            selector.close()
        except OSError as error:
            _implementation_fail(
                f"cannot close native interface selector: {error}"
            )


def invoke_independent_native_verifier(
    executable_path: Path,
    executable_descriptor: int,
    executable_metadata: os.stat_result,
    native_identity: Mapping[str, Any],
    request: Mapping[str, Any],
    artifact_handles: Mapping[str, Mapping[str, Any]],
    *,
    phase_start_monotonic_ns: int,
    prior_research_evidence_bytes: int,
    prior_study_cpu_microseconds: int,
    prior_verifier_cpu_microseconds: int,
    prior_verifier_wall_nanoseconds: int,
    prior_verifier_peak_rss_bytes: int,
) -> tuple[Mapping[str, Any], list[str], str, int, int]:
    """Invoke the independent native replay target without a shell."""

    if executable_descriptor != NATIVE_EXEC_FD:
        _fail("native executable is not bound to the frozen execution descriptor")
    if executable_path.name != NATIVE_BASENAME:
        _fail(f"native verifier must be a regular executable named {NATIVE_BASENAME!r}")
    if native_identity["identity_path"] != NATIVE_IDENTITY_PATH:
        _fail("native verifier identity path is not the reviewed verifier target")
    if executable_metadata.st_mode & 0o111 == 0:
        _fail("native verifier lacks an executable mode bit")
    environment = os.environ.copy()
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        if environment.get(variable) != "1":
            _fail(f"native verifier inherited nonfrozen {variable}")
    command = [f"/proc/self/fd/{NATIVE_EXEC_FD}", "verify-canonical-request"]
    command_sha256 = sha256_bytes(canonical_json_without_lf(command))
    if request["native_child_argv_sha256"] != command_sha256:
        _fail("native request does not bind the exact frozen child argv")
    now = time.monotonic_ns()
    self_cpu, self_rss = _resource_usage(0)
    child_cpu, child_rss = _resource_usage(-1)
    current_cpu = self_cpu + child_cpu
    current_wall = now - phase_start_monotonic_ns
    if current_wall < 0:
        _fail("native preflight phase start is in the future")
    remaining_cpu = min(
        PHASE_CPU_CAP_MICROSECONDS
        - prior_verifier_cpu_microseconds
        - current_cpu
        - PUBLICATION_CPU_RESERVE_MICROSECONDS,
        STUDY_CPU_CAP_MICROSECONDS
        - prior_study_cpu_microseconds
        - current_cpu
        - PUBLICATION_CPU_RESERVE_MICROSECONDS,
    )
    remaining_wall = (
        PHASE_WALL_CAP_NANOSECONDS
        - prior_verifier_wall_nanoseconds
        - current_wall
        - PUBLICATION_WALL_RESERVE_NANOSECONDS
    )
    if remaining_cpu <= 0 or remaining_wall <= 0:
        _resource_fail("native verifier lacks the frozen publication resource reserve")
    if max(prior_verifier_peak_rss_bytes, self_rss, child_rss) > PHASE_PEAK_RSS_CAP_BYTES:
        _resource_fail("native verifier preflight already exceeds the peak-RSS ceiling")
    cpu_limit_seconds = max(1, (remaining_cpu + 999_999) // 1_000_000)
    request_payload = canonical_json_document(dict(request))
    if len(request_payload) > 1 << 20:
        _fail("native verifier canonical request exceeds 1 MiB")
    _require_nonnegative_integer(
        prior_research_evidence_bytes,
        "prior_research_evidence_bytes",
    )
    if prior_research_evidence_bytes > RESEARCH_EVIDENCE_CAP_BYTES:
        _resource_fail("prior research evidence already exceeds its registered ceiling")
    stdout_budget = (
        RESEARCH_EVIDENCE_CAP_BYTES - prior_research_evidence_bytes
    )
    artifact_fds = tuple(
        sorted(handle["fd"] for handle in artifact_handles.values())
    )
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        cwd=REPOSITORY_ROOT,
        pass_fds=(NATIVE_EXEC_FD, *artifact_fds),
        env=environment,
        start_new_session=True,
        preexec_fn=lambda: _native_child_limits(cpu_limit_seconds),
    )

    def enforce_native_watchdog() -> None:
        sample = _sample_native_process(process.pid)
        if sample is None:
            return
        native_cpu, native_rss = sample
        current = time.monotonic_ns()
        self_now_cpu, self_now_rss = _resource_usage(0)
        child_now_cpu, child_now_rss = _resource_usage(-1)
        watchdog_cpu = max(
            self_now_cpu + child_now_cpu + native_cpu,
            current_cpu + native_cpu,
        )
        reserve_crossed = (
            prior_verifier_cpu_microseconds
            + watchdog_cpu
            + PUBLICATION_CPU_RESERVE_MICROSECONDS
            > PHASE_CPU_CAP_MICROSECONDS
            or prior_study_cpu_microseconds
            + watchdog_cpu
            + PUBLICATION_CPU_RESERVE_MICROSECONDS
            > STUDY_CPU_CAP_MICROSECONDS
            or prior_verifier_wall_nanoseconds
            + (current - phase_start_monotonic_ns)
            + PUBLICATION_WALL_RESERVE_NANOSECONDS
            > PHASE_WALL_CAP_NANOSECONDS
            or max(
                prior_verifier_peak_rss_bytes,
                self_now_rss,
                child_now_rss,
                native_rss,
            )
            > PHASE_PEAK_RSS_CAP_BYTES
        )
        if reserve_crossed:
            _resource_fail(
                "native verifier watchdog preserved the publication reserve"
            )

    try:
        stdout, stderr_count, stderr_identity = _exchange_native_bounded(
            process,
            request_payload,
            stdout_budget,
            enforce_native_watchdog,
        )
    except BaseException as primary_error:
        cleanup_error = _kill_close_reap_native(process)
        if cleanup_error is not None:
            if isinstance(
                primary_error,
                (VerificationImplementationError, VerificationContractError),
            ) and not isinstance(
                primary_error,
                (
                    VerificationEvidenceError,
                    VerificationResourceError,
                    VerificationExternalInterruption,
                ),
            ):
                primary_error.detail = (
                    f"{primary_error.detail}; native cleanup: {cleanup_error}"
                )
                primary_error.args = (primary_error.detail,)
            else:
                raise VerificationImplementationError(
                    "native exchange cleanup failed after "
                    f"{type(primary_error).__name__}: {primary_error}; "
                    f"cleanup: {cleanup_error}"
                ) from primary_error
        raise
    if process.returncode != 0:
        terminal_now = time.monotonic_ns()
        terminal_self_cpu, terminal_self_rss = _resource_usage(0)
        terminal_child_cpu, terminal_child_rss = _resource_usage(-1)
        terminal_resource_crossed = (
            prior_verifier_cpu_microseconds
            + terminal_self_cpu
            + terminal_child_cpu
            + PUBLICATION_CPU_RESERVE_MICROSECONDS
            > PHASE_CPU_CAP_MICROSECONDS
            or prior_study_cpu_microseconds
            + terminal_self_cpu
            + terminal_child_cpu
            + PUBLICATION_CPU_RESERVE_MICROSECONDS
            > STUDY_CPU_CAP_MICROSECONDS
            or prior_verifier_wall_nanoseconds
            + terminal_now
            - phase_start_monotonic_ns
            + PUBLICATION_WALL_RESERVE_NANOSECONDS
            > PHASE_WALL_CAP_NANOSECONDS
            or max(
                prior_verifier_peak_rss_bytes,
                terminal_self_rss,
                terminal_child_rss,
            )
            > PHASE_PEAK_RSS_CAP_BYTES
        )
        if terminal_resource_crossed:
            _resource_fail(
                "independent native verifier stopped at a registered resource ceiling: "
                f"exit={process.returncode}, stderr_bytes={stderr_count}, "
                f"stderr_sha256={stderr_identity}"
            )
        if process.returncode < 0:
            raise VerificationExternalInterruption(
                "independent native verifier was externally signalled: "
                f"signal={-process.returncode}, stderr_bytes={stderr_count}, "
                f"stderr_sha256={stderr_identity}"
            )
        _implementation_fail(
            "independent native verifier failed: "
            f"exit={process.returncode}, stderr_bytes={stderr_count}, "
            f"stderr_sha256={stderr_identity}"
        )
    if stderr_count:
        _fail(
            "successful native verifier emitted stderr: "
            f"bytes={stderr_count}, sha256={stderr_identity}"
        )
    response = _require_mapping(
        parse_canonical_json_document(stdout, "native verifier response"),
        "native verifier response",
    )
    expected_keys = {
        "artifact_kind",
        "build_manifest_sha256",
        "complete",
        "decision_counts_observed",
        "discrepancies",
        "input_identity_sha256",
        "native_binary_sha256",
        "native_child_argv_sha256",
        "producer_manifest_sha256",
        "schema_version",
        "source_manifest_sha256",
    }
    if set(response) != expected_keys:
        _fail("native verifier response has a nonfrozen key set")
    if response["artifact_kind"] != "a4_v2_native_replay" or response["schema_version"] != 1:
        _fail("native verifier response identity mismatch")
    if not isinstance(response["complete"], bool):
        _fail("native verifier complete flag is not boolean")
    if response["producer_manifest_sha256"] != request["producer_manifest_sha256"]:
        _fail("native verifier response is not bound to producer manifest")
    if response["input_identity_sha256"] != request["input_identity_sha256"]:
        _fail("native verifier response is not bound to input identity")
    for key in (
        "build_manifest_sha256",
        "native_binary_sha256",
        "native_child_argv_sha256",
        "source_manifest_sha256",
    ):
        if response[key] != request[key]:
            _fail(f"native verifier response is not bound to {key}")
    counts = _require_mapping(response["decision_counts_observed"], "native counts")
    if tuple(counts.keys()) != tuple(sorted(DECISION_COUNT_KEYS)):
        _fail("native decision counts lack the exact canonical key set")
    if any(not isinstance(counts[key], int) or isinstance(counts[key], bool) or counts[key] < 0 for key in counts):
        _fail("native decision counts contain a nonnegative-integer violation")
    discrepancies = _require_list(response["discrepancies"], "native discrepancies")
    discrepancy_keys = {"class", "expected_sha256", "location", "message", "observed_sha256"}
    for index, discrepancy in enumerate(discrepancies):
        item = _require_mapping(discrepancy, f"native discrepancy {index}")
        if set(item) != discrepancy_keys:
            _fail("native discrepancy has a nonfrozen key set")
        if not isinstance(item["class"], str) or not item["class"]:
            _fail("native discrepancy class is empty")
        if not isinstance(item["location"], str) or not item["location"]:
            _fail("native discrepancy location is empty")
        if not isinstance(item["message"], str):
            _fail("native discrepancy message is not a string")
        for key in ("expected_sha256", "observed_sha256"):
            if item[key] is not None:
                _require_sha256(item[key], f"native discrepancy {key}")
    if (not response["complete"] or counts != request.get("decision_counts_expected")) and not discrepancies:
        _fail("incomplete or count-mismatching native replay lacks a discrepancy")
    return (
        response,
        command,
        command_sha256,
        len(stdout),
        stderr_count,
    )


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        try:
            written = os.write(descriptor, payload[offset:])
        except OSError as error:
            raise VerificationEvidenceError(
                f"cannot write verifier output: {error}"
            ) from error
        if written <= 0:
            _evidence_fail("short write while publishing verifier output")
        offset += written


def _resource_usage(which: int) -> tuple[int, int]:
    if _GETRUSAGE is None:
        _implementation_fail(
            "getrusage is unavailable for the verifier prepublication ceiling check"
        )
    usage = _Rusage()
    if _GETRUSAGE(which, ctypes.byref(usage)) != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))
    cpu = (
        usage.ru_utime.tv_sec * 1_000_000
        + usage.ru_utime.tv_usec
        + usage.ru_stime.tv_sec * 1_000_000
        + usage.ru_stime.tv_usec
    )
    return cpu, usage.ru_maxrss * 1024


def _validate_prepublication_resource_ceiling(
    *,
    phase_start_monotonic_ns: int,
    prior_study_cpu_microseconds: int,
    prior_research_evidence_bytes: int,
    prior_verifier_cpu_microseconds: int,
    prior_verifier_wall_nanoseconds: int,
    prior_verifier_peak_rss_bytes: int,
    summary_size: int,
) -> None:
    _require_nonnegative_integer(
        phase_start_monotonic_ns, "phase_start_monotonic_ns"
    )
    now = time.monotonic_ns()
    if phase_start_monotonic_ns > now:
        _implementation_fail("verifier phase monotonic start is in the future")
    self_cpu, self_rss = _resource_usage(0)
    child_cpu, child_rss = _resource_usage(-1)
    cpu = self_cpu + child_cpu
    wall = now - phase_start_monotonic_ns
    peak_rss = max(self_rss, child_rss)
    live_owned_bytes = summary_size
    if (
        prior_verifier_cpu_microseconds
        + cpu
        + PUBLICATION_CPU_RESERVE_MICROSECONDS
        > PHASE_CPU_CAP_MICROSECONDS
    ):
        _resource_fail("V_replay lacks the CPU reserve required for atomic publication")
    if (
        prior_verifier_wall_nanoseconds
        + wall
        + PUBLICATION_WALL_RESERVE_NANOSECONDS
        > PHASE_WALL_CAP_NANOSECONDS
    ):
        _resource_fail("V_replay lacks the wall reserve required for atomic publication")
    if max(prior_verifier_peak_rss_bytes, peak_rss) > PHASE_PEAK_RSS_CAP_BYTES:
        _resource_fail("V_replay peak-RSS ceiling crossed before verifier publication")
    if live_owned_bytes > OWNED_LIVE_TEMPORARY_CAP_BYTES:
        _resource_fail("V_replay owned-live-byte ceiling crossed before verifier publication")
    if summary_size > RESEARCH_EVIDENCE_CAP_BYTES:
        _resource_fail("V_replay research-evidence byte ceiling crossed before publication")
    if (
        prior_study_cpu_microseconds
        + cpu
        + PUBLICATION_CPU_RESERVE_MICROSECONDS
        > STUDY_CPU_CAP_MICROSECONDS
    ):
        _resource_fail("global T_study lacks the CPU reserve required for publication")
    if prior_research_evidence_bytes + summary_size > RESEARCH_EVIDENCE_CAP_BYTES:
        _resource_fail(
            "global research-evidence/archive byte ceiling crossed before verifier publication"
        )


def atomically_publish_verifier_summary(
    artifact_root: Path, summary: Mapping[str, Any]
) -> None:
    try:
        _atomically_publish_verifier_summary(artifact_root, summary)
    except VerificationContractError:
        raise
    except OSError as error:
        raise VerificationEvidenceError(
            f"cannot atomically publish verifier summary: {error}"
        ) from error


def _atomically_publish_verifier_summary(
    artifact_root: Path, summary: Mapping[str, Any]
) -> None:
    payload = canonical_json_document(dict(summary))
    root_descriptor = _open_artifact_root(artifact_root)
    try:
        for name in ("verifier", "verifier.staging"):
            try:
                os.stat(name, dir_fd=root_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                continue
            _fail("verifier target or staging directory already exists")
        os.mkdir("verifier.staging", 0o700, dir_fd=root_descriptor)
        staging_descriptor = os.open(
            "verifier.staging",
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
                "verifier_summary.json", flags, 0o600, dir_fd=staging_descriptor
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
            "verifier.staging",
            root_descriptor,
            "verifier",
        )
        os.fsync(root_descriptor)
    finally:
        os.close(root_descriptor)


def _parse_control_request(payload: bytes) -> dict[str, Any]:
    control = dict(
        _require_mapping(
            parse_canonical_json_document(payload, "verifier control request"),
            "verifier control request",
        )
    )
    expected_keys = {
        "artifact_root",
        "build_manifest",
        "logical_run_id",
        "native_verifier",
        "par_review_binding",
        "phase_start_monotonic_ns",
        "prior_phase_receipts",
        "prior_research_evidence_bytes",
        "prior_study_cpu_microseconds",
        "protocol",
        "schema",
        "source_manifest",
        "start_utc",
    }
    if set(control) != expected_keys:
        _fail("verifier control request does not have the exact frozen key set")
    if not isinstance(control["artifact_root"], str):
        _fail("verifier artifact_root is not a string")
    _require_sha256(control["logical_run_id"], "logical_run_id")
    _validate_utc(control["start_utc"], "verifier start UTC")
    _require_nonnegative_integer(
        control["phase_start_monotonic_ns"], "phase_start_monotonic_ns"
    )
    _require_nonnegative_integer(
        control["prior_research_evidence_bytes"],
        "prior_research_evidence_bytes",
    )
    _require_nonnegative_integer(
        control["prior_study_cpu_microseconds"],
        "prior_study_cpu_microseconds",
    )
    _require_list(control["prior_phase_receipts"], "prior_phase_receipts")
    for key in (
        "build_manifest",
        "native_verifier",
        "par_review_binding",
        "protocol",
        "schema",
        "source_manifest",
    ):
        _, item = _sealed_file_request(control[key], key)
        control[key] = item
    return control


def verify_and_publish(control: Mapping[str, Any], _control_payload_size: int) -> dict[str, Any]:
    root = _normalized_absolute_directory(Path(control["artifact_root"]), "artifact root")
    logical_run_id = control["logical_run_id"]
    start_utc = control["start_utc"]
    protocol_bytes = _read_reviewed_sealed_file(
        control["protocol"], "preregistration", maximum_bytes=4 << 20
    )
    schema_bytes = _read_reviewed_sealed_file(
        control["schema"], "artifact schema", maximum_bytes=4 << 20
    )
    source_manifest_bytes = _read_reviewed_sealed_file(
        control["source_manifest"], "source manifest", maximum_bytes=16 << 20
    )
    build_manifest_bytes = _read_reviewed_sealed_file(
        control["build_manifest"], "build manifest", maximum_bytes=16 << 20
    )
    par_review_binding_bytes = _read_reviewed_sealed_file(
        control["par_review_binding"],
        "PAR independent-review binding",
        maximum_bytes=16 << 20,
    )
    native_command = [f"/proc/self/fd/{NATIVE_EXEC_FD}", "verify-canonical-request"]
    _, seal_registry, authority_components = _validate_protocol_authority(
        protocol_bytes, control["protocol"], control["schema"]
    )
    source_manifest = _validate_source_manifest(
        source_manifest_bytes,
        control["protocol"],
        control["schema"],
        authority_components,
    )
    if control["source_manifest"]["identity_path"] != "docs/saq_a4_v2_implementation_manifest_2026_07_14.json":
        _fail("verifier source-manifest path is not frozen")
    if (
        control["build_manifest"]["identity_path"]
        != source_manifest["par_contract"]["build_manifest_path"]
        or control["native_verifier"]["identity_path"]
        != source_manifest["par_contract"]["verifier_binary_identity_path"]
    ):
        _fail("control build/native paths differ from the reviewed PAR contract")
    build_manifest = _validate_build_manifest(
        build_manifest_bytes,
        control["source_manifest"],
        control["protocol"],
        control["schema"],
        schema_bytes,
        control["native_verifier"],
        source_manifest,
        native_command,
    )
    git_authority, par_phase_receipts = _validate_par_review_binding(
        par_review_binding_bytes,
        control["par_review_binding"],
        seal_registry,
        source_manifest,
        build_manifest,
        control["build_manifest"],
        control["source_manifest"],
        control["protocol"],
        control["schema"],
        control["native_verifier"],
    )
    registry, manifest, payloads, artifact_handles, input_file_count = _load_and_validate_inputs(
        root,
        protocol_bytes,
        control["protocol"],
        schema_bytes,
        control["schema"],
    )
    current_receipts = [
        receipt
        for receipt in manifest["phase_receipts_through_instrument"]
        if receipt["phase"] in {"C_setup", "C_core", "C_bundle_io"}
    ]
    if not current_receipts or any(
        receipt["logical_run_id"] != logical_run_id for receipt in current_receipts
    ):
        _fail("verifier logical_run_id does not match every producer C-phase receipt")
    source_identity = _require_mapping(
        manifest["source_identity"], "producer source identity"
    )
    if (
        source_identity["clean_tree"] is not True
        or source_identity["source_tree_sha256"]
        != source_manifest["source_tree_sha256"]
    ):
        _fail("producer source identity differs from the reviewed source closure")
    execution_commit = _require_git_oid(
        source_identity["execution_commit"], "producer execution commit"
    )
    _validate_git_execution_authority(
        git_authority,
        execution_commit,
        source_manifest,
        source_manifest_bytes,
    )
    (
        prior_study_cpu,
        prior_verifier_cpu,
        prior_verifier_wall,
        prior_verifier_peak_rss,
    ) = _validate_prior_phase_receipts(
        registry,
        control["prior_phase_receipts"],
        manifest,
        logical_run_id,
        build_manifest["implementation_commit"],
        execution_commit,
        par_phase_receipts,
    )
    if prior_study_cpu != control["prior_study_cpu_microseconds"]:
        _implementation_fail(
            "trusted prior-study CPU differs from exact prior phase receipts"
        )
    published_evidence_bytes = sum(len(payloads[path]) for path in EVIDENCE_PATHS)
    exact_prior_research_evidence_bytes = (
        git_authority["par_research_evidence_bytes"] + published_evidence_bytes
    )
    if (
        control["prior_research_evidence_bytes"]
        != exact_prior_research_evidence_bytes
    ):
        _implementation_fail(
            "trusted prior evidence bytes differ from exact PAR plus producer evidence"
        )
    if control["prior_research_evidence_bytes"] > RESEARCH_EVIDENCE_CAP_BYTES:
        _resource_fail("trusted prior evidence bytes already exceed the global ceiling")
    producer_manifest_payload = payloads["evidence/producer_manifest.json"]
    _validate_verifier_system_preflight(root)
    native_command_sha256 = sha256_bytes(canonical_json_without_lf(native_command))
    request = _native_request(
        control["protocol"],
        control["schema"],
        control["source_manifest"],
        control["build_manifest"],
        control["native_verifier"],
        native_command_sha256,
        manifest,
        producer_manifest_payload,
        artifact_handles,
    )
    native_path = Path(control["native_verifier"]["read_path"])
    native_descriptor, native_metadata = _open_and_validate_sealed_file(
        native_path,
        "native verifier",
        expected_size_bytes=control["native_verifier"]["size_bytes"],
        expected_sha256=control["native_verifier"]["sha256"],
    )
    try:
        if native_descriptor != NATIVE_EXEC_FD:
            try:
                os.fstat(NATIVE_EXEC_FD)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise
            else:
                _implementation_fail(
                    f"frozen native execution fd {NATIVE_EXEC_FD} is already occupied"
                )
            os.dup2(native_descriptor, NATIVE_EXEC_FD, inheritable=True)
            os.close(native_descriptor)
            native_descriptor = NATIVE_EXEC_FD
        else:
            os.set_inheritable(native_descriptor, True)
        (
            response,
            observed_native_command,
            observed_native_command_sha256,
            _native_stdout_size,
            _native_stderr_size,
        ) = _run_as_verifier_implementation(
            lambda: invoke_independent_native_verifier(
                native_path,
                native_descriptor,
                native_metadata,
                control["native_verifier"],
                request,
                artifact_handles,
                phase_start_monotonic_ns=control["phase_start_monotonic_ns"],
                prior_research_evidence_bytes=control[
                    "prior_research_evidence_bytes"
                ],
                prior_study_cpu_microseconds=prior_study_cpu,
                prior_verifier_cpu_microseconds=prior_verifier_cpu,
                prior_verifier_wall_nanoseconds=prior_verifier_wall,
                prior_verifier_peak_rss_bytes=prior_verifier_peak_rss,
            )
        )
        _revalidate_sealed_fd_and_path(
            native_descriptor,
            native_path,
            "native verifier",
            native_metadata,
            control["native_verifier"]["sha256"],
        )
        for handle in artifact_handles.values():
            revalidate_immutable_artifact(root, handle)
        _require_exact_regular_directory(
            root / "evidence",
            [PurePosixPath(path).name for path in EVIDENCE_PATHS],
            "post-replay producer evidence directory",
        )
        if manifest["bundle_published"]:
            _require_exact_regular_directory(
                root / "bundle",
                [PurePosixPath(path).name for path in BUNDLE_PATHS],
                "post-replay producer bundle directory",
            )
        elif _artifact_entry_exists(root, "bundle"):
            _fail("bundle directory appeared during native replay")
    finally:
        primary_error = sys.exc_info()[1]
        close_errors: list[str] = []
        try:
            os.close(native_descriptor)
        except OSError as error:
            close_errors.append(f"native descriptor close failed: {error}")
        close_errors.extend(close_immutable_artifacts(artifact_handles))
        if close_errors:
            detail = "; ".join(close_errors)
            if isinstance(
                primary_error,
                (VerificationImplementationError, VerificationContractError),
            ) and not isinstance(
                primary_error,
                (
                    VerificationEvidenceError,
                    VerificationResourceError,
                    VerificationExternalInterruption,
                ),
            ):
                primary_error.detail = f"{primary_error.detail}; cleanup: {detail}"
                primary_error.args = (primary_error.detail,)
            elif primary_error is None:
                _implementation_fail(detail)
            else:
                raise VerificationImplementationError(
                    "verifier descriptor cleanup failed after "
                    f"{type(primary_error).__name__}: {primary_error}; "
                    f"cleanup: {detail}"
                ) from primary_error
    if observed_native_command != native_command or observed_native_command_sha256 != native_command_sha256:
        _implementation_fail(
            "observed native child argv differs from the frozen invocation identity"
        )
    observed_counts = dict(response["decision_counts_observed"])
    discrepancies = list(response["discrepancies"])
    if not response["complete"]:
        status = "INCOMPLETE"
    elif observed_counts != manifest["record_counts"] or discrepancies:
        status = "MISMATCH"
    else:
        status = "VERIFIED"
    summary = {
        "artifact_kind": "a4_verifier_summary",
        "decision_counts_expected": dict(manifest["record_counts"]),
        "decision_counts_observed": observed_counts,
        "discrepancies": discrepancies,
        "independence_attestations": list(INDEPENDENCE_ATTESTATIONS),
        "input_identity": manifest["input_identity"]["input_identity_sha256"],
        "producer_identity": sha256_bytes(producer_manifest_payload),
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "verifier_start_checkpoint": {
            "completed_unit_count": manifest["completed_unit_count"],
            "input_file_count": input_file_count,
            "last_completed_unit_index": manifest["last_completed_unit_index"],
            "logical_run_id": logical_run_id,
            "phase": "V_replay",
            "start_utc": start_utc,
        },
    }
    summary_payload = _run_as_verifier_implementation(
        lambda: canonical_json_document(summary)
    )
    _run_as_verifier_implementation(
        lambda: registry.validate_definition(
            summary, "verifier_summary_v2", "verifier_summary"
        )
    )
    summary_size = len(summary_payload)
    if summary_size < _native_stdout_size:
        _implementation_fail(
            "native response-to-summary transport dominance proof failed"
        )
    _validate_prepublication_resource_ceiling(
        phase_start_monotonic_ns=control["phase_start_monotonic_ns"],
        prior_study_cpu_microseconds=prior_study_cpu,
        prior_research_evidence_bytes=control["prior_research_evidence_bytes"],
        prior_verifier_cpu_microseconds=prior_verifier_cpu,
        prior_verifier_wall_nanoseconds=prior_verifier_wall,
        prior_verifier_peak_rss_bytes=prior_verifier_peak_rss,
        summary_size=summary_size,
    )
    atomically_publish_verifier_summary(root, summary)
    return {
        "native_binary_sha256": control["native_verifier"]["sha256"],
        "native_binary_size_bytes": control["native_verifier"]["size_bytes"],
        "native_child_argv": observed_native_command,
        "native_child_argv_sha256": observed_native_command_sha256,
        "status": status,
        "verifier_summary_sha256": sha256_bytes(summary_payload),
        "verifier_summary_size_bytes": summary_size,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("command", choices=("verify-canonical-request",))
    parser.add_argument("--control-fd", required=True, type=int, choices=(CONTROL_FD,))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    # The supervisor blocks SIGINT before exec so interpreter startup cannot
    # synthesize exit 130.  Own the phase only after raw-signal semantics are
    # installed; a pending wrapper SIGINT then terminates by SIGINT.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT})
    try:
        args = _parser().parse_args(argv)
    except SystemExit as error:
        print(
            f"A4-V2 verifier IMPLEMENTATION_INVALID: argv parse exited {error.code}",
            file=sys.stderr,
        )
        return 5
    try:
        payload = _read_all_from_fixed_fd(args.control_fd, "verifier control", 1 << 20)
        os.close(args.control_fd)
        result = verify_and_publish(_parse_control_request(payload), len(payload))
        _write_all(sys.stdout.fileno(), canonical_json_document(result))
    except VerificationExternalInterruption as error:
        print(f"A4-V2 verifier external interruption: {error}", file=sys.stderr)
        return 6
    except VerificationContractError as error:
        exit_code = {
            "ARTIFACT_INVALID": 4,
            "EVIDENCE_INCOMPLETE_NO_DECISION": 2,
            "IMPLEMENTATION_INVALID": 5,
            "RESOURCE_INCOMPLETE_NO_DECISION": 3,
        }[error.status]
        print(f"A4-V2 verifier {error.status}: {error}", file=sys.stderr)
        return exit_code
    except OSError as error:
        print(f"A4-V2 verifier IMPLEMENTATION_INVALID: {error}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
