<!-- capsule-v2 -->
# Post-sampling hook registry — why does a synchronous-looking "run all hooks" loop swallow every error?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the minimal internal registry contract for programmatic (non-settings) lifecycle hooks fired after each model response?

## postSamplingHooks module registry
**Path/Symbol:** `src/utils/hooks/postSamplingHooks.ts` (whole file, 70L): `REPLHookContext` type, module-level array `postSamplingHooks`, `registerPostSamplingHook`, `clearPostSamplingHooks`, `executePostSamplingHooks`.
**Signature:** `(hook: (context: REPLHookContext) => Promise<void> | void) => void`; `executePostSamplingHooks(messages, systemPrompt, userContext, systemContext, toolUseContext, querySource?): Promise<void>`.
**Data Shape:** `REPLHookContext = { messages; systemPrompt; userContext; systemContext; toolUseContext; querySource? }` — the same context object stopHooks saves as the cache-safe params snapshot (shared type via import).

### Decisive source
```ts
for (const hook of postSamplingHooks) {
  try { await hook(context) }
  catch (error) { logError(toError(error)) }  // Log but don't fail on hook errors
}
```

**Flow:** query.ts fires it `void`-style right after streaming completes IF any assistant messages exist (:999-1009) — fire-and-forget relative to the tool phase; sequential execution in registration order; registration happens programmatically (internal API, "not exposed in settings.json config (yet)").
**Invariant:** (1) one hook throwing must not skip later hooks NOR propagate — post-sampling observers are advisory; (2) the call site passes `[...messagesForQuery, ...assistantMessages]` (turn-local view), NOT the live history array; (3) contrast with stop hooks (query/stopHooks.ts): those run at TERMINATION, CAN block continuation, and stream progress to the UI — post-sampling hooks are silent mid-turn observers. Choosing the wrong layer is the classic porter mistake.
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `cat src/utils/hooks/postSamplingHooks.ts | grep -c "catch"` → 1 (the swallow); `grep -n "executePostSamplingHooks(" src/query.ts` pins the void call.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "registerPostSamplingHook REPLHookContext", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the try-per-hook observer loop and the context shape; adapt registration surface (settings vs programmatic); omit if you have no mid-turn observers. Porting trap: reusing this swallow-all pattern for STOP hooks removes the user's only lever over runaway agents.
