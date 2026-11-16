"""Durable start commit of a standard task.

AGP_DECISION_OVERTAKEN_V1 (workflow-friction plan C7): the panel kept the commit a task
started on only in memory (``_tracked_head``). A question of „Abschließen“ adopted after a
restart (``adopt_pending_decision``) therefore knew no start commit, and the check whether
the question is overtaken could not run. The start commit is now stored per task id in the
runtime folder, written like ``ActiveTaskStore`` (temporary file, then replace).
"""

from __future__ import annotations

import json
from pathlib import Path

FILE_NAME = "task-start-heads.json"
KEEP = 20   # one task runs at a time; a few older entries suffice for adoption


class TaskStartHeadStore:
    def __init__(self, runtime_root: Path) -> None:
        self.path = Path(runtime_root) / FILE_NAME

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def record(self, task_id: str, *, task_key: str, head: str) -> None:
        """Remember ``head`` for ``task_id``; an empty task id or head is not stored."""
        if not task_id or not head:
            return
        data = {key: value for key, value in self._load().items() if key != task_id}
        data[task_id] = {"task_key": str(task_key), "head": str(head)}
        data = dict(list(data.items())[-KEEP:])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def head(self, task_id: str, *, task_key: str = "") -> str:
        """The stored start commit of ``task_id`` (and ``task_key`` when given), or ""."""
        entry = self._load().get(str(task_id or ""))
        if not isinstance(entry, dict):
            return ""
        if task_key and entry.get("task_key") != task_key:
            return ""
        return str(entry.get("head") or "")
