<!-- capsule-v2 -->
# Commit-time conflict detection — where do write-write conflicts get validated, and by what rule?

**Source:** turso (MIT) `main@def9a0601b8e` (/mnt/hdd/utopia/inspo/memory/turso); Codebase Memory project `turso`. **Question:** How does turso get first-committer-wins serializability without any write locks or waits?

## Conflicts live at commit — and only there
**Path/Symbol:** `core/mvcc/database/mod.rs`: insert-time note (:5011-5013 at HEAD), `check_rowid_for_conflicts` / `check_index_for_conflicts` (fns at :1781/:1805; body span :1857-2040), driven from the Commit machine step (:2987-3000); tombstone-as-lock rule (:9905-9908). (Commit-sweep half of the duality — the eager write-time lane is `is_write_write_conflict` :9785-9821, covered by `mvcc-conflict-detection-duality.md`.)
**Signature:** `fn check_rowid_for_conflicts(&self, row_id: RowID, tx: &Transaction) -> Result<()>` (chains scanned in REVERSE so conflicts exit early).
**Data Shape:** inputs are the committing tx's write-set entries; each entry validates once against the row's version chain; unique-index conflicts run a prefix-key range scan and deliberately skip non-unique indexes and NULL keys (SQLite semantics, :1893-1933).

### Decisive source
```rust
// mod.rs:5150-5156
// NOTE: We do NOT check for conflicts at insert time (pure optimistic).
// Conflicts are detected at commit time using end_ts comparison.
// mod.rs:1955-1960 — even an "ended" version conflicts:
//   "Even if that version is now \"ended\", this is still a write-write conflict."
```

**Flow:** inserts never check → at commit every write-set chain is validated once → a committed end-ts greater than our begin_ts aborts us → an in-flight (non-infinity) end ts acts as a write lock on the row ("it can never be updated by another transaction", :9905-9908, again Hekaton §2.6) → in-flight B-tree tombstones count as those write locks, our own TxID references skipped → Preparing-vs-Preparing races tie-break on the LOWER end_ts ("Other tx has lower end_ts, they win") → unknown transaction ids are treated conservatively as conflicts (admitted TODO at :1998-2001).
**Invariant:** validation happens exactly once per write-set entry, in one reverse scan, inside the commit state machine — never at insert time, never spread across statement execution.
**Probe:** `core/mvcc/database/tests.rs:14887` and `:14943` stage T1-insert → Td-delete/update-commit → T2-rewrite-commit and assert `WriteWriteConflict` both times.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "check_rowid_for_conflicts WriteWriteConflict end_ts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt optimism-at-write + single reverse-scan validation at commit — that combination buys first-committer-wins without waits. Adapt the tie-break direction only together with the commit-dependency acyclicity argument (see mvcc-commit-dependencies capsule). Omit nothing here; the conservative unknown-txid arm is deliberate debt — keep or fix it consciously.
