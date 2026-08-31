# AGP Cockpit Architecture

Normative scope authority: `docs/planning/SCOPE_BOUNDARY.md`.

## 1. Architectural style

AGP Cockpit uses a pragmatic Hexagonal/Clean Architecture with an explicit transport-state machine.

Primary design goals:

- deterministic transport rather than local reasoning;
- strict separation of browser/OS/process integrations;
- testability without Chrome, Hermes, Ollama, GitHub, Agentic Project Kit, or a real repository;
- observable/recoverable transport state;
- replaceable adapters;
- macOS-first implementation with portable boundaries.

The Cockpit is not a development agent and not a Kit workflow orchestrator.

## 2. Layers

```text
+-----------------------------------------------------------+
| Presentation                                              |
| Tkinter GUI, view models, user commands                   |
+-----------------------------------------------------------+
| Application                                               |
| Transport-session orchestration only                      |
+-----------------------------------------------------------+
| Core                                                      |
| Transport protocol, IDs, FSM, invariants, events          |
+-----------------------------------------------------------+
| Ports                                                     |
| Browser, local executor, persistence, platform, clock     |
+-----------------------------------------------------------+
| Adapters / Infrastructure                                 |
| Chrome, macOS, subprocess/Hermes, local store             |
+-----------------------------------------------------------+
```

There is intentionally no autonomous development-planning layer, no Kit-command-selection service, and no Cockpit-owned GitHub/FILE_TRANSFER workflow layer.

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
    dispatch_work_order.py
    submit_result.py
    recover_session.py
  ports/
    browser.py
    executor.py
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

The exact module names may evolve, but the dependency and scope rules are normative.

## 4. Core domain model

Representative objects:

- `SessionId`
- `RoundId`
- `ActionId`
- `TargetIdentity`
- `CommunicationMode`
- `ActionEnvelope`
- `ResultEnvelope`
- `TransportState`
- `TransportEvent`
- `TransitionResult`

The action payload is opaque to the Cockpit except for protocol metadata required for safe transport.

## 5. State machine ownership

The state machine belongs to the transport core. Adapters report transport events; they do not decide development or Kit workflow semantics.

Example:

```text
Browser adapter: completed assistant response available
        |
        v
Event(ResponseAvailable)
        |
        v
WAITING_FOR_LLM -> VALIDATING_TRANSPORT_ENVELOPE
```

A timeout can cause browser/process re-check or a transport-level stop. It must not infer Kit workflow progress.

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

It must not interpret development semantics.

### LocalExecutorPort

Responsibilities:

- execute/deliver one already-validated work-order payload unchanged;
- capture bounded stdout/stderr/return-code information;
- return evidence references;
- support cancellation at defined safe points.

It MUST NOT:

- choose a command;
- replace a failed command;
- diagnose the software problem;
- choose a Kit wrapper;
- advance Git/GitHub workflow logic.

If the browser LLM sends a Kit command, the executor merely executes it and waits for that local process to finish.

### SessionStore

Responsibilities:

- atomically persist transport-session snapshots/journal records;
- load the latest valid transport state;
- detect corruption;
- prevent unsafe duplicate dispatch after crash/restart.

It must not persist or reconstruct Kit-internal workflow state.

### PlatformPort

Responsibilities:

- executable discovery;
- process enumeration/termination;
- listener/port ownership inspection;
- application data/config/log directories;
- browser binary discovery/startup helpers;
- platform capability reporting.

## 7. Explicit absence of Kit workflow and GitHub ports

AGP Cockpit deliberately has no runtime `KitWorkflowPort`, `GitHubPort`, `TransferOrderPort`, or equivalent service for repository workflow progression.

The Cockpit may execute a browser-supplied local work order that invokes `agentic-kit`, but it must not select or construct that command itself.

In FILE_TRANSFER mode, all generation, validation, GitHub communication, remote synchronization, correlation, waiting, result association, and PASS/BLOCKED/FAIL semantics remain inside the current Agentic Project Kit process/workflow.

From the Cockpit's perspective:

```text
browser FILE_TRANSFER work order
 -> local executor starts exact work order
 -> Cockpit waits for local process
 -> local process exits/returns output
 -> Cockpit sends output to browser
```

Nothing more.

## 8. Platform strategy

### macOS adapter

Initial adapter may use controlled subprocesses, platform-specific process/listener inspection, Homebrew-aware executable discovery, standard macOS user directories, and Chrome application discovery.

No caller outside the macOS platform adapter may rely directly on `/opt/homebrew`, `/Applications/Google Chrome.app`, `pkill`, `lsof`, or macOS bundle paths.

### Future Windows/Linux adapters

Future implementations may use different process/listener APIs and browser paths while implementing the same ports. Unsupported features must be explicit capability failures.

## 9. Browser automation boundary

Browser automation is an unreliable external system.

Therefore:

- DOM selectors are adapter configuration, not domain constants;
- ambiguous page state fails closed;
- conversation identity is verified before submission;
- browser text becomes a dispatchable payload only after strict transport-envelope validation;
- completed-response detection uses observable browser state/content stability, not a single fixed delay;
- a fake browser adapter is mandatory for CI.

## 10. Hermes boundary

Hermes is optional infrastructure, not a domain dependency.

If retained, its contract is mechanical:

```text
payload in -> exact delivery/execution -> raw result out
```

No semantic rewriting, autonomous fallback, hidden continuation, development reasoning, or Kit command selection is permitted.

If this cannot be guaranteed, use a deterministic direct Python adapter.

## 11. Persistence and duplicate prevention

The Cockpit needs only strong practical at-most-once local dispatch for transport actions.

Required mechanism:

1. persist validated action ID before dispatch;
2. persist local-dispatch state;
3. capture immutable result/evidence reference when the process completes;
4. persist result before browser submission;
5. persist browser-submission evidence;
6. on ambiguous restart, stop for user/browser-LLM recovery rather than replaying automatically.

This mechanism must not attempt to infer whether an internal Kit FILE_TRANSFER sub-step completed.

## 12. Configuration

Configuration is split into version-controlled defaults/schema, local user settings, runtime/session state, and secrets.

Maintainer-specific absolute paths are not portable product configuration defaults. Browser cookies, credentials, tokens, and profiles are never version-controlled.

## 13. Logging and observability

Structured application logs may include:

- session_id;
- round_id;
- action_id;
- transport state;
- adapter;
- event;
- duration;
- local process return code;
- bounded evidence references.

The Cockpit should report what it transported and whether transport succeeded. It must not present itself as having adjudicated development correctness.

## 14. Error model

Distinguish transport/infrastructure failures such as:

- `ProtocolError`
- `BrowserStateError`
- `TargetIdentityError`
- `LocalExecutionFailure`
- `TransportTimeout`
- `PersistenceError`
- `RecoveryAmbiguous`
- `UserCancelled`
- `UnsupportedCapability`

Kit-reported `BLOCKED` or `FAIL` may be transported as terminal output/result content, but the Cockpit does not diagnose or resolve them.

## 15. Concurrency model

The GUI main thread never performs blocking browser or process operations. Application work runs in controlled workers. State changes are serialized through the transport session controller.

Prefer simple serialized orchestration over broad concurrency.

## 16. UI architecture

The GUI is a thin presentation layer. Typical commands:

- Select local repository/context
- Connect browser
- Start transport session
- Pause
- Resume
- Stop
- Open local log/evidence

The GUI must not choose Kit commands, execute GitHub workflow logic, or interpret FILE_TRANSFER progress.

## 17. Architectural fitness tests

Automated checks must prevent scope drift, including:

- `core` cannot import adapters/presentation/platform modules;
- `application` cannot import concrete adapters;
- platform-specific calls stay in platform adapters;
- browser selectors stay out of core/application;
- no runtime module named or behaving as a Kit command selector/orchestrator;
- no GitHub API/client dependency in the FILE_TRANSFER runtime path;
- no Cockpit states representing Kit-internal FILE_TRANSFER progression;
- no local-LLM semantic transformation in the executor path.
