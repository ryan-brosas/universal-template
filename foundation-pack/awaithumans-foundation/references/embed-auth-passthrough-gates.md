<!-- capsule-v2 -->
# Embed Auth Passthrough Gates — when must a bearer middleware NOT touch the token?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How does one ASGI middleware verify embed JWTs while leaving service keys, session cookies' bearer twins, and disabled-feature requests completely alone?

## Default-None state + four pass-through arms before verify
**Path/Symbol:** `packages/python/awaithumans/server/core/embed_auth.py` — `SecretProvider` alias (:27), `EmbedAuthMiddleware.__init__` (:53-55), `.dispatch` (:57-102), `get_embed_ctx` (:108-115).
**Signature:** `EmbedAuthMiddleware(app, *, secret_provider: Callable[[], str | None])` — provider invoked PER REQUEST so secret rotation needs no restart.
**Data Shape:** success writes `request.state.embed_ctx = EmbedClaims`; every other arm sets `embed_ctx = None` FIRST so downstream handlers never hit AttributeError.

### Decisive source
```python
request.state.embed_ctx = None                      # default BEFORE any branch
header = request.headers.get("authorization", "")
if not header.lower().startswith("bearer "):        # non-bearer schemes pass
    return await call_next(request)
token = header.split(" ", 1)[1].strip()
if token.startswith("ah_sk_"):                      # service keys belong to another dependency
    return await call_next(request)
if token.count(".") != 2:                           # only JWT-shaped tokens are ours
    return await call_next(request)
secret = self._secret_provider()
if not secret:                                      # feature disabled → pass anonymous
    return await call_next(request)
try:
    claims = verify_embed_token(token, secret=secret)
except InvalidEmbedTokenError as e:
    return JSONResponse(status_code=401, content={"error": {"code": "INVALID_EMBED_TOKEN", "message": str(e)}})
request.state.embed_ctx = claims
return await call_next(request)
```

**Flow:** set default None → bearer-prefix gate → ah_sk_ prefix gate → JWT three-dot shape gate → configured-secret gate → verify → 401 envelope `{error:{code:"INVALID_EMBED_TOKEN"}}` on failure or claims on request.state on success.
**Invariant:** ONLY cryptographically-invalid embed JWTs get an early 401; every other bearer credential (admin tokens, dashboard sessions, Basic auth) must reach its own route/dependency untouched — dropping any of the four passthrough arms breaks coexisting auth schemes, not just convenience.
**Probe:** `packages/python/tests/embed/test_embed_auth_middleware.py` (`test_valid_bearer_sets_embed_ctx`:36, `test_basic_auth_header_passes_through_anonymous`:66, `test_invalid_bearer_token_returns_401`:77 asserting the INVALID_EMBED_TOKEN code).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "EmbedAuthMiddleware dispatch secret_provider embed_ctx", limit: 4 });
```
Live rank-1/2 line-exact (:57-102 dispatch, :108-115 accessor).

## Verdict
Adopt the default-state-then-gates ordering and the 401 error envelope; adapt the service-key prefix sentinel to your own credential namespace; omit the per-request provider indirection only if secrets truly never rotate mid-process. Direct middleware suite green at pin.
