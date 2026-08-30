---
name: graphiti-foundation
description: "Use when building agent memory over knowledge graphs: bi-temporal fact edges, arithmetic contradiction invalidation, hybrid-search resolution pipelines, and multi-driver graph abstractions."
disable-model-invocation: true
---
# Graphiti Foundation

## Use this for
Agent memory over a knowledge graph where facts are bi-temporal, contradictions invalidate via arithmetic, and retrieval is a named hybrid-search recipe behind one driver. Source and direct tests are ground truth; the capsules carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/bitemporal.md` — the four-clock edge model, resolution pipeline, contradiction arithmetic.
- `references/search.md` — hybrid composition, rerankers, empty-query short-circuit, filter scaffolding, cost-tier recipes.
- `references/nodes.md` — extraction batching, three-tier dedup with defensive LLM guardrails, summary flights, node taxonomy traps.
- `references/graphiti-orchestrator.md` — add_episode/bulk flow, saga summarization.
- `references/add-episode-contract.md` — the steerable ingestion signature (typed schemas, exclusions, edge_type_map, custom instructions).
- `references/driver.md` — the GraphDriver ABC (Cypher queries, sessions, transactions, node ops) across Neo4j/FalkorDB/Kuzu/Neptune.
- `references/edges.md` — the bi-temporal fact-edge model (save, get_by_uuid, embedding).
- `references/node-model-namespaces.md` — provider-matched deletes + namespace repositories.
- `references/search-rerankers.md` — RRF, MMR, node-distance, episode-mentions.
- `references/search-primitives.md` — fulltext/similarity/BFS per node/edge/episode/community with provider fallbacks.
- `references/falkordb-fulltext-builder.md` — fail-closed RediSearch query construction (empty-string refusals, never truncation).
- `references/dialect-query-dispatch.md` — one logical index name → four query grammars; FalkorDB cosine-distance rescaling invariant.
- `references/retrieval-for-update.md` — relevant nodes/edges + invalidation candidates.
- `references/bulk-dedup.md` — UnionFind canonicalization + combined extraction.
- `references/node-resolution-summaries.md` — LLM-confirmed merges + flight-batched summarization.
- `references/content-chunking.md` — density-gated chunking (token estimate, JSON/text split with overlap).
- `references/generic-client-structured-output.md` — OpenAI-compatible client: json_schema default / json_object prompt-injection fallback, fence stripping, empty-body guard.
- `references/llm-client.md` — provider-agnostic LLM client base (transient-error retry taxonomy, sentinel-idempotent preamble, input cleaning).
- `references/dedup.md` — MinHash + LSH fuzzy dedup with entropy gating.
- `references/attribute-capping.md` — cap string/list attributes against schema-description bleed.
- `references/community-detection.md` — label-propagation community clustering.
- `references/cross-encoder-embedder.md` — LLM-as-judge reranking via logprobs + embedding ABC.
- `references/prompt-library.md` — versioned prompts-as-code + group-id fan-out decorator.
- `references/tracing.md` — NoOp/OpenTelemetry spans behind one ABC.
- `references/telemetry-capture.md` — silent-by-design PostHog product telemetry beside (not merged with) OTel tracing.
- `references/embedder-dim-contract.md` — frozen embedding_dim; slice-vs-request-vs-passthrough strategies per provider.
- `references/to-prompt-json.md` — single serialization choke point for all prompt context (ensure_ascii=False by design).
- `references/record-parser-split.md` — per-dialect JSON pre-normalization → shared typed hydration; reserved-key pop list as schema boundary.
- `references/kuzu-edge-as-node.md` — relationships materialized as RelatesToNode_ nodes + twin edges when edge properties can't be indexed.
- `references/neptune-encoding-traps.md` — comma-join/split pairing + removeKeyFromMap ordering; documents the latent entity_edges delimiter bug.
- `references/llm-cache-sqlite.md` — SQLite+JSON response cache replacing pickle (CVE-driven); degrade-to-miss contract.
- `references/datetime-text-utils.md` — UTC normalization, sentence-boundary truncation.
- `references/mcp-queue-service.md` — per-group-id sequential episode queues (lazy workers, crash-recovery flag).
- `references/mcp-type-config.md` — config name+description → Pydantic type models (doc-only fallback feeds the LLM).
- `references/mcp-provider-factories.md` — provider routing factories; two-tier fatal/degraded failure policy.
- `references/mcp-yaml-config-source.md` — YAML settings source with ${VAR} expansion + precedence ladder.
- `references/combined-extraction.md` — single-call node+edge extraction; attribution derived from edges, orphans dropped.
- `references/validation-gates.md` — group_id/label regex guards + reserved entity-type field names.
- `references/server-tool-invariants.md` — wrapper contract: fail-fast before queues, recipe↔feature coupling, cascade deletes.
- `references/driver-composition-root.md` — capability-property ops accessors + feature-detect; single-`run()` Transaction interface.
- `references/openai-base-client.md` — OpenAI-family base: `'auto'` reasoning sentinel, dual response parsers, self-correcting retry.
- `references/token-usage-tracker.md` — thread-safe per-prompt token ledger with copy-on-read snapshots.
- `references/search-recipe-grammar.md` — per-family method/reranker matrices + `SearchResults.merge` parallel-list contract.
- `references/label-propagation-clustering.md` — weighted label-propagation community clustering with stability guard.
- `references/falkordb-driver.md` — datetime→ISO coercion, `(records, header, None)` result contract, idempotent-index swallow, close-drain ladder.
- `references/graph-operations-interface.md` — dual saga watermark (temporal vs ingestion), direction-limited edge reads.
- `references/neptune-dual-store.md` — scheme-branched composition root attaching AOSS as a sidecar store behind three driver-back-referenced ops classes.
- `references/neptune-aoss-search-fusion.md` — two-phase candidate-then-hydrate retrieval: score-carrying ids, pre-hydration thresholds, ORDER BY carried score in Cypher.
- `references/neptune-datetime-splicing.md` — temporal params without native binding: in-place ISO coercion + `$k`→`datetime($k)` query-text rewrite and its idempotence trap.
- `references/neptune-aoss-quirks.md` — latent-trap ledger: module-global template mutation, entity_edges comma-split corruption, un-awaited cleanup coroutine.
- `references/maintenance-dispatch-ladder.md` — capability-probe → NotImplementedError-fallback maintenance helpers; DESC-query + Python-reversed chronological contract.
- `references/gliner2-specialist-delegation.md` — one-response-model local NER specialist with full-fidelity delegate forwarding for everything else.
- `references/provider-client-contract.md` — cross-provider tool-forced JSON extraction, four-step max-token precedence, retry/refusal/safety error taxonomy.
- `references/edge-ce-shortlist-rrf-fusion.md` — cross-encoder shortlist = RRF fusion before ranking with a 2·limit cap (#1642); BM25 insertion order must never crowd out cosine/BFS hits.
- `references/node-attributes-preservation.md` — untyped attribute extraction must return prior attributes, not `{}`; overlay merge + validation-only discard keeps typed attributes alive.
- `references/edge-resolve-orchestration.md` — resolution orchestrator: exact-dedup fast path, per-pair override merge, duplicate-vs-invalidation exclusive candidate fan-out, strict zips.
- `references/edge-per-edge-resolution.md` — verbatim-fact short circuit, continuous LLM index space with offset mapping + range validation, identity-preserving reuse, two-sided expiry ladder.
- `references/edge-multi-episode-extraction.md` — multi-episode attribution via 0-based episode_indices: clamp-or-broadcast mapping, first-claimed-episode reference time, self-edge drop by resolved uuid.
- `references/edge-duplicate-prefilter.md` — subtract-before-write filter for IS_DUPLICATE_OF pairs across three provider grammars (Kuzu two-hop through RelatesToNode_).
- `references/chunking-message-boundaries.md` — message-atomic transcript chunking: JSON→speaker→line dispatch, oversized message = own chunk, whole-message overlap reseeded from the tail.
- `references/chunking-pair-covering.md` — greedy pair-covering set cover (Schönheim bound) with sampling fallback and guaranteed size-2 completion chunks.
- `references/saga-incremental-summarization.md` — dual watermarks: wall-clock cursor filters the fetch (backfill-safe), event-time cursor is consumer-facing and monotone.
- `references/episode-provenance-read.md` — provenance asymmetry: edges exact via entity_edges backpointers, nodes derived via MENTIONS traversal.
- `references/triplet-direct-write.md` — direct fact writes: resolve-or-create endpoints, merge-not-replace fields, uuid-collision mints a new edge.
- `references/episode-delete-cascade.md` — delete cascade guards: creation ownership (`episodes[0]`) + last-mention node GC + child-first order.
- `references/mcp-service-bootstrap.md` — boot-time failure policy: LLM/embedder degrade to warnings, cross-encoder stays fatal, connection errors become operator runbooks.
- `references/azure-openai-dual-api.md` — one Azure client over reasoning + chat APIs: model-prefix request split independent of response-shape parse dispatch.
- `references/mcp-response-typeddicts.md` — uniform tool envelopes: `message`+payload vs bare `{'error': ...}`, pre-serialized time strings at the wire boundary.
- `references/falkordb-group-id-routing.md` — per-group physical-graph routing: call-scoped executor clone or the default DB silently answers empty.
- `references/single-group-id-decorator-routing.md` — decorator owns partition routing INCLUDING N=1 (#1659): inject a cloned driver kwarg without reassigning shared state.
- `references/driver-ops-contract-layer.md` — typed ops ABC layer: executor-first + optional-tx signatures, None-means-unsupported capabilities, ignored batch_size trap, keyset pagination.
- `references/community-rebuild-choreography.md` — scoped wipe→cluster→pairwise-summarize rebuild + incremental mode-community attach; [] == None scoping asymmetry.
- `references/mcp-wire-embedding-strip.md` — two-layer embedding exclusion (declared-field exclude + free-form attributes substring sweep) keeps vectors off the MCP wire.
- `references/cache-key-mutation-ordering.md` — cache key hashes the POST-transformation message list; cleaning/schema/language injected before md5 or typed callers get schema-less cached text.
- `references/host-search-interface-hook.md` — SearchInterface: open BaseModel hook for hosts overriding single primitives vs the strict SearchOperations ABC for driver authors.
- `references/zep-graph-service-adapter.md` — REST adapter: per-request client lifecycle (close in finally), error-to-HTTP translation at the edge, asymmetric backend-switch strictness, warning-backed empty-group delete.
- `references/rest-ingest-fire-forget.md` — fire-and-forget ingest: closure-per-message 202 queue, single serial consumer, cancel-then-drain loss window vs the durable MCP queue.
- `references/rest-retrieval-wire-contract.md` — retrieval wire contract: INVERTED write/read chat templates (probe-falsified symmetry), UTC-forced datetime encoding incl. naive-input TZ shift, required-Optional center_node_uuid trap.
- `references/graphiticlients-bundle.md` — GraphitiClients typed bundle replacing five parallel params across the pipeline; arbitrary_types_allowed ABCs; model_construct test doubles.
- `references/error-taxonomy-raise-sites.md` — raise-site census over the flat GraphitiError hierarchy: which bulk fetches throw NotFound vs return [] silently, latent dead classes, message-before-super convention.
- `references/write-path-driver-rebinding.md` — add_episode may rebind self.driver/clients.driver ONLY under sequential ingestion; reads clone call-scoped (#1659); offline FakeDriver test pins both halves.
- `references/reranker-rank-contract.md` — one rank() ABC, three divergent implementations: sorted-same-length contract, strict=False vs strict=True zips, executor bridge for local models, synthetic 0.0 vs dropped passages.
- `references/groq-json-object-client.md` — minimal-provider counterexample: response_model accepted but never applied, non-user/system roles silently dropped, bare json.loads; what the base-class contract silently loses.
- `references/summary-budget-binding.md` — MAX_SUMMARY_CHARS binds LLM prompt prose AND code-side truncation to one runtime constant; hard slice vs sentence-aware enforcement styles are deliberate.
- `references/search-results-context-string.md` — closed per-section dict projections serialize typed SearchResults into one XML-tagged context string through to_prompt_json; 'Present'/'present' sentinel split is deliberate.

## Capsule map
- **Bi-temporal facts** — `bitemporal`, `edges`: valid_at/invalid_at/expired_at clocks, contradiction arithmetic, fact-edge lifecycle.
- **Retrieval** — `search`, `search-primitives`, `falkordb-fulltext-builder`, `dialect-query-dispatch`, `search-rerankers`, `edge-ce-shortlist-rrf-fusion`, `retrieval-for-update`, `search-recipe-grammar`, `reranker-rank-contract`, `search-results-context-string`: recipes, primitive matrix (kind × mode), fail-closed fulltext construction, per-dialect query/cosine dispatch, RRF/MMR/distance fusion, cross-encoder shortlist via RRF + 2·limit cap, update-driven candidate lookup, per-family method/reranker matrices + `SearchResults.merge` parallel-list contract, the rank() contract every CrossEncoderClient must keep (sorted-same-length; zip-strictness and empty-input divergence), closed-projection typed-results→LLM context string with deliberate sentinel split.
- **Ingestion & resolution** — `nodes`, `add-episode-contract`, `node-resolution-summaries`, `bulk-dedup`, `dedup`, `content-chunking`, `attribute-capping`, `node-attributes-preservation`, `combined-extraction`: steerable extraction, LLM-confirmed merges, union-find canonicalization, density-gated chunking, single-call extraction with edge-derived attribution, prior-preserving untyped attribute extraction (overlay merge + validation-only discard).
- **Edge resolution & maintenance** — `edge-resolve-orchestration`, `edge-per-edge-resolution`, `edge-multi-episode-extraction`, `edge-duplicate-prefilter`, `triplet-direct-write`, `episode-delete-cascade`, `episode-provenance-read`: candidate fan-out with exclusive duplicate/invalidation lists and strict zips, verbatim short circuit + continuous-index LLM mapping + two-sided expiry ladder, multi-episode attribution clamp-or-broadcast, provider-branched IS_DUPLICATE_OF pre-filter, direct triplet writes (merge-not-replace + collision guard), deletion cascade (creation ownership + last-mention GC), provenance reads with backpointer-exact / traversal-derived asymmetry.
- **Chunking & summarization** — `content-chunking`, `chunking-message-boundaries`, `chunking-pair-covering`, `saga-incremental-summarization`, `summary-budget-binding`: density gating, message-atomic chunking with whole-message overlap, pair-covering set cover for pairwise mining budgets, dual-watermark incremental saga roll-ups, one runtime constant binding prompt prose to enforcement truncation.
- **Driver dialects & storage encodings** — `record-parser-split`, `kuzu-edge-as-node`, `neptune-encoding-traps`, `driver-composition-root`, `falkordb-driver`, `graph-operations-interface`, `neptune-dual-store`, `neptune-aoss-search-fusion`, `neptune-datetime-splicing`, `neptune-aoss-quirks`, `maintenance-dispatch-ladder`: dialect JSON pre-normalization → shared typed hydration, edge-as-node modeling for non-indexable edge properties, native-type encode/decode pairings (incl. the latent Neptune entity_edges delimiter bug), capability-property ops accessors + feature-detect + single-`run()` Transaction, Falkor datetime coercion + `(records, header, None)` contract + idempotent-index swallow, dual saga watermark + direction-limited edge reads, Neptune dual-store composition + candidate-then-hydrate fusion + datetime splicing + latent-trap audit checklist, capability-probe fallback ladder for maintenance helpers.
- **LLM clients & caching** — `llm-client`, `generic-client-structured-output`, `llm-cache-sqlite`, `openai-base-client`, `token-usage-tracker`, `gliner2-specialist-delegation`, `provider-client-contract`, `azure-openai-dual-api`, `cache-key-mutation-ordering`, `groq-json-object-client`: transient-error retry taxonomy, json_schema/json_object output ladder, CVE-safe SQLite+JSON response cache, `'auto'` reasoning sentinel + dual response parsers + self-correcting retry, thread-safe per-prompt token ledger, one-operation local-NER specialist wrapper with full-fidelity delegation, cross-provider tool-forced JSON + max-token precedence + retry/refusal/safety taxonomy, Azure dual-API client (model-gated requests vs shape-gated parsing), post-transformation cache-key derivation ordering, the minimal-provider counterexample showing which guarantees a bare json_object subclass silently loses.
- **MCP server** — `mcp-queue-service`, `mcp-type-config`, `mcp-provider-factories`, `mcp-yaml-config-source`, `server-tool-invariants`, `mcp-service-bootstrap`, `mcp-response-typeddicts`, `mcp-wire-embedding-strip`: per-group ordered ingestion, config→typed-schema bridge, provider factories with fatal-reranker policy, YAML+env settings source, wrapper contract invariants, boot-time degrade-vs-fail component policy with operator-runbook connection errors, uniform response envelopes, two-layer embedding exclusion at the wire.
- **Partition routing** — `falkordb-group-id-routing`, `single-group-id-decorator-routing`, `write-path-driver-rebinding`: physically-partitioned backends route reads via call-scoped executor/driver clones (default-DB silent-empty trap), decorator-level N=1 interception + typed multi-group merge (#1659), and the write-side mirror: add_episode rebinds shared instance state legally only under the sequential-ingestion contract.
- **Driver ops contracts** — `driver-ops-contract-layer`, `host-search-interface-hook`: the 11-ABC typed operations layer (executor-first signatures, None-means-unsupported capability properties, ignored batch_size, keyset pagination) vs the open SearchInterface BaseModel hook for application-side primitive overrides.
- **Community lifecycle** — `community-detection`, `label-propagation-clustering`, `community-rebuild-choreography`: weighted label propagation w/ stability guard, scoped wipe→cluster→pairwise-summary rebuild choreography, incremental mode-community attach.
- **Infrastructure** — `graphiti-orchestrator`, `driver`, `node-model-namespaces`, `cross-encoder-embedder`, `embedder-dim-contract`, `prompt-library`, `to-prompt-json`, `tracing`, `telemetry-capture`, `datetime-text-utils`, `validation-gates`, `graphiticlients-bundle`, `error-taxonomy-raise-sites`: orchestration, driver ABCs, the five-client typed bundle, rerankers, embedding dimensionality contracts, prompts-as-code + serialization choke point, OTel spans, product telemetry, time/text utils, boundary validation guards, the error taxonomy as a raise-site census with throw-vs-empty bulk-fetch semantics.
- **REST service plane** — `zep-graph-service-adapter`, `rest-ingest-fire-forget`, `rest-retrieval-wire-contract`: per-request client lifecycle with edge-layer error-to-HTTP translation and backend-switch strictness asymmetry; closure-per-message 202 ingest queue with cancel-then-drain loss window (deliberate opposite of the durable MCP queue); retrieval wire contract with UTC-forced datetime encoding, the required-Optional DTO trap, and probe-falsified INVERTED write/read chat templates (shared-constant lesson).

## Extending the foundation
Add one references-fileshaped capsule per portable seam: one loader line, one grouped map entry, decisive source with an invariant, a direct-test probe, and a `search_graph` retrieval.

## Provenance
Indexed in Codebase Memory: canonical graph project **`graphiti`** at root `/mnt/hdd/utopia/inspo/graphiti`; confirm every claim against source — the graph is an index, not truth. CORRECTION (pass 10, 2026-08-25): earlier passes cited twin project `mnt-hdd-utopia-inspo-memory-graphiti` at `/mnt/hdd/utopia/inspo/memory/graphiti`; that project no longer exists and the repo is a real directory (not a symlink). list_projects shows exactly one graphiti project, ready at head==base==pin. Pass 8 depth re-entry (2026-08-24) at unchanged pin `main@993e081a` (zero drift, origin fetched 0 behind): 55 → 68 capsule-v2, all cited paths re-verified against source. Pass 9 depth re-entry (2026-08-24) at unchanged pin `main@993e081a` (zero drift): 68 → 75 capsule-v2 — partition-routing, ops-contract, community-lifecycle, wire-serialization, cache-key-ordering, host-hook planes; probes derived from live grep before writing; real-runner battery green at pin.
Pass 10 depth re-entry (2026-08-25) at unchanged pin `main@993e081a` (zero drift, head==base==origin/main): 75 → 79 capsule-v2 — REST service plane (ZepGraphiti adapter+lifecycle, fire-and-forget ingest queue, retrieval wire contract) + GraphitiClients bundle; runtime probes P1–P4 executed against real sources via repo venv (fastapi/pydantic_settings import shims disclosed); probe P2' FALSIFIED an initial symmetry claim → capsule documents the inverted-template finding instead.
Pass 11 depth re-entry (2026-08-25) at unchanged pin `main@993e081a` (zero drift, head==base==993e081a, FULL 4415/23443): 79 → 85 capsule-v2 — error taxonomy raise-site census (throw-vs-empty bulk-fetch split; latent GroupsNodesNotFoundError), write-path driver rebinding vs call-scoped read clones (#1659, offline FakeDriver test), reranker rank() contract across BGE/Gemini/OpenAI, Groq minimal-provider counterexample, MAX_SUMMARY_CHARS prompt↔enforcement binding, SearchResults→XML context projection. Probes re-executed this pass: pytest test_handle_multiple_group_ids.py (4), test_text_utils.py (11), test_gemini_reranker_client.py (17) all green + offline stubs P-E/P-F. License provenance sweep MIT→Apache-2.0 completed this pass (repo LICENSE/pyproject are Apache-2.0).

## Full view (memory graph)
Revalidate the canonical project **`graphiti`** before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Live at last verification (2026-08-25, pass 11): root `/mnt/hdd/utopia/inspo/graphiti` (real directory), branch `main` head==base==`993e081a6d7948a0d8851c12a5fbdbeb49fed862` (matches pin), FULL mode, **4,415 nodes / 23,443 edges**; parse_partial limited to Dockerfiles + pytest.ini files (none cited); skipped=0; generation_matches=true. The twin project `mnt-hdd-utopia-inspo-memory-graphiti` cited by passes ≤9 NO LONGER EXISTS in list_projects — short-name `graphiti` is the only and canonical project; cite it in all Retrieve blocks. Source and direct tests decide shipped claims.

## Boundaries
Adopt the bi-temporal edge model, contradiction arithmetic, search recipe matrix, resolution pipeline, and infrastructure ABCs; adapt driver dialects and embedding providers; choose the durability point deliberately per surface (durable MCP queue vs fire-and-forget REST 202); omit Graphiti-specific pipelines and prompts unless a target requires them.
