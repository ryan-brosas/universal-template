<!-- capsule-v2 -->
# Tracked-prop Proxy notification gate — how do unused result properties stop triggering re-renders?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How can an observer notify ONLY when a property the consumer actually read has changed — without compile-time instrumentation?

## trackResult Proxy + shouldNotifyListeners filter
**Path/Symbol:** `packages/query-core/src/queryObserver.ts:trackResult` (:259–270), `updateResult` notify gate (:622–678), `#trackedProps` field (:66).
**Signature:** `trackResult(result, onPropTracked?): QueryObserverResult` — Proxy recording reads; `trackProp(key)` adds to `#trackedProps`.
**Data Shape:** `#trackedProps = Set<keyof QueryObserverResult>`; options.notifyOnChangeProps ('all' | Array | fn) overrides.

### Decisive source
```ts
trackResult(result, onPropTracked?) {
  return new Proxy(result, {
    get: (target, key) => {
      this.trackProp(key as keyof QueryObserverResult)
      onPropTracked?.(key)
      return Reflect.get(target, key)
    },
  })
}
// inside updateResult, AFTER shallowEqualObjects(nextResult, prevResult) early-return:
const { notifyOnChangeProps } = this.options
const notifyOnChangePropsValue = typeof notifyOnChangeProps === 'function' ? notifyOnChangeProps() : notifyOnChangeProps
if (notifyOnChangePropsValue === 'all' || (!notifyOnChangePropsValue && !this.#trackedProps.size)) {
  return true
}
const includedProps = new Set(notifyOnChangePropsValue ?? this.#trackedProps)
if (this.options.throwOnError) includedProps.add('error')
return Object.keys(this.#currentResult).some((key) => {
  const changed = this.#currentResult[key] !== prevResult[key]
  return changed && includedProps.has(key)
})
```

**Flow:** render wraps the result in the tracking Proxy (useBaseQuery returns `observer.trackResult(result)`); component reads `.data` → 'data' enters #trackedProps; later updates run updateResult → if ANY field changed but NONE of the tracked (or explicitly listed) fields changed, listeners are skipped while #currentResult still updates (getCurrentResult stays fresh for next render). QueriesObserver.#trackResult propagates each accessed prop to ALL sibling observers so multi-query hooks stay synchronized (#7000).
**Invariant:** (1) notification suppression is per-update, not sticky: untracked changes still mutate currentResult — a later render always sees truth; only listener wake-ups are gated; (2) throwOnError force-adds 'error' so boundaries never miss a thrown error even when untracked; (3) 'all'/explicit-array bypasses tracking entirely (v5 replaced v4's opt-out footgun); (4) shallowEqualObjects gate runs FIRST — zero-diff updates cost nothing.
**Probe:** `grep -n "trackProp" packages/query-core/src/queryObserver.ts | head -2` (:265/:272) and `grep -n "observer.trackProp(accessedProp)" packages/query-core/src/queriesObserver.ts` (:213); binding-side wrap: `grep -n "trackResult(result)" packages/react-query/src/useBaseQuery.ts` (:141).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^trackResult$|^getOptimisticResult$", limit: 5 });
```

## Verdict
Adopt read-tracking for fat result objects in any framework bridge. Adapt to host reactivity (Vue could use computed getters instead of a Proxy). Omit the fn-form notifyOnChangeProps unless exposing it. Direct tests: queryObserver.test.tsx notifyOnChangeProps suites.
