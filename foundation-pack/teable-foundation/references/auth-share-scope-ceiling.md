<!-- capsule-v2 -->
# Share scope ceiling — how are base-share and share-view permissions derived, scoped to a subtree, and prevented from escalating?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do you grant read/edit through a share link without letting the link leak cross-base access or exceed its declared scope?

## Permission families (`PermissionService` share methods + guard endpoint rules)
**Path/Symbol:** `apps/nestjs-backend/src/features/auth/permission.service.ts` : `getBaseSharePermissions` (:613–665), `checkResourceBelongsToShare` (:675–696), `isTableLinkedFromSharedNode` (:744–790), `getBaseNodesWithCache` (:868–889), `validateBaseSharePasswordToken` (:592–611), `getShareViewPermissions` (:1074–1115); `guard/permission.guard.ts` : `shareViewEndpointRules` (:29–44), `tryShareViewPermissionCheck` (:430–479).
**Signature:** `getBaseSharePermissions(shareId, resourceId): Promise<Action[]>`; `validateBaseSharePasswordToken(shareId, token): Promise<boolean>`.
**Data Shape:** `baseShare` row `{shareId, enabled, baseId, nodeId|null, password, allowEdit, allowCopy}`; view row `shareMeta {password, allowEdit, includeRecords, allowCopy}`; success writes cls keys `baseShare {baseId,nodeId}` / `shareViewId`.

### Decisive source
```ts
// Always verify the requested resource actually belongs to the shared base.
// For a whole-base share (nodeId null) every resource in the base is reachable,
// but the base-membership check MUST still run — otherwise a share created for
// one base could be replayed with another base's id to gain cross-base access.
const resourceBelongsToShare = await this.checkResourceBelongsToShare(resourceId, baseId, nodeId);
if (!resourceBelongsToShare) { throw ... }
this.cls.set('baseShare', { baseId, nodeId });
if (baseShare.allowEdit && !this.isAnonymous()) {
  return getPermissions(Role.Editor).filter((p) => !shareExcludedPermissions.has(p));
}
const permissions = [...TemplatePermissions];
if (baseShare.allowCopy) { permissions.push('record|copy'); }
return permissions;
```

**Flow:** Header (`X-Tea-Base-Share`/`X-Tea-Share-View`, must start `shr`) → optional password gate (JWT cookie named by shareId carrying `{shareId,password}` is verified against the LIVE DB password, so changing the password silently invalidates all cookies) → resource-belongs dispatch by id prefix: base⇒id equality, table/view/field/app resolve up to their table then node-subtree check. Node-scoped shares compute the allowed set as shared node + descendants from a per-request cls-cached node list (`baseShareNodeCache`); a table OUTSIDE the subtree still passes if it is the `foreignTableId` of any link field on a shared table (link targets must remain reachable). Edit grants require logged-in identity and subtract a fixed exclusion set (`view|share`, invite/email/integration actions); anonymous or allowEdit-off ⇒ TemplatePermissions + optional `record|copy`. Share-view additionally gates edits on `includeRecords` AND an editable view type (Grid/Kanban/Gallery/Calendar) and restricts which endpoints may carry the header at all: POST/PATCH/DELETE only, path must match an explicit rule regex, and every declared permission must be inside that rule's set — anything else throws `notAllowedOperation`.
**Invariant:** The membership check runs even for whole-base shares (no nodeId) — replaying a shareId against another base's resource ids must fail; share-derived permissions never exceed Editor-minus-exclusions; finer record/view-level scoping is delegated to ShareViewScopeService before handler execution, not to the guard.
**Probe:** No dedicated upstream spec exists for these service methods (coverage caveat recorded). Deterministic probe: grep the guard's `shareViewEndpointRules` table and assert each rule's regex+permission pair against this excerpt; source lines above are the pin at 06a4461e.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__query_graph({ project: "teable", query: "MATCH (m:Method) WHERE m.file CONTAINS 'features/auth' AND (m.file CONTAINS 'permission.guard' OR m.file CONTAINS 'permission.service') RETURN m.name, m.file, m.line ORDER BY m.file, m.line LIMIT 80" })
→ executed live this pass; returned the full method roster incl. getBaseSharePermissions/isTableLinkedFromSharedNode/getBaseNodesWithCache line anchors
```

## Verdict
Adopt: always-run membership check, subtree closure with request-scoped caching, link-target escape hatch, password-as-JWT-cookie revalidated against DB, edit-grant exclusions, and the share-view endpoint allowlist grammar. Adapt id-prefix dispatch and Prisma models. Omit template-permission constants (host-specific action sets).
