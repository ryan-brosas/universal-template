<!-- capsule-v2 -->
# Empty-table seed ANALYZE — why does the FIRST bulk insert into a table trigger ANALYZE, and why only then?

## tableHasExistingRows probe BEFORE insert → if table was empty, run ANALYZE once after seeding
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `tableHasExistingRows(db, tableName)` (:832–838, `SELECT EXISTS (SELECT 1 FROM t LIMIT 1)`), `analyzeSeededTable(db, tableName, tableWasEmpty)` (:840–851, early-return `if (!tableWasEmpty)`); call sites :1403 (`tableWasEmpty = !(await …)` before any DML) and :1678 (after batch inserts). Companion capsule: `computed-backfill` (pg_class estimate consumer).
**Signature:** `(db, tableName, tableWasEmpty: boolean): Promise<void>`.

### Decisive source
```ts
const result = await sql<{has_rows: boolean}>`
  SELECT EXISTS (SELECT 1 FROM ${tableRef} LIMIT 1) AS has_rows`.execute(db);
...
async function analyzeSeededTable(db, tableName, tableWasEmpty) {
  if (!tableWasEmpty) return;
  await sql`ANALYZE ${tableRef}`.execute(db);
}
```

**Flow:** before inserting, record whether the table had ANY row (EXISTS+LIMIT 1 — index-cheap even on huge tables) → after the seed batches commit their inserts (same tx), run ANALYZE exactly when the table WAS empty.
**Invariant:** Postgres autovacuum's statistics lag means a freshly-seeded table otherwise presents near-zero-row estimates to the planner — every subsequent query plan (joins onto the data table, computed UPDATE … FROM SELECT plans) would be catastrophically wrong until autovacuum eventually fires. Seeding is the one moment the app KNOWS statistics are stale-and-cheap-to-fix, so it pays synchronously. The was-empty gate keeps the O(table-scan-ish) ANALYZE off hot incremental-insert paths where stats are already representative. EXISTS(LIMIT 1) beats count(*) by orders of magnitude on populated tables — porters "simplifying" to count reintroduce a full scan per insertMany.
**Probe:** insert.pglite.spec.ts 'analyzes the first batch inserted into an empty table' (:479).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "analyzeSeededTable tableWasEmpty ANALYZE", limit: 5 });
```
## Verdict
Adopt wherever app code bulk-seeds SQL tables the planner must immediately serve: one EXISTS probe, one conditional ANALYZE, inside the same transaction.
