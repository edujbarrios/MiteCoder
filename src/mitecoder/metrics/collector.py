"""Structured event and process metrics."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def peak_rss_mb() -> float | None:
    try:
        import resource

        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value / (1024 * 1024 if __import__("sys").platform == "darwin" else 1024)
    except (AttributeError, ImportError, ValueError):
        try:
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
            )
            return counters.PeakWorkingSetSize / 1024 / 1024
        except Exception:
            return None


@dataclass
class MetricsCollector:
    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, event: str, **fields: Any) -> None:
        self.events.append({"event": event, "timestamp": time.time(), **fields})

    def write_jsonl(self, path: Path) -> None:
        path.write_text(
            "".join(json.dumps(event, sort_keys=True) + "\n" for event in self.events),
            encoding="utf-8",
        )
