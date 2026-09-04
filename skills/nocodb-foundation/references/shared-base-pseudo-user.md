<!-- capsule-v2 -->
# Shared-base pseudo-user — how does an xc-shared-base-id header become authenticated roles, and which two checks block private-base sharing?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How do anonymous collaborators on a shared BASE authenticate, and what distinguishes them from shared-VIEW requests?

## Header→Base.getByUuid→role-bag pseudo-user
**Path/Symbol:** `packages/nocodb/src/strategies/base-view.strategy/base-view.strategy.ts:BaseViewStrategy.validate` (:13–:45 whole).
**Signature:** `async validate(req, callback)` — passport-custom `'base-view'`; trigger header `xc-shared-base-id`.
**Data Shape:** success user = `{roles: extractRolesObj(sharedBase.roles), base_roles: extractRolesObj(sharedBase.roles)}` — NO id/email; downstream `req.user.isPublicBase` + context stamping happen in AclMiddleware (acl-evaluation-ladder capsule).

### Decisive source
```ts
// block shared base for private base
if (sharedBase.default_role) {
  return callback(new UnauthorizedException(
    'Shared base feature is not available for private bases. Please contact the base owner for access.'));
}
// validate base id
if (!sharedBase || req.ncBaseId !== sharedBase.id) {
  return callback(new UnauthorizedException());
}
```
(:21–:32)

**Flow:** header present → resolve Base by share uuid → PRIVATE-BASE GUARD: a `default_role` on the share row means the base is private (share feature disabled — explicit message, not generic 401) → identity guard: share must match the request's ALREADY-RESOLVED ncBaseId (ExtractIds ran first) else generic unauthorized → mint pseudo-user from the SHARE's roles (not any user's). Shared-base requests therefore take AUTHENTICATED routes with is_public stamped in aclFn (:1110–:1114), unlike shared-view requests which stay anonymous.
**Invariant:** ordering of the two guards is deliberate — the friendly private-base error only fires when a share row EXISTS; a mismatched uuid gets the opaque error (no oracle distinguishing missing vs wrong-base shares). The strategy DEPENDS on ExtractIds having set ncBaseId — running it before id extraction makes every comparison undefined-vs-id and fails open into the generic branch.
**Probe:** `cd packages/nocodb && grep -n "default_role" src/strategies/base-view.strategy/base-view.strategy.ts` (:22 single guard site) and `grep -c "UnauthorizedException" src/strategies/base-view.strategy/base-view.strategy.ts` (=3: import :1 + two throw paths :23/:31).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "BaseViewStrategy xc-shared-base-id getByUuid default_role", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pseudo-user pattern and guard ordering (friendly-error-first, opaque-mismatch-second); adapt role derivation; omit if no shared-base surface. Coverage caveat: spec file construction-only at pin; count-pinned greps.
