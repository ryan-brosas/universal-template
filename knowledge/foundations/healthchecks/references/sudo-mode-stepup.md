<!-- capsule-v2 -->
# Sudo mode + TOTP one-time buckets — session-scoped step-up auth where every guard is a TokenBucket

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How does a self-hostable app implement bank-style "confirm sensitive actions with a fresh code" using only Django sessions and the shared rate-limit table — and why is an expired code a silent miss rather than an error?

## require_sudo_mode + login_totp view
**Path/Symbol:** `hc/accounts/decorators.py:require_sudo_mode/_session_unsign` (:17-49), applied at accounts/views.py :579/602/684/719/755/790/804; TOTP view (:897-920); bucket wrappers `TokenBucket.authorize_sudo_code` (10/day), `authorize_totp_attempt` (96/24h), `authorize_totp_code` (1 per 90s).
**Signature:** `_session_unsign(request, key, max_age) -> str | None` (SignatureExpired → None, never raises); decorator flow: check "sudo" → check bucket → verify POSTed "sudo_code" → issue-or-reissue.
**Data Shape:** Session keys: `sudo` = TimestampSigner().sign("active") (30-min max_age), `sudo_code` = sign(6-digit) (15-min). Codes are "%06d" % secrets.randbelow(1_000_000) — zero-padded string comparison, not int.

### Decisive source
```python
# hc/accounts/decorators.py — the whole state machine
if _session_unsign(request, "sudo", 1800) == "active":
    return f(request, *args, **kwds)

if not TokenBucket.authorize_sudo_code(request.user):
    return render(request, "try_later.html")

if "sudo_code" in request.POST:
    ours = _session_unsign(request, "sudo_code", 900)
    if ours and ours == request.POST["sudo_code"]:
        request.session.pop("sudo_code")
        request.session["sudo"] = TimestampSigner().sign("active")
        return redirect(request.path)

if not _session_unsign(request, "sudo_code", 900):
    code = "%06d" % secrets.randbelow(1000000)
    request.session["sudo_code"] = TimestampSigner().sign(code)
    emails.sudo_code(request.user.email, {"sudo_code": code})

ctx = {}
if "sudo_code" in request.POST:
    ctx["wrong_code"] = True      # wrong code ≠ missing code: re-show form WITH hint
return render(request, "accounts/sudo.html", ctx)
```

**Flow:** Decorated view → active-sudo fast path → daily-bucket gate (10 sudo codes/day/user) → submitted-code verification → on success pop-then-replace (a used code can never re-arm) and redirect-to-self so the URL is clean GET → on failure re-render with wrong_code. TOTP twin: attempt bucket BEFORE validating (96/day ≈ 1 per 15 min), then authorize_totp_code capacity=1/refill=90s blacklists the exact verified code for its remaining validity window so an eavesdropped replay fails.
**Invariant:** Timestamped signing of SESSION-stored values means expiry checks survive server restarts without a clock column — but _session_unsign must map SignatureExpired to None (an expired sudo silently demotes to challenge, it never 500s). The pop-before-rearm ordering closes replay-via-reread; wrong-code vs no-code render differently because user confusion is the real UX failure mode. Bucket placement matters: sudo-code issuance burns budget even when the email never gets used — that's the anti-fatigue feature working as designed.
**Probe:** `hc/accounts/tests/test_sudo_mode.py::test_it_passes_through_if_sudo_mode_is_active`, `test_it_uses_rate_limiting`, `hc/accounts/tests/test_login_totp.py::test_it_rejects_used_code`, plus `hc/api/tests/test_tokenbucket.py::test_it_works` for the substrate.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "sudo mode totp authorize code session", limit: 10 });
```

## Verdict
Adopt signed-session step-up state machines, one-time-code buckets keyed by (user, code) with validity-matched refills, and silent-expiry semantics over hard errors. Adapt code delivery (email→SMS/authenticator) and budgets. Omit nothing from the pop-and-replace ordering or you own a replay window.
