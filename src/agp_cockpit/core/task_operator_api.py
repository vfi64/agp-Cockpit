from pathlib import Path
from agp_cockpit.core.task_controller import DurableTaskController
from agp_cockpit.core.file_loop_lifecycle import FileLoopLifecycle
from agp_cockpit.core.operator_control import OperatorControlStore

class TaskOperatorAPI:
    def __init__(self, repository_root: Path, *, task_id: str = "operator-task") -> None:
        self.repository_root = repository_root.expanduser().resolve()
        runtime_root = Path.home()/".local"/"share"/"agp-cockpit"/"runtime"
        runtime_root.mkdir(parents=True, exist_ok=True)
        self.controller = DurableTaskController(task_id, runtime_root/"tasks.sqlite3")
        self.file_loop = FileLoopLifecycle()
        # AGP_K07_UNIFIED_DESKTOP_CONTROL_1007
        self.operator_control = OperatorControlStore(runtime_root)
    def file_loop_status(self) -> dict:
        return self.file_loop.snapshot()
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
    def validate_task_contract(self, payload) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("Task Contract must be a JSON object")
        task_id = str(payload.get("task_id") or "").strip()
        goal = str(payload.get("goal") or "").strip()
        repo = Path(str(payload.get("repository_root") or "")).expanduser().resolve()
        criteria = payload.get("acceptance_criteria")
        if not task_id:
            raise ValueError("task_id required")
        if not goal:
            raise ValueError("goal required")
        if repo != self.repository_root:
            raise ValueError("repository_root does not match current Cockpit repository")
        if not isinstance(criteria, list) or not criteria:
            raise ValueError("acceptance_criteria must be a non-empty list")
        return payload

    def start_task_from_contract(self, payload) -> dict:
        payload = self.validate_task_contract(payload)
        task_id = str(payload["task_id"])
        self.controller.close()
        runtime_root = Path.home()/".local"/"share"/"agp-cockpit"/"runtime"
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
        # Persist configured local authority under the real task identity.
        from agp_cockpit.adapters.macos_settings import settings_path
        from agp_cockpit.settings import load_and_migrate_settings
        settings, _ = load_and_migrate_settings(settings_path())
        self.controller.set_task_authority(
            repository_root=self.repository_root,
            allowed_effects=settings.allowed_effects,
            allowed_tools=settings.allowed_tools,
            allow_network=settings.allow_network,
        )
        self.controller.store.set_states(task_id, state="WAITING_FOR_REMOTE")
        self.file_loop.start()
        return self.status()
