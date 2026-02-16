# ZSI Next-Level Improvements

Dieses Dokument sammelt konkrete Verbesserungen, um ZSI technisch, operativ und qualitativ auf das naechste Level zu bringen.

## Ziele

- Hoehere Performance bei Parse/Serialize und `wsdl2py`
- Modernere, wartbare Python-3-Codebasis
- Bessere Test- und Release-Sicherheit
- Klarere Developer Experience (DX)

## Prioritaeten

- `P0` = sofort hoher Nutzen / geringe bis mittlere Komplexitaet
- `P1` = hoher Nutzen / mittlere Komplexitaet
- `P2` = strategisch wichtig / groessere Arbeiten

## P0 Quick Wins

- Profiling-Baseline aufsetzen:
  - `cProfile`-Runs fuer `test\test_zsi.py` und `test\wsdl2py\runTests.py local`
  - Top-Hotspots je Lauf dokumentieren
- Performance-Regression-Guard:
  - kleiner Benchmark-Smoke (Zeitbudget + Trendvergleich)
- `wsdl2py`-Dedupe:
  - doppelte `pyclass_type`-Imports in generierten Stubs eliminieren
- Low-risk Micro-Optimierungen:
  - unnötige String-/List-Kopien in Parse/Serialize-Pfaden reduzieren
  - einfache Caches fuer wiederholte Namespace-/Lookup-Operationen
- Test-Hygiene:
  - flakey/umgebungsabhaengige Tests markieren/isolieren
  - stabile `local`-Testausfuehrung als Standard dokumentieren

## P1 Performance & Runtime

- Hotspot-Tuning in:
  - `ZSI/TCcompound.py`
  - `ZSI/parse.py`
  - `ZSI/writer.py`
- Lazy-Typecode-Pfad weiter haerten:
  - `_Mirage`/Reveal-Logik vereinheitlichen
  - wiederholte Instanziierungen minimieren
- XML-Handling evaluieren:
  - Kosten fuer DOM-Aufbau vs. gezieltere Verarbeitung messen
- Memory-Footprint:
  - grosse SOAP-Payloads (Streaming/inkrementelle Verarbeitung) untersuchen

## P1 Generator (wsdl2py) Next Steps

- Generierter Code:
  - konsistente Imports, keine Duplikate
  - einheitliche Exception-Syntax und Style
- Optionaler `--fast`-Modus:
  - weniger Runtime-Magie in generierten Klassen
  - mehr direkte Verweise, wo sicher
- Stabilitaet bei WSDL-Edge-Cases:
  - leere `wsdl:message`
  - schwierige substitution groups
  - große WSDLs (z. B. VIM) als Dauer-Regressionstest

## P1 Modern Python

- Typannotationen schrittweise einfuehren:
  - Start bei `generate/*`, `parse.py`, `schema.py`
- Lint/Format-Stack modernisieren:
  - `ruff` + `black` (oder klar definierte Alternative)
- Alte Kompatibilitaetsreste aufraeumen:
  - ungenutzte Legacy-Pfade, tote Kommentare, alte Namenskonventionen

## P2 Qualitaet & Architektur

- Klarere Modulgrenzen:
  - Generator, Runtime, Transport, XML-Tools staerker trennen
- API-Stabilitaet:
  - explizite Public API definieren
  - interne APIs markieren
- Fehlerbilder verbessern:
  - praezisere Exceptions mit Kontext (WSDL-Teil, Namespace, Operation)

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
  - untrusted XML-Szenarien pruefen
  - defensive Limits fuer große/rekursive Payloads

## DX & Doku

- README erweitern:
  - schnelle Startpfade fuer User vs. Maintainer trennen
- Architektur-Notizen:
  - "How parsing works", "How wsdl2py works"
- Troubleshooting:
  - typische Fehler + bekannte Loesungen

## Konkreter 4-Wochen-Plan

### Woche 1

- Profiling-Baseline + Benchmark-Smoke
- `wsdl2py`-Import-Dedupe

### Woche 2

- Top-2 Hotspots optimieren
- erste Typannotationen in `generate/*`

### Woche 3

- CI-Splits (`unit`, `local integration`)
- Fehlerdiagnostik verbessern (Exception-Kontext)

### Woche 4

- Release-Automation vorbereiten
- Doku-Politur (`README.md`, `RELEASE.md`, Troubleshooting)

## Definition of Done fuer Verbesserungen

- messbarer Nutzen (Zeit, Stabilitaet, DX)
- gruen in Kernsuite + `wsdl2py local`
- dokumentiert in `CHANGES` + ggf. `README.md`/`RELEASE.md`
