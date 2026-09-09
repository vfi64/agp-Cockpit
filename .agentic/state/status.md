# Workspace Status

## Current continuation — Phase 14 / S4 durable task control and runtime isolation

- Repository: `vfi64/agp-Cockpit`.
- Phase 11 / S0 desktop basis: COMPLETE / CERTIFIED.
- Active phase: Phase 14 / S4 — durable task control, runtime isolation, browser readiness, and first self-hosting readiness.
- Maintainer-approved direction: deterministic persistent task runtime driven by
  a Remote Development LLM; Agentic Project Kit remains repository-lifecycle
  authority; no local development LLM required.
- ADR: `docs/architecture/ADR-0003-persistent-remote-llm-task-runtime.md`.
- Normative product authority: `docs/planning/SCOPE_BOUNDARY.md`.
- Phase 12 / S1, Phase 13 / S2, and Phase 14 / S3 are integrated and certified.
- Historical Phase7/8/9 acceptance remains valid as legacy transport evidence.
- Generated handoff projections are not primary semantic authority.

## Phase 13 / S2 — Minimal Remote Recovery Proof

- Status: implementation proof in progress.
- Scope: deterministic controller only; no local LLM, live repository mutation, or automatic crash resume.

## Phase 14 / S3 — Durable Task Runtime

- Status: implementation in progress.
- SQLite-backed task/action/attempt/message/evidence persistence.
- Stable payload hashes, durable duplicate protection, persisted budgets, OUTCOME_UNKNOWN and reconciliation.
\n## Phase 14 / S4 — Durable control and runtime isolation\n\n- Status: ACTIVE.\n- Production bridge runtime authority is Application Support, not repository `.local`.\n- pytest/temp runtime roots are test-only and explicitly injected.\n- Production transient-root startup is fail-closed; authentication remains mandatory.\n