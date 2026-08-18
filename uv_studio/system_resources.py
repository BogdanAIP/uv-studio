"""Secret-safe host resource snapshot for Stage 9 diagnostics and support."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any

MemoryProbe = Callable[[], tuple[int | None, int | None, str]]
CpuProbe = Callable[[], int | None]


def _windows_memory_status() -> tuple[int | None, int | None, str]:
    try:
        import ctypes

        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None, None, "unavailable"
        return int(status.ullTotalPhys), int(status.ullAvailPhys), "windows_global_memory_status"
    except (AttributeError, OSError, TypeError, ValueError):
        return None, None, "unavailable"


def _posix_memory_status() -> tuple[int | None, int | None, str]:
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        total_pages = int(os.sysconf("SC_PHYS_PAGES"))
        available_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        if page_size <= 0 or total_pages <= 0 or available_pages < 0:
            raise ValueError("invalid sysconf memory values")
        return (
            page_size * total_pages,
            page_size * available_pages,
            "posix_sysconf",
        )
    except (AttributeError, OSError, TypeError, ValueError):
        return None, None, "unavailable"


def _memory_status() -> tuple[int | None, int | None, str]:
    if sys.platform == "win32":
        return _windows_memory_status()
    return _posix_memory_status()


def build_system_resource_snapshot(
    *,
    memory_probe: MemoryProbe = _memory_status,
    cpu_probe: CpuProbe = os.cpu_count,
) -> dict[str, Any]:
    """Return coarse resource capacity without hostnames, paths or process listings."""
    try:
        logical_cpu_count = cpu_probe()
    except (OSError, RuntimeError):
        logical_cpu_count = None
    if not isinstance(logical_cpu_count, int) or isinstance(logical_cpu_count, bool) or logical_cpu_count <= 0:
        logical_cpu_count = None

    try:
        total_bytes, available_bytes, memory_source = memory_probe()
    except (OSError, RuntimeError):
        total_bytes, available_bytes, memory_source = None, None, "unavailable"

    if not isinstance(total_bytes, int) or isinstance(total_bytes, bool) or total_bytes <= 0:
        total_bytes = None
    if (
        not isinstance(available_bytes, int)
        or isinstance(available_bytes, bool)
        or available_bytes < 0
        or (total_bytes is not None and available_bytes > total_bytes)
    ):
        available_bytes = None
    if not isinstance(memory_source, str) or memory_source not in {
        "windows_global_memory_status",
        "posix_sysconf",
        "unavailable",
    }:
        memory_source = "unavailable"

    return {
        "logical_cpu_count": logical_cpu_count,
        "memory": {
            "total_bytes": total_bytes,
            "available_bytes": available_bytes,
            "source": memory_source,
        },
    }
