# Systemic Failure Escalation

Status: active
Decision status: accepted
Review policy: on material change
## Purpose

Prevent repeated local repairs in the same failure domain from accumulating
into an implicit architecture or state machine without explicit review.

## Trigger

A `SYSTEMIC_FAILURE_REVIEW` is mandatory before a third substantive product
repair in the same failure domain.

Examples of a failure domain include:

- browser transport / send acknowledgement,
- assistant response pickup,
- bridge/runtime lifecycle,
- persistence/state semantics,
- execution safety,
- test-model correctness.

## Required review

The review must contain all of the following.

### 1. Failure history

List the recent repair cycles, their symptoms, affected files/functions, and
whether the regression was observed in unit, integration, browser, or LIVE
evidence.

### 2. Failure-domain clustering

State whether the observed failures belong to one subsystem or represent
independent defects.

### 3. Architecture / state-transition map

Describe the components, authorities, state transitions, side effects, and
cross-boundary contracts involved.

### 4. Test-model audit

Classify relevant tests as behavior-oriented or implementation-/source-coupled.
Identify brittle exact-source assertions, duplicated tests, contradictory
expectations, and fixture/live mismatches.

### 5. Patch-history audit

Identify layered repair markers, accumulated heuristics, retries, compatibility
paths, and obsolete or redundant patches.

### 6. Root-cause hypothesis

Classify the likely root cause as one or more of:

- local implementation defect,
- missing abstraction,
- implicit state machine,
- incorrect boundary,
- test architecture defect,
- environment/external interface drift.

### 7. Decision

Choose exactly one:

- `PATCH_LOCAL`
- `REFACTOR_SUBSYSTEM`
- `REDESIGN_BOUNDARY`
- `TEST_MODEL_REPAIR`
- `NEEDS_HUMAN`

The decision must state why another local patch is or is not justified.

## Escalation levels

### R1 — Repeat

Second failure/repair in the same failure domain.

Action: preserve failure history and warn that the next recurrence requires
systemic review.

### R2 — Recurrence

Third substantive repair candidate in the same failure domain.

Action: block product mutation until `SYSTEMIC_FAILURE_REVIEW` is complete.

### R3 — Patch spiral

Further recurrence after systemic review, or strong evidence of layered
heuristics / test-model contradiction.

Action: prefer subsystem refactoring, boundary redesign, or test-model repair
over another local patch.

## Test regression classification

A test that fails after a valid refactor is not automatically evidence of a
product regression.

Before changing product code, classify the test failure:

- `BEHAVIOR_REGRESSION`
- `IMPLEMENTATION_COUPLED_TEST_REGRESSION`
- `FIXTURE_MODEL_REGRESSION`
- `UNCLASSIFIED`

Implementation-coupled assertions such as exact source-string matching must not
override a valid behavioral contract merely to restore a green suite.

## Current motivating evidence

The Browser Transport Stabilization inventory in
`docs/validation/BROWSER_TRANSPORT_STABILIZATION_086.md` found 18 relevant
tests, of which 15 were classified as source-coupled and only 3 as
behavior-oriented. The same transport domain had already accumulated multiple
historical repair markers and repeated LIVE regressions.

That evidence is sufficient to classify the browser transport work as at least
R2 and to require systemic consolidation before further symptom patches.
