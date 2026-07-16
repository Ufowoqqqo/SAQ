#!/usr/bin/env python3
"""Bootstrap for the separately authorized A4-V2-SRUN command.

The present A4-V2-I stage authorizes this source file, not its execution.
Only minimal Linux integer-clock machinery is imported before the immutable
start snapshots.  All protocol, producer, native, evidence, and NumPy-capable
modules are imported afterward.
"""

from __future__ import annotations

import ctypes
import os
import time


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


def _integer_family_cpu_microseconds() -> int:
    total = 0
    for who in (0, -1):  # Linux RUSAGE_SELF and RUSAGE_CHILDREN.
        usage = _Rusage()
        if _GETRUSAGE(who, ctypes.byref(usage)) != 0:
            number = ctypes.get_errno()
            raise OSError(number, os.strerror(number))
        for value in (
            usage.ru_utime,
            usage.ru_stime,
        ):
            if not 0 <= value.tv_usec < 1_000_000:
                raise RuntimeError("getrusage returned a noncanonical timeval")
            total += int(value.tv_sec) * 1_000_000 + int(value.tv_usec)
    return total


# These are the first authority-bearing observations.  Argument parsing,
# protocol imports, filesystem checks, and scientific imports occur below.
_START_CPU_MICROSECONDS = _integer_family_cpu_microseconds()
_START_WALL_NANOSECONDS = time.monotonic_ns()


import sys as _sys  # noqa: E402  (builtin, post-snapshot governance)


def _write_bootstrap_status(status: str, detail: str) -> None:
    payload = f"{status}: {detail}".encode("utf-8", errors="backslashreplace")
    os.write(2, payload[:4095] + b"\n")


_PAR_MODE_REQUESTED = len(_sys.argv) >= 2 and _sys.argv[1] == "par"
if _PAR_MODE_REQUESTED:
    try:
        import hashlib as _hashlib  # noqa: E402  (charged PAR governance)
        import stat as _stat  # noqa: E402  (charged PAR governance)
    except MemoryError as _governance_resource_error:
        _write_bootstrap_status(
            "RESOURCE_INCOMPLETE_NO_DECISION",
            f"cache-governance import resource failure: {_governance_resource_error}",
        )
        raise SystemExit(3)
    except (ImportError, OSError, RuntimeError, SyntaxError, TypeError, ValueError) as _governance_import_error:
        _write_bootstrap_status(
            "IMPLEMENTATION_INVALID",
            f"cache-governance import failure: {_governance_import_error}",
        )
        raise SystemExit(3)


_EXPECTED_PAR_RAW_ARGV = (
    b"python",
    b"-B",
    b"script/run_arbitrary_cardinality_a4_v2.py",
    b"par",
    b"docs/saq_a4_v2_par_artifacts_2026_07_14",
)
_EXPECTED_PAR_SYS_ARGV = [item.decode("ascii") for item in _EXPECTED_PAR_RAW_ARGV[2:]]
_EXPECTED_THREAD_ENVIRONMENT = {
    "MKL_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
}
_EXPECTED_CACHE_TAG = "cpython-39"
_EXPECTED_LEADER_SHA256 = "c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0"
_EXPECTED_LEADER_SIZE_BYTES = 15_448
_BOOTSTRAP_EXTERNAL_PATH = "/usr/lib64/python3.9/importlib/_bootstrap_external.py"
_EXPECTED_BOOTSTRAP_SHA256 = "8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4"
_EXPECTED_BOOTSTRAP_SIZE_BYTES = 66_447
_OLD_WORKTREE = "/tmp/saq-arbitrary-cardinality-feasibility-v2"
_ALLOWED_INSTALLED_ORIGIN_ROOTS = (
    "/usr/lib/python3.9",
    "/usr/lib64/python3.9",
    "/usr/lib64/python39.zip",
    "/usr/local/lib/python3.9/site-packages",
    "/usr/local/lib64/python3.9/site-packages",
)
_CACHE_RELATIVE_PATHS = (
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
_STARTUP_MODULE_LIMIT = 4_096
_SYS_PATH_LIMIT = 128
_META_PATH_LIMIT = 64


def _sha256(payload: bytes) -> str:
    return _hashlib.sha256(payload).hexdigest()


def _read_bounded(descriptor: int, maximum_bytes: int, description: str) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = os.read(descriptor, min(65_536, maximum_bytes + 1 - size))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size > maximum_bytes:
            raise RuntimeError(f"{description} exceeds its frozen byte bound")


def _regular_file_identity(path: str, maximum_bytes: int) -> dict[str, object]:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if not _stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"cache-policy identity is not regular: {path}")
        payload = _read_bounded(descriptor, maximum_bytes, path)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or len(payload) != before.st_size
    ):
        raise RuntimeError(f"cache-policy identity changed while read: {path}")
    return {
        "device": int(before.st_dev),
        "inode": int(before.st_ino),
        "mode": int(before.st_mode),
        "path": path,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _followed_file_identity(path: str, maximum_bytes: int) -> dict[str, object]:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    try:
        before = os.fstat(descriptor)
        if not _stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"followed cache-policy identity is not regular: {path}")
        payload = _read_bounded(descriptor, maximum_bytes, path)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or len(payload) != before.st_size
    ):
        raise RuntimeError(f"followed cache-policy identity changed while read: {path}")
    return {
        "device": int(before.st_dev),
        "inode": int(before.st_ino),
        "mode": int(before.st_mode),
        "path": path,
        "resolved_path": os.path.realpath(path),
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _raw_proc_cmdline() -> tuple[bytes, list[bytes]]:
    descriptor = os.open(
        "/proc/self/cmdline",
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        payload = _read_bounded(descriptor, 16_384, "/proc/self/cmdline")
    finally:
        os.close(descriptor)
    if not payload or not payload.endswith(b"\0") or payload.endswith(b"\0\0"):
        raise RuntimeError("raw parent cmdline lacks exactly one terminal NUL")
    fields = payload[:-1].split(b"\0")
    if not fields or any(not item for item in fields):
        raise RuntimeError("raw parent cmdline contains an empty argument")
    return payload, fields


def _python_command_path(raw_argv0: bytes) -> str:
    try:
        name = raw_argv0.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise RuntimeError("parent argv[0] is not UTF-8") from error
    if "/" in name:
        candidate = name if os.path.isabs(name) else os.path.join(os.getcwd(), name)
        return os.path.normpath(candidate)
    for directory in os.environ.get("PATH", os.defpath).split(os.pathsep):
        base = directory or os.getcwd()
        candidate = os.path.join(base, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.normpath(candidate)
    raise RuntimeError("parent python command cannot be resolved through PATH")


def _bounded_string(value: object, description: str, maximum: int = 512) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or any(ord(character) < 32 or ord(character) > 126 for character in value)
    ):
        raise RuntimeError(f"{description} is not bounded printable ASCII")
    return value


def _sys_path_records() -> list[str]:
    if len(_sys.path) > _SYS_PATH_LIMIT:
        raise RuntimeError("sys.path exceeds its frozen count bound")
    return [_bounded_string(item, "sys.path entry") for item in _sys.path]


def _meta_path_records() -> list[dict[str, object]]:
    if len(_sys.meta_path) > _META_PATH_LIMIT:
        raise RuntimeError("sys.meta_path exceeds its frozen count bound")
    records = []
    for index, finder in enumerate(_sys.meta_path):
        finder_type = type(finder)
        module_name = _bounded_string(finder_type.__module__, "meta_path type module")
        module = _sys.modules.get(module_name)
        specification = getattr(module, "__spec__", None)
        origin = getattr(specification, "origin", None)
        records.append(
            {
                "origin": (
                    None
                    if origin is None
                    else _bounded_string(origin, "meta_path type origin")
                ),
                "type": _bounded_string(
                    f"{module_name}.{finder_type.__qualname__}",
                    f"meta_path type {index}",
                ),
            }
        )
    return records


def _loader_type(loader: object) -> str:
    loader_type = type(loader)
    return _bounded_string(
        f"{loader_type.__module__}.{loader_type.__qualname__}", "module loader type"
    )


def _retained_module_records(
    retained_names: tuple[str, ...] | None = None,
) -> list[dict[str, object]]:
    names = (
        tuple(sorted(_sys.modules, key=lambda value: value.encode("utf-8")))
        if retained_names is None
        else retained_names
    )
    if len(names) > _STARTUP_MODULE_LIMIT:
        raise RuntimeError("retained startup modules exceed their frozen count bound")
    records = []
    for name in names:
        module = _sys.modules.get(name)
        if module is None:
            raise RuntimeError(f"retained startup module disappeared: {name}")
        specification = getattr(module, "__spec__", None)
        origin = getattr(specification, "origin", None)
        file_name = getattr(module, "__file__", None)
        cached = getattr(module, "__cached__", None)
        if name == "__main__":
            main_path = os.path.abspath(str(file_name))
            file_name = main_path
            origin = main_path
        records.append(
            {
                "cached": (
                    None
                    if cached is None
                    else _bounded_string(cached, "startup module __cached__")
                ),
                "file": (
                    None
                    if file_name is None
                    else _bounded_string(file_name, "startup module __file__")
                ),
                "loader_type": _loader_type(getattr(module, "__loader__", None)),
                "name": _bounded_string(name, "startup module name", 256),
                "origin": (
                    None
                    if origin is None
                    else _bounded_string(origin, "startup module origin")
                ),
            }
        )
    return records


def _cache_path_observation(repository_root: str) -> list[dict[str, str]]:
    root_descriptor = os.open(
        repository_root,
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    records = []
    try:
        for relative in _CACHE_RELATIVE_PATHS:
            components = relative.split("/")
            parent_descriptor = os.dup(root_descriptor)
            try:
                for component in components[:-1]:
                    next_descriptor = os.open(
                        component,
                        os.O_RDONLY
                        | getattr(os, "O_CLOEXEC", 0)
                        | getattr(os, "O_DIRECTORY", 0)
                        | getattr(os, "O_NOFOLLOW", 0),
                        dir_fd=parent_descriptor,
                    )
                    os.close(parent_descriptor)
                    parent_descriptor = next_descriptor
                try:
                    os.stat(
                        components[-1],
                        dir_fd=parent_descriptor,
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    records.append({"path": relative, "state": "ABSENT"})
                except OSError as error:
                    raise RuntimeError(
                        f"cache path is unclassifiable: {relative}: errno={error.errno}"
                    ) from error
                else:
                    raise RuntimeError(
                        f"cache or adjacent legacy path is present: {relative}"
                    )
            except OSError as error:
                raise RuntimeError(
                    f"cache path parent is unclassifiable: {relative}: errno={error.errno}"
                ) from error
            finally:
                os.close(parent_descriptor)
    finally:
        os.close(root_descriptor)
    return records


def _module_records(
    repository_root: str, reviewed_sources: object | None
) -> list[dict[str, object]]:
    if reviewed_sources is None:
        return []
    if not isinstance(reviewed_sources, dict):
        raise RuntimeError("reviewed Python source map is malformed")
    reviewed_names = {}
    for relative in reviewed_sources:
        if not isinstance(relative, str) or not relative.startswith("script/"):
            raise RuntimeError("reviewed Python source path is malformed")
        name = (
            "__main__"
            if relative == "script/run_arbitrary_cardinality_a4_v2.py"
            else relative.removeprefix("script/").removesuffix(".py")
        )
        if name.startswith("a4_v2_") or name == "__main__":
            reviewed_names[name] = relative
    expected = {
        name: relative
        for name, relative in reviewed_names.items()
        if name in _sys.modules
    }
    if len(expected) > 10:
        raise RuntimeError("loaded A4 module inventory exceeds its frozen count")
    repository_real = os.path.realpath(repository_root)
    installed_reals = tuple(
        os.path.realpath(path) for path in _ALLOWED_INSTALLED_ORIGIN_ROOTS
    )
    for module_name, module in sorted(
        _sys.modules.items(), key=lambda item: item[0].encode("utf-8")
    ):
        if module is None:
            continue
        specification = getattr(module, "__spec__", None)
        fields = {
            "cached": getattr(module, "__cached__", None),
            "file": getattr(module, "__file__", None),
            "origin": getattr(specification, "origin", None),
        }
        reviewed_relative = reviewed_names.get(module_name)
        reviewed_source = (
            None
            if reviewed_relative is None
            else os.path.realpath(os.path.join(repository_root, reviewed_relative))
        )
        reviewed_cache = (
            None
            if reviewed_relative is None
            else os.path.realpath(
                os.path.join(
                    repository_root,
                    "script",
                    "__pycache__",
                    reviewed_relative.removeprefix("script/").removesuffix(".py")
                    + f".{_EXPECTED_CACHE_TAG}.pyc",
                )
            )
        )
        for field, raw_path in fields.items():
            if not isinstance(raw_path, str) or raw_path in {
                "built-in",
                "frozen",
            }:
                continue
            normalized = os.path.realpath(
                raw_path
                if os.path.isabs(raw_path)
                else os.path.join(repository_root, raw_path)
            )
            if _OLD_WORKTREE in normalized:
                raise RuntimeError(
                    f"loaded module names the quarantined worktree: {module_name}"
                )
            if normalized == repository_real or normalized.startswith(
                repository_real + os.sep
            ):
                expected_path = reviewed_cache if field == "cached" else reviewed_source
                if expected_path is None or normalized != expected_path:
                    raise RuntimeError(
                        f"unreviewed clone-local module {field}: {module_name}"
                    )
            elif not any(
                normalized == root or normalized.startswith(root + os.sep)
                for root in installed_reals
            ):
                raise RuntimeError(
                    f"loaded module {field} is outside frozen roots: {module_name}"
                )
    records = []
    for name, relative in sorted(expected.items(), key=lambda item: item[0].encode("utf-8")):
        module = _sys.modules.get(name)
        if module is None:
            if name == "__main__":
                raise RuntimeError("reviewed entrypoint is absent from sys.modules")
            continue
        expected_path = os.path.join(repository_root, relative)
        file_name = getattr(module, "__file__", None)
        if not isinstance(file_name, str):
            raise RuntimeError(f"reviewed module has no source file: {name}")
        observed_path = os.path.normpath(
            file_name if os.path.isabs(file_name) else os.path.join(repository_root, file_name)
        )
        if os.path.realpath(observed_path) != os.path.realpath(expected_path):
            raise RuntimeError(f"reviewed module source origin changed: {name}")
        specification = getattr(module, "__spec__", None)
        origin = getattr(specification, "origin", None)
        if name == "__main__":
            origin = observed_path
        if name != "__main__" and (
            not isinstance(origin, str)
            or os.path.realpath(origin) != os.path.realpath(expected_path)
        ):
            raise RuntimeError(f"reviewed module spec origin changed: {name}")
        loader = getattr(module, "__loader__", None)
        cached = getattr(module, "__cached__", None)
        expected_cache_relative = os.path.join(
            "script",
            "__pycache__",
            (
                "run_arbitrary_cardinality_a4_v2"
                if name == "__main__"
                else name
            )
            + f".{_EXPECTED_CACHE_TAG}.pyc",
        )
        identity = _regular_file_identity(expected_path, 16 << 20)
        if reviewed_sources is not None:
            reviewed = reviewed_sources.get(relative)
            if not isinstance(reviewed, dict) or (
                identity["sha256"] != reviewed.get("sha256")
                or identity["size_bytes"] != reviewed.get("size_bytes")
            ):
                raise RuntimeError(f"reviewed module blob changed: {name}")
        records.append(
            {
                "cached": (
                    None if cached is None else _bounded_string(cached, "module __cached__")
                ),
                "expected_cache_path": expected_cache_relative,
                "file": observed_path,
                "loader_type": _loader_type(loader),
                "name": _bounded_string(name, "A4 module name", 256),
                "origin": origin,
                "source_path": relative,
                "source_sha256": identity["sha256"],
                "source_size_bytes": identity["size_bytes"],
            }
        )
    return records


def _self_start_time_clock_ticks() -> int:
    descriptor = os.open(
        "/proc/self/stat",
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        payload = _read_bounded(descriptor, 16_384, "/proc/self/stat")
    finally:
        os.close(descriptor)
    closing = payload.rfind(b")")
    if closing <= 0 or closing + 2 >= len(payload):
        raise RuntimeError("/proc/self/stat is malformed")
    fields = payload[closing + 2 :].split()
    if len(fields) < 20 or not fields[19].isdigit():
        raise RuntimeError("/proc/self/stat start-time field is malformed")
    value = int(fields[19])
    if value <= 0:
        raise RuntimeError("/proc/self/stat start-time field is nonpositive")
    return value


_STARTUP_RETAINED_MODULE_NAMES: tuple[str, ...] | None = None


def _cache_policy_observation(
    checkpoint: str, reviewed_sources: object | None = None
) -> dict[str, object]:
    global _STARTUP_RETAINED_MODULE_NAMES

    if checkpoint not in {"STARTUP_PREIMPORT", "B_PRETERMINAL", "P_PRETERMINAL"}:
        raise RuntimeError("unknown cache-policy observation stage")
    repository_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    site_module = _sys.modules.get("site")
    user_site_enabled = getattr(site_module, "ENABLE_USER_SITE", None)
    retained = _retained_module_records(_STARTUP_RETAINED_MODULE_NAMES)
    if checkpoint == "STARTUP_PREIMPORT":
        _STARTUP_RETAINED_MODULE_NAMES = tuple(
            str(item["name"]) for item in retained
        )
    observation = {
        "a4_modules": _module_records(repository_root, reviewed_sources),
        "cache_paths": _cache_path_observation(repository_root),
        "checkpoint": checkpoint,
        "interpreter": {
            "dont_write_bytecode": _sys.dont_write_bytecode,
            "flags": {
                "dont_write_bytecode": _sys.flags.dont_write_bytecode,
                "ignore_environment": _sys.flags.ignore_environment,
                "isolated": _sys.flags.isolated,
                "no_site": _sys.flags.no_site,
                "optimize": _sys.flags.optimize,
            },
            "implementation_cache_tag": _sys.implementation.cache_tag,
            "pycache_prefix": _sys.pycache_prefix,
        },
        "observed_monotonic_ns": time.monotonic_ns(),
        "parent_identity": {
            "pid": os.getpid(),
            "start_time_clock_ticks": _self_start_time_clock_ticks(),
        },
        "retained_modules": retained,
        "sys_meta_path": _meta_path_records(),
        "sys_path": _sys_path_records(),
        "user_site_enabled": user_site_enabled,
    }
    _reject_old_worktree(observation, f"{checkpoint} observation")
    return observation


def _reject_old_worktree(value: object, description: str) -> None:
    if isinstance(value, str):
        if _OLD_WORKTREE in value:
            raise RuntimeError(f"{description} names the quarantined old worktree")
        return
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_old_worktree(key, description)
            _reject_old_worktree(child, description)
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            _reject_old_worktree(child, description)


def _parent_cache_policy_binding() -> dict[str, object]:
    raw_cmdline, raw_arguments = _raw_proc_cmdline()
    cwd_path = os.readlink("/proc/self/cwd")
    if os.path.normpath(cwd_path) != os.path.normpath(os.getcwd()):
        raise RuntimeError("/proc/self/cwd differs from os.getcwd()")
    command_path = _python_command_path(raw_arguments[0])
    return {
        "bootstrap_external": _regular_file_identity(
            _BOOTSTRAP_EXTERNAL_PATH, 1 << 20
        ),
        "cwd": cwd_path,
        "environment": {
            "python_prefixed_names": sorted(
                name for name in os.environ if name.startswith("PYTHON")
            ),
            "thread_environment": {
                name: os.environ.get(name) for name in sorted(_EXPECTED_THREAD_ENVIRONMENT)
            },
        },
        "leader": {
            "command": _followed_file_identity(command_path, 1 << 20),
            "proc_self_exe": _followed_file_identity("/proc/self/exe", 1 << 20),
            "sys_executable": _followed_file_identity(_sys.executable, 1 << 20),
        },
        "raw_cmdline_hex": raw_cmdline.hex(),
        "raw_cmdline_sha256": _sha256(raw_cmdline),
        "raw_cmdline_size_bytes": len(raw_cmdline),
        "sys_argv": list(_sys.argv),
    }


def _startup_precondition_errors(
    observation: dict[str, object], parent: dict[str, object]
) -> list[str]:
    errors = []
    raw = bytes.fromhex(str(parent["raw_cmdline_hex"]))
    fields = raw[:-1].split(b"\0") if raw.endswith(b"\0") else []
    if tuple(fields) != _EXPECTED_PAR_RAW_ARGV:
        errors.append("raw parent argv is not the exact registered python -B command")
    if list(_sys.argv) != _EXPECTED_PAR_SYS_ARGV:
        errors.append("sys.argv is not the exact registered PAR argv")
    environment = parent["environment"]
    interpreter = observation["interpreter"]
    if not isinstance(environment, dict) or environment.get("python_prefixed_names") != []:
        errors.append("a PYTHON-prefixed environment key is present")
    if not isinstance(environment, dict) or environment.get("thread_environment") != _EXPECTED_THREAD_ENVIRONMENT:
        errors.append("thread environment is not the exact registered PAR environment")
    expected_interpreter = {
        "dont_write_bytecode": True,
        "flags": {
            "dont_write_bytecode": 1,
            "ignore_environment": 0,
            "isolated": 0,
            "no_site": 0,
            "optimize": 0,
        },
        "implementation_cache_tag": _EXPECTED_CACHE_TAG,
        "pycache_prefix": None,
    }
    if not isinstance(interpreter, dict) or any(
        interpreter.get(name) != value for name, value in expected_interpreter.items()
    ):
        errors.append("pre-import interpreter/cache state is not frozen")
    retained = observation.get("retained_modules")
    retained_names = (
        {item.get("name") for item in retained if isinstance(item, dict)}
        if isinstance(retained, list)
        else set()
    )
    if retained_names & {"sitecustomize", "usercustomize"}:
        errors.append("sitecustomize or usercustomize was retained at startup")
    return errors


def _startup_artifact_errors(
    observation: dict[str, object], parent: dict[str, object]
) -> list[str]:
    errors = []
    leader = parent.get("leader")
    bootstrap = parent.get("bootstrap_external")
    if not isinstance(leader, dict) or not all(
        isinstance(leader.get(name), dict)
        for name in ("command", "proc_self_exe", "sys_executable")
    ):
        errors.append("parent leader identity record is malformed")
    else:
        identities = [leader[name] for name in ("command", "proc_self_exe", "sys_executable")]
        if len({(item.get("device"), item.get("inode")) for item in identities}) != 1:
            errors.append("python command, sys.executable, and /proc/self/exe differ")
        if any(
            item.get("sha256") != _EXPECTED_LEADER_SHA256
            or item.get("size_bytes") != _EXPECTED_LEADER_SIZE_BYTES
            or item.get("resolved_path") != "/usr/bin/python3.9"
            or not isinstance(item.get("mode"), int)
            or not _stat.S_ISREG(item["mode"])
            or not isinstance(item.get("path"), str)
            or not os.path.isabs(item["path"])
            for item in identities
        ):
            errors.append("parent leader ELF differs from the CACHE-I byte pin")
    if not isinstance(bootstrap, dict) or (
        bootstrap.get("path") != _BOOTSTRAP_EXTERNAL_PATH
        or bootstrap.get("sha256") != _EXPECTED_BOOTSTRAP_SHA256
        or bootstrap.get("size_bytes") != _EXPECTED_BOOTSTRAP_SIZE_BYTES
        or not isinstance(bootstrap.get("device"), int)
        or not isinstance(bootstrap.get("inode"), int)
        or bootstrap.get("inode", 0) <= 0
        or not isinstance(bootstrap.get("mode"), int)
        or not _stat.S_ISREG(bootstrap["mode"])
    ):
        errors.append("installed importlib bootstrap differs from the CACHE-I byte pin")
    repository_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    clone_script = os.path.join(repository_root, "script")

    def allowed_installed(value: object) -> bool:
        return isinstance(value, str) and (
            value in {"built-in", "frozen"}
            or any(
                value == root or value.startswith(root + os.sep)
                for root in _ALLOWED_INSTALLED_ORIGIN_ROOTS
            )
        )

    retained = observation.get("retained_modules")
    if not isinstance(retained, list) or len(retained) > _STARTUP_MODULE_LIMIT:
        errors.append("startup retained-module inventory is malformed")
    else:
        for item in retained:
            if not isinstance(item, dict) or set(item) != {
                "cached",
                "file",
                "loader_type",
                "name",
                "origin",
            }:
                errors.append("startup retained-module record is malformed")
                break
            if item.get("name") == "__main__":
                expected_main = os.path.join(
                    clone_script, "run_arbitrary_cardinality_a4_v2.py"
                )
                if (
                    item.get("file") != expected_main
                    or item.get("origin") != expected_main
                    or item.get("cached") is not None
                ):
                    errors.append("startup __main__ identity differs")
                continue
            for field in ("cached", "file", "origin"):
                value = item.get(field)
                if value is not None and not allowed_installed(value):
                    errors.append(f"startup module {field} is outside frozen roots")
                    break
    sys_path = observation.get("sys_path")
    if not isinstance(sys_path, list) or (
        [path for path in sys_path if isinstance(path, str) and path.startswith(repository_root + os.sep)]
        != [clone_script]
    ) or any(
        not isinstance(path, str)
        or (path != clone_script and not allowed_installed(path))
        for path in (sys_path if isinstance(sys_path, list) else [])
    ):
        errors.append("startup sys.path differs from frozen roots")
    meta_path = observation.get("sys_meta_path")
    if not isinstance(meta_path, list) or any(
        not isinstance(item, dict)
        or set(item) != {"origin", "type"}
        or (
            item.get("origin") is not None
            and not allowed_installed(item.get("origin"))
        )
        for item in (meta_path if isinstance(meta_path, list) else [])
    ):
        errors.append("startup sys.meta_path differs from frozen roots")
    return errors


_STARTUP_CAPTURE: dict[str, object] | None = None
if _PAR_MODE_REQUESTED:
    try:
        _STARTUP_PARENT_BINDING = _parent_cache_policy_binding()
        _STARTUP_OBSERVATION = _cache_policy_observation("STARTUP_PREIMPORT")
    except (OSError, RuntimeError, ValueError) as _startup_error:
        os.write(
            2,
            f"ARTIFACT_INVALID: pre-import cache capture failed: {_startup_error}\n".encode(
                "utf-8", errors="backslashreplace"
            ),
        )
        raise SystemExit(3)
    _STARTUP_CAPTURE = {
        "observation": _STARTUP_OBSERVATION,
        "parent": _STARTUP_PARENT_BINDING,
    }
    _precondition_errors = _startup_precondition_errors(
        _STARTUP_OBSERVATION, _STARTUP_PARENT_BINDING
    )
    if _precondition_errors:
        os.write(
            2,
            ("PRECONDITION_NOT_MET: " + "; ".join(_precondition_errors) + "\n").encode(
                "utf-8"
            ),
        )
        raise SystemExit(2)
    _artifact_errors = _startup_artifact_errors(
        _STARTUP_OBSERVATION, _STARTUP_PARENT_BINDING
    )
    if _artifact_errors:
        os.write(
            2,
            ("ARTIFACT_INVALID: " + "; ".join(_artifact_errors) + "\n").encode(
                "utf-8"
            ),
        )
        raise SystemExit(3)


try:
    from a4_v2_runner import main  # noqa: E402  (intentionally post-snapshot)
except MemoryError as _runner_import_resource_error:
    _write_bootstrap_status(
        "RESOURCE_INCOMPLETE_NO_DECISION",
        f"runner import resource failure: {_runner_import_resource_error}",
    )
    raise SystemExit(3)
except (ImportError, OSError, RuntimeError, SyntaxError, TypeError, ValueError) as _runner_import_error:
    _write_bootstrap_status(
        "IMPLEMENTATION_INVALID",
        f"reviewed runner import failure: {_runner_import_error}",
    )
    raise SystemExit(3)


if __name__ == "__main__":
    try:
        _main_result = main(
            _START_CPU_MICROSECONDS,
            _START_WALL_NANOSECONDS,
            _STARTUP_CAPTURE,
            _cache_policy_observation if _PAR_MODE_REQUESTED else None,
        )
    except MemoryError as _main_resource_error:
        _write_bootstrap_status(
            "RESOURCE_INCOMPLETE_NO_DECISION",
            f"bootstrap resource failure: {_main_resource_error}",
        )
        raise SystemExit(3)
    except KeyboardInterrupt:
        _write_bootstrap_status(
            "RESOURCE_INCOMPLETE_NO_DECISION", "bootstrap interrupted"
        )
        raise SystemExit(3)
    except SystemExit as _argument_exit:
        _write_bootstrap_status(
            "PRECONDITION_NOT_MET",
            f"bootstrap argument parser exited: {_argument_exit.code}",
        )
        raise SystemExit(2)
    except Exception as _main_defect:
        _write_bootstrap_status(
            "IMPLEMENTATION_INVALID",
            f"unhandled runner bootstrap defect: {_main_defect}",
        )
        raise SystemExit(3)
    if not isinstance(_main_result, int) or isinstance(_main_result, bool):
        _write_bootstrap_status(
            "IMPLEMENTATION_INVALID", "runner returned a non-integer status"
        )
        raise SystemExit(3)
    raise SystemExit(_main_result)
