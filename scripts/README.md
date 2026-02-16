# Scripts

Modernized helper scripts for local development and release safety.

## Available tools

- `scripts/wsdl2py`: generator entrypoint
- `scripts/wsdl2dispatch`: dispatch generator entrypoint
- `scripts/profile_baseline.py`: cProfile baseline for core suites
- `scripts/benchmark_smoke.py`: runtime smoke benchmark with budgets
- `scripts/check_release_gate.py`: tag/release gate checks
- `scripts/security_input_guard.py`: untrusted resolver URI validation

## Typical usage

```powershell
python scripts\profile_baseline.py --top 20
python scripts\benchmark_smoke.py --runs 1
python scripts\check_release_gate.py --tag v2.1.0
python scripts\security_input_guard.py --uri "https://schemas.example.internal/wsdl/service.wsdl" --allow-prefix "https://schemas.example.internal/"
```
