<!-- capsule-v2 -->
# Workspace list composition with folder visibility scoping — how does GET /links turn user filters into one safe Prisma where-clause?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** How do search modes, tag/tagIds/tagNames precedence, folder permissions, and archived filtering compose into one query?

## getLinksForWorkspace + validateLinksQueryFilters
**Path/Symbol:** `apps/web/lib/api/links/get-links-for-workspace.ts:getLinksForWorkspace` (18-190); pre-filter `apps/web/lib/api/links/validate-links-query-filters.ts:validateLinksQueryFilters` (14-68); route wrapper `apps/web/app/api/links/route.ts:GET`.
**Signature:** `getLinksForWorkspace(filters: GetLinksQuerySchemaExtended & { workspaceId, folderIds? }): Promise<TransformedLink[]>`; `validateLinksQueryFilters({...}): Promise<{ folderIds?: string[] }>`.
**Data Shape:** where clause = flat tenant columns + one `AND[]` array carrying the OR-heavy branches (folders, search) so they intersect rather than union.

### Decisive source
```ts
// validate side: derive VISIBLE folder ids when no explicit folder filter is given
if (!folderId && (search || domain || tagId || tagIds || tagNames || tenantId || linkIds)) {
  folderIds = await getFolderIdsToFilter({ workspace, userId });   // permitted folders only
}
// empty after cleanup means NO folder restriction, never zero results
folderIds = folderIds?.filter((id) => id !== "");
if (folderIds.length === 0) folderIds = undefined;

where: {
  ...(linkIds && { id: { in: linkIds } }),
  projectId: workspaceId,                       // tenancy always flat, never inside AND
  AND: [
    ...(folderIds ? [{ OR: [{ folderId: { in: folderIds } }, { folderId: null }] }]   // unfiled links stay visible
                   : [{ folderId: folderId || null }]),
    ...(search ? [{
      ...(searchMode === "fuzzy" && { OR: [{ shortLink: { contains: search } }, { url: { contains: search } }] }),
      ...(searchMode === "exact" && {
        [search.startsWith("https://") ? "shortLink" : "key"]: { startsWith: search },
      }),
    }] : []),
  ],
  archived: showArchived ? undefined : false,    // default hides archived WITHOUT excluding nulls elsewhere
  ...(withTags && { tags: { some: {} } }),
  ...(combinedTagIds?.length > 0 ? { tags: { some: { tagId: { in: combinedTagIds } } } }
    : tagNames ? { tags: { some: { tag: { name: { in: tagNames } } } } } : {}),
}
// exact-mode URL searches encode case-sensitive keys INSIDE the search string first:
const encodedKey = encodeKeyIfCaseSensitive({ domain, key });
search = search.replace(key, encodedKey);
```

**Flow:** route validates domain ownership (`getDomainOrThrow`) and folder read-access first, computes visible `folderIds` ONLY when narrowing filters are present (pure lists skip the folders query) → list fn validates the cursor (see pagination capsule), folds tagId+tagIds into combinedTagIds (ids win over names), rewrites exact-mode URLs to encoded keys, then composes the single findMany with include-tags/user/webhooks/dashboard flags and the shared pagination fragment.
**Invariant:** Tenancy (`projectId`) is a TOP-LEVEL equality, never buried in OR branches — an OR can only widen filters, never escape the workspace. Folder visibility has TWO regimes: explicit folderId = permission-checked direct filter; no filter but narrowing criteria = OR over permitted folder ids UNION `folderId: null`, because unfiled links belong to everyone in the workspace — dropping the null branch would hide them from filtered searches. Tag filters have strict precedence (tagId/tagIds > tagNames). Exact search field choice pivots on whether the input looks like a full URL. `archived: undefined` vs `false` is how Prisma expresses "don't filter" vs "not archived".
**Probe:** direct integration tests `tests/links/list-links.test.ts:14 "GET /links"` (baseline assertions incl. tags/user includes) plus the six pagination pins (:77-:215); count-side twin `tests/links/count-links.test.ts`. Fuzzy-vs-exact branch coverage is partial upstream — caveat noted.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getLinksForWorkspace validateLinksQueryFilters folderIds", limit: 5 });
// → get-links-for-workspace.getLinksForWorkspace @ 18-190 · validate-links-query-filters.validateLinksQueryFilters @ 14-68
```

## Verdict
Adopt flat tenancy + AND-intersected OR branches, the unfiled-rows-stay-visible folder union, computed-visible-folder-sets only when needed, tag-filter precedence, and exact/fuzzy search-mode split. Adapt folder semantics and search fields. Omit the case-sensitive search rewrite without such domains.
