from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from agp_cockpit.core.mission_state import (
    MissionState,
    MissionStore,
)

from .mission_state import TERMINAL_STATES, validate_state_transition


@dataclass
class BridgeRuntime:
    repository_root: Path
    _execution_stop: Callable[[], dict[str, object]] | None = field(
        default=None,
        repr=False,
    )
    last_execution_stop: dict[str, object] | None = field(
        default=None,
        init=False,
    )

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
        conversation_url: str = "",
        execution_mode: str = "DRY_RUN",
        run_mode: str = "SINGLE_STEP",
    ) -> MissionState:
        self.state = self.store.create(
            title=title,
            mission_text=mission_text,
            conversation_url=conversation_url.strip(),
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
            "COMPOSER_MODEL_VERIFIED", "COMPOSER_MODEL_NOT_VERIFIED",
            "COMPOSER_MODEL_RECOVERY_EXHAUSTED",
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
            "COMPOSER_MODEL_RECOVERY_EXHAUSTED",
        } and str(details.get("failure_class") or "") != "COMPOSER_MODEL_NOT_VERIFIED":
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

    def bind_execution_stop(
        self,
        stop_callback: Callable[[], dict[str, object]],
    ) -> None:
        """Bind the process authority used before a mission is marked stopped."""
        self._execution_stop = stop_callback

    def record_assistant(self, text: str) -> MissionState:
        state = self.require_state()
        state.last_assistant_text = text
        state.turn_count += 1
        self.store.save(state)
        return state

    def record_local_step(self) -> MissionState:
        """Count one newly executed local command file (never a replay).

        AGP_K07_STEP_COUNT_V1: the file loop executes steps without
        record_step_result, so step_count stayed 0 in live runs.
        """
        state = self.require_state()
        state.step_count += 1
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

    def stop(self, note: str = "Stopped by operator") -> MissionState:
        """Stop owned execution, then persist the operator stop.

        Standalone state-only runtimes may omit the callback. The production
        Bridge binds it to ``RunNextProcessController.stop`` so this method
        cannot claim a K07 stop before the local process authority has acted.
        """
        state = self.require_state()
        self.last_execution_stop = (
            self._execution_stop() if self._execution_stop is not None else None
        )
        if state.state in TERMINAL_STATES:
            return state
        return self.final("STOPPED", note)

    def stop_stale_on_desktop_start(self) -> MissionState | None:
        """Start without an active mission from an older app run.

        Mission evidence remains persisted in its per-mission state file. The
        current pointer is cleared so a browser reconnect cannot present an
        old STOPPED/READY mission as the fresh desktop state.
        """
        state = self.state
        if state is None or state.state in TERMINAL_STATES:
            self.store.clear_current()
            self.state = None
            return state

        stopped = self.stop("Stopped during desktop startup; explicit restart required")
        self.store.clear_current()
        self.state = None
        return stopped

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
