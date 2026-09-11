<!-- capsule-v2 -->
# Bulk insert builder reuse — how does bulkInsert fan N records through ONE builder instance and one shared additional-statement list without cross-record contamination?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** What is the correct way to reuse `RecordInsertBuilder.buildInsertData` across a whole batch (statement ordering, per-record context, shared execution point)?

## Repository bulk path consuming the builder
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordRepository.ts:bulkInsert` (:1457–1688).
**Signature:** ONE `insertBuilder = new RecordInsertBuilder(db)` (:1458) reused for EVERY record; `insertDataResult = insertBuilder.buildInsertData({table, fieldValues, context})` per record (:1488).
**Data Shape:** per-record contexts differ (recordId, restoreValues fields, created/modified identities) while table + fieldValues map shape stay uniform; all records' `additionalStatements` are concatenated into `allAdditionalStatements` and executed ONCE via `await RecordInsertBuilder.executeStatements(db, allAdditionalStatements)` (:1688).

### Decisive source
```ts
// Use RecordInsertBuilder to build insert data for all records
const insertBuilder = new RecordInsertBuilder(db);        // ONE instance for the batch
...
const insertDataResult = insertBuilder.buildInsertData({...});   // per record i
...
await RecordInsertBuilder.executeStatements(db, allAdditionalStatements);  // once, in order
```
Main-row inserts run first (batched by the caller's insert strategy), THEN every junction/FK/attachment statement executes — two-phase within the same transaction. The builder instance itself is stateless between calls (all state lives in the returned result), which is what makes single-instance reuse safe.
**Flow:** build phase N× (pure) → main INSERTs → lock acquisition → statement-drain phase → computed updates.
**Invariant:** Additional statements must execute AFTER all main rows exist AND after linked-record locks are held — junction rows referencing foreign records need those locks; running them interleaved per-record invites deadlock under concurrency. Concatenating preserves per-record statement ORDER within each record's list.
**Probe:** `PostgresTableRecordRepository.insert.pglite.spec.ts` (:595/:618 ranges cover bulk flows with link columns); recording-level coverage via update.spec driver pattern — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "bulkInsert buildInsertData executeStatements allAdditionalStatements", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-stateless-builder-instance fan-out with a deferred shared side-effect drain after locks. Adapt batching thresholds to your driver. Omit teable's view-order/restore plumbing around it (covered by other capsules). Coverage caveat: pglite integration evidence; no runner here.
