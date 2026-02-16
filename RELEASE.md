# ZSI Release Guide (Modernized)

This document is the maintained release blueprint for the current repository state.
The legacy `RELEASE` file remains unchanged as historical reference.

## Scope

This guide covers:

- preparing a release branch/state
- running mandatory validation
- tagging and publishing release artifacts
- announcing and documenting the release

## Release Checklist

1. Announce release intent to maintainers/contributors.
1. Ensure `README.md`, `CHANGES`, and relevant docs reflect the release scope.
1. Verify version metadata in `setup.cfg` (`[version]` and packaging-related fields).
1. Commit all pending release-relevant changes.
1. Run required tests in your active Python environment.
1. Create and push an annotated Git tag.
1. Build release artifacts from a clean state.
1. Validate artifacts in a fresh environment.
1. Publish release (GitHub/PyPI as applicable).
1. Announce release and link notes/changelog.

## Versioning

Primary version metadata is currently maintained in `setup.cfg`:

- `major`
- `minor`
- `patchlevel`
- pre-release markers (`candidate`, `alpha`, `beta`) when needed

Before tagging:

- update version values
- ensure `CHANGES` top entry matches the release version/date/status

## Mandatory Test Matrix

All commands below are expected to run from repo root (`K:\ZSI`).

Important:

PowerShell:

```powershell
python test\test_zsi.py
python test\test_zsi_net.py
python test\wsdl2py\runTests.py local
```

Notes:

- `test\test_zsi_net.py` may require network availability/external services.
- `test\wsdl2py\runTests.py local` is the key integration check for generator/runtime paths.

## Tagging

Use annotated tags. Recommended format:

- stable: `vMAJOR.MINOR.PATCH`
- pre-release: `vMAJOR.MINOR.PATCH-rcN` / `-aN` / `-bN`

Example:

```bash
git tag -a v2.1.0 -m "ZSI 2.1.0"
git push origin v2.1.0
```

## Build Artifacts

Build from a clean working tree:

```bash
git status
```

If clean, build:

```bash
python -m pip install --upgrade build
python -m build
```

Expected outputs in `dist/`:

- source distribution (`.tar.gz`)
- wheel (`.whl`)

## Artifact Validation

Validate install from built artifacts in a clean environment:

```bash
python -m pip install --force-reinstall dist\*.whl
```

Then rerun at least:

```bash
python test\test_zsi.py
```

For full release confidence, rerun the full matrix listed above.

## Publish

Typical publish targets:

- GitHub release (tag + release notes)
- PyPI (if publishing policy allows)

PyPI upload flow (example):

```bash
python -m pip install --upgrade twine
python -m twine check dist/*
python -m twine upload dist/*
```

## Release Notes Content

Minimum recommended sections:

- highlights
- compatibility notes (Python version/runtime changes)
- migration notes
- known limitations
- test status summary

## Post-Release

1. Confirm tag and artifacts are accessible.
1. Post release announcement with links to:
   - tag/release page
   - `CHANGES`
   - upgrade notes (if any)
1. Start next development cycle (bump to next dev version if your workflow uses it).
