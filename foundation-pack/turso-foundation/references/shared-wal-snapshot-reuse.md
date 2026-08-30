<!-- capsule-v2 -->
# Shared-WAL snapshot reuse — how do same-process readers at the SAME snapshot share one scarce slot without double-release races?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** When N connections in one process read at identical max_frame, how do they avoid exhausting the global reader-slot pool — and who releases the shared slot?

## Keyed refcount registry: retain-before-acquire, publish-once, release-returns-must-free
**Path/Symbol:** `core/storage/shared_wal_coordination.rs:2085-2111` (`register_reader_for_snapshot`), :223-276 (`ProcessLocalOwnershipState` snapshot-reader methods), unregister path :2113+.
**Signature:** `pub(crate) fn register_reader_for_snapshot(&self, owner, max_frame) -> Option<SharedReaderSlot>`; `release_shared_snapshot_reader(slot) -> bool` — true ONLY when caller must also free the underlying slot.
**Data Shape:** `HashMap<u64 /*max_frame*/, SharedReadMarkRegistration{slot, ref_count}>` in process-local state; invariant assert on publish ("replaced a live registration" must be unreachable); release asserts slot identity AND refcount > 0.

### Decisive source
```rust
// :2081-2084 — the reason:
// Multiple sibling connections reading the same `max_frame` should share
// one slot so they do not exhaust the global reader-slot pool.
// :2097-2107 — the race window handled:
let slot = self.register_reader(owner, max_frame)?;   // took a FRESH slot...
if let Some(existing_slot) = process_local.shared_snapshot_reader(max_frame) {
    // ...but a sibling published theirs first → keep THEIRS, drop mine:
    drop(process_local);
    self.unregister_reader(slot);
    return Some(existing_slot.slot);
}
```
The check-after-acquire ordering is load-bearing: registration and publication can't hold one mutex across the OS byte-lock acquisition (lock-ordering hazard vs other paths), so a tie is resolved by loser-drops-freshly-taken-slot. Release decrements the count and only signals "free it" when it hits zero — callers can't double-free a shared slot because they never owned it individually.

**Flow:** register_for_snapshot {retain existing? → done | acquire fresh → re-check → keep winner} … release_shared {decrement; zero ⇒ true ⇒ caller unregisters}.
**Invariant:** exactly one live registration per max_frame per process; the last releaser is the only freer; a lost race must undo its own acquisition before returning.
**Probe:** in-file tests: `process_local_ownership_state_tracks_same_process_exclusion`, `process_scoped_mapping_drop_releases_same_process_ownership`; reader-pool pressure pinned wal-side by `test_read_retry_does_not_leak_vacuum_guard_or_block_vacuum` (wal.rs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "register_reader_for_snapshot shared_snapshot_readers ref_count", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt keyed-refcount sharing for any pool of cross-caller resources with identical state. Adapt keying (max_frame → your snapshot token). Omit if your slot pool exceeds your connection fan-out.
