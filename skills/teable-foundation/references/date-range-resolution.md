<!-- capsule-v2 -->
# DateRangeResolution — 27-mode date filter ranges with format-derived granularity

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a date filter value (today/oneWeekAgo/exactDate/currentMonth/pastNumberOfDays/...) become a concrete `{start,end}` ISO range, and why does granularity depend on the field's formatting preset?

## Date range resolution
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/visitors/TableRecordConditionWhereVisitor.ts` (`resolveDateRange` 486-676, `DateUtil` 228-278, `shouldCompareAsDateOnly`/`buildDateComparableExpr` ~440-475).
**Signature:** `resolveDateRange(value: RecordConditionDateValue, formatting?): Result<{start,end}, DomainError>`.
**Data Shape:** `value = { mode, numberOfDays?, exactDate?, timeZone }`. Modes: today/tomorrow/yesterday, oneWeekAgo/oneMonthAgo/oneWeekFromNow/oneMonthFromNow, daysAgo/daysFromNow, exactDate/exactDateTime/exactFormatDate, currentWeek/Month/Year, lastWeek/Month/Year, nextWeekPeriod/MonthPeriod/YearPeriod, pastWeek/Month/Year, nextWeek/Month/Year, pastNumberOfDays/nextNumberOfDays. `DateUtil` is timezone-aware (`dayjs.utc().tz(timeZone)`).

### Decisive source
```ts
const determineDateUnit = (): 'day' | 'month' | 'year' => {
  const dateFormat = formatting?.date() ?? DateFormattingPreset.ISO;
  return match(dateFormat)
    .with(DateFormattingPreset.Y, () => 'year')
    .with(DateFormattingPreset.YM, DateFormattingPreset.M, () => 'month')
    .otherwise(() => 'day');
};
// exactFormatDate: range granularity = the field's date-format preset
const parsed = dateUtil.date(raw); const unit = determineDateUnit();
return [parsed.startOf(unit), parsed.endOf(unit)];
```

**Flow:** `resolveRange` matches the mode → fixed-day modes (`today` etc.) use `dateUtil[method]()` startOf/endOf day; offset modes use `offsetDay/offsetWeek/offsetMonth`; exact modes parse the raw date; relative current/last/next modes set `dayjs.locale(locale, {weekStart:1})` and shift by unit; `pastNumberOfDays`/`nextNumberOfDays` use `generateOffsetDateRange`. `exactFormatDate` derives granularity from the field's date-format preset (Y→year, YM/M→month, else day). Returns `[start.toISOString(), end.toISOString()]`.

**Invariant:** All ranges are half-open `[start, end)` where end = startOf(unit)+1 for search, or inclusive startOf/endOf for filters; the timezone is the field's formatting timezone (default UTC); `exactFormatDate` granularity is format-driven, so a Y-only formatted date field matches a whole year.

**Probe:** `record/visitors/TableRecordConditionWhereVisitor.spec.ts` — `'date field reference comparisons'` (:527) and the date-mode describe blocks pin range boundaries.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveDateRange exactFormatDate determineDateUnit DateUtil offsetDay", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mode→range ladder and the format-preset-derived granularity. Adapt the dayjs locale/weekStart and timezone plumbing. Omit nothing portable. Probes pinned to the real spec suite.
