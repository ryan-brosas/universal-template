---
name: qdrant-foundation
description: "Use when porting or re-implementing filtered vector-search machinery: filterable HNSW builds, ACORN/graph dispatch decisions, cardinality-driven prefilter-vs-index planning, WAL durability, hybrid RRF fusion, prefetch-tree query planning, or flush-ordered post-optimize cleanup. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."

---
# Qdrant: vector-engine foundations

## Use this for
Use when porting or re-implementing filtered vector-search machinery: filterable HNSW builds, ACORN/graph dispatch decisions, cardinality-driven prefilter-vs-index planning, WAL durability, hybrid RRF fusion, prefetch-tree query planning, or flush-ordered post-optimize cleanup. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/hnsw-build-warmstart-parallelism.md` — why a parallel HNSW insert needs a single-threaded warm start and how deleted points are excluded.
- `references/payload-graph-percolation-heuristics.md` — when an extra payload-filtered HNSW graph pays for itself (percolation math).
- `references/acorn-selectivity-dispatch.md` — the selectivity estimate that routes a filtered query to ACORN vs plain HNSW.
- `references/graph-inline-vectors-dual-scorer.md` — graph-with-inline-vectors search: quantized link vectors + full base vectors, and every fallback condition.
- `references/quantization-oversample-rescore.md` — oversampled top-k and post-search rescoring contract for quantized segments.
- `references/cardinality-estimator-algebra.md` — must/should/min_should/must_not cardinality combination algebra and deleted-vector adjustment.
- `references/sparse-cardinality-plain-vs-inverted.md` — sparse engine dispatch on cardinality.max vs full_scan_threshold, plus batch-wide prefilter caching.
- `references/wal-segment-crc-chain.md` — WAL segment byte format, chained CRC32C, crash recovery, and truncate-zeroing.
- `references/wal-retention-prefix-truncate.md` — segment retirement, retention, prefix truncation, and open-recovery contiguity validation.
- `references/rrf-weighted-fusion.md` — weighted Reciprocal Rank Fusion over heterogeneous prefetch lists.
- `references/planned-query-prefetch-flattening.md` — flattening a nested prefetch tree into batched searches plus shard/collection rescore stages.
- `references/post-flush-action-ack-waterline.md` — running queued post-flush actions without ever letting the WAL acknowledge pass unflushed data.
- `references/discover-two-stage-entry.md` — bootstrapping Discover traversal via a Context-search warmup for its own entry points.
- `references/query-cost-model.md` — per-point similarity-comparison cost accounting across query types for rate limiting.
- `references/hnsw-links-residency.md` — cold/cached/pinned residency selection for HNSW links at open time.
- `references/operation-to-shard-fanout.md` — ByShard/ToAll operation envelope; clone-per-owner fan-out with resharding multi-shard tolerance.
- `references/chunked-two-phase-upsert.md` — 32-point chunked upsert: conditional-move updates first, new points into the smallest appendable segment.
- `references/point-version-gating-ladder.md` — holder `>=` skip vs segment strict-`>` ignore; success-only version advancement.
- `references/cross-segment-cow-move.md` — flush-dependency write-before-delete CoW move out of non-appendable/proxy segments via raw bytes.
- `references/segment-error-latch-recovery.md` — SegmentFailedState latch: newer ops fail fast until the same point/version retries successfully.
- `references/wal-update-worker-loop.md` — WAL-backed apply loop: flush-before-ack, success-only applied-seq waterline, detached deferred waits.
- `references/proxy-delete-buffering.md` — proxy rejects every point mutation except deletes, which buffer into a shared id→version map plus a local offset mask.
- `references/proxy-deleted-mask-finalize-window.md` — two-phase proxy construction: the deleted-mask snapshot must be taken under the holder write lock or racing writes ghost points out of KNN.
- `references/proxy-index-change-buffering.md` — payload-index ops journal per-field versioned intents (Create/Delete/DeleteIfIncompatible); nothing is built inside the proxy.
- `references/proxy-drain-propagate-ordering.md` — unproxy drain: index changes → vector-name intents → deletes under one upgradable-read lock; stale queued deletes tolerated.
- `references/vector-rename-intent-taint.md` — IntendedVector end-states with sticky supersedes_wrapped taint so delete+recreate cannot preserve stale vector storage.
- `references/stale-has-vector-redaction.md` — HasVector conditions on tainted names become always-false checkers; WithVector selectors drop tainted names before wrapped reads.

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
## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Qdrant (Apache-2.0), `master@74f3e85b9473c62560006c043e13737ce6b48412` ("Bump version to 1.19.0", head_sha == base_sha == origin/master → zero drift). Codebase Memory project `qdrant` (37,187 nodes / 230,815 edges, FULL mode, generation 2026-08-25T20:10:06Z) rooted at `/mnt/hdd/utopia/inspo/qdrant`. Pass-2 (2026-08-25) deepened ONE connected subsystem — the local shard update pipeline — adding 6 capsule-v2 refs: operation-to-shard-fanout, chunked-two-phase-upsert, point-version-gating-ladder, cross-segment-cow-move, segment-error-latch-recovery, wal-update-worker-loop. Pass-1 (15 capsules) was mined against the now-retired project name `ext-qdrant` at `/mnt/hdd/utopia/inspo/external/qdrant`, same commit 74f3e85b — its content claims remain valid at pin; legacy capsules' Retrieve calls still name `ext-qdrant` and are queued for migration (see work record NEXT-PASS TARGETS). parse_partial files are SQL/proto/asm/Dockerfile/.mmd/docs — none cited by either pass.

## Full view (memory graph)
Revalidate `qdrant` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root `/mnt/hdd/utopia/inspo/qdrant`, branch `master`, commit `74f3e85b`, mode FULL, 37,187 nodes / 230,815 edges; all 11 paths cited by pass-2 sources/tests returned coverage `no_recorded_issue` + `metadata_match`. All Probe anchors are repo-root-relative unless stated otherwise; counts were executed live against this pin. Source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: estimator algebra, RRF formula, WAL framing/CRC chaining, prefetch-tree flattening semantics, warm-start build ordering. Adapt host-specific integration: rayon pools, mmap backends, parking_lot locks, gRPC/API surface. Omit product behavior: GPU graph construction feature flag, distributed consensus/raft sharding, strict-mode API validation, OpenAPI tests.
