<!-- capsule-v2 -->
# Email datetime rendering — which timezone does each recipient's event email use?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** Given start/end/allDay/timeZone/inviteeTimeZone/locale/timeFormat, what zone and labels render in finalize/cancel emails?

## formatEventDateTime three-zone semantics
**Path/Symbol:** `apps/web/src/features/scheduled-event/utils.ts:formatEventDateTime` (lines 45–79).
**Signature:** `formatEventDateTime(opts): { date: string; day: string; dow: string; time?: string }` — time undefined for all-day.
**Data Shape:** displayTimeZone = `"UTC"` if allDay or !timeZone, else `inviteeTimeZone || timeZone`; showTimeZone only when the event has a zone.

### Decisive source
```ts
// Zone semantics:
// - All-day events are stored as UTC midnight and format in UTC, so every
//   recipient sees the same date.
// - Fixed events (with a zone) render in the recipient's zone when known,
//   falling back to the event's zone, with the zone name appended.
// - Floating events (no zone) render their wall time, stored as UTC, with no
//   zone name.
const displayTimeZone = allDay || !timeZone ? "UTC" : inviteeTimeZone || timeZone;
```

**Flow:** host email formats with the HOST's locale/timeFormat and no inviteeTimeZone → each participant email re-formats with THEIR captured locale + inviteeTimeZone (captured at RSVP time on the invite row). The poll's floating option encoding decides which of the three zones applies — this function never re-derives storage, it only renders.
**Invariant:** the same event legitimately renders different times per recipient, EXCEPT all-day events which must render identically worldwide (that is what UTC-midnight storage buys); `time: undefined` is the template's signal to render a localized "All-day" label instead of a clock time.
**Probe:** `apps/web/src/features/scheduled-event/utils.test.ts` formatEventDateTime suite (:12–89 — all-day-in-UTC, fixed-in-invitee-zone-with-EDT, fallback-to-event-zone, floating-no-zone-name regex `/GMT|UTC|[A-Z]{3,4}$/`, hours24, German locale).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "formatEventDateTime inviteeTimeZone", limit: 5 });
```

## Verdict
Adopt the three-zone decision table verbatim; adapt formatting to your i18n stack (Intl presets here); omit nothing. Direct tests pin all six rendering behaviors including negative regex assertions.
