---
name: duckdb-foundation
description: "Use when porting analytical-database internals — DPhyp join ordering, cardinality estimation, and adaptive-radix-tree index machinery. Source code and direct tests are ground truth."
disable-model-invocation: true
---

# duckdb: Join-Order Optimizer + ART Index Foundation

## Use this for
Use when building or porting an in-process query engine's planner core or its ordered index: dynamic-programming join enumeration over hyper-graphs (DPhyp), cost/cardinality estimation without deep statistics, index build/scan/constraint-check protocols, and byte-order-preserving key encoding. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/art-builder-stack-leaf-inlining.md` — sorted-array divide-and-conquer bulk build; adjacency-based uniqueness detection.
- `references/art-insert-chunk-rollback.md` — stop-at-first-conflict plus ordered compensating deletes for chunk atomicity.
- `references/art-iterator-lowerbound-gate-scan.md` — prefix-compare lower-bound snap, gate-depth mirroring, PAUSED/resume scan protocol.
- `references/art-key-encoding-null-escape.md` — order-preserving byte keys: ≤0x01 escaping, terminator, whole-key NULL semantics.
- `references/art-merge-buffer-id-remap.md` — remap deserialized buffer ids BEFORE allocator concatenation.
- `references/art-merger-orientation-invariants.md` — swap-normalized merge sides, extract-before-free, gate-aware duplicate rule.
- `references/art-operator-gate-delete-art.md` — delete-art shadow lookup distinguishing real duplicates from same-transaction re-inserts.
- `references/art-prefix-split-gate-status.md` — three-case prefix split whose returned GateStatus must decorate the replacement node.
- `references/art-sorted-parallel-build-merge.md` — chunk-local throwaway ARTs merged thread→global with uniform conflict mapping.
- `references/art-try-initialize-scan-predicate-ladder.md` — which WHERE shapes serve index scans; IS-NOT-DISTINCT-FROM-NULL refusal.
- `references/art-vacuum-allocator-threshold.md` — threshold-gated compaction preserving type+gate metadata across relocation.
- `references/block-manager-convert-persistent.md` — block manager convert persistent seam.
- `references/block-manager-registry.md` — block manager registry seam.
- `references/block-memory-lifecycle.md` — block memory lifecycle seam.
- `references/buffer-handle-raii.md` — buffer handle raii seam.
- `references/buffer-manager-allocator-bridge.md` — buffer manager allocator bridge seam.
- `references/buffer-manager-inmemory-warnings.md` — buffer manager inmemory warnings seam.
- `references/buffer-manager-pin-deadlock.md` — buffer manager pin deadlock seam.
- `references/buffer-manager-temp-directory-lifecycle.md` — buffer manager temp directory lifecycle seam.
- `references/buffer-manager-temp-file-offload.md` — buffer manager temp file offload seam.
- `references/buffer-manager-virtual-contract.md` — buffer manager virtual contract seam.
- `references/bufferpool-evict-blocks-entry.md` — bufferpool evict blocks entry seam.
- `references/bufferpool-eviction-node-lifecycle.md` — bufferpool eviction node lifecycle seam.
- `references/bufferpool-eviction-purge-cycle.md` — bufferpool eviction purge cycle seam.
- `references/bufferpool-eviction-queue-routing.md` — bufferpool eviction queue routing seam.
- `references/bufferpool-memory-usage-cache.md` — bufferpool memory usage cache seam.
- `references/bufferpool-purge-aged-blocks.md` — bufferpool purge aged blocks seam.
- `references/bufferpool-reservation-token.md` — bufferpool reservation token seam.
- `references/bufferpool-set-limit-rollback.md` — bufferpool set limit rollback seam.
- `references/bufferpool-temporary-memory-ladder.md` — bufferpool temporary memory ladder seam.
- `references/database-encryption-util-ladder.md` — database encryption util ladder seam.
- `references/database-extension-settings-replay.md` — database extension settings replay seam.
- `references/database-instance-init-order.md` — database instance init order seam.
- `references/database-storage-extension-attach.md` — database storage extension attach seam.
- `references/datachunk-cardinality-contract.md` — datachunk cardinality contract seam.
- `references/datachunk-type-copy-contention.md` — datachunk type copy contention seam.
- `references/denominator-subgraph-assembly.md` — per-edge create/extend/merge state machine producing one join denominator.
- `references/domain-estimate-reliability-tiers.md` — HLL/EXACT > MIN_MAX > heuristic merge rule for conflicting NDVs.
- `references/dphyp-pair-budget-approximate-fallback.md` — exact→cross-product-rerun→greedy ladder bounded by a 10k pair budget; original plan is always the final fallback.
- `references/equal-cost-right-cardinality-tiebreaker.md` — DP-table tiebreak on equal costs: prefer larger RIGHT input to keep LEFT orientation downstream.
- `references/fkpk-composite-join-pair-cap.md` — composite-equality FK/PK row-count cap with the ×8 plausibility gate.
- `references/left-join-input-cost-correction.md` — RHS-input surcharge that stops LEFT joins from looking free.
- `references/preserve-identifier-case-three-state.md` — preserve identifier case three state seam.
- `references/required-cross-product-activation-latch.md` — one-shot legalization of graph-connecting cross products plus enumerator cache reset.
- `references/task-execution-result-ladder.md` — task execution result ladder seam.
- `references/task-scheduler-idle-flush-loop.md` — task scheduler idle flush loop seam.
- `references/task-scheduler-pool-queues.md` — task scheduler pool queues seam.
- `references/task-scheduler-producer-token.md` — task scheduler producer token seam.
- `references/task-scheduler-thread-resize.md` — task scheduler thread resize seam.
- `references/vector-reinterpret-dictionary-identity.md` — vector reinterpret dictionary identity seam.
- `references/vector-serialization-roundtrip.md` — vector serialization roundtrip seam.
- `references/vector-tounified-format.md` — vector tounified format seam.

## Capsule map
- **Join-order planner kernel** — `dphyp-pair-budget-approximate-fallback`, `equal-cost-right-cardinality-tiebreaker`, `left-join-input-cost-correction`, `domain-estimate-reliability-tiers`, `fkpk-composite-join-pair-cap`, `denominator-subgraph-assembly`, `required-cross-product-activation-latch`: enumeration always terminates in a valid plan; costs are output-cardinality plus LEFT corrections; estimates come from tiered NDV merging, composite caps, and subgraph denominators.
- **Adaptive radix tree index** — `art-sorted-parallel-build-merge`, `art-key-encoding-null-escape`, `art-insert-chunk-rollback`, `art-try-initialize-scan-predicate-ladder`, `art-iterator-lowerbound-gate-scan`, `art-operator-gate-delete-art`, `art-merger-orientation-invariants`, `art-builder-stack-leaf-inlining`, `art-merge-buffer-id-remap`, `art-vacuum-allocator-threshold`, `art-prefix-split-gate-status`: conflict-detected merges at every tier, byte-comparable keys with NULL-as-empty-key, atomic chunk appends via compensation, gate-flagged nested row-id leaves threaded through scan/merge/vacuum/split.
- **Task scheduler** — `task-scheduler-pool-queues`: pool-per-type plus queue array where the REGULAR pool drains every queue and every enqueue signals. `task-scheduler-idle-flush-loop`: 0.5s timed wait then allocator flush then decay-delay idle marking. `task-execution-result-ladder`: FINISHED/ERROR reset, NOT_FINISHED re-enqueues through the task's own producer token with a fresh signal, BLOCKED deschedules. `task-scheduler-producer-token`: one producer identity across all queues with locked/requires-lock dequeue split. `task-scheduler-thread-resize`: positive total >= external validation, relaunch under thread_lock, forced best-effort shutdown in the destructor.
- **Buffer pool eviction** — `bufferpool-eviction-queue-routing`: BLOCK/EXTERNAL first, MANAGED write-back second, TINY last, front-is-coldest index arithmetic. `bufferpool-eviction-node-lifecycle`: weak_ptr + monotonic sequence numbers + has-live-entry flag give exactly-once dead-node counting including increment-before-bump ordering. `bufferpool-eviction-purge-cycle`: 4096-insert trigger, try-to-lock single purger, bulk dequeue with paired consumer/producer tokens. `bufferpool-memory-usage-cache`: 64 CPU-pinned cache slots folding into global atomics at a 32 KiB threshold with a TOTAL slot updated exactly once per call. `bufferpool-evict-blocks-entry`: reserve-first eviction with exact-AllocSize block recycling and object-cache fallback only after all queues fail. `bufferpool-set-limit-rollback`: trial evict under old limit, commit, re-evict, roll back on failure. `bufferpool-purge-aged-blocks`: monotonic-clock age sweep that unloads visited blocks and stops at the freshness frontier. `bufferpool-reservation-token`: deleted-copy RAII charge token whose move zeroes the source and whose destructor asserts zero. `bufferpool-temporary-memory-ladder`: five-arm reservation ladder ending in derivative-guided fair share only for operators bigger than memory.
- **Block memory & handles** — `block-memory-lifecycle`: VerifyMutex at each mutation, unsigned double-wrap for negative deltas, destructor repairs dead-node counts for expired live entries (TINY excepted). `block-manager-registry`: weak_ptr map keyed by block id where lock() decides liveness. `block-manager-convert-persistent`: register, optional THREAD_SAFE copy, write-before-convert, uncontended new-block lock for requeue. `buffer-handle-raii`: swap-based move-only pin delegating Unpin to the manager policy.
- **Buffer manager** — `buffer-manager-pin-deadlock`: never return a BufferHandle while holding the block lock; recheck after eviction. `buffer-manager-temp-file-offload`: grouped .tmp files for fixed blocks vs per-id .block files with plaintext size headers and single-owner counter updates. `buffer-manager-temp-directory-lifecycle`: lazy handle creation under mutex with a hard switch-after-use error. `buffer-manager-inmemory-warnings`: empty OOM postscript iff temp dir exists; NULL_IF_NOT_EXISTS stat races tolerated. `buffer-manager-virtual-contract`: capability queries answer false while machinery throws NotImplemented. `buffer-manager-allocator-bridge`: allocate evicts under ALLOCATOR tag then discards its reservation; free fabricates a charged reservation resized to zero.
- **Data chunks & vectors** — `datachunk-cardinality-contract`: optional_idx count derived from children; SetChildCardinality refuses non-flat/non-constant resize. `datachunk-type-copy-contention`: Initialize copies LogicalTypes to dodge ExtraTypeInfo atomic contention; caches must move with columns. `vector-tounified-format`: FSST/SEQUENCE/SHREDDED flatten first; physical_type set before buffer access. `vector-reinterpret-dictionary-identity`: entry id + global flag survive re-mint as one contract. `vector-serialization-roundtrip`: CODE_UNSEEN dictionary pruning gated by used*2<count with version-gated payloads.
- **Instance lifecycle** — `database-instance-init-order`: Configure, managers, settings replay, attach main, threads started last. `database-extension-settings-replay`: iterate a snapshot map, apply in one transaction, throw listing leftovers. `preserve-identifier-case-three-state`: legacy boolean cast wins over enum parse, NULL rejected, PRESERVE_CASE forced during ToString reparse. `database-encryption-util-ladder`: read-only paths autoload without installing; writes without a provider name the unsafe opt-in. `database-storage-extension-attach`: attach + create_transaction_manager both required for the modern path, else legacy constructor, else built-in duckdb.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question against project `ext-duckdb`. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Candidate seams for future passes live in `.pi/work/foundations-deep-farm/research.md` next-pass targets (relation_manager/query_graph extraction, statistics_propagator plane, node48 growth paths, storage checkpoint serialization).

## Provenance
duckdb (MIT), `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory project `ext-duckdb` (FULL mode, 115,679 nodes / 595,569 edges, head==base==working-tree HEAD 044a04a7, zero drift; parse_partial ×1140 dominated by benchmark SQL/data fixtures — none of the 14 cited .cpp/.hpp paths carry flags; 3 skipped tpch/tpcds generator headers uncited). First squeeze pass 1, 2026-08-24, data-engine deep lane.

## Full view (memory graph)
Revalidate `ext-duckdb` before porting: run `index_status --project ext-duckdb`, `check_index_coverage` (pass paths as stdin JSON), `search_graph`, `trace_path`, `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/duckdb`, branch `main`, mode FULL. Freshness at pin: BM25 search resolves planner symbols line-exact (`TryEmitPair`, `ComputeCost`) and ART symbols (`ARTMerger.MergeNodeAndPrefix`, `Leaf.MergeInlined`, `ARTBuilder.Build`). Coverage caveat: benchmark/data files are parse_partial BY DESIGN — prefer grep for anything under `benchmark/` or `data/`. SIMILAR_TO (15,557 edges) clusters the repeated node-type dispatch pattern across node4/16/48/256 implementations.

## Boundaries
Adopt the pure contracts: enumeration ladders and fallbacks, estimator tier/cap semantics, key encoding rules, gate-status lifecycle, merge/remap ordering, compensating-delete protocol. Adapt host-specific integrations: FixedSizeAllocator/block-manager plumbing, settings framework, sqllogic test harness. Omit product surface: extension ecosystem (parquet/json/icu/tpch generators), shell/Python/R clients, jemalloc/zstd vendored trees — none are ported by these capsules.
