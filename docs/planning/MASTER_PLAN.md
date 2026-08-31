# AGP Cockpit Master Plan

Status: corrected planning baseline

Normative scope authority: `docs/planning/SCOPE_BOUNDARY.md`.

If this plan ever conflicts with `SCOPE_BOUNDARY.md`, the scope-boundary document wins.

## 1. Mission

AGP Cockpit is a local Python/Tkinter desktop application that removes the mechanical copy/paste work between a browser-based development LLM and a local terminal/executor.

It does not perform development work.

The browser LLM performs reasoning, planning, development, diagnosis, and formulation of the next local work order. The Agentic Project Kit performs governed repository work, workflow validation, mutation, Git/GitHub lifecycle, FILE_TRANSFER, evidence, gates, handoff, PR/merge/release behavior. AGP Cockpit only transports browser work orders to the local terminal and transports resulting terminal/Kit output back to the same browser conversation.

Initial supported host: macOS. Architecture must keep OS-specific behavior behind adapters so later Windows/Linux support does not require rewriting the portable core.

## 2. Non-negotiable role separation

```text
User
  |
  v
Browser LLM
  |  reasoning / planning / development / diagnosis / next work order
  v
AGP Cockpit
  |  deterministic local transport only
  v
Local terminal / executor
  |
  v
Agentic Project Kit
  |  workflow / validation / mutation / GitHub / FILE_TRANSFER /
  |  evidence / gates / handoff / PR / merge / release
  v
Repository / Remote
```

AGP Cockpit MUST NOT:

- decide what code to write;
- diagnose software semantically;
- plan development slices;
- choose the next repository step;
- choose, construct, repair, or substitute Agentic Project Kit commands;
- resolve Kit `BLOCKED` or `FAIL` outcomes;
- implement Git/GitHub repository workflow logic;
- implement or mirror FILE_TRANSFER generation, validation, publishing, fetching, synchronization, waiting, correlation, or result association;
- let Hermes/Qwen or another local LLM reinterpret browser-LLM work orders;
- treat arbitrary unstructured assistant prose as executable work.

## 3. Product goals

### G1 — Reliable local bridge

Provide a GUI showing at minimum:

- browser/conversation connection state;
- selected local working repository/context;
- local execution state;
- communication mode;
- current transport round/action ID;
- last local process result;
- PAUSE/STOP controls;
- local audit-log location.

### G2 — Deterministic browser transport

The browser adapter must:

1. connect to the intended Chrome session/profile;
2. bind to one explicit browser conversation;
3. detect completed assistant responses;
4. extract exactly one framed work-order payload;
5. return exactly one framed result payload;
6. fail closed on ambiguity.

### G3 — Deterministic local execution transport

The local executor must:

1. receive one already-framed work order;
2. execute/deliver it without semantic rewriting;
3. capture bounded stdout/stderr/return code or result references;
4. support cancellation at defined safe boundaries;
5. return raw/structured execution evidence to the Cockpit.

The executor must not choose commands.

### G4 — Two communication modes, same Cockpit responsibility

`DIRECT_EXECUTION` and `FILE_TRANSFER` differ in what the browser LLM asks the local terminal/Kit to do, not in Cockpit authority.

- `DIRECT_EXECUTION`: the browser LLM provides the complete local work order; Cockpit executes/transports it and returns the result.
- `FILE_TRANSFER`: the browser LLM provides the complete local work order that invokes the current canonical Kit FILE_TRANSFER path; Cockpit executes/transports it and waits for the local Kit process to finish. The Kit owns all remote/GitHub transfer semantics.

### G5 — No local reasoning dependency

Hermes/Qwen may be used only as a mechanical transport/execution adapter if payload fidelity can be guaranteed. The architecture must allow replacing Hermes with a deterministic Python adapter.

### G6 — Crash-safe transport resumability

Persist only the transport/session information required to prevent accidental duplicate dispatch and to recover browser/local-process state safely. Recovery logic must not infer or continue Kit workflow semantics.

### G7 — Portable architecture

macOS-first, portable core. OS-specific executable discovery, process/listener handling, browser startup, and user-data locations live behind platform adapters.

## 4. Architecture principles

Pragmatic Clean/Hexagonal Architecture:

```text
presentation/        Tkinter GUI only
application/         transport-session orchestration only
core/                transport protocol, IDs, transport FSM, invariants
ports/               browser, executor, persistence, platform, clock, audit
adapters/
  browser/
  executor/
  persistence/
  platform/
infrastructure/      composition root, logging, config
```

There is intentionally no autonomous development-planning service, no Kit-command-selection service, and no Cockpit-owned GitHub/FILE_TRANSFER workflow service.

## 5. Cockpit transport state machine

The Cockpit state machine represents transport state only:

```text
IDLE
 -> PREFLIGHT
 -> CONNECTING_BROWSER
 -> WAITING_FOR_LLM
 -> VALIDATING_TRANSPORT_ENVELOPE
 -> READY_TO_DISPATCH
 -> EXECUTING_LOCAL_WORK_ORDER
 -> COLLECTING_LOCAL_RESULT
 -> PREPARING_RESULT_ENVELOPE
 -> SENDING_RESULT_TO_BROWSER
 -> WAITING_FOR_LLM

Terminal/interrupt states:
 DONE
 BLOCKED_TRANSPORT
 FAIL_TRANSPORT
 PAUSED
 USER_STOPPED
```

There must be no Cockpit FILE_TRANSFER states such as `ORDER_PUBLISHING`, `WAITING_FOR_REMOTE_RESULT`, `REMOTE_VISIBLE`, `RESULT_FETCHING`, or equivalent. Those belong to the Kit.

## 6. Protocol invariants

The protocol protects transport integrity, not development semantics.

Each action contains at minimum:

- protocol version;
- session/round/action IDs;
- communication mode;
- local target/repository identity expectations where required;
- opaque work-order payload.

Each result contains at minimum:

- matching IDs;
- local process return/result status;
- bounded output/summary or evidence references;
- transport/browser submission evidence where needed.

The Cockpit validates framing, IDs, duplication, target identity, and size constraints. It does not judge whether the work order is a good development decision.

## 7. Security/trust boundary

- Browser LLM is development intelligence.
- Agentic Project Kit is repository workflow/safety authority.
- Cockpit is transport infrastructure.
- Hermes/local LLM is optional mechanical infrastructure only.

A feature is in scope only if it is necessary for browser-to-terminal transport, terminal-to-browser transport, or safe operation/observation of that transport channel.

## 8. Development phases

### Phase 0 — Repository governance bootstrap

Place this repository under the current Agentic Project Kit external-workspace governance path using the current highest-level Kit orchestrators. Establish clean local/remote gates before product implementation.

Exit: governed workspace, adjudicated planning sources, green applicable Kit checks.

### Phase 1 — CI/gate baseline

Establish CI before substantive feature work:

- Python test/lint baseline;
- Linux CI for portable layers;
- macOS CI for safe platform tests;
- architecture/scope fitness tests;
- Kit gates for exact commit.

Exit: required checks green.

### Phase 2 — Legacy GUI characterization

Import the existing working macOS Ollama/Hermes Tkinter application as a reference/baseline fixture. Characterize only behavior that supports the future transport environment: process lifecycle, executable/model/config discovery, GUI start/stop/status, and logging.

Do not preserve or add any autonomous local-LLM reasoning behavior.

### Phase 3 — Architectural extraction

Separate:

- portable transport core/application;
- browser port;
- local executor port;
- persistence/session store;
- platform port;
- thin Tkinter presentation.

Exit: core/application tests run without Chrome, Hermes, Ollama, macOS, GitHub, or a real repository.

### Phase 4 — macOS platform adapter

Implement executable/process/browser discovery and safe lifecycle control behind platform ports.

### Phase 5 — Browser bridge proof of concept

One configured Chrome conversation:

- connect;
- identify conversation;
- read a completed assistant message;
- insert text without send;
- send under explicit confirmation;
- detect next completed response.

No Kit workflow intelligence.

### Phase 6 — Transport protocol v1

Implement strict, versioned framing and duplicate/action-ID handling. Payload content is opaque to the Cockpit except for transport metadata.

### Phase 7 — Single DIRECT_EXECUTION round

```text
browser work order
 -> validate transport envelope
 -> dispatch unchanged to local executor
 -> wait
 -> capture result
 -> return result to browser
 -> stop
```

### Phase 8 — Automated multi-round bridge

Repeat the same mechanical round trip with bounded maximum rounds, pause/stop, duplicate protection, browser/process timeout handling, and explicit browser-LLM DONE declaration.

### Phase 9 — FILE_TRANSFER pass-through

Prove that a browser-LLM work order can invoke the current canonical Kit FILE_TRANSFER workflow locally and that the Cockpit simply waits for the local process and returns its output.

Acceptance criteria explicitly include:

- no Cockpit GitHub API/client code for FILE_TRANSFER;
- no Cockpit transfer-order generator/validator;
- no Cockpit remote polling/synchronization/correlation state machine;
- no handcrafted transfer YAML;
- all FILE_TRANSFER semantics evidenced as Kit-owned.

### Phase 10 — Hermes versus deterministic adapter gate

Compare Hermes mechanical transport with a deterministic Python executor/browser path. Choose the simplest reliable non-reasoning transport. Remove Hermes from the critical path if it adds semantic transformation or unnecessary failure modes.

### Phase 11 — Desktop hardening

- Tkinter product polish;
- structured logs;
- settings/version migration;
- first-run diagnostics;
- macOS packaging independent of Thonny/Automator environment assumptions.

### Phase 12 — Cross-platform readiness validation

Keep portable layers platform-neutral and add explicit unsupported-platform capability reporting. Do not claim Windows/Linux support until their adapters are implemented and tested.

## 9. Definition of Done for v0.1

v0.1 is complete only when:

- the macOS Tkinter app starts independently of an IDE;
- one configured Chrome conversation can be bridged;
- browser work orders can be delivered unchanged to the local executor;
- local results can be returned automatically to the same browser conversation;
- multiple mechanical rounds can run with pause/stop and duplicate protection;
- no local LLM reasoning is required;
- the Cockpit contains no development-planning, Kit-command-selection, GitHub lifecycle, or FILE_TRANSFER workflow implementation;
- applicable unit/integration/scope-fitness tests are green;
- remote CI is green for the exact commit;
- applicable Agentic Project Kit gates are green.

## 10. Explicit non-goals

- autonomous coding or diagnosis by AGP Cockpit;
- autonomous coding or diagnosis by Hermes/Qwen;
- Kit command selection by AGP Cockpit;
- Git/GitHub repository workflow logic in AGP Cockpit;
- FILE_TRANSFER semantics in AGP Cockpit;
- transfer-order creation/validation in AGP Cockpit;
- GitHub polling/webhooks for Kit workflow progression in AGP Cockpit;
- replacing Agentic Project Kit safety/workflow logic;
- generic browser automation unrelated to the configured LLM bridge;
- interpreting arbitrary unstructured assistant prose;
- supporting multiple simultaneous development chats in v0.1.

## 11. Planning governance

`docs/planning/SCOPE_BOUNDARY.md` is normative and exists specifically to prevent future LLMs from expanding the Cockpit into a development agent, Kit orchestrator, or GitHub/FILE_TRANSFER implementation.

Any proposed scope expansion requires explicit maintainer approval, an ADR, updated planning documents, and corresponding tests/gates before implementation.
