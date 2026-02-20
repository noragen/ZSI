# Scripts

Modernized helper scripts for local development and release safety.

## Available tools

- `scripts/wsdl2py`: generator entrypoint
- `scripts/wsdl2dispatch`: dispatch generator entrypoint
- `scripts/zsi.py`: minimal subcommand CLI (`call`)
- `scripts/zsi_call.py`: compact one-liner call helper (`zsi call` style)
- `scripts/profile_baseline.py`: cProfile baseline for core suites
- `scripts/benchmark_smoke.py`: runtime smoke benchmark with budgets
- `scripts/benchmark_snapshot.py`: Trendvergleich aktueller Benchmarks gegen Snapshot-Historie
- `scripts/build_dashboards.py`: statische Security/Release/Perf-Dashboard-Datei aus Artefakten bauen
- `scripts/check_release_gate.py`: tag/release gate checks
- `scripts/security_input_guard.py`: untrusted resolver URI validation
- `scripts/security_policy_defaults.py`: zentrale Security-Policy-Defaults fuer URI-Validierung
- `scripts/security_policy.json.example`: Beispiel fuer zentrale Policy-Datei
- `scripts/security_scan_smoke.py`: deterministischer Security-Scan fuer URI/XML-Smoke-Faelle
- `scripts/parser_typecode_fuzz_smoke.py`: reproduzierbarer Parser/Typecode-Fuzz-Smoke
- `scripts/wsdl2py_plugin_example.py`: Beispiel fuer `wsdl2py`-Plugin-Hooks
- `scripts/stream_parse_prototype.py`: Streaming-Scan-Prototyp fuer grosse SOAP-Payloads

## Typical usage

```powershell
python scripts\profile_baseline.py --top 20
python scripts\benchmark_smoke.py --runs 1
python scripts\benchmark_snapshot.py --current .perf\benchmark-smoke.json --history .perf\benchmark-history.json --update-history
python scripts\build_dashboards.py --benchmark-smoke .perf\benchmark-smoke.json --benchmark-history .perf\benchmark-history.json --out doc\ci-artifact-dashboard.md
python scripts\check_release_gate.py --tag v2.1.0
python scripts\security_input_guard.py --uri "https://schemas.example.internal/wsdl/service.wsdl" --allow-prefix "https://schemas.example.internal/"
python scripts\security_input_guard.py --policy-file scripts\security_policy.json.example --uri "https://schemas.example.internal/wsdl/service.wsdl"
python scripts\security_scan_smoke.py --uri "https://example.internal/service" --xml-file .\safe_soap.xml
python scripts\parser_typecode_fuzz_smoke.py --seed 1337 --cases 24
python scripts\stream_parse_prototype.py --xml-file .\samples\safe_soap.xml
python scripts\wsdl2py --plugin .\scripts\wsdl2py_plugin_example.py --output-dir .\generated .\test\wsdl2py\wsdl\BasicComm.wsdl
python scripts\zsi.py call .\test\wsdl2py\wsdl\BasicComm.wsdl Basic --port BasicServerSoapBindingSOAP MsgIn=\"hello\"
python scripts\zsi_call.py .\test\wsdl2py\wsdl\BasicComm.wsdl Basic --port BasicServerSoapBindingSOAP MsgIn=\"hello\"
```
