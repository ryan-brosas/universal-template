<!-- capsule-v2 -->
# MVCC cursor merge — how do you iterate a live version store and a materialized B-tree as one ordered stream?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** When some rows live only in MVCC and others only in the B-tree, what merge discipline yields correct order without duplicate or missing keys?

## Dual-cursor peek with per-advance consumption + finger-optimized shadow checks
**Path/Symbol:** `core/mvcc/cursor.rs:201-293` (`DualCursorPeek`, `get_next`, `cursor_position_from_next`), :386-490 (`IndexShadowFinger`), lifetime hack `static_iterator_hack!` :341-384.
**Signature:** `fn get_next(&self, dir: IterationDirection) -> Option<(RowKey, bool /*from_btree*/, Option<RowVersions<A>>)>` — returns the smaller (forwards) / larger (backwards) of the two peeked keys plus the resolved version chain when the winner is from MVCC.
**Data Shape:** each side holds ONE `CursorPeek{Uninitialized | Row{key, versions} | Exhausted}`; "we read rows from both cursors and then advance the cursor that was just consumed" — peeks are single-slot caches, not queues.

### Decisive source
```rust
// cursor.rs:201-205 — the invariant in prose:
// This means we read rows from both cursors and then advance the cursor that was just consumed.
// With DualCursorPeek we track the "peeked" next value for each cursor ...
// so that we always return the correct 'next' value (e.g. if mvcc has 1 and 3
// and btree has 2 and 4, we should return 1, 2, 3, 4 in order).
// :236-240 — forwards arm: mvcc wins ties:
if mvcc_key <= btree_key { Some((mvcc_key.clone(), false, ...)) } else { Some((btree_key...)) }
```
Tie order matters: on equal keys the MVCC chain wins because it may carry an uncommitted-or-newer shadow of the B-tree row; the `in_btree` flag tells the caller which validity rule applies. For index scans, `IndexShadowFinger` turns "is this B-tree row shadowed by an MVCC version?" from an O(log N) `index_rows.get()` per row into an amortized O(1) co-advanced merge step — seeded at the first key ≥ the B-tree key ("a seek-initiated scan does not re-walk every preceding version"), reset REQUIRED on any B-tree reposition ("a finger left ahead of the new position would report a shadowed row as valid"). The `static_iterator_hack!` macro exists because skiplist `Entry<'a,K,V>` is INVARIANT over K — lifetimes can't be coerced through a function boundary, so the transmute expands inline; safety rests on `Arc<MvStore>` outliving the cursor.

**Flow:** rewind/seek → prime both peeks → get_next picks winner → consumer advances ONLY the winning side → exhausted sides drop out → End/BeforeFirst when both empty.
**Invariant:** exactly one advance per consumed key (peek caches make double-advance impossible); finger reset on every reposition; MVCC-side tie-break preserves shadowing semantics.
**Probe:** `test_logical_log_read_table_and_index_rows`-style round-trips exercise merged iteration after restart; yield-injection tests assert byte-exact record reconstruction across mid-scan yields (btree.rs probe `process_overflow_read_survives_spill_yield_from_next_chain_read` covers the B-tree half).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "DualCursorPeek IndexShadowFinger MvccLazyCursor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-peek merge for any storage with a hot layer over a cold layer (LSM memtable+sstable analogues). Adapt tie-breaking to your shadow rules. Omit the finger until profiled hot index scans demand it — but if you port it, port its reset contract too.
