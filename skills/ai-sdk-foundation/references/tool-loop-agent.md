<!-- capsule-v2 -->
# ToolLoopAgent — how do you wrap generateText/streamText into an agent class without breaking callback layering, defaults, or attribution?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** How does the agent merge settings-layer and call-layer callbacks, inject its loop default, and tag requests so usage attributes to the agent?

## prepareCall: strip, default, override
**Path/Symbol:** `packages/ai/src/agent/tool-loop-agent.ts:ToolLoopAgent.prepareCall` (80–178); class doc lists loop terminations at :28–38.
**Signature:** `prepareCall({prompt?, messages?, options?})` → validates `options` against optional `callOptionsSchema` via `validateTypes`, then spreads `settingsWithoutCallbacks` + `{stopWhen: this.settings.stopWhen ?? isStepCount(20)}` + call options.
**Data Shape:** callbacks destructured OUT of settings (`onStart…onEnd`) so they never leak into the base args; returned object is re-split into prompt fields (`instructions/allowSystemInMessages/messages/prompt`), `runtimeContext`, and the rest.

### Decisive source
```ts
const baseCallArgs = {
  ...settingsWithoutCallbacks,
  stopWhen: this.settings.stopWhen ?? isStepCount(20),
  ...options,
};
```
(tool-loop-agent.ts:130–134, verbatim)

```ts
private agentHeaders(preparedCall: { headers?: unknown }): Record<string, string> {
  return withUserAgentSuffix(
    (preparedCall.headers as Record<string, string | undefined>) ?? {},
    'ai-sdk-agent/tool-loop',
  );
}
```
(:185–192)

**Flow:** constructor normalizes `onEnd = onFinish ?? onEnd` → per call: schema-validate user options → build base = agent defaults overridden by call options → run user's `prepareCall` hook if present → split into `{callArgs, runtimeContext?, promptArgs}` → in `generate()`/`stream()`: merge EACH callback as `mergeCallbacks(settingsCallback ?? deprecatedAlias, callCallback)` and pass `agentHeaders(preparedCall)` LAST so the header wins the spread.
**Invariant:** (1) The agent-level default is `isStepCount(20)`, NOT streamText's 1 — porting the wrapper without its own default silently caps agents at a single step. (2) Callbacks merge TWO layers (agent settings × call options) with the stable-name-first lookup (`onStart ?? experimental_onStart`), and `mergeCallbacks` runs them via `Promise.allSettled` — errors from one listener are swallowed by design, never propagated. A porter "fixing" that error-swallowing changes agent semantics. (3) UA suffix CHAINS: `withUserAgentSuffix` appends `ai-sdk-agent/tool-loop` after existing headers, then downstream adds `ai/<version>` and provider suffixes — attribution survives multi-hop wrapping only because each layer APPENDS rather than replaces. Caller-provided UA is preserved (:152–162 test).
**Probe:** `tool-loop-agent.test.ts:142` ("should tag the user-agent with the agent identifier"), `:152` caller-UA preservation; loop-termination contract pinned by 4245-line suite incl. approval-pause paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", name_pattern: "^ToolLoopAgent\\.", detail: "ids" });
await mcp.codebase_memory.search_graph({ project: "ai", query: "mergeCallbacks allSettled", limit: 5 });
```
(`merge-callbacks.ts:19–25`: `await Promise.allSettled(callbacks.map(async cb => { await cb?.(event); }))` — parallel, settle-tolerant.)

## Verdict
Adopt the strip-default-override preparation order, two-layer allSettled callback merging, the agent-owned step budget (20), and append-style UA attribution. Adapt the settings surface to your host option names; keep deprecated-alias resolution (`newName ?? oldName`). Omit `create-agent-ui-stream*` siblings unless porting chat UIs. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2; decisive ranges read at HEAD this session.
