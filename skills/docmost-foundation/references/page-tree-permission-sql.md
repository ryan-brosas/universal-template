<!-- capsule-v2 -->
# Page-tree permission SQL — one recursive CTE deciding traversal access AND nearest-writer edit rights

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How can a single query answer both "can the user see this page through restricted ancestors" and "can they write, per the nearest restricted ancestor"?

## canUserEditPage recursive-CTE aggregate
**Path/Symbol:** `apps/server/src/database/repos/page/page-permission.repo.ts`:`canUserEditPage` (lines 383–435; file carries a tree-sitter partial-parse flag around line 399 — cite from source, not graph spans).
**Signature:** `canUserEditPage(userId: string, pageId: string): Promise<{ hasAnyRestriction: boolean; canAccess: boolean; canEdit: boolean }>`, memoized via `withCache(PAGE_CAN_EDIT(userId, pageId), PERMISSION_CACHE_TTL_MS)`.
**Data Shape:** `page_permissions` rows hang off `page_access` (per restricted page) and grant to a user OR any of the user's groups.

### Decisive source
```sql
WITH RECURSIVE ancestors AS (
  SELECT id AS ancestor_id, parent_page_id, 0 AS depth FROM pages WHERE id = ${pageId}::uuid
  UNION ALL
  SELECT p.id, p.parent_page_id, a.depth + 1 FROM pages p JOIN ancestors a ON a.parent_page_id = p.id
)
SELECT
  bool_and(pp.id IS NOT NULL) AS "canAccess",
  (array_agg(pp.role ORDER BY a.depth ASC, pp.role DESC NULLS LAST))[1] = 'writer' AS "canEdit"
FROM ancestors a
JOIN page_access pa ON pa.page_id = a.ancestor_id
LEFT JOIN page_permissions pp ON pp.page_access_id = pa.id
  AND (pp.user_id = ${userId}::uuid
       OR pp.group_id IN (SELECT gu.group_id FROM group_users gu WHERE gu.user_id = ${userId}::uuid))
```
Zero restricted ancestors ⇒ single row of NULLs ⇒ `{hasAnyRestriction:false, canAccess:true, canEdit:true}`. Otherwise `canEdit = canAccess && nearest-role === 'writer'`.

**Flow:** walk parent chain from the page up → join each restricted ancestor's permission rows → `bool_and` fails closed on ANY restricted ancestor lacking permission → nearest-restricted-writer decides edit.
**Invariant:** permissions inherit DOWNWARD from ancestors and fail closed (`bool_and` over an empty-permission ancestor = false); the nearest restricted ancestor wins for editing regardless of more distant grants; NULL roles sort last so no-permission never masquerades as writer.
**Probe:** `grep -cF 'bool_and(pp.id IS NOT NULL)' apps/server/src/database/repos/page/page-permission.repo.ts` (=2) and `grep -cF 'ORDER BY a.depth ASC, pp.role DESC NULLS LAST' apps/server/src/database/repos/page/page-permission.repo.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "canUserEditPage ancestors recursive bool_and page_access", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-in-one CTE shape (traversal AND + ordered array_agg pick) for any hierarchical ACL; adapt role names/table names; omit the kysely/postgres specifics if targeting another DB but keep NULLS LAST semantics. Direct tests: none found for this repo method upstream; behavior pinned by source read + probes against live SQL text.
