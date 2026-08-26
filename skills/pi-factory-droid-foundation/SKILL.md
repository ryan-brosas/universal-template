---
name: pi-factory-droid-foundation
description: "Use when bridging an external CLI coding agent (Factory Droid or any subprocess-backed agent harness) into a host LLM runtime: pooling long-lived agent sessions per conversation without cross-contamination, surviving a process-wide provider registry whose closures lie about caller identity, translating foreign agent event streams onto host assistant-message blocks, converting session-cumulative token counters into honest per-turn usage, keeping auto-compact in sync with the remote harness's own context meter, and running host-executed tools inside the remote agent's own loop via a suspension bridge (rendezvous board, name aliasing, turn FSM, result envelopes). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# pi-factory-droid: Factory Droid provider runtime foundation

## Use this for
Use when bridging an external CLI coding agent (Factory Droid or any subprocess-backed agent harness) into a host LLM runtime: pooling long-lived agent sessions per conversation without cross-contamination, surviving a process-wide provider registry whose closures lie about caller identity, translating foreign agent event streams onto host assistant-message blocks, converting session-cumulative token counters into honest per-turn usage, keeping auto-compact in sync with the remote harness's own context meter, and running host-executed tools inside the remote agent's own loop via a suspension bridge (rendezvous board, name aliasing, turn FSM, result envelopes). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/droid-session-pool-lifecycle.md` — how do I pool foreign agent subprocesses per conversation and tear them down safely?
- `references/caller-runtime-affinity.md` — how do I resolve the true caller when the provider registry shares one streamFn across conversations?
- `references/dual-mode-stream-dispatch.md` — how do I route turns through two bridge modes (host-tools MCP vs native agent) over one session pool?
- `references/droid-event-translate.md` — how do I map a foreign delta stream onto host content blocks without duplicates or dangling blocks?
- `references/cumulative-usage-baseline.md` — how do I convert session-cumulative token counters into truthful per-turn usage?
- `references/context-window-sync.md` — how do I stop host auto-compaction from firing before the remote harness compacts?
- `references/autonomy-permission-ladder.md` — how do autonomy levels map to confirmation outcomes without nagging per step?
- `references/host-context-forwarding.md` — how does host persona/memory/skills context ride into a bridged external agent?
- `references/pi-tools-bridge-rendezvous-board.md` — how do an agent's tool calls meet host results delivered on a LATER request, whichever arrives first?
- `references/pi-tools-name-map-aliasing.md` — how do I resolve one logical tool across systems that rename, re-case, or prefix it?
- `references/suspend-inside-mcp-handler.md` — how do I suspend a host tool call inside a remote agent loop without polling?
- `references/native-tool-suppression-allowlist.md` — how do I stop a hybrid agent from using its native tools when a bridge owns them?
- `references/pi-tools-turn-fsm.md` — how do I structure a multi-request turn where the assistant message pauses mid-turn awaiting tool results?
- `references/trailing-toolresult-envelope.md` — how do I harvest just the newest tool results from a message history?
- `references/json-schema-to-zod-shape.md` — how do I feed JSON-Schema tool parameters to a zod-typed SDK validator?
- `references/tools-fingerprint-invalidation.md` — how do I detect "the tool set changed" cheaply and rebuild only what depends on it?

## Capsule map
- **Session pool kernel** — `droid-session-pool-lifecycle`: pool keyed `sha256(apiKey):conversationId:mode`; contextHash/toolsHash invalidation recreates sessions; LRU cap + idle-TTL sweeper + best-effort exit hook; destroy ordering aborts consumers before closing transports.
- **Caller identity resolution** — `caller-runtime-affinity`: per-call sessionId resolves the bound InstanceRuntime; unbound ids still re-key the pool so histories never merge.
- **Bridge-mode dispatch** — `dual-mode-stream-dispatch`: mode split at stream entry; pi-tools continuation delivers results into hanging MCP handlers; superseded turns are aborted+rejected; errors (not aborts) destroy the pooled entry.
- **Event translation** — `droid-event-translate`: `messageId:blockIndex` keys dedup text/thinking block creation; open-key sets close every block exactly once; Result.isError throws.
- **Usage baseline math** — `cumulative-usage-baseline`: per-turn = max(0, cumulative − baseline); thinkingTokens fold into output; finalize advances baseline from cumulative snapshot else accumulated deltas; preferLastCall keeps max output.
- **Context-window synchronization** — `context-window-sync`: write the remote meter's effective limit back into model.contextWindow; totalTokens = meter `used`, else min(prompt-side tokens, window).
- **Permission autonomy ladder** — `autonomy-permission-ladder`: autoLevel → ProceedAutoRun{Low,Medium,High} short-circuits UI prompts; PI_DROID_PROMPT_ALWAYS forces prompting; no UI ⇒ Cancel.
- **Host-context forwarding** — `host-context-forwarding`: AGENTS.md + tiered skills catalog rendered into a `<host-context>` preamble prepended to the first turn after (re)creation only.

### Pi-tools bridge plane (pass 2)
- **Rendezvous board** — `pi-tools-bridge-rendezvous-board`: four maps (pending-by-id, early-results-by-id, waiters-by-name, buffered-ids-by-name) make handler-first and id-first races non-lossy; teardown RESOLVES with isError text instead of rejecting.
- **Name alias maps** — `pi-tools-name-map-aliasing`: every wire spelling (sanitized, lowercased, `server___tool`, prefix-stripped) maps back to the ORIGINAL tool name; unknown ⇒ undefined, never throw.
- **Suspension as MCP handler** — `suspend-inside-mcp-handler`: each host tool registers as an agent-side MCP tool whose handler is one awaited promise over the board — no polling, survives across requests on the pooled session; empty content degrades to one empty text block.
- **Native-tool suppression** — `native-tool-suppression-allowlist`: disable list = complement of (escape-hatch tool + bridged ids + own-server prefix) computed FROM the live catalog; event-time `isOurTool` re-check is the real gate.
- **Turn FSM** — `pi-tools-turn-fsm`: idle→streaming→awaiting-results on the POOLED entry; continuation delivers results then re-arms a FRESH output envelope on the same turn; supersede = abort consumer + rejectAll before nulling; exactly one ended stream per request.
- **Result envelope** — `trailing-toolresult-envelope`: backward scan collects trailing toolResult rows to the assistant boundary, order-preserving, idempotent, never emits empty content arrays.
- **Schema back-fill** — `json-schema-to-zod-shape`: enum beats type, required-set drives `.optional()`, only arrays recurse, objects flatten to record(unknown), unknown types degrade to z.unknown().
- **Tool-set fingerprint** — `tools-fingerprint-invalidation`: order-normalized sha256 over name+description+parameters; mismatch destroys the whole pool entry so session+board+MCP server rebuild as one consistent unit.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-factory-droid (MIT), `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory project `pi-factory-droid` (full index @ generation 2026-08-25T19:58:03Z, 336 nodes / 907 edges; no parse_partial, no skipped files; `.git/` excluded by design).

## Full view (memory graph)
Revalidate `pi-factory-droid` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: pool key composition and invalidation hashing, baseline-subtraction usage math, context-window write-back, autonomy→outcome ladder, keyed block translation. Adapt the transport specifics (`@factory/droid-sdk` session API, Pi `AssistantMessageEventStream`, `ToolConfirmationOutcome` enum values) to your host. Omit the product behaviors: the Chinese-language preamble copy, Factory-specific model discovery via throwaway sessions, and the `PI_DROID_*` env-var names unless you keep their semantics.
