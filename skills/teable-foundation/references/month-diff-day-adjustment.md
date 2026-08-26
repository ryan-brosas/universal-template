<!-- capsule-v2 -->
# month-diff-day-adjustment — Why is DATETIMEDIFF(month) hand-rolled instead of using Postgres AGE?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What exact day-of-month adjustment does the month difference implement, and how does it differ from FROMNOW's AGE-based months?

## buildMonthDiff: baseMonths ± 1 via end-day vs start-day comparisons; FROMNOW uses AGE()
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/select-query/postgres/select-query.postgres.ts:buildMonthDiff` (:1296-1313) consumed by datetimeDiff month/quarter/year (:1329-1345); contrast `buildNowDiffByUnit` (:1383-1414).
**Signature:** `private buildMonthDiff(startDate: string, endDate: string): string` — both sides pass through tzWrap with their own metadata indexes (0 and 1).
**Data Shape:** returns integer-ish SQL; quarter divides by 3.0; year casts /12.0 to INTEGER.

### Decisive source
```ts
const baseMonths = ((startYear - endYear) * 12 + (startMonth - endMonth));
const adjustDown = `(CASE WHEN ${baseMonths} > 0 AND ${startDay} < ${endDay}
                        AND ${startDay} < ${startLastDay} THEN 1 ELSE 0 END)`;
const adjustUp   = `(CASE WHEN ${baseMonths} < 0 AND ${startDay} > ${endDay}
                        AND ${endDay} < ${endLastDay} THEN 1 ELSE 0 END)`;
return `(${baseMonths} - ${adjustDown} + ${adjustUp})`;
...
// FROMNOW/TONOW take the OTHER route:
const diffMonths = `EXTRACT(MONTH FROM AGE(now, date)) + EXTRACT(YEAR FROM AGE(now, date)) * 12`;
```

**Flow:** extract Y/M/D of both tz-wrapped operands plus each month's LAST DAY → subtract adjustDown when counting down and the start day hasn't reached the end day-of-month → add adjustUp symmetrically for negative spans → scale for quarter/year. The now-relative functions deliberately use AGE() instead.
**Invariant:** two different month semantics coexist by design: DATETIMEDIFF uses calendar-boundary arithmetic (last-day guards prevent off-by-one at month ends); FROMNOW/TONOW use AGE()'s monotone month count. Unifying them changes user-visible results for same-month-boundary dates.
**Probe:** static byte-exact: `grep -n 'adjustDown' select-query.postgres.ts` → :1309/:1312; upstream spec pins unit scaling in `generated-column-query.postgres.spec.ts` ("applies unit conversion for FROMNOW": `/86400`, `/3600`).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildMonthDiff","limit":3,"detail":"ids"}'
```

## Verdict
Adopt both semantics WITH their split. Adapt interval units. Omit nothing — the asymmetry is intentional.
