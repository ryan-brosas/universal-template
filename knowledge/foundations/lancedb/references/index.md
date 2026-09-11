<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# LanceDB: embedded vector database SDK foundation

## Use this for
Porting the lancedb Rust crate's query and table-maintenance machinery — the
layer between a fluent query builder (`Query`/`VectorQuery`) and Lance's dataset
scanner/index engine. Source of truth is `$REFERENCE_ROOT/external/lancedb`
at pin `main@1b950188` (v0.38.0-beta.5) with direct tests under each module.
Covers all four lane themes: filter-then-search planning (prefilter/postfilter,
top_k pre-offsetting), segment/LSM machinery (MemWAL shards, SSTable exclusion
watermarks), index structure selection (IvfPq/IvfHnsw dispatch ladder), and
hybrid sparse+dense fusion (rank→normalize→rerank choreography).

## Load the matching source dump
- `./hybrid-fusion-choreography.md` — what order do rank, normalize, rerank run in `execute_hybrid`, and what must both arms share?
- `./rrf-reranker-k60.md` — exact RRF score per row, duplicate-row handling, k=60 default.
- `./hybrid-score-normalization.md` — rank()/normalize_scores() edge behavior (empty, constant, near-equal).
- `./filter-composition-deferred-error.md` — repeated/mixed `.only_if()` filters AND-compose; where combination errors surface.
- `./lsm-read-routing.md` — use_lsm tri-state routing and why unsupported shapes must error, not fall back.
- `./sstable-exclusion-watermarks.md` — min-across-indexes retention gating for compacted generations.
- `./lsm-merge-insert-dispatch.md` — upsert-only LSM merge_insert, single-shard rule, atomic collect-then-put.
- `./shard-writer-cache-snapshot.md` — memtables-before-manifest capture order for consistent reads.
- `./lsm-overfetch-projection-restore.md` — 2× over-fetch to fill pages under PK dedup; dropping leaked PK columns.
- `./index-dispatch-ladder.md` — Index variant → Lance params derivation incl. Auto→IvfPq and 4-bit even-sub-vector bump.
- `./optimize-action-fanout.md` — All = compact→prune(7d)→index-optimize order; checkout mutability gate.
- `./topk-limit-offset-preoffset.md` — ANN candidate count must be limit+offset before scanner.limit trims.
- `./multi-vector-union-plan.md` — per-vector plans unioned with tagged `query_index`; List-column concat exception.
- `./stream-wrappers-batch-timeout.md` — MaxBatchLengthStream ceiling semantics; lazy-deadline TimeoutStream.
- `./vector-column-auto-detect.md` — unique-candidate-or-error vector column resolution with dimension filtering.

## Capsule map
- **Hybrid sparse+dense fusion** — `hybrid-fusion-choreography`: dual-arm row-id join → optional rank → normalize → rerank (default RRF) → slice → drop `_rowid`.
- **Hybrid sparse+dense fusion** — `rrf-reranker-k60`: `1/(i+k)` on 0-based positions summed across arms; first-occurrence dedup keeps vector-arm payload.
- **Hybrid sparse+dense fusion** — `hybrid-score-normalization`: `< 10e-5` closeness picks divisor=max but still normalizes; empty batch untouched.
- **Filter & projection planning** — `filter-composition-deferred-error`: `(a) AND (b)` string compose / expr.and() / mixed lowers expr→SQL; Substrait never composes; failure deferred via `filter_error`.
- **Filter & projection planning** — `topk-limit-offset-preoffset`: `top_k = limit + offset` fed to nearest(); offset applied by scanner.limit afterwards.
- **Filter & projection planning** — `vector-column-auto-detect`: zero candidates = dim-mismatch error; >1 = specify-column error.
- **MemWAL LSM plane** — `lsm-read-routing`: unset⇒LSM-iff-spec, Some(true)-requires-spec, Some(false)=base-only; unsupported shapes reject with `use_lsm(false)` guidance.
- **MemWAL LSM plane** — `sstable-exclusion-watermarks`: watermark = min(compaction, every relied-on index catch-up); missing entry pins 0.
- **MemWAL LSM plane** — `lsm-merge-insert-dispatch`: upsert-only shape enforced; whole input validated then ONE atomic ShardWriter::put; uuidv5 shard ids; validate_single_shard checks first row only when false.
- **MemWAL LSM plane** — `shard-writer-cache-snapshot`: memtable refs captured BEFORE manifest so mid-capture flushes lose no rows.
- **MemWAL LSM plane** — `lsm-overfetch-projection-restore`: over-fetch 2.0 keeps pages filled despite cross-generation dedup; restore_projection drops only unselected PK columns.
- **Index build & maintenance** — `index-dispatch-ladder`: Auto=IvfPq(L2); dtype predicates gate at param-build; case-insensitive nested field paths; even sub-vectors for 4-bit PQ.
- **Index build & maintenance** — `optimize-action-fanout`: ordered compact→prune→index-optimize; stats isolated per action; checked-out tables refuse everything.
- **Plan shape** — `multi-vector-union-plan`: N vectors ⇒ N sub-plans + literal query_index projections + UnionExec + repartition-to-one; List-typed target column concatenates instead.
- **Execution plumbing** — `stream-wrappers-batch-timeout`: max_batch_length is a ceiling not an equality; timeout deadline armed on first poll.

## Extending the foundation
Add one source-confirmed capsule: loader line, map entry, decisive source,
invariant, direct-test probe, and `search_graph` retrieval against project
`ext-lancedb`. Keep the canonical pinned commit; volume follows the seam.

## Provenance
LanceDB, Apache-2.0, `main@1b950188c3dc73383707fbab1ce85d4679787e07`
(v0.38.0-beta.5). Codebase Memory project `ext-lancedb` (13,496 nodes / 86,569
edges, FULL mode, generation 2026-08-23T09:41:29Z; head_sha == base_sha ==
recorded pin — no drift, no stale twin). All 15 cited paths returned
`no_recorded_issue` + `metadata_match` from check_index_coverage; parse_partial
files exist only under nodejs/ (not cited). Pass 1 (2026-08-24): ~7k lines read
whole-file across query.rs (2689L), rerankers.rs+rrf.rs, query/hybrid.rs,
table/query.rs+query/lsm.rs, table/merge/lsm.rs (1309L), optimize.rs,
create_index.rs, utils/mod.rs.

## Full view (memory graph)
Graph retrieval works well for Rust symbols in this repo (BM25 over qualified
names). Entry queries: `execute_hybrid`, `RRFReranker`, `create_plan use_lsm`,
`exclusion_watermarks`, `make_index_params`, `create_multi_vector_plan`,
`MaxBatchLengthStream`. SIMILAR_TO edges connect the Node/Python reranker twins
of the Rust seam mined here. Work record:
`.pi/work/foundations-deep-farm/research.md`; learning state mirrored in
OpenViking `llm-repo-learning`.

## Boundaries
Adopt the behavioral contracts (fusion ordering, RRF formula, routing truth
tables, retention watermarks, atomic write shapes, param derivations); adapt
DataFusion exec nodes, Arrow kernels, and tokio stream mechanics to host
equivalents; omit remote/server (`remote/table.rs` 11.3k lines), namespace
pushdown, embeddings registry, dataloader, and materialized-view planes — those
are separate porting questions, recorded as next-pass targets.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`filter-composition-deferred-error.md`](./filter-composition-deferred-error.md)
- [`hybrid-fusion-choreography.md`](./hybrid-fusion-choreography.md)
- [`hybrid-score-normalization.md`](./hybrid-score-normalization.md)
- [`index-dispatch-ladder.md`](./index-dispatch-ladder.md)
- [`lsm-merge-insert-dispatch.md`](./lsm-merge-insert-dispatch.md)
- [`lsm-overfetch-projection-restore.md`](./lsm-overfetch-projection-restore.md)
- [`lsm-read-routing.md`](./lsm-read-routing.md)
- [`multi-vector-union-plan.md`](./multi-vector-union-plan.md)
- [`optimize-action-fanout.md`](./optimize-action-fanout.md)
- [`rrf-reranker-k60.md`](./rrf-reranker-k60.md)
- [`shard-writer-cache-snapshot.md`](./shard-writer-cache-snapshot.md)
- [`sstable-exclusion-watermarks.md`](./sstable-exclusion-watermarks.md)
- [`stream-wrappers-batch-timeout.md`](./stream-wrappers-batch-timeout.md)
- [`topk-limit-offset-preoffset.md`](./topk-limit-offset-preoffset.md)
- [`vector-column-auto-detect.md`](./vector-column-auto-detect.md)
