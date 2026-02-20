# ZSI CI Artifact Dashboard

Lightweight snapshot for Security / Release / Performance artifacts.

## Performance

| Case | Mean (s) | Max (s) | Budget (s) | Status |
| --- | ---: | ---: | ---: | --- |
| test_zsi | 0.394 | 0.394 | 30.000 | PASS |
| wsdl2py_local | 4.212 | 4.212 | 180.000 | PASS |

## Trend History

- History snapshots: `1`

## Security

- Source artifacts: `test/test_security_scan_smoke.py`, `scripts/security_scan_smoke.py`
- CI gate: workflow job `security-scan-smoke`

## Release

- Source artifacts: `scripts/check_release_gate.py`, `RELEASE.md`, `CHANGES`
- CI gate: workflow job `release-gates`

## Note

This dashboard is static and intended for quick inspection in PRs/artifacts.
