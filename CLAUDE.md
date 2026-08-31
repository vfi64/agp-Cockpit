# CLAUDE.md

This file provides Claude-specific bootstrap guidance for AGP Cockpit. It does not replace repository-wide rules.

## Mandatory first read

Before planning, editing, or executing anything, read in this order:

1. `AGENTS.md`
2. `docs/planning/SCOPE_BOUNDARY.md`
3. `docs/planning/MASTER_PLAN.md`
4. `docs/planning/ARCHITECTURE.md`
5. `docs/planning/PROTOCOL.md`
6. `docs/planning/DEVELOPMENT_GATES.md`
7. `docs/planning/TEST_PLAN.md`
8. `docs/planning/LOCAL_EXECUTION_POLICY.md`
9. all applicable files under `docs/architecture/`
10. after Kit workspace bootstrap, the current `.agentic/` state, rules, handoff, manifests, and current Kit-generated evidence

Do not use prior-chat memory as authority when repository or current Agentic Project Kit evidence exists.

## Absolute product boundary

AGP Cockpit is ONLY a deterministic local communication bridge between a browser-based development LLM and a local terminal/executor.

It does not perform development work.

The role split is:

- Browser LLM: reasoning, planning, development, diagnosis, selection/formulation of the next local work order.
- AGP Cockpit: mechanical browser-to-terminal and terminal-to-browser transport only, plus transport safety/observability.
- Hermes/Qwen: optional mechanical adapter only; never a development decision-maker.
- Agentic Project Kit: authoritative workflow, validation, mutation, Git/GitHub lifecycle, FILE_TRANSFER, evidence, gates, handoff, PR/merge/release lifecycle.

Claude MUST NOT propose or implement Cockpit features that choose Kit commands, plan development work, diagnose software semantically, resolve Kit `BLOCKED`/`FAIL`, implement GitHub workflow progression, or duplicate FILE_TRANSFER semantics.

In FILE_TRANSFER mode the Cockpit does not publish, poll, fetch, correlate, synchronize, or advance remote/GitHub transfer state. The current Agentic Project Kit owns all of that. From the Cockpit's point of view, FILE_TRANSFER is just a local terminal work order that may take time because the Kit is doing its own work.

If any older planning text, prior chat, issue, or suggestion conflicts with `docs/planning/SCOPE_BOUNDARY.md`, the scope boundary wins and the stale source must be corrected before implementation.

## Implementation constraints

- Product language: Python.
- GUI: `tkinter` for the initial product line.
- Initial runtime: macOS.
- Architecture: pragmatic clean/hexagonal architecture with portable core/application layers and explicit ports/adapters.
- macOS-specific logic must remain in platform adapters.
- No maintainer-specific absolute paths in portable product code.
- Browser integration, process control, persistence, and OS calls must not live in Tkinter widgets.
- Do not introduce an autonomous Kit command-selection service.
- Do not introduce a Cockpit-owned GitHub/FILE_TRANSFER workflow service.

## Local maintainer instructions

Whenever the maintainer must perform local work, provide that work as an executable Python script whenever reasonably possible.

A local-work script must:

- perform explicit preflight checks;
- verify repository identity and important Git state;
- fail closed on ambiguity;
- use bounded side effects;
- print diagnostics and meaningful exit status;
- invoke shell commands internally only as implementation detail.

Do not make loose multi-command shell recipes the primary maintainer workflow.

Local maintainer script history belongs in `<repo-root>/Download/`; on the primary Mac this currently resolves to `/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit/Download/`. This directory is local-only, Git-ignored, and must never be committed or pushed. Preserve scripts with sequential names where practical. A first bootstrap script downloaded outside the repository may create this directory and copy its own exact source into it once the checkout exists. This absolute path is an operations convention, never a portable product-code dependency.

## Agentic Project Kit command selection while developing this repository

Use the current Kit contract, not remembered syntax.

Prefer the highest semantically correct Kit surface available:

```text
current Kit orchestrator
  > current Kit workflow wrapper
  > current Kit primitive
  > custom git/gh/shell implementation
```

Do not bypass Kit `BLOCKED` or `FAIL` outcomes with direct Git/GitHub commands.
Do not handcraft transfer YAML or Kit-owned state when current generators/validators exist.

This hierarchy applies to Claude's development work on the AGP Cockpit repository. It does NOT mean the finished Cockpit product may select Kit commands at runtime.

## Mandatory tests and gates

Every implementation slice, refactor, bug fix, protocol change, or architecture change requires applicable automated tests and gates.

A slice is complete only when:

- applicable local tests are green;
- remote CI is green for the exact commit;
- applicable Agentic Project Kit gates are green for that exact commit;
- documentation and architecture evidence match the implementation;
- scope-boundary fitness checks remain green.

Never weaken a test/gate merely to obtain green status.

## Current project phase

The repository is at initial governance/bootstrap stage. Do not jump directly into browser automation or product feature implementation.

The next intended work remains Phase 0 from `docs/planning/MASTER_PLAN.md`: place the repository under the current Agentic Project Kit external-workspace governance path, then establish the initial CI/gate baseline before importing/refactoring the legacy Ollama/Hermes GUI.

Use the current Kit's high-level external-repository intake/adoption orchestration as soon as available. Re-discover and verify the current command surface before execution.

## Mutation discipline

Before changing files:

1. confirm the proposed change is within `SCOPE_BOUNDARY.md`;
2. inspect current branch, HEAD, worktree, remote, and repository identity;
3. inspect current Kit workspace state if present;
4. identify the smallest safe slice;
5. state the tests/gates that will prove completion;
6. only then mutate.

If evidence is missing or contradictory, stop mutation and perform bounded diagnosis.

## Handoff discipline

When stopping or handing work to another LLM, use the current canonical Agentic Project Kit handoff mechanism once the workspace is bootstrapped. The successor must reconstruct state from repository/Kit evidence rather than relying on prose chat summaries.
