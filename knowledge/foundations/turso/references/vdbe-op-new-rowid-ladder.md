<!-- capsule-v2 -->
# op_new_rowid resumable ladder — how do you allocate rowids across MVCC allocator, B-tree max, and random fallback without losing the lock across IO?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** Rowid generation spans a per-table lock, an async seek-to-last, counter initialization, and a bounded random search — what state must persist across each yield?

## Six-state machine; every state carries exactly what resume needs
**Path/Symbol:** `core/vdbe/execute.rs`: `enum OpNewRowidState` (:12217-12235: `Start | SeekingToLast{mvcc_already_initialized} | ReadingMaxRowid | GeneratingRandom{attempts} | VerifyingCandidate{attempts, candidate} | GoNext`), `op_new_rowid` error wrapper (:12237-12262), `new_rowid_inner` machine (:12264-12486).
**Signature:** states read/written via `*state.active_op_state.new_rowid()` (lazy-init `OpNewRowidState::Start`); constants `MAX_ROWID = i64::MAX`, `MAX_ATTEMPTS: u32 = 100`.
**Data Shape:** `SeekingToLast` remembers whether the MVCC allocator was already initialized (decides GoNext vs ReadingMaxRowid); `GeneratingRandom/VerifyingCandidate` carry attempt counters + the in-flight candidate across yields.

### Decisive source
```rust
// execute.rs:12358-12365 — init under the held lock:
//   if let Some(mvcc_cursor) = cursor.downcast_mut::<MvCursor>() {
//       // Initialize the monotonic counter from the btree max.
//       // The allocator lock is held, so no other thread can
//       // race between this read and initialize.
//       mvcc_cursor.initialize_max_rowid(current_max)?;
// :12417-12422 — random mode masks to the LOWER half:
//   // We use the lower half (1 to MAX_ROWID/2) because we're in random mode only
//   // when sequential allocation reached MAX_ROWID, meaning the upper range is full.
//   random_rowid &= MAX_ROWID >> 1;
// :12243-12261 — every error path releases the allocator lock via inspect_err → end_new_rowid()
```
Lock lifecycle: `start_new_rowid()` takes the per-table allocator lock (yielding a bare Completion if another cursor holds it, cursor.rs:725-747); `end_new_rowid()` releases — called on the fast Next arm (:12301), on FindRandom (:12312), after verification succeeds (:12449-12455), in GoNext (:12474-12480), on ANY error via the wrapper, and defensively in `Drop` for statements dropped mid-yield. The btree path mirrors SQLite: seek_to_last → rowid()=max ⇒ max+1; empty table ⇒ 1; exhausted ⇒ random. `GoNext` exists because the cursor sits ON the max row and the subsequent insert expects to be positioned AFTER it (:12231-12234).

**Flow:** Start → (MVCC? try allocator fast path / Uninitialized / FindRandom) → SeekingToLast{flag} → ReadingMaxRowid (init counter under lock, allocate first id; non-MVCC writes prev_largest + max+1) → GoNext (cursor.next(), then end_new_rowid) — or GeneratingRandom ⇄ VerifyingCandidate (seek GE eq_only; collision ⇒ attempts+1, 100 strikes ⇒ DatabaseFull).

**Invariant:** the allocator lock is never dropped by an IO yield (it lives in the cursor, not the slot); allocation stays monotonic until i64::MAX, after which random candidates are masked to [1, MAX/2] and verified absent before use.

**Probe:** structural pins at HEAD via search_graph (`turso.core.vdbe.execute.op_new_rowid`, execute.rs:12237-12262); allocator semantics pinned by `mvcc-rowid-allocation.md`'s cited round-trips (`test_logical_log_roundtrip_random_table_ops`). Coverage caveat: upstream has no dedicated op_new_rowid unit test file; deterministic source checks stand in (no cargo runner).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "OpNewRowidState new_rowid_inner start_new_rowid end_new_rowid NextRowidResult", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-tier ladder (monotonic allocator → btree max+1 → bounded random with existence check) and the lock-held-across-IO discipline. Adapt the random mask to your id-space exhaustion policy. Omit GoNext if inserts don't require post-max positioning. Coverage caveat recorded above.
