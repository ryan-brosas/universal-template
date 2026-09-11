<!-- capsule-v2 -->
# Auth-token base scoping — how does an xc-token request authenticate, and when must a base-scoped token be REJECTED rather than downscoped?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What identity does an API token produce, and where is the base-confinement boundary enforced?

## Token→pseudo-user with hard scope rejection
**Path/Symbol:** `packages/nocodb/src/strategies/authtoken.strategy/authtoken.strategy.ts:AuthTokenStrategy.validate` (:13–:86 whole).
**Signature:** `async validate(req: NcRequest, callback: Function)` — passport-custom strategy named `'authtoken'`; token read via `getApiTokenFromHeader` (`xc-token` header or Bearer).
**Data Shape:** success user = `{is_api_token: true, id?, email?, display_name?, roles, base_roles, workspace_roles?, org_roles?, extra?}`; legacy tokens (no `fk_user_id`) get ONLY `{is_api_token, base_roles: EDITOR}`.

### Decisive source
```ts
// Enforce the token's base scope. A token minted through a base-scoped
// endpoint carries a `base_id` and must only operate within that base;
// reject any request that targets a different base. Account-wide
// tokens leave `base_id` null and are unaffected.
if (
  apiToken.base_id &&
  req['ncBaseId'] &&
  apiToken.base_id !== req['ncBaseId']
) {
  return callback({ msg: 'Invalid token' });
}
```
(:28–:40)

**Flow:** extract token → `ApiToken.getByToken` (miss = 'Invalid token') → scope gate ABOVE → legacy-token short-circuit returns editor pseudo-user WITHOUT user linkage → otherwise `User.getWithRoles(context, fk_user_id, {baseId: ncBaseId, workspaceId?})` resolves the REAL user's role bags so ACL sees person-roles, not token-roles → SSO extras appended via `apiToken.getExtraForUserPayload()` → `sanitiseUserObj` strips secrets before callback.
**Invariant:** cross-base requests are rejected outright ('Invalid token' — same message as unknown token, no oracle) — NEVER silently downscoped to another base; workspace/org-level routes with NO resolved `ncBaseId` skip the check and fall through to normal ACL (there is no target base to mismatch). The rejection depends on ExtractIds having already set `req.ncBaseId` — strategy ordering matters.
**Probe:** `cd packages/nocodb && grep -n "apiToken.base_id &&" src/strategies/authtoken.strategy/authtoken.strategy.ts` (:33 single three-clause site; spec file is construction-only — coverage caveat in-capsule) and `grep -c "extractRolesObj(ProjectRoles.EDITOR)" src/strategies/authtoken.strategy/authtoken.strategy.ts` (=1 legacy path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "AuthTokenStrategy ApiToken getByToken getWithRoles is_api_token", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reject-don't-downscope and the legacy-token compatibility shim; adapt header names and role defaults; omit SSO extra plumbing unless porting the token model wholesale. Companion capsule: api-token-sso-scoping.md owns the service-layer CRUD surface — this capsule owns the passport strategy.
