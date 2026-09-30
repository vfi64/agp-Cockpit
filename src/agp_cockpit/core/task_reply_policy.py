"""Which terminal replies the remote side may give, per task.

AGP_TASK_REPLY_POLICY_V1
Three concerns are kept apart:

* the task definition (standard_tasks.py) says what the task must achieve;
* this policy says how the remote may end a turn for that task;
* the transport (orchestrator, extension, bridge) only applies the policy.

Live 2026-09-30: after D4 every prompt offered a terminal DONE file. In a chat
that had already completed "Chat wechseln", the remote answered the new
bootstrap with DONE instead of a work order, so no local run, no handoff files
and no run_next output were produced. A task whose completion is verified
locally must never be offered a remote DONE: only a work order, or
NEEDS_HUMAN when a genuine human decision is required.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplyPolicy:
    remote_done_allowed: bool


# Generic missions (tab "Arbeiten") have no local verifier; the remote may end them.
GENERIC = ReplyPolicy(remote_done_allowed=True)
# Tasks with a local completion contract end only through local verification.
LOCALLY_VERIFIED = ReplyPolicy(remote_done_allowed=False)


def policy_for(completion_contract_active: bool) -> ReplyPolicy:
    return LOCALLY_VERIFIED if completion_contract_active else GENERIC


def terminal_reply_instruction(step: int, policy: ReplyPolicy) -> str:
    if policy.remote_done_allowed:
        return (
            "If the task is finished, or a human decision is required, attach instead exactly one "
            f"file named {step}_agp_terminal.json containing only "
            '{"state": "DONE" or "NEEDS_HUMAN", "reason": "<evidence-backed reason>"}. '
            "A prose-only reply is not read by the Cockpit.\n"
        )
    return (
        "Completion of this task is verified locally by the Cockpit; never declare it DONE. "
        "Return the next Python work order. Only if a genuine human decision is required, "
        f"attach instead exactly one file named {step}_agp_terminal.json containing only "
        '{"state": "NEEDS_HUMAN", "reason": "<the decision required>"}. '
        "A prose-only reply is not read by the Cockpit.\n"
    )
