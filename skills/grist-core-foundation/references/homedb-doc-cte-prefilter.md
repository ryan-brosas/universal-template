<!-- capsule-v2 -->
# _doc CTE prefilter — how do you force a query planner to use indexes when WHERE mixes doc-id and alias matches with OR?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Why does the single-doc lookup embed a hand-written UNION ALL CTE, and what is the parameter-ordering trap?

## Raw-SQL CTE unions docs.id and alias matches so Postgres plans index scans; the :urlId param must be introduced LATER in the outer where
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `_doc` (:4325–4390), CTE string + QUIRK comment (:4333–4351), merged-org urlId branch (:4362–4365), `FilteredDocument` swap via `_docs(cte)` (:4310–4316) + `getDocResult` prototype restore (:5584–5592).
**Signature:** `_doc(scope: DocScope, options: DocQueryOptions = {})` → SelectQueryBuilder over `filtered_docs` CTE; accessStyle default "open".
**Data Shape:** CTE text:
```sql
SELECT docs.* FROM docs WHERE docs.id = :urlId
UNION ALL
SELECT docs.* FROM aliases JOIN docs ON docs.id = aliases.doc_id WHERE aliases.url_id = :urlId
```
Outer builder `.from(FilteredDocument, "docs")` — a tiny Document subclass whose only purpose is a distinct TypeORM alias for the CTE ("a hack around some TypeORM limitations").

### Decisive source
```ts
// OPTIMIZATION: we add a CTE to prefilter docs table for a union of matches on
// docs.id or on aliases. We observe the Postgres query planner having a hard time
// with the WHERE clause that does this filtering later with an OR.
// QUIRK: the :urlId parameter in the CTE relies on it being introduced later in the
// where clause. There's nowhere to add it in TypeORM's CTE interface.
let query = this._docs(options.manager, `
  SELECT docs.* FROM docs WHERE docs.id = :urlId
  UNION ALL
  SELECT docs.* FROM aliases JOIN docs ON docs.id = aliases.doc_id WHERE aliases.url_id = :urlId
`)
```
Merged-org compatibility branch inside the OR:
```ts
if (mergedOrg) {
  // Filter specifically for merged org documents.
  urlIdQuery = urlIdQuery.andWhere("orgs.owner_id is not null");
}
```

**Flow:** ambiguity is impossible at SQL level here because the same :urlId binds both union arms; duplicates surface as `docs.length > 1 → "ambiguous document request"` 400 in getDocImpl. `accessStyle`/limit machinery (`_applyLimit`) appends permission subselects onto this base.
**Invariant:** Parameter-binding ORDER is load-bearing: TypeORM numbers parameters by first appearance in the FINAL SQL, and the CTE is spliced before the where-clause bindings exist — reorder the builder calls and Postgres throws bind-parameter mismatch. The FilteredDocument→Document prototype reset in getDocResult MUTATES the query result ("CAUTION") so downstream instanceof checks keep working.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "UNION ALL" app/gen-server/lib/homedb/HomeDBManager.ts'` → :4345.
`bash -c 'grep -n "ambiguous document request" app/gen-server/lib/homedb/HomeDBManager.ts'` → :1098.
Direct tests: every doc-scoped suite exercises it transitively; `test/gen-server/lib/urlIds.ts` :113 pins alias-vs-doc disambiguation.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"_doc filtered_docs UNION ALL aliases FilteredDocument addCommonTableExpression","limit":8,"detail":"ids"}'`

**Verdict:** ADAPT — planner-workaround CTEs are ORM-specific but the pattern (prefilter-union + documented binding quirk) transfers to any heavy OR-mapped lookup.
