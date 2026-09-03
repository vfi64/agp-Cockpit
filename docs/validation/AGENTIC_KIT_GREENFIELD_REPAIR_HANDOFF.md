# Agentic Project Kit — Greenfield Repair Handoff

Status: active
Decision status: accepted
Review policy: on material change

## Authority

`docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.md` is the canonical defect ledger.
`docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json` is its machine-readable projection.

Historical reports remain primary evidence and must not be rewritten to match the
canonical numbering. Their IDs are aliases in the ledger.

## Recommended repair order

### P0 — lifecycle convergence / first normal development cycle

- `KIT-GF-010`
- `KIT-GF-011`
- `KIT-GF-005`
- `KIT-GF-009`

### P1 — workspace-mode/profile correctness and closeout consistency

- `KIT-GF-008`
- `KIT-GF-004`
- `KIT-GF-002`
- `KIT-GF-003`
- `KIT-GF-012`

### P2 — bootstrap UX, empty-state/provenance quality, systemic agent governance

- `KIT-GF-001`
- `KIT-GF-006`
- `KIT-GF-007`
- `KIT-GF-013`

## Required repair discipline in the Kit repository

- Reproduce each family against the then-current Kit implementation before mutation.
- Preserve aliases and historical evidence; do not silently renumber old source reports.
- Prefer root-cause fixes over Greenfield-specific command exceptions.
- Add disposable-clone integration tests for external-manifest workspace lifecycle.
- Do not classify Cockpit/harness/authentication defects as Kit defects.
- Close a `KIT-GF-*` family only with explicit regression evidence.

## Final acceptance scenario

The external-workspace matrix must ultimately prove the complete path from fresh
workspace adoption through first work start, first closeout/push/PR/CI/merge, and
trustworthy successor-chat handoff without raw manual git/gh repair paths.
