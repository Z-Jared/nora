from dataclasses import dataclass


@dataclass
class ContextWindow:
    max_tool_result_chars: int = 8000
    head_chars: int = 3000
    tail_chars: int = 2000

    def compact_tool_result(self, tool_name: str, result: str) -> str:
        if len(result) <= self.max_tool_result_chars:
            return result

        head_size = max(0, min(self.head_chars, self.max_tool_result_chars))
        tail_size = max(0, min(self.tail_chars, self.max_tool_result_chars - head_size))
        head = result[:head_size]
        tail = result[-tail_size:] if tail_size else ""
        omitted = max(0, len(result) - len(head) - len(tail))
        summary = _summarize(result)

        return "\n".join(
            [
                (
                    "[tool_result_compacted "
                    f"tool={tool_name} original_chars={len(result)} "
                    f"shown_chars={len(head) + len(tail)} omitted_chars={omitted}]"
                ),
                f"summary: {summary}",
                "--- head ---",
                head.rstrip(),
                "--- tail ---",
                tail.lstrip(),
            ]
        ).strip()


def _summarize(text: str) -> str:
    lines = text.splitlines()
    non_empty = [line.strip() for line in lines if line.strip()]
    return f"{len(text)} chars, {len(lines)} lines, {len(non_empty)} non-empty lines"
