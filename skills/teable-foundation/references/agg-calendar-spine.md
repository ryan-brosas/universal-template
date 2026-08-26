<!-- capsule-v2 -->
# Calendar daily collection SQL — timezone-pinned generate_series + array_agg[1:10] sample

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the calendar view get per-day counts + record samples when records SPAN day ranges?

## Cross-join date spine + start<=day AND coalesced-end>=day
**Path/Symbol:** builder `apps/nestjs-backend/src/db-provider/postgres.provider.ts:calendarDailyCollectionQuery` (:693–754); orchestrator `apps/nestjs-backend/src/features/aggregation/aggregation.service.ts:getCalendarDailyCollection` (:1193–1331) — field validation :1228–1253, countMap/id assembly :1305–1323.
**Signature:** `calendarDailyCollectionQuery(qb, {startDate, endDate, startField, endField, dbTableName})`.
**Data Shape:** rows `{date: Date|string, count: number, ids: string[]|string}` — ids = first-10 array from `array_agg(...)[1:10]`, comma-string when driver flattens.

### Decisive source
```ts
this.knex.raw(`(array_agg(?? ORDER BY ??.??))[1:10] as ids`, ['__id', dbTableName, startField.dbFieldName]),
...
.andWhereRaw(
  `(COALESCE(??.??::timestamptz, ??.??)::timestamptz AT TIME ZONE ?)::date >= (?::timestamptz AT TIME ZONE ?)::date`,
  [dbTableName, endField.dbFieldName, dbTableName, startField.dbFieldName, timezone, startDate, timezone]
)
```

**Flow:** A `generate_series(start::date, end::date, '1 day')` subquery (`dates`) cross-joins the view CTE so EMPTY days still return rows (count 0) — the calendar grid needs contiguous cells. Membership test: a record belongs to `dates.date` when its START day ≤ that day AND its END (falling back to start for single-date events) ≥ that day; all comparisons pin the FIELD's configured timezone via `AT TIME ZONE` before ::date truncation. Service side decodes dates to ISO-day keys and re-fetches full record payloads for the deduped id union.
**Invariant:** The COALESCE(end,start) is what makes single-date events appear on exactly one day while ranged events paint every covered cell; dropping it empties half the calendar. Timezone must come from the FIELD's formatting options (not server TZ) or days shift for every non-UTC user. The `[1:10]` slice bounds payload size per day — ids are a SAMPLE for hover cards, not the membership set; porters who treat it as complete break downstream counts.
**Probe:** `grep -cF 'generate_series' apps/nestjs-backend/src/db-provider/postgres.provider.ts` → 1; `grep -cF 'COALESCE' apps/nestjs-backend/src/db-provider/postgres.provider.ts` → 6.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "calendarDailyCollectionQuery generate_series array_agg", limit: 10 });
```

## Verdict
Adopt date-spine cross-joins for range-spanning calendar aggregation; adapt the field-tz pinning and sample-slice to your payload budget.
