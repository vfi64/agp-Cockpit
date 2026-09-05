# Local Execution Policy

Status: active
Status-date: 2026-08-31
Decision status: accepted
Review policy: on material change

## Purpose

All maintainer-local work instructions for AGP Cockpit are delivered as executable Python scripts rather than loose terminal command sequences once a script can reasonably express the operation.

This rule exists to make local work reproducible, reviewable, testable, and less dependent on shell history or manual copy/paste.

## Rules

1. Local maintainer actions are provided as Python scripts with explicit preflight checks, bounded side effects, clear exit codes, and useful error messages.
2. Scripts MUST prefer current high-level Agentic Project Kit orchestrators over reconstructed chains of primitive commands whenever the Kit exposes an appropriate orchestrator.
3. Kit command names and semantics MUST be taken from the current Kit contract/repository/package, not reconstructed from chat memory.
4. Mutating Kit operations SHOULD remain dry-run/read-only until the script has established preconditions and, where appropriate, obtained explicit maintainer confirmation.
5. Scripts MUST fail closed when repository identity, branch/HEAD expectations, required executables, or Kit state are ambiguous.
6. Scripts MUST print the exact repository path and relevant command/result state before and after mutations.
7. Shell subprocesses may be invoked from Python when required, but shell composition is an implementation detail inside a bounded script, not the user-facing workflow.
8. Local scripts SHOULD be written so that OS-specific behavior is isolated in small helper functions and can later move behind platform adapters.
9. CI and Kit gates remain authoritative. A local script completing successfully does not make a development slice complete unless the required local tests, remote CI, and Kit gates are green for the exact commit.

## Product implementation rule

AGP Cockpit itself is a Python desktop GUI application using `tkinter` as the initial and preferred GUI toolkit.

The GUI layer MUST NOT contain operating-system commands, browser automation details, Kit subprocess construction, Git logic, or persistence implementation. It calls application use cases through ports/interfaces.

The initial implementation target is macOS. Portability is preserved through platform adapters so Windows or Linux support can later be added without replacing the core/application layers.

## Agentic Project Kit usage hierarchy

When multiple Kit surfaces can perform the same intended workflow, development and maintenance scripts prefer the highest-level current orchestrator that preserves required evidence and safety semantics.

Conceptually:

```text
current Kit orchestrator
    > current Kit workflow wrapper
    > current Kit primitive
    > custom shell/git/gh logic
```

A lower-level mechanism is used only when the higher-level current surface is unavailable or semantically inappropriate, and that choice must be documented when it affects workflow safety or evidence.

## Mandatory terminal completion banner

Every local maintainer script MUST terminate with a clearly delimited result
banner, including PASS, BLOCKED, and FAIL paths. The required visual form is:

```text
=======================================================================
=======================================================================
=== <STEP RESULT TITLE> ===
=======================================================================
=======================================================================
```

The title must reflect the real outcome. The banner is part of the local
execution contract and must be emitted even when an exception is raised or a
Kit command returns BLOCKED/FAIL. This makes long terminal transcripts
unambiguous and easy to return to the development LLM.

## Cockpit development execution discipline

These rules are project-owned execution conventions. They supplement the Agentic Project Kit
control plane and MUST NOT duplicate, weaken, replace, or reinterpret Kit-owned lifecycle,
repository, Git/GitHub, transfer, gate, or handoff rules. Where a Kit command contract or rule
conflicts with this section, the Kit-owned contract wins.

1. Work in coherent vertical slices of useful size. Avoid both unnecessary micro-steps and
   uncontrolled multi-subsystem mutations.
2. User-facing maintenance/development actions are delivered as uniquely numbered Python scripts
   under `Download/` and are executed through `python3 Download/run_next.py <step>`.
3. Never reuse a generated script filename. Every new script must have a unique name and should
   support `py_compile` plus a bounded `--self-test` where practical.
4. `run_next.py` is the execution harness. Its captured output is treated as bounded evidence and
   the latest run output is overwritten intentionally.
5. For a new or not-yet-proven Kit command/data contract, use:
   `INSPECT CONTRACT -> DRY-RUN -> VALIDATE MACHINE-READABLE PLAN -> EXECUTE -> VERIFY`.
6. Dry-run and execute must describe the same intended operation, including merge/review mode,
   selected paths, branch, title/message, and other safety-relevant options.
7. Prefer the highest-level current Kit wrapper that preserves the required lifecycle semantics.
   Do not manually rebuild Git/GitHub/FILE_TRANSFER lifecycle logic that the Kit already owns.
8. After two unexpected failures in the same family, stop mutation and perform bounded diagnosis
   before another repair attempt.
9. Classify failures explicitly as `VALIDATION/ASSISTANT ERROR`, `KIT UX/CONTRACT IMPROVEMENT`, or
   `KIT DEFECT`. An assistant-script defect is never recorded as a Kit defect.
10. Qualifying Kit findings discovered during Cockpit development belong in the canonical
    Greenfield findings ledger, but Kit-side improvement work must not unnecessarily derail the
    Cockpit product slice.
11. Restore known volatile Kit state only through the supported
    `agentic-kit transfer restore-known-volatile` path.
12. Substantive PR closeout and post-merge successor/handoff refresh are distinct lifecycle
    stages. Use the current high-level Kit closeout wrapper rather than composing them manually.
13. Generated handoff prompts are projections. Machine-readable successor-package files and
    durable project-owned planning sources take precedence.
14. Prefer deliberate chat switches at stable phase/slice boundaries. Before switching chats,
    create and validate a Kit successor handoff package and provide a detailed copy/paste prompt.
