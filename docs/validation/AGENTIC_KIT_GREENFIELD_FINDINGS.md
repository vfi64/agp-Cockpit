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
| 2026-09-07 | `GF-E021` | `Phase-8 Steps 335 / 335R1` | `KIT-GF-018` | merged-work-branch cleanup returned BLOCKED/remote_delete_failed although authoritative remote ref was already absent; stale remote-tracking state remained |

| 2026-09-08 | `GF-E022` | `Phase-10 Steps 504-509` | `KIT-GF-019` | restore-known-volatile missed archived transfer outbox residue and external pr-merge-safe blocked despite green CI |

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

---

### KIT-GF-018 — Merged-work-branch cleanup is not idempotent when the authoritative remote ref is already absent

First observed: 2026-09-07
Status: OPEN
Severity: medium
Classification: agentic-kit-ux-contract
Historical aliases: none

**Expected**

After verified merge, `delete-merged-work-branch` must adjudicate the desired cleanup postcondition. If the authoritative remote branch is already absent, remote cleanup is already satisfied and the wrapper must return deterministic PASS/NOOP or an equivalent successful idempotent state.

**Observed**

During Phase-8 final housekeeping, `delete-merged-work-branch` successfully verified the PR as MERGED, then attempted `git push origin --delete feature/phase8-automated-multi-round-bridge`. Git reported `remote ref does not exist`; the wrapper returned BLOCKED with blocker `remote_delete_failed`. Step 335R1 independently proved that the authoritative remote ref was already absent and only stale local remote-tracking state had made cleanup appear necessary.

**Impact**

Automated lifecycle/housekeeping can block despite the desired end state already being achieved, forcing agents to diagnose a false mutation failure when no repair mutation is required.

**Validated/temporary workaround**

Adjudicate authoritative remote state read-only before retrying cleanup; when authoritative absence is proven, do not repeat the delete mutation. Prune stale local tracking state only when separately justified.

**Required Kit repair direction**

Before and/or after remote deletion, distinguish an existing ref with successful deletion, an already-absent authoritative ref, stale local remote-tracking state, and a genuine transport/permission/delete failure. Already absent must be successful idempotent cleanup; a genuine failure deleting an existing ref must remain fail-closed.

**Required regression/acceptance evidence**

- merged PR + remote branch present -> delete -> PASS
- merged PR + remote branch already absent -> PASS/NOOP
- stale local `origin/<branch>` tracking ref + authoritative ref absent -> PASS/NOOP
- PR not merged -> BLOCKED
- remote ref exists and actual delete fails -> BLOCKED

**Current repair status**

Kit 1.0.9: **NOT_PROVEN_FIXED**. Step 347 source inspection still found the direct `git push origin --delete <branch>` path followed by `remote_delete_failed`, with no proven already-absent success path.

**Evidence sources / IDs**

- Phase-8 Step 335 final housekeeping
- Phase-8 Step 335R1 remote-branch absence adjudication
- Step 347 Greenfield ledger reconciliation
- Kit 1.0.9 `cli_commands/transfer_repo_pre_pr.py`


### KIT-GF-019 — restore-known-volatile does not cover archived transfer operational residue

First observed: 2026-09-08
Status: OPEN
Severity: high
Classification: agentic-kit
Historical aliases: none

**Expected**

Kit-owned volatile transfer cleanup must cover operational residue wherever the Kit itself relocates it, or merge preflight must exclude semantically archived operational artifacts from target-repository product dirtiness.

**Observed**

During Phase-10 closeout, the supported `transfer restore-known-volatile` path knew the active `.agentic/transfer/outbox/last_result.txt` path but did not remove an archived copy at `.agentic/transfer/archive/.../.agentic/transfer/outbox/last_result.txt`. That untracked Kit-owned operational residue caused `external_pr_merge_preflight` / `pr-merge-safe` to block although PR #43 had green required CI and was otherwise ready to merge. The supported transfer closeout path later removed the archive residue, after which the existing PR lifecycle completed and Phase 10 merged successfully.

**Impact**

A high-level external-workspace lifecycle can deadlock at safe merge because Kit-generated archival residue is classified as target-repository dirtiness while the advertised known-volatile restoration surface cannot clean it.

**Validated/temporary workaround**

Preserve the evidence, use supported Kit transfer closeout/cleanup rather than raw Git deletion, then re-run the existing high-level PR lifecycle. Do not recreate the PR or bypass merge safety.

**Required Kit repair direction**

Make volatile ownership recursive/location-aware across Kit-created transfer archives, or make archive creation/closeout transactional so no merge-blocking operational residue remains. `restore-known-volatile` and external merge preflight must share the same ownership classification.

**Required regression/acceptance evidence**

Create Kit transfer outbox state, archive it through the supported lifecycle, and verify that the supported cleanup/restore path leaves no Kit-owned archived operational residue that blocks `pr-merge-safe`. Genuine product dirtiness must remain fail-closed.

**Evidence sources / IDs**

- Phase-10 Steps 504-509
- PR #43
- `.agentic/transfer/archive/.../.agentic/transfer/outbox/last_result.txt`
- `transfer restore-known-volatile`
- `external_pr_merge_preflight`

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

## KIT-GF-LESSON-MEGABLICK-001 — Megablick before repeated micro-patching

**Status:** ACCEPTED_GREENFIELD_LESSON

**Finding:** When repeated patch failures expose successive coupled symptoms in the same failure domain,
local fail-fast output can make one systemic model drift look like a sequence of unrelated defects.

**Lesson:** After the second failed mutation in one patch family, stop mutation and perform a bounded,
read-only Megablick over lifecycle/call path, coupled invariants, persistence/restart behavior, delivered-path
wiring, authority/confinement, and related tests. Distinguish product defect from stale test model, then make
one coherent justified repair and validate broadly. Do not infer closure from static symbols alone.

**Evidence:** Steps 592R9–592R14: a hardened seven-action runtime was correct while a legacy Phase-18 fixture
retained several six-action expectations. Pytest fail-fast exposed them sequentially; the Megablick identified
the common model drift and the coherent correction closed all runtime gates.

## KIT-GF-LESSON-COMMAND-AUTHORITY-001 — Kit command authority must govern LLM repository work

**Status:** ACCEPTED_GREENFIELD_LESSON

**Finding:** Agentic Project Kit only delivers its intended repository/workflow
governance value when LLM-generated repository work is forced through the Kit's
existing command-authority and workflow gates. Merely having Kit commands
available is insufficient if an LLM can guess CLI options, reconstruct raw
Git/GitHub workflows, or continue after missing authority surfaces.

**Lesson:** Every LLM work order that manages repository state must fail closed
unless the exact Kit command, options, required parameters, workspace
applicability, and lifecycle route are proven from the installed command
manifest and `agentic-kit command-for`. Existing Kit mechanisms such as
`audit-command-authority`, `instruction lint`, `rules validate-sources`,
`rule-registry`, `workflow-guard`, workspace orchestrators, and `work finish`
must be used as enforcement gates. A Kit BLOCKED/FAIL must never be bypassed by
inventing operating-layer files or reconstructed git/gh commands.

**Evidence:** Steps 597–601R2 exposed avoidable LLM-side command assumptions.
Step 601R2 then demonstrated that the packaged `audit-command-authority`
mechanism correctly fails closed on missing command-authority terms and handoff
surfaces. The remedy is therefore mandatory use of existing Kit governance, not
a parallel mechanism.

## KIT-GF-RULE-REGISTRY-BOOTSTRAP: external-workspace rule-registry bootstrap gap

- Status: CONFIRMED
- Evidence: 601R5 and 601R6 disposable/read-only adjudication.
- Finding: an already initialized external workspace can be valid for workspace adoption while `agentic-kit rule-registry check` hard-fails because `.agentic/rule_mechanism_inventory.yaml` is absent.
- No automatic Kit producer was found among the manifest-proven workspace/rules paths tested, and `rule-registry register` requires reviewed semantic values that are not completely defined by authoritative repository evidence.
- Required behavior: fail closed. Do not invent registration values and do not hand-create Kit-owned inventory state.
- Product implication: Kit Greenfield/adoption must either provide a deterministic bootstrap/adoption path for the rule-mechanism inventory or make applicability explicit so non-applicable external workspaces are not blocked by this gate.
- Remediation policy for this repository: continue only with gates whose applicability is established for the external workspace; preserve this finding for Kit repair.


## Method/tooling lessons — authority and fail-closed guards

### KIT-GF-LESSON-AUTHORITY-BEFORE-MUTATION-001 — ACCEPTED_GREENFIELD_LESSON

**Finding:** LLM repository work becomes unreliable when command syntax, source shape, policy files, or workflow prerequisites are inferred instead of established from repository and installed-Kit authority.

**Lesson:** Before mutation, establish exact command authority with the installed manifest and agentic-kit command-for, and establish exact source/schema shape from the repository. If authority is missing or contradictory, fail closed and diagnose; never fabricate Kit-owned state or reconstruct a mapped raw Git/GitHub workflow.

**Impact:** This removes avoidable mutation failures caused by guessed CLI contracts, guessed JSON structures, and guessed policy prerequisites.

**Evidence:** Steps 597-601R2, Steps 609-611.

### KIT-GF-LESSON-GUARD-PREREQUISITE-001 — ACCEPTED_GREENFIELD_LESSON

**Finding:** A mandatory workflow guard currently dereferences .agentic/rule_preservation.yaml unconditionally even though this external workspace neither tracks nor historically contained that file.

**Lesson:** A fail-closed guard must distinguish a policy violation from absent or non-applicable adoption prerequisite state. Missing prerequisite authority must produce a bounded actionable diagnostic, not an unhandled traceback; the caller must not synthesize the missing policy file.

**Impact:** External-workspace governance remains strict without forcing agents to invent Kit-owned policy state.

**Evidence:** Step 609 workflow-guard traceback, Step 610 tracked/history/source adjudication, Step 611 diagnose reproduces FileNotFoundError.

### KIT-GF-LESSON-DRYRUN-EXECUTE-PARITY-001 — ACCEPTED_GREENFIELD_LESSON

`work finish --dry-run` accepted `.agentic/rule_ack/current.json` in the commit path set, while execute rejected that same volatile runtime path. Dry-run must validate the same path-admissibility constraints as execute so an apparently executable plan cannot fail only after lifecycle side effects have begun.

### KIT-GF-020 — External-workspace governance requires a non-persistable empty transfer inbox directory

**Expected:** A valid external workspace remains governance-valid across clone/checkout. Empty runtime carriers are Kit-provisioned, persistably represented, or accepted as a legitimate absent/empty state.

**Observed:** `workspace init` owns `.agentic/transfer/inbox`, while `governance check` requires the directory itself. Git cannot persist an empty directory, and the authority probe established no supported standalone producer authorizing manual fabrication.

**Impact:** External-workspace lifecycle work can be blocked by ephemeral filesystem shape rather than missing semantic state.

**Rule for ongoing LLM work:** Never infer or fabricate Kit-owned workspace files/directories. Resolve applicability and command authority first; if no supported producer exists, record the Kit defect and fail closed.

**Repair:** Close the lifecycle across checkout through deterministic Kit provisioning/persistable carrier semantics or by making governance consume the legitimate empty-state model used by transfer state.

**Regression:** init → commit/push → fresh clone/checkout → governance succeeds without manual inbox creation; NO_COMMAND remains deterministic.


## KIT-GF-021 — External-workspace Kit CLI discovery can misdiagnose an intact project-local installation as missing

**Status:** OPEN

**Finding:** Workspace troubleshooting can treat Agentic Project Kit as absent when it is not globally discoverable even though the external workspace has a functional project-local `.venv` installation.

**Evidence:** Step 1277 proved `agentic-project-kit 1.0.10` already installed in `agp-Cockpit/.venv`, upgraded that exact environment to 1.0.13, and then passed `command-for`, `check`, and `doctor`.

**Required Kit repair:** Resolve and report workspace-owned executable/environment provenance deterministically before global PATH assumptions. Upgrade/install guidance must preserve the selected environment.

**Regression:** A project-local Kit with no global PATH entry is detected as installed and upgraded in place.

## KIT-GF-022 — command-reference-refresh is not closed for packaged Kit use in an external workspace

**Status:** OPEN

**Finding:** Kit 1.0.13 detects stale repo-local command authority but its prescribed refresh route assumes a Kit development-checkout script that is absent from the external workspace.

**Evidence:** Step 1278 produced `JSON_DRIFT`; Step 1279 confirmed `command-reference-check` FAIL; Step 1280 showed `command-reference-refresh` invoking missing `scripts/generate_agentic_kit_command_reference.py`; Step 1281 proved the released package hard-codes that checkout-local path and exposes no matching packaged generator file.

**Required Kit repair:** Make refresh package-backed and workspace-aware. It must regenerate/synchronize from packaged command-manifest authority or provide one exact supported executable remediation. It must not depend on Kit source-checkout layout.

**Regression:** Released wheel + fresh external workspace + stale command reference -> check detects drift -> refresh succeeds without source checkout -> subsequent check/audit PASS.

<!-- AGP_FINDINGS_2026_10_01 -->
## Findings 2026-10-01/02 (K07 lifecycle runs 1520-1560)

Status vocabulary (JSON `status_vocabulary`): OPEN, CONFIRMED, FIXED (`fixed_in`), VERIFIED_FIXED
(`verified_by`). A Cockpit mitigation (`cockpit_mitigation`) never changes the status.

| Date | Event | Evidence | Canonical family | Observation |
|---|---|---|---|---|
| 2026-10-01 | `GF-E027` | Steps 1534-1545 | `KIT-GF-011` | post-merge refresh rewrote status.md after #140 |
| 2026-10-01 | `GF-E028` | GitHub Actions #490/#491/#501-#503 | `KIT-GF-026` | unpinned Kit, duplicate runs and 3-8 min CI in the managed template |
| 2026-10-01 | `GF-E029` | Step 1551 | `KIT-GF-027` | pr-create-complete rc 2 for a red PR CI; 37 KB output |
| 2026-10-01 | `GF-E030` | K07 handoff 2026-10-01 §3.1-3.3 | `KIT-GF-023` | --json output with trailing FINAL_SIGNAL lines |
| 2026-10-01 | `GF-E031` | ci_gate.main_ci | `KIT-GF-024` | no Kit read command for main CI after a merge |
| 2026-10-01 | `GF-E032` | kit_command_catalog | `KIT-GF-025` | manifest without remote-effect classification |
| 2026-10-02 | `GF-E033` | Kit 1.0.13 sources | `KIT-GF-028` | hard-coded /tmp logs and diffs |

Extensions of existing families:

- `KIT-GF-010` (2026-10-01): Rule acknowledgement after a rule-source change on main (#134) — After a rule source changed on main, push stayed blocked until `rules acknowledge` ran. Invalidation itself is intended (regression clause); the orchestrators neither re-acknowledge nor name it as the next action.
- `KIT-GF-011` (2026-10-01): Post-merge refresh re-marks itself as open; Kit-owned files dirty after lifecycle — After refresh #140 the Kit rewrote .agentic/state/status.md ('refresh state after PR #139 ... dd4a15d4') on the leftover branch; the next finish run needed an extra step (1549) to remove it. .agentic/rule_ack/current.json is dirty after each lifecycle and the handoff package after Chat wechseln.
- `KIT-GF-017` (2026-10-01): transfer pr-create blocked by the fresh-LLM-context gate — transfer pr-create stopped at the gate for fresh LLM context carriers; the orchestrators do not refresh the carriers themselves.

## KIT-GF-023 — --json output is not pure JSON

- Status: OPEN · Severity: medium · First observed: 2026-10-01
- Expected: Commands invoked with --json print exactly one JSON document on stdout.
- Observed: Lifecycle commands append FINAL_SIGNAL=... and similar lines after the JSON document; consumers must cut the JSON out heuristically.
- Impact: Every consumer (Cockpit CI gate, remote work orders) needs tolerant parsing; a format change silently breaks evidence extraction.
- Workaround: Cockpit extracts the outermost JSON object/array (ci_gate._json_from).
- Repair: Emit signals on stderr or inside the JSON document when --json is set.
- Regression: Every --json command parses with json.loads(stdout) unchanged.

## KIT-GF-024 — No read command for the CI of a commit or branch without a pull request

- Status: OPEN · Severity: medium · First observed: 2026-10-01
- Expected: A read-only Kit command reports the CI verdict of a commit (e.g. main after a merge).
- Observed: pr status and pr wait-ci require a PR number; main CI after a merge can only be read with raw gh run list.
- Impact: The Cockpit's lifecycle verification has to call gh directly, outside the Kit command authority.
- Workaround: ci_gate.main_ci() uses gh run list / gh run view --log-failed.
- Repair: Add e.g. `agentic-kit ci status --commit <sha> --json`.
- Regression: Post-merge verification works with Kit commands only.

## KIT-GF-025 — Command manifest does not classify remote effects

- Status: OPEN · Severity: high · First observed: 2026-10-01
- Expected: Each manifest command declares whether it pushes, fetches, opens/merges PRs or publishes.
- Observed: Surface and safety are present, remote effect is not; the Cockpit keeps its own lists (REMOTE_EFFECT_COMMANDS, PUBLISHING_COMMANDS, MERGE_COMMANDS).
- Impact: Approval gating depends on a second, hand-maintained classification that can drift from the Kit.
- Workaround: Cockpit lists; unknown effects are treated as remote and ask the human (AGP_REMOTE_EFFECT_ASKS_HUMAN_V1).
- Repair: Add an effect classification (none/local/remote/destructive) to the manifest.
- Regression: Cockpit approval gating derives entirely from the manifest.

## KIT-GF-026 — Managed CI template: unpinned Kit, duplicate runs, no browser cache, no update path

- Status: OPEN · Severity: high · First observed: 2026-10-01
- Expected: The managed template pins the Kit version, runs once per commit, caches browsers, and can be updated by a Kit command.
- Observed: `pip install agentic-project-kit` without version; push and pull_request on all branches (two runs per PR commit, e.g. #501/#502); Playwright browsers and apt deps on every run (3-8 min, #490 vs #491, #503 6:23); runs over 300 s exceed the orchestrators' default --timeout-seconds 300. Only `workspace init` writes the template; no command transfers a changed template to .github/workflows/, and `workspace remove` describes itself as removing only unchanged Kit files.
- Impact: CI may check with a different Kit than the developer (determinism leak); doubled CI cost and wait time inside every lifecycle turn.
- Workaround: Cockpit-side template change AGP_CI_GATE_V2 (PR #143).
- Repair: Ship the template with a pinned Kit version, push only on the default branch, PR concurrency, browser cache, and provide a template update command.
- Regression: One run per PR commit plus one per main commit; CI Kit version equals the workspace Kit version.
- Cockpit mitigation (2026-10-01, `AGP_CI_GATE_V2`): Template changed in .agentic/ci and mirrored: push only on main, PR concurrency, Kit pinned to 1.0.13, parallel python/browser jobs, browser cache, aggregate check agentic-gate. Live: runs #504-#507, 1:46-2:06 instead of 2:50-6:23.

## KIT-GF-027 — Orchestrator output size and non-zero return code for a red CI finding

- Status: OPEN · Severity: medium · First observed: 2026-10-01
- Expected: Orchestrators summarize (result, next action, failed steps in detail) and report a red CI as a structured finding.
- Observed: pr-closeout-complete printed 28 KB, pr-create-complete 37 KB of step output; pr-create-complete returned rc 2 for a red PR CI (step 1551), which the runner treats as an execution failure.
- Impact: Large remote-context cost per turn; an extra recovery turn for a domain finding.
- Workaround: Cockpit result projection (AGP_RESULT_PROJECTION_V1) shortens success output; the recovery prompt carries the candidate bundle projection.
- Repair: Compact summary by default or --summary; distinguish 'ran, finding red' (rc 0, decision red) from 'could not run'.
- Regression: Finish run with one red CI repair needs no recovery-only turn; orchestrator stdout under ~4 KB on success.
- Cockpit mitigation (2026-10-01, `AGP_RESULT_PROJECTION_V1`): Deterministic projection of result files for the remote side; finish run 1547-1555: 399 KB -> 117 KB.

## KIT-GF-028 — Kit writes to fixed /tmp paths

- Status: OPEN · Severity: low · First observed: 2026-10-01
- Expected: Temporary files go to tempfile.gettempdir() (honouring TMPDIR) or a repository-local tmp directory.
- Observed: Logs /tmp/agentic-project-kit-*.log and protected-change diffs /tmp/<label>.diff (transfer repo-pre-pr) use a hard-coded /tmp; artifact-gc --tmp-logs collects only the logs.
- Impact: Files outside the repository accumulate; the Cockpit cannot redirect them with TMPDIR.
- Workaround: Cockpit maintenance runs `agentic-kit artifact-gc --tmp-logs --execute`.
- Repair: Use tempfile.gettempdir() / repository tmp; include the diffs in artifact-gc.
- Regression: With TMPDIR set, no Kit file appears under /tmp.

<!-- AGP_FINDINGS_2026_10_02 -->
## Kit-side adjudication (snapshot 2026-10-02, Kit commit `26be95becefb`)

Read from the Kit repository's `docs/reports/*.json` by `core/kit_findings_sync.py`
(AGP_KIT_FINDINGS_SYNC_V1). `fixed_in` is derived from CHANGELOG release dates
(first release after the first statement of the final closed streak; a statement
about a released package names that release). This snapshot does not change the
ledger `status`; a finding becomes VERIFIED_FIXED only with evidence from this
workspace.

| Family | Kit state | Fixed in | Latest Kit statement | Report |
|---|---|---|---|---|
| `KIT-GF-001` | PARTIAL | — | external_init_retested_pass_remaining_provenance_under_gf_007 | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-002` | CLOSED | 1.0.9 | fixed | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-003` | PARTIAL | — | partially_addressed_post_merge_successor_evidence_deferred | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-004` | CLOSED | 1.0.9 | fixed | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-005` | PARTIAL | — | external_first_cycle_start_retested_pass_closeout_tied_to_gf_009_and_g | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-006` | CLOSED | 1.0.9 | fixed | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-007` | CLOSED | 1.0.13 | closed_current_main_external_fixture | POST_V1_0_12_GREENFIELD_PROVENANCE_RETEST_20260915.json |
| `KIT-GF-008` | CLOSED | 1.0.9 | fixed | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-009` | CLOSED | 1.0.13 | PASS | KIT-GF-009 is externally closed for the tested boundary. | POST_V1_0_13_GF009_PRIVATE_RELEASED_PACKAGE_RETEST_20260916.json |
| `KIT-GF-010` | CLOSED | 1.0.9 | fixed_released_package_retest_pass_for_rule_ack_routing | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-011` | OPEN | — | open_external_released_package_evidence_required | POST_V1_0_12_RELEASED_PACKAGE_CONTEXT_RETEST_20260916.json |
| `KIT-GF-012` | CLOSED | 1.0.9 | fixed | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-013` | CLOSED | 1.0.9 | fixed_in_v1_0_9 | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |
| `KIT-GF-014` | CLOSED | 1.0.13 | closed_current_checkout_external_fixture | POST_V1_0_12_GREENFIELD_REMAINING_CLOSEOUT_20260915.json |
| `KIT-GF-015` | CLOSED | 1.0.13 | closed_current_checkout | POST_V1_0_12_GREENFIELD_REMAINING_CLOSEOUT_20260915.json |
| `KIT-GF-016` | CLOSED | 1.0.13 | closed_current_checkout_external_smoke | POST_V1_0_12_GREENFIELD_REMAINING_CLOSEOUT_20260915.json |
| `KIT-GF-017` | OPEN | — | open_repair_and_released_package_retest_required | POST_V1_0_12_RELEASED_PACKAGE_CONTEXT_RETEST_20260916.json |
| `KIT-GF-018` | CLOSED | 1.0.10 | fixed_in_this_slice | POST_V1_0_10_GREENFIELD_REMAINING_FINDINGS_20260908.json |

Note: KIT-GF-011 remains open on the Kit side; the 2026-10-01 runs with Kit 1.0.13
(steps 1534-1549) still showed the post-merge refresh re-marking itself and
Kit-owned files dirty after lifecycle runs (extension of KIT-GF-011).

## KIT-GF-029 — Release lifecycle assumes public publication; no private-release policy

- Status: VERIFIED_FIXED (fixed in 1.0.14, retest 2026-10-03 GF-E036) · Severity: high · First observed: 2026-10-02
- Expected: a managed repository can declare that it is never published; then no GitHub Release is required and no Zenodo/DOI record is created, updated or queried; the managed repository's documentation states the policy.
- Observed (Kit 1.0.13 / main 26be95b): `post-release-check` FAILs without a GitHub Release; Zenodo is skipped only with a WARN when CITATION.cff has no DOI; the CHANGELOG quality check requires a Zenodo DOI or pending marker per release (Kit's own checks; external applicability not verified); closeout templates assume GitHub Release, PyPI and Zenodo; no publication policy switch exists.
- Workaround / Cockpit mitigation (`AGP_RELEASE_POLICY_V1`): `docs/planning/release_policy.json` and `docs/planning/RELEASE_POLICY.md`; work orders with publication steps are rejected.
- Repair: publication policy in the workspace manifest (none | github | github+pypi | github+pypi+zenodo) gating publish, DOI closeout, post-release checks and CHANGELOG markers; rendered into the managed repository's docs.

## KIT-GF-030 — pr-create-complete opens a second pull request for an already squash-merged branch

- Status: OPEN · Severity: high · First observed: 2026-10-02
- Expected: `transfer pr-create(-complete)` refuses or reports DONE when the head branch adds nothing to the base (squash-aware); post-merge removes or marks the merged remote head branch.
- Observed (Kit 1.0.13, steps 1573/1574): after PR #147 (squash), refresh #148 and a passing post-merge, the remote head branch stayed on origin; re-running `pr-create-complete` for it opened PR #149 without content difference, ran CI #516/#517 and finally merged the empty commit `44e0c69` (`git diff 5c1544c 44e0c69` is empty).
- Workaround / Cockpit mitigation (`AGP_MERGED_BRANCH_GUARD_V1`, `AGP_REPOSITORY_FACTS_V1`): pr-create work orders for a merged head branch are rejected as correctable violations; every continuation carries locally verified repository facts.
- Repair: squash-aware comparison before creating a pull request, report the merged PR; clean up the merged remote head branch.

## KIT-GF-031 — pr-complete: no --post-merge-complete and a fresh-context blocker mid-lifecycle

- Status: OPEN · Severity: medium · First observed: 2026-10-02
- Observed (Kit 1.0.13, steps 1578–1581): `pr-complete 149 --post-merge-complete` BLOCKED (invalid argument); without it BLOCKED by `require-fresh-llm-context` right after the Kit's own post-merge run; `refresh-llm-context-carriers` needed first.
- Repair: same lifecycle options as `pr-create-complete`; the orchestrator refreshes the carriers it requires.

## KIT-GF-027 — extension 2026-10-02: verdict only at the start of the JSON

- Step 1573: the verdict of `pr-create-complete --json` (PR number, merge, result_status) stands at the start of ~20 KB of JSON whose end is a restore sub-step; a work order keeping the stdout tail lost it, and the remote side re-ran the orchestrator (KIT-GF-030).

## KIT-GF-032 — Release preparation is self-hosting only

- Status: OPEN · Severity: high · First observed: 2026-10-02
- Observed (Kit 1.0.13, clone of agp-Cockpit main 25afb5d): `release-prep --dry-run` fails on the hard-coded path `src/agentic_project_kit/__init__.py`; `release ready --version 0.1.0` is BLOCKED (version 0.1.0.dev0 rejected, package version mismatch, no previous tag for a first release, release notes missing_ref, currency audit checks the Kit's own package, DOIs, CITATION.cff and CHANGELOG.md, docs audit requires Kit documentation files, 16 Cockpit planning documents flagged); `release ready` also runs `transfer sync-main`. No Kit route pushes a tag without `release-publish`.
- Impact: no Kit-conform release of an external workspace; P11 has no Kit route.
- Repair: workspace-derived version sources, first release without previous tag, audits scoped to registered documents, private-release route (prepare, annotated tag, tag push) under the publication policy of KIT-GF-029.

## KIT-GF-011 — extension 2026-10-02: work start leaves Kit-owned files dirty

- Step 1594 `work start` (rc 0) left Kit-owned transfer files modified; step 1596 needed `work recover` and `transfer restore-known-volatile`.

## KIT-GF-033 — No recovery route for main with local changes or local commits

- Status: VERIFIED_FIXED (fixed in 1.0.14, retest 2026-10-03 GF-E037) · Severity: high · First observed: 2026-10-02
- Observed (Kit 1.0.13, sandbox clone of agp-Cockpit main ad2a38d): `transfer branch-create … --start-point HEAD` refuses a dirty main ("Clean or preserve local changes before creating a branch."); `work discard-changes` is blocked on main (`main-branch`); `transfer sync-main` fails when main is ahead of origin/main (`normalize-session_failed`); `work recover` never resets, cleans or checks out product files. Covered by the Kit: main behind origin/main (`transfer sync-main`), detached HEAD (`transfer branch-switch main`), discarding changes on a work branch (`work discard-changes` with dry-run signature). The Kit's work-order validator forbids `git reset --hard`, so a remote work order cannot fill the gap.
- Impact: the full Wiederherstellen button (P8) has no Kit route for the two most common disturbances; any workaround would put raw git outside the Kit.
- Owner's decision 2026-10-02: the full P8 waits for this fix (like P11 for KIT-GF-029/032); the basic Wiederherstellen stays (remote diagnosis, Kit routes only, NEEDS_HUMAN where the Kit has no route).
- Repair: a non-lossy rescue route (e.g. `work rescue --json`): rescue branch for changes or commits, main realigned with origin/main after a containment check, dry-run signature, no remote effect.

## KIT-GF-032 — update 2026-10-02: owner's decision

- Release 0.1.0 was made by hand. The Release button (P11) waits for a Kit route that respects `publication: none` (KIT-GF-029) and external workspaces (KIT-GF-032); no Cockpit-local release procedure.

## 2026-10-03 — Retest with Kit 1.0.14 (sandbox clones of main 81b2dfb)

- KIT-GF-029 → VERIFIED_FIXED (GF-E036): with `publication: none` in `.agentic/config.yaml`, gh/curl replaced by failing shims and no network, `release-plan` renders local tag steps only; `post-release-check` PASS by policy; `post-release-doi-closeout --json` is a PASS no-op without a Zenodo query; `release-publish` (dry-run and `--execute --allow-execute`) PASS with publishing disabled; no gh/curl call, no tag.
- KIT-GF-033 → VERIFIED_FIXED (GF-E037): `work rescue` with dry-run signature recovers dirty main (changes committed on `rescue/main-…`) and main two commits ahead (rescue branch contains both commits); afterwards main == origin/main and the worktree is clean; a wrong signature is BLOCKED without change; repeated runs report `rescue_required: false`; no remote effect. The full P8 Wiederherstellen is no longer Kit-gated and follows as its own P step.
- KIT-GF-032 stays OPEN (GF-E038): `release-check` still requires `src/agentic_project_kit/__init__.py`, CITATION.cff, docs/STATUS.md and docs/handoff/CURRENT_HANDOFF.md in an external workspace. P11 Release now waits only for KIT-GF-032.
- The managed CI template pins Kit 1.0.14.

## KIT-GF-034 — post-release-doi-closeout --write leaves the committed docs-pages fallback site stale

- Status: OPEN · Severity: medium · First observed: 2026-10-03 (GF-E039)
- Expected: the DOI closeout writes every projection that depends on the release records it changes, including `docs/site`, so the closeout pull request passes the Kit's own CI.
- Observed (Kit release 1.0.14, PR #2348, CI run 37122569105): `post-release-doi-closeout --version 1.0.14 --write` updated CHANGELOG, CITATION, README, STATUS, CURRENT_HANDOFF, VERIFIED_RELEASES and the closeout report, but not `docs/site`; `test_docs_pages_fallback_projection_is_fresh` failed (v1.0.9 / 10.5281/zenodo.22541661 instead of v1.0.14 / 10.5281/zenodo.23120536). `python site/scripts/build.py --docs-pages-fallback --json` plus `work finish` on the same branch (PR reused) made it green; merged as 43d30d23.
- Workaround: regenerate the fallback site on the closeout branch before `work finish` (maintainer's local release script).
- Repair: the closeout rebuilds the docs-pages fallback projection and includes `docs/site` in its changed paths, or names the step with a staleness preflight.

## KIT-GF-035 — docs-audit checks the Kit's own document set in an external workspace

- Status: OPEN · Severity: high · First observed: 2026-10-03 (GF-E040)
- Observed (Kit main 3b6c5eb7, clone of agp-Cockpit with `publication: none`): `docs-audit` fails six of seven dimensions on Kit files — 16 required Kit documents, the fixed doc mesh (README marker, CITATION.cff, `src/agentic_project_kit/__init__.py`, STATUS, CURRENT_HANDOFF), the successor-chat sources of the compiled agent context, registry classes; `doc-lifecycle-audit` exits 1 although `doc_lifecycle: warn`.
- Impact: without the skip, `release ready` cannot pass in an external workspace; the standalone `docs-audit` and `doc-lifecycle-audit` still fail on Kit files.
- Workaround (Kit #2354, KIT-GF-032 slice C, main 7b3cd57a): the release scan records `docs-audit` as skipped in external workspaces; `release ready` reports doc-lifecycle findings as warnings under `doc_lifecycle: warn`.
- Repair (design decision per rule group): required documents from manifest/registry; doc mesh from the version anchors and registered documents; handoff contracts only with the transfer module; registry classes; `doc_lifecycle: warn` non-blocking in `docs-audit` and `doc-lifecycle-audit` as well.

## 2026-10-03 — Retest of KIT-GF-032 with Kit main c912afe0 (GF-E041)

- Slices A–D are merged in the Kit (#2350, #2352, #2354, #2356). Sandbox clone of main 3762b8a with `publication: none`: `release ready --version 0.1.0` passes sync-main, doc-lifecycle-release-review and release-status; the Kit self-hosting checks are recorded as skipped.
- Still BLOCKED by the standard-error scan, so KIT-GF-032 stays OPEN:
  1. Fresh-context check: `outbox_missing`, `latest_handoff_report_missing`. The carriers live in excluded runtime paths, and `release ready`'s own sync-main removes them. After `transfer refresh-llm-context-carriers` the standalone scan passes this step.
  2. `release-notes-generate`: six PR items unclassified (#164, #172, #174, #176, #178, #180); no PR body carries a `release-note-category:` line.
  3. `release-notes-generate` writes `tmp/release-<n>-summary-lines.json` into the workspace root; not ignored here, so the next sync-main stops on `external_dirty_worktree`.
- `post-merge-check` NEEDS_SUCCESSOR_PACKAGE_REFRESH came from the sandbox's local commit without a PR.

## 2026-10-03 — KIT-GF-032 verified fixed with Kit 1.0.15 (GF-E042)

- KIT-GF-032 → VERIFIED_FIXED (fixed in 1.0.15; Kit #2350, #2352, #2354, #2356, #2358). Kit 1.0.15 from PyPI in a sandbox clone of main 5e9c26c with `publication: none`: `release ready --version 0.1.1` PASS; `release prepare --version 0.1.1 --write` PASS; `check` and `doctor` PASS. The private tag route was verified on the same Kit code in the GF-E041 sandbox.
- Cockpit prerequisite for P11, not a Kit defect: the Cockpit's version map (AGP_VERSION_MAP_V1: `APP_VERSION`, `docs/releases/versions.json`) is no Kit version anchor, so `tests/test_release_versions.py` fails after `release prepare --write`.
- The managed CI template pins Kit 1.0.15; `.agentic/config.yaml` declares `publication: none`; the Release verb is no longer Kit-gated (plan P11).

## KIT-GF-036 — release prepare writes summary lines that fail the Kit's own CHANGELOG quality gate

- Status: OPEN · Severity: medium · First observed: 2026-10-03 (GF-E043)
- Observed (Kit release 1.0.15): `release prepare --write` used the PR titles as summary lines; they hit two of four CHANGELOG quality categories. `release ready` passed; PR #2360 CI failed in check-docs/docs-audit. Same for 1.0.12.
- Workaround: rewrite the section through `release-prep --summary-line …` on the release branch and push with work finish.
- Repair: check the planned section before writing; accept explicit summary lines in `release prepare`.

## KIT-GF-037 — Workspaces cannot declare further release version anchors

- Status: OPEN · Severity: medium · First observed: 2026-10-04 (GF-E044)
- Observed (Kit 1.0.15): `release prepare --write` updates `pyproject.toml` only; the Cockpit's version map (`APP_VERSION`, `docs/releases/versions.json`) stays behind and `tests/test_release_versions.py` fails on the release branch.
- Workaround (owner 2026-10-04): the P11 work order updates the version map between `release prepare --write` and `work finish`; the test enforces it in CI.
- Repair: manifest key for additional version anchors, used by release-prep, release-check and the release commit integrity check.

## KIT-GF-038 — Live release-publish requires a committed marker file instead of a signed approval

- Status: OPEN · Severity: low · First observed: 2026-10-04 (GF-E045)
- Observed: `release-publish --execute` needs `.agentic/release/ENABLE_LIVE_PUBLISH` committed on main; two extra PRs per release (Kit 1.0.15: #2362, removal in #2364).
- Workaround (owner 2026-10-04): P11 uses the marker flow as it is.
- Repair: signed dry-run approval as in `work rescue`.
