"""Python AST symbol retrieval."""

from __future__ import annotations

import ast
import re

from mitecoder.repository.workspace import Workspace
from mitecoder.retrieval.base import ContextItem


class SymbolRetrieval:
    def __init__(self, max_files: int = 5) -> None:
        self.max_files = max_files

    def retrieve(self, query: str, workspace: Workspace) -> list[ContextItem]:
        terms = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", query.lower()))
        items: list[ContextItem] = []
        for path in workspace.iter_files():
            if path.suffix != ".py":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                name = getattr(node, "name", "")
                if name and name.lower() in terms:
                    lines = text.splitlines()
                    start = max(1, getattr(node, "lineno", 1))
                    end = min(len(lines), getattr(node, "end_lineno", start + 40))
                    items.append(
                        ContextItem(
                            workspace.relative(path),
                            start,
                            end,
                            "\n".join(lines[start - 1 : end]),
                            20.0,
                            f"symbol={name}",
                        )
                    )
        return sorted(items, key=lambda item: (item.path, item.start_line))[: self.max_files]
