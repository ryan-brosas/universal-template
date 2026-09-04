<!-- capsule-v2 -->
# executeSql guard ladder — what stands between user SQL and Postgres: size caps, EXPLAIN cost preflight, impersonation line rewinding, and the no-results sentinel?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** Before running arbitrary user SQL through a metadata API, which client-side guards must run, in what order, and how do role-impersonation wrappers distort error line numbers and empty results?

## executeSql guard ladder
**Path/Symbol:** `apps/studio/data/sql/execute-sql-mutation.ts:76-220` (`executeSql`); sentinel contract in `packages/pg-meta/src/sql/studio/role-impersonation.ts:26-57` (`ROLE_IMPERSONATION_SQL_LINE_COUNT = 11`, `ROLE_IMPERSONATION_NO_RESULTS`, `getImpersonationSQL`).
**Signature:** `export async function executeSql<T = any>({projectRef, connectionString, sql, queryKey, handleError, isRoleImpersonationEnabled, isStatementTimeoutDisabled, preflightCheck}, signal?, headersInit?, fetcherOverride?): Promise<{ result: T }>`.
**Data Shape:** Input SQL is a branded `SafeSqlFragment`; output is always `{ result }` — errors either throw (default) or are converted by a caller-supplied `handleError` that returns `{ result: any }`. Cost rejections carry `metadata: {cost, sql}`.

### Decisive source
```ts
const sqlSize = new Blob([sql]).size
// [Joshen] I think the limit is around 1MB from testing, but its not exactly 1MB it seems
if (sqlSize > 0.98 * MB) throw new Error('Query is too large to be run via the SQL Editor')

let headers = new Headers(headersInit)
if (connectionString) headers.set('x-connection-encrypted', connectionString)

if (preflightCheck) {
  // intentionally omitted error handling: NOT blocking the UI if preflight fails
  const { data: costCheck } = await post('/platform/pg-meta/{ref}/query', {
    ...options,
    body: { query: `explain ${sql}`, disable_statement_timeout: isStatementTimeoutDisabled },
    params: { ...options.params, query: { key: 'preflight-check' } },
  })
  const summary = !!costCheck ? calculateSummary(createNodeTree(costCheck)) : undefined
  if ((summary?.totalCost ?? 0) >= COST_THRESHOLD /* 200_000 */) {
    return handleErrorFetchers({ message: COST_THRESHOLD_ERROR, code: cost, metadata: { cost, sql } })
  }
}
```
```ts
// Role-impersonation post-fixes:
// error side — rewind LINE n by the wrapper's fixed height:
const regex = /LINE (\d+):/im
updatedError.error.replace(regex, `LINE ${lineNumber - ROLE_IMPERSONATION_SQL_LINE_COUNT}:`)
// success side — collapse the marker row:
if (isRoleImpersonationEnabled && Array.isArray(data) &&
    data?.[0]?.[ROLE_IMPERSONATION_NO_RESULTS] === 1) return { result: [] as T }
```

**Flow:** projectRef required → Blob byte-size ≤ 0.98 MB → build headers (+`x-connection-encrypted`) → optional EXPLAIN preflight (own request tagged `key=pre-flight-check`; failure never blocks; cost ≥ 200_000 rejects via handleErrorFetchers with `{cost, sql}` metadata) → main POST to `QUERY_SOURCE_REGISTRY.database.endpoint` with `key` built from string/number queryKey segments → on error: impersonation mode rewrites every `LINE n:` down by 11 in both `error` and `formattedError`, then caller handleError or default throw → on success: impersonation marker row collapses to `[]`.
**Invariant:** the pg-meta wrapper prepends exactly 11 lines before user SQL (pinned by `ROLE_IMPERSONATION_SQL_LINE_COUNT = 11` and the `getImpersonationSQL` template), so Postgres error line numbers and formattedError line refs must both be rewound by the same constant or users see shifted diagnostics; the marker row (`select 1 as "ROLE_IMPERSONATION_NO_RESULTS";` placed BEFORE user SQL so pg-meta falls back to it only when user SQL returns nothing) must be checked at index `[0]` and only when impersonation is enabled.
**Probe:** no dedicated upstream unit test for executeSql at this pin (the database-queues infinite-query test mocks executeSql — consumer-side only) — caveat recorded; probe by construction: call executeSql with a 1 MB SQL string and assert the size-cap Error fires before any fetch; simulate an impersonated error body `'LINE 14: ...'` and assert post-fix yields `'LINE 3: ...'`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "executeSql preflight role impersonation", limit: 10 });
```

## Verdict
Adopt the guard ORDER (cheap local throws first, network preflight second, main call last), the fail-open preflight posture, the paired rewind-both-fields + marker-row-collapse impersonation contract, and the constant-coupling between client rewind and SQL wrapper height (keep them in one package or pin them with a shared test). Adapt the endpoint path, cost threshold (200_000 tuned to Supabase sizing guidance in-source), and application-name header values to your host. Coverage: `no_recorded_issue + metadata_match` @ gen 2026-08-25T19:56:24Z.
