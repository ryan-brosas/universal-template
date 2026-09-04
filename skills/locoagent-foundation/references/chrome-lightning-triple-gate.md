<!-- capsule-v2 -->
# Triple-gated agent loop — how do you ship an internal-only LLM-driven browser_task tool so external builds never even advertise it?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What does it take to run a lightning-mode agent loop inside the MCP server, with inference injected from the host CLI?

## chrome-lightning-triple-gate
**Path/Symbol:** `src/utils/claudeInChrome/mcpServer.ts` (`callAnthropicMessages` injection :152-217; gate comment :152-169).
**Signature:** `callAnthropicMessages(req: {model, max_tokens, system, messages, stop_sequences?, signal?}): Promise<{content: TextBlock[], stop_reason: string|null, usage}>` — spread into `ClaudeForChromeContext` only when `process.env.USER_TYPE === 'ant'`.
**Data Shape:** implemented over host's `sideQuery` (handles OAuth attribution fingerprint, proxy, model betas); response filtered to text blocks only; typed against UNPUBLISHED 0.4.0 package types while CI installs 0.3.0.

### Decisive source
```ts
// Ant-only: the extension's lightning_turn is build-time-gated via
// import.meta.env.ANT_ONLY_BUILD — the whole lightning/ module graph is
// tree-shaken from the public extension build (build:prod greps for a
// marker to verify). Without this injection, the Node MCP server's
// ListTools also filters browser_task + lightning_turn out, so external
// users never see the tools advertised. Three independent gates.
```
and inside the sideQuery call:
```ts
// tools: [] is load-bearing — without it Sonnet emits
// <function_calls> XML before the text commands. Original
// lightning-harness.js (apps repo) does the same.
tools: [],
skipSystemPromptPrefix: true,
```

**Flow:** gate 1 = extension build tree-shakes the lightning module graph (`ANT_ONLY_BUILD`, verified by a grep in build:prod); gate 2 = MCP server's ListTools filters `browser_task`/`lightning_turn` unless inference is injected; gate 3 = this context spread is ant-env-only. At runtime the server runs its agent loop in Node and calls the extension's `lightning_turn` once per iteration for execution; each loop iteration is one `sideQuery` with the CLI system-prompt prefix suppressed (the lightning prompt is complete alone) and NO tools declared.
**Invariant:** all three gates must fail closed independently — removing any single one leaks the tool (build marker grep catches gate 1 regressions). The empty-tools call shape is a MODEL-behavior invariant: declaring tools makes Sonnet prepend XML function-call syntax to what must be pure text commands.
**Probe:** no upstream test. Deterministic pins: `grep -n "Three independent gates" src/utils/claudeInChrome/mcpServer.ts` → :161; `grep -n "is load-bearing" src/utils/claudeInChrome/mcpServer.ts` → :186.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "callAnthropicMessages sideQuery chrome_mcp", limit: 10 });
```

## Verdict
Adopt the defense-in-depth gating pattern for internal-only tools and the no-tools-declared text-command call shape. Adapt model specifics. Omit unpublished-type plumbing once the dep publishes. Coverage caveat: no unit tests; behavior documented via in-source comments pinned verbatim.
