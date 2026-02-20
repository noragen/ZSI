# ZSI Next-Level Improvements

Dieses Dokument sammelt konkrete Verbesserungen, um ZSI technisch, operativ und qualitativ auf das nächste Level zu bringen.

## Ziele

- Höhere Performance bei Parse/Serialize und `wsdl2py`
- Modernere, wartbare Python-3-Codebasis
- Bessere Test- und Release-Sicherheit
- Klarere Developer Experience (DX)

## Prioritäten

- `P0` = sofort hoher Nutzen / geringe bis mittlere Komplexität
- `P1` = hoher Nutzen / mittlere Komplexität
- `P2` = strategisch wichtig / größere Arbeiten

## P0 Quick Wins

- Profiling-Baseline aufsetzen:
  - `cProfile`-Runs für `test\test_zsi.py` und `test\wsdl2py\runTests.py local`
  - Top-Hotspots je Lauf dokumentieren
- Performance-Regression-Guard:
  - kleiner Benchmark-Smoke (Zeitbudget + Trendvergleich)
- `wsdl2py`-Dedupe:
  - doppelte `pyclass_type`-Imports in generierten Stubs eliminieren
- Low-risk Micro-Optimierungen:
  - unnötige String-/List-Kopien in Parse/Serialize-Pfaden reduzieren
  - einfache Caches für wiederholte Namespace-/Lookup-Operationen
- Test-Hygiene:
  - flakey/umgebungsabhaengige Tests markieren/isolieren
  - stabile `local`-Testausführung als Standard dokumentieren

## P1 Performance & Runtime

- Hotspot-Tuning in:
  - `ZSI/TCcompound.py`
  - `ZSI/parse.py`
  - `ZSI/writer.py`
- Lazy-Typecode-Pfad weiter härten:
  - `_Mirage`/Reveal-Logik vereinheitlichen
  - wiederholte Instanziierungen minimieren
- XML-Handling evaluieren:
  - Kosten für DOM-Aufbau vs. gezieltere Verarbeitung messen
- Memory-Footprint:
  - große SOAP-Payloads (Streaming/inkrementelle Verarbeitung) untersuchen

## P1 Generator (wsdl2py) Next Steps

- Generierter Code:
  - konsistente Imports, keine Duplikate
  - einheitliche Exception-Syntax und Style
- Optionaler `--fast`-Modus:
  - weniger Runtime-Magie in generierten Klassen
  - mehr direkte Verweise, wo sicher
- Stabilität bei WSDL-Edge-Cases:
  - leere `wsdl:message`
  - schwierige substitution groups
  - große WSDLs (z. B. VIM) als Dauer-Regressionstest

## P1 Modern Python

- Typannotationen schrittweise einführen:
  - Start bei `generate/*`, `parse.py`, `schema.py`
- Lint/Format-Stack modernisieren:
  - `ruff` + `black` (oder klar definierte Alternative)
- Alte Kompatibilitätsreste aufräumen:
  - ungenutzte Legacy-Pfade, tote Kommentare, alte Namenskonventionen

## P2 Qualität & Architektur

- Klarere Modulgrenzen:
  - Generator, Runtime, Transport, XML-Tools stärker trennen
- API-Stabilität:
  - explizite Public API definieren
  - interne APIs markieren
- Fehlerbilder verbessern:
  - präzisere Exceptions mit Kontext (WSDL-Teil, Namespace, Operation)

## P2 Tests, CI, Releases

- CI-Matrix:
  - Windows + Linux
  - mehrere Python-3-Versionen
- Test-Splits:
  - `unit` / `integration-local` / `network-optional`
- Release-Pipeline:
  - automatisierte Build+Test+Tag-Checks
  - `RELEASE.md` als Gate-Checklist in CI

## Sicherheit & Robustheit

- Netzwerkresolver absichern:
  - klare URI-Allowlist-Policies
  - Timeout-/Retry-Defaults dokumentieren
- Input-Hardening:
  - untrusted XML-Szenarien prüfen
  - defensive Limits für große/rekursive Payloads
- Minimaler Hardening-Baustein:
  - `scripts/security_input_guard.py` validiert untrusted Resolver-URIs (Scheme, Credentials, Prefix)
  - `test/test_security_input_guard.py` deckt Positiv-/Negativfälle als Regression ab

## Security Deep Dive (ZSI)

- [x] Threat-Model-Basis für ZSI dokumentiert (`SECURITY.md`: Parser, Resolver, Generator, Transport, CI-Artefakte)
- [x] Security-Baseline für Parser definieren (max. Elementtiefe, Attributgröße, Gesamtpayload-Grenzen)
- [x] Resolver-Policy-Defaults zentralisieren (Allowlist/Blocklist-Basis) (`scripts/security_policy_defaults.py`)
- [x] Explizite SSRF-Schutzregeln für Resolver ergänzen und testen
- [x] XML-Input-Hardening für typische Angriffsvektoren dokumentieren (Entity-/DTD-/PI-Missbrauch, Ressourcenerschöpfung)
- [x] Security-Fallbacks/Fehlercodes standardisieren (klare, sichere Fehlermeldungen ohne sensitive Details)

### Security Scan-Tests (gezielte Fälle)

- [x] Scan-Test: bösartige URI-Schemata (`file:`, `data:`, `gopher:`, `jar:`, `javascript:`)
- [x] Scan-Test: eingebettete Credentials und ungewöhnliche URI-Encodings
- [x] Scan-Test: SSRF-Muster (localhost/metadata-IP/private ranges/redirect chains)
- [x] Scan-Test: übergroße XML-Dokumente (Payload- und Memory-Stress)
- [x] Scan-Test: tiefe XML-Verschachtelung (Recursion/Depth-Stress)
- [x] Scan-Test: extreme Attributanzahl/-länge und QName-Kantenfälle
- [x] Scan-Test: kaputte/malforme SOAP-Envelope-Strukturen
- [x] Scan-Test: WSDL/XSD mit problematischen Import-Ketten (Zyklen, unerreichbare Endpunkte)
- [x] Scan-Test: Generator-Stabilität bei adversarial WSDL/XSD-Eingaben
- [x] CI-Job `security-scan-smoke` mit kleinem Budget (schnell, deterministisch, non-flaky)

## DX & Doku

- README erweitern:
  - schnelle Startpfade für User vs. Maintainer trennen
- Architektur-Notizen:
  - "How parsing works", "How wsdl2py works"
- Troubleshooting:
  - typische Fehler + bekannte Lösungen

## Konkrete Checkliste

- [x] Profiling-Baseline erstellen (`test\test_zsi.py`, `test\wsdl2py\runTests.py local`)
- [x] Benchmark-Smoke mit einfachen Zeit-Budgets einführen
- [x] Top-2 Runtime-Hotspots in `ZSI/TCcompound.py` / `ZSI/parse.py` optimieren
- [x] `wsdl2py`-Output weiter deduplizieren (Imports, Boilerplate)
- [x] Option für schnelleren Generatorpfad (`--fast`) evaluieren/prototypen
- [x] Typannotationen in `ZSI/generate/*`, `ZSI/parse.py`, `ZSI/schema.py` starten
- [x] Lint/Format-Stack konsolidieren (`ruff`/`black` oder klar definierte Alternative)
- [x] CI-Matrix für `unit` + `integration-local` aufsetzen
- [x] Release-Checks automatisieren (Build+Test+Tag-Gates)
- [x] Fehlerdiagnostik verbessern (präzisere Exceptions mit WSDL-/Namespace-Kontext)
- [x] Security-Hardening für Resolver/Untrusted-Input dokumentieren und testen (`README.md`, `RELEASE.md`, `scripts/security_input_guard.py`, `test/test_security_input_guard.py`)
- [x] DX-Doku ergänzen (Architektur-Notizen + Troubleshooting)

## Refactoring Wave (abgeschlossen)

- [x] Chunk 1: Parse-Matching vereinfacht und beschleunigt
  (`ZSI/parse.py::ParseHeaderElements`, `ZSI/TCcompound.py::ComplexType.parse`)
- [x] Chunk 2: Resolve-Caching für `ofwhat` mit sicherer Invalidation ergänzt
  (`ZSI/TCcompound.py`)
- [x] Chunk 3: Diagnostik-Helfer zentralisiert (shared Kontext-/Exception-Helpers)
  (`ZSI/diagnostics.py`, Nutzung in `generate/commands.py`, `parse.py`, `schema.py`)
- [x] Regressionen geprüft: `test\test_zsi.py`, `test\wsdl2py\runTests.py local`,
  `test\wsdl2py\test_RuntimeDiagnostics.py`, `test\test_security_input_guard.py`

## Features (Next Next Level)

- [x] XSD Capability Matrix einführen (pro Schema: unterstützte Konstrukte, bekannte Limits, Workarounds)
- [x] Kompatibilitätsmodus für branchenspezifische "Schema v1.2"-Profile dokumentieren (z. B. CAP/GDTF) inkl. Beispielvalidierung
- [x] Optionaler Strict-Validation-Mode (`--strict-schema`) für frühzeitige Fehlererkennung in Generator und Runtime
- [x] Optionaler Compatibility-Mode (`--compat`) für toleranteres Parsing bei Legacy-Partnern
- [ ] Streaming-Parse-Prototyp für große SOAP-Payloads (geringerer Memory-Footprint)
- [ ] Namespaces/Type-Lookups mit gezielten Caches und Messpunkten weiter optimieren
- [x] Erweiterte Fault-Diagnostik mit korrelierbarer Request-ID und kompakter Context-Summary
- [x] Structured Logging (JSON) für Generator/Runtime/Resolver mit einheitlichem Event-Schema
- [x] OpenTelemetry-Hooks für Parse/Serialize/Resolver-Latenzen ergänzen
- [x] Security-Policy-Datei (Allowlist/Timeout/Retry/Limits) für Resolver zentral konfigurierbar machen
- [x] XML-Hardening-Testsuite für untrusted Input (Billion Laughs-ähnliche Muster, tiefe Rekursion, große Attribute)
- [x] Fuzzing-Smoke für Parser-/Typecode-Eingaben in CI (kleiner budgetierter Job)
- [x] Golden-File-Tests für `wsdl2py`-Output (Determinismus und Diff-Stabilität über Versionen)
- [x] Snapshot-Benchmarks mit Trendvergleich und CI-Warnschwellen erweitern
- [x] Multi-Python-CI auf 3.10/3.11/3.12 ausbauen
- [ ] Optionaler `mypy`-Pilot für ausgewählte Module (`generate/*`, `parse.py`, `schema.py`)
- [x] Public-API-Vertrag definieren und per API-Surface-Test absichern
- [x] Plugin-Hook-System für projektspezifische Generator-Anpassungen (ohne Fork-Zwang)
- [x] Migrationsleitfaden ZSI -> Zeep (Feature-Gaps, Risiko, Parallelbetrieb, Cutover-Plan)
- [x] Interop-Korpus aus realen WSDL/XSD-Beispielen als dauerhafte Regression-Suite aufbauen
- [x] Security/Release/Perf-Dashboards aus CI-Artefakten generieren (leichtgewichtig, statisch)

## Bewertung: Vorschläge aus `vorschlaege von chatgpt.txt`

- [x] Übernommen: Plugin-Hook-System für `wsdl2py` (`--plugin`, Hook-Lifecycle, Beispiel-Plugin, Tests)
- [x] Übernommen: Interop-Korpus als dauerhafte lokale Regression (`interop/*.wsdl` in `wsdl2py local`)
- [x] Bereits umgesetzt: Public-API-Vertrag, Security-Hardening, Snapshot-Benchmarks, strukturierte Diagnostik/Logging
- [ ] Geplant (hoher Nutzen): Operation-Dispatch-Index + `bind(service, port)` für eindeutiges Routing
- [x] Geplant (hoher Nutzen): Resolver-Caching mit reproduzierbarem Cache-Key (URL + Content-Hash)
- [ ] Geplant (hoch): Transport-Layer modernisieren (`timeout`/`verify`/`proxies`/Retries, SOAP 1.1/1.2 Header-Korrektheit)
- [ ] Geplant (mittel): Compact-CLI/One-liner (`zsi call <wsdl> <op> key=val`) als DX-Ausbau
- [x] Geplant (mittel): Zeep-Migrationsleitfaden mit Feature-Mapping und Cutover-Strategie
- [ ] Nicht Teil der aktuellen Umsetzung: optionaler `mypy`-Pilot (bewusst zurückgestellt)
- [ ] Vorerst nicht priorisiert: vollständiger "Zeep-Mode" API-Nachbau als eigener Betriebsmodus

## Definition of Done für Verbesserungen

- messbarer Nutzen (Zeit, Stabilität, DX)
- grün in Kernsuite + `wsdl2py local`
- dokumentiert in `CHANGES` + ggf. `README.md`/`RELEASE.md`

## Abschlussziel

- [x] Sämtliche Dokumentationen, Extensions und Samples sind auf den aktuellen
  Modernisierungsstand nachgezogen:
  `.md`-Dateien sowie Inhalte in `doc/`, `interop/`, `samples/` und `scripts/`
  wurden aktualisiert (inkl. Runbooks, DX-/Troubleshooting-Hinweisen und
  Security-/Release-Checks).
