## Machine-readable execution contract

The markdown successor prompt is a compact projection. The machine-readable files take precedence.

Read first: `execution_contract.json`, `successor_context.yaml`, `validation_report.json`, and `source_manifest.json`.

## Durable agentic-kit operating model

- scope: `durable-agentic-kit-operating-model`
- agentic-kit provides the operating-layer control plane for this external workspace.
- Use the workspace manifest, external status/handoff files, registries, check/doctor, repo-status, and successor handoff package as active Kit subsystems.
- Target-repository product behavior remains project-owned; native tests and docs stay authoritative for product correctness.
- GC is technical retention, not semantic documentation migration.

Source authorities:
- `.agentic/config.yaml`
- `.agentic/state/status.md`
- `.agentic/state/handoff/README.md`
- `.agentic/registries/documentation.yaml`
- `.agentic/registries/rules.yaml`

Critical rule IDs:
- `local-copy-paste-protocol` (critical)
- `strict-start-decision` (critical)
- `bootstrap_acceptance_gate` (critical)
- `wrapper-first-complete-development-cycle` (critical)
- `successor-package-not-prompt-only` (critical)
- `documentation-authority-model` (critical)
- `repo-backed-rules-and-gates` (critical)
- `gc-retention-not-document-migration` (critical)
- `ns-legacy-not-active-control-plane` (critical)
- `generated-handoff-projection-update-policy` (critical)
- `successor-final-head-identity` (critical)
- `patch-cycle-diagnostic-gate` (critical)
- `copy-paste-output-discipline` (critical)
- `protected-file-preservation` (critical)

## Current continuation state

- branch: `docs/post-pr268-successor-package-refresh`
- head_matches_origin_main: `True`
- worktree_clean: `True`
- open_tasks_source: `docs/planning/PROJECT_DIRECTION.yaml`
- document_registry_source: `.agentic/registries/documentation.yaml`
- Current state is volatile continuation data, not a durable rule source.

## Wrapper-first complete development cycle

External workspace lifecycle: read target-repo authority files -> use a feature branch or local smoke branch -> run native tests plus `agentic-kit check --root .`, `agentic-kit doctor --root .`, and `transfer repo-status` -> inspect diffs -> refresh successor handoff package for chat switches.

`transfer post-merge-check` and `rules acknowledge` are self-hosting/post-merge gates unless the external repository has explicitly adopted their required sources and branch preconditions.

## Handoff package precedence

- prompt_is_projection_only: `True`
- machine_readable_files_take_precedence: `True`
- source_of_truth: `generator_and_machine_readable_successor_package`
- generator_command: `agentic-kit transfer prepare-successor-handoff --render-prompt`
- Markdown handoff files and latest package files are generated projections; update generator/contract/rule sources first, then regenerate projections.
- Forbidden update path: manual direct edits to generated handoff projections as the primary source of new rules.
- Do not use stale copied prompt text or `NEW_CHAT_HANDOFF_PROMPT.md` as sole authority.

## Patch-cycle diagnostic gate

After one failed patch, exactly one direct correction is allowed. After a second failure in the same patch family, stop mutations, run bounded diagnosis, classify product bug versus test-model bug, and record `next_mutation_allowed`.

## Local copy-and-paste protocol

Use exactly one complete Bash block per local action. The block must start by changing into the repository root, write verbose output to `~/Downloads/*.log`, and end by printing `LOG=...` and `RC=...`.

Chat output after local blocks should be only `LOG=...` and `RC=...`; large diagnostics belong in compact JSON summaries or log files.

Forbidden local-command patterns: loose command fragments, manual editor instructions, naked `python`, naked `pytest`, `git add .`, `{ ... } > "$OUT" 2>&1` as the recommended logging pattern, `cat` of whole diagnostic files, and unbounded grep over reports/outbox/generated logs.

# Successor Chat Prompt

Du bist ein neuer LLM-/Coding-Chat für das Repo `vfi64/agp-Cockpit`.

Arbeite nicht aus Chat-Erinnerung. Quelle der Wahrheit ist der aktuelle Remote-Stand von `main`, der lokale Repo-Zustand, repo-/log-backed Evidenz und das maschinenlesbare Successor-Paket.

## Pflichtstart

```bash
cd /path/to/
git branch --show-current
git status -sb
git status --short
agentic-kit transfer repo-status
agentic-kit check --root .
agentic-kit doctor --root .
```

## Zuerst lesen

- `.agentic/state/handoff/packages/latest/successor_context.yaml`
- `.agentic/state/handoff/packages/latest/source_manifest.json`
- `.agentic/state/handoff/packages/latest/validation_report.json`
- `.agentic/state/handoff/packages/latest/execution_contract.json`
- `.agentic/state/handoff/NEXT_CHAT_BOOTSTRAP.md`
- `.agentic/state/handoff/START_NEW_CHAT_PROMPT.md`
- `.agentic/state/handoff/CLOSEOUT_BEFORE_CHAT_SWITCH_PROMPT.md`
- `docs/reference/AGENTIC_KIT_COMMANDS.md`
- `docs/reference/agentic-kit-commands.json`

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

## Aktueller Paketstand

```json
{
  "open_tasks": [
    {
      "files": [
        ".agentic/state/status.md",
        ".agentic/state/handoff/README.md"
      ],
      "id": "external-workspace-no-project-direction",
      "status": "review",
      "summary": "No Kit project-direction file is required for this external workspace; continue from .agentic/state/status.md and .agentic/state/handoff/README.md."
    }
  ],
  "recent_lessons": [
    "The old prepare-successor-handoff mechanism is not sufficient as a standalone chat-switch source.",
    "Successor handoff must combine repo-backed long-term context with explicit short-term local work state.",
    "Generated prompt files must be deterministic projections, not accumulative append targets.",
    "Stale prompt markers, literal backslash-n artifacts, and old current-state PR anchors must block handoff trust.",
    "The copy prompt must be usable by other LLMs, not only ChatGPT.",
    "After v0.4.9, release metadata preparation must have one supported agentic-kit route before manual-metadata gates are tightened.",
    "release_publish_core must not remain able to execute removed ./ns release routes after the ns entrypoint removal."
  ],
  "repo": {
    "branch": "docs/post-pr268-successor-package-refresh",
    "full_name": "vfi64/agp-Cockpit",
    "head": "e70c5ea75673cc0bbb22c06172f2c7a5e72e1859",
    "head_matches_origin_main": true,
    "head_short": "e70c5ea7",
    "local_path": "cd /path/to/",
    "origin_main": "e70c5ea75673cc0bbb22c06172f2c7a5e72e1859",
    "origin_main_short": "e70c5ea7",
    "worktree_clean": true
  }
}
```

## Arbeitsregeln

- Deutsch, knapp, direkt.
- Keine langen Terminalausgaben in den Chat ziehen.
- Große Ausgaben nach `~/Downloads/*.log` umleiten und nur `LOG=...` posten.
- Vor Commit: tatsächlichen Diff inspizieren, Tests laufen lassen, protected-diff-plan ausführen.
- Bei `BLOCK` oder `FAIL`: sofort stoppen, Diagnose statt Weiterarbeiten.
- Aktive Aufgaben stammen aus `docs/planning/PROJECT_DIRECTION.yaml`; wenn diese Datei in einem externen Workspace fehlt, gelten Status- und Handoff-State als Fortsetzungsquelle.
- Allgemeingültige Regeln stehen in `execution_contract.json.general_contract`; aktueller Fortsetzungspunkt steht in `execution_contract.json.current_state_contract` und `successor_context.yaml`.
- `successor_prompt.md` ist nur Projektion. Maschinenlesbare Dateien haben Vorrang.
- Komplexe `agentic-kit`-Wrapper haben Vorrang vor selbstgebauten Git-/GitHub-/Handoff-/GC-/Release-Blöcken.
- Garbage Collector nur für technische Retention verwenden, nicht für semantische Dokumentenmigration.

## Nächste sichere Entscheidung

1. Wenn `validation_report.json` nicht PASS ist: Handoff-Projektion reparieren.
2. Wenn der Arbeitsbaum dirty ist: nur explizite WIP-Dateien prüfen und abschließen oder sauber dokumentieren.
3. Danach die nächste aktive Aufgabe aus `docs/planning/PROJECT_DIRECTION.yaml` oder dem externen Workspace-State bearbeiten.
