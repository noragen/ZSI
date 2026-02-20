# Doc Notes

This directory primarily contains legacy LaTeX documentation and examples.

## 2026 modernization notes

- The historical `.tex` content is preserved as-is.
- Current operational guidance is tracked in:
  - `README.md` (repo-level)
  - `RELEASE.md` (release flow)
  - `doc/dx-parsing-wsdl2py-troubleshooting.md` (architecture + troubleshooting)
  - `doc/xsd-capability-matrix.md` (initial XSD construct support matrix)

## Validation baseline

```powershell
python test\test_zsi.py
python test\wsdl2py\runTests.py local
```
