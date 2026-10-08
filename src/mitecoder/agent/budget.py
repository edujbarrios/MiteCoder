"""First-class execution budgets."""

from __future__ import annotations

import time
from dataclasses import dataclass

from mitecoder.config.schema import AgentConfig


@dataclass
class BudgetManager:
    limits: AgentConfig
    steps: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    context_tokens: int = 0

    def __post_init__(self) -> None:
        self.started = time.monotonic()

    def exhausted(self) -> str | None:
        if self.steps >= self.limits.max_steps:
            return "max_steps"
        if self.llm_calls >= self.limits.max_llm_calls:
            return "max_llm_calls"
        if self.tool_calls >= self.limits.max_tool_calls:
            return "max_tool_calls"
        if time.monotonic() - self.started >= self.limits.max_wall_seconds:
            return "max_wall_seconds"
        return None
