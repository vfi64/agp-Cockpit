# Phase 8 Acceptance — Automated Multi-Round Bridge

**Status:** PASS  
**Date:** 2026-09-07

## Accepted scope

Phase 8 provides a bounded automated multi-round browser/local bridge while preserving the existing Phase 5 conversation-safety contract and the Phase 7 single-round transport/execution boundary.

Canonical runtime sequence:

`STABLE FRAME -> ACTION EXECUTE -> RESULT SEND -> STABLE FRAME -> ACTION | DONE`

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| P8-01 bounded maximum rounds | PASS | deterministic stress; real-browser `maxRounds=1` ended at `1 / 40` with `MAX_ROUNDS_REACHED` |
| P8-02 pause | PASS | deterministic stress harness |
| P8-03 stop | PASS | deterministic stress harness |
| P8-04 duplicate protection | PASS | Protocol-v1 replay/idempotency regression |
| P8-05 browser timeout | PASS | timeout contract + deterministic stress |
| P8-06 process timeout | PASS | operator/process-timeout acceptance path |
| P8-07 explicit browser-LLM DONE | PASS | DONE-control tests + real-browser E2E-5 |
| P8-08 same mechanical round trip | PASS | consolidated state machine + real-browser E2E-5 |

## Real-browser evidence

### E2E-5 — multi-round DONE

Session: `phase8-e2e5-20260907-13`

1. Round 1 executed locally and returned `transport_status=PASS`; stdout marker `AGP_PHASE8_E2E5_ROUND1_OK`.
2. A fresh Round-2 ACTION was consumed automatically.
3. Round 2 executed locally and returned `transport_status=PASS`; stdout marker `AGP_PHASE8_E2E5_ROUND2_OK`.
4. Browser LLM emitted explicit Protocol-v1 `CONTROL DONE`.
5. Final overlay: `Turns 2 / 40`, `Phase 8: DONE (2 rounds)`, `Last event: PHASE8_DONE`.
6. No third local dispatch was observed.

### Live round counter

Session: `phase8-counter-e2e-20260907-14`

With `maxRounds=1`, one local execution returned PASS and the overlay ended at:

- `Turns 1 / 40`
- `Phase 8: MAX_ROUNDS_REACHED (1 rounds)`
- `Last event: PHASE8_MAX_ROUNDS_REACHED`

No `UI_ACTION_ERROR` was present.

## Regression evidence

The closeout reruns the complete `test_phase8_*.py` surface together with the Phase-7 browser bridge controller tests, Protocol-v1 transport tests, available execution/runner tests, `agentic-kit check`, and `git diff --check`.

## Architectural closeout

The initial-streaming race was removed by consolidating initial and subsequent browser frames onto the same stable protocol waiter. Phase 8 does not duplicate Phase-7 transport. Live UI progress is emitted through an optional callback isolated from the transport state machine.

**Phase 8: COMPLETE.**
