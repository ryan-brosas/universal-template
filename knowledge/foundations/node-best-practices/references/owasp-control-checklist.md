<!-- capsule-v2 -->
# OWASP control checklist — the cross-cutting A2/A3/A5/A6/A7/A9/A10 items that have no single code home

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Which security controls are checklists rather than patterns, and what belongs on each?

## Seven OWASP families + PII + reporting files, each with concrete verifiable items
**Path/Symbol:** `sections/security/commonsecuritybestpractices.md` (A2 :35-44, A5 :46-52, A6 :53-63, A3 :65-74, A9 :76-82, A10 :85-89, A7 :91-96, PII :98-105, security.txt/SECURITY.md :107-122).
**Signature:** per-family bullet controls, e.g. auth rate limiting, id+access+refresh token triad, STRIDE threat modeling.
**Data Shape:** the three named primitives outside OWASP: `crypto.timingSafeEqual` (:19), `crypto.randomBytes` (:27), SSL/TLS everywhere (:7).

### Decisive source
```text
// commonsecuritybestpractices.md :42-43 — sample of decision-bearing items
- Auth rate limiting: Disallow more than X login attempts ... in a period of Y
- On login failure, don't let the user know whether the username or password
  verification failed, just return a common auth error
// :80 — the token triad
Provide the user with both 'id', 'access' and 'refresh' token so the access
token is short-lived and renewed with the refresh token
```

**Flow:** broken authentication (A2) → MFA, rotation, no default credentials, standard protocols only (OAuth/OIDC), unified error on login failure; broken access control (A5) → least privilege, role/service accounts, group-based permissions; misconfiguration (A6) → internal-only admin surfaces, secured/samesite/HttpOnly cookies, DDoS shields; sensitive data (A3) → vault storage (KMS/HashiCorp), encrypted transit, no secrets in logs; vulnerable components (A9) → image scanning, auto-patching, CloudTrail-class audit; logging (A10) → alert on suspicious + irregular-failure events; XSS (A7) → auto-escaping templating + CSP defense-in-depth (feeds `context-aware-output-escaping`).
**Invariant:** these are ORGANIZATIONAL controls — they fail silently because no single PR implements them; the doc's structure (checklist per family) is itself the pattern: audit against it periodically. Reporting surfaces are part of the surface: `/.well-known/security.txt` in production, SECURITY.md in OSS repos (:107-122).
**Probe:** no runner upstream. Deterministic probe: `grep -c '^## .*OWASP' sections/security/commonsecuritybestpractices.md` >= 7.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "authentication", "limit": 10}'
# resolves `sections/security/commonsecuritybestpractices.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt as the standing audit template for service reviews. Adapt tooling names to your stack (vaults, cloud audit services). Omit nothing — every line is independently actionable.
