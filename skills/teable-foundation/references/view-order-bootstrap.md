<!-- capsule-v2 -->
# View order column bootstrap — how does inserting into a view get an order column that may not physically exist yet, and how are append orders computed?

**Source:** teable AGPL `develop@06a4461e`. **Question:** Per-view row-order columns (`__row_<viewId>`) are added lazily — what is the create-and-backfill recipe and the max+index append formula?

## information_schema check → ADD COLUMN double precision → backfill from __auto_number → hash-suffixed index; append = max + recordIndex + 1
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `getViewOrderInfo` (:328–383), `buildViewOrderValues(viewOrderInfo, recordIndex)` (:389–400), `checkOrderColumnExists` (:420–435), `ensureViewOrderColumnsExist` (:518–549), snapshot variant `buildSnapshotViewOrderValues` (:402–418); consumers in `insert` :1158–1245 and `insertMany` :1425–1567. Companion capsule: `record-order-fractional` (interactive reordering).
**Signature:** `ensureViewOrderColumnsExist(db, tableName, viewIds): Promise<void>`; `getViewOrderInfo(db, tableName, views): Promise<Map<columnName, number>>`.

### Decisive source
```sql
ALTER TABLE ${tableName} ADD COLUMN "__row_${viewId}" double precision;
UPDATE ${tableName} SET "__row_${viewId}" = __auto_number WHERE "__row_${viewId}" IS NULL;
CREATE INDEX IF NOT EXISTS "${hash(idx_${plainTableName}_${orderColumnName})}" ON t ("__row_${viewId}");
-- per insert batch:  SELECT COALESCE(MAX(col),0) AS col FROM t   (one column per existing view)
```
```ts
values[columnName] = maxOrder + recordIndex + 1;      // append order for record #recordIndex
// restore path: buildSnapshotViewOrderValues writes literal snapshot orders keyed `__row_${viewId}`
```

**Flow:** before writing view orders, verify each target column actually exists (information_schema) → lazily CREATE it as double precision (fractional ordering ready), backfilling existing rows from `__auto_number` so new rows sort after all old rows → add a named-with-hash index → compute append values as currentMax + recordIndex + 1 across the batch.
**Invariant:** FIVE facts porters miss: (1) getViewOrderInfo filters candidate columns to those that EXIST first, then runs ONE grouped `MAX()` query — never one query per view. (2) The whole probe is try/catch fail-open returning an empty map (order loss beats write failure). (3) Backfill seeds from `__auto_number`, NOT 0/row_number — preserving original relative order matters more than density. (4) Index names go through `toPostgresIdentifierWithHash` because raw `idx_<table>_<col>` exceeds PG's 63-char identifier cap on long table+view ids. (5) Restore flows pass explicit snapshot orders and must ensure columns exist BEFORE building values (`insert` :1210–1218) — else the INSERT references a missing column.
**Probe:** deterministic grep pins: :531–547 (ALTER/UPDATE/CREATE INDEX block), :366–370 (grouped MAX). Behavior pinned by 'sets default row order when inserting into schema-qualified table' (insert.pglite.spec.ts :322).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ensureViewOrderColumnsExist getViewOrderInfo buildViewOrderValues", limit: 5 });
```
## Verdict
Adopt for any lazy per-projection sort-column scheme: existence-check → typed ADD COLUMN → meaningful backfill → hashed index name → grouped MAX append math.
