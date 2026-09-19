# Protocol Change and Failure Log
Durable engineering memory; normative semantics remain in planning protocol authorities.

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
