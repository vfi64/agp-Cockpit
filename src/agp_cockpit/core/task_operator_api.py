from pathlib import Path
from agp_cockpit.core.task_controller import DurableTaskController

class TaskOperatorAPI:
    def __init__(self, repository_root: Path, *, task_id: str = "operator-task") -> None:
        self.repository_root = repository_root.expanduser().resolve()
        runtime_root = Path.home()/".local"/"share"/"agp-cockpit"/"runtime"
        runtime_root.mkdir(parents=True, exist_ok=True)
        self.controller = DurableTaskController(task_id, runtime_root/"tasks.sqlite3")
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
