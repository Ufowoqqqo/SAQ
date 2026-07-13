#!/usr/bin/env python3
"""Scientific runner for the frozen synthetic-only A4-1S implementation gate.

The script deliberately has no data-root arguments and imports NumPy only
inside an authorized, clean-commit execution.  The compiled executable is the
optimized authority; :mod:`a4_1s_reference` is the independent small-fixture
authority.
"""

from __future__ import annotations

import argparse
import array
import contextlib
import ctypes
import hashlib
import itertools
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

import a4_1s_artifacts as artifacts
import a4_1s_reference as reference


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_SPEC_PATH = REPO_ROOT / "docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json"
HYPOTHESES_PATH = REPO_ROOT / "docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json"
PROTOCOL_PATH = REPO_ROOT / "docs/saq_attempt4_a4_1s_synthetic_implementation_protocol_2026_07_13.md"
NATIVE_BINARY = REPO_ROOT / "build/a4_1s/a4_1s_native"
COMPILE_COMMANDS = REPO_ROOT / "build/a4_1s/compile_commands.json"
COMMITTED_PARITY_DIR = REPO_ROOT / "docs/saq_attempt4_a4_1s_artifacts_2026_07_13"
PARITY_REVIEW_PATH = REPO_ROOT / "docs/saq_attempt4_a4_1s_implementation_parity_review_2026_07_13.md"

PROTOCOL_VERSION = artifacts.PROTOCOL_VERSION
SCIENTIFIC_PROTOCOL_VERSION = "saq-attempt4-a4-1-20260713-schema2"
SEED = 20260713
FULL_ROWS = 8192
FULL_DIMENSIONS = 128
FULL_COORDINATE_CARDINALITY = 256
FULL_GROUP_COUNT = 64
BLOCK_START_COUNT = 8
CPU_PANEL_LIMIT_US = 34_560_000_000
PROJECTED_LIMIT_US = 86_400_000_000

PARITY_FILENAMES = (
    "build_manifest.json",
    "scalar_exact_parity.json",
    "representation_parity.json",
    "block_vq_parity.json",
    "parity_summary.json",
)

SOURCE_PATHS = (
    "research/a4_1s/CMakeLists.txt",
    "research/a4_1s/a4_1s_native.cpp",
    "research/a4_1s/allocation_curve_io.hpp",
    "research/a4_1s/allocation_item_cli.hpp",
    "research/a4_1s/allocation_item_cli_impl.hpp",
    "research/a4_1s/exact_quantizer.cpp",
    "research/a4_1s/exact_quantizer.hpp",
    "research/a4_1s/exhaustive_product_reference.hpp",
    "research/a4_1s/numeric_runtime.cpp",
    "research/a4_1s/numeric_runtime.hpp",
    "research/a4_1s/block_vq.cpp",
    "research/a4_1s/block_vq.hpp",
    "research/a4_1s/block_cli.cpp",
    "research/a4_1s/block_cli.hpp",
    "research/a4_1s/representation.cpp",
    "research/a4_1s/representation.hpp",
    "research/a4_1s/representation_cli.cpp",
    "research/a4_1s/representation_cli.hpp",
    "script/a4_1s_artifacts.py",
    "script/a4_1s_bootstrap_usage.py",
    "script/a4_1s_reference.py",
    "script/a4_1s_runner.py",
    "script/evaluate_arbitrary_cardinality.py",
    "script/run_arbitrary_cardinality_a4_1s.py",
    "tests/test_a4_1s_reference.py",
    "tests/test_evaluate_arbitrary_cardinality.py",
)

FROZEN_CONTRACT_BLOBS = (
    (
        INPUT_SPEC_PATH,
        "3aa2f6e219763cfe72218050e420766a5a0efbcb",
        "8bbac813ba09b58d2a290ea67580d78266739c2d",
    ),
    (
        HYPOTHESES_PATH,
        "3aa2f6e219763cfe72218050e420766a5a0efbcb",
        "1faff6b1cff190967d030d98765ad9e5a3f2f21a",
    ),
    (
        PROTOCOL_PATH,
        "3c0a49f6a9d7de5c394635a8b7e6ac8035affed8",
        "b86487ad9c457389f77cccebd3ac3e088bfed1fe",
    ),
)

_UINT_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")
_SINT_RE = re.compile(r"^(?:0|-?[1-9][0-9]*)$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BITS32_RE = re.compile(r"^0x[0-9a-f]{8}$")
_BITS64_RE = re.compile(r"^0x[0-9a-f]{16}$")
_FAILURE_NAMES = {
    "NONE",
    "NONFINITE_CONTROL",
    "CANDIDATE_SSE_INCREASE",
    "ITERATION_LIMIT",
    "SERIALIZED_CENTER_COLLISION",
    "CARTESIAN_DOMINANCE",
}

EXTRA_FORBIDDEN_ROOTS = (
    REPO_ROOT / "data",
    REPO_ROOT / "results",
    Path("/rwproject/kdd-db/kluaq/saq/data"),
    Path("/rwproject/kdd-db/kluaq/saq/results"),
    Path("/rwproject/kdd-db/kluaq/saq/data/gist_sample50k"),
    Path("/tmp/saq-run/data/cifar60k"),
)


class GateFailure(RuntimeError):
    """A registered A4-1S status that must stop the runner."""

    def __init__(self, status: str, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


_FROZEN_TERMINAL_PRECEDENCE = (
    "ARTIFACT_INVALID",
    "IMPLEMENTATION_INVALID",
    "CONTROL_INVALID",
    "NO_GO_REPRESENTATION",
    "NO_GO_EXACT_SOLVER_COST",
)


def _resolve_frozen_terminal_status(candidates: Iterable[str]) -> str:
    """Return the first applicable frozen status, or the synthetic pass."""

    observed = list(candidates)
    if any(status not in _FROZEN_TERMINAL_PRECEDENCE for status in observed):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "unknown frozen terminal-status candidate"
        )
    if not observed:
        return "PASS_SYNTHETIC_GATE_ONLY"
    rank = {status: index for index, status in enumerate(_FROZEN_TERMINAL_PRECEDENCE)}
    return min(observed, key=rank.__getitem__)


def _status_precedence_fixture() -> dict[str, Any]:
    """Execute the complete deterministic precedence fault matrix."""

    cases = (
        (
            "artifact_over_all",
            list(reversed(_FROZEN_TERMINAL_PRECEDENCE)),
            "ARTIFACT_INVALID",
        ),
        (
            "implementation_over_downstream",
            list(reversed(_FROZEN_TERMINAL_PRECEDENCE[1:])),
            "IMPLEMENTATION_INVALID",
        ),
        (
            "control_over_representation_and_cost",
            [
                "NO_GO_EXACT_SOLVER_COST",
                "NO_GO_REPRESENTATION",
                "CONTROL_INVALID",
            ],
            "CONTROL_INVALID",
        ),
        (
            "representation_over_cost",
            ["NO_GO_EXACT_SOLVER_COST", "NO_GO_REPRESENTATION"],
            "NO_GO_REPRESENTATION",
        ),
        (
            "cost_only",
            ["NO_GO_EXACT_SOLVER_COST"],
            "NO_GO_EXACT_SOLVER_COST",
        ),
        ("no_failure", [], "PASS_SYNTHETIC_GATE_ONLY"),
    )
    records = []
    for name, candidates, expected in cases:
        observed = _resolve_frozen_terminal_status(candidates)
        if observed != expected:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"status precedence fixture failed: {name}",
            )
        records.append(
            {
                "case": name,
                "candidates": candidates,
                "expected": expected,
                "observed": observed,
            }
        )
    return {"case_count": len(records), "cases": records, "passed": True}


def _tsv_uint(text: str, field: str, *, maximum: int | None = None) -> int:
    if not isinstance(text, str) or _UINT_RE.fullmatch(text) is None:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not canonical unsigned decimal")
    value = int(text)
    if maximum is not None and value > maximum:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} exceeds its declared range")
    return value


def _tsv_sint(text: str, field: str) -> int:
    if not isinstance(text, str) or _SINT_RE.fullmatch(text) is None:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not canonical signed decimal")
    return int(text)


def _tsv_bool(text: str, field: str) -> bool:
    if text not in {"0", "1"}:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not a canonical TSV boolean")
    return text == "1"


def _tsv_bits(text: str, width: int, field: str) -> str:
    pattern = _BITS32_RE if width == 32 else _BITS64_RE
    if not isinstance(text, str) or pattern.fullmatch(text) is None:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not canonical bits{width}")
    return text


def _tsv_sha256(text: str, field: str) -> str:
    if not isinstance(text, str) or _SHA256_RE.fullmatch(text) is None:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not canonical SHA-256")
    return text


def _tsv_rational(
    numerator_text: str,
    denominator_text: str,
    field: str,
    *,
    signed: bool,
) -> tuple[str, str]:
    numerator = (
        _tsv_sint(numerator_text, f"{field}.numerator")
        if signed
        else _tsv_uint(numerator_text, f"{field}.numerator")
    )
    denominator = _tsv_uint(denominator_text, f"{field}.denominator")
    if denominator == 0:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field}.denominator must be positive")
    if math.gcd(abs(numerator), denominator) != 1 or (numerator == 0 and denominator != 1):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not a reduced rational")
    return numerator_text, denominator_text


def _json_int(
    value: Any,
    field: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not an integer >= {minimum}")
    if maximum is not None and value > maximum:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} exceeds {maximum}")
    return value


def _json_count(value: Any, field: str) -> int:
    if not isinstance(value, str) or _UINT_RE.fullmatch(value) is None:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not a canonical count string")
    return int(value)


def _json_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not canonical SHA-256")
    return value


def _json_bits(value: Any, width: int, field: str) -> str:
    pattern = _BITS32_RE if width == 32 else _BITS64_RE
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not canonical bits{width}")
    return value


def _json_boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not boolean")
    return value


def _json_exact_rational(
    value: Any,
    field: str,
    *,
    exponent: int,
    signed: bool,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} is not an exact-rational object")
    _require_exact_keys(
        value,
        {"binary_grid_exponent", "denominator", "numerator"},
        field,
    )
    if value["binary_grid_exponent"] != exponent or isinstance(
        value["binary_grid_exponent"], bool
    ):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} exponent mismatch")
    numerator_text = value["numerator"]
    denominator_text = value["denominator"]
    if not isinstance(numerator_text, str) or not isinstance(denominator_text, str):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} rational fields are not strings")
    _tsv_rational(numerator_text, denominator_text, field, signed=signed)
    return value


@dataclass(frozen=True)
class ScalarCase:
    case_id: int
    suite: str
    value_bits: tuple[int, ...]
    weights: tuple[int, ...]
    vector_ids: tuple[int, ...]
    maximum_cardinality: int
    suite_index: int


@dataclass
class CompactCoordinateModel:
    effective_cardinalities: list[int]
    objectives: list[dict[str, Any]]
    binary32_centroids: list[array.array]
    binary64_centroids: list[array.array]
    distinct_support_size: int


@dataclass
class CostTerminalState:
    """Mutable state needed to publish a registered terminal prefix."""

    ready: bool = False
    finalizing: bool = False
    output_dir: Path | None = None
    plan: list[dict[str, Any]] | None = None
    completed: list[dict[str, Any]] | None = None
    working: Path | None = None
    implementation_commit: str = ""
    parity_evidence_commit: str = ""
    parity_review_commit: str = ""
    execution_commit: str = ""
    thread_environment: Mapping[str, str] | None = None
    input_ledger: Sequence[Mapping[str, Any]] | None = None
    runtime_numeric: Mapping[str, Any] | None = None
    parity_build: Mapping[str, Any] | None = None
    array_identity: Mapping[str, Any] | None = None
    clock: "ComponentClock | None" = None
    counters: Mapping[str, Any] | None = None
    phase: str = "preflight"
    current_plan_index: int = -1
    context: dict[str, Any] | None = None


def _deterministic_owned_buffer_bytes(*roots: Any) -> int:
    """Count unique logical payload buffers, excluding interpreter headers.

    The metric is deterministic across allocators/Python builds: ndarray and
    ``array.array`` payloads count their exact byte capacity, byte/string
    payloads count their encoded bytes, and containers/dataclasses recurse
    without charging implementation-dependent object headers.
    """

    seen: set[int] = set()

    def visit(value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, bool):
            return 1
        if isinstance(value, int):
            return max(1, (abs(value).bit_length() + 7) // 8)
        if isinstance(value, float):
            return 8
        if isinstance(value, Fraction):
            return visit(value.numerator) + visit(value.denominator)
        identity = id(value)
        if identity in seen:
            return 0
        seen.add(identity)
        if isinstance(value, str):
            return len(value.encode("utf-8"))
        if isinstance(value, (bytes, bytearray, memoryview)):
            return int(value.nbytes) if isinstance(value, memoryview) else len(value)
        if isinstance(value, array.array):
            return len(value) * value.itemsize
        # Avoid importing NumPy here; the dynamically imported ndarray exposes
        # these stable payload properties.
        if type(value).__module__.startswith("numpy") and hasattr(value, "nbytes"):
            return int(value.nbytes)
        if isinstance(value, Mapping):
            return sum(visit(key) + visit(item) for key, item in value.items())
        if isinstance(value, (list, tuple, set, frozenset)):
            return sum(visit(item) for item in value)
        if hasattr(value, "__dict__"):
            return visit(vars(value))
        return 0

    return sum(visit(root) for root in roots)


def _update_supervisor_owned_buffer_hwm(
    counters: dict[str, Any],
    stage: str,
    *roots: Any,
    transient_payload_bytes: int = 0,
) -> int:
    """Update the deterministic Python-supervisor logical-payload HWM.

    Native child address spaces are intentionally a separate scope and are
    covered by process-family peak RSS (plus the encoding child's explicit
    payload diagnostic).  ``transient_payload_bytes`` is used for parser and
    canonical-line frames that are no longer reachable when a stage returns.
    """

    if (
        not isinstance(transient_payload_bytes, int)
        or isinstance(transient_payload_bytes, bool)
        or transient_payload_bytes < 0
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "owned-buffer transient bound is invalid"
        )
    observed = (
        _deterministic_owned_buffer_bytes(*roots) + transient_payload_bytes
    )
    counters["owned_buffer_high_water_bytes"] = max(
        int(counters.get("owned_buffer_high_water_bytes", 0)), observed
    )
    by_stage = counters.setdefault("supervisor_owned_buffer_stage_high_water_bytes", {})
    if not isinstance(by_stage, dict):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "owned-buffer stage inventory is invalid"
        )
    by_stage[stage] = max(int(by_stage.get(stage, 0)), observed)
    return observed


class ComponentClock:
    """Partition the exact whole-command resource delta without gaps."""

    NAMES = (
        "preflight",
        "generation_and_order",
        "scalar",
        "allocation",
        "block",
        "encoding",
        "shard_serialization",
    )

    def __init__(self, start_cpu_us: int, start_wall_ns: int) -> None:
        self.start_cpu_us = start_cpu_us
        self.start_wall_ns = start_wall_ns
        self.last_cpu_us = start_cpu_us
        self.last_wall_ns = start_wall_ns
        self.current = "preflight"
        self.cpu = {name: 0 for name in self.NAMES}
        self.wall = {name: 0 for name in self.NAMES}

    def switch(self, name: str) -> None:
        if name not in self.cpu:
            raise ValueError(f"unknown timing component {name}")
        now_cpu = _cpu_usage_us()
        now_wall = _wall_ns()
        if now_cpu < self.last_cpu_us or now_wall < self.last_wall_ns:
            raise GateFailure("IMPLEMENTATION_INVALID", "resource clock moved backwards")
        self.cpu[self.current] += now_cpu - self.last_cpu_us
        self.wall[self.current] += now_wall - self.last_wall_ns
        self.last_cpu_us = now_cpu
        self.last_wall_ns = now_wall
        self.current = name

    def cumulative_cpu_us(self) -> int:
        return _cpu_usage_us() - self.start_cpu_us

    def finish(self) -> tuple[int, int, dict[str, int], dict[str, int], int]:
        end_cpu, peak_rss_bytes = _usage_snapshot()
        end_wall = _wall_ns()
        self.cpu[self.current] += end_cpu - self.last_cpu_us
        self.wall[self.current] += end_wall - self.last_wall_ns
        total_cpu = end_cpu - self.start_cpu_us
        total_wall = end_wall - self.start_wall_ns
        if sum(self.cpu.values()) != total_cpu or sum(self.wall.values()) != total_wall:
            raise GateFailure("IMPLEMENTATION_INVALID", "component timing does not partition total")
        cpu = {**self.cpu, "total": total_cpu}
        wall = {**self.wall, "total": total_wall}
        return total_cpu, total_wall, cpu, wall, peak_rss_bytes


def _usage_snapshot() -> tuple[int, int]:
    class Timeval(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]

    class Rusage(ctypes.Structure):
        _fields_ = [
            ("ru_utime", Timeval),
            ("ru_stime", Timeval),
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

    libc = ctypes.CDLL(None, use_errno=True)
    getrusage = libc.getrusage
    getrusage.argtypes = [ctypes.c_int, ctypes.POINTER(Rusage)]
    getrusage.restype = ctypes.c_int

    total = 0
    process_family_peak_bound_kib = 0
    for who in (0, -1):  # RUSAGE_SELF, RUSAGE_CHILDREN on Linux.
        usage = Rusage()
        if getrusage(who, ctypes.byref(usage)) != 0:
            errno = ctypes.get_errno()
            raise OSError(errno, os.strerror(errno))
        for value in (usage.ru_utime, usage.ru_stime):
            if not 0 <= value.tv_usec < 1_000_000:
                raise RuntimeError("getrusage returned a noncanonical timeval")
            total += int(value.tv_sec) * 1_000_000 + int(value.tv_usec)
        process_family_peak_bound_kib += max(0, int(usage.ru_maxrss))
    return total, process_family_peak_bound_kib * 1024


def _cpu_usage_us() -> int:
    return _usage_snapshot()[0]


def _wall_ns() -> int:
    return time.monotonic_ns()


def _hex32(value: int) -> str:
    return f"0x{value:08x}"


def _hex64(value: int) -> str:
    return f"0x{value:016x}"


def _exact_value(value: Fraction, exponent: int) -> dict[str, Any]:
    return {
        "binary_grid_exponent": exponent,
        "denominator": str(value.denominator),
        "numerator": str(value.numerator),
    }


def _sha256_canonical_array(values: Sequence[Any]) -> str:
    return artifacts.sha256_bytes(artifacts.canonical_json_bytes(list(values)))


def _read_json_guarded(path: Path, *, allowed: Sequence[Path]) -> dict[str, Any]:
    try:
        checked = artifacts.guard_synthetic_read_path(
            path,
            repo_root=REPO_ROOT,
            allowed_files=allowed,
            extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
            require_allowlist_match=True,
        )
    except artifacts.ArtifactContractError as error:
        raise GateFailure("ARTIFACT_INVALID", str(error)) from error
    try:
        value = json.loads(checked.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GateFailure("ARTIFACT_INVALID", f"cannot read contract {path}: {error}") from error
    if not isinstance(value, dict):
        raise GateFailure("ARTIFACT_INVALID", f"contract {path} is not an object")
    return value


def _prepare_output_directory(path: Path) -> Path:
    try:
        resolved = artifacts.guard_synthetic_read_path(
            path,
            repo_root=REPO_ROOT,
            extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
            require_allowlist_match=False,
        )
    except artifacts.ArtifactContractError as error:
        raise GateFailure("ARTIFACT_INVALID", f"forbidden output path: {error}") from error
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise GateFailure("ARTIFACT_INVALID", "A4-1S output must be outside the repository")
    if resolved.exists():
        if not resolved.is_dir() or any(resolved.iterdir()):
            raise GateFailure("ARTIFACT_INVALID", "output directory must not exist or be empty")
    else:
        resolved.mkdir(parents=True)
    return resolved


def _validate_contracts(input_spec: Mapping[str, Any], hypotheses: Mapping[str, Any]) -> None:
    if input_spec.get("protocol_version") != SCIENTIFIC_PROTOCOL_VERSION:
        raise GateFailure("ARTIFACT_INVALID", "input-spec protocol identity mismatch")
    if input_spec.get("stage") != "A4-1P" or input_spec.get("schema_version") != 2:
        raise GateFailure("ARTIFACT_INVALID", "input-spec stage/schema mismatch")
    if hypotheses.get("protocol_version") != SCIENTIFIC_PROTOCOL_VERSION:
        raise GateFailure("ARTIFACT_INVALID", "hypotheses protocol identity mismatch")
    panel = input_spec.get("group_panel", {})
    fitting = input_spec.get("fitting", {})
    execution = input_spec.get("execution", {})
    if panel.get("group_count") != 64 or panel.get("group_width") != 2:
        raise GateFailure("ARTIFACT_INVALID", "frozen group-panel shape mismatch")
    if panel.get("word_bits") != [4, 8] or panel.get("capacities") != [16, 256]:
        raise GateFailure("ARTIFACT_INVALID", "frozen rates/capacities mismatch")
    if fitting.get("maximum_scalar_cardinality") != 256:
        raise GateFailure("ARTIFACT_INVALID", "maximum scalar cardinality mismatch")
    if fitting.get("block_vq_start_count") != 8:
        raise GateFailure("ARTIFACT_INVALID", "block start count mismatch")
    if execution.get("threads") != 1:
        raise GateFailure("ARTIFACT_INVALID", "thread contract mismatch")


def _bind_frozen_contract_blobs(execution_commit: str) -> None:
    """Bind both current files and their named provenance commits exactly."""

    for path, source_commit, expected_blob in FROZEN_CONTRACT_BLOBS:
        relative = path.relative_to(REPO_ROOT).as_posix()
        try:
            payload = path.read_bytes()
            observed_blob = hashlib.sha1(
                f"blob {len(payload)}\0".encode("ascii") + payload
            ).hexdigest()
            source_blob = artifacts.git_blob_oid(
                REPO_ROOT, relative, commit=source_commit
            )
            execution_blob = artifacts.git_blob_oid(
                REPO_ROOT, relative, commit=execution_commit
            )
        except (OSError, artifacts.ArtifactContractError) as error:
            raise GateFailure(
                "ARTIFACT_INVALID",
                f"cannot bind frozen contract blob {relative}: {error}",
            ) from error
        if (
            observed_blob != expected_blob
            or source_blob != expected_blob
            or execution_blob != expected_blob
        ):
            raise GateFailure(
                "ARTIFACT_INVALID",
                f"frozen contract blob mismatch: {relative}",
            )


def _input_ledger() -> list[dict[str, Any]]:
    contract_paths = (INPUT_SPEC_PATH, HYPOTHESES_PATH, PROTOCOL_PATH)
    try:
        for path in contract_paths:
            artifacts.guard_synthetic_read_path(
                path,
                repo_root=REPO_ROOT,
                allowed_files=contract_paths,
                extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
                require_allowlist_match=True,
            )
        return artifacts.sort_ledger(
            (
                artifacts.make_input_ledger_entry(
                    INPUT_SPEC_PATH,
                    ledger_path=INPUT_SPEC_PATH.relative_to(REPO_ROOT).as_posix(),
                    role="frozen_input_spec",
                ),
                artifacts.make_input_ledger_entry(
                    HYPOTHESES_PATH,
                    ledger_path=HYPOTHESES_PATH.relative_to(REPO_ROOT).as_posix(),
                    role="frozen_hypotheses",
                ),
                artifacts.make_input_ledger_entry(
                    PROTOCOL_PATH,
                    ledger_path=PROTOCOL_PATH.relative_to(REPO_ROOT).as_posix(),
                    role="a4_1s_protocol",
                ),
            )
        )
    except (artifacts.ArtifactContractError, OSError) as error:
        raise GateFailure(
            "ARTIFACT_INVALID", f"cannot bind frozen A4-1S contracts: {error}"
        ) from error


def _run_native(arguments: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    command = [str(NATIVE_BINARY), *arguments]
    process = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"native command failed ({process.returncode}): {' '.join(command)}: "
            f"{(process.stderr or '').strip()}",
        )
    return process


def _runtime_numeric_manifest() -> dict[str, Any]:
    process = _run_native(("manifest",), capture=True)
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise GateFailure("IMPLEMENTATION_INVALID", "native manifest is not JSON") from error
    if not isinstance(value, dict):
        raise GateFailure("IMPLEMENTATION_INVALID", "native manifest must be a JSON object")
    _require_exact_keys(
        value,
        {
            "compiler_id",
            "compiler_version",
            "compile_flags",
            "cpu_model",
            "gmp_version",
            "mpfr_version",
            "openssl_version",
            "initial_rounding_mode",
            "initial_rounding_mode_name",
            "initial_mxcsr",
            "initial_mxcsr_flush_to_zero",
            "initial_mxcsr_denormals_are_zero",
            "final_rounding_mode",
            "final_rounding_mode_name",
            "final_mxcsr",
            "final_mxcsr_flush_to_zero",
            "final_mxcsr_denormals_are_zero",
        },
        "native numeric manifest",
    )
    expected = {
        "compiler_id": "GCC",
        "compile_flags": (
            "-O3 -fno-fast-math -ffp-contract=off "
            "-frounding-math -mfpmath=sse"
        ),
        "initial_rounding_mode": 0,
        "initial_rounding_mode_name": "FE_TONEAREST",
        "initial_mxcsr_flush_to_zero": False,
        "initial_mxcsr_denormals_are_zero": False,
        "final_rounding_mode": 0,
        "final_rounding_mode_name": "FE_TONEAREST",
        "final_mxcsr_flush_to_zero": False,
        "final_mxcsr_denormals_are_zero": False,
    }
    for key, wanted in expected.items():
        observed = value.get(key)
        if type(observed) is not type(wanted) or observed != wanted:
            raise GateFailure("IMPLEMENTATION_INVALID", f"numeric manifest mismatch: {key}")
    compiler_version = value.get("compiler_version")
    if (
        not isinstance(compiler_version, str)
        or not compiler_version
        or compiler_version.split(maxsplit=1)[0] != "11.5.0"
    ):
        raise GateFailure("IMPLEMENTATION_INVALID", "native compiler is not GCC 11.5.0")
    for field in ("cpu_model", "gmp_version", "mpfr_version", "openssl_version"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", f"numeric manifest omits {field}"
            )
    for field in ("initial_mxcsr", "final_mxcsr"):
        if not isinstance(value.get(field), str) or _BITS32_RE.fullmatch(value[field]) is None:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", f"numeric manifest {field} is not canonical"
            )
    if value["initial_mxcsr"] != value["final_mxcsr"]:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "numeric MXCSR changed between initial/final snapshots"
        )
    return value


def _int_grid_bits(value: int) -> int:
    if value not in {-2, -1, 0, 1, 2}:
        raise ValueError("tiny integer is outside the frozen universe")
    return reference.float32_bits(float(value))


def _generate_scalar_cases(np: Any) -> list[ScalarCase]:
    cases: list[ScalarCase] = []
    case_id = 0
    universe = (-2, -1, 0, 1, 2)
    for support_size in range(1, 5):
        for support in itertools.combinations(universe, support_size):
            for weights in itertools.product((1, 2, 3), repeat=support_size):
                cases.append(
                    ScalarCase(
                        case_id,
                        "exhaustive_tiny",
                        tuple(_int_grid_bits(value) for value in support),
                        tuple(weights),
                        tuple(range(support_size)),
                        support_size,
                        case_id,
                    )
                )
                case_id += 1
    if case_id != 780:
        raise AssertionError(f"tiny suite generated {case_id}, expected 780")

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
    for suite_index, (bits, weights) in enumerate(bit_cases):
        distinct = len(set(reference.decode_float32_grid(value) for value in bits))
        cases.append(
            ScalarCase(
                case_id,
                "bit_pattern",
                tuple(bits),
                tuple(weights),
                tuple(range(len(bits))),
                distinct,
                suite_index,
            )
        )
        case_id += 1

    generator = np.random.Generator(np.random.PCG64(SEED))
    for suite_index in range(256):
        size = 1 + suite_index % 12
        values = generator.integers(-8, 9, size=size)
        weights = generator.integers(1, 6, size=size)
        float_values = np.asarray(values, dtype=np.float32)
        value_bits = tuple(int(value) for value in float_values.view(np.uint32))
        distinct = len(set(reference.decode_float32_grid(value) for value in value_bits))
        cases.append(
            ScalarCase(
                case_id,
                "pcg64_256",
                value_bits,
                tuple(int(value) for value in weights),
                tuple(range(size)),
                min(8, distinct),
                suite_index,
            )
        )
        case_id += 1
    if len(cases) != 1044:
        raise AssertionError("scalar fixture inventory mismatch")
    return cases


def _write_scalar_input(path: Path, cases: Sequence[ScalarCase]) -> None:
    with path.open("xb") as output:
        output.write(b"A4SCL001")
        output.write(struct.pack("<I", len(cases)))
        for case in cases:
            output.write(
                struct.pack(
                    "<III",
                    case.case_id,
                    len(case.value_bits),
                    case.maximum_cardinality,
                )
            )
            for bits, weight, vector_id in zip(
                case.value_bits, case.weights, case.vector_ids
            ):
                output.write(struct.pack("<IQQ", bits, weight, vector_id))
        output.flush()


def _parse_scalar_output(path: Path) -> dict[int, dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0] != "A4S_SCALAR_RESULT_V1":
            raise GateFailure("IMPLEMENTATION_INVALID", "scalar native output header mismatch")
        parsed: dict[int, dict[str, Any]] = {}
        ended_cases: set[int] = set()
        saw_end = False
        declared_case_count: int | None = None
        for line_index, line in enumerate(lines[1:], start=1):
            fields = line.split("\t")
            kind = fields[0]
            if kind == "END":
                if len(fields) != 2 or saw_end or line_index != len(lines) - 1:
                    raise GateFailure(
                        "IMPLEMENTATION_INVALID",
                        "scalar END is missing, duplicate, malformed, or nonterminal",
                    )
                declared_case_count = _tsv_uint(fields[1], "scalar END case_count")
                saw_end = True
                continue
            if saw_end or len(fields) < 2:
                raise GateFailure("IMPLEMENTATION_INVALID", "scalar record follows END or is truncated")
            case_id = _tsv_uint(fields[1], "scalar case_id", maximum=(1 << 32) - 1)
            if kind == "CASE":
                if len(fields) != 10 or case_id in parsed:
                    raise GateFailure("IMPLEMENTATION_INVALID", "duplicate or malformed scalar CASE")
                sample_count = _tsv_uint(fields[2], "scalar sample_count")
                maximum_cardinality = _tsv_uint(fields[3], "scalar maximum_cardinality")
                support_count = _tsv_uint(fields[4], "scalar support_count")
                if sample_count <= 0 or maximum_cardinality <= 0 or not 1 <= support_count <= sample_count:
                    raise GateFailure("IMPLEMENTATION_INVALID", "invalid scalar CASE shape")
                parsed[case_id] = {
                    "sample_count": sample_count,
                    "maximum_cardinality": maximum_cardinality,
                    "support_count": support_count,
                    "diagnostics": {
                        "exact_comparisons": _tsv_uint(fields[5], "scalar exact_comparisons"),
                        "exact_ties": _tsv_uint(fields[6], "scalar exact_ties"),
                        "matrix_entry_evaluations": _tsv_uint(fields[7], "scalar matrix evaluations"),
                        "interval_evaluations": _tsv_uint(fields[8], "scalar interval evaluations"),
                        "exact_replay_checks": _tsv_uint(fields[9], "scalar replay checks"),
                    },
                    "support": [],
                    "solutions": {},
                    "monotone": {},
                }
                continue
            if case_id not in parsed or case_id in ended_cases:
                raise GateFailure("IMPLEMENTATION_INVALID", "scalar record is outside an open case")
            case = parsed[case_id]
            if kind == "SUPPORT":
                if len(fields) != 6 or _tsv_uint(fields[2], "scalar support_id") != len(case["support"]):
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar support order/field mismatch")
                _tsv_sint(fields[3], "scalar support grid_integer")
                if _tsv_uint(fields[4], "scalar support weight") == 0:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar support weight must be positive")
                case["support"].append(
                    {
                        "support_id": _tsv_uint(fields[2], "scalar support_id"),
                        "grid_integer": fields[3],
                        "weight": fields[4],
                        "lowest_vector_id": _tsv_uint(fields[5], "scalar lowest_vector_id"),
                    }
                )
            elif kind == "SOLUTION":
                if len(fields) != 10:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar SOLUTION field count mismatch")
                cardinality = _tsv_uint(fields[2], "scalar requested_cardinality")
                if cardinality in case["solutions"] or not 1 <= cardinality <= case["maximum_cardinality"]:
                    raise GateFailure("IMPLEMENTATION_INVALID", "duplicate/out-of-range scalar solution")
                effective = _tsv_uint(fields[3], "scalar effective_cardinality")
                cluster_count = _tsv_uint(fields[7], "scalar cluster_count")
                if not 1 <= effective <= cardinality or cluster_count != effective:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar effective/cluster count mismatch")
                _tsv_rational(fields[4], fields[5], "scalar objective", signed=False)
                if _tsv_sint(fields[6], "scalar objective exponent") != -298:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar objective exponent mismatch")
                case["solutions"][cardinality] = {
                    "requested_cardinality": cardinality,
                    "effective_cardinality": effective,
                    "objective": {
                        "numerator": fields[4],
                        "denominator": fields[5],
                        "binary_grid_exponent": _tsv_sint(fields[6], "scalar objective exponent"),
                    },
                    "cluster_count": cluster_count,
                    "comparison_count": _tsv_uint(fields[8], "scalar solution comparison_count"),
                    "exact_tie_count": _tsv_uint(fields[9], "scalar solution exact_tie_count"),
                    "clusters": [],
                    "predecessor_indices": [],
                    "predecessor_seen": False,
                }
            elif kind == "CLUSTER":
                if len(fields) != 11:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar CLUSTER field count mismatch")
                solution = case["solutions"][_tsv_uint(fields[2], "scalar cluster cardinality")]
                cluster_id = _tsv_uint(fields[3], "scalar cluster_id")
                if solution["predecessor_seen"] or cluster_id != len(solution["clusters"]):
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar cluster order mismatch")
                begin = _tsv_uint(fields[4], "scalar cluster begin")
                end = _tsv_uint(fields[5], "scalar cluster end")
                _tsv_rational(fields[6], fields[7], "scalar cluster mean", signed=True)
                if _tsv_sint(fields[8], "scalar mean exponent") != -149:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar mean exponent mismatch")
                _tsv_bits(fields[9], 32, "scalar centroid binary32")
                _tsv_bits(fields[10], 64, "scalar centroid binary64")
                solution["clusters"].append(
                    {
                        "cluster_id": cluster_id,
                        "begin": begin,
                        "end": end,
                        "mean": {
                            "numerator": fields[6],
                            "denominator": fields[7],
                            "binary_grid_exponent": _tsv_sint(fields[8], "scalar mean exponent"),
                        },
                        "binary32_bits": fields[9],
                        "binary64_bits": fields[10],
                    }
                )
            elif kind == "PREDECESSOR_ROW":
                if len(fields) < 4:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar predecessor row is truncated")
                solution = case["solutions"][_tsv_uint(fields[2], "scalar predecessor cardinality")]
                if solution["predecessor_seen"]:
                    raise GateFailure("IMPLEMENTATION_INVALID", "duplicate scalar predecessor row")
                expected_count = _tsv_uint(fields[3], "scalar predecessor count")
                values = [
                    _tsv_uint(value, "scalar predecessor index") for value in fields[4:]
                ]
                if len(values) != expected_count or expected_count != case["support_count"] + 1:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar predecessor row length mismatch")
                solution["predecessor_indices"] = values
                solution["predecessor_seen"] = True
            elif kind == "MONOTONE":
                if len(fields) != 4 or fields[3] not in {"0", "1"}:
                    raise GateFailure("IMPLEMENTATION_INVALID", "malformed scalar MONOTONE")
                layer = _tsv_uint(fields[2], "scalar monotone layer")
                if layer in case["monotone"]:
                    raise GateFailure("IMPLEMENTATION_INVALID", "duplicate scalar MONOTONE")
                case["monotone"][layer] = _tsv_bool(fields[3], "scalar monotone value")
            elif kind == "END_CASE":
                if len(fields) != 2 or case_id in ended_cases:
                    raise GateFailure("IMPLEMENTATION_INVALID", "duplicate or malformed END_CASE")
                if len(case["support"]) != case["support_count"]:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar support count mismatch")
                expected_cardinalities = set(range(1, case["maximum_cardinality"] + 1))
                if set(case["solutions"]) != expected_cardinalities:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar solution inventory mismatch")
                effective_maximum = min(case["maximum_cardinality"], case["support_count"])
                if set(case["monotone"]) != set(range(1, effective_maximum + 1)):
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar monotonicity inventory mismatch")
                prior_effective = 0
                for cardinality in range(1, case["maximum_cardinality"] + 1):
                    solution = case["solutions"][cardinality]
                    clusters = solution["clusters"]
                    if len(clusters) != solution["cluster_count"] or not solution.pop("predecessor_seen"):
                        raise GateFailure("IMPLEMENTATION_INVALID", "incomplete scalar solution trace")
                    if clusters[0]["begin"] != 0 or clusters[-1]["end"] != case["support_count"]:
                        raise GateFailure("IMPLEMENTATION_INVALID", "scalar partition boundary mismatch")
                    if any(
                        left["end"] != right["begin"] or left["begin"] >= left["end"]
                        for left, right in zip(clusters, clusters[1:])
                    ) or clusters[-1]["begin"] >= clusters[-1]["end"]:
                        raise GateFailure("IMPLEMENTATION_INVALID", "scalar partition is not contiguous")
                    if solution["effective_cardinality"] < prior_effective:
                        raise GateFailure("IMPLEMENTATION_INVALID", "scalar effective cardinality decreased")
                    prior_effective = solution["effective_cardinality"]
                diagnostics = case["diagnostics"]
                if sum(solution["comparison_count"] for solution in case["solutions"].values()) != diagnostics["exact_comparisons"]:
                    raise GateFailure("IMPLEMENTATION_INVALID", "per-K comparisons do not sum to curve total")
                if sum(solution["exact_tie_count"] for solution in case["solutions"].values()) != diagnostics["exact_ties"]:
                    raise GateFailure("IMPLEMENTATION_INVALID", "per-K ties do not sum to curve total")
                expected_replays = effective_maximum
                if diagnostics["exact_replay_checks"] != expected_replays:
                    raise GateFailure("IMPLEMENTATION_INVALID", "scalar exact replay count mismatch")
                ended_cases.add(case_id)
            else:
                raise GateFailure("IMPLEMENTATION_INVALID", f"unknown scalar output record {kind}")
        if not saw_end or declared_case_count != len(parsed) or ended_cases != set(parsed):
            raise GateFailure("IMPLEMENTATION_INVALID", "scalar terminal inventory mismatch")
        return parsed
    except GateFailure:
        raise
    except (
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        UnicodeError,
        OSError,
    ) as error:
        raise GateFailure("IMPLEMENTATION_INVALID", f"malformed scalar native output: {error}") from error


def _reference_solution_json(solution: reference.ExactScalarSolution) -> dict[str, Any]:
    return {
        "requested_cardinality": solution.requested_cardinality,
        "effective_cardinality": solution.effective_cardinality,
        "objective": _exact_value(solution.objective_grid, -298),
        "clusters": [
            {
                "begin": cluster.begin,
                "end": cluster.end,
                "mean": _exact_value(Fraction(cluster.sum_n, cluster.weight), -149),
                "binary32_bits": _hex32(
                    reference.round_grid_mean_to_float32_bits(cluster.sum_n, cluster.weight)
                ),
                "binary64_bits": _hex64(
                    reference.round_grid_mean_to_float64_bits(cluster.sum_n, cluster.weight)
                ),
            }
            for cluster in solution.clusters
        ],
    }


def _validate_scalar_case(
    case: ScalarCase, optimized: Mapping[str, Any]
) -> tuple[dict[str, Any], reference.ExactScalarCurve]:
    independent = reference.exact_scalar_curve_reference(
        case.value_bits,
        case.maximum_cardinality,
        case.weights,
        case.vector_ids,
    )
    expected_support = [
        {
            "support_id": index,
            "grid_integer": str(value),
            "weight": str(weight),
            "lowest_vector_id": source_id,
        }
        for index, (value, weight, source_id) in enumerate(
            zip(
                independent.support,
                independent.support_weights,
                independent.support_lowest_ids,
            )
        )
    ]
    if list(optimized["support"]) != expected_support:
        raise GateFailure("IMPLEMENTATION_INVALID", f"scalar support mismatch case {case.case_id}")

    solution_records: list[dict[str, Any]] = []
    for cardinality in range(1, case.maximum_cardinality + 1):
        actual = dict(optimized["solutions"][cardinality])
        comparison_count = int(actual.pop("comparison_count"))
        exact_tie_count = int(actual.pop("exact_tie_count"))
        actual.pop("cluster_count")
        actual.pop("predecessor_indices")
        actual["clusters"] = [
            {key: value for key, value in cluster.items() if key != "cluster_id"}
            for cluster in actual["clusters"]
        ]
        expected = _reference_solution_json(independent.at(cardinality))
        if actual != expected:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"scalar exact parity mismatch case={case.case_id} K={cardinality}",
            )
        solution_records.append(
            {
                "independent": expected,
                "optimized": actual,
                "parity": True,
                "comparison_count": str(comparison_count),
                "exact_tie_count": str(exact_tie_count),
            }
        )
    if not all(optimized["monotone"].values()):
        raise GateFailure("IMPLEMENTATION_INVALID", f"nonmonotone predecessor case {case.case_id}")
    return (
        {
            "case_id": case.case_id,
            "suite": case.suite,
            "suite_index": case.suite_index,
            "value_bits": [_hex32(value) for value in case.value_bits],
            "weights": [str(value) for value in case.weights],
            "vector_ids": list(case.vector_ids),
            "maximum_cardinality": case.maximum_cardinality,
            "support": expected_support,
            "solutions": solution_records,
            "optimized_diagnostics": dict(optimized["diagnostics"]),
            "predecessor_monotone": [
                optimized["monotone"][layer]
                for layer in sorted(optimized["monotone"])
            ],
        },
        independent,
    )


def _common(
    *,
    status: str,
    implementation_commit: str,
    execution_commit: str,
    thread_environment: Mapping[str, str],
    input_ledger: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return artifacts.common_artifact_fields(
        status=status,
        implementation_commit=implementation_commit,
        execution_commit=execution_commit,
        command=sys.argv,
        thread_environment=thread_environment,
        input_ledger=input_ledger,
        output_ledger=(),
    )


def _write_build_manifest(
    output_dir: Path,
    *,
    common: Mapping[str, Any],
    runtime_numeric: Mapping[str, Any],
    numpy_version: str,
) -> None:
    source_files = tuple(REPO_ROOT / path for path in SOURCE_PATHS)
    build_inputs = (COMPILE_COMMANDS, NATIVE_BINARY, *source_files)
    for path in build_inputs:
        artifacts.guard_synthetic_read_path(
            path,
            repo_root=REPO_ROOT,
            allowed_files=build_inputs,
            extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
            require_allowlist_match=True,
        )
    for relative in SOURCE_PATHS:
        artifacts.git_blob_oid(
            REPO_ROOT,
            relative,
            commit=str(common["execution_commit"]),
        )
    compile_commands = artifacts.load_and_validate_compile_commands(
        COMPILE_COMMANDS, repo_root=REPO_ROOT
    )
    manifest = artifacts.make_build_runtime_manifest(
        common,
        compile_commands=compile_commands,
        runtime_numeric=runtime_numeric,
        native_binary_path=NATIVE_BINARY,
        native_binary_ledger_path="build/a4_1s/a4_1s_native",
        source_paths=source_files,
        repo_root=REPO_ROOT,
        numpy_version=numpy_version,
        extra_fields={
            "compile_command_count": len(compile_commands),
            "build_command": [
                "cmake",
                "--build",
                "build/a4_1s",
                "--target",
                "a4_1s_native",
                "-j1",
            ],
        },
    )
    artifacts.write_canonical_json(output_dir / "build_manifest.json", manifest)


def _load_numpy() -> Any:
    try:
        import numpy as np
    except ImportError as error:
        raise GateFailure("IMPLEMENTATION_INVALID", "NumPy is unavailable") from error
    return np


def _run_compatibility_tests() -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "tests/test_evaluate_arbitrary_cardinality.py",
        "tests/test_a4_1s_reference.py",
    ]
    process = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"A4-0/A4-1S compatibility tests failed: {process.stdout}{process.stderr}",
        )
    return {
        "command": command,
        "a4_0_test_count": 7,
        "a4_1s_nonrandom_test_count": 15,
        "returncode": process.returncode,
        "passed": True,
    }


def _preflight(
    args: argparse.Namespace,
) -> tuple[
    Path,
    str,
    dict[str, str],
    list[dict[str, Any]],
    dict[str, Any],
    int,
]:
    if args.threads != 1:
        raise GateFailure("ARTIFACT_INVALID", "--threads must equal one")
    expected_input_arg = INPUT_SPEC_PATH.relative_to(REPO_ROOT).as_posix()
    expected_hypotheses_arg = HYPOTHESES_PATH.relative_to(REPO_ROOT).as_posix()
    if args.input_spec != expected_input_arg:
        raise GateFailure("ARTIFACT_INVALID", "input-spec path identity mismatch")
    if args.hypotheses != expected_hypotheses_arg:
        raise GateFailure("ARTIFACT_INVALID", "hypotheses path identity mismatch")
    try:
        for argument, expected in (
            (args.input_spec, INPUT_SPEC_PATH),
            (args.hypotheses, HYPOTHESES_PATH),
        ):
            observed = artifacts.guard_synthetic_read_path(
                argument,
                repo_root=REPO_ROOT,
                allowed_files=(expected,),
                extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
                require_allowlist_match=True,
            )
            if observed != expected:
                raise artifacts.ArtifactContractError(
                    "contract argument did not resolve to its frozen literal path"
                )
    except (artifacts.ArtifactContractError, OSError, RuntimeError) as error:
        raise GateFailure(
            "ARTIFACT_INVALID", f"contract argument path is forbidden: {error}"
        ) from error
    expected_output = Path(
        "/tmp/saq-attempt4-a4-1s-parity"
        if args.mode == "parity"
        else "/tmp/saq-attempt4-a4-1s-cost-projection"
    )
    if args.output_dir != expected_output.as_posix():
        raise GateFailure("ARTIFACT_INVALID", "mode-specific output path identity mismatch")
    thread_environment = artifacts.require_frozen_thread_environment()
    output_dir = _prepare_output_directory(Path(args.output_dir))
    execution_commit = artifacts.require_clean_execution_commit(REPO_ROOT)
    _bind_frozen_contract_blobs(execution_commit)
    allowed = (INPUT_SPEC_PATH, HYPOTHESES_PATH)
    input_spec = _read_json_guarded(INPUT_SPEC_PATH, allowed=allowed)
    hypotheses = _read_json_guarded(HYPOTHESES_PATH, allowed=allowed)
    _validate_contracts(input_spec, hypotheses)
    ledger = _input_ledger()
    try:
        artifacts.guard_synthetic_read_path(
            NATIVE_BINARY,
            repo_root=REPO_ROOT,
            allowed_files=(NATIVE_BINARY,),
            extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
            require_allowlist_match=True,
        )
    except artifacts.ArtifactContractError as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", f"native binary path is invalid: {error}"
        ) from error
    if not NATIVE_BINARY.is_file():
        raise GateFailure("IMPLEMENTATION_INVALID", "native binary is missing")
    runtime = _runtime_numeric_manifest()
    # This is deliberately conservative: the contracts are decoded one at a
    # time and file hashing is streamed, but charging all guarded preflight
    # inputs as simultaneous transient frames gives a deterministic upper
    # bound without depending on CPython allocator behavior.  The 13x factor
    # covers raw bytes, a worst-case UCS-4 decode, decoded logical payload,
    # and a canonical reserialization frame.
    preflight_files = (
        INPUT_SPEC_PATH,
        HYPOTHESES_PATH,
        PROTOCOL_PATH,
        NATIVE_BINARY,
    )
    try:
        preflight_transient_bound = 13 * sum(
            path.stat().st_size for path in preflight_files
        )
    except OSError as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"cannot account preflight input payloads: {error}",
        ) from error
    preflight_transient_bound += 13 * len(
        artifacts.canonical_json_bytes(runtime)
    )
    preflight_owned_buffer_high_water = _deterministic_owned_buffer_bytes(
        input_spec,
        hypotheses,
        ledger,
        runtime,
        thread_environment,
        execution_commit,
        output_dir.as_posix(),
    ) + preflight_transient_bound
    return (
        output_dir,
        execution_commit,
        thread_environment,
        ledger,
        runtime,
        preflight_owned_buffer_high_water,
    )


def _run_parity(args: argparse.Namespace) -> str:
    (
        output_dir,
        execution_commit,
        thread_environment,
        ledger,
        runtime,
        _preflight_owned_buffer_high_water,
    ) = _preflight(args)
    np = _load_numpy()
    common = _common(
        status="PASS_PARITY",
        implementation_commit=execution_commit,
        execution_commit=execution_commit,
        thread_environment=thread_environment,
        input_ledger=ledger,
    )
    _write_build_manifest(
        output_dir,
        common=common,
        runtime_numeric=runtime,
        numpy_version=np.__version__,
    )
    compatibility = _run_compatibility_tests()

    cases = _generate_scalar_cases(np)
    scalar_input = output_dir / ".scalar_suite_input.bin"
    scalar_output = output_dir / ".scalar_suite_output.tsv"
    _write_scalar_input(scalar_input, cases)
    _run_native(("scalar-suite", str(scalar_input), str(scalar_output)))
    optimized = _parse_scalar_output(scalar_output)
    if set(optimized) != {case.case_id for case in cases}:
        raise GateFailure("IMPLEMENTATION_INVALID", "scalar native case inventory mismatch")
    scalar_records: list[dict[str, Any]] = []
    tiny_curves: list[reference.ExactScalarCurve] = []
    for case in cases:
        record, curve = _validate_scalar_case(case, optimized[case.case_id])
        scalar_records.append(record)
        if case.suite == "exhaustive_tiny":
            tiny_curves.append(curve)
    if len(tiny_curves) != 780:
        raise AssertionError("tiny curve inventory mismatch")
    scalar_input.unlink()
    scalar_output.unlink()

    scalar_artifact = artifacts.add_artifact_body(
        common,
        {
            "artifact_kind": "scalar_exact_parity",
            "rng": {
                "algorithm": "PCG64",
                "seed": SEED,
                "stream_scope": "scalar_256_only",
            },
            "suite_counts": {
                "bit_pattern": 8,
                "exhaustive_tiny": 780,
                "pcg64_256": 256,
                "total": len(scalar_records),
            },
            "cases": scalar_records,
            "all_exact_equal": True,
            "all_replays_equal": True,
            "all_predecessors_monotone": True,
        },
    )
    artifacts.write_canonical_json(
        output_dir / "scalar_exact_parity.json", scalar_artifact
    )

    # Representation and block suites are compiled into separate native
    # subcommands.  Keeping their runners in named helpers makes it impossible
    # to silently omit either checkpoint from the parity summary.
    representation_body = _run_representation_parity(output_dir, tiny_curves)
    representation_artifact = artifacts.add_artifact_body(common, representation_body)
    artifacts.write_canonical_json(
        output_dir / "representation_parity.json", representation_artifact
    )

    block_body = _run_block_parity(output_dir, np, representation_body)
    block_artifact = artifacts.add_artifact_body(common, block_body)
    artifacts.write_canonical_json(output_dir / "block_vq_parity.json", block_artifact)

    precedence_fixture = _status_precedence_fixture()

    summary = artifacts.add_artifact_body(
        common,
        {
            "artifact_kind": "parity_summary",
            "a4_0_test_count": 7,
            "a4_0_tests_passed": True,
            "compatibility_tests": compatibility,
            "block_case_count": 64,
            "block_microfixture_count": 5,
            "representation_passed": True,
            "scalar_case_count": len(cases),
            "status_precedence_checked": precedence_fixture["passed"],
            "status_precedence_fixture": precedence_fixture,
            "outcome": "PASS_PARITY",
        },
    )
    artifacts.write_canonical_json(output_dir / "parity_summary.json", summary)

    index_entries = [
        artifacts.make_artifact_index_entry(
            output_dir / filename,
            ledger_path=filename,
            producer_execution_commit=execution_commit,
        )
        for filename in PARITY_FILENAMES
    ]
    index = artifacts.make_artifact_index(
        common,
        index_entries,
        index_ledger_path="parity_artifact_index.json",
    )
    artifacts.write_canonical_json(output_dir / "parity_artifact_index.json", index)
    return "PASS_PARITY"


_REPRESENTATION_INTEGER_UNIVERSE = (-2.0, -1.0, 0.0, 1.0, 2.0)
_BINARY32_POSITIVE_INFINITY = 0x7F800000
_BINARY64_POSITIVE_INFINITY = 0x7FF0000000000000


def _representation_support_size_winners() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for capacity in (16, 256):
        curves = {
            support_size: reference.exact_scalar_curve_reference(
                [
                    reference.float32_bits(value)
                    for value in _REPRESENTATION_INTEGER_UNIVERSE[:support_size]
                ],
                capacity,
            )
            for support_size in range(1, 5)
        }
        for dyadic_only in (False, True):  # arbitrary before dyadic
            allowed = (
                tuple(1 << bit for bit in range(capacity.bit_length()))
                if dyadic_only
                else tuple(range(1, capacity + 1))
            )
            exhaustive_count = sum(
                1 for first in allowed for second in allowed if first * second <= capacity
            )
            optimized_count = len(allowed)
            for first_support_size in range(1, 5):
                for second_support_size in range(1, 5):
                    allocation = reference.exact_product_allocation_reference(
                        curves[first_support_size],
                        curves[second_support_size],
                        capacity,
                        dyadic_only=dyadic_only,
                    )
                    first, second = allocation.cardinalities
                    records.append(
                        {
                            "capacity": capacity,
                            "cardinality_kind": "dyadic" if dyadic_only else "arbitrary",
                            "exhaustive_valid_tuple_count": str(exhaustive_count),
                            "first_support_size": first_support_size,
                            "objective": _exact_value(allocation.objective_grid, -298),
                            "optimized_candidate_evaluation_count": str(optimized_count),
                            "reachable": (
                                first <= first_support_size
                                and second <= second_support_size
                            ),
                            "second_support_size": second_support_size,
                            "selected_cardinalities": [first, second],
                            "used_states": allocation.used_states,
                        }
                    )
    if len(records) != 64:
        raise AssertionError("support-size winner inventory is not 64")
    return records


def _representation_mixed_radix_case() -> dict[str, Any]:
    radices = (3, 5)
    entries = []
    for address in range(16):
        if address < 15:
            labels = reference.mixed_radix_decode(address, radices)
            entries.append(
                {
                    "address": address,
                    "decoded_labels": list(labels),
                    "encoded_address": reference.mixed_radix_encode(labels, radices),
                    "labels": list(labels),
                    "valid": True,
                }
            )
        else:
            entries.append(
                {
                    "address": address,
                    "decoded_labels": None,
                    "encoded_address": None,
                    "labels": None,
                    "valid": False,
                }
            )
    return {
        "entries": entries,
        "nominal_capacity": 16,
        "radices": list(radices),
        "valid_tuple_count": 15,
    }


def _representation_matched_packing_cases() -> list[dict[str, Any]]:
    result = []
    for word_bits, labels in (
        (4, tuple(index % 16 for index in range(64))),
        (8, tuple((3 * index + 1) % 256 for index in range(64))),
    ):
        payload = reference.pack_matched_labels(labels, word_bits)
        result.append(
            {
                "labels": list(labels),
                "payload_bytes": len(payload),
                "payload_hex": payload.hex(),
                "roundtrip_labels": list(
                    reference.unpack_matched_labels(payload, word_bits)
                ),
                "word_bits": word_bits,
            }
        )
    return result


def _representation_global_packing_case(paid_bytes: int) -> dict[str, Any]:
    widths = [0] * 128
    labels = [0] * 128
    if paid_bytes == 32:
        prefix_widths = (0, 1, 3, 4, 0, 7, 2)
        prefix_labels = (0, 1, 5, 9, 0, 85, 3)
    elif paid_bytes == 64:
        prefix_widths = (8, 0, 5, 3, 1, 7, 2, 4)
        prefix_labels = (255, 0, 17, 5, 1, 100, 3, 9)
    else:
        raise ValueError("unexpected global paid-byte fixture")
    widths[: len(prefix_widths)] = prefix_widths
    labels[: len(prefix_labels)] = prefix_labels
    offsets = []
    offset = 0
    for width in widths:
        offsets.append(offset)
        offset += width
    payload = reference.pack_global_labels(labels, widths, paid_bytes)
    zero_tail = all(
        payload[bit // 8] & (1 << (bit % 8)) == 0
        for bit in range(offset, paid_bytes * 8)
    )
    return {
        "bit_offsets": offsets,
        "bit_widths": widths,
        "labels": labels,
        "paid_payload_bytes": paid_bytes,
        "payload_hex": payload.hex(),
        "roundtrip_labels": list(reference.unpack_global_labels(payload, widths)),
        "used_bits": offset,
        "zero_tail": zero_tail,
    }


def _lookup_entry(pre_narrow: int, stored: int, *, valid: bool) -> dict[str, Any]:
    return {
        "pre_narrow_binary64_bits": _hex64(pre_narrow),
        "stored_binary32_bits": _hex32(stored),
        "valid": valid,
    }


def _representation_matched_lookup_cases() -> list[dict[str, Any]]:
    fixtures = (
        (
            16,
            (3, 5),
            (-1.0, 0.0, 2.0),
            (-2.0, -0.5, 1.0, 3.0, 4.0),
            (0.5, -0.75),
        ),
        (
            256,
            (13, 19),
            tuple(float(value) for value in range(-6, 7)),
            tuple(float(value) for value in range(-9, 10)),
            (0.25, -0.5),
        ),
    )
    cases = []
    for capacity, radices, axis0, axis1, query in fixtures:
        axis0_bits = [reference.float32_bits(value) for value in axis0]
        axis1_bits = [reference.float32_bits(value) for value in axis1]
        query_bits = [reference.float32_bits(value) for value in query]
        reconstructions = [
            [left, right] for right in axis1_bits for left in axis0_bits
        ]
        entries = []
        for address in range(capacity):
            if address < len(reconstructions):
                pre_narrow, stored = reference.point_lookup_entry_bits(
                    query_bits, reconstructions[address]
                )
                entry = _lookup_entry(pre_narrow, stored, valid=True)
            else:
                entry = _lookup_entry(
                    _BINARY64_POSITIVE_INFINITY,
                    _BINARY32_POSITIVE_INFINITY,
                    valid=False,
                )
            entries.append({"address": address, **entry})
        cases.append(
            {
                "axis0_centroid_bits": [_hex32(value) for value in axis0_bits],
                "axis1_centroid_bits": [_hex32(value) for value in axis1_bits],
                "capacity": capacity,
                "entries": entries,
                "query_bits": [_hex32(value) for value in query_bits],
                "radices": list(radices),
                "reconstruction_bits": [
                    [_hex32(value[0]), _hex32(value[1])]
                    for value in reconstructions
                ],
                "valid_states": len(reconstructions),
            }
        )
    return cases


def _representation_global_lookup_case() -> dict[str, Any]:
    packing = _representation_global_packing_case(32)
    widths = packing["bit_widths"]
    palette = [
        reference.float32_bits(value)
        for value in (
            -4.0,
            -3.0,
            -2.0,
            -1.0,
            -0.5,
            -0.25,
            0.0,
            0.25,
            0.5,
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
            6.0,
            8.0,
        )
    ]
    query = [palette[(3 * coordinate) % len(palette)] for coordinate in range(128)]
    centroids = [
        [
            palette[(coordinate + 3 * label) % len(palette)]
            for label in range(1 << width)
        ]
        for coordinate, width in enumerate(widths)
    ]
    offsets = [0]
    entries = []
    for coordinate, (query_bits, table) in enumerate(zip(query, centroids)):
        for label, centroid_bits in enumerate(table):
            pre_narrow, stored = reference.scalar_lookup_entry_bits(
                query_bits, centroid_bits
            )
            entries.append(
                {
                    "coordinate": coordinate,
                    "flat_index": len(entries),
                    "label": label,
                    **_lookup_entry(pre_narrow, stored, valid=True),
                }
            )
        offsets.append(len(entries))
    return {
        "bit_widths": widths,
        "centroid_bits_by_coordinate": [
            [_hex32(value) for value in table] for table in centroids
        ],
        "coordinate_offsets": offsets,
        "entries": entries,
        "query_coordinate_bits": [_hex32(value) for value in query],
    }


def _strict_json_equal(expected: Any, observed: Any) -> bool:
    """Compare decoded JSON values without Python's bool/int/float coercions."""

    if type(expected) is not type(observed):
        return False
    if isinstance(expected, dict):
        return set(expected) == set(observed) and all(
            isinstance(key, str)
            and _strict_json_equal(expected[key], observed[key])
            for key in expected
        )
    if isinstance(expected, list):
        return len(expected) == len(observed) and all(
            _strict_json_equal(left, right)
            for left, right in zip(expected, observed)
        )
    return expected == observed


def _paired_fixture(independent: Any, optimized: Any) -> dict[str, Any]:
    parity = _strict_json_equal(independent, optimized)
    return {
        "independent": independent,
        "optimized": optimized,
        "parity": parity,
    }


def _paired_lookup_case(
    independent: Mapping[str, Any], optimized: Mapping[str, Any]
) -> dict[str, Any]:
    independent_metadata = {key: value for key, value in independent.items() if key != "entries"}
    optimized_metadata = {key: value for key, value in optimized.items() if key != "entries"}
    if not _strict_json_equal(independent_metadata, optimized_metadata):
        raise GateFailure("IMPLEMENTATION_INVALID", "lookup fixture metadata mismatch")
    independent_entries = independent["entries"]
    optimized_entries = optimized["entries"]
    if len(independent_entries) != len(optimized_entries):
        raise GateFailure("IMPLEMENTATION_INVALID", "lookup fixture entry count mismatch")
    paired_entries = [
        _paired_fixture(expected, actual)
        for expected, actual in zip(independent_entries, optimized_entries)
    ]
    return {
        **independent_metadata,
        "independent": independent,
        "optimized": optimized,
        "entries": paired_entries,
        "parity": (
            _strict_json_equal(independent_metadata, optimized_metadata)
            and all(entry["parity"] for entry in paired_entries)
        ),
    }


def _validate_block_selected_distinctness(case: dict[str, Any]) -> None:
    """Apply the frozen binary32-distinctness rule only to the winner.

    A nonselected Lloyd start may converge with colliding serialized centers;
    Section 2.6 gates the codebook selected by best-of-eight.  Conversely, a
    valid BEST must be fully distinct, and the registered collision control
    must identify an actually colliding selected start.
    """

    capacity = int(case["capacity"])
    starts = case["starts"]
    valid_best = case["best"].get("control_valid") is True
    collision_control = case.get("failure") == "SERIALIZED_CENTER_COLLISION"
    if not valid_best and not collision_control:
        # Other registered block-control failures may intentionally carry a
        # nonfinite or incomplete trace for which best-of-eight is undefined.
        # Their CONTROL_INVALID status must not be rewritten as an
        # implementation defect by the selected-codebook-only rule.
        case["validation_best_start_sse_comparison_count"] = 0
        return
    ordered_start_ids = sorted(starts)
    if not ordered_start_ids:
        raise GateFailure("IMPLEMENTATION_INVALID", "block start inventory is empty")
    best_start_id = ordered_start_ids[0]
    best_sse = reference.bits_to_float64(
        int(starts[best_start_id]["final_sse_bits"], 16)
    )
    if not math.isfinite(best_sse) or best_sse < 0.0:
        raise GateFailure("IMPLEMENTATION_INVALID", "block best replay SSE is invalid")
    comparison_count = 0
    for candidate_start_id in ordered_start_ids[1:]:
        candidate_sse = reference.bits_to_float64(
            int(starts[candidate_start_id]["final_sse_bits"], 16)
        )
        if not math.isfinite(candidate_sse) or candidate_sse < 0.0:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "block best replay SSE is invalid"
            )
        comparison_count += 1
        if candidate_sse < best_sse:
            best_start_id = candidate_start_id
            best_sse = candidate_sse
    case["validation_best_start_sse_comparison_count"] = comparison_count

    if valid_best:
        declared_start_id = int(case["best"]["start_id"])
        if declared_start_id != best_start_id:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "block BEST tie/order mismatch"
            )
        selected = starts[declared_start_id]
        if int(selected["distinct_serialized_center_count"]) != capacity:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "valid block BEST selected colliding centers",
            )
    elif collision_control:
        failed_start_id = int(case["failed_start_id"])
        if failed_start_id != best_start_id:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "block collision failure does not identify the winning start",
            )
        for start_id in ordered_start_ids:
            start = starts[start_id]
            expected_failure = (
                "SERIALIZED_CENTER_COLLISION"
                if start_id == best_start_id
                else "NONE"
            )
            if not start["converged"] or start["failure"] != expected_failure:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    "block collision control has an invalid Lloyd-start state",
                )
        failed = starts[failed_start_id]
        if (
            int(failed["final_assignment_count"]) != int(case["point_count"])
            or int(failed["final_center_count"]) != capacity
            or int(failed["serialized_center_count"]) != capacity
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "block collision winner has an invalid completed shape",
            )
        if int(failed["distinct_serialized_center_count"]) >= capacity:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "block collision failure has no selected-center collision",
            )


def _parse_native_smoke(
    path: Path,
) -> tuple[
    dict[tuple[str, str, str, str], tuple[str, str]],
    dict[str, list[str]],
]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise GateFailure("IMPLEMENTATION_INVALID", f"cannot read native smoke: {error}") from error
    if len(lines) != 23 or lines[0] != "A4S_NATIVE_SMOKE_V1" or lines[-1] != "END":
        raise GateFailure("IMPLEMENTATION_INVALID", "native smoke framing/inventory mismatch")

    patterns = (
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
    for index, bits in enumerate(patterns, start=1):
        fields = lines[index].split("\t")
        if len(fields) != 5 or fields[0] != "ROUNDTRIP":
            raise GateFailure("IMPLEMENTATION_INVALID", "native roundtrip record schema mismatch")
        grid = reference.decode_float32_grid(bits)
        expected = (
            "ROUNDTRIP",
            _hex32(bits),
            str(grid),
            _hex32(reference.round_grid_mean_to_float32_bits(grid, 1)),
            _hex64(reference.round_grid_mean_to_float64_bits(grid, 1)),
        )
        if tuple(fields) != expected:
            raise GateFailure("IMPLEMENTATION_INVALID", "native roundtrip fixture mismatch")

    expected_rounding = {
        ("MIDPOINT", "1", "2", "-149"): ("0x00000000", "0x3690000000000000"),
        ("MIDPOINT", "3", "2", "-149"): ("0x00000002", "0x36a8000000000000"),
        ("MIDPOINT", "-1", "2", "-149"): ("0x80000000", "0xb690000000000000"),
        ("MIDPOINT", "-3", "2", "-149"): ("0x80000002", "0xb6a8000000000000"),
        ("RATIONAL", "1", "3", "0"): ("0x3eaaaaab", "0x3fd5555555555555"),
        ("RATIONAL", "-1", "3", "0"): ("0xbeaaaaab", "0xbfd5555555555555"),
    }
    observed_rounding: dict[tuple[str, str, str, str], tuple[str, str]] = {}
    for expected_key, line in zip(expected_rounding, lines[11:17]):
        fields = line.split("\t")
        if len(fields) != 6 or fields[0] not in {"MIDPOINT", "RATIONAL"}:
            raise GateFailure("IMPLEMENTATION_INVALID", "native rounding record schema mismatch")
        _tsv_rational(fields[1], fields[2], "native rounding", signed=True)
        _tsv_sint(fields[3], "native rounding exponent")
        _tsv_bits(fields[4], 32, "native rounding binary32")
        _tsv_bits(fields[5], 64, "native rounding binary64")
        key = tuple(fields[:4])
        if key != expected_key or key in observed_rounding:
            raise GateFailure("IMPLEMENTATION_INVALID", "duplicate native rounding fixture")
        observed_rounding[key] = (fields[4], fields[5])
    if observed_rounding != expected_rounding:
        raise GateFailure("IMPLEMENTATION_INVALID", "direct rational rounding fixture mismatch")

    expected_controls = {
        "SCALAR_K_GT_H": ["4", "2", "2", "3"],
        "BLOCK_ASSIGNMENT_TIE": ["0", "0x3ff0000000000000", "2", "1"],
        "BLOCK_FARTHEST_FALLBACK": ["3", "7", "1"],
        "BLOCK_VALID_EIGHT_STARTS": ["8", "0"],
        "BLOCK_NONFINITE_CONTROL": ["8", "0"],
    }
    observed_controls: dict[str, list[str]] = {}
    for expected_kind, line in zip(expected_controls, lines[17:-1]):
        fields = line.split("\t")
        if (
            fields[0] != expected_kind
            or fields[0] not in expected_controls
            or fields[0] in observed_controls
        ):
            raise GateFailure("IMPLEMENTATION_INVALID", "native control-smoke inventory mismatch")
        if fields[1:] != expected_controls[fields[0]]:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", f"native control-smoke mismatch: {fields[0]}"
            )
        observed_controls[fields[0]] = fields[1:]
    if observed_controls != expected_controls:
        raise GateFailure("IMPLEMENTATION_INVALID", "native control-smoke inventory mismatch")
    return observed_rounding, observed_controls


def _tiny_curve_inventory_sha256(
    tiny_curves: Sequence[reference.ExactScalarCurve],
) -> str:
    """Bind all 780 weighted tiny curves independently of native enumeration."""

    grid_to_bits = {
        reference.decode_float32_grid(_int_grid_bits(value)): _hex32(
            _int_grid_bits(value)
        )
        for value in (-2, -1, 0, 1, 2)
    }
    digest = hashlib.sha256()
    for case_id, curve in enumerate(tiny_curves):
        if curve.support_lowest_ids != tuple(range(len(curve.support))):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"tiny curve {case_id} has unexpected vector-id provenance",
            )
        try:
            samples = [
                {
                    "binary32_bits": grid_to_bits[grid],
                    "vector_id": vector_id,
                    "weight": str(weight),
                }
                for grid, weight, vector_id in zip(
                    curve.support,
                    curve.support_weights,
                    curve.support_lowest_ids,
                )
            ]
        except KeyError as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"tiny curve {case_id} escaped the frozen integer universe",
            ) from error
        digest.update(
            artifacts.canonical_json_bytes({"case_id": case_id, "samples": samples})
            + b"\n"
        )
    return digest.hexdigest()


def _same_h_different_weight_fixture() -> dict[str, Any]:
    """Independent Python construction for the native anti-shortcut fixture."""

    bits = tuple(_int_grid_bits(value) for value in (-2, -1, 0))
    weights_a = (1, 1, 1)
    weights_b = (1, 1, 2)
    mate_weights = (3, 3, 3)
    curve_a = reference.exact_scalar_curve_reference(bits, 4, weights_a)
    curve_b = reference.exact_scalar_curve_reference(bits, 4, weights_b)
    mate = reference.exact_scalar_curve_reference(bits, 4, mate_weights)

    def parity_record(
        curve: reference.ExactScalarCurve,
        *,
        dyadic_only: bool,
    ) -> dict[str, Any]:
        allocation = reference.exact_product_allocation_reference(
            curve, mate, 4, dyadic_only=dyadic_only
        )
        objective = _exact_value(allocation.objective_grid, -298)
        return {
            "independent_cardinalities": list(allocation.cardinalities),
            "independent_feasible_tuple_evaluation_count": (
                "6" if dyadic_only else "8"
            ),
            "independent_objective": objective,
            "optimized_candidate_evaluation_count": (
                "3" if dyadic_only else "4"
            ),
            "optimized_cardinalities": list(allocation.cardinalities),
            "optimized_objective": objective,
            "parity": True,
        }

    arms = []
    for dyadic_only in (False, True):
        arms.append(
            {
                "cardinality_kind": "dyadic" if dyadic_only else "arbitrary",
                "curve_a": parity_record(curve_a, dyadic_only=dyadic_only),
                "curve_b": parity_record(curve_b, dyadic_only=dyadic_only),
                "different_weight_sensitive_winners": True,
            }
        )
    return {
        "arms": arms,
        "capacity": 4,
        "common_support_binary32_bits": [_hex32(value) for value in bits],
        "curve_a_k1_objective": _exact_value(curve_a.at(1).objective_grid, -298),
        "curve_a_weights": list(weights_a),
        "curve_b_k1_objective": _exact_value(curve_b.at(1).objective_grid, -298),
        "curve_b_weights": list(weights_b),
        "mate_weights": list(mate_weights),
        "same_support_size": 3,
    }


def _run_representation_parity(
    output_dir: Path,
    tiny_curves: Sequence[reference.ExactScalarCurve],
) -> dict[str, Any]:
    if len(tiny_curves) != 780:
        raise GateFailure("IMPLEMENTATION_INVALID", "representation curve inventory mismatch")
    # This analytical support-size shortcut is retained only as an independent
    # canonical-record order fingerprint.  It is not the allocation-correctness
    # authority: the compiled structurally independent exhaustive enumerator
    # visits every feasible tuple for every actual weighted curve pair.
    allocation_count = len(tiny_curves) * len(tiny_curves) * 2 * 2
    allocation_digest = hashlib.sha256()
    winner_cache: dict[tuple[int, int, int, bool], reference.ProductAllocation] = {}

    def extended_tiny_winner(
        first: reference.ExactScalarCurve,
        second: reference.ExactScalarCurve,
        capacity: int,
        dyadic_only: bool,
    ) -> reference.ProductAllocation:
        # Every tiny curve reaches exact zero at its distinct-support count.
        # Reusing that final curve point for larger nominal K leaves only the
        # frozen maximum-product/lexicographic tie.  Cache the sixteen support
        # shape pairs; no floating surrogate chooses a decision.
        key = (len(first.support), len(second.support), capacity, dyadic_only)
        cached = winner_cache.get(key)
        if cached is not None:
            return cached
        if dyadic_only:
            allowed = tuple(1 << bit for bit in range(capacity.bit_length()))
        else:
            allowed = tuple(range(1, capacity + 1))
        feasible = [
            (-(first_k * second_k), (first_k, second_k))
            for first_k in allowed
            for second_k in allowed
            if first_k >= len(first.support)
            and second_k >= len(second.support)
            and first_k * second_k <= capacity
        ]
        if not feasible:
            raise AssertionError("tiny zero-SSE allocation unexpectedly infeasible")
        negative_product, cardinalities = min(feasible)
        cached = reference.ProductAllocation(cardinalities, -negative_product, Fraction(0))
        winner_cache[key] = cached
        return cached

    for capacity in (16, 256):
        for dyadic_only in (False, True):
            for first in tiny_curves:
                for second in tiny_curves:
                    allocation = extended_tiny_winner(
                        first, second, capacity, dyadic_only
                    )
                    record = {
                        "capacity": capacity,
                        "cardinalities": list(allocation.cardinalities),
                        "dyadic_only": dyadic_only,
                        "objective": _exact_value(allocation.objective_grid, -298),
                        "used_states": allocation.used_states,
                    }
                    allocation_digest.update(artifacts.canonical_json_bytes(record) + b"\n")
    native = _run_native(("representation-suite",), capture=True)
    try:
        native_result = json.loads(native.stdout)
    except (json.JSONDecodeError, TypeError, ValueError, RecursionError) as error:
        raise GateFailure("IMPLEMENTATION_INVALID", "native representation output is not JSON") from error
    if not isinstance(native_result, Mapping):
        raise GateFailure("IMPLEMENTATION_INVALID", "native representation output is not an object")
    _require_exact_keys(
        native_result,
        {
            "allocation_record_count",
            "allocation_sha256",
            "all_decisions_equal",
            "authority_hashes_equal",
            "candidate_counts",
            "checks",
            "decision_equality_count",
            "exact_objective_class_count",
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
        },
        "native representation output",
    )
    if _json_int(
        native_result.get("allocation_record_count"),
        "native representation allocation_record_count",
    ) != allocation_count:
        raise GateFailure("IMPLEMENTATION_INVALID", "native allocation fixture count mismatch")
    python_order_fingerprint = allocation_digest.hexdigest()
    independent_exhaustive_sha256 = _json_sha256(
        native_result["independent_exhaustive_sha256"],
        "native representation independent_exhaustive_sha256",
    )
    optimized_sha256 = _json_sha256(
        native_result["optimized_sha256"],
        "native representation optimized_sha256",
    )
    legacy_allocation_sha256 = _json_sha256(
        native_result["allocation_sha256"],
        "native representation allocation_sha256",
    )
    native_python_fingerprint = _json_sha256(
        native_result["python_order_fingerprint_sha256"],
        "native representation python_order_fingerprint_sha256",
    )
    if (
        native_result["python_order_fingerprint_authoritative"] is not False
        or native_python_fingerprint != python_order_fingerprint
        or legacy_allocation_sha256 != python_order_fingerprint
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            "native/Python representation order fingerprint mismatch",
        )
    if (
        independent_exhaustive_sha256 != optimized_sha256
        or native_result["authority_hashes_equal"] is not True
        or native_result["all_decisions_equal"] is not True
        or _json_int(
            native_result["decision_equality_count"],
            "native representation decision_equality_count",
        )
        != allocation_count
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            "compiled exhaustive allocation authority disagrees with optimized allocation",
        )
    candidate_counts = native_result["candidate_counts"]
    if not isinstance(candidate_counts, Mapping):
        raise GateFailure("IMPLEMENTATION_INVALID", "native candidate_counts is not an object")
    _require_exact_keys(
        candidate_counts,
        {
            "independent_feasible_tuple_evaluations",
            "optimized_candidate_evaluations",
        },
        "native candidate_counts",
    )
    if (
        _json_count(
            candidate_counts["independent_feasible_tuple_evaluations"],
            "native exhaustive tuple count",
        )
        != 958_838_400
        or _json_count(
            candidate_counts["optimized_candidate_evaluations"],
            "native optimized candidate count",
        )
        != 174_002_400
    ):
        raise GateFailure("IMPLEMENTATION_INVALID", "native allocation work count mismatch")
    objective_class_count = _json_count(
        native_result["exact_objective_class_count"],
        "native exact objective class count",
    )
    if not allocation_count <= objective_class_count <= allocation_count * 16:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "native objective-class count is out of bounds"
        )
    expected_inventory_sha256 = _tiny_curve_inventory_sha256(tiny_curves)
    if expected_inventory_sha256 != "d3007781fa14b6a1291bf26aae7a9741a945ebc36b5073982645f8035b99c6eb":
        raise GateFailure("IMPLEMENTATION_INVALID", "Python tiny inventory identity drifted")
    if (
        _json_sha256(
            native_result["tiny_curve_inventory_sha256"],
            "native tiny_curve_inventory_sha256",
        )
        != expected_inventory_sha256
        or native_result["tiny_curve_inventory_preimage_schema"]
        != (
            "canonical JSONL: case_id, then samples with binary32_bits, "
            "vector_id, weight; terminal LF per case"
        )
    ):
        raise GateFailure("IMPLEMENTATION_INVALID", "native tiny inventory mismatch")
    expected_same_h = _same_h_different_weight_fixture()
    if not _strict_json_equal(
        expected_same_h, native_result["same_h_different_weight_fixture"]
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "same-H/different-weight fixture mismatch"
        )
    checks = native_result.get("checks")
    expected_check_keys = {
        "allocation_record_count",
        "all_decisions_equal",
        "authority_hashes_equal",
        "candidate_counts",
        "equidistant_lower_codeword",
        "objective_contract",
        "representation_constant_smoke",
        "tiny_case_count",
    }
    if not isinstance(checks, Mapping) or set(checks) != expected_check_keys or any(
        value is not True for value in checks.values()
    ):
        raise GateFailure("IMPLEMENTATION_INVALID", "native representation fixture failed")

    expected_support_winners = _representation_support_size_winners()
    expected_mixed_radix = _representation_mixed_radix_case()
    expected_matched_packing = _representation_matched_packing_cases()
    expected_global_packing = [
        _representation_global_packing_case(paid_bytes)
        for paid_bytes in (32, 64)
    ]
    expected_matched_lookup = _representation_matched_lookup_cases()
    expected_global_lookup = _representation_global_lookup_case()
    expected_sections = {
        "support_size_winners": expected_support_winners,
        "mixed_radix_case": expected_mixed_radix,
        "matched_packing_cases": expected_matched_packing,
        "global_packing_cases": expected_global_packing,
        "matched_lookup_cases": expected_matched_lookup,
        "global_lookup_case": expected_global_lookup,
    }
    for section, independent in expected_sections.items():
        if section not in native_result:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"native representation output omits {section}",
            )
        if not _strict_json_equal(independent, native_result[section]):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"native representation {section} mismatch",
            )

    smoke_path = output_dir / ".native_smoke.tsv"
    _run_native(("native-smoke", str(smoke_path)))
    observed_rounding, smoke_controls = _parse_native_smoke(smoke_path)
    smoke_path.unlink()
    return {
        "artifact_kind": "representation_parity",
        "allocation_pair_count": len(tiny_curves) ** 2,
        "allocation_record_count": allocation_count,
        "allocation_sha256": python_order_fingerprint,
        "allocation_authority": "compiled_structurally_independent_exhaustive_enumerator",
        "candidate_counts": dict(candidate_counts),
        "decision_equality_count": allocation_count,
        "exact_objective_class_count": str(objective_class_count),
        "full_allocation_digest": {
            "decision_order": (
                "capacity=16,256; cardinality=arbitrary,dyadic; "
                "first_tiny_case=0..779; second_tiny_case=0..779"
            ),
            "independent_sha256": independent_exhaustive_sha256,
            "optimized_sha256": optimized_sha256,
            "record_count": allocation_count,
            "equal": independent_exhaustive_sha256 == optimized_sha256,
        },
        "python_order_fingerprint": {
            "authoritative": False,
            "sha256": python_order_fingerprint,
        },
        "same_h_different_weight_fixture": _paired_fixture(
            expected_same_h,
            native_result["same_h_different_weight_fixture"],
        ),
        "tiny_curve_inventory_sha256": expected_inventory_sha256,
        "support_size_winners": [
            _paired_fixture(independent, optimized)
            for independent, optimized in zip(
                expected_support_winners,
                native_result["support_size_winners"],
            )
        ],
        "mixed_radix_case": _paired_fixture(
            expected_mixed_radix,
            native_result["mixed_radix_case"],
        ),
        "matched_packing_cases": [
            _paired_fixture(independent, optimized)
            for independent, optimized in zip(
                expected_matched_packing,
                native_result["matched_packing_cases"],
            )
        ],
        "global_packing_cases": [
            _paired_fixture(independent, optimized)
            for independent, optimized in zip(
                expected_global_packing,
                native_result["global_packing_cases"],
            )
        ],
        "matched_lookup_cases": [
            _paired_lookup_case(independent, optimized)
            for independent, optimized in zip(
                expected_matched_lookup,
                native_result["matched_lookup_cases"],
            )
        ],
        "global_lookup_case": _paired_lookup_case(
            expected_global_lookup,
            native_result["global_lookup_case"],
        ),
        "native": native_result,
        "packing_fixture": {
            "b4_payload_bytes": 32,
            "b8_payload_bytes": 64,
            "global_nonbyte_aligned_exercised": True,
        },
        "rounding_fixture_count": len(observed_rounding),
        "native_control_smoke": smoke_controls,
        "direct_rounding": [
            {
                "kind": key[0],
                "numerator": key[1],
                "denominator": key[2],
                "binary_grid_exponent": int(key[3]),
                "binary32_bits": value[0],
                "binary64_bits": value[1],
            }
            for key, value in sorted(observed_rounding.items())
        ],
    }


def _write_block_input(
    path: Path,
    cases: Sequence[
        tuple[
            int,
            int,
            int,
            str,
            Sequence[Sequence[float]],
            Sequence[float],
            Sequence[float],
            Sequence[int],
        ]
    ],
) -> None:
    with path.open("xb") as output:
        output.write(b"A4BLK001")
        output.write(struct.pack("<I", len(cases)))
        for case_id, capacity, group_id, dataset_id, rows, axis0, axis1, cells in cases:
            if len(cells) != len(rows):
                raise GateFailure("IMPLEMENTATION_INVALID", "block cell-id shape mismatch")
            encoded_dataset = dataset_id.encode("utf-8")
            output.write(
                struct.pack(
                    "<IIII",
                    case_id,
                    capacity,
                    group_id,
                    len(encoded_dataset),
                )
            )
            output.write(encoded_dataset)
            output.write(struct.pack("<III", len(rows), len(axis0), len(axis1)))
            for vector_id, (row, cell_id) in enumerate(zip(rows, cells)):
                output.write(
                    struct.pack(
                        "<IIQQ",
                        reference.float32_bits(float(row[0])),
                        reference.float32_bits(float(row[1])),
                        int(cell_id),
                        vector_id,
                    )
                )
            for value in itertools.chain(axis0, axis1):
                output.write(struct.pack("<Q", reference.float64_bits(float(value))))
        output.flush()


def _expected_block_output_cases(
    requested_cases: Sequence[
        tuple[
            int,
            int,
            int,
            str,
            Sequence[Sequence[float]],
            Sequence[float],
            Sequence[float],
            Sequence[int],
        ]
    ],
) -> list[dict[str, Any]]:
    expected: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for case_id, capacity, group_id, dataset_id, rows, axis0, axis1, cells in requested_cases:
        if case_id in seen_ids or len(rows) != len(cells):
            raise GateFailure("IMPLEMENTATION_INVALID", "requested block-case inventory is invalid")
        seen_ids.add(case_id)
        ordered_rows = []
        for vector_id, (row, cell_id) in enumerate(zip(rows, cells)):
            if len(row) != 2:
                raise GateFailure("IMPLEMENTATION_INVALID", "requested block row is not two-dimensional")
            coordinate_bits = [
                _hex32(reference.float32_bits(float(row[0]))),
                _hex32(reference.float32_bits(float(row[1]))),
            ]
            digest = reference.sha256_bytes(
                f"{SCIENTIFIC_PROTOCOL_VERSION}|{dataset_id}|{int(cell_id)}|{vector_id}"
            ).hex()
            ordered_rows.append(
                {
                    "cell_id": int(cell_id),
                    "vector_id": vector_id,
                    "selection_digest": digest,
                    "coordinate_bits": coordinate_bits,
                }
            )
        ordered_rows.sort(
            key=lambda row: (
                row["cell_id"],
                bytes.fromhex(row["selection_digest"]),
                row["vector_id"],
            )
        )
        axes = [
            [_hex64(reference.float64_bits(float(value))) for value in axis0],
            [_hex64(reference.float64_bits(float(value))) for value in axis1],
        ]
        expected.append(
            {
                "case_id": int(case_id),
                "protocol_version": SCIENTIFIC_PROTOCOL_VERSION,
                "dataset_id": dataset_id,
                "capacity": int(capacity),
                "group_id": int(group_id),
                "point_count": len(rows),
                "axis_counts": [len(axis0), len(axis1)],
                "axes": axes,
                "rows": ordered_rows,
                "cartesian_centers": [
                    [left, right] for right in axes[1] for left in axes[0]
                ],
            }
        )
    return expected


def _parse_block_output_unchecked(
    path: Path,
    *,
    requested_cases: Sequence[
        tuple[
            int,
            int,
            int,
            str,
            Sequence[Sequence[float]],
            Sequence[float],
            Sequence[float],
            Sequence[int],
        ]
    ],
    allow_control_invalid: bool = False,
) -> dict[int, dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "A4S_BLOCK_RESULT_V1":
        raise GateFailure("IMPLEMENTATION_INVALID", "block output header mismatch")
    if len(lines) < 2 or lines[1] != f"PROTOCOL\t{SCIENTIFIC_PROTOCOL_VERSION}":
        raise GateFailure("IMPLEMENTATION_INVALID", "block protocol namespace mismatch")

    expected_cases = _expected_block_output_cases(requested_cases)
    cases: dict[int, dict[str, Any]] = {}
    ended_cases: set[int] = set()
    ended_starts: set[tuple[int, int]] = set()
    saw_end = False
    terminal_counts: tuple[int, int, int] | None = None
    active_case_id: int | None = None
    record_arities = {
        "CASE": 13,
        "AXIS": 5,
        "ROW": 8,
        "CARTESIAN": 5,
        "CARTESIAN_CENTER": 5,
        "START": 19,
        "START_SELECTED": 5,
        "START_CENTER": 6,
        "STEP": 9,
        "STEP_EMPTY": 6,
        "STEP_CENTER": 7,
        "FINAL_ASSIGNMENT": 6,
        "FINAL_CENTER": 6,
        "FINAL_SERIALIZED_CENTER": 6,
        "END_START": 3,
        "BEST_CENTER": 7,
        "BEST_ASSIGNMENT": 5,
        "END_CASE": 2,
    }
    for line_index, line in enumerate(lines[2:], start=2):
        fields = line.split("\t")
        kind = fields[0]
        if kind == "END":
            if saw_end or line_index != len(lines) - 1 or len(fields) != 4:
                raise GateFailure("IMPLEMENTATION_INVALID", "block END is missing, duplicate, or nonterminal")
            if active_case_id is not None:
                raise GateFailure("IMPLEMENTATION_INVALID", "block END occurs inside a case")
            terminal_counts = (
                _tsv_uint(fields[1], "block END case_count"),
                _tsv_uint(fields[2], "block END valid_count"),
                _tsv_uint(fields[3], "block END invalid_count"),
            )
            saw_end = True
            continue
        if saw_end:
            raise GateFailure("IMPLEMENTATION_INVALID", "block record follows END")
        if len(fields) < 2:
            raise GateFailure("IMPLEMENTATION_INVALID", "truncated block output record")
        if kind == "BEST":
            if len(fields) not in {3, 8}:
                raise GateFailure("IMPLEMENTATION_INVALID", "block BEST field count mismatch")
        elif kind not in record_arities or len(fields) != record_arities[kind]:
            raise GateFailure("IMPLEMENTATION_INVALID", f"block {kind} field count mismatch")
        case_id = _tsv_uint(fields[1], "block case_id", maximum=(1 << 32) - 1)
        if kind == "CASE":
            if active_case_id is not None or case_id in cases:
                raise GateFailure("IMPLEMENTATION_INVALID", "duplicate block case")
            if len(cases) >= len(expected_cases):
                raise GateFailure("IMPLEMENTATION_INVALID", "unexpected block case")
            expected = expected_cases[len(cases)]
            if case_id != expected["case_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block requested-case order mismatch")
            control_valid = _tsv_bool(fields[9], "block CASE control_valid")
            if fields[10] not in _FAILURE_NAMES:
                raise GateFailure("IMPLEMENTATION_INVALID", "block CASE failure enum mismatch")
            declared_shape = {
                "protocol_version": fields[2],
                "dataset_id": fields[3],
                "capacity": _tsv_uint(fields[4], "block CASE capacity"),
                "group_id": _tsv_uint(fields[5], "block CASE group_id"),
                "point_count": _tsv_uint(fields[6], "block CASE point_count"),
                "axis_counts": [
                    _tsv_uint(fields[7], "block CASE axis0_count"),
                    _tsv_uint(fields[8], "block CASE axis1_count"),
                ],
            }
            if any(declared_shape[key] != expected[key] for key in declared_shape):
                raise GateFailure("IMPLEMENTATION_INVALID", "block requested CASE metadata mismatch")
            cases[case_id] = {
                "case_id": case_id,
                "protocol_version": fields[2],
                "dataset_id": fields[3],
                "capacity": declared_shape["capacity"],
                "group_id": declared_shape["group_id"],
                "point_count": declared_shape["point_count"],
                "axis_counts": declared_shape["axis_counts"],
                "control_valid": control_valid,
                "failure": fields[10],
                "failed_start_id": _tsv_uint(fields[11], "block CASE failed_start_id"),
                "failure_detail": fields[12],
                "axes": [[], []],
                "rows": [],
                "cartesian": {"centers": []},
                "starts": {},
                "best": {"centers": [], "assignments": []},
                "_expected": expected,
                "_active_start_id": None,
                "_cartesian_seen": False,
                "_best_seen": False,
                "_best_phase": 0,
                "validation_best_start_sse_comparison_count": 0,
            }
            active_case_id = case_id
            continue
        if case_id != active_case_id or case_id not in cases or case_id in ended_cases:
            raise GateFailure("IMPLEMENTATION_INVALID", "block record is outside an open case")
        case = cases[case_id]
        if kind == "AXIS":
            if case["rows"] or case["_cartesian_seen"] or case["starts"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block AXIS record is out of order")
            axis = _tsv_uint(fields[2], "block axis id", maximum=1)
            axis_index = _tsv_uint(fields[3], "block axis index")
            bits = _tsv_bits(fields[4], 64, "block axis bits")
            if axis_index != len(case["axes"][axis]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block axis order mismatch")
            if axis == 1 and len(case["axes"][0]) != case["axis_counts"][0]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block axis-1 precedes complete axis-0")
            if bits != case["_expected"]["axes"][axis][axis_index]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block requested axis bits mismatch")
            case["axes"][axis].append(bits)
        elif kind == "ROW":
            if (
                any(len(case["axes"][axis]) != case["axis_counts"][axis] for axis in (0, 1))
                or case["_cartesian_seen"]
                or case["starts"]
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block ROW record is out of order")
            row_index = _tsv_uint(fields[2], "block row index")
            if row_index != len(case["rows"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block row order mismatch")
            row = {
                "cell_id": _tsv_uint(fields[3], "block row cell_id"),
                "vector_id": _tsv_uint(fields[4], "block row vector_id"),
                "selection_digest": _tsv_sha256(fields[5], "block row selection_digest"),
                "coordinate_bits": [
                    _tsv_bits(fields[6], 32, "block row coordinate0"),
                    _tsv_bits(fields[7], 32, "block row coordinate1"),
                ],
            }
            if row != case["_expected"]["rows"][row_index]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block requested row identity mismatch")
            case["rows"].append(row)
        elif kind == "CARTESIAN":
            if (
                len(case["rows"]) != case["point_count"]
                or case["_cartesian_seen"]
                or case["starts"]
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block CARTESIAN record is out of order")
            center_count = _tsv_uint(fields[2], "block Cartesian center_count")
            if center_count != len(case["_expected"]["cartesian_centers"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block Cartesian shape mismatch")
            case["cartesian"].update(
                {
                    "center_count": center_count,
                    "sse_bits": _tsv_bits(fields[3], 64, "block Cartesian SSE"),
                    "filled_sse_bits": _tsv_bits(fields[4], 64, "block filled SSE"),
                }
            )
            case["_cartesian_seen"] = True
        elif kind == "CARTESIAN_CENTER":
            if not case["_cartesian_seen"] or case["starts"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block Cartesian center is out of order")
            center_index = _tsv_uint(fields[2], "block Cartesian center index")
            if center_index != len(case["cartesian"]["centers"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "Cartesian center order mismatch")
            center = [
                _tsv_bits(fields[3], 64, "block Cartesian center coordinate0"),
                _tsv_bits(fields[4], 64, "block Cartesian center coordinate1"),
            ]
            if center != case["_expected"]["cartesian_centers"][center_index]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block Cartesian center identity mismatch")
            case["cartesian"]["centers"].append(center)
        elif kind == "START":
            if (
                not case["_cartesian_seen"]
                or len(case["cartesian"]["centers"])
                != case["cartesian"].get("center_count")
                or case["_active_start_id"] is not None
                or case["_best_seen"]
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block START record is out of order")
            start_id = _tsv_uint(fields[2], "block start_id", maximum=BLOCK_START_COUNT - 1)
            if (
                start_id != len(case["starts"])
                or start_id in case["starts"]
                or (case_id, start_id) in ended_starts
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "duplicate block start")
            first_seed_digest = _tsv_sha256(fields[3], "block first_seed_digest")
            selected_count = _tsv_uint(fields[4], "block selected_count")
            initial_center_count = _tsv_uint(fields[5], "block initial_center_count")
            step_count = _tsv_uint(fields[7], "block step_count")
            iterations = _tsv_uint(fields[8], "block iterations")
            converged = _tsv_bool(fields[9], "block start converged")
            if fields[10] not in _FAILURE_NAMES:
                raise GateFailure("IMPLEMENTATION_INVALID", "block START failure enum mismatch")
            case["starts"][start_id] = {
                "start_id": start_id,
                "first_seed_digest": first_seed_digest,
                "selected_count": selected_count,
                "initial_center_count": initial_center_count,
                "initial_sse_bits": _tsv_bits(fields[6], 64, "block initial SSE"),
                "step_count": step_count,
                "iterations": iterations,
                "converged": converged,
                "failure": fields[10],
                "final_sse_bits": _tsv_bits(fields[11], 64, "block final SSE"),
                "final_assignment_count": _tsv_uint(fields[12], "block final_assignment_count"),
                "final_center_count": _tsv_uint(fields[13], "block final_center_count"),
                "serialized_center_count": _tsv_uint(fields[14], "block serialized_center_count"),
                "distinct_serialized_center_count": _tsv_uint(fields[15], "block distinct center_count"),
                "distance_comparison_count": _tsv_uint(fields[16], "block distance comparisons"),
                "assignment_tie_count": _tsv_uint(fields[17], "block assignment ties"),
                "farthest_tie_count": _tsv_uint(fields[18], "block farthest ties"),
                "selected_vector_ids": [],
                "initial_centers_bits": [],
                "steps": [],
                "final_assignments": [],
                "final_centers_bits": [],
                "serialized_centers_bits": [],
                "ended": False,
                "_phase": 0,
            }
            case["_active_start_id"] = start_id
        elif kind == "START_SELECTED":
            start_id = _tsv_uint(fields[2], "block selected start_id")
            if start_id != case["_active_start_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block selected row references inactive start")
            start = case["starts"][start_id]
            if start["ended"] or start["_phase"] != 0:
                raise GateFailure("IMPLEMENTATION_INVALID", "block start record follows END_START")
            selected_index = _tsv_uint(fields[3], "block selected row index")
            if selected_index != len(start["selected_vector_ids"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block selected-id order mismatch")
            vector_id = _tsv_uint(fields[4], "block selected vector_id")
            if vector_id not in {row["vector_id"] for row in case["rows"]}:
                raise GateFailure("IMPLEMENTATION_INVALID", "block selected vector_id is not requested")
            start["selected_vector_ids"].append(vector_id)
        elif kind == "START_CENTER":
            start_id = _tsv_uint(fields[2], "block initial-center start_id")
            if start_id != case["_active_start_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block initial center references inactive start")
            start = case["starts"][start_id]
            if start["ended"] or start["_phase"] > 1:
                raise GateFailure("IMPLEMENTATION_INVALID", "block start record follows END_START")
            if len(start["selected_vector_ids"]) != start["selected_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block initial centers precede selected rows")
            start["_phase"] = 1
            center_index = _tsv_uint(fields[3], "block initial-center index")
            if center_index != len(start["initial_centers_bits"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block initial-center order mismatch")
            start["initial_centers_bits"].append(
                [
                    _tsv_bits(fields[4], 64, "block initial center coordinate0"),
                    _tsv_bits(fields[5], 64, "block initial center coordinate1"),
                ]
            )
        elif kind == "STEP":
            start_id = _tsv_uint(fields[2], "block STEP start_id")
            if start_id != case["_active_start_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block STEP references inactive start")
            start = case["starts"][start_id]
            if start["ended"] or start["_phase"] > 2:
                raise GateFailure("IMPLEMENTATION_INVALID", "block start record follows END_START")
            if (
                len(start["selected_vector_ids"]) != start["selected_count"]
                or len(start["initial_centers_bits"]) != start["initial_center_count"]
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block STEP precedes complete initialization")
            if start["steps"]:
                prior = start["steps"][-1]
                if (
                    len(prior["empty_center_ids"]) != prior["declared_empty_count"]
                    or len(prior["centers_after_bits"]) != prior["declared_center_count"]
                ):
                    raise GateFailure("IMPLEMENTATION_INVALID", "block STEP overlaps prior step")
            start["_phase"] = 2
            iteration = _tsv_uint(fields[3], "block STEP iteration")
            if iteration != len(start["steps"]) + 1:
                raise GateFailure("IMPLEMENTATION_INVALID", "block STEP iteration order mismatch")
            start["steps"].append(
                {
                    "iteration": iteration,
                    "prior_sse_bits": _tsv_bits(fields[4], 64, "block STEP prior SSE"),
                    "candidate_sse_bits": _tsv_bits(fields[5], 64, "block STEP candidate SSE"),
                    "changed_assignment_count": _tsv_uint(fields[6], "block STEP changed assignments"),
                    "declared_empty_count": _tsv_uint(fields[7], "block STEP empty count"),
                    "declared_center_count": _tsv_uint(fields[8], "block STEP center count"),
                    "empty_center_ids": [],
                    "centers_after_bits": [],
                }
            )
        elif kind == "STEP_EMPTY":
            start_id = _tsv_uint(fields[2], "block STEP_EMPTY start_id")
            iteration = _tsv_uint(fields[3], "block STEP_EMPTY iteration")
            if start_id != case["_active_start_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block STEP_EMPTY references inactive start")
            start = case["starts"][start_id]
            if start["ended"] or start["_phase"] != 2 or iteration != len(start["steps"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block STEP_EMPTY references a closed or unknown step")
            step = start["steps"][iteration - 1]
            if step["iteration"] != iteration or step["centers_after_bits"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block STEP_EMPTY iteration mismatch")
            empty_index = _tsv_uint(fields[4], "block empty-center index")
            if empty_index != len(step["empty_center_ids"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block empty-center order mismatch")
            center_id = _tsv_uint(fields[5], "block empty center_id")
            if center_id >= case["capacity"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block empty center_id is out of range")
            step["empty_center_ids"].append(center_id)
        elif kind == "STEP_CENTER":
            start_id = _tsv_uint(fields[2], "block STEP_CENTER start_id")
            iteration = _tsv_uint(fields[3], "block STEP_CENTER iteration")
            if start_id != case["_active_start_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block STEP_CENTER references inactive start")
            start = case["starts"][start_id]
            if start["ended"] or start["_phase"] != 2 or iteration != len(start["steps"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block STEP_CENTER references a closed or unknown step")
            step = start["steps"][iteration - 1]
            if (
                step["iteration"] != iteration
                or len(step["empty_center_ids"]) != step["declared_empty_count"]
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block STEP_CENTER iteration mismatch")
            center_index = _tsv_uint(fields[4], "block step-center index")
            if center_index != len(step["centers_after_bits"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block step-center order mismatch")
            step["centers_after_bits"].append(
                [
                    _tsv_bits(fields[5], 64, "block step center coordinate0"),
                    _tsv_bits(fields[6], 64, "block step center coordinate1"),
                ]
            )
        elif kind == "FINAL_ASSIGNMENT":
            start_id = _tsv_uint(fields[2], "block final-assignment start_id")
            if start_id != case["_active_start_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block final assignment references inactive start")
            start = case["starts"][start_id]
            if start["ended"] or start["_phase"] > 3:
                raise GateFailure("IMPLEMENTATION_INVALID", "block final assignment is out of order")
            if start["steps"]:
                prior = start["steps"][-1]
                if (
                    len(prior["empty_center_ids"]) != prior["declared_empty_count"]
                    or len(prior["centers_after_bits"]) != prior["declared_center_count"]
                ):
                    raise GateFailure("IMPLEMENTATION_INVALID", "block final assignment precedes complete step")
            start["_phase"] = 3
            row_index = _tsv_uint(fields[3], "block final-assignment row index")
            if row_index != len(start["final_assignments"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block final assignment order mismatch")
            if _tsv_uint(fields[4], "block final-assignment vector_id") != case["rows"][row_index]["vector_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block final-assignment vector identity mismatch")
            assignment = _tsv_uint(fields[5], "block final assignment")
            if assignment >= case["capacity"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block final assignment is out of range")
            start["final_assignments"].append(assignment)
        elif kind == "FINAL_CENTER":
            start_id = _tsv_uint(fields[2], "block final-center start_id")
            if start_id != case["_active_start_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block final center references inactive start")
            start = case["starts"][start_id]
            if start["ended"] or start["_phase"] > 4:
                raise GateFailure("IMPLEMENTATION_INVALID", "block final center is out of order")
            if len(start["final_assignments"]) != start["final_assignment_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block final centers precede assignments")
            start["_phase"] = 4
            center_index = _tsv_uint(fields[3], "block final-center index")
            if center_index != len(start["final_centers_bits"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block final-center order mismatch")
            start["final_centers_bits"].append(
                [
                    _tsv_bits(fields[4], 64, "block final center coordinate0"),
                    _tsv_bits(fields[5], 64, "block final center coordinate1"),
                ]
            )
        elif kind == "FINAL_SERIALIZED_CENTER":
            start_id = _tsv_uint(fields[2], "block serialized-center start_id")
            if start_id != case["_active_start_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block serialized center references inactive start")
            start = case["starts"][start_id]
            if start["ended"] or start["_phase"] > 5:
                raise GateFailure("IMPLEMENTATION_INVALID", "block serialized center is out of order")
            if len(start["final_centers_bits"]) != start["final_center_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block serialized centers precede final centers")
            start["_phase"] = 5
            center_index = _tsv_uint(fields[3], "block serialized-center index")
            if center_index != len(start["serialized_centers_bits"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block serialized-center order mismatch")
            start["serialized_centers_bits"].append(
                [
                    _tsv_bits(fields[4], 32, "block serialized center coordinate0"),
                    _tsv_bits(fields[5], 32, "block serialized center coordinate1"),
                ]
            )
        elif kind == "END_START":
            start_id = _tsv_uint(fields[2], "block END_START start_id")
            key = (case_id, start_id)
            if (
                key in ended_starts
                or start_id not in case["starts"]
                or start_id != case["_active_start_id"]
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "duplicate or unknown END_START")
            start = case["starts"][start_id]
            if len(start["selected_vector_ids"]) != start["selected_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block selected-row count mismatch")
            if len(start["initial_centers_bits"]) != start["initial_center_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block initial-center count mismatch")
            if start["initial_center_count"] != case["capacity"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block initial-center capacity mismatch")
            if len(start["steps"]) != start["step_count"] or start["iterations"] != start["step_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block step/iteration count mismatch")
            for expected_iteration, step in enumerate(start["steps"], start=1):
                if step["iteration"] != expected_iteration:
                    raise GateFailure("IMPLEMENTATION_INVALID", "block step iteration sequence mismatch")
                if len(step["empty_center_ids"]) != step.pop("declared_empty_count"):
                    raise GateFailure("IMPLEMENTATION_INVALID", "block empty-center count mismatch")
                if len(step["centers_after_bits"]) != step.pop("declared_center_count"):
                    raise GateFailure("IMPLEMENTATION_INVALID", "block step-center count mismatch")
            if len(start["final_assignments"]) != start["final_assignment_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block final-assignment count mismatch")
            if len(start["final_centers_bits"]) != start["final_center_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block final-center count mismatch")
            if len(start["serialized_centers_bits"]) != start["serialized_center_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block serialized-center count mismatch")
            if len({tuple(bits) for bits in start["serialized_centers_bits"]}) != start["distinct_serialized_center_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block distinct serialized-center count mismatch")
            if len(start["selected_vector_ids"]) != len(set(start["selected_vector_ids"])):
                raise GateFailure("IMPLEMENTATION_INVALID", "block selected vector ids are not distinct")
            if start["failure"] == "NONE" and not start["converged"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block successful start did not converge")
            if start["failure"] == "NONE" and (
                start["final_assignment_count"] != case["point_count"]
                or start["final_center_count"] != case["capacity"]
                or start["serialized_center_count"] != case["capacity"]
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "successful block start shape mismatch")
            start["ended"] = True
            ended_starts.add(key)
            case["_active_start_id"] = None
        elif kind == "BEST":
            if (
                case["_active_start_id"] is not None
                or len(case["starts"]) != BLOCK_START_COUNT
                or case["_best_seen"]
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block BEST record is out of order")
            valid = _tsv_bool(fields[2], "block BEST control_valid")
            if len(fields) != (8 if valid else 3):
                raise GateFailure("IMPLEMENTATION_INVALID", "block BEST arity/control mismatch")
            case["best"]["control_valid"] = valid
            case["_best_seen"] = True
            if valid:
                case["best"].update(
                    {
                        "start_id": _tsv_uint(fields[3], "block BEST start_id", maximum=BLOCK_START_COUNT - 1),
                        "sse_bits": _tsv_bits(fields[4], 64, "block BEST SSE"),
                        "center_count": _tsv_uint(fields[5], "block BEST center_count"),
                        "assignment_count": _tsv_uint(fields[6], "block BEST assignment_count"),
                        "serialized_center_count": _tsv_uint(fields[7], "block BEST serialized_center_count"),
                    }
                )
        elif kind == "BEST_CENTER":
            if (
                not case["_best_seen"]
                or case["best"].get("control_valid") is not True
                or case["_best_phase"] > 1
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block BEST_CENTER follows no valid BEST")
            case["_best_phase"] = 1
            center_index = _tsv_uint(fields[2], "block BEST center index")
            if center_index != len(case["best"]["centers"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block best-center order mismatch")
            case["best"]["centers"].append(
                {
                    "binary64_bits": [
                        _tsv_bits(fields[3], 64, "block BEST center coordinate0"),
                        _tsv_bits(fields[4], 64, "block BEST center coordinate1"),
                    ],
                    "binary32_bits": [
                        _tsv_bits(fields[5], 32, "block BEST serialized coordinate0"),
                        _tsv_bits(fields[6], 32, "block BEST serialized coordinate1"),
                    ],
                }
            )
        elif kind == "BEST_ASSIGNMENT":
            if (
                not case["_best_seen"]
                or case["best"].get("control_valid") is not True
                or len(case["best"]["centers"]) != case["best"].get("center_count")
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block BEST_ASSIGNMENT follows no valid BEST")
            case["_best_phase"] = 2
            row_index = _tsv_uint(fields[2], "block BEST assignment row")
            if row_index != len(case["best"]["assignments"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block best-assignment order mismatch")
            if _tsv_uint(fields[3], "block BEST assignment vector_id") != case["rows"][row_index]["vector_id"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block BEST assignment vector identity mismatch")
            assignment = _tsv_uint(fields[4], "block BEST assignment")
            if assignment >= case["capacity"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block BEST assignment is out of range")
            case["best"]["assignments"].append(assignment)
        elif kind == "END_CASE":
            if case_id in ended_cases or case["_active_start_id"] is not None:
                raise GateFailure("IMPLEMENTATION_INVALID", "duplicate block END_CASE")
            if any(not start["ended"] for start in case["starts"].values()):
                raise GateFailure("IMPLEMENTATION_INVALID", "block case ended before a start")
            if len(case["axes"][0]) != case["axis_counts"][0] or len(case["axes"][1]) != case["axis_counts"][1]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block axis count mismatch")
            if len(case["rows"]) != case["point_count"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block row count mismatch")
            if len(case["cartesian"]["centers"]) != case["cartesian"].get("center_count"):
                raise GateFailure("IMPLEMENTATION_INVALID", "block Cartesian-center count mismatch")
            if not case["_best_seen"] or "control_valid" not in case["best"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block BEST record missing")
            if case["best"]["control_valid"] is not case["control_valid"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "block CASE/BEST control mismatch")
            if case["control_valid"]:
                if (
                    case["failure"] != "NONE"
                    or case["failure_detail"] != ""
                    or case["failed_start_id"] != 0
                    or any(
                        start["failure"] != "NONE" or not start["converged"]
                        for start in case["starts"].values()
                    )
                ):
                    raise GateFailure("IMPLEMENTATION_INVALID", "valid block CASE/start failure state mismatch")
            else:
                if (
                    case["failure"] == "NONE"
                    or not case["failure_detail"]
                    or case["failed_start_id"] not in case["starts"]
                ):
                    raise GateFailure("IMPLEMENTATION_INVALID", "invalid block CASE failure state mismatch")
                failed_start = case["starts"][case["failed_start_id"]]
                if failed_start["failure"] not in {"NONE", case["failure"]}:
                    raise GateFailure("IMPLEMENTATION_INVALID", "block CASE/start failure enum mismatch")
            _validate_block_selected_distinctness(case)
            if case["best"]["control_valid"]:
                if len(case["best"]["centers"]) != case["best"]["center_count"]:
                    raise GateFailure("IMPLEMENTATION_INVALID", "block best-center count mismatch")
                if len(case["best"]["assignments"]) != case["best"]["assignment_count"]:
                    raise GateFailure("IMPLEMENTATION_INVALID", "block best-assignment count mismatch")
                selected = case["starts"][case["best"]["start_id"]]
                expected_best_centers = [
                    {"binary64_bits": binary64, "binary32_bits": binary32}
                    for binary64, binary32 in zip(
                        selected["final_centers_bits"],
                        selected["serialized_centers_bits"],
                    )
                ]
                if (
                    case["best"]["sse_bits"] != selected["final_sse_bits"]
                    or case["best"]["centers"] != expected_best_centers
                    or case["best"]["assignments"] != selected["final_assignments"]
                    or case["best"]["center_count"] != selected["final_center_count"]
                    or case["best"]["serialized_center_count"]
                    != selected["serialized_center_count"]
                    or case["best"]["assignment_count"]
                    != selected["final_assignment_count"]
                ):
                    raise GateFailure("IMPLEMENTATION_INVALID", "block BEST does not equal selected start")
            elif case["best"]["centers"] or case["best"]["assignments"]:
                raise GateFailure("IMPLEMENTATION_INVALID", "invalid block BEST has payload records")
            ended_cases.add(case_id)
            active_case_id = None
        else:
            raise GateFailure("IMPLEMENTATION_INVALID", f"unknown block record {kind}")

    if not saw_end or terminal_counts is None:
        raise GateFailure("IMPLEMENTATION_INVALID", "block terminal END is missing")
    declared_cases, declared_valid, declared_invalid = terminal_counts
    if (
        declared_cases != len(cases)
        or declared_cases != len(expected_cases)
        or ended_cases != set(cases)
        or list(cases) != [case["case_id"] for case in expected_cases]
    ):
        raise GateFailure("IMPLEMENTATION_INVALID", "block case terminal count mismatch")
    observed_valid = sum(bool(case["control_valid"]) for case in cases.values())
    observed_invalid = len(cases) - observed_valid
    if declared_valid != observed_valid or declared_invalid != observed_invalid:
        raise GateFailure("IMPLEMENTATION_INVALID", "block validity counters are inconsistent")
    if declared_invalid and not allow_control_invalid:
        raise GateFailure("CONTROL_INVALID", "native block control is invalid")

    # Convert the lossless native trace into the independent replay schema.
    for case in cases.values():
        case.pop("_expected")
        case.pop("_active_start_id")
        case.pop("_cartesian_seen")
        case.pop("_best_seen")
        case.pop("_best_phase")
        points = tuple(
            reference.BlockPoint(
                reference.bits_to_float32(int(row["coordinate_bits"][0], 16)),
                reference.bits_to_float32(int(row["coordinate_bits"][1], 16)),
                row["cell_id"],
                row["vector_id"],
                bytes.fromhex(row["selection_digest"]),
            )
            for row in case["rows"]
        )
        replay_starts = []
        parser_step_distance_comparisons = 0
        for start_id in sorted(case["starts"]):
            start = case["starts"][start_id]
            start.pop("ended")
            start.pop("_phase")
            replay_steps = []
            for step in start["steps"]:
                centers = [
                    (
                        reference.bits_to_float64(int(center[0], 16)),
                        reference.bits_to_float64(int(center[1], 16)),
                    )
                    for center in step["centers_after_bits"]
                ]
                assignments, _, distance_comparisons = reference._assign_points(
                    points, centers
                )
                parser_step_distance_comparisons += distance_comparisons
                replay_steps.append(
                    {
                        "iteration": step["iteration"],
                        "prior_sse_bits": step["prior_sse_bits"],
                        "candidate_sse_bits": step["candidate_sse_bits"],
                        "changed_assignment_count": step["changed_assignment_count"],
                        "empty_center_ids": step["empty_center_ids"],
                        "centers_after_bits": step["centers_after_bits"],
                        "assignment_hash": reference.assignment_digest(assignments),
                    }
                )
            replay_starts.append(
                {
                    "start_id": start_id,
                    "first_seed_digest": start["first_seed_digest"],
                    "selected_vector_ids": start["selected_vector_ids"],
                    "initial_sse_bits": start["initial_sse_bits"],
                    "initial_centers_bits": start["initial_centers_bits"],
                    "final_sse_bits": start["final_sse_bits"],
                    "iterations": start["iterations"],
                    "assignment_hash": reference.assignment_digest(start["final_assignments"]),
                    "centers_bits": start["serialized_centers_bits"],
                    "final_assignments": start["final_assignments"],
                    "empty_events": sum(len(step["empty_center_ids"]) for step in start["steps"]),
                    "converged": start["converged"],
                    "steps": replay_steps,
                    "distance_comparison_count": start["distance_comparison_count"],
                    "assignment_tie_count": start["assignment_tie_count"],
                    "farthest_tie_count": start["farthest_tie_count"],
                }
            )
        case["native_starts"] = [case["starts"][start_id] for start_id in sorted(case["starts"])]
        case["starts"] = replay_starts
        case["best_start_id"] = case["best"].get("start_id")
        case["validation_parser_step_distance_comparison_count"] = (
            parser_step_distance_comparisons
        )
    return cases


def _parse_block_output(
    path: Path,
    *,
    requested_cases: Sequence[
        tuple[
            int,
            int,
            int,
            str,
            Sequence[Sequence[float]],
            Sequence[float],
            Sequence[float],
            Sequence[int],
        ]
    ],
    allow_control_invalid: bool = False,
) -> dict[int, dict[str, Any]]:
    try:
        return _parse_block_output_unchecked(
            path,
            requested_cases=requested_cases,
            allow_control_invalid=allow_control_invalid,
        )
    except GateFailure:
        raise
    except (
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        UnicodeError,
        OSError,
    ) as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", f"malformed block native output: {error}"
        ) from error


def _block_axes(
    rows: Sequence[Sequence[float]], capacity: int
) -> tuple[list[float], list[float]]:
    bits = [
        [reference.float32_bits(float(row[coordinate])) for row in rows]
        for coordinate in range(2)
    ]
    curves = [
        reference.exact_scalar_curve_reference(values, capacity)
        for values in bits
    ]
    allocation = reference.exact_product_allocation_reference(
        curves[0], curves[1], capacity, dyadic_only=False
    )
    axes: list[list[float]] = []
    for curve, cardinality in zip(curves, allocation.cardinalities):
        solution = curve.at(cardinality)
        axes.append(
            [
                reference.bits_to_float64(
                    reference.round_grid_mean_to_float64_bits(
                        cluster.sum_n, cluster.weight
                    )
                )
                for cluster in solution.clusters
            ]
        )
    return axes[0], axes[1]


def _reference_block_start_json(result: reference.BlockStartResult) -> dict[str, Any]:
    return {
        "start_id": result.start_id,
        "first_seed_digest": result.first_seed_digest,
        "selected_vector_ids": list(result.selected_vector_ids),
        "initial_sse_bits": _hex64(result.initial_sse_bits),
        "initial_centers_bits": [
            [_hex64(left), _hex64(right)] for left, right in result.initial_centers_bits
        ],
        "final_sse_bits": _hex64(result.final_sse_bits),
        "iterations": result.iterations,
        "assignment_hash": result.assignment_hash,
        "centers_bits": [
            [_hex32(left), _hex32(right)] for left, right in result.centers_bits
        ],
        "final_assignments": list(result.final_assignments),
        "empty_events": result.empty_events,
        "converged": result.converged,
        "distance_comparison_count": result.distance_comparison_count,
        "assignment_tie_count": result.assignment_tie_count,
        "farthest_tie_count": result.farthest_tie_count,
        "steps": [
            {
                "iteration": step.iteration,
                "prior_sse_bits": _hex64(step.prior_sse_bits),
                "candidate_sse_bits": _hex64(step.candidate_sse_bits),
                "changed_assignment_count": step.changed_assignment_count,
                "empty_center_ids": list(step.empty_center_ids),
                "centers_after_bits": [
                    [_hex64(left), _hex64(right)]
                    for left, right in step.centers_after_bits
                ],
                "assignment_hash": step.assignment_hash,
            }
            for step in result.steps
        ],
    }


def _run_block_parity(
    output_dir: Path, np: Any, representation_body: Mapping[str, Any]
) -> dict[str, Any]:
    micro_input = output_dir / ".block_micro_input.bin"
    micro_output = output_dir / ".block_micro_output.tsv"
    micro_cases = (
        (
            1000,
            2,
            0,
            "synthetic_block_micro_farthest",
            ((-1.0, 0.0), (1.0, 0.0)),
            (0.0,),
            (0.0,),
            (0, 1),
        ),
        (
            1001,
            3,
            0,
            "synthetic_block_micro_empty",
            ((0.0, 0.0), (0.0, 0.0), (1.0, 0.0)),
            (0.0,),
            (0.0,),
            (0, 1, 2),
        ),
    )
    _write_block_input(micro_input, micro_cases)
    _run_native(("block-suite", str(micro_input), str(micro_output)))
    micros = _parse_block_output(
        micro_output,
        requested_cases=micro_cases,
        allow_control_invalid=True,
    )
    micro_input.unlink()
    micro_output.unlink()
    farthest = micros[1000]
    empty = micros[1001]
    farthest_start0 = farthest["native_starts"][0]
    empty_start0 = empty["native_starts"][0]
    empty_retained = any(
        2 in step["empty_center_ids"]
        and step["centers_after_bits"][2] == empty_start0["initial_centers_bits"][2]
        for step in empty_start0["steps"]
    )
    microfixtures = {
        "equidistant_lower_codeword": bool(
            representation_body["native"]["checks"].get("equidistant_lower_codeword")
        ),
        "farthest_lower_vector_id": farthest_start0["selected_vector_ids"] == [0],
        "empty_center_retention": empty_retained,
        "cartesian_start_before_fill": (
            farthest["cartesian"]["center_count"] == 1
            and len(farthest_start0["initial_centers_bits"]) == 2
        ),
        "best_start_lower_id_tie": (
            farthest["best_start_id"] == 0
            and len({start["final_sse_bits"] for start in farthest["native_starts"]}) == 1
        ),
    }
    if not all(microfixtures.values()):
        raise GateFailure("CONTROL_INVALID", f"block microfixture failure: {microfixtures}")

    generator = np.random.Generator(np.random.PCG64(SEED))
    native_cases = []
    references: dict[int, tuple[reference.BlockStartResult, ...]] = {}
    case_metadata: dict[int, dict[str, Any]] = {}
    for case_id in range(64):
        row_count = 8 + case_id % 25
        capacity = 2 + case_id % 7
        array = generator.integers(-8, 9, size=(row_count, 2))
        rows = np.asarray(array, dtype=np.float32).tolist()
        dataset_id = f"synthetic_block_case_{case_id}"
        axis0, axis1 = _block_axes(rows, capacity)
        native_cases.append(
            (
                case_id,
                capacity,
                0,
                dataset_id,
                rows,
                axis0,
                axis1,
                tuple(index % 4 for index in range(row_count)),
            )
        )
        references[case_id] = reference.block_suite_reference(
            rows, capacity, SCIENTIFIC_PROTOCOL_VERSION, dataset_id, 0
        )
        raw = np.asarray(rows, dtype=np.float32).tobytes(order="C")
        case_metadata[case_id] = {
            "array_sha256": hashlib.sha256(raw).hexdigest(),
            "capacity": capacity,
            "dataset_id": dataset_id,
            "row_count": row_count,
            "start0_axis0_bits": [_hex64(reference.float64_bits(value)) for value in axis0],
            "start0_axis1_bits": [_hex64(reference.float64_bits(value)) for value in axis1],
        }

    block_input = output_dir / ".block_suite_input.bin"
    first_output = output_dir / ".block_suite_output_first.jsonl"
    second_output = output_dir / ".block_suite_output_second.jsonl"
    _write_block_input(block_input, native_cases)
    _run_native(("block-suite", str(block_input), str(first_output)))
    _run_native(("block-suite", str(block_input), str(second_output)))
    if first_output.read_bytes() != second_output.read_bytes():
        raise GateFailure("CONTROL_INVALID", "block repeated run is not bit-identical")
    optimized = _parse_block_output(first_output, requested_cases=native_cases)
    if set(optimized) != set(range(64)):
        raise GateFailure("CONTROL_INVALID", "block case inventory mismatch")

    records = []
    for case_id in range(64):
        actual = optimized[case_id]
        if not actual.get("control_valid"):
            raise GateFailure("CONTROL_INVALID", f"native block case {case_id} invalid")
        independent_starts = [
            _reference_block_start_json(value) for value in references[case_id]
        ]
        actual_starts = actual.get("starts")
        if actual_starts != independent_starts:
            raise GateFailure("CONTROL_INVALID", f"block replay mismatch case {case_id}")
        expected_cartesian_bits = [
            [left, right]
            for right in actual["axes"][1]
            for left in actual["axes"][0]
        ]
        if actual["cartesian"]["centers"] != expected_cartesian_bits:
            raise GateFailure(
                "CONTROL_INVALID",
                f"block Cartesian prefill order mismatch case {case_id}",
            )
        points = _block_points_from_native(actual)
        cartesian_centers = [
            (
                reference.bits_to_float64(int(bits[0], 16)),
                reference.bits_to_float64(int(bits[1], 16)),
            )
            for bits in expected_cartesian_bits
        ]
        _, cartesian_sse, _ = reference._assign_points(points, cartesian_centers)
        if (
            _hex64(reference.float64_bits(cartesian_sse))
            != actual["cartesian"]["sse_bits"]
            or actual["cartesian"]["filled_sse_bits"]
            != _hex64(references[case_id][0].initial_sse_bits)
        ):
            raise GateFailure(
                "CONTROL_INVALID",
                f"block Cartesian prefill SSE replay mismatch case {case_id}",
            )
        best_expected = min(
            references[case_id], key=lambda value: (value.final_sse_bits, value.start_id)
        ).start_id
        if actual.get("best_start_id") != best_expected:
            raise GateFailure("CONTROL_INVALID", f"block best-start mismatch case {case_id}")
        records.append(
            {
                **case_metadata[case_id],
                "case_id": case_id,
                "independent_starts": independent_starts,
                "optimized": actual,
                "repeated_run_equal": True,
                "cartesian_prefill_replay_match": True,
                "native_counter_parity": True,
            }
        )
    block_input.unlink()
    first_output.unlink()
    second_output.unlink()
    return {
        "artifact_kind": "block_vq_parity",
        "rng": {"algorithm": "PCG64", "seed": SEED, "stream_scope": "block_64_only"},
        "microfixtures": microfixtures,
        "cases": records,
        "case_count": len(records),
        "all_controls_valid": True,
        "all_repeated_runs_equal": True,
    }


def _cost_plan() -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for coordinate in range(128):
        plan.append(
            {
                "index": len(plan),
                "path": f"detail/scalar/coordinate_{coordinate:03d}.jsonl",
                "role": "scalar_curve_shard",
                "expected_record_count": 256,
            }
        )
    plan.append(
        {
            "index": len(plan),
            "path": "detail/allocations.jsonl",
            "role": "allocation_shard",
            "expected_record_count": 130,
        }
    )
    for word_bits in (4, 8):
        for group in range(64):
            plan.append(
                {
                    "index": len(plan),
                    "path": f"detail/block/group_{group:03d}_b{word_bits:02d}.jsonl",
                    "role": "block_vq_shard",
                    "expected_record_count": 9,
                }
            )
    for word_bits in (4, 8):
        plan.append(
            {
                "index": len(plan),
                "path": f"detail/encoding/rate_b{word_bits:02d}.jsonl",
                "role": "encoding_shard",
                "expected_record_count": 8192,
            }
        )
    if len(plan) != 259 or [entry["index"] for entry in plan] != list(range(259)):
        raise AssertionError("cost shard plan mismatch")
    return plan


_SCALAR_RECORD_KEYS = {
    "record_type", "coordinate_id", "requested_cardinality",
    "effective_cardinality", "fit_row_count", "distinct_support_size",
    "exact_sse", "partition", "exact_means", "binary32_centroid_bits",
    "binary32_centroid_bits_sha256", "binary64_centroid_bits",
    "binary64_centroid_bits_sha256", "predecessor_indices",
    "predecessor_indices_sha256", "comparison_count", "exact_tie_count",
    "exact_replay_sse", "exact_replay_match", "predecessors_nondecreasing",
    "serialized_binary32_strictly_increasing",
}
_BLOCK_METADATA_KEYS = {
    "record_type", "word_bits", "capacity", "group_id", "coordinates",
    "fit_row_count", "row_order_vector_ids", "row_order_vector_ids_sha256",
    "arbitrary_cardinalities", "arbitrary_used_states", "selected_start_id",
}
_BLOCK_START_KEYS = {
    "record_type", "word_bits", "capacity", "group_id", "start_id",
    "initialization_kind", "initialization_vector_ids",
    "initialization_vector_ids_sha256", "prefill_cartesian_centers_binary64_bits",
    "prefill_cartesian_centers_binary64_bits_sha256", "prefill_cartesian_sse_bits",
    "initial_centers_binary64_bits", "initial_centers_binary64_bits_sha256",
    "steps", "iteration_count", "accepted_update_count", "converged",
    "final_assignments", "final_assignments_sha256",
    "final_centers_binary64_bits", "final_centers_binary64_bits_sha256",
    "final_centers_binary32_bits", "final_centers_binary32_bits_sha256",
    "final_sse_bits", "distance_comparison_count", "assignment_tie_count",
    "farthest_tie_count", "serialized_distinct_center_count",
    "direct_replay_match", "cartesian_dominance_pass", "selected_best_start",
}
_BLOCK_STEP_KEYS = {
    "iteration", "prior_sse_bits", "candidate_sse_bits",
    "assignments_before_sha256", "assignments_after_sha256",
    "centers_after_binary64_bits_sha256", "changed_assignment_count",
    "empty_center_ids", "empty_center_ids_sha256", "accepted",
}
_GROUP_ALLOCATION_KEYS = {
    "record_type", "word_bits", "capacity", "group_id", "coordinates",
    "dyadic_word", "arbitrary_word",
}
_ALLOCATION_ARM_KEYS = {
    "requested_cardinalities", "effective_cardinalities", "used_states",
    "invalid_states", "exact_fitting_sse", "enumerated_candidate_count",
}
_GLOBAL_ALLOCATION_KEYS = {
    "record_type", "word_bits", "total_bit_budget", "bit_widths",
    "bit_widths_sha256", "cardinalities", "cardinalities_sha256",
    "used_bits", "exact_fitting_sse", "enumerated_transition_count",
}
_ENCODING_RECORD_KEYS = {"record_type", "word_bits", "vector_id", "arms"}
_ENCODING_ARM_KEY_SET = {
    "dyadic_word", "arbitrary_word", "trained_block_vq",
    "global_dyadic_pack_cap8",
}
_ENCODING_ARM_KEYS = {
    "label_count", "labels", "labels_sha256", "payload_bytes", "payload_hex",
    "payload_sha256", "alignment_bytes", "output_bytes", "roundtrip_labels",
    "roundtrip_labels_sha256", "roundtrip_match", "distance_comparison_count",
    "pack_operation_count", "unpack_operation_count",
}


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], description: str) -> None:
    if not isinstance(value, Mapping):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{description} is not an object")
    if set(value) != expected:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"{description} key set mismatch: missing={sorted(expected - set(value))}, "
            f"extra={sorted(set(value) - expected)}",
        )


def _require_array_hash(record: Mapping[str, Any], field: str) -> None:
    _json_sha256(record.get(f"{field}_sha256"), f"{field}_sha256")
    expected = _sha256_canonical_array(record[field])
    if record.get(f"{field}_sha256") != expected:
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} canonical hash mismatch")


def _json_id_array(
    value: Any,
    field: str,
    *,
    length: int | None = None,
    minimum: int = 0,
    maximum: int | None = None,
) -> list[int]:
    if not isinstance(value, list) or (length is not None and len(value) != length):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} array shape mismatch")
    for index, item in enumerate(value):
        _json_int(item, f"{field}[{index}]", minimum=minimum, maximum=maximum)
    return value


def _json_bits_array(
    value: Any,
    width: int,
    field: str,
    *,
    length: int | None = None,
) -> list[str]:
    if not isinstance(value, list) or (length is not None and len(value) != length):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} array shape mismatch")
    for index, item in enumerate(value):
        _json_bits(item, width, f"{field}[{index}]")
    return value


def _json_center_bits_array(
    value: Any,
    width: int,
    field: str,
    *,
    length: int | None = None,
) -> list[list[str]]:
    if not isinstance(value, list) or (length is not None and len(value) != length):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{field} center-array shape mismatch")
    for index, center in enumerate(value):
        _json_bits_array(center, width, f"{field}[{index}]", length=2)
    return value


def _validate_cost_record_unchecked(
    plan_entry: Mapping[str, Any], index: int, record: Mapping[str, Any]
) -> None:
    role = str(plan_entry["role"])
    plan_index = _json_int(plan_entry["index"], "cost plan index", maximum=258)
    if not isinstance(record, Mapping):
        raise GateFailure("IMPLEMENTATION_INVALID", f"{role} record is not an object")
    if role == "scalar_curve_shard":
        _require_exact_keys(record, _SCALAR_RECORD_KEYS, "scalar record")
        coordinate_id = _json_int(record["coordinate_id"], "scalar coordinate_id", maximum=127)
        requested = _json_int(
            record["requested_cardinality"],
            "scalar requested_cardinality",
            minimum=1,
            maximum=256,
        )
        effective = _json_int(
            record["effective_cardinality"],
            "scalar effective_cardinality",
            minimum=1,
            maximum=256,
        )
        support_size = _json_int(
            record["distinct_support_size"],
            "scalar distinct_support_size",
            minimum=1,
            maximum=FULL_ROWS,
        )
        if (
            record["record_type"] != "scalar_curve"
            or requested != index + 1
            or record["fit_row_count"] != FULL_ROWS
            or isinstance(record["fit_row_count"], bool)
            or effective != min(requested, support_size)
        ):
            raise GateFailure("IMPLEMENTATION_INVALID", "scalar record order/type mismatch")
        if coordinate_id != plan_index:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "scalar record is bound to the wrong shard"
            )
        length = effective
        if not isinstance(record["partition"], list) or not isinstance(record["exact_means"], list):
            raise GateFailure("IMPLEMENTATION_INVALID", "scalar partition/mean is not an array")
        if not (
            len(record["partition"]) == length
            and len(record["exact_means"]) == length
            and len(record["binary32_centroid_bits"]) == length
            and len(record["binary64_centroid_bits"]) == length
        ):
            raise GateFailure("IMPLEMENTATION_INVALID", "scalar record array length mismatch")
        prior_end = 0
        for cluster_id, interval in enumerate(record["partition"]):
            _require_exact_keys(interval, {"begin", "end"}, "scalar interval")
            begin = _json_int(interval["begin"], f"scalar interval {cluster_id} begin")
            end = _json_int(interval["end"], f"scalar interval {cluster_id} end")
            if begin != prior_end or end <= begin or end > support_size:
                raise GateFailure("IMPLEMENTATION_INVALID", "scalar partition is not contiguous")
            prior_end = end
        if prior_end != support_size:
            raise GateFailure("IMPLEMENTATION_INVALID", "scalar partition does not cover support")
        for mean_id, mean in enumerate(record["exact_means"]):
            _json_exact_rational(
                mean, f"scalar exact_mean[{mean_id}]", exponent=-149, signed=True
            )
        _json_bits_array(record["binary32_centroid_bits"], 32, "scalar binary32 centroids", length=length)
        _json_bits_array(record["binary64_centroid_bits"], 64, "scalar binary64 centroids", length=length)
        _json_id_array(
            record["predecessor_indices"],
            "scalar predecessor_indices",
            length=support_size + 1,
            maximum=support_size,
        )
        for field in (
            "binary32_centroid_bits",
            "binary64_centroid_bits",
            "predecessor_indices",
        ):
            _require_array_hash(record, field)
        _json_exact_rational(record["exact_sse"], "scalar exact_sse", exponent=-298, signed=False)
        _json_exact_rational(
            record["exact_replay_sse"],
            "scalar exact_replay_sse",
            exponent=-298,
            signed=False,
        )
        _json_count(record["comparison_count"], "scalar comparison_count")
        _json_count(record["exact_tie_count"], "scalar exact_tie_count")
        for field in (
            "exact_replay_match",
            "predecessors_nondecreasing",
            "serialized_binary32_strictly_increasing",
        ):
            _json_boolean(record[field], f"scalar {field}")
        if (
            record["exact_sse"] != record["exact_replay_sse"]
            or record["exact_replay_match"] is not True
            or record["predecessors_nondecreasing"] is not True
        ):
            raise GateFailure("IMPLEMENTATION_INVALID", "scalar exact replay mismatch")
    elif role == "allocation_shard":
        if plan_index != 128:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "allocation shard plan index is invalid"
            )
        if index < 128:
            _require_exact_keys(record, _GROUP_ALLOCATION_KEYS, "group allocation")
            expected_word_bits = 4 if index < 64 else 8
            expected_group = index % 64
            word_bits = _json_int(record["word_bits"], "group allocation word_bits")
            capacity = _json_int(record["capacity"], "group allocation capacity")
            group_id = _json_int(record["group_id"], "group allocation group_id", maximum=63)
            coordinates = _json_id_array(
                record["coordinates"], "group allocation coordinates", length=2, maximum=127
            )
            if (
                record["record_type"] != "group_allocation"
                or word_bits != expected_word_bits
                or capacity != 1 << word_bits
                or group_id != expected_group
                or coordinates != [2 * group_id, 2 * group_id + 1]
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "group allocation order mismatch")
            for name in ("dyadic_word", "arbitrary_word"):
                arm = record[name]
                _require_exact_keys(arm, _ALLOCATION_ARM_KEYS, f"{name} allocation")
                requested = _json_id_array(
                    arm["requested_cardinalities"],
                    f"{name} requested_cardinalities",
                    length=2,
                    minimum=1,
                    maximum=capacity,
                )
                effective = _json_id_array(
                    arm["effective_cardinalities"],
                    f"{name} effective_cardinalities",
                    length=2,
                    minimum=1,
                    maximum=capacity,
                )
                used_states = _json_int(arm["used_states"], f"{name} used_states", minimum=1)
                invalid_states = _json_int(arm["invalid_states"], f"{name} invalid_states")
                _json_exact_rational(
                    arm["exact_fitting_sse"],
                    f"{name} exact_fitting_sse",
                    exponent=-298,
                    signed=False,
                )
                if (
                    any(observed > nominal for observed, nominal in zip(effective, requested))
                    or used_states != requested[0] * requested[1]
                    or used_states + invalid_states != capacity
                    or (name == "dyadic_word" and any(value & (value - 1) for value in requested))
                    or _json_count(
                        arm["enumerated_candidate_count"],
                        f"{name} enumerated_candidate_count",
                    )
                    <= 0
                ):
                    raise GateFailure("IMPLEMENTATION_INVALID", "allocation cardinality shape mismatch")
        else:
            _require_exact_keys(record, _GLOBAL_ALLOCATION_KEYS, "global allocation")
            expected_word_bits = 4 if index == 128 else 8
            word_bits = _json_int(record["word_bits"], "global allocation word_bits")
            budget = _json_int(record["total_bit_budget"], "global allocation bit budget")
            widths = _json_id_array(
                record["bit_widths"], "global allocation bit_widths", length=128, maximum=8
            )
            cardinalities = _json_id_array(
                record["cardinalities"],
                "global allocation cardinalities",
                length=128,
                minimum=1,
                maximum=256,
            )
            used_bits = _json_int(record["used_bits"], "global allocation used_bits")
            if (
                index not in (128, 129)
                or record["record_type"] != "global_allocation"
                or word_bits != expected_word_bits
                or budget != 64 * word_bits
                or cardinalities != [1 << width for width in widths]
                or used_bits != sum(widths)
                or used_bits > budget
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "global allocation order mismatch")
            _json_exact_rational(
                record["exact_fitting_sse"],
                "global allocation exact_fitting_sse",
                exponent=-298,
                signed=False,
            )
            if _json_count(
                record["enumerated_transition_count"],
                "global allocation enumerated_transition_count",
            ) <= 0:
                raise GateFailure("IMPLEMENTATION_INVALID", "global allocation transition count mismatch")
            _require_array_hash(record, "bit_widths")
            _require_array_hash(record, "cardinalities")
    elif role == "block_vq_shard":
        if not 129 <= plan_index <= 256:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "block shard plan index is invalid"
            )
        expected_word_bits = 4 if plan_index < 193 else 8
        expected_group_id = (plan_index - 129) % FULL_GROUP_COUNT
        if index == 0:
            _require_exact_keys(record, _BLOCK_METADATA_KEYS, "block metadata")
            if record["record_type"] != "block_metadata":
                raise GateFailure("IMPLEMENTATION_INVALID", "block metadata must be first")
            word_bits = _json_int(record["word_bits"], "block metadata word_bits")
            capacity = _json_int(record["capacity"], "block metadata capacity")
            group_id = _json_int(record["group_id"], "block metadata group_id", maximum=63)
            row_ids = _json_id_array(
                record["row_order_vector_ids"],
                "block row_order_vector_ids",
                length=FULL_ROWS,
                maximum=FULL_ROWS - 1,
            )
            cardinalities = _json_id_array(
                record["arbitrary_cardinalities"],
                "block arbitrary_cardinalities",
                length=2,
                minimum=1,
                maximum=capacity,
            )
            if (
                word_bits != expected_word_bits
                or capacity != 1 << word_bits
                or group_id != expected_group_id
                or record["coordinates"] != [2 * group_id, 2 * group_id + 1]
                or record["fit_row_count"] != FULL_ROWS
                or isinstance(record["fit_row_count"], bool)
                or len(set(row_ids)) != FULL_ROWS
                or _json_int(record["arbitrary_used_states"], "block arbitrary_used_states")
                != cardinalities[0] * cardinalities[1]
                or _json_int(
                    record["selected_start_id"],
                    "block selected_start_id",
                    maximum=BLOCK_START_COUNT - 1,
                )
                not in range(BLOCK_START_COUNT)
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block metadata shape mismatch")
            _json_id_array(
                record["coordinates"], "block metadata coordinates", length=2, maximum=127
            )
            _require_array_hash(record, "row_order_vector_ids")
        else:
            _require_exact_keys(record, _BLOCK_START_KEYS, "block start")
            word_bits = _json_int(record["word_bits"], "block start word_bits")
            capacity = _json_int(record["capacity"], "block start capacity")
            group_id = _json_int(record["group_id"], "block start group_id", maximum=63)
            start_id = _json_int(
                record["start_id"], "block start_id", maximum=BLOCK_START_COUNT - 1
            )
            if (
                record["record_type"] != "block_start"
                or start_id != index - 1
                or word_bits != expected_word_bits
                or capacity != 1 << word_bits
                or group_id != expected_group_id
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block start order mismatch")
            expected_kind = "cartesian_fill" if start_id == 0 else "hashed_farthest_first"
            if record["initialization_kind"] != expected_kind:
                raise GateFailure("IMPLEMENTATION_INVALID", "block initialization kind mismatch")
            initialization_ids = _json_id_array(
                record["initialization_vector_ids"],
                "block initialization_vector_ids",
                maximum=FULL_ROWS - 1,
            )
            if (
                len(initialization_ids) != len(set(initialization_ids))
                or (start_id > 0 and len(initialization_ids) != capacity)
                or len(initialization_ids) > capacity
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "block initialization IDs are not distinct")
            if not isinstance(record["steps"], list):
                raise GateFailure("IMPLEMENTATION_INVALID", "block steps is not an array")
            iteration_count = _json_int(record["iteration_count"], "block iteration_count")
            accepted_count = _json_int(record["accepted_update_count"], "block accepted_update_count")
            if iteration_count != len(record["steps"]) or accepted_count != len(record["steps"]):
                raise GateFailure("IMPLEMENTATION_INVALID", "block step count mismatch")
            _json_boolean(record["converged"], "block converged")
            if record["converged"] is not True:
                raise GateFailure("IMPLEMENTATION_INVALID", "published block start did not converge")
            _json_center_bits_array(
                record["initial_centers_binary64_bits"],
                64,
                "block initial centers",
                length=capacity,
            )
            _json_id_array(
                record["final_assignments"],
                "block final_assignments",
                length=FULL_ROWS,
                maximum=capacity - 1,
            )
            _json_center_bits_array(
                record["final_centers_binary64_bits"],
                64,
                "block final binary64 centers",
                length=capacity,
            )
            _json_center_bits_array(
                record["final_centers_binary32_bits"],
                32,
                "block final binary32 centers",
                length=capacity,
            )
            _json_bits(record["final_sse_bits"], 64, "block final SSE")
            for field in (
                "distance_comparison_count",
                "assignment_tie_count",
                "farthest_tie_count",
            ):
                _json_count(record[field], f"block {field}")
            if _json_int(
                record["serialized_distinct_center_count"],
                "block serialized distinct centers",
            ) != capacity:
                raise GateFailure("IMPLEMENTATION_INVALID", "block serialized center count mismatch")
            for field in (
                "direct_replay_match",
                "cartesian_dominance_pass",
                "selected_best_start",
            ):
                _json_boolean(record[field], f"block {field}")
            if record["direct_replay_match"] is not True:
                raise GateFailure("IMPLEMENTATION_INVALID", "block direct replay mismatch")
            for field in (
                "initialization_vector_ids",
                "initial_centers_binary64_bits",
                "final_assignments",
                "final_centers_binary64_bits",
                "final_centers_binary32_bits",
            ):
                _require_array_hash(record, field)
            if record["prefill_cartesian_centers_binary64_bits"] is None:
                if (
                    start_id == 0
                    or record["prefill_cartesian_centers_binary64_bits_sha256"] is not None
                    or record["prefill_cartesian_sse_bits"] is not None
                ):
                    raise GateFailure("IMPLEMENTATION_INVALID", "partial null block prefill fields")
            else:
                if start_id != 0:
                    raise GateFailure("IMPLEMENTATION_INVALID", "nonnull block prefill on salted start")
                _json_center_bits_array(
                    record["prefill_cartesian_centers_binary64_bits"],
                    64,
                    "block Cartesian prefill centers",
                )
                _json_sha256(
                    record["prefill_cartesian_centers_binary64_bits_sha256"],
                    "block Cartesian prefill hash",
                )
                _json_bits(record["prefill_cartesian_sse_bits"], 64, "block Cartesian prefill SSE")
                if (
                    len(record["prefill_cartesian_centers_binary64_bits"])
                    + len(initialization_ids)
                    != capacity
                ):
                    raise GateFailure("IMPLEMENTATION_INVALID", "block Cartesian/fill count mismatch")
                if record["prefill_cartesian_centers_binary64_bits_sha256"] != _sha256_canonical_array(record["prefill_cartesian_centers_binary64_bits"]):
                    raise GateFailure("IMPLEMENTATION_INVALID", "block prefill hash mismatch")
            for step_index, step in enumerate(record["steps"], start=1):
                _require_exact_keys(step, _BLOCK_STEP_KEYS, "block step")
                _json_int(step["iteration"], "block step iteration", minimum=1)
                _json_bits(step["prior_sse_bits"], 64, "block step prior SSE")
                _json_bits(step["candidate_sse_bits"], 64, "block step candidate SSE")
                for field in (
                    "assignments_before_sha256",
                    "assignments_after_sha256",
                    "centers_after_binary64_bits_sha256",
                ):
                    _json_sha256(step[field], f"block step {field}")
                _json_int(step["changed_assignment_count"], "block changed assignments", maximum=FULL_ROWS)
                _json_id_array(
                    step["empty_center_ids"],
                    "block empty_center_ids",
                    maximum=capacity - 1,
                )
                _json_boolean(step["accepted"], "block step accepted")
                if step["iteration"] != step_index or step["accepted"] is not True:
                    raise GateFailure("IMPLEMENTATION_INVALID", "block step order/acceptance mismatch")
                _require_array_hash(step, "empty_center_ids")
    elif role == "encoding_shard":
        if plan_index not in (257, 258):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "encoding shard plan index is invalid"
            )
        expected_word_bits = 4 if plan_index == 257 else 8
        _require_exact_keys(record, _ENCODING_RECORD_KEYS, "encoding record")
        word_bits = _json_int(record["word_bits"], "encoding word_bits")
        vector_id = _json_int(record["vector_id"], "encoding vector_id", maximum=FULL_ROWS - 1)
        if (
            record["record_type"] != "encoded_vector"
            or vector_id != index
            or word_bits != expected_word_bits
        ):
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding record order/type mismatch")
        arms = record["arms"]
        _require_exact_keys(arms, _ENCODING_ARM_KEY_SET, "encoding arms")
        paid_bytes = 32 if record["word_bits"] == 4 else 64
        for name, arm in arms.items():
            _require_exact_keys(arm, _ENCODING_ARM_KEYS, f"{name} encoding arm")
            expected_labels = 128 if name == "global_dyadic_pack_cap8" else 64
            label_count = _json_int(arm["label_count"], f"{name} label_count")
            labels = _json_id_array(
                arm["labels"], f"{name} labels", length=expected_labels, maximum=255
            )
            roundtrip_labels = _json_id_array(
                arm["roundtrip_labels"],
                f"{name} roundtrip_labels",
                length=expected_labels,
                maximum=255,
            )
            payload_bytes = _json_int(arm["payload_bytes"], f"{name} payload_bytes")
            if (
                not isinstance(arm["payload_hex"], str)
                or re.fullmatch(r"[0-9a-f]*", arm["payload_hex"]) is None
                or len(arm["payload_hex"]) != 2 * payload_bytes
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "encoding payload is not lowercase hex")
            _json_sha256(arm["payload_sha256"], f"{name} payload_sha256")
            _json_sha256(arm["labels_sha256"], f"{name} labels_sha256")
            _json_sha256(
                arm["roundtrip_labels_sha256"], f"{name} roundtrip_labels_sha256"
            )
            _json_boolean(arm["roundtrip_match"], f"{name} roundtrip_match")
            alignment = _json_int(arm["alignment_bytes"], f"{name} alignment_bytes")
            output_bytes = _json_int(arm["output_bytes"], f"{name} output_bytes")
            try:
                payload = bytes.fromhex(arm["payload_hex"])
            except (TypeError, ValueError) as error:
                raise GateFailure("IMPLEMENTATION_INVALID", "encoding payload is not lowercase hex") from error
            if (
                label_count != expected_labels
                or labels != roundtrip_labels
                or payload_bytes != paid_bytes
                or len(payload) != paid_bytes
                or payload.hex() != arm["payload_hex"]
                or hashlib.sha256(payload).hexdigest() != arm["payload_sha256"]
                or alignment != 1
                or output_bytes != paid_bytes
                or arm["pack_operation_count"] != "1"
                or arm["unpack_operation_count"] != "1"
                or _json_count(
                    arm["distance_comparison_count"],
                    f"{name} distance_comparison_count",
                )
                <= 0
                or _json_count(arm["pack_operation_count"], f"{name} pack_operation_count")
                != 1
                or _json_count(
                    arm["unpack_operation_count"], f"{name} unpack_operation_count"
                )
                != 1
                or arm["roundtrip_match"] is not True
                or arm["labels_sha256"] != _sha256_canonical_array(arm["labels"])
                or arm["roundtrip_labels_sha256"] != _sha256_canonical_array(arm["roundtrip_labels"])
            ):
                raise GateFailure("IMPLEMENTATION_INVALID", "encoding arm shape/payload mismatch")
            if name != "global_dyadic_pack_cap8" and any(
                label >= (1 << record["word_bits"]) for label in arm["labels"]
            ):
                raise GateFailure(
                    "IMPLEMENTATION_INVALID", "matched encoding label is invalid"
                )
    else:
        raise GateFailure("IMPLEMENTATION_INVALID", f"unknown cost shard role {role}")


def _validate_cost_record(
    plan_entry: Mapping[str, Any], index: int, record: Mapping[str, Any]
) -> None:
    role = str(plan_entry.get("role"))
    try:
        _validate_cost_record_unchecked(plan_entry, index, record)
    except GateFailure:
        raise
    except (
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
    ) as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"malformed {role} record {index}: {error}",
        ) from error


def _records_with_supervisor_hwm(
    records: Iterable[Mapping[str, Any]],
    *,
    counters: dict[str, Any],
    persistent_roots: Sequence[Any],
) -> Iterator[Mapping[str, Any]]:
    """Charge the current record and canonical line alongside live roots."""

    for record in records:
        canonical_line_bytes = len(artifacts.canonical_json_bytes(record)) + 1
        _update_supervisor_owned_buffer_hwm(
            counters,
            "shard_serialization",
            *persistent_roots,
            record,
            transient_payload_bytes=canonical_line_bytes,
        )
        yield record


def _publish_jsonl_shard(
    output_dir: Path,
    plan_entry: Mapping[str, Any],
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    path = output_dir / str(plan_entry["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists() or path.exists():
        raise GateFailure("IMPLEMENTATION_INVALID", f"cost shard already exists: {path}")
    role = str(plan_entry["role"])

    def checked_records() -> Iterator[Mapping[str, Any]]:
        for index, record in enumerate(records):
            _validate_cost_record(plan_entry, index, record)
            yield record

    identity = artifacts.write_canonical_json_lines(temporary, checked_records())
    expected = int(plan_entry["expected_record_count"])
    if identity.record_count != expected:
        temporary.unlink(missing_ok=True)
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"cost shard {plan_entry['path']} has {identity.record_count}, expected {expected}",
        )
    os.replace(temporary, path)
    return {
        "index": int(plan_entry["index"]),
        "path": str(plan_entry["path"]),
        "role": str(plan_entry["role"]),
        "record_count": expected,
        "size_bytes": identity.size_bytes,
        "sha256": identity.sha256,
    }


def _checkpoint(
    *,
    phase: str,
    completed_operation_count: int,
    last_completed_plan_index: int,
    cumulative_cpu_microseconds: int,
    reason_code: str,
    message: str,
    **overrides: Any,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "phase": phase,
        "completed_operation_count": completed_operation_count,
        "last_completed_plan_index": last_completed_plan_index,
        "cumulative_cpu_microseconds": cumulative_cpu_microseconds,
        "reason_code": reason_code,
        "message": message,
        "path": None,
        "coordinate_id": None,
        "word_bits": None,
        "group_id": None,
        "start_id": None,
        "arm": None,
        "requested_cardinality": None,
        "effective_cardinality": None,
        "first_colliding_label": None,
        "prior_sse_bits": None,
        "candidate_sse_bits": None,
        "center_count": None,
        "distinct_center_count": None,
        "expected_sha256": None,
        "observed_sha256": None,
    }
    unknown = set(overrides) - set(value)
    if unknown:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"unknown checkpoint keys: {sorted(unknown)}",
        )
    value.update(overrides)
    return value


def _load_checkpoint_json_object(path: Path) -> dict[str, Any]:
    """Load committed parity JSON and map every decode/schema fault to the gate."""

    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"cannot decode committed parity JSON {path.name}: {error}",
        ) from error
    if not isinstance(value, dict):
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"committed parity JSON must be an object: {path.name}",
        )
    try:
        canonical_payload = artifacts.canonical_json_bytes(value) + b"\n"
    except artifacts.ArtifactContractError as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"committed parity JSON violates canonical schema {path.name}: {error}",
        ) from error
    if payload != canonical_payload:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"committed parity JSON is not canonical: {path.name}",
        )
    return value


def _load_and_validate_parity_checkpoint(
    execution_commit: str,
    current_runtime: Mapping[str, Any],
) -> tuple[str, str, str, list[dict[str, Any]], dict[str, Any], int]:
    required = [COMMITTED_PARITY_DIR / name for name in PARITY_FILENAMES]
    required.extend((COMMITTED_PARITY_DIR / "parity_artifact_index.json", PARITY_REVIEW_PATH))
    for path in required:
        try:
            artifacts.guard_synthetic_read_path(
                path,
                repo_root=REPO_ROOT,
                allowed_files=required,
                extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
                require_allowlist_match=True,
            )
        except artifacts.ArtifactContractError as error:
            raise GateFailure(
                "ARTIFACT_INVALID",
                f"forbidden parity evidence read {path}: {error}",
            ) from error
        if not path.is_file():
            raise GateFailure("IMPLEMENTATION_INVALID", f"missing committed parity evidence: {path}")
        relative = path.relative_to(REPO_ROOT).as_posix()
        try:
            artifacts.git_blob_oid(REPO_ROOT, relative, commit=execution_commit)
        except artifacts.ArtifactContractError as error:
            raise GateFailure("IMPLEMENTATION_INVALID", f"parity evidence is not committed: {relative}") from error

    loaded = {
        filename: _load_checkpoint_json_object(COMMITTED_PARITY_DIR / filename)
        for filename in PARITY_FILENAMES
    }
    build = loaded["build_manifest.json"]
    index = _load_checkpoint_json_object(
        COMMITTED_PARITY_DIR / "parity_artifact_index.json"
    )
    implementation_commit = build.get("implementation_commit")
    try:
        implementation_commit = artifacts.validate_commit(implementation_commit)
        parity_evidence_commit = artifacts.git_last_modified_commit(
            REPO_ROOT,
            (COMMITTED_PARITY_DIR / "parity_artifact_index.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            commit=execution_commit,
        )
        parity_review_commit = artifacts.git_last_modified_commit(
            REPO_ROOT,
            PARITY_REVIEW_PATH.relative_to(REPO_ROOT).as_posix(),
            commit=execution_commit,
        )
        commit_chain = (
            (implementation_commit, parity_evidence_commit, "implementation/evidence"),
            (parity_evidence_commit, parity_review_commit, "evidence/review"),
            (parity_review_commit, execution_commit, "review/execution"),
        )
        for chain_index, (ancestor, descendant, label) in enumerate(commit_chain):
            if (
                not artifacts.git_commit_is_ancestor(REPO_ROOT, ancestor, descendant)
                or (chain_index < 2 and ancestor == descendant)
            ):
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    f"parity commit ancestry is invalid at {label}",
                )
        evidence_index_blob = artifacts.git_blob_oid(
            REPO_ROOT,
            (COMMITTED_PARITY_DIR / "parity_artifact_index.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            commit=parity_evidence_commit,
        )
        execution_index_blob = artifacts.git_blob_oid(
            REPO_ROOT,
            (COMMITTED_PARITY_DIR / "parity_artifact_index.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            commit=execution_commit,
        )
        review_commit_blob = artifacts.git_blob_oid(
            REPO_ROOT,
            PARITY_REVIEW_PATH.relative_to(REPO_ROOT).as_posix(),
            commit=parity_review_commit,
        )
        execution_review_blob = artifacts.git_blob_oid(
            REPO_ROOT,
            PARITY_REVIEW_PATH.relative_to(REPO_ROOT).as_posix(),
            commit=execution_commit,
        )
        if evidence_index_blob != execution_index_blob:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "parity artifact index changed after its evidence commit",
            )
        if review_commit_blob != execution_review_blob:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "parity review changed after its review commit",
            )
    except artifacts.ArtifactContractError as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"cannot bind parity commit ancestry: {error}",
        ) from error

    expected_common = {
        "schema_version": artifacts.SCHEMA_VERSION,
        "protocol_version": artifacts.PROTOCOL_VERSION,
        "stage": artifacts.STAGE,
        "status": "PASS_PARITY",
        "parent_preregistration_commit": artifacts.PARENT_PREREGISTRATION_COMMIT,
        "implementation_commit": implementation_commit,
        "execution_commit": implementation_commit,
    }
    expected_kinds = {
        "build_manifest.json": "build_manifest",
        "scalar_exact_parity.json": "scalar_exact_parity",
        "representation_parity.json": "representation_parity",
        "block_vq_parity.json": "block_vq_parity",
        "parity_summary.json": "parity_summary",
        "parity_artifact_index.json": "artifact_index",
    }
    common_reference: dict[str, Any] | None = None
    for filename, value in {**loaded, "parity_artifact_index.json": index}.items():
        for key, expected in expected_common.items():
            if type(value.get(key)) is not type(expected) or value.get(key) != expected:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    f"parity common field mismatch {filename}:{key}",
                )
        if value.get("artifact_kind") != expected_kinds[filename]:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"parity artifact kind mismatch: {filename}",
            )
        command = value.get("command")
        environment = value.get("thread_environment")
        input_ledger = value.get("input_ledger")
        output_ledger = value.get("output_ledger")
        if (
            not isinstance(command, list)
            or not command
            or any(not isinstance(item, str) or not item for item in command)
            or not isinstance(environment, dict)
            or any(
                not isinstance(key, str) or not isinstance(item, str)
                for key, item in environment.items()
            )
            or not isinstance(input_ledger, list)
            or any(not isinstance(entry, dict) for entry in input_ledger)
            or output_ledger != []
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"parity common schema mismatch: {filename}",
            )
        try:
            normalized_common = artifacts.common_artifact_fields(
                status=value["status"],
                implementation_commit=value["implementation_commit"],
                execution_commit=value["execution_commit"],
                command=command,
                thread_environment=environment,
                input_ledger=input_ledger,
                output_ledger=output_ledger,
                parent_preregistration_commit=value[
                    "parent_preregistration_commit"
                ],
            )
        except (artifacts.ArtifactContractError, TypeError, ValueError) as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"parity common schema mismatch {filename}: {error}",
            ) from error
        if any(value.get(key) != normalized for key, normalized in normalized_common.items()):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"parity common fields are not canonical: {filename}",
            )
        if common_reference is None:
            common_reference = normalized_common
        elif normalized_common != common_reference:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"parity common fields disagree: {filename}",
            )
    if build.get("status") != "PASS_PARITY" or index.get("status") != "PASS_PARITY":
        raise GateFailure("IMPLEMENTATION_INVALID", "parity checkpoint status mismatch")

    scalar = loaded["scalar_exact_parity.json"]
    representation = loaded["representation_parity.json"]
    block = loaded["block_vq_parity.json"]
    summary = loaded["parity_summary.json"]
    full_allocation_digest = representation.get("full_allocation_digest")
    if (
        not isinstance(scalar.get("cases"), list)
        or scalar.get("all_exact_equal") is not True
        or scalar.get("all_replays_equal") is not True
        or scalar.get("all_predecessors_monotone") is not True
        or not isinstance(full_allocation_digest, dict)
        or full_allocation_digest.get("equal") is not True
        or full_allocation_digest.get("independent_sha256")
        != full_allocation_digest.get("optimized_sha256")
        or not isinstance(block.get("cases"), list)
        or block.get("all_controls_valid") is not True
        or block.get("all_repeated_runs_equal") is not True
        or summary.get("outcome") != "PASS_PARITY"
        or summary.get("representation_passed") is not True
        or summary.get("a4_0_tests_passed") is not True
        or summary.get("status_precedence_checked") is not True
        or summary.get("status_precedence_fixture")
        != _status_precedence_fixture()
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "parity pass-evidence schema mismatch"
        )

    current_contract_ledger = _input_ledger()
    if build.get("input_ledger") != current_contract_ledger:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "contract hashes changed since parity"
        )
    for entry in current_contract_ledger:
        try:
            implementation_blob = artifacts.git_blob_oid(
                REPO_ROOT, entry["path"], commit=implementation_commit
            )
            execution_blob = artifacts.git_blob_oid(
                REPO_ROOT, entry["path"], commit=execution_commit
            )
            last_contract_change = artifacts.git_last_modified_commit(
                REPO_ROOT, entry["path"], commit=execution_commit
            )
            contract_unchanged = artifacts.git_commit_is_ancestor(
                REPO_ROOT, last_contract_change, implementation_commit
            )
        except artifacts.ArtifactContractError as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"contract is not a regular committed Git blob: {entry['path']}",
            ) from error
        if implementation_blob != execution_blob or not contract_unchanged:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"contract Git blob changed after parity: {entry['path']}",
            )

    entries = index.get("artifacts")
    if not isinstance(entries, list) or len(entries) != 5:
        raise GateFailure("IMPLEMENTATION_INVALID", "parity index inventory mismatch")
    by_path: dict[str, dict[str, Any]] = {}
    expected_index_entry_fields = {
        "path",
        "producer_execution_commit",
        "schema_version",
        "sha256",
        "size_bytes",
    }
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != expected_index_entry_fields:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "parity index entry schema mismatch"
            )
        path = entry.get("path")
        if not isinstance(path, str) or not path or path in by_path:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "parity index contains a non-string or duplicate path",
            )
        if (
            not isinstance(entry.get("sha256"), str)
            or not isinstance(entry.get("size_bytes"), int)
            or isinstance(entry.get("size_bytes"), bool)
            or not isinstance(entry.get("schema_version"), int)
            or isinstance(entry.get("schema_version"), bool)
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", f"parity index identity schema mismatch: {path}"
            )
        by_path[path] = entry
    if set(by_path) != set(PARITY_FILENAMES):
        raise GateFailure("IMPLEMENTATION_INVALID", "parity index filenames mismatch")
    for filename in PARITY_FILENAMES:
        identity = artifacts.file_identity(COMMITTED_PARITY_DIR / filename)
        entry = by_path[filename]
        if entry.get("sha256") != identity.sha256 or entry.get("size_bytes") != identity.size_bytes:
            raise GateFailure("IMPLEMENTATION_INVALID", f"parity artifact hash mismatch: {filename}")
        if entry.get("producer_execution_commit") != implementation_commit or entry.get("schema_version") != 1:
            raise GateFailure("IMPLEMENTATION_INVALID", f"parity producer mismatch: {filename}")
        relative = (COMMITTED_PARITY_DIR / filename).relative_to(REPO_ROOT).as_posix()
        try:
            evidence_blob = artifacts.git_blob_oid(
                REPO_ROOT, relative, commit=parity_evidence_commit
            )
            execution_blob = artifacts.git_blob_oid(
                REPO_ROOT, relative, commit=execution_commit
            )
            last_artifact_change = artifacts.git_last_modified_commit(
                REPO_ROOT, relative, commit=execution_commit
            )
            artifact_unchanged = artifacts.git_commit_is_ancestor(
                REPO_ROOT, last_artifact_change, parity_evidence_commit
            )
        except artifacts.ArtifactContractError as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"parity artifact was not committed with the evidence: {filename}",
            ) from error
        if evidence_blob != execution_blob or not artifact_unchanged:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"parity artifact changed after evidence commit: {filename}",
            )

    source_entries = build.get("sources")
    if not isinstance(source_entries, list) or len(source_entries) != len(SOURCE_PATHS):
        raise GateFailure("IMPLEMENTATION_INVALID", "build source manifest missing")
    source_paths: list[str] = []
    for entry in source_entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size_bytes"}:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "build source entry schema mismatch"
            )
        path = entry.get("path")
        if (
            not isinstance(path, str)
            or not isinstance(entry.get("sha256"), str)
            or not isinstance(entry.get("size_bytes"), int)
            or isinstance(entry.get("size_bytes"), bool)
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "build source entry type mismatch"
            )
        source_paths.append(path)
    expected_source_paths = sorted(SOURCE_PATHS, key=lambda value: value.encode("utf-8"))
    if source_paths != expected_source_paths or len(source_paths) != len(set(source_paths)):
        raise GateFailure("IMPLEMENTATION_INVALID", "build source inventory is not exact")
    allowed_sources = tuple(REPO_ROOT / path for path in SOURCE_PATHS)
    for entry in source_entries:
        path = REPO_ROOT / entry["path"]
        try:
            artifacts.guard_synthetic_read_path(
                path,
                repo_root=REPO_ROOT,
                allowed_files=allowed_sources,
                extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
                require_allowlist_match=True,
            )
            identity = artifacts.file_identity(path)
        except (artifacts.ArtifactContractError, OSError) as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"cannot bind implementation source {entry['path']}: {error}",
            ) from error
        if identity.sha256 != entry.get("sha256") or identity.size_bytes != entry.get("size_bytes"):
            raise GateFailure("IMPLEMENTATION_INVALID", f"source changed since parity: {entry['path']}")
        try:
            implementation_blob = artifacts.git_blob_oid(
                REPO_ROOT, entry["path"], commit=implementation_commit
            )
            execution_blob = artifacts.git_blob_oid(
                REPO_ROOT, entry["path"], commit=execution_commit
            )
            last_source_change = artifacts.git_last_modified_commit(
                REPO_ROOT, entry["path"], commit=execution_commit
            )
            source_unchanged = artifacts.git_commit_is_ancestor(
                REPO_ROOT, last_source_change, implementation_commit
            )
        except artifacts.ArtifactContractError as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"source is not a regular committed Git blob: {entry['path']}",
            ) from error
        if implementation_blob != execution_blob or not source_unchanged:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"source Git blob changed after implementation: {entry['path']}",
            )

    try:
        artifacts.guard_synthetic_read_path(
            COMPILE_COMMANDS,
            repo_root=REPO_ROOT,
            allowed_files=(COMPILE_COMMANDS,),
            extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
            require_allowlist_match=True,
        )
        current_compile_commands = artifacts.load_and_validate_compile_commands(
            COMPILE_COMMANDS, repo_root=REPO_ROOT
        )
        artifacts.guard_synthetic_read_path(
            NATIVE_BINARY,
            repo_root=REPO_ROOT,
            allowed_files=(NATIVE_BINARY,),
            extra_forbidden_roots=EXTRA_FORBIDDEN_ROOTS,
            require_allowlist_match=True,
        )
        native_identity = artifacts.file_identity(NATIVE_BINARY)
    except (artifacts.ArtifactContractError, OSError) as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", f"cannot revalidate parity build: {error}"
        ) from error
    if build.get("compile_command_count") != len(artifacts.REQUIRED_TRANSLATION_UNITS):
        raise GateFailure("IMPLEMENTATION_INVALID", "compile command count changed since parity")
    if build.get("compile_commands") != current_compile_commands:
        raise GateFailure("IMPLEMENTATION_INVALID", "compile commands changed since parity")
    if build.get("build_command") != [
        "cmake",
        "--build",
        "build/a4_1s",
        "--target",
        "a4_1s_native",
        "-j1",
    ]:
        raise GateFailure("IMPLEMENTATION_INVALID", "build command manifest mismatch")
    if build.get("runtime_numeric") != dict(current_runtime):
        raise GateFailure("IMPLEMENTATION_INVALID", "numeric runtime changed since parity")
    if not isinstance(build.get("numpy_version"), str) or not build["numpy_version"]:
        raise GateFailure("IMPLEMENTATION_INVALID", "NumPy manifest schema mismatch")

    binary = build.get("native_binary")
    if not isinstance(binary, dict) or set(binary) != {"path", "sha256", "size_bytes"}:
        raise GateFailure("IMPLEMENTATION_INVALID", "native binary manifest schema mismatch")
    if binary.get("path") != "build/a4_1s/a4_1s_native":
        raise GateFailure("IMPLEMENTATION_INVALID", "native binary path mismatch")
    if binary.get("sha256") != native_identity.sha256 or binary.get("size_bytes") != native_identity.size_bytes:
        raise GateFailure("IMPLEMENTATION_INVALID", "native binary changed since parity")

    extra_ledger = [
        artifacts.make_input_ledger_entry(
            path,
            ledger_path=path.relative_to(REPO_ROOT).as_posix(),
            role="parity_review" if path == PARITY_REVIEW_PATH else "parity_evidence",
        )
        for path in required
    ]
    # Bound every Python-owned parity-checkpoint root together with a
    # deliberately overconservative allowance for all guarded JSON/source/
    # build payloads.  Actual JSON decoding is sequential, but this charges
    # every raw byte, worst-case UCS-4 text, decoded payload, and canonical
    # reserialization as if simultaneously live.  That makes the preflight
    # HWM independent of garbage-collector and allocator timing.
    try:
        source_and_build_paths = [
            REPO_ROOT / str(entry["path"]) for entry in source_entries
        ]
        accounted_paths = [
            *required,
            COMPILE_COMMANDS,
            NATIVE_BINARY,
            *source_and_build_paths,
        ]
        parity_preflight_transient_bound = 13 * sum(
            path.stat().st_size for path in accounted_paths
        )
    except (OSError, KeyError, TypeError) as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"cannot account parity-checkpoint payloads: {error}",
        ) from error
    parity_preflight_owned_buffer_high_water = (
        _deterministic_owned_buffer_bytes(
            loaded,
            index,
            current_contract_ledger,
            current_compile_commands,
            extra_ledger,
            current_runtime,
        )
        + parity_preflight_transient_bound
    )
    return (
        implementation_commit,
        parity_evidence_commit,
        parity_review_commit,
        extra_ledger,
        build,
        parity_preflight_owned_buffer_high_water,
    )


def _independent_scalar_solution_replays(
    parsed: Mapping[str, Any],
) -> tuple[dict[int, dict[str, Any]], int, int]:
    """Replay every selected partition from serialized support in Python.

    This authority intentionally does not consume native prefix moments or a
    native replay value.  It rebuilds exact integer prefix sums from the TSV
    support inventory, recomputes every interval SSE/mean, and independently
    rounds each mean to binary32 and binary64 before accepting the optimized
    curve.  The returned values are the replay objectives persisted in the
    full-shape scalar shards.
    """

    support = parsed.get("support")
    support_count = parsed.get("support_count")
    maximum_cardinality = parsed.get("maximum_cardinality")
    solutions = parsed.get("solutions")
    if (
        not isinstance(support, list)
        or not isinstance(support_count, int)
        or isinstance(support_count, bool)
        or len(support) != support_count
        or not isinstance(maximum_cardinality, int)
        or isinstance(maximum_cardinality, bool)
        or maximum_cardinality < 1
        or not isinstance(solutions, Mapping)
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "scalar replay input shape mismatch"
        )

    prefix_weight = [0]
    prefix_sum = [0]
    prefix_square = [0]
    for support_id, point in enumerate(support):
        if not isinstance(point, Mapping):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "scalar replay support is not an object"
            )
        grid_integer = _tsv_sint(
            point.get("grid_integer"),
            f"scalar replay support {support_id} grid_integer",
        )
        weight = _tsv_uint(
            point.get("weight"), f"scalar replay support {support_id} weight"
        )
        if weight == 0:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "scalar replay support weight is zero"
            )
        prefix_weight.append(prefix_weight[-1] + weight)
        prefix_sum.append(prefix_sum[-1] + weight * grid_integer)
        prefix_square.append(
            prefix_square[-1] + weight * grid_integer * grid_integer
        )

    replay_by_cardinality: dict[int, dict[str, Any]] = {}
    interval_evaluation_count = 0
    internal_high_water_bytes = _deterministic_owned_buffer_bytes(
        prefix_weight,
        prefix_sum,
        prefix_square,
        replay_by_cardinality,
    )
    for cardinality in range(1, maximum_cardinality + 1):
        solution = solutions.get(cardinality)
        if not isinstance(solution, Mapping) or not isinstance(
            solution.get("clusters"), list
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"scalar replay solution K={cardinality} is missing",
            )
        replay = Fraction(0, 1)
        prior_end = 0
        for cluster_id, cluster in enumerate(solution["clusters"]):
            if not isinstance(cluster, Mapping):
                raise GateFailure(
                    "IMPLEMENTATION_INVALID", "scalar replay cluster is not an object"
                )
            begin = cluster.get("begin")
            end = cluster.get("end")
            if (
                not isinstance(begin, int)
                or isinstance(begin, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or begin != prior_end
                or not begin < end <= support_count
            ):
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    f"scalar replay partition mismatch K={cardinality}",
                )
            weight = prefix_weight[end] - prefix_weight[begin]
            weighted_sum = prefix_sum[end] - prefix_sum[begin]
            weighted_square = prefix_square[end] - prefix_square[begin]
            numerator = weight * weighted_square - weighted_sum * weighted_sum
            if weight <= 0 or numerator < 0:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    f"scalar replay interval statistics invalid K={cardinality}",
                )
            replay += Fraction(numerator, weight)
            mean = _json_exact_rational(
                cluster.get("mean"),
                f"scalar replay mean K={cardinality} cluster={cluster_id}",
                exponent=-149,
                signed=True,
            )
            if Fraction(int(mean["numerator"]), int(mean["denominator"])) != Fraction(
                weighted_sum, weight
            ):
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    f"scalar replay mean mismatch K={cardinality}",
                )
            expected_f32 = _hex32(
                reference.round_grid_mean_to_float32_bits(weighted_sum, weight)
            )
            expected_f64 = _hex64(
                reference.round_grid_mean_to_float64_bits(weighted_sum, weight)
            )
            if (
                cluster.get("binary32_bits") != expected_f32
                or cluster.get("binary64_bits") != expected_f64
            ):
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    f"scalar replay direct-rounding mismatch K={cardinality}",
                )
            prior_end = end
            interval_evaluation_count += 1
            internal_high_water_bytes = max(
                internal_high_water_bytes,
                _deterministic_owned_buffer_bytes(
                    prefix_weight,
                    prefix_sum,
                    prefix_square,
                    replay_by_cardinality,
                    replay,
                    mean,
                    expected_f32,
                    expected_f64,
                ),
            )
        if prior_end != support_count:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"scalar replay partition does not cover support K={cardinality}",
            )
        objective = _json_exact_rational(
            solution.get("objective"),
            f"scalar replay objective K={cardinality}",
            exponent=-298,
            signed=False,
        )
        if Fraction(
            int(objective["numerator"]), int(objective["denominator"])
        ) != replay:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"scalar independent exact replay mismatch K={cardinality}",
            )
        replay_by_cardinality[cardinality] = _exact_value(replay, -298)
        internal_high_water_bytes = max(
            internal_high_water_bytes,
            _deterministic_owned_buffer_bytes(
                prefix_weight,
                prefix_sum,
                prefix_square,
                replay_by_cardinality,
                replay,
                objective,
            ),
        )
    return (
        replay_by_cardinality,
        interval_evaluation_count,
        internal_high_water_bytes,
    )


def _cost_scalar_record(
    coordinate: int,
    cardinality: int,
    parsed: Mapping[str, Any],
    replay_objective: Mapping[str, Any],
) -> dict[str, Any]:
    solution = parsed["solutions"][cardinality]
    clusters = solution["clusters"]
    binary32 = [cluster["binary32_bits"] for cluster in clusters]
    binary64 = [cluster["binary64_bits"] for cluster in clusters]
    predecessor = solution["predecessor_indices"]
    # At-most-K solutions above H reuse the H-layer certificate and therefore
    # also reuse that effective layer's monotonicity diagnostic.
    monotone = bool(
        parsed["monotone"].get(solution["effective_cardinality"], False)
    )
    increasing = all(
        reference.bits_to_float32(int(left, 16))
        < reference.bits_to_float32(int(right, 16))
        for left, right in zip(binary32, binary32[1:])
    )
    objective = dict(solution["objective"])
    return {
        "record_type": "scalar_curve",
        "coordinate_id": coordinate,
        "requested_cardinality": cardinality,
        "effective_cardinality": solution["effective_cardinality"],
        "fit_row_count": FULL_ROWS,
        "distinct_support_size": parsed["support_count"],
        "exact_sse": objective,
        "partition": [
            {"begin": cluster["begin"], "end": cluster["end"]}
            for cluster in clusters
        ],
        "exact_means": [dict(cluster["mean"]) for cluster in clusters],
        "binary32_centroid_bits": binary32,
        "binary32_centroid_bits_sha256": _sha256_canonical_array(binary32),
        "binary64_centroid_bits": binary64,
        "binary64_centroid_bits_sha256": _sha256_canonical_array(binary64),
        "predecessor_indices": predecessor,
        "predecessor_indices_sha256": _sha256_canonical_array(predecessor),
        "comparison_count": str(solution["comparison_count"]),
        "exact_tie_count": str(solution["exact_tie_count"]),
        "exact_replay_sse": dict(replay_objective),
        "exact_replay_match": True,
        "predecessors_nondecreasing": monotone,
        "serialized_binary32_strictly_increasing": increasing,
    }


def _compact_coordinate_model(parsed: Mapping[str, Any]) -> CompactCoordinateModel:
    effective = [0]
    objectives: list[dict[str, Any]] = [{}]
    f32: list[array.array] = [array.array("I")]
    f64: list[array.array] = [array.array("Q")]
    for cardinality in range(1, 257):
        solution = parsed["solutions"][cardinality]
        effective.append(int(solution["effective_cardinality"]))
        objectives.append(dict(solution["objective"]))
        f32.append(array.array("I", (int(cluster["binary32_bits"], 16) for cluster in solution["clusters"])))
        f64.append(array.array("Q", (int(cluster["binary64_bits"], 16) for cluster in solution["clusters"])))
    return CompactCoordinateModel(effective, objectives, f32, f64, int(parsed["support_count"]))


def _write_allocation_input(path: Path, models: Sequence[CompactCoordinateModel]) -> None:
    if len(models) != 128:
        raise GateFailure("IMPLEMENTATION_INVALID", "allocation input requires 128 curves")
    with path.open("xb") as output:
        output.write(b"A4ALC001")
        output.write(struct.pack("<II", 128, 256))
        for model in models:
            for cardinality in range(1, 257):
                objective = model.objectives[cardinality]
                numerator = objective["numerator"].encode("ascii")
                denominator = objective["denominator"].encode("ascii")
                output.write(struct.pack("<IiI", model.effective_cardinalities[cardinality], -298, len(numerator)))
                output.write(numerator)
                output.write(struct.pack("<I", len(denominator)))
                output.write(denominator)
        output.flush()


_ALLOCATION_ITEM_INPUT_MAGIC = b"A4ALI001"
_ALLOCATION_ITEM_INPUT_TERMINAL = b"A4AIEND1"
_ALLOCATION_ITEM_OUTPUT_MAGIC = b"A4ALO001"
_ALLOCATION_ITEM_OUTPUT_TERMINAL = b"A4AOEND1"
_ALLOCATION_ITEM_SCHEMA_VERSION = 1
_ALLOCATION_PRODUCT_KIND = 1
_ALLOCATION_GLOBAL_KIND = 2
_ALLOCATION_ARBITRARY_SET = 0
_ALLOCATION_DYADIC_SET = 1
_ALLOCATION_ITEM_COUNT = 258


def _allocation_objective_fraction(
    objective: Mapping[str, Any], field: str
) -> Fraction:
    checked = _json_exact_rational(
        objective, field, exponent=-298, signed=False
    )
    return Fraction(int(checked["numerator"]), int(checked["denominator"]))


def _allocation_objective_from_fraction(value: Fraction) -> dict[str, Any]:
    if value < 0:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation objective became negative"
        )
    return {
        "binary_grid_exponent": -298,
        "denominator": str(value.denominator),
        "numerator": str(value.numerator),
    }


class _AllocationItemWriter:
    """Canonical little-endian request writer with deterministic buffer HWM."""

    def __init__(self) -> None:
        self.payload = bytearray()
        self.peak_owned_bytes = 0

    def _append(self, value: bytes) -> None:
        self.payload.extend(value)
        # During bytearray.extend the source frame and its copied payload are
        # simultaneously live.  Allocator slack and object headers are outside
        # the registered deterministic-owned-buffer metric.
        self.peak_owned_bytes = max(
            self.peak_owned_bytes, len(self.payload) + len(value)
        )

    def write_u32(self, value: int, field: str) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            or value > 0xFFFFFFFF
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", f"{field} is outside uint32"
            )
        self._append(struct.pack("<I", value))

    def write_i32(self, value: int, field: str) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < -(1 << 31)
            or value >= (1 << 31)
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", f"{field} is outside int32"
            )
        self._append(struct.pack("<i", value))

    def write_objective(self, objective: Mapping[str, Any], field: str) -> None:
        checked = _json_exact_rational(
            objective, field, exponent=-298, signed=False
        )
        numerator = checked["numerator"].encode("ascii")
        denominator = checked["denominator"].encode("ascii")
        self.write_i32(-298, f"{field}.binary_grid_exponent")
        self.write_u32(len(numerator), f"{field}.numerator_byte_count")
        self._append(numerator)
        self.write_u32(len(denominator), f"{field}.denominator_byte_count")
        self._append(denominator)
        # Both encoded decimal source frames remain live until this method
        # returns, including while the second one has already been copied.
        self.peak_owned_bytes = max(
            self.peak_owned_bytes,
            len(self.payload) + len(numerator) + len(denominator),
        )

    def finish(self, path: Path) -> tuple[int, int]:
        self._append(_ALLOCATION_ITEM_INPUT_TERMINAL)
        try:
            with path.open("xb", buffering=0) as output:
                written = output.write(self.payload)
                if written != len(self.payload):
                    raise OSError("short allocation-item input write")
        except OSError as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"cannot write allocation-item input: {error}",
            ) from error
        return len(self.payload), self.peak_owned_bytes


def _write_allocation_item_curve(
    writer: _AllocationItemWriter,
    *,
    curve_id: int,
    model: CompactCoordinateModel,
    maximum_cardinality: int,
) -> None:
    if maximum_cardinality not in {16, 256}:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation-item curve maximum is not frozen"
        )
    if (
        len(model.effective_cardinalities) != 257
        or len(model.objectives) != 257
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation-item curve shape mismatch"
        )
    writer.write_u32(curve_id, "curve_id")
    support = model.effective_cardinalities[maximum_cardinality]
    if (
        not isinstance(support, int)
        or isinstance(support, bool)
        or support < 1
        or support > maximum_cardinality
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation-item support is outside [1,Kmax]"
        )
    support_objective: Fraction | None = None
    previous_objective: Fraction | None = None
    for cardinality in range(1, maximum_cardinality + 1):
        effective = model.effective_cardinalities[cardinality]
        if effective != min(cardinality, support):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"allocation-item curve {curve_id} violates min(K,H)",
            )
        objective = model.objectives[cardinality]
        coefficient = _allocation_objective_fraction(
            objective, f"allocation curve {curve_id} K={cardinality}"
        )
        if previous_objective is not None and coefficient > previous_objective:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"allocation-item curve {curve_id} objective increases",
            )
        if cardinality == support:
            support_objective = coefficient
        if cardinality > support and coefficient != support_objective:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"allocation-item curve {curve_id} unreachable tail changed",
            )
        writer.write_u32(effective, "effective_cardinality")
        writer.write_objective(
            objective, f"allocation curve {curve_id} K={cardinality}"
        )
        previous_objective = coefficient


def _write_allocation_item_input(
    path: Path,
    *,
    item_id: int,
    models: Sequence[CompactCoordinateModel],
) -> tuple[int, int]:
    """Write exactly one canonical A4ALI001 request.

    Returns ``(file_size, peak_live_serialization_payload_bytes)``.  The
    latter includes the growing bytearray and the largest simultaneously live
    source frame copied into it.
    """

    if len(models) != FULL_DIMENSIONS:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation-item input requires 128 curves"
        )
    if (
        not isinstance(item_id, int)
        or isinstance(item_id, bool)
        or item_id < 0
        or item_id >= _ALLOCATION_ITEM_COUNT
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation item id is outside [0,257]"
        )
    writer = _AllocationItemWriter()
    writer._append(_ALLOCATION_ITEM_INPUT_MAGIC)
    writer.write_u32(_ALLOCATION_ITEM_SCHEMA_VERSION, "schema_version")
    if item_id < 256:
        kind = _ALLOCATION_PRODUCT_KIND
        rate_index = item_id // 128
        within_rate = item_id % 128
        group_id = within_rate // 2
        cardinality_set = within_rate % 2
        capacity = 16 if rate_index == 0 else 256
        writer.write_u32(kind, "item_kind")
        writer.write_u32(item_id, "item_id")
        writer.write_u32(capacity, "capacity")
        writer.write_u32(cardinality_set, "cardinality_set")
        writer.write_u32(2, "curve_count")
        writer.write_u32(capacity, "maximum_cardinality")
        for curve_id in (2 * group_id, 2 * group_id + 1):
            _write_allocation_item_curve(
                writer,
                curve_id=curve_id,
                model=models[curve_id],
                maximum_cardinality=capacity,
            )
    else:
        kind = _ALLOCATION_GLOBAL_KIND
        bit_budget = 256 if item_id == 256 else 512
        writer.write_u32(kind, "item_kind")
        writer.write_u32(item_id, "item_id")
        writer.write_u32(bit_budget, "bit_budget")
        writer.write_u32(FULL_DIMENSIONS, "curve_count")
        writer.write_u32(FULL_COORDINATE_CARDINALITY, "maximum_cardinality")
        for curve_id, model in enumerate(models):
            _write_allocation_item_curve(
                writer,
                curve_id=curve_id,
                model=model,
                maximum_cardinality=FULL_COORDINATE_CARDINALITY,
            )
    return writer.finish(path)


class _AllocationItemReader:
    """Strict A4ALO001 reader; terminal and exact EOF are mandatory."""

    def __init__(self, path: Path) -> None:
        try:
            self.data = path.read_bytes()
        except OSError as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"cannot read allocation-item output: {error}",
            ) from error
        self.offset = 0
        self.maximum_frame_bytes = 0

    def _take(self, count: int, field: str) -> bytes:
        if count < 0 or self.offset + count > len(self.data):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", f"truncated allocation-item {field}"
            )
        value = self.data[self.offset : self.offset + count]
        self.offset += count
        self.maximum_frame_bytes = max(self.maximum_frame_bytes, len(value))
        return value

    def require(self, expected: bytes, field: str) -> None:
        if self._take(len(expected), field) != expected:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", f"allocation-item {field} mismatch"
            )

    def read_u8(self, field: str) -> int:
        return self._take(1, field)[0]

    def read_bool(self, field: str) -> bool:
        value = self.read_u8(field)
        if value not in {0, 1}:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"allocation-item {field} is not a canonical bool8",
            )
        return value == 1

    def read_u32(self, field: str) -> int:
        return struct.unpack("<I", self._take(4, field))[0]

    def read_i32(self, field: str) -> int:
        return struct.unpack("<i", self._take(4, field))[0]

    def read_u64(self, field: str) -> int:
        return struct.unpack("<Q", self._take(8, field))[0]

    def read_decimal(self, field: str, *, positive: bool) -> str:
        length = self.read_u32(f"{field}_byte_count")
        if length == 0:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", f"allocation-item {field} is empty"
            )
        encoded = self._take(length, field)
        try:
            value = encoded.decode("ascii")
        except UnicodeDecodeError as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"allocation-item {field} is not ASCII",
            ) from error
        if _UINT_RE.fullmatch(value) is None or (positive and value == "0"):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"allocation-item {field} is not canonical unsigned decimal",
            )
        return value

    def read_objective(self, field: str) -> dict[str, Any]:
        exponent = self.read_i32(f"{field}.binary_grid_exponent")
        if exponent != -298:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"allocation-item {field} exponent mismatch",
            )
        numerator = self.read_decimal(f"{field}.numerator", positive=False)
        denominator = self.read_decimal(f"{field}.denominator", positive=True)
        _tsv_rational(numerator, denominator, field, signed=False)
        return {
            "binary_grid_exponent": exponent,
            "denominator": denominator,
            "numerator": numerator,
        }

    def finish(self) -> None:
        self.require(_ALLOCATION_ITEM_OUTPUT_TERMINAL, "output terminal")
        if self.offset != len(self.data):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "allocation-item output has trailing bytes",
            )

    def live_payload_bound(self, parsed: Mapping[str, Any]) -> int:
        # ``data`` and the parsed object coexist on return.  Twice the largest
        # sliced frame conservatively covers a simultaneously live byte slice
        # and its decoded string while parsing a decimal field.
        return (
            len(self.data)
            + _deterministic_owned_buffer_bytes(parsed)
            + 2 * self.maximum_frame_bytes
        )


def _exact_product_allocation_reference(
    models: Sequence[CompactCoordinateModel],
    *,
    first_curve_id: int,
    second_curve_id: int,
    capacity: int,
    dyadic: bool,
) -> tuple[int, int, Fraction, int, int, int]:
    """Independent complete-codebook authority for one product decision.

    Every feasible allowed ``(K1,K2)`` is visited.  The frozen order is exact
    objective, then larger used-state count, then lexicographically smaller
    cardinality tuple.  The final two diagnostics are feasible visits and the
    peak live validation payload bytes.
    """

    if (
        len(models) != FULL_DIMENSIONS
        or capacity not in {16, 256}
        or not 0 <= first_curve_id < FULL_DIMENSIONS
        or second_curve_id != first_curve_id + 1
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            "product allocation reference shape is outside the frozen panel",
        )
    allowed = (
        tuple(1 << width for width in range(capacity.bit_length()))
        if dyadic
        else tuple(range(1, capacity + 1))
    )
    first_costs = tuple(
        _allocation_objective_fraction(
            models[first_curve_id].objectives[cardinality],
            f"product reference curve {first_curve_id} K={cardinality}",
        )
        for cardinality in range(1, capacity + 1)
    )
    second_costs = tuple(
        _allocation_objective_fraction(
            models[second_curve_id].objectives[cardinality],
            f"product reference curve {second_curve_id} K={cardinality}",
        )
        for cardinality in range(1, capacity + 1)
    )
    best: tuple[Fraction, int, int, int] | None = None
    feasible_visit_count = 0
    peak_live_payload_bytes = _deterministic_owned_buffer_bytes(
        allowed, first_costs, second_costs
    )
    for first in allowed:
        for second in allowed:
            used_states = first * second
            if used_states > capacity:
                continue
            feasible_visit_count += 1
            candidate = (
                first_costs[first - 1] + second_costs[second - 1],
                -used_states,
                first,
                second,
            )
            if best is None or candidate < best:
                best = candidate
            peak_live_payload_bytes = max(
                peak_live_payload_bytes,
                _deterministic_owned_buffer_bytes(
                    allowed, first_costs, second_costs, best, candidate
                ),
            )
    if best is None:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "product allocation reference found no state"
        )
    expected_visits = sum(
        1
        for first in allowed
        for second in allowed
        if first * second <= capacity
    )
    if feasible_visit_count != expected_visits:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            "product allocation reference visit inventory mismatch",
        )
    return (
        best[2],
        best[3],
        best[0],
        -best[1],
        feasible_visit_count,
        peak_live_payload_bytes,
    )


def _exact_global_dyadic_allocation_reference(
    models: Sequence[CompactCoordinateModel], bit_budget: int
) -> tuple[tuple[int, ...], int, Fraction, int, int]:
    """Independent exact-Fraction DP for the frozen global control.

    The order is exact objective, then larger used-bit count, then
    lexicographically smaller width vector.  The returned diagnostics are
    ``(widths, used_bits, objective, transitions, peak_live_payload_bytes)``.
    """

    if len(models) != FULL_DIMENSIONS or bit_budget not in {256, 512}:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            "global allocation reference shape is outside the frozen panel",
        )
    objective_grid = tuple(
        tuple(
            _allocation_objective_fraction(
                model.objectives[1 << width],
                f"global reference curve {coordinate} width={width}",
            )
            for width in range(9)
        )
        for coordinate, model in enumerate(models)
    )
    previous: dict[int, tuple[Fraction, tuple[int, ...]]] = {
        0: (Fraction(0, 1), ())
    }
    transition_count = 0
    peak_live_payload_bytes = _deterministic_owned_buffer_bytes(
        objective_grid, previous
    )
    for coordinate in range(FULL_DIMENSIONS):
        current: dict[int, tuple[Fraction, tuple[int, ...]]] = {}
        for used_bits, (prior_objective, prior_widths) in previous.items():
            for width in range(9):
                next_used = used_bits + width
                if next_used > bit_budget:
                    break
                transition_count += 1
                candidate = (
                    prior_objective + objective_grid[coordinate][width],
                    prior_widths + (width,),
                )
                incumbent = current.get(next_used)
                if incumbent is None or candidate < incumbent:
                    current[next_used] = candidate
        peak_live_payload_bytes = max(
            peak_live_payload_bytes,
            _deterministic_owned_buffer_bytes(objective_grid, previous, current),
        )
        previous = current
    if not previous:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "global allocation reference found no state"
        )
    best_used, (best_objective, best_widths) = min(
        previous.items(),
        key=lambda item: (item[1][0], -item[0], item[1][1]),
    )
    expected_transitions = _global_transition_count(FULL_DIMENSIONS, bit_budget)
    if transition_count != expected_transitions:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            "global allocation reference transition inventory mismatch",
        )
    return (
        best_widths,
        best_used,
        best_objective,
        transition_count,
        peak_live_payload_bytes,
    )


def _parse_allocation_item_output(
    path: Path,
    *,
    expected_item_id: int,
    models: Sequence[CompactCoordinateModel],
) -> tuple[dict[str, Any], int, int, int]:
    """Parse/replay one item and return old-consumer shape plus live-byte HWM."""

    if (
        not isinstance(expected_item_id, int)
        or isinstance(expected_item_id, bool)
        or expected_item_id < 0
        or expected_item_id >= _ALLOCATION_ITEM_COUNT
        or len(models) != FULL_DIMENSIONS
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            "allocation-item parser expectation is outside the frozen inventory",
        )
    reader = _AllocationItemReader(path)
    reader.require(_ALLOCATION_ITEM_OUTPUT_MAGIC, "output magic")
    if reader.read_u32("schema_version") != _ALLOCATION_ITEM_SCHEMA_VERSION:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation-item output version mismatch"
        )
    kind = reader.read_u32("item_kind")
    item_id = reader.read_u32("item_id")
    if item_id != expected_item_id:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation-item output id mismatch"
        )

    validation_product_visit_count = 0
    validation_transition_count = 0
    validation_peak_live_bytes = 0
    if expected_item_id < 256:
        if kind != _ALLOCATION_PRODUCT_KIND:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "product allocation-item kind mismatch"
            )
        rate_index = expected_item_id // 128
        within_rate = expected_item_id % 128
        group_id = within_rate // 2
        cardinality_set = within_rate % 2
        capacity = 16 if rate_index == 0 else 256
        if (
            reader.read_u32("capacity") != capacity
            or reader.read_u32("cardinality_set") != cardinality_set
            or reader.read_u32("curve_count") != 2
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "product allocation-item descriptor mismatch",
            )
        selected: list[tuple[int, int, int, bool]] = []
        for offset in range(2):
            curve_id = reader.read_u32(f"curve[{offset}].id")
            requested = reader.read_u32(f"curve[{offset}].requested")
            effective = reader.read_u32(f"curve[{offset}].effective")
            reachable = reader.read_bool(f"curve[{offset}].reachable")
            expected_curve_id = 2 * group_id + offset
            if curve_id != expected_curve_id or not 1 <= requested <= capacity:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    "product allocation-item curve order/cardinality mismatch",
                )
            expected_effective = models[curve_id].effective_cardinalities[requested]
            if (
                effective != expected_effective
                or reachable != (effective == requested)
            ):
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    "product allocation-item effective/reachability mismatch",
                )
            selected.append((curve_id, requested, effective, reachable))
        used_states = reader.read_u64("used_states")
        all_reachable = reader.read_bool("all_reachable")
        objective = reader.read_objective("selected_sse")
        candidates = reader.read_u64("candidate_evaluation_count")
        reader.finish()
        first_requested = selected[0][1]
        second_requested = selected[1][1]
        selected_objective = _allocation_objective_fraction(
            models[selected[0][0]].objectives[first_requested],
            f"product replay curve {selected[0][0]} K={first_requested}",
        ) + _allocation_objective_fraction(
            models[selected[1][0]].objectives[second_requested],
            f"product replay curve {selected[1][0]} K={second_requested}",
        )
        (
            expected_first,
            expected_second,
            expected_objective,
            expected_used_states,
            validation_product_visit_count,
            validation_peak_live_bytes,
        ) = _exact_product_allocation_reference(
            models,
            first_curve_id=selected[0][0],
            second_curve_id=selected[1][0],
            capacity=capacity,
            dyadic=cardinality_set == _ALLOCATION_DYADIC_SET,
        )
        if (
            (first_requested, second_requested)
            != (expected_first, expected_second)
            or used_states != first_requested * second_requested
            or used_states > capacity
            or used_states != expected_used_states
            or all_reachable != (selected[0][3] and selected[1][3])
            or _allocation_objective_fraction(objective, "selected_sse")
            != selected_objective
            or selected_objective != expected_objective
            or candidates
            != _product_candidate_count(
                capacity, cardinality_set == _ALLOCATION_DYADIC_SET
            )
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "product allocation-item optimum/tie/result replay mismatch",
            )
        parsed = {
            "cardinalities": [first_requested, second_requested],
            "objective": objective,
            "reachable": all_reachable,
            "used_states": used_states,
        }
    else:
        if kind != _ALLOCATION_GLOBAL_KIND:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "global allocation-item kind mismatch"
            )
        budget = 256 if expected_item_id == 256 else 512
        if (
            reader.read_u32("bit_budget") != budget
            or reader.read_u32("curve_count") != FULL_DIMENSIONS
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "global allocation-item descriptor mismatch"
            )
        used_bits = reader.read_u32("used_bits")
        all_reachable = reader.read_bool("all_reachable")
        objective = reader.read_objective("selected_sse")
        transitions = reader.read_u64("transition_evaluation_count")
        if reader.read_u32("selected_record_count") != FULL_DIMENSIONS:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "global allocation-item selected-record count mismatch",
            )
        widths: list[int] = []
        replay_reachable = True
        replay_objective = Fraction(0, 1)
        replay_used_bits = 0
        for coordinate in range(FULL_DIMENSIONS):
            curve_id = reader.read_u32(f"selected[{coordinate}].curve_id")
            width = reader.read_u8(f"selected[{coordinate}].bit_width")
            requested = reader.read_u32(f"selected[{coordinate}].requested")
            effective = reader.read_u32(f"selected[{coordinate}].effective")
            reachable = reader.read_bool(f"selected[{coordinate}].reachable")
            if (
                curve_id != coordinate
                or width > 8
                or requested != 1 << width
                or effective
                != models[coordinate].effective_cardinalities[requested]
                or reachable != (effective == requested)
            ):
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    "global allocation-item selected record mismatch",
                )
            widths.append(width)
            replay_used_bits += width
            replay_reachable = replay_reachable and reachable
            replay_objective += _allocation_objective_fraction(
                models[coordinate].objectives[requested],
                f"global replay curve {coordinate} K={requested}",
            )
        reader.finish()
        (
            expected_widths,
            expected_used_bits,
            expected_objective,
            validation_transition_count,
            validation_peak_live_bytes,
        ) = _exact_global_dyadic_allocation_reference(models, budget)
        if (
            used_bits != replay_used_bits
            or used_bits > budget
            or all_reachable != replay_reachable
            or _allocation_objective_fraction(objective, "selected_sse")
            != replay_objective
            or transitions != _global_transition_count(FULL_DIMENSIONS, budget)
            or tuple(widths) != expected_widths
            or used_bits != expected_used_bits
            or replay_objective != expected_objective
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                "global allocation-item optimum/tie/result replay mismatch",
            )
        parsed = {
            "bit_widths": widths,
            "objective": objective,
            "reachable": all_reachable,
            "used_bits": used_bits,
        }
    return (
        parsed,
        reader.live_payload_bound(parsed) + validation_peak_live_bytes,
        validation_product_visit_count,
        validation_transition_count,
    )


def _assemble_allocation_items(
    product_items: Mapping[int, Mapping[str, Any]],
    global_items: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    if set(product_items) != set(range(256)) or set(global_items) != {256, 257}:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation-item result inventory is incomplete"
        )
    groups: list[dict[str, Any]] = []
    for word_bits in (4, 8):
        rate_index = 0 if word_bits == 4 else 1
        for group_id in range(FULL_GROUP_COUNT):
            arbitrary_id = ((rate_index * FULL_GROUP_COUNT + group_id) * 2)
            dyadic_id = arbitrary_id + 1
            groups.append(
                {
                    "arbitrary": dict(product_items[arbitrary_id]),
                    "dyadic": dict(product_items[dyadic_id]),
                    "group": group_id,
                    "rate": f"B{word_bits}",
                }
            )
    return {
        "globals": {
            "B4": dict(global_items[256]),
            "B8": dict(global_items[257]),
        },
        "groups": groups,
    }


def _product_item_representation_failure(
    *,
    item_id: int,
    arm: Mapping[str, Any],
    models: Sequence[CompactCoordinateModel],
) -> dict[str, Any] | None:
    if item_id >= 256:
        return None
    rate_index = item_id // 128
    group_id = (item_id % 128) // 2
    cardinality_set = item_id % 2
    word_bits = 4 if rate_index == 0 else 8
    arm_name = "arbitrary_word" if cardinality_set == 0 else "dyadic_word"
    cardinalities = [int(value) for value in arm["cardinalities"]]
    effective = [
        models[2 * group_id + offset].effective_cardinalities[cardinality]
        for offset, cardinality in enumerate(cardinalities)
    ]
    calculated_reachable = effective == cardinalities
    if bool(arm.get("reachable")) != calculated_reachable:
        raise GateFailure(
            "IMPLEMENTATION_INVALID",
            f"allocation reachability flag mismatch item {item_id}",
        )
    for coordinate_offset, (requested, observed) in enumerate(
        zip(cardinalities, effective)
    ):
        if observed != requested:
            return {
                "word_bits": word_bits,
                "group_id": group_id,
                "arm": arm_name,
                "requested_cardinality": requested,
                "effective_cardinality": observed,
                "center_count": requested,
                "distinct_center_count": observed,
            }
        bits = models[2 * group_id + coordinate_offset].binary32_centroids[
            requested
        ]
        values = [reference.bits_to_float32(int(value)) for value in bits]
        for label, (left, right) in enumerate(zip(values, values[1:])):
            if not left < right:
                return {
                    "word_bits": word_bits,
                    "group_id": group_id,
                    "arm": arm_name,
                    "requested_cardinality": requested,
                    "effective_cardinality": len(bits),
                    "first_colliding_label": label,
                    "center_count": len(bits),
                    "distinct_center_count": len(set(bits)),
                }
    return None


def _product_candidate_count(capacity: int, dyadic: bool) -> int:
    if dyadic:
        return capacity.bit_length()
    return capacity


def _global_transition_count(dimensions: int, budget: int) -> int:
    count = 0
    for coordinate in range(dimensions):
        for used in range(min(8 * coordinate, budget) + 1):
            count += min(8, budget - used) + 1
    return count


def _allocation_records(
    allocation: Mapping[str, Any], models: Sequence[CompactCoordinateModel]
) -> tuple[list[dict[str, Any]], dict[tuple[int, int], Mapping[str, Any]], dict[int, Mapping[str, Any]]]:
    records: list[dict[str, Any]] = []
    groups_by_rate: dict[tuple[int, int], Mapping[str, Any]] = {}
    for raw in allocation["groups"]:
        word_bits = int(str(raw["rate"])[1:])
        capacity = 1 << word_bits
        group_id = int(raw["group"])
        group_record: dict[str, Any] = {
            "record_type": "group_allocation",
            "word_bits": word_bits,
            "capacity": capacity,
            "group_id": group_id,
            "coordinates": [2 * group_id, 2 * group_id + 1],
        }
        for source_key, target_key, dyadic in (
            ("dyadic", "dyadic_word", True),
            ("arbitrary", "arbitrary_word", False),
        ):
            arm = raw[source_key]
            cardinalities = [int(value) for value in arm["cardinalities"]]
            effective = [
                models[2 * group_id + offset].effective_cardinalities[cardinality]
                for offset, cardinality in enumerate(cardinalities)
            ]
            group_record[target_key] = {
                "requested_cardinalities": cardinalities,
                "effective_cardinalities": effective,
                "used_states": int(arm["used_states"]),
                "invalid_states": capacity - int(arm["used_states"]),
                "exact_fitting_sse": dict(arm["objective"]),
                "enumerated_candidate_count": str(_product_candidate_count(capacity, dyadic)),
            }
        records.append(group_record)
        groups_by_rate[(word_bits, group_id)] = raw

    globals_by_rate: dict[int, Mapping[str, Any]] = {}
    for word_bits, name in ((4, "B4"), (8, "B8")):
        raw = allocation["globals"][name]
        widths = [int(value) for value in raw["bit_widths"]]
        cardinalities = [1 << width for width in widths]
        records.append(
            {
                "record_type": "global_allocation",
                "word_bits": word_bits,
                "total_bit_budget": 64 * word_bits,
                "bit_widths": widths,
                "bit_widths_sha256": _sha256_canonical_array(widths),
                "cardinalities": cardinalities,
                "cardinalities_sha256": _sha256_canonical_array(cardinalities),
                "used_bits": int(raw["used_bits"]),
                "exact_fitting_sse": dict(raw["objective"]),
                "enumerated_transition_count": str(_global_transition_count(128, 64 * word_bits)),
            }
        )
        globals_by_rate[word_bits] = raw
    if len(records) != 130:
        raise GateFailure("IMPLEMENTATION_INVALID", "allocation record count mismatch")
    return records, groups_by_rate, globals_by_rate


def _populate_allocation_accounting(
    counters: dict[str, Any],
    models: Sequence[CompactCoordinateModel],
    groups: Mapping[tuple[int, int], Mapping[str, Any]],
    globals_by_rate: Mapping[int, Mapping[str, Any]],
) -> None:
    comparisons = counters["comparison_counts"]
    byte_counts = counters["representation_bytes"]
    address_counts = counters["address_counts"]
    selected = counters["selected_cardinalities"]
    distinct = counters["distinct_center_checks"]
    for word_bits in (4, 8):
        capacity = 1 << word_bits
        rate = f"B{word_bits}"
        rate_codebooks: dict[str, int] = {}
        rate_addresses: dict[str, dict[str, int]] = {}
        for source, arm_name, dyadic in (
            ("dyadic", "dyadic_word", True),
            ("arbitrary", "arbitrary_word", False),
        ):
            codebook_bytes = 0
            valid_addresses = 0
            for group_id in range(FULL_GROUP_COUNT):
                raw = groups[(word_bits, group_id)][source]
                cardinalities = [int(value) for value in raw["cardinalities"]]
                for offset, cardinality in enumerate(cardinalities):
                    model = models[2 * group_id + offset]
                    effective_cardinality = model.effective_cardinalities[cardinality]
                    bits = model.binary32_centroids[cardinality]
                    distinct["scalar_selected_alphabet_checks"] += 1
                    if effective_cardinality != cardinality or len(set(bits)) != len(bits):
                        distinct["scalar_selected_alphabet_failures"] += 1
                    codebook_bytes += len(bits) * 4
                valid_addresses += int(raw["used_states"])
            comparisons["product_candidate_evaluations"] += (
                FULL_GROUP_COUNT * _product_candidate_count(capacity, dyadic)
            )
            rate_codebooks[arm_name] = codebook_bytes
            rate_addresses[arm_name] = {
                "valid": valid_addresses,
                "invalid": FULL_GROUP_COUNT * capacity - valid_addresses,
            }

        for group_id in range(FULL_GROUP_COUNT):
            selected["group_arms"].append(
                {
                    "word_bits": word_bits,
                    "group_id": group_id,
                    "dyadic_word": [
                        int(value)
                        for value in groups[(word_bits, group_id)]["dyadic"]["cardinalities"]
                    ],
                    "arbitrary_word": [
                        int(value)
                        for value in groups[(word_bits, group_id)]["arbitrary"]["cardinalities"]
                    ],
                }
            )

        global_raw = globals_by_rate[word_bits]
        widths = [int(value) for value in global_raw["bit_widths"]]
        cardinalities = [1 << width for width in widths]
        global_codebook_bytes = 0
        global_unreachable = 0
        global_nominal_unreachable = 0
        for coordinate, cardinality in enumerate(cardinalities):
            model = models[coordinate]
            bits = model.binary32_centroids[cardinality]
            global_codebook_bytes += len(bits) * 4
            if model.effective_cardinalities[cardinality] != cardinality:
                global_nominal_unreachable += 1
            if model.effective_cardinalities[cardinality] != cardinality or len(set(bits)) != len(bits):
                global_unreachable += 1
        if bool(global_raw.get("reachable")) != (global_nominal_unreachable == 0):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"global control reachability flag mismatch B{word_bits}",
            )
        distinct["global_control_unreachable_alphabets"] += global_unreachable
        selected["global_control"].append(
            {
                "word_bits": word_bits,
                "bit_widths": widths,
                "cardinalities": cardinalities,
                "used_bits": int(global_raw["used_bits"]),
            }
        )
        rate_codebooks["global_dyadic_pack_cap8"] = global_codebook_bytes
        rate_codebooks["trained_block_vq"] = 0
        byte_counts["codebook"][rate] = rate_codebooks
        byte_counts["radix_and_address_metadata"][rate] = {
            "dyadic_word_uint16_radices_and_used_states": FULL_GROUP_COUNT * 3 * 2,
            "arbitrary_word_uint16_radices_and_used_states": FULL_GROUP_COUNT * 3 * 2,
            "derived_product_multiplier_persistent_bytes": 0,
            "derived_address_offset_persistent_bytes": 0,
            "trained_block_codeword_metadata_bytes": 0,
            "global_bit_width_uint8_bytes": FULL_DIMENSIONS,
            "global_bit_offset_uint32_bytes": FULL_DIMENSIONS * 4,
        }
        byte_counts["expanded_lookup"][rate] = {
            "dyadic_word": FULL_GROUP_COUNT * capacity * 4,
            "arbitrary_word": FULL_GROUP_COUNT * capacity * 4,
            "trained_block_vq": FULL_GROUP_COUNT * capacity * 4,
            "global_dyadic_pack_cap8": sum(cardinalities) * 4,
        }
        byte_counts["database_payload"][rate] = {
            arm: {"per_vector": word_bits * FULL_GROUP_COUNT // 8, "completed_total": 0}
            for arm in (
                "dyadic_word",
                "arbitrary_word",
                "trained_block_vq",
                "global_dyadic_pack_cap8",
            )
        }
        rate_addresses["trained_block_vq"] = {
            "valid": FULL_GROUP_COUNT * capacity,
            "invalid": 0,
        }
        rate_addresses["global_dyadic_pack_cap8"] = {
            "valid": sum(cardinalities),
            "invalid": 0,
        }
        address_counts[rate] = rate_addresses
        comparisons["global_transition_evaluations"] += _global_transition_count(
            FULL_DIMENSIONS, FULL_GROUP_COUNT * word_bits
        )


def _canonical_array_hash(values: Sequence[int]) -> str:
    return artifacts.sha256_bytes(artifacts.canonical_json_bytes([int(value) for value in values]))


def _block_points_from_native(case: Mapping[str, Any]) -> tuple[reference.BlockPoint, ...]:
    return tuple(
        reference.BlockPoint(
            reference.bits_to_float32(int(row["coordinate_bits"][0], 16)),
            reference.bits_to_float32(int(row["coordinate_bits"][1], 16)),
            int(row["cell_id"]),
            int(row["vector_id"]),
            bytes.fromhex(row["selection_digest"]),
        )
        for row in case["rows"]
    )


def _assign_to_binary64_centers(
    points: Sequence[reference.BlockPoint], center_bits: Sequence[Sequence[str]]
) -> tuple[list[int], int, int, int]:
    centers = [
        (
            reference.bits_to_float64(int(value[0], 16)),
            reference.bits_to_float64(int(value[1], 16)),
        )
        for value in center_bits
    ]
    assignments, sse, comparisons, ties = reference._assign_points_audit(
        points, centers
    )
    return assignments, reference.float64_bits(sse), comparisons, ties


def _block_cost_records(
    case: Mapping[str, Any],
    *,
    word_bits: int,
    group_id: int,
    arbitrary_cardinalities: Sequence[int],
    arbitrary_used_states: int,
) -> tuple[list[dict[str, Any]], list[list[str]], dict[str, int]]:
    capacity = 1 << word_bits
    if not case.get("control_valid") or len(case.get("starts", [])) != 8:
        raise GateFailure("CONTROL_INVALID", f"block group {group_id} B{word_bits} failed")
    points = _block_points_from_native(case)
    row_ids = [int(row["vector_id"]) for row in case["rows"]]
    selected = int(case["best_start_id"])
    metadata = {
        "record_type": "block_metadata",
        "word_bits": word_bits,
        "capacity": capacity,
        "group_id": group_id,
        "coordinates": [2 * group_id, 2 * group_id + 1],
        "fit_row_count": FULL_ROWS,
        "row_order_vector_ids": row_ids,
        "row_order_vector_ids_sha256": _canonical_array_hash(row_ids),
        "arbitrary_cardinalities": [int(value) for value in arbitrary_cardinalities],
        "arbitrary_used_states": int(arbitrary_used_states),
        "selected_start_id": selected,
    }
    records: list[dict[str, Any]] = [metadata]
    replay_audit = {"distance_comparisons": 0, "assignment_ties": 0}
    cartesian = case["cartesian"]
    cartesian_sse = reference.bits_to_float64(int(cartesian["sse_bits"], 16))
    for start, raw in zip(case["starts"], case["native_starts"]):
        before_centers = raw["initial_centers_bits"]
        steps = []
        for step in raw["steps"]:
            (
                before_assignments,
                before_sse_bits,
                before_comparisons,
                before_ties,
            ) = _assign_to_binary64_centers(points, before_centers)
            (
                after_assignments,
                after_sse_bits,
                after_comparisons,
                after_ties,
            ) = _assign_to_binary64_centers(points, step["centers_after_bits"])
            replay_audit["distance_comparisons"] += (
                before_comparisons + after_comparisons
            )
            replay_audit["assignment_ties"] += before_ties + after_ties
            if _hex64(before_sse_bits) != step["prior_sse_bits"] or _hex64(after_sse_bits) != step["candidate_sse_bits"]:
                raise GateFailure("CONTROL_INVALID", "block step direct replay mismatch")
            steps.append(
                {
                    "iteration": int(step["iteration"]),
                    "prior_sse_bits": step["prior_sse_bits"],
                    "candidate_sse_bits": step["candidate_sse_bits"],
                    "assignments_before_sha256": _canonical_array_hash(before_assignments),
                    "assignments_after_sha256": _canonical_array_hash(after_assignments),
                    "centers_after_binary64_bits_sha256": _sha256_canonical_array(step["centers_after_bits"]),
                    "changed_assignment_count": int(step["changed_assignment_count"]),
                    "empty_center_ids": list(step["empty_center_ids"]),
                    "empty_center_ids_sha256": _canonical_array_hash(step["empty_center_ids"]),
                    "accepted": True,
                }
            )
            before_centers = step["centers_after_bits"]
        (
            final_assignments,
            final_sse_bits,
            final_comparisons,
            final_ties,
        ) = _assign_to_binary64_centers(points, raw["final_centers_bits"])
        replay_audit["distance_comparisons"] += final_comparisons
        replay_audit["assignment_ties"] += final_ties
        if final_assignments != raw["final_assignments"] or _hex64(final_sse_bits) != raw["final_sse_bits"]:
            raise GateFailure("CONTROL_INVALID", "block final direct replay mismatch")
        final_sse = reference.bits_to_float64(int(raw["final_sse_bits"], 16))
        start_id = int(raw["start_id"])
        prefill_centers = cartesian["centers"] if start_id == 0 else None
        records.append(
            {
                "record_type": "block_start",
                "word_bits": word_bits,
                "capacity": capacity,
                "group_id": group_id,
                "start_id": start_id,
                "initialization_kind": "cartesian_fill" if start_id == 0 else "hashed_farthest_first",
                "initialization_vector_ids": list(raw["selected_vector_ids"]),
                "initialization_vector_ids_sha256": _canonical_array_hash(raw["selected_vector_ids"]),
                "prefill_cartesian_centers_binary64_bits": prefill_centers,
                "prefill_cartesian_centers_binary64_bits_sha256": (
                    _sha256_canonical_array(prefill_centers) if prefill_centers is not None else None
                ),
                "prefill_cartesian_sse_bits": cartesian["sse_bits"] if start_id == 0 else None,
                "initial_centers_binary64_bits": raw["initial_centers_bits"],
                "initial_centers_binary64_bits_sha256": _sha256_canonical_array(raw["initial_centers_bits"]),
                "steps": steps,
                "iteration_count": int(raw["iterations"]),
                "accepted_update_count": int(raw["iterations"]),
                "converged": bool(raw["converged"]),
                "final_assignments": list(raw["final_assignments"]),
                "final_assignments_sha256": _canonical_array_hash(raw["final_assignments"]),
                "final_centers_binary64_bits": raw["final_centers_bits"],
                "final_centers_binary64_bits_sha256": _sha256_canonical_array(raw["final_centers_bits"]),
                "final_centers_binary32_bits": raw["serialized_centers_bits"],
                "final_centers_binary32_bits_sha256": _sha256_canonical_array(raw["serialized_centers_bits"]),
                "final_sse_bits": raw["final_sse_bits"],
                "distance_comparison_count": str(raw["distance_comparison_count"]),
                "assignment_tie_count": str(raw["assignment_tie_count"]),
                "farthest_tie_count": str(raw["farthest_tie_count"]),
                "serialized_distinct_center_count": int(raw["distinct_serialized_center_count"]),
                "direct_replay_match": True,
                "cartesian_dominance_pass": final_sse <= cartesian_sse,
                "selected_best_start": start_id == selected,
            }
        )
    if len(records) != 9 or sum(bool(record.get("selected_best_start")) for record in records[1:]) != 1:
        raise GateFailure("CONTROL_INVALID", "block selected-start inventory mismatch")
    selected_raw = case["native_starts"][selected]
    return records, selected_raw["serialized_centers_bits"], replay_audit


def _replay_nearest_labels_numpy(
    np: Any, values: Any, centroid_bits: Sequence[int]
) -> tuple[Any, int]:
    """Return replay labels and exact live ndarray workspace high-water."""

    centers_u32 = np.asarray(list(centroid_bits), dtype=np.uint32)
    centers = centers_u32.view(np.float32).astype(np.float64)
    promoted = np.asarray(values, dtype=np.float32).astype(np.float64)
    distances = np.subtract(promoted[:, None], centers[None, :])
    np.square(distances, out=distances)
    finite = np.empty(distances.shape, dtype=np.bool_)
    np.isfinite(distances, out=finite)
    if not finite.all():
        raise GateFailure("IMPLEMENTATION_INVALID", "encoding distance is nonfinite")
    raw_labels = np.argmin(distances, axis=1)
    labels = raw_labels.astype(np.uint16)
    workspace_high_water = sum(
        int(value.nbytes)
        for value in (
            centers_u32,
            centers,
            promoted,
            distances,
            finite,
            raw_labels,
            labels,
        )
    )
    return labels, workspace_high_water


def _replay_nearest_point_labels_numpy(
    np: Any, values: Any, center_bits: Sequence[Sequence[str]]
) -> tuple[Any, int]:
    """Return replay labels and exact live ndarray workspace high-water."""

    center0_u32 = np.asarray([int(value[0], 16) for value in center_bits], dtype=np.uint32)
    center1_u32 = np.asarray([int(value[1], 16) for value in center_bits], dtype=np.uint32)
    center0 = center0_u32.view(np.float32).astype(np.float64)
    center1 = center1_u32.view(np.float32).astype(np.float64)
    promoted = np.asarray(values, dtype=np.float32).astype(np.float64)
    distances = np.subtract(promoted[:, 0, None], center0[None, :])
    np.square(distances, out=distances)
    scratch = np.subtract(promoted[:, 1, None], center1[None, :])
    np.square(scratch, out=scratch)
    np.add(distances, scratch, out=distances)
    finite = np.empty(distances.shape, dtype=np.bool_)
    np.isfinite(distances, out=finite)
    if not finite.all():
        raise GateFailure("IMPLEMENTATION_INVALID", "block encoding distance is nonfinite")
    raw_labels = np.argmin(distances, axis=1)
    labels = raw_labels.astype(np.uint16)
    workspace_high_water = sum(
        int(value.nbytes)
        for value in (
            center0_u32,
            center1_u32,
            center0,
            center1,
            promoted,
            distances,
            scratch,
            finite,
            raw_labels,
            labels,
        )
    )
    return labels, workspace_high_water


_ENCODING_INPUT_MAGIC = b"A4ENC002"
_ENCODING_INPUT_TERMINAL = b"A4EIEND2"
_ENCODING_OUTPUT_MAGIC = b"A4EOUT02"
_ENCODING_OUTPUT_TERMINAL = b"A4EOEND2"
_ENCODING_SCHEMA_VERSION = 2
_ENCODING_ROW_MARKER = 0x31574F52
_ENCODING_REPLAY_CHUNK_ROWS = FULL_COORDINATE_CARDINALITY
_ENCODING_ARM_NAMES = (
    "dyadic_word",
    "arbitrary_word",
    "trained_block_vq",
    "global_dyadic_pack_cap8",
)


def _write_u32_sequence(output: Any, values: Iterable[int]) -> None:
    chunk: list[int] = []
    for raw in values:
        value = int(raw)
        if not 0 <= value <= 0xFFFFFFFF:
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding uint32 is out of range")
        chunk.append(value)
        if len(chunk) == 4096:
            output.write(struct.pack("<4096I", *chunk))
            chunk.clear()
    if chunk:
        output.write(struct.pack(f"<{len(chunk)}I", *chunk))


def _write_encoding_input(
    path: Path,
    *,
    np: Any,
    word_bits: int,
    selected_arm_id: int,
    matrix: Any,
    models: Sequence[CompactCoordinateModel],
    groups: Mapping[tuple[int, int], Mapping[str, Any]],
    globals_by_rate: Mapping[int, Mapping[str, Any]],
    block_centers: Mapping[tuple[int, int], Sequence[Sequence[str]]],
) -> None:
    """Write one arm-major A4ENC002 input without assigning any labels."""

    if (
        word_bits not in (4, 8)
        or selected_arm_id not in range(4)
        or matrix.shape != (FULL_ROWS, FULL_DIMENSIONS)
        or matrix.dtype != np.dtype("float32")
        or not matrix.flags.c_contiguous
        or len(models) != FULL_DIMENSIONS
    ):
        raise GateFailure("IMPLEMENTATION_INVALID", "encoding input shape mismatch")
    matrix_bits = matrix.view(np.uint32)
    if matrix_bits.shape != matrix.shape or not matrix_bits.flags.c_contiguous:
        raise GateFailure("IMPLEMENTATION_INVALID", "encoding matrix bit view mismatch")
    with path.open("xb") as output:
        output.write(_ENCODING_INPUT_MAGIC)
        output.write(
            struct.pack(
                "<IIIIIIQ",
                _ENCODING_SCHEMA_VERSION,
                selected_arm_id,
                word_bits,
                FULL_ROWS,
                FULL_DIMENSIONS,
                FULL_GROUP_COUNT,
                FULL_ROWS * FULL_DIMENSIONS,
            )
        )
        output.write(memoryview(matrix_bits).cast("B"))

        if selected_arm_id in (0, 1):
            source = ("dyadic", "arbitrary")[selected_arm_id]
            output.write(struct.pack("<I", selected_arm_id))
            for group_id in range(FULL_GROUP_COUNT):
                raw = groups[(word_bits, group_id)][source]
                cardinalities = [int(value) for value in raw["cardinalities"]]
                if len(cardinalities) != 2:
                    raise GateFailure(
                        "IMPLEMENTATION_INVALID", "encoding scalar cardinality shape mismatch"
                    )
                axis0 = models[2 * group_id].binary32_centroids[cardinalities[0]]
                axis1 = models[2 * group_id + 1].binary32_centroids[cardinalities[1]]
                if len(axis0) != cardinalities[0] or len(axis1) != cardinalities[1]:
                    raise GateFailure(
                        "IMPLEMENTATION_INVALID", "encoding scalar centroid count mismatch"
                    )
                output.write(
                    struct.pack(
                        "<III", group_id, cardinalities[0], cardinalities[1]
                    )
                )
                _write_u32_sequence(output, axis0)
                _write_u32_sequence(output, axis1)

        elif selected_arm_id == 2:
            capacity = 1 << word_bits
            output.write(struct.pack("<I", 2))
            for group_id in range(FULL_GROUP_COUNT):
                centers = block_centers[(word_bits, group_id)]
                if len(centers) != capacity:
                    raise GateFailure(
                        "IMPLEMENTATION_INVALID", "encoding block centroid count mismatch"
                    )
                output.write(struct.pack("<II", group_id, capacity))
                for center in centers:
                    if len(center) != 2:
                        raise GateFailure(
                            "IMPLEMENTATION_INVALID", "encoding block centroid shape mismatch"
                        )
                    output.write(
                        struct.pack("<II", int(center[0], 16), int(center[1], 16))
                    )
        else:
            global_raw = globals_by_rate[word_bits]
            widths = [int(value) for value in global_raw["bit_widths"]]
            if len(widths) != FULL_DIMENSIONS:
                raise GateFailure("IMPLEMENTATION_INVALID", "encoding global width count mismatch")
            output.write(struct.pack("<I", 3))
            for coordinate, width in enumerate(widths):
                nominal_cardinality = 1 << width
                centroids = models[coordinate].binary32_centroids[nominal_cardinality]
                actual_cardinality = len(centroids)
                if (
                    not 0 <= width <= 8
                    or actual_cardinality == 0
                    or actual_cardinality > nominal_cardinality
                ):
                    raise GateFailure(
                        "IMPLEMENTATION_INVALID", "encoding global centroid count mismatch"
                    )
                output.write(
                    struct.pack("<III", coordinate, width, actual_cardinality)
                )
                _write_u32_sequence(output, centroids)
        output.write(_ENCODING_INPUT_TERMINAL)
        output.write(struct.pack("<II", FULL_ROWS, selected_arm_id))
        output.flush()


class _EncodingBinaryReader:
    def __init__(self, path: Path):
        self._input = path.open("rb")

    def __enter__(self) -> "_EncodingBinaryReader":
        return self

    def __exit__(self, *args: Any) -> None:
        self._input.close()

    def read_exact(self, byte_count: int, field: str) -> bytes:
        if byte_count < 0:
            raise GateFailure("IMPLEMENTATION_INVALID", f"negative encoding {field} length")
        value = self._input.read(byte_count)
        if len(value) != byte_count:
            raise GateFailure("IMPLEMENTATION_INVALID", f"truncated encoding output {field}")
        return value

    def u32(self, field: str) -> int:
        return int(struct.unpack("<I", self.read_exact(4, field))[0])

    def u64(self, field: str) -> int:
        return int(struct.unpack("<Q", self.read_exact(8, field))[0])

    def u32s(self, count: int, field: str) -> list[int]:
        if count > FULL_DIMENSIONS:
            raise GateFailure("IMPLEMENTATION_INVALID", f"encoding {field} count is too large")
        if count == 0:
            return []
        return [int(value) for value in struct.unpack(f"<{count}I", self.read_exact(4 * count, field))]

    def require_eof(self) -> None:
        if self._input.read(1) != b"":
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding output has trailing bytes")


@dataclass
class EncodingNativeTotals:
    row_count: int = 0
    distance_comparisons: dict[str, int] | None = None
    validation_distance_comparisons: dict[str, int] | None = None
    payload_bytes: dict[str, int] | None = None
    pack_operations: dict[str, int] | None = None
    validation_pack_operations: dict[str, int] | None = None
    unpack_operations: dict[str, int] | None = None
    validation_unpack_operations: dict[str, int] | None = None
    mixed_radix_encodes: dict[str, int] | None = None
    mixed_radix_decodes: dict[str, int] | None = None
    arm_vector_counts: dict[str, int] | None = None
    owned_payload_high_water_bytes: int = 0
    python_owned_high_water_bytes: int = 0
    replay_workspace_high_water_bytes: int = 0
    current_record_high_water_bytes: int = 0
    canonical_line_high_water_bytes: int = 0


@dataclass(frozen=True)
class _NativeEncodedArmRow:
    arm_id: int
    labels: list[int]
    payload: bytes
    roundtrip_labels: list[int]
    distance_comparisons: int
    pack_operations: int
    unpack_operations: int

    def logical_payload_bytes(self) -> int:
        return 4 * (len(self.labels) + len(self.roundtrip_labels)) + len(self.payload)


class _EncodingArmStream:
    def __init__(self, path: Path, *, arm_id: int, word_bits: int):
        self.reader = _EncodingBinaryReader(path)
        self.arm_id = arm_id
        self.arm_name = _ENCODING_ARM_NAMES[arm_id]
        self.word_bits = word_bits
        self.comparisons = 0
        self.payload_bytes = 0
        self.pack_operations = 0
        self.unpack_operations = 0
        self.native_owned_high_water = 0
        self.mixed_radix_encodes = 0
        self.mixed_radix_decodes = 0
        self.arm_vector_count = 0

    def __enter__(self) -> "_EncodingArmStream":
        self.reader.__enter__()
        try:
            if self.reader.read_exact(8, "magic") != _ENCODING_OUTPUT_MAGIC:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID", "encoding output magic mismatch"
                )
            header = [
                self.reader.u32(name)
                for name in (
                    "schema_version",
                    "selected_arm_id",
                    "word_bits",
                    "row_count",
                    "coordinate_count",
                    "group_count",
                    "arm_count",
                )
            ]
            if header != [
                _ENCODING_SCHEMA_VERSION,
                self.arm_id,
                self.word_bits,
                FULL_ROWS,
                FULL_DIMENSIONS,
                FULL_GROUP_COUNT,
                1,
            ]:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID", "encoding output header mismatch"
                )
            return self
        except BaseException:
            self.reader.__exit__()
            raise

    def __exit__(self, *args: Any) -> None:
        self.reader.__exit__(*args)

    def read_row(self, vector_id: int) -> _NativeEncodedArmRow:
        reader = self.reader
        if (
            reader.u32("row_marker") != _ENCODING_ROW_MARKER
            or reader.u32("vector_id") != vector_id
            or reader.u32("arm_id") != self.arm_id
        ):
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding output row/arm order mismatch")
        comparison_count = reader.u64("distance_comparison_count")
        expected_label_count = (
            FULL_DIMENSIONS if self.arm_id == 3 else FULL_GROUP_COUNT
        )
        label_count = reader.u32("label_count")
        if label_count != expected_label_count:
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding output label count mismatch")
        labels = reader.u32s(label_count, "labels")
        paid_bytes = 32 if self.word_bits == 4 else 64
        payload_count = reader.u32("payload_count")
        if payload_count != paid_bytes:
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding output payload size mismatch")
        payload = reader.read_exact(payload_count, "payload")
        roundtrip_count = reader.u32("roundtrip_count")
        if roundtrip_count != label_count:
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding roundtrip count mismatch")
        roundtrip = reader.u32s(roundtrip_count, "roundtrip_labels")
        roundtrip_match = reader.u32("roundtrip_match")
        pack_operations = reader.u64("pack_operations")
        unpack_operations = reader.u64("unpack_operations")
        if (
            roundtrip != labels
            or roundtrip_match != 1
            or pack_operations != 1
            or unpack_operations != 1
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "encoding native roundtrip contract mismatch"
            )
        self.comparisons += comparison_count
        self.payload_bytes += payload_count
        self.pack_operations += pack_operations
        self.unpack_operations += unpack_operations
        return _NativeEncodedArmRow(
            arm_id=self.arm_id,
            labels=labels,
            payload=payload,
            roundtrip_labels=roundtrip,
            distance_comparisons=comparison_count,
            pack_operations=pack_operations,
            unpack_operations=unpack_operations,
        )

    def finish(self) -> None:
        reader = self.reader
        if reader.read_exact(8, "terminal") != _ENCODING_OUTPUT_TERMINAL:
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding output terminal mismatch")
        if (
            reader.u32("terminal_row_count") != FULL_ROWS
            or reader.u32("terminal_arm_count") != 1
        ):
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding output terminal shape mismatch")
        terminal = (
            reader.u32("terminal_arm_id"),
            reader.u64("terminal_comparisons"),
            reader.u64("terminal_payload_bytes"),
            reader.u64("terminal_pack_operations"),
            reader.u64("terminal_unpack_operations"),
        )
        expected = (
            self.arm_id,
            self.comparisons,
            self.payload_bytes,
            self.pack_operations,
            self.unpack_operations,
        )
        if terminal != expected:
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding output terminal totals mismatch")
        self.mixed_radix_encodes = reader.u64("terminal_mixed_radix_encodes")
        self.mixed_radix_decodes = reader.u64("terminal_mixed_radix_decodes")
        self.arm_vector_count = reader.u64("terminal_arm_vector_count")
        expected_mixed = FULL_ROWS * FULL_GROUP_COUNT if self.arm_id in (0, 1) else 0
        if (
            self.mixed_radix_encodes != expected_mixed
            or self.mixed_radix_decodes != expected_mixed
            or self.arm_vector_count != FULL_ROWS
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "encoding terminal operation counts mismatch"
            )
        self.native_owned_high_water = reader.u64(
            "terminal_owned_payload_high_water_bytes"
        )
        if self.native_owned_high_water <= 0:
            raise GateFailure(
                "IMPLEMENTATION_INVALID", "native encoding owned-buffer total is invalid"
            )
        reader.require_eof()


def _encoding_replay_chunk_labels(
    *,
    np: Any,
    word_bits: int,
    row_begin: int,
    row_end: int,
    matrix: Any,
    models: Sequence[CompactCoordinateModel],
    groups: Mapping[tuple[int, int], Mapping[str, Any]],
    globals_by_rate: Mapping[int, Mapping[str, Any]],
    block_centers: Mapping[tuple[int, int], Sequence[Sequence[str]]],
) -> tuple[tuple[Any, Any, Any, Any], tuple[int, int, int, int], int, int]:
    """Replay one fixed-size row chunk and report exact ndarray live bytes."""

    if not 0 <= row_begin < row_end <= FULL_ROWS:
        raise GateFailure("IMPLEMENTATION_INVALID", "encoding replay chunk is invalid")
    row_count = row_end - row_begin
    dyadic = np.empty((row_count, FULL_GROUP_COUNT), dtype=np.uint16)
    arbitrary = np.empty((row_count, FULL_GROUP_COUNT), dtype=np.uint16)
    block = np.empty((row_count, FULL_GROUP_COUNT), dtype=np.uint16)
    global_labels = np.empty((row_count, FULL_DIMENSIONS), dtype=np.uint16)
    outputs = (dyadic, arbitrary, block, global_labels)
    output_bytes = sum(int(value.nbytes) for value in outputs)
    live_high_water = output_bytes
    validation_comparisons = [0, 0, 0, 0]
    matrix_chunk = matrix[row_begin:row_end]
    for group_id in range(FULL_GROUP_COUNT):
        for arm_id, (source, destination) in enumerate(
            (("dyadic", dyadic), ("arbitrary", arbitrary))
        ):
            cardinalities = [
                int(value) for value in groups[(word_bits, group_id)][source]["cardinalities"]
            ]
            axis0, axis0_workspace = _replay_nearest_labels_numpy(
                np,
                matrix_chunk[:, 2 * group_id],
                models[2 * group_id].binary32_centroids[cardinalities[0]],
            )
            axis1, axis1_workspace = _replay_nearest_labels_numpy(
                np,
                matrix_chunk[:, 2 * group_id + 1],
                models[2 * group_id + 1].binary32_centroids[cardinalities[1]],
            )
            validation_comparisons[arm_id] += row_count * sum(cardinalities)
            combined = np.multiply(axis1, cardinalities[0])
            np.add(combined, axis0, out=combined)
            destination[:, group_id] = combined
            live_high_water = max(
                live_high_water,
                output_bytes + axis0_workspace,
                output_bytes + int(axis0.nbytes) + axis1_workspace,
                output_bytes
                + int(axis0.nbytes)
                + int(axis1.nbytes)
                + int(combined.nbytes),
            )
            del axis0, axis1, combined
        block_result, block_workspace = _replay_nearest_point_labels_numpy(
            np,
            matrix_chunk[:, (2 * group_id, 2 * group_id + 1)],
            block_centers[(word_bits, group_id)],
        )
        validation_comparisons[2] += row_count * len(
            block_centers[(word_bits, group_id)]
        )
        block[:, group_id] = block_result
        live_high_water = max(live_high_water, output_bytes + block_workspace)
        del block_result
    widths = [int(value) for value in globals_by_rate[word_bits]["bit_widths"]]
    for coordinate, width in enumerate(widths):
        global_centroids = models[coordinate].binary32_centroids[1 << width]
        global_result, global_workspace = _replay_nearest_labels_numpy(
            np,
            matrix_chunk[:, coordinate],
            global_centroids,
        )
        validation_comparisons[3] += row_count * len(global_centroids)
        global_labels[:, coordinate] = global_result
        live_high_water = max(live_high_water, output_bytes + global_workspace)
        del global_result
    return outputs, tuple(validation_comparisons), live_high_water, output_bytes


def _encoding_arm_record(
    labels: Sequence[int],
    payload: bytes,
    roundtrip: Sequence[int],
    *,
    distance_comparison_count: int,
) -> dict[str, Any]:
    logical = [int(value) for value in labels]
    replay = [int(value) for value in roundtrip]
    return {
        "label_count": len(logical),
        "labels": logical,
        "labels_sha256": _canonical_array_hash(logical),
        "payload_bytes": len(payload),
        "payload_hex": payload.hex(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "alignment_bytes": 1,
        "output_bytes": len(payload),
        "roundtrip_labels": replay,
        "roundtrip_labels_sha256": _canonical_array_hash(replay),
        "roundtrip_match": logical == replay,
        "distance_comparison_count": str(distance_comparison_count),
        "pack_operation_count": "1",
        "unpack_operation_count": "1",
    }


def _encoding_records(
    *,
    native_outputs: Mapping[str, Path],
    np: Any,
    word_bits: int,
    matrix: Any,
    models: Sequence[CompactCoordinateModel],
    groups: Mapping[tuple[int, int], Mapping[str, Any]],
    globals_by_rate: Mapping[int, Mapping[str, Any]],
    block_centers: Mapping[tuple[int, int], Sequence[Sequence[str]]],
    expected_comparisons: Sequence[int],
    global_widths: Sequence[int],
    parent_persistent_owned_bytes: int,
    totals: EncodingNativeTotals,
) -> Iterator[dict[str, Any]]:
    paid_bytes = 32 if word_bits == 4 else 64
    if set(native_outputs) != set(_ENCODING_ARM_NAMES) or len(expected_comparisons) != 4:
        raise GateFailure("IMPLEMENTATION_INVALID", "encoding replay arm shape mismatch")
    if len(global_widths) != FULL_DIMENSIONS or parent_persistent_owned_bytes <= 0:
        raise GateFailure("IMPLEMENTATION_INVALID", "encoding replay metadata mismatch")
    validation_distance_comparisons = {
        arm_name: 0 for arm_name in _ENCODING_ARM_NAMES
    }
    validation_pack_operations = {
        arm_name: 0 for arm_name in _ENCODING_ARM_NAMES
    }
    validation_unpack_operations = {
        arm_name: 0 for arm_name in _ENCODING_ARM_NAMES
    }
    with contextlib.ExitStack() as stack:
        streams = [
            stack.enter_context(
                _EncodingArmStream(
                    native_outputs[arm_name], arm_id=arm_id, word_bits=word_bits
                )
            )
            for arm_id, arm_name in enumerate(_ENCODING_ARM_NAMES)
        ]
        for row_begin in range(0, FULL_ROWS, _ENCODING_REPLAY_CHUNK_ROWS):
            row_end = min(FULL_ROWS, row_begin + _ENCODING_REPLAY_CHUNK_ROWS)
            native_chunk = [
                [stream.read_row(vector_id) for vector_id in range(row_begin, row_end)]
                for stream in streams
            ]
            native_chunk_payload_bytes = sum(
                row.logical_payload_bytes()
                for arm_rows in native_chunk
                for row in arm_rows
            )
            (
                replay_labels,
                replay_chunk_comparisons,
                replay_live_high_water,
                replay_output_bytes,
            ) = (
                _encoding_replay_chunk_labels(
                    np=np,
                    word_bits=word_bits,
                    row_begin=row_begin,
                    row_end=row_end,
                    matrix=matrix,
                    models=models,
                    groups=groups,
                    globals_by_rate=globals_by_rate,
                    block_centers=block_centers,
                )
            )
            for arm_name, comparison_count in zip(
                _ENCODING_ARM_NAMES, replay_chunk_comparisons
            ):
                validation_distance_comparisons[arm_name] += comparison_count
            totals.replay_workspace_high_water_bytes = max(
                totals.replay_workspace_high_water_bytes, replay_live_high_water
            )
            totals.python_owned_high_water_bytes = max(
                totals.python_owned_high_water_bytes,
                parent_persistent_owned_bytes
                + native_chunk_payload_bytes
                + replay_live_high_water,
            )
            for chunk_index, vector_id in enumerate(range(row_begin, row_end)):
                arms: dict[str, Any] = {}
                for arm_id, arm_name in enumerate(_ENCODING_ARM_NAMES):
                    native = native_chunk[arm_id][chunk_index]
                    labels = native.labels
                    payload = native.payload
                    roundtrip = native.roundtrip_labels
                    comparison_count = native.distance_comparisons
                    expected = [
                        int(value) for value in replay_labels[arm_id][chunk_index]
                    ]
                    if labels != expected:
                        raise GateFailure(
                            "IMPLEMENTATION_INVALID",
                            f"native encoding assignment replay mismatch B{word_bits} row {vector_id} arm {arm_name}",
                        )
                    if comparison_count != int(expected_comparisons[arm_id]):
                        raise GateFailure(
                            "IMPLEMENTATION_INVALID", "encoding comparison count mismatch"
                        )
                    if arm_id == 3:
                        if any(
                            label >= (1 << global_widths[coordinate])
                            for coordinate, label in enumerate(labels)
                        ):
                            raise GateFailure(
                                "IMPLEMENTATION_INVALID",
                                "global label exceeds nominal width",
                            )
                        validation_pack_operations[arm_name] += 1
                        validation_payload = reference.pack_global_labels(
                            labels, global_widths, paid_bytes
                        )
                        if validation_payload != payload:
                            raise GateFailure(
                                "IMPLEMENTATION_INVALID", "global payload replay mismatch"
                            )
                        validation_unpack_operations[arm_name] += 1
                        validation_roundtrip = list(
                            reference.unpack_global_labels(payload, global_widths)
                        )
                        if validation_roundtrip != roundtrip:
                            raise GateFailure(
                                "IMPLEMENTATION_INVALID", "global unpack replay mismatch"
                            )
                    else:
                        if any(label >= (1 << word_bits) for label in labels):
                            raise GateFailure(
                                "IMPLEMENTATION_INVALID",
                                "matched label exceeds word width",
                            )
                        validation_pack_operations[arm_name] += 1
                        validation_payload = reference.pack_matched_labels(
                            labels, word_bits
                        )
                        if validation_payload != payload:
                            raise GateFailure(
                                "IMPLEMENTATION_INVALID", "matched payload replay mismatch"
                            )
                        validation_unpack_operations[arm_name] += 1
                        validation_roundtrip = list(
                            reference.unpack_matched_labels(payload, word_bits)
                        )
                        if validation_roundtrip != roundtrip:
                            raise GateFailure(
                                "IMPLEMENTATION_INVALID", "matched unpack replay mismatch"
                            )
                    arms[arm_name] = _encoding_arm_record(
                        labels,
                        payload,
                        roundtrip,
                        distance_comparison_count=comparison_count,
                    )
                record = {
                    "record_type": "encoded_vector",
                    "word_bits": word_bits,
                    "vector_id": vector_id,
                    "arms": arms,
                }
                canonical_line_bytes = len(artifacts.canonical_json_bytes(record)) + 1
                current_record_bytes = (
                    _deterministic_owned_buffer_bytes(record)
                    + 2 * 4 * (3 * FULL_GROUP_COUNT + FULL_DIMENSIONS)
                )
                totals.current_record_high_water_bytes = max(
                    totals.current_record_high_water_bytes, current_record_bytes
                )
                totals.canonical_line_high_water_bytes = max(
                    totals.canonical_line_high_water_bytes, canonical_line_bytes
                )
                totals.python_owned_high_water_bytes = max(
                    totals.python_owned_high_water_bytes,
                    parent_persistent_owned_bytes
                    + native_chunk_payload_bytes
                    + replay_output_bytes
                    + current_record_bytes
                    + canonical_line_bytes,
                )
                yield record
        for stream in streams:
            stream.finish()

    aggregate_comparisons = [stream.comparisons for stream in streams]
    aggregate_payload_bytes = [stream.payload_bytes for stream in streams]
    aggregate_pack = [stream.pack_operations for stream in streams]
    aggregate_unpack = [stream.unpack_operations for stream in streams]
    for arm_id, arm_name in enumerate(_ENCODING_ARM_NAMES):
        expected_distance_total = int(expected_comparisons[arm_id]) * FULL_ROWS
        if (
            aggregate_comparisons[arm_id] != expected_distance_total
            or validation_distance_comparisons[arm_name] != expected_distance_total
            or validation_distance_comparisons[arm_name]
            != aggregate_comparisons[arm_id]
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"encoding native/validation distance work mismatch: {arm_name}",
            )
        if (
            aggregate_pack[arm_id] != FULL_ROWS
            or aggregate_unpack[arm_id] != FULL_ROWS
            or validation_pack_operations[arm_name] != FULL_ROWS
            or validation_unpack_operations[arm_name] != FULL_ROWS
        ):
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"encoding native/validation pack work mismatch: {arm_name}",
            )
    totals.row_count = FULL_ROWS
    totals.distance_comparisons = dict(zip(_ENCODING_ARM_NAMES, aggregate_comparisons))
    totals.validation_distance_comparisons = validation_distance_comparisons
    totals.payload_bytes = dict(zip(_ENCODING_ARM_NAMES, aggregate_payload_bytes))
    totals.pack_operations = dict(zip(_ENCODING_ARM_NAMES, aggregate_pack))
    totals.validation_pack_operations = validation_pack_operations
    totals.unpack_operations = dict(zip(_ENCODING_ARM_NAMES, aggregate_unpack))
    totals.validation_unpack_operations = validation_unpack_operations
    totals.mixed_radix_encodes = {
        stream.arm_name: stream.mixed_radix_encodes for stream in streams
    }
    totals.mixed_radix_decodes = {
        stream.arm_name: stream.mixed_radix_decodes for stream in streams
    }
    totals.arm_vector_counts = {
        stream.arm_name: stream.arm_vector_count for stream in streams
    }
    totals.owned_payload_high_water_bytes = max(
        stream.native_owned_high_water for stream in streams
    )


def _cost_output_ledger(
    completed: Sequence[Mapping[str, Any]],
    body_identity: artifacts.FileIdentity | None = None,
) -> list[dict[str, Any]]:
    entries = [
        {
            "path": str(entry["path"]),
            "role": str(entry["role"]),
            "size_bytes": int(entry["size_bytes"]),
            "sha256": str(entry["sha256"]),
            "timed": True,
        }
        for entry in completed
    ]
    if body_identity is not None:
        entries.append(
            {
                "path": "detail/timed_output_ledger_body.json",
                "role": "timed_output_ledger_body",
                "size_bytes": body_identity.size_bytes,
                "sha256": body_identity.sha256,
                "timed": True,
            }
        )
    return artifacts.sort_ledger(entries)


def _finalize_cost_projection(
    *,
    output_dir: Path,
    plan: Sequence[Mapping[str, Any]],
    completed: Sequence[Mapping[str, Any]],
    checkpoint: Mapping[str, Any],
    timed_status: str,
    projection_complete: bool,
    implementation_commit: str,
    parity_evidence_commit: str,
    parity_review_commit: str,
    execution_commit: str,
    thread_environment: Mapping[str, str],
    input_ledger: Sequence[Mapping[str, Any]],
    runtime_numeric: Mapping[str, Any],
    parity_build: Mapping[str, Any],
    array_identity: Mapping[str, Any],
    clock: ComponentClock,
    counters: dict[str, Any],
) -> str:
    if [entry["index"] for entry in completed] != list(range(len(completed))):
        raise GateFailure("IMPLEMENTATION_INVALID", "completed cost shards are not a prefix")
    missing = [dict(entry) for entry in plan[len(completed) :]]
    body_common = artifacts.common_artifact_fields(
        status=timed_status,
        implementation_commit=implementation_commit,
        execution_commit=execution_commit,
        command=sys.argv,
        thread_environment=thread_environment,
        input_ledger=input_ledger,
        output_ledger=_cost_output_ledger(completed),
    )
    body = artifacts.add_artifact_body(
        body_common,
        {
            "planned_shards": [dict(entry) for entry in plan],
            "completed_shards": [dict(entry) for entry in completed],
            "missing_suffix": missing,
            "checkpoint": dict(checkpoint),
            "projection_complete": projection_complete,
            "terminal_status": timed_status,
        },
    )
    body_path = output_dir / "detail/timed_output_ledger_body.json"
    body_path.parent.mkdir(parents=True, exist_ok=True)
    body_serialized_payload_bytes = len(artifacts.canonical_json_bytes(body)) + 1
    _update_supervisor_owned_buffer_hwm(
        counters,
        "output",
        plan,
        completed,
        missing,
        body_common,
        body,
        checkpoint,
        transient_payload_bytes=body_serialized_payload_bytes,
    )
    body_identity = artifacts.write_canonical_json(body_path, body)
    # These hashes/ledger normalizations describe timed-region results.  They
    # must be completed before the authority-bearing end snapshot so the
    # four-file trailer only copies already-derived identities.
    output_ledger = _cost_output_ledger(completed, body_identity)
    ordered_completed_shards_payload = artifacts.canonical_json_bytes(
        [dict(entry) for entry in completed]
    )
    ordered_completed_shards_sha256 = artifacts.sha256_bytes(
        ordered_completed_shards_payload
    )
    _update_supervisor_owned_buffer_hwm(
        counters,
        "output",
        plan,
        completed,
        missing,
        body,
        output_ledger,
        transient_payload_bytes=len(ordered_completed_shards_payload),
    )

    # Authority-bearing end snapshot: no model or shard work may occur after
    # this point.  Only the registered four-file trailer follows.
    total_cpu, total_wall, component_cpu, component_wall, peak_rss_bytes = clock.finish()
    gate_left = 5 * total_cpu
    gate_right = 2 * PROJECTED_LIMIT_US
    gate_pass = gate_left <= gate_right
    if timed_status == "PENDING_FINAL_CPU_DECISION":
        final_status = _resolve_frozen_terminal_status(
            [] if gate_pass else ["NO_GO_EXACT_SOLVER_COST"]
        )
    else:
        final_status = _resolve_frozen_terminal_status([timed_status])
    timing = {
        "timed_region_cpu_microseconds": total_cpu,
        "projected_cpu_numerator_microseconds": gate_left,
        "projected_cpu_denominator": 2,
        "base_cpu_limit_microseconds": PROJECTED_LIMIT_US,
        "gate_left_integer": gate_left,
        "gate_right_integer": gate_right,
        "gate_pass": gate_pass,
        "component_cpu_microseconds": component_cpu,
        "component_wall_nanoseconds": component_wall,
    }
    common = artifacts.common_artifact_fields(
        status=final_status,
        implementation_commit=implementation_commit,
        execution_commit=execution_commit,
        command=sys.argv,
        thread_environment=thread_environment,
        input_ledger=input_ledger,
        output_ledger=output_ledger,
    )
    manifest = artifacts.add_artifact_body(
        common,
        {
            "artifact_kind": "synthetic_cost_projection_manifest",
            "array_identity": dict(array_identity),
            "runtime_numeric": dict(runtime_numeric),
            "parity_evidence_commit": parity_evidence_commit,
            "parity_review_commit": parity_review_commit,
            "projection_complete": projection_complete,
            "outcome": final_status,
            **timing,
        },
    )
    summary = artifacts.add_artifact_body(
        common,
        {
            "artifact_kind": "synthetic_cost_projection_summary",
            "array_identity": dict(array_identity),
            "shape_checks": {
                "rows": FULL_ROWS,
                "dimensions": FULL_DIMENSIONS,
                "groups": FULL_GROUP_COUNT,
                "rates": [4, 8],
                "scalar_cardinality_maximum": FULL_COORDINATE_CARDINALITY,
                "block_start_count": BLOCK_START_COUNT,
                "completed_shard_count": len(completed),
                "planned_shard_count": len(plan),
            },
            "projection_complete": projection_complete,
            "outcome": final_status,
            "peak_rss_bytes": peak_rss_bytes,
            "peak_rss_definition": (
                "Linux ru_maxrss(RUSAGE_SELF) plus ru_maxrss(RUSAGE_CHILDREN), "
                "converted from KiB to bytes; conservative process-family bound"
            ),
            "deterministic_owned_buffer_high_water_bytes": int(counters.get("owned_buffer_high_water_bytes", 0)),
            "deterministic_owned_buffer_definition": (
                "conservative high-water upper bound for unique logical payload "
                "bytes simultaneously owned by the timed-region Python supervisor, including "
                "registered parser/text frames and canonical output-line frames; "
                "interpreter object headers and allocator slack excluded"
            ),
            "deterministic_owned_buffer_scope": {
                "included": (
                    "Python supervisor ndarray, array.array, byte/string, "
                    "container, dataclass, parser-frame, replay-workspace, and "
                    "canonical-line logical payloads across every pipeline stage"
                ),
                "excluded": (
                    "native child address spaces, GMP/MPFR allocator internals, "
                    "interpreter object headers, and allocator slack"
                ),
                "native_memory_coverage": (
                    "all native children are covered by the separately reported "
                    "conservative process-family peak_rss_bytes; encoding children "
                    "also report a deterministic payload high water per rate"
                ),
            },
            "supervisor_owned_buffer_stage_high_water_bytes": dict(
                counters.get(
                    "supervisor_owned_buffer_stage_high_water_bytes", {}
                )
            ),
            "operation_counts": {
                key: int(value)
                for key, value in counters.items()
                if isinstance(value, int) and key != "owned_buffer_high_water_bytes"
            },
            "comparison_counts": dict(counters.get("comparison_counts", {})),
            "iteration_counts": dict(counters.get("iteration_counts", {})),
            "representation_bytes": dict(counters.get("representation_bytes", {})),
            "address_counts": dict(counters.get("address_counts", {})),
            "selected_cardinalities": dict(counters.get("selected_cardinalities", {})),
            "distinct_center_checks": dict(counters.get("distinct_center_checks", {})),
            "encoding_arm_operation_counts": dict(
                counters.get("encoding_arm_operation_counts", {})
            ),
            "encoding_arm_timings": dict(counters.get("encoding_arm_timings", {})),
            "encoding_memory_accounting": dict(
                counters.get("encoding_memory_accounting", {})
            ),
            "allocation_item_memory_accounting": dict(
                counters.get("allocation_item_memory_accounting", {})
            ),
            "checkpoint": dict(checkpoint),
            **timing,
        },
    )
    detail_wrapper = artifacts.add_artifact_body(
        common,
        {
            "artifact_kind": "synthetic_cost_projection_detail_ledger",
            "timed_output_ledger_body": body,
            "timed_output_ledger_body_sha256": body_identity.sha256,
            "ordered_completed_shards_sha256": (
                ordered_completed_shards_sha256
            ),
            "projection_complete": projection_complete,
            "outcome": final_status,
            **timing,
        },
    )
    wrappers = (
        ("synthetic_cost_projection_manifest.json", manifest),
        ("synthetic_cost_projection_summary.json", summary),
        ("synthetic_cost_projection_detail_ledger.json", detail_wrapper),
    )
    for filename, value in wrappers:
        artifacts.write_canonical_json(output_dir / filename, value)
    index_entries = [
        artifacts.make_artifact_index_entry(
            output_dir / filename,
            ledger_path=filename,
            producer_execution_commit=execution_commit,
        )
        for filename, _ in wrappers
    ]
    index = artifacts.make_artifact_index(
        common,
        index_entries,
        index_ledger_path="cost_projection_artifact_index.json",
    )
    artifacts.write_canonical_json(output_dir / "cost_projection_artifact_index.json", index)
    return final_status


def _representation_failure(
    models: Sequence[CompactCoordinateModel],
    groups: Mapping[tuple[int, int], Mapping[str, Any]],
    globals_by_rate: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any] | None:
    for word_bits in (4, 8):
        for group_id in range(64):
            raw = groups[(word_bits, group_id)]
            for source, arm_name in (("dyadic", "dyadic_word"), ("arbitrary", "arbitrary_word")):
                arm = raw[source]
                cardinalities = [int(value) for value in arm["cardinalities"]]
                effective_cardinalities = [
                    models[2 * group_id + offset].effective_cardinalities[cardinality]
                    for offset, cardinality in enumerate(cardinalities)
                ]
                calculated_reachable = effective_cardinalities == cardinalities
                if bool(arm.get("reachable")) != calculated_reachable:
                    raise GateFailure(
                        "IMPLEMENTATION_INVALID",
                        f"allocation reachability flag mismatch B{word_bits} group {group_id} {arm_name}",
                    )
                if not calculated_reachable:
                    for cardinality, effective in zip(
                        cardinalities, effective_cardinalities
                    ):
                        if effective != cardinality:
                            return {
                                "word_bits": word_bits,
                                "group_id": group_id,
                                "arm": arm_name,
                                "requested_cardinality": cardinality,
                                "effective_cardinality": effective,
                                "center_count": cardinality,
                                "distinct_center_count": effective,
                            }
                for offset, cardinality in enumerate(cardinalities):
                    bits = models[2 * group_id + offset].binary32_centroids[int(cardinality)]
                    values = [reference.bits_to_float32(int(value)) for value in bits]
                    for label, (left, right) in enumerate(zip(values, values[1:])):
                        if not left < right:
                            return {
                                "word_bits": word_bits,
                                "group_id": group_id,
                                "arm": arm_name,
                                "requested_cardinality": int(cardinality),
                                "effective_cardinality": len(bits),
                                "first_colliding_label": label,
                                "center_count": len(bits),
                                "distinct_center_count": len(set(bits)),
                            }
        # The global capped allocation is an attribution control.  Its
        # reachability is reported by the cost summary, but Section 2.4
        # explicitly forbids it from determining passage.
    return None


def _discard_unpublished_cost_suffix(state: CostTerminalState) -> None:
    if state.working is not None and state.working.exists():
        shutil.rmtree(state.working)
    if state.output_dir is None or state.plan is None or state.completed is None:
        return
    completed_paths = {str(entry["path"]) for entry in state.completed}
    for entry in state.plan:
        relative = str(entry["path"])
        if relative in completed_paths:
            continue
        path = state.output_dir / relative
        temporary = path.with_suffix(path.suffix + ".tmp")
        for candidate in (path, temporary):
            if candidate.is_file() or candidate.is_symlink():
                candidate.unlink()


def _terminalize_cost_failure(state: CostTerminalState, failure: GateFailure) -> str:
    if (
        not state.ready
        or state.finalizing
        or state.output_dir is None
        or state.plan is None
        or state.completed is None
        or state.clock is None
        or state.thread_environment is None
        or state.input_ledger is None
        or state.runtime_numeric is None
        or state.parity_build is None
        or state.counters is None
    ):
        raise failure
    if failure.status not in {"ARTIFACT_INVALID", "IMPLEMENTATION_INVALID", "CONTROL_INVALID"}:
        raise failure
    state.finalizing = True
    state.clock.switch("shard_serialization")
    _discard_unpublished_cost_suffix(state)
    context = dict(state.context or {})
    path: str | None = None
    if 0 <= state.current_plan_index < len(state.plan):
        path = str(state.plan[state.current_plan_index]["path"])
    operation_count = sum(
        int(value)
        for key, value in state.counters.items()
        if key != "owned_buffer_high_water_bytes"
        and isinstance(value, int)
        and value >= 0
    )
    checkpoint = _checkpoint(
        phase=state.phase,
        completed_operation_count=operation_count,
        last_completed_plan_index=len(state.completed) - 1,
        cumulative_cpu_microseconds=state.clock.cumulative_cpu_us(),
        reason_code=f"REGISTERED_{failure.status}",
        message=failure.detail,
        path=path,
        **context,
    )
    return _finalize_cost_projection(
        output_dir=state.output_dir,
        plan=state.plan,
        completed=state.completed,
        checkpoint=checkpoint,
        timed_status=failure.status,
        projection_complete=False,
        implementation_commit=state.implementation_commit,
        parity_evidence_commit=state.parity_evidence_commit,
        parity_review_commit=state.parity_review_commit,
        execution_commit=state.execution_commit,
        thread_environment=state.thread_environment,
        input_ledger=state.input_ledger,
        runtime_numeric=state.runtime_numeric,
        parity_build=state.parity_build,
        array_identity=state.array_identity or {},
        clock=state.clock,
        counters=state.counters,
    )


def _run_cost_projection(args: argparse.Namespace, start_cpu_us: int, start_wall_ns: int) -> str:
    state = CostTerminalState()
    try:
        return _execute_cost_projection(args, start_cpu_us, start_wall_ns, state)
    except artifacts.ArtifactContractError as error:
        return _terminalize_cost_failure(
            state, GateFailure("IMPLEMENTATION_INVALID", str(error))
        )
    except GateFailure as failure:
        return _terminalize_cost_failure(state, failure)


def _execute_cost_projection(
    args: argparse.Namespace,
    start_cpu_us: int,
    start_wall_ns: int,
    terminal_state: CostTerminalState,
) -> str:
    clock = ComponentClock(start_cpu_us, start_wall_ns)
    (
        output_dir,
        execution_commit,
        thread_environment,
        ledger,
        runtime,
        preflight_owned_buffer_high_water,
    ) = _preflight(args)
    (
        implementation_commit,
        parity_evidence_commit,
        parity_review_commit,
        parity_ledger,
        parity_build,
        parity_preflight_owned_buffer_high_water,
    ) = _load_and_validate_parity_checkpoint(execution_commit, runtime)
    ledger = artifacts.sort_ledger([*ledger, *parity_ledger])
    np = _load_numpy()
    if np.__version__ != parity_build.get("numpy_version"):
        raise GateFailure("IMPLEMENTATION_INVALID", "NumPy changed since parity")
    plan = _cost_plan()
    completed: list[dict[str, Any]] = []
    counters: dict[str, Any] = {
        "scalar_coordinate_count": 0,
        "scalar_curve_count": 0,
        "scalar_exact_replay_interval_count": 0,
        "scalar_native_matrix_entry_evaluation_count": 0,
        "scalar_native_interval_evaluation_count": 0,
        "scalar_native_exact_replay_check_count": 0,
        "allocation_item_count": 0,
        "group_allocation_count": 0,
        "global_allocation_count": 0,
        "block_model_count": 0,
        "block_start_count": 0,
        "encoding_native_arm_count": 0,
        "encoded_vector_rate_count": 0,
        "encoding_native_pack_operation_count": 0,
        "encoding_validation_pack_operation_count": 0,
        "encoding_total_pack_operation_count": 0,
        "encoding_native_unpack_operation_count": 0,
        "encoding_validation_unpack_operation_count": 0,
        "encoding_total_unpack_operation_count": 0,
        "owned_buffer_high_water_bytes": max(
            preflight_owned_buffer_high_water,
            parity_preflight_owned_buffer_high_water,
        ),
        "supervisor_owned_buffer_stage_high_water_bytes": {
            "preflight": max(
                preflight_owned_buffer_high_water,
                parity_preflight_owned_buffer_high_water,
            )
        },
        "comparison_counts": {
            "scalar_exact_objective": 0,
            "scalar_exact_ties": 0,
            "product_candidate_evaluations": 0,
            "product_validation_feasible_tuple_evaluations": 0,
            "global_transition_evaluations": 0,
            "global_validation_transition_evaluations": 0,
            "block_distance": 0,
            "block_native_distance": 0,
            "block_validation_step_final_distance": 0,
            "block_validation_parser_step_distance": 0,
            "block_native_cartesian_fill_distance": 0,
            "block_validation_cartesian_fill_distance": 0,
            "block_best_of_eight_final_sse_comparisons": 0,
            "block_native_best_of_eight_final_sse_comparisons": 0,
            "block_validation_best_of_eight_final_sse_comparisons": 0,
            "block_assignment_ties": 0,
            "block_native_assignment_ties": 0,
            "block_validation_assignment_ties": 0,
            "block_farthest_ties": 0,
            "encoding_native_distance": 0,
            "encoding_validation_distance": 0,
            "encoding_total_distance": 0,
        },
        "iteration_counts": {
            "block_complete_iterations": 0,
            "block_accepted_updates": 0,
        },
        "representation_bytes": {
            "codebook": {},
            "radix_and_address_metadata": {},
            "expanded_lookup": {},
            "database_payload": {},
        },
        "address_counts": {},
        "selected_cardinalities": {"group_arms": [], "global_control": []},
        "distinct_center_checks": {
            "scalar_selected_alphabet_checks": 0,
            "scalar_selected_alphabet_failures": 0,
            "block_selected_codebook_checks": 0,
            "block_selected_codebook_failures": 0,
            "global_control_unreachable_alphabets": 0,
        },
        "encoding_arm_operation_counts": {},
        "encoding_arm_timings": {},
        "encoding_memory_accounting": {},
        "allocation_item_memory_accounting": {
            "input_file_bytes_total": 0,
            "output_file_bytes_total": 0,
            "maximum_input_serialization_live_bytes": 0,
            "maximum_output_parse_and_validation_live_bytes": 0,
            "scope": (
                "item-local Python request bytearray, strict output read/parse "
                "buffers, independent exhaustive-product state, and global-DP "
                "validation state; each is combined with then-live persistent roots in "
                "deterministic_owned_buffer_high_water_bytes"
            ),
        },
    }
    terminal_state.output_dir = output_dir
    terminal_state.plan = plan
    terminal_state.completed = completed
    terminal_state.implementation_commit = implementation_commit
    terminal_state.parity_evidence_commit = parity_evidence_commit
    terminal_state.parity_review_commit = parity_review_commit
    terminal_state.execution_commit = execution_commit
    terminal_state.thread_environment = thread_environment
    terminal_state.input_ledger = ledger
    terminal_state.runtime_numeric = runtime
    terminal_state.parity_build = parity_build
    terminal_state.clock = clock
    terminal_state.counters = counters
    terminal_state.phase = "preflight"
    terminal_state.context = {}
    terminal_state.ready = True

    clock.switch("generation_and_order")
    generator = np.random.Generator(np.random.PCG64(SEED))
    matrix = generator.standard_normal((FULL_ROWS, FULL_DIMENSIONS), dtype=np.float32)
    if matrix.shape != (FULL_ROWS, FULL_DIMENSIONS) or matrix.dtype != np.dtype("float32") or not matrix.flags.c_contiguous:
        raise GateFailure("IMPLEMENTATION_INVALID", "synthetic array shape/dtype/order mismatch")
    row_order_vector_ids = list(range(FULL_ROWS))
    selection_digests = [
        hashlib.sha256(
            f"{SCIENTIFIC_PROTOCOL_VERSION}|synthetic_cost_projection|0|{vector_id}".encode("utf-8")
        ).hexdigest()
        for vector_id in row_order_vector_ids
    ]
    per_row_raw_sha256 = [
        hashlib.sha256(memoryview(matrix[vector_id]).cast("B")).hexdigest()
        for vector_id in row_order_vector_ids
    ]
    raw_matrix_sha256 = hashlib.sha256(memoryview(matrix).cast("B")).hexdigest()
    array_identity = {
        "generator": "Generator(PCG64(20260713))",
        "numpy_version": np.__version__,
        "dtype": matrix.dtype.str,
        "endianness": "little" if matrix.dtype.byteorder in ("<", "=", "|") and sys.byteorder == "little" else matrix.dtype.byteorder,
        "shape": [FULL_ROWS, FULL_DIMENSIONS],
        "c_order": True,
        "raw_byte_count": int(matrix.nbytes),
        "sha256": raw_matrix_sha256,
        "per_row_raw_sha256": per_row_raw_sha256,
        "per_row_raw_sha256_sha256": _sha256_canonical_array(per_row_raw_sha256),
        "registered_row_order": {
            "rule": "ascending synthetic vector_id, inclusive range [0,8191]",
            "vector_ids": row_order_vector_ids,
            "vector_ids_sha256": _sha256_canonical_array(row_order_vector_ids),
            "selection_digests_sha256": _sha256_canonical_array(selection_digests),
        },
        "selection_digests_sha256": _sha256_canonical_array(selection_digests),
    }
    terminal_state.array_identity = array_identity
    _update_supervisor_owned_buffer_hwm(
        counters,
        "generation_and_order",
        matrix,
        row_order_vector_ids,
        selection_digests,
        per_row_raw_sha256,
        array_identity,
        ledger,
        plan,
        completed,
        runtime,
        parity_build,
        thread_environment,
        transient_payload_bytes=FULL_ROWS * 4,
    )

    working = output_dir / ".working"
    working.mkdir()
    terminal_state.working = working
    models: list[CompactCoordinateModel] = []
    scalar_common_roots = (
        matrix,
        row_order_vector_ids,
        selection_digests,
        per_row_raw_sha256,
        array_identity,
        models,
        ledger,
        plan,
        completed,
        runtime,
        parity_build,
        thread_environment,
        counters,
    )
    clock.switch("scalar")
    for coordinate in range(FULL_DIMENSIONS):
        terminal_state.phase = "scalar"
        terminal_state.current_plan_index = coordinate
        terminal_state.context = {"coordinate_id": coordinate}
        scalar_input = working / "scalar_input.bin"
        scalar_output = working / "scalar_output.tsv"
        bits = tuple(int(value) for value in matrix[:, coordinate].view(np.uint32))
        cost_case = ScalarCase(
            0,
            "synthetic_cost_projection",
            bits,
            tuple(1 for _ in range(FULL_ROWS)),
            tuple(range(FULL_ROWS)),
            FULL_COORDINATE_CARDINALITY,
            coordinate,
        )
        _write_scalar_input(scalar_input, (cost_case,))
        _update_supervisor_owned_buffer_hwm(
            counters,
            "scalar",
            *scalar_common_roots,
            bits,
            cost_case,
            terminal_state.context,
            transient_payload_bytes=32,
        )
        _run_native(("scalar-suite", str(scalar_input), str(scalar_output)))
        try:
            scalar_output_file_bytes = scalar_output.stat().st_size
        except OSError as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"cannot stat scalar native output: {error}",
            ) from error
        parsed_cases = _parse_scalar_output(scalar_output)
        parsed = parsed_cases.get(0)
        if parsed is None or parsed["sample_count"] != FULL_ROWS:
            raise GateFailure("IMPLEMENTATION_INVALID", "cost scalar output shape mismatch")
        if not all(parsed["monotone"].values()):
            raise GateFailure("IMPLEMENTATION_INVALID", f"cost scalar predecessor failure coordinate {coordinate}")
        (
            scalar_replays,
            scalar_replay_interval_count,
            scalar_replay_internal_high_water,
        ) = (
            _independent_scalar_solution_replays(parsed)
        )
        counters["scalar_exact_replay_interval_count"] += (
            scalar_replay_interval_count
        )
        model = _compact_coordinate_model(parsed)
        models.append(model)
        counters["comparison_counts"]["scalar_exact_objective"] += sum(
            int(solution["comparison_count"])
            for solution in parsed["solutions"].values()
        )
        counters["comparison_counts"]["scalar_exact_ties"] += sum(
            int(solution["exact_tie_count"])
            for solution in parsed["solutions"].values()
        )
        counters["scalar_native_matrix_entry_evaluation_count"] += int(
            parsed["diagnostics"]["matrix_entry_evaluations"]
        )
        counters["scalar_native_interval_evaluation_count"] += int(
            parsed["diagnostics"]["interval_evaluations"]
        )
        counters["scalar_native_exact_replay_check_count"] += int(
            parsed["diagnostics"]["exact_replay_checks"]
        )
        # ASCII parser bound: input bytes + at most three simultaneous Python
        # text/split payload copies, each conservatively charged at UCS-4.
        scalar_parser_payload_bound = 13 * scalar_output_file_bytes
        _update_supervisor_owned_buffer_hwm(
            counters,
            "scalar",
            *scalar_common_roots,
            bits,
            cost_case,
            parsed_cases,
            scalar_replays,
            terminal_state.context,
            transient_payload_bytes=(
                scalar_parser_payload_bound
                + scalar_replay_internal_high_water
            ),
        )
        scalar_input.unlink()
        scalar_output.unlink()
        counters["scalar_coordinate_count"] += 1
        counters["scalar_curve_count"] += 256

        # The frozen protocol has two distinct checkpoints here: completion
        # of the scalar model and completion of its normal output shard.  Do
        # not serialize the shard after the model checkpoint has already made
        # an unmasked cost no-go irreversible.
        if clock.cumulative_cpu_us() > CPU_PANEL_LIMIT_US:
            clock.switch("shard_serialization")
            checkpoint = _checkpoint(
                phase="scalar",
                completed_operation_count=counters["scalar_coordinate_count"],
                last_completed_plan_index=coordinate - 1,
                cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
                reason_code="RUNNING_CPU_LOWER_BOUND_EXCEEDED",
                message=(
                    "complete scalar-coordinate model checkpoint crossed "
                    "the frozen panel CPU limit"
                ),
                path=plan[coordinate]["path"],
                coordinate_id=coordinate,
            )
            shutil.rmtree(working)
            terminal_state.working = None
            terminal_state.finalizing = True
            return _finalize_cost_projection(
                output_dir=output_dir,
                plan=plan,
                completed=completed,
                checkpoint=checkpoint,
                timed_status="NO_GO_EXACT_SOLVER_COST",
                projection_complete=False,
                implementation_commit=implementation_commit,
                parity_evidence_commit=parity_evidence_commit,
                parity_review_commit=parity_review_commit,
                execution_commit=execution_commit,
                thread_environment=thread_environment,
                input_ledger=ledger,
                runtime_numeric=runtime,
                parity_build=parity_build,
                array_identity=array_identity,
                clock=clock,
                counters=counters,
            )

        clock.switch("shard_serialization")
        entry = _publish_jsonl_shard(
            output_dir,
            plan[coordinate],
            _records_with_supervisor_hwm(
                (
                    _cost_scalar_record(
                        coordinate,
                        cardinality,
                        parsed,
                        scalar_replays[cardinality],
                    )
                    for cardinality in range(1, 257)
                ),
                counters=counters,
                persistent_roots=(
                    *scalar_common_roots,
                    bits,
                    cost_case,
                    parsed_cases,
                    scalar_replays,
                ),
            ),
        )
        completed.append(entry)
        del bits, cost_case, parsed, parsed_cases, scalar_replays
        if clock.cumulative_cpu_us() > CPU_PANEL_LIMIT_US:
            checkpoint = _checkpoint(
                phase="scalar",
                completed_operation_count=counters["scalar_coordinate_count"],
                last_completed_plan_index=coordinate,
                cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
                reason_code="RUNNING_CPU_LOWER_BOUND_EXCEEDED",
                message=(
                    "complete scalar output-shard checkpoint crossed the "
                    "frozen panel CPU limit"
                ),
                path=plan[coordinate]["path"],
                coordinate_id=coordinate,
            )
            shutil.rmtree(working)
            terminal_state.working = None
            terminal_state.finalizing = True
            return _finalize_cost_projection(
                output_dir=output_dir,
                plan=plan,
                completed=completed,
                checkpoint=checkpoint,
                timed_status="NO_GO_EXACT_SOLVER_COST",
                projection_complete=False,
                implementation_commit=implementation_commit,
                parity_evidence_commit=parity_evidence_commit,
                parity_review_commit=parity_review_commit,
                execution_commit=execution_commit,
                thread_environment=thread_environment,
                input_ledger=ledger,
                runtime_numeric=runtime,
                parity_build=parity_build,
                array_identity=array_identity,
                clock=clock,
                counters=counters,
            )
        clock.switch("scalar")

    clock.switch("allocation")
    terminal_state.phase = "allocation"
    terminal_state.current_plan_index = 128
    terminal_state.context = {}
    product_items: dict[int, Mapping[str, Any]] = {}
    global_items: dict[int, Mapping[str, Any]] = {}
    representation_failure: dict[str, Any] | None = None
    allocation: dict[str, Any] | None = None
    allocation_records: list[dict[str, Any]] | None = None
    groups: dict[tuple[int, int], Mapping[str, Any]] | None = None
    globals_by_rate: dict[int, Mapping[str, Any]] | None = None
    cost_lower_bound_crossed = False
    allocation_memory = counters["allocation_item_memory_accounting"]

    for item_id in range(_ALLOCATION_ITEM_COUNT):
        if item_id < 256:
            rate_index = item_id // 128
            group_id = (item_id % 128) // 2
            cardinality_set = item_id % 2
            item_context = {
                "word_bits": 4 if rate_index == 0 else 8,
                "group_id": group_id,
                "arm": (
                    "arbitrary_word"
                    if cardinality_set == _ALLOCATION_ARBITRARY_SET
                    else "dyadic_word"
                ),
            }
        else:
            item_context = {
                "word_bits": 4 if item_id == 256 else 8,
                "arm": "global_dyadic_pack_cap8",
            }
        terminal_state.context = item_context
        allocation_input = working / f"allocation_item_{item_id:03d}_input.bin"
        allocation_output = working / f"allocation_item_{item_id:03d}_output.bin"
        persistent_before_item = _deterministic_owned_buffer_bytes(
            matrix,
            selection_digests,
            per_row_raw_sha256,
            array_identity,
            models,
            product_items,
            global_items,
            ledger,
            plan,
            completed,
            runtime,
            parity_build,
            thread_environment,
            counters,
            item_context,
        )
        input_file_bytes, input_live_bytes = _write_allocation_item_input(
            allocation_input, item_id=item_id, models=models
        )
        allocation_memory["input_file_bytes_total"] += input_file_bytes
        allocation_memory["maximum_input_serialization_live_bytes"] = max(
            allocation_memory["maximum_input_serialization_live_bytes"],
            input_live_bytes,
        )
        _update_supervisor_owned_buffer_hwm(
            counters,
            "allocation",
            transient_payload_bytes=persistent_before_item + input_live_bytes,
        )
        _run_native(
            ("allocation-item", str(allocation_input), str(allocation_output))
        )
        try:
            output_file_bytes = allocation_output.stat().st_size
        except OSError as error:
            raise GateFailure(
                "IMPLEMENTATION_INVALID",
                f"cannot stat allocation-item output: {error}",
            ) from error
        (
            parsed_item,
            output_live_bytes,
            validation_product_visit_count,
            validation_transition_count,
        ) = _parse_allocation_item_output(
            allocation_output,
            expected_item_id=item_id,
            models=models,
        )
        counters["comparison_counts"][
            "product_validation_feasible_tuple_evaluations"
        ] += validation_product_visit_count
        counters["comparison_counts"][
            "global_validation_transition_evaluations"
        ] += validation_transition_count
        allocation_memory["output_file_bytes_total"] += output_file_bytes
        allocation_memory["maximum_output_parse_and_validation_live_bytes"] = max(
            allocation_memory[
                "maximum_output_parse_and_validation_live_bytes"
            ],
            output_live_bytes,
        )
        _update_supervisor_owned_buffer_hwm(
            counters,
            "allocation",
            transient_payload_bytes=persistent_before_item + output_live_bytes,
        )
        allocation_input.unlink()
        allocation_output.unlink()

        if item_id < 256:
            product_items[item_id] = parsed_item
            if item_id % 2 == 1:
                counters["group_allocation_count"] += 1
            item_representation_failure = _product_item_representation_failure(
                item_id=item_id, arm=parsed_item, models=models
            )
            if (
                representation_failure is None
                and item_representation_failure is not None
            ):
                representation_failure = item_representation_failure
        else:
            global_items[item_id] = parsed_item
            counters["global_allocation_count"] += 1
        counters["allocation_item_count"] += 1

        # Item 257 completes the exact old-consumer inventory.  Resolve the
        # authoritative full representation condition before this item's CPU
        # decision, but do not publish the 130-record shard until the distinct
        # item checkpoint permits continuation.
        if item_id == _ALLOCATION_ITEM_COUNT - 1:
            try:
                allocation = _assemble_allocation_items(
                    product_items, global_items
                )
                allocation_records, groups, globals_by_rate = _allocation_records(
                    allocation, models
                )
                representation_failure = _representation_failure(
                    models, groups, globals_by_rate
                )
            except GateFailure:
                raise
            except (
                AttributeError,
                IndexError,
                KeyError,
                TypeError,
                ValueError,
                OverflowError,
            ) as error:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    f"malformed allocation-item inventory: {error}",
                ) from error
            _update_supervisor_owned_buffer_hwm(
                counters,
                "allocation",
                matrix,
                row_order_vector_ids,
                selection_digests,
                per_row_raw_sha256,
                array_identity,
                models,
                product_items,
                global_items,
                allocation,
                allocation_records,
                groups,
                globals_by_rate,
                ledger,
                plan,
                completed,
                runtime,
                parity_build,
                thread_environment,
                counters,
                item_context,
            )

        crossed_at_item = clock.cumulative_cpu_us() > CPU_PANEL_LIMIT_US
        cost_lower_bound_crossed = cost_lower_bound_crossed or crossed_at_item
        if crossed_at_item and representation_failure is None:
            clock.switch("shard_serialization")
            checkpoint = _checkpoint(
                phase="allocation",
                completed_operation_count=counters["allocation_item_count"],
                last_completed_plan_index=127,
                cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
                reason_code="RUNNING_CPU_LOWER_BOUND_EXCEEDED",
                message=(
                    "complete allocation-item checkpoint crossed the frozen "
                    "panel CPU limit"
                ),
                path=plan[128]["path"],
                **item_context,
            )
            shutil.rmtree(working)
            terminal_state.working = None
            terminal_state.finalizing = True
            return _finalize_cost_projection(
                output_dir=output_dir,
                plan=plan,
                completed=completed,
                checkpoint=checkpoint,
                timed_status="NO_GO_EXACT_SOLVER_COST",
                projection_complete=False,
                implementation_commit=implementation_commit,
                parity_evidence_commit=parity_evidence_commit,
                parity_review_commit=parity_review_commit,
                execution_commit=execution_commit,
                thread_environment=thread_environment,
                input_ledger=ledger,
                runtime_numeric=runtime,
                parity_build=parity_build,
                array_identity=array_identity,
                clock=clock,
                counters=counters,
            )

    if (
        allocation is None
        or allocation_records is None
        or groups is None
        or globals_by_rate is None
    ):
        raise GateFailure(
            "IMPLEMENTATION_INVALID", "allocation-item loop did not complete"
        )
    try:
        _populate_allocation_accounting(counters, models, groups, globals_by_rate)
    except GateFailure:
        raise
    except (
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
    ) as error:
        raise GateFailure(
            "IMPLEMENTATION_INVALID", f"malformed allocation accounting input: {error}"
        ) from error
    allocation_persistent_roots = (
        matrix,
        row_order_vector_ids,
        selection_digests,
        per_row_raw_sha256,
        array_identity,
        models,
        allocation,
        allocation_records,
        groups,
        globals_by_rate,
        ledger,
        plan,
        completed,
        runtime,
        parity_build,
        thread_environment,
        counters,
    )
    _update_supervisor_owned_buffer_hwm(
        counters, "allocation", *allocation_persistent_roots
    )
    terminal_state.context = {}
    clock.switch("shard_serialization")
    completed.append(
        _publish_jsonl_shard(
            output_dir,
            plan[128],
            _records_with_supervisor_hwm(
                allocation_records,
                counters=counters,
                persistent_roots=allocation_persistent_roots,
            ),
        )
    )
    crossed_at_allocation_shard = clock.cumulative_cpu_us() > CPU_PANEL_LIMIT_US
    cost_lower_bound_crossed = (
        cost_lower_bound_crossed or crossed_at_allocation_shard
    )
    if crossed_at_allocation_shard and representation_failure is None:
        checkpoint = _checkpoint(
            phase="allocation",
            completed_operation_count=counters["allocation_item_count"],
            last_completed_plan_index=128,
            cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
            reason_code="RUNNING_CPU_LOWER_BOUND_EXCEEDED",
            message=(
                "complete allocation output-shard checkpoint crossed the "
                "frozen panel CPU limit"
            ),
            path=plan[128]["path"],
        )
        shutil.rmtree(working)
        terminal_state.working = None
        terminal_state.finalizing = True
        return _finalize_cost_projection(
            output_dir=output_dir,
            plan=plan,
            completed=completed,
            checkpoint=checkpoint,
            timed_status="NO_GO_EXACT_SOLVER_COST",
            projection_complete=False,
            implementation_commit=implementation_commit,
            parity_evidence_commit=parity_evidence_commit,
            parity_review_commit=parity_review_commit,
            execution_commit=execution_commit,
            thread_environment=thread_environment,
            input_ledger=ledger,
            runtime_numeric=runtime,
            parity_build=parity_build,
            array_identity=array_identity,
            clock=clock,
            counters=counters,
        )
    clock.switch("allocation")

    # Status order is CONTROL, representation, then cost.  When representation
    # has already failed, retain it while every full-shape block control runs;
    # a lower-priority CPU crossing cannot mask that known condition.  Without
    # a pending representation failure, the frozen bounded gate has already
    # stopped at the first complete item/output-shard checkpoint above.

    del allocation, allocation_records, product_items, global_items

    block_centers: dict[tuple[int, int], list[list[str]]] = {}
    block_common_roots = (
        matrix,
        row_order_vector_ids,
        selection_digests,
        per_row_raw_sha256,
        array_identity,
        models,
        groups,
        globals_by_rate,
        block_centers,
        ledger,
        plan,
        completed,
        runtime,
        parity_build,
        thread_environment,
        counters,
    )
    clock.switch("block")
    for word_bits in (4, 8):
        capacity = 1 << word_bits
        for group_id in range(64):
            plan_index = 129 + (0 if word_bits == 4 else 64) + group_id
            terminal_state.phase = "block"
            terminal_state.current_plan_index = plan_index
            terminal_state.context = {"word_bits": word_bits, "group_id": group_id}
            raw_group = groups[(word_bits, group_id)]
            cardinalities = [int(value) for value in raw_group["arbitrary"]["cardinalities"]]
            axis0 = [
                reference.bits_to_float64(int(value))
                for value in models[2 * group_id].binary64_centroids[cardinalities[0]]
            ]
            axis1 = [
                reference.bits_to_float64(int(value))
                for value in models[2 * group_id + 1].binary64_centroids[cardinalities[1]]
            ]
            rows = matrix[:, (2 * group_id, 2 * group_id + 1)]
            block_input = working / "block_input.bin"
            block_output = working / "block_output.tsv"
            block_requested_cases = (
                (
                    group_id,
                    capacity,
                    group_id,
                    "synthetic_cost_projection",
                    rows,
                    axis0,
                    axis1,
                    tuple(0 for _ in range(FULL_ROWS)),
                ),
            )
            _write_block_input(block_input, block_requested_cases)
            _update_supervisor_owned_buffer_hwm(
                counters,
                "block",
                *block_common_roots,
                raw_group,
                cardinalities,
                axis0,
                axis1,
                rows,
                block_requested_cases,
                terminal_state.context,
                transient_payload_bytes=64,
            )
            _run_native(("block-suite", str(block_input), str(block_output)))
            try:
                block_output_file_bytes = block_output.stat().st_size
            except OSError as error:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    f"cannot stat block native output: {error}",
                ) from error
            parsed_block = _parse_block_output(
                block_output, requested_cases=block_requested_cases
            )
            block_input.unlink()
            block_output.unlink()
            case = parsed_block.get(group_id)
            if case is None:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID", "block parser omitted the requested case"
                )
            if not case.get("control_valid"):
                clock.switch("shard_serialization")
                checkpoint = _checkpoint(
                    phase="block",
                    completed_operation_count=counters["block_model_count"],
                    last_completed_plan_index=plan_index - 1,
                    cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
                    reason_code="BLOCK_CONTROL_FAILURE",
                    message="frozen block trainer returned an invalid control",
                    path=plan[plan_index]["path"],
                    word_bits=word_bits,
                    group_id=group_id,
                )
                shutil.rmtree(working)
                terminal_state.working = None
                terminal_state.finalizing = True
                return _finalize_cost_projection(
                    output_dir=output_dir,
                    plan=plan,
                    completed=completed,
                    checkpoint=checkpoint,
                    timed_status=_resolve_frozen_terminal_status(
                        [
                            "CONTROL_INVALID",
                            *(
                                ["NO_GO_REPRESENTATION"]
                                if representation_failure is not None
                                else []
                            ),
                            *(
                                ["NO_GO_EXACT_SOLVER_COST"]
                                if cost_lower_bound_crossed
                                else []
                            ),
                        ]
                    ),
                    projection_complete=False,
                    implementation_commit=implementation_commit,
                    parity_evidence_commit=parity_evidence_commit,
                    parity_review_commit=parity_review_commit,
                    execution_commit=execution_commit,
                    thread_environment=thread_environment,
                    input_ledger=ledger,
                    runtime_numeric=runtime,
                    parity_build=parity_build,
                    array_identity=array_identity,
                    clock=clock,
                    counters=counters,
                )
            block_records, selected_centers, block_replay_audit = (
                _block_cost_records(
                    case,
                    word_bits=word_bits,
                    group_id=group_id,
                    arbitrary_cardinalities=cardinalities,
                    arbitrary_used_states=int(
                        raw_group["arbitrary"]["used_states"]
                    ),
                )
            )
            block_centers[(word_bits, group_id)] = selected_centers
            counters["block_model_count"] += 1
            counters["block_start_count"] += 8
            native_block_distance = sum(
                int(start["distance_comparison_count"])
                for start in case["native_starts"]
            )
            counters["comparison_counts"]["block_native_distance"] += (
                native_block_distance
            )
            counters["comparison_counts"]["block_distance"] += native_block_distance
            parser_step_distance = int(
                case["validation_parser_step_distance_comparison_count"]
            )
            counters["comparison_counts"][
                "block_validation_parser_step_distance"
            ] += parser_step_distance
            counters["comparison_counts"]["block_distance"] += (
                parser_step_distance
            )
            replay_block_distance = int(block_replay_audit["distance_comparisons"])
            counters["comparison_counts"][
                "block_validation_step_final_distance"
            ] += replay_block_distance
            counters["comparison_counts"]["block_distance"] += replay_block_distance
            # Two direct start-0 control replays are outside RunLloyd's
            # per-start counters: Cartesian prefill and post-fill codebooks.
            # The native trainer performs that pair once and the independent
            # Python control below performs the same pair again, so both
            # timed work sets must be charged separately.
            cartesian_fill_distance = FULL_ROWS * (
                len(case["cartesian"]["centers"]) + capacity
            )
            counters["comparison_counts"][
                "block_native_cartesian_fill_distance"
            ] += cartesian_fill_distance
            counters["comparison_counts"][
                "block_validation_cartesian_fill_distance"
            ] += cartesian_fill_distance
            counters["comparison_counts"]["block_distance"] += 2 * (
                cartesian_fill_distance
            )
            # A valid best-of-eight result performs one strict final-SSE
            # comparison for each start after start 0 in both the native
            # selector and the independent parser replay above.
            native_best_sse_comparisons = BLOCK_START_COUNT - 1
            validation_best_sse_comparisons = int(
                case["validation_best_start_sse_comparison_count"]
            )
            if validation_best_sse_comparisons != BLOCK_START_COUNT - 1:
                raise GateFailure(
                    "IMPLEMENTATION_INVALID",
                    "block best-of-eight validation comparison count mismatch",
                )
            counters["comparison_counts"][
                "block_native_best_of_eight_final_sse_comparisons"
            ] += native_best_sse_comparisons
            counters["comparison_counts"][
                "block_validation_best_of_eight_final_sse_comparisons"
            ] += validation_best_sse_comparisons
            counters["comparison_counts"][
                "block_best_of_eight_final_sse_comparisons"
            ] += native_best_sse_comparisons + validation_best_sse_comparisons
            native_trace_assignment_ties = sum(
                int(start["assignment_tie_count"])
                for start in case["native_starts"]
            )
            control_points = _block_points_from_native(case)
            cartesian_centers = [
                (
                    reference.bits_to_float64(int(bits[0], 16)),
                    reference.bits_to_float64(int(bits[1], 16)),
                )
                for bits in case["cartesian"]["centers"]
            ]
            filled_centers = [
                (
                    reference.bits_to_float64(int(bits[0], 16)),
                    reference.bits_to_float64(int(bits[1], 16)),
                )
                for bits in case["native_starts"][0]["initial_centers_bits"]
            ]
            cartesian_fill_ties = (
                reference._assign_points_audit(control_points, cartesian_centers)[3]
                + reference._assign_points_audit(control_points, filled_centers)[3]
            )
            # The native control pair uses the same frozen binary64 arithmetic
            # and tie rule as these independent replays; its result object
            # deliberately does not serialize the otherwise unused tie
            # diagnostics.  Charge the observed equal-event count to both the
            # native control work and the validation work.
            native_assignment_ties = (
                native_trace_assignment_ties + cartesian_fill_ties
            )
            counters["comparison_counts"]["block_native_assignment_ties"] += (
                native_assignment_ties
            )
            counters["comparison_counts"]["block_assignment_ties"] += (
                native_assignment_ties
            )
            validation_assignment_ties = (
                int(block_replay_audit["assignment_ties"])
                + cartesian_fill_ties
            )
            counters["comparison_counts"][
                "block_validation_assignment_ties"
            ] += validation_assignment_ties
            counters["comparison_counts"]["block_assignment_ties"] += (
                validation_assignment_ties
            )
            counters["comparison_counts"]["block_farthest_ties"] += sum(
                int(start["farthest_tie_count"])
                for start in case["native_starts"]
            )
            counters["iteration_counts"]["block_complete_iterations"] += sum(
                int(start["iterations"]) for start in case["native_starts"]
            )
            counters["iteration_counts"]["block_accepted_updates"] += sum(
                len(start["steps"]) for start in case["native_starts"]
            )
            counters["distinct_center_checks"]["block_selected_codebook_checks"] += 1
            selected_native = case["native_starts"][int(case["best_start_id"])]
            if int(selected_native["distinct_serialized_center_count"]) != capacity:
                counters["distinct_center_checks"]["block_selected_codebook_failures"] += 1
            counters["representation_bytes"]["codebook"][f"B{word_bits}"][
                "trained_block_vq"
            ] += capacity * 2 * 4
            # Same ASCII bound as scalar parsing: bytes plus three maximum
            # UCS-4 text/split payload copies.  All replay objects that remain
            # live at the model boundary are included explicitly.
            block_parser_payload_bound = 13 * block_output_file_bytes
            _update_supervisor_owned_buffer_hwm(
                counters,
                "block",
                *block_common_roots,
                raw_group,
                cardinalities,
                axis0,
                axis1,
                rows,
                block_requested_cases,
                parsed_block,
                case,
                block_records,
                control_points,
                cartesian_centers,
                filled_centers,
                selected_native,
                selected_centers,
                block_replay_audit,
                terminal_state.context,
                transient_payload_bytes=block_parser_payload_bound,
            )

            # As with scalar fitting, the block model and its normal shard
            # are separate registered CPU checkpoints.  A pending higher-
            # priority representation failure suppresses only the cost stop;
            # all block controls must still run so CONTROL_INVALID can win.
            if clock.cumulative_cpu_us() > CPU_PANEL_LIMIT_US:
                cost_lower_bound_crossed = True
                if representation_failure is None:
                    clock.switch("shard_serialization")
                    checkpoint = _checkpoint(
                        phase="block",
                        completed_operation_count=counters["block_model_count"],
                        last_completed_plan_index=plan_index - 1,
                        cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
                        reason_code="RUNNING_CPU_LOWER_BOUND_EXCEEDED",
                        message=(
                            "complete block-model checkpoint crossed the "
                            "frozen panel CPU limit"
                        ),
                        path=plan[plan_index]["path"],
                        word_bits=word_bits,
                        group_id=group_id,
                    )
                    shutil.rmtree(working)
                    terminal_state.working = None
                    terminal_state.finalizing = True
                    return _finalize_cost_projection(
                        output_dir=output_dir,
                        plan=plan,
                        completed=completed,
                        checkpoint=checkpoint,
                        timed_status="NO_GO_EXACT_SOLVER_COST",
                        projection_complete=False,
                        implementation_commit=implementation_commit,
                        parity_evidence_commit=parity_evidence_commit,
                        parity_review_commit=parity_review_commit,
                        execution_commit=execution_commit,
                        thread_environment=thread_environment,
                        input_ledger=ledger,
                        runtime_numeric=runtime,
                        parity_build=parity_build,
                        array_identity=array_identity,
                        clock=clock,
                        counters=counters,
                    )
            clock.switch("shard_serialization")
            completed.append(
                _publish_jsonl_shard(
                    output_dir,
                    plan[plan_index],
                    _records_with_supervisor_hwm(
                        block_records,
                        counters=counters,
                        persistent_roots=(
                            *block_common_roots,
                            raw_group,
                            cardinalities,
                            axis0,
                            axis1,
                            rows,
                            parsed_block,
                            block_records,
                        ),
                    ),
                )
            )
            del (
                axis0,
                axis1,
                rows,
                parsed_block,
                case,
                block_records,
                control_points,
                cartesian_centers,
                filled_centers,
                selected_native,
                selected_centers,
                block_replay_audit,
            )
            clock.switch("block")
            if clock.cumulative_cpu_us() > CPU_PANEL_LIMIT_US:
                cost_lower_bound_crossed = True
                if representation_failure is None:
                    clock.switch("shard_serialization")
                    checkpoint = _checkpoint(
                        phase="block",
                        completed_operation_count=counters["block_model_count"],
                        last_completed_plan_index=plan_index,
                        cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
                        reason_code="RUNNING_CPU_LOWER_BOUND_EXCEEDED",
                        message=(
                            "complete block output-shard checkpoint crossed "
                            "the frozen panel CPU limit"
                        ),
                        path=plan[plan_index]["path"],
                        word_bits=word_bits,
                        group_id=group_id,
                    )
                    shutil.rmtree(working)
                    terminal_state.working = None
                    terminal_state.finalizing = True
                    return _finalize_cost_projection(
                        output_dir=output_dir,
                        plan=plan,
                        completed=completed,
                        checkpoint=checkpoint,
                        timed_status="NO_GO_EXACT_SOLVER_COST",
                        projection_complete=False,
                        implementation_commit=implementation_commit,
                        parity_evidence_commit=parity_evidence_commit,
                        parity_review_commit=parity_review_commit,
                        execution_commit=execution_commit,
                        thread_environment=thread_environment,
                        input_ledger=ledger,
                        runtime_numeric=runtime,
                        parity_build=parity_build,
                        array_identity=array_identity,
                        clock=clock,
                        counters=counters,
                    )

    del raw_group, cardinalities, block_input, block_output
    if representation_failure is not None:
        clock.switch("shard_serialization")
        timed_status = _resolve_frozen_terminal_status(
            [
                "NO_GO_REPRESENTATION",
                *(
                    ["NO_GO_EXACT_SOLVER_COST"]
                    if cost_lower_bound_crossed
                    else []
                ),
            ]
        )
        checkpoint = _checkpoint(
            phase="block",
            completed_operation_count=130 + counters["block_model_count"],
            last_completed_plan_index=len(completed) - 1,
            cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
            reason_code="SELECTED_ALPHABET_UNREACHABLE_OR_COLLIDED",
            message=(
                "all full-shape block controls passed; a retained selected "
                "scalar alphabet representation failure now determines status"
            ),
            path=plan[128]["path"],
            **representation_failure,
        )
        shutil.rmtree(working)
        terminal_state.working = None
        terminal_state.finalizing = True
        return _finalize_cost_projection(
            output_dir=output_dir,
            plan=plan,
            completed=completed,
            checkpoint=checkpoint,
            timed_status=timed_status,
            projection_complete=False,
            implementation_commit=implementation_commit,
            parity_evidence_commit=parity_evidence_commit,
            parity_review_commit=parity_review_commit,
            execution_commit=execution_commit,
            thread_environment=thread_environment,
            input_ledger=ledger,
            runtime_numeric=runtime,
            parity_build=parity_build,
            array_identity=array_identity,
            clock=clock,
            counters=counters,
        )

    del representation_failure
    clock.switch("encoding")
    for word_bits in (4, 8):
        plan_index = 257 if word_bits == 4 else 258
        terminal_state.phase = "encoding"
        terminal_state.current_plan_index = plan_index
        terminal_state.context = {"word_bits": word_bits}
        global_widths = [int(value) for value in globals_by_rate[word_bits]["bit_widths"]]
        expected_comparisons = [
            sum(
                sum(int(value) for value in groups[(word_bits, group_id)][source]["cardinalities"])
                for group_id in range(FULL_GROUP_COUNT)
            )
            for source in ("dyadic", "arbitrary")
        ]
        expected_comparisons.extend(
            [
                FULL_GROUP_COUNT * (1 << word_bits),
                sum(
                    len(models[coordinate].binary32_centroids[1 << width])
                    for coordinate, width in enumerate(global_widths)
                ),
            ]
        )
        parent_persistent_owned_bytes = (
            _deterministic_owned_buffer_bytes(
                matrix,
                selection_digests,
                per_row_raw_sha256,
                array_identity,
                models,
                groups,
                globals_by_rate,
                block_centers,
                ledger,
                plan,
                completed,
                runtime,
                parity_build,
                thread_environment,
                counters,
            )
            + FULL_ROWS * 4
        )
        native_inputs: dict[str, Path] = {}
        native_outputs: dict[str, Path] = {}
        rate_timing: dict[str, dict[str, Any]] = {}
        for arm_id, arm_name in enumerate(_ENCODING_ARM_NAMES):
            terminal_state.context = {
                "word_bits": word_bits,
                "arm": arm_name,
            }
            encoding_input = (
                working / f"encoding_b{word_bits:02d}_arm_{arm_id:01d}_input.bin"
            )
            encoding_output = (
                working / f"encoding_b{word_bits:02d}_arm_{arm_id:01d}_output.bin"
            )
            arm_start_cpu = _cpu_usage_us()
            arm_start_wall = _wall_ns()
            _write_encoding_input(
                encoding_input,
                np=np,
                word_bits=word_bits,
                selected_arm_id=arm_id,
                matrix=matrix,
                models=models,
                groups=groups,
                globals_by_rate=globals_by_rate,
                block_centers=block_centers,
            )
            _update_supervisor_owned_buffer_hwm(
                counters,
                "encoding",
                transient_payload_bytes=(
                    parent_persistent_owned_bytes + int(matrix.nbytes)
                ),
            )
            child_start_cpu = _cpu_usage_us()
            child_start_wall = _wall_ns()
            _run_native(
                ("encoding-suite", str(encoding_input), str(encoding_output))
            )
            child_end_cpu = _cpu_usage_us()
            child_end_wall = _wall_ns()
            if (
                child_end_cpu < child_start_cpu
                or child_end_wall < child_start_wall
                or child_start_cpu < arm_start_cpu
                or child_start_wall < arm_start_wall
            ):
                raise GateFailure(
                    "IMPLEMENTATION_INVALID", "native encoding arm clock moved backwards"
                )
            rate_timing[arm_name] = {
                "arm_total_cpu_microseconds": child_end_cpu - arm_start_cpu,
                "arm_total_wall_nanoseconds": child_end_wall - arm_start_wall,
                "input_serialization_cpu_microseconds": (
                    child_start_cpu - arm_start_cpu
                ),
                "input_serialization_wall_nanoseconds": (
                    child_start_wall - arm_start_wall
                ),
                "native_child_cpu_microseconds": child_end_cpu - child_start_cpu,
                "native_child_wall_nanoseconds": child_end_wall - child_start_wall,
                "scope": (
                    "arm total covers arm-specific input serialization plus "
                    "native child invocation and parent wait"
                ),
            }
            counters["encoding_native_arm_count"] += 1
            native_inputs[arm_name] = encoding_input
            native_outputs[arm_name] = encoding_output
            if clock.cumulative_cpu_us() > CPU_PANEL_LIMIT_US:
                counters["encoding_arm_timings"][f"B{word_bits}"] = rate_timing
                clock.switch("shard_serialization")
                checkpoint = _checkpoint(
                    phase="encoding",
                    completed_operation_count=counters["encoding_native_arm_count"],
                    last_completed_plan_index=len(completed) - 1,
                    cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
                    reason_code="RUNNING_CPU_LOWER_BOUND_EXCEEDED",
                    message=(
                        "complete native encoding-arm checkpoint crossed the "
                        "frozen panel CPU limit"
                    ),
                    path=plan[plan_index]["path"],
                    word_bits=word_bits,
                    arm=arm_name,
                )
                shutil.rmtree(working)
                terminal_state.working = None
                terminal_state.finalizing = True
                return _finalize_cost_projection(
                    output_dir=output_dir,
                    plan=plan,
                    completed=completed,
                    checkpoint=checkpoint,
                    timed_status="NO_GO_EXACT_SOLVER_COST",
                    projection_complete=False,
                    implementation_commit=implementation_commit,
                    parity_evidence_commit=parity_evidence_commit,
                    parity_review_commit=parity_review_commit,
                    execution_commit=execution_commit,
                    thread_environment=thread_environment,
                    input_ledger=ledger,
                    runtime_numeric=runtime,
                    parity_build=parity_build,
                    array_identity=array_identity,
                    clock=clock,
                    counters=counters,
                )
        counters["encoding_arm_timings"][f"B{word_bits}"] = rate_timing

        totals = EncodingNativeTotals()
        clock.switch("shard_serialization")
        completed.append(
            _publish_jsonl_shard(
                output_dir,
                plan[plan_index],
                _encoding_records(
                    native_outputs=native_outputs,
                    np=np,
                    word_bits=word_bits,
                    matrix=matrix,
                    models=models,
                    groups=groups,
                    globals_by_rate=globals_by_rate,
                    block_centers=block_centers,
                    expected_comparisons=expected_comparisons,
                    global_widths=global_widths,
                    parent_persistent_owned_bytes=parent_persistent_owned_bytes,
                    totals=totals,
                ),
            )
        )
        if (
            totals.row_count != FULL_ROWS
            or totals.distance_comparisons is None
            or totals.validation_distance_comparisons is None
            or totals.payload_bytes is None
            or totals.pack_operations is None
            or totals.validation_pack_operations is None
            or totals.unpack_operations is None
            or totals.validation_unpack_operations is None
            or totals.mixed_radix_encodes is None
            or totals.mixed_radix_decodes is None
            or totals.arm_vector_counts is None
            or totals.owned_payload_high_water_bytes <= 0
            or totals.python_owned_high_water_bytes <= 0
        ):
            raise GateFailure("IMPLEMENTATION_INVALID", "encoding terminal totals were not populated")
        parent_plus_native_high_water = (
            parent_persistent_owned_bytes + totals.owned_payload_high_water_bytes
        )
        _update_supervisor_owned_buffer_hwm(
            counters,
            "encoding",
            transient_payload_bytes=totals.python_owned_high_water_bytes,
        )
        native_distance_total = sum(totals.distance_comparisons.values())
        validation_distance_total = sum(
            totals.validation_distance_comparisons.values()
        )
        counters["comparison_counts"]["encoding_native_distance"] += (
            native_distance_total
        )
        counters["comparison_counts"]["encoding_validation_distance"] += (
            validation_distance_total
        )
        counters["comparison_counts"]["encoding_total_distance"] += (
            native_distance_total + validation_distance_total
        )
        native_pack_total = sum(totals.pack_operations.values())
        validation_pack_total = sum(totals.validation_pack_operations.values())
        native_unpack_total = sum(totals.unpack_operations.values())
        validation_unpack_total = sum(
            totals.validation_unpack_operations.values()
        )
        counters["encoding_native_pack_operation_count"] += native_pack_total
        counters["encoding_validation_pack_operation_count"] += (
            validation_pack_total
        )
        counters["encoding_total_pack_operation_count"] += (
            native_pack_total + validation_pack_total
        )
        counters["encoding_native_unpack_operation_count"] += native_unpack_total
        counters["encoding_validation_unpack_operation_count"] += (
            validation_unpack_total
        )
        counters["encoding_total_unpack_operation_count"] += (
            native_unpack_total + validation_unpack_total
        )
        payload_accounting = counters["representation_bytes"]["database_payload"][
            f"B{word_bits}"
        ]
        for arm_name in _ENCODING_ARM_NAMES:
            payload_accounting[arm_name]["completed_total"] = totals.payload_bytes[
                arm_name
            ]
        nominal_global_per_vector = sum(1 << width for width in global_widths)
        rate_operations: dict[str, dict[str, Any]] = {}
        for arm_id, arm_name in enumerate(_ENCODING_ARM_NAMES):
            native_effective_total = totals.distance_comparisons[arm_name]
            validation_effective_total = totals.validation_distance_comparisons[
                arm_name
            ]
            native_pack_operations = totals.pack_operations[arm_name]
            validation_pack_operations = totals.validation_pack_operations[arm_name]
            native_unpack_operations = totals.unpack_operations[arm_name]
            validation_unpack_operations = totals.validation_unpack_operations[
                arm_name
            ]
            nominal_per_vector = (
                nominal_global_per_vector
                if arm_name == "global_dyadic_pack_cap8"
                else expected_comparisons[arm_id]
            )
            rate_operations[arm_name] = {
                "arm_vector_count": totals.arm_vector_counts[arm_name],
                "native_distance_comparisons_effective": native_effective_total,
                "validation_distance_comparisons_effective": (
                    validation_effective_total
                ),
                "total_distance_comparisons_effective": (
                    native_effective_total + validation_effective_total
                ),
                "distance_comparisons_nominal_descriptive": (
                    nominal_per_vector * FULL_ROWS
                ),
                "native_distance_comparisons_effective_per_vector": (
                    expected_comparisons[arm_id]
                ),
                "validation_distance_comparisons_effective_per_vector": (
                    expected_comparisons[arm_id]
                ),
                "total_distance_comparisons_effective_per_vector": (
                    2 * expected_comparisons[arm_id]
                ),
                "distance_comparisons_nominal_per_vector": nominal_per_vector,
                "native_pack_operations": native_pack_operations,
                "validation_pack_operations": validation_pack_operations,
                "total_pack_operations": (
                    native_pack_operations + validation_pack_operations
                ),
                "native_unpack_operations": native_unpack_operations,
                "validation_unpack_operations": validation_unpack_operations,
                "total_unpack_operations": (
                    native_unpack_operations + validation_unpack_operations
                ),
                "mixed_radix_encodes": totals.mixed_radix_encodes[arm_name],
                "mixed_radix_decodes": totals.mixed_radix_decodes[arm_name],
            }
        counters["encoding_arm_operation_counts"][f"B{word_bits}"] = rate_operations
        counters["encoding_memory_accounting"][f"B{word_bits}"] = {
            "replay_chunk_rows": _ENCODING_REPLAY_CHUNK_ROWS,
            "parent_persistent_owned_bytes": parent_persistent_owned_bytes,
            "native_child_live_payload_high_water_bytes": (
                totals.owned_payload_high_water_bytes
            ),
            "parent_plus_native_high_water_bytes": parent_plus_native_high_water,
            "python_replay_pipeline_high_water_bytes": (
                totals.python_owned_high_water_bytes
            ),
            "replay_workspace_high_water_bytes": (
                totals.replay_workspace_high_water_bytes
            ),
            "current_record_high_water_bytes": (
                totals.current_record_high_water_bytes
            ),
            "canonical_json_line_high_water_bytes": (
                totals.canonical_line_high_water_bytes
            ),
        }
        counters["encoded_vector_rate_count"] += FULL_ROWS
        for path in (*native_inputs.values(), *native_outputs.values()):
            path.unlink()
        clock.switch("encoding")
        if clock.cumulative_cpu_us() > CPU_PANEL_LIMIT_US:
            clock.switch("shard_serialization")
            checkpoint = _checkpoint(
                phase="encoding",
                completed_operation_count=counters["encoded_vector_rate_count"],
                last_completed_plan_index=plan_index,
                cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
                reason_code="RUNNING_CPU_LOWER_BOUND_EXCEEDED",
                message="complete encoding-shard checkpoint crossed the frozen panel CPU limit",
                path=plan[plan_index]["path"],
                word_bits=word_bits,
            )
            shutil.rmtree(working)
            terminal_state.working = None
            terminal_state.finalizing = True
            return _finalize_cost_projection(
                output_dir=output_dir,
                plan=plan,
                completed=completed,
                checkpoint=checkpoint,
                timed_status="NO_GO_EXACT_SOLVER_COST",
                projection_complete=False,
                implementation_commit=implementation_commit,
                parity_evidence_commit=parity_evidence_commit,
                parity_review_commit=parity_review_commit,
                execution_commit=execution_commit,
                thread_environment=thread_environment,
                input_ledger=ledger,
                runtime_numeric=runtime,
                parity_build=parity_build,
                array_identity=array_identity,
                clock=clock,
                counters=counters,
            )

    shutil.rmtree(working)
    terminal_state.working = None
    clock.switch("shard_serialization")
    terminal_state.phase = "complete"
    terminal_state.current_plan_index = 258
    terminal_state.context = {}
    terminal_state.finalizing = True
    checkpoint = _checkpoint(
        phase="complete",
        completed_operation_count=sum(
            int(value)
            for key, value in counters.items()
            if key != "owned_buffer_high_water_bytes" and isinstance(value, int)
        ),
        last_completed_plan_index=258,
        cumulative_cpu_microseconds=clock.cumulative_cpu_us(),
        reason_code="FULL_PIPELINE_COMPLETE",
        message="all 259 registered normal shards completed",
        path=plan[258]["path"],
    )
    return _finalize_cost_projection(
        output_dir=output_dir,
        plan=plan,
        completed=completed,
        checkpoint=checkpoint,
        timed_status="PENDING_FINAL_CPU_DECISION",
        projection_complete=True,
        implementation_commit=implementation_commit,
        parity_evidence_commit=parity_evidence_commit,
        parity_review_commit=parity_review_commit,
        execution_commit=execution_commit,
        thread_environment=thread_environment,
        input_ledger=ledger,
        runtime_numeric=runtime,
        parity_build=parity_build,
        array_identity=array_identity,
        clock=clock,
        counters=counters,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Frozen A4-1S synthetic-only implementation gate",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for mode in ("parity", "cost-projection"):
        child = subparsers.add_parser(mode, allow_abbrev=False)
        child.add_argument("--input-spec", required=True)
        child.add_argument("--hypotheses", required=True)
        child.add_argument("--output-dir", required=True)
        child.add_argument("--threads", required=True, type=int)
    return parser


def main(start_cpu_us: int, start_wall_ns: int) -> int:
    # The bootstrap captures these integer values before importing this
    # module.  They are carried unchanged through the complete cost region.
    if not isinstance(start_cpu_us, int) or not isinstance(start_wall_ns, int):
        raise TypeError("bootstrap snapshots must be integers")
    args = _parser().parse_args()
    try:
        if args.mode == "parity":
            status = _run_parity(args)
        else:
            status = _run_cost_projection(args, start_cpu_us, start_wall_ns)
    except artifacts.ArtifactContractError as error:
        print(f"A4-1S IMPLEMENTATION_INVALID: {error}", file=sys.stderr)
        return 2
    except GateFailure as error:
        print(f"A4-1S {error.status}: {error.detail}", file=sys.stderr)
        return 3
    print(f"A4-1S {status}")
    return 0
