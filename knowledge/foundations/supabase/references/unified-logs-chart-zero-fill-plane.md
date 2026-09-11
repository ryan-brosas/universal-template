<!-- capsule-v2 -->
# Unified-logs chart zero-fill + level-filter plane — how do you keep a severity chart honest under active level filters?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** A severity chart shows three series (success/warning/error) while the user's active filters may exclude some levels — how does the chart stay consistent with the filtered row list, and how are empty time buckets rendered?

## Client-side level zeroing from the parsed filter set (`data/logs/unified-logs-chart-query.ts`)
**Path/Symbol:** `apps/studio/data/logs/unified-logs-chart-query.ts` : `getUnifiedLogsChart` (:16-154), level-zeroing block (:90-106), bucket ladder (:119-127), zero-fill loop (:128-145).
**Signature:** `getUnifiedLogsChart({ projectRef, search, useOtel }, signal?, headersInit?): Promise<Array<{ timestamp, success, warning, error }>>`.
**Data Shape:** the SQL comes from the same flag-routed dialect twin pair as the shared builder (unified-logs-shared-safe-sql-builder capsule): `pickLogsQueryBuilder(useOtel, getLogsChartQuery, getLogsChartQueryBq)(search)` — both twins apply ALL filters including level in their WHERE (OTEL `buildBaseWhere(search)` at queries.ts :543; BQ `buildConditions(search)` at queries.bq.ts :514). The client then RE-DERIVES the active level set from the URL filter params and zeros inactive series on every data point — a client-side guarantee layered on top of the SQL filter, so the three series depend only on the parsed filter set, independent of how each dialect derives level (OTEL inline LEVEL_EXPR CASE vs BQ CTE level column).

### Decisive source
```ts
// Zero out levels excluded by the active filter set.
// `=` filters narrow to an allow-list; `<>` filters carve out a deny-list.
const levelFilters = parseLogsFilterUrlParams(search.filter).filter(
  (f) => f.column === 'level'
)
if (levelFilters.length > 0) {
  const included = levelFilters.filter((f) => f.operator === '=').map((f) => f.value)
  const excluded = new Set(
    levelFilters.filter((f) => f.operator === '<>').map((f) => f.value)
  )
  const isActive = (lvl: 'success' | 'warning' | 'error') =>
    (included.length === 0 || included.includes(lvl)) && !excluded.has(lvl)
  if (!isActive('success')) dataPoint.success = 0
  if (!isActive('warning')) dataPoint.warning = 0
  if (!isActive('error')) dataPoint.error = 0
}
```

**Flow:** guard projectRef → default range = last hour when `search.date` is absent or not length 2 (:28-40; range always sent as ISO strings to endpoint params, never into SQL) → dialect-twin SQL → executeAnalyticsSql (pass-5 brand-only wire boundary) → per row: normalize timestamp (format-discriminated ISO-vs-microseconds, repeated INLINE with the comment "Disambiguate by format rather than Number.isFinite — see unified-logs-infinite-query.ts for the reasoning" — the documented coupling to parseOtelTimestamp) → zero inactive levels → map by timestamp → zero-fill missing buckets → sort by timestamp.
**Invariant:** when a derived display column (level) is computed by an engine-side expression that can diverge from the filtered value, the presentation layer must re-derive the allowed set from the USER'S parsed filters and force the output — never trust that the engine's derivation and the filter agree. Allow-list (`=`) and deny-list (`<>`) semantics compose: a level is active iff (no allow-list OR listed) AND not denied.
**Probe:** direct read at the pin; no dedicated upstream test for getUnifiedLogsChart (zero-fill/level-zeroing logic) — recorded as test absence, not claimed covered. Vitest unexecutable in-lane — never claimed passing.

## Bucket ladder + zero-fill so empty periods render as gaps-free zeros (`data/logs/unified-logs-chart-query.ts`)
**Path/Symbol:** same file : bucketSizeMs ladder (:119-127), fill loop (:128-145).
**Signature:** internal; input = selected range `[startTime, endTime]` + rows keyed by ms timestamp.
**Data Shape:** `timeRangeHours >= 48 → day`, `> 12 → hour`, else minute. The SQL-side bucketing uses the SAME thresholds in both twins (BQ `calculateChartBucketing` :161-163: `dayDiff >= 2 → DAY`, `hourDiff >= 12 → HOUR`, else MINUTE; OTEL `calculateChartBucketing` at queries.ts :207) so client fill and server buckets agree. The fill loop walks start→end stepping bucketSizeMs, rounds each t DOWN to its boundary (`Math.floor(t / bucketSizeMs) * bucketSizeMs`), and inserts an all-zero point when the map lacks that boundary.

### Decisive source
```ts
let bucketSizeMs: number
if (timeRangeHours >= 48) {
  bucketSizeMs = 24 * 60 * 60 * 1000
} else if (timeRangeHours > 12) {
  bucketSizeMs = 60 * 60 * 1000
} else {
  bucketSizeMs = 60 * 1000
}

// Fill in any missing buckets
for (let t = startTimeMs; t <= endTimeMs; t += bucketSizeMs) {
  // Round to the nearest bucket boundary
  const bucketTime = Math.floor(t / bucketSizeMs) * bucketSizeMs

  if (!dataByTimestamp.has(bucketTime)) {
    // Create empty data point for this bucket
    dataByTimestamp.set(bucketTime, {
      timestamp: bucketTime,
      success: 0,
      warning: 0,
      error: 0,
    })
  }
}
```

**Flow:** server returns only buckets that have rows; the client materializes the full grid over the selected range so the chart x-axis is continuous; final array sorted by timestamp before return.
**Invariant:** a time-series chart must be filled CLIENT-SIDE over the selected range with the same bucket size the server used — otherwise empty periods render as missing points (visual gap or axis compression) instead of honest zeros, and the two sides must share one threshold table or fill boundaries won't align with server buckets.
**Probe:** direct read at the pin; threshold parity verified against both twin builders at the pin (queries.ts :205+ / queries.bq.ts :122-164); no dedicated test — recorded absence.

## Filter URL-param grammar with round-trip guarantees (`components/interfaces/UnifiedLogs/UnifiedLogs.filters.ts`)
**Path/Symbol:** `apps/studio/components/interfaces/UnifiedLogs/UnifiedLogs.filters.ts` : operator maps (:26-40), `parseLogsFilterUrlParams` (:50-61), `logsFiltersToColumnFilters` (:84-90), `groupLogsFiltersByColumn` (:66-82), `buildFilterSearchUpdate` (:125-144), `buildDefaultColumnFilters` (:92-103).
**Signature:** `parseLogsFilterUrlParams(filter?: string[] | null): LogsFilter[]`; `buildFilterSearchUpdate(columnFilters, filterFields): Record<string, unknown>`.
**Data Shape:** closed 4-operator set `= <> ~~* !~~*` mirrored to PostgREST abbreviations eq/neq/ilike/notilike via two total Record maps (both directions). URL form `column:abbrev:value` where value is everything after the second colon rejoined on ':' (values may contain colons); malformed entries (missing column or unknown abbrev) are SILENTLY SKIPPED, never thrown. Column-filter shape: `=` groups emit bare string[] (sidebar checkbox shape); non-eq groups stay WRAPPED `{operator, values}` so the operator survives a round-trip. Mixed operators per column collapse last-write-wins (one operator per column is the expressible shape). Timerange-typed fields route to their OWN URL keys, never into `filter`; absent timerange keys are nulled so a cleared brush leaves the URL.

### Decisive source
```ts
export const parseLogsFilterUrlParams = (filter?: string[] | null): LogsFilter[] => {
  if (!Array.isArray(filter)) return []
  const parsed: LogsFilter[] = []
  for (const raw of filter) {
    const [column, abbrev, ...rest] = raw.split(':')
    const operator = ABBREV_TO_OPERATOR[abbrev]
    if (!column || !operator) continue
    parsed.push({ column, operator, value: rest.join(':') })
  }
  return parsed
}
```

**Flow:** URL params ⇄ LogsFilter[] ⇄ column-filter UI shape is a three-way conversion where every hop is lossless for expressible shapes; `buildDefaultColumnFilters` seeds `date` too — regression guard: without it "the debounced sync back to `search`" would null a deep-linked date range.
**Invariant:** a URL-serializable filter state must round-trip WITHOUT semantic downgrade (a neq filter must come back neq, not eq), unknown/malformed entries degrade by skipping (the URL is hostile input), and every field type has exactly one home key (timerange never mixes into the generic filter param).
**Probe:** `UnifiedLogs.filters.test.ts` (168L, read whole) pins: bare string[] ⇒ default `=` serialization; wrapped-value operator preservation; scalar-as-single-eq; filterableNames exclusion of the date brush; null/undefined skip; eq-group bare-array seeding; non-eq wrapped round-trip; **eq and neq URL filters round-trip without downgrading to eq**; timerange routing to its own key + nulling; date-seed regression guard incl. no duplicate `date` id when a hand-crafted `filter` param also targets it. Vitest unexecutable in-lane — read whole, never claimed passing.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "getUnifiedLogsChart parseLogsFilterUrlParams bucketSizeMs Zero out levels excluded by the active filter set", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: client-side re-derivation of the allowed series set from parsed user filters (allow-list ∩ ¬deny-list) layered on top of the SQL filter; the shared-threshold bucket ladder (≥48h→day / >12h→hour / else minute) duplicated between server bucketing and client zero-fill; boundary-rounded zero-fill over the selected range; the closed operator-abbreviation grammar with silent-skip malformed handling, colon-in-value rejoin, no-downgrade round-trips, and per-type-key routing of timerange fields. Adapt the operator set, bucket thresholds, and marker columns to your schema. Omit Supabase-product specifics: the exact OTEL/BQ dialect twins and platform endpoint paths. Direct-test caveat: UnifiedLogs.filters.test.ts read whole; no dedicated test for getUnifiedLogsChart (recorded absence); vitest unexecutable in-lane — never claimed passing.
