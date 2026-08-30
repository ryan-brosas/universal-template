---
name: webappsec-coding-practices
description: "Use when building or reviewing web apps — Mozilla WebAppSec auth/sessions, whitelist input, output encoding, CSRF/TLS/CSP, safe uploads, generic errors, and QA checklist verification."
disable-model-invocation: true
---

# WebAppSec Secure Coding Practices

Application skill for Mozilla WebAppSec Secure Coding Guidelines + QA checklist ingest (`awesome-guidelines`). General security baseline: `security-and-hardening`. Accessibility overlap: `wcag-accessibility-practices`.

## Core Principle

Secure web apps **validate all request data**, **encode at output boundaries**, **protect sessions on HTTPS**, and **authorize every action on every object** — with generic user errors and QA probes to prove it.

## When to Use / NOT

- Web apps, APIs with browser clients, login/session flows, file uploads.
- PR review on auth, forms, templates, cookies, headers, admin surfaces.

**NOT when:**

- Non-HTTP backend with no web surface — `security-and-hardening` primary.
- WCAG conformance audit — `wcag-accessibility-practices` (pair for CAPTCHA/error UX).
- Pure static markup — `frontend-markup-practices` + this for deployment headers.

## Workflow

1. **Quick wins** — HttpOnly+Secure cookies; HTTPS auth pages; validate all user data.
2. **Auth/session/access** — passwords, sessions, IDOR (`webappsec-auth-session.md`).
3. **Input/output** — whitelist + encoding + parameterized SQL (`webappsec-input-output.md`).
4. **Cross-domain/transport** — CSRF, framing, TLS, CSP (`webappsec-cross-domain-transport.md`).
5. **Uploads/errors/verify** — files, errors, QA checklist (`webappsec-uploads-errors-verify.md`).

## Red Flags

- Cookie missing Secure or HttpOnly
- Login or authenticated assets over HTTP / mixed content
- Username enumeration on login or password reset
- Weak password hashing (md5/sha1) without migration
- Session ID not rotated on login
- Authorization only in UI or only by action type
- Blocklist input validation; client-only validation
- SQL string concatenation with user input
- Unencoded user data in HTML/JS templates
- State-changing POST without CSRF token
- Remote third-party script without update review
- Missing X-Frame-Options on HTML
- Inline JS blocking CSP adoption
- User-controlled upload filename or path
- Wrong Content-Type on user uploads
- Stack traces or SQL errors shown to users
- DEBUG enabled in production

## Verification

- Mozilla QA checklist probes on changed endpoints (input, SQLi, XSS, CSRF, X-Frame)
- Cookie and session flag inspection
- HTTPS-only auth flow crawl
- Parameterized query audit on changed data access
- Template/output encoding review
- Upload test cases (extension spoof, archive size)
- Pair with `npm audit`/dependency check from `security-and-hardening`

## Skill Result Contract

```xml
<skill_result>
  <skill>webappsec-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>diff, header/cookie audit, QA probe results</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>IDOR, missing CSRF, or upload content-type bypass</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/webappsec-style-learning-note.md`
- `awesome-guidelines/references/webappsec-auth-session.md`
- `awesome-guidelines/references/webappsec-input-output.md`
- `awesome-guidelines/references/webappsec-cross-domain-transport.md`
- `awesome-guidelines/references/webappsec-uploads-errors-verify.md`

## Related skills

- `security-and-hardening` — OWASP, secrets, dependencies, headers
- `wcag-accessibility-practices` — accessible error messages and forms
- `json-api-practices` — API contract security adjacent to CSRF/CORS
