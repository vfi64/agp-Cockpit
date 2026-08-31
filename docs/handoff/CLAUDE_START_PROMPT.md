# Claude Start Prompt — AGP Cockpit

Work only in `vfi64/agp-Cockpit`.

Your first responsibility is not feature development. Establish and verify the repository's governed development baseline.

## Bootstrap

Read `CLAUDE.md` first, then follow its mandatory first-read order. Treat `AGENTS.md`, current repository evidence, and the current Agentic Project Kit contract as authoritative. Do not work from chat memory.

## Immediate objective

Complete the smallest safe Phase-0 slice from `docs/planning/MASTER_PLAN.md`:

1. inspect exact repository identity, branch, HEAD, remote, and worktree state;
2. discover the currently installed/current Agentic Project Kit version and command surface;
3. verify the highest-level external-repository onboarding/intake orchestrator currently available;
4. prepare the maintainer's local work as an executable Python script, not a loose shell recipe;
5. use the current high-level Kit intake/adoption path rather than recreating it with lower-level commands;
6. do not execute irreversible or ambiguous mutation without verified preconditions;
7. once Kit governance is bootstrapped, establish the initial CI/test/gate baseline before product feature work.

At the planning baseline, the expected high-level path begins with `agentic-kit workspace dpa-intake`, followed by the current adoption/init path, but you must verify the live Kit command surface rather than assuming remembered syntax.

## Local-script requirement

The maintainer should be able to run one Python file for the local Phase-0 operation. The script must perform preflights, explain what it is doing, stop on ambiguity, preserve useful logs/evidence, and return meaningful exit codes. It may call Git and Agentic Project Kit commands internally.

## Product constraints to preserve

Do not redesign these without an ADR and evidence:

- Python product implementation;
- Tkinter GUI for the initial product line;
- macOS first runtime;
- portable clean/hexagonal core with OS-specific adapters;
- no local-LLM development decisions;
- Hermes/Qwen, if retained, is mechanical transport only;
- browser LLM is the reasoning/development layer;
- Agentic Project Kit remains workflow/safety authority.

## Gate requirement

Before declaring the Phase-0 slice complete, identify and run all applicable local tests and Kit gates, then verify remote CI for the exact commit once CI exists. A local success without required remote CI/gates is not DONE.

If CI does not yet exist, the next slice must create the minimal CI baseline before importing or refactoring the legacy Ollama/Hermes GUI.

## Stop conditions

Stop and report `BLOCKED` rather than improvising if:

- repository identity is ambiguous;
- branch/HEAD/worktree state is unsafe;
- current Kit commands differ materially from the planning assumptions;
- a Kit gate returns `BLOCKED` or `FAIL`;
- the proposed path would require bypassing a higher-level Kit workflow;
- a mutation would require inventing Kit-owned state or transfer files.

At the end, leave repository-backed handoff evidence using the current canonical Kit mechanism when available.
