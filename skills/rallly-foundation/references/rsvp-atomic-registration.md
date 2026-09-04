<!-- capsule-v2 -->
# RSVP atomicity — how is duplicate registration rejected without a check-then-insert race?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How does event registration enforce one response per email while keeping cache freshness?

## createRsvp unique-index catch + tag revalidation
**Path/Symbol:** `apps/web/src/features/scheduled-event/mutations.ts:createRsvp` (lines 9–60) + `cancelRsvp` (62–77).
**Signature:** `createRsvp({ eventId, name, email, status: "accepted"|"declined", inviteeId?, locale?, timeZone? }) → { ok:true, inviteUid } | { ok:false, reason:"already_responded" }`.
**Data Shape:** DB unique `(scheduledEventId, inviteeEmail)` index; P2002 = Prisma known unique-violation code; invite rows capture locale/timeZone at registration for later emails.

### Decisive source
```ts
try {
  // The unique (scheduledEventId, inviteeEmail) index makes this atomic: a
  // concurrent duplicate fails with P2002 instead of racing past a prior
  // existence check.
  invite = await prisma.scheduledEventInvite.create({ data: { uid: nanoid(), scheduledEventId: eventId, /* ... */ status } });
} catch (e) {
  if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2002") {
    return { ok: false, reason: "already_responded" } as const;
  }
  throw e;
}
updateTag(scheduledEventTag(eventId));
```

**Flow:** insert-first → unique violation converts to a typed result, never an exception path → Next.js `updateTag(scheduledEventTag(eventId))` invalidates the event's cached views so capacity/attendee lists reflect the RSVP immediately.
**Invariant:** existence checks are NEVER trusted — only the constraint decides; result-shaped errors (ok/reason) keep the route free of try/catch UX logic; locale+timeZone are frozen at registration because later emails must render in the language/zone the invitee used when they signed up.
**Probe:** deterministic grep anchors: `grep -n 'P2002' apps/web/src/features/scheduled-event/mutations.ts` → lines 49–50; `grep -cF 'already_responded' apps/web/src/features/scheduled-event/mutations.ts` → 1.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "createRsvp already_responded updateTag", limit: 5 });
```

## Verdict
Adopt constraint-decides-dedup + captured-preferences verbatim; adapt to your ORM's unique-violation surface; omit Next.js updateTag if uncached. Source-pinned; no direct test file.
