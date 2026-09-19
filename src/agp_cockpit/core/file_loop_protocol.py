from __future__ import annotations
import re
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
DONE="AGP_DONE"; HUMAN="AGP_NEEDS_HUMAN"
class RemoteState(str,Enum):
    COMMAND_FILE="COMMAND_FILE"; DONE="DONE"; NEEDS_HUMAN="NEEDS_HUMAN"; BLOCKED="BLOCKED"
@dataclass(frozen=True)
class RemoteReply:
    state:RemoteState; command_file:Path|None=None; human_reason:str|None=None
def parse_terminal_reply(text:str)->RemoteReply:
    raw=text.strip()
    if raw==DONE:return RemoteReply(RemoteState.DONE)
    if raw.startswith(HUMAN):
        reason=raw[len(HUMAN):].strip()
        return RemoteReply(RemoteState.NEEDS_HUMAN,human_reason=reason or None)
    raise ValueError("remote prose is not executable; expected a .py command attachment or terminal sentinel")
def next_step_number(download_dir:Path)->int:
    nums=[]
    for p in download_dir.iterdir():
        m=re.match(r"^(\d+)_",p.name)
        if m:nums.append(int(m.group(1)))
    return max(nums,default=0)+1
def accept_command_file(source:Path,download_dir:Path,stem:str="remote_command")->Path:
    source=source.expanduser().resolve()
    if not source.is_file() or source.suffix.lower()!=".py":raise ValueError("remote command attachment must be one existing .py file")
    n=next_step_number(download_dir);safe=re.sub(r"[^a-z0-9_]+","_",stem.lower()).strip("_") or "remote_command"
    target=download_dir/f"{n:03d}_{safe}.py"
    if source==target.resolve():return target
    shutil.copyfile(source,target);return target
