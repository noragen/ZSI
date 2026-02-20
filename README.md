# ZSI

Fork von: http://pywebsvcs.svn.sourceforge.net/viewvc/pywebsvcs/trunk/zsi/

## Projektüberblick

`ZSI` (Zolera SOAP Infrastructure) ist eine Python-Bibliothek für SOAP/WSDL:

- SOAP-Nachrichten parsen/serialisieren
- Client- und Server-Unterstützung
- WSDL-basierte Stub-Generierung (`wsdl2py`)

## Voraussetzungen

- Python `3.x`

Abhängigkeiten:

- `six` (siehe `requirements.txt`)

## Installation

PowerShell (Windows):

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Test-Run

### Lokale Tests

PowerShell:

```powershell
python test\test_zsi.py
```

### Tests inkl. Netzwerk

PowerShell:

```powershell
python test\test_zsi_net.py
```

### Security-Hardening-Checks (Resolver/Untrusted Input)

PowerShell:

```powershell
python test\test_security_input_guard.py
python scripts\security_input_guard.py --uri "https://schemas.example.internal/wsdl/service.wsdl" --allow-prefix "https://schemas.example.internal/"
```

Hardening-Leitlinien fuer Resolver-Input:

- Untrusted URIs nur absolut (`scheme://host/...`) annehmen.
- Standardmaessig nur `https` erlauben.
- Unsichere Schemes blockieren (`file`, `data`, `javascript`, `jar`, `ftp`, `gopher`).
- URIs mit eingebetteten Credentials (`user:pass@host`) ablehnen.
- Zugriff nur auf explizit gepflegte Trusted-Prefixe erlauben.
- Bei Resolver-Netzwerkzugriffen stets Timeouts setzen (z. B. `timeout=5`).

Minimales Integrationsmuster:

```python
from scripts.security_input_guard import validate_untrusted_uri
from ZSI.resolvers import NetworkResolver

uri = "https://schemas.example.internal/wsdl/service.wsdl"
validate_untrusted_uri(uri, allow_prefixes=("https://schemas.example.internal/",))
resolver = NetworkResolver(prefix=["https://schemas.example.internal/"])
result = resolver.Opaque(uri, tc, ps, timeout=5)
```

## Repo-Struktur

```text
ZSI/                 # Kernbibliothek
ZSI/generate/        # Code-Generatoren (u. a. wsdl2py)
ZSI/wstools/         # XML/WSDL-Hilfswerkzeuge
test/                # Unit-/Integrationstests
test/wsdl2py/        # Spezifische wsdl2py-Testfälle
samples/             # Beispielcode
doc/                 # LaTeX-Dokumentation und Beispiele
scripts/             # CLI-Wrapper (z. B. wsdl2py)
```

## Weiterentwicklung

Eine priorisierte Next-Level-Roadmap für Performance, Modernisierung und Qualität:

- [improvements.md](improvements.md)

## DX-Doku

- Parsing + `wsdl2py` + Troubleshooting:
  [doc/dx-parsing-wsdl2py-troubleshooting.md](doc/dx-parsing-wsdl2py-troubleshooting.md)
- Doc-Index/Status:
  [doc/README.md](doc/README.md)
- Script-Tooling-Übersicht:
  [scripts/README.md](scripts/README.md)

## Projekt-Update (Modernisierung, Stand: Februar 2026)

Dieser Abschnitt ergänzt die bestehende README und dokumentiert die zuletzt
integrierten Modernisierungen für Python 3 im Projekt.

### Was modernisiert wurde

- `wsdl2py`-Generatorpfade auf Python-3-kompatible Ausgabe stabilisiert
  (u. a. Klassenreferenzen, Metaclass-Syntax, Exception-Syntax).
- `wsdl2py --fast` als Prototyp ergänzt (optional schnellerer Pfad:
  Lazy-Typecodes aktiv, `_server.py`-Generierung ausgelassen).
- Laufzeitpfade für Lazy-Typecodes/Mirage robust gemacht
  (`ZSI/schema.py`, `ZSI/TCcompound.py`, `ZSI/generate/pyclass.py`).
- Doc/Lit-Edge-Case mit leerem SOAP-Body (`<wsdl:message/>` ohne Parts)
  über Generator, Dispatch, Parser und Writer durchgängig unterstützt.
- Legacy-Tests auf moderne Python-APIs angepasst (z. B. ElementTree-Zugriffe).
- Dev-Qualitätsstack konsolidiert mit `ruff` + `black`
  (`requirements-dev.txt`, `pyproject.toml`, CI-Lintjob).
- Refactoring-Welle (Speedup + Vereinfachung) umgesetzt:
  - Header-Matching in `ParsedSoap.ParseHeaderElements` auf gruppiertes QName-Mapping
  - `ComplexType.parse` mit sicherem Fast-Path (unordered Fälle) und geringerem Matching-Overhead
  - `ComplexType`-internes Resolve-Caching für `ofwhat` inkl. Invalidation bei Inhaltsänderungen
  - zentrale Diagnostik-Utilities in `ZSI/diagnostics.py` statt duplizierter Kontextlogik

### Verifizierter Teststand

Erfolgreich ausgeführt:

```powershell
python test\test_zsi.py
python test\wsdl2py\runTests.py local
python test\wsdl2py\test_RuntimeDiagnostics.py
python test\test_security_input_guard.py
```

Aktueller Status:

- `test\test_zsi.py`: OK
- `test\wsdl2py\runTests.py local`: OK
