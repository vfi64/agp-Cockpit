<!-- command-manifest-entrypoint:start -->
MANDATORY FIRST READ: docs/reference/agentic-kit-commands.json (manifest_sha: d1604f13011e). Every reply containing commands MUST start with: COMMAND_MANIFEST_ACK d1604f13011e. Consult `agentic-kit command-for` before proposing commands and choose the most specific available Kit workflow command.
<!-- command-manifest-entrypoint:end -->

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

The authoritative runtime and artifact locations are documented in
`docs/engineering/RUNTIME_PATH_AUTHORITY.md`. Read it before changing any
Bridge, task-operator, browser transport, file-loop, build, or local-evidence
path. Do not introduce a second runtime root.

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

## Megablick failure-domain method (MEGABLICK_FAILURE_DOMAIN_METHOD_V1)

When repeated failures occur in one patch/failure family, do not continue symptom-by-symptom micro-patching.
After the second failed mutation, switch to a bounded read-only **Megablick** before any third mutation:
inspect the complete failure domain, including lifecycle/call path, coupled invariants and counters,
persistent state and restart behavior, delivered product path, effect/resource authority, and all relevant tests.
Classify product defect versus stale/partial test model, identify interacting causes, and derive one coherent
minimal repair. Validate that repair at the narrow failing test, independent adjudication tests, and the
broadest affected regression gate. Static presence alone is not closure when delivered-path behavior is at issue.

<!-- AGP_PROTOCOL_FIRST_RULE_V1 -->
## Protocol-first engineering rule (mandatory)
For every communication/browser/bridge/mission/turn/transport/Protocol-v1/authorization/executor/result-delivery/reload/recovery failure or change, every agent/LLM/chat/handoff MUST first read `docs/planning/COMMUNICATION_PROTOCOL.md`, `docs/engineering/FAILURE_META_ANALYSIS.md`, and relevant `docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md` entries. Reconstruct the trace against the normative state/transition model and identify the first proven divergence before repair.
Local symptom chasing across protocol boundaries is prohibited. No repair may silently redefine protocol semantics.
Every protocol-affecting success MUST update protocol authority, tests/invariants, and durable history in the same slice. Every materially informative failed attempt MUST record hypothesis, evidence, outcome, and learning.
Every non-trivial failure meta-analysis MUST cover architecture/ownership, state machine, temporal ordering/concurrency, identity/lifetime, authorization, observability, recovery/idempotency, reuse of established solutions, root-cause versus symptom, regression risk, tests, and authority/document drift.
A handoff is incomplete if current protocol state, unresolved first divergence, and relevant evidence are omitted.
