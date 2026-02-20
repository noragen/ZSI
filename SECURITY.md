# Security Model Baseline (ZSI)

This document defines the current threat-model baseline for ZSI.
It is a living document and should be updated when parser/resolver/generator/runtime behavior changes.

## Scope

Covered components:

- XML/SOAP parser and runtime deserialization paths
- Resolver behavior for external URI/WSDL/XSD fetches
- `wsdl2py` generator input handling
- CI and release artifact checks

## Security Objectives

- Prevent unsafe remote/local resource access from untrusted input.
- Reduce SSRF and URI abuse risk in resolver paths.
- Keep parsing behavior predictable under malformed or adversarial payloads.
- Preserve release integrity via reproducible CI gates.

## Key Assets

- Host filesystem and local secrets on build/runtime machines
- Internal network endpoints reachable by resolver code
- Generated code artifacts (`wsdl2py` output) and release packages
- CI credentials, tags, and published artifacts

## Trust Boundaries

- Untrusted boundary: incoming XML/SOAP payloads, external WSDL/XSD, URI inputs
- Trusted boundary: repository code, reviewed CI workflows, signed/tagged release flow
- Mixed boundary: partner-provided schemas that may be syntactically valid but adversarial

## Threat Surfaces

- Parser: malformed XML, deeply nested structures, oversized attributes/payloads
- Resolver: blocked scheme bypass, embedded credentials, prefix confusion, internal host targeting
- Generator: adversarial schema graphs/import chains causing excessive processing or bad output
- CI/release: accidental gate removal, unvalidated artifacts, weak release check discipline

## Baseline Controls (Current)

- URI hardening guard in `scripts/security_input_guard.py`:
  - blocks risky schemes (for example `file`, `data`, `gopher`, `javascript`, `jar`)
  - enforces allowed schemes (default `https`)
  - rejects embedded credentials
  - supports trusted prefix allowlisting
- Regression tests in `test/test_security_input_guard.py`
- CI smoke job `security-scan-smoke` validates:
  - guard unit tests
  - allowlisted trusted URI acceptance
  - blocked-scheme rejection (`file://` must fail)

## Known Gaps / Next Hardening Steps

- Formal parser limits (depth/attribute/payload caps) are not fully enforced globally.
- SSRF protection should be expanded beyond scheme/prefix checks (redirect/IP-range policies).
- Security-focused fuzz/smoke coverage for parser/generator can be broadened.
- Security policy centralization (single config source for resolver limits) is pending.

## Release Gate Expectation

For security-relevant changes, release validation must include:

- `python test/test_security_input_guard.py`
- trusted URI smoke check with allow-prefix
- blocked URI smoke check expecting non-zero exit

See `RELEASE.md` and `.github/workflows/ci.yml` for operational gate details.
