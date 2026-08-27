---
name: ragflow-foundation
description: "Use when porting ragflow's RAG retrieval engine — hybrid search orchestration, citation attach, ingestion task kernel, resumable GraphRAG indexing pipeline, query-side KG retrieval with Go twin."
---

# ragflow: Retrieval & Ingestion Foundation

## Use this for
Use when porting RAG retrieval pipelines — per-backend hybrid fusion weights, empty-result retry ladders, vectorless rerank over ES-style stores, page-aligned rerank windows, inline `[ID:n]` citation attachment, weighted full-text query building for CJK+English, or a Redis-queue document-ingestion worker with cooperative cancellation — and when porting LLM knowledge-graph indexing: three-tier crash-resume durability, phase retry ladders with cancel passthrough, gleaning extraction loops, concurrency-safe node merges, gated entity resolution, deterministic Leiden communities, and insert-then-prune report replacement — and the GraphRAG query side: LLM query rewrite with JSON repair, three-channel entity/relation candidate fusion ranked by sim×pagerank, community-report attach mirrored in a tested Go twin, no-LLM NER extractor dispatch, and build-before-delete graph persistence feeding stored n-hop enrichment. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/fusion-weight-per-backend.md` — which weights reach each store's fusion expression and why ES is pinned to "0.001,1".
- `references/empty-retrieval-retry-ladder.md` — the single ordered retry that relaxes lexical matching while tightening vector similarity.
- `references/es-vectorless-rerank.md` — second-pass ids-filtered KNN scoring so chunk vectors never leave the engine.
- `references/rerank-window-pagination.md` — candidate window MUST be a multiple of page_size or deep pages silently drop.
- `references/citation-threshold-decay.md` — decaying absolute threshold × relative max bar attaching ≤4 citations per sentence.
- `references/query-boost-grammar.md` — two-branch (EN/ZH) boosted query grammar with lexer-safe escaping.
- `references/stale-chunk-prune-safety-net.md` — post-search existence re-check filtering chunks of deleted docs before rerank.
- `references/tag-feature-pagerank-boost.md` — add-after-blend tag cosine ×10 + PageRank; GaussDB double-add trap.
- `references/task-mode-dispatch.md` — one consumer, five task types, drain-then-consume, exactly-once ack.
- `references/progress-cancel-latch.md` — persist-then-raise cancellation checkpoints and partial-chunk cleanup.
- `references/thread-pool-exec-contextvars.md` — why every blocking call crosses threads via ctx.run on a per-call executor.
- `references/toc-parent-expansion.md` — mom_id child→parent synthesis and LLM-ranked TOC additive boosts.
- `references/graphrag-resume-tiers.md` — doc-store subgraphs + content-addressed Redis checkpoints + KB-scoped phase markers; merge clears markers.
- `references/graphrag-retry-ladder.md` — coro-factory retries with per-phase timeouts, capped backoff, cancel passthrough, clamp-to-default config.
- `references/graphrag-gleaning-extraction.md` — CONTINUE/LOOP gleaning with forced single-token probe, cached chat wrapper, error-budget breaker.
- `references/graphrag-node-merge-concurrency.md` — snapshot-before-mutate fold of duplicate nodes; GraphChange bookkeeping; serialized merges.
- `references/entity-resolution-pipeline.md` — similarity-gated candidates → batched checkpointed LLM verdicts → component merge.
- `references/leiden-stable-communities.md` — canonical input ordering + fixed seed = reproducible partitions.
- `references/community-report-recovery.md` — membership-keyed replay, brace-repair JSON ladder, typed schema gate, drop-not-fail.
- `references/insert-then-prune-replacement.md` — deterministic ids + insert-before-prune keeps the old complete set on crash.
- `references/kg-query-three-channel-fusion.md` — question → entity/relation channels → sim×pagerank ranking → one token-budgeted pseudo-chunk inserted first.
- `references/kg-query-rewrite-json-repair.md` — type-pool-hinted LLM keyword extraction with two-tier JSON repair; failure downgrades to the raw question.
- `references/kg-community-report-go-twin.md` — community reports by entity membership + weight order, mirrored byte-for-byte in the tested Go service.
- `references/ner-extractor-dispatch.md` — config dispatch fail-to-light; NER path skips chunk batching; spaCy keywords + co-occurrence edges, zero LLM extraction.
- `references/set-graph-build-before-delete.md` — build all chunks (graph/subgraphs/embeddings) before any delete; batch embed pre-warm; bounded edge-delete retries.
- `references/nhop-weight-cross-layer-contract.md` — stored n-hop paths+weights feed distance-decayed edge credit; absent/empty/malformed degrade to [].

## Capsule map
- **Hybrid fusion** — `fusion-weight-per-backend`: term/vector weights are `%g` complements in a string; Infinity user-tunable, GaussDB inline, ES hardcoded near-vector-only because rescoring happens client-side.
- **Recall safety** — `empty-retrieval-retry-ladder`: total==0 → doc_id filter short-circuit else min_match 0.3→0.1 + similarity 0.1→0.17, once.
- **Scoring** — `es-vectorless-rerank`: KNN-only probe filtered by candidate ids with similarity 0.0; missing scores default 0.0 in merge.
- **Pagination** — `rerank-window-pagination`: ceil(64/ps)·ps window bounded by top; block index = offset//window, slice begin = offset%window.
- **Grounding** — `citation-threshold-decay`: thr 0.63 ×0.8 decay while zero cites; cite set = {sim > 0.99·max} capped 4; dim-mismatch zero-fill guard.
- **Query building** — `query-boost-grammar`: EN term^w + bigram ^2max(w); ZH OR-groups with synonym ^0.2/^0.7 folds and ("s m")~2 proximity; keywords cap 32.
- **Consistency** — `stale-chunk-prune-safety-net`: one batched doc-exists check; rebuild ids/fields/highlights together; documented fallback-not-mechanism.
- **Ranking features** — `tag-feature-pagerank-boost`: pagerank excluded from cosine denominators, added after blend; server-fused engines skip local tags.
- **Ingestion** — `task-mode-dispatch`: memory → canvas-dataflow → dataflow → raptor → graphrag → mindmap → skill → standard chunking; kg_limiter around graph tasks.
- **Lifecycle** — `progress-cancel-latch`: Redis `{id}-cancel`; progress write precedes TaskCanceledException; finally deletes partial chunks; terminal ack unconditional.
- **Concurrency** — `thread-pool-exec-contextvars`: contextvars.copy_context + ctx.run inside fresh ThreadPoolExecutor per call (Py3.13 reuse deadlock note).
- **Structure-aware retrieval** — `toc-parent-expansion`: children pop-partition by mom_id with warn-and-fallback; TOC similarity increments for existing chunks.

### GraphRAG indexing pipeline (added pass 2)
- **Durability** — `graphrag-resume-tiers`: per-doc subgraph chunks, sha256-canonical-JSON Redis checkpoints (SSCAN index, 7d TTL, MULTI-atomic), KB-scoped phase markers; any successful merge clears markers.
- **Retries** — `graphrag-retry-ladder`: fresh coro per attempt under `asyncio.wait_for`; cancel exceptions never retried; config clamps to DEFAULT not to bound.
- **Extraction** — `graphrag-gleaning-extraction`: ≤2 gleanings; LOOP probe logit-biases Y/N max_tokens=1 and is skipped on the final glean; `GRAPHRAG_MAX_ERRORS` (3) breaker; timeout in `_async_chat` is non-transient.
- **Merging** — `graphrag-node-merge-concurrency`: snapshot `list(graph.neighbors(...))`, track redirected neighbors so duplicate edges sum weights, serialize merges behind a lock; pinned by regression tests.
- **Resolution** — `entity-resolution-pipeline`: digit-2gram veto → Levenshtein ≤ len//2 (EN) / char-set ≥0.8 (CJK); 100-pair batches ×5 concurrent with content-addressed checkpoint replay; fail-forward timeouts.
- **Communities** — `leiden-stable-communities`: sorted nodes + canonical undirected edge order + seed 0xDEADBEEF before hierarchical_leiden.
- **Reports** — `community-report-recovery`: checkpoint key embeds sorted membership; JSON brace-repair then typed schema gate; <2-entity communities skipped.
- **Replacement** — `insert-then-prune-replacement`: deterministic `(kb_id,title)` chunk ids; snapshot old ids → insert new → delete exactly `{old−new}`; snapshot failure falls back to legacy delete-all.

### GraphRAG query-side retrieval + extractor selection (added pass 3)
- **KG ranking** — `kg-query-three-channel-fusion`: dense-keyword entities, type-recall entities (no sim floor), dense relations; n-hop edge credit `sim/(2+i)`; final score `sim × pagerank`; overflow item dropped at token budget; one pseudo-chunk `insert(0)` when non-empty.
- **Query rewrite** — `kg-query-rewrite-json-repair`: minirag prompt seeded with the KB's entity-type pool; json_repair → echo-strip+brace-rebuild ladder; any failure ⇒ keywords=[raw question].
- **Communities** — `kg-community-report-go-twin`: reports filtered by top-entity membership, ordered weight_flt desc, default top-1; Go twin (`internal/service/graph/search.go`) mirrors filter/order/parse with an active 30+-test file.
- **Extractor dispatch** — `ner-extractor-dispatch`: method general/light/ner with fail-to-light default; NER bypasses chunk merging (sentence context preserved); MGranRAG keyword stacking + LinearRAG co-occurrence edges, LLM only for downstream summary.
- **Graph persistence** — `set-graph-build-before-delete`: all chunks built (incl. regenerated per-doc subgraphs) before old rows are deleted; embed-cache batch pre-warm collapses 17k round-trips; removed-edge deletes retry 3× exponential backoff under the limiter.
- **n-hop contract** — `nhop-weight-cross-layer-contract`: `n_hop_with_weight` JSON + `rank_flt` written per entity chunk (regression-tested); read side tolerates absent fields and empty-string Infinity defaults.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
ragflow (Apache-2.0), `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`. Pass 1 (2025-08-24) mined retrieval + task-executor seams against Codebase Memory project `ext-ragflow` (root `/mnt/hdd/utopia/inspo/external/ragflow`). Pass 2 re-gated on project `ragflow` — first-run full index of the canonical checkout `/mnt/hdd/utopia/inspo/ragflow`, same HEAD, 105,292 nodes / 623,264 edges, skipped=0; edge delta vs pass-1 record is indexer drift at identical HEAD. Pass 3 (this pass) deepened from pass-2 NEXT-PASS TARGETS on the same pin: GraphRAG query-side retrieval (`search.py`, `query_analyze_prompt.py`, Go twin `internal/service/graph/search{,_test}.go`), NER extractor-selection seam, and the `utils.py` storage plane. Upstream origin/main remains ahead of pin (fetched, not merged); checkout is read-only in the mining lane, so diff-first past-pin mining stays BLOCKED and remains the top NEXT-PASS TARGET.

## Full view (memory graph)
Revalidate `ragflow` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Recorded through pass 3: root above, branch main, commit `9ea83b7a`, FULL, ready, 105,292 nodes / 623,264 edges. `check_index_coverage` over every path cited by passes 2–3 (checkpoints/phase_markers/entity_resolution/general index+extractor; search.py, query_analyze_prompt.py, ner/graph_extractor.py, utils.py, internal/service/graph/search.go + search_test.go, agent/tools/retrieval.py, test/unit_test/rag/graphrag/test_graphrag_utils.py) returned no_recorded_issue + metadata_match, generation_matches=true. Direct tests decide shipped claims: pass-2 tests (`test_checkpoints.py`, `test_phase_markers.py`, `test_merge_graph_nodes.py`, `test_entity_resolution.py`) plus pass-3 tests (`internal/service/graph/search_test.go` — request builders, chunk parsers, n-hop name dedup, mock-engine integration, dense-expr column naming — and `test_graphrag_utils.py::TestNNeighbor` / `::TestGraphNodeToChunk`) are ACTIVE at the pin. Coverage caveats: `test_checkpoint_resume.py` is entirely commented out (zero executed tests); `_run_with_retry`, gleaning loops, leiden.py, community_reports_extractor, insert-then-prune ordering, `KGSearch.retrieval`, `query_rewrite`, the NER dispatch/extraction path, and `set_graph` ordering have no dedicated unit test at this pin — those claims are source-read-confirmed only. Test execution under a repo venv remains an infrastructure block carried from pass 2.

## Boundaries
Adopt pure ranking/fusion/pagination/citation contracts and the cooperative-cancel checkpoint shape; adapt backend switches (`settings.DOC_ENGINE_*` flags), boost constants, thresholds, and the metadata-store existence check to your host; omit product transport (doc store connectors under `common/doc_store/`, Go engine internals under `internal/engine/`, deepdoc parsers, web UI, sandbox agent, helm/docker packaging) — they are integration surfaces, not portable kernels. GraphRAG boundaries: adopt the resume/retry/merge/community contracts and the query-side fusion/ranking/persistence contracts including the Go twin's field vocabulary; adapt prompt texts (Microsoft-copyrighted in `general/graph_prompt.py`, LightRAG-derived in `light/graph_prompt.py`; `query_analyze_prompt.py` minirag examples carry upstream few-shot text) and Redis/doc-store specifics; omit the spaCy model dependency if your host lacks it (`ner/*` degrades to the light extractor via fail-to-light dispatch) and omit `ner/dep_relation_extractor.py` — its call sites are commented out at this pin. The advanced-RAG harness callers of `kg_retriever` (`rag/advanced_rag/**`) are a separate subsystem not yet mined.
