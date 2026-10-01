# K07 File-Loop-Protokoll — Stand, Änderungen, Folgerungen (2026-09-30)

> Abgelöst durch `K07_STATE_AND_NEXT_STEPS_2026-10-01.md` (D1–D4, D7 repariert und live bestätigt).

Adressat: Codex bzw. jede nachfolgende Entwicklungs-LLM. Quelle der Wahrheit
bleiben Code, Tests, `docs/planning/COMMUNICATION_PROTOCOL.md` und
`docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md`. Dieses Dokument ist eine
Arbeitszusammenfassung, keine neue Normquelle.

## 1. Live-belegter Stand (Mission `4abfe28e`, 2026-09-30 11:43–11:47 UTC)

Extension `0.3.15` / `expected-step-attachment-20260930`, Bridge
`send-commit-nonce-delivery-state-20260929`.

| Grenze | Ergebnis | Evidenz (bridge.log / Download) |
|---|---|---|
| Veraltete Karte 1475 reservieren | OK | `K07_REMOTE_STEP_RESERVED step=1475 reason=visible-unmaterialized-remote-attachment` |
| Bootstrap senden (Commit) | OK | `NATIVE_USER_TURN_COMMITTED`, `NATIVE_SEND_ACCEPTED` in < 1 s |
| Antwortgrenze erkennen | OK | `K07_ASSISTANT_ATTACHMENT_OBSERVED 1476_chat_switch_standard_task.py` |
| Browser-Download + Provenienz | OK | `download_bytes 4306 == chars 4306`, `~/Downloads/1476_…py` |
| Vertragsprüfung + Annahme | OK | `K07_COMMAND_ACCEPTED sha256 8b0105…` |
| Ausführung genau einmal | OK | `1476_run_next_output.txt`: py_compile rc0, self-test PASS, real run rc0, RUN_NEXT PASS |
| Ergebnisbündel | OK | `1476_…_return_bundle.json`: status PASS, Kit rc 0, validation PASS, generated_head = HEAD |
| **Ergebniszustellung** | **FEHLER** | `TICK_ERROR ChatGPT file input did not confirm the selected result evidence files`; Dateien liegen sichtbar im Composer, Prompt nicht gesendet |
| **Fertig-Erkennung** | **nicht erreicht** | Turn 0/40, danach `K07_ASSISTANT_RESPONSE_TIMEOUT` |

DOM-Befund aus `K07_ASSISTANT_WAIT_OBSERVATION`: `role_any=0`, `role_assistant=0`,
`message_ids=0`, `turn_articles=0`, `testid_turns=0`; Autorenüberschriften
`du hast gesagt:` / `chatgpt hat gesagt:` vorhanden; Dateikarten tragen
`aria-label="Vorschau von <name>.py öffnen"`; `stop_like_buttons=[]` und
`generation_active=false`, obwohl ChatGPT 46 s „nachdachte“.

## 2. In dieser Arbeitsphase geänderte Mechanismen

Alle mit Marker im Code, Tests und Eintrag im Failure-Log:

1. `AGP_K07_SEND_COMMIT_NONCE_V1` — jede Sendung beginnt mit `AGP-SEND-<16 hex>`;
   Commit-Beleg ist dessen Auftreten außerhalb des Composers. Workaround
   „leerer Composer = gesendet“ entfernt.
2. Trace-Transport: `background.js` sendet Traces per `chrome.tabs.sendMessage`
   (vorher `runtime.sendMessage` — erreichte nie das Content-Skript).
3. `AGP_K07_DELIVERY_STATE_V1` — Zustellstatus je Schritt, `/v1/file-loop/delivery-ack`,
   Neuzustellung beim Replay eines `PENDING`-Ergebnisses.
4. `AGP_K07_INFLIGHT_RECORD_V1` — `RUNNING` vor `run_next.py`; verlorenes Ergebnis blockiert.
5. `AGP_K07_POST_EXECUTION_OPERATOR_CONTROL_V1` — STOP/PAUSE nach Ausführung beachten.
6. `AGP_K07_DOWNLOAD_PROVENANCE_V1` — Bytes/Hash zwischen `/download` und `/command`.
7. `AGP_K07_BASELINE_BEFORE_SEND_V1`, `AGP_K07_ATTACHMENT_STABILITY_V1`.
8. `AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1` — Antwort = Dateikarte mit der
   frisch vergebenen Schrittnummer; unabhängig von Assistant-Wrappern.
   Schon sichtbare Nummern werden vor dem Bootstrap reserviert.
9. `AGP_K07_ASSISTANT_WAIT_OBSERVATION_V1` — begrenzte DOM-Evidenz beim Warten.
10. Runner/run_next (bereits zuvor von Codex umgesetzt): rc≠0 nie Erfolg,
    Selektor-Padding, SystemExit-Text im Log, `FAIL` als Fehlschlag.

## 3. Defekte (Reihenfolge = Priorität), jeweils mit Beleg

Stand-Nachtrag 2026-09-30 (Extension `0.3.16`, Bridge
`delivery-and-task-binding-20260930`): D1, D2 und D3 sind im Code behoben und
durch Verhaltenstests belegt; Live-Nachweis steht aus. D4–D7 bleiben offen.

### D1 — Ergebniszustellung bricht an falscher Bestätigung ab (FEHLER, live)
`chrome_extension/result_file_attachment.js` `attachResultFiles`: nach
`DOM.setFileInputFiles` werden zusätzlich `input`/`change` manuell ausgelöst und
danach `this.files` gelesen. Die Dateien sind live im Composer angekommen,
die Prüfung meldet trotzdem Fehlschlag. Wahrscheinliche Ursache (nicht bewiesen):
`DOM.setFileInputFiles` löst selbst die Events aus, ChatGPT übernimmt die Dateien
und leert das Input; die manuellen Zusatz-Events finden ein leeres `files` vor.
Die doppelte Event-Auslösung erklärt vermutlich auch den bisher per Workaround
weggeklickten „already uploaded“-Dialog.
Reparaturrichtung: keine manuellen Events; `files` direkt nach
`setFileInputFiles` lesen; Aufnahme im Composer über einen DOM-unabhängigen
Beleg prüfen (z. B. Dateinamen im Composer-Bereich); Test mit echtem Chromium.

### D2 — Erwartete Schrittnummer wird vor erfolgreicher Zustellung weitergeschaltet (FEHLER)
`content.js` `submitAssistantCommandFile`: `STATE.nextLocalStep = result.next_step`
vor dem Senden der Fortsetzung. Scheitert die Zustellung (D1), sucht der Loop
nach Karte 1477 statt 1476; die in `AGP_K07_DELIVERY_STATE_V1` vorgesehene
Neuzustellung per Replay kann dadurch nie greifen (live: `expected_step 1477`,
dann Timeout). Reparatur: `nextLocalStep` erst nach bestätigter Zustellung setzen.

### D3 — Task-Bindung geht beim Start verloren; verifizierte Fertig-Erkennung kann live nicht greifen (FEHLER)
`TASK_START_REQUEST_ACCEPTED` ruft `StartRequestStore.invalidate_pending()` auf,
das `mission_id` und `task_id` leert. `/v1/file-loop/command` liest danach
`StartRequestStore.current()["task_id"]` → leer (live: `K07_COMMAND_ACCEPTED task_id=null`).
Damit ist `handoff_contract=False`, `prepare_receipt` läuft nie, und
`/v1/file-loop/result-delivered` würde an `start.mission_id != mission_id` scheitern.
Konflikt zweier früherer Reparaturen (#133 Start-Request-Invalidierung vs.
Verified Handoff Completion). Reparatur: eigene, persistente aktive
Task-Bindung (Mission ↔ Task ↔ Completion-Contract), unabhängig vom
Einmal-Trigger; gelöscht nur bei terminalem Zustand/STOP/neuer Mission.

### D4 — Textbasierte Antworten sind im aktuellen DOM unsichtbar (FEHLER, latent) — REPARIERT, Live-Nachweis offen
Reparatur 2026-09-30 (`AGP_K07_TERMINAL_REPLY_FILE_V1`): terminale Antwort als
Datei `<schritt>_agp_terminal.json`, Endpoint `/v1/file-loop/terminal`,
Remote-DONE nur Antrag (siehe COMMUNICATION_PROTOCOL.md, Punkt 11). Belegt durch
`tests/test_k07_terminal_reply.py`, `tests/terminal_reply_browser.cjs`,
`tests/e2e/test_k07_expected_step_attachment.spec.js`. Ursprünglicher Befund:
`assistantMessageNodes()` nutzt nur `[data-message-author-role="assistant"]`
(live 0 Treffer). Damit werden Terminalantworten (`AGP_DONE`,
`AGP_NEEDS_HUMAN`, Quittung des Handoff-Abschlusses) nie erkannt.

### D5 — Generierungserkennung wirkungslos (RISIKO)
`chatgptGenerationActive()` war live während der gesamten Denkphase `false`.
Schutz gegen verfrühtes Lesen beruht derzeit auf Schrittnummer, zwei stabilen
Polls, Browser-Download und Vertragsprüfung.

### D6 — Kit-Befunde im erzeugten Handoff-Paket (agentic-kit 1.0.13, nicht Cockpit)
`execution_contract.json`/`successor_context.yaml`: `local_path: "cd /path/to/"`
(Platzhalter statt Repo-Pfad), `dirty_paths: []` bei `worktree_clean: false`,
`open_tasks_source: docs/planning/PROJECT_DIRECTION.yaml` im externen Workspace,
Kit-interne „recent_lessons“. `validation_report.json` meldet dennoch PASS —
der Validator prüft diese Inhalte nicht. Im Kit-Repo beheben.

### D7 — Arbeitsbaum-Hygiene
Großer gemischter uncommitteter Stand auf `fix/k07-verified-handoff-completion`;
Kernmodule `command_file_contract.py`, `handoff_completion.py` und mehrere Tests
sind untracked. Vor weiterer Arbeit in kohärente Commits zerlegen.

## 4. Folgerungen für weitere Standardaufträge und mehrstufige Aufträge

„Chat wechseln“ ist nur eine Anwendung. Für `kit-release`, `kit-commit`,
`kit-push` und komplexe Aufträge mit vielen Turns gilt:

1. **Identität statt DOM-Struktur.** Jede Grenze wird über eine vom Cockpit
   vergebene, nicht wiederverwendbare Identität erkannt: Sende-Nonce für den
   Nutzer-Turn, Schrittnummer für die Antwort. Keine neue Logik auf
   ChatGPT-Wrapper, IDs oder Rollenattribute stützen.
2. **Auch Terminalantworten als Datei.** `AGP_DONE`/`AGP_NEEDS_HUMAN` als
   Prosa ist im aktuellen DOM nicht verlässlich erkennbar (D4). Empfehlung:
   terminale Antwort als Dateikarte `<schritt>_agp_terminal.json`
   (`{"state":"DONE"|"NEEDS_HUMAN","reason":…}`), gleiche Erkennung, gleicher
   Download- und Validierungsweg wie `.py`. Prosa bleibt nie Autorität.
3. **Fertig ist lokal verifiziert, nicht remote behauptet.** Jeder
   Standardauftrag trägt einen expliziten Completion-Contract
   (Muster: `verified-successor-handoff-v1`) mit lokalem Verifizierer, der nur
   Kit-erzeugte Evidenz prüft (Kit-JSON-Ergebnis, Rückgabecode, Revision,
   Artefakt-Hashes). Remote-`DONE` ist nur ein Antrag. Der Cockpit bewertet
   keine Kit-Semantik (AGENTS.md), er prüft Evidenz gegen den Vertrag.
4. **„Mensch muss eingreifen“** ist ein eigener dauerhafter Zustand
   (`WAITING_FOR_HUMAN`) mit Grund, der keine weiteren Turns sendet; ausgelöst
   durch Remote-`NEEDS_HUMAN`, Kit `BLOCKED`, `OUTCOME_UNKNOWN`, Budget- oder
   Wiederholungsgrenzen. Fortsetzung nur durch explizite menschliche Aktion.
5. **Zustellung vor Fortschritt.** Schrittnummer, Turnzähler und terminale
   Zustände rücken erst nach bestätigter Zustellung vor (D2). Jede Zustellung
   ist idempotent wiederholbar ohne erneute Ausführung (Delivery-State).
6. **Mehrstufige Aufträge** brauchen pro Turn: frische Schrittnummer,
   genau eine Datei, genau ein Ergebnisbündel, Zustellbeleg, Fehlersignatur-
   Zähler, Turn-Budget. Die bestehenden Grenzen (3 gleiche Fehler → BLOCKED,
   2 Preflight-Fehler → BLOCKED, 40 Turns) bleiben; `OUTCOME_UNKNOWN` blockiert.
7. **Effektklassen.** `kit-push`/`kit-release` sind externe, nicht
   rücknehmbare Effekte. Vor der Ausführung muss die lokale Task-Authority den
   Effekt erlauben; nach `OUTCOME_UNKNOWN` ist Blind-Replay verboten.
8. **Tests.** Verhaltenstests gegen echtes Chromium (Muster:
   `tests/e2e/test_k07_send_commit_nonce.spec.js`,
   `tests/e2e/test_k07_expected_step_attachment.spec.js`) und HTTP-Tests gegen
   die echte Bridge (`tests/test_k07_delivery_http.py`). Reine
   Quelltext-String-Tests belegen kein Verhalten und genügen nicht als Nachweis.
9. **Live-Diagnose zuerst.** Vor jeder Reparatur einer Live-Divergenz die
   Evidenz aus `.local/agp-cockpit/logs/bridge.log*` lesen
   (`K07_NATIVE_TRACE`, `K07_ASSISTANT_WAIT_OBSERVATION`, `TICK_ERROR`).
   Das Log rotiert bei ~2 MB; ältere Einträge stehen in `bridge.log.1` ff.

## 5. Empfohlene nächste Scheiben

1. D2 + D1 (Zustellung) — kleinste Scheibe, macht „Chat wechseln“ bis zur
   Quittung live prüfbar.
2. D3 (aktive Task-Bindung) — Voraussetzung für jede verifizierte Fertig-Erkennung.
3. D4 über Terminaldatei (Folgerung 2) statt DOM-Heuristik.
4. D7 Commits; danach je ein Live-Lauf pro Scheibe.
5. D6 im Kit-Repository.
