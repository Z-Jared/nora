from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


def confirm_in_terminal(prompt: str) -> bool:
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False

    return answer in {"y", "yes"}


@dataclass(frozen=True)
class PermissionChoice:
    label: str
    value: bool


ALLOW_ONCE = PermissionChoice(label="Allow once", value=True)
DENY = PermissionChoice(label="Deny", value=False)
ALWAYS_ALLOW_SESSION = PermissionChoice(label="Always allow this tool this session", value=True)
DEFAULT_CHOICES: list[PermissionChoice] = [ALLOW_ONCE, DENY]


def selectable_confirm(
    prompt: str,
    choices: Optional[list[PermissionChoice]] = None,
    input_func: Optional[Callable[[str], str]] = None,
) -> bool:
    """Present numbered approval choices with deny-by-default behavior."""
    choices = choices or DEFAULT_CHOICES
    read_input = input_func or input
    lines = [prompt, ""]
    for index, choice in enumerate(choices, start=1):
        lines.append(f"  [{index}] {choice.label}")
    lines.append("")
    lines.append(f"Select [1-{len(choices)}]: ")
    try:
        raw = read_input("\n".join(lines)).strip()
    except EOFError:
        return False
    try:
        selected = int(raw) - 1
    except (TypeError, ValueError):
        return False
    if 0 <= selected < len(choices):
        return choices[selected].value
    return False


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records
