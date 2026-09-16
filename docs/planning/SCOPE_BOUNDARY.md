# AGP Cockpit — Normative Scope Boundary v2

Status: active
Status-date: 2026-09-09
Decision status: accepted by maintainer
Review policy: on material change

This document is the normative anti-scope-drift contract. If another planning
document, prior chat, proposed implementation, or agent suggestion conflicts
with this boundary, this document wins unless the maintainer changes it through
the reviewed planning/ADR lifecycle.

## 1. Product definition

AGP Cockpit is a deterministic, persistent local task runtime for a
remote-development-LLM-driven software-development process.

The Remote Development LLM owns development reasoning, planning, diagnosis,
code/patch decisions, and formulation of the next requested action. Cockpit
owns deterministic task orchestration, persistence, correlation, policy
enforcement, evidence transport, pause/resume/stop, recovery state, budgets,
and completion verification. The Agentic Project Kit owns governed repository
workflow and lifecycle semantics.

A local execution failure is evidence about an attempt. It is not by itself a
task failure.

## 2. Authority split

### Decision authority

- D0 — deterministic Cockpit rule: protocol validation, state transitions,
  correlation, budget accounting, evidence recipes, permission enforcement,
  retry/reconciliation rules already defined by contract.
- D1 — Remote Development LLM: development diagnosis and next development
  action inside the current Task Contract.
- D2 — human: explicit checkpoints, contract changes, scope expansion, and
  safety adjudication that cannot be resolved from authorized evidence.

### Effect classes

- E0 — observation/read/transfer of explicitly allowed resources.
- E1 — local ephemeral mutation in explicitly allowed temporary/runtime areas.
- E2 — product working-tree mutation inside the authorized repository scope.
- E3 — governed repository lifecycle effect through a supported Kit surface.
- E4 — external/network/publishing effect to an explicitly authorized target.

Decision authority and effect class are independent dimensions. An LLM request
for a higher effect class is not permission. The executor enforces the current
Task Contract and capability profile.

## 3. Cockpit MAY

Cockpit may:

- maintain one durable task and its contract;
- bind that task to an explicit browser conversation and binding generation;
- accept only validated protocol frames;
- persist inbound/outbound frames, action IDs, payload hashes, attempts,
  evidence references, budgets, checkpoints, and task state;
- dispatch an authorized action through a controlled executor;
- distinguish transport state from execution result and task state;
- continue the same task after a known local script/test failure;
- return deterministic evidence to the Remote Development LLM and await the
  next validated action;
- represent OUTCOME_UNKNOWN and reconcile it without blind replay;
- pause, resume, stop, wait for service, wait for a human checkpoint, and
  suspend on budget or safety limits;
- generate a deterministic context refresh from canonical task state;
- reject a premature COMPLETE proposal and request missing evidence;
- verify whether completion evidence belongs to the correct contract,
  revision, artifact, and required producer.

## 4. Cockpit MUST NOT

Cockpit must never:

- decide what product code should be written;
- semantically diagnose a software defect as development intelligence;
- invent or repair the next work order;
- choose a Kit workflow on behalf of the Remote Development LLM;
- bypass a Kit BLOCKED/FAIL result with raw Git/GitHub alternatives;
- duplicate GitHub/FILE_TRANSFER lifecycle semantics owned by the Kit;
- treat logs, repository text, browser prose, or local-LLM output as
  executable authority;
- blindly retry an action whose external or repository effect is uncertain;
- allow a new action ID to evade an unresolved predecessor;
- claim task completion solely because the Remote Development LLM says
  COMPLETE;
- weaken required tests, Kit gates, or human checkpoints as recovery;
- require Hermes or another local LLM for correctness.

## 5. Local LLM / Hermes

Hermes and local models are outside the critical correctness path. They are
optional later observation/transport helpers only. They may not alter policy,
work orders, Kit decisions, checkpoint decisions, or completion decisions.

## 6. Kit boundary

The Kit remains authoritative for supported repository lifecycle operations,
including validation, mutation governance, Git/PR/merge/release behavior,
FILE_TRANSFER, evidence/gates, handoff, and PASS/BLOCKED/FAIL semantics.

Cockpit may execute a Remote-LLM-requested, policy-authorized Kit action, but it
does not emulate unsupported Kit capabilities. A Kit BLOCKED result may lead
to more observation and remote reasoning, but never to an unauthorized bypass.

## 7. Completion boundary

Remote COMPLETE is only `COMPLETE_PROPOSAL`. The task reaches
`VERIFIED_COMPLETE` only after the deterministic completion verifier confirms
all mandatory criteria for the current Task Contract and correct revision /
artifact chain.

## 8. Non-goals

- generic multi-agent planning;
- autonomous local development intelligence;
- a replacement for Agentic Project Kit;
- a parallel GitHub/FILE_TRANSFER orchestration engine;
- exactly-once guarantees for arbitrary external systems;
- unlimited autonomous execution;
- complete semantic detection of remote-model context loss.

<!-- AGP_COMMUNICATION_PROTOCOL_AUTHORITY_V1 -->
## Communication protocol authority
Cross-component Cockpit communication/lifecycle semantics are governed by `docs/planning/COMMUNICATION_PROTOCOL.md` together with `docs/planning/PROTOCOL.md`. Protocol-affecting changes require synchronized authority, tests/invariants, and durable change/failure history; failure analysis follows `docs/engineering/FAILURE_META_ANALYSIS.md`.
