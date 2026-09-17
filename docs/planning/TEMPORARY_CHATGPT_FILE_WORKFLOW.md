# Temporary ChatGPT File Workflow

Status: **ACTIVE until Cockpit is both usable and explicitly chosen for the current work.**

This is the canonical human↔ChatGPT development transport while Cockpit is not being used.

## Required loop

1. ChatGPT supplies exactly one new Python assignment file per turn.
2. Its filename starts with the next unused monotonically increasing step number.
3. The human downloads/copies that file into `Download/`.
4. The human executes only:
   `python3 Download/run_next.py <step>`
5. The assignment must always emit a machine-readable JSON return bundle in `Download/`,
   including meaningful BLOCKED/FAIL outcomes whenever execution reached the assignment.
6. The human uploads that JSON return bundle to ChatGPT.
7. ChatGPT treats the uploaded return bundle as the authoritative result of the previous step
   and derives the next numbered assignment from it.
8. Additional bounded text evidence may be emitted when needed, but it is secondary; the JSON
   return bundle remains mandatory and must reference the evidence file.

## Anti-drift rules

- Do not replace this loop with ad-hoc shell commands, manual copy/paste command sequences,
  direct repository edits by the human, or a different transport merely because another path
  appears convenient.
- A task may internally run shell commands, tests, Git, or other deterministic tooling; those
  operations belong inside the numbered Python assignment.
- Never reuse a step number or filename.
- Prefer the largest safe coherent step instead of chains of tiny diagnostic assignments.
- Every assignment must support `--self-test` because `run_next.py` performs compile,
  self-test, then real execution.
- Every assignment must print and record the current `COMMAND_MANIFEST_ACK`.
- Product failures must remain fail-loud; do not fabricate recovery or widen authority.

## Exit condition

This workflow is **temporary**, not an architectural Cockpit requirement.

It ceases to govern a work item only when BOTH are true:
1. Cockpit is technically usable for that work item; and
2. the human explicitly chooses/wants Cockpit transport for that work item.

Until both conditions hold, this file workflow remains ACTIVE. A Cockpit test or a running
Cockpit instance by itself does not switch the development conversation to Cockpit transport.

When Cockpit transport is chosen, repository/Kit/Cockpit authority remains governed by the
normal canonical project documents; this temporary file is only a transport discipline.
