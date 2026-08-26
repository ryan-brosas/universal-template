<!-- capsule-v2 -->
# IndexShadowFinger lazy shadow bit — why must the co-advanced finger NOT resolve visibility while stepping over MVCC-only keys?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** A finger turns per-row shadow checks into an amortized O(1) merge — but which side effect hides in resolving the shadow predicate, and where must it be deferred?

## Peeked{key, versions} resolves the chain ONLY on an exact B-tree-key match
**Path/Symbol:** `core/mvcc/cursor.rs`: `enum IndexShadowFinger` (:391-405: `Uninitialized | Peeked { iter, key, versions } | Exhausted`), `advance` (:418-427), `btree_row_is_valid` (:432-489), consumer `MvccLazyCursor::btree_row_is_valid_forward` (:600-628).
**Signature:** `fn btree_row_is_valid<Clock: LogicalClock>(&mut self, db: &MvStore<Clock, A>, table_id: MVTableId, tx_id: u64, key: &Arc<SortableIndexKey>) -> bool`.
**Data Shape:** finger states: `Peeked` holds the skiplist iterator + cloned key/version-chain Arcs (no borrowed Entry survives); `Exhausted` ⇒ every remaining B-tree row visible. Compare arm per call: finger_key Greater ⇒ visible (no version at/after key); Equal ⇒ resolve `!db.index_chain_invalidates_btree(versions, tx_id)`; Less ⇒ step forward and loop.

### Decisive source
```rust
// cursor.rs:395-402 — the laziness contract:
//   Positioned at `key`, holding its version chain. The shadow bit is resolved
//   lazily (only when a B-tree row matches this key exactly)
// cursor.rs:474-478 — resolution point:
//   // Version present at this key -> resolve the shadow bit now,
//   // on the one key that actually matches a B-tree row.
//   std::cmp::Ordering::Equal => {
//       return !db.index_chain_invalidates_btree(versions, tx_id);
```
Why it matters beyond perf: `index_chain_invalidates_btree` can register a commit dependency on a speculative writer. An EAGER design that evaluated the predicate on every advance would attach the reader to writers whose rows the scan never observes — a spurious dependency that cascade-aborts the reader when that writer later aborts. The debug build cross-checks the fast path against authoritative `query_btree_version_is_valid` on every row (:617-626 "index finger diverged from query_btree_version_is_valid"), so any missed reset fails tests instead of shipping.

**Flow:** first check with `Uninitialized` → seed range iterator at `(Included(key), Unbounded)` ("a seek-initiated scan does not re-walk every preceding version") → advance clones key+chain into `Peeked` → per B-tree row run the three-arm compare; only Equal touches the version chain and its side effects → epoch mismatch (`index_finger_epoch != db.index_rows_epoch()`, checked BEFORE reseeding) or any reposition resets to Uninitialized.

**Invariant:** the shadow predicate (with its commit-dependency side effect) executes at most once per key, and only for keys that exactly match a B-tree row; stepped-over MVCC-only keys stay side-effect-free.

**Probe:** `core/mvcc/database/tests.rs:7093` (`test_index_finger_no_spurious_dep_on_stepped_over_key`) — B-tree keys 10/30 plus an MVCC-only tombstone at 20 deleted by a `Preparing` writer; scan must see both rows visible AND leave `commit_dep_counter == 0` / the writer's commit-dep set empty (:7167-7177).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "IndexShadowFinger btree_row_is_valid index_chain_invalidates_btree register_commit_dependency", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-arm compare with predicate resolution restricted to exact matches whenever your shadow check has observable side effects (dependency registration, stats, locks). Adapt seeding bounds to your ordered map API. Omit the transmute-based `'static' iterator hack` if your language coerces lifetimes through functions. Coverage caveat: probe test not executed here (no cargo runner); source read directly at HEAD.
