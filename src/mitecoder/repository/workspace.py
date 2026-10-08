"""Workspace sandbox and file access."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mitecoder.exceptions import WorkspaceSecurityError


@dataclass(frozen=True)
class Workspace:
    root: Path

    def __init__(self, root: str | Path) -> None:
        resolved = Path(root).expanduser().resolve(strict=True)
        if not resolved.is_dir():
            raise WorkspaceSecurityError(f"workspace is not a directory: {resolved}")
        object.__setattr__(self, "root", resolved)

    def resolve(self, relative: str | Path, *, must_exist: bool = False) -> Path:
        raw = Path(relative)
        if raw.is_absolute():
            raise WorkspaceSecurityError("absolute paths are not allowed")
        candidate = (self.root / raw).resolve(strict=False)
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceSecurityError(f"path escapes workspace: {relative}") from exc
        # Resolve every existing ancestor, preventing symlink escapes for new files too.
        probe = candidate
        while not probe.exists() and probe != self.root:
            probe = probe.parent
        try:
            probe.resolve(strict=True).relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceSecurityError(f"symlink escapes workspace: {relative}") from exc
        if must_exist and not candidate.exists():
            raise FileNotFoundError(str(relative))
        return candidate

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def read_text(self, path: str | Path) -> str:
        return self.resolve(path, must_exist=True).read_text(encoding="utf-8", errors="replace")

    def iter_files(self) -> list[Path]:
        ignored = {
            ".mypy_cache",
            ".nox",
            ".git",
            ".venv",
            ".pytest_cache",
            ".ruff_cache",
            ".tox",
            "__pycache__",
            "benchmark-results",
            "build",
            "dist",
            "node_modules",
            "runs",
        }
        files: list[Path] = []
        for directory, names, filenames in os.walk(self.root, followlinks=False):
            names[:] = [
                name
                for name in names
                if name not in ignored
                and not name.startswith(".test-")
                and not (Path(directory) / name).is_symlink()
            ]
            for name in filenames:
                path = Path(directory) / name
                if not path.is_symlink() and path.stat().st_size <= 2_000_000:
                    files.append(path)
        return sorted(files)
