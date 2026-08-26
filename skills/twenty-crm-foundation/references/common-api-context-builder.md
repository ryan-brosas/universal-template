<!-- capsule-v2 -->
# common-api-context-builder — How does a tool call resolve role-based permissions and selectable fields before touching data?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** What is the auth-context → roleId → objectsPermissions → selectedFields ladder?

## common-api-context-builder
**Path/Symbol:** `packages/twenty-server/src/engine/core-modules/record-crud/services/common-api-context-builder.service.ts:CommonApiContextBuilderService.build` (:47-131) + `getObjectsPermissions` (:133-189).
**Signature:** `build({authContext: WorkspaceAuthContext, objectName, rolePermissionConfig?}): Promise<CommonApiContext>`; private `getObjectsPermissions({authContext, rolePermissionConfig?}): Promise<ObjectsPermissions>`.
**Data Shape:** context bundles queryRunnerContext (auth + flat maps + id index), selectedFields (all selectable minus restricted), flatObjectMetadata/field maps, and objectsPermissions.

### Decisive source
```ts
if (isApiKeyAuthContext(authContext)) {
  roleId = await this.apiKeyRoleService.getRoleIdForApiKeyId(authContext.apiKey.id, workspaceId);
} else if (isApplicationAuthContext(authContext) && isDefined(authContext.application.defaultRoleId)) {
  roleId = authContext.application.defaultRoleId;
} else if (isUserAuthContext(authContext)) {
  const userWorkspaceRoleId = await this.userRoleService.getRoleIdForUserWorkspace({...});
  if (!isDefined(userWorkspaceRoleId)) {
    throw new RecordCrudException('No role found for user workspace', ...INVALID_REQUEST);
  }
  roleId = userWorkspaceRoleId;
} else {
  throw new RecordCrudException('Invalid auth context - no authentication mechanism found', ...INVALID_REQUEST);
}
return rolesPermissions[roleId] ?? {};
```
(:154-188 — four-way ladder ending in fail-open-to-empty permission map.)

**Flow:** load cached flat entity maps (`getOrRecomputeManyOrAllFlatEntityMaps` for object+field+index) → resolve object by nameSingular through `buildObjectIdByNameMaps` with two not-found throws (:77-99) → resolve permissions by auth kind (API key → application default role → user-workspace role; unknown context throws) → derive `restrictedFields` for THIS object from its permissions → `getAllSelectableFields` subtracts restricted fields so every downstream query selects only permitted columns (:106-113).
**Invariant:** the permission map lookup `rolesPermissions[roleId] ?? {}` FAILS OPEN — an unknown role yields an empty restriction set (documented asymmetry vs the missing-user-role case which fails closed). Field-level restrictions are applied at SELECT construction time, not post-read filtering. All three metadata map families must come from ONE consistent cache snapshot.
**Probe:** `grep -n 'rolesPermissions\[roleId\] ?? {}' packages/twenty-server/src/engine/core-modules/record-crud/services/common-api-context-builder.service.ts` → line 188.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "getObjectsPermissions restrictedFields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the auth-kind→role resolution ladder with explicit throw for unresolvable contexts, select-time field restriction, and cache-snapshot consistency. Decide consciously whether your host wants the unknown-role fail-open (Twenty accepts it); document your choice. Omit NestJS DI specifics.
