<!-- capsule-v2 -->
# JWT issue/revoke algebra — how do you revoke stateless JWTs both per-token (sign-out) and per-user (IdP logout) with TTL-bounded Redis state?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When tokens are stateless HS256 JWTs, how do you make sign-out kill one token, IdP back-channel logout kill a whole user's tokens, keep revocation state from outliving the tokens it revokes, and still serve WebSocket handshakes that run outside the HTTP dependency chain?

## Issue: jti + iat always, exp optional
**Path/Symbol:** `backend/open_webui/utils/auth.py:create_token` (222-233) + `decode_token` (236-241).
**Signature:** `def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str`; `def decode_token(token: str) -> dict | None`.
**Data Shape:** payload = caller data + always-minted `jti` (uuid4) + `iat` (now); `exp` only when a delta is passed; signed with `SESSION_SECRET = WEBUI_SECRET_KEY`, `ALGORITHM = 'HS256'` (:47-48).

### Decisive source
```python
if expires_delta:
    expire = datetime.now(UTC) + expires_delta
    payload.update({'exp': expire})

jti = str(uuid.uuid4())
payload.update({'jti': jti, 'iat': datetime.now(UTC)})

encoded_jwt = jwt.encode(payload, SESSION_SECRET, algorithm=ALGORITHM)
```
(auth.py 225-232)

**Flow:** copy the caller payload (never mutate it) → add exp only if requested → mint jti/iat unconditionally → encode. `decode_token` swallows every exception and returns None — callers branch on None, never on exceptions.
**Invariant:** every token carries jti AND iat even when it never expires — both revocation mechanisms below depend on them, so "stateless forever" tokens must still be individually addressable.

## Revoke check: dual mechanism, fail-closed on legacy
**Path/Symbol:** `auth.py:is_valid_token` (244-273).
**Signature:** `async def is_valid_token(decoded, redis=None) -> bool`.
**Data Shape:** per-token key `{REDIS_KEY_PREFIX}:auth:token:{jti}:revoked`; per-user key `{REDIS_KEY_PREFIX}:auth:user:{id}:revoked_at` (epoch seconds); no Redis ⇒ everything valid (revocation is an opt-in capability).

### Decisive source
```python
# Per-user revocation (OIDC back-channel logout)
user_id = decoded.get('id')
if user_id:
    revoked_at = await redis.get(f'{REDIS_KEY_PREFIX}:auth:user:{user_id}:revoked_at')
    if revoked_at:
        try:
            revoked_at_ts = int(revoked_at)
            token_iat = decoded.get('iat')
            # No iat means legacy token — reject since we can't verify issue time
            if token_iat is None or token_iat <= revoked_at_ts:
                return False
        except (ValueError, TypeError):
            pass
```
(auth.py 259-271)

**Flow:** per-token jti lookup first (sign-out path) → per-user revoked_at comparison second (back-channel path): reject when `iat <= revoked_at`, reject FAIL-CLOSED when iat is missing entirely (legacy token whose issue time can't be verified), swallow unparseable revoked_at values (a corrupt marker must not lock everyone out).
**Invariant:** the two mechanisms are independent keys with independent writers — sign-out writes only the jti key, back-channel logout writes only the user key — so neither can accidentally clear the other's state.

## Write side: TTL-bounded sign-out + 30-day back-channel marker
**Path/Symbol:** `auth.py:invalidate_token` (276-297); writer twin `backend/open_webui/utils/oauth.py` back-channel logout (2255-2284).
**Signature:** `async def invalidate_token(request, token)`; sole caller `routers/auths.signout` (trace_path inbound callers_total=1).
**Data Shape:** jti key set to `'1'` with `ex=ttl` where `ttl = exp - now`; user key set to `str(int(time.time()))` with `ex=60*60*24*30`.

### Decisive source
```python
if jti and exp:
    ttl = exp - int(datetime.now(UTC).timestamp())  # Calculate time-to-live for the token

    if ttl > 0:
        # Store the revoked token in Redis with an expiration time
        await request.app.state.redis.set(
            f'{REDIS_KEY_PREFIX}:auth:token:{jti}:revoked',
            '1',
            ex=ttl,
        )
```
(auth.py 288-297)

**Flow:** decode → skip if already invalid/expired → require Redis → set jti key with TTL equal to remaining token life (revocation state self-expires with the token it revokes; no janitor needed). Back-channel writer: delete the user's OAuth sessions, then stamp the epoch into the user key with a 30-day TTL; when Redis is absent it logs a warning that existing JWTs remain valid until expiry — a documented degrade, not a silent no-op.
**Invariant:** revocation state must never outlive its subject: per-token TTL = token lifetime, per-user TTL bounded (30 days) so a forgotten marker can't permanently brick a re-issued identity.

## WebSocket handshakes outside the dependency chain
**Path/Symbol:** `auth.py:get_verified_user_by_token` (503-513).
**Signature:** `async def get_verified_user_by_token(token: str, redis=None) -> UserModel | None`.
**Data Shape:** returns None on any failure instead of raising HTTPException; role gate `VERIFIED_USER_ROLES = {'user', 'admin'}` (:491).

### Decisive source
```python
decoded = decode_token(token)
if decoded is None or 'id' not in decoded or not await is_valid_token(decoded, redis):
    return None

user = await Users.get_user_by_id(decoded['id'])
if user is None or user.role not in VERIFIED_USER_ROLES:
    return None
```
(auth.py 505-511)

**Flow:** duplicate of the HTTP arm's decode→revoke-check→lookup→role-gate, but returning None because socket.io connect handlers can't raise FastAPI HTTPExceptions mid-handshake. Seven traced callers: socket.main connect/join_channel/join_note/user_join, terminals ws_terminal/_resolve_authenticated_connection, channels get_channel_messages (2 hops).
**Invariant:** the WS path must enforce the SAME revocation checks as the HTTP path — a token revoked by sign-out or back-channel logout dies in sockets too; the only difference is the failure shape (None vs 401).
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "jti = str(uuid.uuid4())" backend/open_webui/utils/auth.py` → 229; `grep -n "auth:token:{jti}:revoked" backend/open_webui/utils/auth.py` → 255, 294; `grep -n "token_iat is None or token_iat <= revoked_at_ts" backend/open_webui/utils/auth.py` → 268; `grep -n "auth:user:{user.id}:revoked_at" backend/open_webui/utils/oauth.py` → 2270.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "create_token decode_token is_valid_token jti revoked", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-key revocation algebra (per-token jti for sign-out, per-user iat-comparison for IdP logout), the fail-closed legacy-token rule, the self-expiring TTL discipline, and the None-returning mirror for non-HTTP handshake surfaces. Adapt the Redis key layout and the 30-day user-marker bound to your threat model. Omit open-webui's no-Redis-everything-valid posture unless you deliberately treat revocation as an opt-in feature. Coverage caveat: all cited paths are graph-clean (`no_recorded_issue`, metadata_match) but have no upstream tests; claims pinned by direct source reads at the lines cited above.
