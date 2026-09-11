# Independent Ultra Review Remediation Plan

Status: ACTIVE
Status-date: 2026-09-11
Decision owner: Maintainer
Review baseline: independent review of revision `90eff979e8e27e52b4e50b6de20655e30d8000fb`
Current implementation baseline at plan creation: `f1076d6f8c7133a4db088b38b46926de9a5409b4`

## 1. Purpose and adjudication

The 2026-09-09 declaration that the v2 macOS product was `FUNCTIONALLY_ACCEPTED`
is withdrawn. It is retained only as historical evidence of the earlier
adjudication and must not be treated as current product acceptance.

The independent review demonstrated that green component/runtime tests did not
yet prove the promised persistent, controlled remote-task-runner product.
Remediation therefore continues against the complete review contract, not
against phase names or test counts.

No finding is closed merely because a similarly named class, helper, test, or
static symbol exists. Closure requires the behavior at the supported product
entry point and the evidence class required by the original finding.

The review's reproduction artifacts are treated as external regression
requirements. They must not be weakened, hidden with `xfail`, or replaced by
narrower assertions. If a public API legitimately changes, an equivalent or
stronger behavioral test must preserve the same guarantee.

## 2. Current release/acceptance boundary

Current product status: `REVIEW_REMEDIATION_ACTIVE`.

The following remain prohibited until the relevant acceptance contract is
re-proven:

- claiming the complete v2 product `FUNCTIONALLY_ACCEPTED`;
- claiming unattended mutating development is production-ready;
- using unit/component evidence as a substitute for required live evidence;
- broadening executor authority to make tests or recovery succeed;
- bypassing Agentic Project Kit BLOCKED/FAIL results.

Guided, bounded bridge experiments remain a smaller operating scope and must be
described as such.

## 3. Finding inventory

### F01 / P1 — Runtime not fully integrated into the product path
Status: PARTIALLY_REMEDIATED / OPEN.

The delivered HTTP `/v1/protocol/execute` path has since been wired to durable
controller state, but closure still requires one authoritative controller
across the supported Desktop/Browser/HTTP path. Legacy continuation logic must
not retain a second task authority. Product-level FAIL/correction/DONE behavior
must be proven end to end.

### F02 / P1 — Executor resource/effect confinement is insufficient
Status: OPEN.

Repository cwd validation is not technical confinement of file, process,
network, credential, or other external effects. Capability/effect profiles must
derive from the local Task Contract and be enforced by the execution context.
Tests must cover at least out-of-scope writes, symlinks, interpreter/shell
subprocesses, and unauthorized network targets.

### F03 / P1 — Duplicate and dispatch protection is incomplete
Status: PARTIALLY_REMEDIATED / OPEN UNTIL CRASH-PROCESS EVIDENCE.

Persistent duplicate suppression and several controller/store invariants have
been hardened, including restart behavior. Closure still requires the review's
process/crash/concurrency guarantees, effective ownership/claim behavior, and
no blind replay of uncertain effects.

### F04 / P1 — Pause/recovery can violate human gates or terminal states
Status: PARTIALLY_REMEDIATED / OPEN UNTIL PRODUCT-PATH PROOF.

Controller-level suspension/terminal invariants were hardened. Closure requires
the same guarantees through the supported product path, including restart and
human-checkpoint resume.

### F05 / P1 — VERIFIED_COMPLETE can lack trusted evidence
Status: PARTIALLY_REMEDIATED / OPEN.

Completion semantics have been hardened at controller level. Closure requires
trusted local acquisition and revision/action/contract binding of Kit, CI, and
artifact evidence. Remote `DONE` is only a completion proposal and may never
directly produce `VERIFIED_COMPLETE`.

### F06 / P1 — Tests can mutate real user settings
Status: OPEN / NEXT IMPLEMENTATION PACKAGE.

Settings paths/adapters must be injectable. Startup tests must use an isolated
temporary profile. A guard must fail any access to the real user settings path,
and a before/after digest of the real configuration must remain unchanged.

### F07 / P1 — E2E/long-running acceptance was overstated
Status: OPEN; FALSE ACCEPTANCE CLAIM WITHDRAWN.

Tests must be classified honestly as unit, component, integration, or live
acceptance. Required real feature, human-gate, crash/replay/chat-switch, and
long-running evidence remains to be produced before any renewed acceptance.

### F08 / P1 — Dispatch transition atomicity was insufficient
Status: PARTIALLY_REMEDIATED / OPEN UNTIL FAILURE-INJECTION EVIDENCE.

Store/controller transaction ownership has been hardened. Closure requires
failure injection and process/crash evidence showing no partial transition
persists when dispatch-state persistence fails.

### F09 / P2 — Budgets, binding, deadlines, and resume context are incomplete
Status: PARTIALLY_REMEDIATED / OPEN.

Direct budget and binding invariants have been hardened. Closure requires
admission/reservation/consumption semantics, binding/epoch checks at acceptance
and dispatch, and canonical resume context containing goal, scope, evidence,
open effects, approvals, budgets, and completion contract.

### F10 / P2 — First-use and accessibility are not accepted
Status: OPEN.

Installation resources and target repository must be separate concepts. A new
user must be able to use an ordinary Kit repository and see the real runtime
state, gates, pause/resume, and completion state. Keyboard and macOS
accessibility semantics require explicit acceptance evidence.

## 4. Correction packages and order

Each package may contain multiple coherent slices. One slice means one branch,
one PR, applicable gates, Kit-governed closeout, and post-merge evidence.

### K01 — Protect user data and isolate tests
Findings: F06.
Status: EVIDENCE-BACKED COMPLETE.

The settings-isolation implementation is materially present. Acceptance step
605 ran the focused startup/settings regression in a temporary HOME profile:
14 tests passed, the temporary profile received its own settings file, and the
real `~/Library/Application Support/AGP Cockpit/settings.json` SHA-256 remained
`5b3b8666e9d9842a68d9ab10de97af21aab97d7c7b53fd36362eaefa95bb0014`
before and after the run. The static consumer-binding guard and `git diff
--check` also passed. Do not restore or rewrite real user settings unless the
intended repository and port values are independently verified.

### K02 — Correct persistent runtime invariants
Findings: F03, F04, F08.
Status: PARTIALLY IMPLEMENTED / OPEN FOR REVIEW CONTRACT COMPLETION.

Controller/store regression status was re-adjudicated on 2026-09-11. Step 613
showed that the two temporary 612R1 failures were harness defects rather than
product defects: the corrected contract passed 3/3 and the existing focused
K02 suites passed 22/22. Step 614R1 then passed the broader K02 regression
40/40, the complete repository pytest suite, and `git diff --check`.

This evidence does not close K02 or F03/F04/F08 beyond their finding-specific
boundaries above. Remaining acceptance still requires the independent review
contract's process/crash/concurrency ownership evidence, product-path
human-gate/restart proof, and dispatch failure-injection evidence. No product
patch is justified solely by the invalid 612R1 harness failures.

### K03 — Bind authorization and completion to trusted authority
Findings: F02, F05.
Status: OPEN.

Implement real effect/resource confinement and trusted evidence acquisition.
Do not infer authority from remote payload `kind` or harmlessness claims.

### K04 — Establish one vertical product path
Findings: F01, F03, F05, F10.
Status: PARTIALLY IMPLEMENTED / OPEN.

Desktop/Browser/HTTP must converge on the same hardened controller. A genuine
local FAIL must be delivered as task evidence and permit an authorized
correction round. A duplicate action after server restart must not duplicate
effect. A direct controller-only test is insufficient.

K04 mutating product acceptance must not outrun K02/K03 safety boundaries.

### K05 — Complete budgets, chat switch, and canonical context
Findings: F09.
Status: OPEN.

Complete budget boundary semantics, binding epochs, stale-message rejection,
deadlines, scope/acceptance preservation, open-effect preservation, and
evidence-based progress.

### K06 — Align first-use and accessibility with the real task
Findings: F10.
Status: OPEN.

Provide a task-oriented entry path for an ordinary target repository, persistent
human gates and resume state, and documented keyboard/screen-reader/layout
acceptance.

### K07 — Rebuild acceptance evidence and release status
Findings: F07.
Status: OPEN / FINAL ACCEPTANCE PACKAGE.

Run a real bounded feature through the required Kit lifecycle, a human-gate
variant, crash/replay/chat-switch scenarios, and the defined long-running
profile. Map every original v2 acceptance criterion to exact-revision evidence.
Open criteria remain open.

## 5. Required sequencing and dependency rules

1. K01 first, because test infrastructure must not mutate user state.
2. K02 before broad mutating product-path authority.
3. K03 before K04 is accepted for unattended mutation.
4. K04 establishes the single real vertical product path.
5. K05 completes bounded continuity and resume semantics.
6. K06 validates first-use and accessibility on that real path.
7. K07 alone may re-adjudicate whole-product acceptance.

Safe independent sub-slices may overlap only when they do not weaken these
dependency boundaries.

## 6. Repair method

For every failure domain:

- use current repository and installed Kit authority, not chat-memory command
  reconstruction;
- preserve `MEGABLICK_FAILURE_DOMAIN_METHOD_V1`;
- after two substantive failed repairs in one failure domain, stop mutation and
  perform a bounded read-only Megablick/Systemic Failure Review;
- prefer architectural correction over assertion patching;
- preserve original independent review guarantees;
- use the highest appropriate Kit orchestrator;
- never bypass Kit BLOCKED/FAIL with raw Git/GitHub;
- no shortcut may trade away scope, evidence provenance, resource authority,
  restart safety, or human gates.

## 7. Acceptance rule

Whole-product `FUNCTIONALLY_ACCEPTED` may be reconsidered only after K01-K07
applicable acceptance criteria are evidenced at the correct revision. Green CI
or a large number of tests is necessary evidence for what those tests execute;
it is not by itself evidence of live product capability.

### KIT-GF-RULE-REGISTRY-BOOTSTRAP

Confirmed Kit Greenfield/adoption defect. The rule-registry inventory gate is not repairable in this external workspace without invented semantics. Track the Kit-side bootstrap/applicability repair; do not block unrelated Cockpit remediation gates whose applicability is independently established.
