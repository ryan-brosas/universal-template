<!-- capsule-v2 -->
# Notification preference JSONB merge — how do concurrent toggles of different preference keys avoid last-writer-wins clobber?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** When a user flips two notification switches from two tabs at once, what prevents one toggle from erasing the other's key in the shared JSONB row?

## UPDATE-first atomic merge with create fallback + P2002 retry
**Path/Symbol:** `apps/web/src/features/notifications/mutations.ts:updateNotificationPreference` (lines 8–51); entry `apps/web/src/features/notifications/actions.ts:updateNotificationPreferenceAction` (lines 8–25).
**Signature:** `updateNotificationPreference({ userId, eventType, enabled }) → Promise<void>`; raw arm returns the Prisma `$executeRaw` affected-row count.
**Data Shape:** one `user_notification_preferences` row per user; `prefs` jsonb keyed by activity event type → boolean.

### Decisive source
```ts
const patch = JSON.stringify({ [eventType]: enabled });

// The merge happens in the database (jsonb ||) so concurrent toggles of
// different keys can't clobber each other the way a read-merge-replace
// upsert would.
const mergeIntoExistingRow = () => prisma.$executeRaw`
  UPDATE user_notification_preferences
  SET prefs = prefs || ${patch}::jsonb, updated_at = now()
  WHERE user_id = ${userId}
`;

if ((await mergeIntoExistingRow()) > 0) {
  return;
}

// No row yet — create through Prisma for the client-generated cuid. A
// concurrent create surfaces as P2002 and falls back to the atomic merge.
try {
  await prisma.userNotificationPreferences.create({ data: { userId, prefs: { ...defaultNotificationPreferences, [eventType]: enabled } } });
} catch (e) {
  if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2002") {
    await mergeIntoExistingRow();
    return;
  }
  throw e;
}
```

**Flow:** stringify a single-key patch → try the raw `UPDATE ... prefs || patch` first → if it affected ≥1 row, done (the key merged atomically server-side) → else no row existed yet, so create through the Prisma client (which owns id generation) seeded with defaults + this key → if a concurrent creator won the unique constraint (P2002), re-run the raw merge instead of failing.
**Invariant:** never read-modify-write the whole prefs object on the hot path — a read-merge-replace upsert would silently drop the other tab's key between read and write; the create branch exists ONLY because Prisma owns the cuid, so porters who let the DB generate ids can collapse everything into one `INSERT ... ON CONFLICT DO UPDATE prefs || patch`.
**Probe:** deterministic grep anchors (executed): `grep -c 'prefs ||' apps/web/src/features/notifications/mutations.ts` → 1; `grep -n 'P2002' apps/web/src/features/notifications/mutations.ts` → lines 33 (comment) + 44 (code check). No dedicated upstream test for this file — shape pinned by source comments.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "updateNotificationPreference mergeIntoExistingRow", limit: 5 });
```

## Verdict
Adopt the UPDATE-first jsonb-merge + typed-conflict-retry ladder verbatim; adapt the raw-SQL dialect to your ORM's escape hatch; omit the Prisma-create branch if your schema generates ids in the database. See also `activity-event-prefs-codec` for the read side of the same column.
