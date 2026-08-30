<!-- capsule-v2 -->
|# Base-user roster query — inner-workspace/left-base join asymmetry feeding export payloads and id→email maps

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What does the underlying roster query guarantee — the join shape, cache behavior, and keep-deleted-users rule a porter would silently lose?

## Path/Symbol
`packages/nocodb/src/models/BaseUser.ts:getUsersList` (229–363); payload consumer `modules/jobs/jobs/export-import/export.service.ts:serializeUsers` (856–873).

**Signature:** `getUsersList(context, {base_id, mode='full', strict_in_record=false, include_ws_deleted=true, include_internal_user=false, user_ids?})`.

**Data Shape:** users ⋈ project_users ⋈ workspace_user with aliased roles — `main_roles` (global), `roles` (base-level → exported as base_role), `workspace_user.roles as workspace_roles` (exported verbatim). Export keeps email/display_name/both role fields; import side (`importUsers`, import.service.ts 94–105) is a deliberate notImplemented stub.

### Decisive source
```ts
// workspace membership is INNER (must be in this workspace);
// base mapping is LEFT (a workspace member may not be mapped to this base)
.innerJoin(MetaTable.WORKSPACE_USER, ... .andOn(fk_workspace_id = ?, [context.workspace_id]))
[joinClause](MetaTable.PROJECT_USERS,   ... .andOn(base_id = ?, [base_id])) // left|inner by strict_in_record

// No is_deleted filter here — soft-deleted users are excluded at the
// workspace level (WorkspaceUser.softDeleteByUser removes memberships).
// This list intentionally includes them so user fields (created_by,
// last_modified_by) can still render historical "Anonymous" entries.
```

**Flow:** cache check (`getList(BASE_USER,[base_id])`) → on miss run the three-table query → stamp base_id + parse meta per row → setList write-back keyed ['base_id','id'] unless strict_in_record → mode='viewer' strips full-version cols (invite_token). serializeUsers maps rows to the identity-free payload.

**Invariant:** (1) Join ASYMMETRY: inner for workspace membership, left for base mapping — flipping either changes who appears. (2) NO is_deleted filter by design: historical created_by references must render. (3) Cached rows are SHARED via scope list — callers must not mutate returned rows in place (cache poisoning). (4) Everything else in export/import remaps ids because ids don't survive instances; USERS travel by email (see getUserEmails at export.service.ts:229-239: "email is the only handle that survives the hop").

**Probe:** no unit test upstream. Source-grounded probe: BaseUser.ts:274-302 verbatim, :306-323 write-back, :351-360 viewer strip; export.service.ts:856-873 + :229-239; pairing capsules export-users-roster.md (payload view), baseuser-service-actors.md, cache-setlist-projection.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "BaseUser getUsersList WORKSPACE_USER PROJECT_USERS joinClause", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the join asymmetry, keep-deleted-for-references rule, and shared-cache mutation discipline; adapt role column names; omit viewer-mode stripping unless porting token surfaces. Coverage caveat: no in-repo unit tests; source-grounded.
