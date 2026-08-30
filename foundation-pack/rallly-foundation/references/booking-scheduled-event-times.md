<!-- capsule-v2 -->
# Scheduled event times — when is a booked option an all-day UTC-midnight span vs a timed instant?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** When finalizing (booking) a poll option into a scheduled event, how are start/end/allDay/timeZone derived, and what legacy encoding must be repaired on the way?

## getScheduledEventTimes — the duration>0 fork with legacy snap
**Path/Symbol:** `apps/web/src/trpc/routers/polls/scheduled-event-times.ts:getScheduledEventTimes` (lines 13–47).
**Signature:** `getScheduledEventTimes({ startTime: Date; duration: number; timeZone: string | null }) → { allDay: boolean; start: Date; end: Date; timeZone: string | null }`.
**Data Shape:** timed branch returns `{allDay:false, start, start+duration, timeZone}`; all-day branch returns `{allDay:true, utcMidnight, utcMidnight+24h, timeZone:null}`.

### Decisive source
```ts
// All-day events are floating: start/end sit at exactly UTC midnight with no
// time zone. The upcoming-events predicate, finalize emails, and ICS files all
// read all-day dates via UTC, so any other encoding renders off by one day.
if (duration > 0) { /* ... timed branch keeps startTime + poll timeZone ... */ }

// Mixed polls used to encode date-only options at midnight in the poll's
// zone; snap those to the zone's calendar date. Options already at UTC
// midnight are correctly encoded and must not be shifted.
const isUtcMidnight = startTime.getTime() % DAY_MS === 0;
const start = calendarDateToUTCMidnight(
  timeZone && !isUtcMidnight
    ? getCalendarDate(startTime, timeZone)
    : toISODate(startTime),
);
```

**Flow:** duration>0 → timed event keeping the poll's zone (or null = floating wall time); duration 0 → snap to UTC midnight of the calendar date (re-deriving the date in the poll's zone ONLY for legacy zone-midnight rows; already-UTC rows pass through unshifted), timeZone nulled.
**Invariant:** all-day spans are ALWAYS `[UTC midnight, next UTC midnight)` with `timeZone: null`; `end` is exclusive. The `% DAY_MS === 0` guard is what prevents double-shifting correctly-encoded options — dropping it shifts every post-fix poll by a day.
**Probe:** `apps/web/src/trpc/routers/polls/scheduled-event-times.test.ts` (6 cases incl. west/east-of-UTC legacy snaps: Chicago 05:00Z → Oct 17, Tokyo Oct16 15:00Z → Oct 17).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "getScheduledEventTimes calendarDateToUTCMidnight", limit: 5 });
```

## Verdict
Adopt both branches + the UTC-midnight guard as-is (pure function, no host deps); adapt `getCalendarDate`/`toISODate` if your stack lacks Intl formatToParts helpers; omit nothing else. Fully pinned by direct unit tests.
