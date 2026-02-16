Roadmap:

[x] rewrite ZSI/resolvers.py to py3 (with help of six)
[x] iterative port/fix loop until tests run green

Status:

- `ZSI/resolvers.py` is Python-3 modernized.
- Core suite passes: `python test\test_zsi.py`
- Local wsdl2py integration suite passes: `python test\wsdl2py\runTests.py local`

Next candidates:

- optional cleanup/refactor of remaining legacy comments and historical compatibility shims
- extend release/docs maintenance (`RELEASE.md`, `README.md`) as changes land
