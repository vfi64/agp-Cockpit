---
schema_version: 2
artifact_type: chat_switch_prompt
role: start_new_chat
current_handoff_marker: 0f570b22
current_branch_at_generation: work/phase0-agentic-workspace-bootstrap
canonical_bootstrap: .agentic/state/handoff/NEXT_CHAT_BOOTSTRAP.md
successor_context: .agentic/state/handoff/packages/latest/successor_context.yaml
paired_prompt: .agentic/state/handoff/CLOSEOUT_BEFORE_CHAT_SWITCH_PROMPT.md
must_update_together:
  - .agentic/state/handoff/START_NEW_CHAT_PROMPT.md
  - .agentic/state/handoff/CLOSEOUT_BEFORE_CHAT_SWITCH_PROMPT.md
  - .agentic/state/handoff/NEXT_CHAT_BOOTSTRAP.md
required_terms:
  - successor_context.yaml
  - source_manifest.json
  - validation_report.json
  - agentic-kit transfer chat-switch-complete
  - AGENTS.md
  - README.md
  - SECURITY.md
  - FINAL_SUMMARY_CONTRACT.md
  - handoff_state.yaml
  - compiled_agent_context.yaml
  - Rule Registry
  - boot write
  - PASS_ALREADY_DONE
  - d/f
  - red CI
---

# Start New Chat Prompt

Current handoff marker: `0f570b22`.

Copy `.agentic/state/handoff/packages/latest/successor_prompt.md` into the successor chat.

The successor chat must treat the Successor Handoff Package as the short-term handoff and the repository files listed in `source_manifest.json` as long-term truth.

If the package validation is not PASS, or if HEAD/local status differs from the package without explanation, stop and repair handoff drift first.

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
