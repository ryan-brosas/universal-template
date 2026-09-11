<!-- capsule-v2 -->
# Input validation and output encoding — is all request data whitelisted and encoded at output boundaries?

**Source:** WebAppSec §Input Validation, §Output Encoding; QA Checklist input/SQL/XSS tests. **Question:** Does the app accept known-good input server-side and encode user data in every output context?

## Input seam
**Path/Symbol:** HTTP request surfaces — forms, query, hidden, cookies, headers.
**Signature:** whitelist regex + length bounds; server-side mandatory.
**Data Shape:** `[0-9a-zA-Z]{3,10}` username; rich HTML via sanitizer library.

### Decisive pattern
```python
# server — never trust client validation alone
if not USERNAME_RE.fullmatch(username):
    return generic_form_error()
# SQL — always parameterized
cursor.execute("SELECT id FROM users WHERE name = %s", (username,))
```

**Flow:** treat **all request data** as malicious — forms, URL params, hidden fields, cookies, headers → **accept known good** (whitelist regex + min/max length) — not blocklist of bad strings → **server-side** validation always (JS bypassable) → input validation is **secondary** — does not replace output encoding → **rich HTML** via HTML Purifier / AntiSamy / bleach → unexpected input → **graceful** generic error, no stack trace (**QA input test**).
**Invariant:** blocklist-only validation, client-only checks, or unhandled special chars in URL/hidden fields fail input review.
**Probe:** QA checklist — inject `<>&"'` in form, query, hidden; verify no 500/stack trace.

## Output seam
**Flow:** **XSS** — encode user data for **HTML/attribute/JS/CSS/URL context** (OWASP XSS cheat sheet) → **SQL** — **parameterized queries only** — no concat even if "probably not user controlled" → **OS** — avoid passing user data to shell; positive escape if unavoidable → **XML** — escape `< > " ' &`; escalate raw XML to security review.
**Invariant:** reflected/stored user string in HTML without context encoding, or dynamic SQL concat, fails output review.
**Probe:** QA SQLi + XSS tests; grep `"SELECT.*" +` / f-string SQL; template auto-escape audit.

## Verdict
Whitelist server validation plus context-aware output encoding and parameterized SQL. Learning note: `webappsec-style-learning-note.md`.
