from __future__ import annotations

from dataclasses import dataclass

from agp_cockpit.core.process_control import ProcessInfo, PortOwner, list_processes, ollama_processes, port_owner
from agp_cockpit.core.runtime import OLLAMA_DEFAULT_PORT


@dataclass(frozen=True)
class MacOSProcessSnapshot:
    ollama_processes: tuple[ProcessInfo, ...]
    ollama_port_owner: PortOwner


def inspect_macos_process_state() -> MacOSProcessSnapshot:
    processes = list_processes()
    return MacOSProcessSnapshot(
        ollama_processes=ollama_processes(processes=processes),
        ollama_port_owner=port_owner(OLLAMA_DEFAULT_PORT, processes=processes),
    )
