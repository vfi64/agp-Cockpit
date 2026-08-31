# AGP Cockpit Transport Protocol v1 — Planning Specification

Status: design baseline, not yet implementation authority

## 1. Purpose

The protocol creates a deterministic handoff between a browser-based reasoning LLM and the local AGP Cockpit. It deliberately avoids requiring a local LLM to interpret natural language.

## 2. Envelope framing

Assistant-to-cockpit actions are transported inside exactly one bounded block:

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

The implementation must reject:

- missing begin/end markers;
- nested markers;
- multiple action blocks in one assistant response unless a later protocol version explicitly permits batching;
- truncated payloads;
- unsupported protocol versions;
- duplicate action IDs already executed or in-flight;
- payloads exceeding configured size limits.

## 3. Serialization

The first implementation should use JSON for transport envelopes because it is ubiquitous, strict, readily validated, and avoids YAML ambiguity. Human-readable summaries may remain plain text fields.

Representative action shape:

```json
{
  "protocol_version": 1,
  "session_id": "...",
  "round_id": "...",
  "action_id": "...",
  "mode": "DIRECT_EXECUTION",
  "repository": {
    "path_hint": "/path/on/local-machine",
    "remote": "vfi64/example",
    "expected_branch": "...",
    "expected_head": "..."
  },
  "payload": {
    "kind": "kit_command",
    "command": "..."
  },
  "expectation": {
    "terminal": false
  }
}
```

Representative result shape:

```json
{
  "protocol_version": 1,
  "session_id": "...",
  "round_id": "...",
  "action_id": "...",
  "status": "PASS",
  "repository_observed": {
    "remote": "vfi64/example",
    "branch": "...",
    "head": "..."
  },
  "execution": {
    "return_code": 0,
    "summary": "...",
    "log_ref": "..."
  }
}
```

Exact schemas will be versioned in code and machine-readable schema files once implementation begins.

## 4. Communication modes

### DIRECT_EXECUTION

The remote LLM provides one complete bounded action. The cockpit validates envelope identity and delegates execution to the configured executor/Kit adapter.

DIRECT_EXECUTION is not authorization to run arbitrary compensating commands. If an action returns `BLOCKED` or `FAIL`, the cockpit returns that result and waits for the remote LLM.

### FILE_TRANSFER

The payload expresses structured intent and references the canonical Kit transfer mechanism. The cockpit delegates generation/validation/transfer to the current Kit interface and tracks the exact correlation/order identity.

No transfer YAML is synthesized by the cockpit from memory.

## 5. Status values

Protocol v1 recognizes:

- `PASS`
- `BLOCKED`
- `FAIL`
- `DONE`
- `CANCELLED`

`DONE` is a terminal declaration for the user-level task/session and must be explicit. Absence of another action is not sufficient to infer DONE.

## 6. Repository identity

Before local execution, the cockpit verifies the selected repository against available expectations. Any mismatch in explicit remote/branch/head preconditions becomes BLOCKED.

Head preconditions may intentionally be omitted when the requested action is expected to observe current state rather than mutate from a fixed head. The protocol schema must distinguish `not specified` from wildcard acceptance.

## 7. Idempotency and replay

`action_id` is globally unique within the persisted cockpit history relevant to recovery.

Rules:

1. a received duplicate action ID with identical payload is not re-executed; the persisted result is re-surfaced if safely available;
2. a duplicate action ID with different payload is a protocol violation and BLOCKED;
3. an action left in ambiguous `EXECUTING` state after crash is not replayed automatically;
4. recovery requires evidence to establish whether execution completed.

## 8. Browser response completion

The browser adapter determines message completion using browser-level evidence. The protocol parser runs only after the adapter reports a completed assistant response.

The core must never parse a streaming partial response.

## 9. Bounded output

Result envelopes should contain concise diagnostic material. Large stdout/stderr is stored locally as evidence/log and referenced by path/identifier. The remote LLM may subsequently request a bounded excerpt through a new action.

## 10. Forward compatibility

Unknown protocol versions are rejected rather than guessed. Optional fields must be explicitly versioned/schema-defined. Semantic changes require a protocol-version increment or a backward-compatible schema change with tests.
