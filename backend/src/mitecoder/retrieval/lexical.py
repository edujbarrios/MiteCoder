"""Transparent pure-Python lexical ranking."""

from __future__ import annotations

import re
from collections import Counter

from mitecoder.repository.content import readable_text
from mitecoder.repository.workspace import Workspace
from mitecoder.retrieval.base import ContextItem


class LexicalRetrieval:
    def __init__(self, max_files: int = 5, max_lines_per_file: int = 120) -> None:
        self.max_files, self.max_lines = max_files, max_lines_per_file

    def retrieve(self, query: str, workspace: Workspace) -> list[ContextItem]:
        terms = _tokens(query)
        ranked: list[ContextItem] = []
        files = workspace.iter_files()
        for path in files:
            try:
                text = readable_text(path)
            except OSError:
                continue
            if not text.strip():
                continue
            rel = workspace.relative(path)
            token_counts = Counter(_tokens(text))
            hits = sum(token_counts[term] for term in terms)
            path_hits = sum(1 for term in terms if term in rel.casefold())
            if not hits and not path_hits:
                continue
            lines = text.splitlines()
            hit_lines = [
                i for i, line in enumerate(lines) if set(terms).intersection(_tokens(line))
            ]
            center = hit_lines[0] if hit_lines else 0
            start = max(0, center - self.max_lines // 3)
            end = min(len(lines), start + self.max_lines)
            density = hits / max(len(lines), 1)
            score = hits + path_hits * 5 + density
            ranked.append(
                ContextItem(
                    rel,
                    start + 1,
                    end,
                    "\n".join(lines[start:end]),
                    score,
                    f"term_hits={hits}, path_hits={path_hits}",
                )
            )
        ranked.sort(key=lambda item: (-item.score, item.path))
        selected = ranked[: self.max_files]
        selected_paths = {item.path for item in selected}
        if len(selected) < self.max_files:
            fallbacks: list[ContextItem] = []
            for path in files:
                rel = workspace.relative(path)
                if rel in selected_paths:
                    continue
                try:
                    text = readable_text(path)
                except OSError:
                    continue
                if not text.strip():
                    continue
                lines = text.splitlines()
                end = min(len(lines), self.max_lines)
                priority = _overview_priority(rel)
                fallbacks.append(
                    ContextItem(
                        rel,
                        1,
                        end,
                        "\n".join(lines[:end]),
                        priority / 1000,
                        "workspace_overview",
                    )
                )
            fallbacks.sort(key=lambda item: (-item.score, item.path))
            selected.extend(fallbacks[: self.max_files - len(selected)])
        return selected


def _overview_priority(path: str) -> int:
    lowered = path.lower()
    name = lowered.rsplit("/", 1)[-1]
    if name.startswith("readme"):
        return 100
    if name in {"pyproject.toml", "package.json", "cargo.toml", "go.mod"}:
        return 90
    if lowered.endswith(".ipynb"):
        return 80
    if "/tests/" in f"/{lowered}" or name.startswith("test_"):
        return 20
    if lowered.endswith((".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp")):
        return 60
    if lowered.endswith((".md", ".rst", ".txt", ".yaml", ".yml", ".toml", ".json")):
        return 40
    return 10


def _tokens(text: str) -> list[str]:
    return [
        token.casefold()
        for token in re.findall(r"[^\W\d]\w*", text, flags=re.UNICODE)
        if len(token) > 1
    ]
