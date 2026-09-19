from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_HERMES_CONFIG = Path("~/.hermes/config.yaml").expanduser()

CANONICAL_MODEL_PATHS: tuple[tuple[str, ...], ...] = (
    ("model", "default"),
    ("model",),
    ("model", "name"),
    ("model", "model"),
    ("model", "id"),
    ("llm", "model"),
    ("inference", "model"),
)

SECONDARY_MODEL_PATH_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("custom_providers",),
    ("stt",),
)

MODEL_KEY_HINTS = (
    "model",
    "model_name",
    "model_id",
    "default_model",
    "default",
)


@dataclass(frozen=True)
class HermesConfigInfo:
    path: Path
    exists: bool
    model: str | None
    model_path: tuple[str, ...] | None
    error: str | None = None


def _value_at_path(data: Any, path: tuple[str, ...]) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _walk_strings(
    data: Any,
    *,
    path: tuple[str, ...] = (),
) -> Iterable[tuple[tuple[str, ...], str]]:
    if isinstance(data, dict):
        for key, value in data.items():
            yield from _walk_strings(
                value,
                path=path + (str(key),),
            )
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from _walk_strings(
                value,
                path=path + (str(index),),
            )
    elif isinstance(data, str) and data.strip():
        yield path, data.strip()


def _is_secondary_model_path(path: tuple[str, ...]) -> bool:
    return any(
        path[:len(prefix)] == prefix
        for prefix in SECONDARY_MODEL_PATH_PREFIXES
    )


def detect_model_path(
    data: Any,
    *,
    known_models: tuple[str, ...] = (),
) -> tuple[tuple[str, ...] | None, str | None]:
    canonical_matches: list[tuple[tuple[str, ...], str]] = []

    for path in CANONICAL_MODEL_PATHS:
        value = _value_at_path(data, path)
        if isinstance(value, str) and value.strip():
            canonical_matches.append((path, value.strip()))

    if canonical_matches:
        # Priority order above is intentional: model.default wins.
        preferred_path, preferred_value = canonical_matches[0]

        # Other canonical paths may only coexist if they resolve to the same model.
        conflicting = [
            (path, value)
            for path, value in canonical_matches[1:]
            if value != preferred_value
        ]
        if conflicting:
            raise ValueError(
                "Hermes config contains conflicting canonical model fields"
            )

        return preferred_path, preferred_value

    if not known_models:
        return None, None

    known = set(known_models)
    inferred: list[tuple[tuple[str, ...], str]] = []

    for path, value in _walk_strings(data):
        if value not in known:
            continue
        if not path:
            continue
        if _is_secondary_model_path(path):
            continue

        key = path[-1].casefold()
        parent = path[-2].casefold() if len(path) > 1 else ""

        plausible = (
            key in MODEL_KEY_HINTS
            or "model" in key
            or "model" in parent
        )
        if plausible:
            inferred.append((path, value))

    deduplicated: list[tuple[tuple[str, ...], str]] = []
    seen = set()
    for item in inferred:
        if item not in seen:
            seen.add(item)
            deduplicated.append(item)

    if len(deduplicated) == 1:
        return deduplicated[0]

    if len(deduplicated) > 1:
        raise ValueError(
            "Hermes config contains multiple plausible primary model fields; "
            "refusing ambiguous inference"
        )

    return None, None


def read_hermes_config(
    path: Path = DEFAULT_HERMES_CONFIG,
    *,
    known_models: tuple[str, ...] = (),
) -> HermesConfigInfo:
    path = path.expanduser()

    if not path.exists():
        return HermesConfigInfo(
            path=path,
            exists=False,
            model=None,
            model_path=None,
        )

    try:
        data = yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:  # noqa: BLE001 - parser diagnostics are returned to the UI.
        return HermesConfigInfo(
            path=path,
            exists=True,
            model=None,
            model_path=None,
            error=f"YAML could not be read: {exc}",
        )

    try:
        model_path, model = detect_model_path(
            data,
            known_models=known_models,
        )
    except ValueError as exc:
        return HermesConfigInfo(
            path=path,
            exists=True,
            model=None,
            model_path=None,
            error=str(exc),
        )

    return HermesConfigInfo(
        path=path,
        exists=True,
        model=model,
        model_path=model_path,
    )
