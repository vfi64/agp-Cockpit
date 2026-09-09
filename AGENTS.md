# AGENTS.md

Repository-wide rules for AGP Cockpit development.

## Normative boundary

Read `docs/planning/SCOPE_BOUNDARY.md` first.

Remote Development LLM = development reasoning, diagnosis, planning, next action.
AGP Cockpit = deterministic durable task orchestration and transport.
Agentic Project Kit = governed repository workflow/lifecycle authority.
Human = explicit checkpoints and contract/scope adjudication.

Cockpit must not become a local development planner, Kit-command selector,
GitHub/FILE_TRANSFER replacement or local-LLM coding agent.

## Current evidence before memory

Use current repository and installed Kit evidence. Do not reconstruct current
Kit commands/schemas/lifecycle from chat memory.

## Maintainer local work

Until accepted self-hosting replaces it, use numbered Python scripts in
`<repo>/Download/`. Scripts must support `--self-test` without mutation,
preflight state, fail closed, use the highest appropriate Kit orchestrator,
produce one compact return bundle, and print a truthful result banner.

## Kit-first lifecycle

Current Kit orchestrator > workflow wrapper > primitive > custom Git/GitHub.
Never bypass Kit BLOCKED/FAIL through raw Git/GitHub.

## Runtime authority

Cockpit may validate protocol/state/capabilities, persist task state, enforce
effects, collect bounded evidence, manage budgets/checkpoints, reconcile
unknown outcomes, transport messages and verify completion evidence.

Cockpit may not decide product code, semantically diagnose development failure,
invent/repair work orders, choose alternate Kit commands, infer permissions
from LLM text, blindly replay unknown effects, or accept Remote COMPLETE as
terminal without verification.

## Hermes/local LLM

Optional and outside correctness-critical path. It may not alter policy, work
orders, Kit decisions, checkpoints or completion decisions.

## Tests/gates

Every slice requires applicable focused/full tests, exact-revision CI and Kit
gates. Do not weaken gates to make recovery succeed.

## Persistence/recovery

OUTCOME_UNKNOWN never permits blind replay. Missing/corrupt persistence is not
assumed success. New action IDs cannot bypass unresolved predecessor effects.

## Systemic failure

After two substantive failed repairs in one failure domain, perform
SYSTEMIC_FAILURE_REVIEW before a third product mutation.
