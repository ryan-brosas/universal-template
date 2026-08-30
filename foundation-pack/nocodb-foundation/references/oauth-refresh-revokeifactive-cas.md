<!-- capsule-v2 -->
# Refresh rotation revokeIfActive CAS — where must the single-use guard sit so a failed mint doesn't destroy a still-valid token chain?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb2`; Codebase Memory `nocodb`. **Question:** Two concurrent refreshes present the same refresh token — who wins, and what ordering keeps a signing failure from revoking the survivor's chain?

## Generate first, CAS second; the loser is rejected instead of minting a twin chain
**Path/Symbol:** `packages/nocodb/src/modules/oauth/services/oauth-token.service.ts:refreshAccessToken` (:253–348); CAS helper `packages/nocodb/src/models/oauth-token.queries.ts:buildRevokeIfActiveUpdate` (:13–21); `OAuthToken.revokeIfActive` (:182–206).
**Signature:** `revokeIfActive(id): Promise<boolean>` — true iff THIS caller flipped an active token.
**Data Shape:** tokens row {access_token, access_token_expires_at, refresh_token, refresh_token_expires_at, scope, granted_resources, resource, is_revoked}; ACCESS=1h, REFRESH=60d.

### Decisive source
```ts
// Atomically revoke the presented refresh token, gating issuance of the new
// chain. This compare-and-swap is the single-use guard: two concurrent
// refreshes presenting the same token both pass the is_revoked check above,
// but only one wins revokeIfActive — the loser is rejected here instead of
// minting a second valid token chain. Done after token generation so a
// generateAccessToken failure does not burn the still-valid refresh token
// (GHSA-353r).
const revoked = await OAuthToken.revokeIfActive(tokenRecord.id);
if (!revoked) NcError.badRequest('Refresh token has been revoked');

export function buildRevokeIfActiveUpdate(knex, tableName, id) {
  return knex(tableName).where({ id, is_revoked: false }).update({ is_revoked: true });
}
```
(service :315–325; queries :18–20)

**Flow:** getByRefreshToken → revoked/expiry/client-id checks (plain reads) → authenticateClient → mint NEW access+refresh (rotation always, no reuse) → revokeIfActive CAS → loser rejected → winner inserts the new token row. Cache follows via `NocoCache.update('root', OAUTH_TOKEN:<accessToken>, {is_revoked:true})` keyed by the OLD access token.
**Invariant:** the read-level `is_revoked` check is advisory; correctness lives ENTIRELY in the WHERE-guarded UPDATE rowcount; the CAS deliberately runs AFTER minting so jwt.sign failure leaves the presented chain intact (documented advisory rationale). Known drift preserved by an in-code TODO: authorization-code grants throw RFC-6749 `invalid_grant: …` strings while refresh-grant failures use NcError.badRequest — alignment was deliberately kept out of the GHSA-353r fix to avoid changing response shapes mid-advisory. `revokeToken` returns TRUE for unknown tokens (RFC 7009-style idempotence) yet still rejects client mismatch; lookup honors tokenTypeHint with access-then-refresh fallback.
**Probe:** `grep -c "revokeIfActive" packages/nocodb/src/models/OAuthToken.ts packages/nocodb/src/modules/oauth/services/oauth-token.service.ts` (=1 model def + =2 service) · `grep -c "GHSA-353r" packages/nocodb/src/models/oauth-token.queries.ts packages/nocodb/src/modules/oauth/services/oauth-token.service.ts` (=1 + =2) · `grep -c "is_revoked: false" packages/nocodb/src/models/oauth-token.queries.ts` (=2: docstring quote + WHERE guard).
**Direct test:** none upstream for this module — probes pin shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "refreshAccessToken revokeIfActive buildRevokeIfActiveUpdate rotate", limit: 10 });
```

## Verdict
Adopt mint-before-CAS rotation with a WHERE-guarded single-row UPDATE as the concurrency arbiter for any refreshable credential; adapt TTL constants and whether old access tokens are blacklisted via cache; omit the dual-error-taxonomy drift (fix it in your port — NocoDB documents why THEY deferred it). Coverage caveat: grep-pinned only; direct read of all three files performed.
