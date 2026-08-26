<!-- capsule-v2 -->
# Parameter-limit-proof filtered fetch — how do you run `WHERE id IN (…)` when the value list exceeds SQLite's bound-parameter maximum?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you execute large IN-list queries without dropping the single-connection transactional context or leaking temp tables?

## Threshold-switched query planner: inline placeholders below the cap, TEMP tables above it
**Path/Symbol:** `app/server/lib/DocStorage.ts:fetchQuery` (:953–973), `_fetchQueryWithManyParameters` (:1882–1906), `_getSqlForQuery` (:1912–1921); constant `maxSQLiteVariables = 500` (:41, deliberately under SQLite's 999); sibling chunked read `fetchActionData` (:922–942).
**Signature:** `async fetchQuery(query: ExpandedQuery): Promise<Buffer>` — returns a marshalled column dictionary straight off `db.allMarshal`.
**Data Shape:** `ExpandedQuery { tableId, filters: {colId: value[]}, where?: {clause, params}, joins?, selects?, limit? }`.

### Decisive source
```ts
private async _fetchQueryWithManyParameters(query: ExpandedQuery): Promise<Buffer> {
  const db = this._getDB();
  // Temp-table backing lives OUTSIDE the document database and runs fast
  // (synchronous=OFF, journal_mode=PERSIST) per sqlite.org/tempfiles.html.
  return db.execTransaction(async () => {
    const tableNames: string[] = [];
    const whereParts: string[] = [];
    for (const colId of Object.keys(query.filters)) {
      const values = query.filters[colId];
      const tableName = `_grist_tmp_${tableNames.length}_${uuidv4().replace(/-/g, "_")}`;
      await db.exec(`CREATE TEMPORARY TABLE ${tableName}(data)`);
      tableNames.push(tableName);
      for (const valuesChunk of chunk(values, maxSQLiteVariables)) {
        const placeholders = valuesChunk.map(() => "(?)").join(",");
        await db.run(`INSERT INTO ${tableName}(data) VALUES ${placeholders}`, valuesChunk);
      }
      whereParts.push(`${q(query.tableId)}.${q(colId)} IN (SELECT data FROM ${tableName})`);
    }
    const sql = this._getSqlForQuery(query, whereParts);
    try { return await db.allMarshal(sql, ...params); }
    finally { await Promise.all(tableNames.map(t => db.exec(`DROP TABLE ${t}`))); }
  });
}
```

**Flow:** count total filter values → ≤500: build one statement with inline `IN (?,…)` placeholders → >500: inside ONE transaction, create one uniquely-named `_grist_tmp_<n>_<uuid>` TEMP table per filtered column, bulk-insert its values in 500-placeholder chunks, point the WHERE term at `IN (SELECT data FROM tmp)`, marshal the result, DROP all temps in a finally — still inside the transaction. Empty value lists are fine inline (`IN ()` is always-false in SQLite; would break on Postgres).
**Invariant:** The whole many-parameter plan is atomic with the reads because it rides the SAME connection's transaction — porters who shard across connections get wrong answers under concurrent writes; temp tables are named with a uuid so parallel queries can't collide; cleanup is in `finally` (an error mid-query cannot leak temp storage). The 500 cap is chosen BELOW the engine's real limit as safety margin.
**Probe:** `test/server/lib/DocStorageQuery.ts` `"should construct correct query for many-valued filters"` (:96, 1200-value filter asserts exact BEGIN/CREATE/INSERT×3/allMarshal/DROP×2/COMMIT sequence incl. 500-chunk boundaries via named-group regex matching) and `"should combine where clause and many-valued filters correctly"` (:124).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "_fetchQueryWithManyParameters maxSQLiteVariables ExpandedQuery", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whenever an embedded DB's bind-parameter cap meets user-sized filters: threshold-switch to per-column temp tables inside one same-connection transaction, uuid-suffixed names, finally-DROP. Adapt the cap to your engine's true limit minus margin (Postgres 32767, DuckDB none) — or to a VALUES-row constructor if temp DDL is unavailable. Omit the empty-IN note if your target isn't SQL-portable across engines.
