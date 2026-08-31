# AGP Cockpit Test Plan

## 1. Test strategy

Testing follows the architectural boundaries. Most behavior must be testable without Chrome, Hermes, Ollama, GitHub, or a real Agentic Project Kit workspace.

Test layers:

1. core unit tests;
2. application/use-case tests with fake ports;
3. adapter contract tests;
4. macOS integration tests;
5. local browser integration tests;
6. Kit integration tests;
7. bounded end-to-end tests.

## 2. Core tests

Mandatory coverage:

- protocol framing and strict parsing;
- protocol schema validation;
- supported/unsupported versions;
- session/round/action ID handling;
- duplicate action detection;
- repository precondition comparison;
- state-machine valid transitions;
- rejection of invalid transitions;
- terminal-state behavior;
- timeout event handling;
- repeated BLOCKED handling;
- pause/stop behavior;
- recovery from persisted snapshots;
- ambiguous recovery becoming BLOCKED rather than replay.

Core tests must run on any Python-supported CI host without platform tools.

## 3. Property/fuzz-style protocol tests

Where practical, generate malformed variants:

- missing delimiters;
- swapped delimiters;
- duplicated blocks;
- nested blocks;
- invalid UTF-8 boundaries at adapter edges;
- oversized payloads;
- unknown fields if strict mode applies;
- changed payload under reused action ID;
- partial streamed response fragments.

The invariant is fail closed, never partial execution.

## 4. Application tests with fakes

Use fake implementations of all ports.

Scenarios:

- happy-path single round;
- PASS returned and submitted;
- BLOCKED returned and no fallback execution occurs;
- FAIL returned and loop stops;
- DONE terminates session;
- browser message never completes;
- user presses STOP during wait;
- user presses STOP during executable safe boundary;
- duplicate assistant response is observed twice;
- result submission succeeds but process crashes before local state update;
- action persisted then crash before execution;
- action execution result persisted then crash before browser submission.

## 5. Architecture fitness tests

Automated import/dependency checks should prove:

- core does not import adapters/presentation/platform libraries;
- application does not import concrete adapters;
- macOS-specific modules are not imported by portable core/application;
- browser selectors do not leak outside browser adapter/config;
- subprocess calls do not occur in GUI/core modules;
- Kit command strings are centralized in the Kit adapter/capability layer.

## 6. Browser adapter contract tests

A local fake chat web application should emulate the minimum relevant ChatGPT interaction model:

- conversation identity;
- assistant message list;
- streaming response state;
- composer;
- send action;
- delayed response completion;
- DOM changes;
- duplicate message rendering.

The Chrome adapter must pass the same behavioral contract as the fake browser adapter.

No CI test should require login to a real ChatGPT account.

## 7. macOS platform integration tests

Test in a temporary environment where possible:

- executable discovery with PATH variations;
- Homebrew location differences;
- listener ownership detection;
- safe Ollama process termination;
- refusal to kill an unrelated process owning the configured port;
- Chrome application discovery;
- application support/config/log path creation;
- operation outside Thonny/IDE environment;
- GUI startup from packaged/launcher context.

Tests that could kill real user processes must use spawned test fixtures, never broad process-name killing against the host session.

## 8. Ollama/Hermes regression tests

Characterize the imported legacy GUI behavior:

- model discovery;
- selected/default Hermes model mapping;
- Hermes config update behavior;
- port 11434 cleanup;
- Ollama startup/shutdown;
- foreign port-owner protection;
- missing Ollama/Hermes diagnostics;
- missing Tk runtime diagnostics where detectable.

These are compatibility tests, not reasons to keep legacy architecture.

## 9. Kit integration tests

Use disposable repositories.

Validate:

- Kit unavailable -> explicit BLOCKED/capability failure;
- non-governed repo -> correct preflight outcome;
- governed repo PASS path;
- `agentic-kit check`/`doctor` result transport;
- Kit BLOCKED is preserved as BLOCKED;
- no direct Git fallback is triggered;
- repository identity mismatch blocks before mutation;
- current Kit command/capability discovery behaves as specified by adapter contract.

For FILE_TRANSFER later:

- canonical order generation only;
- validation failure blocks;
- remote-order visibility delayed;
- result delayed;
- mismatched result correlation ID rejected;
- duplicate result handled idempotently;
- timeout does not cause blind replay.

## 10. End-to-end maturity ladder

### E2E-0

Desktop app starts on macOS independently of IDE/Automator environment assumptions.

### E2E-1

Cockpit connects to dedicated Chrome and reads one completed fake-chat response.

### E2E-2

Cockpit inserts a result into the composer without sending.

### E2E-3

One real ChatGPT test conversation completes a no-op/test round with explicit user confirmation.

### E2E-4

One automatic real-browser round completes and stops.

### E2E-5

Multiple read-only Kit rounds complete to explicit DONE.

### E2E-6

Crash is injected between execution and browser submission; recovery does not re-execute the action.

### E2E-7

Bounded mutating Kit workflow demonstrates correct PASS/BLOCKED/FAIL handling.

### E2E-8

FILE_TRANSFER round proves evidence-based asynchronous waiting.

## 11. CI strategy

Initial CI should include at minimum:

- supported Python version matrix as appropriate;
- unit/application tests;
- architecture fitness tests;
- lint/format/type checks chosen by repository policy;
- package/import smoke test;
- fake browser integration.

A Linux CI lane should be introduced early even though the product is macOS-first. Its purpose is to prove that portable modules import and test cleanly without macOS assumptions. It does not claim Linux product support.

Real macOS/browser/ChatGPT tests remain local/manual or dedicated opt-in CI because they depend on GUI/session credentials.

## 12. Release gate principles

No milestone may claim automation reliability based solely on a successful happy-path demo.

A release gate must include failure tests for:

- incomplete browser response;
- duplicate action;
- browser tab/conversation mismatch;
- repository mismatch;
- Kit BLOCKED;
- local execution failure;
- delayed remote state;
- crash/restart at critical boundaries;
- user STOP.

The current Agentic Project Kit gates and repository governance remain additional release evidence once the workspace is bootstrapped.
