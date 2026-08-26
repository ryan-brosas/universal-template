---
name: pi-mono-foundation
description: Use when porting agent-loop, event-stream, provider-retry, context-compaction, branch-summarization, tool-batch-execution, auto-compaction wiring, Anthropic wire-compat/message normalization, session-storage backends, or extension tool-wrapping machinery from badlogic/pi-mono — capsule-v2 source maps with decisive excerpts and graph retrieval.
---

# pi-mono: agent-runtime foundation

## Use this for
Use when porting the request-lifecycle spine of a coding agent: typed single-consumer event streams, provider retry ladders, two-tier agent loops with steering hooks, auto-compaction triggers with structurally safe cuts, repeated-compaction correctness, or abandoned-branch summarization. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/event-stream.md` — expose a long-running operation as a typed single-consumer async stream whose final result is independently awaitable.
- `references/provider-retry.md` — which provider errors auto-retry, what delay applies, and when a server-suggested delay must abort instead of wait.
- `references/agent-loop.md` — exact continue/stop rules of a two-tier loop interleaving streamed responses, tool batches, steering injections, and truncation fail-safety.
- `references/compaction-trigger-cut.md` — what threshold fires auto-compaction and which entries a cut may split on without orphaning tool calls.
- `references/compaction-repeat.md` — how repeated compaction reuses the previous summary and retained tail without losing or duplicating messages.
- `references/branch-summarization.md` — fold an abandoned conversation branch into one chronological summary under a token budget that preserves prior summaries.
- `references/anthropic-message-normalization.md` — convert arbitrary internal messages into wire-valid Anthropic blocks without empty-content or tool-orphan rejections.
- `references/anthropic-wire-compat.md` — derive every per-clone request difference from one defaulted `model.compat` record (eager streaming, strict tools, beta fallback).
- `references/tool-batch-execution.md` — run a mixed batch of model tool calls across parallel/sequential modes preserving call order, validation funneling, and all-terminate semantics.
- `references/auto-compaction-activation.md` — the session-level gate ladder that fires compaction, retries overflow exactly once, and never re-fires on stale usage.
- `references/sqlite-session-backend.md` — the pluggable SessionStorage contract, serialized write path, and shared conformance battery that proves backend equivalence.
- `references/extension-tool-wrapping.md` — interconvert extension ToolDefinitions and kernel AgentTools and announce dynamically added tools as data on results.

## Capsule map
- **EventStream kernel** — `event-stream`: queue+waiter dual surface; push-after-done dropped; `result()` independent of iteration; error events resolve (not reject) the final promise.
- **Provider retry ladder** — `provider-retry`: `x-should-retry` header veto, 408/409/429/5xx list, jittered exponential cap (0.5s·2ⁱ max 8s), throw on oversized server delay, fresh-request retries, abort-checked sleeps.
- **Agent loop semantics** — `agent-loop`: outer follow-up loop / inner tool-call loop; `length` stopReason fails EVERY tool call of that message; steering before response, follow-ups keep the loop alive; `agent_end` exactly once.
- **Compaction trigger & safe cut** — `compaction-trigger-cut`: fire at `contextTokens > window − reserveTokens`; valid cuts exclude only toolResult; backward token walk + forward snap + split-turn detection via user-message test; stale-usage guard prevents re-fire loops.
- **Repeated compaction** — `compaction-repeat`: previous retainedTail re-chained as virtual `${id}:retained:${i}` entries; previous summary passed as `<previous-summary>`; split-turn stitch + combined usage; never throws (`Result`).
- **Branch summarization** — `branch-summarization`: common-ancestor tree diff → newest-first budget packing with 90% boundary-admission for prior summaries → single 2048-token summary with file-ops footer.
- **Anthropic message normalization** — `anthropic-message-normalization`: empty-drop + consecutive-toolResult coalescing + thinking-signature downgrade ladder; `tool_reference` content displaced to sibling blocks after the `tool_result`.
- **Anthropic wire-compat ladder** — `anthropic-wire-compat`: one defaulted compat record drives per-tool `eager_input_streaming`, legacy beta-header fallback (only with tools), strict-schema projection, deferred `defer_loading` tools uncached.
- **Tool batch execution** — `tool-batch-execution`: any `executionMode: "sequential"` tool serializes the whole batch; parallel mode keeps model order via positional entries + Promise.all; validation/block/abort funnel into immediate error outcomes; terminate = all-terminate.
- **Auto-compaction activation** — `auto-compaction-activation`: `_checkCompaction` gate ladder (enabled → aborted → same-model → stale-timestamp guard) around overflow compact-and-retry-once latch and threshold firing with zero-usage estimate fallback; resolves the leaf's recorded graph blind spot.
- **SQLite session backend** — `sqlite-session-backend`: SessionStorage contract with storage-assigned parentId/seq/timestamp under a single write queue; equivalence proven by the shared `createSessionBackendConformance` battery (30/30 live).
- **Extension tool wrapping** — `extension-tool-wrapping`: ToolDefinition↔AgentTool interconversion with closure-injected context; `addedToolNames` diffed across execute feeds Anthropic `tool_reference` deferred loading as replayable data.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-mono (MIT, © Mario Zechner), `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory project `pi-mono` FULL mode, ready, 18491 nodes / 80381 edges, generation 2026-08-24T16:11:21Z, head == base == pin. Coverage caveats: parse-partial ×8 (none cited); `packages/agent/src/harness/env` excluded by design.

## Full view (memory graph)
Revalidate `pi-mono` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Known graph blind spots: `compact()`/`shouldCompact()`/`generateBranchSummary()` show zero inbound CALLS edges — activation is dynamic wiring in `coding-agent/src/core/agent-session.ts` (:2150 threshold check, :2166 `_runAutoCompaction`, :3056/:3122 branch switch).

## Boundaries
Adopt pure kernels: EventStream, retry ladder, loop semantics, compaction pipeline, branch summarization, tool-batch execution, compaction gate ladder, SessionStorage contract, wrapper interconversion. Adapt message-model boundaries (`convertToLlm`, AgentMessage roles) and compat flag sets to your host vocabulary; adapt the coding-agent fork's auth-bearing summarizer options if your host owns auth outside the model registry. Omit product planes: tui component kit and server/client/protocol RPC remain unmined seams; the sqlite-node FTS search-backend plane is deferred behind the storage contract.
