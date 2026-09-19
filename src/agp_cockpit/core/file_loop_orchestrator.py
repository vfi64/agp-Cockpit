from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .file_loop_protocol import RemoteState, accept_command_file, parse_terminal_reply
from .file_loop_runner import FileLoopRun, execute_with_run_next

MAX_CONSECUTIVE_FAILURES = 3
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


def _result_for_run(run: FileLoopRun) -> dict:
    try:
        result = json.loads(run.return_bundle.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return result if isinstance(result, dict) else {}


def _failure_signature(result: dict, run: FileLoopRun) -> str:
    payload = {
        "status": result.get("status"),
        "failure_reason": result.get("failure_reason"),
        "artifact_kind": run.artifact_kind,
        "runner_returncode": result.get("runner_returncode", run.runner_returncode),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
def consume_command_file(source:Path,root:Path,state_file:Path,stem:str="remote_command")->LoopOutcome:
    source=source.expanduser().resolve();fp=hashlib.sha256(source.read_bytes()).hexdigest();state=_load(state_file)
    history = state.get("command_history", [])
    if not isinstance(history, list):
        history = []
    previous = next(
        (entry for entry in reversed(history) if isinstance(entry, dict) and entry.get("sha256") == fp),
        None,
    )
    if previous is None and state.get("last_command_sha256") == fp:
        previous = state
    if previous is not None:
        result_path = Path(str(previous.get("return_bundle") or ""))
        if not result_path.is_file():
            raise RuntimeError("duplicate remote command file has no preserved result bundle")
        result = _load(result_path)
        run = FileLoopRun(
            step=int(previous.get("step", 0)),
            command_file=source,
            return_bundle=result_path,
            run_next_output=Path(str(previous.get("run_next_output") or (root / "Download" / "__run_next_output.txt"))),
            runner_returncode=int(result.get("runner_returncode", 0)),
            stdout=str(result.get("stdout", "") or ""),
            stderr=str(result.get("stderr", "") or ""),
            artifact_kind=str(result.get("artifact_kind", "return_bundle") or "return_bundle"),
        )
        return LoopOutcome(
            RemoteState.BLOCKED if previous.get("state") == RemoteState.BLOCKED.value else RemoteState.COMMAND_FILE,
            run=run,
            continuation_text=None if previous.get("state") == RemoteState.BLOCKED.value else REPLAY_CONTINUATION_TEXT,
            human_reason=(str(previous.get("human_reason")) if previous.get("state") == RemoteState.BLOCKED.value else None),
            replayed=True,
        )
    command=accept_command_file(source,root/"Download",stem);run=execute_with_run_next(root,command)
    result = _result_for_run(run)
    failed = result.get("status") == "failed" or run.artifact_kind == "execution_diagnostic"
    consecutive_failures = int(state.get("consecutive_failures", 0) or 0)
    failure_signature = str(state.get("last_failure_signature", "") or "")
    if failed:
        current_signature = _failure_signature(result, run)
        consecutive_failures = consecutive_failures + 1 if current_signature == failure_signature else 1
        failure_signature = current_signature
    else:
        consecutive_failures = 0
        failure_signature = ""
    terminal_blocked = failed and consecutive_failures >= MAX_CONSECUTIVE_FAILURES
    human_reason = (
        f"file-loop blocked after {consecutive_failures} consecutive failures without proven progress"
        if terminal_blocked else None
    )
    record={"sha256":fp,"step":run.step,"return_bundle":str(run.return_bundle),"run_next_output":str(run.run_next_output),"artifact_kind":run.artifact_kind,"command_file":str(run.command_file),"state":RemoteState.BLOCKED.value if terminal_blocked else RemoteState.COMMAND_FILE.value,"human_reason":human_reason}
    history = (history + [record])[-16:]
    persisted={"last_command_sha256":fp,"step":run.step,"return_bundle":str(run.return_bundle),"run_next_output":str(run.run_next_output),"artifact_kind":run.artifact_kind,"command_file":str(run.command_file),"command_history":history,"consecutive_failures":consecutive_failures,"last_failure_signature":failure_signature,"state":RemoteState.BLOCKED.value if terminal_blocked else RemoteState.COMMAND_FILE.value,"human_reason":human_reason}
    _save(state_file,persisted)
    if terminal_blocked:
        return LoopOutcome(
            RemoteState.BLOCKED,
            run=run,
            human_reason=human_reason,
            continuation_text=None,
        )
    return LoopOutcome(RemoteState.COMMAND_FILE,run=run,continuation_text=_continuation_for_run(run))
def consume_terminal_reply(text:str,state_file:Path)->LoopOutcome:
    reply=parse_terminal_reply(text);state=_load(state_file);fp=hashlib.sha256(text.encode()).hexdigest()
    if state.get("last_terminal_sha256")==fp:raise RuntimeError("duplicate remote terminal reply refused")
    _save(state_file,{"last_terminal_sha256":fp,"terminal":reply.state.value})
    return LoopOutcome(reply.state,human_reason=reply.human_reason)
