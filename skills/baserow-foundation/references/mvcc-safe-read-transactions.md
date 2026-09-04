<!-- capsule-v2 -->
# MVCC-safe read transactions — how do you read user tables while other requests ALTER them?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** Why do exports/snapshots need REPEATABLE READ plus a FOR KEY SHARE first statement instead of a plain transaction?

## read_repeatable_single_database_atomic_transaction lock-then-snapshot
**Path/Symbol:** `backend/src/baserow/contrib/database/db/atomic.py` — `read_repeatable_single_database_atomic_transaction` (7–52), `read_committed_single_table_transaction` (55–96), `read_repeatable_read_single_table_transaction` (99–144); consumers: `application_types.py:103–104` (export_safe_transaction_context), `core/registries.py`.
**Signature:** each returns an Atomic CM built via `transaction_atomic(isolation_level=..., first_sql_to_run_in_transaction_with_args=(sql.SQL, args))`; the database-wide variant wraps itself in `cachalot_disabled()`.
**Data Shape:** First statement is a metadata-row lock: `SELECT * FROM database_field INNER JOIN database_table ON database_field.table_id = database_table.id WHERE database_table.database_id = {id} FOR KEY SHARE OF database_field, database_table`.

### Decisive source
```python
# It is critical we obtain the locks in the first SELECT statement run in the
# REPEATABLE READ transaction so we are given a snapshot that is guaranteed to never
# have harmful MVCC operations run on it.
first_statement = sql.SQL("""
SELECT * FROM database_field
INNER JOIN database_table ON database_field.table_id = database_table.id
WHERE database_table.database_id = {0} FOR KEY SHARE OF database_field, database_table
""")
...
with cachalot_disabled():
    return transaction_atomic(
        isolation_level=IsolationLevel.REPEATABLE_READ,
        first_sql_to_run_in_transaction_with_args=(first_statement, first_statement_args),
    )
```

**Flow:** enter atomic at chosen isolation → VERY FIRST statement locks every field+table metadata row FOR KEY SHARE (non-blocking vs writers of OTHER rows, but blocks ALTER/DROP which need stronger conflicts) → snapshot fixed at that statement for RR variants → long export/import reads proceed; concurrent schema edits queue behind the lock.
**Invariant:** The lock MUST be the transaction's first statement — in REPEATABLE READ the snapshot is taken at the first statement, and Postgres docs' MVCC caveats say DDL by concurrent sessions can break an otherwise-consistent snapshot; locking metadata rows first makes conflicting ALTERs wait. FOR KEY SHARE (not FOR UPDATE) is deliberate: it minimizes contention with ordinary row writes. The three flavors trade guarantees: db-wide+RR (exports), table+RC (cheap consistent-enough reads), table+RR.
**Probe:** `grep -c "FOR KEY SHARE" backend/src/baserow/contrib/database/db/atomic.py` → 5 (3 statements + 2 doc mentions); `grep -cn "cachalot_disabled()" backend/src/baserow/contrib/database/db/atomic.py` → 2. Coverage caveat noted in-source; no dedicated upstream test file for this module (behavior pinned by export suites under `backend/tests/baserow/contrib/database/`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "read repeatable single database atomic transaction key share", limit: 6 });
```

## Verdict
Adopt lock-metadata-first snapshot reads for any engine where user data lives beside mutable runtime schemas; adapt lock strength to your write mix; omit cachalot interplay if you have no ORM result cache. Runner blocked honestly — SQL verified byte-exact against pin.
