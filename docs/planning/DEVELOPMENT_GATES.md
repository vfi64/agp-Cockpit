# AGP Cockpit Development Gates

Status: normative planning baseline

## 1. Governing rule

No implementation slice, refactor, feature phase, bug fix, dependency change, protocol change, platform change, or documentation-governance change is considered complete until its required local validation and remote CI/gates are green.

A locally working application is not sufficient evidence of completion.

A slice may be described as `IN_PROGRESS` while CI is pending. It may only be marked `PASS`/complete when all required gates for that slice have passed on the exact commit intended for integration.

## 2. Required development sequence

Every development slice follows this sequence:

```text
PLAN
  -> IMPLEMENT
  -> TARGETED LOCAL TESTS
  -> FULL REQUIRED LOCAL GATES
  -> COMMIT/PUSH THROUGH KIT-GOVERNED WORKFLOW
  -> REMOTE CI
  -> KIT/REPOSITORY GATES
  -> EVIDENCE REVIEW
  -> SLICE PASS OR BLOCKED/FAIL
```

If any stage fails, the slice remains incomplete.

## 3. Exact-commit evidence

Remote CI evidence must correspond to the exact commit/HEAD being accepted. Results from an earlier commit are not transferable to a later commit unless the current Kit explicitly provides and validates such an evidence reuse mechanism.

Required recorded evidence should include, where available:

- commit SHA;
- branch;
- CI workflow/run identifier;
- required job/check names;
- pass/fail conclusion;
- relevant Kit gate result;
- bounded log/evidence reference.

## 4. Baseline CI lanes

The repository should establish CI as early as possible. The initial baseline should contain at least:

### Portable-core lane

Runs on Linux and proves that portable code does not accidentally depend on macOS:

- unit tests;
- application/use-case tests with fake ports;
- protocol tests;
- state-machine tests;
- architecture fitness tests;
- lint/format checks;
- static typing once adopted;
- packaging/import smoke test.

This lane does not claim Linux product support.

### macOS lane

Runs on a GitHub-hosted macOS runner for platform-independent and safe platform integration checks:

- portable test suite;
- macOS adapter tests that do not depend on a logged-in desktop session;
- executable/path discovery fixtures;
- process/listener test fixtures;
- packaging/import smoke tests;
- GUI module import/startup tests where runner limitations permit.

Real interactive Chrome/ChatGPT tests remain local opt-in tests unless a secure dedicated automation environment is later introduced.

## 5. Required gate classes per slice

Every slice must classify itself and run all applicable gates.

### A — Core/protocol/FSM changes

Required:

- targeted unit tests;
- full core/application suite;
- property/fuzz-style malformed protocol tests where applicable;
- architecture fitness tests;
- Linux CI;
- macOS CI;
- current Kit planning/code slice gate as applicable.

### B — Browser adapter changes

Required:

- fake-browser contract tests;
- browser adapter unit tests;
- local Chrome integration test for behavior that cannot be proven in CI;
- Linux portable tests;
- macOS CI;
- explicit evidence that no unrelated tab/conversation can be targeted in tested scenarios.

### C — macOS platform/process changes

Required:

- unit tests with process/listener fixtures;
- foreign-process protection test;
- macOS CI;
- local macOS integration test when runner environment cannot reproduce the behavior;
- regression test for independent app startup outside IDE assumptions.

### D — Kit integration changes

Required:

- fake Kit adapter tests;
- disposable governed-repository integration test;
- preservation of PASS/BLOCKED/FAIL semantics;
- proof that no direct Git/GitHub fallback bypass is introduced;
- current `agentic-kit check`;
- current `agentic-kit doctor`;
- applicable current Kit slice/transfer gates.

### E — FILE_TRANSFER changes

Required in addition to D:

- canonical generator/validator integration tests;
- correlation-ID tests;
- delayed remote visibility test;
- delayed result test;
- wrong-result-ID rejection test;
- duplicate result test;
- timeout-without-blind-retry test;
- crash/recovery test at transfer boundaries.

### F — GUI changes

Required:

- view-model/application tests;
- GUI construction/import smoke test;
- no blocking work on GUI thread test where practical;
- local macOS launch test;
- regression check of STOP/PAUSE controls when affected.

### G — persistence/recovery changes

Required:

- atomic-write tests;
- corrupt-state tests;
- schema migration tests;
- crash injection at every critical dispatch/submission boundary affected;
- no automatic replay from ambiguous state.

### H — documentation/planning/architecture changes

Required:

- documentation links/structure checks;
- architecture consistency checks where implemented;
- current Kit planning-document slice gate when available;
- current `check-docs`/docs audit/doctor gates as applicable.

## 6. Phase gates

Each phase in `MASTER_PLAN.md` has two levels of exit criteria:

1. **functional exit criterion** — the behavior described by that phase exists;
2. **acceptance gate** — all required tests and remote CI for the exact phase-closing commit are green.

A phase cannot close on functional evidence alone.

## 7. Pull request policy

Once the repository is bootstrapped and CI exists, normal development should use working branches and pull requests rather than direct product development on `main`.

Before merge:

- required CI checks are green;
- required Kit gates are PASS;
- worktree/repository state satisfies the Kit merge preflight;
- documentation/evidence is current for the change class;
- unresolved BLOCKED/FAIL evidence is not hidden by a later unrelated success.

Branch protection/rulesets should require the stable CI checks once their names are established.

## 8. Failure semantics

A failed CI/gate is not permission to weaken, skip, or manually bypass the gate.

Response to failure:

```text
FAIL/BLOCKED
  -> preserve bounded evidence
  -> diagnose
  -> make one targeted correction
  -> rerun targeted validation
  -> rerun all required acceptance gates
```

Repeated identical failures trigger bounded diagnosis rather than an unbounded repair loop.

## 9. Local-only tests

Some tests cannot safely run in shared CI, especially:

- real logged-in ChatGPT browser interaction;
- interactive desktop GUI behavior;
- real local Ollama/Hermes lifecycle;
- tests involving user browser profiles or credentials.

These may remain explicit local acceptance gates, but they do not replace remote CI. A slice that changes such behavior requires both:

- the strongest reproducible automated CI tests using fakes/fixtures;
- the designated local integration gate.

The local result must be captured as bounded evidence under the Kit-governed evidence conventions.

## 10. CI-before-complexity rule

The CI skeleton is an early deliverable, not release polish.

Before browser automation, multi-round execution, FILE_TRANSFER, or crash recovery is developed, the repository must already have a functioning baseline CI pipeline capable of rejecting regressions in portable core behavior and architecture boundaries.

## 11. No gate-free bootstrap exception

Repository bootstrap itself must also be validated. Phase 0 is complete only when the current Agentic Project Kit workspace initialization has been executed through the supported path and the resulting repository passes the applicable Kit checks/gates.

After the first CI workflow is introduced, subsequent bootstrap/structure changes are subject to remote CI like all other changes.

## 12. Definition of accepted change

An accepted change is therefore:

```text
correct behavior
+ targeted tests
+ regression tests
+ architecture checks
+ applicable platform/integration tests
+ remote CI PASS on exact commit
+ applicable Agentic Project Kit gates PASS
+ bounded evidence
```

Anything less remains provisional.
