<!-- capsule-v2 -->
# Floating all-day options — how are date-only options encoded so they never shift across timezones?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** When a poll mixes date-only and timed options, what exactly is stored for each option, and what single field decides how every reader interprets it?

## Option storage: startTime + duration with timeZone as floating flag
**Path/Symbol:** `apps/web/src/trpc/routers/polls.ts:make` (lines 164–185) + `apps/web/src/trpc/routers/polls/schema.ts:timeZoneInput` (lines 8–11).
**Signature:** `make(input: { options: { startDate: string; endDate?: string }[]; timeZone: string | null | undefined })` → stores `{ startTime: Date; duration: number }` rows.
**Data Shape:** duration = minute-diff of endDate−startDate, or **0 for date-only**; poll.kind = `"time"` if any option has endDate else `"date"`; poll.timeZone set iff any option is timed.

### Decisive source
```ts
// Date-only (all-day) options are floating: they are stored at UTC
// midnight so they never shift across timezones. A falsy poll.timeZone
// is the single source of truth for "floating", so date-only polls drop
// any timezone the client sent, and date-only options of mixed polls
// ignore the poll's timezone.
const isTimePoll = input.options.some((option) => option.endDate);
const timeZone = isTimePoll ? input.timeZone : null;

const optionsData = input.options.map((option) => ({
  startTime:
    timeZone && option.endDate
      ? dayjs(option.startDate).tz(timeZone, true).toDate()
      : dayjs(option.startDate).utc(true).toDate(),
  duration: option.endDate
    ? dayjs(option.endDate).diff(dayjs(option.startDate), "minute")
    : 0,
}));
```

**Flow:** client sends dates (+optional end times) → if ANY option is timed, poll.timeZone kept and timed starts pinned via `.tz(tz, true)` (keep-local-time); otherwise timeZone forced to null and EVERY start stored with `.utc(true)` — date-only options land exactly on UTC midnight.
**Invariant:** falsy `poll.timeZone` ⟺ floating semantics everywhere (rendering, finalize emails, ICS export, upcoming/past predicates). A porter who "helpfully" defaults an empty timeZone to the viewer's zone breaks every date-only poll by one day for half the world. The boundary normalizes legacy `""` to null (`timeZoneInput` transform), but keeps `undefined` passing through untouched because in `modify` undefined means "leave unchanged".
**Probe:** `apps/web/src/trpc/routers/polls/schema.test.ts` ("keeps undefined as undefined so modify can mean 'leave unchanged'"; "normalizes an empty string to null").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "optionEndsInFuture make poll", limit: 5 });
```

## Verdict
Adopt the dual encoding (tz-pinned instants vs UTC-midnight floats) and the null-timeZone-as-flag contract verbatim; adapt the zod boundary shape to your schema lib; omit PostHog tracking calls. Direct tests exist only for the boundary normalization, not the dayjs arithmetic itself.
