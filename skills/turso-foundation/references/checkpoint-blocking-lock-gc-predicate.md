<!-- capsule-v2 -->
# Blocking-lock-flag dual role — why is the checkpoint's own lock flag read as a GC safety predicate?

**Source:** turso MIT `main@def9a0601b8ead82675e672e1843447251b15fb4`; Codebase Memory `turso`. **Question:** Why does version-GC consult a boolean that means "I hold the blocking checkpoint lock", and what breaks if you replace it with a store-level lock query?

## LockStates.blocking_checkpoint_lock_held as GC-mode discriminator
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs` — field `LockStates.blocking_checkpoint_lock_held: bool` :149; acquisition sites :1993-1998 (`AcquireLock`, blocking mode), passive publish window :2719-2723 / :2780-2784 / :2918-2922 (brief write lock taken just for publish); release :857-869 via `release_checkpoint_locks_if_needed`; predicate reads `gc_checkpointed_table_versions` :1774-1775 and `gc_checkpointed_index_versions` :1840-1841; Finalize branch :2987-2997.
**Signature:** `let drop_current_if_in_btree = self.lock_states.blocking_checkpoint_lock_held || !self.mvstore.experimental_mvcc_passive_checkpoint;`
**Data Shape:** Pure `bool &&/||` composition — no locking, no atomics. True ⇒ SkipMap current copies may be dropped during GC; False (passive, flag unset) ⇒ keep latest SkipMap copy per row and floor the sweep with `gc_floor_reader_mark()`.

### Decisive source
```rust
// Finalize :2987-2997 — same flag picks the GC kernel:
if self.lock_states.blocking_checkpoint_lock_held {
    // Truncate: under the blocking lock, drop last SkipMap copies and empty slots.
    // That lock waits out open MVCC txs, so no old reader can see a later rewrite.
    self.mvstore.drop_unused_row_versions_and_slots();
} else {
    // Passive: ... keep the latest SkipMap copy of each row. Without it, an older
    // reader can fall through to a B-tree page that a later checkpoint already rewrote.
    self.mvstore.drop_unused_row_versions_unlink_empty_at(self.gc_floor_reader_mark());
}
```

**Flow:** The flag answers ONE question at two decision points: "are B-trees stable right now?" Under the blocking lock (Truncate mode) all open MVCC transactions were waited out, so after versions are written into the B-tree the SkipMap copies are redundant → aggressive GC (`drop_unused_row_versions_and_slots`, :7211). In passive mode the blocking lock is deferred to a brief publish-window grab (:2719+/:2780+/:2918+) while collection/write run concurrently — so between collection and publish an old reader can still hold a pre-checkpoint snapshot → conservative GC keeps the newest in-memory version and floors deletion at the pager reader mark (`drop_unused_row_versions_unlink_empty_at(floor)`, :7218). The SAME flag doubles as the cleanup ledger bit (:857-869) deciding whether unlock runs.
**Invariant:** The flag is OWNERSHIP-tracked state of THIS machine instance, not a global "is anyone checkpointing" query — substituting `mvstore.checkpoint_in_progress` (the AtomicBool at core/mvcc/database/mod.rs:4039) or a WAL/pager lock probe would read OTHER machines' state and let a passive checkpoint aggressively drop current copies while another connection still reads them, resurrecting the exact fall-through-to-rewritten-page corruption the passive branch documents. It also gates legality asymmetrically: acquire-only-if-not-held (:1993) makes publish-window re-entry idempotent.
**Probe:** `core/mvcc/database/tests.rs:1007 mvcc_passive_auto_checkpoint_retries_publish_while_reader_pinned` + :964 `mvcc_passive_checkpoint_busy_under_pinned_reader_no_corruption` — pinned-reader scenarios pin exactly this conservative-vs-aggressive split (retry publish while reader holds snapshot; no corruption under pinned reader).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "release_checkpoint_locks_if_needed LockStates", limit: 10, fields: ["signature", "name", "file"] });
// resolves Method :857-869 + Struct LockStates :148-152 (+3 Field nodes)
```

## Verdict
Adopt the ownership-tracked-lock-as-mode-predicate pattern (per-machine bool, not a shared lock-state query) whenever a background maintenance job has a blocking and a concurrent mode sharing one code path. Adapt the specific flag placement to your state-machine struct. Omit the tempting "just query the lock manager" refactor — it is the wrong-port trap this capsule exists to prevent. Distinct from `checkpoint-gc-floor` (which owns the three-mark floor VALUE); this owns WHY the aggressive/conservative kernel choice keys off a machine-local lock bit. Coverage caveat: none (`no_recorded_issue`, generation matches).
