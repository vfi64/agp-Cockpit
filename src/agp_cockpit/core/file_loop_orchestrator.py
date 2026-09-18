from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .file_loop_protocol import RemoteState, accept_command_file, parse_terminal_reply
from .file_loop_runner import FileLoopRun, execute_with_run_next

CONTINUATION_TEXT="Attached is the result file. Evaluate it and continue the current task. Return exactly one Python command file if more local work is required; otherwise finish or request human input."
REPLAY_CONTINUATION_TEXT="This command file was already executed and is being replayed idempotently. Read the attached existing result file; do not return the same command again. Continue the current task or finish."
RECOVERY_CONTINUATION_PREFIX="""The attached local execution evidence reports a FAILED command-file step.
Recovery is required. Do not claim that the requested Kit operation ran successfully.
Read both attached files completely: the canonical return bundle and the immutable step-scoped run_next log.
If the failure is a syntax/compile failure, the real run was never reached and no Kit command was executed.
Return exactly one newly numbered Python command file that corrects the diagnosed failure.
The replacement file must execute the intended local work during its real run and create exactly one canonical return bundle.
The return-bundle file must contain exactly one parseable JSON object; do not append shell output, ACK text, or diagnostics to that file.
Do not return prose, a JSON command description, or the same broken file. Do not bypass the local runner, Kit gates, or evidence requirements.
"""
@dataclass(frozen=True)
class LoopOutcome:
    state:RemoteState;run:FileLoopRun|None=None;human_reason:str|None=None;continuation_text:str|None=None
    replayed:bool=False
def _load(path:Path)->dict:
    if not path.exists():return {}
    data=json.loads(path.read_text(encoding="utf-8"));return data if isinstance(data,dict) else {}
def _save(path:Path,data:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
def _continuation_for_run(run:FileLoopRun)->str:
    try:
        result=json.loads(run.return_bundle.read_text(encoding="utf-8"))
    except (OSError,UnicodeDecodeError,json.JSONDecodeError):
        result={}
    failed=result.get("status")=="failed" or run.artifact_kind=="execution_diagnostic"
    if not failed:
        return CONTINUATION_TEXT
    reason=str(result.get("failure_reason") or "local execution evidence is incomplete")
    return (RECOVERY_CONTINUATION_PREFIX
        + f"Failure reason: {reason}\n"
        + f"Runner return code: {result.get('runner_returncode', run.runner_returncode)}\n"
        + f"Command file: {run.command_file}\n")
def consume_command_file(source:Path,root:Path,state_file:Path,stem:str="remote_command")->LoopOutcome:
    source=source.expanduser().resolve();fp=hashlib.sha256(source.read_bytes()).hexdigest();state=_load(state_file)
    if state.get("last_command_sha256")==fp:
        result_path = Path(str(state.get("return_bundle") or ""))
        if not result_path.is_file():
            raise RuntimeError("duplicate remote command file has no preserved result bundle")
        result = _load(result_path)
        run = FileLoopRun(
            step=int(state.get("step", 0)),
            command_file=source,
            return_bundle=result_path,
            run_next_output=Path(str(state.get("run_next_output") or (root / "Download" / "__run_next_output.txt"))),
            runner_returncode=int(result.get("runner_returncode", 0)),
            stdout=str(result.get("stdout", "") or ""),
            stderr=str(result.get("stderr", "") or ""),
            artifact_kind=str(result.get("artifact_kind", "return_bundle") or "return_bundle"),
        )
        return LoopOutcome(
            RemoteState.COMMAND_FILE,
            run=run,
            continuation_text=REPLAY_CONTINUATION_TEXT,
            replayed=True,
        )
    command=accept_command_file(source,root/"Download",stem);run=execute_with_run_next(root,command)
    _save(state_file,{"last_command_sha256":fp,"step":run.step,"return_bundle":str(run.return_bundle),"run_next_output":str(run.run_next_output),"artifact_kind":run.artifact_kind,"command_file":str(run.command_file)})
    return LoopOutcome(RemoteState.COMMAND_FILE,run=run,continuation_text=_continuation_for_run(run))
def consume_terminal_reply(text:str,state_file:Path)->LoopOutcome:
    reply=parse_terminal_reply(text);state=_load(state_file);fp=hashlib.sha256(text.encode()).hexdigest()
    if state.get("last_terminal_sha256")==fp:raise RuntimeError("duplicate remote terminal reply refused")
    _save(state_file,{"last_terminal_sha256":fp,"terminal":reply.state.value})
    return LoopOutcome(reply.state,human_reason=reply.human_reason)
