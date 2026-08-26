<!-- capsule-v2 -->
# Session Cookie & Signed Handoff URLs — how do passwordless humans clear an auth wall they never registered for?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How does the middleware authenticate three caller classes at once, and how do DM/email links mint sessions without passwords?

## mac||body cookie + bound-field signed handoffs under one public-prefix gate
**Path/Symbol:** `packages/python/awaithumans/server/core/auth.py` — `_PUBLIC_PREFIXES` (:62–80), `SessionClaims/sign_session/verify_session` (:88–176), `DashboardAuthMiddleware.dispatch` (:216–246); handoffs `server/core/slack_handoff.py` (pipe-message sign :79–96) and `server/core/email_handoff.py` (case-insensitive recipient variant); exchange routes `server/routes/auth.py`.
**Signature:** `cookie = base64url(hmac(body)||body)`, `body = json({u,o,e})` canonical (sort_keys, no whitespace); `sign_handoff(user_id, task_id, exp_unix) -> str` over `f"{user_id}|{task_id}|{exp}"`.
**Data Shape:** claims {user_id, is_operator} only — display data deliberately unsigned-out (keeps cookie short, avoids stale rename); TTL 7 days.

### Decisive source
```python
# Middleware ladder (order matters):
if path.startswith("/embed/"):            return await call_next(request)  # JWT layer owns it
if not path.startswith("/api/"):          return await call_next(request)  # static assets pass
if _is_public_path(path):                 return await call_next(request)  # self-signed surfaces
if getattr(request.state, "embed_ctx", None) is not None: return await call_next(request)
if _has_valid_admin_token(request):       request.state.auth_admin_token = True; ...
claims = verify_session(cookie)           # else 401
request.state.auth_claims = claims
```
Handoff binding (why each query param exists):
```
u = directory user_id  → session is minted for THIS user, not a generic login
t = task_id            → leaked URL cannot read OTHER tasks
e = task.timeout_at    → link lives exactly as long as the task (day 6 of a 7-day approval still works)
s = HMAC(u|t|e)        → pipe-separator: no field can contain '|' (uuids + int)
```

**Flow:** notifier signs at post time → human clicks → route verifies HMAC + expiry → mints a REAL short-TTL session cookie → redirects to `/task?id=`; terminal-at-click-time STILL mints+redirects (read-only view beats a 410 stare). Email twin adds case-insensitive recipients (senders case-flip; re-rendered mail must keep working links) and auto-provisions a passwordless directory user on first click — `notify=` is implicit consent.
**Invariant:** single-use is DELIBERATELY NOT enforced on handoff URLs (blocks legit re-click; damage capped by expiry + short session TTL). Password change doesn't invalidate outstanding sessions (accepted v1 gap, documented future `session_version`). Admin bearer = compare_digest skeleton key accepting legacy `X-Admin-Token` too.
**Probe:** `tests/auth/test_session_tokens.py`, `tests/auth/test_slack_handoff_signing.py` (:38–111), `tests/auth/test_email_handoff_signing.py` (+case-insensitivity pin), `tests/tasks/test_route_authorization.py` (:120–137 non-operator create blocked).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "session cookie HMAC middleware", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt mac||body cookies with minimal claims, ordered middleware ladders, task-bound expiring handoff URLs, and implicit-consent provisioning. Adapt claim fields/TTLs. Omit Next.js dashboard redirect wiring (host surface).
