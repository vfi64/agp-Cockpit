# AGP Cockpit Architecture

## 1. Architectural style

AGP Cockpit uses a pragmatic Hexagonal/Clean Architecture with an explicit finite-state-machine core.

Primary design goals:

- deterministic transport rather than local reasoning;
- strict separation of product logic from operating-system and browser automation;
- testability without Chrome, Hermes, Ollama, GitHub, or a real repository;
- observable, recoverable state transitions;
- replaceable adapters;
- macOS-first implementation with portable boundaries.

## 2. Layers

```text
+-----------------------------------------------------------+
| Presentation                                              |
| Desktop GUI, view models, user commands                   |
+-----------------------------------------------------------+
| Application                                               |
| Use cases, orchestration, policies for session control    |
+-----------------------------------------------------------+
| Core                                                      |
| Protocol, IDs, FSM, invariants, result types, events      |
+-----------------------------------------------------------+
| Ports                                                     |
| Browser, executor, Kit, persistence, platform, clock      |
+-----------------------------------------------------------+
| Adapters / Infrastructure                                 |
| Chrome, macOS, subprocess, Hermes, Kit CLI, file store    |
+-----------------------------------------------------------+
```

Dependency direction is inward. Outer adapters may depend on core/ports; core never depends on adapters.

## 3. Proposed Python package layout

```text
src/agp_cockpit/
  __init__.py
  core/
    ids.py
    protocol.py
    state.py
    events.py
    errors.py
    result.py
  application/
    session_controller.py
    preflight.py
    execute_action.py
    submit_result.py
    recover_session.py
  ports/
    browser.py
    executor.py
    kit.py
    persistence.py
    platform.py
    clock.py
    audit.py
  adapters/
    browser/
      chrome_cdp.py
      fake_browser.py
    executor/
      direct_subprocess.py
      hermes_transport.py
      fake_executor.py
    kit/
      cli_adapter.py
      fake_kit.py
    persistence/
      json_session_store.py
      memory_session_store.py
    platform/
      macos.py
      unsupported.py
  infrastructure/
    config.py
    logging.py
    composition.py
  presentation/
    tkinter_app.py
    view_model.py
  main.py
```

The exact module names may evolve, but the dependency rules are normative.

## 4. Core domain model

Core objects should be small immutable dataclasses or frozen value objects where practical.

Representative objects:

- `SessionId`
- `RoundId`
- `ActionId`
- `RepositoryIdentity`
- `CommunicationMode`
- `ActionEnvelope`
- `ResultEnvelope`
- `SessionState`
- `SessionEvent`
- `TransitionResult`

IDs are opaque values and never inferred from timestamps alone.

## 5. State machine ownership

The state machine belongs to the core. Adapters report events; they do not decide transitions.

Example:

```text
Browser adapter: assistant response complete
        |
        v
Event(ResponseAvailable)
        |
        v
Core transition: WAITING_FOR_LLM -> VALIDATING_ACTION
```

A timeout adapter/clock can emit `TimeoutExpired`, but only the FSM decides whether that means `BLOCKED`, `FAIL`, retry/recheck, or no transition.

## 6. Ports

### BrowserSessionPort

Responsibilities:

- connect/start a browser session;
- bind to an explicit conversation;
- observe whether assistant generation is active/complete;
- retrieve the latest completed assistant message;
- place text into the composer;
- submit the composer;
- return browser/conversation identity evidence.

It must not parse AGP Cockpit protocol semantics.

### LocalExecutorPort

Responsibilities:

- execute one already-validated local execution request;
- stream/capture bounded stdout/stderr metadata;
- return exit status and evidence references;
- support cancellation at defined safe points.

It must not choose commands.

### KitPort

Responsibilities:

- discover current Kit capabilities/commands where supported;
- run canonical preflight/check/doctor/transfer operations;
- expose machine-readable Kit outcomes to the application layer;
- avoid reconstructing Kit internals.

### SessionStore

Responsibilities:

- atomically persist session snapshots/journal records;
- load the latest valid state;
- detect corruption;
- support migration of persisted state schema.

### PlatformPort

Responsibilities:

- executable discovery;
- process enumeration/termination;
- listener/port ownership inspection;
- application data/config/log directories;
- browser binary discovery/startup helpers;
- platform capability reporting.

## 7. Platform strategy

### macOS adapter

Initial concrete adapter may use:

- `subprocess` for controlled process execution;
- `lsof`/native socket inspection behind `PlatformPort` where needed;
- Homebrew-aware executable discovery without assuming Homebrew is mandatory;
- standard macOS user directories for config/log/runtime data;
- Chrome application bundle discovery;
- CDP launch arguments for dedicated browser automation sessions.

No caller outside `adapters/platform/macos.py` may rely on `/opt/homebrew`, `/Applications/Google Chrome.app`, `pkill`, `lsof`, or macOS bundle paths directly.

### Future Windows/Linux adapters

Future implementations may use different process/listener APIs and browser paths while implementing the same ports. Unsupported features must be surfaced as explicit capability failures.

## 8. Browser automation boundary

Browser automation is considered an unreliable external system.

Therefore:

- DOM selectors are adapter configuration, not domain constants;
- all selectors must have bounded fallback strategies;
- ambiguous page state fails closed;
- conversation identity is verified before every submission;
- browser text is never treated as an executable payload until the protocol parser validates it;
- completed-response detection uses observable browser state and content stability, not a single fixed delay.

A fake browser adapter is mandatory for CI.

## 9. Hermes boundary

Hermes is optional infrastructure, not a domain dependency.

If retained, the Hermes adapter must operate in a no-reasoning transport contract:

- payload in;
- deterministic tool/execution request;
- payload/result out;
- no semantic rewriting;
- no autonomous fallback commands;
- no hidden continuation loop.

If Hermes cannot provide this guarantee reliably, the direct deterministic adapter becomes the default path.

## 10. Persistence and exactly-once semantics

The cockpit cannot guarantee globally transactional exactly-once execution across browser, local process, Git, and remote systems. It can, however, implement strong practical at-most-once local dispatch with evidence-based recovery.

Required mechanism:

1. persist validated action and `READY_TO_EXECUTE` before dispatch;
2. persist `EXECUTING` and action ID before invoking executor;
3. executor returns immutable result/evidence reference;
4. persist result before browser submission;
5. persist `RESULT_SUBMITTED` only after browser submission evidence;
6. on restart, inspect persisted state plus local/Kit evidence before deciding whether any action may be replayed.

Ambiguous recovery must become `BLOCKED_RECOVERY_REQUIRED`, never automatic replay.

## 11. Configuration

Configuration is split into:

- version-controlled defaults/schema;
- local user settings;
- runtime/session state;
- secrets.

Local settings must not require repository-local absolute user paths. Repository selection is a runtime/user setting.

Secrets, browser cookies, tokens, and Chrome profile data are never stored in version-controlled configuration.

## 12. Logging and observability

Use structured application logs with correlation fields:

- session_id;
- round_id;
- action_id;
- state;
- adapter;
- event;
- duration;
- status.

Do not log secrets or full unbounded LLM responses by default.

User-visible audit information should answer:

- what action was received;
- whether it was validated;
- what adapter executed it;
- what result status occurred;
- what evidence/log location exists;
- whether the result was submitted;
- why the system stopped.

## 13. Error model

Distinguish at least:

- `ProtocolError`
- `BrowserStateError`
- `RepositoryIdentityError`
- `KitBlocked`
- `ExecutionFailure`
- `TimeoutBlocked`
- `PersistenceError`
- `RecoveryAmbiguous`
- `UserCancelled`
- `UnsupportedCapability`

Do not collapse all errors into a generic exception string in the UI.

## 14. Concurrency model

The GUI main thread never performs blocking browser, process, network, or Kit operations.

Application work runs in controlled worker tasks/threads/processes. State changes are serialized through the session controller/FSM. The first implementation should prefer simple serialized orchestration over broad async concurrency.

The design may later adopt `asyncio`, but asynchronous technology is not itself an architectural goal. Deterministic transitions and cancellation are the goal.

## 15. UI architecture

The GUI is a thin presentation layer. It exposes commands such as:

- Select repository
- Connect browser
- Run preflight
- Start session
- Pause
- Resume
- Stop
- Open log/evidence

The GUI binds to a view model or immutable snapshot. It must not directly call `subprocess`, manipulate Chrome, edit Hermes config, or inspect port 11434.

## 16. Dependency policy

Prefer Python standard library for core/application code.

Third-party dependencies are accepted when they materially improve correctness or maintainability. Each runtime dependency must be isolated behind a narrow adapter where possible.

Browser automation technology (CDP client, Playwright, Selenium, Hermes browser tooling) is an implementation decision to be tested, not a domain commitment.

## 17. Architectural fitness tests

Add automated checks that prevent architectural drift, for example:

- `core` may not import from `adapters`, `presentation`, or platform modules;
- `application` may not import concrete adapters;
- platform-specific imports are restricted to platform adapter packages;
- browser selectors do not appear in core/application packages;
- Kit-specific command strings are centralized in the Kit adapter/capability layer rather than scattered across GUI code.

These tests are part of the definition of done for structural refactors.
