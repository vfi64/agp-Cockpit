from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock


class FileLoopState(str,Enum):
    IDLE="IDLE"; RUNNING="RUNNING"; PAUSED="PAUSED"; STOPPED="STOPPED"
@dataclass
class FileLoopLifecycle:
    state: FileLoopState=FileLoopState.IDLE
    generation: int=0
    def __post_init__(self): self._lock=RLock()
    def snapshot(self):
        with self._lock: return {"state":self.state.value,"generation":self.generation}
    def start(self):
        with self._lock:
            self.generation+=1; self.state=FileLoopState.RUNNING; return self.snapshot()
    def pause(self):
        with self._lock:
            if self.state is FileLoopState.RUNNING: self.state=FileLoopState.PAUSED
            return self.snapshot()
    def resume(self):
        with self._lock:
            if self.state is FileLoopState.PAUSED: self.state=FileLoopState.RUNNING
            return self.snapshot()
    def stop(self):
        with self._lock:
            self.generation+=1; self.state=FileLoopState.STOPPED; return self.snapshot()
    def reset(self):
        with self._lock:
            self.generation+=1; self.state=FileLoopState.IDLE; return self.snapshot()
    def may_start_next_turn(self,g):
        with self._lock: return self.state is FileLoopState.RUNNING and self.generation==g
