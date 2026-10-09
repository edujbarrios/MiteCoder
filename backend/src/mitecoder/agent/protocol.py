"""Strict untrusted model-action parser."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mitecoder.exceptions import ProtocolError


@dataclass(frozen=True)
class AgentAction:
    action: str
    arguments: dict[str, Any]
    summary: str


def parse_action(text: str, allowed_actions: set[str]) -> AgentAction:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"model response is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict) or set(value) - {"action", "arguments", "summary"}:
        raise ProtocolError("action must be an object with only action, arguments, and summary")
    action = value.get("action")
    arguments = value.get("arguments", {})
    summary = value.get("summary", "")
    if not isinstance(action, str) or action not in allowed_actions | {"finish"}:
        raise ProtocolError(f"unsupported action: {action!r}")
    if not isinstance(arguments, dict) or not isinstance(summary, str) or len(summary) > 300:
        raise ProtocolError(
            "arguments must be an object and summary must be at most 300 characters"
        )
    return AgentAction(action, arguments, summary)
