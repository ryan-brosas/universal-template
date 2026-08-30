<!-- capsule-v2 -->
# Insert batch bind ceiling — how do you split multi-row inserts so wide tables cannot overflow PostgreSQL's bind-parameter limit?

**Source:** teable AGPL `develop@06a4461e`. **Question:** Multi-row INSERT sends columns×rows bind parameters — what is the safe dynamic batch-size formula?

## width-aware clamp between 1 and 500
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `INSERT_BATCH_SIZE = 500` (:1354), `POSTGRES_BIND_PARAMETER_SAFE_LIMIT = 30_000` (:1357), `resolveInsertBatchSize(values)` (:1359–1378), consumption loop in `insertMany` (:1633–1677). Tests: `PostgresTableRecordRepository.insert.pglite.spec.ts` 'splits wide insertMany batches under the PostgreSQL bind parameter limit' (:525).
**Signature:** `private static resolveInsertBatchSize(values: ReadonlyArray<Record<string, unknown>>): number`.

### Decisive source
```ts
const columnNames = new Set<string>();          // UNION of keys across ALL rows
for (const value of values)
  for (const columnName of Object.keys(value)) columnNames.add(columnName);
if (columnNames.size === 0) return INSERT_BATCH_SIZE;              // 500 default
const bindLimitedBatchSize = Math.floor(
  POSTGRES_BIND_PARAMETER_SAFE_LIMIT / columnNames.size);          // 30k / width
return Math.max(1, Math.min(INSERT_BATCH_SIZE, bindLimitedBatchSize));
// loop: for (let i = 0; i < allValues.length; i += batchSize) { ...values(batch)... }
```

**Flow:** collect the union of column names over every row in the batch (sparse rows widen it) → divide the 30,000-parameter safety budget by that width → clamp between 1 and the 500-row default → slice the values array into batches executed sequentially.
**Invariant:** The ceiling is Postgres' hard 65,535-bind protocol limit halved "to leave room for driver/dialect quirks on wide tables" — NOT the theoretical max. Width comes from the KEY UNION across all rows, not per-row width, because kysely pads missing keys. Clamping at max(1, …) means an absurdly wide table degrades to row-at-a-time inserts instead of failing. RETURNING adds `record_id` + changed-field columns to each row's parameters, which the 50% headroom absorbs without a second term.
**Probe:** insert.pglite.spec.ts :525 pins the split behavior against the parameter limit.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveInsertBatchSize POSTGRES_BIND_PARAMETER_SAFE_LIMIT insertMany", limit: 5 });
```
## Verdict
Adopt the formula verbatim (union-width ÷ budget clamped to [1, default]) wherever generated multi-row INSERTs meet a parameter cap; adapt the constants to your driver's real ceiling.
