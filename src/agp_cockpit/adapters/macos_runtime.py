from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from agp_cockpit.core.runtime import RuntimeStatus, discover_local_runtime, process_name_present


@dataclass(frozen=True)
class MacOSProcessPort:
    """macOS process inspection adapter."""
    def is_running(self, process_name: str) -> bool:
        completed = subprocess.run(["ps", "-axo", "pid=,command="], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if completed.returncode != 0:
            return False
        needle = process_name.casefold()
        return any(needle in line.casefold() for line in completed.stdout.splitlines() if line.strip())

@dataclass(frozen=True)
class MacOSRuntimeSnapshot:
    runtime: RuntimeStatus
    ollama_process_present: bool
    hermes_process_present: bool

def is_macos() -> bool:
    return platform.system() == "Darwin"

def discover_macos_runtime() -> MacOSRuntimeSnapshot:
    if not is_macos():
        raise RuntimeError("macOS runtime adapter used on a non-macOS system")
    runtime = discover_local_runtime()
    return MacOSRuntimeSnapshot(
        runtime=runtime,
        ollama_process_present=process_name_present("ollama", process_port=MacOSProcessPort()),
        hermes_process_present=process_name_present("hermes", process_port=MacOSProcessPort()),
    )
