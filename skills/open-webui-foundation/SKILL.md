---
name: open-webui-foundation
description: "Use when porting open-webui's runtime-mutable config store, typed event bus, socket emitter/caller pair, hybrid RAG retrieval ladder, DB-stored plugin loader, filter inlet/outlet/stream pipeline, chat-stream machinery (agentic tool loop, tag scanner, delta coalescing, cancellation), built-in-tool authz gates, access-grants ACL plane, outbound provider-proxy plane (timeout ladders, Ollama error ladder, multi-backend routing, OpenAI/Azure/Responses normalization), file-to-knowledge ingest plane (upload admission, process bridge with knowledge auto-link, hash-dedup chunking kernel, embed-first/bind-later binding, transitive file ACL), inbound trust boundary (three-transport auth-token ladder, dual-mechanism JWT revocation, API-key gates on raw ASGI paths, hash-prefix password dispatch), or SDK-constrained MCP client lifecycle (construction-time SSL, pop_all ownership transfer, no-shield same-task teardown). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
disable-model-invocation: true
---

# open-webui: Extension Runtime & Realtime Services Foundation

## Use this for
Use when porting open-webui's runtime-mutable config store, typed event bus, socket event emitter/caller pair, hybrid RAG retrieval ladder, DB-stored plugin loader, filter inlet/outlet/stream pipeline, the chat-stream machinery (agentic tool loop, tag scanner, delta coalescing, cancellation), the access-grants ACL plane, the outbound provider-proxy plane, the file→knowledge-collection ingest plane (upload → process → status → bind → ACL), or the inbound trust boundary + MCP client plane (auth transports, JWT revocation algebra, API-key gates, password-hash migration, SDK-constrained client teardown). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/config-store.md` — How does app config persist to DB while env-seeded defaults never override persisted values?
- `references/event-bus.md` — How do you fan one validated domain event to pluggable sinks without leaking secrets or cross-sink failures?
- `references/socket-events.md` — How do chat events reach every device of a user across instances, and how does the backend safely call back into one browser session?
- `references/hybrid-retrieval.md` — How do BM25 and vector search fuse under a reranker, degrading gracefully when the vector store lacks native hybrid?
- `references/plugin-loader.md` — How does DB-stored user Python become an importable module without corrupting `sys.modules`?
- `references/filter-pipeline.md` — In what order do filter plugins run, and how are their params and valves bound?
- `references/agentic-tool-loop.md` — How do streamed tool calls become a bounded agent loop whose OR-style display state stays aligned across continuation rounds?
- `references/stream-tag-scanner.md` — How do you parse `<think>`/`<code>`-style tags incrementally over a token stream without rescanning or re-detecting your own start tag?
- `references/delta-coalescing.md` — How do you throttle high-frequency stream deltas into bounded socket writes without reordering or losing a type?
- `references/cancellation-ladder.md` — What must happen on client cancel mid-stream so nothing leaks upstream or corrupts persisted state?
- `references/builtin-authz-gates.md` — How do you guarantee a legacy second execution path enforces identical authorization to the primary path?
- `references/access-grants-acl.md` — How do you replace a per-model JSON ACL column with a relational grant table without changing semantics?
- `references/shared-session-pool.md` — How do you share one outbound aiohttp ClientSession across a FastAPI monolith without leaking connections or closing the pool?
- `references/provider-timeout-ladder.md` — What should "unset" mean for an outbound LLM timeout env var, and how do streaming calls differ from unary ones?
- `references/ollama-send-request-ladder.md` — When a proxied provider call fails, what reaches the client vs telemetry, and who releases the connection?
- `references/provider-backend-resolution.md` — How do you route one logical model across N backends with per-backend keys/config without letting callers escape the allow-list?
- `references/openai-completion-proxy.md` — How do you normalize one OpenAI-ish payload across vanilla, Azure (v1 + legacy deployment), and Responses dialects in a single entry point?
- `references/proxy-auth-header-ladder.md` — How do you send credentials upstream (bearer/session/OAuth/Entra) without leaking your own transport headers back to clients?
- `references/ollama-model-aggregation.md` — How do you fan out a model census across N backends so failures and disabled entries never corrupt per-index post-processing?
- `references/upload-process-status-pipeline.md` — How does a browser upload become processed content with live SSE progress, and why must client-supplied linkage metadata be re-gated server-side?
- `references/process-file-ingest-ladder.md` — How does one endpoint turn a stored file into embedded chunks without holding DB connections across slow embedding calls?
- `references/save-docs-vector-db-kernel.md` — What makes landing chunks into a vector collection safe: hash dedup scoped by file, splitter validation, embedding_config stamping, overwrite/add lifecycle?
- `references/knowledge-file-binding-lifecycle.md` — In what order do embed, bind-row, and destructive cleanup run when attaching, refreshing, or removing a file from a shared collection?
- `references/kb-metadata-embedding-maintenance.md` — How do you upsert fail-soft self-description embeddings into one fixed catalog collection without exhausting the pool during admin reindex?
- `references/transitive-file-access-resolver.md` — How do you resolve read/write on a file that arrives transitively via collections/channels/chats/models without read access laundering into write?
- `references/auth-token-transport-ladder.md` — How do you authenticate one FastAPI dependency across header/cookie/custom-header transports without holding a DB session?
- `references/jwt-issue-revoke-algebra.md` — How do you revoke stateless JWTs both per-token (sign-out) and per-user (IdP logout) with TTL-bounded Redis state?
- `references/api-key-config-gates.md` — How do you gate API keys by runtime config, user permissions, AND endpoint allow-lists without trusting proxy-visible paths?
- `references/password-hash-prefix-dispatch.md` — How do you migrate password hashing algorithms without breaking stored hashes?
- `references/mcp-client-lifecycle.md` — How do you host MCP client sessions whose SDK forbids shielded/cross-task teardown?

## Capsule map
- **Config store** — `config-store`: per-key dotted DB rows over a DEFAULTS dict; seeding is insert-if-absent so DB wins after first boot; oauth.* stays ephemeral unless explicitly enabled.
- **Event bus** — `event-bus`: catalog-validated `resource.operation` names, sanitized Event build, fail-soft sink list.
- **Socket events** — `socket-events`: emit gated on redis-mode-or-local-room, per-type DB persistence; caller RPC refuses sessions not owned by the requesting user.
- **Hybrid retrieval** — `hybrid-retrieval`: native server-side hybrid -> weighted EnsembleRetriever keyed by chunk content hash -> rerank compressor -> trim-to-k.
- **Plugin loader** — `plugin-loader`: synthetic module via exec in temp-file namespace; class-shape dispatch (Pipe/Filter/Action/Event, Tools); failed load deactivates the function.
- **Filter pipeline** — `filter-pipeline`: priority+id sorted filters, signature-filtered params, valves caching per request context.
- **Agentic tool loop** — `agentic-tool-loop`: FIFO batch while-loop capped by env ladder (legacy-name fallback, -1 unlimited); `_split_tool_calls` raw_decode expansion; sequential-except-delegate execution; prior_output splice with placeholder trim on each continuation.
- **Stream tag scanner** — `stream-tag-scanner`: per-(item_id, content_type) scan memory, longest-tag resume offset, open-bracket backtrack, inside-tag-block append guard prevents self re-detection.
- **Delta coalescing** — `delta-coalescing`: single pending slot keyed by delta type over full-output snapshots (lossless latest-wins); type-switch/non-delta/end-of-stream flush guarantees.
- **Cancellation ladder** — `cancellation-ladder`: shielded body_iterator.aclose() -> shielded done+output persist (touch=False under realtime save) -> unconditional re-raise.
- **Builtin authz gates** — `builtin-authz-gates`: five-factor mirror gate documented at the legacy XML-tag entrance; internal callers get narrower tool surfaces; spec-level param stripping.
- **Access grants ACL** — `access-grants-acl`: three-arm limit(1) existence check, correlated-EXISTS list filter with owner arm, delete-all-then-insert bridge, anyone-capped-at-read normalization, NULL-semantics-aware boot backfill.
- **Shared session pool** — `shared-session-pool`: one lazily-created module-global ClientSession; streaming adds only a sock_read idle cap; `cleanup_response` closes only responses (version-tolerant); `stream_wrapper` try/finally cleanup; passthrough vs NDJSON line modes.
- **Provider timeout ladder** — `provider-timeout-ladder`: unset ⇒ None = unlimited (not a default); garbage ⇒ safe fallbacks; stream idle cap separate from total; per-purpose overrides with legacy env-name fallbacks.
- **Ollama send-request ladder** — `ollama-send-request-ladder`: header precedence base→forwarded→custom-LAST; upstream errors parsed/published/re-raised status-preserving on both JSON-decode arms; streaming flips response ownership to StreamingResponse.
- **Provider backend resolution** — `provider-backend-resolution`: caller url_idx validated against the model's backend allow-list (admin/bypass exempt); random.choice load-balancing; str(idx)-then-base-url config/key fallback; refetch-on-cache-miss before NOT_FOUND.
- **OpenAI completion proxy** — `openai-completion-proxy`: ordered normalization ladder across vanilla/Azure-v1/deployment/Responses dialects; request.state-only bypass flags; SSE-error-as-JSON gate.
- **Proxy auth header ladder** — `proxy-auth-header-ladder`: auth_type ladder bearer/session/system_oauth/azure_ad; HS256 user-info JWT mint with plain-header fallback; hop-by-hop response headers stripped (aiohttp#4462); custom headers applied LAST.
- **Ollama model aggregation** — `ollama-model-aggregation`: gather over per-backend futures with no-op sleep(0) placeholders keeping index alignment for disabled backends; failed_idxs skip-list; prefix_id/tags/connection stamping.
- **Upload-process-status pipeline** — `upload-process-status-pipeline`: dict-vs-model response encodes processing mode; post-storage size cap with compensating blob delete; ENAMETOOLONG rename retry; fresh-session-per-second SSE status ladder; server-side CWE-862/863 re-gate of client-supplied knowledge auto-link.
- **File ingest ladder** — `process-file-ingest-ladder`: three content arms (form-content / knowledge copy-reuse / loader); commit-before-embed + fresh-session completion writes; failure = failed-status + hash-clear pairing so retries pass the dedup gate.
- **Vector-DB landing kernel** — `save-docs-vector-db-kernel`: hash-dedup scoped by file_id; splitter validation order; sanitize + embedding_config stamping per row; overwrite/silent-no-op/append collection lifecycle; main-loop embed bridge with timeout.
- **Knowledge binding lifecycle** — `knowledge-file-binding-lifecycle`: dual gate (KB-write ∧ file-read); embed-then-bind on add; has_file-validate-then-mutate on update; unbind-then-purge with ownership-gated destructive cleanup on remove.
- **KB metadata embeddings** — `kb-metadata-embedding-maintenance`: fixed 'knowledge-bases' catalog; stable-id upsert; fail-soft bool returns; session-free admin reindex with counted partial success.
- **Transitive file ACL** — `transitive-file-access-resolver`: five containment arms; write/delete conferred ONLY when the containing object's owner owns the file (CWE-863 rule); batched existence checks; group-set threading.
- **Auth token transport ladder** — `auth-token-transport-ladder`: pure-ASGI three-transport normalization (header → token cookie → custom API-key header) into scope state; dependency re-reads all three; `sk-` prefix dispatch; delete-all-OAuth-cookies on JWT failure; scope-backed user reuse by outer audit middleware.
- **JWT issue/revoke algebra** — `jwt-issue-revoke-algebra`: jti+iat always minted, exp optional; dual Redis revocation keys (per-token jti, per-user iat-comparison with fail-closed legacy rule); TTL = remaining token life; None-returning mirror for WebSocket handshakes.
- **API-key config gates** — `api-key-config-gates`: one batched four-key config read; separate global-enable and per-user-permission 403 gates; endpoint allow-list enforced at the dependency layer on the raw ASGI path (CVE-2026-48710) with exact-or-`/`-prefix matching.
- **Password hash prefix-dispatch** — `password-hash-prefix-dispatch`: verification dispatches on the stored `$argon2` prefix, not the configured algorithm; asymmetric reject-new/truncate-old 72-byte policy; off-loop crypto; boolean-failure mapping.
- **MCP client lifecycle** — `mcp-client-lifecycle`: construction-time verify factory; bounded initialize handshake; pop_all ownership transfer; null-before-close idempotent disconnect forbidding shield/wait_for (same-task TaskGroup exit); per-request fresh clients torn down LIFO in a contained finally.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
open-webui ("Open WebUI License" — BSD-3-Clause base plus branding condition; keep reuse citations-only), `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory project `open-webui` (FULL, ready, 207312 nodes / 268255 edges, generation 2026-08-24T16:13:21Z; 7 parse-partial cosmetic files uncited).

## Full view (memory graph)
Revalidate `open-webui` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts (config precedence algebra, sink dispatch loop, retrieval result shape, module-exec hygiene, param filtering); adapt host-specific integration (SQLAlchemy models, socket.io rooms, LangChain retrievers, FastAPI state); omit product behavior (branding/license terms, product UI chrome beyond the mined client planes).
