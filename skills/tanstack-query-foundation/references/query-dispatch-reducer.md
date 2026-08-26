<!-- capsule-v2 -->
# Query dispatch reducer — which state fields does each action own, and what does an error do to existing data?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** What is the exact transition table for query state, including the counter fields nobody remembers to reset?

## #dispatch reducer over 8 actions
**Path/Symbol:** `packages/query-core/src/query.ts:#dispatch` (:633–715) + helpers `fetchState` (:718), `successState` (:739), `getDefaultState` (:749).
**Signature:** private `#dispatch(action: Action)` where Action ∈ failed|fetch|success|error|invalidate|pause|continue|setState.
**Data Shape:** QueryState {data, dataUpdateCount, dataUpdatedAt, error, errorUpdateCount, errorUpdatedAt, fetchFailureCount, fetchFailureReason, fetchMeta, isInvalidated, status, fetchStatus}.

### Decisive source
```ts
case 'success': {
  const newState = {
    ...state,
    ...successState(action.data, action.dataUpdatedAt),   // data, dataUpdatedAt=??Date.now(), error:null, isInvalidated:false, status:'success'
    dataUpdateCount: state.dataUpdateCount + 1,
    ...(!action.manual && { fetchStatus: 'idle', fetchFailureCount: 0, fetchFailureReason: null }),
  }
  // If fetching ends successfully, we don't need revertState as a fallback anymore.
  // For manual updates, capture the state to revert to it in case of a cancellation.
  this.#revertState = action.manual ? newState : undefined
  return newState
}
case 'error':
  return {
    ...state,
    error,
    errorUpdateCount: state.errorUpdateCount + 1,
    errorUpdatedAt: Date.now(),
    fetchFailureCount: state.fetchFailureCount + 1,
    fetchFailureReason: error,
    fetchStatus: 'idle',
    status: 'error',
    // flag existing data as invalidated if we get a background error
    isInvalidated: true,
  }
```
and the notification tail:
```ts
this.state = reducer(this.state)
notifyManager.batch(() => {
  // Keep the current iteration stable if an observer unsubscribes synchronously while it is being notified.
  this.observers.slice().forEach((observer) => { observer.onQueryUpdate() })
  this.#cache.notify({ query: this, type: 'updated', action })
})
```

**Flow:** fetch→spread fetchState (+meta); pause/continue flip ONLY fetchStatus; failed sets failure counters; success clears failures+invalidation (manual setData keeps fetchStatus untouched AND latches revertState); invalidate just flips the flag; setState is the escape hatch used by hydration/reset.
**Invariant:** (1) error NEVER touches `data` — background refetch errors preserve last-good data and mark it stale (isInvalidated:true unconditionally, since no-data was already stale); (2) manual success (setQueryData) does NOT idle the fetchStatus — an in-flight refetch stays in flight over your optimistic write; (3) observers are notified over a SLICE copy because unsubscribe-during-notify must not skip/repeat siblings; (4) initialData seeds status:'success' WITHOUT incrementing counts (isFetched() stays false until a real fetch).
**Probe:** `grep -n "observers.slice()" packages/query-core/src/query.ts` (:709 exactly once) and `grep -n "revertState = action.manual" packages/query-core/src/query.ts` (:673).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^successState$|^getDefaultState$", limit: 5 });
```

## Verdict
Adopt the reducer table wholesale — it encodes five years of issue-driven edge cases (#652-class). Adapt action names; keep ownership boundaries per field. Mutation has a parallel reducer (`mutation.ts` :339–407) with pending/success/error/pause/continue/failed — same pattern, no data-staleness flag. Direct tests: `__tests__/query.test.tsx`.
