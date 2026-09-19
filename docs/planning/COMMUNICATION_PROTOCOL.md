# AGP Cockpit Communication Protocol
Status: canonical communication authority; complete cross-component lifecycle baseline.

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

## Participants and interfaces

Human owns the overall Task Contract and genuine checkpoints. Cockpit owns durable task/mission lifecycle and enforcement of already-established local authority. Browser/content script owns mechanical observation, framing, native submit and result return. Bridge owns the authenticated transport and Protocol execution boundary. The persisted Local Task Contract is the sole source of local effect/tool/network authority. The local executor executes only authorized work. Agentic Project Kit owns repository/workflow/Git/GitHub semantics when invoked. The Remote LLM produces bounded work orders and completion proposals; it cannot self-grant local authority.

## Event catalogue and layer state

Canonical forward chain:
`TASK_START_REQUEST_ACCEPTED` -> bootstrap prepared -> native submit dispatched ->
`NATIVE_USER_TURN_COMMITTED` -> `NATIVE_SEND_ACCEPTED` -> `MISSION_BOOTSTRAP_SENT` ->
assistant observed/completed -> `TURN_SUBMIT_STARTED_CLIENT` -> work-order parse/validation ->
local Task Contract authorization -> Protocol execution -> authoritative `result_frame` ->
`RESULT_DELIVERED` -> `TURN_SUBMIT_OK` -> continuation or terminal transition.

Mission/task state, start-request generation, content-script attachment generation, browser-message identity, Protocol action identity and executor attempt are correlated but not interchangeable.

## Cross-layer transition table

| From | Required evidence | To | Failure owner |
|---|---|---|---|
| task requested | persisted start request plus accepted identity | bootstrap prepared | task runtime |
| bootstrap prepared | native dispatch plus authoritative user-turn commit | bootstrap sent | browser/native transport |
| bootstrap sent | completed assistant observation | turn submission | browser observation |
| turn submission | valid framed work order | authorization | parser/protocol |
| authorization | persisted Local Task Contract permits effect/tool/network | execution | authority/bridge |
| execution | EXECUTED/REPLAYED plus non-empty authoritative result frame | result delivery | executor/bridge |
| result delivery | delivery acknowledgement | turn committed | browser transport |
| turn committed | continuation or verified terminal proposal | next/terminal | task controller |

Classify failure at the first transition whose required evidence is absent or contradictory.

## Temporal sequence

Human/Cockpit -> Task runtime -> Browser/Content -> Bridge/Authority -> Executor/Kit -> Remote LLM.
The normative order is task/start, native bootstrap send, assistant observation, turn submit, authorization, execution, result delivery, turn acknowledgement, then continuation or terminal transition. Durable state is reconciled before new work after reload/restart.

## Identity and lifetime table

`task_id` is stable across the overall task. `mission_id` identifies a concrete mission execution. Start generation and browser/content generation are distinct epochs. `message_id` identifies a message; resend preserves it. `session_id` scopes a transport session. `round_id` correlates a round. `action_id` identifies the requested effect; same-payload replay must not duplicate it and changed-payload reuse is a violation. `attempt_id` correlates an execution/result attempt where v2 applies. A binding epoch versions task/capability binding and stale epochs are rejected. Reload, bridge restart, browser reattachment or chat switch alone authorize none of these to advance.

## Authorization matrix

Human/persisted Local Task Contract may grant local effect/tool/network authority. Remote LLM work orders may request work but cannot grant authority. Browser/content and Bridge transport/enforce only. Executor cannot widen authority. Kit governs Kit-owned workflow only within supplied local authority. Authorization failure is fail-loud; recovery may repair propagation but must not widen configured authority to make an E2E pass.

## Retry, replay and idempotency

Same `action_id` plus same payload may replay without duplicate effect. Same `action_id` plus changed payload is a protocol violation. A result may be resent with the same message identity without re-execution. A completed assistant response executes at most once for its authoritative identity. Reload/restart reconciles durable state before new dispatch. Unknown effect outcome remains unknown/BLOCKED until reconciled.

## Timeout ownership

Browser observation owns assistant-observation timeout; Bridge owns bounded transport timeout; executor owns local process timeout; Kit owns Kit workflow/gate timeout. Timeout reports the last authoritative completed transition and never by itself authorizes a retry that could duplicate an effect.

## Error taxonomy

`TRANSPORT`: authenticated delivery/browser/native boundary. `FRAME_OR_PARSE`: malformed or semantically invalid frame/work order. `AUTHORIZATION`: persisted Local Task Contract denies requested effect/tool/network. `EXECUTION`: authorized local work fails/times out. `RESULT_DELIVERY`: authoritative result exists but downstream acknowledgement fails. `STATE_DIVERGENCE`: identity/generation/durable/runtime state contradict. `NEEDS_HUMAN`: genuine declared checkpoint. `KIT_BLOCKED`/`KIT_FAIL`: Kit-owned outcome that Cockpit preserves rather than bypasses. Primary classification is the first proven divergent transition.

## Trace-to-spec conformance procedure

For every real acceptance and non-trivial protocol failure: bind all task/mission/generation/message/session/round/action identities and timestamps; reconstruct observed events from durable/runtime evidence; compare each transition with this authority; identify the first missing/contradictory transition; check Local Task Contract authorization; check replay/idempotency before recovery; attribute the owning layer; preserve evidence; repair the smallest coherent owning-layer cause; run focused and broad affected gates; repeat the real browser/remote-LLM E2E; record the trace in `docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md`.

## Current acceptance baseline

Generation 52 proved native bootstrap send and real assistant observation. Its first proven divergence was Local Task Contract authorization after `TURN_SUBMIT_STARTED_CLIENT`. Acceptance of the repair requires repeating the real same-conversation path through authorization, execution, result delivery and `TURN_SUBMIT_OK`. No older Phase-7/8/9 E2E substitutes for this current acceptance.

## Documentation completion status

The complete cross-component communication baseline required for protocol-first engineering is represented by this document together with `docs/planning/PROTOCOL.md`. Future protocol-affecting changes update these authorities, regression invariants and `docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md` in the same coherent slice.

## K07 FILE_TRANSFER — NON-NEGOTIABLE ARCHITECTURE BOUNDARY

This section is normative and overrides legacy text/JSON compatibility behavior for normal task-first K07 `LIVE` + `FULL_AUTO` cycles.

1. The command payload from ChatGPT is exactly one `.py` attachment. The visible assistant prose/text is not the command payload.
2. Cockpit materializes that attachment and sends it through the existing file-loop ingress (`submitAssistantCommandFile` -> `/v1/file-loop/command`).
3. A normal K07 cycle MUST NOT require, parse, repair, or execute a pure-JSON work order from visible ChatGPT text.
4. If the required `.py` attachment is absent, K07 MUST fail loud with `K07_FILE_TRANSFER_ATTACHMENT_REQUIRED`. It MUST NOT send a JSON format-repair prompt.
5. JSON remains permitted only as an internal control/serialization format and for explicitly named legacy/probe compatibility paths. It is not the normal K07 chat payload.
6. Result/continuation transport is file-oriented as defined by the file loop; Protocol-v1 text execution is not a substitute for FILE_TRANSFER.
7. Local Task Contract authority remains authoritative. FILE_TRANSFER cannot widen effect/tool/network/cwd authority. Cockpit is mechanical transport; Kit owns repository/workflow semantics.
8. Acceptance evidence for a normal non-terminal K07 turn is successful file-loop processing (`K07_COMMAND_FILE_TURN_COMPLETE` or its canonical successor), not legacy text-path `TURN_SUBMIT_OK`.
9. Any implementation or test that routes a normal task-first K07 `LIVE` + `FULL_AUTO` response without an attachment into pure-JSON parsing/format repair contradicts this protocol and must fail.

## K07 EXECUTION MAXIME — MINIMAL PROVEN PATH

This section is normative for K07 development and acceptance.

1. Optimize for the shortest authoritative end-to-end chain: create command file -> transfer command file -> execute locally under Local Task Contract -> create result file -> transfer result file.
2. Files are the payload for normal K07 FILE_TRANSFER. Visible chat text, pure JSON work orders, format-repair prompts, and Protocol-v1 text execution are not alternate success paths.
3. Do not add, repair, or activate a fallback merely to bypass a failure in the authoritative path. Fail loud at the first divergent boundary.
4. Proven facts are frozen. Do not rediscover or replace them with assumptions unless new contradictory evidence exists.
5. After every product-code mutation, run the cheapest mechanically relevant integrity gate before E2E (for example JS syntax check, Python compile/test, `git diff --check`, focused regression tests).
6. Run at most one fresh real E2E after those gates pass. Diagnose and repair only its first new divergence.
7. Do not broaden Local Task Contract authority, bypass Kit workflow semantics, manipulate the turn counter, or substitute synthetic/direct execution for real transport evidence.
8. A step should be the largest safe coherent unit: reproduce when necessary, repair the proven defect, run focused gates, then real E2E when justified. Avoid diagnostic-only micro-steps when the repair is mechanically determined.
9. Acceptance is evidence-based: each boundary must be proven by authoritative events/artifacts. UI appearance or absence of an error is not sufficient evidence.
10. If a proposed change increases protocol paths or ambiguity instead of reducing them, stop and justify it against this section before implementation.

## K07 COMMAND-FILE EXECUTION CONTRACT

This section is normative for the local Python work-order boundary.

1. A command attachment must be semantically complete, not merely valid
   Python. The deterministic preflight requires an executable entry point,
   an explicit `__main__` guard, an explicit `--self-test` argument, a
   declared `agentic-kit` command, and a return-bundle writer.
2. A command that fails this contract is rejected before the local runner or
   Kit is invoked. The rejection produces one diagnostic return bundle with
   command-file byte size, line count, SHA-256, interpreter, CWD and runner
   argv.
3. `py_compile` success, `--self-test` exit code 0, or a real-run exit code 0
   alone never proves that the requested work happened. Exactly one valid
   JSON return bundle is required.
4. The execution identity in the return bundle must distinguish the command
   file, interpreter, CWD, argv and return code. Transport hashes prove only
   that the received content was not changed between transport stages; they
   do not prove that the remote model originally generated a complete file.
5. A failed file-loop step may request bounded recovery only while progress is
   still possible. After three consecutive failures with the same failure
   signature and no proven progress, the loop enters terminal `BLOCKED` and
   sends no additional automatic remote turn.
