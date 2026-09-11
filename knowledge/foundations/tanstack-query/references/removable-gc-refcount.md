<!-- capsule-v2 -->
# Removable GC refcount base — what keeps live entries alive and evicts exactly when idle?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How is time-based eviction coordinated with observer refcounting so a cache entry dies only after being idle for gcTime — without weakrefs?

## Removable abstract base
**Path/Symbol:** `packages/query-core/src/removable.ts:Removable` (:6–40); subclass hooks `Query.optionalRemove` (query.ts :226–230), `Mutation.optionalRemove` (:155–163).
**Signature:** `protected scheduleGc(): void; protected updateGcTime(newGcTime?: number): void; protected clearGcTimeout(): void; destroy(): void; protected abstract optionalRemove(): void`.
**Data Shape:** `gcTime!: number`; private `#gcTimeout?: ManagedTimerId`.

### Decisive source
```ts
protected scheduleGc(): void {
  this.clearGcTimeout()
  if (isValidTimeout(this.gcTime)) {
    this.#gcTimeout = timeoutManager.setTimeout(() => { this.optionalRemove() }, this.gcTime)
  }
}
protected updateGcTime(newGcTime: number | undefined): void {
  // Default to 5 minutes (Infinity for server-side) if no gcTime is set
  this.gcTime = Math.max(
    this.gcTime || 0,
    newGcTime ?? (environmentManager.isServer() ? Infinity : 5 * 60 * 1000),
  )
}
// Query.optionalRemove:
if (!this.observers.length && this.state.fetchStatus === 'idle') {
  this.#cache.remove(this)
}
// add/removeObserver bracket:
addObserver   → this.clearGcTimeout()
removeObserver→ if (!this.observers.length) { ...cancel logic...; this.scheduleGc() }
```

**Flow:** constructor schedules GC immediately (hydrate/setQueryData entries with no observers die on schedule); first addObserver cancels the timer; last removeObserver re-arms it; fetch completion re-schedules (`finally { this.scheduleGc() }`). optionalRemove double-checks liveness (zero observers + idle fetch) before removing.
**Invariant:** (1) gcTime update is MAX-monotonic per instance (`Math.max(this.gcTime || 0, ...)`) — a later observer with smaller gcTime cannot shorten an armed timer's window, but the timer itself IS rescheduled with the stored value on next arm; (2) isValidTimeout rejects Infinity/negatives → gcTime: Infinity means never collected (server default); (3) eviction is cooperative: the timer only REQUESTS removal; the subclass decides if it's still safe — that's why a query mid-fetch survives its own gc tick; (4) Mutation variant re-arms instead of removing while status pending (in-flight mutations are immortal until settled).
**Probe:** `grep -n "scheduleGc()" packages/query-core/src/query.ts | head -4` (constructor :189 + finally :629 + removeObserver :378) and `grep -n "Math.max" packages/query-core/src/removable.ts` (:26).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^Removable$|^optionalRemove$", limit: 5 });
```

## Verdict
Adopt the timer+refcount bracket for any entry cache with TTL semantics. Adapt defaults (5min/Infinity) and liveness predicate. Omit server-awareness if single-runtime. Direct tests: gc behavior suites inside `__tests__/queryCache.test.tsx` / `queryClient.test.tsx`.
