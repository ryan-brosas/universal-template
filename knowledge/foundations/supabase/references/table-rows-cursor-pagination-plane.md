<!-- capsule-v2 -->
# Table-rows cursor-pagination plane — how does a dashboard grid fetch every row of a large table without crashing the SQL endpoint, and which errors are worth retrying?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What pagination, ordering, throttling, and retry machinery stands between a "fetch all rows" request and the pg-meta query endpoint, and how is the impersonation sentinel cleaned off the accumulated result?

## Eligibility ladder + SQL composition (`data/table-rows/table-rows-query.ts`)
**Path/Symbol:** `apps/studio/data/table-rows/table-rows-query.ts` : `getPreferredOrderByColumns` (:41-70), `checkIfCtidAvailable` (:117-120), `getAllTableRowsSql` (:122-202), `formatFilterValue` (`./utils.ts` :8-21).
**Signature:** `getAllTableRowsSql({ table, filters?, sorts? }): { sql: QueryFilter; cursorColumns: string[] | false }`.
**Data Shape:** cursor eligibility ladder — primary key columns first (a keyset on them guarantees uniqueness), then unique indexes whose columns are ALL non-null; non-eligible fallback = sortable columns excluding json types. ctid tie-breakers are only legal for TABLE / PARTITIONED_TABLE / MATERIALIZED_VIEW. Filters with empty values are dropped before composition. Numeric filter values are coerced to numbers only when finite and within MAX_SAFE_INTEGER (temporary-fix comment in utils).

### Decisive source
```ts
if (sorts.length === 0) {
  if (cursorPaginationEligible.length > 0) {
    cursorColumns = cursorPaginationEligible[0]
    cursorPaginationEligible[0].forEach((col) => {
      queryChains = queryChains.order(table.name, col)
    })
    // Cursor paginated columns do not require ctid fallback as they
    // guarantee uniqueness
  } else if (cursorPaginationNonEligible.length > 0) {
    queryChains = queryChains.order(table.name, cursorPaginationNonEligible[0])
    if (hasCtid) {
      queryChains = queryChains.order(table.name, 'ctid')
    }
  }
}
// user sorts: append tie-breaker so page order doesn't shuffle
const tieBreaker = cursorPaginationEligible[0]
if (tieBreaker) {
  const sortedColumns = new Set(sorts.filter((s) => s.table === table.name).map((s) => s.column))
  tieBreaker.filter((col) => !sortedColumns.has(col)).forEach((col) => {
    queryChains = queryChains.order(table.name, col)
  })
}
```

**Flow:** build one base Query chain (from → select `*` plus enum-array columns cast `${ident(name)}::text[]` → filters → orders) ONCE, then per page either clone it and add a tuple keyset filter `(cols) > (lastRowValues)` (cursor mode) or apply `range(from, to)` (offset mode). User sorts always get a uniqueness tie-breaker appended from the eligible keyset minus already-sorted columns, else ctid — so page order never shuffles between fetches.
**Invariant:** offset pagination over an unordered or non-uniquely-ordered table double-skips/duplicates rows under concurrent writes; the tie-breaker rule (unique keyset first, ctid second, never both when the keyset already guarantees uniqueness) is what makes paging stable.
**Probe:** no direct upstream test for the SQL composition (the module test covers only `executeWithRetry`); confirmed by direct read at the pin.

## Paged fetch loop + 429-only retry ladder
**Path/Symbol:** same file : `executeWithRetry` (:93-115), `getErrorCode` (:72-78), `getRetryAfter` (:80-91), `fetchAllTableRows` (:210-310), marker strip at :309.
**Signature:** `executeWithRetry<T>(fn: () => Promise<T>, maxRetries = 3, baseDelay = 1000): Promise<T>`; `fetchAllTableRows({ projectRef, connectionString, table, filters?, sorts?, roleImpersonationState?, progressCallback? }): Promise<any[]>`.
**Data Shape:** rowsPerPage = 500, THROTTLE_DELAY = 500ms between pages, progress callback receives the running row count. Retry delay = `retryAfter * 1000` when present (from `ResponseError.retryAfter` or `headers.get('retry-after')` parseInt) else `baseDelay * 2^attempt`. Error code read from `ResponseError.code` for the typed error, else `error.status` — the duck-typed dual shape from pass-1's error taxonomy.

### Decisive source
```ts
export async function executeWithRetry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn()
    } catch (error: unknown) {
      const errorCode = getErrorCode(error)
      if (errorCode === 429 && attempt < maxRetries) {
        const retryAfter = getRetryAfter(error)
        const delayMs = retryAfter ? retryAfter * 1000 : baseDelay * Math.pow(2, attempt)
        await timeout(delayMs)
        continue
      }
      throw error
    }
  }
  throw new Error('Max retries reached without success')
}
// ... per page:
const query = wrapWithRoleImpersonation(
  queryChainsWithCursor.range(0, rowsPerPage - 1).toSql(),
  roleImpersonationState
)
const { result } = await executeWithRetry(async () =>
  executeSql({ projectRef, connectionString, sql: query })
)
// final line of fetchAllTableRows:
return rows.filter((row) => row[ROLE_IMPERSONATION_NO_RESULTS] !== 1)
```

**Flow:** IS_PLATFORM without a connection string ⇒ console.error + return [] (fail soft); otherwise loop pages: wrap each page's SQL with the current impersonation state (pass-1 contract), execute through the retry ladder, accumulate, throttle, stop when a short page arrives; finally strip every row carrying the `ROLE_IMPERSONATION_NO_RESULTS === 1` sentinel — the client-side half of the no-results marker contract.
**Invariant:** only 429 is retried — any other error class (including statement timeouts) must surface immediately or a long export silently hangs. The sentinel strip belongs to the CONSUMER of wrapped SQL: any plane that accumulates results across wrapped queries must filter the marker row itself, because the wrapper injects it into every result set.
**Probe:** `apps/studio/data/table-rows/table-rows-query.test.ts` (pure vitest, read whole; unexecutable in-lane — standing block) pins all four retry behaviors: success-once, two 429s then success = 3 calls, max-retries exhaustion rethrows the 429 after initial+retries calls, non-429 throws immediately with exactly 1 call.

## Grid query consumer edge cases
**Path/Symbol:** same file : `getTableRows` (:325-398), `useTableRowsQuery` (:400-428).
**Signature:** `useTableRowsQuery<TData>({ projectRef, tableId, ...args }, options?): UseQueryResult<TableRowsData, ResponseError, TData>`.
**Data Shape:** MS-SQL foreign-table edge case — equality-filter columns are excluded from default sort columns because the Postgres planner may drop sorts redundant with filters, producing invalid MS SQL syntax. `preflightCheck` is deliberately EXCLUDED from the queryKey (in-source [Ali] comment: it controls how the query executes — whether an EXPLAIN guard runs first — not what data is returned). enabled gate: defined projectRef ∧ tableId ∧ (!IS_PLATFORM || connectionString defined).

### Decisive source
```ts
// [Ali] Exclude preflightCheck from query key — it controls how the query
// executes (whether an EXPLAIN guard runs first), not what data is returned.
const { preflightCheck, ...queryKeyArgs } = args
```

**Flow:** prefetchTableEditor → parseSupaTable → compose via pg-meta's `getTableRowsSql` → wrapWithRoleImpersonation → executeSql carrying `isRoleImpersonationEnabled` + preflightCheck → catch handleError (pass-1 taxonomy).
**Invariant:** execution-mode flags never belong in cache keys; data-shape arguments always do. A flag that changes HOW not WHAT poisons cache identity and causes duplicate in-flight work.
**Probe:** no dedicated upstream test for getTableRows/useTableRowsQuery (consumer of executeSql); confirmed by direct read at the pin.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct whole-file reads plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "fetchAllTableRows executeWithRetry getAllTableRowsSql cursorPaginationEligible", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full ladder: unique-keyset-first ordering with ctid second, clone-per-page keyset filtering vs range fallback, fixed page size + inter-page throttle, 429-only retry with retryAfter-preferred backoff, consumer-side sentinel stripping, and execution-mode flags kept out of cache keys. Adapt page size/throttle to your endpoint's rate profile and the connection-string gate to your deployment topology. Omit the MS-SQL foreign-table sort exclusion unless you federate heterogeneous backends. Caveat carried from source: the in-file TODO admits this untruncated fetch will crash the pg-meta side on very big tables (Blob cap) — port the graceful-error hint (suggest pg_dump-style extraction) rather than the crash.
