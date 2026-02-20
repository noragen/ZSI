# Schema v1.2 Profile Notes (Domain Schemas)

"Schema v1.2" in many ecosystems (for example CAP 1.2 or GDTF 1.2) usually means
*domain schema versioning*, not a new W3C XSD language version.

ZSI interpretation:

- Treat these artifacts as XSD 1.0/1.1-based schemas with profile-specific rules.
- Validate both:
  - technical XSD compatibility
  - domain profile constraints (naming, cardinality, required fields, conventions)

## Practical validation flow

1. Run `wsdl2py` generation on local profile schema/WSDL.
2. Run deterministic smoke checks for URI/XML guardrails.
3. Run profile-specific assertions in dedicated tests.

Example (local, Python commands only):

```powershell
python scripts\wsdl2py --strict-schema --output-dir .\_schema_check .\path\to\profile.wsdl
python scripts\security_scan_smoke.py --uri "https://schemas.example.internal/profile.wsdl" --xml-file .\samples\safe_soap.xml
python test\wsdl2py\runTests.py local
```

## CAP/GDTF-style profile checklist template

- Namespace and version URI matches expected profile version.
- Required top-level elements/types are present.
- Known profile-specific optionality/cardinality rules are asserted.
- Import/include graph is finite and locally reproducible.
- Generated stubs are deterministic across repeated generation.

## Known limits and recommendation

- If profile schemas use advanced constructs outside current support, keep a
  compatibility test with explicit expected behavior and workaround notes.
- Prefer adding profile-specific regression tests over broad runtime exceptions.
