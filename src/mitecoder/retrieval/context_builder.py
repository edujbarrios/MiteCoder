"""Token-budgeted context assembly."""

from mitecoder.retrieval.base import ContextItem


class ContextBuilder:
    def __init__(self, max_tokens: int) -> None:
        self.max_chars = max_tokens * 4

    def build(self, items: list[ContextItem]) -> str:
        parts: list[str] = []
        used = 0
        seen: set[tuple[str, int, int]] = set()
        for item in items:
            key = (item.path, item.start_line, item.end_line)
            if key in seen:
                continue
            header = f"\n--- {item.path}:{item.start_line}-{item.end_line} ---\n"
            available = self.max_chars - used - len(header)
            if available <= 0:
                break
            body = item.content[:available]
            parts.append(header + body)
            used += len(header) + len(body)
            seen.add(key)
        return "".join(parts).strip()
