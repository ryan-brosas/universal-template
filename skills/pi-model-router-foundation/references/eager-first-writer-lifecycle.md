<!-- capsule-v2 -->
# Eager first-writer-wins initialization + turn-end model enforcement — how do you lazily initialize from any available context while protecting against subagent overwrites and keeping the virtual model selected?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** In a host where `session_start` may never fire (subagent contexts), how do you ensure the extension is initialized before the first LLM call, without a subagent's context clobbering the parent's valid state?

## First-writer-wins registry capture + turn-end router-model re-assertion
**Path/Symbol:** `extensions/index.ts:ensureInitializedFromContext` (:454–461), `turn_end` handler (:501–511), `model_select` handler capacity-refresh block (:479–488).
**Signature:** `ensureInitializedFromContext(ctx: ExtensionContext): void` (closure); turn_end handler: `async (_event, ctx) => Promise<void>`.
**Data Shape:** Guards on `!currentModelRegistry` (undefined = not yet initialized). Once set, the registry reference is sticky for the lifetime of the closure. Turn-end checks `routerEnabled && selectedProfile && ctx.model?.provider !== 'router'` to detect drift.

### Decisive source
```ts
// Eagerly initialize the model registry from any event that provides
// ExtensionContext. In subagent contexts (e.g. pi-dynamic-workflows),
// session_start may never fire, but turn_start/model_select fire before every LLM
// call — including the first call to the router provider's streamSimple.
// Only set when not already initialized: if extensions share instances across
// parent/subagent sessions, always overwriting would replace the parent's valid
// registry with the subagent's — which goes stale when the subagent ends.
const ensureInitializedFromContext = (ctx: ExtensionContext) => {
  if (!currentModelRegistry) {
    currentModelRegistry = ctx.modelRegistry;
    lastExtensionContext = ctx;
    currentCwd = ctx.cwd;
    actions.reloadConfig(ctx);
  }
};

// turn_end: enforce router model stays selected
pi.on('turn_end', async (_event, ctx) => {
  ensureInitializedFromContext(ctx);
  if (routerEnabled && selectedProfile && ctx.model?.provider !== 'router') {
    const routerModel = ctx.modelRegistry.find('router', selectedProfile);
    if (routerModel) {
      await setModelInternally(routerModel);  // force-switch back
    }
  }
  persistState();
  actions.updateStatus(ctx);
});
```

**Flow:** Any of the 4 event handlers (turn_start, model_select, turn_end, thinking_level_select) calls `ensureInitializedFromContext` first. If registry is still undefined (first call in this closure instance), it captures ctx's registry, cwd, and reloads config. Subsequent calls are no-ops (registry already set). At turn_end, if the router is enabled but the current model has drifted to a non-router provider (user switched mid-turn, another extension changed it), the handler force-switches back to the router profile model via `setModelInternally` (which sets the guard flag, so the resulting model_select event is ignored). The model_select handler also refreshes stale capacities: if the registry's contextWindow/maxTokens differ from what's currently displayed, it re-applies the model to force a TUI refresh.
**Invariant:** The first context to arrive wins the registry slot; subsequent contexts (subagents) NEVER overwrite it; the router model is re-asserted at every turn boundary if it was externally displaced; capacity drift triggers a silent re-apply without user notification.
**Probe:** `extensions/index.test.ts` :577–601 (first ctx initializes + reloads config; second ctx with different cwd does NOT trigger setStatus — proves no overwrite), :154–184 (turn_end after model drift to openai/gpt-4o → setModel called with router/balanced), :501–535 (turn_end when router disabled → setModel NOT called).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "ensureInitializedFromContext currentModelRegistry turn_end setModelInternally", limit: 10 });
```

## Verdict
Adopt the first-writer-wins lazy init pattern verbatim for any extension that must work in both top-level and subagent contexts; adopt the turn-end re-assertion for any virtual/alias model that must stay selected; adapt the "drift detection" condition to your host's model-change semantics; omit the 50ms setTimeout (used elsewhere in this file for registry sync) if your host's registration is synchronous. The comment block at :447–453 is the design rationale — preserve it when porting.
