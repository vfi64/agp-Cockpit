# Protocol Change and Failure Log
Durable engineering memory; normative semantics remain in planning protocol authorities.

## 2026-09-23 — verified handoff completion and service-limit boundary

Observed failure: local step `1468` generated a fresh successor package, returned
`PASS`, and incremented the browser turn to `1/40`, but the browser then demanded
step `1469`. That mission used a durable task created before the handoff completion
contract was added, so its persisted `completion_contract` was empty. A subsequent
fresh task has the required `verified-successor-handoff-v1` contract, but ChatGPT's
visible account-limit notice was then mistaken for a new assistant work response
and failed as a missing Python attachment at `0/40`.

Repair: fresh Chat-switch tasks carry the explicit completion contract and finish
only after local Kit validation plus confirmed result delivery. The content script
now recognizes bounded German and English ChatGPT usage-limit notices after checking
for an authoritative Python attachment and before entering the K07 attachment timer.
It records `REMOTE_SERVICE_LIMIT` and stops the mission without reporting a protocol
or file-transfer error. All other FULL_AUTO assistant responses still require exactly
one `.py` attachment; visible JSON or prose remains non-authoritative.

Verification: the full Python suite, focused JavaScript behavior tests, Ruff, and
diff checks pass. Extension identity advances to `0.3.11` /
`service-limit-boundary-20260923`. A final live run requires available ChatGPT usage
and must show either verified `DONE` after the first successful handoff step or
`REMOTE_SERVICE_LIMIT` at `0/40`, never a fabricated next-step attachment error.

## 2026-09-20 — Chrome `Uncaught (in promise)` timeout hardening

Observed failure: Chrome displayed `Uncaught (in promise) Error:
K07_ASSISTANT_RESPONSE_TIMEOUT after 180s` for `content.js:1710`. Source and
staged-extension inspection showed that the current timeout path no longer
throws that error; the message was a retained Chrome extension error entry from
an earlier build. The remaining structural risk was real: both file-loop start
paths passed the asynchronous `tick` function directly to `setInterval`, so an
exception outside its inner recovery block, or a rejected diagnostic call in
the recovery path, could still become an unhandled browser promise.

Repair: the whole tick path, including timeout and operator polling, is now
inside one recovery boundary. `scheduleTick()` owns the interval and observes
every returned promise. Unexpected escapes become `TICK_UNHANDLED_ERROR` with
the error count and are rendered/logged instead of becoming an unhandled
rejection. Stop-event reporting is best-effort and cannot turn a completed
stop into a second rejected promise. The extension identity was advanced to
`0.3.4` with build `tick-scheduler-hardening-20260920`; the Bridge uses the
same build ID.

Verification: JavaScript syntax, focused extension/file-ingress regression
tests, and the macOS app build passed. The fresh app staged the exact new
version/build and source hash. Chrome's retained error list was cleared, the
extension was reloaded, and the ChatGPT tab showed `v0.3.4` and
`CONNECTED IDLE` without a new extension error. A real mission run remains a
separate acceptance test; its evidence must include the fresh handshake, one
attachment-ingress event chain, one `run_next.py` execution, one bounded return
bundle, and a non-zero turn count.

## 2026-09-20 — `tick` generation scope regression

Observed in the first real acceptance run after the preceding repair: the
remote model rendered command files `1453` and `1454`, but no file reached the
local `Download/` directory. The Cockpit showed `TICK_UNHANDLED_ERROR` with
`ReferenceError: runGeneration is not defined` and remained at `0 / 40`.

Root cause: `tick()` declared `runGeneration` only after the asynchronous
operator-poll calls. Its shared `catch` also referenced that name. A rejection
from either poll therefore entered the catch while the lexical binding was
still uninitialized, producing a second ReferenceError and bypassing file
ingress. This was introduced by the previous whole-tick recovery refactor.

Repair: capture `const runGeneration = STATE.runGeneration` immediately after
entering the tick recovery boundary, before any await. The extension identity
is advanced to `0.3.5` with build `tick-scope-hardening-20260920`; the Bridge
uses the same build ID. The regression test asserts the declaration precedes
operator polling. The required acceptance evidence remains: one fresh `.py`
attachment observed, local Download ingress, `run_next.py` execution, one
bounded return bundle, updated handoff files, and a non-zero turn count.

## 2026-09-20 — v0.3.5 runtime identity verified

The first rebuild attempt left the packaged app and staged extension at the
previous `0.3.4`/`tick-scheduler-hardening-20260920` identity even though the
source tree already contained `0.3.5`. Chrome therefore continued running the
old extension after a reload. This was a deployment-verification failure, not
another protocol diagnosis.

Repair and verification: rebuild the PyInstaller app from the current source,
stage from the freshly built package, restart the app, reload the unpacked
extension, and reload the ChatGPT tab. The authoritative stage record now
reports extension `0.3.5`, build `tick-scope-hardening-20260920`, the expected
repository root, `Download/`, and `Download/run_next.py`; the live Cockpit
overlay reports `v0.3.5`, `CONNECTED`, and neutral `IDLE · 0/40`.

The full Python suite, Ruff, documentation gate, project doctor, JavaScript
syntax check, and diff check passed. A new real mission is still required to
prove the complete remote-file-to-local-runner chain; this version must be
identified by `v0.3.5` before that test begins.

## 2026-09-20 — remote step authority and tick catch scope

Observed in the next real acceptance run: the remote conversation rendered
`1456` and `1457`, while the local Bridge materialized the first file as
`1443`. The Bridge log proves that the file was received and passed to
`run_next.py`, but the local runner rejected it during semantic preflight:
the file had no `__main__` execution guard and no `--self-test` contract. No
Kit command ran and no fresh handoff package could therefore be produced.

Two independent defects caused the misleading result. First,
`accept_command_file()` previously treated the remote numeric prefix as
authoritative. That made retries with the same remote name replay or reject
instead of advancing the local work-order counter. The local `Download/`
inventory plus persisted step is now authoritative: every newly admitted
command gets the next local number, while the original remote filename is
stored only as correlation metadata. Continuations state the expected next
local number explicitly. This preserves idempotent replay by content while
ensuring a new remote response can never keep the local counter at its old
number.

Second, the v0.3.5 repair still declared `runGeneration` inside `try` while
the shared `catch` used it from a sibling lexical scope. That caused the
observed `ReferenceError: runGeneration is not defined` after a failed ingress
poll, even though the original ingress error was already available. The
generation fence is now captured before `try` begins.

Identity for the next test is Extension `0.3.6` and Bridge build
`remote-step-authority-20260920`. The required evidence is now unambiguous:
the local numeric step must appear in the local `Download/` filename, runner
argv, return bundle, and `K07_RESULT_BUNDLE_CREATED` log event; the remote
filename is recorded separately as a correlation hint. A valid command must
also pass preflight before a handoff package can be expected.

Deployment verification: after explicitly quitting the old desktop process and
starting the rebuilt app, the fresh Bridge log reports build
`remote-step-authority-20260920` with extension version `0.3.6` and matching
extension build ID. The runtime is `IDLE`; the previous `BLOCKED` mission was
not revived across the restart. This proves artifact identity and restart
separation, but not yet a successful new remote mission.

## 2026-09-20 — file-card ingress, version identity, and diagnostic sequence

Observed failure: ChatGPT visibly rendered a new `1453_*.py` attachment, but
the Cockpit remained at `0 / 40`; no command file reached `Download/`, no
`run_next.py` execution occurred, and the handoff package remained unchanged.
The extension then surfaced an uncaught `K07_ASSISTANT_RESPONSE_TIMEOUT` after
180 seconds. The first proven divergence was the browser DOM boundary: the
attachment was rendered as an ordinary button containing the filename, while
the detector required an `.py` link or a button with an `.py` aria label.

Repair: ordinary buttons and role buttons are now inspected for visible `.py`
filenames; a single visible new file card is an authoritative K07 response
boundary and immediately enters file ingress. The complete assistant baseline
also records attachment names, preventing an old file card in a long-lived
conversation from being replayed. Ingress now emits explicit requested,
fetched, accepted, and failed events. Timeout is terminal and structured, not
an uncaught browser promise rejection. Every Bridge event carries UTC timing,
application version, Bridge build, and protocol version; browser events carry
the matching extension version/build and conversation URL.

Identity for this build: Cockpit `0.1.0.dev0`, Bridge build
`file-loop-ingress-observability-20260920`, extension `0.3.3`, extension build
`native-file-card-ingress-20260920`. The sequence and evidence contract are
documented in `docs/engineering/COMMUNICATION_SEQUENCE.md`; authoritative
runtime locations remain documented in `docs/engineering/RUNTIME_PATH_AUTHORITY.md`.

Verification: full Python suite passed, Ruff passed, JavaScript syntax passed,
`agentic-kit check-docs` passed, `agentic-kit doctor` reported overall PASS,
the macOS app rebuilt successfully, and the staged extension was verified at
the expected version/build. A real end-to-end file-loop run remains the next
manual acceptance test; do not call the runtime behavior proven until the log
contains `K07_ASSISTANT_ATTACHMENT_OBSERVED`, `K07_COMMAND_ACCEPTED`,
`K07_RESULT_BUNDLE_CREATED`, `K07_FILE_INGRESS_ACCEPTED`, and
`CONTINUATION_SENT` for one fresh mission.

## 2026-09-16 Generation 51 — title/start path
Successful repair; title guard allowed bootstrap preparation. Learning: acceptance alone is insufficient; trace the next authoritative transition.

## 2026-09-16 Generation 51 — native composer
Failure `MISSION_BOOTSTRAP_SEND_FAILED: native transport composer not found`; root cause was divergent locator contract. Repair aligned native locator with established textbox fallback; focused tests and staging parity passed.

## 2026-09-16 attempt 1260
Informative failure: handwritten unauthenticated bridge HTTP received 403. Learning: use canonical authenticated clients.

## 2026-09-16 attempt 1262
Informative failure: Download execution context could not import repository package. Learning: bootstrap repo src/use canonical environment.

## 2026-09-16 Generation 52 — native send
Success: native submit dispatched/accepted, user turn committed, native send accepted, MISSION_BOOTSTRAP_SENT. Real-path native composer repair proven.

## 2026-09-16 Generation 52 — unresolved authorization divergence
Assistant observed → TURN_SUBMIT_STARTED_CLIENT → TICK_ERROR `ACTION_NOT_AUTHORIZED_BY_LOCAL_TASK_CONTRACT`; READY, turn 0, step 0. Next work is protocol-first authorization reconstruction, not another blind E2E retry.

## 2026-09-18 Standard Task autostart — title-family divergence
Informative failure: the Standard Tasks button persisted a valid explicit start
request and created a `LIVE` + `FULL_AUTO` mission, but the browser remained in
`READY` because the task-first autostart guard accepted only `Task ·` and `E2E ·`
titles while the existing Standard Tasks panel emits `Standard · <label>`.
The first divergence was the presentation-title eligibility guard after start
request identity validation; mission identity, generation, and authority were
otherwise valid. Repair: include the established `Standard ·` title family in
the same task-first allowlist and preserve the guard for unrelated expert
missions. Real browser evidence: manual overlay start completed the first
file-transfer turn and produced a canonical return bundle before this repair.

## 2026-09-18 Standard Task — stale assistant baseline and attachment ingress
Informative failure: the explicit start request was accepted and native
bootstrap submission reached ChatGPT, but a long-lived conversation contained
older assistant replies and file buttons. The observer used only the last
assistant message id as its baseline, so the current turn could be confused
with historical conversation DOM. The run then failed closed with
`K07_FILE_TRANSFER_ATTACHMENT_REQUIRED` after observing no current `.py`
attachment. Repair: capture the complete pre-turn assistant message-id set,
exclude that set from text and attachment selection, and accept bounded UI
label variants only when the filename still contains a `.py` suffix. The
file-loop boundary remains strict: exactly one current `.py` attachment is
materialized into `Download/`, executed only through `run_next.py`, and
returned as one canonical JSON bundle. No prose or JSON fallback was added.

## 2026-09-18 K07 — result evidence fallback and closed-loop contract
Informative failure: a remote command file reached `Download/` and `run_next.py` returned code 0, but the command produced no canonical return bundle. The bridge synthesized a failed bundle, but only that bundle was attached; `Download/__run_next_output.txt` was not part of the remote evidence package. Root cause was an incomplete result-delivery contract, not a local execution success. Repair: carry the runner-log path and digest through the file-loop result, attach the return bundle and runner log together, and preserve replay idempotency. The Cockpit remains fail-closed: malformed, incomplete, or contradictory result evidence cannot become terminal success.
## 2026-09-18 K07 — JSON-only command file was not execution
Informative failure: `1415_037_chat_switch_complete_work_order.py` passed compile and self-test and exited with code 0, but its real run only printed a JSON object describing `agentic-kit transfer chat-switch-complete --json`. It did not invoke the Kit command and did not create a handoff result bundle itself. The previous runner converted that printed declaration into a synthetic success bundle. Repair: stdout declarations are now diagnostic only; a command file must execute the authorized local operation and create its own canonical bundle. JSON-only output becomes a failed step with the runner log attached, and the Standard Task prompt now states this executable-file contract explicitly.

Informative failure: `1417_038_chat_switch_execute_validate_and_bundle.py` was accepted as an attachment, but `run_next.py` stopped at `py_compile` with an `IndentationError` on line 78. The real run and Kit command were therefore never reached. The bridge already preserved a failed return bundle and `__run_next_output.txt`, but the browser extension discarded the bridge's specific recovery prompt and sent only a generic continuation sentence. Repair: propagate the server-provided prompt through the content/background extension boundary; failed evidence now explicitly requires diagnosis and one newly numbered corrected command file, while remaining fail-closed and bounded by the mission/step limits.

## 2026-09-18 K07 — runner contract and environment hardening

Informative failures: `1419_042_chat_switch_standard_task.py` passed compile,
self-test, and the real run with exit code 0 but created no return bundle;
`1420_042_chat_switch_standard_task.py` was truncated and failed with an
`IndentationError` before the real run. A further audit found that a generated
bundle can exist while containing invalid JSON, as in an older `1387` work
order that wrote a literal `\\n` suffix and appended an acknowledgement after
the JSON object.

The first two failures are distinct: the former is an execution-contract
failure, the latter an attachment-integrity failure. The local runner now
prefers the repository `.venv/bin/python` while preserving the unchanged human
entry point, writes non-overwriting step-scoped log snapshots, and refuses to
report `RUN_NEXT PASS` unless the real run creates exactly one parseable JSON
object. The versioned Cockpit executor independently converts invalid bundles
into one failed diagnostic bundle naming the raw candidate, preserving the
runner log and recovery evidence. Learning: compile/self-test success does not
prove real execution, exit code 0 does not prove result evidence, and a file
existence check does not prove JSON validity.

## 2026-09-18 K07 — owned recovery draft was treated as foreign

Informative failure: step `1426` was automatically executed and correctly
produced a failed bundle plus `__run_next_output.txt` after the attached command
file failed at `py_compile` with an `IndentationError`. Result delivery then
stopped because the browser composer contained the Cockpit-generated recovery
prompt, while the native transport recognized only bootstrap and normal-result
drafts as Cockpit-owned. The recovery prompt was therefore incorrectly treated
as foreign composer content. Repair: recognize the stable Cockpit recovery
prefix as owned while retaining the fail-closed refusal for unrelated non-empty
composer text. The local-run failure was not an autostart failure; it was an
attachment-integrity failure followed by a recovery-transport classification
failure.

## 2026-09-19 K07 — syntactically valid truncated command file

Informative failure: command file `1438` passed `py_compile`, accepted the
unknown `--self-test` argument by simply ignoring it, and ended its real run
with exit code 0 without a main guard, Kit invocation, or return-bundle writer.
`run_next.py` detected the missing result only after the real-run phase. The
first proven divergence was therefore semantic command-file completeness, not
local Python startup or Hermes availability. Repair: add deterministic
semantic work-order preflight, attach command-file size/line/hash and
interpreter/CWD/argv evidence, and block the file loop after three consecutive
same-signature failures without proven progress. Transport hashes remain
limited to transport-integrity evidence; they cannot prove that the remote
model originally generated a complete file.

## 2026-09-19 K07 - rendered user-turn false negative

Informative failure: the Standard Task bootstrap was visibly present in the
ChatGPT conversation and ChatGPT produced command-file replies, but the bridge
classified the send as `USER_TURN_INDETERMINATE`, left the mission at `0/40`,
and never reached file ingress. The first proven divergence was browser/native
user-turn reconciliation. Root cause: the raw prompt contains Markdown
delimiters and escaped punctuation, while the observable ChatGPT user bubble is
the rendered projection; exact raw-text comparison therefore rejected a real
turn. A second integration hazard was that the native snapshot is serialized
into CDP with `toString()`, so it must not depend on outer JavaScript bindings.

Repair: add one deterministic rendered-user-turn projection shared by the
content observer and native commit comparison. Keep raw normalization for
composer/model verification unchanged. Keep message identity and the
pre-existing-message exclusion unchanged; rendered normalization is not a
replacement for persistent-message evidence. Add regression coverage for
Markdown rendering and a source gate that enforces debugger-safe
self-containment. Update the extension build identifier so the staged/runtime
extension cannot silently keep the old protocol code.

Required acceptance trace: extension handshake with the new build identifier,
`NATIVE_USER_TURN_COMMITTED`, `NATIVE_SEND_ACCEPTED`,
`MISSION_BOOTSTRAP_SENT`, current `.py` attachment ingress into the repository
`Download/` directory, and a non-zero turn count. A UI attachment alone is not
acceptance evidence.

Verification and restore boundary: the full Python suite passed with local
loopback access, the focused native-commit Playwright suite passed, Ruff,
`check-docs`, `doctor`, and `git diff --check` passed. The application was
rebuilt and restarted; the staged extension now reports
`native-commit-rendered-turn-20260919`. Before protocol changes, preserve both
the committed restore branch `backup-pre-rendered-turn-20260919` and the exact
uncommitted patch snapshot
`.local/restore-checkpoints/pre-rendered-turn-20260919.patch`. A restore must
pair source and staged application build; never diagnose a live run against an
older staged extension. The current Bridge operator state was left at `STOP`
after verification so no stale mission can restart implicitly.

## 2026-09-19 — runtime identity and path/version pairing

The previous readiness gate compared only extension version `0.3.2`. That
allowed an older staged or running extension with the same version to appear
ready, which explains why source fixes repeatedly failed to change live
behavior. The source, built app, staged extension, browser handshake, Bridge
runtime, and `Download/run_next.py` were not one verifiable identity.

Repair: the extension now loads `build_identity.js` as a normal content script;
the handshake reads that value from the running extension, and startup requires
both version and build identity to match the staged extension. Staging records the identity,
source/staged paths, repository root, `Download/`, and `Download/run_next.py`
in `.agp-stage.json`. A mismatch is a readiness failure and must not enter a
mission. This turns the former diagnostic assumption into a deterministic gate
and preserves the exact restore boundary.

The first post-build startup confirmed the value of the gate: the new app
staged the correct identity and paths, but Chrome had not yet emitted a fresh
handshake. The runtime therefore remained `CONNECTING` and a task start is now
rejected with the concrete identity reasons instead of creating a no-op
mission. This is the intended fail-closed behavior; a successful test now
requires a fresh browser-extension handshake before the first Start action.

## 2026-09-19 - shared guard, fresh handshake, and conversation binding

The file-loop path previously bypassed the existing `AutomationGuard`: its
turn budget, duplicate-response detector, prompt-repeat detector, and error
budget were active only in the browser-turn path. This explained both the
visible `75/40` runaway and the file-loop's stale `0/40` display. It also meant
that the Stop path and the file-loop path had no common terminal state.

Repair: the file loop now uses the same mission-scoped guard instance as the
browser path. It checks every incoming command before execution, records the
assistant artifact and continuation prompt, records success/error evidence,
and persists `BLOCKED` when a bound is exhausted. `BLOCKED` is now a genuine
terminal mission state and is never silently converted into another retry.

The runtime identity gate also now checks handshake age and binds the fresh
handshake to the concrete `/c/<conversation-id>` mission URL. Missing source
files produce only their primary diagnostic; malformed or stale handshake
timestamps fail closed without crashing. The mission URL is captured from the
active allowed ChatGPT tab and persisted through the HTTP and extension paths.

Regression coverage proves the shared turn budget, repeated assistant
response stop, terminal `BLOCKED` persistence, stale-handshake rejection,
foreign-conversation rejection, malformed timestamp handling, and the
existing missing-file diagnostics. This is a prevention boundary: source,
staged extension, active tab, mission, and local file loop must now identify
the same runtime before work begins.

## 2026-09-19 - runner timeout and effective stop authority

The next audit found that `subprocess.run(..., timeout=...)` raised
`TimeoutExpired` outside the file-loop contract, so no canonical diagnostic
was returned. It also found that the operator stop persisted `STOPPED` without
owning the running `run_next` process. The resulting state could claim that a
mutation had ended while a descendant Kit process was still running.

Repair: `RunNextProcessController` is now the single local execution owner for
the Bridge. It starts `run_next.py` in a dedicated process group, tracks the
active PID, kills the complete group on timeout or operator stop, and always
materializes a diagnostic return artifact with `status: unknown`,
`outcome: OUTCOME_UNKNOWN`, termination cause, candidate bundles, stdout,
stderr, and the runner log path. The Bridge `/v1/file-loop/control` STOP path
invokes this controller before persisting mission `STOPPED`; Bridge shutdown
uses the same path. The old lifecycle stop remains only a generation/admission
fence, and `BridgeRuntime.stop()` remains state persistence rather than a
second process-kill implementation.

Regression coverage executes a real timeout and an asynchronous operator stop,
checks that the runner process group is gone, verifies that no late return
bundle appears, and requires the unknown-outcome diagnostic. This closes the
status-versus-effect gap without treating uncertain local execution as a
successful or safely replayable step.

The K07 admission boundary is fail-closed as well: while durable operator
control is `PAUSE` or `STOP`, `/v1/file-loop/command` rejects a new command
before it is written or executed. The stop contract is scoped explicitly:
`OperatorControlStore` controls admission, `RunNextProcessController` controls
the live runner effect, and `BridgeRuntime` records mission state. Unrelated
task, terminal, and service cancellation APIs remain separate scopes rather than
competing K07 stop authorities.

## 2026-09-19 - unbounded evidence output and runner-path hardening

The first real post-repair run exposed a separate contract failure: work order
1354 recursively searched `Download/`, including historical return bundles, and
embedded the complete search output in `commands[5].stdout`. This produced a
74 MB evidence text file and an 87 MB JSON return bundle. The runner accepted
both because it had no output or artifact-size gate.

Repair: the canonical root `Download/run_next.py` is now versioned; the `alt/`
copy is explicitly non-authoritative. Runner output is bounded to 256 KiB,
including the combined log and captured process streams. New return bundles are
limited to 2,000,000 bytes. Oversized bundles remain available locally for
diagnosis but are fail-closed and replaced by a bounded diagnostic bundle.
Missing or unstartable `Download/run_next.py` also produces a diagnostic bundle
instead of an uncaught bridge failure.

Regression coverage executes a real runner with 600 KiB of child output,
verifies bounded stdout and log files, rejects a 2.1 MB result bundle, and
checks the missing-runner path. This closes the evidence-amplification loop;
the remote model receives a bounded failure explanation rather than historical
repository contents.

## 2026-09-19 - stale mission pointer after desktop restart

The first manual restart acceptance test did not reach the required neutral
startup state. The browser overlay still showed `STOPPED`, `0/40`, and the old
conversation still displayed the previous `062_chat_switch_standard_task.py`.
The Bridge had stopped the old mission, but left it in `current.json`, so a
reconnected content script continued to receive the terminal mission as if it
were the current task.

Repair: desktop startup now preserves the old mission's per-mission evidence,
then clears only the current-mission pointer and exposes `IDLE` until a new
standard task explicitly creates a mission. This prevents a stale `STOPPED`,
`READY`, or `FULL_AUTO` mission from becoming the next implicit start target.

Regression coverage verifies both non-terminal and terminal persisted missions,
the HTTP status after a Bridge restart, and preservation of the historical
mission evidence file. The required manual acceptance state is now: empty
composer, no new user turn, no automatic task, and `IDLE`/`0/40` until the
operator explicitly selects a standard task.

## 2026-09-19 - HTTP 400 caused by split handshake authority

The first post-restart standard-task test created a new `READY` mission but
returned `HTTP Error 400: Bad Request` before the first remote turn. The Bridge
log showed repeated empty start-request polls and no downloaded work order.
The failure was not a ChatGPT conversation error: the desktop app passed the
production Bridge root under `~/Library/Application Support/AGP Cockpit/bridge/`
to the server, while the `EXTENSION_HANDSHAKE` handler still wrote
`extension.json` to the repository-local `.local/agp-cockpit/bridge/` path.
The start-request gate correctly read the production root and therefore
reported a missing runtime identity.

Repair: the handshake writer now uses the server's injected `runtime_root`, and
the app bootstrap passes that same root to every handshake reader. The
repository-local `.local` tree remains reserved for repository evidence and
browser-refresh coordination; it is no longer a second source of truth for
production Bridge identity. Regression tests use a deliberately separate
runtime root and execute the full handshake -> mission -> start-request path,
which must return `200` and queue the request.

## 2026-09-20 - truncated command files must terminate the loop

The next manual run produced numbered files `1439` and `1440`, but both were
truncated Python sources. `Download/__run_next_output.txt` reported
`RUN_NEXT_PRECHECK_FAILED` with an `IndentationError`/unclosed block, and the
return bundles contained no runner return code, command, or Kit result. The
canonical handoff package therefore correctly remained at its previous
timestamp: the authorized Kit command was never reached. Historical files in
`Download/alt/` show the same repeated truncation pattern, so this was not a
Python-environment or repository-path failure.

The file loop nevertheless treated each newly numbered malformed source as a
fresh recovery opportunity. Because the filename and generated diagnostic
changed, the same failure did not reach the existing same-signature threshold;
the remote exchange continued until the operator stopped it. The HTTP handler
also finalized a blocked loop only when no result artifact existed, leaving a
terminal error bundle without an equally terminal mission state.

Repair: classify semantic/syntax/indentation preflight rejection explicitly,
allow one bounded correction response, and persist `BLOCKED` on the second
preflight failure without producing a third remote turn. Preserve the failed
bundle and immutable runner log as evidence. Finalize the Bridge mission as
`BLOCKED` even when the diagnostic bundle exists. Regression tests cover the
two-failure terminal boundary and prove that `run_next.py` is not started for
a truncated source. This preserves the existing numbered `Download/` and
`run_next.py` authority while making the failure deterministic and stoppable.

## 2026-09-20 - unified process-stop authority

The stop review correctly identified an architectural ambiguity: the plain
`BridgeRuntime.stop()` method had no process reference. The active HTTP K07
path already used `RunNextProcessController.stop()`, but the state API did not
make that relationship explicit, so a future caller could persist `STOPPED`
without terminating a running command.

Repair: the production `CockpitBridgeServer` binds the runtime to its single
`RunNextProcessController`. `BridgeRuntime.stop()` now invokes that bound
process authority before persisting the terminal mission state and exposes the
bounded stop result for the HTTP response. Server shutdown and the operator
STOP endpoint use the same orchestration. A standalone `BridgeRuntime` remains
state-only by design for isolated persistence tests; it cannot be treated as a
K07 executor. Regression coverage proves callback-before-state ordering and
retains the real process-group stop test. The remaining task, terminal, and
service cancellation APIs are documented as separate scopes rather than
competing K07 stop implementations.
# 2026-09-20 - File-card ingress and versioned observability

- The live browser evidence showed a visible `1453_*.py` attachment while the
  extension remained at `0/40` and eventually raised an uncaught response
  timeout. The DOM exposed the file card as ordinary buttons containing the
  filename, while the detector inspected only links and labelled buttons.
- The detector now accepts the observed ChatGPT file-card shape and treats one
  unique `.py` card as the terminal remote-response evidence for K07.
- Every attachment ingress now logs observation, materialization, bridge
  acceptance, cycle identity, and version/build metadata. The response timeout
  is terminalized and logged instead of escaping as an unhandled promise.
- Desktop, bridge, and extension identities are visible and machine-readable;
  the exact sequence is documented in `docs/engineering/COMMUNICATION_SEQUENCE.md`.

# 2026-09-20 - authoritative retry after legacy-numbered preflight failure

The next live run exposed a second numbering boundary. The extension delivered
`1457_chat_switch_standard_task.py`, but the local evidence contained
`1444_chat_switch_standard_task.py`. The file content hash matched the earlier
legacy-numbered record, so replay suppression ran before authoritative filename
acceptance. The new remote file was therefore treated as already handled even
though its earlier record was only a semantic preflight failure and
`run_next.py` had never started.

Repair: replay suppression now remains authoritative for completed or ambiguous
execution, but a result explicitly marked `execution=command_file_failed` with
`semantic contract rejected` is retryable. The retry re-enters filename
acceptance, preserves the remote numeric step, and is recorded with
`replayed=false`. The default orchestrator entry point also derives the stem
from the source filename, so direct and HTTP-driven execution use the same
step authority. Regression coverage proves that a failed `1444` record does not
strand a later `1457` retry, while successful duplicate execution remains an
idempotent replay.

Build identity for this correction: Cockpit `0.1.0.dev1`, Extension `0.3.7`,
Bridge `remote-step-retry-authority-20260920`. This identity must appear in the
Cockpit header, extension details, bridge log, and each future test report.

# 2026-09-20 - persisted preflight counters crossed mission boundaries

The first real retry delivered `1457_chat_switch_standard_task.py` and created
the correctly numbered failed bundle, but the canonical handoff package was
unchanged. The command file was rejected before `run_next.py` because it had
no `__main__` guard and no argparse `--self-test` contract. A second defect
then made the result misleading: the persistent file-loop state already held
four preflight failures from steps `1442` through `1444`. The new mission was
therefore blocked immediately, and repeated observation of the same assistant
attachment exhausted the repeat guard.

Repair: persist the active mission ID in `file-loop-state.json` and discard
older counters, replay history, and terminal state when a new mission ID is
received. Old bundles and runner logs remain available as evidence. Regression
coverage proves that an old mission's preflight failure does not block the
first failed command of a new mission, while repeated failures within one
mission remain bounded and terminal.

## 2026-09-23: Verified Handoff Completion After 1467

Observed: 1467 generated the package with PASS, followed by confirmed native
result delivery. The first divergence was an unconditional next-step request:
the remote final acknowledgement had no .py, causing a false missing-1468 error.
Visible PASS text is not sufficient authority and must not bypass FILE_TRANSFER.

Repair: an explicit local standard-task contract, fresh artifact/revision
verification using the installed Kit validator, hash-bound delivery receipt,
and the existing durable completion gate. Desktop task scope now comes from
tasks.sqlite3, rather than the independent protocol session store. Browser DONE
halts locally without an operator STOP. No command/download/upload format changes.

Tests cover core rejection cases, idempotency, HTTP command-to-receipt-to-DONE,
actual content.js delivery ordering, failed sends and ordinary continuation.
The initial full run exposed two static tests tied to old implementation text;
their assertions were updated alongside behavioral coverage, without relaxing
the generation fence or Python-attachment requirement. The local full suite
passed. Live browser E2E remains a separate acceptance check, not implied by
the isolated integration tests. CI and handoff-content cleanup are out of scope.

## 2026-09-25: Artifact Side Panel and Premature Attachment Deduplication

Observed: the fresh `1469_chat_switch_standard_task.py` card appeared in a new
ChatGPT conversation, but no local command file or handoff package was created.
The event chain proved that the extension recognized the numbered attachment,
then spent 45 seconds looking only for a dialog-hosted CodeMirror preview and
another 45 seconds waiting for a browser download that never started. The
extension had already recorded the attachment key before either operation
succeeded, so the next poll suppressed the only valid response as a duplicate.

First divergence: ChatGPT now renders code attachments in a side-panel artifact
preview with a filename-labelled textbox, not necessarily under
`[role="dialog"]`. The download timeout was therefore the primary failure; the
premature deduplication marker converted that retryable transport failure into
a permanent mission stall and eventual assistant-response timeout.

Repair: accept both dialog and filename-labelled artifact preview text, locate
the nearest preview container for deterministic close handling, scope attachment
identity to mission and run generation, and commit the processed key only after
successful local processing. A failed preview/download remains retryable; the
server's existing idempotency boundary still protects a command accepted before
a later continuation failure. Regression coverage exercises multiple changing
numeric filenames and verifies that the current artifact-side-panel shape is
readable without weakening the one-Python-file or expected-step rules.

Build identity for this correction: Extension `0.3.12`, build
`artifact-preview-retry-20260925`.

## 2026-09-28: Preview Text Was Not the Authoritative Attachment Payload

Observed: the side-panel repair allowed content to arrive, but the arrived
content was not complete. The locally materialized
`Download/1469_chat_switch_standard_task.py` was 3,452 bytes / 75 lines with
SHA-256 `3baa69aeb62154455302d288a69f0f453e6db26aae4314b04bfebf67b1e81ba1`.
The complete browser download at
`~/Downloads/1469_chat_switch_standard_task(2).py` was 4,431 bytes / 77 lines
with SHA-256 `c385efa5346c04ec8a917a2a8f978c5226c55d3a23f42192c957eb111ea0db5b`.
The diff showed that the local file ended inside the `if ok:` block and missed
the successor prompt writer, return-bundle writer, and `__main__` guard.

First divergence: the content script treated readable CodeMirror/artifact
preview `innerText` as the command payload. ChatGPT's preview was a virtualized
UI projection, not the complete attachment. The local runner correctly rejected
the result before executing the file, and the file-loop blocked after repeated
same-family preflight failures; the Kit command was not reached.

Repair: button-rendered `.py` attachments now require the browser download path.
The preview may open and close as UI, but it is never submitted as command
content. The background download arm is persisted in `chrome.storage.session`
so a Manifest-V3 worker restart does not lose correlation; completed downloads
must be fresh relative to the arm timestamp and must not be one of the
previously known same-name files. `/v1/file-loop/download` remains the bounded
server-side materialization point and enforces the existing filename/path/size
rules. It now also validates the executable work-order contract before
returning `COMMAND_FILE_FETCHED`; `/v1/file-loop/command` performs the same
check before `K07_COMMAND_ACCEPTED`. A syntactically truncated or semantically
incomplete Python file therefore stops at ingress instead of consuming a local
execution number as an accepted command.

Verification: JS syntax checks for `content.js` and `background.js` pass. The
new Node regression uses a truncated preview and a complete simulated download
and requires `readAssistantButtonAttachment()` to return the download content.
A second Node regression proves the download arm survives worker restart,
ignores stale same-name downloads, accepts the fresh one, records byte size,
and clears the arm. Focused Python tests for attachment preview identity,
background download correlation, attachment dialog close, command-file ingress,
and download ingress pass. Additional ingress regressions reject truncated
Python before download fetch completion and before file-loop command
acceptance.

Build identity for this correction: Extension `0.3.13`, build
`download-authoritative-payload-20260928`.

Follow-up restart divergence: after manually staging `0.3.13`, restarting the
Cockpit could restore Chrome to extension `0.3.12`. The cause was the app
staging source order: a PyInstaller build exposes its embedded extension through
`sys._MEIPASS`, and `packaged_extension_source()` preferred that bundle before
the configured repository source. A stale built `.app` therefore overwrote the
fresh Application Support stage with its older embedded copy.

Repair: repository `chrome_extension/` is now the first staging source whenever
it exists; packaged app resources are fallback only when no repository source
extension is available. Runtime path authority records this source order, and
regression coverage simulates a stale bundled `0.3.12` app plus repository
`0.3.13`, requiring staging to preserve the repository identity.

Follow-up live divergence: a fresh standard-task E2E accepted start generation
`134` with extension `0.3.13` / build `download-authoritative-payload-20260928`
and prepared the bootstrap for local step `1472`. The native send path reported
`USER_TURN_INDETERMINATE` and the Cockpit stopped the mission as
`SEND_INDETERMINATE`, but the visible ChatGPT page later showed the exact new
user turn and a generated `1472_chat_switch_standard_task.py` response. No local
`Download/1472*` file was materialized because the mission had already stopped.

First divergence: send reconciliation was a false negative. The current
ChatGPT DOM exposed the user turn through visible localized author headings
such as `Du hast gesagt:` rather than the previously counted
`data-message-author-role="user"` wrappers. Generation activity and assistant
activity remain telemetry only; they are still not send acceptance.

Repair: the shared native-message snapshot now keeps the existing semantic
selectors first, then falls back to visible localized author-heading layouts
(`Du hast gesagt:` / `You said:`) and extracts the adjacent user-turn body while
discarding controls. Regression coverage proves both the snapshot and the
native commit path accept this role-less heading layout without accepting old
identical messages, altered messages, generation activity, or assistant
activity as authority.

Second live divergence: after the author-heading fallback, generations `135`
and `136` counted visible user turns, but still reported
`exact_user_message_found: false`. The page had persisted the new long user
turn in a collapsed rendering with a `Mehr anzeigen` control. In the live DOM,
the visible projection is a long ChatGPT-rendered beginning, but it may omit or
reshape later Markdown instead of being a complete prefix string of the raw
prompt.

Repair: native send reconciliation accepts a new persistent user turn when its
rendered text is either an exact match or a sufficiently long collapsed prefix
of the exact inserted prompt. It also accepts a long rendered projection with
the same beginning as the exact inserted prompt, because the native path already
verified the full composer content before submitting. These relaxed rendering
rules are only usable for a turn that is new after the send boundary; old
matching turns, short fragments, generation activity, composer mutation, and
assistant activity remain non-authoritative.

Related freshness repair: an indeterminate send can still have a remote side
effect. Before stopping, the browser now reserves the currently expected local
step as remote-issued. `next_step_number()` includes those reservations, so a
later fresh mission must not ask ChatGPT to reuse a number that may already
exist in the conversation but was not locally materialized.

Follow-up review divergence: an external protocol review reproduced two
runner-boundary failures with the real `Download/run_next.py`, not with the
stub runners used by several tests. First, `execute_with_run_next()` could
accept a newly created return bundle even when `run_next.py` exited non-zero.
That made a self-test-created bundle or a command that wrote a bundle and then
failed look like success. Second, a fresh local step below 100 was passed to
`run_next.py` as `1`, while the materialized command file was named
`001_*.py`; the canonical runner therefore could not select the command.

Repair: `run_next.py` now maps numeric selectors to zero-padded local command
filenames and logs textual `SystemExit` reasons into the runner log. The local
runner treats any non-zero `run_next.py` return code as an execution diagnostic
when candidate bundles exist; those bundles are retained only as evidence and
are not promoted to success. File-loop failure classification now treats both
`failed` and `FAIL` status values as failed outcomes.

Verification: focused runner regressions execute the real `Download/run_next.py`
for selector `1`, textual `SystemExit` logging, and a self-test-created bundle.
Additional runner tests prove that `rc != 0` plus a candidate return bundle
produces an execution diagnostic rather than a successful return bundle.

Follow-up live divergence: a later standard-task start reserved expected step
`1474` after native send reconciliation failed with `SEND_INDETERMINATE`.
The ChatGPT conversation then produced `1474_chat_switch_standard_task.py`, but
the Cockpit mission had already stopped at turn 0 and therefore never entered
the assistant-attachment download path. The manually downloaded file was
complete enough to pass the work-order shape checks; the first divergence was
the send boundary, not the file download or runner.

Repair: `USER_TURN_INDETERMINATE` with an empty composer is now treated as a
plausible remote side effect. The content script records a provisional send and
continues into the normal assistant-wait path instead of reserving the step and
stopping immediately. Positive unsent evidence still fails. If no assistant
response arrives before the existing assistant timeout, the provisional step is
then reserved as remote-issued to avoid later number reuse.

Verification: content-script regression coverage exercises the indeterminate
empty-composer path and requires `MISSION_BOOTSTRAP_SENT` rather than
`MISSION_BOOTSTRAP_SEND_FAILED`. Static contract tests assert the timeout-side
reservation path remains present.

## 2026-09-29: Megablick — Native Send Commit, Delivery State and In-Flight Records

Trigger: the native-send reconciliation domain had three consecutive repairs
without live success (author-heading fallback, long collapsed-prefix matching,
empty-composer provisional acceptance). AGENTS.md requires a Megablick before
a further mutation in the same failure domain.

Evidence (repository bridge log `.local/agp-cockpit/logs/bridge.log*`): every
live start on 2026-09-28/29 (missions `97cdc602`, `9a981d60`, `1c4ca481`,
`325227f2`) failed at bootstrap with `USER_TURN_INDETERMINATE` in the same
conversation. Each attempt reported `composer_chars: 0`,
`exact_user_message_found: false`, `generation_started_observed: false` and
`user_message_count: 5`, although the conversation grew by one user turn per
attempt. Across all five rotated logs there were zero `K07_NATIVE_TRACE`
events despite five indeterminate sends.

First divergence and root causes:

1. Observability defect: `background.js` sent native-transport traces with
   `chrome.runtime.sendMessage`. From a service worker this only addresses
   extension pages, never content scripts, so the `COMMIT_FAILURE` snapshot
   (before/after messages, URL) could never reach `/v1/client-event`. The test
   `test_k07_native_trace_event_sink_1165` only asserted source strings. Every
   later repair in this domain was therefore designed without the decisive
   trace.
2. Commit-evidence design defect: acceptance depended on recognising the new
   user turn through DOM wrappers, ids or positional index plus a rendered-text
   projection of a long Markdown prompt. The constant visible count of five
   is consistent with a bounded render window in which the index rule
   (`index >= before.length`) can never hold for id-less turns. Consecutive
   recovery prompts also shared their first 240 normalized characters, so the
   prefix rule could not distinguish them.
3. The 2026-09-29 empty-composer repair treated composer mutation as
   acceptance, contradicting this protocol, and on the handoff path would have
   allowed `/result-delivered` and `VERIFIED_COMPLETE` without proven delivery.

Coherent repair (one slice):

- Traces are addressed to the originating tab (`chrome.tabs.sendMessage`).
- `AGP_K07_SEND_COMMIT_NONCE_V1`: every native send is prefixed with a fresh
  `AGP-SEND-<16 hex>` line; its persistent appearance outside the composer is
  decisive commit evidence in `background.js` and in content-script
  reconciliation. The empty-composer provisional acceptance was removed; an
  unconfirmed send fails closed again.
- `AGP_K07_DELIVERY_STATE_V1`: per-step delivery state, `/v1/file-loop/delivery-ack`,
  re-delivery of `PENDING` results on replay (previously a replay after a lost
  send suppressed the continuation forever and stranded handoff completion).
- `AGP_K07_INFLIGHT_RECORD_V1`: `RUNNING` is persisted before `run_next.py`;
  a lost outcome blocks instead of executing again under a new number.
- `AGP_K07_POST_EXECUTION_OPERATOR_CONTROL_V1`: STOP/PAUSE requested during
  execution suppresses the continuation (STOP withholds, PAUSE re-delivers on
  resume). The browser also checks its run generation before sending.
- `AGP_K07_DOWNLOAD_PROVENANCE_V1`: download byte/hash binding between
  `/download` and `/command`; duplicate-name matching accepts the live
  `(2)`-without-space form and nothing looser than `<stem>( ?)(N).py`.
- `AGP_K07_BASELINE_BEFORE_SEND_V1` and `AGP_K07_ATTACHMENT_STABILITY_V1`.
- Recovery prompts after `OUTCOME_UNKNOWN` state that effects may have applied.

Verification: full Python suite and `ruff check .` green (Python 3.12 venv).
New behavioral tests: `tests/native_trace_delivery.cjs` (fails on the previous
`background.js`), `tests/test_k07_delivery_and_inflight_state.py`,
`tests/test_k07_delivery_http.py`, download-name tests in
`tests/test_download_ingress.py`, and `tests/e2e/test_k07_send_commit_nonce.spec.js`,
which drives the real `background.js` native transport against a real Chromium
DOM through forwarded CDP commands. In that fixture (role-less turns, five-turn
window, URL change, collapsed projection) the legacy matcher stays
indeterminate while the nonce commits; an emptied composer without a persisted
turn never commits. Playwright suite: 52 passed; the 11 failures
(`test_066_send_ack_false_negative_fixture` needs `tests/browser_fixtures/chatgpt_fixture.js`,
`test_203_phase5_conversation_contract` needs network access to chatgpt.com)
fail identically on the pre-change code in the review environment.

Build identity: extension `0.3.14` / `send-commit-nonce-delivery-state-20260929`,
bridge `send-commit-nonce-delivery-state-20260929`.

Not yet proven (G9, live acceptance): the fixture reproduces the divergence
class, not the exact live DOM. The next single real E2E must show
`NATIVE_SEND_ACCEPTED` or, if it still fails, a `K07_NATIVE_TRACE`
`COMMIT_FAILURE` whose `last_observed.commit_marker` settles whether the nonce
line is rendered. Result-file upload completeness before the continuation
commit and the generation-activity selectors remain unverified live.

## 2026-09-30: Live E2E — Send Commit Proven, Response Boundary Missed

Live run (mission `0be812a4`, extension `0.3.14`, bridge
`send-commit-nonce-delivery-state-20260929`): the bootstrap was committed in
one second (`NATIVE_USER_TURN_COMMITTED` → `NATIVE_SEND_ACCEPTED` →
`MISSION_BOOTSTRAP_SENT`). The send-boundary divergence of 2026-09-28/29 is
closed by live evidence. ChatGPT then rendered `1475_chat_switch_standard_task.py`
(complete, 79 lines, passes the command-file contract), but the browser emitted
no assistant observation and stopped with `K07_ASSISTANT_RESPONSE_TIMEOUT after 180s`
at turn 0. With the K07 debug trace enabled, `ASSISTANT_OBSERVED` never fired,
so `newAssistantTextAfterBaseline()` returned before its first trace point on
every poll; `assistantPythonAttachmentCandidates()` also returns nothing when
`[data-message-author-role="assistant"]` matches no node.

First divergence: response-boundary detection after a committed send. Most
consistent explanation, matching the 2026-09-28 finding that user turns lost
their role wrappers: the assistant turn has no `data-message-author-role`
wrapper either. Not yet proven by DOM evidence; no DOM snapshot was logged.

Repair: `AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1` identifies the awaited
response by the freshly assigned step number on a file card, independent of
assistant wrappers (analogous to the send nonce), and
`AGP_K07_ASSISTANT_WAIT_OBSERVATION_V1` logs bounded DOM evidence while
waiting, so the next miss is diagnosable from the log. Real-Chromium spec
`tests/e2e/test_k07_expected_step_attachment.spec.js` covers role-less turns,
older numbered cards, prose mentions and composer/dialog copies.

Stale-card guard: `1475` was rendered remotely but never materialized or
reserved locally, so the next mission would again expect `1475` and would find
the old card. Before the bootstrap is issued, every expected step that is
already visible as a card is reserved (`visible-unmaterialized-remote-attachment`)
and the number advances; before a continuation is sent, a visible card for the
next step reserves it and fails closed instead of sending.

Build identity: extension `0.3.15` / `expected-step-attachment-20260930`.

## 2026-09-30: Live E2E 4abfe28e — Transport Through Execution Proven, Delivery Fails

Extension `0.3.15`, bridge `send-commit-nonce-delivery-state-20260929`.
Proven live: stale-card reservation (1475), nonce/rendered send commit,
expected-step response detection without any assistant-role node
(`role_any=0`, `message_ids=0`), browser download with byte match (4306),
contract acceptance, exactly-once execution of `1476` (RUN_NEXT PASS, Kit rc 0,
validation PASS, generated_head = HEAD).

First divergence: result delivery. `result_file_attachment.js` reported
`ChatGPT file input did not confirm the selected result evidence files` while
both evidence files were visibly attached in the composer; the continuation was
not sent. Because `content.js` had already advanced `STATE.nextLocalStep` to
1477 before delivery, the replay/re-delivery path could not re-detect card 1476
and the loop timed out. Additional finding: `TASK_START_REQUEST_ACCEPTED`
invalidates the start request including `task_id`, so `/v1/file-loop/command`
saw `task_id=null` and verified handoff completion could not engage.
Details, priorities and design consequences:
`docs/engineering/K07_PROTOCOL_STATE_AND_NEXT_STEPS_2026-09-30.md` (D1–D7).

## 2026-09-30: Repair D1–D3 — Delivery Confirmation, Step Advance, Task Binding

D1 `AGP_K07_RESULT_ATTACHMENT_EVIDENCE_V2`: `result_file_attachment.js` no longer
re-dispatches `input`/`change` after `DOM.setFileInputFiles` and no longer reads
the transient `input.files`. Confirmation is the appearance of every step-scoped
evidence file name (also visually truncated) in the composer after the
selection; evidence already present in the composer is reused on re-delivery
instead of attached twice; otherwise it fails closed with composer diagnostics.
Proof: `tests/e2e/test_k07_result_attachment_evidence.spec.js` drives the seam
through a real CDP session on Chromium. The previous implementation fails that
spec with exactly the live message `ChatGPT file input did not confirm the
selected result evidence files`, which confirms the diagnosed cause.

D2 `AGP_K07_ADVANCE_STEP_AFTER_DELIVERY_V1`: `STATE.nextLocalStep` advances only
after the continuation was committed (or when delivery is not required:
terminal, already-delivered replay). A held (PAUSE) or failed delivery keeps
the current step, so replay can re-detect the card and re-deliver.
Proof: `tests/handoff_browser_completion.cjs`.

D3 `AGP_K07_ACTIVE_TASK_BINDING_V1`: accepting a start request now records a
durable mission-to-task binding (`active_task_binding.json`) before the one-shot
trigger is invalidated. `/v1/file-loop/command` and
`/v1/file-loop/result-delivered` resolve the task through that binding for the
current mission only. Proof:
`tests/test_handoff_completion.py::test_task_binding_survives_start_request_invalidation`
(fails when the binding lookup is disabled).

Build identity: extension `0.3.16` / bridge `delivery-and-task-binding-20260930`.
Live acceptance pending.

## 2026-09-30: Live E2E 0f655637 — Full Cycle With Confirmed Delivery; Old Bridge Running

Extension `0.3.16` was active; the desktop bridge still ran build
`send-commit-nonce-delivery-state-20260929` (app restarted without rebuild).
Proven live for the first time end to end: bootstrap commit, expected-step card
`1477`, browser download (4306 bytes), exactly-once execution (RUN_NEXT PASS,
Kit rc 0, validation PASS), result attachment confirmed (D1) and continuation
committed, followed by `K07_RESULT_DELIVERED` for the step's result hash (D2).
Not reached: verified handoff completion. The old bridge still logged
`K07_COMMAND_ACCEPTED task_id=null` (D3 not deployed), so it sent the ordinary
continuation expecting step 1478; the remote answered with prose
(`PASS — die Übergabe ist vollständig abgeschlossen.`), and the loop stopped
with `K07_ASSISTANT_RESPONSE_TIMEOUT` at 14:50:55. The desktop Standard Tasks
panel kept showing `WAITING_FOR_REMOTE` from the start message (stale UI state).
Next: rebuild/restart the bridge with `delivery-and-task-binding-20260930` and
repeat once.

## 2026-09-30 — Live acceptance mission ab040cc1 (step 1478) and Standard Tasks status line

- Build `delivery-and-task-binding-20260930` (bridge + extension 0.3.16). bridge.log sequence for mission `ab040cc1-0046-454e-a77a-0095a914ff24`:
  MISSION_BOOTSTRAP_SENT → K07_ASSISTANT_ATTACHMENT_OBSERVED (1478) → K07_ATTACHMENT_DOWNLOAD_USED (4306 bytes) → K07_COMMAND_ACCEPTED → K07_RESULT_BUNDLE_CREATED → NATIVE_USER_TURN_COMMITTED (FINAL_RECEIPT_PROMPT, 222 chars) → DONE.
  D1 (attachment confirmation), D2 (advance after delivery) and D3 (task binding across start-request invalidation) are live-proven.
- Failure: the desktop Standard Tasks panel still showed "Lokaler Zustand: WAITING_FOR_REMOTE". The text was written once at start and never refreshed; mission (DONE) and durable task (VERIFIED_COMPLETE) were correct.
- Repair (AGP_STANDARD_TASK_PROGRESS_V1): `core/standard_task_progress.py` derives the status from the bridge mission bound to the started mission id and the durable task state; the panel polls every 2 s until terminal. Mission DONE without VERIFIED_COMPLETE is reported as "Mensch muss prüfen", never as success; a foreign/absent mission is "Unklar".
- Test: `tests/test_standard_task_progress.py`.
- Second acceptance run (step 1479, 17:27): panel showed "Fertig ✓ … Mission: DONE · Lokaler Task: VERIFIED_COMPLETE"; remote acknowledged the final receipt.
- Remaining display defect in that run: "Steps 0" although one command file executed. The file loop never incremented `step_count` (only the legacy `record_step_result` did). Repair AGP_K07_STEP_COUNT_V1: `BridgeRuntime.record_local_step()` once per newly executed command file, never on replay; HTTP test `test_mission_counts_each_executed_step_once_and_never_a_replay` (fails without the fix).

## 2026-09-30 — D4 repair: terminal replies as step-scoped files

- Failure (latent, confirmed by live DOM evidence): prose terminal markers (`AGP_DONE`, `AGP_NEEDS_HUMAN`) are invisible because the ChatGPT DOM has no `data-message-author-role` nodes; a terminal answer could only end in `K07_ASSISTANT_WAIT_TIMEOUT` without reason. The bootstrap prompt still asked the remote to "respond with AGP_NEEDS_HUMAN".
- Repair AGP_K07_TERMINAL_REPLY_FILE_V1: `core/terminal_reply.py` (strict schema, step binding, idempotent recording), `/v1/file-loop/terminal`, download ingress and service-worker name checks accept `<step>_agp_terminal.json`; content script detects the card by expected step with two-poll stability, submits it and stops with "Fertig (Remote)" or "Mensch muss eingreifen". Remote DONE on a task with an unverified completion contract becomes NEEDS_HUMAN. Prompts (bootstrap, every step-assigning continuation) state the rule; wait-timeout message names the awaited files.
- Build `terminal-reply-file-20260930`, extension 0.3.17.
- Tests: `tests/test_k07_terminal_reply.py` (parse, binding, HTTP), `tests/test_handoff_completion.py::test_remote_done_file_cannot_complete_a_contract_task`, `tests/terminal_reply_browser.cjs` (actual tick), Playwright card detection.
- Live proof pending: whether ChatGPT renders a `.json` attachment as a card with the file name in its label and whether the download path delivers it.

## 2026-09-30 — New-chat send failure: COMPOSER_FOCUS_NOT_VERIFIED

- Live (build terminal-reply-file-20260930, mission d1061326, URL https://chatgpt.com/): bootstrap send rejected with `COMPOSER_FOCUS_NOT_VERIFIED`; before the focus step the visible composer (DIV, role textbox, no id) was already focused, afterwards the active element was BODY. The service worker resolved the composer by first match (`#prompt-textarea` no longer exists; fallback `[contenteditable="true"][role="textbox"]`), blurred the focused composer and focused an element that could not take focus. In the same run step 1480 of the previous chat was reported visible on the new-chat page (reserved, harmless). Both point to a hidden previous-conversation view kept in the DOM.
- Repair AGP_COMPOSER_RESOLVER_V1: one self-contained `agpResolveComposer()` (native_message_evidence.js) used by every CDP expression in background.js, the native snapshot and the content-side transport: only visible, enabled, non-inert candidates; the focused candidate wins. Focus failure diagnostics now report textbox counts. Expected-step cards inside hidden/inert containers are ignored.
- Test: `tests/e2e/test_composer_resolver.spec.js` (real Chromium). Build `composer-resolver-20260930`, extension 0.3.18.

## 2026-09-30 — Chat switch in a new chat: verified PASS not recognized (mission 8f7886a8)

- Positive live evidence: new-chat send works (AGP_COMPOSER_RESOLVER_V1); the terminal reply file `1483_agp_terminal.json` was detected, downloaded, recorded and ended the mission (`K07_TERMINAL_REPLY_ACCEPTED`, D4 live-proven); remote DONE on a contract task correctly became NEEDS_HUMAN; step counter correct (2).
- Step 1481: remote script bug (Kit ran with rc 0, script looked for the package in the wrong place, reported BLOCKED) → execution diagnostic and recovery turn. Correct Cockpit behavior.
- Failure (step 1482): Kit PASS, package regenerated, but the remote bundle used `"state"`/`"command"` instead of `"status"`/`"execution"`. `prepare_receipt` required the remote schema, returned None, and the verified result was sent on as an ordinary continuation; the remote then answered DONE → NEEDS_HUMAN. The task was complete but not recognized.
- Repair AGP_HANDOFF_EVIDENCE_NOT_SCHEMA_V1: completion rests on locally observed evidence (runner rc 0 and return bundle, all package files regenerated during the step, installed Kit validator PASS, Kit-written validation report for current HEAD, detailed prompt for this step). Remote positive claims are not required; remote negative declarations (`status` or `state` FAIL/BLOCKED) are respected. The chat-switch prompt now names the exact bundle keys. Tests: `test_live_1482_bundle_schema_completes_from_local_evidence` (fails on the old code) and neighbours. Build `handoff-evidence-20260930`, extension 0.3.19.

## 2026-09-30 — Regression by D4 prompt: remote DONE instead of a work order (mission at 16:48 UTC)

- Live: "Chat wechseln" started in the conversation that had just completed the task (same URL 6abd3ab2…). The remote answered the bootstrap with `1484_agp_terminal.json` (DONE, "already complete: step 1482 …"): no work order, no run_next output, no new handoff files. The Cockpit correctly refused the remote DONE (NEEDS_HUMAN), but the task did no work.
- Cause: D4 offered a terminal DONE in every prompt, including the bootstrap and continuations of a locally verified task. Before D4 the remote had no such exit and produced a fresh work order in the same conversation (1476–1479).
- Repair AGP_TASK_REPLY_POLICY_V1: `core/task_reply_policy.py` separates the reply policy from task definition and transport. Bootstrap: work order or NEEDS_HUMAN only, and "earlier results in this conversation do not complete" the new mission. Continuations: DONE offered only to generic missions; contract tasks get "never declare it DONE". The chat-switch task text requires a fresh local run on every start. Tests: `tests/test_task_reply_policy.py` (policy, orchestrator continuation, actual bootstrap function, task text). Build `reply-policy-20260930`, extension 0.3.20.

## 2026-09-30 — Hardening after the live runs (build fail-fast-20260930, extension 0.3.21)

- Live acceptance: "Chat wechseln" re-run in the same conversation (build reply-policy-20260930) — step 1485, one turn, one step, package regenerated, local verification, final receipt, DONE / VERIFIED_COMPLETE.
- AGP_BUILD_IDENTITY_GATE_V1: `startAuto` refuses to start (nothing sent) when the bridge build id differs from the extension build id; the mission is stopped with the reason "Build passt nicht …". Cause: a run with extension 0.3.17 against an older bridge failed only after the remote turn.
- AGP_K07_FAIL_FAST_REJECTION_V1: a bridge contract rejection (HTTP 400 "ValueError: …") stops the run at the first occurrence with "Vom Cockpit abgelehnt: …"; transient errors keep the existing three-attempt limit. Cause: three downloads of the same rejected file.
- AGP_STOP_REASON_V1: `/v1/file-loop/control` STOP accepts a `reason`; the extension sends the real cause, the mission records it, the Standard Tasks panel shows it (previously always "Stopped by operator control").
- Tests: `tests/fail_fast_browser.cjs` (actual tick/startAuto/stop), `tests/test_k07_delivery_http.py::test_stop_records_the_real_reason`.

## 2026-09-30 — Test 3 (tab "Arbeiten", push preparation): work order rejected, rule never stated

- Live (build fail-fast-20260930, step 1486): the remote returned `1486_push_preparation.py` using only git. The bridge rejected it ("missing declared agentic-kit command"); fail-fast worked: one download, immediate stop, mission STOPPED with the real reason. But the rule was stated nowhere in the prompts, which even listed git as an allowed tool; the test task itself (written by the reviewer) asked for git only.
- Decision (user): the Kit is always the command authority — every work order must execute at least one agentic-kit command; other allowed tools only in addition.
- Repair AGP_KIT_COMMAND_AUTHORITY_V1: `WORK_ORDER_KIT_RULE` next to the enforcing check in `command_file_contract.py`; stated verbatim in the bootstrap and every step-assigning continuation (test ties the JS text to the Python constant).
- Display: tab "Arbeiten" showed "Auftrag läuft" for a STOPPED mission and the overlay kept "READY" (AGP_TASK_PROGRESS_FROM_MISSION_V1: the panel uses the started mission's state; generic DONE is reported as remote-declared; `stop()` re-reads the mission state).
- Build `kit-authority-20260930`, extension 0.3.22.

## 2026-09-30 — Kit command catalog as enforced command authority (build kit-catalog-20260930, extension 0.3.23)

- User decisions: no git push/fetch as a standing rule; prefer complex (orchestrator) Kit commands; commands are not prescribed per task but taken from `docs/reference/agentic-kit-commands.json`.
- AGP_KIT_COMMAND_CATALOG_V1: digest of the manifest (254 commands, orchestrators first, ~58 KB) is attached to every mission start; work orders are rejected for unknown agentic-kit commands, git push/fetch/pull, or raw git/gh commands with a Kit wrapper. Checked against all real work orders 1458–1485: no false rejection (1462 is the known truncated file).
- Open (Kit side): the manifest has no "remote effect" classification; Kit orchestrators that push (e.g. `work finish`, `transfer pr-complete`) cannot yet be distinguished mechanically from local ones.
- Tests: `tests/test_kit_command_catalog.py`, `test_status_offers_the_kit_command_digest`, `tests/fail_fast_browser.cjs` (digest attached before the bootstrap send; attach failure sends nothing).

## 2026-09-30 — Tab "Arbeiten": editable task editor (build task-editor-20260930, extension 0.3.24)

- AGP_TASK_EDITOR_V1: the task is typed, pasted or loaded ("Auftrag laden", JSON shown formatted) into an editable editor; "Neuer Auftrag" empties it; "Task starten" is enabled for non-empty text and converts the editor text at start (plain text → goal, text starting with "{" → JSON task contract, invalid JSON reported, not started). While a task runs the editor is read-only; a terminal mission hands it back for change and restart.
- Tests: `tests/test_task_editor_gui.py` (real Tk widgets under a display; parsing without).

## 2026-09-30 — Test 3 accepted; human decision flow (build human-decision-20260930, extension 0.3.25)

- Live acceptance (mission at 18:06 UTC, build task-editor-20260930): Kit command digest attached; the remote chose `agentic-kit transfer divergence-status --json` itself; 1487 executed (PASS); `1488_agp_terminal.json` NEEDS_HUMAN with a correct question (no upstream configured). There was no way to answer it: NEEDS_HUMAN ended the mission and "Entscheidung freigeben" belongs to the unrelated durable checkpoint.
- AGP_HUMAN_DECISION_V1 / AGP_REMOTE_EFFECT_GATE_V1: question, note field and "Freigeben"/"Ablehnen" in the tab "Arbeiten"; `/v1/task/decision`; continuation of the same task in the same chat; one-shot, task-bound approval that alone admits remote-effect Kit commands (previously not blocked at all). Activity line shows "wartet auf deine Entscheidung".
- Worktree cleanup before a push: generated handoff package and rule-ack snapshot restored to the committed state (regenerated by every "Chat wechseln"), egg-info SOURCES committed, stray file `Q` removed.
- Tests: `tests/test_human_decision.py` (store, real manifest, HTTP flow: rejected → NEEDS_HUMAN → approve → one push accepted → next push rejected), `tests/test_task_editor_gui.py` (decision UI).

## 2026-09-30 — Test 4: approval recorded, but no push (build approval-scope-20260930, extension 0.3.26)

- Live run (steps 1489–1492): 1489 read-only `transfer divergence-status` PASS; `1490_agp_terminal.json` NEEDS_HUMAN "May this branch be pushed …?"; the human approved; the continuation mission ran 1491, again only `divergence-status`, with the bundle `human_approval_received: true`, `push_executed: false`, reason "Original task contract requires preparation only; allow_network=false also forbids remote execution."; `1492_agp_terminal.json` DONE "Task completed without push". Remote repository unchanged.
- Root causes: (1) `decision_mission_text` appended the original prepare-only task "unchanged" and never said that the approval lifts that restriction or orders the action; (2) the local authority sent to the remote side kept `allow_network=false`, so the approval contradicted the stated hard limit; (3) the unused one-shot approval stayed open (24 h) after the continuation ended.
- AGP_HUMAN_APPROVAL_SCOPE_V2: the APPROVE text orders the approved action now, via the matching Kit command (branch push: `agentic-kit transfer push-current --branch <branch> --json`, which sets the upstream itself), and states that it supersedes a prepare-only restriction for exactly that action; the original task follows as "context only". While the grant is open, `/v1/status` reports `allow_network: true` and `human_approval` in `local_authority` (the bootstrap prompt shows both). The continuation mission claims the grant; it expires when that mission ends (terminal reply, STOP, status poll) or another mission of the task becomes current. The asking mission never uses it. Raw git push/fetch/pull stay forbidden.
- Tests: `tests/test_human_decision.py` (continuation text, claim/expiry in the store, HTTP status with a local contract: allow_network false → true for the continuation → false after it ended unused, push rejected again).

## 2026-09-30 — Test 4 rerun: approval works, Kit blocks the push, retry stops the run (build approval-asks-20260930, extension 0.3.27)

- Live run (1493–1496): 1493 read-only PASS; `1494_agp_terminal.json` NEEDS_HUMAN; approved; the continuation's `1495_push_current.py` ran `agentic-kit transfer push-current --branch fix/k07-verified-handoff-completion --json` (approval consumed as designed). The Kit returned rc 2; the work order only tried to parse stdout as JSON, so the bundle said FAIL with `kit_result: null`, `stderr: ""`. The remote sent `1496_push_current_recovery.py` with the same push; the Cockpit rejected it (approval already used) and the run ended STOPPED with a ValueError.
- Kit cause (reproduced read-only with `build_transfer_state`): `rules_confirmed` false, `snapshot_id_mismatch`. `.agentic/rule_ack/current.json` (committed in #111) predates the change of the rule source `.agentic/state/status.md` in #134 on main; "Chat wechseln" rewrites it locally, but the pre-push cleanup had restored the stale committed version. `push-current` then prints the BLOCKED JSON followed by `FINAL_SIGNAL=…` lines on stdout (not parseable as JSON despite `--json`; Kit finding).
- Repair: rule acknowledgement refreshed with `agentic-kit rules acknowledge` and committed.
- AGP_REMOTE_EFFECT_ASKS_HUMAN_V1: an otherwise valid remote-effect work order without an open approval is not executed and ends the mission with NEEDS_HUMAN (question names file and Kit commands) instead of a hard rejection; invalid work orders are still rejected. The browser accepts a terminal command response without `result_file`.
- WORK_ORDER_KIT_RULE now requires every agentic-kit command's argv, returncode, stdout and stderr tails in the return bundle (1495 lost the Kit's reason).

## 2026-10-01 — Push accepted as DONE while CI was red; green CI before DONE (build ci-gate-20261001, extension 0.3.28)

- Live run (1497–1500, build approval-asks-20260930): 1497 read-only, 1498 NEEDS_HUMAN, approved, 1499 `agentic-kit transfer push-current --branch fix/k07-verified-handoff-completion --json` PASS (upstream set; the stale rule acknowledgement was the only cause of the earlier block), `1500_agp_terminal.json` DONE accepted as "von der Remote-Seite gemeldet". GitHub Actions "Agentic Gate #481" for `dab61bf` was red. Logically the task was not done.
- CI cause: two own e2e tests (`test_k07_result_attachment_evidence`, `test_k07_send_commit_nonce`) used `expect(promise).rejects` on a promise from a `vm` context; `@playwright/test` 1.62.1 (package-lock, CI) fails with "Unexpected return from a matcher function", 1.56 (local harness) passed. Fixed in `9952554`, reproduced and verified against 1.62.1.
- AGP_CI_GREEN_COMPLETION_V1 (see COMMUNICATION_PROTOCOL 15): a task that pushed is DONE only with green CI for the local HEAD, checked by the Cockpit with `agentic-kit pr status`; otherwise the DONE is rejected and the finding (with log excerpt) continues the task; bounded repair budget; evidence under `.local/agp-cockpit/ci/`. The download path no longer turns a missing approval into a hard rejection (the decision belongs to the command endpoint). Run_next and Kit checks get Homebrew on PATH for `gh`.
- Gap (Kit): `agentic-kit pr status`/`wait-ci` need a pull request number; there is no Kit command for the CI of a branch without PR, so the loop creates the PR with `transfer pr-create`.
- Tests: `tests/test_ci_gate.py` (verdicts, Kit call, terminal `pr`, repair budget, HTTP: no PR → continue, red with log → continue, repair push allowed, other remote effect asks, pending → wait, green → DONE `ci-verified`, no push → not gated, exhausted → NEEDS_HUMAN), `tests/terminal_reply_browser.cjs` (CONTINUE sends the prompt and keeps the run going), `tests/test_human_decision.py` (repair budget).

## 2026-10-01 — CI gate live: DONE verified, but primitives instead of the Kit lifecycle (build lifecycle-20261001, extension 0.3.29)

- Live run (1501–1519, build ci-gate-20261001): approval, `transfer push-current` (1503), `transfer pr-create` blocked four times by the Kit's fresh-LLM-context gate (outbox and latest handoff report missing; 1504–1513, each blocked attempt consumed approval budget, four approvals), `transfer refresh-llm-context-carriers` (1514), PR #137 (1516), `pr wait-ci` (1518), DONE with `"pr": 137`; the Cockpit ran `agentic-kit pr status 137` itself: green for `5c816fc` → DONE `ci-verified`. Evidence `.local/agp-cockpit/ci/5c816fc….json`.
- Findings: (1) the approval text and the DONE rejection named primitives (`push-current`, `pr-create`, `pr wait-ci`) and the repair budget admitted only those — this steered the remote side away from the Kit orchestrator (`work finish`, `pr-create-complete --post-merge-complete`) against the operator's requirement; with "do not merge" in the task no post-merge closeout ("Refresh successor package after PR…") could happen. (2) `sleep` was used but never defined in content.js since #105 (`NATIVE_TRANSPORT_FAILED: sleep is not defined`, 1510 and 1518; re-delivery followed). (3) The status line showed that stale error and "von der Remote-Seite gemeldet" for a CI-verified DONE.
- AGP_CI_LIFECYCLE_COMPLETION_V2 (COMMUNICATION_PROTOCOL 16): goals instead of command names; gate activated by every publishing Kit command; merged lifecycle verified (PR merged and containing the local work, main synchronized, Kit post-merge-check PASS, main CI green); repair budget follows the approved commands and their lifecycle (6 work orders); run_next timeout 30 minutes; `sleep` defined; status line "Fertig ✓ — CI grün geprüft (…)".
- Tests: `tests/test_ci_gate.py` (merge expectation, open green PR not enough after a merging orchestrator, approved orchestrator re-run allowed, merged lifecycle: unsynced → closeout → red main with log → pending → green; merged PR without the local work), `tests/test_human_decision.py` (no command names, orchestrator wording), `tests/test_standard_task_progress.py`.
