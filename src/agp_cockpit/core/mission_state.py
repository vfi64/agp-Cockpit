from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid
from typing import Any


VALID_EXECUTION_MODES = {"DRY_RUN", "LIVE"}
VALID_RUN_MODES = {"FULL_AUTO", "SINGLE_STEP"}
VALID_STATES = {
    "IDLE",
    "READY",
    "RUNNING",
    "WAITING_NEXT_STEP",
    "DONE",
    "NEEDS_HUMAN",
    "BLOCKED",
    "FAILED",
    "STOPPED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()



TERMINAL_STATES = frozenset({'DONE', 'FAILED', 'NEEDS_HUMAN', 'STOPPED'})
ALLOWED_STATE_TRANSITIONS = {
    'READY': frozenset({'RUNNING', 'DONE', 'FAILED', 'NEEDS_HUMAN'}),
    'RUNNING': frozenset({'RUNNING', 'WAITING_NEXT_STEP', 'DONE', 'FAILED', 'NEEDS_HUMAN', 'STOPPED'}),
    'WAITING_NEXT_STEP': frozenset({'RUNNING'}),
}


def validate_state_transition(previous_state: str, next_state: str) -> None:
    if previous_state not in VALID_STATES:
        raise ValueError(f'invalid previous state: {previous_state}')
    if next_state not in VALID_STATES:
        raise ValueError(f'invalid next state: {next_state}')
    if next_state not in ALLOWED_STATE_TRANSITIONS.get(previous_state, frozenset()):
        raise ValueError(f'illegal mission state transition: {previous_state} -> {next_state}')


@dataclass
class MissionState:
    schema_version: int = 1
    mission_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    repository_root: str = ""
    title: str = ""
    mission_text: str = ""
    execution_mode: str = "DRY_RUN"
    run_mode: str = "SINGLE_STEP"
    state: str = "IDLE"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    turn_count: int = 0
    step_count: int = 0
    last_result: str = ""
    # AGP_TERMINAL_SUMMARY_SEMANTICS_082R1
    last_summary: str = ""
    last_error: str = ""
    last_prompt: str = ""
    last_assistant_text: str = ""
    browser_transport_event: str = ""
    browser_transport_note: str = ""
    browser_transport_blocked: bool = False
    browser_transport_block_reason: str = ""
    browser_transport_recovery_attempts: int = 0

    def validate(self) -> None:
        if self.execution_mode not in VALID_EXECUTION_MODES:
            raise ValueError(
                f"invalid execution_mode: {self.execution_mode}"
            )
        if self.run_mode not in VALID_RUN_MODES:
            raise ValueError(f"invalid run_mode: {self.run_mode}")
        if self.state not in VALID_STATES:
            raise ValueError(f"invalid state: {self.state}")
        if not self.repository_root:
            raise ValueError("repository_root must not be empty")

    def touch(self) -> None:
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionState":
        state = cls(**data)
        state.validate()
        return state


class MissionStore:
    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        self.root = (
            self.repository_root
            / ".local"
            / "agp-cockpit"
            / "missions"
        )
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_path = self.root / "current.json"

    def save(self, state: MissionState) -> Path:
        state.validate()
        state.touch()

        target = self.root / f"{state.mission_id}.json"
        payload = (
            json.dumps(
                state.to_dict(),
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )

        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(target)

        current_tmp = self.current_path.with_suffix(".json.tmp")
        current_tmp.write_text(payload, encoding="utf-8")
        current_tmp.replace(self.current_path)

        return target

    def load_current(self) -> MissionState | None:
        if not self.current_path.exists():
            return None
        data = json.loads(
            self.current_path.read_text(encoding="utf-8")
        )
        return MissionState.from_dict(data)

    def create(
        self,
        *,
        title: str,
        mission_text: str,
        execution_mode: str = "DRY_RUN",
        run_mode: str = "SINGLE_STEP",
    ) -> MissionState:
        state = MissionState(
            repository_root=str(self.repository_root),
            title=title.strip(),
            mission_text=mission_text.strip(),
            execution_mode=execution_mode,
            run_mode=run_mode,
            state="READY",
        )
        self.save(state)
        return state
