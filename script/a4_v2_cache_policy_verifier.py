#!/usr/bin/env python3
"""Standalone PAR-only verifier for the frozen A4-V2 cache policy.

This file is source evidence during A4-V2-CACHE-I.  It is deliberately
independent of every A4 module and repository helper.  A later, separately
authorized PAR-R1 parent may execute it only through the reviewed descriptor,
argv, environment, and control-pipe surface frozen by CACHE-P.

The verifier never imports a repository module, installs an import hook,
loads bytecode, or creates/removes a cache path.  A well-formed policy
mismatch is published as a canonical ``MISMATCH`` artifact with exit status
zero.  Malformed control, output-publication defects, and ordinary runtime
defects are nonzero verifier failures for the parent to classify as
``IMPLEMENTATION_INVALID`` or by its frozen system/resource precedence.
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import re
import resource
import stat
import subprocess
import sys
import time
from typing import Any, Mapping, NoReturn, Sequence


LEADER_FD = 197
CONTROL_FD = 198
CACHE_VERIFIER_RESOURCE_EXIT = 75
SCHEMA_VERSION = 1
MAX_CONTROL_BYTES = 1_048_576
MAX_AUTHORITY_BYTES = 8_388_608
MAX_SOURCE_BYTES = 8_388_608
MAX_GIT_OUTPUT_BYTES = 8_388_608
MAX_MISMATCHES = 256
MAX_STRING_BYTES = 65_536
MAX_PATH_BYTES = 512
MAX_DETAIL_BYTES = 4_096
MAX_CMDLINE_BYTES = 32_768
MAX_CMDLINE_HEX_BYTES = 65_536
MAX_LIST_ITEMS = 4_096
MAX_OUTPUT_BYTES = 8_388_608
EXPECTED_SOURCE_COUNT = 37
CONTROL_MEMFD_NAME = "saq-a4-v2-cache-policy-control"
CONTROL_MEMFD_TARGET = "/memfd:" + CONTROL_MEMFD_NAME + " (deleted)"
CONTROL_MEMFD_SEALS = (
    fcntl.F_SEAL_SEAL
    | fcntl.F_SEAL_SHRINK
    | fcntl.F_SEAL_GROW
    | fcntl.F_SEAL_WRITE
)

CLONE_ROOT = "/tmp/saq-a4-v2-par-r1-isolation/repo"
OLD_WORKTREE = "/tmp/saq-arbitrary-cardinality-feasibility-v2"
BRANCH = "saq-arbitrary-cardinality-feasibility-v2"
FETCH_URL = "https://github.com/Ufowoqqqo/SAQ.git"
PUSH_URL = "git@github.com:Ufowoqqqo/SAQ.git"
OUTPUT_NAME = "cache_policy_verification.json"

IMPLEMENTATION_MANIFEST_PATH = (
    "docs/saq_a4_v2_implementation_manifest_2026_07_14.json"
)
CACHE_AUTHORITY_PATH = (
    "docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json"
)
STATIC_CLOSURE_PATH = "docs/saq_a4_v2_cache_static_closure_2026_07_15.json"
CACHE_BINDING_PATH = "docs/saq_a4_v2_cache_prep_binding_2026_07_15.json"
RUNTIME_SCHEMA_PATH = "docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json"

CPYTHON_SHA256 = "c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b"
CPYTHON_SIZE = 15_448
BOOTSTRAP_EXTERNAL_PATH = "/usr/lib64/python3.9/importlib/_bootstrap_external.py"
BOOTSTRAP_EXTERNAL_SHA256 = (
    "8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4"
)
BOOTSTRAP_EXTERNAL_SIZE = 66_447

CACHE_PATHS = (
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

# These roots are policy literals, not values selected by the parent control.
# The control and additive cache authority must repeat this exact byte order.
INSTALLED_ORIGIN_ROOTS = (
    "/usr/lib/python3.9",
    "/usr/lib64/python3.9",
    "/usr/lib64/python39.zip",
    "/usr/local/lib/python3.9/site-packages",
    "/usr/local/lib64/python3.9/site-packages",
)

CONTROL_KEYS = frozenset(
    {
        "artifact_kind",
        "authority",
        "cache_paths",
        "clone",
        "output",
        "parent",
        "preterminal_observations",
        "reviewed_python_sources",
        "schema_version",
        "startup_observation",
    }
)
AUTHORITY_KEYS = frozenset(
    {
        "cache_prep_binding",
        "cache_protocol_authority",
        "cache_static_closure",
        "implementation_manifest",
        "par_r1_authorization",
        "runtime_schema",
    }
)
CLONE_KEYS = frozenset(
    {
        "allowed_installed_origin_roots",
        "branch",
        "expected_commit",
        "expected_tree_oid",
        "origin_fetch_url",
        "origin_push_url",
        "par_staging_relative_path",
        "root",
        "source_tree_sha256",
    }
)
OUTPUT_KEYS = frozenset(
    {
        "artifact_name",
        "maximum_bytes",
        "staging_relative_path",
    }
)
PARENT_KEYS = frozenset(
    {
        "bootstrap_external",
        "cmdline_hex",
        "cmdline_sha256",
        "cwd",
        "environment",
        "leader",
        "pid",
        "start_time_clock_ticks",
    }
)
IDENTITY_KEYS = frozenset({"path", "sha256", "size_bytes"})
BOOTSTRAP_IDENTITY_KEYS = frozenset(
    {"device", "inode", "mode", "path", "sha256", "size_bytes"}
)
LEADER_IDENTITY_KEYS = frozenset(
    {
        "device",
        "inode",
        "mode",
        "path",
        "resolved_path",
        "sha256",
        "size_bytes",
    }
)
LEADER_GROUP_KEYS = frozenset({"command", "proc_self_exe", "sys_executable"})
PARENT_ENVIRONMENT_KEYS = frozenset(
    {"python_prefixed_names", "thread_environment"}
)
THREAD_ENVIRONMENT_KEYS = frozenset(
    {"MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"}
)
SOURCE_KEYS = frozenset(
    {"family", "git_blob", "path", "role", "sha256", "size_bytes"}
)
MANIFEST_SOURCE_KEYS = frozenset(
    {"family", "path", "role", "sha256", "size_bytes"}
)
IMPLEMENTATION_MANIFEST_KEYS = frozenset(
    {
        "artifact_kind",
        "artifact_schema_identity",
        "authorization_identity",
        "build_status",
        "cache_protocol_identity",
        "contract_identity",
        "implementation_binding_identity",
        "inline_executable_sources",
        "par_contract",
        "parent_preregistration_identity",
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
)
OBSERVATION_KEYS = frozenset(
    {
        "a4_modules",
        "cache_paths",
        "checkpoint",
        "interpreter",
        "observed_monotonic_ns",
        "parent_identity",
        "retained_modules",
        "sys_meta_path",
        "sys_path",
        "user_site_enabled",
    }
)
INTERPRETER_KEYS = frozenset(
    {
        "dont_write_bytecode",
        "flags",
        "implementation_cache_tag",
        "pycache_prefix",
    }
)
FLAG_KEYS = frozenset(
    {
        "dont_write_bytecode",
        "ignore_environment",
        "isolated",
        "no_site",
        "optimize",
    }
)
PROCESS_IDENTITY_KEYS = frozenset({"pid", "start_time_clock_ticks"})
MODULE_KEYS = frozenset({"cached", "file", "loader_type", "name", "origin"})
A4_MODULE_KEYS = frozenset(
    {
        "cached",
        "expected_cache_path",
        "file",
        "loader_type",
        "name",
        "origin",
        "source_path",
        "source_sha256",
        "source_size_bytes",
    }
)
META_PATH_KEYS = frozenset({"origin", "type"})
CACHE_STATE_KEYS = frozenset({"path", "state"})
MISMATCH_KEYS = frozenset({"code", "detail", "path"})

CACHE_AUTHORITY_KEYS = frozenset(
    {
        "artifact_kind",
        "authority_chain",
        "claim_ceiling",
        "commit_closure",
        "future_authority_slots",
        "generic_object_identities",
        "implementation_parent_admission",
        "inline_executable_source",
        "no_execution_attestation",
        "outcome_ceiling",
        "prohibitions",
        "protocol_components",
        "runtime_policy",
        "schema_version",
        "source_closure",
        "stage",
    }
)
AUTHORITY_CHAIN_KEYS = frozenset(
    {
        "cache_i_authorization_review_commit",
        "cache_i_authorization_target_commit",
        "cache_p_review_commit",
        "cache_p_target_commit",
        "implementation_parent_commit",
    }
)
IMPLEMENTATION_PARENT_ADMISSION_KEYS = frozenset(
    {
        "argv",
        "branch_ref",
        "claim_ceiling",
        "cwd",
        "exit_code",
        "expected_oid",
        "home_absent_after",
        "home_absent_before",
        "home_path",
        "observed_oid",
        "role",
        "status",
        "stderr",
        "stdin",
        "stdout",
        "xdg_config_home_absent_after",
        "xdg_config_home_absent_before",
        "xdg_config_home_path",
    }
)
COMMIT_CLOSURE_KEYS = frozenset(
    {
        "every_other_tracked_blob_rule",
        "implementation_parent_commit",
        "implementation_review_changed_paths",
        "implementation_review_direct_child_required",
        "implementation_target_changed_paths",
        "implementation_target_direct_parent_required",
        "review_head_closure_role",
        "target_head_closure_role",
    }
)
PROTOCOL_COMPONENT_KEYS = frozenset(
    {
        "cache_contract",
        "cache_i_authorization",
        "cache_i_authorization_review",
        "cache_p_independent_review",
        "cache_primary_review",
        "cache_primary_sources",
        "cache_protocol",
        "prep_host_identity_rebind_erratum_contract",
    }
)
GENERIC_OBJECT_KEYS = frozenset(
    {
        "cache_static_closure",
        "prep_binding_maximal_instance",
        "prep_binding_schema",
        "prep_receipt_maximal_instance",
        "prep_receipt_schema",
        "prep_token_maximal_instance",
        "prep_token_schema",
        "runtime_maximal_instance",
        "runtime_schema",
    }
)
AUTHORITY_SOURCE_CLOSURE_KEYS = frozenset(
    {
        "changed_existing_source_paths",
        "executable_unit_count",
        "implementation_manifest_path",
        "native_source_count",
        "new_source_paths",
        "python_source_count",
        "source_count",
        "source_files",
        "source_tree_algorithm",
        "source_tree_sha256",
        "unchanged_python_source_paths",
    }
)
INLINE_SOURCE_KEYS = frozenset(
    {
        "argv_template",
        "encoding",
        "id",
        "maximal_argv",
        "prologue_sha256",
        "prologue_size_bytes",
        "sha256",
        "size_bytes",
        "source",
        "static_closure_unit_id",
        "storage",
    }
)
RUNTIME_POLICY_KEYS = frozenset(
    {
        "allowed_installed_origin_roots",
        "artifact_index_shape_version",
        "bootstrap_external",
        "build_manifest_shape_version",
        "cache_paths",
        "control_max_bytes",
        "control_transport",
        "environment_preimage_field",
        "leader",
        "output_artifact",
        "output_max_bytes",
        "parent_argv",
        "parent_sys_argv",
        "thread_environment",
        "verifier_argv_template",
        "verifier_environment",
    }
)
STATIC_CLOSURE_KEYS = frozenset(
    {
        "artifact_kind",
        "cache_authority_path",
        "claim_ceiling",
        "executable_units",
        "filesystem_and_mutation_closure",
        "forbidden_constructs",
        "implementation_manifest_path",
        "import_and_process_closure",
        "inline_executable_source",
        "no_execution_attestation",
        "par_reachable_python_actors",
        "parent_precedence_crosswalk",
        "prep_binding_schema_path",
        "runtime_schema_path",
        "schema_version",
        "source_closure",
        "stage",
        "status_mapping",
    }
)
BINDING_KEYS = frozenset(
    {
        "artifact_kind",
        "cache_i_review_commit",
        "cache_i_target_commit",
        "cache_protocol_identity",
        "isolated_clone_identity",
        "par_r1_authorization_slot",
        "prep_authorization_review_commit",
        "prep_authorization_target_commit",
        "prep_execution_base_commit",
        "prep_receipt_review_commit",
        "prep_receipt_target_commit",
        "prep_seal_identity",
        "prep_token_identity",
        "remote_branch_identity",
        "schema_version",
        "source_manifest_identity",
        "source_tree_sha256",
    }
)

CACHE_I_IMPLEMENTATION_PARENT = "187e363ee08d1f63888137c21fd5a533555bb248"
CACHE_I_AUTHORIZATION_TARGET = "4f38ca9e056e2a8e40f5f966407a6bc6ddb51b5d"
CACHE_I_AUTHORIZATION_REVIEW = CACHE_I_IMPLEMENTATION_PARENT
CACHE_P_TARGET = "56210f8f81557ed7a2521bf7f13c9f937396da29"
CACHE_P_REVIEW = "249d5b8c1939acefbf12711790b3e791b019d560"

CACHE_I_TARGET_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_artifact_schema_2026_07_14.json",
    "docs/saq_a4_v2_cache_prep_binding_maximal_instance_2026_07_15.json",
    "docs/saq_a4_v2_cache_prep_binding_schema_2026_07_15.json",
    "docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json",
    "docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json",
    "docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json",
    "docs/saq_a4_v2_cache_static_closure_2026_07_15.json",
    "docs/saq_a4_v2_implementation_binding_2026_07_14.md",
    "docs/saq_a4_v2_implementation_manifest_2026_07_14.json",
    "docs/saq_a4_v2_isolated_clone_prep_receipt_maximal_instance_2026_07_15.json",
    "docs/saq_a4_v2_isolated_clone_prep_receipt_schema_2026_07_15.json",
    "docs/saq_a4_v2_isolated_clone_prep_token_maximal_instance_2026_07_15.json",
    "docs/saq_a4_v2_isolated_clone_prep_token_schema_2026_07_15.json",
    "docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md",
    "script/a4_v2_cache_policy_verifier.py",
    "script/a4_v2_isolated_clone_prep.py",
    "script/a4_v2_parity.py",
    "script/a4_v2_runner.py",
    "script/a4_v2_verifier.py",
    "script/run_arbitrary_cardinality_a4_v2.py",
)
CACHE_I_REVIEW_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_cache_implementation_independent_review_2026_07_15.md",
)
PREP_AUTHORIZATION_TARGET_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md",
)
PREP_AUTHORIZATION_REVIEW_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md",
)
PREP_RECEIPT_TARGET_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15/clone_inventory.json",
    "docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15/clone_operations.jsonl",
    "docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15/clone_postcheck.json",
    "docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15/prep_seal.json",
)
PREP_RECEIPT_REVIEW_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_isolated_clone_prep_independent_review_2026_07_15.md",
)
CACHE_BIND_TARGET_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_cache_prep_binding_2026_07_15.json",
)
CACHE_BIND_REVIEW_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_cache_prep_binding_independent_review_2026_07_15.md",
)
PAR_R1_AUTHORIZATION_TARGET_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_par_r1_authorization_2026_07_15.md",
)
PAR_R1_AUTHORIZATION_REVIEW_CHANGED_PATHS = (
    "AGENTS.md",
    "TASK.md",
    "docs/saq_a4_v2_par_r1_authorization_independent_review_2026_07_15.md",
)

IMPLEMENTATION_PARENT_ADMISSION_ARGV = (
    "/usr/bin/env",
    "-i",
    "GIT_ATTR_NOSYSTEM=1",
    "GIT_CONFIG_GLOBAL=/dev/null",
    "GIT_CONFIG_NOSYSTEM=1",
    "GIT_EXEC_PATH=/usr/libexec/git-core",
    "GIT_OPTIONAL_LOCKS=0",
    "GIT_TERMINAL_PROMPT=0",
    "HOME=/tmp/saq-a4-v2-incident-git-home-absent",
    "XDG_CONFIG_HOME=/tmp/saq-a4-v2-incident-git-xdg-absent",
    "LANG=C",
    "LC_ALL=C",
    "PATH=/usr/bin:/bin",
    "/usr/bin/timeout",
    "--signal=TERM",
    "--kill-after=5s",
    "300s",
    "/usr/bin/git",
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
    "ls-remote",
    "--refs",
    FETCH_URL,
    "refs/heads/saq-arbitrary-cardinality-feasibility-v2",
)
NO_CLONE_EQUALITY_CLAIM = (
    "only pinned env-to-timeout-to-Git wall-bounded successful exit and exact "
    "returned bytes; no outer executor, capture, hashing, process-count, "
    "hard-reap, failure-resource, or systems-performance claim"
)

PROTOCOL_COMPONENT_PATHS = {
    "cache_contract": (
        "docs/saq_a4_v2_cache_staging_disposition_contract_2026_07_15.json"
    ),
    "cache_i_authorization": (
        "docs/saq_a4_v2_cache_implementation_authorization_2026_07_15.md"
    ),
    "cache_i_authorization_review": (
        "docs/saq_a4_v2_cache_implementation_authorization_independent_review_2026_07_15.md"
    ),
    "cache_p_independent_review": (
        "docs/saq_a4_v2_cache_staging_disposition_protocol_independent_review_2026_07_15.md"
    ),
    "cache_primary_review": (
        "docs/saq_a4_v2_cache_staging_primary_source_review_2026_07_15.md"
    ),
    "cache_primary_sources": (
        "docs/saq_a4_v2_cache_staging_primary_sources_2026_07_15.json"
    ),
    "cache_protocol": (
        "docs/saq_a4_v2_cache_staging_disposition_protocol_2026_07_15.md"
    ),
    "prep_host_identity_rebind_erratum_contract": (
        "docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json"
    ),
}
GENERIC_OBJECT_PATHS = {
    "cache_static_closure": STATIC_CLOSURE_PATH,
    "prep_binding_maximal_instance": (
        "docs/saq_a4_v2_cache_prep_binding_maximal_instance_2026_07_15.json"
    ),
    "prep_binding_schema": (
        "docs/saq_a4_v2_cache_prep_binding_schema_2026_07_15.json"
    ),
    "prep_receipt_maximal_instance": (
        "docs/saq_a4_v2_isolated_clone_prep_receipt_maximal_instance_2026_07_15.json"
    ),
    "prep_receipt_schema": (
        "docs/saq_a4_v2_isolated_clone_prep_receipt_schema_2026_07_15.json"
    ),
    "prep_token_maximal_instance": (
        "docs/saq_a4_v2_isolated_clone_prep_token_maximal_instance_2026_07_15.json"
    ),
    "prep_token_schema": (
        "docs/saq_a4_v2_isolated_clone_prep_token_schema_2026_07_15.json"
    ),
    "runtime_maximal_instance": (
        "docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json"
    ),
    "runtime_schema": RUNTIME_SCHEMA_PATH,
}

GIT_PREFIX = (
    "/usr/bin/git",
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
GIT_ENVIRONMENT = {
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_EXEC_PATH": "/usr/libexec/git-core",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "HOME": "/tmp/saq-a4-v2-par-r1-isolation/git-home",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "XDG_CONFIG_HOME": "/tmp/saq-a4-v2-par-r1-isolation/git-xdg",
}

HEX_40 = re.compile(r"[0-9a-f]{40}\Z")
HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z")
RELATIVE_PATH = re.compile(
    r"(?:[A-Za-z0-9._-]+)(?:/[A-Za-z0-9._-]+)*\Z"
)


class VerifierDefect(RuntimeError):
    """Malformed control or verifier-side implementation failure."""


class MismatchRecorder:
    """Bounded deterministic accumulator for well-formed policy mismatches."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, code: str, detail: str, path: str | None = None) -> None:
        if len(self.items) >= MAX_MISMATCHES:
            raise VerifierDefect("cache-policy mismatch inventory exceeds cap")
        _require_text(code, "mismatch code", maximum=128, ascii_only=True)
        _require_text(detail, "mismatch detail", maximum=MAX_DETAIL_BYTES)
        if path is not None:
            _require_text(path, "mismatch path", maximum=MAX_DETAIL_BYTES)
        item = {"code": code, "detail": detail, "path": path}
        if set(item) != MISMATCH_KEYS:
            raise VerifierDefect("internal mismatch record has wrong shape")
        self.items.append(item)

    def equal(
        self,
        code: str,
        actual: Any,
        expected: Any,
        detail: str,
        path: str | None = None,
    ) -> None:
        if actual != expected or type(actual) is not type(expected):
            self.add(code, detail, path)


def _defect(message: str) -> NoReturn:
    raise VerifierDefect(message)


def _require_mapping(value: Any, description: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _defect(f"{description} is not an object")
    return value


def _require_keys(
    value: Mapping[str, Any], expected: frozenset[str], description: str
) -> None:
    if set(value) != expected:
        _defect(f"{description} does not have its exact key closure")


def _require_list(value: Any, description: str, maximum: int = MAX_LIST_ITEMS) -> list[Any]:
    if not isinstance(value, list) or len(value) > maximum:
        _defect(f"{description} is not a bounded list")
    return value


def _require_bool(value: Any, description: str) -> bool:
    if not isinstance(value, bool):
        _defect(f"{description} is not Boolean")
    return value


def _require_int(
    value: Any,
    description: str,
    *,
    minimum: int = 0,
    maximum: int = (1 << 63) - 1,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _defect(f"{description} is not an integer")
    if value < minimum or value > maximum:
        _defect(f"{description} is outside its bound")
    return value


def _require_text(
    value: Any,
    description: str,
    *,
    maximum: int = MAX_STRING_BYTES,
    ascii_only: bool = False,
) -> str:
    if not isinstance(value, str):
        _defect(f"{description} is not text")
    try:
        payload = value.encode("ascii" if ascii_only else "utf-8", errors="strict")
    except UnicodeError as error:
        raise VerifierDefect(f"{description} has forbidden encoding") from error
    if len(payload) > maximum or "\x00" in value:
        _defect(f"{description} exceeds its byte/string closure")
    return value


def _require_sha256(value: Any, description: str) -> str:
    text = _require_text(value, description, maximum=64, ascii_only=True)
    if HEX_64.fullmatch(text) is None:
        _defect(f"{description} is not lowercase SHA-256")
    return text


def _require_oid(value: Any, description: str) -> str:
    text = _require_text(value, description, maximum=40, ascii_only=True)
    if HEX_40.fullmatch(text) is None:
        _defect(f"{description} is not a lowercase Git OID")
    return text


def _require_relative(value: Any, description: str) -> str:
    text = _require_text(value, description, maximum=MAX_PATH_BYTES)
    if RELATIVE_PATH.fullmatch(text) is None or text in {".", ".."}:
        _defect(f"{description} is not a canonical relative path")
    if any(part in {"", ".", ".."} for part in text.split("/")):
        _defect(f"{description} contains a forbidden component")
    return text


def _validate_json_value(value: Any, location: str = "$") -> None:
    if value is None or isinstance(value, (bool, int, str)):
        if isinstance(value, str):
            _require_text(value, location)
        return
    if isinstance(value, list):
        if len(value) > MAX_LIST_ITEMS:
            _defect(f"{location} list exceeds cap")
        for index, item in enumerate(value):
            _validate_json_value(item, f"{location}[{index}]")
        return
    if isinstance(value, dict):
        if len(value) > MAX_LIST_ITEMS:
            _defect(f"{location} object exceeds cap")
        for key, item in value.items():
            _require_text(key, f"{location} key", maximum=256)
            _validate_json_value(item, f"{location}.{key}")
        return
    _defect(f"{location} contains a forbidden JSON value")


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


def _canonical_result_document(value: Mapping[str, Any]) -> bytes:
    preimage = value.get("control_preimage_hex")
    if (
        not isinstance(preimage, str)
        or not 2 <= len(preimage) <= 2 * MAX_CONTROL_BYTES
        or len(preimage) % 2 != 0
        or any(character not in "0123456789abcdef" for character in preimage)
    ):
        _defect("result control preimage is not bounded lowercase even hex")
    validation_view = dict(value)
    validation_view["control_preimage_hex"] = ""
    _validate_json_value(validation_view)
    return (
        json.dumps(
            dict(value),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def _parse_canonical_document(payload: bytes, description: str) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in values:
            if key in result:
                _defect(f"duplicate key in {description}: {key}")
            result[key] = item
        return result

    def reject(token: str) -> NoReturn:
        _defect(f"forbidden numeric token in {description}: {token}")

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
            parse_float=reject,
            parse_constant=reject,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as error:
        raise VerifierDefect(f"invalid {description}: {error}") from error
    _validate_json_value(value)
    if _canonical_document(value) != payload:
        _defect(f"{description} is not canonical JSON with final LF")
    return value


def _read_fd_bounded(descriptor: int, maximum: int, description: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(65_536, maximum + 1 - total))
        if not chunk:
            break
        total += len(chunk)
        if total > maximum:
            _defect(f"{description} exceeds byte cap")
        chunks.append(chunk)
    return b"".join(chunks)


def _read_control_memfd() -> bytes:
    metadata = os.fstat(CONTROL_FD)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size < 0
        or metadata.st_size > MAX_CONTROL_BYTES
    ):
        _defect("control fd is not a bounded regular memfd")
    target = os.readlink(f"/proc/self/fd/{CONTROL_FD}")
    if target != CONTROL_MEMFD_TARGET:
        _defect("control fd target differs from exact anonymous memfd")
    seals = fcntl.fcntl(CONTROL_FD, fcntl.F_GET_SEALS)
    if seals != CONTROL_MEMFD_SEALS:
        _defect("control memfd does not have the exact immutable seal set")
    if os.lseek(CONTROL_FD, 0, os.SEEK_CUR) != 0:
        _defect("control memfd offset is not zero at verifier entry")
    payload = _read_fd_bounded(
        CONTROL_FD, MAX_CONTROL_BYTES, "cache verifier control"
    )
    if len(payload) != metadata.st_size:
        _defect("control memfd size differs from bytes read")
    return payload


def _read_all_fd(descriptor: int, expected_size: int, description: str) -> bytes:
    chunks: list[bytes] = []
    offset = 0
    while offset < expected_size:
        chunk = os.pread(descriptor, min(1 << 20, expected_size - offset), offset)
        if not chunk:
            break
        chunks.append(chunk)
        offset += len(chunk)
    if offset != expected_size or os.pread(descriptor, 1, offset):
        _defect(f"{description} changed size during read")
    return b"".join(chunks)


def _identity_from_fd(
    descriptor: int, description: str, *, maximum: int
) -> tuple[dict[str, Any], os.stat_result]:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode) or before.st_size < 0 or before.st_size > maximum:
        _defect(f"{description} is not a bounded regular file")
    payload = _read_all_fd(descriptor, before.st_size, description)
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
        _defect(f"{description} mutated during read")
    return (
        {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        after,
    )


def _leader_identity_from_fd(
    descriptor: int,
    path: str,
    description: str,
    *,
    maximum: int = MAX_AUTHORITY_BYTES,
) -> dict[str, Any]:
    identity, metadata = _identity_from_fd(
        descriptor, description, maximum=maximum
    )
    resolved_path = os.path.realpath(path)
    return {
        "device": int(metadata.st_dev),
        "inode": int(metadata.st_ino),
        "mode": int(metadata.st_mode),
        "path": path,
        "resolved_path": resolved_path,
        "sha256": identity["sha256"],
        "size_bytes": identity["size_bytes"],
    }


def _bootstrap_identity_from_path(path: str) -> dict[str, Any]:
    _, identity, metadata = _read_absolute_regular(
        path,
        maximum=MAX_AUTHORITY_BYTES,
        description="installed bootstrap_external",
    )
    return {
        "device": int(metadata.st_dev),
        "inode": int(metadata.st_ino),
        "mode": int(metadata.st_mode),
        "path": identity["path"],
        "sha256": identity["sha256"],
        "size_bytes": identity["size_bytes"],
    }


def _open_absolute_dir_nofollow(path: str) -> int:
    if not path.startswith("/") or os.path.normpath(path) != path:
        _defect("absolute directory path is not normalized")
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


def _open_relative_dir_nofollow(root_fd: int, relative: str) -> int:
    relative = _require_relative(relative, "relative directory")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.dup(root_fd)
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
) -> tuple[bytes, dict[str, Any]]:
    relative = _require_relative(relative, description)
    parts = relative.split("/")
    parent_fd = os.dup(root_fd)
    flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, flags_dir, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        try:
            identity, _ = _identity_from_fd(descriptor, description, maximum=maximum)
            payload = _read_all_fd(descriptor, identity["size_bytes"], description)
        finally:
            os.close(descriptor)
        return payload, {
            "path": relative,
            "sha256": identity["sha256"],
            "size_bytes": identity["size_bytes"],
        }
    finally:
        os.close(parent_fd)


def _observe_relative_regular(
    root_fd: int,
    relative: str,
    *,
    maximum: int,
    description: str,
) -> tuple[bytes | None, dict[str, Any]]:
    """Preserve an actual size when a physical file cannot be fully admitted."""

    relative = _require_relative(relative, description)
    parts = relative.split("/")
    parent_fd = os.dup(root_fd)
    flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, flags_dir, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        try:
            before = os.fstat(descriptor)
            size = int(before.st_size)
            if size < 0 or size > (1 << 64) - 1:
                _defect(f"{description} reports an unrepresentable size")
            unavailable = {
                "path": relative,
                "sha256": "0" * 64,
                "size_bytes": size,
            }
            if not stat.S_ISREG(before.st_mode) or size > maximum:
                return None, unavailable
            try:
                payload = _read_all_fd(descriptor, size, description)
                after = os.fstat(descriptor)
            except (OSError, VerifierDefect, ValueError):
                return None, unavailable
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
                return None, unavailable
            return payload, {
                "path": relative,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        finally:
            os.close(descriptor)
    finally:
        os.close(parent_fd)


def _read_absolute_regular(
    path: str, *, maximum: int, description: str
) -> tuple[bytes, dict[str, Any], os.stat_result]:
    if not path.startswith("/") or os.path.normpath(path) != path:
        _defect(f"{description} path is not normalized absolute")
    parent, leaf = os.path.split(path)
    parent_fd = _open_absolute_dir_nofollow(parent)
    try:
        descriptor = os.open(
            leaf,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        try:
            identity, metadata = _identity_from_fd(
                descriptor, description, maximum=maximum
            )
            payload = _read_all_fd(descriptor, identity["size_bytes"], description)
        finally:
            os.close(descriptor)
    finally:
        os.close(parent_fd)
    return payload, {"path": path, **identity}, metadata


def _parse_proc_stat(payload: bytes, expected_pid: int, description: str) -> int:
    opening = payload.find(b"(")
    closing = payload.rfind(b") ")
    if opening <= 0 or closing <= opening:
        _defect(f"{description} has ambiguous framing")
    if payload[:opening].strip() != str(expected_pid).encode("ascii"):
        _defect(f"{description} PID differs")
    fields = payload[closing + 2 :].strip().split()
    if len(fields) < 20 or re.fullmatch(rb"(?:0|[1-9][0-9]*)", fields[19]) is None:
        _defect(f"{description} lacks canonical start time")
    value = int(fields[19])
    if value <= 0:
        _defect(f"{description} start time is not positive")
    return value


def _proc_start_time(pid: int) -> int:
    payload = _read_proc_file(pid, "stat", 65_536)
    return _parse_proc_stat(payload, pid, f"PID {pid} stat")


def _proc_bytes(pid: int, leaf: str, maximum: int) -> bytes:
    return _read_proc_file(pid, leaf, maximum)


def _read_proc_file(pid: int, leaf: str, maximum: int) -> bytes:
    """Read one bounded proc pseudo-file without trusting its zero ``st_size``."""

    if pid <= 0 or DECIMAL.fullmatch(str(pid)) is None:
        _defect("proc PID is not canonical positive decimal")
    if leaf not in {"cmdline", "environ", "stat"}:
        _defect("proc leaf is outside the verifier allowlist")
    proc_fd = _open_absolute_dir_nofollow(f"/proc/{pid}")
    try:
        descriptor = os.open(
            leaf,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=proc_fd,
        )
        try:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, min(65_536, maximum + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > maximum:
                    _defect(f"PID {pid} {leaf} exceeds cap")
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            os.close(descriptor)
    finally:
        os.close(proc_fd)


def _proc_symlink(pid: int, leaf: str) -> str:
    value = os.readlink(f"/proc/{pid}/{leaf}")
    return _require_text(value, f"PID {pid} {leaf} target")


def _decode_cmdline(payload: bytes, description: str) -> list[str]:
    if not payload or not payload.endswith(b"\x00"):
        _defect(f"{description} lacks one terminal NUL")
    raw = payload[:-1].split(b"\x00")
    if not raw or any(not item for item in raw):
        _defect(f"{description} contains an empty argument")
    result: list[str] = []
    for item in raw:
        try:
            result.append(item.decode("utf-8", errors="strict"))
        except UnicodeError as error:
            raise VerifierDefect(f"{description} is not UTF-8") from error
    return result


def _observe_parent_environment(pid: int) -> dict[str, Any] | None:
    try:
        payload = _proc_bytes(pid, "environ", 65_536)
        if payload and not payload.endswith(b"\x00"):
            return None
        entries = payload[:-1].split(b"\x00") if payload else []
        names: list[str] = []
        thread: dict[str, str | None] = {
            "MKL_NUM_THREADS": None,
            "OMP_NUM_THREADS": None,
            "OPENBLAS_NUM_THREADS": None,
        }
        seen_relevant: set[str] = set()
        for raw in entries:
            if not raw or b"=" not in raw:
                return None
            raw_name, raw_value = raw.split(b"=", 1)
            try:
                name = raw_name.decode("ascii", errors="strict")
            except UnicodeError:
                continue
            if name.startswith("PYTHON"):
                names.append(name)
            if name in thread:
                if name in seen_relevant:
                    return None
                seen_relevant.add(name)
                try:
                    value = raw_value.decode("ascii", errors="strict")
                except UnicodeError:
                    return None
                if not value or len(value.encode("ascii")) > 128 or any(
                    ord(character) < 32 or ord(character) > 126
                    for character in value
                ):
                    return None
                thread[name] = value
        if (
            len(names) > 128
            or len(set(names)) != len(names)
            or any(
                not name
                or len(name.encode("ascii")) > 128
                or any(ord(character) < 32 or ord(character) > 126 for character in name)
                for name in names
            )
        ):
            return None
        names.sort(key=lambda value: value.encode("ascii"))
        return {
            "python_prefixed_names": names,
            "thread_environment": thread,
        }
    except (OSError, VerifierDefect, ValueError):
        return None


def _observe_leader_path(path: str, description: str) -> dict[str, Any] | None:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
        try:
            return _leader_identity_from_fd(
                descriptor, path, description, maximum=MAX_AUTHORITY_BYTES
            )
        finally:
            os.close(descriptor)
    except (OSError, VerifierDefect, ValueError):
        return None


def _observe_bootstrap() -> dict[str, Any] | None:
    try:
        return _bootstrap_identity_from_path(BOOTSTRAP_EXTERNAL_PATH)
    except (OSError, VerifierDefect, ValueError):
        return None


def _read_absolute_identity_observation(
    path: str, description: str, *, maximum: int
) -> tuple[bytes | None, dict[str, Any] | None]:
    try:
        payload, identity, _ = _read_absolute_regular(
            path, maximum=maximum, description=description
        )
        return payload, identity
    except (OSError, VerifierDefect, ValueError):
        return None, None


def _leader_core(value: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(
        value[key]
        for key in (
            "device",
            "inode",
            "mode",
            "resolved_path",
            "sha256",
            "size_bytes",
        )
    )


def _identity_check_status(observed: Any, expected: Any) -> str:
    if observed is None:
        return "UNAVAILABLE"
    return "MATCH" if observed == expected else "MISMATCH"


def _identity_control(value: Any, description: str) -> dict[str, Any]:
    item = _require_mapping(value, description)
    _require_keys(item, IDENTITY_KEYS, description)
    path = _require_text(
        item["path"], f"{description} path", maximum=MAX_PATH_BYTES
    )
    sha256 = _require_sha256(item["sha256"], f"{description} SHA-256")
    size = _require_int(
        item["size_bytes"], f"{description} size", maximum=(1 << 64) - 1
    )
    return {"path": path, "sha256": sha256, "size_bytes": size}


def _bootstrap_control(value: Any, description: str) -> dict[str, Any]:
    item = _require_mapping(value, description)
    _require_keys(item, BOOTSTRAP_IDENTITY_KEYS, description)
    normalized = {
        "device": _require_int(
            item["device"], f"{description} device", maximum=(1 << 64) - 1
        ),
        "inode": _require_int(
            item["inode"], f"{description} inode", minimum=1, maximum=(1 << 64) - 1
        ),
        "mode": _require_int(
            item["mode"], f"{description} mode", maximum=(1 << 64) - 1
        ),
        "path": _require_text(
            item["path"], f"{description} path", maximum=MAX_PATH_BYTES
        ),
        "sha256": _require_sha256(item["sha256"], f"{description} SHA-256"),
        "size_bytes": _require_int(
            item["size_bytes"],
            f"{description} size",
            maximum=(1 << 64) - 1,
        ),
    }
    if not stat.S_ISREG(normalized["mode"]):
        _defect(f"{description} mode is not regular")
    return normalized


def _leader_control(value: Any, description: str) -> dict[str, Any]:
    item = _require_mapping(value, description)
    _require_keys(item, LEADER_IDENTITY_KEYS, description)
    normalized = {
        "device": _require_int(
            item["device"], f"{description} device", maximum=(1 << 64) - 1
        ),
        "inode": _require_int(
            item["inode"], f"{description} inode", minimum=1, maximum=(1 << 64) - 1
        ),
        "mode": _require_int(
            item["mode"], f"{description} mode", maximum=(1 << 64) - 1
        ),
        "path": _require_text(
            item["path"], f"{description} path", maximum=MAX_PATH_BYTES
        ),
        "resolved_path": _require_text(
            item["resolved_path"],
            f"{description} resolved path",
            maximum=MAX_PATH_BYTES,
        ),
        "sha256": _require_sha256(item["sha256"], f"{description} SHA-256"),
        "size_bytes": _require_int(
            item["size_bytes"],
            f"{description} size",
            maximum=(1 << 64) - 1,
        ),
    }
    if (
        not stat.S_ISREG(normalized["mode"])
        or not normalized["path"].startswith("/")
        or os.path.normpath(normalized["path"]) != normalized["path"]
        or not normalized["resolved_path"].startswith("/")
        or os.path.normpath(normalized["resolved_path"])
        != normalized["resolved_path"]
    ):
        _defect(f"{description} path/mode closure differs")
    return normalized


def _leader_group_control(value: Any, description: str) -> dict[str, Any]:
    group = _require_mapping(value, description)
    _require_keys(group, LEADER_GROUP_KEYS, description)
    normalized = {
        name: _leader_control(group[name], f"{description}.{name}")
        for name in ("command", "proc_self_exe", "sys_executable")
    }
    records = list(normalized.values())
    if (
        len({(record["device"], record["inode"]) for record in records}) != 1
        or any(
            record["resolved_path"] != "/usr/bin/python3.9"
            or record["sha256"] != CPYTHON_SHA256
            or record["size_bytes"] != CPYTHON_SIZE
            for record in records
        )
    ):
        _defect(f"{description} aliases do not identify the pinned leader")
    return normalized


def _parent_environment_control(value: Any, description: str) -> dict[str, Any]:
    environment = _require_mapping(value, description)
    _require_keys(environment, PARENT_ENVIRONMENT_KEYS, description)
    python_names = _require_list(
        environment["python_prefixed_names"],
        f"{description}.python_prefixed_names",
        maximum=128,
    )
    if python_names:
        _defect(f"{description} contains a PYTHON-prefixed key")
    thread = _require_mapping(
        environment["thread_environment"], f"{description}.thread_environment"
    )
    _require_keys(thread, THREAD_ENVIRONMENT_KEYS, f"{description}.thread_environment")
    expected_thread = {
        "MKL_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
    }
    if thread != expected_thread:
        _defect(f"{description} thread environment differs")
    return {
        "python_prefixed_names": [],
        "thread_environment": expected_thread,
    }


def _validate_cache_state_list(value: Any, description: str) -> list[dict[str, str]]:
    items = _require_list(value, description, maximum=len(CACHE_PATHS))
    result: list[dict[str, str]] = []
    for index, raw in enumerate(items):
        item = _require_mapping(raw, f"{description}[{index}]")
        _require_keys(item, CACHE_STATE_KEYS, f"{description}[{index}]")
        path = _require_relative(item["path"], f"{description}[{index}].path")
        state = _require_text(
            item["state"], f"{description}[{index}].state", maximum=32, ascii_only=True
        )
        if state != "ABSENT":
            _defect(f"{description}[{index}] records a non-ABSENT state")
        result.append({"path": path, "state": state})
    if [item["path"] for item in result] != list(CACHE_PATHS):
        _defect(f"{description} does not equal the exact cache path order")
    return result


def _validate_module_list(
    value: Any, description: str, *, a4: bool
) -> list[dict[str, Any]]:
    items = _require_list(value, description, maximum=10 if a4 else 4_096)
    result: list[dict[str, Any]] = []
    keys = A4_MODULE_KEYS if a4 else MODULE_KEYS
    previous: bytes | None = None
    for index, raw in enumerate(items):
        item = _require_mapping(raw, f"{description}[{index}]")
        _require_keys(item, keys, f"{description}[{index}]")
        name = _require_text(item["name"], f"{description}[{index}].name", maximum=256)
        encoded = name.encode("utf-8")
        if previous is not None and encoded <= previous:
            _defect(f"{description} is not uniquely byte-sorted")
        previous = encoded
        for nullable in ("cached", "file", "origin"):
            if item[nullable] is not None:
                _require_text(
                    item[nullable],
                    f"{description}[{index}].{nullable}",
                    maximum=MAX_PATH_BYTES,
                )
        _require_text(item["loader_type"], f"{description}[{index}].loader_type", maximum=512)
        if a4:
            _require_relative(item["source_path"], f"{description}[{index}].source_path")
            _require_sha256(item["source_sha256"], f"{description}[{index}].source_sha256")
            _require_int(
                item["source_size_bytes"],
                f"{description}[{index}].source_size_bytes",
                maximum=(1 << 64) - 1,
            )
            _require_relative(item["expected_cache_path"], f"{description}[{index}].expected_cache_path")
        result.append(dict(item))
    return result


def _validate_observation(
    value: Any, description: str, checkpoint: str
) -> dict[str, Any]:
    item = _require_mapping(value, description)
    _require_keys(item, OBSERVATION_KEYS, description)
    if _require_text(item["checkpoint"], f"{description}.checkpoint", maximum=32, ascii_only=True) != checkpoint:
        _defect(f"{description} checkpoint differs")
    _require_int(item["observed_monotonic_ns"], f"{description}.observed_monotonic_ns")
    parent = _require_mapping(item["parent_identity"], f"{description}.parent_identity")
    _require_keys(parent, PROCESS_IDENTITY_KEYS, f"{description}.parent_identity")
    _require_int(parent["pid"], f"{description}.parent_identity.pid", minimum=1, maximum=(1 << 31) - 1)
    _require_int(parent["start_time_clock_ticks"], f"{description}.parent_identity.start_time_clock_ticks", minimum=1)
    interpreter = _require_mapping(item["interpreter"], f"{description}.interpreter")
    _require_keys(interpreter, INTERPRETER_KEYS, f"{description}.interpreter")
    _require_bool(interpreter["dont_write_bytecode"], f"{description}.interpreter.dont_write_bytecode")
    if interpreter["pycache_prefix"] is not None:
        _require_text(interpreter["pycache_prefix"], f"{description}.interpreter.pycache_prefix")
    _require_text(interpreter["implementation_cache_tag"], f"{description}.interpreter.implementation_cache_tag", maximum=64, ascii_only=True)
    flags = _require_mapping(interpreter["flags"], f"{description}.interpreter.flags")
    _require_keys(flags, FLAG_KEYS, f"{description}.interpreter.flags")
    for key in FLAG_KEYS:
        _require_int(flags[key], f"{description}.interpreter.flags.{key}", maximum=16)
    _validate_cache_state_list(item["cache_paths"], f"{description}.cache_paths")
    _validate_module_list(item["retained_modules"], f"{description}.retained_modules", a4=False)
    _validate_module_list(item["a4_modules"], f"{description}.a4_modules", a4=True)
    paths = _require_list(item["sys_path"], f"{description}.sys_path", maximum=128)
    for index, path in enumerate(paths):
        _require_text(
            path, f"{description}.sys_path[{index}]", maximum=MAX_PATH_BYTES
        )
    meta = _require_list(item["sys_meta_path"], f"{description}.sys_meta_path", maximum=64)
    for index, raw in enumerate(meta):
        record = _require_mapping(raw, f"{description}.sys_meta_path[{index}]")
        _require_keys(record, META_PATH_KEYS, f"{description}.sys_meta_path[{index}]")
        _require_text(record["type"], f"{description}.sys_meta_path[{index}].type", maximum=512)
        if record["origin"] is not None:
            _require_text(
                record["origin"],
                f"{description}.sys_meta_path[{index}].origin",
                maximum=MAX_PATH_BYTES,
            )
    if item["user_site_enabled"] is not None:
        _require_bool(item["user_site_enabled"], f"{description}.user_site_enabled")
    return dict(item)


def _validate_control(value: Any) -> dict[str, Any]:
    control = _require_mapping(value, "cache verifier control")
    _require_keys(control, CONTROL_KEYS, "cache verifier control")
    if control["artifact_kind"] != "a4_v2_cache_policy_verifier_control":
        _defect("cache verifier control artifact_kind differs")
    if _require_int(control["schema_version"], "control schema_version", maximum=16) != SCHEMA_VERSION:
        _defect("cache verifier control schema_version differs")

    authority = _require_mapping(control["authority"], "control authority")
    _require_keys(authority, AUTHORITY_KEYS, "control authority")
    normalized_authority = {
        key: _identity_control(authority[key], f"control authority {key}")
        for key in sorted(AUTHORITY_KEYS)
    }
    required_paths = {
        "cache_prep_binding": CACHE_BINDING_PATH,
        "cache_protocol_authority": CACHE_AUTHORITY_PATH,
        "cache_static_closure": STATIC_CLOSURE_PATH,
        "implementation_manifest": IMPLEMENTATION_MANIFEST_PATH,
        "runtime_schema": RUNTIME_SCHEMA_PATH,
    }
    for key, path in required_paths.items():
        if normalized_authority[key]["path"] != path:
            _defect(f"control authority {key} path differs")
    if normalized_authority["par_r1_authorization"]["path"] != (
        "docs/saq_a4_v2_par_r1_authorization_2026_07_15.md"
    ):
        _defect("PAR-R1 authorization path differs")

    clone = _require_mapping(control["clone"], "control clone")
    _require_keys(clone, CLONE_KEYS, "control clone")
    if clone["root"] != CLONE_ROOT or clone["branch"] != BRANCH:
        _defect("control clone root/branch differs")
    if clone["origin_fetch_url"] != FETCH_URL or clone["origin_push_url"] != PUSH_URL:
        _defect("control clone remote URLs differ")
    expected_commit = _require_oid(clone["expected_commit"], "control expected commit")
    expected_tree = _require_oid(clone["expected_tree_oid"], "control expected tree")
    source_tree = _require_sha256(clone["source_tree_sha256"], "control source tree")
    staging = _require_relative(clone["par_staging_relative_path"], "control PAR staging path")
    if staging != "docs/saq_a4_v2_par_artifacts_2026_07_14.staging":
        _defect("control PAR staging path differs")
    allowed_roots = _require_list(
        clone["allowed_installed_origin_roots"],
        "control allowed installed roots",
        maximum=5,
    )
    normalized_roots: list[str] = []
    for index, raw in enumerate(allowed_roots):
        root = _require_text(
            raw, f"allowed installed root {index}", maximum=MAX_PATH_BYTES
        )
        if not root.startswith("/") or os.path.normpath(root) != root:
            _defect("allowed installed origin root is not normalized absolute")
        normalized_roots.append(root)
    if normalized_roots != list(INSTALLED_ORIGIN_ROOTS):
        _defect("allowed installed origin roots differ from frozen policy literals")

    output = _require_mapping(control["output"], "control output")
    _require_keys(output, OUTPUT_KEYS, "control output")
    if (
        output["artifact_name"] != OUTPUT_NAME
        or output["staging_relative_path"] != staging
        or _require_int(output["maximum_bytes"], "control output maximum", maximum=MAX_OUTPUT_BYTES) != MAX_OUTPUT_BYTES
    ):
        _defect("control output contract differs")

    parent = _require_mapping(control["parent"], "control parent")
    _require_keys(parent, PARENT_KEYS, "control parent")
    pid = _require_int(parent["pid"], "control parent PID", minimum=1, maximum=(1 << 31) - 1)
    start = _require_int(parent["start_time_clock_ticks"], "control parent start", minimum=1)
    cmdline_hex = _require_text(
        parent["cmdline_hex"],
        "control parent cmdline hex",
        maximum=MAX_CMDLINE_HEX_BYTES,
        ascii_only=True,
    )
    if len(cmdline_hex) % 2 or re.fullmatch(r"[0-9a-f]*", cmdline_hex) is None:
        _defect("control parent cmdline hex is not canonical")
    cmdline_sha = _require_sha256(parent["cmdline_sha256"], "control parent cmdline SHA-256")
    cmdline_payload = bytes.fromhex(cmdline_hex)
    expected_parent_cmdline = b"\0".join(
        (
            b"python",
            b"-B",
            b"script/run_arbitrary_cardinality_a4_v2.py",
            b"par",
            b"docs/saq_a4_v2_par_artifacts_2026_07_14",
        )
    ) + b"\0"
    if (
        hashlib.sha256(cmdline_payload).hexdigest() != cmdline_sha
        or cmdline_payload != expected_parent_cmdline
    ):
        _defect("control parent cmdline identity is internally inconsistent")
    if parent["cwd"] != CLONE_ROOT:
        _defect("control parent cwd differs")
    leader = _leader_group_control(parent["leader"], "control parent leader")
    bootstrap = _bootstrap_control(
        parent["bootstrap_external"], "control parent bootstrap"
    )
    environment = _parent_environment_control(
        parent["environment"], "control parent environment"
    )
    if (
        bootstrap["path"] != BOOTSTRAP_EXTERNAL_PATH
        or bootstrap["sha256"] != BOOTSTRAP_EXTERNAL_SHA256
        or bootstrap["size_bytes"] != BOOTSTRAP_EXTERNAL_SIZE
    ):
        _defect("control parent bootstrap identity differs")

    cache_paths = _require_list(control["cache_paths"], "control cache paths", maximum=len(CACHE_PATHS))
    for index, path in enumerate(cache_paths):
        _require_relative(path, f"control cache path {index}")
    if cache_paths != list(CACHE_PATHS):
        _defect("control cache paths differ")

    reviewed_sources = _require_list(
        control["reviewed_python_sources"],
        "reviewed Python sources",
        maximum=10,
    )
    normalized_sources: list[dict[str, Any]] = []
    previous: bytes | None = None
    for index, raw in enumerate(reviewed_sources):
        item = _require_mapping(raw, f"reviewed source {index}")
        _require_keys(item, SOURCE_KEYS, f"reviewed source {index}")
        path = _require_relative(item["path"], f"reviewed source {index} path")
        encoded = path.encode("utf-8")
        if previous is not None and encoded <= previous:
            _defect("reviewed Python sources are not uniquely byte-sorted")
        previous = encoded
        if not path.startswith("script/") or not path.endswith(".py"):
            _defect("reviewed Python source path is outside script/*.py")
        normalized_sources.append(
            {
                "family": _require_text(item["family"], f"reviewed source {index} family", maximum=128),
                "git_blob": _require_oid(item["git_blob"], f"reviewed source {index} blob"),
                "path": path,
                "role": _require_text(item["role"], f"reviewed source {index} role", maximum=128),
                "sha256": _require_sha256(item["sha256"], f"reviewed source {index} SHA-256"),
                "size_bytes": _require_int(
                    item["size_bytes"],
                    f"reviewed source {index} size",
                    maximum=(1 << 64) - 1,
                ),
            }
        )
    if len(normalized_sources) != 10:
        _defect("reviewed Python source inventory is not exactly ten")

    startup = _validate_observation(
        control["startup_observation"], "startup observation", "STARTUP_PREIMPORT"
    )
    preterminal_raw = _require_list(
        control["preterminal_observations"],
        "preterminal observations",
        maximum=2,
    )
    if len(preterminal_raw) != 2:
        _defect("preterminal observations are not exactly B and P")
    preterminal = [
        _validate_observation(preterminal_raw[0], "B preterminal observation", "B_PRETERMINAL"),
        _validate_observation(preterminal_raw[1], "P preterminal observation", "P_PRETERMINAL"),
    ]
    for description, observation in (
        ("startup", startup),
        ("B preterminal", preterminal[0]),
        ("P preterminal", preterminal[1]),
    ):
        if observation["parent_identity"] != {"pid": pid, "start_time_clock_ticks": start}:
            _defect(f"{description} observation parent identity differs")

    return {
        "artifact_kind": control["artifact_kind"],
        "authority": normalized_authority,
        "cache_paths": list(CACHE_PATHS),
        "clone": {
            "allowed_installed_origin_roots": normalized_roots,
            "branch": BRANCH,
            "expected_commit": expected_commit,
            "expected_tree_oid": expected_tree,
            "origin_fetch_url": FETCH_URL,
            "origin_push_url": PUSH_URL,
            "par_staging_relative_path": staging,
            "root": CLONE_ROOT,
            "source_tree_sha256": source_tree,
        },
        "output": {
            "artifact_name": OUTPUT_NAME,
            "maximum_bytes": MAX_OUTPUT_BYTES,
            "staging_relative_path": staging,
        },
        "parent": {
            "bootstrap_external": bootstrap,
            "cmdline_hex": cmdline_hex,
            "cmdline_sha256": cmdline_sha,
            "cwd": CLONE_ROOT,
            "environment": environment,
            "leader": leader,
            "pid": pid,
            "start_time_clock_ticks": start,
        },
        "preterminal_observations": preterminal,
        "reviewed_python_sources": normalized_sources,
        "schema_version": SCHEMA_VERSION,
        "startup_observation": startup,
    }


def _run_git_observation(
    suffix: Sequence[str], description: str
) -> tuple[int, bytes, bytes]:
    argv = [*GIT_PREFIX, *suffix]
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/",
            env=GIT_ENVIRONMENT,
            check=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired as error:
        raise TimeoutError(f"{description} Git execution timed out") from error
    if (
        len(completed.stdout) > MAX_GIT_OUTPUT_BYTES
        or len(completed.stderr) > MAX_GIT_OUTPUT_BYTES
    ):
        raise OSError(errno.EFBIG, f"{description} Git output exceeds cap")
    if completed.returncode < 0:
        raise ChildProcessError(
            f"{description} Git child was signal-terminated"
        )
    return completed.returncode, completed.stdout, completed.stderr


def _git_scalar_observation(
    suffix: Sequence[str],
    description: str,
    *,
    git_oid: bool,
    mismatches: MismatchRecorder,
    ledger: dict[str, Any],
) -> str:
    """Return one schema-representable scalar without turning drift into a defect."""

    code, stdout, stderr = _run_git_observation(suffix, description)
    ledger["git_stdout_bytes"] += len(stdout)
    ledger["git_stderr_bytes"] += len(stderr)
    value: str | None = None
    if code == 0 and not stderr and stdout.endswith(b"\n"):
        raw = stdout[:-1]
        if raw and b"\n" not in raw and b"\r" not in raw:
            try:
                candidate = raw.decode("ascii", errors="strict")
            except UnicodeError:
                candidate = ""
            if git_oid:
                if HEX_40.fullmatch(candidate) is not None:
                    value = candidate
            elif (
                len(candidate.encode("ascii")) <= MAX_PATH_BYTES
                and all(32 <= ord(character) <= 126 for character in candidate)
            ):
                value = candidate
    if value is not None:
        return value
    mismatches.add(
        "CLONE_GIT_OBSERVATION_UNAVAILABLE",
        f"{description} did not return one schema-representable scalar",
        CLONE_ROOT,
    )
    return "0" * 40 if git_oid else "UNAVAILABLE"


def _git_direct_parent(
    commit: str,
    description: str,
    mismatches: MismatchRecorder,
    ledger: dict[str, Any],
) -> str | None:
    code, stdout, stderr = _run_git_observation(
        ("-C", CLONE_ROOT, "rev-list", "--parents", "-n", "1", commit),
        description,
    )
    ledger["git_stdout_bytes"] += len(stdout)
    ledger["git_stderr_bytes"] += len(stderr)
    fields = stdout.rstrip(b"\n").split(b" ") if code == 0 else []
    if (
        code != 0
        or stderr
        or not stdout.endswith(b"\n")
        or len(fields) != 2
    ):
        mismatches.add(
            "COMMIT_PARENT_UNAVAILABLE",
            f"{description} is absent, non-single-parent, or unparseable",
        )
        return None
    try:
        observed_commit = fields[0].decode("ascii", errors="strict")
        parent = fields[1].decode("ascii", errors="strict")
    except UnicodeError:
        mismatches.add(
            "COMMIT_PARENT_UNAVAILABLE",
            f"{description} parent record is not ASCII",
        )
        return None
    if HEX_40.fullmatch(observed_commit) is None or HEX_40.fullmatch(parent) is None:
        mismatches.add(
            "COMMIT_PARENT_UNAVAILABLE",
            f"{description} parent record is not a Git OID pair",
        )
        return None
    if observed_commit != commit:
        mismatches.add(
            "COMMIT_IDENTITY_MISMATCH",
            f"{description} resolved a different commit",
        )
        return None
    return parent


def _git_changed_paths(
    commit: str,
    expected: Sequence[str],
    description: str,
    mismatches: MismatchRecorder,
    ledger: dict[str, Any],
) -> None:
    code, stdout, stderr = _run_git_observation(
        (
            "-C",
            CLONE_ROOT,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "-z",
            commit,
        ),
        description,
    )
    ledger["git_stdout_bytes"] += len(stdout)
    ledger["git_stderr_bytes"] += len(stderr)
    observed: list[str] | None = None
    if code == 0 and not stderr and (not stdout or stdout.endswith(b"\0")):
        try:
            observed = [
                item.decode("utf-8", errors="strict")
                for item in stdout.split(b"\0")[:-1]
            ]
        except UnicodeError:
            observed = None
    if observed is None or any(
        RELATIVE_PATH.fullmatch(path) is None for path in observed
    ):
        mismatches.add(
            "COMMIT_CHANGED_PATHS_UNAVAILABLE",
            f"{description} changed-path inventory is unavailable",
        )
        return
    observed.sort(key=lambda value: value.encode("utf-8"))
    expected_sorted = sorted(expected, key=lambda value: value.encode("utf-8"))
    if observed != expected_sorted or len(set(observed)) != len(observed):
        mismatches.add(
            "COMMIT_CHANGED_PATHS_MISMATCH",
            f"{description} changed-path set differs",
        )


def _git_tree_oid(
    commit: str,
    description: str,
    mismatches: MismatchRecorder,
    ledger: dict[str, Any],
) -> str | None:
    code, stdout, stderr = _run_git_observation(
        ("-C", CLONE_ROOT, "rev-parse", f"{commit}^{{tree}}"), description
    )
    ledger["git_stdout_bytes"] += len(stdout)
    ledger["git_stderr_bytes"] += len(stderr)
    try:
        value = stdout.decode("ascii", errors="strict").rstrip("\n")
    except UnicodeError:
        value = ""
    if (
        code != 0
        or stderr
        or stdout != (value + "\n").encode("ascii")
        or HEX_40.fullmatch(value) is None
    ):
        mismatches.add(
            "COMMIT_TREE_UNAVAILABLE",
            f"{description} tree identity is unavailable",
        )
        return None
    return value


def _parse_full_git_tree(payload: bytes) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    if payload and not payload.endswith(b"\x00"):
        _defect("Git ls-tree output lacks terminal NUL")
    for index, record in enumerate(payload.split(b"\x00")[:-1]):
        try:
            header, raw_path = record.split(b"\t", 1)
            mode, kind, raw_oid = header.split(b" ", 2)
            path = raw_path.decode("utf-8", errors="strict")
            oid = raw_oid.decode("ascii", errors="strict")
            mode_text = mode.decode("ascii", errors="strict")
            kind_text = kind.decode("ascii", errors="strict")
        except (UnicodeError, ValueError) as error:
            raise VerifierDefect(
                f"Git ls-tree record {index} has invalid framing"
            ) from error
        _require_relative(path, f"Git ls-tree path {index}")
        _require_oid(oid, f"Git ls-tree OID {index}")
        if kind_text not in {"blob", "tree"} or mode_text not in {
            "040000",
            "100644",
            "100755",
        }:
            _defect("Git ls-tree contains a forbidden type/mode")
        if path in result:
            _defect("Git ls-tree contains a duplicate path")
        result[path] = {"git_blob": oid, "kind": kind_text, "mode": mode_text}
    if not result:
        _defect("Git ls-tree output is empty")
    return result


def _check_identity(
    root_fd: int,
    expected: Mapping[str, Any],
    label: str,
    mismatches: MismatchRecorder,
    read_ledger: dict[str, int],
    *,
    fallback_commit: str,
) -> tuple[bytes, dict[str, Any]]:
    try:
        payload, actual = _observe_relative_regular(
            root_fd,
            expected["path"],
            maximum=MAX_AUTHORITY_BYTES,
            description=label,
        )
    except (OSError, VerifierDefect, ValueError):
        payload = None
        actual = {
            "path": expected["path"],
            "sha256": "0" * 64,
            "size_bytes": 0,
        }
    if payload is not None:
        read_ledger["filesystem_bytes_read"] += len(payload)
    if payload is None or actual != expected:
        mismatches.add(
            "AUTHORITY_IDENTITY_MISMATCH",
            f"{label} physical bytes differ or are unavailable",
            expected["path"],
        )
    if payload is not None and actual == expected:
        return payload, actual

    code, git_payload, git_stderr = _run_git_observation(
        (
            "-C",
            CLONE_ROOT,
            "show",
            f"{fallback_commit}:{expected['path']}",
        ),
        f"reviewed fallback for {label}",
    )
    read_ledger["git_stdout_bytes"] += len(git_payload)
    read_ledger["git_stderr_bytes"] += len(git_stderr)
    if (
        code != 0
        or git_stderr
        or len(git_payload) != expected["size_bytes"]
        or hashlib.sha256(git_payload).hexdigest() != expected["sha256"]
    ):
        _defect(f"{label} is unavailable physically and from the reviewed Git tree")
    return git_payload, actual


def _check_cache_absence(root_fd: int, relative: str) -> str:
    relative = _require_relative(relative, "cache absence path")
    parts = relative.split("/")
    parent_fd = os.dup(root_fd)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        for component in parts[:-1]:
            try:
                next_fd = os.open(component, flags, dir_fd=parent_fd)
            except OSError as error:
                if error.errno == errno.ENOENT:
                    return "UNCLASSIFIABLE_PARENT_ABSENT"
                raise
            os.close(parent_fd)
            parent_fd = next_fd
        try:
            os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
        except OSError as error:
            if error.errno == errno.ENOENT:
                return "ABSENT"
            return f"UNCLASSIFIABLE_ERRNO_{error.errno}"
        return "PRESENT"
    finally:
        os.close(parent_fd)


def _origin_allowed(origin: str | None, clone: Mapping[str, Any]) -> bool:
    if origin is None or origin in {"built-in", "frozen"}:
        return True
    if origin == os.path.join(CLONE_ROOT, "script", "run_arbitrary_cardinality_a4_v2.py"):
        return True
    if not origin.startswith("/") or os.path.normpath(origin) != origin:
        return False
    return any(
        origin == root or origin.startswith(root + "/")
        for root in clone["allowed_installed_origin_roots"]
    )


def _forbidden_recorded_path(value: str | None) -> bool:
    return value is not None and (
        OLD_WORKTREE in value
        or (
            (value == CLONE_ROOT or value.startswith(CLONE_ROOT + "/"))
            and not value.startswith(CLONE_ROOT + "/script/")
        )
    )


def _check_observation(
    observation: Mapping[str, Any],
    clone: Mapping[str, Any],
    reviewed_by_path: Mapping[str, Mapping[str, Any]],
    mismatches: MismatchRecorder,
) -> dict[str, Any]:
    checkpoint = observation["checkpoint"]
    interpreter = observation["interpreter"]
    expected_flags = {
        "dont_write_bytecode": 1,
        "ignore_environment": 0,
        "isolated": 0,
        "no_site": 0,
        "optimize": 0,
    }
    if (
        interpreter["dont_write_bytecode"] is not True
        or interpreter["pycache_prefix"] is not None
        or interpreter["implementation_cache_tag"] != "cpython-39"
        or interpreter["flags"] != expected_flags
    ):
        mismatches.add(
            "SERIALIZED_INTERPRETER_STATE_MISMATCH",
            f"{checkpoint} interpreter/cache state differs",
        )
    for record in observation["cache_paths"]:
        if record != {"path": record["path"], "state": "ABSENT"}:
            mismatches.add(
                "SERIALIZED_CACHE_STATE_MISMATCH",
                f"{checkpoint} records non-absent cache state",
                record["path"],
            )
    for path in observation["sys_path"]:
        if OLD_WORKTREE in path:
            mismatches.add(
                "OLD_WORKTREE_PATH_OBSERVED",
                f"{checkpoint} sys.path names old worktree",
                path,
            )
        elif path != os.path.join(CLONE_ROOT, "script") and not any(
            path == root or path.startswith(root + "/")
            for root in INSTALLED_ORIGIN_ROOTS
        ):
            mismatches.add(
                "SYS_PATH_OUTSIDE_FROZEN_ROOTS",
                f"{checkpoint} sys.path entry is outside frozen roots",
                path,
            )
    clone_local = [
        path
        for path in observation["sys_path"]
        if path == CLONE_ROOT or path.startswith(CLONE_ROOT + "/")
    ]
    if clone_local != [os.path.join(CLONE_ROOT, "script")]:
        mismatches.add(
            "CLONE_IMPORT_ROOT_MISMATCH",
            f"{checkpoint} clone-local sys.path is not exact script root",
        )
    observed_a4_by_name = {
        item["name"]: item for item in observation["a4_modules"]
    }
    for module in observation["retained_modules"]:
        a4_record = observed_a4_by_name.get(module["name"])
        a4_origin = (
            os.path.join(CLONE_ROOT, a4_record["source_path"])
            if a4_record is not None
            else None
        )
        a4_cached = (
            os.path.join(CLONE_ROOT, a4_record["expected_cache_path"])
            if a4_record is not None
            else None
        )
        for field in ("cached", "file", "origin"):
            if _forbidden_recorded_path(module[field]):
                mismatches.add(
                    "FORBIDDEN_MODULE_PATH",
                    f"{checkpoint} retained module {field} names a forbidden worktree path",
                    module[field],
                )
        if module["name"] == "__main__":
            expected_main = os.path.join(
                CLONE_ROOT, "script", "run_arbitrary_cardinality_a4_v2.py"
            )
            if module["file"] != expected_main or module["origin"] != expected_main:
                mismatches.add(
                    "MAIN_ORIGIN_MISMATCH",
                    f"{checkpoint} __main__ is not reviewed clone entrypoint",
                    module["origin"],
                )
        elif module["origin"] != a4_origin and not _origin_allowed(
            module["origin"], clone
        ):
            mismatches.add(
                "MODULE_ORIGIN_MISMATCH",
                f"{checkpoint} retained module origin is outside admitted roots",
                module["origin"],
            )
        if (
            module["file"] is not None
            and module["file"] != a4_origin
            and not _origin_allowed(module["file"], clone)
        ):
            mismatches.add(
                "MODULE_FILE_MISMATCH",
                f"{checkpoint} retained module file is outside admitted roots",
                module["file"],
            )
        if (
            module["cached"] is not None
            and module["cached"] != a4_cached
            and not _origin_allowed(module["cached"], clone)
        ):
            mismatches.add(
                "MODULE_CACHED_PATH_MISMATCH",
                f"{checkpoint} retained module cache metadata is outside admitted roots",
                module["cached"],
            )
    retained_names = {item["name"] for item in observation["retained_modules"]}
    if "sitecustomize" in retained_names or "usercustomize" in retained_names:
        mismatches.add(
            "CUSTOMIZATION_MODULE_PRESENT",
            f"{checkpoint} retained modules include site/user customization",
        )
    for meta in observation["sys_meta_path"]:
        if _forbidden_recorded_path(meta["origin"]) or (
            meta["origin"] is not None
            and not _origin_allowed(meta["origin"], clone)
        ):
            mismatches.add(
                "META_PATH_ORIGIN_MISMATCH",
                f"{checkpoint} meta-path origin is outside admitted roots",
                meta["origin"],
            )
    seen_a4: set[str] = set()
    for module in observation["a4_modules"]:
        path = module["source_path"]
        expected = reviewed_by_path.get(path)
        if expected is None:
            mismatches.add(
                "UNREVIEWED_A4_MODULE",
                f"{checkpoint} records an unreviewed A4 module",
                path,
            )
            continue
        seen_a4.add(path)
        expected_cached = (
            None
            if module["name"] == "__main__"
            else os.path.join(CLONE_ROOT, module["expected_cache_path"])
        )
        if (
            module["source_sha256"] != expected["sha256"]
            or module["source_size_bytes"] != expected["size_bytes"]
            or module["file"] != os.path.join(CLONE_ROOT, path)
            or module["origin"] != os.path.join(CLONE_ROOT, path)
            or module["cached"] != expected_cached
            or not module["expected_cache_path"].startswith("script/__pycache__/")
            or _forbidden_recorded_path(module["file"])
            or _forbidden_recorded_path(module["origin"])
            or (
                expected_cached is not None
                and OLD_WORKTREE in expected_cached
            )
        ):
            mismatches.add(
                "A4_MODULE_IDENTITY_MISMATCH",
                f"{checkpoint} A4 module identity differs",
                path,
            )
    return {
        "a4_module_count": len(observation["a4_modules"]),
        "checkpoint": checkpoint,
        "identity_sha256": hashlib.sha256(_canonical_body(observation)).hexdigest(),
        "retained_module_count": len(observation["retained_modules"]),
        "seen_reviewed_source_count": len(seen_a4),
        "sys_meta_path_count": len(observation["sys_meta_path"]),
        "sys_path_count": len(observation["sys_path"]),
    }


def _observe_self() -> dict[str, Any]:
    pid = os.getpid()
    cmdline = _proc_bytes(pid, "cmdline", MAX_CMDLINE_BYTES)
    expected_argv = [
        "/proc/self/fd/197",
        "-I",
        "-B",
        "-S",
        os.path.join(CLONE_ROOT, "script", "a4_v2_cache_policy_verifier.py"),
        "verify-parent-cache-policy",
        "--control-fd",
        "198",
    ]
    if _decode_cmdline(cmdline, "verifier cmdline") != expected_argv:
        _defect("verifier raw argv differs from frozen descriptor launch")
    if os.getcwd() != "/" or _proc_symlink(pid, "cwd") != "/":
        _defect("verifier cwd differs from root")
    if dict(os.environ) != {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}:
        _defect("verifier environment differs from exact closure")
    if (
        sys.flags.isolated != 1
        or sys.flags.dont_write_bytecode != 1
        or sys.flags.no_site != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.optimize != 0
        or sys.dont_write_bytecode is not True
        or sys.pycache_prefix is not None
    ):
        _defect("verifier interpreter flags/cache state differ")
    if any(path == CLONE_ROOT or path.startswith(CLONE_ROOT + "/") for path in sys.path):
        _defect("isolated verifier sys.path contains clone path")
    return {
        "cmdline_hex": cmdline.hex(),
        "cmdline_sha256": hashlib.sha256(cmdline).hexdigest(),
        "cwd": "/",
        "environment": {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        "flags": {
            "dont_write_bytecode": sys.flags.dont_write_bytecode,
            "ignore_environment": sys.flags.ignore_environment,
            "isolated": sys.flags.isolated,
            "no_site": sys.flags.no_site,
            "optimize": sys.flags.optimize,
        },
        "pid": pid,
        "start_time_clock_ticks": _proc_start_time(pid),
    }


def _verify(control: Mapping[str, Any], control_payload: bytes) -> dict[str, Any]:
    start_wall = time.monotonic_ns()
    start_self_usage = resource.getrusage(resource.RUSAGE_SELF)
    start_children_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    mismatches = MismatchRecorder()
    control_metadata = os.fstat(CONTROL_FD)
    ledger = {
        "cache_verifier_transient_bytes": {
            "control_allocated_bytes": int(control_metadata.st_blocks) * 512,
            "control_logical_bytes": len(control_payload),
            "stderr_allocated_bytes": 0,
            "stderr_logical_bytes": 0,
            "stdout_allocated_bytes": 0,
            "stdout_logical_bytes": 0,
        },
        "control_bytes": len(control_payload),
        "filesystem_bytes_read": 0,
        "git_stderr_bytes": 0,
        "git_stdout_bytes": 0,
    }
    verifier_process = _observe_self()
    expected_leader_group = control["parent"]["leader"]
    try:
        verifier_descriptor_observed = _leader_identity_from_fd(
            LEADER_FD,
            "/proc/self/fd/197",
            "verifier leader descriptor",
            maximum=MAX_AUTHORITY_BYTES,
        )
    except (OSError, VerifierDefect, ValueError):
        verifier_descriptor_observed = None
    verifier_proc_exe_observed = _observe_leader_path(
        "/proc/self/exe", "verifier /proc/self/exe"
    )
    for observed in (verifier_descriptor_observed, verifier_proc_exe_observed):
        if observed is not None:
            ledger["filesystem_bytes_read"] += observed["size_bytes"]
    verifier_leader_available = (
        verifier_descriptor_observed is not None
        and verifier_proc_exe_observed is not None
    )
    verifier_leader_matches = verifier_leader_available and (
        _leader_core(verifier_descriptor_observed)
        == _leader_core(expected_leader_group["proc_self_exe"])
        == _leader_core(verifier_proc_exe_observed)
    )
    verifier_leader_status = (
        "UNAVAILABLE"
        if not verifier_leader_available
        else "MATCH"
        if verifier_leader_matches
        else "MISMATCH"
    )
    if verifier_leader_status != "MATCH":
        mismatches.add(
            "VERIFIER_LEADER_IDENTITY_MISMATCH",
            "verifier descriptor/leader bytes or inode differ",
            "/proc/self/fd/197",
        )
    expected_bootstrap = control["parent"]["bootstrap_external"]
    bootstrap_observed = _observe_bootstrap()
    if bootstrap_observed is not None:
        ledger["filesystem_bytes_read"] += bootstrap_observed["size_bytes"]
    bootstrap_status = _identity_check_status(bootstrap_observed, expected_bootstrap)
    if bootstrap_status != "MATCH":
        mismatches.add(
            "VERIFIER_BOOTSTRAP_IDENTITY_MISMATCH",
            "installed bootstrap_external bytes differ",
            BOOTSTRAP_EXTERNAL_PATH,
        )
    verifier_process["bootstrap_external_check"] = {
        "expected": expected_bootstrap,
        "observed": bootstrap_observed,
        "status": bootstrap_status,
    }
    verifier_process["leader_check"] = {
        "descriptor_observed": verifier_descriptor_observed,
        "expected": expected_leader_group,
        "proc_exe_observed": verifier_proc_exe_observed,
        "status": verifier_leader_status,
    }

    root_fd = _open_absolute_dir_nofollow(CLONE_ROOT)
    try:
        authority_checks: list[dict[str, Any]] = []
        authority_payloads: dict[str, bytes] = {}
        for key in sorted(AUTHORITY_KEYS):
            payload, actual = _check_identity(
                root_fd,
                control["authority"][key],
                key,
                mismatches,
                ledger,
                fallback_commit=control["clone"]["expected_commit"],
            )
            authority_payloads[key] = payload
            authority_checks.append(
                {
                    "path": actual["path"],
                    "sha256": actual["sha256"],
                    "size_bytes": actual["size_bytes"],
                    "status": (
                        "MATCH"
                        if actual == control["authority"][key]
                        else "MISMATCH"
                    ),
                }
            )

        manifest = _require_mapping(
            _parse_canonical_document(
                authority_payloads["implementation_manifest"],
                "implementation manifest",
            ),
            "implementation manifest",
        )
        _require_keys(
            manifest,
            IMPLEMENTATION_MANIFEST_KEYS,
            "implementation manifest",
        )
        if (
            manifest["artifact_kind"] != "a4_v2_implementation_manifest"
            or manifest["schema_version"] != 2
        ):
            mismatches.add(
                "IMPLEMENTATION_MANIFEST_VERSION_MISMATCH",
                "implementation manifest kind/schema_version differs",
                IMPLEMENTATION_MANIFEST_PATH,
            )
        if manifest["cache_protocol_identity"] != control["authority"]["cache_protocol_authority"]:
            mismatches.add(
                "MANIFEST_CACHE_AUTHORITY_CROSSLINK_MISMATCH",
                "implementation manifest cache authority identity differs",
                IMPLEMENTATION_MANIFEST_PATH,
            )
        par_contract = _require_mapping(
            manifest["par_contract"], "implementation manifest par_contract"
        )
        if par_contract.get("par_command") != [
            "python",
            "-B",
            "script/run_arbitrary_cardinality_a4_v2.py",
            "par",
            "docs/saq_a4_v2_par_artifacts_2026_07_14",
        ]:
            mismatches.add(
                "MANIFEST_PAR_COMMAND_MISMATCH",
                "implementation manifest PAR command does not contain exact -B launch",
                IMPLEMENTATION_MANIFEST_PATH,
            )
        if manifest.get("source_tree_sha256") != control["clone"]["source_tree_sha256"]:
            mismatches.add(
                "SOURCE_TREE_IDENTITY_MISMATCH",
                "implementation manifest source-tree identity differs",
                IMPLEMENTATION_MANIFEST_PATH,
            )
        python_paths = manifest.get("python_source_files")
        if python_paths != [item["path"] for item in control["reviewed_python_sources"]]:
            mismatches.add(
                "PYTHON_SOURCE_INVENTORY_MISMATCH",
                "implementation manifest Python source inventory differs",
                IMPLEMENTATION_MANIFEST_PATH,
            )
        raw_source_entries = _require_list(
            manifest.get("source_files"),
            "implementation manifest source_files",
            maximum=EXPECTED_SOURCE_COUNT,
        )
        if len(raw_source_entries) != EXPECTED_SOURCE_COUNT:
            _defect("implementation manifest source inventory is not exactly 37")
        source_entries: list[dict[str, Any]] = []
        previous_source_path: bytes | None = None
        for index, raw_source in enumerate(raw_source_entries):
            source = _require_mapping(raw_source, f"manifest source {index}")
            _require_keys(
                source, MANIFEST_SOURCE_KEYS, f"manifest source {index}"
            )
            path = _require_relative(source["path"], f"manifest source {index} path")
            encoded_path = path.encode("utf-8")
            if previous_source_path is not None and encoded_path <= previous_source_path:
                _defect("implementation source paths are not uniquely byte-sorted")
            previous_source_path = encoded_path
            source_entries.append(
                {
                    "family": _require_text(
                        source["family"], f"manifest source {index} family", maximum=128
                    ),
                    "path": path,
                    "role": _require_text(
                        source["role"], f"manifest source {index} role", maximum=128
                    ),
                    "sha256": _require_sha256(
                        source["sha256"], f"manifest source {index} SHA-256"
                    ),
                    "size_bytes": _require_int(
                        source["size_bytes"],
                        f"manifest source {index} size",
                        maximum=(1 << 64) - 1,
                    ),
                }
            )
        source_preimage = [
            {
                "path": item["path"],
                "sha256": item["sha256"],
                "size_bytes": item["size_bytes"],
            }
            for item in source_entries
        ]
        recomputed_source_tree = hashlib.sha256(
            _canonical_body(source_preimage)
        ).hexdigest()
        if (
            recomputed_source_tree != manifest.get("source_tree_sha256")
            or recomputed_source_tree != control["clone"]["source_tree_sha256"]
        ):
            mismatches.add(
                "SOURCE_TREE_RECOMPUTATION_MISMATCH",
                "canonical 37-source preimage hash differs",
                IMPLEMENTATION_MANIFEST_PATH,
            )

        cache_authority = _require_mapping(
            _parse_canonical_document(
                authority_payloads["cache_protocol_authority"],
                "cache protocol authority",
            ),
            "cache protocol authority",
        )
        _require_keys(
            cache_authority, CACHE_AUTHORITY_KEYS, "cache protocol authority"
        )
        if (
            cache_authority["artifact_kind"] != "a4_v2_cache_protocol_authority"
            or cache_authority["schema_version"] != 1
            or cache_authority["stage"] != "A4-V2-CACHE-I"
            or cache_authority["outcome_ceiling"]
            != "GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS"
        ):
            mismatches.add(
                "CACHE_AUTHORITY_HEADER_MISMATCH",
                "cache authority header/stage/ceiling differs",
                CACHE_AUTHORITY_PATH,
            )
        if cache_authority["claim_ceiling"] != (
            "Artifact-governance source/static-review evidence only; no PREP "
            "readiness, parity, synthetic feasibility, SAQ limitation, systems "
            "performance, novelty, data authority, SRUN authority, or SAQ/CAQ "
            "change authority."
        ):
            mismatches.add(
                "CACHE_AUTHORITY_CLAIM_CEILING_MISMATCH",
                "cache authority claim ceiling differs",
                CACHE_AUTHORITY_PATH,
            )
        if cache_authority["future_authority_slots"] != [
            {
                "authority_path": (
                    "docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md"
                ),
                "stage": "A4-V2-CACHE-PREP-ISO",
                "status": "NOT_AUTHORIZED",
            },
            {
                "authority_path": (
                    "docs/saq_a4_v2_cache_prep_binding_2026_07_15.json"
                ),
                "stage": "A4-V2-CACHE-BIND",
                "status": "NOT_AUTHORIZED",
            },
            {
                "authority_path": (
                    "docs/saq_a4_v2_par_r1_authorization_2026_07_15.md"
                ),
                "stage": "A4-V2-PAR-R1",
                "status": "NOT_AUTHORIZED",
            },
            {
                "authority_path": None,
                "stage": "A4-V2-SRUN",
                "status": "NOT_AUTHORIZED",
            },
        ]:
            mismatches.add(
                "CACHE_AUTHORITY_FUTURE_SLOTS_MISMATCH",
                "cache authority future-stage slots differ",
                CACHE_AUTHORITY_PATH,
            )
        if cache_authority["prohibitions"] != [
            "NO_PYTHON_IMPORT_SYNTAX_BUILD_TEST_FIXTURE_RNG_OR_NATIVE_EXECUTION",
            "NO_CLONE_PREP_CACHE_VERIFIER_PAR_R1_OR_SRUN_EXECUTION",
            (
                "NO_QUARANTINE_ENUMERATION_READ_STAT_HASH_COPY_RENAME_CHMOD_"
                "CLEANUP_DELETE_OR_REUSE"
            ),
            "NO_DATASET_BASE_QUERY_GROUND_TRUTH_INDEX_OR_GENERATED_RESULT_ACCESS",
            "NO_RUNTIME_ENVIRONMENT_MUTATION",
            "NO_SAQ_OR_CAQ_ACCESS_OR_MODIFICATION",
        ]:
            mismatches.add(
                "CACHE_AUTHORITY_PROHIBITIONS_MISMATCH",
                "cache authority prohibition list differs",
                CACHE_AUTHORITY_PATH,
            )
        if cache_authority["no_execution_attestation"] != {
            "build_compiler_test_fixture_rng": "NOT_PERFORMED",
            "clone": "NOT_CREATED",
            "data_or_index_access": "NOT_PERFORMED",
            "environment_mutation": "NOT_PERFORMED",
            "par_r1": "NOT_PERFORMED",
            "prep": "NOT_PERFORMED",
            "python_import_syntax_or_execution": "NOT_PERFORMED",
            "quarantine_state": "NOT_ACCESSED_OR_MODIFIED",
            "saq_caq_access_or_change": "NOT_PERFORMED",
            "srun": "NOT_PERFORMED",
            "static_methods": [
                "SOURCE_AND_DOCUMENT_TEXT_INSPECTION",
                "GIT_DIFF_SHOW_HASH_OBJECT",
                "JQ_STRUCTURED_JSON_PARSING",
                "SHA256_AND_BYTE_SIZE_MEASUREMENT",
                "REGISTERED_NO_CLONE_HTTPS_EQUALITY_PROBE",
            ],
            "untracked_wip_used_as_evidence": False,
        }:
            mismatches.add(
                "CACHE_AUTHORITY_NO_EXECUTION_ATTESTATION_MISMATCH",
                "cache authority static-only attestation differs",
                CACHE_AUTHORITY_PATH,
            )
        authority_chain = _require_mapping(
            cache_authority["authority_chain"],
            "cache authority authority_chain",
        )
        _require_keys(
            authority_chain,
            AUTHORITY_CHAIN_KEYS,
            "cache authority authority_chain",
        )
        if authority_chain != {
            "cache_i_authorization_review_commit": CACHE_I_AUTHORIZATION_REVIEW,
            "cache_i_authorization_target_commit": CACHE_I_AUTHORIZATION_TARGET,
            "cache_p_review_commit": CACHE_P_REVIEW,
            "cache_p_target_commit": CACHE_P_TARGET,
            "implementation_parent_commit": CACHE_I_IMPLEMENTATION_PARENT,
        }:
            mismatches.add(
                "AUTHORITY_CHAIN_MISMATCH",
                "cache authority historical commit chain differs",
                CACHE_AUTHORITY_PATH,
            )
        parent_admission = _require_mapping(
            cache_authority["implementation_parent_admission"],
            "cache authority implementation_parent_admission",
        )
        _require_keys(
            parent_admission,
            IMPLEMENTATION_PARENT_ADMISSION_KEYS,
            "cache authority implementation_parent_admission",
        )
        expected_parent_stdout = (
            CACHE_I_IMPLEMENTATION_PARENT
            + "\trefs/heads/saq-arbitrary-cardinality-feasibility-v2\n"
        )
        if parent_admission != {
            "argv": list(IMPLEMENTATION_PARENT_ADMISSION_ARGV),
            "branch_ref": "refs/heads/saq-arbitrary-cardinality-feasibility-v2",
            "claim_ceiling": NO_CLONE_EQUALITY_CLAIM,
            "cwd": "/",
            "exit_code": 0,
            "expected_oid": CACHE_I_IMPLEMENTATION_PARENT,
            "home_absent_after": True,
            "home_absent_before": True,
            "home_path": "/tmp/saq-a4-v2-incident-git-home-absent",
            "observed_oid": CACHE_I_IMPLEMENTATION_PARENT,
            "role": "CACHE_I_IMPLEMENTATION_PARENT_ADMISSION",
            "status": "MATCH",
            "stderr": "",
            "stdin": "/dev/null",
            "stdout": expected_parent_stdout,
            "xdg_config_home_absent_after": True,
            "xdg_config_home_absent_before": True,
            "xdg_config_home_path": "/tmp/saq-a4-v2-incident-git-xdg-absent",
        }:
            mismatches.add(
                "IMPLEMENTATION_PARENT_ADMISSION_MISMATCH",
                "cache authority implementation-parent admission differs",
                CACHE_AUTHORITY_PATH,
            )
        commit_closure = _require_mapping(
            cache_authority["commit_closure"],
            "cache authority commit_closure",
        )
        _require_keys(
            commit_closure,
            COMMIT_CLOSURE_KEYS,
            "cache authority commit_closure",
        )
        if commit_closure != {
            "every_other_tracked_blob_rule": "UNCHANGED",
            "implementation_parent_commit": CACHE_I_IMPLEMENTATION_PARENT,
            "implementation_review_changed_paths": list(
                CACHE_I_REVIEW_CHANGED_PATHS
            ),
            "implementation_review_direct_child_required": True,
            "implementation_target_changed_paths": list(
                CACHE_I_TARGET_CHANGED_PATHS
            ),
            "implementation_target_direct_parent_required": True,
            "review_head_closure_role": (
                "LIVE_NON_EVIDENTIARY_POST_COMMIT_PREDICATE"
            ),
            "target_head_closure_role": (
                "MANDATORY_IN_DIRECT_CHILD_REVIEW_MEMO"
            ),
        }:
            mismatches.add(
                "IMPLEMENTATION_COMMIT_CLOSURE_MISMATCH",
                "cache authority implementation commit closure differs",
                CACHE_AUTHORITY_PATH,
            )
        protocol_components = _require_mapping(
            cache_authority["protocol_components"],
            "cache authority protocol_components",
        )
        _require_keys(
            protocol_components,
            PROTOCOL_COMPONENT_KEYS,
            "cache authority protocol_components",
        )
        normalized_protocol_components = {
            key: _identity_control(
                protocol_components[key],
                f"cache authority protocol component {key}",
            )
            for key in sorted(PROTOCOL_COMPONENT_KEYS)
        }
        if any(
            normalized_protocol_components[key]["path"]
            != PROTOCOL_COMPONENT_PATHS[key]
            for key in sorted(PROTOCOL_COMPONENT_KEYS)
        ):
            mismatches.add(
                "PROTOCOL_COMPONENT_PATH_MISMATCH",
                "cache authority protocol-component path closure differs",
                CACHE_AUTHORITY_PATH,
            )
        generic_objects = _require_mapping(
            cache_authority["generic_object_identities"],
            "cache authority generic_object_identities",
        )
        _require_keys(
            generic_objects,
            GENERIC_OBJECT_KEYS,
            "cache authority generic_object_identities",
        )
        normalized_generic = {
            key: _identity_control(
                generic_objects[key], f"cache authority generic object {key}"
            )
            for key in sorted(GENERIC_OBJECT_KEYS)
        }
        if any(
            normalized_generic[key]["path"] != GENERIC_OBJECT_PATHS[key]
            for key in sorted(GENERIC_OBJECT_KEYS)
        ):
            mismatches.add(
                "GENERIC_OBJECT_PATH_MISMATCH",
                "cache authority generic-object path closure differs",
                CACHE_AUTHORITY_PATH,
            )
        if (
            normalized_generic["runtime_schema"]
            != control["authority"]["runtime_schema"]
            or normalized_generic["cache_static_closure"]
            != control["authority"]["cache_static_closure"]
        ):
            mismatches.add(
                "GENERIC_AUTHORITY_CROSSLINK_MISMATCH",
                "runtime/static object identity differs from cache authority",
                CACHE_AUTHORITY_PATH,
            )
        for key in sorted(PROTOCOL_COMPONENT_KEYS):
            _check_identity(
                root_fd,
                normalized_protocol_components[key],
                f"protocol component {key}",
                mismatches,
                ledger,
                fallback_commit=control["clone"]["expected_commit"],
            )
        for key in sorted(GENERIC_OBJECT_KEYS):
            _check_identity(
                root_fd,
                normalized_generic[key],
                f"generic object {key}",
                mismatches,
                ledger,
                fallback_commit=control["clone"]["expected_commit"],
            )

        authority_source_closure = _require_mapping(
            cache_authority["source_closure"],
            "cache authority source_closure",
        )
        _require_keys(
            authority_source_closure,
            AUTHORITY_SOURCE_CLOSURE_KEYS,
            "cache authority source_closure",
        )
        if (
            authority_source_closure["implementation_manifest_path"]
            != IMPLEMENTATION_MANIFEST_PATH
            or authority_source_closure["source_count"] != EXPECTED_SOURCE_COUNT
            or authority_source_closure["python_source_count"] != 10
            or authority_source_closure["native_source_count"] != 27
            or authority_source_closure["executable_unit_count"] != 38
            or authority_source_closure["source_tree_sha256"]
            != recomputed_source_tree
        ):
            mismatches.add(
                "AUTHORITY_SOURCE_SUMMARY_MISMATCH",
                "cache authority source-count/tree summary differs",
                CACHE_AUTHORITY_PATH,
            )
        if authority_source_closure["new_source_paths"] != [
            "script/a4_v2_cache_policy_verifier.py",
            "script/a4_v2_isolated_clone_prep.py",
        ]:
            mismatches.add(
                "NEW_SOURCE_ALLOWLIST_MISMATCH",
                "cache authority new-source allowlist differs",
                CACHE_AUTHORITY_PATH,
            )
        if authority_source_closure["changed_existing_source_paths"] != [
            "script/a4_v2_parity.py",
            "script/a4_v2_runner.py",
            "script/a4_v2_verifier.py",
            "script/run_arbitrary_cardinality_a4_v2.py",
        ]:
            mismatches.add(
                "CHANGED_SOURCE_ALLOWLIST_MISMATCH",
                "cache authority changed-source allowlist differs",
                CACHE_AUTHORITY_PATH,
            )
        if authority_source_closure["unchanged_python_source_paths"] != [
            "script/a4_v2_archive.py",
            "script/a4_v2_evidence.py",
            "script/a4_v2_producer.py",
            "script/a4_v2_producer_wire.py",
        ]:
            mismatches.add(
                "UNCHANGED_SOURCE_ALLOWLIST_MISMATCH",
                "cache authority unchanged-Python allowlist differs",
                CACHE_AUTHORITY_PATH,
            )
        raw_authority_sources = _require_list(
            authority_source_closure["source_files"],
            "cache authority source files",
            maximum=EXPECTED_SOURCE_COUNT,
        )
        if len(raw_authority_sources) != EXPECTED_SOURCE_COUNT:
            _defect("cache authority source inventory is not exactly 37")
        authority_sources: list[dict[str, Any]] = []
        previous_authority_path: bytes | None = None
        for index, raw_source in enumerate(raw_authority_sources):
            source = _require_mapping(raw_source, f"authority source {index}")
            _require_keys(source, SOURCE_KEYS, f"authority source {index}")
            path = _require_relative(source["path"], f"authority source {index} path")
            encoded_path = path.encode("utf-8")
            if previous_authority_path is not None and encoded_path <= previous_authority_path:
                _defect("cache authority source paths are not uniquely sorted")
            previous_authority_path = encoded_path
            authority_sources.append(
                {
                    "family": _require_text(
                        source["family"], f"authority source {index} family", maximum=128
                    ),
                    "git_blob": _require_oid(
                        source["git_blob"], f"authority source {index} Git blob"
                    ),
                    "path": path,
                    "role": _require_text(
                        source["role"], f"authority source {index} role", maximum=128
                    ),
                    "sha256": _require_sha256(
                        source["sha256"], f"authority source {index} SHA-256"
                    ),
                    "size_bytes": _require_int(
                        source["size_bytes"],
                        f"authority source {index} size",
                        maximum=(1 << 64) - 1,
                    ),
                }
            )
        if [
            {key: item[key] for key in MANIFEST_SOURCE_KEYS}
            for item in authority_sources
        ] != source_entries:
            mismatches.add(
                "AUTHORITY_MANIFEST_SOURCE_MISMATCH",
                "cache authority 37-source closure differs from manifest",
                CACHE_AUTHORITY_PATH,
            )
        authority_sources_by_path = {
            item["path"]: item for item in authority_sources
        }

        inline_source = _require_mapping(
            cache_authority["inline_executable_source"],
            "cache authority inline executable source",
        )
        _require_keys(
            inline_source,
            INLINE_SOURCE_KEYS,
            "cache authority inline executable source",
        )
        if inline_source["id"] != "a4_v2_prep_c_bootstrap" or inline_source["encoding"] != "ASCII":
            mismatches.add(
                "INLINE_SOURCE_HEADER_MISMATCH",
                "inline PREP bootstrap id/encoding differs",
                CACHE_AUTHORITY_PATH,
            )
        inline_text = _require_text(
            inline_source["source"],
            "inline PREP bootstrap source",
            maximum=MAX_STRING_BYTES,
            ascii_only=True,
        )
        inline_bytes = inline_text.encode("ascii")
        inline_size = _require_int(
            inline_source["size_bytes"],
            "inline PREP bootstrap size",
            maximum=(1 << 64) - 1,
        )
        prologue_size = _require_int(
            inline_source["prologue_size_bytes"],
            "inline PREP bootstrap prologue size",
            maximum=inline_size,
        )
        if (
            inline_size != len(inline_bytes)
            or inline_source["sha256"] != hashlib.sha256(inline_bytes).hexdigest()
            or prologue_size <= 0
            or inline_source["prologue_sha256"]
            != hashlib.sha256(inline_bytes[:prologue_size]).hexdigest()
        ):
            mismatches.add(
                "INLINE_SOURCE_IDENTITY_MISMATCH",
                "inline PREP bootstrap source/prologue identity differs",
                CACHE_AUTHORITY_PATH,
            )
        manifest_inline = _require_list(
            manifest["inline_executable_sources"],
            "manifest inline executable sources",
            maximum=1,
        )
        if len(manifest_inline) != 1 or manifest_inline[0] != dict(inline_source):
            mismatches.add(
                "MANIFEST_INLINE_SOURCE_CROSSLINK_MISMATCH",
                "implementation manifest inline bootstrap differs from authority",
                IMPLEMENTATION_MANIFEST_PATH,
            )

        runtime_policy = _require_mapping(
            cache_authority["runtime_policy"], "cache authority runtime_policy"
        )
        _require_keys(
            runtime_policy, RUNTIME_POLICY_KEYS, "cache authority runtime_policy"
        )
        if (
            runtime_policy["allowed_installed_origin_roots"]
            != list(INSTALLED_ORIGIN_ROOTS)
            or runtime_policy["parent_argv"]
            != [
                "python",
                "-B",
                "script/run_arbitrary_cardinality_a4_v2.py",
                "par",
                "docs/saq_a4_v2_par_artifacts_2026_07_14",
            ]
            or runtime_policy["parent_sys_argv"]
            != [
                "script/run_arbitrary_cardinality_a4_v2.py",
                "par",
                "docs/saq_a4_v2_par_artifacts_2026_07_14",
            ]
            or runtime_policy["thread_environment"]
            != {
                "MKL_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
            }
            or runtime_policy["cache_paths"] != list(CACHE_PATHS)
            or runtime_policy["control_max_bytes"] != MAX_CONTROL_BYTES
            or runtime_policy["output_artifact"] != OUTPUT_NAME
            or runtime_policy["output_max_bytes"] != MAX_OUTPUT_BYTES
            or runtime_policy["build_manifest_shape_version"] != 2
            or runtime_policy["artifact_index_shape_version"] != 2
            or runtime_policy["environment_preimage_field"]
            != "python_cache_policy"
            or runtime_policy["leader"]
            != {
                "path": "/usr/bin/python3.9",
                "sha256": CPYTHON_SHA256,
                "size_bytes": CPYTHON_SIZE,
            }
            or runtime_policy["bootstrap_external"]
            != {
                "path": BOOTSTRAP_EXTERNAL_PATH,
                "sha256": BOOTSTRAP_EXTERNAL_SHA256,
                "size_bytes": BOOTSTRAP_EXTERNAL_SIZE,
            }
            or runtime_policy["control_transport"]
            != {
                "descriptor": CONTROL_FD,
                "name": CONTROL_MEMFD_NAME,
                "offset_bytes": 0,
                "seals": [
                    "F_SEAL_SEAL",
                    "F_SEAL_SHRINK",
                    "F_SEAL_GROW",
                    "F_SEAL_WRITE",
                ],
                "transport": "SEALED_ANONYMOUS_MEMFD",
            }
            or runtime_policy["verifier_argv_template"]
            != [
                "/proc/self/fd/197",
                "-I",
                "-B",
                "-S",
                (
                    "/tmp/saq-a4-v2-par-r1-isolation/repo/script/"
                    "a4_v2_cache_policy_verifier.py"
                ),
                "verify-parent-cache-policy",
                "--control-fd",
                "198",
            ]
            or runtime_policy["verifier_environment"]
            != {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}
        ):
            mismatches.add(
                "RUNTIME_POLICY_CROSSLINK_MISMATCH",
                "cache authority runtime policy differs from verifier literals",
                CACHE_AUTHORITY_PATH,
            )

        binding = _require_mapping(
            _parse_canonical_document(
                authority_payloads["cache_prep_binding"], "CACHE-BIND object"
            ),
            "CACHE-BIND object",
        )
        _require_keys(binding, BINDING_KEYS, "CACHE-BIND object")
        binding_commits = {
            key: _require_oid(binding[key], f"CACHE-BIND {key}")
            for key in (
                "cache_i_target_commit",
                "cache_i_review_commit",
                "prep_authorization_target_commit",
                "prep_authorization_review_commit",
                "prep_execution_base_commit",
                "prep_receipt_target_commit",
                "prep_receipt_review_commit",
            )
        }
        binding_cache_protocol_identity = _identity_control(
            binding["cache_protocol_identity"],
            "CACHE-BIND cache protocol identity",
        )
        binding_source_manifest_identity = _identity_control(
            binding["source_manifest_identity"],
            "CACHE-BIND source manifest identity",
        )
        binding_seal_identity = _identity_control(
            binding["prep_seal_identity"], "CACHE-BIND PREP seal identity"
        )
        binding_token_identity = _identity_control(
            binding["prep_token_identity"], "CACHE-BIND PREP token identity"
        )
        binding_source_tree = _require_sha256(
            binding["source_tree_sha256"], "CACHE-BIND source tree"
        )
        if (
            binding.get("artifact_kind") != "a4_v2_cache_prep_binding"
            or binding.get("schema_version") != 1
            or binding_cache_protocol_identity
            != control["authority"]["cache_protocol_authority"]
            or binding_source_manifest_identity
            != control["authority"]["implementation_manifest"]
            or binding_source_tree
            != control["clone"]["source_tree_sha256"]
            or binding_seal_identity["path"]
            != (
                "docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15/"
                "prep_seal.json"
            )
            or binding_token_identity["path"]
            != "/rwproject/kdd-db/kluaq/saq/.git/saq-a4-v2-isolated-prep.lock"
        ):
            mismatches.add(
                "CACHE_BINDING_MISMATCH",
                "concrete CACHE-BIND object does not bind current source tree",
                CACHE_BINDING_PATH,
            )
        isolated = _require_mapping(
            binding["isolated_clone_identity"],
            "CACHE-BIND isolated clone identity",
        )
        isolated_keys = frozenset(
            {
                "clean_tree",
                "device_id",
                "forbidden_paths_absent",
                "git_common_dir",
                "git_object_count",
                "head_commit",
                "head_tree",
                "owner_uid",
                "root",
                "source_tree_sha256",
                "worktree_entry_count",
            }
        )
        _require_keys(isolated, isolated_keys, "CACHE-BIND isolated clone identity")
        isolated_head = _require_oid(
            isolated["head_commit"], "CACHE-BIND isolated clone HEAD"
        )
        isolated_tree = _require_oid(
            isolated["head_tree"], "CACHE-BIND isolated clone tree"
        )
        isolated_device = _require_int(
            isolated["device_id"],
            "CACHE-BIND isolated clone device",
            maximum=(1 << 64) - 1,
        )
        isolated_owner = _require_int(
            isolated["owner_uid"],
            "CACHE-BIND isolated clone owner",
            maximum=(1 << 64) - 1,
        )
        _require_int(
            isolated["git_object_count"],
            "CACHE-BIND isolated clone object count",
            minimum=1,
            maximum=(1 << 64) - 1,
        )
        _require_int(
            isolated["worktree_entry_count"],
            "CACHE-BIND isolated clone entry count",
            minimum=1,
            maximum=(1 << 64) - 1,
        )
        clone_metadata = os.fstat(root_fd)
        if (
            isolated.get("clean_tree") is not True
            or isolated.get("forbidden_paths_absent") is not True
            or isolated.get("git_common_dir") != CLONE_ROOT + "/.git"
            or isolated.get("root") != CLONE_ROOT
            or isolated.get("source_tree_sha256") != binding_source_tree
            or isolated_head != binding_commits["prep_receipt_review_commit"]
            or isolated_device != int(clone_metadata.st_dev)
            or isolated_owner != int(clone_metadata.st_uid)
        ):
            mismatches.add(
                "CACHE_BINDING_ISOLATED_CLONE_MISMATCH",
                "CACHE-BIND isolated-clone identity/history differs",
                CACHE_BINDING_PATH,
            )
        remote = _require_mapping(
            binding["remote_branch_identity"],
            "CACHE-BIND remote branch identity",
        )
        remote_keys = frozenset(
            {
                "branch",
                "fetch_url",
                "fresh_fetch_head",
                "local_head",
                "origin_tracking_head",
                "push_url",
                "ref",
                "remote_equal",
            }
        )
        _require_keys(remote, remote_keys, "CACHE-BIND remote branch identity")
        remote_heads = {
            key: _require_oid(remote[key], f"CACHE-BIND remote {key}")
            for key in (
                "fresh_fetch_head",
                "local_head",
                "origin_tracking_head",
            )
        }
        if (
            remote.get("branch") != BRANCH
            or remote.get("fetch_url") != FETCH_URL
            or remote.get("push_url") != PUSH_URL
            or remote.get("ref") != f"refs/heads/{BRANCH}"
            or remote.get("remote_equal") is not True
            or set(remote_heads.values())
            != {binding_commits["prep_receipt_review_commit"]}
        ):
            mismatches.add(
                "CACHE_BINDING_REMOTE_HISTORY_MISMATCH",
                "CACHE-BIND historical remote-equality record differs",
                CACHE_BINDING_PATH,
            )
        par_slot = _require_mapping(
            binding["par_r1_authorization_slot"],
            "CACHE-BIND PAR-R1 authorization slot",
        )
        if par_slot != {
            "commit": None,
            "path": "docs/saq_a4_v2_par_r1_authorization_2026_07_15.md",
            "sha256": None,
            "size_bytes": None,
            "status": "NOT_ISSUED",
        }:
            mismatches.add(
                "CACHE_BINDING_FUTURE_SLOT_MISMATCH",
                "CACHE-BIND must preserve its historically unissued PAR-R1 slot",
                CACHE_BINDING_PATH,
            )

        seal_payload, actual_seal_identity = _check_identity(
            root_fd,
            binding_seal_identity,
            "CACHE-BIND PREP seal",
            mismatches,
            ledger,
            fallback_commit=control["clone"]["expected_commit"],
        )
        seal = _require_mapping(
            _parse_canonical_document(seal_payload, "bound PREP seal"),
            "bound PREP seal",
        )
        seal_keys = frozenset(
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
        _require_keys(seal, seal_keys, "bound PREP seal")
        prep_execution_tree = _git_tree_oid(
            binding_commits["prep_execution_base_commit"],
            "PREP execution-base commit",
            mismatches,
            ledger,
        )
        if (
            actual_seal_identity != binding_seal_identity
            or seal.get("artifact_kind") != "a4_v2_isolated_clone_prep_seal"
            or seal.get("schema_version") != 1
            or seal.get("execution_base_commit")
            != binding_commits["prep_execution_base_commit"]
            or seal.get("execution_base_tree") != prep_execution_tree
            or seal.get("source_manifest_identity")
            != binding_source_manifest_identity
            or seal.get("source_tree_sha256") != binding_source_tree
            or seal.get("journal_copy_equal") is not True
            or seal.get("tail_duration") != "NOT_MEASURED_NOT_INTERPRETED"
            or seal.get("tail_rss") != "NOT_MEASURED_NOT_INTERPRETED"
        ):
            mismatches.add(
                "CACHE_BINDING_PREP_SEAL_MISMATCH",
                "bound PREP seal bytes/crosslinks differ",
                binding_seal_identity["path"],
            )

        token_payload, actual_token_identity = _read_absolute_identity_observation(
            binding_token_identity["path"],
            "CACHE-BIND PREP terminal token",
            maximum=MAX_AUTHORITY_BYTES,
        )
        if actual_token_identity is not None:
            ledger["filesystem_bytes_read"] += actual_token_identity["size_bytes"]
        token_matches = actual_token_identity == binding_token_identity
        if token_payload is not None:
            token_lines = token_payload.splitlines(keepends=True)
            if len(token_lines) == 2 and all(line.endswith(b"\n") for line in token_lines):
                token_start = _require_mapping(
                    _parse_canonical_document(token_lines[0], "PREP START token"),
                    "PREP START token",
                )
                token_terminal = _require_mapping(
                    _parse_canonical_document(
                        token_lines[1], "PREP TERMINAL token"
                    ),
                    "PREP TERMINAL token",
                )
                token_matches = token_matches and (
                    token_start.get("record_type") == "START"
                    and token_start.get("schema_version") == 1
                    and token_start.get("sequence") == 0
                    and token_terminal.get("record_type") == "TERMINAL"
                    and token_terminal.get("schema_version") == 1
                    and token_terminal.get("sequence") == 1
                    and token_terminal.get("previous_record_sha256")
                    == hashlib.sha256(token_lines[0]).hexdigest()
                    and token_terminal.get("status")
                    == "ISOLATED_CLONE_PREPARED_PENDING_COMMIT_REVIEW"
                    and token_terminal.get("receipt_seal_identity")
                    == binding_seal_identity
                )
            else:
                token_matches = False
        if not token_matches:
            mismatches.add(
                "CACHE_BINDING_PREP_TOKEN_MISMATCH",
                "bound PREP terminal token is absent or differs",
                binding_token_identity["path"],
            )

        historical_edges = (
            (
                binding_commits["cache_i_target_commit"],
                CACHE_I_IMPLEMENTATION_PARENT,
                CACHE_I_TARGET_CHANGED_PATHS,
                "CACHE-I implementation target",
            ),
            (
                binding_commits["cache_i_review_commit"],
                binding_commits["cache_i_target_commit"],
                CACHE_I_REVIEW_CHANGED_PATHS,
                "CACHE-I implementation review",
            ),
            (
                binding_commits["prep_authorization_target_commit"],
                binding_commits["cache_i_review_commit"],
                PREP_AUTHORIZATION_TARGET_CHANGED_PATHS,
                "PREP authorization target",
            ),
            (
                binding_commits["prep_authorization_review_commit"],
                binding_commits["prep_authorization_target_commit"],
                PREP_AUTHORIZATION_REVIEW_CHANGED_PATHS,
                "PREP authorization review",
            ),
            (
                binding_commits["prep_receipt_target_commit"],
                binding_commits["prep_execution_base_commit"],
                PREP_RECEIPT_TARGET_CHANGED_PATHS,
                "PREP receipt target",
            ),
            (
                binding_commits["prep_receipt_review_commit"],
                binding_commits["prep_receipt_target_commit"],
                PREP_RECEIPT_REVIEW_CHANGED_PATHS,
                "PREP receipt review",
            ),
        )
        if (
            binding_commits["prep_execution_base_commit"]
            != binding_commits["prep_authorization_review_commit"]
        ):
            mismatches.add(
                "PREP_EXECUTION_BASE_MISMATCH",
                "CACHE-BIND PREP execution base is not its authorization review",
                CACHE_BINDING_PATH,
            )
        for child, expected_parent, changed_paths, description in historical_edges:
            observed_parent = _git_direct_parent(
                child, description, mismatches, ledger
            )
            if observed_parent != expected_parent:
                mismatches.add(
                    "COMMIT_DIRECT_PARENT_MISMATCH",
                    f"{description} direct parent differs",
                )
            _git_changed_paths(
                child, changed_paths, description, mismatches, ledger
            )

        par_review_commit = control["clone"]["expected_commit"]
        par_target_commit = _git_direct_parent(
            par_review_commit, "PAR-R1 authorization review", mismatches, ledger
        )
        cache_bind_review_commit = (
            None
            if par_target_commit is None
            else _git_direct_parent(
                par_target_commit,
                "PAR-R1 authorization target",
                mismatches,
                ledger,
            )
        )
        cache_bind_target_commit = (
            None
            if cache_bind_review_commit is None
            else _git_direct_parent(
                cache_bind_review_commit,
                "CACHE-BIND review",
                mismatches,
                ledger,
            )
        )
        prep_review_parent = (
            None
            if cache_bind_target_commit is None
            else _git_direct_parent(
                cache_bind_target_commit,
                "CACHE-BIND target",
                mismatches,
                ledger,
            )
        )
        if prep_review_parent != binding_commits["prep_receipt_review_commit"]:
            mismatches.add(
                "CACHE_BINDING_CURRENT_DAG_MISMATCH",
                "CACHE-BIND/PAR-R1 chain does not descend by exact direct-parent edges",
                CACHE_BINDING_PATH,
            )
        later_commits = (
            (
                cache_bind_target_commit,
                CACHE_BIND_TARGET_CHANGED_PATHS,
                "CACHE-BIND target",
            ),
            (
                cache_bind_review_commit,
                CACHE_BIND_REVIEW_CHANGED_PATHS,
                "CACHE-BIND review",
            ),
            (
                par_target_commit,
                PAR_R1_AUTHORIZATION_TARGET_CHANGED_PATHS,
                "PAR-R1 authorization target",
            ),
            (
                par_review_commit,
                PAR_R1_AUTHORIZATION_REVIEW_CHANGED_PATHS,
                "PAR-R1 authorization review",
            ),
        )
        for commit, changed_paths, description in later_commits:
            if commit is not None:
                _git_changed_paths(
                    commit, changed_paths, description, mismatches, ledger
                )
        receipt_review_tree = _git_tree_oid(
            binding_commits["prep_receipt_review_commit"],
            "PREP receipt review",
            mismatches,
            ledger,
        )
        if isolated_tree != receipt_review_tree:
            mismatches.add(
                "CACHE_BINDING_HISTORICAL_TREE_MISMATCH",
                "CACHE-BIND isolated clone tree differs from PREP review tree",
                CACHE_BINDING_PATH,
            )

        static_closure = _require_mapping(
            _parse_canonical_document(
                authority_payloads["cache_static_closure"], "cache static closure"
            ),
            "cache static closure",
        )
        _require_keys(
            static_closure, STATIC_CLOSURE_KEYS, "cache static closure"
        )
        if (
            static_closure["artifact_kind"] != "a4_v2_cache_static_closure"
            or static_closure["schema_version"] != 1
            or static_closure["stage"] != "A4-V2-CACHE-I"
            or static_closure["cache_authority_path"] != CACHE_AUTHORITY_PATH
            or static_closure["implementation_manifest_path"]
            != IMPLEMENTATION_MANIFEST_PATH
            or static_closure["runtime_schema_path"] != RUNTIME_SCHEMA_PATH
            or static_closure["prep_binding_schema_path"]
            != "docs/saq_a4_v2_cache_prep_binding_schema_2026_07_15.json"
        ):
            mismatches.add(
                "STATIC_CLOSURE_HEADER_MISMATCH",
                "cache static closure header/path binding differs",
                STATIC_CLOSURE_PATH,
            )
        static_source_closure = _require_mapping(
            static_closure["source_closure"],
            "static closure source_closure",
        )
        if (
            static_source_closure.get("source_count") != EXPECTED_SOURCE_COUNT
            or static_source_closure.get("executable_unit_count") != 38
            or static_source_closure.get("source_tree_sha256")
            != recomputed_source_tree
            or static_source_closure.get("source_files") != authority_sources
        ):
            mismatches.add(
                "STATIC_SOURCE_CROSSLINK_MISMATCH",
                "static closure source summary differs from authority/manifest",
                STATIC_CLOSURE_PATH,
            )
        if static_closure["inline_executable_source"] != dict(inline_source):
            mismatches.add(
                "STATIC_INLINE_SOURCE_CROSSLINK_MISMATCH",
                "static closure inline source differs from cache authority",
                STATIC_CLOSURE_PATH,
            )
        executable_units = _require_list(
            static_closure["executable_units"],
            "static closure executable_units",
            maximum=38,
        )
        if len(executable_units) != 38:
            mismatches.add(
                "EXECUTABLE_UNIT_COUNT_MISMATCH",
                "static closure does not enumerate exactly 38 executable units",
                STATIC_CLOSURE_PATH,
            )

        reviewed_by_path = {
            item["path"]: item for item in control["reviewed_python_sources"]
        }
        tree_code, tree_stdout, tree_stderr = _run_git_observation(
            (
                "-C",
                CLONE_ROOT,
                "ls-tree",
                "-r",
                "-z",
                "--full-tree",
                control["clone"]["expected_commit"],
            ),
            "complete execution source tree",
        )
        ledger["git_stdout_bytes"] += len(tree_stdout)
        ledger["git_stderr_bytes"] += len(tree_stderr)
        if tree_code != 0 or tree_stderr:
            mismatches.add(
                "CURRENT_SOURCE_GIT_CLOSURE_UNAVAILABLE",
                "current commit tree is unavailable from Git",
            )
            git_tree = {}
        else:
            try:
                git_tree = _parse_full_git_tree(tree_stdout)
            except VerifierDefect:
                mismatches.add(
                    "CURRENT_SOURCE_GIT_CLOSURE_UNAVAILABLE",
                    "current commit tree is not a valid complete Git tree",
                )
                git_tree = {}
        history_commits = [
            binding_commits["cache_i_target_commit"],
            binding_commits["cache_i_review_commit"],
            binding_commits["prep_authorization_target_commit"],
            binding_commits["prep_authorization_review_commit"],
            binding_commits["prep_receipt_target_commit"],
            binding_commits["prep_receipt_review_commit"],
            cache_bind_target_commit,
            cache_bind_review_commit,
            par_target_commit,
            par_review_commit,
        ]
        expected_source_blobs = {
            path: item["git_blob"] for path, item in authority_sources_by_path.items()
        }
        if any(
            git_tree.get(path, {}).get("git_blob") != blob
            or git_tree.get(path, {}).get("kind") != "blob"
            for path, blob in expected_source_blobs.items()
        ):
            mismatches.add(
                "CURRENT_SOURCE_GIT_CLOSURE_MISMATCH",
                "current commit does not retain the reviewed 37-source blobs",
            )
        for commit in history_commits:
            if commit is None:
                continue
            code, history_stdout, history_stderr = _run_git_observation(
                (
                    "-C",
                    CLONE_ROOT,
                    "ls-tree",
                    "-r",
                    "-z",
                    "--full-tree",
                    commit,
                ),
                f"37-source history {commit}",
            )
            ledger["git_stdout_bytes"] += len(history_stdout)
            ledger["git_stderr_bytes"] += len(history_stderr)
            if code != 0 or history_stderr:
                mismatches.add(
                    "SOURCE_HISTORY_UNAVAILABLE",
                    "a registered source-history commit is unavailable",
                )
                continue
            history_tree = _parse_full_git_tree(history_stdout)
            if any(
                history_tree.get(path, {}).get("git_blob") != blob
                or history_tree.get(path, {}).get("kind") != "blob"
                for path, blob in expected_source_blobs.items()
            ):
                mismatches.add(
                    "SOURCE_HISTORY_MISMATCH",
                    "a registered commit changed the reviewed 37-source closure",
                )
        source_checks: list[dict[str, Any]] = []
        for source in source_entries:
            try:
                payload, actual = _observe_relative_regular(
                    root_fd,
                    source["path"],
                    maximum=MAX_SOURCE_BYTES,
                    description=f"reviewed source {source['path']}",
                )
            except (OSError, VerifierDefect, ValueError):
                payload = None
                actual = {
                    "path": source["path"],
                    "sha256": "0" * 64,
                    "size_bytes": 0,
                }
                mismatches.add(
                    "REVIEWED_SOURCE_PHYSICAL_UNAVAILABLE",
                    "reviewed physical source is absent or unclassifiable",
                    source["path"],
                )
            if payload is not None:
                ledger["filesystem_bytes_read"] += len(payload)
            physical_matches = (
                payload is not None
                and actual["sha256"] == source["sha256"]
                and actual["size_bytes"] == source["size_bytes"]
            )
            tree_entry = git_tree.get(source["path"])
            git_blob = (
                "0" * 40 if tree_entry is None else tree_entry["git_blob"]
            )
            git_matches = False
            if tree_entry is None or tree_entry["kind"] != "blob":
                mismatches.add(
                    "REVIEWED_SOURCE_GIT_NONBLOB",
                    "reviewed source is absent or nonblob in the admitted Git tree",
                    source["path"],
                )
            else:
                git_code, git_stdout, git_stderr = _run_git_observation(
                    (
                        "-C",
                        CLONE_ROOT,
                        "show",
                        f"{control['clone']['expected_commit']}:{source['path']}",
                    ),
                    f"source blob {source['path']}",
                )
                ledger["git_stdout_bytes"] += len(git_stdout)
                ledger["git_stderr_bytes"] += len(git_stderr)
                git_matches = (
                    git_code == 0
                    and not git_stderr
                    and hashlib.sha256(git_stdout).hexdigest() == source["sha256"]
                    and len(git_stdout) == source["size_bytes"]
                )
            expected_python = reviewed_by_path.get(source["path"])
            blob_matches = expected_python is None or (
                git_blob == expected_python["git_blob"]
            )
            if not physical_matches or not git_matches or not blob_matches:
                mismatches.add(
                    "REVIEWED_SOURCE_MISMATCH",
                    "physical/Git/reviewed source identity differs",
                    source["path"],
                )
            source_checks.append(
                {
                    "git_blob": git_blob,
                    "git_matches": git_matches and blob_matches,
                    "path": source["path"],
                    "physical_matches": physical_matches,
                    "sha256": actual["sha256"],
                    "size_bytes": actual["size_bytes"],
                }
            )

        cache_checks: list[dict[str, str]] = []
        for relative in CACHE_PATHS:
            raw_state = _check_cache_absence(root_fd, relative)
            state = (
                "ABSENT"
                if raw_state == "ABSENT"
                else "PRESENT_OR_UNCLASSIFIABLE"
            )
            cache_checks.append(
                {"checkpoint": "VERIFIER_LIVE_P", "path": relative, "state": state}
            )
            if state != "ABSENT":
                mismatches.add(
                    "CACHE_PATH_NOT_ABSENT",
                    f"live verifier cache path is present/unclassifiable ({raw_state})",
                    relative,
                )

        module_checks = [
            _check_observation(
                control["startup_observation"],
                control["clone"],
                reviewed_by_path,
                mismatches,
            ),
            *[
                _check_observation(
                    item,
                    control["clone"],
                    reviewed_by_path,
                    mismatches,
                )
                for item in control["preterminal_observations"]
            ],
        ]

        parent_pid = control["parent"]["pid"]
        parent_start = _proc_start_time(parent_pid)
        parent_cmdline = _proc_bytes(parent_pid, "cmdline", MAX_CMDLINE_BYTES)
        parent_cwd = _proc_symlink(parent_pid, "cwd")
        expected_parent_leader = control["parent"]["leader"]
        parent_command_observed = _observe_leader_path(
            expected_parent_leader["command"]["path"],
            "followed captured parent python command",
        )
        parent_proc_exe_path = f"/proc/{parent_pid}/exe"
        parent_proc_exe_observed = _observe_leader_path(
            parent_proc_exe_path, "parent executing image"
        )
        for observed in (parent_command_observed, parent_proc_exe_observed):
            if observed is not None:
                ledger["filesystem_bytes_read"] += observed["size_bytes"]
        parent_leader_available = (
            parent_command_observed is not None
            and parent_proc_exe_observed is not None
        )
        parent_leader_matches = parent_leader_available and (
            parent_command_observed == expected_parent_leader["command"]
            and _leader_core(parent_proc_exe_observed)
            == _leader_core(expected_parent_leader["proc_self_exe"])
            and _leader_core(parent_command_observed)
            == _leader_core(parent_proc_exe_observed)
            and parent_proc_exe_observed["path"] == parent_proc_exe_path
        )
        parent_leader_status = (
            "UNAVAILABLE"
            if not parent_leader_available
            else "MATCH"
            if parent_leader_matches
            else "MISMATCH"
        )
        if parent_leader_status != "MATCH":
            mismatches.add(
                "PARENT_LEADER_IDENTITY_MISMATCH",
                "live parent image and captured python command differ from pinned leader",
                expected_parent_leader["command"]["path"],
            )
        parent_environment_observed = _observe_parent_environment(parent_pid)
        expected_parent_environment = control["parent"]["environment"]
        parent_environment_status = _identity_check_status(
            parent_environment_observed, expected_parent_environment
        )
        if parent_environment_status != "MATCH":
            mismatches.add(
                "PARENT_ENVIRONMENT_MISMATCH",
                "live parent Python/thread environment differs or is unavailable",
            )
        if parent_start != control["parent"]["start_time_clock_ticks"]:
            mismatches.add(
                "PARENT_START_IDENTITY_MISMATCH",
                "live parent start-time identity differs",
            )
        if (
            parent_cmdline.hex() != control["parent"]["cmdline_hex"]
            or hashlib.sha256(parent_cmdline).hexdigest()
            != control["parent"]["cmdline_sha256"]
        ):
            mismatches.add(
                "PARENT_CMDLINE_IDENTITY_MISMATCH",
                "live parent cmdline differs from serialized identity",
            )
        if parent_cwd != CLONE_ROOT:
            mismatches.add(
                "PARENT_CWD_MISMATCH",
                "live parent cwd differs from isolated clone",
                parent_cwd,
            )
        expected_parent_argv = [
            "python",
            "-B",
            "script/run_arbitrary_cardinality_a4_v2.py",
            "par",
            "docs/saq_a4_v2_par_artifacts_2026_07_14",
        ]
        if _decode_cmdline(parent_cmdline, "parent cmdline") != expected_parent_argv:
            mismatches.add(
                "PARENT_ARGV_MISMATCH",
                "live parent argv differs from frozen PAR-R1 command",
            )

        head_observed = _git_scalar_observation(
            ("-C", CLONE_ROOT, "rev-parse", "HEAD"),
            "clone HEAD",
            git_oid=True,
            mismatches=mismatches,
            ledger=ledger,
        )
        tree_observed = _git_scalar_observation(
            ("-C", CLONE_ROOT, "rev-parse", "HEAD^{tree}"),
            "clone tree",
            git_oid=True,
            mismatches=mismatches,
            ledger=ledger,
        )
        symbol_observed = _git_scalar_observation(
            ("-C", CLONE_ROOT, "symbolic-ref", "-q", "HEAD"),
            "clone symbolic HEAD",
            git_oid=False,
            mismatches=mismatches,
            ledger=ledger,
        )
        fetch_observed = _git_scalar_observation(
            ("-C", CLONE_ROOT, "remote", "get-url", "origin"),
            "clone fetch URL",
            git_oid=False,
            mismatches=mismatches,
            ledger=ledger,
        )
        push_observed = _git_scalar_observation(
            ("-C", CLONE_ROOT, "remote", "get-url", "--push", "origin"),
            "clone push URL",
            git_oid=False,
            mismatches=mismatches,
            ledger=ledger,
        )
        tracking_observed = _git_scalar_observation(
            (
                "-C",
                CLONE_ROOT,
                "rev-parse",
                f"refs/remotes/origin/{BRANCH}",
            ),
            "clone origin-tracking HEAD",
            git_oid=True,
            mismatches=mismatches,
            ledger=ledger,
        )
        clone_observed = {
            "branch_ref": symbol_observed,
            "fetch_url": fetch_observed,
            "head": head_observed,
            "push_url": push_observed,
            "tree": tree_observed,
        }
        clone_expected = {
            "branch_ref": f"refs/heads/{BRANCH}",
            "fetch_url": FETCH_URL,
            "head": control["clone"]["expected_commit"],
            "push_url": PUSH_URL,
            "tree": control["clone"]["expected_tree_oid"],
        }
        if clone_observed != clone_expected:
            mismatches.add(
                "CLONE_GIT_IDENTITY_MISMATCH",
                "live clone HEAD/tree/branch/URL closure differs",
                CLONE_ROOT,
            )
        if tracking_observed != control["clone"]["expected_commit"]:
            mismatches.add(
                "CLONE_ORIGIN_TRACKING_MISMATCH",
                "origin-tracking branch does not equal the admitted PAR head",
                CLONE_ROOT,
            )

        end_self_usage = resource.getrusage(resource.RUSAGE_SELF)
        end_children_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        stop_wall = time.monotonic_ns()
        cpu_microseconds = int(
            (
                (end_self_usage.ru_utime - start_self_usage.ru_utime)
                + (end_self_usage.ru_stime - start_self_usage.ru_stime)
                + (end_children_usage.ru_utime - start_children_usage.ru_utime)
                + (end_children_usage.ru_stime - start_children_usage.ru_stime)
            )
            * 1_000_000
        )
        if cpu_microseconds < 0 or stop_wall < start_wall:
            _defect("verifier diagnostic timer is nonmonotonic")
        ledger.update(
            {
                "cpu_microseconds": cpu_microseconds,
                "maximum_rss_bytes": max(
                    int(end_self_usage.ru_maxrss),
                    int(end_children_usage.ru_maxrss),
                    0,
                )
                * 1024,
                "measurement_scope": "DIAGNOSTIC_PARENT_P_LEDGER_AUTHORITATIVE",
                "wall_nanoseconds": stop_wall - start_wall,
            }
        )
        return {
            "artifact_kind": "a4_v2_cache_policy_verification",
            "authority_checks": authority_checks,
            "cache_checks": cache_checks,
            "claim_ceiling": (
                "Cooperative isolated-clone B/P cache-policy evidence only; no "
                "malicious-writer, SRUN-child, parity, feasibility, systems, or "
                "scientific claim."
            ),
            "clone_checks": {
                "expected": clone_expected,
                "observed": clone_observed,
                "status": "MATCH" if clone_observed == clone_expected else "MISMATCH",
            },
            "control_identity": {
                "name": CONTROL_MEMFD_NAME,
                "offset_bytes": 0,
                "seals": [
                    "F_SEAL_SEAL",
                    "F_SEAL_SHRINK",
                    "F_SEAL_GROW",
                    "F_SEAL_WRITE",
                ],
                "sha256": hashlib.sha256(control_payload).hexdigest(),
                "size_bytes": len(control_payload),
                "transport": "SEALED_ANONYMOUS_MEMFD",
            },
            "control_preimage_hex": control_payload.hex(),
            "mismatches": mismatches.items,
            "module_checks": module_checks,
            "parent_checks": {
                "bootstrap_external_check": {
                    "expected": expected_bootstrap,
                    "observed": bootstrap_observed,
                    "status": bootstrap_status,
                },
                "cmdline_hex": parent_cmdline.hex(),
                "cmdline_sha256": hashlib.sha256(parent_cmdline).hexdigest(),
                "cwd": parent_cwd,
                "environment_check": {
                    "expected": expected_parent_environment,
                    "observed": parent_environment_observed,
                    "status": parent_environment_status,
                },
                "leader_check": {
                    "command_observed": parent_command_observed,
                    "expected": expected_parent_leader,
                    "proc_exe_observed": parent_proc_exe_observed,
                    "status": parent_leader_status,
                },
                "pid": parent_pid,
                "start_time_clock_ticks": parent_start,
            },
            "resource_ledger": ledger,
            "schema_version": SCHEMA_VERSION,
            "source_checks": source_checks,
            "status": "PASS" if not mismatches.items else "MISMATCH",
            "verifier_process": verifier_process,
        }
    finally:
        os.close(root_fd)


def _write_output(control: Mapping[str, Any], value: Mapping[str, Any]) -> None:
    payload = _canonical_result_document(value)
    if len(payload) > control["output"]["maximum_bytes"]:
        _defect("cache-policy artifact exceeds exact output cap")
    root_fd = _open_absolute_dir_nofollow(CLONE_ROOT)
    try:
        staging_fd = _open_relative_dir_nofollow(
            root_fd, control["output"]["staging_relative_path"]
        )
        try:
            descriptor = os.open(
                control["output"]["artifact_name"],
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                0o600,
                dir_fd=staging_fd,
            )
            try:
                offset = 0
                while offset < len(payload):
                    written = os.write(descriptor, payload[offset:])
                    if written <= 0:
                        _defect("cache-policy artifact write made no progress")
                    offset += written
                os.fsync(descriptor)
                metadata = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or stat.S_IMODE(metadata.st_mode) != 0o600
                    or metadata.st_size != len(payload)
                ):
                    _defect("cache-policy artifact mode/size differs after write")
            finally:
                os.close(descriptor)
            os.fsync(staging_fd)
        finally:
            os.close(staging_fd)
    finally:
        os.close(root_fd)


def _main(argv: Sequence[str]) -> int:
    if list(argv) != ["verify-parent-cache-policy", "--control-fd", "198"]:
        _defect("cache verifier CLI differs from exact PAR-only surface")
    control_payload = _read_control_memfd()
    control = _validate_control(
        _parse_canonical_document(control_payload, "cache verifier control")
    )
    result = _verify(control, control_payload)
    _write_output(control, result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main(sys.argv[1:]))
    except VerifierDefect as error:
        message = f"A4-V2 cache verifier implementation failure: {error}\n".encode(
            "utf-8", errors="backslashreplace"
        )
        try:
            os.write(2, message[:4_096])
        except OSError:
            pass
        raise SystemExit(70)
    except (OSError, MemoryError, TimeoutError) as error:
        message = (
            "A4-V2 cache verifier resource failure: "
            f"{type(error).__name__}\n"
        ).encode("ascii", errors="strict")
        try:
            os.write(2, message[:4_096])
        except OSError:
            pass
        raise SystemExit(CACHE_VERIFIER_RESOURCE_EXIT)
