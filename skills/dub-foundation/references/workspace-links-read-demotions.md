<!-- capsule-v2 -->
# Workspace links read demotions — how does a list endpoint degrade sorting and search as the workspace grows past six and seven figures of links?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** Where do expensive list features (user-chosen sort, fuzzy search) get silently demoted, and when must the COUNT route re-materialize folder scoping that validation skipped?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/api/links/route.ts:GET` (:23-52) · `apps/web/app/api/links/count/route.ts:GET` (:9-51) · `apps/web/lib/api/links/validate-links-query-filters.ts:validateLinksQueryFilters` (:14-68).
**Signature:** `GET = withWorkspace(...)`; `validateLinksQueryFilters({...filters, workspace, userId}) => { folderIds?: string[] }`.
**Data Shape:** Constants in `lib/constants/misc.ts`: `SORTABLE_LINKS_LIMIT = 10_000` (:3), `MEGA_WORKSPACE_LINKS_LIMIT = 1_000_000` (:4). Demotion reads `workspace.totalLinks` (denormalized counter), NOT a live count.

### Decisive source
```ts
// GET /api/links — size-driven silent demotions on the ROUTE side:
sortBy:   workspace.totalLinks > SORTABLE_LINKS_LIMIT      ? "createdAt" : filters.sortBy,  // :37-40
searchMode: workspace.totalLinks > MEGA_WORKSPACE_LINKS_LIMIT ? "exact"   : "fuzzy",       // :41-42

// validateLinksQueryFilters materializes RBAC folder scope ONLY under cross-cutting filters:
if (!folderId && (search || domain || tagId || tagIds || tagNames || tenantId || linkIds)) {
  folderIds = await getFolderIdsToFilter({ workspace, userId });                             // :48-56
}
if (Array.isArray(folderIds)) { folderIds = folderIds.filter((id) => id !== "");
  if (folderIds.length === 0) folderIds = undefined; }                                       // :58-63 sentinel strip, []→undefined

// GET /api/links/count — SECOND-CHANCE materialization: groupBy bypassed validation above
if (filters.groupBy && filters.groupBy !== "folderId" && !filters.folderId && !folderIds) {
  folderIds = await getFolderIdsToFilter({ workspace, userId });                              // :19-36 (+ same strip/undefined)
}
```

**Flow:** parse → validate (domain existence oracle, per-folder access check, conditional whole-workspace folder-scope materialization) → [list] apply demotions from the denormalized totalLinks counter → query / [count] re-check whether groupBy slipped past materialization and repair before counting.
**Invariant:** Folder RBAC scope is materialized lazily but NEVER skipped for queries that cross folder boundaries — any filter that can match rows across folders (search/domain/tags/tenant/linkIds) triggers it, and the count route closes the one loophole (groupBy over a non-folder dimension). Demotions are SILENT and COUNTER-DRIVEN (>10k loses custom sort to createdAt; >1M loses fuzzy to exact), so a stale counter changes behavior — that is accepted drift, not a bug. The "" sentinel means "unsorted links" and consumers strip it last, collapsing [] to undefined (no scope ⇒ no constraint).
**Probe:** Direct test `tests/links/count-links.test.ts` :8-33 — integration harness (PG+Redis+QStash cloud-gated, offline here) pins only 200 + count ≥ 1; the DEMOTIONS themselves are UNTESTED (list-links suite pins sortBy passthrough at :57 only). Deterministic probes: ternaries :37-40/:41-42; second-chance guard :19-24; empty-collapse :30-35.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", qn_pattern: ".*api\\.links.*route", name_pattern: "^(GET|POST)$", limit: 10 }); // links GET :23-52, count GET :9-51 among 14 route symbols
```

## Verdict
Adopt counter-threshold feature demotion as a scalability contract (and accept its counter-drift), plus the rule "validation materializes scope only for cross-cutting filters — every specialized consumer (groupBy!) must audit whether it escaped that path". Adapt thresholds to your storage's real cost curve. Omit nothing silently: if you drop the sentinel protocol, replace it with an explicit unfiled-scope representation.
