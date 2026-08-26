<!-- capsule-v2 -->
# MVCC garbage collection — at which intersection of two clocks may a version be reclaimed?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** When is it safe to free a row version, considering both logical snapshots and physical WAL materialization?

## GC at the intersection of the LWM and the WAL read-mark floor
**Path/Symbol:** `core/mvcc/database/mod.rs:compute_lwm` (:7071; legacy cite :7080-7095), `gc_version_chain` (:7645; legacy cite :7640-7712), `RowVersion.materialized_at` (:118-135), `is_btree_readable_at` (:9620-9660).
**Signature:** incremental pass bounded by `MAX_CHAINS_PER_GC = 4096`, triggered past `DEFAULT_GC_VERSION_THRESHOLD = 16×1024` new versions; single-flighted via CAS with RAII reset.
**Data Shape:** A version is reclaimable only when BOTH clocks allow: (1) **Logical** — no active/preparing transaction's snapshot begins below the LWM; (2) **Physical** — the version's content is durably materialized in the B-tree at a position every reader's frozen read-mark can reach. `materialized_at` tracks the WAL position where the version landed.

### Decisive source
```text
// mod.rs:9620-9660 — why physical reachability gates GC:
//   without is_btree_readable_at, "a transaction that opened before a
//   checkpoint materialization would seek a page its read mark cannot reach
//   (a torn/foreign/zeroed-page read)."
// :7638 — the tombstone trap, cited by issue number:
//   "Tombstones without a committed current successor must survive, as must
//   versions already in the B-tree… Dropping the latter erases the only
//   evidence that a later delete must be written (#7638)."
```

Per-chain rules (`gc_version_chain`): aborted garbage always goes; superseded versions go below LWM once materialized; the current version goes last, only when B-tree-resident. The pass short-circuits while the LWM is pinned (resetting its trigger baseline "so should_gc doesn't spin on every commit"), clamps candidate materialization by a backfill floor ("never reclaim a version materialized in un-backfilled WAL frames"), and shrinks surviving chains to capacity/4 (`CHAIN_SHRINK_MIN_CAPACITY = 16`). Any `set_begin`/`set_end` resets materialized_at to ORIGIN — "over-resetting is safe: it only delays GC, never reclaims early" (:9720-9722).

**Flow:** commit triggers threshold check → CAS single-flight → compute LWM → per-chain: drop aborted garbage, drop superseded-below-LWM-and-materialized, keep current unless B-tree-resident.
**Invariant:** prefer delayed GC over any early free; over-resetting materialized_at is safe, early reclamation is corruption (#7638).
**Probe:** `core/mvcc/database/tests.rs:10485` builds a chain of 1 committed + 1023 aborted-garbage versions, runs gc_version_chain, asserts dropped==1023, len==1, capacity shrunk to ≤¼+slack; `:6910-6935` covers finalized-tx cache pruning.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "gc_version_chain materialized_at compute_lwm", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-clock gating (logical AND physical) and the tombstone-survival rule verbatim; adapt thresholds/batch sizes to your workload; omit chain-capacity shrinking until long chains are observed. Coverage caveat: none material.
