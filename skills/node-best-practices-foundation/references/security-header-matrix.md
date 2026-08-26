<!-- capsule-v2 -->
# Security response-header matrix — which eight headers carry the protection, and what does each parameter actually gate?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What is the complete header set that defends a browser-facing Node service, with correct values?

## Eight-header defense matrix, settable via Helmet in one line
**Path/Symbol:** `sections/security/secureheaders.md` (HSTS :27-34, HPKP :44-55, XFO :65-72, XXSS :82-89, XCTO :99-104, Referrer-Policy :115-122, Expect-CT :133-140, CSP :149-154).
**Signature:** HTTP response headers, ideally via `helmet` (Express) / `koa-helmet`.
**Data Shape:** HSTS `Strict-Transport-Security: max-age=<s>; includeSubDomains`; HPKP `Public-Key-Pins: pin-sha256="..."(x N); report-uri; max-age; includeSubDomains`; XFO `deny|sameorigin|allow-from=<host>`; XXSS `1; mode=block; report=<url>`; XCTO `nosniff`; Referrer-Policy one of 8 values (`no-referrer` … `unsafe-url`); Expect-CT `max-age, enforce, report-uri="..."`; CSP `script-src 'self'` baseline.

### Decisive source
```text
// secureheaders.md :33 — canonical HSTS form
Strict-Transport-Security: max-age=2592000; includeSubDomains
// :153 — CSP floor
Content-Security-Policy: script-src 'self'
```

**Flow:** HSTS blocks protocol downgrade + cookie hijacking by forcing HTTPS-only UA contact; XFO denies frame embedding (clickjacking); XCTO stops MIME sniffing; CSP whitelists loadable origins (XSS defense-in-depth); Referrer-Policy throttles referer leakage across 8 strictness levels (strict-origin-when-cross-origin is the modern middle); Expect-CT enforces Certificate Transparency before trusting certs; HPKP pins expected public keys but the doc routes you to evaluate Expect-CT FIRST for misconfiguration recovery.
**Invariant:** headers are cumulative, not alternatives — dropping XCTO while keeping CSP still leaves content-sniffing open. HSTS `includeSubDomains` is load-bearing: a subdomain downgrade reopens the parent.
**Probe:** no runner upstream. Deterministic probe: `grep -c '^### ' sections/security/secureheaders.md` >= 8 (one section per header).
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "headers", "limit": 10}'
# resolves `sections/security/secureheaders.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the matrix wholesale via Helmet; hand-tune CSP to your actual origin set. Adapt HPKP → Expect-CT per current deprecation reality. Omit X-XSS-Protection in browsers that dropped the auditor, but know its `report=` form for legacy coverage.
