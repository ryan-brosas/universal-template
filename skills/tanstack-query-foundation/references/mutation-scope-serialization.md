<!-- capsule-v2 -->
# MutationCache scope serialization — how do scoped mutations queue-and-chain instead of racing?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How do you make mutations with the same scope.id run one-at-a-time in submission order, including ones that start while offline?

## scope buckets + canRun/runNext handshake
**Path/Symbol:** `packages/query-core/src/mutationCache.ts:MutationCache.canRun` (:160–175), `runNext` (:177–188), private `#scopes: Map<string, Array<Mutation>>`.
**Signature:** `canRun(mutation): boolean`; `runNext(mutation): Promise<unknown>`; scope key = `mutation.options.scope?.id`.
**Data Shape:** Set-bag of all mutations + per-scope arrays; mutationId monotonic counter for build().

### Decisive source
```ts
canRun(mutation) {
  const scope = scopeFor(mutation)
  if (typeof scope === 'string') {
    const mutationsWithSameScope = this.#scopes.get(scope)
    const firstPendingMutation = mutationsWithSameScope?.find((m) => m.state.status === 'pending')
    // we can run if there is no current pending mutation (start use-case)
    // or if WE are the first pending mutation (continue use-case)
    return !firstPendingMutation || firstPendingMutation === mutation
  }
  return true
}
runNext(mutation) {
  const scope = scopeFor(mutation)
  if (typeof scope === 'string') {
    const foundMutation = this.#scopes.get(scope)?.find((m) => m !== mutation && m.state.isPaused)
    return foundMutation?.continue() ?? Promise.resolve()
  }
  return Promise.resolve()
}
```
plus the retryer wiring in Mutation.execute:
```ts
const retryer = createRetryer({
  ...,
  canRun: () => this.#mutationCache.canRun(this),
})
...
if (!retryer.canStart()) /* retryer.start() pauses via pause().then(run) */
```

**Flow:** execute builds a retryer whose canRun consults the cache — when an earlier same-scope mutation is pending, canStart() fails and the retryer STARTS PAUSED (its start() calls pause().then(run)); onPause dispatches 'pause' (isPaused:true). When the running one settles, its finally invokes cache.runNext(this), which continues the FIRST OTHER paused sibling → chain proceeds in insertion order. resumePausedMutations() (focus/online reconnect) fans continue() over ALL paused mutations — the canRun gate re-serializes them, so only the head actually runs.
**Invariant:** (1) serialization lives in canRun, NOT in an explicit queue pop — order emerges from array insertion + find-first-pending semantics ("we are the first pending" lets a resumed head pass); (2) unscoped mutations bypass entirely; (3) remove() maintains #scopes incrementally (splice vs delete-key on last element); (4) offline start: networkMode gates canFetch → paused state BEFORE any request fires, so scoped queues drain automatically on reconnect.
**Probe:** `grep -n "firstPendingMutation === mutation" packages/query-core/src/mutationCache.ts` (:169 once) and `grep -n "resumePausedMutations" packages/query-core/src/mutationCache.ts packages/query-core/src/queryClient.ts | head -4`; direct tests `__tests__/mutationCache.test.tsx` scope-serialization suite.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^runNext$|^scopeFor$", limit: 5 });
```

## Verdict
Adopt the gate-in-retryer pattern for any serialized side-effect queue; it composes with pause/resume for free. Adapt scope identity (id string). Omit dehydration restore nuance (`continue()` re-execute path :165–174) unless porting offline mutations. Direct tests: `__tests__/mutationCache.test.tsx`.
