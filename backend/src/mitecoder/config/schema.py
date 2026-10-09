"""Typed runtime configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from mitecoder.exceptions import ConfigurationError


@dataclass(frozen=True)
class InferenceConfig:
    backend: str = "llama_cpp"
    model: str = "qwen2.5-coder-0.5b-q4"
    context_length: int = 2048
    max_output_tokens: int = 256
    temperature: float = 0.0
    top_p: float = 1.0
    top_k: int = 1
    seed: int = 42
    threads: int = 4
    batch_size: int = 32
    mmap: bool = True
    mlock: bool = False


@dataclass(frozen=True)
class RetrievalConfig:
    strategy: str = "hybrid"
    max_files: int = 5
    max_lines_per_file: int = 120
    max_context_tokens: int = 1200


@dataclass(frozen=True)
class AgentConfig:
    max_steps: int = 8
    max_llm_calls: int = 8
    max_tool_calls: int = 16
    max_wall_seconds: float = 600.0


@dataclass(frozen=True)
class RuntimeConfig:
    max_ram_mb: int = 2048
    artifact_dir: str = "runs"


@dataclass(frozen=True)
class TestingConfig:
    commands: tuple[str, ...] = ("pytest -q",)
    timeout_seconds: float = 120.0


@dataclass(frozen=True)
class Config:
    profile: str = "custom"
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)

    def validate(self) -> None:
        positive = {
            "context_length": self.inference.context_length,
            "max_output_tokens": self.inference.max_output_tokens,
            "threads": self.inference.threads,
            "batch_size": self.inference.batch_size,
            "max_files": self.retrieval.max_files,
            "max_lines_per_file": self.retrieval.max_lines_per_file,
            "max_context_tokens": self.retrieval.max_context_tokens,
            "max_steps": self.agent.max_steps,
            "max_llm_calls": self.agent.max_llm_calls,
            "max_tool_calls": self.agent.max_tool_calls,
            "max_wall_seconds": self.agent.max_wall_seconds,
            "max_ram_mb": self.runtime.max_ram_mb,
            "timeout_seconds": self.testing.timeout_seconds,
        }
        invalid = [name for name, value in positive.items() if value <= 0]
        if invalid:
            raise ConfigurationError(f"Values must be positive: {', '.join(invalid)}")
        if (
            self.retrieval.max_context_tokens + self.inference.max_output_tokens
            > self.inference.context_length
        ):
            raise ConfigurationError("retrieval and output token budgets exceed context_length")
        if not self.testing.commands:
            raise ConfigurationError("at least one configured test command is required")
        if any(not command.strip() for command in self.testing.commands):
            raise ConfigurationError("configured test commands cannot be empty")
        if self.inference.temperature < 0:
            raise ConfigurationError("temperature must be non-negative")
        if not 0 < self.inference.top_p <= 1:
            raise ConfigurationError("top_p must be greater than 0 and at most 1")
        if self.inference.top_k < 0:
            raise ConfigurationError("top_k must be non-negative")
        if not self.runtime.artifact_dir.strip():
            raise ConfigurationError("artifact_dir cannot be empty")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
