<!-- capsule-v2 -->
# Shared-WAL cross-process coordination — how do multiple processes share one WAL through an mmap'd `.tshm` file?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** What lives in shared memory vs process-local registries, and what are the reclamation rules for dead owners?

## `.tshm`: authority snapshot + ownership bytes + append-only frame index
**Path/Symbol:** `core/storage/shared_wal_coordination.rs` module doc (:1-29), layout constants (:44-70), ownership bytes (:60-64), frame-index geometry (:66-78), defensive dedup registry (:80+).
**Signature:** mmap holds (1) authoritative WAL snapshot header (`max_frame`, checksums, salts, checkpoint counters); (2) cross-process ownership: byte 0 lifetime lock (detect another process), byte 1 single-writer, byte 2 single-checkpointer, byte 3+ one reader byte per slot; (3) shared page→frame index — blocks of `FRAME_INDEX_BLOCK_CAPACITY = 4096` entries with `2×` hash slots ("Mirroring SQLite's oversubscription keeps probe chains short"), ≤64 blocks per generation.
**Data Shape:** "The shared frame index is append-only within a WAL generation and is only published after each entry is fully written, so other processes never observe half-written mappings."

### Decisive source
```text
// shared_wal_coordination.rs:21-26 — the split that porters must keep:
// "- Shared memory is the source of truth across processes.
//  - Process-local registries prevent same-process re-opens from reclaiming or
//    double-using slots that are still owned by sibling connections."
// :27-28 — the conservatism rule:
//   "Stale-owner reclamation is best-effort and must only trade performance
//    for conservatism, never correctness: if the authority cannot prove a slot
//    is dead, it must leave that slot in place."
```

Owner identity = PID + process-local monotonic instance counter (`NEXT_SHARED_OWNER_INSTANCE_ID`), which lets a same-PID stale writer field be ignored without killing a live sibling (:3141 test). Repair paths reclaim dead owners WITHOUT clearing the frame index (:3217), preserve live reader slots (:3248), and rebuild undersized files only on exclusive open (:3274).

**Flow:** open → claim lifetime lock + role/reader bytes → publish fully-written index entries → readers resolve pages via shared index → crash leaves bytes; next opener classifies and repairs conservatively.
**Invariant:** shared memory = truth; local registries = same-process exclusion; never reclaim what you cannot prove dead; never expose half-written index entries.
**Probe:** `mapped_shared_wal_coordination_reclaims_dead_reader_owner` (:3065); `process_scoped_mapping_ignores_stale_same_pid_writer_owner_field` (:3141); `mapped_shared_wal_coordination_repair_preserves_live_reader_slots_and_frame_index` (:3248).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "MappedSharedWalCoordination tshm reader slot writer lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-region mmap layout and prove-death reclamation verbatim for multi-process storage; adapt slot counts/geometry to your scale; omit the backfill-proof payload until you persist trust snapshots. Coverage caveat: probes pinned to the file's 43 in-file tests; live multi-process matrix in multiprocess_tests.rs not executed this pass.
