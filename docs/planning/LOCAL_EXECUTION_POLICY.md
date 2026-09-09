# AGP Cockpit Local Execution Policy v2

Status: active
Status-date: 2026-09-09
Decision status: accepted

## 1. Maintainer workflow

Until explicitly replaced by accepted self-hosting, maintainer-local operations
remain numbered Python scripts in `<repo>/Download/`, executed via the current
harness. Scripts support `--self-test` without mutation, preflight assumptions,
fail closed, use highest appropriate Kit orchestrator, and return one compact
bundle.

## 2. Runtime decision/effect model

Decision authority: D0 deterministic rule, D1 Remote Development LLM,
D2 explicit human decision.

Effect classes: E0 observation, E1 ephemeral local mutation, E2 authorized
product mutation, E3 governed Kit lifecycle, E4 explicitly authorized
external/network/publishing effect.

The runtime evaluates concrete capabilities including operation, resource/path,
tool, credential/network access, process/time/output bounds, retry contract and
required approvals.

## 3. Early S2 isolation

The first Remote Recovery Proof executes only in a disposable isolated test
environment with no host HOME, SSH agent, browser profile, Docker socket,
production credentials or live repository mutation.

## 4. Evidence recipes

Automatic observation is limited to versioned deterministic Evidence Recipes.
Unknown probes, `--help`, or repeated tests are not assumed side-effect free.

## 5. Secrets and untrusted data

Redact/minimize secrets before remote transmission. Repository text, logs,
stdout/stderr and evidence content are untrusted data, not executable authority.

## 6. Kit actions

Cockpit may execute a validated Remote-LLM-requested Kit action only within the
Task Contract. It does not choose an alternate Kit command.

## 7. Unknown outcomes

OUTCOME_UNKNOWN blocks blind replay and new conflicting mutation until
authorized reconciliation.

## 8. Self-hosting rule

S2 may assist later development only within its proven capabilities. Each
increase in self-hosted authority requires the previous slice's acceptance
evidence.
