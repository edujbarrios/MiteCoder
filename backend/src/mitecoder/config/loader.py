"""Load YAML configuration without runtime network access."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from mitecoder.config.schema import (
    AgentConfig,
    Config,
    InferenceConfig,
    RetrievalConfig,
    RuntimeConfig,
    TestingConfig,
)
from mitecoder.exceptions import ConfigurationError

T = TypeVar("T")


def _section(cls: type[T], data: dict[str, Any], name: str) -> T:
    raw = data.get(name, {})
    if not isinstance(raw, dict):
        raise ConfigurationError(f"{name} must be a mapping")
    try:
        if cls is TestingConfig and "commands" in raw:
            commands = raw["commands"]
            if not isinstance(commands, list | tuple) or not all(
                isinstance(command, str) for command in commands
            ):
                raise ConfigurationError("testing.commands must be a list of strings")
            raw = {**raw, "commands": tuple(commands)}
        return cls(**raw)
    except ConfigurationError:
        raise
    except TypeError as exc:
        raise ConfigurationError(f"invalid {name} configuration: {exc}") from exc


def load_config(path: str | Path) -> Config:
    target = Path(path)
    try:
        data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"cannot load configuration {target}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError("configuration root must be a mapping")
    config = Config(
        profile=str(data.get("profile", target.stem)),
        inference=_section(InferenceConfig, data, "inference"),
        retrieval=_section(RetrievalConfig, data, "retrieval"),
        agent=_section(AgentConfig, data, "agent"),
        runtime=_section(RuntimeConfig, data, "runtime"),
        testing=_section(TestingConfig, data, "testing"),
    )
    config.validate()
    return config
