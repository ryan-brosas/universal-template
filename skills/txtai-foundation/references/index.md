<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# txtai: Embeddings Engine Foundation

## Use this for
Use when porting txtai's vector-database engine contracts: hybrid fusion strategy dispatch, sparse IVF cluster lifecycle, common-terms two-phase BM25, sqlite-vec typed DDL, vector encode/quantize pipelines, the transform/stream document spine, multi-store delete choreography, config shortcut expansion, index persistence layout, or the text-to-SQL parser plane that turns user strings into clause dicts. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./hybrid-fusion-dispatch.md` — which fusion math runs for a given sparse scoring config, and why candidate lists over-fetch 10x.
- `./filter-planner-scan.md` — SQL-filter + similar() clause planning: candidate sizing, uid/qid join, bind resolution order.
- `./ivfsparse-cluster-lifecycle.md` — build → prune → re-aggregate → max-summary centroids; offset-stable appends; tombstone deletes.
- `./terms-common-two-phase.md` — term-at-a-time scoring with >cutoff terms merged only into top candidates.
- `./bm25-tfidf-stat-lifecycle.md` — counter accumulation then stat freeze; docfreq-vs-wordfreq; OOV→avgidf.
- `./sparse-vector-normalize.md` — neural-sparse encode thread, double-normalization guard, linear vs bayes calibration.
- `./faiss-component-derivation.md` — auto components/cells/nprobe ladders, positional ids, binary quantization path.
- `./sqlitevec-typed-ddl.md` — quantization-typed vec0 virtual tables, 1−distance projection, in_transaction copy guard.
- `./numpy-zero-delete.md` — zero-fill tombstones keeping positional ids stable; hamming scoring table.
- `./vector-encode-pipeline.md` — truncate→normalize→quantize ordering, memmap spool, checkpoint recovery identity.
- `./transform-stream-spine.md` — one-pass stream fanning to all datastores; yielded-count offsets; delete-once upserts.
- `./multi-index-delete-choreography.md` — resolve uids once, fan positional indexids everywhere, return uids.
- `./config-shortcut-expansion.md` — keyword/sparse/hybrid/dense booleans compiled into component configs; default-model gate.
- `./index-persistence-layout.md` — directory contract, offset completeness marker, JSON/pickle dual format.
- `./explain-token-attribution.md` — leave-one-out token importance in one batched similarity pass.
- `./subindexes-shared-cache.md` — named subindex spaces sharing one model cache with independent id numbering.
- `./bb25-bayes-normalization.md` — positive-candidate sigmoid calibration making scores log-odds-fusable.
- `./ann-factory-settings.md` — backend table, dotted custom resolution, presence-aware setting lookup.
- `./rdbms-session-lifecycle.md` — lazy single-connection content-store sessions; session-scope temp tables/functions.
- `./document-insert-triage.md` — dict/list/object insert semantics; store-filtered JSON; silent object drop without encoder.
- `./temp-table-similarity-join.md` — batch/scores TEMP tables injecting vector results into user SQL; score averaging.
- `./sql-column-resolution-ladder.md` — column→expression ladder, dialect hooks, JOIN heuristic, SQLError wrapping.
- `./reindex-copy-swap-renumber.md` — dense correlated-count indexid renumbering with decode-on-stream copy-swap.
- `./object-encoder-plane.md` — objects config factory, format-keeping image codec, fail-closed ALLOW_PICKLE gate.
- `./database-factory-content-backends.md` — content backend dispatch + DuckDB override-only dialect patches.
- `./sql-dispatch-gate.md` — substring gate deciding SQL vs natural-language; non-SQL → single similar clause.
- `./sql-tokenize-clause-slicing.md` — shlex lexer with operator punctuation; positional clause slicing, two-token `group by`/`order by`.
- `./similar-placeholder-protocol.md` — `similar(...)` → quote-stripped params + `__SIMILAR__<n>` marker replaced at query time.
- `./bracket-json-path-expression.md` — `[a[0].b]` raw JSON paths as one token; quote doubling; unterminated → SQLError.
- `./select-alias-suppression.md` — alias registry suppressing resolution across clauses; SQLError for stray commas / trailing AS.
- `./aggregate-shard-merge.md` — post-hoc aggregate fold over sharded result lists by result-column name prefix.

## Capsule map
- **Hybrid search & fusion** — `hybrid-fusion-dispatch`: bayes→LogOdds / normalized→convex / raw→RRF dispatch keyed on scoring flags; `[w, 1-w]` weight split; limit×10 over-fetch.
- **Query planning** — `filter-planner-scan`: Scan groups similar() clauses per subindex, sizes candidates (multitoken where ⇒ 10x), joins results via global uid→qid sort.
- **Sparse ANN indexes** — `ivfsparse-cluster-lifecycle`: kmeans→snap-to-point→prune(39)→re-aggregate→block-max centroids; append by offset; delete = tombstone list.
- **Keyword scoring** — `terms-common-two-phase`: ≤10% docs scored directly, common terms merged into limit×5 candidates, recompute-on-empty fallback; `bm25-tfidf-stat-lifecycle`: frozen stats, k1=1.2/b=0.75, avgscore anchor.
- **Sparse vectors** — `sparse-vector-normalize`: Queue(5)+encoder thread+EOS drain; normalize unless model self-normalizes; bb25 alias ladder.
- **Dense ANN backends** — `faiss-component-derivation` (IDMap,Flat/SQ{q}, IVF cells=min(4√n,n/39), nprobe=cells//16); `sqlitevec-typed-ddl` (BIT/INT8/FLOAT32 DDL + iterdump copy guard); `numpy-zero-delete` (zero-row tombstones, non-zero count).
- **Vector computation** — `vector-encode-pipeline`: truncate→normalize→quantize order IS semantics; uuid5 checkpoint identity; recovery-file double-crash safety.
- **Indexing spine** — `transform-stream-spine`: Stream autoid normalization + Transform yielded-offset fan-out + UPSERT delete-once set; `multi-index-delete-choreography`: uid→indexid resolve once, positional fan-out.
- **Lifecycle & config** — `config-shortcut-expansion` (hybrid⇒dense flip; keyword blocks default model), `index-persistence-layout` (offset marker = completeness), `subindexes-shared-cache`, `ann-factory-settings` (`name in backend` presence check beats .get-default).
- **Introspection** — `explain-token-attribution`; `bb25-bayes-normalization` (median-centered logits, zero-stays-zero).
- **Content database plane** (`src/python/txtai/database/**`) — `rdbms-session-lifecycle` (lazy init, one connection, external thread lock, temp tables die with session); `document-insert-triage` (dict→JSON store / list→token join / object→encoder-or-silent-drop; indexid advances only on saved sections); `temp-table-similarity-join` (per-clause batch keys, clear-on-batch-0, sum/len score averaging); `sql-column-resolution-ladder` (alias→expression→prefix→bare→json_extract ladder hides all dialect syntax; parser-side alias/`:bind` gate + configure-time snippet pre-parse); `reindex-copy-swap-renumber` (correlated-count dense renumbering; dynamic-dispatch edge invisible to call graphs); `object-encoder-plane` (True/messagepack/pickle/dotted factory; ALLOW_PICKLE fail-closed); `database-factory-content-backends` (content normalize + write-back; DuckDB quirks patched only in overrides).
- **Text-to-SQL parser plane** (`src/python/txtai/database/sql/**`) — `sql-dispatch-gate` (`select `+` from txtai` substring test; non-SQL → `{"similar": [[q]]}`); `sql-tokenize-clause-slicing` (punctuation-as-tokens shlex; first-position clause map; slice to min of later clauses); `similar-placeholder-protocol` (`__SIMILAR__<n>` append-order markers → temp-table IN-clause at query time — pairs with `temp-table-similarity-join`); `bracket-json-path-expression` (nested-bracket JSON paths, `''` doubling); `select-alias-suppression` (normalized alias registry blocks resolution in every later clause); `aggregate-shard-merge` (name-prefix folds count/sum/total/max/min/avg; reverse-order stable sort; empty-shard guard).

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
txtai (Apache-2.0), `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (v9.13.0); Codebase Memory project `txtai` (FULL mode, 4,577 nodes / 24,033 edges, generated 2026-08-25T20:20:01Z, zero parse_partial, zero skipped; all cited paths no_recorded_issue + metadata_match). Passes 1–N of the pre-ledger era were mined against the since-deleted twin project `ext-txtai` (root inspo/external/txtai) at the same commit a10667a — content remains valid, but re-pin all new Retrieves to project `txtai`. Ledger pass 1 (FAC-275) added the content-database plane capsules; ledger pass 2 (same pin) deep-mined the text-to-SQL parser plane (`src/python/txtai/database/sql/**`) and reconciled the reference count to 31 (the pass-1 records undercounted `database-factory-content-backends`).

## Full view (memory graph)
Revalidate `txtai` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root (/mnt/hdd/utopia/inspo/txtai), branch master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a, mode full, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure engine contracts (fusion math, cluster lifecycle, score calibration, id choreography). Adapt backend-specific constants (cells formulas, cutoff, scale factors) to your workload. Omit product transport surfaces (api/ FastAPI routers, app/, console/, cloud/, workflow orchestration, pipeline/model wrappers) and graph-network analytics — separate seams, not engine primitives.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`aggregate-shard-merge.md`](./aggregate-shard-merge.md)
- [`ann-factory-settings.md`](./ann-factory-settings.md)
- [`bb25-bayes-normalization.md`](./bb25-bayes-normalization.md)
- [`bm25-tfidf-stat-lifecycle.md`](./bm25-tfidf-stat-lifecycle.md)
- [`bracket-json-path-expression.md`](./bracket-json-path-expression.md)
- [`config-shortcut-expansion.md`](./config-shortcut-expansion.md)
- [`database-factory-content-backends.md`](./database-factory-content-backends.md)
- [`document-insert-triage.md`](./document-insert-triage.md)
- [`explain-token-attribution.md`](./explain-token-attribution.md)
- [`faiss-component-derivation.md`](./faiss-component-derivation.md)
- [`filter-planner-scan.md`](./filter-planner-scan.md)
- [`hybrid-fusion-dispatch.md`](./hybrid-fusion-dispatch.md)
- [`index-persistence-layout.md`](./index-persistence-layout.md)
- [`ivfsparse-cluster-lifecycle.md`](./ivfsparse-cluster-lifecycle.md)
- [`multi-index-delete-choreography.md`](./multi-index-delete-choreography.md)
- [`numpy-zero-delete.md`](./numpy-zero-delete.md)
- [`object-encoder-plane.md`](./object-encoder-plane.md)
- [`rdbms-session-lifecycle.md`](./rdbms-session-lifecycle.md)
- [`reindex-copy-swap-renumber.md`](./reindex-copy-swap-renumber.md)
- [`select-alias-suppression.md`](./select-alias-suppression.md)
- [`similar-placeholder-protocol.md`](./similar-placeholder-protocol.md)
- [`sparse-vector-normalize.md`](./sparse-vector-normalize.md)
- [`sql-column-resolution-ladder.md`](./sql-column-resolution-ladder.md)
- [`sql-dispatch-gate.md`](./sql-dispatch-gate.md)
- [`sql-tokenize-clause-slicing.md`](./sql-tokenize-clause-slicing.md)
- [`sqlitevec-typed-ddl.md`](./sqlitevec-typed-ddl.md)
- [`subindexes-shared-cache.md`](./subindexes-shared-cache.md)
- [`temp-table-similarity-join.md`](./temp-table-similarity-join.md)
- [`terms-common-two-phase.md`](./terms-common-two-phase.md)
- [`transform-stream-spine.md`](./transform-stream-spine.md)
- [`vector-encode-pipeline.md`](./vector-encode-pipeline.md)
