"""Retrieval strategy types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mitecoder.repository.workspace import Workspace


@dataclass(frozen=True)
class ContextItem:
    path: str
    start_line: int
    end_line: int
    content: str
    score: float
    reason: str


class RetrievalStrategy(Protocol):
    def retrieve(self, query: str, workspace: Workspace) -> list[ContextItem]: ...
