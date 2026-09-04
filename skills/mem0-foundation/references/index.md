<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Mem0 Foundation

## Use this for
Agent memory that adds and extracts facts on write and serves scoped, reranked retrieval on read — over pluggable vector backends with SQLite history. Source and direct tests are the ground truth; references carry decisive excerpts and retrieval.

## Load the matching source dump
- `./pipeline.md` — the V3 phased add pipeline: extract, add, update, delete on write.
- `./scoping.md` — identity-stripping metadata templates, deliberate add-vs-search asymmetry, escaped scope keys.
- `./search.md` — reject-don't-default validation, operator filter language, per-backend normalization.
- `./vector-store-base.md` — the VectorStoreBase ABC (create/insert/search/delete/list + keyword/search_batch).
- `./sqlite-storage.md` — SQLiteManager history/messages storage, idempotent schema migration, thread-locked.
- `./entity-store.md` — entity dedup (exact + semantic 0.95) and linked_memory_ids.
- `./v3-phased-add.md` — V3 phase-by-phase write path: integer-ID fence, hash dedup, batch persist w/ per-row fallback.
- `./hybrid-scoring.md` — semantic+BM25+entity fusion with adaptive divisor; threshold gates semantic FIRST.
- `./entity-boost-ranking.md` — query entities → linked-memory boosts: max-aggregate, quadratic popularity damping.
- `./update-ladder.md` — payload deep-copy merge, immutable scope keys, created_at preservation, entity repair on text change.
- `./delete-all-pagination.md` — re-list-until-empty loop, repeated-batch terminator, async bulk entity clear.
- `./expiration-read-filter.md` — TTL as read-time predicate; fail-open parsing; over-fetch to refill.
- `./sensitive-config-redaction.md` — runtime allowlist > exact deny > suffix deny for telemetry-safe config clones.
- `./entity-id-coercion.md` — single-chokepoint str-coercion/trim/whitespace validation for scope ids.
- `./backend-list-normalization.md` — structural unwrap of wrapped vs flat list() results across backends.
- `./qdrant-filter-translation.md` — universal operators → native conditions; $or/$not dual-key dedup trap; range/match mixing refusal.
- `./bm25-write-path.md` — sparse BM25 materialized at insert; slot detection; stale-on-payload-only-update tradeoff.
- `./telemetry-sampling-singleton.md` — before_send sampling, self-describing rates, md5 id encoding, one client per process.
- `./factory-provider-resolution.md` — lazy load_class registries; introspection-gated base→provider config conversion.
- `./reranker-contract.md` — one-method rerank contract with double-layered fail-open degradation.
- `./llm-response-salvage.md` — fence/think stripping → brace-slice fallback → fact-shape normalization; raise on transport only.
- `./session-scope-key.md` — %-escape-first, key-sorted composite session key for last-messages lanes.
- `./reset-teardown-ladder.md` — capability-probed reset, lazy entity-store demotion, atexit telemetry shutdown.
- `./payload-projection.md` — core/promoted/metadata three-bucket result projection shared by get/get_all/search.
- `./error-taxonomy-http-mapping.md` — 5-field MemoryError envelope, HTTP-status table with base-class fallback, Retry-After header intelligence.
- `./filter-front-end-compilation.md` — platform AND/OR/NOT operator dialect → universal per-key op-dict intermediate; merge-not-nest AND semantics.
- `./bm25-lemmatization-normalization.md` — write-time lemma token stream with -ing dual-token recall rule; latched fail-open spaCy loader.
- `./local-identity-bootstrap.md` — ~/.mem0/config.json atomic best-effort writes, OSS-vs-CLI identity coexistence, hashed once-only email aliasing.
- `./llm-content-shape-salvage.md` — provider block-list flattening → fence stripping → empty-after-salvage still raises.
- `./entity-collection-twin.md` — entity store derived from main vector-store config; s3_vectors separator exception; qdrant embedded-client sharing.
- `./oss-project-stub-surface.md` — loud-refusal project.update stubs, unwrapped pydantic re-raise in from_config, dead agent-extraction predicate flagged.
- `./notice-state-machine.md` — once-ever claim gates, CAP=10/WINDOW=7d sliding ledgers in ~/.mem0/config.json, fail-closed-read vs fail-silent-write capacity asymmetry.
- `./temporal-detection-heuristics.md` — relative-phrase/ISO-date regexes, temporal-key suffix classifier, range-operator-vs-data-key split, bool-is-not-epoch guard.
- `./scale-threshold-detection.md` — top_k≥50 instant trigger vs once-ever memory_count≥2000 latch paced every 100 adds; five-spelling provider-count ladder.
- `./decay-usage-detect.md` — process-local 5-strike delete counter + bulk delete_all shortcut; nothing persists a consumed marker.
- `./llm-base-param-gate.md` — reasoning-allowlist ≠ GPT-5 completion-token-rename table; prefix-strip before match; store opt-in for compatible backends.
- `./anthropic-sampling-arbitration.md` — temperature-beats-top_p when both set; family/major/minor sampling gate; thinking-block-first scan parser.
- `./bedrock-provider-dispatch.md` — roster+override provider detection, three capability tables, per-family message formats and temp/topP omission on Converse.
- `./openai-embeddings-batch.md` — dimensions opt-in gate, MAX_BATCH=100 chunking, sort-by-index reassembly, loud count assert.
- `./proxy-memory-injection.md` — OpenAI-shaped wrapper: async write + sync read around litellm, mandatory scope key, dual Memory/MemoryClient result shapes.
- `./faiss-local-store.md` — restricted unpickler whitelist, JSON-over-pickle auto-migration, always-normalize-cosine, rebuild-on-delete renumbering.
- `./pgvector-filter-sql-compilation.md` — universal op-dict → parameterized SQL over JSONB payload; ::numeric casts, LIKE escaping, bool JSON casing, loud non-list in/nin.
- `./pgvector-lazy-collection-pool.md` — open=False non-blocking pool, first-use _ensure_collection latch, dual-psycopg cursor context manager.
- `./pgvector-keyword-search-lane.md` — ts_rank_cd over materialized lemma column, None-not-raise contract feeding BM25 fusion, init-time capability sniffing.
- `./chromadb-where-grammar.md` — split-per-operator $and ranges, De Morgan negation w/ $ne fallback for unmapped ops, singleton unwrap.
- `./chromadb-distance-score-squash.md` — 1/(1+d) similarity squash pinned by fleet regression suite; ragged nested-list parse degrades per-field.
- `./chromadb-client-mode-selection.md` — injected > cloud(api_key+tenant) > host+port server > embedded "db" ladder; eager get_or_create_collection.
- `./langchain-scored-method-ladder.md` — duck-typed scored-method probe ladder, neutral score=1.0 stamp so None never reaches threshold ranking.
- `./http-proxy-client-builder.md` — falsy⇒None / dict-mounts / single-proxy str → httpx.Client built at CONFIG construction, factory-inherited.
- `./azure-assistant-keyword-rewrite.md` — copy-on-write last-message "assistant"→"ai" rewrite dodging Azure Indirect-Attacks filter (#2636); DefaultAzureCredential placeholder fallback.
- `./openai-structured-parse-endpoint.md` — beta.chat.completions.parse twin sharing the base-class reasoning param gate; thin passthrough shape.
- `./huggingface-sigmoid-normalization.md` — absolute per-doc sigmoid replaces set-relative min-max (singleton/tie collapse regressions); copy-stamped rerank_score.
- `./reranker-doc-text-funnel.md` — memory→text→content→str(doc) extraction funnel shared by all rerankers; never drops, never raises.
- `./cohere-server-side-topn.md` — top_n ladder arg→config→len(documents); API order IS output order, no client resort.
- `./zeroentropy-client-side-slice.md` — no top_n param: fetch-all → index-remap → sort-descending → slice.
- `./st-forced-default-config-conversion.md` — base-config rebuild FORCES device/batch_size/progress defaults (deliberately lossy).
- `./st-crossencoder-pair-scoring.md` — local CrossEncoder pair predict, positional zip, ndarray→float coercion, sort-then-slice.
- `./llm-rerank-score-ladder.md` — decimal-first regex → int → clamp [0,1] → neutral 0.5; 4000-char input caps.
- `./llm-reranker-perdoc-failopen.md` — per-document try/except stamps neutral 0.5 and CONTINUES; batch sort after all docs.
- `./reranker-family-completion.md` — family contract: copy-on-stamp, empty short-circuit, fail-open; 0.0-batch vs 0.5-per-doc granularity split.
- `./gcp-credential-priority-ladder.md` — json→file→env→ADC silent-skip ladder; only total failure at rung 4 is fatal.
- `./vertexai-auth-fallback-sandwich.md` — rich authenticator try → bare-except legacy env-var emulation; add/update=DOCUMENT vs search=QUERY task types.
- `./embedding-base-batch-shim.md` — None-config materialization + always-available sequential embed_batch default = the capability probe.
- `./vertexai-embedbatch-chunk-tripwire.md` — 250-chunk native batch with final count-equality raise (never return ragged vectors).
- `./reranker-factory-dispatch.md` — eager string-keyed provider map + three-shape config normalization; bad configs die at the boundary.
- `./dsh-plugin-mount-contract.md` — Cordis `apply(ctx, config)` plugin: inject-gated tool registry, mount-time apiKey/userId validation BEFORE client construction, auto-revertible registrations.
- `./dsh-per-call-scoping-casing-split.md` — per-call userId/agentId/runId overrides of a mount default; snake_case-for-filters vs camelCase-for-add is deliberate twin resolvers.
- `./dsh-add-pending-write-acknowledgment.md` — async /v3/add returns PENDING+event id AFTER the call; three-shape unwrap, camel/snake event-key tolerance, queued-not-stored wording.
- `./dsh-compact-memory-line-format.md` — cross-harness one-line memory contract `[category] text (age) [mem0:id]` with per-field fallbacks and always-present id token.
- `./dsh-output-truncation-dual-cap.md` — every tool output passes 200-line/50KB dual caps (lines then bytes) plus a combined-reason truncation notice.
- `./dsh-failsoft-tool-error-envelope.md` — backend failures resolve to `<tool> failed: <msg>` strings instead of rejecting; fail-soft is the deliberate inverse of pi-agent-plugin's throwing tool.
- `./dsh-wire-asymmetry-offline-tests.md` — search=filters+topK vs add=top-level-camel+source wire contract; two-mock vi.mock harness runs the real plugin offline (29/29).
- `./dsh-source-attribution-family-pattern.md` — KNOWN_EVENT_SOURCES source tagging (unrecognized silently buckets to OTHERS) + the shared kernel across all Mem0 harness-plugin siblings.
- `./plugin-hook-failopen-envelope.md` — always-exit-0 wrapper, typed-return network helpers, stderr-only logging: the side-channel failure posture.
- `./plugin-identity-ladder.md` — env, userConfig, shell-profile regex key ladder with comment/quote/dollar-var guards; user-id fallback chain.
- `./plugin-project-remote-hash-selfheal.md` — cwd + remote-hash dual-key project map with write-back self-heal; git remote slug algorithm.
- `./plugin-transcript-extraction-filters.md` — binary-seek tail read, sidechain and compact-summary skips, angle-bracket and brace noise gates, capped last-N windows.
- `./plugin-session-state-expiry-dedup.md` — 90-day TTL for churny session_state vs unexpiring agent facts; tmp stats-counter fallback suppression gate.
- `./plugin-search-filter-shape.md` — AND-scoped/OR-global filter dialect, double-duty top_k, server threshold vs client min_score, loud-empty regression #22, rerank-opt-in #5684.
- `./plugin-settings-allowlist-merge.md` — DEFAULTS-as-schema merge, unknown_keys typo surfacing, create-once defaults with one-time announcement.
- `./plugin-instructions-policy-merge.md` — repo mem0.md instruction sections merged verbatim into add bodies; absent policy adds zero keys.
- `./plugin-stop-summary-recapture.md` — Stop-hook summary made self-updating per session via run_id infer-dedup; assistant-role attribution; raw-length gate before tag stripping.
- `./plugin-prompt-context-compiler.md` — deterministic grep detectors + /tmp cadence counters compiled into ONE additionalContext emission; overlapping capture windows; once-per-session rubric flag.
- `./plugin-pretooluse-deny-gate.md` — exit-code deny contract (0 allow / 2 block-with-stderr-coaching) protecting memory files from direct writes.
- `./plugin-updatedinput-rewrite-kernel.md` — transparent tool-input completion: absent-gated identity/metadata injection, three-shape filter handling, session_id-in-metadata-not-run_id partition trap.
- `./plugin-config-section-parser.md` — mem0.md heading grammar with five typed readers; malformed lines skipped silently; keys-only-when-non-empty assembly.
- `./plugin-category-bootstrap-latch.md` — once-ever remote-taxonomy apply keyed sha256(apikey)→sha256(taxonomy); EXCL lock with stale steal; success-gated state save.
- `./plugin-telemetry-privacy-envelope.md` — hashed distinct/project ids, env-ladder platform attribution with explicit override, system-props-win payload precedence, bare-except fire-and-forget send.
- `./opencode-scope-ladder.md` — per-call scope parameter (project/session/global) as twin ladders: global search keeps app_id:"*" as a filter while global writes drop app_id entirely; fail-toward-narrowest normalization; fresh-read persisted default.
- `./opencode-dream-gate-fsm.md` — agent-driven memory consolidation: cheap fs gates before any API call, distinct-session counters, 1h-stale exclusive lock, write-evidenced completion, log-the-reasons skips.
- `./opencode-project-remote-parse.md` — one-regex git remote → owner-repo slug (https/scp-ssh/host-alias/.git/trailing-slash) plus the fail-open ladder env > remote > toplevel basename > cwd basename.
- `./opencode-telemetry-parity.md` — TS surface emits into the shared plugin.* namespace field-for-field with scripts/telemetry.py; system-props-win; deliberate keyless-gating divergence (TS silent vs Py user-hash fallback).
- `./opencode-plugin-entry-surface.md` — one async plugin function: no-key log-then-{} guard, 7-hook map matching the package.json manifest, 10 native tools, deny=throw, inject=marker-guarded transform, cleanup=once-guarded beforeExit, identity export via shell.env.
- `./plugin-file-read-context-gate.md` — PreToolUse(Read) context injection: 1500-byte gate ladder, worker-text/wrapper-JSON split, silent exit 0 on every failure path so the Read never blocks.
- `./plugin-session-start-timeline.md` — SessionStart recent-activity banner via the LIST endpoint (page sort), not search; global flip as filter-shape change (`user_id:"*"` OR clause); portable `perl alarm 5` timeout.
- `./plugin-formatting-shared-funnel.md` — shared TYPE_ICONS + format_age display funnel: total-function contract (fallback icon, empty-string age, blanket except), Z-suffix ISO normalization, UTC-pinned deltas.
- `./plugin-compact-summary-marker-capture.md` — compact summary harvested at NEXT SessionStart(compact) because PreCompact precedes the artifact; success-only marker file replaces run_id dedup for once-per-session capture; assistant-role attribution.
- `./plugin-auto-import-triple-dedup.md` — declarative-file importer: O_EXCL lock (120s stale reclaim) → SHA-256 hash store keyed project:branch:file → server probe arbitrating BOTH drift directions; delete-then-rechunk re-import; hash persisted only on full success.
- `./plugin-competing-tools-import.md` — per-source splitter dispatch (cursorrules/copilot ## headers, cline whole-file-per-md, continue HR-or-headers) with hash-skip; export round-trip parser: whole-line `---` block grammar, first-colon frontmatter, comma-list fields, `[]`-on-error exit 0.


## Capsule map
- **Add/search pipeline** — `./pipeline.md`, `./v3-phased-add.md`: LLM extract + batch persist on write; scoped hybrid retrieval with rerank.
- **Scoping & search** — `./scoping.md`, `./search.md`, `./session-scope-key.md`, `./entity-id-coercion.md`: user/agent/run scoping, filter operators, reject-don't-default validation, collision-free session keys.
- **Filter compilation** — `./filter-front-end-compilation.md`, `./qdrant-filter-translation.md`: platform dialect → universal intermediate → native conditions, with the $or/$not dual-key trap at the boundary.
- **Ranking & scoring** — `./hybrid-scoring.md`, `./entity-boost-ranking.md`, `./reranker-contract.md`, `./bm25-lemmatization-normalization.md`: adaptive-divisor fusion, popularity-damped entity boosts, fail-open reranking, the lemmatized token stream BM25 consumes.
- **Write-path mutations** — `./update-ladder.md`, `./delete-all-pagination.md`, `./expiration-read-filter.md`: immutable-scope updates, paged deletes, read-time TTL.
- **Storage backends** — `./vector-store-base.md`, `./sqlite-storage.md`, `./qdrant-filter-translation.md`, `./bm25-write-path.md`, `./backend-list-normalization.md`, `./entity-collection-twin.md`: the vector-store ABC, SQLite history, filter compilation, write-time sparse indexing, shape normalization, derived entity collections.
- **Entity linking** — `./entity-store.md`: exact + semantic dedup, linked_memory_ids, remove-on-delete.
- **Platform plumbing & lifecycle** — `./factory-provider-resolution.md`, `./sensitive-config-redaction.md`, `./telemetry-sampling-singleton.md`, `./llm-response-salvage.md`, `./llm-content-shape-salvage.md`, `./payload-projection.md`, `./reset-teardown-ladder.md`, `./local-identity-bootstrap.md`: provider factories, secret-safe cloning, sampled telemetry, LLM output parsing, result shaping, teardown, local install identity.
- **Errors & API surface** — `./error-taxonomy-http-mapping.md`, `./oss-project-stub-surface.md`: typed exceptions over HTTP statuses, loud feature-gated refusals.
- **Growth notices engine** — `./notice-state-machine.md`, `./temporal-detection-heuristics.md`, `./scale-threshold-detection.md`, `./decay-usage-detect.md`: the once-ever/cap-window notice state machine plus its three trigger detectors (time-shaped intent, scale thresholds, delete strikes).
- **Provider planes (LLM/embeddings/proxy)** — `./llm-base-param-gate.md`, `./anthropic-sampling-arbitration.md`, `./bedrock-provider-dispatch.md`, `./openai-embeddings-batch.md`, `./proxy-memory-injection.md`: per-model-family request shaping, sampling arbitration, Bedrock multi-provider dispatch, native batch embeddings, and the OpenAI-compatible memory proxy.
- **Embedded vector store** — `./faiss-local-store.md`: safe persistence (restricted pickle → JSON), cosine-via-inner-product normalization, rebuild-on-delete.
- **SQL vector store (pgvector)** — `./pgvector-filter-sql-compilation.md`, `./pgvector-lazy-collection-pool.md`, `./pgvector-keyword-search-lane.md`: param-bound operator→SQL compilation, non-blocking pool + first-use ensure latch, the None-on-failure keyword lane hybrid scoring consumes.
- **Chroma adapter** — `./chromadb-where-grammar.md`, `./chromadb-distance-score-squash.md`, `./chromadb-client-mode-selection.md`: one-operator-per-field where compilation (both pinned regressions), 1/(1+d) squash + ragged parse, four-rung client-mode ladder.
- **Untyped store adapters** — `./langchain-scored-method-ladder.md`, `./backend-list-normalization.md`: duck-typed capability probing with a neutral score stamp so threshold ranking never sees None.
- **Config & transport plumbing** — `./http-proxy-client-builder.md`, `./azure-assistant-keyword-rewrite.md`, `./openai-structured-parse-endpoint.md`: config-time httpx proxy client, Azure content-filter keyword rewrite, structured-output parse endpoint over the shared reasoning gate.
- **Reranker internals** — `./huggingface-sigmoid-normalization.md` (+ `./reranker-contract.md`): absolute sigmoid normalization replacing min-max, inside the double-layered fail-open contract.
- **Reranker family completion (pass 6)** — `./reranker-family-completion.md`, `./reranker-doc-text-funnel.md`, `./cohere-server-side-topn.md`, `./zeroentropy-client-side-slice.md`, `./st-forced-default-config-conversion.md`, `./st-crossencoder-pair-scoring.md`, `./llm-rerank-score-ladder.md`, `./llm-reranker-perdoc-failopen.md`, `./reranker-factory-dispatch.md`: the four remaining backends whole — shared extraction funnel and copy-on-stamp contract, server-side vs client-side top-k cut variants, forced-default config conversion, cross-encoder pair scoring, the decimal-first→clamp→0.5 LLM score ladder, per-doc vs batch fail-open granularity, and the eager factory dispatch that binds them.
- **GCP auth & VertexAI embedding plane** — `./gcp-credential-priority-ladder.md`, `./vertexai-auth-fallback-sandwich.md`, `./embedding-base-batch-shim.md`, `./vertexai-embedbatch-chunk-tripwire.md`: four-rung credential ladder with ADC safety net, legacy env-var fallback sandwich, the embedder ABC's sequential batch shim, and the 250-chunk native batch with count-mismatch tripwire.
- **Harness-plugin family (dsh-mem0, pass 7)** — `./dsh-plugin-mount-contract.md`, `./dsh-per-call-scoping-casing-split.md`, `./dsh-add-pending-write-acknowledgment.md`, `./dsh-compact-memory-line-format.md`, `./dsh-output-truncation-dual-cap.md`, `./dsh-failsoft-tool-error-envelope.md`, `./dsh-wire-asymmetry-offline-tests.md`, `./dsh-source-attribution-family-pattern.md`: the integrations/dsh-mem0 package whole (DeepSeek Harness/Cordis plugin over the mem0ai TS SDK) — mount-time validation + inject-gated revertible tool registration, per-call scoping with the deliberate snake/camel casing split, PENDING write acknowledgment, cross-harness one-line memory format, 200-line/50KB dual-cap output guard, fail-soft error envelope vs the throwing sibling, the search-filters/add-top-level wire asymmetry proven by an offline two-mock suite, and KNOWN_EVENT_SOURCES attribution as the decisive instance of the whole harness-plugin idiom.
- **Agent-hook capture kernel (mem0-plugin, pass 8)** — `./plugin-hook-failopen-envelope.md`, `./plugin-identity-ladder.md`, `./plugin-project-remote-hash-selfheal.md`, `./plugin-transcript-extraction-filters.md`, `./plugin-session-state-expiry-dedup.md`, `./plugin-search-filter-shape.md`, `./plugin-settings-allowlist-merge.md`, `./plugin-instructions-policy-merge.md`: the integrations/mem0-plugin hook suite whole — fail-open envelope (exit 0, stderr-only, typed returns), four-rung identity ladder with shell-profile extraction, remote-hash self-healing project identity, transcript JSONL noise-gated extraction windows, tiered expiry plus cross-process dedup gate, scoped search dialect with loud-empty/fail-open pair and regressions #22/#5684, allowlist settings loader, and repo-carried extraction-policy merge.
- **Agent-hook capture kernel II (mem0-plugin, pass 9)** — `./plugin-stop-summary-recapture.md`, `./plugin-prompt-context-compiler.md`, `./plugin-pretooluse-deny-gate.md`, `./plugin-updatedinput-rewrite-kernel.md`, `./plugin-config-section-parser.md`, `./plugin-category-bootstrap-latch.md`, `./plugin-telemetry-privacy-envelope.md`: the remaining capture/guard/config kernel — run_id-scoped self-updating session summaries with assistant-role attribution, the zero-LLM prompt-context compiler with overlapping auto-capture windows and once-per-session rubric, the exit-code deny gate plus the transparent updatedInput rewrite pair (metadata-not-run_id partition rule), the mem0.md section grammar with silent-skip typed readers, the fingerprint-latched remote taxonomy bootstrap, and the hashed-identity fire-and-forget telemetry envelope shared by five editor surfaces.
- **Display + import + post-compact planes (mem0-plugin, pass 11)** — `./plugin-file-read-context-gate.md`, `./plugin-session-start-timeline.md`, `./plugin-formatting-shared-funnel.md`, `./plugin-compact-summary-marker-capture.md`, `./plugin-auto-import-triple-dedup.md`, `./plugin-competing-tools-import.md`: the remaining Python hook planes — the never-blocking Read-context gate with worker-text/wrapper-JSON split, the list-endpoint recency banner with filter-shape global flip, the total-function shared display funnel, the next-SessionStart compact-summary harvest with success-only marker dedup, the two-directional hash+server-probe import ladder with delete-then-rechunk, and the per-source splitter dispatch plus whole-line `---` export round-trip grammar.
- **OpenCode plugin plane (.opencode-plugin, pass 10)** — `./opencode-scope-ladder.md`, `./opencode-dream-gate-fsm.md`, `./opencode-project-remote-parse.md`, `./opencode-telemetry-parity.md`, `./opencode-plugin-entry-surface.md`: the sixth editor surface whole — a bun/TypeScript native-tool plugin (no MCP) ported from the pi-agent lineage: per-call scope with the global read/write asymmetry, the gated auto-dream consolidation FSM with write-evidenced completion, one-regex project identity, cross-language telemetry schema parity with its deliberate keyless-gating divergence, and the full entry registration surface (no-key silent absence, deny-by-throw, marker-guarded context injection, beforeExit finalization).

## Extending the foundation
Add one references-fileshaped capsule per new seam: one loader line, one grouped map entry, decisive source with an invariant, a direct-test probe, and `search_graph` retrieval.

## Provenance
Indexed in Codebase Memory as `mem0` (root `/mnt/hdd/utopia/inspo/mem0` — symlink to canonical `/mnt/hdd/utopia/inspo/memory/mem0`; the FRESH graph lives under the slugged twin project `mnt-hdd-utopia-inspo-memory-mem0`, 17,049 nodes / 65,094 edges, full mode @ `main@8d5b7865` = head_sha = base_sha, origin/main identical → zero drift at pass 4; the short-name `mem0` project still serves the pre-drift 16,822-node graph). Pass 2 ([DONE:131]) mined main.py whole-file planes plus utils/scoring.py, vector_stores/qdrant.py, utils/factory.py, reranker/, memory/{telemetry,notices,utils}.py. Pass 3 ([DONE:162], this entry) re-indexed after upstream drift 001c235→8d5b786 (procedural empty-guard + remove_code_blocks list branch) and ran the symbol-granular citation-vs-inventory grep over all 148 mem0/*.py files before mining exceptions.py, client/utils.py, memory/setup.py, utils/{lemmatization,spacy_models,gcp_auth}.py and the uncited main.py symbols against direct tests in tests/{test_client_utils.py,memory/test_memory_utils.py,utils/test_lemmatization.py,test_telemetry_aliasing.py}. Source and its tests remain authoritative; the graph is a discovery index, not truth. Pass 4 ([DONE:269], rotation lane, pin unchanged): citation-vs-inventory re-run exposed 131/148 files uncited; mined notices.py WHOLE (1,582L) into the four-capsule growth-notices engine, llms/{base,openai,anthropic,aws_bedrock}.py whole into the provider plane, embeddings/{base,openai}.py, proxy/main.py whole, and vector_stores/faiss.py whole — all with direct tests now present upstream (tests/memory/test_notices.py 1,551L + dedicated temporal/decay/performance suites, tests/llms/* 18 files, tests/embeddings/*, tests/test_proxy.py, tests/vector_stores/test_faiss.py); queued `graph_*.py` verification resolved NEGATIVE (no graphs/ subpackage at this pin). Pass 5 ([DONE:343], rotation lane, pin UNCHANGED `main@8d5b7865` = head_sha = base_sha = origin/main zero-drift, graph fresh): executed the queued citation-vs-inventory grep FIRST — 122/148 uncited, mostly standing omission set; executed queued target #2 by mining vector_stores/pgvector.py (563L) + chroma.py (364L) WHOLE plus the never-cited langchain.py adapter, utils/http.py, llms/{openai_azure}_structured twins, reranker/huggingface_reranker sigmoid seam → 11 capsule-v2; queued target #4 RESOLVED POSITIVE: upstream ships direct tests for every newly-mined plane (test_pgvector.py 2,527L incl. TestBuildFilterConditions :2338-2527 + lazy-init/rollback suites; test_chroma.py 396L with FOUR regression docstrings naming the old silent-drop bugs; test_langchain_vector_store.py 300L score-never-None ladder; test_http_client_proxies.py; test_huggingface_reranker_normalize.py 7-case sigmoid suite; test_score_normalization.py cross-backend squash pinning) → in-capsule caveats retired for these planes. Pass 6 ([DONE:385], rotation lane, pin STILL UNCHANGED `main@8d5b7865` = head = base = origin/main after fetch rev-list=0, graph fresh): citation-vs-inventory grep FIRST exposed the four never-ruled reranker backends + gcp_auth/vertexai/base planes; mined reranker/{cohere,zero_entropy,sentence_transformer,llm}_reranker.py whole (92+103+119+172L) into 9 capsules (family completion group), utils/gcp_auth.py + embeddings/vertexai.py whole + embeddings/base.py & memory/base.py ABCs into 4 more — 13 new capsule-v2 → 65 total; direct tests exist for the vertexai plane only (test_vertexai_embeddings.py 14 tests incl. chunking/count-mismatch/memory-action matrices) — the four reranker backends carry NO dedicated suites at this pin, caveats recorded in-capsule rather than invented. Pass 7 ([DONE:456-class], deepening-A lane, cron drain-lane-deepening-a d19142a386f6 successor fire, 2026-08-24): DRIFT RE-ENTRY — origin fetch found pin ADVANCED `8d5b7865`→`7e09615` (+2 commits: docs redirects d18e751 + NEW package `integrations/dsh-mem0/` in feat #7027); ff-pulled clean, re-indexed IN PLACE through the live-symlink root per [DONE:366] benign-variant ruling (NO path-slugged twin; project `mnt-hdd-utopia-inspo-memory-mem0` now 17,134n/65,252e ready head==base==pin; freshness proven by drift-introduced `apply` resolving index.ts 69-138 line-exact after a first-probe wrong-symbol zero was adjudicated as bad needle, not stale graph). Mined the new package WHOLE (4 src modules 293L + 4 test files) into 8 capsule-v2 → **73 total** across a new Harness-plugin-family map group; family pattern mined with pi-agent-plugin/src/memory as the sibling instance (shared formatter kernel verified by fixed-string equality probe, NOT range-diff — first diff probe was executed, found false, and repaired pre-wiring). GATE5 REAL RUNNER: the package's own vitest suite ran offline at pin (`cd integrations/dsh-mem0 && vitest run`, v4.1.10) = **29/29 GREEN** (peer deps deliberately vi.mock'd upstream; no network). Probes byte-exact derived from live grep BEFORE writing (T1-T15 incl. exact census `grep -c 'ctx.tools.register'` = 3 with comment site named); retrieves live-resolved x8 (three tied-twin/twin-page cases routed by qualified name or limit≥4 per [DONE:217]/[DONE:348] precedent); adversarial wrong-project probe on railway-nexus3 total:0 with positive control green; coverage stdin-JSON ×8 cited paths no_recorded_issue+metadata_match+generation_matches=true. Pass 8 ([DONE:pass8], miner-mem0 dedicated lane, pin main@7e096155714c = graph head = base = origin/main zero drift; the SHORT-name project mem0 now serves the fresh 16,822n/64,103e FULL graph at this pin, so the twin-project note above is historical): FIRST pass with a work record — created inspo/mem0-work/{state,research,verification}.md and repaired the never-maintained shared-ledger row (was pass-0/unstarted despite passes 2-7); mined the integrations/mem0-plugin hook-capture kernel WHOLE (_identity.py, load_settings.py, _project.py, on_pre_compact.py, auto_capture.py, _search.py, _instructions.py, session_stats.py + hooks.json wiring) into 8 capsule-v2 -> 81 total in the new Agent-hook capture kernel group; probes executed byte-for-byte GREEN under the checkout .venv pytest 9.1.1 offline (test_search 13, test_write_path -k resolve 4, test_project 15, test_auto_capture 11, test_session_stats 17, test_load_settings 8, -k instructions 10 passed); retrieves live-resolved x8 (get_code_snippet x4, search_graph x3, search_code x1) after an early search_graph unexpected-token flake recovered on retry; adversarial negative-symbol snippet fetch rejected-as-expected; check_index_coverage x18 cited paths no_recorded_issue + metadata_match + generation_matches=true; LICENSE CORRECTION recorded: repo root LICENSE is Apache-2.0, so pre-pass-8 capsules labeled MIT carry a mislabel queued for a later parity pass; server/* (fastapi/slowapi absent -> tests importorskip-SKIP) and cli/node TS (no node_modules) planes recorded as RUNNER-BLOCKED omissions, not completions.
Pass 9 (2026-08-25, pin unchanged `main@7e096155714c`, graph `mem0` 16,822 nodes / 64,103 edges): mined the remaining mem0-plugin capture/guard/config kernel into seven capsule-v2 references (refs 81 → 88). Runner discoveries: `.opencode-plugin` TS suites run offline under bun 1.4.0 (32/33; api-key.test.ts needs @opencode-ai/plugin); server plane still blocked (fastapi present but jose/slowapi/sqlalchemy absent); cli/node node_modules still absent. 59 pre-pass-8 references still carry an MIT provenance label vs the repo's Apache-2.0 LICENSE (relabel queued). Pass 10 (2026-08-27, pin UNCHANGED `main@7e096155714c` re-verified by rev-parse before citation): `.opencode-plugin` deep pass under bun 1.4.0 — mined the whole TS plane (scope.ts 71L, dream.ts 225L, project.ts 20L, telemetry.ts 113L, opencode-mem0.ts 1,000L, api-key.ts 30L + all five test files) into five capsule-v2 references (refs 88 → 93) in a new OpenCode-plugin-plane map group; `bun install` now works (network available) unblocking api-key.test.ts → full suite 40 tests / 39 pass / 1 environmental failure (bun 1.4.0 caches os.homedir() from startup $HOME, so the runtime-HOME profile-recovery test fails under bun but would pass under Node semantics — probed directly, not a source defect); Codebase Memory MCP NOT connected this session → direct source+test reading fallback per AGENTS.md, recorded in verification.md pass 10. Pass 11 (2026-08-27, pin UNCHANGED `main@7e096155714c` re-verified by rev-parse, tree clean; MCP again NOT connected → DEGRADED direct-read path): mined the remaining Python hook planes — file_context.py + session_timeline.py + _formatting.py Read/display lane, capture_compact_summary.py + on_pre_compact.sh post-compact chain, auto_import.py + import_competing_tools.py + parse_export_file.py import pipeline — into six capsule-v2 references (refs 93 → 99) in a new pass-11 map group; direct tests executed GREEN under checkout .venv pytest: test_message_roles.py 4 + test_parse_export_file.py 12 + test_import_competing_tools.py 13 = 29 passed; byte-exact grep probes GREEN for the untested display-plane files (honest no-dedicated-test gaps recorded in-capsule).

## Full view (memory graph)
Revalidate `mem0` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the write-time extraction pipeline, scoping, reject-not-default validation, hybrid scoring, vector-store ABC, SQLite history, the notice state machine, provider request-shaping contracts, (pass 5) the pgvector/chroma/langchain backend-adapter contracts + config-time proxy plumbing + sigmoid reranker normalization, (pass 6) the complete five-backend reranker family with its truncation/failure variants + the GCP credential ladder + VertexAI auth-fallback/batch-tripwire contracts, and (pass 7) the harness-plugin integration idiom whole — mount validation, per-call scoping with its casing split, PENDING write acknowledgment, compact line format, dual-cap output guard, fail-soft envelope, wire asymmetry, source attribution; adapt vector-store, LLM, embedder, and reranker backends via the factory registries; omit the hosted-api/cloud orchestration (client/project.py is the hosted surface — its org/project pair validation informs the OSS stub contract but is not portable), the notices' product copy and PostHog flag payloads (the STATE MACHINE is portable, the upsell wording is not), remaining thin per-provider LLM/embedder twins beyond the mined contracts (azure/deepseek/groq/litellm/lmstudio/minimax/ollama/sarvam/together/vllm/xai/gemini + embeddings twins — the structured-output TWINS are now mined as the representative shape), remaining vector-store backend bodies (~20 files repeating the same ABC contract beyond qdrant/faiss/pgvector/chroma/langchain — mine one on a named porting question; azure_mysql/oracledb/cassandra SQL cousins share pgvector's JSONB-payload shape), configs/** declarative bases (roster ruling; the reranker config CLASSES are cited as data inside the factory capsule but their field bodies stay omitted), and prompt text packs unless a target requires them. mem0-ts is a separate codebase (its scoring/factory/notices.ts twins were used only to confirm pattern symmetry). Known dead code at this pin: `_should_use_agent_memory_extraction` (sync+asyn[c twin pair — BOUNDARIES TAIL LOSS MARKER, 2026-08-25: the remainder of this pre-pass-8 boundaries sentence beyond the roster clause was irrecoverably cut by a long-line read/write tooling fault during pass-8 wiring; surviving text before this marker is original, later clauses must be re-derived from the capsules if ever needed] Plus (pass 8) adopt the agent-hook capture kernel whole — fail-open envelope posture, identity resolution ladder, remote-hash self-healing project identity, noise-gated transcript extraction windows, tiered expiry with cross-process dedup gate, scoped search filter dialect with loud-empty/fail-open pair, allowlist settings loader, and verbatim repo-carried extraction-policy merge — adapt hook cadences/metadata vocabulary to the host, omit mem0 REST specifics and product copy; KNOWN REPAIR: relabel pre-pass-8 capsules' license from MIT to Apache-2.0 during a later parity pass.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`anthropic-sampling-arbitration.md`](./anthropic-sampling-arbitration.md)
- [`azure-assistant-keyword-rewrite.md`](./azure-assistant-keyword-rewrite.md)
- [`backend-list-normalization.md`](./backend-list-normalization.md)
- [`bedrock-provider-dispatch.md`](./bedrock-provider-dispatch.md)
- [`bm25-lemmatization-normalization.md`](./bm25-lemmatization-normalization.md)
- [`bm25-write-path.md`](./bm25-write-path.md)
- [`chromadb-client-mode-selection.md`](./chromadb-client-mode-selection.md)
- [`chromadb-distance-score-squash.md`](./chromadb-distance-score-squash.md)
- [`chromadb-where-grammar.md`](./chromadb-where-grammar.md)
- [`cohere-server-side-topn.md`](./cohere-server-side-topn.md)
- [`decay-usage-detect.md`](./decay-usage-detect.md)
- [`delete-all-pagination.md`](./delete-all-pagination.md)
- [`dsh-add-pending-write-acknowledgment.md`](./dsh-add-pending-write-acknowledgment.md)
- [`dsh-compact-memory-line-format.md`](./dsh-compact-memory-line-format.md)
- [`dsh-failsoft-tool-error-envelope.md`](./dsh-failsoft-tool-error-envelope.md)
- [`dsh-output-truncation-dual-cap.md`](./dsh-output-truncation-dual-cap.md)
- [`dsh-per-call-scoping-casing-split.md`](./dsh-per-call-scoping-casing-split.md)
- [`dsh-plugin-mount-contract.md`](./dsh-plugin-mount-contract.md)
- [`dsh-source-attribution-family-pattern.md`](./dsh-source-attribution-family-pattern.md)
- [`dsh-wire-asymmetry-offline-tests.md`](./dsh-wire-asymmetry-offline-tests.md)
- [`embedding-base-batch-shim.md`](./embedding-base-batch-shim.md)
- [`entity-boost-ranking.md`](./entity-boost-ranking.md)
- [`entity-collection-twin.md`](./entity-collection-twin.md)
- [`entity-id-coercion.md`](./entity-id-coercion.md)
- [`entity-store.md`](./entity-store.md)
- [`error-taxonomy-http-mapping.md`](./error-taxonomy-http-mapping.md)
- [`expiration-read-filter.md`](./expiration-read-filter.md)
- [`factory-provider-resolution.md`](./factory-provider-resolution.md)
- [`faiss-local-store.md`](./faiss-local-store.md)
- [`filter-front-end-compilation.md`](./filter-front-end-compilation.md)
- [`gcp-credential-priority-ladder.md`](./gcp-credential-priority-ladder.md)
- [`http-proxy-client-builder.md`](./http-proxy-client-builder.md)
- [`huggingface-sigmoid-normalization.md`](./huggingface-sigmoid-normalization.md)
- [`hybrid-scoring.md`](./hybrid-scoring.md)
- [`langchain-scored-method-ladder.md`](./langchain-scored-method-ladder.md)
- [`llm-base-param-gate.md`](./llm-base-param-gate.md)
- [`llm-content-shape-salvage.md`](./llm-content-shape-salvage.md)
- [`llm-rerank-score-ladder.md`](./llm-rerank-score-ladder.md)
- [`llm-reranker-perdoc-failopen.md`](./llm-reranker-perdoc-failopen.md)
- [`llm-response-salvage.md`](./llm-response-salvage.md)
- [`local-identity-bootstrap.md`](./local-identity-bootstrap.md)
- [`notice-state-machine.md`](./notice-state-machine.md)
- [`openai-embeddings-batch.md`](./openai-embeddings-batch.md)
- [`openai-structured-parse-endpoint.md`](./openai-structured-parse-endpoint.md)
- [`opencode-dream-gate-fsm.md`](./opencode-dream-gate-fsm.md)
- [`opencode-plugin-entry-surface.md`](./opencode-plugin-entry-surface.md)
- [`opencode-project-remote-parse.md`](./opencode-project-remote-parse.md)
- [`opencode-scope-ladder.md`](./opencode-scope-ladder.md)
- [`opencode-telemetry-parity.md`](./opencode-telemetry-parity.md)
- [`oss-project-stub-surface.md`](./oss-project-stub-surface.md)
- [`payload-projection.md`](./payload-projection.md)
- [`pgvector-filter-sql-compilation.md`](./pgvector-filter-sql-compilation.md)
- [`pgvector-keyword-search-lane.md`](./pgvector-keyword-search-lane.md)
- [`pgvector-lazy-collection-pool.md`](./pgvector-lazy-collection-pool.md)
- [`pipeline.md`](./pipeline.md)
- [`plugin-auto-import-triple-dedup.md`](./plugin-auto-import-triple-dedup.md)
- [`plugin-category-bootstrap-latch.md`](./plugin-category-bootstrap-latch.md)
- [`plugin-compact-summary-marker-capture.md`](./plugin-compact-summary-marker-capture.md)
- [`plugin-competing-tools-import.md`](./plugin-competing-tools-import.md)
- [`plugin-config-section-parser.md`](./plugin-config-section-parser.md)
- [`plugin-file-read-context-gate.md`](./plugin-file-read-context-gate.md)
- [`plugin-formatting-shared-funnel.md`](./plugin-formatting-shared-funnel.md)
- [`plugin-hook-failopen-envelope.md`](./plugin-hook-failopen-envelope.md)
- [`plugin-identity-ladder.md`](./plugin-identity-ladder.md)
- [`plugin-instructions-policy-merge.md`](./plugin-instructions-policy-merge.md)
- [`plugin-pretooluse-deny-gate.md`](./plugin-pretooluse-deny-gate.md)
- [`plugin-project-remote-hash-selfheal.md`](./plugin-project-remote-hash-selfheal.md)
- [`plugin-prompt-context-compiler.md`](./plugin-prompt-context-compiler.md)
- [`plugin-search-filter-shape.md`](./plugin-search-filter-shape.md)
- [`plugin-session-start-timeline.md`](./plugin-session-start-timeline.md)
- [`plugin-session-state-expiry-dedup.md`](./plugin-session-state-expiry-dedup.md)
- [`plugin-settings-allowlist-merge.md`](./plugin-settings-allowlist-merge.md)
- [`plugin-stop-summary-recapture.md`](./plugin-stop-summary-recapture.md)
- [`plugin-telemetry-privacy-envelope.md`](./plugin-telemetry-privacy-envelope.md)
- [`plugin-transcript-extraction-filters.md`](./plugin-transcript-extraction-filters.md)
- [`plugin-updatedinput-rewrite-kernel.md`](./plugin-updatedinput-rewrite-kernel.md)
- [`proxy-memory-injection.md`](./proxy-memory-injection.md)
- [`qdrant-filter-translation.md`](./qdrant-filter-translation.md)
- [`reranker-contract.md`](./reranker-contract.md)
- [`reranker-doc-text-funnel.md`](./reranker-doc-text-funnel.md)
- [`reranker-factory-dispatch.md`](./reranker-factory-dispatch.md)
- [`reranker-family-completion.md`](./reranker-family-completion.md)
- [`reset-teardown-ladder.md`](./reset-teardown-ladder.md)
- [`scale-threshold-detection.md`](./scale-threshold-detection.md)
- [`scoping.md`](./scoping.md)
- [`search.md`](./search.md)
- [`sensitive-config-redaction.md`](./sensitive-config-redaction.md)
- [`session-scope-key.md`](./session-scope-key.md)
- [`sqlite-storage.md`](./sqlite-storage.md)
- [`st-crossencoder-pair-scoring.md`](./st-crossencoder-pair-scoring.md)
- [`st-forced-default-config-conversion.md`](./st-forced-default-config-conversion.md)
- [`telemetry-sampling-singleton.md`](./telemetry-sampling-singleton.md)
- [`temporal-detection-heuristics.md`](./temporal-detection-heuristics.md)
- [`update-ladder.md`](./update-ladder.md)
- [`v3-phased-add.md`](./v3-phased-add.md)
- [`vector-store-base.md`](./vector-store-base.md)
- [`vertexai-auth-fallback-sandwich.md`](./vertexai-auth-fallback-sandwich.md)
- [`vertexai-embedbatch-chunk-tripwire.md`](./vertexai-embedbatch-chunk-tripwire.md)
- [`zeroentropy-client-side-slice.md`](./zeroentropy-client-side-slice.md)
