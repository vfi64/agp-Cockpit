# Auftrag an Claude: Kommunikations- und Ausführungsregelkreis des AGP Cockpit analysieren

## Ziel

Analysiere den Kommunikationsregelkreis zwischen AGP Cockpit, Chrome-Extension, Bridge, ChatGPT-Tab, lokaler LLM/Hermes und dem lokalen Python-Datei-Loop. Finde die tatsächlichen Ursachen der wiederkehrenden Kommunikations- und Ausführungsfehler und entwickle eine stabile, deterministische und kit-konforme Lösung.

Arbeite nicht symptomorientiert. Rekonstruiere den vollständigen Ablauf anhand von Quellcode, Tests, Logs und Laufzeitartefakten. Eine Lösung gilt erst als akzeptabel, wenn sie den gesamten Regelkreis beweisbar schließt und Fehler begrenzt, diagnostizierbar sowie sicher abbrechbar macht.

## Repository und Arbeitsgrenzen

Repository:

`/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit`

Wichtige Bereiche:

- `chrome_extension/`
- `src/agp_cockpit/core/`
- `src/agp_cockpit/adapters/`
- `tests/`
- `tests/e2e/`
- `docs/K07_FILE_LOOP_PROTOCOL.md`
- `docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md`
- `docs/engineering/RUNTIME_PATH_AUTHORITY.md`
- `Download/`
- `.local/agp-cockpit/`

Lies zuerst die Projektregeln und die aktuelle Kit-Autorität. Verwende keine rekonstruierten oder veralteten Kommandos. Behandle Repository-Zustand, Handoff-Dateien und Logs als maßgebliche Evidenz, nicht den Chatverlauf.

## Aktuelles Fehlerbild

1. Die Remote-LLM erzeugt eine Python-Datei, aber sie wird nicht zuverlässig in `Download/` abgelegt oder nicht über `Download/run_next.py` ausgeführt.
2. Der Turn-Zähler bleibt bei `0/40`, obwohl im Chat ein Python-Anhang sichtbar ist.
3. Es entstehen Endlosschleifen oder viele Turns ohne Fortschritt, zum Beispiel `75/40`.
4. Der Stop-Button beendet solche Abläufe nicht immer zuverlässig.
5. Der Chat-Wechsel-Button kann mit `HTTP Error 400: Bad Request` blockieren.
6. Die Bridge kann `CONNECTED` anzeigen, obwohl die Laufzeitidentität noch nicht vollständig bestätigt ist.
7. Chrome zeigte zeitweise: `Unrecognized manifest key 'x_agp_build_id'.`
8. Nach einem Build kann Chrome noch einen alten Extension-Fehler anzeigen, während die aktuelle staged Extension bereits korrigiert ist.
9. Python-Dateien wurden zeitweise mit falschen, wiederverwendeten oder nicht fortlaufenden Nummern erzeugt, statt die nächste Nummer nach dem vorhandenen `Download/`-Bestand zu verwenden.
10. Syntaktisch gültige, aber semantisch unvollständige Python-Dateien konnten `py_compile` und einen zu schwachen Self-Test passieren, ohne ein Kit-Kommando auszuführen oder ein Return-Bundle zu erzeugen.

## Bereits bekannte technische Befunde

Diese Befunde sind zu verifizieren, nicht ungeprüft zu übernehmen:

- Extension-, App-, staged- und Browser-Versionen waren zeitweise nicht durch eine gemeinsame Build-Identität gekoppelt.
- Die Runtime-Identitätsprüfung verlangt inzwischen Version, Build-ID, Repository-Pfad, `Download/`-Pfad, `run_next.py` und passenden ChatGPT-Tab.
- Die Build-ID wird inzwischen über `chrome_extension/build_identity.js` geladen. Sie darf nicht als nicht standardisierter Schlüssel in `manifest.json` stehen.
- Ein Start-Request wird bei fehlendem oder nicht passendem frischem Handshake absichtlich abgewiesen. Diese Abweisung muss für den Benutzer verständlich und nach erfolgreicher Bereitschaft automatisch auflösbar sein.
- Der Bridge-Log meldete für einen fehlgeschlagenen Start: `fresh-extension-handshake-missing, handshake-version-mismatch, handshake-build-id-mismatch, handshake-page-mismatch`.
- Die alte Chrome-Fehlermeldung kann ein historischer Fehlerdatensatz sein und muss von einem aktuell geladenen Manifest unterschieden werden.
- Der gültige lokale Startpfad ist immer das Repository-`Download/`-Verzeichnis zusammen mit `Download/run_next.py`. Andere Download-Verzeichnisse dürfen nicht stillschweigend verwendet werden.

## Zentrale Analysefragen

### A. Remote-Dialog und Composer

1. Wie wird ein Remote-Turn eindeutig erkannt?
2. Wird vor dem Absenden nur der DOM-Inhalt geprüft oder auch das interne Editor-Modell, insbesondere ProseMirror?
3. Sind `COMPOSER_MODEL_VERIFIED`, `USER_TURN_COMMITTED`, `INSERT_NOT_VERIFIED`, `NATIVE_TRANSPORT_FAILED` und `SEND_INDETERMINATE` sauber getrennt?
4. Wie wird `SEND_INDETERMINATE` deterministisch reconciliert?
5. Welche begrenzten Recovery-Pfade sind bei Einfügefehlern zulässig, ohne einen neuen Turn oder eine Endlosschleife zu erzeugen?
6. Wie wird verhindert, dass Zwischenablageinhalt automatisch im Composer erscheint?

### B. Python-Datei-Loop

1. Welche Komponente erkennt den Anhang?
2. Welche Komponente schreibt ihn nach `Download/`?
3. Wie wird die nächste fortlaufende Schritt- bzw. Dateinummer ermittelt?
4. Wie wird ausgeschlossen, dass eine Datei nur als Chat-Codeblock sichtbar, aber nicht als echter Download-Anhang vorhanden ist?
5. Wie wird vor dem Lauf geprüft, dass die Datei genau ein ausführbares Work-Order-Programm mit gültigem Hauptpfad enthält?
6. Wie wird nachgewiesen, dass `run_next.py` tatsächlich `py_compile`, Self-Test und Real-Run ausgeführt hat?
7. Was passiert bei Syntaxfehler, falscher Pythonumgebung, falschem `cwd`, fehlenden Rechten, nicht erreichbarem Kit, fehlendem Bundle-Writer oder fehlerhafter JSON-Ausgabe?
8. Wird bei jedem Fehler zusätzlich `__run_next_output.txt` als Rückkanal übertragen?
9. Gibt es genau ein kanonisches Return-Bundle je ausgeführtem Schritt?
10. Wie werden alte Bundles, doppelte Nummern und stale Dateien behandelt?

### C. Bridge, Hermes und lokale LLM

1. Welche Rolle hat Hermes tatsächlich: Transport, Dateispeicherung, Terminalausführung oder nur Orchestrierung?
2. Wird der lokale Python-Auftrag von Hermes wirklich gestartet oder nur als Datei erkannt?
3. Wie werden `cwd`, `sys.executable`, `argv`, Returncode, stdout, stderr, SHA-256 und Laufzeitdauer erfasst?
4. Sind Bridge-Port, Token-Datei, lokale LLM, Hermes und Extension im Cockpit sichtbar und eindeutig diagnostizierbar?
5. Welche Zustände sind erlaubt, und welche Übergänge sind verboten?
6. Wie verhindert das System einen Start, wenn der Handshake fehlt, aber die Bridge trotzdem `CONNECTED` zeigt?
7. Wie wird ein echter Stop/Break durchgeführt, so dass Polling, Retry, Timer, Browseraktionen und laufende lokale Prozesse beendet werden?

### D. Build, Staging und Pfadautorität

Prüfe die Identitätskette:

`Quell-Extension -> App-Build -> staged Extension -> Chrome -> Handshake -> Bridge -> Download/run_next.py`

Für jedes Glied müssen absolute Pfade, Version, Build-ID, SHA-256 sofern vorgesehen, Aktualisierungszeitpunkt, Quelle der Wahrheit, Abweichungsverhalten sowie Restore- und Reparaturmechanismus festgestellt werden.

Prüfe besonders, ob ein App-Neustart tatsächlich die Extension aktualisiert, ob Chrome die Extension neu lädt und ob ein alter Fehlerdatensatz mit einem aktuellen Lauf verwechselt werden kann.

## Geforderte Arbeitsweise

1. Zuerst eine reine Bestandsaufnahme erstellen. In dieser Phase keine Produktdateien ändern.
2. Den Fehler anhand mindestens eines realen Logs und eines reproduzierbaren Testfalls lokalisieren.
3. Die erste bewiesene Abweichung im Ablauf benennen.
4. Einen kleinen, begrenzten Reparatur-Slice mit Alternativen und Risiken vorschlagen.
5. Den Vorschlag mit Codex bzw. dem Maintainer diskutieren. Nicht mehrere konkurrierende Protokolländerungen gleichzeitig beginnen.
6. Nach Zustimmung modular implementieren.
7. Für jede neue Regel einen Test, ein Gate oder eine deterministische Validierung ergänzen.
8. Keine stillschweigenden Fallbacks, keine unbegrenzten Retries und keine bloßen UI-Scheinzustände einführen.
9. Bestehende funktionierende Nummerierungs-, Pfad-, Download- und `run_next.py`-Konventionen erhalten.
10. Jede relevante Erkenntnis und jede Protokolländerung im Entwicklungslog mit Ursache, Entscheidung, Test und Restore-Punkt festhalten.

## Erwartete Ergebnisse der Analysephase

Liefere zunächst ein Review-Dokument mit:

- reproduzierbarem Fehlerablauf;
- Zustandsdiagramm des Kommunikationsregelkreises;
- Komponenten- und Verantwortungsmatrix;
- vollständiger Artefakt- und Pfadkarte;
- Liste aller beobachteten Fehlerklassen;
- Ursache, Symptom und bisherige falsche Annahme je Fehlerklasse;
- Bewertung des aktuellen Fail-Closed-Verhaltens;
- Vorschlag für begrenzte Retry-, Reconciliation-, Reset- und Break-Regeln;
- fehlenden Tests und fehlende Logs;
- minimalem Umsetzungsschnitt;
- Risiken und offenen Entscheidungen.

## Abnahmekriterien für eine spätere Umsetzung

Eine Umsetzung ist erst akzeptabel, wenn mindestens folgende Nachweise vorliegen:

1. Ein frischer Build wird eindeutig erkannt.
2. Ein alter oder falsch gestagter Build wird blockiert und verständlich diagnostiziert.
3. Der Start-Button erzeugt genau einen neuen Auftrag.
4. Der Turn-Zähler steigt genau einmal pro bestätigtem Remote-Turn.
5. Die Python-Datei landet im autorisierten `Download/`-Verzeichnis.
6. Die Datei wird über den autorisierten `run_next.py`-Pfad ausgeführt.
7. Self-Test und Real-Run sind getrennt nachgewiesen.
8. Syntax-, Umgebungs-, Pfad-, Kit- und Logfehler werden unterschieden.
9. Bei jedem Fehler entstehen kanonisches Return-Bundle und, falls nötig, `__run_next_output.txt`.
10. Eine fehlende oder fehlerhafte JSON-Antwort führt nicht zu einem stillen Weiterlaufen.
11. Der Remote-LLM wird der konkrete Fehler samt Artefaktpfaden übermittelt.
12. Retry und Recovery sind begrenzt und erzeugen keinen zusätzlichen Turn ohne nachgewiesenen Fortschritt.
13. Stop, Break und Reset beenden einen laufenden Zyklus sicher und hinterlassen verwertbare Evidenz.
14. Ein Ende-zu-Ende-Test deckt erfolgreichen Lauf, Syntaxfehler, fehlenden Bundle-Writer, fehlenden Handshake, stale Extension, falschen Pfad und Abbruch ab.
15. Die vorgeschriebenen Repository-Gates sind erfolgreich und der Restore-Checkpoint ist dokumentiert.

## Wichtiges Ergebnisformat

Antworte nach der Analyse nicht mit einem pauschalen „funktioniert“ oder mit einem ungetesteten Patch. Liefere:

1. Befunde nach Priorität;
2. Beweise mit Datei-, Log- und Testpfaden;
3. genaue Ursache des jeweils ersten Fehlers;
4. gemeinsam zu entscheidende Architekturpunkte;
5. vorgeschlagenen Umsetzungsschnitt;
6. konkrete Tests und erwartete Ergebnisse.

Wenn mehrere Ursachen gleichzeitig plausibel sind, trenne sie ausdrücklich. Eine erfolgreiche Diagnose eines Teilproblems darf nicht als Beweis für einen geschlossenen Gesamtregelkreis dargestellt werden.

## Gemeinsame Entscheidungsregel

Führe die Lösungsdiskussion mit Codex bzw. dem Maintainer, bis die Ursachen, der Umsetzungsschnitt, die Zustandsübergänge, die Recovery-Grenzen und die Nachweise eindeutig festgelegt sind. Beginne erst danach mit Änderungen.
