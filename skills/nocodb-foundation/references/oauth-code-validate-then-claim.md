<!-- capsule-v2 -->
# OAuth code exchange validate-then-claim — how does an authorization code stay single-use WITHOUT burning itself on a failed exchange?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb2`; Codebase Memory `nocodb`. **Question:** Where exactly does the single-use CAS sit relative to the precondition checks, and why?

## All preconditions first, THEN the atomic claim; markAsUsed is only a safety net
**Path/Symbol:** `packages/nocodb/src/modules/oauth/services/oauth-token.service.ts:exchangeCodeForTokens` (:129–251); CAS primitive `packages/nocodb/src/models/OAuthAuthorizationCode.ts:claimByCode` (:127–140); client gate `authenticateClient` (:88–127); claims builder `oauth-token.claims.ts` (:17–39).
**Signature:** `claimByCode(code): Promise<boolean>` — true ONLY if this caller won the CAS.
**Data Shape:** codes row {code, fk_client_id, fk_user_id, scope, resource, granted_resources, redirect_uri, code_challenge(+method), expires_at, is_used}; token response {access_token(JWT HS256), token_type 'Bearer', expires_in 3600, refresh_token(64-byte base64url), refresh_expires_in 60d, scope:'mcp', resource}.

### Decisive source
```ts
// Fast-path reject before CAS.
if (authCode.is_used) throw new Error('invalid_grant: Authorization code has already been used');
/* ... expiry → redirect_uri equality → PKCE (S256 only, verifier 43–128 chars,
   charset [A-Za-z0-9._~-], sha256-base64url equality) → authenticateClient ... */
// Atomic single-use claim deferred until all preconditions pass so a
// failing redirect_uri / PKCE / client auth check does not consume the code.
const claimed = await OAuthAuthorizationCode.claimByCode(code);
if (!claimed) throw new Error('invalid_grant: Authorization code has already been used');
await OAuthToken.insert(insertObj);
// markAsUsed is a safety net — claimByCode above already won the single-use race.
await OAuthAuthorizationCode.markAsUsed(code);

// model CAS: rowcount is the win signal
.update({ is_used: true })   // WHERE { code, is_used: false }
await NocoCache.del('root', `${CacheScope.OAUTH_AUTH_CODE}:${code}`);
```
(service :154–240 condensed; model :134–138)

**Flow:** getByCode → resource match → fast-path used-reject (cheap UX) → expiry/redirect/PKCE checks → authenticateClient (confidential ⇒ bcrypt secret EVERY grant — "PKCE proves the token request came from whoever started the flow; it does not authenticate the client"; public client SUPPLYING a secret = spoof signal ⇒ invalid_client) → mint access JWT + refresh token → claimByCode CAS (loser throws already-used) → OAuthToken.insert → markAsUsed + cache DEL.
**Invariant:** failing ANY precondition must leave the code consumable (claim is LAST); concurrent winners are decided by affected-row-count, never by read-then-write; the JWT carries MANDATORY `is_oauth_token:true` because OAuth tokens share the FIRST-PARTY JWT secret and JwtStrategy would otherwise accept them as xc-auth sessions bypassing OAuth bearer route confinement (GHSA-xmfr-pc8j-4xh5; cross-ref oauth-bearer-route-confinement). PKCE shape gates: method MUST be S256, verifier length 43–128 from the RFC 7636 alphabet.
**Probe:** `grep -c "invalid_grant" packages/nocodb/src/modules/oauth/services/oauth-token.service.ts` (=8 lines incl. the TODO comment) · `grep -c "claimByCode" packages/nocodb/src/modules/oauth/services/oauth-token.service.ts packages/nocodb/src/models/OAuthAuthorizationCode.ts` (=2 service + =1 model def) · `grep -c "S256" packages/nocodb/src/modules/oauth/services/oauth-token.service.ts` (=2) · `grep -c "is_oauth_token" packages/nocodb/src/modules/oauth/services/oauth-token.claims.ts` (=2: docstring + claim key).
**Direct test:** none upstream for this module beyond shells — probes pin shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "exchangeCodeForTokens claimByCode validatePKCE authenticateClient", limit: 10 });
```

## Verdict
Adopt validate-then-claim ordering with a rowcount CAS for any one-time grant/token (passwordless links, magic codes, webhook delivery receipts); adapt the precondition list and error taxonomy to your framework; omit the fast-path pre-check if you don't need its friendlier hot-path message (the CAS alone is sufficient for correctness). Coverage caveat: no behavioral upstream tests; full-file direct reads of service (:1–435), claims (:40L), and model CAS ranges.
