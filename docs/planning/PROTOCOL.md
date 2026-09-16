# AGP Cockpit Protocol

Status: active
Status-date: 2026-09-09
Decision status: accepted
Current deployed protocol: V1
Target task-runtime protocol: V2

## 1. Version decision

V1 remains frozen for legacy sessions. Current V1 strictly validates exact
fields and protocol_version=1. The v2 task runtime requires additional
causality, binding, contract and separated-result semantics; therefore these
fields must not be silently injected into V1 frames.

S1 reserves protocol version 2 for the new task runtime. S2 may narrow the
schema, but may not redefine V1 meaning.

## 2. Frame families

Keep:
- ACTION
- RESULT
- CONTROL

Task contract/checkpoint/context-refresh data may be typed CONTROL payloads.
Observations belong in RESULT. A Remote-LLM decision has no execution effect
until it arrives as a validated ACTION.

## 3. Required v2 correlation

Target frames carry where applicable:
- protocol_version;
- message_id;
- task_id;
- contract_hash;
- binding_epoch;
- parent_message_id/predecessor;
- round_id;
- action_id;
- attempt_id for result correlation;
- expected_execution_revision.

ACTION carries requested capabilities/effects and work-order payload.

RESULT separates:
- transport/delivery status;
- execution status;
- Kit evidence/status when applicable;
- evidence/artifact references;
- reconciliation state where applicable.

CONTROL covers at least:
- capability/task binding handshake;
- completion proposal;
- pause/resume;
- context/binding handoff.

## 4. Invariants

- only complete, exactly framed messages are parsed;
- prose outside a frame is not executable authority;
- same action_id + changed payload is a protocol violation;
- duplicate same-payload ACTION causes no second effect;
- stale binding_epoch is rejected;
- predecessor/correlation mismatch is rejected;
- logs/files/evidence cannot become a new ACTION;
- acknowledgement confirms only its defined delivery step;
- late/stale replies after resume/chat switch do not execute.

## 5. Result semantics

V1 `transport_status` currently conflates local failure with transport FAIL.
V2 represents these independently. A failed script/test can therefore be
delivered successfully and keep the same task alive.

## 6. Completion semantics

Remote COMPLETE is a typed completion proposal, not terminal authority.
The controller verifies the current completion contract.

## 7. Delivery and replay

Incoming and outgoing v2 messages are durable before their corresponding
next-stage transition. After restart, reconcile Inbox/Outbox before dispatching
new work. Resending a result uses the same message identity and never
re-executes the action.

No silent downgrade of an active v2 task to V1 is allowed.

<!-- AGP_COMMUNICATION_PROTOCOL_AUTHORITY_V1 -->
## Communication protocol authority
Cross-component Cockpit communication/lifecycle semantics are governed by `docs/planning/COMMUNICATION_PROTOCOL.md` together with `docs/planning/PROTOCOL.md`. Protocol-affecting changes require synchronized authority, tests/invariants, and durable change/failure history; failure analysis follows `docs/engineering/FAILURE_META_ANALYSIS.md`.
