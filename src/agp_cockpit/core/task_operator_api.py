from pathlib import Path

from agp_cockpit.adapters.macos_settings import bridge_runtime_root
from agp_cockpit.core.file_loop_lifecycle import FileLoopLifecycle
from agp_cockpit.core.operator_control import OperatorControlStore
from agp_cockpit.core.task_contract import LocalTaskContract
from agp_cockpit.core.task_controller import DurableTaskController


class TaskOperatorAPI:
    def __init__(self, repository_root: Path, *, task_id: str = "operator-task", local_contract: LocalTaskContract | None = None) -> None:
        self.repository_root = repository_root.expanduser().resolve()
        if local_contract is not None and local_contract.repository_root != self.repository_root:
            raise ValueError("local_contract repository_root does not match TaskOperatorAPI repository")
        self.local_contract = local_contract or LocalTaskContract(self.repository_root)
        runtime_root = bridge_runtime_root()
        runtime_root.mkdir(parents=True, exist_ok=True)
        self.controller = DurableTaskController(task_id, runtime_root/"tasks.sqlite3")
        self.file_loop = FileLoopLifecycle()
        # AGP_K07_UNIFIED_DESKTOP_CONTROL_1007
        self.operator_control = OperatorControlStore(runtime_root)
    def file_loop_status(self) -> dict:
        snapshot = dict(self.file_loop.snapshot())
        control = self.operator_control.current()
        action = str(control.get("action") or "").upper()
        if action == "PAUSE": snapshot["state"] = "PAUSED"
        elif action == "RESUME": snapshot["state"] = "RUNNING"
        elif action == "STOP": snapshot["state"] = "STOPPED"
        snapshot["generation"] = max(int(snapshot.get("generation", 0)), int(control.get("generation", 0)))
        return snapshot
    def file_loop_pause(self) -> dict:
        snapshot = self.file_loop.pause()
        self.operator_control.request('PAUSE')
        return snapshot
    def file_loop_resume(self) -> dict:
        snapshot = self.file_loop.resume()
        self.operator_control.request('RESUME')
        return snapshot
    def file_loop_stop(self) -> dict:
        snapshot = self.file_loop.stop()
        self.operator_control.request('STOP')
        return snapshot
    def file_loop_reset(self) -> dict:
        return self.file_loop.reset()
    def status(self) -> dict:
        s=dict(self.controller.snapshot); s["repository_root"]=str(self.repository_root); return s
    def pause(self) -> dict:
        self.controller.pause(); return self.status()
    def resume(self) -> dict:
        self.controller.resume(); return self.status()
    def approve_checkpoint(self) -> dict:
        s=self.status(); ident=(s.get("checkpoint_id"),s.get("checkpoint_revision"),s.get("checkpoint_artifact_hash"))
        if not all(ident): raise RuntimeError("no pending human checkpoint")
        self.controller.approve_human_checkpoint(*ident); return self.status()
    def prepare_task_contract(self, payload) -> dict:
        if not isinstance(payload, dict):
            raise TypeError("Task Contract must be an object")
        prepared = dict(payload)
        goal = str(prepared.get("goal") or "").strip()
        if not goal:
            raise ValueError("goal required")
        supplied_repo = str(prepared.get("repository_root") or "").strip()
        if supplied_repo and Path(supplied_repo).expanduser().resolve() != self.repository_root:
            raise ValueError("repository_root does not match current Cockpit repository")
        if not str(prepared.get("task_id") or "").strip():
            import uuid
            prepared["task_id"] = "cockpit-" + uuid.uuid4().hex
        prepared["repository_root"] = str(self.repository_root)
        criteria = prepared.get("acceptance_criteria")
        if criteria is None:
            prepared["acceptance_criteria"] = []
        elif not isinstance(criteria, list):
            raise ValueError("acceptance_criteria must be a list")
        return prepared

    def validate_task_contract(self, payload) -> dict:
        return self.prepare_task_contract(payload)

    def start_task_from_contract(self, payload) -> dict:
        payload = self.prepare_task_contract(payload)
        task_id = str(payload["task_id"])
        self.controller.close()
        runtime_root = bridge_runtime_root()
        runtime_root.mkdir(parents=True, exist_ok=True)
        self.controller = DurableTaskController(task_id, runtime_root/"tasks.sqlite3")
        scope = {
            "title": payload.get("title"),
            "acceptance_criteria": payload.get("acceptance_criteria") or [],
            "constraints": payload.get("constraints") or [],
            "human_checkpoints": payload.get("human_checkpoints") or [],
            "completion_contract": payload.get("completion_contract") or {},
        }
        self.controller.store.set_runtime_contract(
            task_id,
            goal=str(payload["goal"]),
            scope=scope,
            deadline_utc=payload.get("deadline_utc"),
        )
        # Persist exactly the application-established authority under the real task identity.
        self.controller.set_task_authority(
            repository_root=self.local_contract.repository_root,
            allowed_effects=self.local_contract.allowed_effects,
            allowed_tools=self.local_contract.allowed_tools,
            allow_network=self.local_contract.allow_network,
        )
        # Operator controls are durable evidence for the previous task. A
        # newly accepted task must start from a clean running control state;
        # otherwise a stale STOP would immediately terminate every retry.
        self.operator_control.request("RESUME")
        self.controller.store.set_states(task_id, state="WAITING_FOR_REMOTE")
        self.file_loop.start()
        return self.status()
