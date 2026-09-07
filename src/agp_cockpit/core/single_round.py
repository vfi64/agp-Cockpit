from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

class RoundState(str, Enum):
    WAITING_FOR_LLM="WAITING_FOR_LLM"
    VALIDATING_TRANSPORT_ENVELOPE="VALIDATING_TRANSPORT_ENVELOPE"
    READY_TO_DISPATCH="READY_TO_DISPATCH"
    EXECUTING_LOCAL_WORK_ORDER="EXECUTING_LOCAL_WORK_ORDER"
    COLLECTING_LOCAL_RESULT="COLLECTING_LOCAL_RESULT"
    PREPARING_RESULT_ENVELOPE="PREPARING_RESULT_ENVELOPE"
    SENDING_RESULT_TO_BROWSER="SENDING_RESULT_TO_BROWSER"
    DONE="DONE"
    BLOCKED_TRANSPORT="BLOCKED_TRANSPORT"
    FAIL_TRANSPORT="FAIL_TRANSPORT"
    USER_STOPPED="USER_STOPPED"

@dataclass(frozen=True)
class SingleRoundOutcome:
    state: RoundState
    action_id: str | None = None
    result: Any = None

class SingleDirectExecutionRound:
    def __init__(self, *, read_completed, parse_action, dispatch, make_result, submit_result, stopped=lambda: False):
        self.read_completed=read_completed; self.parse_action=parse_action; self.dispatch=dispatch
        self.make_result=make_result; self.submit_result=submit_result; self.stopped=stopped
        self.state=RoundState.WAITING_FOR_LLM
    def _stop(self):
        if self.stopped():
            self.state=RoundState.USER_STOPPED
            return True
        return False
    def run(self):
        if self._stop(): return SingleRoundOutcome(self.state)
        text=self.read_completed()
        if self._stop(): return SingleRoundOutcome(self.state)
        self.state=RoundState.VALIDATING_TRANSPORT_ENVELOPE
        try: action=self.parse_action(text)
        except Exception:
            self.state=RoundState.BLOCKED_TRANSPORT
            return SingleRoundOutcome(self.state)
        aid=getattr(action,"action_id",None)
        if getattr(action,"mode",None) not in {"DIRECT_EXECUTION","FILE_TRANSFER"}:
            self.state=RoundState.BLOCKED_TRANSPORT
            return SingleRoundOutcome(self.state,aid)
        if self._stop(): return SingleRoundOutcome(self.state,aid)
        self.state=RoundState.READY_TO_DISPATCH
        try:
            self.state=RoundState.EXECUTING_LOCAL_WORK_ORDER
            local=self.dispatch(action.work_order)
            self.state=RoundState.COLLECTING_LOCAL_RESULT
            framed=self.make_result(action,local)
            self.state=RoundState.PREPARING_RESULT_ENVELOPE
            if self._stop(): return SingleRoundOutcome(self.state,aid,framed)
            self.state=RoundState.SENDING_RESULT_TO_BROWSER
            self.submit_result(framed)
        except Exception as exc:
            self.state=RoundState.FAIL_TRANSPORT
            return SingleRoundOutcome(self.state,aid,exc)
        self.state=RoundState.DONE
        return SingleRoundOutcome(self.state,aid,framed)
