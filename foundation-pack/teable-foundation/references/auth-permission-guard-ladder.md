<!-- capsule-v2 -->
# Permission guard decision ladder — in what order does one NestJS guard resolve public/token/permission/share decorators into a single allow/deny?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When an endpoint carries several auth-related decorators plus share headers, what is the exact evaluation order and error-preservation contract a porter must reproduce?

## Guard ladder (`canActivate` → `permissionCheckWithPublicFallback`)
**Path/Symbol:** `apps/nestjs-backend/src/features/auth/guard/permission.guard.ts` : `PermissionGuard.canActivate` / `permissionCheckWithPublicFallback` (:596–687).
**Signature:** `canActivate(context: ExecutionContext): Promise<boolean>`; `permissionCheckWithPublicFallback(context, permissionCheck: () => Promise<boolean>): Promise<boolean>`.
**Data Shape:** Inputs are reflector metadata (`IS_PUBLIC_KEY`, `IS_DISABLED_PERMISSION`, `PERMISSIONS_KEY: Action[]`, `ANY_PERMISSIONS_KEY: Action[][]`, `IS_ALLOW_ANONYMOUS`, `IS_TOKEN_ACCESS`) read with handler-over-class override; request headers via `getTemplateHeader/getBaseShareHeader/getShareViewHeader`; CLS carries `user.id`, `user.isAdmin`, `accessTokenId`. Success stores resolved `ownPermissions` under cls `permissions`.

### Decisive source
```ts
// 1. RESOURCE-level: exclusively use resource-specific auth (base share > share view > template)
if (allowAnonymousType === AllowAnonymousType.RESOURCE) {
  const result = await this.resolveResourcePermission(context, baseShareHeader, shareViewHeader, templateHeader);
  if (result !== undefined) return result;
}
// 2. Share link — permissions are bounded by the link, regardless of user role
if (baseShareHeader) { const result = await this.tryBaseSharePermissionCheck(context, baseShareHeader); if (result !== undefined) return result; }
if (shareViewHeader) { const result = await this.tryShareViewPermissionCheck(context, shareViewHeader); if (result !== undefined) return result; }
// 3. Anonymous user handling
if (this.isAnonymous()) { return this.resolveAnonymousPermission(context, allowAnonymousType); }
// 4. Authenticated user: standard check, with PUBLIC fallback
try { return await permissionCheck(); } catch (error) {
  if (allowAnonymousType !== AllowAnonymousType.PUBLIC) throw error;
  return this.resolvePublicFallback(context, baseShareHeader, shareViewHeader, error);
}
```

**Flow:** `@Public()` or permission-disabled metadata short-circuits to `true`. Otherwise the four-step ladder runs; inside step 4's `permissionCheck()`: token pre-check (an `accessTokenId` on an endpoint with NO declared permissions passes only when `IS_TOKEN_ACCESS` is set), then empty permissions ⇒ login-is-enough `true`; `anyPermissions` alternative groups are tried after the primary group fails, preserving the primary error if every alternative fails too; `checkPermissions` dispatches special non-resource actions first (`instance|update`/`instance|read` require admin + token scope, `space|create`, `base|read_all`, `space|read` only when no resourceId, `user|integrations`) before falling through to resource-scoped `validPermissions`.
**Invariant:** Share headers act as a CEILING for authenticated users — when a share check resolves, the personal role is never consulted; anonymous users get PUBLIC→template-check / USER→allow / else 401; the fallback chain re-throws the ORIGINAL standard-check error after all fallbacks fail.
**Probe:** `apps/nestjs-backend/src/features/auth/guard/permission.guard.spec.ts` — pins that the primary permission wins without consulting `user.isAdmin`, that instance-admin alternatives unlock the route when the primary check rejects, and that rejection preserves the primary error message `not allowed to operate table|update on <tableId>`.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "teable", label: "Class", name_pattern: "^(PermissionGuard)$" })
→ PermissionGuard @ apps/nestjs-backend/src/features/auth/guard/permission.guard.ts lines 47-687 (executed live this pass)
```

## Verdict
Adopt the four-step ladder order and the anyPermissions primary-error-preservation semantics verbatim — both are behavior-pinned by the spec. Adapt decorator key names and CLS paths to host conventions. Omit the teable-specific action vocabulary (`space|create`, `base|read_all`) except as examples of user-level vs resource-level dispatch.
