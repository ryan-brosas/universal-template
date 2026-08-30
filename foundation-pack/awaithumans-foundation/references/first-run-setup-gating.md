<!-- capsule-v2 -->
# First-Run Setup Gating — how does an unauthenticated bootstrap route stay safe without a login?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What must a public-by-design setup endpoint do so a brand-new server can be claimed safely — and can never be claimed twice?

## Public route that gates ITSELF on token + user-count
**Path/Symbol:** `packages/python/awaithumans/server/routes/setup.py:create_first_operator` (:64–124) + `setup_status` (:48–56); URL builder `packages/python/awaithumans/server/app.py:_first_run_setup_url` (:198–215). Token module contract: `bootstrap-token-error-taxonomy.md`. Direct tests: `packages/python/tests/auth/test_setup_bootstrap.py`.
**Signature:** `async def create_first_operator(request, body: CreateOperatorRequest{token,email,password,display_name}, response, session) -> CreateOperatorResponse` (201; sets session cookie).
**Data Shape:** `GET /api/setup/status → {needs_setup: count_users==0, token_active: is_active() and count_users==0}`; `POST /api/setup/operator` one-shot → 201 + cookie, 403 invalid token, 409 any user exists, 429 per-IP rate-limited.

### Decisive source
```python
# Rate-limit per IP. The route is unauthenticated by design (the
# bootstrap token gates it), and the first-run window can stretch
# for hours/days ... long enough that an attacker discovering the
# install could grind the 32-byte token endlessly.
ip = client_ip(request)
if not SETUP_PER_IP.check(f"setup:{ip}"):
    raise HTTPException(429, ...)

# Re-check on the DB rather than only trusting the bootstrap flag:
# two concurrent /setup posts could both see `_completed=False`
# before the row commits.
if await count_users(session) > 0:
    bootstrap.mark_complete()          # self-heal the in-memory flag
    raise SetupAlreadyCompletedError() # 409 — even with a VALID token
if not bootstrap.verify_token(body.token):   # fail-closed, one-shot
    raise InvalidSetupTokenError()         # 403
user = await create_user(session, ..., is_operator=True)
bootstrap.mark_complete()
token = sign_session(user_id=user.id, is_operator=True)
response.set_cookie(DASHBOARD_SESSION_COOKIE_NAME, token, ...)  # no re-login
```

**Flow:** server boots with zero users → lifespan detects `count_users==0`, generates token IN-PROCESS (`_first_run_setup_url`), prints banner URL → operator opens `/setup?token=…` → dashboard posts credentials+token → rate-limit gate → DB user-count gate (409 forever once passed) → token verify (403 fail-closed) → create operator → mark complete → session cookie issued inline.
**Invariant:** authorization NEVER comes from the middleware for `/api/setup/*` (public prefix by design); it comes from the route's own ladder. The DB count check — not the in-memory `_completed` flag — is the concurrency truth, and passing it repairs the flag (`mark_complete()` on the 409 path too). One-shot semantics survive restart-before-completion: a regenerated valid token still 409s because users exist. Token verification stays fail-closed after completion.
**Probe:** `tests/auth/test_setup_bootstrap.py` (:66–78 wrong token ⇒ 403; :82–97 success sets session cookie; :101–115 second attempt with same valid token ⇒ 409; :119–125 routes bypass auth middleware; :128–140 ensure_token idempotent until mark_complete). Deterministic source probe (runner-blocked run): `grep -n 'count_users(session)' packages/python/awaithumans/server/routes/setup.py` → hits at both :52 and :95 (status read + write-path re-check).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "create_first_operator setup bootstrap token operator", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the self-gating public-route ladder (rate limit → durable-state re-check → token verify → create → immediate session), including the flag-self-heal on the conflict path. Adapt the credential store and session-cookie mechanics. Omit any middleware exemption beyond the minimal public prefix — every other route keeps normal auth.
