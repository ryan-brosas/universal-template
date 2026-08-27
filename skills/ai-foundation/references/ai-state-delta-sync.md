<!-- capsule-v2 -->
# AI-state ALS + delta sync — how does server AI state flow to the client as jsondiffpatch deltas under AsyncLocalStorage?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do `getMutableAIState`/`getAIState` scope per-request, and what crosses the wire?

## ai-state.tsx + createAI + InternalAIProvider
**Path/Symbol:** `packages/rsc/src/ai-state.tsx` (:15-210); action wrapper `rsc/src/provider.tsx:createAI/innerAction` (:20-149); client context `rsc/src/shared-client/context.tsx:InternalAIProvider` (:22-125).
**Signature:** `withAIState({state, options}, fn)`; `getAIState(key?)`; `getMutableAIState(key?) → {get, update, done(final?)}`; `sealMutableAIState()`; `getAIStateDeltaPromise()`.
**Data Shape:** ALS store `{currentState (deep-cloned working copy), originalState, sealed, options, mutationDeltaPromise?}`; wire payload = `[deltaPromise, result]` where delta is a jsondiffpatch diff of original→current.

### Decisive source
```ts
// per-request isolation — multiple concurrent AI requests each get their own store:
const asyncAIStateStorage = new AsyncLocalStorage<{currentState, originalState, sealed, options, ...}>();
// mutation accumulates on a CLONE; delta computed against the ORIGINAL:
store.currentState = newState;
// done(): resolve the delta promise — this is what serializes to the client:
const delta = jsondiffpatch.diff(store.originalState, store.currentState);
store.mutationDeltaResolve!(delta);
// actions return [deltaPromise, result] and seal AFTER the action body:
const result = await action(...args);
sealMutableAIState();               // later getMutableAIState() calls throw
return [getAIStateDeltaPromise(), result];
// client applies the delta against ITS OWN snapshot (three-way convergence):
aiState[1](jsondiffpatch.patch(jsondiffpatch.clone(aiStateSnapshot), delta));
```

**Flow:** createAI wraps EVERY action with `wrapAction` (binds `{action, options}` ahead of the state arg) → invoke: client passes its current aiState snapshot as first arg → withAIState clones it into ALS → action reads/mutates via get(Mutable)AIState (keyed variants require object state; sealed ⇒ throw with "move it to the top level" remediation) → done computes + resolves delta → client wrapper awaits result FIRST, patches state from the delta ASYNC (fire-and-forget IIFE :69-79), returns result immediately. `onSetAIState` fires per update with `{key, state, done}` for persistence. The optional `onGetUIState` server hook returns UI state + optionally mutates AI state for initial-render sync; `<AI>` server component detects client execution via `'useState' in React` and throws.
**Invariant:** mutations MUST land before the action returns (seal) — async callbacks spawned by the action can no longer mutate. The client patches its OWN snapshot, not the server's original: concurrent actions converge via snapshot-anchored diffs instead of clobbering.
**Probe:** `packages/rsc/src/ai-state.test.ts:49/:55` ("throw an error when accessing AI state outside of withAIState" / "...after it has been sealed"), `:64` (onSetAIState fired), `:80` (updates with and without key).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "withAIState getMutableAIState sealMutableAIState createAI jsondiffpatch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ALS scoping, clone-vs-original delta accounting, seal-on-return, and snapshot-anchored client patching. Adapt diff library and persistence hooks to your stack. Omit nothing behavioral.
