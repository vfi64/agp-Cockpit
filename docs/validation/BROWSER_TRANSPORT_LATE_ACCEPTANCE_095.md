# Browser Transport Late-Acceptance Analysis 095

Status: accepted
Decision status: accepted
Review policy: on material change

## Scope

Forensic analysis of the real Step 093 Chrome/ChatGPT/Cockpit LIVE round trip after the Browser Sender state-machine refactor.

## Result

Classification: `FALSE_NEGATIVE_CONFIRMATION`

The second prompt was recorded as `FAILED_CONFIRMATION`, but subsequent durable evidence proves that ChatGPT received it and produced the expected terminal assistant response. The server then accepted that response and the mission ended `DONE`.

This means the current state machine conflates two different facts:

1. confirmation was not observed inside the acknowledgement window;
2. the send actually failed.

The Step 093 evidence proves that these are not equivalent.

## Evidence

Mission state: `DONE`
Turn count: `2`
Step count: `1`
Last error: ``
Last summary: `093 live browser transport state-machine confirmation completed`

`FAILED_CONFIRMATION` positions: `[27]`

Late-success findings:

```json
[
  {
    "failed_confirmation_index": 27,
    "failed_confirmation_details": {
      "retry_count": 0,
      "state": "FAILED_CONFIRMATION",
      "via": "timeout"
    },
    "assistant_response_complete_index": 35,
    "turn_submit_started_index": 37,
    "turn_submit_ok_index": 38,
    "done_index": 39,
    "late_success_after_failed_confirmation": true
  }
]
```

Retry attempted: `False`

## Architectural conclusion

`FAILED_CONFIRMATION` is too strong for an acknowledgement timeout.

The transport boundary should model acknowledgement timeout as:

```text
WAITING_FOR_ACCEPTANCE
        |
        +-- decisive acceptance evidence --> ACCEPTED
        |
        +-- acknowledgement timeout ------> INDETERMINATE
                                             |
                                             +-- later assistant edge --> ACCEPTED_LATE
                                             |
                                             +-- positive unsent evidence --> SAFE_RETRY_ELIGIBLE
```

The state `FAILED_CONFIRMATION` should be reserved for cases where the transport has positive evidence that confirmation failed, not merely the absence of timely acknowledgement.

## Decision

`REDESIGN_BOUNDARY`

Do not apply another local retry/DOM heuristic patch.

The next product step should change transport semantics so that timeout becomes `INDETERMINATE`, and later assistant activity can retrospectively establish acceptance.

## Guardrail

Retry remains bounded and is allowed only when there is positive evidence that the exact pending prompt is still unsent.

Step 095 is evidence-only and performs no browser action, mission mutation, product mutation, test mutation, commit, push, or Kit repair.
