<!-- capsule-v2 -->
# Window & granularity resolution — who wins: start/end, interval, or dataAvailableFrom

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** Given any mix of interval/start/end/dataAvailableFrom, what absolute UTC window and bucket size does the warehouse query receive?

## getStartEndDates + the INTERVAL_DATA preset table
**Path/Symbol:** `apps/web/lib/analytics/utils/get-start-end-dates.ts:getStartEndDates` (:6-54); `apps/web/lib/analytics/utils/get-interval-data.ts` INTERVAL_DATA (:13-68) + `getIntervalData` (:70-73); `DUB_FOUNDING_DATE` = `packages/utils/src/constants/misc.ts:35` (= 2022-09-22T00:00:00Z).
**Signature:** `getStartEndDates({interval?, start?, end?, dataAvailableFrom?, timezone?}): { startDate: TZDate, endDate: TZDate, granularity: "minute"|"hour"|"day"|"month }`.
**Data Shape:** timezone sanitized first (`sanitizeTimezone`); all arithmetic in `TZDate`/`date-fns/tz` so windows honor the requester's timezone.

### Decisive source
```ts
if (start || (interval === "all" && dataAvailableFrom)) {
  startDate = startOfDay(new TZDate(new Date(start ?? dataAvailableFrom ?? Date.now()), timezone));
  endDate = endOfDay(new TZDate(new Date(end ?? Date.now()), timezone));

  const daysDifference = differenceInDays(endDate, startDate, { in: tz(timezone) });

  if (daysDifference <= 2) {
    granularity = "hour";
  } else if (daysDifference > 180) {
    granularity = "month";
  }

  // Swap start and end if start is greater than end
  if (startDate > endDate) {
    [startDate, endDate] = [endDate, startDate];
  }
} else {
  interval = interval ?? "30d";
  const intervalData = getIntervalData(interval, { timezone });
  ...
}
```
(get-start-end-dates.ts :25-50 condensed)

**Flow:** custom `start` ALWAYS wins over interval; `interval:"all"` degrades to `dataAvailableFrom` (workspace plan's retention floor) then to the founding-date preset; fixed presets hard-code their own granularity — 24h→hour, 7d/30d/90d/mtd/qtd→day, 1y/ytd/all→month; default interval is 30d.
**Invariant:** reversed ranges SWAP silently instead of erroring (dashboard date pickers can emit them); bucket choice caps timeseries cardinality — hourly buckets exist only for spans ≲3 days, monthly beyond ~6 months.

**Probe:** executed: `grep -n 'granularity = "hour"' apps/web/lib/analytics/utils/get-start-end-dates.ts` → :36; `grep -n 'daysDifference > 180' ...` → :37; `grep -n 'granularity: "month"' apps/web/lib/analytics/utils/get-interval-data.ts` → :44 :61 :66. Coverage caveat: NO direct unit test exists for either util (grep across `apps/web/tests/` finds none) — claims rest on whole-file source reads plus call site :82 of get-analytics.ts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", name_pattern: "^(getStartEndDates|getIntervalData)$", limit: 5, fields: ["signature"] });
```
(observed: getStartEndDates 6-54 fan-in 24; getIntervalData 70-73.)

## Verdict
Adopt precedence (custom range > interval preset > retention floor > epoch), the silent swap, and the width-driven granularity ladder. Adapt preset boundaries and timezone lib. Omit dub's founding-date constant value.
