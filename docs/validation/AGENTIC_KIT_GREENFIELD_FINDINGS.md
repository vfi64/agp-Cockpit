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

**Impact**

The Kit cannot simultaneously guarantee committed successor package, exact final-HEAD identity, and clean tracked worktree with the current projection model.

**Validated/temporary workaround**

Render final-HEAD successor projections after the final code/remote HEAD is fixed and keep those exact-final-HEAD projections volatile/uncommitted.

**Required Kit repair direction**

Decouple durable committed handoff source from volatile exact-final-HEAD projection, or introduce a transaction/identity model that explicitly understands the handoff commit boundary.

**Required regression/acceptance evidence**

A disposable clone must prove that final successor authority remains exact and validation-clean without a self-staling render->commit->rerender loop.

**Evidence sources / IDs**

- `AGP_Cockpit_Greenfield_Kit_Defect_Report_2026-09-03.md`
- `AGP_Cockpit_Greenfield_Kit_Handoff_Defects_latest.md`
- `062-D1`
- `062-D2`

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
