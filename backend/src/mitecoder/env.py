"""Environment and provenance reporting."""

from __future__ import annotations

import importlib.metadata
import os
import platform
from typing import Any

from mitecoder import __version__
from mitecoder.metrics.collector import peak_rss_mb


def environment_report() -> dict[str, Any]:
    try:
        llama_version = importlib.metadata.version("llama-cpp-python")
    except importlib.metadata.PackageNotFoundError:
        llama_version = None
    total_ram = None
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_phys", ctypes.c_ulonglong),
                ("avail_phys", ctypes.c_ulonglong),
                ("total_page", ctypes.c_ulonglong),
                ("avail_page", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("avail_virtual", ctypes.c_ulonglong),
                ("avail_extended", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if os.name == "nt" and ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            total_ram = round(status.total_phys / 1024 / 1024, 1)
    except Exception:
        pass
    return {
        "mitecoder_version": __version__,
        "python": platform.python_version(),
        "os": platform.system(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or None,
        "logical_cores": os.cpu_count(),
        "total_ram_mb": total_ram,
        "llama_cpp_python": llama_version,
        "process_peak_rss_mb": peak_rss_mb(),
    }
