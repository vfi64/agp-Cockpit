# Failure Meta-Analysis Policy
Mandatory for every non-trivial AGP Cockpit failure.
Each analysis must establish: visible symptom; complete relevant protocol trace; first proven divergence from `docs/planning/COMMUNICATION_PROTOCOL.md`; owning architecture layer; state/temporal/concurrency correctness; identity/lifetime correctness; Task Contract/authorization consistency; retry/reload/idempotency; observability sufficiency; root cause vs contributing/downstream symptom; existing project/library/framework mechanism to reuse; regression risks; required tests/invariants/docs; and real E2E acceptance evidence.
Do not patch the latest symptom first. Reconstruct the transition chain and repair the smallest coherent owning-layer cause.
Protocol-affecting successes and materially informative failures are recorded in `PROTOCOL_CHANGE_AND_FAILURE_LOG.md`.
