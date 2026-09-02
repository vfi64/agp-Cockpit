from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommunicationMode(str, Enum):
    COPY_PASTE = "copy_paste"
    FILE_TRANSFER = "file_transfer"


class RunState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETE = "complete"


@dataclass(frozen=True)
class CockpitSession:
    repository: str
    mode: CommunicationMode
    state: RunState = RunState.IDLE
