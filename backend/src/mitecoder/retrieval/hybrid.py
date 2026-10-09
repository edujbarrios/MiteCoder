"""Hybrid lexical and symbol retrieval."""

from mitecoder.repository.workspace import Workspace
from mitecoder.retrieval.base import ContextItem
from mitecoder.retrieval.lexical import LexicalRetrieval
from mitecoder.retrieval.symbols import SymbolRetrieval


class HybridRetrieval:
    def __init__(self, max_files: int = 5, max_lines_per_file: int = 120) -> None:
        self.max_files = max_files
        self.lexical = LexicalRetrieval(max_files, max_lines_per_file)
        self.symbols = SymbolRetrieval(max_files)

    def retrieve(self, query: str, workspace: Workspace) -> list[ContextItem]:
        merged: dict[tuple[str, int, int], ContextItem] = {}
        for item in self.lexical.retrieve(query, workspace) + self.symbols.retrieve(
            query, workspace
        ):
            key = (item.path, item.start_line, item.end_line)
            if key not in merged or item.score > merged[key].score:
                merged[key] = item
        return sorted(merged.values(), key=lambda item: (-item.score, item.path))[: self.max_files]
