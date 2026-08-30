<!-- capsule-v2 -->
# State.batch cross-store rebuild batching — how do you register transforms in five different stores inside one boot sequence without paying five full rebuilds per store?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Boot registers dozens of transforms across many independent stores (agents, commands, skills, catalog, integrations). Naively each `transform()` triggers an immediate full rebuild of its store. How do you collapse that into one rebuild per store, run only after the whole registration sequence completes?

## An ambient Context.Reference holding a Set of pending reloads
**Path/Symbol:** `packages/core/src/state.ts` (`CurrentBatch` :29-31, `batch` :33-42, transform's batch branch :107-112 and :119-120, dispose's batch branch :101-105).
**Signature:** `State.batch<A, E, R>(effect: Effect<A, E, R>) → Effect<A, E, R>`; nested `batch` calls are no-ops (the innermost effect reuses the ambient set).
**Data Shape:** `CurrentBatch: Context.Reference<Set<Reload> | undefined>` with default `undefined`; `Reload = () => Effect<void>`.

### Decisive source
```ts
// state.ts:33-42 — one Set for the batch's dynamic extent; reloads run AFTER the effect
export function batch<A, E, R>(effect: Effect.Effect<A, E, R>) {
  return Effect.gen(function* () {
    const current = yield* CurrentBatch
    if (current) return yield* effect          // nested batch: reuse, never double-run
    const reloads = new Set<Reload>()
    const result = yield* effect.pipe(Effect.provideService(CurrentBatch, reloads))
    yield* Effect.forEach(reloads, (reload) => reload(), { discard: true })
    return result
  })
}
```

**Flow:** inside `State.batch`, every `transform()` appends its callback under the semaphore but then adds `reload` to the ambient set INSTEAD of rebuilding (:119-120); every scope-close dispose does the same (:101-105). When the batch effect completes, each distinct store's `reload` runs exactly once (a Set, so N transforms to one store = one rebuild). Outside a batch, transform/dispose rebuild immediately. Nested batches are structurally impossible to double-batch because the inner call sees the ambient set and passes through.
**Invariant:** no rebuild is observable until the batch effect finishes; each store rebuilds at most once per batch regardless of how many transforms/disposes touched it; the reload set is keyed by store identity (each State instance contributes its own `reload` closure), so batching is per-store, not global; a transform registered inside a batch is still fully durable — the batch only defers WHEN the rebuild runs.
**Probe:** `packages/core/test/state.test.ts` "batches automatic rebuilds" (:81-114): two independent State instances each with a finalize counter; three transforms inside one `State.batch` assert `finalized === 0` INSIDE the effect, then `finalized === 2` after, with each store's values exactly the replayed result. Source pin:
```bash
grep -c 'CurrentBatch' packages/core/src/state.ts   # expect 5
grep -c 'State.batch' packages/core/test/state.test.ts # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "State.batch CurrentBatch reload set deferred rebuild registration boot", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ambient-batch pattern: a dynamically-scoped set of deferred reload closures, deduplicated per store, drained after the batched effect. Adapt the Context.Reference mechanism to whatever dynamic-scoping your runtime offers (AsyncLocalStorage, thread-locals); omit Effect's service plumbing. Coverage caveat: Codebase Memory MCP not connected this session — Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
