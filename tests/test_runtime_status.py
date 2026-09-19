from pathlib import Path

from agp_cockpit.adapters.macos_runtime import MacOSRuntimeSnapshot
from agp_cockpit.core.runtime import ExecutableInfo, PortStatus, RuntimeStatus
from agp_cockpit.ui.runtime_status import format_runtime_status


def test_runtime_status_text() -> None:
    snapshot = MacOSRuntimeSnapshot(
        runtime=RuntimeStatus(
            ollama=ExecutableInfo("ollama", Path("/opt/homebrew/bin/ollama")),
            hermes=ExecutableInfo("hermes", None),
            ollama_port=PortStatus("127.0.0.1", 11434, True),
        ),
        ollama_process_present=True,
        hermes_process_present=False,
    )
    text = format_runtime_status(snapshot)
    assert "Ollama-Prozess: läuft" in text
    assert "Ollama-Port 11434: belegt/erreichbar" in text
    assert "Hermes: nicht gefunden" in text
