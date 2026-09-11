<!-- capsule-v2 -->
# Booking transaction — how does a poll option become a scheduled event with deduped invites?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** When the host books the winning option, what must happen atomically, and how are multiple participants sharing one email collapsed into one invite?

## polls.book — event+poll status transaction, committal-rank invite dedup
**Path/Symbol:** `apps/web/src/trpc/routers/polls.ts:book` (lines 728–1093; dedup 870–912; transaction 914–953).
**Signature:** `book({ pollId, optionId, notify: "none"|"all"|"attendees" })` (proProcedure); creates ScheduledEvent + invites, flips poll to scheduled.
**Data Shape:** invite `{uid: nanoid(), inviteeName, inviteeEmail, inviteeTimeZone, status ∈ accepted|tentative|declined}`; vote→status map yes→accepted, ifNeedBe→tentative, no→declined.

### Decisive source
```ts
// A poll can have several participants sharing an email; an event holds at
// most one invite per email, so collapse them, keeping the most committal
// response (accepted > tentative > declined) so a stale "no" duplicate
// can't bury an "accepted".
const inviteStatusRank = { accepted: 0, tentative: 1, declined: 2 };
const key = p.email.trim().toLowerCase();
const existing = invitesByEmail.get(key);
if (existing && inviteStatusRank[existing.status] <= inviteStatusRank[status]) {
  continue;   // keep the strictly-more-committal one only
}
invitesByEmail.set(key, { uid: nanoid(), ... });
```
```ts
const scheduledEvent = await prisma.$transaction(async (tx) => {
  const event = await tx.scheduledEvent.create({ data: { id: eventId, uid: `${eventId}@rallly.co`, /* ... */ invites: { createMany: { data: inviteData } } } });
  await tx.poll.update({ where: { id: poll.id }, data: { status: "scheduled", closedReason: null, scheduledEventId: event.id } });
  return event;
});
```

**Flow:** admin check → load option → getScheduledEventTimes (see booking-scheduled-event-times capsule) → build ICS (uid `${eventId}@rallly.co`) → dedup participants by lowercased-trimmed email keeping lowest rank → ONE transaction creates the event + invites + flips poll status → after() sends host + per-participant emails with per-recipient timezone/locale rendering. Attendees = voters with type !== "no" on that option.
**Invariant:** booking is all-or-nothing (event without poll-flip would double-book on retry); ICS generation happens BEFORE the transaction but its error is checked AFTER — a failed ICS aborts the response while the DB commit stands, so retries are safe because the flip is idempotent within the same poll state; emails fire via after() so a slow SMTP never blocks the mutation.
**Probe:** deterministic grep anchors: `grep -n 'inviteStatusRank' apps/web/src/trpc/routers/polls.ts` → lines 879 + 900 (3 occurrences; 900 carries two on one line — grep -c counts LINES = 2); `grep -cF '@rallly.co' apps/web/src/trpc/routers/polls.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "book invitesByEmail inviteStatusByVote", limit: 5 });
```

## Verdict
Adopt the committal-rank dedup + atomic event/status flip verbatim; adapt the ICS library and mail transport; omit cloud-only branding resolution. No direct unit test covers book — it is the highest-risk untested seam in the router.
