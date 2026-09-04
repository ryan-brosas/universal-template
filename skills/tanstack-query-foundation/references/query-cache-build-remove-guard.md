<!-- capsule-v2 -->
# QueryCache build/remove identity guard — what stops removal races from deleting a newer replacement?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** When a stale GC or removeQueries lands after the same hash was rebuilt, how does the store avoid deleting the WRONG object?

## hash-keyed Map with identical-reference delete guard
**Path/Symbol:** `packages/query-core/src/queryCache.ts:QueryCache` (:92–223), QueryStore interface (:82–88).
**Signature:** `build(client, options, state?): Query` (get-or-create by queryHash), `remove(query)` , `clear()` batched, `find/findAll(filters)`.
**Data Shape:** private `#queries: QueryStore` (Map<queryHash, Query> default); notify events typed union incl. observerAdded/Removed/ResultsUpdated/OptionsUpdated.

### Decisive source
```ts
remove(query: Query): void {
  const queryInMap = this.#queries.get(query.queryHash)
  if (queryInMap) {
    query.destroy()
    if (queryInMap === query) {          // ← identity guard
      this.#queries.delete(query.queryHash)
    }
    this.notify({ type: 'removed', query })
  }
}
add(query): void {
  if (!this.#queries.has(query.queryHash)) {   // first-wins add
    this.#queries.set(query.queryHash, query)
    this.notify({ type: 'added', query })
  }
}
```

**Flow:** build(): existing hash returns the SAME instance (dedupe point for every observer/client call); otherwise construct with `client.defaultQueryOptions(options)` + per-key defaults and add(). remove(): ALWAYS destroy the passed query (cancels silent, clears gc), but only delete the map slot if it still maps to that exact object; notify('removed') fires even when the delete was skipped.
**Invariant:** (1) the `queryInMap === query` check is the whole race-safety story — a rebuild between GC-fire and delete would leave the NEW query in the map while only destroying the old one; (2) add is guarded has-first so double-add of different instances cannot clobber (first wins); (3) clear() wraps removes in one notifyManager.batch so N removals notify once; (4) find() defaults `{ exact: true }` while findAll({}) short-circuits to all.
**Probe:** `grep -n "queryInMap === query" packages/query-core/src/queryCache.ts` (:150 exactly once) and `grep -n "exact: true" packages/query-core/src/queryCache.ts packages/query-core/src/mutationCache.ts`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^QueryStore$|^build$", limit: 8 });
```

## Verdict
Adopt the destroy-vs-delete split plus identity guard verbatim in any keyed store whose values can be recreated under the same key. Adapt QueryStore injection point (interface exists for custom storage). Omit config callbacks (onSuccess/onError/onSettled) if your host lacks global hooks. Direct tests: `__tests__/queryCache.test.tsx`.
