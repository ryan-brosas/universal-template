<!-- capsule-v2 -->
# Unified-logs pagination + inspection plane — how do you page a log stream whose sort column is not unique, and look up one row fast?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** When the log table's natural sort column (timestamp) has duplicate values, how does infinite scroll avoid skipping/duplicating rows, and how does a single-row detail lookup stay fast without scanning the whole selected time range?

## Timestamp cursor stored as milliseconds (`data/logs/unified-logs-infinite-query.ts`)
**Path/Symbol:** `apps/studio/data/logs/unified-logs-infinite-query.ts` : `getUnifiedLogs` (:56-167), `LOGS_PAGE_LIMIT` (:19), `useUnifiedLogsInfiniteQuery` (:169-202).
**Signature:** `getUnifiedLogs({ projectRef, search, pageParam, useOtel }, signal?, headersInit?): Promise<{ data, nextCursor, prevCursor }>`.
**Data Shape:** the cursor is the last row's timestamp stored as MILLISECONDS (`lastRow.date.getTime()`) — the in-source comment: "Cursors are stored as milliseconds (Date.getTime()) so the OTEL endpoint's wire format (ISO string vs numeric microseconds) doesn't bleed into pagination." The range is bounded by ENDPOINT PARAMS `iso_timestamp_start/end`, not a WHERE clause: first page ends at the search range end (default last hour); 'next' pages end at the cursor; 'prev' (live mode, newer rows) ends at now. The SQL appends `ORDER BY timestamp DESC, id DESC LIMIT 50`.

### Decisive source
```ts
const hasMore = result.length >= LOGS_PAGE_LIMIT - 1

// Cursors are stored as milliseconds (Date.getTime()) so the OTEL endpoint's
// wire format (ISO string vs numeric microseconds) doesn't bleed into pagination.
const nextCursor = lastRow ? lastRow.date.getTime() : null
const prevCursor = firstRow ? firstRow.date.getTime() : new Date().getTime()

return {
  data: result,
  nextCursor: hasMore ? nextCursor : null,
  prevCursor,
}
```

**Flow:** parseOtelTimestamp normalizes each row's timestamp (format-disambiguated ISO vs numeric microseconds — see otel-inspection.utils) → map to a stable domain shape → compute cursors from first/last row → react-query `getNextPageParam`/`getPreviousPageParam` wrap `{cursor, direction}`; `placeholderData: keepPreviousData`; UNIFIED_LOGS_QUERY_OPTIONS disables every refetch-on-* with staleTime 5min.
**Invariant:** the hasMore heuristic is `>= LIMIT - 1`, NOT `== LIMIT` — the in-source comment admits identical-timestamp rows make a pure timestamp cursor lossy ("there's always the edge case where by there's multiple rows with identical timestamps"), so the FE de-dupes already-seen ids when flattening pages (UnifiedLogs.tsx :197-201). Storing the cursor in one canonical unit (ms) decouples pagination from whatever wire format the engine returns.
**Probe:** direct read at the pin; no dedicated upstream test for getUnifiedLogs (the query builders it calls are test-pinned — see unified-logs-shared-safe-sql-builder capsule). Vitest unexecutable in-lane — never claimed passing.

## Tight-window point lookup + input gating before interpolation (`data/logs/unified-log-inspection-query.ts`)
**Path/Symbol:** `apps/studio/data/logs/unified-log-inspection-query.ts` : `INSPECTION_WINDOW_MS` (:69), `getInspectionISOStartEnd` (:71-82), `getUnifiedLogInspection` (:165-292), uuid gate (:232-234), SERVICE_FLOW_TYPE_SOURCE (:44-50).
**Signature:** `getInspectionISOStartEnd(search, logTimestampMs): { isoTimestampStart, isoTimestampEnd }`; `getUnifiedLogInspection({ projectRef, logId, type, search, useOtel, logTimestampMs }, signal?)`.
**Data Shape:** when the selected row's own timestamp (ms) is known, the lookup bounds the query to ±60s around IT instead of the (potentially much wider) selected search range — the in-source rationale: "The row's timestamp is the exact stored value (parsed from the same `timestamp` column), not an approximate clock reading, so this only needs to absorb millisecond-vs-microsecond rounding — not real clock skew." `logId` ultimately originates from a URL query parameter, so it is regex-gated `/^[0-9a-fA-F-]{1,64}$/` BEFORE interpolation — "Reject anything that isn't a plain uuid before interpolating it into SQL so a crafted id can't break out of the string literal." SERVICE_FLOW_TYPE_SOURCE pre-brands each type→source literal from the shared LOG_TYPE_TO_SOURCE map (one source of truth; only key spelling differs).

### Decisive source
```ts
if (!/^[0-9a-fA-F-]{1,64}$/.test(logId)) {
  throw new Error('Invalid logId')
}
const sql = safeSql`-- unified logs: inspect single log by id
SELECT id, timestamp, source, event_message, severity_text, log_attributes
FROM logs
WHERE id = ${lit(logId)} AND source = ${SERVICE_FLOW_TYPE_SOURCE[type]}
LIMIT 1
`
```

**Flow:** guard ladder (projectRef/logId/type required) → tight window or search-range fallback → OTEL path fetches the single row by id+source, flattens its `log_attributes` Map onto the legacy underscored field shape so existing panel components keep working without per-service-flow SQL → edge-function rows trigger the only legitimate cross-source join (function_logs by execution_id/request_id, ALSO uuid-gated, fail-soft catch — "function logs are supplementary; silently ignore fetch errors").
**Invariant:** a point lookup on a partitioned/sorted store must bound the scan around the ROW'S OWN stored value, not the user's selection range; and any value that can originate from a URL must be shape-validated before it reaches SQL composition even though the literal escaper would also stop injection — the gate makes the intent explicit and rejects non-uuid ids that would be legal-but-wrong queries.
**Probe:** direct read at the pin; the flatten/aggregate helpers are exercised indirectly (no dedicated inspection-query test file exists — recorded as test absence, not claimed covered).

## Wire-format disambiguation by format, not finiteness (`data/logs/otel-inspection.utils.ts`)
**Path/Symbol:** `apps/studio/data/logs/otel-inspection.utils.ts` : `parseOtelTimestamp` (:14-21), `flattenOtelInspectionRow` (:38-150), `aggregateFunctionLogs` (:155-172).
**Signature:** `parseOtelTimestamp(timestamp: unknown): Date`.
**Data Shape:** OTEL timestamps arrive as an ISO string (sometimes space-separated, no zone) OR numeric microseconds. Disambiguation is by FORMAT: strings containing `T` or `-` are ISO (space→T, append Z when no zone suffix), anything else is treated as microseconds (/1000). The chart consumer repeats the same rule inline with the comment "Disambiguate by format rather than Number.isFinite". Level derivation ladder: HTTP status (≥500 error / ≥400 warning / else success) → postgres severity (WARNING warning; ERROR/FATAL/CRITICAL/PANIC error) → severity_text lowercase. `flattenOtelInspectionRow` coalesces per-source key variants (request.path vs request.pathname vs path; response.status_code vs parsed.sql_state_code for postgres rows) and spreads raw dotted attribute keys verbatim because some consumers read `enrichedData['request.path']` directly.

### Decisive source
```ts
// OTEL timestamps arrive as an ISO string (sometimes space-separated, no zone)
// or as numeric microseconds. Strings have a `T` or `-`; anything else is micros.
export function parseOtelTimestamp(timestamp: unknown): Date {
  const ts = String(timestamp ?? '')
  const looksLikeIso = /[T-]/.test(ts)
  if (!looksLikeIso) return new Date(Number(ts) / 1000)
  const withT = ts.includes(' ') ? ts.replace(' ', 'T') : ts
  const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(withT)
  return new Date(hasTz ? withT : `${withT}Z`)
}
```

**Flow:** every row's timestamp passes through parseOtelTimestamp exactly once at the fetch boundary; downstream code (cursors, charts) sees canonical Dates/ms.
**Invariant:** when one column carries two encodings across engine versions, normalize ONCE at the boundary using a format discriminator that cannot misfire on the other encoding — and keep the discriminator identical wherever the raw value is re-read (the chart re-implements it inline rather than importing, which is the documented coupling).
**Probe:** `unified-logs.utils.test.ts` (173L, read whole) pins the sibling extractLogMetadata ladders (leading-3-digit-only status extraction, 4+-digit rejection, non-JSON tolerance); parseOtelTimestamp itself has no dedicated test — recorded as test absence.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "getUnifiedLogs nextCursor prevCursor INSPECTION_WINDOW_MS parseOtelTimestamp flattenOtelInspectionRow", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: millisecond-canonical cursors decoupled from wire format; endpoint-param range bounding for paged reads over a non-unique sort column; the `>= LIMIT - 1` hasMore heuristic paired with consumer-side de-duplication when the sort column has duplicates; tight ±window point lookups bounded by the row's own stored value; shape-validation of URL-originated ids before SQL composition; format-discriminated dual-encoding timestamp normalization at a single boundary. Adapt the window size, page limit, and attribute-key coalescing table to your schema. Omit Supabase-product specifics: the exact OTEL attribute keys and the platform endpoint paths. Direct-test caveat: unified-logs.utils.test.ts read whole; no dedicated tests exist for the infinite-query/inspection fns (recorded absence); vitest unexecutable in-lane — never claimed passing.
