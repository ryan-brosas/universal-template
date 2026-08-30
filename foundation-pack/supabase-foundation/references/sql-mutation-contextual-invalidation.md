<!-- capsule-v2 -->
# SQL mutation contextual invalidation — how does one DDL mutation invalidate exactly the right slice of the query cache while emitting telemetry?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** After a schema-mutating SQL statement succeeds, how do I sweep every stale cached query for that project without nuking unrelated caches, and where does telemetry fit so a parser bug can never fail the mutation?

## useExecuteSqlMutation onSuccess/onError choreography
**Path/Symbol:** `apps/studio/data/sql/execute-sql-mutation.ts:224-284` (`useExecuteSqlMutation`; ignore list :24; cost threshold constants :32-33).
**Signature:** `useExecuteSqlMutation({onSuccess, onError, ...options})` → `useMutation<ExecuteSqlData, QueryResponseError, ExecuteSqlMutationVariables>` with internal `mutationFn: (args) => executeSql(args)`.
**Data Shape:** Variables extend executeSql's with `autoLimit?`, `contextualInvalidation?: boolean`. Invalidation targets every live cache entry whose key starts `['projects', projectRef]` minus keys containing any ignore substring.

### Decisive source
```ts
const INVALIDATION_KEYS_IGNORE = ['branches', 'settings-v2', 'addons', 'custom-domains', 'content']
const COST_THRESHOLD = 200_000
export const COST_THRESHOLD_ERROR = 'Query cost exceeds threshold'

async onSuccess(data, variables, context) {
  const { contextualInvalidation, sql, projectRef } = variables
  try {
    const tableEvents = sqlEventParser.getTableEvents(sql)
    tableEvents.forEach((event) => {
      if (projectRef) track(event.type, {
        method: 'sql_editor',
        schema_name: event.schema,
        table_name: event.tableName,
      }, { project: projectRef })
    })
  } catch (error) {
    console.error('Failed to parse SQL for telemetry:', error)
  }

  const sqlLower = sql.toLowerCase()
  const isMutationSQL =
    sqlLower.includes('create ') || sqlLower.includes('alter ') || sqlLower.includes('drop ')
  if (contextualInvalidation && projectRef && isMutationSQL) {
    const databaseRelatedKeys = queryClient.getQueryCache()
      .findAll({ queryKey: ['projects', projectRef] })
      .map((x) => x.queryKey)
      .filter((x) => !INVALIDATION_KEYS_IGNORE.some((a) => x.includes(a)))
    await Promise.all(
      databaseRelatedKeys.map((key) => queryClient.invalidateQueries({ queryKey: key }))
    )
  }
  await onSuccess?.(data, variables, context)
},
async onError(data, variables, context) {
  if (onError === undefined) toast.error(`Failed to execute SQL: ${data.message}`)
  else onError(data, variables, context)
}
```

**Flow:** mutation success → telemetry parse (fail-soft try/catch — a malformed SQL string logs but never rejects) → DDL heuristic on lowercase substrings → if opted in via `contextualInvalidation`: enumerate the whole query cache under the `['projects', ref]` prefix, subtract the five ignore families, invalidate all matches concurrently → caller onSuccess last. Failure path: caller onError or default toast.
**Invariant:** telemetry failure is contained (its own try/catch); invalidation only fires when ALL THREE of contextualInvalidation opt-in, projectRef present, and DDL-substring match hold; the ignore-list filter runs on the serialized key array (substring containment), which is why the keys factory must root everything at `['projects', projectRef, ...]`; caller callbacks run AFTER the sweep completes (`await Promise.all(...)` precedes `await onSuccess?.(...)`).
**Probe:** no dedicated upstream test for this hook at pin — caveat recorded; probe by construction: seed react-query with keys `['projects','r','tables']`, `['projects','r','branches,x']`, `['projects','r2','x']`, run the hook's onSuccess path with `contextualInvalidation: true, sql: 'create table t()'` and assert only non-ignored `r`-scoped keys invalidated.
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "supabase", function_name: "supabase.apps.studio.data.sql.execute-sql-mutation.useExecuteSqlMutation", direction: "inbound", depth: 1 });
```

## Verdict
Adopt the prefix-sweep-plus-denylist invalidation as the pattern for coarse schema-change coherence, and the fail-soft telemetry wrapper around any best-effort side effect inside a success path. Adapt the DDL heuristic (substring matching is deliberately loose — tighten per host) and the ignore list to your cache topology. Omit Supabase's specific key vocabulary ('branches'/'content'/etc.) — port the MECHANISM, re-derive the denylist from your own key factory.
