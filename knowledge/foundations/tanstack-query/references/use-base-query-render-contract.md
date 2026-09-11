<!-- capsule-v2 -->
# useBaseQuery render-phase binding contract — what must a framework binding do in render vs effect order?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** In what exact order must getOptimisticResult, subscription, setOptions, suspense, and error-boundary throws happen for a correct store binding?

## useBaseQuery ordering
**Path/Symbol:** `packages/react-query/src/useBaseQuery.ts:useBaseQuery` (:26–143); core helpers `shouldSuspend`/`fetchOptimistic` (`react-query/src/suspense.ts`) + `getHasError` (errorBoundaryUtils.ts).
**Signature:** `useBaseQuery(options, Observer, queryClient?): QueryObserverResult` — shared by useQuery/useInfiniteQuery.
**Data Shape:** `_optimisticResults: 'optimistic' | 'isRestoring' | undefined` stamped onto defaulted options pre-subscription.

### Decisive source
```ts
const [observer] = React.useState(() => new Observer(client, defaultedOptions))
// note: this must be called before useSyncExternalStore
const result = observer.getOptimisticResult(defaultedOptions)
React.useSyncExternalStore(
  React.useCallback((onStoreChange) => {
    const unsubscribe = shouldSubscribe
      ? observer.subscribe(notifyManager.batchCalls(onStoreChange))
      : noop
    // Update result to make sure we did not miss any query updates between creating the observer and subscribing to it.
    observer.updateResult()
    return unsubscribe
  }, [observer, shouldSubscribe]),
  () => observer.getCurrentResult(),
  () => observer.getCurrentResult(),   // server snapshot = same source
)
React.useEffect(() => { observer.setOptions(defaultedOptions) }, [defaultedOptions, observer])
if (shouldSuspend(defaultedOptions, result)) {
  throw fetchOptimistic(defaultedOptions, observer, errorResetBoundary)   // promise → Suspense
}
if (getHasError({ result, errorResetBoundary, throwOnError, query, suspense })) {
  throw result.error                                                       // → ErrorBoundary
}
return !defaultedOptions.notifyOnChangeProps ? observer.trackResult(result) : result
```

**Flow:** observer created once via lazy useState → optimistic result computed IN RENDER (so first paint already reflects an imminent fetch via fetchState overlay) → subscribe with batched onStoreChange + immediate updateResult catch-up → options reconciliation deferred to EFFECT (never during render — it can trigger fetches/notifies) → render-phase THROW of the optimistic promise for suspense / result.error for boundaries (React re-renders after resolution) → final return wrapped in the tracking Proxy.
**Invariant:** (1) getOptimisticResult BEFORE subscribing both seeds currentResult and assigns it (shouldAssignObserverCurrentProperties gate in queryObserver :794–812) so useSyncExternalStore's first snapshot matches; (2) server snapshot fn = client snapshot fn — SSR renders never subscribe; (3) suspense/error throws must be AFTER effect-time option sync is scheduled but evaluated on CURRENT result — that's why shouldSuspend reads the optimistic result captured at render start; (4) fetchOptimistic races the query's own fetch against a cache-subscription promise so a parallel fetch resolves the suspension without a duplicate request.
**Probe:** `grep -n "before useSyncExternalStore" packages/react-query/src/useBaseQuery.ts` (:94 comment, once) and `grep -n "throw fetchOptimistic" packages/react-query/src/useBaseQuery.ts` (:123).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^useBaseQuery$", limit: 3 });
```

## Verdict
Adopt the ORDER (create → optimistic-read → subscribe+catch-up → effect-setOptions → conditional throws → tracked return) as the checklist for porting to Solid/Svelte/Vue. Adapt primitives: useSyncExternalStore→host store hook, batchCalls→host batching. Omit isRestoring/suspense branches if unsupported. Direct tests live in react-query __tests__ (not executed this window — no installed deps).
