<!-- capsule-v2 -->
# Auto-number sequence resync — why must setval run after restoring explicit autoNumber values, and what is the exact GREATEST form?

**Source:** teable AGPL `develop@06a4461e`. **Question:** Restored rows carry historical auto-number values — how does the identity sequence avoid future collisions?

## pg_get_serial_sequence → setval(GREATEST(max(col),0), true), gated on explicit restore only
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `syncAutoNumberSequence(db, tableName)` (:811–830); gates in `insert` :1288–1290 (`if (restoreValues?.autoNumber !== undefined)`) and `insertMany` :1679–1681 via `hasExplicitAutoNumberRestore` flag collected at :1531–1533. Tests: insert.pglite.spec.ts suite (restore paths) :286ff.
**Signature:** `syncAutoNumberSequence(db, tableName): Promise<void>`.

### Decisive source
```ts
const sequenceResult = await sql<{seq_name: string | null}>`
  SELECT pg_get_serial_sequence(${qualifiedTableName}, '__auto_number') AS seq_name`.execute(db);
if (!sequenceName) return;                       // no sequence ⇒ nothing to do
await sql`SELECT setval(${sequenceName},
  GREATEST(COALESCE((SELECT MAX(__auto_number) FROM ${tableRef}), 0), 1), true)`.execute(db);
```

**Flow:** resolve the sequence bound to `__auto_number` (null-safe exit when the column isn't serial-typed) → set it to max(existing values, 1) with `is_called=true` so the NEXT nextval returns max+1.
**Invariant:** Runs ONLY when a restore supplied explicit autoNumbers (`hasExplicitAutoNumberRestore` in batch mode — a single flag over all records, not per-row), because setval is a catalog write that takes heavyweight locks and would be pure overhead on normal inserts. `GREATEST(…, 1)` guards the empty-table case (MAX=NULL→COALESCE 0→setval(…,1,true) yields next=2 on an empty table, harmless); `is_called=true` means "this value IS used" — porters who pass false make the next insert REUSE max, colliding with the just-restored row. Restores also skip snapshot capture by default (`skipSnapshotCapture` option :309–313) because capture infra may not exist yet in ephemeral databases.
**Probe:** deterministic: grep :813/:823-829; gate :1288/:1679.
**Coverage caveat:** no dedicated unit test isolates syncAutoNumberSequence; covered indirectly by insert-spec restore suites — noted per quality bar.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "syncAutoNumberSequence pg_get_serial_sequence setval", limit: 5 });
```
## Verdict
Adopt verbatim whenever rows can be inserted with explicit identity values: gate on the restore case, resolve the sequence dynamically, setval(GREATEST(max,1), true).
