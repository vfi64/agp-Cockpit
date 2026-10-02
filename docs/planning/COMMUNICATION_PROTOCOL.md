# AGP Cockpit Communication Protocol
Status: canonical communication authority; complete cross-component lifecycle baseline.

This document complements `docs/planning/PROTOCOL.md`: that file defines Protocol-v1 frame semantics; this file governs the complete cross-component Cockpit communication/lifecycle protocol.

## Layers
Track separately: mission lifecycle; start-request generation/latch; content-script lifecycle; native browser send; conversation observation; turn submission; Protocol-v1 execution; local Task Contract authorization; result delivery/ack; reload/recovery/idempotency.

## Identities
Track where applicable `mission_id`, `task_id`, start generation, run/content generation, turn, step, `message_id`, `session_id`, `round_id`, `action_id`, correlation IDs, and reload/attachment lifetime. They are not interchangeable.

## Normative high-level sequence
MISSION/READY → task-start persisted/accepted → bootstrap prepared → native submit dispatched → authoritative user-turn commit → native send accepted → MISSION_BOOTSTRAP_SENT → assistant observed/completed → TURN_SUBMIT_STARTED_CLIENT → work-order parse/validation → local Task Contract authorization → Protocol-v1 execution → authoritative result_frame → RESULT_DELIVERED → TURN_SUBMIT_OK → continuation or terminal transition.

## Invariants
Reload does not silently create or duplicate mission/task/generation/action/execution. A completed assistant response executes at most once for its identity. Remote work-order content never self-grants authority. No Protocol-v1 action bypasses the local Task Contract. Success requires authoritative commit/result evidence. BLOCKED/FAIL/NEEDS_HUMAN are not bypassed. Contradictory state fails loud.

A bounded ChatGPT account/service-limit notice is remote service state, not an
assistant work order. After checking for an authoritative command attachment, the
browser must stop with `REMOTE_SERVICE_LIMIT` before the K07 attachment timer. This
classification never permits ordinary prose to bypass the exactly-one-`.py` rule.

## Failure analysis
Classify at the first failed transition. State recovery ownership and which identities retry/reuse/advance. Absence of a success event alone does not identify root cause.

## Verified Generation 52 trace — 2026-09-16
Start accepted → native bootstrap send succeeded → real assistant response observed → TURN_SUBMIT_STARTED_CLIENT → TICK_ERROR `PermissionError: ACTION_NOT_AUTHORIZED_BY_LOCAL_TASK_CONTRACT`; mission remained READY, turn 0, step 0.
Current first proven divergence: local Task Contract authorization after turn submission starts. This is not a native-composer failure.

Before repair, reconstruct work-order shape → Protocol-v1 action mapping → local Task Contract/effect/tool/network authority → executor boundary → failure/recovery semantics.

## Participants and interfaces

Human owns the overall Task Contract and genuine checkpoints. Cockpit owns durable task/mission lifecycle and enforcement of already-established local authority. Browser/content script owns mechanical observation, framing, native submit and result return. Bridge owns the authenticated transport and Protocol execution boundary. The persisted Local Task Contract is the sole source of local effect/tool/network authority. The local executor executes only authorized work. Agentic Project Kit owns repository/workflow/Git/GitHub semantics when invoked. The Remote LLM produces bounded work orders and completion proposals; it cannot self-grant local authority.

## Event catalogue and layer state

Canonical forward chain:
`TASK_START_REQUEST_ACCEPTED` -> bootstrap prepared -> native submit dispatched ->
`NATIVE_USER_TURN_COMMITTED` -> `NATIVE_SEND_ACCEPTED` -> `MISSION_BOOTSTRAP_SENT` ->
assistant observed/completed -> `TURN_SUBMIT_STARTED_CLIENT` -> work-order parse/validation ->
local Task Contract authorization -> Protocol execution -> authoritative `result_frame` ->
`RESULT_DELIVERED` -> `TURN_SUBMIT_OK` -> continuation or terminal transition.

Mission/task state, start-request generation, content-script attachment generation, browser-message identity, Protocol action identity and executor attempt are correlated but not interchangeable.

Native send acceptance requires decisive commit evidence after the send
boundary (`AGP_K07_SEND_COMMIT_NONCE_V1`). Every native send prefixes the
prompt with a fresh first line `AGP-SEND-<16 hex>` generated from
`crypto.getRandomValues`. Its occurrence outside the composer in two
consecutive observations after submit is decisive commit evidence; because the
nonce did not exist before the send, this evidence is independent of ChatGPT's
user-turn wrappers, message ids, Markdown projection, virtualization window and
conversation URL. The rendered-turn match below remains an additional,
equally decisive path. An emptied composer is never commit evidence.

The rendered-turn path requires a persistent user-turn match after the send
boundary. The browser may recognize that user turn through ChatGPT's semantic
role/test-id wrappers or through the visible localized author-heading layout
(`Du hast gesagt:` / `You said:`) when role wrappers are absent. The match must
be exact, except that a new long collapsed rendering may count when it is a
prefix of the exact text inserted by the native transport or has the same long
rendered beginning as that exact inserted text.
Generation activity, composer mutation, and assistant activity remain telemetry
only and do not prove send acceptance.

If send acceptance remains indeterminate and the prompt may have reached
ChatGPT, the bridge reserves the expected local work-order number before
stopping. Future `next_local_step` calculations include that reservation, even
when no local command file was materialized, so a retry does not request a
number that may already be visible in the conversation.

## Cross-layer transition table

| From | Required evidence | To | Failure owner |
|---|---|---|---|
| task requested | persisted start request plus accepted identity | bootstrap prepared | task runtime |
| bootstrap prepared | native dispatch plus authoritative user-turn commit | bootstrap sent | browser/native transport |
| bootstrap sent | completed assistant observation | turn submission | browser observation |
| turn submission | valid framed work order | authorization | parser/protocol |
| authorization | persisted Local Task Contract permits effect/tool/network | execution | authority/bridge |
| execution | EXECUTED/REPLAYED plus non-empty authoritative result frame | result delivery | executor/bridge |
| result delivery | delivery acknowledgement | turn committed | browser transport |
| turn committed | continuation or verified terminal proposal | next/terminal | task controller |

Classify failure at the first transition whose required evidence is absent or contradictory.

## Temporal sequence

Human/Cockpit -> Task runtime -> Browser/Content -> Bridge/Authority -> Executor/Kit -> Remote LLM.
The normative order is task/start, native bootstrap send, assistant observation, turn submit, authorization, execution, result delivery, turn acknowledgement, then continuation or terminal transition. Durable state is reconciled before new work after reload/restart.

## Identity and lifetime table

`task_id` is stable across the overall task. `mission_id` identifies a concrete mission execution. Start generation and browser/content generation are distinct epochs. `message_id` identifies a message; resend preserves it. `session_id` scopes a transport session. `round_id` correlates a round. `action_id` identifies the requested effect; same-payload replay must not duplicate it and changed-payload reuse is a violation. `attempt_id` correlates an execution/result attempt where v2 applies. A binding epoch versions task/capability binding and stale epochs are rejected. Reload, bridge restart, browser reattachment or chat switch alone authorize none of these to advance.

## Authorization matrix

Human/persisted Local Task Contract may grant local effect/tool/network authority. Remote LLM work orders may request work but cannot grant authority. Browser/content and Bridge transport/enforce only. Executor cannot widen authority. Kit governs Kit-owned workflow only within supplied local authority. Authorization failure is fail-loud; recovery may repair propagation but must not widen configured authority to make an E2E pass.

## Retry, replay and idempotency

Same `action_id` plus same payload may replay without duplicate effect. Same `action_id` plus changed payload is a protocol violation. A result may be resent with the same message identity without re-execution. A completed assistant response executes at most once for its authoritative identity. Reload/restart reconciles durable state before new dispatch. Unknown effect outcome remains unknown/BLOCKED until reconciled.

## Timeout ownership

Browser observation owns assistant-observation timeout; Bridge owns bounded transport timeout; executor owns local process timeout; Kit owns Kit workflow/gate timeout. Timeout reports the last authoritative completed transition and never by itself authorizes a retry that could duplicate an effect.

## Error taxonomy

`TRANSPORT`: authenticated delivery/browser/native boundary. `FRAME_OR_PARSE`: malformed or semantically invalid frame/work order. `AUTHORIZATION`: persisted Local Task Contract denies requested effect/tool/network. `EXECUTION`: authorized local work fails/times out. `RESULT_DELIVERY`: authoritative result exists but downstream acknowledgement fails. `STATE_DIVERGENCE`: identity/generation/durable/runtime state contradict. `NEEDS_HUMAN`: genuine declared checkpoint. `KIT_BLOCKED`/`KIT_FAIL`: Kit-owned outcome that Cockpit preserves rather than bypasses. Primary classification is the first proven divergent transition.

## Trace-to-spec conformance procedure

For every real acceptance and non-trivial protocol failure: bind all task/mission/generation/message/session/round/action identities and timestamps; reconstruct observed events from durable/runtime evidence; compare each transition with this authority; identify the first missing/contradictory transition; check Local Task Contract authorization; check replay/idempotency before recovery; attribute the owning layer; preserve evidence; repair the smallest coherent owning-layer cause; run focused and broad affected gates; repeat the real browser/remote-LLM E2E; record the trace in `docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md`.

## Current acceptance baseline

Generation 52 proved native bootstrap send and real assistant observation. Its first proven divergence was Local Task Contract authorization after `TURN_SUBMIT_STARTED_CLIENT`. Acceptance of the repair requires repeating the real same-conversation path through authorization, execution, result delivery and `TURN_SUBMIT_OK`. No older Phase-7/8/9 E2E substitutes for this current acceptance.

## Documentation completion status

The complete cross-component communication baseline required for protocol-first engineering is represented by this document together with `docs/planning/PROTOCOL.md`. Future protocol-affecting changes update these authorities, regression invariants and `docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md` in the same coherent slice.

## K07 FILE_TRANSFER — NON-NEGOTIABLE ARCHITECTURE BOUNDARY

This section is normative and overrides legacy text/JSON compatibility behavior for normal task-first K07 `LIVE` + `FULL_AUTO` cycles.

1. The command payload from ChatGPT is exactly one `.py` attachment. The visible assistant prose/text is not the command payload. The only other accepted remote file is the terminal reply `<step>_agp_terminal.json` (see item 11 of "K07 Delivery, Replay and In-Flight State"); it is never executed.
2. Cockpit materializes that attachment and sends it through the existing file-loop ingress (`submitAssistantCommandFile` -> `/v1/file-loop/command`).
   Attachment preview text is UI evidence only. For link-rendered files the payload
   comes from the authenticated file fetch; for button-rendered files the payload
   comes from the browser download materialized through `/v1/file-loop/download`.
   Preview `innerText`/`textContent` must not be submitted as command content.
   Download and command ingress validate the executable work-order contract
   before returning `COMMAND_FILE_FETCHED` or accepting a local file-loop turn.
3. A normal K07 cycle MUST NOT require, parse, repair, or execute a pure-JSON work order from visible ChatGPT text.
4. If the required `.py` attachment is absent, K07 MUST fail loud with `K07_FILE_TRANSFER_ATTACHMENT_REQUIRED`. It MUST NOT send a JSON format-repair prompt.
5. JSON remains permitted only as an internal control/serialization format and for explicitly named legacy/probe compatibility paths. It is not the normal K07 chat payload.
6. Result/continuation transport is file-oriented as defined by the file loop; Protocol-v1 text execution is not a substitute for FILE_TRANSFER.
7. Local Task Contract authority remains authoritative. FILE_TRANSFER cannot widen effect/tool/network/cwd authority. Cockpit is mechanical transport; Kit owns repository/workflow semantics.
8. Acceptance evidence for a normal non-terminal K07 turn is successful file-loop processing (`K07_COMMAND_FILE_TURN_COMPLETE` or its canonical successor), not legacy text-path `TURN_SUBMIT_OK`.
9. Any implementation or test that routes a normal task-first K07 `LIVE` + `FULL_AUTO` response without an attachment into pure-JSON parsing/format repair contradicts this protocol and must fail.

## K07 EXECUTION MAXIME — MINIMAL PROVEN PATH

This section is normative for K07 development and acceptance.

1. Optimize for the shortest authoritative end-to-end chain: create command file -> transfer command file -> execute locally under Local Task Contract -> create result file -> transfer result file.
2. Files are the payload for normal K07 FILE_TRANSFER. Visible chat text, pure JSON work orders, format-repair prompts, and Protocol-v1 text execution are not alternate success paths.
3. Do not add, repair, or activate a fallback merely to bypass a failure in the authoritative path. Fail loud at the first divergent boundary.
4. Proven facts are frozen. Do not rediscover or replace them with assumptions unless new contradictory evidence exists.
5. After every product-code mutation, run the cheapest mechanically relevant integrity gate before E2E (for example JS syntax check, Python compile/test, `git diff --check`, focused regression tests).
6. Run at most one fresh real E2E after those gates pass. Diagnose and repair only its first new divergence.
7. Do not broaden Local Task Contract authority, bypass Kit workflow semantics, manipulate the turn counter, or substitute synthetic/direct execution for real transport evidence.
8. A step should be the largest safe coherent unit: reproduce when necessary, repair the proven defect, run focused gates, then real E2E when justified. Avoid diagnostic-only micro-steps when the repair is mechanically determined.
9. Acceptance is evidence-based: each boundary must be proven by authoritative events/artifacts. UI appearance or absence of an error is not sufficient evidence.
10. If a proposed change increases protocol paths or ambiguity instead of reducing them, stop and justify it against this section before implementation.

## K07 COMMAND-FILE EXECUTION CONTRACT

This section is normative for the local Python work-order boundary.

1. A command attachment must be semantically complete, not merely valid
   Python. The deterministic preflight requires an executable entry point,
   an explicit `__main__` guard, an explicit `--self-test` argument, a
   declared `agentic-kit` command, and a return-bundle writer.
2. A command that fails this contract is rejected before the local runner or
   Kit is invoked. The rejection produces one diagnostic return bundle with
   command-file byte size, line count, SHA-256, interpreter, CWD and runner
   argv.
   The same contract is checked at the transport ingress, so a truncated or
   non-executable download is rejected before it becomes an accepted local
   work order.
3. `py_compile` success, `--self-test` exit code 0, or a real-run exit code 0
   alone never proves that the requested work happened. Exactly one valid
   JSON return bundle is required.
4. The execution identity in the return bundle must distinguish the command
   file, interpreter, CWD, argv and return code. Transport hashes prove only
   that the received content was not changed between transport stages; they
   do not prove that the remote model originally generated a complete file.
5. A failed file-loop step may request bounded recovery only while progress is
   still possible. After three consecutive failures with the same failure
   signature and no proven progress, the loop enters terminal `BLOCKED` and
   sends no additional automatic remote turn.

## Verified Standard-Task Handoff Completion

The locally created chat-switch task carries `verified-successor-handoff-v1`.
Only this explicit contract enables local terminal handoff verification.
The file-loop reads desktop task authority from `tasks.sqlite3`, not the
independent Protocol-v1 session database.

A successful runner result must identify the canonical package, fresh required
files, the current revision and a step-bound detailed prompt. The installed Kit
validator independently checks the package. A receipt binds mission, task,
cycle, result hash and artifact hashes; assistant prose is never authority.
The unchanged result attachment/native-send path sends a final receipt request.
Only its confirmed send permits `/v1/file-loop/result-delivered`; revalidation
and the durable completion gate then produce `VERIFIED_COMPLETE` and `DONE`.
The browser stops polling without issuing an operator STOP. It does not request
another Python work order. Ordinary file turns still require exactly one .py.

Missing, stale or changed evidence fails closed. Interrupted/uncertain delivery
does not complete or blindly resend the work order. Matching delivery receipts
are idempotent; existing tasks without this contract are not retroactively
completed. Start a fresh standard task after installing the updated runtime.

## K07 Delivery, Replay and In-Flight State (2026-09-29)

This section is normative for the file loop after local execution.

1. In-flight record (`AGP_K07_INFLIGHT_RECORD_V1`). After a command file is
   accepted and numbered, and before `run_next.py` starts, the bridge persists
   the step as `RUNNING` in `file-loop-state.json`. An exception during
   execution turns it into `OUTCOME_UNKNOWN`. A `RUNNING` or `OUTCOME_UNKNOWN`
   record found at admission means the bridge lost that outcome; the loop
   enters `BLOCKED` and executes nothing, for the same or any other command
   file (no blind replay). A new mission identity starts a fresh loop state.
2. Delivery state (`AGP_K07_DELIVERY_STATE_V1`). Every executed step records
   `result_sha256` and a delivery state: `PENDING` (result exists, delivery
   unconfirmed), `DELIVERED` (browser confirmed a committed continuation via
   `/v1/file-loop/delivery-ack`, or the handoff `/v1/file-loop/result-delivered`),
   `DELIVERED_IMPLIED` (a newer remote command proves the remote continued) or
   `WITHHELD` (terminal or operator STOP suppressed delivery).
3. Replay. A byte-identical command file is never executed twice. If its
   result is `PENDING`, the replay re-delivers the preserved result files with
   the original continuation, prefixed by an explicit re-delivery notice. If it
   was delivered, the replay is suppressed. A lost delivery acknowledgement is
   never a reason to resend: only a replay of a `PENDING` result re-delivers.
4. Operator control after execution
   (`AGP_K07_POST_EXECUTION_OPERATOR_CONTROL_V1`). The bridge re-reads operator
   control after `run_next.py` returns. `STOP` makes the response terminal,
   sends no continuation and marks the result `WITHHELD`. `PAUSE` returns
   `held: true` without a prompt; the attachment stays unconsumed and the
   resumed loop replays and re-delivers the `PENDING` result. The browser also
   refuses to send a continuation when its run generation changed.
5. Download provenance (`AGP_K07_DOWNLOAD_PROVENANCE_V1`). `/v1/file-loop/download`
   returns `bytes` and `sha256` of the materialized file. The browser rejects a
   size mismatch against Chrome's download item and submits `download_sha256`;
   `/v1/file-loop/command` rejects content that does not match it. Accepted
   browser duplicate names are exactly `<stem>.py`, `<stem> (N).py` and
   `<stem>(N).py`.
6. Turn boundary (`AGP_K07_BASELINE_BEFORE_SEND_V1`). The assistant baseline
   for the next turn is snapshotted before the continuation is sent and applied
   only after the send is committed.
7. Attachment settling (`AGP_K07_ATTACHMENT_STABILITY_V1`). A visible `.py`
   attachment is consumed only after the same attachment identity was observed
   on two consecutive polls with generation idle.
8. Unknown outcome. A timeout or operator stop during `run_next.py` produces
   `OUTCOME_UNKNOWN`; the recovery prompt states that the effect may have been
   applied and that the replacement must inspect current state first.
9. Response identity (`AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1`). While a
   local step number is assigned, the awaited remote response is identified by
   a file card named `<expected step>_*.py` anywhere in the conversation,
   excluding composer, user-turn and dialog copies. This does not depend on
   assistant-turn wrappers. While no response boundary is visible, the browser
   emits a bounded `K07_ASSISTANT_WAIT_OBSERVATION` (every 20 s) with DOM
   selector counts, author headings, visible `.py` labels and stop controls.
10. Observability. Native-transport traces from the service worker are sent to
   the originating tab with `chrome.tabs.sendMessage` and reach the bridge log
   as `K07_NATIVE_TRACE`; `SEND_INDETERMINATE` additionally carries the native
   diagnostics and the nonce evidence.
11. Terminal reply file (`AGP_K07_TERMINAL_REPLY_FILE_V1`, D4). Prose is not
   read: the live ChatGPT DOM has no assistant role nodes, so `AGP_DONE` /
   `AGP_NEEDS_HUMAN` text was never observed and ended in the 180 s wait
   timeout. A terminal remote answer is exactly one file card
   `<expected step>_agp_terminal.json` containing only
   `{"state": "DONE"|"NEEDS_HUMAN", "reason": "<text>"}` (optional `"step"`
   equal to the filename step; unknown keys rejected; at most 16 KiB). It is
   materialized through the same download/provenance path as a work order and
   submitted to `/v1/file-loop/terminal`, which records it in `Download/`
   (bound to the next local step, idempotent for identical bytes) and ends the
   mission. Remote `DONE` is a request: for a task with a local completion
   contract that is not yet verified it becomes `NEEDS_HUMAN`
   (`authority: completion-contract-rejected`); without a contract it is
   `DONE` with `authority: remote-declared`. A `.py` and a terminal file for the
   same step, or two terminal files, fail closed.
12. Reply policy (`AGP_TASK_REPLY_POLICY_V1`, `core/task_reply_policy.py`).
   Task definition, reply policy and transport are separate. The bootstrap of
   every mission offers only a work order or `NEEDS_HUMAN` (a new mission is
   never completed by earlier results in the conversation). Continuations of
   a task with a local completion contract offer only a work order or
   `NEEDS_HUMAN`; only generic missions are offered a remote `DONE`. The
   bridge still converts an unoffered remote `DONE` on a contract task into
   `NEEDS_HUMAN`.
13. Command authority (`AGP_KIT_COMMAND_CATALOG_V1`, `core/kit_command_catalog.py`).
   `docs/reference/agentic-kit-commands.json` is the command authority
   (`.agentic/INITIAL_LLM_PROMPT.md`). The remote side cannot read it, so the
   bridge offers a compact digest (`/v1/status` → `kit_command_digest_path`,
   orchestrator commands first) and the extension attaches it to the mission
   start (fail closed if it cannot be attached). Standing rules, stated in the
   bootstrap and every continuation and enforced on every received work
   order: at least one agentic-kit command; only commands present in the
   manifest; no git push / fetch / pull; no raw git/gh command that has a Kit
   wrapper (`replaces_raw`). Orchestrator commands are preferred (prompt rule;
   not enforceable).
14. Human decision and remote effects (`AGP_HUMAN_DECISION_V1`,
   `AGP_REMOTE_EFFECT_GATE_V1`). Kit commands with an effect outside the
   repository (push, pull/fetch, PR, merge, publish, remote branches; Cockpit
   list `REMOTE_EFFECT_COMMANDS` plus `replaces_raw` naming git push or gh)
   are rejected unless the human approved. A remote `NEEDS_HUMAN` shows its
   question in the tab "Arbeiten"; "Freigeben"/"Ablehnen" (with an optional
   note) is recorded through `/v1/task/decision` (only for the current
   mission in `NEEDS_HUMAN`), and the same task continues in the same
   conversation as a new mission. An approval is a one-shot grant bound to the
   task: it admits exactly one executed work order with remote-effect commands
   and is then consumed (expires after 24 h). Raw git push/fetch/pull remain
   forbidden in every case. The wait timeout names
   the awaited file names and says that a human must check.
15. Green CI before DONE (`AGP_CI_GREEN_COMPLETION_V1`, `core/ci_gate.py`).
   Once a task executed `agentic-kit transfer push-current`, a remote DONE is
   accepted only when the Cockpit itself has run `agentic-kit pr status <pr>
   --json` and the Kit reports `green` for exactly the local HEAD. The DONE
   file names the pull request (`"pr": <number>`, remembered per task). No PR,
   pending CI, a PR head behind HEAD or red CI reject the DONE; the bridge
   answers `{"state": "CONTINUE", "terminal": false, "prompt": ...}` and the
   extension sends that finding (for red CI with the failed-run log excerpt
   from the Kit) as the next turn of the same mission. Evidence of every check:
   `.local/agp-cockpit/ci/<head>.json`. Limits: after 3 red commits or 12
   rejected DONEs, or when the CI cannot be read, the mission ends with
   NEEDS_HUMAN. An approval also carries a repair budget for this loop:
   creating the PR plus 3 repair pushes (`transfer pr-create`,
   `transfer push-current` only) in the same continuation mission; any other
   remote effect needs a new decision. Local Kit runs get the project venv and
   Homebrew on PATH (an app started via `open` has no `gh` otherwise).
16. Kit lifecycle completion (`AGP_CI_LIFECYCLE_COMPLETION_V2`). Neither the
   approval text nor the Cockpit's DONE rejection names a Kit command; they name
   the goal, and the remote side chooses from the command digest, the most
   comprehensive orchestrator first. Every publishing Kit command (push, PR,
   `work finish`, `pr-create-complete`, closeout commands) activates the gate;
   a merging one requires the merged lifecycle: the PR merged and containing
   the local work the run started from, local main equal to origin/main,
   `agentic-kit transfer post-merge-check` PASS (handoff refresh and successor
   package current) and green CI for the origin/main head (`gh run list`: no
   Kit read command exists for a branch head). The repair budget (6 work
   orders) re-runs the approved Kit commands and, after an approved merging
   orchestrator, the publishing and closeout commands of that lifecycle.
   Local run_next timeout: 30 minutes (an orchestrator waits for two CIs).
17. Approval budget and app identity (`AGP_EFFECT_REFUND_V1`,
   `AGP_STALE_APP_GUARD_V1`). A remote-effect work order consumes approval
   budget only when a ref of origin changed (compared with `git ls-remote
   origin` before and after). A packaged app whose build id differs from the
   bundle on disk or from the source tree refuses to start tasks or record
   decisions until it is restarted.
18. Kit command authority (`AGP_KIT_INSTALLATION_AUTHORITY_V1`,
   `AGP_STANDARD_TASK_ORCHESTRATOR_V1`, `AGP_UNKNOWN_EFFECT_ASKS_V1`,
   `AGP_CORRECTABLE_REJECTION_V1`; plan P1). The command digest comes from the
   manifest of the installed Kit (its interpreter is asked for the packaged
   manifest; the repository copy is a fallback). Work orders of standard tasks
   (mission title "Standard · …") must run at least one orchestrator and may
   have remote effects only through orchestrators. An orchestrator the Cockpit
   cannot classify counts as remote effect and asks. A work order that breaks
   these rules is not executed: its step is recorded as `<step>_agp_rejected.json`
   and the remote side receives the violations and the next step number;
   after three rejections in one mission the human decides (NEEDS_HUMAN).
19. Repository state (`AGP_REPO_STATE_V1`, plan P2, `core/repo_state.py`). The
   Cockpit observes the active repository read-only (git, `git ls-remote
   origin`, `gh auth status`, installed Kit, Kit workspace, on main `agentic-kit
   transfer post-merge-check`) when the Standard Tasks tab opens, after each
   task and on request, classifies KEIN_KIT / BEREIT / IN_ARBEIT / LÄUFT /
   STÖRUNG / UNKLAR with one recommendation, shows the Lagebericht and writes
   `.local/agp-cockpit/state/repo-state.json`. Kit-owned volatile paths do not
   count as changes. Without an installed Kit no task starts.
20. Standard Tasks tab (`AGP_STANDARD_TASK_VERBS_V1`, plan P3,
   `core/verbs.py`, `ui/standard_tasks_panel.py`, `ui/tooltip.py`). Tab order
   Standard Tasks → Arbeiten → System. The tab shows the Lage card, the main path
   ① Arbeit beginnen → ② Arbeiten → ③ Abschließen → ④ Chat wechseln, the group
   "Bei Problemen" (Wiederherstellen) and the collapsed group "Weitere" (Repo
   übernehmen, Release, Pflege). Each verb carries an effect badge (liest nur /
   ändert lokal / wirkt auf GitHub / fragt vor Eingriffen / je nach Auftrag)
   and a tooltip (what happens · effect · when available). A button is enabled
   only when the repository state offers the verb, nothing runs and its plan
   slice is implemented; the state's recommendation is marked with ★ and bold.
   Arbeiten switches to the Arbeiten tab; Chat wechseln starts the existing
   chat-switch standard task. Labels, badges and tooltip texts live only in
   `core/verbs.py`.
21. Result projection (`AGP_RESULT_PROJECTION_V1`, `core/result_projection.py`).
   The return bundle and the run_next log stay unchanged in `Download/` and keep
   identifying the result (`result_sha256`). The remote side receives, under the
   same file names from `.local/agp-cockpit/delivery/`, a projection that is a
   pure function of the file bytes: copies of earlier results (`previous_*`) and
   raw output next to parsed `json` become markers; an execution diagnostic drops
   the text already in the attached log and carries the projections of its
   candidate return bundles; long strings keep head and tail, with much more
   room in failure context than in success context; every cut names size and
   SHA-256. A projection is delivered only if it is smaller. Finish run
   1547–1555: 399 KB → 117 KB.
22. Command digest (`AGP_DIGEST_COMPACT_V1`): orchestrators complete; diagnostic
   and primitive commands as a compact table (command, surface, remote_effect,
   use) without options, which the remote side reads with `--help` in a work
   order; written without indentation (81 KB → 33 KB per mission start).
23. Task closure (`AGP_TASK_CLOSE_ON_DONE_V1`). An accepted DONE closes the
   durable task: `VERIFIED_COMPLETE` when the Cockpit verified it (CI gate),
   `REMOTE_DONE` when only the remote side declared it. NEEDS_HUMAN keeps the
   task open for the decision. Terminal tasks accept no further dispatch.
24. Host independence of tests (`AGP_GH_BINARY_V1`): the Cockpit calls `gh`
   through `ci_gate.gh_binary()`, overridable with `AGP_COCKPIT_GH_BINARY`; the
   test suite sets `none`, tests with a fake gh name it explicitly.
25. Extension refresh (`AGP_EXTENSION_AUTO_REFRESH_V2`). The handshake decides:
   an extension reporting a build other than the staged one gets one refresh
   request per target build (`target_build_id` in `refresh_request.json`; no
   reload loop if the browser keeps the old build). The idle start-request poll
   (every second) names the staged build, so an outdated extension asks at once
   instead of after the throttled handshake; the reloaded service worker reloads
   the recorded ChatGPT tabs (`onInstalled`). Startup no longer aborts when the
   active tab is not ChatGPT.
26. Download hygiene (`AGP_DOWNLOAD_HYGIENE_V1`). After the bridge accepted and
   persisted a work order or terminal reply in `Download/`, the extension removes
   exactly that browser download item (id and name checked) from `~/Downloads`.
   Rejected work orders keep their browser copy. Work orders run with
   `TMPDIR`/`TEMP`/`TMP` = `.local/agp-cockpit/tmp/<step>`.
27. Maintenance (`AGP_MAINTENANCE_CLEANUP_V1`, System tab „Aufräumen …“):
   preview first, deletion only after OK and never while a task runs. Rules:
   `Download/<step>_*` outside the newest 50 steps and older than 30 days
   (`run_next.py` never), projections older than 30 days, work-order tmp older
   than one day, CI evidence older than 30 days beyond the newest 20, and the
   Kit's `/tmp` logs via `agentic-kit artifact-gc --tmp-logs` (dry run in the
   preview, `--execute` on OK). Only files a fresh plan still lists are deleted.
28. Kit findings view (`AGP_KIT_FINDINGS_VIEW_V1`, System tab „Kit-Befunde …“):
   read-only window over `docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json`
   with filter, details, Cockpit mitigations and the installed Kit version; the
   effective status compares `fixed_in` with the installed Kit.
29. Command digest once per chat (`AGP_DIGEST_ONCE_PER_CHAT_V1`): attached again
   only for a new conversation, a changed manifest SHA or after five missions;
   otherwise the mission start names the earlier attachment. Local work-order
   validation is unaffected. The Bridge panel shows the mission's remote turns
   (same count as the Cockpit) and no duplicate mission line.
30. Kit findings sync (`AGP_KIT_FINDINGS_SYNC_V1`): „Mit Kit-Repo abgleichen“ in
   the Kit findings window clones the public Kit repository read-only into
   `.local/agp-cockpit/kit/kit-repo`, reads its `docs/reports/*.json` and writes
   `.local/agp-cockpit/kit/kit-findings-status.json` (Kit commit, latest Kit
   statement per KIT-GF id, CLOSED/PARTIAL/OPEN, `fixed_in` from CHANGELOG dates).
   The tracked ledger carries a dated snapshot (`kit_repo_status`); neither
   changes the ledger `status` — VERIFIED_FIXED needs evidence from this
   workspace.
31. Release policy (`AGP_RELEASE_POLICY_V1`, `docs/planning/release_policy.json`,
   `docs/planning/RELEASE_POLICY.md`): agp-Cockpit is never published. Work
   orders running `agentic-kit release-publish`, `agentic-kit
   post-release-doi-closeout`, `gh release create|upload|edit|delete` or
   contacting Zenodo/PyPI upload hosts are rejected as correctable violations.
32. Window (`AGP_SCROLLABLE_TABS_V1`): the window opens at 90 % of the screen
   (1020×600 … 1500×1100); every tab scrolls when its content does not fit.
33. A recommended verb whose button belongs to a later plan slice is named as
   the next step with a pointer to the „Arbeiten“ tab instead of „Empfohlen“
   next to a disabled button.
34. Orphaned content script (`AGP_ORPHANED_CONTENT_SCRIPT_GUARD_V1`): after an
   extension reload the old content script of an open tab detects the lost
   extension context (`chrome.runtime.id`), stops its timers, removes its
   overlay and never calls the bridge again (live 2026-10-02: „Uncaught (in
   promise) Error: Extension context invalidated“ at the old `content.js`). The
   first reload after installing this build still comes from an older script
   without the guard.
35. Work-order contract for a fresh chat (`AGP_WORK_ORDER_SHAPE_RULE_V1`,
   `AGP_INGRESS_SAFETY_ONLY_V1`): `WORK_ORDER_KIT_RULE` states the structural
   contract (main(), `__main__` guard, STEP, `--self-test` without side
   effects, one `Download/<STEP>_<topic>_return_bundle.json`) verbatim in the
   mission start, every continuation and every correction prompt. Download
   ingress checks only name, location, size and UTF-8; every semantic check,
   syntax included, happens at `/v1/file-loop/command` and is answered with a
   bounded correction (live 2026-10-02, step 1568: a fresh chat omitted
   `--self-test`, ingress rejected it fail-fast and the mission stopped).
36. Merged-branch guard (`AGP_MERGED_BRANCH_GUARD_V1`): a work order with
   `agentic-kit transfer pr-create*` whose head branch (local, else
   `origin/<branch>`) has every path it changed since the merge base identical
   in `origin/<base>` is rejected as a correctable violation. Not blocked: a
   branch without own commits, the current branch with uncommitted changes,
   unknown refs (live 2026-10-02: step 1574 re-ran `pr-create-complete` after
   1573 had merged PR #147; the Kit opened the empty PR #149).
37. Repository facts (`AGP_REPOSITORY_FACTS_V1`): every continuation after a
   local step carries one line the Cockpit read itself — current branch and
   HEAD, `origin/main`, main = origin/main, clean worktree, and for each pr-create
   head of the completed work order (and a non-main current branch) whether it
   adds nothing to `origin/main`; with `gh` available also its pull requests.
38. Kit verdict rule (`AGP_KIT_VERDICT_RULE_V1`, part of `WORK_ORDER_KIT_RULE`):
   work orders record `result_status`, `final_signal`, `failed_step` and
   `next_action` of every `--json` Kit command and never re-run a remote-effect
   command to check a result.
39. Standard-task framework (`AGP_STANDARD_TASK_FRAMEWORK_V1`, plan P5,
   `core/standard_tasks.py`): each task declares goal text without Kit command
   names, inputs, a local precheck, the remote-effect scope its start click
   approves, whether DONE needs the merged CI lifecycle, a confirmation text,
   R6 behaviour and a follow-up verb. One task at a time (R5): a start is
   refused while a mission runs.
40. Start-click approval (`AGP_START_CLICK_APPROVAL_V1`, R4): before the first
   mission the Cockpit records a pre-approval limited to the task's scope; it is
   claimed by that mission, restricts every work order (first and repair) to
   the scope, keeps the repair budget and logs every consumption with step and
   commands; the Standard Tasks tab shows these effects. Other remote effects
   still ask.
41. Local verifiers (`AGP_STANDARD_VERIFIER_V1`): a remote DONE of a task with
   `completion_contract.kind = agp-standard-verifier-v1` is accepted only when
   the named verifier passes (`work-started`: requested branch checked out,
   contains origin/main, clean; `recovered`: Lagebericht BEREIT or IN_ARBEIT);
   otherwise the task continues with the finding, after three failures
   NEEDS_HUMAN. Abschließen arms the CI gate with merge expected at start.
42. Abschließen (P6): never from main, only with own changes, explicit dialog,
   no force option on publishing Kit commands (`AGP_NO_FORCE_V1`); DONE only
   ci-verified; afterwards „Chat wechseln“ is recommended; an interrupted run
   unlocks and recommends „Wiederherstellen“ (R6). Arbeit beginnen (P7): kind
   and name dialog, branch must not exist, clean worktree; scope limited to the
   Kit's sync and work-start routes. Wiederherstellen: diagnosis first,
   destructive steps only after NEEDS_HUMAN, no pre-approval.
43. Tool lists are not invocations (`AGP_TOOL_LIST_NOT_INVOCATION_V1`): a list
   made only of program names (e.g. `"allowed_tools": ["agentic-kit", "git"]`)
   no longer reads as the command `agentic-kit git` (live 1569/1570/1583).
44. Send readiness after an upload (`AGP_SEND_READY_AFTER_UPLOAD_V1`): the
   native transport waits up to 30 s (was 3 s) for an actionable send control;
   a re-attached command digest that is still uploading keeps it disabled
   (live 2026-10-02: „Arbeit beginnen“ stopped with SEND_BUTTON_NOT_READY
   right after KIT_COMMAND_DIGEST_ATTACHED). After a finished task its
   follow-up verb is the only recommendation (star, hint, Lage); a verified
   DONE shows the Cockpit's verdict (CI gate or local verifier).
   The command digest counts as present in the chat only after the message
   carrying it was sent (`AGP_DIGEST_REMEMBERED_AFTER_SEND_V1`).

Open, not yet proven live: whether ChatGPT's current DOM exposes the nonce line
in the committed user turn (expected, it is plain text), whether result files
are fully uploaded before the continuation is committed, and whether the
generation-activity selectors still match the current ChatGPT DOM. The next
real E2E must confirm or refute each from `K07_NATIVE_TRACE`,
`K07_RESULT_DELIVERED` and `SEND_INDETERMINATE` evidence.
