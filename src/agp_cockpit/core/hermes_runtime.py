from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.hermes_config import (
    DEFAULT_HERMES_CONFIG,
    HermesConfigInfo,
    read_hermes_config,
)
from agp_cockpit.core.runtime import ExecutableInfo, find_executable


@dataclass(frozen=True)
class HermesRuntimeInfo:
    executable: ExecutableInfo
    config: HermesConfigInfo
    configured_model_available: bool | None


def discover_hermes_runtime(
    *,
    ollama_models: tuple[str, ...] = (),
    config_path: Path = DEFAULT_HERMES_CONFIG,
) -> HermesRuntimeInfo:
    executable = find_executable(
        "hermes",
        extra_candidates=(
            "~/.local/bin/hermes",
            "/opt/homebrew/bin/hermes",
            "/usr/local/bin/hermes",
        ),
    )

    config = read_hermes_config(
        config_path,
        known_models=ollama_models,
    )

    if config.model is None:
        available = None
    else:
        available = config.model in ollama_models

    return HermesRuntimeInfo(
        executable=executable,
        config=config,
        configured_model_available=available,
    )
