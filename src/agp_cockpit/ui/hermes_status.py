from __future__ import annotations

from agp_cockpit.core.hermes_runtime import HermesRuntimeInfo


def format_hermes_status(info: HermesRuntimeInfo) -> str:
    executable = (
        str(info.executable.path)
        if info.executable.path is not None
        else "nicht gefunden"
    )

    if not info.config.exists:
        config_state = f"nicht gefunden ({info.config.path})"
    elif info.config.error:
        config_state = f"Fehler: {info.config.error}"
    else:
        config_state = str(info.config.path)

    model = info.config.model or "nicht erkannt"

    if info.configured_model_available is True:
        model_state = "lokal verfügbar"
    elif info.configured_model_available is False:
        model_state = "NICHT lokal verfügbar"
    else:
        model_state = "nicht prüfbar"

    return "\n".join((
        f"Hermes: {executable}",
        f"Konfiguration: {config_state}",
        f"Hermes-Standardmodell: {model}",
        f"Modellstatus: {model_state}",
    ))
