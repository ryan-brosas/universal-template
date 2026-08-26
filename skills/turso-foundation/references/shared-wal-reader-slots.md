<!-- capsule-v2 -->
# Shared-WAL reader slots — how do cross-process readers publish snapshot bounds and reclaim dead owners without ever stealing a live slot?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** In a multi-process mmap coordination file, what is the authoritative liveness signal for a reader slot, and in what order do you check, claim, and reclaim?

## Bitmap-CAS → byte-lock acquire → owner/frame publish; reclaim ONLY on provable death
**Path/Symbol:** `core/storage/shared_wal_coordination.rs:1970-2064` (`register_reader`, 2-attempt ladder), :2067-2079 (`update_reader`, non-owner assert), :2189-2245 (`min_active_reader_frame` with inline reclamation), stale sweep `try_reclaim_stale_reader_slot`/`reclaim_stale_reader_slots` :1910-1958.
**Signature:** `pub(crate) fn register_reader(&self, owner: SharedOwnerRecord, max_frame: u64) -> Option<SharedReaderSlot>`; `SharedReaderSlot{slot_index, max_frame, owner}`; `UNUSED_READER_FRAME = u64::MAX` sentinel.
**Data Shape:** per-slot state lives in THREE places that must agree: a shared bitmap word (1 = free, cleared via CAS to claim), an OFD/supplemental byte-range lock (the AUTHORITATIVE cross-process liveness signal), and two shared atomics (`reader_owner`, `reader_frames`). A process-local registry (`LocalLockState` counts + `ProcessLocalOwnershipState` owners) prevents same-process siblings from colliding — per-slot COUNTS not booleans, because connections nest.

### Decisive source
```rust
// :1773-1775 — which signal wins:
// The lock byte is the authoritative cross-process liveness signal for
// writer/checkpoint/reader ownership. Shared owner fields are metadata and
// may legitimately lag behind crash recovery or repair paths.
// :1281-1288 — why blind clearing is forbidden:
// For reader slots, we must NOT blindly clear slots owned by
// live processes: doing so would cause those processes to panic with
// "reader slot released by non-owner" when they try to end their read
// transactions, corrupting the shared WAL state.
```
Claim order inside the loop: local-lock skip-check → CAS bitmap bit → acquire byte lock (on failure: restore bitmap bit via fetch_or, break) → store owner+frame with Release. If all slots taken, ONE retry after `reclaim_stale_reader_slots()` probes each holder: OFD lock acquirable ⇒ dead ⇒ clear frame/owner/bitmap under the probe lock; on macOS (POSIX per-process locks) PID-liveness (`kill(pid,0)`, EPERM counts as alive) substitutes. `min_active_reader_frame` folds reclamation into its min() scan — checkpoints get both the safe backfill boundary and freed slots in one pass.

**Flow:** register → attempt ×2 → Some(slot) | None (all occupied by LIVE processes) → update_reader moves only your own frame → unregister asserts owner match.
**Invariant:** never treat owner FIELDS as truth while holding no lock; never clear a slot whose byte lock you couldn't acquire; every failed acquisition must roll back the previously-taken resource (bitmap bit restored before returning).
**Probe:** in-file suite (`mod tests` :2915+, 43 tests): `mapped_shared_wal_coordination_reclaims_dead_reader_owner` (forks an exited child for a real dead PID), `process_scoped_mapping_reclaims_stale_same_pid_reader_slot`, `mapped_shared_wal_coordination_shares_lock_and_reader_state`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "register_reader reclaim_stale_reader_slot min_active_reader_frame", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-layer slot model (bitmap + OS lock + metadata) with lock-bytes-as-truth for any multi-process shared resource pool. Adapt reclamation probes to your platform's lock semantics. Omit same-snapshot slot sharing until connection density demands it.
