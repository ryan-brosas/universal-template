<!-- capsule-v2 -->
# Vixie-cron kernel — how do I parse, match, and advance 5-field cron without a cron library?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** What are the exact parse/match/next-occurrence semantics (day-field OR rule, Sunday alias, scan bound) a porter must reproduce for cron firing to be correct?

## Parse → set-membership match → bounded next-occurrence scan
**Path/Symbol:** `packages/server/src/cron-expression.ts:parseCronExpression` (120–142), `cronMatchesDay` (145–152), `cronMatchesDate` (155–159), `nextCronOccurrence` (161–184).
**Signature:** `parseCronExpression(expression: string): ParsedCronExpression | null`; `cronMatchesDate(parsed, date: Date): boolean`; `nextCronOccurrence(parsed, from: Date): Date | null`.
**Data Shape:** `ParsedCronExpression` = five `ReadonlySet<number>` fields + two booleans (`isDayOfMonthRestricted`, `isDayOfWeekRestricted` = field text does NOT start with `*`). All invalid input returns `null` — never throws.

### Decisive source
```ts
// :145-152 — Vixie day semantics is THE trap
const cronMatchesDay = (parsed: ParsedCronExpression, date: Date): boolean => {
  const dayOfMonthMatches = parsed.daysOfMonth.has(date.getDate());
  const dayOfWeekMatches = parsed.daysOfWeek.has(date.getDay());
  if (parsed.isDayOfMonthRestricted && parsed.isDayOfWeekRestricted) {
    return dayOfMonthMatches || dayOfWeekMatches;
  }
  return dayOfMonthMatches && dayOfWeekMatches;
};
```

**Flow:** aliases (`@hourly`…`@annually`) resolve case-insensitively before splitting on `\s+` — exactly 5 fields or `null`. Field grammar: comma parts → optional `/step` (step must be integer ≥1; `*/0` rejected) → range `a-b` or `*`; names (jan…dec, sun…sat) case-insensitive; bare-value-with-step means value-to-max ("5/15" ⇒ {5,20,35,50}); out-of-range values reject the whole expression. `daysOfWeek.has(7)` adds 0 (Sunday dual encoding). Matching requires minute∧hour∧month∧day. `nextCronOccurrence` zeroes seconds and +1 minute (strictly-after contract: a matching `from` minute itself never matches), then scans with coarse skips (non-matching month/day ⇒ jump to next midnight; non-matching hour ⇒ next hour; non-matching minute ⇒ next minute) until `from + CRON_NEXT_OCCURRENCE_SCAN_LIMIT_DAYS` (constants.ts:738 = 1466 days ≈ 4 years, so Feb-29 schedules resolve but `0 0 31 2 *` returns `null`).
**Invariant:** when BOTH day fields are restricted the date matches if EITHER does (Vixie OR); when either field is a wildcard it defers entirely to the other (AND). Porters who implement plain AND for the both-restricted case break `0 9 13 * fri`. Every failure mode is `null`, so callers decide skip-vs-error.
**Probe:** `packages/server/tests/cron-expression.test.ts` — `"matches either day field when both are restricted (vixie semantics)"` (:99), `"treats a bare value with a step as value-to-max"` (:41), `"does not return a matching from minute itself"` (:115), `"returns null when the schedule can never fire"` (:136), `"rejects malformed expressions"` (:65).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "nextCronOccurrence parseCronExpression", limit: 5, detail: "compact" });
// → parseCronExpression @ cron-expression.ts:120-142, nextCronOccurrence @ :161-184
await mcp.codebase_memory.search_graph({ project: "localterm", query: "cronMatchesDate cronMatchesDay", limit: 5, detail: "compact" });
```

## Verdict
Adopt the whole kernel verbatim (~180 lines, zero deps) including the OR-rule, Sunday alias, and 1466-day scan bound; adapt the constants table if your host needs seconds/timezones; omit nothing — every branch is regression-pinned by 16 direct tests.
