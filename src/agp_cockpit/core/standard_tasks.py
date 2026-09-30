from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StandardTask:
    """A stable, user-facing task template backed by a local contract."""

    key: str
    label: str
    description: str
    contract_factory: Callable[[Path], dict]
    prompt_factory: Callable[[Path], str]

    def contract(self, repository_root: Path) -> dict:
        return self.contract_factory(repository_root.expanduser().resolve())

    def prompt(self, repository_root: Path) -> str:
        return self.prompt_factory(repository_root.expanduser().resolve())


def _chat_switch_contract(repository_root: Path) -> dict:
    return {
        "title": "Standard Task: Chat wechseln",
        "goal": (
            "Create and validate a complete successor handoff package for the "
            "currently configured repository without starting further product work."
        ),
        "repository_root": str(repository_root),
        "completion_contract": {"kind": "verified-successor-handoff-v1"},
        "acceptance_criteria": [
            "The canonical successor handoff package is generated.",
            "All required handoff files exist and validation_report.json is PASS.",
            "A detailed successor prompt is produced with absolute paths.",
            "No further development work starts after a PASS result.",
        ],
        "constraints": [
            "Use the repository's current Agentic Project Kit authority and contracts.",
            "The local authority must explicitly allow both git and agentic-kit.",
            "Do not change product files during handoff preparation.",
            "Fail closed on missing or invalid handoff evidence.",
        ],
    }


def _chat_switch_prompt(repository_root: Path) -> str:
    return f"""CHAT SWITCH STANDARD TASK

Prepare a complete, validated successor handoff for the Agentic Project Kit-managed repository at:
{repository_root}

This is a standard Cockpit task. Use the repository's current authoritative Kit route for chat switching. Prefer the installed route `agentic-kit transfer chat-switch-complete --json` when it is available; consult the current command authority only when that route is unavailable or fails.

Complete the handoff in one coherent local work order whenever possible. Capture the current branch, HEAD, worktree, installed Kit version, development state, open risks, established decisions, relevant runtime and log paths, and the next safe step. Generate the canonical successor package and verify these files:

- execution_contract.json
- successor_context.yaml
- validation_report.json
- source_manifest.json
- successor_prompt.md

Evaluate validation_report.json and continue only when it is PASS. Create a separate continuation brief only for repository-specific or volatile information that does not belong in the canonical package. Create a detailed start prompt containing the absolute repository path, absolute package and file paths, required reading order, current state, next step, diagnostics, and the rule that the successor must make no repository changes during initial handoff intake.

Pass on the communication contract: exactly one newly numbered Download/*.py work order per local step, no reused number, execution through run_next.py, exactly one canonical *_return_bundle.json per execution, complete result evaluation before the next work order, and large coherent steps.

The attached Python file is the executable local work order. It must execute the authorized Kit command during its real run (for this task: `agentic-kit transfer chat-switch-complete --json`), capture its return code/stdout/stderr, validate the required handoff files and validation report, and write exactly one canonical return bundle into Download/. Printing a JSON object that merely describes an argv/cwd command is not execution evidence and is an invalid work order. `--self-test` must validate structure without running the Kit command or mutating the repository.

Keep the attached Python work order deliberately small: at most 80 source lines and 16 KiB, with no long comments, embedded logs, recursive Download scans, or prose outside the attachment. Before attaching it, verify that the complete file parses, has a `main()` plus `if __name__ == "__main__"`, accepts `--self-test`, executes the Kit command during the real run, and writes the one return bundle. A truncated or incomplete attachment is worse than a short diagnostic response and must not be submitted.

Write exactly one canonical JSON completion result into the local return bundle for this standard task. It must include PASS, BLOCKED, or FAIL; package path; validation status; continuation-brief path; detailed-start-prompt path; and next action. The Cockpit independently validates a successful package and ends this task after confirmed result delivery. When asked to acknowledge the final result, acknowledge only; do not produce another work order. Visible JSON is not an executable command or completion authority. On PASS, do not start further development in this chat.
"""


STANDARD_TASKS: tuple[StandardTask, ...] = (
    StandardTask(
        key="chat-switch",
        label="Chat wechseln",
        description="Erzeugt und validiert den vollständigen Nachfolge-Handoff.",
        contract_factory=_chat_switch_contract,
        prompt_factory=_chat_switch_prompt,
    ),
)


def standard_tasks() -> tuple[StandardTask, ...]:
    return STANDARD_TASKS
