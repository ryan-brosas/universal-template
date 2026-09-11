<!-- capsule-v2 -->
# Cross-domain and transport — are CSRF, framing, third-party scripts, and TLS enforced end-to-end?

**Source:** WebAppSec §Cross Domain, §Secure Transmission, §CSP. **Question:** Are state-changing requests protected and authenticated traffic confined to HTTPS with defense-in-depth headers?

## CSRF and framing seam
**Path/Symbol:** state-changing HTTP endpoints, HTML responses.
**Signature:** per-session CSRF token; X-Frame-Options on HTML.
**Data Shape:** framework CSRF middleware preferred over custom.

### Decisive pattern
```http
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'; script-src 'self'
Set-Cookie: session=…; Secure; HttpOnly; SameSite=Lax
```

**Flow:** **CSRF token** unique per user session, large random, CSPRNG — validate on mutating requests — use **framework CSRF** (Django etc.) when available → reject action if token fails → **clickjacking**: **`X-Frame-Options: DENY`** unless SAMEORIGIN required → **3rd party scripts** — **host locally**; review script **updates** like new installs → **OAuth/social** — entire chain **HTTPS**; no 3rd-party beacon on page load without user click.
**Invariant:** state-changing POST without CSRF protection, or HTML without frame denial when embed not required, fails cross-domain review.
**Probe:** QA CSRF test; curl -I for X-Frame-Options; inventory external script src.

## Transport seam
**Flow:** **login page GET + POST** over **HTTPS** → **all authenticated pages and assets** (CSS/JS/img) over **HTTPS** — no mixed content → never serve login/authenticated pages on **HTTP** (redirect or warn to HTTPS) → deploy **HSTS** where possible → design for **CSP** — minimize **inline JavaScript**.
**Invariant:** authenticated session over HTTP or mixed passive/active content fails transport review.
**Probe:** crawl authenticated flow scheme; browser mixed-content warnings; STS header check.

## Verdict
CSRF tokens, frame denial, local vetted scripts, full HTTPS authenticated surface, HSTS/CSP-ready JS. Learning note: `webappsec-style-learning-note.md`.
