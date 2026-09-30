from __future__ import annotations

import json
from pathlib import Path


class StartRequestStore:
    def __init__(self,root:Path)->None:
        self.path=root/'task_start_request.json'; self.path.parent.mkdir(parents=True,exist_ok=True)
    def _read(self)->dict:
        try: return json.loads(self.path.read_text(encoding='utf-8'))
        except (FileNotFoundError,json.JSONDecodeError): return {'generation':0,'mission_id':'','task_id':''}
    def request(self,mission_id:str,*,task_id:str='')->dict:
        cur=self._read(); data={
            'generation':int(cur.get('generation',0))+1,
            'mission_id':str(mission_id),
            'task_id':str(task_id),
        }
        tmp=self.path.with_suffix('.tmp'); tmp.write_text(json.dumps(data)+'\n',encoding='utf-8'); tmp.replace(self.path); return data
    def current(self)->dict: return self._read()
    def pending(self)->dict:
        """Expose only an actionable request to browser pollers."""
        data=self._read()
        if not str(data.get('mission_id') or '').strip():
            return {'generation':0,'mission_id':'','task_id':''}
        return data
    def invalidate_pending(self)->dict:
        """Invalidate a request from an earlier bridge lifetime or stopped run."""
        cur=self._read()
        data={
            'generation':int(cur.get('generation',0)),
            'mission_id':'',
            'task_id':'',
        }
        tmp=self.path.with_suffix('.tmp'); tmp.write_text(json.dumps(data)+'\n',encoding='utf-8'); tmp.replace(self.path); return data


class ActiveTaskStore:
    """Durable mission-to-task binding of the running mission.

    AGP_K07_ACTIVE_TASK_BINDING_V1: the start request is a one-shot trigger
    and is invalidated as soon as the browser accepts it. Task identity (and
    with it the task's completion contract) must survive that invalidation
    for the whole mission; it is only ever used for the mission it names.
    """

    @staticmethod
    def _empty() -> dict:
        return {"generation": 0, "mission_id": "", "task_id": ""}

    def __init__(self, root: Path) -> None:
        self.path = root / "active_task_binding.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def bind(self, mission_id: str, task_id: str, generation: int) -> dict:
        data = {"generation": int(generation), "mission_id": str(mission_id), "task_id": str(task_id)}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data) + "\n", encoding="utf-8")
        tmp.replace(self.path)
        return data

    def current(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return self._empty()
        return data if isinstance(data, dict) else self._empty()

    def for_mission(self, mission_id: str) -> dict:
        data = self.current()
        if mission_id and str(data.get("mission_id") or "") == str(mission_id) and str(data.get("task_id") or "").strip():
            return data
        return self._empty()


def resolve_task_binding(root: Path, mission_id: str | None) -> dict:
    """Pending start request if it names a task, else the mission's durable binding."""
    start = StartRequestStore(root).current()
    if str(start.get("task_id") or "").strip():
        return start
    return ActiveTaskStore(root).for_mission(str(mission_id or ""))
