# Communication Failure Analysis: 1457/1458/1459

Date: 2026-09-20

## Executive Summary

The previous failures were caused by three independent gaps in the delivered
desktop path:

1. The ChatGPT attachment preview remained open after the Python file was
   selected. The bridge then tried to send the continuation prompt while the
   preview dialog still owned focus. The browser-side send failed with
   `INSERT_NOT_VERIFIED` and the active control was the dialog `OK` button.
2. The failed 1457 file was accepted again as a retry even though it was not a
   newer command. That replay produced `remote command step 1457 is not newer
   than persisted step 1457`, after which the mission entered `BLOCKED`.
3. After the first 1458 rejection, the content script did not advance its
   assistant baseline. The same visible attachment was therefore treated as a
   new assistant answer once per polling tick. The replay path incremented the
   turn counter and eventually surfaced `TypeError: Failed to fetch`.

Because the mission was terminally blocked, the later 1458 file was generated
in the chat but could not be consumed by the bridge. In the later 1458 run, the
same invalid attachment was re-ingressed repeatedly until the user aborted at
turn 27. This explains the visible combination of a remote file, no local
execution, no new handoff package, no upload, and the final fetch error.

## Proven Trace

Mission: `3c605e2a-d6aa-4529-8f41-283ecd930839`

- 12:40:31 UTC: attachment 1457 observed.
- 12:40:33 UTC: attachment fetched and accepted by the local bridge.
- 12:40:35 UTC: automatic continuation prompt failed with
  `INSERT_NOT_VERIFIED`; the active element was a dialog `BUTTON` labelled
  `OK`, while the composer was a contenteditable `DIV`.
- 12:40:36-12:40:37 UTC: 1457 was processed again. The persisted-step guard
  rejected it because step 1457 was not newer than step 1457.
- The mission became `BLOCKED`. A subsequently generated 1458 could not be
  consumed by that terminal mission.

The complete rotated source logs remain in
`.local/agp-cockpit/logs/bridge.log*`. A chronological combined copy for this
incident is written to the local `Download` directory.

### 1458 replay-storm trace

The first 1458 observation at `2026-09-20T16:31:56Z` was a real, non-replayed
attachment. The local preflight correctly rejected it because the file lacked
the required `__main__` guard, `--self-test`, and return-bundle contract. From
`16:31:59Z` onward, the same attachment was accepted with `replayed: true`
roughly once per second. Each replay advanced the visible turn state even
though no new continuation was sent. The user stopped the mission at turn 27.

This is distinct from the local command-file failure: 1458 was not supposed to
create a handoff package because its semantic preflight failed. The defect was
that the already-rejected visible attachment was not suppressed at the UI
ingress boundary.

### 1459 local preflight and blocked recovery

The next run reached the local machine correctly. The downloaded file was
`Download/1459_chat_switch_standard_task.py`, and the runner created the
step-scoped return bundle and `Download/__run_next_output.txt`. The file was
not executable under the local contract: it had a `main()` function and wrote
some evidence, but it did not contain an executable `if __name__ ==
"__main__":` guard and did not register an argparse `--self-test` argument.
The exact preflight result was:

```text
RUN_NEXT_PRECHECK_FAILED
- missing __main__ execution guard
- missing --self-test contract
```

Therefore `run_next.py` was intentionally not started and no new canonical
handoff package could be produced. The unchanged files in
`.agentic/state/handoff/packages/latest` are expected evidence for this
failed step, not proof that the handoff command ran.

The recovery continuation then exposed the remaining browser transport defect.
The attachment preview reported `K07_ATTACHMENT_PREVIEW_CLOSED`, but the
active element was still the preview dialog's `OK` button. CDP inserted into
the composer while focus ownership was not verified, and the continuation
could not be committed. This made a correctly diagnosed local failure look
like a missing handoff.

Repair: the content script now restores and verifies composer focus after the
preview disappears, and the background native transport refuses
`Input.insertText` unless the debugger context independently verifies the
composer as `document.activeElement`. The rejection includes the active and
composer identities for diagnosis. The next recovery file must still be a new
numbered Python attachment satisfying the local command contract; the bridge
must not silently manufacture a handoff package from 1459.

## Implemented Corrections

- The attachment reader now closes the preview dialog through its visible
  controls, falls back to Escape, waits for disappearance, and fails closed if
  the dialog remains visible.
- The command-file retry rule now permits a retry only when the incoming
  numbered file is strictly newer than the persisted step. Identical or older
  files are treated as replays and are not executed again.
- The content ingress now keys an assistant attachment by message, filename,
  URL, and normalized response text. It records that key before processing,
  captures a fresh assistant baseline after a real continuation, and treats
  replayed or terminal command-file results as non-progressing states. The
  same visible attachment can no longer consume turns once per poll.
- Runtime and extension identities are explicit and correlated:
  - application: `0.1.0.dev3`
  - extension: `0.3.9`
  - bridge/extension build: `composer-focus-guard-20260920`
- The staged extension marker records the source bundle, repository root,
  `Download` directory, `run_next.py` path, version, build ID, and SHA-256.
- The running Chrome extension was reloaded from the rebuilt application and
  visibly reported `v0.3.9` and `CONNECTED READY`.

The authoritative production handshake is
`~/Library/Application Support/AGP Cockpit/bridge/extension.json`; it now
reports version `0.3.9` and build `composer-focus-guard-20260920`. The
older repository-local `.local/agp-cockpit/bridge/extension.json` is not the
production runtime path and may retain historical evidence from earlier
development launches.

## Verification

- Full Python test suite: PASS.
- Ruff: PASS.
- JavaScript syntax checks for content, background, and native transport:
  PASS.
- `git diff --check`: PASS.
- `agentic-kit check-docs`: PASS.
- `agentic-kit doctor`: PASS. Optional external-workspace warnings are
  informational and do not affect the result.
- Focused replay/ingress regression tests after the 1458 analysis: 18 passed.
- Focused attachment-close, native-send, command-ingress, and file-loop tests
  after the 1459 analysis: 31 passed.

## Remaining Acceptance Boundary

The local implementation and delivered runtime path are verified. A new live
ChatGPT mission must still be run to provide end-to-end evidence that a fresh
numbered attachment is downloaded, executed, produces a new handoff package,
and is uploaded. The test must start from the visible `0.3.9` extension and
application build `composer-focus-guard-20260920`; otherwise the evidence
does not identify this fix. The generated `1458` file itself is not a valid
acceptance fixture because its own contract preflight fails.
