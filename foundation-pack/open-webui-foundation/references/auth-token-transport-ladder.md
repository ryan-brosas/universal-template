<!-- capsule-v2 -->
# Auth token transport ladder — how do you authenticate one FastAPI dependency across header/cookie/custom-header transports without holding a DB session?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When the same credential can arrive as an Authorization header, a browser cookie, or a custom API-key header (because a reverse proxy may consume `Authorization` for itself), how does ONE dependency resolve the user without pinning a DB connection for the whole request?

## ASGI middleware normalizes three transports into scope state
**Path/Symbol:** `backend/open_webui/utils/asgi_middleware.py:AuthTokenMiddleware` (134-180).
**Signature:** `class AuthTokenMiddleware: def __init__(self, app: ASGIApp, *, fastapi_app) -> None; async def __call__(self, scope, receive, send) -> None`.
**Data Shape:** precedence is strict — `Authorization` header → `token` cookie → `CUSTOM_API_KEY_HEADER` (env default `x-api-key`, env.py:766); result stashed as `request.state.token` (`HTTPAuthorizationCredentials | None`). Non-http scopes pass through untouched. Also stamps `X-Process-Time` on response start.

### Decisive source
```python
token = get_http_authorization_cred(request.headers.get('Authorization'))
if token is None:
    cookie_token = request.cookies.get('token')
    if cookie_token:
        token = HTTPAuthorizationCredentials(scheme='Bearer', credentials=cookie_token)
if token is None:
    api_key = request.headers.get(CUSTOM_API_KEY_HEADER)
    if api_key:
        token = HTTPAuthorizationCredentials(scheme='Bearer', credentials=api_key)

request.state.token = token
```
(asgi_middleware.py 161-171)

**Flow:** pure-ASGI middleware (NOT BaseHTTPMiddleware — main.py:758-765 documents that the anyio task group wrapped by BaseHTTPMiddleware cancelled in-flight DB calls on client disconnect, surfacing as SQLAlchemy `terminate_force_close` tracebacks and CancelledError storms) → three-way credential extraction → stash on scope-backed state → wrap `send` to stamp process time. Stack position (main.py:766-779, last-added-runs-outermost): CORS ⊃ WebsocketUpgradeGuard ⊃ **AuthToken** ⊃ CommitSession ⊃ SecurityHeaders ⊃ Redirect; AuditLoggingMiddleware (added :745) sits outside all of them so it can read the resolved user on the way out.
**Invariant:** the dependency below must re-read all three sources itself (it does), so auth keeps working even if middleware ordering changes; the custom header exists precisely so deployments behind proxies that own `Authorization` don't 401-loop.

## The dependency: prefix dispatch + OAuth-state cleanup on failure
**Path/Symbol:** `backend/open_webui/utils/auth.py:get_current_user` (319-430).
**Signature:** `async def get_current_user(request: Request, response: Response, background_tasks: BackgroundTasks, auth_token: HTTPAuthorizationCredentials = Depends(bearer_security)) -> UserModel`, where `bearer_security = HTTPBearer(auto_error=False)` (:165).
**Data Shape:** `sk-`-prefixed tokens route to the API-key plane; everything else to the JWT arm; 401 on missing/invalid/revoked/unknown-user.

### Decisive source
```python
# Fallback to request.state.token (set by middleware, e.g. for x-api-key)
if token is None and hasattr(request.state, 'token') and request.state.token:
    token = request.state.token.credentials

if token is None:
    raise HTTPException(status_code=401, detail='Not authenticated')

# auth by api key
if token.startswith('sk-'):
    user = await get_current_user_by_api_key(request, token)
    ...
    # Scope-backed, so outer middleware (audit) can reuse the resolved user
    request.state.user = user
    return user
```
(auth.py 337-361, condensed)

**Flow:** bearer_security → cookie → state.token re-read → `sk-` dispatch → JWT arm: `decode_token` → `is_valid_token` revocation check → `Users.get_user_by_id` → optional trusted-email-header cross-check (`WEBUI_AUTH_TRUSTED_EMAIL_HEADER`) → fire-and-forget last-active update (`asyncio.create_task(Users.update_last_active_by_id(user.id))` :408) → stamp `request.state.user`.
**Invariant:** on ANY exception in the JWT arm, the handler deletes the `token`, `oauth_id_token`, AND `oauth_session_id` cookies before re-raising (:418-430) — failed JWT auth must clean OAuth session state, not just reject. The resolved user lives on scope-backed state so the outer audit middleware reuses it instead of re-running the pipeline: `utils/audit.py::_get_authenticated_user` (211-227) reads `request.state.user` first and only falls back to calling `get_current_user` directly when absent, with a comment naming the four avoided steps (JWT decode, Redis revocation checks, DB fetch, last-active write).
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "request.state.token = token" backend/open_webui/utils/asgi_middleware.py` → 171; `grep -n "Scope-backed, so outer middleware (audit)" backend/open_webui/utils/auth.py` → 359, 410; `grep -n "add_middleware(AuthTokenMiddleware" backend/open_webui/main.py` → 769; `grep -n "HTTPBearer(auto_error=False)" backend/open_webui/utils/auth.py` → 165. Graph caveat: trace_path inbound reports callers_total=2 for `get_current_user` while import census shows 310 `Depends(get_verified_user)` + 152 `Depends(get_admin_user)` sites transitively through it — FastAPI `Depends()` wiring is invisible to CALLS edges; verify fan-in from imports, not the graph.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "AuthTokenMiddleware get_current_user token cookie x-api-key transport", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-transport normalization with strict precedence, the scope-state handoff plus dependency-side re-read (defense against stack reordering), the `sk-` prefix dispatch, and the delete-all-OAuth-cookies-on-JWT-failure cleanup. Adapt the custom-header env name, the audit-middleware reuse contract, and the DB-session discipline (short-lived internal sessions, never `Depends(get_session)` in an auth dependency) to your host. Omit open-webui's OTEL span stamping and X-Process-Time header unless your observability plane wants them. Coverage caveat: all cited paths are graph-clean (`no_recorded_issue`, metadata_match) but have no upstream tests; claims pinned by direct source reads at the lines cited above.
