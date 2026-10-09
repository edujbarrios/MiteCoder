"""Capture subprocess output consistently across Windows and Unix locales."""

from __future__ import annotations

import subprocess
from typing import Any


def run_text(*popenargs: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Decode UTF-8 output without crashing on invalid or legacy-encoded bytes."""
    return subprocess.run(*popenargs, text=True, encoding="utf-8", errors="replace", **kwargs)


def combined_output(completed: subprocess.CompletedProcess[str]) -> str:
    """Return captured stdout and stderr even if either stream is missing."""
    return (completed.stdout or "") + (completed.stderr or "")
