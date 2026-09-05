---
name: security-and-hardening
description: "Use when auditing for security vulnerabilities, implementing auth or authz, handling secrets, or hardening against OWASP Top 10 - covers input validation, authentication, dependency auditing, and secure defaults."
invocation: entry
---

# Security and hardening

Scope the actual boundary: who controls the input, what authority consumes it,
and what data or effect is at risk? A parser diagnostic fix does not require an
auth system, dependency overhaul or full web-security checklist. Use current
project contracts and advisories to choose the relevant defenses.

## Traps worth checking

- **Diagnostics are an output boundary.** Parser exceptions, source snippets,
  request URLs and nested causes can contain secrets. Prefer safe error classes
  and locations; test a synthetic sensitive value through stdout, stderr and
  public error responses. Pattern-based redaction alone misses unknown secrets.
- **Classification can bypass validation.** A text file containing binary bytes,
  an unexpected content type or a decoder fallback must not silently skip a
  required safety check. Reject unsupported input at its owner; distinguish
  rejected, scanned, skipped and partially scanned results.
- **Authentication is not resource authority.** Test another user's identifier,
  tenant and nested resource, not just unauthenticated access. Enforce access at
  the server-side operation, including bulk/background paths where relevant.
- **Validation is not interpretation safety.** Parameterize SQL, encode for the
  actual output context, and constrain file/URL destinations after resolution.
  For SSRF, redirects and DNS changes can cross the original destination check.
- **Use mature auth primitives.** Password hashing, session rotation and secure
  cookie handling belong to established libraries. Choose rate limits, expiry
  and MFA from the threat model, not universal numbers copied from a checklist.
- **Remediation can change behavior.** Review dependency fixes and lockfile diffs;
  do not blindly run an automatic audit fix. CSP, CORS, framing and HSTS settings
  must fit legitimate origins, embeds and deployment rather than being pasted
  as a supposedly universal secure header set.

Reproduce safely with synthetic data and test a legitimate control alongside
the attack. Use existing scanners and tests when they cover the boundary; add
a small regression at the escaped failure's owner when useful. Report what was
actually exercised and what remains outside the audit. Credential rotation and
production changes still require the appropriate authorization.
