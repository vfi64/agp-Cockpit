# AGP Cockpit Architecture v2

Status: active
Status-date: 2026-09-09
Decision status: accepted
ADR: `docs/architecture/ADR-0003-persistent-remote-llm-task-runtime.md`

## 1. Architectural decision

AGP Cockpit uses one deterministic Task Controller as the sole authoritative
task-state machine. Tkinter, browser scripts and adapters may expose/transport
state but may not independently decide task continuation.

## 2. Ownership

Remote Development LLM:
- development planning;
- semantic diagnosis;
- code/patch decision;
- next requested action within the Task Contract.

Task Controller:
- state transitions;
- dispatch locks;
- action/message correlation;
- persistence ordering;
- budgets;
- checkpoint/suspension handling;
- reconciliation state;
- completion verification.

Task Store:
- atomic local durable task state;
- event/action/attempt/message/evidence records;
- contract versions;
- binding epochs;
- approvals and budgets.

Browser adapter:
- explicit conversation binding;
- complete-frame transport;
- delivery observation.
It does not own task continuation.

Executor/Policy:
- path/tool/process/network/capability enforcement;
- no autonomous repair or permission expansion.

Kit:
- governed repository lifecycle and Kit semantics.

Evidence/Verifier:
- provenance, integrity, revision/artifact binding and completeness.
It does not judge subjective product quality.

Tkinter:
- task creation/status, pause/resume/stop and checkpoints.

## 3. Durable storage

Target store: SQLite with explicit schema versioning and transactions, stored
under platform Application Support outside repository and Dropbox/File
Provider synchronization. Start with one writer and durable synchronization;
WAL is optional later based on measured need.

## 4. Task contract

Before first effect, persist:
- task_id and contract_version;
- original goal and acceptance criteria;
- repository identity and expected context;
- allowed capabilities/effect classes;
- human checkpoints;
- completion contract;
- budgets/deadlines;
- remote binding;
- contract hash.

## 5. State model

TransportState:
`READY`, `WAITING`, `DISCONNECTED`, `IDENTITY_BLOCKED`.

ExecutionState:
`NOT_STARTED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `TIMED_OUT`,
`OUTCOME_UNKNOWN`.

Kit result evidence:
`PASS`, `BLOCKED`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`.

TaskState:
`CREATED`, `READY`, `AWAITING_REMOTE`, `VALIDATING_ACTION`, `EXECUTING`,
`DELIVERING_RESULT`, `RECONCILING`, `VERIFYING_COMPLETION`, `PAUSING`,
`SUSPENDED`, `CANCELLING`, `VERIFIED_COMPLETE`, `CANCELLED`, `FAILED_FINAL`.

Suspension reasons:
`WAITING_FOR_HUMAN`, `USER_PAUSED`, `BUDGET_EXHAUSTED`, `STALLED`,
`WAITING_FOR_SERVICE`, `SAFETY_BLOCK`, `OUTCOME_UNKNOWN`, `STORAGE_BLOCKED`.

A known nonzero command return code normally means healthy transport,
`ExecutionState=FAILED`, and a task that delivers evidence and returns to
remote reasoning. It does not mean task failure.

## 6. Dispatch order

1. Persist incoming message.
2. Validate binding, predecessor, contract, capabilities and budgets.
3. Persist action, attempt and dispatch intent atomically.
4. Start the controlled effect.
5. Secure raw result and deterministic/redacted evidence.
6. Persist result, budget use, task transition and outgoing message.
7. Deliver persisted outgoing message and record delivery observation.

A crash between durable dispatch intent and durable result can yield
OUTCOME_UNKNOWN.

## 7. Duplicate/retry contract

- same action_id + same payload -> prior result/status; no new dispatch;
- same action_id + changed payload -> protocol violation;
- repaired command -> new action_id referencing predecessor;
- new action_id cannot bypass an unresolved predecessor;
- OUTCOME_UNKNOWN -> reconcile first;
- retry only where retry contract and fresh policy permit it.

## 8. Reconciliation

Allowed conclusions:
`CONFIRMED_APPLIED`, `CONFIRMED_NOT_APPLIED`, `STILL_UNKNOWN`.

For Kit actions, reconciliation uses current supported Kit surfaces. Cockpit
does not recreate missing Kit lifecycle behavior.

## 9. Evidence recipes

Versioned deterministic families:
`COMMAND_NONZERO`, `KIT_RESULT`, `TEST_RESULT`, `TIMEOUT`,
`TRANSPORT_INTERRUPTION`.

Raw observation, normalized evidence and Remote-LLM interpretation remain
separate.

## 10. Browser binding and remote continuity

Canonical task state lives locally, not solely in browser history. Each binding
has a binding_epoch. Late frames from older epochs never regain execution
authority.

## 11. Completion

`COMPLETE_PROPOSAL -> VERIFYING_COMPLETION`.

Missing or stale evidence produces `COMPLETE_REJECTED`. Only valid evidence
for the current contract and revision/artifact chain yields
`VERIFIED_COMPLETE`.

## 12. Migration from current runtime

Reusable foundations:
- strict V1 frame parsing;
- IDs and duplicate concepts;
- browser binding/transport;
- Phase7 result return;
- Phase8 pause/resume/stop and multi-round behavior;
- executor and Kit pass-through;
- Mission/Operator UI concepts;
- settings/logging/packaging.

Known semantic replacements:
- `protocol_execution_v1.py` currently maps failed local execution to
  transport FAIL; v2 separates transport and execution status.
- `phase8_multi_round.js` currently stops on `BLOCKED`/`FAIL`; the new
  controller owns continuation.
- `ActionRegistry` is in-memory; S3 replaces this authority with durable
  action/attempt records.
- `MissionStore` stores JSON snapshots under repository `.local`; S3 migrates
  durable task authority to Application Support.
- existing Mission state names are legacy and must not coexist as a second
  authoritative task state machine once the new controller activates.

Legacy migration occurs only at a proven quiescent point.
\n## 13. Production runtime isolation\n\nThe production desktop bridge stores runtime identity and token under platform Application Support, outside the repository and Dropbox/File Provider synchronization. Temporary/pytest roots are test-only through explicit injection. Production rejects transient runtime roots before binding. Test-owned bridges must stop during teardown. A stale or foreign listener must not be silently accepted merely because the TCP port is occupied. Authentication remains mandatory.\n