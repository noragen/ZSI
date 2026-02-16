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
conda run -n zsi python -m pip install --upgrade pip
conda run -n zsi python -m pip install -r requirements.txt
conda run -n zsi python -m pip install -e .
```

Alternativ mit Mamba:

```powershell
mamba run -n zsi python -m pip install -r requirements.txt
mamba run -n zsi python -m pip install -e .
```

## Test-Run

Wichtig: Die Tests erwarten, dass das Repo-Root im `PYTHONPATH` liegt.

### Lokale Tests

PowerShell:

```powershell
$env:PYTHONPATH='.'
conda run -n zsi python test\test_zsi.py
```

### Tests inkl. Netzwerk

PowerShell:

```powershell
$env:PYTHONPATH='.'
conda run -n zsi python test\test_zsi_net.py
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
