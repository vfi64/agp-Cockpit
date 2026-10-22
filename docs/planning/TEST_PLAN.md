# AGP Cockpit Test Plan v2

Status: active
Status-date: 2026-09-09
Decision status: accepted
Review policy: on material change

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

The desktop-start regression in `tests/test_app_bootstrap.py` also exercises
Chrome navigation failures and timeouts. Optional navigation must not terminate
the available desktop/runtime; readiness still requires a fresh extension
handshake, and ambiguous tab selection must not become a successful reload.

## 2026-09-15 — K07 communication-loop rebaseline

This section supersedes older K07 planning statements where they conflict with the merged implementation through PR #115/#116. Historical remediation evidence remains historical and is not rewritten.

### Current implemented direction

The primary remote-LLM development path is the decomplexified artifact/file loop:

`human -> Cockpit -> remote LLM -> one Python command artifact -> browser/download -> Cockpit -> run_next.py / Agentic Project Kit -> one return bundle -> browser file attachment -> same remote-LLM conversation -> next Python artifact | AGP_DONE | AGP_NEEDS_HUMAN`

The remote LLM is not required to return a Protocol-v1 JSON work frame for this primary path. The browser/bridge transports opaque artifacts and minimal continuation control; it must not reproduce Git, GitHub, Agentic Project Kit, repository lifecycle, gate, PR, release, or handoff semantics.

Protocol-v1, DIRECT_EXECUTION and FILE_TRANSFER remain compatibility/transport infrastructure only where still required by existing implementation and tests. They are not the target semantic interface for the simplified remote-LLM file loop. Do not create a parallel protocol.

### Responsibility boundary

- Remote LLM: reasoning, diagnosis, and creation of the next executable Python work artifact; terminal outcome is `AGP_DONE` or `AGP_NEEDS_HUMAN`.
- Cockpit: deterministic orchestration, correlation, persistence, bounded execution and recovery.
- Browser/bridge: minimal deterministic transport of the task, one Python artifact, one return bundle, and the fixed continuation trigger.
- Agentic Project Kit: repository/Git/GitHub/workflow/lifecycle semantics.

### Next acceptance objective

Before further semantic expansion, prove the simplified loop with a real same-conversation end-to-end cycle. Instrument the existing seams rather than parsing browser/network traffic semantically. The cycle trace should correlate, at minimum:

1. `LLM_COMMAND_CREATED`
2. `BROWSER_COMMAND_DOWNLOADED`
3. `COCKPIT_COMMAND_ACCEPTED`
4. `LOCAL_EXECUTION_STARTED`
5. `LOCAL_EXECUTION_FINISHED`
6. `RESULT_BUNDLE_CREATED`
7. `BROWSER_RESULT_ATTACHED`
8. `CONTINUATION_SENT`
9. terminal/next outcome: `LLM_NEXT_COMMAND`, `AGP_DONE`, or `AGP_NEEDS_HUMAN`

Use one stable correlation identity across the cycle where current contracts permit it, plus artifact filename, SHA-256 and timestamp. Reuse existing task/cycle identifiers and persistence structures; do not introduce a second ledger if an existing authority can carry the evidence.

Acceptance requires fail-loud, resumable behavior at browser boundaries and protection against duplicate local execution. Exactly-once or demonstrably idempotent handoff behavior is more important than hiding browser failures.

### Immediate work order

1. Inventory which transition events above are already emitted/persisted by the merged PR #115 implementation.
2. Add only missing correlation/trace seams in one coherent product slice.
3. Run focused Python and Playwright tests plus repository/Kit gates.
4. Perform a real browser/remote-LLM E2E cycle in the same conversation.
5. Preserve the resulting trace as acceptance evidence.
6. Only after that evidence adjudicate whether legacy Protocol-v1 complexity can be further isolated or removed.

## External installation acceptance — digital-embryo

Status: NOT_RUN (prepared 2026-10-21). Target: vfi64/digital-embryo, default branch
main, private at the read-only inventory. This is installer stage A, not a proof of
K07 or an authorization to publish the target repository.

Record the Cockpit source revision, built app version/build and digest, installed
Kit version, target origin/main SHA, staged extension build and browser-handshake
identity before making acceptance claims. Keep tokens and private source out of
the committed report. Use the existing runtime root from RUNTIME_PATH_AUTHORITY;
record original settings for restoration and do not reset the production profile.

1. Inventory the existing app and target checkout read-only. A dirty target or an
   active Cockpit task is a stop condition. If no target checkout exists, obtain
   the intended disposable checkout location before creating it.
2. Run the packaged app with digital-embryo as the target repository. Cockpit source
   must not be the selected target or a required fallback resource. Verify the app
   uses packaged extension/resources and resolves its target Kit independently.
   Merely running tests from the Cockpit source tree does not pass this check.
3. Inspect components separately: Python/Tk, gh authentication, target Kit and
   workspace, Chrome, staged extension and fresh browser binding. Record actual
   host/port; stale 8765 defaults or build/binding mismatches stop the test.
4. If adoption is necessary, plan it through the installed Kit. Review the exact
   changed paths before execute; do not emulate missing Kit routes in Cockpit.
   An unavailable route or BLOCKED result is a recorded blocker, never a bypass.
5. In a dedicated target test branch, run one owner-bounded task through the
   supported Cockpit/browser work-order path: start, harmless reviewable change,
   result delivery, continuation, Kit validation and closeout. The specific
   content change and any remote publication/merge scope must be named before
   this live phase; do not infer it from installation approval.
6. Verify target repository identity, approvals and exact commands, required CI,
   resulting commit/PR (if authorized), clean final state and Kit post-merge state.
   Preserve one sanitized evidence report with PASS/FAIL/NOT_RUN per step and
   exact revision/artifact references. A human observes app/browser interaction;
   unit tests and file presence cannot substitute for these observations.
7. Restore the original app repository selection through supported UI/settings
   paths and retain test evidence. Do not delete user state or private target data
   as an implicit cleanup action.

No installed-app or live work-cycle result is claimed by this procedure. Installer
stage B (the component check/setup assistant) remains a separate product slice.
