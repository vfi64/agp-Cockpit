# AGP Cockpit Communication Protocol
Status: canonical communication authority; detailed reconstruction is mandatory and ongoing.

This document complements `docs/planning/PROTOCOL.md`: that file defines Protocol-v1 frame semantics; this file governs the complete cross-component Cockpit communication/lifecycle protocol.

## Layers
Track separately: mission lifecycle; start-request generation/latch; content-script lifecycle; native browser send; conversation observation; turn submission; Protocol-v1 execution; local Task Contract authorization; result delivery/ack; reload/recovery/idempotency.

## Identities
Track where applicable `mission_id`, `task_id`, start generation, run/content generation, turn, step, `message_id`, `session_id`, `round_id`, `action_id`, correlation IDs, and reload/attachment lifetime. They are not interchangeable.

## Normative high-level sequence
MISSION/READY → task-start persisted/accepted → bootstrap prepared → native submit dispatched → authoritative user-turn commit → native send accepted → MISSION_BOOTSTRAP_SENT → assistant observed/completed → TURN_SUBMIT_STARTED_CLIENT → work-order parse/validation → local Task Contract authorization → Protocol-v1 execution → authoritative result_frame → RESULT_DELIVERED → TURN_SUBMIT_OK → continuation or terminal transition.

## Invariants
Reload does not silently create or duplicate mission/task/generation/action/execution. A completed assistant response executes at most once for its identity. Remote work-order content never self-grants authority. No Protocol-v1 action bypasses the local Task Contract. Success requires authoritative commit/result evidence. BLOCKED/FAIL/NEEDS_HUMAN are not bypassed. Contradictory state fails loud.

## Failure analysis
Classify at the first failed transition. State recovery ownership and which identities retry/reuse/advance. Absence of a success event alone does not identify root cause.

## Verified Generation 52 trace — 2026-09-16
Start accepted → native bootstrap send succeeded → real assistant response observed → TURN_SUBMIT_STARTED_CLIENT → TICK_ERROR `PermissionError: ACTION_NOT_AUTHORIZED_BY_LOCAL_TASK_CONTRACT`; mission remained READY, turn 0, step 0.
Current first proven divergence: local Task Contract authorization after turn submission starts. This is not a native-composer failure.

Before repair, reconstruct work-order shape → Protocol-v1 action mapping → local Task Contract/effect/tool/network authority → executor boundary → failure/recovery semantics.

## Required completion
Maintain participant/interface and event catalogues; per-layer state tables; cross-layer transition table; temporal sequence diagrams; identity/lifetime table; authorization matrix; retry/idempotency matrix; timeout ownership; error taxonomy; trace-to-spec conformance procedure.
