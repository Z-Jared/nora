from dataclasses import dataclass


@dataclass
class ContextWindow:
    max_tool_result_chars: int = 8000
    head_chars: int = 3000
    tail_chars: int = 2000
    max_context_pack_chars: int = 3000

    def compact_tool_result(self, tool_name: str, result: str) -> str:
        if len(result) <= self.max_tool_result_chars:
            return result

        return self._compact(
            marker="tool_result_compacted",
            metadata=f"tool={tool_name}",
            text=result,
            limit=self.max_tool_result_chars,
        )

    def compact_context_pack(self, context_pack: str) -> str:
        if len(context_pack) <= self.max_context_pack_chars:
            return context_pack

        return self._compact(
            marker="context_pack_compacted",
            metadata="source=auto_context",
            text=context_pack,
            limit=self.max_context_pack_chars,
        )

    def _compact(self, marker: str, metadata: str, text: str, limit: int) -> str:
        head_size = max(0, min(self.head_chars, limit))
        tail_size = max(0, min(self.tail_chars, limit - head_size))
        head = text[:head_size]
        tail = text[-tail_size:] if tail_size else ""
        omitted = max(0, len(text) - len(head) - len(tail))
        summary = _summarize(text)

        return "\n".join(
            [
                (
                    f"[{marker} {metadata} original_chars={len(text)} "
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
