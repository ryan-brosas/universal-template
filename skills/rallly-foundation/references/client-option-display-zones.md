<!-- capsule-v2 -->
# Client option display — how does one renderer show tz-pinned, floating, and all-day options correctly?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** Given poll options + poll.timeZone + viewer zone, which zone renders each option kind in the browser?

## createOptionsContextValue display-zone fork
**Path/Symbol:** `apps/web/src/features/poll/components/poll-context.tsx:createOptionsContextValue` (lines 119–203).
**Signature:** `createOptionsContextValue({ pollOptions: {id; startTime; duration}[]; pollTimeZone: string | null; locale; timeZone?; timeFormat? }): { pollType: "date"|"timeSlot"; options }`.
**Data Shape:** duration>0 → timeSlot rows with formatted start/end times; duration 0 → date rows (month/day/dow/year only).

### Decisive source
```ts
if (pollOptions[0].duration > 0) {
  // Floating times are stored as UTC wall times, so reading them in UTC
  // shows them unshifted.
  const displayTimeZone = pollTimeZone ? timeZone : "UTC";
  /* ... format startTime/endTime in displayTimeZone ... */
} else {
  return {
    pollType: "date",
    options: pollOptions.map((option) => {
      // All-day options are floating dates: always read them in UTC so the
      // calendar date is identical for every viewer, regardless of timezone.
      const parts = formatDateParts(option.startTime, { locale, timeZone: "UTC" });
      /* ... */
    }),
  };
}
```

**Flow:** three rendering regimes from two bits (poll.timeZone set?, duration>0): fixed instants render in the VIEWER's zone (that's the point of storing an instant); floating wall times read in UTC (unshifted); all-day dates always UTC. The first option's duration classifies the whole poll.
**Invariant:** this mirrors the server's write-side encoding (floating-all-day-options capsule) — read-side must invert exactly what write-side did; the test file pins the historical bug ("viewer in an earlier timezone saw the prior day") that any divergence re-introduces.
**Probe:** `apps/web/src/features/poll/components/poll-context.test.ts` ("renders Jul 1 for viewer=%s, poll=%s" ×4 zone pairs; "shows floating times as stored, ignoring the viewer's zone", :78–91).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "createOptionsContextValue pollType timeSlot", limit: 5 });
```

## Verdict
Adopt the display-zone decision table verbatim; adapt formatting presets to your design system; omit React context wiring if you call it directly. Direct tests include the regression matrix across 4 zone pairs.
