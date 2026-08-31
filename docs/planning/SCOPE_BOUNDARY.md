# AGP Cockpit — Normative Scope Boundary

Status: active
Status-date: 2026-08-31
Decision status: accepted
Review policy: on material change

This document exists to prevent architectural scope drift. If another planning document, prior chat, proposed implementation, or agent suggestion conflicts with this boundary, this document wins unless the maintainer explicitly changes it through a reviewed planning/ADR change.

## 1. One-sentence product definition

AGP Cockpit is only a deterministic local communication bridge between a browser-based development LLM and a local terminal/executor.

It does not perform development work.

## 2. Exact responsibility split

```text
User
  |
  v
Browser LLM
  |  reasoning, planning, development, diagnosis,
  |  selection/formulation of the next local work order
  v
AGP Cockpit
  |  mechanical local transport only
  v
Local terminal / executor
  |
  v
Agentic Project Kit
  |  workflow, validation, mutation, Git/GitHub lifecycle,
  |  file transfer, remote synchronization, evidence, gates,
  |  handoff, PR/merge/release behavior
  v
Local repository / GitHub as controlled by the Kit
```

## 3. AGP Cockpit MAY do only transport-support work

AGP Cockpit may:

- connect to the configured browser conversation;
- wait until a browser-LLM response is complete;
- extract an explicitly framed transport payload;
- validate transport framing, IDs, size limits, duplicate IDs, and target-session identity;
- deliver the payload to the configured local terminal/executor without semantic rewriting;
- observe process completion and capture bounded stdout/stderr/return-code data;
- return the resulting terminal/Kit output to the same browser conversation;
- repeat this mechanical round trip until the browser LLM explicitly declares the user task finished;
- maintain local transport/session state needed for crash safety, duplicate prevention, pause/stop, and observability;
- start/stop/configure purely local supporting processes such as Ollama/Hermes/Chrome when they are part of the mechanical transport environment.

Transport validation is not development reasoning. It is limited to protocol integrity and safe delivery.

## 4. AGP Cockpit MUST NOT perform development work

AGP Cockpit must never:

- decide what code to write;
- diagnose a software defect semantically;
- plan a development slice;
- choose the next repository/workflow step;
- choose which Agentic Project Kit command should be used;
- construct or improve a Kit command;
- replace a failed Kit action with another command;
- decide how to resolve `BLOCKED` or `FAIL`;
- edit product source code as an autonomous development actor;
- create its own Git/GitHub/PR/merge/release workflow;
- interpret arbitrary natural-language assistant prose as an executable action;
- let Hermes/Qwen or another local LLM reinterpret, summarize, improve, repair, or replace the browser-LLM work order.

The browser LLM is the development intelligence. The Kit is the workflow/safety authority. The Cockpit is the wire between them.

## 5. DIRECT_EXECUTION mode

In `DIRECT_EXECUTION`, the browser LLM provides one complete local work order suitable for execution in the local terminal/executor.

AGP Cockpit:

1. verifies the transport envelope;
2. delivers the contained work order unchanged to the local executor;
3. waits for completion;
4. captures bounded result/evidence references;
5. sends that result back to the browser LLM.

AGP Cockpit does not select a Kit wrapper or command. If the correct work order is an Agentic Project Kit command, the browser LLM must formulate that work order according to the current repository/Kit contract, and the Kit performs the governed work.

## 6. FILE_TRANSFER mode

In `FILE_TRANSFER`, AGP Cockpit still performs only the same local browser-to-terminal and terminal-to-browser transport.

All file-transfer semantics belong to the Agentic Project Kit, including where supported by the current Kit:

- transfer-order generation;
- transfer-order validation;
- inbox/outbox handling;
- Git/GitHub communication;
- remote publishing/fetching;
- remote visibility checks;
- correlation/order tracking;
- waiting/retry policy;
- synchronization;
- result association;
- transfer evidence;
- PASS/BLOCKED/FAIL semantics.

AGP Cockpit MUST NOT implement, duplicate, emulate, or partially mirror any of those responsibilities.

Therefore the Cockpit must not contain a FILE_TRANSFER state machine such as `ORDER_PUBLISHING`, `WAITING_FOR_REMOTE_RESULT`, `RESULT_FETCHING`, or equivalent Kit-internal workflow states. From the Cockpit's perspective, a FILE_TRANSFER action is simply a local work order whose terminal execution may take time because the Kit is performing its own transfer workflow.

The Cockpit may expose only transport-level states such as `EXECUTING_LOCAL_WORK_ORDER` or `WAITING_FOR_LOCAL_PROCESS`, without interpreting Kit-internal progress.

## 7. GitHub boundary

AGP Cockpit is not a GitHub client for repository development.

It must not directly:

- poll GitHub CI to decide workflow progress;
- create/merge PRs;
- push branches;
- publish/fetch file-transfer orders;
- inspect remote transfer state in order to advance FILE_TRANSFER;
- implement GitHub webhooks for Kit workflow progression.

If GitHub participates in development or FILE_TRANSFER, the current Agentic Project Kit workflow owns that interaction.

## 8. Hermes/Qwen boundary

Hermes and a local LLM are optional mechanical infrastructure only.

If used, their contract is equivalent to a dumb transport/execution adapter:

```text
payload in -> execute/deliver exactly -> raw result out
```

No local-LLM reasoning may become required for correctness. If Hermes cannot guarantee payload fidelity and non-reasoning behavior, replace that transport path with a deterministic Python adapter.

## 9. Development rule for this repository

When developing AGP Cockpit itself, every LLM/agent must test proposed features against this question:

> Is this feature necessary to transport browser-LLM work to the local terminal, transport the resulting local output back, or safely operate that transport channel?

If the answer is no, it is out of scope unless the maintainer explicitly changes this normative boundary.

In particular, "it would be more convenient if the Cockpit decided/planned/managed the Kit or GitHub workflow" is not a valid reason to expand scope.
