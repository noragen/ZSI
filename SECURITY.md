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

## Parser Security Baseline (Normative Richtwerte)

These limits are the default security baseline for untrusted XML/SOAP input.
They are intentionally conservative and may be tightened per deployment profile.

- Maximum XML element depth: `64` (hard fail)
- Maximum attributes per element: `64` (hard fail)
- Maximum attribute value size: `8192` bytes
- Maximum QName length (element/attribute names): `256` chars
- Maximum text node size: `1 MiB`
- Maximum SOAP/XML payload size: `5 MiB` (reject above limit)
- Maximum total parsed element count: `100000` nodes

Operational guidance:

- Parse untrusted data with strict limits enabled by default (fail-closed).
- Treat these as security defaults, not parser correctness guarantees.
- Changes to limits require a release-note entry and security sign-off in review.

## XML Hardening Guidance

For untrusted input, the parser/runtime baseline must enforce:

- `DOCTYPE` and DTD processing disabled.
- External entities (XXE) disabled.
- External schema/resource loading disabled unless explicitly trusted/allowlisted.
- XML Processing Instructions rejected or ignored in secure mode.
- XInclude and similar expansion mechanisms disabled.
- Resolver/network access disabled by default during parse unless explicitly required.

These controls are mandatory for default operation and may only be relaxed in explicit trusted-input profiles.

## Security Fallback and Error-Code Rules (No API Break)

To keep behavior stable without changing public exception APIs:

- Existing external exception types/messages remain source-compatible.
- Internally, map failures to stable security reason codes for logs/diagnostics.
- All security rejections fail closed (no permissive fallback to insecure parsing).
- User-facing errors stay minimal; sensitive internals (paths, tokens, internal hosts) must not be disclosed.

Standard security reason-code set:

- `ZSI-SEC-100` `URI_SCHEME_BLOCKED`
- `ZSI-SEC-110` `URI_CREDENTIALS_BLOCKED`
- `ZSI-SEC-120` `URI_PREFIX_DENIED`
- `ZSI-SEC-200` `XML_DEPTH_LIMIT_EXCEEDED`
- `ZSI-SEC-210` `XML_ATTRIBUTE_LIMIT_EXCEEDED`
- `ZSI-SEC-220` `XML_PAYLOAD_LIMIT_EXCEEDED`
- `ZSI-SEC-230` `XML_DTD_FORBIDDEN`
- `ZSI-SEC-240` `XML_PI_FORBIDDEN`

Fallback contract:

- CLI/tools: non-zero exit on blocked input.
- Runtime parse/resolver paths: deterministic failure, no retry with weaker policy.
- Logging: include reason code + bounded context only (for example input type, size bucket).

## Known Gaps / Next Hardening Steps

- SSRF protection should be expanded beyond scheme/prefix checks (redirect/IP-range policies).
- Security-focused fuzz/smoke coverage for parser/generator can be broadened.
- Security policy centralization (single config source for resolver limits) is pending.

## Release Gate Expectation

For security-relevant changes, release validation must include:

- `python test/test_security_input_guard.py`
- trusted URI smoke check with allow-prefix
- blocked URI smoke check expecting non-zero exit

See `RELEASE.md` and `.github/workflows/ci.yml` for operational gate details.
