# AGENTS.md

These rules apply repository-wide to every LLM, coding agent, maintainer assistant, and automation working on AGP Cockpit.

## 0. Normative product boundary — read first

`docs/planning/SCOPE_BOUNDARY.md` is the normative anti-scope-drift contract for this repository.

AGP Cockpit is ONLY a deterministic local communication bridge between a browser-based development LLM and a local terminal/executor.

AGP Cockpit does not perform development work. It does not plan, diagnose, choose repository workflow steps, choose Agentic Project Kit commands, implement Git/GitHub lifecycle logic, or replicate Kit FILE_TRANSFER behavior.

The role split is non-negotiable unless the maintainer explicitly changes the normative boundary:

```text
Browser LLM = reasoning, planning, development, diagnosis, next work order
AGP Cockpit = mechanical local transport only
Agentic Project Kit = workflow, validation, mutation, Git/GitHub, FILE_TRANSFER, evidence, gates, handoff, PR/merge/release lifecycle
```

If any older plan, chat, issue, proposed architecture, or agent suggestion conflicts with `docs/planning/SCOPE_BOUNDARY.md`, follow the scope-boundary document and correct the stale source before implementing the conflicting design.

## 1. Authority and source of truth

- Do not work from chat memory when current repository or Kit evidence is available.
- The current repository state and the currently installed/current Agentic Project Kit contract are authoritative.
- Do not reconstruct Kit commands, schemas, transfer files, workflow steps, or lifecycle behavior from memory if the current Kit exposes a canonical surface.
- If repository evidence contradicts a prompt or prior chat summary, repository evidence wins and the discrepancy must be documented.

## 2. Local maintainer work must be scripted

- Local work instructions for the maintainer MUST be provided as executable Python scripts whenever a script can reasonably express the operation.
- Do not give the maintainer loose multi-command terminal recipes as the primary workflow.
- A local-operation script must perform explicit preflight checks, use bounded side effects, print useful diagnostics, and return meaningful exit codes.
- Shell commands may be invoked internally by Python when necessary, but the user-facing execution unit is the Python script.
- Scripts must fail closed on ambiguous repository identity, branch/HEAD state, missing dependencies, unexpected Kit state, or unsafe preconditions.
- The maintainer's local script history lives in `<repo-root>/Download/` (currently `/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit/Download/` on the primary Mac).
- `/Download/` is local-only history and MUST remain ignored by Git. It must never be committed or pushed.
- Local scripts should use stable sequential names such as `001_phase0_bootstrap.py`, `002_ci_baseline.py`, etc., and should normally preserve prior scripts rather than overwrite them.
- A bootstrap script initially downloaded elsewhere may create `<repo-root>/Download/` and copy its own exact source into that directory after the repository checkout exists. Subsequent execution should use the archived copy.
- The absolute maintainer path above is an operations convention only and MUST NOT leak into portable product/application logic.

Detailed policy: `docs/planning/LOCAL_EXECUTION_POLICY.md`.

## 3. Prefer complex/high-level Agentic Project Kit commands during development of this repo

- As soon as the current Kit provides an orchestrator or higher-level workflow command for repository-development work, use it instead of reproducing the workflow with lower-level Kit primitives, `git`, `gh`, shell, or custom Python logic.
- Selection order is conceptually:

```text
current Kit orchestrator
    > current Kit workflow wrapper
    > current Kit primitive
    > custom git/gh/shell implementation
```

- Use a lower-level surface only when the higher-level one is unavailable or semantically inappropriate.
- When such a fallback affects safety, evidence, or lifecycle semantics, document the reason.
- Never bypass a Kit `BLOCKED` or `FAIL` by replacing the blocked Kit action with direct Git/GitHub commands.

This rule governs how contributing LLMs develop AGP Cockpit. It does NOT authorize the AGP Cockpit product itself to select Kit commands. At runtime, the browser LLM formulates the work order; the Cockpit only transports it.

## 4. Product implementation rules

- AGP Cockpit is a Python desktop application.
- The GUI uses `tkinter` for the initial product line.
- Tkinter is presentation only. The GUI must not own browser automation, Git logic, Kit command construction, subprocess orchestration, persistence implementation, or OS-specific process logic.
- Architecture follows pragmatic clean/hexagonal boundaries: core/application logic depends on ports; concrete integrations live in adapters.
- macOS is the first supported runtime platform.
- macOS-specific behavior must remain behind platform adapters so that Windows/Linux support can later be added without rewriting the core/application layers.
- Do not hard-code maintainer-specific paths such as `/Users/...`, Homebrew locations, Chrome paths, or repository paths into portable product logic.
- Runtime application logic may validate transport envelopes, duplicate IDs, browser/conversation identity, and local process state, but must not perform development reasoning.
- There must be no autonomous Kit command-selection layer in the product.
- There must be no Cockpit-owned GitHub/FILE_TRANSFER workflow layer in the product.

Architecture decisions: `docs/architecture/ADR-0001-macos-first-portable-core.md` and `docs/architecture/ADR-0002-python-tkinter-and-scripted-local-ops.md`.

## 5. Hermes/local LLM role

- Hermes/Qwen is not a development decision-maker for AGP Cockpit.
- A local LLM must not reinterpret, improve, summarize, repair, or replace work orders produced by the browser-based development LLM.
- Hermes may serve only as a mechanical browser/execution transport adapter if evidence shows that it is useful.
- The architecture must preserve the option to replace Hermes with a deterministic direct adapter.
- The browser-based LLM performs reasoning, planning, coding decisions, and diagnosis; the Kit remains the authoritative workflow/safety layer.

## 6. CI, tests, and gates are mandatory

- Every development slice, refactor, feature, bug fix, protocol change, or architecture change must be covered by appropriate automated tests and gates.
- A slice is not complete merely because it works locally.
- Completion requires the applicable local tests, remote CI checks, and Agentic Project Kit gates to be green for the exact commit under review.
- Do not merge, declare DONE, or advance the plan while required checks are red, missing, stale, or running against a different commit.
- Do not weaken or bypass a failing gate to make a slice appear complete.
- Add or update tests before or together with behavioral changes.
- Platform-neutral core/application code must remain testable without Chrome, macOS, Ollama, Hermes, GitHub, or a live ChatGPT session.
- Add scope-boundary tests/fitness checks that prevent introduction of Kit workflow selection or GitHub FILE_TRANSFER logic into the Cockpit.

Detailed gate policy: `docs/planning/DEVELOPMENT_GATES.md` and `docs/planning/TEST_PLAN.md`.

## 7. Browser and protocol safety

- Browser automation must bind to an explicit intended conversation/session and fail closed on ambiguity.
- Do not interpret arbitrary unstructured assistant prose as executable work.
- Execute only validated protocol envelopes defined by the repository protocol.
- Duplicate action IDs must never execute twice.
- Fixed sleeps may be used only as bounded implementation detail for browser/process rechecks; they are never semantic evidence of Kit workflow progress.

Protocol authority: `docs/planning/PROTOCOL.md`.

## 8. Kit authority boundary

AGP Cockpit transports work to the local terminal and transports terminal/Kit output back. It does not replace or partially implement Agentic Project Kit policy or lifecycle logic.

The Kit remains authoritative for, when applicable:

- workflow validation;
- approved mutations;
- Git/PR/merge/release lifecycle;
- transfer generation and validation;
- FILE_TRANSFER GitHub/remote communication and synchronization;
- handoff generation;
- evidence and gates;
- PASS/BLOCKED/FAIL semantics.

Never handcraft transfer YAML or internal Kit state when a current generator/validator exists.
Never add Cockpit code that publishes, polls, fetches, correlates, or advances Kit FILE_TRANSFER state through GitHub.

## 9. Planning and architectural changes

- `docs/planning/SCOPE_BOUNDARY.md` is the normative product-scope contract.
- `docs/planning/MASTER_PLAN.md` is the product-level development plan, subordinate to the scope boundary, current repository evidence, and the bootstrapped Kit governance layer.
- Changes to the scope boundary, trust boundaries, protocol semantics, exactly-once guarantees, browser identity rules, adapter architecture, supported-platform boundaries, or GUI framework require explicit maintainer approval, an ADR, and corresponding tests/gates.
- Keep planning documents synchronized with implemented behavior; stale documentation is a gate failure, not harmless drift.

## 10. Definition of acceptable agent behavior

An assisting LLM/agent should be able to answer, from current repository/Kit evidence rather than chat memory:

1. Is the proposed feature strictly necessary for browser-to-terminal or terminal-to-browser transport, or safe operation of that transport?
2. What exact state is the repository in?
3. Which current Kit orchestrator is appropriate for developing this repository?
4. Which tests and gates apply to the change?
5. What is the smallest safe next slice?
6. What evidence proves that slice is complete?

If the answer to question 1 is no, the feature is out of scope. If the remaining questions cannot be answered reliably, stop mutation and perform bounded diagnosis instead of guessing.
