# Migration Guide: ZSI -> Zeep

This guide outlines a pragmatic migration path for teams moving from ZSI to Zeep.

## Scope

- Keep service behavior stable during migration.
- Minimize cutover risk with parallel verification.
- Make feature gaps explicit before switching production traffic.

## Feature Mapping (Quick View)

| Topic | ZSI | Zeep | Notes |
| --- | --- | --- | --- |
| WSDL-driven client | `ZSI.generate` / `ServiceProxy` | `zeep.Client` | Both support generated operation calls. |
| SOAP fault handling | `Fault` / `FaultException` | `zeep.exceptions.Fault` | Normalize error mapping in adapter layer. |
| Transport tuning | legacy `http.client` paths | requests-based transport | Validate timeout/verify/proxy behavior explicitly. |
| Custom resolver/security policy | custom `resolvers.py` + guards | custom transport/plugins | Preserve SSRF and URI hardening rules. |
| Generated stubs | `wsdl2py` output modules | runtime model via Zeep | Plan replacement for direct stub imports. |

## Risk Categories

1. Contract mismatch: element naming, namespace handling, optional fields.
2. Behavior mismatch: fault mapping, retries, TLS/proxy handling.
3. Performance mismatch: parse/serialize latency and memory profile.
4. Security drift: resolver and XML hardening defaults.

## Recommended Migration Plan

1. Inventory current ZSI usage.
2. Select pilot operations with deterministic request/response fixtures.
3. Build adapter/facade so callers can switch implementation behind one interface.
4. Run parallel calls (shadow mode), compare semantic outputs.
5. Cut over by service/port/operation in controlled batches.
6. Keep rollback path to ZSI during stabilization window.

## Parallel Run Checklist

- Same WSDL version pinned for both clients.
- Same auth/TLS/proxy settings.
- Same timeout budget and retry policy.
- Compare:
  - business fields
  - fault code/fault text
  - status/error semantics
- Record mismatches as explicit compatibility decisions.

## Cutover Criteria

- Contract tests pass for target operations.
- Fault mapping approved for known negative cases.
- No unresolved P1/P0 mismatches in shadow run.
- On-call runbook updated for new error signatures.

## Rollback Strategy

- Feature flag per operation or service binding.
- Keep ZSI path live until post-cutover soak period ends.
- Preserve request/response tracing for incident diffing.

## Notes for This Repository

- Security baseline remains mandatory (`SECURITY.md`).
- Use local suites as migration confidence gates:
  - `python test/test_zsi.py`
  - `python test/wsdl2py/runTests.py local`
  - security smoke/fuzz scripts under `scripts/`.
