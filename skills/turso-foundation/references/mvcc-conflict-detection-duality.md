<!-- capsule-v2 -->
# Conflict detection duality — where do write-write conflicts actually fire?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Is conflict validation at commit time only, or also inline — and which rule applies to deletes vs inserts?

## Eager check on visible-row delete, commit-time scan for the rest
**Path/Symbol:** `core/mvcc/database/mod.rs:9785-9821` (`is_write_write_conflict`), eager call sites `mod.rs:5245-5293` (`delete_from_table_or_index`) and index twin :5209-5216; commit-time ladder `check_rowid_for_conflicts` :1781 / `check_index_for_conflicts` :1805 driven from Commit state :2987-2999; the insert-time exemption comment :5011.
**Signature:** `fn is_write_write_conflict(txs, finalized_tx_states, tx: &Transaction<A>, rv: &RowVersion) -> bool`.
**Data Shape:** Input is a version chain scanned in reverse plus the writer's tx; output is a bool that maps directly to `Err(LimboError::WriteWriteConflict)`.

### Decisive source
```rust
// mod.rs:9813-9821 — Hekaton §2.6 write-lock semantics
// A non-"infinity" end timestamp (here modeled by Some(ts)) functions as a write lock
// on the row, so it can never be updated by another transaction.
Some(TxTimestampOrID::Timestamp(_)) => true,
None => false,
```
The TxID arm resolves the ender's fate via `lookup_tx_state`: Aborted/Terminated → false (their delete evaporated); Active/Preparing/Committed → **true**; unknown tx id → conservatively true with a debug log. The delete path checks visibility FIRST ("A transaction cannot delete a version that it cannot see, nor can it conflict with it"), then conflicts, and carries a self-check `turso_assert_reachable!("write-write conflict on delete")`. Inserts never check at write time:

> "NOTE: We do NOT check for conflicts at insert time (pure optimistic). Conflicts are detected at commit time using end_ts comparison. This allows multiple transactions to insert the same rowid, with first-committer-wins semantics." (:5011)

At commit, every write-set entry validates once: a committed end-timestamp greater than our begin_ts is a conflict "even if that version is now 'ended'" (:1955 region); Preparing-vs-Preparing ties break on the lower end_ts ("Other tx has lower end_ts, they win"); chains are scanned reverse so conflicts exit early; unique-index checks run a prefix-key range scan and skip non-unique indexes and NULL keys (SQLite semantics).

**Flow:** delete on visible row → eager `is_write_write_conflict` → WriteWriteConflict immediately | insert/update → defer → commit → reverse scan of write set → same predicate family + end_ts comparison.
**Invariant:** hermitage header pins the observable contract: snapshot at BEGIN, "Write-write conflicts are detected immediately at write time (WriteWriteConflict), NOT deferred to commit (like FoundationDB)" for the paths that touch an existing visible version — while first-committer-wins still governs pure inserts. A port that drops either half breaks one of the two pinned behaviors.
**Probe:** `core/mvcc/database/hermitage_tests.rs` — 25-test suite adapted from ept/hermitage: `test_hermitage_write_write_conflict`, `test_hermitage_p4_lost_update`, `test_hermitage_g2_item_write_skew` (documents that G2/write-skew are NOT prevented — snapshot isolation, not serializable); legacy probes tests.rs:14887/:14943 stage T1-insert → Td-delete-commit → T2-rewrite asserting WriteWriteConflict both times.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "is_write_write_conflict check_rowid_for_conflicts WriteWriteConflict", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-lane split: eager conflict on delete-of-visible-version, optimistic deferral for inserts, single reverse-scan validation at commit. Adapt error plumbing to your result type. Omit the conservative unknown-tx-conflict arm only if your live map can never lose entries mid-flight. ERRATUM vs prior leaf prose: mvcc.md claimed "conflicts live at commit — and only there"; current source contradicts it for deletes — this capsule supersedes that claim.
