<!-- capsule-v2 -->
# QueryObserver select + placeholderData memoization — how do derived results stay stable across renders?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How can a per-render select() transform and a placeholderData fallback avoid producing new references (and new renders) every time createResult runs?

## memo latches inside createResult
**Path/Symbol:** `packages/query-core/src/queryObserver.ts:createResult` (:451–620) with fields `#selectFn/#selectResult/#selectError`, `#lastQueryWithDefinedData`, `#currentResultState/#currentResultOptions`.
**Signature:** `createResult(query, options): QueryObserverResult` — pure-ish; mutates only its own memo slots.
**Data Shape:** result object with ~25 boolean/data fields; isStale computed via module-level `isStale(query, options)` helper.

### Decisive source
```ts
// use placeholderData if needed
if (options.placeholderData !== undefined && data === undefined && status === 'pending') {
  let placeholderData
  if (prevResult?.isPlaceholderData &&
      options.placeholderData === prevResultOptions?.placeholderData) {
    placeholderData = prevResult.data
    // we have to skip select when reading this memoization
    // because prevResult.data is already "selected"
    skipSelect = true
  } else {
    placeholderData = typeof options.placeholderData === 'function'
      ? options.placeholderData(this.#lastQueryWithDefinedData?.state.data, this.#lastQueryWithDefinedData)
      : options.placeholderData
  }
  if (placeholderData !== undefined) {
    status = 'success'; data = replaceData(prevResult?.data, placeholderData, options); isPlaceholderData = true
  }
}
// Select data if needed — this also runs placeholderData through the select function
if (options.select && data !== undefined && !skipSelect) {
  if (prevResult && data === prevResultState?.data && options.select === this.#selectFn) {
    data = this.#selectResult                       // memo hit: same data ref + same fn ref
  } else {
    try { this.#selectFn = options.select; data = options.select(data);
          data = replaceData(prevResult?.data, data, options); this.#selectResult = data; this.#selectError = null }
    catch (selectError) { this.#selectError = selectError }
  }
} else if (data === undefined) {
  // a stored select error belongs to previously selected data; once that
  // data is gone (query switch or reset), it must not leak into this result
  this.#selectError = null
}
```

**Flow:** placeholder branch memoizes on (isPlaceholderData flag + placeholderData option identity) → skipSelect prevents double-selecting an already-selected value. Select branch memoizes on (data reference equality against the state snapshot captured at last updateResult + select fn identity); errors are CAPTURED into #selectError rather than thrown, then converted into a synthetic error result (`status:'error'`, data falls back to #selectResult, errorUpdatedAt=now).
**Invariant:** (1) select identity matters — inline arrow selects recompute each render but still converge because data-reference memo dominates; (2) select errors do NOT propagate synchronously; they ride the normal notify path as an error result (and throwOnError decides boundary behavior downstream); (3) stale-select-error hygiene: cleared whenever data becomes undefined so a query switch can't inherit the previous key's select failure; (4) placeholderData functions receive keepPreviousData-style input via #lastQueryWithDefinedData (the most recent query that HAD data), not the current one.
**Probe:** `grep -n "skipSelect" packages/query-core/src/queryObserver.ts` (:502/:520/:547 exactly 3) and `grep -n "selectError" packages/query-core/src/queryObserver.ts | head -4`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^createResult$|^getOptimisticResult$", limit: 5 });
```

## Verdict
Adopt both memo latches for any observer-style view layer with user transforms. Adapt the error-capture semantics to your boundary strategy. Omit placeholder plumbing if unsupported. Direct tests: `__tests__/queryObserver.test.tsx` (1,937 lines incl. dedicated select-memo suites).
