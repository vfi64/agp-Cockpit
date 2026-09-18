from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.mission_state import (
    MissionState,
    MissionStore,
)
from .mission_state import TERMINAL_STATES, validate_state_transition


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

    def record_browser_transport(self, event: str, details: dict) -> bool:
        """Persist correlated transport observations without changing task authority."""
        allowed = {
            "NATIVE_TRANSPORT_REQUESTED", "NATIVE_SEND_ACCEPTED",
            "NATIVE_TRANSPORT_FAILED", "SEND_INDETERMINATE", "ACCEPTED_LATE",
            "MISSION_BOOTSTRAP_SEND_FAILED", "MISSION_BOOTSTRAP_SENT",
            "EXTENSION_HANDSHAKE",
        }
        state = self.state
        if event not in allowed or state is None:
            return False
        if event != "EXTENSION_HANDSHAKE" and details.get("mission_id") != state.mission_id:
            return False
        state.browser_transport_event = event
        state.browser_transport_note = str(details.get("reason") or details.get("message") or "")[:500]
        if event == "EXTENSION_HANDSHAKE":
            # A fresh extension handshake is the only automatic recovery from
            # a transport block. A native send acknowledgement is not enough:
            # it can come from a stale content script instance.
            version = str(details.get("version") or "").strip()
            if not version:
                return False
            state.browser_transport_blocked = False
            state.browser_transport_block_reason = ""
        elif event in {
            "NATIVE_TRANSPORT_FAILED",
            "SEND_INDETERMINATE",
            "MISSION_BOOTSTRAP_SEND_FAILED",
        }:
            state.browser_transport_blocked = True
            state.browser_transport_block_reason = state.browser_transport_note or event
        self.store.save(state)
        return True

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
        validate_state_transition(state.state, 'RUNNING')
        state.state = 'RUNNING'
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

        next_state = 'WAITING_NEXT_STEP' if state.run_mode == 'SINGLE_STEP' else 'RUNNING'

        validate_state_transition(state.state, next_state)

        state.state = next_state

        self.store.save(state)
        return state

    def final(self, state_name: str, note: str = "") -> MissionState:
        state = self.require_state()
        if state_name not in TERMINAL_STATES:
            raise ValueError(f'final state must be terminal: {state_name}')
        validate_state_transition(state.state, state_name)
        state.state = state_name

        # AGP_TERMINAL_SUMMARY_SEMANTICS_082R1
        if state_name in {"DONE", "NEEDS_HUMAN"}:
            state.last_summary = note
            state.last_error = ""
        else:
            state.last_summary = ""
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
        validate_state_transition(state.state, 'RUNNING')
        state.state = 'RUNNING'
        self.store.save(state)
        return state
