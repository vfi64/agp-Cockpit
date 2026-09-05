# Agentic Project Kit — AGP Cockpit Greenfield Defect Ledger

Status: active
Decision status: accepted
Review policy: on material change

## Purpose

This is the canonical chronological defect ledger for Kit defects and high-confidence
Kit defect candidates discovered while developing `agp-Cockpit` as a real external/
Greenfield workspace with `agentic-project-kit`.

Historical IDs are preserved as aliases. Canonical `KIT-GF-*` IDs identify defect
families after adjudicating duplicate observations and later root-cause confirmations.

Cockpit product defects, harness/script defects, credentials, and expected external
service behavior are explicitly excluded.

## Chronological observation log

| Date | Event | Historical ID / Evidence | Canonical family | Observation |
|---|---|---|---|---|
| 2026-08-31 | `GF-E001` | `GW-01` | `KIT-GF-001` | workspace init/check PASS followed by doctor lifecycle failure |
| 2026-08-31 | `GF-E002` | `GW-02` | `KIT-GF-002` | planning-doc slice gate invoked Kit self-hosting tests/docs |
| 2026-08-31 | `GF-E003` | `GW-03` | `KIT-GF-003` | handoff state path/bootstrap inconsistency and missing fresh state |
| 2026-08-31 | `GF-E004` | `GW-04` | `KIT-GF-004` | governance check disagreed with doctor on external-workspace mode |
| 2026-08-31 | `GF-E005` | `GW-05` | `KIT-GF-005` | fresh work start falsely blocked by post-merge successor state |
| 2026-08-31 | `GF-E006` | `GW-06` | `KIT-GF-006` | transfer status raised Errno for legitimate empty inbox |
| 2026-08-31 | `GF-E007` | `GW-07` | `KIT-GF-007` | workspace adopt inflated manual/adjudication surfaces after init |
| 2026-08-31 | `GF-E008` | `GW-08` | `KIT-GF-008` | bootstrap-generated CI suspected of using self-hosting gate; later confirmed |
| 2026-08-31 | `GF-E009` | `GW-09` | `KIT-GF-009` | work finish execute generated dirty state and blocked first push |
| 2026-08-31 | `GF-E010` | `GW-09e` | `KIT-GF-010` | rule acknowledgement self-invalidating cycle isolated as root cause |
| 2026-09-03 | `GF-E011` | `KIT-HANDOFF-CI-001` | `KIT-GF-008` | external-workspace CI defect confirmed and workaround validated remotely |
| 2026-09-03 | `GF-E012` | `KIT-HANDOFF-RULEACK-002` | `KIT-GF-010` | rule-ack self-invalidation reproduced deterministically in disposable sandbox |
| 2026-09-03 | `GF-E013` | `KIT-HANDOFF-HEAD-003` | `KIT-GF-011` | tracked successor package proved self-stale after own commit |
| 2026-09-03 | `GF-E014` | `Step 071` | `KIT-GF-012` | work finish dry-run PASS but execute BLOCKED |
| 2026-09-03 | `GF-E015` | `Steps 065-086` | `KIT-GF-013` | patch spiral exposed missing automatic systemic-failure escalation |

| 2026-09-05 | `GF-E019` | `Step 207 / PR #22` | `KIT-GF-017` | green HEAD-verified external-workspace PR merge blocked by missing Kit-owned fresh LLM context artifacts |
| 2026-09-05 | `GF-E020` | `Steps 215-218` | `KIT-GF-011` | Kit-generated tracked successor projections block next work start; normalize-session and post-merge-settle both reject the Kit-owned dirty state |

## Canonical defect families

### KIT-GF-001 — Workspace lifecycle bootstrap is not closed after successful external workspace init

First observed: 2026-08-31
Status: OPEN
Severity: medium
Classification: agentic-kit
Historical aliases: `GW-01`

**Expected**

dpa-intake/workspace init must either preflight lifecycle metadata, normalize it canonically, or return a deterministic remediation path before doctor is expected to pass.

**Observed**

workspace init reported PASS and agentic-kit check passed, but doctor failed iteratively on missing/invalid Status, Decision status, and Review policy metadata.

**Impact**

Fresh external-workspace bootstrap reports success before the lifecycle contract is actually closed; the operator must reverse-engineer document metadata iteratively.

**Validated/temporary workaround**

Add the lifecycle headers manually according to the installed Kit contract.

**Required Kit repair direction**

Integrate lifecycle preflight/remediation into dpa-intake/workspace init, or provide a canonical lifecycle-normalization command.

**Required regression/acceptance evidence**

Fresh external repo with planning docs lacking lifecycle metadata must either block before init, pass doctor after init, or emit one deterministic remediation command.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31.md`
- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`

---

### KIT-GF-002 — Planning-document slice gate leaks Kit self-hosting assumptions into external workspaces

First observed: 2026-08-31
Status: OPEN
Severity: high
Classification: agentic-kit
Historical aliases: `GW-02`

**Expected**

External-manifest workspace slice gates must resolve only workspace-applicable gates, project-native tests, and explicitly registered extra gates.

**Observed**

slice gate --kind planning-doc attempted Kit self-hosting test paths and Kit documentation-mesh requirements absent from the external repository.

**Impact**

Healthy external workspaces are classified as broken because they do not contain the Kit repository's own source/tests/docs structure.

**Validated/temporary workaround**

Use external-workspace-safe project tests plus agentic-kit check/doctor instead of the affected higher-level gate.

**Required Kit repair direction**

Centralize workspace-mode/capability resolution and make slice gates profile-aware.

**Required regression/acceptance evidence**

A minimal external manifest workspace without Kit source files must not fail planning-doc gate because Kit self-hosting paths are absent.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31.md`
- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`

---

### KIT-GF-003 — Handoff-state paths and fresh bootstrap state are inconsistent

First observed: 2026-08-31
Status: OPEN
Severity: high
Classification: agentic-kit
Historical aliases: `GW-03`

**Expected**

Exactly one authoritative handoff-state resolver/path per workspace mode, with an explicit legitimate fresh/no-previous-handoff state.

**Observed**

Commands referenced .agentic/handoff_state.yaml, .agentic/state/handoff/handoff_state.yaml, and directory-level state differently; fresh workspace checks could raise FileNotFoundError.

**Impact**

A newly initialized workspace cannot rely on a single deterministic handoff authority and read-only handoff checks may fail on a legitimate empty state.

**Validated/temporary workaround**

Use the specific currently functioning transfer/handoff surfaces and avoid inventing missing state files.

**Required Kit repair direction**

Centralize handoff path resolution and model NO_PREVIOUS_HANDOFF explicitly.

**Required regression/acceptance evidence**

Immediately after workspace init, handoff check, post-merge-check and work recover must classify deterministically without traceback.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31.md`
- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`

---

### KIT-GF-004 — governance check is not external-workspace aware

First observed: 2026-08-31
Status: OPEN
Severity: high
Classification: agentic-kit
Historical aliases: `GW-04`

**Expected**

governance check must resolve the same external-manifest workspace mode as doctor.

**Observed**

doctor correctly skipped .agentic/project.yaml/full-contract policy checks while governance check demanded Kit/full-constitution files and legacy handoff state.

**Impact**

Two governance surfaces disagree about the same repository and configuration.

**Validated/temporary workaround**

Treat doctor/check as authoritative external-workspace baseline until governance check is corrected.

**Required Kit repair direction**

Use a shared workspace-mode/capability resolver for doctor, governance, slice, handoff and workflow orchestrators.

**Required regression/acceptance evidence**

If doctor recognizes external_manifest_workspace, governance check must not fail solely because full-contract/self-hosting constitution files are absent.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31.md`
- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`

---

### KIT-GF-005 — Fresh external workspace work start is blocked by predecessor/post-merge state

First observed: 2026-08-31
Status: OPEN
Severity: high
Classification: agentic-kit
Historical aliases: `GW-05`

**Expected**

A freshly initialized external workspace with no previous merge has a legitimate VIRGIN_WORKSPACE / POST_MERGE_NOT_APPLICABLE state and may start its first work branch.

**Observed**

work start was BLOCKED by post-merge-check even though refresh_required=false, result=NOOP and no previous merge existed.

**Impact**

The intended high-level Greenfield workflow cannot start immediately after successful initialization.

**Validated/temporary workaround**

Use bounded lower-level recovery/workflow steps while preserving evidence; do not fabricate predecessor state.

**Required Kit repair direction**

Model virgin/fresh workspace explicitly in the post-merge/work-start state machine.

**Required regression/acceptance evidence**

Immediately after fresh workspace init, work start --branch feature/x --from-ref main must proceed when repository safety conditions are satisfied.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31.md`
- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`
- `AGP_Cockpit_Greenfield_Kit_Defect_Report_2026-09-03.md`

---

### KIT-GF-006 — transfer status treats an empty inbox as a file error

First observed: 2026-08-31
Status: OPEN
Severity: medium
Classification: agentic-kit
Historical aliases: `GW-06`

**Expected**

Empty transfer inbox is a valid NO_COMMAND state.

**Observed**

transfer status raised Errno 2 for .agentic/transfer/inbox/current.yaml while transfer state correctly classified the same workspace as NO_COMMAND.

**Impact**

A legitimate empty state leaks an operating-system file error through a public workflow surface.

**Validated/temporary workaround**

Use transfer state for empty-state inspection.

**Required Kit repair direction**

Make transfer status use the same state-layer logic as transfer state and treat missing current.yaml as expected.

**Required regression/acceptance evidence**

Fresh transfer workspace: transfer state and transfer status must report semantically equivalent NO_COMMAND state.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31.md`
- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`

---

### KIT-GF-007 — workspace adopt reclassifies Kit-generated init files as new manual/adjudication surfaces

First observed: 2026-08-31
Status: OPEN
Severity: medium-high
Classification: agentic-kit
Historical aliases: `GW-07`

**Expected**

Unmodified files generated/owned by workspace init retain provenance and do not immediately return as unknown maintainer/manual surfaces.

**Observed**

Surface count increased from 13 to 28 after init and many Kit-generated files were reintroduced as manual-preservation/adjudication surfaces.

**Impact**

Adoption can enter a self-amplifying adjudication loop and obscure ownership/provenance.

**Validated/temporary workaround**

Manually distinguish generated Kit projections from true maintainer authority during subsequent adoption assessment.

**Required Kit repair direction**

Carry writer/generated provenance from workspace-init projection into adoption classification.

**Required regression/acceptance evidence**

workspace adopt before/after init must classify unchanged init-generated files as Kit-generated/command-owned or already adjudicated.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31.md`
- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`

---

### KIT-GF-008 — Bootstrap-generated external-workspace CI uses a self-hosting/internal gate

First observed: 2026-08-31
Status: OPEN
Severity: high
Classification: agentic-kit
Historical aliases: `GW-08`, `KIT-HANDOFF-CI-001`

**Expected**

workspace init --inject-ci must generate CI appropriate to an external manifest workspace.

**Observed**

Generated canonical and managed workflows invoked agentic-kit standard-gates-audit-suite, while doctor explicitly skips standard audit suite outside the Kit development checkout. Later diagnosis and repaired remote CI confirmed the external-workspace contract.

**Impact**

A fresh external workspace can receive a CI definition aimed at the Kit's own/self-hosting project model.

**Validated/temporary workaround**

Validated agp-Cockpit CI contract: python -m pytest -q; agentic-kit check --root .; agentic-kit doctor --root .

**Required Kit repair direction**

Generate an explicit external-workspace CI profile/surface selected from workspace mode.

**Required regression/acceptance evidence**

Bootstrap an external workspace, push a minimal PR, and require generated Agentic Gate CI to pass without Kit self-hosting paths.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31.md`
- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`
- `AGENTIC_PROJECT_KIT_GREENFIELD_HANDOFF_DEFECTS_2026-09-03.md`
- `AGP_Cockpit_Greenfield_Kit_Defect_Report_2026-09-03.md`
- `AGP_Cockpit_Greenfield_Kit_Handoff_Defects_latest.md`
- `053_external_workspace_ci_surface_diagnosis_latest.json`
- `054_external_workspace_ci_surface_diagnosis_rich_help_latest.json`
- `055R1_external_workspace_ci_contract_repair_latest.json`
- `remote GitHub Actions run 33768245355 (success after repaired external contract)`

---

### KIT-GF-009 — work finish first-push lifecycle can generate its own blocking dirty state

First observed: 2026-08-31
Status: OPEN
Severity: high
Classification: agentic-kit
Historical aliases: `GW-09`

**Expected**

work finish --execute on a never-pushed work branch must settle all Kit-owned generated state before clean-worktree/first-push preconditions and then establish upstream safely.

**Observed**

work finish dry-run passed; execute created commits/handoff refresh, rewrote tracked rule acknowledgement for the new HEAD, left the worktree dirty, then push-current blocked before first upstream/remote branch creation.

**Impact**

The high-level first closeout can block itself before the first push/PR.

**Validated/temporary workaround**

Use only bounded documented recovery while retaining the self-generated dirty-state evidence; do not globally weaken clean-worktree safety.

**Required Kit repair direction**

Correct the transaction/order boundary among commit, handoff refresh, rule acknowledgement settlement, clean-worktree verification and first push.

**Required regression/acceptance evidence**

Fresh external work branch with no upstream: work finish --execute must create remote/upstream and must not be blocked by Kit-owned state it generated itself.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`

---

### KIT-GF-010 — Rule acknowledgement is self-invalidating across the Kit-owned commit it authorizes

First observed: 2026-08-31
Status: OPEN
Severity: critical
Classification: agentic-kit
Historical aliases: `GW-09e`, `KIT-HANDOFF-RULEACK-002`

**Expected**

A valid acknowledgement must survive the authorized Kit mutation, or the owning transaction must settle/re-anchor it without entering a self-referential loop.

**Observed**

rules acknowledge binds current.json to HEAD H1; transfer commit succeeds and creates H2; the tracked acknowledgement still points to H1 and immediately becomes invalid/dirty again. Disposable sandbox reproduction proved the cycle.

**Impact**

acknowledge -> Kit commit -> next transfer action cannot remain continuously valid; committing the acknowledgement itself can recreate the mismatch indefinitely.

**Validated/temporary workaround**

Acknowledge immediately before intended Kit commit, confirm self-invalidation, restore tracked acknowledgement from the new HEAD, then continue only through narrowly justified workflow paths.

**Required Kit repair direction**

Redesign acknowledgement identity/transaction semantics: content/snapshot authority, volatile command-owned state, stable rules-source identity, or an explicit transaction that does not self-invalidate.

**Required regression/acceptance evidence**

Fresh external workspace must support acknowledge -> required persistence/commit -> acknowledgement remains valid -> clean worktree -> push-current; actual rule-source changes must still invalidate acknowledgement.

**Evidence sources / IDs**

- `agentic_project_kit_greenfield_external_workspace_error_protocol_2026-08-31-2.md`
- `AGENTIC_PROJECT_KIT_GREENFIELD_HANDOFF_DEFECTS_2026-09-03.md`
- `AGP_Cockpit_Greenfield_Kit_Defect_Report_2026-09-03.md`
- `AGP_Cockpit_Greenfield_Kit_Handoff_Defects_latest.md`
- `056D2_rule_ack_self_invalidation_latest.json`

---

### KIT-GF-011 — Tracked successor handoff projections are self-stale after their own commit

First observed: 2026-09-03
Status: OPEN
Severity: critical
Classification: agentic-kit
Historical aliases: `KIT-HANDOFF-HEAD-003`

**Expected**

A deterministic successor handoff must converge on a trustworthy final repository identity without requiring perpetual re-render/commit cycles.

**Observed**

chat-switch-complete generated tracked files containing current HEAD; committing those files created a new HEAD that none of them referenced; rerendering dirtied the same files again.

A later full lifecycle reproduction after Phase 5 strengthened the defect: five Kit-generated tracked successor projections remained dirty after successful post-merge closeout. `restore-known-volatile` did not recognize them, `sync-main -> normalize-session` blocked the next `work start` with `dirty_worktree`, and the dedicated `post-merge-settle --after-pr 22` also blocked because it classified those same generated projections as `dirty_product_paths_before_post_merge_complete`.

**Impact**

The Kit cannot simultaneously guarantee committed successor package, exact final-HEAD identity, and clean tracked worktree with the current projection model. The defect can also make the next ordinary high-level work cycle unreachable through supported settlement commands, because Kit-generated continuation projections are reclassified as user/product dirtiness.

**Validated/temporary workaround**

Render final-HEAD successor projections after the final code/remote HEAD is fixed and keep those exact-final-HEAD projections volatile/uncommitted. If an already affected external workspace is blocked after the supported `restore-known-volatile`, `normalize-session`, and `post-merge-settle` paths have been evidenced, preserve the generated diff and restore only the exact known successor-projection paths to the committed state as a bounded recovery exception before resuming the normal Kit workflow.

**Required Kit repair direction**

Decouple durable committed handoff source from volatile exact-final-HEAD projection, or introduce a transaction/identity model that explicitly understands the handoff commit boundary.

**Required regression/acceptance evidence**

A disposable clone must prove that final successor authority remains exact and validation-clean without a self-staling render->commit->rerender loop.

**Evidence sources / IDs**

- `AGP_Cockpit_Greenfield_Kit_Defect_Report_2026-09-03.md`
- `AGP_Cockpit_Greenfield_Kit_Handoff_Defects_latest.md`
- `062-D1`
- `062-D2`
- `Steps 215-218`
- `217_SYSTEMIC_FAILURE_REVIEW.json`
- `219_recovery_evidence/kit_gf011_successor_projection_diff.patch` (local diagnostic evidence)

---

### KIT-GF-012 — work finish dry-run may pass while execute blocks in the same bounded closeout

First observed: 2026-09-03
Status: OPEN
Severity: medium
Classification: agentic-kit
Historical aliases: `former local ledger KIT-GF-001`

**Expected**

A successful work finish dry-run should describe an executable valid plan, or clearly surface execution-only preconditions before claiming PASS.

**Observed**

For the four-file Greenfield-governance slice, dry-run returned STATE=PASS; --execute returned STATE=BLOCKED with blockers pr-create-complete, sync-main and post-merge-check.

**Impact**

Operator cannot trust dry-run PASS as evidence that the advertised closeout route is executable.

**Validated/temporary workaround**

Collect evidence and continue Cockpit development safely without repairing Kit internals in this repository.

**Required Kit repair direction**

Align planning/execution precondition evaluation and report execution-only blockers during dry-run.

**Required regression/acceptance evidence**

Equivalent bounded work finish dry-run and execute must agree on route validity unless an externally changed condition is explicitly evidenced.

**Evidence sources / IDs**

- `Step 071 terminal evidence`

---

### KIT-GF-013 — No automatic escalation from repeated local repair to systemic/root-cause review

First observed: 2026-09-03
Status: OPEN
Severity: medium
Classification: agentic-kit
Historical aliases: `former local ledger KIT-GF-002`

**Expected**

Repeated failures in the same subsystem/failure domain should trigger a deterministic systemic review before another local patch is accepted.

**Observed**

Multiple locally reasonable Browser/ChatGPT transport repair cycles accumulated before a system-wide review. Inventory 086 found 18 relevant tests, 15 source-coupled tests, 5 active historical repair markers and repeated LIVE-vs-simulated disagreement.

**Impact**

An agent can rationally continue symptom patches while the repository-level history already indicates a patch spiral or missing abstraction/state machine.

**Validated/temporary workaround**

AGP Cockpit locally enforces SYSTEMIC_FAILURE_REVIEW before a third substantive mutation in the same failure domain.

**Required Kit repair direction**

Add recurrence/failure-domain detection to workflow-guard / patch-failure discipline and block patch spirals until systemic review classifies PATCH_LOCAL, REFACTOR_SUBSYSTEM, REDESIGN_BOUNDARY, TEST_MODEL_REPAIR or NEEDS_HUMAN.

**Required regression/acceptance evidence**

Repeated repairs in one failure domain must escalate at a deterministic threshold and prevent a third unreviewed product mutation.

**Evidence sources / IDs**

- `docs/validation/BROWSER_TRANSPORT_STABILIZATION_086.md`
- `docs/validation/BROWSER_TRANSPORT_STABILIZATION_086.json`
- `docs/planning/SYSTEMIC_FAILURE_ESCALATION.md`

---

## Explicit exclusions

- Development-script syntax/regex/harness mistakes are not Kit defects.
- GitHub OAuth workflow-scope failure was an authentication issue, not a Kit defect.
- Cockpit browser/send-acknowledgement implementation defects are Cockpit defects, not Kit defects.
- Cockpit hard-coded executable test roots are Cockpit portability/test defects.
- Cockpit planning-document Review-policy mistakes are Cockpit/document-authoring defects.

## Cross-defect systemic conclusions

### A. External-workspace mode/capability resolution is not consistently centralized

The earliest GW-01..GW-08 findings repeatedly show drift among `doctor`,
`governance check`, `slice gate`, handoff, transfer, work-start, and generated CI.
A durable Kit repair should centralize workspace-mode/capability resolution rather
than add more command-local exceptions.

### B. First-work / first-closeout transaction boundaries are not fully convergent

`KIT-GF-005`, `KIT-GF-009`, `KIT-GF-010`, `KIT-GF-011`, and `KIT-GF-012`
show distinct symptoms around virgin workspace state, rule-ack identity, generated
handoff state, first push, and closeout planning/execution consistency.

### C. The Kit needs an explicit recurrence-to-systemic-review escalation

`KIT-GF-013` is a meta-governance defect exposed by the Cockpit Browser transport
patch spiral. It should become a Kit-level workflow mechanism, not remain a Cockpit-only rule.

### D. Evidence-first convergence workflow reduces patch instability and false-positive repairs

Later Phase-1 integration work exposed a positive workflow finding complementary to
`KIT-GF-013`. After the Browser transport patch spiral, Cockpit work became materially
more stable when mutation was delayed until architecture evidence had been collected
and adjudicated.

The effective sequence was:

```text
exact baseline preflight
-> bounded inventory
-> ownership/call-path seam mapping
-> contextual adjudication
-> explicit NO_DEFECT / LAYERED_AUTHORITY result when appropriate
-> smallest justified mutation only if a concrete seam remains
-> focused regression
-> broader integration/governance gates at controlled boundaries
```

This produced useful negative findings without unnecessary product changes: operator
UI transport authority delegates through `OperatorAPI`; BridgeRuntimeServer and
CockpitBridgeServer start/stop ownership is layered; and BridgeEngine/BridgeRuntime
authority is one-way/layered rather than duplicated.

**Greenfield lesson for the Kit**

The Kit should not treat high fan-in, overlapping vocabulary, repeated method names,
or architectural suspicion alone as a repair candidate. Workflow guidance should
require evidence that distinguishes competing mutation/execution authority from a
legitimate layered dependency before authorizing code mutation.

A reusable Kit-level convergence discipline should:

1. pin and verify the exact repository baseline and tolerated dirty state;
2. inventory the bounded implementation and regression surface before editing;
3. map ownership, imports and call paths for the suspected seam;
4. adjudicate explicitly, including durable negative outcomes such as `NO_DEFECT`
   or `LAYERED_AUTHORITY_CONFIRMED`;
5. preserve negative adjudications so later agents do not reopen the same candidate
   without new evidence;
6. permit mutation only after a concrete competing authority, invariant violation,
   or failing behavior is demonstrated;
7. use focused regression after a bounded step and broader gates at integration
   boundaries;
8. combine this discipline with `KIT-GF-013`: repeated repair in one failure domain
   escalates to systemic review rather than another symptom patch.

**Expected Kit benefit**

Reduced patch spirals, speculative refactors, accidental regressions, duplicate
investigation, and agent-to-agent architectural drift, while making no-change
findings first-class evidence.

**Evidence sources / IDs**

- Steps 106-108
- Steps 129-130
- Step 131
- Step 132
- `KIT-GF-013`



### E. Preserve Kit-owned multi-stage lifecycle and prefer high-level wrappers

The first real Phase-3 PR lifecycle exposed a validation-process lesson. After
`work finish --execute --no-merge` had correctly created and validated PR #2, the
Greenfield operator path initially composed lower-level transfer commands manually
instead of continuing through the Kit's high-level multi-stage closeout wrapper.

This is itself Greenfield evidence: validation must not silently replace a Kit-owned
lifecycle with an operator-owned approximation and then classify the resulting
low-level blocker as a product defect.

The reusable rule is:

```text
highest-level supported lifecycle wrapper first
-> observe its result
-> preserve partial state on failure
-> inspect lower-level commands only for diagnosis
-> no manual fallback unless explicitly required for recovery
```

`KIT-GF-010` also received a concrete Kit 1.0.8 lifecycle extension. The Kit-owned
`work finish --execute --no-merge` path left only
`.agentic/rule_ack/current.json` modified. The subsequent high-level
`transfer pr-closeout-complete` therefore blocked with `DIRTY_WORKTREE`. Using the
official `transfer restore-known-volatile` recovery cleaned that generated state;
the same high-level closeout then completed successfully, merged substantive PR #2,
created and merged successor-package refresh PR #3, synchronized `main`, and left
the worktree clean.

This does not require a new defect family: it strengthens `KIT-GF-010` by showing
that its volatile Rule-ACK behavior crosses a real multi-stage PR closeout boundary.

**Evidence**

- Steps 170--175-R1
- PR #2: Phase 3 terminal-executor extraction
- PR #3: successor-package refresh
- final `main`: `3de6b9f2080f57bd6aafa3e4d046f38bb66d0e15`


## Greenfield end-to-end acceptance target

A future repaired Kit should pass this external-repository lifecycle without manual
raw git/gh substitution or fabricated state:

```text
workspace dpa-intake
-> maintainer adjudication
-> workspace init --execute --inject-ci
-> check PASS
-> doctor PASS
-> first work start PASS
-> local change
-> work check PASS
-> work finish dry-run with executable plan
-> work finish --execute
-> first push/upstream
-> PR creation
-> CI PASS
-> merge
-> post-merge closeout
-> trustworthy successor handoff
```

## KIT-GF-014 — External-workspace governance does not detect stale or ambiguous continuation authority

**Status:** OPEN
**Severity:** high
**Classification:** agentic-kit

**Expected:** External-workspace governance should validate freshness and consistency of active continuation authority and clearly distinguish product-owned canonical sources, Kit operating state, registries, and generated projections.

**Observed:** .agentic/state/status.md still declared obsolete Phase 066 active, documentation.yaml was empty, and generated successor material mixed PROJECT_DIRECTION.yaml with the external-workspace no-project-direction model while Kit documentation gates/lifecycle audit were green.

**Impact:** A successor LLM can receive obsolete or ambiguous direction despite a formally green lifecycle.

**Workaround:** Define explicit Cockpit-side document authority and canonical values until the Kit provides this governance.

**Repair:** Add external-workspace authority checks for stale active phase/status, registry coverage/intent, and contradictions between open_tasks_source and the selected workspace/project-direction model.

**Regression:** An external workspace with stale active status, empty/unclassified registry, or contradictory successor authority must warn or fail deterministically.


## KIT-GF-015 — Canonical document facts are not propagated across registered documents

**Status:** OPEN
**Severity:** medium-high
**Classification:** agentic-kit

**Expected:** A project should be able to declare a canonical fact once and have Kit-managed/generated documents reference or refresh it deterministically; project-owned prose should be audited for stale/conflicting values and only rewritten when explicitly opted in.

**Observed:** The Kit can register and lifecycle-check documents, but there is no declared single-source mechanism for shared project facts such as one desired DOI link, concept DOI, project URL, or release version, nor deterministic detection/refresh of stale occurrences across documents.

**Impact:** Shared metadata can drift across otherwise valid documents, leaving contradictory DOI links, versions, URLs, or other facts while document lifecycle checks remain green.

**Workaround:** Define explicit Cockpit-side document authority and canonical values until the Kit provides this governance.

**Repair:** Extend the documentation registry with canonical facts/metadata and reference declarations; add drift audit plus safe normalization for explicitly managed/generated surfaces, and review-required findings for project-owned prose.

**Regression:** Declare one canonical DOI link, place an old conflicting DOI in registered managed/generated and project-owned documents, then require deterministic managed refresh plus a review finding for non-opted-in project prose.

## KIT-GF-016 — High-level external-workspace workflows should support contract-first guided execution

**Status:** OPEN
**Severity:** medium
**Classification:** agentic-kit-ux-contract

**Expected:** Mutating high-level workflows expose a machine-readable contract-first plan that detects context, proposes changed paths, reports required decisions/blockers, and becomes execution-ready before mutation.

**Observed:** During Cockpit foreign-repository closeout, `work finish` behaved correctly once branch, title, message, and all six explicit `--path` selections were supplied. The explicit-path JSON dry-run then returned no blockers and a coherent merge/post-merge plan, but the calling agent had discovered parts of that invocation contract incrementally.

**Impact:** Agents can waste iterations guessing or reimplementing orchestration contracts even when the underlying Kit workflow is sound.

**Workaround:** Inspect `--help` and require a non-mutating JSON dry-run before `--execute`.

**Repair:** Standardize **Inspect -> Plan -> Validate -> Execute -> Verify** for mutating high-level commands. Dry-run JSON should surface detected context, proposed paths, required inputs, blockers, and an execution-ready structured plan.

**Regression:** In an external workspace with multiple dirty paths, the first planning call deterministically identifies or proposes all required inputs and paths without mutation; execution of the accepted plan requires no undocumented agent-side inference.

## KIT-GF-017 — pr-merge-safe requires Kit-owned fresh LLM context artifacts that may not exist in a valid external workspace

**Status:** OPEN
**Severity:** high
**Classification:** agentic-kit
**First observed:** 2026-09-05
**Evidence event:** `GF-E019` / Step 207 / PR #22

**Expected:** A green, merge-clean, exact-HEAD-verified external-workspace PR
should be able to continue through the regular high-level `pr-merge-safe`
lifecycle. If fresh LLM context is a mandatory safety precondition, the wrapper
must either create/refresh the required Kit-owned artifacts itself or return one
specific supported predecessor command that does so.

**Observed:** PR #22 was OPEN, `merge_state_status=CLEAN`, `decision=green`, and
its `head_ref_oid` exactly matched the expected
`4edace6738a34a0fee98aca9daf85c4d25063f29`. The regular
`agentic-kit transfer pr-merge-safe 22 --expected-head-sha ... --json` path
nevertheless blocked before merge in `require-fresh-llm-context` with
`outbox_missing` and `latest_handoff_report_missing`. The missing paths were
`.agentic/transfer/outbox/last_result.txt` and
`.agentic/state/handoff/transfer_handoff_reports/latest-transfer-handoff-report.json`.

**Impact:** A product-complete, CI-green external workspace can be unable to
complete the documented high-level merge lifecycle because optional or
Kit-generated communication/context artifacts do not exist. The reported
remediation is descriptive ("Regenerate and publish fresh LLM context") rather
than an execution-ready supported command, forcing the agent to discover or
guess the predecessor lifecycle.

**Validated/temporary workaround:** Do not bypass with
`--skip-llm-context-gate` during normal operation; that option is documented as
recovery-only. Preserve the blocked state, inspect the installed Kit contract,
and use only the supported fresh-context predecessor once identified.

**Required Kit repair direction:** Make external-workspace merge lifecycle
context-aware and closed. Either (a) generate/refresh required fresh-context
artifacts inside the high-level merge wrapper, (b) classify them as not
applicable when the external-workspace safety evidence is already sufficient, or
(c) return a machine-readable exact predecessor command/plan that creates the
required artifacts without operator inference.

**Required regression/acceptance evidence:** In a fresh external workspace,
create a PR, pin its exact head SHA, obtain green required CI and CLEAN merge
state, then invoke the regular high-level safe-merge route. The route must either
merge successfully or deterministically expose and execute/identify the exact
supported fresh-context predecessor. It must not require fabricated outbox or
handoff-report files and must not require the recovery-only skip flag.

**Evidence sources / IDs:**

- Step 207 terminal evidence
- PR #22, head `4edace6738a34a0fee98aca9daf85c4d25063f29`
- blocker `outbox_missing`
- blocker `latest_handoff_report_missing`
- `.agentic/transfer/outbox/last_result.txt`
- `.agentic/state/handoff/transfer_handoff_reports/latest-transfer-handoff-report.json`

---
