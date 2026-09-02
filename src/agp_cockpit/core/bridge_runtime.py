from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.mission_state import (
    MissionState,
    MissionStore,
)


@dataclass
class BridgeRuntime:
    repository_root: Path

    def __post_init__(self) -> None:
        self.repository_root = self.repository_root.resolve()
        self.store = MissionStore(self.repository_root)
        self.state = self.store.load_current()

    def require_state(self) -> MissionState:
        if self.state is None:
            raise RuntimeError("no active mission")
        return self.state

    def create_mission(
        self,
        *,
        title: str,
        mission_text: str,
        execution_mode: str = "DRY_RUN",
        run_mode: str = "SINGLE_STEP",
    ) -> MissionState:
        self.state = self.store.create(
            title=title,
            mission_text=mission_text,
            execution_mode=execution_mode,
            run_mode=run_mode,
        )
        return self.state

    def set_modes(
        self,
        *,
        execution_mode: str | None = None,
        run_mode: str | None = None,
    ) -> MissionState:
        state = self.require_state()

        if execution_mode is not None:
            state.execution_mode = execution_mode
        if run_mode is not None:
            state.run_mode = run_mode

        state.validate()
        self.store.save(state)
        return state

    def mark_running(self) -> MissionState:
        state = self.require_state()
        state.state = "RUNNING"
        self.store.save(state)
        return state

    def record_assistant(self, text: str) -> MissionState:
        state = self.require_state()
        state.last_assistant_text = text
        state.turn_count += 1
        self.store.save(state)
        return state

    def record_step_result(
        self,
        *,
        result: str,
        prompt: str,
        passed: bool,
    ) -> MissionState:
        state = self.require_state()
        state.last_result = result
        state.last_prompt = prompt
        state.step_count += 1

        if state.run_mode == "SINGLE_STEP":
            state.state = "WAITING_NEXT_STEP"
        else:
            state.state = "RUNNING" if passed else "RUNNING"

        self.store.save(state)
        return state

    def final(self, state_name: str, note: str = "") -> MissionState:
        state = self.require_state()
        state.state = state_name
        state.last_error = note
        self.store.save(state)
        return state

    def resume_next_step(self) -> MissionState:
        state = self.require_state()
        if state.run_mode != "SINGLE_STEP":
            raise RuntimeError(
                "resume_next_step requires SINGLE_STEP run mode"
            )
        if state.state != "WAITING_NEXT_STEP":
            raise RuntimeError(
                f"mission is not waiting for next step: {state.state}"
            )
        state.state = "RUNNING"
        self.store.save(state)
        return state
