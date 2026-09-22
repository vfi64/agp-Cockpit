# Protocol Change and Failure Log
Durable engineering memory; normative semantics remain in planning protocol authorities.

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
