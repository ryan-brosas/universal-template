<!-- capsule-v2 -->
# Upcoming/past predicate — how do all-day and timed events split "upcoming" without drift?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What single where-clause shape makes past the exact complement of upcoming for both event kinds, across viewer timezones?

## scheduledEventWhere dual-arm predicate
**Path/Symbol:** `apps/web/src/features/scheduled-event/utils.ts:scheduledEventWhere` (lines 89–112) + `upcomingScheduledEventWhere`/`pastScheduledEventWhere` (114–123).
**Signature:** `scheduledEventWhere({ now: Date; timeZone: string; past: boolean }): Prisma.ScheduledEventWhereInput`.
**Data Shape:** OR of two arms — `{allDay:false, end gt|lte now}` and `{allDay:true, end gt|lte todayUtcMidnight(viewerZone)}`.

### Decisive source
```ts
// For allDay rows, `start`/`end` are calendar dates encoded as UTC midnight,
// not instants, so they must be compared against "today in the viewer's zone"
// encoded the same way. `end` is stored exclusive (start + 1 day), so
// `end > todayUtcMidnight` keeps an event through its final day and handles
// multi-day spans. The timed arm uses `end > now` so in-progress meetings
// still count as upcoming. A single core with the gt/lte complements side by
// side makes past the exact negation of upcoming structurally, so the two
// cannot drift apart.
return {
  status: "confirmed",
  deletedAt: null,
  OR: [
    { allDay: false, end: past ? { lte: now } : { gt: now } },
    { allDay: true,  end: past ? { lte: todayUtcMidnight } : { gt: todayUtcMidnight } },
  ],
} satisfies Prisma.ScheduledEventWhereInput;
```

**Flow:** compute viewer's local date → encode as UTC midnight → one where-clause serves dashboard lists, registration gating (with getEventPhase) and calendar feeds; in-progress timed events stay upcoming because the comparison is on END.
**Invariant:** exclusive-end storage (`start + 24h`) means an all-day event is upcoming through its final day even for viewers already past midnight UTC; both arms must flip gt/lte together — deriving past from upcoming by hand-invoking negation is exactly the drift this shape prevents.
**Probe:** `apps/web/src/features/scheduled-event/utils.test.ts` ("is the exact negation of upcoming for the same inputs", :192–230 — replays the clause over 9 boundary events × 3 viewer zones).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "upcomingScheduledEventWhere scheduledEventWhere", limit: 5 });
```

## Verdict
Adopt the two-arm complement structure verbatim; adapt to your query dialect; omit the satisfies-typing if not TS. Fully pinned by a direct test that structurally enforces non-drift.
