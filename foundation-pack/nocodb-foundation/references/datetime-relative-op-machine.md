<!-- capsule-v2 -->
# DateTime relative-op machine — how do today/tomorrow/pastWeek compile to UTC BETWEEN windows, and which ops must NOT parse a date?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How are relative date sub-ops anchored, what does eq mean for a datetime (day window vs minute bucket), and why do null/blank/empty bypass the date parser entirely?

## DateTimeGeneralHandler.filter + overrides
**Path/Symbol:** `packages/nocodb/src/db/field-handler/handlers/date-time/date-time.general.handler.ts` — verifyFilter :34-162; filter :308-484 (isWithin sub-op logic inside, :426/:471); filterEq :486-519; filterNeq :521-555; gt/gte/lte/lt :557-716; blank/notblank :717-803; getNow :243; parseFilterValue :203.
**Signature:** `filter(knex, filter & {groupby?: boolean}, column, options)`; sub-ops switch :382-453 maps today/tomorrow/yesterday/oneWeekAgo/oneWeekFromNow/oneMonthAgo/oneMonthFromNow/daysAgo/daysFromNow/exactDate/pastWeek/pastMonth/pastYear/nextWeek/nextMonth/nextYear/pastNumberOfDays/nextNumberOfDays → anchorDate.
**Data Shape:** `dateValueFormat = 'YYYY-MM-DD HH:mm:ss'` (UTC, offset-less); timezone resolution ladder `filter.meta.timezone → column.meta.timezone → context.timezone` via getNodejsTimezone (:187-191).

### Decisive source
```ts
// :362-369 — the all-rows bug this routing kills:
// top-level NULL-check operators carry no date value — route straight to the
// generic handler. Otherwise they fall through to the date-parsing path below
// where the missing anchorDate short-circuits to an empty clause (all rows).
if (['blank','notblank','null','notnull','empty','notempty'].includes(filter.comparison_op)) {
  return await this.handleFilter({ val: filter.value, sourceField: field }, ...);
}
// :503-505 — eq is a WINDOW, not an instant:
const rangeDate = filter.groupby
  ? anchorDate.add(1, 'minute').add(-1, 'milliseconds')     // minute bucket
  : anchorDate.add(24, 'hours').add(-1, 'milliseconds');    // day window
```

**Flow:** `in` normalizes string entries through dayjs.utc→dateValueFormat because dialects with pinned session formats (Oracle NLS) reject the raw `+00:00` token with ORA-01830/01861 (:319-327) → keyword-valued is/isnot route straight to generic (parsing 'null' as a date previously returned ALL rows silently) → sub-op builds anchor from now (startOf day; startOf MINUTE when groupby) or exactDate → isWithin orders [anchor, now.startOf(day)+24h−1ms] by whichever is earlier → value ops pass `anchorDate.valueOf()` into overridden eq/neq/gt/gte/lt/lte.
**Invariant:** (1) eq = BETWEEN [day-start, +24h−1ms]; neq = `< anchor OR > range OR NULL`. (2) gt/gte/lt/lte detect a time component in the RAW filter string (`value.replace('T',' ').split(' ')[1]`) and use the parsed instant instead of the day window — date-only and datetime filters take different SQL shapes. (3) blank/notblank OVERRIDE to strict NULL forms (no '' comparison ever). (4) groupby flag switches both getNow AND rangeDate to minute granularity so grouped buckets match filtered ones.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "short-circuits to an empty clause" (:364); search_graph resolves `DateTimeGeneralHandler.filter Method ... :308-484` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "filterIsWithin", limit: 5 });
```

## Verdict
Adopt the anchor/window algebra and the null-op early routing; adapt format strings/timezone ladder; omit the debug() chatter. Caveat: no direct tests at pin.
