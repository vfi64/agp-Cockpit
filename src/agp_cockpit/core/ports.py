from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from agp_cockpit.core.terminal_exec import TerminalCommand, TerminalResult


class TerminalPort(Protocol):
    def preview(self, command: TerminalCommand) -> str:
        """Render one already-authorized local command without executing it."""

    def execute(self, command: TerminalCommand) -> TerminalResult:
        """Execute one already-authorized local command."""


class BrowserPort(Protocol):
    def installed(self) -> bool:
        """Report whether the configured browser is installed."""

    def focus(self) -> None:
        """Focus or start the configured browser."""

    def open_url(self, url: str) -> None:
        """Open one authorized HTTP(S) URL in the configured browser."""


class KitPort(Protocol):
    def next_safe_action(self, repository: str) -> str:
        """Read the next safe action from the Agentic Project Kit."""


class ProcessPort(Protocol):
    def is_running(self, process_name: str) -> bool:
        """Report whether a local process is running."""
