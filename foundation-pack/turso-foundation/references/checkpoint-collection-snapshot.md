<!-- capsule-v2 -->
# Checkpoint collection snapshot — how do you pick checkpointable versions when transactions are still in flight and tombstones land after your snapshot?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** Which committed row versions belong in this checkpoint's write set, and what must happen to versions whose commit events straddle the collection snapshot?

## Snapshot-bounded selection with future-tombstone clamping
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs:maybe_get_checkpointable_versions` (:912-1047), snapshot sampling `MvStore::checkpoint_snapshot_ts` (mod.rs:7014-7030), `durable_txid_max_new = max(old, snapshot_ts)` (:2105-2115), metadata staging gate (:1897-1950).
**Signature:** `fn maybe_get_checkpointable_versions(&self, versions: &[RowVersion], table_id: MVTableId) -> SmallVec<[RowVersion; 1]>`; `checkpoint_snapshot_ts() -> u64` = `min(last_committed_tx_ts, min(Preparing(ts)) - 1)`.
**Data Shape:** begin/end resolved through `lookup_tx_state`: raw `TxID` markers count only if their transaction reached `Committed(ts)`, else None; `(None, None)` pairs (rolled-back garbage, active placeholders) are skipped entirely; `btree_resident: true` seeds "exists in DB file" before any timestamp rule runs.

### Decisive source
```rust
// :949-960 — the two straddle rules a porter will get wrong:
// "Insert not visible at our snapshot (committed during the collection
//  phase): defer to the next pass and don't let it affect DB-file existence now."
//   → if begin_ts > snapshot_ts: continue;
// "Tombstone committed after our snapshot: clamp to \"live\" (end=None) so the
//  row is checkpointed as PRESENT, not stranded; a later pass (delete <=
//  snapshot) checkpoints the deletion. Fixes the future-tombstone orphan bug."
//   → if end_ts > snapshot_ts: end_ts = None;
// :971-974 — ordering constraint:
// "These timestamp-derived transitions must run after the btree_resident seed
//  so a checkpointed tombstone can clear DB-file existence on a retry checkpoint."
```

**Flow:** resolve begin/end to timestamps via tx-state lookup → skip post-snapshot inserts → clamp post-snapshot tombstones to live → skip (None,None) garbage → seed/clear `exists_in_db_file` (`btree_resident` first, then `begin<=max_old` sets it, then `end<=max_old` clears it) → keep version iff uncheckpointed-insert OR delete-of-existing-row OR schema-delete-of-uncheckpointed-btree-object → push clone with normalized/clamped end; non-schema rows collapse to newest, schema rows honor drop-pair semantics.
**Invariant:** every collected version's terminal timestamp ≤ `snapshot_ts`, which becomes `durable_txid_max_new` — so the persisted replay watermark never exceeds what the B-tree actually received; existence tracking is order-sensitive (btree_resident seed BEFORE timestamp transitions).
**Probe:** `checkpoint_state_machine.rs::tests::checkpoint_collection_uses_btree_marker_for_existence_but_writes_surviving_replacement` (:3515), `checkpoint_collection_uses_btree_marker_for_later_delete_of_replacement` (:3530), `checkpoint_collection_skips_delete_of_never_checkpointed_replacement_without_btree_marker` (:3545); retry idempotence `checkpoint_retry_does_not_replay_checkpointed_btree_resident_delete` (:3415).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "maybe_get_checkpointable_versions checkpoint_snapshot_ts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-gate selection ladder + snapshot clamp verbatim for any store→file materializer under concurrent commits; adapt the `btree_resident` seeding to whether you have a pre-MVCC resident flag; omit schema-delete special-casing if your catalog has no uncheckpointed-sentinel encoding. Coverage caveat: none material — probes are direct tests.
