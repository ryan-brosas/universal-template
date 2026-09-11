<!-- capsule-v2 -->
# replaceData structural-sharing policy gate — when is sharing skipped, customized, or crash-guarded?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How does a data-write funnel honor user opt-outs and custom sharing functions without letting a broken comparator corrupt the cache?

## replaceData three-arm gate
**Path/Symbol:** `packages/query-core/src/utils.ts:replaceData` (lines 402–425); call sites `Query.setData` (query.ts :236) and `QueryObserver.createResult` (select + placeholder outputs).
**Signature:** `replaceData<TData>(prevData: TData|undefined, data: TData, options: {structuralSharing?: boolean | ((prev?: TData, next: TData) => TData)}): TData`.
**Data Shape:** options-driven; throws (dev) on non-JSON-serializable data.

### Decisive source
```ts
if (typeof options.structuralSharing === 'function') {
  return options.structuralSharing(prevData, data) as TData
} else if (options.structuralSharing !== false) {
  if (process.env.NODE_ENV !== 'production') {
    try {
      return replaceEqualDeep(prevData, data)
    } catch (error) {
      console.error(
        `Structural sharing requires data to be JSON serializable. ... [${options.queryHash}]: ${error}`,
      )
      // Prevent the replaceEqualDeep from being called again down below.
      throw error
    }
  }
  return replaceEqualDeep(prevData, data)
}
return data
```

**Flow:** custom fn → trusted with full responsibility. Default (undefined/true) → replaceEqualDeep; in dev a throw is logged WITH the queryHash then rethrown so the same bad comparator cannot be silently swallowed twice in one write path. Explicit false → raw `data` (escape hatch for non-JSON payloads like Maps/Dates).
**Invariant:** (1) the rethrow comment is the point — dev builds must surface the error at THIS write instead of degrading into identity churn downstream; production skips the try/catch entirely (perf), accepting that pathological comparators crash later; (2) prevData may be undefined — replaceEqualDeep(undefined, b) returns b via the non-plain-pair arm; (3) BOTH cache writes (setData) and observer-derived writes (select results, placeholderData) route through this single funnel — porters who share only setData lose select stability.
**Probe:** `grep -n "Structural sharing requires" packages/query-core/src/utils.ts` (:414 exactly once) and `grep -c "replaceData(" packages/query-core/src/query.ts packages/query-core/src/queryObserver.ts`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^replaceData$", limit: 3 });
```

## Verdict
Adopt the three-arm gate as the ONLY write funnel for cached values. Adapt the dev guard to your logging stack but keep the rethrow. Omit the function arm if you don't expose custom sharing.
