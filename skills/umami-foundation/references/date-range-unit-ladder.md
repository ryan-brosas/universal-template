<!-- capsule-v2 -->
# Date-range grammar & unit ladder — how do you turn `value=1month`-style ranges into start/end/unit with automatic unit selection?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are named ranges, custom ranges, timezone-aware "now", and the minimum-chart-unit ladder computed?

## date-range-unit-ladder
**Path/Symbol:** `src/lib/date.ts:parseDateValue :106-116, parseDateRange :118-206, getOffsetDateRange :208-252, getMinimumUnit :265-282, getAllowedUnits :284-289, generateTimeSeries :351-370`; direct tests `src/lib/date.test.ts:57-471`.
**Signature:** `parseDateRange('1month'|'range:ms:ms', unit?, locale?, timezone?) -> {startDate,endDate,unit,num,value,offset}`.
**Data Shape:** unit ladder minute→hour→day→month→year chosen from SPAN: ≤60min ⇒ minute; ≤48h(range)/≤30d ⇒ hour; ≤7cal-months ⇒ day; ≤24 ⇒ month; else year.

### Decisive source
```ts
const now = timezone ? toZonedTime(date, timezone) : date;   // "today" means user's today
case 'day':
  return { startDate: num ? subDays(startOfDay(now), num) : startOfDay(now),
           endDate: endOfDay(now), unit: unitValue ? unitValue : num ? 'day' : 'hour', ... };
// getAllowedUnits: units.splice(index of minimum) — chart granularity can only be ≥ minUnit
```

**Flow:** string grammar (`N<unit>`, `range:start:end`) → boundary-snapped dates in the viewer's timezone → default unit = coarsest-fitting ladder rung unless explicitly overridden → compare periods shift by `num*offset` units (calendar functions per unit, not raw ms).
**Invariant:** boundaries snap with date-fns calendar math (startOfWeek honors locale) — never `Date.now() - N*86400000` (DST drift). The hour/day dual default on ranges (`unit: num ? 'day' : 'hour'`-style picks) keeps short ranges from rendering monthly buckets; `getAllowedUnits` returning [] for sub-minute spans signals "no chart".
**Probe:** `grep -cE "parses (hour|day|week|month|year) ranges" src/lib/date.test.ts` → 5 (:95 hour, :107 day, :119 week, :131 month, :143 year) plus null-inputs (:72,:80,:89).
**Probe:** `grep -c "differenceInCalendar" src/lib/date.ts` → ≥4 lines.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "parseDateRange getMinimumUnit getAllowedUnits generateTimeSeries", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt the span-driven unit ladder + tz-aware snapping for any dashboard time-range selector; adapt ladder thresholds to your data density; keep locale-aware week starts or your weeks silently shift.
