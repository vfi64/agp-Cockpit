from __future__ import annotations

import json
from pathlib import Path

class OperatorControlStore:
    """Monotonic bridge authority for live browser-loop controls."""
    def __init__(self, runtime_root: Path) -> None:
        self.path = Path(runtime_root) / "operator-control.json"

    def current(self) -> dict:
        if not self.path.exists(): return {"generation": 0, "action": ""}
        try: data=json.loads(self.path.read_text(encoding="utf-8"))
        except Exception: return {"generation": 0, "action": ""}
        return {"generation": int(data.get("generation",0)), "action": str(data.get("action",""))}

    def request(self, action: str) -> dict:
        action=str(action).upper().strip()
        if action not in {"PAUSE","RESUME","STOP"}: raise ValueError("operator action must be PAUSE, RESUME, or STOP")
        cur=self.current(); nxt={"generation": int(cur["generation"])+1, "action": action}
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(nxt,sort_keys=True),encoding="utf-8"); tmp.replace(self.path)
        return nxt
