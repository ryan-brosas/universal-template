<!-- capsule-v2 -->
# Embed JWT Lifecycle — how do you sign/verify a short-lived iframe token without letting alg=none or a stale secret through?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** Where do the TTL clamp, algorithm pinning, claim requirements, and sortable token-ID generation live in an HS256 embed-token service?

## Clamp-sign-return / decode-pin-raise pair
**Path/Symbol:** `packages/python/awaithumans/server/services/embed_token_service.py` — `_ALGORITHMS = [_ALGORITHM]` (:37-44), `_token_id` (:71-80), `sign_embed_token` (:86-133), `verify_embed_token` (:136-195), `EmbedClaims` frozen dataclass (:50-65).
**Signature:** `sign_embed_token(*, secret, task_id, sub, kind, parent_origin, ttl_seconds) -> tuple[str, int]`; `verify_embed_token(token, *, secret) -> EmbedClaims`.
**Data Shape:** claims `{iss:"awaithumans", aud:"embed", iat, exp, task_id, sub|None, kind, parent_origin, jti}`; jti = 13-hex timestamp-ms + 16-hex random = 29-char lowercase hex ("not a true ULID" per docstring); TTL clamped to [60, 3600] via constants; negative TTL raises ValueError BEFORE any crypto.

### Decisive source
```python
_ALGORITHM = "HS256"
_ALGORITHMS = [_ALGORITHM]   # MUST be a list so PyJWT's algorithm-pinning defence applies
...
clamped_ttl = max(EMBED_TOKEN_MIN_TTL_SECONDS, min(ttl_seconds, EMBED_TOKEN_MAX_TTL_SECONDS))
...
decoded: dict[str, object] = pyjwt.decode(
    token, secret,
    algorithms=_ALGORITHMS,      # allowlist pins HS256; rejects alg=none
    audience=EMBED_TOKEN_AUDIENCE, issuer=EMBED_TOKEN_ISSUER,
    leeway=EMBED_TOKEN_LEEWAY_SECONDS,
    options={"require": ["exp", "iat", "aud", "iss"]},
)
```

**Flow:** sign → validate ttl ≥ 0 → clamp → build payload with iss/aud/iat/exp/jti → HS256 encode → return `(token, exp_unix)` (exp returned so callers forward it WITHOUT re-parsing). Verify → PyJWT decode with allowlist+aud+iss+leeway+required-claims → map each PyJWTError subclass to `InvalidEmbedTokenError(reason=...)` (expired/audience/issuer/algorithm/generic ladder) → check custom claims `task_id/kind/parent_origin/jti` all truthy → check `kind in _SUPPORTED_KINDS` (only `"end_user"` at this pin) → freeze into `EmbedClaims`.
**Invariant:** downstream consumers receive an ALREADY-VERIFIED `EmbedClaims` and must never re-validate; verification failure is always `InvalidEmbedTokenError`, never a raw PyJWT exception.
**Probe:** `packages/python/tests/embed/test_token_service.py` (`test_alg_none_rejected`:122, `test_ttl_clamped_to_max`:171, `test_negative_ttl_raises_value_error`:192, `test_unsupported_kind_rejected`:227, `test_token_with_missing_required_claim_rejected`:242) — 34 passed at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "sign_embed_token verify_embed_token EmbedClaims", limit: 5 });
```
Live-verified rank-1/2 line-exact (:86-133, :136-195).

## Verdict
Adopt the list-form algorithms allowlist, TTL clamp-before-sign, exp-returned-not-reparsed contract, and typed error mapping; adapt constants and supported kinds to your product; omit the ULID-shaped jti only if you already have a sortable ID primitive. No coverage caveat — direct tests executed green.
