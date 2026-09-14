# AGP Cockpit Test Plan v2

Status: active
Status-date: 2026-09-09
Decision status: accepted

## 1. Mandatory baseline

Every slice:
- focused tests;
- full portable/unit/integration suite where applicable;
- `git diff --check`;
- current `agentic-kit check`;
- exact-commit CI before merge;
- post-merge verification.

## 2. Acceptance matrix

T01 valid local script fails; same task gets evidence, Remote corrects, task completes.
T02 invalid/partial/ambiguous frame causes no execution.
T03 execution failure with healthy transport does not end task.
T04 wrong tab/target/effect is rejected before dispatch.
T05 premature COMPLETE is rejected.
T06 duplicate same action -> no second effect; changed payload -> rejection.
T07 crash after dispatch intent before observation -> unknown outcome.
T08 crash after effective mutation before result persistence -> no blind replay.
T09 crash after result persistence before delivery -> resend result, no new effect.
T10 timeout with possibly running process -> no concurrent mutator.
T11 second controller/corrupt store/full disk/old backup blocks unsafe dispatch.
T12 reconciliation requires attribution to original attempt.
T13 human checkpoint blocks protected follow-up and resumes same task.
T14 revision/artifact change invalidates stale human approval.
T15 pause/stop do not produce false terminal claims.
T16 budgets persist across restart; cosmetic activity does not reset STALLED.
T17 long active test/Kit process is not stalled merely due to no chat.
T18 recoverable Kit BLOCKED is resolved only through allowed Kit path.
T19 non-resolvable Kit gate suspends instead of claiming success.
T20 stale CI/wrong revision/fabricated PASS blocks completion.
T21 FILE_TRANSFER remains Kit-owned.
T22 secrets/log instructions/manipulated evidence do not expand authority.
T23 chat switch preserves contract/budgets; late old binding cannot execute.
T24 context refresh preserves goal, constraints, blockers and valid evidence.
T25 old client/new schema/downgrade follows capability rules.
T26 bounded real feature completes authorized lifecycle/post-merge.
T27 long-running disruption profile preserves deterministic state.
T28 optional local model cannot alter policy/work-order/gate/completion.

## 3. Slice gates

S2: T01-T06, T22 plus minimal completion verifier.
S3: T07-T12.
S4: T13-T17.
S5: T18-T22.
S6: T23-T25.
S7/S8: T26 plus human-checkpoint variant.
S11 robustness: T27.
Optional local-LLM slice: T28.

## 4. Independent review remediation contract

The independent Ultra review is an external regression contract for the current
remediation program. Its F01-F10 findings and K01-K07 package acceptance
criteria are tracked in `ULTRA_REVIEW_REMEDIATION.md`.

Rules:
- do not mark an original counterprobe `xfail` merely because it exposes a
  current product defect;
- if an API changes, preserve the same or a stronger behavior guarantee;
- direct store/controller tests do not substitute for a required shipped-path
  or live-product acceptance test;
- mock/unit/component evidence does not substitute for required live evidence;
- exact revision, producer, action, artifact, and Task Contract binding are
  required where the finding demands provenance;
- K07 must map every original v2 acceptance criterion to concrete
  exact-revision evidence, and unresolved criteria remain open.

## Native browser message evidence

The native transport regression and formatting variants execute the real
background script and its serialized browser expressions. Run the Playwright
suite as well as the Python suite; both are included in the existing CI gate.
See [Browser Native Message Evidence 107](../validation/BROWSER_NATIVE_SUBMIT_STRATEGIES_107.md)
for the live mismatch, bounded repair and remaining K07 acceptance boundary.
