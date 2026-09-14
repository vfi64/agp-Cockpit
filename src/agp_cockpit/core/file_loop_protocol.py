from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re

BEGIN="AGP_COMMAND_FILE_BEGIN"
END="AGP_COMMAND_FILE_END"
DONE="AGP_DONE"
HUMAN="AGP_NEEDS_HUMAN"

class RemoteState(str, Enum):
    COMMAND_FILE="COMMAND_FILE"
    DONE="DONE"
    NEEDS_HUMAN="NEEDS_HUMAN"

@dataclass(frozen=True)
class RemoteReply:
    state: RemoteState
    command_text: str | None = None
    human_reason: str | None = None

def parse_remote_reply(text: str) -> RemoteReply:
    raw=text.strip()
    if raw == DONE:
        return RemoteReply(RemoteState.DONE)
    if raw.startswith(HUMAN):
        reason=raw[len(HUMAN):].strip()
        return RemoteReply(RemoteState.NEEDS_HUMAN,human_reason=reason or None)
    if raw.count(BEGIN)!=1 or raw.count(END)!=1:
        raise ValueError("expected exactly one command-file block or terminal sentinel")
    before,rest=raw.split(BEGIN,1)
    body,after=rest.split(END,1)
    if before.strip() or after.strip():
        raise ValueError("prose outside command-file block is not allowed")
    body=body.strip("\n")
    if not body.strip():
        raise ValueError("empty command file")
    return RemoteReply(RemoteState.COMMAND_FILE,command_text=body+"\n")

def next_step_number(download_dir: Path) -> int:
    nums=[]
    for p in download_dir.iterdir():
        m=re.match(r"^(\d+)_",p.name)
        if m: nums.append(int(m.group(1)))
    return max(nums,default=0)+1

def persist_command(reply: RemoteReply,download_dir: Path,stem: str="remote_command") -> Path:
    if reply.state is not RemoteState.COMMAND_FILE or reply.command_text is None:
        raise ValueError("reply has no command file")
    n=next_step_number(download_dir)
    safe=re.sub(r"[^a-z0-9_]+","_",stem.lower()).strip("_") or "remote_command"
    path=download_dir/f"{n:03d}_{safe}.py"
    path.write_text(reply.command_text,encoding="utf-8")
    return path
