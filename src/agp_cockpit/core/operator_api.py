from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from agp_cockpit.core.bridge_runtime import BridgeRuntime


class OperatorAPI:
    def __init__(self, repository_root: Path) -> None:
        self.runtime = BridgeRuntime(repository_root)

    def status(self) -> dict:
        state = self.runtime.state
        if state is None:
            return {
                "mission": None,
                "state": "IDLE",
            }
        return {
            "mission": asdict(state),
            "state": state.state,
        }

    def create(
        self,
        *,
        title: str,
        mission_text: str,
        execution_mode: str = "DRY_RUN",
        run_mode: str = "SINGLE_STEP",
    ) -> dict:
        state = self.runtime.create_mission(
            title=title,
            mission_text=mission_text,
            execution_mode=execution_mode,
            run_mode=run_mode,
        )
        return asdict(state)

    def resume_next_step(self) -> dict:
        state = self.runtime.resume_next_step()
        return asdict(state)
