"""Cheap workspace inspection with optional Git metadata."""

from __future__ import annotations

import subprocess
from collections import Counter
from dataclasses import asdict, dataclass

from mitecoder.repository.workspace import Workspace
from mitecoder.subprocess_utils import run_text

LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".c": "C",
    ".cpp": "C++",
    ".java": "Java",
    ".ipynb": "Jupyter Notebook",
}


@dataclass
class Inspection:
    files: int
    languages: dict[str, int]
    text_bytes: int
    test_frameworks: list[str]
    candidate_test_commands: list[str]
    git_status: str
    largest_files: list[tuple[str, int]]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def inspect_workspace(workspace: Workspace) -> Inspection:
    files = workspace.iter_files()
    languages = Counter(LANGUAGES.get(p.suffix.lower(), "Other") for p in files)
    sizes = [(workspace.relative(p), p.stat().st_size) for p in files]
    names = {p.name for p in files}
    frameworks: list[str] = []
    commands: list[str] = []
    if (
        "pytest.ini" in names
        or "pyproject.toml" in names
        or any("test" in p.name for p in files if p.suffix == ".py")
    ):
        frameworks.append("pytest")
        commands.append("pytest -q")
    if "package.json" in names:
        frameworks.append("npm")
        commands.append("npm test")
    try:
        proc = run_text(
            ["git", "status", "--short"],
            cwd=workspace.root,
            capture_output=True,
            timeout=5,
            check=False,
        )
        git_status = (proc.stdout or "").strip() or (
            "clean" if proc.returncode == 0 else "not a Git repository"
        )
    except (OSError, subprocess.TimeoutExpired):
        git_status = "unavailable"
    return Inspection(
        len(files),
        dict(languages),
        sum(size for _, size in sizes),
        frameworks,
        commands,
        git_status,
        sorted(sizes, key=lambda item: item[1], reverse=True)[:5],
    )
