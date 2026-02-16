# DX-Notizen: Parsing und `wsdl2py`

Kurze How-it-works-Notizen fuer den Alltag im Repository.

## Parsing: Wie es intern laeuft

Code-Einstieg: `ZSI/parse.py`.

1. `ParsedSoap(...)` liest XML in ein DOM (`fromString` oder `fromStream`).
2. Validierung der SOAP-Struktur:
   - genau ein Root-Element
   - Root muss `Envelope` sein
   - optional `Header`, danach `Body`
3. `Body` wird in `body_root` (Serialisierungs-Root) und `data_elements` aufgeteilt.
4. `Parse(typecode)` ruft den Typecode-Parser auf `body_root` auf.
5. Hilfspfade:
   - `FindLocalHREF(...)` fuer `href="#id"`-Aufloesung
   - `ResolveHREF(...)` fuer externe URI-Resolver
   - `ParseHeaderElements(...)` fuer Header-Typecodes

Wichtige Stellen:
- `ZSI/parse.py` -> `ParsedSoap.__init__`
- `ZSI/parse.py` -> `ParsedSoap.Parse`
- `ZSI/parse.py` -> `ParsedSoap.FindLocalHREF`
- `ZSI/parse.py` -> `ParsedSoap.ResolveHREF`

## `wsdl2py`: Wie es intern laeuft

CLI-Einstieg:
- `scripts/wsdl2py` -> ruft `ZSI.generate.commands.wsdl2py()` auf.

Pipeline:
1. Optionen parsen (`--schema`, `--lazy`, `--fast`, `--output-dir`, ...).
2. WSDL/XSD laden:
   - lokale Datei: `loadFromFile`
   - URL: `loadFromURL`
3. `_wsdl2py(...)` generiert:
   - `<name>_client.py`
   - `<name>_types.py`
4. Standardmodus: zusaetzlich `_wsdl2dispatch(...)` => `<name>_server.py`
5. `--fast`: lazy typecodes an, `_server.py` wird nicht generiert.

Beispiele (Python-Command-Style):

```powershell
python scripts\wsdl2py test\wsdl2py\wsdl\BasicComm.wsdl
python scripts\wsdl2py --fast test\wsdl2py\wsdl\BasicComm.wsdl
python scripts\wsdl2py --output-dir .\generated test\wsdl2py\wsdl\BasicComm.wsdl
python scripts\wsdl2py --debug test\wsdl2py\wsdl\BasicComm.wsdl
```

## Troubleshooting

### Parsing-Fehler

| Fehlerbild | Typische Ursache | Workaround |
|---|---|---|
| `ParseException: Document has no Envelope` | Antwort ist kein SOAP-Envelope (HTML/JSON/Fehlerseite) | Rohantwort loggen und `Content-Type`/Endpoint pruefen |
| `... not Body` / `Envelope has header but no Body` | SOAP-Struktur unvollstaendig oder falscher Namespace | SOAP-Envelope gegen WSDL/SOAP-Version pruefen |
| `Element found after Body` | Trailer-Elemente vorhanden, aber `trailers=False` | Parser mit `trailers=True` verwenden, falls Trailer erwartet sind |
| `Found DTD` oder `Found processing instruction` | Eingehendes XML enthaelt DTD/PI, wird aus Sicherheitsgruenden geblockt | Upstream XML bereinigen, nur SOAP-relevante Elemente senden |
| `Can't find node for HREF "#..."` | `href` zeigt auf nicht vorhandenes `id` | Payload auf konsistente `id`/`href`-Paare pruefen |
| `No resolver for "..."` | Externe URI-Aufloesung benoetigt, aber kein Resolver gesetzt | `ParsedSoap(..., resolver=callable)` setzen |

### `wsdl2py`-Fehler

| Fehlerbild | Typische Ursache | Workaround |
|---|---|---|
| `Expecting a file/url as argument (WSDL).` | WSDL-Pfad/URL fehlt | Aufruf mit genau einem WSDL-Argument starten |
| WSDL laedt nicht (lokal/URL) | Falscher Pfad, Netzwerkproblem, Import in WSDL nicht erreichbar | Absoluten Pfad testen, URL pruefen, lokale Kopie der Imports verwenden |
| `_server.py` fehlt | `--fast` aktiv | Ohne `--fast` laufen lassen, wenn Server-Skeleton gebraucht wird |
| Importfehler in generierten Modulen | Mehrfach generierte Dateien oder falscher Output-Ordner im `PYTHONPATH` | In sauberen Output-Ordner generieren und nur diesen importieren |

## Schnellcheck bei Problemen

```powershell
python scripts\wsdl2py --debug <WSDL-PFAD-ODER-URL>
python test\test_zsi.py
python test\wsdl2py\runTests.py local
```
