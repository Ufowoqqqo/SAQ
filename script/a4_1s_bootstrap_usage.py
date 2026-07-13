"""Minimal integer resource snapshot used before importing A4-1S modules."""

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


def _integer_cpu_microseconds() -> int:
    total = 0
    for who in (0, -1):  # Linux RUSAGE_SELF and RUSAGE_CHILDREN.
        usage = _Rusage()
        if _GETRUSAGE(who, ctypes.byref(usage)) != 0:
            error_number = ctypes.get_errno()
            raise OSError(error_number, os.strerror(error_number))
        for value in (usage.ru_utime, usage.ru_stime):
            if not 0 <= value.tv_usec < 1_000_000:
                raise RuntimeError("getrusage returned a noncanonical timeval")
            total += int(value.tv_sec) * 1_000_000 + int(value.tv_usec)
    return total


def capture_start() -> tuple[int, int]:
    """Return immutable CPU-microsecond and monotonic-wall-nanosecond starts."""

    return _integer_cpu_microseconds(), time.monotonic_ns()
