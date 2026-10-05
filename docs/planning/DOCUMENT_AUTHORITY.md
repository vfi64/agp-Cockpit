# Cockpit document authority

Status: active
Decision status: accepted
Review policy: on material change
Status-date: 2026-09-09

Highest product-scope authority:
`docs/planning/SCOPE_BOUNDARY.md`.

Subordinate durable authorities:
- `MASTER_PLAN.md`
- `ARCHITECTURE.md`
- `PROTOCOL.md`
- `TEST_PLAN.md`
- `DEVELOPMENT_GATES.md`
- `LOCAL_EXECUTION_POLICY.md`
- `ULTRA_REVIEW_REMEDIATION.md`

Architecture decisions live under `docs/architecture/`. ADR-0003 is the
accepted v2 course correction.

Kit operating/control-plane files under `.agentic/` do not override product
semantic planning. Generated handoff files are projections. Validation reports
are evidence, not product direction.

Current phase:
Independent Ultra review remediation is ACTIVE.
The earlier v2 `FUNCTIONALLY_ACCEPTED` declaration is withdrawn.
`ULTRA_REVIEW_REMEDIATION.md` tracks F01-F10 and K01-K07 through renewed
acceptance. Historical phase completion records remain evidence, not current
whole-product acceptance.

<!-- AGP_COMMUNICATION_PROTOCOL_AUTHORITY_V1 -->
## Communication protocol authority
Cross-component Cockpit communication/lifecycle semantics are governed by `docs/planning/COMMUNICATION_PROTOCOL.md` together with `docs/planning/PROTOCOL.md`. Protocol-affecting changes require synchronized authority, tests/invariants, and durable change/failure history; failure analysis follows `docs/engineering/FAILURE_META_ANALYSIS.md`.
