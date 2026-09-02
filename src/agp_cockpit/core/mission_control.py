from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


FINAL_STATES = {
    "DONE",
    "NEEDS_HUMAN",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class MissionSignal:
    state: str
    summary: str
    details: dict[str, Any]


def parse_mission_signal(text: str) -> MissionSignal | None:
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None

    try:
        data: Any = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    state = data.get("mission_state")
    if not isinstance(state, str):
        return None

    state = state.strip().upper()
    if state not in FINAL_STATES:
        return None

    summary = data.get("summary", "")
    if not isinstance(summary, str):
        raise ValueError("mission summary must be a string")

    return MissionSignal(
        state=state,
        summary=summary,
        details=data,
    )
