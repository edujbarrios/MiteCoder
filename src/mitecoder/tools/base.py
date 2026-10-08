"""Command abstraction for restricted tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    output: str
    changed_files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    name: str
    description: str
    schema: dict[str, Any]

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute validated, structured arguments."""
