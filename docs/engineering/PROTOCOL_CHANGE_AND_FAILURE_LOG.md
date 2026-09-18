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
