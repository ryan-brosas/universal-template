<!-- capsule-v2 -->
# Shared-WAL mmap lifecycle — how do you open, share, and tear down a coordination file so the last process out doesn't corrupt late readers?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What distinguishes process-scoped from durable mapping state at create/open/drop time — and what must survive vs reset?

## create_or_open mode ladder + Drop releases owned locks + defensive same-process dedup
**Path/Symbol:** `core/storage/shared_wal_coordination.rs:745-1078` region (`create_or_open` :864, `open_existing` :875, `create_or_open_with_mode` :905, `open_existing_with_mode` :978, `is_last_process_mapping` :1078), Drop :716-722 & `release_owned_locks_on_drop` :1092, defensive registry :76-100 (`PROCESS_LOCAL_COORDINATION_OPENS`, "enforces that invariant for callers that bypass the manager"), rebuild-on-open `mapped_shared_wal_coordination_rebuilds_undersized_file_on_exclusive_open`.
**Signature:** `pub(crate) fn create_or_open(io, path, reader_slot_count) -> Self`; drop path asserts and releases every lock this mapping still owns.
**Data Shape:** durable = header fields (magic+version-gated), frame index blocks; TRANSIENT = lifetime lock byte, owner slots, reader bitmap/locks. File persists after last close ("persists_file_after_last_close" test) but its ownership bytes are re-sanitized on next exclusive open.

### Decisive source
```rust
// :16-24 — module-doc split of responsibilities:
// - Shared memory is the source of truth across processes.
// - Process-local registries prevent same-process re-opens from reclaiming or
//   double-using slots that are still owned by sibling connections.
// - ... Stale-owner reclamation is best-effort and must only trade performance for
//   conservatism, never correctness: if the authority cannot prove a slot is
//   dead, it must leave that slot in place.
```
The test names enumerate the lifecycle hazards: reopen after stale owner FIELDS must not treat them as held locks; undersized files rebuild on EXCLUSIVE open only; last-process detection reacquires the shared lifetime lock rather than deleting. The dedup registry is documented as production-invariant-enforcement (DATABASE_MANAGER guarantees one mapping per file per process) with cfg(test) shims — a pattern for making "only one X per Y" checkable instead of assumed.

**Flow:** create-or-open {detect mode → validate/repair header → map regions} → connections share via Arc → Drop {release OWNED locks only → unmap} → file remains for forensics/next open.
**Invariant:** teardown releases exactly what this mapping provably holds (registry-counted); conservative reclamation beats aggressive: an unprovable-dead slot is kept.
**Probe:** in-file tests: `mapped_shared_wal_coordination_persists_file_after_last_close`, `_last_process_probe_reacquires_shared_lifetime_lock`, `_rebuilds_undersized_file_on_exclusive_open`, `process_scoped_mapping_reopens_after_stale_owner_fields`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "MappedSharedWalCoordination create_or_open release_owned_locks_on_drop", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt durable-vs-transient field partitioning with version gates for any shared-memory control block. Adapt the lifetime-lock scheme to your OS. Omit the bypass-dedup registry if your manager layer already enforces uniqueness structurally.
