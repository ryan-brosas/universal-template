<!-- capsule-v2 -->
# MVCC conflict detection — when are write-write conflicts actually checked, and what exactly counts as one?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** Where in the lifecycle do I validate for first-committer-wins, and which structures act as write locks?

## EAGER detection at WRITE time + deferred validation sweep at commit
**Path/Symbol:** `core/mvcc/database/mod.rs:check_rowid_for_conflicts` / `check_index_for_conflicts` (:1781/:1805), insert-time note (:5011-5013), commit-path sweep from the Commit state (:2987-3000); eager path: plain UPDATE/DELETE detect conflicts AT WRITE TIME via the delete-step probe (`is_write_write_conflict`, delete :5252-5256 "write-write conflict on delete").
**Signature:** commit-path validation driven from the Commit state; chains scanned **in reverse** so conflicts exit early.
**HEAD CORRECTION (source wins over legacy prose):** this repo's own hermitage suite header (`core/mvcc/database/hermitage_tests.rs:17-27`) pins the CURRENT contract: snapshot taken at BEGIN; **"Write-write conflicts are detected immediately at write time (WriteWriteConflict), NOT deferred to commit (like FoundationDB)"** — plain UPDATE eagerly detects conflicts via `delete_from_table_or_index` (tests.rs:14666), while INSERT stays purely optimistic ("We do NOT check for conflicts at insert time… Conflicts are detected at commit time using end_ts comparison", mod.rs:5011-5013) and UPSERT paths can bypass eager detection (tests.rs:14857). The commit-time sweep REMAINS as backstop for insert/rewrite paths. Isolation = snapshot isolation; G2-item/write-skew NOT prevented (hermitage_tests.rs:20-21).
**Data Shape:** Input = the committing transaction's write set (rowids + unique-index keys); output = `WriteWriteConflict` error or success. Unique-index checks run a prefix-key range scan; non-unique indexes and NULL keys are deliberately skipped (SQLite semantics, :1893-1933).

### Decisive source
```rust
// mod.rs:5150-5156 — pure optimism at write time:
// "NOTE: We do NOT check for conflicts at insert time (pure optimistic).
//  Conflicts are detected at commit time using end_ts comparison."
// :1955-1960 — even a version already "ended" can conflict:
//   "Even if that version is now \"ended\", this is still a write-write conflict"
```

The rules, quoting source:
- A committed end-timestamp **greater than our begin_ts** is a conflict (:1955-1960).
- A non-infinity end timestamp "functions as a write lock on the row, so it can never be updated by another transaction" (:9905-9908, Hekaton §2.6).
- In-flight B-tree tombstones count as those write locks; our own TxID references are skipped.
- Preparing-vs-Preparing races tie-break on the **lower end_ts** — "Other tx has lower end_ts, they win."
- Unknown transaction ids are treated conservatively as conflicts, with an admitted TODO (:1998-2001).

**Flow:** optimistic writes accumulate → at Commit, reverse-scan each write-set chain once → any rule hit aborts the committer (first-committer-wins).
**Invariant:** Never add a read-time or write-time lock; validation happens exactly once per commit over the write set.
**Probe:** `core/mvcc/database/tests.rs:14887` and `:14943` stage T1-insert → Td-delete/update-commit → T2-rewrite-commit and assert `WriteWriteConflict` both times.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "check_rowid_for_conflicts WriteWriteConflict", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deferred single-pass commit validation with these exact rules (the tombstone-as-write-lock rule is the one porters miss); adapt tie-breaking to your timestamp discipline; omit index-specific scans until you have unique indexes. Coverage caveat: none material — probes pinned to direct tests.
