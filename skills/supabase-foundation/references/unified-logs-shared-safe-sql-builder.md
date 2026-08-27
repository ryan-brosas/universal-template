<!-- capsule-v2 -->
# Unified-logs shared safe-SQL builder — how do row-list, chart, facet, and count queries share ONE safe-SQL builder across two dialects behind a flag?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** When a dashboard needs four query shapes (paged rows, severity chart, single-facet counts, sidebar facet counts) over the same filtered log set, in two SQL dialects (ClickHouse/OTEL flat vs legacy BigQuery CTE) behind a feature flag — where does the shared WHERE logic live, and what makes the badges match the list?

## One WHERE compiler feeds all four shapes (`components/interfaces/UnifiedLogs/UnifiedLogs.queries.ts`)
**Path/Symbol:** `apps/studio/components/interfaces/UnifiedLogs/UnifiedLogs.queries.ts` : `buildBaseWhere` (:273-307), `translateFilter` (:129-199), `getUnifiedLogsQuery` (:416-423), `getFacetCountQuery` (:428-471), `getLogsCountQuery` (:479-535), `getLogsChartQuery` (:540-557).
**Signature:** `buildBaseWhere(search, excludeField?): SafeLogSqlFragment[]`; each query fn is `(search) => SafeLogSqlFragment`.
**Data Shape:** every query shape calls the SAME `buildBaseWhere(search, excludeField?)` and AND-joins its result. View-option toggles that are NOT URL filter params (show_connection_logs, edge_auth/edge_storage/edge_postgrest) live INSIDE buildBaseWhere via `applySearchParamsFilter`, so the list, chart, and every facet-count scan hide exactly the same rows — the in-source comment: "Shared by every query via buildBaseWhere, so the row list, chart and sidebar facet counts stay in sync (otherwise the badges over-count by the rows the list hides)". A facet count passes `excludeField = facet` so it EXCLUDES its own filter and can still count its other values (a method=GET filter must not zero out the GET badge).

### Decisive source
```ts
const whereClause = (conditions: SafeLogSqlFragment[]): SafeLogSqlFragment =>
  conditions.length > 0 ? safeSql`WHERE ${joinSqlFragments(conditions, ' AND ')}` : safeSql``

// ...inside getFacetCountQuery (the facet's own filter is excluded via excludeField):
const conditions: SafeLogSqlFragment[] = [
  ...buildBaseWhere(search, facet),
  safeSql`(${facetExpr}) IS NOT NULL AND (${facetExpr}) != ''`,
]
```

**Flow:** parse `filter` URL params → group by column → per-group `translateFilter` → operator inversion for `<>` (IN→NOT IN, LIKE→NOT LIKE, multi-value join OR→AND so a row must match NONE) → append view-option conditions → each query shape wraps the shared conditions in its own SELECT/GROUP BY.
**Invariant:** the WHERE compiler is the SINGLE place that knows which rows are visible; any shape that builds its own WHERE will drift from the list. Excluding a facet's own filter is required for correct badge counts, not optional.
**Probe:** `UnifiedLogs.queries.test.ts` (416L, read whole): "applies the connection-logs filter to every count scan so badges match the list" iterates every UNION ALL branch; "gives the log_type facet its own scan that excludes the log_type filter"; "groups by the requested facet and excludes that facet from the WHERE filters".

## OTEL flat-query constraints force inlined derived columns
**Path/Symbol:** same file : `LOG_TYPE_EXPR` (:67-80), `STATUS_EXPR` (:84-88), `LEVEL_EXPR` (:97-107), `AUTH_USER_EXPR` (:108-114), `ROW_PROJECTION` (:258-271).
**Signature:** module-level `SafeLogSqlFragment` constants — pre-branded CASE expressions.
**Data Shape:** the OTEL endpoint REJECTS subqueries/CTEs and cannot resolve aliases inside countIf when the alias is not in GROUP BY, so every derived column is an INLINED CASE expression repeated at every use site (projection, WHERE, countIf) rather than referenced by alias. `LEVEL_EXPR` checks HTTP status first (gateway/auth rows carry severity_text INFO regardless of response code) with postgres-style severity as fallback. `HTTP_STATUS_EXPR` normalizes auth rows whose status lives under `log_attributes['status']` instead of `response.status_code` — without it every auth 4xx/5xx classifies as success.

### Decisive source
```ts
// SQL expression for derived `level`. Used inline (not as alias reference)
// because the OTEL endpoint can't resolve aliases inside countIf when the
// alias is not in GROUP BY.
const LEVEL_EXPR: SafeLogSqlFragment = safeSql`CASE
      WHEN (${HTTP_STATUS_EXPR}) != '' AND toInt32OrZero((${HTTP_STATUS_EXPR})) >= 500 THEN 'error'
      WHEN (${HTTP_STATUS_EXPR}) != '' AND toInt32OrZero((${HTTP_STATUS_EXPR})) BETWEEN 400 AND 499 THEN 'warning'
      ...
    END`
```

**Flow:** derived-column expressions are built once as branded fragments, then interpolated into projection, WHERE (via translateFilter for level/status/pathname), and chart countIf arms — the same fragment object everywhere, so the derivation can never drift between shapes.
**Invariant:** when your engine rejects subqueries or alias-in-aggregate references, inline the full expression at every use site from ONE branded constant — duplicating the CASE text by hand across shapes is the drift this design prevents.
**Probe:** test pins "does not emit subqueries or CTEs (rejected by the OTEL endpoint)" (regex over WITH/FROM(SELECT/SELECT *) and "buckets auth rows by their log_attributes[status] so 4xx/5xx are not counted as success".

## Count-query scan folding + dialect twin behind a flag
**Path/Symbol:** `UnifiedLogs.queries.ts` : `getLogsCountQuery` scanBlock (:495-514); `UnifiedLogs.queries.bq.ts` (whole-file read) : `buildConditions` (:54-104), `getUnifiedLogsCTE` (:367-382), `getEffectiveLogTypes` (:34-41); `data/logs/logs-endpoint.ts` : `pickLogsQueryBuilder` (:10-11); `data/logs/execute-analytics-sql.ts` : `executeAnalyticsSql` (:40-77).
**Signature:** `pickLogsQueryBuilder<T>(useOtel: boolean, otel: T, bq: T): T`; `executeAnalyticsSql({ projectRef, endpoint: AnalyticsSqlEndpoint, sql: SafeLogSqlFragment, iso_timestamp_start, iso_timestamp_end, method?, key?, signal?, headers? })`.
**Data Shape:** the ClickHouse count query folds several facets into ONE scan via `arrayJoin(['total','log_type',...]) AS facet, multiIf(facet = 'total', 'all', facet = 'log_type', LOG_TYPE_EXPR, ...) AS value, count()`; log_type ALWAYS gets its own scan (excluding it also drops the default-types restriction, so its counts differ from the base scan); a FILTERED facet gets its own scan; pathname (high-cardinality) gets its own LIMIT block because "the endpoint rejects LIMIT BY inside the shared arrayJoin". The BigQuery twin answers the same four questions with per-source fragments UNION ALL'd into a `unified_logs` CTE; its `buildConditions` validates identifier-position keys through `quotedIdent()` (reject-not-escape) and values through `analyticsLiteral`, DROPPING the predicate on throw rather than emitting unsafe SQL, and emulates ILIKE as `LOWER(col) LIKE LOWER('%v%')`. The flag pair travels together: `pickLogsQueryBuilder(useOtel, getLogsChartQuery, getLogsChartQueryBq)` preserves the input type so callers keep one signature, and `logsAllEndpointUrl(useOtel)` picks the matching endpoint. The wire boundary accepts ONLY `SafeLogSqlFragment` (plain strings rejected at compile time) over a closed `AnalyticsSqlEndpoint` union.

### Decisive source
```ts
// `key` is interpolated as a column identifier. `quotedIdent()` rejects
// anything outside `[A-Za-z_][A-Za-z0-9_]*` (notably no spaces, so a
// crafted URL key like `level OR id IS NOT NULL` is dropped rather
// than emitted into the WHERE clause).
const col = quotedIdent(key)
...
} catch {
  // quotedIdent() or analyticsLiteral() rejected the input — drop the predicate.
}
```

**Flow:** caller picks builder+endpoint by flag → builder renders a SafeLogSqlFragment → executeAnalyticsSql POSTs `{sql, iso_timestamp_start, iso_timestamp_end}` (or GET for legacy callers) → handleError on error. The BQ file header says it "should be deleted once the flag is removed" — the twin is migration scaffolding, not a permanent second kernel.
**Invariant:** two dialects behind a flag must share the PORTER QUESTION (same inputs, same output contract), not the SQL text; the flag pair (builder picker + endpoint picker) must be selected together or queries hit the wrong engine. A closed endpoint union type is the guard against new endpoints bypassing the brand check.
**Probe:** tests pin BQ backtick quoting, "rejects keys with non-identifier characters" (`foo; DROP TABLE x` dropped entirely), LOWER()-emulated ILIKE with no raw ILIKE keyword, and ≤4 `FROM logs` scans in the folded count query.

## User-attribution filter + guaranteed-zero detection
**Path/Symbol:** `UnifiedLogs.queries.ts` : `userAttributionCondition` (:342-351), `isUserFilterUnreachable` (:364-382), USER_ATTRIBUTABLE_SOURCES (:353).
**Signature:** `userAttributionCondition(search): SafeLogSqlFragment | null`; `isUserFilterUnreachable(search): boolean`.
**Data Shape:** only two sources can be positively tied to a user — auth_logs via `auth_event.actor_id`, edge_logs via the JWT subject attribute — so while the user filter is active the default postgres+edge source restriction is SKIPPED (it would exclude auth_logs, the primary attributable source); other sources are auto-excluded, "never guessed at via IP or timestamp proximity". `isUserFilterUnreachable` detects the guaranteed-zero combination (user filter active + explicit log_type filter restricting to non-attributable sources; neq variant: unreachable only when BOTH attributable sources are excluded) so the UI shows a specific empty state instead of generic "No results found".

### Decisive source
```ts
return safeSql`(
  (source = 'auth_logs' AND log_attributes['auth_event.actor_id'] = ${exact})
  OR 
  (source = 'edge_logs' AND log_attributes['request.sb.jwt.authorization.payload.subject'] = ${exact})
)`
```

**Flow:** user value trimmed → null when inactive → else OR of the two attributable-source branches, ANDed into the shared WHERE; the UI separately asks isUserFilterUnreachable to pick the empty-state copy.
**Invariant:** attribution must be POSITIVE (a field that names the user), never proximity-based; and a filter combination that provably matches zero rows deserves its own empty state — compute reachability from the same source-of-truth set the SQL uses.
**Probe:** test matrix pins all nine cases incl. "(neq) is true only when both attributable sources are excluded" and "restricts to auth_logs/edge_logs and skips the default postgres+edge restriction".

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "buildBaseWhere translateFilter getLogsCountQuery pickLogsQueryBuilder executeAnalyticsSql", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the single shared WHERE compiler feeding every query shape (list/chart/facet/count) with view-option toggles inside it; per-shape `excludeField` so a facet counts its own other values; inlined-from-one-constant derived columns when the engine rejects subqueries/alias-in-aggregate; arrayJoin/multiIf scan folding with own-scan exceptions for facets whose exclusion changes semantics and for high-cardinality LIMITs; the flag-routed dialect twin sharing one input/output contract with a delete-me header; the brand-only wire boundary over a closed endpoint union; positive-only user attribution with guaranteed-zero-combination detection. Adapt the facet set, source map, and bucketing thresholds to your log schema. Omit Supabase-product specifics: the exact OTEL attribute key names, the edge-gateway path conventions, and the platform endpoint paths. Direct-test caveat: UnifiedLogs.queries.test.ts (416L) read whole, vitest unexecutable in-lane — never claimed passing.
