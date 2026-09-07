# AGP Cockpit Transport Protocol v1 — Planning Specification

Status: active
Status-date: 2026-08-31
Decision status: accepted
Review policy: on material change

## 1. Purpose

The protocol provides deterministic framing between a browser-based development LLM and the local AGP Cockpit.

AGP Cockpit transports work orders and results. It does not interpret development semantics, choose Kit commands, or implement Agentic Project Kit workflow logic.

## 2. Envelope framing

Assistant-to-cockpit work orders use exactly one bounded block:

```text
AGP_COCKPIT_ACTION_BEGIN
<UTF-8 protocol document>
AGP_COCKPIT_ACTION_END
```

Cockpit-to-assistant results use:

```text
AGP_COCKPIT_RESULT_BEGIN
<UTF-8 protocol document>
AGP_COCKPIT_RESULT_END
```

Reject missing/nested/multiple markers, truncated payloads, unsupported protocol versions, duplicate action IDs, and oversized payloads.

## 3. Serialization

Protocol v1 should use JSON.

Representative action:

```json
{
  "protocol_version": 1,
  "session_id": "...",
  "round_id": "...",
  "action_id": "...",
  "mode": "DIRECT_EXECUTION",
  "target": {
    "repository_path_hint": "/path/on/local-machine",
    "remote_hint": "vfi64/example"
  },
  "work_order": {
    "type": "terminal_payload",
    "content": "<opaque work order from browser LLM>"
  }
}
```

Representative result:

```json
{
  "protocol_version": 1,
  "session_id": "...",
  "round_id": "...",
  "action_id": "...",
  "transport_status": "PASS",
  "local_execution": {
    "return_code": 0,
    "bounded_output": "...",
    "log_ref": "..."
  }
}
```

`work_order.content` is opaque to AGP Cockpit except for transport-size/safety constraints. The Cockpit must not rewrite, improve, repair, summarize, or replace it.

### Session-control frame

Assistant-to-cockpit session control is distinct from the two communication modes. Protocol v1 uses exactly one bounded control block:

```text
AGP_COCKPIT_CONTROL_BEGIN
{"protocol_version":1,"session_id":"...","round_id":"...","control":"DONE"}
AGP_COCKPIT_CONTROL_END
```

`DONE` is a browser-LLM declaration. It causes no local dispatch and does not inspect or reinterpret `work_order`; therefore it is not a third communication mode. The session ID must correlate with the active multi-round session.

## 4. Communication modes

### DIRECT_EXECUTION

The browser LLM supplies one complete local work order. The Cockpit validates only transport metadata and dispatches the work order unchanged to the configured local executor.

The Cockpit does not choose a Kit command or compensating command. If the local work order invokes Agentic Project Kit, the Kit owns the governed work.

### FILE_TRANSFER

FILE_TRANSFER changes only the semantic intention of the browser-LLM work order; it does not give the Cockpit additional workflow responsibility.

The browser LLM supplies a complete local work order that invokes the current canonical Agentic Project Kit FILE_TRANSFER workflow.

The Cockpit then only:

1. dispatches that work order unchanged;
2. waits for the local process to complete;
3. captures bounded output/result references;
4. returns them to the browser LLM.

The Cockpit MUST NOT implement or interpret:

- transfer-order generation/validation;
- inbox/outbox semantics;
- GitHub publishing/fetching;
- remote visibility checks;
- remote waiting/retry policy;
- correlation/order tracking inside the Kit transfer workflow;
- result association;
- Kit PASS/BLOCKED/FAIL workflow semantics.

Those are Agentic Project Kit responsibilities.

## 5. Transport status values

Protocol-level transport status may include:

- `PASS` — payload/result transport step completed;
- `BLOCKED` — transport cannot proceed safely;
- `FAIL` — unexpected transport/infrastructure failure;
- `DONE` — browser LLM explicitly declares the user-level transport session finished;
- `CANCELLED` — user stopped the local bridge.

These are Cockpit transport statuses. Kit output may itself contain `PASS`, `BLOCKED`, or `FAIL`; the Cockpit transports that content without diagnosing or resolving it.

## 6. Target identity

Before local dispatch, the Cockpit may verify explicitly supplied local target/repository identity constraints to avoid executing in the wrong location.

Identity verification is transport safety, not development reasoning.

## 7. Idempotency and replay

`action_id` identifies a transport dispatch.

1. identical duplicate action ID: do not dispatch twice; safely re-surface persisted result when available;
2. same action ID with different payload: protocol violation;
3. ambiguous in-flight state after crash: no automatic replay;
4. recovery stops or requests a new browser-LLM/user decision when safe local evidence is insufficient.

The Cockpit must not inspect Kit-internal transfer state to infer replay safety.

## 8. Browser response completion

The browser adapter reports completed assistant responses using browser-level evidence. The protocol parser never consumes a streaming partial response.

## 9. Bounded output

Large terminal output is stored locally and referenced. The result envelope contains bounded output or evidence references sufficient for the browser LLM to decide the next work order.

## 10. Scope rule

A protocol field is invalid for v1 if its purpose is to make AGP Cockpit plan development, select Kit commands, manage GitHub workflow, or model Agentic Project Kit FILE_TRANSFER internals.

Unknown protocol versions are rejected rather than guessed.
