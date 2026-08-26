---
name: txtai-foundation
description: Use when porting txtai vector-engine mechanics — hybrid dense+sparse fusion, IVFSparse/FAISS/sqlite-vec index builds, BM25 term scoring, filter-then-search planning, or embeddings lifecycle. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.
---

# txtai: Embeddings Engine Foundation

## Use this for
Use when porting txtai's vector-database engine contracts: hybrid fusion strategy dispatch, sparse IVF cluster lifecycle, common-terms two-phase BM25, sqlite-vec typed DDL, vector encode/quantize pipelines, the transform/stream document spine, multi-store delete choreography, config shortcut expansion, index persistence layout, or the text-to-SQL parser plane that turns user strings into clause dicts. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/hybrid-fusion-dispatch.md` — which fusion math runs for a given sparse scoring config, and why candidate lists over-fetch 10x.
- `references/filter-planner-scan.md` — SQL-filter + similar() clause planning: candidate sizing, uid/qid join, bind resolution order.
- `references/ivfsparse-cluster-lifecycle.md` — build → prune → re-aggregate → max-summary centroids; offset-stable appends; tombstone deletes.
- `references/terms-common-two-phase.md` — term-at-a-time scoring with >cutoff terms merged only into top candidates.
- `references/bm25-tfidf-stat-lifecycle.md` — counter accumulation then stat freeze; docfreq-vs-wordfreq; OOV→avgidf.
- `references/sparse-vector-normalize.md` — neural-sparse encode thread, double-normalization guard, linear vs bayes calibration.
- `references/faiss-component-derivation.md` — auto components/cells/nprobe ladders, positional ids, binary quantization path.
- `references/sqlitevec-typed-ddl.md` — quantization-typed vec0 virtual tables, 1−distance projection, in_transaction copy guard.
- `references/numpy-zero-delete.md` — zero-fill tombstones keeping positional ids stable; hamming scoring table.
- `references/vector-encode-pipeline.md` — truncate→normalize→quantize ordering, memmap spool, checkpoint recovery identity.
- `references/transform-stream-spine.md` — one-pass stream fanning to all datastores; yielded-count offsets; delete-once upserts.
- `references/multi-index-delete-choreography.md` — resolve uids once, fan positional indexids everywhere, return uids.
- `references/config-shortcut-expansion.md` — keyword/sparse/hybrid/dense booleans compiled into component configs; default-model gate.
- `references/index-persistence-layout.md` — directory contract, offset completeness marker, JSON/pickle dual format.
- `references/explain-token-attribution.md` — leave-one-out token importance in one batched similarity pass.
- `references/subindexes-shared-cache.md` — named subindex spaces sharing one model cache with independent id numbering.
- `references/bb25-bayes-normalization.md` — positive-candidate sigmoid calibration making scores log-odds-fusable.
- `references/ann-factory-settings.md` — backend table, dotted custom resolution, presence-aware setting lookup.
- `references/rdbms-session-lifecycle.md` — lazy single-connection content-store sessions; session-scope temp tables/functions.
- `references/document-insert-triage.md` — dict/list/object insert semantics; store-filtered JSON; silent object drop without encoder.
- `references/temp-table-similarity-join.md` — batch/scores TEMP tables injecting vector results into user SQL; score averaging.
- `references/sql-column-resolution-ladder.md` — column→expression ladder, dialect hooks, JOIN heuristic, SQLError wrapping.
- `references/reindex-copy-swap-renumber.md` — dense correlated-count indexid renumbering with decode-on-stream copy-swap.
- `references/object-encoder-plane.md` — objects config factory, format-keeping image codec, fail-closed ALLOW_PICKLE gate.
- `references/database-factory-content-backends.md` — content backend dispatch + DuckDB override-only dialect patches.
- `references/sql-dispatch-gate.md` — substring gate deciding SQL vs natural-language; non-SQL → single similar clause.
- `references/sql-tokenize-clause-slicing.md` — shlex lexer with operator punctuation; positional clause slicing, two-token `group by`/`order by`.
- `references/similar-placeholder-protocol.md` — `similar(...)` → quote-stripped params + `__SIMILAR__<n>` marker replaced at query time.
- `references/bracket-json-path-expression.md` — `[a[0].b]` raw JSON paths as one token; quote doubling; unterminated → SQLError.
- `references/select-alias-suppression.md` — alias registry suppressing resolution across clauses; SQLError for stray commas / trailing AS.
- `references/aggregate-shard-merge.md` — post-hoc aggregate fold over sharded result lists by result-column name prefix.

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
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
txtai (Apache-2.0), `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (v9.13.0); Codebase Memory project `txtai` (FULL mode, 4,577 nodes / 24,033 edges, generated 2026-08-25T20:20:01Z, zero parse_partial, zero skipped; all cited paths no_recorded_issue + metadata_match). Passes 1–N of the pre-ledger era were mined against the since-deleted twin project `ext-txtai` (root inspo/external/txtai) at the same commit a10667a — content remains valid, but re-pin all new Retrieves to project `txtai`. Ledger pass 1 (FAC-275) added the content-database plane capsules; ledger pass 2 (same pin) deep-mined the text-to-SQL parser plane (`src/python/txtai/database/sql/**`) and reconciled the reference count to 31 (the pass-1 records undercounted `database-factory-content-backends`).

## Full view (memory graph)
Revalidate `txtai` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root (/mnt/hdd/utopia/inspo/txtai), branch master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a, mode full, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure engine contracts (fusion math, cluster lifecycle, score calibration, id choreography). Adapt backend-specific constants (cells formulas, cutoff, scale factors) to your workload. Omit product transport surfaces (api/ FastAPI routers, app/, console/, cloud/, workflow orchestration, pipeline/model wrappers) and graph-network analytics — separate seams, not engine primitives.
