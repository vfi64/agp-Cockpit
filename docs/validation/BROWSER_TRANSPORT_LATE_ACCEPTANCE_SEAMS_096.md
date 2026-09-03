# Browser Transport Late-Acceptance Integration Seams 096

Status: accepted
Decision status: accepted
Review policy: on material change

## Purpose

Capture the exact current product seams needed to implement the Step 095 boundary redesign without another symptom-level patch.

## Decision

`REDESIGN_BOUNDARY`

The acknowledgement timeout must become epistemic uncertainty (`INDETERMINATE`) rather than proof of transport failure.

## Required state semantics

```text
WAITING_FOR_ACCEPTANCE
        |
        +-- decisive acceptance evidence --> ACCEPTED
        |
        +-- acknowledgement timeout ------> INDETERMINATE
                                             |
                                             +-- later correlated assistant evidence --> ACCEPTED_LATE
                                             |
                                             +-- positive unsent evidence -----------> SAFE_RETRY_ELIGIBLE
```

## Marker locations

- `SEND_TRANSPORT`: [423, 437, 443, 444, 465, 518, 519, 529, 553, 554, 577, 585]
- `createSendTransport`: [435, 454]
- `async function sendPrompt`: [453]
- `FAILED_CONFIRMATION`: [432, 432, 577]
- `SEND_UNCONFIRMED`: [580, 581]
- `ASSISTANT_RESPONSE_COMPLETE`: [802, 805]
- `submitAssistant`: [657, 698]
- `async function tick`: [724]

## Integration invariants

- No timeout-only transition to FAILED_CONFIRMATION.
- No timeout-only exception that aborts the logical send path.
- Late assistant evidence may resolve a pending indeterminate send.
- A late acceptance must be correlated to the exact pending prompt/turn.
- Retry remains bounded to at most one attempt.
- Existing successful first-send acceptance behavior remains unchanged.
- Terminal mission progression must remain independent from acknowledgement latency.

## Captured functions

- `function createSendTransport`: lines 435-451 (437 chars)
- `async function sendPrompt`: lines 453-591 (4423 chars)
- `async function submitAssistant`: lines 657-695 (1237 chars)
- `async function tick`: lines 724-830 (3213 chars)

Step 096 is evidence-only. It performs no product/test/browser/mission mutation.
