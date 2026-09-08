# NEXT CHAT BOOTSTRAP

This file is a deterministic projection of `.agentic/state/handoff/packages/latest/successor_context.yaml`.
Do not start from chat memory. Read the Successor Handoff Package first.

## Current verified repository state

- Repo: `vfi64/agp-Cockpit`
- HEAD: `796211ad14c31c9b3f769610a1cb56cebcc62bf4` (`796211ad`)
- Handoff freshness marker: `796211ad`
- Branch at generation: `docs/greenfield-gf019-transfer-archive-volatile`
- Worktree clean at generation: `False`

## Successor handoff package

- `.agentic/state/handoff/packages/latest/successor_context.yaml`
- `.agentic/state/handoff/packages/latest/source_manifest.json`
- `.agentic/state/handoff/packages/latest/validation_report.json`
- `.agentic/state/handoff/packages/latest/successor_prompt.md`

## Canonical chat-switch prompt files

- Start a successor chat with `.agentic/state/handoff/START_NEW_CHAT_PROMPT.md`.
- Before leaving a chat, run the closeout routine in `.agentic/state/handoff/CLOSEOUT_BEFORE_CHAT_SWITCH_PROMPT.md`.

## Bootstrap-Akzeptanzbremse

Zusätzliche Startbremse nach dem Bootstrap:

Nach Ausführung des Bootstrap-Blocks darfst du nicht sofort mit neuer Arbeit beginnen. Werte zuerst ausschließlich das Bootstrap-Log aus.

Prüfe:
- `validation_report.json PASS`
- `execution_contract.json` wurde gelesen
- Worktree clean oder nur ausdrücklich benannte WIP-Dateien
- `repo-status PASS`
- `agentic-kit check --root .` PASS
- `agentic-kit doctor --root .` Overall PASS
- Jeder `WARN` ist als Risiko, optionaler Fremdrepo-Bestandteil oder erklärter Skip eingeordnet

Gib danach genau eine kurze Statusentscheidung aus:

- `Übergabe akzeptiert, keine Admin-Arbeit nötig.`

oder:

- `BLOCK: ...` mit konkretem Grund aus dem Log.

Beginne erst nach dieser Statusentscheidung mit neuer Arbeit.

In einem externen Workspace sind Kit-interne Rule-Snapshot- und Post-Merge-Main-Gates keine Pflichtstart-Gates. Nutze `transfer post-merge-check` erst nach einem tatsächlichen PR-Merge auf `main`.

## Required first action in a successor chat

1. Read the Successor Handoff Package files completely.
2. Run or request the Pflichtstart commands from the package.
3. Verify current main HEAD, local status, open PRs, CI, STATUS, CURRENT_HANDOFF, rule registry, command reference, and final-summary contracts before mutation.
4. If the package, prompts, HEAD, or validation report are stale: stop and repair handoff drift first.

## Open high-priority work

Source: `docs/planning/PROJECT_DIRECTION.yaml` or external workspace state.

- `external-workspace-no-project-direction` (review): No Kit project-direction file is required for this external workspace; continue from .agentic/state/status.md and .agentic/state/handoff/README.md.

### RESULT: PASS ###
