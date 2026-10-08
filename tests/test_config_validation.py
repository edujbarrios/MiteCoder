from __future__ import annotations

from pathlib import Path

import pytest

from mitecoder.config.loader import load_config
from mitecoder.config.schema import (
    AgentConfig,
    Config,
    InferenceConfig,
)
from mitecoder.config.schema import (
    TestingConfig as RuntimeTestingConfig,
)
from mitecoder.exceptions import ConfigurationError


def test_testing_commands_must_be_a_list_not_a_string(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text('testing:\n  commands: "pytest -q"\n', encoding="utf-8")

    with pytest.raises(ConfigurationError, match="list of strings"):
        load_config(config)


@pytest.mark.parametrize(
    "config, message",
    [
        (Config(agent=AgentConfig(max_tool_calls=0)), "max_tool_calls"),
        (Config(testing=RuntimeTestingConfig(timeout_seconds=0)), "timeout_seconds"),
        (Config(inference=InferenceConfig(top_p=0)), "top_p"),
        (Config(testing=RuntimeTestingConfig(commands=(" ",))), "cannot be empty"),
    ],
)
def test_invalid_runtime_limits_are_rejected(config: Config, message: str) -> None:
    with pytest.raises(ConfigurationError, match=message):
        config.validate()
