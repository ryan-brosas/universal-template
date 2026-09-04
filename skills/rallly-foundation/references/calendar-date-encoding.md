<!-- capsule-v2 -->
# Calendar-date encoding — how do you get a zone's YYYY-MM-DD without trusting locale patterns?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How are calendar dates extracted per-zone and re-encoded as UTC midnight, and why formatToParts instead of toLocaleDateString?

## getCalendarDate + calendarDateToUTCMidnight + normalizeTimeZone
**Path/Symbol:** `apps/web/src/lib/datetime/utils.ts:getCalendarDate` (21–31), `calendarDateToUTCMidnight` (37–39), `normalizeTimeZone` (46–56).
**Signature:** `getCalendarDate(now: Date, timeZone: string): string` → "YYYY-MM-DD"; `calendarDateToUTCMidnight(date: string): Date` → `new Date(date+"T00:00:00Z")`; `normalizeTimeZone(tz): string | undefined`.
**Data Shape:** parts assembled from `Intl.DateTimeFormat("en-CA", {timeZone, year/month/day 2-digit}).formatToParts`.

### Decisive source
```ts
// The calendar date (YYYY-MM-DD) at the given instant in the given zone.
// Assembled from formatToParts rather than a locale's date pattern: small-ICU
// Node builds (e.g. Alpine's icu-data-en) resolve unavailable locales to "en",
// whose pattern is MM/DD/YYYY, so no locale can be trusted to format ISO 8601.
const parts = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(now);
```
```ts
export function normalizeTimeZone(timeZone) {
  if (!timeZone) return undefined;
  try { new Intl.DateTimeFormat(undefined, { timeZone }); return timeZone; }
  catch { return undefined; }   // corrupt stored values would make Intl throw
}
```

**Flow:** every all-day computation routes through this pair: instant → zone's calendar date → UTC-midnight encoding matching the DB storage. normalizeTimeZone guards user/stored input before it reaches any DateTimeFormat constructor.
**Invariant:** never use `toLocaleDateString("sv-SE")`-style tricks or trust a locale's output pattern — small-ICU builds silently remap locales and hand you MM/DD/YYYY; the formatToParts assembly works on every ICU build. Corrupt timeZone strings must degrade to undefined, not throw inside a request.
**Probe:** deterministic grep anchors: `grep -n 'formatToParts' apps/web/src/lib/datetime/utils.ts` → lines 17 (comment) + 27 (call); `grep -cF 'T00:00:00Z' apps/web/src/lib/datetime/utils.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "getCalendarDate calendarDateToUTCMidnight normalizeTimeZone", limit: 5 });
```

## Verdict
Adopt verbatim — three tiny pure functions with no deps beyond Intl; adapt the en-CA choice only if you also control ICU builds; omit normalizeTimeFormat if you have no 12/24h preference.
