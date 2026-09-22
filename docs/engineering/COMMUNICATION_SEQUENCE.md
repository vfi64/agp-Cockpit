# AGP Cockpit Communication Sequence

This is the normative planning view for the normal LIVE/FULL_AUTO K07 file loop.
The sequence is intentionally explicit about the evidence that must exist before
the next remote turn is allowed.

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Cockpit as AGP Cockpit
    participant Bridge as Local Bridge
    participant Ext as Chrome Extension
    participant Chat as ChatGPT DOM
    participant Runner as Download/run_next.py
    participant Kit as agentic-kit
    participant Handoff as latest handoff package
    participant Log as bridge.log

    User->>Cockpit: Start standard task
    Cockpit->>Bridge: POST /v1/mission
    Bridge-->>Cockpit: READY + mission_id + identity
    Ext->>Bridge: EXTENSION_HANDSHAKE(version, build_id, page_url)
    Bridge->>Log: EXTENSION_HANDSHAKE + identity
    Cockpit->>Ext: start request / bootstrap
    Ext->>Chat: Insert and submit bootstrap prompt
    Ext->>Bridge: MISSION_BOOTSTRAP_SENT
    Bridge->>Log: MISSION_BOOTSTRAP_SENT

    Chat-->>Ext: Assistant response with one .py file card
    Ext->>Log: K07_ASSISTANT_ATTACHMENT_OBSERVED
    Ext->>Ext: Read the visible file card and materialize content
    Ext->>Bridge: POST /v1/file-loop/command
    Bridge->>Log: K07_COMMAND_ACCEPTED + command_sha256
    Bridge->>Runner: Execute exactly once with next number
    Runner->>Kit: Execute authorized argv in repository cwd
    Kit-->>Runner: rc + bounded stdout/stderr
    Runner-->>Bridge: exactly one return bundle + run_next output
    Bridge->>Log: K07_RESULT_BUNDLE_CREATED + hashes + validation
    Bridge-->>Ext: result_file + continuation prompt + cycle_id
    Ext->>Log: K07_FILE_INGRESS_ACCEPTED
    Ext->>Chat: Attach result evidence and send continuation
    Ext->>Bridge: CONTINUATION_SENT
    Bridge->>Log: CONTINUATION_SENT
    Ext->>Chat: Observe the next complete assistant response

    alt Missing, stale, duplicate, or malformed evidence
        Bridge->>Log: explicit failure event and reason
        Bridge-->>Ext: BLOCKED or bounded recovery
        Ext->>Chat: no blind replay
    else Operator stop or timeout
        User->>Cockpit: Stop
        Cockpit->>Bridge: STOP
        Bridge->>Runner: terminate process group
        Bridge->>Log: STOP_REQUESTED + process_stop evidence
        Ext->>Log: K07_ASSISTANT_WAIT_TIMEOUT or K07_FILE_INGRESS_FAILED
    end
```

## Acceptance Invariants

- The visible extension version and build identity match the staged extension.
- A Python file card is sufficient terminal evidence for the remote response; the
  loop does not wait for unrelated prose stability.
- `K07_COMMAND_ACCEPTED` precedes local execution and includes the command hash.
- `K07_RESULT_BUNDLE_CREATED` includes return-bundle and runner-output paths,
  hashes, byte validation, return status, and execution identity.
- The turn counter advances only after the bridge accepts the command-file result.
- `CONTINUATION_SENT` is emitted only after result evidence is attached.
- A timeout or stop leaves a structured diagnostic record and never becomes an
  uncaught browser promise rejection.
- Each diagnostic event carries application version, bridge build, extension
  version, extension build, mission id, conversation URL, run generation, and
  client turn where available.

## Failure Reading Guide

The first missing event identifies the boundary that failed:

| Last event | Interpretation |
| --- | --- |
| `MISSION_BOOTSTRAP_SENT` | ChatGPT did not yield an accepted new response or the DOM observer missed it. |
| `K07_ASSISTANT_ATTACHMENT_OBSERVED` | The file card was found, but fetch or bridge ingress failed. |
| `K07_COMMAND_ACCEPTED` | Local execution, `run_next.py`, or result validation failed. |
| `K07_RESULT_BUNDLE_CREATED` | Browser result transport or continuation submission failed. |
| `CONTINUATION_SENT` | The next remote response is the remaining boundary. |
| `K07_ASSISTANT_WAIT_TIMEOUT` | No new assistant response arrived before the bounded wait; the run is terminal and must not replay automatically. |
