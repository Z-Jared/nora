"""TTY/raw terminal interactive frontend for Nora."""

import sys
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import radiolist_dialog

from mini_agent.cli import MiniAgentCLI
from mini_agent.tools_common import ALLOW_ONCE, DENY, confirm_in_terminal


class SlashCompleter(Completer):
    """Complete Nora slash commands for prefixes like /, /m, and /mo."""

    def __init__(self, commands: list[str]):
        self.commands = sorted(commands)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        for command in self.match(text):
            yield Completion(command, start_position=-len(text), display=command)

    def match(self, text: str) -> list[str]:
        if not text.startswith("/"):
            return []
        prefix = text.lower()
        return [
            command
            for command in self.commands
            if command.lower().startswith(prefix) and command.lower() != prefix
        ]


def selectable_confirm(prompt_text: str) -> bool:
    """TTY approval selector with non-TTY y/N fallback."""
    if not sys.stdout.isatty():
        return confirm_in_terminal(prompt_text)
    try:
        result = radiolist_dialog(
            title="Tool approval",
            text=prompt_text,
            values=[
                (ALLOW_ONCE.value, ALLOW_ONCE.label),
                (DENY.value, DENY.label),
            ],
        ).run()
        return bool(result)
    except Exception:
        return confirm_in_terminal(prompt_text)


class InteractiveCLI:
    """TTY-aware frontend that delegates command semantics to MiniAgentCLI."""

    def __init__(self, agent, registry, settings=None, root: Path = None, session_store=None):
        registry.confirm_action = selectable_confirm
        self._status_events: list[str] = []
        self.cli = MiniAgentCLI(
            agent,
            registry,
            settings=settings,
            root=root or Path.cwd(),
            output_func=self._status_output,
            session_store=session_store,
        )
        self.root = self.cli.root
        self.settings = settings
        self.completer = SlashCompleter(MiniAgentCLI.slash_command_names())
        self.session: Optional[PromptSession] = None

    def _toolbar_text(self) -> HTML:
        if self.settings and getattr(self.settings, "is_llm_enabled", False):
            model = getattr(self.settings, "model", "unknown")
        else:
            model = "disabled"
        cwd = str(self.root)
        if len(cwd) > 50:
            cwd = "..." + cwd[-47:]
        return HTML(
            f" <b>model:</b> {model}  "
            f"<b>cwd:</b> {cwd}  "
            f"<b>local-first</b>  "
            f"<b>/ for commands</b>"
        )

    def _status_output(self, text: str) -> None:
        if text == "Working...":
            self._show_status(text)
        elif text == "Done.":
            self._clear_status()

    def _show_status(self, text: str) -> None:
        self._status_events.append(text)
        sys.stdout.write(f"\r{text}")
        sys.stdout.flush()

    def _clear_status(self) -> None:
        self._status_events.append("Done.")
        sys.stdout.write("\r" + (" " * 24) + "\r")
        sys.stdout.flush()

    def _make_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("/")
        def _(event):
            event.app.current_buffer.insert_text("/")
            event.app.current_buffer.start_completion(select_first=False)

        @bindings.add("tab")
        def _(event):
            buffer = event.app.current_buffer
            text = buffer.document.text_before_cursor
            matches = self.completer.match(text)
            if len(matches) == 1:
                buffer.delete_before_cursor(count=len(text))
                buffer.insert_text(matches[0])
            elif matches:
                buffer.start_completion(select_first=True)
            else:
                buffer.insert_text("\t")

        return bindings

    def run(self) -> None:
        print(self.cli.banner())
        self.session = PromptSession(
            completer=self.completer,
            key_bindings=self._make_bindings(),
            bottom_toolbar=self._toolbar_text,
            message="> ",
        )
        with patch_stdout():
            while True:
                try:
                    user_input = self.session.prompt().strip()
                except (EOFError, KeyboardInterrupt):
                    print("")
                    break
                result = self.cli.handle_input(user_input)
                if result is None:
                    break
                if result:
                    print(result)


def is_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()
