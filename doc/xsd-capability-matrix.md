# XSD Capability Matrix (Initial)

Diese Matrix dokumentiert den initialen Stand der XSD-Unterstützung in ZSI anhand des vorhandenen lokalen Testkorpus (`test/` und `test/wsdl2py/`).

Statuswerte:

- `supported`: durch lokale Regressionen mit Parse/Serialize oder Dispatch abgedeckt
- `partial`: nur teilweise abgedeckt (z. B. nur Generierung oder ohne harte Assertions)
- `known limits`: bekannte Einschränkung im aktuellen Stand

## Matrix

| XSD/WSDL-Konstrukt | Status | Referenzierte Tests/WSDLs | Hinweise / Workaround |
| --- | --- | --- | --- |
| `complexType` + `sequence` + primitive Attribute (`int`, `double`, `float`, `decimal`, `dateTime`, `anyURI`, `QName`, `hexBinary`) | `supported` | `test/wsdl2py/test_Attributes.py`, `test/wsdl2py/wsdl/test_Attributes.xsd` | Roundtrip (SoapWriter + ParsedSoap) ist lokal abgedeckt. |
| `attributeGroup`-Einbindung (`<xs:attributeGroup ref=...>`) | `supported` | `test/wsdl2py/test_Attributes.py`, `test/wsdl2py/wsdl/test_Attributes.xsd` | Attribut-Gruppe `common` wird über den Testfall genutzt. |
| `choice` mit Default-Facets (`minOccurs=1`, `maxOccurs=1`) | `supported` | `test/wsdl2py/test_Choice.py`, `test/wsdl2py/wsdl/test_Choice.xsd` | Lokale Serialisierung für `EasyChoice` vorhanden. |
| `choice` mit `maxOccurs="unbounded"` | `supported` | `test/wsdl2py/test_Choice.py`, `test/wsdl2py/wsdl/test_Choice.xsd` | Listenbelegung für mehrere Choice-Zweige ist lokal abgedeckt. |
| `complexContent`-Extension (mehrstufige Vererbung `BaseActor -> MiddleActor -> TopActor`) | `supported` | `test/wsdl2py/test_DerivedTypes.py`, `test/wsdl2py/wsdl/test_DerivedTypes.xsd` | Parse/Serialize inkl. geerbter Elemente und Attribute wird geprüft. |
| Typ-Substitution via `xsi:type` auf abgeleitete Typen | `supported` | `test/wsdl2py/test_DerivedTypes.py`, `test/wsdl2py/wsdl/test_DerivedTypes.xsd` | Erfolgs- und Fehlerpfad (unbekannter Typ) sind als Regression vorhanden. |
| Substitution Group (`substitutionGroup='tns:baseElt'`) | `supported` | `test/wsdl2py/test_SubstitutionGroup.py`, `test/wsdl2py/wsdl/test_SubstitutionGroup.xsd` | Head-Element plus substituierendes Child wird roundtrip-geprüft. |
| `elementFormDefault="unqualified"`-Verhalten (lokale Elemente ohne Namespace) | `supported` | `test/wsdl2py/test_Unqualified.py`, `test/wsdl2py/wsdl/test_Unqualified.xsd` | Tag-Namen der lokalen Elemente werden explizit verifiziert. |
| Leere `wsdl:message` (0 Parts) bei doc/lit (`<wsdl:message name="..."/>`) | `supported` | `test/wsdl2py/test_NoMessagePart.py`, `test/wsdl2py/wsdl/NoMessagePart.wsdl` | Leerer SOAP-Body (`Body root is None`) ist lokal getestet. |
| `xsd:list` (TypeCode) | `supported` | `test/test_list.py` | Runtime-List-Typecode wird mit nillable und mehreren Einträgen geprüft. |
| `xsd:union` (TypeCode) | `partial` | `test/test_union.py` | Funktional vorhanden, aber Reihenfolge der `memberTypes` kann ambige Werte beeinflussen (siehe Kommentar "Union Limitation"). |
| `xs:gMonthDay` Attribut-Roundtrip | `partial` | `test/wsdl2py/test_Attributes.py`, `test/wsdl2py/wsdl/test_Attributes.xsd` | Test enthält auskommentierte Assertion; Verhalten nicht vollständig abgesichert. |
| `xs:base64Binary` und `xs:NOTATION` in Attributen | `partial` | `test/wsdl2py/test_Attributes.py`, `test/wsdl2py/wsdl/test_Attributes.xsd` | Im Test als TODO markiert, keine aktive Roundtrip-Assertion. |
| WSDL-Import-Kette (`<wsdl:import ...>`) mit eingebettetem `xsd:any` | `partial` | `test/wsdl2py/test_WSDLImport.py`, `test/wsdl2py/wsdl/test_WSDLImport.wsdl`, `test/wsdl2py/wsdl/test_WSDLImport2.wsdl` | Lokal im Wesentlichen Generierungs-/Ladepfad; keine inhaltliche Parse-Assertion auf `xsd:any`. |
| `xsd:list` in externen doc/lit-Interop-WSDLs | `known limits` | `test/wsdl2py/config.txt` (Kommentar zu `test_TerraService`) | In der Konfiguration als nicht unterstützt dokumentiert; Workaround: betroffene WSDL vorverarbeiten oder manuelle Typabbildung. |
| GED direkt als Substitution serialisieren (`_get_global_element_declaration` als direkter Ersatz) | `known limits` | `test/wsdl2py/test_DerivedTypes.py` (`test_local_ged_substitution`) | Test ist explizit als erwarteter Fehler (`TypeError`) angelegt; stattdessen GTD/abgeleitete Instanz verwenden. |

## Scope-Hinweise

- Fokus dieser initialen Matrix ist der lokal reproduzierbare Testkorpus.
- Remote-/Netzwerk-WSDLs aus `test/wsdl2py/config.txt` sind nicht als belastbare lokale Regression gewertet.
