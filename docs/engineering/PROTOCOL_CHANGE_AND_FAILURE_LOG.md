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

## 2026-10-01 — Lifecycle live accepted; stale-app guard and effect refund (build stale-guard-20261001, extension 0.3.30)

- Live run (1520–1532, build lifecycle-20261001): one approval; the remote side chose `work finish`, `transfer pr-complete` (+`push-current`), `post-merge-complete`, `admin-refresh-pr`, `sync-main` itself; PR #137 merged, successor refresh #138, main `e375d60` green. Cockpit check `ci-verified`: PR head `843cb5d` = local work, main synced, Kit post-merge-check PASS, main CI green. 1526 ran 19 minutes (the former 11-minute limit would have cut it). Approval budget: 5 of 6 used.
- AGP_STALE_APP_GUARD_V1: the packaged app compares its build id with the bundle on disk and with `src/agp_cockpit/version.py`; on a mismatch the header shows a red warning and "Task starten", standard tasks and "Freigeben/Ablehnen" are refused. `scripts/build_macos_app.py` warns when an instance still runs; `--restart` quits it and opens the new bundle.
- AGP_EFFECT_REFUND_V1: refs of origin (`git ls-remote origin`) are compared before and after a remote-effect work order; unchanged refs (e.g. a run the Kit blocked, 1504–1513) do not consume approval budget. Unreadable refs consume (conservative).
- Handoff for Codex: `docs/engineering/K07_STATE_AND_NEXT_STEPS_2026-10-01.md` (supersedes the 2026-09-30 summary; lists the Kit findings).
- Tests: `tests/test_build_freshness.py`, `tests/test_ci_gate.py` (refund), all suites green.

## 2026-10-01 — P1 Kit command authority (build kit-authority-20261001, extension 0.3.31)

- Finding: the digest came from `docs/reference/agentic-kit-commands.json` (sha `ce455b7df8c5`), the installed Kit packages `ffae97536a52`; the remote side was offered a stale command list, and foreign repositories have no such file.
- AGP_KIT_INSTALLATION_AUTHORITY_V1: `core/kit_installation.py` finds `<repo>/.venv/bin/agentic-kit` or `agentic-kit` on the tool PATH, asks its interpreter for the packaged manifest and version; the repository copy is the fallback. `AGP_COCKPIT_KIT_BINARY` overrides (tests: `none`).
- AGP_STANDARD_TASK_ORCHESTRATOR_V1 / AGP_UNKNOWN_EFFECT_ASKS_V1: standard-task work orders need an orchestrator; remote effects only through orchestrators; unclassified orchestrators (e.g. `workflow go`) count as remote effect and are marked `"effect": "unknown"` in the digest.
- AGP_CORRECTABLE_REJECTION_V1: rule violations (manifest, raw network git, wrappers, orchestrator rule, contract violations) no longer stop the run with HTTP 400; the step is recorded as `<step>_agp_rejected.json` and the remote side gets the violations and the next step; after three rejections per mission NEEDS_HUMAN. The download path no longer applies the command-authority checks (they belong to the command endpoint).
- Tests: `tests/test_kit_authority.py` (installed manifest wins, fallback, unknown effect, orchestrator rule, HTTP correction and bound, status digest source), `tests/correction_browser.cjs` (actual content script sends the correction), adapted `test_human_decision.py`, `test_assistant_response_completion_064_r1.py`.

## 2026-10-01 — Lifecycle run for PR #139; P2 Lagebericht (build lagebericht-20261001, extension 0.3.32)

- Live run (1534–1545, build kit-authority-20261001): approval; `transfer pr-create-complete` + `post-merge-complete` (+`push-current`) merged PR #139 (`358e348`); `admin-refresh-pr` in 1543 changed nothing on origin and kept the approval budget (`HUMAN_APPROVAL_NOT_CONSUMED`, first live proof of AGP_EFFECT_REFUND_V1); successor refresh #140 (`dd4a15d`) green on GitHub. 1545 asked before `transfer post-merge-settle` (DESTRUCTIVE) + `sync-main`; the human approved at 18:52, the continuation was stopped at 18:52:20 before running. Local state afterwards: branch `docs/post-pr139-handoff-refresh` at `dd4a15d` with a Kit edit of `.agentic/state/status.md` (Kit finding 8); no CI_GATE_CHECKED for this run, i.e. the Cockpit did not confirm completion although GitHub is green.
- Kit findings 7 (managed CI template: unpinned Kit, duplicate runs, uncached browsers, 3–8 min runs) and 8 (self-renewing post-merge refresh) added to `K07_STATE_AND_NEXT_STEPS_2026-10-01.md`.
- AGP_REPO_STATE_V1 (plan P2): `core/repo_state.py` with read-only observation, pure classification, German Lagebericht, JSON report; Standard Tasks tab shows it (worker thread, refreshed on open, on request and after each task); no installed Kit blocks every task start (review sharpening). Rules text in the digest no longer claims a rejection where the Cockpit now asks the human.
- Plan sharpenings from the external review: R1 no silent repository fallback, R4 approval limited to the task's declared effect classes, P6 acceptance criteria (visible protocol, Wiederherstellen offered after interruption).
- Tests: `tests/test_repo_state.py` (all states incl. the live leftover-branch case, real git repository, report file, start block without Kit, Tk panel).

## 2026-10-01 — P3 Standard Tasks tab (build standard-tasks-20261001, extension 0.3.33)

- AGP_STANDARD_TASK_VERBS_V1 (plan P3): one text table `core/verbs.py` (label, group, step, effect badge, tooltip lines, plan slice); `availability()` enables a verb only if the repository state offers it, no task runs and its slice is implemented. The tab is now first (Standard Tasks → Arbeiten → System) with the Lage card, the main path ①–④, "Bei Problemen" and the collapsed "Weitere"; the recommendation is marked with ★ and bold; `ui/tooltip.py` provides delayed tooltips.
- Arbeiten switches to the Arbeiten tab; Chat wechseln keeps the existing chat-switch task; all other verbs stay disabled until P5–P11.
- Rendering note: the VM's default bitmap font lacks the circled digits and arrows; with a Unicode font (DejaVu) they render, and the macOS system font covers them. The "Weitere" toggle uses plain words instead of a triangle glyph.
- Tests: `tests/test_standard_task_verbs.py` (table completeness and tooltip lines, availability per state incl. running task and pending slice, tab order, Tk panel enabling and recommendation, Arbeiten opens the tab, collapsed section, tooltip show/hide).

## 2026-10-01 — Finish run P2 + P3 (1547–1556); slice T1 (build token-diet-20261001, extension 0.3.34)

- Live run (build standard-tasks-20261001): preflight 1547–1549 (incl. removal of the leftover Kit edit of `.agentic/state/status.md`), NEEDS_HUMAN 1550 before `transfer pr-create-complete`, approval; 1551 `pr-create-complete` returned rc 2 because the CI of PR #141 was red → execution diagnostic → 1552 recovery; 1553 test fix `bd7e3e9` (the repo-state test read the developer's `gh` login; CI runners have no login) → 1554 recovery; 1555 `pr-closeout-complete` merged #141, refresh #142, post-merge-check PASS; 1556 DONE with `"pr": 141`, Cockpit `CI_GATE_CHECKED green`, authority `ci-verified`, main `8d881c1`. Three approvals consumed (budget 1 + 6). Lagebericht showed LÄUFT with all verbs disabled during the run. P1–P3 live-confirmed.
- Failures found in the evidence: (a) Lagebericht cut the first porcelain path (`agentic/state/status.md`) because `_git()` stripped leading whitespace; (b) the durable task stayed `WAITING_FOR_REMOTE` after the accepted, CI-verified DONE; (c) the Standard Tasks status line said "bereit" while a task from "Arbeiten" ran; (d) the recommended button was taller (star glyph); (e) a test depended on the host's `gh`; (f) the remote side received 399 KB of result files and twice an 81 KB digest for one finish.
- Slice T1: AGP_RESULT_PROJECTION_V1, AGP_DIGEST_COMPACT_V1, AGP_TASK_CLOSE_ON_DONE_V1, AGP_GH_BINARY_V1, AGP_CI_GATE_V2 (COMMUNICATION_PROTOCOL 21–24) and the UI fixes. Kit finding 9 (orchestrator output size, rc ≠ 0 for a red CI finding) added to the 2026-10-01 handoff; finding 7 updated.
- Tests: `tests/test_result_projection.py`, `tests/test_ci_template.py`, additions in `test_repo_state.py` (first porcelain line, no gh), `test_ci_gate.py` (task closes as VERIFIED_COMPLETE / REMOTE_DONE), `test_kit_command_catalog.py` (compact digest keeps effects and wrappers, < 40 KB), `test_standard_task_verbs.py` (badge, hint while a task runs elsewhere).

## 2026-10-02 — Finish T1 (1557–1560); slice T2 (build hygiene-20261002, extension 0.3.35)

- Live run (build token-diet-20261001): preflight 1557, NEEDS_HUMAN 1558 before `transfer pr-create-complete`, approval, 1559 `pr-create-complete` merged PR #143 and the successor refresh #144, DONE 1560 `ci-verified`, local task `VERIFIED_COMPLETE` (AGP_TASK_CLOSE_ON_DONE_V1 live). `K07_RESULT_PROJECTED` 1559: 81,348 → 14,923 bytes. CI after AGP_CI_GATE_V2: #504 (PR) 2:02, #505 (main) 1:52, #506 1:46, #507 2:06; no duplicate push runs.
- Failures found: (a) the startup worker wrote no refresh request when the first handshake did not arrive within 180 s (20:14 start: extension 0.3.33 ran four hours beside build token-diet); (b) `ACTIVE_TAB_NOT_CHATGPT` aborted the startup although the handshake path refreshed the extension later (04:23 start, 75 s); (c) the handshake is throttled to 60 s; (d) every remote file stayed in `~/Downloads`, Kit logs and diffs in `/tmp`, `Download/alt` held 973 MB.
- Slice T2: AGP_EXTENSION_AUTO_REFRESH_V2, AGP_DOWNLOAD_HYGIENE_V1, AGP_MAINTENANCE_CLEANUP_V1, AGP_KIT_FINDINGS_VIEW_V1, AGP_DIGEST_ONCE_PER_CHAT_V1 (COMMUNICATION_PROTOCOL 25–29); Greenfield ledger KIT-GF-023…028; `Download/alt` removed, five cited files moved to `.local/agp-cockpit/archive/cited-evidence/`.
- Tests: `tests/test_extension_auto_refresh.py`, `tests/test_kit_findings_and_maintenance.py`; stubs for the new content-script helpers in the three Node content-script tests. Playwright e2e: 65 passed; the 9 `test_203_phase5_conversation_contract` specs need network access to chatgpt.com and cannot run in the sandbox (unchanged code).

## 2026-10-02 — Finish T2 (1561–1564); slice T3 (build findings-sync-20261002, extension 0.3.36)

- Live run (build hygiene-20261002): preflight 1561, NEEDS_HUMAN 1562, approval, `pr-create-complete` 1563 merged PR #145 and refresh #146, DONE 1564 `ci-verified`, task `VERIFIED_COMPLETE`. `K07_BROWSER_DOWNLOAD_REMOVED` for 1561–1564 (AGP_DOWNLOAD_HYGIENE_V1 live); `KIT_COMMAND_DIGEST_REUSED` for the decision mission (AGP_DIGEST_ONCE_PER_CHAT_V1 live). CI #508–#511: 1:43–1:59.
- Operator findings: window too small, parts of tabs cut off; „Empfohlen: Abschließen“ next to the disabled P6 button; the Kit repository already records which Greenfield findings are fixed; the owner's release policy (no publication, no Zenodo) is not expressible in the Kit (KIT-GF-029). Chrome shows a „Fehler“ entry for the extension (content not yet read).
- Slice T3: AGP_KIT_FINDINGS_SYNC_V1, AGP_RELEASE_POLICY_V1, AGP_SCROLLABLE_TABS_V1, recommendation hint (COMMUNICATION_PROTOCOL 30–33); ledger snapshot of the Kit adjudication (Kit commit 26be95b) and KIT-GF-029.
- Tests: `tests/test_t3_findings_sync_release_policy.py`.
- Chrome error of the extension, read 2026-10-02: „Uncaught (in promise) Error: Extension context invalidated“, `content.js:3580` (the 0.3.34 script: line 3580 lies in `render()`, which reads `chrome.runtime.getManifest()`/storage). Cause: the automatic reload replaced the extension while the old content script of the open ChatGPT tab kept running its timers. Fix in T3: AGP_ORPHANED_CONTENT_SCRIPT_GUARD_V1 (COMMUNICATION_PROTOCOL 34), test `tests/orphan_guard_browser.cjs`.

## 2026-10-02 — Fresh-chat stop at 1568 (build work-order-contract-20261002, extension 0.3.37)

- Live run (build findings-sync-20261002): the T3 finish started in a new ChatGPT conversation. Work order `1568_agp_branch_closeout_probe.py` had no `--self-test` mode; `/v1/file-loop/download` raised „command file semantic contract rejected: missing --self-test contract“ → `K07_BRIDGE_REJECTED` → `AUTO_ERROR` → mission STOPPED, task left `WAITING_FOR_REMOTE`. Nothing ran locally.
- Causes: (a) the structural work-order contract was enforced but stated to the remote side only in the chat-switch standard task; earlier chats had learned it from history; (b) download ingress ran the semantic checks, which bypassed the correctable path of `/command` (AGP_CORRECTABLE_REJECTION_V1).
- Fix: AGP_WORK_ORDER_SHAPE_RULE_V1 and AGP_INGRESS_SAFETY_ONLY_V1 (COMMUNICATION_PROTOCOL 35); the correction prompt repeats the rule. System tab „Werkzeuge“: descriptions wrap instead of being cut off.
- Tests: `tests/test_fresh_chat_work_order_contract.py` (the live 1568 file is fetched, its violation is correctable, the correction prompt and content.js carry the rule); `test_k07_command_file_ingress_989.py` now expects /download to fetch an incomplete file.

## 2026-10-02 — Finish T3 (1568–1582); slice T4 (build merged-guard-20261002, extension 0.3.38)

- Live run (build work-order-contract-20261002, same conversation as the stopped 1568): 1569 and 1570 rejected for correction (missing `--self-test`, invented `agentic-kit git`), 1571 PASS — AGP_CORRECTABLE_REJECTION_V1 and AGP_INGRESS_SAFETY_ONLY_V1 live, but the rule text alone did not prevent two violations. 1572 NEEDS_HUMAN, approval; 1573 `pr-create-complete --post-merge-complete` rc 0: PR #147 merged (`fc8afef`), refresh #148 (`5c1544c`), post-merge PASS.
- Failure: the 1573 bundle kept only the tail of the Kit stdout; the verdict (PR number, merge) stands at the start of the Kit JSON, so the 24 KB bundle held no PR number (the Cockpit projection cut 18.8 KB more, but the information was already missing). 1574 re-ran `pr-create-complete` as a „recheck“; the Kit recreated the local branch from `origin/feat/t3-…`, opened PR #149 without content difference (CI #516/#517); 1575–1581 completed it (`pr-complete` rejected `--post-merge-complete`, then BLOCKED by stale LLM context carriers, `refresh-llm-context-carriers`, then PASS); main `44e0c69` is an empty squash commit. DONE 1582 `ci-verified`, task `VERIFIED_COMPLETE`; three approvals consumed.
- Slice T4: AGP_MERGED_BRANCH_GUARD_V1, AGP_REPOSITORY_FACTS_V1, AGP_KIT_VERDICT_RULE_V1 (COMMUNICATION_PROTOCOL 36–38); KIT-GF-030 (second PR for a merged branch), KIT-GF-031 (pr-complete option asymmetry and mid-lifecycle context blocker), KIT-GF-027 extension (verdict only at the start of the JSON).
- Tests: `tests/test_t4_merged_branch_guard.py` (temporary git repository with squash merge and refresh; deleted local branch; dirty tree and branches without commits not blocked; correctable rejection; facts in the continuation; gh pull-request listing; the real refs of 1574 classified MERGED against `5c1544c` and CHANGES against `effbc85`).

## 2026-10-02 — Finish T4 (1583–1587); slice T5 (build finish-button-20261002, extension 0.3.39)

- Live run (build merged-guard-20261002): 1583 rejected for correction („unknown agentic-kit command 'agentic-kit git'“), 1584 PASS, 1585 NEEDS_HUMAN quoting the Cockpit-verified facts, approval, 1586 `pr-create-complete` PASS (PR #150, refresh #151), 1587 DONE `ci-verified`, task `VERIFIED_COMPLETE`; one remote turn, no second pull request. The 1586 bundle still kept no separate Kit verdict fields (rule 38 not followed).
- Cause of the recurring „agentic-kit git“ rejections (1569, 1570, 1583): a Cockpit false positive — the work orders' `"allowed_tools": ["agentic-kit", "git"]` was parsed as an invocation. Fixed: AGP_TOOL_LIST_NOT_INVOCATION_V1.
- Slice T5: AGP_STANDARD_TASK_FRAMEWORK_V1, AGP_START_CLICK_APPROVAL_V1, AGP_STANDARD_VERIFIER_V1, AGP_NO_FORCE_V1, Abschließen, Arbeit beginnen, basic Wiederherstellen (COMMUNICATION_PROTOCOL 39–43); release policy `tag_push` allowed after approval.
- Tests: `tests/test_t5_standard_task_framework.py` (definitions and scopes, goal texts without command names, prechecks in temporary git repositories, scoped pre-approval with effect log, verifiers, bridge hook order, tool-list and force rules, panel: dialog/confirmation, pre-approval and CI gate, R5 lock, R6 offer, follow-up); adjusted verb and T3 hint tests.

## 2026-10-02 — Abschließen live (1588–1589); Arbeit beginnen stopped; fix T5b (build send-ready-20261002, extension 0.3.40)

- „③ Abschließen“ of T5 (build finish-button-20261002): one remote turn, 1588 `pr-create-complete` under the start-click approval (one consumption shown in the tab), PR #152 and refresh #153 merged, 1589 DONE `ci-verified`, task `VERIFIED_COMPLETE`, no NEEDS_HUMAN. P5/P6 live-confirmed. Cosmetic: the tab showed a generic „Ergebnis lokal verifiziert“ and two recommendations (status line „Chat wechseln“, star on „Arbeit beginnen“).
- „① Arbeit beginnen“ (feat/p11-release-button): the digest was re-attached (fifth mission in the chat), the bootstrap send failed after 3 s with `SEND_BUTTON_NOT_READY` (send control disabled during the upload) → MISSION_BOOTSTRAP_SEND_FAILED → STOPPED; nothing ran locally, no branch created.
- Fix T5b: AGP_SEND_READY_AFTER_UPLOAD_V1, single recommendation after a finished task, verdict in the DONE text (COMMUNICATION_PROTOCOL 44). Tests in `tests/test_t5_standard_task_framework.py`, `tests/test_k07_send_control_readiness_wait.py`.
- Operator finding after the rebuild: the composer still held the bootstrap text and the digest chip of the failed send; a new start would have appended to it (INSERT_NOT_VERIFIED). Fix AGP_COMPOSER_CLEAN_START_V1 (COMMUNICATION_PROTOCOL 45), build composer-clean-20261002, extension 0.3.41. Tests: `tests/e2e/test_composer_clean.spec.js` (real Chromium page: leftovers removed, own text and foreign files kept and reported, evidence of the current send kept, empty composer untouched), stubs in `tests/fail_fast_browser.cjs` and `tests/e2e/test_066_actual_contentjs_send_ack.spec.js`.

## 2026-10-02 — Abschließen T5b/T5c live (1590–1591); Arbeit beginnen NOT_READY again; T5d (build send-retry-20261002, extension 0.3.42)

- „③ Abschließen“: PR #154 and refresh #155 merged in one remote turn, `ci-verified`; the tab showed the CI verdict and a single recommendation. `COMPOSER_LEFTOVERS_REMOVED` cleared the leftover text; the leftover digest chip was not recognised (`removed_files: []`) — the remove control of ChatGPT's chips does not carry the assumed label; it was sent along (same file, harmless).
- „① Arbeit beginnen“ again: digest reused (no upload), text inserted and verified, send control not actionable for 73 s → `SEND_BUTTON_NOT_READY` → STOPPED, nothing sent. The cause is not the upload; the diagnostics were cut at 500 characters in the log, so the button state is unknown. Both failures came right after a finished Abschließen in the same chat.
- T5d: AGP_SEND_NOT_READY_RETRY_V1 (COMMUNICATION_PROTOCOL 46) — structured diagnostics as non-string event details (not truncated), text-only clean, one retry after 15 s. Tests `tests/send_not_ready_retry.cjs` and `tests/test_browser_cjs_suites.py` (which now also runs the T3 orphan-guard suite that had no wrapper).

## 2026-10-02 — T5d live (1592–1593); Arbeit beginnen live (1594–1597); release 0.1.0 prepared

- „③ Abschließen“ of T5d: PR #156 and refresh #157 in one remote turn, `ci-verified`.
- „① Arbeit beginnen“ (feat/p11-release-button): no send failure this time (no SEND_BUTTON_NOT_READY, so the earlier cause stays unexplained; diagnostics are in place); 1594 `work start` rc 0 but left Kit-owned files dirty (KIT-GF-011 extension), 1595 rejected for correction (no orchestrator in a standard task), 1596 `work recover` + `transfer restore-known-volatile`, 1597 DONE, local verifier `work-started` passed, task `VERIFIED_COMPLETE`. P7 live-confirmed.
- Release check with Kit 1.0.13 in a local clone: `release-prep` fails on `src/agentic_project_kit/__init__.py`; `release ready` BLOCKED by version, first-release, documentation and DOI checks → KIT-GF-032. Owner's decision: manual release 0.1.0 (AGP_VERSION_MAP_V1, CHANGELOG.md), build release-0.1.0, extension 0.4.0; chip diagnostics AGP_COMPOSER_CHIP_DIAGNOSTICS_V1 (COMMUNICATION_PROTOCOL 47–48).
- „③ Abschließen“ of the release branch (build release-0.1.0) stopped with SEND_BUTTON_NOT_READY, the retry too. The new diagnostics settled the cause: the send button was present, enabled, `aria-label="Senden"`, `type="submit"`, inside the form, without `data-testid`; `elementFromPoint` at its centre returned an svg outside the button, so the readiness rule (hit test or test id) never held. The earlier stops (16:11, 16:58) fit the same ChatGPT variant; runs that worked had the test id. Fix AGP_SEND_CONTROL_SEMANTIC_V1 (COMMUNICATION_PROTOCOL 49), build release-0.1.0-r2, extension 0.4.1.

## 2026-10-02 — Release branch merged (#158/#159); send still NOT_READY under r2; probe escape fix (build release-0.1.0-r3, extension 0.4.2)

- „③ Abschließen“ of the release branch under build release-0.1.0-r2: step 1598 `transfer pr-create-complete` ran (PR #158 and refresh #159 merged, main a9a8c1e, post-merge-check PASS), but the continuation was never sent: SEND_BUTTON_NOT_READY, the retry too; the resubmitted 1598 was correctly rejected by the merged-branch guard; the correction send failed the same way → K07_ASSISTANT_RESPONSE_TIMEOUT, STOPPED. The task stayed WAITING_FOR_REMOTE; the CI gate was not verified by the Cockpit.
- Cause: the diagnostics matched rule 49 exactly („Senden“, submit, in form, enabled), yet the probe did not accept it. The probe is a template literal; `/^(send|senden)\b/i` written with one backslash cooked to a backspace, so the regex never matched. The tests only compared source text. A second instance (`/\s+/g` in the form-button diagnostics) cooked to `/s+/g`.
- Fix AGP_PROBE_TEMPLATE_ESCAPES_V1 (COMMUNICATION_PROTOCOL 50): double backslashes; `tests/send_probe_template.cjs` checks every evaluated template for single-backslash escapes and runs the cooked probe against the 1598 DOM (fails on r2, passes on r3).

## 2026-10-02 — Send fix live (#160/#161), tag v0.1.0; Chat wechseln left a false STÖRUNG

- „③ Abschließen“ under build release-0.1.0-r3: PR #160 and refresh #161 in one remote turn, `ci-verified`, no SEND_BUTTON_NOT_READY — AGP_PROBE_TEMPLATE_ESCAPES_V1 live-confirmed. The owner set and pushed the annotated tag `v0.1.0` on `278fa92`. The 56 merged remote branches were already gone on GitHub; `git fetch --prune` removed the stale tracking refs.
- „④ Chat wechseln“ (step 1602) completed and was acknowledged, but `transfer chat-switch-complete` rewrote the five successor-handoff files on main for HEAD 278fa926; the Lagebericht counted them as unexpected changes → STÖRUNG with Wiederherstellen recommended. The Kit itself lists them as known volatile. Fix AGP_KIT_VOLATILE_PATHS_V1 (COMMUNICATION_PROTOCOL 51). The regenerated files were restored to the committed version.
- Open design question: „Chat wechseln“ prepares the package but does not open a new chat or hand it over, and it is recommended after every Abschließen.

## 2026-10-02 — Kit volatile fix live (#162/#163); branch cleanup; no Chat-wechseln recommendation

- „③ Abschließen“ of AGP_KIT_VOLATILE_PATHS_V1: PR #162 and refresh #163 in one remote turn, `ci-verified`, Lage BEREIT on main 7955d0f.
- The three remaining unmerged branches (`backup/k07-1467-…`, `checkpoint/k07-json-protocol-…`, `work/phase1-cockpit-core-integration`) were checked line by line against main: 96 %, 81 % and 98 % of their added lines are in main; the rest is superseded (old command-file contract with `--self-test`, the allowed_effects/allowed_tools envelope of the JSON protocol, the mission transition table without BLOCKED). Recommended for deletion. GitHub's „Automatically delete head branches“ was already on; the earlier „remote ref does not exist“ errors came from stale local tracking refs.
- Owner's decision: „Chat wechseln“ is no longer recommended after Abschließen (AGP_NO_CHAT_SWITCH_FOLLOW_UP_V1, COMMUNICATION_PROTOCOL 52).

## 2026-10-02 — No-chat-switch live (#164/#165); window size; private Release entry

- „③ Abschließen“ of AGP_NO_CHAT_SWITCH_FOLLOW_UP_V1: PR #164 and refresh #165 in one remote turn, `ci-verified`; the star moved to „① Arbeit beginnen“ as intended.
- AGP_INITIAL_WINDOW_SIZE_V2: the Cockpit opens at the size the owner chose by hand (986×754 pt outer on macOS → geometry 986x726), clamped to smaller screens.
- Owner's decision: a GitHub Release entry in the private repository may be created by the owner by hand (`owner_github_release` in `release_policy.json`); Cockpit work orders stay barred from `gh release …`.

## 2026-10-02 — Window and release entry live (#166/#167); Kit-gated buttons (P8 full, P11)

- „③ Abschließen“ of AGP_INITIAL_WINDOW_SIZE_V2 and the private-release policy: PR #166 and refresh #167 in one remote turn, `ci-verified`. The owner created the GitHub Release entry „AGP Cockpit 0.1.0 (privat)“ on tag v0.1.0 (278fa92) by hand; no Zenodo record exists.
- P8 design check with Kit 1.0.13 in a sandbox clone: Kit routes exist for main behind origin/main, detached HEAD and discarding changes on a work branch, but not for a dirty main or local commits on main (KIT-GF-033). Owner's decision: no Cockpit-local or raw-git workaround — the full Wiederherstellen waits for the Kit fix, like the Release button for KIT-GF-029/032 (AGP_KIT_GATED_VERBS_V1, COMMUNICATION_PROTOCOL 53). The basic Wiederherstellen now names the Kit routes as goals and stops with NEEDS_HUMAN where the Kit has none.

## 2026-10-02 — Kit-gated buttons live (#168/#169); P4 Repo wechseln

- „③ Abschließen“ of AGP_KIT_GATED_VERBS_V1: PR #168 and refresh #169 in one remote turn, `ci-verified`; KIT-GF-033 is on main 7f2e421 for the Kit-side work (Codex).
- P4 found that the Cockpit could only steer its own checkout: the start gate required `chrome_extension/` and `.agentic/` in the repository, the staged-extension marker kept the first repository (identity check „repository-root-mismatch“ after a switch), an existing bridge was reused without comparing its repository, and other repositories had no `Download/run_next.py`. All four fixed with the switch (COMMUNICATION_PROTOCOL 54).

## 2026-10-03 — P4 merged (#170/#171); start blocked by the front Chrome tab

- „③ Abschließen“ of P4: PR #170 and refresh #171 in one remote turn, `ci-verified`.
- The first start attempt was blocked: „Aktiver Chrome-Tab ist kein freigegebenes ChatGPT-Ziel: chrome://extensions/“. The bridge log shows a fresh handshake of the ChatGPT tab (11:00:51) — the chat was connected; only the front tab was the extensions page. The owner reloaded the chat by hand, which made it the front tab. Fix AGP_CONNECTED_CHAT_TARGET_V1 (COMMUNICATION_PROTOCOL 55): fall back to the chat of the fresh handshake and focus it.

## 2026-10-03 — Kit 1.0.14 retest (#174/#175), P8 full (#176/#177); P8 live test 1

- „③ Abschließen“ of the Kit 1.0.14 retest (KIT-GF-029, KIT-GF-033 VERIFIED_FIXED) and of P8 full: PRs #174 and #176 with refreshes #175 and #177, each one remote turn, `ci-verified`.
- Live test 1 of the full Wiederherstellen: a local commit on main (`cd1166e`) plus an untracked file. The Lage switched to STÖRUNG by itself (AGP_LAGE_AUTO_REFRESH_V1 confirmed live); the remote side ran the Kit's rescue dry run and stopped with NEEDS_HUMAN naming the planned actions and the rescue branch (terminal file 1622_agp_terminal.json) — as designed. Gap: the Standard Tasks tab had no place to answer a NEEDS_HUMAN (the decision box existed only in „Arbeiten“ for its own missions), so the approval could not be given. The test disturbance was resolved with the same Kit route outside the Cockpit (`work rescue` dry run + signed execute with Kit 1.0.14): main == origin/main 202a6e0, clean, everything on `rescue/main-cd1166e5-61bcdd96e9` (the commit and the untracked file). Fix AGP_STANDARD_TASK_DECISION_V1 (COMMUNICATION_PROTOCOL 58); live test 2 follows after the merge.

## 2026-10-03 — Decision box live (#178/#179); P8 live test 2 passed

- „③ Abschließen“ of AGP_STANDARD_TASK_DECISION_V1: PR #178 and refresh #179 in one remote turn, `ci-verified`.
- Live test 2 of the full Wiederherstellen (local commit `cdc9a82` on main plus an untracked file): the Lage switched to STÖRUNG by itself; the remote side diagnosed (1625), ran the rescue dry run (1626) and asked (1627); the question with planned actions, rescue branch and dry-run signature appeared in the new decision box of the Standard Tasks tab; after „Freigeben“ the continuation „Standard · Wiederherstellen · Entscheidung“ ran the signed `work rescue --execute` (1628, PASS) and ended with DONE (1629), locally verified: Lagebericht BEREIT, main == origin/main 3d8a42a, clean. Nothing lost: `rescue/main-cdc9a828-b76a2efa2b` holds the test commit and the untracked file. P8 full is live-verified.
- Polish found in the same run: the status line cut the summary at 240 characters in the middle of a word („… PASS with fail“ for „failed_step null“) — AGP_SUMMARY_CLIP_V1 cuts at a word boundary and marks the cut; a needless horizontal scroll bar appeared because the tab width was fixed at 900 px while the vertical bar narrowed the canvas — AGP_SCROLL_WIDTH_FROM_CONTENT_V1 takes the content's requested width and re-lays out when it changes.

## 2026-10-03 — KIT-GF-035 recorded (#184); refresh #185 red on a live-website e2e test

- „③ Abschließen“ of KIT-GF-035 and the KIT-GF-032 retest: PR #184 merged (main b744f1d). The successor refresh #185 changes only five handoff files, but its browser job was red (run #588) while the identical code was green on main (run #587): five `test_203_phase5_conversation_contract` specs failed with „Execution context was destroyed, most likely because of a navigation“.
- Cause: `test_203` opened the live `https://chatgpt.com/c/phase5-target` before replacing the content; the live page navigated on its own and destroyed the test context. Without network to chatgpt.com all nine specs fail (reproduced). Fix AGP_E2E_NO_LIVE_NETWORK_V1: the URL is served by a `page.route` stub (as `test_k07_send_commit_nonce` already does); `tests/test_e2e_no_live_network.py` fails every spec that navigates without serving its own page. #185 itself went green when the owner re-ran the failed job (run #588, attempt 2) and was merged (e384203).

## 2026-10-03 — Kit 1.0.15: KIT-GF-032 verified fixed; P11 no longer Kit-gated

- Kit 1.0.15 released (PRs #2360–#2365; Zenodo 10.5281/zenodo.23126837). The tag push built the release but skipped `publish-pypi` (repository variable `PYPI_TRUSTED_PUBLISHING_ENABLED` not set); the owner published to PyPI through the Release workflow from tag v1.0.15 (`publish_target: pypi`). The release PR needed a rewrite of its CHANGELOG summary (KIT-GF-036).
- Retest with Kit 1.0.15 from PyPI (GF-E042): `release ready` and `release prepare --write` PASS in a sandbox clone with `publication: none`; KIT-GF-032 → VERIFIED_FIXED. The managed CI template pins 1.0.15, `.agentic/config.yaml` declares `publication: none`, and the Release verb is no longer Kit-gated (still plan P11).
- Found for P11: `release prepare --write` bumps `pyproject.toml` only; the Cockpit's version map (`APP_VERSION`, `docs/releases/versions.json`) is no Kit anchor, so `tests/test_release_versions.py` fails on the release branch.

## 2026-10-04 — Abschließen of chore/kit-1.0.15 stuck (steps 1650–1657)

- `publication: none` changed `.agentic/config.yaml`, a Kit rule source. `pr-create-complete` blocked with `snapshot_id_mismatch` although `rules acknowledge` passed: the repository tracked `.agentic/rule_ack/current.json`, and the Kit's pre-push volatile restore put the stale committed copy back (as for #134/#137). The remote side then ran `rules communication-refresh --publish`, whose pending state blocks `pr-create-complete` until the capsule is on main — a deadlock (KIT-GF-039). The Cockpit correctly refused `transfer push-current` twice (1654, 1657).
- Recovery: the owner stopped the run; the pending file and the generated capsule were moved to `.agentic/tmp/stale-1656/` (nothing deleted); `.agentic/rule_ack/` is no longer tracked and is ignored, as in the Kit's own layout. Reproduced in a sandbox: without the tracked copy the rule gate passes.

## 2026-10-04 — Kit 1.0.15 in the Cockpit (#188/#189); Abschließen for an open Kit follow-up

- „③ Abschließen“ of `chore/kit-1.0.15`: step 1662 merged PR #188 and refresh #189 (`pr-create-complete --post-merge-complete`, rc 0); the remote side then tried another pull request for the merged branch (1663), which AGP_MERGED_BRANCH_GUARD_V1 refused; the next turn returned DONE, `ci-verified`. Local Kit raised to 1.0.15.
- AGP_FINISH_OPEN_FOLLOWUP_V1 (COMMUNICATION_PROTOCOL 59): after #184 the Kit's follow-up #185 stayed open with red CI; main was clean and synchronized, Abschließen refused main and Wiederherstellen would only have reported the open pull request. Now the Lage offers and recommends Abschließen for exactly this case, with a closeout-only prompt.
- AGP_RECOVER_OFFER_CLEARS_V1: the Lage recommended „Wiederherstellen (nach dem letzten Task)“ in BEREIT after the interrupted Abschließen had been completed through the decision box; the R6 offer is now cleared on BEREIT, on DONE and when the decision continues the task.

## 2026-10-04 — main red after #190: the main follow-up prompt named Kit commands

- The push-to-main CI after #190/#191 (runs #599, #601) failed `test_new_goal_texts_name_no_kit_command`: the new main-only Abschließen prompt (AGP_FINISH_OPEN_FOLLOWUP_V1) named `transfer pr-closeout-complete` and `transfer post-merge-complete`, contrary to the T5 rule that goal texts name no Kit command (the remote LLM takes them from the command digest). The PR CI of #190 was green because it ran on a detached merge ref, where the branch-dependent prompt took the work-branch variant; locally the tests ran on a feature branch. My own test even required the command name.
- The remote side's repair on `fix/t5-finish-goal-wording` (PR #192) removed the names but also the chat-switch sentence of another prompt (f8403ac), then put `pr-closeout-complete` back (4fe4565); the owner stopped the run.
- Fix: the follow-up goal refers to "the Kit's closeout orchestrator from the command digest"; the chat-switch sentence is restored; the T5 test runs for branch `feat/demo` and `main` independently of the checked-out branch; the follow-up test asserts that no Kit command name appears. Lesson: test branch-dependent texts for every branch variant, and run the suite with an installed Kit.

## 2026-10-04 — PR #192/#193 merged; Kit 1.0.16 adopted

- „③ Abschließen“ of `fix/t5-finish-goal-wording` needed the owner twice: no Kit orchestrator publishes a locally committed fast-forward to a branch whose pull request already exists (KIT-GF-040; `pr-create-complete` hid the refused push behind the existing-PR lookup and failed on the old red CI), and `work finish` dry runs reported „PASS, Workflow completed.“ (KIT-GF-041), so the remote side asked for approvals three times. The owner pushed with `agentic-kit transfer push-current` in a terminal and answered the decision box with the orchestrator to use; step 1686 ran `pr-create-complete --post-merge-complete` (PR #192 merged as e7552e2, refresh #193 as 3ffa74a, main CI green). Lesson for my deliveries: a fix for a branch that already has a pull request is handed over uncommitted, not as a local commit.
- Kit 1.0.16 (Codex: KIT-GF-011, 026, 034, 036, 037, 038) retested in disposable clones (GF-E047–GF-E052): all six VERIFIED_FIXED. New: KIT-GF-042 — `workspace ci-update` would replace the Cockpit's customized CI (pytest and Playwright jobs) by the Kit template; the Cockpit keeps AGP_CI_GATE_V2 and pins 1.0.16 by hand. The command manifest changed (sha 9529749193c5); entrypoints synced with `commands sync-entrypoints`.

## 2026-10-04 — Kit 1.0.16 merged (#194/#195); Ablehnen ends the task, effects log kept, remote branch facts

- „③ Abschließen“ of `chore/kit-1.0.16`: step 1688 ran `pr-create-complete --post-merge-complete` (PR #194 merged as dd51ca0, refresh #195 as 9f3d200, main CI green, Lage BEREIT with post-merge-check PASS). The mission still ended STOPPED: the remote side needed more than 180 s for its final answer (thinking plus four analyses; 1689_agp_terminal.json appeared in the chat after the deadline) and the extension's fixed assistant wait (AGP_K07_ASSISTANT_WAIT_TIMEOUT_1360, 180 s from the send, `generation_active` observed False during the thinking phase) stopped the mission at 14:03:00. Nothing was lost; only the Cockpit's DONE verification did not run. Candidate fix (own slice): extend the wait while the assistant turn shows activity and let a timeout run the local completion verifier.
- AGP_REJECT_ENDS_TASK_V1 (COMMUNICATION_PROTOCOL 60): „Ablehnen“ ended in a continuation whose only answer was another question (step 1680). A rejection now ends the standard task locally.
- AGP_EFFECTS_LOG_CONTINUITY_V1: after that rejection the panel said „Freigegebene Wirkungen: noch keine ausgeführt“ although step 1676 had run `pr-create-complete`; the new decision record had replaced the log. The log of executed effects now survives later decisions of the same task. (The star on „Wiederherstellen“ after step 1676 was R6 as designed; the app then running predated #190.)
- AGP_REMOTE_BRANCH_FACT_V1: after the owner's push (steps 1684/1685) the facts still said only „has changes not in origin/main“; they now name origin/<branch> and whether local equals it, is ahead/behind or is unpublished.

## 2026-10-04 — Reject/effects/remote-branch fixes merged (#196/#197); assistant wait by activity

- „③ Abschließen“ of `fix/reject-ends-task`: step 1690 ran `pr-create-complete --post-merge-complete` (PR #196 merged, refresh #197 as 2e040bb, main CI green); DONE arrived in time and was CI-verified.
- AGP_K07_ASSISTANT_ACTIVITY_WAIT_V1 (COMMUNICATION_PROTOCOL 61): the fixed 180 s wait of step 1689 now counts from the last visible activity, with a 900 s maximum. The bridge log of the waits (K07_ASSISTANT_WAIT_OBSERVATION) showed `generation_active: false` together with a composer button labelled „Stoppen“ in every observation: the generation probe's selectors miss the current German ChatGPT UI. The probe that guards attachment completeness is unchanged (a false positive there would stall the loop); the stop-like button only extends the wait.
- AGP_LATE_COMPLETION_CHECK_V1: after such a timeout of „Abschließen“ the panel confirms the merged work from the repository (start commit in origin/main, Lage BEREIT, post-merge-check PASS) instead of recommending „Wiederherstellen“.
- Build release-0.1.0-r4, extension 0.4.3 (the extension reloads only on a new build id, AGP_EXTENSION_AUTO_REFRESH_V2).
