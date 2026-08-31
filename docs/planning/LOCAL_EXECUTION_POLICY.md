# Local Execution Policy

Status: normative project planning rule

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
