# PHASE 066 — Browser Integration & Evidence Gates


Status: active
Decision status: accepted
Review policy: Review at every Phase 066 slice boundary and before any production browser-logic change; close or supersede when Phase 066 exits.

## Zweck

Diese Phase ersetzt das bisherige schrittweise „Browserfehler → Vermutung → Patch → Unit-Test → erneuter Live-Test“-Vorgehen durch eine reproduzierbare, gate-gesicherte Browser-Integrationsarchitektur.

Der aktuelle reale Fehler ist **nicht weiter direkt zu patchen**, bevor er automatisiert reproduziert werden kann:

> ChatGPT hat den Mission-Bootstrap tatsächlich angenommen und eine Assistant-Antwort erzeugt, während AGP Cockpit gleichzeitig `SEND_UNCONFIRMED: expected user message did not appear` meldet.

Dieser Zustand ist die verpflichtende erste Regression-Fixture dieser Phase.

## Autoritäts- und Scope-Grenze

AGP Cockpit bleibt ausschließlich lokale Kommunikations-/Steuerbrücke zwischen LLM, Browser, lokalem Terminal und Agentic Project Kit.

Das Agentic Project Kit bleibt Autorität für:
- Git-/GitHub-Workflow
- Governance
- Branch-/PR-/Merge-Sicherheit
- Repository-Workflowregeln

Phase 066 darf **keine Kit-Workarounds** einführen.

Die in Phase 065 gefundenen Greenfield-Kit-Probleme bleiben separat klassifiziert. Cockpit-Browserfehler dürfen nicht als Kit-Defekte verbucht werden.

## Harte Entwicklungsregel

Ab Beginn Phase 066 gilt:

> Kein weiterer Produktionsfix am Browser-Send-/ACK-/Assistant-Erkennungspfad darf als abgeschlossen gelten, solange der zugehörige reale Fehler nicht zuerst automatisiert reproduziert und danach durch dieselbe Regression grün gemacht wurde.

Insbesondere:
- keine weiteren R15/R16/R17-artigen ad-hoc Produktionspatches;
- keine „PASS“-Bewertung nur aufgrund von Source-Literal-Tests;
- keine Live-Browser-Reparatur ohne reproduzierbare Evidence;
- keine Abschwächung der fail-closed JSON-/cwd-/argv-/timeout-Validierung.

---

# Zielarchitektur der Gates

## G1 — Static / Unit / Contract

Muss mindestens prüfen:

- JavaScript-Syntax der Chrome-Extension
- Python-Syntax
- vollständige `pytest`-Suite
- vorhandene Cockpit-Unit-/Contract-Tests
- `agentic-kit check`
- `agentic-kit doctor`

G1 beweist **nicht** die Browserintegration.

## G2 — Deterministic DOM Fixture

Eine lokale, reproduzierbare ChatGPT-ähnliche DOM-Fixture muss bereitgestellt werden.

Sie muss mindestens folgende Zustände simulieren:

1. leerer Composer
2. Composer nach Texteingabe
3. Send-Button sofort verfügbar
4. Send-Button verspätet verfügbar
5. User-Message erscheint normal
6. User-Message erscheint verspätet
7. User-Message wird textuell anders normalisiert
8. User-Message ist für die aktuelle ACK-Logik nicht beobachtbar
9. Assistant-Generation beginnt trotzdem
10. Assistant streamt
11. Assistant liefert vollständige JSON-Antwort
12. Follow-up Turn 2
13. Follow-up Turn 3
14. Send wird tatsächlich nicht angenommen
15. Assistant-Antwort ist kein gültiges reines JSON
16. Assistant-Antwort hat falsches cwd/argv/timeout
17. identischer Prompt-Loop
18. Abbruch / Stop

G2 muss den aktuell beobachteten Fehler reproduzieren:

**Baseline vor Fix:**
- Send wird von der simulierten ChatGPT-Seite angenommen.
- neue Assistant-Antwort erscheint.
- alte Cockpit-ACK-Logik würde trotzdem `SEND_UNCONFIRMED` melden.

Der Test muss vor dem Produktionsfix ROT sein.

## G3 — Browser E2E

Ein echter Browser-Test muss die entpackte Chrome-Extension laden und die DOM-Fixture als echte Seite bedienen.

Bevorzugt:
- Playwright
- Chromium/Chrome Extension Loading
- headful oder headless nur soweit MV3/Extension-Laden zuverlässig funktioniert

G3 muss mindestens automatisieren:

### E2E-1 Single Turn
Mission erstellen → Start Auto → Prompt senden → Assistant JSON erkennen → lokal validieren → Turn 1 erfolgreich.

### E2E-2 3-Turn FULL_AUTO
Exakt:

1. `/usr/bin/git status --short`
2. `/usr/bin/git branch --show-current`
3. `/usr/bin/git log -1 --oneline`

mit Repository-CWD des AGP Cockpit.

Erwartung:
- Turn 1 PASS
- Turn 2 PASS
- Turn 3 PASS
- danach Auto STOP
- kein `TICK_ERROR`
- keine vierte Ausführung

### E2E-3 Missing User Bubble / Assistant Evidence
Prompt wird angenommen, User-Bubble ist für ACK nicht beobachtbar, Assistant-Generation beginnt.

Erwartung:
- kein falsches `SEND_UNCONFIRMED`
- Acceptance wird über zulässige alternative Evidence erkannt

### E2E-4 Real Send Failure
Prompt wird nicht angenommen und es gibt weder User-Message- noch Assistant-Evidence.

Erwartung:
- fail-closed
- `SEND_UNCONFIRMED`
- keine lokale Ausführung

### E2E-5 Invalid Assistant Payload
Nicht-reines JSON oder falscher Befehl.

Erwartung:
- keine lokale Ausführung
- klare Fehlerklassifikation

---

# Browser-Zustandsautomat

Der bisher zu breite `sendPrompt()`-Pfad soll in explizite Zustände zerlegt bzw. zumindest logisch so instrumentiert werden:

- `COMPOSER_READY`
- `TEXT_INJECTED`
- `SEND_TRIGGERED`
- `ACCEPTANCE_OBSERVED`
- `ASSISTANT_STARTED`
- `ASSISTANT_COMPLETE`
- `RESPONSE_VALIDATED`
- `LOCAL_EXECUTED`
- `NEXT_TURN`
- `DONE`

Fehlerzustände mindestens:

- `COMPOSER_UNAVAILABLE`
- `SEND_PATH_UNAVAILABLE`
- `SEND_UNCONFIRMED`
- `ASSISTANT_TIMEOUT`
- `ASSISTANT_INVALID`
- `LOCAL_VALIDATION_REJECTED`
- `LOCAL_EXECUTION_FAILED`

Jeder Übergang benötigt strukturierte Evidence.

Beispiel:

```json
{
  "transition": "SEND_TRIGGERED->ACCEPTANCE_OBSERVED",
  "evidence": {
    "user_message_count_before": 17,
    "user_message_count_after": 17,
    "assistant_count_before": 16,
    "assistant_count_after": 17,
    "composer_cleared": true,
    "assistant_started": true,
    "accepted_via": "assistant_generation"
  }
}
```

Wichtig:

Assistant-Aktivität darf nur dann als Acceptance-Evidence gelten, wenn sie eindeutig **nach** dem Send-Versuch entstanden ist und nicht bereits vor dem Send vorhanden war.

---

# Send-Acknowledgement-Semantik

Die Send-Bestätigung darf nicht mehr ausschließlich von einer exakten sichtbaren User-Bubble abhängen.

Zulässige positive Evidence kann sein:

1. neue normalisierte User-Message entspricht dem Prompt;
2. eindeutige neue Assistant-Generation nach dem Send-Versuch;
3. eindeutiger generation-/conversation-state change, sofern reproduzierbar und getestet;
4. Composer leert sich **nur als unterstützende**, nicht alleinige Evidence.

Fail-closed bleibt verpflichtend:

Wenn innerhalb eines begrenzten Zeitfensters **keine** belastbare Acceptance-Evidence entsteht, muss `SEND_UNCONFIRMED` bleiben.

---

# Regression Corpus

Die Erkenntnisse aus 065L werden als Regression Corpus konserviert.

Mindestens dokumentieren und testen:

- undefined overlay button
- stale UI-test contract
- SINGLE_STEP statt FULL_AUTO
- verspäteter / fehlender Send-Button
- falscher `PROMPT_SENT` ohne bestätigte Send-Evidence
- ACK false negative trotz sichtbarer Assistant-Antwort
- Test-Harness-Literalfehler nach Produktionsänderungen

Jeder reale Browserfehler erhält:
- reproduzierbare Fixture
- eindeutige Test-ID
- Fehlerklassifikation
- Expected-before-fix
- Expected-after-fix

---

# Kanonisches Cockpit-Gate

Es ist genau ein kanonischer lokaler Entry Point zu schaffen:

```bash
./scripts/cockpit-gate
```

oder gleichwertig unter einem klar dokumentierten Pfad.

Das Gate muss mindestens ausführen:

1. JS syntax
2. Python compile/static sanity
3. pytest
4. G2 DOM fixture tests
5. G3 browser E2E
6. `agentic-kit check`
7. `agentic-kit doctor`

Ausgabe muss deutlich enden mit:

```text
COCKPIT_GATE_RESULT=PASS
```

oder:

```text
COCKPIT_GATE_RESULT=FAIL
BLOCKER=<gate-name>
```

Ein Browserproduktionsfix darf nur als abgeschlossen gelten, wenn dieses Gate PASS ist.

---

# CI

GitHub Actions soll mindestens G1–G3 ausführen.

Anforderungen:

- reproduzierbare Dependency-Installation
- Playwright/Chromium-Setup
- keine privaten Tokens
- keine ChatGPT-Anmeldung
- keine echte OpenAI-Websession
- keine Browser-Secrets
- keine Live-ChatGPT-Ausgabeextraktion in CI
- Artefakte bei Fehlern, soweit sinnvoll:
  - Browser-Screenshot
  - Playwright trace
  - strukturierte Gate-Ausgabe
  - relevante Extension-Logs

Der CI-Check soll einen stabilen Namen erhalten, z. B.:

`cockpit-integration-gate`

Dieser Check soll später als required status check für `main` genutzt werden können.

---

# G4 — Live Canary

Die echte ChatGPT-Weboberfläche ist **nicht** Teil des deterministischen PR-Gates.

Sie wird separat als Live Canary behandelt.

Zweck:
- erkennen, wenn sich die reale ChatGPT-DOM von unseren Fixtures entfernt;
- keine vertraulichen Daten persistieren;
- keine Credentials automatisieren;
- kein CI-Abhängigkeitspunkt.

Live Canary für Phase 066:

1. Cockpit lokal starten.
2. Extension laden.
3. echte ChatGPT-Seite öffnen.
4. exakt die bounded 3-Turn-read-only Mission ausführen.
5. Ergebnis dokumentieren.

Erwartung:
- 1/40
- 2/40
- 3/40
- Auto stoppt
- kein `TICK_ERROR`
- kein falsches `SEND_UNCONFIRMED`

Ein G4-Fehler öffnet eine neue Regression, aber wird nicht durch ad-hoc Patchen repariert. Zuerst muss eine reproduzierbare Fixture ergänzt werden.

---

# Empfohlene Dateistruktur

Codex darf vorhandene Strukturen berücksichtigen, soll aber ungefähr auf folgende Trennung hinarbeiten:

```text
chrome_extension/
  content.js
  ...

tests/
  browser_fixtures/
    chatgpt_fixture.html
    chatgpt_fixture.js
  e2e/
    test_single_turn.*
    test_three_turn_full_auto.*
    test_send_ack_assistant_evidence.*
    test_send_failure.*
  regression/
    test_065l_*.*
  ...

scripts/
  cockpit-gate

.github/workflows/
  cockpit-integration.yml
```

Falls das Repository bereits passendere Konventionen besitzt, diese verwenden und Abweichung begründen.

---

# Reihenfolge der Umsetzung

## Slice 066-A — Reproduction First

Noch **keine Produktionslogik reparieren**.

1. Browser-Testinfrastruktur einführen.
2. lokale ChatGPT-DOM-Fixture bauen.
3. den aktuellen Fehler reproduzieren.
4. Test muss nachweislich ROT sein.
5. Failure-Evidence sichern.

Abnahmekriterium:
Der konkrete Zustand „Assistant-Antwort entsteht, Cockpit meldet trotzdem SEND_UNCONFIRMED“ ist automatisiert reproduziert.

## Slice 066-B — State/Evidence Model

1. Browser-Send-/ACK-Observability strukturieren.
2. Transition-Evidence implementieren.
3. bestehende Sicherheitsgrenzen beibehalten.
4. Tests grün machen, soweit noch ohne eigentlichen Acceptance-Fix möglich.

## Slice 066-C — Narrow Production Fix

Erst jetzt:
- alternative Acceptance-Evidence sauber implementieren;
- Assistant-Aktivität nur generation-sicher akzeptieren;
- fail-closed beibehalten.

Abnahmekriterium:
Die in 066-A rote Regression wird grün.

## Slice 066-D — Full 3-Turn E2E

- FULL_AUTO 3-Turn gegen echte Browser-Fixture
- exakt drei Ausführungen
- Auto stoppt
- keine vierte Ausführung
- kein `TICK_ERROR`

## Slice 066-E — Canonical Gate

- `scripts/cockpit-gate`
- eindeutige PASS/FAIL-Ausgabe
- alle G1–G3 Checks integriert

## Slice 066-F — CI

- GitHub Action
- `cockpit-integration-gate`
- reproduzierbar grün
- Fehlerartefakte

## Slice 066-G — Live Canary

Erst nach G1–G3 PASS.

- reale Chrome-Extension neu laden
- ChatGPT-Tab neu laden
- bounded 3-Turn Mission
- Live-Ergebnis dokumentieren

---

# Verbotene Abkürzungen

Nicht zulässig:

- Produktionsfix vor reproduzierendem Test
- Source-Literal-Test als Ersatz für Browser-E2E
- `sleep` als alleinige Synchronisationsstrategie
- unbegrenzte Retry-Loops
- Abschwächung der exakten 3-Turn-Kommandosequenz
- Abschwächung von cwd-/argv-/timeout-Prüfungen
- automatische Ausführung nicht validierter Assistant-Ausgaben
- Kit-Workarounds
- CI mit echten ChatGPT-Credentials
- CI gegen echte ChatGPT-Websession

---

# Required Evidence je Slice

Codex soll nach jedem Slice ausgeben:

- Branch
- geänderte Dateien
- Zweck
- Tests
- Gate-Ergebnisse
- verbleibende Blocker
- Klassifikation Cockpit vs. Kit vs. Test-Harness
- exakter nächster Schritt

Bei Fehlern:
- zuerst Ursache klassifizieren;
- nicht blind weiterpatchen;
- Regression hinzufügen oder bestehende korrigieren;
- Produktionspfad nur ändern, wenn Evidence die Änderung rechtfertigt.

---

# Abschlusskriterien Phase 066

Phase 066 ist erst abgeschlossen, wenn:

1. der aktuelle SEND_UNCONFIRMED-False-Negative reproduzierbar getestet ist;
2. der Fix denselben Test grün macht;
3. Single-Turn E2E grün ist;
4. 3-Turn FULL_AUTO E2E grün ist;
5. Fail-closed-Send-Failure E2E grün ist;
6. Invalid-Assistant-Payload E2E grün ist;
7. `./scripts/cockpit-gate` PASS liefert;
8. CI `cockpit-integration-gate` PASS liefert;
9. `agentic-kit check` PASS;
10. `agentic-kit doctor` PASS;
11. keine Kit-Workarounds eingeführt wurden;
12. Live Canary erfolgreich 1 → 2 → 3 durchläuft oder ein verbleibender Live-Unterschied als neue Regression reproduzierbar dokumentiert wurde.

---

# Arbeitsweise für Codex

Arbeite autonom, aber evidence-first.

Vor jeder Produktionsänderung:
1. Ursache belegen.
2. reproduzierenden Test erzeugen.
3. Test rot zeigen.
4. kleinste notwendige Änderung implementieren.
5. G1–G3 vollständig ausführen.
6. erst dann zum nächsten Slice.

Bei einem Gate-Fehler nicht mehrere spekulative Reparaturen stapeln.

Wenn ein Test selbst veraltet/falsch ist:
- als Test-Harness-Defekt klassifizieren;
- Produktion unverändert lassen;
- Test korrigieren;
- vollständiges Gate erneut ausführen.

Wenn ein Agentic-Project-Kit-Befehl in diesem externen Greenfield-Workspace scheitert:
- zuerst separat reproduzieren;
- Cockpit-Code nicht verbiegen;
- als Kit-Greenfield-Kandidat dokumentieren, wenn der Fehler tatsächlich im Kit liegt.

---

# Endzustand

Nach Phase 066 soll Browserentwicklung nicht mehr von manuellen Screenshots als primärem Debuggingmechanismus abhängen.

Manuelle Live-Screenshots sind nur noch:
- Canary-Evidence
- neue Regressionseingabe

Die eigentliche Entwicklungsentscheidung wird von reproduzierbaren Browser-Gates getragen.
