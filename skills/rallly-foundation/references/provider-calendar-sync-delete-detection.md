<!-- capsule-v2 -->
# Provider calendar sync with deletion detection — how do you mirror a provider's resource list so deletions propagate but user choices survive?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** When a user deletes a calendar on Google, how does the local mirror learn about it, and how does a re-sync avoid clobbering which calendars the user picked?

## notIn-absence detection + dangling-reference sweep + field-split upsert in one transaction
**Path/Symbol:** `apps/web/src/features/calendars/mutations.ts:syncCalendars` (lines 76–182); provider read `features/calendars/google/service.ts:GoogleCalendarService.listCalendars` (lines 34–50); read model `features/calendars/data.ts:getCalendars` (lines 5–28); router `trpc/routers/calendars.ts` (sync mutation, privateProcedure).
**Signature:** `syncCalendars({ userId, connectionId }) → { success: true } | { success: false, error: "Calendar connection not found" | "Credential not found" }`.
**Data Shape:** `providerCalendar` rows keyed by `(calendarConnectionId, providerCalendarId)`; provider-controlled fields (`name`, `timeZone`, `isPrimary`, `isDeleted`, `isWritable`, `providerData`, `lastSyncedAt`) vs the single user-owned field (`isSelected`); users may point `defaultDestinationCalendarId` at any of their provider calendars.

### Decisive source
```ts
await prisma.$transaction(async (tx) => {
  const providerCalendarIds = calendars.map((cal) => cal.id);

  // Mark any calendars not in the response as deleted
  // (This handles calendars deleted from Google that aren't returned even with showDeleted=true)
  const deletedCalendars = await tx.providerCalendar.findMany({
    where: { calendarConnectionId: connection.id,
             providerCalendarId: { notIn: providerCalendarIds }, isDeleted: false },
    select: { id: true },
  });
  if (deletedCalendars.length > 0) {
    // Clear any users who have a deleted calendar as their default destination
    await tx.user.updateMany({ where: { defaultDestinationCalendarId: { in: deletedCalendarIds } },
                             data: { defaultDestinationCalendarId: null } });
    await tx.providerCalendar.updateMany({ where: { id: { in: deletedCalendarIds } },
                                          data: { isDeleted: true, lastSyncedAt: new Date() } });
  }
  for (const calendar of calendars) {
    await tx.providerCalendar.upsert({
      where: { connection_calendar_unique: { ... } },
      create: { ..., isSelected: calendar.isSelected, ... },
      update: {
        // Only update provider-controlled fields, preserve user customizations
        name: ..., timeZone: ..., isPrimary: ..., isDeleted: ..., isWritable: ...,
        lastSyncedAt: new Date(), providerData: ...,   // NOTE: no isSelected here
      },
    });
  }
});
```

**Flow:** ownership check (`findFirst {id, userId}`) → `loadCredential` (encrypted store, see encrypted-oauth-credential-store) → `createCalendarService` factory parses credentials through the provider's own zod schema → `listCalendars()` → ONE transaction: absence-detect → sweep dangling defaults → mark deleted → upsert survivors. Read side (`getCalendars`) filters `isDeleted: false` and orders by name, so a deleted calendar disappears from the UI while its row stays for audit/restore.
**Invariant:** absence in the provider response IS the deletion signal — the code comment records that Google omits deleted calendars even with showDeleted=true, so polling for an explicit "deleted" flag would never fire. The dangling-default sweep runs BEFORE the rows are marked deleted and inside the same transaction, so no reader can ever observe a `defaultDestinationCalendarId` pointing at a dead row. The upsert's create/update field split is the whole user-customization contract: `isSelected` exists in create (first sync adopts the provider's state) but is ABSENT from update (later syncs can never touch it). Every entry point scopes by `userId` and returns typed `{success:false, error}` instead of throwing.
**Probe:** no upstream test for calendars/mutations.ts (caveat recorded). Behavioral anchors verified by direct read: `notIn` at mutations.ts:120, default-clear updateMany at :133–139, delete-mark at :144, create-arm `isSelected` at :163 vs update-arm absence at :168–177, tx boundary at :110; listCalendars accessRole→isWritable at google/service.ts:48; read-side `isDeleted: false` filter at data.ts:18.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "syncCalendars providerCalendar", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-step transaction shape (absence-detect → dependent-reference sweep → field-split upsert) for ANY mirrored external resource list — it generalizes to webhooks, SSO groups, or device registries. Adopt soft-delete (`isDeleted` + read-side filter) over hard delete so reconnects and audits keep history. Adapt the provider factory to your SDK; keep the per-provider zod credential schema at the use site. Omit the raw `_rawData` blob if you don't need offline replay of provider payloads. Caveat: no direct test suite; the sync is exercised only through the tRPC mutation.
