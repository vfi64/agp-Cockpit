# K07 / Cockpit — Stand und nächste Schritte (2026-10-01)

Adressat: Codex bzw. jede nachfolgende Entwicklungs-LLM. Normquellen bleiben
Code, Tests, `docs/planning/COMMUNICATION_PROTOCOL.md` (Punkte 11–17) und
`docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md`. Dieses Dokument fasst
zusammen; es ersetzt `K07_PROTOCOL_STATE_AND_NEXT_STEPS_2026-09-30.md`.

## 1. Live bestätigt

- **Chat wechseln** (Standard-Task): ein Auftrag, ein Schritt, lokal verifizierter
  Abschluss (`VERIFIED_COMPLETE`), auch im selben Chat.
- **Freier Auftrag mit Entscheidung** (Tab „Arbeiten“): lesende Vorprüfung →
  `<step>_agp_terminal.json` NEEDS_HUMAN → „Freigeben“/„Ablehnen“ →
  Fortsetzung im selben Chat.
- **Kit-Lebenszyklus mit Merge** (Schritte 1520–1532): eine Freigabe;
  ChatGPT wählte selbst `work finish`, `transfer pr-complete`,
  `post-merge-complete`, `admin-refresh-pr`, `sync-main`; PR #137 gemergt,
  Successor-Refresh #138, main `e375d60` grün. Das Cockpit hat den Abschluss
  selbst geprüft (`ci-verified`): PR gemergt mit der lokalen Arbeit `843cb5d`,
  main synchron, `agentic-kit transfer post-merge-check` PASS, main-CI grün.

- **Abschluss P2 + P3** (Schritte 1547–1556, Build `standard-tasks-20261001`):
  drei Freigaben für `transfer pr-create-complete`, `pr-complete`,
  `pr-closeout-complete`; CI von PR #141 zweimal rot (ein Test hing am
  `gh`-Login des Entwicklerrechners), von ChatGPT selbst repariert (`bd7e3e9`);
  PR #141 gemergt, Successor-Refresh #142, main `8d881c1`; Cockpit-Prüfung
  `ci-verified`. P1–P3 damit live bestätigt.

## 2. Mechanismen (Marker im Code)

| Marker | Datei | Wirkung |
|---|---|---|
| `AGP_K07_TERMINAL_REPLY_FILE_V1` | `core/terminal_reply.py` | Abschlussantwort als Datei, optional `"pr"` |
| `AGP_TASK_REPLY_POLICY_V1` | `core/task_reply_policy.py` | Remote-DONE nur bei Tasks ohne lokalen Vertrag |
| `AGP_KIT_COMMAND_CATALOG_V1` | `core/kit_command_catalog.py` | nur Manifest-Kommandos, kein git push/fetch/pull, Kit-Pflicht |
| `AGP_HUMAN_DECISION_V1` | `core/human_decision.py` | Freigabe/Ablehnung, aufgabengebunden, verfällt mit der Mission |
| `AGP_REMOTE_EFFECT_ASKS_HUMAN_V1` | `core/bridge_server.py` | Wirkung nach außen ohne Freigabe → NEEDS_HUMAN statt Abbruch |
| `AGP_CI_GREEN_COMPLETION_V1` / `AGP_CI_LIFECYCLE_COMPLETION_V2` | `core/ci_gate.py` | DONE erst nach lokal geprüftem GitHub-Zustand; Rückmeldung nennt Ziele, keine Kommandos |
| `AGP_EFFECT_REFUND_V1` | `core/ci_gate.py`, `bridge_server.py` | Lauf ohne Änderung an origin (Refs vorher/nachher) verbraucht keine Freigabe |
| `AGP_RESULT_PROJECTION_V1` | `core/result_projection.py`, `bridge_server.py` | ChatGPT erhält eine deterministische Kurzfassung jeder Rückgabe; Originale bleiben lokal |
| `AGP_DIGEST_COMPACT_V1` | `core/kit_command_catalog.py` | Befehlsverzeichnis: Orchestratoren vollständig, Rest als Tabelle (81 → 33 KB) |
| `AGP_TASK_CLOSE_ON_DONE_V1` | `core/task_store.py`, `bridge_server.py` | angenommenes DONE schließt den lokalen Task (`VERIFIED_COMPLETE` bzw. `REMOTE_DONE`) |
| `AGP_GH_BINARY_V1` | `core/ci_gate.py`, `tests/conftest.py` | kein Test hängt am `gh` des Rechners |
| `AGP_CI_GATE_V2` | `.agentic/ci/agentic-gate.yaml` | Push-Läufe nur auf main, Kit festgelegt, parallele Jobs, Pflicht-Check `agentic-gate` |
| `AGP_EXTENSION_AUTO_REFRESH_V2` | `bridge_server.py`, `content.js`, `background.js`, `app_bootstrap.py` | Handshake erzwingt einen Neustart je Ziel-Build; Extension merkt neue App binnen Sekunden |
| `AGP_DOWNLOAD_HYGIENE_V1` | `content.js`, `background.js`, `file_loop_runner.py` | Browser-Kopie nach angenommener Übernahme gelöscht; TMPDIR im Repo |
| `AGP_MAINTENANCE_CLEANUP_V1` | `core/maintenance.py`, Tab System | Aufräumen mit Vorschau und OK, inkl. Kit-`artifact-gc --tmp-logs` |
| `AGP_KIT_FINDINGS_VIEW_V1` | `core/kit_findings.py`, `ui/kit_findings_window.py` | Fenster „Kit-Befunde“ über das Greenfield-Register |
| `AGP_DIGEST_ONCE_PER_CHAT_V1` | `content.js` | Befehlsverzeichnis einmal je Chat und Manifest |
| `AGP_STALE_APP_GUARD_V1` | `core/build_freshness.py`, UI, `scripts/build_macos_app.py --restart` | veraltete laufende App startet keine Tasks |

## 3. Offene Befunde im Kit (nicht im Cockpit lösbar)

1. `--json` liefert kein reines JSON (`FINAL_SIGNAL=…`-Zeilen dahinter).
2. Kein lesendes Kit-Kommando für die CI eines Commits/Branches ohne PR
   (`pr status`/`wait-ci` brauchen eine PR-Nummer); das Cockpit nutzt dafür
   `gh run list`.
3. Das Manifest klassifiziert keine Wirkung nach außen; das Cockpit pflegt
   `REMOTE_EFFECT_COMMANDS`, `PUBLISHING_COMMANDS`, `MERGE_COMMANDS` selbst.
4. Kit-eigene volatile Dateien sind versioniert bzw. erzeugen Worktree-Änderungen
   (`.agentic/rule_ack/current.json` nach jedem Lebenszyklus; Handoff-Paket nach
   „Chat wechseln“).
5. `transfer pr-create` blockiert am Gate für frischen LLM-Kontext; die
   Orchestratoren sollten die Träger selbst auffrischen.
6. Eine Regelbestätigung veraltet, sobald sich eine Regelquelle auf main ändert
   (#134); der Push blieb blockiert, bis `rules acknowledge` lief.
7. Verwaltete CI-Vorlage (`.agentic/ci/agentic-gate.yaml` → `.github/workflows/agentic-gate.yaml`):
   `agentic-project-kit` und Testabhängigkeiten ohne festgelegte Version (jeder
   Lauf kann ein anderes Kit bekommen als das lokale 1.0.13); `push` und
   `pull_request` für alle Branches (doppelte Läufe); Playwright-Browser und apt
   bei jedem Lauf neu (Laufzeit 3–8 min bei gleichem Code, #490 vs. #491). Läufe
   über 300 s überschreiten die Standard-Wartezeit der Orchestratoren
   (`--timeout-seconds 300`). Vorschlag: Kit-Version festlegen, Push nur auf
   main, Browser-Cache mit Versionsschlüssel.
   Stand 2026-10-01: Cockpit-seitig mit `AGP_CI_GATE_V2` umgesetzt (Kit 1.0.13
   festgelegt, Push nur auf main, Browser-Cache, parallele Jobs). Bleibt für
   das Kit: die Vorlage selbst so ausliefern; es gibt kein Kit-Kommando, das eine
   geänderte Vorlage nach `.github/workflows/` überträgt (nur `workspace init`
   schreibt sie), und `workspace remove` entfernt laut eigener Beschreibung nur
   unveränderte Kit-Dateien — eine angepasste Vorlage blockiert es vermutlich
   (nicht ausprobiert).
8. Post-Merge-Refresh erzeugt eine weitere Refresh-Forderung: nach #140 schrieb das
   Kit `.agentic/state/status.md` erneut („refresh state after PR #139 …
   dd4a15d4“), lokal auf dem Rest-Branch `docs/post-pr139-handoff-refresh`.
   Das Cockpit fragte zu Recht vor `transfer post-merge-settle` (DESTRUCTIVE).
   Der Refresh sollte sich nicht selbst erneut als offen markieren.
9. Orchestratoren geben ihre gesamte Schrittausgabe als JSON-Text aus
   (`pr-closeout-complete`: 28 KB, `pr-create-complete`: 37 KB). Gewünscht:
   eine kompakte Zusammenfassung (`--summary` oder Standard) mit Ergebnis,
   nächster Aktion und nur den fehlgeschlagenen Schritten im Detail. Rückgabe-Code
   ≠ 0 bei rotem CI (Schritt 1551) macht aus einem fachlichen Befund einen
   Ausführungsfehler und kostete einen zusätzlichen Erholungsschritt.

Alle Befunde stehen auch im Greenfield-Register
(`docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json`, KIT-GF-023…028, plus
Nachträge zu 010/011/017) und im Fenster „Kit-Befunde“ (Tab System).

## 4. Nächste Schritte

1. Standard-Tasks als Lebenszyklus-Verben und Repo-Wechsel: Arbeitsplan P1–P11
   in `docs/planning/MASTER_PLAN.md`, Abschnitt „2026-10-01 — Standard tasks as
   lifecycle verbs, repository switch“.
2. D5 (Generierungserkennung) bleibt Risiko; Live-Belege sammeln.
3. Kit-Befunde aus Abschnitt 3 im Kit-Repository bearbeiten.
