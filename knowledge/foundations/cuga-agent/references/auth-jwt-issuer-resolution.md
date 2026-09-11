<!-- capsule-v2 -->
# Issuer-resolved JWT validation — how do you validate tokens from ANY trusted issuer when the server doesn't know issuers at startup?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does a FastAPI dependency pick/build the right JWTValidator per request, and what does it do with roles that arrive as a dict?

## Per-issuer validator cache + unverified-iss discovery
**Path/Symbol:** `src/cuga/backend/server/auth/dependencies.py:14,126-253` (`_validator_cache`, `_get_validator_for_token`, `get_current_user`), `jwt_validator.py:23-79` (`JWTValidator.validate_and_decode`, `_extract_roles`, `to_user_info`).
**Signature:** `JWTValidator(jwks_uri, cache_ttl=3600, issuer=None, *, skip_verify=False, ca_bundle=None)`; `validate_and_decode(token, *, audience=None, algorithms=None) -> dict`; `async get_current_user(request) -> Optional[UserInfo]`.
**Data Shape:** `UserInfo(sub, email?, name?, roles?, raw_claims)`; validators cached keyed by issuer config so each distinct IdP gets one PyJWKClient.

### Decisive source
```python
# jwt_validator.py:44-52 — claim-shape tolerance is the contract
options={"verify_exp": True,
         "verify_iss": bool(self.issuer),   # only if configured
         "verify_aud": audience is not None} # only if requested
# _extract_roles: roles may be list OR IAM-style dict
if isinstance(roles_claim, dict):
    flat = []
    for v in roles_claim.values():
        if isinstance(v, list):
            flat.extend(str(r) for r in v)
    return flat or None
```
The per-token path (`_get_validator_for_token`) decodes ONLY the unverified payload to read `iss`, normalizes it via `issuer_allowlist.normalize_issuer_for_discovery` (https-only, params/query/fragment rejected, default-443 port stripped), looks up `_validator_cache[cache_key]`, and builds+stores a `JWTValidator` from the issuer's JWKS on miss. `get_current_user` tries the token-issuing validator first and falls back to the statically-configured OIDC validator. Role authorization (`require_auth` / `require_manage_access` / `require_chat_access`) degrades gracefully: disabled auth ⇒ pass-through with None user; enabled auth + no user ⇒ 401; role checks only run when authorization is separately enabled.

**Flow:** request → bearer token → unverified iss → normalize (reject non-https early) → cached validator → PyJWK signature check against issuer JWKS → conditional exp/iss/aud verification → UserInfo extraction (`sub` REQUIRED — ValueError without it; email/name fall back to `preferred_username`) → role-gated dependencies.
**Invariant:** The issuer URL from an unverified token must never be used unchecked — https normalization/rejection happens BEFORE any network fetch of its discovery document. Verification flags are opt-in per claim: enabling verify_aud without passing an audience breaks every token.

**Probe:** No dedicated unit test for dependencies.py in tests/unit — coverage caveat: pinned indirectly by integration auth flows; read source when porting. `realm_access`/dict-roles flattening is load-bearing for Keycloak vs IAM tokens.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "JWTValidator get_current_user validator_cache issuer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-issuer cache + normalize-before-discovery ordering + claim-tolerant role extraction. Adapt role claim names to your IdPs. Omit IAM instance-binding (separate seam) if you have no multi-tenant CRN tokens.
