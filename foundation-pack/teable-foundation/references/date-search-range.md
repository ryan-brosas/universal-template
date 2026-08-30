<!-- capsule-v2 -->
# DateSearchRange — free-text date search value → half-open range

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a free-text date search value (`2024`, `2024-03`, `2024-03-15`, `2024-03-15 10:30`) become a half-open `{start,end}` range, and what formatting gates it?

## Date search range
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/dateSearchRange.ts` (whole file, 18-76).
**Signature:** `getDateSearchRange(rawSearchValue, formatting?): IDateSearchRange | null`.
**Data Shape:** `IDateSearchRange = { start, end }` ( ISO strings, half-open `[start, end)` ). Patterns: `^\d{4}$`→year, `^\d{4}-\d{2}$`→month, `^\d{4}-\d{2}-\d{2}$`→day, `^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}$`→minute.

### Decisive source
```ts
const isUnitAllowed = (unit, formatting) => {
  const dateFormat = formatting?.date() ?? DateFormattingPreset.ISO;
  const hasTime = formatting != null && formatting.time() !== TimeFormatting.None;
  switch (unit) {
    case 'year': return true;
    case 'month': return dateFormat !== DateFormattingPreset.Y;
    case 'day':   return dateFormat !== DateFormattingPreset.Y && dateFormat !== DateFormattingPreset.YM;
    case 'minute': return hasTime;
  }
};
// parse in the field's timezone, then round-trip-validate the format
const parsed = dayjs.tz(normalizedSearchValue, candidate.format, timeZone);
if (!parsed.isValid() || parsed.format(candidate.format) !== normalizedSearchValue) continue;
const start = parsed.startOf(candidate.unit);
const end = start.add(1, candidate.unit); // half-open
```

**Flow:** trim → empty→null → for each pattern: skip if regex fails OR unit not allowed by the field's date-format preset → normalize (minute `T`→space) → parse in the field timezone → round-trip-validate (parse then reformat must equal input) → return `[startOf(unit), startOf(unit)+1unit]`.

**Invariant:** The unit is gated by the field's date-format preset (a Y-only field rejects month/day granularity; time granularity requires `TimeFormatting.None` absent); the range is half-open; round-trip validation rejects ambiguous/non-round inputs.

**Probe:** `record/repository/RecordSearchWhereBuilder.pglite.spec.ts` (and the jieba integration spec) — pins date-search range derivation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getDateSearchRange dateSearchPatterns isUnitAllowed startOf", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern ladder, format-preset unit gating, round-trip validation, and half-open range. Adapt the dayjs/tz plumbing. Omit nothing portable. Probes pinned to the real specs.
