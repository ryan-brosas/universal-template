# Mozilla WebAppSec secure web coding — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `webappsec-*.md` capsules, `webappsec-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [WebAppSec/Secure Coding Guidelines](https://wiki.mozilla.org/WebAppSec/Secure_Coding_Guidelines) (primary) | Auth, sessions, access control, input/output, CSRF, TLS, CSP, uploads, errors, quick wins |
| [WebAppSec/Secure Coding QA Checklist](https://wiki.mozilla.org/WebAppSec/Secure_Coding_QA_Checklist) (secondary verify) | QA tests for input validation, SQLi, XSS encoding, CSRF, X-Frame-Options |
| `security-and-hardening` (secondary) | OWASP map, secrets, headers — WebAppSec adds Mozilla web-app specifics |
| `wcag-accessibility-practices` (adjacent) | User-facing errors must not leak debug info — overlaps error handling |

**Scope:** **Web applications and web services** — server-side and template/API boundaries. **Not:** native mobile, kernel, or generic non-web backend without HTTP surface (`security-and-hardening` still applies).

## Mental model

Mozilla WebAppSec organizes by **security area**, not attack encyclopedia:

1. **Quick wins** — HttpOnly+Secure cookies; HTTPS for login + authenticated pages; validate all user-controlled data.
2. **Auth & sessions** — password policy, generic errors, bcrypt+hmac, session rotation, timeouts, cookie flags.
3. **Access control** — hide unauthorized UI; enforce in business + data layers per resource.
4. **Input & output** — whitelist validation on all request surfaces; **output encoding** primary for XSS/SQLi.
5. **Cross-domain & transport** — CSRF tokens, X-Frame-Options, local 3rd-party scripts, full HTTPS chain, HSTS, CSP.
6. **Uploads & errors** — rewrite/strip images, separate upload domain, generic user errors, no prod debug.

## Decision tables

### Easy quick wins

| Topic | Rule |
|---|---|
| Cookies | `HttpOnly` + `Secure` on all session cookies |
| HTTPS | Login + all authenticated pages (incl. assets) over TLS |
| Trust | Never trust input, headers, cookies — validate before use |

### Authentication

| Topic | Rule |
|---|---|
| Complexity | ≥8 chars; letters + numbers; blacklist common passwords |
| Critical sites | + special characters |
| Failed login | Generic message: "username or password not valid" |
| Lockout | CAPTCHA or delay after limit; log events |
| Reset | Same response whether account exists — no enumeration |
| Email verify | No auto-login; codes expire on use or 8h |
| Storage | hmac + bcrypt; per-user salt; nonce off-DB filesystem |
| Old hashes | Delete >1y; migrate on login |

### Session management

| Topic | Rule |
|---|---|
| ID length | ≥128 bits |
| ID creation | CSPRNG or server-managed |
| Timeout | Inactivity ~15 min recommended |
| Flags | Secure + HttpOnly always |
| Login | New session ID on login (anti-fixation) |
| Logout | Invalidate server-side + clear client |

### Access control

| Layer | Rule |
|---|---|
| Presentation | Don't show links/actions user can't use |
| Business | Authorize before executing action |
| Data | Authorize per target record, not just action type |

### Input validation

| Topic | Rule |
|---|---|
| Role | Secondary to output encoding; limits malformed data |
| Scope | Forms, URL params, hidden fields, cookies, headers |
| Approach | **Accept known good** (whitelist regex), not blocklist |
| Server | Always re-validate — JS validation bypassable |
| Rich HTML | HTML Purifier / AntiSamy / bleach |

### Output encoding

| Context | Rule |
|---|---|
| XSS | Encode all user data in HTML/JS/attr contexts appropriately |
| SQL | Parameterized queries always — no string concat |
| OS | Avoid user data to shell; positive escape if needed |
| XML | Escape `< > " ' &`; contact security for raw XML |

### Cross-domain & transport

| Topic | Rule |
|---|---|
| CSRF | Per-session random token; framework CSRF when available |
| Clickjacking | `X-Frame-Options: DENY` (or SAMEORIGIN if needed) |
| 3rd party scripts | Host locally; review updates like initial add |
| OAuth/social | Full HTTPS chain; no passive 3rd-party requests on page load |
| TLS | Login form page + POST + authenticated assets all HTTPS |
| HTTP | Never serve login/authenticated pages over HTTP |
| HSTS | Use STS where possible |
| CSP | Avoid inline JS to ease CSP adoption |

### Uploads

| Topic | Rule |
|---|---|
| Filename | Whitelist extension; server-generated storage name |
| Size | Max file and archive member size |
| Domain | Serve uploads from separate domain |
| Content-Type | Set from detected type, not client header alone |
| Images | Rewrite/strip with image library |
| Block | crossdomain.xml, .htaccess, clientaccesspolicy.xml |

### Error handling

| Topic | Rule |
|---|---|
| User messages | Generic — no stack traces or diagnostics |
| Debug | Stage only, never prod |
| Logs | Encode HTML in web logs; prevent log forging newlines |
| Design | Log detail server-side; show generic + optional error code |

### QA checklist (verify)

| Test | Pass criteria |
|---|---|
| Input | Special chars / wrong types in forms, URL, hidden → graceful |
| SQLi | Parameterized handling of user SQL inputs |
| Output encoding | User data encoded in HTML responses |
| CSRF | Token validated on state-changing requests |
| X-Frame-Options | Header on HTML responses |

## Anti-patterns

- Session cookie without HttpOnly/Secure
- Authenticated page with HTTP CSS/script (mixed content)
- Different error for bad username vs bad password
- Password reset reveals account existence
- MD5/sha1 password storage without migration plan
- Session ID reused across login
- Hidden admin links without server-side authz check
- IDOR — authorize action type but not row
- Blocklist-only input validation
- Client-only form validation
- SQL string concatenation with user data
- Reflected user input unencoded in HTML
- Custom CSRF when framework provides one
- Remote `<script src="cdn">` without update review
- Login over HTTP with redirect to HTTPS only on POST
- Inline JS blocking strict CSP
- User-controlled upload filename on disk
- Serving user upload from app origin with wrong Content-Type
- Stack trace shown to user
- Debug mode in production

## Skill trace

| Artifact | Role |
|---|---|
| `webappsec-auth-session.md` | auth + sessions + access control |
| `webappsec-input-output.md` | validation + encoding/injection |
| `webappsec-cross-domain-transport.md` | CSRF, framing, TLS, CSP |
| `webappsec-uploads-errors-verify.md` | uploads, errors, QA probes |
| `webappsec-coding-practices/SKILL.md` | secure web patch/review workflow |

## Relation to sibling skills

| WebAppSec | security-and-hardening |
|---|---|
| Web HTTP cookie/session specifics | General OWASP + secrets + deps |
| Mozilla bcrypt+hmac detail | bcrypt/argon2 general |
| CSRF/X-Frame/CSP web headers | Secure headers section |
| QA checklist probes | Verification workflow |

Pair with `wcag-accessibility-practices` for CAPTCHA UX and error message clarity.
