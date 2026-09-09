# ADR-0003 — Persistent Remote-LLM Task Runtime

Status: Accepted
Date: 2026-09-09
Decision owner: Maintainer

## Context

The existing product already provides browser transport, strict V1 framing,
single/multi-round execution, duplicate concepts, pause/stop foundations,
Mission/Operator concepts, Kit pass-through, desktop packaging and local
extension staging.

Current `protocol_execution_v1.py` maps a failed local process to transport
FAIL, and the Phase8 browser loop terminates on BLOCKED/FAIL. This prevents a
larger Remote-LLM development task from surviving ordinary local failures.

## Decision

1. Remote Development LLM remains sole development reasoning authority.
2. Cockpit becomes deterministic durable Task Controller.
3. Decision Authority D0/D1/D2 is independent of Effect Class E0-E4.
4. Transport, execution, Kit result and task status are separate.
5. Local execution failure is evidence, not automatic task termination.
6. SQLite is target durable store for S3.
7. OUTCOME_UNKNOWN forbids blind replay and requires reconciliation.
8. Kit remains repository-lifecycle authority; no bypass.
9. Remote COMPLETE is a proposal; only verifier yields VERIFIED_COMPLETE.
10. Canonical task context is local and survives chat changes via binding epochs.
11. Budgets and deterministic no-progress detection bound autonomy.
12. Hermes/local LLM is outside critical correctness path.
13. V1 remains frozen; target runtime reserves protocol V2.
14. One controller replaces, not supplements, legacy continuation ownership.

## Consequences

The product can recover across ordinary failures and later self-host more of
its own development, but durable state/replay/capability testing becomes a
major implementation obligation. Exactly-once for arbitrary external effects
is not claimed.

## Migration

S2 proves minimal recovery without crash resume or live repository mutation.
S3 introduces durable store/journal and becomes authority only after migration
tests. Existing Phase8/Mission paths remain legacy until replacement is
accepted, then are disabled/removed rather than left as parallel controllers.
