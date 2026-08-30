<!-- capsule-v2 -->
# minCount duplicates filter — why does a string-typed HAVING bind silently return zero groups on SQLite?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How is "show only groups with N+ rows" (duplicates finder) implemented, and what's the porting trap?

## HAVING COUNT >= minCount with a mandatory numeric coercion
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2/group-by.ts` list :124-130 + :526-531 (or outer :564-566); count :738-744 + :1069-1104.
**Signature:** `minCount?: number` query arg — arrives as TEXT from the query string.
**Data Shape:** `COUNT(pk || '*') >= ?` bind; placement follows the dialect fork.

### Decisive source
```ts
// :124-130 — the coercion IS the fix (comment duplicated verbatim in count):
// minCount comes from the query string as text; coerce to a number so the
// HAVING `COUNT(..) >= ?` bind isn't bound as text. SQLite compares
// INTEGER < TEXT by storage class, so `COUNT(..) >= '2'` is always false
// (0 groups); pg/mysql/oracle coerce the param, sqlite does not.
if (args.minCount !== undefined) {
  args.minCount = Number(args.minCount);
}

// :526-531 — default path: HAVING rides the inner grouped qb...
qb.havingRaw('COUNT(??) >= ?', [baseModel.model.primaryKey?.column_name || '*', args.minCount]);

// :564-566 / :1101-1104 — mssql/oracle: HAVING moves to the OUTER derived
// table (aggregates can't live on the ungrouped inner), and counts COUNT(*)
// of the regrouped rows instead:
grouped.havingRaw('COUNT(*) >= ?', [args.minCount]);
```

**Flow:** parse arg → coerce Number → dialect-appropriate HAVING (inner for pg/mysql/sqlite over the pk count; outer COUNT(*) for mssql/oracle).
**Invariant:** (1) Binding type matters as much as SQL text: the identical query with a `'2'` bind returns ZERO groups on SQLite by storage-class comparison rules. (2) The pk-or-`*` fallback keeps a stable count column even for pk-less tables. (3) On mssql/oracle minCount filters the regrouped table — semantics preserved but the counted expression differs (`COUNT(*)` post-regroup vs `COUNT(pk)` pre-group).
**Probe:** No unit tests upstream. Deterministic probe: rendered sqlite SQL shows the placeholder bound to number 2 (`>= 2`); passing '2' without coercion is the RED case (empty result set).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "minCount havingRaw", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.list Function group-by.ts 109-724 (:124-130, :526-531)
```

## Verdict
Adopt the coerce-before-bind rule and the dialect-placed HAVING. Adapt param binding to host driver. Caveat: no direct tests at pin; graph ranges verified live.
