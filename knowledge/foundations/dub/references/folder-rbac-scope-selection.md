<!-- capsule-v2 -->
# Folder RBAC scope selection — per-user folder visibility as an analytics filter

**Source:** dub AGPL-3.0-or-later main@29df217a29631ced4041882a28d2327cc4546f27; Codebase Memory dub. **Question:** When a listing/analytics query has no explicit folderId, how do you restrict results to folders the requesting user may see — cheaply, and only when folders exist?

## Tri-branch folder-id resolver with an unsorted sentinel
**Path/Symbol:** apps/web/lib/analytics/get-folder-ids-to-filter.ts:getFolderIdsToFilter (:6-44); consumer apps/web/lib/api/links/validate-links-query-filters.ts (:48-63).
**Signature:** getFolderIdsToFilter({workspace: Pick<Project,"id"|"plan"|"foldersUsage">, userId}) -> Promise<string[] | undefined>.
**Data Shape:** returns undefined when the workspace has zero folder usage; otherwise array of visible folder ids PLUS the "" unsorted-folder sentinel appended last.

### Decisive source
```ts
if (workspace.foldersUsage === 0) {
  return undefined;                       // no folders exist: skip ALL folder work
}
const { canManageFolderPermissions } = getPlanCapabilities(workspace.plan);
if (canManageFolderPermissions) {         // RBAC-capable plan: USER-scoped visibility
  const folders = await getFolders({ workspaceId, userId, type: "default", pageSize: 1000 }); // TODO >1000
} else {                                  // plain plan: workspace-wide is already the permission
  const folders = await prisma.folder.findMany({ where: { projectId: workspace.id } });
}
folderIds = folders.map((folder) => folder.id).concat("");   // BOTH branches append the sentinel
```
(get-folder-ids-to-filter.ts :13-43 condensed)

**Flow:** foldersUsage===0 short-circuits before any query (denormalized counter read is free) -> plan capability picks user-scoped getFolders(pageSize 1000) vs whole-workspace findMany -> both append "" so downstream IN(...) clauses also match unfiled links (the filter-side twin of workspace-list-composition's folderId:null union) -> consumers post-process: validateLinksQueryFilters strips the sentinel and maps empty arrays back to undefined (:58-63), and only pays this cost when cross-cutting filters (search/domain/tags/tenant/linkIds) are present without an explicit folderId (:48-51). Second caller: app/api/links/count route.
**Invariant:** the sentinel must survive until the SQL layer — stripping it early silently hides unfiled links from filtered listings. foldersUsage===0 returning undefined (NOT []) is load-bearing: [] would mean match-nothing while undefined means no-constraint.
**Probe:** executed at pin: grep -n "foldersUsage === 0" -> :13; grep -n concat sentinel -> :31,:40. Caller anchors: validate-links-query-filters.ts :52 (call site) and :59-62 (sentinel strip + empty-to-undefined). Direct test: none for this helper in tests/analytics (coverage caveat — behavior pinned by source + caller reads).

## Get live surrounding code
**Retrieve:**
```ts
// graph observed: getFolderIdsToFilter Function get-folder-ids-to-filter.ts 6-44 (in=2 out=12)
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "getFolderIdsToFilter", direction: "inbound", depth: 1 });
// callers_total=2: app.api.links.count route; lib.api.links.validate-links-query-filters.validateLinksQueryFilters
```

## Verdict
Adopt the counter short-circuit, plan-split resolver, sentinel append, and the undefined-vs-empty distinction. Adapt the capability predicate and page size. Omit RBAC branch only if your product has no per-user folder permissions (then the findMany branch IS the whole function).
