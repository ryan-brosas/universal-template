<!-- capsule-v2 -->
# Shared-WAL ownership locks — how do single-writer/single-checkpointer election bytes work when OFD locks and POSIX locks behave differently?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How do you elect one writer and one checkpointer across processes — and across connections WITHIN a process — on platforms whose file locks have different granularity?

## Dual-platform ladder: OFD byte-lock first, process-local registry + supplemental lock + owner field fallback
**Path/Symbol:** `core/storage/shared_wal_coordination.rs:1707-1769` (`try_acquire_writer`/`release_writer`), :1834+ (`try_acquire_checkpoint` twin), :754 (`uses_linux_ofd_locking`), :102-138 (`LocalLockState`, `ProcessLocalOwnershipState`), :279-319 (`SharedOwnerRecord` = `(pid<<32)|instance_id`), probe helper `byte_lock_is_held` :1776-1796.
**Signature:** `pub(crate) fn try_acquire_writer(&self, owner: SharedOwnerRecord) -> bool`; release asserts the recorded owner matches ("process-local writer released by non-owner").
**Data Shape:** `.tshm` byte 0 = lifetime presence lock, byte 1 = writer, byte 2 = checkpointer, bytes 3.. = one per reader slot; owner slots store packed u64 records; UNOWNED_LOCK = 0 and owner records assert non-zero.

### Decisive source
```rust
// :1708-1731 — acquire order (non-OFD path):
let mut local = self.local_lock_state.lock();
if local.writer_lock_held { return false; }          // same-process exclusion FIRST
... try_acquire_supplemental_byte_lock(WRITER_LOCK_OFFSET)   // cross-process
    else { self...release_writer(owner); return false; }     // ROLL BACK local claim
self.header().writer_owner.store(owner.raw(), Ordering::Release);
// :1773-1775 — truth hierarchy:
// The lock byte is the authoritative cross-process liveness signal ... Shared owner
// fields are metadata and may legitimately lag behind crash recovery or repair paths.
```
On Linux, OFD byte-locks are per-fd so the byte IS both exclusions at once; on macOS POSIX fcntl locks are per-PROCESS, so the process-local registry provides same-process exclusion while the byte lock covers cross-process — hence the three-step dance with explicit rollback. Release tolerates a stale owner FIELD with only a debug log (fields lag by design) but still clears it. `repair_transient_state_for_exclusive_open` (:1275+) resets owners after proving liveness via locks, never blind.

**Flow:** acquire {local registry → OS byte lock → publish owner field} | probe {own-local flag → try-lock byte} | release {clear field → unlock → clear registry}.
**Invariant:** every failed acquisition rolls back everything already claimed; owner fields are diagnostics, lock bytes are truth; same-process counting must be per-slot counts because safety regions nest.
**Probe:** in-file tests: `mapped_shared_wal_coordination_prevents_reentrant_lock_reuse_within_same_mapping`, `_prevents_checkpoint_lock_reuse_across_mappings`, `_ignores_stale_writer_owner_field`, `_ignores_stale_checkpoint_owner_field`, `mapped_shared_wal_coordination_last_process_probe_reacquires_shared_lifetime_lock`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "try_acquire_writer SharedOwnerRecord uses_linux_ofd_locking", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lock-bytes-as-truth + registry-as-exclusion split for cross-process election on heterogeneous lock APIs. Adapt offsets/layout to your format (version-gate them). Omit owner-field diagnostics if you have no debugging surface for them.
