---
name: open-webui-foundation
description: "Use when porting open-webui's runtime-mutable config store, typed event bus, socket event emitter/caller pair, hybrid RAG retrieval ladder, DB-stored plugin loader, filter inlet/outlet/stream pipeline, agentic tool-call loop with streamed tool calls, incremental stream tag scanner, socket delta coalescing, mid-stream cancellation persistence, mirrored built-in-tool authz gates, the access-grants ACL plane, or the outbound provider-proxy plane (shared aiohttp session pool, timeout env ladders, Ollama send_request error ladder, multi-backend model routing/resolution, OpenAI/Azure/Responses payload normalization, credential header ladder, fan-out model aggregation). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---

# open-webui: Extension Runtime & Realtime Services Foundation

## Use this for
Use when porting open-webui's runtime-mutable config store, typed event bus, socket event emitter/caller pair, hybrid RAG retrieval ladder, DB-stored plugin loader, or filter inlet/outlet/stream pipeline. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

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

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
open-webui ("Open WebUI License" — BSD-3-Clause base plus branding condition; keep reuse citations-only), `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory project `open-webui` (FULL, ready, 207312 nodes / 268255 edges, generation 2026-08-24T16:13:21Z; 7 parse-partial cosmetic files uncited).

## Full view (memory graph)
Revalidate `open-webui` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts (config precedence algebra, sink dispatch loop, retrieval result shape, module-exec hygiene, param filtering); adapt host-specific integration (SQLAlchemy models, socket.io rooms, LangChain retrievers, FastAPI state); omit product behavior (branding/license terms, specific provider routers, Svelte frontend).
