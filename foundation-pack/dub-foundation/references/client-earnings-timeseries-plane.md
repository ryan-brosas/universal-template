<!-- capsule-v2 -->
# Client earnings timeseries plane — how does the browser consume the partner-earnings timeseries without gaps or stale flashes?

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** What contract must a SWR hook and its server helper satisfy so an earnings chart never shows holes or blank-flickers on filter change?

## Server helper: SQL buckets + zero-fill
**Path/Symbol:** `apps/web/lib/api/partner-profile/get-partner-earnings-timeseries.ts:getPartnerEarningsTimeseries` (:10-:137).
**Signature:** `async ({partnerId, programId, filters}) => {start:string, earnings:number, groupBy?:string, data?:Record<string,number>}[]`.
**Data Shape:** raw SQL over Commission with `DATE_FORMAT(CONVERT_TZ(createdAt,"UTC",tz), dateFormat)` bucket keys from `sqlGranularityMap[granularity]`; output rows are dense across `[startDate,endDate)`.

### Decisive source
```ts
const commissionLookup = earnings.reduce((acc, item) => {
  if (!(item.start in acc)) acc[item.start] = { earnings: 0 };
  acc[item.start].earnings += Number(item.earnings);
  if (groupBy && item[groupBy]) acc[item.start][item[groupBy] as string] = Number(item.earnings);
  return acc;
}, {});
while (currentDate < endDate) {
  const periodData = commissionLookup[format(currentDate, formatString)];
  const { earnings, ...rest } = periodData || { earnings: 0 };
  ...
}
```

**Flow:** enrollment fetch → `getStartEndDates` clamped to `program.startedAt ?? program.createdAt` → granularity map picks dateFormat/increment → one grouped query (`WHERE earnings != 0 AND programId/partnerId/createdAt…` :59) → fold rows into a lookup keyed by formatted bucket string → walk the FULL window incrementing by `dateIncrement`, defaulting missing buckets to earnings 0.
**Invariant:** density is manufactured client-of-the-DB side: SQL returns only non-zero buckets; the while-loop guarantees every period exists. Under `groupBy`, `data` is PRE-SEEDED with every possible key (all of sale/lead/click, or every enrollment link id — filtered down when that dimension itself is filtered) BEFORE spreading actuals (:116-:131), so chart series never gain/lose keys between periods.
**Probe:** no direct unit test at pin (coverage caveat). Anchors observed live: `earnings != 0` :59, `sqlGranularityMap[granularity]` :50, zero-fill loop `while (currentDate < endDate)` :104.

## SWR hook: stable keys and no-flash updates
**Path/Symbol:** `apps/web/lib/swr/use-partner-earnings-timeseries.ts:usePartnerEarningsTimeseries` (:9-:54).
**Signature:** `(params?: PartnerEarningsTimeseriesFilters & {programId?, enabled?}) => {data, error, loading}`.
**Data Shape:** key = `/api/partner-profile/programs/${programIdToUse}/earnings/timeseries${getQueryString(...)}`; start/end sent as ISO strings XOR interval default (`DUB_PARTNERS_ANALYTICS_INTERVAL`); `timezone: Intl.DateTimeFormat().resolvedOptions().timeZone` always appended.

### Decisive source
```ts
{ dedupingInterval: 60000, keepPreviousData: true }
```

**Flow:** gate fetch on session's `defaultPartnerId` AND a program id (param or route slug) AND `enabled !== false` → build query with include-listed filter params → SWR fetcher.
**Invariant:** `keepPreviousData: true` means filter changes render the OLD series until new data lands (no blank flash); `dedupingInterval: 60000` caps refetch storms for a minute-granular chart. The hook returns `loading` only when prerequisites exist but no data/error yet — pre-condition absence is "disabled", not "loading".
**Probe:** anchors observed live: timezone append :38, `dedupingInterval: 60000` :44, `keepPreviousData: true` :45. Route-side sibling test `tests/analytics/partners/analytics.test.ts` is CI-gated.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "partner earnings timeseries SWR", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "dub", qualified_name: "dub.apps.web.lib.api.partner-profile.get-partner-earnings-timeseries.getPartnerEarningsTimeseries" });
```

## Verdict
Adopt: lookup-fold + explicit-window zero-fill, groupBy-key pre-seeding, keepPreviousData/dedup pairing, and the enabled≠loading distinction. Adapt granularity map and interval defaults to your chart lib; omit dub's specific commission table/columns. Coverage caveat: helper has no direct unit test at pin; behavior pinned by source anchors and the CI-gated route test.
