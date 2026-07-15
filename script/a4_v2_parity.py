#!/usr/bin/env python3
"""Frozen A4-V2 build/PAR conductor (source only in A4-V2-I).

This module is imported only by the marker-bearing bootstrap's ``par``
subcommand.  It defines the separately authorized future A4-V2-PAR event; it
must not be imported or executed during A4-V2-I.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import itertools
import json
import os
import platform
import re
import shlex
import shutil
import ssl
import stat
import struct
import subprocess
import sys
import time
import ctypes
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Mapping, NoReturn, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRODUCER_BINARY = REPOSITORY_ROOT / "build/a4_v2/a4_v2_native"
VERIFIER_BINARY = REPOSITORY_ROOT / "build/a4_v2_verifier/a4_v2_native"
IMPLEMENTATION_MANIFEST = (
    REPOSITORY_ROOT / "docs/saq_a4_v2_implementation_manifest_2026_07_14.json"
)
PROTOCOL = REPOSITORY_ROOT / "docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json"
SCHEMA = REPOSITORY_ROOT / "docs/saq_a4_v2_artifact_schema_2026_07_14.json"
EXPECTED_ARTIFACT_ROOT = (
    REPOSITORY_ROOT / "docs/saq_a4_v2_par_artifacts_2026_07_14"
)
HASH_DOMAIN = "saq-attempt4-a4-1-20260713-schema2"
PROTOCOL_VERSION = "saq-a4-v2-synthetic-construction-20260714-schema1"
SEED = 20260713
FIXED_FD = 197
PER_PHASE_CPU_LIMIT = 86_400_000_000
PER_PHASE_WALL_LIMIT = 172_800_000_000_000
STUDY_CPU_LIMIT = 518_400_000_000
TEMPORARY_LIMIT = 17_179_869_184
EVIDENCE_LIMIT = 4_294_967_296
RSS_LIMIT = 25_769_803_776
PAR_SEAL_EXACT_LIMIT = 5_171
PAR_SEAL_COARSE_LIMIT = 65_536
EXPECTED_PAR_ARGV = [
    "script/run_arbitrary_cardinality_a4_v2.py",
    "par",
    "docs/saq_a4_v2_par_artifacts_2026_07_14",
]
EXPECTED_THREAD_ENVIRONMENT = {
    "MKL_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
}
_LIBC = ctypes.CDLL(None, use_errno=True)
_RENAMEAT2 = _LIBC.renameat2
_RENAMEAT2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
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


_GETRUSAGE = _LIBC.getrusage
_GETRUSAGE.argtypes = [ctypes.c_int, ctypes.POINTER(_Rusage)]
_GETRUSAGE.restype = ctypes.c_int
_WAIT4 = _LIBC.wait4
_WAIT4.argtypes = [
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int),
    ctypes.c_int,
    ctypes.POINTER(_Rusage),
]
_WAIT4.restype = ctypes.c_int
_CURRENT_DIRECT_CHILD_PEAK_RSS = 0
CMAKE_BINARY = "/usr/local/software/cmake-4.0.3/bin/cmake"
NINJA_BINARY = "/usr/local/software/ninja-1.9.0/bin/ninja"
CXX_BINARY = "/usr/bin/c++"
EXPECTED_CMAKE_VERSION = "cmake version 4.0.3"
EXPECTED_NINJA_VERSION = "1.9.0"
EXPECTED_COMPILER_ID = "GCC"
EXPECTED_COMPILER_VERSION = "11.5.0 20240719 (Red Hat 11.5.0-14)"
EXPECTED_COMPILER_VERSION_LINE = (
    "c++ (GCC) 11.5.0 20240719 (Red Hat 11.5.0-14)"
)
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
COMPILE_FLAGS = (
    "-O3",
    "-fno-fast-math",
    "-ffp-contract=off",
    "-frounding-math",
    "-mfpmath=sse",
)
EXPECTED_COMPILE_FLAGS_STRING = " ".join(COMPILE_FLAGS)
EXPECTED_CPU_MODEL = "Intel(R) Core(TM) i9-10920X CPU @ 3.50GHz"
EXPECTED_GMP_VERSION = "6.2.0"
EXPECTED_MPFR_VERSION = "4.1.0-p9"
EXPECTED_OPENSSL_VERSION = "OpenSSL 3.5.5 27 Jan 2026"
EXPECTED_HOST_ENVIRONMENT = {
    "CPU": EXPECTED_CPU_MODEL,
    "GMP": EXPECTED_GMP_VERSION,
    "MPFR": EXPECTED_MPFR_VERSION,
    "MXCSR": "0x00001f80; FTZ=false; DAZ=false",
    "NumPy": "1.23.5",
    "OpenSSL": "3.5.5 27 Jan 2026",
    "Python": "CPython 3.9.25",
    "allowed_affinity": "0-23",
    "compiler": f"GCC {EXPECTED_COMPILER_VERSION}",
    "compiler_flags": list(COMPILE_FLAGS),
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
PARITY_INVENTORY = {
    "allocation_decision_count": 2_433_600,
    "block_case_count": 64,
    "block_microfixture_count": 5,
    "block_rng": {
        "algorithm": "PCG64",
        "seed": SEED,
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
        "seed": SEED,
        "stream_scope": "scalar_256_only",
    },
}
PRODUCER_CMAKE_SOURCES = (
    "research/a4_v2/a4_v2_native.cpp",
    "research/a4_v2/block_vq.cpp",
    "research/a4_v2/exact_quantizer.cpp",
    "research/a4_v2/native_cli.cpp",
    "research/a4_v2/numeric_runtime.cpp",
    "research/a4_v2/representation.cpp",
)
VERIFIER_CMAKE_SOURCES = (
    "research/a4_v2_verifier/a4_v2_native.cpp",
    "research/a4_v2_verifier/exact_reference.cpp",
    "research/a4_v2_verifier/input_panel.cpp",
    "research/a4_v2_verifier/json_value.cpp",
    "research/a4_v2_verifier/parity_cli.cpp",
    "research/a4_v2_verifier/replay.cpp",
    "research/a4_v2_verifier/representation_parity.cpp",
    "research/a4_v2_verifier/sha256.cpp",
)
BUILD_ARTIFACT_NAMES = tuple(
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
PARITY_ARTIFACT_NAMES = (
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


class ParityFailure(RuntimeError):
    pass


class ExternalPhaseSignal(ParityFailure):
    """A metered B/P child was terminated by an external POSIX signal."""

    def __init__(
        self,
        signal_number: int,
        *,
        phase_peak_rss_bytes: int = 0,
        retry_safe: bool = True,
    ):
        super().__init__(f"external signal {signal_number}")
        self.signal_number = signal_number
        self.phase_peak_rss_bytes = phase_peak_rss_bytes
        self.retry_safe = retry_safe


@dataclass(frozen=True)
class _WaitResult:
    exit_code: int
    cpu_microseconds: int
    peak_rss_bytes: int


@dataclass(frozen=True)
class _WorkerHandle:
    pid: int
    result_fd: int
    release_fd: int
    supervisor_start_hwm: int


def _timeval_microseconds(value: _Timeval) -> int:
    if value.tv_sec < 0 or not 0 <= value.tv_usec < 1_000_000:
        _fail("noncanonical getrusage timeval")
    return int(value.tv_sec) * 1_000_000 + int(value.tv_usec)


def _one_rusage(who: int) -> _Rusage:
    value = _Rusage()
    if _GETRUSAGE(who, ctypes.byref(value)) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))
    return value


def _self_peak_rss_bytes() -> int:
    return max(int(_one_rusage(0).ru_maxrss), 0) * 1024


def _wait4_integer(pid: int) -> _WaitResult:
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
    return _WaitResult(
        exit_code=os.waitstatus_to_exitcode(status.value),
        cpu_microseconds=(
            _timeval_microseconds(usage.ru_utime)
            + _timeval_microseconds(usage.ru_stime)
        ),
        peak_rss_bytes=max(int(usage.ru_maxrss), 0) * 1024,
    )


def _wait_subprocess(process: subprocess.Popen[Any]) -> _WaitResult:
    global _CURRENT_DIRECT_CHILD_PEAK_RSS

    result = _wait4_integer(process.pid)
    process.returncode = result.exit_code
    _CURRENT_DIRECT_CHILD_PEAK_RSS = max(
        _CURRENT_DIRECT_CHILD_PEAK_RSS, result.peak_rss_bytes
    )
    return result


def _fail(message: str) -> NoReturn:
    raise ParityFailure(message)


def _canonical_body(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_document(value: Any) -> bytes:
    return _canonical_body(value) + b"\n"


def _parse_json(payload: bytes, description: str, *, canonical: bool = False) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                _fail(f"duplicate key in {description}: {key}")
            result[key] = value
        return result

    def reject(token: str) -> NoReturn:
        _fail(f"forbidden JSON numeric token in {description}: {token}")

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
            parse_float=reject,
            parse_constant=reject,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as error:
        raise ParityFailure(f"invalid {description}: {error}") from error
    if canonical and _canonical_document(value) != payload:
        _fail(f"{description} is not canonical JSON")
    return value


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _utc_now() -> str:
    value = time.time_ns()
    seconds, nanoseconds = divmod(value, 1_000_000_000)
    prefix = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(seconds))
    return f"{prefix}.{nanoseconds // 1000:06d}Z"


def _utc_for_monotonic(monotonic_ns: int) -> str:
    realtime = time.time_ns() - (time.monotonic_ns() - monotonic_ns)
    seconds, nanoseconds = divmod(realtime, 1_000_000_000)
    prefix = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(seconds))
    return f"{prefix}.{nanoseconds // 1000:06d}Z"


def _self_start_time_clock_ticks() -> int:
    """Read the leader's lossless Linux /proc start-time identity."""

    payload = Path(f"/proc/{os.getpid()}/stat").read_bytes()
    opening = payload.find(b"(")
    closing = payload.rfind(b") ")
    if opening <= 0 or closing <= opening:
        _fail("PAR leader /proc stat framing is ambiguous")
    pid_token = payload[:opening].strip()
    tail = payload[closing + 2 :].strip().split()
    if (
        pid_token != str(os.getpid()).encode("ascii")
        or len(tail) < 20
        or re.fullmatch(rb"(?:0|[1-9][0-9]*)", tail[19]) is None
    ):
        _fail("PAR leader /proc stat identity is invalid")
    value = int(tail[19])
    if value <= 0:
        _fail("PAR leader start-time clock ticks are not positive")
    return value


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
        _fail("PAR CPU model inventory is missing or heterogeneous")
    return values[0]


def _observed_host_environment() -> dict[str, Any]:
    """Observe every frozen host field material to B/P timing."""

    compiler_version = _capture((CXX_BINARY, "--version")).decode(
        "utf-8", errors="strict"
    )
    if (
        not compiler_version.splitlines()
        or compiler_version.splitlines()[0] != EXPECTED_COMPILER_VERSION_LINE
    ):
        _fail("PAR compiler environment differs from the frozen identity")
    observed = {
        "CPU": _cpu_model(),
        # GMP/MPFR, flags, rounding, and MXCSR are independently observed by
        # both native manifests before any successful B receipt is sealed.
        "GMP": EXPECTED_GMP_VERSION,
        "MPFR": EXPECTED_MPFR_VERSION,
        "MXCSR": "0x00001f80; FTZ=false; DAZ=false",
        "NumPy": importlib.metadata.version("numpy"),
        "OpenSSL": ssl.OPENSSL_VERSION.removeprefix("OpenSSL "),
        "Python": f"{platform.python_implementation()} {platform.python_version()}",
        "allowed_affinity": _affinity_text(set(os.sched_getaffinity(0))),
        "compiler": f"GCC {EXPECTED_COMPILER_VERSION}",
        "compiler_flags": list(COMPILE_FLAGS),
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
    if observed != EXPECTED_HOST_ENVIRONMENT:
        _fail("PAR observed host differs from the frozen environment")
    return observed


def _numpy_distribution_authority() -> dict[str, Any]:
    distribution = importlib.metadata.distribution("numpy")
    if distribution.version != "1.23.5" or distribution.files is None:
        _fail("registered NumPy distribution version changed")
    files = []
    for relative in distribution.files:
        path = Path(distribution.locate_file(relative)).resolve()
        try:
            path.relative_to(REPOSITORY_ROOT)
        except ValueError:
            pass
        else:
            _fail("registered NumPy authority resolves inside the repository")
        payload = _read_regular_nofollow(path)
        files.append(
            {
                "path": path.as_posix(),
                "sha256": _sha256(payload),
                "size_bytes": len(payload),
            }
        )
    files.sort(key=lambda item: item["path"].encode("utf-8"))
    if not files or len({item["path"] for item in files}) != len(files):
        _fail("registered NumPy distribution closure is empty or duplicated")
    return {"files": files, "version": distribution.version}


def _read_regular_nofollow(path: Path) -> bytes:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"identity source is not a regular file: {path}")
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
            _fail(f"identity source changed while read: {path}")
        return bytes(payload)
    finally:
        os.close(descriptor)


_CURRENT_CPYTHON_IDENTITY: tuple[str, int] | None = None


def _current_cpython_identity() -> tuple[str, int]:
    """Hash the running image while proving ``sys.executable`` names it."""

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
        raise OSError("current CPython executable path is not normalized absolute")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    image_fd = os.open("/proc/self/exe", flags)
    try:
        named_fd = os.open(executable, flags)
    except BaseException:
        os.close(image_fd)
        raise
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
            raise OSError("current CPython path does not identify the running image")
        digest = hashlib.sha256()
        remaining = image_before.st_size
        while remaining:
            chunk = os.read(image_fd, min(1 << 20, remaining))
            if not chunk:
                raise OSError("current CPython image ended before its fstat size")
            digest.update(chunk)
            remaining -= len(chunk)
        if os.read(image_fd, 1):
            raise OSError("current CPython image grew during identity read")
        image_after = os.fstat(image_fd)
        if any(
            getattr(image_before, field) != getattr(image_after, field)
            for field in stable_fields
        ):
            raise OSError("current CPython image changed during identity read")
    finally:
        try:
            os.close(named_fd)
        finally:
            os.close(image_fd)
    named_after_fd = os.open(executable, flags)
    try:
        named_after = os.fstat(named_after_fd)
    finally:
        os.close(named_after_fd)
    if any(
        getattr(image_after, field) != getattr(named_after, field)
        for field in stable_fields
    ):
        raise OSError("current CPython executable path changed during identity read")
    _CURRENT_CPYTHON_IDENTITY = (digest.hexdigest(), image_after.st_size)
    return _CURRENT_CPYTHON_IDENTITY


def _sealed(relative: str) -> dict[str, Any]:
    payload = _read_regular_nofollow(REPOSITORY_ROOT / relative)
    return {
        "path": relative,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _artifact_file(path: Path) -> dict[str, Any]:
    payload = _read_regular_nofollow(path)
    return {"path": path.name, "sha256": _sha256(payload), "size_bytes": len(payload)}


def _validate_native_manifests(
    producer_manifest: Any, verifier_manifest: Any
) -> None:
    producer_keys = {
        "artifact_kind",
        "binary_protocols",
        "compile_flags",
        "compiler_id",
        "compiler_version",
        "cpu_model",
        "final_mxcsr",
        "final_mxcsr_denormals_are_zero",
        "final_mxcsr_flush_to_zero",
        "final_rounding_mode",
        "final_rounding_mode_name",
        "gmp_version",
        "initial_mxcsr",
        "initial_mxcsr_denormals_are_zero",
        "initial_mxcsr_flush_to_zero",
        "initial_rounding_mode",
        "initial_rounding_mode_name",
        "mpfr_version",
        "numeric_contract",
        "openssl_version",
        "schema_version",
    }
    verifier_keys = {
        "artifact_kind",
        "compile_flags",
        "compiler_id",
        "compiler_version",
        "gmp_version",
        "input_authority",
        "numpy_repo_imports",
        "openssl_version",
        "parity_surfaces",
        "producer_source_linked",
        "schema_version",
        "solver",
    }
    if (
        not isinstance(producer_manifest, dict)
        or set(producer_manifest) != producer_keys
        or not isinstance(verifier_manifest, dict)
        or set(verifier_manifest) != verifier_keys
    ):
        _fail("native manifest shape mismatch")
    if (
        producer_manifest["artifact_kind"] != "a4_v2_native_build_manifest"
        or verifier_manifest["artifact_kind"]
        != "a4_v2_verifier_source_manifest"
        or producer_manifest["schema_version"] != 1
        or verifier_manifest["schema_version"] != 1
        or producer_manifest["compile_flags"] != EXPECTED_COMPILE_FLAGS_STRING
        or verifier_manifest["compile_flags"] != EXPECTED_COMPILE_FLAGS_STRING
        or producer_manifest["compiler_id"] != EXPECTED_COMPILER_ID
        or verifier_manifest["compiler_id"] != EXPECTED_COMPILER_ID
        or producer_manifest["compiler_version"] != EXPECTED_COMPILER_VERSION
        or verifier_manifest["compiler_version"] != EXPECTED_COMPILER_VERSION
        or producer_manifest["gmp_version"] != EXPECTED_GMP_VERSION
        or verifier_manifest["gmp_version"] != EXPECTED_GMP_VERSION
        or producer_manifest["mpfr_version"] != EXPECTED_MPFR_VERSION
        or producer_manifest["openssl_version"] != EXPECTED_OPENSSL_VERSION
        or verifier_manifest["openssl_version"] != EXPECTED_OPENSSL_VERSION
        or producer_manifest["cpu_model"] != EXPECTED_CPU_MODEL
        or producer_manifest["initial_mxcsr"] != "0x00001f80"
        or producer_manifest["final_mxcsr"] != "0x00001f80"
        or producer_manifest["initial_rounding_mode"] != 0
        or producer_manifest["final_rounding_mode"] != 0
        or producer_manifest["initial_rounding_mode_name"] != "FE_TONEAREST"
        or producer_manifest["final_rounding_mode_name"] != "FE_TONEAREST"
        or producer_manifest["initial_mxcsr_denormals_are_zero"] is not False
        or producer_manifest["final_mxcsr_denormals_are_zero"] is not False
        or producer_manifest["initial_mxcsr_flush_to_zero"] is not False
        or producer_manifest["final_mxcsr_flush_to_zero"] is not False
        or verifier_manifest["numpy_repo_imports"] is not False
        or verifier_manifest["producer_source_linked"] is not False
        or verifier_manifest["parity_surfaces"]
        != ["par-scalar", "par-block", "par-representation"]
        or verifier_manifest["input_authority"]
        != {
            "numpy": "1.23.5",
            "python": "CPython 3.9.25",
            "role": "registered-input-regeneration-only",
        }
    ):
        _fail("native manifest numeric/tool/library contract mismatch")


def _tool_identity(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    if not path.is_absolute() or path.resolve().as_posix() != path_text:
        _fail(f"tool path is not an absolute normalized executable: {path_text}")
    payload = _read_regular_nofollow(path)
    return {
        "path": path_text,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _compile_records(
    payload: bytes,
    expected_sources: Sequence[str],
    description: str,
    expected_manifest_version: str,
) -> list[dict[str, Any]]:
    value = _parse_json(payload, description)
    if not isinstance(value, list) or len(value) != len(expected_sources):
        _fail(f"{description} translation-unit count mismatch")
    mandatory = set(COMPILE_FLAGS)
    forbidden = re.compile(
        r"^(?:-Ofast|-ffast-math|-funsafe-math-optimizations|"
        r"-fassociative-math|-freciprocal-math|-ffinite-math-only|"
        r"-fno-signed-zeros|-fno-trapping-math|-fno-math-errno|"
        r"-fno-rounding-math|-fno-signaling-nans|-fcx-limited-range|"
        r"-fexcess-precision=fast|-fapprox-func|-march(?:=.*)?|"
        r"-mtune=native|-mfma|-ffp-contract=(?:fast|on))$"
    )
    records: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict) or set(raw) not in (
            {"directory", "command", "file"},
            {"directory", "command", "file", "output"},
        ):
            _fail(f"{description}[{index}] has a nonfrozen CMake shape")
        if any(not isinstance(raw[key], str) or not raw[key] for key in raw):
            _fail(f"{description}[{index}] contains an empty string")
        directory = Path(raw["directory"])
        source_path = Path(raw["file"])
        if not source_path.is_absolute():
            source_path = directory / source_path
        try:
            source = source_path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
        except ValueError as error:
            raise ParityFailure(f"{description} source is outside repository") from error
        argv = shlex.split(raw["command"], posix=True)
        if (
            not argv
            or argv[0] != CXX_BINARY
            or not mandatory.issubset(set(argv))
            or any(argv.count(flag) != 1 for flag in COMPILE_FLAGS)
            or any(forbidden.fullmatch(argument) for argument in argv)
            or "-c" not in argv
        ):
            _fail(f"{description} compiler/flag contract mismatch for {source}")
        records.append(
            {
                "argv": argv,
                "argv_sha256": _sha256(_canonical_body(argv)),
                "raw_command": raw["command"],
                "source": source,
            }
        )
    records.sort(key=lambda item: item["source"].encode("utf-8"))
    if [item["source"] for item in records] != list(expected_sources) or len(
        {item["source"] for item in records}
    ) != len(records):
        _fail(f"{description} has extra, missing, duplicate, or reordered TUs")
    compilers = {item["argv"][0] for item in records}
    if compilers != {CXX_BINARY}:
        _fail(f"{description} does not use the frozen compiler executable")
    version = _capture((CXX_BINARY, "--version")).decode(
        "utf-8", errors="strict"
    )
    if (
        not version.splitlines()
        or version.splitlines()[0] != EXPECTED_COMPILER_VERSION_LINE
        or expected_manifest_version != EXPECTED_COMPILER_VERSION
    ):
        _fail(f"{description} compiler version/manifest binding mismatch")
    return records


def _write_new(path: Path, payload: bytes) -> None:
    with path.open("xb", buffering=0) as output:
        offset = 0
        while offset < len(payload):
            written = output.write(payload[offset:])
            if written <= 0:
                _fail(f"short write: {path}")
            offset += written
        os.fsync(output.fileno())


def _read_memfd(descriptor: int, description: str, maximum_bytes: int = 1 << 20) -> bytes:
    size = os.fstat(descriptor).st_size
    if size < 0 or size > maximum_bytes:
        _fail(f"{description} exceeds its bounded capture")
    os.lseek(descriptor, 0, os.SEEK_SET)
    payload = bytearray()
    while len(payload) < size:
        chunk = os.read(descriptor, min(1 << 16, size - len(payload)))
        if not chunk:
            break
        payload.extend(chunk)
    if len(payload) != size:
        _fail(f"short bounded capture for {description}")
    return bytes(payload)


def _capture(arguments: Sequence[str]) -> bytes:
    output_fd = os.memfd_create("a4-v2-par-stdout", getattr(os, "MFD_CLOEXEC", 0))
    error_fd = os.memfd_create("a4-v2-par-stderr", getattr(os, "MFD_CLOEXEC", 0))
    try:
        process = subprocess.Popen(
            list(arguments),
            cwd=REPOSITORY_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=output_fd,
            stderr=error_fd,
            close_fds=True,
        )
        result = _wait_subprocess(process)
        output = _read_memfd(output_fd, "captured command stdout")
        error = _read_memfd(error_fd, "captured command stderr")
    finally:
        os.close(output_fd)
        os.close(error_fd)
    if result.exit_code < 0:
        raise ExternalPhaseSignal(-result.exit_code)
    if result.exit_code != 0:
        _fail(f"command failed {list(arguments)!r}: {error[:4096]!r}")
    return output


def _run_logged(arguments: Sequence[str], stdout_path: Path, stderr_path: Path) -> None:
    with stdout_path.open("xb", buffering=0) as output, stderr_path.open(
        "xb", buffering=0
    ) as error_output:
        process = subprocess.Popen(
            list(arguments),
            cwd=REPOSITORY_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=error_output,
            close_fds=True,
        )
        result = _wait_subprocess(process)
        os.fsync(output.fileno())
        os.fsync(error_output.fileno())
    if result.exit_code < 0:
        raise ExternalPhaseSignal(-result.exit_code)
    if result.exit_code != 0:
        _fail(
            f"build command failed {list(arguments)!r}: "
            f"{stderr_path.read_bytes()[:4096]!r}"
        )


def _run_sealed(
    binary: Path,
    arguments: Sequence[str],
    *,
    stdout_path: Path | None = None,
    stderr_path: Path,
) -> bytes:
    try:
        os.fstat(FIXED_FD)
    except OSError:
        pass
    else:
        _fail("frozen native descriptor 197 is already open")
    descriptor = os.open(binary, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    if descriptor != FIXED_FD:
        os.dup2(descriptor, FIXED_FD, inheritable=True)
        os.close(descriptor)
    else:
        os.set_inheritable(FIXED_FD, True)
    argv = [f"/proc/self/fd/{FIXED_FD}", *arguments]
    capture_fd: int | None = None
    try:
        with stderr_path.open("xb", buffering=0) as error_output:
            if stdout_path is None:
                capture_fd = os.memfd_create(
                    "a4-v2-par-native-stdout", getattr(os, "MFD_CLOEXEC", 0)
                )
                process = subprocess.Popen(
                    argv,
                    cwd=REPOSITORY_ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=capture_fd,
                    stderr=error_output,
                    pass_fds=(FIXED_FD,),
                    close_fds=True,
                )
                result = _wait_subprocess(process)
                payload = _read_memfd(
                    capture_fd, "captured native stdout", maximum_bytes=16 << 20
                )
            else:
                with stdout_path.open("xb", buffering=0) as output:
                    process = subprocess.Popen(
                        argv,
                        cwd=REPOSITORY_ROOT,
                        stdin=subprocess.DEVNULL,
                        stdout=output,
                        stderr=error_output,
                        pass_fds=(FIXED_FD,),
                        close_fds=True,
                    )
                    result = _wait_subprocess(process)
                    os.fsync(output.fileno())
                payload = b""
            os.fsync(error_output.fileno())
    finally:
        if capture_fd is not None:
            os.close(capture_fd)
        os.close(FIXED_FD)
    if result.exit_code < 0:
        raise ExternalPhaseSignal(-result.exit_code)
    if result.exit_code != 0:
        _fail(
            f"native command failed {argv!r}: {stderr_path.read_bytes()[:4096]!r}"
        )
    return payload


def _float32_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _round_ratio_ties_even(numerator: int, denominator: int) -> int:
    """Round one nonnegative exact ratio to an integer under RN-even."""

    if numerator < 0 or denominator <= 0:
        _fail("invalid exact-ratio rounding input")
    quotient, remainder = divmod(numerator, denominator)
    doubled = remainder << 1
    if doubled > denominator or (doubled == denominator and quotient & 1):
        quotient += 1
    return quotient


def _floor_log2_ratio(numerator: int, denominator: int) -> int:
    if numerator <= 0 or denominator <= 0:
        _fail("invalid exact-ratio logarithm input")
    candidate = numerator.bit_length() - denominator.bit_length()
    if candidate >= 0:
        at_least = numerator >= denominator << candidate
    else:
        at_least = numerator << (-candidate) >= denominator
    return candidate if at_least else candidate - 1


def _fraction_to_binary64_bits(value: Fraction) -> int:
    """Convert an exact rational directly to IEEE binary64 RN-ties-to-even.

    PAR fixture construction deliberately returns the serialized bits.  It
    never converts through Python ``float`` and is not the independent block
    replay authority; the verifier separately reconstructs these axis bits
    from the persisted rows before it trains a block fixture.
    """

    fraction_bits = 52
    exponent_bits = 11
    total_bits = 64
    sign_bit = 1 if value < 0 else 0
    magnitude = abs(value)
    if magnitude == 0:
        return 0
    numerator = magnitude.numerator
    denominator = magnitude.denominator
    bias = (1 << (exponent_bits - 1)) - 1
    minimum_normal_exponent = 1 - bias
    maximum_normal_exponent = bias
    minimum_subnormal_exponent = minimum_normal_exponent - fraction_bits
    exponent = _floor_log2_ratio(numerator, denominator)
    if exponent < minimum_normal_exponent:
        rounded = _round_ratio_ties_even(
            numerator << (-minimum_subnormal_exponent), denominator
        )
        if rounded == 0:
            return sign_bit << (total_bits - 1)
        if rounded >= 1 << fraction_bits:
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
        if rounded == 1 << (fraction_bits + 1):
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


def _grid_integer(bits: int) -> int:
    exponent = (bits >> 23) & 0xFF
    fraction = bits & 0x7FFFFF
    if exponent == 0xFF:
        _fail("nonfinite scalar PAR fixture")
    magnitude = fraction if exponent == 0 else (1 << 23) | fraction
    shift = 0 if exponent == 0 else exponent - 1
    value = magnitude << shift
    return -value if bits >> 31 else value


@dataclass(frozen=True)
class ScalarCase:
    case_id: int
    bits: tuple[int, ...]
    weights: tuple[int, ...]
    maximum_cardinality: int


def _scalar_cases(np: Any) -> list[ScalarCase]:
    cases: list[ScalarCase] = []
    universe = (-2, -1, 0, 1, 2)
    for support_size in range(1, 5):
        for support in itertools.combinations(universe, support_size):
            for weights in itertools.product((1, 2, 3), repeat=support_size):
                cases.append(
                    ScalarCase(
                        len(cases),
                        tuple(_float32_bits(float(value)) for value in support),
                        tuple(weights),
                        support_size,
                    )
                )
    if len(cases) != 780:
        _fail("exhaustive scalar inventory changed")
    bit_cases = (
        ((0x80000000, 0x00000000), (1, 1)),
        ((0xBF800000, 0x80000000, 0x00000000, 0x3F800000), (1, 2, 3, 1)),
        ((0x80000001, 0x80000000, 0x00000000, 0x00000001), (1, 1, 1, 1)),
        ((0x80800000, 0x807FFFFF, 0x007FFFFF, 0x00800000), (1, 2, 3, 4)),
        ((0xFF7FFFFF, 0xBF800000, 0x3F800000, 0x7F7FFFFF), (1, 1, 1, 1)),
        ((0xBF800000, 0x00000000, 0x3F800000), (1, 1, 1)),
        ((0x3F800000, 0x3F800001), (1, 1)),
        ((0x3F800001, 0x3F800002), (1, 1)),
    )
    for bits, weights in bit_cases:
        distinct = len({_grid_integer(value) for value in bits})
        cases.append(ScalarCase(len(cases), tuple(bits), tuple(weights), distinct))
    generator = np.random.Generator(np.random.PCG64(SEED))
    for suite_index in range(256):
        size = 1 + suite_index % 12
        values = generator.integers(-8, 9, size=size)
        weights = generator.integers(1, 6, size=size)
        bits = tuple(
            int(value)
            for value in np.asarray(values, dtype=np.float32).view(np.uint32)
        )
        distinct = len({_grid_integer(value) for value in bits})
        cases.append(
            ScalarCase(
                len(cases),
                bits,
                tuple(int(value) for value in weights),
                min(8, distinct),
            )
        )
    if len(cases) != 1044:
        _fail("scalar PAR inventory changed")
    return cases


def _write_scalar_input(path: Path, cases: Sequence[ScalarCase]) -> None:
    payload = bytearray(b"A4SCL001")
    payload.extend(struct.pack("<I", len(cases)))
    for case in cases:
        payload.extend(struct.pack("<III", case.case_id, len(case.bits), case.maximum_cardinality))
        for vector_id, (bits, weight) in enumerate(zip(case.bits, case.weights)):
            payload.extend(struct.pack("<IQQ", bits, weight, vector_id))
    _write_new(path, bytes(payload))


def _validate_scalar_output(payload: bytes, expected_cases: int) -> None:
    lines = payload.decode("utf-8", errors="strict").splitlines()
    if not lines or lines[0] != "A4V2_PAR_SCALAR_V1":
        _fail("scalar PAR magic mismatch")
    cases = [line for line in lines if line.startswith("CASE\t")]
    ended = [line for line in lines if line.startswith("END_CASE\t")]
    if len(cases) != expected_cases or len(ended) != expected_cases:
        _fail("scalar PAR case inventory mismatch")
    if not lines[-1] == f"END\t{expected_cases}":
        _fail("scalar PAR terminal count mismatch")


def _interval_cost(
    support: Sequence[int], weights: Sequence[int], begin: int, end: int
) -> Fraction:
    total_weight = sum(weights[begin:end])
    first = sum(weights[index] * support[index] for index in range(begin, end))
    second = sum(
        weights[index] * support[index] * support[index] for index in range(begin, end)
    )
    return Fraction(total_weight * second - first * first, total_weight)


def _scalar_partition(values: Sequence[int], cardinality: int) -> tuple[tuple[int, int], ...]:
    counts: dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    support = sorted(counts)
    weights = [counts[value] for value in support]
    clusters = min(cardinality, len(support))
    states: dict[tuple[int, int], tuple[Fraction, tuple[int, ...]]] = {}
    for end in range(1, len(support) + 1):
        states[(1, end)] = (_interval_cost(support, weights, 0, end), ())
    for layer in range(2, clusters + 1):
        for end in range(layer, len(support) + 1):
            choices = []
            for predecessor in range(layer - 1, end):
                prior_cost, prior_boundaries = states[(layer - 1, predecessor)]
                choices.append(
                    (
                        prior_cost
                        + _interval_cost(support, weights, predecessor, end),
                        (*prior_boundaries, predecessor),
                    )
                )
            states[(layer, end)] = min(
                choices,
                key=lambda item: (item[0], tuple(reversed(item[1]))),
            )
    boundaries = (0, *states[(clusters, len(support))][1], len(support))
    return tuple(zip(boundaries[:-1], boundaries[1:]))


def _axis_solution(values: Sequence[int], cardinality: int) -> tuple[Fraction, tuple[int, ...]]:
    counts: dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    support = sorted(counts)
    weights = [counts[value] for value in support]
    partition = _scalar_partition(values, cardinality)
    cost = sum(
        (_interval_cost(support, weights, begin, end) for begin, end in partition),
        Fraction(0),
    )
    means = tuple(
        _fraction_to_binary64_bits(
            Fraction(
                sum(weights[index] * support[index] for index in range(begin, end)),
                sum(weights[begin:end]),
            )
        )
        for begin, end in partition
    )
    return cost, means


def _block_axes(rows: Sequence[Sequence[int]], capacity: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    curves = []
    for coordinate in range(2):
        values = [row[coordinate] for row in rows]
        curves.append([None, *(_axis_solution(values, k) for k in range(1, capacity + 1))])
    choices = []
    for first in range(1, capacity + 1):
        for second in range(1, capacity + 1):
            if first * second <= capacity:
                cost = curves[0][first][0] + curves[1][second][0]
                choices.append((cost, -(first * second), first, second))
    _, _, first, second = min(choices)
    return curves[0][first][1], curves[1][second][1]


@dataclass(frozen=True)
class BlockCase:
    case_id: int
    capacity: int
    dataset_id: str
    group_id: int
    rows: tuple[tuple[float, float], ...]
    axis0_bits: tuple[int, ...]
    axis1_bits: tuple[int, ...]
    cells: tuple[int, ...]


def _block_cases(np: Any) -> list[BlockCase]:
    minus_one = struct.unpack("<Q", struct.pack("<d", -1.0))[0]
    plus_one = struct.unpack("<Q", struct.pack("<d", 1.0))[0]
    zero = 0
    helpers = [
        BlockCase(
            1000,
            2,
            "a4_v2_par_block_microfixture",
            0,
            ((-1.0, 0.0), (1.0, 0.0), (0.0, 0.0)),
            (minus_one, plus_one),
            (zero,),
            (0, 1, 2),
        ),
        BlockCase(
            1001,
            2,
            "a4_v2_par_block_microfixture",
            1,
            ((-1.0, 0.0), (1.0, 0.0)),
            (zero,),
            (zero,),
            (0, 1),
        ),
        BlockCase(
            1002,
            3,
            "a4_v2_par_block_microfixture",
            2,
            ((0.0, 0.0), (0.0, 0.0), (1.0, 0.0)),
            (zero,),
            (zero,),
            (0, 1, 2),
        ),
        BlockCase(
            1003,
            2,
            "a4_v2_par_block_microfixture",
            3,
            ((-1.0, 0.0), (1.0, 0.0)),
            (zero,),
            (zero,),
            (0, 1),
        ),
        BlockCase(
            1004,
            2,
            "a4_v2_par_block_microfixture",
            4,
            ((-1.0, 0.0), (1.0, 0.0)),
            (minus_one, plus_one),
            (zero,),
            (0, 1),
        ),
    ]
    generator = np.random.Generator(np.random.PCG64(SEED))
    cases = list(helpers)
    for case_id in range(64):
        row_count = 8 + case_id % 25
        capacity = 2 + case_id % 7
        integers = generator.integers(-8, 9, size=(row_count, 2))
        integer_rows = tuple((int(row[0]), int(row[1])) for row in integers)
        axis0_bits, axis1_bits = _block_axes(integer_rows, capacity)
        cases.append(
            BlockCase(
                case_id,
                capacity,
                f"synthetic_block_case_{case_id}",
                0,
                tuple((float(left), float(right)) for left, right in integer_rows),
                axis0_bits,
                axis1_bits,
                tuple(index % 4 for index in range(row_count)),
            )
        )
    return cases


def _write_block_input(path: Path, cases: Sequence[BlockCase]) -> None:
    payload = bytearray(b"A4BLK001")
    payload.extend(struct.pack("<I", len(cases)))
    for case in cases:
        dataset = case.dataset_id.encode("utf-8")
        payload.extend(
            struct.pack(
                "<IIII", case.case_id, case.capacity, case.group_id, len(dataset)
            )
        )
        payload.extend(dataset)
        payload.extend(
            struct.pack(
                "<III", len(case.rows), len(case.axis0_bits), len(case.axis1_bits)
            )
        )
        for vector_id, ((left, right), cell) in enumerate(zip(case.rows, case.cells)):
            payload.extend(
                struct.pack(
                    "<IIQQ",
                    _float32_bits(left),
                    _float32_bits(right),
                    cell,
                    vector_id,
                )
            )
        for bits in (*case.axis0_bits, *case.axis1_bits):
            payload.extend(struct.pack("<Q", bits))
    _write_new(path, bytes(payload))


def _validate_block_output(payload: bytes, expected_cases: int) -> dict[str, bool]:
    lines = payload.decode("utf-8", errors="strict").splitlines()
    if len(lines) < 3 or lines[0] != "A4S_BLOCK_RESULT_V1" or lines[1] != f"PROTOCOL\t{HASH_DOMAIN}":
        _fail("block PAR header mismatch")
    if not lines[-1].startswith(f"END\t{expected_cases}\t"):
        _fail("block PAR terminal count mismatch")
    by_case: dict[int, list[list[str]]] = {}
    for line in lines[2:-1]:
        fields = line.split("\t")
        if len(fields) >= 2 and fields[1].isdigit():
            by_case.setdefault(int(fields[1]), []).append(fields)
    if set(by_case) != {*range(64), *range(1000, 1005)}:
        _fail("block PAR case-id inventory mismatch")
    case_order = [
        int(fields[1])
        for fields in (line.split("\t") for line in lines[2:-1])
        if len(fields) >= 2 and fields[0] == "CASE" and fields[1].isdigit()
    ]
    if case_order != [*range(1000, 1005), *range(64)]:
        _fail("helper/production block result order changed")
    controls = {
        case_id: next(row for row in records if row[0] == "CASE")[9]
        for case_id, records in by_case.items()
    }
    for helper_id in range(1000, 1005):
        case_row = next(row for row in by_case[helper_id] if row[0] == "CASE")
        row_rows = [row for row in by_case[helper_id] if row[0] == "ROW"]
        if (
            case_row[3] != "a4_v2_par_block_microfixture"
            or case_row[5] != str(helper_id - 1000)
            or any(row[3] != row[2] or row[4] != row[2] for row in row_rows)
        ):
            _fail("helper block metadata identity mismatch")
    for case_id in range(64):
        case_row = next(row for row in by_case[case_id] if row[0] == "CASE")
        if case_row[3] != f"synthetic_block_case_{case_id}" or case_row[5] != "0":
            _fail("production block metadata identity mismatch")
    if any(controls[case_id] != "1" for case_id in range(64)):
        _fail("production block PAR control-valid inventory mismatch")
    assignment_lower = any(
        row[0] == "STEP_ASSIGNMENT_BEFORE"
        and row[4] == "2"
        and row[6] == "0"
        for row in by_case[1000]
    )
    farthest_lower = any(
        row[0] == "START_SELECTED"
        and row[2] == "0"
        and row[3] == "0"
        and row[4] == "0"
        for row in by_case[1001]
    )
    empty_retained = False
    for empty in (row for row in by_case[1002] if row[0] == "STEP_EMPTY"):
        start_id = empty[2]
        iteration = int(empty[3])
        center_id = empty[5]
        after = next(
            (
                row
                for row in by_case[1002]
                if row[0] == "STEP_CENTER"
                and row[2] == start_id
                and row[3] == str(iteration)
                and row[4] == center_id
            ),
            None,
        )
        if iteration == 1:
            before = next(
                (
                    row
                    for row in by_case[1002]
                    if row[0] == "START_CENTER"
                    and row[2] == start_id
                    and row[3] == center_id
                ),
                None,
            )
            prior_bits = None if before is None else (before[4], before[5])
        else:
            before = next(
                (
                    row
                    for row in by_case[1002]
                    if row[0] == "STEP_CENTER"
                    and row[2] == start_id
                    and row[3] == str(iteration - 1)
                    and row[4] == center_id
                ),
                None,
            )
            prior_bits = None if before is None else (before[5], before[6])
        if after is not None and prior_bits == (after[5], after[6]):
            empty_retained = True
            break
    cartesian = next(row for row in by_case[1003] if row[0] == "CARTESIAN")
    start_zero = next(
        row for row in by_case[1003] if row[0] == "START" and row[2] == "0"
    )
    cartesian_before_fill = cartesian[2] == "1" and start_zero[5] == "2"
    starts = [row for row in by_case[1004] if row[0] == "START"]
    best = next(row for row in by_case[1004] if row[0] == "BEST")
    lower_start = (
        len(starts) == 8
        and {int(row[2]) for row in starts} == set(range(8))
        and len({row[11] for row in starts}) == 1
        and len(best) >= 4
        and best[2] == "1"
        and best[3] == "0"
    )
    checks = {
        "cartesian_start_zero_before_fill": cartesian_before_fill,
        "empty_center_retention": empty_retained,
        "equidistant_lower_codeword": assignment_lower,
        "farthest_fallback_lower_vector_id": farthest_lower,
        "best_of_eight_tie_lower_start": lower_start,
    }
    return checks


def _validate_smoke(payload: bytes) -> dict[str, bool]:
    lines = payload.decode("utf-8", errors="strict").splitlines()
    records = [line.split("\t") for line in lines]
    tags = [record[0] for record in records]
    expected_counts = {
        "A4S_NATIVE_SMOKE_V1": 1,
        "ROUNDTRIP": 10,
        "MIDPOINT": 4,
        "RATIONAL": 2,
        "SCALAR_K_GT_H": 1,
        "BLOCK_ASSIGNMENT_TIE": 1,
        "BLOCK_FARTHEST_FALLBACK": 1,
        "BLOCK_VALID_EIGHT_STARTS": 1,
        "BLOCK_NONFINITE_CONTROL": 1,
        "END": 1,
    }
    if len(lines) != 23 or any(tags.count(tag) != count for tag, count in expected_counts.items()):
        _fail("native-smoke inventory mismatch")
    if records[0] != ["A4S_NATIVE_SMOKE_V1"] or records[-1] != ["END"]:
        _fail("native-smoke terminal framing mismatch")
    roundtrips = [record for record in records if record[0] == "ROUNDTRIP"]
    expected_patterns = (
        0x00000000,
        0x80000000,
        0x00000001,
        0x007FFFFF,
        0x00800000,
        0x3F800000,
        0x3F800001,
        0x7F7FFFFF,
        0x80000001,
        0xBF800000,
    )
    for record, bits in zip(roundtrips, expected_patterns):
        canonical = 0 if bits & 0x7FFFFFFF == 0 else bits
        exact = Fraction(_grid_integer(bits), 1 << 149)
        expected = [
            "ROUNDTRIP",
            f"0x{bits:08x}",
            str(_grid_integer(bits)),
            f"0x{canonical:08x}",
            f"0x{_fraction_to_binary64_bits(exact):016x}",
        ]
        if record != expected:
            _fail("native-smoke ROUNDTRIP semantic mismatch")
    expected_exact = (
        ("MIDPOINT", Fraction(1, 2), -149, 0x00000000),
        ("MIDPOINT", Fraction(3, 2), -149, 0x00000002),
        ("MIDPOINT", Fraction(-1, 2), -149, 0x80000000),
        ("MIDPOINT", Fraction(-3, 2), -149, 0x80000002),
        ("RATIONAL", Fraction(1, 3), 0, 0x3EAAAAAB),
        ("RATIONAL", Fraction(-1, 3), 0, 0xBEAAAAAB),
    )
    exact_records = [
        record for record in records if record[0] in {"MIDPOINT", "RATIONAL"}
    ]
    for record, (tag, fraction, exponent, expected32) in zip(
        exact_records, expected_exact
    ):
        value = fraction * Fraction(2) ** exponent
        expected64 = _fraction_to_binary64_bits(value)
        if (
            len(record) != 6
            or record[0] != tag
            or record[1] != str(fraction.numerator)
            or record[2] != str(fraction.denominator)
            or record[3] != str(exponent)
            or record[5] != f"0x{expected64:016x}"
            or record[4] != f"0x{expected32:08x}"
        ):
            _fail("native-smoke exact-rounding semantic mismatch")
    singleton = {record[0]: record for record in records if record[0].startswith(("SCALAR_", "BLOCK_"))}
    if (
        singleton.get("SCALAR_K_GT_H") != ["SCALAR_K_GT_H", "4", "2", "2", "3"]
        or singleton.get("BLOCK_ASSIGNMENT_TIE")
        != ["BLOCK_ASSIGNMENT_TIE", "0", "0x3ff0000000000000", "2", "1"]
        or singleton.get("BLOCK_FARTHEST_FALLBACK")
        != ["BLOCK_FARTHEST_FALLBACK", "3", "7", "1"]
        or singleton.get("BLOCK_VALID_EIGHT_STARTS", [None, None])[1] != "8"
        or singleton.get("BLOCK_NONFINITE_CONTROL")
        != ["BLOCK_NONFINITE_CONTROL", "8", "0"]
    ):
        _fail("native-smoke scalar/block semantic mismatch")
    best_start = singleton["BLOCK_VALID_EIGHT_STARTS"]
    if len(best_start) != 3 or not best_start[2].isdigit() or int(best_start[2]) >= 8:
        _fail("native-smoke best-start semantic mismatch")
    return {
        "assignment_tie_lower_codeword": True,
        "farthest_tie_lower_identity": True,
        "nonfinite_control_rejected": True,
        "scalar_k_gt_h_effective_cardinality": True,
        "valid_eight_start_inventory": True,
    }


def _validate_representation(payload: bytes) -> Mapping[str, Any]:
    value = _parse_json(payload, "representation PAR output", canonical=True)
    expected_keys = {
        "allocation_record_count",
        "allocation_sha256",
        "all_decisions_equal",
        "authority_hashes_equal",
        "candidate_counts",
        "checks",
        "decision_equality_count",
        "exact_objective_class_count",
        "first_mismatch",
        "global_lookup_case",
        "global_packing_cases",
        "independent_exhaustive_sha256",
        "matched_lookup_cases",
        "matched_packing_cases",
        "mixed_radix_case",
        "optimized_sha256",
        "python_order_fingerprint_authoritative",
        "python_order_fingerprint_sha256",
        "same_h_different_weight_fixture",
        "support_size_winners",
        "tiny_curve_inventory_preimage_schema",
        "tiny_curve_inventory_sha256",
    }
    if _canonical_document(value) != payload:
        _fail("representation parity JSON is not canonical")
    if (
        set(value) != expected_keys
        or value.get("allocation_record_count") != 2_433_600
        or value.get("decision_equality_count") != 2_433_600
        or value.get("all_decisions_equal") is not True
        or value.get("authority_hashes_equal") is not True
        or value.get("first_mismatch") is not None
        or not isinstance(value.get("checks"), dict)
        or not all(value["checks"].values())
    ):
        _fail("representation parity authority/count mismatch")
    return value


@dataclass(frozen=True)
class PhaseBoundary:
    cpu_microseconds: int
    wall_nanoseconds: int
    peak_rss_bytes: int
    utc: str


_WORKER_MESSAGE_LIMIT = 8192


def _write_worker_message(descriptor: int, value: Mapping[str, Any]) -> None:
    payload = _canonical_document(dict(value))
    if len(payload) > _WORKER_MESSAGE_LIMIT:
        payload = _canonical_document(
            {
                "detail": "phase-worker diagnostic exceeded its fixed bound",
                "direct_child_peak_rss_bytes": _CURRENT_DIRECT_CHILD_PEAK_RSS,
                "signal_number": None,
                "state": "FAILURE",
            }
        )
    framed = struct.pack(">I", len(payload)) + payload
    offset = 0
    while offset < len(framed):
        written = os.write(descriptor, framed[offset:])
        if written <= 0:
            os._exit(4)
        offset += written


def _read_exact_pipe(descriptor: int, size: int) -> bytes | None:
    payload = bytearray()
    while len(payload) < size:
        chunk = os.read(descriptor, size - len(payload))
        if not chunk:
            return None
        payload.extend(chunk)
    return bytes(payload)


def _launch_phase_worker(task: Callable[[], None]) -> _WorkerHandle:
    result_read, result_write = os.pipe()
    release_read, release_write = os.pipe()
    # Freeze H after all pre-fork supervisor setup and immediately before the
    # fork whose worker must naturally dominate that inherited history.
    supervisor_start_hwm = _self_peak_rss_bytes()
    try:
        pid = os.fork()
    except BaseException:
        os.close(result_read)
        os.close(result_write)
        os.close(release_read)
        os.close(release_write)
        raise
    if pid == 0:
        global _CURRENT_DIRECT_CHILD_PEAK_RSS

        os.close(result_read)
        os.close(release_write)
        _CURRENT_DIRECT_CHILD_PEAK_RSS = 0
        state = "READY"
        detail = ""
        signal_number: int | None = None
        try:
            task()
        except ExternalPhaseSignal as error:
            state = "EXTERNAL_SIGNAL"
            detail = str(error)
            signal_number = error.signal_number
        except BaseException as error:
            state = "FAILURE"
            detail = str(error)[:4096]
        try:
            _write_worker_message(
                result_write,
                {
                    "detail": detail,
                    "direct_child_peak_rss_bytes": _CURRENT_DIRECT_CHILD_PEAK_RSS,
                    "signal_number": signal_number,
                    "state": state,
                },
            )
            os.close(result_write)
            if state == "READY":
                token = os.read(release_read, 2)
                if token != b"R":
                    os._exit(4)
            os.close(release_read)
        except BaseException:
            os._exit(4)
        os._exit(0 if state == "READY" else 2)
    os.close(result_write)
    os.close(release_read)
    return _WorkerHandle(
        pid=pid,
        result_fd=result_read,
        release_fd=release_write,
        supervisor_start_hwm=supervisor_start_hwm,
    )


def _receive_worker_message(handle: _WorkerHandle) -> dict[str, Any] | None:
    try:
        prefix = _read_exact_pipe(handle.result_fd, 4)
        if prefix is None:
            return None
        size = struct.unpack(">I", prefix)[0]
        if size <= 0 or size > _WORKER_MESSAGE_LIMIT:
            _fail("phase-worker message length is invalid")
        payload = _read_exact_pipe(handle.result_fd, size)
        if payload is None:
            _fail("phase-worker message is truncated")
        value = _parse_json(payload, "phase-worker message", canonical=True)
        if not isinstance(value, dict) or set(value) != {
            "detail",
            "direct_child_peak_rss_bytes",
            "signal_number",
            "state",
        }:
            _fail("phase-worker message shape mismatch")
        if (
            value["state"] not in {"READY", "EXTERNAL_SIGNAL", "FAILURE"}
            or not isinstance(value["detail"], str)
            or not isinstance(value["direct_child_peak_rss_bytes"], int)
            or isinstance(value["direct_child_peak_rss_bytes"], bool)
            or value["direct_child_peak_rss_bytes"] < 0
            or (
                value["signal_number"] is not None
                and (
                    not isinstance(value["signal_number"], int)
                    or isinstance(value["signal_number"], bool)
                    or not 1 <= value["signal_number"] <= 64
                )
            )
            or (value["state"] == "EXTERNAL_SIGNAL")
            != (value["signal_number"] is not None)
        ):
            _fail("phase-worker message value mismatch")
        return value
    finally:
        os.close(handle.result_fd)


def _release_and_reap_worker(handle: _WorkerHandle, *, release: bool) -> _WaitResult:
    try:
        if release:
            try:
                os.write(handle.release_fd, b"R")
            except BrokenPipeError:
                pass
    finally:
        os.close(handle.release_fd)
    return _wait4_integer(handle.pid)


def _run_fresh_phase_worker(
    task: Callable[[], None], ready_action: Callable[[], None]
) -> int:
    """Run one attempt and prove its RSS is not inherited supervisor history."""

    handle = _launch_phase_worker(task)
    supervisor_start_hwm = handle.supervisor_start_hwm
    message: dict[str, Any] | None
    try:
        message = _receive_worker_message(handle)
    except BaseException:
        _release_and_reap_worker(handle, release=False)
        raise
    ready = message is not None and message.get("state") == "READY"
    if ready:
        try:
            ready_action()
        except BaseException:
            _release_and_reap_worker(handle, release=True)
            raise
    usage = _release_and_reap_worker(handle, release=ready)
    direct_peak = (
        int(message["direct_child_peak_rss_bytes"]) if message is not None else 0
    )
    family_peak = max(usage.peak_rss_bytes, direct_peak)
    if family_peak < supervisor_start_hwm:
        _fail(
            "fresh phase worker did not naturally dominate inherited supervisor HWM; "
            "RSS is not phase-identifiable"
        )
    if usage.exit_code < 0:
        raise ExternalPhaseSignal(
            -usage.exit_code,
            phase_peak_rss_bytes=family_peak,
            retry_safe=not ready,
        )
    if message is None:
        _fail("phase worker exited without its bounded status message")
    if message["state"] == "EXTERNAL_SIGNAL":
        raise ExternalPhaseSignal(
            int(message["signal_number"]),
            phase_peak_rss_bytes=family_peak,
            retry_safe=True,
        )
    if message["state"] != "READY" or usage.exit_code != 0:
        _fail(f"phase worker failed: {message['detail']}")
    return family_peak


def _capture_boundary(snapshot: Any, phase_child_peak_rss_bytes: int = 0) -> PhaseBoundary:
    observed = snapshot()
    return PhaseBoundary(
        cpu_microseconds=observed.cpu_microseconds,
        wall_nanoseconds=observed.wall_nanoseconds,
        # RUSAGE_CHILDREN.ru_maxrss is cumulative and cannot identify a B/P
        # attempt.  Only the current fresh worker/direct-child wait4 peak is
        # combined with the long-lived supervisor's SELF HWM.
        peak_rss_bytes=max(
            _self_peak_rss_bytes(), phase_child_peak_rss_bytes
        ),
        utc=_utc_now(),
    )


def _receipt_template(
    *,
    phase: str,
    attempt_id: int,
    start: PhaseBoundary,
    logical_run_id: str,
    implementation_commit: str,
    environment_sha256: str,
    binary_sha256: str,
    argv_sha256: str,
    exit_reason: str,
    staging_disposition: str,
) -> dict[str, Any]:
    return {
        "argv_sha256": argv_sha256,
        "attempt_id": attempt_id,
        "binary_sha256": binary_sha256,
        "completed_unit_index": -1,
        "cpu_microseconds": 0,
        "end_utc": start.utc,
        "environment_sha256": environment_sha256,
        "execution_commit": implementation_commit,
        "exit_reason": exit_reason,
        "logical_run_id": logical_run_id,
        "peak_rss_bytes": start.peak_rss_bytes,
        "phase": phase,
        "staging_disposition": staging_disposition,
        "start_utc": start.utc,
        "wall_nanoseconds": 0,
    }


def _inject_receipt_end(
    receipt: dict[str, Any], start: PhaseBoundary, end: PhaseBoundary
) -> None:
    receipt["cpu_microseconds"] = end.cpu_microseconds - start.cpu_microseconds
    receipt["wall_nanoseconds"] = end.wall_nanoseconds - start.wall_nanoseconds
    receipt["peak_rss_bytes"] = end.peak_rss_bytes
    receipt["end_utc"] = end.utc


def _tree_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for parent, directories, files in os.walk(path, followlinks=False):
        for name in directories:
            candidate = Path(parent) / name
            if candidate.is_symlink():
                _fail(f"symlink in owned PAR tree: {candidate}")
        for name in files:
            candidate = Path(parent) / name
            if candidate.is_symlink() or not candidate.is_file():
                _fail(f"nonregular member in owned PAR tree: {candidate}")
            total += candidate.stat().st_size
    return total


def _regular_members(directory: Path) -> tuple[str, ...]:
    names: list[str] = []
    with os.scandir(directory) as entries:
        for entry in entries:
            if (
                entry.name in {"", ".", ".."}
                or "/" in entry.name
                or entry.is_symlink()
                or not entry.is_file(follow_symlinks=False)
            ):
                _fail(f"nonregular or nested PAR staging member: {entry.name}")
            names.append(entry.name)
    names.sort(key=lambda value: value.encode("utf-8"))
    if len(names) != len(set(names)):
        _fail("duplicate PAR staging member")
    return tuple(names)


def _fsync_regular_nofollow(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        mode = os.fstat(descriptor).st_mode
        if not stat.S_ISREG(mode):
            _fail(f"PAR member is not regular: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _discard_attempt(path: Path) -> int:
    deleted = _tree_bytes(path)
    if path.exists():
        shutil.rmtree(path)
    return deleted


def _post_par_report_unchecked(
    *,
    p_receipt: dict[str, Any],
    p_start: PhaseBoundary,
    p_end: PhaseBoundary,
    receipts: list[dict[str, Any]],
    phase_byte_ledger: list[dict[str, Any]],
    seal_fixed: Mapping[str, Any],
    staging_fd: int,
    parent_fd: int,
    staging_name: str,
    published_name: str,
) -> NoReturn:
    """Execute only the finite, unmetered PAR_report closure."""

    _inject_receipt_end(p_receipt, p_start, p_end)
    receipts.append(p_receipt)
    cap_failed = (
        p_receipt["cpu_microseconds"] < 0
        or p_receipt["wall_nanoseconds"] < 0
        or any(
            item["cpu_microseconds"] > PER_PHASE_CPU_LIMIT
            or item["wall_nanoseconds"] > PER_PHASE_WALL_LIMIT
            or item["peak_rss_bytes"] > RSS_LIMIT
            for item in receipts
        )
        or any(
            sum(
                item["cpu_microseconds"]
                for item in receipts
                if item["phase"] == phase
            )
            > PER_PHASE_CPU_LIMIT
            or sum(
                item["wall_nanoseconds"]
                for item in receipts
                if item["phase"] == phase
            )
            > PER_PHASE_WALL_LIMIT
            for phase in ("B_build", "P_parity")
        )
        or sum(item["cpu_microseconds"] for item in receipts) > STUDY_CPU_LIMIT
        or max(
            item["maximum_live_owned_temporary_bytes"]
            for item in phase_byte_ledger
        )
        > TEMPORARY_LIMIT
        or sum(
            item["research_evidence_archive_bytes"]
            for item in phase_byte_ledger
        )
        > EVIDENCE_LIMIT
    )
    if cap_failed:
        os._exit(3)
    seal = dict(seal_fixed)
    seal["phase_receipts"] = receipts
    seal_payload = _canonical_document(seal)
    if len(seal_payload) > PAR_SEAL_EXACT_LIMIT or len(seal_payload) > PAR_SEAL_COARSE_LIMIT:
        os._exit(3)
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        seal_fd = os.open("par_seal.json", flags, 0o600, dir_fd=staging_fd)
        offset = 0
        while offset < len(seal_payload):
            written = os.write(seal_fd, seal_payload[offset:])
            if written <= 0:
                os._exit(3)
            offset += written
        os.fsync(seal_fd)
        os.close(seal_fd)
        os.fsync(staging_fd)
        if _RENAMEAT2(
            parent_fd,
            staging_name.encode("utf-8"),
            parent_fd,
            published_name.encode("utf-8"),
            _RENAME_NOREPLACE,
        ) != 0:
            os._exit(3)
        os.fsync(parent_fd)
        os.close(staging_fd)
        os.close(parent_fd)
    except BaseException:
        os._exit(3)
    os._exit(0)


def _post_par_report(
    *,
    p_receipt: dict[str, Any],
    p_start: PhaseBoundary,
    p_end: PhaseBoundary,
    receipts: list[dict[str, Any]],
    phase_byte_ledger: list[dict[str, Any]],
    seal_fixed: Mapping[str, Any],
    staging_fd: int,
    parent_fd: int,
    staging_name: str,
    published_name: str,
) -> NoReturn:
    """Keep every post-P failure on the same direct, silent exit path."""

    try:
        _post_par_report_unchecked(
            p_receipt=p_receipt,
            p_start=p_start,
            p_end=p_end,
            receipts=receipts,
            phase_byte_ledger=phase_byte_ledger,
            seal_fixed=seal_fixed,
            staging_fd=staging_fd,
            parent_fd=parent_fd,
            staging_name=staging_name,
            published_name=published_name,
        )
    except BaseException:
        os._exit(3)
    os._exit(3)


def _move_attempt_files(
    attempt: Path, staging: Path, expected_names: Sequence[str] | None = None
) -> tuple[str, ...]:
    names = _regular_members(attempt)
    if expected_names is not None and names != tuple(
        sorted(expected_names, key=lambda value: value.encode("utf-8"))
    ):
        _fail("metered attempt artifact membership mismatch")
    for name in names:
        destination = staging / name
        if destination.exists():
            _fail(f"attempt artifact would replace an existing member: {name}")
        os.rename(attempt / name, destination)
    attempt.rmdir()
    _fsync_directory(staging)
    return names


def _run_build_attempt(
    *,
    attempt: Path,
    root: Path,
    implementation_commit: str,
    logical_run_preimage: Mapping[str, Any],
    environment_preimage: Mapping[str, Any],
    prelaunch_observation: Mapping[str, Any],
) -> None:
    for index, command in enumerate(BUILD_COMMANDS):
        _run_logged(
            command,
            attempt / f"build_command_{index:02d}.stdout",
            attempt / f"build_command_{index:02d}.stderr",
        )
    producer_manifest_path = attempt / "build_producer_native_manifest.json"
    verifier_manifest_path = attempt / "build_verifier_native_manifest.json"
    _run_sealed(
        PRODUCER_BINARY,
        ("manifest",),
        stdout_path=producer_manifest_path,
        stderr_path=attempt / "build_producer_manifest.stderr",
    )
    _run_sealed(
        VERIFIER_BINARY,
        ("manifest",),
        stdout_path=verifier_manifest_path,
        stderr_path=attempt / "build_verifier_manifest.stderr",
    )
    producer_manifest_output = producer_manifest_path.read_bytes()
    verifier_manifest_output = verifier_manifest_path.read_bytes()
    producer_manifest = _parse_json(
        producer_manifest_output, "producer native manifest", canonical=True
    )
    verifier_manifest = _parse_json(
        verifier_manifest_output, "verifier native manifest", canonical=True
    )
    _validate_native_manifests(producer_manifest, verifier_manifest)
    producer_compile_payload = (
        REPOSITORY_ROOT / "build/a4_v2/compile_commands.json"
    ).read_bytes()
    verifier_compile_payload = (
        REPOSITORY_ROOT / "build/a4_v2_verifier/compile_commands.json"
    ).read_bytes()
    producer_compile_records = _compile_records(
        producer_compile_payload,
        PRODUCER_CMAKE_SOURCES,
        "producer compile_commands",
        producer_manifest["compiler_version"],
    )
    verifier_compile_records = _compile_records(
        verifier_compile_payload,
        VERIFIER_CMAKE_SOURCES,
        "verifier compile_commands",
        verifier_manifest["compiler_version"],
    )
    _write_new(attempt / "producer_compile_commands.json", producer_compile_payload)
    _write_new(attempt / "verifier_compile_commands.json", verifier_compile_payload)
    build_manifest = {
        "artifact_kind": "a4_v2_build_manifest",
        "build_commands": [list(command) for command in BUILD_COMMANDS],
        "environment_preimage": dict(environment_preimage),
        "environment_sha256": _sha256(_canonical_body(environment_preimage)),
        "implementation_commit": implementation_commit,
        "libraries": {
            "gmp": producer_manifest["gmp_version"],
            "mpfr": producer_manifest["mpfr_version"],
            "openssl": producer_manifest["openssl_version"],
        },
        "logical_run_id": _sha256(_canonical_body(logical_run_preimage)),
        "logical_run_preimage": dict(logical_run_preimage),
        "prelaunch_observation": dict(prelaunch_observation),
        "producer": {
            "binary": _sealed("build/a4_v2/a4_v2_native"),
            "cmake_lists": _sealed("research/a4_v2/CMakeLists.txt"),
            "cmake_source_files": list(PRODUCER_CMAKE_SOURCES),
            "compile_commands": _sealed_identity_for_artifact(
                root, attempt, "producer_compile_commands.json"
            ),
            "manifest_argv": ["build/a4_v2/a4_v2_native", "manifest"],
            "manifest_argv_sha256": _sha256(
                _canonical_body(["build/a4_v2/a4_v2_native", "manifest"])
            ),
            "manifest_output_sha256": _sha256(producer_manifest_output),
            "translation_units": producer_compile_records,
        },
        "protocol": _sealed(
            "docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json"
        ),
        "schema": _sealed("docs/saq_a4_v2_artifact_schema_2026_07_14.json"),
        "schema_version": 1,
        "source_manifest": _sealed(
            "docs/saq_a4_v2_implementation_manifest_2026_07_14.json"
        ),
        "toolchain": {
            "cmake": _tool_identity(CMAKE_BINARY),
            "cmake_version": _capture((CMAKE_BINARY, "--version"))
            .decode("utf-8", errors="strict")
            .splitlines()[0],
            "compile_flags": list(COMPILE_FLAGS),
            "compiler": _tool_identity(CXX_BINARY),
            "compiler_id": producer_manifest["compiler_id"],
            "compiler_version": producer_manifest["compiler_version"],
            "ninja": _tool_identity(NINJA_BINARY),
            "ninja_version": _capture((NINJA_BINARY, "--version"))
            .decode("utf-8", errors="strict")
            .strip(),
        },
        "verifier": {
            "binary": _sealed("build/a4_v2_verifier/a4_v2_native"),
            "cmake_lists": _sealed("research/a4_v2_verifier/CMakeLists.txt"),
            "cmake_source_files": list(VERIFIER_CMAKE_SOURCES),
            "compile_commands": _sealed_identity_for_artifact(
                root, attempt, "verifier_compile_commands.json"
            ),
            "manifest_argv": ["build/a4_v2_verifier/a4_v2_native", "manifest"],
            "manifest_argv_sha256": _sha256(
                _canonical_body(["build/a4_v2_verifier/a4_v2_native", "manifest"])
            ),
            "manifest_output_sha256": _sha256(verifier_manifest_output),
            "runtime_argv": ["/proc/self/fd/197", "verify-canonical-request"],
            "runtime_argv_sha256": _sha256(
                _canonical_body(["/proc/self/fd/197", "verify-canonical-request"])
            ),
            "translation_units": verifier_compile_records,
        },
    }
    if (
        build_manifest["toolchain"]["cmake_version"] != EXPECTED_CMAKE_VERSION
        or build_manifest["toolchain"]["ninja_version"] != EXPECTED_NINJA_VERSION
    ):
        _fail("frozen CMake/Ninja version mismatch")
    _write_new(attempt / "build_manifest.json", _canonical_document(build_manifest))


def _run_parity_attempt(
    attempt: Path, numpy_authority: Mapping[str, Any]
) -> None:
    import numpy as np  # type: ignore[import-not-found]  # future PAR only

    observed_numpy = _numpy_distribution_authority()
    admitted_paths = {item["path"] for item in observed_numpy["files"]}
    loaded_paths = {
        Path(np.__file__).resolve().as_posix(),
        Path(np.random.__file__).resolve().as_posix(),
        Path(np.random._pcg64.__file__).resolve().as_posix(),
    }
    if (
        observed_numpy != dict(numpy_authority)
        or np.__version__ != "1.23.5"
        or np.random.PCG64.__module__ != "numpy.random._pcg64"
        or not loaded_paths.issubset(admitted_paths)
    ):
        _fail("PAR RNG NumPy import differs from the registered distribution")

    smoke_path = attempt / "producer_native_smoke.tsv"
    _run_sealed(
        PRODUCER_BINARY,
        ("native-smoke", str(smoke_path)),
        stdout_path=attempt / "producer_native_smoke.stdout",
        stderr_path=attempt / "producer_native_smoke.stderr",
    )
    smoke_payload = smoke_path.read_bytes()
    smoke_semantics = _validate_smoke(smoke_payload)

    scalar_cases = _scalar_cases(np)
    scalar_input = attempt / "scalar_input.bin"
    scalar_producer = attempt / "scalar_optimized.tsv"
    scalar_verifier = attempt / "scalar_independent.tsv"
    _write_scalar_input(scalar_input, scalar_cases)
    _run_sealed(
        PRODUCER_BINARY,
        ("par-scalar", str(scalar_input), str(scalar_producer)),
        stdout_path=attempt / "scalar_optimized.stdout",
        stderr_path=attempt / "scalar_optimized.stderr",
    )
    _run_sealed(
        VERIFIER_BINARY,
        ("par-scalar", str(scalar_input), str(scalar_verifier)),
        stdout_path=attempt / "scalar_independent.stdout",
        stderr_path=attempt / "scalar_independent.stderr",
    )
    scalar_payload = scalar_producer.read_bytes()
    scalar_independent_payload = scalar_verifier.read_bytes()
    if scalar_payload != scalar_independent_payload:
        _fail("producer/verifier scalar PAR bytes differ")
    _validate_scalar_output(scalar_payload, len(scalar_cases))

    block_cases = _block_cases(np)
    if [item.case_id for item in block_cases[:5]] != list(range(1000, 1005)) or [
        item.case_id for item in block_cases[5:]
    ] != list(range(64)):
        _fail("helper/production block execution order changed")
    block_input = attempt / "block_input.bin"
    block_producer = attempt / "block_optimized_run1.tsv"
    block_producer_second = attempt / "block_optimized_run2.tsv"
    block_verifier = attempt / "block_independent.tsv"
    _write_block_input(block_input, block_cases)
    _run_sealed(
        PRODUCER_BINARY,
        ("par-block", str(block_input), str(block_producer)),
        stdout_path=attempt / "block_optimized_run1.stdout",
        stderr_path=attempt / "block_optimized_run1.stderr",
    )
    _run_sealed(
        PRODUCER_BINARY,
        ("par-block", str(block_input), str(block_producer_second)),
        stdout_path=attempt / "block_optimized_run2.stdout",
        stderr_path=attempt / "block_optimized_run2.stderr",
    )
    _run_sealed(
        VERIFIER_BINARY,
        ("par-block", str(block_input), str(block_verifier)),
        stdout_path=attempt / "block_independent.stdout",
        stderr_path=attempt / "block_independent.stderr",
    )
    block_payload = block_producer.read_bytes()
    block_second_payload = block_producer_second.read_bytes()
    block_independent_payload = block_verifier.read_bytes()
    if block_payload != block_second_payload or block_payload != block_independent_payload:
        _fail("repeated producer or independent block PAR bytes differ")
    block_checks = _validate_block_output(block_payload, len(block_cases))
    if not all(block_checks.values()):
        _fail(f"five helper-level semantic fixtures failed: {block_checks}")

    representation_producer = attempt / "representation_optimized.json"
    representation_verifier = attempt / "representation_independent.json"
    _run_sealed(
        PRODUCER_BINARY,
        ("representation-suite",),
        stdout_path=representation_producer,
        stderr_path=attempt / "representation_optimized.stderr",
    )
    _run_sealed(
        VERIFIER_BINARY,
        ("par-representation", str(representation_verifier)),
        stdout_path=attempt / "representation_independent.stdout",
        stderr_path=attempt / "representation_independent.stderr",
    )
    representation_payload = representation_producer.read_bytes()
    representation_independent_payload = representation_verifier.read_bytes()
    if representation_payload != representation_independent_payload:
        _fail("producer/verifier representation PAR bytes differ")
    representation = _validate_representation(representation_payload)

    parity_summary = {
        "artifact_kind": "a4_v2_parity_summary",
        "block": {
            "helper_case_count": 5,
            "helper_cases_precede_production": True,
            "helper_semantics": block_checks,
            "independent_output_sha256": _sha256(block_independent_payload),
            "input_sha256": _sha256(block_input.read_bytes()),
            "input_size_bytes": block_input.stat().st_size,
            "optimized_output_size_bytes": len(block_payload),
            "optimized_repeated_run_byte_equal": True,
            "optimized_run1_sha256": _sha256(block_payload),
            "optimized_run2_sha256": _sha256(block_second_payload),
            "producer_verifier_byte_equal": True,
            "production_case_count": 64,
            "production_exact_axis_validation": True,
        },
        "native_smoke": {
            "output_sha256": _sha256(smoke_payload),
            "output_size_bytes": len(smoke_payload),
            "semantic_checks": smoke_semantics,
        },
        "outcome": "PASS_PARITY",
        "parity_inventory": PARITY_INVENTORY,
        "representation": {
            "allocation_decision_count": representation["allocation_record_count"],
            "independent_output_sha256": _sha256(representation_independent_payload),
            "optimized_output_sha256": _sha256(representation_payload),
            "output_size_bytes": len(representation_payload),
            "producer_verifier_byte_equal": True,
        },
        "scalar": {
            "bit_pattern_case_count": 8,
            "exhaustive_case_count": 780,
            "independent_output_sha256": _sha256(scalar_independent_payload),
            "input_sha256": _sha256(scalar_input.read_bytes()),
            "input_size_bytes": scalar_input.stat().st_size,
            "optimized_output_sha256": _sha256(scalar_payload),
            "output_size_bytes": len(scalar_payload),
            "pcg64_case_count": 256,
            "producer_verifier_byte_equal": True,
        },
        "schema_version": 1,
    }
    _write_new(attempt / "parity_summary.json", _canonical_document(parity_summary))


def run_par(
    start_cpu_microseconds: int,
    start_wall_nanoseconds: int,
    artifact_root_argument: str,
    snapshot: Any,
    process_inventory: Any,
    prelaunch_observer: Any,
) -> int:
    """Run the future B/P event and terminate through finite PAR_report."""

    global _CURRENT_DIRECT_CHILD_PEAK_RSS

    if Path.cwd().resolve() != REPOSITORY_ROOT:
        _fail("PAR must start at repository root")
    if list(sys.argv) != EXPECTED_PAR_ARGV:
        _fail("PAR argv differs from the frozen command")
    if {
        name: os.environ.get(name, "") for name in EXPECTED_THREAD_ENVIRONMENT
    } != EXPECTED_THREAD_ENVIRONMENT:
        _fail("PAR thread environment differs from the frozen identity")
    root = Path(artifact_root_argument)
    root = (REPOSITORY_ROOT / root).resolve() if not root.is_absolute() else root.resolve()
    if root.exists() or not root.parent.is_dir() or root != EXPECTED_ARTIFACT_ROOT:
        _fail("PAR artifact root is not the frozen absent docs path")
    try:
        root.relative_to(REPOSITORY_ROOT)
    except ValueError as error:
        raise ParityFailure("PAR artifact root must be inside the repository") from error
    implementation_commit = _capture(("git", "rev-parse", "HEAD")).decode().strip()
    if re.fullmatch(r"[0-9a-f]{40}", implementation_commit) is None:
        _fail("implementation commit is not a full Git OID")
    if _capture(("git", "status", "--porcelain", "--untracked-files=all")):
        _fail("PAR requires a clean implementation commit")
    staging = root.with_name(root.name + ".staging")
    if staging.exists():
        _fail("PAR staging path already exists")
    staging.mkdir(mode=0o700)
    for directory in (PRODUCER_BINARY.parent, VERIFIER_BINARY.parent):
        if directory.exists():
            _fail(f"clean PAR build directory already exists: {directory}")

    initial_boundary = PhaseBoundary(
        cpu_microseconds=start_cpu_microseconds,
        wall_nanoseconds=start_wall_nanoseconds,
        peak_rss_bytes=0,
        utc=_utc_for_monotonic(start_wall_nanoseconds),
    )
    leader_binary_sha256, leader_binary_size_bytes = _current_cpython_identity()
    outer_argv = list(sys.argv)
    outer_argv_sha256 = _sha256(_canonical_body(outer_argv))
    preflight_pid = os.getpid()
    preflight_start_time_clock_ticks = _self_start_time_clock_ticks()
    host_environment = _observed_host_environment()
    numpy_authority = _numpy_distribution_authority()
    environment_preimage = {
        "host_environment": host_environment,
        "implementation_commit": implementation_commit,
        "leader_binary_sha256": leader_binary_sha256,
        "leader_binary_size_bytes": leader_binary_size_bytes,
        "numpy_authority": numpy_authority,
        "tool_paths": [CMAKE_BINARY, NINJA_BINARY, CXX_BINARY],
    }
    environment_sha256 = _sha256(_canonical_body(environment_preimage))
    prelaunch, observed_self_start = prelaunch_observer(
        root,
        {"environment_sha256": environment_sha256},
        process_inventory(),
        _utc_now(),
    )
    if (
        observed_self_start != preflight_start_time_clock_ticks
        or prelaunch.get("preflight_pid") != preflight_pid
        or prelaunch.get("preflight_start_time_clock_ticks")
        != preflight_start_time_clock_ticks
        or prelaunch.get("output_root") != str(root)
        or prelaunch.get("environment_identity_sha256") != environment_sha256
        or prelaunch.get("preconditions_pass") is not True
    ):
        _fail("PAR prelaunch observation does not bind the logical run")
    logical_run_preimage = {
        "execution_commit": implementation_commit,
        "outer_argv": outer_argv,
        "output_root": str(root),
        "preflight_pid": preflight_pid,
        "preflight_start_time_clock_ticks": preflight_start_time_clock_ticks,
        "prelaunch_utc": prelaunch["observed_utc"],
        "protocol_version": PROTOCOL_VERSION,
    }
    logical_run_id = _sha256(_canonical_body(logical_run_preimage))

    receipts: list[dict[str, Any]] = []
    build_created = 0
    build_deleted = 0
    build_live_hwm = 0
    build_evidence_bytes = 0
    b_start = initial_boundary
    b_success_start: PhaseBoundary | None = None
    b_success_end: PhaseBoundary | None = None
    b_success_attempt = -1
    prior_b: tuple[PhaseBoundary, PhaseBoundary, int, int, Path] | None = None
    for attempt_id in range(2):
        if attempt_id > 0:
            _CURRENT_DIRECT_CHILD_PEAK_RSS = 0
        if prior_b is not None:
            prior_start, prior_end, prior_signal, prior_created, prior_path = prior_b
            interrupted = _receipt_template(
                phase="B_build",
                attempt_id=attempt_id - 1,
                start=prior_start,
                logical_run_id=logical_run_id,
                implementation_commit=implementation_commit,
                environment_sha256=environment_sha256,
                binary_sha256=leader_binary_sha256,
                argv_sha256=outer_argv_sha256,
                exit_reason=f"EXTERNAL_SIGNAL_{prior_signal}",
                staging_disposition="DISCARDED",
            )
            _inject_receipt_end(interrupted, prior_start, prior_end)
            receipts.append(interrupted)
            build_created += prior_created
            build_live_hwm = max(build_live_hwm, prior_created)
            build_deleted += _discard_attempt(prior_path)
            for directory in (PRODUCER_BINARY.parent, VERIFIER_BINARY.parent):
                build_deleted += _discard_attempt(directory)
            prior_b = None
        attempt_path = staging / f"B{attempt_id}.staging"
        attempt_path.mkdir(mode=0o700)
        if any(
            directory.exists()
            for directory in (PRODUCER_BINARY.parent, VERIFIER_BINARY.parent)
        ):
            _fail("B_build attempt did not begin with absent build directories")
        attempt_created = 0
        names: tuple[str, ...] = ()

        def build_worker_task() -> None:
            _run_build_attempt(
                attempt=attempt_path,
                root=root,
                implementation_commit=implementation_commit,
                logical_run_preimage=logical_run_preimage,
                environment_preimage=environment_preimage,
                prelaunch_observation=prelaunch,
            )

        def build_worker_ready() -> None:
            nonlocal attempt_created, names, build_evidence_bytes

            attempt_created = (
                _tree_bytes(attempt_path)
                + _tree_bytes(PRODUCER_BINARY.parent)
                + _tree_bytes(VERIFIER_BINARY.parent)
            )
            names = _move_attempt_files(
                attempt_path, staging, BUILD_ARTIFACT_NAMES
            )
            build_evidence_bytes = sum(
                (staging / name).stat().st_size for name in names
            )

        try:
            family_peak = _run_fresh_phase_worker(
                build_worker_task, build_worker_ready
            )
            family_peak = max(family_peak, _CURRENT_DIRECT_CHILD_PEAK_RSS)
            build_created += attempt_created
            build_live_hwm = max(build_live_hwm, attempt_created)
            b_success_start = b_start
            b_success_end = _capture_boundary(snapshot, family_peak)
            b_success_attempt = attempt_id
            break
        except ExternalPhaseSignal as signal:
            attempt_peak = max(
                signal.phase_peak_rss_bytes, _CURRENT_DIRECT_CHILD_PEAK_RSS
            )
            end = _capture_boundary(snapshot, attempt_peak)
            if (
                signal.signal_number < 1
                or signal.signal_number > 64
                or attempt_id == 1
                or not signal.retry_safe
            ):
                raise ParityFailure("B_build exhausted its one external-signal restart")
            created = (
                _tree_bytes(attempt_path)
                + _tree_bytes(PRODUCER_BINARY.parent)
                + _tree_bytes(VERIFIER_BINARY.parent)
            )
            prior_b = (b_start, end, signal.signal_number, created, attempt_path)
            b_start = end
    if b_success_start is None or b_success_end is None:
        _fail("B_build did not reach a terminal successful attempt")

    build_complete_receipt = _receipt_template(
        phase="B_build",
        attempt_id=b_success_attempt,
        start=b_success_start,
        logical_run_id=logical_run_id,
        implementation_commit=implementation_commit,
        environment_sha256=environment_sha256,
        binary_sha256=leader_binary_sha256,
        argv_sha256=outer_argv_sha256,
        exit_reason="PHASE_COMPLETE",
        staging_disposition="NONE",
    )
    _inject_receipt_end(build_complete_receipt, b_success_start, b_success_end)
    receipts.append(build_complete_receipt)

    parity_created = 0
    parity_deleted = 0
    parity_live_hwm = 0
    p_start = b_success_end
    prior_p: tuple[PhaseBoundary, PhaseBoundary, int, int, Path] | None = None
    p_attempt_id = -1
    while p_attempt_id < 1:
        p_attempt_id += 1
        _CURRENT_DIRECT_CHILD_PEAK_RSS = 0
        if prior_p is not None:
            prior_start, prior_end, prior_signal, prior_created, prior_path = prior_p
            interrupted = _receipt_template(
                phase="P_parity",
                attempt_id=p_attempt_id - 1,
                start=prior_start,
                logical_run_id=logical_run_id,
                implementation_commit=implementation_commit,
                environment_sha256=environment_sha256,
                binary_sha256=leader_binary_sha256,
                argv_sha256=outer_argv_sha256,
                exit_reason=f"EXTERNAL_SIGNAL_{prior_signal}",
                staging_disposition="DISCARDED",
            )
            _inject_receipt_end(interrupted, prior_start, prior_end)
            receipts.append(interrupted)
            parity_created += prior_created
            persistent_live = (
                _tree_bytes(staging)
                + _tree_bytes(PRODUCER_BINARY.parent)
                + _tree_bytes(VERIFIER_BINARY.parent)
            )
            parity_live_hwm = max(parity_live_hwm, persistent_live)
            parity_deleted += _discard_attempt(prior_path)
            prior_p = None
        attempt_path = staging / f"P{p_attempt_id}.staging"
        attempt_path.mkdir(mode=0o700)
        worker_handle: _WorkerHandle | None = None
        worker_ready = False
        worker_reaped = False
        try:
            worker_handle = _launch_phase_worker(
                lambda: _run_parity_attempt(attempt_path, numpy_authority)
            )
            worker_start_hwm = worker_handle.supervisor_start_hwm
            worker_message = _receive_worker_message(worker_handle)
            worker_ready = (
                worker_message is not None
                and worker_message.get("state") == "READY"
            )
            if not worker_ready:
                worker_usage = _release_and_reap_worker(
                    worker_handle, release=False
                )
                worker_reaped = True
                direct_peak = (
                    int(worker_message["direct_child_peak_rss_bytes"])
                    if worker_message is not None
                    else 0
                )
                family_peak = max(worker_usage.peak_rss_bytes, direct_peak)
                if family_peak < worker_start_hwm:
                    _fail(
                        "fresh P worker did not naturally dominate inherited "
                        "supervisor HWM; RSS is not phase-identifiable"
                    )
                if worker_usage.exit_code < 0:
                    raise ExternalPhaseSignal(
                        -worker_usage.exit_code,
                        phase_peak_rss_bytes=family_peak,
                    )
                if worker_message is None:
                    _fail("P worker exited without its bounded status message")
                if worker_message["state"] == "EXTERNAL_SIGNAL":
                    raise ExternalPhaseSignal(
                        int(worker_message["signal_number"]),
                        phase_peak_rss_bytes=family_peak,
                    )
                _fail(f"P worker failed: {worker_message['detail']}")
            attempt_created = _tree_bytes(attempt_path)
            p_names = _move_attempt_files(
                attempt_path, staging, PARITY_ARTIFACT_NAMES
            )
            if set(p_names) & set(BUILD_ARTIFACT_NAMES):
                _fail("B/P artifact namespaces overlap")
            parity_created += attempt_created
            parity_live_hwm = max(parity_live_hwm, attempt_created)
            indexed_names = _regular_members(staging)
            expected_indexed_names = tuple(
                sorted(
                    (*BUILD_ARTIFACT_NAMES, *PARITY_ARTIFACT_NAMES),
                    key=lambda value: value.encode("utf-8"),
                )
            )
            if indexed_names != expected_indexed_names:
                _fail("exact B/P PAR staging membership changed")
            artifact_index = {
                "artifact_kind": "a4_v2_par_artifact_index",
                "files": [_artifact_file(staging / name) for name in indexed_names],
                "implementation_commit": implementation_commit,
                "schema_version": 1,
            }
            _write_new(staging / "artifact_index.json", _canonical_document(artifact_index))
            complete_names = _regular_members(staging)
            if complete_names != tuple(
                sorted(
                    (*indexed_names, "artifact_index.json"),
                    key=lambda value: value.encode("utf-8"),
                )
            ):
                _fail("pre-P terminal artifact membership changed")
            parity_created += (staging / "artifact_index.json").stat().st_size
            parity_evidence_bytes = sum(
                (staging / name).stat().st_size
                for name in (*p_names, "artifact_index.json")
            )
            build_tree_bytes = _tree_bytes(PRODUCER_BINARY.parent) + _tree_bytes(
                VERIFIER_BINARY.parent
            )
            parity_live_hwm = max(
                parity_live_hwm,
                build_tree_bytes + _tree_bytes(staging),
            )
            phase_byte_ledger = [
                {
                    "created_temporary_bytes": build_created,
                    "deleted_partial_bytes": build_deleted,
                    "maximum_live_owned_temporary_bytes": build_live_hwm,
                    "permanent_intermediate_bundle_bytes": 0,
                    "phase": "B_build",
                    "research_evidence_archive_bytes": build_evidence_bytes,
                },
                {
                    "created_temporary_bytes": parity_created,
                    "deleted_partial_bytes": parity_deleted,
                    "maximum_live_owned_temporary_bytes": parity_live_hwm,
                    "permanent_intermediate_bundle_bytes": 0,
                    "phase": "P_parity",
                    "research_evidence_archive_bytes": parity_evidence_bytes,
                },
            ]
            source_payload = _read_regular_nofollow(IMPLEMENTATION_MANIFEST)
            source_manifest = _parse_json(
                source_payload, "implementation source manifest", canonical=True
            )
            if not isinstance(source_manifest, dict):
                _fail("implementation source manifest is not an object")
            source_tree_sha256 = source_manifest.get("source_tree_sha256")
            if (
                not isinstance(source_tree_sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", source_tree_sha256) is None
            ):
                _fail("implementation manifest source-tree identity is invalid")
            seal_fixed: dict[str, Any] = {
                "artifact_index": _sealed_identity_for_artifact(
                    root, staging, "artifact_index.json"
                ),
                "artifact_kind": "a4_v2_par_seal",
                "build_manifest": _sealed_identity_for_artifact(
                    root, staging, "build_manifest.json"
                ),
                "implementation_commit": implementation_commit,
                "parity_pass": True,
                "parity_summary": _sealed_identity_for_artifact(
                    root, staging, "parity_summary.json"
                ),
                "phase_byte_ledger": phase_byte_ledger,
                "phase_receipts": [],
                "producer_native": _sealed("build/a4_v2/a4_v2_native"),
                "protocol": _sealed(
                    "docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json"
                ),
                "schema": _sealed(
                    "docs/saq_a4_v2_artifact_schema_2026_07_14.json"
                ),
                "schema_version": 1,
                "source_manifest": _sealed(
                    "docs/saq_a4_v2_implementation_manifest_2026_07_14.json"
                ),
                "source_tree_sha256": source_tree_sha256,
                "verifier_native": _sealed(
                    "build/a4_v2_verifier/a4_v2_native"
                ),
            }
            if len(seal_fixed) != 15:
                _fail("PAR seal fixed field count changed")
            p_receipt = _receipt_template(
                phase="P_parity",
                attempt_id=p_attempt_id,
                start=p_start,
                logical_run_id=logical_run_id,
                implementation_commit=implementation_commit,
                environment_sha256=environment_sha256,
                binary_sha256=leader_binary_sha256,
                argv_sha256=outer_argv_sha256,
                exit_reason="PHASE_COMPLETE",
                staging_disposition="NONE",
            )
            for name in complete_names:
                _fsync_regular_nofollow(staging / name)
            _fsync_directory(staging)
            parent_fd = os.open(
                staging.parent,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
            )
            staging_fd = os.open(
                staging,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
            )
            worker_usage = _release_and_reap_worker(
                worker_handle, release=True
            )
            worker_reaped = True
            direct_peak = int(worker_message["direct_child_peak_rss_bytes"])
            family_peak = max(worker_usage.peak_rss_bytes, direct_peak)
            if family_peak < worker_start_hwm:
                _fail(
                    "fresh P worker did not naturally dominate inherited "
                    "supervisor HWM; RSS is not phase-identifiable"
                )
            if worker_usage.exit_code < 0:
                raise ExternalPhaseSignal(
                    -worker_usage.exit_code,
                    phase_peak_rss_bytes=family_peak,
                    retry_safe=False,
                )
            if worker_usage.exit_code != 0:
                _fail("READY P worker did not exit cleanly after release")
            p_end = _capture_boundary(snapshot, family_peak)
            _post_par_report(
                p_receipt=p_receipt,
                p_start=p_start,
                p_end=p_end,
                receipts=receipts,
                phase_byte_ledger=phase_byte_ledger,
                seal_fixed=seal_fixed,
                staging_fd=staging_fd,
                parent_fd=parent_fd,
                staging_name=staging.name,
                published_name=root.name,
            )
        except ExternalPhaseSignal as signal:
            end = _capture_boundary(snapshot, signal.phase_peak_rss_bytes)
            if (
                signal.signal_number < 1
                or signal.signal_number > 64
                or p_attempt_id == 1
                or not signal.retry_safe
            ):
                raise ParityFailure("P_parity exhausted its one external-signal restart")
            created = _tree_bytes(attempt_path)
            prior_p = (p_start, end, signal.signal_number, created, attempt_path)
            p_start = end
        finally:
            if worker_handle is not None and not worker_reaped:
                _release_and_reap_worker(worker_handle, release=worker_ready)
    _fail("unreachable PAR_report return")


def _sealed_identity_for_artifact(root: Path, staging: Path, name: str) -> dict[str, Any]:
    payload = _read_regular_nofollow(staging / name)
    relative = root.relative_to(REPOSITORY_ROOT).as_posix() + "/" + name
    return {
        "path": relative,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }
