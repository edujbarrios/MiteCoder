from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class RunResult:
    status: str
    reason: str
    summary: str
    steps: int
    llm_calls: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    wall_seconds: float
    verification_passed: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
