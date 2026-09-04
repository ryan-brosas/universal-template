<!-- capsule-v2 -->
# MVCC index-method write lease — how can BEGIN CONCURRENT serialize external-index writes without blocking readers?

**Source:** turso (MIT) `main@d9266124f` ($REFERENCE_ROOT/memory/turso); Codebase Memory `turso`. **Question:** How does a per-index write lease distinguish "another transaction is mid-write" (retryable Busy) from "my snapshot predates the published state" (restart-required WriteWriteConflict)?

## Holder + last_publish_ts in one map entry
**Path/Symbol:** `core/mvcc/database/mod.rs`: `IndexMethodWriteLease` (:3971-3978), `MvStore::index_method_write_leases: Mutex<HashMap<MVTableId, IndexMethodWriteLease>>` (:4050), `acquire_index_method_write_lease` (:6247-6273), `release_index_method_write_leases` (:6275-6294).
**Signature:** `fn acquire_index_method_write_lease(&self, tx_id: TxID, index_id: MVTableId) -> Result<()>`; release iterates ALL leases owned by tx_id at commit/rollback time.
**Data Shape:** per index_id: `holder: Option<TxID>` (the one transaction allowed to write) and `last_publish_ts: Option<u64>` (commit timestamp of the last transaction that published this index). Keyed by MVTableId = the logical table id the backing btree resolves to.

### Decisive source
```rust
// mod.rs:6259-6272 — the three-way acquire:
match lease.holder {
    Some(owner) if owner == tx_id => Ok(()),          // reentrant
    Some(_) => Err(LimboError::Busy),                 // someone mid-write: retry later
    None => {
        if lease.last_publish_ts.is_some_and(|publish_ts| publish_ts > snapshot_ts) {
            return Err(LimboError::WriteWriteConflict); // stale snapshot: restart tx
        }
        lease.holder = Some(tx_id);
        Ok(())
    }
}
```

**Flow:** first document mutation acquires (reentrant for the owning tx; contention surfaces as retryable Busy; a writer whose begin-snapshot predates the index's last publication gets WriteWriteConflict and MUST restart its transaction — `BEGIN CONCURRENT` deliberately does not parallelize same-index writes, that ceiling is documented on the enum) → release happens once per transaction end: release_index_method_write_leases looks up the tx's final TransactionState, and ONLY if Committed stamps `last_publish_ts = commit_ts` before clearing holder (:6286-6289). A rolled-back holder clears without touching last_publish_ts.
**Invariant:** last_publish_ts advances only through COMMITTED transactions — stamping it on rollback would poison the index against future writers with older snapshots even though nothing was published. The guard converts the classic lost-update anomaly for out-of-engine state into turso's standard two-error contract: Busy = wait-and-retry, WriteWriteConflict = abort-and-restart. Also gates non-rollbackable txs up front with NoSuchTransactionID (:6252-6254).
**Probe:** `core/vdbe/statement_lifecycle_tests.rs:1693-1719` `dropping_connection_mid_transaction_releases_its_fts_write_lease`: drops the writing connection mid-tx, then asserts a second connection's INSERT succeeds AND `weak.upgrade().is_none()` — the registered cursor must not keep the connection (and thus its rollback+lease-release recovery) alive via the context Arc cycle.
**Retrieve:** search_graph "acquire_index_method_write_lease IndexMethodWriteLease" resolves `turso.core.mvcc.database.mod.MvStore.acquire_index_method_write_lease` core/mvcc/database/mod.rs :6247-6273 line-exact.

## Verdict
Adopt the two-tier refusal (Busy vs WriteWriteConflict keyed on last_publish_ts > snapshot) plus commit-only publication stamping whenever external state must stay transactional under optimistic concurrency. Adapt the lock granularity (turso: one lease per logical index id). Omit nothing — this is small, self-contained, and load-bearing. Coverage: no_recorded_issue on mod.rs; direct test cited executes the drop-recovery path; the Busy/WWC arms are pinned by the FTS runtime counters' unit expectations in tests/integration/index_method/.
