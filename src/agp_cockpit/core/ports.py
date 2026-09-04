from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from agp_cockpit.core.terminal_exec import TerminalCommand, TerminalResult


class TerminalPort(Protocol):
    def preview(self, command: "TerminalCommand") -> str:
        """Render one already-authorized local command without executing it."""

    def execute(self, command: "TerminalCommand") -> "TerminalResult":
        """Execute one already-authorized local command."""


class BrowserPort(Protocol):
    def submit_prompt(self, text: str) -> None:
        """Transport a prompt to the configured browser LLM UI."""


class KitPort(Protocol):
    def next_safe_action(self, repository: str) -> str:
        """Read the next safe action from the Agentic Project Kit."""


class ProcessPort(Protocol):
    def is_running(self, process_name: str) -> bool:
        """Report whether a local process is running."""
