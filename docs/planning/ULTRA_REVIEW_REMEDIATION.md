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
Status: EVIDENCE-BACKED COMPLETE IN K04.

K04 now establishes one durable task authority across the supported
Desktop/Browser/HTTP execution path. The delivered Protocol-v1 execute path uses
`DurableTaskController` before local execution, durable SQLite state lives under
the stable runtime root, result delivery is explicitly acknowledged before a
correction round, and duplicate actions remain suppressed across restart.
Browser `DONE` now enters only the durable `COMPLETE_PROPOSED` surface; it does
not verify completion. Evidence: K04 steps 651-667, including 665, 666R1 and
667 final adjudication.

### F02 / P1 — Executor resource/effect confinement is insufficient
Status: EVIDENCE-BACKED COMPLETE IN K03.

K03 now derives effect/tool/network authority only from the local persisted Task Contract. Remote action/work-order content cannot self-grant authority. The delivered HTTP path validates that local authority before execution and threads the same locally persisted allowed_tools / allow_network constraints into a secondary ExecutionPolicy defense. Original resource-boundary regressions remain green. Evidence: 646R1, 649, 650.

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
Status: EVIDENCE-BACKED COMPLETE IN K03.

Remote DONE remains only a completion proposal. Caller-supplied Kit PASS records remain untrusted. K03 adds a local acquisition boundary that constructs trusted Kit evidence only from an actually executed, locally authorized agentic-kit result, derives revision and raw evidence hash locally, and binds completion to revision, artifact identity, action, and raw hash. Raw-evidence mutation changes the hash and mismatched completion identity is rejected. Evidence: 647-650.

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

#### K02 evidence update — 2026-09-11 / steps 619R2, 620R2, 626

Additional independent evidence now proves:
- separate-process crash after durable `DISPATCH_INTENT` is recovered as `OUTCOME_UNKNOWN` and blind retry is blocked (619R2);
- a second process/controller is denied while another action owns active execution (619R2);
- injected failure at the final dispatch-state persistence seam rolls the entire dispatch transition back atomically (620R2);
- T08's exact effect window is proven with a real harmless temporary filesystem effect followed by hard process exit before result persistence; restart recovers `a1` as `OUTCOME_UNKNOWN`, blocks automatic replay, and preserves one local action (626).

The focused K02 regression remains green. These results close the controller/store-level process/crash/concurrency and dispatch-atomicity evidence requested by F03/F08. F04 remains explicitly bounded by its own wording: controller-level human-gate/terminal behavior is proven, while supported product-path human-checkpoint/restart proof belongs to the later vertical product-path acceptance boundary and must not be silently claimed here.

### K03 — Bind authorization and completion to trusted authority
Findings: F02, F05.
Status: EVIDENCE-BACKED COMPLETE / PENDING KIT CLOSEOUT.

Authority half: local Task Contract is the sole permission source; delivered HTTP execution and the secondary ExecutionPolicy enforce its effect/tool/network bounds, and the frozen authority regression remained unchanged through evidence work.

Evidence half: actual locally authorized Kit execution is converted at a local acquisition boundary into trusted KitResultEvidence; caller-created PASS remains untrusted. Revision, artifact identity, action and raw evidence are bound into completion verification.

Step 650 passed K03 20/20, execution 26/26, runtime/completion 32/32, settings 12/12, complete repository pytest, agentic-kit check, doctor, and git diff --check. K03 is complete subject only to normal Kit-governed branch/PR/post-merge closeout. K04 remains gated until that succeeds.

### K04 — Establish one vertical product path
Findings: F01, F03, F05, F10.
Status: EVIDENCE-BACKED COMPLETE FOR VERTICAL PRODUCT AUTHORITY / PENDING KIT CLOSEOUT.

The supported Desktop/Browser/HTTP path now converges on the durable controller
for task authority. K04 proves genuine local FAIL -> durable result evidence ->
explicit RESULT_DELIVERED acknowledgement -> authorized correction, persistent
duplicate suppression across server restart, a durable task status/control
surface, restart-safe revision/artifact-bound human checkpoints, and browser
`DONE` -> `COMPLETE_PROPOSED` only.

Final read-only adjudication step 667 passed the focused K04 authority set
15/15, human-checkpoint/control set 7/7, completion/proposal set 8/8, the full
repository pytest suite, and `git diff --check`.

Finding boundaries are preserved:
- F01's vertical product-path integration requirement is closed by K04.
- F03's K04 duplicate/delivery portion is proven; broader crash/process
  invariants remain governed by K02 evidence/status.
- F04's deterministic product-path human-gate authority is proven; user-facing
  checkpoint interaction/accessibility belongs to K06.
- F05's browser DONE/proposal separation is proven; trusted Kit/CI/artifact
  acquisition/provenance remains K03.
- F10 first-use/accessibility remains open for K06.

No additional K04 browser checkpoint UI mutation is required. K04 acceptance is
complete subject only to normal Kit-governed branch/PR/post-merge closeout.

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
