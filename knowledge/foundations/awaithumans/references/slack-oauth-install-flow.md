<!-- capsule-v2 -->
# Slack OAuth Install Flow — how do you let operators install workspaces without letting strangers install THEIR workspace?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What gates protect /oauth/start and /oauth/callback, and in what order must callback verification run?

## Install-token start gate + cookie∧HMAC∧TTL triple on callback
**Path/Symbol:** `packages/python/awaithumans/server/routes/slack/oauth.py` — module docstring security model (:1-33), `_oauth_cookie_secure` (:72-74), `_error_redirect` (:77-80), `oauth_start` (:84-140), `oauth_callback` (:144-218).
**Signature:** GET `/oauth/start?install_token=` → RedirectResponse; GET `/oauth/callback?code&state&error` + state cookie → RedirectResponse.
**Data Shape:** state cookie `SLACK_OAUTH_STATE_COOKIE_NAME`, `max_age=600`, httponly, Secure iff PUBLIC_URL starts https://, SameSite=Lax, path scoped to `/api/channels/slack/oauth`.

### Decisive source
```python
if settings.SLACK_BOT_TOKEN:                     # single-workspace mode → OAuth off BY CONSTRUCTION
    raise HTTPException(503, ...)
if install_token is None or not hmac.compare_digest(install_token, settings.SLACK_INSTALL_TOKEN):
    raise HTTPException(403, "Install token required.")
...
if not cookie_state or not hmac.compare_digest(state, cookie_state):   # 1) double-submit cookie
    raise HTTPException(401, "OAuth state mismatch.")
if not settings.SLACK_SIGNING_SECRET or not verify_state(state, settings.SLACK_SIGNING_SECRET):
    raise HTTPException(401, "Invalid OAuth state.")                   # 2) HMAC, 3) expiry inside
```
Success path upserts the installation then DELETES the state cookie ("single-use — replays fail"); failure redirect also clears it. Error redirects urlencode the (length-capped) Slack error param into the dashboard URL.

**Flow:** start → mode-lockout check → credential-presence check → constant-time install-token compare → mint signed state → redirect to slack.com authorize with cookie bound. Callback → explicit `error` passthrough → code/state presence → cookie-match (constant-time) → HMAC verify + age check → oauth.v2.access exchange → required-field validation (team_id/bot_token/bot_user_id else 502) → upsert → success redirect with cookie invalidated.
**Invariant:** without the install-token gate anyone who knows PUBLIC_URL could install their own workspace and — winning default-resolution — receive the server's task notifications; the docstring records this as acceptable only while SLACK_INSTALL_TOKEN stays secret (BUILD_NOTES §4 for hosted multi-tenant).
**Probe:** `packages/python/tests/slack/test_oauth_security.py` (`test_start_rejects_wrong_install_token`:96, `test_start_rejects_when_bot_token_set`:105, `test_callback_rejects_state_cookie_mismatch`:152, `test_install_token_comparison_is_constant_time`:233) — suite green at pin (20 passed incl test_oauth_state.py).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "oauth_start oauth_callback install_token compare_digest", limit: 5 });
```
Live rank-1/3 line-exact (:84-140, :144-218).

## Verdict
Adopt the gate ORDER (mode lockout before credentials before token) and the cookie∧signature∧expiry triple; adapt the install-token bootstrap gate to real user auth for multi-tenant hosting (the source says so itself); omit the static-token-mode 503 only if you have no single-workspace mode. Suite executed green at pin.
