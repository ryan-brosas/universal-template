<!-- capsule-v2 -->
# RSC concurrent AI-state updates — why did keyed setters and delta patches drop sibling writes?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** Server AI state lives in ALS-scoped clones updated by jsondiffpatch deltas — which setter forms survive concurrent interleaving?

## Functional-updates-only rule
**Path/Symbol:** `packages/rsc/src/shared-client/context.tsx` — delta patch via functional form (:72–74), keyed update via functional form (:191).
**Signature:** `setAIState((currentState) => patch(clone(currentState), delta))`; `state[1](s => ({...s, [key]: newState}))`.
**Data Shape:** `aiState` is React's `[snapshot, setter]` pair; deltas are jsondiffpatch diffs against the CLIENT's own snapshot.

### Decisive source
```ts
// BEFORE (#19249 root cause): read-modify-write on a stale closure snapshot
aiState[1](jsondiffpatch.patch(jsondiffpatch.clone(aiStateSnapshot), delta));
return state[1]({ ...state[0], [key]: newState });
// AFTER:
setAIState((currentState: any) =>
  jsondiffpatch.patch(jsondiffpatch.clone(currentState), delta));
return state[1](s => ({ ...s, [key]: newState }));
```

**Flow:** every mutation now derives its base INSIDE the setter callback from React's authoritative current state, so two concurrent actions (e.g., two streamed deltas, or a keyed write racing a delta) compose instead of last-writer-wins overwriting the other's contribution.
**Invariant:** Never close over a snapshot as the patch/update BASE — snapshots are for reading; all writes go through functional updater form. This preserves the sealed-on-render ALS contract (see `ai-state-delta-sync.md`) while fixing concurrent-loss.
**Probe:** deterministic probes: `grep -cF "(currentState: any)" packages/rsc/src/shared-client/context.tsx` → `1`; `grep -cF "state[1](s => ({ ...s, [key]: newState }));" packages/rsc/src/shared-client/context.tsx` → `1`. Direct tests: `context.ui.test.tsx` (new 122-line suite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "setAIState jsondiffpatch patch context", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt functional-updater-everywhere for RSC state stores; adapt the cloning strategy; pairs with `ai-state-delta-sync.md` — that capsule owns the wire format, this one owns the write discipline.
