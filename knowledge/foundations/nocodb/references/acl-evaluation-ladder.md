<!-- capsule-v2 -->
# Acl evaluation ladder — in what ORDER do personal-view, editor-restriction, scope-role, token-block, inheritance and source-readonly checks run inside @Acl?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the exact precedence of the eleven ACL gates, and which ordering property can a porter silently invert?

## Ordered gate ladder in aclFn + decorator metadata wiring
**Path/Symbol:** `packages/nocodb/src/middlewares/extract-ids/extract-ids.middleware.ts:AclMiddleware.aclFn` (:1073–:1305) · `intercept` reads Reflector metadata (:1307–:1358) · `export const Acl` SetMetadata factory (:1363–:1402).
**Signature:** `aclFn(permissionName, {scope='base', allowedRoles?, blockApiTokenAccess?, blockOAuthTokenAccess?, blockPublicBaseAccess?, extendedScope?}, context, req)`; `Acl(permissionName, opts)` returns a method decorator stacking seven SetMetadata keys + `UseInterceptors(AclMiddleware)`.
**Data Shape:** `req.user` carries `is_api_token/is_oauth_token/isPublicBase`, role bags per scope (`roles/base_roles/workspace_roles/org_roles`); roles normalize via SDK `extractRolesObj`; `getUserRoleForScope` maps scope→bag ('workspace'|'base'|'cloud-org'|'org').

### Decisive source
```ts
if (!req.user?.isAuthorized) NcError.unauthorized('Invalid token');
// ...isPublicBase stamps context...
// 1. non-owner filter/sort on someone else's PERSONAL view → forbidden
// 2. EDITOR on unowned personal OR any LOCKED view (21+ perms incl. sort/filter/viewUpdate/viewDelete) → forbidden
// 3. missing role bag for BOTH scope and extendedScope → forbidden
// 4. api-token / oauth / public-base blocks → typed errors
// 5. allowedRoles.some(role => roles[role]) OR bag has ANY known role key, else unauthorized
// 6. isAllowed ladder:
const isAllowed =
  isPersonalViewOwnerAllowed ||            // owner allowlist (33 perms)
  Object.entries(roles).some(([name, hasRole]) =>
    hasRole && rolePermissions[name] &&
    (rolePermissions[name] === '*' ||
      (rolePermissions[name].exclude && !rolePermissions[name].exclude[permissionName]) ||
      (rolePermissions[name].include && rolePermissions[name].include[permissionName]))) ||
  extendedScopeRoles && /* same with `${scope}_${permissionName}` */ ||
  isUserWithNoAccessLeavingWorkspace;      // NO_ACCESS user deleting SELF from workspace
```
(:1087–:1245 condensed; owner-only ops list :1108–:1121, editor gate :1136–:1152, self-leave escape :1203–:1210)

**Flow:** implicit GlobalGuard bootstrap when controller forgot `@UseGuards(GlobalGuard)` (errors CONSOLE.LOGGED not thrown — deliberate fail-open for auth plumbing only) → public-base stamping → personal-view gates (VIEW_KEY-dependent, so ExtractIds MUST have attached before) → scope-bag presence → token-class blocks → allowedRoles/known-role check → include/exclude permission resolution → readable error via `generateReadablePermissionErr` → source-readonly restriction tail: permissions listed in `sourceRestrictions.SCHEMA_READONLY/DATA_READONLY` re-load the Source and reject with `sourceMetaReadOnly`/`sourceDataReadOnly` (:1261–:1301; tableCreate without ncSourceId resolves the meta source).
**Invariant:** order is load-bearing — personal-view gates run BEFORE generic role checks so an editor's legal base role cannot override view ownership; the no-access self-leave escape runs LAST so it can only rescue the exact DELETE-self case. Include/exclude are mutually exclusive per role (module init throws); excludes inherit in REVERSE role order while includes inherit in role order (see acl-inheritance capsule). `extendedScope` keys are PREFIXED (`scope_permission`) — unprefixed lookups silently never match.
**Probe:** `cd packages/nocodb && sed -n '1073,1305p' src/middlewares/extract-ids/extract-ids.middleware.ts | grep -c "NcError\."` (=13 throw sites inside aclFn) and `grep -cn "async aclFn\|async intercept" src/middlewares/extract-ids/extract-ids.middleware.ts` (=2 region bounds at :1073/:1307 — ERRATUM pass 19 audit: shipped form carried a double-escaped `\|` alternation which matches nothing under single quotes; re-derived against live grep).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "AclMiddleware aclFn intercept SetMetadata blockApiTokenAccess sourceRestrictions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered ladder and the decorator→Reflector→interceptor wiring; adapt the permission vocabulary and error taxonomy; omit the cloud-org scope and OAuth/public-base blocks if your host lacks those token classes. Coverage caveat: no unit spec exercises aclFn (controller specs construction-only); probes are count-pinned greps.
