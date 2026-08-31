# AGP Cockpit Master Plan

Status: initial planning baseline

## 1. Mission

AGP Cockpit is a local desktop application that removes the mechanical copy/paste work between a browser-based LLM session and local repository work governed by the Agentic Project Kit (AGP Kit).

The cockpit is not an autonomous development agent. It must not decide what code to write, which Git operation to perform, how to recover from a Kit block, or which workflow step should follow. The remote/browser LLM remains the reasoning and development layer. The Agentic Project Kit remains the authoritative local workflow, policy, validation, mutation, evidence, handoff, PR, merge, and release layer.

The initial supported host is macOS. The architecture must nevertheless isolate operating-system integration so that Windows and Linux support can be added without rewriting the domain/application core.

## 2. Non-negotiable role separation

```text
User
  |
  v
Browser LLM (reasoning, planning, development, diagnosis)
  |
  v
AGP Cockpit (deterministic transport, synchronization, observation)
  |
  +--> Browser adapter
  +--> Local execution adapter / optional Hermes transport adapter
  +--> Agentic Project Kit interface
  |
  v
Agentic Project Kit (authority, validation, controlled mutation, evidence)
  |
  v
Local repository / Git / approved remote lifecycle
```

AGP Cockpit MUST NOT:

- invent Kit commands from memory when the current Kit exposes a canonical command surface;
- invent transfer YAML or internal Kit state files;
- bypass `BLOCKED` or `FAIL` with direct `git`, `gh`, shell, or GitHub mutations;
- let a local LLM reinterpret, improve, summarize, repair, or replace a remote LLM action;
- infer success solely from elapsed time;
- execute the same action twice after crash/restart unless idempotency evidence proves that repetition is safe;
- silently switch communication mode or repository.

## 3. Product goals

### G1 — One-click local session control

The application presents a desktop cockpit showing at minimum:

- selected local repository;
- browser/ChatGPT connection state;
- Kit availability and health state;
- execution transport state;
- communication mode;
- current round/correlation ID;
- current finite-state-machine state;
- last PASS/BLOCKED/FAIL result;
- STOP and PAUSE controls;
- bounded audit log location.

### G2 — Deterministic browser bridge

The browser adapter must be able to:

1. connect to a dedicated Chrome session/profile;
2. identify the intended ChatGPT conversation;
3. wait until an assistant response is complete;
4. extract exactly one protocol action envelope;
5. submit exactly one protocol result envelope back to that same conversation;
6. fail closed if the page shape or protocol is ambiguous.

The core must not depend directly on Chrome DOM selectors. Selectors and browser-specific behavior belong to an adapter.

### G3 — Two transport modes with one control protocol

The cockpit supports:

- `DIRECT_EXECUTION`: successor of manual copy/paste. A complete, explicitly bounded local action is transported and executed.
- `FILE_TRANSFER`: a structured intent/order path in which canonical Kit generators, validators, transfer mechanisms, and reports remain authoritative.

The LLM-facing envelope is common to both modes. Mode-specific details are delegated to separate executors/adapters.

### G4 — No local reasoning dependency

Hermes/Qwen may be retained as an execution/browser transport dependency only if technically useful. The architecture must permit replacing it with a deterministic direct adapter without changing domain behavior.

A mandatory architecture gate will compare:

- `HERMES_TRANSPORT_ADAPTER`
- `DIRECT_DETERMINISTIC_ADAPTER`

The preferred implementation is the one with lower ambiguity, fewer failure modes, less transformation of payloads, and better testability.

### G5 — Crash-safe resumability

Every action/result round has a unique correlation ID and persistent state. On restart the cockpit reconstructs what was requested, what was executed, whether a result was already submitted, and what external evidence exists before taking any further action.

### G6 — Platform-portable architecture

macOS is the first implementation, not the architecture boundary. OS-specific responsibilities must be behind platform ports, including:

- executable discovery;
- process/listener inspection;
- process termination;
- browser location/startup;
- application data/config/log locations;
- secure local secret storage when introduced;
- opening Finder/Explorer/file manager or Terminal UI when needed.

## 4. Architecture principles

The project follows a pragmatic Clean/Hexagonal Architecture:

```text
presentation/        desktop GUI only
application/         use cases + orchestration
core/                domain models, protocol, FSM, invariants
ports/               interfaces/protocols required by core/application
adapters/
  browser/
  execution/
  kit/
  persistence/
  platform/
infrastructure/      composition root, logging, config, telemetry hooks
```

Rules:

1. `core` imports no GUI, browser, subprocess, filesystem, OS, Hermes, GitHub, or Kit implementation modules.
2. `application` depends on `core` and `ports`, never concrete adapters.
3. adapters implement ports and may depend on external libraries/tools.
4. the composition root selects concrete adapters for macOS at runtime.
5. UI invokes application use cases; it never executes shell commands directly.
6. protocol parsing is deterministic and independently unit-testable.
7. mutable session state is represented explicitly, persisted atomically, and transitions only through validated events.

## 5. State machine

Initial control states:

```text
IDLE
  -> PREFLIGHT
  -> CONNECTING_BROWSER
  -> WAITING_FOR_LLM
  -> VALIDATING_ACTION
  -> READY_TO_EXECUTE
  -> EXECUTING
  -> COLLECTING_RESULT
  -> VALIDATING_RESULT
  -> SENDING_RESULT
  -> WAITING_FOR_LLM

Terminal/interrupt states:
  DONE
  BLOCKED
  FAIL
  PAUSED
  USER_STOPPED
```

For file transfer, additional explicit states are inserted rather than hidden behind sleeps:

```text
ORDER_GENERATING
ORDER_VALIDATING
ORDER_PUBLISHING
WAITING_FOR_REMOTE_ORDER_VISIBILITY
WAITING_FOR_REMOTE_RESULT
RESULT_FETCHING
```

No state transition may occur merely because a timer elapsed. Time may trigger a re-check or timeout event; evidence determines progress.

## 6. Protocol invariants

Each browser-to-local action contains at minimum:

- protocol version;
- session ID;
- round ID;
- action ID;
- communication mode;
- repository identity/path expectation;
- action payload;
- completion condition or expected result shape where applicable.

Each local-to-browser result contains at minimum:

- same session/round/action IDs;
- status (`PASS`, `BLOCKED`, `FAIL`);
- return code when applicable;
- bounded human/LLM-readable summary;
- references to logs/evidence rather than unbounded logs;
- enough repository identity evidence to detect accidental target switching.

Duplicate action IDs are never executed twice.

## 7. Security and trust boundaries

Trust order for workflow facts:

1. current local repository and Kit-produced machine-readable state/evidence;
2. current Kit command/manifest/schema surface;
3. browser action envelope from the remote LLM;
4. persisted cockpit transport state;
5. natural-language chat history.

The cockpit may transport a requested operation, but it does not grant authority. Kit gates and wrappers remain authoritative.

Browser automation uses a dedicated Chrome profile where practical. The cockpit must not scrape or manipulate unrelated tabs. It must bind a session to an explicit conversation identity and verify that identity before each send.

Secrets, cookies, browser profiles, access tokens, generated logs, and local machine paths that are not product fixtures must not be committed.

## 8. Development phases

### Phase 0 — Repository governance bootstrap

Goal: place the new repository under current Agentic Project Kit governance without manually recreating Kit internals.

Actions on the local Mac, using the currently installed/current Kit contract:

1. clone `vfi64/agp-Cockpit`;
2. create a Python virtual environment for product development;
3. install/upgrade the Kit separately as required by the current supported path;
4. run `agentic-kit workspace dpa-intake --root .`;
5. run `agentic-kit workspace adopt --root .`;
6. review/adjudicate the intake evidence;
7. run `agentic-kit workspace init --root . --execute` only after the dry-run/intake is accepted;
8. run `agentic-kit check --root .` and `agentic-kit doctor --root .`;
9. commit the generated governance layer through the Kit-governed workflow.

Exit criterion: current Kit reports a valid governed external workspace and no unreviewed adoption blocker remains.

### Phase 1 — Baseline import and characterization

Input: the currently working macOS Ollama/Hermes Tkinter program.

Work:

- import it as a legacy/reference fixture, not as the final architecture;
- characterize current behavior with tests where practical;
- identify responsibilities: Ollama lifecycle, port 11434 cleanup, model discovery, Hermes config, Hermes lifecycle, GUI, logging;
- freeze observable behavior needed for backward compatibility.

Exit criterion: existing start/stop/model/config behavior has regression coverage or explicit documented exceptions.

### Phase 2 — Architectural extraction

Refactor into ports/adapters without adding browser automation.

Create explicit ports such as:

- `ProcessService`
- `PortInspector`
- `ExecutableLocator`
- `BrowserSessionPort`
- `LocalExecutorPort`
- `KitPort`
- `SessionStore`
- `Clock`
- `AuditSink`

Introduce application use cases and a composition root.

Exit criterion: core/application tests run without macOS, Chrome, Ollama, Hermes, or a real repository.

### Phase 3 — macOS platform adapter

Implement modern macOS integration behind platform ports:

- Homebrew and PATH-aware executable discovery;
- safe process inspection/termination;
- TCP listener ownership inspection;
- application support/log/config directories using platform conventions;
- Chrome discovery/startup with dedicated profile option.

Exit criterion: no macOS-specific call is made outside the platform adapter layer.

### Phase 4 — Browser bridge proof of concept

Implement Chrome connection and a fake-chat test surface first.

Progressive gates:

1. connect to dedicated Chrome;
2. identify one configured conversation/tab;
3. read the latest completed assistant message;
4. insert text into composer without sending;
5. send a test message only under explicit user confirmation;
6. detect completion of the next assistant response.

Exit criterion: one browser round trip works without Kit execution.

### Phase 5 — Protocol v1

Implement deterministic action/result envelopes and strict parser/validator.

Requirements:

- versioned schema;
- explicit IDs;
- strict duplicate rejection;
- bounded payload sizes;
- fail-closed parsing;
- no local LLM interpretation.

Exit criterion: property/unit tests cover malformed, partial, duplicated, reordered, and oversized envelopes.

### Phase 6 — Single DIRECT_EXECUTION round

Flow:

```text
completed browser response
-> action envelope
-> validation
-> repository/Kit preflight
-> one local execution
-> bounded result envelope
-> insert into browser
-> explicit user send confirmation
-> stop
```

Exit criterion: exactly-once execution proven for one action ID.

### Phase 7 — Automatic single round

Remove the final manual send confirmation behind an explicit `Automation enabled` session control.

The cockpit sends one result, waits for one complete next response, validates it, and stops before executing the next action.

Exit criterion: browser synchronization is reliable without fixed sleeps.

### Phase 8 — Multi-round supervised loop

Enable repeated rounds with hard guards:

- maximum rounds;
- per-state timeout;
- total session timeout;
- duplicate action detection;
- repeated identical BLOCKED detection;
- pause/stop;
- persistent journal;
- explicit DONE terminal envelope.

Exit criterion: a multi-step read-only test workflow reaches DONE and can recover from an injected crash.

### Phase 9 — Kit-aware DIRECT_EXECUTION production path

Replace generic shell execution with a Kit-aware execution adapter wherever the current Kit provides canonical operations.

The cockpit must not duplicate Git/PR/release workflow logic.

Exit criterion: a bounded real repository workflow demonstrates PASS/BLOCKED/FAIL transport without bypasses.

### Phase 10 — FILE_TRANSFER mode

Integrate the current canonical Kit order generator, validator, transfer runner, and result/evidence path.

Requirements:

- no handcrafted transfer YAML;
- correlation IDs preserved end to end;
- remote visibility checked by evidence;
- result matched to the exact order;
- timeouts become BLOCKED/diagnostic events, not blind retries.

Exit criterion: one complete file-transfer round succeeds and one delayed-result test proves correct waiting behavior.

### Phase 11 — Architecture gate: Hermes or direct adapter

Measure both feasible paths against:

- payload fidelity;
- deterministic behavior;
- observability;
- dependency count;
- latency;
- restart behavior;
- cross-platform burden;
- browser robustness;
- testability.

Decision is recorded as an ADR. If Hermes adds no essential capability, remove it from the critical transport path while optionally retaining it as an auxiliary/manual tool.

### Phase 12 — Desktop product hardening

- polished Tkinter/customtkinter/PySide decision based on evidence, packaging, accessibility, and portability;
- structured logging;
- settings migration/versioning;
- first-run diagnostics;
- safe update strategy;
- application packaging for macOS;
- signed/notarized distribution only if later required;
- documented recovery procedures.

Exit criterion: reproducible macOS installation and clean uninstall; no dependence on Thonny or Automator environment assumptions.

### Phase 13 — Cross-platform readiness validation

Without promising Windows/Linux support yet:

- run core/application/adapter-contract tests on Linux CI;
- ensure path/process/browser abstractions are platform-neutral;
- document missing platform adapters explicitly;
- prevent accidental macOS imports in portable packages.

Exit criterion: unsupported platforms fail with a clear capability report rather than import/runtime crashes.

## 9. Definition of Done for v0.1

v0.1 is complete only when:

- macOS app starts independently of an IDE;
- Chrome connection is explicit and observable;
- one configured ChatGPT conversation can be bridged;
- DIRECT_EXECUTION completes multiple deterministic rounds;
- exactly-once action IDs survive restart;
- PASS/BLOCKED/FAIL/DONE are transported correctly;
- STOP works immediately at safe boundaries;
- no local LLM is required to interpret action/result content;
- Kit authority is preserved;
- unit/integration tests are green;
- Kit `check`/`doctor` gates are green for the governed workspace;
- architecture documentation matches the implementation.

FILE_TRANSFER may land in v0.1 only if it meets the same deterministic/recovery standard; otherwise it becomes the next milestone rather than weakening v0.1.

## 10. Explicit non-goals for the first product

- autonomous coding by Qwen/Hermes;
- generic browser automation for arbitrary websites;
- controlling multiple simultaneous LLM chats;
- replacing Kit workflow logic;
- building another GitHub client;
- interpreting arbitrary unstructured assistant prose;
- supporting Windows/Linux before macOS behavior is stable;
- distributing credentials, Chrome profiles, or model files.

## 11. Planning governance

This document is the product-level master plan. It is subordinate to current repository evidence and the Agentic Project Kit governance layer once bootstrapped.

Changes that alter trust boundaries, protocol semantics, exactly-once guarantees, Kit authority, browser identity rules, or adapter architecture require an ADR and corresponding tests.
