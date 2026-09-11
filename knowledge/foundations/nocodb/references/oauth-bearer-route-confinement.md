<!-- capsule-v2 -->
# OAuth bearer route confinement — which routes may an OAuth token reach, and why must granted-resource matching FAIL CLOSED on context-less routes?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How are OAuth bearers restricted to MCP/V3 surfaces, and what stops a base-restricted grant escaping through context-less routes?

## Allowlist paths + fail-closed resource match
**Path/Symbol:** `packages/nocodb/src/strategies/oauth-token.strategy.ts:OAuthTokenStrategy.validate` (:14–:147 whole).
**Signature:** `async validate(req, callback)` — passport-custom `'oauth-token'`; Bearer-only.
**Data Shape:** token row `{is_revoked, access_token_expires_at, fk_client_id, fk_user_id, granted_resources?: {workspace_id?, base_id?}, scope}`; user gains `is_oauth_token/oauth_client_id/oauth_granted_resources/oauth_scope/oauth_token_id`.

### Decisive source
```ts
const oauthAllowedPaths = ['/mcp', '/api/v3/', '/auth/user/me'];
if (!oauthAllowedPaths.some((p) => req.path?.startsWith(p))) {
  return callback({ msg: 'OAuth token does not permit access to this endpoint' });
}
// ...
// This must FAIL CLOSED: ... A missing context ... is a mismatch, not a
// licence to skip the check — otherwise a base-restricted bearer reaches
// other bases through context-less routes (CWE-863).
if (oAuthToken.granted_resources && !isContextExemptPath) {
```
(:74–:95)

**Flow:** Bearer parse → lookup + revoked check + expiry check → CWE-613 client-existence guard (deleting the client kills its tokens even if the token row survived) → `User.getWithRoles` → ROUTE ALLOWLIST (only /mcp, /api/v3/, /auth/user/me) → context-exempt set = identity lookup + MCP only → granted_resources match: workspace_id ≠ context.workspace_id OR base_id ≠ context.base_id rejects; MISSING context counts as mismatch (fail-closed) → sanitized user out.
**Invariant:** fail-closed direction is the whole point — `grantedResources.base_id && context?.base_id !== grantedResources.base_id` treats undefined context as MISMATCH because `undefined !== base_id` is true; writing the guard as "skip when no context" reopens the escape the comment names (CWE-863). Route allowlist runs BEFORE resource matching so V2/V1 routes never even reach grant evaluation.
**Probe:** `cd packages/nocodb && grep -cn "oauthAllowedPaths\\|CWE-863\\|CWE-613" src/strategies/oauth-token.strategy.ts` (=4 matches: CWE-613 comment :48, allowlist decl :74 + its use :76, CWE-863 comment :94).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "OAuthTokenStrategy granted_resources oauthAllowedPaths getByAccessToken is_revoked", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt allowlist-before-grant ordering and the undefined-context-is-mismatch comparison shape; adapt allowed prefixes and grant vocabulary; omit the EE workspace clause if you have no workspace tier. Coverage caveat: no unit spec for this strategy at pin; probes count-pinned greps.
