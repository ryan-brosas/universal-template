---
name: security-and-hardening
description: "Use when auditing for security vulnerabilities, implementing auth or authz, handling secrets, or hardening against OWASP Top 10 - covers input validation, authentication, dependency auditing, and secure defaults."
invocation: entry
---

# Security & Hardening

## Core Principle

**Validate at every boundary and trust the types inside; deny by default and allow
explicitly.** Secrets never in code, logs, or git; authn ≠ authz; least privilege by
default; and every security event gets logged, never the secrets themselves.

## When to Use / NOT

- **Use when:** auditing for security vulnerabilities, implementing auth or authz,
 handling secrets, or hardening against OWASP Top 10, input validation,
 authentication, dependency auditing, and secure defaults.
- **NOT when:** the change touches no external input, no authentication/authorization,
 no secrets, no dependencies, and no response headers, there is no security surface
 for this skill to apply.

## Iron Laws

<EXTREMELY-IMPORTANT>
- **Validate at every boundary.** Decode at the edge, trust the types inside.
- **Secrets never in code, logs, or git.** Env vars; vault for prod.
- **Authn ≠ Authz.** Who you are ≠ what you can do.
- **Least privilege by default.** Deny by default, allow explicitly.
- **Log security events.** Failed logins, denials, secret access, never the secrets themselves.
</EXTREMELY-IMPORTANT>

## OWASP Top 10 (Quick Map)

| Risk | Defense |
|-----------------|----------------------------------------------------|
| Injection | Parameterized queries, schema-validated input |
| Broken auth | Rate limit, MFA, bcrypt/argon2 |
| Data exposure | Encrypt at rest + transit, minimize retention |
| XXE | Disable external entities |
| Access control | Authz on every action, deny default |
| Misconfig | Secure defaults, no debug in prod, headers |
| XSS | Output encoding, CSP, no innerHTML with user input |
| Deserialization | Schema-validate, no eval on untrusted |
| Vulns (deps) | `npm audit`, Dependabot, lockfile pinning |
| Logging | Auth events, anomalies, access denials |

## Workflow

1. Map the surface against the OWASP Top 10 quick map above.
2. Validate all external input at the boundary (schema, reject unknown fields).
3. Implement authentication (hashing, rate limit, MFA, sessions) and authorization
 (check on every request; test the negative).
4. Handle secrets (env vars locally, CI secret store, vault for prod; rotate; scrub
 logs).
5. Audit dependencies (`npm audit`, lockfile pinning, advisories).
6. Set secure headers.
7. Verify per `Verification` below.

## Input Validation

Validate at the boundary; trust types inside. Schema (Zod, Effect Schema) for all external input; reject unknown fields by default; length, character class, and format limits per field.

## Authentication

bcrypt or argon2 for password hashing (never md5, sha1). Rate limit login (5 per 15 min per IP and per account); MFA for sensitive accounts. Sessions: random, signed, httpOnly cookie, short expiry; refresh tokens separate with rotation.

## Authorization

Check on every request; never trust the frontend. Use a policy engine (CASL, Oso) or explicit checks. Test the negative, "user A accesses user B's resource" must fail. Audit log access denials.

## Secrets

Env vars locally (never `.env` in git); CI secret store; vault for prod (HashiCorp Vault, AWS Secrets Manager). Rotate regularly and on suspected leak; never log secrets; scrub logs for known patterns.

## Dependencies

`npm audit` and `npm audit fix`; pin versions in the lockfile; review major bumps; subscribe to advisories.

## Secure Headers

Use `helmet()`, or set explicitly: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, `Content-Security-Policy: default-src 'self'`, `Referrer-Policy`.

## Common Mistakes

Plain-text passwords; md5/sha1; SQL string concat; "trust the frontend" authz; secrets in git; no rate limit on auth; session in localStorage; no CSP; logging secrets; no HTTPS; user-controlled redirects; eval on input; no CORS config; no security headers; default admin creds; error messages revealing internals.

## Red Flags

`.env` in git; bcrypt replaced with sha256; "auth later"; client-trusted user IDs; no rate limit; secrets in logs; no CSP; permissive CORS; default creds; SQL concat; eval on input; "private" routes without auth.

## Anti-Patterns

**"Auth later"**; **bcrypt-less**; **client-trusted IDs**; **no rate limit**; **secrets in code**; **"we're internal"**; **security by obscurity**.

## Verification

- Test the negative: "user A accesses user B's resource" must fail.
- Confirm no `.env` or secret material in git, logs, or error messages.
- Run `npm audit` and confirm lockfile pinning; confirm rate limiting on auth endpoints.
- Confirm secure headers are present in responses and security events (failed logins,
 denials) are logged without secret values.


## References

N/A, no reference files; defenses are fully covered by the tables and sections in this file.
