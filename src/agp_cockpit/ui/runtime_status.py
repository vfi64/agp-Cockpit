from __future__ import annotations

from agp_cockpit.adapters.macos_runtime import MacOSRuntimeSnapshot


def format_runtime_status(snapshot: MacOSRuntimeSnapshot) -> str:
    runtime = snapshot.runtime
    ollama_binary = str(runtime.ollama.path) if runtime.ollama.path is not None else "nicht gefunden"
    hermes_binary = str(runtime.hermes.path) if runtime.hermes.path is not None else "nicht gefunden"
    port_state = "belegt/erreichbar" if runtime.ollama_port.accepting_connections else "frei/nicht erreichbar"
    return "\n".join(
        (
            f"Ollama: {ollama_binary}",
            "Ollama-Prozess: " + ("läuft" if snapshot.ollama_process_present else "nicht erkannt"),
            f"Ollama-Port {runtime.ollama_port.port}: {port_state}",
            f"Hermes: {hermes_binary}",
            "Hermes-Prozess: " + ("läuft" if snapshot.hermes_process_present else "nicht erkannt"),
        )
    )
