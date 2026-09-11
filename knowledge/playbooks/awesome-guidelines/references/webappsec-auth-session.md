<!-- capsule-v2 -->
# Auth, session, and access control — do login, cookies, and authorization follow Mozilla WebAppSec?

**Source:** WebAppSec Secure Coding Guidelines §Authentication, §Session Management, §Access Control. **Question:** Are credentials, sessions, and permissions handled without enumeration, fixation, or IDOR?

## Auth seam
**Path/Symbol:** login, password reset, email verify flows.
**Signature:** generic errors; bcrypt+hmac storage; lockout + CAPTCHA.
**Data Shape:** ≥8 char mixed policy; reset message identical for valid/invalid accounts.

### Decisive pattern
```
POST /login → 401 "The username or password you entered is not valid"
POST /reset → 200 "An email has been sent…" (always)
DB: hmac+bcrypt(per-user salt); nonce off-database
```

**Flow:** enforce **password complexity** (≥8, letters+numbers; critical sites + special chars) → **generic login errors** — never reveal valid username vs bad password → **CAPTCHA or delay** after failed-attempt threshold; **log** auth events → **password reset** same response whether account exists → **email verify** links do **not** auto-login; codes expire on use or **8h** → store passwords with **hmac+bcrypt**; migrate weak hashes on successful login → delete **old hashes** (>1y or post-migration 3mo).
**Invariant:** user enumeration via login/reset, or plaintext/weak hash storage fails auth review.
**Probe:** login with bad user vs bad pass — identical response; grep for md5/sha1 password paths; reset flow timing.

## Session seam
**Flow:** session ID **≥128-bit** from **CSPRNG** → **new ID on login** → **15min** inactivity timeout (tune per app) → cookies **`Secure` + `HttpOnly`** → **logout** invalidates server session and clears client → admin pages: HTTPS only, brute-force controls (VPN/CAPTCHA/IP limit).
**Invariant:** session cookie over HTTP, reused pre-login session ID, or missing HttpOnly fails session review.
**Probe:** Set-Cookie flags; login rotates session id; logout clears access.

## Access control seam
**Flow:** **presentation** — hide unauthorized actions → **business layer** — authorize before every state change (crafted POST) → **data layer** — check user may act on **this record** (prevent IDOR).
**Invariant:** UI-only hiding or action-level auth without object-level check fails access control.
**Probe:** direct API/POST to other user's id; verify 403/404 consistent policy.

## Verdict
Generic auth errors, strong password storage, hardened session cookies, three-layer access control. Learning note: `webappsec-style-learning-note.md`.
