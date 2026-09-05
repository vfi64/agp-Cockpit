# Cockpit document authority

Status: active

Decision status: Accepted

Review policy: Review when document authority, lifecycle ownership, or active development phase changes.

This file defines ownership and authority boundaries for durable project documentation.

## Product-owned canonical planning

The Cockpit owns its product intent and correctness. Canonical planning documents live in
`docs/planning/`. `MASTER_PLAN.md`, `PROTOCOL.md`, `TEST_PLAN.md`, and
`DEVELOPMENT_GATES.md` are durable product-owned sources. They must be changed deliberately
when product semantics, protocol, tests, or gates change.

The external workspace does **not** adopt `docs/planning/PROJECT_DIRECTION.yaml` as a required
Kit project-direction file. Active continuation is represented by the current repository state
plus `.agentic/state/status.md`; product decisions remain grounded in the project-owned planning
documents.

## Kit-owned operating/control-plane state

`.agentic/config.yaml`, `.agentic/state/status.md`, and the `.agentic/registries/` files are the
Kit-facing operating layer. `status.md` is the concise continuation state and must describe the
current development phase rather than retain an obsolete historical phase as active.

## Generated handoff projections

Files under `.agentic/state/handoff/packages/latest/` and the generated chat-switch prompt files
are projections produced by the Kit handoff mechanism. They are not primary semantic authority
and must not be manually edited to introduce product rules or product direction. Change the
durable source first and regenerate through the supported Kit lifecycle.

## Validation and findings

`docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.md` and its JSON companion are the canonical
Cockpit-side ledger for Kit findings discovered by this external workspace. Validation reports
are evidence; they do not supersede product planning.

## Current phase boundary

Phases 0, 1, 2, 3, and 4 are complete. Phase 4 closed the macOS platform-adapter boundary with
process/listener/browser acceptance tests and a local E2E-0 Tk startup gate outside repository/IDE
environment assumptions. Phase 5 is active: one configured Chrome conversation must complete the
browser-bridge proof of concept without introducing Kit workflow intelligence.
