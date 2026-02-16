# ZSI

Fork von: http://pywebsvcs.svn.sourceforge.net/viewvc/pywebsvcs/trunk/zsi/

## Projektüberblick

`ZSI` (Zolera SOAP Infrastructure) ist eine Python-Bibliothek für SOAP/WSDL:

- SOAP-Nachrichten parsen/serialisieren
- Client- und Server-Unterstützung
- WSDL-basierte Stub-Generierung (`wsdl2py`)

## Voraussetzungen

- Mamba/Conda mit Environment `zsi`
- Python `3.x`

Abhängigkeiten:

- `six` (siehe `requirements.txt`)

## Installation im `zsi`-Environment

PowerShell (Windows):

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

Alternativ mit Mamba:

```powershell
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

- `improvements.md`

## Projekt-Update (Modernisierung, Stand: Februar 2026)

Dieser Abschnitt ergänzt die bestehende README und dokumentiert die zuletzt
integrierten Modernisierungen für Python 3 im Projekt.

### Was modernisiert wurde

- `wsdl2py`-Generatorpfade auf Python-3-kompatible Ausgabe stabilisiert
  (u. a. Klassenreferenzen, Metaclass-Syntax, Exception-Syntax).
- Laufzeitpfade für Lazy-Typecodes/Mirage robust gemacht
  (`ZSI/schema.py`, `ZSI/TCcompound.py`, `ZSI/generate/pyclass.py`).
- Doc/Lit-Edge-Case mit leerem SOAP-Body (`<wsdl:message/>` ohne Parts)
  über Generator, Dispatch, Parser und Writer durchgängig unterstützt.
- Legacy-Tests auf moderne Python-APIs angepasst (z. B. ElementTree-Zugriffe).

### Verifizierter Teststand

Im Environment `zsi` wurden erfolgreich ausgeführt:

```powershell
python test\test_zsi.py
python test\wsdl2py\runTests.py local
```

Aktueller Status:

- `test\test_zsi.py`: OK
- `test\wsdl2py\runTests.py local`: OK
