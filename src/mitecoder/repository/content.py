"""Human-readable extraction for supported workspace files."""

from __future__ import annotations

import json
from pathlib import Path


def readable_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if "\x00" in raw:
        return ""
    if path.suffix.lower() != ".ipynb":
        return raw
    try:
        notebook = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    cells = notebook.get("cells", []) if isinstance(notebook, dict) else []
    if not isinstance(cells, list):
        return raw
    parts: list[str] = []
    for index, cell in enumerate(cells, 1):
        if not isinstance(cell, dict):
            continue
        cell_type = str(cell.get("cell_type", "unknown"))
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(str(line) for line in source)
        if isinstance(source, str) and source.strip():
            parts.append(f"--- {cell_type} cell {index} ---\n{source.rstrip()}")
    return "\n\n".join(parts) if parts else raw
