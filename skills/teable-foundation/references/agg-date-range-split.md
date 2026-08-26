<!-- capsule-v2 -->
# Date-range twin split — SQL MAX/MIN CONCAT vs JS dayjs month diff

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Why do DateRangeOfDays and DateRangeOfMonths compile to completely different things, and where does each half live?

## SQL emits a payload; JS decodes it
**Path/Symbol:** SQL side: `single-value/single-value-aggregation.adapter.ts:dateRangeOfDays` (:4–8) + `:dateRangeOfMonths` (:10–14); MCV twins in `multiple-value-aggregation.adapter.ts` (:64–80) with `::TIMESTAMPTZ` casts. JS decode: `apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` — `formatConvertValue` (:207–230), `calculateDateRangeOfMonths` (:242–245).
**Signature:** SQL months → `"max,min"` string; JS → number of month units.
**Data Shape:** days = INTEGER (extract DAY from interval); months = `CONCAT(MAX,',',MIN)` raw timestamps.

### Decisive source
```ts
// single-value adapter
dateRangeOfDays(): string {
  return this.knex
    .raw(`extract(DAY FROM (MAX(${this.tableColumnRef}) - MIN(${this.tableColumnRef})))::INTEGER`)
    .toQuery();
}
dateRangeOfMonths(): string {
  return this.knex.raw(`CONCAT(MAX(${this.tableColumnRef}), ',', MIN(${this.tableColumnRef}))`).toQuery();
}
// service — the only consumer that decodes it
if (aggFunc === StatisticsFunc.DateRangeOfMonths && typeof currentValue === 'string') {
  convertValue = this.calculateDateRangeOfMonths(currentValue);
}
private calculateDateRangeOfMonths(currentValue: string): number {
  const [maxTime, minTime] = currentValue.split(',');
  return maxTime && minTime ? dayjs(maxTime).diff(minTime, 'month') : 0;
}
```

**Flow:** Days are pure SQL (timestamp difference, DAY component). Months CANNOT be done with a fixed SQL unit (calendar-month math varies by boundaries), so SQL ships both endpoints comma-joined and the SERVICE converts with dayjs. If the value is not a string (NULL aggregate over empty scope) it stays NULL.
**Invariant:** The wire contract is positional "MAX,MIN" — swapping the order flips the sign; the dayjs diff handles negatives silently, so a porter who reverses it produces plausible-looking negative month counts. Porters who try to do months fully in SQL with `extract(YEAR)*12+MONTH` get subtly different answers across DST/timezone edges than the dayjs pair. The `::TIMESTAMPTZ` casts exist ONLY in the MCV twins because jsonb text elements must be typed before subtraction — plain timestamp columns already carry the type.
**Probe:** `grep -cF 'CONCAT(MAX' apps/nestjs-backend/src/db-provider/aggregation-query/postgres/multiple-value/multiple-value-aggregation.adapter.ts` → 1; `grep -cF 'calculateDateRangeOfMonths' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "dateRangeOfMonths calculateDateRangeOfMonths dayjs diff", limit: 10 });
```

## Verdict
Adopt SQL-for-fixed-units / app-for-calendar-units split; adapt the delimiter+decode pair to your serializer; omit the TIMESTAMPTZ casts for natively-typed columns.
