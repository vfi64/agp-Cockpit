from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable

class StartupAction(str, Enum):
    CONTINUE = "continue"
    START_OLLAMA = "start_ollama"
    RECOVER_OLLAMA = "recover_ollama"
    BLOCK = "block"

@dataclass(frozen=True)
class StartupObservation:
    ollama_installed: bool
    port_busy: bool
    port_owner_is_ollama: bool
    api_reachable: bool
    models: tuple[str, ...] = ()
    detail: str = ""

@dataclass(frozen=True)
class StartupDecision:
    action: StartupAction
    message: str
    may_mutate: bool

def decide_startup(obs: StartupObservation) -> StartupDecision:
    if not obs.ollama_installed:
        return StartupDecision(StartupAction.BLOCK,
            "Ollama ist nicht installiert.", False)
    if obs.port_busy and not obs.port_owner_is_ollama:
        return StartupDecision(StartupAction.BLOCK,
            "Port 11434 wird von einem fremden Prozess verwendet.", False)
    if obs.api_reachable:
        if not obs.models:
            return StartupDecision(StartupAction.BLOCK,
                "Ollama ist erreichbar, aber kein lokales Modell ist verfügbar.", False)
        return StartupDecision(StartupAction.CONTINUE,
            "Ollama läuft korrekt und wird weiterverwendet.", False)
    if obs.port_busy:
        return StartupDecision(StartupAction.RECOVER_OLLAMA,
            "Ollama belegt Port 11434, antwortet aber nicht korrekt.", True)
    return StartupDecision(StartupAction.START_OLLAMA,
        "Ollama ist installiert, läuft aber nicht.", True)

@dataclass
class StartupHooks:
    observe: Callable[[], StartupObservation]
    start_ollama: Callable[[], None]
    recover_ollama: Callable[[], None]

@dataclass(frozen=True)
class StartupResult:
    ok: bool
    decision: StartupDecision
    final_observation: StartupObservation

def execute_guarded_startup(hooks: StartupHooks) -> StartupResult:
    initial = hooks.observe()
    decision = decide_startup(initial)
    if decision.action is StartupAction.BLOCK:
        return StartupResult(False, decision, initial)
    if decision.action is StartupAction.CONTINUE:
        return StartupResult(True, decision, initial)
    if decision.action is StartupAction.START_OLLAMA:
        hooks.start_ollama()
    elif decision.action is StartupAction.RECOVER_OLLAMA:
        hooks.recover_ollama()
    final = hooks.observe()
    final_decision = decide_startup(final)
    return StartupResult(final_decision.action is StartupAction.CONTINUE,
                         final_decision, final)

def format_startup_status(obs: StartupObservation) -> str:
    models = ", ".join(obs.models) if obs.models else "keine"
    return "\n".join((
        f"Ollama installiert: {'ja' if obs.ollama_installed else 'nein'}",
        f"Port 11434 belegt: {'ja' if obs.port_busy else 'nein'}",
        f"Portbesitzer Ollama: {'ja' if obs.port_owner_is_ollama else 'nein'}",
        f"Ollama API erreichbar: {'ja' if obs.api_reachable else 'nein'}",
        f"Modelle: {models}",
    ))
