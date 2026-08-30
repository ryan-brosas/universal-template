<!-- capsule-v2 -->
# Bind-parameter insert batching — how do you batch wide-row INSERTs under PostgreSQL's 65,535 parameter ceiling?

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What batch size keeps a multi-row INSERT from overflowing the wire protocol, and what must be deduped across batches?

## Dynamic bind-limited batching
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordRepository.ts` — `INSERT_BATCH_SIZE = 500`, `POSTGRES_BIND_PARAMETER_SAFE_LIMIT = 30_000`, `resolveInsertBatchSize` (:1354–1378); execution loop :1633–1677.
**Signature:** `static resolveInsertBatchSize(values: ReadonlyArray<Record<string, unknown>>): number`.
**Data Shape:** input = assembled value rows (union of all column keys matters, not per-row shape); output = rows per statement; changed-field RETURNING is unioned across ALL batches.

### Decisive source
```ts
private static readonly INSERT_BATCH_SIZE = 500;
// Keep well below PostgreSQL's 65,535 bind-parameter ceiling to avoid
// protocol overflow and leave room for driver/dialect quirks on wide tables.
private static readonly POSTGRES_BIND_PARAMETER_SAFE_LIMIT = 30_000;

const bindLimitedBatchSize = Math.floor(SAFE_LIMIT / columnNames.size);
return Math.max(1, Math.min(INSERT_BATCH_SIZE, bindLimitedBatchSize));
```
```ts
for (let i = 0; i < allValues.length; i += batchSize) {
  const batch = allValues.slice(i, i + batchSize);
  // .returning([sql.ref(RECORD_ID_COLUMN).as('record_id'), ...changedFieldSelects])
}
```

**Flow:** count distinct column names over ALL rows → floor the safe limit by width → clamp to [1,500] → slice into same-transaction statements → when changedFieldColumns exist, every batch carries `.returning(record_id + changed selects)` and results merge into one `changedFieldsByRecord` keyed by returned record_id. Empty-column edge returns the default 500.
**Invariant:** the limit counts COLUMNS × ROWS, not rows alone — a 200-column table drops to 150 rows/statement. The returning set must be accumulated ACROSS batches (each batch only returns its own rows). One snapshot-capture session spans all batches; abort on any failure.
**Probe:** `record/repository/PostgresTableRecordRepository.insert.pglite.spec.ts:525` 'splits wide insertMany batches under the PostgreSQL bind parameter limit'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveInsertBatchSize POSTGRES_BIND_PARAMETER_SAFE_LIMIT", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the formula (`floor(30000 / distinctColumnCount)`, clamped) and cross-batch RETURNING accumulation. Adapt the constants to your driver's true ceiling. Omit teable's RecordInsertBuilder plumbing if you only need the batching rule.
