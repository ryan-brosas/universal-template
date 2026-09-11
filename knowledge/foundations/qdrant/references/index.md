<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Qdrant: vector-engine foundations

## Use this for
Use when porting or re-implementing filtered vector-search machinery: filterable HNSW builds, ACORN/graph dispatch decisions, cardinality-driven prefilter-vs-index planning, WAL durability, hybrid RRF fusion, prefetch-tree query planning, or flush-ordered post-optimize cleanup. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./hnsw-build-warmstart-parallelism.md` — why a parallel HNSW insert needs a single-threaded warm start and how deleted points are excluded.
- `./payload-graph-percolation-heuristics.md` — when an extra payload-filtered HNSW graph pays for itself (percolation math).
- `./acorn-selectivity-dispatch.md` — the selectivity estimate that routes a filtered query to ACORN vs plain HNSW.
- `./graph-inline-vectors-dual-scorer.md` — graph-with-inline-vectors search: quantized link vectors + full base vectors, and every fallback condition.
- `./quantization-oversample-rescore.md` — oversampled top-k and post-search rescoring contract for quantized segments.
- `./cardinality-estimator-algebra.md` — must/should/min_should/must_not cardinality combination algebra and deleted-vector adjustment.
- `./sparse-cardinality-plain-vs-inverted.md` — sparse engine dispatch on cardinality.max vs full_scan_threshold, plus batch-wide prefilter caching.
- `./wal-segment-crc-chain.md` — WAL segment byte format, chained CRC32C, crash recovery, and truncate-zeroing.
- `./wal-retention-prefix-truncate.md` — segment retirement, retention, prefix truncation, and open-recovery contiguity validation.
- `./rrf-weighted-fusion.md` — weighted Reciprocal Rank Fusion over heterogeneous prefetch lists.
- `./planned-query-prefetch-flattening.md` — flattening a nested prefetch tree into batched searches plus shard/collection rescore stages.
- `./post-flush-action-ack-waterline.md` — running queued post-flush actions without ever letting the WAL acknowledge pass unflushed data.
- `./discover-two-stage-entry.md` — bootstrapping Discover traversal via a Context-search warmup for its own entry points.
- `./query-cost-model.md` — per-point similarity-comparison cost accounting across query types for rate limiting.
- `./hnsw-links-residency.md` — cold/cached/pinned residency selection for HNSW links at open time.
- `./operation-to-shard-fanout.md` — ByShard/ToAll operation envelope; clone-per-owner fan-out with resharding multi-shard tolerance.
- `./chunked-two-phase-upsert.md` — 32-point chunked upsert: conditional-move updates first, new points into the smallest appendable segment.
- `./point-version-gating-ladder.md` — holder `>=` skip vs segment strict-`>` ignore; success-only version advancement.
- `./cross-segment-cow-move.md` — flush-dependency write-before-delete CoW move out of non-appendable/proxy segments via raw bytes.
- `./segment-error-latch-recovery.md` — SegmentFailedState latch: newer ops fail fast until the same point/version retries successfully.
- `./wal-update-worker-loop.md` — WAL-backed apply loop: flush-before-ack, success-only applied-seq waterline, detached deferred waits.
- `./proxy-delete-buffering.md` — proxy rejects every point mutation except deletes, which buffer into a shared id→version map plus a local offset mask.
- `./proxy-deleted-mask-finalize-window.md` — two-phase proxy construction: the deleted-mask snapshot must be taken under the holder write lock or racing writes ghost points out of KNN.
- `./proxy-index-change-buffering.md` — payload-index ops journal per-field versioned intents (Create/Delete/DeleteIfIncompatible); nothing is built inside the proxy.
- `./proxy-drain-propagate-ordering.md` — unproxy drain: index changes → vector-name intents → deletes under one upgradable-read lock; stale queued deletes tolerated.
- `./vector-rename-intent-taint.md` — IntendedVector end-states with sticky supersedes_wrapped taint so delete+recreate cannot preserve stale vector storage.
- `./stale-has-vector-redaction.md` — HasVector conditions on tainted names become always-false checkers; WithVector selectors drop tainted names before wrapped reads.
- `./pre-wal-filter-resolution.md` — filter/condition-resolving update ops are rewritten to id-based form under a queue-drain fence before the WAL, so replay hits the same point set.
- `./conditional-upsert-update-modes.md` — Upsert/InsertOnly/UpdateOnly keep/drop table judged against live segment state by one retention function shared by apply and pre-WAL resolution.
- `./sync-points-range-replace.md` — range sync as diff-before-write: delete absent ids, skip byte-identical points (no version bump), upsert changed+new.
- `./wal-replay-load-from-wal.md` — restart replay window algebra: synchronous-by-default, worker-routed tail only under prevent_unoptimized, clamped against truncation and queue capacity.
- `./optimizer-proxy-install-freeze.md` — two-phase proxy install: proxies built unlocked, frozen+finalized under one write lock; temp COW registered in the manifest before any write can reach it.
- `./optimizer-build-bake-changes.md` — merge builds from frozen sources and bakes mid-build deletes/index changes; a post-freeze live-schema read tells a deleted vector from a concurrent create.
- `./optimizer-finish-swap-postflush-drop.md` — fast critical section: ordered buffer replay, swap_new, deferred dedup, manifest-before-retire, and the WAL ack pin re-expressed as a post-flush drop action.
- `./optimizer-cancel-rollback-orphan-cleanup.md` — failed optimization restores originals on every error; the built segment is deleted only on cancellation; in-process cleanup is explicitly not crash-safe.
- `./deferred-points-exclusion-dedup.md` — filtered updates skip points whose newest copy is deferred; optimizer dedup is the single component that removes the stale visible copies.
- `./optimizer-disk-fit-preflight.md` — compaction disk gate: 2× occupied vs physical free space only (quota-blind by design), fail-open on any unmeasurable stat.
- `./merge-optimizer-greedy-batching.md` — ascending greedy merge batching under the size threshold with a held first pair, so every plan provably reduces the segment count.
- `./optimized-segment-config-derivation.md` — threshold-on-largest-name output config: HNSW+quantization iff indexed or deferred, placement ladder, persist-only-explicit-fields.
- `./optimization-cpu-budget-scheduling.md` — IO-permit admission with half-desired minimums, CPU taken in-build, deduped budget waiter, cleanup-tick force-run, round-scoped failure latch.

## Capsule map
- **Filtered HNSW build** — `hnsw-build-warmstart-parallelism`: first N inserts single-threaded to avoid disconnected components; deleted points excluded at iterator level; old graphs healed+reused not rebuilt.
- **Payload subgraphs** — `payload-graph-percolation-heuristics`: per-field extra graphs only for blocks above 1/K×4 cardinality, skipped when main-graph connectivity already suffices at the 2/K sampling point.
- **ACORN dispatch** — `acorn-selectivity-dispatch`: estimated matched-points/available ≤ max_selectivity switches algorithm enum before any scoring work.
- **Graph-with-vectors** — `graph-inline-vectors-dual-scorer`: quantized vectors ride the graph links, full vectors score the final top; falls back through four independent conditions.
- **Quantized search** — `quantization-oversample-rescore`: search ef = max(ef, ceil(oversampling×top)); optional exact-vector rescore then truncate to top.
- **Estimator** — `cardinality-estimator-algebra`: min/exp/max bounds per clause; must = product of probabilities, should = complement rule, must_not = inversion; one unindexed should branch voids primary clauses.
- **Sparse dispatch** — `sparse-cardinality-plain-vs-inverted`: filtered sparse search picks plain iteration under full_scan_threshold using cardinality.max; prefiltered id set computed once per batch.
- **WAL format** — `wal-segment-crc-chain`: mmap'd "wal"v0 segments, u64 len header, padded entries, CRC32C chained via bit-reversed seed; torn tail detected by CRC==0 sentinel.
- **WAL lifecycle** — `wal-retention-prefix-truncate`: append→retire→closed-N rename pipeline; recovery rebuilds contiguous index ranges and closes stranded written-open segments; prefix_truncate keeps ≥1 closed segment.
- **Hybrid fusion** — `rrf-weighted-fusion`: score = Σ w-normalized 1/(pos+k); input scores discarded; weight scales position compression, validated against response count.
- **Query planning** — `planned-query-prefetch-flattening`: recursion flattens ShardPrefetch trees into indexed searches/scrolls; Fusion can never be a leaf; MMR splits into shard nearest-rescore + collection MMR stage.
- **Optimizer cleanup** — `post-flush-action-ack-waterline`: ready_at-ordered action drain gated by persisted-version waterline capped by failed ops; ack pins hold the WAL acknowledge until files match memory.
- **Discover warmup** — `discover-two-stage-entry`: Context search over the same filter seeds exactly DISCOVERY_ENTRY_POINT_COUNT=10 custom entry points before the pairs-based traversal.
- **Cost model** — `query-cost-model`: search cost = sum of per-vector similarity costs over the query's flat vector set; only Nearest is distance-scored.
- **Link residency** — `hnsw-links-residency`: memory placement resolves config → deprecated on_disk fallback → low-memory downgrade clamp at OPEN time; builds always write on-disk format.
- **Shard fan-out** — `operation-to-shard-fanout`: point ops split via hash ring into ByShard buckets (cloned into EVERY owner — two during resharding), collection-wide ops ride ToAll; empty ring panics, never silently drops.
- **Upsert routing** — `chunked-two-phase-upsert`: 32-id chunks bound lock hold; phase A updates existing points in their segments, phase B inserts never-found ids into the smallest appendable segment; empty batches bump the persisted-version waterline for WAL ack.
- **Version gating** — `point-version-gating-ladder`: holder skips `version >= op_num`; segment ignores only strictly older (`>`), letting same-op multi-step writes proceed; versions advance only after success; unknown points always apply.
- **CoW move** — `cross-segment-cow-move`: proxy/non-appendable sources move via aloha random write + flush dependency (dst durable before src delete), deferred-aware raw retrieval, fused upsert, source deleted only when the copy isn't deferred.
- **Error latch** — `segment-error-latch-recovery`: failed write stores (version, point_id) and rejects all newer ops until the same point retries clean, which clears the latch.
- **Apply loop** — `wal-update-worker-loop`: single worker applies WAL ops under the update lock; explicit WAL flush before apply when clients wait; applied-seq waterline advances only on success; deferred-point waits detach per client.
- **Proxy mutation strike + delete buffering** — `proxy-delete-buffering`: how does a segment that must not accept writes still serve deletes during optimization.
- **Unsynced proxy finalize window** — `proxy-deleted-mask-finalize-window`: when must a wrapper's deleted-mask snapshot be taken so a racing write can't ghost points out of KNN.
- **Propagate-to-wrapped drain** — `proxy-drain-propagate-ordering`: in what order and under which lock does a proxy replay its buffers into the frozen segment.
- **Proxy index-change intent buffering** — `proxy-index-change-buffering`: how are payload-index schema changes journaled on a segment that builds nothing.
- **Stale HasVector read redaction** — `stale-has-vector-redaction`: how do queries naming a deleted/renamed vector match nothing instead of reading wrapped stale bytes.
- **Vector-rename intent taint** — `vector-rename-intent-taint`: how do you record "delete v then create v with a new schema" so the optimizer cannot keep stale storage.
- **Pre-WAL filter resolution** — `pre-wal-filter-resolution`: how does a delete-by-filter or conditional upsert replay against the same point set after a restart.
- **Conditional upsert modes** — `conditional-upsert-update-modes`: which points of a conditional insert survive, decided once and reused by both apply and resolution.
- **Sync range replacement** — `sync-points-range-replace`: how does "replace this id range with this set" avoid rewriting unchanged points and stay replay-safe without submit-time resolution.
- **WAL replay at load** — `wal-replay-load-from-wal`: which WAL entries re-apply synchronously before reads are served, which route to the worker, and how stale waterlines/truncation keep the window valid.
- **Optimizer proxy install** — `optimizer-proxy-install-freeze`: how does an optimizer freeze its input segments for a merge while writes keep landing and the deleted-mask race window closes exactly once.
- **Optimizer build bake** — `optimizer-build-bake-changes`: how are mid-build deletes and index changes folded into the new segment, and how is a deleted vector told apart from a concurrent CreateVectorName.
- **Optimizer finish swap** — `optimizer-finish-swap-postflush-drop`: in what order are proxy buffers replayed and segments swapped, and why must source files survive until a flush proves the optimization durable.
- **Optimizer cancel rollback** — `optimizer-cancel-rollback-orphan-cleanup`: how does a failed optimization restore the original segments, and when is it safe to delete the half-built segment.
- **Deferred exclusion dedup** — `deferred-points-exclusion-dedup`: when a point's newest copy is invisible, how do filtered updates avoid acting on a stale copy, and who eventually removes it.
- **Optimizer disk-fit preflight** — `optimizer-disk-fit-preflight`: how does compaction check for room without deadlocking a quota-full or unmeasurable disk.
- **Merge candidate batching** — `merge-optimizer-greedy-batching`: how are merge batches chosen so each stays under the size threshold and the plan always reduces the segment count.
- **Output config derivation** — `optimized-segment-config-derivation`: what makes a merged segment indexed/mmap/plain, and why deferred points force an index below the threshold.
- **Optimization budget scheduling** — `optimization-cpu-budget-scheduling`: how much resource each admitted optimization gets, and how the dispatcher wakes itself when resources free.
## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Qdrant (Apache-2.0), `master@74f3e85b9473c62560006c043e13737ce6b48412` ("Bump version to 1.19.0", head_sha == base_sha == origin/master → zero drift). Codebase Memory project `qdrant` (37,187 nodes / 230,815 edges, FULL mode, generation 2026-08-25T20:10:06Z) rooted at `$REFERENCE_ROOT/qdrant`. Pass-2 (2026-08-25) deepened ONE connected subsystem — the local shard update pipeline — adding 6 capsule-v2 refs: operation-to-shard-fanout, chunked-two-phase-upsert, point-version-gating-ladder, cross-segment-cow-move, segment-error-latch-recovery, wal-update-worker-loop. Pass-3 (2026-08-26) mined the local optimization-time proxy plane (`lib/shard/src/proxy_segment/*`) into 6 more: proxy-delete-buffering, proxy-deleted-mask-finalize-window, proxy-index-change-buffering, proxy-drain-propagate-ordering, vector-rename-intent-taint, stale-has-vector-redaction. Pass-4 (2026-08-27) mined the WAL replay-determinism plane into 4 more: pre-wal-filter-resolution, conditional-upsert-update-modes, sync-points-range-replace, wal-replay-load-from-wal. Pass-5 (2026-08-27) mined the optimizer-side proxy lifecycle (`lib/shard/src/optimize.rs`) into 5 more: optimizer-proxy-install-freeze, optimizer-build-bake-changes, optimizer-finish-swap-postflush-drop, optimizer-cancel-rollback-orphan-cleanup, deferred-points-exclusion-dedup. Pass-6 (2026-08-27) mined the optimization admission & dispatch plane (disk-fit preflight, planner/merge batching, output config derivation, CPU/IO budget scheduling) into 4 more: optimizer-disk-fit-preflight, merge-optimizer-greedy-batching, optimized-segment-config-derivation, optimization-cpu-budget-scheduling. Pass-1 (15 capsules) was mined against the now-retired project name `ext-qdrant` at `$REFERENCE_ROOT/external/qdrant`, same commit 74f3e85b — its content claims remain valid at pin; in pass-4 every legacy Retrieve was re-executed against the live project `qdrant` and all 31 capsules now cite it. parse_partial files are SQL/proto/asm/Dockerfile/.mmd/docs — none cited by any pass.

## Full view (memory graph)
Revalidate `qdrant` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root `$REFERENCE_ROOT/qdrant`, branch `master`, commit `74f3e85b`, mode FULL, 37,187 nodes / 230,815 edges; every source/test path cited by passes 2–5 returned coverage `no_recorded_issue` + `metadata_match`. All Probe anchors are repo-root-relative unless stated otherwise; counts were executed live against this pin. Source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: estimator algebra, RRF formula, WAL framing/CRC chaining, prefetch-tree flattening semantics, warm-start build ordering. Adapt host-specific integration: rayon pools, mmap backends, parking_lot locks, gRPC/API surface. Omit product behavior: GPU graph construction feature flag, distributed consensus/raft sharding, strict-mode API validation, OpenAPI tests.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`acorn-selectivity-dispatch.md`](./acorn-selectivity-dispatch.md)
- [`cardinality-estimator-algebra.md`](./cardinality-estimator-algebra.md)
- [`chunked-two-phase-upsert.md`](./chunked-two-phase-upsert.md)
- [`conditional-upsert-update-modes.md`](./conditional-upsert-update-modes.md)
- [`cross-segment-cow-move.md`](./cross-segment-cow-move.md)
- [`deferred-points-exclusion-dedup.md`](./deferred-points-exclusion-dedup.md)
- [`discover-two-stage-entry.md`](./discover-two-stage-entry.md)
- [`graph-inline-vectors-dual-scorer.md`](./graph-inline-vectors-dual-scorer.md)
- [`hnsw-build-warmstart-parallelism.md`](./hnsw-build-warmstart-parallelism.md)
- [`hnsw-links-residency.md`](./hnsw-links-residency.md)
- [`merge-optimizer-greedy-batching.md`](./merge-optimizer-greedy-batching.md)
- [`operation-to-shard-fanout.md`](./operation-to-shard-fanout.md)
- [`optimization-cpu-budget-scheduling.md`](./optimization-cpu-budget-scheduling.md)
- [`optimized-segment-config-derivation.md`](./optimized-segment-config-derivation.md)
- [`optimizer-build-bake-changes.md`](./optimizer-build-bake-changes.md)
- [`optimizer-cancel-rollback-orphan-cleanup.md`](./optimizer-cancel-rollback-orphan-cleanup.md)
- [`optimizer-disk-fit-preflight.md`](./optimizer-disk-fit-preflight.md)
- [`optimizer-finish-swap-postflush-drop.md`](./optimizer-finish-swap-postflush-drop.md)
- [`optimizer-proxy-install-freeze.md`](./optimizer-proxy-install-freeze.md)
- [`payload-graph-percolation-heuristics.md`](./payload-graph-percolation-heuristics.md)
- [`planned-query-prefetch-flattening.md`](./planned-query-prefetch-flattening.md)
- [`point-version-gating-ladder.md`](./point-version-gating-ladder.md)
- [`post-flush-action-ack-waterline.md`](./post-flush-action-ack-waterline.md)
- [`pre-wal-filter-resolution.md`](./pre-wal-filter-resolution.md)
- [`proxy-delete-buffering.md`](./proxy-delete-buffering.md)
- [`proxy-deleted-mask-finalize-window.md`](./proxy-deleted-mask-finalize-window.md)
- [`proxy-drain-propagate-ordering.md`](./proxy-drain-propagate-ordering.md)
- [`proxy-index-change-buffering.md`](./proxy-index-change-buffering.md)
- [`quantization-oversample-rescore.md`](./quantization-oversample-rescore.md)
- [`query-cost-model.md`](./query-cost-model.md)
- [`rrf-weighted-fusion.md`](./rrf-weighted-fusion.md)
- [`segment-error-latch-recovery.md`](./segment-error-latch-recovery.md)
- [`sparse-cardinality-plain-vs-inverted.md`](./sparse-cardinality-plain-vs-inverted.md)
- [`stale-has-vector-redaction.md`](./stale-has-vector-redaction.md)
- [`sync-points-range-replace.md`](./sync-points-range-replace.md)
- [`vector-rename-intent-taint.md`](./vector-rename-intent-taint.md)
- [`wal-replay-load-from-wal.md`](./wal-replay-load-from-wal.md)
- [`wal-retention-prefix-truncate.md`](./wal-retention-prefix-truncate.md)
- [`wal-segment-crc-chain.md`](./wal-segment-crc-chain.md)
- [`wal-update-worker-loop.md`](./wal-update-worker-loop.md)
