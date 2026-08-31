# External Workspace Adoption Adjudication

Status: active
Status-date: 2026-08-31
Decision status: accepted
Review policy: on material change

Recorded: 2026-08-31T16:23:20.552676+00:00

## Decision

During initial Agentic Project Kit workspace bootstrap, all pre-existing
planning, architecture, instruction, and handoff surfaces listed below are
preserved as maintainer-authored source authority.

No listed surface may be automatically reclassified as generated, replaced
by a Kit projection, migrated into Kit-owned state, or deleted during this
bootstrap unless a later explicit maintainer decision changes that status.

This adjudication does not claim external-repository DPA conformance. It only
resolves the current intake question of how existing authored surfaces are
to be treated while the Kit operating layer is introduced.

## Preserved maintainer-authority surfaces

- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `docs/architecture/ADR-0001-macos-first-portable-core.md`
- `docs/architecture/ADR-0002-python-tkinter-and-scripted-local-ops.md`
- `docs/handoff/CLAUDE_START_PROMPT.md`
- `docs/planning/ARCHITECTURE.md`
- `docs/planning/DEVELOPMENT_GATES.md`
- `docs/planning/LOCAL_EXECUTION_POLICY.md`
- `docs/planning/MASTER_PLAN.md`
- `docs/planning/PROTOCOL.md`
- `docs/planning/TEST_PLAN.md`

## Product scope boundary

`docs/planning/SCOPE_BOUNDARY.md` is normative for AGP Cockpit product scope:
the application is only the local communication bridge between a browser LLM
and the local terminal/executor. Development work, Git/GitHub workflow,
FILE_TRANSFER, gates, evidence, handoff, PR/merge/release, and remote
synchronization remain Agentic Project Kit responsibilities.
