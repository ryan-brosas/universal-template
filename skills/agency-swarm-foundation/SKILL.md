---
name: agency-swarm-foundation
description: "Use when porting multi-agent orchestration machinery from agency-swarm: synchronous send-message bus, per-agent tool concurrency guards, flow-wiring validation, runtime subagent registries, flat thread stores with pair-scoped history, guardrail retry loops, handoff reminders, deferred OAuth MCP activation, loop-affine proxies, fake-id stream normalization."
disable-model-invocation: true
---

# Agency-Swarm Foundation

## Use this for
Use when building or refining a multi-agent orchestration layer in Python: an LLM-visible delegation tool that routes by schema enum and blocks per (thread, recipient), one-call-at-a-time tool guards over inert counters, declarative communication-flow validation that fails loud on duplicates, class-keyed send_message registries with live schema mutation, one flat transcript filtered into global-user vs bilateral-agent threads, an ordered history-sanitization ladder before model replay, output-guardrail retries that grow history instead of dying, handoff transfers that stay attributed and ordered in shared history, model-triggered OAuth MCP activation with per-user tool scoping, event-loop-affine MCP proxies with cancel disambiguation, stable-id synthesis over placeholder stream ids, and fingerprint-gated conversation-starter replay. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/send-message-bus.md` — synchronous agent-to-agent delegation: pending-set backpressure, errors-as-tool-results, parent-run-id plumbing.
- `references/tool-concurrency-guard.md` — wrap-on-add two-tier guard (busy latch + sequential flag) rejecting violations as error strings.
- `references/flow-wiring-validation.md` — parse_agent_flows duplicate taxonomy (default-pair vs custom vs same-class) + always-give-a-route fallback.
- `references/runtime-subagent-registry.md` — AgentRuntimeState-keyed tools shared BY REFERENCE; add_recipient mutates enum AND description roster.
- `references/flat-thread-store.md` — metadata-filtered projections: callerAgent-None = ONE global user thread; agent pairs match BOTH directions.
- `references/history-sanitization-ladder.md` — repair → strip → id-dedup order; mixed history protocols raise, never coerce.
- `references/guardrail-retry-loop.md` — output tripwires append feedback and retry on grown history; input tripwires fail open as final text.
- `references/handoff-reminder-filter.md` — Literal-schema-unified handoffs; reminder stamped timestamp+1 with full caller attribution.
- `references/deferred-mcp-oauth.md` — startup never blocks on OAuth discovery; shielded mid-run conversion; owner-scoped tool storage.
- `references/loop-affine-mcp-proxy.md` — replace-with-proxy so every call site inherits background-loop affinity; TimeoutError/CancelledError relabeling.
- `references/fake-id-stream-normalization.md` — (run_id, output_index)-keyed stable ids; call_id precedence; kind-deque pairing for run-item events.
- `references/starter-cache-replay.md` — exact preconditions for cached first replies; any override bypasses; fingerprint mismatch invalidates.
- `references/send-message-extra-params.md` — three-pattern subclass param discovery with MRO-wide reserved names; degrade-not-crash merge.
- `references/instructions-sandwich-trace.md` — shared→base→additional composition with mandatory restore; regex-gated trace-id inheritance.

## Capsule map
- **Inter-agent messaging** — `send-message-bus`: SendMessage FunctionTool whose params enum IS the routing table; one in-flight message per (thread_manager, recipient); every failure returns a string the calling LLM can read.
- **Tool execution control** — `tool-concurrency-guard`: ToolConcurrencyManager busy-latch blocks ALL tools while a one_call tool runs; active-count tracks plain tools; guards attached at EVERY add path.
- **Topology wiring** — `flow-wiring-validation`: flows parse into (unique pairs, per-pair class lists, default-pair set); ≤1 SendMessage subclass per pair, many Handoffs OK; undeclared pairs still get the fallback route.
- **Runtime registration** — `runtime-subagent-registry`: recipients/pending/lock live on AgentRuntimeState shared by reference; late registration rewrites the tool schema in place.
- **Conversation storage** — `flat-thread-store`: single flat list; embedded agent/callerAgent metadata drives pair-scoped replay; insertion order is semantic order.
- **History hygiene** — `history-sanitization-ladder`: last-assistant-only tool_calls, null-content synthesis, replay-artifact id drops, store:false reasoning includes — in THAT order.
- **Validation & recovery** — `guardrail-retry-loop`: validation_attempts counts retries; same MasterContext, grown history; other failures wrapped in AgentsException naming cause type.
- **Control transfer** — `handoff-reminder-filter`: transfer_to_<name> tools with strict recipient_agent Literal schema; system reminder persisted with attribution + timestamp+1; runtime handoff alignment save/restored per execution.
- **MCP integration** — `deferred-mcp-oauth`: reserved authenticate_mcp_server tool activates OAuth servers model-triggered; scoped_oauth_mcp_tools discards tools on user switch.
- **MCP integration** — `loop-affine-mcp-proxy`: persistent servers proxied onto their owning loop; caller cancellation vs server-side cancel disambiguated via task.cancelling().
- **Streaming fidelity** — `fake-id-stream-normalization`: __fake_id__ placeholders get deterministic msg_<run>_<seq> ids; argument deltas inherit the recorded call_id; storage never keeps the placeholder.
- **Latency economics** — `starter-cache-replay`: warmup thread pre-bakes canned first replies; five-condition gate (user-only, first message, simple text, no overrides) plus fingerprint invalidation.
- **Tool authoring** — `send-message-extra-params`: ExtraParams class > extra_params_model attr > inline Field() declarations; only FieldInfo-or-Ellipsis defaults count; base annotations reserved.
- **Prompt assembly** — `instructions-sandwich-trace`: shared+base joined \n\n, additional appended after --- separator when shared exists; original instructions restored in finally even on early failure.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
agency-swarm (MIT), `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory project `ext-agency-swarm` (full mode, 10,431 nodes / 40,559 edges, generation 2026-08-23T09:20:58Z, generation_matches true; parse_partial limited to docs/CSS/demo-asset files outside every cited range).

## Full view (memory graph)
Revalidate `ext-agency-swarm` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the framework-neutral supervision contracts: backpressure sets, concurrency counters, flow-validation taxonomy, flat-store projections, sanitization ordering, retry-with-grown-history, id normalization, fingerprint caches. Adapt context plumbing (MasterContext/AgencyContext/AgentRuntimeState shapes), provider-specific repairs, and MCP client calls to your host. Omit the OpenAI Agents SDK substrate (Runner, Handoff objects, hosted tools), FastAPI/realtime/UI product surface, and OpenAI pricing plumbing unless you target the same SDK.
