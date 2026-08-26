---
name: os-clovy-foundation
description: "Use when porting a sandboxed agent-runtime child process that talks to its host over versioned NDJSON JSON-RPC: frame validation, request correlation with abort hygiene, secret-redacted logging, failure classification, group-intact history compaction plus on-demand manual compaction, accept-then-settle run lifecycle with steering and cancellation, identity short-circuits, Auto-model resolution across chat-completions streams, reasoning-field wire-format duality, terminal-vs-model-visible tool error splitting, approval-preflight cache binding, stream-delta forwarding gates, SDK history/usage projection, and durable approval/clarification/secret interruption envelopes. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# os-clovy: Agent Runtime Foundation

## Use this for
Use when porting a sandboxed agent-runtime child process that talks to its host over versioned NDJSON JSON-RPC: frame validation, request correlation with abort hygiene, secret-redacted logging, failure classification, group-intact history compaction plus on-demand manual compaction, accept-then-settle run lifecycle with steering and cancellation, identity short-circuits, Auto-model resolution across chat-completions streams, reasoning-field wire-format duality, terminal-vs-model-visible tool error splitting, approval-preflight cache binding, stream-delta forwarding gates, SDK history/usage projection, and durable approval/clarification/secret interruption envelopes. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Architecture in one paragraph
`agent-runtime` is a Node >=24 child process (`bin: clovy-agent-runtime`) spawned by the Tauri host. `main.ts` wires `process.stdin/stdout` into an `NdjsonRpcPeer`; every inbound frame goes to `RuntimeService.handle`, which owns run lifecycle and delegates model work to an `OpenAIAgentsEngine`. The engine's tools AND its chat-completions model provider call back into the host through reserved RPC tools (`tool.invoke`, `__clovy_model_chat_completions`) — the runtime makes zero direct HTTP calls, so routing, privacy level, and credentials stay host-side.

## Load the matching source dump
- `references/versioned-frame-validation.md` — how must every frame be validated before dispatch?
- `references/rpc-pending-abort-hygiene.md` — how are outbound requests correlated, aborted, and torn down without leaks?
- `references/log-redaction-failure-classification.md` — what may safely reach logs, and how do failures become category/code/retryable triples?
- `references/group-intact-compaction-budget.md` — when does history compact and what is never split or accumulated?
- `references/manual-compaction-rpc.md` — how does on-demand history.compact force-shrink without starting a run, and survive summarizer failure?
- `references/run-lifecycle-accept-settle.md` — what does the host see between run.start and a terminal event?
- `references/identity-question-short-circuit.md` — which inputs answer without any model call?
- `references/auto-model-reasoning-wire.md` — how does one stream serve Auto-model selection and two reasoning field dialects?
- `references/host-tool-execution-error-split.md` — which tool failures are terminal and which go back to the model for self-correction?
- `references/notion-preflight-cache-binding.md` — how does an approval preview stay bound to its exact callId across concurrency, pauses, and pruning?
- `references/sdk-stream-delta-forwarding.md` — which SDK events surface as reasoning/message deltas and which die silently?
- `references/engine-result-history-projection.md` — how are SDK history/usage blobs projected to the wire schema without throwing?
- `references/interruption-envelope-resume.md` — how do approvals survive process death and resume exactly once?
- `references/process-lifecycle-shutdown.md` — how does the child boot, refuse work while dying, and crash honestly?

## Capsule map
- **Protocol frames** — `versioned-frame-validation`: every frame carries `jsonrpc:"2.0"`, `protocolVersion:1`, non-empty `sessionId`/`runId`, safe-integer `sequence ≥ 0`; events differ from requests only by `eventId`.
- **RPC transport** — `rpc-pending-abort-hygiene`: UUID-id pending map; abort listeners removed on settle; transport close rejects all pending with the teardown reason.
- **Log hygiene** — `log-redaction-failure-classification`: depth/breadth-bounded sanitizer plus tagged-cause-chain-first failure classifier producing `{message,category,code,retryable}`.
- **Compaction** — `group-intact-compaction-budget`: trigger at 85% of budget, keep 6 recent groups unless they bust 75%, replace (never stack) prior summaries, deterministic fallback on summarizer failure.
- **Manual compaction** — `manual-compaction-rpc`: forced `history.compact` RPC with no run key; triple-clamped summarize budget; fallback keeps the RPC succeeding during provider outages.
- **Run lifecycle** — `run-lifecycle-accept-settle`: synchronous accept, setImmediate-deferred work, messageId-deduped steering at model boundaries, settle algebra choosing cancelled/interrupted/completed/failed.
- **Identity gate** — `identity-question-short-circuit`: normalized exact-match identity questions reply with zero host calls; attachments opt out.
- **Model streaming** — `auto-model-reasoning-wire`: one canonical resolved model per Auto response; `reasoning_content`↔`reasoning` rename latched per provider; empty tool arguments patched to `"{}"`.
- **Tool error split** — `host-tool-execution-error-split`: tagged `AgentToolExecutionError` is terminal; argument mistakes stay model-visible; generic `tool.failed` text keeps hostile output off the event channel.
- **Approval preflight** — `notion-preflight-cache-binding`: preflight-before-pause keyed `${runId}:${callId}`, consume-once presentation binding with digest, run-scoped prune.
- **Delta forwarding** — `sdk-stream-delta-forwarding`: envelope check + channel-substring ∧ delta-suffix double gate; pass-through ordering, no coalescing.
- **Result projection** — `engine-result-history-projection`: drop-don't-throw SDK history conversion with groupId=callId; camel/snake finite-only usage merged with route + resolvedModel.
- **Interruptions** — `interruption-envelope-resume`: versioned state envelope serialized only when interruptions exist; approve/reject replay through `run.resume`.
- **Process lifecycle** — `process-lifecycle-shutdown`: lazy circular wiring, flag-first-then-abort shutdown with one surviving method, stderr-only fatal reporting.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
os-clovy (MIT, LICENSE present), `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory project `os-clovy` (full mode, generation 2026-08-25T19:59:12Z, 27,651 nodes / 129,709 edges; skipped=0; parse_partial files exist elsewhere in the repo — only `agent-runtime/test/sdk-tool-loop.test.ts` range 6-6 touches this leaf's citations, an import line whose cited ranges were read directly). Pass 1: 8 capsules. Pass 2 (same pin): +6 capsules covering the engine↔host callback plane (`createTool` error split, preflight cache, delta gate, result projection, manual compaction RPC, process lifecycle). Standing block: clarification/rpc-model-provider/sdk-tool-loop/secret-interruption/service suites cannot import `@openai/agents` because node_modules is absent from the read-only checkout; their capsules cite test names as Probes without live runs. No direct test drives SIGTERM/uncaught handlers or the shutdown RPC — `process-lifecycle-shutdown` is source-confirmed only.

## Full view (memory graph)
Revalidate `os-clovy` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the protocol/lifecycle/compaction/redaction contracts and the interruption envelope shape. Adapt the reserved-tool callback transport (`stdio://clovy-host`, `__clovy_*` tool names) and the Clovy identity strings to your own host vocabulary. Omit the Tauri host integration, Notion-specific preflight guardrail, and the June-compat aliases (`juneVersion`, `__june_*` prefixes) unless you inherit that lineage.
