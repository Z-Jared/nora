import json
from datetime import datetime, timezone
from pathlib import Path


class JsonlToolLogger:
    def __init__(self, path: Path):
        self.path = path

    def record(self, tool: str, arguments: dict, status: str, result: str = "") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "arguments": arguments,
            "status": status,
            "result_preview": result[:500],
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
