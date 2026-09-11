<!-- capsule-v2 -->
# Blank-vs-null bucket unification — why must '' and NULL share one group bucket per dialect?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do you make empty-string and NULL group together identically across five engines?

## sqlNullIfBlank dialect table
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2/group-by.sqlNullIfBlank` (:53-93); applied at default branch :366-370, pg-string-formula :214-218, sub-group COALESCE :435-442, user sort key :605-609.
**Signature:** `sqlNullIfBlank({ baseModel, columnName, isStringType? }): Knex.Raw`.
**Data Shape:** Input may be a column-name string, QueryBuilder, or Raw — always embedded via knex `:column:` / `??` bindings.

### Decisive source
```sql
-- pg, NON-string-typed columns (:62-74): type-gated CASE because casting a
-- numeric/date to text just to compare '' would mask real values:
CASE WHEN (pg_typeof(:column:) IN ('text','varchar','char')::regtype ...)
      AND (:column:)::text = '' THEN NULL ELSE :column: END

-- mssql, non-string (:76-81): blanket cast, no type introspection available:
CASE WHEN CAST(:column: AS NVARCHAR(MAX)) = '' THEN NULL ELSE :column: END

-- oracle (:83-90): NO-OP BY DESIGN — '' IS NULL already, and NULLIF(col,'')
-- raises ORA-00932 on NUMBER columns because the '' literal is typed CHAR:
return baseModel.dbDriver.raw(`??`, [columnName]);

-- everything else (mysql/sqlite, :92): the textbook form:
NULLIF(??, '')
```

**Flow:** every scalar group key passes through this wrapper before entering SELECT + GROUP BY; `isStringType=true` (formula-string keys, already-text sub-group expressions) skips the type-gated variants and applies the blanket form.
**Invariant:** (1) Oracle's arm returning the raw column is NOT an omission — adding NULLIF there breaks numeric grouping with ORA-00932. (2) pg needs `pg_typeof` gating because its `'' = NULL` semantics don't exist; applying the mssql-style CAST to a date column would corrupt buckets. (3) This is why list() and count() agree on whether a row with `''` lands in the null bucket — both call the same helper.
**Probe:** No unit tests upstream. Deterministic probe: rendered pg SQL for a LongText key contains `pg_typeof(`; rendered Oracle SQL contains bare `??` (no NULLIF) for the same key.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "sqlNullIfBlank", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.sqlNullIfBlank Function group-by.ts 53-93
```

## Verdict
Adopt the four-way blank→NULL normalization table verbatim; adapt only binding style to your query builder. Caveat: no direct tests at pin; graph range verified live.
