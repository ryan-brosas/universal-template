<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Weaviate Foundation

## Use this for

Porting or operating **Weaviate** (`Weaviate B.V.`, BSD-3-Clause, Go) — a distributed
vector database whose two load-bearing engines are (1) a concurrency-hardened HNSW
vector index with three filtered-search strategies and (2) LSMKV, its own log-structured
KV store. Reach for this foundation when you need:

- **Filtered vector search that actually returns results under sparse filters** —
  strategy FSM (SWEEPING/ACORN/RRE), flat-search cutoff, ef ladder.
- **Deletes without rebuilds** — lazy tombstones, cycle-capped cleanup with
  memory-pressure aborts, dead-entrypoint self-repair.
- **Crash-safe index persistence** — commit-log rotation that can never append to a
  snapshot file; WAL recovery where only the newest log becomes live memory.
- **A production LSM store** — non-blocking four-phase memtable flush, level-pair
  compaction selection, replace-strategy merge semantics.
- **Multi-vector (ColBERT-style) storage** — doc-id/vec-id dual id spaces,
  purge-on-retry batch inserts, sum-of-min late-interaction rescoring.

Not for: GraphQL/gRPC API surface, module (vectorizer) integrations, replication/raft
consensus — those are product layers above these kernels.

## Load the matching source dump

Repo at `$REFERENCE_ROOT/external/weaviate` @ `main@adcffc54`. Graph project:
`ext-weaviate` (58,975 nodes / 603,991 edges). Key trees:

- `adapters/repos/db/vector/hnsw/` — index.go (state), search.go (1,487L strategies),
  insert.go, delete.go, heuristic.go, neighbor_connections.go, flat_search.go,
  commit_logger.go
- `adapters/repos/db/lsmkv/` — bucket.go (3,043L), segment_group_compaction.go,
  compactor_replace.go, bucket_recover_from_wal.go
- Tests co-located per package (`*_test.go`); `cmd/weaviate-server` is excluded from
  the graph by ignore rules.

## Load capsules

- `./hnsw-filtered-search-strategy-selection.md` — SWEEPING/ACORN/RRE decision gates + entrypoint-neighborhood ratio test.
- `./hnsw-sweeping-filter-at-results.md` — traverse everything, filter only result insertion; MaxFloat32 empty-results fallback.
- `./hnsw-acorn-two-hop-expansion.md` — ε-neighborhood BFS (2 hops, 8×M0 cap, dual visited sets).
- `./hnsw-flat-search-cutoff.md` — allow-list < cutoff ⇒ parallel brute force instead of graph walk.
- `./hnsw-ef-resolution-ladder.md` — explicit ef → floor k; dynamic efWindow factor→clamp→floor-k.
- `./hnsw-addone-insert-path.md` — first-insert sync.Once, maintenance flag window, double-checked entrypoint promotion.
- `./hnsw-tombstone-lifecycle.md` — delete locks stack, min/max-per-cycle caps, alloc-checker abort, reassign-before-remove ordering.
- `./hnsw-dead-entrypoint-self-repair.md` — termination-guaranteed EP probe loop; CAS-guarded global EP replacement.
- `./hnsw-neighbor-selection-heuristic.md` — diversity filter; in-place queue mutation contract; compressed-bag pairwise path.
- `./hnsw-multivector-docid-mapping.md` — contiguous vec-id blocks, `_mv_mappings` bucket, purge stale docs before retry, budgeted sum-of-min scoring.
- `./hnsw-commitlog-rotation.md` — fresh-file startup, open-before-close rotation, old-name-derived burst-safe naming, fsync only on rotate.
- `./hnsw-search-by-vector-distance-recursion.md` — ×10 growing-window rescan for "everything within distance d" queries.
- `./lsmkv-flush-and-switch.md` — four-phase non-blocking flush; serializer mutex; leftover-flushing drain; inverted-tombstone fan-out race acceptance.
- `./lsmkv-compaction-candidate-selection.md` — newest same-level pair, descending-level invariant, size-limit escape hatches, lazy level-order healing.
- `./lsmkv-replace-strategy-compaction.md` — c1 older/c2 newer merge, root-only tombstone cleanup, key arena vs cursor buffer reuse.
- `./lsmkv-wal-recovery.md` — sort WALs chronologically; last healthy = active memtable, rest flush to segments; torn tails tolerated.
- `./lsmkv-bucket-lifecycle-locks.md` — registry claim before IO, lifetimeLock drain-before-free (no timeout ⇒ no SEGFAULT), claim released only on clean shutdown.

## Capsule map
- **ACORN two-hop neighbor expansion** — `hnsw-acorn-two-hop-expansion`: how a filtered graph walk escapes filtered-out dead zones.
- **addOne insert path** — `hnsw-addone-insert-path`: first-insert Once, maintenance flag, entrypoint promotion double-check.
- **Commit-log rotation** — `hnsw-commitlog-rotation`: never reuse a file, open-before-close, name derived from the old name.
- **Dead-entrypoint self-repair** — `hnsw-dead-entrypoint-self-repair`: entrypointDistWithRepair / repairGlobalEntrypoint termination ladder.
- **ef resolution ladder** — `hnsw-ef-resolution-ladder`: explicit ef, dynamic efWindow, and the k floor.
- **HNSW filtered-search strategy FSM** — `hnsw-filtered-search-strategy-selection`: which filter algorithm runs, and why a naive port picks the wrong one.
- **Flat-search cutoff** — `hnsw-flat-search-cutoff`: tiny allow-lists bypass the graph entirely.
- **Multivector doc-id mapping** — `hnsw-multivector-docid-mapping`: vec-id vs doc-id id spaces, purge-before-retry, late-interaction scoring.
- **Neighbor selection heuristic** — `hnsw-neighbor-selection-heuristic`: diversity filter with compressed-bag fast path.
- **SearchByVectorDistance geometric-threshold recursion** — `hnsw-search-by-vector-distance-recursion`: growing-window rescan with offset arithmetic.
- **SWEEPING filtered layer search** — `hnsw-sweeping-filter-at-results`: filter at result-insert, never at traversal (except RRE).
- **Tombstone lifecycle** — `hnsw-tombstone-lifecycle`: lazy delete marks, cycle-capped cleanup, memory-pressure abort.
- **Bucket lifecycle locks** — `lsmkv-bucket-lifecycle-locks`: double-open refusal, lifetimeLock drain-before-free, shutdown ordering.
- **Level-pair compaction candidate selection** — `lsmkv-compaction-candidate-selection`: descending-level invariant, size limits, level-order repair.
- **FlushAndSwitch four-phase non-blocking flush** — `lsmkv-flush-and-switch`: leftover-drain, writer drain, tombstone fan-out race.
- **Replace-strategy segment merge** — `lsmkv-replace-strategy-compaction`: c2 wins conflicts, tombstone cleanup at root, arena-stable keys.
- **WAL crash recovery** — `lsmkv-wal-recovery`: newest WAL becomes the memtable, older WALs flush to segments, corruption is tolerated.
## Extending the foundation

1. Pick one seam (one porting question) from the source tree above.
2. Confirm it in the graph: `search_graph {project:"ext-weaviate", query:"<symbol>"}`,
   then read the decisive range plus its direct test file.
3. Author ONE `<!-- capsule-v2 -->` reference from `.pi/templates/foundation-capsule.md`
   (Source/Question, Path/Symbol, Signature, Data Shape, Decisive source, Flow,
   Invariant, Probe on a real test, Retrieve, Verdict).
4. Live-execute the Probe grep byte-exact BEFORE wiring; add the loader line here AND
   a Capsule map entry; run parity (disk == loader == map as sets).
5. Record evidence in `.pi/work/foundations-deep-farm/research.md`.

## Provenance

- Repo: `$REFERENCE_ROOT/external/weaviate`, branch `main`, pin
  `adcffc5432aa797c60e3c4e479514054254fae2a` (= graph base_sha/head_sha; upstream had
  drifted to `0508b8c1` but this pass mines the pinned state deliberately).
- Codebase Memory project `ext-weaviate`: ready, FULL mode, generation matches working tree.
- License: BSD-3-Clause (`LICENSE` in repo root). All capsules cite paths inside
  `adapters/repos/db/**` only.
- Pass 1 (2026-08-24): 16 capsule-v2 references authored from whole-file reads of
  hnsw/{search,index,insert,delete,heuristic,neighbor_connections,flat_search,commit_logger}.go
  and lsmkv/{bucket,segment_group_compaction,compactor_replace,bucket_recover_from_wal}.go;
  every Probe anchor grep-executed against the pin; every Retrieve live-resolved rank-1/rank-2.

## Full view (memory graph)

```
codebase-memory-mcp cli get_architecture --project ext-weaviate --aspects '["structure","hotspots"]'
codebase-memory-mcp cli search_graph '{"project":"ext-weaviate","query":"<symbol>","limit":10,"detail":"compact"}'
```

Node census (graph gen 2026-08-23): 18,729 Functions / 16,240 Methods / 6,564 Structs /
5,302 Files across 15 packages; edge mix dominated by USAGE (220k) and CALLS (132k),
with TESTS edges (46k) giving per-symbol test adjacency. BM25 plane is healthy —
Function/Method nodes carry searchable tokens; Module nodes resolve via `search_code`.
Note: `cmd/weaviate-server` excluded by design; cite `adapters/**`, `entities/**`,
`usecases/**` paths in Retrieve blocks.

## Boundaries

- Mined scope = the two storage kernels listed above. NOT covered: raft/replication
  (`cluster/`), GraphQL parser & cross-referencing resolver, modules/* vectorizers,
  backups, schema manager, hfresh (the newer experimental index) — next-pass targets.
- Compression internals (PQ/SQ/RQ/BQ quantizers in `compressionhelpers/`) appear only
  via their interfaces (`CompressorDistancer`, `VectorCompressor`); their algorithms
  are unmined seams.
- Go-specific mechanics (goroutine pools, `sync.Map`, atomic idioms) must be adapted,
  not transcribed, when porting to other languages.
- Direct tests cited are unit/integration files in-repo; running them requires a Go
  toolchain (absent on this host at pass time — probes were executed as byte-exact
  greps against source instead).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`hnsw-acorn-two-hop-expansion.md`](./hnsw-acorn-two-hop-expansion.md)
- [`hnsw-addone-insert-path.md`](./hnsw-addone-insert-path.md)
- [`hnsw-commitlog-rotation.md`](./hnsw-commitlog-rotation.md)
- [`hnsw-dead-entrypoint-self-repair.md`](./hnsw-dead-entrypoint-self-repair.md)
- [`hnsw-ef-resolution-ladder.md`](./hnsw-ef-resolution-ladder.md)
- [`hnsw-filtered-search-strategy-selection.md`](./hnsw-filtered-search-strategy-selection.md)
- [`hnsw-flat-search-cutoff.md`](./hnsw-flat-search-cutoff.md)
- [`hnsw-multivector-docid-mapping.md`](./hnsw-multivector-docid-mapping.md)
- [`hnsw-neighbor-selection-heuristic.md`](./hnsw-neighbor-selection-heuristic.md)
- [`hnsw-search-by-vector-distance-recursion.md`](./hnsw-search-by-vector-distance-recursion.md)
- [`hnsw-sweeping-filter-at-results.md`](./hnsw-sweeping-filter-at-results.md)
- [`hnsw-tombstone-lifecycle.md`](./hnsw-tombstone-lifecycle.md)
- [`lsmkv-bucket-lifecycle-locks.md`](./lsmkv-bucket-lifecycle-locks.md)
- [`lsmkv-compaction-candidate-selection.md`](./lsmkv-compaction-candidate-selection.md)
- [`lsmkv-flush-and-switch.md`](./lsmkv-flush-and-switch.md)
- [`lsmkv-replace-strategy-compaction.md`](./lsmkv-replace-strategy-compaction.md)
- [`lsmkv-wal-recovery.md`](./lsmkv-wal-recovery.md)
