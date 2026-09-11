<!-- capsule-v2 -->
# API-key config gates — how do you gate API keys by runtime config, user permissions, AND endpoint allow-lists without trusting proxy-visible paths?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When a machine credential (`sk-…`) authenticates a user, what gate ladder keeps it from becoming a standing admin backdoor — and where must endpoint restrictions be enforced so no transport can bypass them?

## One batched config read, four gates in order
**Path/Symbol:** `backend/open_webui/utils/auth.py:get_current_user_by_api_key` (433-488).
**Signature:** `async def get_current_user_by_api_key(request, api_key: str) -> UserModel` (raises 401/403).
**Data Shape:** four runtime-config keys read in ONE call: `auth.enable_api_keys`, `user.permissions`, `auth.api_key.endpoint_restrictions`, `auth.api_key.allowed_endpoints`; keys are `sk-` + uuid4 hex (`create_api_key` :304-306).

### Decisive source
```python
config_values = await Config.get_many(
    'auth.enable_api_keys',
    'user.permissions',
    'auth.api_key.endpoint_restrictions',
    'auth.api_key.allowed_endpoints',
)

if not config_values.get('auth.enable_api_keys'):
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED)

if user.role != 'admin':
    user_permissions = config_values.get('user.permissions')
    if not await has_permission(
        user.id,
        'features.api_keys',
        user_permissions,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED)
```
(auth.py 443-460)

**Flow:** lookup user by key (401 if unknown) → single batched `Config.get_many` of all four keys (one round trip instead of four) → global enable gate → per-user permission gate (admins exempt) → endpoint-restriction gate.
**Invariant:** the enable flag and the permission flag are SEPARATE gates with the same 403 shape — an operator can disable API keys fleet-wide without touching any user's permissions, and can grant the feature to a subset without enabling it globally.

## Endpoint restrictions at the dependency layer, on the raw ASGI path
**Path/Symbol:** `auth.py:get_current_user_by_api_key` (462-474).
**Data Shape:** `allowed_endpoints` is a comma-separated string; match = exact path OR `allowed + '/'` prefix.

### Decisive source
```python
# Enforce endpoint restrictions — checked here (not in middleware)
# so it applies regardless of how the API key was transported
# (Authorization header, cookie, x-api-key header, etc.).
if config_values.get('auth.api_key.endpoint_restrictions'):
    allowed_endpoints = config_values.get('auth.api_key.allowed_endpoints', '')
    allowed_paths = [path.strip() for path in str(allowed_endpoints).split(',') if path.strip()]
    request_path = request.scope['path']  # Use raw ASGI path — not spoofable via Host header (CVE-2026-48710)
    is_allowed = any(request_path == allowed or request_path.startswith(allowed + '/') for allowed in allowed_paths)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
```
(auth.py 462-474)

**Flow:** restriction flag off ⇒ skip entirely; on ⇒ parse the comma list (whitespace-trimmed, empties dropped) → compare against `request.scope['path']` → exact-or-prefix match, else 403 ACCESS_PROHIBITED.
**Invariant:** two load-bearing choices are documented in-source: (1) enforcement lives in the DEPENDENCY, not middleware, so every transport into the shared token ladder (header/cookie/custom-header) hits the same allow-list; (2) the path comes from raw ASGI scope, not a Host-header-derived URL — the CVE-2026-48710 comment records that proxy-visible paths are spoofable. The prefix arm appends `/` so `/api/v1/auths` does not match `/api/v1/auths_evil`.

## Last-active asymmetry vs the JWT arm
**Path/Symbol:** `auth.py` :487 vs :408.
**Data Shape:** API-key path `await Users.update_last_active_by_id(user.id)`; JWT arm `asyncio.create_task(Users.update_last_active_by_id(user.id))`.

### Decisive source
```python
    await Users.update_last_active_by_id(user.id)
    return user
```
(auth.py 487-488)

**Flow:** the JWT arm fire-and-forgets the last-active write to avoid blocking interactive sign-in; the API-key arm awaits it because machine traffic has no interactive latency budget and the write is cheap relative to the gated request.
**Invariant:** both arms must update last-active at all — an API key that never touches the column makes "last seen" monitoring blind to machine usage.
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "CVE-2026-48710" backend/open_webui/utils/auth.py` → 468; `grep -n "'auth.api_key.endpoint_restrictions'" backend/open_webui/utils/auth.py` → 446, 465; `grep -n "await Users.update_last_active_by_id(user.id)" backend/open_webui/utils/auth.py` → 487; `grep -n "asyncio.create_task(Users.update_last_active_by_id" backend/open_webui/utils/auth.py` → 408.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "get_current_user_by_api_key endpoint restrictions allowed_endpoints", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the batched multi-key config read, the separate global-enable and per-user-permission gates, dependency-layer (not middleware) endpoint enforcement on the raw ASGI path with exact-or-`/`-prefix matching, and the admin exemption. Adapt the config key names and the permission system to your host. Omit open-webui's shared-403-detail choice if your clients need to distinguish "feature disabled" from "you lack permission". Coverage caveat: all cited paths are graph-clean (`no_recorded_issue`, metadata_match) but have no upstream tests; claims pinned by direct source reads at the lines cited above.
