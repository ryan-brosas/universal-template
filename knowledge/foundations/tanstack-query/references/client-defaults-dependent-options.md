<!-- capsule-v2 -->
# Client defaultQueryOptions dependent rules — which defaults depend on other options, and why is _defaulted idempotent?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** Where do derived option values get computed, and how does defaulting stay referentially stable across renders and recursive calls?

## three-layer spread + dependent derivations
**Path/Symbol:** `packages/query-core/src/queryClient.ts:defaultQueryOptions` (:624–703); twin `defaultMutationOptions` (:705–718).
**Signature:** `defaultQueryOptions(options): DefaultedQueryObserverOptions` — memoized by `options._defaulted === true`.
**Data Shape:** layers: global `#defaultOptions.queries` → per-key `getQueryDefaults(queryKey)` (insertion-ordered partialMatchKey fold via Object.assign) → caller options.

### Decisive source
```ts
if (options._defaulted) return options            // idempotent fast path

const defaultedOptions = {
  ...this.#defaultOptions.queries,
  ...this.getQueryDefaults(options.queryKey),
  ...options,
  _defaulted: true,
}
if (!defaultedOptions.queryHash) {
  defaultedOptions.queryHash = hashQueryKeyByOptions(defaultedOptions.queryKey, defaultedOptions)
}
// dependent default values
if (defaultedOptions.refetchOnReconnect === undefined)
  defaultedOptions.refetchOnReconnect = defaultedOptions.networkMode !== 'always'
if (defaultedOptions.throwOnError === undefined)
  defaultedOptions.throwOnError = !!defaultedOptions.suspense
if (!defaultedOptions.networkMode && defaultedOptions.persister)
  defaultedOptions.networkMode = 'offlineFirst'
if (defaultedOptions.queryFn === skipToken)
  defaultedOptions.enabled = false
return defaultedOptions
```

**Flow:** every API entry (build/fetchQuery/useBaseQuery/getQueryData...) funnels through here exactly once per options object; downstream code may then READ invariants instead of re-deriving them.
**Invariant:** (1) `_defaulted` short-circuit makes the function safe under recursion (fetch → build → defaultQueryOptions with already-defaulted options) and gives render-path reference stability; (2) dependent rules are ORDERED after hashing because networkMode affects nothing earlier but persister→offlineFirst must land before any consumer reads networkMode; (3) getQueryDefaults folds key-prefix defaults in REGISTRATION order — later matching registrations win individual keys (Object.assign), not whole objects; (4) skipToken as queryFn implies disabled — the type system's escape hatch for conditional queries is enforced at runtime here.
**Probe:** `grep -n "_defaulted" packages/query-core/src/queryClient.ts` (:655/:669/:708/:709 ≥4 hits) and `grep -n "offlineFirst" packages/query-core/src/queryClient.ts` (:689).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^getQueryDefaults$", limit: 3 });
```

## Verdict
Adopt single-defaulting-funnel + explicit dependent-rule block for any options-heavy API; keep the boolean stamp on the object itself rather than a WeakMap so it serializes through devtools. Adapt the four dependent rules to your feature set — the PATTERN is the payload. Direct tests: `__tests__/queryClient.test.tsx` default-function suite.
